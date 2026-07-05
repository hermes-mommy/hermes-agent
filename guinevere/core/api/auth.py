"""API key authentication for the Guinevere internal API."""

from __future__ import annotations

import hmac
import os

import structlog
from fastapi import Header, HTTPException

logger = structlog.get_logger()

API_KEY_HEADER: str = "X-Guinevere-API-Key"

def verify_api_key(key: str) -> bool:
    """Validate *key* against the configured API key.

    Reads ``GUINEVERE_API_KEY`` from the environment.  Raises
    :class:`RuntimeError` when the variable is not set.

    Returns ``True`` when the key matches, ``False`` otherwise.
    """
    expected = os.environ.get("GUINEVERE_API_KEY")
    if not expected:
        raise RuntimeError(
            "GUINEVERE_API_KEY environment variable is required"
        )
    return hmac.compare_digest(key, expected)


async def get_api_key(
    x_guinevere_api_key: str | None = Header(None, alias=API_KEY_HEADER),
) -> str:
    """FastAPI dependency that extracts and verifies the API key header.

    Raises :class:`HTTPException` (401) when the key is absent or invalid.
    Returns the validated key on success so downstream code can use it.
    """
    if x_guinevere_api_key is None:
        logger.warning("api_key_missing", header=API_KEY_HEADER)
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    if not verify_api_key(x_guinevere_api_key):
        logger.warning("api_key_invalid", header=API_KEY_HEADER)
        raise HTTPException(
            status_code=401,
            detail="Invalid or missing API key",
        )

    logger.debug("api_key_verified")
    return x_guinevere_api_key
