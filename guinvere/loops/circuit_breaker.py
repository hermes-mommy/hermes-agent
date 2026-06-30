"""3-Layer Safety Circuit Breaker for autonomous loop execution.

Provides:
  Layer 1 — DependencyCircuitBreaker: per-dependency async circuit breaker
  Layer 2 — StuckDetector: hard-loop and soft-stall detection
  Layer 3 — SafetyGate: orchestrator combining L1 + L2 + HARD STOP check

Usage:
    gate = SafetyGate(hard_stop_checker=lambda: handler.is_safe)

    decision = await gate.pre_call("some_tool", '{"arg": 1}')
    if not decision.allowed:
        ...  # follow decision.action

    gate.post_call("some_tool", success=True, progress_delta=0.25)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

import structlog

logger = structlog.get_logger()


# ──────────────────────────────────────────────────────────────
# CircuitState enum
# ──────────────────────────────────────────────────────────────


class CircuitState(str, Enum):
    """State machine for DependencyCircuitBreaker."""

    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


# ──────────────────────────────────────────────────────────────
# StuckReport dataclass
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class StuckReport:
    """Report returned by StuckDetector.check()."""

    is_stuck: bool
    stuck_type: str | None  # "hard_loop" | "soft_stall" | None
    fingerprint: str | None  # repeated fingerprint if hard_loop
    repeat_count: int
    velocity_ratio: float  # current / baseline
    recommendation: str  # "continue" | "retry" | "skip" | "abort"
    detail: str


# ──────────────────────────────────────────────────────────────
# GateDecision dataclass
# ──────────────────────────────────────────────────────────────


@dataclass(frozen=True)
class GateDecision:
    """Decision returned by SafetyGate.pre_call()."""

    allowed: bool
    reason: str
    action: str  # "proceed" | "skip" | "retry" | "abort"
    detail: str = ""


# ──────────────────────────────────────────────────────────────
# Layer 1: DependencyCircuitBreaker
# ──────────────────────────────────────────────────────────────


class DependencyCircuitBreaker:
    """Per-dependency async circuit breaker.

    States:
        CLOSED  → normal operation, calls pass through
        OPEN    → tripped after ``fail_max`` consecutive failures
        HALF_OPEN → allows one test call after ``reset_timeout_s``

    Transitions:
        CLOSED → OPEN   : fail_max consecutive failures
        OPEN   → HALF_OPEN : reset_timeout_s elapsed (checked on next :meth:`call`)
        HALF_OPEN → CLOSED : test call succeeds
        HALF_OPEN → OPEN   : test call fails
    """

    def __init__(
        self,
        name: str,
        fail_max: int = 5,
        reset_timeout_s: float = 60.0,
    ) -> None:
        self._name = name
        self._fail_max = fail_max
        self._reset_timeout_s = reset_timeout_s
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._last_failure_time: float = 0.0
        self._lock = asyncio.Lock()
        logger.debug(
            "circuit_breaker_init",
            name=name,
            fail_max=fail_max,
            reset_timeout_s=reset_timeout_s,
        )

    # ── public API ────────────────────────────────────────

    @property
    def state(self) -> CircuitState:
        return self._state

    @property
    def name(self) -> str:
        return self._name

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* with circuit-breaker protection.

        Raises
            CircuitBreakerOpenError if the circuit is OPEN and the reset
            timeout has not yet elapsed.
        """
        async with self._lock:
            await self._try_reset()

            if self._state == CircuitState.OPEN:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self._name}' is OPEN — call rejected"
                )

            half_open_before = self._state == CircuitState.HALF_OPEN

        # Execute outside the lock so we don't block other callers
        # waiting on the same breaker.
        try:
            if asyncio.iscoroutinefunction(func):
                result = await func(*args, **kwargs)
            else:
                result = func(*args, **kwargs)
        except BaseException:
            await self._record_failure()
            raise

        if half_open_before:
            # Success in HALF_OPEN → reset to CLOSED
            await self._record_success()
        else:
            # Success in CLOSED → just reset the failure count
            async with self._lock:
                self._failure_count = 0

        return result

    async def _record_success(self) -> None:
        """Reset state after a successful call in HALF_OPEN."""
        async with self._lock:
            logger.info(
                "circuit_breaker_closed",
                name=self._name,
            )
            self._state = CircuitState.CLOSED
            self._failure_count = 0

    async def _record_failure(self) -> None:
        """Increment failure count and potentially trip to OPEN."""
        async with self._lock:
            self._failure_count += 1
            self._last_failure_time = time.time()
            logger.warning(
                "circuit_breaker_failure",
                name=self._name,
                failure_count=self._failure_count,
                fail_max=self._fail_max,
            )
            if self._failure_count >= self._fail_max:
                self._state = CircuitState.OPEN
                logger.warning(
                    "circuit_breaker_opened",
                    name=self._name,
                    failure_count=self._failure_count,
                )

    async def _try_reset(self) -> None:
        """Transition from OPEN → HALF_OPEN if reset timeout has elapsed."""
        if self._state != CircuitState.OPEN:
            return
        elapsed = time.time() - self._last_failure_time
        if elapsed >= self._reset_timeout_s:
            self._state = CircuitState.HALF_OPEN
            logger.info(
                "circuit_breaker_half_open",
                name=self._name,
                elapsed_s=round(elapsed, 1),
            )


class CircuitBreakerOpenError(Exception):
    """Raised when a call is rejected because the circuit is OPEN."""


# ──────────────────────────────────────────────────────────────
# Layer 2: StuckDetector
# ──────────────────────────────────────────────────────────────


class StuckDetector:
    """Detects when a loop is stuck in a hard loop or soft stall.

    Hard loop:
        Same tool-call fingerprint (name + args hash) repeated
        ``hard_loop_threshold``+ times consecutively.

    Soft stall:
        Progress velocity drops below ``soft_stall_velocity_pct`` of
        the baseline for ``soft_stall_steps``+ consecutive steps.
    """

    def __init__(
        self,
        hard_loop_threshold: int = 3,
        soft_stall_velocity_pct: float = 0.20,
        soft_stall_steps: int = 5,
    ) -> None:
        self._hard_loop_threshold = hard_loop_threshold
        self._soft_stall_velocity_pct = soft_stall_velocity_pct
        self._soft_stall_steps = soft_stall_steps
        self._fingerprint_history: list[str] = []
        self._velocity_history: list[float] = []
        self._baseline_velocity: float = 1.0

    # ── recorders ─────────────────────────────────────────

    def record_tool_call(self, tool_name: str, arguments: str) -> None:
        """Record a tool-call fingerprint for hard-loop detection."""
        raw = f"{tool_name}:{arguments}"
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()[:16]
        self._fingerprint_history.append(fingerprint)

    def record_progress(self, progress_delta: float) -> None:
        """Record normalised progress delta (0.0-1.0) for soft-stall detection.

        The baseline is computed after the first 5 recordings.
        """
        self._velocity_history.append(progress_delta)
        if len(self._velocity_history) == 5:
            self._baseline_velocity = sum(self._velocity_history) / 5.0
            logger.debug(
                "stuck_detector_baseline",
                baseline_velocity=round(self._baseline_velocity, 4),
            )

    # ── check ─────────────────────────────────────────────

    def check(self) -> StuckReport:
        """Check for stuck conditions and return a StuckReport.

        Hard-loop detection is checked first; if both conditions are
        present the hard-loop report takes precedence.
        """
        # ── Hard loop ──────────────────────────────────────
        if len(self._fingerprint_history) >= self._hard_loop_threshold:
            recent = self._fingerprint_history[-self._hard_loop_threshold :]
            if len(set(recent)) == 1:
                repeat_count = self._count_consecutive_fingerprint(recent[0])
                return StuckReport(
                    is_stuck=True,
                    stuck_type="hard_loop",
                    fingerprint=recent[0],
                    repeat_count=repeat_count,
                    velocity_ratio=self._current_velocity_ratio(),
                    recommendation="abort",
                    detail=(
                        f"Hard loop detected: tool fingerprint {recent[0]} "
                        f"repeated {repeat_count} times"
                    ),
                )

        # ── Soft stall ─────────────────────────────────────
        current_ratio = self._current_velocity_ratio()
        stall_detected = self._check_soft_stall()

        if stall_detected:
            return StuckReport(
                is_stuck=True,
                stuck_type="soft_stall",
                fingerprint=None,
                repeat_count=0,
                velocity_ratio=current_ratio,
                recommendation="retry",
                detail=(
                    f"Soft stall detected: velocity ratio {current_ratio:.3f} "
                    f"below threshold {self._soft_stall_velocity_pct} "
                    f"for {self._soft_stall_steps}+ steps"
                ),
            )

        return StuckReport(
            is_stuck=False,
            stuck_type=None,
            fingerprint=None,
            repeat_count=0,
            velocity_ratio=current_ratio,
            recommendation="continue",
            detail="No stuck condition detected",
        )

    # ── helpers ────────────────────────────────────────────

    def _count_consecutive_fingerprint(self, fingerprint: str) -> int:
        """Count how many consecutive entries match *fingerprint* from the end."""
        count = 0
        for f in reversed(self._fingerprint_history):
            if f == fingerprint:
                count += 1
            else:
                break
        return count

    def _current_velocity_ratio(self) -> float:
        """Return (recent average) / (baseline), or 1.0 if insufficient data."""
        if len(self._velocity_history) < 5:
            return 1.0
        recent = self._velocity_history[-min(5, len(self._velocity_history)) :]
        avg_recent = sum(recent) / len(recent)
        if self._baseline_velocity <= 0:
            return 1.0
        return avg_recent / self._baseline_velocity

    def _check_soft_stall(self) -> bool:
        """Return True if soft-stall condition is met."""
        needed = 5 + self._soft_stall_steps  # 5 baseline + stall window
        if len(self._velocity_history) < needed:
            return False
        recent = self._velocity_history[-self._soft_stall_steps :]
        avg_recent = sum(recent) / len(recent)
        if self._baseline_velocity <= 0:
            return False
        ratio = avg_recent / self._baseline_velocity
        return ratio < self._soft_stall_velocity_pct

    # ── reset ─────────────────────────────────────────────

    def reset(self) -> None:
        """Reset all tracking state."""
        self._fingerprint_history.clear()
        self._velocity_history.clear()
        self._baseline_velocity = 1.0
        logger.debug("stuck_detector_reset")


# ──────────────────────────────────────────────────────────────
# Layer 3: SafetyGate (orchestrator)
# ──────────────────────────────────────────────────────────────


class SafetyGate:
    """Orchestrates all 3 safety layers.

    Before each tool call or LLM call::

        decision = await gate.pre_call(tool_name, arguments)
        if not decision.allowed:
            ...  # follow decision.action

    After each call::

        gate.post_call(tool_name, success=True, progress_delta=0.25)

    The gate checks:
        1. HARD STOP active → abort immediately
        2. Circuit breaker OPEN for this dependency → skip
        3. Stuck detector triggered → follow recommendation
    """

    def __init__(
        self,
        hard_stop_checker: Callable[[], bool],
        circuit_breakers: dict[str, DependencyCircuitBreaker] | None = None,
        stuck_detector: StuckDetector | None = None,
    ) -> None:
        self._hard_stop_checker = hard_stop_checker
        self._breakers = circuit_breakers or {}
        self._stuck = stuck_detector or StuckDetector()
        logger.info(
            "safety_gate_init",
            breaker_count=len(self._breakers),
            stuck_detector_wired=stuck_detector is not None,
        )

    # ── breaker access ────────────────────────────────────

    def get_breaker(self, dependency_name: str) -> DependencyCircuitBreaker:
        """Get or create a circuit breaker for *dependency_name*."""
        if dependency_name not in self._breakers:
            self._breakers[dependency_name] = DependencyCircuitBreaker(
                name=dependency_name,
            )
            logger.debug("safety_gate.new_breaker", name=dependency_name)
        return self._breakers[dependency_name]

    # ── pre-call gate ─────────────────────────────────────

    async def pre_call(self, tool_name: str, arguments: str = "") -> GateDecision:
        """Evaluate all safety layers before a call executes.

        Order of checks:
            1. HARD STOP (L3)
            2. Circuit breaker (L1)
            3. Stuck detector (L2)
        """
        # L3: HARD STOP check
        if self._hard_stop_checker():
            logger.warning("safety_gate.hard_stop_active", tool=tool_name)
            return GateDecision(
                allowed=False,
                reason="HARD_STOP_ACTIVE",
                action="abort",
                detail="HARD STOP protocol is active — all operations aborted",
            )

        # L1: Circuit breaker check
        breaker = self.get_breaker(tool_name)
        if breaker.state == CircuitState.OPEN:
            logger.warning(
                "safety_gate.circuit_open",
                tool=tool_name,
                breaker_name=breaker.name,
            )
            return GateDecision(
                allowed=False,
                reason=f"CIRCUIT_OPEN:{tool_name}",
                action="skip",
                detail=f"Circuit breaker '{breaker.name}' is OPEN — call skipped",
            )

        # L2: Stuck detector check
        stuck_report = self._stuck.check()
        if stuck_report.is_stuck:
            logger.warning(
                "safety_gate.stuck_detected",
                tool=tool_name,
                stuck_type=stuck_report.stuck_type,
                recommendation=stuck_report.recommendation,
            )
            return GateDecision(
                allowed=stuck_report.recommendation != "abort",
                reason=f"STUCK:{stuck_report.stuck_type}",
                action=stuck_report.recommendation,
                detail=stuck_report.detail,
            )

        # Record the tool-call fingerprint for future stuck detection
        self._stuck.record_tool_call(tool_name, arguments)

        return GateDecision(allowed=True, reason="OK", action="proceed")

    # ── post-call gate ────────────────────────────────────

    def post_call(
        self,
        tool_name: str,
        success: bool,
        progress_delta: float = 0.0,
    ) -> None:
        """Record call result for circuit-breaker + stuck-detector state updates.

        This method is fire-and-forget (non-blocking). Circuit-breaker
        state transitions are scheduled as background tasks.
        """
        self._stuck.record_progress(progress_delta)

        breaker = self.get_breaker(tool_name)
        if success:
            # Reset failure count on success
            asyncio.ensure_future(breaker._record_success())
        else:
            asyncio.ensure_future(breaker._record_failure())
