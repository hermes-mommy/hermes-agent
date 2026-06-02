# Research Report: Project Structure Audit for P1-004

| Field | Value |
|---|---|
| **Research Agent** | Explore |
| **Date** | 2026-05-31 |
| **Sources** | Root dir listing, glob searches, P1 evidence files, StepPrompts.md (lines 3433-3529), P1-003 auditor report |
| **Verdict** | `src/` does not exist. `pyproject.toml` does not exist. No Python package structure anywhere. Clean slate for P1-004. |

---

## 1. Current Project Structure - Key Findings

### 1.1 Root Directory (C:\Users\faizz\guinevere\)

| Item | Exists? | Notes |
|---|---|---|
| src/ | No | Clean -- no existing Python package directory |
| pyproject.toml | No | Clean -- no existing project config |
| setup.py | No | Clean |
| setup.cfg | No | Clean |
| Pipfile | No | Clean |
| .python-version | No | Clean |
| requirements*.txt | No | Clean |
| Root .gitignore | No | Only secrets/.gitignore exists |
| __init__.py anywhere | No | No Python package structure in entire repo |

### 1.2 Existing Root Directory Contents

.sops.yaml, adr/, AGENTS.md, audit-reports/, CHECKLIST.md, docs/, evidence/,
fixes/, PROGRESS.md, qa-inputs/, README.md, research-reports/, runbooks/,
scripts/, secrets/, stepprompts/, tmp/

### 1.3 Existing Evidence Directory (docs/setup-evidence/P1/)

```
docs/setup-evidence/P1/
  STEP-P1-001/   evidence.md, python-version.txt
  STEP-P1-002/   evidence.md, uv-version.txt
  STEP-P1-003/   evidence.md, venv-packages.txt (61 packages)
```

Evidence root path: docs/setup-evidence/P1/STEP-P1-{XXX}/evidence.md

---

## 2. P1-003 Virtual Environment Details (VPS)

### 2.1 Venv Path
/home/guinevere/code/guinevere/.venv/bin/python --> /usr/bin/python3.12

### 2.2 Packages Installed in Venv (61 total)

StepPrompts-specified packages installed:
  fastapi==0.115.6, uvicorn==0.34.3, pydantic==2.10.3, sqlalchemy==2.0.36,
  asyncpg==0.30.0, alembic==1.14.1, redis==5.2.1, httpx==0.28.1,
  python-dotenv==1.0.1, python-jose==3.5.0, passlib==1.7.4 (with bcrypt),
  apscheduler==3.11.2, sentry-sdk==2.61.0, prometheus-client==0.21.1,
  structlog==24.4.0, discord-py==2.4.0

Extra packages installed (not in StepPrompts pyproject.toml spec):
  pydantic-settings==2.7.0, aiohttp==3.11.11, websockets==15.0,
  cryptography==44.0.0, typer==0.15.1, rich==13.9.4, tenacity==9.0.0,
  setuptools==82.0.1

hermes-agent: DEFERRED to P1-004 (not installed in P1-003)

---

## 3. P1-004 StepPrompts Specification

### 3.1 What P1-004 Creates

src/ directory structure:
  src/__init__.py
  src/core/__init__.py, src/core/config/, src/core/models/,
    src/core/services/, src/core/api/
  src/memory/__init__.py
  src/persona/__init__.py
  src/loops/__init__.py
  src/surveillance/__init__.py
  src/discord/__init__.py
  src/mcp/__init__.py
  src/observability/__init__.py
  src/financial/__init__.py

pyproject.toml with hatchling build system.

### 3.2 P1-004 Verification Criteria
1. Hermes installed --> python -c "import hermes_agent" succeeds
2. Project structure created --> find src -type d shows all directories
3. pyproject.toml valid --> tomllib.load succeeds

---

## 4. pyproject.toml Dependency Match Analysis

### 4.1 StepPrompts Spec (15 dependencies)

dependencies = [
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2",
    "sqlalchemy[asyncio]>=2",
    "asyncpg>=0.30",
    "alembic>=1",
    "redis>=5",
    "httpx>=0.28",
    "python-dotenv>=1",
    "python-jose[cryptography]>=3",
    "apscheduler>=3",
    "sentry-sdk[fastapi]>=2",
    "prometheus-client>=0.21",
    "structlog>=24",
    "discord.py>=2",
]

### 4.2 Gaps -- Installed in Venv but Missing from pyproject.toml

| Package | Reason to Add |
|---|---|
| passlib[bcrypt]>=1.7 | Auth/password hashing |
| pydantic-settings>=2.7 | Env/settings management for Pydantic |
| aiohttp>=3.11 | Async HTTP client for surveillance |
| websockets>=15 | Real-time communication |
| typer>=0.15 | CLI framework |
| rich>=13.9 | Terminal formatting |
| tenacity>=9.0 | Retry/backoff |

### 4.3 Corrections Needed

- Add apscheduler (present in P1-003 install, missing from pyproject.toml spec)
- Add passlib[bcrypt] (present in P1-003 install, missing from pyproject.toml spec)

---

## 5. Evidence Conventions

### 5.1 Evidence Path
docs/setup-evidence/P1/STEP-P1-004/evidence.md

### 5.2 Evidence Schema (12 sections)
1. What Was Done
2. Files Changed
3. Validation Results (LSP diagnostics replace SSH)
4. Evidence Artifacts
5. Shared VPS Impact -- N/A (P1 code-only)
6. ADR Compliance
7. AC Reference
8. Rollback / Re-run Safety
9. Design Decisions / Caveats
10. Evidence Gate
11. Boundary Compliance (Persona/Surveillance/Memory/Consent/HARD STOP/Yandere)
12. Footer

### 5.3 Auditor Report Path
audit-reports/P1/STEP-P1-004/step-p1-004-auditor-report.md

---

## 6. Recommendations for P1-004

### 6.1 pyproject.toml -- Recommended Dependencies

dependencies = [
    # StepPrompts-specified (15):
    "fastapi>=0.115",
    "uvicorn[standard]>=0.34",
    "pydantic>=2",
    "sqlalchemy[asyncio]>=2",
    "asyncpg>=0.30",
    "alembic>=1",
    "redis>=5",
    "httpx>=0.28",
    "python-dotenv>=1",
    "python-jose[cryptography]>=3",
    "apscheduler>=3",
    "sentry-sdk[fastapi]>=2",
    "prometheus-client>=0.21",
    "structlog>=24",
    "discord.py>=2",

    # P1-003 installed but missing from spec (5):
    "passlib[bcrypt]>=1.7",
    "pydantic-settings>=2.7",
    "aiohttp>=3.11",
    "websockets>=15",
    "typer>=0.15",
    "rich>=13.9",
    "tenacity>=9.0",

    # P1-004:
    "hermes-agent",
]

Total: 23 dependencies

Build system: hatchling

### 6.2 Key Caveats
- No root .gitignore exists -- should be created
- No existing files will be overwritten (clean slate)
- PROGRESS.md line 99 shows P1-004 unchecked
- hermes-agent may not be on PyPI; may need git clone install

---

## 7. Collision Scan -- Pre-Implementation

| Path | Collision Risk | Notes |
|---|---|---|
| src/ | None -- does not exist | Clean creation |
| pyproject.toml | None -- does not exist | Clean creation |
| src/__init__.py | None -- does not exist | Clean creation |
| .gitignore | None -- does not exist | Clean creation |
| P1-004 evidence dir | None -- does not exist | Clean creation |
| P1-003 evidence | Read-only reference | Do not overwrite |
| PROGRESS.md line 99 | Update only | Change [ ] to [x] |

---

## Footer

| Field | Value |
|---|---|
| **Source Task** | P1-004 -- Project Structure Audit |
| **Date** | 2026-05-31 |
| **Researcher** | Guinevere (Explore agent) |
| **Method** | Local glob/grep/read + StepPrompts.md analysis + P1-003 evidence cross-reference |
| **Report Path** | research-reports/P1/project-structure-audit.md |
