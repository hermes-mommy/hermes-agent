from __future__ import annotations

import os

import httpx

try:
    import structlog
except Exception:  # pragma: no cover - fallback when structlog is unavailable in tests
    import logging

    class _StructLogFallback:
        def __init__(self) -> None:
            self._logger = logging.getLogger(__name__)

        def warning(self, event: str, **kwargs: object) -> None:
            self._logger.warning("%s %s", event, kwargs)

        def info(self, event: str, **kwargs: object) -> None:
            self._logger.info("%s %s", event, kwargs)

        def exception(self, event: str, **kwargs: object) -> None:
            self._logger.exception("%s %s", event, kwargs)

    class _StructLogModule:
        @staticmethod
        def get_logger(name: str) -> _StructLogFallback:
            return _StructLogFallback()

    structlog = _StructLogModule()

GOTIFY_URL: str = "http://localhost:8081"
logger = structlog.get_logger(__name__)


def build_gotify_payload(title: str, description: str, priority: int) -> dict[str, object]:
    """Build the JSON payload for Gotify POST /message."""
    return {"title": title, "message": description, "priority": priority}


def get_priority(severity: str) -> int:
    """Map severity string to Gotify priority (0-10)."""
    mapping = {"SEV0": 10, "SEV1": 7, "SEV2": 5, "SEV3": 3, "SEV4": 1}
    return mapping.get(severity.upper().strip(), 0)


async def send_fallback(title: str, description: str, severity: str) -> bool:
    """Send a notification via Gotify. Returns False on any failure (fail-soft)."""
    token = os.environ.get("GOTIFY_APP_TOKEN", "")
    if not token:
        logger.warning("gotify_fallback_disabled", reason="no_token")
        return False

    priority = get_priority(severity)
    payload = build_gotify_payload(title, description, priority)

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{GOTIFY_URL}/message",
                json=payload,
                headers={"X-Gotify-Key": token},
                timeout=5.0,
            )
        if response.is_success:
            logger.info("gotify_fallback_sent", severity=severity, status=response.status_code)
            return True
        logger.warning(
            "gotify_fallback_failed",
            severity=severity,
            status=response.status_code,
            body=response.text[:200],
        )
        return False
    except httpx.TimeoutException:
        logger.warning("gotify_fallback_timeout", severity=severity)
        return False
    except httpx.ConnectError:
        logger.warning("gotify_fallback_unreachable", severity=severity)
        return False
    except Exception:
        logger.exception("gotify_fallback_error", severity=severity)
        return False
