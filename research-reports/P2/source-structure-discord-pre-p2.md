# Source Structure and Code Pattern Inventory - Pre-P2 Discord Bot Implementation

> **Purpose**: Complete map of existing source code, test patterns, evidence style, dependency analysis, and collision risk assessment before P2-001 through P2-003 execution.
>
> **Date**: 2026-06-01
> **Scope**: All Python files in src/, tests/, pyproject.toml, evidence style, P2 readiness artifacts
> **Prepared for**: P2-001 (Discord app creation), P2-002 (Bot token SOPS), P2-003 (Bot intents code)

---

## 1. Source Tree Overview

### 1.1 Full Python src/ Directory Tree

```
src/
+-- __init__.py                           # src module
+-- core/
|   +-- __init__.py                       # src/core module
|   +-- api/ (EMPTY)
|   +-- config/ (EMPTY)
|   +-- models/ (EMPTY)
|   +-- services/
|       +-- __init__.py
|       +-- hard_stop_handler.py          # 149 lines
|       +-- cost_tracker.py               # 68 lines
|       +-- llm_router.py                 # 93 lines
|       +-- prompt_loader.py              # 47 lines
+-- discord/ (EMPTY - only __init__.py)
+-- financial/ (EMPTY)
+-- loops/ (EMPTY)
+-- mcp/ (EMPTY)
+-- memory/ (EMPTY)
+-- observability/ (EMPTY)
+-- persona/ (EMPTY)
+-- surveillance/ (EMPTY)
```

### 1.2 Key Finding

14 Python files total in src/: - 4 actual service files - 1 FastAPI app (main.py) - 9 package stubs (single-line __init__.py)

src/discord/ is a single-line stub. All bot modules will be created from scratch in P2.

## 2. Existing Core Service Patterns (Must-Match)

### 2.1 hard_stop_handler.py (149 lines)
Gold standard deterministic safety code.

| Pattern | Implementation |
|---|---|
| Module-level logger | structlog.get_logger() |
| Enum state machine | SafetyState(Enum) |
| Dataclass models | HardStopEvent dataclass |
| Guard decision API | get_guard_decision -> dict |
| Property accessor | @property is_safe |

### 2.2 llm_router.py (93 lines)

| Pattern | Implementation |
|---|---|
| Enum for routing | TaskType(Enum) |
| Dataclass config | ModelConfig dataclass |
| Async class | httpx.AsyncClient |
| Fallback chain | try/except continue |
| structlog logging | logger.info(key=value) |

### 2.3 cost_tracker.py (68 lines)
| Redis pattern | redis.Redis + pipeline |

### 2.4 prompt_loader.py (47 lines)
| Pure functions | load_system_prompt() |
| Path-based IO | Path.read_text(encoding=utf-8) |

### 2.5 main.py (30 lines)
| FastAPI app | FastAPI(title=, version=) |
| Lifespan | asynccontextmanager |
| Health endpoint | @app.get(/health) |

## 3. Code Conventions Summary

| Convention | Rule |
|---|---|
| Logger | structlog.get_logger() at module level |
| Docstring | triple-quote summary triple-quote at file top |
| Types | Strict typing throughout |
| Dataclasses | @dataclass for data models |
| Enums | class X(Enum) for fixed categories |
| Async | async def for IO-bound operations |
| No if __name__ | None of the files use it |
| No type ignores | BLOCKING per AGENTS.md |
| Line length | 100 chars max (ruff) |
| Python | 3.12+ |

## 4. Dependency Analysis

### 4.1 discord.py Status

discord.py>=2.4 is MISSING from pyproject.toml but IS installed in the VPS venv (discord-py==2.4.0). Must add to pyproject.toml during P2-003.

### 4.2 Existing Compatible Dependencies

| Package | Status | Use in P2 |
|---|---|---|
| aiohttp>=3 | Already present | Required by discord.py |
| structlog>=24 | Already present | Logging |
| pydantic>=2 | Already present | Command models |
| httpx>=0.28 | Already present | REST API calls |
| tenacity>=9 | Already present | Reconnection retry |
| cryptography>=44 | Already present | Token decryption |

## 5. Test Patterns Inventory

### 5.1 Test Directory
tests/
+-- __init__.py
+-- safety/
|   +-- __init__.py
|   +-- test_hard_stop_handler.py  # 248 lines - deterministic
|   +-- test_hard_stop_model.py    # 224 lines - LLM integration
+-- smoke/
    +-- __init__.py
    +-- conftest.py                # 88 lines - shared fixtures
    +-- test_persona_basic.py      # 46 lines
    +-- test_safe_word.py          # 85 lines (2 xfail)
    +-- test_yandere_boundary.py   # 80 lines

### 5.2 Test Conventions

| Convention | Pattern |
|---|---|
| Fixture | def handler() -> Type: |
| Class grouping | class TestFeature: |
| Parametrize | @pytest.mark.parametrize |
| Asyncio | @pytest.mark.asyncio |
| Async client | pytest_asyncio.fixture |
| xfail | @pytest.mark.xfail(reason=) |
| Section comments | # === Section === |

## 6. Evidence Style

Evidence schema (AGENTS.md Appendix B):
1. What Was Done
2. Files Changed
3. Validation Results
4. Evidence Artifacts
5. Doc-Sync Impact
6. Boundary Compliance
7. Rollback / Re-run Safety
8. Design Decisions
9. Auditor Gate
10. Footer

Path convention: docs/setup-evidence/P2/STEP-P2-{NNN}/evidence.md
Auditor reports: audit-reports/P2/STEP-P2-{NNN}/step-p2-{nnn}-auditor-report.md

## 7. Existing Discord-Relevant Artifacts

### 7.1 Configuration (evidence artifact, not live)
File: docs/setup-evidence/P1/STEP-P1-005/config.yaml
Discord section: enabled=true, prefix=!, intents=[messages,guilds,members,message_content]

### 7.2 Discord UX Specification
File: docs/60-persona/63-DiscordUXSpec_v1.0.md
Covers: 4 categories, 13 channels, 34 slash commands, embed colors, bot presence, thread rules

### 7.3 Secrets Status
- Application ID: 1510873134981582858 (registered)
- Token: SOPS-encrypted at secrets/discord-secrets.yaml (on VPS)
- DO NOT access or print tokens in code, evidence, or reports

### 7.4 P2 Readiness (from P1-FINAL/07-p2-readiness.md)
VERDICT: GO - All 3 pre-conditions (C1, C2a, C2b) resolved.

## 8. P2-001 through P2-003 Detailed Scope

### 8.1 P2-001 (Manual - Discord App)
Status: ALREADY COMPLETE per C3 resolution
Action: Create evidence file documenting existing state

### 8.2 P2-002 (Security - Token SOPS)
Status: ALREADY COMPLETE per C3 resolution
Action: Create evidence file documenting decrypt test

### 8.3 P2-003 (Code - Bot Intents)
Files to CREATE: src/discord/intents.py, evidence.md, auditor report
Files to MODIFY: pyproject.toml (add discord.py>=2.4)

## 9. Collision Risk Map

### 9.1 Files to CREATE (zero collision)
- src/discord/intents.py (P2-003)
- Evidence files per step (P2-001/P2-002/P2-003)
- Auditor report files per step

### 9.2 Files to MODIFY (low risk)
- pyproject.toml - add discord.py>=2.4
- PROGRESS.md - mark steps complete
- CHECKLIST.md - mark steps complete

### 9.3 Zero Collision
- No existing src/discord/intents.py
- No other agent writing to src/discord/
- P2-001 and P2-002 are manual steps with no local file changes

## 10. Implementation Recommendations

### 10.1 Execution Order
1. P2-001: Create evidence directory and evidence.md (app already exists)
2. P2-002: Create evidence directory and evidence.md (token already encrypted)
3. P2-003: Add discord.py>=2.4 to pyproject.toml
4. P2-003: Create src/discord/intents.py with get_intents() function
5. P2-003: Verify with Python import test
6. P2-003: Run lsp_diagnostics on changed files
7. P2-003: Create evidence and auditor report
8. Update PROGRESS.md and CHECKLIST.md

### 10.2 Code Pattern for intents.py
```python
"""Discord bot intents configuration."""
import discord
import structlog

logger = structlog.get_logger()

def get_intents() -> discord.Intents:
    intents = discord.Intents.default()
    intents.message_content = True
    intents.guilds = True
    intents.members = True
    intents.presences = True
    intents.messages = True
    intents.reactions = True
    intents.voice_states = True
    return intents
```

### 10.3 Risk Mitigation

| Risk | Probability | Mitigation |
|---|---|---|
| discord.py not in pyproject.toml | CERTAIN | Add before code |
| Portal settings vs code mismatch | MEDIUM | Verify both independently |
| Evidence path misalignment | LOW | Follow P1 convention |

## 11. Summary of Key Findings

1. src/discord/ is empty - single __init__.py stub
2. Code patterns are consistent - structlog, typed dataclasses, Enum, async
3. discord.py is NOT in pyproject.toml but IS in VPS venv
4. P2-001 and P2-002 are already done per C3 resolution
5. P2-003 is the first actual code step - create src/discord/intents.py
6. Zero collision risk for P2-001 through P2-003
7. Evidence pattern is well-established from P1
8. Test pattern is well-established from P1
9. Discord UX Spec (docs/60-persona/63-DiscordUXSpec_v1.0.md) is canonical
10. Configuration loading does not use pydantic-settings yet

---

## Footer

- Source task: Pre-P2 source structure exploration
- Date: 2026-06-01
- Implementer: Guinevere (parent explorer)
- Report path: research-reports/P2/source-structure-discord-pre-p2.md
- Next action: Begin P2-001 evidence documentation, then P2-003 code implementation