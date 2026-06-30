"""Email episode storage for the memory bridge.

Stores email episodes with classification-based access control, deduplication
via Redis, and LLM-summary-only storage (never full body). Episodes are
indexed by time in a Redis sorted set for efficient time-range queries.

Design decisions:
- Never stores raw email body/HTML — only LLM-generated summary (max 500 chars).
- Dedup via Redis SET with 7-day TTL to prevent re-processing the same message
  arriving via both Pub/Sub and polling.
- Classification escalation: default Confidential, FINANCIAL/CLIENT_WORK →
  Restricted, SPAM_PHISHING → Internal, secrets/PII detected → Critical.
- Rule-based tags derived from category + subject keywords.
- Redis pipeline used for atomic multi-key write in store_episode.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis
import structlog
from redis.asyncio.client import Pipeline as AsyncPipeline

from .categories import CATEGORY_PRIORITY, EmailCategory, EmailPriority
from .config import GmailSettings, get_gmail_settings
from .envelope import GmailMessageEnvelope

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_DEDUP_SET_KEY: str = "guinevere:gmail:dedup"
"""Redis SET key for deduplication markers."""

_EPISODE_KEY_PREFIX: str = "guinevere:gmail:episodes:"
"""Prefix for per-episode Redis HASH keys."""

_BY_TIME_KEY: str = "guinevere:gmail:episodes:by_time"
"""Redis SORTED SET key for time-indexed episode lookups."""

_DEDUP_TTL_SECONDS: int = 86400 * 7
"""TTL for dedup set members — 7 days."""

_MAX_SUMMARY_LENGTH: int = 500
"""Maximum characters stored for LLM-generated summary."""

_SUBJECT_KEYWORD_TAGS: dict[str, str] = {
    "invoice": "invoice",
    "payment": "payment",
    "meeting": "meeting",
    "deadline": "deadline",
    "report": "report",
    "urgent": "urgent",
    "receipt": "receipt",
    "approval": "approval",
    "reminder": "reminder",
    "confirm": "confirmation",
    "password": "password_reset",
    "verify": "verification",
    "subscribe": "subscription",
    "bill": "billing",
    "statement": "statement",
    "contract": "contract",
    "proposal": "proposal",
    "offer": "offer",
    "agreement": "agreement",
    "notification": "notification",
    "alert": "alert",
    "newsletter": "newsletter",
    "promo": "promotion",
    "discount": "promotion",
    "sale": "promotion",
}
"""Subject keyword → tag mappings for rule-based tag derivation."""


# ---------------------------------------------------------------------------
# EmailEpisode — frozen dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class EmailEpisode:
    """A single stored email episode — summary only, never full body.

    Attributes:
        episode_id: Unique ID derived from message_id hash.
        message_id: Gmail message ID.
        thread_id: Gmail thread ID.
        sender: Sender email address.
        subject: Email subject line.
        category: Classified email category.
        priority: Email routing priority.
        classification_level: Security level: ``"Internal"``,
            ``"Confidential"``, ``"Restricted"``, or ``"Critical"``.
        summary: LLM-generated summary (max 500 chars, never full body).
        tags: Rule-based tags derived from category + subject keywords.
        timestamp: Original email timestamp (UTC).
        stored_at: When this episode was stored (UTC).
    """

    episode_id: str
    message_id: str
    thread_id: str
    sender: str
    subject: str
    category: EmailCategory
    priority: EmailPriority
    classification_level: str
    summary: str
    tags: list[str]
    timestamp: datetime
    stored_at: datetime


# ---------------------------------------------------------------------------
# Serialization helpers
# ---------------------------------------------------------------------------


def _episode_key(episode_id: str) -> str:
    """Return the Redis HASH key for a given episode ID."""
    return f"{_EPISODE_KEY_PREFIX}{episode_id}"


def _episode_to_dict(episode: EmailEpisode) -> dict[str, Any]:
    """Convert an ``EmailEpisode`` to a JSON-serialisable dict.

    Datetime fields are serialised to ISO-8601 strings; enum fields
    to their ``.value``.
    """
    return {
        "episode_id": episode.episode_id,
        "message_id": episode.message_id,
        "thread_id": episode.thread_id,
        "sender": episode.sender,
        "subject": episode.subject,
        "category": episode.category.value,
        "priority": episode.priority.value,
        "classification_level": episode.classification_level,
        "summary": episode.summary,
        "tags": list(episode.tags),
        "timestamp": episode.timestamp.isoformat(),
        "stored_at": episode.stored_at.isoformat(),
    }


def _dict_to_episode(data: dict[str, Any]) -> EmailEpisode:
    """Reconstruct an ``EmailEpisode`` from a deserialised dict.

    ISO-8601 datetime strings are parsed back to ``datetime``; enum
    string values are resolved to their ``EmailCategory`` / ``EmailPriority``
    enum members.
    """
    return EmailEpisode(
        episode_id=str(data["episode_id"]),
        message_id=str(data["message_id"]),
        thread_id=str(data["thread_id"]),
        sender=str(data["sender"]),
        subject=str(data["subject"]),
        category=EmailCategory(str(data["category"])),
        priority=EmailPriority(str(data["priority"])),
        classification_level=str(data["classification_level"]),
        summary=str(data["summary"]),
        tags=list(data["tags"]),
        timestamp=datetime.fromisoformat(str(data["timestamp"])),
        stored_at=datetime.fromisoformat(str(data["stored_at"])),
    )


# ---------------------------------------------------------------------------
# Classification escalation
# ---------------------------------------------------------------------------


def _determine_classification_level(
    category: EmailCategory,
    has_secrets_or_pii: bool = False,
) -> str:
    """Determine the security classification level for an email episode.

    Escalation rules:
    - Secrets/PII detected → ``"Critical"``
    - FINANCIAL or CLIENT_WORK → ``"Restricted"``
    - SPAM_PHISHING → ``"Internal"`` (minimal storage)
    - Everything else → ``"Confidential"`` (default)

    Args:
        category: The classified email category.
        has_secrets_or_pii: ``True`` if the email body contained secrets
            or PII (detected upstream by ``CombinedScanner``).

    Returns:
        One of ``"Internal"``, ``"Confidential"``, ``"Restricted"``,
        ``"Critical"``.
    """
    if has_secrets_or_pii:
        return "Critical"
    if category in (EmailCategory.FINANCIAL, EmailCategory.CLIENT_WORK):
        return "Restricted"
    if category is EmailCategory.SPAM_PHISHING:
        return "Internal"
    return "Confidential"


# ---------------------------------------------------------------------------
# Rule-based tag derivation
# ---------------------------------------------------------------------------


def _derive_tags(category: EmailCategory, subject: str) -> list[str]:
    """Derive rule-based tags from the category and subject keywords.

    Always includes the category value as the first tag.  Additional tags
    are added when subject text matches known keyword patterns.

    Args:
        category: The classified email category.
        subject: The email subject line (raw, not lowercased).

    Returns:
        Deduplicated list of tag strings.
    """
    tags: list[str] = [category.value]
    subject_lower = subject.lower()
    for keyword, tag in _SUBJECT_KEYWORD_TAGS.items():
        if keyword in subject_lower and tag not in tags:
            tags.append(tag)
    return tags


# ---------------------------------------------------------------------------
# EmailMemoryStore
# ---------------------------------------------------------------------------


class EmailMemoryStore:
    """Email episode storage with classification, dedup, and Redis persistence.

    Stores LLM-generated summaries (never full email body) with classification
    levels controlling retention and access.  Deduplication prevents
    re-processing the same ``message_id`` arriving via both Pub/Sub push
    notifications and polling fallback.

    Args:
        redis: An ``redis.asyncio.Redis`` client instance.
        settings: Optional ``GmailSettings`` override.  Defaults to the
            module-level singleton from ``get_gmail_settings()``.
    """

    def __init__(
        self,
        redis: aioredis.Redis,
        settings: GmailSettings | None = None,
    ) -> None:
        self._redis: aioredis.Redis = redis
        self._settings: GmailSettings = settings or get_gmail_settings()

    # -- public API ---------------------------------------------------------

    async def store_episode(
        self,
        envelope: GmailMessageEnvelope,
        category: EmailCategory,
        summary: str,
        has_secrets_or_pii: bool = False,
    ) -> EmailEpisode | None:
        """Classify, tag, and store an email episode — unless duplicate.

        If ``message_id`` already exists in the dedup SET the episode is
        silently skipped and ``None`` is returned.  Otherwise the episode
        is persisted to a Redis HASH, added to the time-sorted index, and
        marked in the dedup SET with a 7-day TTL.

        **Never stores the full email body** — only *summary* (truncated
        to 500 characters).

        Args:
            envelope: Normalised Gmail message envelope.
            category: Classified email category.
            summary: LLM-generated summary (will be truncated to 500 chars).
            has_secrets_or_pii: Pass ``True`` when upstream secret/PII scan
                detected sensitive content (escalates classification to
                Critical).

        Returns:
            The stored ``EmailEpisode``, or ``None`` if the message is a
            duplicate or a storage error occurred.
        """
        if await self.is_duplicate(envelope.message_id):
            logger.info(
                "gmail.episode_duplicate_skipped",
                message_id=envelope.message_id,
                category=category.value,
            )
            return None

        now = datetime.now(timezone.utc)
        episode_id = hashlib.sha256(
            envelope.message_id.encode("utf-8")
        ).hexdigest()[:16]

        classification: str = _determine_classification_level(
            category, has_secrets_or_pii,
        )
        priority: EmailPriority = CATEGORY_PRIORITY[category]
        tags: list[str] = _derive_tags(category, envelope.subject)
        truncated_summary: str = summary[:_MAX_SUMMARY_LENGTH]

        episode = EmailEpisode(
            episode_id=episode_id,
            message_id=envelope.message_id,
            thread_id=envelope.thread_id,
            sender=envelope.sender,
            subject=envelope.subject,
            category=category,
            priority=priority,
            classification_level=classification,
            summary=truncated_summary,
            tags=tags,
            timestamp=envelope.timestamp,
            stored_at=now,
        )

        try:
            pipe: AsyncPipeline = self._redis.pipeline()
            _ = pipe.hset(
                _episode_key(episode_id),
                "data",
                json.dumps(_episode_to_dict(episode)),
            )
            _ = pipe.sadd(_DEDUP_SET_KEY, envelope.message_id)
            _ = pipe.expire(_DEDUP_SET_KEY, _DEDUP_TTL_SECONDS)
            _ = pipe.zadd(
                _BY_TIME_KEY,
                {episode_id: episode.timestamp.timestamp()},
            )
            _ = await pipe.execute()
        except Exception:
            logger.exception(
                "gmail.episode_store_failed",
                episode_id=episode_id,
                message_id=envelope.message_id,
            )
            return None

        logger.info(
            "gmail.episode_stored",
            episode_id=episode_id,
            category=category.value,
            classification_level=classification,
            tags=tags,
        )
        return episode

    async def is_duplicate(self, message_id: str) -> bool:
        """Check whether *message_id* has already been stored.

        Queries the Redis dedup SET at ``guinevere:gmail:dedup``.
        Fail-safe: returns ``False`` on any Redis error so the pipeline
        does not skip legitimate messages.

        Args:
            message_id: Gmail message ID to check.

        Returns:
            ``True`` if the message ID exists in the dedup set.
        """
        try:
            result: Any = await self._redis.sismember(
                _DEDUP_SET_KEY, message_id,
            )
            return bool(result)
        except Exception:
            logger.exception(
                "gmail.dedup_check_failed",
                message_id=message_id,
            )
            return False

    async def get_episodes_by_category(
        self,
        category: EmailCategory,
        limit: int = 20,
    ) -> list[EmailEpisode]:
        """Return the most recent episodes matching *category*.

        Scans the time-sorted index from newest to oldest, then filters
        by category.  Over-fetches by 5× to account for non-matching
        episodes.  Returns up to *limit* results.

        Args:
            category: The category to filter by.
            limit: Maximum number of episodes to return.

        Returns:
            A list of matching ``EmailEpisode`` objects, newest first.
        """
        overfetch: int = limit * 5
        episode_ids_raw: list[Any] = await self._redis.zrevrange(
            _BY_TIME_KEY, 0, overfetch - 1,
        )
        episode_ids: list[str] = [
            eid.decode("utf-8") if isinstance(eid, bytes) else str(eid)
            for eid in episode_ids_raw
        ]
        episodes: list[EmailEpisode] = await self._fetch_episodes(
            episode_ids,
        )
        filtered: list[EmailEpisode] = [
            ep for ep in episodes if ep.category == category
        ]
        return filtered[:limit]

    async def get_episodes_by_thread(
        self,
        thread_id: str,
    ) -> list[EmailEpisode]:
        """Return all stored episodes belonging to *thread_id*.

        Because thread messages cluster in time, this scans the most
        recent 1000 entries in the time-sorted index.

        Args:
            thread_id: Gmail thread ID.

        Returns:
            A list of ``EmailEpisode`` objects in the thread, newest first.
        """
        episode_ids_raw: list[Any] = await self._redis.zrevrange(
            _BY_TIME_KEY, 0, 999,
        )
        episode_ids: list[str] = [
            eid.decode("utf-8") if isinstance(eid, bytes) else str(eid)
            for eid in episode_ids_raw
        ]
        episodes: list[EmailEpisode] = await self._fetch_episodes(
            episode_ids,
        )
        return [ep for ep in episodes if ep.thread_id == thread_id]

    async def search_episodes(
        self,
        query: str,
        limit: int = 10,
    ) -> list[EmailEpisode]:
        """Basic substring search across episode subjects and summaries.

        **Placeholder** for future semantic / embedding-based search.
        Performs case-insensitive substring matching on the ``subject``
        and ``summary`` fields of the most recent 1000 episodes.

        Args:
            query: The search string (case-insensitive).
            limit: Maximum number of results to return.

        Returns:
            A list of matching ``EmailEpisode`` objects.
        """
        query_lower: str = query.lower()
        episode_ids_raw: list[Any] = await self._redis.zrevrange(
            _BY_TIME_KEY, 0, 999,
        )
        episode_ids: list[str] = [
            eid.decode("utf-8") if isinstance(eid, bytes) else str(eid)
            for eid in episode_ids_raw
        ]
        episodes: list[EmailEpisode] = await self._fetch_episodes(
            episode_ids,
        )

        matched: list[EmailEpisode] = []
        for ep in episodes:
            if (
                query_lower in ep.subject.lower()
                or query_lower in ep.summary.lower()
            ):
                matched.append(ep)
                if len(matched) >= limit:
                    break
        return matched

    async def get_recent_episodes(
        self,
        hours: int = 12,
        limit: int = 50,
    ) -> list[EmailEpisode]:
        """Return episodes from the last *hours*.

        Uses the time-sorted index to efficiently query the time window.

        Args:
            hours: How many hours back to query from now.
            limit: Maximum number of episodes to return.

        Returns:
            A list of recent ``EmailEpisode`` objects, newest first.
        """
        min_score: float = (
            datetime.now(timezone.utc).timestamp() - hours * 3600
        )
        episode_ids_raw: list[Any] = await self._redis.zrevrangebyscore(
            _BY_TIME_KEY, "+inf", min_score, start=0, num=limit,
        )
        episode_ids: list[str] = [
            eid.decode("utf-8") if isinstance(eid, bytes) else str(eid)
            for eid in episode_ids_raw
        ]
        return await self._fetch_episodes(episode_ids)

    # -- private helpers ----------------------------------------------------

    async def _fetch_episodes(
        self,
        episode_ids: list[str],
    ) -> list[EmailEpisode]:
        """Fetch and deserialize multiple episodes by ID.

        Uses a Redis pipeline to batch ``HGET`` calls for efficiency.

        Args:
            episode_ids: List of episode IDs to fetch.

        Returns:
            A list of successfully deserialised ``EmailEpisode`` objects.
            Corrupted or missing episodes are silently skipped with a
            warning log.
        """
        if not episode_ids:
            return []

        try:
            pipe: AsyncPipeline = self._redis.pipeline()
            for eid in episode_ids:
                _ = pipe.hget(_episode_key(eid), "data")
            results: list[Any] = await pipe.execute()

            episodes: list[EmailEpisode] = []
            for raw in results:
                if raw is None:
                    continue
                try:
                    raw_str: str = (
                        raw.decode("utf-8")
                        if isinstance(raw, bytes)
                        else str(raw)
                    )
                    data: dict[str, Any] = json.loads(raw_str)
                    episodes.append(_dict_to_episode(data))
                except (json.JSONDecodeError, KeyError, ValueError) as exc:
                    logger.warning(
                        "gmail.episode_deserialize_failed",
                        error=str(exc),
                    )
            return episodes
        except Exception:
            logger.exception("gmail.episode_fetch_failed")
            return []


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "EmailEpisode",
    "EmailMemoryStore",
]
