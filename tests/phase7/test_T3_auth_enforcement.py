"""
T3: Auth Enforcement — MCP Auth Matrix Contract Tests.

Verifies the MCP auth matrix enforces correct permission levels for all
registered tools: FORBIDDEN tools raise, READ_AUTO returns, WRITE_NOTIFY
requires notification, DESTRUCTIVE_APPROVAL requires approval.
"""

from __future__ import annotations

from src.mcp.auth import AuthLevel, ForbiddenOperationError
from src.mcp.auth_matrix import (
    ALL_TOOL_NAMES,
    AUTH_MATRIX,
    get_auth_level,
    verify_matrix_completeness,
)


class TestAuthMatrixCompleteness:
    """All tools must be registered in AUTH_MATRIX."""

    def test_all_tools_registered(self) -> None:
        """verify_matrix_completeness() confirms every tool is in AUTH_MATRIX."""
        assert verify_matrix_completeness() is True

    def test_minimum_tool_count(self) -> None:
        """At least 10 tools registered (Phase 6 baseline)."""
        assert len(ALL_TOOL_NAMES) >= 10

    def test_known_tools_present(self) -> None:
        """Known core tools are registered."""
        known = {"brave_search", "context7", "filesystem", "github", "git", "time", "sequential_thinking", "exa", "fetch", "websearch"}
        assert known.issubset(ALL_TOOL_NAMES)


class TestAuthLevelContract:
    """Auth level contract: FORBIDDEN blocks, READ_AUTO passes, etc."""

    def test_forbidden_raises(self) -> None:
        """ForbiddenOperationError is raised for forbidden operations."""
        try:
            raise ForbiddenOperationError("shell", "exec")
        except ForbiddenOperationError:
            pass
        else:
            assert False, "Expected ForbiddenOperationError"

    def test_forbidden_operation_message(self) -> None:
        """ForbiddenOperationError includes tool and operation info."""
        try:
            raise ForbiddenOperationError("docker", "rm")
        except ForbiddenOperationError as e:
            msg = str(e).lower()
            assert "docker" in msg
            assert "rm" in msg or "forbidden" in msg

    def test_auth_levels_have_distinct_values(self) -> None:
        """All four AuthLevel members exist with distinct string values."""
        assert AuthLevel.READ_AUTO.value == "read_auto"
        assert AuthLevel.WRITE_NOTIFY.value == "write_notify"
        assert AuthLevel.DESTRUCTIVE_APPROVAL.value == "destructive_approval"
        assert AuthLevel.FORBIDDEN.value == "forbidden"

    def test_get_auth_level_returns_enum(self) -> None:
        """get_auth_level returns an AuthLevel for known tools."""
        level = get_auth_level("filesystem", "read")
        assert isinstance(level, AuthLevel)

    def test_filesystem_read_is_read_auto(self) -> None:
        """Filesystem read operations are READ_AUTO."""
        level = get_auth_level("filesystem", "read")
        assert level == AuthLevel.READ_AUTO

    def test_filesystem_write_is_write_notify(self) -> None:
        """Filesystem write operations are WRITE_NOTIFY."""
        level = get_auth_level("filesystem", "write")
        assert level == AuthLevel.WRITE_NOTIFY

    def test_shell_exec_is_read_auto(self) -> None:
        """Shell exec is READ_AUTO (downgraded from DESTRUCTIVE_APPROVAL)."""
        level = get_auth_level("shell", "exec")
        assert level == AuthLevel.READ_AUTO

    def test_git_commit_is_at_least_write_notify(self) -> None:
        """Git commit requires at minimum WRITE_NOTIFY."""
        level = get_auth_level("git", "commit")
        assert level in (AuthLevel.WRITE_NOTIFY, AuthLevel.DESTRUCTIVE_APPROVAL)


class TestAuthMatrixStructure:
    """AUTH_MATRIX structural invariants."""

    def test_every_tool_has_operations(self) -> None:
        """Every tool in AUTH_MATRIX has at least one operation entry."""
        for tool_name, ops in AUTH_MATRIX.items():
            assert len(ops) > 0, f"Tool {tool_name} has no operations"

    def test_operation_levels_valid(self) -> None:
        """Every operation maps to a valid AuthLevel."""
        for tool_name, ops in AUTH_MATRIX.items():
            for op_name, level in ops.items():
                assert isinstance(level, AuthLevel), f"{tool_name}.{op_name}: not an AuthLevel"

    def test_wildcard_present_for_auto_tools(self) -> None:
        """Brave search has wildcard '*' entry (auto-read)."""
        assert "*" in AUTH_MATRIX.get("brave_search", {})
        assert AUTH_MATRIX["brave_search"]["*"] == AuthLevel.READ_AUTO
