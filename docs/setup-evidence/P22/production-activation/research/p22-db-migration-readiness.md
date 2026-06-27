# P22 DB Migration Readiness Audit — `p22_001_integration_schema`

**Auditor:** DB MIGRATION READINESS AUDITOR (read-only, sub-agent)
**Date:** 2026-06-27
**Scope:** Whether `p22_001_integration_schema` is safe to apply to production DB
**Mode:** READ-ONLY — no migration applied, no service restarted, no secrets printed

---

## 1. Summary Verdict

**VERDICT: HOLD — code/sync blocker**

The migration **p22_001_integration_schema.py** is **structurally ready** to apply:
- Chain is clean (down_revision = `p19_003_audit_chain_version`).
- All DDL is **idempotent** (`IF NOT EXISTS` for schemas, tables, indexes; `ON CONFLICT DO NOTHING` for seed).
- WORM enforcement (`REVOKE UPDATE,DELETE`) is in place for `audit.integration_api_log`.
- No pre-existing `p22` schema, no pre-existing `audit.integration_api_log`, no pre-existing `p22.integration_registry` on prod — **clean target**.
- DB role `guinevere_core` exists with 30 connections.
- DB connection string is intact (host=`localhost:5433`, db=`guinevere`).
- Backup artefacts already exist in `/home/guinevere/backups/` (pattern: `pre-p20-db-YYYYMMDD-HHMMSS.sql`).

**However, the apply is BLOCKED by a code-sync issue:**

| # | Blocker | Detail |
|---|---------|--------|
| 1 | **VPS repo missing migration files** | `/home/guinevere/code/guinevere/alembic/versions/` is **missing** both `p19_003_audit_chain_version.py` AND `p22_001_integration_schema.py`. The local working repo on the VPS is out of sync with prod DB AND with the operator's primary local repo (`C:\Users\faizz\guinevere`). |
| 2 | **`alembic heads` on VPS reports `p19_002` (single head)** | Because VPS is missing the `p19_003` file, the on-disk chain is `p19_001 → p19_002 → p20_001` (with `p20_001` branching from `p5_024`). A naive `alembic upgrade head` on the VPS would not apply `p22_001` at all. |
| 3 | **DB already shows `p19_003` and `p20_001` as applied** | `ops.alembic_version` contains 4 rows: `p19_001`, `p19_002`, `p19_003`, `p20_001`. The DB is ahead of the on-disk code, which means the code must be re-synced *before* any further `alembic upgrade`. |

**Required action before apply:** `git pull` (or equivalent sync) on the VPS to bring `p19_003_audit_chain_version.py` and `p22_001_integration_schema.py` into `/home/guinevere/code/guinevere/alembic/versions/`. After that, `alembic upgrade head` will run `p22_001` cleanly (idempotent on re-run).

Once code is synced, this migration is **READY** to apply.

---

## 2. Migration Chain (local repo at `C:\Users\faizz\guinevere`)

```
p19_001_project_namespaces
   └── p19_002_project_id_not_null
          └── p19_003_audit_chain_version     ← revises
                 └── p22_001_integration_schema (head)
```

Confirmed in `alembic/versions/p22_001_integration_schema.py`:
- `revision: str = "p22_001_integration_schema"`
- `down_revision: Union[str, Sequence[str], None] = "p19_003_audit_chain_version"`
- `branch_labels = None`, `depends_on = None` — single linear chain, no branch conflicts.

`p19_003_audit_chain_version.py` (read in full) shows it adds `chain_version SMALLINT NOT NULL DEFAULT 1` to `audit.audit_trail` plus an index. Idempotent (`ADD COLUMN IF NOT EXISTS`, `CREATE INDEX IF NOT EXISTS`).

---

## 3. Idempotency Assessment

| DDL Operation | Idempotent? | Notes |
|---------------|-------------|-------|
| `CREATE SCHEMA IF NOT EXISTS p22;` | YES | Safe on re-run. |
| `CREATE TABLE IF NOT EXISTS audit.integration_api_log (...)` | YES | Safe on re-run. |
| `CREATE INDEX IF NOT EXISTS ix_integration_api_log_*` (4 indexes) | YES | Safe on re-run. |
| `REVOKE UPDATE, DELETE ON audit.integration_api_log FROM guinevere_core;` | YES | Revoking a permission not granted is a no-op. |
| `GRANT INSERT, SELECT ON audit.integration_api_log TO guinevere_core;` | YES | Granting twice is a no-op. |
| `CREATE TABLE IF NOT EXISTS p22.integration_registry (...)` | YES | Safe on re-run. |
| `CREATE INDEX IF NOT EXISTS ix_integration_registry_enabled` | YES | Safe on re-run. |
| `GRANT SELECT, INSERT, UPDATE ON p22.integration_registry TO guinevere_core;` | YES | No-op on re-run. |
| `CREATE TABLE IF NOT EXISTS p22.secret_ref_metadata (...)` | YES | Safe on re-run. |
| `GRANT SELECT, INSERT, UPDATE ON p22.secret_ref_metadata TO guinevere_core;` | YES | No-op on re-run. |
| `INSERT INTO p22.integration_registry (...) ON CONFLICT (integration_id) DO NOTHING;` | YES | 12 integration rows, conflict-tolerant. |

**Conclusion:** Migration is **fully idempotent**. A failed mid-run (e.g., network blip, lock conflict) can be safely retried.

---

## 4. VPS Alembic State

| Check | Result | Source |
|-------|--------|--------|
| `alembic.ini` location | `/home/guinevere/code/guinevere/alembic.ini` | `find` |
| `alembic` CLI | `.venv/bin/alembic` (not on PATH by default) | manual path required |
| DB URL env var NAME | `DATABASE_URL` (in `.env.core`) | grep |
| DB URL driver/host | `postgresql+asyncpg://guinevere_core:***@localhost:5433/guinevere` | `alembic.ini` (password redacted) |
| `alembic current` | Failed: `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "guinevere_core"` | psql worked when `PGPASSWORD` was set; `.env.core` is the source of truth but `set -a; source .env.core; set +a` fails because line 13 (`9ROUTER_API_KEY=...`) is not a valid env var name (starts with digit) and breaks sourcing. **Workaround:** `export $(grep -v '^#' .env.core | grep -v '^9ROUTER' | grep -E '^[A-Z_]+=' | xargs)` or run `alembic` with explicit `DATABASE_URL` from a wrapper script. |
| `alembic heads --verbose` | Single head reported: `p19_002_project_id_not_null`, parent: `p19_001_project_namespaces` | `alembic heads --verbose` |
| `alembic history` | Shows `p20_001` branching off `p5_024` AND `p19_002` branching off `p19_001` — i.e. **two parallel branches** in VPS code: `p5_024 → p20_001` and `p19_001 → p19_002`. VPS is missing `p19_003` and `p22_001` migration files. | `alembic history` |
| `ops.alembic_version` (DB) | 4 rows: `p19_001`, `p19_002`, `p19_003`, `p20_001` | `SELECT version_num FROM ops.alembic_version` |
| `audit.audit_trail.chain_version` | Column exists (`smallint`) | `information_schema.columns` |

**Multiple heads / branch conflict:** YES at the filesystem level on the VPS — `p20_001` and `p19_002` are two parallel heads (both terminate a branch). This is the state of VPS code, not a conflict introduced by `p22_001`. The DB has recorded `p20_001` and `p19_003` as applied, so the previous operator must have applied `p19_003` via a different path (likely a hot-fix or direct psql) and not committed the file to the repo. **This is a code-state inconsistency between VPS local code and the actual prod DB.**

After VPS is synced with the operator's local repo, the chain will be:
- Branch 1: `p5_024 → p20_001` (no further heads)
- Branch 2: `p19_001 → p19_002 → p19_003 → p22_001` (head = `p22_001`)

The two branches remain separate (no merge point in the repo). This is **acceptable** for `alembic upgrade head` if both `p20_001` and `p22_001` are already applied — but if `p22_001` is the new target, only branch 2 will advance. No multiple-head conflict is introduced by this migration.

---

## 5. Table Pre-existence Check

| Target | Exists? | Notes |
|--------|---------|-------|
| Schema `p22` | **NO** | `\dn p22` returns 0 rows. Will be created by migration. |
| Schema `audit` | YES | Owned by `guinevere` (the superuser). |
| Table `audit.integration_api_log` | **NO** | Will be created by migration. |
| Table `p22.integration_registry` | **NO** | Will be created by migration. |
| Table `p22.secret_ref_metadata` | **NO** | Will be created by migration. |
| `audit.audit_trail.chain_version` column | YES | Confirms `p19_003` actually ran on prod (despite file being missing from VPS code). |

**No name collisions. No accidental re-creation. No data preservation concerns** (WORM table is empty pre-migration).

---

## 6. DB Role Check

| Check | Result |
|-------|--------|
| Role `guinevere_core` exists | YES (30 connections attribute) |
| Role used by migration's GRANT/REVOKE | `guinevere_core` (matches env URL username) |
| Existing grants on `audit.audit_trail` (precedent WORM table) | `guinevere_core` has `INSERT, SELECT, UPDATE, DELETE, TRUNCATE, REFERENCES, TRIGGER` — full DML. (This is the *current* state; the new `audit.integration_api_log` will start with INSERT/SELECT only via the migration's explicit `REVOKE UPDATE, DELETE` and `GRANT INSERT, SELECT`.) |
| Existing grants on `audit.*` other tables | `guinevere_core` has `DELETE, INSERT, REFERENCES, SELECT, TRIGGER, TRUNCATE, UPDATE` (full DML on other audit tables — expected, only the new table is WORM). |

**No role-creation required. Migration's REVOKE will work on a freshly-created table with default public grants.**

---

## 7. Downgrade / Rollback Behavior

`p22_001` downgrade (in `alembic/versions/p22_001_integration_schema.py`):
1. `DROP TABLE IF EXISTS p22.secret_ref_metadata;`
2. `DROP TABLE IF EXISTS p22.integration_registry;`
3. `DROP TABLE IF EXISTS audit.integration_api_log;`  ← WORM table dropped last
4. Schema `p22` is **not** dropped (other objects may exist in the future).

**Downgrade risks:**
- The `audit.integration_api_log` table is **WORM** (intended for production audit data). Once production traffic is flowing, `downgrade()` would **destroy audit history** with no recovery short of `pg_restore`.
- The `ON CONFLICT DO NOTHING` seed of 12 integration rows will be lost; re-running `upgrade` will re-insert them (still idempotent).
- No data-archive step is in the downgrade — manual `pg_dump -t audit.integration_api_log` is required **before** any downgrade post-production-traffic.
- The migration does **not** drop the `p22` schema (deliberate, see comment in code). Downgrade leaves an empty schema behind — cosmetic only.

**Rollback strategy: DO NOT downgrade `p22_001` once audit traffic is flowing. The migration is forward-only in practice.**

`p19_003` downgrade is safe (just `DROP INDEX` + `DROP COLUMN`), and the chain in front of `p22_001` is clean.

---

## 8. Risks

| # | Risk | Severity | Mitigation |
|---|------|----------|------------|
| 1 | **VPS code is missing `p19_003` and `p22_001` migration files** — naive `alembic upgrade head` will not apply `p22_001`. | **HIGH** (blocker) | `git pull` on VPS to sync the two missing files. Verify with `ls alembic/versions/p22_001* alembic/versions/p19_003*` before apply. |
| 2 | **`.env.core` has invalid env-var line 13** (`9ROUTER_API_KEY=...` starts with digit). Sourcing `.env.core` with `set -a; source` will abort the migration script. | MEDIUM | Source env with filter: `export $(grep -E '^[A-Z_][A-Z0-9_]*=' .env.core | xargs)` (skips the bad line) or use `env $(grep ... | xargs) alembic ...`. |
| 3 | **Migration runs in a transaction** (per `env.py` `context.begin_transaction()`). If the seed INSERT fails on conflict edge case, the whole upgrade is rolled back. Idempotent retry is safe. | LOW | Acceptable. |
| 4 | **No pre-existing data in any of the 3 target tables** — there is no risk of data loss. | NONE (positive) | n/a |
| 5 | **`audit.audit_trail` (precedent) has UPDATE/DELETE/TRUNCATE grants** to `guinevere_core`. The migration's REVOKE on the new table is per-table and does not affect `audit.audit_trail`. No risk of collateral lockout. | LOW | Acceptable; matches design intent. |
| 6 | **Two branch heads in VPS code** (`p19_002` and `p20_001`). After sync, branch 2 will extend to `p22_001`. `alembic upgrade head` will refuse to run with multiple heads unless they share a merge point. Need to confirm after sync whether `alembic upgrade head` would be ambiguous. | MEDIUM | Use explicit `alembic upgrade p22_001_integration_schema` (single-revision target) instead of `head` to avoid ambiguity. |
| 7 | **No pre-migration `pg_dump` is in the migration itself.** A failed apply could leave partial state on a non-IF-NOT-EXISTS operation. (All DDL here is IF-NOT-EXISTS, so this is moot.) | LOW | Take a manual `pg_dump` before apply as belt-and-braces. |
| 8 | **`ops.alembic_version` is multi-row** (4 rows). This is non-standard (alembic normally keeps a single row). The presence of `p19_003` and `p20_001` rows means previous operator(s) hand-inserted these. Re-running `alembic upgrade head` will respect the version table and not re-apply. | LOW (informational) | No action needed; behavior is correct. |

---

## 9. Required Pre-Commands (Backup)

Run **before** any `alembic upgrade`. The migration itself has no built-in backup step.

```bash
# 1. Sync VPS code to match local repo
cd /home/guinevere/code/guinevere
git pull   # or rsync / copy the two missing migration files

# 2. Verify the two missing files are present
ls -la alembic/versions/p19_003_audit_chain_version.py \
       alembic/versions/p22_001_integration_schema.py

# 3. Pre-flight: confirm pre-conditions (idempotent, read-only)
PGPASSWORD="$DB_PASS" psql -h localhost -p 5433 -U guinevere_core -d guinevere \
  -c "\dn p22" -c "\dt audit.integration_api_log" \
  -c "\dt p22.integration_registry" -c "\dt p22.secret_ref_metadata"
# EXPECT: schema p22 absent, all 3 tables absent

# 4. Take a logical backup (full DB, ~few hundred MB on prod)
TS=$(date -u +%Y%m%d-%H%M%S)
pg_dump -h localhost -p 5433 -U guinevere_core -d guinevere \
  -Fc -f /home/guinevere/backups/pre-p22-$TS.dump

# 5. Specifically archive the WORM audit table (belt-and-braces)
pg_dump -h localhost -p 5433 -U guinevere_core -d guinevere \
  -t audit.audit_trail -Fc \
  -f /home/guinevere/backups/pre-p22-audit-trail-$TS.dump

# 6. Snapshot the alembic version table (small, fast)
PGPASSWORD="$DB_PASS" psql -h localhost -p 5433 -U guinevere_core -d guinevere \
  -c "COPY (SELECT * FROM ops.alembic_version ORDER BY version_num) \
      TO '/home/guinevere/backups/alembic-version-pre-p22-$TS.csv' CSV HEADER"
```

> **Note:** `DB_PASS` must be extracted from `.env.core` (or operator's secrets manager) and **never** echoed. The 9Router key line in `.env.core` is not a valid env-var name and breaks naïve `source .env.core` — filter it.

---

## 10. Recommended Apply Command

After the code sync and backup are complete, the **single safest apply command** is:

```bash
cd /home/guinevere/code/guinevere
# Source env without the bad 9ROUTER_API_KEY line
export $(grep -E '^[A-Z_][A-Z0-9_]*=' .env.core | xargs)

# Optional: dry-run check (will show SQL without executing)
.venv/bin/alembic upgrade p22_001_integration_schema --sql 2>&1 | head -200

# Actual apply (single revision, no head ambiguity)
.venv/bin/alembic upgrade p22_001_integration_schema 2>&1 | tee -a /home/guinevere/logs/migration-p22-$(date -u +%Y%m%d-%H%M%S).log

# Verify post-conditions
PGPASSWORD="$DB_PASS" psql -h localhost -p 5433 -U guinevere_core -d guinevere -c "
  SELECT version_num FROM ops.alembic_version ORDER BY version_num;
" -c "\dn p22" -c "\dt p22.*" -c "
  SELECT count(*) AS registry_rows FROM p22.integration_registry;
" -c "
  SELECT has_table_privilege('guinevere_core', 'audit.integration_api_log', 'UPDATE') AS has_update,
         has_table_privilege('guinevere_core', 'audit.integration_api_log', 'DELETE') AS has_delete,
         has_table_privilege('guinevere_core', 'audit.integration_api_log', 'INSERT') AS has_insert,
         has_table_privilege('guinevere_core', 'audit.integration_api_log', 'SELECT') AS has_select;
"
# EXPECT:
#   - 5 rows in ops.alembic_version: p19_001, p19_002, p19_003, p20_001, p22_001
#   - schema p22 exists
#   - p22.integration_registry and p22.secret_ref_metadata exist
#   - registry_rows = 12
#   - has_update=f, has_delete=f, has_insert=t, has_select=t  (WORM enforced)
```

`alembic upgrade p22_001_integration_schema` is preferred over `alembic upgrade head` because:
- It explicitly names the target revision (no ambiguity if multiple branches exist).
- It is single-revision (one transaction, easy to roll back if any of the IF-NOT-EXISTS DDL fails — though they shouldn't).
- It is forward-only and idempotent on re-run.

---

## 11. Blockers

1. **CODE SYNC BLOCKER (HIGH):** VPS `/home/guinevere/code/guinevere/alembic/versions/` is **missing** `p19_003_audit_chain_version.py` and `p22_001_integration_schema.py`. Apply will not work until these are present. **Action:** `git pull` (or copy from operator's local repo) on the VPS.

2. **MINOR — `.env.core` line 13** has invalid env-var name `9ROUTER_API_KEY=...` (starts with digit). `source .env.core` will fail. **Action:** filter it out or quote-key it in a wrapper script.

3. **NOT A BLOCKER (informational):** `ops.alembic_version` is multi-row (4 rows) — non-standard but consistent with prod reality. `alembic upgrade` will respect the version table and not re-apply.

4. **NOT A BLOCKER:** `p20_001` is a separate branch off `p5_024` in VPS code. After sync, this branch will have no further heads (head = `p20_001` on that branch). Branch 2 head will be `p22_001`. Use `alembic upgrade p22_001_integration_schema` (explicit) to avoid head-resolution ambiguity.

---

## 12. Quick-Reference Facts (redacted)

- **DB URL env var:** `DATABASE_URL` (in `.env.core`)
- **DB URL driver/host:** `postgresql+asyncpg://guinevere_core:***@localhost:5433/guinevere` (password not printed)
- **alembic.ini:** `/home/guinevere/code/guinevere/alembic.ini`
- **alembic binary:** `/home/guinevere/code/guinevere/.venv/bin/alembic`
- **project root:** `/home/guinevere/code/guinevere`
- **backup dir:** `/home/guinevere/backups/` (existing: `pre-p20-db-20260622-231459.sql`, `alembic-version-backup-20260622-*.sql`)
- **migration file (new):** `alembic/versions/p22_001_integration_schema.py` (revises `p19_003_audit_chain_version`)
- **role used:** `guinevere_core` (30 connections)
- **PostgreSQL version:** 16.14 (Ubuntu 16.14-0ubuntu0.24.04.1)
- **DB pre-state:** schema `p22` absent, all 3 target tables absent — clean
- **DB chain applied (rows in `ops.alembic_version`):** `p19_001, p19_002, p19_003, p20_001`
- **DB chain expected post-apply (rows in `ops.alembic_version`):** `p19_001, p19_002, p19_003, p20_001, p22_001`
- **VPS code head (currently):** `p19_002_project_id_not_null`
- **VPS code head (after sync):** `p22_001_integration_schema` (and `p20_001_life_kernel_schema` on the other branch)
- **idempotent:** YES (all DDL is IF NOT EXISTS, GRANT/REVOKE are no-ops on re-run, seed uses ON CONFLICT DO NOTHING)
- **WORM enforced on new table:** YES (`REVOKE UPDATE,DELETE FROM guinevere_core` + `GRANT INSERT,SELECT TO guinevere_core`)

---

## 13. Final Verdict

**READY — after one prerequisite: code sync (`git pull`) on the VPS.**

The migration itself is **structurally sound, fully idempotent, with clean WORM enforcement and no name collisions**. The only reason the verdict is HOLD rather than READY is that the VPS working copy is missing the migration files, which would cause `alembic upgrade head` to be a no-op for `p22_001`. Sync the code, take a `pg_dump`, run the explicit single-revision upgrade, and the migration will succeed.

Do not downgrade `p22_001` once production audit traffic begins — the WORM `audit.integration_api_log` would be destroyed.
