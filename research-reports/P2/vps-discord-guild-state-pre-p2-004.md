# VPS + Discord Guild State Report — P2-004 to P2-006 Readiness

| Field | Value |
|-------|-------|
| **Task** | Live state verification for P2-004 through P2-006 |
| **Date** | 2026-06-01T14:11+07:00 |
| **Host** | faiz-prod-01 (100.94.104.22) |
| **OS** | Linux 6.8.0-31-generic x86_64 Ubuntu 24.04 LTS |
| **Method** | SSH via guinevere-vps alias, bash scripts on VPS |
| **Secrets handling** | SOPS decrypt to temp file, in-memory token, shred after use. No secrets printed. |

---

## 1. System Health

| Metric | Value | Status |
|--------|-------|--------|
| Uptime | 9 days 3h 36min | PASS |
| CPU | 4 cores, Intel Xeon E5-2686 v4 @ 2.30GHz | PASS |
| Load average | 0.01 / 0.04 / 0.04 | PASS (idle) |
| Memory total | 15Gi | PASS |
| Memory used | 1.7Gi (13Gi available) | PASS |
| Swap | 4.0Gi (0 used) | PASS |
| Disk total | 99G (/dev/vda1, ext4) | PASS |
| Disk used | 17G (18%) | PASS |
| Disk free | 77G | PASS |

**Verdict: PASS** — No resource pressure. Same healthy state as P2 pre-check.

---

## 2. Canonical Port Verification

| Service | Expected | Actual | Interface | Status |
|---------|----------|--------|-----------|--------|
| PostgreSQL (Guinevere) | 5433 | 5433 | 127.0.0.1 | PASS |
| PgBouncer | 5434 | 5434 | 127.0.0.1 | PASS |
| Redis | 6380 | 6380 | 127.0.0.1 | PASS |
| 9Router LLM Proxy | 20128 | 20128 | 0.0.0.0 | PASS (next-server v1, pid=627406) |

**Verdict: PASS** — All four canonical ports listening.

---

## 3. Docker Container Status

### Guinevere Containers

| Container | Image | Status | Ports | Health |
|-----------|-------|--------|-------|--------|
| guinevere-postgres | guinevere-postgres-pgvector:16 | Up 22 hours | 127.0.0.1:5433→5432 | healthy (Docker check) |
| guinevere-pgbouncer | percona/percona-pgbouncer:1.25.2 | Up 20 hours | 127.0.0.1:5434→5432 | healthy (Docker check) |
| guinevere-redis | redis:7.4-alpine | Up 19 hours | 127.0.0.1:6380→6379 | healthy (Docker check) |

### Aizanta Containers (independent — not touched by Guinevere tasks)

| Container | Status | Ports |
|-----------|--------|-------|
| aizanta-bot | Up 8 days (healthy) | 8000/tcp |
| aizanta-nginx | Up 8 days (healthy) | 100.94.104.22:80→80 |
| aizanta-frontend | Up 6 hours (healthy) | 3000/tcp |
| aizanta-postgres | Up 9 days (healthy) | 127.0.0.1:5432→5432 |
| aizanta-redis | Up 9 days (healthy) | 127.0.0.1:6379→6379 |
| objective_buck | Up 9 days | (unknown) |
| elastic_beaver | Up 9 days | (unknown) |

**Verdict: PASS** — All Guinevere containers healthy. Aizanta containers stable and isolated.

---

## 4. Systemd Service Status

| Service | Status | Memory | PID |
|---------|--------|--------|-----|
| guinevere-core.service | active | 121MB | 661232 (uvicorn) |
| guinevere-9router.service | active | 122MB | 627406 (next-server v1) |
| cloudflared.service | active | 17MB | 315061 |

**Verdict: PASS** — All three systemd services active.

---

## 5. Secret File Integrity

| File | Exists | Size | Permissions | Owner | Status |
|------|--------|------|-------------|-------|--------|
| `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml` | Yes | 1792 bytes | 600 | guinevere:guinevere | PASS |
| `/home/guinevere/secrets/age-key.txt` | Yes | 189 bytes | 600 | guinevere:guinevere | PASS |

**Verdict: PASS** — Both files present with correct ownership and permissions.

---

## 6. Secret Decrypt & Discord Bot Identity

### SOPS Decrypt

| Check | Result |
|-------|--------|
| Decrypt exit code | 0 (success) |
| Decrypted size | 257 bytes |
| discord_bot_token | present (72 chars) |
| discord_application_id | 1510873134981582858 |
| discord_public_key | present |

### Discord API /users/@me

| Field | Value |
|-------|-------|
| bot_id | 1510873134981582858 |
| username | Guinevere |
| verified | True |
| is_bot | True |
| matches application_id | Yes |

**Verdict: PASS** — Token valid, bot verified, app ID matches, username is `Guinevere`.

---

## 7. Guild State: Guinevere Lab

### Guild Overview

| Field | Value |
|-------|-------|
| Guild name | Guinevere Lab |
| Guild ID | 1510876414671323206 |
| Bot is owner | No |
| Total guilds bot is in | 1 |

### Categories

| Category ID | Name | Position |
|-------------|------|----------|
| 1510876415397204029 | Text Channels | 0 |
| 1510876415397204030 | Voice Channels | 0 |

### Channels

| Channel ID | Name | Type | Parent Category |
|------------|------|------|-----------------|
| 1510876415397204031 | #general | Text (0) | Text Channels |
| 1510876415397204032 | General | Voice (2) | Voice Channels |

### Bot Member Info

| Field | Value |
|-------|-------|
| Bot joined at | 2026-06-01T05:23:50.254000+00:00 |
| Nickname (server) | none (uses global) |
| Bot role ID | 1510876507973877780 |
| Bot has avatar | Yes (hash: 87e5adc220a7db...) |
| Muted/deaf | No / No |
| Pending membership | No |

### Roles

| Role ID | Name | Permissions | Managed | Bot-specific |
|---------|------|-------------|---------|-------------|
| 1510876414671323206 | @everyone | 2248473465835073 | No | No |
| 1510876507973877780 | **Guinevere** | 8 (ADMINISTRATOR) | **Yes** | **Yes** (bot_id=1510873134981582858) |

**Note:** The bot has been assigned a managed role `Guinevere` with ADMINISTRATOR permission (bit `8`). This is auto-managed by Discord when the bot is added and grants full administrative access to the guild.

**Verdict: PASS** — Guild exists with correct name `Guinevere Lab`. Bot is member with ADMINISTRATOR roll. Minimal structure (1 category, 1 text channel, 1 voice channel). Ready for new channel/category creation in P2-004.

---

## 8. 9Router & Connectivity

| Check | Result |
|-------|--------|
| 9Router /v1/models | HTTP 200 |
| Cloudflared tunnel | active |
| Tailscale Faiz (Windows) | connected direct |

**Verdict: PASS** — All connectivity paths healthy.

---

## 9. Tailscale Network

| Node | Address | Status |
|------|---------|--------|
| faiz-prod-01 (VPS) | 100.94.104.22 | active |
| faizzzzz (Faiz Windows) | 100.112.201.124 | active, direct |
| backend | 100.104.35.93 | linux |
| frontend | 100.108.191.1 | linux |
| db-1 | 100.89.183.24 | linux |
| budgezen-openclaw | 100.127.51.59 | linux |
| xiaomi-11t | 100.108.206.99 | offline (9d ago) |

---

## 10. P2-004 to P2-006 Readiness Assessment

### Prerequisites

| Prerequisite | Status | Evidence |
|-------------|--------|----------|
| VPS SSH accessible | PASS | Batch-mode, key-based auth |
| System resources adequate | PASS | 13Gi avail mem, 77G free disk, load 0.01 |
| PostgreSQL 5433 listening | PASS | Docker healthy |
| PgBouncer 5434 listening | PASS | Docker healthy |
| Redis 6380 listening | PASS | Docker healthy |
| 9Router 20128 listening | PASS | HTTP 200 on /v1/models |
| guinevere-core running | PASS | systemd active |
| guinevere-9router running | PASS | systemd active |
| Cloudflare tunnel active | PASS | systemd active |
| Discord secret file | PASS | 1792 bytes, 600 perms |
| Age key file | PASS | 189 bytes, 600 perms |
| SOPS decrypt works | PASS | exit 0, all fields present |
| Bot token valid | PASS | API 200, verified |
| Bot username = Guinevere | PASS | Discord API confirms |
| Bot app ID = 1510873134981582858 | PASS | matches |
| Guild: Guinevere Lab exists | PASS | ID 1510876414671323206 |
| Bot is member of guild | PASS | joined 2026-06-01 |
| Bot has ADMINISTRATOR role | PASS | managed role, permission 8 |
| Discord guild only bot guild | PASS | only 1 guild |
| Minimal channels exist | PASS | #general + General VC |

### P2-004 Specific: Channel/Category Creation Readiness

| Check | Status | Note |
|-------|--------|------|
| Can create categories | PASS | Bot has ADMIN |
| Can create text channels | PASS | Bot has ADMIN |
| Can create voice channels | PASS | Bot has ADMIN |
| Rate limits (Discord API) | INFO | 5 req/s per route for common ops; be mindful in code |
| Permission overwrites | PASS | ADMIN role bypasses all |

### P2-005 Specific: Bot Command Readiness

| Check | Status | Note |
|-------|--------|------|
| Discord.py installed | INFO | Not tested — will install at P2-004 |
| Intents configured | PASS | Hermes config has `messages,guilds,members,message_content` |
| Message content intent | PASS | Required for prefix commands |

### P2-006 Specific: Voice/Audio Readiness

| Check | Status | Note |
|-------|--------|------|
| Voice channel exists | PASS | "General" VC with ID 1510876415397204032 |
| Discord.py voice support | INFO | Need `discord.py[voice]` extra |
| FFmpeg on VPS? | NOT CHECKED | Verify at P2-006 |
| Bot can join VC | PASS | Has ADMIN permission |

---

## 11. Edge Cases & Risks

| # | Item | Severity | Detail | Action |
|---|------|----------|--------|--------|
| E1 | Only 1 guild | INFO | Bot only in Guinevere Lab (expected, no cross-guild issues) | Verify after invite process |
| E2 | Bot not owner of guild | LOW | Cannot delete/manage guild-level settings; all channel ops fine with ADMIN role | N/A — expected |
| E3 | Bot role is managed | INFO | Cannot manually edit role permissions; ADMIN is sufficient | N/A |
| E4 | Discord.py voice extras | LOW | `discord.py[voice]` requires FFmpeg and libopus on VPS | Verify at P2-006 |
| E5 | Minimal channel structure | INFO | Only #general + General VC exist | P2-004 will add categories/channels |
| E6 | @everyone perms broad | INFO | Default role has extensive perms | Review during category creation if needed |
| E7 | Bot avatar set | INFO | Bot has a custom avatar hash — no action needed | Good for UX |

---

## 12. Verdict

**Overall: GREEN — CLEAR TO START P2-004**

All infrastructure checks pass:
- VPS healthy, idle resources
- All 4 canonical ports listening
- All Docker containers healthy
- All systemd services active
- Discord token valid, bot verified as `Guinevere`
- Guild `Guinevere Lab` exists, bot is member with ADMINISTRATOR role
- Guild has minimal channel structure ready for expansion

---

## 13. Commands Used (Sanitized)

```bash
# SSH connectivity
ssh -o BatchMode=yes guinevere-vps whoami

# System health
uptime; free -h; df -h /; cat /proc/loadavg

# Port verification
for port in 5433 5434 6380 20128; do
    ss -tlnp | grep -q ":$port " && echo "$port OK" || echo "$port MISSING"
done

# Docker status
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"
docker inspect --format '{{.Name}} {{.State.Health.Status}}' guinevere-postgres guinevere-pgbouncer guinevere-redis

# Systemd
for svc in guinevere-core guinevere-9router cloudflared; do
    systemctl is-active "$svc.service"
    systemctl show "$svc.service" -p MemoryCurrent
done

# Discord secret decrypt (temp file, shred after use)
sops --decrypt /home/guinevere/code/guinevere/secrets/discord-secrets.yaml > /tmp/decrypted.yaml

# Discord API verification (token in variable, unset after)
curl -sS -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/users/@me
curl -sS -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/users/@me/guilds
curl -sS -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/guilds/$GUILD_ID/channels
curl -sS -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/guilds/$GUILD_ID/roles
curl -sS -H "Authorization: Bot $TOKEN" https://discord.com/api/v10/guilds/$GUILD_ID/members/$BOT_ID

# 9Router health
curl -sS -o /dev/null -w "%{http_code}" http://127.0.0.1:20128/v1/models

# Tailscale
tailscale status
```

---

## 14. Evidence Artifacts

| Artifact | Path |
|----------|------|
| This report | research-reports/P2/vps-discord-guild-state-pre-p2-004.md |
| Pre-P2 readiness (baseline) | research-reports/P2/vps-discord-readiness-pre-p2.md |
| P2 struct research | research-reports/P2/source-structure-discord-pre-p2.md |
| Discord UX spec | docs/60-persona/63-DiscordUXSpec_v1.0.md |
| Discord intents/token security | research-reports/P2/discord-intents-token-security.md |
| Discord.py app commands | research-reports/P2/discord-py-2-app-commands.md |

---

## Footer

| Field | Value |
|-------|-------|
| Source task | P2-004 through P2-006 pre-implementation live state verification |
| Date | 2026-06-01T14:12+07:00 |
| Implementer | Guinevere (parent) |
| Validation method | SSH + bash scripts on VPS, Discord REST API, SOPS decrypt to temp |
| Secrets policy | All decrypted tokens stored in temp files (shredded) or bash variables (unset). No secrets printed in output or report. |
| Temp scripts cleaned | /tmp/p2-004-check.sh, /tmp/p2-004-guild.sh, /tmp/p2-004-roles.sh — all deleted |
| Next action | Begin P2-004: Discord channel/category creation implementation |