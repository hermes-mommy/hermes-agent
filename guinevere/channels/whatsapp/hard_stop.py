from __future__ import annotations

"""P11-015 — WhatsApp HARD STOP gate using the shared safety core."""

from dataclasses import dataclass

import structlog

from guinevere.core.services.hard_stop_handler import HardStopHandler

from .envelope import WhatsAppMessageEnvelope

logger = structlog.get_logger()


@dataclass(frozen=True, slots=True)
class HardStopDecision:
    blocked: bool
    state: str
    response: str | None
    envelope: WhatsAppMessageEnvelope | None


_SHARED_HANDLER = HardStopHandler()


def get_shared_hard_stop_handler() -> HardStopHandler:
    return _SHARED_HANDLER


class WhatsAppHardStopGate:
    """Thin WhatsApp wrapper around the shared ``HardStopHandler``.

    This gate owns no parallel state. It simply applies the global handler to
    WhatsApp message text and returns a transport-friendly decision object.
    """

    def __init__(self, handler: HardStopHandler | None = None) -> None:
        self._handler: HardStopHandler = handler or get_shared_hard_stop_handler()

    def evaluate(self, envelope: WhatsAppMessageEnvelope) -> HardStopDecision:
        try:
            decision = self._handler.get_guard_decision(envelope.body)
            blocked = bool(decision.get("blocked", False))
            response = decision.get("response")
            state = str(decision.get("state") or self._handler.state.value)
            return HardStopDecision(
                blocked=blocked,
                state=state,
                response=response,
                envelope=None if blocked else envelope,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("whatsapp_hard_stop_failed_closed", error=str(exc))
            return HardStopDecision(
                blocked=True,
                state="safe",
                response=self._handler.get_neutral_response(),
                envelope=None,
            )
