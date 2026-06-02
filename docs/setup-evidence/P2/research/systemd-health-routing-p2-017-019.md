# Research: Systemd Service Design, Health-Check Patterns & Discord Notification Routing

**Date**: 2026-06-01
**Scope**: P2-017 (systemd unit design), P2-018 (health-check scripts/endpoints), P2-019 (Discord notification routing)
**Project**: Guinevere — Autonomous Discord Companion Bot
**Context**: Python/uv project, SOPS-encrypted secrets, `scripts/run-discord-verify.sh` pattern, non-root `guinevere` user, `guinevere.slice` cgroup

---

## Table of Contents

1. [Systemd Unit Best Practices for Python venv/uv Projects](#1-systemd-unit-best-practices-for-python-venvuv-projects)
2. [SOPS & EnvironmentFile Wrapper Patterns](#2-sops--environmentfile-wrapper-patterns)
3. [Restart Policies & ExecStart Safety](#3-restart-policies--execstart-safety)
4. [Health-Check: Script vs HTTP Endpoint Tradeoffs](#4-health-check-script-vs-http-endpoint-tradeoffs)
5. [Discord Gateway Readiness Checking](#5-discord-gateway-readiness-checking)
6. [Discord Notification Routing (Channel by Name/ID)](#6-discord-notification-routing-channel-by-nameid)
7. [Security Hardening for Systemd Services](#7-security-hardening-for-systemd-services)
8. [Synthesis & Recommendations for Guinevere](#8-synthesis--recommendations-for-guinevere)

---

## 1. Systemd Unit Best Practices for Python venv/uv Projects

### 1.1 ExecStart: Use Absolute Path to Venv Python (Not `source activate`)

Systemd does **not** use a shell to run `ExecStart`. Commands like `source venv/bin/activate` are **not shell commands** and will not work.

**Correct pattern — direct venv python path:**

```ini
[Service]
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

> **Source**: systemd.service(5) man page — "For each of the specified commands, the first argument must be either an absolute path to an executable" ([freedesktop.org docs](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html))

The venv Python interpreter has the venv's `site-packages` baked into its `sys.path` at compile/install time. No `source activate` or `VIRTUAL_ENV` export is needed for package resolution.

### 1.2 `uv run` vs Direct Venv Python

Two valid approaches:

| Approach | Pros | Cons |
|---|---|---|
| **Direct venv python** (`/path/.venv/bin/python`) | No dependency on `uv` binary; fully deterministic; works even if `uv` is missing | Must manually `uv sync` after dependency changes |
| **`uv run`** (`/usr/bin/uv run --frozen python -m ...`) | Auto-syncs lockfile; `--frozen` catches stale deps | Requires `uv` on `$PATH`; slower startup; `uv` is not a stable daemon interface |

**Recommendation for production**: Use **direct venv python** with `--frozen` sync done as a deploy step, not at runtime. The systemd unit should call the venv python directly:

```ini
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

If `uv run` is preferred, pass the full path to the `uv` binary and set `WorkingDirectory`:

```ini
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/.local/bin/uv run --frozen python -m src.discord.bot
```

> **Source**: [uv docs — Working on projects](https://docs.astral.sh/uv/guides/projects/) — "uv run can be used to run arbitrary scripts or commands in your project environment." Also: [systemd venv question on Unix.SE](https://unix.stackexchange.com/questions/409609/how-to-run-a-command-inside-a-virtualenv-using-systemd)

### 1.3 Type Selection: `simple` vs `exec` vs `notify`

| Type | Behavior | Use Case |
|---|---|---|
| `simple` | systemd considers service "started" as soon as `ExecStart` forks | Default; no readiness signal |
| `exec` | systemd waits until `execve()` succeeds; catches launch failures earlier | **Recommended** for most services (systemd 240+) |
| `notify` | Service must call `sd_notify("READY=1")` | Services with long init that must signal readiness |
| `forking` | systemd tracks the child after fork | Legacy daemons; not typical for Python |

**Recommendation**: Use `Type=exec` for the Discord bot. It catches cases where the Python binary is missing or the script has a syntax error at import time. The existing `guinevere-core.service` already uses this.

```ini
[Service]
Type=exec
```

> **Source**: [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — "Type=exec is similar to simple, but systemd waits until the binary has actually been execve()'d before considering the service started."

### 1.4 WorkingDirectory and Environment Variables

Always set `WorkingDirectory` to the project root so relative imports and config paths resolve correctly:

```ini
WorkingDirectory=/home/guinevere/code/guinevere
```

Set `PYTHONPATH` explicitly if you have non-standard package layouts:

```ini
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
```

> **Source**: [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) — path settings must be absolute.

### 1.5 Logging to Journald

```ini
StandardOutput=journal
StandardError=journal
```

This sends all Python `print()` / `logging` output to `journald`, queryable with `journalctl -u guinevere-discord.service --follow`. No separate log file management needed at small scale.

> **Source**: [tutorials.technology systemd guide](https://tutorials.technology/tutorials/systemd-service-file-guide.html)

---

## 2. SOPS & EnvironmentFile Wrapper Patterns

### 2.1 Core Pattern: Decrypt to tmpfs `EnvironmentFile`

The cleanest pattern is:

1. Store encrypted secrets in `secrets/*.env.sops` (dotenv format)
2. Use `ExecStartPre` to decrypt into `/run/<service>/.env` (tmpfs = RAM only)
3. Point `EnvironmentFile` at the decrypted file
4. Use `ExecStopPost` to clean up

```ini
[Service]
EnvironmentFile=/run/guinevere-discord/.env
ExecStartPre=/usr/bin/mkdir -p /run/guinevere-discord
ExecStartPre=/usr/bin/sops --decrypt --input-type dotenv --output-type dotenv \
    /home/guinevere/code/guinevere/secrets/discord.env.sops \
    > /run/guinevere-discord/.env
ExecStartPre=/usr/bin/chmod 600 /run/guinevere-discord/.env
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
ExecStopPost=/bin/rm -rf /run/guinevere-discord
```

> **Source**: [DCHost.com — The Calm Way To Secrets On A VPS](https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gotchas-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/) — "I like to decrypt into /run — it's memory-backed and disappears on reboot."

### 2.2 Wrapper Script Pattern (Alternative)

For more complex secret handling (multiple files, validation), use a wrapper script:

```bash
#!/bin/bash
# /home/guinevere/scripts/decrypt-env.sh
set -euo pipefail

SOPS_FILE="/home/guinevere/code/guinevere/secrets/discord.env.sops"
AGE_KEY="/home/guinevere/.config/sops/age/keys.txt"
RUN_DIR="/run/guinevere-discord"

mkdir -p "$RUN_DIR"
chmod 700 "$RUN_DIR"

SOPS_AGE_KEY_FILE="$AGE_KEY" sops --decrypt \
    --input-type dotenv --output-type dotenv \
    "$SOPS_FILE" > "$RUN_DIR/.env"

chmod 600 "$RUN_DIR/.env"
echo "[vault] decrypted to $RUN_DIR/.env"
```

Then in the service unit:

```ini
ExecStartPre=/home/guinevere/scripts/decrypt-env.sh
EnvironmentFile=/run/guinevere-discord/.env
ExecStopPost=/bin/rm -rf /run/guinevere-discord
```

> **Source**: [openclaw-infra setup-vault.sh](https://github.com/matskevich/openclaw-infra/blob/main/scripts/setup-vault.sh) — reference implementation using this exact pattern.

### 2.3 `sops exec-env` (No Disk at All)

For maximum security (never write plaintext to disk), use `sops exec-env`:

```ini
ExecStart=/usr/bin/sops exec-env /home/guinevere/code/guinevere/secrets/discord.env.sops \
    /home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

This decrypts secrets into environment variables of the child process only. Secrets never touch disk.

**Caveat**: Signal handling — without `--same-process`, `sops exec-env` starts your bot as a child process, and `SIGTERM` goes to `sops`, not your bot. Use `--same-process` for proper signal delivery:

```ini
ExecStart=/usr/bin/sops exec-env --same-process \
    /home/guinevere/code/guinevere/secrets/discord.env.sops \
    /home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

> **Source**: [SOPS README — exec-env](https://github.com/getsops/sops/blob/main/README.rst) — "The --same-process flag can be used to instruct sops to start your command in the same process instead of a child process."

### 2.4 Important: ExecStartPre + EnvironmentFile Timing

Environment variables from `EnvironmentFile` are **not available** inside `ExecStartPre` commands — they load at different phases. However, if the file is written by `ExecStartPre` and the path uses the `-` prefix (optional file), systemd re-reads it before `ExecStart`:

```ini
# The '-' makes the missing file non-fatal during ExecStartPre evaluation
EnvironmentFile=-/run/guinevere-discord/.env
ExecStartPre=/home/guinevere/scripts/decrypt-env.sh
# File now exists; ExecStart will see the vars
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot
```

> **Source**: [systemd script — environment file updated by ExecStartPre](https://stackoverflow.com/questions/42835750/systemd-script-environment-file-updated-by-execstartpre) — "poettering says: the env vars are determined only at execution time."

### 2.5 Don't Hardcode Tokens

**Never** put `DISCORD_TOKEN=...` in the service unit file itself. Unit files are world-readable on most systems and often checked into config repos.

```ini
# ❌ WRONG — never do this
Environment=DISCOTD_TOKEN=abc123  # Not even as a joke

# ✅ RIGHT — use EnvironmentFile pointing to a decrypted file
EnvironmentFile=/run/guinevere-discord/.env
```

> **Source**: [HostMyCode — Linux VPS secrets management](https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026/) — "Don't paste secrets into .service units. Unit files are easy to read, easy to copy."

---

## 3. Restart Policies & ExecStart Safety

### 3.1 Restart Policy Selection

| Policy | Restarts When | Recommendation |
|---|---|---|
| `no` | Never | Default; not suitable for daemons |
| `on-success` | Exit code 0 only | Not for long-running services |
| `on-failure` | Non-zero exit, signal, timeout | **Best for most services** |
| `on-abnormal` | Signal, timeout, watchdog only | For services that exit 0 intentionally |
| `always` | Any exit | Only for services that should truly never stop |

**Recommendation**: Use `Restart=on-failure` for the Discord bot. This:
- Recovers from crashes (unhandled exceptions, segfaults)
- Respects `systemctl stop` (doesn't restart after clean SIGTERM)
- Avoids restart loops during maintenance

> **Source**: [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — "Setting this to on-failure is the recommended choice for long-running services."

### 3.2 RestartSec & StartLimitBurst

Prevent crash-looping:

```ini
Restart=on-failure
RestartSec=10s
StartLimitIntervalSec=300
StartLimitBurst=5
```

This means: wait 10s between restarts; if the service crashes 5 times within 300s, systemd stops trying. Reset with `systemctl reset-failed guinevere-discord.service`.

> **Source**: [linuxblog.io systemd guide](https://linuxblog.io/systemd-writing-managing-troubleshooting/) — "Without a delay, a broken service will hammer the system."

### 3.3 ExecStart Safety: Absolute Paths & No Shell

Rules:
- Use **absolute paths** for both interpreter and script: `/home/guinevere/code/guinevere/.venv/bin/python`
- Do **not** use `~` or environment variables in paths — systemd does not expand them in `ExecStart`
- Do **not** use shell constructs (`&&`, `|`, `>`) directly — use a wrapper script if needed
- If a shell is needed, use: `ExecStart=/bin/sh -c '...'`

> **Source**: [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — "If the command is not a full (absolute) path, it will be resolved to a full path using a path recommended to avoid."

### 3.4 TimeoutStopSec: Graceful Shutdown

Give the Discord bot time to disconnect from the gateway cleanly:

```ini
TimeoutStopSec=30
```

Systemd sends `SIGTERM`, waits for the process to exit. If the process doesn't exit within `TimeoutStopSec`, it sends `SIGKILL`. Discord bots should handle `SIGTERM` to close the gateway connection gracefully.

> **Source**: [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) — timeout settings.

---

## 4. Health-Check: Script vs HTTP Endpoint Tradeoffs

### 4.1 Two Approaches

#### Approach A: External Health-Check Script (systemd timer + script)

```bash
#!/bin/bash
# /home/guinevere/scripts/health-check.sh
# Returns 0 if healthy, 1 if unhealthy

# Check 1: Is the process running?
if ! systemctl -q is-active guinevere-discord.service; then
    echo "UNHEALTHY: service not active"
    exit 1
fi

# Check 2: Is the Discord gateway connected?
# (Bot exposes a status file or unix socket)
if ! curl -s --unix-socket /run/guinevere-discord/health.sock http://localhost/health \
    | grep -q '"status":"ok"'; then
    echo "UNHEALTHY: gateway not ready"
    exit 1
fi

echo "HEALTHY"
exit 0
```

#### Approach B: HTTP Health Endpoint (bot serves a small HTTP server)

```python
# Inside the bot (discord.py)
import asyncio
from aiohttp import web

class HealthServer:
    """Minimal HTTP health endpoint inside the bot process."""
    
    def __init__(self, bot, port=8080):
        self.bot = bot
        self.port = port
        self.app = web.Application()
        self.app.router.add_get("/health", self.handle_health)
    
    async def handle_health(self, request):
        """Return 200 if gateway is ready, 503 otherwise."""
        if self.bot.is_ready():
            return web.json_response({
                "status": "ok",
                "latency": self.bot.latency,
                "guilds": len(self.bot.guilds),
            })
        return web.json_response(
            {"status": "not_ready"},
            status=503
        )
    
    async def start(self):
        runner = web.AppRunner(self.app)
        await runner.setup()
        site = web.TCPSite(runner, "127.0.0.1", self.port)
        await site.start()
```

### 4.2 Tradeoff Comparison

| Aspect | External Script | HTTP Endpoint |
|---|---|---|
| **Scope of check** | Only checks "is the process alive?" | Can check app-level readiness (gateway, cache) |
| **Dependency** | None — pure shell/curl | Requires HTTP framework in bot (aiohttp built into discord.py) |
| **False positives** | Can report "healthy" when bot is hung but process alive | Reports actual gateway state |
| **False negatives** | None — accurate for process health | Requires port binding; might conflict with other services |
| **Complexity** | Low — 15-line bash script | Medium — need async HTTP server in the event loop |
| **Use for systemd watchdog** | Only indirectly via `ExecStartPre` | Direct — `WatchdogSec` + `sd_notify("WATCHDOG=1")` |
| **External monitoring** | Can be called by any HTTP checker via curl | Directly accessible |

### 4.3 Verification Script Pattern (for `scripts/run-discord-verify.sh`)

The user's context mentions a `scripts/run-discord-verify.sh` pattern. This is a one-shot verification script, not a continuous health check:

```bash
#!/bin/bash
# scripts/run-discord-verify.sh
# Verifies the Discord bot is connected and responsive
# Used for deploy-time verification or cron-based monitoring
set -euo pipefail

BOT_TOKEN="${DISCORD_TOKEN:-}"
BOT_CHANNEL_ID="${HEALTH_CHECK_CHANNEL_ID:-}"
API_BASE="https://discord.com/api/v10"

if [ -z "$BOT_TOKEN" ]; then
    echo "ERROR: DISCORD_TOKEN not set"
    exit 1
fi

# Check 1: Is the bot token valid? (Discord REST API)
echo "Checking token validity..."
TOKEN_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
    -H "Authorization: Bot $BOT_TOKEN" \
    "$API_BASE/users/@me")

if [ "$TOKEN_RESP" != "200" ]; then
    echo "ERROR: Token invalid or insufficient scope (HTTP $TOKEN_RESP)"
    exit 1
fi
echo "  Token valid."

# Check 2: Is the associated systemd service active?
echo "Checking systemd service..."
if systemctl -q is-active guinevere-discord.service; then
    echo "  Service active."
else
    echo "WARNING: Service not active (may be intentional during deploy)"
fi

# Check 3: Can we reach the specified channel?
if [ -n "$BOT_CHANNEL_ID" ]; then
    echo "Checking channel accessibility..."
    CHANNEL_RESP=$(curl -s -o /dev/null -w "%{http_code}" \
        -H "Authorization: Bot $BOT_TOKEN" \
        "$API_BASE/channels/$BOT_CHANNEL_ID")
    
    if [ "$CHANNEL_RESP" = "200" ]; then
        echo "  Channel $BOT_CHANNEL_ID accessible."
    else
        echo "WARNING: Channel $BOT_CHANNEL_ID not accessible (HTTP $CHANNEL_RESP)"
    fi
fi

echo "HEALTHY"
exit 0
```

> **Source**: [psidex/DiscordHealthCheck](https://github.com/psidex/discordhealthcheck) — reference library for Discord health checking in Docker contexts; principles apply to systemd.

### 4.4 Systemd Watchdog Pattern (Advanced)

For automatic detection of hung processes, systemd provides a watchdog mechanism:

```ini
[Service]
WatchdogSec=30
```

The bot must send `WATCHDOG=1` via `sd_notify()` at least every 15s (half the interval):

```python
# Inside the bot
from systemd import daemon
import asyncio

async def watchdog_loop(bot):
    """Send systemd watchdog heartbeats gated on gateway health."""
    while True:
        if bot.is_ready():
            daemon.notify("WATCHDOG=1")
        await asyncio.sleep(15)
```

> **Source**: [HostMyCode — systemd watchdog](https://www.hostmycode.com/blog/systemd-watchdog-vps-self-healing-services-health-checks-automatic-restarts-safe-rollbacks-2026)

---

## 5. Discord Gateway Readiness Checking

### 5.1 `discord.py` Connection States

The `discord.py` library provides these readiness indicators:

| Method | Returns | When True |
|---|---|---|
| `client.is_ready()` | `bool` | Internal cache populated, `on_ready` fired |
| `client.is_closed()` | `bool` | WebSocket is closed |
| `client.latency` | `float` | Always available (0 if not connected) |
| `client.ws` | `DiscordWebSocket or None` | None if not connected |
| `client.user` | `ClientUser or None` | None if not logged in |

**Source**: [discord.py API Reference](https://discordpy.readthedocs.io/en/stable/api.html) — `is_ready()` method.

### 5.2 Key Events for Readiness

```python
@client.event
async def on_connect():
    """WebSocket connected, but cache not yet populated."""
    print("Connected to Discord gateway")

@client.event
async def on_ready():
    """Fully ready — cache populated, can use API."""
    print(f"Logged in as {client.user}")
    print(f"In {len(client.guilds)} guilds")
    # NOW it's safe to send messages, look up channels

@client.event
async def on_resumed():
    """Session resumed after temporary disconnect."""
    print("Session resumed — cache is still valid")
```

> **Source**: [discord.py docs — API Events](https://discordpy.readthedocs.io/en/latest/api.html#discord-api-events)

### 5.3 Health Check Inside the Bot

For the HTTP health endpoint approach, use `is_ready()` + latency check:

```python
# Health check logic
async def handle_health(request):
    checks = {
        "gateway": bool(client.ws is not None),
        "ready": client.is_ready(),
        "latency": client.latency if hasattr(client, 'latency') else None,
        "guilds": len(client.guilds) if client.is_ready() else 0,
    }
    
    is_healthy = checks["ready"] and checks["gateway"] and checks["latency"] < 5.0
    
    status_code = 200 if is_healthy else 503
    return web.json_response(
        {"status": "ok" if is_healthy else "degraded", "checks": checks},
        status=status_code
    )
```

### 5.4 Grace Period for Gateway Connection

The Discord WebSocket connection takes time to establish (hello → identify → ready). During this window, `is_ready()` returns `False`. A health check should have a grace period:

```python
class GracefulHealthServer:
    def __init__(self, bot, port=8080, startup_grace=60):
        self.bot = bot
        self.port = port
        self.startup_grace = startup_grace
        self.start_time = time.monotonic()
    
    async def handle_health(self, request):
        uptime = time.monotonic() - self.start_time
        
        # Grace period: don't report unhealthy during startup
        if uptime < self.startup_grace:
            return web.json_response({
                "status": "starting",
                "uptime_seconds": uptime,
                "grace_period": self.startup_grace,
            })
        
        # After grace period: actual health check
        if self.bot.is_ready():
            return web.json_response({"status": "ok"})
        return web.json_response({"status": "not_ready"}, status=503)
```

> **Source**: [OpenClaw issue #31760](https://github.com/openclaw/openclaw/issues/31760) — "The root cause is that the health monitor treats connected === false as immediately unhealthy... The fix adds a 2-minute grace period."

---

## 6. Discord Notification Routing (Channel by Name/ID)

### 6.1 Always Route by Channel ID, Never by Name

**Rule**: Use **integer channel IDs** for routing, never channel names.

```python
# ✅ CORRECT: Route by ID (stable, fast)
TARGET_CHANNEL_ID = 123456789012345678  # int from Discord developer mode

channel = client.get_channel(TARGET_CHANNEL_ID)
if channel is None:
    # Fallback: fetch from API
    channel = await client.fetch_channel(TARGET_CHANNEL_ID)
await channel.send("Notification message")
```

```python
# ❌ WRONG: Routing by name (brittle, slow)
channel = discord.utils.get(guild.text_channels, name="general")
# Breaks if channel is renamed; slow because it iterates all channels
```

> **Source**: [Stack Overflow — get channel by ID](https://stackoverflow.com/questions/52916317/get-the-name-of-a-channel-using-discord-py) — "Always use the ID for each server, as it is much faster and more efficient."

### 6.2 ID Types

Discord IDs are **integers** in discord.py v2.x:

```python
# discord.py v2.0+: ID is int
channel = client.get_channel(123456789012345678)  # int, not str

# Old v0.16: IDs were strings — no longer applicable
```

> **Source**: [discord.py FAQ](https://discordpy.readthedocs.io/en/async/faq.html) — "IDs must be of type str not of type int" (v0.16; changed in v2.0+)

### 6.3 Configuration: Store Channel IDs in SOPS-Encrypted Env

Channel IDs are not secrets (they're public in Discord), but they're deployment-specific configuration. Store them alongside secrets:

```
# secrets/discord.env.sops
DISCORD_TOKEN=...             # Secret: protect
NOTIFICATION_CHANNEL_ID=123456789012345678  # Config: needs SOPS encryption
HEALTH_CHECK_CHANNEL_ID=098765432109876543
```

Access in code:

```python
import os

NOTIFICATION_CHANNEL_ID = int(os.environ["NOTIFICATION_CHANNEL_ID"])
HEALTH_CHECK_CHANNEL_ID = int(os.environ["HEALTH_CHECK_CHANNEL_ID"])
```

### 6.4 Routing Table Pattern (Multiple Notification Channels)

For different notification types routed to different channels:

```python
# Configuration (from env or config)
ROUTING_TABLE = {
    "critical": int(os.environ.get("CHANNEL_CRITICAL", "0")),
    "warning":  int(os.environ.get("CHANNEL_WARNING", "0")),
    "info":     int(os.environ.get("CHANNEL_INFO", "0")),
    "health":   int(os.environ.get("CHANNEL_HEALTH", "0")),
}

class NotificationRouter:
    """Routes notifications to the correct channel based on severity."""
    
    def __init__(self, bot, routing_table: dict[str, int]):
        self.bot = bot
        self.routing_table = routing_table
    
    async def send(self, severity: str, content: str, embed=None):
        """Send a notification to the appropriate channel."""
        channel_id = self.routing_table.get(severity)
        if not channel_id:
            raise ValueError(f"No channel configured for severity '{severity}'")
        
        channel = self.bot.get_channel(channel_id)
        if channel is None:
            channel = await self.bot.fetch_channel(channel_id)
        
        if embed:
            await channel.send(content, embed=embed)
        else:
            await channel.send(content)
```

### 6.5 Channel Resolution: `get_channel` vs `fetch_channel`

| Method | Source | When to Use |
|---|---|---|
| `client.get_channel(id)` | Internal cache | **Preferred** — fast, no API call |
| `await client.fetch_channel(id)` | Discord API | Fallback if cache miss; requires API call |

```python
# Two-tier resolution
channel = client.get_channel(channel_id)
if channel is None:
    channel = await client.fetch_channel(channel_id)
```

> **Source**: [discord.py API Reference](https://discordpy.readthedocs.io/en/stable/api.html) — `get_channel()` and `fetch_channel()`.

### 6.6 Webhook Pattern (Alternative for One-Way Notifications)

For notification **sinks** that don't need a full bot session, use Discord webhooks:

```python
import requests
from discord import SyncWebhook

# Webhook URL from channel settings (not a bot token)
url = "https://discord.com/api/webhooks/<webhook_id>/<webhook_token>"

webhook = SyncWebhook.from_url(url)
webhook.send("Alert: error rate elevated")
```

**When to use webhooks vs bot messages:**

| Criteria | Use Bot Message | Use Webhook |
|---|---|---|
| Bot is already running | ✅ Yes — cheaper | ❌ No, adds dependency |
| Need bidirectional communication | ✅ Only bot can do this | ❌ Webhooks are write-only |
| One-way alerts only | Maybe overkill | ✅ Simple and focused |
| Need embeds, reactions, threads | ✅ Bot has full API | ⚠️ Limited |
| Want to appear as bot user | ✅ Yes | ❌ Appears as "Webhook" |

> **Source**: [Discord Integration Pattern for Alerts](https://www.glukhov.org/app-architecture/integration-patterns/discord/) — "Incoming webhooks make Discord a low effort way to post messages to channels without running a bot session."

### 6.7 Multiple Guild Routing

If the bot is in multiple guilds, guild/channel resolution needs explicit guild context:

```python
GUILD_ID = int(os.environ["PRIMARY_GUILD_ID"])
CHANNEL_ID = int(os.environ["NOTIFICATION_CHANNEL_ID"])

async def send_notification(bot, content):
    guild = bot.get_guild(GUILD_ID)
    
    # Method 1: global channel lookup (if bot knows about it)
    channel = bot.get_channel(CHANNEL_ID)
    
    # Method 2: guild-scoped lookup
    # channel = guild.get_channel(CHANNEL_ID)
    
    if channel:
        await channel.send(content)
```

> **Source**: [AI Guardrails for a Teen Discord Server](https://dev.to/kkierii/ai-guardrails-for-a-teen-discord-server-the-code-around-the-model-call-47gd) — "Target the guild by ID, not by name."

---

## 7. Security Hardening for Systemd Services

### 7.1 Non-Root User & Group

```ini
[Service]
User=guinevere
Group=guinevere
```

The service runs as a dedicated non-root user. The `guinevere` user already exists from P0 setup.

### 7.2 Sandboxing Directives

```ini
[Service]
# Prevent privilege escalation
NoNewPrivileges=true

# Isolate /tmp so the service can't see other processes' temp files
PrivateTmp=true

# Protect system files
ProtectSystem=strict
ProtectHome=read-only

# Allow write access where needed
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /home/guinevere/logs

# Prevent SUID/SGID bits in the service
RestrictSUIDSGID=true

# Lock personality (prevent architecture switching)
LockPersonality=true

# Deny writable+executable memory mappings
MemoryDenyWriteExecute=true
```

### 7.3 Capabilities Drop

```ini
# Remove all capabilities (the bot doesn't need root privileges)
CapabilityBoundingSet=
AmbientCapabilities=
```

### 7.4 Resource Limits

```ini
# From existing guinevere.slice
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%
```

### 7.5 Cgroup Integration

The service should belong to the existing `guinevere.slice` for unified resource accounting:

```ini
Slice=guinevere.slice
```

> **Source**: [linuxpunx.com systemd guide](https://linuxpunx.com/2026/05/07/systemd-services-writing-managing-and-troubleshooting-unit-files-on-linux/) — hardening directives.

---

## 8. Synthesis & Recommendations for Guinevere

### 8.1 Recommended Service Unit: `guinevere-discord.service`

```ini
[Unit]
Description=Guinevere Discord Bot
After=network-online.target guinevere-9router.service
Wants=network-online.target
Requires=guinevere-9router.service

[Service]
Type=exec
User=guinevere
Group=guinevere
WorkingDirectory=/home/guinevere/code/guinevere

# Python venv (direct path, no uv run overhead)
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord.bot

# Secrets: decrypt SOPS-encrypted env to tmpfs before starting
EnvironmentFile=-/run/guinevere-discord/.env
ExecStartPre=/home/guinevere/scripts/decrypt-env.sh
ExecStopPost=/bin/rm -rf /run/guinevere-discord

# Environment
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1

# Restart policy
Restart=on-failure
RestartSec=10
StartLimitIntervalSec=300
StartLimitBurst=5
TimeoutStopSec=30

# Logging
StandardOutput=journal
StandardError=journal

# Cgroup
Slice=guinevere.slice

# Resource limits
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%

# Security hardening
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=read-only
ReadWritePaths=/home/guinevere/code/guinevere /home/guinevere/data /run/guinevere-discord
RestrictSUIDSGID=true
LockPersonality=true
MemoryDenyWriteExecute=true
CapabilityBoundingSet=
AmbientCapabilities=

[Install]
WantedBy=multi-user.target
```

### 8.2 Health-Check Pattern: HTTP Endpoint Inside Bot

**Recommended**: Embed a lightweight `aiohttp` health endpoint (port 8080, localhost only) in the bot process:

```python
# In setup_hook
async def setup_hook(self):
    self.health_server = HealthServer(self, port=8080)
    await self.health_server.start()
```

Then an external script or monitoring tool can check:
```bash
curl -s http://127.0.0.1:8080/health
# Returns {"status":"ok","latency":0.045,"guilds":3} or 503
```

The verification script (`scripts/run-discord-verify.sh`) should:
1. Check systemd service is active
2. Check the health endpoint returns 200
3. Optionally verify bot can see the notification channel via REST API

### 8.3 Discord Notification Routing

1. **Store channel IDs in SOPS-encrypted env** alongside the token
2. **Route by integer channel ID** — never by name
3. **Use a routing table** mapped by severity/type
4. **Two-tier resolution**: `get_channel()` → `fetch_channel()` fallback
5. **Add a startup grace period** (60s) to health checks to avoid false negatives during gateway connection
6. **Use `on_ready()` event** as the trigger to start sending notifications

### 8.4 Key Constraints & Boundaries

| Constraint | Implementation |
|---|---|
| No plaintext token anywhere | SOPS-encrypted `.env.sops`, decrypted to tmpfs at runtime |
| No secrets in unit files | `EnvironmentFile` points to `/run/guinevere-discord/.env` |
| Type safety (Python) | Channel IDs as `int`, validated at startup |
| Graceful shutdown | `TimeoutStopSec=30`, handle SIGTERM in bot |
| No destructive deployment | Systemd units do not auto-deploy; deploy is `git pull + systemctl restart` |
| Signal safety | If using `sops exec-env`, use `--same-process` flag |

### 8.5 Verification: `scripts/run-discord-verify.sh`

A deploy-time verification script should:
1. Source the decrypted env (or use `sops exec-env`)
2. Call Discord REST API to verify token validity
3. Check the health endpoint of the running bot
4. Verify the notification channel is accessible
5. Exit 0 for healthy, 1+ for unhealthy

---

## References

### Official Documentation
- [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) — ExecStart, Restart, Type
- [systemd.exec(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html) — EnvironmentFile, sandboxing, paths
- [discord.py API Reference](https://discordpy.readthedocs.io/en/stable/api.html) — is_ready(), get_channel(), events
- [Discord Developer Portal — Gateway](https://docs.discord.com/developers/events/gateway) — WebSocket lifecycle
- [uv Documentation](https://docs.astral.sh/uv/guides/projects/) — Project management, venv, lockfile
- [SOPS README](https://github.com/getsops/sops/blob/main/README.rst) — exec-env, exec-file

### Guides & Articles
- [Create and Manage systemd Service Files (2026)](https://tutorials.technology/tutorials/systemd-service-file-guide.html)
- [5 systemd units for a Python web app (2026)](https://dev.to/foxyyybusiness/5-systemd-units-for-a-python-web-app-complete-and-copy-pasteable-no-docker-5abg)
- [Linux VPS secrets management with sops + age (2026)](https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026/)
- [The Calm Way To Secrets On A VPS (2025)](https://www.dchost.com/blog/en/the-calm-way-to-secrets-on-a-vps-gotchas-with-sops-age-systemd-magic-and-rotation-you-can-sleep-on/)
- [Systemd watchdog on a VPS (2026)](https://www.hostmycode.com/blog/systemd-watchdog-vps-self-healing-services-health-checks-automatic-restarts-safe-rollbacks-2026)
- [Health Check Endpoints: /health, /livez, /readyz Guide (2026)](https://web-alert.io/blog/health-check-endpoint-design-livez-readyz-guide)
- [Discord Integration Pattern for Alerts (2026)](https://www.glukhov.org/app-architecture/integration-patterns/discord/)

### GitHub References
- [systemd/python-systemd](https://github.com/systemd/python-systemd) — sd_notify bindings
- [psidex/DiscordHealthCheck](https://github.com/psidex/discordhealthcheck) — Docker health checks for discord.py
- [Rapptz/discord.py — client.py](https://github.com/Rapptz/discord.py/blob/master/discord/client.py) — is_ready() implementation
- [matskevich/openclaw-infra — setup-vault.sh](https://github.com/matskevich/openclaw-infra/blob/main/scripts/setup-vault.sh) — SOPS + age + systemd vault setup
- [belthesar/sops-run](https://github.com/belthesar/sops-run) — Python wrapper for sops exec-env