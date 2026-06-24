"""Discord /health-report, /health-trend, /health-baseline commands for Guinevere.

Queries TimescaleDB health tables and formats the results into Discord embeds
with wearable-health styling.

Usage:
    /health-report
    /health-trend
    /health-baseline
"""

from __future__ import annotations

import os
from typing import Any

import asyncpg
import structlog

from ._embed_utils import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    format_wib_timestamp,
    now_wib_str,
    send_denied,
    to_discord_embed,
)
from .colors import ALERT, INFO_BLUE, SUCCESS

logger = structlog.get_logger()

TITLE_REPORT: str = "\U0001f48a Health Report"
TITLE_TREND: str = "\U0001f4c8 Health Trend (7 Hari)"
TITLE_BASELINE: str = "\U0001f3af Health Baselines"
FOOTER_ICON: str = "\U0001f48a Guinevere Wearable Health"
NO_DATA_DESC: str = "Belum ada data kesehatan, Darling. Pastikan wearable sudah sync."

TIER_EMOJI: dict[str, str] = {
    "excellent": "\U0001f31f",
    "good": "\u2705",
    "fair": "\U0001f7e1",
    "poor": "\U0001f7e0",
    "critical": "\U0001f534",
}

STAGE_EMOJI: dict[str, str] = {
    "insufficient": "\U0001f534",
    "provisional": "\U0001f7e1",
    "stabilizing": "\U0001f7e0",
    "stable": "\U0001f7e2",
    "rebaseline": "\U0001f535",
}


def _build_dsn() -> str:
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = int(os.getenv("POSTGRES_PORT", "5433"))
    database = os.getenv("POSTGRES_DB", "guinevere")
    user = os.getenv("POSTGRES_USER", "guinevere")
    password = os.getenv("POSTGRES_PASSWORD", "")
    return f"postgresql://{user}:{password}@{host}:{port}/{database}"


def _owner_device() -> tuple[str, str]:
    return os.getenv("WEARABLE_OWNER_ID", ""), os.getenv("WEARABLE_DEVICE_ID", "")


async def _open_pool() -> asyncpg.Pool:
    return await asyncpg.create_pool(dsn=_build_dsn(), min_size=1, max_size=3)


def _coerce_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return None


async def _fetch_health_report(owner_id: str, device_id: str) -> dict[str, Any] | None:
    pool = await _open_pool()
    try:
        async with pool.acquire() as conn:
            ghi_row = await conn.fetchrow(
                """
                SELECT date, ghi_score, confidence, sleep_score, cardio_score,
                       activity_score, recovery_score, tier
                FROM health.ghi_daily
                WHERE owner_id = $1 AND device_id = $2
                ORDER BY date DESC
                LIMIT 1
                """,
                owner_id,
                device_id,
            )
            if ghi_row is None:
                return None

            anomaly_count = await conn.fetchval(
                """
                SELECT COUNT(*)
                FROM health.anomaly_events
                WHERE owner_id = $1 AND device_id = $2
                  AND time >= NOW() - INTERVAL '24 hours'
                """,
                owner_id,
                device_id,
            )
            last_sync = await conn.fetchval(
                """
                SELECT MAX(time)
                FROM health.heart_rate
                WHERE owner_id = $1 AND device_id = $2
                """,
                owner_id,
                device_id,
            )

        return {
            "ghi_score": float(ghi_row["ghi_score"]),
            "confidence": float(ghi_row["confidence"]),
            "tier": str(ghi_row["tier"]),
            "sleep": ghi_row["sleep_score"],
            "cardio": ghi_row["cardio_score"],
            "activity": ghi_row["activity_score"],
            "recovery": ghi_row["recovery_score"],
            "anomalies_24h": int(anomaly_count or 0),
            "last_sync": last_sync,
        }
    finally:
        await pool.close()


def _score_color(score: float) -> int:
    if score >= 70.0:
        return SUCCESS
    if score >= 55.0:
        return INFO_BLUE
    return ALERT


def _build_report_embed(data: dict[str, Any] | None) -> EmbedData:
    ts = now_wib_str()
    if data is None:
        return EmbedData(
            title=TITLE_REPORT,
            description=NO_DATA_DESC,
            color=INFO_BLUE,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    score = float(data["ghi_score"])
    tier = str(data["tier"])
    confidence_pct = round(float(data["confidence"]) * 100.0, 1)
    last_sync = data["last_sync"]
    last_sync_str = format_wib_timestamp(last_sync) if last_sync is not None else "N/A"

    fields = (
        EmbedField(name="\U0001f48a GHI Score", value=f"{TIER_EMOJI.get(tier, '\u2753')} **{score:.1f}** ({tier})", inline=True),
        EmbedField(name="\U0001f4ca Confidence", value=f"{confidence_pct}%", inline=True),
        EmbedField(name="\U0001f634 Sleep", value=f"{_coerce_float(data['sleep']) or 0.0:.1f}", inline=True),
        EmbedField(name="\u2764 Cardio", value=f"{_coerce_float(data['cardio']) or 0.0:.1f}", inline=True),
        EmbedField(name="\U0001f3c3 Activity", value=f"{_coerce_float(data['activity']) or 0.0:.1f}", inline=True),
        EmbedField(name="\U0001f33f Recovery", value=f"{_coerce_float(data['recovery']) or 0.0:.1f}", inline=True),
        EmbedField(name="\u26a0\ufe0f Anomalies (24h)", value=str(int(data["anomalies_24h"])), inline=True),
        EmbedField(name="\U0001f501 Last Sync", value=last_sync_str, inline=True),
    )

    return EmbedData(
        title=TITLE_REPORT,
        description="Skor kesehatan hari ini, Darling.",
        color=_score_color(score),
        fields=fields,
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def health_report_callback(interaction: Any) -> None:
    """Handle a ``/health-report`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        owner_id, device_id = _owner_device()
        if not owner_id or not device_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f WEARABLE_OWNER_ID/WEARABLE_DEVICE_ID belum diset.",
            )
            return

        data = await _fetch_health_report(owner_id, device_id)
        embed = to_discord_embed(_build_report_embed(data))
        await followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("health_report_callback_failed")
        await followup_send(interaction, content="\u26a0\ufe0f Health report is temporarily unavailable.")


async def _fetch_health_trend(owner_id: str, device_id: str) -> list[dict[str, Any]]:
    pool = await _open_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT date, ghi_score, tier
                FROM health.ghi_daily
                WHERE owner_id = $1 AND device_id = $2
                  AND date >= CURRENT_DATE - INTERVAL '7 days'
                ORDER BY date DESC
                """,
                owner_id,
                device_id,
            )
        return [
            {"date": row["date"], "ghi_score": float(row["ghi_score"]), "tier": str(row["tier"])}
            for row in rows
        ]
    finally:
        await pool.close()


def _build_trend_embed(rows: list[dict[str, Any]]) -> EmbedData:
    ts = now_wib_str()
    if not rows:
        return EmbedData(
            title=TITLE_TREND,
            description=NO_DATA_DESC,
            color=INFO_BLUE,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    scores = [float(row["ghi_score"]) for row in rows]
    avg = sum(scores) / len(scores)
    best = max(rows, key=lambda row: float(row["ghi_score"]))
    worst = min(rows, key=lambda row: float(row["ghi_score"]))

    if len(scores) >= 4:
        older = scores[len(scores) // 2 :]
        newer = scores[: len(scores) // 2]
        delta = (sum(newer) / len(newer)) - (sum(older) / len(older))
    elif len(scores) >= 2:
        delta = scores[0] - scores[-1]
    else:
        delta = 0.0

    if delta > 2.0:
        direction = "\u2197\ufe0f improving"
        color = SUCCESS
    elif delta < -2.0:
        direction = "\u2198\ufe0f declining"
        color = ALERT
    else:
        direction = "\u2192 stable"
        color = INFO_BLUE

    fields: list[EmbedField] = []
    for row in rows:
        date_value = row["date"]
        date_str = date_value.strftime("%Y-%m-%d") if hasattr(date_value, "strftime") else str(date_value)
        emoji = TIER_EMOJI.get(str(row["tier"]), "\u2753")
        fields.append(
            EmbedField(
                name=date_str,
                value=f"{emoji} {float(row['ghi_score']):.1f} ({row['tier']})",
                inline=True,
            )
        )

    fields.extend(
        (
            EmbedField(name="\U0001f4ca Average GHI", value=f"{avg:.1f}", inline=True),
            EmbedField(name="\U0001f4c8 Trend", value=direction, inline=True),
            EmbedField(name="\U0001f31f Best Day", value=f"{best['date']} ({float(best['ghi_score']):.1f})", inline=True),
            EmbedField(name="\U0001f4c9 Worst Day", value=f"{worst['date']} ({float(worst['ghi_score']):.1f})", inline=True),
        )
    )

    return EmbedData(
        title=TITLE_TREND,
        description="Tren GHI 7 hari terakhir.",
        color=color,
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def health_trend_callback(interaction: Any) -> None:
    """Handle a ``/health-trend`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        owner_id, device_id = _owner_device()
        if not owner_id or not device_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f WEARABLE_OWNER_ID/WEARABLE_DEVICE_ID belum diset.",
            )
            return

        rows = await _fetch_health_trend(owner_id, device_id)
        embed = to_discord_embed(_build_trend_embed(rows))
        await followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("health_trend_callback_failed")
        await followup_send(interaction, content="\u26a0\ufe0f Health trend is temporarily unavailable.")


async def _fetch_health_baseline(owner_id: str, device_id: str) -> list[dict[str, Any]]:
    pool = await _open_pool()
    try:
        async with pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT metric, stage, baseline_value, confidence, data_points
                FROM health.baseline_state
                WHERE owner_id = $1 AND device_id = $2
                ORDER BY metric ASC
                """,
                owner_id,
                device_id,
            )
        return [
            {
                "metric": str(row["metric"]),
                "stage": str(row["stage"]),
                "baseline_value": row["baseline_value"],
                "confidence": float(row["confidence"]),
                "data_points": int(row["data_points"]),
            }
            for row in rows
        ]
    finally:
        await pool.close()


def _build_baseline_embed(rows: list[dict[str, Any]]) -> EmbedData:
    ts = now_wib_str()
    if not rows:
        return EmbedData(
            title=TITLE_BASELINE,
            description=NO_DATA_DESC,
            color=INFO_BLUE,
            fields=(),
            footer_icon=FOOTER_ICON,
            timestamp=ts,
        )

    fields: list[EmbedField] = []
    for row in rows:
        stage = str(row["stage"])
        emoji = STAGE_EMOJI.get(stage, "\u2753")
        baseline_value = row["baseline_value"]
        baseline_str = f"{float(baseline_value):.2f}" if baseline_value is not None else "n/a"
        confidence_pct = round(float(row["confidence"]) * 100.0, 1)
        fields.append(
            EmbedField(
                name=f"{emoji} {row['metric']}",
                value=(
                    f"baseline: **{baseline_str}**\n"
                    f"confidence: {confidence_pct}%\n"
                    f"data points: {int(row['data_points'])}"
                ),
                inline=True,
            )
        )

    return EmbedData(
        title=TITLE_BASELINE,
        description="Status baseline per metrik, Darling.",
        color=INFO_BLUE,
        fields=tuple(fields),
        footer_icon=FOOTER_ICON,
        timestamp=ts,
    )


async def health_baseline_callback(interaction: Any) -> None:
    """Handle a ``/health-baseline`` interaction."""
    from ._auth_guard import is_faiz_interaction

    if not is_faiz_interaction(interaction):
        await send_denied(interaction)
        return

    await defer_ephemeral(interaction)

    try:
        owner_id, device_id = _owner_device()
        if not owner_id or not device_id:
            await followup_send(
                interaction,
                content="\u26a0\ufe0f WEARABLE_OWNER_ID/WEARABLE_DEVICE_ID belum diset.",
            )
            return

        rows = await _fetch_health_baseline(owner_id, device_id)
        embed = to_discord_embed(_build_baseline_embed(rows))
        await followup_send(interaction, embed=embed)
    except Exception:
        logger.exception("health_baseline_callback_failed")
        await followup_send(interaction, content="\u26a0\ufe0f Health baseline is temporarily unavailable.")


__all__ = ["health_report_callback", "health_trend_callback", "health_baseline_callback"]
