"""P22.2 wave 004 — FinanceReadShim.

Reads from ``finance.*`` tables (``finance.accounts``,
``finance.debts``, ``finance.transactions``, ``finance.categories``) — the
P9 personal-finance store.

This shim satisfies the P22.2 + P22N2 boundary:

- Does NOT instantiate ``FinanceMind`` (P20 closed boundary).
  ``record_transaction`` is an L2 write path that requires a consent row
  (``consent.finance.write``) and an explicit opt-in flag. It is therefore
  DEFERRED_FOR_SAFETY by default — raises ``PermissionDeniedError`` unless the
  caller passes ``allow_record=True`` (test-namespace flag).
- All other methods are L1 read paths (no consent required).
- No DB password is logged or returned — engine is built from
  ``os.environ['DATABASE_URL']`` and the URL is NEVER logged.

The adapter wiring in ``runtime.py`` (wave 006) constructs this shim and
exposes it to ``FinanceIntegrationAdapter`` for L1 reads only. The L2 write
path remains closed until P22N2 consent gating is approved.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from guinvere.life_integrations.errors import PermissionDeniedError

logger = structlog.get_logger(__name__)

# Cap replay rows so a misconfigured caller cannot OOM the process.
REPLAY_LIMIT: int = 200

# WIB timezone (UTC+7) for date arithmetic consistency with ``src.finance.db``.
WIB = timezone(timedelta(hours=7))


class FinanceReadShim:
    """L1 read shim over the P9 personal-finance store tables.

    The L2 ``record_transaction`` path is DEFERRED_FOR_SAFETY by default
    (fail-closed). L1 reads (``replay``, ``summarize``, ``health``) are
    always available once a database URL is wired.

    Args:
        database_url: async SQLAlchemy URL (e.g.
            ``postgresql+asyncpg://user:pass@host:port/db``). Defaults to
            ``os.environ['DATABASE_URL']`` when omitted.
        allow_record: test-namespace flag that enables the L2 write path.
            MUST default to False. Only meaningful inside the P22N2 test
            harness — production wiring in ``runtime.py`` MUST leave this
            unset (or explicitly False).
    """

    def __init__(
        self,
        database_url: str | None = None,
        *,
        allow_record: bool = False,
    ) -> None:
        url = database_url or os.environ.get("DATABASE_URL")
        if not url:
            raise ValueError(
                "FinanceReadShim requires DATABASE_URL or explicit database_url"
            )
        # NOTE: do NOT log ``url`` itself — it contains the DB password.
        self._engine: AsyncEngine = create_async_engine(url)
        self._allow_record: bool = allow_record

    async def _rows_as_dicts(
        self, conn: AsyncConnection, sql: str, params: dict[str, Any] | None = None
    ) -> list[dict[str, Any]]:
        """Execute a parameterized SELECT and return rows as dicts."""
        result = await conn.execute(text(sql), params or {})
        rows = result.mappings().fetchall()
        return [dict(row) for row in rows]

    async def replay(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Return up to 200 recent transactions, newest first.

        ``filters`` is currently a placeholder — keep simple: when falsy we
        issue a plain LIMIT 200 query. When provided we add a single WHERE
        clause on ``category`` (the most common filter — extend with care).
        """
        params: dict[str, Any] = {"limit": REPLAY_LIMIT}
        sql = (
            "SELECT id, amount, currency, category, description, created_at "
            "FROM finance.transactions "
            "ORDER BY created_at DESC "
            "LIMIT :limit"
        )
        if filters and "category" in filters:
            sql = (
                "SELECT id, amount, currency, category, description, created_at "
                "FROM finance.transactions "
                "WHERE category = :category "
                "ORDER BY created_at DESC "
                "LIMIT :limit"
            )
            params["category"] = filters["category"]

        async with self._engine.connect() as conn:
            rows = await self._rows_as_dicts(conn, sql, params)

        logger.info(
            "p22.finance.replay",
            returned=len(rows),
            limit=REPLAY_LIMIT,
            filtered=bool(filters and "category" in filters),
        )
        return rows

    async def summarize(self, period: str) -> dict[str, Any]:
        """Return count + total amount for the requested period.

        Supported ``period`` aliases:

        - ``daily`` / ``today`` — current WIB day (00:00 WIB to now).
        - ``current_week`` / ``weekly`` — current WIB week (Monday 00:00 WIB to now).
        - ``current_month`` / ``monthly`` — first of current WIB month to now.

        Unknown aliases raise :class:`ValueError` (fail-fast, no fake PASS).
        """
        aliases = {
            "daily": "daily",
            "today": "daily",
            "current_week": "weekly",
            "weekly": "weekly",
            "current_month": "monthly",
            "monthly": "monthly",
        }
        canonical = aliases.get(period)
        if canonical is None:
            raise ValueError(f"Unsupported period: {period}")

        now_wib = datetime.now(tz=WIB)
        if canonical == "daily":
            start = now_wib.replace(hour=0, minute=0, second=0, microsecond=0)
        elif canonical == "weekly":
            monday_date = now_wib.date() - timedelta(days=now_wib.weekday())
            start = datetime(
                year=monday_date.year,
                month=monday_date.month,
                day=monday_date.day,
                tzinfo=WIB,
            )
        else:  # monthly
            start = now_wib.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        sql = (
            "SELECT COUNT(*) AS transaction_count, "
            "COALESCE(SUM(amount), 0) AS total "
            "FROM finance.transactions "
            "WHERE created_at >= :start"
        )
        params: dict[str, Any] = {"start": start}

        async with self._engine.connect() as conn:
            rows = await self._rows_as_dicts(conn, sql, params)
        row = rows[0] if rows else {"transaction_count": 0, "total": 0}

        logger.info(
            "p22.finance.summarize",
            period=period,
            canonical=canonical,
            transaction_count=row.get("transaction_count", 0),
        )
        return {
            "period": period,
            "transaction_count": row.get("transaction_count", 0),
            "total": row.get("total", 0),
        }

    async def record_transaction(self, **kwargs: Any) -> dict[str, Any]:
        """L2 write path — DEFERRED_FOR_SAFETY.

        Always raises :class:`PermissionDeniedError` unless the test-namespace
        flag ``allow_record=True`` was passed to ``__init__``. Production
        wiring MUST NOT enable this — consent gating is the prerequisite and
        is itself DEFERRED until P22N2 approval.
        """
        if not self._allow_record:
            raise PermissionDeniedError(
                "finance record_transaction DEFERRED_FOR_SAFETY — "
                "needs consent.finance.write row + test-namespace flag"
            )
        # Even with the flag set, defer the actual implementation until
        # P22N2 consent gating lands. Returning a stub avoids silent writes.
        logger.warning(
            "p22.finance.record_transaction_stub",
            received_keys=sorted(kwargs.keys()),
        )
        return {
            "deferred": True,
            "reason": "P22N2-consent-gating-pending",
            "received_kwargs": sorted(kwargs.keys()),
        }

    async def health(self) -> bool:
        """Return True iff a trivial query on ``finance.accounts`` succeeds.

        Catches and logs engine/db errors so ``health`` never raises — this
        is the wave-004 probe used by ``FinanceIntegrationAdapter.health_check``.
        """
        try:
            async with self._engine.connect() as conn:
                await conn.execute(text("SELECT 1 FROM finance.accounts LIMIT 1"))
            logger.info("p22.finance.health_ok")
            return True
        except Exception as exc:  # noqa: BLE001 — health-ping, must not raise
            logger.warning(
                "p22.finance.health_failed",
                error_type=type(exc).__name__,
                error_message=str(exc)[:200],
            )
            return False
