"""FastAPI router for the surveillance event ingestion webhook.

P7-001: POST /surveillance/events — strict Pydantic v2 validation.
Authentication (P7-002), Redis buffering (P7-005), and classification
(P7-008) are layered on top in later steps.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

import structlog
from fastapi import APIRouter, Depends

from src.surveillance.auth import HMACVerification, verify_hmac
from src.surveillance.models import SurveillanceEventRequest, SurveillanceEventResponse

logger = structlog.get_logger()

surveillance_router = APIRouter(prefix="/surveillance", tags=["surveillance"])


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
    ``X-Timestamp``, and ``X-Nonce`` headers.
    Buffering (P7-005) and classification (P7-008) are handled by
    subsequent P7 steps.
    """
    event_id = str(uuid4())

    logger.info(
        "surveillance_event_received",
        event_type=event.event_type,
        device_id=event.device_id,
        event_id=event_id,
        nonce_prefix=auth.nonce[:8] if auth.nonce else None,
    )

    return SurveillanceEventResponse(
        status="accepted",
        event_id=event_id,
        received_at=datetime.now(tz=timezone.utc),
    )