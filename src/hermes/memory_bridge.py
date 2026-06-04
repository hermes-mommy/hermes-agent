"""Hermes Memory Bridge — Phase 2.

Bridges Hermes conversational agent with Guinevere's episodic memory system.
Provides READ path (recall_for_context) and WRITE path (store_conversation)
with graceful degradation when embeddings are unavailable.

Safety: DNR exclusion, classification ceiling, safe-mode, token budget —
all delegated to underlying pipelines. No raw content in logs.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

if TYPE_CHECKING:
    from src.memory.read_pipeline import EmbeddingClient

_logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session factory protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class AsyncSessionFactory(Protocol):
    """Callable that returns an async context manager yielding a DB session.

    Compatible with ``sqlalchemy.ext.asyncio.async_sessionmaker`` and any
    callable whose return value satisfies ``async with``.
    """

    def __call__(self) -> Any:
        ...


# ---------------------------------------------------------------------------
# HermesMemoryBridge
# ---------------------------------------------------------------------------


class HermesMemoryBridge:
    """Bridge between Hermes conversational agent and Guinevere's episodic memory.

    Wraps ``recall_memories`` (read pipeline) and ``store_episode`` (write
    pipeline) behind a safe facade that never propagates exceptions to the
    caller.  All safety decisions — DNR exclusion, classification ceiling,
    safe-mode substitution, token budget — are delegated to the underlying
    pipelines.

    Parameters
    ----------
    session_factory:
        Callable that returns an async context manager yielding a
        SQLAlchemy ``AsyncSession`` (e.g. ``async_sessionmaker``).
    embedding_service:
        Optional ``EmbeddingService`` instance.  When ``None``, recalls
        fall back to FTS-only search and writes skip embedding.
    """

    def __init__(
        self,
        session_factory: AsyncSessionFactory,
        embedding_service: EmbeddingClient | None = None,
    ) -> None:
        """Initialise the memory bridge.

        Parameters
        ----------
        session_factory:
            Callable that returns an async context manager for database
            sessions.  Typically an ``async_sessionmaker`` bound to the
            Guinevere database.
        embedding_service:
            Optional ``EmbeddingService`` instance for vector search and
            embedding generation.  ``None`` disables embeddings — recall
            uses full-text search only and writes skip embedding.
        """
        self._session_factory: AsyncSessionFactory = session_factory
        self._embedding_service: EmbeddingClient | None = embedding_service

    # ── READ path ──────────────────────────────────────────────────────────

    async def recall_for_context(
        self,
        query: str,
        *,
        safe_mode: bool = False,
        principal: str = "guinevere_core",
        limit: int = 5,
        token_budget: int = 800,
    ) -> list[dict[str, object]]:
        """Recall relevant episodic memories for conversational context.

        Wraps ``recall_memories()`` from ``src.memory.read_pipeline`` with
        automatic session management and exception safety.

        Parameters
        ----------
        query:
            Natural-language query for memory search.
        safe_mode:
            If ``True``, critical/restricted content is replaced with
            placeholders and sensitive topics are blocked.
        principal:
            Identity determining the classification ceiling.
            Default ``"guinevere_core"``.
        limit:
            Maximum number of results to return.  Default ``5``.
        token_budget:
            Maximum estimated token count for returned results.
            Default ``800``.

        Returns
        -------
        ``list[dict[str, object]]``
            Each dict contains keys: ``id``, ``safe_content``,
            ``classification``, ``importance``, ``created_at``,
            ``combined_score``, ``is_summarized``.
            Returns empty list on any error.
        """
        # Lazy import to avoid circular dependency at module level.
        from src.memory.read_pipeline import recall_memories  # noqa: PLC0415

        _query_len: int = len(query)

        try:
            async with self._session_factory() as session:
                results = await recall_memories(
                    session,
                    query,
                    limit=limit,
                    exclude_dnr=True,
                    safe_mode=safe_mode,
                    principal=principal,
                    token_budget=token_budget,
                    embedding_service=self._embedding_service,
                )

            _logger.info(
                "bridge_recall_success",
                extra={
                    "query_length": _query_len,
                    "results_count": len(results),
                    "safe_mode": safe_mode,
                },
            )
            return results

        except Exception as exc:
            _logger.warning(
                "bridge_recall_error",
                extra={
                    "query_length": _query_len,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return []

    # ── WRITE path ─────────────────────────────────────────────────────────

    async def store_conversation(
        self,
        user_message: str,
        assistant_response: str,
        user_id_hash: str,
        *,
        safe_mode: bool = False,
    ) -> str | None:
        """Store a completed conversation turn as an episodic memory.

        Wraps ``store_episode()`` from ``src.memory.write_pipeline`` with
        automatic session management and exception safety.

        Parameters
        ----------
        user_message:
            The user's message text.
        assistant_response:
            The assistant's response text.
        user_id_hash:
            Hashed user identifier for tagging and safe logging.
        safe_mode:
            If ``True``, stored as metadata for downstream filtering.

        Returns
        -------
        ``str | None``
            Episode UUID string on success, ``None`` on any error.
        """
        # Lazy imports to avoid circular dependency at module level.
        from src.memory.write_pipeline import RESTRICTED, store_episode  # noqa: PLC0415

        content: str = (
            f"Faiz: {user_message}\nGuinevere: {assistant_response}"
        )
        _content_len: int = len(content)
        _user_msg_len: int = len(user_message)
        _assistant_len: int = len(assistant_response)

        # Build a summary that includes keywords from both sides so FTS
        # can match on response terms too (e.g. "kopi hitam tanpa gula"
        # in the assistant reply).  search_vector weighs summary at B.
        summary_text: str = (
            f"Faiz: {user_message[:120]} "
            f"Guinevere: {assistant_response[:180]}"
        )[:300]

        try:
            async with self._session_factory() as session:
                # Always pass embedding_service=None for writes.
                # 9Router has no embedding models; passing a live service
                # causes _compute_embedding() to raise → entire store crashes.
                # Episodes are persisted without embedding vectors (FTS-only
                # recall).  A backfill job can generate embeddings later when
                # a capable provider is configured.
                episode_id = await store_episode(
                    session=session,
                    content=content,
                    source="discord_conversation",
                    classification=RESTRICTED,
                    importance=3,
                    title=user_message[:100],
                    summary=summary_text,
                    episode_type="conversation",
                    tags=["discord", "chat", f"user:{user_id_hash}"],
                    metadata={
                        "channel": "guinevere-chat",
                        "user_hash": user_id_hash,
                        "response_length": _assistant_len,
                        "safe_mode": safe_mode,
                    },
                    embedding_service=None,
                )
                # store_episode() flushes but does not commit.
                # Without explicit commit, the async-with session exits
                # and SQLAlchemy rolls back — episode is lost silently.
                await session.commit()

            _episode_id_str: str = str(episode_id)
            _logger.info(
                "bridge_store_success",
                extra={
                    "episode_id": _episode_id_str,
                    "content_length": _content_len,
                },
            )
            return _episode_id_str

        except Exception as exc:
            _logger.warning(
                "bridge_store_error",
                extra={
                    "user_id_hash": user_id_hash,
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return None

    # ── Key fact extraction (stub — Phase 3) ───────────────────────────────

    async def extract_key_facts(
        self,
        conversation: str,
        *,
        limit: int = 3,
    ) -> list[str]:
        """Extract key facts from a conversation (stub — Phase 3).

        Full LLM-based extraction is deferred to Phase 3.  This stub
        returns an empty list and logs the invocation for metrics.

        Parameters
        ----------
        conversation:
            The conversation text to analyze.
        limit:
            Maximum number of facts to extract.  Unused in Phase 2.

        Returns
        -------
        ``list[str]``
            Always returns ``[]`` in Phase 2.
        """
        _ = limit  # reserved for Phase 3 LLM extraction
        _conversation_len: int = len(conversation)
        _logger.info(
            "bridge_extract_key_facts_stub",
            extra={"conversation_length": _conversation_len},
        )
        return []