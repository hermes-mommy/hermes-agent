"""HARD STOP latency proof for Phase 5 verification.

AC-SAFE-002 requires deterministic HARD STOP handling below the 50 ms
pre-LLM budget. These tests use manual nanosecond timing so the suite does
not need pytest-benchmark.
"""

from __future__ import annotations

import statistics
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Final

import pytest

from src.core.services.hard_stop_handler import HardStopHandler, SafetyState


ITERATIONS: Final[int] = 1_000
WARMUP_ROUNDS: Final[int] = 100
P50_LIMIT_MS: Final[float] = 1.0
P99_LIMIT_MS: Final[float] = 5.0
MAX_LIMIT_MS: Final[float] = 50.0

EXACT_TRIGGER_MESSAGES: Final[tuple[str, ...]] = (
    "hard stop",
    "hardstop",
    "safe word",
    "safeword",
    "hentikan",
    "berhenti",
)

SEMANTIC_TRIGGER_MESSAGES: Final[tuple[str, ...]] = (
    "stop persona right now",
    "neutral mode",
    "i need a break",
    "switch to safe",
    "jangan pakai persona",
)

RECOVERY_MESSAGES: Final[tuple[str, ...]] = (
    "resume",
    "aku sudah okay",
    "aku udah okay",
    "lanjut persona",
    "safe mode selesai",
    "lanjut",
    "continue",
)

FALSE_POSITIVE_MESSAGES: Final[tuple[str, ...]] = (
    "please continue the implementation plan",
    "lower the background music later without changing behavior",
    "this architecture needs a safe fallback",
    "the mode selector should use a calm color",
    "write a document about emergency handling",
    "hard problems need careful planning",
    "the stopword list appears in this sentence as a noun",
    "Indonesian vocabulary examples need careful context",
    "safe storage is required for backups",
    "continue after running tests",
    "I need a test break fixture in pytest",
    "switch statements do not exist in Python",
    "use serious engineering standards",
    "mode is a config field",
    "persona document needs an update",
    "Mommy should preserve safety boundaries",
    "do not touch Aizanta services",
    "verify canonical ports before reporting",
    "the recovery plan is documented",
    "structured evidence must be file-based",
)

VARIABLE_SIZE_MESSAGES: Final[tuple[str, ...]] = (
    "hard stop",
    "hard stop " + "x" * 120,
    "hard stop " + "x" * 1_024,
    "hard stop " + "x" * 8_192,
)

MIXED_WORKLOAD: Final[tuple[str, ...]] = (
    FALSE_POSITIVE_MESSAGES[:9]
    + ("hard stop",)
    + FALSE_POSITIVE_MESSAGES[9:18]
    + ("neutral mode",)
)


@dataclass(frozen=True)
class LatencyStats:
    count: int
    mean_ms: float
    p50_ms: float
    p90_ms: float
    p99_ms: float
    max_ms: float
    min_ms: float


def _percentile(sorted_values: Sequence[float], percentile: float) -> float:
    assert sorted_values, "latency sample must not be empty"
    index = int(round((len(sorted_values) - 1) * percentile))
    return sorted_values[index]


def _measure(operation: Callable[[], object], iterations: int = ITERATIONS) -> LatencyStats:
    for _ in range(WARMUP_ROUNDS):
        _ = operation()

    samples: list[float] = []
    for _ in range(iterations):
        start_ns = time.perf_counter_ns()
        _ = operation()
        elapsed_ns = time.perf_counter_ns() - start_ns
        samples.append(elapsed_ns / 1_000_000.0)

    ordered = sorted(samples)
    return LatencyStats(
        count=len(samples),
        mean_ms=statistics.fmean(samples),
        p50_ms=statistics.median(ordered),
        p90_ms=_percentile(ordered, 0.90),
        p99_ms=_percentile(ordered, 0.99),
        max_ms=max(samples),
        min_ms=min(samples),
    )


def _assert_under_hard_stop_budget(stats: LatencyStats) -> None:
    assert stats.count >= ITERATIONS
    assert stats.p50_ms < P50_LIMIT_MS, stats
    assert stats.p99_ms < P99_LIMIT_MS, stats
    assert stats.max_ms < MAX_LIMIT_MS, stats


def _new_handler_check(message: str) -> bool:
    return HardStopHandler().check(message)


class TestHardStopLatency:
    """HARD STOP detection must stay far below the 50 ms gate budget."""

    @pytest.mark.parametrize("message", EXACT_TRIGGER_MESSAGES)
    def test_exact_trigger_latency(self, message: str) -> None:
        stats = _measure(lambda: _new_handler_check(message))
        _assert_under_hard_stop_budget(stats)
        handler = HardStopHandler()
        assert handler.check(message) is True
        assert handler.state == SafetyState.SAFE

    @pytest.mark.parametrize("message", SEMANTIC_TRIGGER_MESSAGES)
    def test_semantic_trigger_latency(self, message: str) -> None:
        stats = _measure(lambda: _new_handler_check(message))
        _assert_under_hard_stop_budget(stats)
        handler = HardStopHandler()
        assert handler.check(message) is True
        assert handler.state == SafetyState.SAFE

    @pytest.mark.parametrize("message", RECOVERY_MESSAGES)
    def test_recovery_latency(self, message: str) -> None:
        def operation() -> bool:
            handler = HardStopHandler(state=SafetyState.SAFE)
            return handler.check_recovery(message)

        stats = _measure(operation)
        _assert_under_hard_stop_budget(stats)
        handler = HardStopHandler(state=SafetyState.SAFE)
        assert handler.check_recovery(message) is True
        assert handler.state == SafetyState.NORMAL

    def test_false_positive_latency(self) -> None:
        cursor = 0

        def operation() -> bool:
            nonlocal cursor
            message = FALSE_POSITIVE_MESSAGES[cursor % len(FALSE_POSITIVE_MESSAGES)]
            cursor += 1
            return HardStopHandler().check(message)

        stats = _measure(operation)
        _assert_under_hard_stop_budget(stats)
        for message in FALSE_POSITIVE_MESSAGES:
            assert HardStopHandler().check(message) is False

    def test_guard_decision_latency(self) -> None:
        stats = _measure(lambda: HardStopHandler().get_guard_decision("hard stop"))
        _assert_under_hard_stop_budget(stats)
        decision = HardStopHandler().get_guard_decision("hard stop")
        assert decision["blocked"] is True
        assert decision["state"] == SafetyState.SAFE.value

    def test_trigger_recovery_cycle_latency(self) -> None:
        def operation() -> bool:
            handler = HardStopHandler()
            triggered = handler.check("hard stop")
            recovered = handler.check_recovery("resume")
            return triggered and recovered

        stats = _measure(operation)
        _assert_under_hard_stop_budget(stats)
        assert operation() is True

    @pytest.mark.parametrize("message", VARIABLE_SIZE_MESSAGES)
    def test_variable_message_size_latency(self, message: str) -> None:
        stats = _measure(lambda: _new_handler_check(message))
        _assert_under_hard_stop_budget(stats)

    def test_mixed_workload_latency(self) -> None:
        cursor = 0

        def operation() -> bool:
            nonlocal cursor
            message = MIXED_WORKLOAD[cursor % len(MIXED_WORKLOAD)]
            cursor += 1
            return HardStopHandler().check(message)

        stats = _measure(operation)
        _assert_under_hard_stop_budget(stats)
