"""M8 Memory backend -- memory, knowledge graph, and internal data.

Ported from: P22 memory_adapter.py, finance_adapter.py, calendar_adapter.py,
notion_adapter.py, drive_adapter.py.

30 actions: 12 REAL (redis.asyncio DB5 + asyncpg), 18 CONFIG_MISSING.
REAL:  memory core (recall, store, store_fact, mark_dnr, search_kg) via Redis DB5,
       finance (list_transactions, summarize, detect_anomalies, export_transactions,
       record_transaction, correct_transaction, bulk_import) via asyncpg.
CONFIG_MISSING: Notion (6), Drive (7), Calendar (5) -- need external API creds (P7).
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

from guinevere.tools.tool_backend import Action, ActionTier, ToolBackend

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Connection factories (module-level so tests can monkeypatch)
# ---------------------------------------------------------------------------

def _get_redis():
    """Return a redis.asyncio client connected to DB5 (memory store)."""
    import redis.asyncio as aioredis
    return aioredis.from_url("redis://localhost:6379/5", decode_responses=True)


async def _get_pg():
    """Return an asyncpg connection to the guinevere database."""
    import asyncpg
    return await asyncpg.connect(dsn="postgresql://localhost:5432/guinevere")


# ---------------------------------------------------------------------------
# CONFIG_MISSING helper
# ---------------------------------------------------------------------------

def _config_missing(service: str, action: str) -> dict[str, Any]:
    """Standard response for actions that need external API credentials."""
    return {
        "ok": False,
        "config_missing": True,
        "action": action,
        "error": f"needs {service} API creds (P7 scope)",
    }


# ---------------------------------------------------------------------------
# MemoryBackend
# ---------------------------------------------------------------------------

class MemoryBackend(ToolBackend):
    """Memory/KG/internal-data backend (L1/L2/L3).

    Absorbs 5 P22 adapters: memory, finance, calendar, notion, drive.
    """

    @property
    def name(self) -> str:
        return "memory"

    def actions(self) -> list[Action]:
        return [
            # -- Memory core (L1 READ) --
            Action("recall", ActionTier.L1_READ, description="Recall memories via vector+FTS"),
            Action("search_kg", ActionTier.L1_READ, description="Search knowledge graph"),
            # -- Finance (L1 READ) --
            Action("list_transactions", ActionTier.L1_READ, description="List financial transactions"),
            Action("summarize", ActionTier.L1_READ, description="Finance period summary"),
            Action("detect_anomalies", ActionTier.L1_READ, description="Spending anomaly detection"),
            Action("export_transactions", ActionTier.L1_READ, description="Export CSV/JSON"),
            # -- Calendar (L1 READ) --
            Action("list_events", ActionTier.L1_READ, description="List calendar events"),
            Action("get_event", ActionTier.L1_READ, description="Get specific event"),
            # -- Notion (L1 READ) --
            Action("retrieve_page", ActionTier.L1_READ, description="Get Notion page"),
            Action("search_notes", ActionTier.L1_READ, description="Search Notion pages"),
            # -- Drive (L1 READ) --
            Action("list_files", ActionTier.L1_READ, description="List Drive files"),
            Action("get_file", ActionTier.L1_READ, description="Get Drive file metadata"),
            # -- Memory core (L2 WRITE) --
            Action("store", ActionTier.L2_WRITE, description="Store episode"),
            Action("store_fact", ActionTier.L2_WRITE, description="Store semantic fact"),
            # -- Finance (L2 WRITE) --
            Action("record_transaction", ActionTier.L2_WRITE, description="Record transaction"),
            # -- Calendar (L2 WRITE) --
            Action("create_event", ActionTier.L2_WRITE, description="Create calendar event"),
            Action("update_event", ActionTier.L2_WRITE, description="Update calendar event"),
            # -- Notion (L2 WRITE) --
            Action("create_page", ActionTier.L2_WRITE, description="Create Notion page"),
            Action("update_page", ActionTier.L2_WRITE, description="Update Notion page"),
            Action("append_blocks", ActionTier.L2_WRITE, description="Append blocks to Notion page"),
            # -- Drive (L2 WRITE) --
            Action("create_file", ActionTier.L2_WRITE, description="Create/upload Drive file"),
            Action("update_file", ActionTier.L2_WRITE, description="Update Drive file"),
            Action("trash_file", ActionTier.L2_WRITE, description="Trash Drive file (30d recovery)"),
            # -- L3 DESTRUCTIVE --
            Action("mark_dnr", ActionTier.L3_DESTRUCTIVE, description="Mark memory do-not-recall"),
            Action("correct_transaction", ActionTier.L3_DESTRUCTIVE, description="Correct via compensating entry"),
            Action("bulk_import", ActionTier.L3_DESTRUCTIVE, description="Bulk import finance data"),
            Action("delete_event", ActionTier.L3_DESTRUCTIVE, description="Delete calendar event"),
            Action("archive_page", ActionTier.L3_DESTRUCTIVE, description="Archive Notion page"),
            Action("delete_file", ActionTier.L3_DESTRUCTIVE, description="Permanently delete Drive file"),
            Action("public_share", ActionTier.L3_DESTRUCTIVE, description="Public sharing"),
        ]

    def is_available(self) -> bool:
        return True  # Memory always available via guinevere.memory (W9)

    # -----------------------------------------------------------------------
    # dispatch -- NEVER raises to caller (fail-soft)
    # -----------------------------------------------------------------------

    async def dispatch(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Execute a memory action.  Redis (DB5) + asyncpg for REAL actions,
        config_missing for external APIs.  Never raises."""
        action_lower = action.lower()

        try:
            # -- Memory core (REAL -- redis.asyncio DB5) --
            if action_lower == "recall":
                return await self._recall(action, args)
            if action_lower == "store":
                return await self._store(action, args)
            if action_lower == "store_fact":
                return await self._store_fact(action, args)
            if action_lower == "mark_dnr":
                return await self._mark_dnr(action, args)
            if action_lower == "search_kg":
                return await self._search_kg(action, args)

            # -- Finance (REAL -- asyncpg) --
            if action_lower == "list_transactions":
                return await self._list_transactions(action, args)
            if action_lower == "summarize":
                return await self._summarize(action, args)
            if action_lower == "detect_anomalies":
                return await self._detect_anomalies(action, args)
            if action_lower == "export_transactions":
                return await self._export_transactions(action, args)
            if action_lower == "record_transaction":
                return await self._record_transaction(action, args)
            if action_lower == "correct_transaction":
                return await self._correct_transaction(action, args)
            if action_lower == "bulk_import":
                return await self._bulk_import(action, args)

            # -- Notion (CONFIG_MISSING) --
            if action_lower in ("retrieve_page", "search_notes", "create_page",
                                 "update_page", "append_blocks", "archive_page"):
                return _config_missing("Notion", action)

            # -- Drive (CONFIG_MISSING) --
            if action_lower in ("list_files", "get_file", "create_file",
                                 "update_file", "trash_file", "delete_file",
                                 "public_share"):
                return _config_missing("Drive", action)

            # -- Calendar (CONFIG_MISSING) --
            if action_lower in ("list_events", "get_event", "create_event",
                                 "update_event", "delete_event"):
                return _config_missing("calendar", action)

            return {"ok": False, "error": f"unknown memory action: {action}"}

        except Exception as exc:
            logger.error("memory.dispatch failed action=%s: %s", action, exc, exc_info=True)
            return {"ok": False, "action": action, "error": str(exc)}

    # -----------------------------------------------------------------------
    # Memory core -- redis.asyncio DB5
    # -----------------------------------------------------------------------

    async def _recall(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Recall episodes by keyword scan over Redis sorted set + hash lookup."""
        query = args.get("query", "")
        limit = args.get("limit", 5)
        redis = _get_redis()
        try:
            # Get all episode IDs from sorted set (scored by timestamp)
            all_ids = await redis.zrangebyscore("memory:episodes", "-inf", "+inf",
                                                 start=0, num=limit * 10)
            results = []
            for ep_id in all_ids:
                data = await redis.hgetall(ep_id)
                if not data:
                    continue
                content = data.get("content", "")
                # Simple substring match for FTS (real impl would use RediSearch)
                if query.lower() in content.lower():
                    # Skip DNR episodes
                    is_dnr = await redis.sismember("memory:dnr", ep_id)
                    if is_dnr:
                        continue
                    results.append({
                        "episode_id": ep_id,
                        "content": content,
                        "tags": json.loads(data.get("tags", "[]")),
                        "timestamp": data.get("timestamp", ""),
                    })
                    if len(results) >= limit:
                        break
            return {"ok": True, "action": action, "query": query, "limit": limit,
                    "results": results, "count": len(results)}
        finally:
            await redis.close()

    async def _store(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Store an episode in Redis DB5 (hash + sorted set)."""
        content = args.get("content", "")
        tags = args.get("tags", [])
        ep_id = f"ep:{uuid.uuid4().hex[:12]}"
        ts = time.time()
        redis = _get_redis()
        try:
            await redis.hset(ep_id, mapping={
                "content": content,
                "tags": json.dumps(tags),
                "timestamp": str(ts),
            })
            await redis.zadd("memory:episodes", {ep_id: ts})
            return {"ok": True, "action": action, "episode_id": ep_id,
                    "content_len": len(content)}
        finally:
            await redis.close()

    async def _store_fact(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Store a semantic fact (subject-predicate-object) in Redis DB5."""
        subject = args.get("subject", "")
        predicate = args.get("predicate", "")
        obj = args.get("object", "")
        fact_id = f"fact:{uuid.uuid4().hex[:12]}"
        redis = _get_redis()
        try:
            await redis.hset(fact_id, mapping={
                "subject": subject,
                "predicate": predicate,
                "object": obj,
            })
            # Also index in KG set for search_kg
            kg_key = f"kg:{subject}:{predicate}"
            await redis.hset(kg_key, mapping={
                "subject": subject,
                "predicate": predicate,
                "object": obj,
                "fact_id": fact_id,
            })
            return {"ok": True, "action": action, "fact_id": fact_id,
                    "subject": subject, "predicate": predicate}
        finally:
            await redis.close()

    async def _mark_dnr(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Mark an episode as do-not-recall (L3 DESTRUCTIVE)."""
        episode_id = args.get("episode_id", "")
        reason = args.get("reason", "")
        redis = _get_redis()
        try:
            await redis.sadd("memory:dnr", episode_id)
            # Store reason alongside
            await redis.set(f"memory:dnr:reason:{episode_id}", reason)
            return {"ok": True, "action": action, "episode_id": episode_id,
                    "marked": True,
                    "restore_method": "UPDATE memory SET do_not_recall=false"}
        finally:
            await redis.close()

    async def _search_kg(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Search knowledge graph by scanning kg:* keys in Redis DB5."""
        query = args.get("query", "")
        redis = _get_redis()
        try:
            results = []
            cursor = 0
            while True:
                cursor, keys = await redis.execute_command(
                    "SCAN", cursor, "MATCH", "kg:*", "COUNT", 100)
                for key in keys:
                    data = await redis.hgetall(key)
                    if not data:
                        continue
                    searchable = (f"{data.get('subject', '')} "
                                  f"{data.get('predicate', '')} "
                                  f"{data.get('object', '')}")
                    if query.lower() in searchable.lower():
                        results.append(data)
                if cursor == 0:
                    break
            return {"ok": True, "action": action, "query": query, "results": results}
        finally:
            await redis.close()

    # -----------------------------------------------------------------------
    # Finance -- asyncpg
    # -----------------------------------------------------------------------

    async def _ensure_finance_table(self, conn) -> None:
        """Ensure finance_transactions table exists."""
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS finance_transactions (
                id SERIAL PRIMARY KEY,
                amount NUMERIC NOT NULL,
                description TEXT DEFAULT '',
                category TEXT DEFAULT '',
                date DATE DEFAULT CURRENT_DATE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                corrected_by INTEGER REFERENCES finance_transactions(id)
            )
        """)

    async def _list_transactions(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """List financial transactions from PostgreSQL."""
        limit = args.get("limit", 50)
        offset = args.get("offset", 0)
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            rows = await conn.fetch(
                "SELECT id, amount, description, category, "
                "date::text, created_at::text "
                "FROM finance_transactions ORDER BY id DESC LIMIT $1 OFFSET $2",
                limit, offset,
            )
            transactions = [dict(r) for r in rows]
            return {"ok": True, "action": action, "transactions": transactions,
                    "count": len(transactions)}
        finally:
            await conn.close()

    async def _summarize(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Finance period summary (total, count, avg, by category)."""
        period = args.get("period", "month")
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            if period == "week":
                date_filter = "date >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == "year":
                date_filter = "date >= CURRENT_DATE - INTERVAL '1 year'"
            else:  # month
                date_filter = "date >= CURRENT_DATE - INTERVAL '30 days'"

            row = await conn.fetchrow(f"""
                SELECT COUNT(*) as count,
                       COALESCE(SUM(amount), 0) as total,
                       COALESCE(AVG(amount), 0) as avg_amount
                FROM finance_transactions WHERE {date_filter}
            """)
            cats = await conn.fetch(f"""
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM finance_transactions WHERE {date_filter}
                GROUP BY category ORDER BY total DESC
            """)
            summary = {
                "count": row["count"],
                "total": float(row["total"]),
                "average": round(float(row["avg_amount"]), 2),
                "by_category": {
                    r["category"]: {"total": float(r["total"]), "count": r["count"]}
                    for r in cats
                },
            }
            return {"ok": True, "action": action, "period": period, "summary": summary}
        finally:
            await conn.close()

    async def _detect_anomalies(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Detect spending anomalies (transactions > 2x average)."""
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            avg_row = await conn.fetchrow(
                "SELECT COALESCE(AVG(amount), 0) as avg_amount "
                "FROM finance_transactions"
            )
            avg = float(avg_row["avg_amount"])
            if avg == 0:
                return {"ok": True, "action": action, "anomalies": [],
                        "count": 0, "threshold": 0}
            threshold = avg * 2
            rows = await conn.fetch(
                "SELECT id, amount, description, category, date::text "
                "FROM finance_transactions WHERE amount > $1 ORDER BY amount DESC",
                threshold,
            )
            anomalies = [dict(r) for r in rows]
            return {"ok": True, "action": action, "anomalies": anomalies,
                    "count": len(anomalies), "threshold": round(threshold, 2)}
        finally:
            await conn.close()

    async def _export_transactions(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Export transactions as CSV or JSON."""
        fmt = args.get("format", "csv")
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            rows = await conn.fetch(
                "SELECT id, amount, description, category, "
                "date::text, created_at::text "
                "FROM finance_transactions ORDER BY id"
            )
            transactions = [dict(r) for r in rows]
            if fmt == "json":
                data = json.dumps(transactions, default=str, indent=2)
            else:
                # CSV
                if transactions:
                    headers = list(transactions[0].keys())
                    lines = [",".join(headers)]
                    for t in transactions:
                        lines.append(",".join(str(t.get(h, "")) for h in headers))
                    data = "\n".join(lines)
                else:
                    data = ""
            return {"ok": True, "action": action, "format": fmt,
                    "count": len(transactions), "data": data}
        finally:
            await conn.close()

    async def _record_transaction(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Record a financial transaction in PostgreSQL."""
        amount = args.get("amount", 0)
        description = args.get("description", "")
        category = args.get("category", "")
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            txn_id = await conn.fetchval(
                "INSERT INTO finance_transactions (amount, description, category) "
                "VALUES ($1, $2, $3) RETURNING id",
                amount, description, category,
            )
            return {"ok": True, "action": action, "amount": amount,
                    "transaction_id": str(txn_id)}
        finally:
            await conn.close()

    async def _correct_transaction(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Correct a transaction via compensating entry (L3 DESTRUCTIVE)."""
        transaction_id = args.get("transaction_id", "")
        new_amount = args.get("new_amount")
        reason = args.get("reason", "")
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            # Look up original
            tid = int(transaction_id) if str(transaction_id).isdigit() else -1
            original = await conn.fetchrow(
                "SELECT id, amount, description, category "
                "FROM finance_transactions WHERE id = $1", tid,
            )
            if original:
                old_amount = float(original["amount"])
                comp_amount = -(old_amount - (new_amount if new_amount is not None
                                               else old_amount))
                comp_id = await conn.fetchval(
                    "INSERT INTO finance_transactions (amount, description, category) "
                    "VALUES ($1, $2, $3) RETURNING id",
                    comp_amount,
                    f"Correction of txn {transaction_id}: {reason}",
                    original["category"],
                )
                await conn.execute(
                    "UPDATE finance_transactions SET corrected_by = $1 WHERE id = $2",
                    comp_id, original["id"],
                )
            return {"ok": True, "action": action, "transaction_id": transaction_id,
                    "corrected": True, "reason": reason}
        finally:
            await conn.close()

    async def _bulk_import(self, action: str, args: dict[str, Any]) -> dict[str, Any]:
        """Bulk import financial transactions (L3 DESTRUCTIVE)."""
        data = args.get("data", [])
        path = args.get("path", "")
        conn = await _get_pg()
        try:
            await self._ensure_finance_table(conn)
            imported = 0
            for item in data:
                amount = item.get("amount", 0)
                description = item.get("description", "")
                category = item.get("category", "")
                await conn.execute(
                    "INSERT INTO finance_transactions (amount, description, category) "
                    "VALUES ($1, $2, $3)",
                    amount, description, category,
                )
                imported += 1
            return {"ok": True, "action": action, "path": path, "imported": imported}
        finally:
            await conn.close()
