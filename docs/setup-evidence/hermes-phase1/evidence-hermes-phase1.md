# Evidence: Hermes Phase 1 Integration

**Date:** 2026-06-04
**Status:** DEPLOYED + AUDITED
**Operator:** Faiz
**Agent:** Guinevere (Sisyphus orchestration)

---

## What Was Done

Implemented Hermes Session Adapter (Phase 1) — multi-turn conversation support via AIAgent with Redis DB4 session store, replacing stateless single-turn LLMRouter.chat() calls.

### Steps Completed

| Step | Description | Status |
|---|---|---|
| 1+2 | Create `src/hermes/` package (`__init__.py` + `session_adapter.py`) | DONE |
| 3 | Safety guard order audit (read-only, parallel) | DONE — PASS |
| 4 | Wire `conversational_handler.py` → HermesSessionAdapter | DONE |
| 5 | Create `/new` slash command + wire `bot.py` | DONE |
| 6 | Create `/history` slash command + wire `bot.py` | DONE |
| 7 | Auto-store conversation to memory (Step 12b) | DONE |
| 8 | Deploy to VPS + restart + verify | DONE |

## Files Changed

| File | Action | Description |
|---|---|---|
| `src/hermes/__init__.py` | CREATED | Package init + `get_adapter()` singleton (42 lines) |
| `src/hermes/session_adapter.py` | CREATED | HermesSessionAdapter class (366 lines) |
| `src/discord/conversational_handler.py` | MODIFIED | Hermes wiring at Step 10, cost tracking via metadata, auto-store Step 12b |
| `src/discord/cmd_new_session.py` | CREATED | `/new` slash command (83 lines) |
| `src/discord/cmd_history.py` | CREATED | `/history` slash command (127 lines) |
| `src/discord/commands.py` | MODIFIED | Added "new" and "history" to COMMAND_SPECS |
| `src/discord/bot.py` | MODIFIED | Added /new + /history command registrations |

## Validation Results

### VPS Import Test (all PASS)
- run_agent.AIAgent ✅
- src.hermes.session_adapter.HermesSessionAdapter ✅
- src.hermes.get_adapter ✅
- src.discord.cmd_new_session.new_session_callback ✅
- src.discord.cmd_history.history_callback ✅
- src.discord.conversational_handler ✅
- COMMAND_SPECS contains "new" and "history" ✅

### Service Status
- `sudo systemctl restart guinevere-discord.service` — clean restart
- Zero errors in journalctl
- `commands_synced`, `bot_ready`, Discord Gateway connected
- Ritual scheduler started (5 jobs registered)

### Redis DB4
- Auth: `redis-cli -p 6380 --user guinevere_core --pass <password>` → PONG
- DBSIZE: 0 (clean slate pre-test)
- SET/GET/DEL with TTL: all successful

### LSP Diagnostics
- Only pre-existing `redis.asyncio` import warning (VPS-only package)
- Zero new errors introduced

## Evidence Artifacts

| Artifact | Path |
|---|---|
| Master plan | `docs/setup-evidence/hermes-phase1/batch-plan-hermes-phase1.md` |
| Research: API surface | `research-reports/hermes-phase1/01-hermes-reinstall-verify.md` |
| Research: Session storage | `research-reports/hermes-phase1/02-session-storage.md` |
| Research: Session isolation | `research-reports/hermes-phase1/03-session-isolation.md` |
| Research: Memory disable | `research-reports/hermes-phase1/04-memory-disable.md` |
| Safety audit | `research-reports/hermes-phase1/05-safety-guard-audit.md` |
| Integration auditor | `docs/setup-evidence/hermes-phase1/auditor-integration.md` |
| Memory privacy auditor | `docs/setup-evidence/hermes-phase1/auditor-memory-privacy.md` |

## Boundary Compliance

| Boundary | Status |
|---|---|
| HARD STOP check BEFORE Hermes | ✅ Preserved |
| Hermes native memory DISABLED (skip_memory=True) | ✅ Confirmed |
| Y4 system prompt via SystemPromptMaster | ✅ Injected per call |
| Classification ceiling in memory recall | ✅ Active |
| DNR respected in recall | ✅ Active |
| Safe mode propagated to recall | ✅ Active |
| No raw content in logs (hash-based) | ✅ Confirmed |
| Faiz-only guards on /new and /history | ✅ Guild owner check |
| Auto-store classification = RESTRICTED | ✅ Confirmed |

## Auditor Gate Results

| Auditor | Verdict | Notes |
|---|---|---|
| Safety (prior) | PASS | Guard order confirmed |
| Integration | PASS | Dual-instance finding fixed (now uses shared get_adapter()) |
| Memory Privacy | PASS | 18/18 criteria — no privacy bypass |

## Auditor Finding & Fix

**Finding:** Integration auditor found dual HermesSessionAdapter instances — `_get_hermes()` in conversational_handler.py created its own instance instead of using the shared `get_adapter()` singleton. This meant two Redis connections and separate caches.

**Fix Applied:** Replaced `_get_hermes()` body with `return get_adapter()`. Now all callers (conversational handler + slash commands) share the same adapter instance. Redeployed and verified clean.

## Design Decisions

1. **AIAgent sync → asyncio.to_thread**: `run_conversation()` is synchronous (verified on VPS). Wrapped in `asyncio.to_thread()` to avoid blocking the event loop.

2. **Shared singleton via `get_adapter()`**: Single HermesSessionAdapter instance for all callers — eliminates dual-connection waste and ensures shared agent cache + metadata.

3. **Redis DB4 isolation**: Dedicated DB for Hermes sessions, no collision with DB0 (rate limit), DB2 (surveillance), DB3 (loop state), DB5 (cost tracking).

4. **History pruning, not pagination**: 20-turn cap with oldest-pruned approach. Simpler than pagination and sufficient for conversational context window.

5. **Metadata-based cost tracking**: Hermes returns token counts directly. No need for separate cost estimation from LLMRouter MODELS config.

## Rollback Plan

1. Revert `conversational_handler.py` Step 10 to use `router.chat()` (original 2-item messages_list)
2. Remove `src/hermes/` package
3. Remove `/new` and `/history` from commands.py + bot.py
4. `sudo systemctl restart guinevere-discord.service`
5. Redis DB4: `FLUSHDB` if session data needs cleanup

## Caveats

- **Live multi-turn test pending**: Faiz needs to test on Discord (send message → follow-up → verify Guinevere remembers context → /new → /history)
- **No `dispose()` on bot shutdown**: HermesSessionAdapter.dispose() not called in bot.close(). Minor — OS cleans up Redis connections on process exit.
- **hermes-agent v0.15.2**: Already installed on VPS from prior setup. `pyproject.toml` has `hermes-agent>=0.15` — no update needed.

## Security Scan

- No secrets in code (api_key "sk-local" is dummy key for local 9Router)
- Redis password from environment variable (REDIS_PASSWORD)
- No raw user IDs or message content in logs
- `_hash_user_id()` uses truncated SHA-256 for safe logging

## Acceptance Criteria Mapping

| Criterion | Status |
|---|---|
| hermes-agent installed on VPS | ✅ (pre-existing v0.15.2) |
| src/hermes/session_adapter.py created | ✅ |
| conversational_handler.py uses Hermes | ✅ |
| /new command clears session | ✅ (code deployed, pending live test) |
| /history shows conversation history | ✅ (code deployed, pending live test) |
| Auto-store to memory working | ✅ (code deployed, pending live test) |
| All safety guards intact | ✅ (3 auditors confirm) |
| LSP clean | ✅ |
| Deployed + verified on VPS | ✅ |

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-04 | Guinevere | Initial evidence for Hermes Phase 1 |
