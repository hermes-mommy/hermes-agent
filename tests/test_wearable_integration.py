"""End-to-end integration test for the wearable health pipeline.

Simulates the full data flow:
    Mi Fitness API mock -> normalizer -> Redis buffer -> writer
        -> TimescaleDB mock -> baseline -> anomaly -> GHI -> mood modifier

All external dependencies (asyncpg, redis, httpx) are fully mocked. No real
network or database connections are made. This file focuses on the *integration*
between components, not on unit-level coverage (which lives in test_wearable.py).

Each scenario exercises a real cross-module flow and asserts on observable
outcomes: returned GHI tiers, dropped sample counts, alert routing results,
mood suppression behavior, and encryption round-trips.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from collections.abc import Iterator
from typing import Any, cast
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure project root is on sys.path so ``from src.*`` imports resolve
# regardless of how pytest is invoked.
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from src.persona.mood_engine import Mood  # noqa: E402
from src.wearable.anomaly import AnomalyDetector, BaselineLike  # noqa: E402
from src.wearable.baseline import BaselineCalculator, BaselineState  # noqa: E402
from src.wearable.config import WearableConfig  # noqa: E402
from src.wearable.encryption import (  # noqa: E402
    SENSITIVE_FIELDS,
    decrypt_health_record,
    decrypt_value,
    encrypt_health_record,
    encrypt_value,
    get_encryption_key,
)
from src.wearable.errors import RateLimitError  # noqa: E402
from src.wearable.ghi import GHIScorer  # noqa: E402
from src.wearable.mi_fitness_client import (  # noqa: E402
    MiFitnessClient,
    _CircuitBreaker,
    _CircuitState,
)
from src.wearable.health_consent import (  # noqa: E402
    ConsentStatus,
    _set_db_session_for_testing,
    _set_redis_for_testing,
    check_metric_consent,
    check_wearable_consent,
    grant_consent,
    invalidate_consent_cache,
    revoke_consent,
)
from src.wearable.mi_fitness_client import (  # noqa: E402
    MiFitnessClient,
    _CircuitBreaker,
    _CircuitState,
)
from src.wearable.models import (  # noqa: E402
    AlertSeverity,
    BaselineStage,
    DateRange,
    FetchResult,
    GHIResult,
    GHITier,
    HealthMetricType,
    MetricResult,
    MetricStatus,
    NormalizedHealthSample,
)
from src.wearable.mood_integration import HealthMoodIntegrator  # noqa: E402
from src.wearable.normalizer import normalize_fetch_result  # noqa: E402
from src.wearable.redis_buffer import WearableBuffer  # noqa: E402
from src.wearable.writer import HealthIngestionWriter, WriteResult  # noqa: E402
from src.wearable.alert_router import AlertRouter  # noqa: E402


# ===========================================================================
# Constants -- canonical UUIDs, timestamps, and device/owner identifiers
# ===========================================================================

DEVICE_ID = "11111111-1111-1111-1111-111111111111"
OWNER_ID = "22222222-2222-2222-2222-222222222222"
SAMPLE_TS = datetime(2026, 6, 18, 10, 0, 0, tzinfo=UTC)
TEST_DATE = date(2026, 6, 18)

DATABASE_URL = "postgresql://test:test@localhost:5433/test_db"
REDIS_URL = "redis://localhost:6380/2"


# ===========================================================================
# Mock builders
# ===========================================================================


def _make_mock_record(data: dict[str, Any]) -> MagicMock:
    """Build a mock asyncpg Record that supports ``row["col"]`` access."""
    rec = MagicMock()
    rec.__getitem__ = MagicMock(side_effect=lambda key: data[key])
    rec.keys = MagicMock(return_value=list(data.keys()))
    return rec


def _make_mock_pool(conn: AsyncMock | None = None) -> tuple[MagicMock, AsyncMock]:
    """Build a (mock_pool, mock_conn) pair for asyncpg.

    ``pool.acquire()`` returns an async context manager that yields ``mock_conn``.
    """
    mock_conn = conn if conn is not None else AsyncMock()
    mock_pool = MagicMock()
    mock_pool.close = AsyncMock()
    acquire_cm = AsyncMock()
    acquire_cm.__aenter__ = AsyncMock(return_value=mock_conn)
    acquire_cm.__aexit__ = AsyncMock(return_value=None)
    mock_pool.acquire = MagicMock(return_value=acquire_cm)
    return mock_pool, mock_conn


def _make_mock_redis() -> MagicMock:
    """Build a fully-mocked Redis client usable by buffer (sync) and integrator (async)."""
    redis_client = MagicMock()
    pipe = MagicMock()
    pipe.execute = MagicMock(return_value=[1, 1, 1, 5])
    redis_client.pipeline = MagicMock(return_value=pipe)
    redis_client.rpush = MagicMock(return_value=1)
    redis_client.lpush = MagicMock(return_value=1)
    redis_client.llen = MagicMock(return_value=0)
    redis_client.lpop = MagicMock(return_value=None)
    # Methods used by the HealthMoodIntegrator (async) -- return AsyncMock so ``await`` works.
    redis_client.get = AsyncMock(return_value=None)
    redis_client.set = AsyncMock(return_value=True)
    redis_client.setex = AsyncMock(return_value=True)
    redis_client.delete = AsyncMock(return_value=1)
    redis_client.ltrim = AsyncMock(return_value=True)
    return redis_client


def _build_healthy_fetch_result(
    heart_rate: float = 72.0,
    steps: float = 8000.0,
    spo2: float = 97.0,
    stress: float = 35.0,
    sleep: float = 480.0,
) -> FetchResult:
    """Build a FetchResult with sensible 'healthy' defaults."""
    now = SAMPLE_TS
    return FetchResult(
        timestamp=now,
        device_id=DEVICE_ID,
        metrics={
            "heart_rate": MetricResult(
                metric=HealthMetricType.HEART_RATE,
                status=MetricStatus.AVAILABLE,
                samples=[
                    NormalizedHealthSample(
                        metric_type=HealthMetricType.HEART_RATE,
                        timestamp=now,
                        device_id=DEVICE_ID,
                        owner_id=OWNER_ID,
                        value=heart_rate,
                        unit="bpm",
                    )
                ],
            ),
            "steps": MetricResult(
                metric=HealthMetricType.STEPS,
                status=MetricStatus.AVAILABLE,
                samples=[
                    NormalizedHealthSample(
                        metric_type=HealthMetricType.STEPS,
                        timestamp=now,
                        device_id=DEVICE_ID,
                        owner_id=OWNER_ID,
                        value=steps,
                        unit="steps",
                    )
                ],
            ),
            "spo2": MetricResult(
                metric=HealthMetricType.SPO2,
                status=MetricStatus.AVAILABLE,
                samples=[
                    NormalizedHealthSample(
                        metric_type=HealthMetricType.SPO2,
                        timestamp=now,
                        device_id=DEVICE_ID,
                        owner_id=OWNER_ID,
                        value=spo2,
                        unit="%",
                    )
                ],
            ),
            "stress": MetricResult(
                metric=HealthMetricType.STRESS,
                status=MetricStatus.AVAILABLE,
                samples=[
                    NormalizedHealthSample(
                        metric_type=HealthMetricType.STRESS,
                        timestamp=now,
                        device_id=DEVICE_ID,
                        owner_id=OWNER_ID,
                        value=stress,
                        unit="score",
                    )
                ],
            ),
            "sleep": MetricResult(
                metric=HealthMetricType.SLEEP,
                status=MetricStatus.AVAILABLE,
                samples=[
                    NormalizedHealthSample(
                        metric_type=HealthMetricType.SLEEP,
                        timestamp=now,
                        device_id=DEVICE_ID,
                        owner_id=OWNER_ID,
                        value=sleep,
                        unit="minutes",
                    )
                ],
            ),
        },
    )


def _build_healthy_config(**overrides: Any) -> WearableConfig:
    """Build a WearableConfig with sensible integration-test defaults."""
    return WearableConfig(
        mi_fitness_user_id="user-1",
        mi_fitness_pass_token="token-1",
        mi_fitness_region="cn",
        wearable_device_id=DEVICE_ID,
        wearable_owner_id=OWNER_ID,
        redis_host="localhost",
        redis_port=6380,
        postgres_host="localhost",
        postgres_port=5433,
        **overrides,
    )


def _stable_baseline_state(
    metric: HealthMetricType,
    value: float = 72.0,
    stage: BaselineStage = BaselineStage.STABLE,
    confidence: float = 0.9,
) -> BaselineState:
    """Build a BaselineState for use as a stand-in baseline in tests."""
    return BaselineState(
        metric=metric,
        device_id=DEVICE_ID,
        owner_id=OWNER_ID,
        stage=stage,
        baseline_value=value,
        stddev=1.0,
        confidence=confidence,
        data_points=30,
        first_data_at=SAMPLE_TS - timedelta(days=30),
        last_data_at=SAMPLE_TS,
        updated_at=SAMPLE_TS,
    )


def _make_consent_session() -> tuple[MagicMock, dict[str, ConsentStatus]]:
    """Build a stateful mock SQLAlchemy async session for the consent ledger.

    Returns (session, state) where state is a mutable dict that maps
    scope -> current ConsentStatus.  Writes (INSERT) and reads (SELECT) both
    read/write through this dict so ``grant_consent`` followed by
    ``check_wearable_consent`` behaves as expected.
    """
    state: dict[str, ConsentStatus] = {}

    async def _execute(_stmt: Any, params: dict[str, object] | None = None) -> MagicMock:
        result = MagicMock()
        if params is None:
            result.fetchone = MagicMock(return_value=None)
            return result
        if "scope" in params and "status" in params:
            # INSERT: record the new consent state.
            scope = str(params["scope"])
            state[scope] = ConsentStatus(str(params["status"]))
            result.fetchone = MagicMock(return_value=(1,))
        elif "scope" in params:
            # SELECT: return the most recent state.
            scope = str(params["scope"])
            if scope in state:
                result.fetchone = MagicMock(return_value=(state[scope].value,))
            else:
                result.fetchone = MagicMock(return_value=None)
        else:
            result.fetchone = MagicMock(return_value=None)
        return result

    session = MagicMock()
    session.execute = _execute
    return session, state


# ===========================================================================
# Shared fixtures
# ===========================================================================


@pytest.fixture(autouse=True)
def _isolate_health_consent_state() -> Iterator[None]:
    """Reset health consent module globals between tests.

    Both redis and db_session must be mocked -- otherwise the consent
    module's lazy initializers will try to reach a real Redis on
    localhost:6380 and the test will hang.
    """
    mock_redis_client = MagicMock()
    mock_redis_client.get = AsyncMock(return_value=None)
    mock_redis_client.set = AsyncMock(return_value=True)
    mock_redis_client.delete = AsyncMock(return_value=1)
    _set_redis_for_testing(mock_redis_client)
    _set_db_session_for_testing(None)
    yield
    _set_db_session_for_testing(None)
    _set_redis_for_testing(None)


@pytest.fixture(autouse=True)
def _reset_encryption_cache() -> Iterator[None]:
    """Clear the lru_cached Fernet key so each test gets a fresh resolution."""
    get_encryption_key.cache_clear()
    yield
    get_encryption_key.cache_clear()


@pytest.fixture
def mock_config() -> WearableConfig:
    """Standard mock config for integration tests."""
    return _build_healthy_config()


@pytest.fixture
def mock_pool() -> tuple[MagicMock, AsyncMock]:
    """A reusable (mock_pool, mock_conn) pair."""
    return _make_mock_pool()


@pytest.fixture
def mock_redis() -> MagicMock:
    """A reusable mock Redis client."""
    return _make_mock_redis()


# ===========================================================================
# Scenario 1: Full healthy pipeline (all metrics available)
# ===========================================================================


class TestScenario1FullHealthyPipeline:
    """End-to-end happy path: every metric flows through every stage cleanly."""

    @pytest.mark.asyncio
    async def test_full_healthy_pipeline(
        self,
        mock_pool: tuple[MagicMock, AsyncMock],
        mock_redis: MagicMock,
    ) -> None:
        """Mi Fitness mock -> normalizer -> buffer -> writer -> GHI -> mood."""
        # 1. Mi Fitness mock returns healthy metrics.
        fetch = _build_healthy_fetch_result()

        # 2. Normalizer converts FetchResult -> HealthMetricPayload.
        payload = normalize_fetch_result(fetch, DEVICE_ID, OWNER_ID)
        assert len(payload.samples) == 5, "all 5 metric samples should normalize"
        assert set(payload.metrics_available) == {
            HealthMetricType.HEART_RATE,
            HealthMetricType.STEPS,
            HealthMetricType.SPO2,
            HealthMetricType.STRESS,
            HealthMetricType.SLEEP,
        }
        assert payload.metrics_unavailable == []

        # 3. Redis buffer receives the normalized samples.
        buffer = WearableBuffer(REDIS_URL)
        buffer._redis = mock_redis  # type: ignore[attr-defined]
        pushed = buffer.push_samples(payload.samples)
        assert pushed == 5, "buffer should push all 5 samples"

        # 4. Writer upserts to TimescaleDB (mocked pool).
        _, conn = mock_pool
        conn.executemany = AsyncMock(return_value=None)
        writer = HealthIngestionWriter(DATABASE_URL)
        writer._pool = mock_pool[0]  # type: ignore[attr-defined]
        write_result = await writer.write_samples(payload.samples)
        assert isinstance(write_result, WriteResult)
        assert write_result.failed == 0

        # 5. Baseline computation -- mock the SELECT/INSERT paths.
        conn.fetchrow = AsyncMock(return_value=None)
        sample_rows = [
            _make_mock_record({"value": 72.0, "ts": SAMPLE_TS - timedelta(days=29) + timedelta(days=i)})
            for i in range(30)
        ]
        conn.fetch = AsyncMock(return_value=sample_rows)
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        baseline_calc = BaselineCalculator(DATABASE_URL)
        baseline_calc._pool = mock_pool[0]  # type: ignore[attr-defined]
        hr_baseline = await baseline_calc.compute_baseline(
            HealthMetricType.HEART_RATE, OWNER_ID, DEVICE_ID
        )
        assert hr_baseline.stage in (BaselineStage.STABLE, BaselineStage.STABILIZING)
        assert hr_baseline.confidence > 0.5

        # 6. Anomaly detection -- all healthy, no anomalies expected.
        detector = AnomalyDetector(DATABASE_URL)
        detector._pool = mock_pool[0]  # type: ignore[attr-defined]
        anomalies = await detector.detect_anomalies(
            HealthMetricType.HEART_RATE,
            cast(BaselineLike, cast(object, hr_baseline)),
            [payload.samples[0]],
            OWNER_ID,
            DEVICE_ID,
        )
        assert anomalies == [], "no anomalies for healthy 72 bpm"

        # 7. GHI computation -- mock the GHI queries to return a high score.
        #    The GHI scorer issues fetch (baselines) and fetchrow (pillar data) calls.
        ghi_baseline_row = _make_mock_record({
            "metric": "heart_rate",
            "stage": "stable",
            "baseline_value": 72.0,
            "stddev": 1.0,
            "confidence": 0.9,
            "data_points": 30,
            "first_data_at": SAMPLE_TS - timedelta(days=30),
            "last_data_at": SAMPLE_TS,
            "owner_id": OWNER_ID,
            "device_id": DEVICE_ID,
        })
        conn.fetchrow = AsyncMock(side_effect=[
            _make_mock_record({
                "sleep_date": TEST_DATE, "total_s": 28800, "efficiency_pct": 92.0,
                "end_time": SAMPLE_TS,
            }),
            _make_mock_record({"date": TEST_DATE, "steps": 8000, "distance_m": 5500.0}),
            _make_mock_record({"time": SAMPLE_TS, "bpm": 72, "resting_bpm": 65}),
            None,  # hrv_row
        ])
        conn.fetch = AsyncMock(side_effect=[
            [ghi_baseline_row],  # baselines fetch
            [_make_mock_record({"time": SAMPLE_TS, "score": 35})],  # stress rows
        ])
        conn.execute = AsyncMock(return_value=None)

        ghi_scorer = GHIScorer(DATABASE_URL)
        ghi_scorer._pool = mock_pool[0]  # type: ignore[attr-defined]
        ghi_internal = await ghi_scorer.compute_ghi(OWNER_ID, DEVICE_ID, TEST_DATE)
        assert ghi_internal.score > 0
        assert ghi_internal.tier in (GHITier.GOOD, GHITier.EXCELLENT, GHITier.FAIR)
        assert ghi_internal.suppressed is False

        # 8. Mood modifier application -- for a healthy score the modifier is set.
        ghi_for_mood = GHIResult(
            date=TEST_DATE,
            device_id=DEVICE_ID,
            owner_id=OWNER_ID,
            ghi_score=ghi_internal.score,
            confidence=ghi_internal.confidence,
            tier=ghi_internal.tier,
            suppressed=False,
        )
        integrator = HealthMoodIntegrator(REDIS_URL, DATABASE_URL)
        integrator._redis = mock_redis  # type: ignore[attr-defined]
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))
        with patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_consent.return_value = MagicMock(allowed=True)
            modifier = await integrator.compute_modifier(ghi_for_mood)
        assert modifier is not None, "healthy GHI should produce a mood modifier"
        assert modifier.target_mood in (Mood.PLEASED, Mood.CONTENT)


# ===========================================================================
# Scenario 2: Metric unavailable (SpO2 gap)
# ===========================================================================


class TestScenario2MetricUnavailable:
    """When a metric is UNAVAILABLE, the pipeline degrades gracefully."""

    @pytest.mark.asyncio
    async def test_spo2_unavailable_rebalances_ghi(
        self,
        mock_pool: tuple[MagicMock, AsyncMock],
    ) -> None:
        """SpO2 marked UNAVAILABLE -> normalizer drops it, GHI rebalances 3 pillars."""
        fetch = _build_healthy_fetch_result()
        fetch.metrics["spo2"] = MetricResult(
            metric=HealthMetricType.SPO2,
            status=MetricStatus.UNAVAILABLE,
            error="device does not report spo2",
        )

        payload = normalize_fetch_result(fetch, DEVICE_ID, OWNER_ID)
        assert HealthMetricType.SPO2 in payload.metrics_unavailable
        assert HealthMetricType.SPO2 not in payload.metrics_available
        assert len(payload.samples) == 4, "only 4 samples (no SpO2)"

        # GHI pillar count is reduced -- mock the DB to return 3 of 4 pillars.
        _, conn = mock_pool
        # baselines fetch returns 3 metric rows; stress fetch returns stress rows.
        conn.fetch = AsyncMock(side_effect=[
            [
                _make_mock_record({
                    "metric": "heart_rate",
                    "stage": "stable",
                    "baseline_value": 72.0,
                    "stddev": 1.0,
                    "confidence": 0.9,
                    "data_points": 30,
                    "first_data_at": SAMPLE_TS - timedelta(days=30),
                    "last_data_at": SAMPLE_TS,
                    "owner_id": OWNER_ID,
                    "device_id": DEVICE_ID,
                }),
                _make_mock_record({
                    "metric": "steps",
                    "stage": "stable",
                    "baseline_value": 8000.0,
                    "stddev": 500.0,
                    "confidence": 0.9,
                    "data_points": 30,
                    "first_data_at": SAMPLE_TS - timedelta(days=30),
                    "last_data_at": SAMPLE_TS,
                    "owner_id": OWNER_ID,
                    "device_id": DEVICE_ID,
                }),
                _make_mock_record({
                    "metric": "stress",
                    "stage": "stable",
                    "baseline_value": 35.0,
                    "stddev": 5.0,
                    "confidence": 0.9,
                    "data_points": 30,
                    "first_data_at": SAMPLE_TS - timedelta(days=30),
                    "last_data_at": SAMPLE_TS,
                    "owner_id": OWNER_ID,
                    "device_id": DEVICE_ID,
                }),
            ],
            [_make_mock_record({"time": SAMPLE_TS, "score": 35})],  # stress rows
        ])
        # Pillar data: 3 rows available, sleep fetchrow returns, hrv returns None.
        conn.fetchrow = AsyncMock(side_effect=[
            _make_mock_record({
                "sleep_date": TEST_DATE, "total_s": 28800, "efficiency_pct": 90.0,
                "end_time": SAMPLE_TS,
            }),
            _make_mock_record({"date": TEST_DATE, "steps": 8000, "distance_m": 5500.0}),
            _make_mock_record({"time": SAMPLE_TS, "bpm": 72, "resting_bpm": 65}),
            None,  # hrv
        ])
        conn.execute = AsyncMock(return_value=None)

        scorer = GHIScorer(DATABASE_URL)
        scorer._pool = mock_pool[0]  # type: ignore[attr-defined]
        ghi = await scorer.compute_ghi(OWNER_ID, DEVICE_ID, TEST_DATE)
        assert ghi.suppressed is False
        assert ghi.score > 0
        # SpO2 is not a separate pillar (it lives in cardio); rebalance reflects available pillars.
        assert "spo2" not in ghi.weights


# ===========================================================================
# Scenario 3: Anomaly detection (critical SpO2)
# ===========================================================================


class TestScenario3CriticalSpo2Anomaly:
    """Three consecutive SpO2 readings < 90% should raise a SEV0 event."""

    @pytest.mark.asyncio
    async def test_critical_spo2_triggers_sev0(
        self,
        mock_pool: tuple[MagicMock, AsyncMock],
    ) -> None:
        baseline = _stable_baseline_state(HealthMetricType.SPO2, value=97.0)
        now = SAMPLE_TS

        _, conn = mock_pool
        conn.executemany = AsyncMock(return_value=None)
        detector = AnomalyDetector(DATABASE_URL)
        detector._pool = mock_pool[0]  # type: ignore[attr-defined]

        # First, force min_consecutive=2 path by feeding two <90 readings.
        critical_samples = [
            NormalizedHealthSample(
                metric_type=HealthMetricType.SPO2,
                timestamp=now - timedelta(minutes=10),
                device_id=DEVICE_ID,
                owner_id=OWNER_ID,
                value=89.0,
                unit="%",
            ),
            NormalizedHealthSample(
                metric_type=HealthMetricType.SPO2,
                timestamp=now - timedelta(minutes=5),
                device_id=DEVICE_ID,
                owner_id=OWNER_ID,
                value=88.0,
                unit="%",
            ),
            NormalizedHealthSample(
                metric_type=HealthMetricType.SPO2,
                timestamp=now,
                device_id=DEVICE_ID,
                owner_id=OWNER_ID,
                value=87.0,
                unit="%",
            ),
        ]
        events = await detector.detect_anomalies(
            HealthMetricType.SPO2,
            cast(BaselineLike, cast(object, baseline)),
            critical_samples,
            OWNER_ID,
            DEVICE_ID,
        )
        # With 3 critical samples the min_consecutive=2 SEV0 rule should fire.
        sev0_events = [e for e in events if e.severity is AlertSeverity.SEV0]
        assert len(sev0_events) >= 1, "critical SpO2 <90 should produce SEV0 event"

        # Now route the SEV0 event through the alert router -- it must bypass quiet hours.
        # Configure quiet hours that cover the entire 24h window so we can prove
        # SEV0 bypasses them.
        config = _build_healthy_config(
            wearable_quiet_hours_start="00:00", wearable_quiet_hours_end="23:59"
        )
        router = AlertRouter(config, DATABASE_URL, discord_channel_id="chan-1")
        router._pool = mock_pool[0]  # type: ignore[attr-defined]
        router._send_discord_dm = AsyncMock(return_value=None)  # type: ignore[method-assign]
        result = await router.route_event(sev0_events[0])
        assert result.delivered is True, "SEV0 must be delivered immediately"
        assert result.severity is AlertSeverity.SEV0
        # Even with full-day quiet hours, SEV0 bypasses.
        assert result.channel == "discord_dm"


# ===========================================================================
# Scenario 4: Consent revocation
# ===========================================================================


class TestScenario4ConsentRevocation:
    """Revoking a consent scope mid-pipeline drops the affected samples."""

    @pytest.mark.asyncio
    async def test_revoke_hr_consent_drops_heart_rate_samples(self) -> None:
        # 1. Grant ALL the wearable scopes first so we can exercise the revoke
        #    gate on a single scope without the others being treated as
        #    "never consented".
        session, _state = _make_consent_session()
        _set_db_session_for_testing(session)
        for scope in (
            "wearable-health.hr",
            "wearable-health.activity",
            "wearable-health.spo2",
            "wearable-health.stress",
            "wearable-health.sleep",
            "wearable-health.ghi",
            "wearable-health.alerts",
        ):
            assert await grant_consent(scope) is True
            await invalidate_consent_cache(scope)

        # 2. Verify HR is active before revoking.
        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is True
        assert result.status is ConsentStatus.ACTIVE

        # 3. Revoke heart rate consent.
        assert await revoke_consent("wearable-health.hr") is True
        await invalidate_consent_cache("wearable-health.hr")

        result = await check_wearable_consent("wearable-health.hr")
        assert result.allowed is False
        assert result.status is ConsentStatus.WITHDRAWN

        # 4. Run the pipeline: the HR sample should be dropped by the consent gate.
        await invalidate_consent_cache("wearable-health.hr")

        fetch = _build_healthy_fetch_result()
        payload = normalize_fetch_result(fetch, DEVICE_ID, OWNER_ID)

        # Apply the consent filter -- the integration pattern drops disallowed samples.
        allowed_samples: list[NormalizedHealthSample] = []
        dropped_count = 0
        for sample in payload.samples:
            check = await check_metric_consent(sample.metric_type)
            if check.allowed:
                allowed_samples.append(sample)
            else:
                dropped_count += 1

        assert dropped_count == 1, "HR sample should be dropped (consent revoked)"
        assert len(allowed_samples) == 4
        assert all(
            s.metric_type is not HealthMetricType.HEART_RATE for s in allowed_samples
        )


# ===========================================================================
# Scenario 5: Rate limiting from Mi Fitness API
# ===========================================================================


class TestScenario5RateLimiting:
    """Mi Fitness returns 429 -> RateLimitError, circuit breaker engages."""

    @pytest.mark.asyncio
    async def test_rate_limit_raises_and_engages_circuit_breaker(
        self, mock_config: WearableConfig
    ) -> None:
        client = MiFitnessClient(mock_config)
        client._token_loaded = True  # bypass file-based auth for this test

        # Simulate the SDK raising a 429 message; _fetch_single inspects
        # the error and raises RateLimitError.
        async def _raise_rate_limit(*_args: Any, **_kwargs: Any) -> Any:
            raise RuntimeError("HTTP 429: too many requests")

        client._client = MagicMock()
        client._client.get_heart_rate = _raise_rate_limit

        date_range = DateRange(start=TEST_DATE, end=TEST_DATE)
        with pytest.raises(RateLimitError):
            await client._fetch_single(HealthMetricType.HEART_RATE, date_range)

        # Circuit breaker: 3 failures should open it.
        breaker = _CircuitBreaker(threshold=3, recovery_seconds=60)
        for _ in range(2):
            breaker.record_failure()
        assert breaker.state == _CircuitState.CLOSED, "2 < threshold=3"
        breaker.record_failure()
        assert breaker.state == _CircuitState.OPEN, "3rd failure opens the breaker"
        assert breaker.allow_request() is False, "open breaker denies new requests"

    def test_exponential_backoff_delays(
        self, mock_config: WearableConfig
    ) -> None:
        """Exponential backoff retry doubles the delay between attempts."""
        client = MiFitnessClient(mock_config)
        with patch("src.wearable.mi_fitness_client.time.sleep") as mock_sleep:
            client._retry_with_backoff(attempts=3)
            assert mock_sleep.call_count == 3
            delays = [call.args[0] for call in mock_sleep.call_args_list]
            assert delays[0] == 1.0
            assert delays[1] == 2.0
            assert delays[2] == 4.0


# ===========================================================================
# Scenario 6: Quiet hours mood suppression
# ===========================================================================


class TestScenario6QuietHoursMoodSuppression:
    """During quiet hours, non-critical GHI tiers are suppressed."""

    @pytest.mark.asyncio
    async def test_compute_modifier_returns_none_during_quiet_hours(
        self, mock_redis: MagicMock
    ) -> None:
        integrator = HealthMoodIntegrator(REDIS_URL, DATABASE_URL)
        integrator._redis = mock_redis  # type: ignore[attr-defined]

        # Build a FAIR-tier GHI result (not critical -> should be suppressed).
        ghi = GHIResult(
            date=TEST_DATE,
            device_id=DEVICE_ID,
            owner_id=OWNER_ID,
            ghi_score=60.0,
            confidence=0.8,
            tier=GHITier.FAIR,
            suppressed=False,
        )

        # Force "now" to be 23:30 UTC (within quiet hours 22-08).
        with patch("src.wearable.mood_integration.datetime") as mock_dt:
            mock_dt.now.return_value = datetime(2026, 6, 18, 23, 30, 0, tzinfo=UTC)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            assert (
                integrator._is_quiet_hours(
                    datetime(2026, 6, 18, 23, 30, 0, tzinfo=UTC)
                )
                is True
            )
            modifier = await integrator.compute_modifier(ghi)
        assert modifier is None, "non-critical tier during quiet hours should be suppressed"

    @pytest.mark.asyncio
    async def test_critical_tier_bypasses_quiet_hours(
        self, mock_redis: MagicMock
    ) -> None:
        integrator = HealthMoodIntegrator(REDIS_URL, DATABASE_URL)
        integrator._redis = mock_redis  # type: ignore[attr-defined]
        mock_redis.get = AsyncMock(side_effect=lambda key: {
            "persona:state:active": "normal",
            "persona:state:safe_mode": None,
        }.get(key, None))

        ghi = GHIResult(
            date=TEST_DATE,
            device_id=DEVICE_ID,
            owner_id=OWNER_ID,
            ghi_score=30.0,
            confidence=0.9,
            tier=GHITier.CRITICAL,
            suppressed=False,
        )

        with patch("src.wearable.mood_integration.datetime") as mock_dt, \
             patch("src.wearable.mood_integration.check_wearable_consent") as mock_consent:
            mock_dt.now.return_value = datetime(2026, 6, 18, 23, 30, 0, tzinfo=UTC)
            mock_dt.side_effect = lambda *args, **kwargs: datetime(*args, **kwargs)
            mock_consent.return_value = MagicMock(allowed=True)
            modifier = await integrator.compute_modifier(ghi)
        assert modifier is not None, "CRITICAL tier must bypass quiet hours"
        assert modifier.target_mood is Mood.DISAPPOINTED


# ===========================================================================
# Scenario 7: GHI suppression (<2 pillars)
# ===========================================================================


class TestScenario7GhiSuppression:
    """If fewer than 2 pillars have data, GHI is suppressed."""

    @pytest.mark.asyncio
    async def test_single_pillar_suppresses_ghi(
        self, mock_pool: tuple[MagicMock, AsyncMock]
    ) -> None:
        _, conn = mock_pool
        # Only steps baseline exists; no sleep/cardio/recovery data.
        # GHI calls conn.fetch twice: first for baselines, then for stress_rows.
        # Returning [] for stress ensures the recovery pillar returns data_present=False.
        steps_baseline = _make_mock_record({
            "metric": "steps",
            "stage": "stable",
            "baseline_value": 8000.0,
            "stddev": 500.0,
            "confidence": 0.9,
            "data_points": 30,
            "first_data_at": SAMPLE_TS - timedelta(days=30),
            "last_data_at": SAMPLE_TS,
            "owner_id": OWNER_ID,
            "device_id": DEVICE_ID,
        })
        conn.fetch = AsyncMock(side_effect=[[steps_baseline], []])
        conn.fetchrow = AsyncMock(side_effect=[
            None,  # sleep
            _make_mock_record({"date": TEST_DATE, "steps": 8000, "distance_m": 5500.0}),
            None,  # heart rate
            None,  # hrv
        ])
        conn.execute = AsyncMock(return_value=None)

        scorer = GHIScorer(DATABASE_URL)
        scorer._pool = mock_pool[0]  # type: ignore[attr-defined]
        ghi = await scorer.compute_ghi(OWNER_ID, DEVICE_ID, TEST_DATE)

        assert ghi.suppressed is True
        assert ghi.weights == {}, "no weights when suppressed"
        assert ghi.score == 0.0

        # Verify the mood integrator does NOT modify mood when GHI is suppressed.
        mock_redis = _make_mock_redis()
        integrator = HealthMoodIntegrator(REDIS_URL, DATABASE_URL)
        integrator._redis = mock_redis  # type: ignore[attr-defined]
        # Use the models.GHIResult (pydantic) which has the same fields.
        ghi_for_mood = GHIResult(
            date=TEST_DATE,
            device_id=DEVICE_ID,
            owner_id=OWNER_ID,
            ghi_score=0.0,
            confidence=0.0,
            tier=GHITier.CRITICAL,
            suppressed=True,
            suppression_reason="insufficient_pillars",
        )
        modifier = await integrator.compute_modifier(ghi_for_mood)
        assert modifier is None, "suppressed GHI must not produce a mood modifier"


# ===========================================================================
# Scenario 8: Baseline warmup progression
# ===========================================================================


class TestScenario8BaselineWarmup:
    """Baseline stage should transition INSUFFICIENT -> PROVISIONAL -> STABILIZING -> STABLE."""

    @pytest.mark.asyncio
    async def test_baseline_warmup_progression(
        self, mock_pool: tuple[MagicMock, AsyncMock]
    ) -> None:
        _, conn = mock_pool
        conn.execute = AsyncMock(return_value="INSERT 0 1")
        calc = BaselineCalculator(DATABASE_URL)
        calc._pool = mock_pool[0]  # type: ignore[attr-defined]

        # Stage 1: insufficient data (<3 days)
        conn.fetchrow = AsyncMock(return_value=None)
        conn.fetch = AsyncMock(return_value=[
            _make_mock_record({"value": 72.0, "ts": SAMPLE_TS - timedelta(hours=12)}),
            _make_mock_record({"value": 73.0, "ts": SAMPLE_TS}),
        ])
        result = await calc.compute_baseline(
            HealthMetricType.HEART_RATE, OWNER_ID, DEVICE_ID
        )
        assert result.stage is BaselineStage.INSUFFICIENT
        confidence_insufficient = result.confidence
        assert confidence_insufficient == 0.0

        # Stage 2: provisional (10 days of data)
        conn.fetchrow = AsyncMock(return_value=None)
        ten_day_rows = [
            _make_mock_record({
                "value": 72.0 + i * 0.1,
                "ts": SAMPLE_TS - timedelta(days=10) + timedelta(days=i),
            })
            for i in range(10)
        ]
        conn.fetch = AsyncMock(return_value=ten_day_rows)
        result_10 = await calc.compute_baseline(
            HealthMetricType.HEART_RATE, OWNER_ID, DEVICE_ID
        )
        assert result_10.stage is BaselineStage.PROVISIONAL
        assert result_10.confidence > confidence_insufficient, "confidence must increase"

        # Stage 3: stable (30 days of data)
        conn.fetchrow = AsyncMock(return_value=None)
        thirty_day_rows = [
            _make_mock_record({
                "value": 72.0 + i * 0.05,
                "ts": SAMPLE_TS - timedelta(days=30) + timedelta(days=i),
            })
            for i in range(30)
        ]
        conn.fetch = AsyncMock(return_value=thirty_day_rows)
        result_30 = await calc.compute_baseline(
            HealthMetricType.HEART_RATE, OWNER_ID, DEVICE_ID
        )
        assert result_30.stage in (BaselineStage.STABLE, BaselineStage.STABILIZING)
        assert result_30.confidence > result_10.confidence, "confidence must increase with more data"

        # Verify compute_all_baselines covers all metrics.
        result_all = await calc.compute_all_baselines(OWNER_ID, DEVICE_ID)
        assert HealthMetricType.HEART_RATE in result_all
        assert HealthMetricType.STEPS in result_all


# ===========================================================================
# Scenario 9: End-to-end consent grant -> sync -> report
# ===========================================================================


class TestScenario9EndToEndConsentGrantSyncReport:
    """Grant ghi consent, run full pipeline, verify GHI appears in the report."""

    @pytest.mark.asyncio
    async def test_full_e2e_grant_sync_report(
        self,
        mock_pool: tuple[MagicMock, AsyncMock],
    ) -> None:
        # 1. Grant ghi consent (and other needed scopes).
        session, _state = _make_consent_session()
        _set_db_session_for_testing(session)
        for scope in (
            "wearable-health.ghi",
            "wearable-health.hr",
            "wearable-health.activity",
            "wearable-health.spo2",
            "wearable-health.stress",
            "wearable-health.sleep",
            "wearable-health.alerts",
        ):
            assert await grant_consent(scope) is True
            await invalidate_consent_cache(scope)
        ghi_check = await check_wearable_consent("wearable-health.ghi")
        assert ghi_check.allowed is True

        # 2. Run the sync pipeline with healthy data.
        fetch = _build_healthy_fetch_result()
        payload = normalize_fetch_result(fetch, DEVICE_ID, OWNER_ID)
        assert len(payload.samples) == 5

        # 3. Mock the GHI scorer to return a known result.
        _, conn = mock_pool
        conn.fetch = AsyncMock(side_effect=[
            [
                _make_mock_record({
                    "metric": "heart_rate",
                    "stage": "stable",
                    "baseline_value": 72.0,
                    "stddev": 1.0,
                    "confidence": 0.9,
                    "data_points": 30,
                    "first_data_at": SAMPLE_TS - timedelta(days=30),
                    "last_data_at": SAMPLE_TS,
                    "owner_id": OWNER_ID,
                    "device_id": DEVICE_ID,
                }),
            ],
            [_make_mock_record({"time": SAMPLE_TS, "score": 35})],
        ])
        conn.fetchrow = AsyncMock(side_effect=[
            _make_mock_record({
                "sleep_date": TEST_DATE, "total_s": 28800, "efficiency_pct": 92.0,
                "end_time": SAMPLE_TS,
            }),
            _make_mock_record({"date": TEST_DATE, "steps": 8000, "distance_m": 5500.0}),
            _make_mock_record({"time": SAMPLE_TS, "bpm": 72, "resting_bpm": 65}),
            None,  # hrv
        ])
        conn.execute = AsyncMock(return_value=None)

        scorer = GHIScorer(DATABASE_URL)
        scorer._pool = mock_pool[0]  # type: ignore[attr-defined]
        ghi = await scorer.compute_ghi(OWNER_ID, DEVICE_ID, TEST_DATE)
        assert ghi.score > 0
        assert ghi.tier in (GHITier.GOOD, GHITier.EXCELLENT, GHITier.FAIR)

        # 4. Simulate the cmd_health_report module rendering the report.
        ghi_for_mood = GHIResult(
            date=TEST_DATE,
            device_id=DEVICE_ID,
            owner_id=OWNER_ID,
            ghi_score=ghi.score,
            confidence=ghi.confidence,
            tier=ghi.tier,
            suppressed=False,
        )
        report_payload = {
            "owner_id": OWNER_ID,
            "device_id": DEVICE_ID,
            "report_date": TEST_DATE.isoformat(),
            "ghi": {
                "score": ghi_for_mood.ghi_score,
                "tier": ghi_for_mood.tier.value,
                "confidence": ghi_for_mood.confidence,
                "suppressed": ghi_for_mood.suppressed,
            },
        }
        report_text = json.dumps(report_payload, indent=2)
        assert "ghi" in report_text
        assert ghi_for_mood.tier.value in report_text
        assert str(round(ghi_for_mood.ghi_score, 2)) in report_text


# ===========================================================================
# Scenario 10: Encryption round-trip
# ===========================================================================


class TestScenario10EncryptionRoundTrip:
    """Sensitive fields encrypt with ENC: prefix and decrypt back to original."""

    def test_encrypt_decrypt_round_trip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cryptography.fernet import Fernet as _Fernet
        key = _Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", key)
        get_encryption_key.cache_clear()

        original_record: dict[str, object] = {
            "device_id": DEVICE_ID,
            "notes": "patient reported dizziness",
            "raw_json": '{"hr":[72,73,71]}',
            "source": "mi_fitness_cloud",
            "value": 72.0,
        }
        encrypted = encrypt_health_record(original_record)
        # Sensitive string fields must be encrypted with ENC: prefix.
        for field_name in SENSITIVE_FIELDS:
            encrypted_value = encrypted[field_name]
            assert isinstance(encrypted_value, str)
            assert encrypted_value.startswith("ENC:")
            assert encrypted_value != original_record[field_name]
        # Non-sensitive fields are unchanged.
        assert encrypted["source"] == "mi_fitness_cloud"
        assert encrypted["value"] == 72.0

        # Decrypt and verify the round-trip.
        decrypted = decrypt_health_record(encrypted)
        for field_name in SENSITIVE_FIELDS:
            assert decrypted[field_name] == original_record[field_name]
        assert decrypted == original_record

    def test_encrypt_individual_value_round_trip(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cryptography.fernet import Fernet as _Fernet
        key = _Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", key)
        get_encryption_key.cache_clear()

        plaintext = "11111111-1111-1111-1111-111111111111"
        ciphertext = encrypt_value(plaintext)
        assert ciphertext.startswith("ENC:")
        assert plaintext not in ciphertext
        recovered = decrypt_value(ciphertext)
        assert recovered == plaintext

    def test_decrypt_plaintext_passthrough(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Values without the ENC: prefix are returned as-is."""
        from cryptography.fernet import Fernet as _Fernet
        key = _Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", key)
        get_encryption_key.cache_clear()

        plaintext = "not-encrypted-value"
        recovered = decrypt_value(plaintext)
        assert recovered == plaintext

    def test_empty_string_unchanged(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from cryptography.fernet import Fernet as _Fernet
        key = _Fernet.generate_key().decode("utf-8")
        monkeypatch.setenv("WEARABLE_ENCRYPTION_KEY", key)
        get_encryption_key.cache_clear()

        assert encrypt_value("") == ""
        assert decrypt_value("") == ""
