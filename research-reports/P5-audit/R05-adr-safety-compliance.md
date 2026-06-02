# R05 — P5 Agent Loop: ADR & Safety Compliance Audit

**Audit Dimension:** ADR-001, ADR-005, ADR-007, ADR-008, ADR-011, ADR-030, ADR-031 + AgentLoopSpec + PersonaSafetyPolicy
**Auditor:** R05 sub-agent (explore)
**Date:** 2026-06-02
**Scope:** `src/loops/` (P5) cross-referenced against ADR decisions and safety policy
**Status:** COMPLETE

---

## Executive Summary

| ADR | Title | Verdict | Severity |
|---|---|---|---|
| ADR-001 | Persona Safety & Ethical Boundary | **GAP — Not Integrated** | CRITICAL |
| ADR-005 | LLM Router & Failover Strategy | PASS | — |
| ADR-007 | Memory Storage Backend Selection | **PARTIAL — No PostgreSQL Persistence** | HIGH |
| ADR-008 | Memory Encryption & Key Management | **GAP — No At-Rest Encryption in P5** | HIGH |
| ADR-011 | SDLC Loop Phase Specification | PASS | — |
| ADR-030 | Redis DB Assignments | **MISMATCH — DB5 Double-Assigned** | HIGH |
| ADR-031 | Database Naming Convention | N/A — Not Implemented | MEDIUM |

**Overall Verdict:** 2 PASS, 3 GAP, 1 PARTIAL, 1 MISMATCH, 1 N/A

---

## 1. ADR-001 — Persona Safety & Ethical Boundary

### ADR Requirement

ADR-001 mandates that safety boundaries are architectural and reviewable. Persona behavior may be intense only while staying inside explicit safety boundaries. Distress, coercion, surveillance, punishment, privacy, or irreversible action must defer to safety policy and user autonomy.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| HardStopHandler exists | `src/core/services/hard_stop_handler.py` | PASS | Fully intact from P1/P2. SafetyState enum, exact/semantic triggers, recovery, audit logging. |
| Discord integration | `src/discord/cmd_safeword.py` | PASS | Imports HardStopHandler, /safeword slash command, text message detection, embed builders. |
| P5 loop safety pre-check | `src/loops/manager.py` | **FAIL** | No import of HardStopHandler. `_run_loop()` has zero safety gate checks. |
| Phase-level safety gate | `src/loops/phases/*.py` | **FAIL** | No phase handler imports or calls HardStopHandler. |
| Loop emergency stop | `src/loops/state_machine.py` | **FAIL** | `cancel()` method exists but is NOT triggered by HARD STOP state. Only callable externally via `stop_loop()`. |
| Safe-mode memory recall | `src/memory/read_pipeline.py` | PASS | `safe_mode=True` parameter blocks Critical content, redacts Restricted/Confidential, blocks surveillance/emotional tags. |

### Finding

**CRITICAL GAP:** The P5 loop system is completely disconnected from the HARD STOP safety protocol.

- `src/loops/manager.py` never imports `HardStopHandler` or checks `SafetyState`.
- The `_run_loop()` method (line 146) iterates through all 7 phases without any pre-phase safety gate.
- If HARD STOP triggers while a loop is running, the loop continues executing all phases unhindered.
- `stop_loop()` (line 91) exists as a manual API call but is not wired to the HARD STOP event.
- The `LoopStateMachine.cancel()` method exists but requires explicit external invocation.

### Impact

PersonaSafetyPolicy §7.2 requires immediate runtime actions when safe word triggers, including stopping autonomous pressure (which includes loop execution). Currently, an active SDLC loop would continue running even after HARD STOP — violating the ADR-001 safety-first principle.

### Remediation Required

1. Import `HardStopHandler` into `LoopManager` (or inject via constructor).
2. Add pre-phase safety check in `_run_loop()`: check `handler.is_safe` before each phase iteration.
3. Wire HARD STOP event to `state.cancel()` for all active loops.
4. Add `safe_mode` parameter to `LoopStateMachine` that short-circuits phase execution.

---

## 2. ADR-005 — LLM Router & Failover Strategy

### ADR Requirement

All LLM routing goes through 9Router only. No direct OpenAI or Anthropic API calls. No OpenRouter fallback. Queue/retry/degrade on 9Router failure.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| Direct OpenAI import | `src/loops/*.py` | PASS | Zero `openai` imports anywhere in P5 code. |
| Direct Anthropic import | `src/loops/*.py` | PASS | Zero `anthropic` imports anywhere in P5 code. |
| 9Router base URL | `src/core/services/llm_router.py` | PASS | All models use `http://localhost:20128/v1` (9Router local proxy). |
| Fallback chain | `src/core/services/llm_router.py` | PASS | Fallback chain: CORE → SUB_AGENT → FALLBACK, all via same 9Router endpoint. |
| Retry/backoff | `src/core/services/llm_router.py` | PARTIAL | Basic exception handling with continue-to-next in fallback chain. No explicit exponential backoff or circuit breaker in router. |
| Embedding pipeline | `src/memory/embeddings.py` | PASS | Uses `httpx` + 9Router URL. Never imports OpenAI SDK. Manual exponential backoff retry implemented. |

### Finding

**PASS.** P5 code does not make any direct LLM provider calls. All routing flows through 9Router via the local proxy endpoint. The `LLMRouter` is not directly called by P5 phase handlers (they are placeholder templates), but the architecture is ADR-005 compliant.

**Minor note:** `LLMRouter` lacks exponential backoff and circuit breaker patterns mentioned in ADR-005 as "queue/retry/degrade behavior." The embedding pipeline has retry, but the router does not. This is a future-wave concern, not a P5 compliance violation.

---

## 3. ADR-007 — Memory Storage Backend Selection

### ADR Requirement

PostgreSQL as primary durable memory store. Redis as cache/working memory. SQLite excluded entirely.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| SQLite usage | `src/loops/*.py` | PASS | Zero SQLite imports or references in any P5 file. |
| PostgreSQL for loop state | `src/loops/state_machine.py` | **FAIL** | Loop state is purely in-memory (Python dict). No PostgreSQL persistence. |
| PostgreSQL for loop results | `src/loops/manager.py` | **FAIL** | `active_loops` is an in-memory `dict[str, LoopStateMachine]`. Lost on process restart. |
| Redis for loop state | `src/loops/manager.py` | **FAIL** | No Redis usage for active loop state. Only `LoopCostTracker` uses Redis. |
| Redis for cost tracking | `src/loops/cost.py` | PASS | Uses Redis DB5 for cost tracking. |
| Artifacts to filesystem | `src/loops/artifacts.py` | PASS | Writes to `/home/guinevere/evidence/loops/{date}-{loop_id}/`. Not a database, but persistent. |
| Memory pipeline | `src/memory/read_pipeline.py` | PASS | Uses SQLAlchemy ORM queries against PostgreSQL `Episodes` table. |

### Finding

**PARTIAL — No PostgreSQL persistence for loop state.**

The loop system stores all state in-memory:
- `LoopManager.active_loops: dict[str, LoopStateMachine]` — volatile, lost on restart.
- `LoopStateMachine` — plain Python object, no ORM mapping or serialization to DB.
- `LoopGuardian.active_loops: dict[str, dict]` — volatile monitoring state.

The AgentLoopSpec §1.3 specifies: "State Manager (Redis active + PostgreSQL permanent)" — this dual-storage architecture is not implemented. A process crash would lose all active loop state, phase progress, and artifact references.

Artifact files on disk survive crashes, but the loop state machine metadata (which loop, which phase, task description, error count) would be lost.

---

## 4. ADR-008 — Memory Encryption & Key Management

### ADR Requirement

Sensitive fields require encryption-at-rest. Auditable key ownership, rotation procedure, emergency revoke path. Separation between secrets, profile memory, surveillance events, and operational logs. SOPS/age and application encryption interact.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| In-transit privacy | `src/memory/embeddings.py` | PASS | Classification-based redaction, Critical text rejection, sensitive pattern scrubbing before send. |
| Safe-mode content blocking | `src/memory/read_pipeline.py` | PASS | Classification ceiling, DNR exclusion, surveillance/emotional content blocking in safe mode. |
| Field-level encryption at rest | `src/loops/*.py` | **FAIL** | No encryption on any loop artifact or state data. |
| Key hierarchy/rotation | `src/loops/*.py` | **FAIL** | No key management code exists in P5. |
| SOPS/age integration | `src/loops/*.py` | **FAIL** | No SOPS or age imports or usage. |
| Artifact encryption | `src/loops/artifacts.py` | **FAIL** | Artifacts written as plaintext markdown via `Path.write_text()`. |

### Finding

**GAP — No at-rest encryption in P5 loop code.**

The P5 loop system writes evidence artifacts as unencrypted markdown to `/home/guinevere/evidence/loops/`. While the embedding pipeline (P3) has excellent in-transit privacy guards (classification, redaction, safe-mode), no encryption is applied to:

1. Loop artifacts (research reports, plans, execution logs, evidence).
2. Loop state machine data (task descriptions, goals, error counts).
3. Cost tracking data in Redis DB5.

ADR-008 requires field-level encryption for sensitive memory fields. Loop artifacts may contain sensitive task descriptions, surveillance-derived context, or intimate data depending on the task.

**Note:** This may be acceptable if: (a) VPS filesystem is already encrypted at the disk level, and (b) loop artifacts are classified as "Internal" rather than "Critical/Confidential." However, the ADR explicitly requires application-level encryption for sensitive fields, and no such encryption exists in P5 code.

---

## 5. ADR-011 — SDLC Loop Phase Specification

### ADR Requirement

Exactly 7 autonomous SDLC phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| LoopPhase enum count | `src/loops/state_machine.py` | PASS | Exactly 7 operational phases + 1 COMPLETE terminal. |
| Phase names match ADR | `src/loops/state_machine.py` | PASS | All 7 names match verbatim. |
| Phase registry completeness | `src/loops/phases/__init__.py` | PASS | All 7 phases have registered handler functions. |
| Phase handler files exist | `src/loops/phases/*.py` | PASS | 7 phase handler modules: research, plan_delegate, delegate, execute, validate_audit, update_docs, setup_evidence. |
| Sequential execution | `src/loops/manager.py` | PASS | `_EXECUTION_PHASES` list iterates phases 1-7 in order. |
| Phase advance logic | `src/loops/state_machine.py` | PASS | `advance()` increments phase value by 1, raises ValueError at COMPLETE. |

### Phase Mapping (ADR-011 vs. Implementation)

| ADR-011 Phase | LoopPhase Enum | Int Value | Handler File | Match |
|---|---|---|---|---|
| 1. Research | `RESEARCH` | 1 | `research.py` | PASS |
| 2. Plan & Delegate | `PLAN_AND_DELEGATE` | 2 | `plan_delegate.py` | PASS |
| 3. Delegate | `DELEGATE` | 3 | `delegate.py` | PASS |
| 4. Execute | `EXECUTE` | 4 | `execute.py` | PASS |
| 5. Validate & Audit | `VALIDATE_AND_AUDIT` | 5 | `validate_audit.py` | PASS |
| 6. Update Documents | `UPDATE_DOCUMENTS` | 6 | `update_docs.py` | PASS |
| 7. Setup Evidence | `SETUP_EVIDENCE` | 7 | `setup_evidence.py` | PASS |
| (terminal) | `COMPLETE` | 8 | N/A | PASS |

### Finding

**PASS — Perfect match.** The LoopPhase enum has exactly 7 operational phases matching ADR-011's canonical specification, plus a COMPLETE terminal state. All phases have registered handler functions and dedicated module files. The `PHASE_NAMES` dict provides human-readable names matching the ADR exactly.

---

## 6. ADR-030 — Redis DB Assignments (DB0-DB5)

### ADR Requirement

| DB | Purpose | Notes |
|---|---|---|
| DB0 | Task queue | Job queue integrity |
| DB1 | LLM cache | Disposable, LRU |
| DB2 | Surveillance buffer | Android/Windows sync |
| DB3 | Sessions / working memory | **Safe-word state here** |
| DB4 | Pub/Sub | Ephemeral |
| DB5 | Rate limiting | Sliding window counters |

### Implementation Evidence

| Component | File | DB Used | ADR-030 Assignment | Match |
|---|---|---|---|---|
| LoopCostTracker | `src/loops/cost.py:31` | `db=5` | DB5 = Rate limiting | **MISMATCH** |
| CostTracker (global) | `src/core/services/cost_tracker.py:13` | `db=5` | DB5 = Rate limiting | **MISMATCH** |
| HardStopHandler | `src/core/services/hard_stop_handler.py` | None (in-memory) | DB3 = Sessions/safe-word | **NOT WIRED** |
| Loop state | `src/loops/manager.py` | None (in-memory) | DB3 = Sessions/working | **NOT WIRED** |
| Task queue | Not implemented | N/A | DB0 = Task queue | N/A |
| LLM cache | Not implemented | N/A | DB1 = LLM cache | N/A |

### Finding

**MISMATCH — Redis DB5 double-assigned.**

ADR-030 assigns DB5 to "Rate limiting" (sliding window counters, disposable on restart). However:

1. `src/loops/cost.py` (`LoopCostTracker`) uses `db=5` for **cost tracking** — per-loop cost accumulation, monthly totals, per-model breakdown.
2. `src/core/services/cost_tracker.py` (`CostTracker`) also uses `db=5` for **cost tracking**.

Cost tracking is NOT rate limiting. The `CostTracker.record_cost()` stores persistent financial data (daily/monthly aggregates) that should survive restarts, which conflicts with ADR-030's "disposable on restart" note for DB5.

**Additional gaps:**
- HardStopHandler safe-word state is stored in-memory only (`SafetyState` enum on the dataclass). ADR-030 reserves DB3 for "Sessions / working memory" and explicitly notes "Safe-word state stored here — must survive restarts." This is NOT implemented.
- Loop state (active loops, phase, status) is entirely in-memory. If it were persisted, it should use DB3 per ADR-030.

---

## 7. ADR-031 — Database Naming Convention

### ADR Requirement

Production database name: `guinevere`. Test: `guinevere_test`. No `guinevere_db`.

### Implementation Evidence

| Check | File | Status | Details |
|---|---|---|---|
| Connection strings in P5 | `src/loops/*.py` | N/A | No PostgreSQL connection strings exist. No database naming used. |
| Memory pipeline | `src/memory/read_pipeline.py` | N/A | Uses SQLAlchemy ORM; connection string comes from external configuration, not P5 code. |

### Finding

**N/A — P5 loop code does not connect to PostgreSQL directly.** The database naming convention is not testable from P5 code because no database connections exist. This will become relevant when PostgreSQL persistence is added for loop state (see ADR-007 gap).

---

## 8. AgentLoopSpec v2.0 Compliance

### Spec Requirements vs. Implementation

| Spec Requirement | File | Status | Notes |
|---|---|---|---|
| 7 phases (exact match) | `state_machine.py` | PASS | Verified in ADR-011 section above. |
| Loop Guardian (30s heartbeat) | `guardian.py` | PASS | `HEARTBEAT_INTERVAL=30`, `PROGRESS_TIMEOUT=300` (5min), `RESOURCE_CHECK=60`. Matches spec. |
| TODO Enforcer (idle yank) | `enforcer.py` | PASS | `IDLE_THRESHOLD=30`, `KILL_THRESHOLD=60`. Yank and kill-respawn logic present. |
| Hash-anchored edits | `hash_anchor.py` | PASS | SHA-256 line hashing, content validation, file validation. Matches spec format. |
| Sub-agent spawner (Pasukan Mommy) | `sub_agent.py` | PASS | 5 categories match spec: visual-engineering, deep-logic, data-infra, integration, testing. |
| Task contract format | `contract.py` | PASS | Pydantic model with TASK/EXPECTED_OUTCOME/REQUIRED_TOOLS/MUST_DO/MUST_NOT_DO/CONTEXT. |
| Output verification | `verify.py` | PASS | File existence, markdown structure, forbidden patterns, command execution checks. |
| Evidence pipeline | `evidence.py` | PASS | Phase artifact collection, final report generation, LQS score (placeholder). |
| Artifact persistence | `artifacts.py` | PASS | Filesystem write/read at `/home/guinevere/evidence/loops/`. |
| Cron scheduler | `scheduler.py` | PASS | APScheduler-based, daily ritual scheduling, WIB timezone. |
| Loop parallel execution | `manager.py` | PASS | `asyncio.create_task()` per loop, unlimited spawn. |
| Phase handlers produce .md | `phases/*.py` | PASS | All 7 handlers return markdown artifact content. |

### Spec Features Not Yet Implemented (Placeholder Acknowledged)

| Feature | Status | Notes |
|---|---|---|
| LLM-powered research (Phase 1) | Placeholder | `research.py` returns template markdown. No LLM call. |
| Real sub-agent execution (Phase 4) | Placeholder | `execute.py` returns template. No actual code execution. |
| Sub-agent spawning in Delegate phase | Placeholder | `delegate.py` returns template manifest. SubAgentSpawner exists but not called. |
| Validation re-delegation loop | Placeholder | `validate_audit.py` returns template. No test running or auto-fix. |
| Real doc-sync (Phase 6) | Placeholder | `update_docs.py` returns template. |
| Loop state persistence (Redis + PG) | Not implemented | All state in-memory. |
| Guardian resource monitoring | Skeleton | `RESOURCE_CHECK` timer exists but only logs debug message. No actual resource checking. |
| Guardian kill with state cleanup | **BUG** | `kill_loop()` unregisters but does NOT call `state.fail()` or `state.cancel()`. State machine left dangling. |

---

## 9. PersonaSafetyPolicy v1.0 — Loop Stop Compliance

### Policy Requirements

PersonaSafetyPolicy §7.2 requires 9 immediate actions on safe-word trigger:
1. Stop persona escalation.
2. Stop punishment framing.
3. Pause yandere intensity.
4. Pause surveillance-driven confrontation.
5. Pause non-essential autonomous pressure.
6. Switch to neutral/supportive mode.
7. Acknowledge the pause plainly.
8. Log minimal non-punitive safety event.
9. Ask only low-pressure clarification.

### P5 Loop Impact on Requirements

| Requirement | P5 Relevance | Status | Notes |
|---|---|---|---|
| 1. Stop persona escalation | N/A | N/A | P5 loops are engineering tasks, not persona rendering. |
| 2. Stop punishment framing | N/A | N/A | P5 loops don't frame punishment. |
| 3. Pause yandere intensity | N/A | N/A | P5 loops don't control persona tone. |
| 4. Pause surveillance confrontation | N/A | N/A | P5 loops don't trigger surveillance confrontation. |
| 5. **Pause non-essential autonomous pressure** | **CRITICAL** | **FAIL** | Active SDLC loops constitute autonomous work. Policy implies loops should pause. |
| 6. Switch to neutral mode | PARTIAL | PARTIAL | HardStopHandler switches state, but P5 loops are unaware. |
| 7. Acknowledge pause | PASS | PASS | `cmd_safeword.py` sends embed with safe mode confirmation. |
| 8. Log safety event | PASS | PASS | `HardStopHandler._trigger()` appends to `event_log` and logs via structlog. |
| 9. Low-pressure clarification | N/A | N/A | Handled by Discord layer, not loops. |

### Finding

**CRITICAL GAP on Requirement 5:** PersonaSafetyPolicy §7.2.5 says "Pause non-essential autonomous pressure." Active SDLC loops performing autonomous coding work constitute autonomous pressure on the system. Currently:

- `LoopManager` does not check `HardStopHandler.is_safe` before phase execution.
- Active loops continue running all 7 phases even after HARD STOP.
- There is no mechanism to pause/resume loops based on safety state.
- `LoopGuardian` continues monitoring and could `kill_loop()` loops during safe mode, which might be undesirable.

### Emergency Stop Assessment

The `HardStopHandler` from P1/P2 is **fully intact** and correctly implements:
- Pre-LLM keyword detection (exact + semantic patterns).
- State machine (NORMAL → SAFE).
- Recovery triggers with explicit readiness.
- Audit logging with non-punitive event records.
- Guard decision API (`get_guard_decision()`).

It is **correctly wired** to the Discord layer (`cmd_safeword.py`) but **NOT wired** to the P5 loop system.

---

## 10. HardStopHandler Integrity Check

### File: `src/core/services/hard_stop_handler.py`

| Check | Status | Details |
|---|---|---|
| File exists | PASS | 149 lines, intact from P1/P2. |
| SafetyState enum | PASS | `NORMAL` and `SAFE` states. |
| Exact triggers | PASS | 6 triggers: "hard stop", "hardstop", "safe word", "safeword", "hentikan", "berhenti". |
| Semantic patterns | PASS | 5 regex patterns for semantic equivalents. |
| Recovery triggers | PASS | 6 recovery phrases including Indonesian variants. |
| Event logging | PASS | `HardStopEvent` dataclass with timestamp, trigger, state transition. |
| Guard decision API | PASS | `get_guard_decision()` returns structured dict with blocked/state/response. |
| Referenced from P5 | **FAIL** | Zero imports from any `src/loops/` file. |
| Referenced from Discord | PASS | `src/discord/cmd_safeword.py` imports and uses it as singleton. |
| Referenced from memory | PASS | `src/memory/read_pipeline.py` accepts `safe_mode` parameter (indirect). |

---

## Summary of All Findings

### CRITICAL Findings (Must Fix)

| ID | Finding | ADR/Policy | File | Impact |
|---|---|---|---|---|
| C-001 | P5 loops have no HARD STOP integration | ADR-001, PersonaSafetyPolicy §7.2.5 | `manager.py` | Active loops continue after safe word — violates safety-first principle. |
| C-002 | Guardian kill_loop doesn't update state machine | AgentLoopSpec §4.1 | `guardian.py:95-103` | Killed loops have dangling state — `state.fail()` or `state.cancel()` never called. |

### HIGH Findings (Should Fix)

| ID | Finding | ADR/Policy | File | Impact |
|---|---|---|---|---|
| H-001 | No PostgreSQL persistence for loop state | ADR-007, AgentLoopSpec §1.3 | `manager.py`, `state_machine.py` | Process crash loses all loop state. |
| H-002 | Redis DB5 used for cost, not rate limiting | ADR-030 | `cost.py:31`, `cost_tracker.py:13` | Cost data lost on restart; DB5 purpose mismatch. |
| H-003 | HardStopHandler safe-word state not in Redis DB3 | ADR-030 | `hard_stop_handler.py` | Safe-word state lost on process restart. |
| H-004 | No at-rest encryption for loop artifacts | ADR-008 | `artifacts.py` | Sensitive task data stored as plaintext markdown. |

### MEDIUM Findings (Track)

| ID | Finding | ADR/Policy | File | Impact |
|---|---|---|---|---|
| M-001 | No PostgreSQL connection strings in P5 | ADR-031 | All loop files | Naming convention untestable until persistence added. |
| M-002 | All phase handlers are placeholder templates | AgentLoopSpec | `phases/*.py` | No real LLM, sub-agent, or test execution. |
| M-003 | LLMRouter lacks exponential backoff | ADR-005 | `llm_router.py` | Retry storms possible on 9Router outage. |

### PASS Findings

| ID | Finding | ADR/Policy |
|---|---|---|
| P-001 | 7 SDLC phases match ADR-011 exactly | ADR-011 |
| P-002 | No direct OpenAI/Anthropic calls | ADR-005 |
| P-003 | No SQLite usage anywhere | ADR-007 |
| P-004 | Embedding pipeline has excellent in-transit privacy | ADR-008 |
| P-005 | HardStopHandler fully intact and Discord-wired | ADR-001 |
| P-006 | Loop Guardian, TodoEnforcer, HashAnchor all present | AgentLoopSpec |
| P-007 | Sub-agent categories match spec | AgentLoopSpec |
| P-008 | Task contract format matches spec | AgentLoopSpec |

---

## File Inventory

### P5 Source Files Audited (21 files)

| File | Lines | Purpose |
|---|---|---|
| `src/loops/__init__.py` | 39 | Package exports |
| `src/loops/state_machine.py` | 226 | LoopPhase enum + LoopStateMachine |
| `src/loops/manager.py` | 272 | Loop orchestration |
| `src/loops/guardian.py` | 157 | Watchdog monitoring |
| `src/loops/enforcer.py` | 132 | Idle agent enforcement |
| `src/loops/scheduler.py` | 175 | Cron-based scheduling |
| `src/loops/evidence.py` | 194 | Evidence pipeline |
| `src/loops/artifacts.py` | 110 | Artifact I/O |
| `src/loops/cost.py` | 194 | Per-loop cost tracking (Redis DB5) |
| `src/loops/contract.py` | 130 | Task contract model |
| `src/loops/sub_agent.py` | 128 | Sub-agent spawner |
| `src/loops/verify.py` | 183 | Output verification |
| `src/loops/hash_anchor.py` | 121 | Hash-anchored edits |
| `src/loops/phases/__init__.py` | 48 | Phase registry |
| `src/loops/phases/research.py` | 84 | Phase 1 handler |
| `src/loops/phases/plan_delegate.py` | 83 | Phase 2 handler |
| `src/loops/phases/delegate.py` | 81 | Phase 3 handler |
| `src/loops/phases/execute.py` | 82 | Phase 4 handler |
| `src/loops/phases/validate_audit.py` | 91 | Phase 5 handler |
| `src/loops/phases/update_docs.py` | 76 | Phase 6 handler |
| `src/loops/phases/setup_evidence.py` | 99 | Phase 7 handler |

### Supporting Files Referenced

| File | Relevance |
|---|---|
| `src/core/services/hard_stop_handler.py` | P1/P2 safety handler — not wired to P5 |
| `src/core/services/llm_router.py` | LLM routing via 9Router — ADR-005 compliant |
| `src/core/services/cost_tracker.py` | Global cost tracker — Redis DB5 mismatch |
| `src/discord/cmd_safeword.py` | Discord HARD STOP integration |
| `src/memory/embeddings.py` | Embedding pipeline with privacy guards |
| `src/memory/read_pipeline.py` | Memory recall with safe-mode support |

### ADRs and Policy Documents Consulted

| Document | Status |
|---|---|
| `adr/ADR-001-persona-safety-ethical-boundary.md` | Accepted with notes |
| `adr/ADR-005-llm-router-failover-strategy.md` | Accepted |
| `adr/ADR-007-memory-storage-backend-selection.md` | Accepted |
| `adr/ADR-008-memory-encryption-key-management.md` | Accepted with notes |
| `adr/ADR-011-sdlc-loop-phase-specification.md` | Accepted |
| `adr/ADR-030-redis-db-assignments.md` | Accepted |
| `adr/ADR-031-database-naming.md` | Accepted |
| `docs/00-core/03-AgentLoopSpec_v2.0.md` | Canonical spec |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Accepted |

---

## Recommended Priority Order

1. **C-001**: Wire HardStopHandler into LoopManager — add pre-phase safety gate.
2. **C-002**: Fix Guardian kill_loop to call state.fail()/cancel().
3. **H-002**: Resolve Redis DB5 assignment — either update ADR-030 to include cost tracking, or move cost tracking to a new DB.
4. **H-003**: Persist HardStopHandler safe-word state to Redis DB3 for restart survival.
5. **H-001**: Add PostgreSQL persistence for loop state (requires ADR-031 naming compliance).
6. **H-004**: Evaluate at-rest encryption needs for loop artifacts based on data classification.
7. **M-003**: Add exponential backoff to LLMRouter.

---

*Report generated 2026-06-02. All findings based on static code analysis of committed source files.*
