"""Checkpointers for Guinevere's Living Autonomy Kernel.

This module provides LangGraph checkpointer setup for PostgreSQL and Redis
persistence, enabling state recovery and checkpointing for the autonomous kernel.
"""

from __future__ import annotations

import logging
import re
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


def _redact_url(url: str) -> str:
    """Redact credentials from a connection URL for safe logging."""
    return re.sub(r"://([^:]+):[^@]+@", r"://\1:***@", url)


async def create_postgres_checkpointer(dsn: str = "postgresql://guinevere_core@localhost:5433/guinevere_core"):
    """Create a PostgreSQL-based LangGraph checkpointer for the autonomous kernel.

    This checkpointer persists kernel state to PostgreSQL, enabling recovery
    after crashes and checkpointing of the autonomous execution state.

    Args:
        dsn: PostgreSQL connection string. Default: `postgresql://guinevere_core@localhost:5433/guinevere_core`

    Returns:
        AsyncPostgresSaver configured checkpointer.

    Raises:
        ImportError: If langgraph.checkpoint.postgres.aio is not installed.
        Exception: If PostgreSQL connection or setup fails.
    """
    logger.info("creating_postgres_checkpointer", dsn=_redact_url(dsn))

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

        # from_conn_string returns an async context manager in langgraph v1.x.
        # We enter it to get the actual checkpointer instance, then keep the CM
        # alive by storing it on the checkpointer to prevent GC closing the pool.
        cm = AsyncPostgresSaver.from_conn_string(dsn)
        checkpointer = await cm.__aenter__()

        # Setup the checkpointer (creates required tables if not exists)
        logger.info("setting_up_postgres_checkpointer")
        await checkpointer.setup()

        # Keep the context manager alive to prevent the connection pool from
        # being closed by garbage collection. Store on a private attribute.
        setattr(checkpointer, "_ctx_manager", cm)

        logger.info("postgres_checkpointer_created", dsn=_redact_url(dsn))

        return checkpointer

    except ImportError as e:
        logger.error("langgraph_postgres_checkpointer_not_available", error=str(e))
        raise
    except Exception as e:
        logger.error("postgres_checkpointer_creation_failed", error=str(e))
        raise


async def create_redis_checkpointer(url: str = "redis://guinevere_core@localhost:6380/6"):
    """Create a Redis-based LangGraph checkpointer for the autonomous kernel.

    This checkpointer persists kernel state to Redis, enabling fast state
    recovery and distributed checkpointing. Uses DB 6 for life_kernel, which
    is reserved and not used by other subsystems.

    Args:
        url: Redis connection string. Default: `redis://guinevere_core@localhost:6380/6`

    Returns:
        AsyncRedisSaver configured checkpointer.

    Raises:
        ImportError: If langgraph.checkpoint.redis.aio is not installed.
        Exception: If Redis connection or setup fails.
    """
    logger.info("creating_redis_checkpointer", url=_redact_url(url))

    try:
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        # Create checkpointer from connection string using async context manager
        cm = AsyncRedisSaver.from_conn_string(url)
        checkpointer = await cm.__aenter__()

        # Setup the checkpointer (creates required keys if not exists)
        logger.info("setting_up_redis_checkpointer")
        await checkpointer.setup()

        # Keep the context manager alive to prevent connection closure by GC.
        setattr(checkpointer, "_ctx_manager", cm)

        logger.info("redis_checkpointer_created", url=_redact_url(url))

        return checkpointer

    except ImportError as e:
        logger.error("langgraph_redis_checkpointer_not_available", error=str(e))
        raise
    except Exception as e:
        logger.error("redis_checkpointer_creation_failed", error=str(e))
        raise


async def create_dual_checkpointer(pg_dsn: str, redis_url: str) -> tuple[Any, Any]:
    """Create both PostgreSQL and Redis checkpointers for layered checkpointing.

    This function creates two checkpointers: PostgreSQL for durable persistence
    and Redis for fast recovery. The kernel can use either or both depending
    on configuration and requirements.

    Args:
        pg_dsn: PostgreSQL connection string.
        redis_url: Redis connection string.

    Returns:
        Tuple of (AsyncPostgresSaver, AsyncRedisSaver) checkpointers.

    Raises:
        ImportError: If either checkpointer library is not installed.
        Exception: If either connection or setup fails.
    """
    logger.info("creating_dual_checkpointer", pg_dsn=_redact_url(pg_dsn), redis_url=_redact_url(redis_url))

    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
        from langgraph.checkpoint.redis.aio import AsyncRedisSaver

        # Create PostgreSQL checkpointer using async context manager
        pg_cm = AsyncPostgresSaver.from_conn_string(pg_dsn)
        pg_checkpointer = await pg_cm.__aenter__()
        logger.info("creating_postgres_checkpointer_for_dual")
        await pg_checkpointer.setup()
        setattr(pg_checkpointer, "_ctx_manager", pg_cm)

        # Create Redis checkpointer using async context manager
        redis_cm = AsyncRedisSaver.from_conn_string(redis_url)
        redis_checkpointer = await redis_cm.__aenter__()
        logger.info("creating_redis_checkpointer_for_dual")
        await redis_checkpointer.setup()
        setattr(redis_checkpointer, "_ctx_manager", redis_cm)

        logger.info("dual_checkpointer_created", pg_dsn=_redact_url(pg_dsn), redis_url=_redact_url(redis_url))

        return pg_checkpointer, redis_checkpointer

    except ImportError as e:
        logger.error("dual_checkpointer_import_failed", error=str(e))
        raise
    except Exception as e:
        logger.error("dual_checkpointer_creation_failed", error=str(e))
        raise