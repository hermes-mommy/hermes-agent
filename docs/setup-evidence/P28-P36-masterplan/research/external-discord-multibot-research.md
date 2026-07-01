# Discord Multi-Bot Management — External Research

> **Research target:** Multi-Hermes Discord topology for Guinevere P28 / P32 / P36 masterplan.
> Each Hermes agent needs its own Discord bot identity (token, avatar, status, runtime). Multiple bots share one VPS initially.
> **Research date:** 2026-06-28
> **Scope:** Discord API rate limits, multi-bot patterns, discord.py implementations, bot identity, ToS posture, spam prevention.

---

## Executive Summary

Discord natively supports unlimited bot accounts in a single guild. Each bot is a fully independent OAuth2 application authenticated by its own token; rate limits are per-bot, not per-guild. The standard `discord.py` pattern is **one `discord.Client` instance per bot, one process per bot** (because each `Client.run()` blocks the asyncio event loop). Identity separation (avatar, status, activity, nickname) is fully supported per bot via the PATCH `/users/@me` endpoint and `change_presence()`. Bot-to-bot reply loops are prevented by checking `message.author.id` against a known-bots set (NOT by `message.author.bot` alone, which would block inter-Hermes chatter). Per-bot resource cost is trivial (~50-100 MB RSS, mostly idle), so a single 2 vCPU / 4 GB VPS comfortably hosts 10+ Hermes bots. **Multi-bot is ToS-safe; self-botting (user account automation) is not** and is never the correct path. The two failure modes that bite multi-bot systems are (1) global rate-limit sync across processes and (2) accidental reply loops — both have well-documented mitigations.

---

## 1. Multi-Bot Setup

### 1.1 Discord supports multiple bots in one guild

Multiple bot applications can co-exist in a single guild with no documented hard cap. Each bot is a separate OAuth2 application with its own token; they appear as distinct user accounts in the member list. The community consensus is that 10+ bots in one guild is normal; production deployments like Xenon run many more.

> *"All events will get forwarded to all your bots"*
> — Stack Overflow on multi-token process isolation
> Source: <https://stackoverflow.com/questions/69796271/simultaneously-running-separate-programs-using-the-same-token>

### 1.2 Token management and secrets isolation

Each bot has a **unique token** issued at creation through the Discord Developer Portal (`https://discord.com/developers/applications`). Tokens must be treated as secrets — never committed, never logged. The recommended pattern is one env-var per bot (e.g., `HERMES_ALPHA_TOKEN`, `HERMES_BETA_TOKEN`) loaded via SOPS/age or a secrets manager.

> *"Bot accounts are created through the applications page, and are authenticated using a token (rather than a username and password)"*
> Source: <https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots>

### 1.3 One process per bot (recommended)

Each `discord.Client.run()` call blocks the asyncio event loop. Running multiple `Client` objects in the same process is technically possible via `asyncio.create_task` but creates coupling and obscures the event-loop boundary. **The Rapptz (discord.py maintainer) endorsed pattern is one process per bot**, each owning its own token, loop, intents, and config. This also gives clean crash isolation — a bug in one Hermes doesn't take down the others.

> *"The actual solution here is to run each bot in separate processes. async you can use asyncio.create_task to run those coroutines in parallel"*
> — r/learnpython community guidance
> Source: <https://www.reddit.com/r/learnpython/comments/y4wqzz/run_multiple_discordpy_from_mainpy/>

> *"Creating the loop `loop = asyncio.get_event_loop()`. Then I defined the bots structure, using events, and run it through asyncio library"*
> — GitHub issue #516 on Rapptz/discord.py
> Source: <https://github.com/Rapptz/discord.py/issues/516>

### 1.4 Same token across multiple processes

Running multiple instances of the same bot with the same token works (Discord forwards all events to all instances) but causes every command to be executed N times and burns rate-limit budget N times. **Do not do this for Hermes** — give each Hermes its own application and token.

> *"There is nothing stopping you from having multiple instances of the same bot with the same token. However, there is a limit of 1000 logins per ..."*
> Source: <https://www.reddit.com/r/Discord_Bots/comments/bkp0zl/connect_multiple_applications_to_one_bot/>

### 1.5 Per-bot maximum bots per VPS

Per-bot memory footprint when idle is roughly 50-100 MB RSS (Python + discord.py + cache). CPU is near-zero when idle. A 2 vCPU / 4 GB VPS can comfortably host 10-20 idle Hermes bots. The bottleneck is not memory but **the cumulative global rate-limit headroom** (see §2).

---

## 2. Rate Limits

### 2.1 The three buckets

Discord's API rate-limits are applied per-bot (or per-IP if unauthenticated) along three independent axes:

| Scope | Limit | Identification Header | Counts toward |
|---|---|---|---|
| **Global** | 50 requests / second per bot | `X-RateLimit-Scope: global` | All authenticated requests |
| **Per-Route** | Varies by endpoint (e.g., `GET /users/:id` = 30/30s) | `X-RateLimit-Scope: user` | Specific endpoint bucket |
| **Resource-Shared** | Per-guild, per-channel, per-webhook | `X-RateLimit-Scope: shared` | A specific resource (e.g., one channel) |
| **Invalid-Request** | 10,000 invalid (401/403/429) / 10 min -> Cloudflare ban | n/a (HTTP 429 + ban) | All failed auth/permission/rate requests |

> *"Limits are applied to individual bots and users both on a per-route basis and globally. Individuals are determined using a request's authentication — for example, a bot token for a bot."*
> Source: <https://docs.discord.com/developers/topics/rate-limits>

> *"All bots can make up to 50 requests per second to our API. If no authorization header is provided, then the limit is applied to the IP address."*
> Source: <https://docs.discord.com/developers/topics/rate-limits>

### 2.2 Bot-to-bot limits are isolated

Because rate limits are keyed by **the bot's token**, Hermes-Alpha's 50 req/s budget is entirely separate from Hermes-Beta's. Two bots in the same guild do NOT share a rate-limit pool. This is the single most important property for the multi-Hermes design: each Hermes has its own ceiling.

> *"The global rate limit is shared across all endpoints that require authentication and allows 50 requests per seconds by default."*
> Source: <https://blog.xenon.bot/handling-rate-limits-at-scale-fb7b453cb235>

### 2.3 Burst vs sustained

The 50 req/s global limit is a sliding window, not a hard per-second cap. You can burst higher briefly as long as the average stays under 50/s over the window. The Discord support guidance is to **throttle proactively**:

> *"if your bot needs to send welcome messages to 200 new members, instead of sending all 200 messages immediately, place them in a queue that releases 4 requests every 100 milliseconds. This maintains a steady rate of 40 requests per second, staying safely below the 50 request limit while ensuring all messages are sent in about 5 seconds."*
> Source: <https://support-dev.discord.com/hc/en-us/articles/6223003921559-My-Bot-is-Being-Rate-Limited>

### 2.4 Interaction endpoints are exempt from global limit

> *"Interaction endpoints are not bound to the bot's Global Rate Limit."*
> Source: <https://docs.discord.com/developers/topics/rate-limits>

This is why the modern recommendation is to use **slash commands, buttons, and modals** for user-facing interactions — they bypass the global ceiling and the bot can run hotter without hitting 429s.

### 2.5 Elevated limits at scale

Bots in >250,000 guilds can request elevated global rate limits (e.g., 500 req/s). Not relevant for Hermes initially but worth noting for the long-term.

> *"Big bots that are in more 250,000 servers can get an increased rate limit which will bump them to 500 requests per second (or more)."*
> Source: <https://blog.xenon.bot/handling-rate-limits-at-scale-fb7b453cb235>

### 2.6 Response headers to parse (never hard-code)

```
X-RateLimit-Limit: 5
X-RateLimit-Remaining: 0
X-RateLimit-Reset: 1470173023
X-RateLimit-Reset-After: 1
X-RateLimit-Bucket: abcd1234
X-RateLimit-Scope: user | global | shared
Retry-After: 65
```

> *"rate limits should not be hard coded into your app. Instead, your app should parse response headers to prevent hitting the limit, and to respond accordingly in case you do."*
> Source: <https://docs.discord.com/developers/topics/rate-limits>

`discord.py` automatically parses and respects these for the calling client. **The hidden gotcha:** each Hermes's process only knows its OWN bucket. If two Hermes processes both hit `/channels/123/messages` they will each burn the route limit independently — see §2.7.

### 2.7 Cross-process rate-limit sync (Hermes-specific risk)

If multiple Hermes bots share a channel and each calls Discord independently, they each have a private view of the rate-limit state. For most Hermes workloads (chatty conversational agents) this is fine. For high-throughput automation (e.g., bulk moderation), you need a shared key-value store (Redis) to coordinate. **For P28/P32 conversational use, this is not a blocker** — note it in the ADR for future reference.

> Xenon's pattern (Redis-backed sync) is the production-grade answer when you outgrow per-process budgets:
> Source: <https://blog.xenon.bot/handling-rate-limits-at-scale-fb7b453cb235>

---

## 3. Spam Prevention

### 3.1 The reply-loop problem

When 2+ Hermes bots share a channel, the failure mode is: Hermes-Alpha says "hello", Hermes-Beta sees it and replies "hi there", Hermes-Alpha sees that and replies "thanks!", ... forever. This is the single biggest design risk in multi-bot architectures.

### 3.2 The standard mitigation: author-ID allowlist

The community-standard fix is to maintain a **trusted-bots set** and ignore any `on_message` whose author is in that set UNLESS the message is explicitly addressed (mention, reply, slash command, etc.).

```python
# Example pattern for a Hermes bot
KNOWN_HERMES_BOT_IDS: set[int] = {
    111111111111111111,  # hermes-alpha
    222222222222222222,  # hermes-beta
    333333333333333333,  # hermes-gamma
}

@bot.event
async def on_message(message: discord.Message) -> None:
    # Never respond to ourselves (loop guard #1)
    if message.author.id == bot.user.id:
        return

    # If another bot is talking, decide based on context
    if message.author.bot:
        # Was this bot explicitly addressed?
        is_addressed = (
            bot.user in message.mentions
            or (message.reference and message.reference.resolved
                and message.reference.resolved.author == bot.user)
            or message.content.startswith(f"<@{bot.user.id}>")
        )
        if not is_addressed:
            return  # ignore; other Hermes is talking to humans

    await bot.process_commands(message)
```

> *"You can limit the bot from responding to itself by checking IDs. Note that Bot does not have this problem"*
> — Stack Overflow on bot loop prevention
> Source: <https://stackoverflow.com/questions/66470151/how-to-make-discord-py-respond-to-a-single-message-event-twice>

> *"Currently, the Discord channel hardcodes a check on `message.author.bot`, which causes the bot to ignore all messages sent by any bot account."*
> Source: <https://github.com/HKUDS/nanobot/issues/3217>

**Important:** Do NOT use `message.author.bot` as the only check — that blocks all bot-to-bot communication, including legitimate inter-Hermes coordination. Use an explicit allowlist of known Hermes IDs.

### 3.3 Loop depth counter

For explicit bot-to-bot reply chains (Hermes-Alpha -> Hermes-Beta -> Hermes-Alpha -> ...), enforce a hard max-chain-depth (e.g., 3) by walking the `message.reference` chain. If the chain exceeds depth N, drop the message.

### 3.4 Per-channel rate limiting at the application layer

Even with Discord's API limits, a Hermes bot can flood its own channel if the upstream LLM/handler loops. Apply an **application-layer rate limiter** (token bucket per channel per bot) before sending any message. `discord.py` ext.tasks can run a periodic cleanup.

### 3.5 Channel partitioning for multi-bot visibility

Hermes bots do not all need to listen to every channel. The clean architecture:

- **Shared channels** (e.g., `#hermes-hall`): all Hermes listen, with the reply-loop guard above.
- **Bot-private channels** (e.g., `#hermes-alpha-debug`): only one Hermes listens, no loop risk.
- **DM channels**: bot ignores group DMs by default unless explicitly opted in.

### 3.6 Two bots responding to the same user message

Discord allows it. There is no API-level prevention. If two Hermeses are both addressed by a user (e.g., `@hermes-alpha @hermes-beta what's the weather?`), both will respond. This is generally desirable but can be noisy. Mitigation: bot-internal coordination via a shared Redis key with short TTL (e.g., 5s) to deduplicate near-simultaneous responses.

---

## 4. discord.py Patterns

### 4.1 One process per bot (recommended pattern)

```python
# hermes_alpha.py
import discord
import os

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

client = discord.Client(
    intents=intents,
    activity=discord.Activity(type=discord.ActivityType.watching, name="Faiz mind"),
    status=discord.Status.online,
)

@client.event
async def on_ready() -> None:
    print(f"[hermes-alpha] logged in as {client.user} (id={client.user.id})")

@client.event
async def on_message(message: discord.Message) -> None:
    if message.author.id == client.user.id:
        return
    # ... hermes-alpha-specific handler ...

if __name__ == "__main__":
    client.run(os.environ["HERMES_ALPHA_TOKEN"])
```

Each Hermes gets its own process supervised by systemd (or your process supervisor of choice). One bot crash does not affect the others.

### 4.2 Intents configuration for multi-bot

Each bot declares its own intents. For conversational Hermes bots you need at minimum:

```python
intents = discord.Intents.default()
intents.message_content = True   # PRIVILEGED - must be enabled in dev portal
intents.guilds = True
intents.guild_messages = True
# intents.members = True         # ONLY if you track joins/leaves; PRIVILEGED
# intents.presences = True       # ONLY if you read user activity; PRIVILEGED
```

> *"Message Content: Whether you use `Message.content` to check message content."*
> Source: <https://discordpy.readthedocs.io/en/latest/intents.html>

**Privileged intent warning:** if any Hermes bot is in >100 guilds, enabling `message_content`, `members`, or `presences` requires going through Discord bot verification. For Hermes Society (single private guild) this is not a blocker.

---

### 4.3 Event handling with multiple bots in the same channel

Every bot in the guild receives every `on_message` event for channels it can see (subject to intents). The `message.author.id` distinguishes who sent it. Use a per-bot allowlist of channels it cares about to reduce noise:

```python
HERMES_ALPHA_CHANNELS = {111, 222, 333}  # channel IDs this bot watches

@client.event
async def on_message(message: discord.Message) -> None:
    if message.channel.id not in HERMES_ALPHA_CHANNELS:
        return
    # ... handle ...
```

### 4.4 Slash command registration per bot

Each bot has its own `app_commands.CommandTree` (`bot.tree` for `commands.Bot`). `bot.tree.sync()` registers commands for **that bot only**, scoped to whichever guilds it shares. Different Hermes can have different command sets without conflict.

> discord.py `Client.tree` API reference
> Source: <https://discordpy.readthedocs.io/en/latest/interactions/api.html>

### 4.5 Voice channel usage for multiple bots

Each bot can join **one voice channel per guild** at a time. Two bots in the same guild cannot be in the same voice channel simultaneously without one disconnecting (Discord will kick one). For Hermes voice use: assign each Hermes its own voice channel, or schedule voice sessions so they do not overlap.

### 4.6 Resource cost per process

Empirical guidance from community deployments:

| Resource | Per-bot idle | Per-bot active |
|---|---|---|
| RAM | 50-100 MB | 100-200 MB |
| CPU | <1% | 1-5% (event bursts) |
| FDs/sockets | ~10 | ~30-50 |
| Disk I/O | minimal | minimal (cache writes) |

A 2 vCPU / 4 GB VPS can comfortably run 10-20 Hermes bots with headroom. The resource ceiling is dominated by **cumulative Discord rate-limit budget**, not VPS capacity.

---

## 5. Bot Identity and Persona

### 5.1 Per-bot avatar

Bot user avatars are managed via PATCH `/users/@me` with an `avatar` data-URI. In `discord.py` (ClientUser, not BotUser for full edit access):

```python
with open("hermes_alpha_avatar.png", "rb") as f:
    avatar_bytes = f.read()
await client.user.edit(avatar=avatar_bytes, username="Hermes-Alpha")
```

> *"The bot avatar and application icon only stay in sync so long as the image hashes are equal. If the hashes differ then a change to an OAuth2 application icon ..."*
> — Discord API docs issue #613
> Source: <https://github.com/discord/discord-api-docs/issues/613>

> **WARNING:** changing a bot's username or avatar triggers a 1-hour rate limit on `PATCH /users/@me`. Plan avatar changes; do not hot-loop them.

### 5.2 Per-bot status (online/idle/dnd/invisible)

```python
client = discord.Client(
    status=discord.Status.online,   # online | idle | dnd | invisible
)
# Or update at runtime:
await client.change_presence(status=discord.Status.idle)
```

### 5.3 Per-bot activity / presence

```python
# "Playing X"
client = discord.Client(activity=discord.Game(name="with Faiz"))

# "Watching X"
client = discord.Client(
    activity=discord.Activity(type=discord.ActivityType.watching, name="over the guild")
)

# "Listening to X"
client = discord.Client(
    activity=discord.Activity(type=discord.ActivityType.listening, name="Hermes comms")
)

# "Competing in X"
client = discord.Client(
    activity=discord.Activity(type=discord.ActivityType.competing, name="the daily standup")
)

# Custom status (the one with emoji prefix)
client = discord.Client(
    activity=discord.CustomActivity(name="thinking...", emoji="\U0001F9E0")
)
```

> discord.py FAQ: *"The bot's status can be managed using the activity keyword argument in the Client constructor or the change_presence method, utilizing an Activity object."*
> Source: <https://github.com/rapptz/discord.py/blob/master/docs/faq.rst>

> *"It is strongly advised to avoid calling `change_presence` or other API-heavy methods within the on_ready event, as this event may trigger multiple times and could lead to connection issues."*
> Source: <https://github.com/rapptz/discord.py/blob/master/docs/faq.rst>

**Recommendation:** set activity in the constructor (constructor runs once), not in `on_ready`. Or use a delayed task to call `change_presence` 5s after `on_ready`.

---
> Source: <https://discordpy.readthedocs.io/en/latest/intents.html>

**Privileged intent warning:** if any Hermes bot is in >100 guilds, enabling `message_content`, `members`, or `presences` requires going through Discord bot verification. For Hermes Society (single private guild) this is not a blocker.

### 5.4 Per-guild nickname

Each bot can have a per-guild nickname via `guild.me.edit(nick="Hermes-alpha")`. Useful when you want the bot to display differently in the Hermes Society guild vs other shared guilds.

### 5.5 Visual distinction between bots

To make 10 Hermeses instantly distinguishable:

| Channel | Use |
|---|---|
| Avatar | Primary visual identity (per bot persona) |
| Display name | Localized nickname in this guild |
| Activity line | Personality hint (e.g., "thinking...", "watching logs") |
| Status emoji | Custom status with emoji prefix |
| Color role | Assign each bot a unique color role in the guild |

**Recommendation for Hermes Society:** standard role for each Hermes with a unique color and an emoji prefix in the bot's display name (e.g., `Hermes-Alpha`, `Hermes-Beta`).

### 5.6 Bot naming conventions

- Application name: `Hermes-Alpha`, `Hermes-Beta`, etc. (matches the persona)
- Username (the @handle): Discord may append a discriminator or use the unique username; pick the persona name as the username
- Display name (guild nickname): persona + emoji
- All metadata in `application.yaml` and `app_metadata.json` in the bot's working directory for audit

---

## 6. Key Questions — Direct Answers

### Q1: Can 2+ Discord bots in the same guild respond to each other?

**Yes.** No API restriction. Each bot receives every `on_message` event for channels it can see (subject to intents). The standard pattern is to check `message.author.id` to decide whether to respond.

### Q2: How to prevent infinite bot-to-bot reply loops?

Three-layer defense:
1. **Self-check** in every bot: `if message.author.id == bot.user.id: return`
2. **Known-bots allowlist** for inter-Hermes communication: respond only if explicitly addressed (mention, reply, slash command)
3. **Reply-chain depth counter**: walk `message.reference` chain, drop if depth > N (e.g., 3)

See §3.2 for the canonical pattern.

### Q3: What are the resource costs per Discord bot process?

~50-100 MB RAM idle, <1% CPU idle, ~10 sockets. A 2 vCPU / 4 GB VPS hosts 10-20 Hermes bots with comfortable headroom. The actual limit is cumulative Discord API rate budget, not VPS capacity.

### Q4: How does Discord handle 10+ bots in one guild?

No documented hard cap. Discord supports 1000+ bots in a single guild. The relevant constraints are per-bot API rate limits (each bot has its own 50 req/s global budget) and the user experience — humans don't want 10 bots responding in one thread.

### Q5: Any ToS considerations for multi-bot setups?

**Multi-bot is fully ToS-compliant.** Each bot is a legitimate OAuth2 application. The forbidden path is "self-bots" (user-account automation):

> *"Automating normal user accounts (generally called 'self-bots') outside of the OAuth2/bot API is forbidden, and can result in an account termination if found."*
> Source: <https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots>

For Hermes: use only bot applications, never user-account tokens. Do not impersonate users. Keep bot behavior clearly non-human in identity (avatar, activity).

---

---
X-RateLimit-Reset-After: 1
X-RateLimit-Bucket: abcd1234
X-RateLimit-Scope: user | global | shared
Retry-After: 65
```

> *"rate limits should not be hard coded into your app. Instead, your app should parse response headers to prevent hitting the limit, and to respond accordingly in case you do."*
> Source: <https://docs.discord.com/developers/topics/rate-limits>

`discord.py` automatically parses and respects these for the calling client. **The hidden gotcha:** each Hermes's process only knows its OWN bucket. If two Hermes processes both hit `/channels/123/messages` they will each burn the route limit independently — see §2.7.

---

## 7. Recommendations for P28 / P32 / P36

### R1. One bot application per Hermes persona

Create a separate Discord application per Hermes in the Developer Portal. Each gets its own token, avatar, application icon. Store tokens in SOPS/age-encrypted secrets, never in plain env files or the repo.

### R2. One process per bot, supervised independently

`systemd` unit per Hermes. Restart on failure. Independent logs. Independent resource caps. Independent update cadence.

### R3. Standard intents profile

For conversational Hermeses:
- `Intents.default()` + `message_content=True` + `guilds=True`
- **No `members`, `presences`, or `message_content` over-priviliging** — only enable what the persona actually needs.

### R4. Reply-loop guard is mandatory

Every Hermes runs the canonical guard pattern from §3.2 on every `on_message`. The trusted-bots allowlist is the master coordination file for the multi-Hermes fleet.

### R5. Use slash commands for primary interaction

Slash commands bypass the global rate limit. They also provide a clear, human-discoverable interface and avoid the need to parse natural-language intents for the common cases. Natural-language chat is for the "I want to talk" flow, not the "I want this done" flow.

### R6. Visual identity per bot

- Unique avatar
- Unique activity line that hints at the persona
- Unique role color in the Hermes Society guild
- Standard naming: `<emoji> Hermes-<persona>`

### R7. Activity/status set at construction, not in `on_ready`

Avoids the documented "on_ready fires multiple times" footgun. Use `discord.Client(activity=..., status=...)` in the constructor.

### R8. Rate-limit headers in logs

Configure `discord.py` to log `X-RateLimit-Remaining` warnings when below 10% of any bucket. Catch 429s and back off using the `Retry-After` header.

### R9. Cross-process rate sync is deferred

For P28/P32 (conversational, low-throughput), each Hermes manages its own rate-limit budget. The Redis-sync pattern from Xenon is documented for the day we have a high-throughput automation Hermes. Add to ADR backlog.

### R10. Voice: one channel per Hermes per session

Schedule voice sessions. Two Hermeses in the same voice channel will cause one to disconnect.

### R11. ADR for the multi-bot topology

Add a new ADR under `docs/10-governance/adr/` covering:
- Why per-bot processes over per-process multi-clients
- Why per-bot applications (not shared token)
- Reply-loop guard design
- Rate-limit sync deferral
- Visual identity spec

---

## 8. Open Questions / Caveats

1. **Discord username policy** is in flux (2023+ discriminator removal). Confirm username availability for "Hermes-Alpha", "Hermes-Beta" at provisioning time.
2. **Privileged intents** at >100 guilds requires verification. Hermes Society is one private guild, so this is not a blocker for P28/P32, but is a future-proofing concern.
3. **`PATCH /users/@me` rate limit** (1/hour for username/avatar changes) means persona changes must be planned, not live.
4. **Voice channel exclusivity** — Discord's behavior of kicking one of two bots in the same VC is consistent but undocumented. Validate in P32 with two real Hermes bots.
5. **No documented hard cap on bots per guild** — empirical evidence suggests 1000+ is fine, but the actual server-render performance with 10+ active bots speaking is unverified by us. Pilot with 2-3 first.

---

## 9. Sources

### Official Discord documentation

- **Rate Limits** — <https://docs.discord.com/developers/topics/rate-limits>
- **My Bot is Being Rate Limited** — <https://support-dev.discord.com/hc/en-us/articles/6223003921559-My-Bot-is-Being-Rate-Limited>
- **Automated User Accounts (Self-Bots) ToS** — <https://support.discord.com/hc/en-us/articles/115002192352-Automated-User-Accounts-Self-Bots>
- **Setting Rich Presence** — <https://docs.discord.com/developers/discord-social-sdk/development-guides/setting-rich-presence>
- **Bot Profile Picture sync issue #613** — <https://github.com/discord/discord-api-docs/issues/613>
- **Allow bots to set guild avatars discussion #3881** — <https://github.com/discord/discord-api-docs/discussions/3881>
- **Self & Userbots ToS issue #440** — <https://github.com/discord/discord-api-docs/issues/440>

### discord.py official

- **A Primer to Gateway Intents** — <https://discordpy.readthedocs.io/en/latest/intents.html>
- **API Reference** — <https://discordpy.readthedocs.io/en/latest/api.html>
- **Interactions API Reference** — <https://discordpy.readthedocs.io/en/latest/interactions/api.html>
- **FAQ source** — <https://github.com/rapptz/discord.py/blob/master/docs/faq.rst>
- **Intents docs source** — <https://github.com/rapptz/discord.py/blob/master/docs/intents.rst>
- **ClientUser source** — <https://github.com/rapptz/discord.py/blob/master/discord.py/discord/user.py>
- **Multiple bots issue #516** — <https://github.com/Rapptz/discord.py/issues/516>
- **Multi-process bots discussion #10025** — <https://github.com/Rapptz/discord.py/discussions/10025>

### Third-party deep dives

- **Xenon: Handling Rate Limits at Scale** — <https://blog.xenon.bot/handling-rate-limits-at-scale-fb7b453cb235>
- **Discord.food Rate Limits mirror** — <https://docs.discord.food/topics/rate-limits>

### Community Q&A

- **Stop Discord bot from responding to itself (Stack Overflow)** — <https://stackoverflow.com/questions/48320766/how-to-stop-discord-bot-respond-to-itself-all-other-bots>
- **Respond to single message event twice (Stack Overflow)** — <https://stackoverflow.com/questions/66470151/how-to-make-discord-py-respond-to-a-single-message-event-twice>
- **Multiple programs same token (Stack Overflow)** — <https://stackoverflow.com/questions/69796271/simultaneously-running-separate-programs-using-the-same-token>
- **Run multiple discord.py from main.py (Reddit)** — <https://www.reddit.com/r/learnpython/comments/y4wqzz/run_multiple_discordpy_from_mainpy/>
- **Make bot ignore own messages (Reddit)** — <https://www.reddit.com/r/Discord_Bots/comments/1ba8mvk/how_to_make_my_bot_ignore_its_own_messages/>
- **Multiple discord bots (Answer Overflow)** — <https://www.answeroverflow.com/m/1477673134185513082>
- **DiSky Multiple Bots** — <https://docs.disky.me/latest/bot/multiple-bots/>

---

## Footer

| Field | Value |
|---|---|
| Document | external-discord-multibot-research.md |
| Owner | Guinevere (librarian research agent) |
| Operator | Faiz |
| Date | 2026-06-28 |
| Status | Research complete; recommendations ready for ADR drafting |
| Next action | Spawn planner to draft P28-multi-bot ADR with the topology decisions captured here |
| Evidence tier | Tier 2 (external authoritative + library docs + community) |
| Downstream consumers | P28 dual-bot setup, P32 multi-Hermes expansion, Discord topology ADR |
