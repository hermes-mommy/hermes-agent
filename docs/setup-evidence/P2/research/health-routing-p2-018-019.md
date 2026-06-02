# Health-Check & Notification-Routing Patterns — discord.py

**Date**: 2026-06-01  
**Scope**: P2-018 (online-status health verification) + P2-019 (message routing to `guinevere-status`, `cost-tracker`, `audit-log`)  
**Library**: discord.py v2.7.x (latest stable, 2026-03-03)  
**Docs**: <https://discordpy.readthedocs.io/en/latest/>

---

## 1. Gateway Readiness State

discord.py exposes these properties to determine bot connection state:

| Property | Type | Meaning |
|---|---|---|
| `bot.is_ready()` | `bool` | Internal cache populated; guilds, members, channels ready for use |
| `bot.is_closed()` | `bool` | WebSocket connection closed |
| `bot.latency` | `float` | Seconds between HEARTBEAT and HEARTBEAT_ACK (WebSocket RTT) |
| `bot.ws` | `WebSocket` | Gateway connection object (None if not connected) |

**Key nuance**: `on_ready()` can fire **multiple times** — Discord reconnection logic calls it whenever a RESUME request fails. Do **not** put one-shot setup there; use `setup_hook()` instead.

**Evidence** — official docs:
- `is_ready()`: <https://discordpy.readthedocs.io/en/latest/api.html#discord.Client.is_ready>
- `latency` property: <https://discordpy.readthedocs.io/en/latest/api.html#discord.Client.latency>
- `on_ready()` warning: <https://discordpy.readthedocs.io/en/latest/api.html#discord.on_ready>

---

## 2. Health-Check Patterns

### 2a. In-Process Script Check (simplest)

```python
# Called from @tasks.loop or after on_ready()
async def check_health(bot):
    return {
        "ready": bot.is_ready(),
        "closed": bot.is_closed(),
        "latency_ms": round(bot.latency * 1000, 1) if bot.latency else None,
        "guild_count": len(bot.guilds),
        "user": str(bot.user) if bot.user else None,
    }
```

- Pros: zero external infra, inline with bot process
- Cons: cannot detect process death (zombie process still reports ready)

**Real-world usage** — `bot.is_ready()` guard pattern (Red-DiscordBot, Dredd, Miso-bot):

<https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/_debuginfo.py#L54-L59>

```python
@property
def is_connected(self) -> bool:
    return self.bot is not None and self.bot.is_ready()
```

---

### 2b. External HTTP Health Endpoint

Run a lightweight HTTP server (Flask/aiohttp) inside the bot process to expose health data:

```python
# Using aiohttp in setup_hook()
async def setup_hook(self):
    self._health_server = await asyncio.start_server(
        self._handle_health, "0.0.0.0", 8080
    )
```

**JSON response shape** (synthesised from common patterns):

```json
{
  "status": "ok",
  "discord_connection": "connected",
  "discord_heartbeat_latency": "63 ms",
  "uptime_seconds": 3600,
  "guild_count": 12,
  "last_ready": "2026-06-01T10:00:00Z"
}
```

**Real-world pattern** (Code of Connor, 2022):

```bash
# External cron job hits the endpoint
details=$(curl -sSf http://localhost:8000/health)
curl -m 10 --retry 5 --data-raw "$details" https://hc-ping.com/<id>/$?
```

**Tradeoffs**:

| Approach | Detects Process Death | Detects Gateway Death | External Deps |
|---|---|---|---|
| In-process script | ❌ | ✅ | None |
| HTTP endpoint + uptime monitor | ✅ | ✅ | Flask/aiohttp + external monitor |
| External cron (self-ping) | ✅ | ✅ | cron + healthchecks.io / similar |

---

### 2c. External Health Checks Library

`discordhealthcheck` (PyPI) provides a TCP socket server that tests client latency, login status, and returns exit code 0/1 for Docker HEALTHCHECK integration.

Docs: <https://pypi.org/project/discordhealthcheck/>

```python
from discordhealthcheck import start

async def setup_hook(self):
    self.healthcheck_server = await start(self, port=40404, bot_max_latency=0.5)
```

Docker HEALTHCHECK:

```dockerfile
HEALTHCHECK CMD discordhealthcheck || exit 1
```

**Caveat**: tests WebSocket latency but not application-level logic (database, external APIs). For P2-018, combine gateway health with a synthetic transaction (e.g. fetch a known channel) for true end-to-end verification.

---

## 3. Notification Routing by Channel Name

### 3a. Resolve Channel by Name (Primary Pattern)

```python
import discord

# Option A: From a specific guild
channel = discord.utils.get(guild.text_channels, name="guinevere-status")

# Option B: Across all guilds the bot sees
channel = discord.utils.get(bot.get_all_channels(), name="guinevere-status")
```

**Evidence** — official FAQ docs:

<https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-get-a-specific-model>

```python
# find a guild by name
guild = discord.utils.get(client.guilds, name='My Server')
if guild is not None:
    # find a channel by name
    channel = discord.utils.get(guild.text_channels, name='cool-channel')
```

**Real-world examples**:

- Channel-by-name lookup (Red-DiscordBot):  
  <https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/utils/predicates.py#L448-L454>  
  ```python
  result = discord.utils.get(guild.text_channels, name=m.content)
  ```

- Log channel by name (JHDBot):  
  <https://github.com/JH-Discord/JHDBot/blob/main/JHDBot/bot.py#L150-L162>  
  ```python
  logchannel = discord.utils.get(channel.guild.channels, name="maintenance")
  ```

- Fallback chain (wespreadjam bot):  
  <https://github.com/wespreadjam/jam-discord-bot/blob/main/bot.py#L473-L478>  
  ```python
  if REFERRAL_CHANNEL_NAME:
      ch = discord.utils.get(guild.text_channels, name=REFERRAL_CHANNEL_NAME)
      if ch:
          return ch
  return guild.system_channel
  ```

### 3b. Send Pattern with Fail-Soft Logging

```python
import logging
logger = logging.getLogger("guinevere")

async def send_notification(bot, channel_name: str, content: str, embed=None):
    """Send a message to a named channel. Fail-soft: log errors, never crash."""
    try:
        channel = discord.utils.get(bot.get_all_channels(), name=channel_name)
        if channel is None:
            logger.warning("Channel '%s' not found — notification dropped", channel_name)
            return
        await channel.send(content=content, embed=embed)
    except discord.Forbidden:
        logger.warning("Missing permissions for channel '%s'", channel_name)
    except discord.HTTPException as e:
        logger.error("HTTP error sending to channel '%s': %s", channel_name, e)
    except Exception as e:
        logger.exception("Unexpected error sending to '%s': %s", channel_name, e)
```

### 3c. Routing Grid for P2-019

| Target Channel | Routing Trigger | Content Type |
|---|---|---|
| `guinevere-status` | Bot ready, health check result, heartbeat threshold breach | Plain text or embed with status/uptime/latency |
| `cost-tracker` | Cost/resource usage reports (periodic or on threshold) | Embed with numeric breakdown |
| `audit-log` | Critical events: config change, error, command usage | Rich embed with timestamp + diff |

---

## 4. Avoiding Hardcoded Tokens and IDs

**Never embed channel names, guild IDs, or tokens in source code.**

Use environment variables loaded via `os.environ.get()`:

```python
import os

# Channel names (not IDs) for portability across environments
CHANNEL_STATUS  = os.environ.get("GUINEVERE_CHANNEL_STATUS", "guinevere-status")
CHANNEL_COST    = os.environ.get("GUINEVERE_CHANNEL_COST", "cost-tracker")
CHANNEL_AUDIT   = os.environ.get("GUINEVERE_CHANNEL_AUDIT", "audit-log")
GUILD_ID        = int(os.environ["GUINEVERE_GUILD_ID"])  # from env, not code
BOT_TOKEN       = os.environ["DISCORD_BOT_TOKEN"]        # never hardcoded
```

**Pattern**: Use `.env` file + `python-dotenv` for local dev; pass via Docker env or secrets manager in production.

**Real-world** (RagFlow / Onyx connectors):  
<https://github.com/infiniflow/ragflow/blob/main/common/data_source/discord_connector.py#L401-L406>

```python
channel_names: str | None = os.environ.get("channel_names", None)
connector = DiscordConnector(
    server_ids=server_ids.split(",") if server_ids else [],
    channel_names=channel_names.split(",") if channel_names else [],
)
```

---

## 5. Latency / Heartbeat Indicator

```python
# Client.latency is in seconds; typically 0.05–0.3 for healthy connections
latency_ms = round(bot.latency * 1000, 1)

# Threshold-based alerting
if bot.latency > 1.0:
    logger.warning("High latency: %.1f ms", latency_ms)
    # optionally alert to guinevere-status
```

**Evidence** — official API: <https://discordpy.readthedocs.io/en/latest/api.html#discord.Client.latency>

> Measures latency between a HEARTBEAT and a HEARTBEAT_ACK in seconds.

**Sharded bot**: use `bot.latencies` (list of per-shard latencies) and `bot.average_latency`.

---

## 6. JSON Health Response Shape (HTTP Endpoint)

Recommended shape for a `/health` endpoint exposed by the bot:

```json
{
  "status": "ok",
  "version": "1.0.0",
  "discord": {
    "connected": true,
    "ready": true,
    "latency_ms": 63.2,
    "guilds": 12,
    "user": "Guinevere#1234"
  },
  "system": {
    "uptime_seconds": 3600,
    "python_version": "3.12.0"
  },
  "checks": {
    "gateway": "pass",
    "api_reachability": "pass"
  }
}
```

Use `503 Service Unavailable` instead of `200 OK` when `bot.is_ready()` is False, so external monitors (UptimeRobot, BetterStack) correctly detect outage.

---

## 7. Summary of Patterns for P2-018 and P2-019

| Requirement | Recommended Pattern | Key API / Tool |
|---|---|---|
| **P2-018**: Online status health | `bot.is_ready()` + `bot.latency` in a `@tasks.loop`; optionally expose `/health` HTTP endpoint | `Client.latency`, `Client.is_ready()`, `discordhealthcheck` lib |
| **P2-019**: Route to named channels | `discord.utils.get(bot.get_all_channels(), name=...)` with fail-soft `try/except` + logging | `discord.utils.get()`, `channel.send()` |
| **P2-019**: Avoid hardcoded tokens | Env vars via `os.environ.get()`; `.env` file for dev | `python-dotenv`, `os.environ` |
| **P2-019**: Fail-soft logging | Wrap `channel.send()` in `try/except` with `logger.warning`/`error` | `logging` module |
| **P2-018**: Process-death detection | External cron / healthchecks.io / Docker HEALTHCHECK hitting bot HTTP endpoint | `aiohttp` / `Flask` + uptime monitor |
| **P2-019**: Channel routing map | Static dict `{"status": ..., "cost": ..., "audit": ...}` populated from env vars | `os.environ.get("GUINEVERE_CHANNEL_*")` |

---

## References

1. discord.py API — Client: <https://discordpy.readthedocs.io/en/latest/api.html#discord.Client>
2. discord.py FAQ — Get specific model: <https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-get-a-specific-model>
3. discord.py FAQ — Send to channel: <https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-send-a-message-to-a-specific-channel>
4. discord.py `utils.get()`: <https://discordpy.readthedocs.io/en/latest/api.html#discord.utils.get>
5. discordhealthcheck PyPI: <https://pypi.org/project/discordhealthcheck/>
6. DiscordHealthCheck GitHub: <https://github.com/psidex/DiscordHealthCheck>
7. Code of Connor health check writeup: <https://codeofconnor.com/monitoring-my-discord-bot/>
8. AutoGPT Discord block — channel-by-name lookup: <https://github.com/Significant-Gravitas/AutoGPT/blob/master/autogpt_platform/backend/backend/blocks/discord/bot_blocks.py#L254-L268>
9. JHDBot — channel by name log routing: <https://github.com/JH-Discord/JHDBot/blob/main/JHDBot/bot.py#L150-L162>
10. Red-DiscordBot — `is_ready()` + property pattern: <https://github.com/Cog-Creators/Red-DiscordBot/blob/V3/develop/redbot/core/_debuginfo.py#L54-L59>