from __future__ import annotations

"""P11-013 — Group / Media / Text-only policy gate."""

from dataclasses import dataclass

from .envelope import WhatsAppMessageEnvelope

MEDIA_ACK_RESPONSE = (
    "Aku sudah menerima medianya, tapi untuk Phase 11 aku masih text-only. "
    "Coba kirim isi atau instruksinya dalam bentuk teks ya."
)


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    allowed: bool
    action: str
    envelope: WhatsAppMessageEnvelope | None
    response_body: str | None = None
    reason: str = ""


class WhatsAppPolicyGate:
    """WhatsApp-specific group/media/text-only policy gate.

    The adapter already performs a structural group ignore. This policy gate keeps
    the explicit contract for later pipeline stages and for direct unit testing.
    """

    def evaluate(self, envelope: WhatsAppMessageEnvelope) -> PolicyDecision:
        if envelope.is_group:
            return PolicyDecision(
                allowed=False,
                action="drop",
                envelope=None,
                reason="group_message",
            )

        if self._is_media_message(envelope):
            return PolicyDecision(
                allowed=False,
                action="ack_media",
                envelope=None,
                response_body=MEDIA_ACK_RESPONSE,
                reason="media_text_only_policy",
            )

        return PolicyDecision(
            allowed=True,
            action="pass",
            envelope=envelope,
            reason="text_allowed",
        )

    def _is_media_message(self, envelope: WhatsAppMessageEnvelope) -> bool:
        if envelope.media_type:
            return True
        return not envelope.is_text
