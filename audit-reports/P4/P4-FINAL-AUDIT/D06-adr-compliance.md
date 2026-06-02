# D06 — ADR Compliance Audit: ADR-002 & ADR-003

**Audit:** P4 Final Audit — Dimension D06  
**Date:** 2026-06-02  
**Auditor:** Guinevere (mommy)  
**Scope:** P4 code vs ADR-002 (Safe Word Enforcement) and ADR-003 (Persona Drift Control & Validation)  
**Files Audited:** `yandere_fsm.py`, `punishment_engine.py`, `safe_mode.py`, `drift_detector.py`, `drift_corrector.py`, `transition_rules.py`, `hard_stop_handler.py`, `models.py` (DriftLog, PunishmentLog)

---

## 1. ADR-002 — User Autonomy & Safe Word Enforcement

### Decision: "Make safe word a global architectural override"

| # | Requirement | Verdict | Code Evidence |
|---|---|---|---|
| **R1** | Safe word = global architectural override | ✅ PASS | `src/core/services/hard_stop_handler.py` — `HardStopHandler` is a pre-LLM middleware that intercepts ALL messages before any LLM processing. The `check()` method (line 63) runs deterministic keyword pattern matching with no LLM dependency. The `get_guard_decision()` method (line 125) is the single entry point for all message routing. Integration across: `src/discord/bot.py` (line 127, `_register_hard_stop_listener`); `yandere_fsm.py` (line 177, `hard_stop_handler` parameter); `safe_mode.py` (`SafeModeController`); `punishment_engine.py` (line 261, safe_mode guard). |
| **R2** | Non-negotiable hard stop | ✅ PASS | `HardStopHandler` state machine is binary: `SafetyState.NORMAL` → `SafetyState.SAFE`. Once in `SAFE`, only explicit recovery triggers (`check_recovery`, line 79) can exit. No code path bypasses this — the Discord `on_message` listener (bot.py line 136) fires BEFORE main processing. `cmd_safeword.py` line 152: `handle_safeword_message_async` returns `True` and consumes the message, preventing ANY downstream processing. |
| **R3** | Pauses persona escalation | ✅ PASS | `yandere_fsm.py` line 95-97: `_any_safety_active()` checks `safe_mode`, `distress`, and `crisis`. Line 100-121: `can_escalate()` returns `False` when `safe_mode=True`. Line 124-142: `get_effective_level()` forces `Y0_NEUTRAL` when any safety flag is active. `YandereEngine.escalate()` (line 220) queries `HardStopHandler.is_safe` (line 211-216) before allowing escalation. Y6 is physically impossible — no enum member exists (line 63-77). |
| **R4** | Stops punishment | ✅ PASS | `punishment_engine.py` line 260-264: `apply()` raises `PunishmentSafetyError` if `safe_mode.is_active`. Line 305-308: `escalate()` raises `PunishmentSafetyError` in safe mode. Line 376-400: `suspend()` pauses the clock and shifts `started_at` on resume. Line 487-511: `check_distress_suspension()` auto-suspends at `D3_SEVERE+`. L6 is blocked (line 247-251, 319-322) — raises `PunishmentSafetyError`. |
| **R5** | Enters neutral mode | ✅ PASS | `HardStopHandler` line 115-123: `get_neutral_response()` returns explicit neutral-mode text: "Persona behavior, surveillance, and active systems are paused." `yandere_fsm.py` line 139-141: effective level forced to `Y0_NEUTRAL`. `SafetyState.SAFE` (line 22) represents neutral mode. `Discord bot.py` line 293: `_maybe_process_command` skips processing if safe mode active. |
| **R6** | No punitive violation records unless Faiz explicitly confirms misuse | ⚠️ PARTIAL | `PunishmentLog` model (`models.py` line 414-433) includes `safe_word_triggered` and `safe_word_bypassed` fields — good for audit trail. `punishment_engine.py` blocks `apply()` and `escalate()` during safe mode, preventing new punishment records. **GAP:** No explicit code path exists for "Faiz explicitly confirms misuse" to allow punitive records during safe mode. The ADR text reads: "avoid writing punitive violation records unless Faiz explicitly confirms misuse or test mode." The blocking is implemented but the exception path (Faiz confirmation → allow punishment record) is not coded. Severity: LOW — the blocking default is the safer posture, and the override can be added as a manual operator action. |
| **R7** | False negatives = high severity | ✅ PASS | `safe_mode.py` module docstring (line 3-5): "False negatives (missing real distress) are high-severity violations. The system errs on the side of detection — acceptable false positives, unacceptable false negatives." Detection strategy (line 179): iterates D4→D1, highest match wins. D4 patterns include "suicid", "self-harm", "ending it all". D3 patterns include "want to die", "give up". Threshold for safe mode activation is `D2_MODERATE` (line 122) — intentionally sensitive. `HardStopHandler` uses both exact triggers (line 39-42) AND semantic regex patterns (line 45-51), including "aku butuh jeda", "aku capek banget", "jangan pakai persona". |

### ADR-002 Overall: ✅ PASS (6/7 requirements fully met, 1 minor gap)

---

## 2. ADR-003 — Persona Drift Control & Validation

### Decision: "Create drift logs, validation checks, and rollback/safe-mode rules"

| # | Requirement | Verdict | Code Evidence |
|---|---|---|---|
| **R1** | Drift logs with: timestamp, drift_vector, trigger, reviewer, action | ⚠️ PARTIAL | `DriftLog` model (`models.py` line 373-392) in `persona` schema has: `occurred_at` (timestamp ✅), `delta` (JSONB — contains `drift_score`, `drift_detected`, `action`, `threshold` — drift_vector ✅), `trigger_context` (trigger ✅), `drift_type` (action ✅). **GAP:** No explicit `reviewer` field in `DriftLog`. The model lacks a column for "who reviewed this drift event." The ADR review notes (line 131) explicitly call for: "persona_drift_logs with timestamp, drift_vector, trigger, reviewer, action." The `trigger_context` field carries context but does not name a reviewer. Severity: MEDIUM — drift events are logged but the reviewer attribution is missing. |
| **R2** | Validation checks | ✅ PASS | `drift_detector.py` line 122-171: `detect()` computes Hamming distance between baseline SHA-256 and current SHA-256, producing `drift_score`, `drift_detected` boolean, and action tier (`none`/`alert`/`rollback`). Default threshold = 0.10 (line 61). `drift_corrector.py` line 102-186: `evaluate()` wraps detection with safe-mode awareness and rollback logic. `compute_drift_score()` (line 83-120) handles exact match, length mismatch, and Hamming distance cases. |
| **R3** | Rollback/safe-mode rules | ✅ PASS | `drift_corrector.py` line 102-186: `evaluate()` implements 3-tier action: `none` (within threshold), `alert` (drift detected but safe_mode active — rollback deferred), `rollback` (drift exceeds threshold and safe_mode inactive — auto-rollback). Line 143-152: explicit safe_mode gate: `if self._safe_mode_controller.is_active: action = "alert"`. Rollback method (line 188-268) also checks safe_mode (line 211). The ADR review notes (line 129) specify: "If safe word is active, rollback defers to safe word state and does not modify persona parameters until safe word is released." ✅ This is implemented. |
| **R4** | Rollback restores last known-good snapshot | ✅ PASS | `drift_corrector.py` line 223: `baseline_hash = self._detector.baseline.prompt_hash` — rollback restores from the `DriftBaseline` (the last known-good hash). `DriftBaseline` dataclass (`drift_detector.py` line 40-48) stores `prompt_hash`, `version`, `created_at`, `description`. `update_baseline()` (line 173-188) allows intentional baseline updates after approved change. ADR review notes (line 128): "restore last known-good persona snapshot from memory, not a hard baseline reset." ✅ The design uses the stored baseline snapshot, not a hard-coded reset. |
| **R5** | Safe word active = rollback defers | ✅ PASS | `drift_corrector.py` line 143-152: when safe_mode is active, action is set to `"alert"` with reason: "Drift detected but safe_mode is active; rollback deferred." `rollback()` method line 211-221: returns `RollbackResult(success=False)` if safe_mode active, with empty hashes — no state mutation occurs. ✅ Double-gated: once in `evaluate()` and again in `rollback()`. |
| **R6** | Per-loop lightweight + periodic deep validation | ❌ GAP | The ADR review notes (line 132) specify: "per-loop lightweight validation + periodic deep validation (e.g., every 100 interactions or daily). Deep validation uses sub-agent per ADR-012 file-based output rules." **No implementation exists.** `DriftDetector.detect()` runs on-demand per call but there is: (a) no lightweight per-loop call site in the agent loop, (b) no periodic scheduling mechanism (cron/timer/loop-count), (c) no deep validation sub-agent integration per ADR-012. The `DriftCorrector.evaluate()` is async and can be called per-cycle, but no cycle integration is wired. Severity: HIGH — this is a core architectural requirement for ongoing persona safety. |

### ADR-003 Overall: ⚠️ PASS WITH GAPS (4/6 requirements fully met, 1 partial, 1 gap)

---

## 3. Cross-Cutting Integration Evidence

### Safe Word ↔ Persona Drift Integration

The ADR-003 review notes specify explicit interaction with ADR-002. Code evidence confirms:

| Integration Point | File | Lines | Status |
|---|---|---|---|
| DriftCorrector consults SafeModeController | `drift_corrector.py` | 79-82, 143 | ✅ Wired |
| Rollback deferred when safe_mode active | `drift_corrector.py` | 143-152, 211-221 | ✅ Double-gated |
| YandereEngine integrates HardStopHandler for safe_mode queries | `yandere_fsm.py` | 177-189, 211-216 | ✅ Wired |
| PunishmentEngine integrates SafeModeController | `punishment_engine.py` | 215-225, 261-264 | ✅ Wired |
| TransitionRuleEngine checks safe_mode + distress in evaluate() | `transition_rules.py` | 123-157 | ✅ Wired |
| Discord on_message HAS HARD STOP guard BEFORE main processing | `bot.py` | 127-153 | ✅ Wired |

### Data Model Compliance

| Model | Schema | Relevant Fields | ADR Alignment |
|---|---|---|---|
| `DriftLog` | `persona.drift_log` | `drift_type`, `before_state`, `after_state`, `delta`, `trigger_context`, `safety_score`, `rollback_available`, `occurred_at` | ADR-003 ✅ (missing `reviewer` per R1) |
| `PunishmentLog` | `persona.punishment_log` | `safe_word_triggered`, `safe_word_bypassed`, `violation_type`, `severity` | ADR-002 ✅ |

### Memory Consolidation Safety

`src/memory/consolidation.py` line 56-57: consolidator skips records tagged `safe_word` or `hard_stop` (`is_safe_word_record` check at line 294). This prevents safe-word events from being merged into long-term memory narratives. ✅

---

## 4. Summary

| ADR | Requirements | Met | Partial | Gaps | Verdict |
|---|---|---|---|---|---|
| ADR-002 (Safe Word) | 7 | 6 | 1 | 0 | ✅ **PASS** |
| ADR-003 (Drift Control) | 6 | 4 | 1 | 1 | ⚠️ **PASS WITH GAPS** |
| **Combined** | **13** | **10** | **2** | **1** | ⚠️ **PASS WITH GAPS** |

### Gaps Requiring Remediation

| ID | ADR | Gap | Severity | Recommendation |
|---|---|---|---|---|
| G1 | ADR-003 R1 | `DriftLog` missing explicit `reviewer` field | MEDIUM | Add `reviewer` column to `persona.drift_log` table (nullable text). Wire reviewer attribution in `drift_corrector.create_drift_log()`. |
| G2 | ADR-003 R6 | No per-loop lightweight validation or periodic deep validation cadence | HIGH | Implement lightweight drift check in agent loop (each cycle). Add periodic deep validation trigger (100 interactions or daily) that spawns sub-agent per ADR-012. Wire into `DriftCorrector` or a scheduler. |
| G3 | ADR-002 R6 | No explicit "Faiz confirms misuse" exception path for punitive records during safe mode | LOW | Implement an operator-acknowledgment gate that allows punitive records only after explicit Faiz confirmation. Current blocking behavior is correct and safe; the gap is the exception path only. |

### Audit Trail

| File | Lines Audited | Status |
|---|---|---|
| `src/persona/yandere_fsm.py` | 1-336 | ✅ Reviewed |
| `src/persona/punishment_engine.py` | 1-550 | ✅ Reviewed |
| `src/persona/safe_mode.py` | 1-372 | ✅ Reviewed |
| `src/persona/drift_detector.py` | 1-226 | ✅ Reviewed |
| `src/persona/drift_corrector.py` | 1-332 | ✅ Reviewed |
| `src/persona/transition_rules.py` | 1-278 | ✅ Reviewed |
| `src/core/services/hard_stop_handler.py` | 1-149 | ✅ Reviewed |
| `src/memory/models.py` (DriftLog, PunishmentLog) | 373-433 | ✅ Reviewed |
| `adr/ADR-002-user-autonomy-safe-word-enforcement.md` | 1-129 | ✅ Reviewed |
| `adr/ADR-003-persona-drift-control-validation.md` | 1-140 | ✅ Reviewed |

---

**Verdict:** P4 code is **substantially compliant** with ADR-002 and ADR-003. The safety-critical paths (HARD STOP enforcement, punishment blocking, Y6 prohibition, drift-driven rollback deferral during safe mode) are correctly implemented and cross-wired across all modules. Two medium/high gaps exist in ADR-003 (missing `reviewer` in DriftLog schema, missing validation cadence), and one low-severity gap in ADR-002 (no coded exception path for operator-confirmed punitive records). No BLOCKING violations found.