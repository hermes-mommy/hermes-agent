import sys
import types
from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if "discord" not in sys.modules:
    discord_stub = types.ModuleType("discord")
    setattr(
        discord_stub,
        "utils",
        types.SimpleNamespace(get=lambda iterable, **attrs: next((item for item in iterable if all(getattr(item, key, None) == value for key, value in attrs.items())), None)),
    )
    sys.modules["discord"] = discord_stub

from src.discord.gotify_fallback import build_gotify_payload, get_priority, send_fallback


def test_build_gotify_payload_returns_dict():
    payload = build_gotify_payload("Title", "Description", 7)
    assert payload == {"title": "Title", "message": "Description", "priority": 7}


@pytest.mark.parametrize(
    "severity,priority",
    [("SEV0", 10), ("SEV1", 7), ("SEV2", 5), ("SEV3", 3), ("SEV4", 1)],
)
def test_get_priority_maps_all_sevs(severity, priority):
    assert get_priority(severity) == priority


def test_get_priority_unknown_returns_0():
    assert get_priority("SEVX") == 0


@pytest.mark.asyncio
async def test_send_fallback_no_token_returns_false(monkeypatch):
    monkeypatch.delenv("GOTIFY_APP_TOKEN", raising=False)
    assert await send_fallback("Title", "Description", "SEV1") is False


@pytest.mark.asyncio
async def test_send_fallback_success(monkeypatch):
    monkeypatch.setenv("GOTIFY_APP_TOKEN", "token")
    response = Mock(is_success=True, status_code=200, text="ok")
    post = AsyncMock(return_value=response)
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.post = post
    with patch("httpx.AsyncClient", return_value=client):
        assert await send_fallback("Title", "Description", "SEV0") is True
    post.assert_awaited_once()


@pytest.mark.asyncio
async def test_send_fallback_http_error(monkeypatch):
    monkeypatch.setenv("GOTIFY_APP_TOKEN", "token")
    response = Mock(is_success=False, status_code=500, text="error")
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.post = AsyncMock(return_value=response)
    with patch("httpx.AsyncClient", return_value=client):
        assert await send_fallback("Title", "Description", "SEV1") is False


@pytest.mark.asyncio
async def test_send_fallback_connection_error(monkeypatch):
    monkeypatch.setenv("GOTIFY_APP_TOKEN", "token")
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.post = AsyncMock(side_effect=httpx.ConnectError("boom", request=Mock()))
    with patch("httpx.AsyncClient", return_value=client):
        assert await send_fallback("Title", "Description", "SEV1") is False


@pytest.mark.asyncio
async def test_send_fallback_timeout(monkeypatch):
    monkeypatch.setenv("GOTIFY_APP_TOKEN", "token")
    client = AsyncMock()
    client.__aenter__.return_value = client
    client.__aexit__.return_value = None
    client.post = AsyncMock(side_effect=httpx.TimeoutException("timeout"))
    with patch("httpx.AsyncClient", return_value=client):
        assert await send_fallback("Title", "Description", "SEV1") is False
