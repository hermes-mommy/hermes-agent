"""MCP Filesystem Tool — Secure file I/O with path whitelist enforcement.

Provides ``register_tools(mcp: FastMCP) -> None`` to register
read, write, delete, and list operations on the MCP server, each
gated with the appropriate ``AuthLevel``.

Path safety is enforced by ``validate_path``, which:
1. Rejects paths containing null bytes.
2. Resolves symlinks with ``Path.resolve()``.
3. Checks the resolved path against a frozen whitelist using
   separator-enforced prefix matching.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from src.mcp.auth import AuthLevel, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Default allowed paths — overridden by FILESYSTEM_ALLOWED_PATHS env var
# ---------------------------------------------------------------------------

_DEFAULT_ALLOWED: tuple[str, ...] = (
    "/home/guinevere/code",
    "/home/guinevere/data",
    "/home/guinevere/evidence",
    "/home/guinevere/logs",
)


@dataclass(frozen=True)
class FilesystemConfig:
    """Frozen configuration for the filesystem MCP tool.

    Allowed paths are read once at registration time.  The environment
    variable ``FILESYSTEM_ALLOWED_PATHS`` (comma-separated) overrides
    the built-in defaults listed in ``_DEFAULT_ALLOWED``.
    """

    allowed_paths: frozenset[str]

    @classmethod
    def from_env(cls) -> FilesystemConfig:
        """Build config from ``FILESYSTEM_ALLOWED_PATHS`` env var.

        If the variable is absent or empty the built-in defaults are used.
        """
        raw = os.environ.get("FILESYSTEM_ALLOWED_PATHS", "").strip()
        if raw:
            paths = tuple(p.strip() for p in raw.split(",") if p.strip())
        else:
            paths = _DEFAULT_ALLOWED
        return cls(allowed_paths=frozenset(paths))


# ---------------------------------------------------------------------------
# Custom exception
# ---------------------------------------------------------------------------


class PathForbiddenError(Exception):
    """Raised when a requested path falls outside the configured whitelist."""


# ---------------------------------------------------------------------------
# Null-byte guard
# ---------------------------------------------------------------------------


def _reject_null_bytes(path: str) -> None:
    """Raise ``ValueError`` if *path* contains a null byte."""
    if "\x00" in path:
        raise ValueError("Path contains null byte")


# ---------------------------------------------------------------------------
# Path validation
# ---------------------------------------------------------------------------


def validate_path(path: str, allowed_paths: frozenset[str]) -> Path:
    """Resolve symlinks and verify *path* is within *allowed_paths*.

    Steps:
    1. Reject null bytes in the raw path string.
    2. ``Path.resolve()`` to eliminate ``..``, symlinks, and relative segments.
    3. For each allowed base, ``Path.resolve()`` it as well and check:
       - Exact match, OR
       - ``str(resolved).startswith(str(allowed_resolved) + os.sep)``

    Returns the resolved ``Path`` on success.

    Raises:
        PathForbiddenError: if the resolved path is outside the whitelist.
    """
    _reject_null_bytes(path)

    resolved = Path(path).resolve()

    for allowed in allowed_paths:
        allowed_resolved = Path(allowed).resolve()
        if resolved == allowed_resolved:
            logger.debug(
                "path_validated_exact", path=path, allowed=allowed
            )
            return resolved
        if str(resolved).startswith(str(allowed_resolved) + os.sep):
            logger.debug(
                "path_validated_prefix", path=path, allowed=allowed
            )
            return resolved

    logger.warning(
        "path_forbidden",
        path=path,
        resolved=str(resolved),
        allowed_paths=sorted(allowed_paths),
    )
    raise PathForbiddenError(
        f"Path not in whitelist: {path} (resolved: {resolved}). "
        f"Allowed: {sorted(allowed_paths)}"
    )


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------


async def fs_read(path: str, _config: FilesystemConfig) -> str:
    """Read file contents. Auth: READ_AUTO."""
    validated = validate_path(path, _config.allowed_paths)
    logger.info("fs_read", path=str(validated))
    return validated.read_text(encoding="utf-8")


async def fs_write(path: str, content: str, _config: FilesystemConfig) -> dict[str, str]:
    """Write file contents. Auth: WRITE_NOTIFY."""
    validated = validate_path(path, _config.allowed_paths)
    logger.info("fs_write", path=str(validated))
    validated.write_text(content, encoding="utf-8")
    return {"status": "ok", "path": str(validated)}


async def fs_delete(path: str, _config: FilesystemConfig) -> dict[str, str]:
    """Delete a file. Auth: DESTRUCTIVE_APPROVAL."""
    validated = validate_path(path, _config.allowed_paths)
    logger.info("fs_delete", path=str(validated))
    validated.unlink(missing_ok=False)
    return {"status": "deleted", "path": str(validated)}


async def fs_list(path: str, _config: FilesystemConfig) -> list[str]:
    """List directory contents. Auth: READ_AUTO."""
    validated = validate_path(path, _config.allowed_paths)
    logger.info("fs_list", path=str(validated))
    return sorted(p.name for p in validated.iterdir())


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register filesystem tools on the MCP server.

    Adds four tools: ``fs_read``, ``fs_write``, ``fs_delete``, and ``fs_list``,
    each decorated with the appropriate ``AuthLevel`` gate.

    The ``FilesystemConfig`` is built once from the environment at
    registration time and frozen for the server's lifetime.
    """
    config = FilesystemConfig.from_env()

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="fs_read")
    async def _fs_read(path: str) -> str:
        return await fs_read(path, config)

    @mcp.tool()
    @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="fs_write")
    async def _fs_write(path: str, content: str) -> dict[str, str]:
        return await fs_write(path, content, config)

    @mcp.tool()
    @require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="fs_delete")
    async def _fs_delete(path: str) -> dict[str, str]:
        return await fs_delete(path, config)

    @mcp.tool()
    @require_approval(AuthLevel.READ_AUTO, tool_name="fs_list")
    async def _fs_list(path: str) -> list[str]:
        return await fs_list(path, config)

    logger.info(
        "filesystem_tools_registered",
        allowed_paths=sorted(config.allowed_paths),
    )