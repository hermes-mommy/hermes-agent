"""FastMCP Custom Manager — KEEP-7-only tool registration bridge.

Provides a FastMCP server that registers exactly the KEEP-7 custom tool
families through a documented stdio MCP server path. Unlike the full
``manager.py`` (which registers all 16 tool modules via
``guinvere.mcp.tools.register_all_tools``), this manager only imports and
registers the seven custom tool modules:

  - postgres_tool   (postgres_query, postgres_tables, postgres_describe)
  - redis_tool      (redis_get, redis_keys, redis_hgetall, redis_lrange,
                     redis_set, redis_hset, redis_del, redis_flushdb,
                     redis_flushall)
  - obscura_cdp     (obscura_navigate, obscura_get_markdown,
                     obscura_fill_form, obscura_click)
  - grep_app        (grep_app_search)
  - context7        (context7_resolve, context7_query)
  - sequential_thinking  (sequential_thinking)
  - time_tools      (time_current_time, time_convert_time,
                     time_days_in_month, time_relative_time,
                     time_get_timestamp, time_get_week_year)

This avoids importing ``filesystem``, ``brave_search``, ``docker_tool``,
``exa_search``, ``fetch``, ``git_tool``, ``github``, ``shell_tool``,
and ``websearch`` — preventing the FastMCP _config registration blocker
and keeping native tools off the custom bridge.
"""

from __future__ import annotations

import importlib
import logging
import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

# ---- Resolve the real mcp package (not our local guinvere/mcp) ----------
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
_SRC_ABS = Path(_SRC_DIR).resolve()
_SAVED_PATH: list[str] = list(sys.path)
sys.path = [p for p in sys.path if Path(p).resolve() != _SRC_ABS]
_fastmcp_module = importlib.import_module("mcp.server.fastmcp")
sys.path[:] = _SAVED_PATH
# --------------------------------------------------------------------

# ---------------------------------------------------------------------------
# KEEP-7 tool modules — only these seven are imported
# ----------------------------------------------------------------------------

from guinvere.mcp.tools import (  # noqa: E402
    context7,
    grep_app,
    obscura_cdp,
    postgres_tool,
    redis_tool,
    sequential_thinking,
    time_tools,
)


class FastMCPServer(Protocol):
    """Minimal FastMCP server protocol used by this module."""

    def run(self) -> None:
        """Run the FastMCP server."""


class FastMCPFactory(Protocol):
    """FastMCP constructor shape used by the custom manager."""

    def __call__(
        self,
        *,
        name: str,
        lifespan: Callable[[FastMCPServer], AbstractAsyncContextManager[None]],
    ) -> FastMCPServer: ...


_FAST_MCP = cast(FastMCPFactory, getattr(_fastmcp_module, "FastMCP"))

_KEEP_MODULES: tuple[ModuleType, ...] = (
    context7,
    grep_app,
    obscura_cdp,
    postgres_tool,
    redis_tool,
    sequential_thinking,
    time_tools,
)

KEEP_TOOL_FAMILIES: tuple[str, ...] = (
    "postgres",
    "redis",
    "obscura_cdp",
    "grep_app",
    "context7",
    "sequential_thinking",
    "time",
)

logger = logging.getLogger(__name__)


def _register_keep_tools(server: FastMCPServer) -> int:
    """Register only KEEP-7 tool modules with *server*.

    Iterates through the hardcoded ``_KEEP_MODULES`` tuple, calling each
    module's ``register_tools(server)`` entry-point. Returns the count of
    tool modules registered.
    """
    count = 0
    for module in _KEEP_MODULES:
        register_tools = cast(
            Callable[[FastMCPServer], None],
            getattr(module, "register_tools"),
        )
        register_tools(server)
        count += 1

    logger.info("Registered %s KEEP-7 tool modules", count)
    return count


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------


def _build_lifespan() -> Callable[[FastMCPServer], AbstractAsyncContextManager[None]]:
    """Build an async lifespan context manager for the FastMCP server."""

    @asynccontextmanager
    async def lifespan(server: FastMCPServer) -> AsyncGenerator[None, None]:
        """Handle server startup and graceful shutdown."""
        logger.info("FastMCP custom server starting")

        tool_count = _register_keep_tools(server)
        logger.info("FastMCP custom server ready; tools registered: %s", tool_count)

        yield

        logger.info("FastMCP custom server shutting down")

    return lifespan


# ---------------------------------------------------------------------------
# Server factory
# ---------------------------------------------------------------------------


def create_custom_server(name: str = "guinevere-fastmcp-custom") -> FastMCPServer:
    """Create and configure a KEEP-7-only FastMCP server instance.

    Args:
        name: Human-readable server name.
            Defaults to ``guinevere-fastmcp-custom``.

    Returns:
        A configured FastMCP-compatible server ready for ``.run()``.
    """
    logger.info("Creating FastMCP custom server: %s", name)

    server = _FAST_MCP(
        name=name,
        lifespan=_build_lifespan(),
    )

    logger.info("FastMCP custom server created: %s", name)
    return server


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    custom_server = create_custom_server()
    custom_server.run()
