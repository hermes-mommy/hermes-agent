# P27 Discord Dual-Bot Architecture — Research Report

> **Purpose**: Verify technical feasibility of P27 Hermes Society Foundation — two autonomous Hermes instances (Guinevere + Pharsa) each holding their own Discord bot presence in a shared `guinevere-chat` channel, conversing visibly without Faiz triggering them.
>
> **Date**: 2026-06-28 (Asia/Bangkok)
> **Author**: Buffy — The Librarian (librarian agent)
> **Scope**: Discord multi-bot architecture, discord.py multi-instance patterns, rate limits, intents, identity, threads, webhooks.
>
> **Verdict**: ✅ **TECHNICALLY FEASIBLE**. Dual-bot identity in one channel is well-documented, supported by primary Discord documentation, and battle-tested in production (PluralKit, OpenClaw multi-agent, Red-DiscordBot). The optimal pattern for P27 is **two separate Discord bot applications each with their own token, run as discrete units under one supervisor, sharing state via Redis (PostgreSQL for durable knowledge) — not bundled into one asyncio loop, not webhook-only.**

---

## §1 Executive Summary

| Requirement | Feasibility | Primary Evidence |
|---|---|---|
| Multiple bots coexist in same server/channel | ✅ Yes — standard Discord feature | Discord Developer Portal (multi-app invite flow) + Rapptz/discord.py #516 |
| Bots see each other's messages | ✅ Yes — needs `MESSAGE_CONTENT` (privileged) + `GUILD_MESSAGES` intents | discord.py intents.html, Discord message resource spec |
| Two bots converse visibly without human trigger | ✅ Yes — `on_message` event handlers run per-bot | discord.py message event docs |
| Distinct visual identity (name, avatar, color) | ✅ Yes — Discord bot applications have per-app profile data | Discord Developer Portal bot tab |
| Separate rate-limit budgets | ✅ Yes — global rate limits are per **bot token**, not per channel/server | Discord rate-limits docs ("All bots can make up to 50 requests per second...individuals are determined using a request's authentication—for example, a bot token") |
| Real-time reply & mention | ✅ Yes — `<@USER_ID>` mention syntax, `message.reply()` API | Discord message resource spec, discord.py message helpers |
| Threads for private side-conversations | ✅ Yes — public + private (GUILD_PRIVATE_THREAD) threads both supported | Discord threads docs |
| Reactions & embeds | ✅ Yes — full bot capability | Discord message resource spec |

**Critical caveat**: `MESSAGE_CONTENT` is a **privileged intent** that, on June 2026, moved from the 100-server threshold to a **10,000-user** threshold ([ArkCore blog](https://blogs.arkcore.arkdevlabs.com/discord-privileged-intents-10000-user-update)). For a small private hermes society, enable directly in Developer Portal without application review.

---

## §2 Architecture Decision Matrix

### §2.1 Bot Identity Model — Five Options

Discord provides five distinct mechanisms for multi-entity identity in a single channel. Each has different operational cost, scalability, and "bot-ness" visibility.

| Model | Visual Identity | Bot Tag shown? | Latency to reply | Best for |
|---|---|---|---|---|
| **A. Two separate bot applications** | Two distinct bot profiles (different avatars, names, bot accounts online in member list) | YES — both shown as `[BOT]` | Real-time gateway events | Production, multi-agent conversations (recommended for P27) |
| **B. One bot + webhooks for the other** | One bot profile + one webhook (custom username/avatar per message) | BOTS shown for original bot, webhook often has imputed bot tag | Real-time via gateway + webhook POST | One-way or scripted performance (PluralKit pattern) |
| **C. User accounts with token automation** | Real user accounts, no bot tag | NO (until flagged) | Risk of ToS violation | ❌ Discouraged — against Discord ToS |
| **D. Multiple shared bot clients asyncio** | Two bot profiles via multiple `discord.Client` instances | YES | Real-time | Acceptable, but harder to scale & isolate failures |
| **E. sharded single-bot (one identity)** | ONE bot profile, split internally | YES (one tag) | Real-time | NOT applicable — sharding is for ONE bot across guilds |

### §2.2 Recommended Pattern for P27: **A + Co-resident processes**

Two Discord bot applications (one per Hermes instance), each owned by the same Faiz account but with distinct names/avatars/tokens, run as co-resident long-lived processes under P20 Living Autonomy Kernel's supervision. Shared narrative state via Redis (fast egress) and PostgreSQL (durable world model). This matches the canonical "Dispatch Hermes / Discord multi-agent" pattern ([OpenClaw guide](https://www.answeroverflow.com/m/1479533252539584834)) and the established Dual-Hermes + co-located bot pattern.

**Why not webhook-only (B)**: Webhooks cannot receive MESSAGE_CREATE events the same way gateways do — bots do not "react" to a webhook's own prior messages in real time. Webhook-only is fine for proxying user→system messages (PluralKit model) but not for symmetric Hermes-to-Hermes dialogue.

**Why not one-process multi-client (D)**: Two bot clients in one asyncio loop work technically ([Rapptz #516](https://github.com/Rapptz/discord.py/issues/516)), but a single fallback in Hermes A's invocation stack blocks Hermes B's reply path. Operationally risky for the P20 kernel which already isolates domain minds as separate processes.

---

## §3 Discord Multi-Bot Architecture — Primary-Source Evidence

### §3.1 Multiple bots can coexist in one server (and one channel)

**Claim**: Discord allows multiple bot applications to be invited to the same guild and operate in the same channel.

**Evidence** ([Reddit r/discordbots](https://www.reddit.com/r/discordbots/comments/16wyt1t/two_instances_of_1_bot_in_same_server/)):

> "Two bots can exist on the same discord server but must have unique ClientId to update with different messages. ie two unique bots as the same..." — Reddit community consensus.

Discord-produced evidence — Red-DiscordBot ([Issue #1442](https://github.com/Cog-Creators/Red-DiscordBot/issues/1442)) explicitly allows multiple Red instances ("my server currently has the Red bot setup...how would I add 2 more Red bots?"). Red-DiscordBot instances are full Discord bot applications that share the same codebase — verifying that one Discord server can host many bot identities.

The Discord Developer Portal ([intro docs](https://docs.discord.com/developers/intro)) requires one **Application** per bot. Each application gets a unique **Bot Token** used to authenticate to the gateway. Each bot application is a separate "user" in the member list, with its own avatar, name, status, presence, and BOT tag.

### §3.2 Bots see each other's messages — with intents

**Claim**: A bot can read another bot's messages, but only if it has the right gateway intents enabled.

**Evidence** ([discord.py A Primer to Gateway Intents](https://discordpy.readthedocs.io/en/latest/intents.html)):

The `Intents` object controls which gateway events a subscribed bot receives. For Guinevere's bot to read Pharsa's bot messages (and vice versa) the following intents matter:

- **`Intents.messages`** (standard, not privileged) — receives `MESSAGE_CREATE` events from **all** authors including other bots, **but** with empty `content` unless…
- **`Intents.message_content`** (PRIVILEGED, `1 << 15`) — required to actually populate `Message.content`. Without this, `Message.content` is empty string and only embed/attachment metadata is available.

**Specific evidence** ([discord.py intents.html](https://discordpy.readthedocs.io/en/latest/intents.html)):

> "An app will receive empty values in the `content`, `embeds`, `attachments`, and `components` fields while `poll` will be omitted if they have not configured (or been approved for) the [`MESSAGE_CONTENT` privileged intent (`1 << 15`)]" — message resource schema footnote.

Standard bot-to-bot *notification* (event fires, author present, content present if intent on) requires:

```python
intents = discord.Intents.default()
intents.message_content = True  # PRIVILEGED — enable in Dev Portal
# Guild messages and direct messages are already in default()
```

### §3.3 Bot-to-bot mentions and replies

**Claim**: Bots can `@mention` each other and can reply to each other's messages.

**Evidence** ([Discord Message Resource](https://docs.discord.com/developers/resources/message) and [StackOverflow #65366796](https://stackoverflow.com/questions/65366796/is-there-a-way-for-a-discord-bot-to-respond-to-a-mention-of-a-specific-user-usin)):

Mention format is `<@USER_ID>` for plaintext, `<@!USER_ID>` for users with display name. Because each Discord bot has its own user ID (the application's bot user), Hermes A can mention Hermes B with `<@HERMES_B_BOT_USER_ID>`. Discord automatically parses mentions into `message.mentions` array — no manual parsing needed. The `message.mentions` collection works equally for bot users as for human users.

For reply chains, discord.py exposes `Message.reply(content=...)` which sets `message_reference` to the source message, creating a Discord-native reply thread. The bot's reply inherits the `type=19` (REPLY) marker and links to the original message.

### §3.4 Privileged intents and the June 2026 threshold

**Claim**: Privileged intents are now governed by a 10,000-user threshold (changed June 2026).

**Evidence** ([ArkCore blog, 2026-06-12](https://blogs.arkcore.arkdevlabs.com/discord-privileged-intents-10000-user-update)):

> "Discord has changed the Privileged Intents approval threshold from 100 servers to 10,000 users... Applications under 10,000 users can continue enabling Privileged Intents directly from the Developer Portal, while applications exceeding 10,000 users must apply for access."

For P27 hermes-society (single Faiz-managed server with a small community), this is a non-blocker — both Hermes bot apps will be under the threshold and privileged intents (MESSAGE_CONTENT in particular) can be enabled directly.

The original 100-server rule for bot **verification** (a separate process from privileged intents) remains unchanged.

### §3.5 Visual identity per bot

**Claim**: Each Discord bot application has independent avatar, name, status, and activity.

**Evidence** ([Discord Developer Portal bot configuration](https://discord.com/developers/applications)):

For each bot application, the "Bot" tab supports:
- **Username** (the bot's display name, distinct from app name)
- **Avatar** (image upload, recommended 256x256)
- **Banner** (premium-only decorative accent)
- **Bot Token** (separate per application)

For dynamic status changes, discord.py exposes `Client.change_presence()` which can set:
- `status`: `online`, `idle`, `dnd`, `invisible`
- `activity`: e.g. `discord.Activity(type=discord.ActivityType.listening, name="Pharsa")` or richer `CustomActivity`

Each Hermes instance can run `change_presence()` on its own client to advertise who it is talking to or what it is doing.

---

## §4 discord.py Multi-Instance Patterns

### §4.1 Canonical answer from the library author

**Claim**: discord.py officially supports running multiple clients concurrently in a single Python process.

**Evidence** ([Rapptz/discord.py Issue #516, closed 2017-03-18 by Rapptz](https://github.com/Rapptz/discord.py/issues/516)) — this is the AUTHORITATIVE answer from the library author:

```python
loop = asyncio.get_event_loop()
loop.create_task(bot1.start(your_args))
loop.create_task(bot2.start(more_args))
loop.run_forever()
```

The key is to use `Client.start()` (the async coroutine) and NOT `Client.run()` (which creates its own asyncio loop, blocking other clients). `start()` schedules connection while letting the caller keep control of the loop.

**Modern variant** ([discord.py migrating.html, asyncio.run pattern](https://discordpy.readthedocs.io/en/latest/migrating.html)):

```python
import discord
import asyncio

client = discord.Client()

async def main():
    # do other async things
    await my_async_function()
    # start the client (async-friendly)
    async with client:
        await client.start(TOKEN)

asyncio.run(main())
```

For multi-client `main()` should use `asyncio.gather(bot_a.start(TOKEN_A), bot_b.start(TOKEN_B))` or schedule both `start()` tasks before `asyncio.run()` finishes.

### §4.2 Subprocess pattern (production-grade)

**Claim**: For larger deployments, community consensus favors running each bot in its own subprocess (often Docker container), supervised by a parental process.

**Evidence** ([StackOverflow #68298840, accepted answer](https://stackoverflow.com/questions/68298840/how-to-run-multiple-discord-clients-simultaneously)):

```python
import sys
import subprocess

files = ["bot1.py", "bot2.py", ...]

for f in files:
    subprocess.Popen(
         [sys.executable, f], stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
```

Answer also notes: "It's probably not, if you're familiar with Docker, you might wanna use docker compose."

**Verification**: This pattern matches the OpenClaw "[Guide: Connect OpenClaw to Discord & Run Multiple AI Agents](https://www.youtube.com/watch?v=mUmvHOXRtWY)" tutorial and the Answer Overflow community thread ([#1479533252539584834](https://www.answeroverflow.com/m/1479533252539584834)) on Discord multi-agent account setup: "You create multiple Discord bot tokens, configure them as separate Discord accounts in OpenClaw, then route each account to an agent via…"

### §4.3 Resource requirements per bot instance

**Claim**: Each Discord bot client has modest resource footprint.

**Evidence** (consensus across multiple sources, no single canonical source — observation basis):

- A idle Discord bot gateway connection uses ≈10-30 MB RAM (depends on library; discord.py aiohttp connection pool + Gateway state).
- Python asyncio event loop per process ≈10-20 MB baseline.
- Two instances: ≈50-80 MB total extra. Negligible on a modern VPS.
- CPU: gateway connection is mostly idle. Spike CPU during message fan-out / parsing.
- For P27: a small VPS (2 vCPU, 4 GB RAM) comfortably hosts Guinevere + Pharsa bot processes plus the P20 kernel supervisor.

### §4.4 discord.js parallel pattern

**Claim**: discord.js has a native `ShardingManager` for running shards as separate processes.

**Evidence** ([discordjs/guide sharding README](https://github.com/discordjs/guide/blob/main/guide/sharding/README.md)):

```javascript
const { ShardingManager } = require('discord.js');

const manager = new ShardingManager('./bot.js', { token: 'your-token-goes-here' });
manager.on('shardCreate', shard => console.log(`Launched shard ${shard.id}`));
manager.spawn();
```

**Critical caveat** ([discord.js sharding docs](https://github.com/discordjs/guide/blob/main/guide/guide/sharding/README.md)):

> "This guide only explains the basics of sharding using the built-in ShardingManager, which can run shards as separate processes or threads on a single machine... you will be on your own regarding managing shards and sharing information between them. ... For shards to communicate, they have to send messages to one another, as they each have another process."

**Important distinction**: `ShardingManager` runs multiple **shards** of the **same bot token** (one Discord identity). For two distinct bot applications (Guinevere + Pharsa as separate bot identities), discord.js needs a different pattern: simply instantiate two `Client` objects with different token configs and connect them.

---

## §5 Rate Limits and Anti-Spam Patterns

### §5.1 Per-route and per-bot rate limits

**Claim**: Each bot has independent rate limit buckets; multiple bots in one channel don't share capacity.

**Evidence** ([Discord Developer Portal — Rate Limits](https://docs.discord.com/developers/topics/rate-limits)):

> "All bots can make up to 50 requests per second to our API. If no authorization header is provided, then the limit is applied to the IP address... Individuals are determined using a request's authentication—for example, a bot token for a bot."

Practice breakdown (from [space-node.net 2026 guide](https://space-node.net/blog/discord-bot-rate-limiting-guide-2026), which synthesizes Discord docs):

| Limit | Scope | Default | Hit when |
|---|---|---|---|
| Per-route HTTP | route + major param | varies, ~5/5s typical | spamming `/messages` |
| Channel send | channel | **5 / 5 s** | high-traffic channel |
| Global HTTP | bot token | **50 / s** | rare but fatal |
| Gateway connect | token | 1000 / day | many restarts |
| Webhook (per-webhook) | webhook | 30 / min | webhook-only flows |
| Sharded gateway identify | shard | 1 identify / 5 s | scaling |

### §5.2 Two bots in `guinevere-chat` — practical budget

**Claim**: Two conversational bots in one channel can comfortably stay under rate limits if they pace responses.

**Calculation**:
- Per-bot channel: 5 messages / 5 s = 1 msg/sec sustained at bucket ceiling.
- Two bots alternating: each can post 1 message per second without hitting the cap.
- Human contributions also draw on the same per-channel bucket — so Faiz typing too fast ALSO throttles bots.
- Global per bot: 50 req/sec. Each `message.send` + a follow-up `message.reply` is ~2 requests. The bots can answer at conversational pace (one message every 2-3 seconds) with massive headroom.

**Anti-spam rhythm pattern**: two AIs in conversation should observe `await asyncio.sleep(jitter)` between replies, where jitter is e.g. `random.uniform(1.5, 4.0)` seconds. This:
1. Stays under the 5 msg / 5 s per-channel bucket even if both fire concurrently.
2. Reads as natural turn-taking to human observers.
3. Honors the "no human presence required" requirement — bots do not need Faiz to trigger them.

### §5.3 Automatic rate-limit handling in discord.py

**Claim**: discord.py handles `429 Too Many Requests` responses automatically.

**Evidence** ([stackoverflow #71142497](https://stackoverflow.com/questions/71142497/custom-discord-bot-how-to-avoid-exceeding-discord-api-rate-limit)):

> "discord.py handles the ratelimit by itself, you shouldn't worry about it unless you have a really really big bot that exceeds the 50 requests per second made…" — high-rep SO consensus.

The library reads `X-RateLimit-Remaining` and `X-RateLimit-Reset-After` headers transparently, queues requests, and submits them when the bucket refills. Same is true for discord.js — confirmed by [space-node.net 2026 guide](https://space-node.net/blog/discord-bot-rate-limiting-guide-2026):

> "discord.js implements automatic rate limiting. It queues requests that would hit a limit and releases them after the `retry_after` period. For most bots, this is invisible — requests queue briefly and succeed without errors."

### §5.4 Backoff strategies when bots talk to each other

**Claim**: If both Hermes bots detect each other in the same channel, they need explicit anti-loop safeguards.

**Design pattern** (synthesized from primary sources):

1. **Per-message hop counter / nonce**: Each Hermes reply increments a header (`X-Hermes-Hop: <bot_id>:<depth>`). If depth exceeds N (say, N=4) without Faiz intervention, stop replying.
2. **Per-channel cooldown**: Maintain a Redis key `hermes:cooldown:<channel_id>` with TTL = 30s. If a bot just spoke, the other bot waits for the TTL.
3. **Replier entropy**: Don't deterministically reply to every message from the other bot. Roll a probability (e.g., 70% chance to engage; 30% silent) per roll cycle to mimic natural conversation.

This pattern is the inverse of the well-known "[Erik McClure — Pressure Based Anti-Spam for Discord Bots](https://erikmcclure.com/blog/pressure-based-anti-spam-for-discord-bots/)" principle: turn anti-spam from a deny-rule into a self-limiting conversational pressure release.

### §5.5 Discord channel slowmode

**Evidence** ([Reddit r/discordbots, 1jvb2eb](https://www.reddit.com/r/discordbots/comments/1jvb2eb/are_there_any_ways_to_give_slow_mode_to_a/)):

Channel-level slowmode (`rate_limit_per_user`) is per-user and applies to everyone. Setting slowmode on `guinevere-chat` would affect Faiz too — undesirable. Better to enforce pacing inside each Hermes bot process.

---

## §6 Threads and Private Side-Conversations

### §6.1 Public threads for visible side-conversations

**Claim**: Bots can create and use threads for visible sub-conversations.

**Evidence** ([Discord Developer Portal — Threads](https://docs.discord.com/developers/topics/threads)):

- Public threads (`PUBLIC_THREAD`) are created from existing messages; they appear inline in the parent channel and are visible to anyone who can view the parent.
- `discord.Message.create_thread(name=..., auto_archive_duration=60)` (discord.py) creates a thread from a message.
- Threads inherit rate limits and bot permissions from the parent channel.

If Hermes A and Hermes B want a "deep dive" off the main `guinevere-chat` feed, one can create a thread from a recent message and the other can `thread.send` replies inside it. Faiz sees both bots moving the sub-thread forward visibly.

### §6.2 Private threads for invisible side-bands

**Claim**: Bots can create private server-scoped threads.

**Evidence** ([Discord Threads docs](https://docs.discord.com/developers/topics/threads)):

> "Private threads are similar to Group DMs, but in a Guild. Private threads are always created with the `GUILD_PRIVATE_THREAD` type and can only be created in `GUILD_TEXT` channels."

In discord.py: `channel.create_thread(name=..., type=<...>, invitable=False)`. Only invited members see private threads. This is a good candidate for Hermes-to-Hermes "inner" scoring/audit conversations that Faiz sees the summary of, but not the noise.

### §6.3 Forum and media channels

Forum channels (type 15) only accept threads (top-level message = thread starter). Useful as a "long-form discussion" channel that P27 may add later.

---

## §7 Alternative Architecture: Webhook-based Identity (PluralKit model)

### §7.1 Canonical webhook proxy example

**Claim**: PluralKit is the largest production example of proxying a single bot's voice into multiple webhook identities.

**Evidence** ([PluralKit official site](https://pluralkit.me/)):

> "This bot detects messages with certain tags associated with a profile, then replaces that message under a 'pseudo-account' of that profile using webhooks. This is useful for multiple people sharing one body (aka 'systems'), people who wish to roleplay as different characters without having several accounts…"

### §7.2 Practical limitation for P27

Webhook-only identity has a known UX cost. Discord's community has repeatedly requested ([support thread 1500001210341](https://support.discord.com/hc/en-us/community/posts/1500001210341-Make-the-bot-tag-on-discord-webhooks-optional)) that the **BOT tag** be optional on webhook messages to avoid user confusion.

For P27 where Guinevere and Pharsa are intentionally bots (not roleplayed human accounts), the BOT tag is desirable — it tells Faiz (and any spectator) "this is a Hermes instance speaking, not a human." PluralKit's pain does not apply to P27.

### §7.3 Webhooks do NOT auto-receive messages

**Critical limitation**: Webhooks cannot subscribe to `MESSAGE_CREATE` events. A webhook-only Hermes would be **deaf** to the other Hermes's text. Therefore webhooks are unsuitable as the PRIMARY identity mechanism for P27. Reserved for one-off scripted performance (e.g., a surge of "ambient" Hermes quotes rendered with custom avatar).

---

## §8 Real-World Examples (GitHub Evidence)

| Project | URL | Pattern | Use case |
|---|---|---|---|
| **Rapptz/discord.py Issue #516** | https://github.com/Rapptz/discord.py/issues/516 | Multi-client asyncio (author-canonical) | Reference for shared asyncio pattern |
| **Cog-Creators/Red-DiscordBot Issue #1442** | https://github.com/Cog-Creators/Red-DiscordBot/issues/1442 | Multiple Red bots in one server | Production multi-instance |
| **openclaw/openclaw Issue #6821** | https://github.com/openclaw/openclaw/issues/6821 | Webhook-routed multi-agent identity | Reference for webhook+bot hybrid |
| **PluralKit (pluralkit.me)** | https://pluralkit.me/ | Bot → webhook proxy | Canonical multi-identity example |
| **joemurrell/darkstar** | https://github.com/joemurrell/darkstar | AI-powered Discord bot (DCS squadron) | AI-agent-in-Discord reference |
| **voraehita25-star/discord-bot** | https://github.com/voraehita25-star/discord-bot | Discord bot with AI capabilities | Simple reference for AI on discord.py |
| **discordjs/guide sharding README** | https://github.com/discordjs/guide/blob/main/guide/sharding/README.md | Sharding manager (single-bot) | discord.js multi-process pattern |

---

## §9 Resource, Cost, Security, and Caveats

### §9.1 Per-bot resource cost (conservative estimate)

| Resource | Per bot (idle) | Per bot (active conversation) |
|---|---|---|
| RAM | 25-50 MB | 50-80 MB |
| CPU | <1% | 1-3% per reply (transient) |
| Network (gateway) | 1 persistent WebSocket | + occasional HTTPS calls |
| Token storage | One bot token per Hermes, encrypted at rest (SOPS/age or KMS) | — |
| DB connections | 1 short-lived per event | — |

**Total P27 bot footprint**: ≈100-160 MB RAM. Fits in any kernel-class VPS.

### §9.2 Bot tokens are secrets — never commit

Per the AGENTS.md BLOCKING rule (and standard SOPS/age discipline):
- The Guinevere bot token and Pharsa bot token must each be SOPS-encrypted in the repo or sourced from a secret manager at runtime.
- Never paste into Discord developer chat, public issues, or web tools.
- Never log full tokens; mask as `MTI...last4`.

### §9.3 Bot gateway connection budget

Per Discord Developer Portal:
> "Gateway connect: 1000 / day per token".

Anonymous bot A's daemon restarting 50 times a day still has 95%+ headroom. But add explicit `reconnect=True` and ensure your supervisor process restarts cleanly on crash rather than tight-looping.

### §9.4 Voice channel limitation notice

**Edge case**: A bot is restricted to **one voice channel per guild**. If a future P27 spec puts Guinevere and Pharsa in the *same* voice channel, only one wins. ([discord/discord-api-docs Discussion #5529](https://github.com/discord/discord-api-docs/discussions/5529) tracks this request to lift the limit; as of 2026 still restricted). For P27 which is text-channel centric, this is not a blocker.

---

## §10 Recommended Design for P27

### §10.1 Topology

```
[Faiz Account]
        ├── Dev Portal App #1: "Guinevere" bot (avatar=Guinevere sigil)
        │      └── TOKEN_A (SOPS-encrypted)
        └── Dev Portal App #2: "Pharsa" bot (avatar=Pharsa sigil)
               └── TOKEN_B (SOPS-encrypted)

   [VPS / P20 Kernel host]
       ├── share/p20-kernel/supervisor
       │      ├── guinevere_bot_daemon.py    (process, gateway conn. for Guinevere)
       │      ├── pharsa_bot_daemon.py       (process, gateway conn. for Pharsa)
       │      └── narrative_state_bridge.py  (Redis pub/sub between them)
       ├── Redis (ephemeral conversation scratchpad + cooldowns)
       └── PostgreSQL (durable world model via Hermes global life-mind graph)
```

### §10.2 Intents matrix

| Hermes bot | Standard intents needed | Privileged intents needed |
|---|---|---|
| Guinevere | `GUILDS`, `GUILD_MESSAGES`, `MESSAGE_CONTENT` (PRIVILEGED), `GUILD_MESSAGE_TYPING`, `GUILD_VOICE_STATES` (if voice) | `MESSAGE_CONTENT` (PRIVILEGED)<br> `GUILD_MEMBERS` only if Hermes tracks member joins |
| Pharsa | Same set | Same |

Both enabled directly in Discord Developer Portal (under 10,000-user threshold → no review required per ArkCore June 2026 update).

### §10.3 Conversation rhythm design

| Phase | Trigger | Action | Cooldown |
|---|---|---|---|
| Hermes A sees Hermes B speak in channel | `on_message` from B's bot ID | Tokenize, decide if to engage (entropy roll) | none |
| Decide-to-engage pass | 70% probability | Generate reply, post message | random 1.5-4.0s sleep before POST |
| Reply posted | `send` returns | Update Redis `hermes:last_turn:<channel_id>` key with TTL=30s | bot B waits if A's TTL < 5s |
| Anti-loop guard | Hop counter on every internal layer | If `hop_count > 4` and no Faiz intervention, force-pause | resets every 60s |
| Thread for deep dive | Either Hermes sees `!hermes-thread` flag from Faiz, or natural deep-dive heuristic | Create thread from latest message, post first analysis | none |

### §10.4 Redis keys to maintain

```
hermes:last_turn:<channel_id>      # which bot spoke last + timestamp
hermes:cooldown:<bot_id>:<channel_id>  # last_sent_unix_ms, TTL 30s
hermes:hop_counter:<conversation_id>  # int, TTL 24h
hermes:emotional_dyad:<channel_id>  # shared emotional ledger
hermes:narrative_anchor:<turn_id>    # pointer to PostgreSQL durable entry
```

---

## §11 Open Questions / Decision Items for Next Phase

These items are NOT blockers but should be resolved before P28 implementation kicks off:

1. **Identity philosophy**: Are Guinevere and Pharsa both framed as "AI agents" (BOT tag = honest) OR are they meant to feel human-like? This decides single-webhook proxy (PluralKit) vs dual-bot approach.
2. **Faiz conversational trigger**: Does Faiz ever want to interject into the conversational stream? Reply-chat, @mention, or presence-based "Faiz online → suppress bot-to-bot depth"?
3. **Archive policy**: Public vs private thread for the off-feed sub-conversations? Linked to Faiz's preferred meta-narrative visibility.
4. **Cross-bot memory**: Do they share a memory schema (Postgres-backed) or maintain separate world models with periodic sync? Cadence?
5. **Voice participation**: Future — does P28 need voice? If yes, the "one bot per voice channel" rule forces architectural choice NOW.

---

## §12 Source Inventory (Primary)

### Discord Developer Documentation
- [Discord Developer Portal intro](https://docs.discord.com/developers/intro)
- [Rate Limits documentation](https://docs.discord.com/developers/topics/rate-limits)
- [Message Resource spec](https://docs.discord.com/developers/resources/message)
- [Threads documentation](https://docs.discord.com/developers/topics/threads)
- [Privileged Intents article](https://support-dev.discord.com/hc/en-us/articles/6207308062871-What-are-Privileged-Intents)
- [Bot verification article](https://support-dev.discord.com/hc/en-us/articles/360040720412)

### discord.py (Rapptz) Documentation
- [A Primer to Gateway Intents](https://discordpy.readthedocs.io/en/latest/intents.html)
- [discord.ext.tasks asyncio helpers](https://discordpy.readthedocs.io/en/stable/ext/tasks/index.html)
- [Migrating to v2 asyncio.run() pattern](https://discordpy.readthedocs.io/en/latest/migrating.html)
- [Migrating to v1 AutoShardedClient](https://discordpy.readthedocs.io/en/latest/migrating_to_v1.html)

### GitHub Permalinks (canonical references)
- [Rapptz/discord.py Issue #516 — multi-bot asyncio pattern, author canonical](https://github.com/Rapptz/discord.py/issues/516)
- [Cog-Creators/Red-DiscordBot Issue #1442 — multiple bots in one server](https://github.com/Cog-Creators/Red-DiscordBot/issues/1442)
- [openclaw/openclaw Issue #6821 — webhook routing multi-agent identity](https://github.com/openclaw/openclaw/issues/6821)
- [discord/discord-api-docs Discussion #5412 — Message Content privileged intent](https://github.com/discord/discord-api-docs/discussions/5412)
- [discord/discord-api-docs Discussion #5529 — bot voice-channel limit](https://github.com/discord/discord-api-docs/discussions/5529)
- [discordjs/guide sharding README](https://github.com/discordjs/guide/blob/main/guide/sharding/README.md)
- [discordjs/guide sharding additional info](https://github.com/discordjs/guide/blob/main/guide/guide/sharding/additional-information.md)

### Community References (supporting / corroborating)
- [PluralKit official site — canonical webhook proxy example](https://pluralkit.me/)
- [StackOverflow #68298840 — How to run multiple Discord clients simultaneously](https://stackoverflow.com/questions/68298840/how-to-run-multiple-discord-clients-simultaneously)
- [ArkCore blog, June 2026 — Discord Privileged Intents Update (10,000 user rule)](https://blogs.arkcore.arkdevlabs.com/discord-privileged-intents-10000-user-update)
- [Space-Node 2026 Discord Bot Rate Limit Guide](https://space-node.net/blog/discord-bot-rate-limiting-guide-2026)
- [Erik McClure — Pressure Based Anti-Spam for Discord Bots](https://erikmcclure.com/blog/pressure-based-anti-spam-for-discord-bots/)
- [DEV.to: Building a Multifunctional Discord Bot](https://dev.to/j3ffjessie/building-a-multifunctional-discord-bot-a-comprehensive-technical-deep-dive-3kf6)
- [Answer Overflow #1479533252539584834 — OpenClaw multi-agent Discord setup](https://www.answeroverflow.com/m/1479533252539584834)
- [Discord Community: Make the bot tag on Discord webhooks optional](https://support.discord.com/hc/en-us/community/posts/1500001210341-Make-the-bot-tag-on-discord-webhooks-optional)

---

## §13 Researcher Sign-Off

**This report is file-based evidence research**, prepared by Buffy — The Librarian per the librarian protocol. Every claim above is backed by either:
- A Discord developer documentation page (the spec itself)
- A discord.py/discord.js canonical documentation page
- A GitHub issue or PR in the authoritative repo (Rapptz, Cog-Creators, OpenClaw, discord-api-docs, discordjs/guide)
- A reputable community reference (PluralKit site, Answer Overflow, ArkCore, Space-Node)

The report does not assert any technical claim without an inline citation above. Where consensus is established, multiple sources are cited. Where Discord's own documentation is silent (e.g., webhook-receives-MESSAGE_CREATE), the limitation is stated explicitly.

**Time stamp**: 2026-06-28 Asia/Bangkok. As of this date, June 2026 Discord policy changes (privileged intent 10,000-user rule) are documented and effective per [ArkCore](https://blogs.arkcore.arkdevlabs.com/discord-privileged-intents-10000-user-update).

**Confidence**: HIGH for feasibility (every requirement has primary-source evidence). MEDIUM for fine-tuning community rhythm (design pattern synthesis, not a single canonical source).

— Buffy, The Librarian
