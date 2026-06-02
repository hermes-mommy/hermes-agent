"""HMAC-SHA256 authentication for the surveillance webhook endpoint.

P7-002: ``verify_hmac`` is a FastAPI dependency that reads the ``X-Signature``,
``X-Timestamp``, and ``X-Nonce`` headers, reconstructs the signing string, and
compares the HMAC against the secret obtained from ``get_hmac_secret()``.

P7-003: Replay protection is layered in before HMAC verification:
1. Timestamp window validation (free, no I/O)
2. Atomic nonce deduplication via Redis SET NX EX (fail-closed)
3. HMAC signature verification (existing logic)
"""

from __future__ import annotations

import hashlib
import hmac
from dataclasses import dataclass

import structlog
from fastapi import Header, HTTPException, Request

from src.surveillance.replay import check_nonce, validate_timestamp
from src.surveillance.secrets import get_hmac_secret

logger = structlog.get_logger()


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

    Execution order (by design):
    1. **Timestamp validation** — free, no I/O.  Reject expired requests
       before they consume Redis capacity.
    2. **Nonce deduplication** — atomic Redis ``SET NX EX``.  Reject
       replays with HTTP 409.
    3. **HMAC verification** — constant-time comparison via
       :func:`hmac.compare_digest`.

    The signing string is built from:
    ``<method>:<path>:<timestamp>:<nonce>:<body-as-utf8>``

    Raises:
        HTTPException(401): Timestamp is expired or HMAC signature is invalid.
        HTTPException(409): Nonce has already been seen (replay detected).
        HTTPException(422): A required header is missing (handled by FastAPI).
        HTTPException(503): Redis is unreachable (fail-closed).
    """
    # ---- 1. Timestamp validation (free, no I/O) ---------------------------
    await validate_timestamp(x_timestamp)

    # ---- 2. Nonce deduplication (Redis, fail-closed) ----------------------
    await check_nonce(x_nonce)

    # ---- 3. HMAC verification ---------------------------------------------
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