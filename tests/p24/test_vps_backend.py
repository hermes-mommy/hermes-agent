"""P6 VPS backend TDD tests — real subprocess for testable actions.

Actions that need real infra (docker/pg/restic/rclone) are tested via
the subprocess they wrap; here we test the subprocess-based actions that
work in any Linux env: shell, service_status, systemctl, journalctl, list_containers.
"""
from __future__ import annotations

import asyncio
import pytest

from guinvere.tools.backends.vps import VPSBackend


@pytest.fixture
def backend():
    return VPSBackend()


@pytest.mark.asyncio
async def test_shell_executes_real_command(backend):
    """shell() runs a real whitelisted command and returns stdout."""
    result = await backend.dispatch("shell", {"cmd": "echo hello-vps"})

    assert result["ok"] is True
    assert "hello-vps" in result["stdout"]


@pytest.mark.asyncio
async def test_shell_captures_stderr(backend):
    """shell() captures stderr separately."""
    # write to stderr via a command
    result = await backend.dispatch("shell", {"cmd": "sh -c 'echo err-msg >&2'"})

    assert result["ok"] is True
    assert "err-msg" in result["stderr"]


@pytest.mark.asyncio
async def test_service_status_returns_real_state(backend):
    """service_status() returns the actual systemctl is-active output."""
    # guinevere-core is running on the VPS (prod). Use a known service.
    result = await backend.dispatch("service_status", {"service": "guinevere-core"})

    assert result["ok"] is True
    assert result["service"] == "guinevere-core"
    # status should be "active" or "inactive" or "unknown" — a real string
    assert result["status"] in ("active", "inactive", "activating", "deactivating", "failed", "unknown")


@pytest.mark.asyncio
async def test_systemctl_status_returns_real_output(backend):
    """systemctl verb=status returns real systemctl output."""
    result = await backend.dispatch("systemctl", {"unit": "guinevere-core", "verb": "is-active"})

    assert result["ok"] is True
    # is-active prints "active" or "inactive" or "unknown"
    assert "active" in result.get("stdout", "") or result.get("status") in ("active", "inactive", "unknown")


@pytest.mark.asyncio
async def test_journalctl_returns_real_entries(backend):
    """journalctl() returns real log entries for a running unit."""
    result = await backend.dispatch("journalctl", {"unit": "guinevere-core", "lines": 5})

    assert result["ok"] is True
    assert result["unit"] == "guinevere-core"
    # entries is a list (may be empty if no logs, but structure must be list)
    assert isinstance(result["entries"], list)


@pytest.mark.asyncio
async def test_shell_rejects_non_whitelisted_dangerous_command(backend):
    """shell() must not execute dangerous commands (rm -rf / etc).

    Security: a denylist of dangerous patterns must block execution.
    """
    result = await backend.dispatch("shell", {"cmd": "rm -rf /tmp/nonexistent-p6-test"})

    # Either rejected (ok=False, blocked) or the command is in denylist
    assert result["ok"] is False or result.get("blocked") is True, \
        "dangerous rm -rf must be blocked, not executed"


@pytest.mark.asyncio
async def test_health_metrics_returns_real_cpu_mem_disk(backend):
    """health_metrics() returns real CPU/memory/disk percentages."""
    result = await backend.dispatch("health_metrics", {})

    assert result["ok"] is True
    m = result["metrics"]
    # real values, not all zeros (VPS is up, has load)
    assert "cpu_percent" in m
    assert "memory_percent" in m
    assert "disk_percent" in m
    # at least disk should be > 0 on a real VPS
    assert m["disk_percent"] > 0
