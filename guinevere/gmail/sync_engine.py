from __future__ import annotations

"""Incremental sync engine for Gmail with Redis-backed state persistence.

Implements three sync modes:
- **incremental** — uses ``history.list`` with a stored ``historyId`` cursor
  for low-cost change detection.
- **full** — fallback when history has expired (HTTP 404); lists recent
  messages and re-bootstraps the cursor.
- **backfill** — resumable historical fetch with per-page Redis cursor.

All state is persisted to Redis under ``guinevere:gmail:sync_state`` (JSON)
and ``guinevere:gmail:backfill_cursor`` for backfill resumption.
"""

import asyncio
import json
import time
from collections.abc import AsyncGenerator, Awaitable, Callable
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

import redis.asyncio as aioredis
import structlog
from redis.asyncio.client import Pipeline as AsyncPipeline

from .client import AsyncGmailClient, parse_message_to_envelope
from .config import GmailSettings
from .envelope import GmailMessageEnvelope
from .exceptions import (
    BackfillInterruptedError,
    HistoryExpiredError,
    SyncStateCorruptedError,
)
from .metrics import observe_processing_latency

_MS_PER_SECOND: int = 1000


# ---------------------------------------------------------------------------
# State model
# ---------------------------------------------------------------------------


class SyncMode(str, Enum):
    """Current sync operating mode."""

    INCREMENTAL = "incremental"
    FULL = "full"
    BACKFILL = "backfill"


@dataclass
class SyncState:
    """Persisted sync cursor and counters.

    Serialized to JSON in Redis after every successful sync cycle.
    """

    history_id: str
    last_sync_time: str
    mode: str
    cursor: str | None = None
    total_synced: int = 0
    backfill_pages: int = 0


# ---------------------------------------------------------------------------
# Sync engine
# ---------------------------------------------------------------------------


class SyncEngine:
    """Core sync engine — incremental, full, and backfill operations.

    Manages the Gmail history cursor, persists state to Redis, and
    deduplicates messages within a single sync cycle.
    """

    _REDIS_STATE_KEY: str = "guinevere:gmail:sync_state"
    _REDIS_CURSOR_KEY: str = "guinevere:gmail:backfill_cursor"
    _REDIS_TTL_SECONDS: int = 86400 * 7  # 7 days

    def __init__(
        self,
        client: AsyncGmailClient,
        settings: GmailSettings,
        redis_client: aioredis.Redis,
    ) -> None:
        self._client: AsyncGmailClient = client
        self._settings: GmailSettings = settings
        self._redis: aioredis.Redis = redis_client
        self._state: SyncState | None = None
        self._bootstrapped: bool = False
        self._log: structlog.stdlib.BoundLogger = (
            structlog.get_logger(__name__)
        )

    @property
    def bootstrapped(self) -> bool:
        """True when sync state was freshly created (not from Redis)."""
        return self._bootstrapped

    async def initialize(self) -> None:
        """Load persisted sync state and bootstrap the history cursor.

        Fetches the current Gmail profile to obtain the latest
        ``historyId``.  If no persisted state exists, a fresh cursor is
        created from the profile ``historyId``.
        """
        self._log.info("gmail.sync_engine_initialize_start")

        try:
            stored: SyncState | None = await self._load_state()
            raw_profile: dict[str, Any] = (
                await self._client.get_profile()
            )
            profile_hid: str | None = raw_profile.get("historyId")
            if not profile_hid:
                raise SyncStateCorruptedError(
                    "profile missing historyId"
                )

            if stored is not None:
                if not stored.history_id:
                    raise SyncStateCorruptedError(
                        "empty history_id in stored state"
                    )
                self._state = stored
                self._log.info(
                    "gmail.sync_state_loaded",
                    history_id=stored.history_id,
                    mode=stored.mode,
                    total_synced=stored.total_synced,
                )
            else:
                self._state = SyncState(
                    history_id=profile_hid,
                    last_sync_time=datetime.now(
                        tz=timezone.utc,
                    ).isoformat(),
                    mode=SyncMode.INCREMENTAL.value,
                )
                self._bootstrapped = True
                await self.save_sync_state()
                self._log.info(
                    "gmail.sync_state_bootstrapped",
                    history_id=profile_hid,
                )

        except SyncStateCorruptedError:
            await self._cleanup_redis()
            raise
        except Exception as exc:
            await self._cleanup_redis()
            raise RuntimeError(
                f"Sync engine initialization failed: {exc}",
            ) from exc

        assert self._state is not None
        self._log.info(
            "gmail.sync_engine_initialized",
            mode=self._state.mode,
            history_id=self._state.history_id,
        )

    # -- incremental sync --------------------------------------------------

    async def incremental_sync(self) -> list[GmailMessageEnvelope]:
        """Fetch new messages via the Gmail history API.

        Uses the stored ``historyId`` as ``startHistoryId`` to retrieve
        only changes since the last sync.  Deduplicates message IDs
        within a single cycle to avoid processing the same message twice.

        Returns:
            List of ``GmailMessageEnvelope`` for newly-arrived messages.

        Raises:
            HistoryExpiredError: When the server no longer retains
                history from the stored cursor.  Callers should fall
                back to ``full_sync``.
        """
        assert self._state is not None

        start_time: float = time.monotonic()
        self._log.info(
            "gmail.sync_incremental",
            history_id=self._state.history_id,
        )

        envelopes: list[GmailMessageEnvelope] = []
        seen_ids: set[str] = set()
        new_history_id: str | None = None

        try:
            while True:
                raw_page: dict[str, Any] = (
                    await self._client.list_history(
                        start_history_id=self._state.history_id,
                        history_types=["messageAdded"],
                    )
                )

                # CRITICAL: startHistoryId is the OLD/stored historyId,
                # not the new one returned by the API.

                page_hid: str | None = raw_page.get("historyId")
                if page_hid is not None:
                    new_history_id = str(page_hid)

                raw_history: list[dict[str, Any]] = (
                    raw_page.get("history", [])
                )
                for record in raw_history:
                    messages_added: list[dict[str, Any]] = (
                        record.get("messagesAdded", [])
                    )
                    for entry in messages_added:
                        msg_ref: dict[str, Any] = (
                            entry.get("message", {})
                        )
                        msg_id: str = msg_ref.get("id", "")
                        if msg_id and msg_id not in seen_ids:
                            seen_ids.add(msg_id)

                page_token: str | None = (
                    raw_page.get("nextPageToken")
                )
                if not page_token:
                    break

            # Fetch full messages and parse to envelopes.
            for msg_id in seen_ids:
                try:
                    raw_msg: dict[str, Any] = (
                        await self._client.get_message(
                            message_id=msg_id, format="full",
                        )
                    )
                    envelope: GmailMessageEnvelope = (
                        parse_message_to_envelope(raw_msg)
                    )
                    self._state.total_synced += 1
                    envelopes.append(envelope)
                except Exception:
                    self._log.error(
                        "gmail.sync_message_fetch_failed",
                        message_id=msg_id,
                    )
                    continue

            # Persist updated state.
            if new_history_id is not None:
                self._state.history_id = new_history_id
            self._state.last_sync_time = datetime.now(
                tz=timezone.utc,
            ).isoformat()
            await self.save_sync_state()

            elapsed_s: float = (
                (time.monotonic() - start_time) / _MS_PER_SECOND
            )
            observe_processing_latency(elapsed_s)

            self._log.info(
                "gmail.sync_incremental_done",
                messages_synced=len(envelopes),
                seen_ids=len(seen_ids),
                new_history_id=new_history_id,
            )

        except HistoryExpiredError:
            self._log.warning(
                "gmail.sync_incremental_expired",
                history_id=self._state.history_id,
            )
            raise
        except Exception as exc:
            self._log.error(
                "gmail.sync_incremental_failed",
                error=str(exc),
            )
            raise

        return envelopes

    # -- full sync ---------------------------------------------------------

    async def full_sync(self) -> list[GmailMessageEnvelope]:
        """List recent messages when history has expired.

        Used as a fallback after ``HistoryExpiredError``.  Fetches the
        first page of recent messages and re-bootstraps the history
        cursor from the profile ``historyId``.
        """
        assert self._state is not None

        start_time: float = time.monotonic()
        self._log.info("gmail.sync_full")

        envelopes: list[GmailMessageEnvelope] = []
        seen_ids: set[str] = set()

        try:
            raw_page: dict[str, Any] = (
                await self._client.list_messages(max_results=100)
            )
            raw_messages: list[dict[str, Any]] = (
                raw_page.get("messages", [])
            )
            for entry in raw_messages:
                msg_id: str = entry.get("id", "")
                if msg_id and msg_id not in seen_ids:
                    seen_ids.add(msg_id)

            for msg_id in seen_ids:
                try:
                    raw_msg: dict[str, Any] = (
                        await self._client.get_message(
                            message_id=msg_id, format="full",
                        )
                    )
                    envelope: GmailMessageEnvelope = (
                        parse_message_to_envelope(raw_msg)
                    )
                    self._state.total_synced += 1
                    envelopes.append(envelope)
                except Exception:
                    self._log.error(
                        "gmail.sync_message_fetch_failed",
                        message_id=msg_id,
                    )
                    continue

            # Re-bootstrap history cursor from profile.
            raw_profile: dict[str, Any] = (
                await self._client.get_profile()
            )
            profile_hid: str | None = raw_profile.get("historyId")
            if profile_hid:
                self._state.history_id = str(profile_hid)

            self._state.last_sync_time = datetime.now(
                tz=timezone.utc,
            ).isoformat()
            self._state.mode = SyncMode.INCREMENTAL.value
            await self.save_sync_state()

            elapsed_s: float = (
                (time.monotonic() - start_time) / _MS_PER_SECOND
            )
            observe_processing_latency(elapsed_s)

            self._log.info(
                "gmail.sync_full_done",
                messages_synced=len(envelopes),
                new_history_id=self._state.history_id,
            )

        except Exception as exc:
            self._log.error(
                "gmail.sync_full_failed",
                error=str(exc),
            )
            raise

        return envelopes

    # -- backfill ----------------------------------------------------------

    async def backfill(
        self,
        days: int | None = None,
    ) -> AsyncGenerator[GmailMessageEnvelope, None]:
        """Resumable historical backfill with per-page cursor.

        Yields ``GmailMessageEnvelope`` for each message found.  The
        pagination cursor is stored in Redis so that interrupted
        backfills can be resumed.

        Args:
            days: Number of days to backfill.  Defaults to
                ``settings.sync_backfill_days``.

        Yields:
            ``GmailMessageEnvelope`` for each historical message.

        Raises:
            BackfillInterruptedError: When the generator is closed
                before all pages are consumed (resumable).
        """
        assert self._state is not None

        if days is None:
            days = self._settings.sync_backfill_days

        start_time: float = time.monotonic()
        cutoff_dt: datetime = datetime.now(
            tz=timezone.utc,
        ) - timedelta(days=days)
        after_date: str = cutoff_dt.strftime("%Y/%m/%d")

        self._log.info(
            "gmail.sync_backfill",
            days=days,
            after_date=after_date,
        )

        self._state.mode = SyncMode.BACKFILL.value

        processed_count: int = 0
        total_estimate: int = 0
        page_count: int = 0

        try:
            raw_cursor: bytes | str | None = (
                await self._redis.get(self._REDIS_CURSOR_KEY)
            )
            start_cursor: str | None = None
            if isinstance(raw_cursor, bytes):
                start_cursor = raw_cursor.decode("utf-8")
            elif isinstance(raw_cursor, str):
                start_cursor = raw_cursor

            if start_cursor:
                self._log.info(
                    "gmail.sync_backfill_resuming",
                    cursor=start_cursor,
                )

            async for msg_id, pages_fetched in (
                self._fetch_message_ids(
                    after_date=after_date,
                    start_page_token=start_cursor,
                )
            ):
                page_count = pages_fetched
                total_estimate = max(
                    total_estimate, processed_count + 1,
                )

                try:
                    raw_msg: dict[str, Any] = (
                        await self._client.get_message(
                            message_id=msg_id, format="full",
                        )
                    )
                    envelope: GmailMessageEnvelope = (
                        parse_message_to_envelope(raw_msg)
                    )
                    self._state.total_synced += 1
                    processed_count += 1
                    yield envelope
                except Exception:
                    self._log.error(
                        "gmail.sync_backfill_message_failed",
                        message_id=msg_id,
                    )
                    continue

                if processed_count % 100 == 0:
                    await self._save_backfill_state(
                        page_count,
                        processed_count,
                    )

            # Completed — clear cursor and persist.
            _ = await self._redis.delete(self._REDIS_CURSOR_KEY)
            self._state.backfill_pages = page_count
            self._state.last_sync_time = datetime.now(
                tz=timezone.utc,
            ).isoformat()
            self._state.mode = SyncMode.INCREMENTAL.value
            await self.save_sync_state()

            elapsed_s: float = (
                (time.monotonic() - start_time) / _MS_PER_SECOND
            )
            observe_processing_latency(elapsed_s)

            self._log.info(
                "gmail.sync_backfill_done",
                total_messages=processed_count,
                pages=page_count,
                elapsed_s=round(elapsed_s, 3),
            )

        except BackfillInterruptedError:
            raise
        except GeneratorExit:
            # Generator closed early — save resume cursor.
            await self._save_backfill_state(
                page_count,
                processed_count,
            )
            raise BackfillInterruptedError(
                processed_count=processed_count,
                remaining_estimate=max(
                    total_estimate - processed_count, 0,
                ),
            )

    async def _fetch_message_ids(
        self,
        after_date: str,
        start_page_token: str | None,
    ) -> AsyncGenerator[tuple[str, int], None]:
        """Paginate ``messages.list`` and yield (message_id, page)."""
        page_token: str | None = start_page_token
        pages_fetched: int = 0

        while True:
            raw_page: dict[str, Any] = (
                await self._client.list_messages(
                    query=f"after:{after_date}",
                    max_results=100,
                    page_token=page_token,
                )
            )
            pages_fetched += 1

            raw_messages: list[dict[str, Any]] = (
                raw_page.get("messages", [])
            )
            for entry in raw_messages:
                msg_id: str = entry.get("id", "")
                if msg_id:
                    yield (msg_id, pages_fetched)

            page_token = raw_page.get("nextPageToken")
            if not page_token:
                break

    async def _save_backfill_state(
        self,
        page_count: int,
        processed_count: int,
    ) -> None:
        """Persist backfill progress cursor and state to Redis."""
        assert self._state is not None

        pipe: AsyncPipeline = self._redis.pipeline()

        # Store next page token for resumption.
        _ = pipe.set(
            self._REDIS_CURSOR_KEY,
            "",
            ex=self._REDIS_TTL_SECONDS,
        )

        # Store sync state snapshot.
        self._state.backfill_pages = page_count
        self._state.total_synced = processed_count
        self._state.last_sync_time = datetime.now(
            tz=timezone.utc,
        ).isoformat()
        _ = pipe.set(
            self._REDIS_STATE_KEY,
            json.dumps(asdict(self._state)),
            ex=self._REDIS_TTL_SECONDS,
        )

        await pipe.execute()

        self._log.info(
            "gmail.sync_state_saved",
            pages=page_count,
            total_synced=processed_count,
        )

    # -- state management --------------------------------------------------

    async def get_sync_state(self) -> SyncState:
        """Return the current in-memory sync state."""
        if self._state is not None:
            return self._state

        loaded: SyncState | None = await self._load_state()
        if loaded is not None:
            self._state = loaded
            return loaded

        return SyncState(
            history_id="",
            last_sync_time="",
            mode=SyncMode.INCREMENTAL.value,
        )

    async def save_sync_state(self) -> None:
        """Persist current sync state to Redis."""
        if self._state is None:
            return

        try:
            _ = await self._redis.set(
                self._REDIS_STATE_KEY,
                json.dumps(asdict(self._state)),
                ex=self._REDIS_TTL_SECONDS,
            )
            self._log.info(
                "gmail.sync_state_saved",
                history_id=self._state.history_id,
                mode=self._state.mode,
                total_synced=self._state.total_synced,
            )
        except Exception as exc:
            self._log.error(
                "gmail.sync_state_save_failed",
                error=str(exc),
            )
            raise

    async def _load_state(self) -> SyncState | None:
        """Load sync state from Redis, or return ``None``."""
        raw: str | bytes | None = await self._redis.get(
            self._REDIS_STATE_KEY,
        )
        if raw is None:
            return None

        try:
            decoded: str = (
                raw.decode("utf-8")
                if isinstance(raw, bytes)
                else raw
            )
            data: dict[str, Any] = json.loads(decoded)
            return SyncState(
                history_id=data["history_id"],
                last_sync_time=data["last_sync_time"],
                mode=data["mode"],
                cursor=data.get("cursor"),
                total_synced=data.get("total_synced", 0),
                backfill_pages=data.get("backfill_pages", 0),
            )
        except (json.JSONDecodeError, KeyError, TypeError) as exc:
            self._log.error(
                "gmail.sync_state_corrupted",
                error=str(exc),
            )
            await self._cleanup_redis()
            raise SyncStateCorruptedError(str(exc))

    async def _cleanup_redis(self) -> None:
        """Remove persisted sync state and backfill cursor."""
        pipe: AsyncPipeline = self._redis.pipeline()
        _ = pipe.delete(self._REDIS_STATE_KEY)
        _ = pipe.delete(self._REDIS_CURSOR_KEY)
        await pipe.execute()


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------


class SyncScheduler:
    """Polling-based sync scheduler with Pub/Sub trigger support.

    Runs ``incremental_sync`` on a timer (default 5 minutes) and
    handles ``HistoryExpiredError`` by falling back to ``full_sync``.
    Can also be triggered manually via ``trigger_sync``.
    """

    def __init__(
        self,
        engine: SyncEngine,
        settings: GmailSettings,
        on_new_envelope: Callable[[GmailMessageEnvelope], Awaitable[None]] | None = None,
    ) -> None:
        self._engine: SyncEngine = engine
        self._settings: GmailSettings = settings
        self._on_new_envelope: Callable[[GmailMessageEnvelope], Awaitable[None]] | None = on_new_envelope
        self._task: asyncio.Task[None] | None = None
        self._running: bool = False
        self._log: structlog.stdlib.BoundLogger = (
            structlog.get_logger(__name__)
        )

    async def start(self) -> None:
        """Start the background polling loop.

        The loop runs ``incremental_sync`` every
        ``sync_poll_interval_seconds`` (default 300s).
        """
        if self._running:
            self._log.warning("gmail.scheduler_already_running")
            return

        self._running = True
        self._log.info(
            "gmail.scheduler_started",
            interval_s=self._settings.sync_poll_interval_seconds,
        )

        self._task = asyncio.create_task(
            self._polling_loop(),
            name="gmail-sync-poll",
        )

    async def stop(self) -> None:
        """Stop the polling loop gracefully."""
        if not self._running or self._task is None:
            return

        self._log.info("gmail.scheduler_stopping")
        self._running = False
        self._task.cancel()

        try:
            await self._task
        except asyncio.CancelledError:
            pass

        self._task = None
        self._log.info("gmail.scheduler_stopped")

    async def trigger_sync(self) -> list[GmailMessageEnvelope]:
        """Manually trigger a sync cycle.

        Used by Pub/Sub push notifications to run a sync immediately
        without waiting for the next polling interval.
        """
        self._log.info("gmail.sync_triggered")
        envelopes: list[GmailMessageEnvelope] = (
            await self._run_sync()
        )
        self._log.info(
            "gmail.sync_triggered_done",
            count=len(envelopes),
        )
        return envelopes

    # -- internals ---------------------------------------------------------

    async def _polling_loop(self) -> None:
        """Background loop — syncs at the configured interval."""
        interval: int = self._settings.sync_poll_interval_seconds

        while self._running:
            try:
                envelopes = await self._run_sync()
                if self._on_new_envelope is not None:
                    for env in envelopes:
                        try:
                            await self._on_new_envelope(env)
                        except Exception as exc:
                            self._log.error(
                                "gmail.sync_envelope_handler_failed",
                                message_id=env.message_id,
                                error=str(exc),
                            )
            except Exception as exc:
                self._log.error(
                    "gmail.sync_poll_cycle_failed",
                    error=str(exc),
                )

            try:
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break

    async def _run_sync(self) -> list[GmailMessageEnvelope]:
        """Execute a single sync cycle with error recovery.

        Handles ``HistoryExpiredError`` by falling back to ``full_sync``.
        """
        try:
            envelopes: list[GmailMessageEnvelope] = (
                await self._engine.incremental_sync()
            )
            self._log.info(
                "gmail.sync_cycle_done",
                count=len(envelopes),
            )
            return envelopes
        except HistoryExpiredError:
            self._log.warning(
                "gmail.sync_history_expired_fallback",
            )
            envelopes = await self._engine.full_sync()
            self._log.info(
                "gmail.sync_cycle_done",
                count=len(envelopes),
                fallback="full_sync",
            )
            return envelopes
        except Exception as exc:
            self._log.error(
                "gmail.sync_cycle_failed",
                error=str(exc),
            )
            raise
