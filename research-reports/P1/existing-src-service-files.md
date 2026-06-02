# Existing Source & Service File Inventory

> **Purpose**: Complete map of existing code files, service definitions, scripts, and config files before implementing P1-017 (persona smoke test), P1-018 (guinevere-core.service + main.py), P1-019 (service health check).
> **Date**: 2026-06-01
> **Scope**: All Python files in `src/`, scripts, systemd units, config files, project structure

---

## 1. Project Root Structure

```
guinevere/
├── .gitignore              # Python/venv/IDE/secrets/OS ignores
├── .sops.yaml              # SOPS encryption rules (age public key)
├── AGENTS.md               # Operating contract
├── CHECKLIST.md            # Phase checklist
├── PROGRESS.md             # Progress tracking
├── README.md               # Project README
├── pyproject.toml          # Project config (hatchling)
├── adr/                    # ADR directory
├── audit-reports/          # Audit reports
├── docs/                   # Documentation
├── evidence/               # Implementation evidence
├── fixes/                  # Applied fixes
├── qa-inputs/              # QA documents
├── research-reports/       # Research reports
├── runbooks/               # Operational runbooks
├── scripts/                # Deployment/backup scripts
├── secrets/                # SOPS-encrypted secrets
├── src/                    # Python source code
├── stepprompts/            # Step prompts
└── tmp/                    # Temp files (gitignored)
```

---

## 2. Python Source Tree (`src/`) — Complete

### 2.1 Directory Structure

```
src/
├── __init__.py                        # "src module"
├── core/
│   ├── __init__.py                    # "src/core module"
│   ├── api/
│   │   └── __init__.py                # "src/core/api module" — EMPTY
│   ├── config/
│   │   └── __init__.py                # "src/core/config module" — EMPTY
│   ├── models/
│   │   └── __init__.py                # "src/core/models module" — EMPTY
│   └── services/
│       ├── __init__.py                # "src/core/services module"
│       ├── llm_router.py              # LLM routing service (EXISTING)
│       └── prompt_loader.py           # System prompt loader (EXISTING)
├── discord/
│   └── __init__.py                    # "src/discord module" — EMPTY
├── financial/
│   └── __init__.py                    # "src/financial module" — EMPTY
├── loops/
│   └── __init__.py                    # "src/loops module" — EMPTY
├── mcp/
│   └── __init__.py                    # "src/mcp module" — EMPTY
├── memory/
│   └── __init__.py                    # "src/memory module" — EMPTY
├── observability/
│   └── __init__.py                    # "src/observability module" — EMPTY
├── persona/
│   └── __init__.py                    # "src/persona module" — EMPTY
└── surveillance/
    └── __init__.py                    # "src/surveillance module" — EMPTY
```

**Key finding**: Only 2 actual Python files exist outside `__init__.py` stubs:
- `src/core/services/llm_router.py`
- `src/core/services/prompt_loader.py`

All other directories (`api/`, `config/`, `models/`, `discord/`, `financial/`, `loops/`, `mcp/`, `memory/`, `observability/`, `persona/`, `surveillance/`) are stubs-only.

### 2.2 Existing Source Files

#### `src/core/services/llm_router.py` (93 lines)
- **Classes**: `TaskType` (Enum), `ModelConfig` (dataclass), `LLMRouter`
- **Dependencies**: `httpx`, `structlog`, `enum`, `typing`, `dataclasses`
- **Module-constants**: `MODELS` dict (3 entries)
- **LLMRouter methods**: `chat()`, `close()`
- **Pattern**: Async class with `httpx.AsyncClient`, fallback chain, `structlog` logger

#### `src/core/services/prompt_loader.py` (47 lines)
- **Functions**: `load_system_prompt()`, `get_system_prompt_with_context()`
- **Dependencies**: `structlog`, `pathlib.Path`
- **Module-constants**: `SYSTEM_PROMPT_PATH` pointing to `/home/guinevere/config/hermes/system-prompt.md`
- **Pattern**: Filesystem path-based loader with safety validation

#### All `__init__.py` Files
Every `__init__.py` is a 1-line comment-only stub. No package exports, no `__all__`, no imports.

---

## 3. `scripts/` Directory — Complete

| File | Type | Purpose |
|---|---|---|
| `guinevere-backup@.service` | systemd template | Template backup service unit |
| `guinevere-backup@.timer` | systemd timer | Daily 02:00 WIB backup |
| `guinevere-backup-weekly@.timer` | systemd timer | Weekly Sun 04:00 WIB redundant backup |
| `guinevere-prune-weekly@.service` | systemd service | Weekly restic prune |
| `guinevere-prune-weekly@.timer` | systemd timer | Weekly Sun 05:00 WIB prune |
| `guinevere-backup.sh` | bash script | Full dual-repo restic backup (615 lines) |
| `preflight-check.sh` | bash script | P0-028 pre-flight verification (467 lines) |
| `setup-restic.sh` | bash script | Restic deployment guide |

### Key systemd patterns from existing units:
- `Type=oneshot` (for backup/prune), `User=root`
- `Wants=network-online.target`, `After=network-online.target`
- Security hardening: `ProtectSystem=strict`, `ProtectHome=yes`, `PrivateTmp=yes`, `NoNewPrivileges=yes`, `UMask=0077`
- `StandardOutput=journal`, `StandardError=journal`

---

## 4. Systemd Unit Files — Complete Inventory

**No systemd unit files exist in workspace root.** All unit files are in `scripts/`:
- `scripts/guinevere-backup@.service` (template)
- `scripts/guinevere-prune-weekly@.service`

**No `guinevere-9router.service` file in repo** — deployed to VPS but source not committed.
**No `guinevere-core.service` file exists yet** — this is what P1-018 will create.
**No `guinevere-surveillance.service` file exists yet** — planned for later phase.

Reference from StepPrompts.md L4826:
```
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app --host 127.0.0.1 --port 8000 --workers 2
```

---

## 5. `.gitignore` — Key Rules

- `.venv/`, `venv/`, `env/` — gitignored
- `tmp/` — gitignored
- `*.log` — gitignored
- `secrets/backup/*-plaintext*`, `*.key`, `*.pem`, `*.env` — gitignored
- `secrets/` allows `*.sops.yaml`, `*.sops` files
- `scripts/*.service`, `scripts/*.timer` — NOT gitignored (tracked)

---

## 6. Test Files — Complete Inventory

**No test files exist.** `tests/` directory does not exist.

`pyproject.toml` configures:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
```

---

## 7. Main Entry Points — Complete Inventory

**No `main.py`, `app.py`, or FastAPI entry point files exist anywhere.**
- Zero FastAPI references in actual `.py` files (only in docs/reports/StepPrompts)
- `src/core/api/` is empty

---

## 8. `__init__.py` Hierarchy — Complete

All 14 `__init__.py` files exist as 1-line stubs. No exports.

---

## 9. `pyproject.toml` — Key Dependencies

**Runtime**: fastapi, uvicorn[standard], pydantic, sqlalchemy[asyncio], asyncpg, alembic, redis, httpx, apscheduler, sentry-sdk, prometheus-client, structlog, pydantic-settings, hermes-agent, and more.
**Build**: hatchling
**Lint**: ruff (py312, 100 chars)
**Type**: mypy (strict)

---

## 10. Existing Code Patterns to Match

| Pattern | Source |
|---|---|
| `structlog.get_logger()` at module level | llm_router.py, prompt_loader.py |
| Async classes with httpx.AsyncClient | llm_router.py |
| `"""Docstring."""` first line | All existing .py files |
| Enum + dataclasses for typed config | llm_router.py |
| No `if __name__ == "__main__"` | No existing module uses it |

---

## 11. Collision Analysis for P1-017/018/019

### Files to CREATE (no collision risk):
| New File | Phase |
|---|---|
| `src/core/main.py` | P1-018 — FastAPI app with lifespan, `/health` |
| `scripts/guinevere-core.service` | P1-018 — systemd unit |
| Test files for persona smoke + health | P1-017 / P1-019 |

### Files that MAY need MODIFICATION:
| File | Change |
|---|---|
| `pyproject.toml` | Only if new deps needed |
| `CHECKLIST.md` / `PROGRESS.md` | Status update |

### No collision risk:
- No existing `main.py` or `app.py`
- No existing tests
- `src/persona/` is empty stub — safe to create persona files
- `src/core/api/` is empty — no router collision
- No systemd unit for core exists

---

## 12. Service Port Mapping

| Service | Port | Notes |
|---|---|---|
| guinevere-core | 8000 | FastAPI main app (P1-018) |
| guinevere-surveillance | 8000 (shared) | Planned for P7 |
| guinevere-9router | 20128 | LLM proxy (deployed) |
| PostgreSQL | 5433 (PgBouncer: 5434) | Database |
| Redis | 6380 | Cache |
| Caddy | 8443 (TLS) | Reverse proxy |

---

## 13. Empty Directories Ready for New Files

| Directory | Next File to Create |
|---|---|
| `src/core/` | `main.py` (P1-018) |
| `src/persona/` | smoke test / engine (P1-017) |
| `src/core/config/` | `settings.py` (P1-018 or later) |
| `src/core/models/` | DB models (P3) |
| `tests/` | test files (P1-017) |

---

## 14. Key Documentation References for P1-017/018/019

- **StepPrompts.md** L4775-L4890 — FastAPI skeleton, systemd unit spec
- **DeploymentGuide_v1.0.md** L1167-L1200 — Service unit template
- **TechnicalArchitecture_v2.0.md** §3.1 — Service table
- **ADR-014** — guinevere.slice resource isolation
- **PersonaSafetyPolicy_v1.0.md** — Persona safety constraints
- **Persona_Document_v3.0.md** — Persona behavior specs
- **enterprise-deployment-guide-research.md** — FastAPI systemd patterns

---

*End of report. Total: 16 Python files (14 stubs + 2 services), 8 scripts, 2 systemd templates, 2 .gitignore, 1 .sops.yaml, 1 pyproject.toml.*
