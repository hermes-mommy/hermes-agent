# Documentation Audit — Post ADR-035 Hermes Migration

**Date:** 2026-06-07  
**Scope:** Documentation synchronization after ADR-035 Hermes migration closure  
**Method:** Read-only audit of ADR, progress tracker, decisions log, StepPrompts, ADR index, and evidence directories/files

## Executive Summary

Overall status: **mostly synchronized, with one important documentation mismatch**.

- **ADR-035 status is correct** in the ADR frontmatter and body: **Implemented**.
- **PROGRESS.md indicates P0–P8 complete**, and Phase 5 is explicitly marked as verified/PASS in the narrative, but the phase table still shows P5 as simply `✅` rather than `✅ PASS`.
- **Decisions log contains the required ADR-035 closure entry (#005)** with the expected 2026-06-07 date and implemented-closure language.
- **StepPrompts still contains many stale/obsolete/blocking markers** tied to pre-migration Hermes/Discord assumptions; this is expected as a legacy reference file, but it is not fully clean.
- **ADR Index includes ADR-035** and matches the ADR status as **Accepted** in the index table / canonical map, which is consistent with the index reflecting accepted ADR lifecycle state while the ADR file itself is now marked Implemented.
- **Evidence directories exist and contain the expected closure/verification artifacts**.

## Findings by Requirement

### 1) ADR-035 status verification

**File read:** `adr/ADR-035-hermes-migration.md` (first 50 lines)

Observed status details:
- Frontmatter `status: "Implemented"` on line 4.
- Body section `## Status` shows `Implemented` on line 45.

**Verdict:** PASS

**Exact status string found:** `Implemented`

---

### 2) PROGRESS.md phase completeness

**File read:** `PROGRESS.md`

#### Phase table status snapshot

The phase summary table shows:
- P0: `✅` complete
- P1: `✅` complete
- P2: `✅` complete
- P3: `✅` complete
- P4: `✅` complete
- P5: `✅` complete
- P6: `✅ PASS (Remediation)`
- P7: `✅` complete
- P8: `✅` complete
- P9–P22: `⏳` pending / not started

#### Requirement check: P0 through P8 complete

- P0: complete
- P1: complete
- P2: complete
- P3: complete
- P4: complete
- P5: complete
- P6: complete
- P7: complete
- P8: complete

**Verdict:** PASS for P0–P8 completion.

#### Requirement check: P5 marked verified/PASS

Relevant evidence in `PROGRESS.md`:
- `Last Updated` line says: `2026-06-07 (Phase 5 verification complete: local deterministic T1-T10 + safety suite PASS with 205 passed; auditor gates PASS for Functional T1-T5, Technical T6-T10, and AC-SAFE...)`
- Later entries include explicit Phase 5 verification and result text in the narrative sections, including:
  - `Phase 5 verification result: PASS`

However, the **phase table row for P5** itself is still just `✅`, not `✅ PASS`.

**Verdict:** PARTIAL PASS / format mismatch

#### Phases still marked in-progress or pending

- **P9–P22** are still marked `⏳`.
- No P0–P8 phase is marked pending or in-progress in the table.

**Verdict:** PASS for the completed core phases; remaining phases are intentionally pending.

---

### 3) Decisions log entry

**File read:** `docs/10-governance/decisions-log.md`

Search result for `ADR-035` found two entries:
- **#003** on `2026-06-04`: Adopt Hermes NousResearch hybrid migration architecture; marked `Faiz (Implemented)`
- **#005** on `2026-06-07`: `ADR-035 implementation closure with accepted DR caveat`

Required closure entry details:
- Entry number: **005**
- Date: **2026-06-07**
- ADR: **ADR-035**
- Status language: closure narrative says `Hybrid Hermes Migration architecture is live`, with B10 accepted as operational DR caveat, B11 resolved, B12 resolved
- The log footer shows `Last updated: 2026-06-07`

**Verdict:** PASS

**Exact relevant entry:**
- `005 | 2026-06-07 | ADR-035 implementation closure with accepted DR caveat | ... | Faiz`

---

### 4) StepPrompts stale markers

**File read:** `stepprompts/StepPrompts.md`
**Search:** `STALE|OBSOLETE|BLOCKING`

Observed results:
- `71` matches total for stale/obsolete/blocking markers.
- Representative categories found:
  - `STALE` references to `hermes-agent` PyPI-era content now obsolete under ADR-035
  - `OBSOLETE` references to `bot.py` being superseded by the Hermes gateway
  - `BLOCKING` gates for old phase gates / safety steps
  - stale `discord.py` references and `GuinevereBot` references

This indicates StepPrompts still contains a substantial amount of pre-migration instructional content that has not been fully rewritten to remove legacy Hermes/Discord assumptions.

**Verdict:** FAIL for “clean of stale markers”; PASS only as a legacy-trace count

**Count documented:** `71`

---

### 5) ADR-Index update

**File read:** `docs/10-governance/17-ADR_Index_v1.0.md`
**Search:** `ADR-035`

Observed references:
- Canonical decision map entry:
  - `Hermes NousResearch hybrid migration architecture | [ADR-035] | Accepted`
- ADR register entry:
  - `ADR-035 | Hermes NousResearch Migration Architecture | Accepted | CRITICAL | ...`

The index clearly includes ADR-035 and shows its status as **Accepted**, which matches the ADR index’s lifecycle mapping style and the current row state.

**Verdict:** PASS

**Status string in index:** `Accepted`

**Compatibility note:** This is not contradictory to the ADR frontmatter being `Implemented`, because the index is recording the canonical decision lifecycle entry, while the ADR file itself now reflects implementation completion.

---

### 6) Cross-reference check

Checked closure and verification evidence presence:

- `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-summary.md` — exists
- `docs/setup-evidence/phase5-verification/VERIFICATION-SUMMARY.md` — exists

Additional relevant supporting files under closure evidence also exist:
- `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-plan.md`
- `docs/setup-evidence/hermes-migration/final-closure/adr-035-closure-verification.md`

**Verdict:** PASS

---

### 7) Evidence completeness

#### `docs/setup-evidence/hermes-migration/`

Directory listing shows **74 files total** in the Hermes migration evidence tree, including key closure artifacts and multiple phase subdirectories.

Expected closure files present in the final-closure directory:
- `adr-035-closure-plan.md`
- `adr-035-closure-summary.md`
- `adr-035-closure-verification.md`

#### `docs/setup-evidence/phase5-verification/`

Directory listing shows **18 files total**, including:
- `VERIFICATION-SUMMARY.md`
- `auditor-functional-T1-T5.md`
- `auditor-technical-T6-T10.md`
- `auditor-safety-AC-SAFE.md`
- `FIX-01-verification.md`
- `FIX-02-verification.md`
- `FIX-03-verification.md`
- `T1-verification.md` through `T10-verification.md`
- `phase5-verification-plan.md`

#### Missing expected evidence files

No missing files were identified from the required checks listed in the task:
- closure summary exists
- phase 5 verification summary exists
- supporting evidence directories exist with expected files

**Verdict:** PASS

## Consolidated Audit Verdicts

| Check | Verdict | Notes |
|---|---|---|
| ADR-035 status in ADR file | PASS | Frontmatter and body both say `Implemented` |
| PROGRESS P0–P8 complete | PASS | Table shows completed/verified core phases; P9–P22 remain pending as expected |
| P5 marked verified/PASS | PARTIAL PASS | Narrative says PASS, but table row is just `✅` |
| Decisions log entry #005 | PASS | Present with 2026-06-07 date |
| StepPrompts stale markers | FAIL | 71 stale/obsolete/blocking markers remain |
| ADR-Index includes ADR-035 | PASS | Status shown as `Accepted` |
| Closure summary evidence | PASS | File exists |
| Phase 5 verification summary evidence | PASS | File exists |

## Audit Conclusion

Documentation is **largely synchronized** after ADR-035 closure, but there is still one material hygiene issue: **StepPrompts contains extensive stale/obsolete/blocking references**, primarily legacy Hermes-agent and Discord bot wording. If the goal is a fully synchronized post-migration documentation set, StepPrompts should be cleaned or explicitly annotated as legacy reference material.

The only other minor issue is formatting consistency in `PROGRESS.md`: Phase 5 is described as verified/PASS in prose, but the phase table row still uses `✅` rather than `✅ PASS`.

## Final Verdict

**PASS with documentation-gap notes**

Primary status checks succeeded, but StepPrompts is not fully synchronized and PROGRESS.md could be tightened for consistency on the P5 row.
