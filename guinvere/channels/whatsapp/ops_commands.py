from __future__ import annotations

"""P11-010 — Minimal WhatsApp ops commands."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

import structlog

from guinvere.core.services.hard_stop_handler import HardStopHandler

from .consent_manager import WhatsAppConsentManager
from .envelope import WhatsAppMessageEnvelope
from .neonize_client import NeonizeClient

logger = structlog.get_logger()

ALLOWED_COMMANDS = {"status", "help", "stop", "resume", "ping"}


@dataclass(frozen=True, slots=True)
class OpsCommandResult:
    handled: bool
    response_text: str
    command_name: str


class WhatsAppOpsCommandHandler:
    """Narrow fixed-surface WA ops command handler."""

    def __init__(
        self,
        *,
        hard_stop_handler: HardStopHandler,
        consent_manager: WhatsAppConsentManager,
        neonize_client: NeonizeClient,
        status_provider: Any | None = None,
    ) -> None:
        self._hard_stop_handler = hard_stop_handler
        self._consent_manager = consent_manager
        self._neonize_client = neonize_client
        self._status_provider = status_provider

    async def handle(
        self,
        command_name: str,
        command_args: list[str],
        envelope: WhatsAppMessageEnvelope,
    ) -> str:
        _ = command_args
        normalized = command_name.strip().lower().lstrip("/")
        if normalized not in ALLOWED_COMMANDS:
            return self._unknown_command_response()

        if normalized == "help":
            return self._help_response()
        if normalized == "ping":
            return self._ping_response()
        if normalized == "status":
            return await self._status_response()
        if normalized == "stop":
            return await self._stop_response(envelope)
        if normalized == "resume":
            return await self._resume_response(envelope)
        return self._unknown_command_response()

    def _help_response(self) -> str:
        return (
            "WhatsApp ops commands tersedia:\n"
            "/status — cek status WA/Hermes/Redis/Postgres/9router\n"
            "/help — tampilkan daftar command\n"
            "/stop — aktifkan HARD STOP global\n"
            "/resume — pulihkan dari HARD STOP jika aman\n"
            "/ping — cek respons lokal"
        )

    def _ping_response(self) -> str:
        return f"pong {datetime.now(UTC).isoformat()}"

    async def _status_response(self) -> str:
        payload = await self._get_status_payload()
        lines = [
            "WhatsApp status:",
            f"- wa_connected: {payload['wa_connected']}",
            f"- hermes_available: {payload['hermes_available']}",
            f"- redis_ok: {payload['redis_ok']}",
            f"- postgres_ok: {payload['postgres_ok']}",
            f"- 9router_ok: {payload['router_ok']}",
            f"- safe_mode: {payload['safe_mode']}",
            f"- consent_granted: {payload['consent_granted']}",
            f"- checked_at: {payload['checked_at']}",
        ]
        return "\n".join(lines)

    async def _stop_response(self, envelope: WhatsAppMessageEnvelope) -> str:
        trigger_text = envelope.body or "hard stop"
        decision = self._hard_stop_handler.get_guard_decision(trigger_text)
        if decision.get("blocked"):
            return str(decision.get("response") or self._hard_stop_handler.get_neutral_response())
        # Fallback if body did not contain trigger terms.
        self._hard_stop_handler.check("hard stop")
        return self._hard_stop_handler.get_neutral_response()

    async def _resume_response(self, _envelope: WhatsAppMessageEnvelope) -> str:
        recovered = self._hard_stop_handler.check_recovery("resume")
        if recovered:
            return "Persona mode restored. Welcome back, darling."
        if self._hard_stop_handler.is_safe:
            return "Masih dalam safe mode. Kirim 'resume' saat memang siap keluar dari HARD STOP."
        return "Safe mode tidak aktif."

    async def _get_status_payload(self) -> dict[str, Any]:
        checked_at = datetime.now(UTC).isoformat()
        safe_mode = self._hard_stop_handler.is_safe
        consent_state = await self._consent_manager.load_state()
        if self._status_provider is not None:
            try:
                payload = await self._status_provider()
            except Exception as exc:  # noqa: BLE001
                logger.warning("whatsapp_status_provider_failed", error=str(exc))
                payload = {}
        else:
            payload = {}

        return {
            "wa_connected": bool(payload.get("wa_connected", self._neonize_client.is_connected or self._neonize_client.is_logged_in)),
            "hermes_available": bool(payload.get("hermes_available", True)),
            "redis_ok": bool(payload.get("redis_ok", True)),
            "postgres_ok": bool(payload.get("postgres_ok", True)),
            "router_ok": bool(payload.get("router_ok", True)),
            "safe_mode": safe_mode,
            "consent_granted": consent_state.granted,
            "checked_at": checked_at,
        }

    def _unknown_command_response(self) -> str:
        return "Command tidak dikenal. Coba /help untuk daftar command yang tersedia."
