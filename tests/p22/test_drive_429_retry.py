"""P22 brutal-audit F09 — Drive client 429 retry-with-backoff tests.

Covers:
    * 429 on Drive API → retry 3 times with exponential backoff (1s/2s/4s).
    * After 3 retries exhausted → raise RateLimitExceededError (NOT ProviderError).
    * Retry-After header is honoured (sleep_for >= Retry-After).
    * 429 followed by success → retry succeeds.
    * time.sleep is mocked to be instant so tests run fast.

Forbidden patterns:
    * No ``# type: ignore``.
    * No bare ``except:`` (HARD REJECTION).
    * No pickle.
    * No token in log output.
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[2]
_SRC = _REPO_ROOT / "src"
if str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

from src.life_integrations.adapters._clients.drive_client import (
    DriveClient,
    _DRIVE_MAX_RETRIES,
    _DRIVE_RETRY_BACKOFFS,
)
from src.life_integrations.errors import (
    PermissionDeniedError,
    ProviderError,
    RateLimitExceededError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeHttpError(Exception):
    """Stand-in for ``googleapiclient.errors.HttpError``.

    DriveClient inspects ``.resp.status`` and ``.resp.headers``.
    """

    def __init__(self, status: int, headers: dict | None = None) -> None:
        super().__init__(f"http {status}")
        self.resp = MagicMock(status=status, headers=headers or {})


def _make_drive_client_with_execute_side_effect(
    execute_side_effect, *, fake_credentials=None,
):
    """Build a DriveClient whose service's first call has *execute_side_effect*.

    Returns (client, fake_resource, fake_HttpError_class).
    """
    fake_resource = MagicMock(name="drive_service_resource")

    # Build a request whose execute() has the given side_effect
    files_chain = MagicMock(name="files_chain")
    fake_resource.files.return_value = files_chain
    request = MagicMock()
    request.execute.side_effect = execute_side_effect
    # make .get().execute, .list().execute etc. all use the same request
    for chain_method in ("list", "get", "create", "update", "delete"):
        getattr(files_chain, chain_method).return_value = request

    about_chain = MagicMock()
    fake_resource.about.return_value = about_chain
    about_chain.get.return_value = request

    fake_HttpError = type("HttpError", (Exception,), {})

    fake_creds = fake_credentials or MagicMock(
        name="FakeCredentials", refresh_token="rt-xyz",
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.build_drive_service",
        return_value=(fake_resource, fake_HttpError),
    ):
        client = DriveClient(credentials=fake_creds)

    # Override _HttpError to our fake so isinstance checks work
    client._HttpError = _FakeHttpError
    return client, fake_resource


# ---------------------------------------------------------------------------
# 429 retry — covers the central _call_with_retry
# ---------------------------------------------------------------------------


def test_drive_429_raises_rate_limit_after_retries_exhausted():
    """429 on Drive API → retry 3 times → RateLimitExceededError (not ProviderError)."""
    http_error = _FakeHttpError(429, {"Retry-After": "3"})
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error] * (_DRIVE_MAX_RETRIES + 1),  # all attempts return 429
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.time.sleep",
    ) as mock_sleep:
        with pytest.raises(RateLimitExceededError) as exc_info:
            client.list_files()

    assert exc_info.value.provider == "google-drive"
    assert mock_sleep.call_count == _DRIVE_MAX_RETRIES
    # Each sleep should be >= Retry-After=3
    for call_args in mock_sleep.call_args_list:
        slept = call_args[0][0]
        assert slept >= 3


def test_drive_429_retry_succeeds_on_second_attempt():
    """429 first, then 200 on second attempt → method succeeds (retry works)."""
    success_response = {"files": [{"id": "f1", "name": "x"}]}
    http_429 = _FakeHttpError(429)

    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_429, success_response],
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.time.sleep",
    ):
        result = client.list_files()

    assert result == success_response.get("files", [])


def test_drive_429_no_retry_after_uses_backoff_schedule():
    """429 without Retry-After → uses backoff schedule (1, 2, 4)."""
    http_error = _FakeHttpError(429, headers={})
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error] * (_DRIVE_MAX_RETRIES + 1),
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.time.sleep",
    ) as mock_sleep:
        with pytest.raises(RateLimitExceededError):
            client.get_file("abc")

    assert mock_sleep.call_count == 3
    slept_values = [c[0][0] for c in mock_sleep.call_args_list]
    assert slept_values == list(_DRIVE_RETRY_BACKOFFS)


def test_drive_429_retry_after_overrides_backoff():
    """Retry-After=10 > backoff=1 → sleep(10) on first attempt."""
    http_error = _FakeHttpError(429, headers={"Retry-After": "10"})
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error, {"files": []}],
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.time.sleep",
    ) as mock_sleep:
        client.list_files()

    # first sleep should be max(backoff[0]=1, retry_after=10) = 10
    assert mock_sleep.call_count == 1
    assert mock_sleep.call_args_list[0][0][0] == 10


def test_drive_403_still_raises_permission_denied():
    """403 → PermissionDeniedError (no retry, not affected by 429 changes)."""
    http_error = _FakeHttpError(403)
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error],
    )

    with pytest.raises(PermissionDeniedError):
        client.list_files()


def test_drive_500_still_raises_provider_error():
    """500 → ProviderError (no retry, not affected by 429 changes)."""
    http_error = _FakeHttpError(500)
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error],
    )

    with pytest.raises(ProviderError):
        client.list_files()


def test_drive_429_health_returns_false():
    """health() returns False (not raises) when 429 is hit."""
    http_error = _FakeHttpError(429, headers={})
    client, _resource = _make_drive_client_with_execute_side_effect(
        [http_error] * (_DRIVE_MAX_RETRIES + 1),
    )

    with patch(
        "src.life_integrations.adapters._clients.drive_client.time.sleep",
    ):
        assert client.health() is False


# ---------------------------------------------------------------------------
# Static guard: forbidden patterns
# ---------------------------------------------------------------------------


def test_drive_no_silent_429_swallows():
    """Static guard: drive_client.py imports RateLimitExceededError."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "life_integrations"
        / "adapters"
        / "_clients"
        / "drive_client.py"
    )
    text = src_path.read_text(encoding="utf-8")
    assert "RateLimitExceededError" in text
    assert "429" in text
    assert "backoff" in text.lower() or "retry" in text.lower()
