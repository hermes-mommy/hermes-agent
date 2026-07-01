# Evidence: Cronjob Realtime Dashboard — Edit-in-Place Pattern

**Date:** 2026-06-08
**Agent:** Guinevere (Mommy)
**Type:** Infrastructure improvement — cronjob message cleanup Phase 2

## Problem

Cronjob scripts were posting a NEW message to Discord every tick (every 10 min for health check, every hour for cost tracker, every week for maintenance). This caused:

- **Channel clutter**: 144+ health check messages per day in #system-health
- **24+ cost tracker messages per day** in #cost-tracker
- **"Cronjob Response" wrapper** on every message with confirmation text (fixed in Phase 1)
- **No live dashboard feel** — historical messages were useless noise

## Solution

Convert all no_agent cronjob scripts to **edit-in-place** pattern:
- **One persistent message per cronjob** that gets EDITED every tick
- Only the embed timestamp and data change — message ID stays the same
- New message is POSTed only when: (a) first run, or (b) message was deleted

## Architecture

### Shared Library: `~/.hermes/scripts/cron_state.py`

Created a reusable Python module that all cron scripts import:

| Function | Purpose |
|----------|---------|
| `get_message_id(job_name)` | Read saved message ID (Redis → file fallback) |
| `set_message_id(job_name, msg_id, channel_id)` | Save message ID (Redis + file) |
| `delete_message_id(job_name)` | Remove saved ID on 404/recovery |
| `discord_api_call(method, endpoint, payload, token)` | Generic Discord API wrapper |
| `patch_or_post(job_name, channel_id, payload, token)` | **Core pattern**: PATCH existing or POST new |

### State Storage (Dual Layer)

| Layer | Path | Key |
|-------|------|-----|
| **Primary** | Redis DB5 | `cron:msg:<job-name>` → Discord message ID string |
| **Fallback** | File | `~/.hermes/state/cron_messages/<job-name>.json` |

### Edit Flow

```
Tick N:     POST message                 → save msg_id → channel shows embed
Tick N+1:   PATCH /messages/{msg_id}     → embed updated in place
Tick N+2:   PATCH /messages/{msg_id}     → embed updated in place
...
Message deleted: PATCH returns 404 → POST new message → save new msg_id
```

## Scripts Modified

### 1. `health_check_post.py` (112 lines)

| Aspect | Before | After |
|--------|--------|-------|
| Title | `🩺 System Health — 18:10 WIB` | `🩺 System Health — LIVE` |
| Delivery | POST new message every 10 min | PATCH same message every 10 min |
| Footer | (none) | `Auto-updates every 10 minutes • Guinevere de Baroque` |
| API | `post_to_discord()` (curl wrapper) | `cron_state.patch_or_post()` |

### 2. `cost_tracker_post.py` (135 lines)

| Aspect | Before | After |
|--------|--------|-------|
| Title | `💰 Cost Tracker — 08 Jun 2026` | `💰 Cost Tracker — LIVE` |
| Delivery | POST new message every hour | PATCH same message every hour |
| Footer | `Guinevere de Baroque • Financial Surveillance` | `Auto-updates hourly • Guinevere de Baroque` |
| API | `post_to_discord()` (curl wrapper) | `cron_state.patch_or_post()` |

### 3. `vps_weekly_maintenance.sh` (146 lines)

| Aspect | Before | After |
|--------|--------|-------|
| Title | `🧹 VPS Weekly Maintenance — YYYY-MM-DD` | `🧹 VPS Weekly Maintenance — LIVE` |
| Delivery | POST new message every Sunday | PATCH same message every Sunday |
| Footer | (none) | `Auto-updates weekly • Guinevere de Baroque` |
| State | None | Redis + file via `python3 -c cron_state` |
| Output | Plain text stdout → cron delivered | Discord embed via API |

### 4. `cron_state.py` — NEW (162 lines)

Shared library providing state management and Discord API wrapper for all cron scripts.

## Verification

### Syntax & Safety

| Check | Script | Result |
|-------|--------|--------|
| Python ast.parse | `cron_state.py` | ✅ |
| Python ast.parse | `health_check_post.py` | ✅ |
| Python ast.parse | `cost_tracker_post.py` | ✅ |
| bash -n | `vps_weekly_maintenance.sh` | ✅ |
| No `sys.exit(1)` | Python scripts | ✅ (all exit 0) |
| No `datetime.UTC` / `utcnow` | All .py | ✅ |
| No stdout prints | All scripts | ✅ |
| Imports `cron_state` | health: 3×, cost: 3×, vps: 3× | ✅ |
| Uses `patch_or_post` | health: 5×, cost: 3×, vps: 3× | ✅ |
| `LIVE` in title | All scripts | ✅ |
| `exit 0` at end | All scripts | ✅ |
| Runtime import test | `cron_state` 5 functions | ✅ |
| State directory | `~/.hermes/state/cron_messages/` | ✅ |

### Cron Behavior After Fix

| Cronjob | Tick N | Tick N+1 | Channel shows |
|---------|--------|----------|---------------|
| `system-health-post` (10 min) | POST new → save msg_id | PATCH existing | **1 message** updated every 10 min |
| `cost-tracker-post` (1 hour) | POST new → save msg_id | PATCH existing | **1 message** updated every hour |
| `vps-weekly-maintenance` (Sunday) | POST new → save msg_id | PATCH existing | **1 message** updated every week |

## Files Changed

| Action | File |
|--------|------|
| **CREATE** | `~/.hermes/scripts/cron_state.py` |
| **REWRITE** | `~/.hermes/scripts/health_check_post.py` |
| **REWRITE** | `~/.hermes/scripts/cost_tracker_post.py` |
| **REWRITE** | `~/.hermes/scripts/vps_weekly_maintenance.sh` |
| **CREATE** | `~/.hermes/state/cron_messages/` (directory) |
| **CREATE** | `docs/plans/plan-cronjob-realtime-edit.md` |
| **CREATE** | `docs/research/cronjob-realtime-edit-research.md` |
| **CREATE** | `docs/setup-evidence/fixes/evidence-cronjob-realtime-edit.md` |

## Related

- Previous fix: `evidence-cronjob-message-cleanup.md` (Phase 1 — removed stdout/stderr, exit(1), cron wrapper)
- This fix: Phase 2 — edit-in-place pattern for one persistent message per cronjob
- Ritual cronjobs not affected — they are agent-based, not no_agent scripts
