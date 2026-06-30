"""Non-deprecated home for HermesSessionAdapter.

This module provides the production ``HermesSessionAdapter`` class that
was originally defined in ``session_adapter.py`` (which is slated for
archive in Phase 7c).  All runtime behaviour is identical — this is a
file-level extraction only.

Importing this module does **not** pull in any deprecated modules.
The deprecated ``src/hermes/session_adapter.py`` is left untouched for
later git-mv archive.

Usage::

    from guinvere.hermes._session_adapter import HermesSessionAdapter

See ``src.hermes.adapter`` for the ``get_adapter()`` singleton factory.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

import redis.asyncio as aioredis
from run_agent import AIAgent

if TYPE_CHECKING:
    from redis.asyncio import Redis

logger = logging.getLogger(__name__)

# ── Constants ────────────────────────────────────────────────────────────────

REDIS_HOST: str = "localhost"
"""Redis server hostname."""

REDIS_PORT: int = 6380
"""Redis server port (non‑standard)."""

REDIS_DB: int = 4
"""Redis logical database for Hermes session storage."""

REDIS_USERNAME: str = "guinevere_core"
"""Redis ACL username."""

SESSION_TTL: int = 7200
"""Session idle TTL in seconds (2 hours)."""

MAX_HISTORY_TURNS: int = 20
"""Maximum number of user+assistant turns before oldest are pruned."""

KEY_PREFIX: str = "hermes:session:"
"""Redis key prefix for session data."""

FALLBACK_MESSAGE: str = (
    "Maaf, aku sedang kesulitan berpikir jernih. "
    "Coba lagi sebentar, ya. \U0001f49b"
)
"""Graceful fallback when LLM call fails. Unicode: \U0001f49b = 💛."""


# ── Helpers ───────────────────────────────────────────────────────────────────


def _hash_user_id(user_id: str) -> str:
    """Return truncated SHA‑256 hash of *user_id* for safe logging.

    Args:
        user_id: The raw user ID string.

    Returns:
        First 8 hex characters of the SHA‑256 digest.
    """
    return hashlib.sha256(user_id.encode()).hexdigest()[:8]


# ── Adapter ───────────────────────────────────────────────────────────────────


class HermesSessionAdapter:
    """Per‑user AIAgent manager with Redis DB4 session store.

    Manages conversation history for multi‑turn conversations.
    Hermes native memory is DISABLED (``skip_memory=True``).
    Safety guards remain in ``conversational_handler.py`` — NEVER here.
    """

    def __init__(self, redis_client: "Redis", llm_config: dict[str, Any]) -> None:
        """Initialise adapter with Redis connection and LLM configuration.

        *redis_client* is accepted for API compatibility; a dedicated
        async Redis connection to **DB4** is created internally.

        Args:
            redis_client: Unused — a dedicated DB4 connection is created.
            llm_config: Dict with keys ``base_url``, ``model``,
                ``provider``, ``api_key``.
        """
        self._redis = aioredis.Redis(
            host=REDIS_HOST,
            port=REDIS_PORT,
            db=REDIS_DB,
            username=REDIS_USERNAME,
            password=os.environ.get("REDIS_PASSWORD", ""),
            decode_responses=True,
        )
        self._llm_config = llm_config
        # In‑memory cache of AIAgent instances keyed by user_id.
        # AIAgent is stateless (history is stored in Redis), so this
        # cache avoids re‑creating the object on every message.
        self._agents: dict[str, AIAgent] = {}
        # Metadata from the most recent send_message() call per user.
        # Used by conversational_handler.py for cost tracking.
        self._last_metadata: dict[str, dict[str, Any]] = {}

    # ── Private helpers ───────────────────────────────────────────────────────

    def _build_key(self, user_id: str) -> str:
        """Return the Redis key for *user_id* session."""
        return f"{KEY_PREFIX}{user_id}"

    @staticmethod
    def _new_agent(llm_config: dict[str, Any]) -> AIAgent:
        """Create a fresh AIAgent instance with Hermes native memory disabled.

        Args:
            llm_config: Dict with ``base_url``, ``model``, ``provider``,
                and ``api_key``.

        Returns:
            A configured ``AIAgent`` instance.
        """
        return AIAgent(
            base_url=llm_config["base_url"],
            model=llm_config["model"],
            provider=llm_config["provider"],
            api_key=llm_config.get("api_key", ""),
            skip_memory=True,
            skip_context_files=True,
            quiet_mode=True,
            max_iterations=1,
            enabled_toolsets=[],
            disabled_toolsets=["*"],
        )

    @staticmethod
    def _prune_history(history: list[dict[str, str]]) -> list[dict[str, str]]:
        """Prune *history* to at most ``MAX_HISTORY_TURNS`` turns.

        Each turn is a user + assistant pair (2 messages).

        Args:
            history: The full conversation history list.

        Returns:
            The pruned history list (newest messages retained).
        """
        max_messages = MAX_HISTORY_TURNS * 2
        if len(history) > max_messages:
            excess = len(history) - max_messages
            return history[excess:]
        return history

    # ── Public API ────────────────────────────────────────────────────────────

    async def get_or_create_session(self, user_id: str) -> AIAgent:
        """Get existing AIAgent or create new one with stored history.

        Args:
            user_id: Discord user snowflake ID (string).

        Returns:
            An ``AIAgent`` instance for the given user.
        """
        if user_id not in self._agents:
            self._agents[user_id] = self._new_agent(self._llm_config)
        return self._agents[user_id]

    async def send_message(
        self,
        user_id: str,
        content: str,
        system_prompt: str,
    ) -> str:
        """Send message via AIAgent, update session history, return response.

        Flow:
            1. Get or create AIAgent for *user_id*.
            2. Load conversation history from Redis.
            3. Call ``run_conversation()`` with history.
            4. Extract ``final_response``.
            5. Append user + assistant turn to history.
            6. Prune history if exceeding ``MAX_HISTORY_TURNS``.
            7. Persist updated session to Redis with TTL.
            8. Return response text.

        Args:
            user_id: Discord user snowflake ID (string).
            content: The user's message text.
            system_prompt: System prompt for this conversation turn.

        Returns:
            The assistant's response text, or a graceful fallback.
        """
        agent = await self.get_or_create_session(user_id)
        key = self._build_key(user_id)

        # ── Load existing history from Redis ──────────────────────────────
        history: list[dict[str, str]] = []
        created_at: str | None = None
        try:
            raw = await self._redis.get(key)
            if raw:
                session_data = json.loads(raw)
                history = session_data.get("history", [])
                created_at = session_data.get("created_at")
        except (json.JSONDecodeError, ConnectionError, OSError) as exc:
            logger.warning(
                "hermes_session_load_error",
                extra={
                    "user_id_hash": _hash_user_id(user_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            # Graceful degradation — start with fresh history

        # ── Call Hermes AIAgent (sync, offloaded to thread) ──────────────
        try:
            result: dict[str, Any] = await asyncio.to_thread(
                agent.run_conversation,
                user_message=content,
                system_message=system_prompt,
                conversation_history=history,
            )
        except Exception as exc:
            logger.error(
                "hermes_run_conversation_failed",
                extra={
                    "user_id_hash": _hash_user_id(user_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return FALLBACK_MESSAGE

        final_response: str = str(result.get("final_response", ""))
        if not final_response:
            logger.warning(
                "hermes_empty_response",
                extra={"user_id_hash": _hash_user_id(user_id)},
            )
            return FALLBACK_MESSAGE

        # ── Store metadata for cost tracking ─────────────────────────────
        self._last_metadata[user_id] = {
            "input_tokens": int(result.get("input_tokens", 0)),
            "output_tokens": int(result.get("output_tokens", 0)),
            "total_tokens": int(result.get("total_tokens", 0)),
            "model": str(result.get("model", self._llm_config.get("model", "unknown"))),
            "estimated_cost_usd": float(result.get("estimated_cost_usd", 0.0)),
            "completion_tokens": int(result.get("completion_tokens", 0)),
        }

        # ── Append new turn ───────────────────────────────────────────────
        history.append({"role": "user", "content": content})
        history.append({"role": "assistant", "content": final_response})
        history = self._prune_history(history)

        # ── Persist to Redis ──────────────────────────────────────────────
        now: str = datetime.now(tz=timezone.utc).isoformat()
        session_data: dict[str, Any] = {
            "history": history,
            "created_at": created_at or now,
            "last_used": now,
            "turn_count": len(history) // 2,
        }
        try:
            await self._redis.setex(
                key,
                SESSION_TTL,
                json.dumps(session_data, ensure_ascii=False),
            )
        except (ConnectionError, OSError) as exc:
            logger.warning(
                "hermes_session_save_error",
                extra={
                    "user_id_hash": _hash_user_id(user_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            # Non‑fatal — response already returned, just log

        return final_response

    async def clear_session(self, user_id: str) -> None:
        """Delete AIAgent instance and Redis session data.

        Args:
            user_id: Discord user snowflake ID (string).
        """
        self._agents.pop(user_id, None)
        try:
            await self._redis.delete(self._build_key(user_id))
        except (ConnectionError, OSError) as exc:
            logger.warning(
                "hermes_session_clear_error",
                extra={
                    "user_id_hash": _hash_user_id(user_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    async def get_history(
        self,
        user_id: str,
        limit: int = 10,
    ) -> list[dict[str, str]]:
        """Return last N turns from session as list of ``{role, content}`` dicts.

        Args:
            user_id: Discord user snowflake ID (string).
            limit: Maximum number of **turns** (user + assistant pairs)
                to return. Defaults to 10 (20 individual messages).

        Returns:
            List of ``{"role": ..., "content": ...}`` dicts, newest last.
        """
        try:
            raw = await self._redis.get(self._build_key(user_id))
            if not raw:
                return []
            session_data = json.loads(raw)
            history: list[dict[str, str]] = session_data.get("history", [])
        except (json.JSONDecodeError, ConnectionError, OSError) as exc:
            logger.warning(
                "hermes_history_load_error",
                extra={
                    "user_id_hash": _hash_user_id(user_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return []

        # Return last limit*2 messages (limit in turns)
        max_messages = limit * 2
        return history[-max_messages:] if len(history) > max_messages else history

    def get_last_metadata(self, user_id: str) -> dict[str, Any]:
        """Return token/cost metadata from the most recent ``send_message()`` call.

        Used by ``conversational_handler.py`` for cost tracking after Hermes
        response. Returns empty dict if no metadata exists for *user_id*.

        Args:
            user_id: Discord user snowflake ID (string).

        Returns:
            Dict with keys ``input_tokens``, ``output_tokens``, ``total_tokens``,
            ``model``, ``estimated_cost_usd``, ``completion_tokens``.
            Returns empty dict if no prior call exists.
        """
        return self._last_metadata.get(user_id, {})

    async def dispose(self) -> None:
        """Close Redis connection and clear all cached agents."""
        self._agents.clear()
        self._last_metadata.clear()
        await self._redis.aclose()
