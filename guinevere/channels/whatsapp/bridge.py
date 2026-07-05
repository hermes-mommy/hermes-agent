from __future__ import annotations

"""P11-006 — Narrow WhatsApp → Hermes bridge.

This module intentionally adds no new conversational intelligence. It accepts a
canonical WhatsApp envelope, builds the current system prompt, invokes the
existing Hermes runtime/session surface, and returns a typed result.
"""

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable

import structlog

from guinevere.core.services.prompt_loader import get_system_prompt_with_context
from guinevere.hermes.adapter import get_adapter

from .envelope import WhatsAppMessageEnvelope

logger = structlog.get_logger()


class HermesBridgeError(RuntimeError):
    """Base error for WhatsApp Hermes bridge failures."""


class HermesUnavailable(HermesBridgeError):
    """Hermes runtime could not be acquired or is not usable."""


class HermesTimeout(HermesBridgeError):
    """Hermes call timed out."""


class HermesToolFailure(HermesBridgeError):
    """Hermes failed due to a downstream tool/runtime issue."""


class HermesInternalError(HermesBridgeError):
    """Hermes failed for an internal, non-tool reason."""


class HermesSafetyRefusal(HermesBridgeError):
    """Hermes returned a refusal/safety-only response."""


@dataclass(frozen=True, slots=True)
class HermesResult:
    response_text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    user_id: str = ""
    system_prompt: str = ""


PromptBuilder = Callable[[WhatsAppMessageEnvelope], str]


class WhatsAppHermesBridge:
    """Stateless bridge from WhatsApp envelopes into the shared Hermes runtime."""

    def __init__(
        self,
        *,
        hermes_getter: Callable[[], Any] | None = None,
        prompt_builder: PromptBuilder | None = None,
        timeout_seconds: float = 60.0,
    ) -> None:
        self._hermes_getter = hermes_getter or get_adapter
        self._prompt_builder = prompt_builder or self._default_prompt_builder
        self._timeout_seconds = timeout_seconds

    def is_available(self) -> bool:
        try:
            self._hermes_getter()
        except Exception:  # noqa: BLE001
            return False
        return True

    async def invoke(self, envelope: WhatsAppMessageEnvelope) -> HermesResult:
        envelope.validate()
        user_id = envelope.sender_identity or envelope.normalized_sender_phone()
        system_prompt = self._prompt_builder(envelope)

        try:
            hermes = self._hermes_getter()
        except Exception as exc:  # noqa: BLE001
            logger.error("whatsapp_hermes_unavailable", error=str(exc))
            raise HermesUnavailable("Hermes runtime unavailable") from exc

        try:
            response_text = await asyncio.wait_for(
                hermes.send_message(
                    user_id=user_id,
                    content=envelope.body,
                    system_prompt=system_prompt,
                ),
                timeout=self._timeout_seconds,
            )
        except asyncio.TimeoutError as exc:
            logger.warning("whatsapp_hermes_timeout", user_id=user_id)
            raise HermesTimeout("Hermes invocation timed out") from exc
        except Exception as exc:  # noqa: BLE001
            message = str(exc).lower()
            logger.error("whatsapp_hermes_error", user_id=user_id, error=str(exc))
            if "tool" in message or "mcp" in message:
                raise HermesToolFailure(str(exc)) from exc
            raise HermesInternalError(str(exc)) from exc

        if not response_text:
            raise HermesInternalError("Hermes returned an empty response")

        metadata = self._safe_metadata(hermes, user_id)
        if self._looks_like_refusal(response_text):
            raise HermesSafetyRefusal(response_text)

        return HermesResult(
            response_text=response_text,
            metadata=metadata,
            user_id=user_id,
            system_prompt=system_prompt,
        )

    async def process(self, envelope: WhatsAppMessageEnvelope) -> str:
        result = await self.invoke(envelope)
        return result.response_text

    def _default_prompt_builder(self, _envelope: WhatsAppMessageEnvelope) -> str:
        return get_system_prompt_with_context(memories=None, mood="Content", token_budget=800)

    def _safe_metadata(self, hermes: Any, user_id: str) -> dict[str, Any]:
        try:
            metadata = hermes.get_last_metadata(user_id)
        except Exception as exc:  # noqa: BLE001
            logger.warning("whatsapp_hermes_metadata_unavailable", error=str(exc), user_id=user_id)
            return {}
        if isinstance(metadata, dict):
            return metadata
        return {}

    def _looks_like_refusal(self, response_text: str) -> bool:
        lowered = response_text.lower()
        return "refuse" in lowered or "cannot help with that" in lowered
