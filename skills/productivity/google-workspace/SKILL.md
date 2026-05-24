---
name: google-workspace
description: "Gmail, Calendar, Drive, Docs, Sheets via gws CLI or Python."
version: 1.0.0
author: Nous Research
license: MIT
metadata:
  hermes:
    tags: [Google, Gmail, Calendar, Drive, Sheets, Docs, Contacts, Email, OAuth]
    homepage: https://github.com/NousResearch/hermes-agent
    related_skills: [himalaya]
---

# Google Workspace

Gmail, Calendar, Drive, Contacts, Sheets, and Docs — through Hermes-managed OAuth and a thin CLI wrapper. When `gws` is installed, the skill uses it as the execution backend for broader Google Workspace coverage; otherwise it falls back to the bundled Python client implementation.

## References

- `references/gmail-search-syntax.md` — Gmail search operators (is:unread, from:, newer_than:, etc.)
- `references/drive-inventory.md` — Full Drive metadata traversal, shared-folder-vs-shared-drive detection, and Shan's Chalo household folder notes.
- `references/drive-organization-audits.md` — Shan-specific Drive audit/reorg proposal and root-level execution pattern.
- `references/drive-recursive-reorg.md` — Recursive Drive organization after root cleanup: no relabeling, idempotent resume, cross-check, and Tailscale reporting.
- `references/drive-dedupe-cleanup.md` — Shan-specific Drive dedupe cleanup: exact-binary duplicate Trash workflow, review group approvals, canonical swaps, rename passes, recovery verification, and readable card-based review artifacts.
- `references/drive-tax-payroll-equity-analysis.md` — Shan-specific Drive workflow for tax/payroll/RSU analysis: extensive Drive search, W-2/return extraction, marginal-rate modeling, RSU/withholding gaps, and evidence-first summaries.
- `references/gmail-label-harmonization.md` — Shan-specific Gmail label/folder harmonization workflow across primary and secondary accounts, including canonical mappings and mutation safety sequence.
- `references/gmail-inbox-triage.md` — Shan-specific Gmail inbox cleanup workflow: bucket messages, archive/read low-risk noise, unsubscribe/filter recurring senders, and verify remaining attention list.
- `references/gmail-lifecycle-cleanup-audit-reports.md` — pattern for scheduled Gmail cleanup jobs that mutate labels/archive state: compact cron notification plus served HTML audit with exact message IDs, snippets, category examples, and safety-skip examples.
- `references/personal-vendor-email-investigations.md` — reconstruct old paid appointments/vendor relationships from Gmail across both accounts, sent mail, scheduler/order emails, and current vendor reputation checks.
- `references/external-scheduler-booking.md` — booking workflow for external scheduler links such as Acuity: verify source email/account, compare calendar slots, handle chip-style email inputs, confirm via browser + Gmail, and create a clean calendar hold.
- `references/opentable-reservation-account-linking.md` — OpenTable confirmation/calendar workflow, app account-linking glitches after email changes, and support-form template.
- `references/gmail-ebay-purchase-reconstruction.md` — reconstruct Shan's eBay/PayPal purchase chains, seller replies, totals, and used-electronics accessory buy lists from HTML-heavy Gmail messages.
- `references/dmv-real-id-workflow.md` — Shan-specific CA DMV REAL ID cancellation/update workflow: search both Gmail accounts, extract official notices, use Drive DL scans only with explicit authorization, and book DMV appointments with reCAPTCHA fallback.
- `references/alumni-gmail-cleanup-2026-05.md` — Session-specific alumni Gmail routing decisions for bulk unread cleanup, category backlog handling, LinkedIn/career routing, and exact-count verification.
- `references/opentable-reservation-account-repair.md` — OpenTable reservation confirmation/account-linking repair workflow, including Gmail searches, support form template, and Salesforce submit-click pitfall.
- `references/cron-auth-health-check.md` — Pre-flight token health check crons should run before spending LLM tokens on Google Workspace operations; detects 0-byte corruption and invalid JSON.
- `references/secondary-google-account-oauth-pkce.md` — Manual PKCE fallback for secondary account OAuth when mobile consent/redirect handling needs precise control; includes token path, `OAUTHLIB_INSECURE_TRANSPORT`, and verification steps.
- `references/mobile-oauth-reauth.md` — Phone-first secondary-account reauth playbook: narrow Gmail-only scopes when mobile consent loops, devbox/phone handoff boundaries, and device-code caveat.
- `references/cloudflare-oauth-callback.md` — Temporary Cloudflare HTTPS callback pattern for headless/mobile Google OAuth reauth: Web OAuth client, exact redirect URI, full-scope code exchange, token verification, and tunnel teardown.
- `references/google-oauth-client-programmatic-limits.md` — Google OAuth client creation/editing limits: check admin/service keys first when Shan says they exist, but regular Gmail OAuth clients/redirect URIs generally require Cloud Console; IAP programmatic OAuth clients are not a Gmail callback workaround.
- `references/google-docs-table-scorecard-pattern.md` — Replace a raw list in a Google Doc with real embedded table scorecards while preserving surrounding sections and avoiding unsolicited proofreading.
- `references/gws-cli-fallback.md` — Install and use the npm `@googleworkspace/cli` (`gws`) via the Hermes OAuth bridge as a structured fallback/introspection path without replacing Shan-specific wrapper workflows.
- `references/sheets-financial-modeling.md` — Formula-first Google Sheets financial modeling pattern: update source Inputs for global assumptions, write formulas with `USER_ENTERED`, and verify both formula presence and zero formula errors before reporting done.

## Scripts

- `scripts/setup.py` — OAuth2 setup (run once to authorize)
- `scripts/google_api.py` — compatibility wrapper CLI. It prefers `gws` for operations when available, while preserving Hermes' existing JSON output contract.
- `scripts/google_oauth_store.py` — 1Password-backed OAuth materializer/writeback helper. Local token/client files are runtime caches when `~/.hermes/google_oauth_op_refs.json` maps them to `op://...` references.

## Pre-flight: Python dependencies

The `google_api.py` wrapper requires the Google Python client libraries. Before any Gmail/Calendar/Drive operation, verify they are importable:

```bash
python3 -c "from googleapiclient.discovery import build; print('READY')" 2>&1
```

If this fails with `ModuleNotFoundError: No module named 'googleapiclient'`, install:

```bash
pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

Do NOT proceed with search/get/send/calendar/drive commands until this check passes. Every session that loads this skill should run the check once before the first API call — the devbox may be freshly provisioned or packages uninstalled.

## First-Time Setup

The setup is fully non-interactive — you drive it step by step so it works
on CLI, Telegram, Discord, or any platform.

Define a shorthand first:

```bash
GSETUP="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py"
```

### Step 0: Check if already set up

```bash
$GSETUP --check
```

If it prints `AUTHENTICATED`, skip to Usage — setup is already done.

### Step 1: Triage — ask the user what they need

Before starting OAuth setup, ask the user TWO questions:

**Question 1: "What Google services do you need? Just email, or also
Calendar/Drive/Sheets/Docs?"**

- **Email only** → They don't need this skill at all. Use the `himalaya` skill
  instead — it works with a Gmail App Password (Settings → Security → App
  Passwords) and takes 2 minutes to set up. No Google Cloud project needed.
  Load the himalaya skill and follow its setup instructions.

- **Google Workspace access** → Continue with this skill. The bundled
  `setup.py` currently requests its configured `SCOPES` as a single set; it does
  **not** accept `--services` or `--format` flags. Before promising narrow or
  full scopes, inspect `scripts/setup.py` / `scripts/google_api.py` and patch
  `SCOPES` if needed. For Shan-approved full access, use Gmail read/send/modify,
  Calendar full, Drive full (`/auth/drive`), Sheets full, and Docs full
  (`/auth/documents`). Include Gmail settings access (`/auth/gmail.settings.basic`) when workflows may inspect, create, update, or delete Gmail filters, because filter management is a separate OAuth permission from Gmail read/modify.

**Question 2: "Does your Google account use Advanced Protection (hardware
security keys required to sign in)? If you're not sure, you probably don't
— it's something you would have explicitly enrolled in."**

- **No / Not sure** → Normal setup. Continue below.
- **Yes** → Their Workspace admin must add the OAuth client ID to the org's
  allowed apps list before Step 4 will work. Let them know upfront.

### Step 2: Create OAuth credentials (one-time, ~5 minutes)

Tell the user:

> You need a Google Cloud OAuth client. This is a one-time setup:
>
> 1. Create or select a project:
>    https://console.cloud.google.com/projectselector2/home/dashboard
> 2. Enable the required APIs from the API Library:
>    https://console.cloud.google.com/apis/library
>    Enable: Gmail API, Google Calendar API, Google Drive API,
>    Google Sheets API, Google Docs API, People API
> 3. Create the OAuth client here:
>    https://console.cloud.google.com/apis/credentials
>    Credentials → Create Credentials → OAuth 2.0 Client ID
> 4. Application type: "Desktop app" → Create
> 5. If the app is still in Testing, add the user's Google account as a test user here:
>    https://console.cloud.google.com/auth/audience
>    Audience → Test users → Add users
> 6. Download the JSON file and tell me the file path
>
> Important Hermes CLI note: if the file path starts with `/`, do NOT send only the bare path as its own message in the CLI, because it can be mistaken for a slash command. Send it in a sentence instead, like:
> `The JSON file path is: /home/user/Downloads/client_secret_....json`

Once they provide the path:

```bash
$GSETUP --client-secret /path/to/client_secret.json
```

If they paste the raw client ID / client secret values instead of a file path,
write a valid Desktop OAuth JSON file for them yourself, save it somewhere
explicit (for example `~/Downloads/hermes-google-client-secret.json`), then run
`--client-secret` against that file.

### Step 3: Get authorization URL

Run:

```bash
$GSETUP --auth-url
```

This prints the OAuth URL directly and stores PKCE state in
`~/.hermes/google_oauth_pending.json`. For named secondary accounts, pass `--account <email>` so pending state is written under `~/.hermes/google_tokens/`. It does **not** return JSON and does not
support `--services` / `--format` unless the script has been explicitly upgraded.

Agent rules for this step:
- Send the exact printed URL to the user as a single line.
- If Shan is on his phone, give phone-first instructions: open in Safari/Chrome rather than Telegram's in-app browser, confirm the exact Google account shown, scroll to the bottom, tap Continue, then copy the full broken `localhost:1` URL back.
- Tell the user that the browser will likely fail on `http://localhost:1` after approval, and that this is expected.
- Tell them to copy the ENTIRE redirected URL from the browser address bar.
- If the user gets `Error 403: access_denied`, send them directly to `https://console.cloud.google.com/auth/audience` to add themselves as a test user.
- If mobile consent loops on the all-Workspace URL, do not keep resending the same URL. Use `references/mobile-oauth-reauth.md` to generate a narrower Gmail-only PKCE URL for the specific secondary account, usually `gmail.modify` for cleanup/archive/label workflows.

### Step 4: Exchange the code

The user will paste back either a URL like `http://localhost:1/?code=4/0A...&scope=...`
or just the code string. Either works. The `--auth-url` step stores a temporary
pending OAuth session locally so `--auth-code` can complete the PKCE exchange
later, even on headless systems:

```bash
$GSETUP --auth-code "THE_URL_OR_CODE_THE_USER_PASTED"
```

If `--auth-code` fails because the code expired, was already used, or came from
an older browser tab, run `$GSETUP --auth-url` again and send the fresh URL to
the user.

### Step 5: Verify

```bash
$GSETUP --check
chmod 600 ~/.hermes/google_token.json ~/.hermes/google_tokens/*.json 2>/dev/null || true
```

Should print `AUTHENTICATED`. Setup is complete — token refreshes automatically from now on. After auth, lock token files to user-only permissions (`600`) because they contain refresh tokens.

### Notes

- Token is stored at `~/.hermes/google_token.json` and auto-refreshes.
- On Shan's devbox, Google Workspace token/client JSONs may also be mapped in `~/.hermes/google_oauth_op_refs.json` to 1Password `op://...` references. In that mode, 1Password is the durable source of truth and local files are runtime caches/materializations for Google client libraries. `scripts/google_oauth_store.py` can re-materialize a missing local token/client JSON and writes refreshed token JSON back to 1Password when possible.
- Pending OAuth session state/verifier are stored temporarily at `~/.hermes/google_oauth_pending.json` until exchange completes.
- If `gws` is installed, `google_api.py` points it at the same `~/.hermes/google_token.json` credentials file. Users do not need to run a separate `gws auth login` flow.
- To revoke: `$GSETUP --revoke`

## Usage

All commands go through the API script for standard Workspace actions. Set `GAPI` as a shorthand:

```bash
GAPI="python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/google_api.py"
## Usage

### GWS CLI fallback / broad Workspace introspection

The primary path remains `google_api.py` and direct Google API Python because Shan-specific workflow rules live in this skill. For Workspace APIs or schema exploration outside the wrapper's narrow surface, use `gws` through the packaged bridge rather than creating a separate auth store:

```bash
python ~/.hermes/skills/productivity/google-workspace/scripts/gws_bridge.py \
  calendar calendarList list --params '{"maxResults":3}'
```

If `gws` is not installed, install the npm package `@googleworkspace/cli`; see `references/gws-cli-fallback.md` for the exact install/verify pattern and examples. Do not present `gws` as a replacement for the wrapper, and do not assume it avoids Google OAuth revocation — it still depends on a valid Hermes OAuth token when used via the bridge.

### Pre-flight: Cron auth health check

Before spending LLM tokens in a cron that uses Google Workspace, gate on token validity:

```bash
# Gate — abort if primary token is 0 bytes or missing
python3 -c "
import os; p=os.path.expanduser('~/.hermes/google_token.json')
if not os.path.exists(p) or os.path.getsize(p)==0: exit(1)
"
```

Full health check recipe with multi-account support: `references/cron-auth-health-check.md`.

Add this to cron prompts: "Run pre-flight: check Google token health. If CORRUPT, abort and notify. If OK, proceed."

### Gmail: filing handled career/interview threads

When Shan says a career/interview/business-case thread is done and asks you to folder/file it appropriately:
- Search both Gmail accounts, but mutate only the specific handled thread(s) that match the request.
- Resolve label IDs first with `gmail labels`; user labels require opaque IDs, not names.
- For handled interview/recruiter threads, a good default is `S&P/Career/Recruiter Outreach` plus `Hermes/Responded`, then remove `INBOX` from every message in the handled thread. Do not remove `SENT` or system category labels.
- If the thread has split into an old handled thread and a new next-step/action-required thread, file only the old handled thread and leave the new next-step thread in Inbox.
- Verify with a narrow `in:inbox subject:"..." newer_than:...` query after mutation.

### Gmail: account routing and missing-message checks

When the user says an expected email is missing:

For OpenTable reservation confirmations

1. Verify which account the token/search is using:
   ```bash
   python3 - <<'PY'
   from pathlib import Path
   from google.oauth2.credentials import Credentials
   from googleapiclient.discovery import build
   creds=Credentials.from_authorized_user_file(str(Path.home()/'.hermes/google_token.json'))
   print(build('gmail','v1',credentials=creds,cache_discovery=False).users().getProfile(userId='me').execute())
   PY
   ```
2. Search primary and any secondary configured accounts before saying the email is absent. Use `--account <email>` for secondary accounts. For Shan's alumni account, prefer this wrapper; `gog` is legacy and invalid_grant-prone and should not be used to conclude Google Workspace is unavailable. Current token locations: primary `~/.hermes/google_token.json`; alumni `~/.hermes/google_tokens/shandutt_alumni_stanford_edu.json`.
   ```bash
   $GAPI --account shandutt@alumni.stanford.edu gmail search 'in:anywhere newer_than:3d (from:ebay OR subject:eBay OR subject:offer)' --max 20
   python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/setup.py --account shandutt@alumni.stanford.edu --check
   ```
3. If Gmail query syntax is uncertain, direct-scan recent messages with the Gmail API metadata endpoint across `includeSpamTrash=True`.
4. For Shan specifically, eBay notifications may route to `shandutt@alumni.stanford.edu`, not the primary `shandutta90@gmail.com`.
5. For eBay purchase/seller-message reconstruction, load `references/gmail-ebay-purchase-reconstruction.md`; read the complete offer → seller reply → invoice → order confirmation → PayPal chain before recommending what to buy or what to do next. Use the `gws`/`google_api.py --account ...` wrapper for secondary accounts rather than direct Gmail API `userId=<secondary>` calls, which can fail with delegation errors.

### Gmail

```bash
# Search (returns JSON array with id, from, subject, date, snippet)
$GAPI gmail search "is:unread" --max 10
$GAPI gmail search "from:boss@company.com newer_than:1d"
$GAPI gmail search "has:attachment filename:pdf newer_than:7d"

# For complex Gmail queries with spaces, parentheses, or quoted labels, shell-quote
# the entire query as one argument. If you build commands programmatically, use
# shlex.quote / hermes_tools.shell_quote. Otherwise argparse may split terms like
# label:"Hermes/Date Night" into invalid extra arguments.
$GAPI gmail search 'label:"Hermes/Date Night" newer_than:30d' --max 10

# Read full message (returns JSON with body text)
$GAPI gmail get MESSAGE_ID

# If `gmail get` returns an empty body for a rich multipart email, fall back to
# raw Gmail API part walking. Some Outlook/marketing-style replies expose the
# useful content only in nested text/plain or text/html MIME parts.
python3 - <<'PY'
import base64, re, html
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
MESSAGE_ID = 'MESSAGE_ID_HERE'
creds = Credentials.from_authorized_user_file(str(Path.home()/'.hermes/google_token.json'))
svc = build('gmail','v1',credentials=creds,cache_discovery=False)
msg = svc.users().messages().get(userId='me', id=MESSAGE_ID, format='full').execute()
def walk(part, out):
    data = (part.get('body') or {}).get('data')
    if data:
        s = base64.urlsafe_b64decode(data + '===').decode('utf-8','replace')
        if part.get('mimeType') == 'text/html':
            s = re.sub(r'<br\s*/?>','\n',s,flags=re.I)
            s = re.sub(r'</p>|</div>|</li>','\n',s,flags=re.I)
            s = html.unescape(re.sub(r'<[^>]+>',' ',s))
        out.append((part.get('mimeType'), re.sub(r'\s+',' ',s).strip()))
    for p in part.get('parts') or []:
        walk(p, out)
parts=[]; walk(msg['payload'], parts)
for mime, text in parts:
    print('\n---', mime, '---')
    print(text[:10000])
PY

# Send
$GAPI gmail send --to user@example.com --subject "Hello" --body "Message text"
$GAPI gmail send --to user@example.com --subject "Report" --body "<h1>Q4</h1><p>Details...</p>" --html
$GAPI gmail send --to user@example.com --subject "Hello" --from '"Research Agent" <user@example.com>' --body "Message text"

# Reply (automatically threads and sets In-Reply-To)
$GAPI gmail reply MESSAGE_ID --body "Thanks, that works for me."
$GAPI gmail reply MESSAGE_ID --from '"Support Bot" <user@example.com>' --body "Thanks"

# Labels
$GAPI gmail labels
$GAPI gmail modify MESSAGE_ID --add-labels LABEL_ID
$GAPI gmail modify MESSAGE_ID --remove-labels UNREAD

#### Pitfall: --add-labels requires label IDs, not names

`google_api.py --add-labels` expects Gmail label IDs (e.g., `Label_60`), not human-readable names (e.g., `Hermes/Date Night`). Using names produces `Invalid label: Hermes/Date Night` errors. Always resolve names to IDs first: run `$GAPI gmail labels` and grep for the name.

System labels like `UNREAD`, `INBOX`, `SPAM`, `TRASH` work by name in both `--add-labels` and `--remove-labels`. Only user-created labels require their opaque ID.

#### Pitfall: `--remove-labels` accepts only ONE label per call

The argparse-based `google_api.py` parses `--remove-labels` as a single string argument — space-separated labels like `--remove-labels UNREAD INBOX` will fail with `unrecognized arguments: INBOX`. To remove multiple labels, issue separate calls:

```bash
$GAPI gmail modify MESSAGE_ID --remove-labels UNREAD
$GAPI gmail modify MESSAGE_ID --remove-labels INBOX
```

#### Gmail cleanup partial-success triage

If a cleanup/archive job mutates one or more messages and then exits non-zero, treat it as a **partial success**, not a clean failure. Do not blindly rerun the whole batch.

Triage sequence:

1. Preserve and report the successfully mutated message IDs from stdout/stderr or the audit file.
2. Re-query the original Gmail search across both primary and alumni accounts.
3. Exclude already-mutated message IDs or threads from any retry set.
4. Inspect the first failing API error before retrying; common causes are invalid label IDs, `--remove-labels` argument splitting, expired auth, or a single message disappearing between search and modify.
5. Retry only the remaining narrow set after fixing the cause.
6. Verify final counts per account and explicitly say `partial-success recovered` when applicable.

For scheduled Gmail cleanup jobs, prefer writing a per-message audit JSON/CSV before each mutation so a later cron notification can distinguish `mutated`, `skipped`, and `failed` without guessing from final labels alone.

When a multi-account Gmail cleanup cron fails but prints a mostly normal report, first check whether exactly one account failed while the other completed. For Shan, a common durable pattern is: primary `~/.hermes/google_token.json` is still valid, but alumni `~/.hermes/google_tokens/shandutt_alumni_stanford_edu.json` returns `RefreshError/invalid_grant: Token has been expired or revoked`. Verify with:

```bash
python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --check
python ~/.hermes/skills/productivity/google-workspace/scripts/setup.py --account shandutt@alumni.stanford.edu --check
```

If that is the cause, explain clearly: “primary cleanup ran; alumni account could not be checked until OAuth is reauthorized.” Do not imply messages were deleted or broadly failed. Report the counts from the successful account and the exact failing account/error.

Scheduled cleanup chat output should include the first account/error inline, not just “Needs attention; see audit.” The HTML audit can carry full details, but Telegram should show enough to diagnose revoked OAuth without opening the artifact.

#### Pre-flight: Python dependencies

`google_api.py` requires `google-api-python-client`, `google-auth-httplib2`, and `google-auth-oauthlib`. Before first Gmail/Calendar/Drive call, verify the import works:

```bash
python3 -c "from googleapiclient.discovery import build; print('OK')" 2>&1 || pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib
```

### Creating labels and filters (direct Gmail API)

`google_api.py` does not support label/filter creation. Use the Gmail API directly with the Hermes OAuth token:

**Create a label:**

```bash
python3 - <<'PY'
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file(str(Path.home()/'.hermes/google_token.json'))
gmail = build('gmail','v1',credentials=creds,cache_discovery=False)
label = gmail.users().labels().create(userId='me', body={
    'name': 'Reading/Substack/newsletter-name',
    'labelListVisibility': 'labelShow',
    'messageListVisibility': 'show',
}).execute()
print(f"Created: {label['id']} = {label['name']}")
PY
```

Do not set a `color` field unless you know a valid Gmail palette color (`#e3e3e3` and other arbitrary hex values are NOT on the allowed palette and will fail with `Label color #XXXXXX is not on the allowed color palette`).

**Create a filter:**

```bash
python3 - <<'PY'
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file(str(Path.home()/'.hermes/google_token.json'))
gmail = build('gmail','v1',credentials=creds,cache_discovery=False)
f = gmail.users().settings().filters().create(userId='me', body={
    'criteria': {'from': 'sender@substack.com', 'query': 'list:(<sender.substack.com>)'},
    'action': {'addLabelIds': ['Label_93'], 'removeLabelIds': ['INBOX', 'UNREAD']},
}).execute()
print(f"Filter created: {f['id']}")
PY
```

Filter creation requires the `gmail.settings.basic` OAuth scope. If you get a 403 permission error, the token was authorized without this scope and needs re-authorization.

#### Pitfall: label color palette is restricted

Gmail only accepts colors from its approved palette. Do not pass arbitrary hex values like `#e3e3e3` or `#ff0000` — they will fail. If you need a color, either omit `color` entirely, or find the exact hex values from Google's documented label palette. In practice, omit color for new labels.
```

#### Shan Gmail label convention for dining reservations

For restaurant reservation/vendor mail, prefer household/admin labels over Hermes labels. OpenTable-related mail should live under `S&P/Dining/OpenTable`, not `Hermes/...`, because it is durable household logistics rather than agent intake. When creating a filter for future OpenTable mail, label it narrowly and do **not** auto-archive by default; active confirmations and support replies should remain visible in Inbox unless Shan explicitly asks to archive them.

### Calendar: family holds, confirmations, and cross-calendar invites

For Shan's family calendar logistics, first inspect available calendar IDs via Calendar API `calendarList().list()` if the calendar name matters. The `Family` calendar is commonly the right target for family weddings, household holds, and purchased date-night/family events.

When Shan asks for logistics from scheduled appointment emails:
- Search both Gmail accounts for the vendor name and scheduler reminders, then read the latest reminder plus the original appointment confirmation. Scheduler reminders often contain the operational details missing from the calendar event.
- Cross-check all calendars, not just the primary calendar, when the event is on a shared/family calendar. For appointment logistics, inspect event title, start/end, location, description, and any companion transit/travel blocks.
- Summarize in operational buckets: appointment time, location, calendar/travel blocks, arrival/access, contact method, parking/transit, rescheduling/cancellation fees, prep/attire, and what to expect after.
- For access-code workflows, explicitly say whether the promised code email has arrived yet; do not infer the code from older confirmations.

When Shan says he bought tickets or made a reservation and asks to add/update the event to calendar:
- Search Gmail for the confirmation first and treat it as authoritative, even if prior cart research had different seats, price, party size, or timing. Summarize any differences briefly.
- For ticket confirmations with attached PDFs/QR codes, do not rely on `gmail get` body text alone. Use direct Gmail API MIME part walking to list/download attachments, upload the ticket PDF to Drive, then attach that Drive file to the Calendar event with `supportsAttachments=True` and an `attachments` entry. Prefer a shared household folder such as Chalo when Parul/family access matters, and share the Drive file with Parul if inheritance is uncertain.
- Add the venue's precise street address in `location`.
- Include confirmation numbers, venue phone, public links, and concise guest-safe recommendations in the description when useful.
- If Shan asks to add a short memory/context note about an artist/event, put a concise human-readable note in the event description, not persistent memory, unless he explicitly asks to remember the artist long-term.
- Before adding external attendees, remove internal planning notes from the invite description (e.g. "if Parul joins," "booking still needs confirmation," source/debug notes, or private workflow status). Shared calendar descriptions should contain only details Shan would be comfortable sending to attendees.
- For OpenTable-specific reservation/account-linking issues, see `references/opentable-reservation-account-linking.md`.
- If he asks for travel time from Oakland, create either a separate travel block before the event or include the travel buffer in the description. Use maps/routing for driving distance/time, and web/search or transit references for BART/transit estimates. For SF events, distinguish no-traffic drive estimates from realistic Bay Bridge/SF traffic + parking buffers.
- Include practical departure guidance in the event description.
- Verify after mutation by reading the event back and reporting calendar, local time, location, attendees, and travel block/details.
- If you first created an event on Shan's primary calendar, then he asks to add the same event to the Family calendar and invite his Stripe/work email, treat that as a **move/canonicalization request**, not a request for two duplicate holds. Create or update the Family event, preserve the event/ticket links and guest-safe details, invite the work email, then remove the duplicate primary-calendar copy unless Shan explicitly says he wants both. Verify both sides: primary has zero matching duplicates and Family has exactly one matching event with the attendee.

When Shan asks for a full-day hold because he is officiating / traveling / otherwise committed:
- Create an all-day event with `start.date` and `end.date` as the following day.
- Set `visibility: private` when requested.
- Leave/default it as busy (`transparency` omitted or `opaque`).
- Include precise venue location after live lookup when the user gives only a venue nickname.
- If he asks to invite his Stripe calendar, use the existing Stripe address discovered from calendar events (`shandutta@stripe.com`) unless he provides a different one.
- Verify after mutation by reading the event back and reporting calendar, date, location, privacy, busy status, and attendees.

Pitfall: avoid running inline shell/Python commands that contain event titles with raw `&` through a guarded terminal shell. Use a temp Python script via `execute_code`, quote carefully, or spell out `and` in event summaries.

### Calendar

```bash
# List events (defaults to next 7 days)
$GAPI calendar list
$GAPI calendar list --start 2026-03-01T00:00:00Z --end 2026-03-07T23:59:59Z

# Create event (ISO 8601 with timezone required)
$GAPI calendar create --summary "Team Standup" --start 2026-03-01T10:00:00-06:00 --end 2026-03-01T10:30:00-06:00
$GAPI calendar create --summary "Lunch" --start 2026-03-01T12:00:00Z --end 2026-03-01T13:00:00Z --location "Cafe"
$GAPI calendar create --summary "Review" --start 2026-03-01T14:00:00Z --end 2026-03-01T15:00:00Z --attendees "alice@co.com,bob@co.com"

# Delete event
$GAPI calendar delete EVENT_ID
```

#### Calendar updates / free-busy status

The `google_api.py` wrapper currently supports calendar list/create/delete, not update. For narrow updates, use the Calendar API directly with Hermes OAuth and verify after mutation. To mark an event as **Free** in Google Calendar, patch `transparency: "transparent"`; busy/default is `opaque` or omitted.

```bash
python3 - <<'PY'
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
creds = Credentials.from_authorized_user_file(str(Path.home() / '.hermes/google_token.json'))
svc = build('calendar', 'v3', credentials=creds, cache_discovery=False)
cal = 'primary'
event_id = 'EVENT_ID_OR_RECURRING_MASTER_ID'
updated = svc.events().patch(calendarId=cal, eventId=event_id, body={'transparency': 'transparent'}).execute()
print(updated['id'], updated.get('summary'), updated.get('transparency'))
PY
```

For recurring events, inspect an instance's `recurringEventId`; patch the master if Shan wants the whole series marked free. Shan's meal-prep/Luchi socialization blocks are soft household holds and should generally be transparent/free rather than hard busy conflicts.

### Drive Upload

`google_api.py` does not have a file upload command. Use the Drive API directly via the pattern in `references/drive-file-upload.md` — it covers uploading files, setting parents, and discovering target folders. For Shan's Chalo folder (shared with Parul), the folder ID is `1RtlWDSOiDnop_haeGTJZxv5fkFq_eaJl`; the "2026 Home Purchase" subfolder inside Chalo is `15SBj0n5fcyF9pGGtMbyr9Y_T5s8uAdgN`.

### Drive

```bash
$GAPI drive search "quarterly report" --max 10
$GAPI drive search "mimeType='application/pdf'" --raw-query --max 5

# Download by file ID when a shared Drive URL must be pulled locally.
# Useful when public curl/gdown returns a Google Accounts HTML page instead of the file.
# IMPORTANT: For files > ~100MB, `curl -L "https://drive.google.com/uc?export=download&id=..."` 
# returns a virus-scan warning page (~900KB HTML), not the actual file. Always use the 
# authenticated download_drive_file.py helper for large files — it uses the Drive API directly.
python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/download_drive_file.py FILE_ID ~/Downloads/file.bin
```

The helper prints Drive metadata before download and writes the file with the authenticated Hermes Google OAuth token.

### Contacts

For a direct shared/private Drive file URL where you already have the file ID and need the binary contents, use the packaged helper. This is useful when public `curl`/`uc?export=download` returns a Google Accounts HTML page but Hermes' OAuth token has access:

```bash
python ${HERMES_HOME:-$HOME/.hermes}/skills/productivity/google-workspace/scripts/download_drive_file.py FILE_ID /path/to/output.ext
```

### Contacts

```bash
$GAPI contacts list --max 20
```

### Sheets

```bash
# Read
$GAPI sheets get SHEET_ID "Sheet1!A1:D10"

# Write
$GAPI sheets update SHEET_ID "Sheet1!A1:B2" --values '[["Name","Score"],["Alice","95"]]'

# Append rows
$GAPI sheets append SHEET_ID "Sheet1!A:C" --values '[["new","row","data"]]'
```

#### Sheets financial models: formulas, not hard-coded outputs

When Shan asks for a Google Sheets model or scenario tab, especially around compensation, home purchase, tax, or affordability, load `references/sheets-financial-modeling.md`. Default to a formula-driven tab that references source assumptions (`Inputs!...`) rather than hard-coded outputs. If Shan says an assumption applies "in all tabs," update the source input cell first, then rebuild/refresh derived analysis tabs. Before reporting completion, verify with `valueRenderOption=FORMULA` that formulas are present and with `valueRenderOption=FORMATTED_VALUE` that the used range has no `#ERROR!`, `#NAME?`, `#VALUE!`, etc.

### Docs

```bash
$GAPI docs get DOC_ID
```

#### Reading Google Doc comments

`google_api.py docs get` returns the document body but not comments. When Shan asks to read, answer, triage, or resolve comments on a Google Doc, use the Drive API comments endpoint with the document/file ID. Include quoted text, author, resolved state, and replies so answers can be tied back to the exact highlighted passage.

```bash
python3 - <<'PY'
from pathlib import Path
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import json
FILE_ID = 'DOC_OR_DRIVE_FILE_ID'
creds = Credentials.from_authorized_user_file(str(Path.home()/'.hermes/google_token.json'))
drive = build('drive','v3',credentials=creds,cache_discovery=False)
comments=[]; page=None
while True:
    resp = drive.comments().list(
        fileId=FILE_ID,
        fields='nextPageToken, comments(id,content,quotedFileContent,anchor,createdTime,modifiedTime,resolved,author(displayName,emailAddress),replies(id,content,createdTime,modifiedTime,deleted,author(displayName,emailAddress),action))',
        includeDeleted=False,
        pageSize=100,
        pageToken=page,
    ).execute()
    comments.extend(resp.get('comments', []))
    page = resp.get('nextPageToken')
    if not page:
        break
print(json.dumps(comments, indent=2))
PY
```

For read-only asks, answer in chat first. Do not reply to or resolve document comments unless Shan explicitly asks you to mutate the doc/comment thread.

## Output Format

All commands return JSON. Parse with `jq` or read directly. Key fields:

- **Gmail search**: `[{id, threadId, from, to, subject, date, snippet, labels}]`
- **Gmail get**: `{id, threadId, from, to, subject, date, labels, body}`
- **Gmail send/reply**: `{status: "sent", id, threadId}`
- **Calendar list**: `[{id, summary, start, end, location, description, htmlLink}]`; in current wrapper output, `start` and `end` are flat strings (`YYYY-MM-DD` or ISO datetime), not nested Google API objects. Parse defensively and do not assume `event['start']['dateTime']`.
- **Calendar create**: `{status: "created", id, summary, htmlLink}`
- **Drive search**: `[{id, name, mimeType, modifiedTime, webViewLink}]`
- **Contacts list**: `[{name, emails: [...], phones: [...]}]`
- **Sheets get**: `[[cell, cell, ...], ...]`

## Multi-account pitfall: always check BOTH accounts

Shan has two Gmail accounts: primary (`shandutta90@gmail.com`) and alumni (`shandutt@alumni.stanford.edu`). Many senders — StubHub, newsletters, purchase confirmations, LinkedIn, recruiters, event notifications — may route to either account. When Shan asks to clean up inbox noise, archive messages from a specific sender, or set up intake routing for a source, you MUST search BOTH accounts. Do not declare a sender "clean" after checking only the primary account. The user has corrected this multiple times.

This applies to: inbox triage, archive/read mutations, label backfills, filter creation, intake pipeline setup, and verification queries.

After cleaning/mutating one account, always run the same query against `--account shandutt@alumni.stanford.edu` before reporting completion. Count results per account separately and report both.

## Gmail reply pitfall

When replying to a thread, always reply to the latest **incoming** message (from the recipient), never to the user's own sent message. Replying to a sent message makes the email appear from/to the user's own address rather than as a proper threaded reply. To find the right message: search the thread, sort by date descending, pick the most recent message where `from` is NOT the user's own address.

## Rules

1. **Access model:** Shan authorizes full read/write access for Gmail, Calendar, Drive, Docs, and Sheets so Hermes can execute approved workflows, including crons. In ad hoc chat, show the exact email/event/document mutation before executing unless Shan explicitly says to proceed. In scheduled/named workflows, mutations are allowed when the cron/workflow prompt narrowly defines them.
2. **Check auth before first use** — run `setup.py --check`. If it fails, guide the user through setup. For secondary Google accounts, use `setup.py --account <email> --auth-url` / `--auth-code` and `google_api.py --account <email> ...`.
3. **Use the Gmail search syntax reference** for complex queries — load it with `skill_view("google-workspace", file_path="references/gmail-search-syntax.md")`.
4. **Calendar times must include timezone** — always use ISO 8601 with offset (e.g., `2026-03-01T10:00:00-06:00`) or UTC (`Z`).
5. **Respect rate limits** — avoid rapid-fire sequential API calls. Batch reads when possible.
6. **For read-only migration/dry-run reports, do not mark Gmail read, archive, label, or mutate messages unless the workflow contract explicitly says to.** Prefer search/list metadata plus stable message IDs first. Use Hermes-native `google_api.py` / `google_workspace_helpers.py`; do not add new `gog` call sites.
7. **For approved newsletter/intake workflows, consumed newsletter messages should be archived and marked read.** Shan explicitly considers this a crucial part of intake hygiene. Narrow mutation only: remove `INBOX,UNREAD` from consumed newsletter messages. Do not send, delete, trash, or broadly mutate Gmail. For user-confirmed order/confirmation checks (e.g. "I just ordered it, look in Gmail"), read the specific confirmation email, summarize key details, then archive/mark read only that confirmation if Shan says it is okay; search both primary and alumni accounts because purchase confirmations may route to either.
8. **For Calendar-driven deterministic syncs, normalize event times to the user's local timezone before scoring or schedule decisions.** UTC event times can misclassify weekend/late-evening behavior if scored directly. When comparing an external scheduler link against Shan's calendar, actually open the scheduler page if browser tools are available, extract visible slots, then check Shan's calendar for the same date range plus any recurring soft blocks. Rank options by conflicts and practical fit; do not book or submit forms without explicit approval. Once Shan explicitly approves a slot, use the same email/account from the source thread, submit only the narrow booking form, then verify with both the browser confirmation and the confirmation email. For Acuity/Squarespace scheduler quirks and the Browserbase confirm-click fallback, see `references/external-scheduler-booking.md`.
9. **Do not recommend service accounts for personal Gmail/Calendar/Drive access.** Use OAuth client ID → Desktop app for user-owned Google data. Service accounts are only appropriate for backend/workload use, domain-wide delegation in Workspace, or individual Drive files/folders explicitly shared with the service account. If Shan is on Google Cloud Credentials, tell him to choose **OAuth client ID**, not API key or Service account. If Shan says he has Google service/admin keys, check existing credentials first (current visible thread/compaction, session memory, GBrain, raw logs, current env/disk, and 1Password metadata without printing secrets) instead of defaulting to a headless Cloud Console flow or only searching files. If Shan reports that the `localhost:1`/mobile OAuth flow spins or already failed, do **not** resend the same Desktop OAuth URL; switch to the HTTPS callback/manual Web OAuth-client path in `references/cloudflare-oauth-callback.md`. Use a temporary Cloudflare tunnel plus a Web application OAuth client whose authorized redirect URI exactly matches the generated `https://*.trycloudflare.com/google/oauth/callback` URL; after successful token verification, kill the callback server and tunnel. Remember that regular Google OAuth clients and redirect URIs are not generally creatable/editable via service-account/admin APIs; the IAP programmatic OAuth-client API is IAP-only and not a Gmail callback workaround. See also `references/google-oauth-client-programmatic-limits.md`.
10. **Drive organization audits:** When Shan asks to review, clean up, reorganize, or propose a Google Drive structure, first load `references/drive-organization-audits.md` in addition to `references/drive-inventory.md`. Default to read-only metadata, exclude Chalo unless explicitly in scope, produce a proposal before mutations, use Shan's paired `X & Y` folder labels, and deliver artifacts via Telegram media or Drive rather than only local devbox paths.
10a. **Drive dedupe/cleanup:** When Shan asks to deduplicate, delete duplicate candidates, process Drive Trash, approve duplicate groups, or rename Drive files after cleanup, also load `references/drive-dedupe-cleanup.md`. Use exact-binary md5+size for auto-cleanup, move to Google Drive Trash rather than permanent delete, recover from partial execution CSVs after timeouts/kills, and publish long review lists as searchable card layouts rather than cramped wide tables.
10b. **Drive tax/payroll/equity analysis:** When Shan asks about taxes, marginal rates, paycheck run rate, W-2s, RSUs, equity vests, withholding, or safe harbor and the data may be in Google Drive, also load `references/drive-tax-payroll-equity-analysis.md` and `ocr-and-documents`. Search Drive extensively before relying on memory or older planning sheets; recurse through `02 Taxes & Finance`, payroll, investments, and older tax folders; download/export key docs read-only; compute rates with Python; then answer with bottom-line marginal rates, evidence docs, assumptions, and gaps.
11. **Gmail label harmonization:** When Shan asks to clean, harmonize, rename, de-duplicate, or color Gmail labels/folders across accounts, first load `references/gmail-label-harmonization.md`. Do read-only discovery across both accounts: user labels with message/thread counts, Gmail filters with label IDs resolved to names, and local Hermes script/skill references. Prefer purpose-based canonical namespaces (`Hermes/...`, `Reading/...`, `S&P/...`, `Reference/...`) over mirroring empty labels across accounts. For merges, apply the new label to messages first, update filters/scripts/crons, verify with live searches and impacted dry-runs, then delete stale labels. Quote labels with spaces/slashes in Gmail search, e.g. `label:"Hermes/Date Night"`. Gmail filter management requires `https://www.googleapis.com/auth/gmail.settings.basic`; if missing, reauthorize with that narrow scope before deleting/updating filters. For label colors, avoid rainbow/source-by-source palettes: use Gmail-approved colors, set parent namespaces to stronger colors, and make children calm lighter variations of their parent; all siblings may share the same child color.
12. **Gmail inbox triage:** When Shan asks to triage/clean an inbox, unsubscribe from senders, or stop recurring inbox noise, first load `references/gmail-inbox-triage.md` plus `references/gmail-search-syntax.md`. Act narrowly: archive and mark read obvious low-value senders he named, create skip-inbox filters for recurring offenders, attempt standards-based unsubscribe when available, and leave personal/finance/security/package/career/home-buying messages for review unless explicitly cleared.
13. **DMV / REAL ID notices:** When Shan asks about CA DMV REAL ID cancellation/update or asks you to handle DMV appointment booking, load `references/dmv-real-id-workflow.md`. Search both primary and alumni Gmail before concluding no notice exists. If Shan explicitly authorizes using Drive for identity docs, search Drive for DL scans, but treat DL number/DOB as sensitive. DMV appointment confirmation may stall on invisible reCAPTCHA; if it does, report the exact office/date/time and direct URL for Shan to finish manually. For LinkedIn routing across Shan's primary and alumni Gmail accounts, follow the detailed account-specific rules in `references/gmail-inbox-triage.md`; do not create broad `from:linkedin.com` skip-inbox filters for alumni because recruiter/InMail/login/security messages must remain visible there if they arrive.
14. **Gmail cleanup cron auditability:** When a scheduled Gmail cleanup/archive job mutates messages and Shan asks for a board/Telegram/HTML report showing what went where, load `references/gmail-lifecycle-cleanup-audit-reports.md`. Default to compact cron output plus a served mobile-friendly HTML artifact with exact message IDs, thread IDs, sender/subject/date/snippet, target label, and safety-skip examples. If per-run details were not previously captured, say that clearly and provide a current label audit as fallback; do not present it as a perfect replay.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `NOT_AUTHENTICATED` | Run setup Steps 2-5 above |
| `REFRESH_FAILED` | Token revoked or expired — redo Steps 3-5. If the user asked you to read a specific email, do **not** infer its contents or absence from a failed token; generate a fresh `setup.py --auth-url`, ask for the redirected URL/code, and clearly label any interim answer as provisional/not based on reading Gmail. For crons, also add a pre-flight token health gate (`references/cron-auth-health-check.md`) to avoid spending tokens on doomed runs. |
| `HttpError 403: Insufficient Permission` | Missing API scope — `$GSETUP --revoke` then redo Steps 3-5 |
| Contacts list 403 / People API scope missing | Do not block the task. Fall back to Gmail search headers for likely email addresses, especially for recent threads (`gmail search "name newer_than:3650d"`), then confirm recipients before sending. Reauthorize with People/Contacts scope only if contact traversal is truly required. |
| `HttpError 403: Access Not Configured` | API not enabled — user needs to enable it in Google Cloud Console |
| `ModuleNotFoundError` | Run `pip install google-api-python-client google-auth-httplib2 google-auth-oauthlib` |
| Advanced Protection blocks auth | Workspace admin must allowlist the OAuth client ID |
| `Invalid label: X` on `--add-labels` | Using label name instead of ID. Run `$GAPI gmail labels`, find the opaque ID (e.g. `Label_60`), use that. |
| `Label color #XXXXXX is not on the allowed color palette` | Gmail only accepts specific palette colors. Omit `color` when creating labels, or use a documented palette value. |
| `HttpError 403` on `settings().filters()` | Missing `gmail.settings.basic` OAuth scope. Re-authorize with this scope. |

## Revoking Access

```bash
$GSETUP --revoke
```
