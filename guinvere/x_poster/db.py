"""P13 X Auto Poster — asyncpg connection pool manager."""

from __future__ import annotations

from typing import Any

import asyncpg
import structlog

from .config import get_xposter_settings
from .exceptions import DatabaseConnectionError, DatabaseQueryError

_logger = structlog.get_logger(__name__)


class DatabaseManager:
    """Manages asyncpg connection pool for P13 PostgreSQL operations."""

    def __init__(self) -> None:
        """Initialize database manager with settings but no pool yet."""
        self._pool: asyncpg.Pool | None = None
        self._settings = get_xposter_settings()

    async def initialize(self) -> None:
        """Create connection pool. Raises DatabaseConnectionError on failure."""
        try:
            self._pool = await asyncpg.create_pool(
                host=self._settings.postgres_host,
                port=self._settings.postgres_port,
                database=self._settings.postgres_db,
                user=self._settings.postgres_user,
                password=self._settings.postgres_password,
                min_size=self._settings.db_pool_min,
                max_size=self._settings.db_pool_max,
                command_timeout=30,
            )
            _logger.info(
                "x_poster.db.pool_created",
                min=self._settings.db_pool_min,
                max=self._settings.db_pool_max,
            )
        except Exception as exc:
            raise DatabaseConnectionError(f"Failed to create pool: {exc}") from exc

    async def close(self) -> None:
        """Close pool gracefully."""
        if self._pool:
            await self._pool.close()
            self._pool = None
            _logger.info("x_poster.db.pool_closed")

    async def execute(self, query: str, *args: Any) -> str:
        """Execute query, return status. Raises DatabaseQueryError."""
        if not self._pool:
            raise DatabaseConnectionError("Pool not initialized")
        try:
            async with self._pool.acquire() as conn:
                return await conn.execute(query, *args)
        except Exception as exc:
            raise DatabaseQueryError(f"Execute failed: {exc}") from exc

    async def fetch(self, query: str, *args: Any) -> list[dict[str, Any]]:
        """Fetch rows as list of dicts. Raises DatabaseQueryError."""
        if not self._pool:
            raise DatabaseConnectionError("Pool not initialized")
        try:
            async with self._pool.acquire() as conn:
                records = await conn.fetch(query, *args)
                return [dict(r) for r in records]
        except Exception as exc:
            raise DatabaseQueryError(f"Fetch failed: {exc}") from exc

    async def fetchrow(self, query: str, *args: Any) -> dict[str, Any] | None:
        """Fetch single row as dict. Raises DatabaseQueryError."""
        if not self._pool:
            raise DatabaseConnectionError("Pool not initialized")
        try:
            async with self._pool.acquire() as conn:
                record = await conn.fetchrow(query, *args)
                return dict(record) if record else None
        except Exception as exc:
            raise DatabaseQueryError(f"Fetchrow failed: {exc}") from exc

    @property
    def pool(self) -> asyncpg.Pool:
        """Direct pool access for transactions."""
        if not self._pool:
            raise DatabaseConnectionError("Pool not initialized")
        return self._pool
