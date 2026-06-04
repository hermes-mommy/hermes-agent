# Discord Bot LLM Integration Patterns — Production Research Report

**Date**: 2026-06-03
**Scope**: Streaming, chunking, rate limiting, cost tracking, typing indicators, AsyncIO patterns
**Sources**: Production OSS bots (DiscordSam, llmcord, js-llmcord), discord.cab guide, discord.py docs, OSS rate limiters

---

## 1. Streaming LLM Responses to Discord

### 1.1 The Golden Rule: Edit-in-Place, Not Chunked Send

Every production bot uses **edit-in-place** — send one placeholder message, then repeatedly `.edit()` it as chunks arrive. This is unanimous across all studied implementations. Nobody sends multiple messages for a single LLM response (unless the response exceeds Discord's character limits, see §4).

**Why**: Multiple separate messages flood the channel and break conversation flow. Edit-in-place gives the user a single growing message that feels responsive.

### 1.2 The Rate-Limit-Safe Streaming Loop

Source: [discord.cab streaming guide](https://www.discord.cab/how-to-stream-ai-replies-discord-bots-langchain-patterns/), validated by [DiscordSam's `_stream_llm_handler`](https://github.com/helix4u/DiscordSam/blob/main/llm_handling.py) and [llmcord's main loop](https://github.com/jakobdylanc/llmcord/blob/main/llmcord.py)

```
1. Post a placeholder message immediately ("Thinking...")
2. Buffer model chunks into a rolling text window
3. Edit on a FIXED CADENCE (time-based), not per-token
4. If Discord responds with rate-limit signals, increase interval + retry
5. Finalize with one clean final message state
```

### 1.3 Critical Streaming Parameters (Production Values)

Source: [DiscordSam config](https://github.com/helix4u/DiscordSam) via `config.py`

| Parameter | DiscordSam | llmcord | Recommendation |
|---|---|---|---|
| Edit throttle | `STREAM_EDIT_THROTTLE_SECONDS = 0.1` | `EDIT_DELAY_SECONDS = 1` | **0.2–0.5s** for smooth UX, 1.0s for safety |
| Max chars per edit | `MAX_CHARS_PER_EDIT = inf` (time-gated only) | N/A (time-gated only) | Time-gated is standard; char gating adds complexity |
| Edits per second target | `EDITS_PER_SECOND = 1.3` | N/A | **1–2 edits/sec** — above 5 risks Discord 429s |
| Catch-up threshold | `CATCH_UP_WAIT_THRESHOLD_SECONDS = 1.5` | N/A | If an edit takes >1.5s, skip remaining edits and catch up next cycle |
| Incomplete indicator | N/A | `STREAMING_INDICATOR = " ⚪"` | Append an indicator to show message is still streaming |
| Embed colors | `incomplete=orange, complete=green` | `incomplete=orange, complete=dark_green` | Use color to signal completion |

### 1.4 DiscordSam's Production Streaming Implementation

Source: [_stream_llm_handler() at L122-L264](https://github.com/helix4u/DiscordSam/blob/main/llm_handling.py)

Key architecture decisions:

```python
# 1. Time-gated edits, NOT token-gated
current_time = asyncio.get_event_loop().time()
if accumulated_delta_for_update and \
   (current_time - last_edit_time >= (1.0 / config.EDITS_PER_SECOND) or \
    len(accumulated_delta_for_update) > config.MAX_CHARS_PER_EDIT):

# 2. Auto-splitting into multiple embed messages if response > STREAM_EMBED_MAX_LENGTH
text_chunks = chunk_text(display_text, config.STREAM_EMBED_MAX_LENGTH)
for i, chunk_content_part in enumerate(text_chunks):
    embed = discord.Embed(
        title=title if i == 0 else f"{title} (cont.)",
        description=chunk_content_part,
        color=config.EMBED_COLOR["incomplete"],
    )

# 3. Catch-up skip: if an edit was slow (rate-limited), skip remaining batch
if (asyncio.get_event_loop().time() - t_before
        >= config.CATCH_UP_WAIT_THRESHOLD_SECONDS):
    break  # Next cycle shows fresh accumulated content

# 4. Authoritative flush after stream ends
# Final chunks get "complete" color, any leftover messages deleted
for k in range(len(final_chunks), len(sent_messages)):
    await sent_messages[k].delete()
```

### 1.5 Three Streaming Architecture Patterns

Source: [discord.cab streaming guide](https://www.discord.cab/how-to-stream-ai-replies-discord-bots-langchain-patterns/)

| Pattern | Setup Complexity | Rate-Limit Safety | Best For |
|---|---|---|---|
| **SSE Bridge** — LLM → SSE → buffer → timed Discord edit | Low | High | Single-response assistants, Q&A bots |
| **WebSocket Relay** — WS handles many concurrent streams | Medium-High | Medium-High | Multi-user interactive bots |
| **Async-Generator Pipeline** — `async for chunk in stream` with middleware | Medium | High (if throttled) | Custom, policy-heavy bots |

**For your use case**: Start with the **Async-Generator pipeline** (it's what both production bots use). You control the streaming yourself via an `async for` loop, and you can inject middleware for truncation, moderation, or pause/resume logic.

---

## 2. Typing Indicator Management During Long LLM Calls

### 2.1 The context manager pattern

Source: [discord.py docs on `channel.typing()`](https://discordpy.readthedocs.io/en/latest/api.html)

```python
# Indefinite typing (lasts as long as the context manager is open)
async with channel.typing():
    await asyncio.sleep(20)  # LLM call here

await channel.send('Done!')
```

```python
# 10-second timeout version (if awaited directly)
await channel.typing()  # typing for 10 seconds max
```

### 2.2 Production Pattern: Wrap the ENTIRE LLM call

Source: [llmcord.py L215](https://github.com/jakobdylanc/llmcord/blob/main/llmcord.py)

```python
async with new_msg.channel.typing():
    async for chunk in await openai_client.chat.completions.create(**openai_kwargs):
        # stream processing + message editing
        ...
```

This is the simplest and most correct pattern. The typing indicator stays active for as long as the `async with` block is executing. You DON'T need to pulse/re-send typing — the context manager handles it.

### 2.3 For Streaming Middleware: Periodic Typing Pings

Source: [gambletan/unified-channel `StreamingMiddleware`](https://github.com/gambletan/unified-channel/commit/91254a5be775983a256c69977ea8ae9840903434)

If you're building a middleware layer that needs to send typing indicators proactively during stream collection:

```python
class StreamingMiddleware:
    def __init__(self, typing_interval=3.0, chunk_delay=0.5):
        self.typing_interval = typing_interval  # seconds between typing pings
        self.chunk_delay = chunk_delay

    async def _send_typing(self, adapter, msg):
        """Periodically send typing indicators."""
        while not self._stream_done:
            await adapter.send_typing(msg)
            await asyncio.sleep(self.typing_interval)
```

**Key insight**: The `channel.typing()` context manager is sufficient for most cases. You rarely need manual typing pings unless you have a very long (>60s) LLM call where Discord's default typing timeout could expire.

### 2.4 Discord's Typing Timeout

Discord auto-stops the typing indicator after ~10 seconds if no new message is sent. The `async with channel.typing()` context manager in discord.py handles this automatically — it re-triggers the indicator under the hood. So you don't need to worry about this.

---

## 3. Response Length Management — Discord 2000/4000 Character Limits

### 3.1 Character Limits

| Message Type | Max Characters | Strategy |
|---|---|---|
| Plain text message | **2000** | Split into multiple messages with `(1/3)`, `(2/3)`, `(3/3)` markers |
| Embed description | **4096** | Embed preferred for AI responses |
| Embed title | 256 | Short, descriptive |
| Embed field value | 1024 | N/A for streaming text |
| Embed total | 6000 | Don't stuff too many fields |

### 3.2 Production Strategies

#### Strategy A: Embed-based with auto-split (DiscordSam, llmcord)

Source: Both bots use embeds for AI responses (larger 4096 char limit), then split into multiple embed messages if the content exceeds that.

```python
# From DiscordSam utils.py
def chunk_text(text: str, max_length: int = 4096) -> List[str]:
    chunks = []
    current_chunk = ""
    for line in text.splitlines(keepends=True):
        if len(current_chunk) + len(line) > max_length:
            if current_chunk: chunks.append(current_chunk)
            current_chunk = line
            while len(current_chunk) > max_length:
                chunks.append(current_chunk[:max_length])
                current_chunk = current_chunk[max_length:]
        else:
            current_chunk += line
    if current_chunk: chunks.append(current_chunk)
    return chunks if chunks else [""]
```

Split messages get sequential titles: `"Sam's Response"`, `"Sam's Response (cont.)"`, etc.

#### Strategy B: Plain text with split (llmcord optional mode)

```python
if use_plain_responses := config.get("use_plain_responses", False):
    max_message_length = 4000  # Discord's actual plain text limit
else:
    max_message_length = 4096 - len(STREAMING_INDICATOR)
```

When using embeds, llmcord reserves 1 char for the streaming indicator (⚪).

### 3.3 Recommendation

**Use embeds for AI responses** — gives you 4096 chars vs 2000, plus visual distinction (colored sidebar). Split into multiple embeds if needed. For very long responses (>12K chars), consider:
1. First embed: summary + "full response below" indicator
2. Follow-up messages: the complete text, chunked

---

## 4. AsyncIO Patterns for Concurrent Message Sending + LLM Calls

### 4.1 Per-Channel Lock (Critical)

Source: [DiscordSam `state.py` per-channel locks](https://github.com/helix4u/DiscordSam/blob/main/state.py)

```python
channel_lock = bot_state.get_channel_lock(interaction.channel_id)
async with channel_lock:
    # Only ONE LLM call + message stream per channel at a time
    full_response_content, final_prompt = await _run_stream()
```

This prevents:
- Two users triggering simultaneous LLM calls in the same channel
- Race conditions on message edits
- Discord rate limit violations from concurrent edits

### 4.2 Background Post-Processing

Source: [DiscordSam `start_post_processing_task` in utils.py](https://github.com/helix4u/DiscordSam/blob/main/utils.py)

```python
def start_post_processing_task(coro, *, progress_message=None) -> asyncio.Task:
    async def _runner():
        try:
            await coro
        finally:
            if progress_message:
                await progress_message.delete()
    return asyncio.create_task(_runner())

# Usage: RAG ingestion runs in background AFTER response is sent
start_post_processing_task(
    ingest_conversation_to_chromadb(...),
    progress_message=progress_msg,  # "Post-processing..." message, deleted when done
)
```

**Pattern**: Send the response first (user sees it immediately), then fire `asyncio.create_task()` for any post-processing (RAG ingestion, TTS, analytics, cost logging). The user never waits for background work.

### 4.3 Non-Blocking LLM Call Lifecycle

```
User Message Received
  ├── async with channel.typing():           # Start typing indicator
  │   └── async for chunk in llm_stream:     # Stream chunks
  │       ├── Buffer chunk
  │       └── Edit message (time-throttled)   # Non-blocking edit
  │
  ├── Send final response (or update embed)   # Response is now visible
  ├── asyncio.create_task(rag_ingestion())    # Fire-and-forget background
  ├── asyncio.create_task(send_tts_audio())   # Fire-and-forget background
  └── asyncio.create_task(log_cost_usage())   # Fire-and-forget background
```

### 4.4 Token Expiry Fallback

Source: [DiscordSam `safe_message_edit` in utils.py](https://github.com/helix4u/DiscordSam/blob/main/utils.py)

Interaction tokens expire after 15 minutes. Production bots handle this:

```python
async def safe_message_edit(message, channel, **kwargs):
    try:
        await message.edit(**kwargs)
        return message
    except discord.HTTPException as e:
        if e.status == 401 and e.code == 50027:
            # Token expired — send a new message instead
            new_msg = await channel.send(**kwargs)
            await message.delete()  # Clean up the dead message
            return new_msg
```

---

## 5. Rate Limiting Strategies for Per-User LLM Calls

### 5.1 Sliding Window Rate Limiter — Production Implementation

Source: [DiscordSam `rate_limiter.py`](https://github.com/helix4u/DiscordSam/blob/main/rate_limiter.py)

```python
class RateLimiter:
    """Proactive async rate limiter with sliding window and per-key cooldowns."""

    def __init__(self, *, requests_per_minute=16.0, jitter_seconds=1.5,
                 failure_backoff_seconds=3.0, fallback_window_seconds=90.0):
        self._lock = asyncio.Lock()
        self._request_timestamps: dict[str, deque[float]] = {}  # per-key deque

    async def await_slot(self, key: str) -> None:
        while True:
            async with self._lock:
                now = time.monotonic()
                # Prune timestamps outside the window
                cutoff = now - 60.0
                while self._request_timestamps[key] and \
                      self._request_timestamps[key][0] < cutoff:
                    self._request_timestamps[key].popleft()

                if len(self._request_timestamps[key]) < self._requests_per_minute:
                    self._request_timestamps[key].append(now)
                    return  # Slot granted

                # Calculate wait time until oldest slot expires
                wait_for = (self._request_timestamps[key][0] + 60.0) - now

            if wait_for > 0:
                await asyncio.sleep(wait_for)
```

**Why sliding window over token bucket**: More accurate at boundary conditions. A fixed window can allow 2x the limit at window edges. Sliding window with deque is O(1) and precise.

### 5.2 Reactive Cooldown from 429 Headers

Source: Same file, `record_response()` method

```python
async def record_response(self, key, status, headers):
    normalized = {k.lower(): v for k, v in headers.items()}

    # Respect Retry-After header
    retry_after = normalized.get("retry-after")
    if retry_after:
        retry_seconds = float(retry_after)

    # Respect X-RateLimit-Reset when remaining=0
    rate_reset = normalized.get("x-rate-limit-reset")
    rate_remaining = normalized.get("x-rate-limit-remaining")
    if rate_reset and rate_remaining == "0":
        retry_seconds = float(rate_reset) - time.time()

    # Fallback for 429 without headers
    if retry_seconds is None and status == 429:
        retry_seconds = self._failure_backoff_seconds  # 3.0s default

    # Apply with jitter
    jitter = random.uniform(0.0, self._jitter_seconds)
    self._next_available[key] = time.monotonic() + retry_seconds + jitter
```

### 5.3 Token Bucket Alternative

Source: [ProtoModder/discord-middleware](https://github.com/ProtoModder/discord-middleware)

```yaml
rate_limit:
  requests_per_minute: 10   # sustained rate
  burst_limit: 20           # temporary burst above sustained
```

Token bucket is simpler to implement but less precise at boundaries. Good for simple cooldowns; sliding window is better for strict enforcement.

### 5.4 Per-User Cooldown (Simple Variant)

Source: [mljourney.com Discord bot guide](https://mljourney.com/how-to-build-a-discord-bot-with-ollama/)

```python
user_cooldowns: dict[int, float] = {}
COOLDOWN_SECONDS = 10

def is_on_cooldown(user_id: int) -> float:
    last = user_cooldowns.get(user_id, 0)
    remaining = COOLDOWN_SECONDS - (time.time() - last)
    return remaining if remaining > 0 else 0

# In slash command:
if cd := is_on_cooldown(interaction.user.id):
    await interaction.response.send_message(f'Wait {cd:.1f}s.', ephemeral=True)
    return
user_cooldowns[interaction.user.id] = time.time()
```

### 5.5 Discord's Own Rate Limits

Source: [Discord Developer Docs](https://docs.discord.com/developers/topics/rate-limits)

- **Global**: 50 requests per second per bot token
- **Per-route**: varies by endpoint; headers tell you (`X-RateLimit-Bucket`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`)
- **Message edits**: No published hard limit, but ~5 edits/second triggers 429 in practice
- **Key headers to respect**: `Retry-After`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`, `X-RateLimit-Scope`

### 5.6 Multi-Resource LLM Rate Limiting (token-throttle)

Source: [token-throttle PyPI](https://pypi.org/project/token-throttle/8.0.4/)

For when you need to limit both requests AND tokens:

```python
limiter = RateLimiter(
    PerModelConfig(quotas=UsageQuotas([
        Quota(metric="requests", limit=60, per_seconds=60),
        Quota(metric="tokens", limit=90_000, per_seconds=60),
    ])),
    backend=MemoryBackendBuilder(),
)

# Reserve before call
reservation = await limiter.acquire_capacity(
    model="demo-model", usage={"requests": 1, "tokens": 1_000})

# After call, refund unused
await limiter.refund_capacity(
    reservation=reservation, actual_usage={"requests": 1, "tokens": 425})
```

---

## 6. Cost Tracking Patterns for LLM Calls in Discord Bots

### 6.1 Token Usage Extraction (Standard Pattern)

Every LLM response includes usage data. Production bots extract it:

```python
# From streaming or non-streaming OpenAI response
if hasattr(response, 'usage'):
    prompt_tokens = response.usage.prompt_tokens
    completion_tokens = response.usage.completion_tokens
    total_tokens = response.usage.total_tokens

    # Cost calculation (per-model pricing)
    cost = calculate_cost(model, prompt_tokens, completion_tokens)
```

### 6.2 Lightweight: Zero-Dependency SQLite Tracking

Source: [batish52/llm-cost-tracker](https://github.com/batish52/llm-cost-tracker)

```python
# Simple pattern for a Discord bot:
import sqlite3, json

class CostTracker:
    """Track LLM costs in SQLite. Zero external dependencies."""

    def __init__(self, db_path="llm_costs.db"):
        self.db = sqlite3.connect(db_path)
        self.db.execute("""CREATE TABLE IF NOT EXISTS costs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT DEFAULT (datetime('now')),
            user_id TEXT,
            channel_id TEXT,
            model TEXT,
            prompt_tokens INTEGER,
            completion_tokens INTEGER,
            cost_usd REAL,
            intent TEXT
        )""")

    def record(self, user_id, channel_id, model, prompt_tokens,
               completion_tokens, cost_usd, intent=""):
        self.db.execute(
            "INSERT INTO costs (user_id, channel_id, model, prompt_tokens, "
            "completion_tokens, cost_usd, intent) VALUES (?,?,?,?,?,?,?)",
            (user_id, channel_id, model, prompt_tokens,
             completion_tokens, cost_usd, intent))
        self.db.commit()

    def get_total_cost(self) -> float:
        return self.db.execute("SELECT SUM(cost_usd) FROM costs").fetchone()[0] or 0.0

    def get_cost_by_user(self, user_id: str) -> float:
        return self.db.execute(
            "SELECT SUM(cost_usd) FROM costs WHERE user_id=?", (user_id,)
        ).fetchone()[0] or 0.0
```

### 6.3 Production-Ready: Cost Telemetry with Budgets

Source: [reaatech/llm-cost-telemetry](https://github.com/reaatech/llm-cost-telemetry) and [prashantdudami/llm-cost-guard](https://github.com/prashantdudami/llm-cost-guard)

Key features for production:

| Feature | Implementation |
|---|---|
| **Per-user budgets** | Track cost by user_id, block when exceeded |
| **Multi-model pricing** | Built-in pricing for 40-1600+ models |
| **Pre-call estimation** | Estimate cost BEFORE the API call |
| **Streaming support** | Track tokens from stream chunks (final chunk has usage) |
| **Alert thresholds** | Warn at 50%, block at 100% of budget |
| **Background logging** | `asyncio.create_task()` to log after response sent |

```python
# Production pattern with budget enforcement
class BudgetTracker:
    def __init__(self, daily_budget_usd: float = 5.0):
        self.daily_budget = daily_budget_usd
        self.today_cost = 0.0

    async def check_budget(self, estimated_cost: float, user_id: str) -> bool:
        if self.today_cost + estimated_cost > self.daily_budget:
            await self._send_budget_alert(user_id)
            return False
        return True

    async def record_actual(self, model: str, prompt_tokens: int,
                            completion_tokens: int, user_id: str):
        cost = calculate_cost(model, prompt_tokens, completion_tokens)
        self.today_cost += cost
        # Fire-and-forget: log to DB/metrics
        asyncio.create_task(self._persist_usage(user_id, model, prompt_tokens,
                                                 completion_tokens, cost))
```

### 6.4 Streaming Cost Tracking Gotcha

For streaming responses, token usage arrives in the LAST chunk or is not available until the stream ends. The pattern:

```python
async for chunk in llm_stream:
    chunks.append(chunk)
    # Token usage NOT available here for most providers

# After stream: usage available
final_chunk = chunks[-1]
if hasattr(final_chunk, 'usage') and final_chunk.usage:
    asyncio.create_task(track_cost(final_chunk.usage))
```

### 6.5 Discord-Specific: Embed-Based Cost Display

Source: [stanley2058/js-llmcord](https://github.com/stanley2058/js-llmcord) — has `stats_for_nerds` option

```yaml
# Show token usage in responses
stats_for_nerds: false  # or { verbose: true }
```

If enabled, append a small footer to response embeds:

```python
embed.set_footer(text=f"🤖 {model} · {prompt_tokens}+{completion_tokens} tokens · ${cost:.4f}")
```

---

## 7. Architecture Recommendation for Your Bot

Based on all production patterns analyzed, here's the recommended architecture:

### 7.1 Core Flow

```python
async def handle_llm_message(interaction: discord.Interaction, prompt: str):
    user_id = str(interaction.user.id)
    channel_id = str(interaction.channel_id)

    # 1. Rate limit check (sliding window, per-user)
    if not await rate_limiter.check_and_consume(user_id):
        await interaction.response.send_message(
            "Rate limited. Try again shortly.", ephemeral=True)
        return

    # 2. Budget check (pre-call)
    est_cost = estimate_cost(model, estimated_tokens=len(prompt) // 4 + 500)
    if not await budget_tracker.can_afford(user_id, est_cost):
        await interaction.response.send_message(
            "Daily budget reached.", ephemeral=True)
        return

    # 3. Defer + send placeholder
    await interaction.response.defer()
    placeholder = await interaction.followup.send(
        embed=discord.Embed(description="⏳ Thinking...", color=ORANGE))

    # 4. Per-channel lock
    async with bot_state.get_channel_lock(channel_id):
        # 5. Stream LLM response with typing indicator
        async with interaction.channel.typing():
            full_response = ""
            last_edit = asyncio.get_event_loop().time()

            async for chunk in llm_stream:
                full_response += chunk

                # Time-throttled edit (not per-token)
                now = asyncio.get_event_loop().time()
                if now - last_edit >= 0.3:  # 3 edits/sec max
                    await placeholder.edit(
                        embed=discord.Embed(
                            description=full_response + " ⚪",
                            color=ORANGE))
                    last_edit = now

            # 6. Finalize with complete color
            await placeholder.edit(
                embed=discord.Embed(description=full_response, color=GREEN))

    # 7. Background post-processing (non-blocking)
    asyncio.create_task(track_cost(user_id, model, usage))
    asyncio.create_task(ingest_to_memory(full_response))

    return full_response
```

### 7.2 Component Summary

| Component | Recommendation | Source Reference |
|---|---|---|
| **Streaming** | Async-generator + time-throttled edit-in-place | DiscordSam, llmcord |
| **Typing** | `async with channel.typing()` wrapping the LLM call | discord.py docs |
| **Rate limiting** | Sliding window + reactive 429 cooldown | DiscordSam `rate_limiter.py` |
| **Character limits** | Embeds (4096 chars) with auto-split | DiscordSam `utils.py chunk_text()` |
| **Concurrency** | Per-channel `asyncio.Lock` | DiscordSam `state.py` |
| **Post-processing** | `asyncio.create_task()` for non-blocking background work | DiscordSam `start_post_processing_task()` |
| **Cost tracking** | SQLite + asyncio background task + budget enforcement | llm-cost-tracker, llm-cost-guard |
| **Error handling** | Token expiry fallback (delete old + send new) | DiscordSam `safe_message_edit()` |
| **Edit throttling** | 0.2-0.5s between edits, catch-up skip at >1.5s | DiscordSam `EDITS_PER_SECOND`, `CATCH_UP_WAIT_THRESHOLD` |

### 7.3 Anti-Patterns to Avoid (From Production Experience)

1. **Per-token edits** — will get you 429'd immediately
2. **No per-channel lock** — concurrent LLM calls in same channel = message editing chaos
3. **Blocking on post-processing** — user should never wait for RAG/analytics
4. **Plain text for AI responses** — wastes 2096 characters (2000 vs 4096 in embeds)
5. **No typing indicator** — user has no feedback during 2-5s LLM latency
6. **No token expiry handling** — interaction tokens expire after 15 min; without fallback, you lose the response
7. **No rate limit jitter** — thundering herd on retry causes more 429s