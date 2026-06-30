"""Sentry SDK integration for Guinevere.

Provides error tracking with mandatory PII protection.
send_default_pii MUST be False — this is a BLOCKING requirement.
DSN loaded from environment variable SENTRY_DSN (SOPS-decrypted at runtime).
Graceful degradation: if DSN not available, log info and continue.

P8-013: PII scrubber with before_send / before_breadcrumb callbacks.
REDACT_PATTERNS: safe-word, surveillance, intimate, api_key, email, credit card.
DROP_EVENT_PATHS: persona-safety, surveillance-raw, consent-revocation, hard-stop.
"""

from __future__ import annotations

import os
import re
from typing import Final

import structlog

logger = structlog.get_logger(__name__)

SEND_DEFAULT_PII: Final[bool] = False  # BLOCKING: never change to True
TRACES_SAMPLE_RATE: Final[float] = 0.1

# ── P8-013: PII Scrubber ──────────────────────────────────────────────────────

# Patterns that must be redacted from Sentry event values.
# ObsSpec §10 + Appendix G: no raw intimate/surveillance/safe-word/PII content.
REDACT_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"\b(safe[_\s-]?word|kasih\s+ruang|HARD\s+STOP)\b", re.IGNORECASE),
    re.compile(r"\b(surveillance|tasker_payload|android_event)\b", re.IGNORECASE),
    re.compile(r"\b(intimate|emotional_memory|inner_journal)\b", re.IGNORECASE),
    re.compile(r"\b(api[_\s-]?key|secret[_\s-]?key|token|password)\s*[:=]\s*\S+", re.IGNORECASE),
    re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),  # email
    re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),  # credit card
]

# Event categories/tags that must be dropped entirely (return None).
# These contain inherently sensitive data that must never reach Sentry.
DROP_EVENT_PATHS: Final[frozenset[str]] = frozenset({
    "persona-safety",
    "surveillance-raw",
    "consent-revocation",
    "hard-stop",
    "distress-protocol",
    "crisis-handling",
})

_REDACTED: Final[str] = "[REDACTED]"


def _redact_value(value: str) -> str:
    """Apply all redaction patterns to a string value."""
    result = value
    for pattern in REDACT_PATTERNS:
        result = pattern.sub(_REDACTED, result)
    return result


def _should_drop_event(event: dict) -> bool:  # type: ignore[type-arg]
    """Check if event should be dropped entirely based on sensitive categories."""
    # Check tags
    tags = event.get("tags", {})
    if isinstance(tags, dict):
        for tag_value in tags.values():
            if isinstance(tag_value, str) and tag_value.lower() in DROP_EVENT_PATHS:
                return True

    # Check extra/context
    extra = event.get("extra", {})
    if isinstance(extra, dict):
        for val in extra.values():
            if isinstance(val, str) and val.lower() in DROP_EVENT_PATHS:
                return True

    # Check breadcrumbs for sensitive categories
    breadcrumbs = event.get("breadcrumbs", {})
    if isinstance(breadcrumbs, dict):
        values = breadcrumbs.get("values", [])
        if isinstance(values, list):
            for crumb in values:
                if isinstance(crumb, dict):
                    category = crumb.get("category", "")
                    if isinstance(category, str) and category.lower() in DROP_EVENT_PATHS:
                        return True

    return False


def _redact_dict(d: dict) -> dict:  # type: ignore[type-arg]
    """Redact sensitive patterns from all string values in a dict."""
    result: dict = {}  # type: ignore[type-arg]
    for key, value in d.items():
        if isinstance(value, str):
            result[key] = _redact_value(value)
        elif isinstance(value, dict):
            result[key] = _redact_dict(value)
        elif isinstance(value, list):
            result[key] = [
                _redact_value(v) if isinstance(v, str)
                else _redact_dict(v) if isinstance(v, dict)
                else v
                for v in value
            ]
        else:
            result[key] = value
    return result


def before_send(event: dict, hint: dict) -> dict | None:  # type: ignore[type-arg]
    """Sentry before_send callback — scrub PII or drop sensitive events.

    Args:
        event: Sentry event dict.
        hint: Sentry hint dict (contains original exception).

    Returns:
        Scrubbed event dict, or None to drop the event entirely.
    """
    # Drop events matching sensitive categories
    if _should_drop_event(event):
        logger.warning(
            "sentry_event_dropped",
            extra={"reason": "sensitive_category"},
        )
        return None

    # Redact PII from event message
    if "message" in event and isinstance(event["message"], str):
        event["message"] = _redact_value(event["message"])

    # Redact PII from extra fields
    if "extra" in event and isinstance(event["extra"], dict):
        event["extra"] = _redact_dict(event["extra"])

    # Redact PII from request data (headers, body summaries — not raw)
    request = event.get("request", {})
    if isinstance(request, dict):
        if "headers" in request and isinstance(request["headers"], dict):
            request["headers"] = _redact_dict(request["headers"])
        if "data" in request and isinstance(request["data"], str):
            request["data"] = _redact_value(request["data"])

    # Redact PII from exception values
    exception = event.get("exception", {})
    if isinstance(exception, dict):
        values = exception.get("values", [])
        if isinstance(values, list):
            for exc in values:
                if isinstance(exc, dict) and "value" in exc:
                    if isinstance(exc["value"], str):
                        exc["value"] = _redact_value(exc["value"])

    return event


def before_breadcrumb(crumb: dict, hint: dict | None = None) -> dict | None:  # type: ignore[type-arg]
    """Sentry before_breadcrumb callback — scrub PII from breadcrumbs.

    Args:
        crumb: Breadcrumb dict.
        hint: Optional hint dict.

    Returns:
        Scrubbed breadcrumb dict, or None to drop the breadcrumb.
    """
    # Drop breadcrumbs from sensitive categories
    category = crumb.get("category", "")
    if isinstance(category, str) and category.lower() in DROP_EVENT_PATHS:
        return None

    # Redact PII from breadcrumb message
    if "message" in crumb and isinstance(crumb["message"], str):
        crumb["message"] = _redact_value(crumb["message"])

    # Redact PII from breadcrumb data
    if "data" in crumb and isinstance(crumb["data"], dict):
        crumb["data"] = _redact_dict(crumb["data"])

    return crumb


# ── End P8-013 Scrubber ───────────────────────────────────────────────────────


def init_sentry(
    *,
    environment: str = "production",
    release: str = "unknown",
) -> bool:
    """Initialize Sentry SDK with PII-safe configuration and P8-013 scrubber.

    Args:
        environment: Deployment environment label.
        release: Application version/release identifier.

    Returns:
        True if Sentry was initialized, False if DSN was not available.
    """
    dsn = os.environ.get("SENTRY_DSN", "")
    if not dsn:
        logger.info("sentry_dsn_not_configured", extra={"environment": environment})
        return False

    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        send_default_pii=SEND_DEFAULT_PII,
        traces_sample_rate=TRACES_SAMPLE_RATE,
        environment=environment,
        release=release,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
        ],
        before_send=before_send,
        before_breadcrumb=before_breadcrumb,
        extra={
            "environment": environment,
            "release": release,
            "send_default_pii": SEND_DEFAULT_PII,
        },
    )

    logger.info(
        "sentry_initialized",
        extra={
            "environment": environment,
            "release": release,
            "send_default_pii": SEND_DEFAULT_PII,
            "traces_sample_rate": TRACES_SAMPLE_RATE,
            "pii_scrubber_active": True,
        },
    )
    return True
