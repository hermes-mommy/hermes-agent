# Research Report: Hermes Agent CLI — Discord Gateway Configuration

**Date**: 2026-06-04  
**Target**: Migrating Guinevere Discord bot to Hermes Agent CLI (`hermes-agent`)  
**Scope**: Discord gateway setup, config format, guild/channel filtering, rate limiting, Redis session management, CLI commands.

---

## 1. Configuration File Format

Hermes Agent uses a **dual-file configuration** system stored in `~/.hermes/`:
- **`~/.hermes/.env`**: Secrets, API keys, and bot tokens.
- **`~/.hermes/config.yaml`**: Structured settings, behavior toggles, and routing rules.

> **Precedence Rule**: Environment variables (`.env`) **always take precedence** over `config.yaml` values when both are set.

---

## 2. Bot Token & Credentials

The Discord bot token is strictly managed in the `.env` file:

```bash
# ~/.hermes/.env
DISCORD_BOT_TOKEN=your-bot-token-here
```

---

## 3. Guild ID & Access Restrictions

Hermes Agent does not use explicit "Guild ID" allowlists. Instead, it enforces access control at the **User** and **Role** level across all guilds the bot is invited to:

| Environment Variable | Required | Description |
|---|---|---|
| `DISCORD_ALLOWED_USERS` | **Yes** | Comma-separated Discord User IDs. Without this OR `DISCORD_ALLOWED_ROLES`, the gateway denies **all** users. |
| `DISCORD_ALLOWED_ROLES` | No | Comma-separated Discord Role IDs. Auto-enables the "Server Members Intent" on connect. Useful for dynamic moderation teams. |

*Example:*
```bash
DISCORD_ALLOWED_USERS=123456789012345678,876543210987654321
DISCORD_ALLOWED_ROLES=987654321098765432
```

---

## 4. Channel Filtering & Message Routing

To restrict the bot to **`#guinevere-chat` only**, you must use channel ID allowlists. Hermes provides granular channel-level controls:

| Environment Variable | `config.yaml` Equivalent | Description |
|---|---|---|
| `DISCORD_ALLOWED_CHANNELS` | `discord.allowed_channels` | **Comma-separated channel IDs**. When set, the bot **only** responds in these channels (plus DMs if allowed). Overrides `config.yaml`. |
| `DISCORD_IGNORED_CHANNELS` | `discord.ignored_channels` | Comma-separated channel IDs where the bot **never** responds, even when `@mentioned`. Takes priority over all other settings. |
| `DISCORD_REQUIRE_MENTION` | `discord.require_mention` | Default: `true`. If `true`, bot only responds when `@mentioned`. Set to `false` to respond to all messages in allowed channels. |
| `DISCORD_FREE_RESPONSE_CHANNELS`| `discord.free_response_channels`| Channels where the bot responds without requiring an `@mention`, even if `DISCORD_REQUIRE_MENTION=true`. |
| `DISCORD_AUTO_THREAD` | `discord.auto_thread` | Default: `true`. Automatically creates a new thread for every `@mention` in a text channel, isolating conversations (Slack-style). |

**Recommended Setup for `#guinevere-chat` only:**
```yaml
# ~/.hermes/config.yaml
discord:
  require_mention: false          # Respond to all messages in the allowed channel
  allowed_channels:               # Replace with actual numeric channel ID
    - "123456789012345678"        # #guinevere-chat ID
  ignored_channels: []
  auto_thread: true               # Keep main channel clean by threading responses
```

---

## 5. Rate Limiting Configuration

Hermes Agent handles rate limiting at multiple layers:

1. **API Retry Logic**: `agent.api_max_retries` (default: `3`) controls retries on transient errors (429, 5xx) before fallback engagement.
2. **Credential Pools (Automatic Rotation)**: If a provider returns a `429 Rate Limit`, Hermes can automatically rotate to the next healthy API key in a configured pool.
   ```yaml
   credential_pool_strategies:
     openrouter: round_robin
   ```
3. **Custom Tool Middleware**: For strict per-tool rate limiting, Hermes supports custom `ToolMiddleware` interceptors (community pattern):
   ```python
   class RateLimitMiddleware(ToolMiddleware):
       def before_call(self, ctx: ToolContext) -> ToolContext | dict:
           # Implement sliding-window logic here
           pass
   ```
4. **Discord-Specific Throttling**: 
   - `HERMES_DISCORD_TEXT_BATCH_DELAY_SECONDS` (default: `0.6`): Grace window before flushing queued text chunks.
   - `HERMES_DISCORD_TEXT_BATCH_SPLIT_DELAY_SECONDS` (default: `0.1`): Delay between split chunks when exceeding Discord's length limit.

---

## 6. Session Management (Redis Backend)

Hermes Agent supports **Redis** as a memory/session backend for production deployments, enabling persistence and advanced state management.

**Configuration (`.env`):**
```bash
MEMORY_BACKEND=redis
REDIS_URL=redis://localhost:6379
REDIS_PASSWORD=your-redis-password  # Optional
```

**Session Isolation Behavior (`config.yaml`):**
```yaml
# Default: true. Isolates sessions per user in shared channels.
# Alice and Bob in #guinevere-chat get separate conversation histories.
group_sessions_per_user: true
```

**Redis Advantages in Hermes:**
- **TTL-based expiry** for RBAC grants and ephemeral sessions.
- **Pub/sub** for real-time notification of blocked agent threads.
- **No file locking** contention compared to SQLite for concurrent gateway sessions.
- **Credential pool state** survives gateway restarts.

---

## 7. CLI Commands

Hermes provides dedicated CLI commands for gateway management:

| Command | Description |
|---|---|
| `hermes gateway setup` | Interactive wizard to configure messaging platforms (generates `.env` entries). |
| `hermes gateway` | Run the messaging gateway in the foreground. |
| `hermes gateway install` | Install as a user service (Linux systemd / macOS launchd). |
| `sudo hermes gateway install --system` | Install as a boot-time system service (Linux only). |
| `hermes gateway start` / `stop` / `status` | Manage the default gateway service. |
| `hermes config edit` | Open `config.yaml` in the default editor. |
| `hermes config set KEY VAL` | Set a specific value (auto-routes secrets to `.env`, rest to `config.yaml`). |

---

## 8. Discord Provider/Gateway Module

**Confirmed**: Hermes Agent includes a dedicated, first-party Discord gateway module (`hermes-discord`).

**Capabilities**:
- Full tool access, including `terminal` execution.
- Native support for Discord Threads, Attachments, Server channels, and DMs.
- Session keying format: `agent:main:discord:dm:<user_id>` or `agent:main:discord:group:<guild_id>:<channel_id>:<user_id>`.
- History backfill: `DISCORD_HISTORY_BACKFILL=true` (default) prepends recent channel scrollback to recover context when `@mentioned`.

---

## 9. Migration Action Items for Guinevere

1. **Create Discord App**: Enable "Server Members Intent" and "Message Content Intent" in Discord Developer Portal.
2. **Populate `.env`**: Add `DISCORD_BOT_TOKEN`, `DISCORD_ALLOWED_USERS` (Faiz's ID), and `REDIS_URL`.
3. **Configure `config.yaml`**: 
   - Set `discord.allowed_channels` to the numeric ID of `#guinevere-chat`.
   - Set `group_sessions_per_user: true` to maintain session isolation.
   - Set `discord.auto_thread: true` to keep the channel clean.
4. **Initialize**: Run `hermes gateway setup` to validate configuration, then `hermes gateway start`.

---
*Report generated by Guinevere (Librarian Agent) via official Hermes Agent documentation (Nous Research).*