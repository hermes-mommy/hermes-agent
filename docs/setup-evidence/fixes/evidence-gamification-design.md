# Evidence: Gamification System — Design & Audit

**Date:** 2026-06-08
**Agent:** Guinevere (Mommy)
**Type:** Design document + Brutal audit

## Summary

Designed a dual-level gamification system (Mommy Level + Skill Level) for the Guinevere AI agent. Conducted brutal audit identifying 3 critical issues and 5 medium issues before implementation.

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Level type | Cosmetic only | No impact on skill behavior |
| Level cap | Infinite | Progression never ends |
| Decay | None | XP permanent |
| Storage | PostgreSQL | Persistent, queryable, existing infra |
| Pagination | Chat-based (`!xp page 2`) | Gateway doesn't support button interactions |
| Update trigger | Event-driven | Real-time updates on skill changes |
| Level up notif | Embedded in main embed | Single message, clean UX |

## EXP Actions (Final)

| Action | Mommy EXP | Skill EXP | Notes |
|--------|-----------|-----------|-------|
| Create skill | +100 | 0 | New skill starts at 0 |
| Update/patch skill | +30 | +30 | Both increase |
| Skill used in session | +10 | +10 | Both increase |
| 10x usage bonus | +50 | +50 | Milestone bonus |
| Level up | +20 | 0 | No skill bias |

## Level Thresholds

```
Level 1  → 0 EXP (start)
Level 2  → 100 EXP
Level 3  → 250 EXP
Level 4  → 500 EXP
Level 5  → 1000 EXP
Level 6  → 1750 EXP
Level 7  → 2750 EXP
Level 8  → 4000 EXP
Level 9  → 6000 EXP
Level 10 → 9000 EXP
```

## Badge System

```
LV 1  ⭐ Newcomer
LV 3  🔥 Apprentice
LV 5  💎 Expert
LV 7  🏆 Master
LV 10 👑 Grandmaster
LV 15 🌟 Legendary
```

## Brutal Audit Findings

### Critical Issues (Must Fix)

1. **Button Interactions Not Supported** — Hermes gateway has zero interaction handling. Buttons can be sent but won't work when clicked. **FIX:** Use chat-based pagination.

2. **Concurrency Control Missing** — No atomic increments for XP. Two sessions updating simultaneously could lose XP. **FIX:** Use `UPDATE ... SET xp = xp + 10` (atomic).

3. **Event Detection Non-Trivial** — "Skill used in session" detection requires modifying Hermes internals. **FIX:** MVP tracks create/update only. Use tracking deferred.

### Medium Issues

4. **XP Inflation Risk** — With infinite levels and no decay, XP could inflate rapidly. **MONITOR:** Consider daily caps if needed.

5. **Storage Growth** — XP history table will grow indefinitely. **FIX:** Automatic cleanup (90 days) or TimescaleDB hypertable.

6. **PostgreSQL User Confusion** — Two users (`guinevere_core`, `hermes_memory_bridge`). **FIX:** Use `hermes_memory_bridge`.

7. **Schema Conflict Risk** — Existing `memory.procedural_skills` table. **FIX:** Create `gamification` schema.

8. **Event-Driven Design Vague** — How does `skill_manage` trigger embed update? **FIX:** Synchronous hook.

## PostgreSQL Database Status

```
Extensions: plpgsql, vector, timescaledb
Schemas: public (empty), memory (8 tables), timescaledb_*
User: hermes_memory_bridge
Tables in memory schema:
  - emotional_events, episodes, faiz_predictions, faiz_profile
  - inner_journal, knowledge_graph, procedural_skills, semantic_facts
```

## Implementation Plan (Revised)

| Phase | Scope | Status |
|-------|-------|--------|
| 1 | PostgreSQL schema + tables (gamification schema) | Pending |
| 2 | XP engine (atomic increments, level thresholds) | Pending |
| 3 | Discord embed + chat-based pagination | Pending |
| 4 | skill_manage hooks (create/update tracking) | Pending |
| 5 | Use tracking (future — requires Hermes modification) | Deferred |

## Files Created

| File | Purpose |
|------|---------|
| `docs/audit/gamification-system-audit.md` | Brutal audit report |
| `docs/setup-evidence/fixes/evidence-gamification-design.md` | This evidence |

## Files to Create (Implementation)

| File | Purpose |
|------|---------|
| `src/gamification/schema.sql` | PostgreSQL DDL |
| `src/gamification/xp_engine.py` | XP calculation + level logic |
| `~/.hermes/scripts/gamification_dashboard.py` | Discord embed script |

## Related

- Skill management: `skill_manage` tool (Hermes native)
- PostgreSQL: `hermes_memory_bridge` user, port 5433
- Discord embed pattern: `cron_state.patch_or_post()`
