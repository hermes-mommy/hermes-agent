from __future__ import annotations

"""P11-021 — Structured metadata-only logging for WhatsApp."""

import hashlib
from collections.abc import MutableMapping
from typing import Any

import structlog

EventDict = MutableMapping[str, Any]


def _redact_body_processor(_logger: object, _method_name: str, event_dict: EventDict) -> EventDict:
    for field in ("body", "text", "content", "message", "raw_message"):
        event_dict.pop(field, None)
    return event_dict


def configure_structlog() -> None:
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso", utc=True),
            structlog.processors.add_log_level,
            _redact_body_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def jid_hash(jid: str) -> str:
    return hashlib.sha256(jid.encode("utf-8")).hexdigest()[:12]


def log_message_received(*, jid: str, message_id: str, message_type: str, byte_length: int) -> None:
    structlog.get_logger().info(
        "wa.message.received",
        direction="inbound",
        jid_hash=jid_hash(jid),
        message_id=message_id,
        message_type=message_type,
        byte_length=byte_length,
    )


def log_message_processed(*, jid: str, latency_ms: float, message_type: str) -> None:
    structlog.get_logger().info(
        "wa.message.processed",
        direction="outbound",
        jid_hash=jid_hash(jid),
        latency_ms=latency_ms,
        message_type=message_type,
    )


def log_message_sent(*, jid: str, message_id: str, byte_length: int) -> None:
    structlog.get_logger().info(
        "wa.message.sent",
        direction="outbound",
        jid_hash=jid_hash(jid),
        message_id=message_id,
        byte_length=byte_length,
    )


def log_message_failed(*, jid: str | None, error: str, connection_state: str) -> None:
    structlog.get_logger().error(
        "wa.message.failed",
        jid_hash=jid_hash(jid) if jid else None,
        error=error,
        connection_state=connection_state,
    )


def log_policy_blocked(*, jid: str, policy_decision: str) -> None:
    structlog.get_logger().info(
        "wa.policy.blocked",
        jid_hash=jid_hash(jid),
        policy_decision=policy_decision,
    )


def log_connection_state_change(*, new_state: str, previous_state: str) -> None:
    structlog.get_logger().info(
        "wa.connection.state_change",
        connection_state=new_state,
        previous_state=previous_state,
    )


def log_health_check(*, connection_state: str, session_age_s: float, needs_manual: bool, status: str) -> None:
    structlog.get_logger().info(
        "wa.health.check",
        connection_state=connection_state,
        session_age_s=session_age_s,
        needs_manual=needs_manual,
        status=status,
    )


def log_reconnect_attempt(*, attempt: int, reason: str) -> None:
    structlog.get_logger().warning("wa.reconnect.attempt", attempt=attempt, reason=reason)


def log_reconnect_exhausted(*, reason: str, final_state: str) -> None:
    structlog.get_logger().error("wa.reconnect.exhausted", reason=reason, final_state=final_state)
