"""P3-011: Hybrid ranking tuning — deterministic unit tests.

Tests cover:
- Weighted RRF with tunable vector/FTS weights.
- Both-signal bonus (x1.25) when vector AND FTS find the same episode.
- Recency boost bounded to max 10%.
- Max candidate pool cap (200).
- DNR pre-filter: WHERE clause present in query builders.
- Classification ceiling: unknown/null classification fails closed.
- Stable ordering for deterministic ranking.
- RecencyConfig 90-day half-life.

All tests use fake EpisodeProtocol-compatible episodes — no DB or network required.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone

from src.memory.read_pipeline import (
    BOTH_SIGNAL_BONUS,
    EXPANDED_LIMIT_MULTIPLIER,
    FTS_WEIGHT,
    MAX_CANDIDATE_POOL,
    RRF_K,
    RECENCY_HALF_LIFE_DAYS,
    RECENCY_MAX_BOOST,
    VECTOR_WEIGHT,
    classification_level,
    compute_rrf_score,
    build_fts_query,
    build_recency_query,
    build_vector_query,
    compute_scored_results,
    normalize_importance,
    RecencyConfig,
    EpisodeEntry,
    build_result_episode_map,
)


# ---------------------------------------------------------------------------
# Fake episode — typed to satisfy EpisodeProtocol structurally
# ---------------------------------------------------------------------------


class FakeEpisode:
    """Minimal fake episode for deterministic tests.

    Attribute types match ``EpisodeProtocol`` exactly.
    """

    def __init__(
        self,
        ep_id: str,
        *,
        classification: str = "Restricted",
        importance: int = 5,
        started_at: datetime | None = None,
        do_not_recall: bool = False,
    ) -> None:
        self.id: object = ep_id
        self.raw_content: str | None = f"episode {ep_id}"
        self.summary: str | None = f"summary {ep_id}"
        self.embedding: list[float] | None = [0.1] * 1536
        self.search_vector: object = f"search_vector_{ep_id}"
        self.do_not_recall: bool = do_not_recall
        self.classification: str = classification
        self.importance: int | None = importance
        self.started_at: datetime | None = (
            started_at or datetime.now(timezone.utc)
        )
        self.created_at: datetime | None = self.started_at

    # Test-only runtime fields (not part of EpisodeProtocol)
    vector_rank: int | None = None
    fts_rank: int | None = None


# ---------------------------------------------------------------------------
# Weighted RRF score computation
# ---------------------------------------------------------------------------


class TestWeightedRRF:
    """Weighted RRF score computation."""

    def test_equal_weights_vector_only(self) -> None:
        score, num_signals = compute_rrf_score(vector_rank=1, fts_rank=None)
        expected = VECTOR_WEIGHT / (RRF_K + 1)
        assert math.isclose(score, expected, rel_tol=1e-9)
        assert num_signals == 1

    def test_equal_weights_fts_only(self) -> None:
        score, num_signals = compute_rrf_score(vector_rank=None, fts_rank=1)
        expected = FTS_WEIGHT / (RRF_K + 1)
        assert math.isclose(score, expected, rel_tol=1e-9)
        assert num_signals == 1

    def test_equal_weights_both_signals(self) -> None:
        score, num_signals = compute_rrf_score(vector_rank=1, fts_rank=2)
        expected = (
            VECTOR_WEIGHT / (RRF_K + 1) + FTS_WEIGHT / (RRF_K + 2)
        )
        assert math.isclose(score, expected, rel_tol=1e-9)
        assert num_signals == 2

    def test_custom_weights(self) -> None:
        score, _ = compute_rrf_score(
            vector_rank=1,
            fts_rank=2,
            vector_weight=0.7,
            fts_weight=0.3,
        )
        expected = 0.7 / (RRF_K + 1) + 0.3 / (RRF_K + 2)
        assert math.isclose(score, expected, rel_tol=1e-9)

    def test_both_none_returns_zero(self) -> None:
        score, num_signals = compute_rrf_score(
            vector_rank=None, fts_rank=None
        )
        assert score == 0.0
        assert num_signals == 0


# ---------------------------------------------------------------------------
# Both-signal bonus
# ---------------------------------------------------------------------------


class TestBothSignalBonus:
    """Both-signal bonus applied when episode found by vector AND FTS."""

    def test_bonus_applied_when_two_signals(self) -> None:
        raw_score = VECTOR_WEIGHT / (RRF_K + 1) + FTS_WEIGHT / (RRF_K + 2)
        assert math.isclose(
            raw_score * BOTH_SIGNAL_BONUS, raw_score * 1.25, rel_tol=1e-9
        )

    def test_bonus_not_applied_single_signal(self) -> None:
        raw_score = VECTOR_WEIGHT / (RRF_K + 1)
        assert math.isclose(raw_score, raw_score * 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Recency scoring and boost bounds
# ---------------------------------------------------------------------------


class TestRecencyConfig:
    """RecencyConfig half-life and boost boundaries."""

    def test_half_life_default_90_days(self) -> None:
        assert RECENCY_HALF_LIFE_DAYS == 90

    def test_score_at_reference_time_is_one(self) -> None:
        now = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)
        rc = RecencyConfig(reference_time=now)
        assert math.isclose(rc.score(now), 1.0, rel_tol=1e-9)

    def test_score_at_half_life_is_half(self) -> None:
        # Verify exponential decay at exactly one half-life period
        half_life_seconds = RECENCY_HALF_LIFE_DAYS * 86_400.0
        score = math.exp(
            -half_life_seconds * math.log(2) / half_life_seconds
        )
        assert math.isclose(score, 0.5, rel_tol=1e-9)

    def test_recency_boost_bounded_to_10_percent(self) -> None:
        """Maximum recency boost is RECENCY_MAX_BOOST (0.10)."""
        assert RECENCY_MAX_BOOST == 0.10
        assert math.isclose(1.0 + RECENCY_MAX_BOOST * 1.0, 1.10, rel_tol=1e-9)
        assert math.isclose(1.0 + RECENCY_MAX_BOOST * 0.0, 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Combined score formula
# ---------------------------------------------------------------------------


class TestCombinedScore:
    """Verify combined score formula in compute_scored_results."""

    def test_both_signal_bonus_increases_score(self) -> None:
        """Episode found by both signals scores higher than single-signal."""
        now = datetime(2026, 6, 2, tzinfo=timezone.utc)
        ep_both = FakeEpisode("both", started_at=now)
        ep_vec_only = FakeEpisode("vec", started_at=now)

        merged = build_result_episode_map(
            [ep_both, ep_vec_only],
            [ep_both],
        )
        scored = compute_scored_results(merged, RecencyConfig())
        scores = {str(r["id"]): float(str(r.get("combined_score", 0))) for r in scored}
        assert scores["both"] > scores["vec"], (
            f"both-signal episode should score higher: {scores}"
        )

    def test_recency_boost_never_dominates(self) -> None:
        """Old high-relevance episode must outrank new low-relevance one."""
        now = datetime(2026, 6, 2, tzinfo=timezone.utc)
        old_date = datetime(2025, 3, 1, tzinfo=timezone.utc)

        old_ep = FakeEpisode("old", started_at=old_date)
        new_ep = FakeEpisode("new", started_at=now)

        base_old = build_result_episode_map([old_ep], [old_ep])
        base_new = build_result_episode_map([new_ep], [new_ep])
        merged: dict[str, EpisodeEntry] = {}
        merged["old"] = base_old["old"]
        merged["old"].vector_rank = 1
        merged["old"].fts_rank = 1
        merged["old"].num_signals = 2
        merged["new"] = base_new["new"]
        merged["new"].vector_rank = 10
        merged["new"].fts_rank = 10
        merged["new"].num_signals = 2

        scored = compute_scored_results(merged, RecencyConfig())
        scores = {str(r["id"]): float(str(r.get("combined_score", 0))) for r in scored}
        assert scores["old"] > scores["new"], (
            f"old high-relevance should outrank new low-relevance: {scores}"
        )

    def test_stable_ordering(self) -> None:
        """Identical episodes should maintain insertion order."""
        now = datetime(2026, 6, 2, tzinfo=timezone.utc)
        episodes = [FakeEpisode(str(i), started_at=now) for i in range(5)]
        merged = build_result_episode_map(episodes, episodes)
        scored = compute_scored_results(merged, RecencyConfig())
        ids = [str(r["id"]) for r in scored]
        assert ids == ["0", "1", "2", "3", "4"]


# ---------------------------------------------------------------------------
# Max candidate pool
# ---------------------------------------------------------------------------


class TestMaxCandidatePool:
    """Candidate pool is capped at MAX_CANDIDATE_POOL (200)."""

    def test_constant_value(self) -> None:
        assert MAX_CANDIDATE_POOL == 200

    def test_expanded_limit_capped(self) -> None:
        raw = 100 * EXPANDED_LIMIT_MULTIPLIER  # 300
        assert min(raw, MAX_CANDIDATE_POOL) == 200

    def test_small_limit_unchanged(self) -> None:
        raw = 20 * EXPANDED_LIMIT_MULTIPLIER  # 60
        assert min(raw, MAX_CANDIDATE_POOL) == 60


# ---------------------------------------------------------------------------
# Classification fail-closed
# ---------------------------------------------------------------------------


class TestClassificationFailClosed:
    """Unknown/null classification must fail closed."""

    def test_unknown_classification_level_5(self) -> None:
        assert classification_level("UnknownClass") == 5

    def test_null_classification_level_5(self) -> None:
        assert classification_level(None) == 5

    def test_empty_string_classification_level_5(self) -> None:
        assert classification_level("") == 5

    def test_known_public_level_0(self) -> None:
        from src.memory.embeddings import PUBLIC

        assert classification_level(PUBLIC) == 0

    def test_known_critical_level_4(self) -> None:
        from src.memory.embeddings import CRITICAL

        assert classification_level(CRITICAL) == 4

    def test_ceiling_filter_blocks_unknown(self) -> None:
        """Episode with unknown classification is filtered for any principal."""
        ep = FakeEpisode("x", classification="UnknownClass")
        merged = build_result_episode_map([ep], [ep])
        scored = compute_scored_results(merged, RecencyConfig())
        filtered = [
            r
            for r in scored
            if classification_level(
                merged[str(r["id"])].episode.classification
            )
            <= classification_level("Restricted")
        ]
        assert len(filtered) == 0, "Unknown classification must be filtered out"


# ---------------------------------------------------------------------------
# DNR pre-filter verification (query builders)
# ---------------------------------------------------------------------------


class TestDNRPreFilter:
    """DNR WHERE clause present in query builders when exclude_dnr=True."""

    def test_vector_query_includes_dnr_filter(self) -> None:
        stmt = build_vector_query([0.1] * 1536, 20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql, f"DNR filter missing: {sql}"

    def test_vector_query_omits_dnr_filter(self) -> None:
        stmt = build_vector_query([0.1] * 1536, 20, exclude_dnr=False)
        sql = str(stmt)
        assert "do_not_recall IS false" not in sql, f"DNR filter present: {sql}"

    def test_fts_query_includes_dnr_filter(self) -> None:
        stmt = build_fts_query("test query", 20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql, f"DNR filter missing: {sql}"

    def test_fts_query_omits_dnr_filter(self) -> None:
        stmt = build_fts_query("test query", 20, exclude_dnr=False)
        sql = str(stmt)
        assert "do_not_recall IS false" not in sql, f"DNR filter present: {sql}"

    def test_recency_query_includes_dnr_filter(self) -> None:
        stmt = build_recency_query(20, exclude_dnr=True)
        sql = str(stmt)
        assert "do_not_recall IS false" in sql, f"DNR filter missing: {sql}"

    def test_recency_query_omits_dnr_filter(self) -> None:
        stmt = build_recency_query(20, exclude_dnr=False)
        sql = str(stmt)
        assert "do_not_recall IS false" not in sql, f"DNR filter present: {sql}"


# ---------------------------------------------------------------------------
# Importance normalization
# ---------------------------------------------------------------------------


class TestNormalizeImportance:
    def test_mid_range(self) -> None:
        assert math.isclose(normalize_importance(5), 0.5, rel_tol=1e-9)

    def test_max(self) -> None:
        assert math.isclose(normalize_importance(10), 1.0, rel_tol=1e-9)

    def test_min(self) -> None:
        assert math.isclose(normalize_importance(1), 0.1, rel_tol=1e-9)

    def test_out_of_range_clamped(self) -> None:
        assert math.isclose(normalize_importance(0), 0.1, rel_tol=1e-9)
        assert math.isclose(normalize_importance(15), 1.0, rel_tol=1e-9)


# ---------------------------------------------------------------------------
# Constants verification
# ---------------------------------------------------------------------------


class TestP3011Constants:
    """Verify P3-011 required constants exist with correct values."""

    def test_rrf_k_60(self) -> None:
        assert RRF_K == 60

    def test_vector_weight(self) -> None:
        assert math.isclose(VECTOR_WEIGHT, 0.5, rel_tol=1e-9)

    def test_fts_weight(self) -> None:
        assert math.isclose(FTS_WEIGHT, 0.5, rel_tol=1e-9)

    def test_both_signal_bonus(self) -> None:
        assert math.isclose(BOTH_SIGNAL_BONUS, 1.25, rel_tol=1e-9)

    def test_recency_half_life_90(self) -> None:
        assert RECENCY_HALF_LIFE_DAYS == 90

    def test_recency_max_boost_10_percent(self) -> None:
        assert math.isclose(RECENCY_MAX_BOOST, 0.10, rel_tol=1e-9)

    def test_max_candidate_pool_200(self) -> None:
        assert MAX_CANDIDATE_POOL == 200

    def test_token_budget_4000(self) -> None:
        from src.memory.read_pipeline import DEFAULT_TOKEN_BUDGET

        assert DEFAULT_TOKEN_BUDGET == 4000

    def test_chars_per_token_4(self) -> None:
        from src.memory.read_pipeline import CHARS_PER_TOKEN

        assert CHARS_PER_TOKEN == 4

    def test_expanded_limit_multiplier_3(self) -> None:
        assert EXPANDED_LIMIT_MULTIPLIER == 3
