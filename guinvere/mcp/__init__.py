"""MCP Module — Guinevere MCP gateway infrastructure.

Exports the core classes and functions needed to build, configure,
and operate the MCP server with authorization-gated tool execution.

Public API:
    ``create_server`` — FastMCP server factory.
    ``AuthLevel`` — Authorization level enum (4 levels).
    ``require_approval`` — Decorator for gating tool functions.
    ``ForbiddenOperationError`` — Raised when a forbidden operation is attempted.
"""

from __future__ import annotations

from guinvere.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval
from guinvere.mcp.manager import create_server

__all__: list[str] = [
    "AuthLevel",
    "create_server",
    "ForbiddenOperationError",
    "require_approval",
]