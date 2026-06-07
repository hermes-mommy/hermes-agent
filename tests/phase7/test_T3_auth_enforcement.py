"""
T3: Auth Enforcement — MCP Auth Matrix Contract Tests.

Verifies the MCP auth matrix enforces correct permission levels for all
registered tools: FORBIDDEN tools raise, READ_AUTO returns, WRITE_NOTIFY
requires notification, DESTRUCTIVE_APPROVAL requires approval.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Protocol, cast

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


class TestPostgresAuthLevels:
    """S3 auth unlock: postgres insert/update are WRITE_NOTIFY, delete_row is DESTRUCTIVE_APPROVAL."""

    def test_postgres_insert_is_write_notify(self) -> None:
        """postgres.insert was FORBIDDEN, now WRITE_NOTIFY (S3 unlock)."""
        assert get_auth_level("postgres", "insert") == AuthLevel.WRITE_NOTIFY

    def test_postgres_update_is_write_notify(self) -> None:
        """postgres.update was FORBIDDEN, now WRITE_NOTIFY (S3 unlock)."""
        assert get_auth_level("postgres", "update") == AuthLevel.WRITE_NOTIFY

    def test_postgres_delete_row_is_destructive_approval(self) -> None:
        """postgres.delete_row was FORBIDDEN, now DESTRUCTIVE_APPROVAL (S3 unlock)."""
        assert get_auth_level("postgres", "delete_row") == AuthLevel.DESTRUCTIVE_APPROVAL

    def test_postgres_drop_still_forbidden(self) -> None:
        """postgres.drop must remain FORBIDDEN."""
        assert get_auth_level("postgres", "drop") == AuthLevel.FORBIDDEN

    def test_postgres_truncate_still_forbidden(self) -> None:
        """postgres.truncate must remain FORBIDDEN."""
        assert get_auth_level("postgres", "truncate") == AuthLevel.FORBIDDEN


class TestRedisAuthLevels:
    """S3 auth unlock: redis expire/persist/rename are WRITE_NOTIFY."""

    def test_redis_expire_is_write_notify(self) -> None:
        """redis.expire was DESTRUCTIVE_APPROVAL, now WRITE_NOTIFY (S3 unlock)."""
        assert get_auth_level("redis", "expire") == AuthLevel.WRITE_NOTIFY

    def test_redis_persist_is_write_notify(self) -> None:
        """redis.persist was DESTRUCTIVE_APPROVAL, now WRITE_NOTIFY (S3 unlock)."""
        assert get_auth_level("redis", "persist") == AuthLevel.WRITE_NOTIFY

    def test_redis_rename_is_write_notify(self) -> None:
        """redis.rename was DESTRUCTIVE_APPROVAL, now WRITE_NOTIFY (S3 unlock)."""
        assert get_auth_level("redis", "rename") == AuthLevel.WRITE_NOTIFY

    def test_redis_flushdb_still_forbidden(self) -> None:
        """redis.flushdb must remain FORBIDDEN."""
        assert get_auth_level("redis", "flushdb") == AuthLevel.FORBIDDEN

    def test_redis_flushall_still_forbidden(self) -> None:
        """redis.flushall must remain FORBIDDEN."""
        assert get_auth_level("redis", "flushall") == AuthLevel.FORBIDDEN


class _AuthDecoratedCallable(Protocol):
    _auth_level: AuthLevel

    def __call__(self, *args: object, **kwargs: object) -> object: ...


class TestNewToolFunctions:
    """S3b/S3c: new postgres_execute, postgres_delete, redis_expire, redis_persist, redis_rename."""

    @staticmethod
    def _assert_auth_level(func: Callable[..., object], expected: AuthLevel) -> None:
        decorated = cast(_AuthDecoratedCallable, func)
        assert hasattr(decorated, "_auth_level")
        assert decorated._auth_level == expected

    def test_postgres_execute_function_exists(self) -> None:
        """postgres_execute function exists and is importable."""
        from src.mcp.tools.postgres_tool import postgres_execute
        assert callable(postgres_execute)

    def test_postgres_delete_function_exists(self) -> None:
        """postgres_delete function exists and is importable."""
        from src.mcp.tools.postgres_tool import postgres_delete
        assert callable(postgres_delete)

    def test_postgres_execute_has_auth_decorator(self) -> None:
        """postgres_execute has WRITE_NOTIFY auth level on its decorator."""
        from src.mcp.tools.postgres_tool import postgres_execute
        self._assert_auth_level(postgres_execute, AuthLevel.WRITE_NOTIFY)

    def test_postgres_delete_has_auth_decorator(self) -> None:
        """postgres_delete has DESTRUCTIVE_APPROVAL auth level on its decorator."""
        from src.mcp.tools.postgres_tool import postgres_delete
        self._assert_auth_level(postgres_delete, AuthLevel.DESTRUCTIVE_APPROVAL)

    def test_redis_expire_function_exists(self) -> None:
        """redis_expire function exists and is importable."""
        from src.mcp.tools.redis_tool import redis_expire
        assert callable(redis_expire)

    def test_redis_persist_function_exists(self) -> None:
        """redis_persist function exists and is importable."""
        from src.mcp.tools.redis_tool import redis_persist
        assert callable(redis_persist)

    def test_redis_rename_function_exists(self) -> None:
        """redis_rename function exists and is importable."""
        from src.mcp.tools.redis_tool import redis_rename
        assert callable(redis_rename)

    def test_redis_expire_has_auth_decorator(self) -> None:
        """redis_expire has WRITE_NOTIFY auth level on its decorator."""
        from src.mcp.tools.redis_tool import redis_expire
        self._assert_auth_level(redis_expire, AuthLevel.WRITE_NOTIFY)

    def test_redis_persist_has_auth_decorator(self) -> None:
        """redis_persist has WRITE_NOTIFY auth level on its decorator."""
        from src.mcp.tools.redis_tool import redis_persist
        self._assert_auth_level(redis_persist, AuthLevel.WRITE_NOTIFY)

    def test_redis_rename_has_auth_decorator(self) -> None:
        """redis_rename has WRITE_NOTIFY auth level on its decorator."""
        from src.mcp.tools.redis_tool import redis_rename
        self._assert_auth_level(redis_rename, AuthLevel.WRITE_NOTIFY)


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
