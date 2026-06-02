"""MCP Docker Tool — Container lifecycle management via docker CLI.

Provides ``register_tools(mcp: FastMCP) -> None`` to register Docker
management tools on the MCP server with 4-tier auth safety:

    - READ_AUTO: ``docker_ps``, ``docker_logs``, ``docker_inspect``, ``docker_images``
    - WRITE_NOTIFY: ``docker_start``, ``docker_stop``, ``docker_restart``
    - DESTRUCTIVE_APPROVAL: ``docker_rm``, ``docker_rmi``
    - FORBIDDEN: ``docker_system_prune``, ``docker_rm_all``

Isolation: only containers attached to the ``guinevere-net`` docker
network are manageable. All execution uses ``asyncio.create_subprocess_exec``.
"""

from __future__ import annotations

import asyncio
import json
import re
import time
from typing import TYPE_CHECKING, Any

import structlog

from src.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GUINEVERE_NETWORK: str = "guinevere-net"

# Container names: letters, digits, underscore, dot, hyphen. Must start
# with a letter or digit.  Rejects shell meta-characters and whitespace.
_CONTAINER_NAME_RE: re.Pattern[str] = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_.\-]*$")

# Docker sub-commands that are unconditionally forbidden regardless of
# auth level.  These are checked in ``_run_docker`` before spawning.
FORBIDDEN_PATTERNS: frozenset[str] = frozenset({
    "system prune -a",
    "system prune --all",
    "volume prune",
    "network prune",
    "builder prune -a",
})


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------


class DockerError(Exception):
    """Base exception for docker operations."""


class DockerNotFoundError(DockerError):
    """Docker CLI is not installed or not found on PATH."""


class DockerContainerError(DockerError):
    """Operation on a container failed (not found, permission, etc.)."""


class DockerNetworkError(DockerError):
    """Container is not on the guinevere-net network."""


class DockerForbiddenError(ForbiddenOperationError):
    """A forbidden docker sub-command was attempted."""


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def _validate_container_name(name: str) -> None:
    """Raise ``DockerContainerError`` if *name* is not a valid container name.

    Only allows ``[a-zA-Z0-9][a-zA-Z0-9_.-]*`` — blocks shell meta-characters.
    """
    if not name or not _CONTAINER_NAME_RE.match(name):
        logger.warning("docker_invalid_container_name", container=name)
        raise DockerContainerError(
            f"Invalid container name: {name!r}. "
            "Must match [a-zA-Z0-9][a-zA-Z0-9_.-]*"
        )


def _validate_image_name(name: str) -> None:
    """Raise ``DockerContainerError`` if *name* contains dangerous characters.

    Image names are more permissive than containers, but we still reject
    shell metacharacters.
    """
    dangerous = frozenset({";", "|", "&", "`", "$", "(", ")", ">", "<", "\n"})
    if any(c in name for c in dangerous):
        logger.warning("docker_invalid_image_name", image=name)
        raise DockerContainerError(
            f"Invalid image name: {name!r}. Contains forbidden characters."
        )


def _check_forbidden_pattern(args: list[str]) -> None:
    """Scan assembled *args* for forbidden docker sub-commands.

    Raises:
        DockerForbiddenError: If a ``FORBIDDEN_PATTERNS`` substring is found.
    """
    arg_str = " ".join(args)
    for pattern in FORBIDDEN_PATTERNS:
        if pattern in arg_str:
            logger.warning("docker_forbidden_pattern", args=args, pattern=pattern)
            raise DockerForbiddenError(
                f"Docker operation '{pattern}' is forbidden."
            )


# ---------------------------------------------------------------------------
# Network isolation
# ---------------------------------------------------------------------------


async def _check_guinevere_network(container: str) -> None:
    """Verify *container* is attached to ``guinevere-net``.

    Inspects the container and checks ``NetworkSettings.Networks``.
    If the container is not found or not on the expected network,
    ``DockerNetworkError`` is raised.
    """
    try:
        info = await _docker_inspect_raw(container)
    except DockerContainerError:
        raise DockerNetworkError(
            f"Container {container!r} not found — cannot verify network membership."
        )

    networks = info.get("NetworkSettings", {}).get("Networks", {})
    if _GUINEVERE_NETWORK not in networks:
        logger.warning(
            "docker_container_wrong_network",
            container=container,
            networks=list(networks.keys()),
        )
        raise DockerNetworkError(
            f"Container {container!r} is not on the '{_GUINEVERE_NETWORK}' network. "
            f"Found networks: {list(networks.keys())}. "
            "Only guinevere-net containers are manageable."
        )


# ---------------------------------------------------------------------------
# Docker CLI execution
# ---------------------------------------------------------------------------


async def _run_docker(args: list[str], timeout: int = 30) -> dict[str, Any]:
    """Execute ``docker args...`` via ``asyncio.create_subprocess_exec``.

    Args:
        args: Positional arguments to ``docker`` (e.g. ``["ps", "--format", "{{json .}}"]``).
        timeout: Deadline in seconds.

    Returns:
        Dict with ``exit_code``, ``stdout``, ``stderr``, ``command``, ``duration_ms``.

    Raises:
        DockerNotFoundError: If the docker binary is not found.
        DockerForbiddenError: If the args match a ``FORBIDDEN_PATTERNS`` entry.
    """
    _check_forbidden_pattern(args)

    start = time.monotonic()

    full_args = ["docker", *args]
    logger.debug("docker_exec", args=args)

    try:
        process = await asyncio.create_subprocess_exec(
            *full_args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
    except FileNotFoundError:
        logger.error("docker_not_found")
        raise DockerNotFoundError(
            "Docker CLI not found. Is Docker installed and on PATH?"
        )
    except PermissionError as exc:
        logger.error("docker_permission_denied", error=str(exc))
        raise DockerContainerError(
            "Permission denied running docker. "
            "Ensure user 'guinevere' is in the 'docker' group: "
            "sudo usermod -aG docker guinevere"
        ) from exc

    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(), timeout=timeout
        )
    except asyncio.TimeoutError:
        process.kill()
        await process.wait()
        elapsed = (time.monotonic() - start) * 1000
        logger.error("docker_timeout", args=args, timeout=timeout, duration_ms=elapsed)
        raise DockerError(f"Docker command timed out after {timeout}s: {full_args}")

    exit_code = process.returncode if process.returncode is not None else -1
    elapsed = (time.monotonic() - start) * 1000

    stdout = stdout_bytes.decode("utf-8", errors="replace").strip()
    stderr = stderr_bytes.decode("utf-8", errors="replace").strip()

    log_level = "error" if exit_code != 0 else "debug"
    getattr(logger, log_level)(
        "docker_exec_done",
        args=args,
        exit_code=exit_code,
        duration_ms=round(elapsed, 2),
        stdout_len=len(stdout),
        stderr_len=len(stderr),
    )

    return {
        "exit_code": exit_code,
        "stdout": stdout,
        "stderr": stderr,
        "command": " ".join(full_args),
        "duration_ms": round(elapsed, 2),
    }


def _parse_json_lines(raw: str) -> list[dict[str, str]]:
    """Parse newline-delimited JSON objects from docker CLI output.

    Docker ``--format '{{json .}}'`` emits one JSON object per line.
    Empty lines are skipped.
    """
    results: list[dict[str, str]] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            parsed = json.loads(line)
            if isinstance(parsed, dict):
                results.append(parsed)
        except json.JSONDecodeError as exc:
            logger.warning("docker_json_parse_error", line=line[:200], error=str(exc))
    return results


async def _docker_inspect_raw(container: str) -> dict[str, Any]:
    """Inspect a container and return the full dict — used internally.

    Raises:
        DockerContainerError: If the container is not found.
    """
    result = await _run_docker(["inspect", container])
    if result["exit_code"] != 0:
        logger.warning(
            "docker_inspect_failed",
            container=container,
            stderr=str(result["stderr"]),
        )
        raise DockerContainerError(
            f"Container {container!r} not found. {result['stderr']}"
        )

    try:
        data: list[dict[str, Any]] = json.loads(str(result["stdout"]))
    except json.JSONDecodeError as exc:
        raise DockerContainerError(
            f"Failed to parse docker inspect output for {container!r}: {exc}"
        )

    if not data:
        raise DockerContainerError(f"Container {container!r} not found.")

    return data[0]


# ---------------------------------------------------------------------------
# READ_AUTO tools — safe, read-only
# ---------------------------------------------------------------------------


async def docker_ps(all: bool = False) -> list[dict[str, str]]:
    """List containers on the guinevere-net network.

    Args:
        all: If ``True``, include stopped containers (``docker ps -a``).

    Returns:
        List of container info dicts (ID, Image, Names, State, Status, etc.).
    """
    args = ["ps", "--filter", f"network={_GUINEVERE_NETWORK}", "--format", "{{json .}}"]
    if all:
        args.insert(1, "-a")

    result = await _run_docker(args)
    if result["exit_code"] != 0:
        logger.warning("docker_ps_failed", exit_code=result["exit_code"], stderr=result["stderr"])
        return []

    return _parse_json_lines(str(result["stdout"]))


async def docker_logs(container: str, tail: int = 100) -> str:
    """Get container logs from stdout/stderr.

    Args:
        container: Container name or ID.
        tail: Number of lines to return from the end (default 100).

    Returns:
        Log text as a single string.
    """
    _validate_container_name(container)

    result = await _run_docker(["logs", "--tail", str(tail), container])
    if result["exit_code"] != 0:
        logger.warning(
            "docker_logs_failed",
            container=container,
            exit_code=result["exit_code"],
            stderr=result["stderr"],
        )
        raise DockerContainerError(
            f"Failed to get logs for container {container!r}: {result['stderr']}"
        )

    return str(result["stdout"])


async def docker_inspect(container: str) -> dict[str, Any]:
    """Inspect container details.

    Args:
        container: Container name or ID.

    Returns:
        Full container inspection dict (ID, Created, State, Config, etc.).
    """
    _validate_container_name(container)
    return await _docker_inspect_raw(container)


async def docker_images(all: bool = False) -> list[dict[str, str]]:
    """List docker images.

    Args:
        all: If ``True``, include intermediate image layers (``-a`` flag).

    Returns:
        List of image info dicts (Repository, Tag, ID, Created, Size, etc.).
    """
    args = ["images", "--format", "{{json .}}"]
    if all:
        args.insert(1, "-a")

    result = await _run_docker(args)
    if result["exit_code"] != 0:
        logger.warning(
            "docker_images_failed",
            exit_code=result["exit_code"],
            stderr=result["stderr"],
        )
        return []

    return _parse_json_lines(str(result["stdout"]))


# ---------------------------------------------------------------------------
# WRITE_NOTIFY tools — execute then notify Discord
# ---------------------------------------------------------------------------


async def docker_start(container: str) -> dict[str, str]:
    """Start a stopped container.

    Args:
        container: Container name or ID. Must be on guinevere-net.

    Returns:
        Dict with ``status``, ``container``, and ``message`` keys.
    """
    _validate_container_name(container)
    await _check_guinevere_network(container)

    result = await _run_docker(["start", container])
    if result["exit_code"] != 0:
        raise DockerContainerError(
            f"Failed to start container {container!r}: {result['stderr']}"
        )

    logger.info("docker_container_started", container=container)
    return {"status": "ok", "container": container, "message": f"Container {container} started."}


async def docker_stop(container: str) -> dict[str, str]:
    """Stop a running container.

    Args:
        container: Container name or ID. Must be on guinevere-net.

    Returns:
        Dict with ``status``, ``container``, and ``message`` keys.
    """
    _validate_container_name(container)
    await _check_guinevere_network(container)

    result = await _run_docker(["stop", container])
    if result["exit_code"] != 0:
        raise DockerContainerError(
            f"Failed to stop container {container!r}: {result['stderr']}"
        )

    logger.info("docker_container_stopped", container=container)
    return {"status": "ok", "container": container, "message": f"Container {container} stopped."}


async def docker_restart(container: str) -> dict[str, str]:
    """Restart a container.

    Args:
        container: Container name or ID. Must be on guinevere-net.

    Returns:
        Dict with ``status``, ``container``, and ``message`` keys.
    """
    _validate_container_name(container)
    await _check_guinevere_network(container)

    result = await _run_docker(["restart", container])
    if result["exit_code"] != 0:
        raise DockerContainerError(
            f"Failed to restart container {container!r}: {result['stderr']}"
        )

    logger.info("docker_container_restarted", container=container)
    return {"status": "ok", "container": container, "message": f"Container {container} restarted."}


# ---------------------------------------------------------------------------
# DESTRUCTIVE_APPROVAL tools — operator must approve
# ---------------------------------------------------------------------------


async def docker_rm(container: str, force: bool = False) -> dict[str, str]:
    """Remove a container.

    Args:
        container: Container name or ID. Must be on guinevere-net.
        force: If ``True``, forcefully remove even if running (``docker rm -f``).

    Returns:
        Dict with ``status``, ``container``, and ``message`` keys.
    """
    _validate_container_name(container)
    await _check_guinevere_network(container)

    args = ["rm"]
    if force:
        args.append("-f")
    args.append(container)

    result = await _run_docker(args)
    if result["exit_code"] != 0:
        raise DockerContainerError(
            f"Failed to remove container {container!r}: {result['stderr']}"
        )

    logger.info("docker_container_removed", container=container, force=force)
    return {"status": "ok", "container": container, "message": f"Container {container} removed."}


async def docker_rmi(image: str, force: bool = False) -> dict[str, str]:
    """Remove a docker image.

    Args:
        image: Image name or ID.
        force: If ``True``, force removal (``docker rmi -f``).

    Returns:
        Dict with ``status``, ``image``, and ``message`` keys.
    """
    _validate_image_name(image)

    args = ["rmi"]
    if force:
        args.append("-f")
    args.append(image)

    result = await _run_docker(args)
    if result["exit_code"] != 0:
        raise DockerContainerError(
            f"Failed to remove image {image!r}: {result['stderr']}"
        )

    logger.info("docker_image_removed", image=image, force=force)
    return {"status": "ok", "image": image, "message": f"Image {image} removed."}


# ---------------------------------------------------------------------------
# FORBIDDEN tools — always blocked
# ---------------------------------------------------------------------------


async def docker_system_prune() -> dict[str, str]:
    """FORBIDDEN: docker system prune is too dangerous.

    The decorator raises ``ForbiddenOperationError`` before this body
    ever executes.  The function exists only so it can be registered
    as an MCP tool with a clear rejection message.
    """
    raise ForbiddenOperationError("docker system prune -a is permanently forbidden.")


async def docker_rm_all() -> dict[str, str]:
    """FORBIDDEN: mass container/image deletion is too dangerous.

    The decorator raises ``ForbiddenOperationError`` before this body
    ever executes.  The function exists only so it can be registered
    as an MCP tool with a clear rejection message.
    """
    raise ForbiddenOperationError("Mass container/image removal is permanently forbidden.")


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register all Docker management tools on the MCP server.

    Four auth tiers:
        - READ_AUTO: ps, logs, inspect, images
        - WRITE_NOTIFY: start, stop, restart
        - DESTRUCTIVE_APPROVAL: rm, rmi
        - FORBIDDEN: system_prune, rm_all
    """

    # -- READ_AUTO -----------------------------------------------------------

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="docker_ps")
    async def docker_ps_mcp(all: bool = False) -> list[dict[str, str]]:
        return await docker_ps(all=all)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="docker_logs")
    async def docker_logs_mcp(container: str, tail: int = 100) -> str:
        return await docker_logs(container, tail=tail)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="docker_inspect")
    async def docker_inspect_mcp(container: str) -> dict[str, Any]:
        return await docker_inspect(container)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="docker_images")
    async def docker_images_mcp(all: bool = False) -> list[dict[str, str]]:
        return await docker_images(all=all)

    # -- WRITE_NOTIFY --------------------------------------------------------

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="docker_start")
    async def docker_start_mcp(container: str) -> dict[str, str]:
        return await docker_start(container)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="docker_stop")
    async def docker_stop_mcp(container: str) -> dict[str, str]:
        return await docker_stop(container)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="docker_restart")
    async def docker_restart_mcp(container: str) -> dict[str, str]:
        return await docker_restart(container)

    # -- DESTRUCTIVE_APPROVAL ------------------------------------------------

    @mcp.tool()
    @require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="docker_rm")
    async def docker_rm_mcp(container: str, force: bool = False) -> dict[str, str]:
        return await docker_rm(container, force=force)

    @mcp.tool()
    @require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="docker_rmi")
    async def docker_rmi_mcp(image: str, force: bool = False) -> dict[str, str]:
        return await docker_rmi(image, force=force)

    # -- FORBIDDEN -----------------------------------------------------------

    @mcp.tool()
    @require_approval(AuthLevel.FORBIDDEN, tool_name="docker_system_prune")
    async def docker_system_prune_mcp() -> dict[str, str]:
        return await docker_system_prune()

    @mcp.tool()
    @require_approval(AuthLevel.FORBIDDEN, tool_name="docker_rm_all")
    async def docker_rm_all_mcp() -> dict[str, str]:
        return await docker_rm_all()

    logger.info("docker_tools_registered", count=11)