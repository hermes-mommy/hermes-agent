"""P22 Google Calendar API client — P22 D3 build.

Clone-style wrapper around ``google-api-python-client`` for the Calendar
v3 API. Mirrors the ``GmailClient`` pattern (sync ``CalendarClient`` +
``AsyncCalendarClient`` thread-pool wrapper) but adapted to the P22
adapters' expectations:

    list_events(calendar_id, max_results)
    get_event(calendar_id, event_id)
    create_event(event_data)
    update_event(calendar_id, event_id, event_data)
    delete_event(calendar_id, event_id)
    health()

Notes:

* **Lazy imports** — ``google-auth``, ``google-api-python-client``, and
  ``google.oauth2`` may be absent in some environments; imports happen
  inside ``__init__`` / methods and ALWAYS raise
  ``ConfigurationMissingError`` on miss so the adapter reports
  ``CONFIG_MISSING`` rather than faking success.
* **No pickle** — JSON only (``Credentials.to_json`` / ``from_json``).
  Pickling Credentials is a security NEVER-DO per project policy.
* **Token never logged** — log lines carry only metadata (calendar_id,
  event_id, latency, op name); the access/refresh token is never
  serialised into a log record.
* **Refresh-on-401** — ``refresh_if_needed`` mirrors ``TokenManager``'s
  expiry-margin refresh; we also opportunistically refresh when the
  Calendar API returns 401.
* **Health pre-flight** — ``health()`` uses ``calendarList().list()``,
  the cheapest authenticated read.
* **No undelete** — Calendar API has no native restore; deletion is
  a snapshot-then-delete operation (orchestrated by the
  ``CalendarIntegrationAdapter``). The client never auto-restores.

Scopes (per P22 research ``google-workspace-full-access.md`` §2, §7):

    https://www.googleapis.com/auth/calendar.events.owned
    https://www.googleapis.com/auth/calendar.calendars
    https://www.googleapis.com/auth/calendar.acls
    https://www.googleapis.com/auth/calendar.calendarlist
    https://www.googleapis.com/auth/calendar.settings.readonly

These grant owned-event CRUD plus calendar/ACL administration,
matching the adapter's L1/L2/L3 surface (L4 remains forbidden).
"""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, Final

import structlog

from guinevere.life_integrations.errors import (
    ConfigurationMissingError,
    RateLimitExceededError,
)

logger = structlog.get_logger(__name__)

# ---- scopes & defaults ----------------------------------------------------

_CALENDAR_DEFAULT_SCOPES: Final[tuple[str, ...]] = (
    "https://www.googleapis.com/auth/calendar.events.owned",
    "https://www.googleapis.com/auth/calendar.calendars",
    "https://www.googleapis.com/auth/calendar.acls",
    "https://www.googleapis.com/auth/calendar.calendarlist",
    "https://www.googleapis.com/auth/calendar.settings.readonly",
)

_DEFAULT_CREDENTIALS_PATH: Final[str] = "/run/guinevere/calendar-token.json"

_REFRESH_MARGIN_SECONDS: Final[int] = 300  # mirror Gmail TokenManager

# 429 retry/backoff configuration (P22 brutal-audit F09).
# Per task spec: 1s/2s/4s exponential, max 3 retries.
_CALENDAR_RETRY_BACKOFFS: Final[tuple[int, ...]] = (1, 2, 4)
_CALENDAR_MAX_RETRIES: Final[int] = 3


# ---- helpers --------------------------------------------------------------

def _fail_missing(reason: str) -> None:
    """Raise ``ConfigurationMissingError`` (fail-closed)."""
    raise ConfigurationMissingError(reason)


def _parse_retry_after(exc: Any) -> int | None:
    """Best-effort Retry-After header parser for HttpError instances.

    Returns the integer seconds if present, else ``None``. The Calendar
    googleapiclient ``HttpError`` exposes the response headers via
    ``exc.resp.headers`` (a dict-like). We do not let malformed headers
    crash the call — they fall back to ``None``.
    """
    try:
        headers = getattr(getattr(exc, "resp", None), "headers", None) or {}
        raw = headers.get("Retry-After") if hasattr(headers, "get") else None
        if raw is None:
            return None
        return max(0, int(str(raw).strip()))
    except (TypeError, ValueError, AttributeError):
        return None


def _handle_http_error(exc: Any, method_name: str) -> None:
    """Map a Calendar API HttpError to a typed integration exception.

    Behaviour (P22 brutal-audit F09):
      * 401 — refresh + retry ONCE (handled inside the calling CRUD method
        since refresh-then-rebuild-service is a service-level mutation;
        this helper only normalises the NON-401 case).
      * 429 — raise ``RateLimitExceededError(provider="google-calendar",
        retry_after=<Retry-After or None>)``. Caller will retry-or-rethrow.
      * other status (incl. 404/5xx/transport) — raise
        ``ConfigurationMissingError`` so the adapter reports
        ``CONFIG_MISSING`` (existing fail-closed behaviour; preserving
        backwards compat).
    """
    status = getattr(getattr(exc, "resp", None), "status", None)
    if status == 429:
        retry_after = _parse_retry_after(exc)
        raise RateLimitExceededError(
            provider="google-calendar", retry_after=retry_after,
        ) from exc
    # Fall through: keep the original Calendar "map non-401 to
    # ConfigurationMissingError" semantics. The CRUD wrapper still does
    # 401-refresh-retry, capture in the calling method body.
    error_type = type(exc).__name__
    _fail_missing(
        f"Calendar client: {method_name} failed: {error_type}",
    )


# ---- sync client ----------------------------------------------------------

class CalendarClient:
    """Synchronous Google Calendar API client.

    Mirrors ``guinevere.gmail.client.GmailClient``: constructor validates
    credentials, ``build``s the API service, every method delegates to
    the service object, and the async wrapper below offloads to a
    thread pool so the event loop stays unblocked.
    """

    def __init__(
        self,
        credentials_path: str = _DEFAULT_CREDENTIALS_PATH,
        scopes: list[str] | None = None,
    ) -> None:
        """Load OAuth credentials from *credentials_path* and build the service.

        Raises:
            ConfigurationMissingError: If the credentials file is missing,
                empty, malformed, or the optional ``google-api-python-client``
                / ``google-auth`` libraries are not installed.
        """
        self._log = logger
        self._credentials_path: str = credentials_path
        self._scopes: list[str] = list(scopes) if scopes else list(
            _CALENDAR_DEFAULT_SCOPES,
        )
        self._credentials: Any = None
        self._service: Any = None

        self._credentials = self._load_credentials(credentials_path)
        self._validate_scopes(self._credentials)
        self._service = self._build_service(self._credentials)

        self._log.info(
            "calendar_client_initialized",
            credentials_path=credentials_path,
            scope_count=len(self._scopes),
        )

    # -- lazy loading -------------------------------------------------------

    @staticmethod
    def _try_import_google_libs() -> tuple[Any, Any, Any, Any, Any]:
        """Import Google Calendar dependencies lazily.

        Returns a tuple ``(Credentials, Request, build, RefreshError,
        TransportError)``. Anything missing raises
        ``ConfigurationMissingError`` so the adapter reports
        ``CONFIG_MISSING`` rather than ``ImportError`` (AGENTS.md §5:
        ``ImportError`` is a banned generic exception class for
        user-visible flows).
        """
        try:
            from google.oauth2.credentials import Credentials
        except ImportError as exc:
            _fail_missing(
                "google-auth (Credentials) not installed: "
                f"{type(exc).__name__}",
            )
        try:
            from google.auth.transport.requests import Request
        except ImportError as exc:
            _fail_missing(
                "google-auth (Request) not installed: "
                f"{type(exc).__name__}",
            )
        try:
            from googleapiclient.discovery import build
        except ImportError as exc:
            _fail_missing(
                "google-api-python-client (build) not installed: "
                f"{type(exc).__name__}",
            )
        try:
            from google.auth.exceptions import (
                RefreshError,
                TransportError,
            )
        except ImportError as exc:
            _fail_missing(
                "google-auth (exceptions) not installed: "
                f"{type(exc).__name__}",
            )

        return Credentials, Request, build, RefreshError, TransportError

    def _load_credentials(self, credentials_path: str) -> Any:
        """Load credentials JSON from *credentials_path* via ``from_authorized_user_file``.

        Fail-closed on every missing-piece scenario:

            * empty / unset ``credentials_path``
            * missing file on disk
            * malformed JSON (caught by google-auth which raises ``ValueError``)
            * missing google-auth library
        """
        if not credentials_path:
            _fail_missing(
                "Calendar client: credentials_path is empty "
                "(sec-google-calendar-oauth not provisioned)",
            )

        Credentials, _Request, _build, _RefreshError, _TransportError = (
            self._try_import_google_libs()
        )

        try:
            credentials = Credentials.from_authorized_user_file(
                credentials_path,
                self._scopes,
            )
        except FileNotFoundError as exc:
            _fail_missing(
                "Calendar client: credentials file not found at "
                f"{credentials_path}",
            )
        except ValueError as exc:
            # google-auth raises ValueError on malformed token JSON.
            _fail_missing(
                "Calendar client: credentials file is malformed: "
                f"{type(exc).__name__}",
            )
        except OSError as exc:
            _fail_missing(
                "Calendar client: credentials file cannot be read: "
                f"{type(exc).__name__}",
            )

        # Defensive validation — google-auth finished ``from_authorized_user_file``
        # without error but we still want the adapter to fail-fast on blatantly
        # empty credentials.
        if credentials is None:
            _fail_missing(
                "Calendar client: Credentials.from_authorized_user_file "
                "returned None",
            )

        return credentials

    def _validate_scopes(self, credentials: Any) -> None:
        """Verify that the granted scopes include all required scopes.

        Raises ``ConfigurationMissingError`` — token in hand but scopes
        missing is a configuration problem, not an auth failure.
        """
        granted = list(credentials.scopes or [])
        required = set(self._scopes)
        missing = required - set(granted)
        if missing:
            # Surface only the missing scope NAME — never the token.
            _fail_missing(
                "Calendar client: token is missing required scopes: "
                f"{sorted(missing)[0]!r}",
            )

    @staticmethod
    def _build_service(credentials: Any) -> Any:
        """Build the Calendar v3 service with ``cache_discovery=False``.

        Returns the ``Resource`` returned by ``googleapiclient.discovery.build``.

        Raises ``ConfigurationMissingError`` if the discovery library is missing.
        """
        try:
            from googleapiclient.discovery import build as _build
        except ImportError as exc:
            _fail_missing(
                "google-api-python-client not installed: "
                f"{type(exc).__name__}",
            )

        return _build(
            "calendar",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

    # -- refresh ------------------------------------------------------------

    def refresh_if_needed(self) -> bool:
        """Refresh *credentials* if it expires within the 5-minute margin.

        Returns ``True`` if a refresh was performed, ``False`` otherwise.

        Mirrors ``guinevere.gmail.token_manager.TokenManager.refresh_if_needed``
        so callers (and the async wrapper) get consistent semantics.

        Raises ``ConfigurationMissingError`` for expired-but-unrefreshable
        credentials so the adapter reports ``CONFIG_MISSING`` rather than
        attempting an API call with a known-stale token.
        """
        if self._credentials is None:
            return False

        if not getattr(self._credentials, "expiry", None):
            return False

        try:
            seconds_until_expiry = (
                self._credentials.expiry.timestamp() - time.time()
            )
        except AttributeError:
            return False

        if seconds_until_expiry > _REFRESH_MARGIN_SECONDS:
            return False

        self._log.info(
            "calendar_refresh_triggered",
            seconds_until_expiry=round(seconds_until_expiry, 1),
        )
        self._do_refresh()
        # Re-bind the service so subsequent calls use the refreshed token.
        self._service = self._build_service(self._credentials)
        return True

    def _do_refresh(self) -> None:
        """Synchronously refresh the access token.

        On ``RefreshError`` / ``TransportError`` raised by google-auth,
        map to ``ConfigurationMissingError``; this lets the adapter flip
        to ``CONFIG_MISSING`` rather than crashing the runtime path.

        NO pickle: the refreshed credentials are persisted via
        ``to_json`` only, never via ``pickle``.
        """
        _, Request, _build, RefreshError, TransportError = (
            self._try_import_google_libs()
        )

        request = Request()
        try:
            self._credentials.refresh(request)
        except RefreshError as exc:
            _fail_missing(
                "Calendar client: token refresh failed (RefreshError)",
            )
        except TransportError as exc:
            _fail_missing(
                "Calendar client: token refresh transport error",
            )

        if not getattr(self._credentials, "token", None):
            _fail_missing(
                "Calendar client: refresh returned empty access token",
            )

        # Persist the refreshed JSON (no pickle — NEVER).
        try:
            token_json = self._credentials.to_json()
            # The token lives at ``self._credentials_path``; SOPS-decrypted
            # filesystem, so plain ``open(..., "w")`` is acceptable.
            with open(
                self._credentials_path,
                "w",
                encoding="utf-8",
            ) as fh:
                fh.write(token_json)
            self._log.debug(
                "calendar_token_saved",
                credentials_path=self._credentials_path,
            )
        except OSError as exc:
            # Non-fatal — the token is refreshed in-memory; the next refresh
            # will retry persistence.
            self._log.warning(
                "calendar_token_save_failed",
                credentials_path=self._credentials_path,
                error_type=type(exc).__name__,
            )

    # -- 429 retry wrapper -------------------------------------------------

    def _retry_with_backoff(
        self,
        method_name: str,
        one_shot: Any,
    ) -> Any:
        """Run *one_shot* and retry-with-backoff on 429 (P22 F09 fix).

        *one_shot* is a callable that re-executes the API call (returning
        the response). On ``RateLimitExceededError`` raised by the Calendar
        helpers, sleep exponentially (1s/2s/4s), up to 3 retries. After
        exhaustion, re-raise so the upstream caller (adapter → router)
        surfaces it via the audit journal.

        Args:
            method_name: For logging only.
            one_shot: Zero-arg callable that performs the API call.

        Returns:
            Whatever *one_shot* returns (parsed response).

        Raises:
            RateLimitExceededError: After 3 retries are exhausted.
            ConfigurationMissingError / other exceptions propagate
            unchanged.
        """
        for attempt in range(_CALENDAR_MAX_RETRIES + 1):
            try:
                return one_shot()
            except RateLimitExceededError as exc:
                if attempt >= _CALENDAR_MAX_RETRIES:
                    self._log.warning(
                        "calendar_429_retries_exhausted",
                        method=method_name,
                        attempts=attempt + 1,
                    )
                    raise
                backoff = _CALENDAR_RETRY_BACKOFFS[
                    min(attempt, len(_CALENDAR_RETRY_BACKOFFS) - 1)
                ]
                # Honour Retry-After if larger.
                sleep_for = (
                    max(backoff, exc.retry_after)
                    if exc.retry_after is not None else backoff
                )
                self._log.warning(
                    "calendar_429_retry",
                    method=method_name,
                    attempt=attempt + 1,
                    sleep_for=sleep_for,
                    retry_after=exc.retry_after,
                )
                time.sleep(sleep_for)

    # -- pre-flight --------------------------------------------------------

    def health(self) -> bool:
        """Return True if ``calendarList().list().execute()`` succeeds.

        On 401 we opportunistically refresh once and retry; repeated
        401s or any other API error map to ``False``. NEVER raises.
        Token values are NEVER logged.
        """
        if self._service is None:
            return False

        try:
            response = (
                self._service.calendarList().list().execute()
            )
            return bool(response.get("items"))
        except Exception as exc:
            # HttpError import is lazy — but ``exc`` is the typed failure.
            # We do NOT log ``str(exc)`` directly because Google's
            # HttpError stringifies may include the failing URL only —
            # never the token — but we still scrub via "error_type".
            error_type = type(exc).__name__
            status = getattr(
                getattr(exc, "resp", None), "status", None,
            )

            if status == 401:
                self._log.info(
                    "calendar_health_401_retry",
                    error_type=error_type,
                )
                try:
                    self._do_refresh()
                    self._service = self._build_service(self._credentials)
                    response = (
                        self._service.calendarList().list().execute()
                    )
                    return bool(response.get("items"))
                except Exception as exc2:
                    self._log.warning(
                        "calendar_health_401_retry_failed",
                        error_type=type(exc2).__name__,
                    )
                    return False

            self._log.warning(
                "calendar_health_error",
                error_type=error_type,
                status=status,
            )
            return False

    # -- CRUD --------------------------------------------------------------

    def list_events(
        self,
        calendar_id: str = "primary",
        max_results: int = 50,
    ) -> list[dict[str, Any]]:
        """List events on *calendar_id* (default ``primary``).

        Returns the ``items`` list from the Calendar API response (each
        item is a dict). Empty list on no items. Raises
        ``ConfigurationMissingError`` if the underlying service lost
        its credentials mid-flight.
        """
        if self._service is None:
            _fail_missing(
                "Calendar client: service not built (no credentials)",
            )

        def _do_list_events():
            try:
                return (
                    self._service.events()
                    .list(
                        calendarId=calendar_id,
                        maxResults=max_results,
                    )
                    .execute()
                )
            except Exception as exc:
                error_type = type(exc).__name__
                status = getattr(
                    getattr(exc, "resp", None), "status", None,
                )
                if status == 401:
                    # Opportunistic refresh-then-retry on 401.
                    try:
                        self._do_refresh()
                        self._service = self._build_service(self._credentials)
                        return (
                            self._service.events()
                            .list(
                                calendarId=calendar_id,
                                maxResults=max_results,
                            )
                            .execute()
                        )
                    except Exception as exc2:
                        self._log.warning(
                            "calendar_list_events_401_retry_failed",
                            calendar_id=calendar_id,
                            error_type=type(exc2).__name__,
                        )
                        _fail_missing(
                            "Calendar client: list_events authentication "
                            "recovery failed",
                        )
                elif status == 429:
                    _handle_http_error(exc, "list_events")
                else:
                    self._log.error(
                        "calendar_list_events_failed",
                        calendar_id=calendar_id,
                        error_type=error_type,
                        status=status,
                    )
                    _handle_http_error(exc, "list_events")

        response = self._retry_with_backoff("list_events", _do_list_events)

        items = response.get("items", [])
        self._log.info(
            "calendar_list_events_ok",
            calendar_id=calendar_id,
            count=len(items) if isinstance(items, list) else 0,
        )
        return list(items) if isinstance(items, list) else []

    def get_event(
        self,
        calendar_id: str,
        event_id: str,
    ) -> dict[str, Any]:
        """Fetch a single Calendar event by ID.

        Returns the raw event dict. Raises ``ConfigurationMissingError``
        on auth/transport failure.
        """
        if self._service is None:
            _fail_missing(
                "Calendar client: service not built (no credentials)",
            )
        if not event_id:
            _fail_missing(
                "Calendar client: get_event requires event_id",
            )

        def _do_get_event():
            try:
                return (
                    self._service.events()
                    .get(
                        calendarId=calendar_id,
                        eventId=event_id,
                    )
                    .execute()
                )
            except Exception as exc:
                error_type = type(exc).__name__
                status = getattr(
                    getattr(exc, "resp", None), "status", None,
                )
                if status == 401:
                    try:
                        self._do_refresh()
                        self._service = self._build_service(self._credentials)
                        return (
                            self._service.events()
                            .get(
                                calendarId=calendar_id,
                                eventId=event_id,
                            )
                            .execute()
                        )
                    except Exception as exc2:
                        self._log.warning(
                            "calendar_get_event_401_retry_failed",
                            event_id=event_id,
                            error_type=type(exc2).__name__,
                        )
                        _fail_missing(
                            "Calendar client: get_event authentication "
                            "recovery failed",
                        )
                elif status == 429:
                    _handle_http_error(exc, "get_event")
                else:
                    self._log.error(
                        "calendar_get_event_failed",
                        event_id=event_id,
                        error_type=error_type,
                        status=status,
                    )
                    _handle_http_error(exc, "get_event")

        response = self._retry_with_backoff("get_event", _do_get_event)

        return response if isinstance(response, dict) else {}

    def create_event(
        self,
        event_data: dict[str, Any],
        calendar_id: str = "primary",
    ) -> dict[str, Any]:
        """Insert a new event.

        The P22 adapter signs as ``create_event(event_data)`` (no
        calendar_id); we accept an optional ``calendar_id`` keyword so
        callers can override the default. ``event_data`` follows the
        Calendar v3 ``Event`` resource schema.

        Returns the inserted event dict.
        """
        if self._service is None:
            _fail_missing(
                "Calendar client: service not built (no credentials)",
            )
        if not isinstance(event_data, dict):
            _fail_missing(
                "Calendar client: create_event requires dict event_data",
            )

        def _do_create_event():
            try:
                return (
                    self._service.events()
                    .insert(
                        calendarId=calendar_id,
                        body=event_data,
                    )
                    .execute()
                )
            except Exception as exc:
                error_type = type(exc).__name__
                status = getattr(
                    getattr(exc, "resp", None), "status", None,
                )
                if status == 401:
                    try:
                        self._do_refresh()
                        self._service = self._build_service(self._credentials)
                        return (
                            self._service.events()
                            .insert(
                                calendarId=calendar_id,
                                body=event_data,
                            )
                            .execute()
                        )
                    except Exception as exc2:
                        self._log.warning(
                            "calendar_create_event_401_retry_failed",
                            error_type=type(exc2).__name__,
                        )
                        _fail_missing(
                            "Calendar client: create_event "
                            "authentication recovery failed",
                        )
                elif status == 429:
                    _handle_http_error(exc, "create_event")
                else:
                    self._log.error(
                        "calendar_create_event_failed",
                        error_type=error_type,
                        status=status,
                    )
                    _handle_http_error(exc, "create_event")

        response = self._retry_with_backoff("create_event", _do_create_event)

        return response if isinstance(response, dict) else {}

    def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Replace *event_id* entirely on *calendar_id* via PUT (events().update).

        Per Google Calendar v3 quota (``google-workspace-full-access.md``
        §2.1):
          * ``events().update`` — 1 quota unit, full-replace
          * ``events().patch`` — 3 quota units, partial-merge

        ``update_event`` semantics in the P22 adapter contract call for
        a full replace (the event dict is the new canonical state), so
        we route to ``events().update`` (PUT) and pay 1 unit, not
        ``events().patch`` (3 units).

        Returns the updated event dict.
        """
        if self._service is None:
            _fail_missing(
                "Calendar client: service not built (no credentials)",
            )
        if not event_id:
            _fail_missing(
                "Calendar client: update_event requires event_id",
            )

        def _do_update_event():
            try:
                return (
                    self._service.events()
                    .update(
                        calendarId=calendar_id,
                        eventId=event_id,
                        body=event_data,
                    )
                    .execute()
                )
            except Exception as exc:
                error_type = type(exc).__name__
                status = getattr(
                    getattr(exc, "resp", None), "status", None,
                )
                if status == 401:
                    try:
                        self._do_refresh()
                        self._service = self._build_service(self._credentials)
                        return (
                            self._service.events()
                            .update(
                                calendarId=calendar_id,
                                eventId=event_id,
                                body=event_data,
                            )
                            .execute()
                        )
                    except Exception as exc2:
                        self._log.warning(
                            "calendar_update_event_401_retry_failed",
                            event_id=event_id,
                            error_type=type(exc2).__name__,
                        )
                        _fail_missing(
                            "Calendar client: update_event "
                            "authentication recovery failed",
                        )
                elif status == 429:
                    _handle_http_error(exc, "update_event")
                else:
                    self._log.error(
                        "calendar_update_event_failed",
                        event_id=event_id,
                        error_type=error_type,
                        status=status,
                    )
                    _handle_http_error(exc, "update_event")

        response = self._retry_with_backoff("update_event", _do_update_event)

        return response if isinstance(response, dict) else {}

    def delete_event(
        self,
        calendar_id: str,
        event_id: str,
    ) -> None:
        """Delete *event_id* on *calendar_id*.

        Calendar API has no native restore — the adapter orchestrates
        a pre-delete snapshot (``events.get``) before this call.
        """
        if self._service is None:
            _fail_missing(
                "Calendar client: service not built (no credentials)",
            )
        if not event_id:
            _fail_missing(
                "Calendar client: delete_event requires event_id",
            )

        def _do_delete_event():
            try:
                self._service.events().delete(
                    calendarId=calendar_id,
                    eventId=event_id,
                ).execute()
            except Exception as exc:
                error_type = type(exc).__name__
                status = getattr(
                    getattr(exc, "resp", None), "status", None,
                )
                if status == 401:
                    try:
                        self._do_refresh()
                        self._service = self._build_service(self._credentials)
                        self._service.events().delete(
                            calendarId=calendar_id,
                            eventId=event_id,
                        ).execute()
                    except Exception as exc2:
                        self._log.warning(
                            "calendar_delete_event_401_retry_failed",
                            event_id=event_id,
                            error_type=type(exc2).__name__,
                        )
                        _fail_missing(
                            "Calendar client: delete_event "
                            "authentication recovery failed",
                        )
                elif status == 429:
                    _handle_http_error(exc, "delete_event")
                else:
                    self._log.error(
                        "calendar_delete_event_failed",
                        event_id=event_id,
                        error_type=error_type,
                        status=status,
                    )
                    _handle_http_error(exc, "delete_event")

        self._retry_with_backoff("delete_event", _do_delete_event)

        self._log.info(
            "calendar_delete_event_ok",
            calendar_id=calendar_id,
            event_id=event_id,
        )
        return None


# ---- async wrapper --------------------------------------------------------

class AsyncCalendarClient:
    """Async wrapper around ``CalendarClient`` via ``asyncio.to_thread``.

    Mirrors ``AsyncGmailClient`` — every method delegates the synchronous
    CalendarClient call to a thread to keep the event loop unblocked.
    """

    def __init__(self, sync_client: CalendarClient) -> None:
        """Wrap a synchronous ``CalendarClient`` for async use."""
        self._client: CalendarClient = sync_client

    async def list_events(
        self,
        calendar_id: str,
        max_results: int,
    ) -> list[dict[str, Any]]:
        """Async ``CalendarClient.list_events``."""
        return await asyncio.to_thread(
            self._client.list_events,
            calendar_id,
            max_results,
        )

    async def get_event(
        self, calendar_id: str, event_id: str,
    ) -> dict[str, Any]:
        """Async ``CalendarClient.get_event``."""
        return await asyncio.to_thread(
            self._client.get_event,
            calendar_id,
            event_id,
        )

    async def create_event(
        self, event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Async ``CalendarClient.create_event``.

        The P22 adapter signs as ``create_event(event_data)``; we add
        ``calendar_id`` as a kwarg with a default of ``"primary"`` so
        the adapter's call site stays identical.
        """
        return await asyncio.to_thread(
            self._client.create_event,
            event_data,
            "primary",
        )

    async def update_event(
        self,
        calendar_id: str,
        event_id: str,
        event_data: dict[str, Any],
    ) -> dict[str, Any]:
        """Async ``CalendarClient.update_event``."""
        return await asyncio.to_thread(
            self._client.update_event,
            calendar_id,
            event_id,
            event_data,
        )

    async def delete_event(
        self, calendar_id: str, event_id: str,
    ) -> None:
        """Async ``CalendarClient.delete_event``."""
        return await asyncio.to_thread(
            self._client.delete_event,
            calendar_id,
            event_id,
        )

    async def health(self) -> bool:
        """Async ``CalendarClient.health``."""
        return await asyncio.to_thread(self._client.health)


__all__ = ["CalendarClient", "AsyncCalendarClient"]


# Sanity helper used by ops + tests — never call directly from adapters.
def safe_default_credentials_path() -> str:
    """Return the canonical SOPS credentials path."""
    return _DEFAULT_CREDENTIALS_PATH


def safe_default_scopes_serialised() -> str:
    """Return the default scopes as a stable JSON string (for audit logs).

    NEVER include any token material here — only the URL scope strings.
    """
    return json.dumps(sorted(_CALENDAR_DEFAULT_SCOPES), separators=(",", ":"))
