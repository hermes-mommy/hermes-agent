from __future__ import annotations

"""P11-017 — WhatsApp number whitelist and identity binding.

This is the first safety gate in the WhatsApp runtime path. Unknown senders are
silently dropped. The single approved operator identity is projected downstream
so later stages do not need to resolve raw JIDs repeatedly.
"""

from dataclasses import dataclass, replace
import re

import redis.asyncio as aioredis
import structlog

from .auth import build_whatsapp_redis_client
from .envelope import WhatsAppMessageEnvelope, normalize_jid

logger = structlog.get_logger()

REDIS_WHITELIST_KEY = "guinevere:whatsapp:whitelist"
OPERATOR_IDENTITY = "Faiz"
_ALLOWED_PERSONAL_JID = re.compile(r"^\d{10,15}(?::\d+)?@s\.whatsapp\.net$")


@dataclass(frozen=True, slots=True)
class WhitelistDecision:
    allowed: bool
    envelope: WhatsAppMessageEnvelope | None
    reason: str
    normalized_phone: str | None = None
    identity: str | None = None


class WhitelistManager:
    """Redis-backed WhatsApp whitelist gate.

    Fail-closed on Redis errors. Unknown senders are dropped silently.
    """

    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        *,
        whitelist_key: str = REDIS_WHITELIST_KEY,
        operator_identity: str = OPERATOR_IDENTITY,
    ) -> None:
        self._redis: aioredis.Redis = redis_client or build_whatsapp_redis_client()
        self._whitelist_key: str = whitelist_key
        self._operator_identity: str = operator_identity

    async def allow_phone(self, phone_or_jid: str) -> bool:
        member = normalize_jid(phone_or_jid)
        _ = await self._redis.sadd(self._whitelist_key, member)
        logger.info("whatsapp_whitelist_added", phone=member)
        return True

    async def remove_phone(self, phone_or_jid: str) -> bool:
        member = normalize_jid(phone_or_jid)
        removed = await self._redis.srem(self._whitelist_key, member)
        logger.info("whatsapp_whitelist_removed", phone=member, removed=bool(removed))
        return bool(removed)

    async def list_allowed(self) -> set[str]:
        members = await self._redis.smembers(self._whitelist_key)
        return {normalize_jid(str(member)) for member in members}

    async def evaluate(self, envelope: WhatsAppMessageEnvelope) -> WhitelistDecision:
        try:
            if not self._is_valid_personal_jid(envelope.sender_raw_jid):
                return WhitelistDecision(
                    allowed=False,
                    envelope=None,
                    reason="invalid_personal_jid",
                )

            normalized_phone = envelope.normalized_sender_phone()
            is_member = await self._redis.sismember(self._whitelist_key, normalized_phone)
            if not bool(is_member):
                logger.info(
                    "whatsapp_sender_not_whitelisted",
                    sender=envelope.sender_jid_hash,
                    phone=normalized_phone,
                )
                return WhitelistDecision(
                    allowed=False,
                    envelope=None,
                    reason="not_whitelisted",
                    normalized_phone=normalized_phone,
                )

            bound = replace(envelope, sender_identity=self._operator_identity)
            return WhitelistDecision(
                allowed=True,
                envelope=bound,
                reason="allowed",
                normalized_phone=normalized_phone,
                identity=self._operator_identity,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("whatsapp_whitelist_failed_closed", error=str(exc))
            return WhitelistDecision(
                allowed=False,
                envelope=None,
                reason="redis_failure",
            )

    def _is_valid_personal_jid(self, jid: str) -> bool:
        if jid.endswith("@g.us"):
            return False
        return bool(_ALLOWED_PERSONAL_JID.fullmatch(jid.strip()))
