"""MCP Tools — Dynamic tool registry.

Provides ``register_all_tools`` which discovers and registers all tool
modules in this package to a FastMCP server instance.  Each tool module
must expose a ``register_tools(mcp: FastMCP) -> None`` entry-point.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Tool module discovery
#
# When a new tool module is added to this package, import it here and call
# its ``register_tools`` function.  Example:
#
#     from src.mcp.tools import my_tool
#     _TOOL_MODULES.append(my_tool)
# ---------------------------------------------------------------------------

from src.mcp.tools import (  # noqa: E402
    brave_search,
    context7,
    docker_tool,
    exa_search,
    fetch,
    filesystem,
    git_tool,
    github,
    grep_app,
    obscura_cdp,
    postgres_tool,
    redis_tool,
    sequential_thinking,
    shell_tool,
    time_tools,
    websearch,
)

_TOOL_MODULES: list[object] = [
    brave_search,
    context7,
    docker_tool,
    exa_search,
    fetch,
    filesystem,
    git_tool,
    github,
    grep_app,
    obscura_cdp,
    postgres_tool,
    redis_tool,
    sequential_thinking,
    shell_tool,
    time_tools,
    websearch,
]


def register_all_tools(server: FastMCP) -> int:
    """Discover and register every tool module in this package.

    Iterates through all known tool modules, calling each module's
    ``register_tools(server)`` entry-point.  Returns the count of
    tool modules registered.

    Args:
        server: The FastMCP server instance to register tools against.

    Returns:
        Number of tool modules successfully registered.
    """
    count = 0
    for module in _TOOL_MODULES:
        register_fn = getattr(module, "register_tools", None)
        if register_fn is None:
            logger.warning(
                "tool_module_missing_entry_point",
                module=type(module).__name__,
            )
            continue
        register_fn(server)
        count += 1

    logger.info("tools_registered", count=count, total=len(_TOOL_MODULES))
    return count