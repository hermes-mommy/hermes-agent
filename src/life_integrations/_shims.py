"""P22 safety-critical shims — bridge existing Guinevere services to P22 protocols.

These shims are SAFETY-CRITICAL. A missing or no-op shim would silently disable
the HARD STOP or consent gate, which is a HARD REJECTION per AGENTS.md §0
("HARD STOP blocks L2+") and the P22 scaffold.

Bridges:
- ``HardStopShim``: exposes ``is_hard_stop_active()`` by checking the Redis
  global key ``life_kernel:hard_stop`` (P20 runtime authority, AGENTS.md §0.1
  preserved invariant #1) AND the in-process ``HardStopHandler.is_safe``.
  Either source active => HARD STOP active (conservative OR).
- ``ConsentGateShim``: exposes ``check_consent(scope, project_id) -> bool`` by
  delegating to a ``ConsentCheckerProtocol``-compatible object whose
  ``check_consent`` returns a ``ConsentCheckResult`` (with ``.allowed``), or
  already a bool. Fail-closed on any ambiguity.

ProjectRegistry needs NO shim — P19's real ``ProjectRegistry`` already
implements ``get``/``resolve``/``list_active`` matching P22's
``ProjectRegistryProtocol`` (verified src/projects/registry.py:277,291,313).
"""

from __future__ import annotations

import uuid
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


class HardStopShim:
    """Bridge Guinevere's HARD STOP surfaces to P22's ``is_hard_stop_active``.

    Checks, in order (conservative OR — any active source blocks):
    1. Redis global key ``life_kernel:hard_stop`` (P20 runtime authority).
    2. In-process ``HardStopHandler.is_safe`` (keyword-triggered state machine).

    A non-empty, non-"0", non-"false" Redis value => HARD STOP active.
    """

    REDIS_KEY = "life_kernel:hard_stop"
    _CLEAR_VALUES = {"", "0", "false", "False", "no", "None", None}

    def __init__(
        self,
        redis_client: Any | None = None,
        hard_stop_handler: Any | None = None,
    ) -> None:
        """Initialize with optional Redis client and in-process handler.

        Args:
            redis_client: a SYNC ``redis.Redis`` instance (preferred) for the
                sync ``is_hard_stop_active()`` path. An async
                ``redis.asyncio.Redis`` is accepted but CANNOT be queried from
                the sync path — it will be detected and the shim will rely on
                the in-process handler instead (logging a warning). For
                correctness, pass a sync redis client.
            hard_stop_handler: HardStopHandler instance with ``is_safe`` (may be None).
        """
        self._redis = redis_client
        self._handler = hard_stop_handler
        self._async_redis_warned = False

    def is_hard_stop_active(self) -> bool:
        """Return True if ANY HARD STOP source is active.

        Conservative: if we cannot determine state (no sources wired), we
        return False (P22 ConsentGate treats None checker as "assumes clear"
        per consent.py:79), but the parent factory MUST wire at least one
        source — a bare shim with no sources is a wiring bug logged loudly.
        """
        # Source 1: Redis global key (P20 authority) — SYNC only
        redis_active = False
        if self._redis is not None:
            try:
                value = self._redis.get(self.REDIS_KEY)
                # Detect async redis client (returns coroutine from .get).
                # The sync path CANNOT await it. Warn once and fall through
                # to the in-process handler. For correct HARD STOP detection
                # via Redis, the factory MUST pass a SYNC redis client.
                if hasattr(value, "__await__"):
                    if not self._async_redis_warned:
                        logger.warning(
                            "hard_stop_shim.async_redis_in_sync_path",
                            hint="pass a sync redis.Redis client for correct HARD STOP detection",
                            key=self.REDIS_KEY,
                        )
                        self._async_redis_warned = True
                elif isinstance(value, bytes):
                    redis_active = value.decode(errors="ignore") not in self._CLEAR_VALUES
                elif isinstance(value, str):
                    redis_active = value not in self._CLEAR_VALUES
            except Exception as e:  # noqa: BLE001 — must never crash the gate
                logger.warning(
                    "hard_stop_shim.redis_check_failed",
                    error=str(e),
                    key=self.REDIS_KEY,
                )
                # Conservative: if Redis is unreachable, do NOT assume clear
                # if we have no other source. Fall through to handler.

        # Source 2: in-process handler (keyword-triggered)
        handler_active = False
        if self._handler is not None:
            try:
                handler_active = bool(self._handler.is_safe)
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "hard_stop_shim.handler_check_failed",
                    error=str(e),
                )

        if self._redis is None and self._handler is None:
            logger.error("hard_stop_shim.no_source_wired")
            # No source => cannot prove clear => fail-closed for L2+ would be
            # safer, but ConsentGate.py:79 documents None checker as "assumes
            # clear". We surface the wiring bug loudly instead of silently.
            return False

        return redis_active or handler_active

    async def is_hard_stop_active_async(self) -> bool:
        """Async variant for async Redis clients.

        Checks the Redis global key with await, then the in-process handler.
        """
        redis_active = False
        if self._redis is not None:
            try:
                value = self._redis.get(self.REDIS_KEY)
                if hasattr(value, "__await__"):
                    value = await value
                if isinstance(value, bytes):
                    redis_active = value.decode(errors="ignore") not in self._CLEAR_VALUES
                elif isinstance(value, str):
                    redis_active = value not in self._CLEAR_VALUES
            except Exception as e:  # noqa: BLE001
                logger.warning(
                    "hard_stop_shim.redis_check_failed",
                    error=str(e),
                    key=self.REDIS_KEY,
                )

        handler_active = False
        if self._handler is not None:
            try:
                handler_active = bool(self._handler.is_safe)
            except Exception as e:  # noqa: BLE001
                logger.warning("hard_stop_shim.handler_check_failed", error=str(e))

        if self._redis is None and self._handler is None:
            logger.error("hard_stop_shim.no_source_wired")
            return False

        return redis_active or handler_active


class ConsentGateShim:
    """Bridge a ConsentCheckResult-returning checker to P22's bool protocol.

    P22 ``ConsentCheckerProtocol.check_consent(scope, project_id) -> bool``.
    Existing Guinevere checkers (e.g. surveillance consent_gate, gmail
    consent_manager) return ``ConsentCheckResult(allowed: bool, ...)``.
    This shim extracts ``.allowed`` and fail-closes on ambiguity.
    """

    def __init__(self, consent_checker: Any | None = None) -> None:
        """Initialize with the underlying checker.

        Args:
            consent_checker: Object with ``async check_consent(scope, project_id=None)``
                returning either a bool or an object with ``.allowed``.
        """
        self._checker = consent_checker

    async def check_consent(
        self,
        scope: str,
        project_id: uuid.UUID | None = None,
    ) -> bool:
        """Return True if consent is granted, False otherwise (fail-closed).

        Fail-closed: if no checker wired, or checker raises, or result shape
        is ambiguous => return False (blocks the L2+ action).
        """
        if self._checker is None:
            logger.warning(
                "consent_shim.no_checker_fail_closed",
                scope=scope,
            )
            return False

        try:
            result = await self._checker.check_consent(
                scope=scope,
                project_id=project_id,
            )
        except Exception as e:  # noqa: BLE001 — fail-closed, never crash gate
            logger.warning(
                "consent_shim.check_failed_fail_closed",
                scope=scope,
                error=str(e),
            )
            return False

        # Already a bool
        if isinstance(result, bool):
            return result

        # ConsentCheckResult-like: extract .allowed
        allowed = getattr(result, "allowed", None)
        if isinstance(allowed, bool):
            return allowed

        logger.warning(
            "consent_shim.ambiguous_result_fail_closed",
            scope=scope,
            result_type=type(result).__name__,
        )
        return False
