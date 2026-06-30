"""Enterprise-grade auto-updating Discord dashboard for X Poster.

Replaces webhook spam with a single rich embed that refreshes every
few seconds in the channel configured by ``X_POSTER_DASHBOARD_CHANNEL_ID``.

Sections shown:
  - Service Health     — running, circuit breaker, session, API auth
  - Queue Overview     — full depth breakdown with visual bars
  - Today's Activity   — sent, failed, success rate, last post
  - Schedule           — next post, slot usage, look-ahead
  - Performance        — refresh interval, ports, uptime
"""

from __future__ import annotations

import asyncio
import datetime
import logging
import os
from typing import Any

import discord
import httpx

logger = logging.getLogger(__name__)

DEFAULT_UPDATE_SECONDS: int = 10
DEFAULT_HEALTH_PORT: int = 8097

# Enterprise-brand color palette
_COLOR_PRIMARY: int = 0x1DA1F2      # X/Twitter blue
_COLOR_DEGRADED: int = 0xF59E0B     # Amber
_COLOR_CRITICAL: int = 0xE53E3E     # Red
_COLOR_SUCCESS: int = 0x48BB78      # Green
_COLOR_NEUTRAL: int = 0x718096      # Grey for informational


def _fmt_num(n: int) -> str:
    """Format integer with thousands separator."""
    return f"{n:,}"


def _fmt_dt(iso_str: str | None) -> str:
    """Format ISO timestamp to WIB human-readable with relative time."""
    if not iso_str:
        return "—"
    try:
        if isinstance(iso_str, str):
            dt = datetime.datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        else:
            return str(iso_str)
        now = datetime.datetime.now(datetime.timezone.utc)
        delta = now - dt
        hours = int(delta.total_seconds() // 3600)
        minutes = int((delta.total_seconds() % 3600) // 60)
        wib = dt.astimezone(datetime.timezone(datetime.timedelta(hours=7)))
        relative = f"{hours}h{minutes}m ago" if hours else f"{minutes}m ago"
        return f"{wib.strftime('%H:%M:%S')} ({relative})"
    except Exception:
        return str(iso_str)


class XPosterDashboard:
    """Background task that polls x_poster and edits one rich embed.

    Args:
        bot: The running ``GuinevereBot`` instance.
        channel_id: Discord channel ID where the dashboard message lives.
        update_seconds: How often to refresh the dashboard.
        health_port: Local x_poster health API port.
    """

    def __init__(
        self,
        bot: Any,
        channel_id: int,
        update_seconds: int = DEFAULT_UPDATE_SECONDS,
        health_port: int = DEFAULT_HEALTH_PORT,
    ) -> None:
        self._bot = bot
        self._channel_id = channel_id
        self._update_seconds = max(5, update_seconds)
        self._health_port = health_port
        self._message_id: int | None = None
        self._task: asyncio.Task[None] | None = None
        self._stopped = False

    # ── Lifecycle ──────────────────────────────────────────────────────

    def start(self) -> None:
        """Start the background refresh loop."""
        if self._task is not None and not self._task.done():
            logger.warning("x_poster_dashboard_already_running")
            return
        self._stopped = False
        self._task = asyncio.create_task(self._run_loop(), name="x_poster_dashboard")
        logger.info(
            "x_poster_dashboard_started",
            extra={
                "channel_id": self._channel_id,
                "update_seconds": self._update_seconds,
            },
        )

    async def stop(self) -> None:
        """Stop the background refresh loop."""
        self._stopped = True
        if self._task is not None and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        self._task = None
        logger.info("x_poster_dashboard_stopped")

    # ── Main loop ──────────────────────────────────────────────────────

    async def _run_loop(self) -> None:
        """Main loop: wait for ready, then refresh the dashboard embed."""
        try:
            await self._bot.wait_until_ready()
            channel = await self._get_channel()
            if channel is None:
                logger.error(
                    "x_poster_dashboard_channel_not_found",
                    extra={"channel_id": self._channel_id},
                )
                return

            while not self._stopped:
                try:
                    status, completed_posts, failed_posts, engagement = await self._fetch_all()
                    await self._update_dashboard(channel, status, completed_posts, failed_posts, engagement)
                except Exception as exc:
                    logger.exception(
                        "x_poster_dashboard_refresh_failed",
                        extra={"error": str(exc), "error_type": type(exc).__name__},
                    )
                await asyncio.sleep(self._update_seconds)
        except asyncio.CancelledError:
            logger.info("x_poster_dashboard_loop_cancelled")
        except Exception as exc:
            logger.exception(
                "x_poster_dashboard_loop_failed",
                extra={"error": str(exc), "error_type": type(exc).__name__},
            )

    # ── Channel resolution ─────────────────────────────────────────────

    async def _get_channel(self) -> discord.TextChannel | None:
        """Resolve the configured text channel."""
        channel = self._bot.get_channel(self._channel_id)
        if channel is None:
            try:
                channel = await self._bot.fetch_channel(self._channel_id)
            except Exception as exc:
                logger.error(
                    "x_poster_dashboard_fetch_channel_failed",
                    extra={"channel_id": self._channel_id, "error": str(exc)},
                )
                return None
        if not isinstance(channel, discord.TextChannel):
            logger.error(
                "x_poster_dashboard_invalid_channel_type",
                extra={
                    "channel_id": self._channel_id,
                    "type": type(channel).__name__,
                },
            )
            return None
        return channel

    # ── Data fetching ──────────────────────────────────────────────────

    async def _fetch_all(self) -> tuple[dict[str, Any], list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
        """Fetch status + last completed + last failed + engagement in parallel."""
        base = f"http://127.0.0.1:{self._health_port}"

        async def get(path: str) -> dict[str, Any]:
            url = f"{base}{path}"
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    resp = await client.get(url)
                    resp.raise_for_status()
                    return resp.json()
            except Exception:
                return {}

        status_task = asyncio.create_task(get("/api/status"))
        completed_task = asyncio.create_task(get("/api/posts?state=completed&limit=1"))
        failed_task = asyncio.create_task(get("/api/posts?state=failed&limit=1"))
        engagement_task = asyncio.create_task(get("/api/engagement?range=3mo"))

        status_resp, completed_resp, failed_resp, engagement_resp = await asyncio.gather(
            status_task, completed_task, failed_task, engagement_task,
        )

        status = status_resp.get("status", {}) if status_resp.get("ok") else {}
        completed_posts = completed_resp.get("posts", []) if completed_resp.get("ok") else []
        failed_posts = failed_resp.get("posts", []) if failed_resp.get("ok") else []
        engagement = engagement_resp if engagement_resp.get("ok") else {}
        return status, completed_posts, failed_posts, engagement

    # ── Embed update ───────────────────────────────────────────────────

    async def _update_dashboard(
        self,
        channel: discord.TextChannel,
        status: dict[str, Any],
        completed_posts: list[dict[str, Any]],
        failed_posts: list[dict[str, Any]],
        engagement: dict[str, Any] | None = None,
    ) -> None:
        """Create or edit the dashboard embed with full enterprise monitoring."""
        embed = self._build_enterprise_embed(status, completed_posts, failed_posts, engagement or {})

        if self._message_id is not None:
            try:
                message = await channel.fetch_message(self._message_id)
                await message.edit(embed=embed)
                return
            except discord.NotFound:
                self._message_id = None
            except Exception as exc:
                logger.warning(
                    "x_poster_dashboard_edit_failed",
                    extra={"message_id": self._message_id, "error": str(exc)},
                )
                self._message_id = None

        message = await channel.send(embed=embed)
        self._message_id = message.id
        logger.info(
            "x_poster_dashboard_message_created",
            extra={"message_id": self._message_id},
        )

    # ── Enterprise embed builder ───────────────────────────────────────

    def _build_enterprise_embed(
        self,
        status: dict[str, Any],
        completed_posts: list[dict[str, Any]],
        failed_posts: list[dict[str, Any]],
        engagement: dict[str, Any] | None = None,
    ) -> discord.Embed:
        """Build a rich monitoring-grade Discord embed."""
        qd: dict[str, int] = status.get("queue_depth", {}) or {}
        running: bool = status.get("running", False)
        session_health: str = status.get("session_health", "unknown")
        circuit_breaker: str = status.get("circuit_breaker", "unknown")
        next_slot = status.get("next_slot")
        metrics_port = status.get("metrics_port", "?")
        health_port = status.get("health_port", "?")
        now = datetime.datetime.now(datetime.timezone.utc)

        # ── Derive metrics ────────────────────────────────────────────
        completed = int(qd.get("completed", 0))
        failed = int(qd.get("failed", 0))
        total_processed = completed + failed
        success_rate = (completed / total_processed * 100) if total_processed > 0 else 100.0
        pending = int(qd.get("pending", 0))
        scheduled = int(qd.get("scheduled", 0))
        in_progress = int(qd.get("in_progress", 0))
        total_queue = pending + scheduled + in_progress

        # Last post time
        last_post_at: str | None = None
        if completed_posts:
            last_post_at = completed_posts[0].get("posted_at") or completed_posts[0].get("updated_at")

        # ── Color ─────────────────────────────────────────────────────
        if not running:
            color = _COLOR_CRITICAL
        elif circuit_breaker == "open":
            color = _COLOR_CRITICAL
        elif session_health != "ok" or circuit_breaker == "half_open":
            color = _COLOR_DEGRADED
        else:
            color = _COLOR_PRIMARY

        # ── Embed ─────────────────────────────────────────────────────
        embed = discord.Embed(
            title="📊 X Poster — Enterprise Monitoring",
            description=(
                "```\n"
                "Live queue and service health dashboard\n"
                "Refreshes every {} seconds\n"
                "```"
            ).format(self._update_seconds),
            color=color,
            timestamp=now,
        )

        # ── Section 1: Service Health ─────────────────────────────────
        def _status_val(label: str, emoji: str, ok: bool, detail: str = "") -> str:
            status_icon = "✅" if ok else "❌"
            detail_str = f" · {detail}" if detail else ""
            return f"{status_icon} {emoji} **{label}**{detail_str}"

        service_lines = []
        service_lines.append(_status_val("Service", "🖥️", running, "Running" if running else "Stopped"))

        cb_ok = circuit_breaker == "closed"
        cb_emoji = "🟢" if cb_ok else ("🟡" if circuit_breaker == "half_open" else "🔴")
        service_lines.append(_status_val("Circuit Breaker", cb_emoji, cb_ok, circuit_breaker.upper()))

        session_ok = session_health == "ok"
        service_lines.append(_status_val("X API Auth", "🔑", session_ok, session_health.upper()))

        embed.add_field(
            name="🟦 Service Health",
            value="\n".join(service_lines),
            inline=False,
        )

        # ── Section 2: Queue Overview ─────────────────────────────────
        max_q = max(completed, failed, scheduled, pending, in_progress) or 1
        bar_len = 12

        def _bar(count: int, emoji: str) -> str:
            filled = int((count / max_q) * bar_len)
            bar = "█" * filled + "░" * (bar_len - filled)
            return f"{emoji} `{bar}` {_fmt_num(count)}"

        queue_lines = [
            f"**Total in Queue:** `{_fmt_num(total_queue)}`",
            _bar(pending, "⏳"),
            _bar(scheduled, "📅"),
            _bar(in_progress, "🔄"),
            "",
            f"**Processed (All Time):** `{_fmt_num(total_processed)}`",
            _bar(completed, "✅"),
            _bar(failed, "❌"),
        ]

        held = int(qd.get("held", 0))
        cancelled = int(qd.get("cancelled", 0))
        if held or cancelled:
            queue_lines.append(f"*Held: {held} · Cancelled: {cancelled}*")

        embed.add_field(
            name="📋 Queue Overview",
            value="\n".join(queue_lines),
            inline=False,
        )

        # ── Section 3: Today's Activity ───────────────────────────────
        today_lines = [
            f"**Success Rate:** `{success_rate:.1f}%` ({_fmt_num(completed)}/{_fmt_num(total_processed)})",
            f"**Last Post:** {_fmt_dt(last_post_at)}",
        ]
        embed.add_field(
            name="📈 Today's Performance",
            value="\n".join(today_lines),
            inline=False,
        )

        # ── Section 4: Schedule ───────────────────────────────────────
        schedule_lines = [
            f"**Next Post:** `{self._format_next_slot(next_slot)}`",
        ]

        embed.add_field(
            name="🗓️ Schedule",
            value="\n".join(schedule_lines),
            inline=False,
        )

        # ── Section 5: Engagement (3mo + all-time) ────────────────────
        eng = engagement or {}
        totals = eng.get("totals", {}) or {}
        posts_tracked = int(eng.get("posts_tracked") or 0)
        top = eng.get("top_post") or {}
        engagement_lines = [
            f"**Range:** `{eng.get('range', '3mo')}` · **Posts Tracked:** `{_fmt_num(posts_tracked)}`",
            f"👁 **Impressions:** `{_fmt_num(int(totals.get('impressions', 0)))}`",
            f"❤️ **Likes:** `{_fmt_num(int(totals.get('likes', 0)))}` · 💬 **Replies:** `{_fmt_num(int(totals.get('replies', 0)))}`",
            f"🔁 **Retweets:** `{_fmt_num(int(totals.get('retweets', 0)))}` · 📢 **Quotes:** `{_fmt_num(int(totals.get('quotes', 0)))}` · 🔖 **Bookmarks:** `{_fmt_num(int(totals.get('bookmarks', 0)))}`",
        ]
        if top:
            engagement_lines.append(
                f"🏆 **Top Post:** `{top.get('tweet_id')}` · 👁 `{_fmt_num(int(top.get('impressions', 0)))}` · ❤️ `{_fmt_num(int(top.get('likes', 0)))}`"
            )
        embed.add_field(
            name="📈 Engagement (3mo)",
            value="\n".join(engagement_lines) if posts_tracked > 0 else "_No engagement data yet._",
            inline=False,
        )

        # ── Section 6: Daily Trend Chart (last 14 days) ───────────────
        daily = eng.get("daily", []) or []
        if daily:
            # Show last 14 days
            recent = daily[-14:]
            max_imp = max((d.get("impressions", 0) for d in recent), default=1) or 1
            chart_lines = ["```"]
            for d in recent:
                day_str = str(d.get("date", ""))[5:]  # MM-DD
                imp = int(d.get("impressions", 0))
                likes = int(d.get("likes", 0))
                bar_len = int((imp / max_imp) * 10)
                bar = "█" * bar_len + "░" * (10 - bar_len)
                chart_lines.append(f"{day_str} │{bar}│ {imp:,} 👁 {likes:,} ❤️")
            chart_lines.append("```")
            embed.add_field(
                name="📊 Daily Trend (14d)",
                value="\n".join(chart_lines),
                inline=False,
            )
        else:
            embed.add_field(
                name="📊 Daily Trend (14d)",
                value="_No daily data yet. Poll runs at 00:00 WIB._",
                inline=False,
            )

        # ── Footer ────────────────────────────────────────────────────
        embed.set_footer(
            text=(
                f"⏱️ {self._update_seconds}s refresh"
                f"  ·  🏥 {health_port}  ·  📈 {metrics_port}"
                f"  ·  🕐 {now.strftime('%H:%M:%S')} UTC"
            ),
        )
        return embed

    # ── Helpers ────────────────────────────────────────────────────────

    @staticmethod
    def _format_next_slot(next_slot: Any) -> str:
        """Format the next scheduled slot for display."""
        if next_slot is None:
            return "—"
        if isinstance(next_slot, str):
            return next_slot
        try:
            dt = datetime.datetime.fromisoformat(str(next_slot))
            return dt.strftime("%Y-%m-%d %H:%M %Z")
        except Exception:
            return str(next_slot)


# ── Factory ─────────────────────────────────────────────────────────────

def create_dashboard(bot: Any) -> XPosterDashboard | None:
    """Factory that builds a dashboard from environment variables.

    Returns ``None`` if ``X_POSTER_DASHBOARD_CHANNEL_ID`` is not set,
    allowing the feature to be disabled by default.
    """
    raw_channel = os.environ.get("X_POSTER_DASHBOARD_CHANNEL_ID", "").strip()
    if not raw_channel:
        logger.info("x_poster_dashboard_disabled_no_channel")
        return None

    try:
        channel_id = int(raw_channel)
    except ValueError:
        logger.error(
            "x_poster_dashboard_invalid_channel_id",
            extra={"value": raw_channel},
        )
        return None

    update_seconds = int(os.environ.get("X_POSTER_DASHBOARD_UPDATE_SECONDS", str(DEFAULT_UPDATE_SECONDS)))
    health_port = int(os.environ.get("X_POSTER_HEALTH_PORT", str(DEFAULT_HEALTH_PORT)))

    return XPosterDashboard(
        bot=bot,
        channel_id=channel_id,
        update_seconds=update_seconds,
        health_port=health_port,
    )
