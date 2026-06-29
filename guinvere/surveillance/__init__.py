"""Surveillance subsystem — HMAC-verified event ingest, buffering, and storage.

Ports from src/surveillance/ (14 files) into 4 target files per r12.
Operator approval gating NOT ported per ADR-062.
"""

from guinevere.surveillance.buffer import (
    NullBuffer,
    RedisSurveillanceBuffer,
    SurveillanceBuffer,
    SurveillanceConsumer,
    create_buffer,
)
from guinevere.surveillance.receiver import (
    ClassificationResult,
    DataClassification,
    HMACVerification,
    SurveillanceEventRequest,
    SurveillanceEventResponse,
    SurveillanceReceiver,
    classify_event,
    get_hmac_secret,
    redact_secrets,
    scan_text,
    verify_hmac,
)
from guinevere.surveillance.storage import (
    CHUNK_INTERVAL_DAYS,
    COMPRESSION_AFTER_DAYS,
    RETENTION_AGGREGATED_DAYS,
    RETENTION_RAW_DAYS,
    RETENTION_SUMMARY_DAYS,
    IngestionResult,
    RetentionTier,
    TimescaleIngester,
    calculate_retention_until,
    get_retention_days,
    get_retention_policy_summary,
)

__all__ = [
    "ClassificationResult",
    "DataClassification",
    "HMACVerification",
    "NullBuffer",
    "RedisSurveillanceBuffer",
    "SurveillanceBuffer",
    "SurveillanceConsumer",
    "SurveillanceEventRequest",
    "SurveillanceEventResponse",
    "SurveillanceReceiver",
    "classify_event",
    "get_hmac_secret",
    "redact_secrets",
    "scan_text",
    "verify_hmac",
    "create_buffer",
    "CHUNK_INTERVAL_DAYS",
    "COMPRESSION_AFTER_DAYS",
    "RETENTION_AGGREGATED_DAYS",
    "RETENTION_RAW_DAYS",
    "RETENTION_SUMMARY_DAYS",
    "IngestionResult",
    "RetentionTier",
    "TimescaleIngester",
    "calculate_retention_until",
    "get_retention_days",
    "get_retention_policy_summary",
]
