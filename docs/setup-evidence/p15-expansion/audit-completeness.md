# P15 Windows Daemon — StepPrompts Completeness Audit

**Date:** 2026-06-04  
**Auditor:** Guinevere (Sisyphus-Junior)  
**Source:** `stepprompts/StepPrompts.md` lines 53382–57318  
**Planner Gate:** `docs/setup-evidence/plans/p15-windows-daemon.md` v1.0  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL

---

## Verdict: FAIL (Remediable)

| Category | Status | Detail |
|----------|--------|--------|
| All 15 steps present | **PASS** | P15-001 through P15-015 all exist |
| Step dependencies correct | **PASS** | All 15 match planner gate exactly |
| Evidence paths correct | **PASS** | All 15 follow `docs/setup-evidence/p15-expansion/STEP-P15-NNN/` |
| Implementation commands real | **PASS** | All 15 contain actual code/commands, zero TBD/placeholders |
| Verification executable | **PASS** | All 15 have executable commands with expected outputs |
| 13-section compliance (sections 2-13) | **PASS** | Goal, Dependencies, Context, Pre-flight, Commands, Verification, Evidence, Rollback, Troubleshooting, Notes, AC References, Est. Time all present |
| Metadata table (section 1) | **FAIL** | All 15 steps missing `Type`, `Risk`, `Git Commit` fields |
| Wave labels on metadata | **FAIL** | P15-006 through P15-015 missing wave assignment |

**3 total failures, all surface-level metadata. Core implementation content is complete.**

---

## Per-Step Checklist (15 Rows)

| Step | Title | 13-Sect | Impl Code | Verif Cmds | Deps | Evidence | Wave Label |
|------|-------|---------|-----------|------------|------|----------|------------|
| P15-001 | Project Scaffold + Base Tracker ABC | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (None) | PASS | Wave 1 ✓ |
| P15-002 | Active Window Tracker | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-001) | PASS | Wave 2 ✓ |
| P15-003 | Idle Tracker | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-001) | PASS | Wave 2 ✓ |
| P15-004 | Git Context Tracker | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-001) | PASS | Wave 2 ✓ |
| P15-005 | Event Pipeline | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-002,3,4) | PASS | Wave 3 ✓ |
| P15-006 | NSSM Service Wrapper + Config | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-005) | PASS | **MISSING** |
| P15-007 | VPS WebSocket Endpoint | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (None) | PASS | **MISSING** |
| P15-008 | Command Protocol (ACK) | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-007) | PASS | **MISSING** |
| P15-009 | Consent Gate Integration | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-007,8) | PASS | **MISSING** |
| P15-010 | Discord /pc Command | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-009) | PASS | **MISSING** |
| P15-011 | Observability (Prom+Grafana) | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-009) | PASS | **MISSING** |
| P15-012 | TimescaleDB Migration | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (None) | PASS | **MISSING** |
| P15-013 | Test Suite | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-005,7,8) | PASS | **MISSING** |
| P15-014 | Integration Test (E2E) | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-013) | PASS | **MISSING** |
| P15-015 | Deployment + Smoke Test | **FAIL** (no Type/Risk/GitCo) | PASS | PASS | PASS (P15-014) | PASS | **MISSING** |

**Legend:** 13-Sect = 13 required sections present? | Impl Code = Actual code, not TBD? | Verif Cmds = Executable verification with expected output? | Deps = Match planner gate? | Evidence = Path follows convention?

---

## Missing Sections Detail

### Finding 1: Metadata Table — Universal Missing Fields

All 15 steps use this metadata table format:

```
| Field | Value |
|---|---|
| Phase | P15 — Windows Daemon (Wave N) |
| Step | P15-NNN |
| Category | ... |
| Dependencies | ... |
| Est. Time | ... |
| ADR Refs | ... |
| Status | ⬜ Not Started |
```

**Three fields are missing from every step:**

| Missing Field | Required Per AGENTS.md | Remediation |
|---------------|------------------------|-------------|
| `Type` | Tier 1 format requires explicit Type label | Change `Category` to `Type`, or add `Type` row |
| `Risk` | Risk assessment required before execution | Add row: `Risk | Low / Medium / High / Safety-Critical` |
| `Git Commit` | Traceability to commit | Add row: `Git Commit | TBD` (fill post-implementation) |

**Affected:** All 15 steps (P15-001 through P15-015).

### Finding 2: Wave Labels Missing (10 steps)

Only P15-001 through P15-005 have explicit wave assignments in their metadata. Steps P15-006 through P15-015 are labeled simply `"P15 — Windows Daemon"` with no wave number.

Per planner gate §2 (Parallelism Groups):

| Wave | Expected Steps | Label Present? | Missing Labels |
|------|---------------|----------------|----------------|
| Wave 1 | P15-001, P15-007, P15-012 | P15-001 only | **P15-007, P15-012** |
| Wave 2 | P15-002, P15-003, P15-004 | All 3 ✓ | — |
| Wave 3 | P15-005, P15-008 | P15-005 only | **P15-008** |
| Wave 4 | P15-006, P15-009 | None | **P15-006, P15-009** |
| Wave 5 | P15-010, P15-011 | None | **P15-010, P15-011** |
| Wave 6 | P15-013, P15-014 | None | **P15-013, P15-014** |
| Wave 7 | P15-015 | None | **P15-015** |

**Note:** P15-007 and P15-012 reference "Wave 1" in their dependency text (`"None (Wave 1, parallel with P15-001 and P15-012)"`) but their Phase metadata row does NOT include the wave label. The dependency text is informative but not a substitute for the Phase field convention.

---

## Dependency Map Verification

All 15 step dependencies match the planner gate exactly:

| Step | Planner Gate Deps | StepPrompts Deps | Match |
|------|-------------------|------------------|-------|
| P15-001 | — (none) | None (Parallel with P15-007 and P15-012) | ✓ |
| P15-002 | P15-001 | P15-001 (BaseTracker ABC) | ✓ |
| P15-003 | P15-001 | P15-001 (BaseTracker ABC) | ✓ |
| P15-004 | P15-001 | P15-001 (BaseTracker ABC) | ✓ |
| P15-005 | P15-002, P15-003, P15-004 | P15-002, P15-003, P15-004 (All trackers) | ✓ |
| P15-006 | P15-005 | P15-005 (Event Pipeline) | ✓ |
| P15-007 | — (none) | None (Wave 1, parallel with P15-001 and P15-012) | ✓ |
| P15-008 | P15-007 | P15-007 (WS Endpoint) | ✓ |
| P15-009 | P15-007, P15-008 | P15-007 (WS Endpoint), P15-008 (Commands) | ✓ |
| P15-010 | P15-009 | P15-009 (Consent Gate) | ✓ |
| P15-011 | P15-009 | P15-009 (Consent Gate) | ✓ |
| P15-012 | — (none) | None (Wave 1, parallel with P15-001 and P15-007) | ✓ |
| P15-013 | P15-005, P15-007, P15-008 | P15-005, P15-007, P15-008 | ✓ |
| P15-014 | P15-013 | P15-013 (unit tests pass first) | ✓ |
| P15-015 | P15-014 | P15-014 (E2E tests pass) | ✓ |

**Verdict: PASS.** Zero dependency mismatches.

---

## Wave Structure Verification

### Planner Gate (Authority) vs StepPrompts

| Wave | Planner Gate Steps | StepPrompts Labels Present | 
|------|-------------------|---------------------------|
| Wave 1 | P15-001, P15-007, P15-012 | Only P15-001 |
| Wave 2 | P15-002, P15-003, P15-004 | All 3 ✓ |
| Wave 3 | P15-005, P15-008 | Only P15-005 |
| Wave 4 | P15-006, P15-009 | None |
| Wave 5 | P15-010, P15-011 | None |
| Wave 6 | P15-013, P15-014 | None |
| Wave 7 | P15-015 | None |

### Note on Task Description Wave Expectations

The original audit task description listed a different wave structure:
- "Wave 3 (P15-005), Wave 4 (P15-006,008), Wave 5 (P15-009,010), Wave 6 (P15-011), Wave 7 (P15-013,014,015)"

This conflicts with the planner gate which defines:
- Wave 3: P15-005, P15-008
- Wave 4: P15-006, P15-009
- Wave 5: P15-010, P15-011
- Wave 6: P15-013, P15-014
- Wave 7: P15-015

**The planner gate is authoritative** per AGENTS.md §2.4: "Planner output is the authority for sequential vs parallel execution." The StepPrompts Phase labels must match the planner gate, not the audit task description.

---

## Section-by-Section Status (All 15 Steps)

| # | Section | P1 | P2 | P3 | P4 | P5 | P6 | P7 | P8 | P9 | P10 | P11 | P12 | P13 | P14 | P15 |
|---|---------|----|----|----|----|----|----|----|----|----|-----|-----|-----|-----|-----|-----|
| 1 | Metadata (Type/Status/Risk/GitCom) | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ | ✗ |
| 2 | Goal | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 3 | Dependencies | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 4 | Context | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 5 | Pre-flight Checks | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 6 | Implementation Commands | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 7 | Verification | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 8 | Evidence | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 9 | Rollback | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 10 | Troubleshooting | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 11 | Notes | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 12 | AC References | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| 13 | Estimated Time | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |

**Legend:** ✓ = Present | ✗ = Missing/Incomplete

---

## Cross-Cutting Checks Summary

| Check | Status | Detail |
|-------|--------|--------|
| All 15 steps present | **PASS** | P15-001 through P15-015, no gaps |
| No extra/missing steps vs planner | **PASS** | Exactly 15 steps in both |
| Implementation = real code, not TBD | **PASS** | All steps have concrete code blocks (Python, PowerShell, SQL, JSON, Markdown, Bash) |
| Verification = executable | **PASS** | All steps have runnable commands with `# Expected:` output annotations |
| Dependencies valid | **PASS** | 15/15 match planner gate §1 |
| Evidence paths correct | **PASS** | 15/15 follow `docs/setup-evidence/p15-expansion/STEP-P15-NNN/` |
| Wave labels complete | **FAIL** | Only 5 of 15 have explicit wave labels |
| Metadata 13-section minimum | **FAIL** | All 15 missing Type, Risk, Git Commit |
| No forbidden patterns in implementation | **PASS** | No `as any`, `# type: ignore`, or bare `except:` found in code blocks |
| Safety-critical flagged (P15-009) | **PARTIAL** | P15-009 Category notes "Safety-Critical" but no `Risk` field to formalize |

---

## Remediation Actions (Required Before Implementation)

### Action 1: Add Missing Metadata Fields (All 15 Steps)
Add these 3 rows to every step's metadata table:

```markdown
| **Type** | Implementation |
| **Risk** | Low / Medium / High / Safety-Critical |
| **Git Commit** | TBD |
```

Risk assignments per planner gate §11 (Auditor Matrix):
- P15-001, P15-003, P15-005, P15-006, P15-008, P15-010, P15-011, P15-012, P15-013, P15-014, P15-015: `Risk | Medium`
- P15-002, P15-004: `Risk | Medium` (data minimization concerns)
- P15-007: `Risk | High` (security boundary)
- P15-009: `Risk | Safety-Critical` (consent gate, fail-closed)

### Action 2: Add Wave Labels to Phase Field (10 Steps)
Update the Phase metadata row for these steps:

| Step | Current Phase Value | Corrected Phase Value |
|------|-------------------|----------------------|
| P15-007 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 1)` |
| P15-012 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 1)` |
| P15-008 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 3)` |
| P15-006 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 4)` |
| P15-009 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 4)` |
| P15-010 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 5)` |
| P15-011 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 5)` |
| P15-013 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 6)` |
| P15-014 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 6)` |
| P15-015 | `P15 — Windows Daemon` | `P15 — Windows Daemon (Wave 7)` |

### Action 3: Re-run Audit After Fixes
After applying Actions 1 and 2, re-run this audit to confirm:
- All 15 steps have `Type`, `Risk`, `Git Commit` in metadata
- All 15 steps have correct wave labels
- No regressions introduced

---

## Evidence Sources

| Source | Path | Purpose |
|--------|------|---------|
| Planner Gate | `docs/setup-evidence/plans/p15-windows-daemon.md` | Authority for dependencies, waves, audit matrix, scope |
| StepPrompts P15 | `stepprompts/StepPrompts.md` L53382-57318 | Subject of audit |
| Batch Report 1 | `docs/setup-evidence/p15-expansion/_audit-batch1.md` | P15-001 through P15-005 analysis |
| Batch Report 2 | `docs/setup-evidence/p15-expansion/_audit-batch2.md` | P15-006 through P15-010 analysis |
| Batch Report 3 | `docs/setup-evidence/p15-expansion/_audit-batch3.md` | P15-011 through P15-015 analysis |

---

## Footer

| Field | Value |
|-------|-------|
| **Audit Version** | 1.0 |
| **Date** | 2026-06-04 |
| **Auditor** | Guinevere (Sisyphus-Junior) |
| **Verdict** | **FAIL** — 3 remediable findings, zero blocking on core implementation content |
| **Blocking Implementation?** | **No.** All implementation commands, verification, dependencies, and evidence paths are complete and correct. Failures are purely metadata/labeling gaps. |
| **Next Step** | Apply remediation Actions 1-2, re-audit, then proceed with Wave 1 implementation delegation |