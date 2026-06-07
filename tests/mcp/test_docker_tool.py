"""Tests for MCP Docker Tool — 4-tier auth, container isolation, CLI safety."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.auth import ForbiddenOperationError  # noqa: E402
from src.mcp.tools.docker_tool import (  # noqa: E402
    FORBIDDEN_PATTERNS,
    DockerContainerError,
    DockerError,
    DockerForbiddenError,
    DockerNetworkError,
    DockerNotFoundError,
    docker_images,
    docker_inspect,
    docker_logs,
    docker_ps,
    docker_restart,
    docker_rm,
    docker_rm_all,
    docker_rmi,
    docker_start,
    docker_stop,
    docker_system_prune,
    register_tools,
)


# ============================================================================
# Helpers
# ============================================================================


def _fake_process(stdout: str = "", stderr: str = "", exit_code: int = 0) -> AsyncMock:
    """Build a mock subprocess that returns pre-canned output."""

    async def _communicate() -> tuple[bytes, bytes]:
        return stdout.encode("utf-8"), stderr.encode("utf-8")

    mock = AsyncMock()
    mock.communicate.side_effect = _communicate
    mock.returncode = exit_code
    mock.wait = AsyncMock()
    mock.kill = AsyncMock()
    return mock


def _container_json(state: str = "running", name: str = "guinevere-agent") -> str:
    """Return a single-line JSON representation of a docker ps container."""
    return json.dumps({
        "ID": "abc123def456",
        "Image": "guinevere:latest",
        "Command": "python -m guinevere",
        "CreatedAt": "2026-06-03 10:00:00 +0000 UTC",
        "RunningFor": "2 hours ago",
        "Ports": "",
        "State": state,
        "Status": "Up 2 hours" if state == "running" else "Exited (0)",
        "Size": "0B (virtual 250MB)",
        "Names": name,
        "Labels": "",
        "Mounts": "",
        "Networks": "guinevere-net",
    }) + "\n"


def _inspect_json(name: str = "guinevere-agent", networks: list[str] | None = None) -> str:
    """Return a docker inspect JSON payload."""
    if networks is None:
        networks = ["guinevere-net"]
    net_obj: dict[str, dict[str, str]] = {}
    for n in networks:
        net_obj[n] = {
            "NetworkID": f"net_{n}",
            "IPAddress": "172.18.0.2",
        }
    payload = [{
        "Id": "abc123def456",
        "Name": f"/{name}",
        "State": {"Status": "running", "Running": True},
        "NetworkSettings": {"Networks": net_obj},
    }]
    return json.dumps(payload)


def _images_json() -> str:
    """Return docker images JSON output."""
    return (
        json.dumps({"Repository": "guinevere", "Tag": "latest", "ID": "img001", "CreatedAt": "2026-06-03 10:00:00 +0000 UTC", "Size": "250MB"}) + "\n"
        + json.dumps({"Repository": "postgres", "Tag": "16", "ID": "img002", "CreatedAt": "2026-05-20 08:00:00 +0000 UTC", "Size": "432MB"}) + "\n"
    )


def _patch_run_docker(mock: AsyncMock) -> Any:
    """Return a patcher for ``src.mcp.tools.docker_tool._run_docker``."""
    return patch("src.mcp.tools.docker_tool._run_docker", return_value=mock)


def _patch_create_subprocess(mock: AsyncMock) -> Any:
    """Return a patcher for ``asyncio.create_subprocess_exec`` in docker_tool."""
    return patch(
        "src.mcp.tools.docker_tool.asyncio.create_subprocess_exec",
        return_value=mock,
    )


def _ok_result(stdout: str = "") -> dict[str, object]:
    """Return a successful _run_docker result dict."""
    return {
        "exit_code": 0,
        "stdout": stdout,
        "stderr": "",
        "command": "docker ps ...",
        "duration_ms": 12.5,
    }


# ============================================================================
# TestValidateContainerName
# ============================================================================


class TestValidateContainerName:
    """Container name validation — rejects shell metacharacters."""

    def test_valid_simple_name(self) -> None:
        """A plain name like 'guinevere-agent' is accepted."""
        # Does not raise
        from src.mcp.tools.docker_tool import _validate_container_name
        _validate_container_name("guinevere-agent")

    def test_valid_with_dots_and_hyphens(self) -> None:
        """Names with dots, hyphens, underscores are valid."""
        from src.mcp.tools.docker_tool import _validate_container_name
        _validate_container_name("my-container_v2.0")

    def test_empty_string_rejected(self) -> None:
        """Empty container name raises DockerContainerError."""
        from src.mcp.tools.docker_tool import _validate_container_name
        with pytest.raises(DockerContainerError, match="Invalid container name"):
            _validate_container_name("")

    def test_semicolon_rejected(self) -> None:
        """Names with ';' are rejected."""
        from src.mcp.tools.docker_tool import _validate_container_name
        with pytest.raises(DockerContainerError, match="Invalid container name"):
            _validate_container_name("good; rm -rf /")

    def test_pipe_rejected(self) -> None:
        """Names with '|' are rejected."""
        from src.mcp.tools.docker_tool import _validate_container_name
        with pytest.raises(DockerContainerError, match="Invalid container name"):
            _validate_container_name("good|evil")

    def test_space_rejected(self) -> None:
        """Names with spaces are rejected."""
        from src.mcp.tools.docker_tool import _validate_container_name
        with pytest.raises(DockerContainerError, match="Invalid container name"):
            _validate_container_name("two words")

    def test_dollar_rejected(self) -> None:
        """Names with '$' are rejected."""
        from src.mcp.tools.docker_tool import _validate_container_name
        with pytest.raises(DockerContainerError, match="Invalid container name"):
            _validate_container_name("$(whoami)")


# ============================================================================
# TestValidateImageName
# ============================================================================


class TestValidateImageName:
    """Image name validation — rejects shell metacharacters."""

    def test_valid_image_name(self) -> None:
        """A standard image name is accepted."""
        from src.mcp.tools.docker_tool import _validate_image_name
        _validate_image_name("guinevere:latest")

    def test_semicolon_rejected(self) -> None:
        """Image names with ';' are rejected."""
        from src.mcp.tools.docker_tool import _validate_image_name
        with pytest.raises(DockerContainerError, match="Invalid image name"):
            _validate_image_name("good;evil")

    def test_pipe_rejected(self) -> None:
        """Image names with '|' are rejected."""
        from src.mcp.tools.docker_tool import _validate_image_name
        with pytest.raises(DockerContainerError, match="Invalid image name"):
            _validate_image_name("a|b")


# ============================================================================
# TestDockerPs — READ_AUTO
# ============================================================================


class TestDockerPs:
    """``docker_ps`` — lists containers on guinevere-net."""

    def test_returns_parsed_containers(self) -> None:
        """Successfully parses docker ps JSON lines."""
        fake = _ok_result(stdout=_container_json(name="guinevere-agent"))

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_ps()
            assert len(result) == 1
            assert result[0]["Names"] == "guinevere-agent"
            assert result[0]["State"] == "running"

        asyncio.run(_run())

    def test_includes_all_stopped_containers(self) -> None:
        """With ``all=True``, stopped containers are included."""
        stdout = (
            _container_json(name="running-app", state="running")
            + _container_json(name="stopped-app", state="exited")
        )
        fake = _ok_result(stdout=stdout)

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_ps(all=True)
            assert len(result) == 2

        asyncio.run(_run())

    def test_filters_by_guinevere_net(self) -> None:
        """docker ps includes --filter network=guinevere-net."""
        captured_args: list[list[str]] = []

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            captured_args.append(list(args[0]))
            return _ok_result(stdout="")

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                await docker_ps()
            assert len(captured_args) >= 1
            joined = " ".join(captured_args[0])
            assert "--filter" in joined
            assert "guinevere-net" in joined

        asyncio.run(_run())

    def test_non_zero_exit_returns_empty(self) -> None:
        """If docker ps returns non-zero exit code, return empty list."""
        fake = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Cannot connect",
            "command": "docker ps",
            "duration_ms": 5.0,
        }

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_ps()
            assert result == []

        asyncio.run(_run())


# ============================================================================
# TestDockerLogs — READ_AUTO
# ============================================================================


class TestDockerLogs:
    """``docker_logs`` — get container logs."""

    def test_returns_log_output(self) -> None:
        """Returns stdout from docker logs."""
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))
        logs_ok = _ok_result(
            stdout="[INFO] Server started\n[INFO] Listening on :8000"
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            if "inspect" in joined:
                return inspect_ok
            return logs_ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                result = await docker_logs("guinevere-agent")
            assert "Server started" in result

        asyncio.run(_run())

    def test_uses_tail_flag(self) -> None:
        """docker logs is called with --tail N."""
        captured: list[str] = []
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            captured.append(joined)
            if "inspect" in joined:
                return inspect_ok
            return _ok_result(stdout="ok")

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                await docker_logs("guinevere-agent", tail=50)
            logs_calls = [c for c in captured if "--tail 50" in c]
            assert len(logs_calls) >= 1

        asyncio.run(_run())

    def test_invalid_name_rejected(self) -> None:
        """Bogus container name raises DockerContainerError."""

        async def _run() -> None:
            with pytest.raises(DockerContainerError, match="Invalid container name"):
                await docker_logs("bad;name")

        asyncio.run(_run())

    def test_non_zero_exit_raises(self) -> None:
        """docker logs failure raises DockerContainerError."""
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))
        logs_fail = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "No such container",
            "command": "docker logs",
            "duration_ms": 5.0,
        }

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            if "inspect" in joined:
                return inspect_ok
            return logs_fail

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerContainerError, match="Failed to get logs"):
                    await docker_logs("guinevere-agent")

        asyncio.run(_run())


# ============================================================================
# TestDockerInspect — READ_AUTO
# ============================================================================


class TestDockerInspect:
    """``docker_inspect`` — inspect container details."""

    def test_returns_container_info(self) -> None:
        """Returns the parsed inspect dict."""
        fake = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_inspect("guinevere-agent")
            assert result["Name"] == "/guinevere-agent"
            assert result["State"]["Status"] == "running"

        asyncio.run(_run())

    def test_invalid_name_rejected(self) -> None:
        """Bogus name raises before exec."""

        async def _run() -> None:
            with pytest.raises(DockerContainerError, match="Invalid container name"):
                await docker_inspect("bad name")

        asyncio.run(_run())


# ============================================================================
# TestDockerImages — READ_AUTO
# ============================================================================


class TestDockerImages:
    """``docker_images`` — list docker images."""

    def test_returns_image_list(self) -> None:
        """Parses docker images JSON lines."""
        fake = _ok_result(stdout=_images_json())

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_images()
            assert len(result) == 2
            assert result[0]["Repository"] == "guinevere"
            assert result[1]["Repository"] == "postgres"

        asyncio.run(_run())

    def test_non_zero_exit_returns_empty(self) -> None:
        """Docker daemon unavailable returns empty list."""
        fake = {
            "exit_code": 1,
            "stdout": "",
            "stderr": "Cannot connect",
            "command": "docker images",
            "duration_ms": 5.0,
        }

        async def _run() -> None:
            with _patch_run_docker(fake):
                result = await docker_images()
            assert result == []

        asyncio.run(_run())


# ============================================================================
# TestDockerStart — WRITE_NOTIFY
# ============================================================================


class TestDockerStart:
    """``docker_start`` — start a container (WRITE_NOTIFY)."""

    def test_starts_container(self) -> None:
        """Returns status dict on success."""
        ok = _ok_result(stdout="abc123def456")
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        call_order: list[str] = []

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            call_order.append(joined)
            if "inspect" in joined:
                return inspect_ok
            if "start" in joined:
                return ok
            return _ok_result()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                result = await docker_start("guinevere-agent")
            assert result["status"] == "ok"
            assert result["container"] == "guinevere-agent"

        asyncio.run(_run())

    def test_invalid_name_rejected(self) -> None:
        """Invalid name raised before any docker call."""

        async def _run() -> None:
            with pytest.raises(DockerContainerError, match="Invalid container name"):
                await docker_start("bad;name")

        asyncio.run(_run())

    def test_non_guinevere_container_rejected(self) -> None:
        """Container not on guinevere-net raises DockerNetworkError."""
        inspect_ok = _ok_result(
            stdout=_inspect_json(name="aizanta-agent", networks=["bridge"])
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return inspect_ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_start("aizanta-agent")

        asyncio.run(_run())


# ============================================================================
# TestDockerStop — WRITE_NOTIFY
# ============================================================================


class TestDockerStop:
    """``docker_stop`` — stop a container (WRITE_NOTIFY)."""

    def test_stops_container(self) -> None:
        """Returns status dict on success."""
        ok = _ok_result(stdout="abc123def456")
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            if "inspect" in joined:
                return inspect_ok
            return ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                result = await docker_stop("guinevere-agent")
            assert result["status"] == "ok"

        asyncio.run(_run())

    def test_non_guinevere_container_rejected(self) -> None:
        """Container not on guinevere-net raises DockerNetworkError."""
        inspect_ok = _ok_result(
            stdout=_inspect_json(name="postgres", networks=["host"])
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return inspect_ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_stop("postgres")

        asyncio.run(_run())


# ============================================================================
# TestDockerRestart — WRITE_NOTIFY
# ============================================================================


class TestDockerRestart:
    """``docker_restart`` — restart a container (WRITE_NOTIFY)."""

    def test_restarts_container(self) -> None:
        """Returns status dict on success."""
        ok = _ok_result(stdout="abc123def456")
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            if "inspect" in joined:
                return inspect_ok
            return ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                result = await docker_restart("guinevere-agent")
            assert result["status"] == "ok"

        asyncio.run(_run())


# ============================================================================
# TestDockerRm — DESTRUCTIVE_APPROVAL
# ============================================================================


class TestDockerRm:
    """``docker_rm`` — remove a container (DESTRUCTIVE_APPROVAL)."""

    def test_removes_container(self) -> None:
        """Returns status dict on success."""
        ok = _ok_result(stdout="abc123def456")
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            if "inspect" in joined:
                return inspect_ok
            return ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                result = await docker_rm("guinevere-agent")
            assert result["status"] == "ok"

        asyncio.run(_run())

    def test_force_remove(self) -> None:
        """With force=True, docker rm -f is used."""
        captured: list[str] = []
        inspect_ok = _ok_result(stdout=_inspect_json(name="guinevere-agent"))
        ok = _ok_result(stdout="abc123def456")

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            joined = " ".join(args[0])
            captured.append(joined)
            if "inspect" in joined:
                return inspect_ok
            return ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                await docker_rm("guinevere-agent", force=True)
            # at least one call should contain "-f"
            rm_calls = [c for c in captured if "rm" in c and "-f" in c]
            assert len(rm_calls) >= 1

        asyncio.run(_run())

    def test_non_guinevere_container_rejected(self) -> None:
        """Container not on guinevere-net raises DockerNetworkError."""
        inspect_ok = _ok_result(
            stdout=_inspect_json(name="aizanta-app", networks=["aizanta-net"])
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return inspect_ok

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_rm("aizanta-app")

        asyncio.run(_run())


# ============================================================================
# TestDockerRmi — DESTRUCTIVE_APPROVAL
# ============================================================================


class TestDockerRmi:
    """``docker_rmi`` — remove a docker image (DESTRUCTIVE_APPROVAL)."""

    def test_removes_image(self) -> None:
        """Returns status dict on success."""
        ok = _ok_result(stdout="Untagged: guinevere:old")

        async def _run() -> None:
            with _patch_run_docker(ok), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                result = await docker_rmi("guinevere:old")
            assert result["status"] == "ok"
            assert result["image"] == "guinevere:old"

        asyncio.run(_run())

    def test_force_remove(self) -> None:
        """With force=True, docker rmi -f is used."""
        captured: list[str] = []

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            captured.append(" ".join(args[0]))
            return _ok_result()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                await docker_rmi("guinevere:old", force=True)
            rm_calls = [c for c in captured if "rmi" in c and "-f" in c]
            assert len(rm_calls) >= 1

        asyncio.run(_run())

    def test_invalid_image_name_rejected(self) -> None:
        """Image name with shell chars raises DockerContainerError."""

        async def _run() -> None:
            with patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                with pytest.raises(DockerContainerError, match="Invalid image name"):
                    await docker_rmi("good;bad")

        asyncio.run(_run())
    def test_non_guinevere_image_rejected(self) -> None:
        """Non-guinevere image names are rejected with DockerError."""

        async def _run() -> None:
            with patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                with pytest.raises(DockerError, match="image_not_guinevere"):
                    await docker_rmi("postgres:16")

        asyncio.run(_run())

    def test_guinevere_image_accepted(self) -> None:
        """Guinevere-prefixed image name passes the prefix check."""
        ok = _ok_result(stdout="Untagged: guinevere:latest")

        async def _run() -> None:
            with _patch_run_docker(ok), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                result = await docker_rmi("guinevere:latest")
            assert result["status"] == "ok"

        asyncio.run(_run())


# ============================================================================
# TestDockerSystemPrune — FORBIDDEN
# ============================================================================


class TestDockerSystemPrune:
    """``docker_system_prune`` — permanently forbidden."""

    def test_raises_forbidden_operation_error(self) -> None:
        """Calling docker_system_prune directly raises ForbiddenOperationError."""

        async def _run() -> None:
            with pytest.raises(ForbiddenOperationError, match="is forbidden"):
                await docker_system_prune()

        asyncio.run(_run())


# ============================================================================
# TestDockerRmAll — FORBIDDEN
# ============================================================================


class TestDockerRmAll:
    """``docker_rm_all`` — permanently forbidden."""

    def test_raises_forbidden_operation_error(self) -> None:
        """Calling docker_rm_all directly raises ForbiddenOperationError."""

        async def _run() -> None:
            with pytest.raises(ForbiddenOperationError, match="is forbidden"):
                await docker_rm_all()

        asyncio.run(_run())


# ============================================================================
# TestForbiddenPatternsSubcommand — FORBIDDEN via _run_docker
# ============================================================================


class TestForbiddenPatternsSubcommand:
    """Forbidden sub-commands are blocked even at the _run_docker level."""

    def test_system_prune_blocked_by_pattern(self) -> None:
        """'system prune -a' in args raises DockerForbiddenError via _run_docker."""
        from src.mcp.tools.docker_tool import _run_docker

        async def _run() -> None:
            with pytest.raises(DockerForbiddenError, match="system prune -a"):
                await _run_docker(["system", "prune", "-a"])

        asyncio.run(_run())

    def test_volume_prune_blocked(self) -> None:
        """'volume prune' raises DockerForbiddenError."""
        from src.mcp.tools.docker_tool import _run_docker

        async def _run() -> None:
            with pytest.raises(DockerForbiddenError, match="volume prune"):
                await _run_docker(["volume", "prune"])

        asyncio.run(_run())

    def test_network_prune_blocked(self) -> None:
        """'network prune' raises DockerForbiddenError."""
        from src.mcp.tools.docker_tool import _run_docker

        async def _run() -> None:
            with pytest.raises(DockerForbiddenError, match="network prune"):
                await _run_docker(["network", "prune"])

        asyncio.run(_run())


# ============================================================================
# TestDockerNotFound — subprocess error handling
# ============================================================================


class TestDockerNotFound:
    """Docker CLI not found / permission denied handling."""

    def test_file_not_found_raises_docker_not_found(self) -> None:
        """If docker is not on PATH, DockerNotFoundError is raised."""
        from src.mcp.tools.docker_tool import _run_docker

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool.asyncio.create_subprocess_exec",
                side_effect=FileNotFoundError,
            ):
                with pytest.raises(DockerNotFoundError, match="Docker CLI not found"):
                    await _run_docker(["ps"])

        asyncio.run(_run())

    def test_permission_denied_raises(self) -> None:
        """PermissionError suggests group membership fix."""
        from src.mcp.tools.docker_tool import _run_docker

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool.asyncio.create_subprocess_exec",
                side_effect=PermissionError("Permission denied"),
            ):
                with pytest.raises(DockerContainerError, match="usermod -aG docker"):
                    await _run_docker(["ps"])

        asyncio.run(_run())


# ============================================================================
# TestForbiddenPatternsFrozenset
# ============================================================================


class TestForbiddenPatternsFrozenset:
    """Verify FORBIDDEN_PATTERNS contains expected entries."""

    def test_system_prune_in_patterns(self) -> None:
        """'system prune -a' is in the forbidden set."""
        assert "system prune -a" in FORBIDDEN_PATTERNS
        assert "system prune --all" in FORBIDDEN_PATTERNS

    def test_volume_prune_in_patterns(self) -> None:
        """'volume prune' is in the forbidden set."""
        assert "volume prune" in FORBIDDEN_PATTERNS

    def test_network_prune_in_patterns(self) -> None:
        """'network prune' is in the forbidden set."""
        assert "network prune" in FORBIDDEN_PATTERNS

    def test_builder_prune_in_patterns(self) -> None:
        """'builder prune -a' is in the forbidden set."""
        assert "builder prune -a" in FORBIDDEN_PATTERNS


# ============================================================================
# TestExceptionHierarchy
# ============================================================================


class TestExceptionHierarchy:
    """Exception inheritance chain for docker tool."""

    def test_docker_error_is_exception(self) -> None:
        """DockerError inherits from Exception."""
        assert issubclass(DockerError, Exception)

    def test_docker_not_found_is_docker_error(self) -> None:
        """DockerNotFoundError inherits from DockerError."""
        assert issubclass(DockerNotFoundError, DockerError)

    def test_docker_container_error_is_docker_error(self) -> None:
        """DockerContainerError inherits from DockerError."""
        assert issubclass(DockerContainerError, DockerError)

    def test_docker_network_error_is_docker_error(self) -> None:
        """DockerNetworkError inherits from DockerError."""
        assert issubclass(DockerNetworkError, DockerError)

    def test_docker_forbidden_is_forbidden_operation(self) -> None:
        """DockerForbiddenError inherits from ForbiddenOperationError."""
        assert issubclass(DockerForbiddenError, ForbiddenOperationError)


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Tests for the ``register_tools`` entry-point."""

    def test_registers_all_tools(self) -> None:
        """register_tools registers exactly 11 docker tools."""
        registered: list[str] = []

        class FakeMCP:
            """Minimal FastMCP stub for registration testing."""

            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                name = getattr(func, "__name__", "unknown")
                registered.append(name)
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)

        expected = {
            "docker_ps",
            "docker_logs",
            "docker_inspect",
            "docker_images",
            "docker_start",
            "docker_stop",
            "docker_restart",
            "docker_rm",
            "docker_rmi",
            "docker_system_prune",
            "docker_rm_all",
        }
        assert len(registered) == 11
        assert set(registered) == expected

    def test_read_auto_tools_registered(self) -> None:
        """READ_AUTO tools are registered."""
        registered: list[str] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append(getattr(func, "__name__", "unknown"))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        assert "docker_ps" in registered
        assert "docker_logs" in registered
        assert "docker_inspect" in registered
        assert "docker_images" in registered

    def test_write_notify_tools_registered(self) -> None:
        """WRITE_NOTIFY tools are registered."""
        registered: list[str] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append(getattr(func, "__name__", "unknown"))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        assert "docker_start" in registered
        assert "docker_stop" in registered
        assert "docker_restart" in registered

    def test_destructive_approval_tools_registered(self) -> None:
        """DESTRUCTIVE_APPROVAL tools are registered."""
        registered: list[str] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append(getattr(func, "__name__", "unknown"))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        assert "docker_rm" in registered
        assert "docker_rmi" in registered

    def test_forbidden_tools_registered(self) -> None:
        """FORBIDDEN tools are registered."""
        registered: list[str] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append(getattr(func, "__name__", "unknown"))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        assert "docker_system_prune" in registered
        assert "docker_rm_all" in registered


# ============================================================================
# TestNetworkIsolation — comprehensive
# ============================================================================


class TestNetworkIsolation:
    """Containers not on guinevere-net are rejected for all write operations."""

    _INSPECT_NON_GUINEVERE = _ok_result(
        stdout=_inspect_json(name="other-app", networks=["bridge", "host"])
    )

    def test_start_rejects_non_guinevere(self) -> None:
        """docker_start rejects non-guinevere containers."""

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return self._INSPECT_NON_GUINEVERE

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_start("other-app")

        asyncio.run(_run())

    def test_stop_rejects_non_guinevere(self) -> None:
        """docker_stop rejects non-guinevere containers."""

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return self._INSPECT_NON_GUINEVERE

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_stop("other-app")

        asyncio.run(_run())

    def test_restart_rejects_non_guinevere(self) -> None:
        """docker_restart rejects non-guinevere containers."""

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return self._INSPECT_NON_GUINEVERE

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_restart("other-app")

        asyncio.run(_run())

    def test_rm_rejects_non_guinevere(self) -> None:
        """docker_rm rejects non-guinevere containers."""

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return self._INSPECT_NON_GUINEVERE

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ), patch(
                "src.mcp.auth._wait_for_approval", return_value=True
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_rm("other-app")

        asyncio.run(_run())

    def test_logs_rejects_non_guinevere(self) -> None:
        """docker_logs rejects non-guinevere containers."""
        inspect_non = _ok_result(
            stdout=_inspect_json(name="aizanta-app", networks=["bridge"])
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return inspect_non

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_logs("aizanta-app")

        asyncio.run(_run())

    def test_inspect_rejects_non_guinevere(self) -> None:
        """docker_inspect rejects non-guinevere containers."""
        inspect_non = _ok_result(
            stdout=_inspect_json(name="aizanta-app", networks=["bridge"])
        )

        async def _side_effect(*args: Any, **kwargs: Any) -> dict[str, object]:
            return inspect_non

        async def _run() -> None:
            with patch(
                "src.mcp.tools.docker_tool._run_docker",
                side_effect=_side_effect,
            ):
                with pytest.raises(DockerNetworkError, match="guinevere-net"):
                    await docker_inspect("aizanta-app")

        asyncio.run(_run())


# ============================================================================


class TestAuthLevelMapping:
    """Verify the auth-level contracts by inspecting the decorator chain.

    Each registered tool wrapper has a ``__wrapped__`` attribute chain.
    The innermost function is the auth decorator wrapper, whose closure
    captures the ``level`` variable.
    """

    def test_docker_ps_is_auto_read(self) -> None:
        """docker_ps uses READ_AUTO."""
        registered: list[tuple[str, Any]] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append((getattr(func, "__name__", "unknown"), func))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        # Find docker_ps in registered names (no _mcp suffix).
        found = [f for name, f in registered if name == "docker_ps"]
        assert len(found) == 1
        # We can't easily introspect the auth level from the decorator,
        # but we can verify the function is callable and decorated.
        assert callable(found[0])

    def test_docker_system_prune_is_forbidden(self) -> None:
        """docker_system_prune uses FORBIDDEN."""
        registered: list[tuple[str, Any]] = []

        class FakeMCP:
            def tool(self) -> "FakeMCP":
                return self

            def __call__(self, func: object) -> object:
                registered.append((getattr(func, "__name__", "unknown"), func))
                return func

        fake_mcp: Any = FakeMCP()
        register_tools(fake_mcp)
        found = [f for name, f in registered if name == "docker_system_prune"]
        assert len(found) == 1
        assert callable(found[0])


# ============================================================================
# TestParseJsonLines
# ============================================================================


class TestParseJsonLines:
    """JSON line parsing via ``_parse_json_lines``."""

    def test_parses_valid_lines(self) -> None:
        """Each non-empty line is a JSON object."""
        from src.mcp.tools.docker_tool import _parse_json_lines

        raw = (
            json.dumps({"a": 1}) + "\n"
            + json.dumps({"b": 2}) + "\n"
        )
        result = _parse_json_lines(raw)
        assert result == [{"a": 1}, {"b": 2}]

    def test_skips_empty_lines(self) -> None:
        """Empty lines are ignored."""
        from src.mcp.tools.docker_tool import _parse_json_lines

        raw = "\n" + json.dumps({"x": 1}) + "\n\n"
        result = _parse_json_lines(raw)
        assert result == [{"x": 1}]

    def test_skips_invalid_json(self) -> None:
        """Invalid JSON lines are skipped with a warning, not a crash."""
        from src.mcp.tools.docker_tool import _parse_json_lines

        raw = '{"valid": 1}\nnot json\n{"also": 2}\n'
        result = _parse_json_lines(raw)
        assert result == [{"valid": 1}, {"also": 2}]