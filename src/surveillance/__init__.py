# src/surveillance module
"""Surveillance integration — event ingestion, classification, and safety gates."""
from __future__ import annotations

from src.surveillance.auth import HMACVerification, verify_hmac
from src.surveillance.classification import (
    ClassificationResult,
    DataClassification,
    classify_event,
    get_retention_days,
)
from src.surveillance.consent_gate import (
    ConsentCheckResult,
    ConsentStatus,
    check_consent,
    invalidate_cache,
)
from src.surveillance.consumer import SurveillanceConsumer, _map_event_to_scope
from src.surveillance.models import (
    ErrorResponse,
    SurveillanceEventRequest,
    SurveillanceEventResponse,
)
from src.surveillance.redis_buffer import (
    RedisSurveillanceBuffer,
    SurveillanceBuffer,
    create_buffer,
)
from src.surveillance.replay import check_nonce, validate_timestamp
from src.surveillance.router import surveillance_router
from src.surveillance.safe_mode import ConfrontationDecision, SurveillanceSafeModeGuard
from src.surveillance.secret_scanner import ScanResult, redact_secrets, scan_text
from src.surveillance.secrets import get_hmac_secret
from src.surveillance.retention import (
    CHUNK_INTERVAL_DAYS,
    COMPRESSION_AFTER_DAYS,
    RETENTION_AGGREGATED_DAYS,
    RETENTION_RAW_DAYS,
    RETENTION_SUMMARY_DAYS,
    RetentionTier,
    calculate_retention_until,
    get_retention_policy_summary,
)
from src.surveillance.retention import get_retention_days as get_tier_retention_days
from src.surveillance.timescale import IngestionResult, TimescaleIngester

__all__ = [
    "ClassificationResult",
    "ConsentCheckResult",
    "ConsentStatus",
    "ConfrontationDecision",
    "DataClassification",
    "ErrorResponse",
    "HMACVerification",
    "IngestionResult",
    "RedisSurveillanceBuffer",
    "RetentionTier",
    "ScanResult",
    "SurveillanceBuffer",
    "SurveillanceConsumer",
    "SurveillanceEventRequest",
    "SurveillanceEventResponse",
    "SurveillanceSafeModeGuard",
    "TimescaleIngester",
    "check_consent",
    "check_nonce",
    "CHUNK_INTERVAL_DAYS",
    "classify_event",
    "COMPRESSION_AFTER_DAYS",
    "create_buffer",
    "calculate_retention_until",
    "get_hmac_secret",
    "get_retention_days",
    "get_retention_policy_summary",
    "get_tier_retention_days",
    "invalidate_cache",
    "redact_secrets",
    "RETENTION_AGGREGATED_DAYS",
    "RETENTION_RAW_DAYS",
    "RETENTION_SUMMARY_DAYS",
    "scan_text",
    "surveillance_router",
    "validate_timestamp",
    "verify_hmac",
    "_map_event_to_scope",
]
