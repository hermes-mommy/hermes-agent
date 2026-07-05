# P27 Evidence File Structure Audit

| Field | Value |
|---|---|
| Auditor | 12-evidence (evidence file structure) |
| Scope | Evidence directory structure, required paths, schema compliance |
| Date | 2026-06-28 |
| Plan reference | `docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md` |
| Sections audited | §20 (L3985-4134), §25 (L4563-4706) |

---

## VERDICT: FAIL

---

## Summary

P27 plan specifies a comprehensive 14-auditor evidence structure with 10 research files, 3 plan files, and dual-round audit directories. The evidence **paths** are well-specified and the docs-sync plan is complete. However, 6 of 14 round-1 audit files are missing (57% coverage), 3 Phase 9 evidence files are absent (expected, deferred), 1 research file is missing, and the evidence schema has 11 sections instead of the required 12 per AGENTS.md §11. P27 correctly defines itself as definition-only with no false implementation claims.

---

## Findings

### F1. Round-1 Audit Files: 8 of 14 Present (57%) — MISSING 6

**Section:** §25.1 (L4589-4603)
**Severity:** FAIL

Plan specifies 14 audit files (`01-equal-peer.md` through `14-hard-rejection-criteria.md`). Only 8 exist:

| # | File | Status |
|---|---|---|
| 01 | `01-equal-peer.md` | ✅ EXISTS |
| 02 | `02-sub-agent-rejection.md` | ✅ EXISTS |
| 03 | `03-memory-isolation.md` | ✅ EXISTS |
| 04 | `04-autonomy.md` | ✅ EXISTS |
| 05 | `05-discord-dual-bot.md` | ✅ EXISTS |
| 06 | `06-peer-protocol.md` | ✅ EXISTS |
| 07 | `07-p24-dependency.md` | ✅ EXISTS |
| 08 | `08-p22-p23-dep.md` | ✅ EXISTS |
| 09 | `09-safety-boundary.md` | ❌ MISSING |
| 10 | `10-persona-safety.md` | ❌ MISSING |
| 11 | `11-roadmap.md` | ❌ MISSING |
| 12 | `12-evidence.md` | ❌ MISSING (this file) |
| 13 | `13-impl-feasibility.md` | ❌ MISSING |
| 14 | `14-hard-rejection-criteria.md` | ❌ MISSING |

**Impact:** Audit round 1 is incomplete. 6 specialist auditor reports have not been generated. The plan claims (L4666) "14 auditors all PASS in round 1 and 2" — this claim is aspirational, not yet verified by existing files.

### F2. Evidence Schema: 11 Sections, Not 12

**Section:** §20.2 (L4036-4048) vs AGENTS.md §11
**Severity:** FAIL

The `evidence_schema_minimum` array in the verification scaffold template lists 11 sections:

```
what_was_done, files_changed, validation_results, doc_sync_impact,
boundary_compliance, rollback_safety, design_decisions_caveats,
auditor_gate, security_scan, acceptance_criteria_mapping, footer
```

AGENTS.md §11 requires **12 sections**: What Was Done; Files Changed; Validation Results; **Evidence Artifacts**; Doc-Sync Impact; Boundary Compliance; Rollback/Re-run Safety; Design Decisions/Caveats; Auditor Gate; Security Scan; Acceptance Criteria Mapping; Footer.

**Missing section:** `evidence_artifacts` (paths to sub-agent reports, auditor reports, verification files).

### F3. `verification.md` Absent from `evidence/`

**Section:** §25.1 (L4606)
**Severity:** EXPECTED (Phase 6/9 artifact)

Plan specifies `docs/setup-evidence/P27/evidence/verification.md` as a Phase 6/8 artifact with 12 sections. File does not exist. This is expected since audit round 1 is still in progress — but it means the evidence cycle cannot be declared complete.

### F4. `auditor-gate.md` Absent from `evidence/`

**Section:** §25.1 (L4607)
**Severity:** EXPECTED (Phase 6/9 artifact)

Plan specifies `docs/setup-evidence/P27/evidence/auditor-gate.md`. File does not exist. Same deferral reasoning as F3.

### F5. `p27-final-report.md` Absent from `evidence/`

**Section:** §25.6 (L4655)
**Severity:** EXPECTED (Phase 9 artifact)

Plan specifies `docs/setup-evidence/P27/evidence/p27-final-report.md` as a Phase 9 finalization artifact. Not yet created. Expected — Phase 9 runs after audits complete.

### F6. `REPO_STATE.md` Absent from `research/`

**Section:** §25.1 (L4582)
**Severity:** LOW

Plan directory tree shows `research/REPO_STATE.md`. File does not exist. 11 of 12 planned research files exist (10 research + synthesis). This is a minor gap — `p27-ground-truth-repo-state.md` may serve the same purpose.

### F7. `README.md` Absent from P27 Root

**Section:** §25.1 (L4569)
**Severity:** LOW

Plan specifies `docs/setup-evidence/P27/README.md` as a Phase 9 artifact. Not yet created. Expected for Phase 9.

### F8. No Implementation Claims — CORRECT

**Section:** §25.6 (L4659-4660), Final Summary (L4734)
**Severity:** N/A (PASS)

P27 correctly defines itself as definition-only. L4659: "new plan file only. No source code changed. No config files changed. No deployment." L4734: "Implementation is deferred to P28." No false implementation claims found.

### F9. Verification Scaffold Structure — WELL SPECIFIED

**Section:** §20.2-20.5 (L3996-4116)
**Severity:** N/A (PASS)

All 5 required scaffold fields present:
- ✅ `expected_files` (L4002-4004)
- ✅ `forbidden_patterns` (L4006-4014, 9 patterns listed)
- ✅ `required_commands` (L4016-4031, 3 commands with exit codes)
- ✅ `evidence_requirements` (L4033-4049, with verification_md and auditor_gate paths)
- ✅ `hard_rejection_criteria` (L4051-4063, 2 criteria in template + 20 in §24)

Scaffold is a **template** for P28 inheritance, not P27 self-verification. This is appropriate.

### F10. Docs Sync Plan — COMPLETE

**Section:** §25.2-25.5 (L4610-4651)
**Severity:** N/A (PASS)

All 4 required doc sync targets specified:
- ✅ `PROGRESS.md` — +1 line (L4614-4616)
- ✅ `CHECKLIST.md` — +10 items (L4622-4633)
- ✅ `ADR-Index` — conditional ADR-054 (L4637-4643)
- ✅ `docs/README.md` — +1 entry (L4648-4651)

All deferred to Phase 9, which is correct for a definition phase.

### F11. Evidence Forbidden Patterns — SPECIFIED

**Section:** §25.8 (L4682-4688)
**Severity:** N/A (PASS)

5 evidence-specific forbidden patterns defined: no fake audits, no skipped coverage, no secrets, no 0-byte verification.md, no FAIL without remediation. These complement AGENTS.md BLOCKING rules.

---

## Recommendations

### R1. CRITICAL — Generate Missing Audit Files 09-14

Complete the 6 missing round-1 auditor reports:

| File | Subject |
|---|---|
| `09-safety-boundary.md` | Safety boundary review (PersonaSafetyPolicy, consent, surveillance) |
| `10-persona-safety.md` | Persona safety (Y4/Y5 ceiling, no Y6, Pharsa persona constraints) |
| `11-roadmap.md` | P28-P36 roadmap completeness and dependency validity |
| `12-evidence.md` | This file (evidence structure audit) |
| `13-impl-feasibility.md` | Implementation feasibility (can P28 execute what P27 defines?) |
| `14-hard-rejection-criteria.md` | Hard rejection criteria review (all 20 criteria valid and testable?) |

### R2. CRITICAL — Fix Evidence Schema to 12 Sections

Add `evidence_artifacts` to the `evidence_schema_minimum` array in §20.2 (L4036-4048). Current 11-item list should become 12:

```diff
 "evidence_schema_minimum": [
   "what_was_done",
   "files_changed",
   "validation_results",
+  "evidence_artifacts",
   "doc_sync_impact",
   "boundary_compliance",
   "rollback_safety",
   "design_decisions_caveats",
   "auditor_gate",
   "security_scan",
   "acceptance_criteria_mapping",
   "footer"
 ]
```

### R3. LOW — Create `research/REPO_STATE.md`

Either create `REPO_STATE.md` as specified in the directory tree, or remove it from the §25.1 tree if `p27-ground-truth-repo-state.md` already serves this purpose.

### R4. DEFERRED — Phase 9 Artifacts

After audit rounds complete, ensure these Phase 9 artifacts are created:
- `evidence/verification.md` (12 sections)
- `evidence/auditor-gate.md` (PASS/FAIL verdict)
- `evidence/p27-final-report.md` (§25.6 template)
- `README.md` (P27 root index)

---

## Evidence Path Verification Matrix

| Specified Path (§25.1) | Exists | Notes |
|---|---|---|
| `research/p27-ground-truth-repo-state.md` | ✅ | |
| `research/p27-hermes-native-runtime-inventory.md` | ✅ | |
| `research/p27-multi-agent-society-research.md` | ✅ | |
| `research/p27-agent-communication-protocol-research.md` | ✅ | |
| `research/p27-discord-dual-bot-research.md` | ✅ | |
| `research/p27-private-shared-memory-research.md` | ✅ | |
| `research/p27-life-loop-beyond-heartbeat-research.md` | ✅ | |
| `research/p27-autonomy-safety-audit-research.md` | ✅ | |
| `research/p27-p24-fork-dependency-map.md` | ✅ | |
| `research/p27-p19-p20-p22-p23-dependency-map.md` | ✅ | |
| `research/p27-research-synthesis.md` | ✅ | |
| `research/REPO_STATE.md` | ❌ | MISSING |
| `plan/p27-hermes-society-foundation-plan.md` | ✅ | |
| `plan/p28-p36-roadmap.md` | ✅ (as `p27-p28-p36-master-roadmap.md`) | Name differs from plan spec |
| `plan/p28-executable-blueprint.md` | ✅ (as `p28-dual-autonomous-hermes-blueprint.md`) | Name differs from plan spec |
| `evidence/audits/round-1/01-equal-peer.md` | ✅ | |
| `evidence/audits/round-1/02-sub-agent-rejection.md` | ✅ | |
| `evidence/audits/round-1/03-memory-isolation.md` | ✅ | |
| `evidence/audits/round-1/04-autonomy.md` | ✅ | |
| `evidence/audits/round-1/05-discord-dual-bot.md` | ✅ | |
| `evidence/audits/round-1/06-peer-protocol.md` | ✅ | |
| `evidence/audits/round-1/07-p24-dependency.md` | ✅ | |
| `evidence/audits/round-1/08-p22-p23-dep.md` | ✅ | |
| `evidence/audits/round-1/09-safety-boundary.md` | ❌ | MISSING |
| `evidence/audits/round-1/10-persona-safety.md` | ❌ | MISSING |
| `evidence/audits/round-1/11-roadmap.md` | ❌ | MISSING |
| `evidence/audits/round-1/12-evidence.md` | ✅ (this file) | |
| `evidence/audits/round-1/13-impl-feasibility.md` | ❌ | MISSING |
| `evidence/audits/round-1/14-hard-rejection-criteria.md` | ❌ | MISSING |
| `evidence/audits/round-2/` | ✅ (empty) | Expected — re-audit after fixes |
| `evidence/verification.md` | ❌ | Phase 6/9 |
| `evidence/auditor-gate.md` | ❌ | Phase 6/9 |
| `evidence/p27-final-report.md` | ❌ | Phase 9 |
| `README.md` | ❌ | Phase 9 |

**Score:** 22 of 33 paths populated (67%). 5 missing are Phase 6/9 deferred. 5 missing are audit files (09-13, plus this one which is being created). 1 missing is REPO_STATE.md.

---

## Footer

| Field | Value |
|---|---|
| Verdict | **FAIL** |
| Blocking findings | F1 (6 missing audit files), F2 (11/12 evidence schema sections) |
| Non-blocking | F3-F7 (deferred Phase 9 artifacts, REPO_STATE.md) |
| Pass items | F8 (no impl claims), F9 (scaffold), F10 (docs sync), F11 (forbidden patterns) |
| Next action | Generate audit files 09-14; fix evidence schema to 12 sections; then re-audit |
