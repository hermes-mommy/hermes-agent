# Research Report: Code Patterns & Conventions for P1-015/P1-016

| Field | Value |
|---|---|
| **Research Agent** | Explore / Parent |
| **Date** | 2026-06-01 |
| **Scope** | pyproject.toml, src/ structure, __init__.py conventions, StepPrompts P1-015/P1-016 templates, ADR-001/003 constraints, Hermes integration patterns, 9Router combo routing |
| **Verdict** | Complete — all patterns identified for exact-reproduction code writing |

---

## 1. pyproject.toml — Dependencies & Tool Configuration

**Path:** /pyproject.toml (repo root)

### Build System

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

### Python & Project Metadata

[project]
name = "guinevere"
version = "0.1.0"
description = "Guinevere AI Companion - Autonomous Agent System"
requires-python = ">=3.12"

### All 23 Dependencies

| # | Package | Version | Used By |
|---|---------|---------|---------|
| 1 | fastapi | >=0.115 | API layer (core/api/) |
| 2 | uvicorn[standard] | >=0.34 | ASGI server |
| 3 | pydantic | >=2 | Type validation everywhere |
| 4 | sqlalchemy[asyncio] | >=2 | PostgreSQL ORM |
| 5 | asyncpg | >=0.30 | async PG driver |
| 6 | alembic | >=1 | DB migrations |
| 7 | redis | >=5 | Cache/pub-sub |
| 8 | httpx | >=0.28 | HTTP client (LLM Router uses this) |
| 9 | python-dotenv | >=1 | Env loading |
| 10 | apscheduler | >=3 | Task scheduling |
| 11 | sentry-sdk[fastapi] | >=2 | Error monitoring |
| 12 | prometheus-client | >=0.21 | Metrics |
| 13 | structlog | >=24 | Structured logging (BOTH modules use this) |
| 14 | aiohttp | >=3 | Async HTTP |
| 15 | cryptography | >=44 | Encryption |
| 16 | tenacity | >=9 | Retry logic |
| 17 | websockets | >=13 | WebSocket support |
| 18 | typer | >=0.15 | CLI |
| 19 | rich | >=14 | Pretty terminal |
| 20 | pydantic-settings | >=2 | Settings management |
| 21 | passlib[bcrypt] | >=1.7 | Password hashing |
| 22 | setuptools | >=75 | Build tooling |
| 23 | hermes-agent | >=0.15 | Agent framework |

### Tool Configuration

[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]

**Key takeaways for code writing:**
- **Python 3.12+** — can use pathlib.Path, enum.Enum, dataclasses, async/await
- **Line length: 100** — not 88 (PEP 8 default)
- **mypy strict** — no Any without justification, no implicit Optional, no unchecked None
- **pytest** — tests in tests/, src on sys.path
- **hatchling** build backend — no setup.py needed

---

## 2. src/ Directory Structure & __init__.py Convention

**All 14 directories confirmed:**

src/__init__.py                    -> "# src module"
src/core/__init__.py               -> "# src/core module"
src/core/api/__init__.py           -> "# src/core/api module"
src/core/config/__init__.py        -> "# src/core/config module"
src/core/models/__init__.py        -> "# src/core/models module"
src/core/services/__init__.py      -> "# src/core/services module"
src/discord/__init__.py            -> "# src/discord module"
src/financial/__init__.py          -> "# src/financial module"
src/loops/__init__.py              -> "# src/loops module"
src/mcp/__init__.py                -> "# src/mcp module"
src/memory/__init__.py             -> "# src/memory module"
src/observability/__init__.py      -> "# src/observability module"
src/persona/__init__.py            -> "# src/persona module"
src/surveillance/__init__.py       -> "# src/surveillance module"

**__init__.py pattern:** ALL existing __init__.py files are single-line module comments. Convention: No __all__, no imports in __init__.py yet.

---

## 3. P1-015 StepPrompt Template — llm_router.py

**Path:** stepprompts/StepPrompts.md lines 4402-4551

### Key Patterns to Replicate:
- """docstring""" module-level
- import ordering: stdlib first, third-party next (no blank line between groups)
- logger = structlog.get_logger() at module level
- Enum for type-safe enums with string values
- @dataclass for config objects (not NamedTuple, not TypedDict)
- Optional[X] from typing (not X | None — template uses Optional)
- async def for all public methods
- httpx.AsyncClient for async HTTP
- response.raise_for_status() pattern
- logger.info/warning with structured context (keyword args, not f-strings)
- Exceptions: catch Exception, log, continue for fallback, raise RuntimeError at end
- self.client initialized in __init__, cleaned up in close()

### Expected Export:
from src.core.services.llm_router import LLMRouter, TaskType

---

## 4. P1-016 StepPrompt Template — prompt_loader.py

**Path:** stepprompts/StepPrompts.md lines 4554-4662

### Key Patterns to Replicate:
- """docstring""" at module level
- from pathlib import Path (stdlib import)
- Path.exists() and Path.read_text(encoding="utf-8") for file ops
- logger.info(...) with structured keyword args
- raise FileNotFoundError / raise ValueError — explicit, specific exception types
- list[str] type annotation (Python 3.12 native syntax, not List[str] from typing)
- Default None for mutable argument, then check inside
- Function-level docstrings with """description""" format
- Constants at module level (UPPER_CASE)
- memories[:10] slicing with enumerate(..., 1) for 1-based numbering
- "\n".join(context_parts) for string composition

### Expected Export:
from src.core.services.prompt_loader import load_system_prompt

---

## 5. Hermes Agent Integration Patterns

### Actual Import Name (Not What StepPrompts Says)

**StepPrompts says:** import hermes_agent
**Actual package:** Flat modules — use import hermes_constants or import hermes_bootstrap

| Import | Verified | Evidence |
|--------|----------|----------|
| import hermes_constants | ✅ PASS | P1-004 evidence, P1-005 evidence |
| import hermes_bootstrap | ✅ PASS | P1-004 evidence |
| import hermes_agent | ❌ NOT AVAILABLE | Package is flat modules |

**IMPORTANT:** For P1-015 and P1-016, Hermes modules are NOT imported directly. The llm_router.py uses httpx (not Hermes) to call the 9Router API directly. The prompt_loader.py is a standalone file loader. Hermes integration happens via the config.yaml at /home/guinevere/config/hermes/config.yaml, not via Python imports from these service modules.

---

## 6. 9Router Combo Configuration

**Evidence path:** docs/setup-evidence/P1/migration-9router/evidence.md

### Current Combo Routing (Final)

| Route Order | Model ID | Purpose |
|---|---|---|
| 1 (Primary) | opencode-go/deepseek-v4-flash | DeepSeek V4 Flash — primary runtime (laptop-independent) |
| 2 (Secondary) | openai-compatible-chat-.../gpt-5.5 | GPT-5.5 via cockpit (requires Windows laptop + Tailscale) |

### API Base URL
http://localhost:20128/v1

### What This Means for llm_router.py
- The base_url in MODELS config points to http://localhost:20128/v1
- Model names map to 9Router combo names: "gpt-5.5", "deepseek-v4-flash", "guinevere"
- The /v1/chat/completions endpoint is OpenAI-compatible
- Cost tracking is NOT duplicated in the router — it is handled by 9Router

---

## 7. ADR-001 & ADR-003 — Persona/Safety Constraints

### ADR-001: Persona Safety & Ethical Boundary
- Risk Level: CRITICAL
- Safety boundaries are architectural, not decorative
- HARD STOP, safe word, distress handling, consent, privacy all outrank persona flavor
- Yandere ceiling: Y5 (Y6 is FORBIDDEN)

**Impact on prompt_loader.py:**
- load_system_prompt() must validate safety elements
- If safety elements missing, raise ValueError — do NOT silently return an unsafe prompt

### ADR-003: Persona Drift Control & Validation
- Risk Level: HIGH
- Persona changes require drift logs, review criteria, rollback/safe-mode
- Prompt loaded FRESH for each conversation to prevent drift

**Impact on llm_router.py:**
- Primary (GPT-5.5) handles core reasoning, safety decisions, persona — where drift validation happens
- Sub-agent (DeepSeek) handles research, validation, code generation — non-persona work
- These must NOT be swapped accidentally

---

## 8. No Existing Test Files

**Finding:** No tests/ directory exists. No test files anywhere.
pytest configured in pyproject.toml but no existing patterns to replicate.

---

## 9. Summary: Exact Conventions to Follow

| Convention | Rule |
|---|---|
| Module docstring | """Description - Purpose.""" on line 1 |
| __init__.py | Single-line: # src/core/services module |
| Import order | stdlib first, then third-party |
| Logger | logger = structlog.get_logger() at module level |
| Enums | from enum import Enum — string values, typed |
| Data classes | @dataclass with from dataclasses import dataclass |
| Type annotations | Optional[X] from typing for optionals |
| Mutable defaults | None with guard |
| Async | async def, await client.post(...) for IO |
| HTTP | httpx.AsyncClient with timeout=60.0 |
| Error handling | Catch Exception, log with structlog, continue or re-raise |
| File IO | Path.read_text(encoding="utf-8") |
| Validation | Explicit checks + raise ValueError(...) |
| Constants | UPPER_CASE at module level |
| Line length | 100 characters max |
| Python | 3.12+ syntax (e.g. list[str] not List[str]) |
| Export | from src.core.services.llm_router import LLMRouter, TaskType |
| Export | from src.core.services.prompt_loader import load_system_prompt |

---

## Footer

| Field | Value |
|---|---|
| Source task | Research for P1-015/P1-016 implementation |
| Date | 2026-06-01 |
| Researcher | Guinevere (parent orchestrator) |
| Files covered | 13 source files across pyproject.toml, src/, stepprompts/, adr/, evidence/ |
| Verdict | Complete |
