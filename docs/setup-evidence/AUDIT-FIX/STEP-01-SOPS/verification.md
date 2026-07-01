# STEP-01-SOPS — Discord Token Encryption Fix

**Step:** Audit Fix 01 — P2-002 SOPS Encryption
**Date:** 2026-06-08
**Auditor:** Guinevere
**Status:** ✅ FIXED

---

## 1. What Was Done

Previously, P2-002 was claimed as DONE but the SOPS-encrypted `secrets/discord-secrets.yaml` **did not exist** (audit found the file missing). The Discord bot token was stored in **plaintext** at `~/.hermes/.env` with no encrypted backup.

### Implementation:

1. **Created SOPS-encrypted secret:**
   - File: `secrets/discord-secrets.enc.yaml`
   - Encryption: SOPS 3.9.4 + age key `age17cyg77cswk0du44k3r02g3l83x2f62crcnjnzv5cz5vtndve7yksck2zqj`
   - Contents: `discord_bot_token` (encrypted), `discord_bot_id` (encrypted)
   - Verify: `sops --decrypt secrets/discord-secrets.enc.yaml` returns correct values

2. **Updated `setup-service-envs.sh`:**
   - Added decryption step for `DISCORD_BOT_TOKEN` from the SOPS file
   - Added `.env.discord` generation with the decrypted token
   - idempotent: skips if decryption fails

3. **Fixed `.sops.yaml` BOM issue:**
   - Found UTF-8 BOM (`EF BB BF`) at start of `.sops.yaml` causing `"no matching creation rules found"` error
   - Removed BOM — all SOPS commands now work correctly
   - This was a latent bug affecting ALL sops operations

### Files Changed:
| Path | Change |
|------|--------|
| `secrets/discord-secrets.enc.yaml` | **NEW** — SOPS-encrypted token |
| `scripts/setup-service-envs.sh` | **UPDATED** — Discord token decryption + .env.discord generation |
| `.sops.yaml` | **FIXED** — UTF-8 BOM removed |

### Verification:
```
$ sops --decrypt secrets/discord-secrets.enc.yaml
discord_bot_token: MTUxMD... [correct token]
discord_bot_id: "1510873134981582858"
```

### Evidence:
- `secrets/discord-secrets.enc.yaml` — encrypted secret file
- `scripts/setup-service-envs.sh` — lines 40-44 (decryption), 81-88 (env generation)
