"""Daily morning email briefing generator for Guinevere Gmail integration.

Produces a structured Discord markdown briefing every morning at 8:00 AM
WIB (Asia/Jakarta) with stats, action items, FYI items, and filtered items.
Supports on-demand briefing via the ``!email-digest`` command.
"""

from __future__ import annotations

import asyncio
import json
import re
import http.client
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone


import structlog
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from .categories import EmailPriority
from .config import GmailSettings, get_gmail_settings
from .exceptions import GmailError
from .memory_store import EmailMemoryStore, EmailEpisode

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BriefingError(GmailError):
    """Raised when briefing generation or delivery fails."""


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIB: timezone = timezone(timedelta(hours=7))
"""Asia/Jakarta fixed offset (UTC+7)."""

_TIME_RANGE_RE: re.Pattern[str] = re.compile(r"^(\d+)([hd])$|^today$")

# Priority buckets for the three briefing sections.
_ACTION_PRIORITIES: frozenset[EmailPriority] = frozenset(
    {
        EmailPriority.HIGH,
    }
)
_FYI_PRIORITIES: frozenset[EmailPriority] = frozenset(
    {
        EmailPriority.MEDIUM,
    }
)
_FILTERED_PRIORITIES: frozenset[EmailPriority] = frozenset(
    {
        EmailPriority.LOW,
        EmailPriority.BLOCK,
    }
)

_MAX_EPISODES: int = 200
"""Upper bound on episodes fetched per briefing."""


# ---------------------------------------------------------------------------
# Module-level helpers
# ---------------------------------------------------------------------------


def _parse_time_range(time_range: str) -> timedelta:
    """Parse a user-facing time range string into a ``timedelta``.

    Args:
        time_range: One of ``"12h"``, ``"24h"``, ``"7d"``, or ``"today"``.

    Returns:
        A ``timedelta`` representing the look-back window.

    Raises:
        BriefingError: When the format is unrecognised.
    """
    m: re.Match[str] | None = _TIME_RANGE_RE.match(time_range.strip().lower())
    if m is None:
        raise BriefingError(
            f"Unrecognised time range: {time_range!r} —"
            + " expected 12h, 24h, 7d, or today",
        )

    if m.group(0) == "today":
        now_wib: datetime = datetime.now(WIB)
        start_of_day: datetime = now_wib.replace(
            hour=0, minute=0, second=0, microsecond=0,
        )
        return now_wib - start_of_day

    value: int = int(m.group(1))
    unit: str | None = m.group(2)
    if unit == "h":
        return timedelta(hours=value)
    # unit == "d"
    return timedelta(days=value)


def _since_from_briefing_hour(briefing_hour: int) -> datetime:
    """Return yesterday's *briefing_hour* in WIB as a UTC datetime.

    The daily briefing at 08:00 WIB covers the preceding 24-hour window.
    """
    now_wib: datetime = datetime.now(WIB)
    yesterday: datetime = now_wib - timedelta(days=1)
    since_wib: datetime = yesterday.replace(
        hour=briefing_hour,
        minute=0,
        second=0,
        microsecond=0,
    )
    return since_wib.astimezone(timezone.utc)


def _format_action_item(ep: EmailEpisode) -> str:
    """Format a high-priority episode for the Action Required section."""
    return (
        f"\u2022 **{ep.subject or '(no subject)'}** \u2014 {ep.sender}"
        f" ({ep.category.value}, importance={ep.priority.value})"
    )


def _format_fyi_item(ep: EmailEpisode) -> str:
    """Format a medium-priority episode for the FYI section."""
    return (
        f"\u2022 {ep.subject or '(no subject)'} \u2014 {ep.sender}"
        f" ({ep.category.value})"
    )


def _format_filtered_item(ep: EmailEpisode) -> str:
    """Format a low-priority episode for the Filtered section."""
    return f"\u2022 {ep.subject or '(no subject)'} \u2014 {ep.sender}"


# ---------------------------------------------------------------------------
# BriefingGenerator
# ---------------------------------------------------------------------------


class BriefingGenerator:
    """Produces and delivers daily morning email briefings.

    Supports both scheduled (configurable hour, default 8:00 AM WIB via
    APScheduler) and on-demand (``!email-digest``) briefing generation.

    Args:
        memory_store: An ``EmailMemoryStore`` instance for fetching episodes.
        config: Optional ``GmailSettings`` override.  Defaults to the
            module-level singleton.
        webhook_url: Discord webhook URL for sending the briefing.
    """

    def __init__(
        self,
        memory_store: EmailMemoryStore,
        config: GmailSettings | None = None,
        webhook_url: str = "",
    ) -> None:
        self._store: EmailMemoryStore = memory_store
        self._config: GmailSettings = config or get_gmail_settings()
        self._webhook_url: str = webhook_url

        self._scheduler: AsyncIOScheduler | None = None
        self._job_id: str | None = None

        self._log: structlog.stdlib.BoundLogger = logger

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_briefing(
        self,
        since: datetime | None = None,
    ) -> str | None:
        """Produce a structured Discord markdown briefing.

        Args:
            since: Earliest UTC timestamp to include.  When ``None``,
                defaults to the most recent briefing hour (e.g. yesterday
                8:00 AM WIB).

        Returns:
            A Discord markdown string, or ``None`` when there are no
            actionable items to report (empty briefing is skipped).
        """
        threshold: datetime = since if since is not None else self._default_since()

        episodes: list[EmailEpisode] = await self._fetch_episodes_since(threshold)

        if not episodes:
            self._log.info(
                "briefing.no_episodes",
                since=threshold.isoformat(),
            )
            return None

        # Bucket episodes by priority.
        action_items: list[EmailEpisode] = []
        fyi_items: list[EmailEpisode] = []
        filtered_items: list[EmailEpisode] = []

        for ep in episodes:
            if ep.priority in _ACTION_PRIORITIES:
                action_items.append(ep)
            elif ep.priority in _FYI_PRIORITIES:
                fyi_items.append(ep)
            elif ep.priority in _FILTERED_PRIORITIES:
                filtered_items.append(ep)
            # Episodes with unrecognised priority are silently excluded.

        # Skip the briefing when there is nothing requiring attention.
        if not action_items and not fyi_items:
            self._log.info(
                "briefing.no_actionable",
                total=len(episodes),
                filtered=len(filtered_items),
            )
            return None

        # -- Build markdown -------------------------------------------------
        now_wib: datetime = datetime.now(WIB)
        date_str: str = now_wib.strftime("%A, %d %B %Y")
        lines: list[str] = []

        lines.append(f"\U0001f4ec **Gmail Daily Briefing \u2014 {date_str}**")
        lines.append("\u2501" * 25)
        lines.append("")

        # Stats
        total: int = len(episodes)
        classified: int = len(episodes)
        action_count: int = len(action_items)

        lines.append("**📊 Stats**")
        lines.append(f"\u2022 {total} emails received")
        lines.append(f"\u2022 {classified} classified")
        lines.append(f"\u2022 {action_count} action required")
        lines.append("")

        # Action Required
        lines.append("**\u26a1 Action Required**")
        if action_items:
            for ep in action_items:
                lines.append(_format_action_item(ep))
        else:
            lines.append("\u2022 _(none)_")
        lines.append("")

        # For Your Information
        lines.append("**\U0001f440 For Your Information**")
        if fyi_items:
            for ep in fyi_items:
                lines.append(_format_fyi_item(ep))
        else:
            lines.append("\u2022 _(none)_")
        lines.append("")

        # Filtered
        lines.append("**\U0001f507 Filtered**")
        if filtered_items:
            for ep in filtered_items:
                lines.append(_format_filtered_item(ep))
        else:
            lines.append("\u2022 _(none)_")
        lines.append("")

        # Footer
        lines.append("\u2501" * 25)
        next_hour: int = self._config.briefing_hour
        lines.append(f"Next briefing: tomorrow {next_hour}:00 AM WIB")

        text: str = "\n".join(lines)

        self._log.info(
            "briefing.generated",
            total=total,
            action=action_count,
            fyi=len(fyi_items),
            filtered=len(filtered_items),
        )

        return text

    async def send_briefing(self, text: str) -> bool:
        """Send the briefing text to Discord via webhook POST.

        Args:
            text: The markdown briefing text produced by
                :meth:`generate_briefing`.

        Returns:
            ``True`` when the webhook responded with HTTP 2xx.

        Raises:
            BriefingError: When the webhook URL is empty / not configured.
        """
        if not self._webhook_url:
            raise BriefingError(
                "Cannot send briefing: webhook_url is not configured",
            )

        payload: dict[str, str] = {"content": text}
        body: bytes = json.dumps(payload).encode("utf-8")

        loop: asyncio.AbstractEventLoop = asyncio.get_running_loop()

        try:
            response: http.client.HTTPResponse = await loop.run_in_executor(
                None,
                self._do_webhook_post,
                body,
            )
            success: bool = 200 <= response.status < 300

            if success:
                self._log.info(
                    "briefing.sent",
                    status=response.status,
                )
            else:
                response_body: str = response.read(
                ).decode("utf-8", errors="replace")[:500]
                self._log.warning(
                    "briefing.send_failed",
                    status=response.status,
                    body=response_body,
                )

            return success

        except urllib.error.HTTPError as exc:
            error_body: str = exc.read().decode(
                "utf-8", errors="replace",
            )[:500]
            self._log.error(
                "briefing.http_error",
                status=exc.code,
                body=error_body,
            )
            return False

        except (OSError, urllib.error.URLError) as exc:
            self._log.error(
                "briefing.network_error",
                error=str(exc),
            )
            return False

    def start_scheduler(self, scheduler: AsyncIOScheduler) -> None:
        """Register the daily briefing job on an APScheduler instance.

        The job fires daily at the configured briefing hour (default 8:00 AM)
        in the ``Asia/Jakarta`` timezone.

        Args:
            scheduler: A running ``AsyncIOScheduler`` instance.

        Raises:
            BriefingError: When a job is already registered (must call
                :meth:`stop_scheduler` first).
        """
        if self._job_id is not None:
            raise BriefingError(
                f"Briefing job '{self._job_id}' is already registered;"
                + " call stop_scheduler() first",
            )

        hour: int = self._config.briefing_hour
        trigger: CronTrigger = CronTrigger(
            hour=hour,
            timezone=self._config.briefing_timezone,
        )

        job = scheduler.add_job(
            self._scheduled_briefing,
            trigger=trigger,
            id="gmail_daily_briefing",
            replace_existing=False,
            name="Gmail Daily Briefing",
        )

        self._scheduler = scheduler
        self._job_id = job.id

        self._log.info(
            "briefing.scheduler_started",
            job_id=self._job_id,
            hour=hour,
            timezone=self._config.briefing_timezone,
        )

    def stop_scheduler(self) -> None:
        """Remove the daily briefing job from the scheduler.

        Safe to call when no job is registered (no-op).
        """
        if self._job_id is None or self._scheduler is None:
            self._log.info("briefing.scheduler_not_running")
            return

        try:
            self._scheduler.remove_job(self._job_id)
            self._log.info(
                "briefing.scheduler_stopped",
                job_id=self._job_id,
            )
        except Exception:
            self._log.exception(
                "briefing.scheduler_stop_failed",
                job_id=self._job_id,
            )
        finally:
            self._scheduler = None
            self._job_id = None

    async def digest_command(self, time_range: str = "12h") -> str:
        """Handle the ``!email-digest`` on-demand briefing command.

        Generates a briefing covering the requested look-back period and
        attempts delivery via the configured webhook.  When no webhook is
        configured the raw markdown is returned for inline display.

        Args:
            time_range: One of ``"12h"`` (default), ``"24h"``, ``"7d"``,
                or ``"today"``.

        Returns:
            A user-facing message indicating the outcome.
        """
        delta: timedelta = _parse_time_range(time_range)
        since: datetime = datetime.now(timezone.utc) - delta

        text: str | None = await self.generate_briefing(since=since)

        if text is None:
            return (
                f"\U0001f4ec **No actionable emails in the last"
                f" {time_range}.** You're all caught up! \u2705"
            )

        if self._webhook_url:
            sent: bool = await self.send_briefing(text)
            if sent:
                return "\U0001f4ec **Briefing sent to Discord!**"
            return (
                "\u26a0\ufe0f **Briefing generated but failed to send"
                " to Discord.**"
            )

        return text

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _default_since(self) -> datetime:
        """Return the default ``since`` timestamp for scheduled briefings."""
        return _since_from_briefing_hour(self._config.briefing_hour)

    async def _fetch_episodes_since(
        self,
        since: datetime,
    ) -> list[EmailEpisode]:
        """Fetch episodes from ``EmailMemoryStore`` since *since*.

        Args:
            since: UTC datetime threshold.

        Returns:
            A list of ``EmailEpisode`` objects, newest first.
        """
        now_utc: datetime = datetime.now(timezone.utc)
        delta: timedelta = now_utc - since
        hours: int = max(1, int(delta.total_seconds() // 3600) + 1)

        return await self._store.get_recent_episodes(
            hours=hours,
            limit=_MAX_EPISODES,
        )

    async def _scheduled_briefing(self) -> None:
        """Internal callback invoked by APScheduler.

        Generates the briefing and sends it via the configured webhook.
        Errors are logged but not propagated to the scheduler.
        """
        self._log.info("briefing.scheduled_trigger")
        try:
            text: str | None = await self.generate_briefing()
            if text is None:
                self._log.info("briefing.scheduled_skip_empty")
                return
            _: bool = await self.send_briefing(text)
        except BriefingError:
            self._log.exception("briefing.scheduled_failed")
        except Exception:
            self._log.exception("briefing.scheduled_unexpected_error")

    def _do_webhook_post(self, body: bytes) -> http.client.HTTPResponse:
        """Synchronous HTTP POST to the Discord webhook.

        Args:
            body: JSON-encoded request body.

        Returns:
            The HTTP response object.
        """
        req: urllib.request.Request = urllib.request.Request(
            self._webhook_url,
            data=body,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Guinevere-Briefing/1.0",
            },
            method="POST",
        )
        # urlopen may raise HTTPError on 4xx/5xx — caller handles it.
        return urllib.request.urlopen(req, timeout=15)  # noqa: S310


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__: list[str] = [
    "BriefingError",
    "BriefingGenerator",
]
