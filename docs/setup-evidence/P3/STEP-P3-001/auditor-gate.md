# Auditor Gate Report — STEP-P3-001 Alembic Setup

**Date:** 2026-06-02
**Auditor:** Guinevere (independent auditor gate)
**Verdict:** **FAIL**

---

## Scope

Audit P3-001 DoD: Alembic installed/configured; asyncpg + multi-schema env.py; canonical 12 schema filter; version table in ops; baseline migration created and applied; `alembic current/heads/check` pass; `src/memory/models.py` exposes metadata-only Base; no P3-002 tables created; verifier reports exist and are internally consistent; evidence verification.md has 12 required sections; no plaintext secrets; Aizanta 5432 untouched; Guinevere PG 5433 only.

---

## Audit Checks — Results

### 1. Alembic Package Installation

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| alembic in .venv site-packages | `alembic/` directory present | **NOT FOUND** — site-packages contains only `__pycache__/` | **FAIL** |
| alembic CLI available | `alembic --help` succeeds | `No module named alembic.__main__` | **FAIL** |
| alembic importable (with version) | `alembic.__version__` exists | Import yields empty module (`__file__` is `None`) | **FAIL** |
| sqlalchemy installed | `import sqlalchemy` succeeds | `ModuleNotFoundError: No module named 'sqlalchemy'` | **FAIL** |
| asyncpg installed | `import asyncpg` succeeds | `ModuleNotFoundError: No module named 'asyncpg'` | **FAIL** |
| pyproject.toml declares alembic | `"alembic>=1"` in dependencies | ✅ Found `"alembic>=1"` in `pyproject.toml` | **PASS** |
| uv sync executed | Packages installed | **NOT EXECUTED** — site-packages empty | **FAIL** |

**Finding: Alembic, SQLAlchemy, and asyncpg are NOT installed.** The `.venv` site-packages directory is empty (only `__pycache__/`). The dependency is listed in `pyproject.toml` but `uv sync` was never run.

### 2. Alembic Configuration

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `alembic.ini` at project root | File present | **NOT FOUND** — no `alembic.ini` anywhere in project | **FAIL** |
| `alembic/` directory exists | Directory present | ✅ Present with `env.py`, `versions/`, `__pycache__/` | **PASS** |
| `alembic/script.py.mako` | Migration template | **NOT FOUND** | **FAIL** |
| `alembic/versions/` | Directory present (may be empty) | ✅ Present but **EMPTY** | **PASS** (empty is acceptable before baseline) |
| `alembic/env.py` exists | File present | ✅ Present, 89 lines | **PASS** |

**Finding: `alembic.ini` is missing.** Alembic cannot function without a configuration file. The `alembic/` directory exists with `env.py` but no ini config and no migration template.

### 3. env.py Content Review

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Async engine | `async_engine_from_config` | ✅ Used (line 71-78) | **PASS** |
| Multi-schema autogenerate | `include_schemas=True` | ✅ Set (lines 47, 60) | **PASS** |
| Canonical 12 schema filter | `GUINEVERE_SCHEMAS` frozenset | ✅ `frozenset({"memory", "persona", "surveillance", "financial", "projects", "social", "agents", "consent", "security", "audit", "ops", "extensions"})` | **PASS** |
| Version table in `ops` | `version_table_schema="ops"` | ✅ Set (lines 48, 62) | **PASS** |
| `compare_type=True` | Set | ✅ Set (lines 49, 63) | **PASS** |
| `compare_server_default=True` | Set | ✅ Set (lines 50, 64) | **PASS** |
| Password via env var | `GUINEVERE_DB_PASSWORD` | ✅ Implemented (lines 26-29) | **PASS** |
| Imports `Base` from `src.memory.models` | `from src.memory.models import Base` | ✅ Line 11 | **PASS** (syntax) |
| **Base import WILL FAIL at runtime** | `src/memory/models.py` must exist | **NOT FOUND** — `src/memory/` has only `__init__.py` | **FAIL** |

**Finding: env.py is syntactically correct** but **will crash on import** because `src/memory/models.py` does not exist. The `from src.memory.models import Base` line will raise `ImportError` at any attempt to use Alembic.

### 4. src/memory/models.py

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `models.py` exists | File present | **NOT FOUND** — only `__init__.py` exists in `src/memory/` | **FAIL** |
| `Base` declarative base | `Base = declarative_base()` | Cannot check — file missing | **FAIL** |
| `metadata` exposed | `Base.metadata` accessible | Cannot check — file missing | **FAIL** |
| No P3-002 tables | Only Base, no model classes | Trivially satisfied (file missing) | **PASS** (by absence) |

**Finding: The models module referenced by env.py does not exist.** Alembic's `target_metadata = Base.metadata` (env.py line 17) will raise `ImportError` before any migration command can execute.

### 5. Baseline Migration

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Baseline revision `2bed93fd1dd0` | File in `versions/` | **NOT FOUND** — `versions/` is empty | **FAIL** |
| `alembic revision --autogenerate` | Runs without error | Cannot run — missing deps | **FAIL** |
| `alembic stamp head` | Stamps current head | Cannot run — missing deps | **FAIL** |

**Finding: No baseline migration exists.** The `alembic/versions/` directory is empty. Expected baseline revision `2bed93fd1dd0` is absent.

### 6. alembic current / heads / check

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `alembic check` | Clean output (no pending migrations) | **CANNOT RUN** — alembic not installed, no alembic.ini | **FAIL** |
| `alembic current` | Shows current revision | **CANNOT RUN** | **FAIL** |
| `alembic heads` | Shows head revision | **CANNOT RUN** | **FAIL** |

**Finding: No Alembic command can execute** due to missing package, missing config, and missing models module.

### 7. Verifier Reports (LSP, Migration, Safety)

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `verifier-lsp.md` | Exists in evidence dir | **NOT FOUND** — evidence directory is empty | **FAIL** |
| `verifier-migration.md` | Exists in evidence dir | **NOT FOUND** | **FAIL** |
| `verifier-safety.md` | Exists in evidence dir | **NOT FOUND** | **FAIL** |
| Reports internally consistent | Cross-checks pass | Cannot check — absent | **FAIL** |

### 8. Evidence verification.md

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `verification.md` | Exists with 12 required sections | **NOT FOUND** — evidence directory is empty | **FAIL** |
| PROGRESS.md reflects status | P3-001 marked complete | ✅ Marked as ⏳ Not Started (0/19) | **PASS** (honest state) |

**Finding: The entire evidence directory for P3-001 is empty.** No verification.md, no verifier reports, no implementation artifacts exist.

### 9. Secret Handling

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| `db-passwords.yaml` SOPS-encrypted | AES256_GCM ciphertext | ✅ All 5 entries properly encrypted | **PASS** |
| Plaintext passwords in evidence | None | ✅ No evidence files exist (empty dir) | **PASS** |
| No plaintext passwords committed | None in repo | ✅ No plaintext passwords found | **PASS** |

### 10. Port Isolation

| Check | Expected | Actual | Status |
|-------|----------|--------|--------|
| Aizanta PG (port 5432) untouched | No connection to 5432 | ✅ Not listening on this Windows machine (PG on VPS) | **PASS** |
| Guinevere PG (port 5433) only | Connections to 5433 only | ✅ 5433 not listening locally (PG on VPS) | **PASS** (by absence of local PG) |

---

## Consolidated Findings

### Critical Failures (block P3-001 completion)

| # | Finding | Severity | Evidence |
|---|---------|----------|----------|
| F1 | **Alembic package NOT installed** in .venv | CRITICAL | site-packages empty; `import alembic` yields empty module; CLI unavailable |
| F2 | **SQLAlchemy NOT installed** | CRITICAL | `ModuleNotFoundError: No module named 'sqlalchemy'` |
| F3 | **asyncpg NOT installed** | CRITICAL | `ModuleNotFoundError: No module named 'asyncpg'` |
| F4 | **alembic.ini does NOT exist** | CRITICAL | No config file anywhere in project tree |
| F5 | **src/memory/models.py does NOT exist** | CRITICAL | `from src.memory.models import Base` at env.py:11 will raise ImportError |
| F6 | **Evidence directory is EMPTY** | CRITICAL | No verification.md, no verifier reports |
| F7 | **No baseline migration** created | CRITICAL | `alembic/versions/` is empty |
| F8 | **script.py.mako missing** | HIGH | Migration template absent |

### Passes

| # | Check | Status |
|---|-------|--------|
| P1 | env.py has correct async + multi-schema pattern | ✅ PASS |
| P2 | env.py has canonical 12-schema filter | ✅ PASS |
| P3 | env.py has `version_table_schema="ops"` | ✅ PASS |
| P4 | env.py uses env var for password | ✅ PASS |
| P5 | db-passwords.yaml properly SOPS-encrypted | ✅ PASS |
| P6 | No plaintext secrets in evidence/code | ✅ PASS |
| P7 | No P3-002 tables created | ✅ PASS (trivially) |
| P8 | Aizanta port 5432 not touched | ✅ PASS |
| P9 | PROGRESS.md honestly reflects 0/19 state | ✅ PASS |
| P10 | P3 batch plan exists with detailed design | ✅ PASS |

---

## Verdict

**FAIL** — P3-001 Alembic setup is NOT implemented.

The implementation is essentially at zero. The `alembic/` directory was created with a hand-written `env.py` that is syntactically correct, but none of the supporting infrastructure exists:

- **Dependencies not installed**: Alembic, SQLAlchemy, and asyncpg are listed in `pyproject.toml` but `uv sync` was never executed
- **Config missing**: No `alembic.ini` for Alembic to read
- **Models module missing**: `src/memory/models.py` does not exist, so `env.py` will crash at import time
- **No migration created**: `alembic/versions/` is empty
- **No evidence**: Evidence directory is empty — no verification artifacts, no verifier reports

The P3 batch plan (`batch-plan-001-003.md`) is well-designed and describes the correct approach, but **no implementation was performed**. PROGRESS.md correctly shows P3-001 as ⏳ Not Started.

---

## Required Fixes

To pass this gate, the following must be completed in order:

1. **`uv sync`** — Install all dependencies including alembic, sqlalchemy, asyncpg
2. **Create `src/memory/models.py`** — Define `Base = declarative_base()` with bare metadata
3. **Create `alembic.ini`** — Config with async connection string to `127.0.0.1:5433/guinevere`
4. **Create `alembic/script.py.mako`** — Migration template
5. **Create baseline migration** — `alembic revision --autogenerate -m "init"` then `alembic stamp head`
6. **Verify** — `alembic check`, `alembic current`, `alembic heads` all pass
7. **Generate evidence** — Write verification.md (12 sections), spawn LSP/migration/safety verifiers
8. **Re-audit** — Re-run this auditor gate

---

*End of auditor gate report. Re-audit via `task_id` after fixes are applied.*