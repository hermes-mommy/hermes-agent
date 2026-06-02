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

__all__ = [
    "ClassificationResult",
    "ConsentCheckResult",
    "ConsentStatus",
    "ConfrontationDecision",
    "DataClassification",
    "ErrorResponse",
    "HMACVerification",
    "RedisSurveillanceBuffer",
    "ScanResult",
    "SurveillanceBuffer",
    "SurveillanceConsumer",
    "SurveillanceEventRequest",
    "SurveillanceEventResponse",
    "SurveillanceSafeModeGuard",
    "check_consent",
    "check_nonce",
    "classify_event",
    "create_buffer",
    "get_hmac_secret",
    "get_retention_days",
    "invalidate_cache",
    "redact_secrets",
    "scan_text",
    "surveillance_router",
    "validate_timestamp",
    "verify_hmac",
    "_map_event_to_scope",
]
