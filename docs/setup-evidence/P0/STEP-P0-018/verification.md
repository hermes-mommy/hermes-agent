# STEP-P0-018 — Verification

**Step**: P0-018 — PostgreSQL Hardening (pg_hba.conf, Connection Limits, Logging)
**Date**: 2026-05-31
**Status**: PASS, independent auditor gate passed

---

## 1. What Was Done
Hardened PostgreSQL authentication from all-trust to scram-sha-256 for all non-admin access. Set per-role connection limits. Enabled connection and slow-query logging. Reloaded configuration without container restart.

## 2. Files Changed
**Remote (VPS)**:
- `/home/guinevere/data/postgres/pg_hba.conf` — hardened (backup: .pre-P0-018)
- `postgresql.auto.conf` — ALTER SYSTEM settings applied

**Local**:
- No local files changed

## 3. Validation Results

### pg_hba.conf (Final)
```
# Superuser admin via docker exec (Unix socket)
local   all     guinevere     trust
# All other local — SCRAM required
local   all     all           scram-sha-256
# Loopback TCP
host    all     all           127.0.0.1/32    scram-sha-256
host    all     all           ::1/128         scram-sha-256
# PgBouncer (guinevere-net Docker subnet)
host    all     all           172.28.0.0/16   scram-sha-256
# Replication (preserved)
local   replication     all     trust
host    replication     all     127.0.0.1/32  scram-sha-256
host    replication     all     ::1/128       scram-sha-256
# Remote fallback
host    all     all     all     scram-sha-256
```

### Connection Limits
```
guinevere_backup:       5
guinevere_core:        30
guinevere_readonly:    15
guinevere_scheduler:   10
guinevere_surveillance: 10
```

### Log Settings
```
log_connections = on
log_disconnections = on
log_statement = ddl
log_min_duration_statement = 1s
```

### Docker Exec Superuser Access
```
PASS: docker exec guinevere-postgres psql -U guinevere → connects (local trust)
```

## 4. Evidence Artifacts
- `pg-hba.txt` — final pg_hba.conf contents
- `pg-settings.txt` — connection limits + log settings
- `aizanta-post-check.md` — Aizanta health verification
- `p0-018-summary.md` — summary and caveats

## 5. Shared VPS Impact
- Aizanta 5/5 containers healthy
- Protected ports unchanged: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432
- guinevere-postgres reloaded via pg_ctl (no restart)
- No Aizanta Docker networks/containers touched

## 6. ADR Compliance
- ADR-018 (Defense-in-Depth): Authentication hardened, logging enabled
- ADR-027 (PostgreSQL): SCRAM-SHA-256 enforcement, connection limits, per-role isolation

## 7. AC Reference
- AC-SEC-001: scram-sha-256 auth enforced for all non-admin access
- AC-CORE-001: PostgreSQL accessible with proper auth only

## 8. Rollback / Re-run Safety
- Backup: /home/guinevere/data/postgres/pg_hba.conf.pre-P0-018
- To rollback: cp pg_hba.conf.pre-P0-018 pg_hba.conf && docker exec -u postgres guinevere-postgres pg_ctl reload
- ALTER SYSTEM settings: reset via ALTER SYSTEM RESET
- Connection limits: ALTER USER ... CONNECTION LIMIT -1

## 9. Design Decisions / Caveats
- guinevere superuser retains local trust for docker exec admin convenience
- SSL deferred (internal Docker network only, no external PostgreSQL exposure)
- PgBouncer subnet 172.28.0.0/16 added preemptively (PgBouncer in P0-019)
- Container reloaded via pg_ctl instead of restart (no downtime)

## 10. Evidence Gate
| Gate | Status |
|---|---|
| Parent verification | PASS |
| LSP diagnostics | Clean |
| Secret scan | No secrets exposed |
| Aizanta guardrails | 5/5 healthy |
| Independent auditor gate | PASS (2 doc findings fixed, re-audit confirmed) |
| Auditor report | audit-reports/P0/STEP-P0-018/step-p0-018-auditor-report.md |

## 11. Footer
- Source task: STEP-P0-018
- Implementer: Guinevere (Sisyphus agent)
- Auditor: Pending (bg task)
- Date: 2026-05-31