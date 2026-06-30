"""Tests for MemoryBackend — P6 memory/finance/Notion/Drive/calendar.

REAL actions (12): memory core (redis.asyncio DB5) + finance (asyncpg).
CONFIG_MISSING actions (18): Notion/Drive/Calendar external APIs.

All external clients are MOCKED — no live network calls.
"""
from __future__ import annotations

import json
import pytest
import pytest_asyncio

from guinevere.tools.backends.memory import MemoryBackend


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def backend():
    return MemoryBackend()


# -- Mock Redis -------------------------------------------------------------

class FakeRedisPipeline:
    """Fake pipeline that records commands."""
    def __init__(self):
        self.commands = []
    def zadd(self, key, mapping):
        self.commands.append(("zadd", key, mapping))
        return self
    def hset(self, key, mapping=None, **kwargs):
        self.commands.append(("hset", key, mapping or kwargs))
        return self
    def set(self, key, value):
        self.commands.append(("set", key, value))
        return self
    def sadd(self, key, *values):
        self.commands.append(("sadd", key, values))
        return self
    async def execute(self):
        return [True] * len(self.commands)


class FakeRedis:
    """Fake redis.asyncio client for testing."""
    def __init__(self):
        self.store: dict[str, str] = {}
        self.sets: dict[str, set] = {}
        self.sorted_sets: dict[str, list] = {}
        self.hashes: dict[str, dict] = {}
        self._pipeline = None

    def pipeline(self, transaction=True):
        self._pipeline = FakeRedisPipeline()
        return self._pipeline

    async def execute_command(self, *args, **kwargs):
        # Handle SCAN commands for search_kg
        if args and args[0] == "SCAN":
            pattern = ""
            for i, a in enumerate(args):
                if a == "MATCH" and i + 1 < len(args):
                    pattern = args[i + 1]
                    break
            matched = []
            if pattern:
                prefix = pattern.replace("*", "")
                for key in list(self.hashes.keys()):
                    if key.startswith(prefix):
                        matched.append(key)
            return (0, matched)  # cursor=0 means done
        return []

    async def zadd(self, key, mapping):
        self.sorted_sets.setdefault(key, []).extend(mapping.items())
        return len(mapping)

    async def zrangebyscore(self, key, min_score, max_score, start=None, num=None, withscores=False):
        entries = self.sorted_sets.get(key, [])
        if start is not None and num is not None:
            entries = entries[start:start + num]
        # Real redis returns just members by default; tuples only with withscores=True
        if withscores:
            return entries
        return [e[0] if isinstance(e, (list, tuple)) else e for e in entries]

    async def hset(self, key, mapping=None, **kwargs):
        d = mapping or kwargs
        self.hashes.setdefault(key, {}).update(d)
        return len(d)

    async def hgetall(self, key):
        return self.hashes.get(key, {})

    async def set(self, key, value):
        self.store[key] = value
        return True

    async def get(self, key):
        return self.store.get(key)

    async def sadd(self, key, *values):
        self.sets.setdefault(key, set()).update(values)
        return len(values)

    async def smembers(self, key):
        return self.sets.get(key, set())

    async def sismember(self, key, value):
        return value in self.sets.get(key, set())

    async def close(self):
        pass


class FakeRedisFactory:
    """Creates FakeRedis instances via from_url()."""
    def __init__(self):
        self._instance = None
    def from_url(self, url, **kwargs):
        if self._instance is None:
            self._instance = FakeRedis()
        return self._instance


# -- Mock asyncpg -----------------------------------------------------------

class FakePGConnection:
    """Fake asyncpg connection for testing."""
    def __init__(self):
        self.tables: dict[str, list[dict]] = {
            "finance_transactions": [],
        }
        self._next_id = 1

    async def execute(self, sql, *args):
        # CREATE TABLE / DDL
        if sql.strip().upper().startswith("CREATE"):
            return "CREATE TABLE"
        # INSERT
        if sql.strip().upper().startswith("INSERT"):
            return "INSERT 0 1"
        # UPDATE
        if sql.strip().upper().startswith("UPDATE"):
            return "UPDATE 0"
        return "OK"

    async def fetch(self, sql, *args):
        if "finance_transactions" in sql:
            rows = self.tables["finance_transactions"]
            sql_upper = sql.upper()
            # GROUP BY category
            if "GROUP BY" in sql_upper:
                cats: dict = {}
                for r in rows:
                    cat = r.get("category", "")
                    if cat not in cats:
                        cats[cat] = {"category": cat, "total": 0.0, "count": 0}
                    cats[cat]["total"] += float(r.get("amount", 0))
                    cats[cat]["count"] += 1
                return list(cats.values())
            return [dict(row) for row in rows]
        return []

    async def fetchrow(self, sql, *args):
        # Handle aggregate queries (COUNT, SUM, AVG)
        if "finance_transactions" in sql:
            rows = self.tables["finance_transactions"]
            sql_upper = sql.upper()
            if "COUNT" in sql_upper or "SUM" in sql_upper or "AVG" in sql_upper:
                count = len(rows)
                total = sum(float(r.get("amount", 0)) for r in rows)
                avg = total / count if count > 0 else 0.0
                return {"count": count, "total": total, "avg_amount": avg}
            if rows:
                return dict(rows[0])
        return None

    async def fetchval(self, sql, *args):
        if "COUNT" in sql.upper():
            return len(self.tables.get("finance_transactions", []))
        return self._next_id

    async def close(self):
        pass


class FakePGFactory:
    """Creates FakePGConnection instances via connect()."""
    def __init__(self):
        self._instance = None
    async def connect(self, dsn=None, **kwargs):
        if self._instance is None:
            self._instance = FakePGConnection()
        return self._instance


# ---------------------------------------------------------------------------
# Action catalogue tests
# ---------------------------------------------------------------------------

class TestActionCatalogue:
    def test_name(self, backend):
        assert backend.name == "memory"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    def test_action_count(self, backend):
        actions = backend.actions()
        assert len(actions) == 30

    def test_action_names_unique(self, backend):
        names = [a.name for a in backend.actions()]
        assert len(names) == len(set(names))

    def test_has_memory_core_actions(self, backend):
        names = {a.name for a in backend.actions()}
        for a in ("recall", "store", "store_fact", "mark_dnr", "search_kg"):
            assert a in names, f"missing memory core action: {a}"

    def test_has_finance_actions(self, backend):
        names = {a.name for a in backend.actions()}
        for a in ("list_transactions", "summarize", "detect_anomalies",
                   "export_transactions", "record_transaction",
                   "correct_transaction", "bulk_import"):
            assert a in names, f"missing finance action: {a}"

    def test_has_notion_actions(self, backend):
        names = {a.name for a in backend.actions()}
        for a in ("retrieve_page", "search_notes", "create_page",
                   "update_page", "append_blocks", "archive_page"):
            assert a in names, f"missing notion action: {a}"

    def test_has_drive_actions(self, backend):
        names = {a.name for a in backend.actions()}
        for a in ("list_files", "get_file", "create_file", "update_file",
                   "trash_file", "delete_file", "public_share"):
            assert a in names, f"missing drive action: {a}"

    def test_has_calendar_actions(self, backend):
        names = {a.name for a in backend.actions()}
        for a in ("list_events", "get_event", "create_event",
                   "update_event", "delete_event"):
            assert a in names, f"missing calendar action: {a}"

    def test_find_action(self, backend):
        assert backend.find_action("recall") is not None
        assert backend.find_action("nonexistent") is None

    def test_l3_destructive_actions(self, backend):
        l3 = [a.name for a in backend.actions() if a.label.value == "L3"]
        assert "mark_dnr" in l3
        assert "correct_transaction" in l3
        assert "bulk_import" in l3
        assert "delete_event" in l3
        assert "archive_page" in l3
        assert "delete_file" in l3
        assert "public_share" in l3


# ---------------------------------------------------------------------------
# Memory core — REAL actions (redis.asyncio DB5 mocked)
# ---------------------------------------------------------------------------

class TestMemoryCoreReal:
    """Tests for recall, store, store_fact, mark_dnr, search_kg."""

    @pytest.fixture
    def fake_redis_factory(self, monkeypatch):
        factory = FakeRedisFactory()
        import guinevere.tools.backends.memory as mod
        monkeypatch.setattr(mod, "_get_redis", lambda: factory.from_url("redis://localhost/5"))
        return factory

    @pytest.mark.asyncio
    async def test_recall_returns_results(self, backend, fake_redis_factory):
        redis = fake_redis_factory.from_url("redis://localhost/5")
        # Seed sorted set with an episode
        redis.sorted_sets["memory:episodes"] = [
            ("ep:1", 1000.0),
        ]
        redis.hashes["ep:1"] = {"content": "I love cats", "tags": json.dumps(["animals"])}

        result = await backend.dispatch("recall", {"query": "cats", "limit": 5})
        assert result["ok"] is True
        assert result["action"] == "recall"
        assert result["query"] == "cats"
        assert isinstance(result["results"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_recall_fail_soft_on_error(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        def boom():
            raise ConnectionError("redis down")
        monkeypatch.setattr(mod, "_get_redis", boom)
        result = await backend.dispatch("recall", {"query": "test"})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_store_creates_episode(self, backend, fake_redis_factory):
        result = await backend.dispatch("store", {"content": "The sky is blue", "tags": ["nature"]})
        assert result["ok"] is True
        assert result["action"] == "store"
        assert "episode_id" in result
        assert result["episode_id"] != ""
        assert result["content_len"] == len("The sky is blue")

    @pytest.mark.asyncio
    async def test_store_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        def boom():
            raise OSError("disk full")
        monkeypatch.setattr(mod, "_get_redis", boom)
        result = await backend.dispatch("store", {"content": "x"})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_store_fact_creates_fact(self, backend, fake_redis_factory):
        result = await backend.dispatch("store_fact", {
            "subject": "user", "predicate": "likes", "object": "coffee",
        })
        assert result["ok"] is True
        assert result["action"] == "store_fact"
        assert "fact_id" in result
        assert result["fact_id"] != ""
        assert result["subject"] == "user"
        assert result["predicate"] == "likes"

    @pytest.mark.asyncio
    async def test_store_fact_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        def boom():
            raise ConnectionRefusedError("no redis")
        monkeypatch.setattr(mod, "_get_redis", boom)
        result = await backend.dispatch("store_fact", {"subject": "a", "predicate": "b", "object": "c"})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_mark_dnr_sets_flag(self, backend, fake_redis_factory):
        redis = fake_redis_factory.from_url("redis://localhost/5")
        # First store an episode so it exists
        await backend.dispatch("store", {"content": "secret data"})
        # Pick up an episode_id from a fresh store
        result = await backend.dispatch("store", {"content": "test ep"})
        ep_id = result["episode_id"]

        result = await backend.dispatch("mark_dnr", {"episode_id": ep_id, "reason": "privacy"})
        assert result["ok"] is True
        assert result["marked"] is True
        assert result["episode_id"] == ep_id

    @pytest.mark.asyncio
    async def test_mark_dnr_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        def boom():
            raise RuntimeError("broken")
        monkeypatch.setattr(mod, "_get_redis", boom)
        result = await backend.dispatch("mark_dnr", {"episode_id": "x"})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_search_kg_returns_results(self, backend, fake_redis_factory):
        redis = fake_redis_factory.from_url("redis://localhost/5")
        redis.hashes["kg:user:likes"] = {"subject": "user", "predicate": "likes", "object": "coffee"}

        result = await backend.dispatch("search_kg", {"query": "user likes"})
        assert result["ok"] is True
        assert result["action"] == "search_kg"
        assert isinstance(result["results"], list)

    @pytest.mark.asyncio
    async def test_search_kg_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        def boom():
            raise TimeoutError("redis timeout")
        monkeypatch.setattr(mod, "_get_redis", boom)
        result = await backend.dispatch("search_kg", {"query": "x"})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Finance — REAL actions (asyncpg mocked)
# ---------------------------------------------------------------------------

class TestFinanceReal:
    """Tests for all 7 finance actions via asyncpg."""

    @pytest.fixture
    def fake_pg_factory(self, monkeypatch):
        factory = FakePGFactory()
        import guinevere.tools.backends.memory as mod
        monkeypatch.setattr(mod, "_get_pg", lambda: factory.connect())
        return factory

    @pytest.mark.asyncio
    async def test_list_transactions_empty(self, backend, fake_pg_factory):
        result = await backend.dispatch("list_transactions", {})
        assert result["ok"] is True
        assert result["action"] == "list_transactions"
        assert isinstance(result["transactions"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_list_transactions_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise ConnectionError("pg down")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("list_transactions", {})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_summarize(self, backend, fake_pg_factory):
        result = await backend.dispatch("summarize", {"period": "month"})
        assert result["ok"] is True
        assert result["action"] == "summarize"
        assert result["period"] == "month"
        assert isinstance(result["summary"], dict)

    @pytest.mark.asyncio
    async def test_summarize_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise OSError("pg gone")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("summarize", {"period": "week"})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_detect_anomalies(self, backend, fake_pg_factory):
        result = await backend.dispatch("detect_anomalies", {})
        assert result["ok"] is True
        assert result["action"] == "detect_anomalies"
        assert isinstance(result["anomalies"], list)
        assert result["count"] >= 0

    @pytest.mark.asyncio
    async def test_detect_anomalies_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise RuntimeError("broken pg")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("detect_anomalies", {})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_export_transactions_csv(self, backend, fake_pg_factory):
        result = await backend.dispatch("export_transactions", {"format": "csv"})
        assert result["ok"] is True
        assert result["action"] == "export_transactions"
        assert result["format"] == "csv"

    @pytest.mark.asyncio
    async def test_export_transactions_json(self, backend, fake_pg_factory):
        result = await backend.dispatch("export_transactions", {"format": "json"})
        assert result["ok"] is True
        assert result["format"] == "json"

    @pytest.mark.asyncio
    async def test_export_transactions_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise ConnectionError("no pg")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("export_transactions", {"format": "csv"})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_record_transaction(self, backend, fake_pg_factory):
        result = await backend.dispatch("record_transaction", {
            "amount": 42.50, "description": "coffee", "category": "food",
        })
        assert result["ok"] is True
        assert result["action"] == "record_transaction"
        assert result["amount"] == 42.50
        assert "transaction_id" in result

    @pytest.mark.asyncio
    async def test_record_transaction_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise OSError("disk full")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("record_transaction", {"amount": 10})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_correct_transaction(self, backend, fake_pg_factory):
        result = await backend.dispatch("correct_transaction", {
            "transaction_id": "txn_001", "new_amount": 35.00, "reason": "typo",
        })
        assert result["ok"] is True
        assert result["action"] == "correct_transaction"
        assert result["transaction_id"] == "txn_001"
        assert result["corrected"] is True

    @pytest.mark.asyncio
    async def test_correct_transaction_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise ConnectionError("pg unreachable")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("correct_transaction", {"transaction_id": "x"})
        assert result["ok"] is False

    @pytest.mark.asyncio
    async def test_bulk_import(self, backend, fake_pg_factory):
        # Provide inline data instead of file
        result = await backend.dispatch("bulk_import", {
            "data": [
                {"amount": 10, "description": "a"},
                {"amount": 20, "description": "b"},
            ],
        })
        assert result["ok"] is True
        assert result["action"] == "bulk_import"
        assert result["imported"] >= 0

    @pytest.mark.asyncio
    async def test_bulk_import_fail_soft(self, backend, monkeypatch):
        import guinevere.tools.backends.memory as mod
        async def boom():
            raise RuntimeError("pg exploded")
        monkeypatch.setattr(mod, "_get_pg", boom)
        result = await backend.dispatch("bulk_import", {"data": [{"amount": 1}]})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# CONFIG_MISSING — Notion (6 actions)
# ---------------------------------------------------------------------------

class TestNotionConfigMissing:
    @pytest.mark.asyncio
    async def test_retrieve_page_config_missing(self, backend):
        result = await backend.dispatch("retrieve_page", {"page_id": "abc"})
        assert result["ok"] is False
        assert result["config_missing"] is True
        assert "Notion" in result["error"]

    @pytest.mark.asyncio
    async def test_search_notes_config_missing(self, backend):
        result = await backend.dispatch("search_notes", {"query": "test"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_create_page_config_missing(self, backend):
        result = await backend.dispatch("create_page", {"title": "New Page"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_update_page_config_missing(self, backend):
        result = await backend.dispatch("update_page", {"page_id": "abc"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_append_blocks_config_missing(self, backend):
        result = await backend.dispatch("append_blocks", {"page_id": "abc"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_archive_page_config_missing(self, backend):
        result = await backend.dispatch("archive_page", {"page_id": "abc"})
        assert result["ok"] is False
        assert result["config_missing"] is True


# ---------------------------------------------------------------------------
# CONFIG_MISSING — Drive (7 actions)
# ---------------------------------------------------------------------------

class TestDriveConfigMissing:
    @pytest.mark.asyncio
    async def test_list_files_config_missing(self, backend):
        result = await backend.dispatch("list_files", {})
        assert result["ok"] is False
        assert result["config_missing"] is True
        assert "Drive" in result["error"]

    @pytest.mark.asyncio
    async def test_get_file_config_missing(self, backend):
        result = await backend.dispatch("get_file", {"file_id": "fid"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_create_file_config_missing(self, backend):
        result = await backend.dispatch("create_file", {"name": "doc.txt"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_update_file_config_missing(self, backend):
        result = await backend.dispatch("update_file", {"file_id": "fid"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_trash_file_config_missing(self, backend):
        result = await backend.dispatch("trash_file", {"file_id": "fid"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_delete_file_config_missing(self, backend):
        result = await backend.dispatch("delete_file", {"file_id": "fid"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_public_share_config_missing(self, backend):
        result = await backend.dispatch("public_share", {"file_id": "fid"})
        assert result["ok"] is False
        assert result["config_missing"] is True


# ---------------------------------------------------------------------------
# CONFIG_MISSING — Calendar (5 actions)
# ---------------------------------------------------------------------------

class TestCalendarConfigMissing:
    @pytest.mark.asyncio
    async def test_list_events_config_missing(self, backend):
        result = await backend.dispatch("list_events", {})
        assert result["ok"] is False
        assert result["config_missing"] is True
        assert "calendar" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_get_event_config_missing(self, backend):
        result = await backend.dispatch("get_event", {"event_id": "evt1"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_create_event_config_missing(self, backend):
        result = await backend.dispatch("create_event", {"title": "Meeting"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_update_event_config_missing(self, backend):
        result = await backend.dispatch("update_event", {"event_id": "evt1"})
        assert result["ok"] is False
        assert result["config_missing"] is True

    @pytest.mark.asyncio
    async def test_delete_event_config_missing(self, backend):
        result = await backend.dispatch("delete_event", {"event_id": "evt1"})
        assert result["ok"] is False
        assert result["config_missing"] is True


# ---------------------------------------------------------------------------
# Fail-soft + unknown action
# ---------------------------------------------------------------------------

class TestFailSoft:
    @pytest.mark.asyncio
    async def test_unknown_action_returns_error(self, backend):
        result = await backend.dispatch("nonexistent_action_xyz", {})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_dispatch_never_raises(self, backend):
        """dispatch() must NEVER raise to caller — always return dict."""
        # Even with completely wrong args, it must return a dict
        result = await backend.dispatch("recall", {"bad_key": [1, 2, 3]})
        assert isinstance(result, dict)
        assert "ok" in result

    @pytest.mark.asyncio
    async def test_all_actions_return_dict(self, backend):
        """Every action must return a dict with 'ok' key."""
        for action in backend.actions():
            result = await backend.dispatch(action.name, {})
            assert isinstance(result, dict), f"{action.name} did not return dict"
            assert "ok" in result, f"{action.name} missing 'ok' key"
