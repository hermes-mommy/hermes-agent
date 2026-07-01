# P10 Production Hardening — Evidence

**Date:** 2026-06-09
**Status:** COMPLETE
**Last Verified:** 2026-06-09 23:15 WIB (iteration 3)

---

## Live VPS Scorecard (12/12 PASS)

| # | Check | Verdict | Evidence |
|---|-------|---------|----------|
| 1 | SSH key access works | ✅ PASS | ssh guinevere-vps succeeded as guinevere@faiz-prod-01 |
| 2 | UFW enabled with deny-incoming default | ✅ PASS | `ufw status verbose` → Status: active, Default: deny (incoming) |
| 3 | SSH port restricted/explicitly allowed | ✅ PASS | UFW only shows 22/tcp and 41641/udp allow rules |
| 4 | Fail2ban active | ✅ PASS | `fail2ban-client status sshd` → active jail, 14+ banned |
| 5 | CrowdSec active | ✅ PASS | `cscli lapi status` succeeded |
| 6 | Core health endpoint | ✅ PASS | `curl http://127.0.0.1:8000/health` → healthy JSON |
| 7 | 9Router health endpoint | ✅ PASS | `curl http://127.0.0.1:20128/api/health` → {"ok":true} |
| 8 | PostgreSQL reachable | ✅ PASS | `pg_isready` → accepting connections |
| 9 | Redis health check | ✅ PASS | `redis-cli -a $PASS ping` → PONG (authenticated) |
| 10 | Monitoring stack containers up | ✅ PASS | Prometheus/Grafana/Loki/Alertmanager/exporters all up |
| 11 | Backup success sentinel present | ✅ PASS | `/home/guinevere/.hermes/backup/last-success` exists |
| 12 | Backup sentinel path matches | ✅ PASS | `/var/log/guinevere/last-backup-success` synced |

---

## Security Hardening — Listener Binding (Iteration 3 Fix)

| Port | Service | Before | After | Status |
|------|---------|--------|-------|--------|
| 8000 | guinevere-core (uvicorn) | 0.0.0.0 | 127.0.0.1 | ✅ FIXED |
| 9191 | guinevere-core (llm_metrics) | 0.0.0.0 | 127.0.0.1 | ✅ FIXED |
| 20128 | 9Router (next-server) | 127.0.0.1 | 127.0.0.1 | ✅ Already OK |

**Files changed:**
- `/etc/systemd/system/guinevere-core.service` — `--host 127.0.0.1`
- `/home/guinevere/code/guinevere/src/core/services/llm_metrics.py` — `addr="127.0.0.1"`

---

## Backup Script Fix (Iteration 3)

**Problem:** Sentinel sync block was after `exit 0` (dead code).
**Fix:** Moved sync before exit, added `SENTINEL_SYNC` variable.

---

## Iteration History

| Iteration | What | Result |
|-----------|------|--------|
| 1 | Initial P10 implementation | 6/6 steps, claimed 12/12 |
| 2 | Faiz audit found 3 FAILs (9Router, Redis, backup sentinel) | Fixed, re-verified 12/12 |
| 3 | Faiz audit found listener binding issue (8000, 9191 on 0.0.0.0) | Fixed to 127.0.0.1 |

---

## Summary

Production hardening fully validated live on VPS: firewall, SSH, Fail2ban, CrowdSec, all services bound to localhost, PostgreSQL, Redis (authenticated), monitoring stack, and backup sentinel all verified with actual commands.

---

## What Was Done

### P10-001: Security Hardening
- UFW firewall enabled (deny incoming default)
- Exposed ports 8000, 9090, 9191, 20128 blocked AND bound to 127.0.0.1
- SSH hardened (key-only, MaxAuthTries=3)
- DSA host key removed
- Leaked Discord token purged from logs
- Plaintext backup .env files deleted

### P10-002: Reliability
- Health checks every 5 minutes (14 checks including Redis auth)
- Auto-restart policies on all services
- Memory limits (hermes-gateway 1GB, core/9router 512MB)
- Graceful shutdown (TimeoutStopSec=30s)

### P10-003: Performance
- Memory limits on critical services
- Global slice cap: 8GB RAM, 512 tasks
- Database indexes verified (11 on finance tables)

### P10-004: Monitoring & Alerting
- SLO scorecard daily at 08:00
- Prometheus: 28 alert rules
- Grafana: 8 dashboards

### P10-005: Disaster Recovery
- Backup daily at 02:00 to S3 (restic+rclone)
- Retention: 7 daily, 4 weekly, 3 monthly
- Sentinel synced to `/var/log/guinevere/last-backup-success`

### P10-006: Documentation
- Evidence document (this file)
- Health check script
- SLO scorecard script
- Backup & verify scripts

---

## Files Created/Modified

| File | Purpose |
|------|---------|
| /etc/systemd/system/hermes-gateway.service.d/reliability.conf | Restart policy |
| /etc/systemd/system/hermes-gateway.service.d/memory.conf | Memory limits |
| /etc/systemd/system/guinevere-core.service | ExecStart --host 127.0.0.1 |
| /etc/systemd/system/guinevere-core.service.d/reliability.conf | Restart policy |
| /etc/systemd/system/guinevere-core.service.d/memory.conf | Memory limits |
| /etc/systemd/system/guinevere-9router.service.d/memory.conf | Memory limits |
| /etc/systemd/system/guinevere-health-check.service | Health check service |
| /etc/systemd/system/guinevere-health-check.timer | Health check timer (5min) |
| ~/.hermes/scripts/health-check.sh | Health check script |
| ~/.hermes/scripts/slo-scorecard.sh | SLO scorecard generator |
| ~/.hermes/backup/backup.sh | Backup script (fixed sync) |
| ~/.hermes/backup/verify-backup.sh | Backup verification |
| /var/log/guinevere/last-backup-success | Backup sentinel (synced) |
| src/core/services/llm_metrics.py | addr="127.0.0.1" |

---

## Cron Jobs

| Schedule | Job | Output |
|----------|-----|--------|
| Every 5 min | Health check | journalctl |
| Daily 02:00 | Backup | ~/.hermes/logs/backup.log |
| Daily 08:00 | SLO Scorecard | ~/.hermes/logs/slo-scorecard.md |

---

## Skipped (per Faiz)

- ~~Rotate all 40+ credentials~~ — deferred
- Cloudflare R2 secondary backup — no credentials provided

---

## Status: ✅ COMPLETE — 12/12 PASS (verified iteration 3)
