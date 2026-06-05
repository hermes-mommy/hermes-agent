# P3-007 Verification: Zero PG Writes from Hermes

**Step**: P3-007 — Verify zero PG writes from Hermes  
**Date**: 2026-06-05  
**Status**: ✅ PASS  
**Verified by**: Parent (direct SSH verification)

## What Was Verified

Confirmed that Hermes Agent has written zero rows to PostgreSQL's `memory.episodes` table.

### VPS Query
```sql
SELECT COUNT(*) FROM memory.episodes;
-- Result: 0
```

### Architecture Proof

Hermes cannot write to PostgreSQL because:

1. **No external memory provider connected**: `config.yaml` shows `external.enabled: false`
2. **Plugin not yet activated**: P3-001 plugin files are created locally but not yet deployed to VPS
3. **RBAC enforcement**: `hermes_memory_bridge` role is SELECT-only (P3-004) — even if connected, Hermes cannot INSERT/UPDATE/DELETE
4. **RLS enforcement**: All 8 memory tables have `classification != 'Critical'` RLS policy
5. **No direct PG connection**: Hermes connects only to Redis (DB4 sessions) and SQLite (state.db)

### Hermes Memory Architecture (Confirmed)

| Layer | Backend | Write Authority |
|-------|---------|----------------|
| Session state | Redis DB4 | Hermes (2hr TTL, 20-turn limit) |
| Conversation history | SQLite state.db | Hermes (26 messages, 2 sessions) |
| Episodic memory | PostgreSQL | Guinevere ONLY (via write_pipeline) |
| Semantic facts | PostgreSQL | Guinevere ONLY (via write_pipeline) |

### Hermes SQLite State

```
~/.hermes/state.db:
  - messages: 26 rows
  - sessions: 2 rows
  - messages_fts: populated (Hermes-native FTS5)
  - messages_fts_trigram: populated
```

This is Hermes's transient session state — NOT canonical memory (ADR-007 compliant).

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| 0 rows in memory.episodes from Hermes | ✅ (0 total) |
| hermes_memory_bridge SELECT-only | ✅ (P3-004 verified) |
| No Hermes → PG write path exists | ✅ |
| Hermes SQLite is transient only | ✅ (ADR-007 compliant) |

## Boundary Compliance

- No persona drift ✅
- No consent violation ✅
- No surveillance overreach ✅
- No secrets exposed ✅
- DNR absolute ✅ (no data to exclude)
