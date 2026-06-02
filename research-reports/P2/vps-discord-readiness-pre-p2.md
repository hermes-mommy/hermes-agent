# VPS Readiness Report -- P2-001 to P2-003 (Discord Bot Infrastructure)

| Field | Value |
|-------|-------|
| **Task** | VPS readiness exploration for P2-001 to P2-003 |
| **Date** | 2026-06-01 |
| **Host** | faiz-prod-01 (100.94.104.22) |
| **OS** | Linux 6.8.0-31-generic x86_64 Ubuntu |
| **Implementer** | Guinevere (parent) |
| **Method** | SSH via guinevere-vps alias, direct commands + script-based verification |

---

## 1. System Health

### 1.1 Basic Resources

| Metric | Value | Status |
|--------|-------|--------|
| Uptime | 9 days 2h 46m | PASS |
| CPU | 4 cores, Intel Xeon E5-2686 v4 @ 2.30GHz | PASS |
| Load average | 0.09 / 0.08 / 0.02 | PASS (idle) |
| Memory total | 15Gi | PASS |
| Memory used | 1.7Gi (13Gi available) | PASS |
| Swap | 4Gi (0 used) | PASS |
| Disk total | 99G (/dev/vda1, ext4) | PASS |
| Disk used | 17G (18%) | PASS |
| Disk free | 77G | PASS |

**Verdict: PASS** -- Resources well within limits. No resource pressure.

### 1.2 Docker Container Status

| Container | Image | Status | Ports | Memory |
|-----------|-------|--------|-------|--------|
| guinevere-postgres | guinevere-postgres-pgvector:16 | Up 21h (healthy) | 127.0.0.1:5433-5432 | 68.4MiB |
| guinevere-pgbouncer | percona/percona-pgbouncer:1.25.2 | Up 20h (healthy) | 127.0.0.1:5434-5432 | 2.5MiB |
| guinevere-redis | redis:7.4-alpine | Up 18h (healthy) | 127.0.0.1:6380-6379 | 3.5MiB |
| aizanta-bot | aizanta-bot | Up 8d (healthy) | 8000/tcp | 188.7MiB/512MiB |
| aizanta-nginx | nginx:1.27-alpine | Up 8d (healthy) | 100.94.104.22:80-80 | 4.8MiB/64MiB |
| aizanta-frontend | aizanta-frontend | Up 5h (healthy) | 3000/tcp | 30.8MiB/512MiB |
| aizanta-postgres | postgres:16-alpine | Up 9d (healthy) | 127.0.0.1:5432-5432 | 120.5MiB/512MiB |
| aizanta-redis | redis:7.2-alpine | Up 9d (healthy) | 127.0.0.1:6379-6379 | 2.8MiB/128MiB |

**Verdict: PASS** -- All Guinevere containers healthy. Aizanta containers independent (different ports).

---

## 2. Canonical Port Verification

| Service | Expected | Actual | Listening | Process |
|---------|----------|--------|-----------|---------|
| PostgreSQL (Guinevere) | 5433 | 5433 | PASS 127.0.0.1:5433 | Docker: guinevere-postgres |
| PgBouncer | 5434 | 5434 | PASS 127.0.0.1:5434 | Docker: guinevere-pgbouncer |
| Redis | 6380 | 6380 | PASS 127.0.0.1:6380 | Docker: guinevere-redis |
| 9Router LLM Proxy | 20128 | 20128 | PASS 0.0.0.0:20128 | systemd: next-server v16.2.1 |

**Test command:** ss -tlnp | grep -E '(5433|5434|6380|20128)'

**Supporting:** 9Router /v1/models responds HTTP 200. Core service /health responds HTTP 200.

**Verdict: PASS** -- All four canonical ports listening on expected interfaces.

---

## 3. Systemd Service Status (Guinevere)

| Service | Status | Uptime | Memory | PID |
|---------|--------|--------|--------|-----|
| guinevere-core.service | active (running) | 3h 35min | 115.7MiB | 661232 (uvicorn) |
| guinevere-9router.service | active (running) | 5h 1min | 116.3MiB | 627184 (node) |
| cloudflared.service | active (running) | 17h | 16.1MiB | 315061 |

**Sudo note:** User guinevere has passwordless sudo only for guinevere-* systemd commands.

**Cloudflared:** Tunnel 47d1c79b-e0e0-4562-95dd-93d91e62590b.
Ingress: discord-webhook.mypapyr.com to localhost:8000.
Historical errors (May 31 19:57) resolved after core service started.

**Verdict: PASS** -- All three systemd services active.

---

## 4. Discord Secrets -- File Existence and Permissions

### 4.1 Secret File

**Path:** /home/guinevere/code/guinevere/secrets/discord-secrets.yaml

| Attribute | Value | Status |
|-----------|-------|--------|
| Exists | Yes | PASS |
| Size | 1792 bytes | PASS |
| Permissions | -rw------- (600) | PASS |
| Owner | guinevere:guinevere | PASS |
| Created | 2026-06-01 13:06 | PASS |

### 4.2 Age Key File

**Path:** /home/guinevere/secrets/age-key.txt

| Attribute | Value | Status |
|-----------|-------|--------|
| Exists | Yes | PASS |
| Size | 189 bytes | PASS |
| Permissions | -rw------- (600) | PASS |
| Owner | guinevere:guinevere | PASS |
| Created | 2026-05-31 14:20 | PASS |

### 4.3 Tool Versions

| Tool | Version | Status |
|------|---------|--------|
| sops | 3.9.4 | PASS (newer 3.13.1 avail) |
| age | 1.1.1 | PASS |

### 4.4 Note: Two Secrets Files

- discord-secrets.yaml -- EXISTS on VPS, 1792 bytes, chmod 600
- guinevere-secrets.yaml -- NOT FOUND on VPS (only in local repo)

The local repo secrets/guinevere-secrets.yaml uses different key naming (discord.bot_token vs discord_bot_token). Only VPS discord-secrets.yaml is runtime-deployable.

**Verdict: PASS** -- Secret file exists with correct permissions (600). Age key accessible. SOPS/age installed.

---

## 5. Discord Secrets -- Decrypt and Integrity Test

**Method:** Bash script decrypts to temp file, verifies field presence, shreds temp file.

| Check | Result |
|-------|--------|
| Decrypt exit code | 0 (success) |
| discord_bot_token field | present |
| discord_application_id field | present |
| discord_public_key field | present |
| Application ID match (1510873134981582858) | ok |
| Decrypted size | 257 bytes |

**Verdict: PASS** -- SOPS decryption works, all required Discord fields present, app_id matches.

---

## 6. Discord API Verification

**Method:** Decrypt token -- curl Discord API /users/@me -- parse JSON -- shred and unset.

| Check | Result |
|-------|--------|
| HTTP status code | 200 |
| discord_api | ok |
| bot_id | 1510873134981582858 |
| bot_username | Guinevere |
| matches_application_id | yes |
| verified | yes |
| bot | yes |
| avatar | none (no avatar set) |

**Verdict: PASS** -- Bot token valid, bot verified, app ID matches, username is Guinevere.

---

## 7. Hermes Config -- Discord Section

Path: /home/guinevere/config/hermes/config.yaml

```
messaging:
  discord:
    enabled: true
    prefix: '!'
    intents: ['messages','guilds','members','message_content']
```

**Note:** yandere_baseline in Hermes config = Y4, PersonaDoc v3.0 specifies Y1. Flag for review.

**Verdict: INFO** -- Config present. Intent names are shorthand -- verify at P2-003.

---

## 8. Source Code Status -- Discord Bot

| Location | Status |
|----------|--------|
| src/core/main.py | FastAPI app, no Discord bot logic |
| src/discord/ | Exists, contains empty __init__.py only |
| Discord Python packages | Not installed in .venv |
| Runbooks directory | Not present on VPS |

**Verdict: EXPECTED** -- P2-001 through P2-003 will create bot structure.

---

## 9. Connectivity Matrix

| Connection | Source to Target | Status |
|-----------|-----------------|--------|
| Core to 9Router | 127.0.0.1:8000 to 127.0.0.1:20128 | PASS (v1/models 200) |
| Core to PostgreSQL | 127.0.0.1:8000 to 127.0.0.1:5433 | AUTH (SOPS-stored creds) |
| Core to PgBouncer | 127.0.0.1:8000 to 127.0.0.1:5434 | AUTH (SOPS-stored creds) |
| Core to Redis | 127.0.0.1:8000 to 127.0.0.1:6380 | AUTH (SOPS-stored creds) |
| Core to Discord API | VPS outbound to discord.com:443 | PASS (bot token validated) |
| Cloudflared to Core | localhost to 127.0.0.1:8000 | PASS (health 200) |
| Cloudflared to Discord | Cloudflare to discord.com | PASS (tunnel active) |

---

## 10. Tailscale Network

| Node | Address | Status |
|------|---------|--------|
| faiz-prod-01 (this VPS) | 100.94.104.22 | linux, active |
| faizzzzz (Faiz Windows) | 100.112.201.124 | active, direct |
| backend | 100.104.35.93 | linux |
| frontend | 100.108.191.1 | linux |
| db-1 | 100.89.183.24 | linux |
| budgezen-openclaw | 100.127.51.59 | linux |
| xiaomi-11t | 100.108.206.99 | offline (9d ago) |

---

## 11. Risk and Edge Case Summary

| # | Item | Severity | Detail | Action |
|---|------|----------|--------|--------|
| E1 | guinevere-secrets.yaml not on VPS | LOW | Only discord-secrets.yaml on VPS. Local repo has both. | Document canonical source; sync on rotation |
| E2 | Yandere baseline drift (Y4 vs Y1) | MEDIUM | Hermes config Y4, PersonaDoc v3.0 Y1 | Flag for config review pre-P2-017 |
| E3 | Cloudflared historical errors | LOW | May 31 19:57 errors before core started | Monitor after restarts |
| E4 | Discord Python packages not installed | LOW | .venv has no discord.py | Install at P2-001 |
| E5 | 9Router /health returns 404 | LOW | No health endpoint, but /v1/models 200 | Verify API compat at P2 |
| E6 | PostgreSQL/Redis auth unknown | INFO | Credentials SOPS-encrypted | Use at runtime |
| E7 | No runbooks on VPS | LOW | runbooks/ missing on VPS | Sync if needed |
| E8 | SOPS v3.9.4 vs latest v3.13.1 | INFO | Older version | Upgrade if compat issues |

---

## 12. Verdict: P2-001 to P2-003 Readiness

### Per-Prerequisite Status

| Prerequisite | Status | Evidence |
|-------------|--------|----------|
| VPS SSH accessible | PASS | Batch-mode SSH works, key-based auth |
| System resources adequate | PASS | 13Gi avail mem, 77G free disk, load under 0.1 |
| PostgreSQL 5433 listening | PASS | Docker container healthy, port open |
| PgBouncer 5434 listening | PASS | Docker container healthy, port open |
| Redis 6380 listening | PASS | Docker container healthy, port open |
| 9Router 20128 listening | PASS | systemd active, API responsive |
| guinevere-core running | PASS | systemd active, health endpoint 200 |
| Cloudflare tunnel active | PASS | systemd active, ingress configured |
| Discord secret file exists | PASS | 1792 bytes, chmod 600 |
| Age key file exists | PASS | 189 bytes, chmod 600 |
| SOPS decrypt works | PASS | exit_code=0, all fields present |
| Discord bot token valid | PASS | API /users/@me to 200, bot verified |
| Bot app ID matches 1510873134981582858 | PASS | matches_application_id=yes |
| Discord public key present | PASS | Field present in decrypted YAML |
| Tailscale connectivity | PASS | Faiz Windows connected direct |

### Final: GREEN -- CLEAR TO START P2-001

---

## 13. Commands Used (Sanitized)

```
# SSH connectivity
ssh -o BatchMode=yes guinevere-vps whoami

# Port check (ss, no sudo needed)
ss -tlnp | grep -E '(5433|5434|6380|20128)'

# Docker status
docker ps --format 'table ...'
docker stats --no-stream --format 'table ...'

# System resources
uptime; free -h; df -h /; cat /proc/loadavg

# Systemd services
systemctl status guinevere-core.service
systemctl status guinevere-9router.service
systemctl status cloudflared.service

# Secret decrypt test (via temp script, auto-shredded)
SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt secrets/discord-secrets.yaml

# Discord API verification (via temp script, token cleared after use)
curl -sS -H 'Authorization: Bot [REDACTED]' https://discord.com/api/v10/users/@me

# Tailscale status
tailscale status

# 9Router API check
curl -sS http://127.0.0.1:20128/v1/models
```

---

## 14. Evidence Artifacts

| Artifact | Path |
|----------|------|
| This report | research-reports/P2/vps-discord-readiness-pre-p2.md |
| Pre-P2 local Discord state | research-reports/P2/local-discord-state-pre-p2.md |
| P2 preconditions evidence | docs/setup-evidence/P1/p2-preconditions-resolved.md |
| P2 readiness report | audit-reports/P1/P1-FINAL/07-p2-readiness.md |
| Hermes config evidence | docs/setup-evidence/P1/STEP-P1-005/config.yaml |
| Discord UX spec | docs/60-persona/63-DiscordUXSpec_v1.0.md |
| ADR-022 (Comm strategy) | adr/ADR-022-communication-channel-strategy.md |

---

## Footer

| Field | Value |
|-------|-------|
| Source task | Pre-P2 VPS readiness exploration (P2-001 to P2-003) |
| Date | 2026-06-01 |
| Implementer | Guinevere (parent) |
| Validation method | SSH batch-mode commands + script-based secret verification |
| Secrets policy | All decrypted tokens cleared from memory and temp files shredded. No secrets printed. |
| Next action | Begin P2-001: Discord application verification |
