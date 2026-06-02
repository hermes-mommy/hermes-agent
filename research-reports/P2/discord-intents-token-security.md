# Discord Bot Gateway Intents & Token Security — Research Report

> **Scope**: Discord gateway intents (privileged, minimal intents principle), bot token storage patterns, SOPS+age encryption, logging redaction, and verification methods for discord.py 2.x.
>
> **Prepared for**: P2-002 (bot token handling) & P2-003 (gateway intents configuration) acceptance checks.
>
> **Date**: 2026-06-01

---

## Table of Contents

1. [Gateway Intents Overview](#1-gateway-intents-overview)
2. [Privileged Intents](#2-privileged-intents)
   - [2.1 GUILD_PRESENCES (1 << 8)](#21-guild_presences-1--8)
   - [2.2 GUILD_MEMBERS (1 << 1)](#22-guild_members-1--1)
   - [2.3 MESSAGE_CONTENT (1 << 15)](#23-message_content-1--15)
3. [Minimal Intents Principle](#3-minimal-intents-principle)
4. [discord.py 2.x Intents API](#4-discordpy-2x-intents-api)
5. [Bot Token Storage Patterns](#5-bot-token-storage-patterns)
   - [5.1 Environment Variables (Local Dev)](#51-environment-variables-local-dev)
   - [5.2 SOPS + age (Production / VPS)](#52-sops--age-production--vps)
   - [5.3 Fail-Fast Validation](#53-fail-fast-validation)
6. [Logging Redaction](#6-logging-redaction)
   - [6.1 discord.py Default Logging](#61-discordpy-default-logging)
   - [6.2 Token Redaction Strategy](#62-token-redaction-strategy)
7. [Verification Methods](#7-verification-methods)
8. [P2-002 / P2-003 Acceptance Checks](#8-p2-002--p2-003-acceptance-checks)
9. [Common Pitfalls](#9-common-pitfalls)
10. [Sources](#10-sources)

---

## 1. Gateway Intents Overview

Gateway intents are bitwise values passed in the `intents` parameter when Identifying (sending `opcode 2`) to the Discord Gateway. They allow a bot to subscribe to specific buckets of events, reducing computational burden and bandwidth.

**Key facts:**

- **Required as of API v8** (current API version is v10). If you don't specify intents, the Gateway will close your connection.
- Intents are **ORed** together (e.g., `intents = GUILDS | GUILD_MEMBERS`).
- Two types exist: **standard intents** (enabled by default, no extra config) and **privileged intents** (must be manually toggled in Developer Portal + may need verification approval).
- Closing a connection with invalid intents produces close code `4013`; using a privileged intent without enabling it produces close code `4014`.

**Intent-to-event mapping** (abbreviated; see [official Gateway docs](https://docs.discord.com/developers/events/gateway) for full list):

| Intent | Bit | Key Events |
|---|---|---|
| `GUILDS` | 1 << 0 | GUILD_CREATE, CHANNEL_*, THREAD_*, ROLE_* |
| `GUILD_MEMBERS` | 1 << 1 | GUILD_MEMBER_ADD/UPDATE/REMOVE |
| `GUILD_MODERATION` | 1 << 2 | AUDIT_LOG_ENTRY_CREATE, BAN_ADD/REMOVE |
| `GUILD_EXPRESSIONS` | 1 << 3 | EMOJIS_UPDATE, STICKERS_UPDATE |
| `GUILD_INTEGRATIONS` | 1 << 4 | INTEGRATION_* |
| `GUILD_WEBHOOKS` | 1 << 5 | WEBHOOKS_UPDATE |
| `GUILD_INVITES` | 1 << 6 | INVITE_CREATE/DELETE |
| `GUILD_VOICE_STATES` | 1 << 7 | VOICE_STATE_UPDATE |
| **`GUILD_PRESENCES`** | **1 << 8** | **PRESENCE_UPDATE — privileged** |
| `GUILD_MESSAGES` | 1 << 9 | MESSAGE_CREATE/UPDATE/DELETE |
| `GUILD_MESSAGE_REACTIONS` | 1 << 10 | REACTION_* |
| `GUILD_MESSAGE_TYPING` | 1 << 11 | TYPING_START |
| `DIRECT_MESSAGES` | 1 << 12 | DM MESSAGE_* |
| `DIRECT_MESSAGE_REACTIONS` | 1 << 13 | DM REACTION_* |
| `DIRECT_MESSAGE_TYPING` | 1 << 14 | DM TYPING_START |
| **`MESSAGE_CONTENT`** | **1 << 15** | **Message content fields — privileged** |
| `GUILD_SCHEDULED_EVENTS` | 1 << 16 | SCHEDULED_EVENT_* |
| `AUTO_MODERATION_CONFIG` | 1 << 20 | AUTO_MOD_RULE_* |
| `AUTO_MODERATION_EXECUTION` | 1 << 21 | AUTO_MOD_ACTION_EXECUTION |

---

## 2. Privileged Intents

Three privileged intents exist. All require:

1. **Manual toggle** in Developer Portal → Application → Bot → "Privileged Gateway Intents" section.
2. **Approval** if the bot is verified (100+ guilds).
3. **Code-level enabling** — portal toggle alone is insufficient; you must also set the intent in Python.

### 2.1 GUILD_PRESENCES (1 << 8)

Controls access to `PRESENCE_UPDATE` events and `Member.status` / `Member.activity`.

**Do you need it?** Only if your bot tracks online statuses, custom statuses, or activities (e.g., "currently playing" games). Most moderation or utility bots do **not** need this.

**Cost**: High volume — presence updates fire frequently for every member in every shared guild. Enabling without need wastes bandwidth and CPU.

### 2.2 GUILD_MEMBERS (1 << 1)

Controls access to:
- `on_member_join()` / `on_member_remove()` / `on_member_update()` events
- `Guild.chunk()` / `Guild.fetch_members()` / `Guild.query_members()`
- Accurate `Guild.members` cache

**Do you need it?** If your bot welcomes new members, tracks nickname changes, or needs the full member list. Note: `on_message()` still delivers `Message.author` as a Member object even without this intent.

**Performance impact**: Enabling `GUILD_MEMBERS` without `GUILD_PRESENCES` forces **1-guild-per-request** chunking at startup. A bot in 840 guilds may wait ~7 minutes for `on_ready()`. Adding `GUILD_PRESENCES` alongside restores the old bulk behaviour (75 guilds/request), but is only worth it if you actually need presence data.

**Mitigation**: Set `chunk_guilds_at_startup=False` on `Client` to defer member loading.

### 2.3 MESSAGE_CONTENT (1 << 15)

Controls access to message content fields: `content`, `embeds`, `attachments`, `components`, and `poll` on `Message` objects.

**Do you need it?** Only if you read message content via:
- `Message.content` (including prefix-based command parsing)
- `Message.attachments` / `Message.embeds` / `Message.components`
- `Message.poll`

**Exceptions (content sent regardless)**:
- Messages the bot itself sends
- DMs with the bot
- Messages where the bot is `@mentioned`
- Messages where a message context menu command is invoked

**This is the most commonly over-requested intent.** If your bot uses slash commands exclusively, you likely do NOT need `MESSAGE_CONTENT`.

---

## 3. Minimal Intents Principle

**Core rule**: Enable only the intents your bot actually needs. Every unnecessary intent increases:
- Gateway bandwidth usage
- Memory consumption (cached objects)
- CPU load (event dispatching)
- Potential latency

**Common minimal configuration** (slash-command-only bot):

```python
import discord

intents = discord.Intents.default()
# Intents.default() enables: guilds, members (non-privileged parts),
# moderation, expressions, integrations, webhooks, invites,
# voice_states, messages, reactions, typing, dm_messages,
# dm_reactions, dm_typing, scheduled_events
# It does NOT enable: presences, members (privileged parts), message_content

# For a slash-command-only bot that doesn't read messages:
intents.message_content = False  # already False in default()
intents.presences = False        # already False in default()

client = discord.Client(intents=intents)
```

**Gradual audit workflow**:
1. Start with `Intents.default()`.
2. For each feature, check: "Does this require an intent I haven't enabled?"
3. Enable only the specific intent needed. Never enable all three privileged intents "just in case."
4. Periodically audit — remove intents for features removed during development.

---

## 4. discord.py 2.x Intents API

### Factory Methods

```python
discord.Intents.all()       # Everything on (development/testing only)
discord.Intents.default()   # All standard intents; no privileged intents
discord.Intents.none()      # Everything off (opt-in from zero)
```

### Per-Intent Attributes

All `Intents` attributes are read-write bools. Key attributes for Guinevere:

| Attribute | Privileged | Default in `default()` |
|---|---|---|
| `.guilds` | No | True |
| `.members` | **Yes** | False |
| `.moderation` | No | True |
| `.voice_states` | No | True |
| `.presences` | **Yes** | False |
| `.messages` | No | True |
| `.message_content` | **Yes** | False |
| `.dm_messages` | No | True |
| `.reactions` | No | True |
| `.auto_moderation_configuration` | No | True |
| `.auto_moderation_execution` | No | True |

### Client Integration

```python
# Required in 2.0+ — intents is no longer optional
client = discord.Client(intents=intents)

# Or with commands.Bot
bot = commands.Bot(command_prefix="!", intents=intents)
```

**Guinevere-specific recommendation** for P2-003:

```python
import discord

intents = discord.Intents.default()
# Enable only what Guinevere needs:
intents.members = True       # member join/leave tracking
intents.message_content = False  # Guinevere uses slash commands + modals
intents.presences = False    # no status tracking needed
intents.reactions = True     # reaction-based verification

client = discord.Client(intents=intents)
```

> ⚠️ `message_content` should only be enabled if Guinevere's agent loop parses raw message content. If all interactions go through slash commands (`discord.Interaction`), this intent is not needed.

---

## 5. Bot Token Storage Patterns

### 5.1 Environment Variables (Local Dev)

**Correct pattern — never hardcode tokens in source code.**

```python
import os
import discord

TOKEN = os.environ["DISCORD_TOKEN"]  # fail-fast: KeyError if missing
intents = discord.Intents.default()
client = discord.Client(intents=intents)
client.run(TOKEN)
```

**Local `.env` file** (development only — NEVER committed):

```bash
# .env — add to .gitignore from commit zero
DISCORD_TOKEN=NzIyMjk0MjM1ODA2NTU4NTI1.GxAMPLE.abc123def456
GUINEVERE_PREFIX="!"
```

**Loading `.env`**:

```python
from dotenv import load_dotenv
load_dotenv()  # loads .env into os.environ
```

**Critical rules**:
- `.env` must be in `.gitignore` from the **first commit**.
- Never use `.env` in **production** (plaintext on disk, no access control, no audit trail).
- Never prefix token with `Bot ` — discord.py does this automatically.

### 5.2 SOPS + age (Production / VPS)

**Production pattern for Guinevere** — Mozilla SOPS with age encryption, matching the infrastructure at `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`.

SOPS encrypts **only the values** while leaving keys readable. This means the file is safe to commit to Git, and diffs are meaningful.

**Workflow**:

```bash
# 1. Install SOPS + age on workstation
# 2. Create encrypted secrets file
sops create secrets/discord-secrets.yaml

# Contents (encrypted at rest):
# discord_bot_token: NzIyMjk0MjM1ODA2NTU4NTI1.GxAMPLE.abc123
# ...

# 3. In .sops.yaml (repo root), configure key routing:
# creation_rules:
#   - path_regex: secrets/.*\.yaml$
#     age: age1abc123...

# 4. Decrypt on VPS at deploy time:
export SOPS_AGE_KEY_FILE=/home/guinevere/.config/sops/age/keys.txt
sops -d secrets/discord-secrets.yaml
```

**Guinevere-specific pattern** (from context):

```bash
# Decrypt only on VPS using SOPS_AGE_KEY_FILE
export SOPS_AGE_KEY_FILE=/home/guinevere/.config/sops/age/key.txt
DISCORD_TOKEN=$(sops -d /home/guinevere/code/guinevere/secrets/discord-secrets.yaml \
  --extract '["discord_bot_token"]')
```

**Why SOPS + age for Guinevere**:

| Requirement | SOPS + age meets it? |
|---|---|
| Encrypted at rest in Git | ✅ — only values encrypted |
| Diff-friendly in PRs | ✅ — YAML structure preserved |
| Decrypts only on VPS with key | ✅ — key never in repo |
| Audit trail via Git | ✅ — all changes tracked |
| Rotatable | ✅ — re-encrypt with new key |
| No cloud dependency | ✅ — age keys are files |

**What NOT to do**:
- ❌ Never commit the **decrypted** file to Git.
- ❌ Never set `SOPS_AGE_KEY` as an env var in CI (use `SOPS_AGE_KEY_FILE` pointing to a GH secret store instead).
- ❌ Never log the decrypted token value.

### 5.3 Fail-Fast Validation

Always validate token presence **before** calling `client.run()`:

```python
import os
import sys

def get_discord_token() -> str:
    """Get Discord bot token with fail-fast validation."""
    token = os.environ.get("DISCORD_TOKEN")
    if not token:
        print("FATAL: DISCORD_TOKEN environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not isinstance(token, str) or len(token) < 50:
        print("FATAL: DISCORD_TOKEN appears invalid (too short).", file=sys.stderr)
        sys.exit(1)
    return token.strip()
```

discord.py 2.x also validates tokens internally: it calls `.strip()` and raises `TypeError` if the token is not a `str`.

---

## 6. Logging Redaction

### 6.1 discord.py Default Logging

Since discord.py 2.0, `Client.run()` provides a **default logging configuration** (coloured output to stderr at INFO level). This can be customised or disabled:

```python
# Disable default logging (use your own config)
client.run(TOKEN, log_handler=None)
```

**Important**: The default logging configuration **does not automatically redact tokens**. If a debug log includes the token, it will appear in plaintext.

### 6.2 Token Redaction Strategy

**Layer 1: Prevent tokens from entering logs (application layer)**

Ensure the token variable is **never** logged directly:

```python
# ❌ BAD — logs the token
logger.debug(f"Starting bot with token: {TOKEN}")

# ✅ GOOD — log only existence check
logger.info("Bot token loaded successfully (redacted)")
logger.debug(f"Bot token length: {len(TOKEN)} characters")
```

**Layer 2: Redaction via logging.Filter (stdlib approach)**

Use Python's built-in `logging.Filter` to redact known sensitive keys:

```python
import logging
import re

class SensitiveDataFilter(logging.Filter):
    """Redact sensitive patterns from log messages."""

    SENSITIVE_PATTERNS = [
        (r'(DISCORD_TOKEN|BOT_TOKEN|TOKEN)\s*[=:]\s*\S+', r'\1=***REDACTED***'),
        (r'(token["\']?\s*:\s*["\'])[^"\']+(["\'])', r'\1***REDACTED***\2'),
        (r'Bearer\s+\S+', 'Bearer ***REDACTED***'),
        (r'[MN][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}', '***JWT-REDACTED***'),
    ]

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg)
        return True

# Wire into logging
root_logger = logging.getLogger()
root_logger.addFilter(SensitiveDataFilter())
```

**Layer 3: Key-based redaction in structured logs (defence-in-depth)**

For structured logging (JSON), redact by key name:

```python
SAFE_LOG_KEYS = {"password", "token", "secret", "authorization", "api_key",
                 "access_token", "refresh_token", "discord_bot_token"}
```

**Verification**: Grep your logs for known token patterns before production:

```bash
grep -rnE '[MN][A-Za-z0-9_-]{23,25}\.[A-Za-z0-9_-]{6,7}\.[A-Za-z0-9_-]{27,}' logs/
```

---

## 7. Verification Methods

### 7.1 Intents Verification

**At startup** — log the enabled intents (without logging their values):

```python
@client.event
async def on_ready():
    enabled = [attr for attr in dir(client.intents)
               if not attr.startswith('_') and getattr(client.intents, attr)]
    logger.info(f"Connected as {client.user} (ID: {client.user.id})")
    logger.info(f"Enabled intents: {enabled}")
    logger.info(f"Guild count: {len(client.guilds)}")
```

**Expected output**:
```
INFO     discord.client: Connected as Guinevere#1234 (ID: 123456789)
INFO     discord.client: Enabled intents: ['guilds', 'members', 'messages', 'reactions', ...]
INFO     discord.client: Guild count: 3
```

### 7.2 Token Verification

**Pre-runtime checks** (CI/CLI script):

```bash
#!/bin/bash
# verify-token.sh — runs before bot startup
# Tests: token exists, is decryptable, has correct format

if [ -z "$DISCORD_TOKEN" ]; then
  echo "FATAL: DISCORD_TOKEN not set"
  exit 1
fi

# Basic format check: Discord tokens are ~70+ chars base64-like
TOKEN_LEN=${#DISCORD_TOKEN}
if [ "$TOKEN_LEN" -lt 50 ]; then
  echo "FATAL: DISCORD_TOKEN too short ($TOKEN_LEN chars)"
  exit 1
fi

echo "Token verification passed (length: $TOKEN_LEN chars)"
```

**SOPS decryption verification**:

```bash
#!/bin/bash
# verify-sops.sh
SOPS_AGE_KEY_FILE=/home/guinevere/.config/sops/age/key.txt \
  sops -d /home/guinevere/code/guinevere/secrets/discord-secrets.yaml \
  --extract '["discord_bot_token"]' \
  > /dev/null \
  && echo "SOPS decryption: OK" \
  || echo "SOPS decryption: FAILED"
```

### 7.3 Discord Gateway Connection Verification

| Symptom | Likely Cause | Fix |
|---|---|---|
| `4013` close code | Invalid intent bitwise value | Check `Intents` configuration |
| `4014` close code | Disallowed privileged intent | Enable in Developer Portal, or remove intent from code |
| `4004` close code | Invalid token | Regenerate token in Developer Portal, verify env var |
| `on_ready` takes >5 min | Member chunking with `GUILD_MEMBERS` but without `GUILD_PRESENCES` | Add `GUILD_PRESENCES` or set `chunk_guilds_at_startup=False` |

---

## 8. P2-002 / P2-003 Acceptance Checks

### P2-002: Bot Token Handling

| # | Check | Pass Criteria |
|---|---|---|
| 1 | Token source | Token is **never** hardcoded in Python files. Sourced from `os.environ` (dev) or SOPS-decrypted env var (production). |
| 2 | Fail-fast | Startup crashes immediately with clear error if `DISCORD_TOKEN` is missing or empty. |
| 3 | No committed secrets | `.env` is in `.gitignore`. No encrypted or decrypted token files committed. |
| 4 | SOPS encryption (prod) | Production token encrypted with SOPS + age. Only decryptable with `SOPS_AGE_KEY_FILE` on VPS. |
| 5 | Log redaction | No token value appears in any log output. Verified via grep of logs. |
| 6 | No `Bot ` prefix | Token passed as-is to `client.run(token)` — discord.py handles the `Bot ` prefix internally. |
| 7 | Rotatability | Token can be rotated by updating the SOPS file and re-deploying. |

### P2-003: Gateway Intents Configuration

| # | Check | Pass Criteria |
|---|---|---|
| 1 | Explicit intents | `intents=` is explicitly passed to `Client`. discord.py 2.x requires this. |
| 2 | Minimal intents | Only intents needed for current features are enabled. No "just in case" privileged intents. |
| 3 | Privileged intent justification | Each enabled privileged intent has a documented reason in code comments or ADR. |
| 4 | `MESSAGE_CONTENT` audit | Verified that enabled message content is actually required (not for slash-only bots). |
| 5 | Developer Portal match | Privileged intents enabled in code **match** those toggled in Discord Developer Portal. |
| 6 | Startup verification | Startup log lists all enabled intents for visibility. |
| 7 | No `4014` errors | Gateway connection does not receive close code 4014. |

---

## 9. Common Pitfalls

### Pitfall 1: "I enabled it in the portal, why doesn't it work?"

The Discord Developer Portal toggle is **necessary but not sufficient**. You must also enable the intent in your Python code:

```python
intents = discord.Intents.default()
intents.members = True       # 👈 Code-level enable required
```

### Pitfall 2: Token is `None` but error is confusing

`os.getenv("WRONG_VAR")` returns `None`. discord.py 2.0+ will raise `TypeError: expected token to be a str`. Always use `os.environ["DISCORD_TOKEN"]` (raises `KeyError` immediately) or add explicit validation.

### Pitfall 3: Committing `.env` to Git

Even for a private repo — **never**. If it happens, **immediately**:
1. Rotate the token in Developer Portal.
2. Add `.env` to `.gitignore` and force-push to remove from history (or use `git filter-branch`).
3. Treat all credentials in that `.env` as compromised.

### Pitfall 4: `MESSAGE_CONTENT` enabled unnecessarily

If your bot uses only slash commands (`/command`), `Message.content` is **not needed**. The `MESSAGE_CONTENT` intent only controls access to message content fields in events and REST endpoints. Interaction data is sent via a separate mechanism.

### Pitfall 5: Logging token in debug output

```python
# BAD — will appear in Discord.py's DEBUG logs
http = aiohttp.ClientSession()
resp = await http.post(
    "https://discord.com/api/v10/gateway/bot",
    headers={"Authorization": f"Bot {TOKEN}"}  # aiohttp logs headers in DEBUG
)
```

discord.py at `logging.DEBUG` may log HTTP request headers. **Never run DEBUG logging in production** unless you have verified redaction.

### Pitfall 6: SOPS key file location mismatch

If `SOPS_AGE_KEY_FILE` points to the wrong path, SOPS will fail silently or prompt for a password. Always verify:

```bash
ls -la $SOPS_AGE_KEY_FILE  # Must exist and be readable
sops -d secrets/test.yaml --extract '["test"]'  # Test decryption
```

---

## 10. Sources

| Source | URL |
|---|---|
| Discord Gateway Docs | https://docs.discord.com/developers/events/gateway |
| Discord Gateway Events | https://docs.discord.com/developers/events/gateway-events |
| Discord Privileged Intents | https://docs.discord.com/developers/events/gateway#privileged-intents |
| Discord Close Codes | https://docs.discord.com/developers/topics/opcodes-and-status-codes |
| discord.py Intents Primer | https://discordpy.readthedocs.io/en/stable/intents.html |
| discord.py API Reference (Client) | https://discordpy.readthedocs.io/en/stable/api.html#discord.Client |
| discord.py API Reference (Intents) | https://discordpy.readthedocs.io/en/stable/api.html#intents |
| discord.py Logging Guide | https://discordpy.readthedocs.io/en/stable/logging.html |
| discord.py Migrating to 2.0 | https://discordpy.readthedocs.io/en/stable/migrating.html |
| SOPS (Mozilla) | https://getsops.io/docs/ |
| SOPS + age on VPS Guide | https://www.hostmycode.com/blog/linux-vps-secrets-management-sops-age-2026 |
| Env Var Best Practices | https://env.dev/guides/env-vars-best-practices |
| Python Logging Redaction | https://trailonix.com/blog/posts/pii-redaction-logs/ |
| payload-redactor lib | https://github.com/larsderidder/payload-redactor |
| GitHub SOPS Action | https://github.com/marketplace/actions/get-secrets-from-encrypted-sops |

---

*End of report. All patterns are adapted for Guinevere's VPS-based deployment with SOPS+age encryption at `/home/guinevere/code/guinevere/secrets/discord-secrets.yaml`.*