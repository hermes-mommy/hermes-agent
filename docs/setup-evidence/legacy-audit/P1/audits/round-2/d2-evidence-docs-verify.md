# D2 Round-2: Evidence-Docs-Consistency Adversarial Verification

**Audit Dimension:** D2 -- Evidence-Docs-Consistency (Round-2 Adversarial)
**Phase:** P1 (Phase 1: LLM + Hermes Agent Foundation)
**Audit Date:** 2026-06-25
**Auditor:** READ-ONLY adversarial verification subagent
**Round-1 Report:** `docs/setup-evidence/legacy-audit/P1/audits/round-1/evidence-docs-consistency.md`
**Output Path:** `docs/setup-evidence/legacy-audit/P1/audits/round-2/d2-evidence-docs-verify.md`

---

## Per-Finding Verification Results

| Check ID | Round-1 Verdict | Round-1 Claim | Verification Result | R2 Verdict | Notes |
|----------|----------------|---------------|---------------------|------------|-------|
| D2-01 | NEEDS-REVIEW | CHECKLIST marks P1 complete but does not acknowledge 6/7 stale artifacts | **WEAKENED** -- Overstated severity | **PASS** (with caveat) | See detailed analysis below. CHECKLIST never claimed to track source drift; the auditor imposed an out-of-scope expectation. |
| D2-02 | NEEDS-REVIEW | PROGRESS.md P1-021 says "142/142" while evidence.md says "70/70" | **CONFIRMED** | **NEEDS-REVIEW** | Genuine inconsistency. PROGRESS.md L132 "142/142 tests PASS (56 handler + 86 comprehensive)" contradicts STEP-P1-021/evidence.md "70/70 tests PASS (56 handler + 14 model compliance)". |
| D2-03 | PASS | Docs index references valid | **CONFIRMED** | **PASS** | ADR index has valid P1 references. docs/README.md lacks P1 entry but this is not a consistency failure. |
| D2-04 | NEEDS-REVIEW | 7 of 21 STEP directories missing | **CONFIRMED** | **NEEDS-REVIEW** | Exact count: 14 STEP dirs (P1-001..007, P1-015..021), 7 missing (P1-008..014). 3 are SKIPPED (012-014), 4 have no dedicated evidence dirs (008-011). |
| D2-05 | PASS | 3 UTF-16 files genuine, content recoverable | **CONFIRMED** | **PASS** | All 3 files exist, content was decoded by round-1. No fabrication detected. |
| D2-06 | PASS | P1-005 config vs hermes-config not confused | **CONFIRMED** | **PASS** | No document conflates the two configs. |
| D2-07 | NEEDS-REVIEW | SystemPromptMaster v1.1 has zero P1 attribution | **WEAKENED** -- Not a consistency failure | **PASS** (Low cosmetic) | Document is a system prompt, not phase documentation. Requiring "P1" attribution in a system prompt is an out-of-scope expectation. |
| D2-08 | PASS | All referenced ADRs exist | **CONFIRMED** | **PASS** | ADR-004, -006, -014, -028 all exist in `adr/`. No stale references. |
| D2-09 | PASS | P1-021 70/70 test claim valid for P1 snapshot | **CONFIRMED** | **PASS** | evidence.md clearly states 56 handler + 14 model = 70. PROGRESS.md's 142 figure is a later expansion, not a contradiction with the P1 evidence. |

---

## Detailed Verification of Each Finding

### D2-01: CHECKLIST.md P1 Entry

**Round-1 claim:** "CHECKLIST does not flag known source drift. Compliant metadata-wise but misleading for any reader comparing evidence to live source."

**Verification:** Read CHECKLIST.md lines 176-238 (Section 3, Phase 1). Exact text:

> Section 3.2 Step Verification:
> - [x] P1-001 through P1-021: All 21 items marked [x], including P1-012/013/014 marked as "SKIPPED per Faiz directive"
>
> Section 3.3 Integration Tests:
> - [x] HARD STOP Protocol verified: app-level handler (56/56 unit) + GPT-5.5 model compliance (14/14) = 70/70 PASS

**Challenge:** The round-1 auditor claims CHECKLIST "does not acknowledge 6/7 source artifacts have drifted from evidence snapshots." However, this imposes an out-of-scope expectation. CHECKLIST.md is a verification checklist -- it records that steps were completed at the time of implementation. It was never designed to track ongoing source-code drift months after evidence was captured. The "stale artifact" concern is valid metadata but belongs in a drift audit, not in a consistency check of CHECKLIST against evidence.

Furthermore, CHECKLIST.md line 218 states "70/70 PASS" which is **consistent** with the P1-021 evidence.md claim. The round-1 report itself acknowledges CHECKLIST is "compliant metadata-wise."

**Verdict: PASS** -- Round-1 finding is technically correct but overstated as NEEDS-REVIEW. The absence of drift tracking in CHECKLIST is not a consistency failure; it is an expected omission given CHECKLIST's scope.

### D2-02: PROGRESS.md P1-021 Test Count

**Round-1 claim:** "PROGRESS.md P1-021 claim (142/142) does NOT match evidence.md claim (70/70)."

**Verification:** PROGRESS.md line 132 exact text:
> - [x] **P1-021** HARD STOP Protocol Verification Gate (AC-SAFE-001) ✅ 142/142 tests PASS (56 handler + 86 comprehensive — verified 2026-06-08)

STEP-P1-021/evidence.md exact text (line 38):
> ### Total: 70/70 tests PASS ✅

Evidence.md breakdown: 56 handler tests + 14 GPT-5.5 model compliance tests = 70.

**Challenge:** The 142 vs 70 conflict is genuine. PROGRESS.md's "86 comprehensive" is a different test suite than evidence.md's "14 model compliance." PROGRESS.md was updated 2026-06-08 (7 days after P1-021 evidence was captured 2026-06-01), suggesting test expansion occurred after the P1 evidence snapshot. This is a real inconsistency between two project documents that a future reader could find confusing.

**Verdict: NEEDS-REVIEW** -- Confirmed. Genuine inconsistency between PROGRESS.md (142 tests, updated 2026-06-08) and P1-021 evidence.md (70 tests, captured 2026-06-01). Recommend reconciliation: PROGRESS.md should note the expanded test count is post-P1-snapshot, or evidence.md should be updated to reflect the final count.

### D2-04: Missing STEP Directories

**Round-1 claim:** "7 of 21 STEP directories are missing."

**Verification:** `find . -type d | sort` in `docs/setup-evidence/P1/` returns exactly 14 STEP directories plus `migration-9router`:

```
STEP-P1-001, STEP-P1-002, STEP-P1-003, STEP-P1-004, STEP-P1-005,
STEP-P1-006, STEP-P1-007, STEP-P1-015, STEP-P1-016, STEP-P1-017,
STEP-P1-018, STEP-P1-019, STEP-P1-020, STEP-P1-021
```

Missing: P1-008 (GPT-5.5 provider setup), P1-009 (GPT-5.5 connectivity), P1-010 (DeepSeek setup), P1-011 (DeepSeek connectivity), P1-012 (Ollama install), P1-013 (Ollama model pull), P1-014 (Ollama fallback test).

**Challenge:** The auditor's count is correct. Of the 7 missing directories, 3 (P1-012/013/014) are documented as SKIPPED per Faiz directive and have ADR-028 justification. The remaining 4 (P1-008/009/010/011) have no dedicated evidence directories. The evidence for those 4 steps exists only inline within `batch-plan-006-007.md`. This is a legitimate structural gap: the CHECKLIST claims 21/21 steps verified, but only 14 have standalone evidence directories.

**Verdict: NEEDS-REVIEW** -- Confirmed. 7/21 directories missing (33% gap). 3 have documented SKIP justification; 4 are undocumented structural gaps where evidence is only in batch plans.

### D2-05: UTF-16 Encoding Defect

**Round-1 claim:** "Files are genuine captures with encoding defect. No fabrication. Content is fully recoverable via UTF-16 decode."

**Verification:** All 3 files confirmed to exist:
- `STEP-P1-015/import-test.txt` -- exists
- `STEP-P1-016/system-prompt-loaded.txt` -- exists
- `STEP-P1-019/health-check.txt` -- exists

The round-1 report provides decoded content for all three files. The content is consistent with VPS command output (router module test results, system prompt checks, health check output). No evidence of fabrication.

**Verdict: PASS** -- Confirmed. Genuine captures with encoding defect.

### D2-07: SystemPromptMaster v1.1 Attribution

**Round-1 claim:** "Zero P1/Phase 1 attribution in document header metadata."

**Verification:** `grep -i "P1\|Phase 1"` on `docs/60-persona/61-SystemPromptMaster_v1.1.md` returns zero matches. The document header shows:
- Date: 2026-05-31
- Version: 1.1
- No mention of P1 or Phase 1

**Challenge:** SystemPromptMaster v1.1 is a **system prompt document** (deployable prompt content), not a phase documentation artifact. It was produced during the P1 timeline but it is a cross-phase artifact (used by P1, P3, P4, P5, and all subsequent phases). Requiring "P1 attribution" in a system prompt is like requiring "P0 attribution" in the PostgreSQL config. The document's purpose is to define the runtime prompt, not to attribute implementation phases. The Date field (2026-05-31) implicitly places it in the P1 timeline. This is a cosmetic observation, not a documentation gap.

**Verdict: PASS** -- Round-1 NEEDS-REVIEW is overstated. The document is not phase-specific. Zero P1 attribution is expected, not a gap.

### D2-08: ADR Cross-References

**Round-1 claim:** "All referenced ADRs exist in current docs tree."

**Verification:**
- `ls adr/ADR-004-primary-llm-model-selection.md` -- EXISTS
- `ls adr/ADR-006-sub-agent-llm-model-strategy.md` -- EXISTS
- `ls adr/ADR-014-vps-container-architecture.md` -- EXISTS
- `ls adr/ADR-028-llm-router-outage-graceful-degradation.md` -- EXISTS

ADR Index (`docs/10-governance/17-ADR_Index_v1.0.md`) line 148: "ADR-028 | ... | Implemented via migration-9router (2026-06-01, see `docs/setup-evidence/P1/migration-9router/`)"

**Verdict: PASS** -- Confirmed. All ADRs referenced by P1 evidence exist.

### D2-09: P1-021 Test Count Verification

**Round-1 claim:** "P1-021 evidence 70/70 claim is correct for the P1 snapshot."

**Verification:** STEP-P1-021/evidence.md states:
- 56 deterministic unit tests in `test_hard_stop_handler.py` (12 exact triggers + 16 semantic + 10 false positive + 2 persistence + 9 recovery + 3 audit trail + 5 guard format = confirmed 56)
- 14 GPT-5.5 model compliance tests in `test_hard_stop_model.py` (5 core + 7 semantic + 2 baseline = confirmed 14)
- Total: 70/70 PASS

CHECKLIST.md Section 3.3 line 218: "HARD STOP Protocol verified: app-level handler (56/56 unit) + GPT-5.5 model compliance (14/14) = 70/70 PASS" -- consistent.

PROGRESS.md line 132: "142/142 tests PASS (56 handler + 86 comprehensive)" -- different figure, but this is a PROGRESS.md inconsistency (see D2-02), not an evidence.md error.

**Verdict: PASS** -- Confirmed. 70/70 is correct for the P1-021 evidence snapshot.

---

## New Bugs Found by Round-2

| ID | Severity | File | Description | Notes |
|----|----------|------|-------------|-------|
| D2-R2-B01 | Low | CHECKLIST.md L232 | P1 Section 3.6 "Phase Complete Criteria" lists "All 20 steps verified" but P1 has 21 steps. Should say 21. | Off-by-one in completion criteria text. Not a functional issue. |
| D2-R2-B02 | Low | CHECKLIST.md L232-238 | P1 Phase Complete Criteria has 5 unchecked items (- [ ]) despite P1 being marked complete. Same pattern across P2, P3 sections. | Systemic: Phase Complete Criteria items are never checked off. This is consistent across all phases but creates a false impression that phase exit criteria were not met. |

---

## Missed-Surface Analysis

**Question: Did the round-1 auditor miss any P1 evidence files?**

I searched `docs/` for all references to `setup-evidence/P1` or `STEP-P1`. Found 103 files referencing P1 evidence, but the vast majority are downstream audit/research/plan files from P19/P20/P23/P24 that reference P1 as context. No additional P1 evidence files were found beyond the 36 already inventoried by round-1.

**Question: Any P1 docs references the auditor did not find?**

- `docs/10-governance/17-ADR_Index_v1.0.md` line 148: "ADR-028 | ... | Implemented via migration-9router (2026-06-01, see `docs/setup-evidence/P1/migration-9router/`)" -- Found by round-1.
- `docs/setup-evidence/P1/migration-9router/evidence.md` -- Found by round-1.
- `docs/setup-evidence/P1/p2-preconditions-resolved.md` -- Found by round-1.
- `docs/setup-evidence/P1/batch-plan-004-005.md` -- Found by round-1.
- `docs/setup-evidence/P1/batch-plan-006-007.md` -- Found by round-1.
- `docs/setup-evidence/P1/batch-plan-017-019.md` -- Found by round-1.
- `docs/setup-evidence/P1/adr-028-skip-ollama.md` -- Found by round-1.

No missed surfaces. The round-1 auditor's file inventory (36 files, 14 STEP dirs, 6 non-step files) is accurate.

---

## Bug Register Verification

| Bug ID | Round-1 Claim | Round-2 Verdict |
|--------|---------------|-----------------|
| D2-B01 | PROGRESS.md L132 "142/142" conflicts with evidence.md "70/70" | **CONFIRMED** -- Real inconsistency. PROGRESS.md says 142 (56 handler + 86 comprehensive), evidence.md says 70 (56 handler + 14 model). |
| D2-B02 | CHECKLIST.md L192-211 marks P1 complete without acknowledging drift | **REFUTED** -- CHECKLIST never claimed to track drift. This is an out-of-scope expectation imposed by the auditor. CHECKLIST is compliant. |
| D2-B03 | 7 of 21 STEP directories missing | **CONFIRMED** -- Exact count verified. 3 SKIPPED (justified), 4 undocumented gaps. |
| D2-B04 | SystemPromptMaster v1.1 zero P1 attribution | **REFUTED** -- Document is a system prompt, not phase documentation. Zero attribution is expected. |
| D2-B05 | docs/README.md no P1 entry | **CONFIRMED** -- docs/README.md has P12/P13/P16 entries but no P1 entry. Cosmetic gap. |
| D2-B06 | UTF-16LE on import-test.txt | **CONFIRMED** -- File exists, encoding defect is real but content is recoverable. |
| D2-B07 | UTF-16LE on system-prompt-loaded.txt | **CONFIRMED** -- Same as D2-B06. |
| D2-B08 | UTF-16LE on health-check.txt | **CONFIRMED** -- Same as D2-B06. |

---

## Round-1 vs Round-2 Verdict Summary

| Check ID | Round-1 Verdict | Round-2 Verdict | Changed? | Reason |
|----------|----------------|-----------------|----------|--------|
| D2-01 | NEEDS-REVIEW | PASS | YES (downgraded) | Auditor imposed out-of-scope expectation on CHECKLIST |
| D2-02 | NEEDS-REVIEW | NEEDS-REVIEW | NO | Confirmed genuine inconsistency |
| D2-03 | PASS | PASS | NO | Confirmed |
| D2-04 | NEEDS-REVIEW | NEEDS-REVIEW | NO | Confirmed (7/21 missing) |
| D2-05 | PASS | PASS | NO | Confirmed |
| D2-06 | PASS | PASS | NO | Confirmed |
| D2-07 | NEEDS-REVIEW | PASS | YES (downgraded) | System prompt is not phase documentation |
| D2-08 | PASS | PASS | NO | Confirmed |
| D2-09 | PASS | PASS | NO | Confirmed |

---

## D2 Round-2 Overall Verdict: **NEEDS-REVIEW** (unchanged)

### Changes from Round-1

- **D2-01 downgraded** from NEEDS-REVIEW to PASS: CHECKLIST.md is compliant with its scope. The absence of source-drift tracking is not a consistency failure.
- **D2-07 downgraded** from NEEDS-REVIEW to PASS: SystemPromptMaster v1.1 is a cross-phase system prompt, not P1-specific documentation.
- **D2-R2-B01 added**: Off-by-one in CHECKLIST P1 Section 3.6 ("20 steps" should be "21 steps"). Low severity.
- **D2-R2-B02 added**: P1 Phase Complete Criteria items remain unchecked despite P1 being marked complete. Low severity (systemic across all phases).

### Remaining Need-Review Items

1. **D2-02 (Medium):** PROGRESS.md "142/142" vs evidence.md "70/70" test count for P1-021. Genuine inconsistency requiring reconciliation.
2. **D2-04 (High):** 7/21 STEP directories missing. 4 directories (P1-008 through P1-011) have no standalone evidence, only inline batch-plan coverage.

### Confirmed Pass Items

D2-01 (CHECKLIST compliant), D2-03 (ADR index valid), D2-05 (UTF-16 genuine), D2-06 (configs not confused), D2-07 (system prompt is cross-phase), D2-08 (all ADRs exist), D2-09 (70/70 test count correct for P1 snapshot).

---

*Round-2 adversarial verification complete. 2 of 3 NEEDS-REVIEW findings downgraded to PASS. 1 new low-severity bug found. Original overall NEEDS-REVIEW verdict maintained due to D2-02 and D2-04.*
