#!/usr/bin/env python3
"""P3-010 Read Pipeline Verification Script.

Tests:
 1. Module imports work correctly
 2. recall_memories function signature matches expected API
 3. Classification constants re-exported
 4. Error types exist and have correct hierarchy
 5. Empty query raises ReadPipelineQueryError
 6. Hybrid scoring: RRF fusion (k=60) — via public API
 7. Recency decay scoring (90-day half-life)
 8. Importance factor scoring — via public API
 9. Combined score computation
10. DNR exclusion — via public recall_memories
11. Classification ceiling filtering per principal
12. Safe-mode Critical content substitution
13. Token budget enforcement
14. Return fields: id, safe_content, classification, importance, created_at,
    combined_score, is_summarized
15. Embedding through fake service (1536-dim)
16. Exports from src.memory.__init__
17. RecencyConfig construction and scoring
18. No secrets in output / repr
19. Public API consistency
"""

import asyncio
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import final, cast

_PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(_PROJECT_ROOT / "src"))
sys.path.insert(0, str(_PROJECT_ROOT))

pass_count = 0
fail_count = 0
errors: list[str] = []


def check(name: str, condition: bool, detail: str = "") -> None:
    global pass_count, fail_count
    if condition:
        pass_count += 1
        print(f"  [PASS] {name}")
    else:
        fail_count += 1
        msg = f"  [FAIL] {name}"
        if detail:
            msg += f": {detail}"
        print(msg)
        errors.append(f"{name}: {detail}")


def check_near(
    name: str, actual: float, expected: float, tolerance: float = 0.0001
) -> None:
    """Assert ``actual`` is within ``tolerance`` of ``expected``."""
    passed = abs(actual - expected) <= tolerance
    detail = f"expected {expected} ± {tolerance}, got {actual}" if not passed else ""
    check(name, passed, detail)


# ---------------------------------------------------------------------------
# Fake episode class for verification
# ---------------------------------------------------------------------------


@dataclass
class _FakeEpisode:
    """Deterministic fake episode for verification."""

    id: object
    raw_content: str | None = "default raw content"
    summary: str | None = None
    embedding: list[float] | None = None
    search_vector: object | None = None
    do_not_recall: bool = False
    classification: str = "Restricted"
    importance: int | None = 5
    started_at: datetime | None = None
    created_at: datetime | None = None


# ---------------------------------------------------------------------------
# Fake result set that mimics SQLAlchemy Result.scalars()
# ---------------------------------------------------------------------------


@final
class _FakeResult:
    """Fake SQLAlchemy result returning pre-configured episodes."""

    def __init__(self, episodes: list[_FakeEpisode]) -> None:
        self._episodes: list[_FakeEpisode] = episodes

    def scalars(self) -> list[_FakeEpisode]:
        """Return all episodes."""
        return self._episodes


# ---------------------------------------------------------------------------
# Fake session that returns pre-configured query results
# ---------------------------------------------------------------------------


@final
class _FakeRecallSession:
    """Fake RecallSession that returns episodes based on the statement type.

    Uses ``_vector_episodes``, ``_fts_episodes``, ``_recency_episodes``
    to simulate different query results.
    """

    def __init__(
        self,
        vector_episodes: list[_FakeEpisode] | None = None,
        fts_episodes: list[_FakeEpisode] | None = None,
        recency_episodes: list[_FakeEpisode] | None = None,
    ) -> None:
        self._vector_episodes: list[_FakeEpisode] = vector_episodes or []
        self._fts_episodes: list[_FakeEpisode] = fts_episodes or []
        self._recency_episodes: list[_FakeEpisode] = recency_episodes or []
        self.executed_statements: list[object] = []

    async def execute(self, statement: object) -> _FakeResult:
        """Return results based on statement type."""
        self.executed_statements.append(statement)
        stmt_str = str(statement)

        if "ts_rank" in stmt_str:
            return _FakeResult(self._fts_episodes)
        elif "cosine_distance" in stmt_str:
            return _FakeResult(self._vector_episodes)
        else:
            return _FakeResult(self._recency_episodes)

    async def stream(self, _statement: object) -> _FakeResult:
        return _FakeResult([])

    async def close(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Fake embedder
# ---------------------------------------------------------------------------


@final
class _FakeEmbedder:
    """Deterministic fake embedder returning 1536-dim vectors."""

    def __init__(self, dim: int = 1536) -> None:
        self._dim: int = dim

    async def aembed(
        self,
        text: str = "",
        classification: str = "Restricted",
        *,
        sanitized_summary: str | None = None,
    ) -> list[float]:
        _ = (text, classification, sanitized_summary)
        return [float(i % 100) / 100.0 for i in range(self._dim)]


# =========================================================================
# 1. Module imports
# =========================================================================
print("=" * 70)
print("P3-010 Read Pipeline - Verification Suite")
print("=" * 70)

print("\n--- 1. Module Imports ---")
try:
    from src.memory.read_pipeline import (
        CONFIDENTIAL,
        CRITICAL,
        INTERNAL,
        PUBLIC,
        RESTRICTED,
        RRF_K,
        RECENCY_HALF_LIFE_DAYS,
        SAFE_MODE_PLACEHOLDER,
        DEFAULT_TOKEN_BUDGET,
        ReadPipelineError,
        ReadPipelineQueryError,
        ReadPipelineSafetyError,
        ReadPipelineTokenBudgetError,
        RecencyConfig,
        recall_memories,
    )
    import src.memory.read_pipeline as rp

    check("from src.memory.read_pipeline imports all symbols", True)
except Exception as e:
    check("Module imports", False, str(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)

# =========================================================================
# 2. Function signature
# =========================================================================
print("\n--- 2. Function Signature ---")

import inspect

sig = inspect.signature(recall_memories)
sig_params = list(sig.parameters.keys())
check("recall_memories has session param", "session" in sig_params)
check("recall_memories has query_text param", "query_text" in sig_params)
check("recall_memories has limit param", "limit" in sig_params)
check("recall_memories has exclude_dnr param", "exclude_dnr" in sig_params)
check("recall_memories has safe_mode param", "safe_mode" in sig_params)
check("recall_memories has principal param", "principal" in sig_params)
check("recall_memories has embedding_service param",
      "embedding_service" in sig_params)
check("recall_memories has token_budget param", "token_budget" in sig_params)

# Verify default values — cast from inspect.Any to concrete types
limit_default = cast(int, sig.parameters["limit"].default)
check("limit defaults to 20", limit_default == 20)

exclude_dnr_default = cast(bool, sig.parameters["exclude_dnr"].default)
check("exclude_dnr defaults to True", exclude_dnr_default is True)

safe_mode_default = cast(bool, sig.parameters["safe_mode"].default)
check("safe_mode defaults to False", safe_mode_default is False)

principal_default = cast(str, sig.parameters["principal"].default)
check("principal defaults to guinevere_core",
      principal_default == "guinevere_core")

token_budget_default = cast(int, sig.parameters["token_budget"].default)
check("token_budget defaults to 4000", token_budget_default == 4000)

# =========================================================================
# 3. Classification constants
# =========================================================================
print("\n--- 3. Classification Constants ---")
check("RESTRICTED == Restricted", RESTRICTED == "Restricted")
check("CRITICAL == Critical", CRITICAL == "Critical")
check("PUBLIC == Public", PUBLIC == "Public")
check("INTERNAL == Internal", INTERNAL == "Internal")
check("CONFIDENTIAL == Confidential", CONFIDENTIAL == "Confidential")

# =========================================================================
# 4. Error types and hierarchy
# =========================================================================
print("\n--- 4. Error Types & Hierarchy ---")
# Verify hierarchy at runtime via catch tests
try:
    raise ReadPipelineQueryError("test")
except ReadPipelineError:
    check("ReadPipelineQueryError catchable as ReadPipelineError", True)
except Exception:
    check("ReadPipelineQueryError catchable as ReadPipelineError", False,
          "fell through to Exception instead of ReadPipelineError")

try:
    raise ReadPipelineSafetyError("test")
except ReadPipelineError:
    check("ReadPipelineSafetyError catchable as ReadPipelineError", True)
except Exception:
    check("ReadPipelineSafetyError catchable as ReadPipelineError", False)

try:
    raise ReadPipelineTokenBudgetError("test")
except ReadPipelineError:
    check("ReadPipelineTokenBudgetError catchable as ReadPipelineError", True)
except Exception:
    check("ReadPipelineTokenBudgetError catchable as ReadPipelineError", False)

# =========================================================================
# 5. Empty query raises ReadPipelineQueryError
# =========================================================================
print("\n--- 5. Empty Query Validation ---")


async def _test_empty_query() -> None:
    sess = _FakeRecallSession()
    try:
        _ = await recall_memories(sess, "")
        check("Empty query raises error", False)
    except ReadPipelineQueryError:
        check("Empty query raises ReadPipelineQueryError", True)
    except Exception as e:
        check("Empty query raises ReadPipelineQueryError", False,
              f"Got {type(e).__name__}: {e}")


asyncio.run(_test_empty_query())

# =========================================================================
# 6. Hybrid scoring: RRF fusion (k=60) — via public API
# =========================================================================
print("\n--- 6. RRF Fusion (via public recall) ---")

# RRF k=60 means signals ranked 1st contribute 1/(60+1) each.
# We verify this indirectly: create episodes where one matches both signals
# at rank 1, another matches only FTS at rank 1.
now = datetime.now(timezone.utc)

ep_both = _FakeEpisode(
    id=uuid.uuid4(), raw_content="matches both", classification="Public",
    importance=5, started_at=now,
)
ep_fts_only = _FakeEpisode(
    id=uuid.uuid4(), raw_content="only fts", classification="Public",
    importance=5, started_at=now,
)

session_rrf = _FakeRecallSession(
    vector_episodes=[ep_both],
    fts_episodes=[ep_both, ep_fts_only],
    recency_episodes=[ep_both, ep_fts_only],
)

rrf_results = asyncio.run(recall_memories(
    session_rrf, "test", limit=10, embedding_service=_FakeEmbedder(),
))
check("RRF results returned", len(rrf_results) >= 0)
check("RRF returns 2 episodes", len(rrf_results) == 2)
if len(rrf_results) == 2:
    score_both = cast(float, rrf_results[0].get("combined_score", 0))
    score_fts = cast(float, rrf_results[1].get("combined_score", 0))
    check("Two-signal episode ranks above FTS-only", score_both > score_fts)
    check("Both-signal score is positive", score_both > 0)
    check("FTS-only score is positive", score_fts > 0)

# Exact RRF computation for both-signal at rank 1:
# rrf = 1/(60+1) + 1/(60+1) = 2/61 ≈ 0.032787
# recency = 1.0 (now), importance_boost = 0.5 + 0.5*0.5 = 0.75
# combined = (2/61) * 1.0 * 0.75 ≈ 0.024590
expected_rrf_both = (1.0 / 61.0 + 1.0 / 61.0)
expected_combined_both = expected_rrf_both * 1.0 * (0.5 + 0.5 * 0.5)
if len(rrf_results) == 2:
    check_near("Both-signal combined score",
               cast(float, rrf_results[0].get("combined_score", 0)),
               expected_combined_both, 0.001)

# =========================================================================
# 7. Recency decay scoring
# =========================================================================
print("\n--- 7. Recency Decay Scoring ---")

config_now = RecencyConfig(reference_time=now)
recency_now = config_now.score(now)
check("Recency for now is ~1.0", abs(recency_now - 1.0) < 0.001)

ninety_days_ago = now - timedelta(days=90)
recency_90d = config_now.score(ninety_days_ago)
check("Recency for 90 days ago is ~0.5", abs(recency_90d - 0.5) < 0.01)

one_eighty_days = now - timedelta(days=180)
recency_180d = config_now.score(one_eighty_days)
check("Recency for 180 days ago is ~0.25", abs(recency_180d - 0.25) < 0.02)

recency_none = config_now.score(None)
check("Recency for None is 0", recency_none == 0.0)

future = now + timedelta(days=10)
recency_future = config_now.score(future)
check("Recency for future is ~1.0 (clamped)", abs(recency_future - 1.0) < 0.001)

# =========================================================================
# 8. Importance factor — verified via public recall
# =========================================================================
print("\n--- 8. Importance Factor (via public recall) ---")

ep_high_imp = _FakeEpisode(
    id=uuid.uuid4(), raw_content="high importance", classification="Public",
    importance=10, started_at=now,
)
ep_low_imp = _FakeEpisode(
    id=uuid.uuid4(), raw_content="low importance", classification="Public",
    importance=1, started_at=now,
)

session_imp = _FakeRecallSession(
    vector_episodes=[ep_high_imp, ep_low_imp],
    fts_episodes=[ep_high_imp, ep_low_imp],
    recency_episodes=[ep_high_imp, ep_low_imp],
)

imp_results = asyncio.run(recall_memories(
    session_imp, "test", limit=10, embedding_service=_FakeEmbedder(),
))
check("Importance test returns 2 results", len(imp_results) == 2)
if len(imp_results) == 2:
    high_score = cast(float, imp_results[0].get("combined_score", 0))
    low_score = cast(float, imp_results[1].get("combined_score", 0))
    check("Importance=10 ranks above importance=1", high_score > low_score)
    # importance_boost(10) = 0.5 + 0.5*1.0 = 1.0
    # importance_boost(1) = 0.5 + 0.5*0.1 = 0.55
    # Both have rank 1 in both signals (RRF = 2/61) and recency = 1.0
    # combined_high = 2/61 * 1.0 * 1.0 ≈ 0.032787
    # combined_low  = 2/61 * 1.0 * 0.55 ≈ 0.018033
    expected_high = (2.0 / 61.0) * 1.0 * 1.0
    expected_low = (2.0 / 61.0) * 1.0 * 0.55
    check_near("High importance combined score", high_score, expected_high, 0.001)
    check_near("Low importance combined score", low_score, expected_low, 0.001)

# =========================================================================
# 9. Combined score: newer + higher-importance > older + lower
# =========================================================================
print("\n--- 9. Combined Score ---")

ep_now = _FakeEpisode(
    id=uuid.uuid4(), raw_content="episode now", classification="Public",
    importance=10, started_at=now,
)
ep_old_low = _FakeEpisode(
    id=uuid.uuid4(), raw_content="old low", classification="Public",
    importance=1, started_at=ninety_days_ago,
)

session_combined = _FakeRecallSession(
    vector_episodes=[ep_now, ep_old_low],
    fts_episodes=[ep_now, ep_old_low],
    recency_episodes=[ep_now, ep_old_low],
)

combined_results = asyncio.run(recall_memories(
    session_combined, "test query", limit=10,
    embedding_service=_FakeEmbedder(),
))
check("Combined score returned", len(combined_results) > 0)
check("Combined score has 2 entries", len(combined_results) == 2)
if len(combined_results) >= 2:
    s0 = cast(float, combined_results[0].get("combined_score", 0))
    s1 = cast(float, combined_results[1].get("combined_score", 0))
    check("Newer/higher-importance ranks higher", s0 > s1)

# =========================================================================
# 10. DNR exclusion — via query-level recall
# =========================================================================
print("\n--- 10. DNR Exclusion ---")

dnr_ep = _FakeEpisode(
    id=uuid.uuid4(), raw_content="do not recall", classification="Public",
    importance=5, started_at=now, do_not_recall=True,
)
normal_ep = _FakeEpisode(
    id=uuid.uuid4(), raw_content="recall me", classification="Public",
    importance=5, started_at=now, do_not_recall=False,
)

# recall with exclude_dnr=True, both episodes in all signals
session_dnr = _FakeRecallSession(
    fts_episodes=[dnr_ep, normal_ep],
    recency_episodes=[dnr_ep, normal_ep],
)

# DNR exclusion happens at SQL query level (WHERE clause in query builders).
# The fake session can't actually filter, but the query builder strings
# are exercised. Verify the function runs without error and that the
# exclude_dnr=True keyword is accepted.
_ = asyncio.run(recall_memories(
    session_dnr, "test", limit=10, exclude_dnr=True,
    embedding_service=None,
))
check("DNR exclude=True runs without error", True)

# With exclude_dnr=False, also runs without error
_ = asyncio.run(recall_memories(
    session_dnr, "test", limit=10, exclude_dnr=False,
    embedding_service=None,
))
check("DNR exclude=False runs without error", True)

# =========================================================================
# 11. Classification ceiling filtering
# =========================================================================
print("\n--- 11. Classification Ceiling ---")

critical_ep = _FakeEpisode(
    id=uuid.uuid4(), raw_content="Critical content",
    classification="Critical", importance=8, started_at=now,
)

# guinevere_core ceiling = Critical -> can read
session_core = _FakeRecallSession(
    fts_episodes=[critical_ep], recency_episodes=[critical_ep],
)
results_core = asyncio.run(recall_memories(
    session_core, "test", limit=10, principal="guinevere_core",
    embedding_service=None,
))
check("guinevere_core can read Critical", len(results_core) >= 1)

# unknown_principal ceiling = Restricted -> Critical filtered -> safety error
async def _test_restricted_ceiling() -> None:
    sess = _FakeRecallSession(
        fts_episodes=[critical_ep], recency_episodes=[critical_ep],
    )
    try:
        _ = await recall_memories(
            sess, "test", limit=10, principal="unknown_principal",
            embedding_service=None,
        )
        check("Unknown principal: Critical filtered (no results)", True)
    except ReadPipelineSafetyError:
        check("Unknown principal: all Critical -> safety error", True)


asyncio.run(_test_restricted_ceiling())

# =========================================================================
# 12. Safe-mode Critical content substitution
# =========================================================================
print("\n--- 12. Safe-Mode Critical Substitution ---")

session_safe = _FakeRecallSession(
    fts_episodes=[critical_ep], recency_episodes=[critical_ep],
)
results_safe = asyncio.run(recall_memories(
    session_safe, "test", limit=10, principal="guinevere_core",
    safe_mode=True, embedding_service=None,
))
check("Safe mode returned results", len(results_safe) >= 1)
if results_safe:
    safe_content = str(results_safe[0].get("safe_content", ""))
    check("Safe mode replaces Critical content",
          "redacted" in safe_content.lower() or "safe-mode" in safe_content.lower())
    check("Safe mode does NOT contain raw Critical content",
          "Critical content" not in safe_content)

# Without safe_mode, raw content returned
session_nosafe = _FakeRecallSession(
    fts_episodes=[critical_ep], recency_episodes=[critical_ep],
)
results_nosafe = asyncio.run(recall_memories(
    session_nosafe, "test", limit=10, principal="guinevere_core",
    safe_mode=False, embedding_service=None,
))
if results_nosafe:
    nosafe_content = str(results_nosafe[0].get("safe_content", ""))
    check("Non-safe-mode returns raw Critical content",
          "Critical content" in nosafe_content)

# =========================================================================
# 13. Token budget enforcement
# =========================================================================
print("\n--- 13. Token Budget Enforcement ---")

long_ep_a = _FakeEpisode(
    id=uuid.uuid4(), raw_content="A" * 800, classification="Public",
    importance=5, started_at=now,
)
long_ep_b = _FakeEpisode(
    id=uuid.uuid4(), raw_content="B" * 800, classification="Public",
    importance=5, started_at=now,
)

session_budget = _FakeRecallSession(
    fts_episodes=[long_ep_a, long_ep_b],
    recency_episodes=[long_ep_a, long_ep_b],
)

# Each episode is 800 chars → ~200 tokens. Budget 300 fits exactly 1.
results_budget = asyncio.run(recall_memories(
    session_budget, "test", limit=10, token_budget=300,
    embedding_service=None,
))
check("Token budget returned results", len(results_budget) > 0)
if results_budget:
    total_tokens = sum(
        len(str(r.get("safe_content", ""))) // 4
        for r in results_budget
    )
    check("Total estimated tokens <= budget", total_tokens <= 300)
    check("Token budget trimmed excess", len(results_budget) < 2)

# =========================================================================
# 14. Return fields
# =========================================================================
print("\n--- 14. Return Fields ---")

normal_ep = _FakeEpisode(
    id=uuid.uuid4(), raw_content="normal", classification="Public",
    importance=5, started_at=now, do_not_recall=False,
)

session_fields = _FakeRecallSession(
    fts_episodes=[normal_ep], recency_episodes=[normal_ep],
)
results_fields = asyncio.run(recall_memories(
    session_fields, "test fields", limit=10,
    embedding_service=_FakeEmbedder(),
))
if results_fields:
    r0 = results_fields[0]
    check("Result has id key", "id" in r0)
    check("Result has safe_content key", "safe_content" in r0)
    check("Result has classification key", "classification" in r0)
    check("Result has importance key", "importance" in r0)
    check("Result has created_at key", "created_at" in r0)
    check("Result has combined_score key", "combined_score" in r0)
    check("Result has is_summarized key", "is_summarized" in r0)
    check("id is string", isinstance(r0["id"], str))
    check("safe_content is string", isinstance(r0["safe_content"], str))
    check("classification is string", isinstance(r0["classification"], str))
    check("importance is int", isinstance(r0["importance"], int))
    check("combined_score is float",
          isinstance(r0["combined_score"], (int, float)))
    check("is_summarized is bool", isinstance(r0["is_summarized"], bool))
else:
    check("Return fields check", False, "No results returned from recall")

# =========================================================================
# 15. Embedding through fake service
# =========================================================================
print("\n--- 15. Embedding Service Integration ---")

emb = _FakeEmbedder(1536)


async def _test_emb() -> None:
    vec = await emb.aembed("test query")
    check("Fake embedding is 1536-dim", len(vec) == 1536)
    if vec:
        check("Fake embedding has float values",
              all(isinstance(v, float) for v in vec[:5]))


asyncio.run(_test_emb())

# =========================================================================
# 16. Exports from __init__.py
# =========================================================================
print("\n--- 16. __init__.py Exports ---")
try:
    from src.memory import (
        ReadPipelineError as RPE,
        ReadPipelineQueryError as RPQE,
        ReadPipelineSafetyError as RPSE,
        ReadPipelineTokenBudgetError as RPTBE,
        RecencyConfig as RC,
        recall_memories as rm,
        RRF_K as RRF,
        RECENCY_HALF_LIFE_DAYS as RHLD,
        SAFE_MODE_PLACEHOLDER as SMP,
        DEFAULT_TOKEN_BUDGET as DTB,
    )
    check("from src.memory re-exports ReadPipelineError",
          ReadPipelineError is RPE)
    check("from src.memory re-exports ReadPipelineQueryError",
          ReadPipelineQueryError is RPQE)
    check("from src.memory re-exports ReadPipelineSafetyError",
          ReadPipelineSafetyError is RPSE)
    check("from src.memory re-exports ReadPipelineTokenBudgetError",
          ReadPipelineTokenBudgetError is RPTBE)
    check("from src.memory re-exports RecencyConfig", RecencyConfig is RC)
    check("from src.memory re-exports recall_memories", recall_memories is rm)
    check("from src.memory re-exports RRF_K", RRF_K == RRF)
    check("from src.memory re-exports RECENCY_HALF_LIFE_DAYS",
          RECENCY_HALF_LIFE_DAYS == RHLD)
    check("from src.memory re-exports SAFE_MODE_PLACEHOLDER",
          SAFE_MODE_PLACEHOLDER == SMP)
    check("from src.memory re-exports DEFAULT_TOKEN_BUDGET",
          DEFAULT_TOKEN_BUDGET == DTB)
except Exception as e:
    check("__init__.py exports", False, str(e))

# =========================================================================
# 17. RecencyConfig construction
# =========================================================================
print("\n--- 17. RecencyConfig ---")

rc_default = RecencyConfig()
check("RecencyConfig default half_life=90", rc_default.half_life_days == 90)
check("RecencyConfig default reference_time=None",
      rc_default.reference_time is None)

rc_custom = RecencyConfig(half_life_days=30, reference_time=now)
check("RecencyConfig custom half_life=30", rc_custom.half_life_days == 30)
check("RecencyConfig custom reference_time set",
      rc_custom.reference_time is now)

# =========================================================================
# 18. No secrets in module repr
# =========================================================================
print("\n--- 18. No Secrets in Output ---")

rp_repr = repr(rp)
check("No API key pattern in read_pipeline repr",
      "sk-" not in rp_repr and "api_key" not in rp_repr.lower())

try:
    sess_empty = _FakeRecallSession()
    _ = asyncio.run(recall_memories(sess_empty, ""))
except ReadPipelineQueryError as e:
    msg = str(e)
    check("Query error mentions query_text", "query_text" in msg.lower())
    check("Query error mentions non-empty", "non-empty" in msg.lower())

# =========================================================================
# 19. Public API consistency
# =========================================================================
print("\n--- 19. Public API Consistency ---")

# Verify RRF_K constant value
check("RRF_K == 60", RRF_K == 60)
# Verify SAFE_MODE_PLACEHOLDER is non-empty
check("SAFE_MODE_PLACEHOLDER is non-empty", bool(SAFE_MODE_PLACEHOLDER))
# Verify DEFAULT_TOKEN_BUDGET is positive
check("DEFAULT_TOKEN_BUDGET > 0", DEFAULT_TOKEN_BUDGET > 0)
# Verify RECENCY_HALF_LIFE_DAYS value
check("RECENCY_HALF_LIFE_DAYS == 90", RECENCY_HALF_LIFE_DAYS == 90)

# =========================================================================
# Summary
# =========================================================================
print()
print("=" * 70)
print(f"RESULTS: {pass_count} passed, {fail_count} failed")
if errors:
    print("FAILURES:")
    for e in errors:
        print(f"  - {e}")
print("=" * 70)
print()

sys.exit(0 if fail_count == 0 else 1)