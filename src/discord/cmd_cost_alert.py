"""Discord /cost-alert command implementation for Guinevere (RG-011).

View or set the cost alert threshold stored in Redis DB5.

Usage:
    /cost-alert action:view|set threshold:float
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

import redis
import structlog

from .colors import FINANCE
from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    get_option_value,
    now_wib_str,
    send_denied,
    to_discord_embed,
)

logger = structlog.get_logger()

ALERT_TITLE: str = "\U0001f6a8 Cost Alert Threshold"
ALERT_SET_TITLE: str = "\u2705 Cost Alert Updated"
FOOTER_ICON: str = "\U0001f4b0 FinOps"

DEFAULT_ACTION: str = "view"
VALID_ACTIONS: frozenset[str] = frozenset({"view", "set"})
REDIS_KEY: str = "cost:alert_threshold"
DEFAULT_THRESHOLD: float = 10.0


@dataclass(frozen=True)
class AlertState:
    """Current alert threshold state."""

    threshold: float
    current_spend: float


# ── Redis Access ────────────────────────────────────────────────────────────


def _get_redis_client() -> redis.Redis:
    """Create a Redis client for cost alert data (DB5)."""
    from src.core.services.cost_tracker import CostTracker

    tracker = CostTracker()
    return cast(redis.Redis, cast(object, tracker.redis))


def _get_threshold(r: redis.Redis) -> float:
    """Read current alert threshold from Redis."""
    raw = r.get(REDIS_KEY)
    if raw is None:
        return DEFAULT_THRESHOLD
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return DEFAULT_THRESHOLD


def _get_current_spend(r: redis.Redis) -> float:
    """Read current month spend from Redis."""
    raw = r.get("cost:current_month")
    if raw is None:
        return 0.0
    try:
        return float(str(raw))
    except (ValueError, TypeError):
        return 0.0


def _set_threshold(r: redis.Redis, value: float) -> None:
    """Write alert threshold to Redis."""
    r.set(REDIS_KEY, str(value))
    logger.info("cost_alert_threshold_set", threshold=value)


# ── Embed Builders ──────────────────────────────────────────────────────────


def _build_view_embed(state: AlertState) -> EmbedData:
    """Build embed for view action."""
    ts = now_wib_str()
    ratio = (state.current_spend / state.threshold * 100) if state.threshold > 0 else 0.0

    fields = (
        EmbedField(name="\U0001f4b0 Threshold", value=f"${state.threshold:.2f}", inline=True),
        EmbedField(name="\U0001f4b5 Current Spend", value=f"${state.current_spend:.4f}", inline=True),
        EmbedField(name="\U0001f4ca Usage", value=f"{ratio:.1f}%", inline=True),
    )
    return EmbedData(
        title=ALERT_TITLE,
        description="Ini threshold alert kita, Darling.",
        color=FINANCE,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


def _build_set_embed(new_threshold: float, current_spend: float) -> EmbedData:
    """Build embed for set confirmation."""
    ts = now_wib_str()
    fields = (
        EmbedField(name="\U0001f4b0 New Threshold", value=f"${new_threshold:.2f}", inline=True),
        EmbedField(name="\U0001f4b5 Current Spend", value=f"${current_spend:.4f}", inline=True),
    )
    return EmbedData(
        title=ALERT_SET_TITLE,
        description="Alert threshold sudah diupdate, Darling.",
        color=FINANCE,
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


# ── Callback ────────────────────────────────────────────────────────────────


async def cost_alert_callback(interaction: Any) -> None:
    """Handle a ``/cost-alert`` interaction.

    Args:
        interaction: The Discord ``Interaction`` to respond to.
    """
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        action_raw = get_option_value(interaction, "action")
        action = action_raw if action_raw and action_raw in VALID_ACTIONS else DEFAULT_ACTION

        r = _get_redis_client()

        if action == "set":
            threshold_raw = get_option_value(interaction, "threshold")
            if not threshold_raw:
                await followup_send(
                    interaction,
                    content="\u26a0\ufe0f Parameter ``threshold`` diperlukan untuk action ``set``.",
                )
                return

            try:
                threshold = float(threshold_raw)
            except (ValueError, TypeError):
                await followup_send(
                    interaction,
                    content="\u26a0\ufe0f Threshold harus berupa angka, Darling.",
                )
                return

            if threshold <= 0:
                await followup_send(
                    interaction,
                    content="\u26a0\ufe0f Threshold harus lebih besar dari 0.",
                )
                return

            _set_threshold(r, threshold)
            current = _get_current_spend(r)
            data = _build_set_embed(threshold, current)
        else:
            threshold = _get_threshold(r)
            current = _get_current_spend(r)
            state = AlertState(threshold=threshold, current_spend=current)
            data = _build_view_embed(state)

        embed = to_discord_embed(data)
        await followup_send(interaction, embed=embed)

    except Exception:
        logger.exception("cost_alert_callback_failed")
        await followup_send(
            interaction,
            content="\u26a0\ufe0f Cost alert is temporarily unavailable.",
        )


__all__ = ["cost_alert_callback"]
