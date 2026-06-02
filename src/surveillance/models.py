"""Pydantic v2 request/response models for the surveillance webhook endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class SurveillanceEventRequest(BaseModel):
    """Validated payload accepted at POST /surveillance/events.

    Every field uses strict validation.  ``extra="forbid"`` ensures that
    unknown top-level keys result in a 422 response.

    The ``occurred_at`` field accepts ISO-8601 datetime strings (as sent
    by JSON clients) and converts them to timezone-aware ``datetime``
    objects before Pydantic's strict-mode core validation runs.
    """

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