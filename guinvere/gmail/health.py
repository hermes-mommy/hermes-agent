from __future__ import annotations

"""P12 — Health check HTTP endpoint for the Gmail service.

Exposes a ``/health`` endpoint bound to ``127.0.0.1:8096`` (by default)
for systemd ``WatchdogSec=120`` and Prometheus external monitoring.

Usage::

    endpoint = GmailHealthEndpoint(service_ref)
    await endpoint.start()
    # ...
    await endpoint.stop()

Component status rules:

* all ``"ok"`` → overall ``"ok"``
* any ``"degraded"`` → overall ``"degraded"``
* any ``"error"`` → overall ``"unhealthy"``
"""

import asyncio
import time
from collections.abc import Awaitable, Callable
from typing import Protocol, runtime_checkable

import structlog
from aiohttp import web

from .metrics import set_connected

logger = structlog.get_logger(__name__)

_COMPONENT_CHECK_TIMEOUT: float = 5.0
"""Max seconds to wait per component check before marking it as timed out."""

_VERSION: str = "1.0.0"
"""Service version reported in every health response."""


class HealthCheckError(Exception):
    """Raised when a health component check times out or raises unexpectedly."""


@runtime_checkable
class _HealthCheckProvider(Protocol):
    """Protocol for objects that provide per-component health checks.

    Any object passed as ``service_ref`` to :class:`GmailHealthEndpoint`
    may optionally implement some or all of these methods.  Each method
    returns a human-readable detail string describing the component state.
    """

    async def check_oauth_health(self) -> str: ...
    async def check_gmail_api_health(self) -> str: ...
    async def check_pubsub_health(self) -> str: ...
    async def check_sync_health(self) -> str: ...
    async def check_watch_health(self) -> str: ...
    async def check_consent_health(self) -> str: ...
    async def check_hard_stop_health(self) -> str: ...


class GmailHealthEndpoint:
    """HTTP health check endpoint for the Gmail service.

    Parameters
    ----------
    service_ref :
        Reference to the main GmailService instance.  Each component check
        attempts to call a ``check_<name>_health`` coroutine on this object.
        If the method does not exist the component is reported as
        ``"degraded"`` with a descriptive message.
    host : str
        Bind address (default ``127.0.0.1`` — never ``0.0.0.0``).
    port : int
        Bind port (default ``8096``).
    """

    def __init__(
        self,
        service_ref: _HealthCheckProvider,
        host: str = "127.0.0.1",
        port: int = 8096,
    ) -> None:
        self._service_ref: _HealthCheckProvider = service_ref
        self._host: str = host
        self._port: int = port
        self._start_time: float = time.monotonic()
        self._app: web.Application | None = None
        self._runner: web.AppRunner | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Start the aiohttp HTTP server on the configured host:port.

        Only binds to ``127.0.0.1`` (never ``0.0.0.0``) to avoid exposing
        the health endpoint outside the host.
        """
        self._app = web.Application()
        _ = self._app.router.add_get("/health", self._handle_health)
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        site = web.TCPSite(self._runner, self._host, self._port)
        await site.start()
        logger.info(
            "gmail_health_server_started",
            bind=self._host,
            port=self._port,
        )

    async def stop(self) -> None:
        """Gracefully shut down the HTTP server."""
        if self._runner is not None:
            await self._runner.cleanup()
            self._runner = None
            self._app = None
            logger.info("gmail_health_server_stopped")

    # ------------------------------------------------------------------
    # Request handler
    # ------------------------------------------------------------------

    async def _handle_health(self, _request: web.Request) -> web.Response:
        """Return a JSON health response with per-component status.

        HTTP status codes:

        * ``200`` — overall status is ``"ok"`` or ``"degraded"``.
        * ``503`` — overall status is ``"unhealthy"`` (systemd-friendly).
        """
        components = await self._check_components()
        overall = self._compute_overall_status(components)

        # Surface the Prometheus connected gauge.
        set_connected(overall == "ok")

        uptime = time.monotonic() - self._start_time

        body: dict[str, object] = {
            "status": overall,
            "service": "guinevere-gmail",
            "version": _VERSION,
            "components": components,
            "uptime_seconds": round(uptime, 1),
        }

        status_code = 503 if overall == "unhealthy" else 200
        return web.json_response(body, status=status_code)

    # ------------------------------------------------------------------
    # Component checks
    # ------------------------------------------------------------------

    async def _check_components(self) -> dict[str, dict[str, str]]:
        """Check every registered component with an individual timeout.

        Each component is checked via a named method on the class so that
        ``asyncio.wait_for`` wraps only the async I/O portion and not the
        full method dispatch overhead.
        """
        checks: dict[str, Callable[[], Awaitable[dict[str, str]]]] = {
            "oauth": self._check_oauth,
            "gmail_api": self._check_gmail_api,
            "pubsub": self._check_pubsub,
            "sync": self._check_sync,
            "watch": self._check_watch,
            "consent": self._check_consent,
            "hard_stop": self._check_hard_stop,
            "metrics": self._check_metrics,
        }

        results: dict[str, dict[str, str]] = {}

        for name, check_fn in checks.items():
            try:
                result: dict[str, str] = await asyncio.wait_for(
                    check_fn(), timeout=_COMPONENT_CHECK_TIMEOUT
                )
                results[name] = result
            except asyncio.TimeoutError:
                logger.warning(
                    "gmail_health_component_timeout",
                    component=name,
                    timeout=_COMPONENT_CHECK_TIMEOUT,
                )
                results[name] = {
                    "status": "error",
                    "detail": f"check timed out after {_COMPONENT_CHECK_TIMEOUT}s",
                }
                set_connected(False)
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "gmail_health_component_failed",
                    component=name,
                    error=str(exc),
                )
                results[name] = {
                    "status": "error",
                    "detail": str(exc),
                }
                set_connected(False)

        return results

    @staticmethod
    def _compute_overall_status(
        components: dict[str, dict[str, str]],
    ) -> str:
        """Aggregate per-component status into a single overall status.

        Rules:
        * Any ``"error"`` → ``"unhealthy"``
        * Any ``"degraded"`` → ``"degraded"``
        * All ``"ok"`` → ``"ok"``
        """
        for result in components.values():
            status = result.get("status", "error")
            if status == "error":
                return "unhealthy"
        for result in components.values():
            status = result.get("status", "error")
            if status == "degraded":
                return "degraded"
        return "ok"

    # ------------------------------------------------------------------
    # Individual component check helpers
    # ------------------------------------------------------------------

    async def _check_oauth(self) -> dict[str, str]:
        """Check OAuth2 token validity via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_oauth_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "oauth check not wired"}

    async def _check_gmail_api(self) -> dict[str, str]:
        """Check Gmail API connectivity via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_gmail_api_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "gmail_api check not wired"}

    async def _check_pubsub(self) -> dict[str, str]:
        """Check Pub/Sub subscription status via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_pubsub_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "pubsub check not wired"}

    async def _check_sync(self) -> dict[str, str]:
        """Check sync-engine liveness via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_sync_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "sync check not wired"}

    async def _check_watch(self) -> dict[str, str]:
        """Check watch/push-notification registration via service_ref."""
        try:
            detail: str = await self._service_ref.check_watch_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "watch check not wired"}

    async def _check_consent(self) -> dict[str, str]:
        """Check email consent status via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_consent_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "consent check not wired"}

    async def _check_hard_stop(self) -> dict[str, str]:
        """Check whether a HARD STOP is active via service_ref delegation."""
        try:
            detail: str = await self._service_ref.check_hard_stop_health()
            return {"status": "ok", "detail": detail}
        except AttributeError:
            return {"status": "degraded", "detail": "hard_stop check not wired"}

    async def _check_metrics(self) -> dict[str, str]:
        """Report Prometheus metrics endpoint status."""
        try:
            from .config import get_gmail_settings

            settings = get_gmail_settings()
            metrics_port = settings.metrics_port
            return {
                "status": "ok",
                "detail": f"port {metrics_port}",
            }
        except Exception as exc:
            return {
                "status": "degraded",
                "detail": f"metrics check not wired: {exc!s}",
            }
