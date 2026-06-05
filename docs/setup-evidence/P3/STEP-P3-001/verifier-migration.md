# Verifier Report: STEP-P3-001 Alembic/Database Baseline

**Verdict: PASS** ✅

| Check | Result | Evidence |
|---|---|---|
| Guinevere DB on port 5433 | PASS | Docker container `guinevere-postgres` mapping `127.0.0.1:5433->5432/tcp` |
| Aizanta 5432 isolation | PASS | Aizanta DB on 5432 has zero tables; no write cross-contamination |
| `ops.alembic_version` table exists | PASS | Schema: `ops`, Owner: `guinevere_core` |
| `ops.alembic_version` current head | PASS | Version: `2bed93fd1dd0` |
| `alembic current` | PASS | Output: `2bed93fd1dd0 (head)` |
| `alembic heads` | PASS | Output: `2bed93fd1dd0 (head)` (single head, no branching) |
| `alembic check` | PASS | Output: `No new upgrade operations detected` |
| env.py canonical 12-schema filtering | PASS | `GUINEVERE_SCHEMAS` frozenset with exactly 12 schemas |
| env.py `version_table_schema=ops` | PASS | Set in both `run_migrations_offline` and `do_run_migrations` |
| env.py `include_name` filter | PASS | Function `include_name` filters schemas to `GUINEVERE_SCHEMAS` |
| env.py `include_schemas=True` | PASS | Present in both `context.configure()` calls |
| Baseline migration empty | PASS | Both `upgrade()` and `downgrade()` contain only `pass` |
| No P3-002 tables present | PASS | Only `ops.alembic_version` exists (plus TimescaleDB system schemas) |

## Detailed Findings

### 1. Database Port Assignment

```
Docker container guinevere-postgres:  127.0.0.1:5433 -> 5432 (container internal)
Docker container aizanta-postgres:    127.0.0.1:5432 -> 5432 (container internal)
```

Guinevere connects to `127.0.0.1:5433` (host port). Container maps to internal PostgreSQL port 5432. Aizanta runs on a separate container at `127.0.0.1:5432` (host port).

### 2. Alembic Version Table

- Schema: `ops`
- Table: `alembic_version`
- Owner: `guinevere_core`
- Version: `2bed93fd1dd0`

### 3. Alembic CLI Output

- **current**: `2bed93fd1dd0 (head)`
- **heads**: `2bed93fd1dd0 (head)` -- single head, no fork
- **check**: `No new upgrade operations detected.` -- migration state matches model metadata

### 4. env.py Configuration

- **Schema filter**: 12 canonical schemas configured as `GUINEVERE_SCHEMAS` frozenset (memory, persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions)
- **Version table schema**: `"ops"` in both offline and online config
- **include_name**: Filters by schema membership in `GUINEVERE_SCHEMAS`
- **include_schemas**: `True` in both `context.configure()` calls
- **Password injection**: Via `GUINEVERE_DB_PASSWORD` env var, replacing `:****@` placeholder

### 5. Baseline Migration Content

File: `alembic/versions/2bed93fd1dd0_baseline_init.py`

- `upgrade()`: `pass` -- no operations
- `downgrade()`: `pass` -- no operations
- `down_revision`: `None` -- root migration
- No `op.create_table()`, no `sa.Column()`, no schema/table operations

### 6. Isolation

Aizanta PostgreSQL 5432 is accessible only via `docker exec aizanta-postgres`. The `aizanta` database contains zero application tables. No Guinevere schema/table leakage to Aizanta.

## Conclusion

**PASS** -- All 13 verification checks pass. The Alembic baseline is correctly established:

1. Migration `2bed93fd1dd0` is at head
2. env.py has correct 12-schema filtering with `ops` version table schema
3. Baseline is empty (no table creation -- tables deferred to P3-002+)
4. No cross-contamination with Aizanta 5432
5. All CLI commands (`current`, `heads`, `check`) report healthy state

## Caveats

- `uv run alembic` fails due to hatchling build config issue (missing `[tool.hatch.build.targets.wheel]` packages). Workaround: `source .venv/bin/activate && PYTHONPATH=src alembic <cmd>`.
- Aizanta DB appears empty (0 application tables). This is expected per isolation requirement but noted for awareness.
- Secrets handled via `PGPASSWORD` env var; no plaintext in output artifacts.

---
*Report generated: 2026-06-02 by Guinevere verifier agent*