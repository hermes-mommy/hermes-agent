"""Alert routing engine with SEV matrix, quiet hours, and rate limiting.

Routes health anomaly events to Discord DM channels based on severity.
SEV0 bypasses quiet hours for immediate attention.
SEV1-3 are buffered and delivered during active hours.
Rate limiting prevents alert storms per severity per time window.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime, time as dtime, timedelta
from typing import Any

import asyncpg
import redis.asyncio as aioredis
import structlog

from guinvere.wearable.config import WearableConfig
from guinvere.wearable.health_consent import check_metric_consent
from guinvere.wearable.models import AlertSeverity, AnomalyEvent, HealthMetricType

try:
    from guinvere.persona.yandere_fsm import is_safe_mode_active
except ImportError:
    is_safe_mode_active = None  # type: ignore[assignment]

REDIS_PERSONA_SAFE_MODE_KEY = "persona:state:safe_mode"

logger = structlog.get_logger(__name__)


@dataclass(slots=True)
class RoutingResult:
    delivered: bool
    buffered: bool
    rate_limited: bool
    severity: AlertSeverity
    channel: str
    event_count: int


@dataclass(slots=True)
class AlertBatch:
    events: list[AnomalyEvent] = field(default_factory=list)
    severity: AlertSeverity = AlertSeverity.SEV3
    batched_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    summary: str = ""


@dataclass(slots=True)
class RateLimiter:
    max_alerts: int
    window_seconds: int
    _history: deque[datetime] = field(default_factory=deque)

    def _prune(self, now: datetime) -> None:
        cutoff = now - timedelta(seconds=self.window_seconds)
        while self._history and self._history[0] < cutoff:
            self._history.popleft()

    def _is_allowed(self, now: datetime | None = None) -> bool:
        current = now or datetime.now(UTC)
        self._prune(current)
        return len(self._history) < self.max_alerts

    def _record_alert(self, now: datetime | None = None) -> None:
        self._history.append(now or datetime.now(UTC))


class AlertRouter:
    def __init__(
        self,
        config: WearableConfig,
        database_url: str,
        discord_channel_id: str | None = None,
        redis_url: str | None = None,
    ) -> None:
        self._config = config
        self._database_url = database_url
        self._discord_channel_id = discord_channel_id
        self._redis_url = redis_url
        self._redis: aioredis.Redis | None = None
        self._pool: asyncpg.Pool | None = None
        self._rate_limiters: dict[str, RateLimiter] = {
            AlertSeverity.SEV0.value: RateLimiter(max_alerts=max(config.wearable_alert_rate_limit, 1), window_seconds=3600),
            AlertSeverity.SEV1.value: RateLimiter(max_alerts=max(config.wearable_alert_rate_limit, 1), window_seconds=3600),
            AlertSeverity.SEV2.value: RateLimiter(max_alerts=max(config.wearable_alert_rate_limit, 1), window_seconds=3600),
            AlertSeverity.SEV3.value: RateLimiter(max_alerts=max(config.wearable_alert_rate_limit, 1), window_seconds=86400),
        }
        self._quiet_hours_start = self._parse_time(config.wearable_quiet_hours_start)
        self._quiet_hours_end = self._parse_time(config.wearable_quiet_hours_end)
        self._buffer: dict[str, list[AlertBatch]] = {AlertSeverity.SEV1.value: [], AlertSeverity.SEV2.value: []}

    async def close(self) -> None:
        if self._pool is not None:
            await self._pool.close()
            self._pool = None
        if self._redis is not None:
            await self._redis.aclose()
            self._redis = None

    async def _ensure_redis(self) -> aioredis.Redis | None:
        if self._redis is not None:
            return self._redis
        if self._redis_url is None:
            return None
        self._redis = aioredis.from_url(self._redis_url, decode_responses=True)
        return self._redis

    async def _is_safe_mode_active(self) -> bool:
        """Return True if HARD STOP safe-mode is active.

        Prefers the yandere_fsm.is_safe_mode_active coroutine when importable.
        Falls back to a direct Redis lookup on persona:state:safe_mode so the
        router is not hard-coupled to the persona FSM module. Returns False
        when neither signal is available so delivery is not silently blocked.
        """
        if is_safe_mode_active is not None:
            try:
                return bool(await is_safe_mode_active())
            except Exception:
                logger.exception("alert_safe_mode_fsm_probe_failed")
        redis = await self._ensure_redis()
        if redis is None:
            return False
        try:
            value = await redis.get(REDIS_PERSONA_SAFE_MODE_KEY)
        except Exception:
            logger.exception("alert_safe_mode_redis_probe_failed", key=REDIS_PERSONA_SAFE_MODE_KEY)
            return False
        if value is None:
            return False
        return str(value).strip().lower() == "true"

    def _resolve_metric_type(self, event: AnomalyEvent) -> HealthMetricType | None:
        try:
            return HealthMetricType(event.metric)
        except ValueError:
            logger.warning("alert_unknown_metric_type", metric=event.metric, device_id=event.device_id)
            return None

    async def _check_event_consent(self, event: AnomalyEvent) -> tuple[bool, bool]:
        """Return (allowed, consent_override_active).

        For SEV0 (life-threatening), consent revocation is overridden but
        flagged via consent_override_active=True so the embed title is
        prefixed with [CONSENT-OVERRIDE].
        """
        metric_type = self._resolve_metric_type(event)
        if metric_type is None:
            return False, False
        result = await check_metric_consent(metric_type)
        if result.allowed:
            return True, False
        if event.severity is AlertSeverity.SEV0:
            logger.warning(
                "alert_consent_overridden_sev0",
                metric=event.metric,
                severity=event.severity.value,
                reason=result.reason,
            )
            return False, True
        return False, False

    async def route_event(self, event: AnomalyEvent) -> RoutingResult | None:
        severity = event.severity
        rate_limiter = self._rate_limiters[severity.value]
        now = datetime.now(UTC)

        if not rate_limiter._is_allowed(now):
            logger.info("alert_rate_limited", severity=severity.value, metric=event.metric, device_id=event.device_id)
            self._inc_alert_counter(severity, "rate_limited")
            return RoutingResult(False, False, True, severity, "rate_limited", 1)

        if severity is AlertSeverity.SEV3:
            logger.info("alert_log_only", severity=severity.value, metric=event.metric, device_id=event.device_id)
            self._inc_alert_counter(severity, "log_only")
            return RoutingResult(False, False, False, severity, "log_only", 1)

        # Consent gate — fail-closed: any exception or denial blocks delivery
        try:
            allowed, consent_override = await self._check_event_consent(event)
        except Exception as exc:
            logger.error("alert_consent_gate_failed", metric=event.metric, error=str(exc))
            return None
        if not allowed and not consent_override:
            logger.info("alert_consent_blocked", metric=event.metric, severity=event.severity)
            return None

        # HARD STOP check
        if await self._is_safe_mode_active():
            if event.severity == AlertSeverity.SEV0:
                # SEV0 bypass HARD STOP
                logger.warning("alert_bypassing_hard_stop_sev0", severity=event.severity)
            else:
                logger.warning("alert_halted_safe_mode", severity=event.severity)
                # Buffer instead of dropping
                self._buffer[event.severity.value].append(AlertBatch(
                    events=[event],
                    severity=event.severity,
                    batched_at=datetime.now(UTC),
                    summary=self._format_batch_summary([event]),
                ))
                return None

        if self._is_quiet_hours(now) and severity in {AlertSeverity.SEV1, AlertSeverity.SEV2}:
            batch = AlertBatch(events=[event], severity=severity, batched_at=now, summary=self._format_batch_summary([event]))
            self._buffer[severity.value].append(batch)
            logger.info("alert_buffered", severity=severity.value, metric=event.metric, device_id=event.device_id)
            self._inc_alert_counter(severity, "buffered")
            return RoutingResult(False, True, False, severity, "buffered", 1)

        if severity is AlertSeverity.SEV0 or not self._is_quiet_hours(now):
            embed = self._format_discord_embed(event, consent_override=consent_override)
            send_started = datetime.now(UTC)
            await self._send_discord_dm(embed)
            latency_ms = int((datetime.now(UTC) - send_started).total_seconds() * 1000)
            self._observe_delivery_latency(severity, latency_ms)
            await self._persist_alert_sent(event)
            rate_limiter._record_alert(now)
            self._inc_alert_counter(severity, "discord_dm")
            logger.info("alert_delivered", severity=severity.value, metric=event.metric, device_id=event.device_id, latency_ms=latency_ms)
            return RoutingResult(True, False, False, severity, "discord_dm", 1)

        batch = AlertBatch(events=[event], severity=severity, batched_at=now, summary=self._format_batch_summary([event]))
        self._buffer[severity.value].append(batch)
        logger.info("alert_buffered_fallback", severity=severity.value, metric=event.metric, device_id=event.device_id)
        self._inc_alert_counter(severity, "buffered")
        return RoutingResult(False, True, False, severity, "buffered", 1)

    async def flush_buffered(self) -> list[RoutingResult]:
        results: list[RoutingResult] = []
        now = datetime.now(UTC)
        if await self._is_safe_mode_active():
            logger.warning("alert_flush_halted_safe_mode")
            return results
        if self._is_quiet_hours(now):
            return results

        for severity_value in (AlertSeverity.SEV1.value, AlertSeverity.SEV2.value):
            batches = self._buffer[severity_value]
            if not batches:
                continue
            events = [event for batch in batches for event in batch.events]
            severity = AlertSeverity(severity_value)
            rate_limiter = self._rate_limiters[severity_value]
            if not rate_limiter._is_allowed(now):
                logger.info("buffer_flush_rate_limited", severity=severity_value, event_count=len(events))
                self._inc_alert_counter(severity, "rate_limited")
                results.append(RoutingResult(False, False, True, severity, "rate_limited", len(events)))
                continue
            embed = self._format_batch_embed(events)
            send_started = datetime.now(UTC)
            await self._send_discord_dm(embed)
            latency_ms = int((datetime.now(UTC) - send_started).total_seconds() * 1000)
            self._observe_delivery_latency(severity, latency_ms)
            for event in events:
                await self._persist_alert_sent(event)
            rate_limiter._record_alert(now)
            self._inc_alert_counter(severity, "discord_dm")
            results.append(RoutingResult(True, False, False, severity, "discord_dm", len(events)))
            logger.info("buffer_flush_delivered", severity=severity_value, event_count=len(events), latency_ms=latency_ms)
            self._buffer[severity_value] = []
        return results

    async def _ensure_pool(self) -> asyncpg.Pool:
        if self._pool is None:
            self._pool = await asyncpg.create_pool(dsn=self._database_url, min_size=1, max_size=5)
        return self._pool

    async def _persist_alert_sent(self, event: AnomalyEvent) -> None:
        pool = await self._ensure_pool()
        query = """
            UPDATE health.anomaly_events
            SET alert_sent = TRUE
            WHERE time = $1 AND metric = $2 AND device_id = $3
        """
        async with pool.acquire() as conn:
            await conn.execute(query, event.time, event.metric, self._as_uuid(event.device_id))

    async def _send_discord_dm(self, embed: dict[str, Any]) -> None:
        logger.info(
            "discord_dm_delivery_hook",
            channel_id=self._discord_channel_id,
            title=embed.get("title"),
            severity=embed.get("severity"),
        )

    def _format_discord_embed(self, event: AnomalyEvent, consent_override: bool = False) -> dict[str, Any]:
        color, title = self._severity_style(event.severity)
        if consent_override:
            title = f"[CONSENT-OVERRIDE] {title}"
        fields = self._event_fields(event)
        return {
            "title": title,
            "color": color,
            "severity": event.severity.value,
            "description": event.description,
            "fields": fields,
            "timestamp": event.time.isoformat(),
            "device_id": event.device_id,
            "owner_id": event.owner_id,
        }

    def _format_batch_embed(self, events: list[AnomalyEvent]) -> dict[str, Any]:
        severity = events[0].severity if events else AlertSeverity.SEV3
        color, _ = self._severity_style(severity)
        return {
            "title": f"📋 Health Alert Summary — {len(events)} events",
            "color": color,
            "severity": severity.value,
            "description": self._format_batch_summary(events),
            "fields": [],
            "timestamp": datetime.now(UTC).isoformat(),
        }

    def _format_batch_summary(self, events: list[AnomalyEvent]) -> str:
        lines = [f"• {event.time.isoformat()} | {event.metric} | {event.severity.value} | value={event.value}" for event in events]
        return "\n".join(lines)

    def _event_fields(self, event: AnomalyEvent) -> list[dict[str, str]]:
        return [
            {"name": "Metric", "value": event.metric, "inline": "true"},
            {"name": "Value", "value": str(event.value), "inline": "true"},
            {"name": "Baseline", "value": self._format_number(event.baseline), "inline": "true"},
            {"name": "Deviation", "value": self._format_number(event.deviation), "inline": "true"},
            {"name": "Timestamp", "value": event.time.isoformat(), "inline": "false"},
        ]

    def _severity_style(self, severity: AlertSeverity) -> tuple[int, str]:
        if severity is AlertSeverity.SEV0:
            return 0xDC143C, "🚨 URGENT HEALTH ALERT"
        if severity is AlertSeverity.SEV1:
            return 0xFF8C00, "⚠️ Health Concern"
        if severity is AlertSeverity.SEV2:
            return 0xFFD700, "ℹ️ Health Notice"
        return 0x808080, "Health Log"

    def _is_quiet_hours(self, now: datetime) -> bool:
        current = now.time()
        if self._quiet_hours_start <= self._quiet_hours_end:
            return self._quiet_hours_start <= current < self._quiet_hours_end
        return current >= self._quiet_hours_start or current < self._quiet_hours_end

    @staticmethod
    def _parse_time(value: str) -> dtime:
        hour, minute = value.split(":", 1)
        return dtime(hour=int(hour), minute=int(minute))

    @staticmethod
    def _format_number(value: float | None) -> str:
        if value is None:
            return "n/a"
        return f"{value:.2f}"

    @staticmethod
    def _as_uuid(value: str) -> str:
        return value

    def _inc_alert_counter(self, severity: AlertSeverity, channel: str) -> None:
        return None

    def _observe_delivery_latency(self, severity: AlertSeverity, latency_ms: int) -> None:
        return None


__all__ = ["AlertBatch", "AlertRouter", "RateLimiter", "RoutingResult"]
