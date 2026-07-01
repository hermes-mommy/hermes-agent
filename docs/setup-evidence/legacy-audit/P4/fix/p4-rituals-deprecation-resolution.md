# P4 Rituals Deprecation Resolution

**Date:** 2026-06-26
**Status:** DOCUMENTED — deprecated, Hermes cron replaces

---

## Problem

P4-008 through P4-013 (6 modules: ritual_scheduler + 5 rituals) are marked `[x] ✅` in CHECKLIST/PROGRESS but are ALL deprecated Phase 5, scheduled removal Phase 7. Phase 7 never removed them. Deprecation warnings are suppressed in `__init__.py:128-129`.

## Resolution

| Module | P4 Step | Status | Replacement | Documentation Action |
|--------|---------|--------|-------------|---------------------|
| `ritual_scheduler.py` | P4-008 | DEPRECATED | Hermes cron (5 jobs in hermes-config/config.yaml:294-318) | Note added to fix evidence |
| `rituals/morning.py` | P4-009 | DEPRECATED | Hermes cron + PersonaPlugin | Note added |
| `rituals/midday.py` | P4-010 | DEPRECATED | Hermes cron + PersonaPlugin | Note added |
| `rituals/afternoon.py` | P4-011 | DEPRECATED | Hermes cron + PersonaPlugin | Note added |
| `rituals/evening.py` | P4-012 | DEPRECATED | Hermes cron + PersonaPlugin | Note added |
| `rituals/midnight.py` | P4-013 | DEPRECATED | Hermes cron + PersonaPlugin | Note added |

## Hermes Cron Replacement

`hermes-config/config.yaml` lines 294-318 defines 5 cron jobs matching the 5 ritual times:

| Ritual | Time (WIB) | Cron Job Command |
|--------|------------|------------------|
| Morning | 07:00 | `hermes chat -Q -q 'Execute morning ritual'` |
| Midday | 12:00 | `hermes chat -Q -q 'Execute midday ritual'` |
| Afternoon | 17:00 | `hermes chat -Q -q 'Execute afternoon ritual'` |
| Evening | 21:00 | `hermes chat -Q -q 'Execute evening ritual'` |
| Midnight | 00:00 | `hermes chat -Q -q 'Execute midnight ritual'` |

The Hermes cron replacement is stripped-down (simple `hermes chat -Q` calls) compared to the original APScheduler rituals (which had mood-aware greetings, health reminders, DND gating). The PersonaPlugin provides the mood/yandere context for the LLM call, so the ritual prompts have access to persona state through the existing injection pipeline.

## CHECKLIST/PROGRESS Note

CHECKLIST.md and PROGRESS.md should mark these steps as "DEPRECATED — Hermes cron replaces" in a future update. This fix evidence serves as the correction pending that update (shared docs are parent-only per AGENTS.md §2.6).
