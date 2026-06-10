from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.channels.whatsapp.envelope import (
    WhatsAppDeliveryEnvelope,
    WhatsAppMessageEnvelope,
    ensure_utc_timestamp,
    normalize_jid,
    to_jid,
)


def test_message_envelope_validate_and_is_text() -> None:
    envelope = WhatsAppMessageEnvelope(
        sender_jid_hash="abc123def456",
        sender_raw_jid="628123@s.whatsapp.net",
        message_id="wamid-1",
        timestamp=datetime.now(UTC),
        body="hello",
        chat_jid="628123@s.whatsapp.net",
        is_group=False,
    )

    envelope.validate()
    assert envelope.is_text is True
    assert envelope.normalized_sender_phone() == "628123"


def test_message_envelope_rejects_empty_required_fields() -> None:
    envelope = WhatsAppMessageEnvelope(
        sender_jid_hash="",
        sender_raw_jid="628123@s.whatsapp.net",
        message_id="wamid-1",
        timestamp=datetime.now(UTC),
        body="hello",
        chat_jid="628123@s.whatsapp.net",
        is_group=False,
    )

    with pytest.raises(ValueError, match="sender_jid_hash"):
        envelope.validate()


def test_delivery_envelope_validate() -> None:
    delivery = WhatsAppDeliveryEnvelope(target_jid="628123", body="hello")
    delivery.validate()
    assert delivery.normalized_target_phone() == "628123"


def test_delivery_envelope_rejects_invalid_chunk_range() -> None:
    delivery = WhatsAppDeliveryEnvelope(target_jid="628123", body="hello", chunk_index=2, total_chunks=2)
    with pytest.raises(ValueError, match="chunk_index"):
        delivery.validate()


def test_jid_helpers() -> None:
    assert normalize_jid("628123:9@s.whatsapp.net") == "628123"
    assert normalize_jid("120363@g.us") == "120363"
    assert to_jid("628123") == "628123@s.whatsapp.net"
    assert to_jid("628123@s.whatsapp.net") == "628123@s.whatsapp.net"


def test_ensure_utc_timestamp_accepts_numeric() -> None:
    dt = ensure_utc_timestamp(1_700_000_000)
    assert dt.tzinfo is not None
