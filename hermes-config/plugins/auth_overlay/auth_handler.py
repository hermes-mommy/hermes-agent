"""Auth handler — tool name normalisation and AuthLevel enforcement.

This module is the core of the auth overlay plugin.  It:

1. Normalises Hermes/native/MCP tool names to canonical (tool, operation) pairs.
2. Looks up the ``AuthLevel`` from ``src.mcp.auth_matrix``.
3. Enforces the level: READ_AUTO → allow, WRITE_NOTIFY → notify + allow,
   DESTRUCTIVE_APPROVAL → persist approval request → block, FORBIDDEN → block.
4. Returns Hermes-compatible ``{"action": "block", ...}`` or ``None`` (allow).
5. Fails closed on any unexpected exception.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Protocol, cast

import structlog

# Import the canonical auth matrix as the sole runtime auth source.
from src.mcp.auth import AuthLevel, ForbiddenOperationError
from src.mcp.auth_matrix import (
    AUTH_MATRIX,
    ALL_TOOL_NAMES,
    get_auth_level,
)

from .approval_handler import APPROVAL_TTL_SECONDS, ApprovalHandler
from .forbidden_handler import handle_forbidden
from .notify_handler import NotifyHandler

class Logger(Protocol):
    def info(self, event: str, **kwargs: object) -> None: ...
    def warning(self, event: str, **kwargs: object) -> None: ...
    def error(self, event: str, **kwargs: object) -> None: ...


logger = cast(Logger, structlog.get_logger(__name__))

ToolArgs = Mapping[str, object]

# ==============================================================================
# Canonical tool set (frozenset for O(1) membership checks)
# ==============================================================================

_CANONICAL_TOOLS: frozenset[str] = frozenset(ALL_TOOL_NAMES)

# ==============================================================================
# Prefix patterns to strip from Hermes/MCP tool names
# ==============================================================================

KNOWN_PREFIXES: list[str] = [
    "mcp_fastmcp_custom_",
    "mcp_fastmcp_full_",
    "mcp_fastmcp_",
    "mcp_native_",
    "mcp_",
    "hermes_",
]

# ==============================================================================
# Tool-name alias map: non-canonical name → (canonical_tool, operation)
# ==============================================================================
# Covers native Hermes tool names, terminal/git aliases, shell aliases, and
# any FastMCP registered names that do not follow the tool_operation pattern.

TOOL_ALIASES: dict[str, tuple[str, str] | None] = {
    # --- Native Hermes tool aliases ---
    "fetch_url": ("fetch", "*"),
    "fetch_get": ("fetch", "*"),
    "fetch_page": ("fetch", "*"),
    "web_search": ("websearch", "*"),
    "websearch_search": ("websearch", "*"),
    "web_browse": ("fetch", "*"),
    "webfetch": ("fetch", "*"),
    # --- Hermes native tool aliases (VPS logs show these are blocked) ---
    "read_file": ("filesystem", "read"),
    "write_file": ("filesystem", "write"),
    "search_files": ("filesystem", "read"),
    "execute_code": ("shell", "exec"),
    "memory": ("redis", "get"),          # Hermes built-in memory → safe read
    "skills_list": ("shell", "exec"),    # Internal Hermes op → safe read
    "skill_manage": ("shell", "exec"),   # Internal Hermes op → safe read
    # --- Terminal / shell aliases ---
    "shell_exec": ("shell", "exec"),
    "terminal_exec": ("shell", "exec"),
    "terminal": ("shell", "exec"),
    "terminal.read_commands": ("shell", "exec"),
    "terminal.write_commands": ("shell", "exec"),
    "terminal.destructive_commands": ("shell", "exec"),
    # --- Git aliases ---
    "git_log": ("git", "log"),
    "git_diff": ("git", "diff"),
    "git_status": ("git", "status"),
    "git_commit": ("git", "commit"),
    "git_push": ("git", "push"),
    "git_force_push": ("git", "force_push"),
    "git_force_push_main": ("git", "force_push_main"),
    # --- Git force-push name mismatch ---
    "git_push_force": ("git", "force_push"),
    # --- Filesystem aliases ---
    "filesystem_read": ("filesystem", "read"),
    "filesystem_write": ("filesystem", "write"),
    "filesystem_delete": ("filesystem", "delete"),
    "filesystem_list": ("filesystem", "list"),
    "filesystem_create_directory": ("filesystem", "write"),
    # --- MCP fs_* aliases (registered names differ from overlay) ---
    "fs_read": ("filesystem", "read"),
    "fs_write": ("filesystem", "write"),
    "fs_delete": ("filesystem", "delete"),
    "fs_list": ("filesystem", "list"),
    # --- Redis aliases ---
    "redis_get": ("redis", "get"),
    "redis_set": ("redis", "set"),
    "redis_del": ("redis", "del"),
    "redis_keys": ("redis", "keys"),
    "redis_lrange": ("redis", "lrange"),
    "redis_hget": ("redis", "hget"),
    "redis_hset": ("redis", "hset"),
    "redis_flushdb": ("redis", "flushdb"),
    "redis_expire": ("redis", "expire"),
    # --- Redis additional aliases (S1 batch) ---
    "redis_scan": ("redis", "scan"),
    "redis_ttl": ("redis", "ttl"),
    "redis_exists": ("redis", "exists"),
    "redis_type": ("redis", "type"),
    "redis_lpush": ("redis", "lpush"),
    "redis_rpush": ("redis", "rpush"),
    "redis_sadd": ("redis", "sadd"),
    "redis_setnx": ("redis", "setnx"),
    "redis_setex": ("redis", "setex"),
    "redis_incr": ("redis", "incr"),
    "redis_incrbyfloat": ("redis", "incrbyfloat"),
    "redis_persist": ("redis", "persist"),
    "redis_rename": ("redis", "rename"),
    # --- Postgres aliases ---
    "postgres_query": ("postgres", "select"),
    "postgres_select": ("postgres", "select"),
    "postgres_insert": ("postgres", "insert"),
    "postgres_update": ("postgres", "update"),
    "postgres_delete_row": ("postgres", "delete_row"),
    "postgres_drop": ("postgres", "drop"),
    # --- Postgres S3b aliases (new tool functions) ---
    "postgres_execute": ("postgres", "insert"),   # covers insert and update
    "postgres_delete": ("postgres", "delete_row"),
    # --- Docker aliases ---
    "docker_ps": ("docker", "ps"),
    "docker_logs": ("docker", "logs"),
    "docker_start": ("docker", "start"),
    "docker_stop": ("docker", "stop"),
    "docker_restart": ("docker", "restart"),
    "docker_rm": ("docker", "rm"),
    "docker_rmi": ("docker", "rmi"),
    "docker_system_prune": ("docker", "system_prune"),
    # --- Docker inspect/images (S1 batch) ---
    "docker_inspect": ("docker", "inspect"),
    "docker_images": ("docker", "images"),
    # --- Github aliases ---
    "github_create_issue": ("github", "create_issue"),
    "github_create_pr": ("github", "create_pr"),
    # --- GitHub read/get/search aliases (S1 batch) ---
    "github_list_repos": ("github", "read"),
    "github_get_file": ("github", "get"),
    "github_search_code": ("github", "search"),
    # --- Obscura aliases ---
    "obscura_get_markdown": ("obscura_cdp", "read"),
    "obscura_navigate": ("obscura_cdp", "navigate"),
    "obscura_read": ("obscura_cdp", "read"),
    "obscura_form_fill": ("obscura_cdp", "form_fill"),
    "obscura_click": ("obscura_cdp", "click"),
    "obscura_file_upload": ("obscura_cdp", "file_upload"),
    # --- Context7 aliases ---
    "context7_resolve": ("context7", "resolve"),
    "context7_query": ("context7", "query"),
    # --- Sequential thinking alias ---
    "sequential_thinking_think": ("sequential_thinking", "*"),
    # --- Time aliases ---
    "time_current": ("time", "*"),
    "time_convert": ("time", "*"),
    # --- Time tools (additional, S1 batch) ---
    "time_days_in_month": ("time", "*"),
    "time_relative_time": ("time", "*"),
    "time_get_timestamp": ("time", "*"),
    "time_get_week_year": ("time", "*"),
    "time_convert_time": ("time", "*"),
    "time_current_time": ("time", "*"),
    # --- Brave_search / exa alias ---
    "brave_search_search": ("brave_search", "*"),
    "exa_search": ("exa", "*"),
    "exa_fetch": ("exa", "*"),
    # --- grep_app aliases ---
    "grep_app_search": ("grep_app", "*"),
    # --- Internal (not real tools — block) ---
    "require_approval": None,
}

# ==============================================================================
# Tools that have a wildcard "*" operation mapping
# ==============================================================================

_WILDCARD_TOOLS: frozenset[str] = frozenset(
    tool for tool, ops in AUTH_MATRIX.items() if "*" in ops
)


def _resolve_operation(canonical_tool: str, args: ToolArgs | None) -> str:
    """Extract the operation from *args* for a known canonical tool.

    Args:
        canonical_tool: Known canonical tool name.
        args: Tool invocation arguments.

    Returns:
        The resolved operation string (defaults to ``"read"``).
    """
    # Wildcard tools accept any operation.
    if canonical_tool in _WILDCARD_TOOLS:
        return "*"

    if args:
        op = args.get("operation") or args.get("action") or args.get("command")
        if isinstance(op, str) and op:
            return op
    return "read"


def normalize_tool_name(
    raw_name: str,
    args: ToolArgs | None = None,
) -> tuple[str, str] | None:
    """Normalise a Hermes/MCP tool name to a canonical (tool, operation) pair.

    The normalisation pipeline:

    1. Check the explicit ``TOOL_ALIASES`` map.
    2. Strip known MCP/Hermes prefixes.
    3. If the stripped name is a canonical tool, extract operation from *args*.
    4. Split ``tool_operation`` (longest canonical tool match).
    5. Check the alias map with the stripped name.
    6. Fall back to extracting tool from *args*.

    Args:
        raw_name: The raw Hermes tool name (e.g. ``mcp_fastmcp_custom_redis_get``).
        args: Optional dict of tool arguments.

    Returns:
        ``(canonical_tool, operation)`` or ``None`` if the name is unknown.
    """
    # Step 1 — Direct alias lookup.
    if raw_name in TOOL_ALIASES:
        result = TOOL_ALIASES[raw_name]
        if result is None:
            return None  # Explicitly blocked internal name.
        return result

    # Step 2 — Strip known prefixes.
    stripped = raw_name
    for prefix in KNOWN_PREFIXES:
        if stripped.startswith(prefix):
            stripped = stripped[len(prefix):]
            break

    # If stripping consumed everything, unknown.
    if not stripped:
        return None

    # Step 3 — Exact canonical match.
    if stripped in _CANONICAL_TOOLS:
        op = _resolve_operation(stripped, args)
        return (stripped, op)

    # Step 4 — Try ``tool_operation`` split (longest canonical tool first).
    # Sort by length descending so ``sequential_thinking`` matches before
    # just ``sequential`` (which doesn't exist), etc.
    for tool in sorted(_CANONICAL_TOOLS, key=len, reverse=True):
        prefix_check = tool + "_"
        if stripped == tool:
            op = _resolve_operation(tool, args)
            return (tool, op)
        if stripped.startswith(prefix_check):
            operation = stripped[len(prefix_check):]
            # Accept any operation for wildcard tools; validate for others.
            tool_ops = AUTH_MATRIX.get(tool, {})
            if operation in tool_ops or "*" in tool_ops:
                return (tool, operation)
            # Operation not in matrix — fall through to alias check
            # rather than defaulting to "read".  This allows aliases
            # like ``postgres_query → select`` to resolve correctly.
            break

    # Step 5 — Check alias map with the stripped name.
    if stripped in TOOL_ALIASES:
        result = TOOL_ALIASES[stripped]
        if result is None:
            return None
        return result

    # Step 6 — Try extracting tool from args.
    if args:
        tool_arg = args.get("_tool") or args.get("tool")
        if isinstance(tool_arg, str) and tool_arg in _CANONICAL_TOOLS:
            op = _resolve_operation(tool_arg, args)
            return (tool_arg, op)

    return None  # Unknown — will be blocked fail-closed.


# ==============================================================================
# Plugin
# ==============================================================================


class AuthOverlayPlugin:
    """Hermes plugin that enforces the auth matrix on every ``pre_tool_call``.

    The plugin uses Python ``src.mcp.auth_matrix`` as the sole runtime auth
    source and fails closed on any error.
    """

    def __init__(
        self,
        approval_handler: ApprovalHandler | None = None,
        notify_handler: NotifyHandler | None = None,
    ) -> None:
        self._approval: ApprovalHandler = approval_handler or ApprovalHandler()
        self._notify: NotifyHandler = notify_handler or NotifyHandler()

    # ------------------------------------------------------------------
    # Hook: pre_tool_call
    # ------------------------------------------------------------------

    def pre_tool_call(self, **kwargs: object) -> dict[str, str] | None:
        """Enforce auth matrix before tool execution.

        Args:
            **kwargs: Hermes hook kwargs including ``tool_name``, ``args``,
                ``session_id``, ``task_id``.

        Returns:
            ``None`` to allow the tool, or ``{"action": "block", ...}`` to
            block it.
        """
        raw_tool_value = kwargs.get("tool_name", "unknown")
        raw_tool_name = raw_tool_value if isinstance(raw_tool_value, str) else "unknown"
        args_value = kwargs.get("args")
        args = cast(ToolArgs, args_value) if isinstance(args_value, Mapping) else None

        try:
            return self._enforce(raw_tool_name, args)
        except ForbiddenOperationError:
            logger.warning(
                "auth_overlay_forbidden_error",
                tool=raw_tool_name,
            )
            return {
                "action": "block",
                "reason": f"AUTH_FORBIDDEN:{raw_tool_name}",
                "message": f"Operation '{raw_tool_name}' is forbidden.",
            }
        except Exception:
            logger.error(
                "auth_overlay_enforcement_error",
                tool=raw_tool_name,
                exc_info=True,
            )
            # Fail-closed: any unexpected exception blocks execution.
            return {
                "action": "block",
                "reason": "AUTH_OVERLAY_ERROR",
                "message": (
                    "Auth overlay encountered an unexpected error. "
                    "Tool execution blocked for safety."
                ),
            }

    # ------------------------------------------------------------------
    # Internal enforcement logic
    # ------------------------------------------------------------------

    def _enforce(
        self,
        raw_tool_name: str,
        args: ToolArgs | None,
    ) -> dict[str, str] | None:
        """Core enforcement — extracted for testability."""
        # --- 1. Normalise tool name ---
        canonical = normalize_tool_name(raw_tool_name, args)
        if canonical is None:
            logger.warning(
                "auth_overlay_unknown_tool",
                raw_tool_name=raw_tool_name,
            )
            return {
                "action": "block",
                "reason": f"AUTH_UNKNOWN_TOOL:{raw_tool_name}",
                "message": (
                    f"Unknown tool '{raw_tool_name}' — blocked by auth overlay."
                ),
            }

        canonical_tool, operation = canonical

        # --- 2. Look up auth level ---
        try:
            level = get_auth_level(canonical_tool, operation)
        except KeyError:
            logger.warning(
                "auth_overlay_unknown_operation",
                tool=canonical_tool,
                operation=operation,
                raw_tool_name=raw_tool_name,
            )
            return {
                "action": "block",
                "reason": f"AUTH_UNKNOWN_OPERATION:{canonical_tool}:{operation}",
                "message": (
                    f"Unknown operation '{operation}' for tool "
                    f"'{canonical_tool}' — blocked."
                ),
            }

        logger.info(
            "auth_overlay_check",
            tool=canonical_tool,
            operation=operation,
            level=level.value,
            raw_tool_name=raw_tool_name,
        )

        # --- 3. Enforce ---

        # FORBIDDEN — block immediately.
        if level is AuthLevel.FORBIDDEN:
            return handle_forbidden(canonical_tool, operation, raw_tool_name)

        # READ_AUTO — allow.
        if level is AuthLevel.READ_AUTO:
            return None  # Allow tool execution.

        # WRITE_NOTIFY — notify then allow.
        if level is AuthLevel.WRITE_NOTIFY:
            self._notify.send(
                canonical_tool=canonical_tool,
                operation=operation,
                level="write_notify",
                details=f"Executed by {raw_tool_name}",
            )
            return None  # Allow tool execution.

        # DESTRUCTIVE_APPROVAL — check/request approval.
        if level is AuthLevel.DESTRUCTIVE_APPROVAL:
            return self._handle_destructive(canonical_tool, operation, raw_tool_name)

        # Unknown level (shouldn't happen) — fail-closed.
        logger.error(
            "auth_overlay_unhandled_level",
            level=level.value if hasattr(level, "value") else str(level),
            tool=canonical_tool,
        )
        return {
            "action": "block",
            "reason": "AUTH_UNHANDLED_LEVEL",
            "message": "Unhandled auth level — blocked for safety.",
        }

    def _handle_destructive(
        self,
        canonical_tool: str,
        operation: str,
        raw_tool_name: str,
    ) -> dict[str, str] | None:
        """Handle a DESTRUCTIVE_APPROVAL operation.

        Checks whether an approval already exists.  If so, consumes it and
        allows execution.  Otherwise creates a pending approval request and
        blocks.
        """
        status = self._approval.check_approval(canonical_tool)

        if status == "approved":
            _ = self._approval.consume_approval(canonical_tool)
            logger.info(
                "auth_overlay_destructive_approved",
                tool=canonical_tool,
                operation=operation,
            )
            return None  # Allow tool execution.

        if status == "denied":
            logger.warning(
                "auth_overlay_destructive_denied",
                tool=canonical_tool,
                operation=operation,
            )
            return {
                "action": "block",
                "reason": f"AUTH_DENIED:{canonical_tool}:{operation}",
                "message": (
                    f"Destructive operation '{operation}' on "
                    f"'{canonical_tool}' was denied."
                ),
            }

        # No approval yet — create a pending request.
        _ = self._approval.request_approval(
            canonical_tool=canonical_tool,
            operation=operation,
            details=f"Requested by {raw_tool_name}",
            ttl=APPROVAL_TTL_SECONDS,
        )
        logger.warning(
            "auth_overlay_destructive_requested",
            tool=canonical_tool,
            operation=operation,
        )
        return {
            "action": "block",
            "reason": f"AUTH_APPROVAL_REQUIRED:{canonical_tool}:{operation}",
            "message": (
                f"Destructive operation '{operation}' on "
                f"'{canonical_tool}' requires approval. "
                f"Request sent — TTL {APPROVAL_TTL_SECONDS}s."
            ),
        }
