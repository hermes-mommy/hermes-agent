"""Tests for MCP Redis tool — command classification, auth levels, DB allocation, TTL."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.mcp.auth import ForbiddenOperationError  # noqa: E402
from src.mcp.tools.redis_tool import (  # noqa: E402
    COMMAND_CLASSIFICATION,
    DB_ALLOCATION,
    DESTRUCTIVE_COMMANDS,
    FORBIDDEN_COMMANDS,
    READ_COMMANDS,
    WRITE_COMMANDS,
    _connect,
    _DEFAULT_DB,
    redis_del,
    redis_flushall,
    redis_flushdb,
    redis_get,
    redis_hgetall,
    redis_hset,
    redis_keys,
    redis_lrange,
    redis_set,
    register_tools,
)


# ============================================================================
# Helpers
# ============================================================================


def _mock_client() -> AsyncMock:
    """Return an ``AsyncMock`` simulating a ``redis.asyncio.Redis`` client."""
    client = AsyncMock()
    client.aclose = AsyncMock()
    return client


async def _approved_redis_del(keys: str) -> int:
    """Run ``redis_del`` with destructive approval granted for Redis tests."""
    with patch("src.mcp.auth._wait_for_approval", return_value=True):
        return await redis_del(keys)


# ============================================================================
# TestCommandClassification
# ============================================================================


class TestCommandClassification:
    """Verify command classification dictionaries are correct and non-overlapping."""

    def test_read_commands_present(self) -> None:
        """READ commands include GET, LRANGE, HGET, HGETALL, KEYS, SCAN."""
        assert "GET" in READ_COMMANDS
        assert "LRANGE" in READ_COMMANDS
        assert "HGET" in READ_COMMANDS
        assert "HGETALL" in READ_COMMANDS
        assert "KEYS" in READ_COMMANDS
        assert "SCAN" in READ_COMMANDS

    def test_write_commands_present(self) -> None:
        """WRITE commands include SET, HSET, LPUSH, RPUSH, SADD."""
        assert "SET" in WRITE_COMMANDS
        assert "HSET" in WRITE_COMMANDS
        assert "LPUSH" in WRITE_COMMANDS
        assert "RPUSH" in WRITE_COMMANDS
        assert "SADD" in WRITE_COMMANDS

    def test_destructive_commands_include_del(self) -> None:
        """DEL is classified as DESTRUCTIVE."""
        assert "DEL" in DESTRUCTIVE_COMMANDS

    def test_forbidden_commands_include_flush(self) -> None:
        """FLUSHALL and FLUSHDB are both FORBIDDEN."""
        assert "FLUSHALL" in FORBIDDEN_COMMANDS
        assert "FLUSHDB" in FORBIDDEN_COMMANDS

    def test_no_overlap_between_categories(self) -> None:
        """No command appears in more than one classification set."""
        all_sets = [READ_COMMANDS, WRITE_COMMANDS, DESTRUCTIVE_COMMANDS, FORBIDDEN_COMMANDS]
        total = sum(len(s) for s in all_sets)
        combined = READ_COMMANDS | WRITE_COMMANDS | DESTRUCTIVE_COMMANDS | FORBIDDEN_COMMANDS
        assert len(combined) == total

    def test_classification_dict_completeness(self) -> None:
        """COMMAND_CLASSIFICATION maps every command to exactly one level."""
        expected_count = (
            len(READ_COMMANDS)
            + len(WRITE_COMMANDS)
            + len(DESTRUCTIVE_COMMANDS)
            + len(FORBIDDEN_COMMANDS)
        )
        assert len(COMMAND_CLASSIFICATION) == expected_count
        for cmd in READ_COMMANDS:
            assert COMMAND_CLASSIFICATION[cmd] == "read"
        for cmd in WRITE_COMMANDS:
            assert COMMAND_CLASSIFICATION[cmd] == "write"
        for cmd in DESTRUCTIVE_COMMANDS:
            assert COMMAND_CLASSIFICATION[cmd] == "destructive"
        for cmd in FORBIDDEN_COMMANDS:
            assert COMMAND_CLASSIFICATION[cmd] == "forbidden"


# ============================================================================
# TestDBAllocation
# ============================================================================


class TestDBAllocation:
    """Verify DB allocation map is complete and correct."""

    def test_all_six_dbs_present(self) -> None:
        """DB0 through DB5 are all mapped."""
        for db in range(6):
            assert db in DB_ALLOCATION

    def test_db5_is_cost_tracking(self) -> None:
        """DB5 is the cost tracking namespace."""
        assert DB_ALLOCATION[5] == "Cost tracking"

    def test_db0_is_session_cache(self) -> None:
        """DB0 is the session cache namespace."""
        assert DB_ALLOCATION[0] == "Session cache"

    def test_db2_is_surveillance(self) -> None:
        """DB2 is the surveillance buffer."""
        assert DB_ALLOCATION[2] == "Surveillance buffer"

    def test_default_db_is_5(self) -> None:
        """The module default DB constant is 5 (cost tracking)."""
        assert _DEFAULT_DB == 5


# ============================================================================
# TestConnect
# ============================================================================


class TestConnect:
    """Verify ``_connect`` factory uses correct connection parameters."""

    def test_default_db(self) -> None:
        """Default DB is 5 when not specified."""
        with patch("src.mcp.tools.redis_tool.aioredis.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()
            with patch.dict("os.environ", {"REDIS_PASSWORD": "test_pw"}, clear=False):
                _connect()
            mock_redis.assert_called_once_with(
                host="localhost",
                port=6380,
                db=5,
                username="guinevere_core",
                password="test_pw",
                decode_responses=True,
            )

    def test_custom_db(self) -> None:
        """Custom DB number is passed through."""
        with patch("src.mcp.tools.redis_tool.aioredis.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()
            with patch.dict("os.environ", {"REDIS_PASSWORD": "pw"}, clear=False):
                _connect(db=2)
            mock_redis.assert_called_once_with(
                host="localhost",
                port=6380,
                db=2,
                username="guinevere_core",
                password="pw",
                decode_responses=True,
            )

    def test_password_from_env(self) -> None:
        """Password is read from REDIS_PASSWORD env var."""
        with patch("src.mcp.tools.redis_tool.aioredis.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()
            with patch.dict("os.environ", {"REDIS_PASSWORD": "secret123"}, clear=False):
                _connect()
            _, kwargs = mock_redis.call_args
            assert kwargs["password"] == "secret123"

    def test_port_is_6380(self) -> None:
        """Non-standard port 6380 is used."""
        with patch("src.mcp.tools.redis_tool.aioredis.Redis") as mock_redis:
            mock_redis.return_value = MagicMock()
            with patch.dict("os.environ", {}, clear=False):
                _connect()
            _, kwargs = mock_redis.call_args
            assert kwargs["port"] == 6380


# ============================================================================
# TestRedisGet — READ_AUTO
# ============================================================================


class TestRedisGet:
    """Tests for ``redis_get`` — READ_AUTO auth level."""

    def test_get_existing_key(self) -> None:
        """Returns string value for existing key."""
        client = _mock_client()
        client.get = AsyncMock(return_value="hello")
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_get("my_key"))
        assert result == "hello"

    def test_get_missing_key_returns_none(self) -> None:
        """Returns None when key does not exist."""
        client = _mock_client()
        client.get = AsyncMock(return_value=None)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_get("missing"))
        assert result is None

    def test_get_uses_correct_db(self) -> None:
        """DB parameter is forwarded to _connect."""
        client = _mock_client()
        client.get = AsyncMock(return_value="val")
        with patch("src.mcp.tools.redis_tool._connect", return_value=client) as mock_conn:
            asyncio.run(redis_get("key", db=2))
        mock_conn.assert_called_once_with(2)

    def test_get_default_db_is_5(self) -> None:
        """Default DB is 5 when not specified."""
        client = _mock_client()
        client.get = AsyncMock(return_value="val")
        with patch("src.mcp.tools.redis_tool._connect", return_value=client) as mock_conn:
            asyncio.run(redis_get("key"))
        mock_conn.assert_called_once_with(5)

    def test_get_closes_client(self) -> None:
        """Client is always closed after operation."""
        client = _mock_client()
        client.get = AsyncMock(return_value="val")
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_get("key"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisKeys — READ_AUTO
# ============================================================================


class TestRedisKeys:
    """Tests for ``redis_keys`` — READ_AUTO auth level."""

    def test_keys_default_pattern(self) -> None:
        """Default pattern is '*' (all keys)."""
        client = _mock_client()
        client.keys = AsyncMock(return_value=["a", "b", "c"])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_keys())
        assert result == ["a", "b", "c"]

    def test_keys_custom_pattern(self) -> None:
        """Custom glob pattern filters keys."""
        client = _mock_client()
        client.keys = AsyncMock(return_value=["cost:day:1", "cost:day:2"])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_keys("cost:day:*"))
        assert len(result) == 2

    def test_keys_empty_result(self) -> None:
        """Empty list when no keys match."""
        client = _mock_client()
        client.keys = AsyncMock(return_value=[])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_keys("nonexistent*"))
        assert result == []

    def test_keys_closes_client(self) -> None:
        """Client is closed after keys scan."""
        client = _mock_client()
        client.keys = AsyncMock(return_value=[])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_keys())
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisHgetall — READ_AUTO
# ============================================================================


class TestRedisHgetall:
    """Tests for ``redis_hgetall`` — READ_AUTO auth level."""

    def test_hgetall_existing_hash(self) -> None:
        """Returns dict of field-value pairs."""
        client = _mock_client()
        client.hgetall = AsyncMock(return_value={"name": "guinevere", "role": "mama"})
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_hgetall("user:1"))
        assert result == {"name": "guinevere", "role": "mama"}

    def test_hgetall_missing_key(self) -> None:
        """Returns empty dict for non-existent key."""
        client = _mock_client()
        client.hgetall = AsyncMock(return_value={})
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_hgetall("nonexistent"))
        assert result == {}

    def test_hgetall_closes_client(self) -> None:
        """Client is closed after hgetall."""
        client = _mock_client()
        client.hgetall = AsyncMock(return_value={})
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_hgetall("key"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisLrange — READ_AUTO
# ============================================================================


class TestRedisLrange:
    """Tests for ``redis_lrange`` — READ_AUTO auth level."""

    def test_lrange_full_list(self) -> None:
        """Returns all elements when start=0, stop=-1."""
        client = _mock_client()
        client.lrange = AsyncMock(return_value=["a", "b", "c"])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_lrange("my_list"))
        assert result == ["a", "b", "c"]

    def test_lrange_partial(self) -> None:
        """Returns subset with custom start/stop."""
        client = _mock_client()
        client.lrange = AsyncMock(return_value=["b"])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_lrange("my_list", start=1, stop=1))
        assert result == ["b"]

    def test_lrange_empty_list(self) -> None:
        """Returns empty list for non-existent key."""
        client = _mock_client()
        client.lrange = AsyncMock(return_value=[])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_lrange("empty"))
        assert result == []

    def test_lrange_closes_client(self) -> None:
        """Client is closed after lrange."""
        client = _mock_client()
        client.lrange = AsyncMock(return_value=[])
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_lrange("key"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisSet — WRITE_NOTIFY
# ============================================================================


class TestRedisSet:
    """Tests for ``redis_set`` — WRITE_NOTIFY auth level."""

    def test_set_without_ttl(self) -> None:
        """Sets key without TTL using plain SET."""
        client = _mock_client()
        client.set = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_set("k", "v"))
        assert result is True
        client.set.assert_awaited_once_with("k", "v")
        client.setex.assert_not_awaited()

    def test_set_with_ttl(self) -> None:
        """Sets key with TTL using SETEX."""
        client = _mock_client()
        client.setex = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_set("k", "v", ttl=300))
        assert result is True
        client.setex.assert_awaited_once_with("k", 300, "v")
        client.set.assert_not_awaited()

    def test_set_ttl_zero(self) -> None:
        """TTL of 0 uses SETEX with zero TTL."""
        client = _mock_client()
        client.setex = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_set("k", "v", ttl=0))
        assert result is True
        client.setex.assert_awaited_once_with("k", 0, "v")

    def test_set_uses_correct_db(self) -> None:
        """DB parameter is forwarded to _connect."""
        client = _mock_client()
        client.set = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client) as mock_conn:
            asyncio.run(redis_set("k", "v", db=1))
        mock_conn.assert_called_once_with(1)

    def test_set_closes_client(self) -> None:
        """Client is closed after set."""
        client = _mock_client()
        client.set = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_set("k", "v"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisHset — WRITE_NOTIFY
# ============================================================================


class TestRedisHset:
    """Tests for ``redis_hset`` — WRITE_NOTIFY auth level."""

    def test_hset_new_field(self) -> None:
        """Returns True when field is newly created."""
        client = _mock_client()
        client.hset = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_hset("hash_key", "field1", "value1"))
        assert result is True

    def test_hset_existing_field(self) -> None:
        """Returns False when field already existed (updated)."""
        client = _mock_client()
        client.hset = AsyncMock(return_value=False)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_hset("hash_key", "field1", "updated"))
        assert result is False

    def test_hset_closes_client(self) -> None:
        """Client is closed after hset."""
        client = _mock_client()
        client.hset = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(redis_hset("key", "f", "v"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisDel — DESTRUCTIVE_APPROVAL
# ============================================================================


class TestRedisDel:
    """Tests for ``redis_del`` — DESTRUCTIVE_APPROVAL auth level."""

    def test_del_single_key(self) -> None:
        """Deletes a single key and returns count."""
        client = _mock_client()
        client.delete = AsyncMock(return_value=1)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(_approved_redis_del("my_key"))
        assert result == 1

    def test_del_multiple_keys(self) -> None:
        """Deletes multiple space-separated keys."""
        client = _mock_client()
        client.delete = AsyncMock(return_value=2)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(_approved_redis_del("key1 key2"))
        assert result == 2

    def test_del_nonexistent_key(self) -> None:
        """Returns 0 when key does not exist."""
        client = _mock_client()
        client.delete = AsyncMock(return_value=0)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(_approved_redis_del("ghost"))
        assert result == 0

    def test_del_closes_client(self) -> None:
        """Client is closed after delete."""
        client = _mock_client()
        client.delete = AsyncMock(return_value=1)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            asyncio.run(_approved_redis_del("key"))
        client.aclose.assert_awaited_once()


# ============================================================================
# TestRedisFlushdb — FORBIDDEN
# ============================================================================


class TestRedisFlushdb:
    """Tests for ``redis_flushdb`` — FORBIDDEN, always blocked."""

    def test_flushdb_raises_forbidden(self) -> None:
        """FLUSHDB always raises ForbiddenOperationError."""
        with pytest.raises(ForbiddenOperationError, match="FLUSHDB"):
            asyncio.run(redis_flushdb())

    def test_flushdb_with_db_arg_raises(self) -> None:
        """FLUSHDB with explicit db argument is still forbidden."""
        with pytest.raises(ForbiddenOperationError):
            asyncio.run(redis_flushdb(db=0))

    def test_flushdb_is_forbidden_operation(self) -> None:
        """FLUSHDB is in the FORBIDDEN_COMMANDS set."""
        assert "FLUSHDB" in FORBIDDEN_COMMANDS

    def test_flushdb_classified_as_forbidden(self) -> None:
        """FLUSHDB is classified as forbidden in COMMAND_CLASSIFICATION."""
        assert COMMAND_CLASSIFICATION["FLUSHDB"] == "forbidden"


# ============================================================================
# TestRedisFlushall — FORBIDDEN
# ============================================================================


class TestRedisFlushall:
    """Tests for ``redis_flushall`` — FORBIDDEN, always blocked."""

    def test_flushall_raises_forbidden(self) -> None:
        """FLUSHALL always raises ForbiddenOperationError."""
        with pytest.raises(ForbiddenOperationError, match="FLUSHALL"):
            asyncio.run(redis_flushall())

    def test_flushall_is_forbidden_operation(self) -> None:
        """FLUSHALL is in the FORBIDDEN_COMMANDS set."""
        assert "FLUSHALL" in FORBIDDEN_COMMANDS

    def test_flushall_classified_as_forbidden(self) -> None:
        """FLUSHALL is classified as forbidden in COMMAND_CLASSIFICATION."""
        assert COMMAND_CLASSIFICATION["FLUSHALL"] == "forbidden"


# ============================================================================
# TestAuthLevels
# ============================================================================


class TestAuthLevels:
    """Verify auth levels for each registered tool via decorator application."""

    def test_read_auto_functions_execute(self) -> None:
        """READ_AUTO functions execute immediately without Discord."""
        client = _mock_client()
        client.get = AsyncMock(return_value="ok")
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_get("key"))
        assert result == "ok"

    def test_write_notify_functions_execute(self) -> None:
        """WRITE_NOTIFY functions execute (notification is fire-and-forget)."""
        client = _mock_client()
        client.set = AsyncMock(return_value=True)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(redis_set("k", "v"))
        assert result is True

    def test_destructive_functions_execute(self) -> None:
        """DESTRUCTIVE_APPROVAL functions execute (approval happens in decorator)."""
        client = _mock_client()
        client.delete = AsyncMock(return_value=1)
        with patch("src.mcp.tools.redis_tool._connect", return_value=client):
            result = asyncio.run(_approved_redis_del("key"))
        assert result == 1

    def test_forbidden_functions_raise(self) -> None:
        """FORBIDDEN functions always raise ForbiddenOperationError."""
        with pytest.raises(ForbiddenOperationError):
            asyncio.run(redis_flushall())
        with pytest.raises(ForbiddenOperationError):
            asyncio.run(redis_flushdb())


# ============================================================================
# TestRegisterTools
# ============================================================================


class TestRegisterTools:
    """Smoke test for ``register_tools`` entry-point."""

    def test_registers_nine_tools(self) -> None:
        """``register_tools`` calls ``mcp.tool()`` exactly 9 times."""
        mock_mcp = MagicMock()
        register_tools(mock_mcp)
        assert mock_mcp.tool.call_count == 9

    def test_register_tools_returns_none(self) -> None:
        """``register_tools`` returns ``None``."""
        mock_mcp = MagicMock()
        result = register_tools(mock_mcp)
        assert result is None


# ============================================================================
# TestForbiddenOperationError
# ============================================================================


class TestForbiddenOperationError:
    """Tests for the ``ForbiddenOperationError`` exception in redis context."""

    def test_is_exception_subclass(self) -> None:
        """``ForbiddenOperationError`` is a subclass of ``Exception``."""
        assert issubclass(ForbiddenOperationError, Exception)

    def test_message_preserved(self) -> None:
        """Exception message is preserved."""
        msg = "FLUSHALL is forbidden"
        exc = ForbiddenOperationError(msg)
        assert str(exc) == msg
