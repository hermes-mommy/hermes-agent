# Domain 9: Discord Gateway — Research Report

**Generated**: 2026-06-29
**Method**: Read all 62 `.py` files in `src/discord/`; enumerated `cmd_*.py` files; parsed `_command_registry.py` COMMAND_SPECS tuple; read `_entrypoint.py` setup_hook; searched entire repo for bot identity names; read Hermes `gateway/run.py` header; searched for `consent_gate` usage.

---

## 1. File Inventory

### 1.1 Total Files

62 `.py` files in `src/discord/` (excluding `__pycache__`). 47 are `cmd_*.py` command modules. 2 `.bak.pre-phase2` archive files remain (`bot.py.bak.pre-phase2`, `conversational_handler.py.bak.pre-phase2`).

### 1.2 Infrastructure Modules (non-cmd)

| File | Purpose | Key Lines |
|---|---|---|
| `_entrypoint.py` | Active bot entrypoint. GuinevereBot class, setup_hook, main() | Lines 84-622 |
| `_command_registry.py` | Canonical COMMAND_SPECS tuple (41 entries), REST payload builders | Lines 130-302 |
| `_auth_guard.py` | Faiz-only gate: is_faiz_interaction() checks guild.owner_id == user.id | Lines 11-22 |
| `_intents.py` | Gateway intent config: message_content, members, presences, guilds, messages, reactions, voice_states | Lines 54-115 |
| `_startup.py` | Startup greeting embed + presence. on_ready() handler with idempotency guard | Lines 1-353 |
| `_embed_utils.py` | Shared embed protocols, dataclasses, helpers (DRY for all cmd modules) | Lines 1-50+ |
| `colors.py` | Canonical color palette (PRIMARY, ALERT, WARNING, SUCCESS, etc.) | Lines 1-125 |
| `hermes_conversational.py` | Hermes-native conversational handler for #guinevere-chat | Lines 1-690 |
| `notifications.py` | SEV alert routing (SEV0-SEV4) to Discord channels + Gotify fallback | Lines 1-241 |
| `gotify_fallback.py` | Gotify push notification fallback for SEV0/SEV1 | Lines 1-84 |
| `shadow_pipeline.py` | Shadow comparison pipeline (Hermes vs production, NEVER sends to Discord) | Lines 1-40+ |
| `shadow_monitor.py` | Shadow parity metrics, threshold checks, webhook alerts | Lines 1-491 |
| `project_session.py` | Active project UUID session state (P19-007) | Lines 1-47 |

### 1.3 Subdirectories

- `listeners/` — `gmail_reactions.py` (Gmail draft-approval via reactions), `x_reactions.py` (X Poster control via reactions)
- `loops/` — `__init__.py` only (imports `src.x_poster.discord.dashboard.create_dashboard`)

---

## 2. Slash Command Inventory

### 2.1 Canonical Registry: 41 Commands

`_command_registry.py:130-302` defines COMMAND_SPECS with exactly **41** CommandSpec entries. `require_canonical_registry()` at line 341-356 asserts `len(names) == 41` as a hard invariant.

**Categories** (from `_command_registry.py:320-327`):

| Category | Commands |
|---|---|
| core (6) | status, mood, help, safeword, new, history |
| loop (7) | loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority |
| memory (4) | memory-search, memory-add, memory-forget, memory-export |
| surveillance (3) | surveillance-status, surveillance-pause, surveillance-resume |
| finance (3) | cost, budget, cost-alert |
| system (7) | approve, deny, approve-all, focus, casual, consent, punishment, reward |
| admin (4) | restart-service, backup-now, health-check, clear-cache |
| integration (6) | integration-status, integration-capabilities, integration-test, integration-missing, integration-consent, integration-dry-run |

**Total: 41 commands. All 41 wired with real callbacks in _entrypoint.py setup_hook (no stubs remain).**

`_entrypoint.py:447` comment: "Stubs (none remaining -- all wired)"

### 2.2 Unregistered cmd_*.py Files (11 files)

These `cmd_*.py` files exist in `src/discord/` but have **no corresponding CommandSpec in the registry** and are **not wired in _entrypoint.py**:

| File | Callback(s) | Notes |
|---|---|---|
| `cmd_email.py` | email-digest, email-consent, email-reauth, email-search | 4 sub-commands, calls Gmail API at 127.0.0.1:8096 |
| `cmd_health_report.py` | health-report, health-trend, health-baseline | Queries TimescaleDB health tables |
| `cmd_loop_cost.py` | loop-cost (P5-018) | Aggregates cost stats from completed loops |
| `cmd_loop_history.py` | loop-history (P5-018) | Shows recent loop history |
| `cmd_loop_status.py` | loop-status (P5-018) | Shows last 10 loop instances |
| `cmd_memory_decay.py` | memory-decay (P18) | Active forgetting statistics |
| `cmd_memory_review.py` | memory-review (P18) | FSRS manual review trigger |
| `cmd_memory_schedule.py` | memory-schedule (P18) | FSRS review schedule |
| `cmd_memory_stats.py` | memory-stats (P18) | Tier distribution + FSRS stats |
| `cmd_pc.py` | pc (P15-010) | Windows daemon status |
| `cmd_project.py` | project, projects (P19-007) | Project switching + management |

These 11 files are **implemented but not registered** — they cannot be invoked via Discord slash commands in the current state.

---

## 3. Bot Identities

### 3.1 Finding: SINGLE Bot Only — @Guinevere

`_entrypoint.py:84` defines `class GuinevereBot(_BotBase)`. This is the **only** bot class. The prompt claims 3 bots (@Guinevere, @Pharsa, @Company). **This is WRONG.**

**Evidence**: Searched entire `src/` for "Pharsa", "Company", "multi-bot", "second-bot", "third-bot", "bot-identity" — **zero matches**. The only hit for "Company" is `src/knowledge_graph/extraction/patterns.py:434` (a regex pattern for corporate entity extraction) and `src/gmail/tests/test_e2e_gmail.py:495` (a test email address). Neither relates to a Discord bot identity.

**Corrected claim**: The codebase has exactly **one** Discord bot identity: **Guinevere** (GuinevereBot). No @Pharsa or @Company bot exists.

### 3.2 Bot Configuration

- **Guild ID**: 1_510_876_414_671_323_206 (`_entrypoint.py:46`)
- **Application ID**: 1_510_873_134_981_582_858 (`_command_registry.py:20`)
- **Token**: Read from `os.environ["DISCORD_BOT_TOKEN"]` (`_entrypoint.py:601`)
- **Prefix**: `!` (`_entrypoint.py:97`)
- **Channel**: #guinevere-chat ID 1_510_914_600_777_023_659 (`hermes_conversational.py:50`)

---

## 4. Gateway Architecture

### 4.1 No Custom gateway/run.py

There is **no** `gateway/run.py` in the repo. The Hermes upstream `gateway/run.py` (18,866 lines) lives in `.venv/Lib/site-packages/gateway/run.py` and is Hermes's generic multi-platform gateway runner (Telegram, Discord, WhatsApp, etc.). Guinevere does **not** use it — instead it uses `src/discord/_entrypoint.py` as its own bot entrypoint.

`_entrypoint.py:595-622` defines `async def main()` which creates GuinevereBot() and calls `bot.start(token)` directly.

### 4.2 Entrypoint Flow

1. `main()` reads DISCORD_BOT_TOKEN from env (`_entrypoint.py:601`)
2. Creates GuinevereBot() instance (`_entrypoint.py:608`)
3. GuinevereBot.__init__() calls get_intents(), registers HARD STOP listener, initializes ShadowPipeline and SurveillanceSafeModeGuard (`_entrypoint.py:93-116`)
4. setup_hook() registers all 41 slash commands (real callbacks) and guild-syncs (`_entrypoint.py:159-486`)
5. on_ready() logs readiness and calls startup_on_ready() for greeting + presence (`_entrypoint.py:534-551`)
6. on_message() checks safe mode, then tries conversational handler, then falls through to process_commands (`_entrypoint.py:555-589`)

### 4.3 Handler Registration Point

All command registration happens in setup_hook() at `_entrypoint.py:159-486`. Each command uses:

```
self.tree.command(name=..., description=..., guild=discord.Object(id=GUILD_ID))(callback_fn)
```

Guild-scoped sync at line 484-486:

```
guild = discord.Object(id=GUILD_ID)
synced = await self.tree.sync(guild=guild)
```

---

## 5. Autonomous Conversation Initiation

### 5.1 Finding: NO Autonomous Initiation Exists

The conversational handler (`hermes_conversational.py`) is **purely reactive**:

1. handle_conversation() is called from on_message() (`_entrypoint.py:585`)
2. It filters for #guinevere-chat channel only (`hermes_conversational.py:386`)
3. It requires a human-authored message to trigger (`hermes_conversational.py:390`)
4. It requires the message author to be the guild owner (`hermes_conversational.py:401`)

**There is no mechanism for a bot to initiate a conversation without a user trigger.** The shadow pipeline (`shadow_pipeline.py`) is a comparison/monitoring system, not an autonomous initiator.

### 5.2 Implications for M13 Design

Autonomous initiation (tied to M3 consciousness) does not exist yet. It would need to be **designed and implemented** as new code. Potential approaches:
- A background task/loop that monitors conditions and sends messages to #guinevere-chat
- Integration with the consciousness module (M3) to trigger proactive outreach
- Timer-based or event-based triggers (e.g., "check in every 4 hours", "notify when mood changes")

---

## 6. Consent Gate Analysis

### 6.1 cmd_consent.py is NOT a Command Gate

`cmd_consent.py` is a **consent management command** (/consent action:view|grant|revoke). It manages consent grants stored in Redis (consent:grants key). It does **not** gate/block other commands.

### 6.2 consent_gate Usage (Surveillance Only)

`src.surveillance.consent_gate` is imported by only 3 files in `src/discord/`:

| File | Line | Usage |
|---|---|---|
| `cmd_pc.py` | 234 | check_consent("surveillance.app_usage") — checks Windows surveillance consent |
| `cmd_surveillance_pause.py` | 116 | Imports consent_gate functions for pausing surveillance |
| `cmd_surveillance_status.py` | 157 | check_consent() for all surveillance scopes |

**No command is blocked by consent_gate.** The consent gate is a surveillance-scoping mechanism, not a command gating mechanism. The /consent command exists as a self-service management tool.

---

## 7. Key Dependencies for M13 PORT

| Component | Location | Notes |
|---|---|---|
| Command registry | `src/discord/_command_registry.py` | 41 specs, REST payload builders |
| Bot class | `src/discord/_entrypoint.py` | GuinevereBot, setup_hook, on_message |
| Auth guard | `src/discord/_auth_guard.py` | is_faiz_interaction() — Faiz-only gate |
| Intents | `src/discord/_intents.py` | 7 intent flags (3 privileged + 4 standard) |
| Embed utils | `src/discord/_embed_utils.py` | Shared embed protocols + helpers |
| Colors | `src/discord/colors.py` | Canonical color palette |
| Startup | `src/discord/_startup.py` | on_ready greeting + presence |
| Conversational | `src/discord/hermes_conversational.py` | Hermes-native chat handler |
| Notifications | `src/discord/notifications.py` | SEV0-SEV4 alert routing |
| Listeners | `src/discord/listeners/` | Gmail + X reaction handlers |
| Shadow | `src/discord/shadow_pipeline.py`, `shadow_monitor.py` | Comparison pipeline |
| Project session | `src/discord/project_session.py` | Active project state |

---

## 8. M13 Design Recommendations

### 8.1 Command PORT Strategy

**PORT** all 41 registered commands + the 11 unregistered cmd files into `guinevere/discord/commands.py`. The `_command_registry.py` pattern (dataclass CommandSpec + COMMAND_SPECS tuple + payload builders) is clean and should be preserved.

**Dispatch pattern**: Each `cmd_*.py` currently has an independent callback function. For M13, consolidate into a single `commands.py` with a registry dict mapping command name to callback.

### 8.2 Bot Identity (Single Bot)

Since only @Guinevere exists (no @Pharsa/@Company), `guinevere/discord/bots.py` should define a single GuinevereBot identity. If Pharsa/Company are planned, they would be NEW implementations.

### 8.3 gateway/run.py Patch

Not needed. Guinevere does not use Hermes's `gateway/run.py`. The entrypoint is `_entrypoint.py` with direct discord.py commands.Bot usage. M13 should port the main() entrypoint pattern.

### 8.4 Autonomous Initiation (NEW CODE)

No existing code to port. This requires NEW implementation:
- Background task loop in the bot (e.g., @tasks.loop(hours=4))
- Integration with M3 consciousness module for trigger conditions
- Target channel configuration (likely #guinevere-chat)

### 8.5 D2 Compliance (No Live Tokens)

All command registration is guild-scoped (guild=discord.Object(id=GUILD_ID)). Tests should use mock Interaction objects. The _auth_guard.py can be tested without a live guild by mocking interaction.guild.owner_id.

---

## 9. Disposition for P24

| Component | Disposition | Rationale |
|---|---|---|
| 41 registered commands | **PORT** | Core Discord functionality, all wired with real callbacks |
| 11 unregistered cmd files | **PORT** | Implemented but not yet wired; port as available commands |
| `_command_registry.py` pattern | **PORT** | Clean dataclass pattern, well-tested |
| `_auth_guard.py` | **PORT** | Faiz-only gate, simple and effective |
| `_intents.py` | **PORT** | Gateway configuration, required for bot startup |
| `_startup.py` | **PORT** | Startup greeting + presence |
| `_embed_utils.py` | **PORT** | Shared infrastructure for all commands |
| `colors.py` | **PORT** | Canonical color palette |
| `hermes_conversational.py` | **PORT** | Core conversational handler (Hermes-native) |
| `notifications.py` | **PORT** | SEV alert routing |
| `gotify_fallback.py` | **PORT** | Push notification fallback |
| `shadow_pipeline.py` + `shadow_monitor.py` | **PORT** | Shadow comparison infrastructure |
| `project_session.py` | **PORT** | Active project state |
| `listeners/` | **PORT** | Gmail + X reaction handlers |
| `loops/__init__.py` | **PORT** | X poster dashboard import |
| Autonomous initiation | **MODIFY-CREATE** | Does not exist yet; needs new implementation |
| Multi-bot (Pharsa/Company) | **DELETE** (from plan) | Does not exist in codebase; plan claim is wrong |
| `bot.py.bak.pre-phase2` | **DELETE** | Archive backup, not needed |
| `conversational_handler.py.bak.pre-phase2` | **DELETE** | Archive backup, not needed |

---

## 10. Risks

1. **11 unregistered commands**: cmd_email, cmd_health_report, cmd_loop_cost, cmd_loop_history, cmd_loop_status, cmd_memory_decay, cmd_memory_review, cmd_memory_schedule, cmd_memory_stats, cmd_pc, cmd_project are implemented but cannot be invoked. M13 should register all of them.
2. **External service dependencies**: Many commands depend on external services (Redis on port 6380, Gmail API on 127.0.0.1:8096, X Poster on 127.0.0.1:8097, Gotify on localhost:8081, PostgreSQL/TimescaleDB). D2 local-runtime-only means these need mocking.
3. **Consent gate is NOT a command gate**: The plan's mention of "consent_gate removed (no cmd_consent gating)" is a mischaracterization. cmd_consent.py is a consent management command, not a gating mechanism. consent_gate from src.surveillance.consent_gate is a surveillance-scoping module.
4. **No autonomous initiation exists**: The plan references this as existing — it does not. This is a greenfield implementation for M13.
5. **Single bot only**: The plan's claim of "3 bots (@Guinevere/@Pharsa/@Company)" is factually incorrect. Only @Guinevere exists.

---

## 11. Verdict

**PASS** — The Discord gateway domain is well-structured for PORT. The _command_registry.py + _entrypoint.py architecture is clean, with 41 canonical commands all wired with real callbacks. Key corrections to the plan: (1) only 1 bot identity exists, not 3; (2) no autonomous initiation exists to port; (3) consent_gate is not a command gate. The 11 unregistered cmd files represent additional portable surface area not mentioned in the plan.
