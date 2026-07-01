# Research: Test Coverage Mapping — Komponen yang Akan Dihapus/Dimodifikasi

**Date:** 2026-06-09
**Status:** Research Complete
**Task:** Pra-analisis test coverage sebelum penghapusan safety enforcement modules

---

## Ringkasan Eksekutif

Enam source module target (safe_mode.py, drift_corrector.py, transition_rules.py,
hard_stop_handler.py, safety_plugin.py, drift_detector.py) di-cover oleh **23 test files**
dengan total **899+ test functions**. Semua test file yang exclusively test komponen
tersebut harus dihapus. Test file yang hanya partially menggunakan komponen tersebut
perlu dimodifikasi untuk menghapus referensi yang relevan.

---

## 1. `src/persona/safe_mode.py` — SafeModeController + DistressDetector

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/persona/test_safe_mode.py` | 69 | **HAPUS** |
| `tests/persona/test_distress_detection.py` | 44 | **HAPUS** |
| `tests/safety/test_distress_protocol_e2e.py` | 55 | **HAPUS** |
| `tests/surveillance/test_safe_mode.py` | 30 | **HAPUS** (test SurveillanceSafeModeGuard, bukan SafeModeController, tapi import dari src.surveillance.safe_mode — beda file) |

**Catatan:** `tests/surveillance/test_safe_mode.py` mengimport dari `src.surveillance.safe_mode`
(bukan `src.persona.safe_mode`). File ini mengetes `SurveillanceSafeModeGuard` / `ConfrontationDecision`.
Tergantung apakah `src/surveillance/safe_mode.py` juga dihapus — jika ya, hapus. Jika tidak, pertahankan.

### Test Files yang Partially Menggunakan safe_mode.py

| Path | Test Count | Referensi ke safe_mode.py | Aksi |
|------|-----------|--------------------------|------|
| `tests/phase7/test_T7_distress_protocol.py` | 13 | `from src.persona.safe_mode import DistressLevel, DistressSignal, SafeModeController, SafeModeError` | **HAPUS** (seluruh file khusus distress protocol) |
| `tests/safety/test_consent_revocation.py` | 44 | Load `safe_mode.py` via importlib; `SafeModeController`, `DistressLevel`, `DistressSignal` | **HAPUS** (SafeModeController dipakai di semua fixtures) |
| `tests/safety/test_punishment_overflow.py` | 43 | Load `safe_mode.py` via importlib; `SafeModeController`, `DistressLevel` | **MODIFIKASI** (hapus fixture `safe_mode`, test yang pakai `safe_mode_controller`) |
| `tests/persona/test_drift_corrector.py` | 43 | `from persona.safe_mode import SafeModeController` | **MODIFIKASI** (hapus fixture safe_mode, test defer-saat-safe-mode) |
| `tests/memory/test_safe_mode_memory.py` | 64 | Import `HardStopHandler`, behavior safe-mode dalam prompt assembly | **MODIFIKASI** (hapus test safe-mode-specific) |
| `tests/memory/test_prompt_context_injection.py` | 18 | `safe_mode` param di `assemble_system_prompt_with_memory` | **MODIFIKASI** (hapus test safe_mode propagation) |
| `tests/hermes/test_safety_plugin.py` | 99 | `plugin._distress_available`, `plugin._distress_detector`, mock `src.persona.safe_mode` | **MODIFIKASI** (hapus TestDistressDetection class, hapus mock safe_mode) |

---

## 2. `src/persona/drift_corrector.py` — DriftCorrector

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/persona/test_drift_corrector.py` | 43 | **HAPUS** |

### Test Files yang Partially Menggunakan drift_corrector.py

Tidak ada test file lain yang langsung mengimport `DriftCorrector`.
`tests/hermes/test_safety_plugin.py` menggunakan `_drift_available` / `_drift_detector`
yang merujuk ke `drift_detector`, bukan `drift_corrector`. Lihat section 6 untuk detail.

---

## 3. `src/persona/transition_rules.py` — TransitionRuleEngine

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/persona/test_transition_rules.py` | 42 | **HAPUS** |

### Test Files yang Partially Menggunakan transition_rules.py

| Path | Test Count | Referensi | Aksi |
|------|-----------|-----------|------|
| `tests/phase7/test_T6_persona_fsm.py` | 22 | `from src.persona.transition_rules import TransitionContext, TransitionRuleEngine` — `class TestTransitionRules` (3 tests) | **MODIFIKASI** (hapus `TestTransitionRules` class) |

---

## 4. `src/core/services/hard_stop_handler.py` — HardStopHandler

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/safety/test_hard_stop_handler.py` | 16 | **HAPUS** |
| `tests/safety/test_hard_stop_latency.py` | 8 | **HAPUS** |
| `tests/safety/test_hard_stop_comprehensive.py` | 86 | **HAPUS** |

### Test Files yang Partially Menggunakan hard_stop_handler.py

| Path | Test Count | Referensi | Aksi |
|------|-----------|-----------|------|
| `tests/phase7/test_T2_safety_gates.py` | 10 | `from src.core.services.hard_stop_handler import HardStopHandler, SafetyState` — `class TestHardStopSafetyGate` (10 tests) | **HAPUS** (seluruh file hanya test hard_stop + yandere_fsm) |
| `tests/phase7/test_T7_distress_protocol.py` | 13 | N/A langsung, tapi closely related | **HAPUS** (sudah di section 1) |
| `tests/phase7/test_T8_consent_revocation.py` | 11 | `from src.core.services.hard_stop_handler import HardStopHandler, SafetyState` — `class TestHardStopConsentRevocation` | **MODIFIKASI** (hapus TestHardStopConsentRevocation, pertahankan TestConsentGate) |
| `tests/safety/test_consent_revocation.py` | 44 | `HardStopHandler` di-load via importlib | **HAPUS** (covered di section 1, SafeModeController juga hilang) |
| `tests/memory/test_safe_mode_memory.py` | 64 | `HardStopHandler.is_safe` dipakai dalam prompt assembly tests | **MODIFIKASI** |
| `tests/memory/test_prompt_context_injection.py` | 18 | `hard_stop_handler.is_safe` override test | **MODIFIKASI** |
| `tests/hermes/test_safety_plugin.py` | 99 | mock `src.core.services.hard_stop_handler`; `plugin._hard_stop_available`, `_hard_stop_handler` | **MODIFIKASI** (hapus TestDistressDetection, hapus hard_stop mock/tests) |
| `tests/safety/test_hard_stop_model.py` | 8 | Tidak import HardStopHandler — test model LLM compliance. Tetap valid. | **PERTAHANKAN** (independent dari handler code) |
| `tests/persona/test_yandere_fsm.py` | 71 | `FakeHardStopHandler` stub, bukan import langsung | **MODIFIKASI** (hapus HardStopHandler integration tests, gunakan stub-only) |

---

## 5. `src/hermes/safety_plugin.py` — GuinevereSafetyPlugin

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/hermes/test_safety_plugin.py` | 99 | **HAPUS** |

### Test Files yang Partially Menggunakan safety_plugin.py

Tidak ada test file lain yang langsung import `GuinevereSafetyPlugin`.
File ini adalah primary test file untuk plugin tersebut.

---

## 6. `src/persona/drift_detector.py` — DriftDetector

### Test Files yang Exclusively Mengetes Komponen Ini

| Path | Test Count | Aksi |
|------|-----------|------|
| `tests/persona/test_drift_detector.py` | 34 | **HAPUS** |

### Test Files yang Partially Menggunakan drift_detector.py

| Path | Test Count | Referensi | Aksi |
|------|-----------|-----------|------|
| `tests/phase7/test_T6_persona_fsm.py` | 22 | `from src.persona.drift_detector import DriftBaseline, DriftDetector, DriftResult` — `class TestDriftDetector` (3 tests) | **MODIFIKASI** (hapus `TestDriftDetector` class) |
| `tests/persona/test_drift_corrector.py` | 43 | `from persona.drift_detector import DriftBaseline, DriftDetector` | **HAPUS** (sudah di section 2) |
| `tests/hermes/test_safety_plugin.py` | 99 | `plugin._drift_available`, `_drift_detector`, mock `src.persona.drift_detector`, `class TestDriftDetection` | **HAPUS** (sudah di section 5) |

---

## Tabel Konsolidasi: Semua Test Files Terdampak

| No | Test File | Total Tests | Komponen Terdampak | Status Aksi | Alasan |
|----|-----------|------------|-------------------|-------------|--------|
| 1 | `tests/persona/test_safe_mode.py` | 69 | safe_mode.py (full) | **HAPUS** | 100% dedicated ke SafeModeController/DistressDetector |
| 2 | `tests/persona/test_distress_detection.py` | 44 | safe_mode.py (full) | **HAPUS** | 100% dedicated ke DistressDetector |
| 3 | `tests/persona/test_drift_corrector.py` | 43 | drift_corrector.py + safe_mode.py + drift_detector.py | **HAPUS** | 100% dedicated ke DriftCorrector |
| 4 | `tests/persona/test_transition_rules.py` | 42 | transition_rules.py (full) | **HAPUS** | 100% dedicated ke TransitionRuleEngine |
| 5 | `tests/persona/test_drift_detector.py` | 34 | drift_detector.py (full) | **HAPUS** | 100% dedicated ke DriftDetector |
| 6 | `tests/hermes/test_safety_plugin.py` | 99 | safety_plugin.py + semua deps | **HAPUS** | 100% dedicated ke GuinevereSafetyPlugin |
| 7 | `tests/safety/test_hard_stop_handler.py` | 16 | hard_stop_handler.py (full) | **HAPUS** | 100% dedicated ke HardStopHandler |
| 8 | `tests/safety/test_hard_stop_latency.py` | 8 | hard_stop_handler.py (full) | **HAPUS** | 100% latency test HardStopHandler |
| 9 | `tests/safety/test_hard_stop_comprehensive.py` | 86 | hard_stop_handler.py (full) | **HAPUS** | 100% dedicated ke HardStopHandler |
| 10 | `tests/safety/test_distress_protocol_e2e.py` | 55 | safe_mode.py (full) | **HAPUS** | 100% dedicated ke DistressDetector E2E |
| 11 | `tests/safety/test_consent_revocation.py` | 44 | safe_mode.py + hard_stop_handler.py | **HAPUS** | Entirely depends on SafeModeController + HardStopHandler |
| 12 | `tests/phase7/test_T2_safety_gates.py` | 10 | hard_stop_handler.py (full) | **HAPUS** | Entire file tests HardStopHandler gates |
| 13 | `tests/phase7/test_T7_distress_protocol.py` | 13 | safe_mode.py (full) | **HAPUS** | 100% dedicated ke SafeModeController/DistressSignal |
| 14 | `tests/phase7/test_T6_persona_fsm.py` | 22 | transition_rules.py + drift_detector.py (partial) | **MODIFIKASI** | Hapus `TestTransitionRules` (3 tests) + `TestDriftDetector` (3 tests); pertahankan `TestYandereFSM`, `TestMoodEngine`, `TestStreakTracker` |
| 15 | `tests/phase7/test_T8_consent_revocation.py` | 11 | hard_stop_handler.py (partial) | **MODIFIKASI** | Hapus `TestHardStopConsentRevocation` (5 tests); pertahankan `TestConsentGate` |
| 16 | `tests/safety/test_punishment_overflow.py` | 43 | safe_mode.py (partial) | **MODIFIKASI** | Hapus fixture `safe_mode` + test yang pakai SafeModeController; pertahankan test punishment murni |
| 17 | `tests/memory/test_safe_mode_memory.py` | 64 | hard_stop_handler.py + safe_mode.py (partial) | **MODIFIKASI** | Hapus test safe-mode memory gating; review apakah source prompt_loader masih ada |
| 18 | `tests/memory/test_prompt_context_injection.py` | 18 | hard_stop_handler.py (partial) | **MODIFIKASI** | Hapus 2 test `safe_mode propagation` + `hard_stop_handler override` |
| 19 | `tests/persona/test_yandere_fsm.py` | 71 | hard_stop_handler.py (stub, partial) | **MODIFIKASI** | Hapus integration test dengan FakeHardStopHandler jika handler hilang |
| 20 | `tests/safety/test_hard_stop_model.py` | 8 | LLM compliance (independent) | **PERTAHANKAN** | Test model LLM behavior, tidak import HardStopHandler |
| 21 | `tests/safety/test_forbidden_pattern_scanner.py` | 8 | hermes-config hook (independent) | **PERTAHANKAN** | Test `safety_scan.py` hook, bukan `safety_plugin.py` |
| 22 | `tests/safety/test_auto_rollback.py` | 27 | sandbox simulator (independent) | **PERTAHANKAN** | Pure sandbox simulation, tidak ada dependency ke 6 modules |
| 23 | `tests/safety/test_yandere_cap.py` | 53 | yandere_fsm.py (partial) | **PERTAHANKAN** | Tidak import komponen target; Y6/Y5 tests remain valid |

---

## Ringkasan per Source Module

| Source Module | Test Files Dedicated (HAPUS) | Test Files Partial (MODIFIKASI) | Total Tests Terdampak |
|--------------|------------------------------|--------------------------------|----------------------|
| `src/persona/safe_mode.py` | 4 files (181 tests) | 7 files (partial) | ~181 langsung + partial |
| `src/persona/drift_corrector.py` | 1 file (43 tests) | 0 files | 43 |
| `src/persona/transition_rules.py` | 1 file (42 tests) | 1 file (~3 tests) | ~45 |
| `src/core/services/hard_stop_handler.py` | 3 files (110 tests) | 5 files (partial) | ~110 langsung + partial |
| `src/hermes/safety_plugin.py` | 1 file (99 tests) | 0 files | 99 |
| `src/persona/drift_detector.py` | 1 file (34 tests) | 2 files (~6 tests) | ~40 |

**Total test files yang perlu diproses: 23 files**
- Files yang harus dihapus sepenuhnya: **13 files** (dengan ~597 tests)
- Files yang perlu dimodifikasi: **6 files** (total ~252 tests, subset yang dihapus)
- Files yang dipertahankan tanpa perubahan: **4 files**

---

## Catatan Risiko

1. **`tests/surveillance/test_safe_mode.py`** — Mengetes `src.surveillance.safe_mode`
   (bukan `src.persona.safe_mode`). Kalau `src/surveillance/safe_mode.py` TIDAK dihapus,
   file ini tetap valid. Perlu konfirmasi scope penghapusan surveillance module.

2. **`tests/memory/test_safe_mode_memory.py`** — Mengetes behavior di `prompt_loader.py`
   yang menggunakan `HardStopHandler`. Kalau `prompt_loader.py` masih ada tapi
   parameter `hard_stop_handler` dihapus dari API-nya, file ini perlu dimodifikasi.

3. **`tests/persona/test_yandere_fsm.py`** — Menggunakan `FakeHardStopHandler` (bukan
   import langsung). Test integrasi bisa digantikan dengan mock sederhana tanpa
   bergantung ke implementasi `HardStopHandler`. Modifikasi ringan.

4. **`tests/safety/test_consent_revocation.py`** — Walaupun load via importlib bukan
   import langsung, tetap bergantung pada keberadaan file fisik `safe_mode.py` dan
   `hard_stop_handler.py` di disk. Harus dihapus sepenuhnya.

5. **`tests/phase7/test_T6_persona_fsm.py`** — Setelah modifikasi (hapus 2 class),
   file ini masih valid dengan 16 tests (TestYandereFSM, TestMoodEngine, TestStreakTracker).

---

*Generated by test coverage research sub-agent, 2026-06-09*
