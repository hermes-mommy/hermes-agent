"""P3-018: Memory E2E tests -- write -> recall -> inject -> verify.

Tests exercise the full memory pipeline chain:
- Write episodes via store_episode / store_episode_batch
- Recall via recall_memories with various configurations
- Verify DNR exclusion, safe-mode filtering, classification ceiling
- Verify token budget enforcement
- Verify importance-based ranking

All tests use FakeSession + AsyncMock -- no live DB or network required.
"""
from __future__ import annotations

import asyncio
import uuid
from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock

import pytest

from src.memory.embeddings import (
    CLASSIFICATION_ORDER,
    CONFIDENTIAL,
    CRITICAL,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
)
from src.memory.read_pipeline import (
    CHARS_PER_TOKEN,
    DEFAULT_TOKEN_BUDGET,
    SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER,
    SAFE_MODE_PLACEHOLDER,
    SAFE_MODE_RESTRICTED_PLACEHOLDER,
    ReadPipelineQueryError,
    ReadPipelineSafetyError,
    recall_memories,
)
from src.memory.write_pipeline import (
    WritePipelineCriticalError,
    store_episode,
    store_episode_batch,
)


# ---------------------------------------------------------------------------
# Fake embedding service -- returns deterministic vector for any text
# ---------------------------------------------------------------------------


class FakeEmbeddingService:
    """Minimal fake for EmbeddingService.aembed()."""

    async def aembed(
        self,
        text: str,
        classification: str = RESTRICTED,
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        return [0.1] * 1536


# ---------------------------------------------------------------------------
# Fake episode -- satisfies EpisodeProtocol structurally
# ---------------------------------------------------------------------------


class FakeEpisode:
    """Minimal fake episode for E2E tests.

    Attribute types match ``EpisodeProtocol`` exactly.
    """

    def __init__(
        self,
        ep_id: str | None = None,
        *,
        raw_content: str | None = "test raw content",
        summary: str | None = None,
        classification: str = RESTRICTED,
        importance: int = 5,
        do_not_recall: bool = False,
        started_at: datetime | None = None,
        tags: list[str] | None = None,
        episode_type: str | None = None,
        source: str | None = None,
    ) -> None:
        self.id: object = ep_id or str(uuid.uuid4())
        self.raw_content: str | None = raw_content
        self.summary: str | None = summary
        self.embedding: list[float] | None = [0.1] * 1536
        self.search_vector: object = f"sv_{self.id}"
        self.do_not_recall: bool = do_not_recall
        self.classification: str = classification
        self.importance: int | None = importance
        self.started_at: datetime | None = (
            started_at or datetime.now(timezone.utc)
        )
        self.created_at: datetime | None = self.started_at
        # Optional fields read via getattr by safe-mode content builder
        self.tags: list[str] | None = tags
        self.episode_type: str | None = episode_type
        self.source: str | None = source


# ---------------------------------------------------------------------------
# Fake session -- in-memory store for both read and write
# ---------------------------------------------------------------------------


class FakeScalarResult:
    """Mimics SQLAlchemy ``Result.scalars()``."""

    def __init__(self, rows: list[object]) -> None:
        self._rows = list(rows)

    def all(self) -> list[object]:
        return self._rows

    def __iter__(self) -> Any:
        return iter(self._rows)


class FakeExecuteResult:
    """Mimics SQLAlchemy execution result."""

    def __init__(self, scalars_result: FakeScalarResult) -> None:
        self._scalars_result = scalars_result

    def scalars(self) -> FakeScalarResult:
        return self._scalars_result


class FakeSession:
    """Fake async session for E2E memory tests.

    Stores episodes in a dict.  ``execute()`` returns all stored episodes
    (with optional DNR filtering based on SQL string inspection).
    ``add()`` simulates DB-assigned UUIDs on flush.
    """

    def __init__(self) -> None:
        self.episodes: dict[object, object] = {}
        self._added_objects: list[object] = []

    def add(self, obj: object) -> None:
        self._added_objects.append(obj)
        # Simulate DB assigning a UUID on insert
        if getattr(obj, "id", None) is None:
            setattr(obj, "id", uuid.uuid4())
        ep_id = getattr(obj, "id", None)
        if ep_id is not None:
            self.episodes[ep_id] = obj

    async def flush(self) -> None:
        """No-op for tests."""

    async def execute(self, statement: object) -> FakeExecuteResult:
        """Return stored episodes, filtering DNR if SQL requires it."""
        sql_str = str(statement)
        results = list(self.episodes.values())

        # Inspect SQL for DNR exclusion filter
        if "do_not_recall IS false" in sql_str:
            results = [
                e for e in results if not getattr(e, "do_not_recall", False)
            ]

        return FakeExecuteResult(FakeScalarResult(results))

    async def __aenter__(self) -> "FakeSession":
        return self

    async def __aexit__(self, *args: object) -> None:
        """Support async context manager protocol."""

    def seed(self, episode: FakeEpisode) -> None:
        """Convenience: pre-populate a FakeEpisode into the store."""
        self.episodes[episode.id] = episode


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

UTC = timezone.utc


@pytest.fixture
def fake_session() -> FakeSession:
    return FakeSession()


@pytest.fixture
def embedding_service() -> FakeEmbeddingService:
    return FakeEmbeddingService()


# ---------------------------------------------------------------------------
# TestWriteRecallRoundTrip
# ---------------------------------------------------------------------------


class TestWriteRecallRoundTrip:
    """Write an episode, recall it, verify content matches."""

    def test_write_single_episode_returns_uuid(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """store_episode returns a valid UUID."""

        async def _run() -> uuid.UUID:
            return await store_episode(
                fake_session,
                content="Hello world episode",
                source="test",
                embedding_service=embedding_service,
            )

        result = asyncio.run(_run())
        assert isinstance(result, uuid.UUID)

    def test_write_single_episode_recallable(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Episode written via store_episode is found by recall_memories."""

        async def _run() -> list[dict[str, object]]:
            await store_episode(
                fake_session,
                content="Important discussion about Python",
                source="discord",
                classification=PUBLIC,
                importance=7,
                embedding_service=embedding_service,
            )
            results = await recall_memories(
                fake_session,
                "Python discussion",
                embedding_service=embedding_service,
            )
            return results

        results = asyncio.run(_run())
        assert len(results) >= 1
        first = results[0]
        assert "Important discussion about Python" in str(first["safe_content"])

    def test_write_episode_stores_correct_classification(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Written episode preserves its classification."""

        async def _run() -> list[dict[str, object]]:
            await store_episode(
                fake_session,
                content="Internal memo content",
                source="test",
                classification=INTERNAL,
                embedding_service=embedding_service,
            )
            return await recall_memories(
                fake_session,
                "memo",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) >= 1
        assert results[0]["classification"] == INTERNAL


# ---------------------------------------------------------------------------
# TestMultiEpisodeRanking
# ---------------------------------------------------------------------------


class TestMultiEpisodeRanking:
    """Write multiple episodes, recall top-k, verify ranking order."""

    def test_recall_returns_top_k_results(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Recall respects the limit parameter."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        for i in range(10):
            fake_session.seed(
                FakeEpisode(
                    raw_content=f"Episode content number {i}",
                    classification=PUBLIC,
                    importance=5,
                    started_at=now,
                )
            )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "content",
                limit=3,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) <= 3

    def test_recall_ranking_descending_by_score(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Results are sorted by combined_score descending."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        for i in range(5):
            fake_session.seed(
                FakeEpisode(
                    raw_content=f"Ranked episode {i}",
                    classification=PUBLIC,
                    importance=5,
                    started_at=now,
                )
            )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "ranked",
                limit=5,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        scores = [float(str(r["combined_score"])) for r in results]
        assert scores == sorted(scores, reverse=True), (
            f"Scores must be descending: {scores}"
        )


# ---------------------------------------------------------------------------
# TestDNRIntegration
# ---------------------------------------------------------------------------


class TestDNRIntegration:
    """DNR-marked episodes must be excluded from recall."""

    def test_dnr_episode_excluded_from_results(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Episodes with do_not_recall=True are not returned."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        dnr_id = "dnr-ep-001"
        normal_id = "normal-ep-001"

        fake_session.seed(
            FakeEpisode(
                ep_id=dnr_id,
                raw_content="This is secret DNR content",
                classification=PUBLIC,
                do_not_recall=True,
                started_at=now,
            )
        )
        fake_session.seed(
            FakeEpisode(
                ep_id=normal_id,
                raw_content="This is normal content",
                classification=PUBLIC,
                do_not_recall=False,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "content",
                exclude_dnr=True,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        result_ids = [str(r["id"]) for r in results]
        assert dnr_id not in result_ids
        assert normal_id in result_ids

    def test_dnr_included_when_exclude_dnr_false(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """With exclude_dnr=False, DNR episodes appear in results."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        dnr_id = "dnr-ep-002"
        fake_session.seed(
            FakeEpisode(
                ep_id=dnr_id,
                raw_content="DNR content visible",
                classification=PUBLIC,
                do_not_recall=True,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "visible",
                exclude_dnr=False,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        result_ids = [str(r["id"]) for r in results]
        assert dnr_id in result_ids


# ---------------------------------------------------------------------------
# TestSafeModeIntegration
# ---------------------------------------------------------------------------


class TestSafeModeIntegration:
    """Safe-mode must filter Critical/Restricted content appropriately.

    In safe mode with guinevere_core, the classification ceiling drops to
    Internal (level 1).  Critical, Restricted, and Confidential episodes are
    filtered by the ceiling BEFORE safe_content substitution.  Only Public
    and Internal episodes pass through, where safe_content logic applies.
    """

    def test_safe_mode_filters_critical_via_ceiling(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Critical episodes are filtered by the lowered safe-mode ceiling."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        # Add a Critical episode and a Public episode
        fake_session.seed(
            FakeEpisode(
                ep_id="critical-sm",
                raw_content="TOP SECRET CRITICAL DATA",
                summary="critical summary",
                classification=CRITICAL,
                started_at=now,
            )
        )
        fake_session.seed(
            FakeEpisode(
                ep_id="public-sm",
                raw_content="Public safe data",
                summary="public summary",
                classification=PUBLIC,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "data",
                safe_mode=True,
                principal="guinevere_core",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        result_ids = [str(r["id"]) for r in results]
        # Critical must be filtered out by ceiling
        assert "critical-sm" not in result_ids
        # Public should pass through
        assert "public-sm" in result_ids

    def test_safe_mode_filters_restricted_via_ceiling(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Restricted episodes are filtered by the lowered safe-mode ceiling."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="RESTRICTED RAW SECRET",
                summary=None,
                classification=RESTRICTED,
                started_at=now,
            )
        )

        async def _run() -> None:
            # Only Restricted episodes exist; safe-mode ceiling is Internal,
            # so all are filtered and SafetyError is raised.
            with pytest.raises(ReadPipelineSafetyError):
                await recall_memories(
                    fake_session,
                    "restricted",
                    safe_mode=True,
                    principal="guinevere_core",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_safe_mode_blocks_emotional_internal_content(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Internal episodes with emotional tags get blocked placeholder."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="EMOTIONAL INTERNAL CONTENT",
                summary="emotional summary",
                classification=INTERNAL,
                tags=["emotional"],
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "emotional",
                safe_mode=True,
                principal="guinevere_core",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) >= 1
        assert results[0]["safe_content"] == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER

    def test_safe_mode_allows_public_content(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Public episodes with neutral content pass through in safe mode."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="Public neutral information",
                summary="Public summary",
                classification=PUBLIC,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "public",
                safe_mode=True,
                principal="guinevere_core",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) >= 1
        assert "Public summary" in str(results[0]["safe_content"])


# ---------------------------------------------------------------------------
# TestClassificationCeiling
# ---------------------------------------------------------------------------


class TestClassificationCeiling:
    """Unknown classification must fail closed; ceiling enforcement."""

    def test_unknown_classification_filtered(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Episodes with unknown classification are filtered by ceiling."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="Unknown class content",
                classification="UnknownClass",
                started_at=now,
            )
        )

        async def _run() -> None:
            with pytest.raises(ReadPipelineSafetyError):
                await recall_memories(
                    fake_session,
                    "unknown",
                    principal="default_principal",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_subagent_cannot_read_critical(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """guinevere_subagent principal cannot read Critical episodes."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="Critical data for subagent test",
                classification=CRITICAL,
                started_at=now,
            )
        )

        async def _run() -> None:
            with pytest.raises(ReadPipelineSafetyError):
                await recall_memories(
                    fake_session,
                    "critical subagent",
                    principal="guinevere_subagent",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_guinevere_core_can_read_critical(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """guinevere_core principal can read up to Critical."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="Critical content for core",
                classification=CRITICAL,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "critical core",
                principal="guinevere_core",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) >= 1
        assert results[0]["classification"] == CRITICAL


# ---------------------------------------------------------------------------
# TestTokenBudget
# ---------------------------------------------------------------------------


class TestTokenBudget:
    """Results must respect token budget limits."""

    def test_token_budget_truncates_results(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Large content is truncated to fit token budget."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        # Each episode has 400 chars = 100 tokens at 4 chars/token
        for i in range(5):
            fake_session.seed(
                FakeEpisode(
                    raw_content="x" * 400,
                    classification=PUBLIC,
                    importance=5,
                    started_at=now,
                )
            )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "budget test",
                limit=5,
                token_budget=250,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) <= 2, (
            f"Expected at most 2 results with 250 token budget, got {len(results)}"
        )

    def test_token_budget_zero_returns_empty(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Zero token budget returns no results."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                raw_content="Some content",
                classification=PUBLIC,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "budget zero",
                token_budget=0,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) == 0

    def test_default_token_budget_accommodates_normal(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Default 4000-token budget allows small results through."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        for i in range(3):
            fake_session.seed(
                FakeEpisode(
                    raw_content=f"Short content {i}",
                    classification=PUBLIC,
                    started_at=now,
                )
            )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "short",
                limit=3,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) == 3


# ---------------------------------------------------------------------------
# TestImportanceRanking
# ---------------------------------------------------------------------------


class TestImportanceRanking:
    """Higher importance episodes should rank higher."""

    def test_higher_importance_ranks_higher(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Episode with importance=10 outranks importance=1."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        low_id = "low-imp"
        high_id = "high-imp"

        # Low importance first in list (lower position = higher RRF rank)
        fake_session.seed(
            FakeEpisode(
                ep_id=low_id,
                raw_content="Low importance episode",
                classification=PUBLIC,
                importance=1,
                started_at=now,
            )
        )
        fake_session.seed(
            FakeEpisode(
                ep_id=high_id,
                raw_content="High importance episode",
                classification=PUBLIC,
                importance=10,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "importance",
                limit=2,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) == 2
        # High importance should be first (higher combined_score)
        assert str(results[0]["id"]) == high_id
        assert str(results[1]["id"]) == low_id

    def test_importance_boost_applied_correctly(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Verify importance affects scoring magnitude."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        fake_session.seed(
            FakeEpisode(
                ep_id="imp-5",
                raw_content="Medium importance",
                classification=PUBLIC,
                importance=5,
                started_at=now,
            )
        )
        fake_session.seed(
            FakeEpisode(
                ep_id="imp-10",
                raw_content="Max importance",
                classification=PUBLIC,
                importance=10,
                started_at=now,
            )
        )

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "importance boost",
                limit=2,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        scores = {str(r["id"]): float(str(r["combined_score"])) for r in results}
        # imp-10 should have higher score than imp-5
        assert scores["imp-10"] > scores["imp-5"]


# ---------------------------------------------------------------------------
# TestBatchWrite
# ---------------------------------------------------------------------------


class TestBatchWrite:
    """store_episode_batch must store all episodes."""

    def test_batch_write_stores_all_episodes(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """All episodes in batch are stored and recallable."""
        batch_data: list[dict[str, object]] = [
            {"content": "Batch episode one", "source": "test"},
            {"content": "Batch episode two", "source": "test"},
            {"content": "Batch episode three", "source": "test"},
        ]

        async def _run() -> list[uuid.UUID]:
            return await store_episode_batch(
                fake_session,
                batch_data,
                embedding_service=embedding_service,
            )

        ids = asyncio.run(_run())
        assert len(ids) == 3
        assert all(isinstance(uid, uuid.UUID) for uid in ids)
        # All 3 episodes should be in the session
        assert len(fake_session._added_objects) == 3

    def test_batch_write_returns_unique_uuids(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Each episode in batch gets a unique UUID."""
        batch_data: list[dict[str, object]] = [
            {"content": "Unique one", "source": "test"},
            {"content": "Unique two", "source": "test"},
        ]

        async def _run() -> list[uuid.UUID]:
            return await store_episode_batch(
                fake_session,
                batch_data,
                embedding_service=embedding_service,
            )

        ids = asyncio.run(_run())
        assert len(ids) == len(set(ids)), "All UUIDs must be unique"

    def test_batch_write_episodes_recallable(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Episodes written via batch are found by recall_memories."""

        async def _run() -> list[dict[str, object]]:
            await store_episode_batch(
                fake_session,
                [
                    {
                        "content": "Recallable batch one",
                        "source": "test",
                        "classification": PUBLIC,
                    },
                    {
                        "content": "Recallable batch two",
                        "source": "test",
                        "classification": PUBLIC,
                    },
                ],
                embedding_service=embedding_service,
            )
            return await recall_memories(
                fake_session,
                "recallable batch",
                limit=5,
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert len(results) >= 2


# ---------------------------------------------------------------------------
# TestErrorHandling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    """Empty queries, safety errors, and edge cases."""

    def test_empty_query_raises_query_error(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Empty query_text raises ReadPipelineQueryError."""

        async def _run() -> None:
            with pytest.raises(ReadPipelineQueryError):
                await recall_memories(
                    fake_session,
                    "",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_whitespace_query_raises_query_error(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Whitespace-only query_text raises ReadPipelineQueryError."""

        async def _run() -> None:
            with pytest.raises(ReadPipelineQueryError):
                await recall_memories(
                    fake_session,
                    "   ",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_all_filtered_raises_safety_error(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """All results filtered by ceiling raises ReadPipelineSafetyError."""
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=UTC)
        # Only Critical episodes, queried by subagent (ceiling=Confidential)
        fake_session.seed(
            FakeEpisode(
                raw_content="Critical only content",
                classification=CRITICAL,
                started_at=now,
            )
        )

        async def _run() -> None:
            with pytest.raises(ReadPipelineSafetyError):
                await recall_memories(
                    fake_session,
                    "critical only",
                    principal="guinevere_subagent",
                    embedding_service=embedding_service,
                )

        asyncio.run(_run())

    def test_critical_without_summary_raises_write_error(
        self, fake_session: FakeSession
    ) -> None:
        """store_episode with Critical and no summary raises WritePipelineCriticalError."""

        async def _run() -> None:
            with pytest.raises(WritePipelineCriticalError):
                await store_episode(
                    fake_session,
                    content="Critical without summary",
                    source="test",
                    classification=CRITICAL,
                )

        asyncio.run(_run())

    def test_critical_with_summary_succeeds(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """store_episode with Critical and summary succeeds."""

        async def _run() -> uuid.UUID:
            return await store_episode(
                fake_session,
                content="Critical with summary",
                source="test",
                classification=CRITICAL,
                summary="Safe summary of critical content",
                embedding_service=embedding_service,
            )

        result = asyncio.run(_run())
        assert isinstance(result, uuid.UUID)

    def test_recall_no_results_returns_empty(
        self, fake_session: FakeSession, embedding_service: FakeEmbeddingService
    ) -> None:
        """Empty session returns empty results (no safety error)."""

        async def _run() -> list[dict[str, object]]:
            return await recall_memories(
                fake_session,
                "nothing here",
                embedding_service=embedding_service,
            )

        results = asyncio.run(_run())
        assert results == []
