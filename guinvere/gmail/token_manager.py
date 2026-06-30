from __future__ import annotations

"""OAuth2 token lifecycle management for Gmail API.

Handles SOPS-decrypted credential loading, automatic refresh before
expiry, token age tracking via Prometheus, and graceful degradation
on refresh failure.
"""

import asyncio
import time

import google.auth.exceptions
import structlog
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

from .config import GmailSettings
from .exceptions import (
    CredentialsNotFoundError,
    ScopeViolationError,
    TokenRefreshError,
)
from .metrics import set_connected, set_token_age

logger = structlog.get_logger(__name__)

_REFRESH_MARGIN_SECONDS = 300
_METRICS_INTERVAL_SECONDS = 60
_MAX_CONSECUTIVE_FAILURES = 5
_BACKOFF_BASE_SECONDS = 60
_BACKOFF_MAX_SECONDS = 900


class TokenManager:
    """OAuth2 token lifecycle manager for Gmail API.

    Handles:
    - Loading SOPS-decrypted credentials from disk
    - Automatic token refresh before expiry
    - Token age tracking via Prometheus
    - Graceful degradation on refresh failure
    """

    def __init__(self, settings: GmailSettings) -> None:
        self._settings: GmailSettings = settings
        self._credentials: Credentials | None = None
        self._last_refresh_time: float = 0.0
        self._lock: asyncio.Lock = asyncio.Lock()
        self._background_task: asyncio.Task[None] | None = None
        self._consecutive_failures: int = 0
        self._last_failure_time: float = 0.0

    async def initialize(self) -> None:
        """Load credentials from SOPS-decrypted path.

        Raises:
            CredentialsNotFoundError: If the credentials file is missing.
            ScopeViolationError: If required scopes are not granted.
        """
        self._credentials = await self._load_credentials()
        self._last_refresh_time = time.monotonic()
        await self._update_metrics()
        logger.info(
            "token_manager_initialized",
            path=str(self._settings.credentials_path),
        )

    async def get_credentials(self) -> Credentials:
        """Get valid credentials, refreshing if needed.

        Thread-safe via asyncio.Lock to prevent concurrent refreshes.

        Returns:
            Valid, non-expired OAuth2 credentials.

        Raises:
            CredentialsNotFoundError: If credentials are not loaded.
            TokenRefreshError: If refresh fails.
            TokenExpiredError: If token is expired and cannot refresh.
        """
        if self._credentials is None:
            raise CredentialsNotFoundError(
                searched_paths=[str(self._settings.credentials_path)],
            )

        _ = await self.refresh_if_needed()
        assert self._credentials is not None  # noqa: S101
        return self._credentials

    async def refresh_if_needed(self) -> bool:
        """Check expiry and refresh proactively.

        Triggers a refresh when the token expires within
        ``_REFRESH_MARGIN_SECONDS`` (5 minutes).

        Returns:
            True if a refresh was performed, False otherwise.
        """
        if self._credentials is None:
            return False

        if not self._credentials.expiry:
            return False

        now = time.time()
        expiry_ts = self._credentials.expiry.timestamp()
        seconds_until_expiry = expiry_ts - now

        if seconds_until_expiry > _REFRESH_MARGIN_SECONDS:
            return False

        logger.info(
            "token_refresh_triggered",
            seconds_until_expiry=round(seconds_until_expiry, 1),
        )
        await self.force_refresh()
        return True

    async def force_refresh(self) -> None:
        """Force token refresh.

        Used by the ``!email-reauth`` command or when proactive
        refresh detects imminent expiry.

        Tracks consecutive failures and refuses to retry after
        ``_MAX_CONSECUTIVE_FAILURES``, requiring a manual ``!email-reauth``
        (which resets the failure counter).

        Raises:
            CredentialsNotFoundError: If credentials are not loaded.
            TokenRefreshError: If the refresh exchange fails.
        """
        if self._credentials is None:
            raise CredentialsNotFoundError(
                searched_paths=[str(self._settings.credentials_path)],
            )

        async with self._lock:
            try:
                self._credentials = await self._do_refresh(
                    self._credentials,
                )
                self._last_refresh_time = time.monotonic()
                self._consecutive_failures = 0
                self._last_failure_time = 0.0
                await self._save_credentials(self._credentials)
                await self._update_metrics()
                logger.info(
                    "token_refresh_success",
                    consecutive_failures_before=0,
                )
            except (
                google.auth.exceptions.RefreshError,
                google.auth.exceptions.TransportError,
            ) as exc:
                self._consecutive_failures += 1
                self._last_failure_time = time.monotonic()
                logger.error(
                    "token_refresh_failure",
                    error=str(exc),
                    consecutive_failures=self._consecutive_failures,
                )
                set_connected(False)
                raise TokenRefreshError(reason=str(exc)) from exc
            except TokenRefreshError:
                self._consecutive_failures += 1
                self._last_failure_time = time.monotonic()
                set_connected(False)
                raise

    @property
    def is_authenticated(self) -> bool:
        """Whether we have valid, non-expired credentials."""
        if self._credentials is None:
            return False
        if self._credentials.expired:
            return False
        if not self._credentials.token:
            return False
        return True

    @property
    def token_age_seconds(self) -> float:
        """Seconds since last token refresh."""
        if self._last_refresh_time == 0.0:
            return 0.0
        return time.monotonic() - self._last_refresh_time

    async def revoke(self) -> None:
        """Revoke current token for consent revocation.

        Clears in-memory credentials and deletes the token file.
        """
        if self._credentials is not None and self._credentials.token:
            try:
                request = Request()
                await asyncio.to_thread(
                    self._credentials.revoke, request,
                )
                logger.info("token_revoked_successfully")
            except (
                google.auth.exceptions.RevokeError,
                google.auth.exceptions.TransportError,
            ) as exc:
                logger.warning(
                    "token_revocation_failed",
                    error=str(exc),
                )

        self._credentials = None
        self._last_refresh_time = 0.0
        set_connected(False)
        set_token_age(0.0)
        logger.info("token_manager_credentials_cleared")

    async def start_background_refresh(self) -> None:
        """Start periodic token age metric update (every 60s).

        Safe to call multiple times; cancels any existing task first.
        """
        await self.stop()
        self._background_task = asyncio.create_task(
            self._background_metrics_loop(),
        )
        logger.info(
            "token_background_refresh_started",
            interval_seconds=_METRICS_INTERVAL_SECONDS,
        )

    async def stop(self) -> None:
        """Cancel background refresh task."""
        if self._background_task is not None:
            self._background_task.cancel()
            try:
                await self._background_task
            except asyncio.CancelledError:
                pass
            self._background_task = None
            logger.info("token_background_refresh_stopped")

    async def _load_credentials(self) -> Credentials:
        """Load credentials from JSON file at credentials_path.

        Raises:
            CredentialsNotFoundError: If the file does not exist.
            ScopeViolationError: If required scopes are missing.
        """
        path = self._settings.credentials_path
        if not path.exists():
            raise CredentialsNotFoundError(
                searched_paths=[str(path)],
            )

        try:
            credentials = await asyncio.to_thread(
                Credentials.from_authorized_user_file,
                str(path),
                self._settings.scopes,
            )
        except FileNotFoundError as exc:
            raise CredentialsNotFoundError(
                searched_paths=[str(path)],
            ) from exc
        except ValueError as exc:
            raise CredentialsNotFoundError(
                searched_paths=[str(path)],
            ) from exc

        self._validate_scopes(credentials)
        set_connected(True)
        return credentials

    def _validate_scopes(self, credentials: Credentials) -> None:
        """Verify that required scopes are present.

        Raises:
            ScopeViolationError: If any required scope is missing.
        """
        if credentials.scopes is None:
            granted_scopes: list[str] = []
        else:
            granted_scopes = list(credentials.scopes)

        required = set(self._settings.scopes)
        granted = set(granted_scopes)
        missing = required - granted

        if missing:
            raise ScopeViolationError(
                required_scope=sorted(missing)[0],
                available_scopes=granted_scopes,
            )

    async def _do_refresh(
        self, credentials: Credentials,
    ) -> Credentials:
        """Execute token refresh via google-auth in a thread pool.

        The underlying ``credentials.refresh()`` call is synchronous
        and performs an HTTP request to Google's token endpoint.
        We offload it to avoid blocking the event loop.

        After refresh, we explicitly validate that the new ``expiry``
        timestamp is genuinely in the future — not just that
        ``expired`` is False (which can be unreliable with clock skew).
        """
        request = Request()
        await asyncio.to_thread(credentials.refresh, request)

        # Double-check: token must be present AND not expired
        if not credentials.token:
            raise TokenRefreshError(
                reason="Refresh returned empty access token",
            )
        if credentials.expired:
            raise TokenRefreshError(
                reason=(
                    "Refresh succeeded but credentials.expired is still True"
                ),
            )

        # Explicit future-expiry check — warn, don't block.
        # The Google client library may report stale expiry even after
        # a successful refresh. Actual 401s will be caught at API call time.
        if credentials.expiry is not None:
            now = time.time()
            expiry_ts = credentials.expiry.timestamp()
            if expiry_ts <= now:
                logger.warning(
                    "gmail.token.expiry_in_past",
                    seconds_behind=round(now - expiry_ts, 0),
                    hint="Token refresh succeeded but expiry appears stale; trusting credentials anyway",
                )
            elif expiry_ts - now < _REFRESH_MARGIN_SECONDS:
                logger.warning(
                    "gmail.token.expiry_within_margin",
                    seconds_remaining=round(expiry_ts - now, 0),
                )

        return credentials

    async def _save_credentials(
        self, credentials: Credentials,
    ) -> None:
        """Persist refreshed token back to disk.

        Writes the credential JSON to the SOPS-decrypted path so
        that subsequent loads (e.g. after restart) pick up the
        latest refresh token.
        """
        path = self._settings.credentials_path
        try:
            token_json = credentials.to_json()
            await asyncio.to_thread(path.write_text, token_json)
            logger.debug(
                "token_saved_to_disk",
                path=str(path),
            )
        except OSError as exc:
            logger.warning(
                "token_save_failed",
                path=str(path),
                error=str(exc),
            )

    async def _update_metrics(self) -> None:
        """Update Prometheus metrics for connection and token age."""
        set_connected(self.is_authenticated)
        set_token_age(self.token_age_seconds)

    async def _background_metrics_loop(self) -> None:
        """Periodically update token age metric + trigger proactive refresh.

        Runs every ``_METRICS_INTERVAL_SECONDS`` until cancelled.

        When consecutive refresh failures accumulate, the loop introduces
        exponential backoff (base 60 s, max 900 s) and stops after
        ``_MAX_CONSECUTIVE_FAILURES`` to prevent resource exhaustion.
        Manual ``!email-reauth`` resets the failure counter.
        """
        while True:
            try:
                # Exponential backoff on failure
                if self._consecutive_failures > 0:
                    backoff = min(
                        _BACKOFF_BASE_SECONDS * (2 ** (self._consecutive_failures - 1)),
                        _BACKOFF_MAX_SECONDS,
                    )
                    logger.info(
                        "token_background_backoff",
                        consecutive_failures=self._consecutive_failures,
                        backoff_seconds=backoff,
                    )
                    await asyncio.sleep(backoff)
                else:
                    await asyncio.sleep(_METRICS_INTERVAL_SECONDS)

                await self._update_metrics()

                # Stop auto-refreshing after max failures
                if self._consecutive_failures >= _MAX_CONSECUTIVE_FAILURES:
                    logger.warning(
                        "token_background_refresh_blocked",
                        consecutive_failures=self._consecutive_failures,
                        message="Use !email-reauth to retry.",
                    )
                    continue

                _ = await self.refresh_if_needed()
            except asyncio.CancelledError:
                raise
            except Exception:  # noqa: BLE001
                logger.exception("token_background_loop_error")
                # Brief cooldown even on unexpected errors
                await asyncio.sleep(_BACKOFF_BASE_SECONDS)
