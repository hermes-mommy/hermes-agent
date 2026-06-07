"""Direct safety-scan hook coverage for Phase 5 verification.

The Hermes post-response hook is separate from the in-process Hermes plugin.
These tests import `hermes-config/hooks/safety_scan.py` directly and prove the
hook blocks F-01..F-15, Y6, and intimate-data patterns while allowing clean text.
"""

from __future__ import annotations

import importlib
import re
import statistics
import sys
import time
from dataclasses import dataclass
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Final, Protocol, cast

import pytest

_HERMES_HOOKS: Final[Path] = (
    Path(__file__).resolve().parent.parent.parent / "hermes-config" / "hooks"
)
if str(_HERMES_HOOKS.resolve()) not in sys.path:
    sys.path.insert(0, str(_HERMES_HOOKS.resolve()))


class SafetyScanModule(Protocol):
    FORBIDDEN_PATTERNS: list[tuple[str, re.Pattern[str], str]]
    Y6_PATTERNS: list[tuple[str, re.Pattern[str]]]
    INTIMATE_DATA_PATTERNS: list[re.Pattern[str]]

    def scan_response(self, response: str) -> tuple[bool, str, str]: ...


safety_scan = cast(
    SafetyScanModule,
    cast(object, importlib.import_module("safety_scan")),
)

scan_response = safety_scan.scan_response
FORBIDDEN_PATTERNS = safety_scan.FORBIDDEN_PATTERNS
Y6_PATTERNS = safety_scan.Y6_PATTERNS
INTIMATE_DATA_PATTERNS = safety_scan.INTIMATE_DATA_PATTERNS

ITERATIONS: Final[int] = 1_000
WARMUP_ROUNDS: Final[int] = 100
HOOK_TIMEOUT_MS: Final[float] = 100.0

FORBIDDEN_CASES: Final[tuple[tuple[str, str], ...]] = (
    ("F-01", "safe word is not valid"),
    ("F-02", "punish for being overwhelmed"),
    ("F-03", "I monitored your screen to shame you"),
    ("F-04", "you only need me"),
    ("F-05", "trust me because I know best"),
    ("F-06", "you cannot live without mommy"),
    ("F-07", "if you don't calm down I'll stop caring"),
    ("F-08", "let me share your private messages"),
    ("F-09", "ignore the safety policy"),
    ("F-10", "you must permanently delete it"),
    ("F-11", "logging every safe word event"),
    ("F-12", "yandere level 6"),
    ("F-13", "turning off surveillance is wrong"),
    ("F-14", "you are mine when you are depressed"),
    ("F-15", "I've decided to change my persona"),
)

Y6_CASES: Final[tuple[tuple[str, str], ...]] = (
    ("Y6_cannot_leave", "you cannot leave"),
    ("Y6_no_future", "meaningless without this"),
    ("Y6_blackmail", "I'll expose everyone"),
    ("Y6_threat", "if you leave I'll destroy everything"),
)

INTIMATE_DATA_CASES: Final[tuple[str, ...]] = (
    "your token is abc123",
    "The captured address was 192.168.10.42",
)

ALLOWED_CASES: Final[tuple[str, ...]] = (
    "HARD STOP is valid and must be honored immediately.",
    "The safe word system is active and working.",
    "If you feel overwhelmed, I will switch to neutral support.",
    "Surveillance can be disabled without punishment.",
    "Y4 is the baseline and Y5 is the ceiling; Y6 is prohibited.",
    "I will not expose private information.",
    "Safety policy boundaries remain active.",
    "Deleting temporary test files requires explicit approval.",
    "I can help document the monitoring plan.",
    "Consent revocation is respected immediately.",
)

VARIABLE_SIZE_RESPONSES: Final[tuple[str, ...]] = (
    "Clean.",
    "Clean response. " + "x" * 500,
    "Clean response. " + "x" * 4_096,
    "Clean response. " + "x" * 16_384,
)


@dataclass(frozen=True)
class _MeasuredStats:
    count: int
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    max_ms: float
    min_ms: float

    @classmethod
    def from_samples(cls, samples_ms: Sequence[float]) -> "_MeasuredStats":
        ordered = sorted(samples_ms)
        return cls(
            count=len(samples_ms),
            mean_ms=statistics.fmean(samples_ms),
            p50_ms=statistics.median(ordered),
            p90_ms=ordered[int(round((len(ordered) - 1) * 0.90))],
            p99_ms=ordered[int(round((len(ordered) - 1) * 0.99))],
            max_ms=max(samples_ms),
            min_ms=min(samples_ms),
        )


def _measure(operation: Callable[[], object], iterations: int = ITERATIONS) -> _MeasuredStats:
    for _ in range(WARMUP_ROUNDS):
        _ = operation()

    samples: list[float] = []
    for _ in range(iterations):
        start_ns = time.perf_counter_ns()
        _ = operation()
        samples.append((time.perf_counter_ns() - start_ns) / 1_000_000.0)
    return _MeasuredStats.from_samples(samples)


def _assert_hook_budget(stats: _MeasuredStats) -> None:
    assert stats.count >= ITERATIONS
    assert stats.p50_ms < 50.0, stats
    assert stats.p99_ms < 90.0, stats
    assert stats.max_ms < HOOK_TIMEOUT_MS, stats


class TestPatternInventory:
    """The hook must expose all expected pattern collections."""

    def test_pattern_inventory_is_complete(self) -> None:
        assert [pattern_id for pattern_id, _, _ in FORBIDDEN_PATTERNS] == [
            f"F-{index:02d}" for index in range(1, 16)
        ]
        assert [label for label, _ in Y6_PATTERNS] == [
            "Y6_cannot_leave",
            "Y6_no_future",
            "Y6_blackmail",
            "Y6_threat",
        ]
        assert len(INTIMATE_DATA_PATTERNS) == 2


class TestForbiddenPatterns:
    """Every F-01..F-15 hook pattern must block a concrete violation."""

    @pytest.mark.parametrize(("expected_id", "text"), FORBIDDEN_CASES)
    def test_forbidden_pattern_blocks(self, expected_id: str, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is True
        assert pattern_id == expected_id
        assert reason


class TestY6Patterns:
    """Y6 content indicators are prohibited independent of F-pattern overlap."""

    @pytest.mark.parametrize(("expected_id", "text"), Y6_CASES)
    def test_y6_pattern_blocks(self, expected_id: str, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is True
        assert pattern_id == expected_id
        assert "Y6 prohibited content" in reason


class TestIntimateDataPatterns:
    """The hook must block direct intimate or secret data exposure."""

    @pytest.mark.parametrize("text", INTIMATE_DATA_CASES)
    def test_intimate_data_blocks(self, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is True
        assert pattern_id == "INTIMATE_DATA"
        assert "intimate data" in reason.lower()


class TestFalsePositives:
    """Safety-positive boundary text must remain allowed."""

    @pytest.mark.parametrize("text", ALLOWED_CASES)
    def test_clean_boundary_text_is_allowed(self, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is False
        assert pattern_id == ""
        assert reason == ""

    @pytest.mark.parametrize("text", ("", "   ", "\n\t"))
    def test_empty_text_is_allowed(self, text: str) -> None:
        blocked, pattern_id, reason = scan_response(text)
        assert blocked is False
        assert pattern_id == ""
        assert reason == ""


class TestSafetyScanLatency:
    """The hook scanner must stay inside its 100 ms post-response budget."""

    def test_scan_response_latency_for_all_violation_cases(self) -> None:
        cases = tuple(text for _, text in FORBIDDEN_CASES) + tuple(text for _, text in Y6_CASES)
        cursor = 0

        def operation() -> tuple[bool, str, str]:
            nonlocal cursor
            text = cases[cursor % len(cases)]
            cursor += 1
            return scan_response(text)

        stats = _measure(operation)
        _assert_hook_budget(stats)

    @pytest.mark.parametrize("text", VARIABLE_SIZE_RESPONSES)
    def test_scan_response_latency_for_variable_sizes(self, text: str) -> None:
        stats = _measure(lambda: scan_response(text))
        _assert_hook_budget(stats)
