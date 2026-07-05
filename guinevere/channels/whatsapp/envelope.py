from __future__ import annotations

"""Canonical WhatsApp DTO seam for P11 Wave 2/3.

This module defines the narrow normalized payloads used between the
transport/adapter layer and downstream safety / routing / bridge /
formatting stages. It intentionally stays WhatsApp-specific and does not
introduce any generic multi-channel abstraction.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class WhatsAppMessageEnvelope:
    """Normalized inbound WhatsApp payload.

    Required canonical fields come from the approved P11-004 contract.
    `media_type` and `media_size_bytes` are optional narrow metadata fields used
    by the adapter and later policy stages without widening this module into a
    generic media-processing layer.
    """

    sender_jid_hash: str
    sender_raw_jid: str
    message_id: str
    timestamp: datetime
    body: str
    chat_jid: str
    is_group: bool
    reply_to_id: str | None = None
    push_name: str | None = None
    media_type: str | None = None
    media_size_bytes: int | None = None
    sender_identity: str | None = None

    @property
    def is_text(self) -> bool:
        return bool(self.body.strip())

    @property
    def has_media(self) -> bool:
        return bool(self.media_type)

    def validate(self) -> None:
        if not self.sender_jid_hash:
            raise ValueError("sender_jid_hash must not be empty")
        if not self.sender_raw_jid:
            raise ValueError("sender_raw_jid must not be empty")
        if not self.message_id:
            raise ValueError("message_id must not be empty")
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        if not self.chat_jid:
            raise ValueError("chat_jid must not be empty")
        if self.media_size_bytes is not None and self.media_size_bytes < 0:
            raise ValueError("media_size_bytes must be >= 0")

    def normalized_sender_phone(self) -> str:
        return normalize_jid(self.sender_raw_jid)


@dataclass(frozen=True, slots=True)
class WhatsAppDeliveryEnvelope:
    """Normalized outbound WhatsApp payload."""

    target_jid: str
    body: str
    reply_to_id: str | None = None
    chunk_index: int = 0
    total_chunks: int = 1

    def validate(self) -> None:
        if not self.target_jid:
            raise ValueError("target_jid must not be empty")
        if not self.body:
            raise ValueError("body must not be empty for delivery")
        if self.chunk_index < 0:
            raise ValueError("chunk_index must be >= 0")
        if self.total_chunks < 1:
            raise ValueError("total_chunks must be >= 1")
        if self.chunk_index >= self.total_chunks:
            raise ValueError("chunk_index must be < total_chunks")

    def normalized_target_phone(self) -> str:
        return normalize_jid(self.target_jid)


def normalize_jid(jid: str) -> str:
    """Normalize a WhatsApp JID to a bare phone/user identifier.

    Examples:
    - ``628123@s.whatsapp.net`` -> ``628123``
    - ``628123:7@s.whatsapp.net`` -> ``628123``
    - ``120363...@g.us`` -> ``120363...``
    """

    value = jid.strip()
    if "@" in value:
        value = value.split("@", 1)[0]
    if ":" in value:
        value = value.split(":", 1)[0]
    return value


def to_jid(phone_or_jid: str) -> str:
    """Convert a bare phone number into a personal WhatsApp JID string."""

    value = phone_or_jid.strip()
    if "@" in value:
        return value
    return f"{value}@s.whatsapp.net"


def ensure_utc_timestamp(value: datetime | int | float | None) -> datetime:
    """Normalize supported timestamp inputs into an aware UTC datetime."""

    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(float(value), tz=UTC)
    return datetime.now(UTC)


def safe_int(value: Any) -> int | None:
    if value in (None, ""):
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
