"""Thread context manager for email conversations.

Tracks email thread state, loads thread history (last N messages), and
provides context for draft reply generation.  Uses Redis for ephemeral
thread metadata with configurable TTL.

Design decisions:
- **Immutable snapshot**: ``ThreadContext`` is a frozen dataclass so
  downstream stages (draft/generator.py) can rely on it not changing.
- **Redis-backed metadata**: thread-level state (participants, count,
  last_activity) is persisted with TTL so the manager stays stateless
  across restarts.
- **Fail-open on Redis errors**: ``get_active_threads`` returns an empty
  list rather than raising when Redis is unavailable — the pipeline
  continues without thread context rather than blocking.
- **No raw email content in Redis**: only metadata (count, participants,
  timestamps) is stored; full messages are always passed in-memory.
"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any

import redis.asyncio as aioredis
import structlog

from guinvere.gmail.categories import EmailCategory
from guinvere.gmail.config import GmailSettings, get_gmail_settings
from guinvere.gmail.envelope import GmailMessageEnvelope

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_REDIS_KEY_PREFIX: str = "guinevere:gmail:thread"
"""Redis key prefix for thread metadata (``guinevere:gmail:thread:{thread_id}``)."""

_DEFAULT_THREAD_TTL_DAYS: int = 30
"""Default TTL for thread metadata in Redis.  Configurable at the module level."""

_ACTIVE_THREAD_DAYS: int = 7
"""A thread is considered active when its latest message falls within this window."""

_MAX_REPLY_CONTEXT_MESSAGES: int = 3
"""Number of most recent messages included in ``build_reply_context()``."""

_MAX_BODY_CHARS: int = 500
"""Maximum characters of body text shown per message in the reply context string."""


# ---------------------------------------------------------------------------
# ThreadContext
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ThreadContext:
    """Immutable snapshot of an email thread's aggregated state.

    This dataclass is the primary output of ``ThreadContextManager`` and
    is consumed by the draft generator (Wave 7) to produce context-aware
    LLM replies.

    Attributes:
        thread_id: The Gmail thread identifier.
        message_count: Total number of messages in the thread.
        participants: Unique sender email addresses across all messages.
        latest_messages: The last N messages (default 3), sorted oldest
            first within this list.
        category: Thread-level email classification, derived from the
            most common per-message category, or ``None`` when no
            messages are classified.
        is_active: ``True`` when the most recent message is within the
            last 7 days.
        summary: A brief human-readable summary of the thread for LLM
            context injection.
    """

    thread_id: str
    message_count: int
    participants: list[str] = field(default_factory=list)
    latest_messages: list[GmailMessageEnvelope] = field(default_factory=list)
    category: EmailCategory | None = None
    is_active: bool = False
    summary: str = ""


# ---------------------------------------------------------------------------
# ThreadContextManager
# ---------------------------------------------------------------------------


class ThreadContextManager:
    """Manages email thread state via Redis and provides reply context.

    Args:
        redis: An ``redis.asyncio.Redis`` client for thread metadata storage.
        settings: Optional ``GmailSettings``.  Falls back to
            ``get_gmail_settings()`` when ``None``.
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        settings: GmailSettings | None = None,
    ) -> None:
        self._redis: aioredis.Redis = redis
        self._settings: GmailSettings = settings or get_gmail_settings()

    # -- public API ---------------------------------------------------------

    async def get_thread_context(
        self,
        thread_id: str,
        messages: list[GmailMessageEnvelope],
    ) -> ThreadContext:
        """Build a ``ThreadContext`` snapshot for *thread_id*.

        Sorts messages by timestamp, extracts unique participants,
        determines activity state, resolves a thread-level category,
        and generates a brief summary for LLM consumption.

        Args:
            thread_id: The Gmail thread ID.
            messages: All known messages for this thread, typically
                fetched from the Gmail API or sync engine.

        Returns:
            A ``ThreadContext`` with aggregated thread state.  Returns a
            zero-state context when *messages* is empty.
        """
        if not messages:
            logger.warning(
                "get_thread_context.empty",
                thread_id=thread_id,
            )
            return ThreadContext(
                thread_id=thread_id,
                message_count=0,
                participants=[],
                latest_messages=[],
                category=None,
                is_active=False,
                summary="Empty thread — no messages available.",
            )

        # Sort by timestamp ascending (oldest first)
        sorted_msgs = sorted(messages, key=lambda m: m.timestamp)

        # Unique participants
        participants = sorted(
            {m.sender for m in sorted_msgs if m.sender},
        )

        # Last N messages for context (newest, but kept in chronological order)
        latest_messages = sorted_msgs[-_MAX_REPLY_CONTEXT_MESSAGES:]

        # Activity check: latest message within 7 days
        latest_ts: datetime = sorted_msgs[-1].timestamp
        is_active = (datetime.now(timezone.utc) - latest_ts) <= timedelta(
            days=_ACTIVE_THREAD_DAYS,
        )

        # Thread-level category from most common per-message classification
        category = self._resolve_category(sorted_msgs)

        # Build summary for LLM
        subject = sorted_msgs[-1].subject or "(no subject)"
        participant_str = ", ".join(participants) if participants else "unknown"
        summary = (
            f"Thread with {len(sorted_msgs)} messages between "
            f"{participant_str}. Subject: {subject}. "
            f"Latest activity: {latest_ts.isoformat()}."
            f"{' Active' if is_active else ' Inactive'}."
        )

        context = ThreadContext(
            thread_id=thread_id,
            message_count=len(sorted_msgs),
            participants=participants,
            latest_messages=latest_messages,
            category=category,
            is_active=is_active,
            summary=summary,
        )

        logger.info(
            "get_thread_context.complete",
            thread_id=thread_id,
            message_count=context.message_count,
            is_active=context.is_active,
            category=context.category.value if context.category else None,
        )

        return context

    async def update_thread(self, envelope: GmailMessageEnvelope) -> None:
        """Update Redis state with new message data for the thread.

        Creates or updates the ``guinevere:gmail:thread:{thread_id}`` key
        in Redis.  Merges the sender into the participants list,
        increments ``message_count``, refreshes ``last_activity``, and
        sets a TTL of 30 days.

        Args:
            envelope: The newly received or processed message envelope.
        """
        key = f"{_REDIS_KEY_PREFIX}:{envelope.thread_id}"

        try:
            raw = await self._redis.get(key)
            if raw is not None:
                existing: dict[str, Any] = json.loads(raw)
            else:
                existing = {
                    "participants": [],
                    "message_count": 0,
                    "last_activity": None,
                    "category": None,
                    "last_subject": "",
                }

            # Merge sender into participants (deduplicate)
            sender = envelope.sender
            if sender and sender not in existing.get("participants", []):
                existing.setdefault("participants", []).append(sender)

            # Increment message count
            existing["message_count"] = existing.get("message_count", 0) + 1

            # Update last activity timestamp
            existing["last_activity"] = envelope.timestamp.isoformat()

            # Update category from envelope classification
            try:
                msg_category = envelope.classify()
                existing["category"] = msg_category.value
            except Exception:
                pass

            # Update last known subject
            if envelope.subject:
                existing["last_subject"] = envelope.subject

            # Persist with TTL
            _set: Any = await self._redis.set(key, json.dumps(existing))
            _exp: Any = await self._redis.expire(key, _DEFAULT_THREAD_TTL_DAYS * 24 * 3600)

            logger.info(
                "update_thread.complete",
                thread_id=envelope.thread_id,
                message_count=existing["message_count"],
                is_active=True,
            )

        except Exception:
            logger.exception(
                "update_thread.failed",
                thread_id=envelope.thread_id,
            )

    async def get_active_threads(self, limit: int = 10) -> list[str]:
        """Return thread IDs with activity in the last 7 days.

        Uses ``SCAN`` to iterate over ``guinevere:gmail:thread:*`` keys,
        checks each ``last_activity`` field against the active threshold,
        and returns the most recently active threads up to *limit*.

        This is a best-effort scan — Redis errors result in an empty list
        so the pipeline is not blocked.

        Args:
            limit: Maximum number of thread IDs to return (default 10).

        Returns:
            A list of thread IDs sorted by most recent activity first.
        """
        pattern = f"{_REDIS_KEY_PREFIX}:*"
        cursor = 0
        active: list[tuple[str, str]] = []
        cutoff = datetime.now(timezone.utc) - timedelta(days=_ACTIVE_THREAD_DAYS)

        try:
            while True:
                cursor, keys = await self._redis.scan(
                    cursor=cursor, match=pattern, count=100,
                )
                if not keys:
                    if cursor == 0:
                        break
                    continue

                # Pipeline-fetch all matched keys
                pipe = self._redis.pipeline()
                for _key in keys:
                    _: Any = pipe.get(_key)
                results: list[bytes | None] = await pipe.execute()

                for key, raw in zip(keys, results):
                    if raw is None:
                        continue
                    try:
                        data: dict[str, Any] = json.loads(raw)
                        last_activity_str = data.get("last_activity")
                        if last_activity_str:
                            last_activity = datetime.fromisoformat(
                                last_activity_str,
                            )
                            if last_activity >= cutoff:
                                key_str = key.decode() if isinstance(key, bytes) else key
                                thread_id = key_str.split(":").pop()
                                active.append((thread_id, last_activity_str))
                    except (json.JSONDecodeError, ValueError, TypeError):
                        continue

                if cursor == 0:
                    break

            # Sort descending by last_activity
            active.sort(key=lambda x: x[1], reverse=True)
            result = [t[0] for t in active[:limit]]

            logger.info(
                "get_active_threads.complete",
                active_count=len(result),
                limit=limit,
            )
            return result

        except Exception:
            logger.exception(
                "get_active_threads.failed",
                limit=limit,
            )
            return []

    async def build_reply_context(
        self,
        thread_id: str,
        messages: list[GmailMessageEnvelope],
    ) -> str:
        """Build a formatted context string for LLM draft generation.

        Formats the thread subject and the last 3 messages — each with
        sender, timestamp, and body text truncated to 500 characters —
        into a compact string ready for LLM context injection.

        Expected format::

            [Thread: {subject}]
            [Message {N} from {sender} at {timestamp}]:
            {body_text truncated to 500 chars}
            ...

        Args:
            thread_id: The Gmail thread ID (used for logging only).
            messages: Messages belonging to this thread.

        Returns:
            A formatted string suitable for LLM context injection.
        """
        if not messages:
            logger.warning(
                "build_reply_context.empty",
                thread_id=thread_id,
            )
            return "[Thread: (empty — no messages available)]\n"

        sorted_msgs = sorted(messages, key=lambda m: m.timestamp)
        total = len(sorted_msgs)

        subject = sorted_msgs[-1].subject or "(no subject)"
        lines: list[str] = [f"[Thread: {subject}]"]

        # Show last N messages with absolute 1-based message numbering
        start_index = max(0, total - _MAX_REPLY_CONTEXT_MESSAGES)
        for i, msg in enumerate(
            sorted_msgs[start_index:], start=start_index + 1,
        ):
            sender = msg.sender or "unknown"
            ts_str = msg.timestamp.isoformat() if msg.timestamp else "unknown"
            body = msg.body_text or msg.snippet or ""
            truncated = body[:_MAX_BODY_CHARS]
            lines.append("")
            lines.append(f"[Message {i} from {sender} at {ts_str}]:")
            lines.append(truncated if truncated else "(no content)")

        result = "\n".join(lines)

        logger.info(
            "build_reply_context.complete",
            thread_id=thread_id,
            messages_included=min(total, _MAX_REPLY_CONTEXT_MESSAGES),
            context_length=len(result),
        )

        return result

    # -- internal helpers ---------------------------------------------------

    @staticmethod
    def _resolve_category(
        messages: list[GmailMessageEnvelope],
    ) -> EmailCategory | None:
        """Determine the thread-level category from per-message classifications.

        Uses the most common ``EmailCategory`` among the messages.
        Returns ``None`` when no messages can be classified.

        Args:
            messages: Sorted or unsorted list of message envelopes.

        Returns:
            The most common ``EmailCategory``, or ``None``.
        """
        if not messages:
            return None

        categories: list[EmailCategory] = []
        for msg in messages:
            try:
                cat = msg.classify()
                categories.append(cat)
            except Exception:
                continue

        if not categories:
            return None

        most_common = Counter(categories).most_common(1)
        return most_common[0][0] if most_common else None


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "ThreadContext",
    "ThreadContextManager",
]
