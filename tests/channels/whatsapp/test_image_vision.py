from __future__ import annotations

"""Tests for WhatsApp image / vision flow across 4 modules:

1. Envelope — ``has_image`` property.
2. Policy   — image messages pass / block decisions.
3. Bridge   — ``_build_content()`` multimodal payload construction.
4. Session  — history storage extracts text from multimodal parts.
"""

import base64
from datetime import UTC, datetime
from typing import Any

from src.channels.whatsapp.bridge import WhatsAppHermesBridge
from src.channels.whatsapp.envelope import WhatsAppMessageEnvelope
from src.channels.whatsapp.policy import WhatsAppPolicyGate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SENDER_HASH = "abc123def456"
_SENDER_JID = "628123@s.whatsapp.net"
_MESSAGE_ID = "wamid-img-1"
_NOW = datetime.now(UTC)
_FAKE_IMAGE = b"\xff\xd8\xff\xe0" + b"\x00" * 64  # minimal JPEG header


def _make_envelope(
    *,
    body: str = "hello",
    media_type: str | None = None,
    image_bytes: bytes | None = None,
    is_group: bool = False,
) -> WhatsAppMessageEnvelope:
    """Create a WhatsAppMessageEnvelope for testing."""
    return WhatsAppMessageEnvelope(
        sender_jid_hash=_SENDER_HASH,
        sender_raw_jid=_SENDER_JID,
        message_id=_MESSAGE_ID,
        timestamp=_NOW,
        body=body,
        chat_jid=_SENDER_JID,
        is_group=is_group,
        media_type=media_type,
        image_bytes=image_bytes,
    )


# ===================================================================
# 1. Envelope — has_image property
# ===================================================================


class TestEnvelopeHasImage:
    """Verify ``has_image`` returns True/False correctly."""

    def test_has_image_true_when_image_media_and_bytes(self) -> None:
        envelope = _make_envelope(media_type="image", image_bytes=_FAKE_IMAGE)
        assert envelope.has_image is True

    def test_has_image_false_when_image_media_but_no_bytes(self) -> None:
        envelope = _make_envelope(media_type="image", image_bytes=None)
        assert envelope.has_image is False

    def test_has_image_false_for_text_only_envelope(self) -> None:
        envelope = _make_envelope()
        assert envelope.has_image is False

    def test_has_image_false_when_bytes_present_but_not_image_media(self) -> None:
        envelope = _make_envelope(media_type="video", image_bytes=_FAKE_IMAGE)
        assert envelope.has_image is False


# ===================================================================
# 2. Policy — image messages pass / block decisions
# ===================================================================


class TestPolicyImageGate:
    """Verify policy gate allows images with bytes, blocks without."""

    def test_image_envelope_with_bytes_passes_policy(self) -> None:
        envelope = _make_envelope(
            media_type="image",
            image_bytes=_FAKE_IMAGE,
            body="look at this",
        )
        gate = WhatsAppPolicyGate()
        decision = gate.evaluate(envelope)
        assert decision.allowed is True
        assert decision.action == "pass"
        assert decision.envelope is envelope

    def test_image_envelope_without_bytes_is_blocked(self) -> None:
        envelope = _make_envelope(media_type="image", body="look at this")
        gate = WhatsAppPolicyGate()
        decision = gate.evaluate(envelope)
        assert decision.allowed is False
        assert decision.action == "ack_media"

    def test_non_image_media_envelope_is_blocked(self) -> None:
        envelope = _make_envelope(media_type="video")
        gate = WhatsAppPolicyGate()
        decision = gate.evaluate(envelope)
        assert decision.allowed is False
        assert decision.action == "ack_media"


# ===================================================================
# 3. Bridge — _build_content() multimodal payload
# ===================================================================


class TestBridgeBuildContent:
    """Verify ``_build_content()`` produces correct payloads."""

    def _make_bridge(self) -> WhatsAppHermesBridge:
        return WhatsAppHermesBridge(
            hermes_getter=lambda: None,
            prompt_builder=lambda _e: "test-prompt",
        )

    def test_text_only_returns_plain_string(self) -> None:
        bridge = self._make_bridge()
        envelope = _make_envelope(body="hello world")
        result = bridge._build_content(envelope)
        assert isinstance(result, str)
        assert result == "hello world"

    def test_image_envelope_returns_multimodal_list(self) -> None:
        bridge = self._make_bridge()
        envelope = _make_envelope(
            body="describe this",
            media_type="image",
            image_bytes=_FAKE_IMAGE,
        )
        result = bridge._build_content(envelope)
        assert isinstance(result, list)
        assert len(result) == 2

        image_part, text_part = result
        assert image_part["type"] == "image_url"
        assert image_part["image_url"]["url"].startswith("data:image/jpeg;base64,")
        # Verify the base64 payload is correct.
        b64_payload = image_part["image_url"]["url"].split(",", 1)[1]
        assert base64.b64decode(b64_payload) == _FAKE_IMAGE

        assert text_part["type"] == "text"
        assert text_part["text"] == "describe this"

    def test_image_without_caption_uses_default_text(self) -> None:
        bridge = self._make_bridge()
        envelope = _make_envelope(
            body="",
            media_type="image",
            image_bytes=_FAKE_IMAGE,
        )
        result = bridge._build_content(envelope)
        assert isinstance(result, list)
        text_part = result[1]
        assert text_part["type"] == "text"
        assert text_part["text"] == "Describe this image."


# ===================================================================
# 4. Session adapter — history storage extracts text from parts
# ===================================================================


class TestSessionHistoryExtraction:
    """Verify inline history-extraction logic from multimodal content.

    The session adapter stores only text in history — never base64
    image blobs.  We test the extraction logic inline to avoid
    mocking the full Redis / AIAgent stack.
    """

    @staticmethod
    def _extract_history_content(content: str | list[dict[str, Any]]) -> str:
        """Replicate the extraction logic from HermesSessionAdapter.send_message."""
        if isinstance(content, list):
            text_parts = [
                p.get("text", "")
                for p in content
                if isinstance(p, dict) and p.get("type") == "text"
            ]
            return " ".join(text_parts).strip() or "[image]"
        return content

    def test_plain_string_passes_through(self) -> None:
        assert self._extract_history_content("hello") == "hello"

    def test_multimodal_list_extracts_text_parts(self) -> None:
        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}},
            {"type": "text", "text": "describe this"},
        ]
        assert self._extract_history_content(content) == "describe this"

    def test_multimodal_list_falls_back_to_image_placeholder(self) -> None:
        content: list[dict[str, Any]] = [
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}},
        ]
        assert self._extract_history_content(content) == "[image]"

    def test_multimodal_multiple_text_parts_joined(self) -> None:
        content: list[dict[str, Any]] = [
            {"type": "text", "text": "first"},
            {"type": "image_url", "image_url": {"url": "data:image/jpeg;base64,AAAA"}},
            {"type": "text", "text": "second"},
        ]
        assert self._extract_history_content(content) == "first second"
