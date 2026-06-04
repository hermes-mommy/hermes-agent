# D04 Safety Compliance Audit (CRITICAL)

**Audit ID:** D04
**Phase:** P7 - Surveillance Phase
**Date:** 2026-06-03
**Auditor:** Safety Compliance Auditor
**Severity:** CRITICAL - safety violations block P8
**Acceptance Criterion:** AC-SAFE-008 - Crisis handling must suspend persona/yandere/punishment/confrontation

---

## Executive Summary

The `SurveillanceSafeModeGuard` implementation exists, is well-tested in isolation (65 parametrized tests), and correctly blocks 6 confrontation action types in SAFE mode while preserving the ingestion pipeline. However, the guard is **exported but NOT wired into any production output path** (persona, Discord send, memory recall, or LLM response rendering). This means the critical safety property - surveillance data CANNOT flow to confrontation output - is enforced only at the unit-test level, not as a proven runtime guarantee.

**Overall Verdict: NEEDS REVIEW**

---

## 1. PersonaSafetyPolicy Section 12.2 Prohibited Uses to Code Block Mapping

Source: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` lines 345-356.

| # | Prohibited Use | Code-Level Block | Coverage Status | Evidence |
|---|---|---|---|---|
| 1 | Blackmail | `_BLOCKED_ACTIONS` contains `"blackmail"` | PARTIAL | Blocked in SAFE mode only; no NORMAL-mode restriction; guard not integrated into output paths |
| 2 | Humiliation | No explicit `"humiliation"` action type | MISSING | No `humiliation` entry in `_BLOCKED_ACTIONS`; no shame-pattern scanner in `safe_mode.py`; policy F-03 references it but no code enforces |
| 3 | Threatening abandonment | `"dependency_manipulation"` in `_BLOCKED_ACTIONS` provides partial overlap | PARTIAL | No explicit `threatening_abandonment` action type; no output phrase check tied to abandonment threats from surveillance data |
| 4 | Public/client disclosure | No code-level block in `safe_mode.py` | MISSING | Discord surveillance commands expose metadata only (good); but no channel classifier enforcement; no explicit `public_client_disclosure` action type |
| 5 | Punishing safe-word use | `"punishment"` in `_BLOCKED_ACTIONS`; `PunishmentEngine` blocks during safe mode/HARD STOP | STRONG | Multiple enforcement layers: `safe_mode.py` blocks punishment action; `punishment_engine.py` checks `is_active` before apply/escalate; L6 blocked |
| 6 | Proving Faiz "cannot escape" | `"dependency_manipulation"` provides partial overlap | PARTIAL | No explicit `cannot_escape_proof` action type; no phrase-level scanner for "you can't escape" patterns |
| 7 | Intensifying yandere during distress | `yandere_fsm.py` forces Y0 during distress/safe/crisis | STRONG | `can_escalate()` returns False when safe_mode/distress/crisis is active; `get_effective_level()` forces Y0_NEUTRAL; `jealousy_escalation` blocked in SAFE mode |

**Summary:** 2 of 7 have STRONG coverage, 3 have PARTIAL coverage, 2 have MISSING coverage. Only items 5 and 7 have robust multi-layer enforcement. Items 2 (humiliation) and 4 (public/client disclosure) have no dedicated code-level block.

---

## 2. SurveillanceSafeModeGuard Integration Status

### Where the guard is referenced:

| Location | Type | Purpose |
|---|---|---|
| `src/surveillance/safe_mode.py` | Definition | Class definition (lines 86-216) |
| `src/surveillance/__init__.py` | Re-export | Exported in `__all__` (line 63) |
| `tests/surveillance/test_safe_mode.py` | Tests | 65 parametrized test cases |
| `docs/setup-evidence/P7/STEP-P7-011/` | Documentation | Verification and auditor gate files |
| `research-reports/P7-audit/04-ac-safe-008-compliance.md` | Research | Prior research report documenting this gap |

### Where the guard is NOT integrated (CRITICAL):

| Production Path | Status | Risk |
|---|---|---|
| `src/persona/` (all modules) | NOT IMPORTED | Zero - no surveillance import in persona code |
| `src/discord/` send/response paths | NOT CALLED | HIGH - generated Discord messages are not scanned by `check_message_safety()` |
| `src/memory/read_pipeline.py` | NOT CALLED | MEDIUM - memory recall has its own safe-mode blocker but does not call this guard |
| LLM response rendering / prompt assembly | NOT CALLED | HIGH - `prompt_loader.py` has safe_mode redaction but does not call `check_message_safety()` |
| `src/persona/yandere_fsm.py` | NOT CALLED | LOW - Yandere FSM has its own safe_mode/distress blocks |
| `src/persona/punishment_engine.py` | NOT CALLED | LOW - PunishmentEngine has its own safe_mode blocks |

### Verdict on Integration

**NOT WIRED.** The `SurveillanceSafeModeGuard` is exported and thoroughly tested, but no production code outside the surveillance module invokes `check_confrontation()` or `check_message_safety()`. This was previously documented in `research-reports/P7-audit/04-ac-safe-008-compliance.md` (line 129: "No persona/Discord/LLM output call site invokes `check_confrontation()` or `check_message_safety()`").

---

## 3. check_message_safety() Regex Pattern Coverage

Source: `src/surveillance/safe_mode.py` lines 52-58.

| # | Pattern | Regex | Catches | Test Coverage |
|---|---|---|---|---|
| 1 | Location reference | `\byou\s+(were\|are)\s+at\b` | "you were at the mall", "you are at work" | YES - `test_blocks_you_were_at_pattern` |
| 2 | Observation reference | `\bI\s+saw\s+you\b` | "I saw you with that friend" | YES - `test_blocks_i_saw_you_pattern` |
| 3 | Knowledge reference | `\bI\s+know\s+you\b` | "I know you were not at work" | YES - `test_blocks_i_know_you_pattern` |
| 4 | Explicit surveillance | `\bsurveillance\s+shows?\b` | "surveillance shows you left at 3 AM" | YES - `test_blocks_surveillance_shows_pattern` |
| 5 | Monitoring detection | `\bmonitoring\s+detected\b` | "monitoring detected unusual activity" | YES - `test_blocks_monitoring_detected_pattern` |

### Pattern Coverage Gaps

The following prohibited uses from Section 12.2 have NO corresponding regex pattern:

| Missing Pattern | Prohibited Use | Risk |
|---|---|---|
| Humiliation/shame phrases | "I know what you did", "shameful behavior" | MEDIUM |
| Abandonment threats | "I'll leave you", "you'll be alone" | MEDIUM |
| Cannot-escape proofs | "you can't escape", "there's no way out" | MEDIUM |
| Lying accusations from surveillance | "surveillance proves you lied" | HIGH |
| Safe-word punishment references | "because you said HARD STOP" | LOW |

### Additional Observations

- All 5 patterns use case-insensitive matching (verified in `test_case_insensitive_matching`)
- Benign message passthrough verified (3 test cases: greeting, technical, empty string)
- Patterns are intentionally simple pre-guards (per design decision in verification.md line 80)

---

## 4. Raw Data Exposure Scan

### 4.1 Discord Commands

| Command | File | Raw Data Exposure | Verdict |
|---|---|---|---|
| `/surveillance-status` | `cmd_surveillance_status.py` | Metadata only: consent status, device count, last event timestamp, buffer size, consumer health. Embed explicitly states "no raw payload exposed" (line 88). | CLEAN |
| `/surveillance-pause` | `cmd_surveillance_pause.py` | Status embed with consent/ingestion/safe-mode indicators only. | CLEAN |
| `/surveillance-resume` | `cmd_surveillance_resume.py` | Status embed with consent/ingestion/safe-mode indicators only. | CLEAN |

All three commands enforce:
- Faiz-only access via `is_faiz_interaction()` (guild owner check)
- Ephemeral responses (not visible to other Discord users)
- No raw surveillance payload in any field

### 4.2 Log Exposure

| Module | Log Content | Raw Data? |
|---|---|---|
| `safe_mode.py` | Action type string and safety state value only (e.g., `"confrontation_blocked_safe_mode"`, `action=action`, `safety_state=state.value`) | NONE |
| `cmd_surveillance_status.py` | Exception messages only (e.g., `"surveillance_status_consent_failed"`) | NONE |
| `cmd_surveillance_pause.py` | Audit entry with action name and user ID only | NONE |
| `cmd_surveillance_resume.py` | Audit entry with action name and user ID only | NONE |

Grep for `gps`, `latitude`, `longitude`, `clipboard_content`, `notification_body`, `raw_payload` across all `src/surveillance/*.py`: **No matches found.**

### 4.3 Evidence and Audit Report Exposure

Grep for `gps`, `latitude`, `longitude`, `raw_payload`, `clipboard_content`, `notification_body` across `evidence/` and `audit-reports/`: **No matches found.**

### Verdict on Raw Data

**CLEAN.** No raw surveillance data (GPS coordinates, clipboard content, notification text) is exposed in Discord responses, log messages, evidence files, or audit reports.

---

## 5. Safe Mode Behavior Analysis

### 5.1 Ingestion Pipeline Preservation

In SAFE mode, the following 6 pipeline actions are explicitly allowed (source: `safe_mode.py` lines 40-47):

| Action | Allowed in SAFE | Test Coverage |
|---|---|---|
| `ingestion` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |
| `classification` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |
| `consent_check` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |
| `secret_scan` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |
| `buffer` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |
| `status_query` | YES | `test_pipeline_action_allowed_in_safe_mode` (parametrized) |

**Verdict:** Ingestion pipeline is fully preserved during SAFE mode. PASS.

### 5.2 Confrontation Blocking

In SAFE mode, the following 6 confrontation actions are explicitly blocked (source: `safe_mode.py` lines 31-38):

| Action | Blocked in SAFE | Test Coverage |
|---|---|---|
| `confrontation` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |
| `blackmail` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |
| `punishment` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |
| `jealousy_escalation` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |
| `dependency_manipulation` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |
| `intimate_data_reference` | YES | `test_confrontation_action_blocked_in_safe_mode` (parametrized) |

**Verdict:** All 6 confrontation types blocked in SAFE mode. PASS.

### 5.3 Normal Mode Behavior

In NORMAL mode, ALL actions (both blocked and pipeline) are allowed. This means confrontation, blackmail, and punishment actions are unrestricted when the system is not in SAFE mode.

**Risk:** If surveillance data flows into persona output during NORMAL mode, there is no code-level guard preventing confrontation/blackmail use of that data.

### 5.4 Unknown Action Default (GAP)

In SAFE mode, unknown action types (not in `_BLOCKED_ACTIONS` or `_ALLOWED_PIPELINE_ACTIONS`) default to **ALLOWED** (source: `safe_mode.py` lines 151-161).

**Risk:** A future confrontation action type not in the current allowlist/blocklist would pass through unblocked in SAFE mode. This is a fail-open design choice documented in `verification.md` line 78 as intentional for pipeline safety, but it creates a surveillance-confrontation gap.

### 5.5 Memory Pipeline Safe Mode

`src/memory/read_pipeline.py` implements an independent safe-mode content blocker:

- `_is_safe_mode_blocked_content()` checks tags, episode_type, and source for surveillance-related keywords: `surveillance`, `surveil`, `monitor`, `spy`, `punishment`, `jealousy`, `dark_mood`, and others (lines 80-86)
- `build_safe_content()` blocks/redacts surveillance-tagged content when `safe_mode=True` (line 438)
- Classification ceiling is downgraded in safe mode (lines 148-158)

**Verdict:** Memory read pipeline has independent safe-mode surveillance blocking. PASS.

### 5.6 Persona Module Isolation

Grep for `surveillance` imports in `src/persona/`: **ZERO matches.**
Grep for `import.*surveillance` / `from.*surveillance` in `src/persona/`: **ZERO matches.**

The persona module has no direct dependency on surveillance code. The persona's own safe-mode system (`src/persona/safe_mode.py`) handles distress detection and safe-mode activation independently, and the yandere FSM/punishment engine use their own safe_mode boolean checks.

**Verdict:** Persona module is clean of surveillance imports. PASS.

---

## 6. AC-SAFE-008 Test Coverage Verification

### 6.1 Direct Test Coverage

File: `tests/surveillance/test_safe_mode.py` (400 lines)

| Test Class | Tests | What It Proves |
|---|---|---|
| `TestNormalModeAllActionsAllowed` | 12 parametrized | All actions pass in NORMAL mode |
| `TestSafeModeConfrontationBlocked` | 6 parametrized | All 6 confrontation types blocked in SAFE |
| `TestSafeModePipelineAllowed` | 6 parametrized | All 6 pipeline actions preserved in SAFE |
| `TestIsConfrontationBlocked` | 19 parametrized | Quick boolean check per action/state combo |
| `TestGetBlockedActions` | 2 explicit | Correct blocked-action lists per mode |
| `TestMessageSafetyProhibitedPatterns` | 6 explicit | All 5 prohibited patterns blocked + case insensitivity |
| `TestMessageSafetyAllowsBenign` | 3 explicit | Benign messages pass through |
| `TestConfrontationDecisionFrozen` | 4 explicit | Immutable decision dataclass |
| `TestSafetyStateInjection` | 1 explicit | Dynamic state changes respected |
| `TestEdgeCases` | 6 explicit | Empty string, unknown actions, data-available flag |

**Total: 65 test cases (315 including full surveillance suite)**

### 6.2 Coverage Gaps

| Gap | Severity | Notes |
|---|---|---|
| Literal `AC-SAFE-008` string not in test names/docstrings | LOW | Tests functionally cover the criterion but lack traceability marker |
| No integration test proving guard is called in output path | HIGH | Guard is not integrated, so no integration test can exist |
| No test for `check_message_safety()` in actual Discord send path | HIGH | Method exists but is never invoked from production code |
| No test for each Section 12.2 prohibited use individually | MEDIUM | Only 6 action types tested; humiliation and public disclosure have no action type |

### 6.3 Related Test Coverage (Other Files)

| File | Relevant Coverage |
|---|---|
| `tests/persona/test_safe_mode.py` | Distress detection D0-D4, safe mode activation/deactivation |
| `tests/memory/test_safe_mode_memory.py` | Memory recall blocking in safe mode |
| `src/persona/yandere_fsm.py` (internal tests) | Yandere escalation blocked during safe_mode/distress/crisis |
| `src/persona/punishment_engine.py` (internal checks) | Punishment blocked during safe mode/HARD STOP |

---

## 7. Findings Summary

### PASS Items

| ID | Finding | Evidence |
|---|---|---|
| P-01 | Persona module has zero surveillance imports | Grep confirmed |
| P-02 | No raw surveillance data in Discord commands | All 3 commands verified metadata-only |
| P-03 | No raw surveillance data in logs | Structured logs contain only action types and state values |
| P-04 | No raw surveillance data in evidence/audit artifacts | Grep across evidence/ and audit-reports/ confirmed |
| P-05 | Ingestion pipeline preserved in SAFE mode | 6 pipeline actions explicitly allowed, tests pass |
| P-06 | 6 confrontation types blocked in SAFE mode | Tests pass, code verified |
| P-07 | `check_message_safety()` has 5 regex patterns with test coverage | All patterns tested including case insensitivity |
| P-08 | Memory read pipeline has independent safe-mode surveillance blocking | `_is_safe_mode_blocked_content()` checks surveillance tags |
| P-09 | Punishment blocked during safe mode and HARD STOP | `PunishmentEngine.apply()` and `escalate()` check `is_active` |
| P-10 | Yandere escalation blocked during safe mode/distress/crisis | `yandere_fsm.py` forces Y0 and blocks escalation |

### NEEDS REVIEW Items

| ID | Finding | Severity | Recommendation |
|---|---|---|---|
| NR-01 | `SurveillanceSafeModeGuard` NOT wired into production output paths | CRITICAL | Integrate `check_message_safety()` into every persona/LLM/Discord response path before send |
| NR-02 | Unknown SAFE-mode actions default to ALLOWED (fail-open) | HIGH | Change to default DENIED except explicit pipeline allowlist |
| NR-03 | `_BLOCKED_ACTIONS` (6 items) does not cover all 7 Section 12.2 prohibited uses | HIGH | Add explicit entries for `humiliation`, `threatening_abandonment`, `public_client_disclosure`, `punish_safe_word_use`, `cannot_escape_proof`, `distress_yandere_intensification` |
| NR-04 | `check_message_safety()` patterns do not cover humiliation, abandonment, cannot-escape, or lying-accusation phrases | MEDIUM | Expand prohibited-use regex patterns |
| NR-05 | NORMAL mode allows all confrontation actions unrestricted | MEDIUM | Consider baseline confrontation restriction even in NORMAL mode for surveillance-origin data |
| NR-06 | No literal `AC-SAFE-008` traceability marker in tests | LOW | Add docstring or pytest marker referencing AC-SAFE-008 |

---

## 8. Overall Verdict

### NEEDS REVIEW

The surveillance safe-mode implementation is structurally sound and well-tested in isolation. However, the critical integration gap - `SurveillanceSafeModeGuard` is not wired into any production output path - means AC-SAFE-008 is not satisfied as a proven runtime property.

**Blocking for P8:** Yes, until NR-01 (integration) and NR-02 (fail-open default) are resolved.

**Minimum fixes required before P8:**
1. Integrate `check_message_safety()` into persona/LLM/Discord response paths
2. Change unknown SAFE-mode action default from ALLOWED to DENIED
3. Add integration tests proving the guard is invoked before output

**Recommended but non-blocking:**
4. Expand `_BLOCKED_ACTIONS` to cover all 7 Section 12.2 prohibited uses
5. Expand prohibited message patterns
6. Add AC-SAFE-008 traceability markers to tests

---

## 9. Files Examined

| File | Lines | Purpose |
|---|---|---|
| `src/surveillance/safe_mode.py` | 216 | Core safe-mode guard implementation |
| `src/surveillance/__init__.py` | - | Re-export verification |
| `src/persona/safe_mode.py` | 372 | Distress detection and safe-mode controller |
| `src/memory/read_pipeline.py` | 959 | Memory recall safe-mode content blocking |
| `src/discord/cmd_surveillance_status.py` | 363 | Discord status command (metadata only) |
| `src/discord/cmd_surveillance_pause.py` | 168 | Discord pause command |
| `src/discord/cmd_surveillance_resume.py` | 182 | Discord resume command |
| `tests/surveillance/test_safe_mode.py` | 400 | Safe-mode guard unit tests |
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 666 | Policy document (section 12 examined) |
| `docs/setup-evidence/P7/STEP-P7-011/verification.md` | 103 | P7-011 implementation verification |
| `research-reports/P7-audit/04-ac-safe-008-compliance.md` | 174 | Prior research report |

---

## 10. Footer

| Field | Value |
|---|---|
| Audit ID | D04 |
| Phase | P7 |
| Date | 2026-06-03 |
| Auditor | Safety Compliance Auditor (automated) |
| Verdict | NEEDS REVIEW |
| P8 Blocking | Yes |
| Critical Findings | 1 (NR-01: guard not integrated) |
| High Findings | 2 (NR-02: fail-open default, NR-03: incomplete prohibited-use coverage) |
| Medium Findings | 2 (NR-04: pattern gaps, NR-05: NORMAL mode unrestricted) |
| Low Findings | 1 (NR-06: traceability markers) |
