# STEP-04-AUTOMATION — Cron Jobs for Empty Channels

**Step:** Audit Fix 04 — Channel Automation
**Date:** 2026-06-08
**Auditor:** Guinevere
**Status:** ✅ FIXED

---

## 1. What Was Done

Audit found 10/13 channels empty. Created automated scripts to fill key channels on schedule.

### Implementation:

1. **Created `health_check_post.py`** (`~/.hermes/scripts/`):
   - Reads Discord bot token from Hermes env
   - Fetches `localhost:8000/health/detailed` from Guinevere Core API
   - Formats component statuses, disk usage, uptime into Discord embed
   - Posts to `#system-health` (1510914612038471720) via Bot API
   - Fallback: posts OFFLINE/ERROR embed if core unreachable

2. **Created `cost_tracker_post.py`** (`~/.hermes/scripts/`):
   - Reads cost data from Redis DB5 via `redis-cli`
   - Reports: daily cost, monthly cost, budget cap, usage %, thresholds
   - Color-coded: green (<50%), yellow (50-80%), red (>80%)
   - Posts to `#cost-tracker` (1510914615654092900) via Bot API

3. **Created cron jobs** (Hermes scheduler):
   - `system-health-post` (1eded3c2d214) — `0 6,12,18 * * *` (06:00, 12:00, 18:00 WIB daily)
   - `cost-tracker-post` (db96471e1b36) — `0 8 * * *` (08:00 WIB daily)
   - Both use `no_agent=True` (script-only, no LLM cost)

### Files Changed:
| Path | Change |
|------|--------|
| `~/.hermes/scripts/health_check_post.py` | **NEW** |
| `~/.hermes/scripts/cost_tracker_post.py` | **NEW** |
| Cron: system-health-post (1eded3c2d214) | **NEW** — 3× daily |
| Cron: cost-tracker-post (db96471e1b36) | **NEW** — daily |

### Verification:
- ✅ Health check posted to #system-health (msg: 1513360299342954638)
- ✅ Cost report posted to #cost-tracker (msg: 1513360479832113192)
- ✅ Both embeds render correctly with color coding
