# P19 Completion Round 2 — Audit Plan

**Date:** 2026-06-27 ~17:15 WIB  
**Author:** Guinevere (parent orchestrator)  
**Phase:** Phase 2 — Planner Gate  
**Status:** PLAN ACTIVE — AWAITING PHASE 1 AUDIT RESULTS

---

## Executive Summary

This plan defines the audit strategy for verifying P19 production completeness claims. Ground truth inspection (Phase 0) revealed **critical contradictions** between the P19 final production report and actual VPS state. This plan ensures all findings are investigated, validated, and resolved before final closure.

---

## Ground Truth Findings (Phase 0)

The following contradictions were discovered during live VPS inspection:

| ID | Finding | Severity | Status |
|----|---------|----------|--------|
| F1 | Feature flag ON but report says OFF | 🔴 CRITICAL | Stale claim in report |
| F2 | Service restarted at 15:31:10 but report claims uptime since 2026-06-25 | 🔴 CRITICAL | Stale claim in report |
| F3 | `memory_recall_degraded` errors at 15:30 (Episodes model missing project_id) | 🔴 CRITICAL | Resolved by 16:50 — root cause unknown |
| F4 | `life_kernel.audit_journal` has no `project_id` column (only in JSON payload) | 🟡 DESIGN GAP | Not a bug — design choice |
| F5 | `project_id=None` in cognition logs despite flag being ON | 🟡 PROPAGATION GAP | Benign with 1 project, will break with multiple projects |
| F6 | No Discord command sync logs in recent window | 🟡 EVIDENCE GAP | Source code verified, but live state unconfirmed |
| F7 | `project_registry` schema uses `id` not `project_id` (naming deviation) | 🟢 COSMETIC | No functional impact |

---

## Audit Strategy

### Phase 1: Research Brutal (7 parallel agents)

Seven independent sub-agents are currently running, each investigating a specific dimension:

1. **Runtime auditor** — Verify P19 code is loaded on VPS, investigate F3 (Episodes model)
2. **DB auditor** — Verify project_id propagation across all tables, investigate F4 (audit_journal)
3. **Recall auditor** — Verify recall pipeline project_id forwarding, investigate F3 root cause
4. **Discord auditor** — Verify /project and /projects commands are registered and usable
5. **Security/consent auditor** — Verify consent isolation with flag ON
6. **P20 regression auditor** — Verify P20 living autonomy health after restart
7. **Evidence/docs auditor** — Reconcile stale claims in documentation

Each agent will write a markdown report to:
```
docs/setup-evidence/P19/evidence/completion-round-2/audits/<dimension>.md
```

### Phase 2: Synthesize Findings (current phase)

After all agents complete, the parent will:
1. Read all 7 audit reports
2. Consolidate findings into a master findings list
3. Classify each finding by severity (CRITICAL / HIGH / MEDIUM / LOW / INFORMATIONAL)
4. Determine which findings require fixes vs. documentation updates

### Phase 3: Audit Round 2 (verification checks)

Run the following verification checks (parent or verifier agents):

#### 3.1 Runtime Health
- [ ] guinevere-core active
- [ ] NRestarts unchanged since 15:31:10 (or explained if changed)
- [ ] No GraphRecursionError in logs
- [ ] No recall_degraded errors after 16:50
- [ ] No memory_recall_degraded TypeError
- [ ] No dashboard duplicate regression
- [ ] No fallback storm

#### 3.2 Database Integrity
- [ ] Recent audit_journal rows have project_id (in JSON)
- [ ] No recent P19-owned audit rows missing project_id
- [ ] project_registry default project exists
- [ ] memory tables contain expected project_id/project_scope columns
- [ ] audit.audit_trail has project_id and chain_version columns

#### 3.3 Recall Pipeline
- [ ] `_life_recall_fn` forwards project_id
- [ ] `recall_memories` filters by project_id/project_scope
- [ ] Live logs show `memory_recall_success` (not degraded)
- [ ] No silent fallback to unscoped memory

#### 3.4 Discord Commands
- [ ] /project and /projects registered in live bot
- [ ] Command sync log is not sole evidence (API verification preferred)
- [ ] No duplicate Discord writer regression

#### 3.5 Safety & Consent
- [ ] HARD STOP still honored globally
- [ ] Consent revocation not bypassed by project isolation
- [ ] No secrets printed in logs
- [ ] No Y6/persona boundary violations

#### 3.6 Regression Testing
- [ ] Run relevant local tests (if available)
- [ ] Run P19 targeted tests
- [ ] Run P20 regression subset
- [ ] Document skipped tests honestly

#### 3.7 Evidence & Documentation
- [ ] All completion evidence paths exist
- [ ] No stale final status contradictions
- [ ] Final status not overstated

### Phase 4: Fix All Severity (if findings appear)

If any valid finding appears:
- Classify severity (CRITICAL / HIGH / MEDIUM / LOW)
- Fix all severities, including LOW/COSMETIC if they affect evidence clarity
- Do not leave known issues unless Faiz explicitly accepts risk
- If deploy needed:
  1. Backup (pg_dump, git tag)
  2. Patch only touched files
  3. Restart only required service
  4. Smoke test
  5. Runtime proof
  6. Rollback path documented
- Write fixes to:
  ```
  docs/setup-evidence/P19/evidence/completion-round-2/fixes/p19-completion-fix-log.md
  ```
- Re-run affected tests/checks

### Phase 5: Re-Audit After Fix (if fixes happened)

If fixes were applied:
- Spawn re-audit agents for affected dimensions
- Write re-audit report to:
  ```
  docs/setup-evidence/P19/evidence/completion-round-2/audits/round-2-after-fix.md
  ```
- Parent verifies all claims

### Phase 6: Finalization

Update:
- P19 final report/status docs
- PROGRESS.md / CHECKLIST.md (if used)
- Evidence index/readme (if used)
- Historical reports marked as superseded (not silently rewritten)

### Phase 7: Final Report

Write final report to:
```
docs/setup-evidence/P19/evidence/completion-round-2/final/p19-completion-round-2-final-report.md
```

Final report must include:
- Final verdict
- What was verified live
- Tests run
- Runtime proof
- DB proof
- Discord proof
- P20 regression proof
- Evidence paths
- Unresolved findings (if any)
- Exact next action

---

## Hard Rejection Criteria

The audit will FAIL if:

1. ❌ Only docs are compared without inspecting runtime/VPS
2. ❌ `commands_synced` is accepted as sole Discord proof without caveat
3. ❌ project_id propagation is only source-code claimed and not DB/log verified
4. ❌ Recall success is claimed while degraded/fallback logs exist
5. ❌ P20 health is not checked
6. ❌ Any secret/token appears in evidence
7. ❌ Audit round 2 finds a valid issue and it is not fixed/re-audited
8. ❌ Final status says CLOSED/PASS without evidence paths
9. ❌ Sub-agent output is inline-only without file

---

## Allowed Final Statuses

1. **P19 PRODUCTION COMPLETE — CLOSED**  
   Only if runtime + DB + recall + Discord + P20 regression + evidence all PASS.

2. **P19 PRODUCTION COMPLETE — PASS WITH ACCEPTED RISK**  
   Only if Faiz/mama explicitly accepts a documented residual risk.

3. **P19 PRODUCTION COMPLETE CANDIDATE — FIXES REQUIRED**  
   If valid findings remain unresolved.

4. **P19 BLOCKED**  
   Only with exact blocker and next executable step.

---

## Dependency Map

```
Phase 0 (Ground Truth) ──> Phase 1 (Research Brutal) ──> Phase 2 (Synthesize) ──> Phase 3 (Audit Round 2)
                                                                                     │
                                                                                     ├─> Phase 4 (Fix) ──> Phase 5 (Re-Audit)
                                                                                     │
                                                                                     └─> Phase 6 (Finalization) ──> Phase 7 (Final Report)
```

---

## Rollback / No-Touch Policy

- Do not restart/deploy services unless a valid runtime finding requires a fix
- Do not disturb P20 production except for read-only health checks
- If fix requires deploy:
  1. Backup (pg_dump, git tag)
  2. Patch only touched files
  3. Restart only required service
  4. Smoke test
  5. Runtime proof
  6. Rollback path documented

---

## Evidence Files

All evidence will be written to:
```
docs/setup-evidence/P19/evidence/completion-round-2/
├── research/
│   └── p19-completion-ground-truth.md
├── plan/
│   └── p19-completion-round-2-plan.md
├── audits/
│   ├── runtime-health.md
│   ├── db-project-id-propagation.md
│   ├── memory-recall-project-scope.md
│   ├── discord-project-commands.md
│   ├── security-consent-boundary.md
│   ├── p20-regression-safety.md
│   ├── evidence-docs-consistency.md
│   └── round-2-after-fix.md (if fixes needed)
├── fixes/
│   └── p19-completion-fix-log.md (if fixes needed)
└── final/
    └── p19-completion-round-2-final-report.md
```

---

## Current Status

**Phase 1: Research Brutal** — 7 agents running in background:
- Runtime auditor (ID: ae1ffe3b817e32f62)
- DB auditor (ID: ab9efba1100c935a3)
- Recall auditor (ID: ac5fce8dc3a648de6)
- Discord auditor (ID: a3f907c57446f4aab)
- Security/consent auditor (ID: aff3d58675a32feb1)
- P20 regression auditor (ID: acef82adc13a83ea8)
- Evidence/docs auditor (ID: a7af9af6ec982e8b4)

**Next step:** Wait for all agents to complete, then read all reports and synthesize findings.

---

## Footer

| Field | Value |
|---|---|
| Plan date | 2026-06-27 ~17:15 WIB |
| Author | Guinevere (parent orchestrator) |
| Status | PLAN ACTIVE — AWAITING PHASE 1 AUDIT RESULTS |
| Agents running | 7 |
