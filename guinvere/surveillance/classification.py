"""Data classification module - tag surveillance events with security levels.

Maps surveillance event types to data classification levels (Internal,
Confidential, Restricted, Critical) along with purpose, retention class, access
policy, and encryption profile.

Classification values are consumed by:
- ClassificationMetaMixin columns (classification, purpose, retention_class,
  access_policy, encryption_profile)
- SurveillanceDataPolicy retention rules
- Encryption and access control layers

Design decisions:
- Fail-closed: unknown event types default to Confidential with transient
  retention and guinevere_core+faiz access.
- Enum-gated: classification is always an enum, never free-text.
- Structlog: classification decisions are logged at debug level.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Final

import structlog

logger = structlog.get_logger()


# ---------------------------------------------------------------------------
# DataClassification enum
# ---------------------------------------------------------------------------


class DataClassification(StrEnum):
    """Security classification levels for surveillance event data.

    Mirrors the ClassificationMetaMixin.classification column values.
    Four tiers: Internal, Confidential, Restricted, Critical.
    """

    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"
    CRITICAL = "Critical"


# ---------------------------------------------------------------------------
# ClassificationResult - frozen output from classify_event
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ClassificationResult:
    """Result of classifying a surveillance event.

    Attributes:
        classification: The security level (Internal, Confidential, Restricted,
            Critical).
        purpose: Why this event data is collected.
        retention_class: Retention tier (transient, short_raw, etc.).
        access_policy: Who may access this data.
        encryption_profile: Encryption strength applied (standard, enhanced,
            high, double_high).
    """

    classification: DataClassification
    purpose: str
    retention_class: str
    access_policy: str
    encryption_profile: str


# ---------------------------------------------------------------------------
# Event type -> classification mapping
# ---------------------------------------------------------------------------


EVENT_TYPE_CLASSIFICATION: Final[dict[str, ClassificationResult]] = {
    # -- Restricted (tier 3) ------------------------------------------------
    "app_usage": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "screen_state": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="activity_tracking",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "active_window": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "idle_time": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="activity_tracking",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    # -- Critical (tier 4) --------------------------------------------------
    "notification": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="context_awareness",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "browser": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "location": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="safety_geofencing",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "call_log": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="context_awareness",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "health": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="health_monitoring",
        retention_class="medium_operational",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "clipboard": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="secret_protection",
        retention_class="transient",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
    "screenshot": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="visual_context",
        retention_class="critical_media",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
    "camera": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="visual_context",
        retention_class="critical_media",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
}


# ---------------------------------------------------------------------------
# Classification function
# ---------------------------------------------------------------------------

_DEFAULT_CONFIDENTIAL: Final[ClassificationResult] = ClassificationResult(
    classification=DataClassification.CONFIDENTIAL,
    purpose="unknown",
    retention_class="transient",
    access_policy="guinevere_core+faiz",
    encryption_profile="enhanced",
)


def classify_event(event_type: str) -> ClassificationResult:
    """Classify a surveillance event type and return its classification result.

    Unknown event types are treated as Confidential (fail-closed) to ensure
    no new event type leaks data without explicit classification.

    Args:
        event_type: The event type string (e.g. "app_usage", "clipboard").

    Returns:
        ClassificationResult with classification, purpose, retention_class,
        access_policy, and encryption_profile.
    """
    result = EVENT_TYPE_CLASSIFICATION.get(event_type, _DEFAULT_CONFIDENTIAL)
    logger.debug(
        "event_classified",
        event_type=event_type,
        classification=result.classification.value,
        is_known=event_type in EVENT_TYPE_CLASSIFICATION,
    )
    return result


# ---------------------------------------------------------------------------
# Retention days helper
# ---------------------------------------------------------------------------

_RETENTION_DAYS: Final[dict[str, int]] = {
    "transient": 1,
    "short_raw": 7,
    "critical_media": 1,
    "medium_operational": 90,
    "long_term_curated": 365,
    "regulated_audit": 365,
    "formal_hold": 730,
}


def get_retention_days(retention_class: str) -> int:
    """Return the maximum retention period in days for a given retention class.

    Unknown retention classes default to 1 day (fail-closed).

    Args:
        retention_class: The retention class name (e.g. "short_raw", "transient").

    Returns:
        Retention period in days.
    """
    return _RETENTION_DAYS.get(retention_class, 1)
