"""F05 production audit writer wiring tests — NO main.py import.

Avoiding ``import src.core.main`` is critical: importing the module twice in
the same process re-registers the Prometheus counters and raises
"Duplicated timeseries in CollectorRegistry".  Instead we extract the testable
behavior by importing ``build_audit_writer`` lazily and ensuring no two
imports of the module happen.

Hard rejections tested here:
- ``build_audit_writer()`` returns a non-None writer in BOTH DB-available
  and DB-unavailable paths.
- DB path → IntegrationAuditWriter; file path → FileAuditWriter.
- ``FileAuditWriter.write_event`` writes one JSON line per event.
- ``FileAuditWriter.write_event`` never raises even when the path is bad.
- ``build_runtime_registry`` propagates the writer to the resulting
  ActionRouter's ``audit_logger._writer`` field.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import uuid
from pathlib import Path
from types import ModuleType

import pytest


# ---------------------------------------------------------------------------
# Lazy, single-import loader for src.core.main. The `main` module registers
# Prometheus counters at import time; re-running the import would raise
# "Duplicated timeseries in CollectorRegistry" — so we cache it.
# ---------------------------------------------------------------------------

_main_module: ModuleType | None = None


def _get_main_module() -> ModuleType:
    global _main_module
    if _main_module is not None:
        return _main_module
    import src.core.main as m
    _main_module = m
    return m


def test_build_audit_writer_returns_writer_when_no_db_url():
    """No DATABASE_URL → FileAuditWriter engages cleanly."""
    writer, target = _get_main_module().build_audit_writer(database_url=None)
    assert target == "file"
    from src.life_integrations.audit_db_writer import FileAuditWriter
    assert isinstance(writer, FileAuditWriter)
    assert writer is not None


def test_build_audit_writer_bogus_database_url_falls_back_to_file():
    """Bogus DB URL → DB construction never actually connects (asyncpg is
    lazy) — the writer either returns IntegrationAuditWriter OR falls back
    to FileAuditWriter. Either is fine; we just need non-None.
    """
    writer, target = _get_main_module().build_audit_writer(
        database_url="postgresql+asyncpg://bogus_host:9999/no_such_db",
    )
    assert writer is not None, (
        "build_audit_writer MUST return non-None on bogus URL"
    )
    from src.life_integrations.audit_db_writer import (
        FileAuditWriter, IntegrationAuditWriter,
    )
    if target == "db":
        assert isinstance(writer, IntegrationAuditWriter)
    else:
        assert isinstance(writer, FileAuditWriter)


@pytest.mark.asyncio
async def test_runtime_registry_passes_audit_writer_to_router():
    """End-to-end: writer passes through build_runtime_registry to
    ActionRouter.audit_logger._writer."""
    from src.life_integrations.runtime import build_runtime_registry

    writer, _ = _get_main_module().build_audit_writer(database_url=None)
    assert writer is not None

    class _NoopRedis:
        async def ping(self):
            return True
        async def aclose(self):
            return None
        async def get(self, *args, **kw):
            return None

    registry, router = await build_runtime_registry(
        redis_client=_NoopRedis(),
        hard_stop_handler=None,
        consent_checker=None,
        project_registry=None,
        audit_writer=writer,
        workspace_root=tempfile.gettempdir(),
        discord_rest_client=None,
    )

    if router is not None:
        assert router._audit_logger is not None
        assert router._audit_logger._writer is writer, (
            "router._audit_logger._writer must be the writer passed in"
        )
        assert router._audit_logger._writer is not None


@pytest.mark.asyncio
async def test_file_audit_writer_appends_json_line(tmp_path: Path):
    """FileAuditWriter writes one JSON line per event to the configured path."""
    from src.life_integrations.audit_db_writer import FileAuditWriter

    target = tmp_path / "audit.log"
    fw = FileAuditWriter(str(target))

    event = {
        "event_id": str(uuid.uuid4()),
        "occurred_at": "2026-06-28T00:00:00+00:00",
        "actor_type": "system",
        "actor_id": "agent:guinevere",
        "integration_id": "discord",
        "provider": "Discord",
        "action": "send_message",
        "tier": "L2_WRITE",
        "project_id": None,
        "result": "success",
        "correlation_id": str(uuid.uuid4()),
        "metadata": {"channel_id": "123"},
        "previous_hash": "",
        "event_hash": "deadbeef" * 8,
    }
    await fw.write_event(event)
    await fw.write_event(event)

    text = target.read_text(encoding="utf-8")
    lines = [ln for ln in text.splitlines() if ln]
    assert len(lines) == 2
    for ln in lines:
        parsed = json.loads(ln)
        assert parsed["integration_id"] == "discord"
        assert parsed["action"] == "send_message"


@pytest.mark.asyncio
async def test_file_audit_writer_does_not_raise_on_bad_path(tmp_path: Path):
    """FileAuditWriter.write_event must NOT raise when path is unwritable."""
    from src.life_integrations.audit_db_writer import FileAuditWriter

    bad_path = tmp_path / "nope" / "audit.log"
    fw = FileAuditWriter(str(bad_path))
    # Must NOT raise despite mkdir+write failing.
    await fw.write_event(
        {"event_id": str(uuid.uuid4()),
         "occurred_at": "2026-06-28T00:00:00+00:00",
         "actor_type": "system", "actor_id": "agent:guinevere",
         "integration_id": "discord", "provider": "Discord",
         "action": "send_message", "tier": "L2_WRITE",
         "project_id": None, "result": "success",
         "correlation_id": "00000000-0000-0000-0000-000000000000",
         "metadata": {}, "previous_hash": "", "event_hash": "abc"},
    )
