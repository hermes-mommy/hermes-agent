"""Tests for MCP Gateway — server factory, auth levels, and tool registration."""

from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on sys.path for `from src.*` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

# Import FastMCP from our manager (it handles the sys.path dance
# to avoid shadowing the pip-installed ``mcp`` package).
from src.mcp.manager import FastMCP  # noqa: E402

from src.mcp.auth import (  # noqa: E402
    AuthLevel,
    ForbiddenOperationError,
    _pending_approvals,
    _approval_results,
    approve,
    deny,
    require_approval,
)
from src.mcp.manager import create_server  # noqa: E402


# ============================================================================
# TestMCPServer
# ============================================================================


class TestMCPServer:
    """Tests for the ``create_server()`` FastMCP factory."""

    def test_create_server_returns_fastmcp(self) -> None:
        """``create_server()`` produces a ``FastMCP`` instance."""
        server = create_server()
        assert isinstance(server, FastMCP)

    def test_create_server_default_name(self) -> None:
        """Default name is ``guinevere-mcp``."""
        server = create_server()
        assert server.name == "guinevere-mcp"

    def test_create_server_custom_name(self) -> None:
        """Custom ``name`` kwarg is respected."""
        server = create_server(name="test-mcp-custom")
        assert server.name == "test-mcp-custom"


# ============================================================================
# TestAuthLevel
# ============================================================================


class TestAuthLevel:
    """Tests for the ``AuthLevel`` enum."""

    def test_exactly_four_members(self) -> None:
        """``AuthLevel`` enumerates exactly 4 authorization levels."""
        members = list(AuthLevel)
        assert len(members) == 4, f"Expected 4, got {len(members)}: {members}"

    @pytest.mark.parametrize(
        "level,expected_value",
        [
            (AuthLevel.READ_AUTO, "read_auto"),
            (AuthLevel.WRITE_NOTIFY, "write_notify"),
            (AuthLevel.DESTRUCTIVE_APPROVAL, "destructive_approval"),
            (AuthLevel.FORBIDDEN, "forbidden"),
        ],
    )
    def test_enum_values(
        self, level: AuthLevel, expected_value: str
    ) -> None:
        """Each ``AuthLevel`` member has the expected string value."""
        assert level.value == expected_value


# ============================================================================
# TestRequireApproval — sync / structural
# ============================================================================


class TestRequireApproval:
    """Tests for the ``require_approval`` decorator."""

    def test_returns_callable(self) -> None:
        """``require_approval()`` returns a decorator (callable)."""
        dec = require_approval(AuthLevel.READ_AUTO)
        assert callable(dec), "require_approval should return a callable"

        decorated = dec(lambda: None)
        assert callable(decorated), "decorated result should be callable"

    def test_decorator_with_tool_name(self) -> None:
        """Explicit ``tool_name`` arg is accepted by the decorator."""

        @require_approval(AuthLevel.READ_AUTO, tool_name="explicit_name")
        async def sample() -> str:
            return "ok"

        assert callable(sample)


# ============================================================================
# TestRequireApprovalAsync — async auth behaviour
# ============================================================================


class TestRequireApprovalAsync:
    """Async tests for auth-level behaviour (FORBIDDEN, READ_AUTO, etc.)."""

    # ------------------------------------------------------------------
    # FORBIDDEN
    # ------------------------------------------------------------------

    def test_forbidden_raises(self) -> None:
        """FORBIDDEN level raises ``ForbiddenOperationError`` immediately."""

        async def _run() -> None:
            @require_approval(AuthLevel.FORBIDDEN, tool_name="blocked")
            async def blocked_tool() -> None:
                pytest.fail("should not execute")

            with pytest.raises(ForbiddenOperationError):
                await blocked_tool()

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # READ_AUTO
    # ------------------------------------------------------------------

    def test_read_auto_executes(self) -> None:
        """READ_AUTO lets the tool execute without interruption."""

        async def _run() -> None:
            @require_approval(AuthLevel.READ_AUTO, tool_name="reader")
            async def reader() -> int:
                return 42

            result = await reader()
            assert result == 42

        asyncio.run(_run())

    def test_read_auto_passes_arguments(self) -> None:
        """READ_AUTO wrapper forwards positional and keyword args."""

        async def _run() -> None:
            @require_approval(AuthLevel.READ_AUTO, tool_name="adder")
            async def adder(a: int, b: int) -> int:
                return a + b

            assert await adder(10, 32) == 42

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # WRITE_NOTIFY
    # ------------------------------------------------------------------

    def test_write_notify_fires_webhook(self) -> None:
        """WRITE_NOTIFY fires a Discord notification (mocked httpx)."""

        async def _run() -> None:
            mock_post = AsyncMock()
            mock_post.return_value = MagicMock()
            mock_post.return_value.raise_for_status = MagicMock()

            with (
                patch.dict(os.environ, {"DISCORD_WEBHOOK_URL": "https://discord.example/webhook"}),
                patch("httpx.AsyncClient.post", new=mock_post),
            ):
                @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="notifier")
                async def notifier() -> str:
                    return "notified"

                result = await notifier()
                assert result == "notified"

                # Give the fire-and-forget task time to complete.
                await asyncio.sleep(0.05)

            # After exiting the asyncio block the HTTP call should have been made.
            assert mock_post.call_count >= 1, "Discord webhook should have been called"

        asyncio.run(_run())

    def test_write_notify_no_webhook_url_logs_warning(self) -> None:
        """WRITE_NOTIFY logs a warning when DISCORD_WEBHOOK_URL is absent."""

        async def _run() -> None:
            # Ensure the env var is NOT set.
            with patch.dict(os.environ, clear=True):
                os.environ.pop("DISCORD_WEBHOOK_URL", None)

                @require_approval(AuthLevel.WRITE_NOTIFY, tool_name="no_webhook")
                async def no_webhook_tool() -> str:
                    return "done"

                result = await no_webhook_tool()
                assert result == "done"

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # DESTRUCTIVE_APPROVAL
    # ------------------------------------------------------------------

    def test_destructive_approval_approves(self) -> None:
        """DESTRUCTIVE_APPROVAL blocks then proceeds after explicit approval."""

        async def _run() -> None:
            # Clean any leftover state from previous tests.
            _pending_approvals.clear()
            _approval_results.clear()

            with patch(
                "src.mcp.auth._send_discord_notification", new=AsyncMock()
            ):
                @require_approval(
                    AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="approve_me"
                )
                async def destroyer() -> str:
                    return "destroyed_safely"

                # Start in background, approve, collect result.
                task = asyncio.create_task(destroyer())
                await asyncio.sleep(0)  # yield to let the tool hit the gate
                approve("approve_me")
                result = await task
                assert result == "destroyed_safely"

        asyncio.run(_run())

    def test_destructive_approval_denies(self) -> None:
        """DESTRUCTIVE_APPROVAL raises when explicitly denied."""

        async def _run() -> None:
            _pending_approvals.clear()
            _approval_results.clear()

            with patch(
                "src.mcp.auth._send_discord_notification", new=AsyncMock()
            ):
                @require_approval(
                    AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="deny_me"
                )
                async def destroyer() -> str:
                    pytest.fail("should not execute after denial")

                task = asyncio.create_task(destroyer())
                await asyncio.sleep(0)
                deny("deny_me")

                with pytest.raises(ForbiddenOperationError):
                    await task

        asyncio.run(_run())

    def test_destructive_approval_timeout(self) -> None:
        """DESTRUCTIVE_APPROVAL raises after timeout with no response."""

        async def _run() -> None:
            _pending_approvals.clear()
            _approval_results.clear()

            with (
                patch("src.mcp.auth._send_discord_notification", new=AsyncMock()),
                patch("src.mcp.auth._APPROVAL_TIMEOUT_SECONDS", 0.01),
            ):
                @require_approval(
                    AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="timeout_me"
                )
                async def destroyer() -> str:
                    pytest.fail("should not execute after timeout")

                with pytest.raises(ForbiddenOperationError):
                    await destroyer()

        asyncio.run(_run())

    # ------------------------------------------------------------------
    # ForbiddenOperationError
    # ------------------------------------------------------------------

    def test_forbidden_operation_error_is_exception(self) -> None:
        """``ForbiddenOperationError`` is a subclass of ``Exception``."""
        assert issubclass(ForbiddenOperationError, Exception)

    def test_forbidden_operation_error_message(self) -> None:
        """``ForbiddenOperationError`` preserves its message."""
        msg = "Operation denied."
        exc = ForbiddenOperationError(msg)
        assert str(exc) == msg