"""Knowledge Graph base repository.

Encapsulates session lifecycle so downstream modules (``extraction``,
``resolution``, ``query``, ``ingestion``, ``consent``, ``eval``) never
own a DB engine or pool.  The repository receives a ``session_factory``
callable (typically :func:`guinevere.memory.db.get_async_session`) and yields
sessions through a context manager.

Critical rules:

- The repository NEVER creates its own engine / pool / connection.
  It always reuses the caller-supplied ``session_factory`` to keep the
  Guinevere memory connection budget unchanged.
- :meth:`KGRepository.health_check` swallows ``OperationalError`` (the
  ``memory.kg_entities`` table may not be migrated yet) and returns a
  status object.  All other exceptions propagate.
- No empty catches: every error path either re-raises or returns a
  status object with the underlying error recorded for audit.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Protocol, TypeAlias

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Session protocol
# ---------------------------------------------------------------------------


class AsyncSessionProtocol(Protocol):
    """Minimal async SQLAlchemy session interface used by the KG module.

    Covers the subset of ``sqlalchemy.ext.asyncio.AsyncSession`` that the
    base repository needs.  Mirrors the pattern from
    ``guinevere.memory.consolidation.AsyncSessionProtocol``.
    """

    async def execute(self, statement: object, params: object | None = None) -> object:
        """Execute a statement and return a SQLAlchemy ``Result``."""
        ...

    async def __aenter__(self) -> "AsyncSessionProtocol":
        ...

    async def __aexit__(self, *args: object) -> None:
        ...


SessionFactory: TypeAlias = Callable[[], AsyncSessionProtocol]
"""Callable that returns a fresh :class:`AsyncSessionProtocol`.

The factory is responsible for commit / rollback semantics — the
repository does not commit on behalf of the caller.
"""


# ---------------------------------------------------------------------------
# Health status
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KGHealthStatus:
    """Outcome of a :meth:`KGRepository.health_check` probe.

    Attributes:
        ok: ``True`` only when the probe query executed successfully
            AND the ``memory.kg_entities`` table is present and readable.
        schema_ready: ``True`` when the table exists (absence triggers
            ``OperationalError`` from asyncpg).  Distinguishes "DB up,
            KG not migrated" from "DB up, KG migrated, probe failed".
        detail: Human-readable status line safe for logging.
    """

    ok: bool
    schema_ready: bool
    detail: str


# ---------------------------------------------------------------------------
# Repository
# ---------------------------------------------------------------------------


# Lazy import to keep this module free of SQLAlchemy at import time.
_sa_text: Callable[[str], object] | None = None
_sa_operational_error: type[Exception] | None = None


def _load_sqlalchemy_helpers() -> tuple[Callable[[str], object], type[Exception]]:
    """Resolve :func:`sqlalchemy.text` and :class:`OperationalError` lazily.

    Imported here (not at module top) so :mod:`guinevere.knowledge_graph.__init__`
    can be imported in environments that have not installed SQLAlchemy
    yet (e.g. early config-validation runs).
    """
    global _sa_text, _sa_operational_error
    if _sa_text is None or _sa_operational_error is None:
        from sqlalchemy import text as _text
        from sqlalchemy.exc import OperationalError as _OperationalError
        _sa_text = _text
        _sa_operational_error = _OperationalError
    return _sa_text, _sa_operational_error


class BorrowedSession:
    """Proxy that strips lifecycle methods from an AsyncSession.

    When the KG repository's :meth:`KGRepository.get_session` receives
    this wrapper from a ``session_factory``:

    1. ``hasattr(wrapper, "__aenter__")`` → ``False`` → bare yield path.
    2. ``getattr(wrapper, "close", None)`` → ``None`` → finally no-op.

    The caller retains full lifecycle ownership of the underlying session.
    This is used by integration points (``consolidation.py``,
    ``read_pipeline.py``, ``prompt_loader.py``) that already have an
    active session and want the KG module to use it without closing it.

    Args:
        session: The active async session to borrow.  The caller is
            responsible for commit / rollback / close.
    """

    __slots__ = ("_wrapped",)

    def __init__(self, session: object) -> None:
        object.__setattr__(self, "_wrapped", session)

    def __getattr__(self, name: str) -> object:
        if name in ("__aenter__", "__aexit__", "close"):
            raise AttributeError(name)
        return getattr(self._wrapped, name)


def make_borrowed_factory(session: object) -> Callable[[], BorrowedSession]:
    """Create a session factory that returns a :class:`BorrowedSession`.

    Use this in integration points where you already have an active
    session and want the KG module to use it without taking ownership::

        kg_engine = KGQueryEngine(make_borrowed_factory(session))

    The returned factory is a closure that captures ``session`` and
    returns a new :class:`BorrowedSession` wrapper each time.
    """
    def _factory() -> BorrowedSession:
        return BorrowedSession(session)
    return _factory


class KGRepository:
    """Base repository for the Knowledge Graph module.

    Provides session lifecycle and a small set of helpers (raw execute,
    health probe) shared by every downstream submodule.  No business
    logic lives here — entity / edge / triple-specific queries are added
    by ``query/`` and ``ingestion/`` once the schema migration lands.

    Args:
        session_factory: Callable that returns a fresh async session.
            Typically ``guinevere.memory.db.get_async_session`` from the
            Guinevere memory module — wired in at app start-up so
            the KG shares the existing connection pool.

    Example::

        repo = KGRepository(session_factory=guinevere.memory.db.get_async_session)
        async with repo.get_session() as session:
            result = await session.execute(...)
    """

    def __init__(self, session_factory: SessionFactory) -> None:
        self._session_factory: SessionFactory = session_factory

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    @asynccontextmanager
    async def get_session(self) -> AsyncIterator[AsyncSessionProtocol]:
        """Yield an :class:`AsyncSessionProtocol` from the injected factory.

        The factory owns commit / rollback semantics.  This method is a
        pure lifecycle helper — it never closes a session it did not
        open and never commits on the caller's behalf.
        """
        session = self._session_factory()
        # The factory may return either an async-context-manager-style
        # session or a bare session.  We support both: if the session
        # supports ``__aenter__`` we use the context manager; otherwise
        # we yield the bare session and let the factory close it.
        if hasattr(session, "__aenter__"):
            async with session as managed:
                yield managed
        else:
            try:
                yield session
            finally:
                close = getattr(session, "close", None)
                if close is not None:
                    result = close()
                    if hasattr(result, "__await__"):
                        await result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    async def execute(
        self,
        text_sql: str,
        params: dict[str, object] | None = None,
    ) -> object:
        """Execute a raw parameterized SQL string and return the ``Result``.

        Args:
            text_sql: Parameterized SQL using ``:name`` placeholders.
            params: Bind values keyed by placeholder name.  ``None`` is
                treated as an empty mapping.

        Returns:
            The raw ``sqlalchemy.engine.Result`` (or compatible) object
            from the underlying driver.  Callers should narrow the type
            as needed.
        """
        text, _ = _load_sqlalchemy_helpers()
        async with self.get_session() as session:
            return await session.execute(text(text_sql), params or {})

    async def health_check(self) -> KGHealthStatus:
        """Probe the ``memory.kg_entities`` table for schema readiness.

        Returns:
            :class:`KGHealthStatus` describing the outcome.  ``OperationalError``
            (table missing → schema not yet migrated) is swallowed and
            reported as ``ok=False, schema_ready=False``.  All other
            exceptions propagate.
        """
        text, operational_error = _load_sqlalchemy_helpers()
        try:
            async with self.get_session() as session:
                await session.execute(
                    text("SELECT 1 FROM memory.kg_entities LIMIT 1"),
                )
        except Exception as exc:  # noqa: BLE001 — narrowed below
            if operational_error is not None and isinstance(exc, operational_error):
                logger.warning(
                    "kg_health_check_schema_missing",
                    extra={"table": "memory.kg_entities"},
                )
                return KGHealthStatus(
                    ok=False,
                    schema_ready=False,
                    detail="memory.kg_entities not migrated",
                )
            # Unexpected error — re-raise so it is not silently swallowed.
            raise

        return KGHealthStatus(ok=True, schema_ready=True, detail="ok")


__all__ = [
    "AsyncSessionProtocol",
    "SessionFactory",
    "KGHealthStatus",
    "KGRepository",
]
