"""Mi Fitness Cloud API client with circuit breaker and graceful degradation.

Fetches health metrics from Xiaomi's Mi Fitness Cloud API using the
`mi-fitness` v0.2.0 SDK. The SDK is async, token-file based, and
per-relative. This module adapts the SDK into the Guinevere wearable
sync contract: consent gate, Redis buffer, per-date fetch, typed
pydantic normalization, circuit breaker.

Auth is performed once per process via `token.json` (produced by
`XiaomiAuth.login_qr()` on a workstation, shipped to the VPS via SOPS).
`MI_FITNESS_PASS_TOKEN` is preserved as a legacy field for backwards
compatibility but is no longer consumed by the auth path.
"""

from __future__ import annotations

import asyncio
import importlib
import json
import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import structlog
from structlog.stdlib import BoundLogger

from guinevere.wearable.config import WearableConfig
from guinevere.wearable.errors import (
    AuthError,
    CircuitBreakerOpenError,
    MetricUnavailableError,
    RateLimitError,
    WearableError,
)
from guinevere.wearable.models import (
    DateRange,
    FetchResult,
    HealthMetricType,
    MetricResult,
    MetricSource,
    MetricStatus,
    NormalizedHealthSample,
)

logger: BoundLogger = structlog.get_logger(__name__)

MiHealthClient: Any | None = None
XiaomiAuth: Any | None = None
MiSDKError: type[Exception] | None = None
TokenExpiredError: type[Exception] | None = None
APIError: type[Exception] | None = None
FamilyMemberNotFoundError: type[Exception] | None = None
mi_fitness_available = False

try:
    mi_fitness_module = importlib.import_module("mi_fitness")
    MiHealthClient = getattr(mi_fitness_module, "MiHealthClient", None)
    XiaomiAuth = getattr(mi_fitness_module, "XiaomiAuth", None)
    _mi_sdk_error = getattr(mi_fitness_module, "MiSDKError", None)
    MiSDKError = _mi_sdk_error if isinstance(_mi_sdk_error, type) and issubclass(_mi_sdk_error, Exception) else Exception
    _token_expired = getattr(mi_fitness_module, "TokenExpiredError", None)
    TokenExpiredError = _token_expired if isinstance(_token_expired, type) and issubclass(_token_expired, Exception) else Exception
    _api_error = getattr(mi_fitness_module, "APIError", None)
    APIError = _api_error if isinstance(_api_error, type) and issubclass(_api_error, Exception) else Exception
    _family_not_found = getattr(mi_fitness_module, "FamilyMemberNotFoundError", None)
    FamilyMemberNotFoundError = _family_not_found if isinstance(_family_not_found, type) and issubclass(_family_not_found, Exception) else Exception
    mi_fitness_available = MiHealthClient is not None
except ImportError:
    MiHealthClient = None
    XiaomiAuth = None
    MiSDKError = Exception
    TokenExpiredError = Exception
    APIError = Exception
    FamilyMemberNotFoundError = Exception


class _CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class _CircuitBreaker:
    __slots__ = ("threshold", "recovery_seconds", "consecutive_failures", "opened_at", "state")

    def __init__(self, threshold: int, recovery_seconds: int) -> None:
        self.threshold = threshold
        self.recovery_seconds = recovery_seconds
        self.consecutive_failures = 0
        self.opened_at: datetime | None = None
        self.state = _CircuitState.CLOSED

    def allow_request(self) -> bool:
        if self.state == _CircuitState.CLOSED:
            return True
        if self.state == _CircuitState.OPEN:
            if self.opened_at is None:
                return False
            if datetime.now(timezone.utc) - self.opened_at >= timedelta(seconds=self.recovery_seconds):
                self.state = _CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.opened_at = None
        self.state = _CircuitState.CLOSED

    def record_failure(self) -> None:
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.threshold:
            self.state = _CircuitState.OPEN
            self.opened_at = datetime.now(timezone.utc)


class MiFitnessClient:
    """Async Mi Fitness Cloud API client adapted to the Guinevere wearable contract."""

    SDK_FETCHERS: dict[HealthMetricType, str] = {
        HealthMetricType.HEART_RATE: "get_heart_rate",
        HealthMetricType.STEPS: "get_steps",
        HealthMetricType.SPO2: "get_spo2_history",
        HealthMetricType.SLEEP: "get_sleep",
        # STRESS and ACTIVITY are not exposed by mi-fitness v0.2.0 public API.
    }

    def __init__(self, config: WearableConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._client_cm: Any | None = None
        self._token_loaded = False
        self._circuit = _CircuitBreaker(
            threshold=config.wearable_circuit_breaker_threshold,
            recovery_seconds=config.wearable_circuit_breaker_recovery_sec,
        )

    async def authenticate(self) -> None:
        if not self.config.mi_fitness_user_id:
            raise AuthError("MI_FITNESS_USER_ID missing from configuration")
        if not self.config.mi_fitness_token_path:
            raise AuthError("MI_FITNESS_TOKEN_PATH missing from configuration")
        if not mi_fitness_available or MiHealthClient is None:
            raise AuthError("mi-fitness SDK not installed; run `uv add mi-fitness>=0.2.0,<0.3`")

        token_path = Path(self.config.mi_fitness_token_path)
        if not token_path.is_file():
            raise AuthError(
                f"Mi Fitness token file not found at {token_path}; "
                "generate it once with `uv run python -m mi_fitness.cli qr-login` "
                "and ship via SOPS."
            )
        try:
            json.loads(token_path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise AuthError(f"Mi Fitness token file is not valid JSON: {exc}") from exc

        self._token_loaded = True
        self._record_auth_outcome(True)
        logger.info("mi_fitness_token_loaded", token_path=str(token_path))

    async def fetch_metrics(self, date_range: DateRange) -> FetchResult:
        if not self._circuit.allow_request():
            raise CircuitBreakerOpenError("Mi Fitness circuit breaker is open")
        if not self._token_loaded:
            await self.authenticate()

        metrics: dict[str, MetricResult] = {}
        for metric in self._iter_metrics_to_fetch():
            if metric not in self.SDK_FETCHERS:
                metrics[metric.value] = MetricResult(
                    metric=metric,
                    status=MetricStatus.UNAVAILABLE,
                    error=f"Metric {metric.value} is not exposed by mi-fitness v0.2.0 SDK",
                )
                continue

            try:
                metrics[metric.value] = await self._fetch_single(metric, date_range)
            except MetricUnavailableError as exc:
                logger.warning("metric_unavailable", metric=metric.value, error=str(exc))
                metrics[metric.value] = MetricResult(metric=metric, status=MetricStatus.UNAVAILABLE, error=str(exc))
            except RateLimitError as exc:
                self._circuit.record_failure()
                metrics[metric.value] = MetricResult(metric=metric, status=MetricStatus.UNAVAILABLE, error=str(exc))
            except WearableError as exc:
                self._circuit.record_failure()
                logger.exception("metric_fetch_failed", metric=metric.value, error=str(exc))
                metrics[metric.value] = MetricResult(metric=metric, status=MetricStatus.UNAVAILABLE, error=str(exc))
            except Exception as exc:  # noqa: BLE001
                self._circuit.record_failure()
                logger.exception("metric_fetch_unexpected_error", metric=metric.value, error=str(exc))
                metrics[metric.value] = MetricResult(metric=metric, status=MetricStatus.UNAVAILABLE, error=str(exc))
            else:
                self._circuit.record_success()

        return FetchResult(
            timestamp=datetime.now(timezone.utc),
            device_id=self.config.wearable_device_id,
            metrics=metrics,
            consecutive_failures=self._circuit.consecutive_failures,
        )

    async def close(self) -> None:
        """Close the underlying SDK client if it was opened."""
        if self._client_cm is not None and self._client is not None:
            try:
                await self._client_cm.__aexit__(None, None, None)
            except Exception as exc:  # noqa: BLE001
                logger.warning("sdk_client_close_failed", error=str(exc))
            self._client = None
            self._client_cm = None

    async def _open_client(self) -> Any:
        if self._client is not None:
            return self._client
        if not mi_fitness_available or MiHealthClient is None:
            raise MetricUnavailableError(
                "Mi Fitness SDK is unavailable; run `uv add mi-fitness>=0.2.0,<0.3`"
            )
        cm = MiHealthClient.from_token(self.config.mi_fitness_token_path)
        try:
            client = await cm.__aenter__()
        except Exception as exc:  # noqa: BLE001
            raise AuthError(f"Mi Fitness client initialization failed: {exc}") from exc
        self._client_cm = cm
        self._client = client
        return client

    async def _fetch_single(self, metric: HealthMetricType, date_range: DateRange) -> MetricResult:
        method_name = self.SDK_FETCHERS.get(metric)
        if method_name is None:
            raise MetricUnavailableError(
                f"Metric {metric.value} is not exposed by mi-fitness v0.2.0 SDK",
                metric=metric.value,
            )
        client = await self._open_client()
        method = getattr(client, method_name)

        samples: list[NormalizedHealthSample] = []
        cursor = date_range.start
        while cursor <= date_range.end:
            try:
                rows = await method(self.config.mi_fitness_relative_uid, cursor)
            except Exception as exc:  # noqa: BLE001
                # Check rate limit first since it's the most specific string match
                if self._is_rate_limit_error(exc):
                    self._retry_with_backoff()
                    raise RateLimitError(f"Mi Fitness rate limit detected: {exc}") from exc
                # SDK-specific exceptions (only match when SDK is installed and raises its own types)
                if mi_fitness_available and FamilyMemberNotFoundError is not Exception and isinstance(exc, FamilyMemberNotFoundError):
                    raise MetricUnavailableError(
                        f"Relative UID {self.config.mi_fitness_relative_uid!r} not found",
                        metric=metric.value,
                    ) from exc
                if mi_fitness_available and TokenExpiredError is not Exception and isinstance(exc, TokenExpiredError):
                    raise AuthError(f"Mi Fitness token expired; refresh via SOPS + qr-login: {exc}") from exc
                if mi_fitness_available and APIError is not Exception and isinstance(exc, APIError):
                    raise WearableError(f"Mi Fitness API error: {exc}") from exc
                raise WearableError(f"Mi Fitness SDK call failed: {exc}") from exc

            if rows:
                for row in rows:
                    sample = self._normalize_typed_sample(metric, row)
                    if sample is not None:
                        samples.append(sample)
            cursor += timedelta(days=1)

        status = MetricStatus.AVAILABLE if samples else MetricStatus.UNAVAILABLE
        return MetricResult(
            metric=metric,
            status=status,
            samples=samples,
            error=None if samples else "No samples in window",
        )

    def _iter_metrics_to_fetch(self) -> list[HealthMetricType]:
        return [
            HealthMetricType.HEART_RATE,
            HealthMetricType.STEPS,
            HealthMetricType.SPO2,
            HealthMetricType.STRESS,
            HealthMetricType.SLEEP,
            HealthMetricType.ACTIVITY,
        ]

    def _normalize_typed_sample(self, metric: HealthMetricType, row: Any) -> NormalizedHealthSample | None:
        try:
            if metric == HealthMetricType.HEART_RATE:
                ts = getattr(row, "timestamp", None)
                value = float(getattr(row, "bpm", 0.0))
                unit = "bpm"
            elif metric == HealthMetricType.STEPS:
                ts = getattr(row, "timestamp", None)
                value = float(getattr(row, "steps", 0.0))
                unit = "steps"
            elif metric == HealthMetricType.SPO2:
                ts = getattr(row, "timestamp", None)
                value = float(getattr(row, "value", 0.0))
                unit = "%"
            elif metric == HealthMetricType.SLEEP:
                ts = getattr(row, "end_time", None) or getattr(row, "timestamp", None)
                value = float(getattr(row, "total_minutes", 0.0))
                unit = "minutes"
            else:
                return None
        except (AttributeError, TypeError, ValueError) as exc:
            logger.warning("skipping_unexpected_row_shape", metric=metric.value, error=str(exc))
            return None

        if ts is None or value == 0.0:
            logger.warning("skipping_incomplete_typed_sample", metric=metric.value)
            return None
        try:
            parsed_ts = self._parse_timestamp(ts)
        except (TypeError, ValueError) as exc:
            logger.warning("skipping_invalid_timestamp", metric=metric.value, error=str(exc))
            return None

        return NormalizedHealthSample(
            metric_type=metric,
            timestamp=parsed_ts,
            device_id=self.config.wearable_device_id,
            owner_id=self.config.wearable_owner_id,
            value=value,
            unit=unit,
            source=MetricSource.MI_FITNESS_CLOUD,
            confidence=1.0,
            metadata={},
        )

    def _parse_timestamp(self, raw_timestamp: Any) -> datetime:
        if isinstance(raw_timestamp, datetime):
            return raw_timestamp if raw_timestamp.tzinfo else raw_timestamp.replace(tzinfo=timezone.utc)
        if isinstance(raw_timestamp, (int, float)):
            return datetime.fromtimestamp(float(raw_timestamp), tz=timezone.utc)
        if isinstance(raw_timestamp, str):
            normalized = raw_timestamp.replace("Z", "+00:00")
            parsed = datetime.fromisoformat(normalized)
            return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
        raise ValueError(f"Unsupported timestamp type: {type(raw_timestamp).__name__}")

    def _retry_with_backoff(self, attempts: int = 3) -> None:
        delay = 1.0
        for _ in range(attempts):
            time.sleep(delay)
            delay = min(delay * 2, 30.0)

    def _is_rate_limit_error(self, exc: Exception) -> bool:
        message = str(exc).lower()
        return any(token in message for token in ("rate limit", "too many requests", "429"))

    def _record_auth_outcome(self, success: bool) -> None:
        logger.debug("mi_fitness_auth_outcome", success=success)
