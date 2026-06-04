# Conversational Handler Research Report

**Date**: 2026-06-03
**Author**: Guinevere (parent research)
**Scope**: Implement conversational on_message handler for #guinevere-chat

## 1. Current on_message Flow (bot.py)

```
_on_message_listener (listen decorator, fires FIRST):
  → HardStopHandler.check(message)
  → If blocked: send neutral response, return
  → If not blocked: check_recovery (if in SAFE state)

on_message(message):
  → skip if message.author == bot.user
  → if handler.is_safe:
      → check_recovery, return (don't process commands)
  → else:
      → process_commands (slash commands)
```

**Gap**: No conversational LLM response. Only slash commands and safety guards.

## 2. Required New Flow

```
on_message(message):
  → skip if bot
  → skip if not #guinevere-chat (channel 1510914600777023659)
  → skip if slash command (starts with /)
  → skip if not Faiz (is_faiz_interaction equivalent)
  → HARD STOP check (existing handler)
  → rate limit check (Redis, 10 msg/min)
  → async with message.channel.typing()
  → recall memories (read_pipeline.recall_memories)
  → assemble system prompt (prompt_loader.assemble_system_prompt_with_memory)
  → LLM call (LLMRouter.chat, TaskType.CORE_REASONING)
  → format response (auto-split >2000 chars, max 3 chunks)
  → send response chunks
  → log metadata (structlog, no raw content)
  → track cost (CostTracker.record_cost)
  → fallback: process_commands if not handled
```

## 3. Integration Points (existing code)

| Component | File | Import | Signature |
|---|---|---|---|
| HardStopHandler | src/core/safety/hard_stop_handler.py | from src.core.safety.hard_stop_handler import HardStopHandler | `get_guard_decision(message_text)` → dict |
| DistressDetector | src/core/safety/safe_mode.py | from src.core.safety.safe_mode import DistressDetector, SafeModeController | `detect(message)` → DistressSignal |
| Mood | src/core/persona/mood_engine.py | from src.core.persona.mood_engine import Mood, evaluate_mood | `evaluate_mood(...)` → MoodTransition\|None |
| prompt_loader | src/core/memory/prompt_loader.py | from src.core.memory.prompt_loader import assemble_system_prompt_with_memory | Full signature with 9 params |
| LLMRouter | src/core/llm/llm_router.py | from src.core.llm.llm_router import LLMRouter, TaskType | `chat(messages, task_type, max_tokens)` → dict |
| recall_memories | src/core/memory/read_pipeline.py | from src.core.memory.read_pipeline import recall_memories | `recall_memories(session, query, limit, ...)` → list[dict] |
| CostTracker | src/core/services/cost_tracker.py | from src.core.services.cost_tracker import CostTracker | `record_cost(model, input_tokens, output_tokens, ...)` |
| send_alert | src/discord/notifications.py | from src.discord.notifications import send_alert | `send_alert(bot, sev, title, description)` |

## 4. Channel Configuration

```yaml
# channel-ids.yaml
guinevere-chat: 1510914600777023659
guinevere-status: 1510914604291588237
system-health: 1510914612038471720
cost-tracker: 1510914615654092900
```

## 5. Rate Limiting Design

- Redis DB0, key: `rate:conversational:{user_id}:{minute_bucket}`
- Window: sliding 1-minute buckets
- Limit: 10 messages per minute
- On limit: silent ignore (no response, no error)

## 6. Response Formatting

- Discord limit: 2000 chars per message
- Auto-split at sentence boundaries (`.`, `!`, `?`, `\n\n`)
- Max 3 chunks (6000 chars total)
- If response > 6000 chars: truncate with "...(truncated)"
- Typing indicator during LLM call

## 7. Cost Tracking

- Model: from LLM response `model` field
- Tokens: from LLM response `usage` field (prompt_tokens, completion_tokens)
- Cost rates: from CostTracker (uses Redis DB5)
- GPT-5.5: ~$0.01/1K input, $0.03/1K output (approximate)

## 8. Safety Integration

- HARD STOP: existing `HardStopHandler` singleton from cmd_safeword.py
- Distress: `DistressDetector.detect()` → if D2+, suppress persona tone
- Mood: `evaluate_mood()` → pass to prompt_loader
- PersonaSafetyPolicy authority chain: system > safety > safe-word > Faiz > persona > memory > style

## 9. Logging

- structlog only, metadata fields:
  - user_id_hash (SHA256 first 8 chars)
  - channel_id
  - response_length
  - latency_ms
  - model_used
  - memories_recalled
  - rate_limited (bool)
- NEVER log raw message content or response content

## 10. Binding Decisions

- NEW FILE: `src/discord/conversational_handler.py`
- MODIFY: `src/discord/bot.py` (wire handler into on_message)
- Redis: DB0 for rate limiting (existing DB5 for costs)
- LLM: TaskType.CORE_REASONING, max_tokens=500
- Channel: hardcoded ID 1510914600777023659 (from channel-ids.yaml)
- No new dependencies (all existing in pyproject.toml)
