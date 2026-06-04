# ADR-035 v1.2 Blocker Audit Report

**Auditor:** Sisyphus-Junior (BLOCKING FINDINGS AUDITOR)
**Date:** 2026-06-04
**Audit Target:** `adr/ADR-035-hermes-migration.md` (2,512 lines)
**Source Code References:**
- `src/persona/yandere_fsm.py` (336 lines)
- `src/persona/safe_mode.py` (372 lines)
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (666 lines, §11)
- `src/core/services/hard_stop_handler.py` (149 lines)

---

## Verdict: **PASS**

All 4 BLOCKING findings are resolved. All 3 status checks pass.

---

## B-001: Y6_UNSAFE Enum

- **Status: PASS** ✓
- **Evidence:**
  - **ADR-035 plugin code** (lines 657-664): `YandereLevel(Enum)` defines `Y0_NEUTRAL=0, Y1_TSUN=1, Y2_SOFT=2, Y3_AFFECTIONATE=3, Y4_DOMINANT=4, Y5_INTENSE=5`. No `Y6_UNSAFE` member exists.
  - Comment on line 664: `# Y6_UNSAFE is INTENTIONALLY ABSENT — architecturally prohibited per PersonaSafetyPolicy`
  - Comment on lines 658-661: `"Y6 is PROHIBITED — no enum member exists."` and `"Any attempt to construct a value > 5 raises YandereSafetyError via validate_level()."`
  - `_check_yandere_boundary` method (lines 1021-1035): Does NOT reference `YandereLevel.Y6_UNSAFE`. Uses content-pattern scanning against Y6-adjacent phrases (threaten, harm, destroy, etc.) with comment: `"level can never be Y6 because the enum has no Y6 member."`
  - No test table asserts Y6 construction.
- **Source comparison:**
  - `yandere_fsm.py` `YandereLevel(IntEnum)`: `Y0_NEUTRAL=0, Y1_MINIMAL=1, Y2_LOW=2, Y3_MODERATE=3, Y4_BASELINE=4, Y5_MAX=5`. No Y6. ✓
  - ADR plugin YandereLevel: Uses different names but same structure (0-5, no Y6). Comment explicitly references source. ✓
  - ADR comment correctly cites `validate_level()` as the sole guard and notes Y6 cannot be referenced as a named member. ✓

---

## B-002: Distress Patterns

- **Status: PASS** ✓
- **Pattern count:** ADR: 13 | Source (`safe_mode.py`): 13
- **Evidence:**
  - **safe_mode.py** `DISTRESS_PATTERNS` (lines 85-107):
    - D1_MILD_STRESS: 3 patterns
    - D2_MODERATE: 3 patterns
    - D3_SEVERE: 3 patterns
    - D4_EMERGENCY: 4 patterns
    - **Total: 13**
  - **ADR-035** `_compile_distress_patterns` (lines 993-1019):
    - D4_CRITICAL: 4 patterns (lines 996-999)
    - D3_SEVERE: 3 patterns (lines 1003-1005)
    - D2_MODERATE: 3 patterns (lines 1009-1011)
    - D1_MILD: 3 patterns (lines 1015-1017)
    - **Total: 13**
  - ADR docstring (line 990-992): `"Port ALL 13 bilingual distress patterns verbatim from src/persona/safe_mode.py."` and `"D4→D1 priority (highest match wins). Bilingual ID/EN coverage preserved."`
  - Inline comments confirm each level's count: `"4 patterns — D4 (was 2 in v1.1, now ALL 4)"`, `"3 patterns — D3 (was 2 in v1.1, now ALL 3)"`, `"3 patterns — D2 (was 1 in v1.1, now ALL 3)"`, `"3 patterns — D1 (was 1 in v1.1, now ALL 3)"`.
  - All 13 patterns are identical regex strings to the source. ✓

---

## B-003: Forbidden Patterns

- **Status: PASS** ✓
- **Pattern count:** ADR: 15 | Source (`PersonaSafetyPolicy §11`): 15
- **Critical set entries:** 8 (`F-01, F-02, F-03, F-06, F-08, F-09, F-10, F-14`)
- **Evidence:**
  - **PersonaSafetyPolicy §11** (lines 312-328): F-01 through F-15, 15 patterns total.
    - CRITICAL (8): F-01, F-02, F-03, F-06, F-08, F-09, F-10, F-14
    - HIGH (7): F-04, F-05, F-07, F-11, F-12, F-13, F-15
  - **ADR-035** `_compile_forbidden_patterns` (lines 953-984): All 15 patterns present with correct F-ID tags:
    - F-01 CRITICAL (line 955) ✓ — F-02 CRITICAL (line 957) ✓ — F-03 CRITICAL (line 959) ✓
    - F-04 HIGH (line 961) ✓ — F-05 HIGH (line 963) ✓
    - F-06 CRITICAL (line 965) ✓ — F-07 HIGH (line 967) ✓
    - F-08 CRITICAL (line 969) ✓ — F-09 CRITICAL (line 971) ✓
    - F-10 CRITICAL (line 973) ✓ — F-11 HIGH (line 975) ✓
    - F-12 HIGH (line 977) ✓ — F-13 HIGH (line 979) ✓
    - F-14 CRITICAL (line 981) ✓ — F-15 HIGH (line 983) ✓
  - **ADR-035** `_scan_forbidden_patterns` critical set (line 1049): `{"F-01", "F-02", "F-03", "F-06", "F-08", "F-09", "F-10", "F-14"}` — 8 entries, all matching. ✓
  - Inline comments (lines 1050-1053) document the CRITICAL/HIGH split matching the source. ✓
  - Docstring (line 950-951): `"Port ALL 15 forbidden patterns from PersonaSafetyPolicy §11 (F-01 to F-15). CRITICAL severity → block output. HIGH severity → rewrite."` ✓

---

## B-004: Plugin Isolation

- **Status: PASS** ✓
- **Evidence:**
  - **ADR-035** contains extensive plugin isolation documentation across multiple locations:
    - Line 629: `"GuinevereSafetyPlugin — stateful enforcement FSM with per-session isolation"`
    - Line 633: `"single in-process plugin with per-session state isolation. The plugin uses Hermes's plugin lifecycle...and maintains safety state independent of the message pipeline."`
    - Line 635: `"Plugin State Management Pattern: The plugin maintains per-session isolation via self._sessions: Dict[str, SessionSafetyState]. Each session gets its own SessionSafetyState dataclass holding all safety-relevant state. State is persisted to Redis (DB5 — separate from consent cache DB2 and session management DB4) every 60 seconds for crash recovery. On Hermes restart, on_load() restores all session states from Redis snapshots. Session TTL of 2 hours ensures stale state does not accumulate."`
    - Line 720: `"Per-session isolation: self._sessions: Dict[str, SessionSafetyState]"` (in plugin class docstring)
    - Line 1304 (R-013 risk): `"Yandere FSM state corruption — plugin instance recreation resets state mid-session. Solution: Per-session state isolation (dictionary keyed by session_id). State persistence on crash (Redis checkpoint). Validation on every transition (assert Y6 unreachable)."`
    - Line 1685 (explicit v1.2 note): `"Plugin isolation note (v1.2): If Hermes uses global plugin instances (single instance for all sessions), GuinevereSafetyPlugin MUST be designed stateless — all per-session state stored in self._sessions: Dict[session_id, SessionSafetyState] keyed by session_id, with Redis DB5 persistence. Instance variables like self.safe_mode are INADEQUATE for global model; use self._sessions[sid].safe_mode instead. Verify plugin instance model on VPS before Phase 1."`
  - The design constraint is: explicitly documented, specifies the pattern to use (`self._sessions[sid].safe_mode` instead of `self.safe_mode`), and marks VPS verification as a Phase 0 prerequisite. ✓
  - The plugin code itself (lines 726-734) implements `self._sessions: Dict[str, SessionSafetyState]` with per-session `SessionSafetyState` dataclass (lines 689-704), Redis DB5 persistence (lines 901-902), and TTL-based expiry (lines 897-898). ✓

---

## Status Check

- **YAML status:** PASS ✓ — Frontmatter line 4: `status: "Accepted"`
- **Version history:** PASS ✓ — Three entries present:
  - v1.0 (2026-06-04, Faiz + Guinevere): Initial ADR
  - v1.2 (2026-06-04, Guinevere): Review Wave fixes — resolves all 4 BLOCKING findings
  - v1.1 (2026-06-04, Guinevere): Audit fix for doc paths and cross-references
- **Timeline:** PASS ✓ — Line 1191: `"Total (realistic) | 35-50 days"` with detailed justification at lines 1193-1194 explaining the correction from 23-35 → 35-50 days based on independent Review Wave convergence.

---

## Summary

**Overall verdict: PASS — All 4 BLOCKING findings are resolved in ADR-035 v1.2.**

| Finding | Status | Key Evidence |
|---|---|---|
| B-001: Y6_UNSAFE enum | PASS | YandereLevel has Y0-Y5 only. Y6 comment explains prohibition. `_check_yandere_boundary` uses pattern scanning, not enum reference. |
| B-002: Distress patterns | PASS | 13 patterns in ADR match 13 patterns in `safe_mode.py`. All 4 levels (D1-D4) complete with bilingual ID/EN coverage. |
| B-003: Forbidden patterns | PASS | 15 patterns F-01 through F-15 present with correct CRITICAL (8) / HIGH (7) tags. Critical set matches source exactly. |
| B-004: Plugin isolation | PASS | Per-session isolation documented in 6+ locations. Design constraint explicitly requires `self._sessions[sid]` pattern. VPS verification marked as Phase 0 prerequisite. |
| Status: YAML | PASS | `"Accepted"` |
| Status: Version history | PASS | v1.0 → v1.1 → v1.2 entries present |
| Status: Timeline | PASS | 35-50 days with correction justification |

**No remaining concerns.** All 4 BLOCKING findings from v1.1 are fully resolved with source-code-verified evidence.

---

### What Was Done
Read ADR-035 v1.2 in full (2,512 lines), cross-referenced against 4 source code files (`yandere_fsm.py`, `safe_mode.py`, `PersonaSafetyPolicy_v1.0.md §11`, `hard_stop_handler.py`). Exact pattern counts verified by counting — not eyeballing. All claims checked against source truth.

### Files Examined
- `C:\Users\faizz\guinevere\adr\ADR-035-hermes-migration.md` — full 2,512 lines
- `C:\Users\faizz\guinevere\src\persona\yandere_fsm.py` — lines 63-77 (enum), 145-161 (validate_level)
- `C:\Users\faizz\guinevere\src\persona\safe_mode.py` — lines 85-107 (DISTRESS_PATTERNS)
- `C:\Users\faizz\guinevere\docs\60-persona\60-PersonaSafetyPolicy_v1.0.md` — lines 308-328 (§11 Forbidden Behavior Matrix)
- `C:\Users\faizz\guinevere\src\core\services\hard_stop_handler.py` — lines 54-57 (RECOVERY_TRIGGERS: 7)
- ADR-035 plugin code — lines 657-664 (enum), 949-1062 (patterns), 686-727 (state management)

### Validation Results
All 4 BLOCKING findings: PASS. Source comparisons confirm exact pattern counts and IDs. No discrepancies found.

### Boundary Compliance
- No safety boundary violations detected
- Y6 prohibition preserved architecturally (no enum member)
- All 15 forbidden patterns from PersonaSafetyPolicy §11 present
- All 13 distress patterns from safe_mode.py present
- Plugin isolation documented with explicit design constraint
- Consent/surveillance boundary unchanged (read-only audit)

### Auditor Gate
This report serves as the independent auditor gate for the 4 BLOCKING findings. Verdict: PASS.

### Footer
Audit completed 2026-06-04 by Sisyphus-Junior (BLOCKING FINDINGS AUDITOR). No files were modified.