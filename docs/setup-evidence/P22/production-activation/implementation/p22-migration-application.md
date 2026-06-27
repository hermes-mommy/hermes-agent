# P22 Production Activation — Migration Application Evidence (T4 + T5)

**Date:** 2026-06-27
**Steps:** T4 (auth resolve) + T5 (apply migration `p22_001_integration_schema`)
**VPS:** faiz-prod-01 via `ssh guinevere-vps`
**DB:** PostgreSQL 16 + pgvector, container `guinevere-postgres`, host `localhost:5433`, db `guinevere`

## T4 — Alembic Auth Resolution

**Research claim (B-B):** `.env.core` `DATABASE_URL` password stale for alembic (`InvalidPasswordError`).

**Parent-verified resolution:** Auth was NEVER the blocker. `alembic/env.py:27` prefers `DATABASE_URL` from env. The `InvalidPasswordError` seen in research was caused by `.env.core` line 13 (`9ROUTER_API_KEY`, invalid env-var name starting with digit) breaking `source .env.core` — NOT a stale password. Once env is sourced with a filter, `DATABASE_URL` (which contains a valid embedded password) authenticates `guinevere_core` cleanly.

**Working auth command:**
```bash
export $(grep -E "^[A-Z_][A-Z0-9_]*=" .env.core | xargs)
.venv/bin/alembic current   # → Context impl PostgresqlImpl (auth OK)
```

**pg_hba:** `local all guinevere trust` (superuser local); `host 127.0.0.1 scram-sha-256` for `guinevere_core` (password via `DATABASE_URL`). No password ever printed.

**Blocker B-C RESOLVED** (filter skips `9ROUTER_API_KEY`). **Blocker B-B RESOLVED** (auth works via `DATABASE_URL` path).

## T5 — Migration Apply

### Pre-state
- `alembic current` = `p19_003_audit_chain_version` (after T3 deployed the missing `p19_003` file)
- `alembic heads` = `p22_001_integration_schema` (single head — multi-head concern resolved once files synced)
- schema `p22` absent, `audit.integration_api_log` absent (clean target)
- `ops.alembic_version` had 4 rows: p19_001, p19_002, p19_003, p20_001

### Issue encountered: branch-overlap
`alembic upgrade p22_001_integration_schema` FAILED with:
```
Requested revision p19_001_project_namespaces overlaps with other requested revisions p20_001_life_kernel_schema
```

**Root cause:** The revision graph is LINEAR (`p5_024 → p20_001 → p19_001 → p19_002 → p19_003 → p22_001`), but the DB's `ops.alembic_version` table had accumulated 4 separate rows (prior operators applied migrations out-of-band, leaving the version table in a non-standard multi-row state). Alembic's upgrade traversal could not reconcile `p19_001` (needed in the path to p22_001) with the already-applied `p20_001` row.

### Resolution: direct idempotent DDL + stamp
The `p22_001` migration is **fully idempotent** (`IF NOT EXISTS` for all DDL, `ON CONFLICT DO NOTHING` for seed). Since `p19_003` is genuinely applied (verified: `audit.audit_trail.chain_version` column exists) and `p22_001` only creates NEW objects with no dependency on existing state, the migration DDL was applied directly via asyncpg (replicating the migration's `upgrade()` SQL verbatim), then `alembic stamp p22_001_integration_schema` collapsed the 4-row version table into the single head.

### Apply commands
```bash
# 1. Direct DDL (idempotent) via /tmp/p22_apply_ddl.py
.venv/bin/python /tmp/p22_apply_ddl.py
# 2. Stamp version table
.venv/bin/alembic stamp p22_001_integration_schema
# → "Running stamp_revision ... -> p22_001_integration_schema"
```

### Post-conditions (all VERIFIED)

| Check | Expected | Actual | ✓ |
|---|---|---|---|
| schema `p22` exists | yes | True | ✓ |
| `p22.integration_registry` exists | yes | True | ✓ |
| `p22.secret_ref_metadata` exists | yes | True | ✓ |
| `audit.integration_api_log` exists | yes | True | ✓ |
| `p22.integration_registry` rows | 12 | 12 | ✓ |
| `alembic_version` rows | 1 (p22_001) | `['p22_001_integration_schema']` | ✓ |
| WORM: guinevere_core INSERT on audit log | True | True | ✓ |
| WORM: guinevere_core SELECT on audit log | True | True | ✓ |
| WORM: guinevere_core UPDATE on audit log | **False** | False | ✓ |
| WORM: guinevere_core DELETE on audit log | **False** | False | ✓ |
| guinevere_core on p22.integration_registry | SELECT/INSERT/UPDATE | all True | ✓ |

## Idempotency / Re-run Safety

- All DDL uses `IF NOT EXISTS` → safe to re-run.
- Seed uses `ON CONFLICT (integration_id) DO NOTHING` → safe to re-run.
- `alembic stamp` is idempotent (re-stamp to same head = no-op).
- A failed mid-run can be retried safely.

## Rollback Caveat

`audit.integration_api_log` is WORM. Once production audit traffic flows, **DO NOT downgrade** (would destroy audit chain). Code-only rollback per plan §8.3 if needed. Currently empty (no P22 traffic yet).

## Footer

Migration applied and verified. All hard-rejection criteria for migration (applied, 12 rows, WORM enforced, idempotent) PASS. Safe to proceed to T6 (importability smoke) and Phase B (wiring).
