"""Consciousness Memory Bridge — thought persistence and recall.

Bridges ThoughtStream with HermesMemoryBridge for thought persistence.
All thoughts are recorded via HermesMemoryBridge (the existing production
memory pipeline). High-confidence thoughts (confidence > 0.9) are flagged
for priority storage.

Design decisions:
  - Composition over inheritance: wraps HermesMemoryBridge, does not subclass.
  - Thread-safe: asyncio.Lock guards write operations.
  - Fire-and-forget: all record operations are non-blocking to thought stream.
  - Graceful degradation: falls back to InMemoryThoughtStore when bridge unavailable.
  - No direct DB writes: always delegates through HermesMemoryBridge.
  - No raw secrets stored in memory.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from guinevere.consciousness.state import ConsciousnessState
    from guinevere.hermes._memory_bridge import HermesMemoryBridge

from guinevere.consciousness.thought import Thought, ThoughtType

_logger = logging.getLogger(__name__)

# Threshold for high-confidence priority flagging.
_HIGH_CONFIDENCE_THRESHOLD: float = 0.9

# Maximum in-memory thoughts before eviction.
_MAX_STORE_SIZE: int = 1000


# ---------------------------------------------------------------------------
# InMemoryThoughtStore — degraded mode fallback
# ---------------------------------------------------------------------------


class InMemoryThoughtStore:
    """Simple dict-based in-memory thought store for degraded mode.

    Stores thought_id -> {type, content, confidence, timestamp,
    affect_snapshot, acted}.  Capped at 1000 thoughts with oldest-first
    auto-eviction.  Supports recall_by_type and recall_recent.
    """

    def __init__(self) -> None:
        self._store: dict[str, dict[str, object]] = {}
        # Ordered list for oldest-first eviction (append = newest last).
        self._order: list[str] = []

    @property
    def count(self) -> int:
        """Return number of stored thoughts."""
        return len(self._store)

    def put(self, thought: Thought, thought_id: str) -> None:
        """Store a thought with oldest-first eviction when capped."""
        self._store[thought_id] = {
            "type": thought.type.value,
            "content": thought.content,
            "confidence": thought.confidence,
            "timestamp": thought.timestamp.isoformat(),
            "affect_snapshot": dict(thought.affect_snapshot),
            "acted": thought.acted,
        }
        self._order.append(thought_id)

        # Evict oldest when over cap.
        while len(self._store) > _MAX_STORE_SIZE:
            old_id = self._order.pop(0)
            self._store.pop(old_id, None)

    def recall_by_type(
        self, thought_type: ThoughtType, limit: int = 10,
    ) -> list[dict[str, object]]:
        """Retrieve recent thoughts of a given type (most recent first)."""
        results: list[dict[str, object]] = []
        type_value = thought_type.value
        for thought_id in reversed(self._order):
            entry = self._store.get(thought_id)
            if entry is not None and entry["type"] == type_value:
                results.append({"id": thought_id, **entry})
                if len(results) >= limit:
                    break
        return results

    def recall_recent(
        self, minutes: int = 60, limit: int = 20,
    ) -> list[dict[str, object]]:
        """Retrieve thoughts from the last N minutes (most recent first)."""
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
        cutoff_iso = cutoff.isoformat()
        results: list[dict[str, object]] = []
        for thought_id in reversed(self._order):
            entry = self._store.get(thought_id)
            if entry is None:
                continue
            ts = entry.get("timestamp", "")
            if isinstance(ts, str) and ts >= cutoff_iso:
                results.append({"id": thought_id, **entry})
                if len(results) >= limit:
                    break
        return results


# ---------------------------------------------------------------------------
# ConsciousnessMemoryBridge
# ---------------------------------------------------------------------------


class ConsciousnessMemoryBridge:
    """Bridges ThoughtStream with HermesMemoryBridge for thought persistence.

    All thoughts are recorded via HermesMemoryBridge (the existing production
    memory pipeline). High-confidence thoughts (confidence > 0.9) are flagged
    for priority storage.

    Methods:
    - record_thought(thought): persist a single thought to memory
    - recall_by_type(thought_type, limit): retrieve thoughts by ThoughtType
    - recall_recent(minutes, limit): retrieve recent thoughts by time
    - consolidate(): Periodic memory consolidation — reflection-type thoughts
      extract patterns from memory
    - recall_for_context(query, limit): bridge to HermesMemoryBridge.recall_for_context
    """

    def __init__(
        self,
        memory_bridge: HermesMemoryBridge | None = None,
    ) -> None:
        """Initialise the consciousness memory bridge.

        Args:
            memory_bridge: Production HermesMemoryBridge instance.  If None,
                operates in degraded mode using InMemoryThoughtStore only.
        """
        self._bridge: HermesMemoryBridge | None = memory_bridge
        self._fallback_store: InMemoryThoughtStore = InMemoryThoughtStore()
        self._lock: asyncio.Lock = asyncio.Lock()
        self._total_recorded: int = 0
        self._high_confidence_count: int = 0
        self._consolidation_count: int = 0

    # ── public properties ───────────────────────────────────

    @property
    def total_recorded(self) -> int:
        """Return total number of thoughts recorded (prod + fallback)."""
        return self._total_recorded

    @property
    def using_production_bridge(self) -> bool:
        """Return True if production HermesMemoryBridge is available."""
        return self._bridge is not None

    # ── WRITE path (fire-and-forget) ────────────────────────

    async def record_thought(self, thought: Thought) -> str | None:
        """Persist a single thought to memory (fire-and-forget safe).

        If HermesMemoryBridge is available, stores via store_conversation.
        Always caches in InMemoryThoughtStore for type/time-based recall.
        High-confidence thoughts (confidence > 0.9) are flagged with
        importance metadata.

        Args:
            thought: The Thought to persist.

        Returns:
            Episode UUID string on success (prod mode), thought_id string
            (degraded mode), or None on error.
        """
        thought_id: str = uuid.uuid4().hex
        is_high_confidence: bool = thought.confidence > _HIGH_CONFIDENCE_THRESHOLD

        # Always cache locally for recall_by_type / recall_recent.
        self._fallback_store.put(thought, thought_id)

        # Attempt production persistence.
        episode_id: str | None = None
        if self._bridge is not None:
            try:
                # Build content with type tag for FTS searchability.
                content = f"[{thought.type.value}] {thought.content}"
                importance_tag = " [HIGH_CONFIDENCE]" if is_high_confidence else ""
                user_msg = f"consciousness:{thought.type.value}{importance_tag}"
                assistant_msg = content

                async with self._lock:
                    episode_id = await self._bridge.store_conversation(
                        user_message=user_msg,
                        assistant_response=assistant_msg,
                        user_id_hash="guinevere_consciousness",
                        safe_mode=False,
                    )
            except Exception as exc:
                _logger.warning(
                    "memory_bridge.record_thought.prod_failed",
                    extra={
                        "thought_type": thought.type.value,
                        "error": str(exc),
                    },
                )
                # Graceful degradation: local store already updated above.

        # Update metrics.
        self._total_recorded += 1
        if is_high_confidence:
            self._high_confidence_count += 1

        return episode_id or thought_id

    # ── READ path ───────────────────────────────────────────

    async def recall_by_type(
        self,
        thought_type: ThoughtType,
        limit: int = 10,
    ) -> list[dict[str, object]]:
        """Retrieve thoughts by ThoughtType.

        Uses InMemoryThoughtStore (always available). Falls back to
        HermesMemoryBridge.recall_for_context with type filter when
        in-memory store is empty (e.g. after restart in prod mode).

        Args:
            thought_type: The ThoughtType to filter by.
            limit: Maximum number of results. Default 10.

        Returns:
            List of thought dicts (most recent first). Empty on error.
        """
        # Try in-memory store first (most accurate for type filtering).
        results = self._fallback_store.recall_by_type(thought_type, limit)
        if results:
            return results

        # Fallback to production bridge with type as search query.
        if self._bridge is not None:
            try:
                raw = await self._bridge.recall_for_context(
                    query=f"thought type:{thought_type.value}",
                    limit=limit,
                )
                # Filter to matching type (bridge returns generic results).
                return [
                    r for r in raw
                    if thought_type.value in str(r.get("safe_content", ""))
                ]
            except Exception as exc:
                _logger.warning(
                    "memory_bridge.recall_by_type.prod_failed",
                    extra={
                        "thought_type": thought_type.value,
                        "error": str(exc),
                    },
                )

        return []

    async def recall_recent(
        self,
        minutes: int = 60,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        """Retrieve recent thoughts by time window.

        Uses InMemoryThoughtStore (always available). Falls back to
        HermesMemoryBridge.recall_for_context when in-memory store is
        empty.

        Args:
            minutes: Lookback window in minutes. Default 60.
            limit: Maximum number of results. Default 20.

        Returns:
            List of thought dicts (most recent first). Empty on error.
        """
        # Try in-memory store first.
        results = self._fallback_store.recall_recent(minutes, limit)
        if results:
            return results

        # Fallback to production bridge.
        if self._bridge is not None:
            try:
                return await self._bridge.recall_for_context(
                    query=f"thoughts from the last {minutes} minutes",
                    limit=limit,
                )
            except Exception as exc:
                _logger.warning(
                    "memory_bridge.recall_recent.prod_failed",
                    extra={"minutes": minutes, "error": str(exc)},
                )

        return []

    # ── CONSOLIDATION (periodic, fire-and-forget) ───────────

    async def consolidate(self, state: ConsciousnessState) -> dict[str, object]:
        """Periodic memory consolidation — extract patterns from recent thoughts.

        Reviews recent reflection-type thoughts, builds a consolidation
        summary, and stores it via HermesMemoryBridge.store_conversation.
        If patterns are detected, updates state.self_story.

        Designed to be called periodically (e.g. every N thought cycles)
        and to run as a fire-and-forget asyncio.Task.

        Args:
            state: The current ConsciousnessState.

        Returns:
            Dict with consolidation metadata: {
                "consolidated": int,
                "patterns_found": int,
                "episode_id": str | None,
                "story_updated": bool,
            }
        """
        result: dict[str, object] = {
            "consolidated": 0,
            "patterns_found": 0,
            "episode_id": None,
            "story_updated": False,
        }

        # Gather recent reflection-type thoughts.
        reflection_thoughts = self._fallback_store.recall_by_type(
            ThoughtType.REFLECTION, limit=10,
        )

        if not reflection_thoughts:
            return result

        # Build consolidation summary.
        consolidated_count = len(reflection_thoughts)
        summary_lines: list[str] = []
        for entry in reflection_thoughts:
            content = entry.get("content", "")
            if isinstance(content, str) and content:
                summary_lines.append(f"- {content[:200]}")

        if not summary_lines:
            return result

        consolidation_text = "\n".join(summary_lines)

        result["consolidated"] = consolidated_count
        result["patterns_found"] = len(summary_lines)

        # Store consolidation summary via production bridge.
        episode_id: str | None = None
        if self._bridge is not None:
            try:
                episode_id = await self._bridge.store_conversation(
                    user_message="consciousness:consolidation",
                    assistant_response=(
                        f"[consolidation] Extracted {consolidated_count} "
                        f"reflection patterns:\n{consolidation_text}"
                    ),
                    user_id_hash="guinevere_consciousness",
                    safe_mode=False,
                )
                result["episode_id"] = episode_id
            except Exception as exc:
                _logger.warning(
                    "memory_bridge.consolidate.store_failed",
                    extra={"error": str(exc)},
                )

        # Update self_story if meaningful patterns detected.
        if consolidated_count >= 3:
            new_insight = summary_lines[0][:100] if summary_lines else ""
            if new_insight:
                state.self_story = (
                    f"{state.self_story} Recent reflection: {new_insight}"
                )
                result["story_updated"] = True

        self._consolidation_count += 1

        return result

    # ── CONTEXT RECALL (direct bridge delegation) ───────────

    async def recall_for_context(
        self,
        query: str,
        limit: int = 5,
    ) -> list[dict[str, object]]:
        """Bridge to HermesMemoryBridge.recall_for_context.

        Returns relevant episodic memories for the given query.
        In degraded mode, falls back to in-memory store (returns
        most recent thoughts regardless of query).

        Args:
            query: Natural-language query for memory search.
            limit: Maximum number of results. Default 5.

        Returns:
            List of memory dicts. Empty on error.
        """
        if self._bridge is not None:
            try:
                return await self._bridge.recall_for_context(
                    query=query,
                    limit=limit,
                )
            except Exception as exc:
                _logger.warning(
                    "memory_bridge.recall_for_context.failed",
                    extra={"query_length": len(query), "error": str(exc)},
                )

        # Degraded mode: return recent thoughts from local store.
        return self._fallback_store.recall_recent(minutes=1440, limit=limit)
