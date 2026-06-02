# D01 — Code Architecture & Module Quality Audit

**Audit:** P5 Agent Loop — Code Architecture & Module Quality
**Date:** 2026-06-02
**Scope:** `src/loops/` (14 .py files + 7 phase handlers) and `src/core/api/` (3 .py files)
**Total files reviewed:** 24
**Auditor:** D01 — independent auditor

---

## 1. Module Dependency Graph

### 1.1 Internal Dependency Map

```
                    ┌──────────────────────────────────┐
                    │        state_machine.py          │ (foundation — zero internal deps)
                    │  LoopPhase, LoopStatus, PHASE_NAMES│
                    └───────┬─────────────────┬────────┘
                            │                 │
              ┌─────────────┼─────────────────┼──────────────────────┐
              │             │                 │                      │
    ┌─────────▼──┐  ┌───────▼───┐  ┌─────────▼────┐  ┌──────────────▼──────┐
    │ artifacts  │  │ evidence  │  │ phases/__init__│  │ phases/research     │
    │ (no deps)  │  │ (→ artfcts│  │ (→ state_mach │  │ plan_delegate       │
    └────────────┘  │  + state) │  │  + 7 handlers) │  │ delegate            │
    ┌────────────┐  └───────┬───┘  └─────────┬────┘  │ execute             │
    │ contract   │          │               │        │ validate_audit      │
    │ (no deps)  │          │               │        │ update_docs         │
    └────────────┘          │               │        │ setup_evidence      │
    ┌────────────┐          │               │        │ (each → state_mach) │
    │ cost       │          │               │        └─────────────────────┘
    │ (→ core.svc│          │               │
    │  external) │          │               │
    └────────────┘          │               │
    ┌────────────┐          │               │
    │ enforcer   │          │               │
    │ (no deps)  │          │               │
    └────────────┘          │               │
    ┌────────────┐          │               │
    │ guardian   │          │               │
    │ (no deps)  │          │               │
    └────────────┘          │               │
    ┌────────────┐          │               │
    │ hash_anchor│          │               │
    │ (no deps)  │          │               │
    └────────────┘          │               │
    ┌────────────┐          │               │
    │ sub_agent  │          │               │
    │ (no deps)  │          │               │
    └────────────┘          │               │
    ┌────────────┐          │               │
    │ verify     │          │               │
    │ (no deps)  │          │               │
    └────────────┘          │               │
                            │               │
                    ┌───────▼───────────────▼────┐
                    │        manager.py          │ (orchestration)
                    │ (→ evidence, guardian,     │
                    │  phases, state_machine)     │
                    └───────────┬───────────────┘
                                │
                    ┌───────────▼───────────────┐
                    │       scheduler.py         │ (orchestration)
                    │  (→ manager)               │
                    └────────────────────────────┘

    core/api/auth.py (no internal deps)
    core/api/routes.py (→ auth)
```

### 1.2 Circular Dependencies

**RESULT: ZERO circular dependencies found.** The dependency graph is a clean directed acyclic graph (DAG) with a clear bottom-up flow: foundation → composition → orchestration → public API.

### 1.3 Cross-Package Dependency

| Source | Target | Assessment |
|---|---|---|
| `src/loops/cost.py` | `src.core.services.cost_tracker` | ⚠️ Cross-package. Acceptable but creates coupling from `loops` to `core.services`. Worth documenting as an intentional coupling point. |

---

## 2. Layer Separation

Four layers identified:

| Layer | Modules | Verdict |
|---|---|---|
| **Foundation** | state_machine, artifacts, contract, cost, enforcer, guardian, hash_anchor, sub_agent, verify, auth | ✓ Clean — zero internal dependencies |
| **Composition** | evidence (→ artifacts + state_machine), phases/__init__ (→ state_machine + handlers), routes (→ auth) | ✓ Clean — only depends on foundation |
| **Orchestration** | manager (→ evidence + guardian + phases + state_machine), scheduler (→ manager) | ✓ Clean — only depends on composition |
| **Public API** | loops/__init__.py, core/api/__init__.py | ✓ Clean — re-exports from lower layers |

**Verdict: PASS** — Layer separation is textbook-clean.

---

## 3. __all__ Exports Verification

### 3.1 `src/loops/__init__.py` — 22 symbols

| Symbol | Source Module | Resolves? |
|---|---|---|
| `LoopPhase` | state_machine | ✓ IntEnum |
| `LoopStateMachine` | state_machine | ✓ class |
| `LoopStatus` | state_machine | ✓ Enum |
| `PHASE_NAMES` | state_machine | ✓ dict |
| `evidence_dir` | artifacts | ✓ function |
| `write_artifact` | artifacts | ✓ function |
| `read_artifact` | artifacts | ✓ function |
| `artifact_exists` | artifacts | ✓ function |
| `EvidencePipeline` | evidence | ✓ class |
| `LoopManager` | manager | ✓ class |
| `LoopScheduler` | scheduler | ✓ class |
| `LoopCostTracker` | cost | ✓ class |
| `LoopGuardian` | guardian | ✓ class |
| `TodoEnforcer` | enforcer | ✓ class |
| `compute_line_hash` | hash_anchor | ✓ function |
| `validate_edit` | hash_anchor | ✓ function |
| `HashAnchorError` | hash_anchor | ✓ exception |
| `SubAgentSpawner` | sub_agent | ✓ class |
| `TaskContract` | contract | ✓ Pydantic model |
| `build_contract` | contract | ✓ function |
| `contract_to_prompt` | contract | ✓ function |
| `OutputVerifier` | verify | ✓ class |

**Result: 22/22 symbols resolve correctly.** ✓

### 3.2 `src/loops/phases/__init__.py` — 2 symbols

| Symbol | Resolves? |
|---|---|
| `PHASE_REGISTRY` | ✓ dict[LoopPhase, Callable] |
| `get_phase_handler` | ✓ function |

**Result: 2/2 symbols resolve correctly.** ✓

### 3.3 `src/core/api/__init__.py`

**No `__all__` defined.** File contains only a comment (`# src/core/api module`). The `router`, `get_api_key`, `LoopRequest`, and `LoopResponse` symbols are not re-exported.

⚠️ **Finding:** Missing `__all__` in `core/api/__init__.py`. While FastAPI typically imports `router` directly from `routes.py`, the package should at minimum export `router` for consistency with project conventions.

---

## 4. Code Duplication

### 4.1 Duplicated `_EXECUTION_PHASES` list

**Found in:** `evidence.py` (line ~50) and `manager.py` (line ~28)

```python
# evidence.py
_EXECUTION_PHASES = [
    LoopPhase.RESEARCH,
    LoopPhase.PLAN_AND_DELEGATE,
    LoopPhase.DELEGATE,
    LoopPhase.EXECUTE,
    LoopPhase.VALIDATE_AND_AUDIT,
    LoopPhase.UPDATE_DOCUMENTS,
    LoopPhase.SETUP_EVIDENCE,
]

# manager.py
_EXECUTION_PHASES = [
    LoopPhase.RESEARCH,
    LoopPhase.PLAN_AND_DELEGATE,
    LoopPhase.DELEGATE,
    LoopPhase.EXECUTE,
    LoopPhase.VALIDATE_AND_AUDIT,
    LoopPhase.UPDATE_DOCUMENTS,
    LoopPhase.SETUP_EVIDENCE,
]
```

**Severity: LOW** — Identical lists. Should be defined once in `state_machine.py` and imported by both consumers, or defined in a shared constant location.

### 4.2 Duplicated `goal_section` pattern

**Found in:** all 7 phase handlers

```python
goal_section = f"\n**Goal:** {goal}\n" if goal else ""
```

Appears identically in `research.py`, `plan_delegate.py`, `delegate.py`, `execute.py`, `validate_audit.py`, `update_docs.py`, `setup_evidence.py`.

**Severity: LOW** — Trivial one-liner but repeated 7 times. Could be extracted to a shared utility.

### 4.3 Duplicated artifact header template

All 7 phase handlers build artifacts starting with the same header structure:
```python
f"""\
# {REPORT_TITLE}

**Loop:** `{loop_id}`
**Phase:** {_PHASE_NAME} (Phase {_PHASE.value})
**Task:** {task}
{goal_section}
---
...
```

**Severity: LOW** — By-design template duplication for uniformity. Acceptable as-is, but a shared `artifact_header()` helper would DRY this up.

### 4.4 Phase constants pattern

Each handler defines:
```python
_PHASE = LoopPhase.*PHASE_NAME*
_PHASE_NAME = "*Human Name*"
```

While this is intentional for handler identity, a base class or factory pattern could eliminate the duplication.

---

## 5. Single Responsibility Analysis

| Module | Responsibility | SRP Score |
|---|---|---|
| `state_machine.py` | Phase/status state management + serialization | ✓ PASS |
| `artifacts.py` | Evidence directory management + file I/O | ✓ PASS |
| `contract.py` | Task contract model + prompt generation | ✓ PASS |
| `cost.py` | Per-loop cost tracking via Redis | ✓ PASS |
| `enforcer.py` | Idle agent detection + enforcement | ✓ PASS |
| `evidence.py` | Evidence collection + final report generation | ✓ PASS |
| `guardian.py` | Loop health monitoring (heartbeat, stall, resource) | ✓ PASS |
| `hash_anchor.py` | SHA-256 edit validation | ✓ PASS |
| `manager.py` | Loop lifecycle orchestration (create, run, stop, list) | ✓ PASS |
| `scheduler.py` | Cron-based loop scheduling | ✓ PASS |
| `sub_agent.py` | Sub-agent record management (spawn, track, complete, fail) | ✓ PASS |
| `verify.py` | Scaffold-based output verification | ✓ PASS |
| `research.py` | Phase 1 handler | ✓ PASS |
| `plan_delegate.py` | Phase 2 handler | ✓ PASS |
| `delegate.py` | Phase 3 handler | ✓ PASS |
| `execute.py` | Phase 4 handler | ✓ PASS |
| `validate_audit.py` | Phase 5 handler | ✓ PASS |
| `update_docs.py` | Phase 6 handler | ✓ PASS |
| `setup_evidence.py` | Phase 7 handler | ✓ PASS |
| `auth.py` | API key authentication | ✓ PASS |
| `routes.py` | HTTP route definitions | ✓ PASS |

**Verdict:** 21/21 modules have clear single responsibility. **PASS.**

---

## 6. Naming Conventions

### 6.1 Module Naming

| Convention | Pattern | Examples | Status |
|---|---|---|---|
| Modules | `snake_case.py` | `state_machine.py`, `hash_anchor.py`, `validate_audit.py` | ✓ Consistent |
| Packages | `snake_case/` | `phases/`, `api/` | ✓ Consistent |

### 6.2 Symbol Naming

| Convention | Pattern | Examples | Status |
|---|---|---|---|
| Classes | PascalCase | `LoopPhase`, `OutputVerifier`, `TaskContract` | ✓ Consistent |
| Functions | snake_case | `compute_line_hash`, `build_contract`, `get_phase_handler` | ✓ Consistent |
| Constants | UPPER_SNAKE | `HEARTBEAT_INTERVAL`, `PHASE_NAMES`, `_EVIDENCE_ROOT`, `_KEY_PREFIX` | ✓ Consistent |
| Private | `_underscore` | `_as_list`, `_PHASE_SLUGS`, `_EXECUTION_PHASES` | ✓ Consistent |
| Enums | PascalCase + UPPER values | `LoopPhase.RESEARCH`, `LoopStatus.RUNNING` | ✓ Consistent |

### 6.3 Logger Event Names

⚠️ **Minor inconsistency found:**

| Style | Examples | Files |
|---|---|---|
| Dot-separated | `loop_state_machine.created`, `phase.research.start`, `artifacts.artifact_written` | state_machine, phases/*, artifacts, evidence, guardian, manager, scheduler, verify |
| Underscore-separated | `contract_built`, `agent_tracked`, `pasukan_mommy_spawned`, `todo_enforcer_initialized` | contract, enforcer, sub_agent |

**Severity: LOW** — The codebase predominantly uses dot-separated names. A few modules use underscore style. Recommend standardizing on dot-separated namespace convention (e.g., `contract.built`, `enforcer.agent_tracked`).

---

## 7. File & Function Sizes

### 7.1 File Sizes

| File | Est. Lines | Limit | Status |
|---|---|---|---|
| `state_machine.py` | ~220 | 300 | ✓ |
| `manager.py` | ~210 | 300 | ✓ |
| `cost.py` | ~175 | 300 | ✓ |
| `guardian.py` | ~170 | 300 | ✓ |
| `scheduler.py` | ~170 | 300 | ✓ |
| `verify.py` | ~170 | 300 | ✓ |
| `evidence.py` | ~160 | 300 | ✓ |
| `sub_agent.py` | ~140 | 300 | ✓ |
| `enforcer.py` | ~130 | 300 | ✓ |
| `hash_anchor.py` | ~130 | 300 | ✓ |
| `contract.py` | ~120 | 300 | ✓ |
| `artifacts.py` | ~100 | 300 | ✓ |
| `routes.py` | ~90 | 300 | ✓ |
| `setup_evidence.py` | ~90 | 300 | ✓ |
| `auth.py` | ~70 | 300 | ✓ |
| Phase handlers (5x) | ~70-80 | 300 | ✓ |
| `research.py` | ~80 | 300 | ✓ |
| `phases/__init__.py` | ~50 | 300 | ✓ |
| `loops/__init__.py` | ~33 | 300 | ✓ |
| `core/api/__init__.py` | 2 | 300 | ✓ |

**Result:** 0 files exceed 300 lines. **PASS.**

### 7.2 Function Sizes

| Function | Module | Est. Lines | Limit | Status |
|---|---|---|---|---|
| `LoopManager._run_loop` | manager | ~55 | 50 | ⚠️ Slight excess |
| `EvidencePipeline.generate_final_report` | evidence | ~50 | 50 | ✓ At limit |
| `LoopCostTracker.record_loop_cost` | cost | ~35 | 50 | ✓ |
| `LoopGuardian.monitor` | guardian | ~35 | 50 | ✓ |
| `OutputVerifier.verify_command` | verify | ~30 | 50 | ✓ |
| All other methods | — | <30 | 50 | ✓ |

**Assessment:** `_run_loop` at ~55 lines is slightly above the 50-line target but includes try/except/finally error handling which inflates line count. Acceptable.

**Verdict: PASS** — No egregious violations.

---

## 8. Phase Handler Uniformity

### 8.1 Signature Comparison

| # | Phase | Handler | Signature |
|---|---|---|---|
| 1 | Research | `phases/research.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 2 | Plan & Delegate | `phases/plan_delegate.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 3 | Delegate | `phases/delegate.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 4 | Execute | `phases/execute.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 5 | Validate & Audit | `phases/validate_audit.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 6 | Update Documents | `phases/update_docs.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |
| 7 | Setup Evidence | `phases/setup_evidence.py::run` | `async def run(loop_id: str, task: str, goal: str = "") -> str` |

**Result: 7/7 identical.** ✓

### 8.2 Structure Comparison

All 7 handlers follow the identical structure:
1. `from __future__ import annotations`
2. `import structlog` + `from src.loops.state_machine import LoopPhase`
3. `_PHASE` module constant
4. `_PHASE_NAME` module constant
5. `async def run(loop_id, task, goal="") -> str`
6. Log start with structured logger
7. Build `goal_section`
8. Build artifact f-string
9. Log complete with artifact length
10. Return artifact string

**Result:** Perfect structural uniformity across all 7 handlers. **PASS.**

### 8.3 Registry Mapping

The `PHASE_REGISTRY` in `phases/__init__.py` correctly maps each `LoopPhase` value to its handler:

```
LoopPhase.RESEARCH          → research_run      ✓
LoopPhase.PLAN_AND_DELEGATE → plan_delegate_run  ✓
LoopPhase.DELEGATE          → delegate_run       ✓
LoopPhase.EXECUTE           → execute_run        ✓
LoopPhase.VALIDATE_AND_AUDIT→ validate_audit_run ✓
LoopPhase.UPDATE_DOCUMENTS  → update_docs_run    ✓
LoopPhase.SETUP_EVIDENCE    → setup_evidence_run ✓
```

**Result:** 7/7 phases registered. COMPLETE terminal correctly excluded. **PASS.**

---

## 9. Public API Surface Assessment

### 9.1 `src/loops/__init__.py` — 22 symbols

| Category | Count | Symbols |
|---|---|---|
| Core types | 4 | `LoopPhase`, `LoopStateMachine`, `LoopStatus`, `PHASE_NAMES` |
| Artifact I/O | 4 | `evidence_dir`, `write_artifact`, `read_artifact`, `artifact_exists` |
| Orchestration | 4 | `EvidencePipeline`, `LoopManager`, `LoopScheduler`, `LoopCostTracker` |
| Monitoring | 2 | `LoopGuardian`, `TodoEnforcer` |
| Hash | 3 | `compute_line_hash`, `validate_edit`, `HashAnchorError` |
| Sub-agents | 1 | `SubAgentSpawner` |
| Contracts | 3 | `TaskContract`, `build_contract`, `contract_to_prompt` |
| Verification | 1 | `OutputVerifier` |
| **Total** | **22** | |

**Assessment:** The surface is broad but each symbol serves a distinct external consumer role. While 22 is on the larger side, the modules form a coherent system (Agent Loop Engine). Splitting into sub-packages (`loops.core`, `loops.contracts`, `loops.agents`) is a future consideration, not a defect.

⚠️ **Finding:** `PHASE_NAMES` is exported as a **mutable dict**. External consumers can mutate it. Should be read-only (`types.MappingProxyType` or `frozenset`).

### 9.2 `src/core/api/__init__.py`

**Surface is empty.** No `__all__`, no re-exports.

⚠️ **Finding:** Consumers must import directly from `src.core.api.routes` (for `router`) and `src.core.api.auth` (for `get_api_key`). The `__init__.py` should minimally export `router`.

---

## 10. Additional Findings

### 10.1 Stub Implementations

All 7 phase handlers currently return **template/placeholder markdown** — they do not perform real LLM-powered work. Each handler explicitly documents this as expected for the current wave. This is a known architectural state, not a defect.

### 10.2 Routes Not Wired to LoopManager

`routes.py` endpoints return hardcoded/stub data:

| Endpoint | Behavior | Wired to LoopManager? |
|---|---|---|
| `GET /api/v1/loops` | Returns `{"loops": [], "active": 0, "completed": 0}` | ❌ No |
| `POST /api/v1/loops` | Generates UUID, returns "pending" status | ❌ No |
| `GET /api/v1/loops/{id}` | Returns `status: "unknown"` | ❌ No |
| `POST /api/v1/loops/{id}/cancel` | Returns `status: "cancelled"` message | ❌ No |

`routes.py` does not import `LoopManager`. This is intentional for the current wave (API skeleton before full wiring) but should be tracked.

### 10.3 Auth Gap on Read Endpoints

| Endpoint | API Key Required? |
|---|---|
| `GET /api/v1/loops` | ❌ No `Depends(get_api_key)` |
| `POST /api/v1/loops` | ✓ Yes |
| `GET /api/v1/loops/{id}` | ❌ No `Depends(get_api_key)` |
| `POST /api/v1/loops/{id}/cancel` | ✓ Yes |

May be intentional (public read access, authenticated writes) but should be a documented decision.

### 10.4 Error Handling Gap in Cost Tracker

In `cost.py::LoopCostTracker.record_loop_cost`, the Redis pipeline operations succeed before calling `self._global_tracker.record_cost()`. If the global `CostTracker` call fails, the per-loop Redis data is already committed but no exception handling wraps the external call. Consider wrapping in try/except to avoid partial state on failure.

### 10.5 Linear Phase Iteration

`manager.py::_run_loop` iterates phases with a simple `for` loop. The state machine supports `pause()`/`resume()` but the manager never uses them. If a phase needs conditional branching or retry logic, the current linear iteration does not support it. This is acceptable for the current wave but worth noting for future complexity.

---

## Summary

| Check | Result | Details |
|---|---|---|
| 1. Circular dependencies | **PASS** | Zero circular imports. Clean DAG. |
| 2. Layer separation | **PASS** | Four distinct layers: foundation → composition → orchestration → public API |
| 3. __all__ exports valid | **PASS** | 24/24 symbols across two __all__ resolve correctly. |
| 4. Code duplication | **PASS** | Minor: duplicated _EXECUTION_PHASES list (LOW), duplicated goal_section (LOW) |
| 5. Single responsibility | **PASS** | 21/21 modules have clear single focus |
| 6. Naming conventions | **PASS** | Consistent. Minor logger event naming inconsistency (LOW) |
| 7. File/function sizes | **PASS** | 0 files over 300 lines. Longest function ~55 lines (acceptable) |
| 8. Phase handler uniformity | **PASS** | 7/7 identical signatures and structure |
| 9. Public API surface | **PASS** | Broad (22 symbols) but justified. `PHASE_NAMES` mutable (LOW). `core/api` missing __all__ (LOW) |

---

## Verdict

### **NEEDS REVIEW**

**Justification:** The code architecture is fundamentally sound — clean DAG, textbook layer separation, zero circular dependencies, perfect handler uniformity, all __all__ symbols verified, no oversized files, strong SRP compliance. No blocking architectural issues exist.

The NEEDS REVIEW designation reflects **7 actionable, non-blocking quality findings** that should be tracked and addressed in a follow-up wave:

| # | Finding | Severity | Recommendation |
|---|---|---|---|
| F1 | Duplicated `_EXECUTION_PHASES` in `evidence.py` and `manager.py` | LOW | Centralize in `state_machine.py` |
| F2 | Duplicated `goal_section` pattern across 7 phase handlers | LOW | Extract to shared utility |
| F3 | `PHASE_NAMES` exported as mutable dict | LOW | Wrap in `MappingProxyType` |
| F4 | Logger event naming inconsistency (dot vs underscore) | LOW | Standardize on dot-separated |
| F5 | `core/api/__init__.py` missing `__all__` | LOW | Add minimal `__all__` with `router` |
| F6 | Routes not wired to `LoopManager` | MEDIUM | Wire in next implementation wave |
| F7 | Global `CostTracker` call unwrapped in `record_loop_cost` | LOW | Add try/except around external call |

None of these findings indicate architectural failure. The system is well-structured and ready for deeper implementation waves.