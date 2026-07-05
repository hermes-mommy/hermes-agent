from __future__ import annotations

"""Canonical Gmail DTO seam for P12 Gmail Integration.

This module defines the narrow normalized payloads used between the
Gmail API adapter layer and downstream classification / routing / reply
/ extraction stages.  Both envelopes are frozen and slotted, following
the same pattern established by the WhatsApp channel envelopes.
"""

from dataclasses import dataclass
from datetime import datetime

import structlog

from .categories import EmailCategory, CATEGORY_PRIORITY, CATEGORY_ACTIONS

logger = structlog.get_logger(__name__)

_REQUIRED_FIELDS: tuple[str, ...] = (
    "message_id",
    "thread_id",
    "sender",
    "subject",
    "timestamp",
)

_REQUIRED_DELIVERY_FIELDS: tuple[str, ...] = (
    "target_email",
    "subject",
    "body_html",
)


@dataclass(frozen=True, slots=True)
class GmailMessageEnvelope:
    """Normalized inbound Gmail payload.

    Maps a single Gmail message into the canonical shape consumed by the
    classifier, policy gate, and routing stages.  All timestamps are
    stored as timezone-aware UTC datetimes.
    """

    message_id: str
    thread_id: str
    sender: str
    recipients: list[str]
    subject: str
    body_text: str
    body_html: str
    timestamp: datetime
    labels: list[str]
    snippet: str
    has_attachments: bool
    in_reply_to: str | None = None
    references: list[str] | None = None
    importance_markers: list[str] | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_reply(self) -> bool:
        """True when the message is part of an existing thread."""
        return self.in_reply_to is not None and len(self.in_reply_to) > 0

    @property
    def recipient_count(self) -> int:
        """Number of direct recipients (To: only, not CC/BCC aware)."""
        return len(self.recipients)

    @property
    def reference_count(self) -> int:
        """Number of RFC-2822 ``References`` header entries."""
        return len(self.references) if self.references else 0

    # ------------------------------------------------------------------
    # Classification helpers
    # ------------------------------------------------------------------

    def classify(self) -> EmailCategory:
        """Return the primary category for this envelope.

        The stub implementation falls back to ``IMPORTANT``.  The real
        classifier will be wired during a later wave.
        """
        logger.debug(
            "classify_stub",
            message_id=self.message_id,
            subject=self.subject,
        )
        return EmailCategory.IMPORTANT

    def priority_for(self, category: EmailCategory) -> str:
        """Return the priority label string for *category*."""
        return CATEGORY_PRIORITY[category].value

    def actions_for(self, category: EmailCategory) -> list[str]:
        """Return the action list for *category*."""
        return list(CATEGORY_ACTIONS[category])

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Validate required fields and invariants.

        Raises:
            ValueError: When a required field is empty or the timestamp
                is not timezone-aware.
        """
        for field_name in _REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if isinstance(value, str) and not value.strip():
                raise ValueError(f"{field_name} must not be empty")
            if value is None:
                raise ValueError(f"{field_name} must not be None")

        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware (UTC)")

        if not self.recipients:
            raise ValueError("recipients must not be empty")

        for idx, addr in enumerate(self.recipients):
            if not addr.strip():
                raise ValueError(f"recipients[{idx}] must not be empty")

        if self.in_reply_to is not None and not self.in_reply_to.strip():
            raise ValueError(
                "in_reply_to, when provided, must not be empty"
            )

        logger.debug(
            "envelope_validated",
            message_id=self.message_id,
            thread_id=self.thread_id,
        )


@dataclass(frozen=True, slots=True)
class GmailDeliveryEnvelope:
    """Normalized outbound Gmail payload.

    Used by the reply-draft and notification stages to construct a
    Gmail API ``messages.send`` (or draft) request.
    """

    target_email: str
    subject: str
    body_html: str
    thread_id: str | None = None
    in_reply_to: str | None = None
    cc: list[str] | None = None
    draft_id: str | None = None

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def is_reply(self) -> bool:
        """True when this delivery is a reply in an existing thread."""
        return self.thread_id is not None and len(self.thread_id) > 0

    @property
    def cc_count(self) -> int:
        """Number of CC recipients."""
        return len(self.cc) if self.cc else 0

    @property
    def is_draft(self) -> bool:
        """True when an existing draft ID is being updated."""
        return self.draft_id is not None and len(self.draft_id) > 0

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self) -> None:
        """Validate required fields and invariants.

        Raises:
            ValueError: When a required field is empty or structural
                constraints are violated.
        """
        for field_name in _REQUIRED_DELIVERY_FIELDS:
            value = getattr(self, field_name)
            if not value.strip():
                raise ValueError(f"{field_name} must not be empty")

        if self.cc is not None:
            for idx, addr in enumerate(self.cc):
                if not addr.strip():
                    raise ValueError(f"cc[{idx}] must not be empty")

        if self.thread_id is not None and not self.thread_id.strip():
            raise ValueError(
                "thread_id, when provided, must not be empty"
            )

        if self.in_reply_to is not None and not self.in_reply_to.strip():
            raise ValueError(
                "in_reply_to, when provided, must not be empty"
            )

        if self.draft_id is not None and not self.draft_id.strip():
            raise ValueError(
                "draft_id, when provided, must not be empty"
            )

        logger.debug(
            "delivery_envelope_validated",
            target_email=self.target_email,
            thread_id=self.thread_id,
        )
