from __future__ import annotations

from dataclasses import replace

import pytest

from src.channels.whatsapp.consent_manager import WhatsAppConsentManager
from src.channels.whatsapp.envelope import WhatsAppMessageEnvelope, ensure_utc_timestamp
from src.channels.whatsapp.hard_stop import WhatsAppHardStopGate
from src.channels.whatsapp.policy import MEDIA_ACK_RESPONSE, WhatsAppPolicyGate
from src.channels.whatsapp.rate_limiter import WhatsAppRateLimiter
from src.channels.whatsapp.whitelist import WhitelistManager


class FakeRedis:
    def __init__(self) -> None:
        self._sets: dict[str, set[str]] = {}
        self._hashes: dict[str, dict[str, str]] = {}
        self._strings: dict[str, str] = {}
        self._zsets: dict[str, dict[str, float]] = {}

    async def sadd(self, key: str, member: str) -> int:
        bucket = self._sets.setdefault(key, set())
        before = len(bucket)
        bucket.add(member)
        return 1 if len(bucket) > before else 0

    async def srem(self, key: str, member: str) -> int:
        bucket = self._sets.setdefault(key, set())
        if member in bucket:
            bucket.remove(member)
            return 1
        return 0

    async def smembers(self, key: str) -> set[str]:
        return set(self._sets.get(key, set()))

    async def sismember(self, key: str, member: str) -> bool:
        return member in self._sets.get(key, set())

    async def hgetall(self, key: str) -> dict[str, str]:
        return dict(self._hashes.get(key, {}))

    async def hset(self, key: str, field: str, value: str) -> int:
        self._hashes.setdefault(key, {})[field] = value
        return 1

    async def delete(self, key: str) -> int:
        removed = 0
        if key in self._hashes:
            del self._hashes[key]
            removed += 1
        if key in self._strings:
            del self._strings[key]
            removed += 1
        if key in self._zsets:
            del self._zsets[key]
            removed += 1
        return removed

    async def set(self, key: str, value: str, *, ex: int | None = None, nx: bool = False):
        if nx and key in self._strings:
            return False
        self._strings[key] = value
        return True

    async def zremrangebyscore(self, key: str, _min: str | float, max_score: float) -> int:
        bucket = self._zsets.setdefault(key, {})
        to_delete = [member for member, score in bucket.items() if score <= float(max_score)]
        for member in to_delete:
            del bucket[member]
        return len(to_delete)

    async def zcard(self, key: str) -> int:
        return len(self._zsets.get(key, {}))

    async def zadd(self, key: str, mapping: dict[str, float]) -> int:
        bucket = self._zsets.setdefault(key, {})
        for member, score in mapping.items():
            bucket[member] = score
        return len(mapping)

    async def expire(self, key: str, _ttl: int) -> bool:
        return key in self._zsets or key in self._strings

    async def zrangebyscore(self, key: str, min_score: float, max_score: str | float, *, start: int = 0, num: int = 1, withscores: bool = False):
        bucket = self._zsets.get(key, {})
        upper = float("inf") if max_score == "+inf" else float(max_score)
        filtered = [(member, score) for member, score in bucket.items() if float(min_score) <= score <= upper]
        filtered.sort(key=lambda item: item[1])
        sliced = filtered[start:start + num]
        if withscores:
            return sliced
        return [member for member, _score in sliced]


@pytest.fixture
def sample_envelope() -> WhatsAppMessageEnvelope:
    return WhatsAppMessageEnvelope(
        sender_jid_hash="abc123",
        sender_raw_jid="628123456789@s.whatsapp.net",
        message_id="mid-1",
        timestamp=ensure_utc_timestamp(1_700_000_000),
        body="hello mommy",
        chat_jid="628123456789@s.whatsapp.net",
        is_group=False,
    )


@pytest.mark.asyncio
async def test_whitelist_binds_identity(sample_envelope: WhatsAppMessageEnvelope) -> None:
    redis = FakeRedis()
    manager = WhitelistManager(redis)
    await manager.allow_phone("628123456789")

    decision = await manager.evaluate(sample_envelope)

    assert decision.allowed is True
    assert decision.identity == "Faiz"
    assert decision.envelope is not None
    assert decision.envelope.sender_identity == "Faiz"


@pytest.mark.asyncio
async def test_whitelist_denies_unknown_sender(sample_envelope: WhatsAppMessageEnvelope) -> None:
    redis = FakeRedis()
    manager = WhitelistManager(redis)

    decision = await manager.evaluate(sample_envelope)

    assert decision.allowed is False
    assert decision.envelope is None
    assert decision.reason == "not_whitelisted"


def test_hard_stop_blocks_and_recovers(sample_envelope: WhatsAppMessageEnvelope) -> None:
    gate = WhatsAppHardStopGate()

    blocked = gate.evaluate(replace(sample_envelope, body="hard stop sekarang"))
    assert blocked.blocked is True
    assert blocked.response is not None

    recovery = gate.evaluate(replace(sample_envelope, body="resume"))
    assert recovery.blocked is False
    assert recovery.response == "Persona mode restored. Welcome back, darling."


@pytest.mark.asyncio
async def test_consent_gate_default_denies(sample_envelope: WhatsAppMessageEnvelope) -> None:
    redis = FakeRedis()
    manager = WhatsAppConsentManager(redis)

    denied = await manager.evaluate(replace(sample_envelope, sender_identity="Faiz"))
    assert denied.allowed is False
    assert denied.response is not None

    await manager.grant()
    allowed = await manager.evaluate(replace(sample_envelope, sender_identity="Faiz"))
    assert allowed.allowed is True
    assert allowed.envelope is not None


@pytest.mark.asyncio
async def test_rate_limiter_dedup_and_limits(sample_envelope: WhatsAppMessageEnvelope) -> None:
    redis = FakeRedis()
    limiter = WhatsAppRateLimiter(redis)

    first = await limiter.check_inbound_dedup(sample_envelope)
    second = await limiter.check_inbound_dedup(sample_envelope)
    assert first.allowed is True
    assert second.allowed is False
    assert second.reason == "duplicate"

    target = "628123456789"
    decisions = [await limiter.reserve_outbound_slot(target) for _ in range(8)]
    assert all(item.allowed for item in decisions)
    blocked = await limiter.reserve_outbound_slot(target)
    assert blocked.allowed is False
    assert blocked.reason == "rate_limited_minute"
    assert blocked.retry_after_seconds is not None


def test_policy_gate_media_and_group(sample_envelope: WhatsAppMessageEnvelope) -> None:
    gate = WhatsAppPolicyGate()

    group = gate.evaluate(replace(sample_envelope, is_group=True, chat_jid="120363@g.us"))
    assert group.allowed is False
    assert group.action == "drop"

    media = gate.evaluate(replace(sample_envelope, body="", media_type="image"))
    assert media.allowed is False
    assert media.action == "ack_media"
    assert media.response_body == MEDIA_ACK_RESPONSE

    text_ok = gate.evaluate(sample_envelope)
    assert text_ok.allowed is True
    assert text_ok.action == "pass"
    assert text_ok.envelope == sample_envelope
