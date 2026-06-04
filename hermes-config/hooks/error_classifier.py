#!/usr/bin/env python3
"""Error Classifier Hook — on_error (50ms, on_failure: warn).

Classifies runtime errors into categories for logging and alerting.
Never blocks — this is a classification-only hook (on_failure: warn).

Categories:
  - transient:   Retry is safe (timeout, connection drop, rate limit)
  - safety:      Safety-critical, escalate immediately
  - infrastructure: Service down, alert on-call

Exit codes:
  0 = classified (always — never blocks)
"""

from __future__ import annotations

import re
import sys
import time
from typing import Final

from _hook_utils import read_stdin_json, setup_logger, write_stdout_json

_log = setup_logger("error_classifier")

# ── Classification Rules ──────────────────────────────────────────────────────

# Transient errors — safe to retry
_TRANSIENT_PATTERNS: Final[list[tuple[str, re.Pattern[str], str]]] = [
    (
        "timeout",
        re.compile(r"(?:time\s*out|timed?\s*out|deadline\s*exceeded|TimeoutError)", re.IGNORECASE),
        "low",
    ),
    (
        "rate_limit",
        re.compile(r"(?:rate\s*limit|too\s+many\s+requests|429|quota\s+exceeded)", re.IGNORECASE),
        "low",
    ),
    (
        "connection_reset",
        re.compile(r"(?:connection\s+(?:reset|refused|dropped|closed)|ECONNRESET|ECONNREFUSED)", re.IGNORECASE),
        "medium",
    ),
    (
        "temporary_failure",
        re.compile(r"(?:temporary|transient|try\s+again|later|retry)", re.IGNORECASE),
        "low",
    ),
    (
        "network",
        re.compile(r"(?:network\s+(?:error|unreachable|failure)|DNS|ENOTFOUND|EHOSTUNREACH)", re.IGNORECASE),
        "medium",
    ),
]

# Safety-critical errors — escalate immediately
_SAFETY_PATTERNS: Final[list[tuple[str, re.Pattern[str], str]]] = [
    (
        "hook_system_failure",
        re.compile(r"(?:hook\s+(?:system|execution|chain|pipeline)\s+(?:failure|error|crash|broken))", re.IGNORECASE),
        "high",
    ),
    (
        "safety_bypass_attempt",
        re.compile(r"(?:safety\s+(?:bypass|override|disabled|turned\s+off|circumvented))", re.IGNORECASE),
        "high",
    ),
    (
        "consent_breach",
        re.compile(r"(?:consent\s+(?:breach|violation|bypass|override|ignored))", re.IGNORECASE),
        "high",
    ),
    (
        "persona_escalation",
        re.compile(r"(?:yandere\s+(?:level|escalation)\s+(?:6|maximum|uncontrolled)|F-0[1-9]|F-1[0-5]\s+triggered)", re.IGNORECASE),
        "high",
    ),
    (
        "unauthorized_tool",
        re.compile(r"(?:unauthorized|forbidden|prohibited)\s+(?:tool|command|action|operation)", re.IGNORECASE),
        "high",
    ),
    (
        "memory_corruption",
        re.compile(r"(?:memory\s+(?:corruption|poison|tamper|injection))", re.IGNORECASE),
        "high",
    ),
]

# Infrastructure errors — service down, alert
_INFRA_PATTERNS: Final[list[tuple[str, re.Pattern[str], str]]] = [
    (
        "redis_down",
        re.compile(r"(?:redis\s+(?:connection|unavailable|down|refused|cannot\s+connect))", re.IGNORECASE),
        "high",
    ),
    (
        "postgresql_down",
        re.compile(r"(?:postgres(?:ql)?\s+(?:connection|unavailable|down|refused|cannot\s+connect))", re.IGNORECASE),
        "high",
    ),
    (
        "disk_full",
        re.compile(r"(?:disk\s+full|no\s+space|ENOSPC|out\s+of\s+(?:disk\s+)?space)", re.IGNORECASE),
        "high",
    ),
    (
        "oom",
        re.compile(r"(?:out\s+of\s+memory|OOM|memory\s+exhausted|MemoryError)", re.IGNORECASE),
        "high",
    ),
    (
        "service_down",
        re.compile(r"(?:service\s+(?:unavailable|down|stopped|crashed)|503|gateway\s+timeout)", re.IGNORECASE),
        "high",
    ),
]

# Error type keyword mapping (fast path before regex)
_ERROR_TYPE_MAP: Final[dict[str, tuple[str, str, str]]] = {
    "TimeoutError": ("transient", "timeout_error", "low"),
    "ConnectionError": ("transient", "connection_error", "medium"),
    "ConnectionRefusedError": ("transient", "connection_refused", "medium"),
    "RateLimitError": ("transient", "rate_limit", "low"),
    "HTTPError": ("transient", "http_error", "medium"),
    "SafetyError": ("safety", "safety_error", "high"),
    "YandereSafetyError": ("safety", "yandere_safety_error", "high"),
    "PersonaDriftError": ("safety", "persona_drift_error", "high"),
    "ConsentError": ("safety", "consent_error", "high"),
    "ForbiddenPatternError": ("safety", "forbidden_pattern", "high"),
    "MemoryError": ("infrastructure", "memory_error", "high"),
    "DiskFullError": ("infrastructure", "disk_full", "high"),
    "DatabaseError": ("infrastructure", "database_error", "high"),
    "RedisError": ("infrastructure", "redis_error", "high"),
    "SystemError": ("infrastructure", "system_error", "medium"),
}


# ── Classification ────────────────────────────────────────────────────────────


def classify_error(error_text: str, error_type: str) -> dict[str, str]:
    """Classify an error into transient, safety, or infrastructure.

    Args:
        error_text: The full error message or traceback.
        error_type: The error type/class name (e.g. "TimeoutError").

    Returns:
        Dictionary with ``classification``, ``severity``, and optional ``subtype``.
    """
    # 1. Fast path: error type keyword matching
    if error_type in _ERROR_TYPE_MAP:
        classification, subtype, severity = _ERROR_TYPE_MAP[error_type]
        return {
            "classification": classification,
            "severity": severity,
            "subtype": subtype,
        }

    text = error_text.lower()

    # 2. Safety patterns (highest priority)
    for label, pattern, severity in _SAFETY_PATTERNS:
        if pattern.search(error_text):
            return {
                "classification": "safety",
                "severity": severity,
                "subtype": label,
            }

    # 3. Infrastructure patterns
    for label, pattern, severity in _INFRA_PATTERNS:
        if pattern.search(error_text):
            return {
                "classification": "infrastructure",
                "severity": severity,
                "subtype": label,
            }

    # 4. Transient patterns
    for label, pattern, severity in _TRANSIENT_PATTERNS:
        if pattern.search(error_text):
            return {
                "classification": "transient",
                "severity": severity,
                "subtype": label,
            }

    # 5. Unknown — default to safety (conservative)
    return {
        "classification": "safety",
        "severity": "medium",
        "subtype": "unclassified",
    }


# ── Main ──────────────────────────────────────────────────────────────────────


def main() -> None:
    """Read error from stdin, classify, write result to stdout."""
    start_ns = time.perf_counter_ns()

    try:
        data = read_stdin_json()
    except SystemExit:
        _log.error("Failed to read stdin: invalid or empty JSON")
        write_stdout_json({
            "action": "warn",
            "classification": "safety",
            "severity": "high",
            "subtype": "hook_input_error",
        })
        sys.exit(0)

    error_text: str = str(data.get("error", ""))
    error_type: str = str(data.get("error_type", ""))
    raw_ctx = data.get("context", {})
    context: dict[str, object] = dict(raw_ctx) if isinstance(raw_ctx, dict) else {}

    result = classify_error(error_text, error_type)
    elapsed_ns = time.perf_counter_ns() - start_ns
    elapsed_ms = elapsed_ns / 1_000_000.0

    classification = result["classification"]
    severity = result["severity"]

    _log.info(
        "CLASSIFIED | class=%s | severity=%s | subtype=%s | "
        "error_type=%s | context_keys=%s | elapsed_ms=%.2f",
        classification,
        severity,
        result.get("subtype", ""),
        error_type,
        list(context.keys()) if context else [],
        elapsed_ms,
    )

    write_stdout_json({
        "action": "warn",
        "classification": classification,
        "severity": severity,
        "subtype": result.get("subtype", ""),
    })
    sys.exit(0)


if __name__ == "__main__":
    main()