"""P22 brutal-audit F09 — Calendar client 429 retry-with-backoff tests.

Covers:
    * 429 on CRUD methods → retry-with-backoff (1s/2s/4s, max 3) attempted.
    * After 3 retries exhausted → RateLimitExceededError raised.
    * Retry-After header is honoured (sleep_for >= Retry-After).
    * 429 followed by 200 → method succeeds (retry succeeds).
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

from src.life_integrations.adapters._clients.calendar_client import (
    CalendarClient,
    _CALENDAR_MAX_RETRIES,
    _CALENDAR_RETRY_BACKOFFS,
)
from src.life_integrations.errors import (
    ConfigurationMissingError,
    RateLimitExceededError,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _FakeCredentials:
    """Minimal google.oauth2.credentials.Credentials stand-in."""

    def __init__(
        self,
        scopes: list[str] | None = None,
        token: str | None = "fake-token",
        refresh_token: str = "fake-refresh",
    ) -> None:
        self.scopes: list[str] | None = list(scopes) if scopes else None
        self.token: str | None = token
        self.expiry = None
        self.refresh_token: str = refresh_token

    def refresh(self, request) -> None:  # noqa: ARG002
        return None

    def to_json(self) -> str:
        import json
        return json.dumps({"token": self.token, "scopes": self.scopes})


_FAKE_SCOPES = (
    "https://www.googleapis.com/auth/calendar.events.owned",
    "https://www.googleapis.com/auth/calendar.calendars",
    "https://www.googleapis.com/auth/calendar.acls",
    "https://www.googleapis.com/auth/calendar.calendarlist",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
)


class _HttpErrorLike(Exception):
    """Stand-in for ``googleapiclient.errors.HttpError``.

    The Calendar client only inspects ``.resp.status`` and
    ``.resp.headers``.
    """

    def __init__(self, status: int, headers: dict | None = None) -> None:
        super().__init__(f"http {status}")
        self.resp = MagicMock(status=status, headers=headers or {})


def _make_client_with_http_error(
    tmp_path, fake_google_libs, execute_side_effect, *, creds=None,
):
    """Construct a CalendarClient whose service's CRUD execute() raises *execute_side_effect*."""
    import json

    creds = creds or _FakeCredentials(scopes=list(_FAKE_SCOPES))
    fake_google_libs.Credentials.from_authorized_user_file.return_value = creds

    creds_path = tmp_path / "cal-token.json"
    creds_path.write_text(json.dumps({
        "client_id": "x", "client_secret": "y",
        "refresh_token": "rt", "token": "at",
        "scopes": list(_FAKE_SCOPES),
    }), encoding="utf-8")

    service = MagicMock(name="calendar_service")
    # all CRUD execute() raise the side_effect
    events_resource = MagicMock(name="events")
    service.events.return_value = events_resource

    # each CRUD sub-method returns a request whose execute() has the side_effect
    for method_name in ("list", "get", "insert", "update", "delete"):
        request = MagicMock()
        request.execute = MagicMock(side_effect=execute_side_effect)
        getattr(events_resource, method_name).return_value = request

    # calendarList().list().execute() for health() — not 429
    cl_request = MagicMock()
    cl_request.execute.return_value = {"items": [{"id": "primary"}]}
    cl_list = MagicMock(return_value=cl_request)
    service.calendarList.return_value.list = cl_list

    fake_google_libs.build.return_value = service

    client = CalendarClient(credentials_path=str(creds_path))
    return client, service, events_resource


# ---------------------------------------------------------------------------
# 429 retry — all 5 CRUD methods
# ---------------------------------------------------------------------------


@pytest.fixture
def fake_google_libs_for_429(monkeypatch):
    """Inject google-* mocks for calendar 429 tests."""
    Credentials = MagicMock(name="Credentials")
    Request = MagicMock(name="Request")
    build = MagicMock(name="build")
    RefreshError = type("RefreshError", (Exception,), {})
    TransportError = type("TransportError", (Exception,), {})

    mods = {
        "google.oauth2.credentials": MagicMock(Credentials=Credentials),
        "google.auth.transport.requests": MagicMock(Request=Request),
        "googleapiclient.discovery": MagicMock(build=build),
        "google.auth.exceptions": MagicMock(
            RefreshError=RefreshError, TransportError=TransportError,
        ),
    }
    for mod_name, mod_mock in mods.items():
        monkeypatch.setitem(sys.modules, mod_name, mod_mock)

    import types
    bundle = types.SimpleNamespace(
        Credentials=Credentials,
        Request=Request,
        build=build,
        RefreshError=RefreshError,
        TransportError=TransportError,
    )
    return bundle


def _make_http_error(status, headers=None):
    return _HttpErrorLike(status, headers)


@pytest.mark.parametrize(
    "crud_method,args",
    [
        ("list_events", ("primary", 10)),
        ("get_event", ("primary", "evt-1")),
        ("create_event", ({"summary": "test"},)),
        ("update_event", ("primary", "evt-1", {"summary": "upd"})),
        ("delete_event", ("primary", "evt-1")),
    ],
)
def test_calendar_429_raises_rate_limit_after_retries_exhausted(
    tmp_path, fake_google_libs_for_429, crud_method, args,
):
    """429 on any CRUD method → retry 3 times → raise RateLimitExceededError."""
    http_error = _make_http_error(429, {"Retry-After": "5"})
    client, _service, _events = _make_client_with_http_error(
        tmp_path, fake_google_libs_for_429, http_error,
    )

    # All CRUD sub-methods raise 429 on every attempt.
    # Mock time.sleep so retries are instant.
    with patch("src.life_integrations.adapters._clients.calendar_client.time.sleep") as mock_sleep:
        method = getattr(client, crud_method)
        with pytest.raises(RateLimitExceededError) as exc_info:
            method(*args)

    assert exc_info.value.provider == "google-calendar"
    # Should have slept _CALENDAR_MAX_RETRIES times (1+2+4 backoffs)
    assert mock_sleep.call_count == _CALENDAR_MAX_RETRIES
    # Verify the sleep values match our backoff schedule (respecting Retry-After=5)
    for call_args in mock_sleep.call_args_list:
        slept = call_args[0][0]
        assert slept >= 5  # Retry-After=5 overrides backoff


def test_calendar_429_then_200_retries_succeeds(
    tmp_path, fake_google_libs_for_429,
):
    """429 followed by 200 on the retry → method succeeds."""
    success_response = {"items": [{"id": "evt-1"}]}
    http_429 = _make_http_error(429)

    client, _service, _events = _make_client_with_http_error(
        tmp_path, fake_google_libs_for_429, http_429,
    )

    # Patch the CRUD sub-method's execute to raise 429 on first call,
    # return success on second call.
    request = _events.list.return_value
    request.execute.side_effect = [http_429, success_response]

    with patch("src.life_integrations.adapters._clients.calendar_client.time.sleep"):
        result = client.list_events("primary", 10)

    # list_events extracts "items" from the response.
    assert result == [{"id": "evt-1"}]


def test_calendar_429_no_retry_after_header_uses_backoff(
    tmp_path, fake_google_libs_for_429,
):
    """429 without Retry-After → backoff schedule used (1, 2, 4)."""
    http_error = _make_http_error(429)  # no Retry-After header
    client, _service, _events = _make_client_with_http_error(
        tmp_path, fake_google_libs_for_429, http_error,
    )

    with patch("src.life_integrations.adapters._clients.calendar_client.time.sleep") as mock_sleep:
        with pytest.raises(RateLimitExceededError):
            client.list_events("primary", 10)

    # Should have used the backoff schedule
    assert mock_sleep.call_count == 3
    slept_values = [c[0][0] for c in mock_sleep.call_args_list]
    assert slept_values == list(_CALENDAR_RETRY_BACKOFFS)


def test_calendar_429_exhaustion_logs_and_raises(tmp_path, fake_google_libs_for_429):
    """After all retries exhausted → raises RateLimitExceededError (not ConfigurationMissingError)."""
    http_error = _make_http_error(429, {"Retry-After": "1"})
    client, _service, _events = _make_client_with_http_error(
        tmp_path, fake_google_libs_for_429, http_error,
    )

    with patch("src.life_integrations.adapters._clients.calendar_client.time.sleep"):
        with pytest.raises(RateLimitExceededError) as exc_info:
            client.list_events("primary", 10)

    assert "google-calendar" in str(exc_info.value)


def test_calendar_non_429_errors_still_raise_config_missing(
    tmp_path, fake_google_libs_for_429,
):
    """Non-429 errors (e.g. 500) still raise ConfigurationMissingError (not silently swallowed)."""
    http_error = _make_http_error(500)
    client, _service, _events = _make_client_with_http_error(
        tmp_path, fake_google_libs_for_429, http_error,
    )

    with pytest.raises(ConfigurationMissingError):
        client.list_events("primary", 10)


# ---------------------------------------------------------------------------
# Static guard: forbidden patterns
# ---------------------------------------------------------------------------


def test_calendar_no_silent_429_swallow():
    """Static guard: calendar_client.py does not silently swallow 429 as ConfigurationMissingError."""
    src_path = (
        Path(__file__).resolve().parents[2]
        / "src"
        / "life_integrations"
        / "adapters"
        / "_clients"
        / "calendar_client.py"
    )
    text = src_path.read_text(encoding="utf-8")
    assert "RateLimitExceededError" in text, "must import RateLimitExceededError"
    assert "429" in text, "must reference 429 status code"
    assert "backoff" in text.lower() or "retry" in text.lower()
