"""A/B evaluation runner for KG recall (P16-005).

This module wires the :class:`GoldenTestSet` together with the
existing :func:`src.memory.read_pipeline.recall_memories` to
produce an A/B comparison: **baseline** (KG signal off) vs
**with-KG** (KG signal on, per the 4th-RRF path).

Design contract
---------------

* Lazy import of ``src.memory.read_pipeline`` — the eval module must
  not pull the memory pipeline at import time (the spec forbids
  module-level imports from ``src.memory``).
* All DB access is funnelled through the injected
  :data:`src.knowledge_graph.repository.SessionFactory`.
* Each golden case is scored independently; the final metric is the
  arithmetic mean across cases (see
  :func:`src.knowledge_graph.eval.metrics.aggregate_metrics`).

Why lazy import
---------------

``recall_memories`` lives in ``src.memory.read_pipeline``.  Pulling
it at module-load time would couple the entire KG eval package to
the memory runtime (a runtime dependency that breaks unit tests and
documentation builds).  Importing inside the coroutines keeps the
dependency on the actual call boundary where the function is used.

KG integration is forward-compatible
------------------------------------

When :func:`recall_memories` does not yet accept ``kg_enabled`` (a
pre-Wave-3 build), the runner falls back to the baseline path with
a logged warning.  This keeps the harness executable on older
snapshots of the read pipeline.
"""
from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Final, cast

from guinvere.knowledge_graph.eval.golden_set import GoldenCase, GoldenTestSet
from guinvere.knowledge_graph.eval.metrics import (
    EvaluationMetrics,
    MetricDelta,
    aggregate_metrics,
    compute_deltas,
    score_case,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Verdict thresholds (Faiz-locked — see task spec)
# ---------------------------------------------------------------------------

#: F1 delta above which we declare a significant improvement.
THRESHOLD_SIGNIFICANT: Final[float] = 0.05

#: F1 delta above which we declare a marginal improvement.
THRESHOLD_MARGINAL: Final[float] = 0.01

#: Verdict labels.  Order matters — we evaluate them top-down.
VERDICT_SIGNIFICANT_IMPROVEMENT: Final[str] = "SIGNIFICANT_IMPROVEMENT"
VERDICT_MARGINAL_IMPROVEMENT: Final[str] = "MARGINAL_IMPROVEMENT"
VERDICT_NO_CHANGE: Final[str] = "NO_CHANGE"
VERDICT_REGRESSION: Final[str] = "REGRESSION"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PerCaseComparisonResult:
    """Per-case A/B comparison snapshot.

    Attributes:
        case_id: Identifier of the :class:`GoldenCase` (mirrors
            ``GoldenCase.id``).
        query: The query string for the case (echoed for report
            rendering).
        baseline: Per-case metrics for the baseline run.
        with_kg: Per-case metrics for the KG-enabled run.
        delta_f1: ``with_kg.f1 - baseline.f1``.
    """

    case_id: str
    query: str
    baseline: EvaluationMetrics
    with_kg: EvaluationMetrics
    delta_f1: float

    @property
    def improved(self) -> bool:
        """``True`` iff the KG run improved F1 over the baseline."""
        return self.with_kg.f1 > self.baseline.f1


@dataclass(frozen=True)
class ABComparisonResult:
    """Aggregate outcome of an A/B recall evaluation run.

    Attributes:
        baseline_metrics: Aggregated metrics for the run with KG off.
        kg_metrics: Aggregated metrics for the run with KG on.
        per_case_results: One :class:`PerCaseComparisonResult` per
            golden case (preserves the golden-set order).
        delta_precision: ``kg.precision - baseline.precision``.
        delta_recall: ``kg.recall - baseline.recall``.
        delta_f1: ``kg.f1 - baseline.f1`` — drives the verdict.
        delta_mrr: ``kg.mrr - baseline.mrr``.
        delta_ndcg: ``kg.ndcg - baseline.ndcg``.
        verdict: One of the four verdict labels (see module constants).
    """

    baseline_metrics: EvaluationMetrics
    kg_metrics: EvaluationMetrics
    per_case_results: list[PerCaseComparisonResult] = field(default_factory=list)
    delta_precision: float = 0.0
    delta_recall: float = 0.0
    delta_f1: float = 0.0
    delta_mrr: float = 0.0
    delta_ndcg: float = 0.0
    verdict: str = VERDICT_NO_CHANGE

    @property
    def improved(self) -> bool:
        """``True`` iff the verdict indicates any improvement."""
        return self.verdict in (
            VERDICT_SIGNIFICANT_IMPROVEMENT,
            VERDICT_MARGINAL_IMPROVEMENT,
        )

    @property
    def deltas(self) -> dict[str, MetricDelta]:
        """Per-metric :class:`MetricDelta` mapping (mirrors
        :func:`src.knowledge_graph.eval.metrics.compute_deltas`)."""
        return compute_deltas(self.baseline_metrics, self.kg_metrics)


# ---------------------------------------------------------------------------
# Verdict derivation
# ---------------------------------------------------------------------------


def derive_verdict(delta_f1: float) -> str:
    """Map an F1 delta to a verdict label.

    Thresholds (Faiz-locked):

    * ``> +0.05``  → ``SIGNIFICANT_IMPROVEMENT``
    * ``> +0.01``  → ``MARGINAL_IMPROVEMENT``
    * ``±0.01``    → ``NO_CHANGE``
    * ``< -0.01``  → ``REGRESSION``

    Args:
        delta_f1: ``kg.f1 - baseline.f1``.

    Returns:
        The verdict label.
    """
    if delta_f1 > THRESHOLD_SIGNIFICANT:
        return VERDICT_SIGNIFICANT_IMPROVEMENT
    if delta_f1 > THRESHOLD_MARGINAL:
        return VERDICT_MARGINAL_IMPROVEMENT
    if delta_f1 < -THRESHOLD_MARGINAL:
        return VERDICT_REGRESSION
    return VERDICT_NO_CHANGE


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


#: Callable that yields an async session compatible with
#: :func:`recall_memories`.  Matches
#: :data:`src.knowledge_graph.repository.SessionFactory` semantically
#: but is duplicated here to keep this module free of any
#: ``src.memory`` import.
SessionFactory = Callable[[], object]


class KGRecallEvaluator:
    """Run the KG recall benchmark with and without the KG signal.

    Args:
        session_factory: Callable returning a fresh async session
            (typically ``src.memory.db.get_async_session``).  The
            runner uses the session for every golden case.
        golden_set: Curated test cases.  Iteration order is preserved
            so per-case reports are deterministic.
        recall_limit: Per-case ``limit=`` passed to
            :func:`recall_memories`.  Defaults to ``20`` — matches
            the read pipeline default.
        ndcg_k: Cutoff for nDCG in per-case scoring.  Defaults to
            ``10``.
        kg_supported: When ``True`` (default), the runner passes
            ``kg_enabled=...`` to :func:`recall_memories`.  Set to
            ``False`` for pre-Wave-3 builds where the kwarg does
            not exist — the runner logs a one-time warning per
            case instead of failing.

    Example::

        evaluator = KGRecallEvaluator(
            session_factory=src.memory.db.get_async_session,
            golden_set=create_sample_golden_set(),
        )
        result = await evaluator.run_ab_comparison()
        print(result.verdict, result.delta_f1)
    """

    def __init__(
        self,
        session_factory: SessionFactory,
        golden_set: GoldenTestSet,
        *,
        recall_limit: int = 20,
        ndcg_k: int = 10,
        kg_supported: bool = True,
    ) -> None:
        if session_factory is None:
            raise ValueError("session_factory must not be None")
        if golden_set is None:
            raise ValueError("golden_set must not be None")
        if recall_limit < 1:
            raise ValueError(f"recall_limit must be >= 1; got {recall_limit}")
        if ndcg_k < 1:
            raise ValueError(f"ndcg_k must be >= 1; got {ndcg_k}")

        self._session_factory: SessionFactory = session_factory
        self._golden_set: GoldenTestSet = golden_set
        self._recall_limit: int = recall_limit
        self._ndcg_k: int = ndcg_k
        self._kg_supported: bool = kg_supported
        # One-shot warning — we do not spam the logger once per case
        # when the integration is missing.
        self._warned_missing_kwarg: bool = False

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_baseline(self) -> EvaluationMetrics:
        """Run recall **without** the KG signal.

        Returns:
            Aggregated :class:`EvaluationMetrics` over all golden
            cases.
        """
        per_case = await self._run_recall(kg_enabled=False)
        return aggregate_metrics(per_case)

    async def run_with_kg(self) -> EvaluationMetrics:
        """Run recall **with** the KG signal.

        Returns:
            Aggregated :class:`EvaluationMetrics` over all golden
            cases.
        """
        per_case = await self._run_recall(kg_enabled=True)
        return aggregate_metrics(per_case)

    async def run_ab_comparison(self) -> ABComparisonResult:
        """Run both arms and assemble the A/B comparison result.

        Returns:
            A populated :class:`ABComparisonResult` with verdict.
        """
        baseline_per_case = await self._run_recall(kg_enabled=False)
        kg_per_case = await self._run_recall(kg_enabled=True)

        baseline_metrics = aggregate_metrics(baseline_per_case)
        kg_metrics = aggregate_metrics(kg_per_case)

        deltas = compute_deltas(baseline_metrics, kg_metrics)

        per_case_results: list[PerCaseComparisonResult] = []
        for case, base_m, kg_m in zip(
            self._golden_set, baseline_per_case, kg_per_case,
        ):
            per_case_results.append(
                PerCaseComparisonResult(
                    case_id=case.id,
                    query=case.query,
                    baseline=base_m,
                    with_kg=kg_m,
                    delta_f1=kg_m.f1 - base_m.f1,
                ),
            )

        verdict = derive_verdict(deltas["f1"].delta)

        return ABComparisonResult(
            baseline_metrics=baseline_metrics,
            kg_metrics=kg_metrics,
            per_case_results=per_case_results,
            delta_precision=deltas["precision"].delta,
            delta_recall=deltas["recall"].delta,
            delta_f1=deltas["f1"].delta,
            delta_mrr=deltas["mrr"].delta,
            delta_ndcg=deltas["ndcg"].delta,
            verdict=verdict,
        )

    # ------------------------------------------------------------------
    # Internal — per-case recall + scoring
    # ------------------------------------------------------------------

    async def _run_recall(
        self,
        *,
        kg_enabled: bool,
    ) -> list[EvaluationMetrics]:
        """Run recall for every case with ``kg_enabled`` set.

        Args:
            kg_enabled: Forwarded to
                :func:`recall_memories` when supported by the
                signature.

        Returns:
            One :class:`EvaluationMetrics` per case, in golden-set
            order.
        """
        per_case: list[EvaluationMetrics] = []
        for case in self._golden_set:
            metrics = await self._score_one_case(case=case, kg_enabled=kg_enabled)
            per_case.append(metrics)
        return per_case

    async def _score_one_case(
        self,
        *,
        case: GoldenCase,
        kg_enabled: bool,
    ) -> EvaluationMetrics:
        """Recall + score a single case.

        Args:
            case: The :class:`GoldenCase` to score.
            kg_enabled: Forwarded to :func:`recall_memories`.

        Returns:
            A single :class:`EvaluationMetrics` (``total_cases=1``).
        """
        # Lazy import — keep src.memory off the module-level surface.
        from guinvere.memory.read_pipeline import recall_memories

        try:
            session = self._session_factory()
        except Exception as exc:  # noqa: BLE001 — narrowed below
            logger.error(
                "kg_eval_session_factory_failed",
                extra={
                    "case_id": case.id,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            )
            return _zero_metrics()

        try:
            results = await self._safe_recall(
                session=session,
                query=case.query,
                kg_enabled=kg_enabled,
                case_id=case.id,
            )
        except Exception as exc:  # noqa: BLE001 — narrowed below
            logger.error(
                "kg_eval_recall_failed",
                extra={
                    "case_id": case.id,
                    "kg_enabled": kg_enabled,
                    "error_type": type(exc).__name__,
                    "error": str(exc)[:200],
                },
            )
            return _zero_metrics()
        finally:
            await self._close_session(session)

        retrieved_ids = _extract_ids(results)
        return score_case(
            retrieved_ids=retrieved_ids,
            expected_recall_ids=case.expected_recall_ids,
            k=self._ndcg_k,
        )

    async def _safe_recall(
        self,
        *,
        session: object,
        query: str,
        kg_enabled: bool,
        case_id: str,
    ) -> list[dict[str, object]]:
        """Call :func:`recall_memories` with ``kg_enabled`` if supported.

        Pre-Wave-3 builds of the read pipeline do not accept
        ``kg_enabled``; on those builds we transparently fall back to
        the baseline path so the harness remains runnable.
        """
        from guinvere.memory.read_pipeline import RecallSession, recall_memories

        _session = cast(RecallSession, session)
        if self._kg_supported:
            try:
                return list(
                    await recall_memories(
                        _session,
                        query,
                        self._recall_limit,
                        kg_enabled=kg_enabled,
                    ),
                )
            except TypeError as exc:
                if "kg_enabled" not in str(exc):
                    raise
                # Disable future attempts and fall through to the
                # kwarg-free path.  Logged once per evaluator instance.
                if not self._warned_missing_kwarg:
                    logger.warning(
                        "kg_eval_kg_enabled_unsupported_falling_back",
                        extra={"error": str(exc)[:200]},
                    )
                    self._warned_missing_kwarg = True
                self._kg_supported = False

        return list(
            await recall_memories(
                _session,
                query,
                self._recall_limit,
            ),
        )

    @staticmethod
    async def _close_session(session: object) -> None:
        """Best-effort async close of a session returned by the factory.

        Calls ``session.close()`` when it exists and is awaitable.
        Swallows non-awaitable / missing-attribute errors so a
        bare-sync session does not crash the harness.
        """
        close = getattr(session, "close", None)
        if close is None:
            return
        try:
            result = close()
        except Exception:  # noqa: BLE001 — narrowed below
            logger.debug("kg_eval_session_close_failed", exc_info=False)
            return
        if isinstance(result, Awaitable):
            try:
                await result
            except Exception:  # noqa: BLE001 — narrowed below
                logger.debug("kg_eval_session_close_failed", exc_info=False)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_ids(results: list[dict[str, object]]) -> list[str]:
    """Project ``recall_memories`` results to a list of ID strings.

    The KG evaluator only cares about the ``id`` field for ranking
    purposes — the rest of the dict (``safe_content``,
    ``combined_score``, ...) is forwarded to the caller by the
    production pipeline, not by the eval harness.

    Args:
        results: Output of :func:`recall_memories`.

    Returns:
        IDs in their original ranked order.  Missing or
        non-string ``id`` values are coerced to ``str``.
    """
    ids: list[str] = []
    for entry in results:
        raw = entry.get("id") if isinstance(entry, dict) else None
        if raw is None:
            continue
        ids.append(str(raw))
    return ids


def _zero_metrics() -> EvaluationMetrics:
    """Return a per-case metrics record with all values at zero.

    Used when recall fails for a case so the harness still produces
    a deterministic aggregated score instead of crashing.
    """
    return EvaluationMetrics(
        precision=0.0,
        recall=0.0,
        f1=0.0,
        mrr=0.0,
        ndcg=0.0,
        total_cases=1,
        passed_cases=0,
    )


__all__ = [
    "KGRecallEvaluator",
    "ABComparisonResult",
    "PerCaseComparisonResult",
    "SessionFactory",
    "derive_verdict",
    "VERDICT_SIGNIFICANT_IMPROVEMENT",
    "VERDICT_MARGINAL_IMPROVEMENT",
    "VERDICT_NO_CHANGE",
    "VERDICT_REGRESSION",
    "THRESHOLD_SIGNIFICANT",
    "THRESHOLD_MARGINAL",
]