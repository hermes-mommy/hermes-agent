# Report 03: Hermes Native Discord Gateway

**Date:** 2026-06-04
**Version:** 1.0
**Scope:** Hermes Agent v0.15.2 native Discord gateway capabilities -- architecture, lifecycle, feature set, and current state
**Source:** VPS SSH session (`hermes gateway --help`), librarian research on Hermes Discord integration

---

## Executive Summary

Hermes Agent v0.15.2 includes a native Discord gateway as part of its multi-platform messaging system. The gateway manages the full lifecycle of Discord bot integration: installation, configuration, startup, runtime, and shutdown. It supports Discord intents, slash commands, and RBAC role-based access control. The gateway is part of a broader multi-platform architecture that also supports WhatsApp, Slack, and Telegram.

**Current State:** The gateway is installed but NOT configured and NOT running. No Discord bot token has been provided (confirmed by `hermes doctor`). No gateway setup has been performed. The existing GuinevereBot (`discord.ext.commands.Bot`) runs completely independently of the Hermes gateway.

---

## Gateway Architecture

### Multi-Platform Design

Hermes gateway is a unified messaging layer that routes conversations across platforms through a shared agent backend:

```
                    +---------------------------+
                    |     Hermes Agent Core     |
                    |  (LLM, Memory, Tools)     |
                    +------------+--------------+
                                 |
                    +------------+--------------+
                    |     Gateway Dispatcher     |
                    |  (Message Router, Auth,   |
                    |   Session Management)      |
                    +----+----+----+----+-------+
                         |    |    |    |
                +--------+    |    |    +--------+
                |             |    |             |
          +-----v-----+ +----v----v----+ +-----v-----+
          |  Discord   | |  WhatsApp   | |   Slack   |
          |  Gateway   | |   Gateway   | |  Gateway  |
          +-----+------+ +-----+-------+ +-----+-----+
                |               |               |
          +-----v-----+ +-----v-------+ +-----v-----+
          |  Discord   | |  WhatsApp   | |   Slack   |
          |    API     | |    API      | |    API    |
          +------------+ +-------------+ +-----------+
```

This architecture means Discord configuration is isolated from the agent core. Platform-specific features (intents, slash commands, role checks) are handled at the gateway layer.

### Gateway as a Service

The gateway runs as a background process managed by Hermes:

```
hermes gateway start    # Start gateway in background
hermes gateway stop     # Stop running gateway
hermes gateway restart  # Restart gateway
hermes gateway status   # Check gateway health
```

The gateway process maintains persistent WebSocket connections to Discord's Gateway API, handles reconnection, and manages heartbeat/keepalive.

---

## Gateway Lifecycle Commands

### Full Command Inventory

| Command | Syntax | Purpose |
|---------|--------|---------|
| `install` | `hermes gateway install` | Install gateway dependencies and register as service |
| `uninstall` | `hermes gateway uninstall` | Remove gateway service registration |
| `setup` | `hermes gateway setup` | Interactive setup wizard for platform configuration |
| `start` | `hermes gateway start` | Start the gateway process |
| `stop` | `hermes gateway stop` | Stop the gateway process |
| `restart` | `hermes gateway restart` | Restart the gateway process |
| `status` | `hermes gateway status` | Show gateway runtime status |
| `list` | `hermes gateway list` | List configured platform gateways |
| `run` | `hermes gateway run` | Run gateway in foreground (foreground process) |
| `migrate-legacy` | `hermes gateway migrate-legacy` | Migrate from legacy bot configuration |

### Lifecycle Flow

```
Installation:
  hermes gateway install
    -> Installs dependencies
    -> Registers gateway service
    -> Creates platform config stubs

Configuration:
  hermes gateway setup
    -> Interactive: asks for platform selection
    -> For Discord: requests bot token, guild ID, channel config
    -> For Discord: requests intents configuration
    -> For Discord: requests RBAC role mappings
    -> Writes to messaging section of config.yaml

Runtime:
  hermes gateway start
    -> Launches gateway process
    -> Connects to Discord Gateway API (WebSocket)
    -> Registers slash commands
    -> Begins message routing

Monitoring:
  hermes gateway status
    -> Shows uptime, connected platforms, message throughput

Shutdown:
  hermes gateway stop
    -> Graceful disconnect from Discord
    -> Drains pending messages
    -> Closes WebSocket connections
```

---

## Discord-Specific Capabilities

### Intents Support

Hermes Discord gateway supports Discord Gateway Intents, which control which events the bot receives:

| Intent | Required for Guinevere | Notes |
|--------|----------------------|-------|
| `GUILDS` | Yes | Basic guild information |
| `GUILD_MESSAGES` | Yes | Message content in guilds |
| `MESSAGE_CONTENT` | Yes | Privileged intent -- required for command parsing and HARD STOP detection |
| `GUILD_MEMBERS` | No | Not needed for single-channel operation |
| `PRESENCE` | No | Not needed |
| `DIRECT_MESSAGES` | No | Guinevere operates only in guild channels |

**Gap:** Current GuinevereBot already handles intents via `discord.ext.commands.Bot`. Hermes gateway setup should request the same intents currently configured. `MESSAGE_CONTENT` is the privileged intent that requires Discord Developer Portal approval.

### Slash Commands

Hermes gateway registers slash commands with Discord automatically on startup:

```yaml
# Conceptual -- actual Hermes config format TBD
messaging:
  discord:
    slash_commands:
      - name: chat
        description: Send a message to Guinevere
        handler: agent.chat
      - name: status
        description: Check Guinevere status
        handler: agent.status
```

**Key questions for migration:**
- Does Hermes map slash commands to agent tools/actions automatically?
- Can custom handlers be registered for commands not in the standard agent toolset?
- How are command permissions (RBAC) enforced at the slash command level?

### RBAC (Role-Based Access Control)

Hermes gateway supports role-based access for commands:

| RBAC Feature | Description |
|-------------|-------------|
| Role-to-command mapping | Specific Discord roles can access specific commands |
| Default deny | Commands are denied by default unless explicitly granted |
| Admin bypass | Admin role can access all commands |
| Channel scoping | Commands can be restricted to specific channels |

**Guinevere mapping:**
- `is_faiz_interaction()` guard in current code = Hermes RBAC with Faiz's user ID
- Admin commands (system, admin categories) = Hermes RBAC admin role
- Surveillance commands = Requires specific role + Faiz identity check
- Public commands (core category) = Allowlist of safe commands for all users

### Channel and Guild Scoping

| Scope | Current GuinevereBot | Hermes Gateway |
|-------|---------------------|----------------|
| Guild | GUILD_ID: 1510876414671323206 | Configurable in gateway setup |
| Channel | #guinevere-chat (ID: 1510914600777023659) | Configurable -- supports allowlist |
| DM support | None | Configurable |

---

## Interactive Setup Walkthrough

Based on librarian research, `hermes gateway setup` follows this interactive flow:

```
Step 1: Platform Selection
  "Which platforms would you like to configure?"
  [1] Discord
  [2] WhatsApp
  [3] Slack
  [4] Telegram
  [5] All

Step 2: Discord Token
  "Enter your Discord bot token:"
  > [DISCORD_BOT_TOKEN input]

Step 3: Guild Configuration
  "Enter the Discord guild (server) ID:"
  > [GUILD_ID input]
  "Restrict bot to specific channels? (y/n):"
  > y
  "Enter channel IDs (comma-separated):"
  > [CHANNEL_IDS input]

Step 4: Intents
  "Select intents to enable:"
  [x] GUILDS (required)
  [x] GUILD_MESSAGES (required)
  [ ] GUILD_MEMBERS
  [x] MESSAGE_CONTENT (recommended)
  [ ] PRESENCE

Step 5: RBAC Configuration
  "Configure role-based access? (y/n):"
  > y
  "Enter admin role ID:"
  > [ADMIN_ROLE_ID]
  "Enter operator role ID (optional):"
  > [OPERATOR_ROLE_ID]

Step 6: Confirmation
  "Configuration summary:
   - Platform: Discord
   - Guild: [GUILD_ID]
   - Channels: [CHANNEL_IDS]
   - Intents: GUILDS, GUILD_MESSAGES, MESSAGE_CONTENT
   - RBAC: enabled
   Save configuration? (y/n):"
  > y
```

---

## Configuration Storage

Gateway configuration is stored in the `messaging` section of `config.yaml`:

```yaml
messaging:
  discord:
    enabled: true
    token: "${DISCORD_BOT_TOKEN}"  # References .env
    guild_id: "1510876414671323206"
    channels:
      - "1510914600777023659"       # #guinevere-chat
    intents:
      - guilds
      - guild_messages
      - message_content
    rbac:
      enabled: true
      admin_role: "[ADMIN_ROLE_ID]"
      operator_role: "[OPERATOR_ROLE_ID]"
    slash_commands:
      auto_register: true
      guild_specific: true
```

---

## Current State Assessment

### Gateway Status

```
Command: hermes gateway status
Result:  Gateway not running
         No Discord configured
```

### Prerequisites Status

| Prerequisite | Status | Action |
|-------------|--------|--------|
| `.env` file | MISSING | Create with `DISCORD_BOT_TOKEN` |
| `config.yaml` | EXISTS but path mismatch | Fix path |
| Discord bot token | NOT CONFIGURED | Run `hermes gateway setup` |
| Gateway installed | INSTALLED | No action needed |
| Gateway service registered | UNKNOWN | Check with `hermes gateway list` |

### What Works Now

- Gateway CLI is functional
- `hermes gateway --help` returns full command documentation
- Gateway binary/package is installed as part of Hermes v0.15.2
- `install` subcommand has been run (or gateway is included in base install)

### What Does Not Work

- Gateway is not running
- No Discord bot token has been provided
- No platform configuration exists
- No slash commands are registered
- No WebSocket connection to Discord

---

## Multi-Platform Architecture

### Supported Platforms

| Platform | Command | Integration Method | Status for Guinevere |
|----------|---------|-------------------|---------------------|
| Discord | `hermes gateway` subcommands | Gateway WebSocket + REST API | Target -- not configured |
| WhatsApp | `hermes whatsapp` | BAW (Baileys WhatsApp) WebSocket | Not needed |
| Slack | `hermes slack` | Slack Events API + WebSocket | Not needed |
| Telegram | Via gateway (no standalone command) | Telegram Bot API | Not needed |

### Architecture Benefits

1. **Unified agent backend:** Same LLM, memory, and tools serve all platforms
2. **Isolated platform logic:** Discord-specific features don't pollute agent core
3. **Independent lifecycle:** Discord gateway can restart without restarting agent core
4. **Consistent auth model:** RBAC and session management shared across platforms

---

## Gap Analysis

### What Hermes Gateway Provides Natively

| Feature | Native Support | Notes |
|---------|---------------|-------|
| Discord WebSocket connection | Yes | Gateway manages lifecycle |
| Slash command registration | Yes | Auto-registers on startup |
| Intents management | Yes | Configurable in setup |
| RBAC | Yes | Role-based command access |
| Channel scoping | Yes | Allowlist channels |
| Guild scoping | Yes | Single guild or multi-guild |
| Multi-platform routing | Yes | Shared dispatcher |
| Session management | Yes | Hermes native sessions |
| Rate limiting | Yes | Hermes built-in |
| Message routing to agent | Yes | Messages flow to Hermes core |

### What Guinevere Needs That Gateway May Not Provide

| Need | Gateway Status | Risk |
|------|---------------|------|
| HARD STOP interception before LLM | Unknown | Critical -- must verify hook support |
| `_on_message_listener` equivalent | Unknown | High -- pre-processing hook needed |
| 33 custom slash commands | Unknown | High -- may require custom handler registration |
| `is_faiz_interaction()` guard | Partial | RBAC can handle role, but not complex multi-condition check |
| 10-step conversational pipeline | Not native | High -- pipeline is custom code |
| Custom PostgreSQL+pgvector memory | Not native | Medium -- `skip_memory` bridge still works |
| Streaming responses | Supported by Hermes | Neither current bot nor gateway has it |
| Reaction handling | Unknown | Low -- current bot supports reactions |
| Thread support | Not in Hermes | Neither has it |

### What Is Missing (Known)

1. **Gateway not configured:** Must run `hermes gateway setup` to provide token and config
2. **Environment not ready:** `.env` file required before setup
3. **Config path issue:** `config.yaml` not found by Hermes
4. **Token not available:** `DISCORD_BOT_TOKEN` listed as missing in `hermes doctor`
5. **Custom slash commands:** Unknown how to register Guinevere's 33 non-standard commands
6. **Pre-processing hooks:** Unknown if gateway supports message interception hooks

---

## Recommendations

### Immediate Actions (Unblocking)

1. **Create `.env`** file with `DISCORD_BOT_TOKEN` (use a test token, not production)
2. **Fix `config.yaml` path** so Hermes can find it
3. **Run `hermes gateway setup`** in interactive mode to understand the full configuration flow
4. **Document the setup** with screenshots or transcript for the migration plan

### Evaluation Actions (Before Migration Decision)

5. **Configure test guild:** Use a development/test guild, not the production guild (ID: 1510876414671323206)
6. **Test slash command registration:** Verify gateway registers commands successfully
7. **Test message routing:** Send messages and verify they reach Hermes agent core
8. **Test RBAC:** Verify role-based access restrictions work as documented
9. **Investigate hook system:** Determine if `hooks` CLI can register pre-processing interceptors
10. **Test with 9Router:** Verify gateway routes LLM calls through the configured model

### Design Actions (Migration Planning)

11. **Map 33 commands** to gateway registration format (see Report 04)
12. **Design hook for HARD STOP:** If gateway hooks support pre-processing
13. **Plan parallel run:** Both GuinevereBot and Hermes gateway running simultaneously
14. **Create rollback plan:** Document steps to revert to GuinevereBot if gateway fails

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|-----------|
| Gateway cannot handle 33 custom slash commands | Medium | High | Verify command registration API before committing |
| HARD STOP interception impossible via gateway | Medium | Critical | Must verify hook/pre-processing support |
| Gateway setup accidentally connects to production guild | Low | Critical | Use test guild and test token only |
| Gateway performance insufficient under load | Low | Medium | Load test with simulated message volume |
| Gateway conflicts with existing GuinevereBot | Medium | High | Do not run both on same guild/channel simultaneously |
| Hermes gateway update changes config format | Low | Medium | Pin Hermes version during migration |
| Discord rate limits on slash command registration | Low | Low | 33 commands is within Discord limits (100 per guild) |

---

## Cross-References

- **Report 01 (CLI-CAPABILITIES.md):** `hermes gateway` subcommand inventory
- **Report 02 (CONFIG-SYSTEM.md):** Messaging section of config.yaml
- **Report 04 (DISCORD-MIGRATION-GAP.md):** Side-by-side comparison and migration risk matrix

---

## Footer

| Field | Value |
|-------|-------|
| Author | Guinevere (Sisyphus-Junior) |
| Review Status | Draft |
| Date | 2026-06-04 |
| Hermes Version | v0.15.2 (2026.5.29.2) |
| Gateway Status | Not running, not configured |
| Evidence Source | `hermes gateway --help`, `hermes doctor`, librarian research |
| Next Review | After `hermes gateway setup` spike in test environment |