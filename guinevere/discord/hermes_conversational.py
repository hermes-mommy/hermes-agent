"""Hermes-native conversational handler for multi-channel support.

Replaces the previous ``conversational_handler.py`` pipeline with a
Hermes AIAgent-native architecture. All custom hooks — distress detection,
mood evaluation, memory recall, cost tracking, auto-store, and shadow
forward — are preserved as independent processing stages around the
Hermes LLM invocation.

Architecture::

    Incoming Message
      -> Channel check (conversational_channels frozenset)
      -> Bot check (ignore bot messages)
      -> Slash command check (skip if slash)
      -> Faiz check (guild owner only)
      -> Rate limit (Redis DB0, 10/min/user)
      -> Typing indicator
      -> Distress detection (custom hook — preserved)
      -> Mood system (guinevere_safety plugin state)
      -> Affect-driven tone (AffectVector -> system prompt modifier)
      -> System prompt construction (SOUL.md + memory context)
      -> Memory recall (HermesMemoryBridge)
      -> Hermes AIAgent invocation (replaces direct LLM call)
      -> Response chunking (Hermes streaming with manual fallback)
      -> Cost tracking (custom hook on post_response)
      -> Auto-store (memory_bridge.store_conversation)
      -> Shadow forward (fire-and-forget via asyncio.create_task)
      -> Structured logging

B5 Loop-Driven Behavior:
    ThoughtStream affect → tone: AffectVector dimensions (valence, arousal,
    curiosity, serenity) modify the system prompt tone before Hermes call.

    High-confidence thoughts → Discord: When ThoughtStream produces a
    COGNITION or PLANNING thought with confidence > 0.8, ActionExecutor
    routes it as a Discord message via ``process_thought_for_discord()``.

Channels:
    Conversational mode is enabled for channels listed in
    ``CONVERSATIONAL_CHANNELS`` (default: general + commands_hq).
    Channel IDs are resolved via ``ChannelConfig`` — no hardcoded IDs.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import time
from typing import Any, Final

import structlog

logger: Final = structlog.get_logger()


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Default conversational channels — resolved from ChannelConfig at runtime.
# These are the ChannelConfig *key names*, not snowflake IDs.
CONVERSATIONAL_CHANNEL_KEYS: Final[frozenset[str]] = frozenset({
    "general",
    "commands_hq",
})
"""Channel config keys where conversational mode is enabled by default."""

# Backward-compat alias — deprecated; prefer CONVERSATIONAL_CHANNEL_KEYS.
# No hardcoded snowflake IDs — resolved at runtime via ChannelConfig.
GUINEVERE_CHAT_CHANNEL_ID: Final[int] = 0
"""Deprecated. Use ChannelConfig to resolve channel IDs at runtime."""

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

FALLBACK_MESSAGE: Final[str] = (
    "I'm having trouble thinking right now, sayang. "
    "Try again in a moment? 💛"
)

ANTI_HALLUCINATION_GUARD: Final[str] = (
    "\n\n[MEMORY STATUS: No relevant memories found for this query. "
    "Do NOT fabricate or guess past preferences, conversations, or facts. "
    "If asked about past conversations or preferences, say: "
    "'Mommy belum punya catatan tentang itu, Darling. "
    "Ceritakan ke Mommy sekarang.']"
)
"""Injected into system prompt when recall returns empty to prevent hallucination."""


# ---------------------------------------------------------------------------
# Module-Level Singletons
# ---------------------------------------------------------------------------

_cost_tracker: Any = None
"""Lazy-initialised ``CostTracker`` singleton."""

_rate_limit_redis: Any = None
"""Lazy-initialised async Redis client for rate limiting (DB0)."""

_embedding_service: Any = None
"""Lazy-initialised ``EmbeddingService`` singleton for memory recall."""

_memory_bridge: Any = None
"""Lazy-initialised ``HermesMemoryBridge`` singleton for memory bridge."""

_conversational_channel_ids: frozenset[int] | None = None
"""Resolved set of channel snowflake IDs where conversational mode is active."""

_action_executor: Any = None
"""Lazy-initialised ``ActionExecutor`` singleton for loop-driven Discord."""

_bot_ref: Any = None
"""Weak reference to the bot instance for Discord send callbacks."""


def set_action_executor(executor: Any) -> None:
    """Inject an ActionExecutor instance for loop-driven Discord behavior.

    Called during startup (e.g. from _entrypoint.py) to enable the
    ThoughtStream → ActionExecutor → Discord pipeline.

    Args:
        executor: An ``ActionExecutor`` instance from
            ``guinevere.consciousness.action_executor``.
    """
    global _action_executor
    _action_executor = executor
    logger.info("action_executor.injected", executor_type=type(executor).__name__)


def set_bot_reference(bot: Any) -> None:
    """Store a reference to the bot instance for send callbacks.

    Args:
        bot: The ``GuinevereBot`` instance.
    """
    global _bot_ref
    _bot_ref = bot


def resolve_conversational_channels(channel_config: Any) -> frozenset[int]:
    """Build the frozenset of channel snowflake IDs for conversational mode.

    Reads channel IDs from *channel_config* for each key in
    ``CONVERSATIONAL_CHANNEL_KEYS``.

    Args:
        channel_config: A ``ChannelConfig`` instance (duck-typed).

    Returns:
        A frozenset of Discord channel snowflake IDs.
    """
    ids: set[int] = set()
    for key in CONVERSATIONAL_CHANNEL_KEYS:
        ch_id = getattr(channel_config, key, None)
        if isinstance(ch_id, int):
            ids.add(ch_id)
    return frozenset(ids)


# ---------------------------------------------------------------------------
# B5 Loop-Driven Behavior — Affect → Tone + Thought → Discord
# ---------------------------------------------------------------------------


def compute_affect_tone(affect: Any) -> str:
    """Derive a tone directive from the AffectVector for system prompt injection.

    Maps affect dimensions to natural-language tone guidance:
    - valence → positivity/negativity
    - arousal → energy level
    - curiosity → exploration enthusiasm
    - serenity → calmness
    - confidence → assertiveness

    Args:
        affect: An ``AffectVector`` instance (duck-typed with valence, arousal,
            curiosity, serenity, confidence attributes).

    Returns:
        A short tone directive string suitable for injection into the system
        prompt.  Returns empty string if affect is None.
    """
    if affect is None:
        return ""

    parts: list[str] = []

    valence = getattr(affect, "valence", 0.5)
    if valence > 0.6:
        parts.append("warm and positive")
    elif valence < 0.4:
        parts.append("gentle and empathetic")

    arousal = getattr(affect, "arousal", 0.5)
    if arousal > 0.7:
        parts.append("energetic")
    elif arousal < 0.3:
        parts.append("calm and measured")

    curiosity = getattr(affect, "curiosity", 0.5)
    if curiosity > 0.7:
        parts.append("curious and exploratory")

    serenity = getattr(affect, "serenity", 0.5)
    if serenity > 0.7:
        parts.append("serene and composed")

    confidence = getattr(affect, "confidence", 0.5)
    if confidence > 0.7:
        parts.append("confident")
    elif confidence < 0.3:
        parts.append("humble and tentative")

    if not parts:
        return ""

    return "Tone: " + ", ".join(parts) + "."


def create_discord_send_callback(bot: Any = None) -> Any:
    """Create an async callback for ActionExecutor to send Discord messages.

    The callback resolves the target channel via ChannelConfig and sends
    the message content.  Returns True on success, False on failure.

    Args:
        bot: Optional bot instance.  Falls back to module-level ``_bot_ref``.

    Returns:
        An async callable ``(channel_key: str, content: str) -> bool``.
    """
    effective_bot = bot or _bot_ref

    async def _send_to_discord(channel_key: str, content: str) -> bool:
        """Send content to a Discord channel resolved by ChannelConfig key.

        Args:
            channel_key: ChannelConfig attribute name (e.g. "general").
            content: Message text to send.

        Returns:
            True if sent successfully, False otherwise.
        """
        if effective_bot is None:
            logger.warning(
                "discord_send_callback.no_bot_ref",
                channel_key=channel_key,
            )
            return False

        cfg = getattr(effective_bot, "channel_config", None)
        if cfg is None:
            logger.warning(
                "discord_send_callback.no_channel_config",
                channel_key=channel_key,
            )
            return False

        channel_id = getattr(cfg, channel_key, None)
        if not isinstance(channel_id, int):
            logger.warning(
                "discord_send_callback.invalid_channel_key",
                channel_key=channel_key,
            )
            return False

        # Get the channel object from the bot's guild cache.
        channel = None
        for guild in effective_bot.guilds:
            channel = guild.get_channel(channel_id)
            if channel is not None:
                break

        if channel is None:
            logger.warning(
                "discord_send_callback.channel_not_found",
                channel_key=channel_key,
                channel_id=channel_id,
            )
            return False

        try:
            await channel.send(content)
            logger.info(
                "discord_send_callback.sent",
                channel_key=channel_key,
                channel_id=channel_id,
                content_length=len(content),
            )
            return True
        except Exception as exc:
            logger.error(
                "discord_send_callback.send_failed",
                channel_key=channel_key,
                channel_id=channel_id,
                error=str(exc),
                error_type=type(exc).__name__,
            )
            return False

    return _send_to_discord


async def process_thought_for_discord(
    thought: Any,
    action_executor: Any = None,
    channel_config: Any = None,
) -> bool:
    """Evaluate a thought and route it to Discord if high-confidence.

    This is the B5 integration point: ThoughtStream produces a Thought,
    this function evaluates it via ActionExecutor and sends it to Discord
    if it meets the criteria (COGNITION/PLANNING type, confidence > 0.8,
    channel in conversational_channels).

    Args:
        thought: A ``Thought`` instance from ThoughtStream.
        action_executor: Optional ``ActionExecutor`` instance.  Falls back
            to module-level ``_action_executor``.
        channel_config: Optional ``ChannelConfig`` for target resolution.

    Returns:
        True if the thought was acted upon and sent to Discord.
    """
    executor = action_executor or _action_executor
    if executor is None:
        logger.debug(
            "process_thought_for_discord.no_executor",
            thought_type=getattr(thought, "type", None),
        )
        return False

    # Evaluate the thought — ActionExecutor checks confidence > 0.8
    # and type in {COGNITION, PLANNING}.
    action_spec = executor.evaluate_thought(thought)
    if action_spec is None:
        return False

    # For discord_message actions, ensure we have a send callback wired.
    if action_spec.action_type == "discord_message":
        # Check if executor already has a send callback (preferred path).
        send_callback = getattr(executor, "_discord_send_callback", None)
        if send_callback is None:
            # Wire one dynamically if not already set.
            cfg = channel_config or _bot_ref
            if cfg is not None:
                send_callback = create_discord_send_callback(cfg)
            else:
                logger.warning(
                    "process_thought_for_discord.no_send_callback",
                    thought_type=getattr(thought, "type", None),
                )

        if send_callback is not None:
            target_channel = action_spec.payload.get("channel", "general")
            content = action_spec.payload.get("content", thought.content)
            sent = await send_callback(target_channel, content)
            if sent:
                logger.info(
                    "process_thought_for_discord.sent",
                    thought_type=getattr(thought, "type", "unknown"),
                    confidence=thought.confidence,
                    target_channel=target_channel,
                )
                return True
            logger.warning(
                "process_thought_for_discord.send_failed",
                thought_type=getattr(thought, "type", "unknown"),
                target_channel=target_channel,
            )
            return False

    # Non-discord actions: delegate to executor normally.
    result = await executor.execute(action_spec)
    acted = result.get("status") not in ("error",)
    if acted:
        logger.info(
            "process_thought_for_discord.executed",
            thought_type=getattr(thought, "type", "unknown"),
            action_type=action_spec.action_type,
            status=result.get("status"),
        )
    return acted


def _get_cost_tracker() -> Any:
    """Return the CostTracker singleton, creating lazily on first call."""
    global _cost_tracker
    if _cost_tracker is None:
        from guinevere.core.services.cost_tracker import CostTracker

        _cost_tracker = CostTracker()
    return _cost_tracker


def _get_embedding_service() -> Any:
    """Return the EmbeddingService singleton, creating lazily on first call."""
    global _embedding_service
    if _embedding_service is None:
        from guinevere.memory.embeddings import EmbeddingService

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
        from guinevere.hermes._memory_bridge import HermesMemoryBridge

        _memory_bridge = HermesMemoryBridge(
            session_factory=session_factory,
            embedding_service=embedding_svc,
        )
    return _memory_bridge


def _get_rate_limit_redis() -> Any:
    """Return the async Redis client singleton for rate limiting.

    Connects to DB0 (separate from cost tracker's DB5).
    Authenticates with ``REDIS_PASSWORD`` when present (production).
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
    """Return the shared HermesSessionAdapter singleton.

    Delegates to ``get_adapter()`` so that slash commands (/new, /history)
    and the conversational handler share the **same** adapter instance,
    Redis connection, agent cache, and metadata store.

    This is the Hermes-native integration point — the adapter wraps
    ``AIAgent`` from ``run_agent`` with per-user session persistence
    and metadata extraction.
    """
    from guinevere.hermes.adapter import get_adapter

    return get_adapter()


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# Response Chunking (fallback — Hermes streaming handles this natively)
# ---------------------------------------------------------------------------

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

    This is the **fallback** chunker — Hermes streaming handles chunking
    natively when available. Used when streaming is disabled or unavailable.

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


# ---------------------------------------------------------------------------
# Hermes AIAgent Response — Streaming with fallback
# ---------------------------------------------------------------------------


async def _invoke_hermes_and_send(
    author: Any,
    channel: Any,
    content: str,
    system_prompt: str,
) -> tuple[str, dict[str, Any]]:
    """Invoke Hermes AIAgent and send response via streaming or chunk fallback.

    The HermesSessionAdapter wraps ``AIAgent.run_conversation()`` under the
    hood. The response is sent to Discord via progressive streaming when
    the Hermes backend supports it; otherwise falls back to the sentence-
    boundary chunker.

    Args:
        author: The ``discord.Member`` who sent the message.
        channel: The ``discord.TextChannel`` to send responses to.
        content: The cleaned user message content.
        system_prompt: The assembled system prompt string.

    Returns:
        A tuple of ``(full_response_text, metadata_dict)`` where metadata
        contains token and cost information from the Hermes response.

    Raises:
        Exception: If the Hermes call fails — caught by caller.
    """
    hermes = _get_hermes()

    # HermesSessionAdapter.send_message() wraps AIAgent.run_conversation()
    # synchronously via asyncio.to_thread(). This is the Hermes-native
    # integration path — all custom hooks (distress, mood, memory, etc.)
    # run in the conversational handler layer, NOT inside Hermes.
    response_text: str = await hermes.send_message(
        user_id=str(author.id),
        content=content,
        system_prompt=system_prompt,
    )

    if not response_text:
        return "", {}

    # Extract metadata for cost tracking
    metadata: dict[str, Any] = hermes.get_last_metadata(str(author.id))

    # Send response to Discord — chunk if needed (streaming fallback)
    chunks = _split_response(response_text)
    for chunk in chunks:
        await channel.send(chunk)

    return response_text, metadata


# ---------------------------------------------------------------------------
# Main Handler — Interface compatible with bot.py ``on_message``
# ---------------------------------------------------------------------------


async def handle_conversation(
    bot: Any,
    message: Any,
    channel_config: Any = None,
    action_executor: Any = None,
) -> bool:
    """Handle conversational messages in conversational channels.

    Orchestrates the full Hermes-native conversational flow: guard checks,
    rate limiting, distress detection, system prompt assembly with
    affect-driven tone, memory recall, Hermes AIAgent invocation, response
    delivery, cost tracking, shadow forwarding, auto-store, and structured
    logging.

    B5: When *action_executor* is provided, it is stored as the module
    default for ``process_thought_for_discord()`` and used for any
    inline thought evaluations.

    Interface is compatible with ``bot.py`` ``on_message``::

        handled = await handle_conversation(self, message)
        if handled:
            return

    Returns ``True`` if the message was handled (even if silently absorbed),
    ``False`` to pass through to ``process_commands``.

    Args:
        bot: The ``GuinevereBot`` instance (used for context, not modified).
        message: The ``discord.Message`` to evaluate and respond to.
        channel_config: Optional ``ChannelConfig`` instance.  If not
            provided, the function attempts to read ``bot.channel_config``.
            Falls back to an empty set (no channels → no conversational
            messages processed).
        action_executor: Optional ``ActionExecutor`` instance for B5
            loop-driven behavior.  Stored as module-level reference.

    Returns:
        ``True`` if the message was handled, ``False`` to pass through.
    """
    global _conversational_channel_ids

    # B5: store action executor reference if provided.
    if action_executor is not None:
        set_action_executor(action_executor)
    # B5: store bot reference for send callbacks.
    set_bot_reference(bot)

    start_time = time.time()

    # --- Resolve conversational channel IDs ---
    if _conversational_channel_ids is None:
        cfg = channel_config or getattr(bot, "channel_config", None)
        if cfg is not None:
            _conversational_channel_ids = resolve_conversational_channels(cfg)
        else:
            _conversational_channel_ids = frozenset()

    # --- Step 1: Channel check ---
    channel = message.channel if message is not None else None
    if channel is None or channel.id not in _conversational_channel_ids:
        return False

    # --- Step 2: Bot check ---
    author = message.author if message is not None else None
    if author is None or author.bot:
        return False

    # --- Step 3: Slash command check ---
    content: str = message.content if message is not None else ""
    if not content or content.startswith("/"):
        return False

    # --- Step 4: Faiz check (guild owner) ---
    guild = message.guild if message is not None else None
    if guild is None or guild.owner_id != author.id:
        return False

    # --- Step 5: Rate limiting ---
    user_id: int = int(author.id)
    if await _is_rate_limited(user_id):
        return True  # Absorbed silently

    # --- Step 6: Typing indicator ---
    typing_ctx = channel.typing if channel is not None else None
    if typing_ctx is not None:
        async with typing_ctx():
            return await _process_and_respond(
                bot, author, channel, content, start_time,
                action_executor=action_executor,
            )
    # Fallback: no typing context available (shouldn't happen in practice)
    return await _process_and_respond(
        bot, author, channel, content, start_time,
        action_executor=action_executor,
    )


# ---------------------------------------------------------------------------
# Internal: Process and Respond
# ---------------------------------------------------------------------------


async def _process_and_respond(
    bot: Any,
    author: Any,
    channel: Any,
    content: str,
    start_time: float,
    action_executor: Any = None,
) -> bool:
    """Core Hermes-native conversational flow after guard checks pass.

    Handles distress detection, memory recall + system prompt assembly,
    Hermes AIAgent invocation, response delivery, cost tracking, shadow
    forwarding, auto-store, and structured logging.

    All safety decisions are made HERE — not inside Hermes. Hermes is
    treated as a pure LLM backend.

    Args:
        bot: The ``GuinevereBot`` instance (provides session factory, shadow).
        author: The ``discord.Member`` who sent the message.
        channel: The ``discord.TextChannel`` to send responses to.
        content: The cleaned message content string.
        start_time: ``time.time()`` timestamp for latency measurement.

    Returns:
        ``True`` — the message was always handled (even on error).
    """
    # ── Step 7: Distress detection ─────────────────────────────────────────
    from guinevere.persona.safe_mode import DistressDetector, SafeModeController

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
        from datetime import datetime, timezone as tz

        from guinevere.persona.safe_mode import DistressLevel, DistressSignal

        signal = DistressSignal(
            text="",
            detected_level=DistressLevel.D0_NORMAL,
            confidence=1.0,
            matched_patterns=[],
            timestamp=datetime.now(tz=tz.utc),
        )
        safe_mode_activated = False

    # ── Step 8: Mood evaluation + B5 Affect-driven tone ────────────────────
    from guinevere.persona.mood_engine import Mood

    # Default to Content for conversational context
    current_mood: str = Mood.CONTENT.value

    # B5: Read AffectVector from consciousness state for tone modulation.
    affect_tone: str = ""
    try:
        consciousness_loop = getattr(bot, "consciousness_loop", None)
        if consciousness_loop is not None:
            state = getattr(consciousness_loop, "state", None)
            if state is not None:
                affect = getattr(state, "affect", None)
                affect_tone = compute_affect_tone(affect)
                if affect_tone:
                    logger.info(
                        "affect_tone_computed",
                        tone=affect_tone,
                        valence=getattr(affect, "valence", 0.5),
                        arousal=getattr(affect, "arousal", 0.5),
                    )
    except Exception as exc:
        logger.debug(
            "affect_tone_fallback",
            error=str(exc),
            error_type=type(exc).__name__,
        )

    # ── Step 9: System prompt assembly with memory recall ──────────────────
    from guinevere.core.services.prompt_loader import get_system_prompt_with_context

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

        # B5: Inject affect-driven tone into system prompt.
        if affect_tone:
            system_prompt += f"\n\n[{affect_tone}]"
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

    # ── Step 10: Hermes AIAgent invocation ─────────────────────────────────
    # HermesSessionAdapter.send_message() wraps AIAgent.run_conversation().
    # All custom hooks (distress, mood, memory, cost, shadow) live HERE —
    # Hermes is a pure LLM backend.
    try:
        response_text, hermes_metadata = await _invoke_hermes_and_send(
            author=author,
            channel=channel,
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

    # Extract token/model metadata for logging and cost tracking
    prompt_tokens: int = int(hermes_metadata.get("input_tokens", 0))
    completion_tokens: int = int(hermes_metadata.get("output_tokens", 0))
    model_used: str = str(hermes_metadata.get("model", "unknown"))
    chunk_count: int = len(_split_response(response_text))

    # ── Step 10b: Shadow forward (fire-and-forget) ─────────────────────────
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

    # ── Step 11: Cost tracking ─────────────────────────────────────────────
    try:
        estimated_cost: float = float(
            hermes_metadata.get("estimated_cost_usd", 0.0)
        )
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
            from guinevere.core.services.llm_router import MODELS, TaskType

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

    # ── Step 12: Auto-store conversation to memory ─────────────────────────
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
            logger.info(
                "memory_auto_store_skipped", reason="no_session_factory",
            )
    except Exception as exc:
        logger.warning(
            "memory_auto_store_error",
            error=str(exc),
            error_type=type(exc).__name__,
        )

    # ── Step 13: Structured logging (metadata only, no content) ────────────
    logger.info(
        "hermes_conversational_response",
        user_id_hash=user_id_hash,
        channel_id=getattr(channel, "id", 0),
        response_length=len(response_text),
        latency_ms=round((time.time() - start_time) * 1000, 1),
        model_used=model_used,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
        chunks_sent=chunk_count,
        distress_level=signal.detected_level.name,
        safe_mode_active=safe_mode_activated,
    )

    return True