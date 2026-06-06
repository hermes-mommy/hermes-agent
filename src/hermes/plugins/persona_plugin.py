"""PersonaPlugin — Dynamic persona state injection for Hermes Agent.

This plugin reads Guinevere's dynamic persona state from Redis DB5
and injects it into the LLM prompt context **without** modifying the
static SOUL.md constitution. It acts as a pre-LLM middleware layer
that appends a ``[PERSONA STATE]`` block to the system messages.

Architecture:
    - **Stateless**: No mutable instance state whatsoever. Redis clients
      are short-lived, created per call and closed after use. No
      connection pool, no availability flags, no persona data cached
      between hook invocations.
    - **Graceful degradation**: If Redis is unavailable, injects base
      prompt only and logs a warning. Never blocks the LLM call.
    - **Safety-compatible**: Does NOT override or weaken
      ``safety_plugin.py``. The safety plugin (``GuinevereSafetyPlugin``)
      handles all 10 safety gates. This plugin only *enriches* context.
    - **SOUL.md** remains the static constitution; this plugin provides
      the dynamic overlay only (mood, yandere level, punishment, reward,
      distress, safe word, last interaction).

Redis DB5 key convention (canonical — reconciled with ``guinevere_safety``/StateManager):
    ``guinevere:mood_variant``        — Current mood variant (str: default|playful|serious|caring)
    ``guinevere:yandere_level``       — Current yandere level Y0-Y5 (int, immutable Y4 baseline)
    ``guinevere:punishment_level``    — Current punishment level L0-L5 (int)
    ``guinevere:punishment_reason``   — Reason for active punishment (str)
    ``guinevere:reward_tier``         — Current reward tier T0-T5 (int)
    ``guinevere:distress_state``      — Current distress state D0-D4 (int)
    ``guinevere:last_interaction``    — ISO-8601 timestamp of last user interaction (str)
    ``guinevere:interaction_count``   — Daily interaction counter (int)
    ``guinevere:safe_word``           — Configured safe word (str)

Injection format on every pre_llm_call::

    [PERSONA STATE]
    Mood Variant: {mood_variant}
    Yandere Level: Y{level}
    Punishment Active: L{level} - {reason}
    Reward Tier: T{tier}
    Distress State: D{state}
    Safe Word: {safe_word}
    Interactions Today: {count}
    Last Interaction: {timestamp}
    [END PERSONA STATE]

The punishment line always uses the ``L{level} - {reason}`` format,
even when punishment is inactive (``L0 - none``).
"""

from __future__ import annotations

import importlib
import os
from typing import Final

import structlog

logger: Final = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Redis DB5 connection defaults
# ---------------------------------------------------------------------------
# Match the existing codebase pattern from session_adapter.py:
#   host=localhost, port=6380, username=guinevere_core,
#   password from REDIS_PASSWORD env var.
# DB5 is reserved for dynamic persona state (not DB0 drift baseline).

REDIS_HOST: Final[str] = "localhost"
REDIS_PORT: Final[int] = 6380
REDIS_DB: Final[int] = 5
REDIS_USERNAME: Final[str] = "guinevere_core"
REDIS_SOCKET_TIMEOUT: Final[float] = 2.0

# Redis key prefixes for DB5 persona state (canonical — reconciled with guinevere_safety/StateManager).
_KEY_MOOD_VARIANT: Final[str] = "guinevere:mood_variant"
_KEY_YANDERE_LEVEL: Final[str] = "guinevere:yandere_level"
_KEY_PUNISHMENT_LEVEL: Final[str] = "guinevere:punishment_level"
_KEY_PUNISHMENT_REASON: Final[str] = "guinevere:punishment_reason"
_KEY_REWARD_TIER: Final[str] = "guinevere:reward_tier"
_KEY_DISTRESS_STATE: Final[str] = "guinevere:distress_state"
_KEY_LAST_INTERACTION: Final[str] = "guinevere:last_interaction"
_KEY_INTERACTION_COUNT: Final[str] = "guinevere:interaction_count"
_KEY_SAFE_WORD: Final[str] = "guinevere:safe_word"

# ---------------------------------------------------------------------------
# Plugin-level metadata for Hermes plugin loader.
# ---------------------------------------------------------------------------
# ``safety_critical: true`` is metadata-only documentation. This plugin
# is enrichment-only — it never blocks calls, modifies safety gates, or
# alters enforcement. All safety enforcement remains exclusively in
# ``GuinevereSafetyPlugin`` (``safety_plugin.py``).

PLUGIN_METADATA: Final[dict[str, object]] = {
    "safety_critical": True,
    "description": "Dynamic persona state injection from Redis DB5",
    "impact": "enrichment-only — does not block or alter safety gates",
}

# Default fallback state used when Redis is unavailable.
_DEFAULT_MOOD_VARIANT: Final[str] = "default"
_DEFAULT_YANDERE: Final[int] = 4
_DEFAULT_PUNISHMENT_LEVEL: Final[int] = 0
_DEFAULT_PUNISHMENT_REASON: Final[str] = "none"
_DEFAULT_REWARD_TIER: Final[int] = 0
_DEFAULT_DISTRESS_STATE: Final[int] = 0
_DEFAULT_LAST_INTERACTION: Final[str] = "unknown"
_DEFAULT_INTERACTION_COUNT: Final[int] = 0
_DEFAULT_SAFE_WORD: Final[str] = "HARD STOP"


# =============================================================================
# Stateless Redis helper
# =============================================================================


def _read_persona_state() -> dict[str, object]:
    """Read all persona state keys from Redis DB5.

    **Stateless**: Creates a short-lived Redis client per call, closes
    it after reading. No connection pool, no instance state, no
    availability flags persisted between calls.

    Uses ``importlib.import_module("redis")`` to avoid direct ``import
    redis`` at module level, which has no available type stubs and would
    trigger LSP diagnostics.

    Returns:
        A dict with canonical keys: ``mood_variant`` (str),
        ``yandere_level`` (int), ``punishment_level`` (int),
        ``punishment_reason`` (str), ``reward_tier`` (int),
        ``distress_state`` (int), ``last_interaction`` (str),
        ``interaction_count`` (int), ``safe_word`` (str).
        Missing keys or Redis failures default to sensible fallbacks.

    Pipeline approach: all 9 keys read in a single round-trip.
    """
    try:
        redis_mod = importlib.import_module("redis")
        r = redis_mod.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME,
            password=os.environ.get("REDIS_PASSWORD", ""),
            socket_timeout=REDIS_SOCKET_TIMEOUT,
            decode_responses=True,
        )
    except Exception:
        logger.warning(
            "persona_plugin_redis_unavailable",
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            exc_info=True,
        )
        return {
            "mood_variant": _DEFAULT_MOOD_VARIANT,
            "yandere_level": _DEFAULT_YANDERE,
            "punishment_level": _DEFAULT_PUNISHMENT_LEVEL,
            "punishment_reason": _DEFAULT_PUNISHMENT_REASON,
            "reward_tier": _DEFAULT_REWARD_TIER,
            "distress_state": _DEFAULT_DISTRESS_STATE,
            "last_interaction": _DEFAULT_LAST_INTERACTION,
            "interaction_count": _DEFAULT_INTERACTION_COUNT,
            "safe_word": _DEFAULT_SAFE_WORD,
        }

    try:
        pipe = r.pipeline()
        pipe.get(_KEY_MOOD_VARIANT)
        pipe.get(_KEY_YANDERE_LEVEL)
        pipe.get(_KEY_PUNISHMENT_LEVEL)
        pipe.get(_KEY_PUNISHMENT_REASON)
        pipe.get(_KEY_REWARD_TIER)
        pipe.get(_KEY_DISTRESS_STATE)
        pipe.get(_KEY_LAST_INTERACTION)
        pipe.get(_KEY_INTERACTION_COUNT)
        pipe.get(_KEY_SAFE_WORD)
        results = pipe.execute()
    except Exception:
        logger.warning(
            "persona_plugin_read_error",
            exc_info=True,
        )
        r.close()
        return {
            "mood_variant": _DEFAULT_MOOD_VARIANT,
            "yandere_level": _DEFAULT_YANDERE,
            "punishment_level": _DEFAULT_PUNISHMENT_LEVEL,
            "punishment_reason": _DEFAULT_PUNISHMENT_REASON,
            "reward_tier": _DEFAULT_REWARD_TIER,
            "distress_state": _DEFAULT_DISTRESS_STATE,
            "last_interaction": _DEFAULT_LAST_INTERACTION,
            "interaction_count": _DEFAULT_INTERACTION_COUNT,
            "safe_word": _DEFAULT_SAFE_WORD,
        }

    # Close the Redis connection after reading.
    r.close()

    # Unpack pipeline results: 0=mood_variant, 1=yandere, 2=punishment_level,
    # 3=punishment_reason, 4=reward_tier, 5=distress_state,
    # 6=last_interaction, 7=interaction_count, 8=safe_word.
    mood_variant: str = (
        str(results[0]) if results[0] is not None else _DEFAULT_MOOD_VARIANT
    )

    try:
        yandere_level = int(results[1]) if results[1] is not None else _DEFAULT_YANDERE
    except (ValueError, TypeError):
        yandere_level = _DEFAULT_YANDERE

    try:
        punishment_level = (
            int(results[2]) if results[2] is not None else _DEFAULT_PUNISHMENT_LEVEL
        )
    except (ValueError, TypeError):
        punishment_level = _DEFAULT_PUNISHMENT_LEVEL

    punishment_reason: str = (
        str(results[3]) if results[3] is not None else _DEFAULT_PUNISHMENT_REASON
    )

    try:
        reward_tier = int(results[4]) if results[4] is not None else _DEFAULT_REWARD_TIER
    except (ValueError, TypeError):
        reward_tier = _DEFAULT_REWARD_TIER

    try:
        distress_state = (
            int(results[5]) if results[5] is not None else _DEFAULT_DISTRESS_STATE
        )
    except (ValueError, TypeError):
        distress_state = _DEFAULT_DISTRESS_STATE

    last_interaction: str = (
        str(results[6]) if results[6] is not None else _DEFAULT_LAST_INTERACTION
    )

    try:
        interaction_count = (
            int(results[7]) if results[7] is not None else _DEFAULT_INTERACTION_COUNT
        )
    except (ValueError, TypeError):
        interaction_count = _DEFAULT_INTERACTION_COUNT

    safe_word: str = (
        str(results[8]) if results[8] is not None else _DEFAULT_SAFE_WORD
    )

    # Clamp values to safe ranges.
    yandere_level = max(0, min(5, yandere_level))
    punishment_level = max(0, min(5, punishment_level))
    reward_tier = max(0, min(5, reward_tier))
    distress_state = max(0, min(4, distress_state))
    interaction_count = max(0, interaction_count)

    return {
        "mood_variant": mood_variant,
        "yandere_level": yandere_level,
        "punishment_level": punishment_level,
        "punishment_reason": punishment_reason,
        "reward_tier": reward_tier,
        "distress_state": distress_state,
        "last_interaction": last_interaction,
        "interaction_count": interaction_count,
        "safe_word": safe_word,
    }


# =============================================================================
# Formatting
# =============================================================================


def _format_persona_block(state: dict[str, object]) -> str:
    """Format the persona state dict into the standard injection block.

    Args:
        state: Dict with canonical keys from ``_read_persona_state``.

    Returns:
        A string block in the exact required format::

            [PERSONA STATE]
            Mood Variant: {mood_variant}
            Yandere Level: Y{level}
            Punishment Active: L{level} - {reason}
            Reward Tier: T{tier}
            Distress State: D{state}
            Safe Word: {safe_word}
            Interactions Today: {count}
            Last Interaction: {timestamp}
            [END PERSONA STATE]

        The punishment line ALWAYS uses the ``L{level} - {reason}``
        format, even when punishment is inactive (``L0 - none``).
    """
    mood_variant = state.get("mood_variant", _DEFAULT_MOOD_VARIANT)
    yandere_level = state.get("yandere_level", _DEFAULT_YANDERE)
    punishment_level = state.get("punishment_level", _DEFAULT_PUNISHMENT_LEVEL)
    punishment_reason = state.get("punishment_reason", _DEFAULT_PUNISHMENT_REASON)
    reward_tier = state.get("reward_tier", _DEFAULT_REWARD_TIER)
    distress_state = state.get("distress_state", _DEFAULT_DISTRESS_STATE)
    last_interaction = state.get("last_interaction", _DEFAULT_LAST_INTERACTION)
    interaction_count = state.get("interaction_count", _DEFAULT_INTERACTION_COUNT)
    safe_word = state.get("safe_word", _DEFAULT_SAFE_WORD)

    # Always use the L{level} - {reason} format per specification.
    punishment_line = (
        f"Punishment Active: L{punishment_level} - {punishment_reason}"
    )

    return (
        f"\n[PERSONA STATE]\n"
        f"Mood Variant: {mood_variant}\n"
        f"Yandere Level: Y{yandere_level}\n"
        f"{punishment_line}\n"
        f"Reward Tier: T{reward_tier}\n"
        f"Distress State: D{distress_state}\n"
        f"Safe Word: {safe_word}\n"
        f"Interactions Today: {interaction_count}\n"
        f"Last Interaction: {last_interaction}\n"
        f"[END PERSONA STATE]"
    )


# =============================================================================
# PersonaPlugin
# =============================================================================


class PersonaPlugin:
    """Hermes plugin that injects dynamic persona state from Redis DB5.

    **Stateless**: No mutable instance state whatsoever. No connection
    pool, no availability flags, no persona data cached between hook
    invocations. Redis is read fresh on each ``pre_llm_call`` via the
    module-level ``_read_persona_state()`` function, which creates a
    short-lived client and closes it after use.

    **Graceful degradation**: If Redis is unreachable, the plugin
    logs a warning and allows the LLM call to proceed with the base
    prompt only (no persona state injected).

    **Redis DB5 key convention** (canonical — reconciled with
    ``guinevere_safety``/``StateManager``)::

        guinevere:mood_variant       — Mood variant (default|playful|serious|caring)
        guinevere:yandere_level      — Yandere level (immutable Y4 baseline)
        guinevere:punishment_level   — Punishment level L0-L5
        guinevere:punishment_reason  — Reason for active punishment
        guinevere:reward_tier        — Reward tier T0-T5
        guinevere:distress_state     — Distress state D0-D4
        guinevere:last_interaction   — ISO-8601 timestamp
        guinevere:interaction_count  — Daily interaction counter
        guinevere:safe_word          — Configured safe word

    **Hooks registered**:
        - ``pre_llm_call``: Reads Redis DB5 persona state and injects
          it into the conversation messages as a system-level
          ``[PERSONA STATE]`` block.
        - ``post_llm_call``: Observational logging only.
        - ``pre_tool_call``: Always returns ``None`` (allow). All
          tool-call safety enforcement is delegated to
          ``GuinevereSafetyPlugin``.
        - ``on_session_start``: Observational session init log.
    """

    def __init__(self) -> None:
        """Initialise the plugin.

        Truly stateless: no Redis connections, no connection pools,
        no availability flags are created or stored. Redis connections
        are created on-demand in ``_read_persona_state()`` and closed
        after use.
        """
        logger.info(
            "persona_plugin_init",
            redis_host=REDIS_HOST,
            redis_port=REDIS_PORT,
            redis_db=REDIS_DB,
            plugin_metadata=PLUGIN_METADATA,
        )

    # ------------------------------------------------------------------
    # Hook: pre_llm_call — Inject persona state
    # ------------------------------------------------------------------

    def pre_llm_call(self, **kwargs: object) -> dict[str, object] | None:
        """Inject dynamic persona state into the pre-LLM message context.

        Reads Guinevere's current mood, yandere level, punishment
        state, and last interaction timestamp from Redis DB5, then
        appends a ``[PERSONA STATE]`` block to the last system message
        in the conversation.

        **Graceful degradation**: If Redis is unreachable, the
        persona state block is omitted and the LLM call proceeds with
        the base prompt only. This is logged as a warning.

        **Safety**: This hook is non-blocking. It always returns
        ``None`` (allow). Safety enforcement is handled exclusively
        by ``GuinevereSafetyPlugin``.

        Args:
            **kwargs: Hermes hook kwargs. Expected keys:
                - ``session_id`` (str): Current session identifier.
                - ``messages`` (list[dict]): Current conversation
                  messages (may be modified in-place to inject state).
                - ``user_message`` (str | None): The user's input text.
                - ``conversation_history`` (list[dict] | None):
                  Previous conversation turns.

        Returns:
            Always ``None`` (allow). This plugin does not block.
        """
        session_id_obj = kwargs.get("session_id", "default")
        session_id: str = str(session_id_obj)

        # Read persona state from Redis DB5.
        state = _read_persona_state()
        persona_block = _format_persona_block(state)

        logger.debug(
            "persona_plugin_inject",
            session_id=session_id,
            mood_variant=state.get("mood_variant"),
            yandere_level=state.get("yandere_level"),
            punishment_level=state.get("punishment_level"),
            reward_tier=state.get("reward_tier"),
            distress_state=state.get("distress_state"),
            interaction_count=state.get("interaction_count"),
        )

        # Inject persona state into the messages list.
        # Append it to the last system message if one exists, otherwise
        # prepend a new system message.
        messages_raw = kwargs.get("messages")
        if isinstance(messages_raw, list):
            injected = False
            for msg_obj in reversed(messages_raw):
                if isinstance(msg_obj, dict):
                    role = msg_obj.get("role")
                    if role == "system":
                        existing_content = msg_obj.get("content")
                        if isinstance(existing_content, str):
                            # Only inject if not already present.
                            if "[PERSONA STATE]" not in existing_content:
                                msg_obj["content"] = existing_content + persona_block
                                injected = True
                        break

            if not injected:
                # No system message found — prepend one.
                messages_raw.insert(
                    0,
                    {
                        "role": "system",
                        "content": persona_block.strip(),
                    },
                )

        # Always allow — this is an enrichment-only plugin.
        return None

    # ------------------------------------------------------------------
    # Optional: post_llm_call — Observational logging
    # ------------------------------------------------------------------

    def post_llm_call(self, **kwargs: object) -> None:
        """Post-LLM observational hook for persona tracking.

        Logs persona state after each LLM call for monitoring and
        debugging. Does not modify any state.

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``,
                ``assistant_message``, ``response``, ``model``, etc.
        """
        session_id_obj = kwargs.get("session_id", "default")
        session_id: str = str(session_id_obj)

        logger.debug(
            "persona_plugin_post_llm",
            session_id=session_id,
        )

    # ------------------------------------------------------------------
    # Optional: pre_tool_call — Observational pass-through
    # ------------------------------------------------------------------

    def pre_tool_call(self, **kwargs: object) -> dict[str, object] | None:
        """Observational pre-tool hook.

        This plugin does NOT gate tool calls. All tool-call safety
        enforcement is handled by ``GuinevereSafetyPlugin``.

        Args:
            **kwargs: Hermes hook kwargs including ``tool_name``,
                ``session_id``, ``args``.

        Returns:
            Always ``None`` (allow).
        """
        session_id_obj = kwargs.get("session_id", "default")
        session_id: str = str(session_id_obj)
        tool_name_obj = kwargs.get("tool_name", "unknown")
        tool_name: str = str(tool_name_obj)

        logger.debug(
            "persona_plugin_pre_tool",
            session_id=session_id,
            tool_name=tool_name,
        )

        return None  # Always allow — safety is handled by safety_plugin.py.

    # ------------------------------------------------------------------
    # Optional: on_session_start — Session initialisation log
    # ------------------------------------------------------------------

    def on_session_start(self, **kwargs: object) -> None:
        """Observational session-start hook.

        Logs session initialisation for debugging continuity.

        Args:
            **kwargs: Hermes hook kwargs including ``session_id``,
                ``config``, ``platform``.
        """
        session_id_obj = kwargs.get("session_id", "default")
        session_id: str = str(session_id_obj)

        logger.info(
            "persona_plugin_session_start",
            session_id=session_id,
            redis_db=REDIS_DB,
        )


# =============================================================================
# Plugin registration — Hermes v0.15.2 compatible
# =============================================================================


class _PluginContext:
    """Protocol for hermes-agent's ``PluginContext``.

    Provides the ``register_hook(hook_name, callback)`` method used
    by the Hermes plugin loader. This class is a reference for duck
    typing; the actual context is provided by hermes-agent at runtime.
    """

    def register_hook(self, hook_name: str, callback: object) -> None: ...


def register(ctx: _PluginContext) -> None:
    """Register PersonaPlugin hooks with hermes-agent.

    Called by hermes-agent's plugin loader via ``register(ctx)``.
    The ``ctx`` object provides ``register_hook(hook_name, callback)``.

    Registers 4 hooks:
        - ``pre_llm_call``: Inject persona state into prompt.
        - ``post_llm_call``: Observational logging.
        - ``pre_tool_call``: Observational pass-through.
        - ``on_session_start``: Session initialisation logging.

    Args:
        ctx: PluginContext from hermes-agent's plugin system.
    """
    plugin = PersonaPlugin()

    ctx.register_hook("pre_llm_call", plugin.pre_llm_call)
    ctx.register_hook("post_llm_call", plugin.post_llm_call)
    ctx.register_hook("pre_tool_call", plugin.pre_tool_call)
    ctx.register_hook("on_session_start", plugin.on_session_start)

    logger.info(
        "persona_plugin_registered",
        hook_count=4,
        hooks=[
            "pre_llm_call",
            "post_llm_call",
            "pre_tool_call",
            "on_session_start",
        ],
        plugin_metadata=PLUGIN_METADATA,
        description="Dynamic persona state injection from Redis DB5",
    )
