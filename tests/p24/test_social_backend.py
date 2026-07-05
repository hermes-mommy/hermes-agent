"""Tests for guinevere.tools.backends.social — SocialBackend.

TDD RED phase: one test per action, all httpx calls mocked.
NO live external API/network calls.

7 actions: post_x, read_mentions, reply_x, send_telegram,
get_telegram_updates, edit_telegram, delete_telegram.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

pytestmark = pytest.mark.social


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def backend():
    """Import and instantiate SocialBackend."""
    from guinevere.tools.backends.social import SocialBackend
    return SocialBackend()


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    """Ensure env vars are clean for each test."""
    for key in [
        "X_POSTER_X_API_KEY", "X_POSTER_X_API_SECRET",
        "X_POSTER_X_OAUTH1_ACCESS_TOKEN", "X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET",
        "X_POSTER_X_ACCESS_TOKEN", "TELEGRAM_BOT_TOKEN",
    ]:
        monkeypatch.delenv(key, raising=False)


def _set_x_write_creds(monkeypatch):
    """Set env vars for X OAuth 1.0a (write operations)."""
    monkeypatch.setenv("X_POSTER_X_API_KEY", "ck_test123")
    monkeypatch.setenv("X_POSTER_X_API_SECRET", "cs_test456")
    monkeypatch.setenv("X_POSTER_X_OAUTH1_ACCESS_TOKEN", "at_test789")
    monkeypatch.setenv("X_POSTER_X_OAUTH1_ACCESS_TOKEN_SECRET", "ats_test012")


def _set_x_read_creds(monkeypatch):
    """Set env var for X Bearer token (read operations)."""
    monkeypatch.setenv("X_POSTER_X_ACCESS_TOKEN", "bearer_test_token")


def _set_telegram_creds(monkeypatch):
    """Set env var for Telegram bot token."""
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")


class _MockResponse:
    """Minimal httpx.Response mock."""

    def __init__(self, status_code: int, json_data: dict | None = None, text: str = ""):
        self.status_code = status_code
        self._json = json_data or {}
        self.text = text

    def json(self):
        return self._json

    def raise_for_status(self):
        if self.status_code >= 400:
            raise Exception(f"HTTP {self.status_code}")


def _mock_httpx(response: _MockResponse):
    """Return a patch context that makes httpx.AsyncClient return a mock."""
    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=False)
    # Default: mock all methods to return the given response
    mock_client.post = AsyncMock(return_value=response)
    mock_client.get = AsyncMock(return_value=response)
    mock_client.request = AsyncMock(return_value=response)
    return patch("guinevere.tools.backends.social.httpx.AsyncClient", return_value=mock_client)


# ---------------------------------------------------------------------------
# X / Twitter Actions
# ---------------------------------------------------------------------------


class TestPostX:
    """post_x: Post a tweet via X API v2."""

    @pytest.mark.asyncio
    async def test_post_x_success(self, backend, monkeypatch):
        _set_x_write_creds(monkeypatch)
        resp = _MockResponse(201, {"data": {"id": "12345", "text": "Hello world"}})
        with _mock_httpx(resp):
            result = await backend.dispatch("post_x", {"text": "Hello world"})
        assert result["ok"] is True
        assert result["tweet_id"] == "12345"
        assert result["text"] == "Hello world"

    @pytest.mark.asyncio
    async def test_post_x_missing_creds(self, backend, monkeypatch):
        """No OAuth creds -> config_missing."""
        result = await backend.dispatch("post_x", {"text": "Hello"})
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_post_x_api_error(self, backend, monkeypatch):
        _set_x_write_creds(monkeypatch)
        resp = _MockResponse(403, {"detail": "Forbidden"})
        with _mock_httpx(resp):
            result = await backend.dispatch("post_x", {"text": "Hello"})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_post_x_empty_text(self, backend, monkeypatch):
        """Empty text should return ok=False or handled gracefully."""
        _set_x_write_creds(monkeypatch)
        result = await backend.dispatch("post_x", {"text": ""})
        assert result["ok"] is False
        assert "error" in result


class TestReadMentions:
    """read_mentions: Read mentions via X API v2 with Bearer token."""

    @pytest.mark.asyncio
    async def test_read_mentions_success(self, backend, monkeypatch):
        _set_x_read_creds(monkeypatch)
        resp_data = {
            "data": [
                {"id": "100", "text": "@you great post!", "author_id": "999"},
                {"id": "101", "text": "@you agreed", "author_id": "998"},
            ],
            "meta": {"result_count": 2},
        }
        resp = _MockResponse(200, resp_data)
        with _mock_httpx(resp):
            result = await backend.dispatch("read_mentions", {"user_id": "42"})
        assert result["ok"] is True
        assert len(result["mentions"]) == 2
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_read_mentions_no_data(self, backend, monkeypatch):
        _set_x_read_creds(monkeypatch)
        resp = _MockResponse(200, {"data": [], "meta": {"result_count": 0}})
        with _mock_httpx(resp):
            result = await backend.dispatch("read_mentions", {"user_id": "42"})
        assert result["ok"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_read_mentions_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("read_mentions", {"user_id": "42"})
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_read_mentions_api_error(self, backend, monkeypatch):
        _set_x_read_creds(monkeypatch)
        resp = _MockResponse(429, {"title": "Too Many Requests"})
        with _mock_httpx(resp):
            result = await backend.dispatch("read_mentions", {"user_id": "42"})
        assert result["ok"] is False
        assert "error" in result


class TestReplyX:
    """reply_x: Reply to a tweet via X API v2."""

    @pytest.mark.asyncio
    async def test_reply_x_success(self, backend, monkeypatch):
        _set_x_write_creds(monkeypatch)
        resp = _MockResponse(201, {"data": {"id": "200", "text": "@author nice!"}})
        with _mock_httpx(resp):
            result = await backend.dispatch("reply_x", {
                "text": "@author nice!",
                "in_reply_to_tweet_id": "199",
            })
        assert result["ok"] is True
        assert result["tweet_id"] == "200"

    @pytest.mark.asyncio
    async def test_reply_x_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("reply_x", {
            "text": "@author nice!",
            "in_reply_to_tweet_id": "199",
        })
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_reply_x_missing_tweet_id(self, backend, monkeypatch):
        _set_x_write_creds(monkeypatch)
        result = await backend.dispatch("reply_x", {"text": "@author nice!"})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_reply_x_api_error(self, backend, monkeypatch):
        _set_x_write_creds(monkeypatch)
        resp = _MockResponse(500, {"error": "internal server error"})
        with _mock_httpx(resp):
            result = await backend.dispatch("reply_x", {
                "text": "@author nice!",
                "in_reply_to_tweet_id": "199",
            })
        assert result["ok"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Telegram Actions
# ---------------------------------------------------------------------------


class TestSendTelegram:
    """send_telegram: Send a text message via Telegram Bot API."""

    @pytest.mark.asyncio
    async def test_send_telegram_success(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {
            "ok": True,
            "result": {"message_id": 42, "chat": {"id": 12345}, "text": "Hello"},
        })
        with _mock_httpx(resp):
            result = await backend.dispatch("send_telegram", {
                "chat_id": "12345",
                "text": "Hello",
            })
        assert result["ok"] is True
        assert result["message_id"] == 42

    @pytest.mark.asyncio
    async def test_send_telegram_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("send_telegram", {
            "chat_id": "12345",
            "text": "Hello",
        })
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_send_telegram_api_error(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {"ok": False, "description": "Bad Request: chat not found"})
        with _mock_httpx(resp):
            result = await backend.dispatch("send_telegram", {
                "chat_id": "99999",
                "text": "Hello",
            })
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_send_telegram_empty_text(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        result = await backend.dispatch("send_telegram", {
            "chat_id": "12345",
            "text": "",
        })
        assert result["ok"] is False
        assert "error" in result


class TestGetTelegramUpdates:
    """get_telegram_updates: Get updates via Telegram Bot API."""

    @pytest.mark.asyncio
    async def test_get_updates_success(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {
            "ok": True,
            "result": [
                {"update_id": 1, "message": {"text": "hi"}},
                {"update_id": 2, "message": {"text": "hello"}},
            ],
        })
        with _mock_httpx(resp):
            result = await backend.dispatch("get_telegram_updates", {"offset": 0})
        assert result["ok"] is True
        assert len(result["updates"]) == 2

    @pytest.mark.asyncio
    async def test_get_updates_empty(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {"ok": True, "result": []})
        with _mock_httpx(resp):
            result = await backend.dispatch("get_telegram_updates", {})
        assert result["ok"] is True
        assert result["count"] == 0

    @pytest.mark.asyncio
    async def test_get_updates_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("get_telegram_updates", {})
        assert result["ok"] is False
        assert result.get("config_missing") is True


class TestEditTelegram:
    """edit_telegram: Edit a message via Telegram Bot API."""

    @pytest.mark.asyncio
    async def test_edit_telegram_success(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {
            "ok": True,
            "result": {"message_id": 42, "edit_date": 1234567890},
        })
        with _mock_httpx(resp):
            result = await backend.dispatch("edit_telegram", {
                "chat_id": "12345",
                "message_id": 42,
                "text": "Updated text",
            })
        assert result["ok"] is True
        assert result["edited"] is True

    @pytest.mark.asyncio
    async def test_edit_telegram_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("edit_telegram", {
            "chat_id": "12345",
            "message_id": 42,
            "text": "Updated",
        })
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_edit_telegram_api_error(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {"ok": False, "description": "Bad Request: message not found"})
        with _mock_httpx(resp):
            result = await backend.dispatch("edit_telegram", {
                "chat_id": "12345",
                "message_id": 99999,
                "text": "Updated",
            })
        assert result["ok"] is False
        assert "error" in result


class TestDeleteTelegram:
    """delete_telegram: Delete a message via Telegram Bot API."""

    @pytest.mark.asyncio
    async def test_delete_telegram_success(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {"ok": True, "result": True})
        with _mock_httpx(resp):
            result = await backend.dispatch("delete_telegram", {
                "chat_id": "12345",
                "message_id": 42,
            })
        assert result["ok"] is True
        assert result["deleted"] is True
        assert "restore_method" in result

    @pytest.mark.asyncio
    async def test_delete_telegram_missing_creds(self, backend, monkeypatch):
        result = await backend.dispatch("delete_telegram", {
            "chat_id": "12345",
            "message_id": 42,
        })
        assert result["ok"] is False
        assert result.get("config_missing") is True

    @pytest.mark.asyncio
    async def test_delete_telegram_api_error(self, backend, monkeypatch):
        _set_telegram_creds(monkeypatch)
        resp = _MockResponse(200, {"ok": False, "description": "Bad Request"})
        with _mock_httpx(resp):
            result = await backend.dispatch("delete_telegram", {
                "chat_id": "12345",
                "message_id": 99999,
            })
        assert result["ok"] is False
        assert "error" in result


# ---------------------------------------------------------------------------
# Meta / contract tests
# ---------------------------------------------------------------------------


class TestContract:
    """Backend contract compliance."""

    def test_name(self, backend):
        assert backend.name == "social"

    def test_is_available(self, backend):
        assert backend.is_available() is True

    def test_actions_count(self, backend):
        actions = backend.actions()
        assert len(actions) == 7

    def test_actions_names(self, backend):
        names = {a.name for a in backend.actions()}
        expected = {"post_x", "read_mentions", "reply_x", "send_telegram",
                    "get_telegram_updates", "edit_telegram", "delete_telegram"}
        assert names == expected

    @pytest.mark.asyncio
    async def test_dispatch_unknown_returns_error(self, backend):
        result = await backend.dispatch("nonexistent_action", {})
        assert result["ok"] is False
        assert "error" in result

    @pytest.mark.asyncio
    async def test_dispatch_never_raises(self, backend, monkeypatch):
        """dispatch() must NEVER raise to caller (fail-soft)."""
        # Pass garbage args that could cause TypeError
        monkeypatch.setenv("X_POSTER_X_ACCESS_TOKEN", "x")
        result = await backend.dispatch("read_mentions", {"user_id": "42"})
        # Should return a dict with ok field, not raise
        assert isinstance(result, dict)
        assert "ok" in result

    def test_find_action(self, backend):
        action = backend.find_action("post_x")
        assert action is not None
        assert action.label.value == "L2"
