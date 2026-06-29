"""HMAC-verified surveillance event ingest.

Ports: src/surveillance/auth.py, classification.py, models.py, replay.py,
secrets.py, secret_scanner.py.

Consolidates HMAC-SHA256 verification (X-Signature/X-Timestamp/X-Nonce),
data classification, Pydantic v2 request/response models, replay protection
(timestamp window 300s + nonce dedup), HMAC secret loading (env-first,
SOPS fallback), and clipboard secret scanning (16 regex patterns + Shannon
entropy).

NOTE: operator approval gating is NOT ported per ADR-062. Hermes owns all
surveillance decisions.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import math
import os
import re
import subprocess
import time
import uuid
from collections import Counter
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final, Literal

import structlog
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, field_validator

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# DataClassification (from classification.py)
# ---------------------------------------------------------------------------


class DataClassification(StrEnum):
    """Security classification levels for surveillance event data."""

    INTERNAL = "Internal"
    CONFIDENTIAL = "Confidential"
    RESTRICTED = "Restricted"
    CRITICAL = "Critical"


@dataclass(frozen=True)
class ClassificationResult:
    """Result of classifying a surveillance event."""

    classification: DataClassification
    purpose: str
    retention_class: str
    access_policy: str
    encryption_profile: str


EVENT_TYPE_CLASSIFICATION: Final[dict[str, ClassificationResult]] = {
    "app_usage": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "screen_state": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="activity_tracking",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "active_window": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "idle_time": ClassificationResult(
        classification=DataClassification.RESTRICTED,
        purpose="activity_tracking",
        retention_class="short_raw",
        access_policy="guinevere_core",
        encryption_profile="high",
    ),
    "notification": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="context_awareness",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "browser": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="productivity_monitoring",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "location": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="safety_geofencing",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "call_log": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="context_awareness",
        retention_class="short_raw",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "health": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="health_monitoring",
        retention_class="medium_operational",
        access_policy="guinevere_core+faiz",
        encryption_profile="double_high",
    ),
    "clipboard": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="secret_protection",
        retention_class="transient",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
    "screenshot": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="visual_context",
        retention_class="critical_media",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
    "camera": ClassificationResult(
        classification=DataClassification.CRITICAL,
        purpose="visual_context",
        retention_class="critical_media",
        access_policy="guinevere_core_only",
        encryption_profile="double_high",
    ),
}

_DEFAULT_CONFIDENTIAL: Final[ClassificationResult] = ClassificationResult(
    classification=DataClassification.CONFIDENTIAL,
    purpose="unknown",
    retention_class="transient",
    access_policy="guinevere_core+faiz",
    encryption_profile="enhanced",
)


def classify_event(event_type: str) -> ClassificationResult:
    """Classify a surveillance event type.

    Unknown event types default to Confidential (fail-closed).
    """
    result = EVENT_TYPE_CLASSIFICATION.get(event_type, _DEFAULT_CONFIDENTIAL)
    logger.debug(
        "event_classified",
        event_type=event_type,
        classification=result.classification.value,
        is_known=event_type in EVENT_TYPE_CLASSIFICATION,
    )
    return result


_RETENTION_DAYS: Final[dict[str, int]] = {
    "transient": 1,
    "short_raw": 7,
    "critical_media": 1,
    "medium_operational": 90,
    "long_term_curated": 365,
    "regulated_audit": 365,
    "formal_hold": 730,
}


def get_retention_days(retention_class: str) -> int:
    """Return the maximum retention period in days for a retention class.

    Unknown retention classes default to 1 day (fail-closed).
    """
    return _RETENTION_DAYS.get(retention_class, 1)


# ---------------------------------------------------------------------------
# Pydantic v2 models (from models.py)
# ---------------------------------------------------------------------------


class SurveillanceEventRequest(BaseModel):
    """Validated payload accepted at POST /surveillance/events."""

    model_config = ConfigDict(extra="forbid", strict=True)

    device_id: str = Field(..., min_length=1, max_length=128)
    event_type: Literal[
        "app_usage",
        "screen_state",
        "notification",
        "location",
        "clipboard",
        "call_log",
        "health",
        "browser",
        "active_window",
        "idle_time",
        "screenshot",
        "camera",
    ]
    occurred_at: datetime
    payload: dict[str, Any]
    metadata: dict[str, Any] | None = None

    @field_validator("occurred_at", mode="before")
    @classmethod
    def _parse_occurred_at(cls, v: Any) -> datetime:
        """Pre-parse ISO-8601 datetime strings so strict mode accepts them."""
        if isinstance(v, str):
            dt = datetime.fromisoformat(v)
            if dt.tzinfo is None:
                raise ValueError("occurred_at must be timezone-aware")
            return dt
        return v


class SurveillanceEventResponse(BaseModel):
    """Returned to the caller on successful event ingestion (202 Accepted)."""

    model_config = ConfigDict(extra="forbid", strict=True)

    status: Literal["accepted"]
    event_id: str
    received_at: datetime


class ErrorResponse(BaseModel):
    """Returned on validation or processing errors."""

    model_config = ConfigDict(extra="forbid", strict=True)

    detail: str
    error_code: str


# ---------------------------------------------------------------------------
# Secret scanner (from secret_scanner.py)
# ---------------------------------------------------------------------------

REDACTION_MARKER: Final[str] = "[REDACTED]"
ENTROPY_THRESHOLD: Final[float] = 4.5
MIN_ENTROPY_STRING_LENGTH: Final[int] = 32


@dataclass(frozen=True)
class SecretPattern:
    """A named regex pattern for detecting a specific secret type."""

    name: str
    pattern: re.Pattern[str]
    description: str


@dataclass(frozen=True)
class ScanResult:
    """Result of scanning text for secrets."""

    has_secrets: bool
    secret_types: list[str] = field(default_factory=list)
    redacted_text: str = ""
    secrets_found: int = 0


PATTERNS: Final[list[SecretPattern]] = [
    SecretPattern(
        name="aws_access_key",
        pattern=re.compile(r"(?<![A-Z0-9])(AKIA[0-9A-Z]{16})(?![A-Z0-9])"),
        description="AWS Access Key ID",
    ),
    SecretPattern(
        name="aws_secret_key",
        pattern=re.compile(
            r"(?i)aws[_\-]?secret[_\-]?(?:access)?[_\-]?key\s*[:=]\s*['\"]?([A-Za-z0-9/+=]{40})['\"]?"
        ),
        description="AWS Secret Access Key assignment",
    ),
    SecretPattern(
        name="github_pat",
        pattern=re.compile(
            r"(ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9]{22}_[A-Za-z0-9]{59})"
        ),
        description="GitHub Personal Access Token",
    ),
    SecretPattern(
        name="github_oauth",
        pattern=re.compile(r"gho_[A-Za-z0-9]{36}"),
        description="GitHub OAuth token",
    ),
    SecretPattern(
        name="openai_api_key",
        pattern=re.compile(r"sk-[a-zA-Z0-9]{48}"),
        description="OpenAI API Key",
    ),
    SecretPattern(
        name="generic_api_key",
        pattern=re.compile(
            r"(?i)(api[_\-]?key|apikey|api[_\-]?secret)\s*[:=]\s*['\"]?([A-Za-z0-9_\-]{20,64})['\"]?"
        ),
        description="Generic API key assignment",
    ),
    SecretPattern(
        name="bearer_token",
        pattern=re.compile(r"(?i)bearer\s+([A-Za-z0-9_\-\.]{20,512})"),
        description="Bearer token in Authorization header",
    ),
    SecretPattern(
        name="jwt",
        pattern=re.compile(r"eyJ[A-Za-z0-9_-]+\.eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
        description="JSON Web Token",
    ),
    SecretPattern(
        name="pem_key",
        pattern=re.compile(
            r"-----BEGIN\s+(RSA\s+|EC\s+|DSA\s+|OPENSSH\s+)?PRIVATE\s+KEY-----"
        ),
        description="PEM Private Key header",
    ),
    SecretPattern(
        name="db_connection",
        pattern=re.compile(r"(postgresql|postgres|mysql|mongodb|redis)://[^\s'\"]+"),
        description="Database connection string",
    ),
    SecretPattern(
        name="discord_token",
        pattern=re.compile(r"[MN][A-Za-z\d]{23,}\.[\w-]{6}\.[\w-]{27,}"),
        description="Discord Bot Token",
    ),
    SecretPattern(
        name="slack_token",
        pattern=re.compile(
            r"xox[bpors]-[0-9]{10,13}-[0-9]{10,13}-[0-9]{10,13}-[a-f0-9]{32}"
        ),
        description="Slack API Token",
    ),
    SecretPattern(
        name="stripe_key",
        pattern=re.compile(r"sk_(live|test)_[A-Za-z0-9]{24,}"),
        description="Stripe API Key",
    ),
    SecretPattern(
        name="google_api_key",
        pattern=re.compile(r"AIza[0-9A-Za-z_-]{35}"),
        description="Google API Key",
    ),
    SecretPattern(
        name="age_key",
        pattern=re.compile(r"AGE-SECRET-KEY-1[A-Z0-9]{58}"),
        description="age secret key",
    ),
    SecretPattern(
        name="password_url",
        pattern=re.compile(r"://[^:]+:([^\s@]+)@"),
        description="Password embedded in URL",
    ),
    SecretPattern(
        name="password_assignment",
        pattern=re.compile(
            r"(?i)(password|passwd|pwd|pass)\s*[:=]\s*['\"]([^\s'\"]{8,})['\"]"
        ),
        description="Password assignment in code",
    ),
]

_HIGH_ENTROPY_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9])[A-Za-z0-9_\-/+=]{32,}(?![A-Za-z0-9])"
)

_WHITELIST_PATTERNS: Final[list[re.Pattern[str]]] = [
    re.compile(r"^[a-fA-F0-9]{32,64}$"),
    re.compile(
        r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$",
        re.IGNORECASE,
    ),
    re.compile(r"^data:image/[a-z]+;base64,"),
]


def shannon_entropy(data: str) -> float:
    """Calculate Shannon entropy of a string."""
    if not data:
        return 0.0
    counter = Counter(data)
    length = len(data)
    return -sum(
        (count / length) * math.log2(count / length) for count in counter.values()
    )


def _is_whitelisted(text: str) -> bool:
    """Check if a string matches known safe patterns (hashes, UUIDs, etc.)."""
    for pattern in _WHITELIST_PATTERNS:
        if pattern.match(text):
            return True
    return False


def scan_text(text: str) -> ScanResult:
    """Scan text for secrets and return a detailed result.

    Checks all compiled regex patterns first, then falls back to
    high-entropy string detection with Shannon entropy >= 4.5.
    """
    if not text:
        logger.info("secret_scan_empty_text")
        return ScanResult(
            has_secrets=False, secret_types=[], redacted_text="", secrets_found=0
        )

    secret_types: list[str] = []
    total_secrets = 0
    redacted = text

    for secret_pattern in PATTERNS:
        matches = secret_pattern.pattern.findall(redacted)
        if matches:
            count = len(matches)
            total_secrets += count
            secret_types.append(secret_pattern.name)
            redacted = secret_pattern.pattern.sub(REDACTION_MARKER, redacted)
            logger.info(
                "secret_detected",
                secret_type=secret_pattern.name,
                count=count,
                text_length=len(text),
            )

    entropy_matches = _HIGH_ENTROPY_PATTERN.findall(redacted)
    for match_str in entropy_matches:
        if match_str == REDACTION_MARKER:
            continue
        if len(match_str) < MIN_ENTROPY_STRING_LENGTH:
            continue
        if _is_whitelisted(match_str):
            continue
        entropy = shannon_entropy(match_str)
        if entropy >= ENTROPY_THRESHOLD:
            total_secrets += 1
            if "high_entropy" not in secret_types:
                secret_types.append("high_entropy")
            redacted = redacted.replace(match_str, REDACTION_MARKER, 1)
            logger.info(
                "secret_detected",
                secret_type="high_entropy",
                entropy=round(entropy, 2),
                string_length=len(match_str),
                text_length=len(text),
            )

    has_secrets = total_secrets > 0
    if has_secrets:
        logger.info(
            "secret_scan_complete",
            secrets_found=total_secrets,
            secret_types=secret_types,
            text_length=len(text),
        )
    else:
        logger.info("secret_scan_clean", text_length=len(text))

    return ScanResult(
        has_secrets=has_secrets,
        secret_types=secret_types,
        redacted_text=redacted,
        secrets_found=total_secrets,
    )


def redact_secrets(text: str) -> str:
    """Return text with all detected secrets replaced by [REDACTED]."""
    if not text:
        return text
    result = scan_text(text)
    return result.redacted_text


# ---------------------------------------------------------------------------
# HMAC secret loader (from secrets.py)
# ---------------------------------------------------------------------------

_ENV_VAR: str = "SURVEILLANCE_HMAC_SECRET"
_SECRETS_FILE: Path = Path(__file__).resolve().parents[2] / "secrets" / "guinevere-secrets.yaml"

_cached_secret: str | None = None


def _decrypt_sops_secret() -> str:
    """Decrypt ``surveillance.hmac_secret`` from the SOPS-encrypted YAML."""
    if not _SECRETS_FILE.exists():
        raise FileNotFoundError(
            f"SOPS secrets file not found: {_SECRETS_FILE}"
        )

    result = subprocess.run(
        ["sops", "--decrypt", str(_SECRETS_FILE)],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        logger.error(
            "sops_decrypt_failed",
            returncode=result.returncode,
            stderr=result.stderr.strip(),
        )
        raise RuntimeError(
            f"SOPS decryption failed (exit {result.returncode}): "
            f"{result.stderr.strip()}"
        )

    data: dict[str, object] | None = json.loads(result.stdout)
    if not isinstance(data, dict):
        raise RuntimeError("SOPS decryption returned unexpected non-dict output")

    surveillance = data.get("surveillance")
    if not isinstance(surveillance, dict):
        raise RuntimeError(
            "'surveillance' section missing or invalid in decrypted secrets"
        )

    secret = surveillance.get("hmac_secret")
    if not isinstance(secret, str) or not secret:
        raise RuntimeError(
            "'surveillance.hmac_secret' is missing or empty in decrypted secrets"
        )

    return secret


def get_hmac_secret() -> str:
    """Return the surveillance HMAC secret string.

    Resolution order:
    1. Cache (previous call already resolved)
    2. Environment variable SURVEILLANCE_HMAC_SECRET
    3. SOPS-encrypted secrets file
    """
    global _cached_secret  # noqa: PLW0603

    if _cached_secret is not None:
        return _cached_secret

    env_value = os.environ.get(_ENV_VAR)
    if env_value:
        logger.debug("hmac_secret_resolved", source="environment")
        _cached_secret = env_value
        return _cached_secret

    logger.debug("hmac_secret_resolving", source="sops")
    _cached_secret = _decrypt_sops_secret()
    logger.debug("hmac_secret_resolved", source="sops")
    return _cached_secret


def _clear_cache() -> None:
    """Reset the cached secret to None. For test isolation only."""
    global _cached_secret  # noqa: PLW0603
    _cached_secret = None


# ---------------------------------------------------------------------------
# Replay protection (from replay.py)
# ---------------------------------------------------------------------------

TIMESTAMP_WINDOW_SECONDS: int = 300
NONCE_TTL_SECONDS: int = 660
NONCE_KEY_PREFIX: str = "surveillance:nonce:"

_nonce_store: dict[str, float] = {}
"""In-memory nonce store used when Redis is unavailable. Maps nonce -> expiry."""


async def validate_timestamp(timestamp: str) -> None:
    """Raise HTTPException(401) if timestamp is outside the allowed window."""
    try:
        ts = int(timestamp)
    except (ValueError, TypeError):
        logger.warning("replay_timestamp_invalid_format", timestamp=timestamp)
        raise HTTPException(status_code=401, detail="Request expired")

    now = int(time.time())
    diff = abs(now - ts)

    if diff > TIMESTAMP_WINDOW_SECONDS:
        logger.warning(
            "replay_timestamp_expired",
            server_time=now,
            request_timestamp=ts,
            diff_seconds=diff,
            window_seconds=TIMESTAMP_WINDOW_SECONDS,
        )
        raise HTTPException(status_code=401, detail="Request expired")

    logger.debug("replay_timestamp_valid", timestamp=ts, server_time=now)


async def check_nonce(nonce: str, redis_client: Any = None) -> None:
    """Atomically store nonce and reject duplicates.

    Uses Redis SET NX EX when a client is provided; falls back to an
    in-memory dict when Redis is unavailable (fail-soft).
    """
    if redis_client is not None:
        nonce_key = f"{NONCE_KEY_PREFIX}{nonce}"
        try:
            result = await redis_client.set(
                nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS
            )
            if result is None:
                logger.warning(
                    "replay_nonce_duplicate",
                    nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
                )
                raise HTTPException(status_code=409, detail="Replay detected")
            logger.debug(
                "replay_nonce_accepted",
                nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
            )
            return
        except HTTPException:
            raise
        except (ConnectionError, TimeoutError, OSError):
            logger.exception(
                "replay_redis_error",
                nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
            )
            # Fail-soft: fall through to in-memory store

    # In-memory fallback
    now = time.time()
    # Evict expired nonces
    expired = [k for k, exp in _nonce_store.items() if exp < now]
    for k in expired:
        del _nonce_store[k]

    if nonce in _nonce_store:
        logger.warning(
            "replay_nonce_duplicate",
            nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
        )
        raise HTTPException(status_code=409, detail="Replay detected")

    _nonce_store[nonce] = now + NONCE_TTL_SECONDS
    logger.debug(
        "replay_nonce_accepted",
        nonce_prefix=nonce[:8] if len(nonce) >= 8 else nonce,
    )


# ---------------------------------------------------------------------------
# HMAC verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HMACVerification:
    """Result of a successful HMAC verification."""

    nonce: str
    timestamp: str


async def verify_hmac(
    request: Request,
    x_signature: str = Header(..., alias="X-Signature"),
    x_timestamp: str = Header(..., alias="X-Timestamp"),
    x_nonce: str = Header(..., alias="X-Nonce"),
) -> HMACVerification:
    """FastAPI dependency that validates replay protection + HMAC-SHA256.

    Execution order:
    1. Timestamp validation (free, no I/O)
    2. Nonce deduplication (Redis or in-memory fallback)
    3. HMAC signature verification (constant-time comparison)

    The signing string is: ``<method>:<path>:<timestamp>:<nonce>:<body-as-utf8>``
    """
    await validate_timestamp(x_timestamp)
    await check_nonce(x_nonce)

    body = await request.body()
    body_str = body.decode("utf-8")
    signing_string = (
        f"{request.method}:{request.url.path}:"
        f"{x_timestamp}:{x_nonce}:{body_str}"
    )

    secret = get_hmac_secret()
    expected = hmac.new(
        secret.encode("utf-8"),
        signing_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(x_signature, expected):
        raise HTTPException(status_code=401, detail="Invalid HMAC signature")

    logger.debug(
        "hmac_verified",
        device_id=request.headers.get("X-Device-ID", "unknown"),
        nonce_prefix=x_nonce[:8] if x_nonce else None,
    )

    return HMACVerification(nonce=x_nonce, timestamp=x_timestamp)


# ---------------------------------------------------------------------------
# SurveillanceReceiver — callable facade for the router
# ---------------------------------------------------------------------------


class SurveillanceReceiver:
    """Callable facade for HMAC-verified event ingest.

    Exposes both a FastAPI router (``router``) and a direct ``receive()``
    method for programmatic use (e.g. from a lifespan consumer).
    """

    def __init__(self, redis_client: Any = None) -> None:
        self._redis = redis_client
        self._router = self._build_router()

    @property
    def router(self) -> APIRouter:
        """Return the FastAPI router for mounting."""
        return self._router

    def _build_router(self) -> APIRouter:
        """Build the FastAPI router with the /surveillance/events endpoint."""
        r = APIRouter(prefix="/surveillance", tags=["surveillance"])

        @r.post("/events", response_model=SurveillanceEventResponse, status_code=202)
        async def ingest_event(
            body: SurveillanceEventRequest,
            request: Request,
            x_signature: str = Header(..., alias="X-Signature"),
            x_timestamp: str = Header(..., alias="X-Timestamp"),
            x_nonce: str = Header(..., alias="X-Nonce"),
        ) -> SurveillanceEventResponse:
            """Ingest a surveillance event with HMAC verification."""
            # Verify HMAC
            await validate_timestamp(x_timestamp)
            await check_nonce(x_nonce, redis_client=self._redis)

            raw_body = await request.body()
            body_str = raw_body.decode("utf-8")
            signing_string = (
                f"{request.method}:{request.url.path}:"
                f"{x_timestamp}:{x_nonce}:{body_str}"
            )
            secret = get_hmac_secret()
            expected = hmac.new(
                secret.encode("utf-8"),
                signing_string.encode("utf-8"),
                hashlib.sha256,
            ).hexdigest()
            if not hmac.compare_digest(x_signature, expected):
                raise HTTPException(status_code=401, detail="Invalid HMAC signature")

            # Classify
            classify_event(body.event_type)

            # Generate event ID
            event_id = str(uuid.uuid4())

            logger.info(
                "surveillance_event_ingested",
                event_type=body.event_type,
                device_id=body.device_id,
                event_id=event_id,
            )

            return SurveillanceEventResponse(
                status="accepted",
                event_id=event_id,
                received_at=datetime.now(),
            )

        return r

    async def receive(
        self,
        event_data: dict[str, Any],
        x_signature: str,
        x_timestamp: str,
        x_nonce: str,
        method: str = "POST",
        path: str = "/surveillance/events",
    ) -> dict[str, Any]:
        """Programmatic event ingest (no HTTP layer).

        Verifies HMAC and returns event metadata. Useful for internal
        pipeline consumers that already have raw event dicts.
        """
        await validate_timestamp(x_timestamp)
        await check_nonce(x_nonce, redis_client=self._redis)

        body_bytes = json.dumps(event_data, default=str).encode("utf-8")
        body_str = body_bytes.decode("utf-8")
        signing_string = f"{method}:{path}:{x_timestamp}:{x_nonce}:{body_str}"
        secret = get_hmac_secret()
        expected = hmac.new(
            secret.encode("utf-8"),
            signing_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(x_signature, expected):
            raise HTTPException(status_code=401, detail="Invalid HMAC signature")

        event_id = str(uuid.uuid4())
        logger.info(
            "surveillance_event_received",
            event_type=event_data.get("event_type", "unknown"),
            event_id=event_id,
        )
        return {"status": "accepted", "event_id": event_id}


# ---------------------------------------------------------------------------
# Exports
# ---------------------------------------------------------------------------

__all__ = [
    "DataClassification",
    "ClassificationResult",
    "EVENT_TYPE_CLASSIFICATION",
    "classify_event",
    "get_retention_days",
    "SurveillanceEventRequest",
    "SurveillanceEventResponse",
    "ErrorResponse",
    "ScanResult",
    "scan_text",
    "redact_secrets",
    "shannon_entropy",
    "PATTERNS",
    "get_hmac_secret",
    "_clear_cache",
    "validate_timestamp",
    "check_nonce",
    "TIMESTAMP_WINDOW_SECONDS",
    "NONCE_TTL_SECONDS",
    "HMACVerification",
    "verify_hmac",
    "SurveillanceReceiver",
]
