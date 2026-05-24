# Mobile OAuth reauth for secondary Google accounts

Use when Shan is on his phone and a Google Workspace/Gmail OAuth refresh token has expired/revoked, especially for a secondary account such as `shandutt@alumni.stanford.edu`.

## Key lesson

The agent is on the devbox, but Google consent still requires Shan's signed-in browser session. Do not over-explain desktop/devbox mechanics when he is handling the approval from iPhone. Give phone-first steps and keep the URL path narrow.

## Recommended sequence

0. Before asking Shan to do more Console/OAuth work, load `onepassword-headless-auth` and check existing local metadata + 1Password item titles for Google OAuth Web/Desktop clients, service-account JSONs, and account token items. If prior context says a service/admin key or Web OAuth client exists, verify that path first instead of repeating a failed browser/localhost flow.
1. Verify which token failed with `setup.py --account <email> --check`. If `~/.hermes/google_oauth_op_refs.json` maps that token path to `op://...`, the local file is only a runtime cache: `google_oauth_store.py` can re-materialize it from 1Password if deleted, and refresh writes should update 1Password.
2. Generate the normal `--auth-url` for that account.
3. If Shan reports the Google consent screen loops on iPhone, or sends a screenshot showing the same Google consent/checklist screen after a failed attempt:
   - Treat this as a correction/frustration signal and **stop the old path immediately**.
   - Do **not** resend the same Desktop OAuth URL or repeat `localhost:1` copy-back instructions.
   - Re-anchor by checking visible context/session logs/this reference for the agreed fallback, then say plainly that the previous repetition was wrong.
   - If the failure appears scope-related before redirect, generate a narrower OAuth URL scoped only to the operation needed.
   - For Gmail cleanup/archive/label workflows, `https://www.googleapis.com/auth/gmail.modify` is the minimum useful scope.
   - Add `gmail.settings.basic` only if the workflow needs filter/settings management.
   - If the failure is the mobile localhost handoff or the user explicitly says the point was to find a better alternative, skip narrower Desktop URLs and move directly to the HTTPS callback/Web OAuth-client fallback below.
4. Phone-first instruction text:
   - Open in Safari/Chrome, not Telegram's in-app browser.
   - Confirm the shown account is the intended secondary account.
   - Leave permission checkboxes checked, scroll to the bottom, tap Continue.
   - A broken `http://localhost:1/?code=...` page is success; copy the full address bar URL back to Hermes.
5. Once Shan pastes the callback URL, exchange it with `setup.py --account <email> --auth-code '<full URL>'`, then re-run `--check`.

## Generating a narrow URL manually

`setup.py --auth-url` currently requests the full `SCOPES` list. If mobile consent loops, generate a narrow PKCE URL and write the pending session to the account-specific pending file so the existing `--auth-code` path still works:

```python
import sys, json
sys.path.insert(0, '/home/shan/.hermes/skills/productivity/google-workspace/scripts')
import setup
setup.configure_account('shandutt@alumni.stanford.edu')
from google_auth_oauthlib.flow import Flow
scopes = ['https://www.googleapis.com/auth/gmail.modify']
flow = Flow.from_client_secrets_file(
    str(setup.CLIENT_SECRET_PATH),
    scopes=scopes,
    redirect_uri=setup.REDIRECT_URI,
    autogenerate_code_verifier=True,
)
auth_url, state = flow.authorization_url(access_type='offline', prompt='consent')
setup.PENDING_AUTH_PATH.write_text(json.dumps({
    'state': state,
    'code_verifier': flow.code_verifier,
    'redirect_uri': setup.REDIRECT_URI,
}, indent=2))
print(auth_url)
```

## Why the link appears to spin

Google's docs still support loopback redirects for desktop apps, but explicitly say loopback IP redirects are deprecated for mobile app client types and can be awkward on phones. In Shan's flow, `http://localhost:1/...` points at the iPhone, where no listener exists. A blank/spinning/broken localhost page after tapping Continue is therefore usually success, not failure. The useful artifact is the address bar URL containing `code=`.

If the Google consent screen itself spins before reaching a `localhost` URL:
- open the link in Safari or Chrome, not Telegram's in-app browser; Google documents embedded-user-agent OAuth problems such as `disallowed_useragent`;
- include `login_hint=<secondary account>` to reduce account-switch confusion;
- do not assume narrower scopes will fix it if Shan already tried that; the failure may be the localhost/mobile redirect handoff itself;
- try desktop if iOS keeps trapping the redirect.

## Better fallback hierarchy

If repeated iPhone localhost links spin out, stop regenerating similar links. Prefer one of these instead:

1. Desktop browser on Mac/PC: same localhost redirect pattern, but easier to copy the `code=` URL when it fails to connect.
2. Create a temporary Google **TVs and Limited Input devices** OAuth client and use device-code flow. The existing Desktop client returns `invalid_client: Invalid client type` at `https://oauth2.googleapis.com/device/code`.
3. Create a Google **Web application** OAuth client with a real HTTPS callback URL, such as a temporary Cloudflare Tunnel endpoint, then exchange the server-side callback. This avoids mobile localhost entirely but requires a new web OAuth client/redirect URI.
   - Start a loopback callback server that writes only one captured callback JSON under `~/.hermes/oauth-callback/` and enforces a high-entropy `state`.
   - Expose it with a short-lived Cloudflare quick tunnel, e.g. `cloudflared tunnel --url http://127.0.0.1:8769 --no-autoupdate`.
   - Register the exact HTTPS redirect URI, e.g. `https://<trycloudflare-host>/google/oauth/callback`, on the Web OAuth client. Google does not expose a normal public API for creating/editing Google Auth Platform OAuth client redirect URIs; if headless Google Console sign-in is blocked by “This browser or app may not be secure,” use Shan's real browser or a live-browser handoff for this one console step.
   - For Shan's normal Hermes Workspace account setup, generate the authorization URL with the full approved Workspace scope set: Gmail read/send/modify/settings, Calendar, Drive, Sheets, and Docs. Use a narrow `gmail.modify` URL only as a deliberate troubleshooting step, and do not let a narrow-scope helper consume a full-scope one-time code.
   - Generate an authorization URL with that Web client id/secret, `redirect_uri` set exactly to the Cloudflare URL registered on the Web client, `access_type=offline`, `prompt=consent`, and high-entropy `state`.
   - After approval, exchange the captured `code` with the same full scope set used in the auth URL, verify `gmail.users().getProfile(userId='me').emailAddress` equals the intended secondary account, save the token under `~/.hermes/google_tokens/<account>.json`, chmod `600`, then kill the callback server and tunnel.
   - Generate an authorization URL with that Web client id/secret, `redirect_uri` set to the Cloudflare URL, `access_type=offline`, `prompt=consent`, high-entropy `state`, and the scope set Shan actually wants. Do not silently narrow to Gmail-only if Shan asked for full Workspace access; use the normal full set: Gmail read/send/modify/settings, Calendar, Drive, Sheets, and Docs.
   - After approval, exchange the captured `code` immediately. OAuth codes are one-time-use: if an exchange helper fails after contacting Google's token endpoint, that code is consumed and Shan must approve again.
   - Verify `gmail.users().getProfile(userId='me').emailAddress` equals the intended secondary account, save the token under `~/.hermes/google_tokens/<account>.json`, chmod `600`, then kill the callback server and tunnel.
   - Do **not** keep the Cloudflare tunnel/server persistent for OAuth. Keep it single-purpose and tear it down immediately after token verification. If a quick tunnel expires with Cloudflare 1033, start a fresh tunnel and update the Web OAuth client's redirect URI before sending a new auth link.
4. OAuth Playground can help only with a Web application client and `https://developers.google.com/oauthplayground` as an authorized redirect URI; it is not a drop-in fix for the existing Desktop client.

## HTTPS callback exchange pitfalls

- Keep the requested scopes in the exchange helper synchronized with the auth URL. A helper hardcoded to `gmail.modify` can reject a valid full-Workspace callback as a scope-change warning and consume the one-time code before saving the token.
- If changing from narrow to full scopes mid-flow, clear the stale `callback.json`, regenerate the full-scope URL, and exchange with the full scope list.
- Watch the callback file/log before asking Shan to retry. A direct visit to `/google/oauth/callback` without query parameters is only a probe/page load; a successful OAuth redirect has matching `state` and `code=`.
- For phone guidance, keep instructions short and operational: “update this redirect URI, then open this auth link.” Avoid re-explaining OAuth mechanics while Shan is actively clicking through Console.

## Device-code caveat

Google's device-code flow is attractive for phone-first reauth, but it returns `invalid_client: Invalid client type` for the current Desktop OAuth client. Do not present device code as available unless a **TVs and Limited Input devices** client has been created first. Device flow also has a limited allowed-scope set, so verify `gmail.modify` works before making it the standard path.

## Tone pitfall

If Shan says "Remember I'm on my phone" or "And you're on the devbox," acknowledge the constraint directly. The useful answer is the handoff boundary: Hermes can generate/exchange/verify on the devbox, but Shan must approve Google consent in his signed-in mobile browser.