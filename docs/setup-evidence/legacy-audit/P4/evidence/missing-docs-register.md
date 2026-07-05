# P4 Persona Engine — Missing Documentation Register

**Date:** 2026-06-25
**Audit:** Legacy Implementation Audit (read-only)

---

## Structural Gaps

### M-DOC-01: 23/23 Steps Lack evidence/ Subfolders
- **What's missing:** Every STEP-P4-001 through STEP-P4-023 directory contains only `verification.md`. No `evidence/` subfolder with raw command outputs, CI logs, screenshot captures, or test result dumps.
- **Pattern requirement:** The project pattern (visible in P2, P3, P6, P14, P19, P20, P23 evidence dirs) requires `evidence/` subfolders per step with concrete proof artifacts.
- **Impact:** P4 verification reports are summary-only. No raw evidence exists to independently verify the claimed test counts, command outputs, or runtime behavior.
- **Source:** `research/p4-repo-evidence-inventory.md` §1.2, §8.

### M-DOC-02: 23/23 Steps Lack auditor-gate.md
- **What's missing:** No STEP-P4-NNN directory contains an `auditor-gate.md` file. P4-016 and P4-017 verification.md explicitly claim "mandatory auditor gate" but no such file exists.
- **Pattern requirement:** The project pattern requires auditor-gate.md for independently verifiable steps.
- **Impact:** No independent auditor sign-off exists for any P4 step. All verification is self-reported.
- **Source:** `research/p4-repo-evidence-inventory.md` §8.

### M-DOC-03: D04-tests-batch2.md Empty (0 bytes)
- **What's missing:** `audit-reports/P4/P4-FINAL-AUDIT/D04-tests-batch2.md` exists but is empty.
- **Impact:** Missing test batch audit evidence. Part of the P4-FINAL-AUDIT series.
- **Source:** `research/p4-repo-evidence-inventory.md` §3.

### M-DOC-04: A02 Missing from NEW-AUDIT-2026
- **What's missing:** `audit-reports/P4/NEW-AUDIT-2026/` jumps from A01 to A03. A02 is missing.
- **Impact:** Incomplete audit series. Unknown what A02 covered.
- **Source:** `research/p4-repo-evidence-inventory.md` §3.

### M-DOC-05: D10 Missing from P4-FINAL-AUDIT
- **What's missing:** `audit-reports/P4/P4-FINAL-AUDIT/` jumps from D09-persona-behavioral.md to D11. D10 is missing.
- **Impact:** Incomplete audit series. Unknown what D10 covered.
- **Source:** `research/p4-repo-evidence-inventory.md` §3.

---

## Inaccurate Documentation

### M-DOC-06: P4-002 Wrong Table Name
- **What's wrong:** CHECKLIST.md line 386 and PROGRESS.md line 187 say `persona.mood_states`.
- **Correct:** Actual table is `persona.persona_state` with `state_key="current_mood"` (`src/persona/mood_persistence.py:24,107,149`, `src/memory/models.py:414`).
- **Impact:** Wrong table name propagated to two primary tracking documents. Anyone searching for `mood_states` in the schema would find nothing.
- **Source:** `research/p4-persona-source-map.md` §3 (lines 46-60), `audits/round-1/evidence-docs-consistency.md`.

### M-DOC-07: P4-001 Linear Chain Label
- **What's wrong:** CHECKLIST says "Content → Pleased → Disappointed → Angry → Silent" (linear progression).
- **Correct:** Actual FSM allows Content→Disappointed directly (skipping Pleased) and Silent→Content directly (skipping Angry). `mood_engine.py:39-45`.
- **Impact:** Misleading simplified label. The FSM is a directed graph with skip edges, not a linear chain.
- **Source:** `research/p4-persona-source-map.md` §2 (line 42).

### M-DOC-08: P4-008 Through P4-013 No Deprecation Note
- **What's wrong:** CHECKLIST/PROGRESS mark P4-008-013 `[x] ✅` with no deprecation note.
- **Correct:** All 6 modules are deprecated Phase 5, scheduled removal Phase 7. Source: ritual_scheduler.py:11-15, rituals/*.py module docstrings.
- **Impact:** 6 of 23 P4 steps are marked complete for deprecated code. The deprecation status is invisible to anyone reading the tracking docs.
- **Source:** `research/p4-persona-source-map.md` §9-14, `audits/round-1/architecture-implementation.md` §1.

### M-DOC-09: R-03 KNOWN-ISSUES Entry Factually False
- **What's wrong:** KNOWN-ISSUES.md v1.1 says R-03 RESOLVED — "Enum renamed to SOUL.md names: L1_GENTLE_REMINDER..."
- **Correct:** Source has L1_SILENT_TREATMENT through L5_ISOLATION. SOUL.md rename never applied. L5 duration still (48,72)h, not SOUL.md "Max 24h".
- **Impact:** The KNOWN-ISSUES registry contains a false claim. Future auditors relying on it would be misled.
- **Source:** `research/p4-known-issues-reconciliation.md` §R-03, `audits/round-1/evidence-docs-consistency.md`.

### M-DOC-10: R-05 KNOWN-ISSUES Claim Inaccurate
- **What's wrong:** KNOWN-ISSUES.md says R-05 RESOLVED — "Created src/memory/db.py with write_punishment_log and write_reward_log."
- **Correct:** `src/memory/db.py` does NOT contain these helper functions. Discord callbacks write directly via `get_async_session()`.
- **Impact:** KNOWN-ISSUES documents implementation details that don't exist.
- **Source:** `research/p4-known-issues-reconciliation.md` §R-05.

### M-DOC-11: 5 of 7 Verification Files Reference Wrong Test Paths
- **What's wrong:** P4-017, P4-020, P4-021, P4-022, P4-023 verification.md claim test files at `tests/persona/test_*.py`.
- **Correct:** Actual test files are at `tests/safety/test_*.py`.
- **Impact:** Verification reports pointing to non-existent files are not valid evidence.
- **Source:** `audits/round-1/architecture-implementation.md` §1 (lines 37-42).

### M-DOC-12: Test Count Contradiction
- **What's wrong:** PROGRESS.md says "1449 tests PASS" for P4-017. CHECKLIST.md line 446 says 1460. Actual persona collection is 1160. Whole-repo is 5478.
- **Impact:** Stale numbers in tracking docs. No single authoritative test count.
- **Source:** `audits/round-1/evidence-docs-consistency.md`, `audits/round-1/tests-runtime-readiness.md`.

### M-DOC-13: AC-PERSONA References Missing from PROGRESS.md
- **What's wrong:** CHECKLIST.md has 16 AC-PERSONA-001 through AC-PERSONA-005 references. PROGRESS.md has zero.
- **Impact:** Inconsistent acceptance criteria tracking. AC-PERSONA criteria exist in one doc but not the other.
- **Source:** `research/p4-repo-evidence-inventory.md` §7, `audits/round-1/evidence-docs-consistency.md`.

### M-DOC-14: P4-015 "Rollback" Overstates Functionality
- **What's wrong:** CHECKLIST says "drift correction (>10% → alert + rollback)". P4-015 verification.md says "auto-rollback".
- **Correct:** The "rollback" is record-keeping only — writes baseline hash to DriftLog. Does NOT reload or replace the system prompt. `drift_corrector.py:188-268`.
- **Impact:** Documentation claims a feature (real prompt rollback) that does not exist.
- **Source:** `research/p4-persona-source-map.md` §16 (lines 248-259).

### M-DOC-15: P4-020 Verification.md Tests Wrong Feature
- **What's wrong:** P4-020 STEP verification.md title says "Consent Revocation Flow Test" but the actual test file is `tests/safety/test_yandere_cap.py` (yandere ceiling test, not consent).
- **Impact:** The verification report for P4-020 appears to test consent but actually tests yandere ceiling. The consent claim is documented as verified but was never tested.
- **Source:** `audits/round-1/architecture-implementation.md` line 40.

---

## Missing Documentation

### M-DOC-16: No PersonaPlugin Registration Documentation
- **What's missing:** No documentation explains why `src/hermes/plugins/persona_plugin.py` exists but is not registered. The plugin has a full `register()` function and a plugin package at `hermes-config/plugins/guinevere_persona/` but is not in the `~/.hermes/plugins/` discovery path.
- **Impact:** Unknown whether registration was forgotten or intentionally deferred.
- **Source:** `research/p4-runtime-readiness-readonly.md` lines 207-214.

### M-DOC-17: No Hermes Cron Ritual Replacement Documentation
- **What's missing:** The ritual modules say "replaced by Hermes cron + PersonaPlugin." No documentation describes the Hermes cron replacement, how it differs from the APScheduler rituals, or whether the replacement is feature-equivalent.
- **Impact:** Unknown whether the Hermes cron jobs provide equivalent functionality.
- **Source:** `audits/round-1/ritual-scheduler-drift-correction.md`.

### M-DOC-18: No P4 → P24 Migration Path
- **What's missing:** No documentation describes how the split persona architecture (src/persona/ + hermes/plugins/ + hermes/safety_plugin + discord/) should be consolidated for P24 Hermes fork convergence.
- **Impact:** P24 implementers have no guidance on consolidating the persona engine.
- **Source:** `audits/round-1/downstream-p19-p24-compatibility.md`.

---

## Summary

| Category | Count |
|----------|-------|
| Structural gaps (missing files) | 5 |
| Inaccurate documentation | 10 |
| Missing documentation | 3 |
| **TOTAL** | **18** |