"""FastAPI router for the surveillance event ingestion webhook.

P7-001: POST /surveillance/events - strict Pydantic v2 validation.
Authentication (P7-002) and Redis buffering (P7-005) are integrated.
Classification (P7-008) is layered on top in a later step.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends

from guinevere.surveillance.auth import HMACVerification, verify_hmac
from guinevere.surveillance.models import SurveillanceEventRequest, SurveillanceEventResponse
from guinevere.surveillance.redis_buffer import create_buffer

logger = structlog.get_logger()

surveillance_router = APIRouter(prefix="/surveillance", tags=["surveillance"])

# Module-level buffer instance. create_buffer() returns a Redis client
# wrapper that connects lazily, so this is safe at import time.
_buffer = create_buffer()


@surveillance_router.post(
    "/events",
    response_model=SurveillanceEventResponse,
    status_code=202,
)
async def receive_event(
    event: SurveillanceEventRequest,
    auth: HMACVerification = Depends(verify_hmac),
) -> SurveillanceEventResponse:
    """Accept a validated surveillance event and return an ingestion receipt.

    HMAC-SHA256 authentication is enforced via ``X-Signature``,
    ``X-Timestamp``, and ``X-Nonce`` headers. After validation, the
    event is pushed to the Redis DB2 buffer (P7-005) on a best-effort
    basis. Buffer failures are logged but never block the 202 response.
    Classification (P7-008) is handled by a subsequent P7 step.
    """
    event_id = str(uuid4())

    logger.info(
        "surveillance_event_received",
        event_type=event.event_type,
        device_id=event.device_id,
        event_id=event_id,
        nonce_prefix=auth.nonce[:8] if auth.nonce else None,
    )

    # Best-effort push to Redis DB2 buffer (P7-005).
    # Never blocks the 202 response - failures are logged only.
    try:
        await _buffer.push_event(event.model_dump(mode="json"))
    except Exception:
        logger.exception(
            "surveillance_buffer_push_error",
            event_id=event_id,
            event_type=event.event_type,
        )

    return SurveillanceEventResponse(
        status="accepted",
        event_id=event_id,
        received_at=datetime.now(tz=timezone.utc),
    )