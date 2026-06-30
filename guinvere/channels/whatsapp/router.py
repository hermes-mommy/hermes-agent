from __future__ import annotations

"""P11-008 + P11-009 — Thin WhatsApp router."""

from dataclasses import dataclass
from typing import Any

from .adapter import WhatsAppAdapter
from .bridge import HermesResult, WhatsAppHermesBridge
from .envelope import WhatsAppDeliveryEnvelope, WhatsAppMessageEnvelope
from .formatter import WhatsAppFormatter
from .ops_commands import WhatsAppOpsCommandHandler
from .presence import TypingIndicator


@dataclass(frozen=True, slots=True)
class RouterDecision:
    kind: str
    command_name: str | None = None
    command_args: list[str] | None = None


class WhatsAppRouter:
    """Thin router after all upstream safety gates have passed."""

    def __init__(
        self,
        *,
        bridge: WhatsAppHermesBridge,
        commands: WhatsAppOpsCommandHandler,
        formatter: WhatsAppFormatter,
        adapter: WhatsAppAdapter,
        presence: TypingIndicator,
    ) -> None:
        self._bridge = bridge
        self._commands = commands
        self._formatter = formatter
        self._adapter = adapter
        self._presence = presence

    def classify(self, envelope: WhatsAppMessageEnvelope) -> RouterDecision:
        text = envelope.body.strip()
        if not text:
            return RouterDecision(kind="discard")
        if text.startswith("/"):
            parts = text[1:].split()
            if not parts:
                return RouterDecision(kind="discard")
            return RouterDecision(kind="command", command_name=parts[0].lower(), command_args=parts[1:])
        return RouterDecision(kind="conversation")

    async def route(self, envelope: WhatsAppMessageEnvelope) -> list[str]:
        decision = self.classify(envelope)
        if decision.kind == "discard":
            return []

        await self._presence.start_typing(envelope.sender_raw_jid)
        try:
            if decision.kind == "command":
                response_text = await self._commands.handle(
                    decision.command_name or "",
                    decision.command_args or [],
                    envelope,
                )
            else:
                response_text = await self._bridge.process(envelope)
            chunks = self._formatter.format(response_text)
            for chunk in chunks:
                delivery = WhatsAppDeliveryEnvelope(target_jid=envelope.sender_raw_jid, body=chunk)
                await self._adapter.send(delivery, source_message=envelope)
            return chunks
        finally:
            await self._presence.stop_typing(envelope.sender_raw_jid)

    async def route_result(self, envelope: WhatsAppMessageEnvelope) -> HermesResult | str | None:
        decision = self.classify(envelope)
        if decision.kind == "discard":
            return None
        if decision.kind == "command":
            return await self._commands.handle(
                decision.command_name or "",
                decision.command_args or [],
                envelope,
            )
        return await self._bridge.invoke(envelope)
