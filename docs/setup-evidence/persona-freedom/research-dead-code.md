# Dead Code Research — Persona Freedom Cleanup

**Date:** 2026-06-09  
**Scope:** `src/persona/` dan `src/core/services/`  
**Metodologi:** Baca file → grep import → grep referensi class/function di `src/` dan `tests/`  
**Aturan dead code:** File dianggap dead jika tidak ada file lain di `src/` (selain dirinya sendiri dan `src/persona/__init__.py` sebagai re-exporter) yang mengimpor atau mereferensikan class/function-nya secara langsung dan fungsional.

---

## 1. `src/persona/safe_mode.py`

**Path:** `src/persona/safe_mode.py`

**Classes/Functions:**
- `SafeModeError` (exception)
- `DistressDetectionError` (exception)
- `DistressLevel` (IntEnum)
- `DistressSignal` (dataclass, frozen)
- `SafeModeState` (dataclass, mutable)
- `DISTRESS_PATTERNS` (constant)
- `DISTRESS_RESPONSES` (constant)
- `SAFE_MODE_THRESHOLD` (constant)
- `DistressDetector` (class)
- `SafeModeController` (class)

**Imported By (src/ — non-deprecated, non-self):**
- `src/persona/__init__.py` — re-export ke public API
- `src/persona/drift_corrector.py` — import `SafeModeController`
- `src/persona/punishment_engine.py` — import `DistressLevel`, `SafeModeController`
- `src/discord/hermes_conversational.py` — lazy import `DistressDetector`, `SafeModeController`, `DistressLevel`, `DistressSignal`
- `src/hermes/safety_plugin.py` — lazy import `DistressDetector`, `SafeModeController`
- `src/_deprecated/hermes-migration-phase-7/conversational_handler.py` — import (file deprecated)

**Referenced By (tests/):**
- `tests/persona/test_safe_mode.py` — comprehensive unit tests
- `tests/persona/test_distress_detection.py` — unit tests
- `tests/persona/test_punishment_engine.py` — integration tests
- `tests/persona/test_drift_corrector.py` — fixture
- `tests/safety/test_distress_protocol_e2e.py` — e2e tests
- `tests/safety/test_punishment_overflow.py` — integration tests
- `tests/phase7/test_T7_distress_protocol.py` — phase tests

**Verdict:** `keep`

**Alasan:** Dipakai aktif oleh `punishment_engine.py` (dependency hard), `hermes/safety_plugin.py` (production safety gate), dan `discord/hermes_conversational.py` (runtime distress detection). Ini adalah safety-critical module.

---

## 2. `src/persona/drift_corrector.py`

**Path:** `src/persona/drift_corrector.py`

**Classes/Functions:**
- `DRIFT_THRESHOLD` (constant)
- `DriftCorrectionError` (exception)
- `RollbackError` (exception)
- `DriftCorrectionResult` (dataclass, frozen)
- `RollbackResult` (dataclass, frozen)
- `DriftCorrector` (class — async evaluate, rollback, create_drift_log)

**Imported By (src/ — non-self):**
- `src/persona/__init__.py` — re-export saja

**Tidak ada file src/ lain yang import `drift_corrector` atau menggunakan `DriftCorrector` secara langsung.**  
Search exhaustive: `grep -rn "DriftCorrector\|DriftCorrectionResult\|drift_corrector" src/ | grep -v __init__ | grep -v drift_corrector.py` → **0 hasil**.

**Referenced By (tests/):**
- `tests/persona/test_drift_corrector.py` — comprehensive unit tests
- `tests/persona/test_persona_e2e.py` — e2e tests (loaded via dynamic import)

**Verdict:** `safe_to_delete`

**Alasan:** Tidak ada file `src/` yang mengimpor atau menggunakan `DriftCorrector` secara runtime, selain `__init__.py` sebagai re-exporter pasif. `safety_plugin.py` menggunakan `drift_detector.py` langsung — bukan `drift_corrector`. Module ini adalah auto-rollback layer yang tidak pernah di-wire ke pipeline aktif manapun. Tests ada, tapi tests tidak membuat module jadi "live".

**Catatan:** Jika dihapus, juga perlu hapus entry dari `src/persona/__init__.py` (baris 20-26 dan entries di `__all__`).

---

## 3. `src/persona/transition_rules.py`

**Path:** `src/persona/transition_rules.py`

**Classes/Functions:**
- `TransitionRulesError` (exception)
- `CooldownActiveError` (exception)
- `InvalidTransitionError` (exception)
- `VALID_TRANSITIONS` (constant)
- `ALL_MOODS` (constant)
- `TransitionContext` (dataclass)
- `TransitionDecision` (dataclass)
- `TransitionRuleEngine` (class — evaluate, remaining_cooldown, should_use_llm_evaluation, evaluate_with_llm, get_state_snapshot, get_valid_transitions)

**Imported By (src/ — non-self):**
- `src/persona/__init__.py` — re-export saja

**Tidak ada file src/ lain yang import `transition_rules` atau menggunakan `TransitionRuleEngine` / `TransitionContext` secara langsung.**  
Search exhaustive: `grep -rn "TransitionRuleEngine\|TransitionContext\|TransitionDecision\|CooldownActiveError" src/ | grep -v __init__ | grep -v transition_rules.py` → **0 hasil**.

**Referenced By (tests/):**
- `tests/persona/test_transition_rules.py` — comprehensive unit tests
- `tests/persona/test_persona_e2e.py` — e2e tests (loaded via dynamic import)
- `tests/phase7/test_T6_persona_fsm.py` — phase tests
- `tests/safety/test_consent_revocation.py` — safety integration tests

**Verdict:** `safe_to_delete`

**Alasan:** Tidak ada file `src/` yang menggunakan `TransitionRuleEngine` di runtime. `mood_engine.py` memiliki sendiri logika transisi (`TRANSITIONS`, `can_transition`). `transition_rules.py` adalah implementasi duplikat/alternatif yang tidak pernah di-wire ke PersonaPlugin atau pipeline aktif. Hanya `__init__.py` yang re-export, tidak ada caller sebenarnya.

**Catatan:** Jika dihapus, juga perlu hapus entry dari `src/persona/__init__.py` (baris 112-121 dan entries di `__all__`).

---

## 4. `src/core/services/hard_stop_handler.py`

**Path:** `src/core/services/hard_stop_handler.py`

**Classes/Functions:**
- `SafetyState` (Enum — NORMAL, SAFE)
- `HardStopEvent` (dataclass)
- `HardStopHandler` (dataclass/class — check, check_recovery, _trigger, get_neutral_response, get_guard_decision)

**Imported By (src/ — non-self):**
- `src/discord/cmd_safeword.py` — lazy import `HardStopHandler` (baris 38, 299)
- `src/surveillance/windows_consent.py` — import `SafetyState` (baris 63)
- `src/surveillance/safe_mode.py` — import `SafetyState` (baris 23)
- `src/hermes_plugins/commands_high/safeword.py` — lazy import `HardStopHandler` (baris 14, 50)
- `src/hermes/safety_plugin.py` — lazy import `HardStopHandler`, dipake runtime sebagai G01 gate (baris 438, 440)
- `src/core/services/prompt_loader.py` — duck-typed via `hard_stop_handler` param (tidak import langsung, tapi consume `.is_safe`)
- `src/persona/yandere_fsm.py` — consume via duck-type `SupportsIsSafe` (tidak import langsung)
- `src/persona/punishment_engine.py` — consume via duck-type `SupportsIsSafe` (tidak import langsung)

**Referenced By (tests/):**
- `tests/hermes/test_safety_plugin.py` — integration tests
- Berbagai test melalui mock/duck-typing

**Verdict:** `keep`

**Alasan:** Ini adalah **production safety gate aktif**. `safety_plugin.py` instantiate `HardStopHandler()` di runtime dan memakainya sebagai G01 (gate pertama pre-LLM). `cmd_safeword.py` dan `commands_high/safeword.py` langsung import dan instantiate untuk Discord command. `surveillance/windows_consent.py` dan `surveillance/safe_mode.py` import `SafetyState` dari sini. Module ini adalah live, critical, dan terhubung ke pipeline utama.

---

## 5. `src/persona/drift_detector.py`

**Path:** `src/persona/drift_detector.py`

**Classes/Functions:**
- `DriftDetectionError` (exception)
- `DriftBaselineError` (exception)
- `DriftComputationError` (exception)
- `DriftResult` (dataclass, frozen)
- `DriftBaseline` (dataclass, frozen)
- `DriftDetector` (class — compute_drift_score, detect, update_baseline, compute_prompt_hash)

**Imported By (src/ — non-self):**
- `src/persona/__init__.py` — re-export
- `src/persona/drift_corrector.py` — import `DriftDetector`, `DriftResult` (tapi drift_corrector sendiri dead)
- `src/hermes/safety_plugin.py` — lazy import `DriftDetector`, `DriftBaseline` (baris 467, 802, 826) — **dipakai di runtime sebagai safety gate**

**Referenced By (tests/):**
- `tests/persona/test_drift_corrector.py` — via drift_corrector
- `tests/persona/test_persona_e2e.py` — via e2e
- Berbagai test safety_plugin

**Verdict:** `keep`

**Alasan:** `src/hermes/safety_plugin.py` mengimpor dan menggunakan `DriftDetector` secara langsung di runtime (baris 467, 802, 808, 824, 826) — independent dari `drift_corrector`. Safety plugin membangun `DriftDetector` instance sendiri untuk prompt hash checking. **Berbeda dari `drift_corrector` yang hanya dipakai oleh `__init__.py`**, `drift_detector` punya caller nyata di production code.

---

## Ringkasan

| File | Classes/Functions Utama | Imported By (src/ aktif) | Verdict |
|------|------------------------|--------------------------|---------|
| `src/persona/safe_mode.py` | `DistressDetector`, `SafeModeController`, `DistressLevel` | `punishment_engine`, `hermes_conversational`, `safety_plugin` | **keep** |
| `src/persona/drift_corrector.py` | `DriftCorrector`, `DriftCorrectionResult`, `RollbackResult` | `__init__.py` (re-export saja) | **safe_to_delete** |
| `src/persona/transition_rules.py` | `TransitionRuleEngine`, `TransitionContext`, `TransitionDecision` | `__init__.py` (re-export saja) | **safe_to_delete** |
| `src/core/services/hard_stop_handler.py` | `HardStopHandler`, `SafetyState` | `safety_plugin`, `cmd_safeword`, `surveillance/*` | **keep** |
| `src/persona/drift_detector.py` | `DriftDetector`, `DriftBaseline`, `DriftResult` | `safety_plugin` (langsung), `drift_corrector` | **keep** |

**Files yang aman dihapus:** `drift_corrector.py`, `transition_rules.py`  
**Files yang harus dipertahankan:** `safe_mode.py`, `hard_stop_handler.py`, `drift_detector.py`

**Side effect jika hapus `drift_corrector.py`:** Entry di `src/persona/__init__.py` baris 20-26 dan `__all__` entries untuk `DriftCorrector`, `DriftCorrectionResult`, `DriftCorrectionError`, `RollbackResult`, `RollbackError`, `DRIFT_THRESHOLD` harus ikut dihapus.

**Side effect jika hapus `transition_rules.py`:** Entry di `src/persona/__init__.py` baris 112-121 dan `__all__` entries untuk `TransitionRuleEngine`, `TransitionContext`, `TransitionDecision`, `VALID_TRANSITIONS`, `ALL_MOODS`, `TransitionRulesError`, `CooldownActiveError`, `InvalidTransitionError` harus ikut dihapus.
