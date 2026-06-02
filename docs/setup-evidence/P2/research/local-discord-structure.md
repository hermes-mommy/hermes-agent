# P2-013 to P2-016 Local Discord Structure Research Report

**Date:** 2026-06-01
**Scope:** STEP-P2-013 (`/mood`), STEP-P2-014 (`/help`), STEP-P2-015 (`/safeword` + HARD STOP), STEP-P2-016 (startup message/presence)
**Researcher:** Guinevere parent (post-P2-013 re-synthesis)
**Status:** P2-013 = DONE, P2-014/015/016 = PENDING
**Downstream:** Implementation planning for P2-014, P2-015, P2-016

---

## 1. Current State Summary

| Step | Source File | Test File | Evidence | Status |
|------|------------|-----------|----------|--------|
| P2-013 | `src/discord/cmd_mood.py` (460 lines) | `tests/discord/test_cmd_mood.py` (346 lines, 27 tests) | `docs/setup-evidence/P2/STEP-P2-013/*` | **DONE** (P2-013) |
| P2-014 | NOT CREATED | NOT CREATED | NOT CREATED | PENDING |
| P2-015 | NOT CREATED | NOT CREATED | NOT CREATED | PENDING |
| P2-016 | NOT CREATED | NOT CREATED | NOT CREATED | PENDING |
| P2-017 | NOT CREATED (bot.py) | N/A | N/A | PENDING (future wiring) |

**P2-013 is already fully implemented** with source, 27 deterministic tests, LSP-clean, py_compile-clean, and verification evidence. The `batch-plan-013-016.md` was written before P2-013 existed, but P2-013 was subsequently implemented. Re-implementing P2-013 would be wasteful and wrong.

---

## 2. src/discord/ Module — Complete File Map

### 2.1 All Source Files

| File | Lines | Purpose | Imports discord? | Key Symbols |
|------|-------|---------|------------------|-------------|
| `src/discord/__init__.py` | 1 | Module marker | No | (none) |
| `src/discord/commands.py` | 291 | P2-010: 33-command registry, REST payloads, Faiz-only guard | No | `COMMAND_SPECS`, `CommandSpec`, `CommandOption`, `is_faiz_interaction()`, `command_categories()`, `command_count()`, `require_canonical_registry()` |
| `src/discord/colors.py` | 125 | P2-011: Color constants, MOOD_COLORS, helpers | No | `PRIMARY=0x6B21A8`, `ALERT=0xDC2626`, `SUCCESS=0x16A34A`, `WARNING=0xCA8A04`, `ACHIEVEMENT=0xCA8A04`, `NEUTRAL=0x6B7280`, `MOOD_COLORS`, `color_for_mood()`, `as_hex()` |
| `src/discord/cmd_status.py` | 461 | P2-012: `/status` handler (reference pattern) | Dynamic (`importlib`) | `build_status_embed_data()`, `status_callback()`, `to_discord_embed()`, `DiscordInteractionProtocol`, `StatusEmbedData` |
| `src/discord/cmd_mood.py` | 460 | **P2-013: `/mood` handler (DONE)** | Dynamic (`importlib`) | `build_mood_embed_data()`, `mood_callback()`, `to_discord_embed()`, `display_for_mood()`, `MoodEmbedData`, `MoodEmbedField` |
| `src/discord/guild_setup.py` | 445 | P2-004/005/006: Guild setup, channel specs, `get_token()` | Dynamic (`importlib`) | `get_token()`, `CATEGORIES`, `CHANNELS`, `GUILD_ID`, `create_client()`, `read_scalar_yaml_value()` |
| `src/discord/permissions.py` | 526 | P2-007/008/009: Permissions, topics, admin review | No (uses `http.client`) | `discord_request()`, `read_channel_ids()`, `discover_context()`, `fetch_channels()`, `token_from_environment()` |
| `src/discord/intents.py` | 112 | P2-003: Gateway intent config | Dynamic (`importlib`) | `get_intents()`, `REQUIRED_INTENTS`, `IntentValidationResult` |

### 2.2 Expected New Files for P2-014 through P2-016

| File | Pattern to Follow | Dependencies (read-only) |
|------|------------------|--------------------------|
| `src/discord/cmd_help.py` | `cmd_status.py` / `cmd_mood.py` protocol + dataclass + builder pattern | `commands.py` (`command_categories()`, `COMMAND_SPECS`, `is_faiz_interaction()`), `colors.py` (`PRIMARY`) |
| `src/discord/cmd_safeword.py` | `cmd_status.py` embed pattern + `hard_stop_handler.py` for state machine | `colors.py` (`SUCCESS`, `ALERT`, `NEUTRAL`), `commands.py` (`is_faiz_interaction()`), `src/core/services/hard_stop_handler.py` |
| `src/discord/startup.py` | Dynamic `importlib` + Protocol pattern (no bot.py yet) | `colors.py` (for embed color), channel ID via `guild_setup.py` channel specs or `channel-ids.yaml` |

---

## 3. Command Registration Pattern (commands.py)

### 3.1 Canonical Command Specs for This Batch

```python
CommandSpec("core", "mood", "Show or update Guinevere's current mood state."),
CommandSpec("core", "help", "Show the Guinevere command guide."),
CommandSpec("core", "safeword", "Trigger the configured safety boundary workflow."),
```

These are already registered in `COMMAND_SPECS` (lines 116-118). The registry has **exactly 33 commands** across 7 categories enforced by `require_canonical_registry()`.

### 3.2 Faiz-Only Access Guard

`is_faiz_interaction(interaction: object) -> bool` (lines 245-256) checks `guild.owner_id` vs `user.id`. No hardcoded user ID. Used as:

```python
if not is_faiz_interaction(interaction):
    await _send_denied(interaction)
    return
```

### 3.3 Category Mapping for /help

`command_categories()` returns `dict[str, tuple[str, ...]]` with 7 categories:

```python
{
    'core': ('status', 'mood', 'help', 'safeword'),
    'loop': ('loop-start', 'loop-stop', 'loop-pause', 'loop-resume', 'loops', 'evidence', 'loop-priority'),
    'memory': ('memory-search', 'memory-add', 'memory-forget', 'memory-export'),
    'surveillance': ('surveillance-status', 'surveillance-pause', 'surveillance-resume'),
    'finance': ('cost', 'budget', 'cost-alert'),
    'system': ('approve', 'deny', 'approve-all', 'focus', 'casual', 'consent', 'punishment', 'reward'),
    'admin': ('restart-service', 'backup-now', 'health-check', 'clear-cache'),
}
```

---

## 4. Cog / Command Handler Pattern (No Cogs Used)

**The codebase does NOT use discord.py Cogs.** All command implementations use:

### 4.1 Pure Data + Protocol Pattern

Used by `cmd_status.py` and `cmd_mood.py`:

1. **Frozen dataclass** for embed data (e.g., `MoodEmbedData`, `StatusEmbedData`).
2. **Protocol classes** from `typing` with `@runtime_checkable` for Discord interaction objects (no static `discord.py` dependency).
3. **Pure builder function** with overridable `now` parameter for deterministic tests.
4. **Dynamic importlib** for `discord.py` conversion (`to_discord_embed()`).
5. **Async callback** accepting `interaction: object`, narrowing via `isinstance(interaction, DiscordInteractionProtocol)`.

### 4.2 Callback Flow (from cmd_mood.py / cmd_status.py)

```python
async def mood_callback(interaction: object) -> None:
    from .commands import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await _send_denied(interaction)    # Ephemeral "Hanya Faiz yang bisa..."
        return

    await _defer_ephemeral(interaction)     # interaction.response.defer(ephemeral=True)

    try:
        data = build_mood_embed_data()
        embed = to_discord_embed(data)
        await _followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("mood_callback failed")
        await _followup_send(interaction, content="⚠️ Mommy's mood analysis is temporarily unavailable.")
```

### 4.3 Interaction Response Pattern

All commands use **ephemeral defer/followup**:

1. `interaction.response.defer(ephemeral=True)` — gives >3s processing time
2. `interaction.followup.send(embed=..., ephemeral=True)` — sends result
3. If not Faiz: ephemeral denial message
4. Graceful degradation on exceptions: fallback text instead of crash

### 4.4 Protocol Definitions — Duplication vs. Shared

`cmd_status.py` and `cmd_mood.py` both define their own:
- `DiscordInteractionProtocol`
- `DiscordResponseProtocol`
- `DiscordFollowupProtocol`
- `DiscordEmbedProtocol`
- `DiscordEmbedFactory` / `DiscordColourFactory` / `DiscordEmbedModule`

These are **intentionally duplicated** per the batch plan §6 (collision scan: "Prefer import public Protocols if available; duplicate tiny helper patterns instead of editing this file unless implementer proves a shared helper is safer.").

**For P2-014**: follow the same duplication pattern, OR extract shared protocols into a `src/discord/_protocols.py` module if an implementer proves it safer.

---

## 5. Color/Palette Pattern

All colors in `src/discord/colors.py`:

| Constant | Hex | Integer | Typical Use |
|----------|-----|---------|-------------|
| `PRIMARY` | `#6B21A8` | `0x6B21A8` | Status, info, /help embeds |
| `ALERT` | `#DC2626` | `0xDC2626` | Errors, denials, angry mood |
| `SUCCESS` | `#16A34A` | `0x16A34A` | Completions, safe mode, content mood |
| `WARNING` | `#CA8A04` | `0xCA8A04` | Warnings, disappointed mood |
| `ACHIEVEMENT` | `#CA8A04` | `0xCA8A04` | Rewards, pleased mood |
| `NEUTRAL` | `#6B7280` | `0x6B7280` | Neutral, silent mood |
| `PERSONA` | `#9333EA` | `0x9333EA` | Persona-related |
| `SURVEILLANCE` | `#0891B2` | `0x0891B2` | Surveillance |
| `FINANCE` | `#059669` | `0x059669` | Finance |
| `INFO` | `#CA8A04` | `0xCA8A04` | Info notices |
| `ORANGE` | `#EA580C` | `0xEA580C` | Future use only (not active in P2) |
| `INFO_BLUE` | `#2563EB` | `0x2563EB` | Non-canonical info |

Helpers: `color_for_mood(mood: str) -> int`, `as_hex(color: int) -> str`.

**P2-014 (/help)**: Use `PRIMARY` per DiscordUXSpec.
**P2-015 (/safeword)**: Use `SUCCESS` for safe-mode embed (green). Use `ALERT` for denial. StepPrompts says gray `NEUTRAL` but DiscordUXSpec and batch-plan say `SUCCESS` green.
**P2-016 (startup)**: Use `PRIMARY` for startup embed.

---

## 6. Channel ID Loading Pattern

### 6.1 Source of Truth

Channel IDs are stored in `docs/setup-evidence/P2/STEP-P2-006/channel-ids.yaml`:

```yaml
channels:
  'guinevere-chat': 1510914600777023659
  'guinevere-status': 1510914604291588237
  'audit-log': 1510914647602106408
  ... (13 channels total)
```

### 6.2 Current Reading Methods

Two approaches exist:

**Approach A** — `permissions.py` `read_channel_ids()`: Parses the YAML manually (line-by-line string splitting). Returns `ChannelIdMap` dataclass.

**Approach B** — `guild_setup.py` `CHANNELS` tuple: Contains all 13 canonical `ChannelSpec` objects with names, categories, positions, topics. Channels are looked up by name at runtime via `find_text_channel()`.

### 6.3 Recommendation for P2-016 (startup.py)

Per batch-plan §11.3: "Use channel lookup by name at runtime. Do not hardcode channel IDs in source code."

The startup function should:
1. Accept a fake client/guild that implements `find_text_channel(name)` protocol
2. Find `guinevere-status` by name (not ID)
3. Fall back gracefully if channel not found

---

## 7. Token Handling Pattern

### 7.1 Current Mechanism

Token is obtained via `guild_setup.get_token()`:

```python
def get_token() -> str:
    """Read Discord bot token from the SOPS-decrypted temporary YAML file."""
    secrets_path_raw = os.environ.get("DISCORD_SECRETS_PATH")
    if not secrets_path_raw:
        raise RuntimeError("DISCORD_SECRETS_PATH env var not set")
    # ... reads discord_bot_token key from decrypted YAML
```

The `scripts/run-discord-verify.sh` wrapper:
1. Runs `sops -d secrets/discord-secrets.yaml` to a temp file
2. Sets `DISCORD_SECRETS_PATH` to that temp file
3. Executes the Python script

### 7.2 Forbidden Patterns

```python
# BLOCKING — do not use:
os.environ.get("DISCORD_BOT_TOKEN")
os.environ["DISCORD_BOT_TOKEN"]

# BLOCKING — do not use in code/evidence/artifacts:
sops -d secrets/discord-secrets.yaml | grep discord_bot_token | awk ...
```

### 7.3 Existing tmp/ Scripts Pattern

All `tmp/*.py` scripts use `token_from_environment()` or `get_token()`:
- `tmp/sync-p2-010-commands.py` uses `token_from_environment()` (which calls `get_token()`)
- `tmp/setup-discord-guild.py` uses `get_token()` directly
- All `tmp/verify-p2-*.py` scripts follow the same pattern

---

## 8. HARD STOP / Safety System Pattern

### 8.1 Existing Hard Stop Handler (P1-021)

`src/core/services/hard_stop_handler.py` (149 lines) implements:

- **State machine**: `HardStopHandler` dataclass with `SafetyState` enum (NORMAL / SAFE)
- **Exact triggers**: `"hard stop"`, `"hardstop"`, `"safe word"`, `"safeword"`, `"hentikan"`, `"berhenti"`
- **Semantic patterns**: 5 regex patterns covering "stop persona", "neutral mode", "i need a break", "switch to safe", Indonesian equivalents
- **Recovery triggers**: `"resume"`, `"aku sudah okay"`, `"lanjut persona"`, `"safe mode selesai"`, etc.
- **Guard decision**: `get_guard_decision(message) -> dict` returning `{blocked, state, response}`
- **Neutral response**: "HARD STOP acknowledged. I am now in neutral/safe mode..."
- **Audit logging**: `structlog` warning with trigger/state_change
- **Event log**: `HardStopEvent` records timestamp, trigger, state transitions

### 8.2 P2-015 Integration Requirements

P2-015 must reuse `HardStopHandler`, NOT create parallel `_safe_mode_active` global. The handler already has:

```python
handler = HardStopHandler()
handler.check("HARD STOP")          # → True, state becomes SAFE
handler.is_safe                      # → True
handler.check_recovery("resume")    # → True, state becomes NORMAL
handler.get_neutral_response()      # → neutral text
handler.get_guard_decision("msg")  # → {blocked: bool, state: str, response: str|None}
```

Key constraint (batch-plan §10.4): "Reuse `HardStopHandler`; do **not** create parallel `_safe_mode_active` as source of truth."

---

## 9. Startup / on_ready Pattern

### 9.1 Existing Pattern in tmp/setup-discord-guild.py

The only existing `on_ready` pattern is in `tmp/setup-discord-guild.py`:

```python
async def on_ready() -> None:
    guild = require_guild(client)
    # ... do work ...
    await client.close()

_ = client.event(on_ready)
await client.start(token)
```

This is a one-shot setup script, not a persistent bot. It uses `client.event()` decorator-style registration.

### 9.2 P2-016 Requirements

Per batch-plan §11:
- Startup embed with `👑 Mommy sudah bangun, Darling.` sent to `#guinevere-status`
- Presence set to `Watching Darling 👁️`
- Idempotency guard: second `on_ready` call (reconnect) must NOT send duplicate greeting
- Dynamic import/protocol pattern — no direct token handling
- Expose `on_ready(client: object) -> None` for P2-017 wiring
- Channel lookup by name, NOT hardcoded ID

**Conflict**: DiscordUXSpec says startup channel is `#guinevere-chat` and presence is `Waking up... 👑`. Batch-plan §4.2 resolves: **use `#guinevere-status`** (current-session user DoD) and **use `Watching Darling 👁️`** for default presence. Document UXSpec conflict.

---

## 10. Test Patterns

### 10.1 Existing Discord Tests

| File | Tests | Pattern |
|------|-------|---------|
| `tests/discord/test_cmd_mood.py` | 27 deterministic | pytest classes, frozen dataclass fixtures, no discord.py runtime |
| `tests/safety/test_hard_stop_handler.py` | P1 handler tests | Must still pass after P2-015 |
| `tests/smoke/test_safe_word.py` | LLM-based xfail tests | Not relevant to P2-015 local implementation |
| `tests/smoke/test_persona_basic.py` | LLM-based tests | Not relevant |
| `tests/smoke/test_yandere_boundary.py` | LLM-based tests | Not relevant |

### 10.2 Test Pattern for P2-014 (/help)

Follow `test_cmd_mood.py` pattern:
- Pure data builders testable without discord.py
- Frozen dataclass fixtures returning deterministic data
- Assert on command_count (33), category count (7), command names, etc.
- `@pytest.fixture` for deterministic data
- `TestTopLevelDiscordImport` class to prove no static import

### 10.3 Test Pattern for P2-015 (/safeword)

Per batch-plan §10.6:
- Exact trigger tests (HARD STOP, hardstop, safeword, hentikan, berhenti)
- Semantic trigger tests (stop persona, neutral mode, aku butuh jeda, etc.)
- False positive tests (normal messages shouldn't trigger)
- Slash trigger test (safeword_callback)
- Text trigger helper test (handle_safeword_message)
- Safe embed content verification
- Recovery/no auto-resume test
- Handler integration: reuse `HardStopHandler`, P1 tests must still pass

### 10.4 Test Pattern for P2-016 (startup)

Per batch-plan §11.4:
- Fake client/guild fixture implementing protocols
- First call: sends to `guinevere-status` channel on fake client
- Second call: sends zero additional messages (idempotency)
- Presence verification: watching Darling
- Channel not found graceful handling

---

## 11. Logging Pattern

### 11.1 Current State

`cmd_mood.py` uses standard library `logging` module (not `structlog`):

```python
import logging
logger: logging.Logger = logging.getLogger(__name__)
```

The batch-plan §7 says "Use `structlog` for unexpected callback errors." However, `cmd_mood.py` switched from `structlog` to `logging` during implementation to resolve basedpyright `reportAny` warnings. This divergence should be documented.

`cmd_status.py` uses a bare `except Exception:` without logging (known issue, batch-plan §7).

`hard_stop_handler.py` uses `structlog`.

### 11.2 Recommendation

For P2-014/015/016: use `logging.getLogger(__name__)` to match `cmd_mood.py` and avoid `reportAny` warnings. Structure error messages with `logger.exception()`.

---

## 12. Static Analysis / Lint Rules (Blocking)

From AGENTS.md and batch-plan §7:

| Forbidden | Check |
|-----------|-------|
| `# type: ignore` | grep |
| `@ts-ignore` / `@ts-expect-error` | grep |
| `as any` / avoidable `Any` | grep |
| `except:` (bare) / `except Exception: pass` | grep |
| `DISCORD_BOT_TOKEN` (in source or evidence) | grep |
| `sops -d.*grep` | grep |
| `os.environ.get("DISCORD_BOT_TOKEN")` | grep |
| Hardcoded channel IDs in source | manual review |

---

## 13. StepPrompts Conflicts (Stale Content)

### 13.1 P2-013 StepPrompts (lines 5482-5498) — NOW STALE

The StepPrompts inline snippet uses:
- `from src.discord.colors import Colors, MOOD_COLORS` — `Colors` class does NOT exist
- `discord.Embed(title="💜 Mood State")` — wrong title (actual: "🧠 Mood Analysis")
- Hardcoded `mood = "Content"` — the actual implementation uses `build_mood_embed_data(mood="content")`
- `interaction.followup.send()` without defer — the actual implementation defers first
- Colors.PRIMARY` — `PRIMARY` is a module-level constant, not a class attribute

**The actual P2-013 implementation is completely different and better.** StepPrompts should be updated.

### 13.2 P2-014 StepPrompts (lines 5500-5522) — STALE

StepPrompts inline snippet uses:
- `Colors.INFO` for embed color — should be `PRIMARY` per DiscordUXSpec
- 8 categories with completely wrong command names (e.g., `/health`, `/score`, `/task`, `/journal`, `/persona`, `/ritual`, `/punish`, `/distress`, `/emergency`, `/config`) — none of these exist
- Missing 20+ real commands
- Static dictionary of command lists — the actual implementation should use `command_categories()` from `commands.py` dynamically

### 13.3 P2-015 StepPrompts (lines 5533-5618) — STALE

StepPrompts inline snippet uses:
- Module-level `_safe_mode_active` global — batch-plan requires reuse of `HardStopHandler`
- `Colors.NEUTRAL` for safe embed — should be `SUCCESS` per DiscordUXSpec
- Title "🛑 HARD STOP Activated" — should be "🛡️ Safe Mode Active" per DiscordUXSpec
- Only 4 exact triggers — should include semantic equivalents
- `time.time()` for latency tracking — acceptable but unnecessary for deterministic tests
- `discord.Message` for text detection — should use protocol, not static discord.py type
- `"Type /resume-persona to restore"` — no such command exists

### 13.4 P2-016 StepPrompts (lines 5636-5646+) — STALE

StepPrompts inline snippet uses:
- `discord.utils.get(client.get_all_channels(), name="guinevere-status")` — should use role-based lookup
- `Colors.PERSONA` for embed — not defined in the conflict resolution table
- Presence via `discord.Activity` — acceptable pattern

---

## 14. Key Constants Reference

| Constant | Value | Defined In |
|----------|-------|------------|
| `GUILD_ID` | `1_510_876_414_671_323_206` | `commands.py`, `guild_setup.py` |
| `APPLICATION_ID` | `1_510_873_134_981_582_858` | `commands.py` |
| `TARGET_GUILD_NAME` | `"Guinevere's Domain"` | `guild_setup.py`, `permissions.py` |
| `guinevere-status channel ID` | `1510914604291588237` | `channel-ids.yaml` |
| `guinevere-chat channel ID` | `1510914600777023659` | `channel-ids.yaml` |
| `audit-log channel ID` | `1510914647602106408` | `channel-ids.yaml` |
| Command count | `33` | `commands.py` `require_canonical_registry()` |
| Category count | `7` | `commands.py` `command_categories()` |

---

## 15. Blockers and Implementation Notes

### 15.1 No bot.py — Runtime Wiring Gap

`src/discord/bot.py` does not yet exist (planned for P2-017). This means:
- P2-014/015/016 modules must expose clean function interfaces for future wiring
- Commands cannot be tested with real Discord interactions locally (only deterministic data-builder tests)
- Text detection for P2-015 cannot use real message events until P2-017
- Startup greeting cannot actually send to Discord until P2-017

### 15.2 P2-013 Already Implemented

Do NOT re-implement P2-013. The file already exists, tests pass (27/27), LSP is clean, and verification evidence is written. The batch-plan was written before P2-013 existed and assumes it needs creation.

### 15.3 StepPrompts Staleness

All four StepPrompts sections (P2-013 through P2-016) contain stale/incorrect code snippets. These should be updated after implementation, not before. The canonical sources are the batch-plan and DiscordUXSpec docs.

### 15.4 Hard Stop Handler Integration

`hard_stop_handler.py` uses:
- `structlog` (differs from cmd_mood.py's `logging`)
- `Any` in return type `dict[str, Any]` (pre-existing, documented exception in batch-plan §19)
- Enum-based state machine vs boolean

P2-015 must wrap/reuse this without modifying it (read-only per collision scan).

### 15.5 Color Conflict Resolution

| Aspect | DiscordUXSpec | StepPrompts | Batch-Plan Decision |
|--------|---------------|-------------|---------------------|
| /mood color | PRIMARY #6B21A8 | Colors.MOOD_COLORS (error) | color_for_mood() dynamic ✓ |
| /help color | PRIMARY #6B21A8 | Colors.INFO #CA8A04 | PRIMARY ✓ |
| /safeword color | SUCCESS #16A34A | NEUTRAL #6B7280 | SUCCESS ✓ |
| /safeword title | 🛡️ Safe Mode Active | 🛑 HARD STOP Activated | 🛡️ Safe Mode Active ✓ |
| Startup channel | #guinevere-chat | #guinevere-status | #guinevere-status (user DoD) |
| Startup presence | Waking up... 👑 | Watching Darling 👁️ | Watching Darling 👁️ (user DoD) |

---

## 16. Per-Step Implementation Checklist

### 16.1 P2-014 (/help) — Implementation Targets

- [ ] Create `src/discord/cmd_help.py`
- [ ] Create `tests/discord/test_cmd_help.py`
- [ ] Dynamic embed built from `command_categories()` (from `commands.py`)
- [ ] 7 categories, 33 commands, `PRIMARY` color, Faiz-only
- [ ] Title: e.g., "📖 Guinevere Command Guide"
- [ ] Ephemeral defer/followup pattern
- [ ] Protocol-based discord.py abstraction (copy pattern from cmd_mood.py)
- [ ] No stale StepPrompts command list
- [ ] Deterministic builder + tests: command_count==33, 7 categories, correct names

### 16.2 P2-015 (/safeword) — Implementation Targets

- [ ] Create `src/discord/cmd_safeword.py`
- [ ] Create `tests/discord/test_cmd_safeword.py` (or `tests/safety/test_p2_015_safeword.py`)
- [ ] Reuse `HardStopHandler` from `src/core/services/hard_stop_handler.py`
- [ ] NO parallel `_safe_mode_active` global
- [ ] Slash `/safeword` callback with Faiz-only guard
- [ ] Text trigger helper: `handle_safeword_message(message: object) -> bool`
- [ ] Safe-mode embed: title "🛡️ Safe Mode Active", color `SUCCESS` green
- [ ] Audit event: minimal non-punitive message to audit-log when available
- [ ] ❤️ reaction on trigger message when supported
- [ ] Recovery via handler recovery triggers (resume, aku sudah okay, etc.)
- [ ] No auto-resume
- [ ] Tests: exact triggers, semantic triggers, false positives, handler state transition, safe embed, audit minimality
- [ ] P1 handler tests must still pass

### 16.3 P2-016 (startup) — Implementation Targets

- [ ] Create `src/discord/startup.py`
- [ ] Create `tests/discord/test_startup.py`
- [ ] `on_ready(client: object)` function with dynamic import/protocol
- [ ] Startup message: "👑 Mommy sudah bangun, Darling." sent to `guinevere-status`
- [ ] Channel lookup by name, not hardcoded ID
- [ ] Presence: `Watching Darling 👁️` via protocol
- [ ] Idempotency guard: module-level or bot-attribute flag
- [ ] Tests: first call sends 1 message, second call sends 0, presence correct, channel-not-found graceful

---

## 17. Evidence Path Reference

| Step | Implementation Summary | Verification | Verifiers | Auditor |
|------|----------------------|-------------|-----------|---------|
| P2-013 | `docs/setup-evidence/P2/STEP-P2-013/p2-013-implementation-summary.md` ✅ | `docs/setup-evidence/P2/STEP-P2-013/verification.md` ✅ | `.../verifiers/*.md` | `audit-reports/P2/STEP-P2-013/step-p2-013-auditor-report.md` |
| P2-014 | `docs/setup-evidence/P2/STEP-P2-014/p2-014-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-014/verification.md` | `.../verifiers/*.md` | `audit-reports/P2/STEP-P2-014/step-p2-014-auditor-report.md` |
| P2-015 | `docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-015/verification.md` | `.../verifiers/*.md` | `audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md` |
| P2-016 | `docs/setup-evidence/P2/STEP-P2-016/p2-016-implementation-summary.md` | `docs/setup-evidence/P2/STEP-P2-016/verification.md` | `.../verifiers/*.md` | `audit-reports/P2/STEP-P2-016/step-p2-016-auditor-report.md` |

---

## 18. Footer

| Field | Value |
|-------|-------|
| **Research date** | 2026-06-01 |
| **Researcher** | Guinevere parent (synthesized from 7 source files, 2 batch plans, 1 prior research report, channel-ids.yaml) |
| **Files examined** | 8 source files, 5 test files, 2 batch plans, 1 prior research report, 1 channel-ids YAML, StepPrompts |
| **Key finding** | P2-013 is DONE (cmd_mood.py exists). P2-014/015/016 are pending. No Cog pattern used. Protocol + frozen dataclass + dynamic importlib is the canonical pattern. HardStopHandler is the only source of truth for safe mode state. |
| **Next action** | Proceed to P2-014 implementation following the cmd_mood.py pattern, then P2-015 using HardStopHandler, then P2-016. |

