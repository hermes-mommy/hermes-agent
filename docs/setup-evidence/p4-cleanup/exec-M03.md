# M-03 Execution Evidence — PunishmentLog & RewardLog DB Writes

**Date**: 2026-06-09
**Task**: Wire async PostgreSQL DB writes into `/punishment` and `/reward` Discord commands.

---

## Temuan Awal

| Item | Status |
|---|---|
| `src/memory/db.py` | **Tidak ada** — perlu dibuat |
| `src/memory/models.py` — `PunishmentLog` | Ada, schema `persona` |
| `src/memory/models.py` — `RewardLog` | Ada, schema `persona` |
| `src/discord/cmd_punishment.py` | Ada, hanya Redis write |
| `src/discord/cmd_reward.py` | Ada, hanya Redis write |
| Test punishment/reward | **Tidak ada** — perlu dibuat |

### PunishmentLog required fields (non-null, no server default)

```python
violation_type: str   # Text NOT NULL
severity: int         # Integer NOT NULL
description: str      # Text NOT NULL
applied_at: datetime  # TIMESTAMP(tz) NOT NULL
```

### RewardLog required fields (non-null, no server default)

```python
reward_type: str    # Text NOT NULL
description: str    # Text NOT NULL
awarded_at: datetime  # TIMESTAMP(tz) NOT NULL
```

---

## File Dibuat / Dimodifikasi

### 1. `src/memory/db.py` — DIBUAT (baru)

Session factory async SQLAlchemy dengan `asynccontextmanager`:

- `get_async_engine()` → singleton `AsyncEngine` (asyncpg, port 5433)
- `get_async_session()` → async context manager, commit on success, rollback on error
- DB URL: `postgresql+asyncpg://guinevere_core@localhost:5433/guinevere` (overrideable via `GUINEVERE_DB_URL` env)

### 2. `src/discord/cmd_punishment.py` — DIMODIFIKASI

Tambahan setelah Redis write di `punishment_callback`:

```python
# Persist to DB — graceful degradation: log error but don't crash
try:
    severity_int = int(level[1])  # L1→1, L2→2, ..., L5→5
    description = LEVEL_DESC.get(level, "Punishment recorded.")
    if note:
        description = f"{description} Note: {note}"
    async with get_async_session() as session:
        row = PunishmentLog(
            violation_type=level,
            severity=severity_int,
            description=description,
            applied_at=datetime.now(tz=timezone.utc),
        )
        session.add(row)
    logger.info("punishment_db_written", level=level)
except Exception:
    logger.exception("punishment_db_write_failed", level=level)
```

Import tambahan: `from src.memory.db import get_async_session` dan `from src.memory.models import PunishmentLog`.

### 3. `src/discord/cmd_reward.py` — DIMODIFIKASI

Tambahan setelah Redis write di `reward_callback`:

```python
# Persist to DB — graceful degradation: log error but don't crash
try:
    async with get_async_session() as session:
        row = RewardLog(
            reward_type="manual",
            description=reason,
            awarded_at=datetime.now(tz=timezone.utc),
        )
        session.add(row)
    logger.info("reward_db_written", reason=reason[:50])
except Exception:
    logger.exception("reward_db_write_failed", reason=reason[:50])
```

Import tambahan: `from src.memory.db import get_async_session` dan `from src.memory.models import RewardLog`.

### 4. `tests/discord/test_cmd_punishment_reward.py` — DIBUAT (baru)

8 test cases:

| Test | Coverage |
|---|---|
| `TestPunishmentDBWrite::test_punishment_db_write_called` | DB session.add dipanggil dengan PunishmentLog valid |
| `TestPunishmentDBWrite::test_punishment_db_failure_is_graceful` | DB failure → log error, command tidak crash, embed tetap dikirim |
| `TestPunishmentDBWrite::test_punishment_l6_rejected_no_db_write` | L6 ditolak → tidak ada DB write |
| `TestPunishmentDBWrite::test_punishment_all_valid_levels` | L1-L5 semua valid, severity mapping benar |
| `TestRewardDBWrite::test_reward_db_write_called` | DB session.add dipanggil dengan RewardLog valid |
| `TestRewardDBWrite::test_reward_db_failure_is_graceful` | DB failure → log error, command tidak crash, embed tetap dikirim |
| `TestRewardDBWrite::test_reward_missing_reason_no_db_write` | Reason kosong → tidak ada DB write |
| `TestRewardDBWrite::test_reward_awarded_at_is_utc` | awarded_at timezone-aware UTC |

---

## Hasil Verifikasi

```
$ python3 -m pytest tests/discord/ -q --tb=short -k 'punishment or reward' 2>&1

........                                                                 [100%]
=============================== warnings summary ===============================
...
8 passed, 186 deselected, 1 warning in 4.12s
```

**Semua 8 test baru: PASS. Tidak ada test existing yang fail.**

---

## Safety Notes

- DB write failure ter-catch oleh `try/except Exception` — command Discord tidak crash
- L6+ tetap ditolak sebelum Redis/DB write (safety boundary Y6 PROHIBITED tetap intact)
- Empty reason untuk reward tetap ditolak sebelum DB write
- `applied_at` / `awarded_at` selalu `datetime.now(tz=timezone.utc)` — timezone-aware

---

## Catatan Teknis

- Tidak ada session factory global sebelum M-03 — `src/memory/db.py` dibuat dari scratch
- Pattern mock: `get_async_session` dipatch sebagai fungsi yang mengembalikan async context manager
- `DiscordInteractionProtocol` runtime check membutuhkan `.user` attribute di stub test
- `to_discord_embed` membutuhkan `get_discord_module` dipatch agar tidak bergantung pada discord.py runtime di test
