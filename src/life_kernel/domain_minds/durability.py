"""Durability backends for Living Autonomy Kernel domain records.

Provides an abstract ``DurabilityBackend`` plus two concrete implementations:

* ``PostgresAuditJournal`` persists records to a PostgreSQL audit journal.
* ``InMemoryJournal`` keeps records in memory for testing and fallback only.

FinanceMind uses ``InMemoryJournal`` by default in test mode. Production
configurations should use ``PostgresAuditJournal`` via the factory function
``create_finance_durability(mode="production")``.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any, cast

import structlog

logger = structlog.get_logger(__name__)


class DurabilityBackend(ABC):
    """Abstract durability backend for domain records."""

    @abstractmethod
    async def record(self, entry: dict[str, Any]) -> str:
        """Persist ``entry`` and return a unique entry ID."""

    @abstractmethod
    async def read(self, entry_id: str) -> dict[str, Any] | None:
        """Return the entry with ``entry_id`` or ``None`` if not found."""

    @abstractmethod
    async def list_entries(self, source: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return up to ``limit`` entries for the given ``source``."""

    @abstractmethod
    async def health(self) -> bool:
        """Return ``True`` if the backend is healthy."""


class PostgresAuditJournal(DurabilityBackend):
    """PostgreSQL audit journal persistence.

    Records are stored as JSONB rows in ``<schema>.audit_journal``.  If the
    database is unavailable, operations log a warning and (for ``health``)
    return ``False``.
    """

    def __init__(
        self,
        dsn: str = "postgresql+asyncpg://guinevere_core@localhost:5433/guinevere_core",
        schema: str = "life_kernel",
        table: str = "audit_journal",
    ) -> None:
        self.dsn = dsn
        self.schema = schema
        self.table = table
        self._initialized = False
        self._engine: Any | None = None
        self._log = logger.bind(backend="PostgresAuditJournal")

    def _get_engine(self) -> Any:
        """Return a cached async SQLAlchemy engine, creating it if needed."""
        if self._engine is None:
            from sqlalchemy.ext.asyncio import create_async_engine

            self._engine = create_async_engine(self.dsn, pool_pre_ping=True)
        return self._engine

    async def ensure_table(self) -> bool:
        """CREATE TABLE IF NOT EXISTS life_kernel.audit_journal (shadow table).

        This creates the audit journal table with columns: ``id UUID``,
        ``source TEXT``, ``entry JSONB``, ``recorded_at TIMESTAMPTZ``.
        """
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            # asyncpg (via SQLAlchemy) cannot execute multiple SQL statements
            # in a single prepared statement — "cannot insert multiple commands
            # into a prepared statement". So each DDL statement must be a
            # separate execute() call.
            statements = [
                f"CREATE SCHEMA IF NOT EXISTS {self.schema}",
                f"CREATE TABLE IF NOT EXISTS {self.schema}.{self.table} ("
                "    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
                "    source TEXT NOT NULL,"
                "    entry JSONB NOT NULL,"
                "    recorded_at TIMESTAMPTZ NOT NULL DEFAULT now()"
                ")",
                f"CREATE INDEX IF NOT EXISTS idx_{self.table}_source "
                f"ON {self.schema}.{self.table}(source)",
            ]
            async with engine.begin() as conn:
                for stmt in statements:
                    await conn.execute(text(stmt))
            self._initialized = True
            return True
        except Exception as exc:
            self._log.warning("ensure_table_failed", error=str(exc))
            return False

    async def record(self, entry: dict[str, Any]) -> str:
        """Insert ``entry`` into the audit journal and return the row ID."""
        if not self._initialized:
            await self.ensure_table()
        try:
            import json

            from sqlalchemy import text

            engine = self._get_engine()
            entry_id = str(uuid.uuid4())
            source = str(entry.get("source", "unknown"))
            # asyncpg expects a JSON *string* for a JSONB column (it calls
            # .encode() on the bound value); a raw dict raises DataError.
            # Serialize to a JSON string and bind it, then cast to jsonb in
            # SQL using the ``CAST(:x AS jsonb)`` form (the ``::`` postfix
            # operator collides with SQLAlchemy's ``:param`` syntax when the
            # param name abuts it).
            entry_json = json.dumps(entry, default=str, ensure_ascii=False)
            async with engine.begin() as conn:
                await conn.execute(
                    text(
                        f"INSERT INTO {self.schema}.{self.table} "
                        "(id, source, entry, recorded_at) "
                        "VALUES (:id, :source, CAST(:entry AS jsonb), now())"
                    ),
                    {
                        "id": entry_id,
                        "source": source,
                        "entry": entry_json,
                    },
                )
            return entry_id
        except Exception as exc:
            self._log.warning("record_failed", error=str(exc))
            raise

    async def read(self, entry_id: str) -> dict[str, Any] | None:
        """Return the entry with ``entry_id`` or ``None``."""
        if not self._initialized:
            await self.ensure_table()
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        f"SELECT entry FROM {self.schema}.{self.table} "
                        "WHERE id = :id"
                    ),
                    {"id": entry_id},
                )
                row = result.mappings().first()
                if row is None:
                    return None
                return cast(dict[str, Any], row["entry"])
        except Exception as exc:
            self._log.warning("read_failed", error=str(exc))
            raise

    async def list_entries(self, source: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return up to ``limit`` entries for the given ``source``."""
        if not self._initialized:
            await self.ensure_table()
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            async with engine.connect() as conn:
                result = await conn.execute(
                    text(
                        f"SELECT entry FROM {self.schema}.{self.table} "
                        "WHERE source = :source ORDER BY recorded_at DESC LIMIT :limit"
                    ),
                    {"source": source, "limit": limit},
                )
                rows = result.mappings().all()
                return [cast(dict[str, Any], row["entry"]) for row in rows]
        except Exception as exc:
            self._log.warning("list_entries_failed", error=str(exc))
            raise

    async def health(self) -> bool:
        """Return ``True`` if PostgreSQL is reachable."""
        try:
            from sqlalchemy import text

            engine = self._get_engine()
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
            return True
        except Exception as exc:
            self._log.warning("health_check_failed", error=str(exc))
            return False


class InMemoryJournal(DurabilityBackend):
    """In-memory journal for testing and fallback.

    Stores copies of recorded entries in a list.  ``list_entries`` filters by
    the ``source`` key inside each entry; an empty ``source`` returns every
    entry.
    """

    def __init__(self) -> None:
        self._entries: list[dict[str, Any]] = []

    async def record(self, entry: dict[str, Any]) -> str:
        """Store a copy of ``entry`` and return a generated ID."""
        entry_id = str(uuid.uuid4())
        stored = dict(entry)
        stored["__id__"] = entry_id
        self._entries.append(stored)
        return entry_id

    async def read(self, entry_id: str) -> dict[str, Any] | None:
        """Return the entry whose generated ID matches ``entry_id``."""
        for entry in self._entries:
            if entry.get("__id__") == entry_id:
                return dict(entry)
        return None

    async def list_entries(self, source: str, limit: int = 100) -> list[dict[str, Any]]:
        """Return up to ``limit`` entries whose ``source`` key matches.

        If ``source`` is empty, every entry is considered a match.
        """
        if not source:
            matches = list(self._entries)
        else:
            matches = [e for e in self._entries if e.get("source") == source]
        return matches[:limit]

    async def health(self) -> bool:
        """In-memory backend is always healthy."""
        return True
