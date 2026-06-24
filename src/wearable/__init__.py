"""Wearable health data pipeline — Mi Fitness Cloud -> TimescaleDB -> GHI -> Mood.

P14: Ingests health metrics from Xiaomi Mi Fitness Cloud API, normalizes,
buffers in Redis DB2, writes to TimescaleDB health.* schema, computes
baselines/anomalies/GHI scores, and feeds mood_engine.py as a modifier.

Safety: Health data NEVER drives yandere_fsm.py. NEVER used for confrontation.
Consent: Fail-closed gate via wearable-health.* scopes.
"""

from __future__ import annotations

from .config import WearableConfig, get_wearable_config
from .errors import (
    AuthError,
    CaptchaRequiredError,
    CircuitBreakerOpenError,
    ConsentDeniedError,
    DeviceUntrustedError,
    EndpointDriftError,
    MetricUnavailableError,
    RateLimitError,
    WearableError,
)
from .models import (
    AlertSeverity,
    AnomalyEvent,
    BaselineStage,
    DateRange,
    FetchResult,
    GHIResult,
    GHITier,
    HealthMetricPayload,
    HealthMetricType,
    MetricResult,
    MetricSource,
    MetricStatus,
    MoodModifier,
    NormalizedHealthSample,
)

__version__ = "1.0.0"

__all__ = [
    # Config
    "WearableConfig",
    "get_wearable_config",
    # Errors
    "WearableError",
    "AuthError",
    "RateLimitError",
    "CaptchaRequiredError",
    "EndpointDriftError",
    "DeviceUntrustedError",
    "CircuitBreakerOpenError",
    "ConsentDeniedError",
    "MetricUnavailableError",
    # Models
    "MetricSource",
    "MetricStatus",
    "HealthMetricType",
    "NormalizedHealthSample",
    "HealthMetricPayload",
    "DateRange",
    "MetricResult",
    "FetchResult",
    "BaselineStage",
    "GHITier",
    "GHIResult",
    "AlertSeverity",
    "AnomalyEvent",
    "MoodModifier",
]
