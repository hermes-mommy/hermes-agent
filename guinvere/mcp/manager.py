"""MCP Manager — FastMCP server factory and entry-point.

Provides ``create_server()`` which builds and configures a FastMCP
server, registers all tool modules via the dynamic registry, and
returns the ready-to-run server instance.

Note: the local ``guinvere/mcp`` package shadows the pip-installed ``mcp``
package when ``guinvere/`` is on ``sys.path`` (e.g. via pytest's
``pythonpath`` config).  We temporarily prune ``guinvere/`` from the path
while importing ``FastMCP`` from the third-party ``mcp`` library.
"""

from __future__ import annotations

import sys
from collections.abc import AsyncGenerator, Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from pathlib import Path

import structlog

# ---- Resolve the real mcp package (not our local guinvere/mcp) ----------
_SRC_DIR = str(Path(__file__).resolve().parent.parent)
_SRC_ABS = Path(_SRC_DIR).resolve()
_SAVED_PATH: list[str] = list(sys.path)
# Remove any path entry that matches the guinvere/ directory so that the
# following import resolves to the pip-installed ``mcp`` package.
sys.path = [p for p in sys.path if Path(p).resolve() != _SRC_ABS]

from mcp.server.fastmcp import FastMCP  # noqa: E402

sys.path[:] = _SAVED_PATH
# --------------------------------------------------------------------

from guinvere.mcp.tools import register_all_tools  # noqa: E402

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# FastMCP server factory
# ---------------------------------------------------------------------------


def _build_lifespan() -> Callable[[FastMCP], AbstractAsyncContextManager[None]]:
    """Build an async lifespan context-manager for the FastMCP server."""

    @asynccontextmanager
    async def lifespan(server: FastMCP) -> AsyncGenerator[None, None]:  # noqa: ARG001
        """Handle server startup and graceful shutdown."""
        logger.info("mcp_server_starting")

        tool_count = register_all_tools(server)
        logger.info("mcp_server_ready", tools_registered=tool_count)

        # RG-008: Verify auth matrix completeness at startup
        try:
            from guinvere.mcp.auth_matrix import verify_matrix_completeness

            if not verify_matrix_completeness():
                logger.warning("auth_matrix_incomplete")
            else:
                logger.info("auth_matrix_verified")
        except ImportError as matrix_err:
            logger.warning(
                "auth_matrix_verification_failed",
                error=str(matrix_err),
            )

        yield

        logger.info("mcp_server_shutting_down")

    return lifespan


def create_server(name: str = "guinevere-mcp") -> FastMCP:
    """Create and configure a FastMCP server instance.

    Args:
        name: Human-readable server name.  Defaults to ``guinevere-mcp``.

    Returns:
        A configured ``FastMCP`` instance ready for ``.run()``.
    """
    logger.info("creating_mcp_server", name=name)

    server = FastMCP(
        name=name,
        host="127.0.0.1",
        port=8090,
        lifespan=_build_lifespan(),
    )

    logger.info("mcp_server_created", name=name, host="127.0.0.1", port=8090)
    return server


# ---------------------------------------------------------------------------
# Entry-point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    server = create_server()
    server.run(transport="streamable-http")
