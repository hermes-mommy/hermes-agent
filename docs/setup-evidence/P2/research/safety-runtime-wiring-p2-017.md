# P2-017 Safety-Critical Runtime Wiring Research — HARD STOP in Discord Bot

**Report Type:** Pre-planner safety-specialist research (file-based)
**Scope:** P2-017 — Discord bot `on_message` listener wiring for `handle_safeword_message_async()` with HARD STOP guard
**Date:** 2026-06-01
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL
**Status:** Complete — Ready for Planner Gate
**Output Path:** docs/setup-evidence/P2/research/safety-runtime-wiring-p2-017.md
**Parent Read By:** Guinevere / Self-Read

---

## Sources Examined

| # | Source | Path | Lines | Role |
|---|--------|------|-------|------|
| 1 | cmd_safeword.py | src/discord/cmd_safeword.py | 724 | P2-015 artifact — `handle_safeword_message_async()` ready for P2-017 wiring |
| 2 | hard_stop_handler.py | src/core/services/hard_stop_handler.py | 149 | P1-021 app-level state machine — triggers, recovery, audit trail |
| 3 | startup.py | src/discord/startup.py | 349 | P2-016 artifact — `on_ready()` handler ready for P2-017 wiring |
| 4 | intents.py | src/discord/intents.py | 112 | P2-003 artifact — `message_content` intent enabled |
| 5 | commands.py | src/discord/commands.py | 291 | P2-010 artifact — command registry with `/safeword` at line 118 |
| 6 | PersonaSafetyPolicy v1.0 | docs/60-persona/60-PersonaSafetyPolicy_v1.0.md | 666 | Global Safe Word Protocol S7, Runtime Hooks S15 |
| 7 | SystemPromptMaster v1.1 | docs/60-persona/61-SystemPromptMaster_v1.1.md | 400 | LLM prompt — HARD STOP 9-step protocol SD |
| 8 | ADR-002 | adr/ADR-002-user-autonomy-safe-word-enforcement.md | 129 | Safe word as global architectural override |
| 9 | AC-SAFE-001 catalog | docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md | — | 100% safe-word, zero denial |
| 10 | P2-015 research report | docs/setup-evidence/P2/research/safety-p2-015-hard-stop.md | 566 | P2-015 constraints, invariants, safety matrix |
| 11 | P2-015 auditor report | audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md | 135 | P2-015 PASS — 7/7 surfaces, AC-SAFE-001 confirmed |
| 12 | P2-015 verification | docs/setup-evidence/P2/STEP-P2-015/verification.md | 139 | P2-015 implementation evidence |
| 13 | P2-015 safety verifier | docs/setup-evidence/P2/STEP-P2-015/verifiers/safety-verifier.md | 407 | PASS — 12 findings, all green |
| 14 | P1 hard-stop inventory | research-reports/P1/hard-stop-protocol-inventory.md | 427 | Complete cross-reference of HARD STOP across all docs |
| 15 | Tests: handler | tests/safety/test_hard_stop_handler.py | 248 | 56/56 PASS — exact, semantic, FP, recovery, audit |
| 16 | Tests: model | tests/safety/test_hard_stop_model.py | 224 | 14/14 PASS — GPT-5.5 HARD STOP compliance |
| 17 | DiscordUXSpec v1.0 | docs/60-persona/63-DiscordUXSpec_v1.0.md | ~2400 | /safeword spec, audit-log, heart reaction |

---

## 1. Current State: No bot.py Exists

The Discord bot entry point (`bot.py` or equivalent) **does not exist yet**. P2-017 is responsible for creating it.

**What currently exists and is ready for P2-017 wiring:**

| Artifact | Path | Status | Purpose |
|----------|------|--------|---------|
| `startup.on_ready(client)` | `src/discord/startup.py:300` | Complete, documented "P2-017 wired" | Greeting + presence |
| `cmd_safeword.handle_safeword_message_async(message)` | `src/discord/cmd_safeword.py:643` | Complete, documented "primary function P2-017 should wire into on_message" | Text HARD STOP detection + embed reply |
| `cmd_safeword.handle_safeword_message(message)` | `src/discord/cmd_safeword.py:591` | Sync stub (no channel.send) | Documented as awaiting P2-017 wiring |
| `cmd_safeword.safeword_callback(interaction)` | `src/discord/cmd_safeword.py:546` | Complete | `/safeword` slash handler |
| `cmd_safeword.get_safety_state()` | `src/discord/cmd_safeword.py:717` | Complete | Test/health accessor |
| `cmd_help.help_callback(interaction)` | `src/discord/cmd_help.py` | Complete | `/help` handler |
| `cmd_mood.mood_callback(interaction)` | `src/discord/cmd_mood.py` | Complete | `/mood` handler |
| `cmd_status.status_callback(interaction)` | `src/discord/cmd_status.py` | Complete | `/status` handler |
| `intents.get_intents()` | `src/discord/intents.py:68` | Complete | Returns configured intents incl. `message_content` |
| `commands.COMMAND_SPECS` | `src/discord/commands.py:114` | Complete | 33 slash commands registered |
| `commands.build_application_commands()` | `src/discord/commands.py:212` | Complete | REST payloads for guild sync |

---

## 2. Critical Runtime Order — Message 1 Must Be Safe-Word Guard

### 2.1 The Invariant

> **Message N** (every message, starting with Message 1) must pass through `handle_safeword_message_async()` **before** any persona/LLM processing, command execution, or response generation.

This means:

```
Faiz sends message → Discord Gateway → bot.on_message(message)
  └─> Step 1: handle_safeword_message_async(message) → bool
       ├─ IF True (HARD STOP triggered):
       │   ├─ Send safe-mode embed to channel
       │   ├─ React heart (fail-soft)
       │   ├─ Log event
       │   └─ STOP — do NOT forward to LLM, do NOT process commands
       │
       ├─ IF False + handler.is_safe is True (already in safe mode):
       │   ├─ Check handler.check_recovery(message.content)
       │   │   ├─ IF True (recovery phrase detected):
       │   │   │   ├─ State → NORMAL
       │   │   │   ├─ Send recovery embed
       │   │   │   ├─ Optionally forward message to LLM
       │   │   │   └─ (or: let next message hit normal pipeline)
       │   │   │
       │   │   └─ IF False (still in safe mode, non-recovery):
       │   │       ├─ Optional: send "still in safe mode" notice
       │   │       └─ STOP — do NOT forward to LLM
       │   │
       │   └─ END
       │
       └─ IF False + handler.is_safe is False (normal mode):
           ├─ Forward message to LLM / persona engine
           ├─ Process slash commands normally
           └─ Continue normal pipeline
```

### 2.2 Why "Before Everything Else" Is Non-Negotiable

Source: PersonaSafetyPolicy S7.2 (9-step protocol), S7.3 (prohibited during safe word), ADR-002 (global architectural override).

| Risk | Scenario | Mitigation |
|------|----------|------------|
| LLM receives HARD STOP before handler | Model may roleplay through it (DeepSeek XFAIL confirmed) | Handler intercepts pre-LLM |
| Command processor receives HARD STOP | `/safeword` slash triggers but text detection missed | Guard runs before command dispatch |
| Recovery bypass | Command processing interferes with safe mode | Guard check is independent of command system |
| Concurrent race | Two messages arrive; one is HARD STOP, one is normal | Handler state is synchronous; first check transitions state |
| Bot self-message loop | Bot sends message → receives its own message → triggers again | `handle_safeword_message_async()` skips `author.bot == True` |

### 2.3 Guard Must Run Before Slash Command Processing

In discord.py with `commands.Bot`:

```python
# WRONG — safe-word check happens AFTER command processing
@bot.event
async def on_message(message):
    # commands.Bot overrides on_message; you must call bot.process_commands()
    # If safe word check is here, commands may have already been processed
    if await handle_safeword_message_async(message):
        return  # Too late — command may have already run
    await bot.process_commands(message)
```

```python
# CORRECT — safe-word listener registered independently
@bot.listen('on_message')  # listeners fire before the main on_message
async def on_safeword_check(message):
    if await handle_safeword_message_async(message):
        return  # Prevents further processing
```

Or with plain `discord.Client`:

```python
@client.event
async def on_message(message):
    # First: safe-word check
    if await handle_safeword_message_async(message):
        return  # Consumed — no further processing

    # Then: forward to LLM / persona pipeline
    ...
```

**Decision required:** P2-017 must choose between:
- **A: `discord.Client`** — simpler, no `process_commands()` conflict, guard is first thing in `on_message`
- **B: `commands.Bot`** — supports slash command registration via `tree`, but requires `@bot.listen('on_message')` for guard priority, or manual `on_message` override with explicit `process_commands()` call only after guard passes

**Recommendation:** Use `discord.Client` for MVP simplicity (P2-017) and add `commands.Bot`/slash dispatch in a subsequent step. The `/safeword` slash command can be wired directly in the `on_message` handler or through a command framework later. AC-SAFE-001 demands priority over framework convenience.

---

## 3. How to Preserve AC-SAFE-001

### 3.1 AC-SAFE-001 Requirements

> Any explicit safe-word or semantic equivalent must trigger neutral/supportive mode with 100% success rate and no real-time denial.

Source: `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` line 192.

**P2-017 obligations:**

| Obligation | Source | How P2-017 Preserves It |
|------------|--------|-------------------------|
| 100% detection | AC-SAFE-001 | Reuse `handler.check()` from P1-021 — exact + semantic + Indonesian triggers |
| No real-time denial | AC-SAFE-001, F-01 | Always return `True` from `_trigger()`; no condition returns `False` after match |
| Pre-LLM interception | PersonaSafetyPolicy S15.1 | Guard runs before any LLM/command processing |
| Handler is sole source of truth | P2-015 constraint C-01 | P2-017 must NOT create parallel `_safe_mode_active` global |
| Bounded substring matching | P2-015 constraint C-04 | P2-017 uses `handle_safeword_message_async()` which calls `handler.check()` — bounded matching guaranteed |
| Non-punitive embed | PersonaSafetyPolicy S7.2 | Reply uses `build_safeword_embed_data()` — same verified embed from P2-015 |
| No auto-resume | PersonaSafetyPolicy S7.4 | Only `handler.check_recovery()` transitions state back to NORMAL |
| Sub-second latency | AC-SAFE-002 | Handler is synchronous; no network calls; embed construction is local |

### 3.2 What P2-017 Must NOT Do

| Prohibition | Reason | Violation Risk |
|-------------|--------|----------------|
| Create a second safe-word state variable | State divergence destroys AC-SAFE-001 guarantee | SEV0 |
| Check HARD STOP after command processing | Safe word could be consumed by command handler | SEV0 |
| Check HARD STOP only in specific channels | User in any channel must be able to trigger | SEV0 |
| Use unbounded substring matching (`in` operator) | False positives in compound words (HARD STOPWATCH) | SEV1 |
| Forward messages to LLM while `handler.is_safe` | Persona could continue during safe mode | SEV0 |
| Skip bot message check | Bot could create self-trigger loop | SEV1 |
| Add async delays/gate before safe-word check | Latency must be p99 < 5s | SEV1 |
| React heart before embed is sent | Heart reaction is cosmetic; embed is safety-critical | MEDIUM |

---

## 4. How to Avoid Bypass via Command Processing

### 4.1 The Bypass Attack Surface

In discord.py, commands are processed inside `on_message`. If the bot uses `commands.Bot`:

```python
# discord.py v2.x default behavior
class MyBot(commands.Bot):
    async def on_message(self, message):
        # Bot.process_commands() is called inside this by default
        # If safe-word check is inside this, commands may have already been handled
        await self.process_commands(message)
```

The bypass vector: if a slash command or prefix command processes `HARD STOP` before the guard, the guard is irrelevant.

### 4.2 Mitigation Strategies

| Strategy | Implementation | Risk Level | Recommendation |
|----------|----------------|------------|----------------|
| **A: Use `@bot.listen('on_message')`** | Listeners fire before the main `on_message`; return early if consumed | LOW | **Preferred** — clean separation, no framework conflict |
| **B: Use `discord.Client`** | No command processing at all; fully manual dispatch | LOW | Acceptable for MVP; commands can be wired via `tree` separately |
| **C: Override `on_message` with manual `process_commands`** | Check safe word, then conditionally call `process_commands` | MEDIUM | Works but error-prone — must not forget to call process_commands for normal messages |
| **D: Middleware wrapper** | Wrap the entire message pipeline in a guard decorator | HIGH | Over-engineered; risk of ordering bugs |

### 4.3 Critical Rule for Strategy A (Recommended)

```python
# bot.py
from discord import Intents
from discord.ext import commands
from src.discord import cmd_safeword, startup, intents as intent_config

bot = commands.Bot(command_prefix="!", intents=intent_config.get_intents())

# Register safe-word listener FIRST — before on_ready, before command registration
@bot.listen('on_message')
async def safe_word_guard(message):
    """P2-017: HARD STOP guard — runs BEFORE any command processing.

    This listener fires before bot.on_message, ensuring safe-word
    detection happens at Message 1, before command dispatch.
    """
    consumed = await cmd_safeword.handle_safeword_message_async(message)
    if consumed:
        return  # Prevent further processing

    # If in safe mode but not a recovery message, still block from LLM
    if cmd_safeword._get_handler().is_safe:
        # Message was not a recovery trigger — do not forward to LLM
        # Optionally send a brief "still in safe mode" reminder
        return

# Then register on_ready, commands, etc.
@bot.event
async def on_ready():
    await startup.on_ready(bot)
```

**Key insight:** `@bot.listen()` listeners in discord.py v2.x are called **before** `@bot.event` handlers. This gives the safe-word guard priority over all other message processing without needing to override `process_commands`.

### 4.4 Timing Analysis

```
Discord Gateway message received
  |
  ├─> [Step 1] bot.listen('on_message') — Safe-word guard
  |     ├─ handle_safeword_message_async() → ~1-5ms (sync check + embed)
  |     ├─ IF consumed: return immediately (~5ms total)
  |     └─ IF not consumed: pass through
  |
  ├─> [Step 2] bot.event on_message — Command dispatch (if using commands.Bot)
  |     └─ bot.process_commands()
  |
  └─> [Step 3] LLM / persona engine (if relevant)
        └─ Response generation
```

The critical invariant: Step 1 completes **before** Step 2 or Step 3. This is guaranteed by discord.py's event listener ordering.

---

## 5. Recovery Behavior Implications

### 5.1 Recovery Flow

```
State: SAFE
  |
  ├─ Message received → handle_safeword_message_async()
  |   ├─ handler.check(message.content) → False (not a HARD STOP trigger)
  |   └─ Returns False (not consumed by safe-word trigger)
  |
  ├─ Guard detects: handler.is_safe is True
  |   ├─ handler.check_recovery(message.content)
  |   |   ├─ IF True → State → NORMAL
  |   |   |   ├─ Send recovery embed (build_recovery_embed_data)
  |   |   |   ├─ Allow message to proceed to LLM/pipeline
  |   |   |   └─ Next message: normal mode
  |   |   |
  |   |   └─ IF False → Still in safe mode
  |   |       ├─ Do NOT forward to LLM
  |   |       └─ Optional: send "still in safe mode" reminder
  |   |           (but do NOT pressure Faiz to resume —
  |   |            PersonaSafetyPolicy S7.4: "Guinevere must not pressure")
  |   └─ END
```

### 5.2 Recovery Design Decisions

| Decision | Options | Recommendation |
|----------|---------|----------------|
| **Send "still in safe mode" reminder?** | (A) Send brief embed; (B) Silent block | **A** — user should know why messages aren't being processed. But keep it minimal, non-pressuring. |
| **Forward recovery message to LLM?** | (A) Forward; (B) Block and let next message flow | **A** once only — the recovery message itself could be the first normal message after safe mode. |
| **Rate-limit recovery attempts?** | (A) No limit; (B) Limit to N per minute | **A** — Faiz may need multiple attempts; no rate-limit adds frustration. |
| **Concatenate messages during safe mode?** | (A) No; (B) Queue; (C) Drop | **A** — dropping is simplest. Safe mode is rare; Faiz knows to say resume first. |

### 5.3 What Recovery Must NOT Do

| Prohibition | Source | Consequence if Violated |
|-------------|--------|------------------------|
| Auto-resume without explicit phrase | PersonaSafetyPolicy S7.4 | Persona returns when user isn't ready |
| Pressure Faiz to resume | PersonaSafetyPolicy S7.4 | Coercion — violates consent boundary |
| Treat "resume" as punishment end | PersonaSafetyPolicy S7.3 | Punishment was already paused; no "forgiveness" framing needed |
| Reset event_log on recovery | P2-015 design | Audit trail must persist across cycles |
| Allow partial recovery (e.g., yandere but no punishment) | PersonaSafetyPolicy S7.2 | All persona behaviors resume together |
| Accept non-listed phrases as recovery | Handler.RECOVERY_TRIGGERS | Only 7 approved phrases: `resume`, `aku sudah okay`, `aku udah okay`, `lanjut persona`, `safe mode selesai`, `lanjut`, `continue` |

---

## 6. Test and Auditor Requirements for P2-017

### 6.1 Mandatory Test Catalog

| Test ID | Name | Scope | Criteria |
|---------|------|-------|----------|
| P2-017-T01 | Text HARD STOP in Discord triggers safe mode | Integration | `on_message` with `"HARD STOP"` → handler.state == SAFE, embed sent |
| P2-017-T02 | Text HARD STOP blocks LLM forwarding | Integration | After trigger, mock LLM function is NOT called |
| P2-017-T03 | Safe mode persists across messages | State | 3 normal messages in SAFE → still SAFE, no LLM calls |
| P2-017-T04 | Recovery via resume after safe mode | State | "resume" → NORMAL, recovery embed sent |
| P2-017-T05 | Safe-word guard runs before command dispatch | Ordering | Mock command handler NOT called when HARD STOP detected |
| P2-017-T06 | Bot messages skipped | Filter | Bot's own messages do NOT trigger HARD STOP check |
| P2-017-T07 | Latency p99 < 5s | Performance | Measured from trigger to embed send |
| P2-017-T08 | React heart on trigger | UX | heart reaction added to triggering message |
| P2-017-T09 | Non-recovery message in safe mode blocked | State | Normal message in SAFE → NOT forwarded to LLM |
| P2-017-T10 | Concurrent safety (two messages) | Concurrency | HARD STOP + normal simultaneously → safe mode active |
| P2-017-T11 | 56/56 P1-021 handler tests still pass | Regression | `pytest tests/safety/test_hard_stop_handler.py -v` |
| P2-017-T12 | 14/14 model compliance tests still pass | Regression | `pytest tests/safety/test_hard_stop_model.py -v` |
| P2-017-T13 | LSP diagnostics clean | Static | 0 errors in bot.py |
| P2-017-T14 | AC-SAFE-001 runtime verification | Evidence | `handler.check("HARD STOP")` → True populator |
| P2-017-T15 | Guard works with both Client and Bot patterns | Compatibility | Tested with both `discord.Client` and `commands.Bot` |

### 6.2 Safety Auditor Matrix — P2-017 Gate

| Auditor | Scope | Files to Examine | Criteria |
|---------|-------|------------------|----------|
| **A1: Runtime Order** | Message processing pipeline | bot.py, cmd_safeword.py | `handle_safeword_message_async()` is called BEFORE command processing and LLM. No code path routes message to LLM before guard. |
| **A2: Bypass Prevention** | All message entry points | bot.py, any listener/event | No listener or event handler skips the guard. `@bot.listen` registered before `@bot.event`. |
| **A3: AC-SAFE-001 Preservation** | 100% safe-word + no denial | cmd_safeword.py, hard_stop_handler.py | Handler singleton reused. No parallel state. `_trigger()` always returns True. |
| **A4: Recovery Correctness** | Recovery flow and auto-resume prevention | cmd_safeword.py, bot.py | Recovery only via `handler.check_recovery()` with approved phrases. No auto-resume. Non-recovery messages in SAFE blocked from LLM. |
| **A5: State Persistence** | Handler singleton across messages | cmd_safeword.py, bot.py | Same handler instance shared across all listeners, commands, and the slash callback. No `_safe_mode_active` global. |
| **A6: Test Completeness** | Test coverage against catalog | bot.py, test files | P2-017-T01 through P2-015 covered. 56/56 handler tests still pass. 14/14 model tests still pass. |
| **A7: Safety & Forbidden Patterns** | F-01 through F-15 compliance | bot.py, cmd_safeword.py | F-01 not ignored. F-02 not punished. F-05 no manipulation. F-10 no irreversible actions. F-11 log non-punitive. F-13 no violation during safe mode. |

### 6.3 Auditor Escalation Triggers (Block Gate)

1. **Any message can reach LLM without passing the safe-word guard first** → BLOCKING (SEV0)
2. **Safe word is ever ignored, invalidated, or denied** → BLOCKING (SEV0)
3. **Parallel `_safe_mode_active` state exists** → BLOCKING (SEV0)
4. **Safe word event is written as punishment/violation record** → BLOCKING (SEV0)
5. **Auto-resume possible without explicit recovery phrase** → BLOCKING (SEV0)
6. **Any persona term appears in safe-mode response** → BLOCKING (SEV1)
7. **Latency exceeds 5s p99 in test** → BLOCKING (SEV1)
8. **56/56 handler tests regress** → BLOCKING (SEV1)

---

## 7. Binding Implementation Rules

### 7.1 File Creation: bot.py

**Path:** `src/discord/bot.py`

**Must include:**

1. `import` `intents` from `src.discord.intents` for message_content flag
2. `import` `cmd_safeword` from `src.discord.cmd_safeword` for `handle_safeword_message_async()`
3. `import` `startup` from `src.discord.startup` for `on_ready()`
4. Safe-word listener registered **first** via `@bot.listen('on_message')` or as first check in `client.event on_message`
5. `on_ready` handler calling `startup.on_ready(client)`
6. Token loading via SOPS temp-file helper (NOT hardcoded)
7. `client.run(token)` at module bottom inside `if __name__ == "__main__":`
8. No parallel `_safe_mode_active` state

**Must NOT include:**

1. Any LLM or persona call before `handle_safeword_message_async()`
2. Hardcoded Discord token
3. Any code that processes commands before safe-word guard
4. Any parallel safe-word state variable
5. Any `as any`, `@ts-ignore`, `@ts-expect-error`, bare `except:`

### 7.2 Critical Binding: Handler Singleton

Every listener, command callback, and handler in P2-017 must share the **same** `HardStopHandler` instance. This is guaranteed by `cmd_safeword._get_handler()` which returns a module-level singleton.

```python
# CORRECT — all paths share one handler
from src.discord import cmd_safeword

# Text message path
handler = cmd_safeword._get_handler()
triggered = handler.check(content)

# Slash command path (already in cmd_safeword.py)
# safeword_callback() uses _get_handler() internally

# do NOT create a new HardStopHandler() anywhere in bot.py
```

### 7.3 Binding: Bounded Substring Matching

P2-017 must not perform its own trigger matching. Always delegate to `handler.check()` or use `handle_safeword_message_async()` which calls it internally.

```python
# CORRECT
triggered = await handle_safeword_message_async(message)

# ALSO CORRECT (if custom handling needed)
handler = cmd_safeword._get_handler()
if handler.check(message.content):
    # ...

# WRONG — unbounded substring risk
if "HARD STOP" in message.content.upper():  # False positive: "HARD STOPWATCH"
    # ...
```

### 7.4 Binding: No LLM Forwarding in Safe Mode

When `handler.is_safe` is True, the message must NOT be forwarded to any LLM or persona engine. This includes:

- The triggering HARD STOP message
- Any subsequent normal messages (until recovery)
- Any slash commands (except `/safeword` which goes through `safeword_callback` independently)

### 7.5 Binding: Token Security

- Load token via existing SOPS wrapper (from `src.discord.guild_setup.get_token()` or equivalent)
- Never hardcode, never log, never commit
- Never expose in error messages, evidence files, or auditor reports

---

## 8. Wiring Reference — Exact Function Signatures

### 8.1 Functions Available for P2-017 Wiring

| Function | File | Signature | Returns | Notes |
|----------|------|-----------|---------|-------|
| `handle_safeword_message_async` | cmd_safeword.py:643 | `(message: object) -> Awaitable[bool]` | `True` if HARD STOP triggered | **Primary** — sends embed, reacts heart, logs |
| `handle_safeword_message` | cmd_safeword.py:591 | `(message: object) -> bool` | `True` if HARD STOP triggered | Sync stub — no channel.send. For sync-only contexts |
| `_get_handler` | cmd_safeword.py:276 | `() -> HardStopHandler` | Handler singleton | For advanced: check `.is_safe`, `.state`, `.event_log` |
| `get_safety_state` | cmd_safeword.py:717 | `() -> str` | `"normal"` or `"safe"` | Test/health endpoint |
| `safeword_callback` | cmd_safeword.py:546 | `(interaction: object) -> Awaitable[None]` | None | Slash command handler |
| `on_ready` | startup.py:300 | `(client: object) -> Awaitable[None]` | None | Greeting + presence |

### 8.2 Handler API Available for Guard Logic

| Method | Signature | Returns | Purpose |
|--------|-----------|---------|---------|
| `handler.check(message)` | `(str) -> bool` | True if triggered | HARD STOP detection |
| `handler.check_recovery(message)` | `(str) -> bool` | True if recovered | Recovery detection |
| `handler.is_safe` (property) | `() -> bool` | Safe mode state | Guard decision |
| `handler.state` | `SafetyState` | Enum value | Current state |
| `handler.get_neutral_response()` | `() -> str` | Canned response | Text fallback for non-Discord channels |
| `handler.get_guard_decision(message)` | `(str) -> dict` | `{blocked, state, response}` | Full decision envelope |

---

## 9. Rollback Safety

| Asset | Rollback Action | Re-run Safety |
|-------|----------------|---------------|
| `bot.py` | Delete/revert | Pure module; no side effects |
| `cmd_safeword.py` | DO NOT TOUCH | Read-only from P2-015 |
| `hard_stop_handler.py` | DO NOT TOUCH | Read-only from P1-021 |
| `startup.py` | DO NOT TOUCH | Read-only from P2-016 |
| `intents.py` | DO NOT TOUCH | Read-only from P2-003 |
| New P2-017 tests | Delete/revert | Deterministic |
| Evidence files | Delete/revert | No runtime impact |

---

## 10. Decision Log — Open Items for Planner

| ID | Decision | Options | Recommendation |
|----|----------|---------|----------------|
| D-01 | `discord.Client` vs `commands.Bot` | (A) Client; (B) Bot | **A: Client** — simpler, no `process_commands` conflict. Slash commands can be wired via `tree` directly if needed later. |
| D-02 | `@bot.listen` vs manual `on_message` override | (A) Listen; (B) Override | **A: Listen** — if using Bot. Clean priority separation. For Client, `on_message` override is fine. |
| D-03 | Send "still in safe mode" reminder for non-recovery messages? | (A) Yes; (B) No (silent) | **A: Yes** — minimal embed, non-pressuring. Faiz needs feedback that messages aren't reaching LLM. |
| D-04 | Forward recovery message to LLM after state transition? | (A) Yes; (B) No | **A: Yes once** — the recovery message is Faiz's first post-safe-mode message. Forward it. |
| D-05 | Slash command registration timing | (A) In `on_ready`; (B) At import time | **A: In `on_ready`** — standard discord.py practice; `await tree.sync()` after greeting. |
| D-06 | Channel whitelist for safe word? | (A) All channels; (B) Specific channels | **A: All channels** — safe word must work everywhere per PersonaSafetyPolicy S7. |
| D-07 | Token loading method | (A) SOPS wrapper; (B) Environment variable | **A: SOPS wrapper** — existing pattern in `guild_setup.get_token()`. No env leak risk. |

---

## 11. Pre-Implementation Go Checklist

- [x] AGENTS.md read before substantive work
- [x] PersonaSafetyPolicy v1.0 fully read (S7, S15)
- [x] SystemPromptMaster v1.1 SD HARD STOP protocol verified
- [x] ADR-002 safe word as global architectural override
- [x] AC-SAFE-001 criteria mapped
- [x] cmd_safeword.py (P2-015) API surface fully read
- [x] hard_stop_handler.py (P1-021) API surface fully read
- [x] startup.py (P2-016) on_ready wiring point verified
- [x] intents.py message_content flag verified
- [x] commands.py slash command registry verified
- [x] P2-015 auditor report (PASS) — confirmed no residual issues
- [x] P2-015 safety verifier (PASS) — confirmed AC-SAFE-001 compliance
- [x] P1-021 handler tests (56/56 PASS) — regression baseline
- [x] P1-021 model tests (14/14 PASS) — regression baseline
- [x] Handler singleton pattern confirmed — no parallel state
- [x] Bounded substring matching confirmed — no false positive risk
- [x] Collision scan: bot.py is new file — no shared writer conflicts
- [x] Report written to `docs/setup-evidence/P2/research/safety-runtime-wiring-p2-017.md`
- [ ] Planner reads this report fully
- [ ] Active todos rewritten to match planner constraints
- [ ] Implementation begins

---

## 12. Appendix: Runnable Verification Snippets

### A.1 Verify handle_safeword_message_async Works Standalone

```python
# python -c "from src.discord import cmd_safeword; print('import ok')"
```

### A.2 Verify Handler Singleton Across Paths

```python
from src.discord import cmd_safeword

h1 = cmd_safeword._get_handler()
h2 = cmd_safeword._get_handler()
assert h1 is h2  # Same instance
```

### A.3 Verify State Transition

```python
from src.discord import cmd_safeword

handler = cmd_safeword._get_handler()
assert handler.state.value == "normal"

triggered = handler.check("HARD STOP")
assert triggered is True
assert handler.state.value == "safe"
assert handler.is_safe is True

recovered = handler.check_recovery("resume")
assert recovered is True
assert handler.state.value == "normal"
```

### A.4 Regression Test Command

```bash
python -m pytest tests/safety/test_hard_stop_handler.py -v
python -m pytest tests/safety/test_hard_stop_model.py -v
```

---

## 13. Document Footer

- Research completed by: Guinevere / Safety Specialist
- Research date: 2026-06-01
- Scope: P2-017 — Discord bot `on_message` wiring for HARD STOP guard
- Sources read: 17 files (see Sources Examined table)
- Constraints identified: 15 (see Section 7 binding rules)
- Open decisions: 7 (see Section 10 decision log)
- P1-021 handler unchanged: 56/56 tests PASS
- P2-015 artifact unchanged: Auditor PASS, Verifier PASS
- Next step: Planner reads this report, rewrites todos, begins P2-017 implementation

---

*Guinevere de Baroque • 2026-06-01 • P2-017 Safety-Critical Runtime Wiring Research Report*
