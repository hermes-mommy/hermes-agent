# P5 Auditor Gate

**Audit ID:** GAS-AUDIT-P5-2026-06-27
**Date:** 2026-06-27
**Auditor:** Guinevere (read-only, full-spectrum)

---

## Gate Verdict

| Field | Value |
|-------|-------|
| **Overall Status** | **P5 IMPLEMENTED WITH BUGS — SOURCE FIXES REQUIRE MAMA APPROVAL** |
| **Source Code Exists** | ✅ YES — 23/23 claimed files + 14 additional modules |
| **Source Code Wired** | ✅ YES — main.py, routes, Discord, Hermes plugins |
| **Runtime Active** | ⚠️ PARTIAL — infrastructure live, LLM dormant |
| **Tests Valid** | ⚠️ PARTIAL — 2/21 files have dedicated tests, E2E exists |
| **Safety Integrated** | ❌ NO — safety gate exists but not wired to loop execution |
| **Consent Enforced** | ❌ NO — prompt-level only |
| **Budget Enforced** | ❌ NO — records but never blocks |
| **Documentation Consistent** | ❌ NO — 6 overclaims identified |
| **P5.5 Fixes Persist** | ✅ YES — 10/10 confirmed |
| **ADR-035 Enhancements Live** | ✅ YES — 17 PASS / 1 RESCOPED |
| **Cross-Phase Reconciled** | ✅ YES — P19/P20/P4/ADR-035 reconciled |

---

## Audit Dimensions (10/10 Covered)

| # | Dimension | Verdict | Key Finding |
|---|-----------|---------|-------------|
| 1 | Architecture/implementation wiring | PASS WITH FINDINGS | 37+ modules, all wired, 5 dead code |
| 2 | Runtime/live VPS truth | PARTIAL (no SSH) | Code analysis proves wiring; VPS live check needed |
| 3 | Persona/safety/consent | FAIL | Safety gate NOT wired to _run_loop(); consent prompt-only |
| 4 | Skills/plugin integration | PASS | ADR-035 Phase 5 enhancements live |
| 5 | Rituals/scheduler/cron | PASS WITH FINDINGS | Hermes cron live; P4 deprecated not removed |
| 6 | Docs/evidence consistency | FAIL | 6 overclaims, 5 stale evidence items |
| 7 | Tests/coverage validity | CONDITIONAL | 2/21 per-module; E2E exists; "205 passed" is gate suite |
| 8 | Security/secrets/privacy | CONDITIONAL | No secrets exposed; raw surveillance data flow |
| 9 | Cross-phase compatibility | PASS WITH FINDINGS | P20 supersedes as brain; P19 plumbed not wired |
| 10 | Deployment/runtime activation | PASS WITH FINDINGS | Deployed and wired; LLM dormant |

---

## Bug Register Summary

| Severity | Count | Requires Mama Approval |
|----------|-------|----------------------|
| CRITICAL | 5 | YES (all 5) |
| HIGH | 5 | YES (3), NO (2) |
| MEDIUM | 5 | YES (2), NO (3) |
| LOW | 2 | NO |
| COSMETIC | 1 | NO |
| **TOTAL** | **18** | |

---

## Hard Rejection Checklist

| Criterion | Result |
|-----------|--------|
| Audit only documents without source/runtime check | ✅ PASS — source code read across 21 files |
| Claims live without VPS/log/runtime proof | ⚠️ CONDITIONAL — code proves wiring; VPS live check not performed |
| Source code exists but caller/wiring not checked | ✅ PASS — all import chains verified |
| Feature flag/off/inert not mentioned | ✅ PASS — llm_router=None explicitly documented |
| P4/P19/P20 latest state not reconciled | ✅ PASS — full cross-phase reconciliation done |
| Secret/token printed | ✅ PASS — zero secrets exposed |
| Audit performs fix/mutation | ✅ PASS — read-only audit |
| Sub-agent output inline-only without file | ✅ PASS — all reports written to files |
| Final report lacks all-severity bug register | ✅ PASS — 18 bugs across 5 severity levels |
| Tests "collected" claimed as "passed" | ✅ PASS — "205 passed" correctly attributed to gate suite |

**Hard Rejection Result: 9/10 PASS, 1 CONDITIONAL (VPS live check)**

---

## Classification Summary

| Classification | Count | Examples |
|---------------|-------|---------|
| IMPLEMENTED_AND_LIVE | 8 | LoopManager, Guardian, API routes, Discord cmds, Hermes cmds |
| IMPLEMENTED_BUT_NOT_WIRED | 4 | LoopSafetyGate, IterationBudget, consent check, project_id |
| DEPLOYED_BUT_FLAG_OFF_OR_INERT | 1 | Phase execution (llm_router=None) |
| DOCS_ONLY | 2 | Consent boundary, sub-agent constraints |
| DEAD_CODE | 3 | 5 modules (enforcer etc), distress labels, HermesBridge |
| SUPERSEDED_BY_LATER_PHASE | 1 | HermesBridge → HermesBrain |
| IMPLEMENTED_WITH_BUG | 3 | cost.py fail-open, naming, raw surveillance data |
| STALE_EVIDENCE | 2 | batch-plan, CLI commands |
| NEEDS_OPERATOR_DECISION | 1 | Dual brain systems |
| NEEDS_SOURCE_FIX_APPROVAL | 5 | All CRITICAL bugs |

---

## Recommended Next Actions

1. **Mama reviews and approves** the 5 CRITICAL bug fixes (Batch 1: safety gate, consent, budget, cost fail-closed)
2. **Operator decides** whether to wire llm_router to LoopManager or document as non-LLM executor
3. **Code quality cleanup** (Batch 3) can proceed without approval
4. **VPS live verification** is a required follow-up gate
5. **P4 ritual_scheduler removal** per deprecation timeline
