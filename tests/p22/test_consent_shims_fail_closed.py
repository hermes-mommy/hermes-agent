"""P22 audit brutal-cycle fail-closed regression tests.

Pins the audit findings F03 (ConsentGate fail-closed when hard_stop_checker
is None) and F12 (HardStopShim fail-closed when no source wired OR handler
raises). These tests make the fail-closed axioms contractual.

Companion files:
- src/life_integrations/consent.py (F03: ConsentGate.check)
- src/life_integrations/_shims.py (F12: HardStopShim sync + async)
"""

from __future__ import annotations

import uuid

import pytest

from src.life_integrations._shims import HardStopShim
from src.life_integrations.consent import ConsentGate
from src.life_integrations.types import PermissionTier


# ---------------------------------------------------------------------------
# F03 — ConsentGate fail-closed when hard_stop_checker is None
# ---------------------------------------------------------------------------


class _StubConsentChecker:
    """Stub consent checker that grants every scope by default."""

    def __init__(self, grant_all: bool = True) -> None:
        self._grant_all = grant_all
        self.calls: list[str] = []

    async def check_consent(self, scope, project_id=None):
        self.calls.append(scope)
        return self._grant_all


class _StubHardStopChecker:
    def __init__(self, active: bool = False) -> None:
        self._active = active

    def is_hard_stop_active(self) -> bool:
        return self._active


class TestConsentGateFailClosedWithoutHardStopChecker:
    """F03 — without hard_stop_checker wired, L2+ is denied (fail-closed)."""

    @pytest.mark.asyncio
    async def test_l2_denied_when_hard_stop_checker_none(self):
        """L2_WRITE with hard_stop_checker=None → (False, fail-closed reason)."""
        checker = _StubConsentChecker(grant_all=True)
        gate = ConsentGate(consent_checker=checker, hard_stop_checker=None)
        allowed, reason = await gate.check(
            PermissionTier.L2_WRITE, "consent.test.write"
        )
        assert allowed is False
        assert "hard_stop_checker not configured" in reason
        assert "fail-closed" in reason

    @pytest.mark.asyncio
    async def test_l3_denied_when_hard_stop_checker_none(self):
        """L3_DESTRUCTIVE with hard_stop_checker=None → denied."""
        checker = _StubConsentChecker(grant_all=True)
        gate = ConsentGate(consent_checker=checker, hard_stop_checker=None)
        allowed, reason = await gate.check(
            PermissionTier.L3_DESTRUCTIVE, "consent.test.delete"
        )
        assert allowed is False
        assert "hard_stop_checker not configured" in reason

    @pytest.mark.asyncio
    async def test_l1_still_passes_when_hard_stop_checker_none(self):
        """L1_READ does NOT require a HARD STOP checker — reads are safe."""
        gate = ConsentGate(consent_checker=None, hard_stop_checker=None)
        allowed, reason = await gate.check(
            PermissionTier.L1_READ, "consent.test.read"
        )
        assert allowed is True
        assert "L1" in reason

    @pytest.mark.asyncio
    async def test_l4_always_forbidden_when_hard_stop_checker_none(self):
        """L4 forbiddenness AND missing HARD STOP checker both deny; L4
        returns False. Per audit F03 placement, the hard-stop-checker-miss
        reason fires first for tier≥L2."""
        checker = _StubConsentChecker(grant_all=True)
        gate = ConsentGate(consent_checker=checker, hard_stop_checker=None)
        allowed, reason = await gate.check(
            PermissionTier.L4_FORBIDDEN, "consent.test.forbidden"
        )
        assert allowed is False  # NEVER allowed
        # Either fail-closed reason is acceptable (hard_stop miss OR L4
        # forbidden). Both are correct denials.
        assert (
            "hard_stop_checker not configured" in reason
            or "L4_FORBIDDEN" in reason
        )

    @pytest.mark.asyncio
    async def test_l2_passes_when_hard_stop_checker_pristine(self):
        """Sanity: with a healthy hard_stop_checker=False + consent granted,
        L2 passes (does not regress the legitimate not-active path)."""
        checker = _StubConsentChecker(grant_all=True)
        gate = ConsentGate(
            consent_checker=checker,
            hard_stop_checker=_StubHardStopChecker(active=False),
        )
        allowed, reason = await gate.check(
            PermissionTier.L2_WRITE, "consent.test.write"
        )
        assert allowed is True
        assert reason == "allowed"

    @pytest.mark.asyncio
    async def test_l3_blocked_when_hard_stop_active(self):
        """Sanity: a healthy hard_stop_checker=True still blocks L3."""
        checker = _StubConsentChecker(grant_all=True)
        gate = ConsentGate(
            consent_checker=checker,
            hard_stop_checker=_StubHardStopChecker(active=True),
        )
        allowed, reason = await gate.check(
            PermissionTier.L3_DESTRUCTIVE, "consent.test.delete"
        )
        assert allowed is False
        assert "HARD STOP" in reason


# ---------------------------------------------------------------------------
# F12 — HardStopShim fail-closed (no source wired OR handler raises)
# ---------------------------------------------------------------------------


class _FakeHandler:
    def __init__(self, safe: bool = False) -> None:
        self._safe = safe

    @property
    def is_safe(self) -> bool:
        return self._safe


class _RaisingHandler:
    @property
    def is_safe(self):
        raise RuntimeError("boom")


class TestHardStopShimFailClosed:
    """F12 — shim returns True (HARD STOP active) when cannot prove clear."""

    def test_no_redis_no_handler_sync_returns_true(self):
        """Sync variant: no source wired → True (fail-closed)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=None)
        assert shim.is_hard_stop_active() is True

    def test_handler_raises_sync_returns_true(self):
        """Sync variant: handler raising → True (fail-closed)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=_RaisingHandler())
        assert shim.is_hard_stop_active() is True

    @pytest.mark.asyncio
    async def test_no_source_async_returns_true(self):
        """Async variant: no source wired → True (fail-closed)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=None)
        assert await shim.is_hard_stop_active_async() is True

    @pytest.mark.asyncio
    async def test_handler_raises_async_returns_true(self):
        """Async variant: handler raising → True (fail-closed)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=_RaisingHandler())
        assert await shim.is_hard_stop_active_async() is True

    def test_healthy_handler_says_not_active_still_false(self):
        """Sanity: healthy handler reporting False → False (NOT unconditional
        always-active). This guards against the over-correction described in
        the audit F12 hard-rejection criteria."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=_FakeHandler(safe=False))
        assert shim.is_hard_stop_active() is False

    @pytest.mark.asyncio
    async def test_healthy_handler_says_not_active_async_still_false(self):
        """Async: healthy handler False → False (also NOT unconditional)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=_FakeHandler(safe=False))
        assert await shim.is_hard_stop_active_async() is False
