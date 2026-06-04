"""MCP Redis Tool — Async Redis operations with command-level auth classification.

Provides ``register_tools(mcp: FastMCP) -> None`` to register Redis
read, write, destructive, and forbidden operations on the MCP server,
each gated with the appropriate ``AuthLevel``.

Key design:
- Driver: ``redis.asyncio`` (redis-py async interface)
- Port: 6380 (non-standard, project config)
- Auth: ``guinevere_core`` username, password from ``REDIS_PASSWORD`` env
- DB5 is the default database for this tool (cost tracking namespace)

DB allocation map:
    DB0: Session cache
    DB1: Memory recall
    DB2: Surveillance buffer
    DB3: Agent state
    DB4: Discord state
    DB5: Cost tracking (default for this tool)
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

import redis.asyncio as aioredis
import structlog

from src.mcp.auth import AuthLevel, ForbiddenOperationError, require_approval

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

logger = structlog.get_logger()

# ---------------------------------------------------------------------------
# Redis connection defaults
# ---------------------------------------------------------------------------

_REDIS_HOST = "localhost"
_REDIS_PORT = 6380
_REDIS_USERNAME = "guinevere_core"
_DEFAULT_DB = 5

# ---------------------------------------------------------------------------
# DB allocation map (module-level constant)
# ---------------------------------------------------------------------------

DB_ALLOCATION: dict[int, str] = {
    0: "Session cache",
    1: "Memory recall",
    2: "Surveillance buffer",
    3: "Agent state",
    4: "Discord state",
    5: "Cost tracking",
}

# ---------------------------------------------------------------------------
# Command classification (module-level constant)
# ---------------------------------------------------------------------------

READ_COMMANDS: set[str] = {
    "GET",
    "LRANGE",
    "HGET",
    "HGETALL",
    "KEYS",
    "SCAN",
    "TTL",
    "EXISTS",
    "TYPE",
}

WRITE_COMMANDS: set[str] = {
    "SET",
    "HSET",
    "LPUSH",
    "RPUSH",
    "SADD",
    "SETNX",
    "SETEX",
    "INCR",
    "INCRBYFLOAT",
}

DESTRUCTIVE_COMMANDS: set[str] = {
    "DEL",
    "EXPIRE",
    "PERSIST",
    "RENAME",
}

FORBIDDEN_COMMANDS: set[str] = {
    "FLUSHALL",
    "FLUSHDB",
    "CONFIG",
    "DEBUG",
    "SHUTDOWN",
    "SLAVEOF",
}

COMMAND_CLASSIFICATION: dict[str, str] = {
    **{cmd: "read" for cmd in READ_COMMANDS},
    **{cmd: "write" for cmd in WRITE_COMMANDS},
    **{cmd: "destructive" for cmd in DESTRUCTIVE_COMMANDS},
    **{cmd: "forbidden" for cmd in FORBIDDEN_COMMANDS},
}

# ---------------------------------------------------------------------------
# Connection factory
# ---------------------------------------------------------------------------


def _connect(db: int = _DEFAULT_DB) -> aioredis.Redis:
    """Create a ``redis.asyncio.Redis`` client with project defaults.

    Args:
        db: Redis database number (default 5 — cost tracking).

    Returns:
        A configured async Redis client.
    """
    password = os.environ.get("REDIS_PASSWORD", "")

    logger.debug(
        "redis_connect",
        host=_REDIS_HOST,
        port=_REDIS_PORT,
        db=db,
    )

    return aioredis.Redis(
        host=_REDIS_HOST,
        port=_REDIS_PORT,
        db=db,
        username=_REDIS_USERNAME,
        password=password,
        decode_responses=True,
    )


# ---------------------------------------------------------------------------
# Tool implementations — READ_AUTO
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.READ_AUTO, tool_name="redis_get")
async def redis_get(key: str, db: int = _DEFAULT_DB) -> str | None:
    """Get a value by key. Auth: READ_AUTO.

    Args:
        key: The Redis key to retrieve.
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        The value as a string, or ``None`` if the key does not exist.
    """
    client = _connect(db)
    try:
        value: str | None = await client.get(key)
        logger.debug("redis_get", key=key, db=db, hit=value is not None)
        return value
    finally:
        await client.aclose()


@require_approval(AuthLevel.READ_AUTO, tool_name="redis_keys")
async def redis_keys(pattern: str = "*", db: int = _DEFAULT_DB) -> list[str]:
    """Scan keys matching a glob pattern. Auth: READ_AUTO.

    Args:
        pattern: Glob pattern to match (default ``*``).
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        List of matching key names.
    """
    client = _connect(db)
    try:
        keys: list[str] = await client.keys(pattern)
        logger.debug("redis_keys", pattern=pattern, db=db, count=len(keys))
        return keys
    finally:
        await client.aclose()


@require_approval(AuthLevel.READ_AUTO, tool_name="redis_hgetall")
async def redis_hgetall(key: str, db: int = _DEFAULT_DB) -> dict[str, str]:
    """Get all fields and values of a hash. Auth: READ_AUTO.

    Args:
        key: The hash key.
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        Dict of field-value pairs, or empty dict if key does not exist.
    """
    client = _connect(db)
    try:
        hg_coro: Any = client.hgetall(key)
        hg: Any = await hg_coro
        result: dict[str, str] = hg
        logger.debug("redis_hgetall", key=key, db=db, fields=len(result))
        return result
    finally:
        await client.aclose()


@require_approval(AuthLevel.READ_AUTO, tool_name="redis_lrange")
async def redis_lrange(
    key: str,
    start: int = 0,
    stop: int = -1,
    db: int = _DEFAULT_DB,
) -> list[str]:
    """Get a range of elements from a list. Auth: READ_AUTO.

    Args:
        key: The list key.
        start: 0-based start index.
        stop: Inclusive stop index (``-1`` for end of list).
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        List of elements in the specified range.
    """
    client = _connect(db)
    try:
        lr_coro: Any = client.lrange(key, start, stop)
        lr: Any = await lr_coro
        items: list[str] = lr
        logger.debug("redis_lrange", key=key, start=start, stop=stop, db=db, count=len(items))
        return items
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Tool implementations — WRITE_NOTIFY
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_set")
async def redis_set(
    key: str,
    value: str,
    ttl: int | None = None,
    db: int = _DEFAULT_DB,
) -> bool:
    """Set a key-value pair with optional TTL. Auth: WRITE_NOTIFY.

    Args:
        key: The Redis key.
        value: The value to store.
        ttl: Optional time-to-live in seconds.
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        ``True`` if the key was set successfully.
    """
    client = _connect(db)
    try:
        if ttl is not None:
            await client.setex(key, ttl, value)
        else:
            await client.set(key, value)
        logger.info("redis_set", key=key, db=db, ttl=ttl)
        return True
    finally:
        await client.aclose()


@require_approval(AuthLevel.WRITE_NOTIFY, tool_name="redis_hset")
async def redis_hset(key: str, field: str, value: str, db: int = _DEFAULT_DB) -> bool:
    """Set a field in a hash. Auth: WRITE_NOTIFY.

    Args:
        key: The hash key.
        field: The field name.
        value: The field value.
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        ``True`` if the field was newly created (``False`` if updated).
    """
    client = _connect(db)
    try:
        hset_coro: Any = client.hset(key, field, value)
        created: bool = await hset_coro
        logger.info("redis_hset", key=key, field=field, db=db, created=created)
        return created
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Tool implementations — DESTRUCTIVE_APPROVAL
# ---------------------------------------------------------------------------


@require_approval(AuthLevel.DESTRUCTIVE_APPROVAL, tool_name="redis_del")
async def redis_del(key: str, db: int = _DEFAULT_DB) -> int:
    """Delete one or more keys. Auth: DESTRUCTIVE_APPROVAL.

    Args:
        key: Redis key(s) to delete (space-separated for multiple keys).
        db: Redis database number (default DB5 — cost tracking).

    Returns:
        Number of keys deleted.
    """
    client = _connect(db)
    try:
        keys = key.split()
        del_coro: Any = client.delete(*keys)
        del_result: Any = await del_coro
        count: int = del_result
        logger.info("redis_del", keys=keys, db=db, count=count)
        return count
    finally:
        await client.aclose()


# ---------------------------------------------------------------------------
# Tool implementations — FORBIDDEN (always blocked)
# ---------------------------------------------------------------------------


async def redis_flushdb(db: int | None = None) -> bool:
    """Flush the current database. Auth: FORBIDDEN — NEVER executes.

    The ``require_approval`` decorator with ``AuthLevel.FORBIDDEN`` raises
    ``ForbiddenOperationError`` before this function body is ever reached.

    Args:
        db: Redis database number (ignored — operation is forbidden).

    Raises:
        ForbiddenOperationError: Always.
    """
    raise ForbiddenOperationError(
        "FLUSHDB is a forbidden operation and will never execute."
    )


async def redis_flushall() -> bool:
    """Flush all databases. Auth: FORBIDDEN — NEVER executes.

    The ``require_approval`` decorator with ``AuthLevel.FORBIDDEN`` raises
    ``ForbiddenOperationError`` before this function body is ever reached.

    Raises:
        ForbiddenOperationError: Always.
    """
    raise ForbiddenOperationError(
        "FLUSHALL is a forbidden operation and will never execute."
    )


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------


def register_tools(mcp: FastMCP) -> None:
    """Register Redis tools on the MCP server.

    Registers nine tools across all four auth levels:
    - READ_AUTO: redis_get, redis_keys, redis_hgetall, redis_lrange
    - WRITE_NOTIFY: redis_set, redis_hset
    - DESTRUCTIVE_APPROVAL: redis_del
    - FORBIDDEN: redis_flushdb, redis_flushall

    Auth levels are determined by the command classification map above.
    """
    # READ_AUTO tools
    mcp.tool(name="redis_get")(redis_get)
    mcp.tool(name="redis_keys")(redis_keys)
    mcp.tool(name="redis_hgetall")(redis_hgetall)
    mcp.tool(name="redis_lrange")(redis_lrange)

    # WRITE_NOTIFY tools
    mcp.tool(name="redis_set")(redis_set)
    mcp.tool(name="redis_hset")(redis_hset)

    # DESTRUCTIVE_APPROVAL tools
    mcp.tool(name="redis_del")(redis_del)

    # FORBIDDEN tools — always blocked by the decorator
    mcp.tool(name="redis_flushdb")(
        require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushdb")(redis_flushdb)
    )
    mcp.tool(name="redis_flushall")(
        require_approval(AuthLevel.FORBIDDEN, tool_name="redis_flushall")(redis_flushall)
    )

    logger.info(
        "redis_tools_registered",
        db_allocation=DB_ALLOCATION,
        default_db=_DEFAULT_DB,
        command_counts={
            "read": len(READ_COMMANDS),
            "write": len(WRITE_COMMANDS),
            "destructive": len(DESTRUCTIVE_COMMANDS),
            "forbidden": len(FORBIDDEN_COMMANDS),
        },
    )