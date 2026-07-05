"""MCP Auth Matrix — Central registry mapping every tool operation to AuthLevel.

Provides the authoritative ``AUTH_MATRIX`` registry that maps all 16 MCP tools
and their operations to the appropriate ``AuthLevel``.  This module is the
single source of truth for auth-level assignment — every tool module's
``@require_approval`` decorator MUST match the level declared here.

Design:
    - ``ToolAuthEntry`` — frozen dataclass for a single tool's operation→level map.
    - ``AUTH_MATRIX`` — the complete 16-tool mapping.
    - ``get_auth_level(tool_name, operation)`` — lookup with ``KeyError`` on miss.
    - ``verify_matrix_completeness()`` — assertion gate to catch missing entries.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import structlog

from guinevere.mcp.auth import AuthLevel

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolAuthEntry:
    """Frozen registry entry mapping one tool's operations to auth levels.

    The ``operations`` dict maps operation names (e.g. ``"read"``,
    ``"write"``, ``"delete"``, ``"force_push"``, etc.) to the
    ``AuthLevel`` value required to execute that operation.

    A special ``"*"`` wildcard key means "all operations", used for
    tools where every action shares the same auth level.
    """

    tool_name: str
    operations: dict[str, AuthLevel]


# ---------------------------------------------------------------------------
# Complete Auth Matrix — ALL 16 tools
# ---------------------------------------------------------------------------


AUTH_MATRIX: Final[dict[str, dict[str, AuthLevel]]] = {
    # ---- Read-only search / lookup tools (all ops READ_AUTO) ---------------
    "brave_search": {
        "*": AuthLevel.READ_AUTO,
    },
    "context7": {
        "resolve": AuthLevel.READ_AUTO,
        "query": AuthLevel.READ_AUTO,
    },
    "exa": {
        "*": AuthLevel.READ_AUTO,
    },
    "fetch": {
        "*": AuthLevel.READ_AUTO,
    },
    "grep_app": {
        "*": AuthLevel.READ_AUTO,
    },
    "sequential_thinking": {
        "*": AuthLevel.READ_AUTO,
    },
    "time": {
        "*": AuthLevel.READ_AUTO,
    },
    "websearch": {
        "*": AuthLevel.READ_AUTO,
    },
    # ---- Multi-level tools -------------------------------------------------
    "filesystem": {
        "read": AuthLevel.READ_AUTO,
        "list": AuthLevel.READ_AUTO,
        "write": AuthLevel.WRITE_NOTIFY,
        "delete": AuthLevel.DESTRUCTIVE_APPROVAL,
    },
    "github": {
        "read": AuthLevel.READ_AUTO,
        "get": AuthLevel.READ_AUTO,
        "search": AuthLevel.READ_AUTO,
        "create_issue": AuthLevel.WRITE_NOTIFY,
        "create_pr": AuthLevel.WRITE_NOTIFY,
        "delete_repo": AuthLevel.DESTRUCTIVE_APPROVAL,
    },
    "obscura_cdp": {
        "navigate": AuthLevel.READ_AUTO,
        "read": AuthLevel.READ_AUTO,
        "form_fill": AuthLevel.WRITE_NOTIFY,
        "click": AuthLevel.WRITE_NOTIFY,
        "file_upload": AuthLevel.DESTRUCTIVE_APPROVAL,
    },
    "git": {
        "log": AuthLevel.READ_AUTO,
        "diff": AuthLevel.READ_AUTO,
        "status": AuthLevel.READ_AUTO,
        "commit": AuthLevel.WRITE_NOTIFY,
        "push": AuthLevel.WRITE_NOTIFY,
        "force_push": AuthLevel.DESTRUCTIVE_APPROVAL,
        "force_push_main": AuthLevel.FORBIDDEN,
    },
    "postgres": {
        "select": AuthLevel.READ_AUTO,
        "explain": AuthLevel.READ_AUTO,
        "describe": AuthLevel.READ_AUTO,
        "tables": AuthLevel.READ_AUTO,
        "insert": AuthLevel.WRITE_NOTIFY,
        "update": AuthLevel.WRITE_NOTIFY,
        "execute": AuthLevel.WRITE_NOTIFY,
        "delete_row": AuthLevel.DESTRUCTIVE_APPROVAL,
        "drop": AuthLevel.FORBIDDEN,
        "truncate": AuthLevel.FORBIDDEN,
    },
    "redis": {
        "get": AuthLevel.READ_AUTO,
        "lrange": AuthLevel.READ_AUTO,
        "hget": AuthLevel.READ_AUTO,
        "hgetall": AuthLevel.READ_AUTO,
        "keys": AuthLevel.READ_AUTO,
        "scan": AuthLevel.READ_AUTO,
        "ttl": AuthLevel.READ_AUTO,
        "exists": AuthLevel.READ_AUTO,
        "type": AuthLevel.READ_AUTO,
        "set": AuthLevel.WRITE_NOTIFY,
        "hset": AuthLevel.WRITE_NOTIFY,
        "lpush": AuthLevel.WRITE_NOTIFY,
        "rpush": AuthLevel.WRITE_NOTIFY,
        "sadd": AuthLevel.WRITE_NOTIFY,
        "setnx": AuthLevel.WRITE_NOTIFY,
        "setex": AuthLevel.WRITE_NOTIFY,
        "incr": AuthLevel.WRITE_NOTIFY,
        "incrbyfloat": AuthLevel.WRITE_NOTIFY,
        "del": AuthLevel.DESTRUCTIVE_APPROVAL,
        "expire": AuthLevel.WRITE_NOTIFY,
        "persist": AuthLevel.WRITE_NOTIFY,
        "rename": AuthLevel.WRITE_NOTIFY,
        "flushdb": AuthLevel.FORBIDDEN,
        "flushall": AuthLevel.FORBIDDEN,
        "config": AuthLevel.FORBIDDEN,
        "debug": AuthLevel.FORBIDDEN,
        "shutdown": AuthLevel.FORBIDDEN,
        "slaveof": AuthLevel.FORBIDDEN,
    },
    "shell": {
        "exec": AuthLevel.READ_AUTO,
        "rm_rf_root": AuthLevel.FORBIDDEN,
        "sudo_rm_rf": AuthLevel.FORBIDDEN,
    },
    "docker": {
        "ps": AuthLevel.READ_AUTO,
        "logs": AuthLevel.READ_AUTO,
        "inspect": AuthLevel.READ_AUTO,
        "images": AuthLevel.READ_AUTO,
        "start": AuthLevel.WRITE_NOTIFY,
        "stop": AuthLevel.WRITE_NOTIFY,
        "restart": AuthLevel.WRITE_NOTIFY,
        "rm": AuthLevel.WRITE_NOTIFY,
        "rmi": AuthLevel.WRITE_NOTIFY,
        "system_prune": AuthLevel.FORBIDDEN,
        "rm_all": AuthLevel.FORBIDDEN,
    },
}

# The canonical ordered list of all 16 tool names in the matrix.
ALL_TOOL_NAMES: Final[tuple[str, ...]] = (
    "brave_search",
    "context7",
    "docker",
    "exa",
    "fetch",
    "filesystem",
    "git",
    "github",
    "grep_app",
    "obscura_cdp",
    "postgres",
    "redis",
    "sequential_thinking",
    "shell",
    "time",
    "websearch",
)


# ---------------------------------------------------------------------------
# Lookup
# ---------------------------------------------------------------------------


def get_auth_level(tool_name: str, operation: str) -> AuthLevel:
    """Return the ``AuthLevel`` for *tool_name* + *operation*.

    If the tool's operation map contains a ``"*"`` wildcard, any
    *operation* string will resolve to that level.

    Args:
        tool_name: Canonical tool name (e.g. ``"brave_search"``).
        operation: Operation identifier (e.g. ``"read"``, ``"delete"``).

    Returns:
        The matching ``AuthLevel``.

    Raises:
        KeyError: If *tool_name* is not in ``AUTH_MATRIX``, or if
            *operation* is not mapped for that tool and no wildcard
            ``"*"`` key exists.
    """
    try:
        ops = AUTH_MATRIX[tool_name]
    except KeyError:
        logger.error("auth_level_lookup_tool_unknown", tool_name=tool_name)
        raise KeyError(
            f"Unknown tool '{tool_name}'. "
            f"Registered tools: {', '.join(sorted(AUTH_MATRIX))}"
        ) from None

    # Wildcard match — any operation resolves to the same level.
    if "*" in ops:
        return ops["*"]

    try:
        return ops[operation]
    except KeyError:
        logger.error(
            "auth_level_lookup_operation_unknown",
            tool_name=tool_name,
            operation=operation,
        )
        raise KeyError(
            f"Unknown operation '{operation}' for tool '{tool_name}'. "
            f"Known operations: {', '.join(sorted(ops))}"
        ) from None


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------


def verify_matrix_completeness() -> bool:
    """Verify all 16 expected tools are registered in ``AUTH_MATRIX``.

    Logs warnings for any missing tools and returns ``True`` only when
    every expected tool is present.

    Returns:
        ``True`` if the matrix is complete, ``False`` otherwise.
    """
    registered = frozenset(AUTH_MATRIX)
    expected = frozenset(ALL_TOOL_NAMES)

    missing = expected - registered
    extra = registered - expected

    if missing:
        logger.warning(
            "auth_matrix_missing_tools",
            missing=sorted(missing),
        )
    if extra:
        logger.warning(
            "auth_matrix_extra_tools",
            extra=sorted(extra),
        )

    if not missing and not extra:
        logger.info(
            "auth_matrix_complete",
            tool_count=len(AUTH_MATRIX),
        )
        return True

    return False