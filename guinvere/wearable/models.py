from __future__ import annotations

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field


class MetricSource(str, Enum):
    MI_FITNESS_CLOUD = "mi_fitness_cloud"
    GADGETBRIDGE = "gadgetbridge"  # v2 future
    HEALTH_CONNECT = "health_connect"


class MetricStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    ENDPOINT_CHANGED = "endpoint_changed"


class HealthMetricType(str, Enum):
    HEART_RATE = "heart_rate"
    STEPS = "steps"
    SPO2 = "spo2"
    STRESS = "stress"
    SLEEP = "sleep"
    ACTIVITY = "activity"


class NormalizedHealthSample(BaseModel):
    """Single health metric sample, normalized from any source."""

    metric_type: HealthMetricType
    timestamp: datetime
    device_id: str
    owner_id: str
    value: float
    unit: str
    source: MetricSource = MetricSource.MI_FITNESS_CLOUD
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    metadata: dict[str, str] = Field(default_factory=dict)


class HealthMetricPayload(BaseModel):
    """Batch of normalized health samples from a single sync."""

    sync_timestamp: datetime
    device_id: str
    owner_id: str
    source: MetricSource
    samples: list[NormalizedHealthSample]
    metrics_available: list[HealthMetricType]
    metrics_unavailable: list[HealthMetricType] = Field(default_factory=list)


class DateRange(BaseModel):
    """Date range for API fetch."""

    start: date
    end: date


class MetricResult(BaseModel):
    """Result of fetching a single metric from the API."""

    metric: HealthMetricType
    status: MetricStatus
    samples: list[NormalizedHealthSample] = Field(default_factory=list)
    error: str | None = None


class FetchResult(BaseModel):
    """Result of a full metric fetch cycle."""

    timestamp: datetime
    device_id: str
    metrics: dict[str, MetricResult]
    consecutive_failures: int = 0


class BaselineStage(str, Enum):
    INSUFFICIENT = "insufficient"  # 0-3 days
    PROVISIONAL = "provisional"  # 4-14 days
    STABILIZING = "stabilizing"  # 15-28 days
    STABLE = "stable"  # 28+ days
    REBASELINE = "rebaseline"  # >7 day gap


class GHITier(str, Enum):
    EXCELLENT = "excellent"  # >= 85
    GOOD = "good"  # >= 70
    FAIR = "fair"  # >= 55
    POOR = "poor"  # >= 40
    CRITICAL = "critical"  # < 40


class GHIResult(BaseModel):
    """Global Health Index score result."""

    date: date
    device_id: str
    owner_id: str
    ghi_score: float = Field(ge=0.0, le=100.0)
    confidence: float = Field(ge=0.0, le=1.0)
    tier: GHITier
    sleep_score: float | None = None
    cardio_score: float | None = None
    activity_score: float | None = None
    recovery_score: float | None = None
    suppressed: bool = False
    suppression_reason: str | None = None


class AlertSeverity(str, Enum):
    SEV0 = "SEV0"  # Immediate, bypass quiet hours
    SEV1 = "SEV1"  # Next active window
    SEV2 = "SEV2"  # Daily summary embed
    SEV3 = "SEV3"  # Log only


class AnomalyEvent(BaseModel):
    """Detected health anomaly."""

    time: datetime
    device_id: str
    owner_id: str
    metric: str
    severity: AlertSeverity
    value: float
    baseline: float | None = None
    deviation: float | None = None
    description: str
    alert_sent: bool = False


class MoodModifier(BaseModel):
    """Health-derived mood modifier. Does NOT affect yandere FSM."""

    energy: float = Field(default=0.0, ge=-1.0, le=1.0)
    caring: float = Field(default=0.0, ge=-1.0, le=1.0)
    tone: str = "normal"  # upbeat/normal/gentle/concerned/tender
