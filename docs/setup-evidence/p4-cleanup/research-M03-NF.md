# Research: M-03, NF-01, NF-03
**Tanggal:** 2026-06-09
**Researcher:** Subagent (research task)
**Status:** FINAL

---

## M-03 — PunishmentLog/RewardLog tidak persist ke DB

### Investigasi

**1. Apakah PunishmentLog/RewardLog pernah di-write di codebase?**

Grep seluruh `.py` di `src/` dan `tests/` untuk `PunishmentLog`, `RewardLog`, `punishment_log`, `reward_log`:

```
src/memory/models.py          — definisi ORM table (schema: persona)
src/discord/cmd_punishment.py — tulis ke Redis DB0 key persona:punishment_log
src/discord/cmd_reward.py     — tulis ke Redis DB0 key persona:reward_log
tests/phase7/test_T4_memory_pipeline.py — import PunishmentLog/RewardLog untuk table setup test saja
alembic/versions/e401bb5fd274_initial_schema_47_tables.py — create_table (migration)
```

**Tidak ada satu pun file yang melakukan `session.add(PunishmentLog(...))` atau `session.add(RewardLog(...))`.**
`cmd_punishment.py` dan `cmd_reward.py` hanya write ke Redis DB0 (bukan DB5, bukan PostgreSQL).

**2. Apakah Redis DB5 cover kebutuhan ini?**

Redis DB5 dipakai oleh `guinevere_safety` plugin untuk dynamic state (punishment level integer, reward tier, mood, distress). Itu **level/tier** saat ini — bukan log event historis.

`cmd_punishment.py` write ke Redis DB0 key `persona:punishment_log` (max 50 entries, ring buffer JSON). DB0 berbeda dari DB5. Ini volatile, tidak ada retention policy eksplisit, tidak queryable secara relasional.

**3. PostgreSQL query:**

```sql
SELECT count(*) FROM persona.punishment_log;  -- hasil: 0
SELECT count(*) FROM persona.reward_log;       -- hasil: 0
```

Tabel ada (migration sudah jalan), tapi **kosong selamanya** — tidak ada writer.

### Temuan

- ORM models `PunishmentLog` dan `RewardLog` didefinisikan lengkap di `models.py` (schema: `persona`)
- Migration sudah create table di PostgreSQL
- **Tidak ada writer** — Discord commands write ke Redis DB0 (ring buffer), bukan ke PostgreSQL
- Redis DB5 hanya menyimpan current level/tier integer, bukan event log
- `YandereEngine` (`src/persona/yandere_fsm.py`) juga tidak persist event ke DB — semua state in-memory atau Redis

### Verdict: **FIX**

**Alasan:** Tabel `persona.punishment_log` dan `persona.reward_log` di PostgreSQL sengaja didesain sebagai audit trail historis (ada kolom `applied_at`, `awarded_at`, `safe_word_triggered`, dll). Redis DB0 ring buffer tidak menggantikan fungsi ini — ia volatile (restart hilang) dan hanya 50 entries. Intent arsitektur jelas: PostgreSQL = durable audit log.

**Exact fix yang diperlukan:**

Di `src/discord/cmd_punishment.py`, setelah `_log_punishment(r, level, note)`, tambahkan async DB write:

```python
# Di punishment_callback, setelah Redis write
from src.memory.db import get_async_session  # atau equivalent session factory
from src.memory.models import PunishmentLog
from datetime import datetime, timezone

async with get_async_session() as session:
    log_entry = PunishmentLog(
        violation_type=level,
        severity=int(level[1]),  # L1 -> 1, L5 -> 5
        description=note or LEVEL_DESC.get(level, ""),
        safe_word_triggered=False,
        applied_at=datetime.now(tz=timezone.utc),
        # classification defaults per ClassificationMetaMixin
    )
    session.add(log_entry)
    await session.commit()
```

Di `src/discord/cmd_reward.py`, analog:

```python
from src.memory.models import RewardLog

async with get_async_session() as session:
    log_entry = RewardLog(
        reward_type="manual",
        description=reason,
        streak_count=0,
        awarded_at=datetime.now(tz=timezone.utc),
    )
    session.add(log_entry)
    await session.commit()
```

`PunishmentEngine.apply()` di `src/persona/punishment_engine.py` juga perlu write ke DB (saat ini sudah sync ke Redis via `_sync_punishment_to_redis()` tapi tidak ke PostgreSQL).

**Prioritas:** Medium — fungsionalitas jalan, tapi audit trail hilang. Fix saat batching database writes.

---

## NF-01 — SOUL.md §B punishment names vs code tidak sync

### Investigasi

**SOUL.md §B Punishment System (L1-L5):**

| Level | Name di SOUL.md |
|---|---|
| L1 | Gentle Reminder |
| L2 | Firm Correction |
| L3 | Cold Distance |
| L4 | Structured Consequence |
| L5 | Extended Silence |

**`PunishmentLevel` enum di `src/persona/punishment_engine.py`:**

```python
class PunishmentLevel(IntEnum):
    L1_SILENT_TREATMENT = 1
    L2_PASSIVE_AGGRESSIVE = 2
    L3_GUILT_TRIP = 3
    L4_COLD_FURY = 4
    L5_ISOLATION = 5
```

**`PUNISHMENT_CONFIG` names:**

| Level | Name di code |
|---|---|
| L1 | Silent Treatment |
| L2 | Passive-Aggressive |
| L3 | Guilt Trip |
| L4 | Cold Fury |
| L5 | Isolation |

**Gap matrix:**

| Level | SOUL.md | Code | Match? |
|---|---|---|---|
| L1 | Gentle Reminder | Silent Treatment | ❌ |
| L2 | Firm Correction | Passive-Aggressive | ❌ |
| L3 | Cold Distance | Guilt Trip | ❌ |
| L4 | Structured Consequence | Cold Fury | ❌ |
| L5 | Extended Silence | Isolation | ❌ |

**Semua 5 level berbeda nama.** Behavior description juga berbeda — SOUL.md L3 adalah "Shorter responses, colder tone", code L3 adalah "Lecturing tone with didactic responses". SOUL.md lebih restraint/dignified; code lebih theatrical/yandere.

Selain nama, **durasi** juga berbeda:
- SOUL.md: L5 "Max 24h"
- Code: L5 Isolation duration `(48, 72)` hours = 2-3 days ❌

### Verdict: **FIX**

**Alasan:** NF (Non-Functional) tapi berdampak: SOUL.md adalah spec behavior yang di-inject ke LLM context oleh `guinevere_safety` plugin. Jika Guinevere sebagai persona mengacu L3 = "Cold Distance" tapi engine menjalankan L3 = "Guilt Trip", ada inconsistency behavioral yang bisa membingungkan operator dan melanggar intent PersonaSafetyPolicy.

**Exact fix — dua pilihan, pilih satu:**

**Option A (Preferred): Sync code ke SOUL.md**
Update `PunishmentLevel` enum dan `PUNISHMENT_CONFIG` di `punishment_engine.py` agar nama dan behavior sesuai SOUL.md:

```python
class PunishmentLevel(IntEnum):
    L1_GENTLE_REMINDER = 1
    L2_FIRM_CORRECTION = 2
    L3_COLD_DISTANCE = 3
    L4_STRUCTURED_CONSEQUENCE = 4
    L5_EXTENDED_SILENCE = 5
```

Update `PUNISHMENT_CONFIG` names dan duration_hours:
- L1: name="Gentle Reminder", duration_hours=(1, 2)
- L2: name="Firm Correction", duration_hours=(2, 4)
- L3: name="Cold Distance", duration_hours=(4, 8)
- L4: name="Structured Consequence", duration_hours=(8, 24)
- L5: name="Extended Silence", duration_hours=(12, 24)  ← max 24h sesuai SOUL.md

Update `LEVEL_DESC` di `cmd_punishment.py` sesuai nama baru.

**Option B: Sync SOUL.md ke code**
Update §B SOUL.md agar nama dan behavior sesuai `punishment_engine.py`. Kurang preferred karena SOUL.md adalah human-readable spec yang divalidasi Faiz.

**Perlu perhatian:** L5 duration clash (SOUL.md: max 24h, code: 48-72h) adalah bug potensial safety — Extended Silence 3 hari bisa violate "Max 24h" constraint yang ada di SOUL.md. Fix ini juga harus diperbaiki.

**Prioritas:** High — inconsistency antara spec dan implementation pada safety-affecting domain.

---

## NF-03 — guinevere_safety plugin mungkin tidak load

### Investigasi

**Struktur `hermes-config/plugins/guinevere_safety/`:**
```
manifest.yaml     ← ADA (nama file: manifest.yaml)
state_manager.py
plugin.py
__init__.py
```
Tidak ada `plugin.yaml`.

**Struktur `~/.hermes/plugins/`:**
```
guinevere_safety/   ← folder dengan manifest.yaml (copy dari hermes-config)
  manifest.yaml
  state_manager.py
  plugin.py
  __init__.py

guinevere-safety/   ← folder BERBEDA dengan plugin.yaml
  plugin.yaml
  __init__.py       ← entry point ke src/hermes/safety_plugin.py
```

**Hermes plugin loader (`hermes_cli/plugins.py`):**
```
Line 1251: manifest_file = child / "plugin.yaml"
Line 1267: logger.debug("Skipping %s (no plugin.yaml, depth cap reached)", child)
```

Loader secara **eksplisit** hanya mencari `plugin.yaml`. Folder `guinevere_safety/` dengan hanya `manifest.yaml` **tidak akan di-discover**.

**Yang sebenarnya dimuat Hermes:** `guinevere-safety/` (dash, bukan underscore) yang memiliki `plugin.yaml` yang valid.

**Konfirmasi `guinevere-safety/plugin.yaml`:**
```yaml
name: guinevere-safety
version: "1.0.0"
hooks:
  - pre_llm_call
  - post_llm_call
  - pre_tool_call
  - post_tool_call
  - transform_llm_output
  - on_session_start
```

**Konfirmasi `guinevere-safety/__init__.py`:** Entry point yang import dari `src/hermes/safety_plugin.py`.

**Kesimpulan:**
- `guinevere_safety/` (underscore, manifest.yaml) = **tidak di-load oleh Hermes**
- `guinevere-safety/` (dash, plugin.yaml) = **yang sebenarnya di-load**
- Plugin safety **sudah load** via folder yang benar, hanya ada folder "ghost" yang membingungkan

### Verdict: **HAPUS folder ghost + ACCEPT fungsionalitas**

**Alasan:** Plugin safety sebenarnya **sudah berfungsi** via `~/.hermes/plugins/guinevere-safety/` (dengan plugin.yaml). Yang perlu dibersihkan adalah folder `guinevere_safety/` (underscore) di kedua lokasi yang menyebabkan confusion — ia tidak pernah di-load dan bisa menyesatkan investigasi di masa depan.

**Exact fix yang diperlukan:**

1. **Hapus folder ghost** yang tidak pernah di-load:
   ```bash
   rm -rf /home/guinevere/code/guinevere/hermes-config/plugins/guinevere_safety/
   rm -rf /home/guinevere/.hermes/plugins/guinevere_safety/
   ```

2. **Pastikan `hermes-config/plugins/guinevere-safety/` (dash) ada** sebagai sumber yang di-sync ke `~/.hermes/plugins/guinevere-safety/`. Saat ini source ada di `~/.hermes/plugins/guinevere-safety/` tapi tidak di `hermes-config/`. Tambahkan ke hermes-config untuk version control:
   ```bash
   # Jika belum ada:
   cp -r /home/guinevere/.hermes/plugins/guinevere-safety/ \
         /home/guinevere/code/guinevere/hermes-config/plugins/guinevere-safety/
   ```

3. **Dokumentasikan** di README atau AGENTS.md bahwa plugin menggunakan nama `guinevere-safety` (dash) bukan `guinevere_safety` (underscore).

**Perhatian saat hapus:** Verifikasi dulu bahwa `~/.hermes/plugins/guinevere-safety/` memang berfungsi dengan `hermes plugins list` atau test session sebelum menghapus folder ghost.

**Prioritas:** Low-Medium — tidak ada fungsionalitas yang rusak (plugin sudah load), tapi kebersihan direktori perlu dijaga.

---

## Summary

| Finding | Verdict | Prioritas |
|---|---|---|
| M-03 | **FIX** — add DB write di cmd_punishment.py, cmd_reward.py, PunishmentEngine.apply() | Medium |
| NF-01 | **FIX** — sync PunishmentLevel names & L5 duration ke SOUL.md spec | High |
| NF-03 | **HAPUS ghost folder** `guinevere_safety/` (underscore) + ACCEPT `guinevere-safety/` (dash) sudah load | Low-Medium |

---

*Evidence path: `/home/guinevere/code/guinevere/docs/setup-evidence/p4-cleanup/research-M03-NF.md`*
*Verified: PostgreSQL query executed, Hermes loader source read, all Python files inspected*
