"""Hermes command plugin — /cost. Show LLM cost usage by period.

Reads from Redis DB5 cost tracker and returns a markdown report
with total spend, per-model breakdown, per-tool breakdown, 3-day trend,
and projected month-end spend.

Usage:
    /cost [period: today|week|month]  # default: today
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

import redis

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
VALID_PERIODS: frozenset[str] = frozenset({"today", "week", "month"})
DEFAULT_PERIOD: str = "today"

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6380
REDIS_DB: int = 5


def _redis() -> redis.Redis:
    """Return a Redis client for DB5 cost tracking."""
    return redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)


def _safe_float(raw: object) -> float:
    """Convert a Redis value to float, returning 0.0 on failure."""
    if raw is None:
        return 0.0
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return 0.0


def _format_currency(amount: float) -> str:
    """Format a float as a currency string."""
    return f"${amount:.4f}"


def _format_wib(dt: datetime) -> str:
    """Format datetime as WIB timestamp string."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _period_total(r: redis.Redis, period: str, ref_date: date) -> float:
    """Get total cost for the specified period."""
    if period == "today":
        return _safe_float(r.get("cost:current_day"))

    if period == "week":
        total = 0.0
        for i in range(7):
            day = ref_date - timedelta(days=i)
            total += _safe_float(r.get(f"cost:daily:{day.isoformat()}"))
        return total

    return _safe_float(r.get("cost:current_month"))


def _model_breakdown(r: redis.Redis) -> list[tuple[str, float]]:
    """Get per-model cost breakdown, top 5 by cost."""
    models: list[tuple[str, float]] = []
    try:
        for key in r.scan_iter(match="cost:by_model:*"):
            model_name = key.removeprefix("cost:by_model:")
            cost = _safe_float(r.get(key))
            if cost > 0:
                models.append((model_name, cost))
    except Exception:
        logger.warning("cost_model_breakdown_scan_failed")
    models.sort(key=lambda item: item[1], reverse=True)
    return models[:5]


def _tool_breakdown(r: redis.Redis, ref_date: date) -> list[tuple[str, float]]:
    """Get per-tool cost breakdown for today, top 5."""
    tools: list[tuple[str, float]] = []
    today_str = ref_date.isoformat()
    try:
        for key in r.scan_iter(match=f"tool:cost:*:{today_str}"):
            suffix = key.removeprefix("tool:cost:")
            if suffix.startswith("total:"):
                continue
            parts = suffix.rsplit(":", 1)
            if len(parts) != 2:
                continue
            tool_name = parts[0]
            cost = _safe_float(r.get(key))
            if cost > 0:
                tools.append((tool_name, cost))
    except Exception:
        logger.warning("cost_tool_breakdown_scan_failed")
    tools.sort(key=lambda item: item[1], reverse=True)
    return tools[:5]


def _trend_3day(r: redis.Redis, ref_date: date) -> list[tuple[str, float]]:
    """Get 3-day cost trend."""
    trend: list[tuple[str, float]] = []
    for i in range(2, -1, -1):
        day = ref_date - timedelta(days=i)
        cost = _safe_float(r.get(f"cost:daily:{day.isoformat()}"))
        trend.append((day.strftime("%b %d"), cost))
    return trend


def _projected_month_end(r: redis.Redis, ref_date: date) -> float:
    """Project month-end spend based on daily average."""
    import calendar

    monthly_so_far = _safe_float(r.get("cost:current_month"))
    day_of_month = ref_date.day
    if day_of_month <= 0:
        return monthly_so_far
    days_in_month = calendar.monthrange(ref_date.year, ref_date.month)[1]
    daily_avg = monthly_so_far / day_of_month
    return daily_avg * days_in_month


def _format_trend_bar(trend: list[tuple[str, float]]) -> str:
    """Format trend data as visual text bars."""
    if not trend:
        return "\u2014"
    costs = [c for _, c in trend]
    max_cost = max(costs) if costs else 0.0
    lines: list[str] = []
    for label, cost in trend:
        if max_cost > 0:
            bar_len = int((cost / max_cost) * 10)
        else:
            bar_len = 0
        bar = "\u2588" * max(bar_len, 1) if cost > 0 else "\u2591"
        lines.append(f"`{label}` {bar} {_format_currency(cost)}")
    return "\n".join(lines)


def build_cost_report(period: str = DEFAULT_PERIOD) -> str:
    """Build a markdown cost report from Redis DB5 data.

    Args:
        period: One of "today", "week", "month".

    Returns:
        A markdown-formatted cost report string.
    """
    if period not in VALID_PERIODS:
        period = DEFAULT_PERIOD

    now = datetime.now(tz=timezone.utc)
    ref_date = now.date()
    ts_str = _format_wib(now)

    r = _redis()

    total = _period_total(r, period, ref_date)
    models = _model_breakdown(r)
    tools = _tool_breakdown(r, ref_date)
    trend = _trend_3day(r, ref_date)
    projected = _projected_month_end(r, ref_date)
    monthly_total = _safe_float(r.get("cost:current_month"))

    lines: list[str] = [
        "# 💰 Cost Report",
        "",
        "Ini pengeluaran kita, Darling. Mommy jaga supaya tetap hemat.",
        "",
        "---",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 💵 {period.capitalize()} Spend | {_format_currency(total)} |",
        f"| 📅 Month to Date | {_format_currency(monthly_total)} |",
        f"| 📈 Projected Month-End | {_format_currency(projected)} |",
        "",
        "---",
        "",
        "## 🤖 Per-Model Breakdown",
        "",
    ]

    if models:
        lines.append("| Model | Cost |")
        lines.append("|---|---|")
        for name, cost in models:
            lines.append(f"| `{name}` | {_format_currency(cost)} |")
    else:
        lines.append("No model costs recorded yet.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 🔧 Per-Tool Breakdown (Today)")
    lines.append("")

    if tools:
        lines.append("| Tool | Cost |")
        lines.append("|---|---|")
        for name, cost in tools:
            lines.append(f"| `{name}` | {_format_currency(cost)} |")
    else:
        lines.append("No tool costs recorded today.")
    lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 📊 3-Day Trend")
    lines.append("")
    lines.append(_format_trend_bar(trend))
    lines.append("")

    lines.append("")
    lines.append("---")
    lines.append(f"Guinevere de Baroque • {ts_str} • 💰 FinOps")

    return "\n".join(lines)


def register(ctx: Any) -> None:
    """Register the /cost command with Hermes."""

    @ctx.register_command("cost", description="Show Guinevere cost usage for a given period.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            period = args[0] if args and args[0] in VALID_PERIODS else DEFAULT_PERIOD
            return build_cost_report(period=period)
        except Exception:
            logger.exception("cost_command_failed")
            return "⚠️ Cost report is temporarily unavailable."


__all__ = ["register"]