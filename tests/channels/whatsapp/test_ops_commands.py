from __future__ import annotations

from datetime import UTC, datetime

import pytest

from src.channels.whatsapp.consent_manager import WhatsAppConsentManager
from src.channels.whatsapp.envelope import WhatsAppMessageEnvelope
from src.channels.whatsapp.hard_stop import get_shared_hard_stop_handler
from src.channels.whatsapp.ops_commands import WhatsAppOpsCommandHandler


class DummyConsentManager(WhatsAppConsentManager):
    def __init__(self, granted: bool = True) -> None:
        self._granted = granted

    async def load_state(self):  # type: ignore[override]
        from src.channels.whatsapp.consent_manager import ConsentState

        return ConsentState(
            granted=self._granted,
            timestamp=None,
            channel="whatsapp",
            granted_by="Faiz" if self._granted else None,
            revoked_at=None,
        )


class DummyNeonizeClient:
    is_connected = True
    is_logged_in = True


@pytest.fixture
def sample_envelope() -> WhatsAppMessageEnvelope:
    return WhatsAppMessageEnvelope(
        sender_jid_hash="abc123",
        sender_raw_jid="628123456789@s.whatsapp.net",
        message_id="mid-1",
        timestamp=datetime.now(UTC),
        body="/status",
        chat_jid="628123456789@s.whatsapp.net",
        is_group=False,
        sender_identity="Faiz",
    )


@pytest.mark.asyncio
async def test_help_and_ping(sample_envelope: WhatsAppMessageEnvelope) -> None:
    handler = WhatsAppOpsCommandHandler(
        hard_stop_handler=get_shared_hard_stop_handler(),
        consent_manager=DummyConsentManager(),
        neonize_client=DummyNeonizeClient(),
    )
    help_text = await handler.handle("help", [], sample_envelope)
    ping_text = await handler.handle("ping", [], sample_envelope)
    assert "/status" in help_text
    assert ping_text.startswith("pong ")


@pytest.mark.asyncio
async def test_status_and_unknown(sample_envelope: WhatsAppMessageEnvelope) -> None:
    async def provider():
        return {
            "wa_connected": True,
            "hermes_available": True,
            "redis_ok": True,
            "postgres_ok": True,
            "router_ok": True,
        }

    handler = WhatsAppOpsCommandHandler(
        hard_stop_handler=get_shared_hard_stop_handler(),
        consent_manager=DummyConsentManager(),
        neonize_client=DummyNeonizeClient(),
        status_provider=provider,
    )
    status = await handler.handle("status", [], sample_envelope)
    unknown = await handler.handle("wat", [], sample_envelope)
    assert "wa_connected: True" in status
    assert "Command tidak dikenal" in unknown
