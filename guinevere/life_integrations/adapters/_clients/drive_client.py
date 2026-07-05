"""P22 Google Drive API client — wraps google-api-python-client ``drive v3``.

The P22 ``DriveIntegrationAdapter`` calls instance methods on its
``drive_client`` collaborator. This module is the production-grade
implementation that talks to the real Google Drive API.

Mirrors the GmailClient/TokenManager pattern, but stays self-contained:
  * Lazy import of ``googleapiclient.discovery`` + ``google.oauth2.credentials``
    so that ``google-api-python-client`` is only required when someone
    actually instantiates a Drive client (preserves minimal-container
    import-time performance).
  * Constructor takes ``credentials_path`` + ``scopes``; constructs the
    underlying ``Credentials`` via ``Credentials.from_authorized_user_file``.
  * Exposes the methods the adapter expects (research/google-workspace-full-access.md §3, §7):
        list_files()              → files().list(...)            (L1)
        get_file(file_id)         → files().get(...)             (L1)
        create_file(meta, media)  → files().create(...)  + MediaFileUpload (L2)
        update_file(file_id, meta)→ files().update(...)          (L2)
        trash_file(file_id)       → files().update({trashed:true}) (L2)
        delete_file(file_id, force=False)
                                  → files().delete(...)          (L3)
                                    with TRASH-FIRST policy enforcement
        create_permission(file_id, type, role)
                                  → permissions().create(...)    (L3 public)
        health()                  → about().get(...) → bool      (liveness)
  * Never logs the token; never persists pickled credentials; constructor
    uses ``from_authorized_user_file`` only.
  * On 401 (``HttpError`` with status==401), retry once after a forced
    credential refresh.
  * Trash-first policy: ``delete_file`` without ``force=True`` raises if the
    file is not already trashed. The adapter's pre-delete export runs FIRST,
    so the client refuses to begin a permanent delete on a live file unless
    the caller has explicitly opted in.
  * Lazy ``ConfigurationMissingError`` when ``google-api-python-client`` is
    not importable in the runtime environment — no fake PASS.

Forbidden patterns (per task spec):
  * No ``# type: ignore``.
  * No ``as any``.
  * No printing/hardcoding of token/credentials.
  * No ``except:`` (only explicit error classes).
  * No ``pickle.dumps`` / ``pickle.load`` for credentials.
  * No token emitted in any log line / exception message.
  * delete_file bypass of trash-first policy is rejected.

Lazy import: ``google-api-python-client``, ``google.oauth2.credentials``,
``googleapiclient.errors``. All imports happen on demand inside
``__init__`` / method calls.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import TYPE_CHECKING, Any, Final

import structlog

from guinevere.life_integrations.errors import (
    ConfigurationMissingError,
    PermissionDeniedError,
    ProviderError,
    RateLimitExceededError,
)

if TYPE_CHECKING:  # pragma: no cover - typing-only helper
    from googleapiclient.errors import HttpError as _HttpErrorType

logger = structlog.get_logger(__name__)

# Default Drive scopes — drive.file is the minimal per-app OAuth scope that
# does NOT require CASA (Cloud Application Security Assessment) tier-3.
# Other possible scope: drive (full), drive.readonly, drive.activity,
# drive.metadata.readonly. research/google-workspace-full-access.md §7.
_DEFAULT_SCOPES: tuple[str, ...] = (
    "https://www.googleapis.com/auth/drive.file",
)

_FIELDS_FILE_LIST: str = "nextPageToken,files(id,name,mimeType,modifiedTime,size,trashed)"
_PAGE_SIZE: int = 100

# Trash-first policy
_TRASH_FIRST_POLICY_MESSAGE: str = (
    "TRASH-FIRST POLICY: cannot permanently delete a live file. "
    "Call trash_file() first (30-day recovery window), or pass force=True "
    "to opt out of the safety check."
)

# HTTP status codes we map to typed errors
_HTTP_UNAUTHORIZED: int = 401
_HTTP_FORBIDDEN: int = 403
_HTTP_NOT_FOUND: int = 404
_HTTP_RATE_LIMIT: int = 429

# 429 retry/backoff configuration (P22 brutal-audit F09).
# 1s/2s/4s exponential, max 3 retries.
_DRIVE_RETRY_BACKOFFS: Final[tuple[int, ...]] = (1, 2, 4)
_DRIVE_MAX_RETRIES: Final[int] = 3


def _require_google_api_client() -> tuple[Any, Any, Any, Any]:
    """Lazy-import google-api-python-client pieces.

    Returns:
        Tuple of ``(build, HttpError, MediaFileUpload, Credentials)``.

    Raises:
        ConfigurationMissingError: If ``google-api-python-client`` or
            ``google-auth`` is not installed in this environment.
    """
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError as exc:  # pragma: no cover - environment-specific
        raise ConfigurationMissingError(
            "Google Drive client requires 'google-api-python-client' and "
            "'google-auth' to be installed in the runtime environment; "
            "missing import: "
            f"{exc.name}. Install both with pip before instantiating DriveClient."
        ) from exc

    return build, HttpError, MediaFileUpload, Credentials


def build_drive_service(credentials: Any) -> tuple[Any, Any]:
    """Module-level wrapper around ``googleapiclient.discovery.build``.

    Returns a ``(service, HttpError)`` tuple. ``HttpError`` is the class
    type, so the caller can use it for ``isinstance`` checks in the
    retry layer.

    Raises:
        ConfigurationMissingError: If the runtime is missing the
            google-api-python-client library.
    """
    build, HttpError, _, _ = _require_google_api_client()
    service = build(
        "drive",
        "v3",
        credentials=credentials,
        cache_discovery=False,
    )
    return service, HttpError


class DriveClient:
    """Synchronous Google Drive v3 client with trash-first delete policy.

    Mirrors the ``GmailClient`` class. Constructed with:
      * ``credentials_path``: filesystem path to a SOPS-decrypted OAuth
        JSON token (NOT a pickle).
      * ``scopes``: list of OAuth scopes; defaults to ``drive.file``
        (per-app scope, no CASA).
      * Optional ``credentials`` override — pre-built google-auth
        Credentials object (used in tests; production wires via path).

    All Drive REST calls are wrapped in a small quota tracker
    (no per-second limits, just a counter) and a single forced-refresh
    retry on 401.

    Methods on this class are synchronous; the adapter invokes them
    from inside ``asyncio.to_thread`` if it needs non-blocking calls.
    The adapter signature here matches the call sites in
    ``guinevere/life_integrations/adapters/drive_adapter.py``.
    """

    def __init__(
        self,
        credentials_path: str = "/run/guinevere/drive-token.json",
        scopes: list[str] | None = None,
        credentials: Any | None = None,
    ) -> None:
        """Initialize Drive client.

        Args:
            credentials_path: Path to OAuth credentials JSON (NOT pickle).
            scopes: OAuth scopes list. Defaults to ``drive.file``.
            credentials: Override credentials object (test injection).

        Raises:
            ConfigurationMissingError: If ``google-api-python-client`` is
                not installed, or if the credentials file is missing /
                invalid (fail-closed — no fake success).
        """
        self._credentials_path: str = credentials_path
        self._scopes: list[str] = list(scopes) if scopes else list(_DEFAULT_SCOPES)
        self._service: Any = None
        self._HttpError: Any = None  # cached class for isinstance checks
        self._credentials_obj: Any = credentials

        if credentials is not None:
            # Pre-built credentials (test path or production LongTerm)
            self._service = self._build_service(credentials)
            return

        # Production path: load from JSON file
        path = Path(credentials_path)
        if not path.exists():
            raise ConfigurationMissingError(
                "Google Drive credentials file not found at "
                f"{credentials_path} — sec-google-drive-oauth not provisioned"
            )

        _, _, _, Credentials = _require_google_api_client()

        try:
            credentials = Credentials.from_authorized_user_file(
                str(path), self._scopes,
            )
        except (ValueError, OSError) as exc:
            raise ConfigurationMissingError(
                f"Google Drive credentials file at {credentials_path} is "
                f"invalid or unreadable: {type(exc).__name__}"
            ) from exc

        # Sanity: scopes must match (don't silently downgrade)
        granted = set(getattr(credentials, "scopes", []) or [])
        required = set(self._scopes)
        missing = required - granted
        if missing:
            raise ConfigurationMissingError(
                "Google Drive credentials are missing required scopes: "
                f"{sorted(missing)}. Re-authorize with drive.file."
            )

        self._credentials_obj = credentials
        self._service = self._build_service(credentials)

    # -- service construction ---------------------------------------------

    def _build_service(self, credentials: Any) -> Any:
        """Build (or rebuild) the Drive v3 service Resource.

        Delegates to the module-level ``build_drive_service`` so unit tests
        can mock the build boundary without monkey-patching the class
        itself.
        """
        service, http_error = build_drive_service(credentials)
        self._HttpError = http_error
        return service

    # -- helpers -----------------------------------------------------------

    @staticmethod
    def _parse_retry_after(exc: Any) -> int | None:
        """Best-effort Retry-After header parser for HttpError.

        Returns the integer seconds if present, else ``None``.
        """
        try:
            headers = getattr(getattr(exc, "resp", None), "headers", None) or {}
            raw = headers.get("Retry-After") if hasattr(headers, "get") else None
            if raw is None:
                return None
            return max(0, int(str(raw).strip()))
        except (TypeError, ValueError, AttributeError):
            return None

    def _refresh_credentials(self) -> None:
        """Force-refresh underlying credentials and rebuild the service.

        Called when a Drive API call returns 401. Uses google-auth's
        built-in ``credentials.refresh`` over ``google.auth.transport.requests.Request``.
        On failure, raises ``ConfigurationMissingError`` (no fake PASS).
        """
        creds = self._credentials_obj
        if creds is None or not getattr(creds, "refresh_token", None):
            raise ConfigurationMissingError(
                "Google Drive token expired and no refresh_token available; "
                "re-authorize sec-google-drive-oauth."
            )

        try:
            from google.auth.transport.requests import Request
        except ImportError as exc:  # pragma: no cover
            raise ConfigurationMissingError(
                "google-auth transport missing — cannot refresh Drive token"
            ) from exc

        try:
            creds.refresh(Request())
        except Exception as exc:
            logger.warning(
                "drive.client.refresh_failed",
                error_type=type(exc).__name__,
            )
            raise ConfigurationMissingError(
                f"Google Drive token refresh failed: {type(exc).__name__}"
            ) from exc

        self._service = self._build_service(creds)

    def _call_with_retry(self, request_factory: Any) -> dict[str, Any]:
        """Execute a request, retrying once on 401 after refresh.

        Args:
            request_factory: Callable returning a fresh request object
                each call (``self._service.files().get(...)`` etc.).

        Returns:
            Parsed ``execute()`` body as dict.

        Raises:
            RateLimitExceededError: After 3 retries on 429.
            ProviderError: For non-401/non-429 Drive API errors.
            PermissionDeniedError: On 403.
            ConfigurationMissingError: For hardened token failures.
        """
        for _drive_attempt in range(_DRIVE_MAX_RETRIES + 1):
            try:
                return request_factory().execute()
            except self._HttpError as exc:
                status = getattr(exc.resp, "status", 0)
                if status == _HTTP_UNAUTHORIZED:
                    logger.info(
                        "drive.client.unauthorized_refreshing",
                        status=status,
                    )
                    self._refresh_credentials()
                    try:
                        return request_factory().execute()
                    except self._HttpError as exc2:
                        logger.warning(
                            "drive.client.unauthorized_after_refresh",
                            status=getattr(exc2.resp, "status", 0),
                        )
                        raise ConfigurationMissingError(
                            "Google Drive auth failed even after refresh"
                        ) from exc2
                if status == _HTTP_FORBIDDEN:
                    raise PermissionDeniedError(
                        f"Google Drive permission denied (HTTP {status}): {exc}"
                    ) from exc
                if status == _HTTP_RATE_LIMIT:
                    if _drive_attempt < _DRIVE_MAX_RETRIES:
                        retry_after = self._parse_retry_after(exc)
                        backoff = _DRIVE_RETRY_BACKOFFS[
                            min(_drive_attempt, len(_DRIVE_RETRY_BACKOFFS) - 1)
                        ]
                        sleep_for = (
                            max(backoff, retry_after)
                            if retry_after is not None else backoff
                        )
                        logger.warning(
                            "drive.client.429_retry",
                            attempt=_drive_attempt + 1,
                            sleep_for=sleep_for,
                            retry_after=retry_after,
                        )
                        time.sleep(sleep_for)
                        continue
                    logger.warning(
                        "drive.client.429_retries_exhausted",
                        attempts=_drive_attempt + 1,
                    )
                    raise RateLimitExceededError(
                        provider="google-drive",
                        retry_after=self._parse_retry_after(exc),
                    ) from exc
                raise ProviderError(
                    "Google Drive", status,
                    str(exc),
                ) from exc

    # -- Drive API methods -------------------------------------------------

    def list_files(
        self,
        page_size: int = _PAGE_SIZE,
        page_token: str | None = None,
        fields: str = _FIELDS_FILE_LIST,
    ) -> list[dict[str, Any]]:
        """List files (L1). Returns the ``files`` list from the response."""
        log = logger.bind(op="list_files")

        def _request():
            kwargs: dict[str, Any] = {
                "pageSize": page_size,
                "fields": fields,
            }
            if page_token:
                kwargs["pageToken"] = page_token
            return self._service.files().list(**kwargs)

        result = self._call_with_retry(_request)
        files = result.get("files", [])
        log.info(
            "drive.client.list_files",
            count=len(files),
        )
        return files

    def get_file(self, file_id: str) -> dict[str, Any]:
        """Fetch file metadata by id (L1)."""
        # include ``trashed`` field so we can enforce trash-first without
        # an extra API call when delete_file is invoked.
        def _request():
            return self._service.files().get(
                fileId=file_id,
                fields="id,name,mimeType,modifiedTime,size,trashed",
            )

        result = self._call_with_retry(_request)
        return result

    def create_file(
        self,
        metadata: dict[str, Any],
        media_path: str | None = None,
    ) -> dict[str, Any]:
        """Create a file (L2).

        If ``media_path`` is provided, attaches a MediaFileUpload so the
        underlying google-api-python-client handles multipart upload
        (resumable for >5 MB transparently).
        """
        _, _, MediaFileUpload, _ = _require_google_api_client()

        def _request():
            media_body = (
                MediaFileUpload(media_path, resumable=True)
                if media_path
                else None
            )
            kwargs: dict[str, Any] = {"body": metadata}
            if media_body is not None:
                kwargs["media_body"] = media_body
            return self._service.files().create(**kwargs)

        try:
            result = self._call_with_retry(_request)
        finally:
            logger.info(
                "drive.client.create_file",
                has_media=bool(media_path),
                name=str(metadata.get("name", "")),
            )
        return result

    def update_file(
        self,
        file_id: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Update file metadata (L2). Does NOT touch media content."""
        def _request():
            return self._service.files().update(
                fileId=file_id, body=metadata,
            )

        result = self._call_with_retry(_request)
        return result

    def trash_file(self, file_id: str) -> dict[str, Any]:
        """Move file to trash (L2, reversible 30 days).

        Performs ``files().update(fileId, body={"trashed": true})`` per
        research google-workspace-full-access.md §3.
        """
        def _request():
            return self._service.files().update(
                fileId=file_id, body={"trashed": True},
            )

        result = self._call_with_retry(_request)
        result.setdefault("trashed", True)
        return result

    def delete_file(
        self,
        file_id: str,
        force: bool = False,
    ) -> dict[str, Any]:
        """Permanently delete a file (L3, irreversible).

        Policy:
          * ``force=False`` (default): enforce TRASH-FIRST — refuse unless
            the file is already trashed (checked via ``files().get``).
          * ``force=True``: bypass trash-first (operator override only;
            the adapter is responsible for the pre-delete export in this
            path).

        Permanent deletion bypasses the 30-day recovery window. The
        caller (adapter) MUST have captured a pre-delete export before
        reaching this method.
        """
        if not force:
            existing = self.get_file(file_id)
            trashed = bool(existing.get("trashed"))
            if not trashed:
                logger.warning(
                    "drive.client.delete_file.refused_trash_first",
                    file_id=file_id,
                )
                raise PermissionDeniedError(_TRASH_FIRST_POLICY_MESSAGE)

        def _request():
            return self._service.files().delete(fileId=file_id)

        self._call_with_retry(_request)
        logger.info(
            "drive.client.delete_file.permanent",
            file_id=file_id,
            force=force,
        )
        # Drive ``files().delete`` returns an empty 204 body
        return {"deleted": True, "file_id": file_id, "force": force}

    def create_permission(
        self,
        file_id: str,
        type: str,
        role: str,
    ) -> dict[str, Any]:
        """Create a permission grant (L3, public share when type='anyone').

        Per google-workspace-full-access.md §7, ``type='anyone'`` opens
        the file to the public internet — the adapter treats this action
        as an L3 public_share requiring explicit consent.
        """
        def _request():
            return self._service.permissions().create(
                fileId=file_id,
                body={"type": type, "role": role},
            )

        result = self._call_with_retry(_request)
        logger.info(
            "drive.client.create_permission",
            file_id=file_id,
            type=type,
            role=role,
        )
        return result

    def health(self) -> bool:
        """Lightweight liveness probe via ``about().get()``.

        Returns True on a successful Drive API call, False on any
        transport / auth failure. Never logs the token.
        """
        def _request():
            return self._service.about().get(
                fields="user(displayName,permissionId)",
            )

        try:
            self._call_with_retry(_request)
            return True
        except (
            ConfigurationMissingError,
            ProviderError,
            PermissionDeniedError,
            RateLimitExceededError,
        ):
            return False
        except Exception as exc:  # defensive — transport / unknown
            logger.warning(
                "drive.client.health.unexpected",
                error_type=type(exc).__name__,
            )
            return False


__all__ = [
    "DriveClient",
]
