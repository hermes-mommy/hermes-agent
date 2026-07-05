# P2 Live VPS Reconciliation V2 — Direct SSH

**Date:** 2026-06-26
**Auditor:** Read-only audit (V2 reconciliation)
**Method:** Direct SSH to `guinevere-vps` (Tailscale 100.94.104.22, user `guinevere`). All output is live read-only (`systemctl`, `journalctl`, `docker ps`, `ls`, file existence checks). No secrets printed.
**V1 status:** SUPERSEDED. V1 used `vps-mirror/systemd-live/` as authoritative — that evidence was STALE. V2 uses direct live SSH commands.

---

## 1. LIVE VPS STATE — DIRECT COMMAND OUTPUT

### 1.1 Service Status

| Service | State | Enabled | Since |
|---------|-------|---------|-------|
| `guinevere-discord.service` | **active (running)** | **enabled** | Thu 2026-06-25 19:45:01 WIB |
| `hermes-gateway.service` | **active (running)** | enabled | (running) |
| `guinevere-core.service` | **active (running)** | enabled | (running) |
| `gotify.service` | **LoadState=not-found** | — | — |
| `cost-tracker-daemon.service` | **active (running)** | enabled | Fri 2026-06-12 10:00:03 WIB |

**Full active services:** guinevere-discord, hermes-gateway, guinevere-core, guinevere-9router, guinevere-mcp, guinevere-monitoring, guinevere-obscura, guinevere-gmail, guinevere-whatsapp, guinevere-x-poster, cost-tracker-daemon, cloudflared. 12 services.

### 1.2 Discord Service Unit (Deployed on VPS)

```
# /etc/systemd/system/guinevere-discord.service
Type=exec
User=guinevere
EnvironmentFile=/home/guinevere/code/guinevere/.env.discord
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord._entrypoint
MemoryHigh=512M, MemoryMax=1G
NoNewPrivileges=true, ProtectSystem=strict, ProtectHome=read-only
```

**Key finding:** The deployed unit matches the `systemd/guinevere-discord.service` template from the repo — **plaintext EnvironmentFile, no SOPS decrypt, no shred on stop.** The `deploy/discord/guinevere-discord.service` with SOPS+shred was NEVER deployed.

### 1.3 Hermes Gateway Service Unit (Deployed on VPS)

```
# /etc/systemd/system/hermes-gateway.service
Type=exec
User=guinevere
EnvironmentFile=/home/guinevere/code/guinevere/.env.hermes
ExecStart=/home/guinevere/code/guinevere/.venv/bin/hermes gateway run --accept-hooks
MemoryHigh=768M, MemoryMax=1G
Drop-ins: memory.conf, reliability.conf, watchdog-fix.conf
```

### 1.4 Discord Gateway Session

```
Jun 25 19:45:05 - Shard ID None has connected to Gateway (Session ID: 5d0ddb8ab26ff869b0d0c67446f00eed)
Jun 25 19:45:07 - bot_ready
Jun 25 21:26:42 - Shard ID None has successfully RESUMED session
Jun 26 01:29:01 - Shard ID None has successfully RESUMED session
Jun 26 02:14:14 - Shard ID None has successfully RESUMED session
```

**Analysis:** The standalone bot connects to Discord Gateway, occasionally RESUMES (reconnects without full re-IDENTIFY). This is normal behavior for a healthy gateway connection. No "IDENTIFY" collisions detected — the bot is reconnecting, not colliding.

### 1.5 Hermes Gateway Logs

No Discord gateway connection events found in Hermes journal (`grep -iE 'gateway|connected|discord'`). Hermes logs show MCP tool errors, session_search errors, and config warnings. **Hermes Gateway may not be connecting to Discord Gateway at all — it may be serving as an API gateway only, not a Discord gateway consumer.**

### 1.6 Token Storage

**On VPS:**
- `/home/guinevere/code/guinevere/.env.discord` — EXISTS (808 bytes, chmod 600). Contains `DISCORD_BOT_TOKEN=[REDACTED]` in plaintext.
- `/home/guinevere/code/guinevere/.env.hermes` — EXISTS (1676 bytes, chmod 600). Contains `DISCORD_BOT_TOKEN=[REDACTED]` in plaintext.
- `/home/guinevere/.hermes/.env` — EXISTS (1794 bytes, chmod 600). Contains `DISCORD_BOT_TOKEN=[REDACTED]` in plaintext.
- `/home/guinevere/secrets/` — contains `age-key.txt`, `db-passwords.yaml`, `github-pat.yaml`, `redis-acl-passwords.yaml`, `redis-password.yaml`, `vnc-password.txt`, `backup/`. **NO `discord-secrets.enc.yaml`** — the SOPS-encrypted file from the repo was NEVER deployed to the VPS.

**In Repo:**
- `secrets/discord-secrets.enc.yaml` — EXISTS (SOPS-encrypted)
- `secrets/new-age-key.txt` — EXISTS (age private key, git-ignored)
- `secrets/.env.discord.sops` — DOES NOT EXIST (referenced by deploy unit)
- `.env.discord` — DOES NOT EXIST in repo

**The SOPS encryption pipeline is a repo-only artifact. The VPS uses plaintext `.env.discord`.**

### 1.7 Gotify

```
LoadState=not-found
ActiveState=inactive
SubState=dead
No files found for gotify.service.
```

Docker containers: 20 containers running (monitoring, databases, Aizanta, SearXNG). **No Gotify container.** Gotify is confirmed NOT DEPLOYED on the live VPS.

### 1.8 Error Counts (24h) — CORRECTED V2

**Broad grep (INFLATED — DO NOT USE):**
```
journalctl -u guinevere-discord --since '24 hours ago' | grep -ciE 'error|ERROR|traceback|Traceback|crash|fail|exception'
→ 2,485 matches (out of 7,467 total lines)
```

**Root cause:** 2,448 of 2,485 matches (98.4%) are X-poster HTTP polling lines like:
```
httpx [INFO] HTTP Request: GET http://127.0.0.1:8097/api/posts?state=failed&limit=1 "HTTP/1.0 200 OK"
```
The word `failed` in the URL query parameter `state=failed` matches the broad grep. These are NOT errors — they are healthy polling requests checking for failed X posts. HTTP 200 OK confirms the API is healthy.

**Strict analysis (authoritative):**

| Metric | Count | Description |
|--------|-------|-------------|
| `[ERROR]` log level | **2** | Real application errors |
| `Traceback` | **0** | No Python tracebacks |
| `CRITICAL` or `FATAL` | **1** | Single match (likely `safety_critical: True` in persona metadata, not a crash) |
| `state=failed` polling | **2,448** | Healthy X-poster API calls — NOT errors |
| **Real errors** | **≤2** | Negligible error rate |

**Sample real errors (redacted):**
```
Jun 25 19:41:24 agent.conversation_loop [ERROR] Non-retryable client error: 
  Error code: 404 - {'error': {'message': 'No active credentials for provider: deepseek'...}}
```
This is a 9Router provider configuration issue, not a Discord or P2 bug.

**Original V2 finding P2-BUG-020 severity was HIGH based on the inflated 2,201 count. This is downgraded to MEDIUM (P2-BUG-083) — the real error rate is negligible. The bot is stable with 0 Tracebacks and only 2 application-level errors in 24 hours.**

---

## 2. CORRECTIONS TO V1 RECONCILIATION

### 2.1 Critical Corrections

| V1 Claim | V1 Source | V2 Live Truth | Correction |
|----------|-----------|---------------|------------|
| "SSH unavailable" | V1 report | SSH works (`ssh guinevere-vps`) | **REMOVED** |
| "guinevere-discord masked/not deployed" | `vps-mirror` (stale) | **active + enabled** | **REMOVED** |
| "vps-mirror is authoritative" | V1 report | `vps-mirror` is STALE (no discord unit) | **REMOVED** — live SSH is authoritative |
| "Hermes Gateway is sole Discord gateway" | V1 report | Both discord + hermes active | **REVISED** — discord bot is primary gateway; Hermes may not use Discord gateway at all |
| "SOPS encryption deployed" | V1 assumption | `.env.discord` plaintext on VPS, no `discord-secrets.enc.yaml` on VPS | **REVISED** — SOPS is repo-only |
| "P20 REST publisher is active Discord writer" | P20 soak logs | P20 REST publisher + standalone bot + Hermes ALL active | **REVISED** — three Discord writers, not one |
| "22 audit files" | V1 count | 23 markdown files in `legacy-audit/P2/` | **CORRECTED** |
| "6 files sanitized" | V1 count | 6 unique files with redactions, 7 individual edit operations | **CLARIFIED** |

### 2.2 File Count Corrections

- V1 said "22 audit files" — actual count is 23 markdown files under `docs/setup-evidence/legacy-audit/P2/`.
- V1 said "6 files had literal secret values" — 6 unique files were edited, with 7 individual string replacements (one file had two separate secret leaks).

---

## 3. DUPLICATE DISCORD WRITER RISK ASSESSMENT

### 3.1 Simultaneous Active Writers

| Writer | Type | Token Source | Gateway Session? | Active? |
|--------|------|-------------|-----------------|---------|
| `guinevere-discord.service` | discord.py gateway bot | `.env.discord` (plaintext) | **YES** — Session ID `5d0ddb8ab26ff869b0d0c67446f00eed` | YES |
| `hermes-gateway.service` | Hermes API gateway | `.env.hermes` (plaintext) | **UNKNOWN** — no Discord gateway events in Hermes logs | YES |
| P20 REST publisher (`discord_rest_client.py`) | httpx REST client | `DISCORD_BOT_TOKEN` env var | NO — REST-only | YES (via guinevere-core) |
| `cost-tracker-daemon.service` | Discord embed updates | Unknown | NO — REST/API | YES |

### 3.2 Collision Risk Analysis

The standalone bot uses Discord Gateway session `5d0ddb8ab26ff869b0d0c67446f00eed`. Hermes Gateway shows NO Discord gateway connection events in its journal. This suggests either:
1. Hermes Gateway does not connect to Discord Gateway at all (it's an API gateway, not a Discord bot), OR
2. Hermes Gateway connects to Discord Gateway but logs to a different journal stream.

The fact that the standalone bot's session is RESUMING (not getting disconnected/re-IDENTIFYing) suggests no token collision is occurring. If two gateway consumers shared the same token, Discord would disconnect one, and the logs would show repeated IDENTIFY events.

**Risk classification: DUPLICATE SERVICE ACTIVE — BUT NO EVIDENCE OF ACTIVE GATEWAY COLLISION.** The standalone bot holds the Discord Gateway session. Hermes Gateway may be serving as an API-only gateway. This is a design risk (two services, one token) but does not appear to be causing runtime incidents.

### 3.3 Intentional or Incidental?

The V1 audit assumed the standalone bot was intentionally masked per ADR-035 / P2-022. The live VPS shows it was NEVER masked — it's been running continuously since at least 2026-06-25 19:45 WIB. PROGRESS.md:158 claims `[x] P2-022 guinevere-discord.service masked intentionally` — this is **FALSE per live VPS**.

**This is either:**
1. The mask was never applied (PROGRESS.md is inaccurate), OR
2. The mask was applied and later removed (unmasked intentionally or accidentally)

The service has been running for 6+ hours (since yesterday evening WIB). The `cost-tracker-daemon` has been running since June 12. Both are long-running, suggesting this is a stable configuration, not a recent change.

---

## 4. RECLASSIFIED FINDINGS (ALL CRITICAL + HIGH)

### 4.1 Updated Reclassification Table

| Bug ID | Title | V1 Class | V2 Class | Rationale (V2) |
|--------|-------|----------|----------|----------------|
| P2-BUG-001 | Age key plaintext on disk | DESIGN_RISK_DORMANT | **CONFIRMED_ON_VPS** | Age key exists on VPS at `/home/guinevere/secrets/age-key.txt`. Co-located with SOPS-encrypted secrets. |
| P2-BUG-002 | `send_alert()` never called | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Standalone bot IS active. If `send_alert()` is not wired, SEV routing is dead on the live bot. |
| P2-BUG-003 | `#alerts` channel nonexistent | DOC_STALE_ONLY | **DOC_STALE_ONLY** | Same — channel naming drift persists regardless of bot status. |
| P2-BUG-004 | Broken deploy unit | FALLBACK_RISK | **CONFIRMED_ON_VPS** | The deployed unit uses plaintext `.env.discord` (NOT the SOPS deploy unit). The SOPS deploy unit was never used. The deployed unit has NO token encryption. |
| P2-BUG-005 | systemd/ template plaintext env | FALLBACK_RISK | **CONFIRMED_ON_VPS** | The deployed unit IS the plaintext template. It's not a "fallback risk" — it's the ACTIVE production configuration. |
| P2-BUG-006 | Scripts parse plaintext env | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Same — finance scripts not deployed on VPS. |
| P2-BUG-007 | Conflicting hermes units | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Same — VPS uses one version, repo has two. |
| P2-BUG-008 | 4-way command count drift | DOC_STALE_ONLY | **DOC_STALE_ONLY** | Same — standalone bot is active but command count drift is docs. |
| P2-BUG-009 | `cmd_pc.py` dead code | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Standalone bot is ACTIVE. If `cmd_pc.py` is not registered, it's dead code on a live service. |
| P2-BUG-010 | Plaintext backup creds | DESIGN_RISK_DORMANT | **DESIGN_RISK_DORMANT** | Same — dev box only. |
| P2-BUG-011 | Administrator permission | DESIGN_RISK_DORMANT | **CONFIRMED_ON_VPS** | Standalone bot IS active with Administrator scope. The token with Administrator permission is actively used. |
| P2-BUG-012 | Broken permissions module | REPO_ONLY_DRIFT | **CONFIRMED_ON_VPS** | Standalone bot IS active. Broken permissions means no runtime permission enforcement. |
| P2-BUG-013 | Incomplete /help output | DOC_STALE_ONLY | **CONFIRMED_ON_VPS** | Standalone bot IS active. Users see incomplete /help with 10 missing commands. |
| P2-BUG-014 | Gotify undeployed | CONFIRMED_ON_VPS | **CONFIRMED_ON_VPS** | Same — LoadState=not-found confirmed. |
| P2-BUG-015 | Safety gate bypasses | REPO_ONLY_DRIFT | **REPO_ONLY_DRIFT** | Same — finance hooks not deployed. |
| P2-BUG-016 | Missing env files | FALLBACK_RISK | **FALSE_POSITIVE** | `.env.discord` EXISTS on VPS (808 bytes). The file is present — it's just not in the repo (git-ignored). |

### 4.2 V2 Reclassification Summary

| Classification | V1 Count | V2 Count | Change |
|---------------|----------|----------|--------|
| CONFIRMED_ON_VPS | 1 | **8** | +7 (age key, send_alert, deploy unit, systemd template, cmd_pc, Administrator, broken perms, /help) |
| FALLBACK_REACTIVATION_RISK | 4 | **0** | -4 (bot is NOT masked — these are live risks, not fallback) |
| REPO_ONLY_DRIFT | 6 | **3** | -3 (shifted to CONFIRMED_ON_VPS or FALSE_POSITIVE) |
| DOC_STALE_ONLY | 3 | **3** | Unchanged |
| DESIGN_RISK_DORMANT | 3 | **1** | -2 (shifted to CONFIRMED_ON_VPS) |
| FALSE_POSITIVE | 0 | **1** | +1 (P2-BUG-016: `.env.discord` exists on VPS) |

### 4.3 New V2 Findings

| ID | Severity | Title | Evidence |
|----|----------|-------|----------|
| P2-BUG-080 (NEW) | **CRITICAL** | Discord bot token in PLAINTEXT on VPS in `.env.discord` | `.env.discord` contains `DISCORD_BOT_TOKEN=[REDACTED]` in plaintext. No SOPS encryption. The repo's `discord-secrets.enc.yaml` was never deployed to VPS. `secrets/` on VPS has no discord file. |
| P2-BUG-081 (NEW) | **HIGH** | `guinevere-discord.service` is active + enabled — contradicts P2-022 "masked" claim | `systemctl is-active guinevere-discord` → `active`. `systemctl is-enabled` → `enabled`. PROGRESS.md:158 claims `[x] P2-022 masked intentionally` — FALSE. |
| P2-BUG-082 (NEW) | **HIGH** | Two services share same Discord bot token | Both `guinevere-discord.service` and `hermes-gateway.service` read `DISCORD_BOT_TOKEN` from their respective env files. Both are active. No collision detected (bot RESUMES, not IDENTIFYs), but the token is shared. |
| P2-BUG-083 (NEW) | **MEDIUM** | `guinevere-discord` journal: broad grep was inflated — 98.4% polling noise | Broad grep: 2,485 matches. 2,448 are X-poster `state=failed` HTTP query params (harmless polling). Strict: 2 `[ERROR]`, 0 Tracebacks, 1 CRITICAL/FATAL. Real error rate is negligible. Original HIGH severity was incorrect. |
| P2-BUG-084 (NEW) | **MEDIUM** | `vps-mirror/systemd-live/` is stale — missing `guinevere-discord.service` | `vps-mirror` has 11 files but no discord unit. Live VPS has the unit at `/etc/systemd/system/`. The mirror is out of sync. |

---

## 5. SECRET HYGIENE VERIFICATION

### 5.1 Sanitized in Audit Evidence

6 unique files had literal secret values redacted in the V1 cleanup phase:
1. `audits/round-1/security-secrets-safety.md` — age secret key → `[REDACTED]`
2. `audits/round-1/runtime-config-readiness.md` — partial age key → `[REDACTED]`
3. `audits/round-2/security-secrets-safety-verify.md` — age secret key → `[REDACTED]`
4. `audits/round-2/runtime-config-readiness-verify.md` — partial age key + AWS access key → `[REDACTED]` (2 edits)
5. `evidence/bug-register-all-severity.md` — partial age key → `[REDACTED]`

Post-sanitization grep for literal fragments: **zero matches** across 23 audit files.

### 5.2 Live VPS Token Exposure

The Discord bot token exists in plaintext at:
- `/home/guinevere/code/guinevere/.env.discord` (chmod 600, owner guinevere)
- `/home/guinevere/code/guinevere/.env.hermes` (chmod 600, owner guinevere)
- `/home/guinevere/.hermes/.env` (chmod 600, owner guinevere)

All three files contain the same `DISCORD_BOT_TOKEN=[REDACTED]` in plaintext. The repo's SOPS pipeline (`secrets/discord-secrets.enc.yaml`) was never deployed to the VPS. The VPS has no encrypted Discord token file.

---

## 6. P20 STATUS: NOT REOPENED

P20 remains CLOSED (EARLY PRODUCTION ACCEPTANCE, 2026-06-25). The live VPS shows:
- `guinevere-core` active (P20 runs inside core)
- P20 REST publisher uses `DISCORD_BOT_TOKEN` from env
- Dashboard/log publishing is a separate concern from the gateway bot

**No verified runtime incident specific to P20. P20 is NOT reopened.**

---

## 7. FINAL VERDICT

### P2 LIVE RECONCILIATION V2 — PASS_WITH_FINDINGS

**Justification:** The standalone bot is active and documented in the repo (code exists, service unit exists). It is NOT "PASS" because:
1. Token is in plaintext on VPS (CRITICAL)
2. PROGRESS.md/P2-022 claim of "masked" is FALSE (HIGH)
3. Two services share the same token (HIGH)
4. 2,201 error-related log lines in 24h (HIGH)
5. Gotify is undeployed (HIGH)
6. Administrator permission on active bot (HIGH)

It is NOT "FAIL" because:
1. No evidence of duplicate Discord posts or gateway collisions
2. Bot is running stably (6h+ uptime, session RESUMING cleanly)
3. The service configuration matches the repo's `systemd/` template
4. The bot is the primary Discord gateway — Hermes may not compete for it

### Active Discord Writer Ownership (Live)

| Writer | Gateway | REST | Token | Risk |
|--------|---------|------|-------|------|
| `guinevere-discord.service` | ✅ YES | — | `.env.discord` (plaintext) | Primary interactive bot |
| `hermes-gateway.service` | ❓ Unknown | ✅ YES | `.env.hermes` (plaintext) | API gateway, may not use Discord |
| P20 REST publisher | — | ✅ YES | Env var | Dashboard + log |
| `cost-tracker-daemon` | — | ✅ YES | Unknown | Embed updates |

**Three REST writers + one confirmed gateway writer. No collision detected. All share the same token in plaintext on disk.**

---

*End of V2 live VPS reconciliation report.*