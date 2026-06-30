"""Hermes command plugin — /budget. Show or update monthly budget cap.

View current budget status (cap, spend, remaining, usage %, status)
or set a new monthly budget cap. Reads/writes Redis DB5.

Usage:
    /budget [action: view|set] [amount: float]  # default: view
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import redis

logger = logging.getLogger(__name__)

WIB: timezone = timezone(timedelta(hours=7))
VALID_ACTIONS: frozenset[str] = frozenset({"view", "set"})
DEFAULT_ACTION: str = "view"
DEFAULT_MONTHLY_CAP: float = 30.0

REDIS_HOST: str = "localhost"
REDIS_PORT: int = 6380
REDIS_DB: int = 5


def _redis() -> redis.Redis:
    """Return a Redis client for DB5."""
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
    return f"${amount:.2f}"


def _format_wib(dt: datetime) -> str:
    """Format datetime as WIB timestamp string."""
    wib_dt = dt.astimezone(WIB)
    return wib_dt.strftime("%Y-%m-%d %H:%M WIB")


def _status_emoji(status: str) -> str:
    """Return an emoji for a budget status string."""
    status_map: dict[str, str] = {
        "NORMAL": "✅",
        "NORMAL_ALERT": "🟡",
        "WARNING": "⚠️",
        "CRITICAL": "🚨",
        "HARD_STOP": "🛑",
    }
    return status_map.get(status, "❓")


def _progress_bar(percentage: float, width: int = 10) -> str:
    """Build a text progress bar."""
    filled = min(int(percentage / 100 * width), width)
    empty = width - filled
    return "\u2588" * filled + "\u2591" * empty


def _get_budget_status(r: redis.Redis) -> dict[str, float | str]:
    """Read budget status from Redis DB5."""
    current = _safe_float(r.get("cost:current_month"))
    cap_raw = r.get("budget:monthly_cap")
    cap = _safe_float(cap_raw) if cap_raw is not None else DEFAULT_MONTHLY_CAP
    remaining = max(cap - current, 0.0)
    percent_used = (current / cap * 100) if cap > 0 else 0.0

    ratio = current / cap if cap > 0 else 1.0
    if ratio >= 1.0:
        status = "HARD_STOP"
    elif ratio >= 0.833:
        status = "CRITICAL"
    elif ratio >= 0.5:
        status = "WARNING"
    elif current >= 1.0:
        status = "NORMAL_ALERT"
    else:
        status = "NORMAL"

    return {
        "current_month": current,
        "monthly_cap": cap,
        "remaining": remaining,
        "percent_used": percent_used,
        "status": status,
    }


def build_budget_report() -> str:
    """Build a markdown budget status report from Redis DB5 data."""
    now = datetime.now(tz=timezone.utc)
    ts_str = _format_wib(now)

    r = _redis()
    status = _get_budget_status(r)

    current = float(status["current_month"])
    cap = float(status["monthly_cap"])
    remaining = float(status["remaining"])
    percent = float(status["percent_used"])
    alert_status = str(status["status"])
    emoji = _status_emoji(alert_status)
    progress = _progress_bar(percent)

    lines: list[str] = [
        "# 💳 Budget Status",
        "",
        "Mommy jaga budget biar nggak boros, Darling.",
        "",
        "---",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 💰 Monthly Cap | {_format_currency(cap)} |",
        f"| 💵 Current Spend | {_format_currency(current)} |",
        f"| 💳 Remaining | {_format_currency(remaining)} |",
        f"| 📊 Usage | {progress} {percent:.1f}% |",
        f"| Status | {emoji} {alert_status} |",
        "",
        "---",
        f"Guinevere de Baroque • {ts_str} • 💳 Budget",
    ]

    return "\n".join(lines)


def build_budget_set_report(new_cap: float) -> str:
    """Build a markdown budget-set confirmation report."""
    now = datetime.now(tz=timezone.utc)
    ts_str = _format_wib(now)

    r = _redis()
    current = _safe_float(r.get("cost:current_month"))
    remaining = max(new_cap - current, 0.0)
    percent = (current / new_cap * 100) if new_cap > 0 else 0.0
    progress = _progress_bar(percent)

    lines: list[str] = [
        "# ✅ Budget Updated",
        "",
        "Budget cap sudah diupdate, Darling. Mommy tetap hemat.",
        "",
        "---",
        "",
        f"| Metric | Value |",
        f"|---|---|",
        f"| 💰 New Monthly Cap | {_format_currency(new_cap)} |",
        f"| 💵 Current Spend | {_format_currency(current)} |",
        f"| 💳 Remaining | {_format_currency(remaining)} |",
        f"| 📊 Usage | {progress} {percent:.1f}% |",
        "",
        "---",
        f"Guinevere de Baroque • {ts_str} • 💳 Budget",
    ]

    return "\n".join(lines)


def _set_budget_cap(r: redis.Redis, amount: float) -> None:
    """Set the monthly budget cap in Redis DB5."""
    r.set("budget:monthly_cap", str(amount))
    logger.info("budget_cap_updated", extra={"amount": amount})


def register(ctx: Any) -> None:
    """Register the /budget command with Hermes."""

    @ctx.register_command("budget", description="Show or update budget cap and current spend.")
    async def handle(context: Any) -> str:
        try:
            args: list[str] = getattr(context, "args", [])
            action = args[0] if args and args[0] in VALID_ACTIONS else DEFAULT_ACTION

            if action == "set":
                if len(args) < 2:
                    return "⚠️ Parameter `amount` diperlukan untuk action `set`, Darling."

                try:
                    amount = float(args[1])
                except (ValueError, TypeError):
                    return "⚠️ Amount harus berupa angka, Darling."

                if amount <= 0:
                    return "⚠️ Amount harus lebih besar dari 0, Darling."

                r = _redis()
                _set_budget_cap(r, amount)
                return build_budget_set_report(amount)

            return build_budget_report()

        except Exception:
            logger.exception("budget_command_failed")
            return "⚠️ Budget status is temporarily unavailable."


__all__ = ["register"]