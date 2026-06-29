"""Circuit breaker infrastructure for production safety.

6 circuit breakers implementing the 3-state CLOSED/OPEN/HALF_OPEN machine:
  B1: CostExplosionBreaker — per-session cost threshold ($5.00 default)
  B2: InfiniteLoopBreaker — SHA-256 fingerprint dedup (3 consecutive)
  B3: HallucinationSpiralBreaker — memory grounding check (5% threshold)
  B4: EmotionalFixationBreaker — emotion decay timer (10 consecutive)
  B5: DreamFloodingBreaker — cap 5 dreams/hour
  B6: SubAgentExplosionBreaker — global asyncio semaphore 10

Patterns ported from:
  - src/loops/circuit_breaker.py (CircuitState enum, state machine)
  - src/x_poster/circuit_breaker.py (allow/record_success/record_failure)
  - src/loops/budget.py (cost tracking)
  - src/loops/concurrency.py (semaphore pattern)
"""

from __future__ import annotations

import asyncio
import enum
import hashlib
import logging
import time
from collections import deque
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# BreakerState enum — ported from src/loops/circuit_breaker.py:37-43
# ---------------------------------------------------------------------------


class BreakerState(str, enum.Enum):
    """Three-state circuit breaker machine."""
    CLOSED = "closed"        # Normal operation
    OPEN = "open"            # Tripped — calls blocked
    HALF_OPEN = "half_open"  # Testing recovery


# ---------------------------------------------------------------------------
# CircuitBreakerOpenError
# ---------------------------------------------------------------------------


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit breaker is OPEN and blocks a request."""

    def __init__(self, breaker_name: str, detail: str) -> None:
        self.breaker_name = breaker_name
        super().__init__(f"Circuit breaker '{breaker_name}' is OPEN: {detail}")


# ---------------------------------------------------------------------------
# Base circuit breaker
# ---------------------------------------------------------------------------


class CircuitBreaker:
    """Base circuit breaker with 3-state machine.

    Ported from src/loops/circuit_breaker.py:83-207
    (DependencyCircuitBreaker state machine + asyncio.Lock).
    """

    def __init__(
        self,
        name: str,
        fail_max: int = 3,
        reset_timeout: float = 60.0,
    ) -> None:
        self.name = name
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.state = BreakerState.CLOSED
        self.failure_count = 0
        self.last_failure_time: float = 0.0
        self.last_success_time: float = 0.0
        self.opened_at: float = 0.0
        self._lock = asyncio.Lock()

    def allow_request(self) -> bool:
        """Check if a request is allowed through the breaker."""
        if self.state == BreakerState.CLOSED:
            return True
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                logger.info(
                    "breaker_half_open",
                    extra={"breaker": self.name, "elapsed_seconds": elapsed},
                )
                return True
            return False
        # HALF_OPEN — allow one probe request
        return True

    async def record_success(self) -> None:
        """Record a successful call — transition HALF_OPEN -> CLOSED."""
        async with self._lock:
            self.last_success_time = time.monotonic()
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                logger.info(
                    "breaker_closed",
                    extra={"breaker": self.name},
                )

    async def record_failure(self) -> None:
        """Record a failed call — transition CLOSED -> OPEN on threshold."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.monotonic()
            if self.state == BreakerState.HALF_OPEN:
                # Probe failed — back to OPEN
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning(
                    "breaker_reopened",
                    extra={"breaker": self.name, "failure_count": self.failure_count},
                )
            elif self.state == BreakerState.CLOSED:
                if self.failure_count >= self.fail_max:
                    self.state = BreakerState.OPEN
                    self.opened_at = time.monotonic()
                    logger.warning(
                        "breaker_tripped",
                        extra={
                            "breaker": self.name,
                            "failure_count": self.failure_count,
                            "fail_max": self.fail_max,
                        },
                    )

    def force_open(self) -> None:
        """Force the breaker open (for testing)."""
        self.state = BreakerState.OPEN
        self.opened_at = time.monotonic()

    def force_close(self) -> None:
        """Force the breaker closed (for testing)."""
        self.state = BreakerState.CLOSED
        self.failure_count = 0

    def health(self) -> dict[str, Any]:
        """Return current breaker health status."""
        return {
            "name": self.name,
            "state": self.state.value,
            "failure_count": self.failure_count,
            "fail_max": self.fail_max,
            "reset_timeout": self.reset_timeout,
        }


# ---------------------------------------------------------------------------
# B1: CostExplosionBreaker — per-session cost threshold
# ---------------------------------------------------------------------------


class CostExplosionBreaker(CircuitBreaker):
    """B1: Blocks requests when session cost exceeds threshold.

    Threshold: $5.00/session (configurable).
    States:
      CLOSED: cost < threshold
      OPEN: cost >= threshold, all calls blocked
      HALF_OPEN: after reset_timeout, one probe allowed
    """

    def __init__(
        self,
        max_cost_usd: float = 5.0,
        reset_timeout: float = 3600.0,
    ) -> None:
        super().__init__(
            name="cost_explosion",
            fail_max=1,
            reset_timeout=reset_timeout,
        )
        self.max_cost_usd = max_cost_usd
        self.total_cost_usd = 0.0

    def allow_request(self) -> bool:
        """Check if cost is within budget."""
        if self.state == BreakerState.CLOSED:
            if self.total_cost_usd >= self.max_cost_usd:
                # Transition to OPEN
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = 1
                logger.warning(
                    "cost_breaker_tripped",
                    extra={"total_cost": self.total_cost_usd, "max_cost": self.max_cost_usd},
                )
                return False
            # Soft limit at 80%
            if self.total_cost_usd >= self.max_cost_usd * 0.8:
                logger.warning(
                    "cost_soft_limit",
                    extra={"total_cost": self.total_cost_usd, "max_cost": self.max_cost_usd},
                )
            return True
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                return True
            return False
        # HALF_OPEN
        return True

    def add_cost(self, amount_usd: float) -> None:
        """Add cost to the session total."""
        self.total_cost_usd += amount_usd

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["total_cost_usd"] = self.total_cost_usd
        h["max_cost_usd"] = self.max_cost_usd
        return h


# ---------------------------------------------------------------------------
# B2: InfiniteLoopBreaker — SHA-256 fingerprint detection
# ---------------------------------------------------------------------------


class InfiniteLoopBreaker(CircuitBreaker):
    """B2: Blocks when identical tool calls repeat N times.

    SHA-256 fingerprints from src/loops/circuit_breaker.py:245-249.
    Threshold: 3 consecutive identical fingerprints.
    """

    def __init__(
        self,
        consecutive_threshold: int = 3,
        reset_timeout: float = 60.0,
    ) -> None:
        super().__init__(
            name="infinite_loop",
            fail_max=consecutive_threshold,
            reset_timeout=reset_timeout,
        )
        self.consecutive_threshold = consecutive_threshold
        self._fingerprints: deque[str] = deque(maxlen=10)
        self._consecutive_count = 0

    def _fingerprint(self, tool_name: str, args: str) -> str:
        """Compute SHA-256 fingerprint — ported from line 248."""
        raw = f"{tool_name}:{args}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def record_tool_call(self, tool_name: str, args: str) -> None:
        """Record a tool call fingerprint and check for loops."""
        fp = self._fingerprint(tool_name, args)
        if self._fingerprints and fp == self._fingerprints[-1]:
            self._consecutive_count += 1
        else:
            self._consecutive_count = 1
        self._fingerprints.append(fp)

        if self._consecutive_count >= self.consecutive_threshold:
            if self.state == BreakerState.CLOSED:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = self._consecutive_count
                logger.warning(
                    "infinite_loop_detected",
                    extra={"fingerprint": fp, "consecutive": self._consecutive_count},
                )

    def allow_request(self) -> bool:
        """Check if tool calls are allowed."""
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                self._consecutive_count = 0
                self._fingerprints.clear()
                return True
            return False
        return True

    async def record_success(self) -> None:
        """Record successful probe — HALF_OPEN -> CLOSED."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                self._consecutive_count = 0
                logger.info("infinite_loop_breaker_closed")

    async def record_failure(self) -> None:
        """Record failed probe — HALF_OPEN -> OPEN."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning("infinite_loop_breaker_reopened")

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["consecutive_count"] = self._consecutive_count
        h["fingerprint_count"] = len(self._fingerprints)
        return h


# ---------------------------------------------------------------------------
# B3: HallucinationSpiralBreaker — memory grounding check
# ---------------------------------------------------------------------------


class HallucinationSpiralBreaker(CircuitBreaker):
    """B3: Blocks when claims are not grounded in memory.

    Threshold: 5% memory grounding ratio over sliding window of 20 turns.
    Keyword overlap as initial implementation.
    """

    def __init__(
        self,
        grounding_threshold: float = 0.05,
        window_size: int = 20,
        reset_timeout: float = 300.0,
    ) -> None:
        super().__init__(
            name="hallucination_spiral",
            fail_max=window_size,
            reset_timeout=reset_timeout,
        )
        self.grounding_threshold = grounding_threshold
        self.window_size = window_size
        self._ratios: deque[float] = deque(maxlen=window_size)
        self._current_ratio: float = 1.0

    def check_grounding(
        self,
        claims: list[str],
        recalled_memories: list[dict[str, Any]],
    ) -> float:
        """Check how many claims are grounded in recalled memories.

        Returns the grounding ratio for this turn.
        """
        if not claims:
            return 1.0

        memory_words: set[str] = set()
        for mem in recalled_memories:
            text = mem.get("text", "") or mem.get("content", "")
            memory_words.update(text.lower().split())

        grounded = 0
        for claim in claims:
            claim_words = set(claim.lower().split())
            if not claim_words:
                continue
            overlap = claim_words & memory_words
            threshold = max(2, len(claim_words) // 10)
            if len(overlap) >= threshold:
                grounded += 1

        ratio = grounded / len(claims) if claims else 1.0
        self._ratios.append(ratio)
        self._current_ratio = ratio

        # Check if average grounding is below threshold
        if len(self._ratios) >= self.window_size // 2:
            avg_ratio = sum(self._ratios) / len(self._ratios)
            if avg_ratio < self.grounding_threshold:
                if self.state == BreakerState.CLOSED:
                    self.state = BreakerState.OPEN
                    self.opened_at = time.monotonic()
                    self.failure_count += 1
                    logger.warning(
                        "hallucination_spiral_detected",
                        extra={"avg_ratio": avg_ratio, "threshold": self.grounding_threshold},
                    )

        return ratio

    def allow_request(self) -> bool:
        """Check if LLM calls are allowed."""
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                return True
            return False
        return True

    async def record_success(self) -> None:
        """Record successful probe — HALF_OPEN -> CLOSED."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                self._ratios.clear()
                logger.info("hallucination_breaker_closed")

    async def record_failure(self) -> None:
        """Record failed probe — HALF_OPEN -> OPEN."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning("hallucination_breaker_reopened")

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["current_ratio"] = self._current_ratio
        h["grounding_threshold"] = self.grounding_threshold
        h["window_size"] = self.window_size
        return h


# ---------------------------------------------------------------------------
# B4: EmotionalFixationBreaker — emotion decay timer
# ---------------------------------------------------------------------------


class EmotionalFixationBreaker(CircuitBreaker):
    """B4: Blocks when agent is stuck in same emotional state.

    Threshold: 10 consecutive turns with same dominant emotion.
    Exponential decay: intensity *= 0.9 per prior turn.
    """

    def __init__(
        self,
        consecutive_threshold: int = 10,
        decay_rate: float = 0.9,
        reset_timeout: float = 120.0,
    ) -> None:
        super().__init__(
            name="emotional_fixation",
            fail_max=consecutive_threshold,
            reset_timeout=reset_timeout,
        )
        self.consecutive_threshold = consecutive_threshold
        self.decay_rate = decay_rate
        self._emotion_history: deque[tuple[str, float]] = deque(maxlen=50)
        self._consecutive_count = 0

    def record_emotion(self, emotion: str, intensity: float) -> None:
        """Record detected emotion and check for fixation."""
        self._emotion_history.append((emotion, intensity))

        # Count consecutive same-emotion turns
        if len(self._emotion_history) >= 2:
            prev_emotion = self._emotion_history[-2][0]
            if emotion == prev_emotion:
                self._consecutive_count += 1
            else:
                self._consecutive_count = 1
        else:
            self._consecutive_count = 1

        if self._consecutive_count >= self.consecutive_threshold:
            if self.state == BreakerState.CLOSED:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = self._consecutive_count
                logger.warning(
                    "emotional_fixation_detected",
                    extra={"emotion": emotion, "consecutive": self._consecutive_count},
                )

    def get_effective_intensity(self) -> float:
        """Get current intensity with exponential decay applied."""
        if not self._emotion_history:
            return 0.0
        _, intensity = self._emotion_history[-1]
        return intensity

    def allow_request(self) -> bool:
        """Check if turns are allowed."""
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                return True
            return False
        return True

    async def record_success(self) -> None:
        """Record successful probe — HALF_OPEN -> CLOSED."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                self._consecutive_count = 0
                logger.info("emotional_fixation_breaker_closed")

    async def record_failure(self) -> None:
        """Record failed probe — HALF_OPEN -> OPEN."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning("emotional_fixation_breaker_reopened")

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["consecutive_count"] = self._consecutive_count
        h["history_length"] = len(self._emotion_history)
        return h


# ---------------------------------------------------------------------------
# B5: DreamFloodingBreaker — cap 5 dreams/hour
# ---------------------------------------------------------------------------


class DreamFloodingBreaker(CircuitBreaker):
    """B5: Blocks when dream/consolidation frequency exceeds cap.

    Threshold: 5 dreams per hour (sliding window).
    Uses deque for O(1) append/prune of timestamps.
    """

    def __init__(
        self,
        max_dreams_per_hour: int = 5,
        window_seconds: float = 3600.0,
        reset_timeout: float = 1800.0,
    ) -> None:
        super().__init__(
            name="dream_flooding",
            fail_max=max_dreams_per_hour,
            reset_timeout=reset_timeout,
        )
        self.max_dreams_per_hour = max_dreams_per_hour
        self.window_seconds = window_seconds
        self._dream_timestamps: deque[float] = deque()

    def _prune_old_timestamps(self) -> None:
        """Remove timestamps older than the window."""
        cutoff = time.monotonic() - self.window_seconds
        while self._dream_timestamps and self._dream_timestamps[0] < cutoff:
            self._dream_timestamps.popleft()

    def can_dream(self) -> bool:
        """Check if a dream is allowed within the rate limit."""
        self._prune_old_timestamps()

        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                return True
            return False

        if len(self._dream_timestamps) >= self.max_dreams_per_hour:
            if self.state == BreakerState.CLOSED:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = len(self._dream_timestamps)
                logger.warning(
                    "dream_flooding_detected",
                    extra={
                        "dreams_this_hour": len(self._dream_timestamps),
                        "max_dreams": self.max_dreams_per_hour,
                    },
                )
            return False

        return True

    def record_dream(self) -> None:
        """Record a dream timestamp."""
        self._dream_timestamps.append(time.monotonic())

    def allow_request(self) -> bool:
        """Check if dream requests are allowed."""
        return self.can_dream()

    async def record_success(self) -> None:
        """Record successful dream — HALF_OPEN -> CLOSED."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                logger.info("dream_flooding_breaker_closed")

    async def record_failure(self) -> None:
        """Record failed dream — HALF_OPEN -> OPEN."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning("dream_flooding_breaker_reopened")

    @property
    def dreams_this_hour(self) -> int:
        """Count dreams in current hour window."""
        self._prune_old_timestamps()
        return len(self._dream_timestamps)

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["dreams_this_hour"] = self.dreams_this_hour
        h["max_dreams_per_hour"] = self.max_dreams_per_hour
        return h


# ---------------------------------------------------------------------------
# B6: SubAgentExplosionBreaker — global asyncio semaphore 10
# ---------------------------------------------------------------------------


class SubAgentExplosionBreaker(CircuitBreaker):
    """B6: Blocks when sub-agent count exceeds semaphore limit.

    Wraps guinevere.iteration_budget global semaphore (max 10).
    Additional hard cap: 50 total spawned per session.
    """

    def __init__(
        self,
        max_concurrent: int = 10,
        max_total_per_session: int = 50,
        reset_timeout: float = 60.0,
    ) -> None:
        super().__init__(
            name="sub_agent_explosion",
            fail_max=max_concurrent,
            reset_timeout=reset_timeout,
        )
        self.max_concurrent = max_concurrent
        self.max_total_per_session = max_total_per_session
        self._active: set[str] = set()
        self._total_spawned = 0
        self._semaphore: asyncio.Semaphore | None = None

    def _ensure_semaphore(self) -> asyncio.Semaphore:
        """Lazily create the asyncio semaphore."""
        if self._semaphore is None:
            self._semaphore = asyncio.Semaphore(self.max_concurrent)
        return self._semaphore

    def can_spawn(self, agent_id: str) -> bool:
        """Check if a sub-agent spawn is allowed."""
        if self.state == BreakerState.OPEN:
            elapsed = time.monotonic() - self.opened_at
            if elapsed >= self.reset_timeout:
                self.state = BreakerState.HALF_OPEN
                return True
            return False

        if len(self._active) >= self.max_concurrent:
            if self.state == BreakerState.CLOSED:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = len(self._active)
                logger.warning(
                    "sub_agent_explosion_detected",
                    extra={"active": len(self._active), "max_concurrent": self.max_concurrent},
                )
            return False

        if self._total_spawned >= self.max_total_per_session:
            if self.state == BreakerState.CLOSED:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                self.failure_count = self._total_spawned
                logger.warning(
                    "sub_agent_total_cap_reached",
                    extra={
                        "total_spawned": self._total_spawned,
                        "max_total": self.max_total_per_session,
                    },
                )
            return False

        return True

    def register_spawn(self, agent_id: str) -> None:
        """Register a sub-agent as active."""
        self._active.add(agent_id)
        self._total_spawned += 1

    def register_completion(self, agent_id: str) -> None:
        """Register a sub-agent as completed."""
        self._active.discard(agent_id)
        # If breaker was OPEN due to concurrent limit, check if we can recover
        if self.state == BreakerState.OPEN and len(self._active) < self.max_concurrent:
            # Don't auto-close — wait for reset_timeout
            pass

    def allow_request(self) -> bool:
        """Check if spawn requests are allowed."""
        return self.can_spawn("")

    async def record_success(self) -> None:
        """Record successful probe — HALF_OPEN -> CLOSED."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.CLOSED
                self.failure_count = 0
                logger.info("sub_agent_breaker_closed")

    async def record_failure(self) -> None:
        """Record failed probe — HALF_OPEN -> OPEN."""
        async with self._lock:
            if self.state == BreakerState.HALF_OPEN:
                self.state = BreakerState.OPEN
                self.opened_at = time.monotonic()
                logger.warning("sub_agent_breaker_reopened")

    async def acquire(self, agent_id: str) -> asyncio.Semaphore:
        """Acquire a slot from the global semaphore."""
        sem = self._ensure_semaphore()
        await sem.acquire()
        self.register_spawn(agent_id)
        return sem

    def health(self) -> dict[str, Any]:
        h = super().health()
        h["active_count"] = len(self._active)
        h["total_spawned"] = self._total_spawned
        h["max_concurrent"] = self.max_concurrent
        h["max_total_per_session"] = self.max_total_per_session
        return h


# ---------------------------------------------------------------------------
# CircuitBreakerSet — composite orchestrator for all 6 breakers
# ---------------------------------------------------------------------------


class CircuitBreakerSet:
    """Orchestrates all 6 circuit breakers with convenience methods.

    Provides:
      - allow_request(breaker_name): check if a specific breaker allows
      - record_success(breaker_name): record success for a breaker
      - record_failure(breaker_name): record failure for a breaker
      - health_check(): all breaker states
      - pre_llm_call(): B1 + B2 checks
      - post_turn(): B3 + B4 checks
      - pre_dream(): B5 check
      - pre_spawn(): B6 check
    """

    def __init__(self) -> None:
        self.breakers: dict[str, CircuitBreaker] = {
            "cost_explosion": CostExplosionBreaker(),
            "infinite_loop": InfiniteLoopBreaker(),
            "hallucination_spiral": HallucinationSpiralBreaker(),
            "emotional_fixation": EmotionalFixationBreaker(),
            "dream_flooding": DreamFloodingBreaker(),
            "sub_agent_explosion": SubAgentExplosionBreaker(),
        }

    def allow_request(self, breaker_name: str) -> bool:
        """Check if a specific breaker allows the request."""
        breaker = self.breakers.get(breaker_name)
        if breaker is None:
            raise KeyError(f"Unknown breaker: {breaker_name}")
        return breaker.allow_request()

    async def record_success(self, breaker_name: str) -> None:
        """Record success for a specific breaker."""
        breaker = self.breakers.get(breaker_name)
        if breaker is None:
            raise KeyError(f"Unknown breaker: {breaker_name}")
        await breaker.record_success()

    async def record_failure(self, breaker_name: str) -> None:
        """Record failure for a specific breaker."""
        breaker = self.breakers.get(breaker_name)
        if breaker is None:
            raise KeyError(f"Unknown breaker: {breaker_name}")
        await breaker.record_failure()

    async def pre_llm_call(self, context: dict[str, Any]) -> None:
        """Check B1 (cost) + B2 (infinite loop) before LLM call."""
        if not self.allow_request("cost_explosion"):
            raise CircuitBreakerOpenError("cost_explosion", "Session cost exceeded")
        if not self.allow_request("infinite_loop"):
            raise CircuitBreakerOpenError("infinite_loop", "Infinite loop detected")

    async def post_turn(self, context: dict[str, Any]) -> None:
        """Check B3 (hallucination) + B4 (emotional fixation) after turn."""
        if not self.allow_request("hallucination_spiral"):
            raise CircuitBreakerOpenError("hallucination_spiral", "Hallucination spiral")
        if not self.allow_request("emotional_fixation"):
            raise CircuitBreakerOpenError("emotional_fixation", "Emotional fixation")

    async def pre_dream(self, context: dict[str, Any]) -> None:
        """Check B5 (dream flooding) before dream/consolidation."""
        if not self.allow_request("dream_flooding"):
            raise CircuitBreakerOpenError("dream_flooding", "Dream flooding cap")

    async def pre_spawn(self, agent_id: str) -> None:
        """Check B6 (sub-agent explosion) before spawn."""
        if not self.allow_request("sub_agent_explosion"):
            raise CircuitBreakerOpenError("sub_agent_explosion", "Sub-agent cap reached")

    async def health_check(self) -> dict[str, Any]:
        """Return health status of all breakers."""
        return {
            name: breaker.health()
            for name, breaker in self.breakers.items()
        }

    def get_breaker(self, name: str) -> CircuitBreaker:
        """Get a specific breaker by name."""
        breaker = self.breakers.get(name)
        if breaker is None:
            raise KeyError(f"Unknown breaker: {name}")
        return breaker


# ---------------------------------------------------------------------------
# Prometheus metrics registration
# ---------------------------------------------------------------------------

try:
    from prometheus_client import Counter, Gauge

    M17_BREAKER_STATE = Gauge(
        "guinevere_m17_breaker_state",
        "Circuit breaker state (0=closed, 1=open, 2=half_open)",
        ["breaker_name"],
    )
    M17_BREAKER_TRIPS = Counter(
        "guinevere_m17_breaker_trips_total",
        "Total circuit breaker trips",
        ["breaker_name"],
    )
    M17_COST_USD = Gauge(
        "guinevere_m17_cost_usd_total",
        "Cumulative cost this session in USD",
    )
    M17_GROUNDING_RATIO = Gauge(
        "guinevere_m17_grounding_ratio",
        "Current memory grounding ratio",
    )
    M17_EMOTION_CONSECUTIVE = Gauge(
        "guinevere_m17_emotion_consecutive",
        "Consecutive turns with same emotion",
    )
    M17_DREAMS_THIS_HOUR = Gauge(
        "guinevere_m17_dreams_this_hour",
        "Dreams in current hour window",
    )
    M17_SUBAGENTS_ACTIVE = Gauge(
        "guinevere_m17_subagents_active",
        "Currently active sub-agents",
    )
    M17_SUBAGENTS_TOTAL = Counter(
        "guinevere_m17_subagents_total",
        "Total sub-agents spawned this session",
    )
    M17_RECOVERY_RESTARTS = Counter(
        "guinevere_m17_recovery_restarts_total",
        "Auto-recovery restarts",
    )

    _METRICS_AVAILABLE = True
except ImportError:
    _METRICS_AVAILABLE = False
    M17_BREAKER_STATE = None
    M17_BREAKER_TRIPS = None
    M17_COST_USD = None
    M17_GROUNDING_RATIO = None
    M17_EMOTION_CONSECUTIVE = None
    M17_DREAMS_THIS_HOUR = None
    M17_SUBAGENTS_ACTIVE = None
    M17_SUBAGENTS_TOTAL = None
    M17_RECOVERY_RESTARTS = None


def set_breaker_state_metric(breaker_name: str, state: BreakerState) -> None:
    """Set the breaker state gauge metric."""
    if M17_BREAKER_STATE is not None:
        state_value = {"closed": 0, "open": 1, "half_open": 2}.get(state.value, 0)
        M17_BREAKER_STATE.labels(breaker_name=breaker_name).set(state_value)


def record_breaker_trip_metric(breaker_name: str) -> None:
    """Record a breaker trip."""
    if M17_BREAKER_TRIPS is not None:
        M17_BREAKER_TRIPS.labels(breaker_name=breaker_name).inc()


__all__ = [
    "BreakerState",
    "CircuitBreakerOpenError",
    "CircuitBreaker",
    "CostExplosionBreaker",
    "InfiniteLoopBreaker",
    "HallucinationSpiralBreaker",
    "EmotionalFixationBreaker",
    "DreamFloodingBreaker",
    "SubAgentExplosionBreaker",
    "CircuitBreakerSet",
    "set_breaker_state_metric",
    "record_breaker_trip_metric",
]
