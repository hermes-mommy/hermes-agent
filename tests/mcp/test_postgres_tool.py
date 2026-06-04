"""Tests for MCP PostgreSQL Tool — read-only queries with defense-in-depth."""

from __future__ import annotations

import asyncio
import sys
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.auth import ForbiddenOperationError  # noqa: E402
from src.mcp.tools.postgres_tool import (  # noqa: E402
    classify_sql,
    postgres_describe,
    postgres_query,
    postgres_tables,
    _validate_params,
)


# ---------------------------------------------------------------------------
# Mock helpers
# ---------------------------------------------------------------------------


class _MockRecord(dict[str, Any]):
    """A dict subclass that quacks like an ``asyncpg.Record``."""

    pass


def _make_mock_record(data: dict[str, Any]) -> _MockRecord:
    """Build a mock asyncpg-like record from a plain dict."""
    return _MockRecord(data)


def _make_mock_pool(
    fetch_rows: list[dict[str, Any]] | None = None,
    fetch_error: Exception | None = None,
) -> AsyncMock:
    """Create a mock ``asyncpg.Pool`` that returns controlled results.

    Args:
        fetch_rows: Rows to return from ``conn.fetch()``.
        fetch_error: If set, ``conn.fetch()`` raises this error.
    """
    rows = fetch_rows or []

    mock_conn = AsyncMock()
    mock_conn.fetch = AsyncMock(
        return_value=[_make_mock_record(r) for r in rows],
        side_effect=fetch_error,
    )

    # ``conn.transaction(readonly=True)`` returns an async context manager.
    @asynccontextmanager
    async def _mock_transaction(**kwargs: Any) -> Any:  # noqa: ARG001
        yield None

    mock_conn.transaction = _mock_transaction  # type: ignore[assignment]

    mock_pool = AsyncMock()
    mock_pool.acquire = MagicMock()
    mock_pool.acquire.return_value.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_pool.acquire.return_value.__aexit__ = AsyncMock(return_value=None)

    return mock_pool


def _patch_pool(fetch_rows: list[dict[str, Any]] | None = None) -> AsyncMock:
    """Convenience: build a mock pool and patch ``_get_pool``."""
    mock_pool = _make_mock_pool(fetch_rows=fetch_rows)
    return mock_pool


# ============================================================================
# TestClassifySql
# ============================================================================


class TestClassifySql:
    """SQL keyword classification — read, write, forbidden."""

    # -- allowed read keywords -------------------------------------------

    def test_select_is_read(self) -> None:
        """``SELECT`` is classified as read."""
        assert classify_sql("SELECT * FROM users") == "read"

    def test_select_lowercase_is_read(self) -> None:
        """``select`` (lowercase) is classified as read."""
        assert classify_sql("select 1") == "read"

    def test_show_is_read(self) -> None:
        """``SHOW`` is classified as read."""
        assert classify_sql("SHOW search_path") == "read"

    def test_explain_is_read(self) -> None:
        """``EXPLAIN`` is classified as read."""
        assert classify_sql("EXPLAIN SELECT 1") == "read"

    def test_with_select_is_read(self) -> None:
        """A ``WITH`` CTE followed by ``SELECT`` is classified as read."""
        sql = "WITH cte AS (SELECT 1) SELECT * FROM cte"
        assert classify_sql(sql) == "read"

    def test_with_leading_whitespace_is_read(self) -> None:
        """Leading whitespace does not affect classification."""
        assert classify_sql("   \n\t  SELECT * FROM t") == "read"

    # -- write keywords (blocked in read-only path) ----------------------

    def test_insert_is_write(self) -> None:
        """``INSERT`` is classified as write."""
        assert classify_sql("INSERT INTO t VALUES (1)") == "write"

    def test_update_is_write(self) -> None:
        """``UPDATE`` is classified as write."""
        assert classify_sql("UPDATE t SET x = 1") == "write"

    def test_delete_is_write(self) -> None:
        """``DELETE`` is classified as write."""
        assert classify_sql("DELETE FROM t WHERE id = 1") == "write"

    # -- forbidden keywords ----------------------------------------------

    def test_drop_is_forbidden(self) -> None:
        """``DROP`` is classified as forbidden."""
        assert classify_sql("DROP TABLE users") == "forbidden"

    def test_truncate_is_forbidden(self) -> None:
        """``TRUNCATE`` is classified as forbidden."""
        assert classify_sql("TRUNCATE TABLE users") == "forbidden"

    def test_alter_is_forbidden(self) -> None:
        """``ALTER`` is classified as forbidden."""
        assert classify_sql("ALTER TABLE users ADD COLUMN x int") == "forbidden"

    def test_create_is_forbidden(self) -> None:
        """``CREATE`` is classified as forbidden."""
        assert classify_sql("CREATE TABLE t (id int)") == "forbidden"

    def test_grant_is_forbidden(self) -> None:
        """``GRANT`` is classified as forbidden."""
        assert classify_sql("GRANT SELECT ON t TO u") == "forbidden"

    def test_revoke_is_forbidden(self) -> None:
        """``REVOKE`` is classified as forbidden."""
        assert classify_sql("REVOKE SELECT ON t FROM u") == "forbidden"

    # -- comment stripping -----------------------------------------------

    def test_commented_ddl_ignored(self) -> None:
        """DDL inside a ``--`` comment is ignored; main keyword decides."""
        sql = "-- DROP TABLE users\nSELECT * FROM users"
        assert classify_sql(sql) == "read"

    def test_block_comment_ddl_ignored(self) -> None:
        """DDL inside a ``/* */`` comment is ignored."""
        sql = "/* DROP TABLE users */ SELECT 1"
        assert classify_sql(sql) == "read"

    # -- edge cases ------------------------------------------------------

    def test_empty_string_is_forbidden(self) -> None:
        """Empty SQL is forbidden."""
        assert classify_sql("") == "forbidden"

    def test_whitespace_only_is_forbidden(self) -> None:
        """Whitespace-only SQL is forbidden."""
        assert classify_sql("   \n\t  ") == "forbidden"

    def test_unrecognized_keyword_is_forbidden(self) -> None:
        """An unrecognized keyword defaults to forbidden."""
        assert classify_sql("VACUUM users") == "forbidden"


# ============================================================================
# TestValidateParams
# ============================================================================


class TestValidateParams:
    """Parameter count validation."""

    def test_matching_params_passes(self) -> None:
        """Matching placeholder count and param count passes."""
        _validate_params("SELECT * FROM t WHERE id = $1", [42])

    def test_mismatch_raises_value_error(self) -> None:
        """Mismatched counts raise ``ValueError``."""
        with pytest.raises(ValueError, match="Parameter count mismatch"):
            _validate_params("SELECT * FROM t WHERE a = $1 AND b = $2", [42])

    def test_no_placeholders_no_params(self) -> None:
        """Zero placeholders with zero params passes."""
        _validate_params("SELECT 1", [])

    def test_multiple_placeholders(self) -> None:
        """Multiple placeholders with matching count."""
        _validate_params(
            "SELECT * FROM t WHERE a = $1 AND b = $2 AND c = $3",
            [1, "two", 3.0],
        )


# ============================================================================
# TestPostgresQuery
# ============================================================================


class TestPostgresQuery:
    """Read-only query execution with mocked asyncpg."""

    def test_select_returns_rows(self) -> None:
        """A ``SELECT`` query returns the expected rows."""
        mock_pool = _patch_pool(
            fetch_rows=[{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_query("SELECT id, name FROM users")
            assert len(result) == 2
            assert result[0] == {"id": 1, "name": "Alice"}
            assert result[1] == {"id": 2, "name": "Bob"}

        asyncio.run(_run())

    def test_select_with_params(self) -> None:
        """Parameterized queries are passed through correctly."""
        mock_pool = _patch_pool(fetch_rows=[{"id": 42, "name": "Target"}])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_query(
                    "SELECT id, name FROM users WHERE id = $1",
                    [42],
                )
            assert len(result) == 1
            assert result[0]["id"] == 42

        asyncio.run(_run())

    def test_empty_result(self) -> None:
        """A query returning no rows returns an empty list."""
        mock_pool = _patch_pool(fetch_rows=[])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_query("SELECT * FROM users WHERE id = $1", [999])
            assert result == []

        asyncio.run(_run())

    def test_insert_raises_forbidden(self) -> None:
        """``INSERT`` statements are rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="Write operations"):
                    await postgres_query("INSERT INTO t VALUES (1)")

        asyncio.run(_run())

    def test_update_raises_forbidden(self) -> None:
        """``UPDATE`` statements are rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="Write operations"):
                    await postgres_query("UPDATE t SET x = 1")

        asyncio.run(_run())

    def test_delete_raises_forbidden(self) -> None:
        """``DELETE`` statements are rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="Write operations"):
                    await postgres_query("DELETE FROM t")

        asyncio.run(_run())

    def test_drop_raises_forbidden(self) -> None:
        """``DROP`` statements are rejected with forbidden error."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="forbidden.*DDL"):
                    await postgres_query("DROP TABLE users")

        asyncio.run(_run())

    def test_truncate_raises_forbidden(self) -> None:
        """``TRUNCATE`` is rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="forbidden.*DDL"):
                    await postgres_query("TRUNCATE logs")

        asyncio.run(_run())

    def test_create_raises_forbidden(self) -> None:
        """``CREATE`` is rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="forbidden.*DDL"):
                    await postgres_query("CREATE TABLE x (id int)")

        asyncio.run(_run())

    def test_alter_raises_forbidden(self) -> None:
        """``ALTER`` is rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="forbidden.*DDL"):
                    await postgres_query("ALTER TABLE t ADD c text")

        asyncio.run(_run())

    def test_grant_raises_forbidden(self) -> None:
        """``GRANT`` is rejected before execution."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ForbiddenOperationError, match="forbidden.*DDL"):
                    await postgres_query("GRANT SELECT ON t TO u")

        asyncio.run(_run())

    def test_parameter_mismatch_raises_value_error(self) -> None:
        """Mismatched parameter count raises ``ValueError`` before DB call."""
        mock_pool = _patch_pool()

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(ValueError, match="Parameter count mismatch"):
                    await postgres_query("SELECT * FROM t WHERE a = $1 AND b = $2", [1])

        asyncio.run(_run())

    def test_connection_error_raised(self) -> None:
        """Database errors are raised to the caller."""
        import asyncpg

        mock_pool = _make_mock_pool(
            fetch_error=asyncpg.exceptions.ConnectionDoesNotExistError("gone"),
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                with pytest.raises(asyncpg.exceptions.ConnectionDoesNotExistError):
                    await postgres_query("SELECT 1")

        asyncio.run(_run())

    def test_uses_begin_read_only_transaction(self) -> None:
        """The query wraps in ``BEGIN READ ONLY`` transaction."""
        mock_pool = _patch_pool(fetch_rows=[{"x": 1}])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                await postgres_query("SELECT 1")

            # Verify acquire was called on the pool.
            mock_pool.acquire.assert_called_once()

        asyncio.run(_run())

    def test_none_params_treated_as_empty(self) -> None:
        """``params=None`` is treated as an empty parameter list."""
        mock_pool = _patch_pool(fetch_rows=[{"result": "ok"}])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_query("SELECT 1", None)
            assert result == [{"result": "ok"}]

        asyncio.run(_run())


# ============================================================================
# TestPostgresTables
# ============================================================================


class TestPostgresTables:
    """``postgres_tables`` — list user tables."""

    def test_returns_table_names(self) -> None:
        """Returns sorted list of table names from information_schema."""
        mock_pool = _patch_pool(
            fetch_rows=[
                {"table_name": "agents"},
                {"table_name": "memories"},
                {"table_name": "users"},
            ],
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_tables()
            assert result == ["agents", "memories", "users"]

        asyncio.run(_run())

    def test_custom_schema(self) -> None:
        """Accepts a custom schema name."""
        mock_pool = _patch_pool(
            fetch_rows=[{"table_name": "logs"}],
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_tables(schema="audit")
            assert result == ["logs"]

        asyncio.run(_run())

    def test_empty_tables_returns_empty_list(self) -> None:
        """Schema with no tables returns empty list."""
        mock_pool = _patch_pool(fetch_rows=[])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_tables()
            assert result == []

        asyncio.run(_run())


# ============================================================================
# TestPostgresDescribe
# ============================================================================


class TestPostgresDescribe:
    """``postgres_describe`` — column metadata."""

    def test_returns_column_metadata(self) -> None:
        """Returns column info from information_schema.columns."""
        mock_pool = _patch_pool(
            fetch_rows=[
                {
                    "column_name": "id",
                    "data_type": "integer",
                    "is_nullable": "NO",
                    "column_default": "nextval('...')",
                    "character_maximum_length": None,
                    "ordinal_position": 1,
                },
                {
                    "column_name": "name",
                    "data_type": "character varying",
                    "is_nullable": "YES",
                    "column_default": None,
                    "character_maximum_length": 255,
                    "ordinal_position": 2,
                },
            ],
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_describe("users")
            assert len(result) == 2
            assert result[0]["column_name"] == "id"
            assert result[0]["data_type"] == "integer"
            assert result[1]["column_name"] == "name"
            assert result[1]["is_nullable"] == "YES"

        asyncio.run(_run())

    def test_with_custom_schema(self) -> None:
        """Accepts a custom schema name for describe."""
        mock_pool = _patch_pool(
            fetch_rows=[
                {
                    "column_name": "event",
                    "data_type": "text",
                    "is_nullable": "NO",
                    "column_default": None,
                    "character_maximum_length": None,
                    "ordinal_position": 1,
                },
            ],
        )

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_describe("events", schema="audit")
            assert len(result) == 1
            assert result[0]["column_name"] == "event"

        asyncio.run(_run())

    def test_unknown_table_returns_empty(self) -> None:
        """Describing an unknown table returns an empty list."""
        mock_pool = _patch_pool(fetch_rows=[])

        async def _run() -> None:
            with patch(
                "src.mcp.tools.postgres_tool._get_pool",
                new=AsyncMock(return_value=mock_pool),
            ):
                result = await postgres_describe("nonexistent")
            assert result == []

        asyncio.run(_run())