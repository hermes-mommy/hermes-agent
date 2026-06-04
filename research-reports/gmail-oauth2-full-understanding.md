# Gmail OAuth2 for Personal Account — Full Understanding

**Date**: 2026-06-03  
**Researcher**: THE LIBRARIAN  
**Scope**: Personal Gmail account (NOT Google Workspace), single VPS, single user (Faiz)  
**Downstream impact**: Credential management, token refresh strategy, SOPS encryption approach

---

## 1. Google Cloud Console Project Setup

### Step-by-Step

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project or use existing
3. Enable the **Gmail API**: API Library → search "Gmail API" → Enable
4. Configure **OAuth Consent Screen**: Menu → Google Auth Platform → Branding → Get Started
   - App name: your app name (displayed to you on consent screen)
   - User support email: your own Gmail
   - Audience: **External** (required for @gmail.com accounts — see §2)
   - Contact info: your email
5. Create **OAuth 2.0 Client**: Menu → Google Auth Platform → Clients → Create Client
   - Application type: **Desktop app** (for VPS/headless)
   - Download the JSON file immediately — **client secret is shown only once** (policy change: April 2025)

> **Evidence** ([Google Workspace docs](https://developers.google.com/workspace/guides/configure-oauth-consent)): "In April 2025, we announced that client secrets for OAuth 2.0 clients are only visible and downloadable from the Google Cloud Console at the time of their creation."

### The downloaded JSON looks like:

```json
{
  "installed": {
    "client_id": "XXXX.apps.googleusercontent.com",
    "client_secret": "GOCSPX-XXXX",
    "redirect_uris": ["http://localhost"],
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token"
  }
}
```

> **Evidence** ([Gmail Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)): The quickstart walks through exactly these steps with `credentials.json` as a Desktop app.

---

## 2. OAuth Consent Screen: Internal vs External

| Setting | Who Can Use | Token Lifetime | Verification Required |
|---------|-------------|----------------|----------------------|
| **Internal** | Only users in YOUR Google Workspace domain | Long-lived | No |
| **External — Testing** | Up to 100 test users you manually add | **7 days** | No |
| **External — Production (unverified)** | Any Google user | Long-lived, but unverified warning + 100-user cap | Not yet |
| **External — Production (verified)** | Any Google user | Long-lived, no warnings | Yes (3-5 biz days sensitive, ~6 weeks restricted) |

### For Faiz's Situation (Personal @gmail.com, no Workspace)

- **Internal is NOT available** — it requires a Google Workspace organization
- **External is mandatory** for @gmail.com accounts
- There are two paths:

#### Path A: "Testing" Mode (simpler, short-term)
- Add your Gmail as a test user
- Refresh tokens expire after **7 days**
- You must re-authorize weekly
- Good for prototyping, not production

#### Path B: "Publish to Production" (permanent fix)
- Click **Publish App** in the OAuth consent screen
- If you only request **non-sensitive scopes**, verification is not required — tokens become long-lived immediately
- If you request **sensitive/restricted scopes** (which Gmail scopes ARE), you must either complete verification OR accept the unverified app warning with a 100-user cap

> **Evidence** ([Google OAuth docs](https://developers.google.com/identity/protocols/oauth2)): "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of 'Testing' is issued a refresh token expiring in 7 days."

> **Evidence** ([Manage App Audience](https://support.google.com/cloud/answer/15549945)): "Authorizations by a test user will expire seven days from the time of consent. If your OAuth client requests an offline access type and receives a refresh token, that token will also expire."

### The Critical Insight for Faiz

All Gmail API scopes are **restricted scopes** (read, modify, compose, send — all of them). To use them in Production without the "unverified app" warning, you must submit for verification, which includes:
- Brand verification (2-3 business days)
- Restricted scope verification (~6 weeks)
- **Annual security assessment** by a Google-approved third-party assessor (for apps accessing restricted data from a server)
- A **demo video** showing how scopes are used

**However**: Publishing to Production WITHOUT verification still gives you long-lived refresh tokens — you just get the "unverified app" warning on first consent. Since this is a single-user app (just Faiz), this is the pragmatic path: publish to production, accept the warning once, get permanent tokens.

---

## 3. OAuth2 Scopes for Read + Draft + Send + Labels

All Gmail API scopes from the [official scopes page](https://developers.google.com/workspace/gmail/api/auth/scopes):

| Scope | What It Allows | Category |
|-------|---------------|----------|
| `https://www.googleapis.com/auth/gmail.readonly` | View messages and settings (no modifications) | **Restricted** |
| `https://www.googleapis.com/auth/gmail.send` | Send email only | **Sensitive** |
| `https://www.googleapis.com/auth/gmail.compose` | Manage drafts and send emails | **Restricted** |
| `https://www.googleapis.com/auth/gmail.modify` | Read, compose, send — but NOT permanent delete (trash is allowed) | **Restricted** |
| `https://www.googleapis.com/auth/gmail.labels` | See and edit labels | **Sensitive** |
| `https://www.googleapis.com/auth/gmail.insert` | Insert/import emails into mailbox | **Restricted** |
| `https://mail.google.com/` | **Full access** — read, compose, send, permanent delete | **Restricted** |

### Recommended Scopes for Guinevere (Read + Draft + Send + Labels)

The **minimum set** covering your needs:

```python
SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",   # Read + compose + send + trash (no perm-delete)
    "https://www.googleapis.com/auth/gmail.labels",    # Label management
]
```

- `gmail.modify` covers read, compose, send, and modify (including trash but NOT `messages.delete` which permanently deletes)
- `gmail.labels` covers label CRUD
- If you need **only** send (no reading), swap `gmail.modify` for `gmail.send`
- `gmail.compose` is a subset of `gmail.modify` — if you have modify, you don't need compose separately

**Avoid `https://mail.google.com/`** unless you truly need permanent deletion bypassing Trash. Google will challenge this scope during verification.

> **Evidence** ([Google scopes docs](https://developers.google.com/workspace/gmail/api/auth/scopes)): "Note: Request `https://mail.google.com/` only if your application needs to immediately and permanently delete threads and messages, bypassing the trash. You can perform all other actions using less permissive scopes."

---

## 4. Token Lifecycle

### Access Token
- **Lifetime**: ~1 hour (3600 seconds)
- Refreshed using the refresh token
- The `google-auth` library handles this automatically via `creds.refresh(Request())`

### Refresh Token
- **Purpose**: Obtain new access tokens without user interaction
- Obtained only when `access_type=offline` is set during authorization
- **Expiry conditions** (from [Google OAuth docs](https://developers.google.com/identity/protocols/oauth2)):
  1. **User revokes app access** (via Google Account settings)
  2. **Not used for 6 months** — automatic invalidation
  3. **User changes password** — when Gmail scopes are present
  4. **Exceeded limit of 100 refresh tokens per Google Account per OAuth 2.0 client ID** — oldest is silently invalidated
  5. **App in "Testing" mode** — 7-day expiry (see §2)
  6. **Google Workspace admin sets session control policies** (not applicable for personal accounts)

### Token Refresh Mechanics

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

creds = Credentials.from_authorized_user_file("token.json", SCOPES)

if creds and creds.expired and creds.refresh_token:
    creds.refresh(Request())  # Automatically gets new access token
    # Save the refreshed credentials back
    with open("token.json", "w") as token:
        token.write(creds.to_json())
```

> **Evidence** ([Python quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)): The quickstart code demonstrates exactly this pattern with `creds.refresh(Request())`.

### Revocation

- Via API: `POST https://oauth2.googleapis.com/revoke?token={token}`
- Via user: myaccount.google.com → Security → Third-party apps → Remove access
- **Revocation is final** — no endpoint to revive a revoked token

---

## 5. Refresh Token Gotchas

### ⚠️ Gotcha #1: 7-Day Expiry in Testing Mode
If your Publishing Status is "Testing" and User Type is "External," refresh tokens expire after **7 days**. This is the #1 cause of "my token worked yesterday but not today."

> **Evidence** ([Google OAuth docs](https://developers.google.com/identity/protocols/oauth2)): "A Google Cloud Platform project with an OAuth consent screen configured for an external user type and a publishing status of 'Testing' is issued a refresh token expiring in 7 days."

**Fix**: Publish the app to Production. Even without verification, refresh tokens become long-lived.

### ⚠️ Gotcha #2: 6-Month Inactivity Expiry
A refresh token not used for **6 consecutive months** is automatically invalidated. You must touch the token (by refreshing the access token) at least once every few months.

### ⚠️ Gotcha #3: Password Change Invalidates Gmail-Scoped Tokens
If the user changes their Google password, all refresh tokens with Gmail scopes are revoked. This is specific to Gmail scopes.

### ⚠️ Gotcha #4: Token Limit (100 per user per client)
There's a limit of 100 live refresh tokens per Google Account per OAuth 2.0 client ID. Exceeding it silently invalidates the oldest token. For a single-user app this is unlikely to be an issue, but if you re-authorize frequently (e.g., weekly in Testing mode), you may accumulate tokens.

### ⚠️ Gotcha #5: Client Secret Shown Once
Since April 2025, Google only shows the client secret at creation time. **Download it immediately** and store it in a secret manager (or SOPS-encrypted file).

### ⚠️ Gotcha #6: `invalid_grant` Error
When a refresh token is dead, Google returns `invalid_grant`. Causes: revoked, expired (7 days in Testing), 6-month inactivity, password change, token limit exceeded, or session control. The error is indistinguishable — you must re-authorize.

---

## 6. Service Account vs OAuth2 Consent Flow

### Service Account

| Can It Access Personal Gmail? | How |
|------------------------------|-----|
| **Directly** | ❌ No. Service accounts cannot access Gmail API for personal @gmail.com accounts |
| **With Domain-Wide Delegation** | ❌ No. DWD requires a Google Workspace domain — personal accounts have no domain to delegate |

> **Evidence** ([Google issue #2418](https://github.com/googleapis/google-api-nodejs-client/issues/2418)): "Most Workspace APIs expect to be called as an end-user, not a service account. Gmail and Calendar specifically do not allow it."

> **Evidence** ([SO answer](https://stackoverflow.com/questions/71586987)): "If its a normal standard google gmail account then you will need to authorize the user once. store the refresh token in your system some where and then use that to request an access token as needed."

### OAuth2 Consent Flow

| For Personal Gmail? | How |
|--------------------|-----|
| ✅ **Yes — this is the only path** | User authorizes once via browser → get refresh token → use indefinitely |

### Verdict for Faiz

**Service accounts are not viable for personal Gmail.** You must use the OAuth2 consent flow. The flow is:
1. Run the auth script once (with a browser) to get initial tokens
2. Store the refresh token securely (SOPS-encrypted)
3. Use the refresh token to get new access tokens programmatically
4. The refresh token is long-lived if the app is published to Production

---

## 7. Required Python Libraries

### The Three Core Libraries

| Library | Latest Version (Jun 2026) | Purpose |
|---------|---------------------------|---------|
| `google-api-python-client` | **2.197.0** | Build service objects, call Gmail API |
| `google-auth` | (dependency of the above, ≥1.32.0) | Core auth logic, token refresh |
| `google-auth-oauthlib` | **1.4.0** | OAuth flow helpers (`InstalledAppFlow`) |
| `google-auth-httplib2` | ≥0.2.0 | HTTP transport for auth |

> **Evidence** ([PyPI google-api-python-client](https://pypi.org/project/google-api-python-client/)): Version 2.197.0 as of 2026-05-28.
> **Evidence** ([PyPI google-auth-oauthlib](https://pypi.org/project/google-auth-oauthlib/)): Version 1.4.0 as of 2026-05-07.

### Installation

```bash
pip install google-api-python-client google-auth-oauthlib google-auth-httplib2
```

### What NOT to use

- `oauth2client` — **deprecated**, the old library. Google's own docs still reference it in some pages but it's superseded by `google-auth`.
- `google-auth-oauthlib` requires Python ≥3.10 (as of v1.4.0)

### Import Pattern

```python
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
```

---

## 8. Credential Storage Best Practice (Server-Side, No Browser)

### What to Store

| Artifact | Sensitivity | Storage |
|----------|------------|---------|
| `credentials.json` (client ID + secret) | **High** — client secret is a password-equivalent | SOPS-encrypted at rest |
| `token.json` (access + refresh tokens) | **Critical** — grants full Gmail access | SOPS-encrypted at rest |
| Access token in memory | **Medium** — expires in 1 hour | Never persist to disk; store in memory only |

### Storage Strategy

```
┌─────────────────────────────────────────────┐
│  SOPS-encrypted files on disk                │
│  ├── credentials.enc.json   (client secret) │
│  └── gmail-token.enc.json   (refresh token) │
├─────────────────────────────────────────────┤
│  In memory only (never written to disk)      │
│  └── Access token     (rotates hourly)      │
└─────────────────────────────────────────────┘
```

### Key Principles

1. **Never commit** `credentials.json` or `token.json` to git
2. **Encrypt at rest** with SOPS/age
3. **Refresh token** is the crown jewel — protect it like a password
4. **Access token** should only exist in memory; if persisted, it's stale within an hour anyway
5. Google recommends storing refresh tokens in a **database** for multi-user apps; for single-user, encrypted file is sufficient
6. **Client secret** is shown once (April 2025 policy) — store it immediately

> **Evidence** ([Google OAuth best practices](https://developers.google.com/identity/protocols/oauth2/resources/best-practices)): "Store tokens securely at rest and never transmit them in plain text. Use a secure storage system appropriate for your platform."

---

## 9. Device Flow (Out-of-Band) for Headless VPS

### Available Approaches for VPS Without Browser

#### Approach A: Loopback Flow (Recommended)
The Python quickstart's default approach. The VPS starts a local web server, you forward the port via SSH, open the URL in your local browser:

```python
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_local_server(port=0)  # port=0 = random available port
```

**How it works on a headless VPS**:
1. Run script on VPS
2. It prints: `Please visit this URL: https://accounts.google.com/o/oauth2/auth?...`
3. Open that URL on your **local** machine's browser
4. Google redirects to `http://localhost:PORT/?code=...` — but this is the VPS's localhost
5. **Solution**: SSH port forwarding. Run `ssh -L 8080:localhost:8080 user@vps` on your local machine first, then use a fixed port:
   ```python
   creds = flow.run_local_server(port=8080)
   ```
6. The redirect hits your local browser, which forwards to the VPS via SSH tunnel

> **Evidence** ([Google installed app docs](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html)): "The run_local_server function attempts to open the authorization URL in the user's browser. It also starts a local web server to listen for the authorization response."

#### Approach B: Console Flow (Manual Copy-Paste)
```python
flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
creds = flow.run_console()
```
- Prints a URL → you open it on any device → Google shows an authorization code → you paste it back
- Simplest for one-time setup
- No SSH tunneling needed

#### Approach C: Google's Official Device Flow (TVs & Limited Input)
For the **OAuth 2.0 Device Flow** (`urn:ietf:params:oauth:grant-type:device_code`):
1. POST to `https://oauth2.googleapis.com/device/code` with `client_id` and `scope`
2. Get back `device_code`, `user_code`, `verification_url`
3. Display: "Go to `https://www.google.com/device` and enter code `XXXX-XXXX`"
4. Poll `https://oauth2.googleapis.com/token` until user authorizes

> **Evidence** ([Google device flow docs](https://developers.google.com/identity/protocols/oauth2/limited-input-device)): Full protocol specification for device flow.

**⚠️ Important**: The device flow is only supported for specific scopes. **All Gmail scopes (including `gmail.readonly`, `gmail.send`, `gmail.modify`) are NOT in the allowed scopes list for the device flow.** You must use the loopback or console flow.

#### Approach D: Remote Browser via SSH Forwarding
This is what the Python quickstart actually does if you can open a browser: SSH tunnel + `run_local_server`. Most practical for Faiz:
```bash
# On local machine:
ssh -L 8888:localhost:8888 faiz@vps

# On VPS:
python auth_script.py  # uses port 8888, opens URL for you to visit locally
```

---

## 10. App Password vs OAuth2

| Factor | App Password | OAuth2 |
|--------|-------------|--------|
| **Setup complexity** | Low (generate 16-char code) | Medium-High (Cloud Console, consent screen, code) |
| **Security model** | Static bearer token, no expiry, no scope | Short-lived access token (~1hr) + refresh token |
| **Revocation** | Revoke manually in Google Account; password change revokes all | Revoke per-app in Google Account or programmatically |
| **Scope restriction** | None — full account access via SMTP/IMAP | Granular: readonly, send-only, modify, labels |
| **API access** | SMTP/IMAP only (no Gmail REST API) | Full Gmail REST API (threads, labels, drafts, search) |
| **Token expiry** | Never expires (until revoked or password change) | Access token: ~1hr; refresh token: see §4-5 |
| **Gmail SMTP** | ✅ Works | ✅ Works (via XOAUTH2) |
| **Gmail REST API** | ❌ No | ✅ Yes |
| **2FA requirement** | Must have 2FA enabled | Works regardless of 2FA |
| **Google's recommendation** | "Not recommended" — for legacy apps | "Recommended" — for all modern apps |
| **Personal Gmail** | ✅ Supported | ✅ Supported |
| **Workspace** | ❌ Disabled since May 2025 | ✅ Required |

### When to Use App Passwords

- **Quick testing/prototyping** with SMTP only
- **Fallback** when OAuth2 breaks and you need email immediately
- You only need to **send** email (SMTP), not read/manage via REST API
- You don't want to deal with Cloud Console setup

### When to Use OAuth2

- **Production applications** — it's the correct, secure path
- You need the **Gmail REST API** (not just SMTP/IMAP)
- You need **granular scopes** (read-only, send-only, etc.)
- You want **auditable, revocable** access
- You're building something that will run for months/years

### Faiz's Situation

For Guinevere (read + draft + send + labels via Gmail REST API):

**OAuth2 is mandatory** — App Passwords only work with SMTP/IMAP, not the Gmail REST API. The REST API provides threads, labels, drafts, search, and structured message access that SMTP cannot.

**Recommendation**: OAuth2 primary, App Password as SMTP fallback for emergency send-only capability.

> **Evidence** ([Google App Passwords help](https://support.google.com/mail/answer/185833)): "App passwords aren't recommended and are unnecessary in most cases. To help keep your account secure, use 'Sign in with Google' to connect apps to your Google Account."

> **Evidence** ([Gmail SMTP 2026 guide](https://resources.mailertogo.com/guide/gmail-smtp-settings-host-port-authentication)): "App passwords are static bearer tokens with no expiry and no scope restriction — they bypass 2FA at the application layer. For production code, OAuth2 is the correct path."

---

## Summary: Decision Matrix for Guinevere

| Decision | Answer | Rationale |
|----------|--------|-----------|
| Service Account or OAuth2? | **OAuth2** | Service accounts don't work for personal Gmail |
| Internal or External? | **External** | No Workspace domain available |
| Testing or Production? | **Production** (unverified is OK for single-user) | Avoid 7-day token expiry |
| Scopes? | `gmail.modify` + `gmail.labels` | Covers read, compose, send, labels; avoids `https://mail.google.com/` |
| Headless auth method? | **Console flow** for first setup, then token refresh is fully automated | Simplest one-time setup |
| Libraries? | `google-api-python-client` 2.197.0 + `google-auth-oauthlib` 1.4.0 | Current stable versions |
| Token storage? | SOPS-encrypted JSON files on disk | Refresh token is crown jewel |
| App Password fallback? | Generate one for SMTP emergency | Cold backup if OAuth2 fails |
| Verification required? | No — if published to Production but accepting unverified-warning-once for single user | Verification costs time/money, not needed for personal use |

### The One-Time Setup Flow

```
1. Create Cloud Console project, enable Gmail API
2. Configure External consent screen, add yourself as test user
3. Create Desktop OAuth client, download credentials.json IMMEDIATELY
4. Run auth script via console flow → paste auth code → get token.json
5. Publish app to Production (in console)
6. Encrypt both files with SOPS → store in repo (never commit plaintext)
7. Runtime: decrypt → refresh access token → call Gmail API → re-encrypt if refresh token rotated
```

### References

- [Configure OAuth consent screen](https://developers.google.com/workspace/guides/configure-oauth-consent) — 2026-04-20
- [Using OAuth 2.0 to Access Google APIs](https://developers.google.com/identity/protocols/oauth2)
- [Gmail API Python Quickstart](https://developers.google.com/workspace/gmail/api/quickstart/python)
- [Gmail API Auth Scopes](https://developers.google.com/workspace/gmail/api/auth/scopes) — 2026-04-20
- [OAuth 2.0 for Installed Applications](https://googleapis.github.io/google-api-python-client/docs/oauth-installed.html)
- [OAuth 2.0 for Limited-Input Devices](https://developers.google.com/identity/protocols/oauth2/limited-input-device)
- [Google OAuth 2.0 Policies](https://developers.google.com/identity/protocols/oauth2/policies) — updated 2025-10-27
- [Refresh token expiration](https://developers.google.com/identity/protocols/oauth2#refresh-token-expiration)
- [App Passwords help](https://support.google.com/mail/answer/185833)
- [Gmail SMTP Settings 2026](https://resources.mailertogo.com/guide/gmail-smtp-settings-host-port-authentication) — 2026-05-03
- [Manage App Audience (Testing/Production)](https://support.google.com/cloud/answer/15549945)