"""Tests for the MCP Auth Matrix — verifies all 16 tools × auth levels.

Covers:
    - Completeness (all 16 tools registered).
    - Correctness (each operation → correct AuthLevel).
    - FORBIDDEN behaviour (immediate raise).
    - READ_AUTO behaviour (no notification, result returned).
    - WRITE_NOTIFY behaviour (Discord webhook dispatched, result returned).
    - DESTRUCTIVE_APPROVAL behaviour (blocks on approval, raises on deny/timeout).
"""

from __future__ import annotations

import asyncio
import os
from collections.abc import Generator
from typing import Any
from unittest.mock import ANY, AsyncMock, patch

import pytest

from src.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval
from src.mcp.auth_matrix import (
    ALL_TOOL_NAMES,
    AUTH_MATRIX,
    get_auth_level,
    verify_matrix_completeness,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_EXPECTED_TOOL_COUNT: int = 16

# Canonical operation→level pairs sampled from every tool in the matrix.
_SAMPLE_READ_AUTO: list[tuple[str, str]] = [
    ("brave_search", "*"),
    ("context7", "resolve"),
    ("context7", "query"),
    ("exa", "*"),
    ("fetch", "*"),
    ("grep_app", "*"),
    ("sequential_thinking", "*"),
    ("time", "*"),
    ("websearch", "*"),
    ("filesystem", "read"),
    ("filesystem", "list"),
    ("github", "read"),
    ("github", "get"),
    ("github", "search"),
    ("obscura_cdp", "navigate"),
    ("obscura_cdp", "read"),
    ("git", "log"),
    ("git", "diff"),
    ("git", "status"),
    ("postgres", "select"),
    ("postgres", "explain"),
    ("redis", "get"),
    ("redis", "lrange"),
    ("redis", "hget"),
    ("redis", "hgetall"),
    ("redis", "keys"),
    ("redis", "scan"),
    ("redis", "ttl"),
    ("redis", "exists"),
    ("redis", "type"),
    ("docker", "ps"),
    ("docker", "logs"),
    ("docker", "inspect"),
    ("docker", "images"),
]

_SAMPLE_WRITE_NOTIFY: list[tuple[str, str]] = [
    ("filesystem", "write"),
    ("github", "create_issue"),
    ("github", "create_pr"),
    ("obscura_cdp", "form_fill"),
    ("obscura_cdp", "click"),
    ("git", "commit"),
    ("git", "push"),
    ("redis", "set"),
    ("redis", "hset"),
    ("redis", "lpush"),
    ("redis", "rpush"),
    ("redis", "sadd"),
    ("redis", "setnx"),
    ("redis", "setex"),
    ("redis", "incr"),
    ("redis", "incrbyfloat"),
    ("docker", "start"),
    ("docker", "stop"),
    ("docker", "restart"),
]

_SAMPLE_DESTRUCTIVE: list[tuple[str, str]] = [
    ("filesystem", "delete"),
    ("github", "delete_repo"),
    ("obscura_cdp", "file_upload"),
    ("git", "force_push"),
    ("redis", "del"),
    ("redis", "expire"),
    ("redis", "persist"),
    ("redis", "rename"),
    ("shell", "exec"),
    ("docker", "rm"),
    ("docker", "rmi"),
]

_SAMPLE_FORBIDDEN: list[tuple[str, str]] = [
    ("git", "force_push_main"),
    ("postgres", "drop"),
    ("postgres", "truncate"),
    ("postgres", "insert"),
    ("postgres", "update"),
    ("postgres", "delete_row"),
    ("redis", "flushdb"),
    ("redis", "flushall"),
    ("redis", "config"),
    ("redis", "debug"),
    ("redis", "shutdown"),
    ("redis", "slaveof"),
    ("shell", "rm_rf_root"),
    ("shell", "sudo_rm_rf"),
    ("docker", "system_prune"),
    ("docker", "rm_all"),
]


# ---------------------------------------------------------------------------
# Helper — decorated async function for behavioural tests
# ---------------------------------------------------------------------------


def _make_test_func(
    tool_name: str,
    level: AuthLevel,
    expected_result: object = "ok",
) -> Any:  # noqa: ANN401 — decorator return type is dynamic
    """Create an async function decorated with ``@require_approval``.

    Returns the decorated callable for behavioural testing.
    """

    @require_approval(level, tool_name=tool_name)
    async def _inner(*args: object, **kwargs: object) -> object:
        return expected_result

    return _inner


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _clear_auth_state() -> Generator[None, None, None]:
    """Reset the in-process approval state before each test.

    Clears ``_pending_approvals`` and ``_approval_results`` in
    ``src.mcp.auth`` so that tests are fully isolated.
    """
    import src.mcp.auth as _auth_mod

    _auth_mod._pending_approvals.clear()
    _auth_mod._approval_results.clear()
    yield
    _auth_mod._pending_approvals.clear()
    _auth_mod._approval_results.clear()


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------


class TestAuthMatrix:
    """Comprehensive verification of the auth matrix and decorator behaviour."""

    # -- Completeness --------------------------------------------------------

    def test_matrix_has_all_16_tools(self) -> None:
        """All 16 expected tool names must be present in AUTH_MATRIX."""
        registered = frozenset(AUTH_MATRIX)
        expected = frozenset(ALL_TOOL_NAMES)
        assert registered == expected, (
            f"Missing: {sorted(expected - registered)}, "
            f"Extra: {sorted(registered - expected)}"
        )
        assert len(AUTH_MATRIX) == _EXPECTED_TOOL_COUNT

    def test_verify_matrix_completeness_returns_true(self) -> None:
        """verify_matrix_completeness() must return True for complete matrix."""
        assert verify_matrix_completeness() is True

    def test_auth_level_enum_has_exactly_4_values(self) -> None:
        """AuthLevel must have exactly 4 members."""
        members = set(AuthLevel)
        assert len(members) == 4
        assert AuthLevel.READ_AUTO in members
        assert AuthLevel.WRITE_NOTIFY in members
        assert AuthLevel.DESTRUCTIVE_APPROVAL in members
        assert AuthLevel.FORBIDDEN in members

    # -- Lookup --------------------------------------------------------------

    @pytest.mark.parametrize(
        "tool_name, operation",
        _SAMPLE_READ_AUTO,
        ids=[f"{t}::{o}" for t, o in _SAMPLE_READ_AUTO],
    )
    def test_get_auth_level_read_auto(
        self, tool_name: str, operation: str
    ) -> None:
        assert get_auth_level(tool_name, operation) is AuthLevel.READ_AUTO

    @pytest.mark.parametrize(
        "tool_name, operation",
        _SAMPLE_WRITE_NOTIFY,
        ids=[f"{t}::{o}" for t, o in _SAMPLE_WRITE_NOTIFY],
    )
    def test_get_auth_level_write_notify(
        self, tool_name: str, operation: str
    ) -> None:
        assert get_auth_level(tool_name, operation) is AuthLevel.WRITE_NOTIFY

    @pytest.mark.parametrize(
        "tool_name, operation",
        _SAMPLE_DESTRUCTIVE,
        ids=[f"{t}::{o}" for t, o in _SAMPLE_DESTRUCTIVE],
    )
    def test_get_auth_level_destructive_approval(
        self, tool_name: str, operation: str
    ) -> None:
        assert (
            get_auth_level(tool_name, operation)
            is AuthLevel.DESTRUCTIVE_APPROVAL
        )

    @pytest.mark.parametrize(
        "tool_name, operation",
        _SAMPLE_FORBIDDEN,
        ids=[f"{t}::{o}" for t, o in _SAMPLE_FORBIDDEN],
    )
    def test_get_auth_level_forbidden(
        self, tool_name: str, operation: str
    ) -> None:
        assert get_auth_level(tool_name, operation) is AuthLevel.FORBIDDEN

    def test_get_auth_level_unknown_tool_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown tool"):
            get_auth_level("nonexistent_tool", "read")

    def test_get_auth_level_unknown_operation_raises_key_error(self) -> None:
        with pytest.raises(KeyError, match="Unknown operation"):
            get_auth_level("filesystem", "nonexistent_operation")

    # -- Wildcard behaviour --------------------------------------------------

    def test_wildcard_tools_return_same_level_for_any_operation(self) -> None:
        """Tools with '*' key return the declared level for any operation."""
        wildcard_tools = [
            ("brave_search", AuthLevel.READ_AUTO),
            ("exa", AuthLevel.READ_AUTO),
            ("fetch", AuthLevel.READ_AUTO),
            ("grep_app", AuthLevel.READ_AUTO),
            ("sequential_thinking", AuthLevel.READ_AUTO),
            ("time", AuthLevel.READ_AUTO),
            ("websearch", AuthLevel.READ_AUTO),
        ]
        for tool, expected_level in wildcard_tools:
            # Any arbitrary operation string should resolve.
            assert get_auth_level(tool, "anything") is expected_level
            assert get_auth_level(tool, "random_operation") is expected_level

    # -- FORBIDDEN behaviour ------------------------------------------------

    @pytest.mark.asyncio()
    async def test_forbidden_raises_immediately(self) -> None:
        """Decorating with FORBIDDEN must raise before executing the func."""
        func = _make_test_func("test_tool", AuthLevel.FORBIDDEN)

        with pytest.raises(ForbiddenOperationError):
            await func()

    # -- READ_AUTO behaviour ------------------------------------------------

    @pytest.mark.asyncio()
    async def test_read_auto_executes_without_webhook(self) -> None:
        """READ_AUTO must execute the function and NOT fire a Discord webhook."""
        func = _make_test_func("test_tool", AuthLevel.READ_AUTO, expected_result=42)

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            result = await func()

        assert result == 42
        # Webhook must never be called for READ_AUTO.
        mock_post.assert_not_called()

    # -- WRITE_NOTIFY behaviour ---------------------------------------------

    @pytest.mark.asyncio()
    async def test_write_notify_executes_and_fires_webhook(self) -> None:
        """WRITE_NOTIFY must execute the function AND fire a Discord notification."""
        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.example.com/webhook"

        func = _make_test_func("write_test", AuthLevel.WRITE_NOTIFY, expected_result="done")

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value.raise_for_status = AsyncMock()
            result = await func()
            await asyncio.sleep(0)  # Yield to background notification task

        assert result == "done"
        # Webhook must have been called at least once.
        mock_post.assert_called()
        call_args = mock_post.call_args
        assert call_args is not None
        url_arg = call_args[0][0] if call_args[0] else ""
        assert url_arg == "https://discord.example.com/webhook"

    @pytest.mark.asyncio()
    async def test_write_notify_webhook_url_from_env(self) -> None:
        """Webhook URL must be read from DISCORD_WEBHOOK_URL env var."""
        custom_url = "https://custom.example.com/hook"
        os.environ["DISCORD_WEBHOOK_URL"] = custom_url

        func = _make_test_func("env_test", AuthLevel.WRITE_NOTIFY)

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value.raise_for_status = AsyncMock()
            await func()
            await asyncio.sleep(0)  # Yield to background notification task

        mock_post.assert_called_once_with(
            custom_url, json=ANY
        )

    # -- DESTRUCTIVE_APPROVAL behaviour ------------------------------------

    @pytest.mark.asyncio()
    async def test_destructive_approval_denied_raises(self) -> None:
        """DESTRUCTIVE_APPROVAL must raise ForbiddenOperationError when denied."""
        import src.mcp.auth as _auth_mod

        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.example.com/webhook"

        func = _make_test_func("destructive_deny", AuthLevel.DESTRUCTIVE_APPROVAL)

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value.raise_for_status = AsyncMock()

            # Start the task — it will block on approval.
            import asyncio
            task = asyncio.create_task(func())

            # Give the task a moment to reach the approval wait.
            await asyncio.sleep(0.05)

            # Deny the operation.
            _auth_mod.deny("destructive_deny")

            with pytest.raises(ForbiddenOperationError):
                await task

    @pytest.mark.asyncio()
    async def test_destructive_approval_approved_executes(self) -> None:
        """DESTRUCTIVE_APPROVAL must execute the function when approved."""
        import asyncio

        import src.mcp.auth as _auth_mod

        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.example.com/webhook"

        func = _make_test_func(
            "destructive_ok", AuthLevel.DESTRUCTIVE_APPROVAL, expected_result="executed"
        )

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value.raise_for_status = AsyncMock()

            task = asyncio.create_task(func())

            await asyncio.sleep(0.05)

            _auth_mod.approve("destructive_ok")

            result = await task

        assert result == "executed"

    @pytest.mark.asyncio()
    async def test_destructive_approval_blocks_until_approval(self) -> None:
        """DESTRUCTIVE_APPROVAL must block until an approval signal is received."""
        import asyncio

        import src.mcp.auth as _auth_mod

        os.environ["DISCORD_WEBHOOK_URL"] = "https://discord.example.com/webhook"

        func = _make_test_func(
            "blocking_test", AuthLevel.DESTRUCTIVE_APPROVAL, expected_result="approved_result"
        )

        with patch(
            "httpx.AsyncClient.post", new_callable=AsyncMock
        ) as mock_post:
            mock_post.return_value.raise_for_status = AsyncMock()

            task = asyncio.create_task(func())

            # Verify the task has not completed yet (still blocked).
            await asyncio.sleep(0.1)
            assert not task.done(), "Task completed before approval"

            _auth_mod.approve("blocking_test")

            result = await task

        assert result == "approved_result"
        assert task.done()

    # -- All 16 tools have at least one operation ---------------------------

    def test_every_tool_has_at_least_one_operation(self) -> None:
        """No tool in AUTH_MATRIX should have an empty operations dict."""
        for tool_name, ops in AUTH_MATRIX.items():
            assert len(ops) >= 1, f"Tool '{tool_name}' has zero operations"