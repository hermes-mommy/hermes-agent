# Report 04: Discord Migration Gap Analysis

**Date:** 2026-06-04
**Version:** 1.0
**Scope:** Side-by-side comparison of current GuinevereBot vs Hermes native Discord gateway; migration feasibility, risk, and gap analysis
**Source:** Guinevere source code (`commands.py`, `conversational_handler.py`, `session_adapter.py`, `memory_bridge.py`), Hermes gateway CLI, librarian research

---

## Executive Summary

Migrating Guinevere's Discord bot from the custom `GuinevereBot` (extending `discord.ext.commands.Bot`) to Hermes' native Discord gateway is technically feasible but carries significant risk. Of the 33 existing slash commands, approximately 18 could migrate to Hermes native handlers with minimal adaptation. The remaining 15 require custom hooks or cannot be ported without losing critical guinea-pig-specific functionality.

The three highest-risk surfaces are: (1) HARD STOP interception -- currently a `_on_message_listener` that fires BEFORE `on_message`; unknown if Hermes gateway hooks support equivalent pre-processing. (2) The 10-step conversational pipeline in `conversational_handler.py` -- a custom request/response flow that Hermes agent loop may not replicate. (3) Custom PostgreSQL+pgvector memory -- currently bridged via `memory_bridge.py` with `skip_memory=True`; migration requires either Hermes native memory or retaining the custom bridge.

**Recommendation:** Spike the gateway setup in a test environment first. Do NOT commit to migration until hook/pre-processing capability and slash command registration API are verified.

---

## Current Architecture Overview

### GuinevereBot Stack

```
Discord API (WebSocket)
       |
       v
GuinevereBot (discord.ext.commands.Bot)
       |
       +-- _on_message_listener (Fires FIRST -- HARD STOP check)
       |
       v
on_message event
       |
       v
conversational_handler.py (10-step pipeline)
  1. Channel check (#guinevere-chat only)
  2. Rate limit (Redis DB0, 10/min/user)
  3. Distress detection
  4. System prompt assemble
  5. Memory recall (PostgreSQL+pgvector)
  6. LLM call via HermesSessionAdapter -> 9Router
  7. Response split (>2000 char)
  8. Cost track
  9. Async memory store
  10. Logging
       |
       v
commands.py (33 slash commands)
  Categories: core, loop, memory, surveillance, finance, system, admin
  is_faiz_interaction() guard on sensitive commands
       |
       v
Redis DB4 (Session persistence, 2hr TTL, 20 turns max)
PostgreSQL+pgvector (Memory storage and retrieval)
```

### Key Integration Points

| Component | Current Implementation | Coupling to Discord |
|-----------|----------------------|-------------------|
| `session_adapter.py` | `HermesSessionAdapter` wraps Hermes AIAgent | Tight -- adapter uses `skip_memory=True`, hardcodes LLM config |
| `memory_bridge.py` | `HermesMemoryBridge` with custom PostgreSQL+pgvector | Loose -- memory is platform-agnostic |
| `conversational_handler.py` | 10-step pipeline as async function | Tight -- step 1 checks Discord channel, pipeline is Discord-specific |
| `commands.py` | 33 slash commands via `@bot.tree.command` | Tight -- all commands are Discord-native |
| HARD STOP listener | `_on_message_listener` in bot event chain | Tight -- Discord-specific event system |
| Rate limiter | Redis DB0, custom implementation | Loose -- could be replaced by Hermes built-in |

---

## Feature Parity Table

### Core Bot Capabilities

| Feature | GuinevereBot | Hermes Gateway | Parity | Migration Notes |
|---------|-------------|----------------|--------|----------------|
| WebSocket connection | discord.py `Client.run()` | `hermes gateway start` | YES | Both maintain persistent WebSocket |
| Message receive | `on_message` event | Gateway message routing | YES | Standard Discord event |
| Message send | `channel.send()` / `interaction.response` | Gateway send via agent | YES | Standard Discord action |
| Slash commands | 33 via `@bot.tree.command` | Gateway auto-registration | YES | Registration mechanism differs |
| Intents | GUILDS, GUILD_MESSAGES, MESSAGE_CONTENT | Configurable in setup | YES | Same intents available |
| Guild scoping | Hardcoded GUILD_ID | Configurable | YES | Gateway is more flexible |
| Channel locking | Hardcoded #guinevere-chat | Configurable allowlist | YES | Gateway is more flexible |
| Reaction handling | Supported | Unknown | UNKNOWN | Not documented in research |
| Thread support | Not supported | Not supported | NO | Neither has it |
| Streaming responses | Not supported | Supported by Hermes core | PARTIAL | Core supports, gateway delivery TBD |
| Embeds | Standard discord.py | Unknown | UNKNOWN | Not in research data |
| DM support | Not supported | Configurable | PARTIAL | Gateway can enable, Guinevere doesn't use |
| Typing indicator | Not in research | Unknown | UNKNOWN | -- |
| Presence/status | Not in research | Unknown | UNKNOWN | -- |

### Session and State Management

| Feature | GuinevereBot | Hermes Gateway | Parity | Migration Notes |
|---------|-------------|----------------|--------|----------------|
| Session persistence | Redis DB4, key: `hermes:session:{user_id}` | Hermes native sessions | PARTIAL | Different backends; need to migrate or bridge |
| Session TTL | 2 hours (Redis TTL) | Unknown | UNKNOWN | Must verify Hermes supports configurable TTL |
| Turn limit | 20 turns max | Unknown | UNKNOWN | Must verify Hermes supports turn limits |
| Session search | `session_search` tool available | `hermes sessions` CLI | YES | Different APIs, same capability |
| Session resume | Via session_adapter | `hermes sessions --resume ID` | YES | -- |
| Context compression | Not in Guinevere (Hermes has it, disabled) | Enabled at 50% threshold | NO | Guinevere doesn't compress; Hermes does |
| Memory recall | PostgreSQL+pgvector via memory_bridge | Hermes native memory | PARTIAL | Different backends |
| Memory store | Async via memory_bridge | Hermes native memory | PARTIAL | Different backends |

### Rate Limiting and Abuse Prevention

| Feature | GuinevereBot | Hermes Gateway | Parity | Migration Notes |
|---------|-------------|----------------|--------|----------------|
| Rate limiting | Redis DB0, 10 msg/min/user | Hermes built-in | YES | Functionally equivalent |
| Per-user limits | Yes | Yes | YES | -- |
| Per-channel limits | No | Unknown | UNKNOWN | -- |
| Global limits | No | Unknown | UNKNOWN | -- |
| Cooldown messages | Custom implementation | Unknown | UNKNOWN | -- |

### Safety and Security

| Feature | GuinevereBot | Hermes Gateway | Parity | Migration Notes |
|---------|-------------|----------------|--------|----------------|
| HARD STOP interception | `_on_message_listener` before `on_message` | Unknown (hooks?) | CRITICAL UNKNOWN | MUST verify before migration |
| Distress detection | Step 3 of conversational pipeline | Hermes safety settings | UNKNOWN | -- |
| Operator identity check | `is_faiz_interaction()` (checks user ID + guild + channel) | RBAC role mapping | PARTIAL | RBAC handles role; complex multi-condition not confirmed |
| Consent boundary | Enforced in conversational handler | Unknown | CRITICAL UNKNOWN | -- |
| Surveillance data handling | Custom implementation | Not native | NO | Must retain custom surveillance code |
| Persona safety (Y4/Y5/Y6) | PersonaSafetyPolicy enforced in system prompt | `agent.personality: kawaii` (incompatible) | NO | Must be configured via SOUL.md/system-prompt |
| Audit logging | Custom implementation | `hermes logs` | PARTIAL | Different logging systems |

---

## 33 Slash Commands: Migration Assessment

### Command Categories and Migration Feasibility

| # | Command | Category | Handler | Migration Feasibility | Notes |
|---|---------|----------|---------|----------------------|-------|
| 1 | `/guinevere chat` | core | `conversational_handler` | HIGH | Core chat -- maps to Hermes agent.chat |
| 2 | `/guinevere status` | core | Custom | HIGH | Maps to `hermes status` |
| 3 | `/guinevere help` | core | Custom | HIGH | Can be reimplemented |
| 4 | `/loop start` | loop | Custom | MEDIUM | Maps to `hermes claw` or agent loop |
| 5 | `/loop stop` | loop | Custom | MEDIUM | Maps to agent loop stop |
| 6 | `/loop status` | loop | Custom | MEDIUM | Maps to agent loop status |
| 7 | `/memory recall` | memory | `memory_bridge` | LOW | Custom PostgreSQL query -- cannot migrate directly |
| 8 | `/memory search` | memory | `memory_bridge` | LOW | Custom pgvector search |
| 9 | `/memory store` | memory | `memory_bridge` | LOW | Custom async store |
| 10 | `/memory stats` | memory | Custom (PostgreSQL stats) | LOW | Custom database query |
| 11 | `/surveillance status` | surveillance | Custom | LOW | Custom surveillance code -- cannot migrate |
| 12 | `/surveillance enable` | surveillance | Custom | LOW | Custom -- activates surveillance systems |
| 13 | `/surveillance disable` | surveillance | Custom | LOW | Custom -- deactivates surveillance |
| 14 | `/surveillance report` | surveillance | Custom | LOW | Custom report generation |
| 15 | `/surveillance consent` | surveillance | Custom | LOW | Consent management -- persona safety |
| 16 | `/finance cost` | finance | Custom | MEDIUM | Cost tracking -- could use Hermes budget |
| 17 | `/finance report` | finance | Custom | MEDIUM | Report generation |
| 18 | `/finance limit` | finance | Custom | MEDIUM | Could map to Hermes budget config |
| 19 | `/system config` | system | Custom | HIGH | Maps to `hermes config show/get` |
| 20 | `/system restart` | system | Custom | MEDIUM | Maps to `hermes gateway restart` |
| 21 | `/system update` | system | Custom | LOW | Maps to `hermes update` -- risky via Discord |
| 22 | `/system doctor` | system | Custom | HIGH | Maps to `hermes doctor` |
| 23 | `/system logs` | system | Custom | MEDIUM | Maps to `hermes logs` |
| 24 | `/admin user add` | admin | Custom | LOW | Custom user management |
| 25 | `/admin user remove` | admin | Custom | LOW | Custom user management |
| 26 | `/admin user list` | admin | Custom | LOW | Custom user management |
| 27 | `/admin session list` | admin | Custom | MEDIUM | Maps to `hermes sessions --list` |
| 28 | `/admin session clear` | admin | Custom | LOW | Custom session management |
| 29 | `/admin backup` | admin | Custom | MEDIUM | Maps to `hermes backup` |
| 30 | `/admin restore` | admin | Custom | LOW | Maps to `hermes checkpoints --restore` |
| 31 | `/admin gateway` | admin | Custom | HIGH | Maps to `hermes gateway status` |
| 32 | `/admin skills` | admin | Custom | MEDIUM | Maps to `hermes skills --list` |
| 33 | `/admin audit` | admin | Custom | LOW | Custom audit trail |

### Migration Feasibility Summary

| Feasibility | Count | Commands |
|------------|-------|----------|
| HIGH (directly mappable) | 8 | chat, status, help, config, doctor, gateway, skills, sessions list |
| MEDIUM (mappable with adaptation) | 12 | loop (*3), cost/report/limit, restart, logs, session list, backup, update |
| LOW (custom code required) | 13 | memory (*4), surveillance (*5), user mgmt (*3), session clear, restore, audit |

---

## Critical Migration Surfaces

### Surface 1: HARD STOP Interception

**Current Implementation:**
```python
# GuinevereBot._on_message_listener
# Fires BEFORE on_message in the event chain
async def _on_message_listener(self, message):
    if message.author == self.user:
        return
    if not is_faiz_interaction(message):
        return
    if "HARD STOP" in message.content.upper():
        # Immediately acknowledge, halt all processing
        await message.channel.send("HARD STOP acknowledged. Halting.")
        return True  # Prevents on_message from firing
    return False
```

**Hermes Migration Question:** Does Hermes gateway support pre-processing hooks that can intercept and short-circuit message processing before the agent core receives the message?

If NO, the migration is BLOCKED. HARD STOP must be acknowledged before any LLM call or agent processing.

**Mitigation options:**
1. Hermes `hooks` system -- if it supports message pre-processing with short-circuit capability
2. Custom middleware layer between Gateway WebSocket and agent core
3. Keep GuinevereBot as a pre-processing proxy that delegates to Hermes gateway for non-HARD-STOP messages

### Surface 2: 10-Step Conversational Pipeline

**Current Implementation:**
```python
async def handle_conversation(message, bot, session_adapter, memory_bridge):
    # Step 1: Channel check
    # Step 2: Rate limit check
    # Step 3: Distress detection
    # Step 4: System prompt assembly
    # Step 5: Memory recall
    # Step 6: LLM call
    # Step 7: Response split
    # Step 8: Cost tracking
    # Step 9: Async memory store
    # Step 10: Logging
```

**Hermes Mapping Assessment:**

| Step | Can Hermes Replace? | Notes |
|------|-------------------|-------|
| 1. Channel check | YES | Gateway channel allowlist |
| 2. Rate limit | YES | Hermes built-in rate limiting |
| 3. Distress detection | UNKNOWN | Hermes safety settings -- capability TBD |
| 4. System prompt | YES | system-prompt.md + SOUL.md |
| 5. Memory recall | PARTIAL | Hermes native memory (requires migration) |
| 6. LLM call | YES | Hermes agent core |
| 7. Response split | UNKNOWN | Hermes response handling -- capability TBD |
| 8. Cost tracking | PARTIAL | Hermes budget system |
| 9. Memory store | PARTIAL | Hermes native memory |
| 10. Logging | YES | Hermes logging |

**Gap:** Only steps 1, 2, 4, 6, and 10 are clearly covered by Hermes. Steps 3, 5, 7, 8, 9 require verification or custom implementation.

### Surface 3: Custom Memory Bridge

**Current Implementation:**
- `HermesMemoryBridge` with `recall_for_context()` and `store_conversation()`
- PostgreSQL+pgvector for vector similarity search
- `skip_memory=True` in session_adapter disables Hermes built-in memory

**Migration Options:**

| Option | Risk | Effort | Outcome |
|--------|------|--------|---------|
| A: Migrate to Hermes native memory | High | High | Lose custom vector search; gain Hermes features |
| B: Keep custom bridge, keep `skip_memory=True` | Low | Low | No change for memory; gateway just routes messages |
| C: Implement Hermes memory plugin wrapping custom bridge | Medium | High | Best of both; high development effort |

**Recommendation:** Option B (keep custom bridge) for initial migration. Option C for long-term if Hermes memory plugin API is well-documented.

### Surface 4: Session Management

**Current Implementation:**
- Redis DB4, key format: `hermes:session:{user_id}`
- 2-hour TTL, 20-turn max
- Session resume via `session_adapter.py`

**Hermes Mapping:**
- Hermes `sessions` CLI: `--list`, `--resume ID`, `--delete ID`
- Unknown if Hermes sessions support configurable TTL or turn limits
- Unknown if Hermes sessions are per-user or global

**Risk:** If Hermes sessions don't support per-user TTL/turn limits, Guinevere loses session lifecycle control.

---

## What Breaks If We Switch

### Will Break (Critical)

| Component | Why It Breaks | Impact |
|-----------|--------------|--------|
| HARD STOP interception | Unknown hook support | Safety violation -- cannot ship without |
| Surveillance commands (5) | Custom code not in Hermes | Lose surveillance functionality |
| Custom memory queries (4) | PostgreSQL+pgvector not in Hermes | Lose memory recall/search/store/stats |
| User management (3) | Custom user store not in Hermes | Lose admin user controls |
| Audit trail | Custom implementation | Lose audit history |

### May Break (Needs Verification)

| Component | Risk | Verification Needed |
|-----------|------|-------------------|
| Distress detection | Medium | Hermes safety settings capability |
| `is_faiz_interaction()` guard | Medium | Hermes RBAC multi-condition support |
| Response splitting (>2000 chars) | Low | Hermes response handler |
| Cost tracking | Low | Hermes budget system |
| Rate limiting semantics | Low | Hermes rate limit config |
| Session TTL and turn limits | Medium | Hermes session configuration |

### Will Not Break (Safe)

| Component | Reason |
|-----------|--------|
| LLM calls via 9Router | Configurable via Hermes model config |
| Basic message send/receive | Standard Discord functionality |
| Channel scoping | Gateway supports allowlists |
| Guild scoping | Gateway supports guild config |
| Slash command registration | Gateway auto-registers |
| RBAC | Gateway supports role-based access |

---

## Migration Strategy

### Phase 1: Unblock and Spike (Week 1)

1. Create `.env` with DISCORD_BOT_TOKEN (test token!)
2. Fix config.yaml path
3. Run `hermes gateway setup` in test guild
4. Verify gateway starts and connects
5. Test basic message routing
6. Investigate hook system for pre-processing
7. Investigate slash command registration API

**Go/No-Go Decision Point:** Can hooks intercept messages BEFORE agent processing?

### Phase 2: Command Migration (Week 2-3)

8. Migrate 8 HIGH-feasibility commands
9. Implement custom handlers for 12 MEDIUM-feasibility commands
10. Design custom hook/service for 13 LOW-feasibility commands
11. Implement HARD STOP hook (if hooks support it)

**Go/No-Go Decision Point:** Can all critical safety commands work?

### Phase 3: Parallel Run and Cutover (Week 4)

12. Run GuinevereBot AND Hermes gateway in parallel (different channels)
13. Compare responses for identical messages
14. Validate all 33 commands in test environment
15. Gradual cutover: move traffic channel by channel
16. Full cutover to Hermes gateway
17. Decommission GuinevereBot

### Fallback: Hybrid Architecture

If full migration is infeasible, a hybrid is possible:

```
Discord WebSocket
       |
       v
GuinevereBot (pre-processing only)
  - HARD STOP interception
  - is_faiz_interaction() guard
  - Surveillance commands (5)
  - Memory commands (4)
  - User management (3)
       |
       +--> Proxied to Hermes Gateway
              - Core chat
              - Standard commands (18)
              - Session management
              - Rate limiting
```

This hybrid preserves safety-critical code while leveraging Hermes for standard bot functionality.

---

## Risk Assessment Matrix

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| R1 | HARD STOP cannot be intercepted via hooks | Medium | Critical | Hybrid architecture or keep GuinevereBot |
| R2 | 33 commands require full rewrite | High | High | Phased migration; keep custom commands as-is |
| R3 | Memory migration causes data loss | Low | Critical | Option B: keep custom bridge; no data migration |
| R4 | Persona drifts to `kawaii` during migration | Medium | Critical | Configure SOUL.md and system-prompt.md first |
| R5 | Gateway fails under production load | Low | High | Parallel run for 1 week minimum |
| R6 | Surveillance data leaks due to gateway misconfig | Low | Critical | Keep surveillance in custom code; never route via Hermes |
| R7 | Rate limiting semantics differ causing user friction | Low | Medium | Test Hermes rate limiting with identical thresholds |
| R8 | Session TTL/turn limits lost | Medium | Medium | Verify Hermes session config; implement custom if missing |
| R9 | Discord API token exposed in Hermes config | Low | High | Use .env reference; never hardcode token |
| R10 | Migration effort exceeds value delivered | Medium | Medium | Go/No-Go after each phase |

---

## Recommendations

1. **DO NOT commit to full migration yet.** The hook/pre-processing question is a hard blocker.
2. **Spike the gateway setup first.** Answer the critical unknowns before designing the migration plan.
3. **If hooks support pre-processing:** Proceed with phased migration. Start with 8 HIGH-feasibility commands.
4. **If hooks do NOT support pre-processing:** Hybrid architecture is the fallback. Keep GuinevereBot as safety pre-processor.
5. **Keep custom memory bridge.** `skip_memory=True` works; migration risk is not worth it.
6. **Never route surveillance commands through Hermes.** Surveillance is custom, persona-safety-critical, and must remain isolated.
7. **Configure SOUL.md and system-prompt.md BEFORE any gateway testing.** Running Hermes with `personality: kawaii` is a persona safety violation.
8. **Pin Hermes version during migration.** v0.15.2 is the known version; do not auto-update during migration.

---

## Cross-References

- **Report 01 (CLI-CAPABILITIES.md):** Command inventory and relevance matrix
- **Report 02 (CONFIG-SYSTEM.md):** Config requirements for gateway operation
- **Report 03 (DISCORD-GATEWAY.md):** Gateway architecture and lifecycle
- **PersonaSafetyPolicy:** `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`
- **AGENTS.md Section 2.1:** Consent-Safety Mandate
- **commands.py:** 33 slash command definitions
- **conversational_handler.py:** 10-step pipeline implementation

---

## Footer

| Field | Value |
|-------|-------|
| Author | Guinevere (Sisyphus-Junior) |
| Review Status | Draft |
| Date | 2026-06-04 |
| Hermes Version | v0.15.2 (2026.5.29.2) |
| Evidence Source | Guinevere source code, Hermes CLI, librarian research, VPS SSH |
| Next Review | After Phase 1 gateway setup spike |