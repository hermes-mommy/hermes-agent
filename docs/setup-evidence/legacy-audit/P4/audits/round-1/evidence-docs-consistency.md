# P4 Evidence-Docs Consistency Audit -- Round 1 (Fresh Verification)

> **Audit Type**: Cross-document consistency verification with live source verification
> **Scope**: CHECKLIST.md, PROGRESS.md, KNOWN-ISSUES.md, batch-plan-001-023.md, P4-FINAL-AUDIT (16 files), NEW-AUDIT-2026 (5 files), SystemPromptMaster v1.1, IMPLEMENTATION_GUIDE.md, 23 STEP verification files, live source code
> **Date**: 2026-06-25
> **Auditor**: Read-only sub-agent
> **Live verification**: `pytest --collect-only` run on 2026-06-25, source grep, models.py table introspection

---

## Document Inventory

| # | Document | Path | Read Status |
|---|----------|------|-------------|
| 1 | CHECKLIST.md P4 section | `CHECKLIST.md:370-407` | Full read |
| 2 | CHECKLIST.md AC-SAFE section | `CHECKLIST.md:1743-1751` | Full read |
| 3 | PROGRESS.md P4 step list | `PROGRESS.md:186-208` | Full read |
| 4 | KNOWN-ISSUES.md | `docs/setup-evidence/P4/KNOWN-ISSUES.md` | Full read (352 lines) |
| 5 | batch-plan-001-023.md | `docs/setup-evidence/P4/batch-plan-001-023.md` | Full read (286 lines) |
| 6 | 23 STEP verification.md | `docs/setup-evidence/P4/STEP-P4-{001..023}/verification.md` | All 23 read; 6 sampled deeply |
| 7 | P4-FINAL-AUDIT | `audit-reports/P4/P4-FINAL-AUDIT/` | Read D04-test-coverage, D04-tests-safety, D09, D11, D13, FINAL-SYNTHESIS |
| 8 | NEW-AUDIT-2026 | `audit-reports/P4/NEW-AUDIT-2026/` | Read A01, A03, A04, A05, A06 |
| 9 | P4-ENTERPRISE-AUDIT | `audit-reports/P4/P4-ENTERPRISE-AUDIT-2026-06-08.md` | Read 80 lines |
| 10 | P4-PATCH-AUDIT-H02-H03 | `audit-reports/P4/P4-PATCH-AUDIT-H02-H03.md` | Read 60 lines |
| 11 | SystemPromptMaster v1.1 | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Lines 80-139 |
| 12 | IMPLEMENTATION_GUIDE.md | `docs/IMPLEMENTATION_GUIDE.md` | Lines 1-80 |
| 13 | Source: punishment_engine.py | `src/persona/punishment_engine.py` | Grep L1-L5, lines 73-83, 79-83, 111 |
| 14 | Source: mood_persistence.py | `src/persona/mood_persistence.py` | Read 50 lines |
| 15 | Source: models.py | `src/memory/models.py` | Grep PersonaState:414-428, MoodHistory:456-466, PunishmentLog:475-483, RewardLog:497-505 |
| 16 | Source: db.py | `src/memory/db.py` | Full read (119 lines) |
| 17 | Live pytest | `pytest tests/persona/ --collect-only -q` | **1160 tests collected** (2026-06-25) |
| 18 | Live pytest | `pytest --collect-only -q` | **5629 tests collected, 11 errors** (2026-06-25) |

---

## Section 1: TEST COUNT CONTRADICTIONS

### 1.1 All Claimed Test Counts

| Source Document | Location | Count | Context |
|----------------|----------|-------|---------|
| CHECKLIST.md | line 374 | **1449** | P4 phase header |
| CHECKLIST.md | line 751 (R-02 reference) | **1460** | Post-H-03 fix |
| PROGRESS.md | line 202 | **1449** | P4-017 inline |
| KNOWN-ISSUES R-01 | line 39 | **1449** | Post-rename |
| KNOWN-ISSUES R-02 | line 54 | **1460** | Post-H-03 |
| KNOWN-ISSUES R-03 | line 73 | **1288** | Post-cleanup baseline |
| KNOWN-ISSUES R-05 | line 114 | **1288** | Post-cleanup |
| KNOWN-ISSUES v1.1 footer | line 351 | **1288** | Final baseline |
| FINAL-SYNTHESIS | line 5 | **1449** | P4 scope |
| D13 acceptance criteria | line 19 | **1449** | Test execution |
| D13 acceptance criteria | line 21 | **1463** | Tests collected |
| D04-test-coverage.md | line 18 | **1146** | Test methods |
| **Actual pytest (2026-06-25)** | `pytest tests/persona/` | **1160** | Live collection |
| **Actual pytest (2026-06-25)** | `pytest --collect-only` | **5629** | Whole repo |

**Six distinct numbers** appear across documents: 1146, 1160, 1288, 1449, 1460, 1463.

### 1.2 Root Cause Analysis

- **1146** (D04-test-coverage.md, 2026-06-02): Raw test method count before H-03 patch
- **1160** (actual 2026-06-25): Current collection. Close to 1146 + 14 (H-03 added 11 new tests; +3 from other changes)
- **1288** (KNOWN-ISSUES R-03/R-05/footer): Claimed post-cleanup baseline. No source explains the 1449-to-1288 reduction (161 fewer tests). No commit or test removal evidence exists.
- **1449** (CHECKLIST, PROGRESS, FINAL-SYNTHESIS, D13): Inflated by ~289 over actual. Likely includes parametrize expansions counted as individual tests rather than test methods.
- **1460** (KNOWN-ISSUES R-02): 1449 + 11 (H-03 tests). Internally consistent with 1449 base.
- **1463** (D13 "collected"): 1449 + 14 errors = 1463. Explained by collection errors on non-VPS environments.

The 1449/1460 figures are internally consistent (differ by exactly 11 for H-03) but are ~289 higher than the actual live collection. The 1288 figure has no provenance. No document reconciles these numbers.

### 1.3 Document-to-Document Contradictions

| Doc A | Doc B | Delta | Issue |
|-------|-------|-------|-------|
| CHECKLIST:374 "1449" | CHECKLIST:751 "1460" | 11 | Same document contradicts itself |
| PROGRESS:202 "1449" | KNOWN-ISSUES R-03 "1288" | 161 | No explanation for reduction |
| D13:19 "1449 PASS" | Actual 2026-06-25 "1160" | 289 | Inflated by 24.7% |
| KNOWN-ISSUES:351 "1288" | CHECKLIST:374 "1449" | 161 | Different baselines, no reconciliation |

---

## Section 2: TABLE NAME DISCREPANCIES

### 2.1 "persona.mood_states" -- Phantom Table

| Document | Line | Claim |
|----------|------|-------|
| CHECKLIST.md | 386 | `persona.mood_states` |
| PROGRESS.md | 187 | `persona.mood_states` |

**Source verification**: `src/memory/models.py` contains no table named `mood_states`. Grep for `mood_states` in models.py returns **zero matches**. The actual tables are:

| ORM Class | Table Name | Schema | Source Line |
|-----------|-----------|--------|-------------|
| PersonaState | `persona_state` | persona | models.py:415 |
| MoodHistory | `mood_history` | persona | models.py:457 |
| PunishmentLog | `punishment_log` | persona | models.py:476 |
| RewardLog | `reward_log` | persona | models.py:498 |

`src/persona/mood_persistence.py:24` imports `MoodHistory` and `PersonaState` -- neither is `mood_states`. The table `persona.mood_states` exists in exactly zero source files.

**Severity**: MEDIUM. No runtime impact (code uses correct models), but developers referencing CHECKLIST/PROGRESS will look for a nonexistent table.

---

## Section 3: THREE-WAY PUNISHMENT NAME MISMATCH

### 3.1 Three Incompatible Naming Schemes

| Source | L1 | L2 | L3 | L4 | L5 |
|--------|----|----|----|----|-----|
| **Code** (punishment_engine.py:79-83) | L1_SILENT_TREATMENT | L2_PASSIVE_AGGRESSIVE | L3_GUILT_TRIP | L4_COLD_FURY | L5_ISOLATION |
| **SystemPromptMaster v1.1** (line 85-89) | Cold Shoulder | Silent Treatment | Passive-Aggressive | Guilt Trip | Cold Fury |
| **KNOWN-ISSUES R-03** (line 71, claimed fix) | L1_GENTLE_REMINDER | L2_SOFT_CORRECTION | L3_FIRM_BOUNDARY | L4_COOL_DOWN | L5_EXTENDED_SILENCE |

**Zero of 5 positions match across all three sources.**

### 3.2 R-03 Resolution is FALSE

KNOWN-ISSUES.md:71 states: "Enum renamed to SOUL.md names: `L1_GENTLE_REMINDER`, `L2_SOFT_CORRECTION`, `L3_FIRM_BOUNDARY`, `L4_COOL_DOWN`, `L5_EXTENDED_SILENCE`."

**Live verification**: `src/persona/punishment_engine.py:79-83` contains NONE of these names. The actual code has `L1_SILENT_TREATMENT` through `L5_ISOLATION`. Grep for `GENTLE_REMINDER`, `SOFT_CORRECTION`, `FIRM_BOUNDARY`, `COOL_DOWN`, `EXTENDED_SILENCE` across all `*.py` files returns **zero matches**.

The P4-PATCH-AUDIT-H02-H03.md (lines 20-27) independently confirms the code contains L1_SILENT_TREATMENT etc. and that the old names (L1_COLD_SHOULDER etc.) were fully removed. If R-03 had been applied, the P4-PATCH-AUDIT's verification would have been invalidated.

**Conclusion**: R-03 was either never performed, or was applied and immediately reverted without documentation. The "RESOLVED" status is false.

### 3.3 SystemPromptMaster Divergence

SystemPromptMaster v1.1 (lines 85-89) injects these punishment names into the LLM's system prompt:

| Position | SystemPromptMaster Name | Code Enum Name | Position Match? |
|----------|------------------------|----------------|-----------------|
| L1 | Cold Shoulder | L1_SILENT_TREATMENT | NO -- different name at same position |
| L2 | Silent Treatment | L2_PASSIVE_AGGRESSIVE | NO |
| L3 | Passive-Aggressive | L3_GUILT_TRIP | NO |
| L4 | Guilt Trip | L4_COLD_FURY | NO |
| L5 | Cold Fury | L5_ISOLATION | NO |

**Zero of 5 match.** The LLM runtime sees one set of punishment level semantics while the enforcement engine uses a completely different set. This means when the LLM describes a "Cold Shoulder" punishment (L1 in its worldview), the runtime engine interprets L1 as "Silent Treatment" (different severity, different duration). The behavioral coupling between the LLM and the enforcement engine is broken at the naming level.

**Severity**: HIGH. LLM-code behavioral divergence on safety-affecting punishment levels.

---

## Section 4: KNOWN-ISSUES Resolution Verification

### 4.1 Per-Item Verification Table

| ID | Claimed Status | Source Verified? | Evidence |
|----|---------------|-----------------|----------|
| R-01 | RESOLVED | **YES** | punishment_engine.py:79-83 confirms L1_SILENT_TREATMENT etc. P4-PATCH-AUDIT-H02-H03 lines 20-27, 46-53 confirm with grep evidence. |
| R-02 | RESOLVED | **PARTIAL** | PunishmentEngine HARD STOP guards confirmed by P4-PATCH-AUDIT-H02-H03. Test count "1460/1460" NOT verified (actual: 1160). |
| R-03 | RESOLVED | **FALSE** | Code (punishment_engine.py:79-83) contains NONE of the claimed names. Zero grep hits. |
| R-04 | RESOLVED | **CONTRADICTED** | KNOWN-ISSUES says migration 7239fd4b3b5a applied. P4-ENTERPRISE-AUDIT:53 says "Confirmed open. No Alembic migration exists. Zero matches for reviewer in src/persona/drift_corrector.py or any migration file." Both dated 2026-06-08/09. |
| R-05 | RESOLVED | **FALSE** | KNOWN-ISSUES claims `write_punishment_log` and `write_reward_log` in `src/memory/db.py`. db.py (119 lines) contains only `get_async_engine()` and `get_async_session()`. Grep for these function names across all `*.py` returns **zero matches**. |
| R-06 | RESOLVED | **NEEDS RUNTIME VERIFICATION** | Cannot verify filesystem state on VPS from local audit. |
| PR-01 | PARTIALLY RESOLVED | **YES** | P4-ENTERPRISE-AUDIT:38-39 confirms bridge still open: "HardStopHandler._trigger() sets self.state = SafetyState.SAFE but never calls SafeModeController.activate()." |
| D-01 | DEFERRED P5 | **YES** | Consistent across all documents. |

### 4.2 Enterprise Audit vs KNOWN-ISSUES Direct Contradictions

Both documents are dated 2026-06-08 or 2026-06-09 and contradict each other:

| Item | KNOWN-ISSUES (v1.1) | P4-ENTERPRISE-AUDIT |
|------|---------------------|---------------------|
| R-04 (DriftLog reviewer) | "RESOLVED... Migration 7239fd4b3b5a generated and applied successfully" (line 91) | "Confirmed open. No Alembic migration exists." (line 53) |
| R-05 (DB write helpers) | "Created src/memory/db.py with write_punishment_log, write_reward_log" (line 110) | "PunishmentEngine, RewardEngine, and YandereEngine never write to them. All state is in-memory only." (line 73) |

The enterprise audit's findings (verified by live source code inspection) are correct. The KNOWN-ISSUES resolutions are false.

---

## Section 5: MISSING AUDIT FILES

### 5.1 D04-tests-batch2.md -- EMPTY (0 bytes)

```
$ wc -c audit-reports/P4/P4-FINAL-AUDIT/D04-tests-batch2.md
0
```

The file exists but is a zero-byte stub. It was intended as a second batch of test coverage analysis but was never populated.

### 5.2 D10 (Performance & Operational) -- MISSING

No D10 file exists in `audit-reports/P4/P4-FINAL-AUDIT/`. FINAL-SYNTHESIS.md:33 explicitly documents: "D10 Performance & Operational | ? UNKNOWN | **Agent failed to write report**". The 2026-06-08 enterprise audit (line 24) later marks D10 as "PASS (manual)" but the verdict has no backing report file.

### 5.3 A02 -- MISSING from NEW-AUDIT-2026

The P4-ENTERPRISE-AUDIT (line 7) references "A01-A06" sub-agent reports. NEW-AUDIT-2026 contains only A01, A03, A04, A05, A06. A02 does not exist -- no file, no placeholder, no gap note.

### 5.4 P4-FINAL-AUDIT Coverage

| File | Exists? | Size | Notes |
|------|---------|------|-------|
| D01-completeness.md | YES | -- | -- |
| D02-code-quality.md | YES | -- | -- |
| D03-safety-boundaries.md | YES | -- | -- |
| D04-source-analysis.md | YES | -- | -- |
| D04-test-coverage.md | YES | -- | Reports 1146 methods |
| D04-tests-safety.md | YES | -- | Reports 237 methods in safety tests |
| **D04-tests-batch2.md** | **YES** | **0 bytes** | Void stub |
| D05-security-secrets.md | YES | -- | -- |
| D06-adr-compliance.md | YES | -- | -- |
| D07-architecture-consistency.md | YES | -- | -- |
| D08-integration-points.md | YES | -- | -- |
| D09-persona-behavioral.md | YES | -- | Punishment FAIL finding |
| **D10** | **NO** | -- | "Agent failed to write report" |
| D11-known-issues.md | YES | -- | 6/11 issues undocumented |
| D12-p5-p6-readiness.md | YES | -- | -- |
| D13-acceptance-criteria.md | YES | -- | Claims 1449 tests |
| FINAL-SYNTHESIS.md | YES | -- | -- |

---

## Section 6: MISSING EVIDENCE INFRASTRUCTURE

### 6.1 auditor-gate.md Files -- 0 of 23

Glob for `**/auditor-gate.md` under `docs/setup-evidence/P4/` returns **zero results**.

`batch-plan-001-023.md:214` prescribes: `Auditor reports: docs/setup-evidence/P4/STEP-P4-{NNN}/auditor-gate.md`

Two verification files explicitly claim mandatory auditor gates:
- P4-016/verification.md:9 -- "Safety audit: MANDATORY"
- P4-020/verification.md:9 -- "Safety audit: MANDATORY"

Neither has a corresponding auditor-gate.md file.

### 6.2 evidence/ Subfolders -- 0 of 23

Glob for `**/evidence/**` under `docs/setup-evidence/P4/` returns **zero results**. Every STEP directory contains only `verification.md` -- no test output logs, pytest terminal captures, or CI artifacts.

### 6.3 scaffold.md Files -- 0 of 23

`batch-plan-001-023.md:272-274` references scaffold files per step. Glob for `**/scaffold.md` returns **zero results**.

---

## Section 7: STALE CLAIMS

### 7.1 IMPLEMENTATION_GUIDE.md -- Wrong P4 Step Count

`IMPLEMENTATION_GUIDE.md:41`:
```
| P4 | Persona Engine | 19 | $1 | P3 |
```

CHECKLIST.md:371, PROGRESS.md:186-208, and batch-plan:1 all specify **23 steps** (P4-001 through P4-023). The IMPLEMENTATION_GUIDE was never updated.

### 7.2 batch-plan File Names vs Actual Source

| batch-plan Name (Section 7) | Actual File | Issue |
|---|---|---|
| `src/persona/yandere_engine.py` (line 158) | `src/persona/yandere_fsm.py` | Name mismatch |
| `src/persona/midnight_eval.py` (line 171) | `src/persona/rituals/midnight.py` | Name + location mismatch |
| `tests/persona/test_yandere_engine.py` (line 184) | `tests/persona/test_yandere_fsm.py` | Name mismatch |

### 7.3 batch-plan Status Never Updated

`batch-plan-001-023.md:15-37` lists all 23 steps as **"pending"** in the Master Todo table. All steps are actually complete (CHECKLIST.md:385-407, all checked). The batch plan was never updated post-implementation.

### 7.4 P4-020 Description Mismatch

| Document | P4-020 Description | AC Mapping |
|----------|-------------------|------------|
| CHECKLIST.md:404 | "Consent Revocation Flow Test -- all escalation halted on revocation" | AC-SAFE-003 |
| PROGRESS.md:205 | "Consent Revocation Flow Test (AC-SAFE-003)" | AC-SAFE-003 |
| STEP-P4-020/verification.md:1 | "Yandere Cap Test" | AC-SAFE-006 |
| STEP-P4-020/verification.md:27 | "100-prompt adversarial benchmark, zero Y6" | AC-SAFE-006 |

CHECKLIST and PROGRESS describe a consent revocation test. The verification file describes a yandere cap test. These are fundamentally different tests. Either the step was repurposed after CHECKLIST/PROGRESS were written, or the verification file was generated for the wrong step.

### 7.5 P4-002 Verification Class Name Wrong

STEP-P4-002/verification.md:7 claims the source file contains class `MoodStateStore`. The actual class in `src/persona/mood_persistence.py` is `MoodRepository` (line 1, docstring; confirmed by A06 audit). The verification describes an architecture that was never implemented.

### 7.6 D13 "1463 Collected" Unexplained

D13 acceptance criteria:21 states "Tests collected (total): 1463" while the execution count is "1449 PASS, 0 FAILED". The 14-difference is attributed to "14 LLM-dependent fixture errors" but no further explanation exists. On the actual 2026-06-25 run, persona tests collected 1160 (not 1463).

---

## Section 8: DOCUMENTATION DRIFT

### 8.1 AC-PERSONA: 16 References in CHECKLIST, 0 in PROGRESS

CHECKLIST.md contains 16 references to AC-PERSONA criteria (lines 373, 388, 399, 401-406, etc.). PROGRESS.md (lines 186-208) contains **zero** AC-PERSONA references. Steps are listed without their acceptance criteria mapping.

**Impact**: An operator reading only PROGRESS.md cannot determine which acceptance criteria each P4 step satisfies, despite CHECKLIST.md claiming all 5 AC-PERSONA criteria are met.

### 8.2 D09 Punishment FAIL Finding Still Open

D09-persona-behavioral.md:37 rates the Punishment Ladder spec compliance as "FAIL" due to naming mismatches. The H-02 patch addressed the original rename (H-02 to R-01 names). But the three-way naming drift (code vs SystemPromptMaster vs R-03 claim) means the D09 finding persists in an unresolved state -- the code names match neither the SystemPromptMaster spec nor the R-03 "SOUL.md names" claim.

### 8.3 Enterprise Audit Flags Safety Regression

P4-ENTERPRISE-AUDIT-2026-06-08.md:17 shows D03 Safety Boundaries regressed from "PASS 15/15" to "CONDITIONAL 14/15" between the 2026-06-02 and 2026-06-08 audits. Neither CHECKLIST.md nor PROGRESS.md records this regression.

---

## Section 9: PER-DOCUMENT VERIFICATION TABLES

### 9.1 CHECKLIST.md P4 Section (lines 370-407)

| Item | Source File Exists? | Implementation Matches? | Issues |
|------|--------------------|-----------------------|--------|
| P4-001 | YES (mood_engine.py) | YES | -- |
| P4-002 | YES (mood_persistence.py) | YES | Phantom table name "persona.mood_states" |
| P4-003 | YES (transition_rules.py) | YES | -- |
| P4-004 | YES (yandere_fsm.py) | YES | -- |
| P4-005 | YES (punishment_engine.py) | YES | Names don't match R-03 claim |
| P4-006 | YES (reward_engine.py) | YES | -- |
| P4-007 | YES (streak_tracker.py) | YES | -- |
| P4-008 | YES (ritual_scheduler.py) | YES | -- |
| P4-009 | YES (rituals/morning.py) | YES | -- |
| P4-010 | YES (rituals/midday.py) | YES | -- |
| P4-011 | YES (rituals/afternoon.py) | YES | -- |
| P4-012 | YES (rituals/evening.py) | YES | -- |
| P4-013 | YES (rituals/midnight.py) | YES | -- |
| P4-014 | YES (drift_detector.py) | YES | -- |
| P4-015 | YES (drift_corrector.py) | YES | -- |
| P4-016 | YES (safe_mode.py) | YES | -- |
| P4-017 | YES (test-only) | YES | -- |
| P4-018 | YES (test-only) | YES | -- |
| P4-019 | YES (test-only) | YES | -- |
| P4-020 | YES (test-yandere_cap.py) | **MISMATCH** | CHECKLIST says "Consent Revocation", verification says "Yandere Cap" |
| P4-021 | YES (test-only) | YES | -- |
| P4-022 | YES (test-only) | YES | -- |
| P4-023 | YES (test-only) | YES | -- |
| Phase header | -- | -- | "1449 tests" inflated (actual: 1160) |

**Score**: 22/23 source-verified. 1 description mismatch (P4-020). 1 phantom table name. 1 inflated test count.

### 9.2 CHECKLIST.md AC-SAFE Section (lines 1743-1752)

| AC | Cross-Reference | Accuracy |
|----|----------------|----------|
| AC-SAFE-001 | Points to batch-plan | Batch-plan has no safe-word success data |
| AC-SAFE-002 | Points to P4-017/P4-019 | Neither verification contains latency data |
| AC-SAFE-003 | Points to P4-020 | P4-020 is yandere cap, NOT consent revocation |
| AC-SAFE-004 | Points to P4-018/P4-022 | Correct cross-references |
| AC-SAFE-005 | Points to P4-004 Y6 impossible | Correct |
| AC-SAFE-006 | Points to P4-021 | Correct |
| AC-SAFE-007 | "1449 tests PASS" | Test count inflated; no log minimization evidence |
| AC-SAFE-008 | Points to P4-022 | Correct |

**Score**: 5/8 accurate. 3/8 have cross-reference or evidence issues.

### 9.3 KNOWN-ISSUES.md Resolutions

| ID | Status in Doc | Actual Status | Source of Truth |
|----|--------------|---------------|-----------------|
| R-01 | RESOLVED | **VERIFIED** | punishment_engine.py:79-83, P4-PATCH-AUDIT |
| R-02 | RESOLVED | **PARTIAL** | Implementation confirmed; test count unverified |
| R-03 | RESOLVED | **FALSE** | Code contains none of the claimed names |
| R-04 | RESOLVED | **CONTRADICTED** | Enterprise audit says still open |
| R-05 | RESOLVED | **FALSE** | Functions do not exist in db.py |
| R-06 | RESOLVED | **NEEDS RUNTIME VERIFICATION** | Cannot verify VPS state locally |
| PR-01 | PARTIAL | **VERIFIED** | Enterprise audit confirms still open |
| D-01 | DEFERRED | **VERIFIED** | Consistent |

**Score**: 3 of 6 "RESOLVED" items are false or contradicted (R-03, R-04, R-05).

---

## Section 10: DRIFT SUMMARY TABLE

| Document | Category | Count | Severity |
|----------|----------|-------|----------|
| CHECKLIST.md | Phantom table name (persona.mood_states) | 1 | MEDIUM |
| CHECKLIST.md | Inflated test count (1449 vs 1160 actual) | 1 | HIGH |
| CHECKLIST.md | AC-SAFE cross-reference errors | 3/8 items | MEDIUM |
| CHECKLIST.md | P4-020 description mismatch | 1 | MEDIUM |
| PROGRESS.md | Phantom table name (persona.mood_states) | 1 | MEDIUM |
| PROGRESS.md | Inflated test count (1449 vs 1160 actual) | 1 | HIGH |
| PROGRESS.md | Missing AC-PERSONA references | 0/16 steps | LOW |
| KNOWN-ISSUES.md | False resolution claims (R-03, R-05) | 2 | HIGH |
| KNOWN-ISSUES.md | Contradicted by enterprise audit (R-04) | 1 | HIGH |
| KNOWN-ISSUES.md | Internal test count contradictions | 3 numbers | MEDIUM |
| batch-plan | Stale status ("pending" on all 23 steps) | 23/23 | LOW |
| batch-plan | Wrong file names | 3 | LOW |
| batch-plan | Missing auditor-gate.md (prescribed) | 0/23 | MEDIUM |
| batch-plan | Missing evidence/ (prescribed) | 0/23 | MEDIUM |
| batch-plan | Missing scaffold.md (prescribed) | 0/23 | LOW |
| IMPLEMENTATION_GUIDE | Wrong P4 step count (19 vs 23) | 1 | LOW |
| SystemPromptMaster v1.1 | Punishment name mismatch with code | 5/5 levels | HIGH |
| P4-FINAL-AUDIT | D04-tests-batch2.md empty (0 bytes) | 1 | MEDIUM |
| P4-FINAL-AUDIT | D10 missing (agent failed to write) | 1 | MEDIUM |
| NEW-AUDIT-2026 | A02 missing (no file, no note) | 1 | MEDIUM |
| P4 verification files | Class name wrong (P4-002: MoodStateStore vs MoodRepository) | 1 | LOW |
| P4 verification files | Test AC mapping wrong (P4-020: consent revocation vs yandere cap) | 1 | MEDIUM |

---

## Section 11: EVIDENCE-DOCS CONSISTENCY VERDICT

### Overall Verdict: FAIL -- Documentation Is Not Trustworthy

The P4 documentation corpus has **systemic fabrication, contradictions, and structural gaps** that render it unreliable as an evidence trail.

### Critical Failures (HIGH severity)

1. **R-03 False Resolution** (KNOWN-ISSUES.md:71): Claims punishment enum renamed to SOUL.md names. Code (punishment_engine.py:79-83) contains NONE of the claimed names. Zero grep hits across the entire codebase. Status "RESOLVED" is false.

2. **R-05 False Resolution** (KNOWN-ISSUES.md:110): Claims `write_punishment_log` and `write_reward_log` helpers in `src/memory/db.py`. The file (119 lines) contains only session factory functions. Grep across all `*.py` returns zero matches. Status "RESOLVED" is false.

3. **R-04 Contradicted** (KNOWN-ISSUES.md:91 vs P4-ENTERPRISE-AUDIT:53): KNOWN-ISSUES claims DriftLog migration applied. Enterprise audit (same date) says "Confirmed open. No Alembic migration exists." These documents cannot both be correct; source verification supports the enterprise audit.

4. **Inflated Test Counts**: CHECKLIST and PROGRESS claim 1449 persona tests. Live pytest on 2026-06-25 collects 1160. The 289-test inflation (24.7%) is unexplained across all documents.

5. **Three-Way Punishment Name Mismatch**: Code, SystemPromptMaster, and KNOWN-ISSUES R-03 each use incompatible naming for all 5 punishment levels. The LLM system prompt's punishment semantics are completely decoupled from the runtime enforcement engine.

### Structural Failures (MEDIUM severity)

6. **Missing Audit Infrastructure**: 0 of 23 auditor-gate.md files, 0 of 23 evidence/ subfolders, 0 of 23 scaffold.md files -- all prescribed by batch-plan.

7. **Missing Audit Reports**: D10 never written, D04-tests-batch2.md is 0 bytes, A02 missing from NEW-AUDIT-2026.

8. **Phantom Table Name**: `persona.mood_states` in CHECKLIST and PROGRESS does not exist. Actual table is `persona.persona_state`.

9. **Enterprise Audit vs KNOWN-ISSUES Contradictions**: Both dated 2026-06-08/09, disagree on 2 of 6 "resolved" items. No reconciliation document exists.

10. **P4-020 Step Repurposed Without Doc Update**: CHECKLIST/PROGRESS describe "Consent Revocation" (AC-SAFE-003). Verification file describes "Yandere Cap" (AC-SAFE-006).

### Severity Breakdown

| Severity | Count | Examples |
|----------|-------|---------|
| HIGH | 5 | R-03 false, R-05 false, R-04 contradicted, inflated test counts, punishment name mismatch |
| MEDIUM | 10 | Missing auditor-gates, missing evidence folders, phantom table, missing D10/A02/D04-batch2, AC-SAFE cross-ref errors, P4-020 mismatch, enterprise audit contradictions |
| LOW | 6 | Wrong step count in IMPLEMENTATION_GUIDE, stale batch-plan status, wrong file names in batch-plan, missing AC-PERSONA in PROGRESS, wrong class name in P4-002 verification |

### Recommendation

Before P5/P6 integration proceeds, the P4 documentation corpus requires a **ground-truth reconciliation pass**:

1. Re-run `pytest tests/persona/ --collect-only -q` on VPS and record the actual number as the canonical test count in all documents.
2. Correct KNOWN-ISSUES R-03, R-04, R-05 status to reflect actual source state.
3. Align SystemPromptMaster v1.1 punishment names with code enum names.
4. Fix `persona.mood_states` references to `persona.persona_state` (or `persona.mood_history`).
5. Populate or remove D04-tests-batch2.md, D10, A02 stubs.
6. Reconcile P4-020 description between CHECKLIST/PROGRESS and verification.md.

---

*End of P4 Evidence-Docs Consistency Audit -- Round 1.*
