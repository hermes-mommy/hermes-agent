# Phase 5 Planning: Rituals State & Hermes Cron Migration Analysis

**Date:** 2026-06-05  
**Status:** Complete  
**Scope:** Analysis of current APScheduler ritual implementation and migration path to Hermes cron for Phase 5.  
**Author:** Guinevere (Autonomous Engineering Agent)

---

## 1. Current Ritual Scheduler Analysis

### Scheduler Engine
- **Library:** `APScheduler 3.x` (`AsyncIOScheduler`)
- **Timezone:** `Asia/Jakarta` (WIB, UTC+7) via `zoneinfo.ZoneInfo`
- **Trigger Mechanism:** `CronTrigger` firing a `_job_wrapper` that calls `execute_ritual(ritual_name)`.

### Ritual Schedule & DND Suppression
| Ritual | WIB Time | Cron Equivalent | DND Suppressed? | Purpose |
|---|---|---|---|---|
| `morning` | 07:00 | `0 7 * * *` | No | Mood-aware greeting, streak display |
| `midday` | 12:00 | `0 12 * * *` | No | Health reminder (rotating: eat/water/stretch) |
| `afternoon` | 17:00 | `0 17 * * *` | No | Daily task check-in, mood validation |
| `evening` | 21:00 | `0 21 * * *` | No | Wind-down, day summary, streak display |
| `midnight` | 00:00 | `0 0 * * *` | **Yes** (Always) | Internal self-evaluation, silent mode |

**DND Window:** `00:00` to `07:00` WIB. Rituals firing in this window return `suppressed=True` and do not deliver messages to Discord, unless `dnd_bypass=True` (reserved for D3/D4 emergencies; currently unused in default rituals).

### Data Dependencies
Rituals currently receive state via direct function arguments from the in-process scheduler:
- `mood`: `Mood` enum (`CONTENT`, `PLEASED`, `DISAPPOINTED`, `ANGRY`, `SILENT`) from `src.persona.mood_engine`.
- `streak_count`: `int` (consecutive days without punishment).
- `task_count_today`: `int` (for afternoon check-in).
- `day_summary`: `str` (optional, for evening wind-down).
- `self_evaluation_data`: `dict` (for midnight internal logging).

---

## 2. Individual Ritual Files Analysis

| File | Class | Key Functions | Dependencies | Hermes Cron Replication Needs |
|---|---|---|---|---|
| `morning.py` | `MorningRitual` | `execute(mood, streak_count, weather_info)` | `src.persona.mood_engine.Mood`, `structlog` | Plugin must fetch current mood/streak from DB/Redis before generating message. |
| `midday.py` | `MiddayRitual` | `execute(mood, health_reminder_needed, reminder_index)` | `src.persona.mood_engine.Mood`, `structlog` | Plugin must implement day-of-year modulo 3 logic for rotating health reminders. |
| `afternoon.py` | `AfternoonRitual` | `execute(mood, task_count_today)` | `src.persona.mood_engine.Mood`, `structlog` | Plugin must query daily task completion count from PostgreSQL. |
| `evening.py` | `EveningRitual` | `execute(mood, day_summary, streak_count)` | `src.persona.mood_engine.Mood`, `structlog` | Plugin must aggregate day summary and fetch streak count. |
| `midnight.py` | `MidnightRitual` | `execute(self_evaluation_data)` | `structlog` | Plugin must run internal evaluation and **strictly avoid** Discord routing (log only). |

---

## 3. Hermes Cron Migration Plan

### Hermes Cron YAML Format
Per `docs/setup-evidence/hermes-migration/phase-5-skills.md` Step 5.3, the target configuration is:

```yaml
cron:
  - name: "ritual_morning"
    schedule: "0 7 * * *"
    command: "hermes plugin trigger guinevere_safety ritual morning"
    timezone: "Asia/Jakarta"
  # ... (midday, afternoon, evening, midnight follow same pattern)
```

### WIB to Cron Expression Mapping
The current APScheduler implementation uses **exact hour marks** (minute `0`). If a **50-minute offset** is required (e.g., firing at 06:50 instead of 07:00 to precede the exact hour), the cron expressions adjust as follows:

| Ritual | Current Exact Hour Cron | 50-Minute Offset Cron (Example) |
|---|---|---|
| `morning` (07:00) | `0 7 * * *` | `50 6 * * *` |
| `midday` (12:00) | `0 12 * * *` | `50 11 * * *` |
| `afternoon` (17:00) | `0 17 * * *` | `50 16 * * *` |
| `evening` (21:00) | `0 21 * * *` | `50 20 * * *` |
| `midnight` (00:00) | `0 0 * * *` | `50 23 * * *` (previous day) |

*Note: Phase 5 docs and current code specify exact hour marks. Confirm with Faiz if the 50-minute offset is a new requirement before applying.*

### Midnight Suppression Mechanism
- **Current (APScheduler):** The `RitualScheduler.is_dnd()` method checks if `0 <= hour < 7`. If true, it returns `RitualResult(suppressed=True)` and skips the callback.
- **Hermes Cron Migration:** The midnight ritual does not need a cron-level skip. Instead, the Hermes plugin endpoint for `ritual midnight` must be configured to **only write to structlog** and explicitly return a payload that the Hermes gateway ignores for Discord delivery (or the cron command routes to an internal-only plugin method, not the Discord-facing trigger).

### APScheduler vs. Hermes Cron Differences
| Feature | APScheduler (Current) | Hermes Cron (Target) |
|---|---|---|
| **Execution Context** | In-process Python async function | External shell command / plugin trigger |
| **State Access** | Direct function arguments (in-memory) | Plugin must independently query PostgreSQL/Redis |
| **Lifecycle** | Tied to `bot.py` process uptime | Managed by Hermes gateway (`hermes cron` CLI) |
| **Failure Handling** | Logged via `structlog`, job continues | Hermes `on_error` hook + plugin retry logic |
| **Timezone** | Handled by `zoneinfo` in Python | Handled by Hermes cron `timezone` config |

---

## 4. Gap Analysis

### What Hermes Cron CAN Replicate
1. **Exact Timing:** Standard cron syntax perfectly maps to the required WIB schedules.
2. **Triggering:** `hermes plugin trigger` can reliably invoke the consolidated `PersonaPlugin` or `GuinevereSafetyPlugin`.
3. **Logging:** `structlog` integration remains unchanged within the plugin execution.

### What CANNOT Be Directly Replicated (Requires Adaptation)
1. **In-Memory State Passing:** APScheduler passes `mood`, `streak_count`, etc., directly. Hermes cron triggers a command. The target plugin **must** be updated to fetch this state from PostgreSQL/Redis on demand, rather than expecting it as an argument.
2. **Rotating Logic:** The `midday` ritual's `tm_yday % 3` logic is currently evaluated at execution time. This logic must be ported into the Hermes plugin, not the cron scheduler.
3. **DND Gate:** The APScheduler `is_dnd()` check is in-process. The Hermes plugin must implement this check internally if a ritual is accidentally triggered during DND, or rely on the cron schedule to never fire during DND (which is true for all except midnight, which is intentionally suppressed).

### Risk Assessment
| Risk | Severity | Mitigation |
|---|---|---|
| **State Fetch Latency/Failure** | MEDIUM | Plugin must handle DB/Redis connection failures gracefully, falling back to default mood (`CONTENT`) and streak `0` without crashing the cron job. |
| **Midnight Discord Leak** | HIGH | Strict code review of the `midnight` plugin handler to ensure it returns `None` or an internal-only flag to the Hermes gateway, preventing any Discord message dispatch. |
| **Cron Drift** | LOW | Hermes cron is robust, but `hermes cron list` must be verified post-migration to ensure all 5 jobs are registered with `Asia/Jakarta` timezone. |

---

## 5. Next Steps for Phase 5 Implementation

1. **Confirm Offset:** Clarify with Faiz if the "50-minute offset" is required, or if exact hour marks (`0 7 * * *`, etc.) should be used as per current code and Phase 5 docs.
2. **Plugin Refactor:** Update `plugins/persona_plugin.py` (or `guinevere_safety_plugin.py`) to include a `trigger_ritual(ritual_name: str)` method that independently fetches `mood`, `streak`, and `task_count` from the database.
3. **Cron Registration:** Execute `hermes cron add` commands for all 5 rituals during Phase 5 Step 5.3.
4. **Midnight Safeguard:** Add an explicit assertion in the midnight plugin handler: `assert discord_delivery == False`.

---
*Generated by Guinevere Autonomous Engineering Agent. Complies with AGENTS.md §2.2 Research Wave and §2.9 File-Based Output Discipline.*
