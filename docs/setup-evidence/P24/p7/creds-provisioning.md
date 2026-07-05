# P7 — Adapter Creds Provisioning Status

**Date: 2026-06-30 | Branch: p24-initial (hermes-mommy/hermes-agent fork)**

## 3 Services AUTONOMOUS (creds reused from prod — P7 done)
| Service | Creds source (prod) | P24 backend wired | Status |
|---|---|---|---|
| Gmail | /home/guinevere/code/guinevere/secrets/gmail-token.json + gmail-client-secrets.json (OAuth2, gmail.modify scope) | guinevere/tools/backends/email.py (_build_gmail_service, auto-refresh) | ✅ is_available=True (verified) |
| X (Twitter) | /home/guinevere/code/guinevere/.env.x_poster (X OAuth 1.0a: X_POSTER_X_API_KEY/SECRET + ACCESS_TOKEN/SECRET) | guinevere/tools/backends/social.py (post_x/read_mentions/reply_x, OAuth 1.0a HMAC-SHA1 signing) | ✅ wired (verified creds load) |
| WhatsApp | /home/guinevere/code/guinevere/secrets/.env.whatsapp (NEONIZE_SESSION_PATH + PASSWORD, SOPS-encrypted) + neonize session | guinevere/channels/whatsapp/ (21 .py, proven prod code: auth/bridge/consent/hard_stop) | ✅ creds exist (P8 deploy copies session) |

## 4 Services NEED OPERATOR PROVISION (genuinely no creds in prod — not reusable)
| Service | What operator must create | Where to put | P24 backend ready? |
|---|---|---|---|
| Telegram | TELEGRAM_BOT_TOKEN via @BotFather (t.me/BotFather, /newbot) | .env.telegram (new) | ✅ social.py send_telegram/get_telegram_updates/edit_telegram/delete_telegram (CONFIG_MISSING until token set) |
| Notion | NOTION_TOKEN — integration at notion.so/my-integrations → "New integration" → copy secret_xxx | .env.notion (new) | ✅ memory.py retrieve_page/search_notes/create_page/update_page/append_blocks/archive_page (CONFIG_MISSING) |
| Drive (Google) | Google OAuth client with Drive scope — console.cloud.google.com → APIs → Drive API → Credentials → OAuth client (desktop app) → download client_secret.json + run OAuth flow for refresh token | secrets/drive-client-secrets.json + secrets/drive-token.json | ✅ memory.py list_files/get_file/create_file/update_file/trash_file/delete_file/public_share (CONFIG_MISSING) |
| Calendar (Google) | Google OAuth client with Calendar scope — same console, add Calendar API + scope to existing OAuth client (can share with Drive) | reuse drive OAuth client (add calendar scope) OR secrets/calendar-token.json | ✅ memory.py list_events/get_event/create_event/update_event/delete_event (CONFIG_MISSING) |

## Design principle (P22-confirmed)
Per AGENTS.md: "report CONFIG_MISSING status honestly, not fake success." All 4 services above return `{ok: False, config_missing: True, error: "<service> credentials not provisioned"}` until creds are set. This is CORRECT behavior — no mock/fake success.

## Action for operator
Provision the 4 creds above (Telegram fastest — 2 min via BotFather; Notion 5 min; Drive/Calendar 15 min Google OAuth console). Once provisioned, P8 deploy will wire them + the 3 autonomous services to the P24 fork runtime.
