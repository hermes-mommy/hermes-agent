"""MCP PostgreSQL Tool — Read-only database queries with defense-in-depth.

Provides parameterized PostgreSQL query execution with 3-layer read-only
enforcement:

1. ``BEGIN READ ONLY`` transaction wrapper — server-side enforcement.
2. SQL keyword classification — rejects DDL / DML writes before execution.
3. Dedicated ``guinevere_readonly`` database role — SELECT-only grants.

Port: 5433 (Guinevere), not 5432 (Aizanta).
"""

from __future__ import annotations

import os
import re
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, Final

import structlog

if TYPE_CHECKING:
    import asyncpg

from guinvere.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# SQL classification — regex-based keyword extraction
# ---------------------------------------------------------------------------

ALLOWED_READ: Final[frozenset[str]] = frozenset({"SELECT", "SHOW", "EXPLAIN", "WITH"})
"""SQL keywords that are always permitted for read-only queries."""

REQUIRES_APPROVAL: Final[frozenset[str]] = frozenset({"INSERT", "UPDATE", "DELETE"})
"""SQL keywords that require DESTRUCTIVE_APPROVAL (blocked in read-only path)."""

FORBIDDEN: Final[frozenset[str]] = frozenset(
    {"DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"}  # FORBIDDEN keywords
)
"""SQL keywords that are unconditionally forbidden."""

# Regex to strip SQL comments (single-line ``--`` and block ``/* */``).
_COMMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:--[^\n]*)|(?:/\*[\s\S]*?\*/)",
)

# Matches the first substantive SQL keyword after comments and optional CTE preamble.
_MAIN_KEYWORD_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(SELECT|INSERT|UPDATE|DELETE|SHOW|EXPLAIN|DROP|TRUNCATE|ALTER|CREATE|GRANT|REVOKE|WITH)\b",  # SQL keyword set
    re.IGNORECASE,
)


def classify_sql(sql: str) -> str:
    """Classify a SQL string as ``"read"``, ``"write"``, or ``"forbidden"``.

    Strips comments, then locates the first substantive keyword (skipping
    past CTE ``WITH`` clauses by searching for any known keyword).  The
    result drives auth-level selection and execution gating.

    Returns:
        ``"read"`` — SELECT / SHOW / EXPLAIN / WITH.
        ``"write"`` — INSERT / UPDATE / DELETE.
        ``"forbidden"`` — DROP / TRUNCATE / ALTER / CREATE / GRANT / REVOKE
        or unrecognized input.
    """
    # Strip comments to avoid classifying commented-out DDL as live code.
    cleaned = _COMMENT_RE.sub(" ", sql)
    cleaned = cleaned.strip()

    if not cleaned:
        return "forbidden"

    match = _MAIN_KEYWORD_RE.search(cleaned)
    if match is None:
        return "forbidden"

    keyword = match.group(1).upper()

    if keyword in ALLOWED_READ:
        return "read"
    if keyword in REQUIRES_APPROVAL:
        return "write"
    return "forbidden"


# ---------------------------------------------------------------------------
# Connection helpers — lazy pool initialisation
# ---------------------------------------------------------------------------

_DEFAULT_HOST: Final[str] = "localhost"
_DEFAULT_PORT: Final[int] = 5433
_DEFAULT_DB: Final[str] = "guinevere"
_DEFAULT_READONLY_USER: Final[str] = "guinevere_readonly"
_QUERY_TIMEOUT_SECONDS: Final[float] = 30.0

_pool: asyncpg.Pool | None = None


async def _get_pool() -> asyncpg.Pool:
    """Return (or lazily create) the connection pool.

    The pool authenticates as ``POSTGRES_READONLY_USER`` (defaults to
    ``guinevere_readonly``) so that layer-3 database grants are enforced
    even if layers 1 and 2 are bypassed.
    """
    import asyncpg

    global _pool

    if _pool is not None:
        return _pool

    host = os.environ.get("POSTGRES_HOST", _DEFAULT_HOST)
    port = _DEFAULT_PORT  # 5433 — hardcoded, no env override (Aizanta isolation)
    db = _DEFAULT_DB  # "guinevere" — hardcoded, no env override
    user = _DEFAULT_READONLY_USER  # "guinevere_readonly" — hardcoded, no env override
    password = os.environ.get("POSTGRES_PASSWORD", "")

    _pool = await asyncpg.create_pool(
        host=host,
        port=port,
        user=user,
        password=password,
        database=db,
        min_size=1,
        max_size=5,
        command_timeout=_QUERY_TIMEOUT_SECONDS,
    )
    logger.info(
        "postgres_pool_created",
        host=host,
        port=port,
        database=db,
        pool_user=user,
    )
    return _pool


# ---------------------------------------------------------------------------
# Parameter validation
# ---------------------------------------------------------------------------

_PARAM_PLACEHOLDER_RE: Final[re.Pattern[str]] = re.compile(r"\$\d+")


def _validate_params(sql: str, params: Sequence[Any]) -> None:
    """Verify that *params* count matches ``$N`` placeholders in *sql*.

    Raises ``ValueError`` on mismatch to catch silent parameter omission.
    """
    placeholders = _PARAM_PLACEHOLDER_RE.findall(sql)
    if len(placeholders) != len(params):
        raise ValueError(
            f"Parameter count mismatch: SQL has {len(placeholders)} "
            f"placeholder(s), but {len(params)} value(s) were provided."
        )


# ---------------------------------------------------------------------------
# Public query functions
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="postgres_query")
async def postgres_query(
    sql: str,
    params: Sequence[Any] | None = None,
) -> list[dict[str, Any]]:
    """Execute a **read-only** parameterized SQL query.

    Args:
        sql: SQL statement — ``SELECT``, ``SHOW``, ``EXPLAIN``, or read-only
            ``WITH`` only.  Use ``$1``, ``$2``, … placeholders for parameters.
        params: Positional parameter values matching the placeholders in *sql*.

    Returns:
        List of row dicts (column name → value).

    Raises:
        ForbiddenOperationError: If *sql* is classified as write or forbidden.
        ValueError: If parameter count does not match placeholder count.
        asyncpg.PostgresError: On database-level errors.
    """
    # --- Layer 2: classify before any connection is opened ----------------
    classification = classify_sql(sql)
    if classification == "forbidden":
        raise ForbiddenOperationError(
            f"SQL statement is forbidden (DDL / DCL detected). "
            f"Statement: {sql[:120]}"
        )
    if classification == "write":
        raise ForbiddenOperationError(
            f"Write operations (INSERT/UPDATE/DELETE) are not permitted "
            f"via the read-only query tool. Statement: {sql[:120]}"
        )

    import asyncpg

    params = params or []

    # Validate parameter count matches placeholders.
    _validate_params(sql, params)

    pool = await _get_pool()

    try:
        async with pool.acquire() as conn:
            # --- Layer 1: BEGIN READ ONLY transaction --------------------
            async with conn.transaction(readonly=True):
                rows: list[asyncpg.Record] = await conn.fetch(sql, *params)
    except asyncpg.exceptions.ConnectionDoesNotExistError as exc:
        logger.error(
            "postgres_connection_lost",
            error=str(exc),
        )
        raise
    except asyncpg.PostgresError as exc:
        logger.error(
            "postgres_query_error",
            error=str(exc),
            sql_preview=sql[:120],
        )
        raise

    result = [dict(row) for row in rows]
    logger.info(
        "postgres_query_success",
        row_count=len(result),
        sql_preview=sql[:120],
    )
    return result


@require_approval(AuthLevel.READ_AUTO, tool_name="postgres_tables")
async def postgres_tables(schema: str = "public") -> list[str]:
    """List all user tables in *schema*.

    Args:
        schema: Schema name (default ``"public"``).

    Returns:
        Sorted list of table names.
    """
    sql = """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = $1
          AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """
    rows = await postgres_query(sql, [schema])
    return [str(row["table_name"]) for row in rows]


@require_approval(AuthLevel.READ_AUTO, tool_name="postgres_describe")
async def postgres_describe(
    table: str,
    schema: str = "public",
) -> list[dict[str, Any]]:
    """Describe the columns of *table*.

    Args:
        table: Table name.
        schema: Schema name (default ``"public"``).

    Returns:
        List of column metadata dicts (``column_name``, ``data_type``,
        ``is_nullable``, ``column_default``, ``character_maximum_length``,
        ``ordinal_position``).
    """
    sql = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default,
            character_maximum_length,
            ordinal_position
        FROM information_schema.columns
        WHERE table_schema = $1
          AND table_name = $2
        ORDER BY ordinal_position
    """
    return await postgres_query(sql, [schema, table])


# ---------------------------------------------------------------------------
# Write / delete query functions (S3 — auth-unlocked)
# ---------------------------------------------------------------------------

_EXECUTE_ALLOWED_KEYWORDS: Final[frozenset[str]] = frozenset({"INSERT", "UPDATE"})
"""SQL keywords permitted for ``postgres_execute``."""

_DELETE_ALLOWED_KEYWORDS: Final[frozenset[str]] = frozenset({"DELETE"})
"""SQL keywords permitted for ``postgres_delete``."""


def _classify_write_keyword(sql: str) -> str:
    """Return the first substantive SQL keyword after stripping comments.

    Used by ``postgres_execute`` / ``postgres_delete`` to validate that
    only the expected DML keyword class is present.

    Returns:
        The uppercase first keyword, or ``""`` if none found.
    """
    cleaned = _COMMENT_RE.sub(" ", sql).strip()
    if not cleaned:
        return ""
    match = _MAIN_KEYWORD_RE.search(cleaned)
    if match is None:
        return ""
    return match.group(1).upper()


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="postgres_execute")
async def postgres_execute(
    sql: str,
    params: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Execute a **write** parameterized SQL statement (INSERT / UPDATE).

    This function is separate from ``postgres_query`` so the read-only
    guarantee on the primary query tool is preserved.

    Args:
        sql: SQL statement — ``INSERT`` or ``UPDATE`` only.
            ``$1``, ``$2``, … placeholders for parameters.
        params: Positional parameter values matching the placeholders.

    Returns:
        Dict with ``"affected_rows"`` (int) and ``"status"`` (str).

    Raises:
        ForbiddenOperationError: If *sql* is classified as forbidden
            (DROP / TRUNCATE / ALTER / CREATE / GRANT / REVOKE) or
            if the keyword is not INSERT or UPDATE.
        ValueError: If parameter count does not match placeholder count.
        asyncpg.PostgresError: On database-level errors.
    """
    import asyncpg

    # Layer 2: classify and validate keyword.
    classification = classify_sql(sql)
    if classification == "forbidden":
        raise ForbiddenOperationError(
            f"SQL statement is forbidden (DDL / DCL detected). "
            f"Statement: {sql[:120]}"
        )
    if classification == "read":
        raise ForbiddenOperationError(
            f"Read-only statements (SELECT/SHOW/EXPLAIN) must use "
            f"postgres_query, not postgres_execute. Statement: {sql[:120]}"
        )

    first_keyword = _classify_write_keyword(sql)
    if first_keyword not in _EXECUTE_ALLOWED_KEYWORDS:
        raise ForbiddenOperationError(
            f"postgres_execute only permits INSERT or UPDATE. "
            f"Detected keyword: {first_keyword or 'unknown'}. "
            f"Statement: {sql[:120]}"
        )

    params = params or []
    _validate_params(sql, params)

    pool = await _get_pool()

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(sql, *params)
    except asyncpg.exceptions.ConnectionDoesNotExistError as exc:
        logger.error("postgres_connection_lost", error=str(exc))
        raise
    except asyncpg.PostgresError as exc:
        logger.error(
            "postgres_execute_error",
            error=str(exc),
            sql_preview=sql[:120],
        )
        raise

    # asyncpg returns status string like "UPDATE 3" or "INSERT 0 1"
    affected = _parse_affected_rows(result)
    logger.info(
        "postgres_execute_success",
        affected_rows=affected,
        status=result,
        sql_preview=sql[:120],
    )
    return {"affected_rows": affected, "status": result}


@require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="postgres_delete")
async def postgres_delete(
    sql: str,
    params: Sequence[Any] | None = None,
) -> dict[str, Any]:
    """Execute a **DELETE** parameterized SQL statement.

    Separate from ``postgres_execute`` because DELETE is destructive
    and requires ``DESTRUCTIVE_APPROVAL`` rather than ``WRITE_NOTIFY``.

    Args:
        sql: SQL statement — ``DELETE`` only.
            ``$1``, ``$2``, … placeholders for parameters.
        params: Positional parameter values matching the placeholders.

    Returns:
        Dict with ``"affected_rows"`` (int) and ``"status"`` (str).

    Raises:
        ForbiddenOperationError: If *sql* is classified as forbidden
            or if the keyword is not DELETE.
        ValueError: If parameter count does not match placeholder count.
        asyncpg.PostgresError: On database-level errors.
    """
    import asyncpg

    # Layer 2: classify and validate keyword.
    classification = classify_sql(sql)
    if classification == "forbidden":
        raise ForbiddenOperationError(
            f"SQL statement is forbidden (DDL / DCL detected). "
            f"Statement: {sql[:120]}"
        )
    if classification == "read":
        raise ForbiddenOperationError(
            f"Read-only statements (SELECT/SHOW/EXPLAIN) must use "
            f"postgres_query, not postgres_delete. Statement: {sql[:120]}"
        )

    first_keyword = _classify_write_keyword(sql)
    if first_keyword not in _DELETE_ALLOWED_KEYWORDS:
        raise ForbiddenOperationError(
            f"postgres_delete only permits DELETE. "
            f"Detected keyword: {first_keyword or 'unknown'}. "
            f"Use postgres_execute for INSERT/UPDATE. "
            f"Statement: {sql[:120]}"
        )

    params = params or []
    _validate_params(sql, params)

    pool = await _get_pool()

    try:
        async with pool.acquire() as conn:
            async with conn.transaction():
                result = await conn.execute(sql, *params)
    except asyncpg.exceptions.ConnectionDoesNotExistError as exc:
        logger.error("postgres_connection_lost", error=str(exc))
        raise
    except asyncpg.PostgresError as exc:
        logger.error(
            "postgres_delete_error",
            error=str(exc),
            sql_preview=sql[:120],
        )
        raise

    affected = _parse_affected_rows(result)
    logger.info(
        "postgres_delete_success",
        affected_rows=affected,
        status=result,
        sql_preview=sql[:120],
    )
    return {"affected_rows": affected, "status": result}


def _parse_affected_rows(status: str) -> int:
    """Parse affected row count from asyncpg status string.

    asyncpg returns strings like ``"UPDATE 3"``, ``"INSERT 0 1"``,
    or ``"DELETE 5"``.  Extract the trailing integer.
    """
    parts = status.strip().split()
    if not parts:
        return 0
    try:
        return int(parts[-1])
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register the PostgreSQL tool suite with the FastMCP server."""
    mcp.tool(name="postgres_query")(postgres_query)
    mcp.tool(name="postgres_tables")(postgres_tables)
    mcp.tool(name="postgres_describe")(postgres_describe)
    mcp.tool(name="postgres_execute")(postgres_execute)
    mcp.tool(name="postgres_delete")(postgres_delete)