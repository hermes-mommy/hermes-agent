# STEP-P0-019 — Verification

**Step**: P0-019 — PgBouncer Connection Pooling
**Date**: 2026-05-31
**Status**: PASS, independent auditor gate passed

---

## 1. What Was Done
Deployed PgBouncer as a Docker container (percona/percona-pgbouncer:1.25.2) on guinevere-net (172.28.0.3) listening on 127.0.0.1:5434. Configured auth_file mode with SCRAM-SHA-256 hashes for 6 PostgreSQL users extracted from pg_authid.rolpassword. PgBouncer proxies connections to guinevere-postgres:5432 with pool_mode=transaction, default_pool_size=20.

## 2. Files Changed
**Local**:
- `docs/setup-evidence/P0/STEP-P0-019/` — evidence artifacts (NEW)

**Remote (VPS)**:
- `/home/guinevere/config/pgbouncer/pgbouncer.ini` — PgBouncer config
- `/etc/pgbouncer/userlist.txt` — inside container, 6 SCRAM hashes

## 3. Validation Results
### Container
```
guinevere-pgbouncer Up 2 minutes 127.0.0.1:5434->5432/tcp
```

### Config
```
[databases]
guinevere = host=guinevere-postgres port=5432 dbname=guinevere

[pgbouncer]
listen_addr = 0.0.0.0
listen_port = 5432
auth_type = scram-sha-256
auth_file = /etc/pgbouncer/userlist.txt
pool_mode = transaction
default_pool_size = 20
max_db_connections = 100
max_client_conn = 500
```

### Connection Tests (via PgBouncer)
```
guinevere_core:     PASS (current_user=guinevere_core, current_database=guinevere)
guinevere_readonly: PASS (current_user=guinevere_readonly)
```

### userlist.txt
6 users: guinevere, guinevere_core, guinevere_surveillance, guinevere_scheduler, guinevere_readonly, guinevere_backup. All SCRAM-SHA-256 hashes match pg_authid.rolpassword.

## 4. Evidence Artifacts
- `pgbouncer-status.txt` — container status, config, connection test
- `aizanta-post-check.md` — Aizanta health verification
- `p0-019-summary.md` — summary and caveats

## 5. Shared VPS Impact
- Aizanta 5/5 containers healthy: bot, nginx, frontend, postgres:16-alpine, redis
- Protected ports unchanged: 127.0.0.1:6379, 100.94.104.22:80, 127.0.0.1:5432
- New port 127.0.0.1:5434 added (PgBouncer, loopback-only)
- No Aizanta Docker networks/containers/volumes touched
- PgBouncer on separate Docker network (guinevere-net) from Aizanta

## 6. ADR Compliance
- ADR-027: PostgreSQL connection pooling with PgBouncer

## 7. AC Reference
- AC-CORE-001: Connection pooling active for guinevere database

## 8. Rollback / Re-run Safety
- Remove container: `docker stop guinevere-pgbouncer && docker rm guinevere-pgbouncer`
- Re-create: `docker run -d --name guinevere-pgbouncer --network guinevere-net --ip 172.28.0.3 -p 127.0.0.1:5434:5432 -v /home/guinevere/config/pgbouncer/pgbouncer.ini:/etc/pgbouncer/pgbouncer.ini percona/percona-pgbouncer:1.25.2`
- userlist.txt must be regenerated from pg_authid if passwords change

## 9. Design Decisions / Caveats
- auth_file mode chosen over auth_query (auth_query failed with SCRAM negotiation)
- admin_users set to guinevere (superuser) only
- No SSL between PgBouncer and PostgreSQL (same Docker network)
- userlist.txt must be regenerated if PostgreSQL passwords are rotated

## 10. Evidence Gate
| Gate | Status |
|---|---|
| Parent verification | PASS |
| LSP diagnostics | Clean |
| Secret scan | No plaintext in evidence |
| Aizanta guardrails | 5/5 healthy |
| Independent auditor gate | PASS |

**Auditor report**: `audit-reports/P0/STEP-P0-019/step-p0-019-auditor-report.md`
**Auditor verdict**: PASS — PgBouncer container running, SCRAM auth, transaction pooling, guinevere-net isolation, Aizanta unaffected. 3 non-blocking findings: port typo (fixed), userlist.txt root ownership (functional), verbose logging (dev-mode).

## 11. Footer
- Source task: STEP-P0-019
- Implementer: Guinevere (Sisyphus agent)
- Auditor: bg_f51bf16e (PASS)
- Date: 2026-05-31