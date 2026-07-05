"""WSJF-adapted priority scoring for Guinevere autonomous loops.

Provides a deterministic, purely algorithmic scorer that ranks incoming
work items by urgency, value, feasibility, cost-of-delay, aging, and
ADR-029 risk tier. No LLM calls are made by this module.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable

from guinevere.loops.skill_library import SkillLibrary
from guinevere.loops.tool_registry import ToolRegistry

# ---------------------------------------------------------------------------
# Module constants
# ---------------------------------------------------------------------------

DEFAULT_WEIGHTS = {"urgency": 0.3, "value": 0.4, "feasibility": 0.3}
"""Default WSJF weight vector."""

AGING_RATE = 0.01
"""Linear aging boost applied per hour of waiting time."""

AGING_CAP = 2.0
"""Maximum aging multiplier (100 hours at AGING_RATE = 0.01)."""

ESCALATE_KEYWORDS = frozenset(
    {
        "safety",
        "surveillance",
        "consent",
        "credential",
        "hard_stop",
        "distress",
        "password",
        "secret",
        "encrypt",
    }
)
"""Keywords that force the ``escalate`` ADR-029 risk tier."""

APPROVE_KEYWORDS = frozenset(
    {
        "deploy",
        "migrate",
        "self-modify",
        "delete",
        "drop",
        "force",
        "production",
    }
)
"""Keywords that force the ``approve`` ADR-029 risk tier."""

NOTIFY_KEYWORDS = frozenset(
    {
        "write",
        "create",
        "update",
        "api",
        "webhook",
        "email",
        "discord",
    }
)
"""Keywords that force the ``notify`` ADR-029 risk tier."""

COST_TIERS = {
    "flash": {"tokens_per_task": 10_000, "cost_per_1k": 0.00028},
    "standard": {"tokens_per_task": 50_000, "cost_per_1k": 0.002},
    "reasoning": {"tokens_per_task": 200_000, "cost_per_1k": 0.01},
}
"""Per-model-tier token and cost assumptions."""

_SURVEILLANCE_KEYWORDS = frozenset(
    {"surveillance", "alertmanager", "alert", "incident", "page", "pagerduty"}
)
_CI_KEYWORDS = frozenset({"ci failure", "github action", "build failed", "tests failed"})
_URGENT_EMAIL_KEYWORDS = frozenset({"urgent", "asap", "immediately", "critical"})
_TODO_KEYWORDS = frozenset({"todo", "fixme"})
_DISCORD_KEYWORDS = frozenset({"discord", "mention", "message"})
_RUNBOOK_KEYWORDS = frozenset({"runbook", "sop", "playbook"})
_SAFETY_KEYWORDS = frozenset({"safety", "security", "vulnerability", "cve", "exploit"})
_COST_KEYWORDS = frozenset({"cost", "save", "reduce", "cheap", "free", "budget"})
_PRODUCTIVITY_KEYWORDS = frozenset({"productivity", "workflow", "efficiency", "automation"})
_TECH_DEBT_KEYWORDS = frozenset({"tech debt", "refactor", "deprecate", "cleanup", "maintenance"})


# ---------------------------------------------------------------------------
# Domain objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PriorityScore:
    """Immutable result of a single priority scoring pass."""

    item_id: str
    composite_score: float
    urgency: float
    value: float
    feasibility: float
    cost_estimate_usd: float
    cost_estimate_tokens: int
    risk_tier: str
    aging_factor: float
    scored_at: datetime


@dataclass(frozen=True)
class CostEstimate:
    """Immutable pre-execution LLM cost estimate."""

    estimated_tokens: int
    estimated_cost_usd: float
    estimated_duration_minutes: float
    confidence: float
    model_tier: str


# ---------------------------------------------------------------------------
# Priority scorer
# ---------------------------------------------------------------------------


class PriorityScorer:
    """WSJF-adapted priority scorer with cost-benefit and ADR-029 risk tiers.

    The scorer is deterministic and makes no LLM calls. It accepts a raw
    backlog item as either a mapping or an object with attributes, extracts
    signal metadata, and returns a :class:`PriorityScore`.

    Parameters
    ----------
    session_factory:
        Optional callable used to obtain a database session for historical
        cost lookup. Reserved for future use; currently stored but not invoked
        unless it exposes a compatible cost-history API.
    tool_registry:
        Optional :class:`guinevere.loops.tool_registry.ToolRegistry` used to check
        whether the tools required by a task are available.
    skill_library:
        Optional :class:`guinevere.loops.skill_library.SkillLibrary` used to check
        whether relevant procedural skills exist for a task.
    """

    def __init__(
        self,
        session_factory: Callable[[], object] | None = None,
        tool_registry: ToolRegistry | None = None,
        skill_library: SkillLibrary | None = None,
    ) -> None:
        self.session_factory = session_factory
        self.tool_registry = tool_registry
        self.skill_library = skill_library
        self.weights = dict(DEFAULT_WEIGHTS)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def score(
        self,
        item: dict[str, object] | object,
        context: dict[str, object] | None = None,
    ) -> PriorityScore:
        """Score a single backlog item.

        Parameters
        ----------
        item:
            Backlog item, either a ``dict`` or an object with attributes.
            Expected fields/keys: ``item_id``/``id``, ``signal``,
            ``description``, ``title``, ``created_at``/``discovered_at``,
            ``required_tools``, ``metadata``.
        context:
            Optional runtime context passed through to tool lookups.

        Returns
        -------
        A fully populated :class:`PriorityScore`.
        """
        now = datetime.now(timezone.utc)
        item_id = _get_item_id(item)
        text_content = _extract_text(item)

        urgency = self.compute_urgency(item)
        value = self.compute_value(item)
        feasibility = self.compute_feasibility(item, context=context)
        cost_est = self.estimate_cost(item)
        aging = self.compute_aging(item, now=now)

        weighted_sum = (
            self.weights["urgency"] * urgency
            + self.weights["value"] * value
            + self.weights["feasibility"] * feasibility
        )
        cost_penalty = 1.0 / (1.0 + cost_est.estimated_cost_usd)
        composite = weighted_sum * aging * cost_penalty

        risk_tier = self.classify_risk(item)

        return PriorityScore(
            item_id=item_id,
            composite_score=composite,
            urgency=urgency,
            value=value,
            feasibility=feasibility,
            cost_estimate_usd=cost_est.estimated_cost_usd,
            cost_estimate_tokens=cost_est.estimated_tokens,
            risk_tier=risk_tier,
            aging_factor=aging,
            scored_at=now,
        )

    def compute_urgency(self, item: dict[str, object] | object) -> float:
        """Return a 0-1 urgency score for *item*."""
        signal = _get_value(item, "signal", default=None)
        if signal is not None:
            priority_hint = _get_value(signal, "priority_hint", default=None)
            if isinstance(priority_hint, (int, float)):
                return float(max(0.0, min(1.0, priority_hint)))

        text = _extract_text(item).lower()

        if any(kw in text for kw in _SURVEILLANCE_KEYWORDS):
            return 0.95
        if any(kw in text for kw in _CI_KEYWORDS):
            return 0.8
        if any(kw in text for kw in _URGENT_EMAIL_KEYWORDS):
            return 0.7
        if any(kw in text for kw in _DISCORD_KEYWORDS):
            return 0.6
        if any(kw in text for kw in _RUNBOOK_KEYWORDS):
            return 0.4
        if any(kw in text for kw in _TODO_KEYWORDS):
            return 0.3

        return 0.5

    def compute_value(self, item: dict[str, object] | object) -> float:
        """Return a 0-1 business/personal value score for *item*."""
        text = _extract_text(item).lower()

        if any(kw in text for kw in _SAFETY_KEYWORDS):
            return 1.0
        if any(kw in text for kw in _COST_KEYWORDS):
            return 0.9
        if any(kw in text for kw in _PRODUCTIVITY_KEYWORDS):
            return 0.75
        if any(kw in text for kw in _TECH_DEBT_KEYWORDS):
            return 0.45

        return 0.5

    def compute_feasibility(
        self,
        item: dict[str, object] | object,
        context: dict[str, object] | None = None,
    ) -> float:
        """Return a 0-1 feasibility score for *item*."""
        required_tools = _get_list_value(item, "required_tools")
        registry_score = self._score_tool_availability(required_tools, context)

        metadata = _get_value(item, "metadata", default={})
        skill_score = self._score_skill_availability(item, metadata)

        text = _extract_text(item)
        complexity_penalty = _complexity_penalty(text)

        combined = (registry_score + skill_score) / 2.0
        feasibility = combined * (1.0 - complexity_penalty)
        return max(0.0, min(1.0, feasibility))

    def estimate_cost(self, item: dict[str, object] | object) -> CostEstimate:
        """Return a pre-execution cost estimate for *item*."""
        historical = self._load_historical_cost(item)
        if historical is not None:
            return historical

        text = _extract_text(item)
        required_tools = _get_list_value(item, "required_tools")
        tier = _select_cost_tier(text, required_tools)

        tier_info = COST_TIERS[tier]
        estimated_tokens = tier_info["tokens_per_task"]
        estimated_cost_usd = estimated_tokens * tier_info["cost_per_1k"] / 1_000.0

        if tier == "flash":
            duration = 2.0
            confidence = 0.9
        elif tier == "standard":
            duration = 10.0
            confidence = 0.7
        else:
            duration = 30.0
            confidence = 0.5

        return CostEstimate(
            estimated_tokens=estimated_tokens,
            estimated_cost_usd=estimated_cost_usd,
            estimated_duration_minutes=duration,
            confidence=confidence,
            model_tier=tier,
        )

    def compute_aging(
        self,
        item: dict[str, object] | object,
        now: datetime | None = None,
    ) -> float:
        """Return an aging multiplier for *item* based on waiting time."""
        if now is None:
            now = datetime.now(timezone.utc)

        discovered_at = _get_datetime(item, "discovered_at")
        if discovered_at is None:
            discovered_at = _get_datetime(item, "created_at")
        if discovered_at is None:
            return 1.0

        aging_hours = (now - discovered_at).total_seconds() / 3600.0
        factor = 1.0 + aging_hours * AGING_RATE
        return min(AGING_CAP, factor)

    def classify_risk(self, item: dict[str, object] | object) -> str:
        """Classify *item* into an ADR-029 risk tier."""
        text = _extract_text(item).lower()

        if any(kw in text for kw in ESCALATE_KEYWORDS):
            return "escalate"
        if any(kw in text for kw in APPROVE_KEYWORDS):
            return "approve"
        if any(kw in text for kw in NOTIFY_KEYWORDS):
            return "notify"
        return "auto"

    async def score_batch(
        self,
        items: list[dict[str, object] | object],
        limit: int = 10,
    ) -> list[PriorityScore]:
        """Score multiple items and return the top-*limit* results.

        Scoring is CPU-bound and deterministic, so this method can be
        awaited without blocking an event loop for meaningful work.
        """
        scored = [self.score(item) for item in items]
        scored.sort(key=lambda score: score.composite_score, reverse=True)
        return scored[:limit]

    def recalibrate(self, weights: dict[str, float] | None = None) -> None:
        """Update the WSJF weights used for scoring.

        Parameters
        ----------
        weights:
            Mapping with keys ``urgency``, ``value``, and ``feasibility``.
            Missing keys retain their current values.
        """
        if weights is None:
            return
        for key in ("urgency", "value", "feasibility"):
            if key in weights:
                self.weights[key] = float(weights[key])

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _score_tool_availability(
        self,
        required_tools: list[str],
        context: dict[str, object] | None,
    ) -> float:
        """Return feasibility contribution based on tool availability."""
        if self.tool_registry is None or not required_tools:
            return 0.75

        available = 0
        for tool in required_tools:
            if hasattr(self.tool_registry, "get") and self.tool_registry.get(tool) is not None:
                available += 1
            elif hasattr(self.tool_registry, "validate_required"):
                if self.tool_registry.validate_required([tool]):
                    available += 1

        ratio = available / len(required_tools)
        if ratio >= 1.0:
            return 0.9
        if ratio >= 0.5:
            return 0.55
        if ratio > 0.0:
            return 0.3
        return 0.2

    def _score_skill_availability(
        self,
        item: dict[str, object] | object,
        metadata: object,
    ) -> float:
        """Return feasibility contribution based on skill-library coverage."""
        if self.skill_library is None:
            return 0.75

        task_type = _get_value(item, "task_type", default=None)
        if task_type is None and isinstance(metadata, dict):
            task_type = metadata.get("task_type")
        if not task_type:
            return 0.75

        # Synchronous fallback; the skill library is async, but feasibility
        # scoring currently runs in a sync context. Return a neutral score
        # rather than introducing an await here to keep the public API stable.
        return 0.75

    def _load_historical_cost(
        self,
        item: dict[str, object] | object,
    ) -> CostEstimate | None:
        """Attempt to load a historical cost estimate for *item*."""
        # Future hook: when the session_factory exposes a stable cost-history
        # API, query it here and return a calibrated CostEstimate. Until then,
        # fall back to the heuristic estimator.
        _ = item  # item may contain historical averages in future schemas
        if self.session_factory is None:
            return None
        return None


# ---------------------------------------------------------------------------
# Module helpers
# ---------------------------------------------------------------------------


def _get_item_id(item: dict[str, object] | object) -> str:
    """Return the item's identifier as a string."""
    item_id = _get_value(item, "item_id", default=None)
    if item_id is None:
        item_id = _get_value(item, "id", default="unknown")
    return str(item_id)


def _get_value(item: dict[str, object] | object, key: str, default: object = None) -> object:
    """Fetch a value from a dict-like or attribute-backed item."""
    if isinstance(item, dict):
        return item.get(key, default)
    return getattr(item, key, default)


def _get_list_value(item: dict[str, object] | object, key: str) -> list[str]:
    """Fetch a list value and coerce it to a list of strings."""
    value = _get_value(item, key, default=[])
    if not isinstance(value, list):
        return []
    typed: list[str] = []
    for entry in value:
        if isinstance(entry, str):
            typed.append(entry)
    return typed


def _get_datetime(item: dict[str, object] | object, key: str) -> datetime | None:
    """Fetch a datetime value from a dict-like or attribute-backed item."""
    value = _get_value(item, key, default=None)
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value
    return None


def _extract_text(item: dict[str, object] | object) -> str:
    """Return a searchable text blob from *item*."""
    if isinstance(item, dict):
        for key in ("description", "title", "task", "body", "content"):
            value = item.get(key)
            if isinstance(value, str):
                return value
        return ""

    for attr in ("description", "title", "task", "body", "content"):
        value = getattr(item, attr, None)
        if isinstance(value, str):
            return value
    return str(item) if item is not None else ""


def _complexity_penalty(text: str) -> float:
    """Return a 0-1 penalty based on description length."""
    length = len(text)
    if length < 100:
        return 0.0
    if length < 500:
        return 0.1
    if length < 2_000:
        return 0.25
    return 0.4


def _select_cost_tier(text: str, required_tools: list[str]) -> str:
    """Map task complexity to a model tier."""
    text_length = len(text)
    tool_count = len(required_tools)

    if text_length < 200 and tool_count <= 1:
        return "flash"
    if text_length < 1_000 and tool_count <= 3:
        return "standard"
    return "reasoning"


__all__ = [
    "PriorityScorer",
    "PriorityScore",
    "CostEstimate",
    "DEFAULT_WEIGHTS",
    "AGING_RATE",
    "AGING_CAP",
    "ESCALATE_KEYWORDS",
    "APPROVE_KEYWORDS",
    "NOTIFY_KEYWORDS",
    "COST_TIERS",
]
