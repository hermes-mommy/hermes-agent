from __future__ import annotations

"""P11-022 — WhatsApp service entrypoint and runtime wiring."""

import argparse
import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.error import URLError
from urllib.request import urlopen

import asyncpg
import structlog

from .adapter import WhatsAppIngressEgressAdapter
from .auth import WhatsAppAuthManager, build_whatsapp_redis_client
from .bridge import (
    HermesBridgeError,
    HermesInternalError,
    HermesSafetyRefusal,
    HermesTimeout,
    HermesToolFailure,
    HermesUnavailable,
    WhatsAppHermesBridge,
)
from .consent_manager import WhatsAppConsentManager
from .envelope import WhatsAppMessageEnvelope
from .hard_stop import WhatsAppHardStopGate, get_shared_hard_stop_handler
from .health import REDIS_SESSION_CREATED_AT_KEY, WhatsAppHealthProbe
from .metrics import observe_response_latency
from .neonize_client import NeonizeClient
from .ops_commands import WhatsAppOpsCommandHandler
from .policy import WhatsAppPolicyGate
from .presence import TypingIndicator
from .rate_limiter import WhatsAppRateLimiter
from .router import WhatsAppRouter
from .structured_logging import (
    configure_structlog,
    log_connection_state_change,
    log_message_failed,
    log_message_processed,
    log_message_received,
    log_message_sent,
    log_policy_blocked,
)
from .whitelist import WhitelistManager

logger = structlog.get_logger()

RATE_LIMIT_RESPONSE = "Terlalu cepat ya. Tunggu sebentar lalu coba lagi lagi."
HERMES_UNAVAILABLE_RESPONSE = "Hermes lagi belum siap. Coba lagi sebentar ya."
INTERNAL_ERROR_RESPONSE = "Ada kendala internal di jalur WhatsApp. Coba lagi sebentar ya."


class WhatsAppService:
    def __init__(self, *, phone_number: str | None = None) -> None:
        self._phone_number = phone_number
        self._redis = build_whatsapp_redis_client()
        self._auth = WhatsAppAuthManager(redis_client=self._redis)
        self._client = NeonizeClient(redis_client=self._redis, auth_manager=self._auth)
        self._adapter = WhatsAppIngressEgressAdapter(self._client)
        self._whitelist = WhitelistManager(redis_client=self._redis)
        self._hard_stop = WhatsAppHardStopGate(get_shared_hard_stop_handler())
        self._consent = WhatsAppConsentManager(redis_client=self._redis)
        self._rate_limiter = WhatsAppRateLimiter(redis_client=self._redis)
        self._policy = WhatsAppPolicyGate()
        self._bridge = WhatsAppHermesBridge()
        self._health = WhatsAppHealthProbe(self._redis)
        self._presence = TypingIndicator(self._client)
        self._commands = WhatsAppOpsCommandHandler(
            hard_stop_handler=get_shared_hard_stop_handler(),
            consent_manager=self._consent,
            neonize_client=self._client,
            status_provider=self.status_payload,
        )
        self._router = WhatsAppRouter(
            bridge=self._bridge,
            commands=self._commands,
            formatter=__import__("src.channels.whatsapp.formatter", fromlist=["WhatsAppFormatter"]).WhatsAppFormatter(),
            adapter=self._adapter,
            presence=self._presence,
        )
        self._health_task: asyncio.Task[None] | None = None
        self._running = False
        self._last_connection_state = "unknown"
        self._adapter.add_inbound_handler(self.handle_envelope)

    @property
    def neonize_client(self) -> NeonizeClient:
        return self._client

    async def status_payload(self) -> dict[str, Any]:
        redis_ok = False
        try:
            redis_ok = bool(await self._redis.ping())
        except Exception:  # noqa: BLE001
            redis_ok = False

        postgres_ok = await self._check_postgres()
        router_ok = await self._check_9router()
        hermes_available = self._bridge.is_available()
        snapshot = self._health.snapshot()
        return {
            "wa_connected": self._client.is_connected or self._client.is_logged_in,
            "hermes_available": hermes_available,
            "redis_ok": redis_ok,
            "postgres_ok": postgres_ok,
            "router_ok": router_ok,
            "health_status": snapshot.status.value,
            "health_reason": snapshot.degraded_reason,
        }

    async def start(self) -> None:
        configure_structlog()
        _ = await self._auth.ensure_runtime_dir()
        self._health_task = asyncio.create_task(self._health.run())
        await self._client.connect()
        self._running = True
        await self._sync_runtime_state()
        logger.info("whatsapp_service_started")

    async def stop(self) -> None:
        self._running = False
        if self._health_task is not None:
            self._health_task.cancel()
            try:
                await self._health_task
            except asyncio.CancelledError:
                pass
        await self._presence.force_clear_all()
        await self._client.stop()
        await self._client.close()
        logger.info("whatsapp_service_stopped")

    async def handle_envelope(self, envelope: WhatsAppMessageEnvelope) -> None:
        started = datetime.now(UTC)
        log_message_received(
            jid=envelope.sender_raw_jid,
            message_id=envelope.message_id,
            message_type=envelope.media_type or ("text" if envelope.is_text else "unknown"),
            byte_length=len(envelope.body.encode("utf-8")),
        )

        whitelist_decision = await self._whitelist.evaluate(envelope)
        if not whitelist_decision.allowed or whitelist_decision.envelope is None:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=whitelist_decision.reason)
            return
        envelope = whitelist_decision.envelope

        hard_stop_decision = self._hard_stop.evaluate(envelope)
        if hard_stop_decision.blocked:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision="blocked_hard_stop")
            if hard_stop_decision.response:
                await self._adapter.send_text(envelope.sender_raw_jid, hard_stop_decision.response)
            return

        consent_decision = await self._consent.evaluate(envelope)
        if not consent_decision.allowed or consent_decision.envelope is None:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=consent_decision.reason)
            if consent_decision.response:
                await self._adapter.send_text(envelope.sender_raw_jid, consent_decision.response)
            return
        envelope = consent_decision.envelope

        dedup_decision = await self._rate_limiter.check_inbound_dedup(envelope)
        if not dedup_decision.allowed:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=dedup_decision.reason)
            return

        policy_decision = self._policy.evaluate(envelope)
        if policy_decision.action == "drop":
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=policy_decision.reason or "blocked_group")
            return
        if policy_decision.action == "ack_media" and policy_decision.response_body:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision="media_ack")
            await self._adapter.send_text(envelope.sender_raw_jid, policy_decision.response_body)
            return
        if not policy_decision.allowed or policy_decision.envelope is None:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=policy_decision.reason or "blocked_policy")
            return
        envelope = policy_decision.envelope

        rate_limit_decision = await self._rate_limiter.reserve_outbound_slot(envelope.sender_raw_jid)
        if not rate_limit_decision.allowed:
            log_policy_blocked(jid=envelope.sender_raw_jid, policy_decision=rate_limit_decision.reason)
            await self._adapter.send_text(envelope.sender_raw_jid, RATE_LIMIT_RESPONSE)
            return

        previous_state = self._last_connection_state
        await self._sync_runtime_state()
        if self._last_connection_state != previous_state:
            log_connection_state_change(new_state=self._last_connection_state, previous_state=previous_state)

        try:
            chunks = await self._router.route(envelope)
        except HermesSafetyRefusal as exc:
            log_message_failed(jid=envelope.sender_raw_jid, error="hermes_safety_refusal", connection_state=self._last_connection_state)
            await self._adapter.send_text(envelope.sender_raw_jid, str(exc))
            return
        except HermesTimeout:
            log_message_failed(jid=envelope.sender_raw_jid, error="hermes_timeout", connection_state=self._last_connection_state)
            await self._adapter.send_text(envelope.sender_raw_jid, HERMES_UNAVAILABLE_RESPONSE)
            return
        except HermesUnavailable:
            log_message_failed(jid=envelope.sender_raw_jid, error="hermes_unavailable", connection_state=self._last_connection_state)
            await self._adapter.send_text(envelope.sender_raw_jid, HERMES_UNAVAILABLE_RESPONSE)
            return
        except (HermesToolFailure, HermesInternalError, HermesBridgeError) as exc:
            log_message_failed(jid=envelope.sender_raw_jid, error=exc.__class__.__name__, connection_state=self._last_connection_state)
            await self._adapter.send_text(envelope.sender_raw_jid, INTERNAL_ERROR_RESPONSE)
            return

        elapsed = (datetime.now(UTC) - started).total_seconds()
        observe_response_latency(elapsed)
        log_message_processed(
            jid=envelope.sender_raw_jid,
            latency_ms=elapsed * 1000.0,
            message_type=envelope.media_type or ("command" if envelope.body.strip().startswith("/") else "text"),
        )
        total_bytes = sum(len(chunk.encode("utf-8")) for chunk in chunks)
        log_message_sent(jid=envelope.sender_raw_jid, message_id=envelope.message_id, byte_length=total_bytes)

    async def run_forever(self) -> None:
        if not self._running:
            await self.start()
        await asyncio.Event().wait()

    async def test_connect(self) -> None:
        await self.start()
        await asyncio.sleep(2)
        await self.stop()

    async def _sync_runtime_state(self) -> None:
        self._last_connection_state = "connected" if (self._client.is_connected or self._client.is_logged_in) else "disconnected"
        created_at = await self._redis.get(REDIS_SESSION_CREATED_AT_KEY)
        if not created_at:
            metadata = await self._auth.load_metadata()
            if metadata.paired_at is not None:
                _ = await self._redis.set(
                    REDIS_SESSION_CREATED_AT_KEY,
                    datetime.fromtimestamp(metadata.paired_at, tz=UTC).isoformat(),
                )

    async def _check_postgres(self) -> bool:
        dsn = __import__("os").environ.get("DATABASE_URL")
        if not dsn:
            return False
        try:
            conn = await asyncpg.connect(dsn=dsn)
        except Exception:
            return False
        try:
            await conn.execute("SELECT 1")
            return True
        except Exception:
            return False
        finally:
            await conn.close()

    async def _check_9router(self) -> bool:
        def _ping() -> bool:
            try:
                with urlopen("http://localhost:20128/v1/models", timeout=5) as response:
                    return response.status == 200
            except URLError:
                return False
        return await asyncio.to_thread(_ping)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Guinevere WhatsApp service")
    parser.add_argument("--qr-mode", choices=["terminal"], default=None)
    parser.add_argument("--test-connect", action="store_true")
    parser.add_argument("--phone-number", default=None)
    return parser


async def _main_async(args: argparse.Namespace) -> None:
    service = WhatsAppService(phone_number=args.phone_number)
    if args.test_connect:
        await service.test_connect()
        return
    await service.run_forever()


if __name__ == "__main__":
    arguments = build_parser().parse_args()
    asyncio.run(_main_async(arguments))
