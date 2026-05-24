#!/usr/bin/env python3
"""1Password-backed storage helpers for Hermes Google OAuth files.

Local files under ~/.hermes remain the runtime cache expected by Google client
libraries. When ~/.hermes/google_oauth_op_refs.json maps a local path to an
op:// reference, these helpers can re-materialize a missing cache from
1Password and write refreshed OAuth JSON back to 1Password without passing
secrets on the command line.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import unquote

from _hermes_home import get_hermes_home

HERMES_HOME = get_hermes_home()
REFS_PATH = HERMES_HOME / "google_oauth_op_refs.json"


def _path_key(path: Path) -> str:
    return str(path.expanduser().resolve())


def _load_refs() -> dict:
    try:
        return json.loads(REFS_PATH.read_text())
    except Exception:
        return {}


def op_ref_for_path(path: Path) -> str | None:
    key = _path_key(path)
    refs = _load_refs()
    for section in ("tokens", "client_secrets"):
        entries = refs.get(section) or {}
        for entry in entries.values():
            if _path_key(Path(entry.get("path", ""))) == key:
                return entry.get("op_ref")
    return None


def _run_op(args: list[str], *, input_text: str | None = None) -> subprocess.CompletedProcess:
    # Hermes cron/tool shells do not always inherit OP_SESSION_* even though the
    # devbox has a keep-alive. Source Shan's 1Password session and, if needed,
    # run the headless auth helper before invoking `op`. Args are passed after
    # `--`, so secret refs/values are not interpolated into the shell command.
    script = (
        "source ~/.bashrc >/dev/null 2>/dev/null || true; "
        "source ~/.op_session >/dev/null 2>/dev/null || true; "
        "if ! op whoami >/dev/null 2>/dev/null; then "
        "  ~/bin/op_auth >/dev/null 2>/dev/null || true; "
        "  source ~/.op_session >/dev/null 2>/dev/null || true; "
        "fi; "
        "exec op \"$@\""
    )
    return subprocess.run(
        ["bash", "-lc", script, "op", *args],
        input=input_text,
        text=True,
        capture_output=True,
        stdin=subprocess.PIPE if input_text is not None else subprocess.DEVNULL,
        env=os.environ.copy(),
    )


def _op_read(ref: str) -> str | None:
    if not ref:
        return None
    proc = _run_op(["read", ref])
    if proc.returncode != 0:
        return None
    return proc.stdout


def _parse_op_ref(ref: str) -> tuple[str, str, str] | None:
    # op://Vault/Item/Field[/section] — item may be an item ID, which is what we
    # store in Shan's config to avoid title drift. Keep parsing deliberately
    # minimal because this helper only needs vault + item + field.
    if not ref.startswith("op://"):
        return None
    parts = ref[len("op://"):].split("/")
    if len(parts) < 3:
        return None
    return unquote(parts[0]), unquote(parts[1]), unquote(parts[2])


def _op_write(ref: str, value: str) -> bool:
    parsed = _parse_op_ref(ref)
    if not parsed:
        return False
    vault, item, field_id = parsed
    get_proc = _run_op(["item", "get", item, "--vault", vault, "--format", "json"])
    if get_proc.returncode != 0:
        return False
    try:
        data = json.loads(get_proc.stdout)
    except Exception:
        return False
    found = False
    for field in data.get("fields") or []:
        if field.get("id") == field_id or field.get("label") == field_id:
            field["value"] = value
            found = True
            break
    if not found:
        data.setdefault("fields", []).append(
            {"id": field_id, "type": "CONCEALED", "label": field_id, "value": value}
        )
    fd, tmp = tempfile.mkstemp(prefix="google-oauth-op-write-", suffix=".json")
    os.close(fd)
    try:
        os.chmod(tmp, 0o600)
        Path(tmp).write_text(json.dumps(data, indent=2), encoding="utf-8")
        edit_proc = _run_op(["item", "edit", data.get("id", item), "--template", tmp, "--format", "json"])
        return edit_proc.returncode == 0
    finally:
        try:
            os.remove(tmp)
        except FileNotFoundError:
            pass


def write_json_cache(path: Path, payload: dict) -> None:
    """Atomically write a local OAuth JSON cache with mode 0600."""
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2)
            fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def write_text_cache(path: Path, text: str) -> None:
    path = path.expanduser()
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(text)
            if not text.endswith("\n"):
                fh.write("\n")
        os.chmod(tmp, 0o600)
        os.replace(tmp, path)
        os.chmod(path, 0o600)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def ensure_materialized(path: Path, *, force: bool = False) -> bool:
    """Ensure local cache exists, using 1Password if configured.

    Returns True when the file was materialized from 1Password. If the local
    file already exists and force=False, just fixes permissions and returns
    False. This keeps cron/API calls working even when 1Password is temporarily
    locked, while still allowing recovery after local cache deletion.
    """
    path = path.expanduser()
    if path.exists() and not force:
        try:
            os.chmod(path, 0o600)
        except OSError:
            pass
        return False
    ref = op_ref_for_path(path)
    if not ref:
        return False
    text = _op_read(ref)
    if not text:
        return False
    # Validate JSON before writing; all current Google OAuth sources are JSON.
    try:
        json.loads(text)
    except Exception:
        print(f"ERROR: 1Password credential for {path.name} is not valid JSON", file=sys.stderr)
        return False
    write_text_cache(path, text)
    return True


def write_back_if_configured(path: Path) -> bool:
    """Write the current local file content back to its mapped 1Password field."""
    ref = op_ref_for_path(path)
    if not ref or not path.exists():
        return False
    text = path.read_text(encoding="utf-8")
    try:
        json.loads(text)
    except Exception:
        return False
    return _op_write(ref, text)


def save_json_and_write_back(path: Path, payload: dict) -> None:
    write_json_cache(path, payload)
    if op_ref_for_path(path):
        ok = write_back_if_configured(path)
        if not ok:
            print(f"WARNING: Saved local Google OAuth cache but could not update 1Password for {path.name}", file=sys.stderr)
