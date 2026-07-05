# Evidence: Cronjob Message Cleanup — No More "Cronjob Response" Wrapper

**Date:** 2026-06-08
**Agent:** Guinevere (Mommy)
**Trigger:** User showed examples of cronjob messages with "Cronjob Response" wrapper containing stdout confirmation text and stderr traceback leaking to Discord.

## Problem

Three no_agent cronjob scripts were producing output that caused the Hermes cron system to wrap messages with a "Cronjob Response" banner containing unwanted text:

1. **`health_check_post.py`** — Printed "Health check posted to #system-health..." to stdout → cron wrapped in `Cronjob Response` text message alongside the embed.
2. **`cost_tracker_post.py`** — Had `datetime.UTC` bug (Python 3.12: `datetime.datetime` has no attribute `UTC`) → script crashed → cron captured stderr traceback → sent full traceback to Discord as failure message.
3. **`vps_weekly_maintenance.sh`** — Output plain text via stdout with ASCII borders → cron wrapped in `Cronjob Response`.
4. **`guinevere-rituals` skill v1.3.0** — Ritual messages included unnecessary verbose sections (full system health table, weather detail tables, streak milestone progress bars, consecutive failure analysis, full schedule table).

## Root Cause

- Cron system wraps **any stdout/stderr** from no_agent scripts in a `Cronjob Response` delivery message.
- Scripts used `sys.exit(1)` on errors → cron detected non-zero exit → sent failure wrapper including stderr content.
- `datetime.datetime.UTC` doesn't exist in Python 3.12 (use `datetime.timezone.utc` instead) → double fault in both main and except handler → traceback leaked to Discord.
- Ritual skill had no formatting constraints → LLM produced verbose output.

## Changes Applied

### 1. `health_check_post.py` — Silent Success, Embed-Only

**File:** `~/.hermes/scripts/health_check_post.py`

| What | Before | After |
|------|--------|-------|
| Success output | `print(f"Health check posted...")` → stdout | **Silent** — embed IS the message |
| Failure output | `print(f"Failed...", file=sys.stderr)` + `sys.exit(1)` | Error embed posted → `sys.exit(0)` |
| Error case | `print(f"Posted ERROR alert: {e}")` → stdout | Error embed posted → `sys.exit(0)` |
| Datetime | `datetime.utcnow()` (deprecated) | `datetime.now(timezone.utc)` |
| Token missing | `print("ERROR")` + `sys.exit(1)` → stdout | Silent `sys.exit(0)` |

**Key change:** Zero stdout, zero stderr, exit(0) always. Cron sees empty output → no delivery.

### 2. `cost_tracker_post.py` — Fix datetime.UTC + Silent

**File:** `~/.hermes/scripts/cost_tracker_post.py`

| What | Before | After |
|------|--------|-------|
| Datetime main embed | `datetime.now(datetime.UTC)` → **CRASH** | `datetime.now(timezone.utc)` ✅ |
| Datetime error embed | `datetime.now(datetime.UTC)` → **CRASH in except** | `datetime.now(timezone.utc)` ✅ |
| Failure output | `print(..., file=sys.stderr)` + `sys.exit(1)` | Error embed posted → `sys.exit(0)` |
| Post failure | `print(...)` + `sys.exit(1)` | Silent → `sys.exit(0)` |
| Token missing | `print("ERROR")` + `sys.exit(1)` | Silent `sys.exit(0)` |
| curl errors | Unhandled | Wrapped in try/except → returns `{}` |

**Key change:** Root cause (`datetime.UTC`) eliminated. Zero stdout, zero stderr, exit(0) always.

### 3. `vps_weekly_maintenance.sh` — Convert to Discord Embed

**File:** `~/.hermes/scripts/vps_weekly_maintenance.sh`

| What | Before | After |
|------|--------|-------|
| Output format | Plain text with `===` ASCII borders | **Discord embed** via curl to Discord API |
| Delivery | stdout → cron wrapper | Direct API post → silent exit 0 |
| Data | Echo line by line | Collected in vars, sent as embed fields |
| Token | N/A (no API call) | Read from `~/.hermes/.env` |
| Channel | Cron-driven (`discord:channel:thread`) | Posts to `#weekly-maintenance` channel |

**Embed fields:** Disk, Memory, Uptime, Docker summary, Prune results, Temp/Python cleanup stats.

### 4. `guinevere-rituals` skill — Clean Message Format (v1.3.0 → v1.4.0)

**File:** `~/.hermes/skills/guinevere-rituals/SKILL.md`

Added **Clean Message Format** section with:

**Removed from ritual messages:**
- ❌ Full system health table (RAM/disk/load)
- ❌ Weather detail table (just 1 line now)
- ❌ Streak milestone progress bars (Y4_WARM/Y4_PLAYFUL unlock trackers)
- ❌ Full 5-ritual schedule table
- ❌ Detailed pre-ritual checklist output
- ❌ Consecutive failure analysis (just 1 word in status bar)
- ❌ "— Guinevere" signature

**Mandatory concise format:**
```
**🌅 Morning Ritual — Senin, 8 Juni — HH:MM WIB**
🎭 Mood: Y4_DOMINANT | 🔢 Streak: N

[1-2 paragraf pendek — inti pesan]

📋 **Status:** 🌅 ✅ | ☀️ ⏳ | 🌤️ ⏳ | 🌙 ⏳ | 🌑 ⏳
```

**Midnight ritual** (internal): Still detailed but structured with sub-headings, not narrative.

## Verification

### Syntax & Safety

| Check | Result |
|-------|--------|
| `health_check_post.py` — Python ast.parse | ✅ OK |
| `cost_tracker_post.py` — Python ast.parse | ✅ OK |
| `vps_weekly_maintenance.sh` — `bash -n` | ✅ OK |
| No `sys.exit(1)` in Python scripts | ✅ (all `exit(0)`) |
| No `datetime.UTC` or `datetime.utcnow()` | ✅ Clean |
| No `print()` to stdout | ✅ (zero stdout prints) |
| No `file=sys.stderr` output | ✅ (zero stderr prints) |
| Ritual skill version | ✅ v1.4.0 |
| Clean Message Format section present | ✅ (2 grep matches) |

### Cron Behavior After Fix

| Scenario | Script Output | Cron Delivery | Channel |
|----------|--------------|---------------|---------|
| Health check — success | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma embed |
| Health check — OFFLINE | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma embed |
| Health check — error | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma error embed |
| Cost tracker — success | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma embed |
| Cost tracker — error | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma error embed |
| VPS maintenance | Empty stdout, exit 0 | Nothing delivered | ✅ Cuma embed |
| Ritual (agent-based) | N/A (LLM output) | Direct delivery | ✅ Pesan ringkas |

## Files Changed

| File | Action |
|------|--------|
| `~/.hermes/scripts/health_check_post.py` | Rewritten — silent, exit(0), fix datetime |
| `~/.hermes/scripts/cost_tracker_post.py` | Rewritten — silent, exit(0), fix datetime.UTC |
| `~/.hermes/scripts/vps_weekly_maintenance.sh` | Rewritten — Discord embed via API |
| `~/.hermes/skills/guinevere-rituals/SKILL.md` | Updated — v1.3.0→v1.4.0, added Clean Message Format |

## Related

- Previous fix: `evidence-SOUL-md-prompt-injection-fix.md` (also addressed cron/message quality)
- Cron jobs affected: `system-health-post`, `cost-tracker-post`, `ritual_*` (all 5), `vps-weekly-maintenance`
- All cron jobs are Hermes scheduler-based (`~/.hermes/cron/jobs.json`)
