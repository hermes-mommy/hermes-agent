from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock

import httpx
import pytest


def build_gotify_payload(title: str, message: str, priority: int) -> dict[str, Any]:
    return {"title": title, "message": message, "priority": priority}


def build_priority(severity: str) -> int:
    mapping = {
        "SEV0": 10,
        "SEV1": 7,
        "SEV2": 5,
        "SEV3": 3,
        "SEV4": 1,
    }
    try:
        return mapping[severity]
    except KeyError as exc:
        raise ValueError(f"Unsupported severity: {severity}") from exc


async def send_gotify(gotify_url: str, app_token: str, payload: dict[str, Any]) -> bool:
    headers = {"X-Gotify-Key": app_token}
    client = httpx.AsyncClient(timeout=10.0)
    try:
        response = await client.post(f"{gotify_url.rstrip('/')}/message", json=payload, headers=headers)
        response.raise_for_status()
        return True
    except httpx.HTTPError:
        return False
    finally:
        close = getattr(client, "aclose", None)
        if close is not None:
            result = close()
            if hasattr(result, "__await__"):
                await result


@pytest.mark.parametrize(
    ("severity", "expected"),
    [
        ("SEV0", 10),
        ("SEV1", 7),
        ("SEV2", 5),
        ("SEV3", 3),
        ("SEV4", 1),
    ],
)
def test_build_priority_maps_severities(severity: str, expected: int) -> None:
    assert build_priority(severity) == expected


def test_build_priority_rejects_invalid_severity() -> None:
    with pytest.raises(ValueError, match="Unsupported severity: SEV9"):
        build_priority("SEV9")


def test_build_gotify_payload_structure() -> None:
    payload = build_gotify_payload("System alert", "Disk space low", 7)
    assert payload == {"title": "System alert", "message": "Disk space low", "priority": 7}


@pytest.mark.asyncio
async def test_send_gotify_success(monkeypatch: pytest.MonkeyPatch) -> None:
    response = AsyncMock()
    response.raise_for_status.return_value = None
    post_mock = AsyncMock(return_value=response)
    client_cm = AsyncMock()
    client_cm.post = post_mock
    client_cm.aclose = AsyncMock(return_value=None)
    class ClientFactory:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return client_cm

    monkeypatch.setattr(httpx, "AsyncClient", ClientFactory())

    payload = build_gotify_payload("Title", "Message", 5)
    assert await send_gotify("http://localhost:8081", "token", payload) is True
    post_mock.assert_awaited_once_with(
        "http://localhost:8081/message",
        json=payload,
        headers={"X-Gotify-Key": "token"},
    )


@pytest.mark.asyncio
async def test_send_gotify_connection_error(monkeypatch: pytest.MonkeyPatch) -> None:
    client_cm = AsyncMock()
    client_cm.__aenter__.return_value = client_cm
    client_cm.__aexit__.return_value = None
    client_cm.post = AsyncMock(side_effect=httpx.ConnectError("connect failed"))
    class ClientFactory:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return client_cm

    monkeypatch.setattr(httpx, "AsyncClient", ClientFactory())

    assert await send_gotify("http://localhost:8081", "token", build_gotify_payload("Title", "Body", 5)) is False


@pytest.mark.asyncio
async def test_send_gotify_http_error(monkeypatch: pytest.MonkeyPatch) -> None:
    response = AsyncMock()
    response.raise_for_status = lambda: (_ for _ in ()).throw(
        httpx.HTTPStatusError(
            "bad response",
            request=httpx.Request("POST", "http://localhost:8081/message"),
            response=httpx.Response(500, request=httpx.Request("POST", "http://localhost:8081/message")),
        )
    )
    post_mock = AsyncMock(return_value=response)
    client_cm = AsyncMock()
    client_cm.post = post_mock
    client_cm.aclose = AsyncMock(return_value=None)
    class ClientFactory:
        def __call__(self, *args: Any, **kwargs: Any) -> Any:
            return client_cm

    monkeypatch.setattr(httpx, "AsyncClient", ClientFactory())

    assert await send_gotify("http://localhost:8081", "token", build_gotify_payload("Title", "Body", 5)) is False
