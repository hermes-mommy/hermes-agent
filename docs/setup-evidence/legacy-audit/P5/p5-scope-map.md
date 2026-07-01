# P5 Scope Map

**Date:** 2026-06-27

---

## Phase 5 = Agent Loop (23 steps)

**Critical Path:** P1 (LLM) + P3 (Memory) → P5 → P6 (MCP)
**Cost:** $3/month
**Dependencies:** P1+P3

### Intended Scope (from PROGRESS.md)

| Step | Title | Claimed Status |
|------|-------|---------------|
| P5-001 | FastAPI internal API (localhost:8000) | ✅ |
| P5-002 | FastAPI authentication (JWT/API key) | ✅ |
| P5-003 | Loop state machine (7 phases) | ✅ |
| P5-004 | Phase 1: Research | ✅ |
| P5-005 | Phase 2: Plan & Delegate | ✅ |
| P5-006 | Phase 3: Delegate | ✅ |
| P5-007 | Phase 4: Execute | ✅ |
| P5-008 | Phase 5: Validate & Audit | ✅ |
| P5-009 | Phase 6: Update Documents | ✅ |
| P5-010 | Phase 7: Setup Evidence | ✅ |
| P5-011 | Loop Guardian | ✅ |
| P5-012 | Todo Enforcer | ✅ |
| P5-013 | Hash-anchored edit tool | ✅ |
| P5-014 | Sub-agent spawning | ✅ |
| P5-015 | Sub-agent task contract | ✅ |
| P5-016 | Sub-agent output verification | ✅ |
| P5-017 | Evidence generation pipeline | ✅ |
| P5-018 | guinevere-loops.service | ✅ |
| P5-019 | guinevere-scheduler.service | ✅ |
| P5-020 | /loop-start command | ✅ |
| P5-021 | /loop-stop command | ✅ |
| P5-022 | Agent loop E2E (17/17 PASS) | ✅ |
| P5-023 | Cost tracking per loop (Redis DB5) | ✅ |

### What Was Actually Built (37+ modules)

The implementation far exceeds the 23 originally claimed steps. `src/loops/` contains 37+ modules including:
- Core: state_machine, manager, guardian, evidence, cost
- 7 Phase Handlers: research, plan_delegate, delegate, execute, validate_audit, update_docs, setup_evidence
- Safety: safety_integration, circuit_breaker (SafetyGate), escalation
- Infrastructure: scheduler, hermes_bridge, recovery, concurrency, retry, budget
- Intelligence: conversation, prompts, context, review_fork, curator, testing_gate, reflection, discovery, environment
- Audit: audit_writer, skill_library, tool_registry, priority, dedup, backlog
- Dead Code: enforcer, hash_anchor, sub_agent, contract, verify

### ADR-035 Phase 5 Enhancements (8 steps)

| Step | Scope | Status |
|------|-------|--------|
| 5.1 | VPS SOUL.md completion | ✅ v2 |
| 5.2 | Drift baseline reset | ✅ v2 |
| 5.3 | Five priority Hermes skills | ✅ v2 |
| 5.4 | PersonaPlugin/Redis DB5 bridge | ✅ v2 |
| 5.5 | Native Hermes cron rituals | ✅ v2 |
| 5.6 | Ritual verification | ✅ v2 |
| 5.7 | Persona module migration | ✅ v2 |
| 5.8 | Final 18-gate synthesis + OG-6 deploy | ✅ 17 PASS / 1 RESCOPED |

### P5.5 Remediation (10 fixes)

All 10 fixes applied and persist in codebase (2026-06-02).

### P5 Re-Audit (2026-06-09)

6 findings found, 5 resolved, 1 deferred (NoNewPrivileges systemd). Verdict: PASS.

---

## Actual vs Claimed Scope

| Dimension | Claimed | Actual |
|-----------|---------|--------|
| Module count | 23 steps | 37+ modules |
| Dead code | None acknowledged | 5 modules (700 lines) |
| Test coverage | "205 passed" | 2/21 files have dedicated tests |
| LLM integration | "autonomous SDLC engine" | llm_router=None (LLM-dead) |
| Safety integration | "LoopSafetyGate" | EXISTS but NOT called from _run_loop |
| Budget enforcement | "Cost tracking" | Records but never blocks |
| Consent check | "consent boundaries" | Prompt-level only |
| Distress detection | "D0-D4" | Labels only, no detection |
| Hermes integration | "HermesBridge" | Superseded by life_kernel |
| Project scoping | P19 ready | Data model only, not wired |
