"""Metacognitive Evaluation — two-layer thought quality assessment.

Provides real-time evaluation after each thought generation and periodic
self-review every N thoughts for the consciousness thought stream.

Design decisions:
  - MetaCogEval is a frozen dataclass (immutable once created).
  - No asyncio.sleep() in the eval path — synchronous heuristics only.
  - Hallucination guard uses keyword/structure heuristics, not LLM calls.
  - Periodic review uses synchronous analysis of thought history strings.
  - No imports from guinevere.consciousness.infra (boundary separation).
  - No circular imports — does not import ConsciousnessLoop.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import structlog

if TYPE_CHECKING:
    from guinevere.consciousness.thought import ThoughtType

logger = structlog.get_logger("guinevere.consciousness.metacognition")

# Integration constants — weights for composite quality score.
CONFIDENCE_WEIGHT: float = 0.4
COHERENCE_WEIGHT: float = 0.3
NOVELTY_WEIGHT: float = 0.3

# Hallucination guard patterns.
_CONTRADICTION_PAIRS: list[tuple[str, str]] = [
    ("always", "never"),
    ("all", "none"),
    ("everyone", "nobody"),
    ("everything", "nothing"),
    ("must", "must not"),
    ("should", "should not"),
    ("will", "will not"),
    ("can", "cannot"),
    ("is", "is not"),
    ("increase", "decrease"),
]

_SUPERLATIVE_PATTERN = re.compile(
    r"\b(always|never|all|none|every|nothing|impossible|definitely|absolutely|"
    r"completely|totally|utterly|perfect|flawless|guaranteed|certain)\b",
    re.IGNORECASE,
)

_HEDGE_PATTERN = re.compile(
    r"\b(perhaps|maybe|might|could|possibly|potentially|likely|unlikely|"
    r"seems|appears|suggests|indicates|approximately|roughly|generally)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class MetaCogEval:
    """Metacognitive evaluation result for a single thought.

    Immutable once created. Produced by MetacognitiveEvaluator.evaluate()
    after each thought generation.

    Attributes:
        confidence: Overall quality confidence [0.0, 1.0].
        coherence: Logical consistency and structure [0.0, 1.0].
        novelty: Originality and non-redundancy [0.0, 1.0].
        safety_pass: Whether the thought passes hallucination guard.
        should_record: Whether this thought should be recorded in state.
        suggested_type: If eval suggests a different thought type, else None.
    """

    confidence: float
    coherence: float
    novelty: float
    safety_pass: bool
    should_record: bool
    suggested_type: Any  # Optional[ThoughtType] — use Any to avoid import cycle


class MetacognitiveEvaluator:
    """Two-layer metacognitive evaluator for the consciousness thought stream.

    Layer 1 — Real-time evaluation (evaluate()):
        Called after each thought generation. Checks quality, confidence,
        hallucination guard, and suggests type adjustments.

    Layer 2 — Periodic self-review (periodic_review()):
        Called every N thoughts. Reviews thought history for patterns,
        biases, and coverage gaps.

    Configuration:
        review_interval: Number of thoughts between periodic reviews.
            Default 20. Override via constructor.
    """

    def __init__(self, review_interval: int = 20) -> None:
        self._review_interval: int = max(1, review_interval)
        self._thought_count: int = 0
        self._recent_contents: list[str] = []
        self._recent_types: list[str] = []
        logger.info(
            "metacognition.initialized",
            review_interval=self._review_interval,
        )

    @property
    def review_count(self) -> int:
        """Total number of thoughts evaluated so far."""
        return self._thought_count

    @property
    def review_interval(self) -> int:
        """Configured interval for periodic self-review."""
        return self._review_interval

    def evaluate(
        self,
        thought_type: Any,
        content: str,
        affect: dict[str, float] | None = None,
    ) -> MetaCogEval:
        """Real-time metacognitive evaluation after each thought.

        Computes confidence, coherence, novelty, hallucination guard,
        and suggested type for the given thought.

        Args:
            thought_type: The ThoughtType of the generated thought.
                Accepted as Any to avoid circular import; expects
                ThoughtType enum or string value.
            content: The generated thought content string.
            affect: Optional affect vector dict for context-aware scoring.

        Returns:
            MetaCogEval with all evaluation dimensions.
        """
        self._thought_count += 1

        # Extract the string value of the thought type.
        type_value = (
            thought_type.value
            if hasattr(thought_type, "value")
            else str(thought_type)
        )

        # --- Coherence scoring ---
        coherence = self._score_coherence(content)

        # --- Novelty scoring ---
        novelty = self._score_novelty(content)

        # --- Hallucination guard ---
        safety_pass = self._hallucination_guard(content)

        # --- Confidence: composite weighted score ---
        confidence = (
            CONFIDENCE_WEIGHT * (coherence + novelty) / 2.0
            + COHERENCE_WEIGHT * coherence
            + NOVELTY_WEIGHT * novelty
        )

        # Boost baseline with sentence/word structure.
        # A non-empty thought with sentences should never floor at 0.2.
        word_count = len(content.split())
        if word_count >= 5:
            confidence = max(confidence, 0.4)

        # Adjust confidence with affect if available.
        if affect:
            affect_confidence = affect.get("confidence", 0.5)
            confidence = confidence * 0.7 + affect_confidence * 0.3

        # Clamp to [0.0, 1.0].
        confidence = max(0.0, min(1.0, confidence))
        coherence = max(0.0, min(1.0, coherence))
        novelty = max(0.0, min(1.0, novelty))

        # --- Should record: always true unless safety fails badly ---
        should_record = safety_pass or confidence > 0.3

        # --- Suggested type: if coherence is low for cognition, suggest META ---
        suggested_type = None
        if type_value == "cognition" and coherence < 0.4:
            from guinevere.consciousness.thought import ThoughtType

            suggested_type = ThoughtType.META

        # Track for periodic review.
        self._recent_contents.append(content[:500])
        self._recent_types.append(type_value)
        # Keep a sliding window.
        if len(self._recent_contents) > self._review_interval * 2:
            self._recent_contents = self._recent_contents[-self._review_interval :]
            self._recent_types = self._recent_types[-self._review_interval :]

        logger.debug(
            "metacognition.evaluate",
            type=type_value,
            confidence=round(confidence, 3),
            coherence=round(coherence, 3),
            novelty=round(novelty, 3),
            safety_pass=safety_pass,
        )

        return MetaCogEval(
            confidence=confidence,
            coherence=coherence,
            novelty=novelty,
            safety_pass=safety_pass,
            should_record=should_record,
            suggested_type=suggested_type,
        )

    def should_run_periodic_review(self) -> bool:
        """Check if enough thoughts have accumulated for a periodic review.

        Returns:
            True if thought_count is a multiple of review_interval.
        """
        return self._thought_count > 0 and (
            self._thought_count % self._review_interval == 0
        )

    def periodic_review(
        self,
        thought_history: list[str],
        n: int = 20,
    ) -> dict[str, Any]:
        """Periodic self-review: analyse thought history for patterns.

        Called every N thoughts. Reviews the recent thought history for
        repeating patterns, potential biases, and topic coverage gaps.

        Args:
            thought_history: List of recent thought strings to review.
            n: Number of recent thoughts to consider (default 20).

        Returns:
            Dict with keys: patterns_found, biases_detected,
            coverage_gaps, recommendations.
        """
        # Limit to last n thoughts.
        recent = thought_history[-n:] if len(thought_history) > n else thought_history

        patterns_found: list[str] = []
        biases_detected: list[str] = []
        coverage_gaps: list[str] = []
        recommendations: list[str] = []

        if not recent:
            return {
                "thoughts_reviewed": 0,
                "patterns_found": [],
                "biases_detected": [],
                "coverage_gaps": ["no_thoughts_to_review"],
                "recommendations": ["generate_more_thoughts_before_review"],
            }

        # --- Pattern detection: repeated phrases ---
        word_freq: dict[str, int] = {}
        for thought in recent:
            words = thought.lower().split()
            for word in words:
                if len(word) > 4:  # skip short words
                    word_freq[word] = word_freq.get(word, 0) + 1

        repeated = [
            w for w, c in word_freq.items() if c >= max(2, len(recent) * 0.3)
        ]
        if repeated:
            patterns_found.append(
                f"repeated_terms: {', '.join(repeated[:5])}"
            )

        # --- Type distribution check ---
        type_counts: dict[str, int] = {}
        for t in self._recent_types[-n:]:
            type_counts[t] = type_counts.get(t, 0) + 1

        total_types = sum(type_counts.values())
        if total_types > 0:
            for ttype, count in type_counts.items():
                ratio = count / total_types
                if ratio > 0.5:
                    biases_detected.append(
                        f"overrepresented_type: {ttype} ({ratio:.0%})"
                    )

            # Coverage gap: check which types are missing.
            expected_types = {
                "cognition",
                "reflection",
                "planning",
                "dreaming",
                "meta",
                "heartbeat",
            }
            present = set(type_counts.keys())
            missing = expected_types - present
            if missing:
                coverage_gaps.append(
                    f"missing_types: {', '.join(sorted(missing))}"
                )

        # --- Contradiction scan across recent thoughts ---
        contradiction_count = 0
        for thought in recent:
            lower = thought.lower()
            for word_a, word_b in _CONTRADICTION_PAIRS:
                if word_a in lower and word_b in lower:
                    contradiction_count += 1
                    break
        if contradiction_count > len(recent) * 0.3:
            biases_detected.append(
                f"frequent_contradictions: {contradiction_count}/{len(recent)}"
            )

        # --- Recommendations ---
        if not patterns_found and not biases_detected:
            recommendations.append("thought_stream_is_healthy")
        if biases_detected:
            recommendations.append(
                "diversify_thought_types_to_reduce_bias"
            )
        if coverage_gaps and "no_thoughts_to_review" not in coverage_gaps:
            recommendations.append(
                "increase_coverage_of_underrepresented_types"
            )

        result: dict[str, Any] = {
            "thoughts_reviewed": len(recent),
            "patterns_found": patterns_found,
            "biases_detected": biases_detected,
            "coverage_gaps": coverage_gaps,
            "recommendations": recommendations,
        }

        logger.info(
            "metacognition.periodic_review",
            thoughts_reviewed=len(recent),
            patterns=len(patterns_found),
            biases=len(biases_detected),
            gaps=len(coverage_gaps),
        )

        return result

    # ── Internal scoring helpers ─────────────────────────────

    def _score_coherence(self, content: str) -> float:
        """Score the coherence of thought content.

        Heuristics:
          - Length and structure (sentences, paragraphs).
          - Presence of logical connectors.
          - JSON parsability for structured thoughts.

        Returns:
            Coherence score in [0.0, 1.0].
        """
        if not content or not content.strip():
            return 0.1

        score = 0.5  # baseline

        # Length penalty for very short or empty content.
        word_count = len(content.split())
        if word_count < 3:
            return 0.2
        if word_count >= 10:
            score += 0.1

        # Sentence structure bonus.
        sentence_count = content.count(".") + content.count("!") + content.count("?")
        if sentence_count >= 1:
            score += 0.1

        # Logical connectors bonus.
        connectors = [
            "because",
            "therefore",
            "however",
            "although",
            "thus",
            "consequently",
            "furthermore",
            "moreover",
            "additionally",
            "specifically",
        ]
        connector_count = sum(
            1 for c in connectors if c in content.lower()
        )
        score += min(connector_count * 0.05, 0.15)

        # JSON parsability bonus (structured thoughts are coherent).
        try:
            json.loads(content)
            score += 0.15
        except (json.JSONDecodeError, TypeError):
            pass

        return max(0.0, min(1.0, score))

    def _score_novelty(self, content: str) -> float:
        """Score the novelty of thought content.

        Compared against the sliding window of recent contents.

        Returns:
            Novelty score in [0.0, 1.0].
        """
        if not self._recent_contents:
            return 0.7  # first thought is novel by default

        # Simple word-overlap novelty: how much of the content is new words.
        current_words = set(content.lower().split())
        if not current_words:
            return 0.3

        recent_words: set[str] = set()
        for prev in self._recent_contents[-10:]:
            recent_words.update(prev.lower().split())

        if not recent_words:
            return 0.7

        overlap = current_words & recent_words
        overlap_ratio = len(overlap) / len(current_words) if current_words else 0.0

        # Novelty = 1 - overlap_ratio.
        novelty = 1.0 - overlap_ratio

        # Scale to [0.2, 1.0] — even repetitive thoughts get some novelty.
        return max(0.2, min(1.0, 0.2 + novelty * 0.8))

    def _hallucination_guard(self, content: str) -> bool:
        """Check for hallucination indicators in thought content.

        Heuristic checks:
          - Self-contradiction: presence of contradictory word pairs.
          - Unsubstantiated superlatives without hedging.

        Returns:
            True if content passes the guard (no hallucination indicators).
            False if hallucination is suspected.
        """
        if not content or not content.strip():
            return True  # empty content is not a hallucination

        lower = content.lower()

        # --- Self-contradiction check ---
        contradiction_hits = 0
        for word_a, word_b in _CONTRADICTION_PAIRS:
            if word_a in lower and word_b in lower:
                # Check if they appear close together (within 50 chars).
                idx_a = lower.find(word_a)
                idx_b = lower.find(word_b)
                if abs(idx_a - idx_b) < 80:
                    contradiction_hits += 1

        if contradiction_hits >= 2:
            return False

        # --- Unsubstantiated superlative check ---
        superlatives = _SUPERLATIVE_PATTERN.findall(content)
        hedges = _HEDGE_PATTERN.findall(content)

        # If many superlatives but no hedging at all, flag it.
        if len(superlatives) >= 3 and len(hedges) == 0:
            return False

        return True
