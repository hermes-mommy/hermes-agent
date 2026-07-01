# P5 Brutal Implementation Audit — Plan

**Audit ID:** GAS-AUDIT-P5-2026-06-27
**Auditor:** Guinevere (read-only, full-spectrum)
**Date:** 2026-06-27
**Status:** IN PROGRESS

---

## 1. Audit Objective

Brutal implementation audit of Phase 5 (Agent Loop) — not just document consistency, but:
- Does the implementation ACTUALLY EXIST?
- Is the runtime/live VPS ACTUALLY USING the feature?
- Is code dead code or actually wired?
- Do docs/evidence OVERCLAIM?
- Do P20/P19/P4/P3 changes make Phase 5 claims STALE?

---

## 2. Phase 5 Scope (from PROGRESS.md)

**Phase 5 = Agent Loop** (23 steps, critical path, cost $3/mo)
- Dependencies: P1 (LLM + Hermes) + P3 (Memory System)
- Steps: P5-001 through P5-023
- Plus: P5.5 Remediation (10 fixes)
- Plus: ADR-035 Phase 5 Enhancements (8 steps: 5.1-5.8)
- Plus: Phase 5 Verification T1-T10 (205 tests)
- Plus: P5 Re-Audit (2026-06-09, 6 findings)

---

## 3. Audit Workflow

### Phase 1: Research/Inventory (Parallel Sub-agents)
- [x] Agent 1: Source code inventory
- [x] Agent 2: Evidence files catalog
- [x] Agent 3: Tests & runtime check
- [x] Agent 4: Safety/consent/persona audit
- [x] Agent 5: Cross-phase reconciliation

### Phase 2: Synthesis
- [ ] Read all 5 agent reports
- [ ] Cross-reference findings
- [ ] Identify contradictions
- [ ] Build gap register

### Phase 3: Output Generation
- [ ] p5-scope-map.md
- [ ] p5-evidence-inventory.md
- [ ] p5-source-implementation-map.md
- [ ] p5-runtime-live-reconciliation.md
- [ ] p5-docs-consistency-audit.md
- [ ] p5-safety-consent-persona-audit.md
- [ ] p5-bug-register-all-severity.md
- [ ] p5-implementation-gap-register.md
- [ ] p5-missing-docs-register.md
- [ ] p5-superseded-transition-register.md
- [ ] p5-final-implementation-audit-report.md
- [ ] p5-auditor-gate.md

---

## 4. Audit Dimensions (10 mandatory)

| # | Dimension | Agent |
|---|-----------|-------|
| 1 | Architecture/implementation wiring | Agent 1 + Agent 3 |
| 2 | Runtime/live VPS truth | Agent 3 |
| 3 | Persona/safety/consent | Agent 4 |
| 4 | Skills/plugin integration | Agent 5 (ADR-035) |
| 5 | Rituals/scheduler/cron | Agent 5 (P4 overlap) |
| 6 | Docs/evidence consistency | Agent 2 |
| 7 | Tests/coverage validity | Agent 3 |
| 8 | Security/secrets/privacy | Agent 4 |
| 9 | Cross-phase compatibility | Agent 5 |
| 10 | Deployment/runtime activation | Agent 3 |

---

## 5. Hard Rejection Criteria

- Audit only documents without source/runtime check: FAIL
- Claims live without VPS/log/runtime proof: FAIL
- Source code exists but caller/wiring not checked: FAIL
- Feature flag/off/inert not mentioned: FAIL
- P4/P19/P20 latest state not reconciled: FAIL
- Secret/token printed: FAIL
- Audit performs fix/mutation: FAIL
- Sub-agent output inline-only without file: FAIL
- Final report lacks all-severity bug register: FAIL
- Tests "collected" claimed as "passed": FAIL

---

## 6. Classification Schema

For every Phase 5 claim:
- IMPLEMENTED_AND_LIVE
- IMPLEMENTED_BUT_NOT_WIRED
- IMPLEMENTED_BUT_NOT_DEPLOYED
- DEPLOYED_BUT_FLAG_OFF_OR_INERT
- DOCS_ONLY
- DEAD_CODE
- SUPERSEDED_BY_LATER_PHASE
- STALE_EVIDENCE
- FALSE_POSITIVE
- NEEDS_SOURCE_FIX_APPROVAL
- NEEDS_OPERATOR_DECISION

---

## 7. Allowed Final Statuses

- P5 IMPLEMENTED AND LIVE — PASS_WITH_FINDINGS
- P5 IMPLEMENTED WITH BUGS — SOURCE FIXES REQUIRE MAMA APPROVAL
- P5 PARTIALLY IMPLEMENTED — RUNTIME ACTIVATION/FIX REQUIRED
- P5 DOCS/EVIDENCE ONLY — IMPLEMENTATION MISSING
- P5 AUDIT BLOCKED — NEEDS READONLY ACCESS
