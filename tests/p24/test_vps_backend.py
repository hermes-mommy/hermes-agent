"""P24 VPS backend TDD tests — 15 SSH-based actions, mocked subprocess.

Each action is a standalone async function using asyncio.create_subprocess_exec.
Tests mock subprocess for isolation (no real SSH needed).

Actions (15):
  ssh_exec, scp_upload, scp_download, systemctl_status, systemctl_start,
  systemctl_stop, systemctl_restart, journalctl, df, du, free, uptime,
  ps, kill, tail_log.
"""
from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guinvere.tools.backends.vps import (
    df,
    du,
    free,
    journalctl,
    kill,
    ps,
    scp_download,
    scp_upload,
    ssh_exec,
    systemctl_restart,
    systemctl_start,
    systemctl_status,
    systemctl_stop,
    tail_log,
    uptime,
)

# ===================================================================
# Helpers
# ===================================================================

_DEFAULT_HOST = "guinevere-vps"


def _make_proc(stdout: bytes = b"", stderr: bytes = b"", returncode: int = 0) -> AsyncMock:
    """Create a mock subprocess with the given stdout/stderr/returncode."""
    proc = AsyncMock()
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.returncode = returncode
    return proc


def _make_timeout_proc(timeout: float = 30.0) -> AsyncMock:
    """Create a mock subprocess that times out on communicate()."""
    proc = AsyncMock()

    async def _slow_communicate() -> tuple[bytes, bytes]:
        await asyncio.sleep(timeout + 1)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow_communicate)
    proc.returncode = None
    return proc


# ===================================================================
# 1.  ssh_exec
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ssh_exec_success(mock_subprocess: MagicMock) -> None:
    """ssh_exec returns structured dict with stdout on success."""
    mock_subprocess.return_value = _make_proc(b"hello\n", b"", 0)

    result = await ssh_exec(_DEFAULT_HOST, "echo hello")

    assert result["ok"] is True
    assert result["action"] == "ssh_exec"
    assert result["stdout"] == "hello\n"
    assert result["returncode"] == 0
    mock_subprocess.assert_called_once_with(
        "ssh", _DEFAULT_HOST, "echo hello",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ssh_exec_failure(mock_subprocess: MagicMock) -> None:
    """ssh_exec returns ok=False on non-zero exit code."""
    mock_subprocess.return_value = _make_proc(b"", b"permission denied\n", 255)

    result = await ssh_exec(_DEFAULT_HOST, "bad-cmd")

    assert result["ok"] is False
    assert result["action"] == "ssh_exec"
    assert result["returncode"] == 255
    assert "permission denied" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ssh_exec_timeout(mock_subprocess: MagicMock) -> None:
    """ssh_exec returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await ssh_exec(_DEFAULT_HOST, "sleep 999", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ssh_exec_custom_timeout(mock_subprocess: MagicMock) -> None:
    """ssh_exec passes custom timeout to wait_for."""
    mock_subprocess.return_value = _make_proc(b"ok\n", b"", 0)

    result = await ssh_exec(_DEFAULT_HOST, "echo ok", timeout=60)

    assert result["ok"] is True


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ssh_exec_stderr_only(mock_subprocess: MagicMock) -> None:
    """ssh_exec returns stderr when exit code is 0 but stderr has content."""
    mock_subprocess.return_value = _make_proc(b"result\n", b"warning\n", 0)

    result = await ssh_exec(_DEFAULT_HOST, "cmd")

    assert result["ok"] is True
    assert result["stdout"] == "result\n"
    assert result["stderr"] == "warning\n"


# ===================================================================
# 2.  scp_upload
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_upload_success(mock_subprocess: MagicMock) -> None:
    """scp_upload returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await scp_upload("/local/file.txt", "/remote/file.txt")

    assert result["ok"] is True
    assert result["action"] == "scp_upload"
    assert result["local"] == "/local/file.txt"
    assert result["remote"] == "/remote/file.txt"
    mock_subprocess.assert_called_once_with(
        "scp", "/local/file.txt", f"{_DEFAULT_HOST}:/remote/file.txt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_upload_failure(mock_subprocess: MagicMock) -> None:
    """scp_upload returns ok=False on non-zero exit."""
    mock_subprocess.return_value = _make_proc(b"", b"No such file\n", 1)

    result = await scp_upload("/missing/file.txt", "/remote/file.txt")

    assert result["ok"] is False
    assert "No such file" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_upload_timeout(mock_subprocess: MagicMock) -> None:
    """scp_upload returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await scp_upload("/local/file.txt", "/remote/file.txt", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_upload_custom_host(mock_subprocess: MagicMock) -> None:
    """scp_upload uses custom host."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await scp_upload("/local/f.txt", "/remote/f.txt", host="my-host")

    assert result["ok"] is True
    mock_subprocess.assert_called_once_with(
        "scp", "/local/f.txt", "my-host:/remote/f.txt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


# ===================================================================
# 3.  scp_download
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_download_success(mock_subprocess: MagicMock) -> None:
    """scp_download returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await scp_download("/remote/file.txt", "/local/file.txt")

    assert result["ok"] is True
    assert result["action"] == "scp_download"
    assert result["remote"] == "/remote/file.txt"
    assert result["local"] == "/local/file.txt"
    mock_subprocess.assert_called_once_with(
        "scp", f"{_DEFAULT_HOST}:/remote/file.txt", "/local/file.txt",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_download_failure(mock_subprocess: MagicMock) -> None:
    """scp_download returns ok=False on non-zero exit."""
    mock_subprocess.return_value = _make_proc(b"", b"not found\n", 1)

    result = await scp_download("/remote/missing.txt", "/local/file.txt")

    assert result["ok"] is False
    assert "not found" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_scp_download_timeout(mock_subprocess: MagicMock) -> None:
    """scp_download returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await scp_download("/remote/f.txt", "/local/f.txt", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 4.  systemctl_status
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_status_active(mock_subprocess: MagicMock) -> None:
    """systemctl_status returns ok=True for active service."""
    mock_subprocess.return_value = _make_proc(
        b"\xe2\x97\x8f guinevere-core.service - Guinevere Core\n   Active: active (running)\n",
        b"", 0,
    )

    result = await systemctl_status("guinevere-core")

    assert result["ok"] is True
    assert result["action"] == "systemctl_status"
    assert result["service"] == "guinevere-core"
    assert "active" in result["stdout"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_status_inactive(mock_subprocess: MagicMock) -> None:
    """systemctl_status returns ok=False for inactive service (non-zero exit)."""
    mock_subprocess.return_value = _make_proc(
        b"\xe2\x97\x8f some.service\n   Active: inactive (dead)\n",
        b"", 3,
    )

    result = await systemctl_status("some")

    assert result["ok"] is False
    assert result["returncode"] == 3


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_status_timeout(mock_subprocess: MagicMock) -> None:
    """systemctl_status returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await systemctl_status("svc", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_status_custom_host(mock_subprocess: MagicMock) -> None:
    """systemctl_status uses custom host."""
    mock_subprocess.return_value = _make_proc(b"Active: active\n", b"", 0)

    result = await systemctl_status("svc", host="other-host")

    assert result["ok"] is True
    # Verify SSH was called with custom host
    call_args = mock_subprocess.call_args
    assert call_args[0][0] == "ssh"
    assert call_args[0][1] == "other-host"


# ===================================================================
# 5.  systemctl_start
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_start_success(mock_subprocess: MagicMock) -> None:
    """systemctl_start returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await systemctl_start("guinevere-core")

    assert result["ok"] is True
    assert result["action"] == "systemctl_start"
    assert result["service"] == "guinevere-core"


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_start_failure(mock_subprocess: MagicMock) -> None:
    """systemctl_start returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"Failed to start\n", 1)

    result = await systemctl_start("bad-svc")

    assert result["ok"] is False
    assert "Failed to start" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_start_timeout(mock_subprocess: MagicMock) -> None:
    """systemctl_start returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await systemctl_start("svc", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 6.  systemctl_stop
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_stop_success(mock_subprocess: MagicMock) -> None:
    """systemctl_stop returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await systemctl_stop("guinevere-core")

    assert result["ok"] is True
    assert result["action"] == "systemctl_stop"
    assert result["service"] == "guinevere-core"


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_stop_failure(mock_subprocess: MagicMock) -> None:
    """systemctl_stop returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"not loaded\n", 5)

    result = await systemctl_stop("missing-svc")

    assert result["ok"] is False
    assert result["returncode"] == 5


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_stop_timeout(mock_subprocess: MagicMock) -> None:
    """systemctl_stop returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await systemctl_stop("svc", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 7.  systemctl_restart
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_restart_success(mock_subprocess: MagicMock) -> None:
    """systemctl_restart returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await systemctl_restart("guinevere-core")

    assert result["ok"] is True
    assert result["action"] == "systemctl_restart"
    assert result["service"] == "guinevere-core"


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_restart_failure(mock_subprocess: MagicMock) -> None:
    """systemctl_restart returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"Job failed\n", 1)

    result = await systemctl_restart("bad-svc")

    assert result["ok"] is False
    assert "Job failed" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_systemctl_restart_timeout(mock_subprocess: MagicMock) -> None:
    """systemctl_restart returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await systemctl_restart("svc", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 8.  journalctl
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_journalctl_success(mock_subprocess: MagicMock) -> None:
    """journalctl returns parsed log entries."""
    log_output = b"Jul 03 10:00:00 host systemd[1]: Started svc.\nJul 03 10:01:00 host svc[123]: hello\n"
    mock_subprocess.return_value = _make_proc(log_output, b"", 0)

    result = await journalctl("guinevere-core", lines=50)

    assert result["ok"] is True
    assert result["action"] == "journalctl"
    assert result["unit"] == "guinevere-core"
    assert result["lines"] == 50
    assert len(result["entries"]) == 2
    assert "Started svc" in result["entries"][0]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_journalctl_empty_logs(mock_subprocess: MagicMock) -> None:
    """journalctl handles empty logs gracefully."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await journalctl("empty-svc", lines=10)

    assert result["ok"] is True
    assert result["entries"] == []


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_journalctl_failure(mock_subprocess: MagicMock) -> None:
    """journalctl returns ok=False on non-zero exit."""
    mock_subprocess.return_value = _make_proc(b"", b"unit not found\n", 4)

    result = await journalctl("nonexistent-svc")

    assert result["ok"] is False
    assert "unit not found" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_journalctl_timeout(mock_subprocess: MagicMock) -> None:
    """journalctl returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await journalctl("svc", lines=10, timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_journalctl_custom_lines(mock_subprocess: MagicMock) -> None:
    """journalctl uses custom line count."""
    mock_subprocess.return_value = _make_proc(b"log line 1\n", b"", 0)

    result = await journalctl("svc", lines=25)

    assert result["ok"] is True
    assert result["lines"] == 25
    # Verify the command includes -n 25
    call_args = mock_subprocess.call_args[0]
    cmd = call_args[2]  # the SSH command string
    assert "-n 25" in cmd


# ===================================================================
# 9.  df
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_df_success(mock_subprocess: MagicMock) -> None:
    """df returns disk usage information."""
    df_output = (
        b"Filesystem     1K-blocks     Used Available Use% Mounted on\n"
        b"/dev/sda1      100000000 50000000  50000000  50% /\n"
    )
    mock_subprocess.return_value = _make_proc(df_output, b"", 0)

    result = await df()

    assert result["ok"] is True
    assert result["action"] == "df"
    assert "50%" in result["stdout"]
    assert result["returncode"] == 0


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_df_failure(mock_subprocess: MagicMock) -> None:
    """df returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"no such mount\n", 1)

    result = await df("/nonexistent")

    assert result["ok"] is False
    assert "no such mount" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_df_timeout(mock_subprocess: MagicMock) -> None:
    """df returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await df(timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_df_custom_path(mock_subprocess: MagicMock) -> None:
    """df uses custom path in SSH command."""
    mock_subprocess.return_value = _make_proc(b"disk info\n", b"", 0)

    result = await df(path="/home")

    assert result["ok"] is True
    call_args = mock_subprocess.call_args[0]
    cmd = call_args[2]
    assert "/home" in cmd


# ===================================================================
# 10.  du
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_du_success(mock_subprocess: MagicMock) -> None:
    """du returns directory size information."""
    mock_subprocess.return_value = _make_proc(b"2048\t/var/log\n", b"", 0)

    result = await du("/var/log")

    assert result["ok"] is True
    assert result["action"] == "du"
    assert result["path"] == "/var/log"
    assert "2048" in result["stdout"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_du_failure(mock_subprocess: MagicMock) -> None:
    """du returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"permission denied\n", 1)

    result = await du("/root/secret")

    assert result["ok"] is False
    assert "permission denied" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_du_timeout(mock_subprocess: MagicMock) -> None:
    """du returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await du("/var/log", timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 11.  free
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_free_success(mock_subprocess: MagicMock) -> None:
    """free returns memory usage information."""
    free_output = (
        b"              total        used        free      shared  buff/cache   available\n"
        b"Mem:       16384000     8192000     4096000      256000     4096000     7936000\n"
        b"Swap:       2097152           0     2097152\n"
    )
    mock_subprocess.return_value = _make_proc(free_output, b"", 0)

    result = await free()

    assert result["ok"] is True
    assert result["action"] == "free"
    assert "16384000" in result["stdout"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_free_failure(mock_subprocess: MagicMock) -> None:
    """free returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"command not found\n", 127)

    result = await free()

    assert result["ok"] is False
    assert result["returncode"] == 127


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_free_timeout(mock_subprocess: MagicMock) -> None:
    """free returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await free(timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 12.  uptime
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_uptime_success(mock_subprocess: MagicMock) -> None:
    """uptime returns system uptime and load average."""
    mock_subprocess.return_value = _make_proc(
        b" 10:30:00 up 10 days,  2:30,  1 user,  load average: 0.50, 0.60, 0.70\n",
        b"", 0,
    )

    result = await uptime()

    assert result["ok"] is True
    assert result["action"] == "uptime"
    assert "load average" in result["stdout"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_uptime_failure(mock_subprocess: MagicMock) -> None:
    """uptime returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"ssh: connect refused\n", 255)

    result = await uptime()

    assert result["ok"] is False
    assert result["returncode"] == 255


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_uptime_timeout(mock_subprocess: MagicMock) -> None:
    """uptime returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await uptime(timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 13.  ps
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ps_success(mock_subprocess: MagicMock) -> None:
    """ps returns process list."""
    ps_output = (
        b"  PID TTY          TIME CMD\n"
        b"    1 ?        00:00:03 systemd\n"
        b"  123 ?        00:00:01 python3\n"
    )
    mock_subprocess.return_value = _make_proc(ps_output, b"", 0)

    result = await ps()

    assert result["ok"] is True
    assert result["action"] == "ps"
    assert "systemd" in result["stdout"]
    assert "python3" in result["stdout"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ps_failure(mock_subprocess: MagicMock) -> None:
    """ps returns ok=False on failure."""
    mock_subprocess.return_value = _make_proc(b"", b"error\n", 1)

    result = await ps()

    assert result["ok"] is False


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_ps_timeout(mock_subprocess: MagicMock) -> None:
    """ps returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await ps(timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


# ===================================================================
# 14.  kill
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_kill_success(mock_subprocess: MagicMock) -> None:
    """kill returns ok=True on success."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await kill(1234)

    assert result["ok"] is True
    assert result["action"] == "kill"
    assert result["pid"] == 1234


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_kill_failure(mock_subprocess: MagicMock) -> None:
    """kill returns ok=False when process not found."""
    mock_subprocess.return_value = _make_proc(b"", b"No such process\n", 1)

    result = await kill(99999)

    assert result["ok"] is False
    assert "No such process" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_kill_timeout(mock_subprocess: MagicMock) -> None:
    """kill returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await kill(1234, timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_kill_custom_signal(mock_subprocess: MagicMock) -> None:
    """kill uses custom signal (SIGTERM default, SIGKILL optional)."""
    mock_subprocess.return_value = _make_proc(b"", b"", 0)

    result = await kill(1234, signal="KILL")

    assert result["ok"] is True
    call_args = mock_subprocess.call_args[0]
    cmd = call_args[2]
    assert "-9" in cmd or "KILL" in cmd


# ===================================================================
# 15.  tail_log
# ===================================================================


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_tail_log_success(mock_subprocess: MagicMock) -> None:
    """tail_log returns last N lines of a log file."""
    log_lines = b"line 1\nline 2\nline 3\nline 4\nline 5\n"
    mock_subprocess.return_value = _make_proc(log_lines, b"", 0)

    result = await tail_log("/var/log/app.log", n=5)

    assert result["ok"] is True
    assert result["action"] == "tail_log"
    assert result["path"] == "/var/log/app.log"
    assert result["lines"] == 5
    assert "line 1" in result["stdout"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_tail_log_failure(mock_subprocess: MagicMock) -> None:
    """tail_log returns ok=False when file not found."""
    mock_subprocess.return_value = _make_proc(b"", b"No such file\n", 1)

    result = await tail_log("/var/log/missing.log")

    assert result["ok"] is False
    assert "No such file" in result["stderr"]


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_tail_log_timeout(mock_subprocess: MagicMock) -> None:
    """tail_log returns ok=False on timeout."""
    proc = AsyncMock()

    async def _slow() -> tuple[bytes, bytes]:
        await asyncio.sleep(100)
        return (b"", b"")

    proc.communicate = AsyncMock(side_effect=_slow)
    proc.returncode = None
    mock_subprocess.return_value = proc

    result = await tail_log("/var/log/app.log", n=10, timeout=1)

    assert result["ok"] is False
    assert "timed out" in result["error"].lower()


@pytest.mark.asyncio
@patch("guinvere.tools.backends.vps.asyncio.create_subprocess_exec")
async def test_tail_log_custom_lines(mock_subprocess: MagicMock) -> None:
    """tail_log uses custom line count."""
    mock_subprocess.return_value = _make_proc(b"last line\n", b"", 0)

    result = await tail_log("/var/log/app.log", n=100)

    assert result["ok"] is True
    assert result["lines"] == 100
    call_args = mock_subprocess.call_args[0]
    cmd = call_args[2]
    assert "-n 100" in cmd


# ===================================================================
# Meta / registration tests
# ===================================================================


def test_all_functions_importable() -> None:
    """All 15 functions must be importable."""
    funcs = [
        ssh_exec, scp_upload, scp_download,
        systemctl_status, systemctl_start, systemctl_stop, systemctl_restart,
        journalctl, df, du, free, uptime, ps, kill, tail_log,
    ]
    assert len(funcs) == 15


def test_all_functions_are_coroutines() -> None:
    """All 15 functions must be async coroutines."""
    funcs = [
        ssh_exec, scp_upload, scp_download,
        systemctl_status, systemctl_start, systemctl_stop, systemctl_restart,
        journalctl, df, du, free, uptime, ps, kill, tail_log,
    ]
    for fn in funcs:
        assert asyncio.iscoroutinefunction(fn), f"{fn.__name__} is not async"
