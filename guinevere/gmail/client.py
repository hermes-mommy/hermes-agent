from __future__ import annotations

"""Async Gmail API client wrapper with quota tracking and typed responses.

Wraps google-api-python-client with pre-flight quota checks, structured
logging, and typed exception mapping for every Gmail REST API call.
"""

import asyncio
import base64
import collections
import time
from datetime import datetime, timezone
from typing import Any, ClassVar, Final, Protocol

import structlog
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from .config import GmailSettings
from .envelope import GmailMessageEnvelope
from .exceptions import (
    GmailAPIError,
    HistoryExpiredError,
    MessageNotFoundError,
    QuotaExceededError,
    RateLimitError,
    ThreadNotFoundError,
)
from .metrics import set_quota_usage

_RETRY_AFTER_DEFAULT: Final[int] = 60
_MS_PER_SECOND: Final[int] = 1000


class _Executable(Protocol):
    """Minimal interface for google-api-python-client request objects."""

    def execute(self) -> dict[str, Any]: ...


# ---------------------------------------------------------------------------
# Quota tracker
# ---------------------------------------------------------------------------


class QuotaTracker:
    """Sliding-window counter for Gmail API quota (6 000 units/min).

    Tracks per-second consumption timestamps to compute rolling-window
    usage.  Call ``check`` before an API call and ``record`` after.
    """

    def __init__(self, limit_per_minute: int = 6000) -> None:
        self._limit: int = limit_per_minute
        self._window: collections.deque[float] = collections.deque()

    def _prune(self) -> None:
        """Remove timestamps older than 60 seconds."""
        cutoff = time.monotonic() - 60.0
        while self._window and self._window[0] < cutoff:
            self._window.popleft()

    def current_usage(self) -> int:
        """Return units consumed in the current 60-second window."""
        self._prune()
        return len(self._window)

    def check(self, units: int) -> None:
        """Pre-flight: raise ``QuotaExceededError`` if *units* won't fit.

        Does not consume quota — call ``record`` after a successful API
        call to actually register the usage.
        """
        self._prune()
        projected = len(self._window) + units
        if projected > self._limit:
            raise QuotaExceededError(
                retry_after_seconds=_RETRY_AFTER_DEFAULT,
            )

    def record(self, units: int) -> None:
        """Record *units* of quota consumed after a successful API call."""
        now = time.monotonic()
        for _ in range(units):
            self._window.append(now)
        self._prune()
        set_quota_usage(float(self.current_usage()))

    def reset_window(self) -> None:
        """Clear all recorded usage (e.g. after long idle)."""
        self._window.clear()
        set_quota_usage(0.0)


# ---------------------------------------------------------------------------
# Sync client
# ---------------------------------------------------------------------------


class GmailClient:
    """Synchronous Gmail API client with quota tracking and typed errors.

    Every API call is pre-flight checked against the quota window,
    logged with ``structlog``, and wrapped so ``HttpError`` is translated
    into the module-specific exception hierarchy.
    """

    QUOTA_COSTS: ClassVar[dict[str, int]] = {
        "messages.list": 5,
        "messages.get": 5,
        "messages.send": 100,
        "history.list": 2,
        "labels.list": 1,
        "threads.get": 10,
        "drafts.create": 10,
        "drafts.send": 100,
        "users.watch": 100,
        "users.stop": 100,
        "users.getProfile": 5,
    }

    def __init__(
        self,
        credentials: Credentials,
        settings: GmailSettings,
    ) -> None:
        self._tracker: QuotaTracker = QuotaTracker(
            settings.api_quota_limit_per_minute,
        )
        self._log = structlog.get_logger(__name__)
        self._last_history_id: str | None = None

        if credentials is None:
            raise ValueError("credentials must not be None")

        self._service: Resource = build(
            "gmail",
            "v1",
            credentials=credentials,
            cache_discovery=False,
        )

    # -- helpers ----------------------------------------------------------

    def _retry_after(self, error: HttpError) -> int:
        """Extract ``Retry-After`` header from an HTTP error."""
        retry = error.headers.get("retry-after")
        if retry is not None:
            try:
                return max(int(retry), 1)
            except (ValueError, TypeError):
                pass
        return _RETRY_AFTER_DEFAULT

    def _map_error(
        self, operation: str, error: HttpError,
    ) -> Exception:
        """Translate ``HttpError`` into typed Gmail exceptions."""
        status = error.resp.status

        if status == 429:
            return RateLimitError(self._retry_after(error))

        if status == 403:
            return QuotaExceededError(self._retry_after(error))

        if status == 404:
            if operation == "threads.get":
                tid = self._extract_id_from_uri(error.uri)
                return ThreadNotFoundError(tid)
            if operation == "history.list":
                hid = self._last_history_id or "unknown"
                return HistoryExpiredError(hid)
            mid = self._extract_id_from_uri(error.uri)
            return MessageNotFoundError(mid)

        return GmailAPIError(
            f"{operation} failed: HTTP {status} - {error}",
        )

    @staticmethod
    def _extract_id_from_uri(uri: str | None) -> str:
        """Best-effort trailing ID extraction from a Gmail URI."""
        if uri:
            parts = uri.rstrip("/").split("/")
            if parts:
                return parts[-1]
        return "unknown"

    def _api_call(
        self,
        operation: str,
        request: _Executable,
    ) -> dict[str, Any]:
        """Execute *request* with quota check and error mapping."""
        cost = self.QUOTA_COSTS.get(operation, 5)
        self._tracker.check(cost)

        start = time.monotonic()
        try:
            result = request.execute()
        except HttpError as exc:
            raise self._map_error(operation, exc) from exc

        elapsed_ms = (time.monotonic() - start) * _MS_PER_SECOND
        self._tracker.record(cost)
        self._log.info(
            "gmail_api_call",
            operation=operation,
            cost=cost,
            latency_ms=round(elapsed_ms, 1),
        )
        return result

    # -- messages ---------------------------------------------------------

    def list_messages(
        self,
        query: str = "",
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List message IDs matching *query*.

        Returns the raw API response including ``messages``,
        ``nextPageToken``, and ``resultSizeEstimate``.
        """
        params: dict[str, int | str] = {
            "maxResults": max_results,
        }
        if query:
            params["q"] = query
        if page_token:
            params["pageToken"] = page_token

        request = self._service.users().messages().list(
            userId="me", **params,
        )
        return self._api_call("messages.list", request)

    def get_message(
        self,
        message_id: str,
        format: str = "full",
    ) -> dict[str, Any]:
        """Fetch a single message by *message_id*.

        *format*: ``full``, ``metadata``, ``raw``, or ``minimal``.
        """
        request = self._service.users().messages().get(
            userId="me", id=message_id, format=format,
        )
        return self._api_call("messages.get", request)

    def send_message(
        self, message: dict[str, Any],
    ) -> dict[str, Any]:
        """Send a raw MIME message dict via the API.

        Returns the sent message resource including ``id`` and
        ``historyId``.
        """
        request = self._service.users().messages().send(
            userId="me", body=message,
        )
        return self._api_call("messages.send", request)

    # -- threads ----------------------------------------------------------

    def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Fetch a full thread including all messages."""
        request = self._service.users().threads().get(
            userId="me", id=thread_id,
        )
        return self._api_call("threads.get", request)

    # -- history ----------------------------------------------------------

    def list_history(
        self,
        start_history_id: str,
        history_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """List mailbox changes since *start_history_id*.

        Raises ``HistoryExpiredError`` when the server no longer retains
        history from the requested starting point.
        """
        params: dict[str, str | list[str]] = {
            "startHistoryId": start_history_id,
        }
        if history_types:
            params["historyTypes"] = history_types

        request = self._service.users().history().list(
            userId="me", **params,
        )
        result = self._api_call("history.list", request)

        new_hid = result.get("historyId")
        if new_hid is not None:
            self._last_history_id = str(new_hid)

        return result

    # -- labels -----------------------------------------------------------

    def list_labels(self) -> list[dict[str, Any]]:
        """Return all labels for the authenticated user."""
        request = self._service.users().labels().list(
            userId="me",
        )
        response = self._api_call("labels.list", request)
        return response.get("labels", [])

    # -- drafts -----------------------------------------------------------

    def create_draft(
        self, message: dict[str, Any],
    ) -> dict[str, Any]:
        """Create a new draft from *message* (raw MIME dict).

        Returns the draft resource including ``id`` and ``message``.
        """
        request = self._service.users().drafts().create(
            userId="me", body={"message": message},
        )
        return self._api_call("drafts.create", request)

    def send_draft(self, draft_id: str) -> dict[str, Any]:
        """Send an existing draft by *draft_id*.

        Returns the sent message resource.
        """
        request = self._service.users().drafts().send(
            userId="me", body={"id": draft_id},
        )
        return self._api_call("drafts.send", request)

    # -- watch / profile --------------------------------------------------

    def watch(
        self,
        topic_name: str,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Register push notifications on *topic_name*.

        Returns the watch response including ``expiration``.
        """
        body: dict[str, str | list[str]] = {
            "topicName": topic_name,
        }
        if label_ids:
            body["labelIds"] = label_ids

        request = self._service.users().watch(
            userId="me", body=body,
        )
        return self._api_call("users.watch", request)

    def stop_watch(self) -> None:
        """Stop push notifications for the authenticated user."""
        request = self._service.users().stop(userId="me")
        self._api_call("users.stop", request)

    def get_profile(self) -> dict[str, Any]:
        """Return the authenticated user's Gmail profile."""
        request = self._service.users().getProfile(userId="me")
        return self._api_call("users.getProfile", request)

    # -- escape hatch -----------------------------------------------------

    @property
    def service(self) -> Resource:
        """Direct access to the underlying ``Resource``."""
        return self._service


# ---------------------------------------------------------------------------
# Async wrapper
# ---------------------------------------------------------------------------


class AsyncGmailClient:
    """Async wrapper around ``GmailClient`` via ``asyncio.to_thread``.

    Every method delegates to the synchronous client in a thread pool,
    keeping the event loop unblocked.
    """

    def __init__(self, sync_client: GmailClient) -> None:
        self._client: GmailClient = sync_client

    async def list_messages(
        self,
        query: str = "",
        max_results: int = 100,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """Async ``GmailClient.list_messages``."""
        return await asyncio.to_thread(
            self._client.list_messages,
            query, max_results, page_token,
        )

    async def get_message(
        self,
        message_id: str,
        format: str = "full",
    ) -> dict[str, Any]:
        """Async ``GmailClient.get_message``."""
        return await asyncio.to_thread(
            self._client.get_message, message_id, format,
        )

    async def send_message(
        self, message: dict[str, Any],
    ) -> dict[str, Any]:
        """Async ``GmailClient.send_message``."""
        return await asyncio.to_thread(
            self._client.send_message, message,
        )

    async def get_thread(
        self, thread_id: str,
    ) -> dict[str, Any]:
        """Async ``GmailClient.get_thread``."""
        return await asyncio.to_thread(
            self._client.get_thread, thread_id,
        )

    async def list_history(
        self,
        start_history_id: str,
        history_types: list[str] | None = None,
    ) -> dict[str, Any]:
        """Async ``GmailClient.list_history``."""
        return await asyncio.to_thread(
            self._client.list_history,
            start_history_id, history_types,
        )

    async def list_labels(self) -> list[dict[str, Any]]:
        """Async ``GmailClient.list_labels``."""
        return await asyncio.to_thread(
            self._client.list_labels,
        )

    async def create_draft(
        self, message: dict[str, Any],
    ) -> dict[str, Any]:
        """Async ``GmailClient.create_draft``."""
        return await asyncio.to_thread(
            self._client.create_draft, message,
        )

    async def send_draft(
        self, draft_id: str,
    ) -> dict[str, Any]:
        """Async ``GmailClient.send_draft``."""
        return await asyncio.to_thread(
            self._client.send_draft, draft_id,
        )

    async def watch(
        self,
        topic_name: str,
        label_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Async ``GmailClient.watch``."""
        return await asyncio.to_thread(
            self._client.watch, topic_name, label_ids,
        )

    async def stop_watch(self) -> None:
        """Async ``GmailClient.stop_watch``."""
        await asyncio.to_thread(self._client.stop_watch)

    async def get_profile(self) -> dict[str, Any]:
        """Async ``GmailClient.get_profile``."""
        return await asyncio.to_thread(
            self._client.get_profile,
        )


# ---------------------------------------------------------------------------
# Envelope parser
# ---------------------------------------------------------------------------


def parse_message_to_envelope(
    raw: dict[str, Any],
) -> GmailMessageEnvelope:
    """Parse a Gmail API message response into a typed envelope.

    Extracts headers, body content, and metadata from the raw API
    response and constructs a ``GmailMessageEnvelope``.
    """
    log = structlog.get_logger(__name__)
    message_id: str = raw.get("id", "")
    thread_id: str = raw.get("threadId", "")
    snippet: str = raw.get("snippet", "")
    label_ids: list[str] = raw.get("labelIds", [])

    payload: dict[str, Any] = raw.get("payload", {})
    headers = _headers_to_map(payload)

    sender = headers.get("from", "")
    to_raw = headers.get("to", "")
    recipients = [
        a.strip()
        for a in to_raw.split(",")
        if a.strip()
    ] if to_raw else []
    subject = headers.get("subject", "").strip() or "(no subject)"
    in_reply_to = headers.get("in-reply-to") or None
    references_raw = headers.get("references")
    references = (
        references_raw.split() if references_raw else None
    )

    body_text, body_html = _extract_multipart_body(payload)

    internal_ts = raw.get("internalDate")
    if internal_ts is not None:
        timestamp = datetime.fromtimestamp(
            int(internal_ts) / 1000, tz=timezone.utc,
        )
    else:
        timestamp = datetime.now(tz=timezone.utc)

    has_attachments = _count_parts(payload) > 1

    try:
        return GmailMessageEnvelope(
            message_id=message_id,
            thread_id=thread_id,
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
            timestamp=timestamp,
            labels=label_ids,
            snippet=snippet,
            has_attachments=has_attachments,
            in_reply_to=in_reply_to,
            references=references,
        )
    except Exception:
        log.error(
            "envelope_parse_failed",
            message_id=message_id,
            thread_id=thread_id,
            subject_len=len(subject),
            sender=sender,
        )
        raise


def _headers_to_map(
    payload: dict[str, Any],
) -> dict[str, str]:
    """Convert the Gmail header list into a lowercase-keyed dict."""
    result: dict[str, str] = {}
    for header in payload.get("headers", []):
        name: str = header.get("name", "")
        value: str = header.get("value", "")
        result[name.lower()] = value
    return result


def _extract_multipart_body(
    payload: dict[str, Any],
) -> tuple[str, str]:
    """Walk message parts and return (text, html) body content."""
    mime_type: str = payload.get("mimeType", "")

    if mime_type.startswith("multipart/"):
        parts: list[dict[str, Any]] = payload.get("parts", [])
        return _walk_parts(parts)

    body_data: str = payload.get("body", {}).get("data", "")
    decoded = _safe_decode_body(body_data)

    if mime_type == "text/html":
        return ("", decoded)
    return (decoded, "")


def _walk_parts(
    parts: list[dict[str, Any]],
) -> tuple[str, str]:
    """Recursively search *parts* for text/plain and text/html."""
    text = ""
    html = ""

    for part in parts:
        mime: str = part.get("mimeType", "")

        if mime.startswith("multipart/"):
            nested = _walk_parts(
                part.get("parts", []),
            )
            if nested[0] and not text:
                text = nested[0]
            if nested[1] and not html:
                html = nested[1]
            continue

        body_data: str = part.get("body", {}).get(
            "data", "",
        )
        if not body_data:
            continue

        decoded = _safe_decode_body(body_data)

        if mime == "text/plain" and not text:
            text = decoded
        elif mime == "text/html" and not html:
            html = decoded

    return (text, html)


def _safe_decode_body(encoded: str) -> str:
    """Decode a base64url-encoded Gmail body payload."""
    if not encoded:
        return ""
    try:
        return base64.urlsafe_b64decode(encoded).decode(
            "utf-8", errors="replace",
        )
    except (ValueError, UnicodeDecodeError):
        return ""


def _count_parts(payload: dict[str, Any]) -> int:
    """Count total MIME parts in *payload* (including nested)."""
    parts: list[dict[str, Any]] = payload.get("parts", [])
    if not parts:
        return 1
    count = len(parts)
    for part in parts:
        count += _count_parts(part) - 1
    return count
