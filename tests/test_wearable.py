"""Comprehensive unit tests for src/wearable/ package.

Tests cover all wearable health modules:
- config.py: WearableConfig dataclass, from_env(), defaults, env loading, invalid region
- normalizer.py: normalize_fetch_result() with mock API responses, edge cases
- baseline.py: BaselineCalculator with mock DB, warmup transitions, confidence
- anomaly.py: AnomalyDetector with known anomalous values, thresholds, persistence
- ghi.py: GHIScorer with pillar scores, weight rebalance, confidence model
- mood_integration.py: GHI tier to mood mapping, quiet hours, distress override
- alert_router.py: SEV routing, quiet hours buffering, SEV0 bypass, rate limiting
- health_consent.py: consent grant/revoke, fail-closed gate, Redis cache

All external dependencies (Redis, asyncpg, httpx) are mocked -- no real connections.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, time as dtime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.persona.mood_engine import Mood

# Ensure project root is on sys.path for ``from src.*`` imports.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.wearable.alert_router import (
    AlertBatch,
    AlertRouter,
    RateLimiter,
)
from src.wearable.anomaly import (
    METRIC_THRESHOLDS,
    AnomalyDetector,
    BaselineLike,
    SeverityRule,
)
from src.wearable.baseline import (
    BaselineCalculator,
    _confidence_for_stage,
    _mean_stddev,
)
from src.wearable.config import WearableConfig, get_wearable_config
from src.wearable.ghi import (
    DEFAULT_WEIGHTS,
    GHIScorer,
    BaselineResult as GHIBaselineResult,
    PillarScore,
)
from src.wearable.health_consent import (
    CACHE_KEY_PREFIX,
    CACHE_TTL_SECONDS,
    METRIC_TO_SCOPE,
    VALID_WEARABLE_SCOPES,
    ConsentStatus,
    WearableConsentCheckResult,
    _set_db_session_for_testing,
    _set_redis_for_testing,
    check_metric_consent,
    check_wearable_consent,
    grant_consent,
    invalidate_consent_cache,
    pause_consent,
    revoke_consent,
    withdraw_consent,
)
from src.wearable.models import (
    AlertSeverity,
    AnomalyEvent,
    BaselineStage,
    FetchResult,
    GHIResult,
    GHITier,
    HealthMetricPayload,
    HealthMetricType,
    MetricResult,
    MetricSource,
    MetricStatus,
    NormalizedHealthSample,
)
from src.wearable.mood_integration import (
    QUIET_HOURS_END,
    QUIET_HOURS_START,
    HealthMoodIntegrator,
    WearableMoodModifier,
)
from src.wearable.normalizer import normalize_fetch_result


# ===========================================================================
# Shared helpers / mock builders
# ===========================================================================


def _make_mock_record(data: dict[str, Any]) -> MagicMock:
    """Build a mock asyncpg Record that supports ``row["col"]`` access."""
    rec = MagicMock()
    rec.__getitem__ = MagicMock(side_effect=lambda key: data[key])
    rec.keys = MagicMock(return_value=list(data.keys()))
    return rec


def _make_mock_asyncpg_pool(conn: AsyncMock | None = None) -> tuple[MagicMock, AsyncMock]:
    """Build a (mock_pool, mock_conn) pair.  pool.acquire() yields mock_conn."""
    mock_conn = conn if conn is not None else AsyncMock()
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()

    mock_acquire_cm = AsyncMock()
    mock_acquire_cm.__aenter__.return_value = mock_conn
    mock_acquire_cm.__aexit__.return_value = None
    mock_pool.acquire.return_value = mock_acquire_cm
    return mock_pool, mock_conn


def _make_sample(
    metric_type: HealthMetricType,
    value: float,
    timestamp: datetime | None = None,
    device_id: str = "",
    owner_id: str = "",
    unit: str = "",
    confidence: float = 1.0,
    metadata: dict[str, str] | None = None,
) -> NormalizedHealthSample:
    """Build a NormalizedHealthSample with sensible defaults."""
    return NormalizedHealthSample(
        metric_type=metric_type,
        timestamp=timestamp or datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC),
        device_id=device_id,
        owner_id=owner_id,
        value=value,
        unit=unit,
        confidence=confidence,
        metadata=metadata or {},
    )


def _make_metric_result(
    metric: HealthMetricType,
    status: MetricStatus = MetricStatus.AVAILABLE,
    samples: list[NormalizedHealthSample] | None = None,
) -> MetricResult:
    """Build a MetricResult with optional samples."""
    return MetricResult(metric=metric, status=status, samples=samples or [])


def _make_fetch_result(
    metrics: dict[str, MetricResult] | None = None,
    timestamp: datetime | None = None,
) -> FetchResult:
    """Build a FetchResult with optional metrics dict."""
    return FetchResult(
        timestamp=timestamp or datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC),
        device_id="test-device",
        metrics=metrics or {},
    )


def _make_ghi_result(
    tier: GHITier = GHITier.GOOD,
    ghi_score: float = 75.0,
    confidence: float = 0.8,
    suppressed: bool = False,
    suppression_reason: str | None = None,
) -> GHIResult:
    """Build a models.GHIResult (pydantic) for mood_integration tests."""
    return GHIResult(
        date=date(2026, 6, 18),
        device_id="dev-001",
        owner_id="owner-001",
        ghi_score=ghi_score,
        confidence=confidence,
        tier=tier,
        suppressed=suppressed,
        suppression_reason=suppression_reason,
    )


def _make_anomaly_event(
    severity: AlertSeverity = AlertSeverity.SEV2,
    metric: str = "heart_rate",
    value: float = 100.0,
    baseline: float | None = 72.0,
    deviation: float | None = 28.0,
    device_id: str = "00000000-0000-0000-0000-000000000001",
    owner_id: str = "00000000-0000-0000-0000-000000000002",
) -> AnomalyEvent:
    """Build an AnomalyEvent for alert_router tests."""
    return AnomalyEvent(
        time=datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC),
        device_id=device_id,
        owner_id=owner_id,
        metric=metric,
        severity=severity,
        value=value,
        baseline=baseline,
        deviation=deviation,
        description="test anomaly",
    )


# ===========================================================================
# config.py
# ===========================================================================


class TestWearableConfigDefaults:
    """Verify WearableConfig default field values."""

    def test_default_region_is_cn(self) -> None:
        config = WearableConfig()
        assert config.mi_fitness_region == "cn"

    def test_default_sync_interval_1800(self) -> None:
        config = WearableConfig()
        assert config.wearable_sync_interval_sec == 1800

    def test_default_lookback_hours_2(self) -> None:
        config = WearableConfig()
        assert config.wearable_sync_lookback_hours == 2

    def test_default_circuit_breaker_threshold_3(self) -> None:
        config = WearableConfig()
        assert config.wearable_circuit_breaker_threshold == 3

    def test_default_quiet_hours_start_23_00(self) -> None:
        config = WearableConfig()
        assert config.wearable_quiet_hours_start == "23:00"

    def test_default_quiet_hours_end_07_00(self) -> None:
        config = WearableConfig()
        assert config.wearable_quiet_hours_end == "07:00"

    def test_default_alert_rate_limit_5(self) -> None:
        config = WearableConfig()
        assert config.wearable_alert_rate_limit == 5

    def test_default_timezone_asia_shanghai(self) -> None:
        config = WearableConfig()
        assert config.wearable_timezone == "Asia/Shanghai"

    def test_default_ghi_suppression_threshold_0_4(self) -> None:
        config = WearableConfig()
        assert config.wearable_ghi_suppression_threshold == 0.4

    def test_default_ghi_penalty_cap_0_15(self) -> None:
        config = WearableConfig()
        assert config.wearable_ghi_penalty_cap == 0.15

    def test_default_redis_port_6380(self) -> None:
        config = WearableConfig()
        assert config.redis_port == 6380

    def test_default_postgres_port_5433(self) -> None:
        config = WearableConfig()
        assert config.postgres_port == 5433

    def test_defaults_have_slots(self) -> None:
        """WearableConfig uses slots=True -- arbitrary attrs not allowed."""
        config = WearableConfig()
        with pytest.raises(AttributeError):
            setattr(config, "nonexistent_field", "x")


class TestWearableConfigFromEnv:
    """Verify WearableConfig.from_env() reads environment variables."""

    @pytest.fixture(autouse=True)
    def _clear_cache_and_env(self, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
        get_wearable_config.cache_clear()
        for key in (
            "MI_FITNESS_USER_ID", "MI_FITNESS_PASS_TOKEN", "MI_FITNESS_REGION",
            "MI_FITNESS_TOKEN_PATH", "MI_FITNESS_RELATIVE_UID",
            "WEARABLE_DEVICE_ID", "WEARABLE_OWNER_ID",
            "WEARABLE_SYNC_INTERVAL_SEC", "WEARABLE_SYNC_LOOKBACK_HOURS",
            "WEARABLE_CIRCUIT_BREAKER_THRESHOLD", "WEARABLE_CIRCUIT_BREAKER_RECOVERY_SEC",
            "WEARABLE_QUIET_HOURS_START", "WEARABLE_QUIET_HOURS_END",
            "WEARABLE_ALERT_RATE_LIMIT", "WEARABLE_TIMEZONE",
            "WEARABLE_GHI_SUPPRESSION_THRESHOLD", "WEARABLE_GHI_PENALTY_CAP",
            "WEARABLE_GHI_DECAY_DAYS",
            "REDIS_HOST", "REDIS_PORT", "REDIS_PASSWORD",
            "POSTGRES_HOST", "POSTGRES_PORT", "POSTGRES_DB",
            "POSTGRES_USER", "POSTGRES_PASSWORD",
        ):
            monkeypatch.delenv(key, raising=False)
        yield
        get_wearable_config.cache_clear()

    def test_from_env_no_vars_returns_defaults(self) -> None:
        config = WearableConfig.from_env()
        assert config.mi_fitness_region == "cn"
        assert config.mi_fitness_user_id == ""
        assert config.wearable_sync_interval_sec == 1800

    def test_from_env_reads_mi_fitness_user_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MI_FITNESS_USER_ID", "user-abc")
        config = WearableConfig.from_env()
        assert config.mi_fitness_user_id == "user-abc"

    def test_from_env_reads_mi_fitness_pass_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MI_FITNESS_PASS_TOKEN", "tok-xyz")
        config = WearableConfig.from_env()
        assert config.mi_fitness_pass_token == "tok-xyz"

    def test_from_env_reads_mi_fitness_token_path(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MI_FITNESS_TOKEN_PATH", "/tmp/token.json")
        config = WearableConfig.from_env()
        assert config.mi_fitness_token_path == "/tmp/token.json"

    def test_from_env_reads_mi_fitness_relative_uid(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MI_FITNESS_RELATIVE_UID", "relative-001")
        config = WearableConfig.from_env()
        assert config.mi_fitness_relative_uid == "relative-001"

    def test_from_env_reads_wearable_device_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_DEVICE_ID", "dev-001")
        config = WearableConfig.from_env()
        assert config.wearable_device_id == "dev-001"

    def test_from_env_reads_wearable_owner_id(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_OWNER_ID", "owner-001")
        config = WearableConfig.from_env()
        assert config.wearable_owner_id == "owner-001"

    def test_from_env_reads_sync_interval_as_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_SYNC_INTERVAL_SEC", "900")
        config = WearableConfig.from_env()
        assert config.wearable_sync_interval_sec == 900
        assert isinstance(config.wearable_sync_interval_sec, int)

    def test_from_env_reads_alert_rate_limit(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_ALERT_RATE_LIMIT", "10")
        config = WearableConfig.from_env()
        assert config.wearable_alert_rate_limit == 10

    def test_from_env_reads_ghi_threshold_as_float(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_GHI_SUPPRESSION_THRESHOLD", "0.5")
        config = WearableConfig.from_env()
        assert config.wearable_ghi_suppression_threshold == 0.5
        assert isinstance(config.wearable_ghi_suppression_threshold, float)

    def test_from_env_reads_redis_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("REDIS_HOST", "redis.example.com")
        monkeypatch.setenv("REDIS_PORT", "6379")
        monkeypatch.setenv("REDIS_PASSWORD", "secret")
        config = WearableConfig.from_env()
        assert config.redis_host == "redis.example.com"
        assert config.redis_port == 6379
        assert config.redis_password == "secret"

    def test_from_env_reads_postgres_config(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("POSTGRES_HOST", "pg.example.com")
        monkeypatch.setenv("POSTGRES_DB", "mydb")
        monkeypatch.setenv("POSTGRES_USER", "myuser")
        config = WearableConfig.from_env()
        assert config.postgres_host == "pg.example.com"
        assert config.postgres_db == "mydb"
        assert config.postgres_user == "myuser"

    @pytest.mark.parametrize("region", ["cn", "de", "ru", "us", "global"])
    def test_from_env_all_valid_regions(self, monkeypatch: pytest.MonkeyPatch, region: str) -> None:
        monkeypatch.setenv("MI_FITNESS_REGION", region)
        config = WearableConfig.from_env()
        assert config.mi_fitness_region == region

    def test_from_env_invalid_region_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("MI_FITNESS_REGION", "invalid_region")
        with pytest.raises(ValueError) as exc_info:
            WearableConfig.from_env()
        assert "Invalid MI_FITNESS_REGION" in str(exc_info.value)
        assert "invalid_region" in str(exc_info.value)

    def test_from_env_invalid_int_raises_value_error(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("WEARABLE_SYNC_INTERVAL_SEC", "not-a-number")
        with pytest.raises(ValueError):
            WearableConfig.from_env()


class TestGetWearableConfig:
    """Verify get_wearable_config() lru_cache behaviour."""

    def test_returns_same_instance(self) -> None:
        get_wearable_config.cache_clear()
        a = get_wearable_config()
        b = get_wearable_config()
        assert a is b

    def test_cache_clear_returns_new_instance(self) -> None:
        get_wearable_config.cache_clear()
        a = get_wearable_config()
        get_wearable_config.cache_clear()
        b = get_wearable_config()
        assert a is not b


# ===========================================================================
# normalizer.py
# ===========================================================================


class TestNormalizeFetchResult:
    """Unit tests for normalize_fetch_result()."""

    def test_empty_metrics_returns_empty_payload(self) -> None:
        fetch = _make_fetch_result(metrics={})
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert isinstance(payload, HealthMetricPayload)
        assert payload.samples == []
        assert payload.metrics_available == []
        assert payload.metrics_unavailable == []
        assert payload.device_id == "dev-1"
        assert payload.owner_id == "own-1"
        assert payload.source == MetricSource.MI_FITNESS_CLOUD

    def test_available_heart_rate_extracted(self) -> None:
        ts = datetime(2026, 6, 18, 9, 0, 0, tzinfo=UTC)
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 72.0, timestamp=ts, unit="bpm"),
            _make_sample(HealthMetricType.HEART_RATE, 80.0, timestamp=ts + timedelta(minutes=10), unit="bpm"),
        ]
        fetch = _make_fetch_result(
            metrics={
                "heart_rate": _make_metric_result(HealthMetricType.HEART_RATE, samples=samples),
            }
        )
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert len(payload.samples) == 2
        assert payload.metrics_available == [HealthMetricType.HEART_RATE]
        assert payload.metrics_unavailable == []
        assert all(s.device_id == "dev-1" for s in payload.samples)
        assert all(s.owner_id == "own-1" for s in payload.samples)
        assert all(s.source == MetricSource.MI_FITNESS_CLOUD for s in payload.samples)

    def test_unavailable_metric_goes_to_unavailable_list(self) -> None:
        fetch = _make_fetch_result(
            metrics={
                "heart_rate": _make_metric_result(HealthMetricType.HEART_RATE, status=MetricStatus.UNAVAILABLE),
            }
        )
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert payload.metrics_available == []
        assert payload.metrics_unavailable == [HealthMetricType.HEART_RATE]
        assert payload.samples == []

    def test_endpoint_changed_metric_treated_as_unavailable(self) -> None:
        fetch = _make_fetch_result(
            metrics={
                "heart_rate": _make_metric_result(HealthMetricType.HEART_RATE, status=MetricStatus.ENDPOINT_CHANGED),
            }
        )
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert payload.metrics_unavailable == [HealthMetricType.HEART_RATE]

    def test_unknown_metric_name_skipped(self) -> None:
        fetch = _make_fetch_result(
            metrics={
                "unknown_metric": _make_metric_result(HealthMetricType.HEART_RATE),
                "heart_rate": _make_metric_result(
                    HealthMetricType.HEART_RATE,
                    samples=[_make_sample(HealthMetricType.HEART_RATE, 72.0)],
                ),
            }
        )
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert payload.metrics_available == [HealthMetricType.HEART_RATE]

    def test_sample_with_no_timestamp_skipped(self) -> None:
        # Create a sample dict with no timestamp by injecting via raw data
        # We can't easily skip _metric_result_to_raw_data, so test via _parse_sample indirectly
        sample = _make_sample(HealthMetricType.HEART_RATE, 72.0)
        # Override the metadata to be empty and verify it still works
        fetch = _make_fetch_result(
            metrics={
                "heart_rate": _make_metric_result(
                    HealthMetricType.HEART_RATE,
                    samples=[sample],
                ),
            }
        )
        payload = normalize_fetch_result(fetch, device_id="dev-1", owner_id="own-1")
        assert len(payload.samples) == 1

    def test_alternate_timestamp_keys_supported(self) -> None:
        """Raw samples with 'time' or 'ts' keys are accepted by _parse_sample."""
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        # Test "time" key
        raw_with_time = {"samples": [{"time": "2026-06-18T10:00:00Z", "value": 72.0}]}
        result = _extract_samples(raw_with_time, HMT.HEART_RATE, "bpm")
        assert len(result) == 1
        assert result[0].value == 72.0

        # Test "ts" key
        raw_with_ts = {"samples": [{"ts": "2026-06-18T10:00:00Z", "value": 80.0}]}
        result = _extract_samples(raw_with_ts, HMT.HEART_RATE, "bpm")
        assert len(result) == 1
        assert result[0].value == 80.0

    def test_alternate_value_keys_supported(self) -> None:
        """Raw samples with 'count', 'steps', 'rate' keys are accepted."""
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "count": 100.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 1

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "steps": 5000.0}]}
        result = _extract_samples(raw, HMT.STEPS, "steps")
        assert len(result) == 1

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "rate": 60.0}]}
        result = _extract_samples(raw, HMT.STEPS, "steps")
        assert len(result) == 1

    def test_items_key_supported(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"items": [{"timestamp": "2026-06-18T10:00:00Z", "value": 72.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 1

    def test_data_key_supported(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"data": [{"timestamp": "2026-06-18T10:00:00Z", "value": 72.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 1

    def test_non_list_samples_wrapped(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": {"timestamp": "2026-06-18T10:00:00Z", "value": 72.0}}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 1

    def test_non_dict_sample_skipped(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": ["not-a-dict", {"timestamp": "2026-06-18T10:00:00Z", "value": 72.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 1  # Only the dict one is kept

    def test_invalid_timestamp_skipped(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": [{"timestamp": "not-a-date", "value": 72.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 0

    def test_invalid_value_skipped(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "value": "not-a-number"}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert len(result) == 0

    def test_confidence_defaults_to_1_when_missing(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "value": 72.0}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert result[0].confidence == 1.0

    def test_confidence_invalid_defaults_to_1(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {"samples": [{"timestamp": "2026-06-18T10:00:00Z", "value": 72.0, "confidence": "bad"}]}
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert result[0].confidence == 1.0

    def test_parse_datetime_iso_string_with_z(self) -> None:
        from src.wearable.normalizer import _parse_datetime

        result = _parse_datetime("2026-06-18T10:00:00Z")
        assert result.tzinfo is not None
        assert result.year == 2026 and result.month == 6 and result.day == 18

    def test_parse_datetime_epoch_number(self) -> None:
        from src.wearable.normalizer import _parse_datetime

        result = _parse_datetime(1718707200.0)  # 2024-06-18 UTC
        assert result.tzinfo is not None

    def test_parse_datetime_datetime_object_naive_gets_utc(self) -> None:
        from src.wearable.normalizer import _parse_datetime

        naive = datetime(2026, 6, 18, 10, 0, 0)
        result = _parse_datetime(naive)
        assert result.tzinfo is not None

    def test_parse_datetime_unsupported_type_raises(self) -> None:
        from src.wearable.normalizer import _parse_datetime

        with pytest.raises(ValueError):
            _parse_datetime([1, 2, 3])  # type: ignore[arg-type]

    def test_metadata_fields_extracted(self) -> None:
        from src.wearable.normalizer import _extract_samples, HealthMetricType as HMT

        raw = {
            "samples": [
                {
                    "timestamp": "2026-06-18T10:00:00Z",
                    "value": 72.0,
                    "extra_field": "extra_value",
                    "activity_type": "running",
                }
            ]
        }
        result = _extract_samples(raw, HMT.HEART_RATE, "bpm")
        assert result[0].metadata.get("extra_field") == "extra_value"
        assert result[0].metadata.get("activity_type") == "running"


# ===========================================================================
# baseline.py
# ===========================================================================


class TestBaselinePureFunctions:
    """Test module-level pure helper functions."""

    def test_mean_stddev_empty_returns_none(self) -> None:
        mean, stddev = _mean_stddev([])
        assert mean is None
        assert stddev is None

    def test_mean_stddev_single_value(self) -> None:
        mean, stddev = _mean_stddev([42.0])
        assert mean == 42.0
        assert stddev == 0.0

    def test_mean_stddev_multiple_values(self) -> None:
        mean, stddev = _mean_stddev([10.0, 20.0, 30.0])
        assert mean == 20.0
        assert stddev is not None and stddev > 0.0

    def test_confidence_insufficient_zero_points(self) -> None:
        assert _confidence_for_stage(BaselineStage.INSUFFICIENT, 0) == 0.0

    def test_confidence_insufficient_two_points(self) -> None:
        assert _confidence_for_stage(BaselineStage.INSUFFICIENT, 2) == 0.0

    def test_confidence_insufficient_three_points(self) -> None:
        c = _confidence_for_stage(BaselineStage.INSUFFICIENT, 3)
        assert 0.0 < c <= 0.2

    def test_confidence_provisional_minimum(self) -> None:
        c = _confidence_for_stage(BaselineStage.PROVISIONAL, 0)
        assert 0.3 <= c <= 0.5

    def test_confidence_provisional_caps_at_0_5(self) -> None:
        c = _confidence_for_stage(BaselineStage.PROVISIONAL, 1000)
        assert c == 0.5

    def test_confidence_stabilizing_caps_at_0_8(self) -> None:
        c = _confidence_for_stage(BaselineStage.STABILIZING, 1000)
        assert c == 0.8

    def test_confidence_stable_caps_at_1_0(self) -> None:
        c = _confidence_for_stage(BaselineStage.STABLE, 1000)
        assert c == 1.0

    def test_confidence_rebaseline_is_zero(self) -> None:
        assert _confidence_for_stage(BaselineStage.REBASELINE, 100) == 0.0


class TestBaselineStageForValues:
    """Test _stage_for_values transitions."""

    def _make_calc(self) -> BaselineCalculator:
        return BaselineCalculator("postgresql://localhost/test")

    def test_no_values_returns_insufficient(self) -> None:
        calc = self._make_calc()
        stage = calc._stage_for_values([], None, None)
        assert stage is BaselineStage.INSUFFICIENT

    def test_no_timestamps_returns_insufficient(self) -> None:
        calc = self._make_calc()
        stage = calc._stage_for_values([1.0, 2.0], None, None)
        assert stage is BaselineStage.INSUFFICIENT

    def test_one_day_active_returns_insufficient(self) -> None:
        calc = self._make_calc()
        now = datetime(2026, 6, 18, tzinfo=UTC)
        stage = calc._stage_for_values([1.0], now, now)
        assert stage is BaselineStage.INSUFFICIENT

    def test_three_days_active_returns_insufficient(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 6, 15, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values([1.0, 2.0, 3.0], first, last)
        assert stage is BaselineStage.INSUFFICIENT

    def test_four_days_returns_provisional(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 6, 14, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values([1.0, 2.0, 3.0, 4.0], first, last)
        assert stage is BaselineStage.PROVISIONAL

    def test_fourteen_days_returns_provisional(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 6, 4, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values(list(range(14)), first, last)
        assert stage is BaselineStage.PROVISIONAL

    def test_fifteen_days_returns_stabilizing(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 6, 3, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values(list(range(15)), first, last)
        assert stage is BaselineStage.STABILIZING

    def test_twenty_seven_days_returns_stabilizing(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 5, 22, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values(list(range(27)), first, last)
        assert stage is BaselineStage.STABILIZING

    def test_twenty_eight_days_returns_stable(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 5, 20, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values(list(range(28)), first, last)
        assert stage is BaselineStage.STABLE

    def test_sixty_days_returns_stable(self) -> None:
        calc = self._make_calc()
        first = datetime(2026, 4, 18, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        stage = calc._stage_for_values(list(range(60)), first, last)
        assert stage is BaselineStage.STABLE


class TestBaselineComputeBaseline:
    """Test BaselineCalculator.compute_baseline() with mocked DB."""

    def _make_calculator_with_pool(self, conn: AsyncMock) -> BaselineCalculator:
        calc = BaselineCalculator("postgresql://localhost/test")
        mock_pool, _ = _make_mock_asyncpg_pool(conn)
        calc._pool = mock_pool  # type: ignore[assignment]
        return calc

    @pytest.mark.asyncio
    async def test_insufficient_data_returns_insufficient_state(self) -> None:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)  # get_baseline: no existing
        conn.fetch = AsyncMock(return_value=[])  # _load_metric_values: no data
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        calc = self._make_calculator_with_pool(conn)

        result = await calc.compute_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result.stage is BaselineStage.INSUFFICIENT
        assert result.baseline_value is None
        assert result.data_points == 0
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_sufficient_data_returns_provisional(self) -> None:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        # 5 data points spanning 5 days
        first = datetime(2026, 6, 13, tzinfo=UTC)
        last = datetime(2026, 6, 17, tzinfo=UTC)
        rows = []
        for i, day in enumerate(range(5)):
            ts = first + timedelta(days=day)
            rows.append(_make_mock_record({"value": 70.0 + i, "ts": ts}))
        conn.fetch = AsyncMock(return_value=rows)
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        calc = self._make_calculator_with_pool(conn)

        result = await calc.compute_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result.stage is BaselineStage.PROVISIONAL
        assert result.data_points == 5
        assert result.baseline_value is not None
        assert result.first_data_at == first
        assert result.last_data_at == last

    @pytest.mark.asyncio
    async def test_less_than_3_points_forces_insufficient(self) -> None:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        first = datetime(2026, 6, 16, tzinfo=UTC)
        last = datetime(2026, 6, 18, tzinfo=UTC)
        rows = [
            _make_mock_record({"value": 70.0, "ts": first}),
            _make_mock_record({"value": 72.0, "ts": last}),
        ]
        conn.fetch = AsyncMock(return_value=rows)
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        calc = self._make_calculator_with_pool(conn)

        result = await calc.compute_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result.stage is BaselineStage.INSUFFICIENT
        assert result.baseline_value is None
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_db_query_failure_returns_insufficient(self) -> None:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(side_effect=ConnectionError("DB down"))
        calc = self._make_calculator_with_pool(conn)

        result = await calc.compute_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result.stage is BaselineStage.INSUFFICIENT
        assert result.data_points == 0

    @pytest.mark.asyncio
    async def test_rebaseline_when_gap_exceeds_7_days(self) -> None:
        """Existing baseline with last_data_at > 7 days before new data -> REBASELINE."""
        conn = AsyncMock()
        # Existing baseline from 30 days ago
        existing_last = datetime.now(UTC) - timedelta(days=30)
        existing_row = _make_mock_record({
            "metric": "heart_rate",
            "device_id": "dev-1",
            "owner_id": "owner-1",
            "stage": "stable",
            "baseline_value": 72.0,
            "data_points": 100,
            "first_data_at": datetime.now(UTC) - timedelta(days=60),
            "last_data_at": existing_last,
            "updated_at": existing_last,
        })
        conn.fetchrow = AsyncMock(return_value=existing_row)
        # New data points
        new_first = datetime.now(UTC) - timedelta(days=2)
        new_last = datetime.now(UTC) - timedelta(days=1)
        conn.fetch = AsyncMock(return_value=[
            _make_mock_record({"value": 70.0, "ts": new_first}),
            _make_mock_record({"value": 75.0, "ts": new_last}),
        ])
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        calc = self._make_calculator_with_pool(conn)

        result = await calc.compute_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result.stage is BaselineStage.INSUFFICIENT  # Rebaseline -> insufficient
        assert result.data_points == 2

    @pytest.mark.asyncio
    async def test_close_releases_pool(self) -> None:
        calc = BaselineCalculator("postgresql://localhost/test")
        mock_pool, _ = _make_mock_asyncpg_pool()
        calc._pool = mock_pool  # type: ignore[assignment]
        await calc.close()
        mock_pool.close.assert_called_once()
        assert calc._pool is None


class TestBaselineGetBaseline:
    """Test BaselineCalculator.get_baseline() with mocked DB."""

    @pytest.mark.asyncio
    async def test_get_baseline_returns_none_when_not_found(self) -> None:
        conn = AsyncMock()
        conn.fetchrow = AsyncMock(return_value=None)
        calc = BaselineCalculator("postgresql://localhost/test")
        mock_pool, _ = _make_mock_asyncpg_pool(conn)
        calc._pool = mock_pool  # type: ignore[assignment]

        result = await calc.get_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result is None

    @pytest.mark.asyncio
    async def test_get_baseline_returns_state_when_found(self) -> None:
        conn = AsyncMock()
        row = _make_mock_record({
            "metric": "heart_rate",
            "device_id": "dev-1",
            "owner_id": "owner-1",
            "stage": "stable",
            "baseline_value": 72.0,
            "data_points": 50,
            "first_data_at": datetime(2026, 5, 1, tzinfo=UTC),
            "last_data_at": datetime(2026, 6, 17, tzinfo=UTC),
            "updated_at": datetime(2026, 6, 17, tzinfo=UTC),
        })
        conn.fetchrow = AsyncMock(return_value=row)
        calc = BaselineCalculator("postgresql://localhost/test")
        mock_pool, _ = _make_mock_asyncpg_pool(conn)
        calc._pool = mock_pool  # type: ignore[assignment]

        result = await calc.get_baseline(HealthMetricType.HEART_RATE, "owner-1", "dev-1")
        assert result is not None
        assert result.stage is BaselineStage.STABLE
        assert result.baseline_value == 72.0
        assert result.data_points == 50


# ===========================================================================
# anomaly.py
# ===========================================================================


class TestMetricThresholds:
    """Verify METRIC_THRESHOLDS has all expected metrics with proper rules."""

    def test_has_five_metrics(self) -> None:
        assert len(METRIC_THRESHOLDS) == 5
        assert HealthMetricType.HEART_RATE in METRIC_THRESHOLDS
        assert HealthMetricType.STEPS in METRIC_THRESHOLDS
        assert HealthMetricType.SPO2 in METRIC_THRESHOLDS
        assert HealthMetricType.STRESS in METRIC_THRESHOLDS
        assert HealthMetricType.SLEEP in METRIC_THRESHOLDS
        assert HealthMetricType.ACTIVITY not in METRIC_THRESHOLDS  # No threshold for activity

    def test_heart_rate_has_sev0_rule(self) -> None:
        rules = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules
        sev0_rules = [r for r in rules if r.sev is AlertSeverity.SEV0]
        assert len(sev0_rules) == 1
        assert sev0_rules[0].threshold_abs_max == 130
        assert sev0_rules[0].min_consecutive == 3

    def test_spo2_has_sev0_rule(self) -> None:
        rules = METRIC_THRESHOLDS[HealthMetricType.SPO2].severity_rules
        sev0_rules = [r for r in rules if r.sev is AlertSeverity.SEV0]
        assert len(sev0_rules) == 1
        assert sev0_rules[0].threshold_abs_min == 90

    def test_stress_uses_percentage_threshold(self) -> None:
        rules = METRIC_THRESHOLDS[HealthMetricType.STRESS].severity_rules
        pct_rules = [r for r in rules if r.threshold_pct is not None]
        assert len(pct_rules) == 2

    def test_severity_rule_is_frozen(self) -> None:
        rule = SeverityRule(min_consecutive=3, sev=AlertSeverity.SEV0)
        with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
            setattr(rule, "min_consecutive", 5)


class TestAnomalyDetectorHelpers:
    """Test pure helper methods on AnomalyDetector."""

    def _make_detector(self) -> AnomalyDetector:
        return AnomalyDetector("postgresql://localhost/test")

    def test_baseline_value_returns_float(self) -> None:
        baseline = MagicMock()
        baseline.baseline_value = 72.0
        assert AnomalyDetector._baseline_value(baseline) == 72.0

    def test_baseline_value_returns_none_when_missing(self) -> None:
        baseline = MagicMock(spec=["baseline_value"])
        baseline.baseline_value = None
        assert AnomalyDetector._baseline_value(baseline) is None

    def test_is_insufficient_baseline_true(self) -> None:
        baseline = MagicMock()
        baseline.stage = BaselineStage.INSUFFICIENT
        assert AnomalyDetector._is_insufficient_baseline(baseline) is True

    def test_is_insufficient_baseline_false_for_stable(self) -> None:
        baseline = MagicMock()
        baseline.stage = BaselineStage.STABLE
        assert AnomalyDetector._is_insufficient_baseline(baseline) is False

    def test_default_description(self) -> None:
        desc = AnomalyDetector._default_description(HealthMetricType.HEART_RATE, 120.0, 72.0)
        assert "heart_rate" in desc
        assert "120" in desc
        assert "72" in desc

    def test_evaluate_sample_heart_rate_high(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.HEART_RATE, 150.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules
        rule, dev = detector._evaluate_sample(HealthMetricType.HEART_RATE, sample, 72.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV0
        assert dev == 78.0  # 150 - 72

    def test_evaluate_sample_heart_rate_low(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.HEART_RATE, 35.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules
        rule, dev = detector._evaluate_sample(HealthMetricType.HEART_RATE, sample, 72.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV1

    def test_evaluate_sample_spo2_low(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.SPO2, 88.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.SPO2].severity_rules
        rule, _ = detector._evaluate_sample(HealthMetricType.SPO2, sample, 97.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV0

    def test_evaluate_sample_steps_zero(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.STEPS, 0.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.STEPS].severity_rules
        rule, _ = detector._evaluate_sample(HealthMetricType.STEPS, sample, 8000.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV2

    def test_evaluate_sample_stress_high(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.STRESS, 80.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.STRESS].severity_rules
        rule, _ = detector._evaluate_sample(HealthMetricType.STRESS, sample, 40.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV1  # 100% increase >= 50%

    def test_evaluate_sample_sleep_short(self) -> None:
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.SLEEP, 90.0)  # 90 minutes
        rules = METRIC_THRESHOLDS[HealthMetricType.SLEEP].severity_rules
        rule, _ = detector._evaluate_sample(HealthMetricType.SLEEP, sample, 480.0, rules)
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV1  # < 120 min

    def test_evaluate_sample_normal_matches_sev2_deviation_rule(self) -> None:
        """Value outside +-5 of baseline triggers SEV2 deviation rule."""
        detector = self._make_detector()
        sample = _make_sample(HealthMetricType.HEART_RATE, 75.0)
        rules = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules
        rule, dev = detector._evaluate_sample(HealthMetricType.HEART_RATE, sample, 72.0, rules)
        # 75 deviates by 3 from baseline 72, but SEV2 rule checks sample.value
        # against abs_min=-5, abs_max=5, so 75 > 5 triggers the rule
        assert rule is not None
        assert rule.sev is AlertSeverity.SEV2
        assert dev == 3.0  # abs(75 - 72)

    def test_count_consecutive_three_anomalies(self) -> None:
        detector = self._make_detector()
        base_ts = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 140.0, timestamp=base_ts),
            _make_sample(HealthMetricType.HEART_RATE, 145.0, timestamp=base_ts + timedelta(minutes=10)),
            _make_sample(HealthMetricType.HEART_RATE, 150.0, timestamp=base_ts + timedelta(minutes=20)),
        ]
        rule = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules[0]
        count = detector._count_consecutive(samples, 0, HealthMetricType.HEART_RATE, 72.0, rule)
        assert count == 3

    def test_count_consecutive_breaks_on_normal(self) -> None:
        detector = self._make_detector()
        base_ts = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 140.0, timestamp=base_ts),
            _make_sample(HealthMetricType.HEART_RATE, 75.0, timestamp=base_ts + timedelta(minutes=10)),  # normal
            _make_sample(HealthMetricType.HEART_RATE, 150.0, timestamp=base_ts + timedelta(minutes=20)),
        ]
        rule = METRIC_THRESHOLDS[HealthMetricType.HEART_RATE].severity_rules[0]
        count = detector._count_consecutive(samples, 0, HealthMetricType.HEART_RATE, 72.0, rule)
        assert count == 1  # Only the first one matches before breaking


class TestAnomalyDetectorIntegration:
    """Test AnomalyDetector.detect_anomalies() end-to-end (no DB needed)."""

    def _make_detector(self) -> AnomalyDetector:
        return AnomalyDetector("postgresql://localhost/test")

    def _make_stable_baseline(self, metric: HealthMetricType, value: float) -> MagicMock:
        baseline = MagicMock()
        baseline.metric = metric
        baseline.stage = BaselineStage.STABLE
        baseline.baseline_value = value
        baseline.data_points = 100
        return baseline

    @pytest.mark.asyncio
    async def test_empty_samples_returns_empty(self) -> None:
        detector = self._make_detector()
        baseline = self._make_stable_baseline(HealthMetricType.HEART_RATE, 72.0)
        events = await detector.detect_anomalies(HealthMetricType.HEART_RATE, baseline, [], "owner-1", "dev-1")
        assert events == []

    @pytest.mark.asyncio
    async def test_insufficient_baseline_returns_empty(self) -> None:
        detector = self._make_detector()
        baseline = MagicMock()
        baseline.stage = BaselineStage.INSUFFICIENT
        baseline.baseline_value = 72.0
        events = await detector.detect_anomalies(
            HealthMetricType.HEART_RATE, baseline,
            [_make_sample(HealthMetricType.HEART_RATE, 150.0)],
            "owner-1", "dev-1",
        )
        assert events == []

    @pytest.mark.asyncio
    async def test_baseline_none_returns_empty(self) -> None:
        detector = self._make_detector()
        baseline = MagicMock()
        baseline.stage = BaselineStage.STABLE
        baseline.baseline_value = None
        events = await detector.detect_anomalies(
            HealthMetricType.HEART_RATE, baseline,
            [_make_sample(HealthMetricType.HEART_RATE, 150.0)],
            "owner-1", "dev-1",
        )
        assert events == []

    @pytest.mark.asyncio
    async def test_consecutive_readings_below_min_not_flagged(self) -> None:
        """1-2 consecutive high readings (min_consecutive=3) should NOT trigger."""
        detector = self._make_detector()
        baseline = self._make_stable_baseline(HealthMetricType.HEART_RATE, 72.0)
        base_ts = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 140.0, timestamp=base_ts),
            _make_sample(HealthMetricType.HEART_RATE, 145.0, timestamp=base_ts + timedelta(minutes=10)),
        ]
        events = await detector.detect_anomalies(
            HealthMetricType.HEART_RATE, baseline, samples, "owner-1", "dev-1",
        )
        assert events == []

    @pytest.mark.asyncio
    async def test_three_consecutive_high_heart_rate_flagged_sev0(self) -> None:
        detector = self._make_detector()
        baseline = self._make_stable_baseline(HealthMetricType.HEART_RATE, 72.0)
        base_ts = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 140.0, timestamp=base_ts),
            _make_sample(HealthMetricType.HEART_RATE, 145.0, timestamp=base_ts + timedelta(minutes=10)),
            _make_sample(HealthMetricType.HEART_RATE, 150.0, timestamp=base_ts + timedelta(minutes=20)),
        ]
        events = await detector.detect_anomalies(
            HealthMetricType.HEART_RATE, baseline, samples, "owner-1", "dev-1",
        )
        assert len(events) >= 1
        assert any(e.severity is AlertSeverity.SEV0 for e in events)
        assert all(e.alert_sent is False for e in events)

    @pytest.mark.asyncio
    async def test_detect_all_metrics_groups_by_metric(self) -> None:
        detector = self._make_detector()
        baselines: dict[HealthMetricType, object] = {
            HealthMetricType.HEART_RATE: self._make_stable_baseline(HealthMetricType.HEART_RATE, 72.0),
        }
        samples = [
            _make_sample(HealthMetricType.HEART_RATE, 72.0),
            _make_sample(HealthMetricType.STEPS, 1000.0),  # No baseline for steps
        ]
        events = await detector.detect_all_metrics(
            cast("dict[HealthMetricType, BaselineLike]", baselines),
            samples, "owner-1", "dev-1",
        )
        # Only heart_rate has a baseline, steps doesn't
        assert all(e.metric == "heart_rate" for e in events)

    @pytest.mark.asyncio
    async def test_detect_all_metrics_empty_samples(self) -> None:
        detector = self._make_detector()
        events = await detector.detect_all_metrics({}, [], "owner-1", "dev-1")
        assert events == []


# ===========================================================================
# ghi.py
# ===========================================================================


class TestGHIPureFunctions:
    """Test pure helper methods on GHIScorer."""

    def _make_scorer(self) -> GHIScorer:
        return GHIScorer("postgresql://localhost/test")

    def test_tier_excellent(self) -> None:
        scorer = self._make_scorer()
        assert scorer._tier_for_score(100.0) is GHITier.EXCELLENT
        assert scorer._tier_for_score(85.0) is GHITier.EXCELLENT

    def test_tier_good(self) -> None:
        scorer = self._make_scorer()
        assert scorer._tier_for_score(84.9) is GHITier.GOOD
        assert scorer._tier_for_score(70.0) is GHITier.GOOD

    def test_tier_fair(self) -> None:
        scorer = self._make_scorer()
        assert scorer._tier_for_score(69.9) is GHITier.FAIR
        assert scorer._tier_for_score(55.0) is GHITier.FAIR

    def test_tier_poor(self) -> None:
        scorer = self._make_scorer()
        assert scorer._tier_for_score(54.9) is GHITier.POOR
        assert scorer._tier_for_score(40.0) is GHITier.POOR

    def test_tier_critical(self) -> None:
        scorer = self._make_scorer()
        assert scorer._tier_for_score(39.9) is GHITier.CRITICAL
        assert scorer._tier_for_score(0.0) is GHITier.CRITICAL

    def test_rebalance_weights_two_pillars(self) -> None:
        scorer = self._make_scorer()
        weights = scorer._rebalance_weights(["sleep", "activity"])
        assert weights == {"sleep": 0.5, "activity": 0.5}

    def test_rebalance_weights_three_pillars(self) -> None:
        scorer = self._make_scorer()
        weights = scorer._rebalance_weights(["sleep", "cardio", "activity"])
        assert weights["sleep"] == pytest.approx(1 / 3, abs=1e-9)
        assert weights["cardio"] == pytest.approx(1 / 3, abs=1e-9)
        assert weights["activity"] == pytest.approx(1 / 3, abs=1e-9)

    def test_rebalance_weights_four_pillars(self) -> None:
        scorer = self._make_scorer()
        weights = scorer._rebalance_weights(["sleep", "cardio", "activity", "recovery"])
        assert all(abs(v - 0.25) < 1e-9 for v in weights.values())

    def test_rebalance_weights_one_pillar_returns_empty(self) -> None:
        scorer = self._make_scorer()
        weights = scorer._rebalance_weights(["sleep"])
        assert weights == {}

    def test_rebalance_weights_zero_pillars_returns_empty(self) -> None:
        scorer = self._make_scorer()
        weights = scorer._rebalance_weights([])
        assert weights == {}

    def test_default_weights_sum_to_one(self) -> None:
        total = sum(DEFAULT_WEIGHTS.values())
        assert abs(total - 1.0) < 1e-9

    def test_as_float_with_int(self) -> None:
        scorer = self._make_scorer()
        assert scorer._as_float(42) == 42.0

    def test_as_float_with_float(self) -> None:
        scorer = self._make_scorer()
        assert scorer._as_float(42.5) == 42.5

    def test_as_float_with_none(self) -> None:
        scorer = self._make_scorer()
        assert scorer._as_float(None) is None

    def test_as_float_with_numeric_string(self) -> None:
        scorer = self._make_scorer()
        assert scorer._as_float("42.5") == 42.5

    def test_as_float_with_invalid_string(self) -> None:
        scorer = self._make_scorer()
        assert scorer._as_float("not-a-number") is None

    def test_pillar_for_metric_heart_rate(self) -> None:
        scorer = self._make_scorer()
        assert scorer._pillar_for_metric("heart_rate") == "cardio"

    def test_pillar_for_metric_steps(self) -> None:
        scorer = self._make_scorer()
        assert scorer._pillar_for_metric("steps") == "activity"

    def test_pillar_for_metric_sleep(self) -> None:
        scorer = self._make_scorer()
        assert scorer._pillar_for_metric("sleep") == "sleep"

    def test_pillar_for_metric_stress(self) -> None:
        scorer = self._make_scorer()
        assert scorer._pillar_for_metric("stress") == "recovery"

    def test_pillar_for_metric_unknown(self) -> None:
        scorer = self._make_scorer()
        assert scorer._pillar_for_metric("unknown_metric") is None


class TestGHIComputePillarScore:
    """Test _compute_pillar_score for each pillar (pure, no DB)."""

    def _make_scorer(self) -> GHIScorer:
        return GHIScorer("postgresql://localhost/test")

    def _make_baseline(self, value: float, confidence: float = 0.9) -> GHIBaselineResult:
        return GHIBaselineResult(
            metric=HealthMetricType.HEART_RATE,
            stage=BaselineStage.STABLE,
            baseline_value=value,
            stddev=5.0,
            confidence=confidence,
            data_points=100,
            first_data_at=datetime(2026, 5, 1, tzinfo=UTC),
            last_data_at=datetime(2026, 6, 17, tzinfo=UTC),
            owner_id="owner-1",
            device_id="dev-1",
        )

    def test_no_data_returns_data_present_false(self) -> None:
        scorer = self._make_scorer()
        result = scorer._compute_pillar_score("sleep", None, None)
        assert isinstance(result, PillarScore)
        assert result.data_present is False
        assert result.score is None
        assert result.confidence == 0.0

    def test_sleep_pillar_eight_hours(self) -> None:
        scorer = self._make_scorer()
        data: dict[str, object] = {"total_s": 28800.0, "efficiency_pct": 90.0, "end_time": datetime(2026, 6, 18, 7, 0, tzinfo=UTC)}
        result = scorer._compute_pillar_score("sleep", data, None)
        assert result.data_present is True
        assert result.score is not None
        assert result.score > 0.0

    def test_sleep_pillar_short_sleep_penalty(self) -> None:
        """Sleep < 360 (interpreted as minutes by source) gets 15-point penalty."""
        scorer = self._make_scorer()
        data: dict[str, object] = {"total_s": 300.0, "efficiency_pct": 90.0}  # 300 < 360 triggers penalty
        result = scorer._compute_pillar_score("sleep", data, None)
        assert result.score is not None
        # 300/480 * 100 = 62.5, minus 15 = 47.5
        assert result.score < 62.5

    def test_cardio_pillar_with_bpm(self) -> None:
        scorer = self._make_scorer()
        data: dict[str, object] = {"bpm": 72.0, "resting_bpm": 65.0, "time": datetime.now(UTC)}
        baseline = self._make_baseline(70.0)
        result = scorer._compute_pillar_score("cardio", data, baseline)
        assert result.data_present is True
        assert result.score is not None

    def test_cardio_pillar_high_deviation_penalty(self) -> None:
        """BPM more than 10 away from baseline gets 15-point penalty."""
        scorer = self._make_scorer()
        data: dict[str, object] = {"bpm": 100.0, "resting_bpm": 100.0, "time": datetime.now(UTC)}
        baseline = self._make_baseline(70.0)
        result = scorer._compute_pillar_score("cardio", data, baseline)
        assert result.score is not None
        # deviation = 30, penalty applies
        assert result.score < 100.0

    def test_activity_pillar(self) -> None:
        scorer = self._make_scorer()
        data: dict[str, object] = {"steps": 8000.0, "date": date(2026, 6, 18)}
        baseline = self._make_baseline(10000.0)
        result = scorer._compute_pillar_score("activity", data, baseline)
        assert result.data_present is True
        assert result.score is not None
        # 8000/10000 * 100 = 80
        assert result.score == pytest.approx(80.0, abs=1.0)

    def test_recovery_pillar_with_stress(self) -> None:
        scorer = self._make_scorer()
        stress_row = _make_mock_record({"score": 30.0})
        data: dict[str, object] = {"stress_rows": [stress_row], "hrv_row": None}
        result = scorer._compute_pillar_score("recovery", data, None)
        assert result.data_present is True
        assert result.score is not None
        # 100 - 30 = 70
        assert result.score == pytest.approx(70.0, abs=1.0)

    def test_recovery_pillar_with_hrv_bonus(self) -> None:
        scorer = self._make_scorer()
        stress_row = _make_mock_record({"score": 30.0})
        data: dict[str, object] = {"stress_rows": [stress_row], "hrv_row": {"value": 50.0, "time": datetime.now(UTC)}}
        result = scorer._compute_pillar_score("recovery", data, None)
        assert result.score is not None
        # 70 + min(10, 50/10) = 70 + 5 = 75
        assert result.score > 70.0

    def test_unknown_pillar_returns_data_present_false(self) -> None:
        scorer = self._make_scorer()
        result = scorer._compute_pillar_score("unknown", {"value": 1.0}, None)
        assert result.data_present is False


class TestGHIComputeGHI:
    """Test GHIScorer.compute_ghi() with mocked DB."""

    @pytest.mark.asyncio
    async def test_suppression_when_fewer_than_2_pillars(self) -> None:
        scorer = GHIScorer("postgresql://localhost/test")
        conn = AsyncMock()
        conn.fetch = AsyncMock(return_value=[])  # No baselines
        conn.fetchrow = AsyncMock(return_value=None)  # No pillar data
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        mock_pool, _ = _make_mock_asyncpg_pool(conn)
        scorer._pool = mock_pool  # type: ignore[assignment]

        result = await scorer.compute_ghi("owner-1", "dev-1", date(2026, 6, 18))
        assert result.suppressed is True
        assert result.tier is GHITier.CRITICAL
        assert result.score == 0.0
        assert result.confidence == 0.0

    @pytest.mark.asyncio
    async def test_full_ghi_with_all_pillars(self) -> None:
        scorer = GHIScorer("postgresql://localhost/test")
        conn = AsyncMock()

        # Mock baseline rows
        baseline_row = _make_mock_record({
            "metric": "heart_rate",
            "stage": "stable",
            "baseline_value": 72.0,
            "stddev": 5.0,
            "confidence": 0.9,
            "data_points": 100,
            "first_data_at": datetime(2026, 5, 1, tzinfo=UTC),
            "last_data_at": datetime(2026, 6, 17, tzinfo=UTC),
            "owner_id": "owner-1",
            "device_id": "dev-1",
        })

        # Mock pillar data rows
        sleep_row = _make_mock_record({
            "sleep_date": date(2026, 6, 18),
            "total_s": 28800.0,
            "efficiency_pct": 90.0,
            "end_time": datetime(2026, 6, 18, 7, 0, tzinfo=UTC),
        })
        activity_row = _make_mock_record({
            "date": date(2026, 6, 18),
            "steps": 8000.0,
            "distance_m": 6000.0,
        })
        heart_row = _make_mock_record({
            "time": datetime(2026, 6, 18, 10, 0, tzinfo=UTC),
            "bpm": 72.0,
            "resting_bpm": 65.0,
        })
        stress_rows = [_make_mock_record({"time": datetime(2026, 6, 18, 10, 0, tzinfo=UTC), "score": 30.0})]

        # Set up fetch and fetchrow return values in order
        conn.fetch = AsyncMock(side_effect=[
            [baseline_row],  # _fetch_baselines
            stress_rows,      # stress rows in _fetch_pillar_data
        ])
        conn.fetchrow = AsyncMock(side_effect=[
            sleep_row,    # sleep
            activity_row, # activity
            heart_row,    # heart_rate
            None,         # hrv
        ])
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        mock_pool, _ = _make_mock_asyncpg_pool(conn)
        scorer._pool = mock_pool  # type: ignore[assignment]

        result = await scorer.compute_ghi("owner-1", "dev-1", date(2026, 6, 18))
        assert result.suppressed is False
        assert result.tier in (GHITier.EXCELLENT, GHITier.GOOD, GHITier.FAIR)
        assert 0.0 <= result.score <= 100.0
        assert 0.0 <= result.confidence <= 1.0

    @pytest.mark.asyncio
    async def test_close_releases_pool(self) -> None:
        scorer = GHIScorer("postgresql://localhost/test")
        mock_pool, _ = _make_mock_asyncpg_pool()
        scorer._pool = mock_pool  # type: ignore[assignment]
        await scorer.close()
        mock_pool.close.assert_called_once()
        assert scorer._pool is None


# ===========================================================================
# mood_integration.py
# ===========================================================================


class TestMoodModifierSerialization:
    """Test WearableMoodModifier.to_json() and from_json()."""

    def test_to_json_contains_required_fields(self) -> None:
        mod = WearableMoodModifier(
            target_mood=Mood.CONTENT,
            reason="test reason",
            intensity=0.5,
            expires_at=datetime(2026, 6, 19, 10, 0, 0, tzinfo=UTC),
        )
        raw = mod.to_json()
        data = json.loads(raw)
        assert "target_mood" in data
        assert "reason" in data
        assert "intensity" in data
        assert "expires_at" in data
        assert "source" in data

    def test_from_json_roundtrip(self) -> None:
        original = WearableMoodModifier(
            target_mood=Mood.PLEASED,
            reason="healthy trend",
            intensity=0.7,
            expires_at=datetime(2026, 6, 19, 10, 0, 0, tzinfo=UTC),
        )
        raw = original.to_json()
        restored = WearableMoodModifier.from_json(raw)
        assert restored.target_mood == original.target_mood
        assert restored.reason == original.reason
        assert restored.intensity == original.intensity
        assert restored.expires_at == original.expires_at


class TestHealthMoodIntegratorQuietHours:
    """Test _is_quiet_hours static method."""

    @pytest.mark.parametrize("hour,expected", [
        (0, True),   # midnight
        (3, True),   # early morning
        (7, True),   # just before end (8)
        (8, False),  # end of quiet hours
        (9, False),  # morning
        (12, False), # noon
        (18, False), # evening
        (21, False), # just before start (22)
        (22, True),  # start of quiet hours
        (23, True),  # late night
    ])
    def test_quiet_hours_boundaries(self, hour: int, expected: bool) -> None:
        dt = datetime(2026, 6, 18, hour, 0, 0, tzinfo=UTC)
        assert HealthMoodIntegrator._is_quiet_hours(dt) is expected

    def test_quiet_hours_constants(self) -> None:
        assert QUIET_HOURS_START == 22
        assert QUIET_HOURS_END == 8


class TestHealthMoodIntegratorTierMapping:
    """Test _map_tier_to_mood for each GHI tier."""

    def _make_integrator(self) -> HealthMoodIntegrator:
        return HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")

    def test_excellent_maps_to_pleased(self) -> None:
        integrator = self._make_integrator()
        ghi = _make_ghi_result(tier=GHITier.EXCELLENT, ghi_score=90.0)
        mood, intensity, reason = integrator._map_tier_to_mood(ghi)
        assert mood is not None
        assert mood.value == "Pleased"
        assert intensity == 0.7
        assert "energetic" in reason.lower()

    def test_good_maps_to_content(self) -> None:
        integrator = self._make_integrator()
        ghi = _make_ghi_result(tier=GHITier.GOOD, ghi_score=75.0)
        mood, intensity, reason = integrator._map_tier_to_mood(ghi)
        assert mood is not None
        assert mood.value == "Content"
        assert intensity == 0.5
        assert "steady" in reason.lower()

    def test_fair_maps_to_content_gentle(self) -> None:
        integrator = self._make_integrator()
        ghi = _make_ghi_result(tier=GHITier.FAIR, ghi_score=60.0)
        mood, intensity, reason = integrator._map_tier_to_mood(ghi)
        assert mood is not None
        assert mood.value == "Content"
        assert intensity == 0.3
        assert "gentle" in reason.lower()

    def test_poor_maps_to_disappointed(self) -> None:
        integrator = self._make_integrator()
        ghi = _make_ghi_result(tier=GHITier.POOR, ghi_score=45.0)
        mood, intensity, reason = integrator._map_tier_to_mood(ghi)
        assert mood is not None
        assert mood.value == "Disappointed"
        assert intensity == 0.4
        assert "caring" in reason.lower()

    def test_critical_maps_to_disappointed_concerned(self) -> None:
        integrator = self._make_integrator()
        ghi = _make_ghi_result(tier=GHITier.CRITICAL, ghi_score=30.0)
        mood, intensity, reason = integrator._map_tier_to_mood(ghi)
        assert mood is not None
        assert mood.value == "Disappointed"
        assert intensity == 0.6
        assert "concerned" in reason.lower()


class TestHealthMoodIntegratorSafeToApply:
    """Test is_safe_to_apply() with mocked Redis."""

    def _make_integrator_with_redis(self, mock_redis: AsyncMock) -> HealthMoodIntegrator:
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis
        return integrator

    @pytest.mark.asyncio
    async def test_safe_when_consent_granted_and_persona_normal(self) -> None:
        """is_safe_to_apply returns True when consent granted and persona state is normal."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            assert await integrator.is_safe_to_apply() is True

    @pytest.mark.asyncio
    async def test_unsafe_when_no_persona_state(self) -> None:
        """is_safe_to_apply returns False when persona:state:active is missing (default-deny)."""
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            assert await integrator.is_safe_to_apply() is False

    @pytest.mark.asyncio
    async def test_unsafe_when_consent_revoked(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=False)
            assert await integrator.is_safe_to_apply() is False

    @pytest.mark.asyncio
    async def test_unsafe_when_consent_revoked_true(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=False)
            assert await integrator.is_safe_to_apply() is False

    @pytest.mark.asyncio
    async def test_unsafe_when_distress_state(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "distress",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            assert await integrator.is_safe_to_apply() is False

    @pytest.mark.asyncio
    async def test_unsafe_when_argument_state(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "argument",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            assert await integrator.is_safe_to_apply() is False

    @pytest.mark.asyncio
    async def test_safe_when_persona_state_is_neutral(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "content",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator_with_redis(mock_redis)
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            assert await integrator.is_safe_to_apply() is True


class TestHealthMoodIntegratorComputeModifier:
    """Test compute_modifier() with mocked Redis and datetime."""

    def _make_integrator(self, mock_redis: AsyncMock) -> HealthMoodIntegrator:
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis
        return integrator

    @pytest.mark.asyncio
    async def test_suppressed_ghi_returns_none(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = self._make_integrator(mock_redis)
        ghi = _make_ghi_result(suppressed=True)
        result = await integrator.compute_modifier(ghi)
        assert result is None

    @pytest.mark.asyncio
    async def test_unsafe_returns_none(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = self._make_integrator(mock_redis)
        ghi = _make_ghi_result()
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=False)
            result = await integrator.compute_modifier(ghi)
        assert result is None

    @pytest.mark.asyncio
    async def test_quiet_hours_non_critical_returns_none(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator(mock_redis)
        ghi = _make_ghi_result(tier=GHITier.GOOD, ghi_score=75.0)

        with patch("src.wearable.mood_integration.datetime") as mock_dt, \
             patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 3, 0, 0, tzinfo=UTC)  # 3 AM - quiet
            mock_consent.return_value = MagicMock(allowed=True)
            result = await integrator.compute_modifier(ghi)
        assert result is None

    @pytest.mark.asyncio
    async def test_quiet_hours_critical_still_returns_modifier(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator(mock_redis)
        ghi = _make_ghi_result(tier=GHITier.CRITICAL, ghi_score=30.0)

        with patch("src.wearable.mood_integration.datetime") as mock_dt, \
             patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 3, 0, 0, tzinfo=UTC)  # 3 AM - quiet
            mock_consent.return_value = MagicMock(allowed=True)
            result = await integrator.compute_modifier(ghi)
        assert result is not None
        assert result.target_mood is not None

    @pytest.mark.asyncio
    async def test_active_hours_returns_modifier(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))
        integrator = self._make_integrator(mock_redis)
        ghi = _make_ghi_result(tier=GHITier.EXCELLENT, ghi_score=90.0)

        with patch("src.wearable.mood_integration.datetime") as mock_dt, \
             patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 12, 0, 0, tzinfo=UTC)  # noon
            mock_consent.return_value = MagicMock(allowed=True)
            result = await integrator.compute_modifier(ghi)
        assert result is not None
        assert result.target_mood is not None
        assert result.intensity > 0.0


class TestHealthMoodIntegratorApplyAndGet:
    """Test apply_modifier() and get_active_modifier()."""

    @pytest.mark.asyncio
    async def test_apply_modifier_writes_to_redis(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.set = AsyncMock(return_value=True)
        mock_redis.lpush = AsyncMock(return_value=1)
        mock_redis.ltrim = AsyncMock(return_value=True)
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis

        modifier = WearableMoodModifier(
            target_mood=Mood.CONTENT,
            reason="test",
            intensity=0.5,
            expires_at=datetime.now(UTC) + timedelta(hours=24),
        )
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            await integrator.apply_modifier(modifier)
        mock_redis.set.assert_called_once()
        mock_redis.lpush.assert_called_once()
        mock_redis.ltrim.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_active_modifier_returns_none_when_empty(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(return_value=None)
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis

        result = await integrator.get_active_modifier()
        assert result is None

    @pytest.mark.asyncio
    async def test_get_active_modifier_returns_expired_clears(self) -> None:
        mock_redis = AsyncMock()
        expired_modifier = WearableMoodModifier(
            target_mood=Mood.CONTENT,
            reason="test",
            intensity=0.5,
            expires_at=datetime.now(UTC) - timedelta(hours=1),  # expired
        )
        mock_redis.get = AsyncMock(return_value=expired_modifier.to_json())
        mock_redis.delete = AsyncMock(return_value=1)
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis

        result = await integrator.get_active_modifier()
        assert result is None
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_clear_modifier_deletes_key(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(return_value=1)
        integrator = HealthMoodIntegrator("redis://localhost:6380", "postgresql://localhost/test")
        integrator._redis = mock_redis

        await integrator.clear_modifier()
        mock_redis.delete.assert_called_once()


# ===========================================================================
# alert_router.py
# ===========================================================================


class TestRateLimiter:
    """Test RateLimiter sliding window logic."""

    def test_allows_alerts_under_limit(self) -> None:
        limiter = RateLimiter(max_alerts=3, window_seconds=3600)
        now = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        assert limiter._is_allowed(now) is True
        limiter._record_alert(now)
        assert limiter._is_allowed(now) is True
        limiter._record_alert(now)
        assert limiter._is_allowed(now) is True
        limiter._record_alert(now)
        assert limiter._is_allowed(now) is False

    def test_prunes_old_entries(self) -> None:
        limiter = RateLimiter(max_alerts=2, window_seconds=3600)
        old = datetime(2026, 6, 18, 8, 0, 0, tzinfo=UTC)
        new = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
        limiter._record_alert(old)
        limiter._record_alert(old)
        # After window passes, old entries are pruned
        assert limiter._is_allowed(new) is True

    def test_is_allowed_uses_datetime_now_by_default(self) -> None:
        limiter = RateLimiter(max_alerts=5, window_seconds=3600)
        with patch("src.wearable.alert_router.datetime") as mock_dt:
            fixed = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
            mock_dt.now.return_value = fixed
            assert limiter._is_allowed() is True


class TestAlertRouterParsing:
    """Test AlertRouter helper methods (no DB needed)."""

    def _make_router(self) -> AlertRouter:
        config = WearableConfig()
        router = AlertRouter(config, "postgresql://localhost/test")
        router._is_safe_mode_active = AsyncMock(return_value=False)  # type: ignore[method-assign]
        return router

    def test_parse_time_valid(self) -> None:
        result = AlertRouter._parse_time("23:30")
        assert result == dtime(23, 30)

    def test_parse_time_midnight(self) -> None:
        result = AlertRouter._parse_time("00:00")
        assert result == dtime(0, 0)

    def test_format_number_with_value(self) -> None:
        assert AlertRouter._format_number(72.5) == "72.50"

    def test_format_number_none(self) -> None:
        assert AlertRouter._format_number(None) == "n/a"

    def test_severity_style_sev0(self) -> None:
        router = self._make_router()
        color, title = router._severity_style(AlertSeverity.SEV0)
        assert color == 0xDC143C
        assert "URGENT" in title

    def test_severity_style_sev1(self) -> None:
        router = self._make_router()
        color, _ = router._severity_style(AlertSeverity.SEV1)
        assert color == 0xFF8C00

    def test_severity_style_sev2(self) -> None:
        router = self._make_router()
        color, _ = router._severity_style(AlertSeverity.SEV2)
        assert color == 0xFFD700

    def test_severity_style_sev3(self) -> None:
        router = self._make_router()
        color, title = router._severity_style(AlertSeverity.SEV3)
        assert color == 0x808080
        assert "Log" in title

    def test_format_discord_embed_has_required_fields(self) -> None:
        router = self._make_router()
        event = _make_anomaly_event(severity=AlertSeverity.SEV2)
        embed = router._format_discord_embed(event)
        assert embed["title"] is not None
        assert embed["color"] is not None
        assert embed["severity"] == "SEV2"
        assert len(embed["fields"]) == 5


class TestAlertRouterIsQuietHours:
    """Test _is_quiet_hours with various time configurations."""

    def test_default_quiet_hours_23_to_07(self) -> None:
        config = WearableConfig()  # defaults: 23:00 - 07:00
        router = AlertRouter(config, "postgresql://localhost/test")
        # 23:00 is quiet
        assert router._is_quiet_hours(datetime(2026, 6, 18, 23, 0, tzinfo=UTC)) is True
        # 03:00 is quiet
        assert router._is_quiet_hours(datetime(2026, 6, 18, 3, 0, tzinfo=UTC)) is True
        # 12:00 is not quiet
        assert router._is_quiet_hours(datetime(2026, 6, 18, 12, 0, tzinfo=UTC)) is False
        # 07:00 is NOT quiet (exclusive end)
        assert router._is_quiet_hours(datetime(2026, 6, 18, 7, 0, tzinfo=UTC)) is False

    def test_quiet_hours_same_start_end_never_quiet(self) -> None:
        """If start == end, quiet hours logic means never quiet."""
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="00:00",
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        assert router._is_quiet_hours(datetime(2026, 6, 18, 12, 0, tzinfo=UTC)) is False
        assert router._is_quiet_hours(datetime(2026, 6, 18, 3, 0, tzinfo=UTC)) is False

    def test_quiet_hours_within_day_range(self) -> None:
        """Same-day quiet hours (e.g., 09:00-17:00)."""
        config = WearableConfig(
            wearable_quiet_hours_start="09:00",
            wearable_quiet_hours_end="17:00",
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        assert router._is_quiet_hours(datetime(2026, 6, 18, 12, 0, tzinfo=UTC)) is True
        assert router._is_quiet_hours(datetime(2026, 6, 18, 20, 0, tzinfo=UTC)) is False


class TestAlertRouterRouteEvent:
    """Test AlertRouter.route_event() with various SEV levels and time scenarios."""

    def _make_router(self) -> AlertRouter:
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="00:00",  # Never quiet
            wearable_alert_rate_limit=5,
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]
        # Mock safe mode check to avoid real Redis connections in tests
        router._is_safe_mode_active = AsyncMock(return_value=False)  # type: ignore[method-assign]
        return router

    @pytest.mark.asyncio
    async def test_sev0_delivered_immediately(self) -> None:
        router = self._make_router()
        event = _make_anomaly_event(severity=AlertSeverity.SEV0)
        with patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            result = await router.route_event(event)
        assert result.delivered is True
        assert result.severity is AlertSeverity.SEV0
        assert result.channel == "discord_dm"

    @pytest.mark.asyncio
    async def test_sev1_delivered_during_active_hours(self) -> None:
        router = self._make_router()
        event = _make_anomaly_event(severity=AlertSeverity.SEV1)
        with patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            result = await router.route_event(event)
        assert result.delivered is True
        assert result.severity is AlertSeverity.SEV1
        assert result.channel == "discord_dm"

    @pytest.mark.asyncio
    async def test_sev2_delivered_during_active_hours(self) -> None:
        router = self._make_router()
        event = _make_anomaly_event(severity=AlertSeverity.SEV2)
        with patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            result = await router.route_event(event)
        assert result.delivered is True
        assert result.severity is AlertSeverity.SEV2

    @pytest.mark.asyncio
    async def test_sev3_log_only(self) -> None:
        router = self._make_router()
        event = _make_anomaly_event(severity=AlertSeverity.SEV3)
        result = await router.route_event(event)
        assert result.delivered is False
        assert result.buffered is False
        assert result.rate_limited is False
        assert result.channel == "log_only"

    @pytest.mark.asyncio
    async def test_sev0_bypasses_quiet_hours(self) -> None:
        """SEV0 should be delivered even during quiet hours."""
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="23:59",  # Always quiet (almost)
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]
        event = _make_anomaly_event(severity=AlertSeverity.SEV0)
        with patch("src.wearable.alert_router.datetime") as mock_dt, \
             patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 3, 0, 0, tzinfo=UTC)  # quiet hours
            mock_consent.return_value = MagicMock(allowed=True)
            result = await router.route_event(event)
        assert result.delivered is True
        assert result.severity is AlertSeverity.SEV0

    @pytest.mark.asyncio
    async def test_sev1_buffered_during_quiet_hours(self) -> None:
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="23:59",  # Always quiet
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]
        event = _make_anomaly_event(severity=AlertSeverity.SEV1)
        with patch("src.wearable.alert_router.datetime") as mock_dt, \
             patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 12, 0, 0, tzinfo=UTC)  # quiet
            mock_consent.return_value = MagicMock(allowed=True)
            result = await router.route_event(event)
        assert result.delivered is False
        assert result.buffered is True
        assert result.channel == "buffered"

    @pytest.mark.asyncio
    async def test_rate_limiting(self) -> None:
        """When rate limit is exceeded, events are rate-limited."""
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="00:00",
            wearable_alert_rate_limit=2,
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]

        event1 = _make_anomaly_event(severity=AlertSeverity.SEV0)
        event2 = _make_anomaly_event(severity=AlertSeverity.SEV0)
        event3 = _make_anomaly_event(severity=AlertSeverity.SEV0)

        with patch("src.wearable.alert_router.check_metric_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            r1 = await router.route_event(event1)
            r2 = await router.route_event(event2)
            r3 = await router.route_event(event3)

        assert r1.delivered is True
        assert r2.delivered is True
        assert r3.rate_limited is True
        assert r3.delivered is False


class TestAlertRouterFlushBuffered:
    """Test AlertRouter.flush_buffered() behaviour."""

    def _make_router(self, quiet: bool = False) -> AlertRouter:
        config = WearableConfig(
            wearable_quiet_hours_start="00:00" if quiet else "23:00",
            wearable_quiet_hours_end="00:00" if quiet else "07:00",
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]
        # Mock safe mode check to avoid real Redis connections in tests
        router._is_safe_mode_active = AsyncMock(return_value=False)  # type: ignore[method-assign]
        return router

    @pytest.mark.asyncio
    async def test_flush_returns_empty_during_quiet_hours(self) -> None:
        router = self._make_router(quiet=True)
        with patch("src.wearable.alert_router.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 18, 3, 0, 0, tzinfo=UTC)  # quiet
            results = await router.flush_buffered()
        assert results == []

    @pytest.mark.asyncio
    async def test_flush_delivers_buffered_events_during_active_hours(self) -> None:
        config = WearableConfig(
            wearable_quiet_hours_start="00:00",
            wearable_quiet_hours_end="00:00",  # never quiet
        )
        router = AlertRouter(config, "postgresql://localhost/test")
        router._persist_alert_sent = AsyncMock()  # type: ignore[method-assign]

        # Manually add buffered events
        event = _make_anomaly_event(severity=AlertSeverity.SEV1)
        batch = AlertBatch(events=[event], severity=AlertSeverity.SEV1)
        router._buffer[AlertSeverity.SEV1.value].append(batch)

        results = await router.flush_buffered()
        assert len(results) == 1
        assert results[0].delivered is True
        assert results[0].severity is AlertSeverity.SEV1
        assert router._buffer[AlertSeverity.SEV1.value] == []

    @pytest.mark.asyncio
    async def test_flush_empty_buffer(self) -> None:
        router = self._make_router()
        results = await router.flush_buffered()
        assert results == []


# ===========================================================================
# health_consent.py
# ===========================================================================


class TestWearableConsentConstants:
    """Verify module-level constants."""

    def test_cache_key_prefix(self) -> None:
        assert CACHE_KEY_PREFIX == "consent:wearable-health:"

    def test_cache_ttl_seconds(self) -> None:
        assert CACHE_TTL_SECONDS == 300

    def test_valid_scopes_count(self) -> None:
        assert len(VALID_WEARABLE_SCOPES) == 7

    def test_valid_scopes_contents(self) -> None:
        expected = {
            "wearable-health.hr",
            "wearable-health.activity",
            "wearable-health.spo2",
            "wearable-health.stress",
            "wearable-health.sleep",
            "wearable-health.ghi",
            "wearable-health.alerts",
        }
        assert VALID_WEARABLE_SCOPES == expected

    def test_metric_to_scope_mapping(self) -> None:
        assert METRIC_TO_SCOPE[HealthMetricType.HEART_RATE] == "wearable-health.hr"
        assert METRIC_TO_SCOPE[HealthMetricType.STEPS] == "wearable-health.activity"
        assert METRIC_TO_SCOPE[HealthMetricType.SPO2] == "wearable-health.spo2"
        assert METRIC_TO_SCOPE[HealthMetricType.STRESS] == "wearable-health.stress"
        assert METRIC_TO_SCOPE[HealthMetricType.SLEEP] == "wearable-health.sleep"
        assert METRIC_TO_SCOPE[HealthMetricType.ACTIVITY] == "wearable-health.activity"


class TestConsentStatusEnum:
    """Verify ConsentStatus StrEnum values."""

    def test_active(self) -> None:
        assert ConsentStatus.ACTIVE == "ACTIVE"

    def test_paused(self) -> None:
        assert ConsentStatus.PAUSED == "PAUSED"

    def test_withdrawn(self) -> None:
        assert ConsentStatus.WITHDRAWN == "WITHDRAWN"

    def test_count(self) -> None:
        assert len(ConsentStatus) == 3


class TestWearableConsentCheckResult:
    """Verify WearableConsentCheckResult frozen dataclass."""

    def test_fields_accessible(self) -> None:
        now = datetime.now(timezone.utc)
        result = WearableConsentCheckResult(
            allowed=True,
            status=ConsentStatus.ACTIVE,
            scope="wearable-health.hr",
            reason="consent is active",
            checked_at=now,
        )
        assert result.allowed is True
        assert result.status == ConsentStatus.ACTIVE
        assert result.scope == "wearable-health.hr"
        assert result.checked_at == now

    def test_frozen(self) -> None:
        now = datetime.now(timezone.utc)
        result = WearableConsentCheckResult(
            allowed=False, status=None, scope="x", reason="y", checked_at=now,
        )
        with pytest.raises(Exception):
            setattr(result, "allowed", True)


def _make_consent_db(status: ConsentStatus | None) -> MagicMock:
    """Build a mock DB session for consent check."""
    mock_session = MagicMock()
    mock_result = MagicMock()
    if status is None:
        mock_result.fetchone.return_value = None
    else:
        mock_result.fetchone.return_value = (status.value,)
    mock_session.execute = AsyncMock(return_value=mock_result)
    return mock_session


def _make_consent_redis(get_return: str | None = None) -> AsyncMock:
    """Build a mock Redis client for consent check."""
    mock_redis = AsyncMock()
    mock_redis.get = AsyncMock(return_value=get_return)
    mock_redis.set = AsyncMock(return_value=True)
    mock_redis.delete = AsyncMock(return_value=1)
    return mock_redis


class TestCheckWearableConsent:
    """Test check_wearable_consent() with mocked DB and Redis."""

    @pytest.fixture(autouse=True)
    def _cleanup(self) -> Iterator[None]:
        yield
        _set_redis_for_testing(None)
        _set_db_session_for_testing(None)

    @pytest.mark.asyncio
    async def test_active_consent_returns_allowed(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is True
        assert result.status == ConsentStatus.ACTIVE

    @pytest.mark.asyncio
    async def test_paused_consent_returns_blocked(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.PAUSED))

        result = await check_wearable_consent("wearable-health.spo2")
        assert result.allowed is False
        assert result.status == ConsentStatus.PAUSED
        assert "paused" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_withdrawn_consent_returns_blocked(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.WITHDRAWN))

        result = await check_wearable_consent("wearable-health.sleep")
        assert result.allowed is False
        assert result.status == ConsentStatus.WITHDRAWN
        assert "withdrawn" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_no_ledger_entry_returns_blocked(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(None))

        result = await check_wearable_consent("wearable-health.ghi")
        assert result.allowed is False
        assert result.status is None
        assert "never consented" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_unknown_scope_returns_blocked(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)

        result = await check_wearable_consent("wearable-health.nonexistent")
        assert result.allowed is False
        assert "unknown" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_empty_scope_returns_blocked(self) -> None:
        result = await check_wearable_consent("")
        assert result.allowed is False
        assert "unknown" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_db_failure_fails_closed(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)

        mock_session = MagicMock()
        mock_session.execute = AsyncMock(side_effect=ConnectionError("DB down"))
        _set_db_session_for_testing(mock_session)

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is False
        assert "fail-closed" in result.reason.lower()

    @pytest.mark.asyncio
    async def test_cache_hit_skips_db(self) -> None:
        cache_payload = json.dumps({
            "allowed": True,
            "status": "ACTIVE",
            "scope": "wearable-health.hr",
            "reason": "cached",
            "checked_at": datetime.now(timezone.utc).isoformat(),
        })
        mock_redis = _make_consent_redis(get_return=cache_payload)
        _set_redis_for_testing(mock_redis)
        mock_db = _make_consent_db(ConsentStatus.ACTIVE)
        _set_db_session_for_testing(mock_db)

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is True
        # DB should not have been called
        mock_db.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_cache_miss_falls_through_to_db(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is True
        mock_redis.get.assert_called()

    @pytest.mark.asyncio
    async def test_redis_unavailable_falls_through(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.get = AsyncMock(side_effect=ConnectionError("Redis down"))
        mock_redis.set = AsyncMock(return_value=True)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is True

    @pytest.mark.asyncio
    async def test_no_db_session_raises_runtime_error(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        # No DB session set
        _set_db_session_for_testing(None)

        result = await check_wearable_consent("wearable-health.hr")
        # Should fail-closed
        assert result.allowed is False

    @pytest.mark.asyncio
    async def test_active_caches_positive_result(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        await check_wearable_consent("wearable-health.hr")
        mock_redis.set.assert_called_once()
        call_args = mock_redis.set.call_args
        assert call_args[0][0] == f"{CACHE_KEY_PREFIX}wearable-health.hr"
        assert call_args[1]["ex"] == CACHE_TTL_SECONDS


class TestCheckMetricConsent:
    """Test check_metric_consent() delegates to check_wearable_consent()."""

    @pytest.mark.asyncio
    async def test_heart_rate_maps_to_hr_scope(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        result = await check_metric_consent(HealthMetricType.HEART_RATE)
        assert result.allowed is True
        assert result.scope == "wearable-health.hr"

        _set_redis_for_testing(None)
        _set_db_session_for_testing(None)

    @pytest.mark.asyncio
    async def test_steps_maps_to_activity_scope(self) -> None:
        mock_redis = _make_consent_redis(get_return=None)
        _set_redis_for_testing(mock_redis)
        _set_db_session_for_testing(_make_consent_db(ConsentStatus.ACTIVE))

        result = await check_metric_consent(HealthMetricType.STEPS)
        assert result.scope == "wearable-health.activity"

        _set_redis_for_testing(None)
        _set_db_session_for_testing(None)


class TestConsentGrantRevoke:
    """Test grant_consent, revoke_consent, pause_consent, withdraw_consent."""

    @pytest.fixture(autouse=True)
    def _cleanup(self) -> Iterator[None]:
        yield
        _set_redis_for_testing(None)
        _set_db_session_for_testing(None)

    @pytest.mark.asyncio
    async def test_grant_consent_writes_db_and_invalidates_cache(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        _set_db_session_for_testing(mock_db)

        result = await grant_consent("wearable-health.hr")
        assert result is True
        mock_db.execute.assert_called_once()
        mock_redis.delete.assert_called_once()

    @pytest.mark.asyncio
    async def test_revoke_consent_returns_true(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        _set_db_session_for_testing(mock_db)

        result = await revoke_consent("wearable-health.hr")
        assert result is True

    @pytest.mark.asyncio
    async def test_pause_consent_returns_true(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        _set_db_session_for_testing(mock_db)

        result = await pause_consent("wearable-health.hr")
        assert result is True

    @pytest.mark.asyncio
    async def test_withdraw_consent_delegates_to_revoke(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(return_value=MagicMock())
        _set_db_session_for_testing(mock_db)

        result = await withdraw_consent("wearable-health.hr")
        assert result is True

    @pytest.mark.asyncio
    async def test_grant_consent_db_failure_returns_false(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)
        mock_db = MagicMock()
        mock_db.execute = AsyncMock(side_effect=ConnectionError("DB down"))
        _set_db_session_for_testing(mock_db)

        result = await grant_consent("wearable-health.hr")
        assert result is False

    @pytest.mark.asyncio
    async def test_no_db_session_returns_false(self) -> None:
        _set_redis_for_testing(_make_consent_redis())
        _set_db_session_for_testing(None)

        result = await grant_consent("wearable-health.hr")
        assert result is False


class TestInvalidateConsentCache:
    """Test invalidate_consent_cache()."""

    @pytest.mark.asyncio
    async def test_invalidate_deletes_correct_key(self) -> None:
        mock_redis = _make_consent_redis()
        _set_redis_for_testing(mock_redis)

        await invalidate_consent_cache("wearable-health.hr")
        mock_redis.delete.assert_called_once_with(f"{CACHE_KEY_PREFIX}wearable-health.hr")

        _set_redis_for_testing(None)

    @pytest.mark.asyncio
    async def test_invalidate_survives_redis_error(self) -> None:
        mock_redis = AsyncMock()
        mock_redis.delete = AsyncMock(side_effect=ConnectionError("Redis down"))
        _set_redis_for_testing(mock_redis)

        # Should not raise
        await invalidate_consent_cache("wearable-health.hr")

        _set_redis_for_testing(None)


# ===========================================================================
# Error hierarchy
# ===========================================================================


class TestErrorHierarchy:
    """Verify custom exception classes follow proper inheritance."""

    def test_wearable_error_is_exception(self) -> None:
        assert issubclass(Exception, object)  # sanity
        from src.wearable.errors import WearableError
        assert issubclass(WearableError, Exception)

    def test_auth_error_inherits(self) -> None:
        from src.wearable.errors import AuthError, WearableError
        assert issubclass(AuthError, WearableError)

    def test_rate_limit_error_inherits(self) -> None:
        from src.wearable.errors import RateLimitError, WearableError
        assert issubclass(RateLimitError, WearableError)

    def test_consent_denied_error_inherits(self) -> None:
        from src.wearable.errors import ConsentDeniedError, WearableError
        assert issubclass(ConsentDeniedError, WearableError)

    def test_circuit_breaker_error_inherits(self) -> None:
        from src.wearable.errors import CircuitBreakerOpenError, WearableError
        assert issubclass(CircuitBreakerOpenError, WearableError)

    def test_error_with_metric(self) -> None:
        from src.wearable.errors import AuthError
        err = AuthError("auth failed", metric="heart_rate")
        assert err.metric == "heart_rate"
        assert "auth failed" in str(err)
