from __future__ import annotations

"""WhatsApp auth/session persistence helpers for P11 Wave 1.

This module owns:
- session metadata state
- encrypted session blob persistence in Redis
- runtime session directory management
- pairing-code fallback helper

It explicitly does not own consent, identity binding, or HARD STOP.
"""

import asyncio
import base64
import json
import os
import time
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path

import redis.asyncio as aioredis
import structlog
from neonize import NewClient

from .session_crypto import sops_decrypt_bytes, sops_encrypt_bytes

logger = structlog.get_logger()

REDIS_SESSION_KEY = "guinevere:whatsapp:session"
REDIS_SESSION_META_KEY = "guinevere:whatsapp:session:meta"
DEFAULT_SESSION_DIR = Path(
    os.environ.get(
        "GUINEVERE_WHATSAPP_SESSION_DIR",
        str(Path(__file__).resolve().parents[3] / ".runtime" / "whatsapp-session"),
    )
)
SESSION_BLOB_PATH = DEFAULT_SESSION_DIR / "session.blob"


class AuthMethod(StrEnum):
    QR_SCAN = "qr_scan"
    PAIRING_CODE = "pairing_code"


class SessionState(StrEnum):
    UNPAIRED = "unpaired"
    PAIRING = "pairing"
    PAIRED = "paired"
    EXPIRED = "expired"
    ERROR = "error"


@dataclass(slots=True)
class SessionMetadata:
    state: SessionState = SessionState.UNPAIRED
    auth_method: AuthMethod | None = None
    paired_at: float | None = None
    last_phone_online: float | None = None
    session_age_days: float = field(default=0.0)
    last_error: str | None = None

    @property
    def is_expired(self) -> bool:
        if self.last_phone_online is None:
            return False
        return (time.time() - self.last_phone_online) > (14 * 86400)

    def refresh_age(self) -> None:
        if self.paired_at is None:
            self.session_age_days = 0.0
            return
        self.session_age_days = max((time.time() - self.paired_at) / 86400.0, 0.0)

    def to_redis_mapping(self) -> dict[str, str]:
        self.refresh_age()
        return {
            "state": self.state.value,
            "auth_method": self.auth_method.value if self.auth_method else "",
            "paired_at": "" if self.paired_at is None else str(self.paired_at),
            "last_phone_online": "" if self.last_phone_online is None else str(self.last_phone_online),
            "session_age_days": str(self.session_age_days),
            "last_error": self.last_error or "",
        }

    @classmethod
    def from_redis_mapping(cls, mapping: dict[str, str]) -> SessionMetadata:
        def _to_float(value: str) -> float | None:
            return None if value in {"", "None", None} else float(value)

        auth_value = mapping.get("auth_method", "")
        metadata = cls(
            state=SessionState(mapping.get("state", SessionState.UNPAIRED.value)),
            auth_method=AuthMethod(auth_value) if auth_value else None,
            paired_at=_to_float(mapping.get("paired_at", "")),
            last_phone_online=_to_float(mapping.get("last_phone_online", "")),
            session_age_days=float(mapping.get("session_age_days", "0") or 0.0),
            last_error=mapping.get("last_error") or None,
        )
        metadata.refresh_age()
        return metadata


def build_whatsapp_redis_client() -> aioredis.Redis:
    return aioredis.Redis(
        host=os.environ.get("REDIS_HOST", "localhost"),
        port=int(os.environ.get("REDIS_PORT", "6380")),
        db=int(os.environ.get("GUINEVERE_WHATSAPP_REDIS_DB", "4")),
        username=os.environ.get("REDIS_USERNAME", "guinevere_core"),
        password=os.environ.get("REDIS_PASSWORD", ""),
        decode_responses=True,
    )


class WhatsAppAuthManager:
    def __init__(
        self,
        redis_client: aioredis.Redis | None = None,
        session_dir: Path = DEFAULT_SESSION_DIR,
    ) -> None:
        self._redis: aioredis.Redis = redis_client or build_whatsapp_redis_client()
        self._session_dir: Path = session_dir
        self._session_blob_path: Path = session_dir / "session.blob"

    @property
    def session_dir(self) -> Path:
        return self._session_dir

    @property
    def session_blob_path(self) -> Path:
        return self._session_blob_path

    async def ensure_runtime_dir(self) -> Path:
        self._session_dir.mkdir(parents=True, exist_ok=True)
        return self._session_dir

    async def load_metadata(self) -> SessionMetadata:
        raw = await self._redis.hgetall(REDIS_SESSION_META_KEY)
        if not raw:
            return SessionMetadata()
        normalized = {
            (key.decode("utf-8") if isinstance(key, bytes) else str(key)): (
                value.decode("utf-8") if isinstance(value, bytes) else str(value)
            )
            for key, value in raw.items()
        }
        metadata = SessionMetadata.from_redis_mapping(normalized)
        if metadata.is_expired:
            metadata.state = SessionState.EXPIRED
        return metadata

    async def save_metadata(self, metadata: SessionMetadata) -> None:
        mapping = metadata.to_redis_mapping()
        _ = await self._redis.delete(REDIS_SESSION_META_KEY)
        for field_name, field_value in mapping.items():
            _ = await self._redis.hset(REDIS_SESSION_META_KEY, field_name, field_value)

    async def update_state(
        self,
        state: SessionState,
        *,
        auth_method: AuthMethod | None = None,
        error: str | None = None,
    ) -> SessionMetadata:
        metadata = await self.load_metadata()
        metadata.state = state
        metadata.last_error = error
        if auth_method is not None:
            metadata.auth_method = auth_method
        if state == SessionState.PAIRED and metadata.paired_at is None:
            metadata.paired_at = time.time()
        await self.save_metadata(metadata)
        return metadata

    async def mark_phone_online(self) -> SessionMetadata:
        metadata = await self.load_metadata()
        metadata.last_phone_online = time.time()
        if metadata.paired_at is None:
            metadata.paired_at = metadata.last_phone_online
        metadata.state = SessionState.PAIRED
        await self.save_metadata(metadata)
        return metadata

    async def save_session_blob(self, session_blob: bytes) -> None:
        encrypted = sops_encrypt_bytes(session_blob)
        encoded = base64.b64encode(encrypted).decode("ascii")
        _ = await self._redis.set(REDIS_SESSION_KEY, encoded)
        _ = await self.ensure_runtime_dir()
        _ = self._session_blob_path.write_bytes(session_blob)
        logger.info(
            "whatsapp_session_blob_saved",
            redis_key=REDIS_SESSION_KEY,
            runtime_path=str(self._session_blob_path),
            size_bytes=len(session_blob),
        )

    async def load_session_blob(self) -> bytes | None:
        encoded = await self._redis.get(REDIS_SESSION_KEY)
        if not encoded:
            if self._session_blob_path.exists():
                return self._session_blob_path.read_bytes()
            return None
        encoded_text = encoded.decode("ascii") if isinstance(encoded, bytes) else str(encoded)
        encrypted = base64.b64decode(encoded_text.encode("ascii"))
        return sops_decrypt_bytes(encrypted)

    async def clear(self) -> None:
        _ = await self._redis.delete(REDIS_SESSION_KEY, REDIS_SESSION_META_KEY)
        if self._session_blob_path.exists():
            _ = self._session_blob_path.unlink()
        logger.info("whatsapp_session_state_cleared")

    async def export_metadata_json(self) -> str:
        metadata = await self.load_metadata()
        return json.dumps(metadata.to_redis_mapping(), sort_keys=True)

    async def generate_pairing_code(
        self,
        client: NewClient,
        phone_number: str,
        *,
        show_push_notification: bool = False,
    ) -> str:
        _ = await self.update_state(SessionState.PAIRING, auth_method=AuthMethod.PAIRING_CODE)
        code = await asyncio.to_thread(
            client.PairPhone,
            phone_number,
            show_push_notification,
        )
        logger.info("whatsapp_pairing_code_generated")
        return code

    async def persist_runtime_snapshot(self, payload: bytes, *, state: SessionState) -> None:
        await self.save_session_blob(payload)
        _ = await self.update_state(state)

    async def close(self) -> None:
        await self._redis.aclose()
