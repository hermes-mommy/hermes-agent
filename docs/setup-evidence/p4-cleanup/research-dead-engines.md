# Dependency Audit — Dead Engines P4 Cleanup

**Tanggal audit:** 2026-06-09  
**Scope:** `src/` (exclude `src/_deprecated/`, `tests/`, `docs/`)  
**Metode:** grep exhaustif + baca source langsung untuk setiap class utama  

---

## Metodologi

Untuk setiap komponen:
1. Identifikasi class utama dari source file
2. `grep -rn <ClassName>` di seluruh `src/` (kecuali `_deprecated/` dan file itu sendiri)
3. Verifikasi apakah caller tersebut benar-benar instantiate/invoke (bukan sekadar re-export di `__init__.py`)
4. Cek Discord commands, Hermes plugins, scheduler/loop

**Catatan penting tentang `src/persona/__init__.py`:**  
File ini re-export semua class dari sub-modul persona, tapi **tidak ada file lain di luar `src/persona/`** yang melakukan `from src.persona import ...` (zero matches di seluruh src/). Jadi re-export di `__init__.py` adalah dead code dari perspektif callers.

---

## 1. PunishmentEngine

| Field | Detail |
|---|---|
| **path** | `src/persona/punishment_engine.py` |
| **main_classes** | `PunishmentEngine`, `PunishmentLevel`, `PunishmentState`, `PunishmentLevelConfig` |
| **callers_in_src** | `src/persona/__init__.py` (re-export only — tidak ada caller lain) |
| **Discord command** | `src/discord/cmd_punishment.py` ada, tapi **tidak import PunishmentEngine** — langsung tulis Redis + DB via `PunishmentLog` model |
| **Hermes plugin** | `src/hermes_plugins/commands_system/punishment.py` ada, tapi **tidak import PunishmentEngine** — pakai `guinevere_safety.state_manager.StateManager` |
| **Loop/scheduler** | Tidak ada |
| **verdict** | **DEAD** |
| **notes** | `/punishment` command berjalan tanpa PunishmentEngine. Engine class tidak pernah di-instantiate di production path manapun. `punishment_engine.py` memang import `SupportsIsSafe` dari `yandere_fsm.py` (Protocol only), tapi itu internal saja. |

---

## 2. RewardEngine

| Field | Detail |
|---|---|
| **path** | `src/persona/reward_engine.py` |
| **main_classes** | `RewardEngine`, `RewardTier`, `RewardResult`, `RewardConfigEntry` |
| **callers_in_src** | `src/persona/__init__.py` (re-export only); `src/gamification/__init__.py` menyebut "RewardEngine" hanya dalam **docstring komentar** — tidak import |
| **Discord command** | `src/discord/cmd_reward.py` ada, tapi **tidak import RewardEngine** — langsung tulis Redis + DB via `RewardLog` model |
| **Hermes plugin** | `src/hermes_plugins/commands_system/reward.py` ada, tapi **tidak import RewardEngine** — pakai `guinevere_safety.state_manager.StateManager` |
| **Loop/scheduler** | Tidak ada |
| **verdict** | **DEAD** |
| **notes** | `/reward` command berjalan tanpa RewardEngine. Gamification module (`src/gamification/`) tidak import RewardEngine — reference hanya di docstring. |

---

## 3. YandereEngine / yandere_fsm

| Field | Detail |
|---|---|
| **path** | `src/persona/yandere_fsm.py` |
| **main_classes** | `YandereEngine`, `YandereLevel`, `YandereError`, `YandereSafetyError`, `SupportsIsSafe` |
| **callers_in_src** | `src/persona/__init__.py` (re-export); `src/persona/punishment_engine.py` (import `SupportsIsSafe` Protocol only); **`src/hermes/safety_plugin.py`** (instantiate `YandereEngine` aktif) |
| **Discord command** | Tidak ada Discord command yang memanggil langsung |
| **Hermes plugin** | `src/hermes/safety_plugin.py` — **AKTIF**: instantiate `YandereEngine(hard_stop_handler=None, baseline=YandereLevel.Y4_BASELINE)` pada init (line ~509), dipakai untuk safety gate G07/G08 |
| **Loop/scheduler** | Tidak ada loop langsung, tapi dipanggil via safety_plugin yang aktif di setiap conversation turn |
| **verdict** | **LIVE** |
| **notes** | `YandereEngine` adalah komponen safety-critical. Dipakai `safety_plugin.py` untuk gate G07 (yandere level enforcement) dan G08. Jangan dihapus. |

---

## 4. MoodEngine

| Field | Detail |
|---|---|
| **path** | `src/persona/mood_engine.py` |
| **main_classes** | `MoodEngine` (tidak ada — file ini tidak punya class `MoodEngine`!), fungsi `evaluate_mood`, `sync_mood_to_redis`, `can_transition`; enum `Mood`; dataclass `MoodTransition` |
| **callers_in_src** | `src/persona/__init__.py` (re-export); `src/discord/hermes_conversational.py` (import `Mood` enum only — line 489, lazy import); `src/persona/rituals/morning.py`, `midday.py`, `afternoon.py`, `evening.py` (import `Mood` enum only); `src/persona/mood_persistence.py` (referensi di docstring saja) |
| **Discord command** | `src/discord/cmd_mood.py` ada, tapi **tidak import dari mood_engine** — embed data hardcoded dengan degraded placeholders |
| **Hermes plugin** | `src/hermes_plugins/commands_high/mood.py` ada, tapi **tidak import dari mood_engine** — format markdown hardcoded |
| **Loop/scheduler** | Tidak ada |
| **verdict** | **DEAD** (fungsi utama); **LIVE** (enum `Mood` saja) |
| **notes** | Tidak ada class `MoodEngine` — nama file misleading. Yang ada adalah fungsi-fungsi (`evaluate_mood`, `sync_mood_to_redis`, `can_transition`) dan enum `Mood`. Hanya `Mood` enum yang dipakai (oleh conversational handler dan ritual modules sebagai type hint). Fungsi `evaluate_mood`, `sync_mood_to_redis`, `can_transition`, konstanta `TRANSITIONS`/`MOOD_VARIANT_MAP` — semua DEAD (tidak dipanggil di luar persona/ itu sendiri). Jika rituals juga dead (lihat item 5 & 9), maka bahkan `Mood` import dari ritual modules juga dead. |

---

## 5. RitualScheduler

| Field | Detail |
|---|---|
| **path** | `src/persona/ritual_scheduler.py` |
| **main_classes** | `RitualScheduler`, `RitualConfig`, `RitualResult`, `RitualSchedulerError` |
| **callers_in_src** | `src/persona/__init__.py` (re-export dengan `DeprecationWarning`, ditandai deprecated Phase 5) |
| **Discord command** | Tidak ada |
| **Hermes plugin** | Tidak ada |
| **Loop/scheduler** | Tidak ada — `src/loops/scheduler.py` adalah `LoopScheduler` berbasis APScheduler yang berbeda sama sekali, tidak memanggil `RitualScheduler` |
| **verdict** | **DEAD** |
| **notes** | Sudah ditandai deprecated di `src/persona/__init__.py` (Phase 5, scheduled removal Phase 7). Tidak ada caller aktif. `LoopScheduler` di `src/loops/` adalah sistem terpisah dan tidak berkaitan. |

---

## 6. StreakTracker

| Field | Detail |
|---|---|
| **path** | `src/persona/streak_tracker.py` |
| **main_classes** | `StreakTracker`, `StreakError`, `StreakPersistenceError` |
| **callers_in_src** | `src/persona/__init__.py` (re-export only); `src/gamification/__init__.py` menyebut "StreakTracker" dalam **docstring komentar** — tidak import |
| **Discord command** | `src/discord/cmd_mood.py` tampilkan "Streak" field tapi pakai degraded placeholder `"⚠️ — Streak tracking (P4 not deployed)"` — tidak import StreakTracker |
| **Hermes plugin** | `src/hermes_plugins/commands_high/mood.py` — sama, degraded placeholder |
| **Loop/scheduler** | Tidak ada |
| **verdict** | **DEAD** |
| **notes** | Streak tracking diakui belum di-deploy (P4 not deployed) di semua UI yang menampilkannya. Tidak ada instantiation di production path manapun. |

---

## 7. MoodRepository / mood_persistence

| Field | Detail |
|---|---|
| **path** | `src/persona/mood_persistence.py` |
| **main_classes** | `MoodRepository`, `MoodState`, `MoodHistoryRecord`, `MoodPersistenceError` |
| **callers_in_src** | `src/persona/__init__.py` (re-export only); `src/persona/mood_engine.py` menyebut `mood_persistence` di docstring `_MoodStateManagerProtocol` — tidak import actual class |
| **Discord command** | Tidak ada |
| **Hermes plugin** | Tidak ada (persona_plugin.py baca mood dari Redis langsung, bukan via MoodRepository) |
| **Loop/scheduler** | Tidak ada |
| **verdict** | **DEAD** |
| **notes** | `PersonaPlugin` (src/hermes/plugins/persona_plugin.py) baca `guinevere:mood_variant` langsung dari Redis DB5, bypass MoodRepository sepenuhnya. Tidak ada caller yang instantiate MoodRepository di production path. |

---

## 8. DriftDetector

| Field | Detail |
|---|---|
| **path** | `src/persona/drift_detector.py` |
| **main_classes** | `DriftDetector`, `DriftBaseline`, `DriftResult`, `DriftBaselineError`, `DriftComputationError` |
| **callers_in_src** | `src/persona/__init__.py` (re-export, non-deprecated section); **`src/hermes/safety_plugin.py`** (aktif digunakan, multiple sites) |
| **Discord command** | Tidak ada Discord command langsung |
| **Hermes plugin** | `src/hermes/safety_plugin.py` — **AKTIF**: lazy-init `DriftDetector` pada `post_llm_call`, compute `DriftDetector.compute_prompt_hash(text)` setiap LLM response, compare drift against `SOUL_BASELINE_HASH` |
| **Loop/scheduler** | Dipanggil di setiap `post_llm_call` hook (per conversation turn) |
| **verdict** | **LIVE** |
| **notes** | Komponen safety-critical Gate G03. `safety_plugin.py` check `_drift_available` flag, lazy-init DriftDetector, dan compute drift score setiap assistant response. Konfirmasi: ini KEEP. `src/memory/models.py` juga menyebut `'system:drift_detector'` sebagai reviewer string (line 393) — tidak import class tapi acknowledge keberadaannya di audit log. |

---

## 9. src/persona/rituals/ (morning, midday, afternoon, evening, midnight)

| Field | Detail |
|---|---|
| **path** | `src/persona/rituals/morning.py`, `midday.py`, `afternoon.py`, `evening.py`, `midnight.py` |
| **main_classes** | `MorningRitual`, `MiddayRitual`, `AfternoonRitual`, `EveningRitual`, `MidnightRitual` |
| **callers_in_src** | `src/persona/__init__.py` hanya (import dengan `DeprecationWarning` suppressed, ditandai deprecated Phase 5) |
| **Discord command** | Tidak ada |
| **Hermes plugin** | Tidak ada |
| **Loop/scheduler** | Tidak ada — `LoopScheduler` di `src/loops/` tidak memanggil ritual classes ini sama sekali |
| **verdict** | **DEAD** |
| **notes** | Semua 5 ritual modules ditandai deprecated di docstring mereka sendiri ("deprecated in favour of Hermes cron + PersonaPlugin") dan di `src/persona/__init__.py`. Ritual templates sudah diported ke SOUL.md §H/§J. Ritual modules hanya import `Mood` enum dari `mood_engine.py` — tidak ada logic aktif yang dipanggil dari luar. `src/persona/rituals/__init__.py` juga mengeluarkan `DeprecationWarning` saat diimport. |

---

## Ringkasan Verdict

| # | Komponen | Verdict | Caller Aktif |
|---|---|---|---|
| 1 | `PunishmentEngine` | **DEAD** | Tidak ada |
| 2 | `RewardEngine` | **DEAD** | Tidak ada |
| 3 | `YandereEngine` / yandere_fsm | **LIVE** | `safety_plugin.py` (G07/G08) |
| 4 | `MoodEngine` / mood_engine | **DEAD** (fungsi); `Mood` enum dipakai tapi via dead modules | Hanya `Mood` enum — via conversational handler (lazy) dan ritual modules (dead) |
| 5 | `RitualScheduler` | **DEAD** | Tidak ada (deprecated Phase 5) |
| 6 | `StreakTracker` | **DEAD** | Tidak ada (P4 not deployed) |
| 7 | `MoodRepository` / mood_persistence | **DEAD** | Tidak ada |
| 8 | `DriftDetector` | **LIVE** | `safety_plugin.py` (G03) |
| 9 | rituals/ (all 5) | **DEAD** | Tidak ada (deprecated Phase 5) |

### Candidates for deletion (Phase 7)
- `src/persona/punishment_engine.py`
- `src/persona/reward_engine.py`
- `src/persona/ritual_scheduler.py`
- `src/persona/streak_tracker.py`
- `src/persona/mood_persistence.py`
- `src/persona/mood_engine.py` (atau bisa distrip jadi hanya `Mood` enum jika diperlukan)
- `src/persona/rituals/` (seluruh package)

### Keep (safety-critical)
- `src/persona/yandere_fsm.py` — dipakai `safety_plugin.py` G07/G08
- `src/persona/drift_detector.py` — dipakai `safety_plugin.py` G03
- `src/persona/safe_mode.py` — tidak di-audit di sini tapi diasumsikan aktif di safety_plugin G02

---

*Audit oleh: Hermes sub-agent — exhaustif grep + source read, tidak ada assumption*
