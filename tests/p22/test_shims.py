"""P22 safety-critical shim regression tests — pins HARD STOP + consent behavior.

These tests prevent re-introduction of the T3 silent-fallthrough bug
(audit round 1, consent-hardstop finding H3): if HardStopShim is wired with
an async redis client (or no source at all), the sync
is_hard_stop_active() path must NOT silently return False when
life_kernel:hard_stop is set.

The regression test uses a SYNC fake redis (dict-backed) to assert the shim
honors the global key from the sync consent-gate path.
"""

from __future__ import annotations

import uuid

import pytest

from src.life_integrations._shims import ConsentGateShim, HardStopShim


class _FakeSyncRedis:
    """Minimal sync redis-like store for testing (dict-backed)."""

    def __init__(self, store: dict[str, str] | None = None) -> None:
        self._store = store or {}

    def get(self, key: str) -> str | None:
        return self._store.get(key)

    def set(self, key: str, value: str) -> None:
        self._store[key] = value

    def delete(self, key: str) -> None:
        self._store.pop(key, None)


class _FakeHandler:
    """In-process handler stub with is_safe."""

    def __init__(self, safe: bool = False) -> None:
        self._safe = safe

    @property
    def is_safe(self) -> bool:
        return self._safe


class TestHardStopShim:
    """HardStopShim must detect life_kernel:hard_stop via SYNC redis."""

    def test_sync_redis_hard_stop_set_returns_true(self):
        """REGRESSION (audit r1 H3): sync redis + key set → HARD STOP active."""
        store = {"life_kernel:hard_stop": "1"}
        redis = _FakeSyncRedis(store)
        shim = HardStopShim(redis_client=redis, hard_stop_handler=None)
        assert shim.is_hard_stop_active() is True

    def test_sync_redis_hard_stop_clear_returns_false(self):
        """Sync redis + key absent → HARD STOP not active."""
        redis = _FakeSyncRedis({})
        shim = HardStopShim(redis_client=redis, hard_stop_handler=None)
        assert shim.is_hard_stop_active() is False

    def test_sync_redis_hard_stop_falsey_value_returns_false(self):
        """Key present but '0'/'false'/empty → not active (clear values)."""
        for clear_val in ("0", "false", "", "False", "no", "None"):
            redis = _FakeSyncRedis({"life_kernel:hard_stop": clear_val})
            shim = HardStopShim(redis_client=redis, hard_stop_handler=None)
            assert shim.is_hard_stop_active() is False, (
                f"value {clear_val!r} should be treated as clear"
            )

    def test_handler_is_safe_returns_true(self):
        """In-process handler is_safe=True → HARD STOP active (keyword trigger)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=_FakeHandler(safe=True))
        assert shim.is_hard_stop_active() is True

    def test_redis_or_handler_conservative_or(self):
        """Either source active → HARD STOP active (conservative OR)."""
        redis = _FakeSyncRedis({"life_kernel:hard_stop": "1"})
        shim = HardStopShim(
            redis_client=redis,
            hard_stop_handler=_FakeHandler(safe=False),
        )
        assert shim.is_hard_stop_active() is True

    def test_no_source_returns_true_and_logs_fail_closed(self):
        """No redis + no handler → fail-CLOSED: returns True (wiring bug logged).

        Audit F12: a shim with no sources cannot prove clear; the safest
        interpretation is HARD STOP active (safer than allowing L2+ without
        any safety surface in place).
        """
        shim = HardStopShim(redis_client=None, hard_stop_handler=None)
        assert shim.is_hard_stop_active() is True

    def test_handler_raises_fail_closed(self):
        """Handler raising during is_safe check → fail-CLOSED: True.

        Audit F12: when the safety check itself is broken, treat HARD STOP as
        active (cannot prove clear; safer to block than to allow).
        """
        class _RaisingHandler:
            @property
            def is_safe(self):
                raise RuntimeError("boom")

        shim = HardStopShim(redis_client=None, hard_stop_handler=_RaisingHandler())
        assert shim.is_hard_stop_active() is True

    @pytest.mark.asyncio
    async def test_async_no_source_returns_true_fail_closed(self):
        """Async variant: no source → fail-CLOSED (True)."""
        shim = HardStopShim(redis_client=None, hard_stop_handler=None)
        assert await shim.is_hard_stop_active_async() is True

    @pytest.mark.asyncio
    async def test_async_handler_raises_fail_closed(self):
        """Async variant: handler raising → fail-CLOSED (True)."""
        class _RaisingHandler:
            @property
            def is_safe(self):
                raise RuntimeError("boom")

        shim = HardStopShim(redis_client=None, hard_stop_handler=_RaisingHandler())
        assert await shim.is_hard_stop_active_async() is True


class TestConsentGateShim:
    """ConsentGateShim must fail-closed (no fake PASS)."""

    @pytest.mark.asyncio
    async def test_no_checker_fail_closed(self):
        shim = ConsentGateShim(consent_checker=None)
        assert await shim.check_consent("consent.comms.discord.write") is False

    @pytest.mark.asyncio
    async def test_bool_true_passes(self):
        class _BoolChecker:
            async def check_consent(self, scope, project_id=None):
                return True

        shim = ConsentGateShim(consent_checker=_BoolChecker())
        assert await shim.check_consent("scope") is True

    @pytest.mark.asyncio
    async def test_consent_result_allowed_extracted(self):
        class _Result:
            def __init__(self, allowed):
                self.allowed = allowed

        class _ResultChecker:
            async def check_consent(self, scope, project_id=None):
                return _Result(allowed=False)

        shim = ConsentGateShim(consent_checker=_ResultChecker())
        assert await shim.check_consent("scope") is False

    @pytest.mark.asyncio
    async def test_checker_raises_fail_closed(self):
        class _RaisingChecker:
            async def check_consent(self, scope, project_id=None):
                raise RuntimeError("boom")

        shim = ConsentGateShim(consent_checker=_RaisingChecker())
        assert await shim.check_consent("scope") is False

    @pytest.mark.asyncio
    async def test_ambiguous_result_fail_closed(self):
        class _AmbiguousChecker:
            async def check_consent(self, scope, project_id=None):
                return "maybe"  # neither bool nor has .allowed

        shim = ConsentGateShim(consent_checker=_AmbiguousChecker())
        assert await shim.check_consent("scope") is False
