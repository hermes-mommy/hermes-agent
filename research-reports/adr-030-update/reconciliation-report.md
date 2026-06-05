# ADR-030 Redis DB Assignment — Reconciliation Report

**Date**: 2026-06-05  
**Trigger**: StepPrompts audit (Workstream 2 of dual-workstream execution)  
**Decision Rule**: Runtime code is authoritative  

---

## 1. Complete Reconciliation Table

| DB | ADR-030 (v1.0 — original) | Runtime (actual — authoritative) | ADR-035 | Conflict? | Resolution |
|----|---------------------------|----------------------------------|---------|-----------|------------|
| DB0 | Task queue | Rate limiting, persona state, consent grants | — | **Y** | Updated to runtime |
| DB1 | LLM cache | Memory recall (PostgreSQL+pgvector cache) | — | **Y** | Updated to runtime |
| DB2 | Surveillance buffer | Surveillance buffer, consent cache (60s TTL) | DB2=cache for consent gate | **N** (minor) | Expanded to reflect consent cache use |
| DB3 | Sessions / working memory | Agent state (loop state, task metadata) | — | **Y** | Updated to runtime |
| DB4 | Pub/Sub | Hermes session storage, Discord state (2hr TTL, 20-turn limit) | DB4=Hermes session cache | **Y** (MAJOR) | Updated to runtime; ADR-035 consistent |
| DB5 | Rate limiting | Cost tracking, safety plugin state, DNR list, safe word cache | DB5=guinevere_safety plugin state | **Y** (MAJOR) | Updated to runtime; ADR-035 consistent |

**Summary**: 5 of 6 DB assignments had conflicts with original ADR-030. DB2 was the only consistent mapping (surveillance buffer), but even it was expanded to include consent cache usage.

---

## 2. Runtime Evidence by DB

### DB0 — Rate Limiting, Persona State, Consent Grants

| File | Usage |
|------|-------|
| `src/discord/conversational_handler.py` | Rate limiting (10/min/user) via lazy Redis client db=0 |
| `src/discord/hermes_conversational.py` | Rate limiting (10/min/user) via lazy Redis client db=0 |
| `src/discord/cmd_consent.py` | Consent state (`consent:grants` key) db=0 |
| `src/discord/cmd_punishment.py` | Persona punishment FSM state db=0 |
| `src/discord/cmd_reward.py` | Persona reward FSM state db=0 |
| `src/discord/cmd_casual.py` | Persona casual mode toggle db=0 |
| `src/discord/cmd_focus.py` | Persona focus mode (deep/normal/relaxed) db=0 |
| `src/discord/cmd_clear_cache.py` | Flushing DB0 (rate limits + persona cache) |
| `src/hermes_plugins/commands_system/consent.py` | Consent grants REDIS_DB=0 |
| `src/hermes_plugins/commands_high/casual.py` | Casual mode db=0 |
| `src/hermes_plugins/commands_high/focus.py` | Focus mode db=0 |
| `src/hermes_plugins/commands_surveillance/clear_cache.py` | DB0 flush |

### DB1 — Memory Recall

| File | Usage |
|------|-------|
| `src/mcp/tools/redis_tool.py` (docstring) | Maps DB1 as "Memory recall" |
| `tests/mcp/test_redis_tool.py` | Test references for set/get on db=1 |

Minimal runtime usage — primarily a documented allocation for PostgreSQL+pgvector query caching.

### DB2 — Surveillance Buffer, Consent Cache

| File | Usage |
|------|-------|
| `src/surveillance/redis_buffer.py` | Async surveillance event buffer db=2 |
| `src/surveillance/consent_gate.py` | Consent verdict cache db=2 (60s TTL) |
| `src/surveillance/consumer.py` | Event consumer draining db=2 |
| `src/surveillance/replay.py` | Replay detection db=2 |
| `src/surveillance/router.py` | Best-effort event push to db=2 |
| `src/core/main.py` | Core Redis connection db=2 |

### DB3 — Agent State

| File | Usage |
|------|-------|
| `src/mcp/tools/redis_tool.py` (docstring) | Maps DB3 as "Agent state" |

Minimal runtime usage — primarily a documented allocation for agent loop metadata.

### DB4 — Hermes Session Storage, Discord State

| File | Usage |
|------|-------|
| `src/hermes/session_adapter.py` | REDIS_DB=4, 2hr TTL, 20-turn limit, key prefix `hermes:session:` |
| `src/hermes/__init__.py` | Docstring confirms "Redis DB4 storage" |
| `src/discord/cmd_new_session.py` | Session reset using Redis DB4 |
| `src/discord/cmd_history.py` | Session history from Redis DB4 |
| `src/hermes_plugins/commands_high/new_session.py` | Hermes session clear via DB4 |
| `src/hermes_plugins/commands_high/history.py` | Hermes history via DB4 |

### DB5 — Cost Tracking, Safety Plugin State

| File | Usage |
|------|-------|
| `src/loops/cost.py` | Per-loop cost tracking db=5 |
| `src/mcp/cost.py` | MCP tool cost tracker db=5 |
| `src/mcp/budget.py` | Budget enforcement db=5 |
| `src/mcp/tools/brave_search.py` | Search call counter db=5 |
| `src/mcp/tools/context7.py` | Context7 call counter db=5 |
| `src/mcp/tools/exa_search.py` | Exa search call counter db=5 |
| `src/discord/cmd_cost.py` | Cost report from DB5 |
| `src/discord/cmd_budget.py` | Budget read/write from DB5 |
| `src/discord/cmd_cost_alert.py` | Cost alert threshold DB5 |
| `src/hermes_plugins/commands_finance/cost.py` | Hermes cost report DB5 |
| `src/hermes_plugins/commands_finance/budget.py` | Hermes budget DB5 |
| `src/hermes_plugins/commands_finance/cost_alert.py` | Hermes cost alert DB5 |
| `hermes-config/plugins/guinevere_safety/state_manager.py` | Safety FSM state DB5 |
| `hermes-config/plugins/guinevere_safety/plugin.py` | Plugin state DB5 |
| `hermes-config/hooks/hard_stop.py` | Safe word cache DB5 |
| `hermes-config/hooks/dnr_filter.py` | DNR keyword list DB5 |
| `hermes-config/hooks/consent_gate.py` | Consent state DB5 |
| `hermes-config/hooks/_hook_utils.py` | Hook shared Redis (DB5) |
| `src/core/services/monthly_report.py` | Monthly cost report from DB5 |

---

## 3. ADR-035 Cross-Reference

ADR-035 explicitly acknowledged the DB assignment discrepancy (line 146):

> "ADR-030 Redis DB Assignment Conflict: The current Guinevere codebase uses Redis DB4 for session cache and DB2 for consent cache. ADR-030 canonically assigns DB2=Surveillance buffer, DB3=Sessions, DB4=Pub/Sub, DB5=Rate limiting. This pre-existing runtime-vs-ADR discrepancy is documented but not resolved by this ADR. Resolution: ADR-030 should be updated."

ADR-035 also references:
- DB4 for Hermes session cache (consistent with runtime)
- DB5 for safety plugin state (consistent with runtime)
- DB2 for consent cache (consistent with runtime)

---

## 4. redis_tool.py Docstring Mapping

The `src/mcp/tools/redis_tool.py` docstring (lines 13-19) provides its own allocation map which is closer to runtime but has one discrepancy:

```
DB0: Session cache          # Actually: Rate limiter, persona state, consent
DB1: Memory recall          # Consistent with runtime
DB2: Surveillance buffer     # Consistent with runtime
DB3: Agent state            # Consistent with runtime
DB4: Discord state          # Consistent with runtime (Hermes sessions)
DB5: Cost tracking          # Consistent with runtime
```

DB0 shows "Session cache" in the docstring but is actually used for rate limiting, persona state, and consent grants — not sessions. Sessions are on DB4.

---

## 5. Files Modified

| File | Change |
|------|--------|
| `adr/ADR-030-redis-db-assignments.md` | DB assignment table replaced (v1.1). Code reference updated. Revision note added. Version history entry added. |
| `docs/10-governance/17-ADR_Index_v1.0.md` | ADR-030 status updated to `Accepted (Revised 2026-06-05: DB assignments reconciled with runtime)` in both Decision Map and ADR Register. |
| `docs/10-governance/decisions-log.md` | Entry #004 added. Last-updated date changed to 2026-06-05. |

**Files NOT modified** (per scope):
- `adr/ADR-035-hermes-migration.md` — other workstream
- All `src/` Python files — runtime code unchanged
- `src/mcp/tools/redis_tool.py` — docstring has minor DB0 discrepancy but task scope is documentation-only

---

## 6. Verification Results

```bash
# ADR-030 date present
$ grep -n "2026-06-05" adr/ADR-030-redis-db-assignments.md
96:> **Updated 2026-06-05**: Redis DB assignments reconciled...
98:### Code Reference (Runtime Authoritative — reconciled 2026-06-05)
167:| 1.1 | 2026-06-05 | Guinevere (Sisyphus) | **Reconciled DB assignments...

# ADR-Index updated
$ grep -n "Revised 2026-06-05" docs/10-governance/17-ADR_Index_v1.0.md
57:| Redis DB0–DB5 canonical assignments | ... | Accepted (Revised 2026-06-05) |
95:| ADR-030 | ... | Accepted (Revised 2026-06-05: DB assignments reconciled with runtime) |...

# decisions-log updated
$ grep -n "2026-06-05" docs/10-governance/decisions-log.md
17:| 004 | 2026-06-05 | ADR-030 Redis DB Assignment Reconciliation |...
21:*Last updated: 2026-06-05*
```

**All verification checks: PASS**

---

## 7. Issues Encountered

None. All three file edits applied cleanly on first attempt. No runtime code was modified.

---

## 8. Rollback / Re-run Safety

- ADR-030 v1.0 content is preserved in v1.1 revision history
- `git checkout` on each modified file reverts to previous state
- No database migrations or runtime changes — purely documentation

---

## 9. Footer

| Field | Value |
|---|---|
| Execution date | 2026-06-05 |
| Executor | Guinevere (Sisyphus-Junior) |
| Task | ADR-030 Redis DB Assignment Reconciliation |
| Scope | Documentation-only (ADR-030, ADR-Index, decisions-log) |
| Runtime changes | None |
| Verification | 3/3 grep checks passed |