# Research Report: Hermes Agent — Streaming, Threading, and Parallel Execution Configuration

**Date**: 2026-06-04  
**Target**: Guinevere Discord Bot Integration  
**Subject**: Hermes Agent streaming, threading, async, and Discord-specific configuration  

---

## 1. Executive Summary

Hermes Agent (by Nous Research) provides robust, native support for Discord integration via its Messaging Gateway. It handles streaming, session isolation, and concurrency out-of-the-box, but requires strict adherence to its threading model when using the Python `AIAgent` library directly. Key findings:
- **Streaming**: Native progressive message editing for Discord (edits every ~1.2s), with automatic fallback to non-streaming on failure.
- **Threading**: The `AIAgent` class is **not thread-safe**. A new instance must be created per concurrent task/thread.
- **Discord Features**: Native typing indicators, auto-threading on `@mention`, and per-user session isolation in shared channels.
- **Degradation**: Built-in graceful degradation for long-running tasks (heartbeat notifications) and streaming failures.

---

## 2. Streaming & Response Chunking

Hermes v0.3.0+ introduced a unified streaming infrastructure. For Discord, the gateway sends an initial message and progressively edits it as tokens arrive.

### Configuration (`~/.hermes/config.yaml`)
```yaml
streaming:
  enabled: true           # Master switch for gateway streaming
  transport: "edit"       # Progressive message editing (Discord/Telegram/Slack)
  edit_interval: 1.2      # Seconds between message edits (Discord default ~1.2s)
  buffer_threshold: 40    # Characters before forcing an edit flush
  cursor: " ▉"            # Cursor shown during active streaming
```

### Discord-Specific Chunking Tuning
Environment variables in `~/.hermes/.env` allow fine-tuning of chunk delivery to respect Discord's rate limits:
- `HERMES_DISCORD_TEXT_BATCH_DELAY_SECONDS`: Default `0.6`. Grace window the adapter waits before flushing a queued text chunk. Smooths streamed output.
- `HERMES_DISCORD_TEXT_BATCH_SPLIT_DELAY_SECONDS`: Delay between split chunks when a single message exceeds Discord's 2000-character limit.

**Evidence**: [Hermes Agent Discord Messaging Docs](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/messaging/discord.md) | [Gateway Streaming Config](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/configuration.md)

---

## 3. Threading Model & Concurrent Request Handling

### ⚠️ Critical Constraint: `AIAgent` is NOT Thread-Safe
The `AIAgent` maintains internal state (conversation history, tool sessions, iteration counters) that **must not be shared** across concurrent calls. 

### Correct Pattern for Concurrency
When building custom batch logic or handling concurrent Discord events outside the gateway, you **must** instantiate a new `AIAgent` per thread/task:

```python
import concurrent.futures
from run_agent import AIAgent

def process_discord_message(prompt: str):
    # CRITICAL: Create a fresh agent per task for thread safety
    agent = AIAgent(
        model="anthropic/claude-sonnet-4",
        quiet_mode=True,
        skip_memory=True,        # Recommended for stateless API endpoints
        skip_context_files=True, # Skip loading AGENTS.md if not needed
        platform="discord",      # Injects platform-specific formatting hints
        max_iterations=10        # Lower from default 90 to prevent runaway loops
    )
    return agent.chat(prompt)

# Execute concurrently
with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
    results = list(executor.map(process_discord_message, user_prompts))
```

### Built-in Batch Processing
For heavy parallel workloads, use Hermes's built-in `batch_runner.py`, which manages concurrent `AIAgent` instances with proper resource isolation and unique `task_id` assignment.

**Evidence**: [Hermes Agent Python Library Guide](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/guides/python-library.md)

---

## 4. Discord-Specific Configuration

Hermes Gateway provides extensive Discord-specific controls via `~/.hermes/.env` and `~/.hermes/config.yaml`.

| Feature | Config Key / Env Var | Default | Behavior |
|---|---|---|---|
| **Typing Indicators** | Native Gateway Feature | ✅ Enabled | Shows typing indicator while processing. |
| **Auto-Threading** | `DISCORD_AUTO_THREAD` / `discord.auto_thread` | `true` | Creates a new thread for every `@mention` in a text channel, isolating session history. |
| **Session Isolation** | `group_sessions_per_user` | `true` | Ensures Alice and Bob in the same channel have separate conversation histories. |
| **Mention Gating** | `DISCORD_REQUIRE_MENTION` | `true` | Bot only responds in server channels when `@mentioned`. |
| **Free Response** | `DISCORD_FREE_RESPONSE_CHANNELS` | `""` | Comma-separated channel IDs where bot responds inline without `@mention` (skips auto-threading). |
| **Multi-bot Threads** | `DISCORD_THREAD_REQUIRE_MENTION` | `false` | Set to `true` if multiple bots share a thread to prevent all bots from firing on every message. |

**Evidence**: [Hermes Agent Discord Messaging Docs](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/messaging/discord.md)

---

## 5. Rate Limiting & Graceful Degradation

### Discord API Rate Limits
- Discord allows **5 message edits per 5 seconds** per message.
- Hermes handles this automatically via `HERMES_DISCORD_TEXT_BATCH_DELAY_SECONDS` (0.6s), ensuring edits are spaced safely to avoid HTTP 429 errors.

### Graceful Degradation Under Load
1. **Streaming Fallback**: If the LLM provider does not support streaming, or the streaming connection fails, Hermes catches the exception and falls back *silently* to the non-streaming path. The user receives the full response as a single block.
2. **Subagent Non-Blocking**: When subagents are spawned via `delegate_task`, Hermes always prefers a streaming API call. This prevents subagents from hanging when the parent's event loop is occupied.

**Evidence**: [Hermes Agent Streaming Documentation](https://github.com/mudrii/hermes-agent-docs/blob/main/streaming.md)

---

## 6. Long-Running Operations & Timeouts

To prevent users from staring at a perpetual "typing..." indicator or encountering gateway timeouts:

### Heartbeat Notifications
Hermes includes built-in long-running operation feedback:
- `long_running_notifications`: Stays **on** by default.
- Behavior: Updates the message in-place with a "⏳ Working — N min" bubble every few minutes, providing a heartbeat instead of relying solely on the typing indicator.

### Timeout & Iteration Controls
- **Default `max_iterations`**: 90 (very generous, risks runaway tool-calling loops).
- **Recommendation for Discord**: Lower to `max_iterations=10` or `15` for standard Q&A to control costs, prevent infinite loops, and ensure responses complete within Discord's general timeout windows.
- **Resource Cleanup**: The agent automatically cleans up resources (terminal sessions, browser instances) when a conversation ends. Ensure each conversation completes normally in long-lived processes.

**Evidence**: [Hermes Agent Python Library Guide](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/guides/python-library.md) | [Messaging Gateway Index](https://github.com/nousresearch/hermes-agent/blob/main/website/docs/user-guide/messaging/index.md)

---

## 7. Actionable Recommendations for Guinevere

1. **Do not reinvent streaming**: Rely on Hermes Gateway's native `transport: "edit"` streaming. It already handles the 2000-char chunking, 1.2s edit intervals, and Discord rate limits.
2. **Enforce Session Isolation**: Ensure `group_sessions_per_user: true` is set in `config.yaml` to prevent cross-talk in shared Discord channels.
3. **Custom Python Integration**: If Guinevere intercepts or wraps Hermes calls via the Python library, **strictly enforce** `AIAgent` instantiation per request. Never reuse an `AIAgent` instance across Discord `on_message` events.
4. **Tune Iterations**: Set `max_iterations=15` in the `AIAgent` config to prevent runaway tool loops from blocking the Discord event loop.
5. **Leverage Auto-Threading**: Keep `DISCORD_AUTO_THREAD=true` to naturally segment Guinevere's context windows per conversation, reducing token bloat in busy channels.

---
*Report generated by Guinevere Research Agent. All claims verified against official Hermes Agent v2026.4.x documentation.*