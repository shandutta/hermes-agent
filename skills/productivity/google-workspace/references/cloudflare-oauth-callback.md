# Cloudflare HTTPS callback for Google OAuth on headless/mobile flows

Use this when Shan is authorizing Google Workspace access from Telegram/iPhone and the Desktop-app `localhost` redirect is spinning, broken, or has already produced a consumed/expired code. This is a callback technique, not a standing service: keep the local server and Cloudflare tunnel temporary and kill both after token verification.

## When to use

- Mobile browser cannot complete or copy a `localhost` redirect reliably.
- A pasted code fails with `invalid_grant` because the one-time code was already consumed, expired, or exchanged with mismatched scopes.
- A Web application OAuth client exists or Shan can create/edit one in Google Cloud Console.
- You need full Workspace scopes, not a narrow Gmail-only fallback.

Do **not** claim a Google service account can directly access personal Gmail/Calendar/Drive. Service accounts can help manage the GCP project/APIs, but user data access still requires OAuth consent for the specific Google account.

## Flow

1. Verify target account and scopes first.
   - For Shan's alumni account, use the account-specific token path under `~/.hermes/google_tokens/`.
   - Ensure `setup.py` and the callback exchange use the same complete scope set; scope mismatch can consume a one-time code and cause `invalid_grant`.

2. Prepare a local HTTPS-capable callback bridge.
   - Run the local callback server on a high port (for example `127.0.0.1:8769`).
   - Start `cloudflared tunnel --url http://127.0.0.1:<port>` only for the duration of auth.
   - Capture the `https://*.trycloudflare.com` URL from cloudflared logs.

3. Configure the Google OAuth **Web application** client.
   - Add the exact redirect URI, e.g. `https://<trycloudflare-host>/google/oauth/callback`.
   - The URI must match exactly, including scheme, host, path, and no trailing slash drift.
   - A Desktop client JSON is not enough for this Cloudflare callback; use a Web application client JSON.

4. Generate and send a fresh authorization URL.
   - Use the Web client JSON and exact Cloudflare redirect URI.
   - Tell Shan to open in Safari/Chrome if Telegram in-app browser is flaky.
   - Ask him to click the fresh link only; older browser tabs/codes may be invalid.

5. Exchange and verify immediately.
   - On callback success, save the refresh token to the account-specific token file.
   - `chmod 600` token files.
   - Verify with smallest read-only calls for each required service, e.g. Gmail profile, Calendar list, Drive about/files.

6. Tear down.
   - Kill the callback server and cloudflared tunnel.
   - Confirm no `google_oauth_https_callback.py` or matching `cloudflared tunnel --url ...` process remains.

## Pitfalls

- `redirect_uri_mismatch`: the authorization URL redirect URI does not exactly match the Web client's configured authorized redirect URI.
- `invalid_grant`: often means the code was already used/expired, or the exchange used a different scope/redirect/client than the authorization request. Generate a fresh URL instead of retrying the old code repeatedly.
- `invalid_client` from Google's device-code endpoint: Google limited-input device flow may reject normal Web/Desktop clients; do not rely on device code for Gmail reauth unless the client type and scopes are known to support it.
- Cloudflare tunnel URLs are short-lived. Do not store them as durable endpoints or leave tunnels running.

## Consent app publishing status

For external Google OAuth apps, Publishing status matters. Google's OAuth docs say a project with OAuth consent screen status `Testing` gets refresh tokens that expire in 7 days unless the only requested scopes are basic profile/email/openid. Shan's Hermes Workspace scopes include Gmail/Calendar/Drive/Sheets/Docs, so moving the app to `In production` is helpful for durable refresh tokens. It does not prevent revocation, password-change invalidation for Gmail scopes, six-month non-use expiry, or refresh-token-count limits.

Do this only for the stable OAuth client/app configuration; short-lived Cloudflare callback URLs still should not become persistent infrastructure.

## 1Password / credential lifecycle

Before asking Shan to recreate Google OAuth credentials, load `onepassword-headless-auth` and check 1Password item titles/metadata for existing Google OAuth Web clients, Desktop clients, service-account JSONs, and Workspace tokens. If Shan uploads or pastes a Google client JSON/service-account JSON/token, promote it to 1Password first, then materialize only a `0600` local runtime copy.

For Shan's current Hermes Workspace setup, `~/.hermes/google_oauth_op_refs.json` maps local token/client-secret cache paths to `op://...` references. The source of truth is 1Password; local files under `~/.hermes` are cache/materialization paths that Google client libraries still need. `google_oauth_store.py` re-materializes missing local files from 1Password and writes refreshed tokens back when a mapped `op://` reference exists.

Do not store short-lived Cloudflare callback URLs as durable secrets. Only OAuth client JSONs and refresh-token JSONs belong in 1Password. Never print client secrets, refresh tokens, service-account private keys, or full callback URLs containing `code=`.

## Security posture

- Never echo client secrets, refresh tokens, or full credential JSON in chat.
- Store OAuth client JSON and tokens with user-only permissions (`0600`; containing directory `0700`).
- Persist important service-account/client secrets/tokens in 1Password or another durable secret store, not only as loose local files.
- Prefer Cloudflare/cloudflared for temporary phone-to-devbox callbacks; do not modify UFW or cloud firewall rules for OAuth unless Shan explicitly asks.
