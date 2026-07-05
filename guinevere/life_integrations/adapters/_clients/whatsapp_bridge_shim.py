"""P22 WhatsApp loopback HTTP bridge shim.

This shim wraps the running ``guinevere-whatsapp.service`` (an in-VPS Node/Baileys
process) over loopback HTTP at ``127.0.0.1:8095``. The shim speaks only over the
loopback interface to the local bridge service — it does NOT carry WhatsApp
session secrets, does NOT auto-login / re-link, and does NOT send unsolicited
messages.

Capability / risk tier mapping:

- **L1 (health / read-only)**: safe without consent. ``health()`` is a GET to
  ``/health`` and exposes only boolean readiness + connection state. Logs do
  not include any JID or message body.
- **L2 (send_text)**: consent-gated by the P22 consent router + operator-designated
  test target only. ``send_message()`` POSTs to ``/admin/send-test`` and only
  logs ``target_hash`` (the first 12 hex chars of ``sha256(jid)``) — never the
  raw JID, never the message body. The target must be whitelisted by the
  operator (the bridge service refuses non-test targets).
- **L3 (delete_message)**: DEFERRED — the running ``guinevere-whatsapp.service``
  does not expose a delete path through its service bus. ``delete_message()``
  raises ``ConfigurationMissingError`` immediately (fail-closed; no fake
  success; no silent no-op).
- **L4 (promote_admin)**: FORBIDDEN in the adapter layer. The shim does not
  expose it at all; the P22 router must also refuse ``promote_admin`` as an
  ``L4_FORBIDDEN`` action.

No auto-login, no re-link of disconnected sessions, no session secret exposure
on the loopback socket, no outbound calls to WhatsApp servers — only to the
operator-controlled local bridge service.

Fail-closed: any non-200 response, transport exception, or unsupported
operation raises ``ConfigurationMissingError`` (no fake PASS).
"""

from __future__ import annotations

import hashlib
import os
from typing import Any

import structlog

from guinevere.life_integrations.errors import ConfigurationMissingError

logger = structlog.get_logger(__name__)


class WhatsAppBridgeShim:
    """Loopback HTTP bridge to the running ``guinevere-whatsapp.service``.

    The constructor holds only the bridge URL (defaulting to the operator-set
    ``WHATSAPP_BRIDGE_URL`` env var, or the loopback default
    ``http://127.0.0.1:8095``) and an HTTP timeout. The shim does not hold any
    WhatsApp session secret — the bridge service owns those — and only
    communicates over loopback.

    Args:
        bridge_url: Optional override for the bridge base URL. Defaults to
            ``$WHATSAPP_BRIDGE_URL`` or ``http://127.0.0.1:8095``.
        timeout: HTTP timeout (seconds) for bridge calls.
    """

    # Log key prefix for all shim events (matches the ``p22.*`` convention).
    LOG_PREFIX = "p22.whatsapp.shim"

    def __init__(
        self,
        bridge_url: str | None = None,
        timeout: float = 5.0,
    ) -> None:
        self._bridge_url: str = (
            bridge_url
            or os.environ.get("WHATSAPP_BRIDGE_URL", "http://127.0.0.1:8095")
        )
        self._timeout: float = timeout

    @staticmethod
    def _hash_jid(jid: str) -> str:
        """Return the first 12 hex chars of ``sha256(jid)`` for safe logging.

        We only ever log the hash, never the raw JID. The 12-char prefix is
        long enough to be effectively unique per JID while keeping log lines
        short and unlinkable to a specific user.
        """
        return hashlib.sha256(jid.encode()).hexdigest()[:12]

    async def health(self) -> bool:
        """Probe bridge readiness.

        Returns ``True`` only when the bridge reports ``status == "ready"`` and
        ``connection_state == "connected"``. The raw ``service_running`` field
        is intentionally NOT used as a health signal: it is known to flip to
        ``false`` even while the bridge is actually connected (an upstream
        service-bus quirk). Returns ``False`` on any non-200 response or
        transport exception (with a structlog event; never raises).
        """
        import httpx

        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.get(f"{self._bridge_url}/health")
            if resp.status_code != 200:
                logger.warning(
                    f"{self.LOG_PREFIX}.health.non_200",
                    status_code=resp.status_code,
                    bridge_url=self._bridge_url,
                )
                return False
            data: dict[str, Any] = resp.json()
            ready = data.get("status") == "ready"
            connected = data.get("connection_state") == "connected"
            if not (ready and connected):
                logger.warning(
                    f"{self.LOG_PREFIX}.health.not_ready",
                    status=data.get("status"),
                    connection_state=data.get("connection_state"),
                )
                return False
            return True
        except Exception as exc:
            logger.warning(
                f"{self.LOG_PREFIX}.health.exception",
                bridge_url=self._bridge_url,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            return False

    async def send_message(self, jid: str, text: str) -> dict[str, Any]:
        """Send one message to a JID via the bridge ``/admin/send-test`` endpoint.

        The bridge service is operator-designated to only accept
        operator-designated test targets (e.g. the operator's own JID); the
        router must have already verified consent for
        ``consent.comms.whatsapp.send`` and the L2 capability tier.

        Args:
            jid: Destination JID (the raw JID is NEVER logged; only the hash).
            text: Message body (the body itself is NEVER logged).

        Returns:
            ``{"ok": True, "result": <bridge json response>}`` on 200.

        Raises:
            ConfigurationMissingError: if the bridge returns non-200 (caller
                should report the integration as CONFIG_MISSING, not fake
                success). This is fail-closed.
        """
        import httpx

        target_hash = self._hash_jid(jid)
        try:
            async with httpx.AsyncClient(timeout=self._timeout) as client:
                resp = await client.post(
                    f"{self._bridge_url}/admin/send-test",
                    json={"target": jid, "message": text},
                )
        except Exception as exc:
            logger.error(
                f"{self.LOG_PREFIX}.send.transport_exception",
                target_hash=target_hash,
                error_type=type(exc).__name__,
                error=str(exc),
            )
            raise ConfigurationMissingError(
                "whatsapp send-test transport failure"
            ) from exc

        if resp.status_code != 200:
            logger.error(
                f"{self.LOG_PREFIX}.send.non_200",
                target_hash=target_hash,
                status_code=resp.status_code,
            )
            raise ConfigurationMissingError("whatsapp send-test failed")

        logger.info(
            f"{self.LOG_PREFIX}.send.ok",
            target_hash=target_hash,
        )
        return {"ok": True, "result": resp.json()}

    async def delete_message(self, jid: str, key: str) -> dict[str, Any]:
        """Delete one message — DEFERRED (service bus gap).

        The running ``guinevere-whatsapp.service`` does not currently expose a
        delete-Message path in its service bus (WhatsApp/Baileys delete API
        requires the message ``key`` plus the originating session, and the
        bridge service has no route for it). This shim therefore raises
        ``ConfigurationMissingError`` immediately rather than attempting any
        network call. This is fail-closed: the P22 router will surface the
        operation as a L3 DEFERRED failure (not a silent success).

        Args:
            jid: Destination JID of the message to delete (unused; logged only
                as hash for traceability).
            key: Bridge / WhatsApp message key (unused).

        Raises:
            ConfigurationMissingError: always (L3 path not exposed by bridge
                service bus).
        """
        target_hash = self._hash_jid(jid)
        logger.warning(
            f"{self.LOG_PREFIX}.delete.deferred",
            target_hash=target_hash,
        )
        raise ConfigurationMissingError(
            "whatsapp delete path not exposed by service bus — L3 DEFERRED"
        )
