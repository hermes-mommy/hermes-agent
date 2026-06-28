"""P22 integration registry tests."""

from __future__ import annotations

import asyncio
import threading
import uuid

import pytest

from src.life_integrations import (
    BaseIntegrationAdapter,
    IntegrationRegistry,
)
from src.life_integrations.types import (
    IntegrationCapability,
    IntegrationConfig,
    IntegrationHealth,
    PermissionTier,
)


class _StubAdapter(BaseIntegrationAdapter):
    """Stub adapter for testing."""

    def __init__(self, integration_id: str = "stub") -> None:
        config = IntegrationConfig(
            integration_id=integration_id,
            name="Stub",
            provider="Test",
            capabilities=frozenset({IntegrationCapability.READ, IntegrationCapability.WRITE}),
        )
        super().__init__(config)

    async def health_check(self) -> IntegrationHealth:
        return IntegrationHealth.OK

    async def execute_action(self, action, tier, project_id=None, **kwargs):
        return {"success": True, "action": action}


@pytest.mark.asyncio
async def test_register_and_get():
    """Test adapter registration and lookup."""
    registry = IntegrationRegistry()
    adapter = _StubAdapter("discord")
    await registry.register(adapter)
    assert registry.get("discord") is adapter


@pytest.mark.asyncio
async def test_register_duplicate_raises():
    """Duplicate registration should raise."""
    registry = IntegrationRegistry()
    await registry.register(_StubAdapter("discord"))
    with pytest.raises(ValueError):
        await registry.register(_StubAdapter("discord"))


@pytest.mark.asyncio
async def test_unregister():
    """Test adapter unregistration."""
    registry = IntegrationRegistry()
    await registry.register(_StubAdapter("discord"))
    await registry.unregister("discord")
    with pytest.raises(KeyError):
        registry.get("discord")


@pytest.mark.asyncio
async def test_list_by_capability():
    """Test capability-based filtering."""
    registry = IntegrationRegistry()
    await registry.register(_StubAdapter("discord"))
    adapters = registry.list_by_capability(IntegrationCapability.READ)
    assert len(adapters) == 1
    assert adapters[0].integration_id == "discord"


@pytest.mark.asyncio
async def test_health_check_all():
    """Test bulk health check."""
    registry = IntegrationRegistry()
    await registry.register(_StubAdapter("discord"))
    await registry.register(_StubAdapter("gmail"))
    results = await registry.health_check_all()
    assert results["discord"] == IntegrationHealth.OK
    assert results["gmail"] == IntegrationHealth.OK


@pytest.mark.asyncio
async def test_health_check_all_handles_errors():
    """Health check should handle adapter errors gracefully."""
    registry = IntegrationRegistry()

    class _ErrorAdapter(BaseIntegrationAdapter):
        def __init__(self):
            super().__init__(IntegrationConfig(
                integration_id="error",
                name="Error",
                provider="Test",
                capabilities=frozenset(),
            ))

        async def health_check(self):
            raise RuntimeError("boom")

        async def execute_action(self, action, tier, project_id=None, **kwargs):
            pass

    await registry.register(_ErrorAdapter())
    results = await registry.health_check_all()
    assert results["error"] == IntegrationHealth.ERROR


@pytest.mark.asyncio
async def test_registry_thread_safe_snapshot():
    """F23: sync readers (get/list_all/list_by_capability/get_audit_summary)
    must snapshot under threading.Lock while async writers concurrently
    register/unregister — no exceptions, snapshots always consistent.
    """
    registry = IntegrationRegistry()

    # Pre-register a baseline so list_all never returns empty.
    await registry.register(_StubAdapter(f"baseline"))

    errors: list[BaseException] = []
    snapshots_seen: list[int] = []
    stop = threading.Event()

    async def writer() -> None:
        try:
            for i in range(50):
                iid = f"writer-{i:03d}"
                await registry.register(_StubAdapter(iid))
                # Yield to allow readers to interleave.
                await asyncio.sleep(0)
            for i in range(25):
                await registry.unregister(f"writer-{i:03d}")
                await asyncio.sleep(0)
        except BaseException as exc:  # pragma: no cover - diagnostic only
            errors.append(exc)

    def reader() -> None:
        try:
            while not stop.is_set():
                snap = registry.list_all()
                snapshots_seen.append(len(snap))
                # Every snapshot is a real list (TypeError would mean
                # partial mutation leaked through).
                assert isinstance(snap, list)
                # Capability filter must always return a list too.
                _ = registry.list_by_capability(IntegrationCapability.READ)
                # Audit summary must always be a dict.
                _ = registry.get_audit_summary()
                # Pick/get round-trips for any registered id.
                if snap:
                    _ = registry.get(snap[0].integration_id)
        except BaseException as exc:  # pragma: no cover - diagnostic only
            errors.append(exc)

    # Spawn 4 sync reader threads + 1 async writer.
    threads = [threading.Thread(target=reader, daemon=True) for _ in range(4)]
    for t in threads:
        t.start()

    await writer()
    stop.set()
    for t in threads:
        t.join(timeout=5.0)

    assert not errors, f"reader/writer races failed: {errors!r}"
    # Reader observed motion (otherwise the test would be vacuous).
    assert snapshots_seen, "reader recorded zero snapshots — concurrency not exercised"
    # Final state is deterministic: baseline + 25 survivors (indices 25..49).
    final_ids = {a.integration_id for a in registry.list_all()}
    assert "baseline" in final_ids
    survivors = {f"writer-{i:03d}" for i in range(25, 50)}
    assert survivors.issubset(final_ids)
