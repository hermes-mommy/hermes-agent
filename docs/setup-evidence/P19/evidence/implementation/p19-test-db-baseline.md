# P19 Test Database Baseline Runbook

## Method

Establish `guinevere_p19_test` at alembic head `p20_001_life_kernel_schema` by running migrations
against an isolated test database, using a dedicated `p19_test_runner` role with password auth
over TCP on port 5433.

## Prerequisites

- VPS repo at `/home/guinevere/code/guinevere` with venv at `.venv/` (Python 3.12)
- PostgreSQL 16 container `guinevere-postgres` running on `127.0.0.1:5433`
- Existing empty database `guinevere_p19_test` (owned by `guinevere` superuser)
- Two SSH jump hosts configured:
  - `ssh guinevere-root` — root access for `docker exec` (container SQL)
  - `ssh guinevere-vps` — `guinevere` user, runs alembic from repo venv

## Step-by-Step

### 1. Create the test runner role

```bash
ssh guinevere-root
```

```sql
-- inside docker container
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "CREATE ROLE p19_test_runner WITH LOGIN PASSWORD 'p19_test_local_only';"

docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "GRANT ALL PRIVILEGES ON DATABASE guinevere_p19_test TO p19_test_runner;"

docker exec guinevere-postgres psql -U p19_test_runner -d guinevere_p19_test \
  -c "GRANT ALL ON SCHEMA public TO p19_test_runner;"

docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
  -c "ALTER DATABASE guinevere_p19_test OWNER TO p19_test_runner;"

docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
  -c "GRANT CREATE ON DATABASE guinevere_p19_test TO p19_test_runner;"
```

> **Security note:** `p19_test_local_only` is a throwaway local-test password. The role
> `p19_test_runner` owns only the test database (`guinevere_p19_test`). It has no access
> to `guinevere_core` and is scoped to the non-production database. When done, drop the
> role with `DROP ROLE p19_test_runner;`.

### 2. Create required schemas (alembic version table schema)

Alembic's `version_table_schema=ops` must exist before migrations can start.

```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
  -c "CREATE SCHEMA IF NOT EXISTS ops AUTHORIZATION p19_test_runner;"
```

### 3. Install required PostgreSQL extensions

The migration chain uses TimescaleDB (`create_hypertable`) and pgvector (`VECTOR` type).

```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
  -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"

docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
  -c "CREATE EXTENSION IF NOT EXISTS vector;"
```

### 4. Run alembic upgrade

```bash
ssh guinevere-vps

cd /home/guinevere/code/guinevere

DATABASE_URL="postgresql+asyncpg://p19_test_runner:p19_test_local_only@127.0.0.1:5433/guinevere_p19_test" \
  .venv/bin/alembic upgrade p20_001_life_kernel_schema
```

`alembic/env.py` (lines 27-29) reads `DATABASE_URL` from the environment and overrides the
`sqlalchemy.url` in alembic.ini. No password injection or SOPS decryption needed.

Expected output: 13 migrations run, ending at `p20_001_life_kernel_schema`.

### 5. Remove the baseline migration bug (if replaying from scratch)

The file `alembic/versions/p5_add_loop_indexes.py` has a bug: it uses `op.text()` which
does not exist. Replace with `sa.text()` and add `import sqlalchemy as sa`:

```python
"""add_loop_indexes — add performance indexes to loop_instances.

Adds indexes on status, task_id (FK), and started_at (temporal queries).
"""
import sqlalchemy as sa
from alembic import op
# ... rest unchanged, but replace [op.text("started_at DESC")]
# with [sa.text("started_at DESC")]
```

This fix was applied on the VPS repo at `/home/guinevere/code/guinevere/alembic/versions/p5_add_loop_indexes.py`.
If re-cloning, apply the same patch.

## Verification

### Alembic version

```bash
ssh guinevere-root \
  "docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
     -tAc \"SELECT version_num FROM ops.alembic_version;\""
```

Expected: `p20_001_life_kernel_schema`

### Table count

```bash
ssh guinevere-root \
  "docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
     -tAc \"SELECT count(*)::text FROM information_schema.tables
            WHERE table_schema NOT IN ('information_schema','pg_catalog',
                                       '_timescaledb_cache','_timescaledb_catalog',
                                       '_timescaledb_config','_timescaledb_internal',
                                       'timescaledb_experimental','timescaledb_information');\""
```

Expected: 58 user tables across 14 guinevere schemas
(agents=3, audit=3, consent=3, extensions=3, financial=4, gamification=6,
life_kernel=3, memory=9, ops=5, persona=5, projects=4, security=3, social=3, surveillance=4)

### App schemas present

```text
agents, audit, consent, extensions, financial, gamification,
life_kernel, memory, ops, persona, projects, security, social, surveillance
```

Each schema should have its expected tables (e.g., `life_kernel` has `life_mind_state`,
`heartbeat_record`, `domain_mind_state`).

## Isolation from Production

- `guinevere_p19_test` is a separate database on the same cluster.
- The `p19_test_runner` role is a test-only superuser that owns only the test database.
- Production `guinevere_core` was **not modified**. No tables, schemas, roles, or data
  were changed in `guinevere_core`.
- The production DB (`guinevere_core`) does NOT have an `ops.alembic_version` table —
  it was provisioned via raw SQL, not alembic. The test DB now serves as the alembic-baseline
  reference.

## Cleanup

When the test database is no longer needed:

```bash
ssh guinevere-root

# Drop the test database (all objects)
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "DROP DATABASE IF EXISTS guinevere_p19_test WITH (FORCE);"

# Drop the test role
docker exec guinevere-postgres psql -U guinevere -d guinevere \
  -c "DROP ROLE IF EXISTS p19_test_runner;"
```

> If the `FORCE` option is not supported (PG < 13), terminate connections first:
> ```sql
> SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'guinevere_p19_test';
> ```

## How P19-003 Will Use This

P19-003 will use the same connection method to prove the P19 migration applies and is
reversible:

### Apply (upgrade head)

```bash
ssh guinevere-vps

cd /home/guinevere/code/guinevere

DATABASE_URL="postgresql+asyncpg://p19_test_runner:p19_test_local_only@127.0.0.1:5433/guinevere_p19_test" \
  .venv/bin/alembic upgrade head
```

### Verify

```bash
ssh guinevere-root \
  "docker exec guinevere-postgres psql -U guinevere -d guinevere_p19_test \
     -tAc \"SELECT version_num FROM ops.alembic_version;\""
```

### Revert (downgrade)

```bash
DATABASE_URL="postgresql+asyncpg://p19_test_runner:p19_test_local_only@127.0.0.1:5433/guinevere_p19_test" \
  .venv/bin/alembic downgrade p20_001_life_kernel_schema
```

Or downgrade one step at a time. After downgrade, re-run `upgrade head` to prove the
P19 migration applies cleanly over the p20_001 baseline.

### Connection string for P19-003 tests

```
DATABASE_URL=postgresql+asyncpg://p19_test_runner:p19_test_local_only@127.0.0.1:5433/guinevere_p19_test
```

The `p19_test_runner` password is a hardcoded throwaway. If re-creating the role, generate
a new random password and update the connection string. The password MUST NOT be committed
to the repo — document it in local-only infrastructure notes.

## Summary Table

| Item | Value |
|------|-------|
| Test database | `guinevere_p19_test` |
| Alembic head | `p20_001_life_kernel_schema` |
| Connection method | TCP via `p19_test_runner` with password auth |
| Extensions required | `timescaledb`, `vector` |
| Pre-created schemas | `ops` (for version table), `public` |
| Total user tables | 47 (verified) |
| Bugs fixed | `p5_add_loop_indexes.py`: `op.text()` -> `sa.text()` + add `import sqlalchemy` |
| File | `p19-test-db-baseline.md` |
