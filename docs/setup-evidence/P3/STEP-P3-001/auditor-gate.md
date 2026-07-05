# Auditor Gate Report ? STEP-P3-001 Alembic Setup

**Date:** 2026-06-02  
**Auditor:** Guinevere (independent auditor gate)  
**Host:** faiz-prod-01 (100.94.104.22) ? /home/guinevere/code/guinevere  
**Verdict:** **PASS** ?

---

## Scope

Audit P3-001 DoD: Alembic installed/configured; asyncpg + multi-schema env.py; canonical 12 schema filter; version table in ops; baseline migration created and applied; `alembic current/heads/check` pass; `src/memory/models.py` exposes metadata-only Base; no P3-002 tables created; verifier reports exist and are internally consistent; evidence verification.md has 12 required sections; no plaintext secrets; Aizanta 5432 untouched; Guinevere PG 5433 only.

---

## 1. Dependency Installation

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| alembic installed | `importlib.metadata.version('alembic')` | ? **1.18.4** | **PASS** |
| sqlalchemy[asyncio] installed | `importlib.metadata.version('sqlalchemy')` | ? **2.0.50** | **PASS** |
| asyncpg installed | `importlib.metadata.version('asyncpg')` | ? **0.31.0** | **PASS** |
| `alembic` CLI available | `alembic --help` works | ? Available at `.venv/bin/alembic` | **PASS** |

All three core dependencies are installed via `uv sync`. `.venv` site-packages populated.

---

## 2. Alembic Configuration ? Files

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `alembic.ini` exists | File present | ? 5,038 bytes, correct connection string | **PASS** |
| `alembic/` directory exists | Directory present | ? Contains `env.py`, `script.py.mako`, `versions/` | **PASS** |
| `alembic/script.py.mako` exists | Migration template | ? Present (standard template) | **PASS** |
| `alembic/versions/` populated | Contains baseline | ? `2bed93fd1dd0_baseline_init.py` | **PASS** |
| `alembic.ini` port | `127.0.0.1:5433` | ? `postgresql+asyncpg://guinevere_core:****@127.0.0.1:5433/guinevere` | **PASS** |

---

## 3. env.py Content Verification

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Async engine | `async_engine_from_config` | ? Used (line 71-78) | **PASS** |
| Multi-schema autogenerate | `include_schemas=True` | ? Set in both `context.configure()` calls | **PASS** |
| Canonical 12 schema filter | `GUINEVERE_SCHEMAS` frozenset | ? `memory`, `persona`, `surveillance`, `financial`, `projects`, `social`, `agents`, `consent`, `security`, `audit`, `ops`, `extensions` | **PASS** |
| Version table in `ops` | `version_table_schema="ops"` | ? Set in both offline and online config | **PASS** |
| `include_name` filter | Proper schema filtering | ? `include_name()` function filters by `GUINEVERE_SCHEMAS` membership | **PASS** |
| `compare_type=True` | Set | ? Present in both configure calls | **PASS** |
| `compare_server_default=True` | Set | ? Present in both configure calls | **PASS** |
| Password env var injection | `GUINEVERE_DB_PASSWORD` | ? `:****@` placeholder replaced via env var | **PASS** |
| `from src.memory.models import Base` | Importable | ? See Section 4 | **PASS** |

---

## 4. src/memory/models.py

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| File exists | `models.py` in `src/memory/` | ? 151 bytes | **PASS** |
| Exports `Base` | `declarative_base()` | ? `Base = declarative_base()` | **PASS** |
| No table models | No P3-002 model classes | ? Only Base definition | **PASS** |
| Importable | `from src.memory.models import Base` | ? Confirmed via env.py at runtime | **PASS** |

---

## 5. Baseline Migration

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Revision file exists | `2bed93fd1dd0_baseline_init.py` | ? 741 bytes | **PASS** |
| Revision ID | `2bed93fd1dd0` | ? Matches expected | **PASS** |
| `down_revision` | `None` (root) | ? `None` | **PASS** |
| `upgrade()` | `pass` (no operations) | ? Empty baseline | **PASS** |
| `downgrade()` | `pass` (no operations) | ? Empty baseline | **PASS** |
| No `op.create_table()` | No table creation | ? No schema/table operations | **PASS** |

---

## 6. Alembic Runtime Commands (Independent Re-Run)

| Command | Expected | Actual (independently verified) | Status |
|---------|----------|----------------------------------|--------|
| `alembic check` | `No new upgrade operations detected` | ? `No new upgrade operations detected` | **PASS** |
| `alembic current` | `2bed93fd1dd0 (head)` | ? `2bed93fd1dd0 (head)` | **PASS** |
| `alembic heads` | `2bed93fd1dd0 (head)` (single head) | ? `2bed93fd1dd0 (head)` | **PASS** |
| `alembic history` | `<base> -> 2bed93fd1dd0` | ? `<base> -> 2bed93fd1dd0 (head), baseline_init` | **PASS** |

**Note:** `uv run alembic` fails due to hatchling build config issue. Workaround: `source .venv/bin/activate && PYTHONPATH=src alembic <cmd>`. Documented in verifier-migration.md caveats.

---

## 7. Database Verification (Independent psql Read-Only)

| Check | Expected | Actual (independently verified) | Status |
|-------|----------|----------------------------------|--------|
| `ops.alembic_version` exists | Table present | ? 1 row: `2bed93fd1dd0` | **PASS** |
| No P3-002 tables | Only `ops.alembic_version` + TimescaleDB system tables | ? Only `ops.alembic_version` in custom schemas | **PASS** |
| Connection to Guinevere PG | Port 5433 (host) | ? Connected to `guinevere-postgres` container | **PASS** |
| Existing schemas untouched | No schema drops | ? `audit`, `config`, `financial`, `loops`, `memory`, `persona`, `surveillance` intact | **PASS** |

---

## 8. Aizanta PG 5432 Isolation

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Aizanta PG container | On 127.0.0.1:5432 | ? `aizanta-postgres` container | **PASS** |
| Guinevere PG container | On 127.0.0.1:5433 | ? `guinevere-postgres` container | **PASS** |
| Separate containers | No cross-contamination | ? Separate Docker containers, separate ports | **PASS** |
| No Alembic operations on 5432 | Only 5433 configured | ? `alembic.ini` targets `127.0.0.1:5433` | **PASS** |

---

## 9. Secret Handling

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `db-passwords.yaml` SOPS-encrypted | AES256_GCM ciphertext | ? Properly encrypted | **PASS** |
| No plaintext passwords in evidence | Absent | ? No plaintext in any evidence file | **PASS** |
| Password via env var at runtime | `GUINEVERE_DB_PASSWORD` | ? env.py uses `os.environ.get(...)` | **PASS** |
| No secrets committed | None in artifacts | ? All secrets SOPS-encrypted | **PASS** |
| SOPS decryption works | `sops --decrypt` succeeds | ? Successfully decrypted with age key | **PASS** |

---

## 10. Verifier Report Cross-Reference

### verifier-lsp.md consistency

| Claim | Independent Check | Consistent? |
|-------|-------------------|-------------|
| `models.py` exists with Base, no tables | ? File present, only `declarative_base()` | ? **Match** |
| `env.py` compiles/type-checks | ? Compiles at runtime | ? **Match** |
| Baseline migration exists | ? `2bed93fd1dd0` file present | ? **Match** |
| `alembic.ini` has correct port | ? `127.0.0.1:5433` | ? **Match** |
| `verification.md` has 12 sections | ? Counted: all 12 present | ? **Match** |
| No forbidden patterns | ? No `# type: ignore`, bare except | ? **Match** |

### verifier-migration.md consistency

| Claim | Independent Check | Consistent? |
|-------|-------------------|-------------|
| Guinevere DB on 5433 | ? Host port 5433 maps to guinevere-postgres | ? **Match** |
| Aizanta 5432 isolation | ? Separate containers | ? **Match** |
| `ops.alembic_version` with `2bed93fd1dd0` | ? psql confirms 1 row | ? **Match** |
| `alembic current` shows head | ? `2bed93fd1dd0 (head)` | ? **Match** |
| `alembic heads` single head | ? Single, no fork | ? **Match** |
| `alembic check` passes | ? `No new upgrade operations detected` | ? **Match** |
| env.py 12-schema filtering | ? `GUINEVERE_SCHEMAS` frozenset | ? **Match** |
| env.py `version_table_schema=ops` | ? Set in both configure calls | ? **Match** |
| Baseline migration empty | ? Both `upgrade()` and `downgrade()` = `pass` | ? **Match** |
| No P3-002 tables present | ? Only `ops.alembic_version` in custom schemas | ? **Match** |

### verifier-safety.md consistency

| Claim | Independent Check | Consistent? |
|-------|-------------------|-------------|
| Aizanta PG 5432 healthy, untouched | ? Container running, not referenced | ? **Match** |
| Guinevere PG 5433 healthy | ? pg_isready accepting connections | ? **Match** |
| PgBouncer 5434 healthy | ? ss confirms LISTEN | ? **Match** |
| No safety boundary touched | ? No surveillance/consent/persona tables created | ? **Match** |
| Evidence file exists with 12 sections | ? verification.md present and complete | ? **Match** |
| No secrets in evidence | ? Verified via read | ? **Match** |

**All three verifier reports are internally consistent and cross-verify each other's claims.**

---

## 11. verification.md Section Audit

| # | Section | Present | Status |
|---|---------|---------|--------|
| 1 | What Was Done | ? | **PASS** |
| 2 | Files Changed | ? | **PASS** |
| 3 | Validation Results | ? | **PASS** |
| 4 | Evidence Artifacts | ? | **PASS** |
| 5 | Doc-Sync Impact | ? | **PASS** |
| 6 | Boundary Compliance | ? | **PASS** |
| 7 | Rollback/Re-run Safety | ? | **PASS** |
| 8 | Design Decisions/Caveats | ? | **PASS** |
| 9 | Auditor Gate | ? | **PASS** |
| 10 | Security Scan | ? | **PASS** |
| 11 | Acceptance Criteria Mapping | ? | **PASS** |
| 12 | Footer | ? | **PASS** |

---

## 12. PROGRESS.md State Consistency

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| P3-001 status in PROGRESS.md | Unchecked | ? `[ ] P3-001` (not yet started per tracker) | **PASS** |
| P3 total | 0/19 before tracker update | ? 0/19 | **PASS** |

---

## Summary

### All Checks: 81/81 PASS

| Category | Total Checks | PASS | FAIL |
|----------|-------------|------|------|
| Dependency Installation | 4 | 4 | 0 |
| Alembic Configuration Files | 5 | 5 | 0 |
| env.py Content Verification | 9 | 9 | 0 |
| src/memory/models.py | 4 | 4 | 0 |
| Baseline Migration | 6 | 6 | 0 |
| Alembic Runtime Commands | 4 | 4 | 0 |
| Database Verification | 4 | 4 | 0 |
| Aizanta PG 5432 Isolation | 4 | 4 | 0 |
| Secret Handling | 5 | 5 | 0 |
| Verifier Report Cross-Reference | 22 | 22 | 0 |
| verification.md Sections | 12 | 12 | 0 |
| PROGRESS.md Consistency | 2 | 2 | 0 |
| **Total** | **81** | **81** | **0** |

### Non-Blocking Caveat

- `uv run alembic` fails due to missing `[tool.hatch.build.targets.wheel]` packages in `pyproject.toml`. Workaround: `source .venv/bin/activate && PYTHONPATH=src alembic <cmd>`. All alembic commands succeed with this workaround. This should be fixed in a future batch to enable `uv run alembic` workflow.

---

## Verdict

**PASS** ? ? P3-001 Alembic setup is fully implemented and verified.

All 81 independent audit checks pass. The Alembic baseline is correctly established with:
- `alembic 1.18.4`, `sqlalchemy 2.0.50`, `asyncpg 0.31.0` installed
- `alembic.ini` configured for `127.0.0.1:5433/guinevere`
- `env.py` with async engine, multi-schema autogenerate, canonical 12-schema filter, version table in `ops`
- `src/memory/models.py` with metadata-only `Base` (no P3-002 tables)
- Baseline revision `2bed93fd1dd0` created, applied, and at head
- `alembic check`, `current`, `heads`, `history` all pass
- `ops.alembic_version` table confirmed with `2bed93fd1dd0`
- Aizanta 5432 isolated ? no cross-contamination
- All three verifier reports (LSP, migration, safety) exist and are internally consistent
- `verification.md` has all 12 required sections
- No plaintext secrets ? SOPS-only password handling
- P3-002 tables not created

Ready for P3-002.

---

*End of auditor gate report. PASS verdict. No re-audit required.*
