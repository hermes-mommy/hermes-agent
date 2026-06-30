from __future__ import annotations

"""Gmail Pub/Sub StreamingPull client and watch renewal manager.

Provides real-time push notification reception from Gmail via Google Cloud
Pub/Sub StreamingPull, and automatic Gmail watch registration with daily
renewal to ensure the push subscription never expires.

Architecture::

    Gmail API ──push──> Pub/Sub topic ──StreamingPull──> PubSubClient
                                                          │ on_notification(historyId)
                                                          ▼
                                                    SyncEngine.trigger_sync()
"""

import asyncio
import json
import random
from collections.abc import Coroutine
from concurrent.futures import Future
from datetime import datetime, timezone
from typing import Any, Callable

import structlog
from google.cloud.pubsub_v1 import SubscriberClient
from google.cloud.pubsub_v1.subscriber.message import Message
from google.oauth2.service_account import Credentials as SACredentials

from .client import AsyncGmailClient
from .config import GmailSettings
from .exceptions import StreamingPullError, WatchRenewalError
from .metrics import set_watch_active

_BACKOFF_BASE: float = 1.0
_BACKOFF_MAX: float = 60.0
_JITTER_FACTOR: float = 0.5
_RENEWAL_INTERVAL_HOURS: float = 23.0
_LABEL_IDS: list[str] = ["INBOX"]

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Pub/Sub StreamingPull client
# ---------------------------------------------------------------------------


class PubSubClient:
    """Google Cloud Pub/Sub StreamingPull client for Gmail notifications.

    Receives push notifications from Gmail via a Pub/Sub subscription,
    decodes each notification to extract the ``historyId``, and dispatches
    an async callback for downstream processing (e.g. triggering a sync).

    The underlying ``SubscriberClient`` is synchronous; all async integration
    is handled via ``asyncio.to_thread`` for the monitoring loop and
    ``asyncio.run_coroutine_threadsafe`` for the message callback bridge.

    Parameters
    ----------
    settings:
        Gmail configuration including Pub/Sub project, subscription, and
        service account path.
    on_notification:
        Async callback invoked with the ``historyId`` string from each
        received Gmail notification.
    """

    def __init__(
        self,
        settings: GmailSettings,
        on_notification: Callable[[str], Coroutine[Any, Any, None]],
    ) -> None:
        self._settings: GmailSettings = settings
        self._on_notification: Callable[[str], Coroutine[Any, Any, None]] = (
            on_notification
        )
        self._active: bool = False
        self._subscriber: SubscriberClient | None = None
        self._streaming_future: Any = None
        self._reconnect_task: asyncio.Task[None] | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

        self._subscription_path: str = (
            f"projects/{settings.pubsub_project_id}"
            f"/subscriptions/{settings.pubsub_subscription}"
        )

        credentials = SACredentials.from_service_account_file(
            str(settings.pubsub_service_account_path),
        )
        self._subscriber = SubscriberClient(credentials=credentials)

        logger.info(
            "gmail.pubsub_initialized",
            project=settings.pubsub_project_id,
            subscription=settings.pubsub_subscription,
        )

    # -- lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """Start the StreamingPull subscription and monitoring loop.

        Launches a background task that manages the streaming pull
        lifecycle, including automatic reconnection with exponential
        backoff on errors.

        Raises
        ------
        RuntimeError
            If called outside a running asyncio event loop.
        """
        loop = asyncio.get_running_loop()
        if loop is None:
            raise RuntimeError(
                "PubSubClient.start() requires a running event loop",
            )

        self._loop = loop
        self._active = True

        self._reconnect_task = asyncio.create_task(
            self._reconnect_loop(),
        )

        logger.info(
            "gmail.pubsub_started",
            subscription=self._subscription_path,
        )

    async def stop(self) -> None:
        """Cancel the streaming pull and cleanup resources.

        Gracefully terminates the StreamingPull subscription and
        cancels the background monitoring/reconnection task.
        """
        self._active = False

        if self._streaming_future is not None:
            try:
                self._streaming_future.cancel()
            except Exception:
                logger.debug("gmail.pubsub.future_cancel_failed", exc_info=True)
            self._streaming_future = None

        if self._reconnect_task is not None:
            self._reconnect_task.cancel()
            try:
                await self._reconnect_task
            except asyncio.CancelledError:
                pass
            self._reconnect_task = None

        self._loop = None

        logger.info("gmail.pubsub_stopped")

    @property
    def is_active(self) -> bool:
        """Return ``True`` if the client is currently streaming."""
        return self._active

    # -- internals --------------------------------------------------------

    def _start_streaming(self) -> None:
        """Begin the StreamingPull subscription on the subscriber client.

        Raises
        ------
        StreamingPullError
            If the subscription could not be started.
        """
        if self._subscriber is None:
            raise StreamingPullError("Subscriber client not initialized")

        self._streaming_future = self._subscriber.subscribe(
            self._subscription_path,
            callback=self._message_callback,
        )

    def _message_callback(self, message: Message) -> None:
        """Decode a Pub/Sub notification and schedule async processing.

        Each Gmail push notification carries a JSON payload with
        ``emailAddress`` and ``historyId``.  This method extracts the
        ``historyId``, acknowledges the message, and schedules the
        async ``on_notification`` callback on the running event loop.

        Parameters
        ----------
        message:
            The Pub/Sub message containing the Gmail notification.
        """
        try:
            payload: dict[str, Any] = json.loads(
                message.data.decode("utf-8"),
            )
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(
                "gmail.pubsub_decode_failed",
                error=str(exc),
                data_len=len(message.data),
            )
            message.nack()
            return

        history_id: str | None = payload.get("historyId")
        if history_id is None:
            logger.warning(
                "gmail.pubsub_missing_history_id",
                payload_keys=list(payload.keys()),
            )
            message.nack()
            return

        message.ack()

        logger.info(
            "gmail.pubsub_message_received",
            history_id=history_id,
            email_address=payload.get("emailAddress", "unknown"),
        )

        self._schedule_callback(history_id)

    def _schedule_callback(self, history_id: str) -> None:
        """Schedule the async notification callback on the event loop.

        Uses ``asyncio.run_coroutine_threadsafe`` to bridge from the
        Pub/Sub subscriber thread back to the main asyncio event loop.

        Parameters
        ----------
        history_id:
            The Gmail history ID extracted from the notification.
        """
        loop = self._loop
        if loop is None or loop.is_closed():
            logger.warning(
                "gmail.pubsub_callback_skipped",
                reason="event_loop_unavailable",
                history_id=history_id,
            )
            return

        future = asyncio.run_coroutine_threadsafe(
            self._on_notification(history_id),
            loop,
        )
        future.add_done_callback(self._handle_callback_error)

    @staticmethod
    def _handle_callback_error(future: Future[Any]) -> None:
        """Log errors from the scheduled notification callback."""
        exc = future.exception()
        if exc is not None:
            logger.error(
                "gmail.pubsub_callback_error",
                error=str(exc),
            )

    # -- reconnection with backoff ----------------------------------------

    async def _reconnect_loop(self) -> None:
        """Manage the StreamingPull lifecycle with reconnection.

        Starts the streaming pull, monitors it for errors, and
        reconnects with exponential backoff (1s → 2s → 4s → 8s → … → 60s)
        with jitter when errors occur.  Exits when ``stop()`` is called.
        """
        backoff: float = _BACKOFF_BASE

        while self._active:
            try:
                await asyncio.to_thread(self._start_streaming)
                backoff = _BACKOFF_BASE
            except StreamingPullError:
                logger.exception("gmail.pubsub_start_failed")
                if not self._active:
                    break
                backoff = await self._backoff_sleep(backoff)
                continue

            future = self._streaming_future
            if future is None:
                break

            try:
                await asyncio.to_thread(future.result)
            except Exception:
                logger.debug("gmail.pubsub.future_result_failed", exc_info=True)

            if not self._active:
                break

            logger.warning("gmail.pubsub_reconnecting", backoff_s=backoff)
            backoff = await self._backoff_sleep(backoff)

    @staticmethod
    async def _backoff_sleep(current: float) -> float:
        """Sleep with exponential backoff and jitter, return next delay.

        Parameters
        ----------
        current:
            The current backoff interval in seconds.

        Returns
        -------
        float
            The next backoff interval (capped at ``_BACKOFF_MAX``).
        """
        jitter = current * _JITTER_FACTOR * random.random()
        await asyncio.sleep(current + jitter)
        return min(current * 2.0, _BACKOFF_MAX)


# ---------------------------------------------------------------------------
# Gmail watch registration and renewal
# ---------------------------------------------------------------------------


class WatchManager:
    """Gmail watch registration and automatic renewal manager.

    Registers a Gmail push-notification watch on a Pub/Sub topic and
    maintains it with a daily renewal loop.  Gmail watches expire after
    7 days; renewing every 23 hours provides a generous safety margin.

    Parameters
    ----------
    gmail_client:
        Async Gmail API client used to register and stop the watch.
    settings:
        Gmail configuration containing the Pub/Sub topic name.
    """

    def __init__(
        self,
        gmail_client: AsyncGmailClient,
        settings: GmailSettings,
    ) -> None:
        self._gmail_client: AsyncGmailClient = gmail_client
        self._settings: GmailSettings = settings
        self._watch_expiration: datetime | None = None
        self._renewal_task: asyncio.Task[None] | None = None
        self._watching: bool = False

        self._topic_path: str = (
            f"projects/{settings.pubsub_project_id}"
            f"/topics/{settings.pubsub_topic}"
        )

    # -- lifecycle --------------------------------------------------------

    async def start(self) -> None:
        """Register the Gmail watch and start the daily renewal loop.

        Performs an initial watch registration, then launches a
        background task that renews the watch every 23 hours.

        Raises
        ------
        WatchRenewalError
            If the initial watch registration fails.
        """
        await self.renew_watch()
        self._renewal_task = asyncio.create_task(self._renewal_loop())

        logger.info(
            "gmail.watch_started",
            topic=self._topic_path,
            expiration=self._watch_expiration,
        )

    async def stop(self) -> None:
        """Stop the Gmail watch and cancel the renewal loop.

        Calls ``stop_watch()`` on the Gmail API and cancels the
        background renewal task.
        """
        self._watching = False

        if self._renewal_task is not None:
            self._renewal_task.cancel()
            try:
                await self._renewal_task
            except asyncio.CancelledError:
                pass
            self._renewal_task = None

        try:
            await self._gmail_client.stop_watch()
        except Exception as exc:
            logger.warning(
                "gmail.watch_stop_error",
                error=str(exc),
            )

        self._watch_expiration = None
        set_watch_active(False)

        logger.info("gmail.watch_stopped")

    # -- properties -------------------------------------------------------

    @property
    def watch_expiration(self) -> datetime | None:
        """Return the expiration timestamp of the current watch."""
        return self._watch_expiration

    @property
    def is_watching(self) -> bool:
        """Return ``True`` if a Gmail watch is currently registered."""
        return self._watching

    # -- watch management -------------------------------------------------

    async def renew_watch(self) -> None:
        """Register or renew the Gmail watch on the configured topic.

        Calls the Gmail API ``users.watch`` endpoint with the Pub/Sub
        topic name, then stores the returned expiration timestamp.

        Raises
        ------
        WatchRenewalError
            If the API call fails for any reason.
        """
        try:
            response = await self._gmail_client.watch(
                topic_name=self._topic_path,
                label_ids=_LABEL_IDS,
            )
        except Exception as exc:
            self._watching = False
            set_watch_active(False)
            logger.error(
                "gmail.watch_renewal_failed",
                error=str(exc),
            )
            raise WatchRenewalError(str(exc)) from exc

        expiration_raw = response.get("expiration")
        if expiration_raw is not None:
            self._watch_expiration = datetime.fromtimestamp(
                int(expiration_raw) / 1000,
                tz=timezone.utc,
            )

        self._watching = True
        set_watch_active(True)

        logger.info(
            "gmail.watch_renewed",
            expiration=self._watch_expiration,
        )

    async def _renewal_loop(self) -> None:
        """Renew the Gmail watch every 23 hours.

        Runs indefinitely until cancelled via ``stop()``.  Errors during
        renewal are logged and retried on the next cycle rather than
        terminating the loop.
        """
        interval_seconds: float = _RENEWAL_INTERVAL_HOURS * 3600.0

        while self._watching:
            try:
                await asyncio.sleep(interval_seconds)
                await self.renew_watch()
            except asyncio.CancelledError:
                break
            except WatchRenewalError:
                logger.exception(
                    "gmail.watch_renewal_loop_error",
                    next_retry_hours=_RENEWAL_INTERVAL_HOURS,
                )
            except Exception as exc:
                logger.error(
                    "gmail.watch_renewal_unexpected_error",
                    error=str(exc),
                )
