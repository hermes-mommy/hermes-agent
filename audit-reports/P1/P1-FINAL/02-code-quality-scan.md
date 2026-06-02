# P1 Code Quality Scan — Final Audit

**Scope**: All P1-authored Python files (src/core/services/, src/core/main.py, tests/smoke/*, tests/safety/*)
**Date**: 2026-06-01
**Tooling**: basedpyright (LSP), grep, manual review
**Requested dimensions**: type annotations, error handling, docstrings, code smells, import organization, deps vs imports

---

## 1. Files Audited

### Source Files (5)
| File | Lines | Type |
|---|---|---|
| `src/core/services/llm_router.py` | 93 | LLM routing with fallback chain |
| `src/core/services/prompt_loader.py` | 47 | System prompt loading + validation |
| `src/core/services/hard_stop_handler.py` | 149 | Pre-LLM HARD STOP guard |
| `src/core/services/cost_tracker.py` | 68 | Redis-backed LLM cost tracking |
| `src/core/main.py` | 30 | FastAPI application entry point |

### Test Files (6)
| File | Lines | Type |
|---|---|---|
| `tests/smoke/conftest.py` | 88 | Shared fixtures for smoke tests |
| `tests/smoke/test_safe_word.py` | 85 | HARD STOP neutral mode smoke tests |
| `tests/smoke/test_persona_basic.py` | 46 | Identity/empathy/creator persona tests |
| `tests/smoke/test_yandere_boundary.py` | 80 | Y4/Y5/Y6 boundary verification |
| `tests/safety/test_hard_stop_handler.py` | 248 | Deterministic unit tests (no LLM) |
| `tests/safety/test_hard_stop_model.py` | 224 | GPT-5.5 model compliance tests |

### Config Files (1)
| File | Lines |
|---|---|
| `pyproject.toml` | 46 | Project dependencies, tool configuration |

---

## 2. Type Annotations Analysis

### 2.1 Missing Return Type Annotations

| File | Function | Line | Issue |
|---|---|---|---|
| `src/core/services/cost_tracker.py` | `__init__` | 13 | Missing `-> None` |
| `src/core/services/cost_tracker.py` | `record_cost` | 25 | Missing `-> None` |
| `src/core/services/cost_tracker.py` | `check_budget` | 45 | Bare `dict` return — no type arguments |
| `src/core/main.py` | `health()` | 24 | Missing `-> dict[str, str]` |
| `src/core/main.py` | `root()` | 29 | Missing `-> dict[str, str]` |

### 2.2 Deprecated `typing` Imports (Python 3.10+)

| File | Line | Deprecated | Preferred |
|---|---|---|---|
| `src/core/services/llm_router.py` | 5 | `from typing import Optional, Union` | Use `\| None` and `\|` syntax |
| `src/core/services/llm_router.py` | 57-58 | `Optional[int]`, `Union[ModelConfig, None]` | `int \| None`, `ModelConfig \| None` |
| `src/core/services/hard_stop_handler.py` | 15 | `from typing import Any` | Acceptable (detailed below) |

### 2.3 `Any` Usage

| File | Line | Detail | Severity |
|---|---|---|---|
| `src/core/services/hard_stop_handler.py` | 125 | `dict[str, Any]` — `get_guard_decision()` return type | **WARN**: Explicit `Any` flagged by `reportExplicitAny` |
| `structlog` logger vars | all files | Logger type inferred as `Any` | **LOW**: Structlog typed stubs not resolvable; false positive |

**Verdict**: No `Any` abuse found. The single `dict[str, Any]` is justified by dynamic dict shape. No `# type: ignore`, no `@ts-ignore`, no `as any` patterns detected.

### 2.4 Missing Parameter Annotations

| File | Function | Parameter | Line |
|---|---|---|---|
| `src/core/services/llm_router.py` | `chat()` | `**kwargs` | 58 |
| `src/core/services/llm_router.py` | `chat()` | `messages: list[dict]` — missing inner type args | 57 |

### 2.5 Test Fixture Type Gaps

`tests/smoke/conftest.py` produces cascading type shadow (all smoke tests get untyped `chat` fixture):

| Function | Parameter | Issue | Line |
|---|---|---|---|
| `chat()` fixture | `client` | Missing annotation | 67 |
| `chat()` fixture | `system_prompt` | Missing annotation | 67 |
| `safe_json()` | return type | Bare `dict` | 36 |

---

## 3. Error Handling

### 3.1 try/except Blocks Found

| File | Line | Pattern | Assessment |
|---|---|---|---|
| `src/core/services/llm_router.py` | 66-88 | `except Exception as e:` -> continue -> final `raise RuntimeError(...)` | **PASS**: Expected fallback chain. Logs error + next model. |

### 3.2 Empty `except:` Blocks

**None found in any P1 file.** PASS.

### 3.3 Error Handling Coverage

| File | Risk Area | Handling | Assessment |
|---|---|---|---|
| `prompt_loader.py` | File I/O + validation | `FileNotFoundError` raised, `ValueError` raised | PASS: Deterministic |
| `cost_tracker.py` | Redis calls | None (propagates) | **WARN**: `redis.ConnectionError` could crash on Redis down |
| `hard_stop_handler.py` | Deterministic only | None needed | PASS |
| `main.py` | FastAPI startup | None needed | PASS: Framework handles |
| `tests/conftest.py` | HTTP calls | `raise_for_status()` | PASS |

---

## 4. Docstrings

### 4.1 Source File Coverage

| File | Functions | Has Docstring | Missing |
|---|---|---|---|
| `src/core/services/llm_router.py` | 3 | Module, class, `chat` | `__init__`, `close()` |
| `src/core/services/prompt_loader.py` | 2 | All | None |
| `src/core/services/hard_stop_handler.py` | 6 | Module, most methods | `is_safe` (trivial property) |
| `src/core/services/cost_tracker.py` | 4 | All | None |
| `src/core/main.py` | 3 | Module, lifespan | `health()`, `root()` |

### 4.2 Quality Assessment
- **hard_stop_handler.py**: ★★★★★ — architecture overview, safety policy cross-refs, clear params.
- **cost_tracker.py**: ★★★★☆ — clear budget threshold intent.
- **prompt_loader.py**: ★★★★☆ — concise with safety validation context.
- **llm_router.py**: ★★★☆☆ — adequate but could detail fallback chain.
- **main.py**: ★★☆☆☆ — trivial endpoints, low severity.

---

## 5. Import Organization

### 5.1 Violations (All Source Files)

| File | Current Order (first 3 imports) | Expected Order | Severity |
|---|---|---|---|
| `llm_router.py` | httpx (3rd) -> structlog (3rd) -> enum (stdlib) | stdlib first | WARN |
| `prompt_loader.py` | structlog (3rd) -> pathlib (stdlib) | stdlib first | WARN |
| `hard_stop_handler.py` | re -> time -> structlog (3rd) | stdlib grouped | WARN |
| `cost_tracker.py` | os (stdlib) -> redis (3rd) -> structlog (3rd) | stdlib grouped | WARN |
| `main.py` | structlog (3rd) -> fastapi (3rd) -> contextlib (stdlib) | stdlib first | WARN |

**All 5 source files violate PEP8 import ordering.** Stdlib and 3rd-party imports are interleaved.

### 5.2 Unused Import

| File | Import | Line | Issue |
|---|---|---|---|
| `cost_tracker.py` | `from datetime import datetime` | 5 | `datetime` never called; only `date` is used |

---

## 6. Anti-Pattern Scan

### 6.1 Searched Patterns — Not Found

| Pattern | Status |
|---|---|
| `# type: ignore` | Not found |
| `@ts-ignore` | Not found |
| `as any` | Not found |
| `empty except:` | Not found |
| `bare Any` | Not found |
| `FIXME`, `TODO`, `HACK`, `XXX` | Not found |

### 6.2 Magic Numbers

| File | Line | Value | Context | Assessment |
|---|---|---|---|---|
| `cost_tracker.py` | 48 | `30` | Monthly cap default | LOW: Sensible fallback |
| `cost_tracker.py` | 60-67 | `1.0`, `0.833`, `0.5` | Budget thresholds | **WARN**: Extract to named constants |
| `cost_tracker.py` | 66 | `1.0` | Minimum for NORMAL_ALERT | **WARN**: Unclear threshold origin |

### 6.3 Code Duplication

| Pattern | Locations | Assessment |
|---|---|---|
| 9Router `data: [DONE]` stripping | `conftest.py:40-42`, `test_hard_stop_model.py:56-58` | **WARN**: Identical cleanup duplicated |
| JSON response parsing | `llm_router.py:79`, `test_hard_stop_model.py:60-61`, `conftest.py:43` | **WARN**: Parser logic in 3 places with slight variations |

---

## 7. pyproject.toml Dependency Analysis

### 7.1 Active Dependencies (Used in P1)

| Dep | Used In | Status |
|---|---|---|
| `fastapi>=0.115` | `main.py` | PASS |
| `redis>=5` | `cost_tracker.py` | PASS |
| `httpx>=0.28` | `llm_router.py`, `conftest.py`, `test_hard_stop_model.py` | PASS |
| `structlog>=24` | All 5 core files | PASS |

### 7.2 Declared but Not Imported in P1

`uvicorn`, `pydantic`, `sqlalchemy`, `asyncpg`, `alembic`, `python-dotenv`, `apscheduler`, `sentry-sdk`, `prometheus-client`, `aiohttp`, `cryptography`, `tenacity`, `websockets`, `typer`, `rich`, `pydantic-settings`, `passlib`, `setuptools`, `hermes-agent`

All are planned for P2+ use. **No action needed** for P1 scope.

### 7.3 Missing Dependencies (P1 Scope)

| Import Used | Present? | Must Add |
|---|---|---|
| `pytest` | No | **YES** — needs `[project.optional-dependencies] test` |
| `pytest-asyncio` / `pytest_asyncio` | No | **YES** — needs same test group |

---

## 8. Test Coverage & Patterns

### 8.1 Structure Overview

**Deterministic Unit Tests** (`test_hard_stop_handler.py`):
- 16 methods across 6 test classes
- 50+ parametrized test cases
- 100% deterministic, zero network calls
- State machine: trigger -> safe -> recovery -> trigger tested bidirectionally
- Audit trail, guard decision API, false positive prevention all covered
- **Rating: ★★★★★**

**Model Compliance** (`test_hard_stop_model.py`):
- 8 methods across 3 test classes
- Real GPT-5.5 via 9Router (not mock)
- 7 semantic trigger parametrizations
- Neutral mode, punishment, surveillance threat, auto-resume checks
- **Rating: ★★★★☆**

**Smoke Tests** (3 files):
- 9 total tests; identity, empathy, creator context, HARD STOP, yandere Y4/Y5/Y6, distress D0-D4
- `test_safe_word.py` uses honest `xfail` markers for known DeepSeek limitation
- Good forbidden-term sets with safety policy cross-refs
- **Rating: ★★★☆☆**

### 8.2 Conftest Fixture Pattern (Type Gap)

The `chat` fixture at `conftest.py:67` has unannotated `client` and `system_prompt` parameters, causing all consuming test functions to receive untyped callables. This is the root cause of ~25 LSP warnings across smoke tests.

---

## 9. LSP Diagnostics Summary

### 9.1 Errors: ZERO
No LSP errors in any P1 file.

### 9.2 Warning Breakdown (~117 total)

| Source | Count | Category |
|---|---|---|
| Structlog `reportAny` (all files) | ~60 | False positive — structlog stubs |
| Test type propagation (smoke tests) | ~25 | From conftest untyped fixture |
| Redis pipeline `reportUnknownMemberType` | ~12 | Expected with dynamic Redis API |
| Unused call results (unit tests) | ~7 | Intentional — testing side effects |
| Various (deprecated typing, unused param, unused import) | ~13 | Genuine issues |

### 9.3 Pre-existing vs Introduced

All warnings are pre-existing patterns. **No regressions introduced by P1 code.**

---

## 10. Verdict

| Dimension | Status | Notes |
|---|---|---|
| **Type Annotations** | NEEDS REVIEW | Missing return types (cost_tracker, main); deprecated Optional/Union (llm_router) |
| **Error Handling** | PASS | No empty except, proper fallback, deterministic where possible |
| **Docstrings** | PASS | Strong coverage; trivial gaps only |
| **Anti-Patterns** | PASS | Zero `# type: ignore`, `as any`, empty except, FIXME, HACK |
| **Import Order** | NEEDS REVIEW | All 5 source files violate stdlib-first |
| **Deps vs Imports** | NEEDS REVIEW | Missing pytest/pytest-asyncio; unused datetime import |
| **LSP Cleanliness** | NEEDS REVIEW | 117 warnings (mostly false-positive structlog/Redis) |
| **Test Quality** | PASS | Excellent unit tests; good fixture structure; honest xfail |

### Gate Verdict: **NEEDS MINOR FIXES**

**No blocking items**. Recommended fixes (8 items) in next-steps section below.

---

## 11. Implementation Findings Record

All findings are documented with file path, line number, severity, and recommendation.

### Findings Summary

| ID | Severity | File | Line(s) | Category | Summary |
|---|---|---|---|---|---|
| CQ-01 | LOW | cost_tracker.py | 13 | Type annotation | Missing `-> None` on `__init__` |
| CQ-02 | LOW | cost_tracker.py | 25 | Type annotation | Missing `-> None` on `record_cost` |
| CQ-03 | LOW | cost_tracker.py | 45 | Type annotation | Bare `dict` return — add `dict[str, float \| str]` |
| CQ-04 | LOW | cost_tracker.py | 5 | Unused import | `datetime` imported but unused |
| CQ-05 | MEDIUM | cost_tracker.py | 60-67 | Magic numbers | Budget ratios `0.833`, `0.5` should be named constants |
| CQ-06 | MEDIUM | cost_tracker.py | 48 | Magic number | `30` as default cap could be named constant |
| CQ-07 | LOW | llm_router.py | 5, 57-58, 65 | Deprecated typing | `Optional`/`Union` — use `\|` syntax for Python 3.12 |
| CQ-08 | LOW | llm_router.py | 57 | Type annotation | `messages: list[dict]` missing inner type args |
| CQ-09 | LOW | llm_router.py | 58 | Type annotation | `**kwargs` untyped |
| CQ-10 | LOW | main.py | 24, 29 | Type annotation | Missing return types on `health()` and `root()` |
| CQ-11 | MEDIUM | ALL src files | various | Import order | Stdlib before 3rd-party ordering violation |
| CQ-12 | MEDIUM | pyproject.toml | 6-29 | Missing deps | `pytest` and `pytest-asyncio` not declared as test deps |
| CQ-13 | LOW | ALL smoke tests | various | Type shadow | `chat` fixture propagates untyped callable |
| CQ-14 | LOW | conftest.py / test_hard_stop_model.py | 40-42, 56-58 | Duplication | `data: [DONE]` stripping duplicated |
