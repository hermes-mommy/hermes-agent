"""Conversational on_message handler for #guinevere-chat channel.

Enables natural text-based conversation with Guinevere via Discord messages
(not just slash commands). Integrates memory recall, system prompt assembly,
LLM routing, cost tracking, distress detection, and mood evaluation.

Flow:
    1. Channel/bot/slash/Faiz guard checks.
    2. Redis-based rate limiting (10 msg/min/user).
    3. Distress detection via ``DistressDetector``.
    4. Mood evaluation (defaults to Content).
    5. System prompt assembly with memory context.
    6. Multi-turn LLM call via ``HermesSessionAdapter`` with conversation history.
    7. Response formatting and Discord chunked send.
    8. Cost tracking via ``CostTracker``.
    9. Auto-store conversation to episodic memory (``write_pipeline.store_episode``).
   10. Structured logging via structlog.

Channel:
    #guinevere-chat (ID: 1510914600777023659)
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any, Final

import structlog

logger: Final = structlog.get_logger()


# ── Constants ────────────────────────────────────────────────────────────────

GUINEVERE_CHAT_CHANNEL_ID: Final[int] = 1_510_914_600_777_023_659
"""Discord channel ID for #guinevere-chat."""

RATE_LIMIT_MAX: Final[int] = 10
"""Maximum messages per minute per user."""

RATE_LIMIT_WINDOW: Final[int] = 60
"""Rate limit window in seconds."""

DISCORD_MAX_CHARS: Final[int] = 2000
"""Discord message character limit."""

MAX_CHUNKS: Final[int] = 3
"""Maximum number of response chunks to send."""

MAX_TOTAL_CHARS: Final[int] = DISCORD_MAX_CHARS * MAX_CHUNKS
"""Maximum total characters across all chunks (6000)."""

LLM_MAX_TOKENS: Final[int] = 2000
"""Maximum tokens for conversational LLM responses.

DeepSeek V4 Flash allocates a portion of max_tokens for internal reasoning
tokens (``completion_tokens_details.reasoning_tokens``), so this must be
generous enough that actual ``content`` is non-empty after reasoning.
"""

FALLBACK_MESSAGE: Final[str] = (
    "I'm having trouble thinking right now, sayang. "
    "Try again in a moment? \U0001f49b"
)
"""Graceful fallback when LLM call fails. Unicode: \U0001f49b = 💛."""

ANTI_HALLUCINATION_GUARD: Final[str] = (
    "\n\n[MEMORY STATUS: No relevant memories found for this query. "
    "Do NOT fabricate or guess past preferences, conversations, or facts. "
    "If asked about past conversations or preferences, say: "
    "'Mommy belum punya catatan tentang itu, Darling. "
    "Ceritakan ke Mommy sekarang.']"
)
"""Injected into system prompt when recall returns empty to prevent LLM hallucination."""


# ── Module-Level Singletons ─────────────────────────────────────────────────

_router: Any = None
"""Lazy-initialised ``LLMRouter`` singleton."""

_cost_tracker: Any = None
"""Lazy-initialised ``CostTracker`` singleton."""

_rate_limit_redis: Any = None
"""Lazy-initialised async Redis client for rate limiting (DB0)."""

_embedding_service: Any = None
"""Lazy-initialised ``EmbeddingService`` singleton for memory recall."""

_memory_bridge: Any = None
"""Lazy-initialised ``HermesMemoryBridge`` singleton for memory bridge."""


def _get_router() -> Any:
    """Return the LLMRouter singleton, creating lazily on first call.

    Returns:
        The module-level ``LLMRouter`` instance.
    """
    global _router
    if _router is None:
        from src.core.services.llm_router import LLMRouter

        _router = LLMRouter()
    return _router


def _get_cost_tracker() -> Any:
    """Return the CostTracker singleton, creating lazily on first call.

    Returns:
        The module-level ``CostTracker`` instance.
    """
    global _cost_tracker
    if _cost_tracker is None:
        from src.core.services.cost_tracker import CostTracker

        _cost_tracker = CostTracker()
    return _cost_tracker


def _get_embedding_service() -> Any:
    """Return the EmbeddingService singleton, creating lazily on first call.

    Returns:
        The module-level ``EmbeddingService`` instance.
    """
    global _embedding_service
    if _embedding_service is None:
        from src.memory.embeddings import EmbeddingService

        _embedding_service = EmbeddingService()
    return _embedding_service


def _get_or_create_bridge(session_factory: Any, embedding_svc: Any) -> Any:
    """Return or create HermesMemoryBridge with the given session factory.

    Args:
        session_factory: Async session maker for DB operations.
        embedding_svc: ``EmbeddingService`` instance for vector search.

    Returns:
        The module-level ``HermesMemoryBridge`` singleton.
    """
    global _memory_bridge
    if _memory_bridge is None:
        # DEPRECATED (Phase 3): import kept for backward compatibility.
        # New code should use plugins.memory.guinevere_memory.GuinevereMemoryProvider.
        # This import triggers a DeprecationWarning from memory_bridge.py.
        from src.hermes.memory_bridge import HermesMemoryBridge  # noqa: WPS301

        _memory_bridge = HermesMemoryBridge(
            session_factory=session_factory,
            embedding_service=embedding_svc,
        )
    return _memory_bridge


def _get_rate_limit_redis() -> Any:
    """Return the async Redis client singleton for rate limiting.

    Connects to DB0 (separate from cost tracker's DB5).
    Authenticates with ``REDIS_PASSWORD`` when present (production).

    Returns:
        The module-level async ``Redis`` instance.
    """
    global _rate_limit_redis
    if _rate_limit_redis is None:
        import os
        import redis.asyncio as aioredis

        _rate_limit_redis = aioredis.Redis(
            host="localhost",
            port=6380,
            db=0,
            username="guinevere_core",
            password=os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
    return _rate_limit_redis


def _get_hermes() -> Any:
    """Return the shared HermesSessionAdapter singleton from ``src.hermes``.

    Delegates to ``get_adapter()`` so that slash commands (/new, /history)
    and the conversational handler share the **same** adapter instance,
    Redis connection, agent cache, and metadata store.

    Returns:
        The shared HermesSessionAdapter instance.
    """
    from src.hermes import get_adapter

    return get_adapter()


# ── Rate Limiting ────────────────────────────────────────────────────────────


async def _is_rate_limited(user_id: int) -> bool:
    """Check whether *user_id* has exceeded the chat rate limit.

    Uses Redis INCR + EXPIRE with a per-minute bucket key.

    Key pattern: ``rate:chat:{user_id}:{minute_bucket}``

    Args:
        user_id: Discord user snowflake ID.

    Returns:
        ``True`` if rate-limited (caller should absorb silently),
        ``False`` if the message may proceed.
    """
    try:
        r = _get_rate_limit_redis()
        minute_bucket = int(time.time()) // RATE_LIMIT_WINDOW
        key = f"rate:chat:{user_id}:{minute_bucket}"
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, RATE_LIMIT_WINDOW)
        return count > RATE_LIMIT_MAX
    except (ConnectionError, OSError) as exc:
        logger.warning(
            "rate_limit_redis_error",
            user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:8],
            error=str(exc),
        )
        return False
    except Exception as exc:
        # Catches redis.RedisError and any other async Redis failures
        logger.warning(
            "rate_limit_redis_error",
            user_id_hash=hashlib.sha256(str(user_id).encode()).hexdigest()[:8],
            error=str(exc),
            error_type=type(exc).__name__,
        )
        return False


# ── Response Splitting ──────────────────────────────────────────────────────

# Sentence-boundary pattern: splits after ``.``, ``!``, ``?``, or double
# newline while keeping the delimiter attached to the preceding segment.
_SENTENCE_BOUNDARY: Final[re.Pattern[str]] = re.compile(
    r"(?<=[.!?])\s+|\n\n"
)


def _split_response(text: str) -> list[str]:
    """Split *text* into Discord-sendable chunks respecting sentence boundaries.

    Strategy:
        1. Split on sentence boundaries (``. ``, ``! ``, ``? ``, ``\\n\\n``).
        2. Pack segments into chunks up to ``DISCORD_MAX_CHARS`` (2000).
        3. Cap at ``MAX_CHUNKS`` (3) chunks / 6000 chars total.
        4. Truncate the final chunk with ``...(truncated)`` if needed.

    Args:
        text: The full LLM response text.

    Returns:
        A list of message strings, each within the Discord character limit.
    """
    if len(text) <= DISCORD_MAX_CHARS:
        return [text]

    segments = _SENTENCE_BOUNDARY.split(text)

    chunks: list[str] = []
    current = ""

    for segment in segments:
        candidate = (current + " " + segment).strip() if current else segment

        if len(candidate) <= DISCORD_MAX_CHARS:
            current = candidate
        else:
            # Flush current chunk if non-empty
            if current:
                chunks.append(current)
                if len(chunks) >= MAX_CHUNKS:
                    break
            # Single segment exceeding limit — hard-split it
            if len(segment) > DISCORD_MAX_CHARS:
                remaining = segment
                while remaining and len(chunks) < MAX_CHUNKS:
                    chunks.append(remaining[:DISCORD_MAX_CHARS])
                    remaining = remaining[DISCORD_MAX_CHARS:]
                current = ""
            else:
                current = segment

    if current and len(chunks) < MAX_CHUNKS:
        chunks.append(current)

    # Truncate last chunk if total exceeds maximum
    if chunks and sum(len(c) for c in chunks) > MAX_TOTAL_CHARS:
        last = chunks[-1]
        if len(last) > 100:
            chunks[-1] = last[:90] + "...(truncated)"
        else:
            chunks[-1] = last + "...(truncated)"

    return chunks


# ── Main Handler ─────────────────────────────────────────────────────────────


async def handle_conversation(bot: Any, message: Any) -> bool:
    """Handle conversational messages in #guinevere-chat.

    Orchestrates the full conversational flow: guard checks, rate limiting,
    distress detection, system prompt assembly, LLM call, response delivery,
    cost tracking, and structured logging.

    Returns ``True`` if the message was handled (even if silently absorbed),
    ``False`` to pass through to ``process_commands``.

    Args:
        bot: The ``GuinevereBot`` instance (used for context, not modified).
        message: The ``discord.Message`` to evaluate and respond to.

    Returns:
        ``True`` if the message was handled, ``False`` to pass through.
    """
    start_time = time.time()

    # ── Step 1: Channel check ──────────────────────────────────────────────
    channel = message.channel if message is not None else None
    if channel is None or channel.id != GUINEVERE_CHAT_CHANNEL_ID:
        return False

    # ── Step 2: Bot check ──────────────────────────────────────────────────
    author = message.author if message is not None else None
    if author is None or author.bot:
        return False

    # ── Step 3: Slash command check ────────────────────────────────────────
    content: str = message.content if message is not None else ""
    if not content or content.startswith("/"):
        return False

    # ── Step 4: Faiz check (guild owner) ───────────────────────────────────
    guild = message.guild if message is not None else None
    if guild is None or guild.owner_id != author.id:
        return False

    # ── Step 5: Rate limiting ──────────────────────────────────────────────
    user_id: int = int(author.id)
    if await _is_rate_limited(user_id):
        return True  # Absorbed silently

    # ── Step 6: Typing indicator ───────────────────────────────────────────
    typing_ctx = channel.typing if channel is not None else None
    if typing_ctx is not None:
        async with typing_ctx():
            return await _process_and_respond(
                bot, author, channel, content, start_time,
            )
    # Fallback: no typing context available (shouldn't happen in practice)
    return await _process_and_respond(
        bot, author, channel, content, start_time,
    )


async def _process_and_respond(
    bot: Any,
    author: Any,
    channel: Any,
    content: str,
    start_time: float,
) -> bool:
    """Core conversational flow after guard checks pass.

    Handles distress detection, memory recall + prompt assembly, LLM call,
    response formatting, cost tracking, and logging.

    Args:
        bot: The ``GuinevereBot`` instance (provides session factory).
        author: The ``discord.Member`` who sent the message.
        channel: The ``discord.TextChannel`` to send responses to.
        content: The cleaned message content string.
        start_time: ``time.time()`` timestamp for latency measurement.

    Returns:
        ``True`` — the message was always handled (even on error).
    """
    # ── Step 7: Distress detection ─────────────────────────────────────────
    from src.persona.safe_mode import DistressDetector, SafeModeController

    detector = DistressDetector()
    controller = SafeModeController()

    try:
        signal = detector.detect(content)
        safe_mode_activated = controller.evaluate(signal)
        if safe_mode_activated:
            logger.warning(
                "distress_safe_mode_activated",
                level=signal.detected_level.name,
                confidence=signal.confidence,
            )
    except Exception as exc:
        logger.warning(
            "distress_detection_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        # Graceful degradation — create a neutral signal
        from src.persona.safe_mode import DistressLevel, DistressSignal
        from datetime import datetime, timezone

        signal = DistressSignal(
            text="",
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=datetime.now(tz=timezone.utc),
        )
        safe_mode_activated = False

    # ── Step 8: Mood evaluation ────────────────────────────────────────────
    from src.persona.mood_engine import Mood

    # Default to Content for conversational context
    current_mood: str = Mood.CONTENT.value

    # ── Step 9: System prompt assembly with memory recall (Phase 2 bridge) ──
    from src.core.services.prompt_loader import (
        get_system_prompt_with_context,
    )

    try:
        session_factory_fn = getattr(bot, "get_session_factory", None)
        session_factory = session_factory_fn() if session_factory_fn else None

        if session_factory is not None:
            embedding_svc = _get_embedding_service()
            bridge = _get_or_create_bridge(session_factory, embedding_svc)

            memories = await bridge.recall_for_context(
                query=content,
                safe_mode=safe_mode_activated,
                principal="guinevere_core",
                limit=5,
                token_budget=800,
            )

            system_prompt = get_system_prompt_with_context(
                memories=memories if memories else None,
                mood=current_mood,
                token_budget=800,
            )
            # Anti-hallucination: prevent LLM from fabricating memories
            if not memories:
                system_prompt += ANTI_HALLUCINATION_GUARD
            logger.info(
                "memory_recall_integrated",
                query_length=len(content),
                safe_mode=safe_mode_activated,
                memories_count=len(memories),
            )
        else:
            system_prompt = get_system_prompt_with_context(
                memories=None,
                mood=current_mood,
            )
            system_prompt += ANTI_HALLUCINATION_GUARD
            logger.info("memory_recall_skipped", reason="no_session_factory")
    except Exception as exc:
        logger.warning(
            "memory_recall_fallback",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        try:
            system_prompt = get_system_prompt_with_context(
                memories=None,
                mood=current_mood,
            )
            system_prompt += ANTI_HALLUCINATION_GUARD
        except (FileNotFoundError, ValueError) as inner_exc:
            logger.error(
                "system_prompt_assembly_error",
                error=str(inner_exc),
                error_type=type(inner_exc).__name__,
            )
            await channel.send(FALLBACK_MESSAGE)
            return True

    # ── Step 10: Hermes multi-turn call ───────────────────────────────────
    hermes = _get_hermes()

    try:
        response_text: str = await hermes.send_message(
            user_id=str(author.id),
            content=content,
            system_prompt=system_prompt,
        )
    except Exception as exc:
        logger.error(
            "hermes_call_failed",
            error=str(exc),
            error_type=type(exc).__name__,
        )
        await channel.send(FALLBACK_MESSAGE)
        return True

    if not response_text:
        logger.warning("hermes_empty_response")
        await channel.send(FALLBACK_MESSAGE)
        return True

    # Extract metadata for cost tracking
    hermes_metadata: dict[str, Any] = hermes.get_last_metadata(str(author.id))
    prompt_tokens: int = int(hermes_metadata.get("input_tokens", 0))
    completion_tokens: int = int(hermes_metadata.get("output_tokens", 0))
    model_used: str = str(hermes_metadata.get("model", "unknown"))

    # ── Step 11: Format and send response ──────────────────────────────────
    chunks = _split_response(response_text)
    for chunk in chunks:
        await channel.send(chunk)

    # ── Step 11b: Phase 2 Shadow — fire-and-forget to Hermes for comparison ──
    # NEVER sends Hermes response to Discord — logs comparison only.
    try:
        shadow = getattr(bot, "shadow_pipeline", None)
        if shadow is not None and shadow.enabled:
            asyncio.create_task(
                shadow.shadow_forward(
                    content, response_text, str(author.id), str(channel.id),
                )
            )
    except Exception as shadow_exc:
        logger.debug(
            "shadow_forward_skipped",
            error=str(shadow_exc),
            error_type=type(shadow_exc).__name__,
        )

    # ── Step 12: Cost tracking ─────────────────────────────────────────────
    try:
        estimated_cost: float = float(hermes_metadata.get("estimated_cost_usd", 0.0))
        tracker = _get_cost_tracker()
        if estimated_cost > 0:
            # Use Hermes-reported cost directly
            await asyncio.to_thread(
                tracker.record_cost,
                model=model_used,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_per_1k_input=0.0,
                cost_per_1k_output=0.0,
            )
        else:
            # Fallback: estimate from model config
            from src.core.services.llm_router import MODELS, TaskType
            config = MODELS[TaskType.CORE_REASONING]
            await asyncio.to_thread(
                tracker.record_cost,
                model=model_used,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
                cost_per_1k_input=config.cost_per_1k_input,
                cost_per_1k_output=config.cost_per_1k_output,
            )
    except Exception as exc:
        logger.warning(
            "cost_tracking_error",
            error=str(exc),
            error_type=type(exc).__name__,
            model_used=model_used,
        )

    user_id_hash = hashlib.sha256(
        str(author.id).encode()
    ).hexdigest()[:8]

    # ── Step 12b: Auto-store conversation to memory (Phase 2 bridge) ─────────
    try:
        session_factory_fn = getattr(bot, "get_session_factory", None)
        session_factory = session_factory_fn() if session_factory_fn else None

        if session_factory is not None:
            embedding_svc = _get_embedding_service()
            bridge = _get_or_create_bridge(session_factory, embedding_svc)

            asyncio.create_task(
                bridge.store_conversation(
                    user_message=content,
                    assistant_response=response_text,
                    user_id_hash=user_id_hash,
                    safe_mode=safe_mode_activated,
                )
            )
            logger.info(
                "memory_auto_store_queued",
                content_length=len(content) + len(response_text),
            )
        else:
            logger.info("memory_auto_store_skipped", reason="no_session_factory")
    except Exception as exc:
        logger.warning(
            "memory_auto_store_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )

    # ── Step 13: Structured logging (metadata only, no content) ────────────

    logger.info(
        "conversational_response",
        user_id_hash=user_id_hash,
        channel_id=getattr(channel, "id", 0),
        response_length=len(response_text),
        latency_ms=round((time.time() - start_time) * 1000, 1),
        model_used=model_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        chunks_sent=len(chunks),
        distress_level=signal.detected_level.name,
        safe_mode_active=safe_mode_activated,
    )

    return True
