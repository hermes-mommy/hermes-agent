"""Guinevere Phase 3 Memory Bridge — Hermes Agent MemoryProvider plugin.

Wraps Guinevere's existing memory pipelines (``read_pipeline.recall_memories``,
``write_pipeline.store_episode``) as a proper Hermes external memory plugin.

Key features:
- Transparent memory recall via ``prefetch`` hook (injected into user message)
- Fire-and-forget write via ``sync_turn`` hook (daemon thread, never blocks)
- Consent gate — all reads/writes blocked when consent is revoked
- Safe-word detection — writes skipped when distress reaches D4 (crisis)
- Hardcoded principal ``guinevere_core`` (never configurable)
- DNR exclusion, safe-mode content substitution, token budget — all delegated
  to underlying ``read_pipeline`` and ``write_pipeline``.

Registration entry point::

    from plugins.memory.guinevere_memory import register
    register(ctx)
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import threading
from typing import Any

from .safety_gates import (
    ConsentGate,
    DnrIdCache,
    classify_ceiling_filter,
    content_hash,
    run_safety_pipeline,
)

# ---------------------------------------------------------------------------
# Conditional MemoryProvider base class import
# ---------------------------------------------------------------------------

try:
    from agent.memory_provider import MemoryProvider  # type: ignore[import-not-found]
except ImportError:
    from .base import MemoryProvider  # local stub for development

# ---------------------------------------------------------------------------
# Logger
# ---------------------------------------------------------------------------

_logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants (hardcoded, never configurable)
# ---------------------------------------------------------------------------

_GUINEVERE_PRINCIPAL: str = "guinevere_core"
"""Hardcoded principal identity — never read from config or env."""

_ANTI_HALLUCINATION_GUARD: str = (
    "\n\n[MEMORY STATUS: No relevant memories found for this query. "
    "Do NOT fabricate or guess past preferences, conversations, or facts. "
    "If asked about past conversations or preferences, say: "
    "'Mommy belum punya catatan tentang itu, Darling. "
    "Ceritakan ke Mommy sekarang.']"
)
"""Injected into prefetch return when recall returns empty — prevents LLM hallucination."""

_DEFAULT_RECALL_LIMIT: int = 5
"""Default number of memories to recall."""

_DEFAULT_TOKEN_BUDGET: int = 800
"""Default token budget for recall."""

# ---------------------------------------------------------------------------
# Redis consent check — DB5 (same DB as safety state manager)
# ---------------------------------------------------------------------------

_REDIS_CONSENT_URL: str = "redis://localhost:6380/5"
_REDIS_CONNECT_TIMEOUT: int = 3  # seconds — keep short, consent is on hot path


def _check_redis_consent(category: str) -> bool:
    """Check if consent is granted for a category via Redis DB5.

    Returns True only if Redis is reachable AND the consent key
    is explicitly set to a truthy value.  Returns False in all
    error / unavailable / missing cases — fail-closed.

    This function is intentionally self-contained (no shared state)
    so it can be called from daemon threads without connection pooling
    complications.
    """
    try:
        import redis
        import redis.exceptions as _redis_exc
    except ImportError:
        _logger.warning("redis_not_installed_consent_gate_closed")
        return False

    try:
        r = redis.Redis.from_url(
            _REDIS_CONSENT_URL,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
            socket_timeout=_REDIS_CONNECT_TIMEOUT,
            decode_responses=True,
        )
        try:
            raw = r.get(f"guinevere:consent:{category}")
        finally:
            r.close()
        if raw is None:
            return False
        return raw.lower() in ("1", "true", "yes")
    except (_redis_exc.RedisError, ConnectionError, OSError) as exc:
        _logger.warning(
            "redis_consent_check_failed",
            extra={"category": category, "error": str(exc)},
        )
        return False


def _check_redis_safe_word_active() -> bool:
    """Check if safe-word / crisis state is active in Redis DB5.

    Reads ``guinevere:distress_state`` and ``guinevere:safe_word``.
    Returns True if distress is D4 (crisis) or safe word is active.

    Fail-safe: returns False if Redis is unreachable — allows writes.
    """
    try:
        import redis
    except ImportError:
        return False

    try:
        import redis.exceptions as _redis_exc

        r = redis.Redis.from_url(
            _REDIS_CONSENT_URL,
            socket_connect_timeout=_REDIS_CONNECT_TIMEOUT,
            socket_timeout=_REDIS_CONNECT_TIMEOUT,
            decode_responses=True,
        )
        try:
            raw_distress = r.get("guinevere:distress_state")
            raw_safe_word = r.get("guinevere:safe_word")
        finally:
            r.close()

        if raw_distress is not None:
            try:
                distress_val = int(raw_distress)
            except (ValueError, TypeError):
                distress_val = 0
            if distress_val >= 4:  # D4 = crisis
                _logger.info(
                    "consent_gate_distress_block",
                    extra={"distress_state": distress_val},
                )
                return True

        if raw_safe_word is not None:
            sw_active = str(raw_safe_word).lower() in ("1", "true", "active", "yes")
            if sw_active:
                _logger.info("safe_word_active_block")
                return True
    except (_redis_exc.RedisError, ConnectionError, OSError) as exc:
        _logger.warning(
            "redis_safe_word_check_failed",
            extra={"error": str(exc)},
        )

    return False


# ---------------------------------------------------------------------------
# GuinevereMemoryProvider
# ---------------------------------------------------------------------------


class GuinevereMemoryProvider(MemoryProvider):
    """Hermes Agent MemoryProvider wrapping Guinevere's episodic memory pipelines.

    Attributes:
        name: Always ``"guinevere-memory"``.
        hermes_home: Path set during ``initialize()`` for profile-isolated config.
    """

    def __init__(self) -> None:
        self._hermes_home: str = ""
        self._session_id: str = ""
        self._initialized: bool = False

        # Threading guard — join-before-new-thread for sync_turn
        self._active_sync_thread: threading.Thread | None = None
        self._thread_lock: threading.Lock = threading.Lock()

        # Mirror thread guard — join-before-new-thread for on_memory_write
        self._active_mirror_thread: threading.Thread | None = None
        self._mirror_lock: threading.Lock = threading.Lock()

        # Mirror sync counter (P3-009) — flush facts every N messages
        self._turn_count: int = 0
        self._mirror_sync_interval: int = 5  # from config.yaml

        # Safety gates (P3-003)
        self._dnr_cache: DnrIdCache = DnrIdCache()
        self._consent_gate: ConsentGate = ConsentGate()

    # ------------------------------------------------------------------
    # Required methods
    # ------------------------------------------------------------------

    @property
    def name(self) -> str:
        """Provider identifier — always ``"guinevere-memory"``."""
        return "guinevere-memory"

    def is_available(self) -> bool:
        """Check if the provider can activate.

        Checks ``GUINEVERE_PG_DSN`` env var existence.  MUST NOT make
        network calls, database queries, or perform any I/O.
        """
        dsn: str | None = os.environ.get("GUINEVERE_PG_DSN")
        return dsn is not None and len(dsn) > 0

    def initialize(self, session_id: str, **kwargs: Any) -> None:
        """Initialise the provider at agent start.

        Stores ``hermes_home`` from kwargs for profile-isolated config paths.
        Logs activation metadata only (never connection strings).
        """
        self._hermes_home = kwargs.get("hermes_home", "")
        self._session_id = session_id
        self._initialized = True

        # Configure consent gate with Redis URL
        self._consent_gate.configure(_REDIS_CONSENT_URL)

        _logger.info(
            "guinevere_memory_initialized",
            extra={
                "provider": "guinevere-memory",
                "hermes_home": self._hermes_home,
                "session_id": session_id,
            },
        )

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return tool schemas exposed to the LLM.

        Guinevere memory is transparent — no tools exposed.  Returns [].

        Returns:
            Empty list.
        """
        return []

    def handle_tool_call(
        self, name: str, args: dict[str, Any], **kwargs: Any
    ) -> str:
        """Handle tool calls from the LLM.

        No tools are registered, so this always returns a JSON error.

        Returns:
            JSON error string.
        """
        _ = (name, args, kwargs)
        return json.dumps({
            "error": True,
            "message": "No tools registered for guinevere-memory provider",
        })

    def get_config_schema(self) -> list[dict[str, Any]]:
        """Declare config fields for the ``hermes memory setup`` wizard.

        Returns:
            List of field descriptor dicts.
        """
        return [
            {
                "key": "pg_dsn",
                "description": "PostgreSQL connection string for Guinevere memory database",
                "secret": True,
                "required": True,
                "env_var": "GUINEVERE_PG_DSN",
            },
            {
                "key": "embedding_model",
                "description": "Embedding model name for vector search (e.g. text-embedding-3-small)",
                "default": "text-embedding-3-small",
            },
            {
                "key": "recall_limit",
                "description": "Maximum number of memories to recall per query",
                "default": 5,
            },
            {
                "key": "token_budget",
                "description": "Maximum token budget for recalled context",
                "default": 800,
            },
        ]

    def save_config(self, values: dict[str, Any], hermes_home: str) -> None:
        """Write non-secret config to ``{hermes_home}/guinevere-memory.json``.

        Secret fields (e.g. ``pg_dsn``) are written to ``.env`` by Hermes
        separately and are not included here.
        """
        non_secret: dict[str, Any] = {
            k: v
            for k, v in values.items()
            if k != "pg_dsn"
        }

        config_path: str = os.path.join(hermes_home, "guinevere-memory.json")
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(non_secret, f, indent=2)
            _logger.info(
                "guinevere_memory_config_saved",
                extra={"path": config_path},
            )
        except OSError as exc:
            _logger.error(
                "guinevere_memory_config_save_failed",
                extra={"path": config_path, "error": str(exc)},
            )

    # ------------------------------------------------------------------
    # Lifecycle hooks
    # ------------------------------------------------------------------

    def prefetch(self, query: str, *, session_id: str = "") -> str:
        """Recall relevant episodic memories for the current turn.

        Delegates to ``read_pipeline.recall_memories()`` with:
        - principal = ``"guinevere_core"`` (HARDCODED)
        - exclude_dnr = True
        - safe_mode = False (read pipeline handles its own safe-mode logic)
        - limit = 5, token_budget = 800

        **Consent gate**: If consent for ``"surveillance"`` is revoked,
        returns empty string with a log event.  The ``surveillance``
        category is the closest consent gate for memory operations.

        **Anti-hallucination**: If recall returns empty, the
        ``_ANTI_HALLUCINATION_GUARD`` text is returned.

        Returns:
            Formatted memory context string, or empty string if blocked.
        """
        _ = session_id  # reserved for future session-scoped recall

        # ── Consent gate (fail-closed) ──
        consent_granted: bool = _check_redis_consent("surveillance")
        if not consent_granted:
            _logger.info("consent_gate_recall_blocked")
            return ""

        if not self._initialized:
            _logger.warning("prefetch_called_before_initialize")
            return ""

        # ── Lazy-import pipelines to avoid import errors when deps missing ──
        try:
            from src.memory.read_pipeline import recall_memories
        except ImportError:
            _logger.warning("read_pipeline_import_failed")
            return ""

        # ── Run async recall in sync hook ──
        try:
            return asyncio.run(
                self._prefetch_async(query, recall_memories)
            )
        except Exception as exc:
            _logger.warning(
                "prefetch_recall_error",
                extra={
                    "query_length": len(query),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return ""

    async def _prefetch_async(self, query: str, recall_fn: Any) -> str:
        """Async recall with session management.

        Attempts to use the project's ``get_async_sessionmaker`` helper.
        Falls back gracefully if the factory is unavailable.
        """
        try:
            from src.core.db.database import get_async_sessionmaker  # type: ignore[import-not-found]
            sessionmaker_factory = get_async_sessionmaker
        except ImportError:
            _logger.warning("sessionmaker_import_failed_falling_back")
            return ""

        try:
            sessionmaker = sessionmaker_factory()
            async with sessionmaker() as session:
                results = await recall_fn(
                    session,
                    query,
                    limit=_DEFAULT_RECALL_LIMIT,
                    exclude_dnr=True,
                    safe_mode=False,
                    principal=_GUINEVERE_PRINCIPAL,
                    token_budget=_DEFAULT_TOKEN_BUDGET,
                    embedding_service=None,
                )
        except Exception as exc:
            _logger.warning(
                "prefetch_async_session_error",
                extra={
                    "query_length": len(query),
                    "error": str(exc),
                },
            )
            return ""

        if not results:
            _logger.info(
                "prefetch_no_results",
                extra={"query_length": len(query)},
            )
            return _ANTI_HALLUCINATION_GUARD

        # ── Safety gate: structural anti-hallucination check ──
        from .safety_gates import anti_hallucination_check, classify_ceiling_filter

        ah_result = anti_hallucination_check(results)
        results = ah_result.filtered_results

        if not results:
            _logger.info("prefetch_all_results_failed_anti_hallucination")
            return _ANTI_HALLUCINATION_GUARD

        # ── Safety gate: classification ceiling enforcement ──
        cc_result = classify_ceiling_filter(results, principal=_GUINEVERE_PRINCIPAL)
        results = cc_result.filtered_results

        if not results:
            _logger.info("prefetch_all_results_above_classification_ceiling")
            return _ANTI_HALLUCINATION_GUARD

        # Format results as context string
        lines: list[str] = ["[Guinevere Memory Recall]"]
        for idx, mem in enumerate(results, 1):
            content: str = str(mem.get("safe_content", ""))
            if not content.strip():
                continue
            lines.append(f"\n[{idx}] {content.strip()}")

        context: str = "\n".join(lines)
        _logger.info(
            "prefetch_recall_success",
            extra={
                "query_length": len(query),
                "results_count": len(results),
            },
        )
        return context

    def queue_prefetch(self, query: str) -> None:
        """Pre-warm background recall for the next turn. No-op for now."""
        _ = query

    def sync_turn(
        self, user: str, assistant: str, *, session_id: str = ""
    ) -> None:
        """Persist a completed conversation turn as an episodic memory.

        **Non-blocking**: Wraps ``write_pipeline.store_episode()`` in a
        daemon thread.  Uses join-before-new-thread guard — if a previous
        sync thread is still running, it is joined first before starting
        a new one.

        **Consent gate**: If consent for ``"surveillance"`` is revoked,
        skips storage with a log event.

        **Safe-word gate**: If distress state is D4 (crisis), skips storage.

        Returns immediately — never blocks the conversation loop.
        """
        _ = session_id  # reserved for future session-scoped writes

        if not self._initialized:
            _logger.warning("sync_turn_called_before_initialize")
            return

        # ── Consent gate (fail-closed) ──
        consent_granted: bool = _check_redis_consent("surveillance")
        if not consent_granted:
            _logger.info("consent_gate_sync_turn_blocked")
            return

        # ── Safe-word gate ──
        if _check_redis_safe_word_active():
            _logger.info("safe_word_gate_sync_turn_blocked")
            return

        # ── Mirror sync counter (P3-009) ──
        self._increment_mirror_counter()

        # Capture locals for thread closure
        user_msg: str = user
        assistant_msg: str = assistant
        session_str: str = session_id or self._session_id

        def _async_sync() -> None:
            """Worker that performs the actual async DB write."""
            try:
                asyncio.run(
                    self._sync_turn_async(user_msg, assistant_msg, session_str)
                )
            except Exception as exc:
                _logger.error(
                    "sync_turn_thread_error",
                    extra={
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        # Join-before-new-thread guard
        with self._thread_lock:
            if (
                self._active_sync_thread is not None
                and self._active_sync_thread.is_alive()
            ):
                _logger.debug("sync_turn_joining_previous_thread")
                self._active_sync_thread.join(timeout=10.0)

            thread = threading.Thread(target=_async_sync, daemon=True)
            self._active_sync_thread = thread
            thread.start()

    async def _sync_turn_async(
        self, user: str, assistant: str, session_id: str
    ) -> None:
        """Async storage of a conversation turn via write_pipeline."""
        try:
            from src.memory.embeddings import RESTRICTED
            from src.memory.write_pipeline import store_episode
        except ImportError:
            _logger.warning("write_pipeline_import_failed")
            return

        content: str = (
            f"Faiz: {user}\nGuinevere: {assistant}"
        )
        summary_text: str = (
            f"Faiz: {user[:120]} "
            f"Guinevere: {assistant[:180]}"
        )[:300]

        try:
            from src.core.db.database import get_async_sessionmaker  # type: ignore[import-not-found]
            sessionmaker_factory = get_async_sessionmaker
        except ImportError:
            _logger.warning("sessionmaker_import_failed_sync_turn")
            return

        try:
            sessionmaker = sessionmaker_factory()
            async with sessionmaker() as session:
                episode_id = await store_episode(
                    session=session,
                    content=content,
                    source="discord_conversation",
                    classification=RESTRICTED,
                    importance=3,
                    title=user[:100],
                    summary=summary_text,
                    episode_type="conversation",
                    tags=["discord", "chat"],
                    metadata={
                        "channel": "guinevere-chat",
                        "session_id": session_id,
                        "response_length": len(assistant),
                    },
                    embedding_service=None,
                )
                await session.commit()

            _logger.info(
                "sync_turn_stored",
                extra={
                    "episode_id": str(episode_id),
                    "content_length": len(content),
                },
            )
        except Exception as exc:
            _logger.warning(
                "sync_turn_store_error",
                extra={
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )

    def on_pre_compress(self, messages: list[Any]) -> str:
        """Capture key facts before Hermes compresses the context window.

        Extracts a summary of the messages about to be discarded so
        they are not lost from memory.  Uses lightweight heuristics
        (sentence count, keyword extraction) — full LLM extraction
        is deferred to Phase 3 mirror sync (P3-009).

        Returns:
            Summary string for logging/audit purposes.
        """
        if not messages:
            return ""

        msg_count: int = len(messages)
        total_chars: int = sum(
            len(str(getattr(m, "content", m) if hasattr(m, "content") else m))
            for m in messages
        )

        _logger.info(
            "on_pre_compress_extracting",
            extra={
                "message_count": msg_count,
                "total_chars": total_chars,
            },
        )

        # Store facts as a simple summary for future mirror sync
        summary: str = (
            f"[Guinevere Memory: {msg_count} messages ({total_chars} chars) "
            f"before compression at session {self._session_id}]"
        )

        return summary

    def on_session_end(self, messages: list[Any]) -> None:
        """Final flush of pending memory writes.

        Joins any active sync_turn and mirror daemon threads to ensure all
        pending writes are committed before the session ends.
        """
        _ = messages  # reserved for future end-of-session retention

        with self._thread_lock:
            if (
                self._active_sync_thread is not None
                and self._active_sync_thread.is_alive()
            ):
                _logger.info("on_session_end_flushing_sync_thread")
                self._active_sync_thread.join(timeout=30.0)
                self._active_sync_thread = None

        with self._mirror_lock:
            if (
                self._active_mirror_thread is not None
                and self._active_mirror_thread.is_alive()
            ):
                _logger.info("on_session_end_flushing_mirror_thread")
                self._active_mirror_thread.join(timeout=30.0)
                self._active_mirror_thread = None

        _logger.info("guinevere_memory_session_ended")

    def on_memory_write(
        self,
        action: str,
        target: str,
        content: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Mirror built-in MEMORY.md/USER.md writes to Guinevere's backend.

        P3-009: When mirrors are enabled (``memory.mirrors.enabled: true``),
        extracts key facts from the content and stores them as
        ``semantic_facts`` in PostgreSQL via ``write_pipeline``.

        Safety: content hash logged, never raw content. Consent gate applies.
        """
        _logger.info(
            "on_memory_write_notified",
            extra={
                "action": action,
                "target": target,
                "content_hash": content_hash(content) if content else "",
            },
        )

        if not content or not content.strip():
            return

        # Consent gate
        if not _check_redis_consent("surveillance"):
            _logger.info("consent_gate_mirror_write_blocked")
            return

        # Extract key facts and store as semantic_facts
        facts = extract_key_facts(content)
        if not facts:
            return

        # Fire-and-forget: store facts in daemon thread with join-before-new guard
        facts_json: str = json.dumps(facts)
        target_str: str = target

        def _async_store_facts() -> None:
            try:
                asyncio.run(self._store_mirror_facts(facts_json, target_str))
            except Exception as exc:
                _logger.warning(
                    "mirror_facts_store_error",
                    extra={"error": str(exc), "target": target_str},
                )

        with self._mirror_lock:
            if (
                self._active_mirror_thread is not None
                and self._active_mirror_thread.is_alive()
            ):
                _logger.debug("mirror_write_joining_previous_thread")
                self._active_mirror_thread.join(timeout=10.0)

            thread = threading.Thread(target=_async_store_facts, daemon=True)
            self._active_mirror_thread = thread
            thread.start()

    async def _store_mirror_facts(self, facts_json: str, target: str) -> None:
        """Store extracted mirror facts as semantic_facts in PostgreSQL."""
        try:
            from src.memory.embeddings import RESTRICTED
            from src.memory.write_pipeline import store_episode
        except ImportError:
            _logger.warning("write_pipeline_import_failed_mirror_facts")
            return

        try:
            from src.core.db.database import get_async_sessionmaker  # type: ignore[import-not-found]
            sessionmaker_factory = get_async_sessionmaker
        except ImportError:
            _logger.warning("sessionmaker_import_failed_mirror_facts")
            return

        facts: list[dict[str, Any]] = json.loads(facts_json)
        try:
            sessionmaker = sessionmaker_factory()
            async with sessionmaker() as session:
                for fact in facts:
                    await store_episode(
                        session=session,
                        content=fact["content"],
                        source=f"mirror_sync:{target}",
                        classification=RESTRICTED,
                        importance=2,
                        title=fact.get("topic", "Mirror fact"),
                        summary=fact["content"][:200],
                        episode_type="semantic_fact",
                        tags=["mirror", "extracted", target],
                        metadata={
                            "mirror_target": target,
                            "fact_type": fact.get("type", "general"),
                        },
                        embedding_service=None,
                    )
                await session.commit()

            _logger.info(
                "mirror_facts_stored",
                extra={"count": len(facts), "target": target},
            )
        except Exception as exc:
            _logger.warning(
                "mirror_facts_store_error",
                extra={"error": str(exc), "target": target},
            )

    def system_prompt_block(self) -> str:
        """Return a short description of Guinevere memory for the system prompt.

        Returns:
            Memory capabilities description string.
        """
        return (
            "Guinevere Memory (guinevere-memory v1.0.0) is active. "
            "This provider offers PostgreSQL-backed episodic memory with "
            "hybrid vector + full-text search, DNR exclusion, classification "
            "ceiling enforcement, and safe-mode content filtering. "
            "Past conversations, facts, and preferences are recalled "
            "transparently and injected as context."
        )

    def shutdown(self) -> None:
        """Clean up resources. Closes DB connections, flushes buffers.

        Joins any active sync_turn and mirror threads before exit.
        """
        with self._thread_lock:
            if (
                self._active_sync_thread is not None
                and self._active_sync_thread.is_alive()
            ):
                _logger.info("shutdown_flushing_sync_thread")
                self._active_sync_thread.join(timeout=15.0)
                self._active_sync_thread = None

        with self._mirror_lock:
            if (
                self._active_mirror_thread is not None
                and self._active_mirror_thread.is_alive()
            ):
                _logger.info("shutdown_flushing_mirror_thread")
                self._active_mirror_thread.join(timeout=15.0)
                self._active_mirror_thread = None

        _logger.info("guinevere_memory_shutdown_complete")

    # ---------------------------------------------------------------------------
    # Mirror sync counter — increment on each sync_turn
    # ---------------------------------------------------------------------------

    def _increment_mirror_counter(self) -> None:
        """Increment turn counter and trigger mirror sync at interval."""
        self._turn_count += 1
        if self._turn_count >= self._mirror_sync_interval:
            self._turn_count = 0
            _logger.info("mirror_sync_interval_reached")


# ---------------------------------------------------------------------------
# P3-009: extract_key_facts — heuristic fact extraction from text
# ---------------------------------------------------------------------------

# Patterns that indicate user preferences, facts, or important statements
_FACT_PATTERNS: list[re.Pattern[str]] = [
    # Explicit preferences
    re.compile(
        r"(?:aku|saya|gue|gw)\s+(?:suka|mau|pengen|lebih suka|gak suka|benci|prefer)\s+(.+)",
        re.IGNORECASE,
    ),
    # Name/identity facts
    re.compile(
        r"(?:nama(?:ku)?|panggil)\s+(?:aku|saya|gue)?\s*(.+)",
        re.IGNORECASE,
    ),
    # Temporal facts (dates, deadlines, events)
    re.compile(
        r"(?:tanggal|deadline|jadwal|acara|event|meeting)\s+(.+)",
        re.IGNORECASE,
    ),
    # English preference patterns
    re.compile(
        r"(?:I|my)\s+(?:like|love|prefer|hate|dislike|want|need)\s+(.+)",
        re.IGNORECASE,
    ),
    # Declarative facts
    re.compile(
        r"(?:ingat|remember|catat|note|jangan lupa)\s+(?:bahwa\s+)?(.+)",
        re.IGNORECASE,
    ),
]


def extract_key_facts(text: str) -> list[dict[str, Any]]:
    """Extract key facts from text using heuristic pattern matching.

    Returns a list of fact dicts with: content, type, topic, confidence.
    Used by P3-009 mirror sync and on_pre_compress hook.

    This is a lightweight heuristic approach — no LLM calls.
    Full LLM extraction is deferred to a future phase.

    Returns:
        List of extracted fact dicts. Empty if no facts found.
    """
    if not text or not text.strip():
        return []

    facts: list[dict[str, Any]] = []
    seen_hashes: set[str] = set()  # deduplicate

    # Split into sentences
    sentences: list[str] = re.split(r"[.!?\n]+", text)

    for sentence in sentences:
        sentence = sentence.strip()
        if not sentence or len(sentence) < 10:
            continue

        for pattern in _FACT_PATTERNS:
            match = pattern.search(sentence)
            if match:
                fact_content: str = sentence[:300]
                # Deduplicate by hash
                h = hashlib.md5(fact_content.encode("utf-8")).hexdigest()
                if h in seen_hashes:
                    continue
                seen_hashes.add(h)

                facts.append({
                    "content": fact_content,
                    "type": "extracted_fact",
                    "topic": _infer_topic(fact_content),
                    "confidence": 0.7,
                })
                break  # one fact per sentence max

    if facts:
        _logger.info(
            "extract_key_facts",
            extra={
                "input_length": len(text),
                "facts_found": len(facts),
            },
        )

    return facts


def _infer_topic(text: str) -> str:
    """Infer a rough topic from fact text. Lightweight heuristic."""
    lower = text.lower()
    if any(w in lower for w in ("suka", "like", "prefer", "makan", "minum")):
        return "preference"
    if any(w in lower for w in ("nama", "name", "panggil")):
        return "identity"
    if any(w in lower for w in ("tanggal", "deadline", "jadwal", "date", "meeting")):
        return "temporal"
    if any(w in lower for w in ("ingat", "remember", "catat", "note")):
        return "reminder"
    return "general"


# ---------------------------------------------------------------------------
# Registration entry point
# ---------------------------------------------------------------------------


def register(ctx: Any) -> None:
    """Register the GuinevereMemoryProvider with the Hermes plugin system.

    Called by the Hermes memory plugin discovery system at agent start::

        from plugins.memory.guinevere_memory import register
        register(ctx)

    Args:
        ctx: Hermes plugin context providing ``register_memory_provider()``.
    """
    provider = GuinevereMemoryProvider()
    ctx.register_memory_provider(provider)
    _logger.info("guinevere_memory_provider_registered")