# P5 Source Implementation Map

**Date:** 2026-06-27
**Verdict:** PARTIAL PASS — 22/22 files exist, 5 dead code, 2/21 files with dedicated tests

---

## Summary

| Metric | Value |
|--------|-------|
| Total claimed files | 23 (21 source + 2 systemd) |
| Files confirmed existing | 23/23 (100%) |
| Total source lines | ~5,424 (.py only) |
| Dead code modules | 5 (24%, 700 lines) |
| Files with dedicated tests | 2/21 (9.5%) |
| Files with NO test coverage | 19/21 (90.5%) |
| Init files present | 2/2 |
| Entry point integration | VERIFIED |
| Discord wiring | VERIFIED |
| Systemd paths | VERIFIED |

---

## File-by-File Inventory

| # | File | Lines | Key Classes | Imported By | Tests | Status |
|---|------|-------|-------------|-------------|-------|--------|
| 1 | state_machine.py | 227 | LoopPhase, LoopStateMachine | __init__, phases/__init__, manager, evidence, routes | test_T1 | IMPLEMENTED_AND_LIVE |
| 2 | phases/research.py | 244 | ResearchHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 3 | phases/plan_delegate.py | 145 | PlanDelegateHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 4 | phases/delegate.py | 332 | DelegateHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 5 | phases/execute.py | 334 | ExecuteHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 6 | phases/validate_audit.py | 190 | ValidateAuditHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 7 | phases/update_docs.py | 260 | UpdateDocsHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 8 | phases/setup_evidence.py | 285 | SetupEvidenceHandler | phases/__init__ | None | IMPLEMENTED_AND_LIVE |
| 9 | guardian.py | 259 | LoopGuardian | __init__, manager | None | IMPLEMENTED_AND_LIVE |
| 10 | enforcer.py | 133 | TodoEnforcer | __init__ ONLY | None | **DEAD_CODE** |
| 11 | hash_anchor.py | 122 | compute_line_hash, validate_edit | __init__ ONLY | None | **DEAD_CODE** |
| 12 | sub_agent.py | 129 | SubAgentSpawner | __init__ ONLY | None | **DEAD_CODE** |
| 13 | contract.py | 131 | TaskContract, build_contract | __init__ ONLY | None | **DEAD_CODE** |
| 14 | verify.py | 184 | OutputVerifier | __init__ ONLY | None | **DEAD_CODE** |
| 15 | evidence.py | 195 | EvidencePipeline | __init__, manager | None | IMPLEMENTED_AND_LIVE |
| 16 | cost.py | 270 | LoopCostTracker | __init__, manager | test_T9 | IMPLEMENTED_WITH_BUG (fail-open) |
| 17 | manager.py | 504 | LoopManager | __init__, main.py, scheduler, hermes_bridge, environment | test_e2e_loop | IMPLEMENTED_AND_LIVE |
| 18 | core/api/routes.py | 385 | router, internal_router | main.py | None | IMPLEMENTED_AND_LIVE |
| 19 | core/api/auth.py | 55 | verify_api_key, get_api_key | routes.py | None | IMPLEMENTED_AND_LIVE |
| 20 | discord/cmd_loop_start.py | 463 | loop_start_callback | _entrypoint.py | None | IMPLEMENTED_AND_LIVE |
| 21 | discord/cmd_loop_stop.py | 532 | loop_stop_callback | _entrypoint.py | None | IMPLEMENTED_AND_LIVE |

---

## Additional Modules (beyond 23 claimed steps)

The `src/loops/` package actually contains **37+ modules** (exported via `__init__.py`), many added post-P5:

| Module | Exported | Description |
|--------|----------|-------------|
| scheduler.py | YES | LoopScheduler (APScheduler, SDLC cron) |
| state_store.py | YES | LoopStateStore, LoopState, LoopStatus |
| artifacts.py | YES | evidence_dir, write/read_artifact |
| budget.py | YES | IterationBudget (fail-closed, NOT used by main loop) |
| sandbox.py | YES | SandboxVerifier |
| context.py | YES | LoopContext, LoopContextBuilder |
| prompts.py | YES | SystemPromptBuilder |
| conversation.py | YES | ConversationLoop |
| concurrency.py | YES | ConcurrencyLimiter, TokenBucket, ResourceLimits |
| circuit_breaker.py | YES | DependencyCircuitBreaker, StuckDetector, SafetyGate |
| retry.py | YES | RetryPolicy, RetryExecutor |
| escalation.py | YES | EscalationProtocol |
| review_fork.py | YES | BackgroundReviewFork |
| curator.py | YES | CuratorLoop |
| testing_gate.py | YES | TestingGate |
| reflection.py | YES | ReflectionExtractor |
| audit_writer.py | YES | AuditWriter (hash-chained) |
| safety_integration.py | YES | LoopSafetyGate (NOT called from _run_loop) |
| hermes_bridge.py | YES | HermesBridge (superseded by life_kernel) |
| recovery.py | YES | RecoveryManager |
| skill_library.py | YES | SkillLibrary |
| tool_registry.py | YES | ToolRegistry |
| priority.py | YES | PriorityScorer |
| dedup.py | YES | DeduplicationFilter |
| backlog.py | YES | Backlog |
| discovery.py | YES | DiscoveryEngine, SurveillanceCollector |
| environment.py | YES | EnvironmentMonitor |
| metrics.py | (not in __init__) | Prometheus metrics |

---

## Dead Code (5 modules, 700 lines)

| Module | Lines | Reason |
|--------|-------|--------|
| enforcer.py | 133 | TodoEnforcer exported but zero production callers |
| hash_anchor.py | 122 | compute_line_hash exported but zero production callers |
| sub_agent.py | 129 | SubAgentSpawner exported but zero production callers |
| contract.py | 131 | TaskContract exported but zero production callers |
| verify.py | 184 | OutputVerifier exported but zero production callers |

---

## Wiring Verification

| Checkpoint | Status | Evidence |
|-----------|--------|----------|
| LoopManager in main.py lifespan | ✅ | line 103: `LoopManager(llm_router=None)` |
| HardStopHandler wired to guardian | ✅ | line 109-110: `set_hard_stop_handler()` |
| guardian.monitor() background task | ✅ | line 116 |
| HermesBridge created | ✅ | line 470 (but superseded) |
| resume_pending_loops() called | ✅ | line 479 |
| /loop-start registered in Discord | ✅ | _entrypoint.py line 180, _command_registry.py line 137 |
| /loop-stop registered in Discord | ✅ | _entrypoint.py line 181, _command_registry.py line 141 |
| 7 Hermes loop commands | ✅ | src/hermes_plugins/commands_loop/ (7 files) |
| Routes mounted in FastAPI | ✅ | main.py line 783 |
| llm_router passed as None | ⚠️ | main.py line 103 — loop is LLM-dead |
