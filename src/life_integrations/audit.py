"""P22 audit trail — hash-chained integration action log.

Every integration action produces an audit event. Events are hash-chained
(SHA256 of canonical payload + previous_hash) for tamper detection.

Schema matches audit.integration_api_log from P22 plan:
- INSERT/SELECT only (UPDATE/DELETE blocked at DB level)
- Hash-chained for integrity
- No plaintext secrets in metadata
"""

from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

import structlog

logger = structlog.get_logger(__name__)


@dataclass
class AuditEvent:
    """A single integration action audit event.

    Attributes:
        event_id: Unique event UUID.
        occurred_at: Timestamp (UTC ISO-8601).
        actor_type: Who initiated (user/agent/system).
        actor_id: Actor identifier.
        integration_id: Integration that performed the action.
        provider: Provider name.
        action: Action name (e.g., "send_message").
        tier: Permission tier (L1-L4).
        project_id: Project UUID (if scoped).
        result: Action result (success/failed/blocked).
        correlation_id: Correlation UUID for tracing.
        metadata: Additional context (no secrets).
        previous_hash: Hash of previous event in chain.
        event_hash: SHA256 of this event's canonical payload.
    """
    event_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    occurred_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    actor_type: str = "system"
    actor_id: str = "agent:guinevere"
    integration_id: str = ""
    provider: str = ""
    action: str = ""
    tier: str = "L1_READ"
    project_id: str | None = None
    result: str = "success"
    correlation_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: dict[str, Any] = field(default_factory=dict)
    previous_hash: str = ""
    event_hash: str = ""

    def compute_hash(self) -> str:
        """Compute SHA256 hash of canonical payload.

        Returns:
            Hex digest of SHA256(canonical_payload + previous_hash).
        """
        payload = {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "integration_id": self.integration_id,
            "provider": self.provider,
            "action": self.action,
            "tier": self.tier,
            "project_id": self.project_id,
            "result": self.result,
            "correlation_id": self.correlation_id,
            "metadata": self.metadata,
            "previous_hash": self.previous_hash,
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(
            f"{canonical}{self.previous_hash}".encode()
        ).hexdigest()

    def seal(self) -> None:
        """Compute and set the event_hash."""
        self.event_hash = self.compute_hash()

    def to_dict(self) -> dict[str, Any]:
        """Convert to dict for storage/transmission.

        Redacts any secret-like values in metadata.
        """
        return {
            "event_id": self.event_id,
            "occurred_at": self.occurred_at,
            "actor_type": self.actor_type,
            "actor_id": self.actor_id,
            "integration_id": self.integration_id,
            "provider": self.provider,
            "action": self.action,
            "tier": self.tier,
            "project_id": self.project_id,
            "result": self.result,
            "correlation_id": self.correlation_id,
            "metadata": _redact_metadata(self.metadata),
            "previous_hash": self.previous_hash,
            "event_hash": self.event_hash,
        }


import re as _re

# Value-level secret detection patterns — catches tokens embedded in
# content/body/text fields that key-name redaction alone would miss.
_VALUE_SECRET_PATTERNS = _re.compile(
    r"(ghp_[a-zA-Z0-9]{20,}|sk-[a-zA-Z0-9]{20,}|ya29\.[a-zA-Z0-9]+|"
    r"xox[baprs]-[a-zA-Z0-9-]+|AIza[a-zA-Z0-9_-]{30,}|"
    r"-----BEGIN [A-Z ]*PRIVATE KEY-----|"
    r"Bearer\s+[a-zA-Z0-9._-]{20,})",
    _re.IGNORECASE,
)


def _redact_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Redact secret-like values in metadata.

    Two-layer redaction:
    1. Key-name redaction: keys matching token/password/secret/key/credential/auth
    2. Value-pattern redaction: scans all string values for token-shaped
       substrings (ghp_, sk-, ya29., xox, AIza, PEM keys, Bearer) and
       redacts them — catches secrets embedded in content/body/text fields.
    """
    redacted: dict[str, Any] = {}
    secret_key_patterns = ("token", "password", "secret", "key", "credential", "auth")
    for k, v in metadata.items():
        # Layer 1: key-name redaction
        if any(p in k.lower() for p in secret_key_patterns):
            redacted[k] = "<redacted>"
            continue
        # Layer 2: value-pattern redaction (catch secrets in content/body/text)
        if isinstance(v, str):
            if _VALUE_SECRET_PATTERNS.search(v):
                redacted[k] = "<redacted:secret_in_value>"
            elif len(v) > 100:
                redacted[k] = f"<long:{len(v)}>"
            else:
                redacted[k] = v
        else:
            redacted[k] = v
    return redacted


class AuditLogger:
    """Hash-chained audit logger for integration actions.

    Maintains the chain by tracking the last event's hash. Events are
    written via an injected writer callback (DB, file, or in-memory).

    Usage:
        logger = AuditLogger(writer=db_writer)
        event = await logger.log_action(
            integration_id="discord",
            provider="Discord",
            action="send_message",
            tier="L2_WRITE",
            project_id=project_id,
            result="success",
            metadata={"channel_id": "123"},
        )
    """

    def __init__(self, writer: Any | None = None) -> None:
        """Initialize the audit logger.

        Args:
            writer: Callback/protocol with async write_event(event_dict) method.
                     If None, events are logged but not persisted (dev mode).
        """
        self._writer = writer
        self._last_hash: str = ""

    async def log_action(
        self,
        integration_id: str,
        provider: str,
        action: str,
        tier: str,
        project_id: uuid.UUID | None = None,
        result: str = "success",
        actor_type: str = "system",
        actor_id: str = "agent:guinevere",
        correlation_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """Log an integration action and return the sealed event.

        Args:
            integration_id: Integration that performed the action.
            provider: Provider name.
            action: Action name.
            tier: Permission tier (L1-L4).
            project_id: Project UUID (if scoped).
            result: Action result.
            actor_type: Who initiated (user/agent/system).
            actor_id: Actor identifier.
            correlation_id: Correlation UUID (auto-generated if None).
            metadata: Additional context (no secrets).

        Returns:
            The sealed AuditEvent with computed hash.
        """
        event = AuditEvent(
            actor_type=actor_type,
            actor_id=actor_id,
            integration_id=integration_id,
            provider=provider,
            action=action,
            tier=tier,
            project_id=str(project_id) if project_id else None,
            result=result,
            correlation_id=correlation_id or str(uuid.uuid4()),
            metadata=metadata or {},
            previous_hash=self._last_hash,
        )
        event.seal()
        self._last_hash = event.event_hash

        # Log structurally (no secrets)
        logger.info(
            "integration.action",
            event_id=event.event_id,
            integration_id=integration_id,
            provider=provider,
            action=action,
            tier=tier,
            result=result,
            project_id=str(project_id) if project_id else None,
            event_hash=event.event_hash[:16],
        )

        # Persist via writer if configured
        if self._writer is not None:
            try:
                await self._writer.write_event(event.to_dict())
            except Exception as e:
                logger.error(
                    "audit.write_failed",
                    event_id=event.event_id,
                    error=str(e),
                )

        return event

    @property
    def last_hash(self) -> str:
        """Return the hash of the last logged event."""
        return self._last_hash

    def verify_chain(self, events: list[AuditEvent]) -> bool:
        """Verify the integrity of an event chain.

        Args:
            events: List of AuditEvents to verify.

        Returns:
            True if all hashes are valid and chain is unbroken.
        """
        prev_hash = ""
        for event in events:
            if event.previous_hash != prev_hash:
                logger.error(
                    "audit.chain_broken",
                    event_id=event.event_id,
                    expected=prev_hash[:16],
                    got=event.previous_hash[:16],
                )
                return False
            computed = event.compute_hash()
            if computed != event.event_hash:
                logger.error(
                    "audit.hash_mismatch",
                    event_id=event.event_id,
                    expected=event.event_hash[:16],
                    got=computed[:16],
                )
                return False
            prev_hash = event.event_hash
        return True
