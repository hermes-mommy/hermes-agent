# Evidence — STEP-P1-003: Virtual Environment & Core Packages

## What Was Done
Created Python 3.12 virtual environment at `/home/guinevere/code/guinevere/.venv` using UV 0.11.17 and installed 44 core packages including FastAPI, SQLAlchemy, Redis, Discord.py, aiohttp, and cryptography.

## Commands Executed
```bash
# Create venv using system Python 3.12
uv venv --python /usr/bin/python3.12 /home/guinevere/code/guinevere/.venv

# Install 18 core packages + dependencies
uv pip install fastapi==0.115.6 sqlalchemy==2.0.36 asyncpg==0.30.0 \
  alembic==1.14.1 redis==5.2.1 pydantic==2.10.3 pydantic-settings==2.7.0 \
  httpx==0.28.1 discord.py==2.4.0 aiohttp==3.11.11 python-dotenv==1.0.1 \
  websockets==15.0 cryptography==44.0.0 typer==0.15.1 rich==13.9.4 \
  tenacity==9.0.0 structlog==24.4.0

# Install setuptools for distutils compatibility
uv pip install setuptools
```

## Verification Results
| Check | Result |
|---|---|
| `.venv/bin/python --version` | Python 3.12.3 |
| `.venv/bin/python` exists | symlink → /usr/bin/python3.12 |
| `fastapi` import | ✅ OK |
| `sqlalchemy` import | ✅ OK |
| `redis` import | ✅ OK |
| `aiohttp` import | ✅ OK |
| `cryptography` import | ✅ OK |
| `discord` import | ✅ OK |
| `asyncpg` import | ✅ OK |
| `setuptools` import | ✅ OK |
| Package count | 61 packages (44 → 61 after auditor fix) |
| UV version | 0.11.17 |

## Evidence Artifacts
- `docs/setup-evidence/P1/STEP-P1-003/venv-packages.txt` — Full package list (44 packages)
- `docs/setup-evidence/P1/STEP-P1-003/evidence.md` — This file
- `research-reports/P1/python-venv-best-practices.md` — Research: venv best practices

## ADR Compliance
| ADR | Requirement | Status |
|---|---|---|
| ADR-014 | Python 3.12 with systemd services | ✅ `.venv/bin/python` ready for ExecStart |
| ADR-004 | LLM dependencies | ✅ FastAPI + httpx for API integration |

## Design Decisions
1. Used UV venv (not python -m venv) — follows StepPrompts P1-002 + UV docs
2. Systemd ExecStart will use `.venv/bin/python` directly (no `source activate`)
3. setuptools installed in venv (not system) — PEP 668 compliance
4. Package versions pinned to StepPrompts.md specifications

## Rollback / Re-run Safety
- To recreate: `rm -rf /home/guinevere/code/guinevere/.venv && rerun script`
- Idempotent: `uv venv` is safe to re-run (existing venv will be reused)
- No system packages or services touched

## Footer
| Field | Value |
|---|---|
| Source Task | STEP-P1-003 — Virtual Environment Setup |
| Date | 2026-05-31 |
| Implementer | Guinevere (Sisyphus parent) |
| Validation Method | Live SSH import verification + uv pip freeze |
| Evidence Root | `docs/setup-evidence/P1/STEP-P1-003/` |