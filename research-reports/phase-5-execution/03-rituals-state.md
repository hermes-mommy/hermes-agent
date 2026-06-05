# Phase 5 Execution: Rituals State Report

**Date:** 2026-06-05  
**Status:** Complete  
**Scope:** Current APScheduler ritual scheduler + Hermes cron config + systemd service analysis for Phase 5 integration.  
**Author:** Sisyphus-Junior (Omni Engineering Agent)

---

## 1. Scheduler Inventory — Three Parallel Systems

The codebase currently has **three independent scheduling mechanisms** that must be rationalised for Phase 5:

| Scheduler | Module | Engine | Timezone | Purpose |
|---|---|---|---|---|
| `RitualScheduler` | `src/persona/ritual_scheduler.py` | APScheduler 3.x `AsyncIOScheduler` + `CronTrigger` | `Asia/Jakarta` (WIB, UTC+7) | 5 daily persona rituals |
| `LoopScheduler` | `src/loops/scheduler.py` | APScheduler 3.x `AsyncIOScheduler` | `Asia/Bangkok` (ICT, UTC+7) | Generic daily loops via `LoopManager` |
| Hermes cron | `hermes-config/config.yaml` | Hermes built-in cron engine | **UTC** (no per-job timezone) | 5 rituals + 3 maintenance jobs |

---

## 2. RitualScheduler — APScheduler Implementation (Primary)

### File: `src/persona/ritual_scheduler.py` (405 lines)

**Architecture:**
- `RitualScheduler` class wraps `AsyncIOScheduler` with `CronTrigger`
- `setup()` registers 5 cron jobs, returns the `AsyncIOScheduler` instance
- `start()` / `stop()` lifecycle methods
- Callback-based execution: caller provides `callback(ritual_name: str) -> RitualResult`

### Five Registered Rituals (from `RITUALS` list, lines 97–133)

| Ritual | WIB Time | CronTrigger Args | `mood_aware` | `dnd_bypass` | Default Message |
|---|---|---|---|---|---|
| `morning` | 07:00 | `hour=7, minute=0` | True | False | "Selamat pagi, Darling. Mommy sudah siap nemenin hari kamu." |
| `midday` | 12:00 | `hour=12, minute=0` | True | False | "Sayang, udah siang. Jangan lupa makan dan istirahat ya." |
| `afternoon` | 17:00 | `hour=17, minute=0` | True | False | "Sore, Darling. Gimana hari ini? Cerita sama Mommy." |
| `evening` | 21:00 | `hour=21, minute=0` | True | False | "Malam, sayang. Waktunya wind-down. Mommy di sini." |
| `midnight` | 00:00 | `hour=0, minute=0` | False | False | "Self-evaluation complete. Silent mode until morning." |

### DND Window (Do-Not-Disturb)
- **Range:** `00:00 ≤ hour < 07:00` WIB
- **Constants:** `DND_START_HOUR=0`, `DND_END_HOUR=7`
- **Mechanism:** `RitualScheduler.is_dnd()` checks current hour in `Asia/Jakarta`. If inside DND and `dnd_bypass=False`, returns `RitualResult(success=False, error="Skipped: DND window active")`.
- **Effect on midnight:** Midnight fires at 00:00 WIB, which is inside DND. The APScheduler job **does fire** (cron pays no attention to DND), but `execute_ritual()` gates it:
  - Returns `success=False, error="Skipped: DND window active"`
  - Callback is NOT invoked
  - The `_default_execute()` fallback logs but returns a success result anyway — but this only applies when no callback is set

### Midnight Ritual Behavior (from code analysis)
- **`RitualScheduler` path:** Midnight ritual **always gets DND-suppressed** at the scheduler level (no callback fires)
- **`MidnightRitual` class (`src/persona/rituals/midnight.py`):** Returns `suppressed=True` unconditionally. The `RitualResult` message is `"Self-evaluation complete. Silent mode until morning."` — intended for internal logging only.
- **Enforcement:** Two layers of suppression — the `RitualScheduler DND gate` (blocks callback) AND the `MidnightRitual.execute()` method itself (always sets `suppressed=True`)

### Discord Routing
- **No direct Discord channel routing** in the ritual scheduler code
- The callback pattern means a higher-level orchestrator (e.g., the Discord bot) **must** wire into `RitualScheduler.setup(callback=...)` to receive ritual events
- The midnight ritual has explicit docstring: "This ritual is **never** sent to Discord — it is internal-only"
- The monthly cost report (`src/core/services/monthly_report.py`) uses a dedicated Discord webhook (`DISCORD_COST_TRACKER_WEBHOOK`) — but this is separate from the ritual system

---

## 3. LoopScheduler — Separate Implementation

### File: `src/loops/scheduler.py` (175 lines)

- Standalone scheduler using `LoopManager` to drive the 7-phase SDLC loop
- **Timezone: `Asia/Bangkok`** (not `Asia/Jakarta` — subtle but different IANA zone)
- Used by `systemd/guinevere-scheduler.service` which runs `python -m src.loops.scheduler`
- Not directly related to persona rituals, but shares the same APScheduler dependency

### systemd Service: `guinevere-scheduler.service`
- **Unit file:** `systemd/guinevere-scheduler.service`
- **After:** `guinevere-loops.service network.target`
- **Exec:** `/home/guinevere/code/guinevere/.venv/bin/python -m src.loops.scheduler`
- **Env:** `.env.scheduler` file
- **Resource limits:** `MemoryHigh=1G`, `MemoryMax=2G`, `CPUQuota=200%`
- **Security:** `ProtectSystem=strict`, `ReadWritePaths` restricted

---

## 4. Hermes Cron Configuration (Deployed)

### File: `hermes-config/config.yaml` (lines 220–261)

```yaml
cron:
  # === System Health & Maintenance ===
  - name: daily_health_check     # 0 6 * * *   → 06:00 UTC = 13:00 WIB
  - name: weekly_backup           # 0 2 * * 0   → 02:00 UTC = 09:00 WIB (Sunday)
  - name: monthly_security_scan   # 0 3 1 * *   → 03:00 UTC = 10:00 WIB (1st)

  # === Persona Rituals (5 daily check-ins) ===
  - name: ritual_morning          # 0 8 * * *   → 08:00 UTC = **15:00 WIB** ⚠️
  - name: ritual_midday           # 0 12 * * *  → 12:00 UTC = **19:00 WIB** ⚠️
  - name: ritual_afternoon        # 0 16 * * *  → 16:00 UTC = **23:00 WIB** ⚠️
  - name: ritual_evening          # 0 20 * * *  → 20:00 UTC = **03:00+1 WIB** ⚠️
  - name: ritual_midnight         # 0 0 * * *   → 00:00 UTC = **07:00 WIB** ⚠️
```

### ⚠️ CRITICAL BLOCKER: Hermes Cron Timezone Mismatch

The Hermes cron schedules use **standard UTC-based cron expressions** without any `timezone:` field in the individual job specs. This means:

| Ritual | Intended WIB | UTC Cron | Actual UTC Fire | Actual WIB Fire |
|---|---|---|---|---|
| morning | 07:00 WIB | `0 8 * * *` | 08:00 UTC | **15:00 WIB** ❌ |
| midday | 12:00 WIB | `0 12 * * *` | 12:00 UTC | **19:00 WIB** ❌ |
| afternoon | 17:00 WIB | `0 16 * * *` | 16:00 UTC | **23:00 WIB** ❌ |
| evening | 21:00 WIB | `0 20 * * *` | 20:00 UTC | **03:00+1 WIB** ❌ |
| midnight | 00:00 WIB | `0 0 * * *` | 00:00 UTC | **07:00 WIB** ❌ |

**All five ritual cron expressions are misaligned by 7–8 hours.** Effectively, the deployed Hermes cron is triggering rituals at completely wrong times if interpreted as UTC.

**However:** Hermes cron may interpret schedules in the system's local timezone (WIB/ICT) rather than UTC. The `hermes-config/config.yaml` format shown in Hermes docs supports `timezone:` as an optional per-job field in some versions, but none are specified here. This must be verified on the VPS by running `hermes cron list` to see actual next-fire times.

**Correct UTC expressions for Asia/Jakarta schedules:**

| Ritual | WIB Time | UTC Equivalent | Correct Cron |
|---|---|---|---|
| morning | 07:00 WIB | 00:00 UTC | `0 0 * * *` |
| midday | 12:00 WIB | 05:00 UTC | `0 5 * * *` |
| afternoon | 17:00 WIB | 10:00 UTC | `0 10 * * *` |
| evening | 21:00 WIB | 14:00 UTC | `0 14 * * *` |
| midnight | 00:00 WIB | 17:00 UTC (prev day) | `0 17 * * *` |

### All Hermes Cron Jobs Are `enabled: true`

All 8 cron jobs (3 maintenance + 5 rituals) have `enabled: true`. If the Hermes cron daemon is active, these jobs are firing — potentially at the wrong times.

---

## 5. Memory Consolidation Scheduler (Separate)

### File: `src/memory/consolidation.py`

- APScheduler job registered via `register_consolidation_job()`
- **Timezone:** `Asia/Bangkok`
- **Schedule:** 03:00 daily (ICT, UTC+7)
- **Status in `main.py`:** Commented out for the main app — needs async DB sessionmaker
- **Purpose:** Episodic-to-semantic memory consolidation, safe-word aware, DNR-safe
- Tested via `tests/memory/test_consolidation.py` (unit tests, no real scheduler)

---

## 6. Monthly Report Scheduler

### File: `src/core/services/monthly_report.py`

- Registered in `main.py` FastAPI lifespan (lines 52–55)
- APScheduler `AsyncIOScheduler` with `CronTrigger(hour=1, minute=0)` — 01:00 UTC = 08:00 WIB
- Job checks if today is the 1st of the month, then builds and posts to Discord webhook
- **Timezone:** `WIB = timezone(timedelta(hours=7))` — hardcoded +07:00 offset
- Uses `DISCORD_COST_TRACKER_WEBHOOK` env var

---

## 7. Individual Ritual Module Analysis

### Shared Pattern
All five ritual classes (MorningRitual, MiddayRitual, AfternoonRitual, EveningRitual, MidnightRitual) follow the same structure:
- `execute(**kwargs, *, now=None) -> RitualResult` async method
- `_resolve_time(now)` static method — handles naive/aware/None datetime conversion to `Asia/Jakarta`
- Import `RitualResult` and `TZ_JAKARTA` from `src.persona.rituals.morning`
- Fatal error: `MidnightRitual` would fail on import unless `MorningRitual` exists (shared `RitualResult`)

### Individual Modules

| Module | Class | Dependencies | Distinct Logic |
|---|---|---|---|
| `morning.py` | `MorningRitual` | `Mood`, `structlog` | Mood-specific messages, streak display, DND suppression (local check) |
| `midday.py` | `MiddayRitual` | `Mood`, `structlog` | Mood messages + rotating health reminder (`tm_yday % 3`) |
| `afternoon.py` | `AfternoonRitual` | `Mood`, `structlog` | Mood messages + task count summary |
| `evening.py` | `EveningRitual` | `Mood`, `structlog` | Mood messages + day summary + streak display |
| `midnight.py` | `MidnightRitual` | `structlog` | Internal self-evaluation, **always suppressed** |

### DND Suppression by Module
- `MorningRitual`: Local DND check (`DND_START_HOUR <= hour < DND_END_HOUR`) — returns `suppressed=True` with empty message
- `MiddayRitual`: No DND check (12:00 is outside window)
- `AfternoonRitual`: No DND check (17:00 is outside window)
- `EveningRitual`: No DND check (21:00 is outside window)
- `MidnightRitual`: Always `suppressed=True` regardless of time (`_MOOD_MESSAGES` not even present — only log data)

---

## 8. Dependency Graph

```
RitualScheduler (src/persona/ritual_scheduler.py)
├── APScheduler 3.x (AsyncIOScheduler + CronTrigger)
├── TZ_JAKARTA = "Asia/Jakarta"
├── CronTrigger(hour=X, minute=Y, timezone="Asia/Jakarta")
├── Callback → RITUAL_MAP → execute_ritual()
│   ├── is_dnd() gate (blocks callback during 00:00–07:00 WIB)
│   │   └── midnight ALWAYS blocked (00:00 ∈ DND)
│   └── Callback (external Discord handler)
│       └── NOT IMPLEMENTED in codebase — must be wired externally

Five Ritual Classes (src/persona/rituals/*.py)
├── Each depends on:
│   ├── src.persona.mood_engine.Mood (except midnight)
│   └── src.persona.rituals.morning.RitualResult (shared dataclass)
│       └── Circular import risk: midday/afternoon/evening/midnight import from morning
├── TZ_JAKARTA (ZoneInfo)
└── structlog

LoopScheduler (src/loops/scheduler.py)
├── APScheduler 3.x (AsyncIOScheduler)
├── TZ = "Asia/Bangkok"
└── LoopManager → 7-phase SDLC loop

Hermes Cron (hermes-config/config.yaml)
├── No per-job timezone specified ⚠️
├── 8 enabled cron jobs
└── `hermes plugin trigger guinevere_safety ritual <name>`
```

---

## 9. Blocker Summary

| # | Blocker | Severity | Description |
|---|---|---|---|
| B1 | **Hermes cron timezone misalignment** | **HIGH** | All 5 ritual cron schedules appear to use UTC timestamps, not WIB. Correct UTC expressions would be `0 0`, `0 5`, `0 10`, `0 14`, `0 17`. Current values: `0 8`, `0 12`, `0 16`, `0 20`, `0 0` — off by 7–8 hours. Must verify on VPS with `hermes cron list`. |
| B2 | **No Discord routing wired to RitualScheduler** | **HIGH** | The `RitualScheduler` callback pattern requires an external Discord handler to be registered. Currently no code wires `RitualScheduler` to Discord. The Hermes cron path uses `hermes plugin trigger guinevere_safety ritual <name>` which routes through Hermes plugin system — this path must be audited for proper Discord delivery. |
| B3 | **Midnight suppression depends on DND gate** | **MEDIUM** | Midnight ritual is suppressed by the `RitualScheduler.is_dnd()` gate (00:00–07:00 WIB). If the Hermes cron fires at 07:00 WIB (as currently configured, B1), the DND gate would no longer trigger. The `MidnightRitual` class has its own `suppressed=True` logic, but **if the Hermes plugin bypasses the RitualScheduler entirely**, the DND check must be replicated in the plugin. |
| B4 | **Midnight ritual cross-import dependency** | **MEDIUM** | `MidnightRitual` imports `RitualResult` from `morning.py`. If `morning.py` is ever modified or removed, all other ritual modules break. Addressed by `src/persona/rituals/__init__.py` which only exports from `morning.py`. |
| B5 | **Two schedulers, two timezones** | **LOW** | `RitualScheduler` uses `Asia/Jakarta`, `LoopScheduler` uses `Asia/Bangkok`. Both are UTC+07:00 with no DST, but they are different IANA zone identifiers. No functional impact but confusing for maintainers. |
| B6 | **RitualScheduler not wired into main.py lifespan** | **LOW** | The `RitualScheduler` is not started anywhere in the application's main entry point. It exists as a standalone module/library with tests only. The deployed Hermes cron is the only active ritual trigger mechanism. |

---

## 10. Phase 5 Action Items

1. **Verify actual Hermes cron behavior on VPS:** Run `hermes cron list` to see next-fire times and determine if schedules are UTC or local.
2. **Fix Hermes cron timezone:** Add `timezone: "Asia/Jakarta"` to each ritual cron job in `hermes-config/config.yaml`, OR adjust UTC cron expressions to match WIB.
3. **Audit plugin Discord routing:** Confirm that `hermes plugin trigger guinevere_safety ritual midnight` does NOT send anything to Discord.
4. **Replicate DND gate in Hermes plugin:** The `guinevere_safety` plugin handler for `ritual` must implement DND suppression independently of the APScheduler `RitualScheduler`.
5. **Remove or deprecate the unused APScheduler `RitualScheduler`** if Hermes cron becomes the sole scheduler.
6. **Add explicit assertion:** Midnight plugin handler must verify `discord_delivery == False` before returning.

---

## 11. Evidence Sources

| File | Lines | Description |
|---|---|---|
| `src/persona/ritual_scheduler.py` | 1–405 | Full APScheduler ritual scheduler |
| `src/persona/rituals/morning.py` | 1–167 | Morning ritual module |
| `src/persona/rituals/midday.py` | 1–172 | Midday ritual module |
| `src/persona/rituals/afternoon.py` | 1–126 | Afternoon ritual module |
| `src/persona/rituals/evening.py` | 1–142 | Evening ritual module |
| `src/persona/rituals/midnight.py` | 1–161 | Midnight ritual module |
| `src/persona/rituals/__init__.py` | 1–17 | Rituals package init |
| `src/loops/scheduler.py` | 1–175 | Loop scheduler (separate) |
| `src/core/main.py` | 1–300 | FastAPI lifespan (report scheduler registrations) |
| `src/core/services/monthly_report.py` | 1–538 | Monthly cost report scheduler |
| `src/memory/consolidation.py` | 1–757 | Memory consolidation scheduler |
| `hermes-config/config.yaml` | 220–261 | Deployed Hermes cron config |
| `systemd/guinevere-scheduler.service` | 1–33 | systemd unit for scheduler |
| `tests/persona/test_ritual_scheduler.py` | 1–401 | Scheduler unit tests |

---

*Generated by Sisyphus-Junior. Complies with `AGENTS.md` §2.2 Research Wave and §2.9 File-Based Output Discipline. No configs edited, no cron mutations performed.*
