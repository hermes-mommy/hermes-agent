from __future__ import annotations

"""P12 Resend transactional email client with rate limiting and templates."""

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, ClassVar

import structlog
from jinja2 import Environment, FileSystemLoader, select_autoescape
from prometheus_client import Counter, Gauge, Histogram

from .config import GmailSettings

logger = structlog.get_logger(__name__)

# Template directory relative to this file
TEMPLATE_DIR = Path(__file__).parent / "templates"

# ---------------------------------------------------------------------------
# Prometheus metrics
# ---------------------------------------------------------------------------
RESEND_EMAILS_SENT_TOTAL = Counter(
    "resend_emails_sent_total",
    "Total transactional emails sent via Resend",
    ["status"],
)

RESEND_RATE_LIMITED_TOTAL = Counter(
    "resend_rate_limited_total",
    "Total emails rejected by rate limiter",
)

RESEND_TEMPLATE_RENDER_SECONDS = Histogram(
    "resend_template_render_seconds",
    "Jinja2 template rendering latency",
    buckets=(0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, float("inf")),
)

RESEND_SEND_LATENCY_SECONDS = Histogram(
    "resend_send_latency_seconds",
    "Resend API send latency",
    buckets=(0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 30.0, float("inf")),
)

RESEND_QUOTA_REMAINING = Gauge(
    "resend_quota_remaining",
    "Approximate remaining daily email quota",
)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class EmailResult:
    """Result of sending a transactional email."""

    success: bool
    message_id: str | None = None
    error: str | None = None


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------
class TokenBucketRateLimiter:
    """Token bucket rate limiter for daily email quota.

    Refills at rate of (daily_limit / 86400) tokens per second.
    """

    def __init__(self, daily_limit: int = 100) -> None:
        self._daily_limit: int = daily_limit
        self._tokens: float = float(daily_limit)
        self._last_refill: float = time.monotonic()
        self._refill_rate: float = daily_limit / 86400.0  # tokens/sec

    def consume(self, tokens: int = 1) -> bool:
        """Try to consume tokens. Returns True if allowed."""
        self._refill()
        if self._tokens >= tokens:
            self._tokens -= tokens
            return True
        return False

    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(
            self._daily_limit,
            self._tokens + elapsed * self._refill_rate,
        )
        self._last_refill = now

    @property
    def remaining(self) -> int:
        """Approximate remaining tokens."""
        self._refill()
        return int(self._tokens)


# ---------------------------------------------------------------------------
# Resend client
# ---------------------------------------------------------------------------
class ResendClient:
    """Transactional email client via Resend API.

    Features:
    - Token bucket rate limiting (100/day default)
    - Jinja2 HTML template rendering
    - Structured logging for all sends
    - Prometheus metrics integration
    """

    TEMPLATES: ClassVar[list[str]] = [
        "invoice",
        "notification",
        "digest",
        "alert",
    ]

    def __init__(self, settings: GmailSettings) -> None:
        self._settings = settings
        self._rate_limiter = TokenBucketRateLimiter(
            daily_limit=settings.resend_daily_limit,
        )
        self._jinja_env: Environment | None = None
        self._initialized: bool = False

    async def initialize(self) -> None:
        """Initialize Resend SDK and Jinja2 template environment."""
        import resend

        resend.api_key = self._settings.resend_api_key

        if TEMPLATE_DIR.exists():
            self._jinja_env = Environment(
                loader=FileSystemLoader(str(TEMPLATE_DIR)),
                autoescape=select_autoescape(["html", "xml"]),
                trim_blocks=True,
                lstrip_blocks=True,
            )

        self._initialized = True
        RESEND_QUOTA_REMAINING.set(self._rate_limiter.remaining)
        logger.info(
            "resend_client.initialized",
            daily_limit=self._settings.resend_daily_limit,
        )

    async def send_email(
        self,
        to: str | list[str],
        subject: str,
        html: str,
        reply_to: str | None = None,
        cc: list[str] | None = None,
        tags: list[dict[str, str]] | None = None,
    ) -> EmailResult:
        """Send a transactional email via Resend.

        Args:
            to: Recipient email(s)
            subject: Email subject
            html: HTML body content
            reply_to: Optional reply-to address
            cc: Optional CC recipients
            tags: Optional Resend tags for tracking

        Returns:
            EmailResult with success status and message_id or error
        """
        if not self._initialized:
            return EmailResult(
                success=False,
                error="ResendClient not initialized",
            )

        if not self._rate_limiter.consume():
            RESEND_RATE_LIMITED_TOTAL.inc()
            RESEND_QUOTA_REMAINING.set(self._rate_limiter.remaining)
            logger.warning(
                "resend_client.rate_limited",
                remaining=self._rate_limiter.remaining,
            )
            return EmailResult(
                success=False,
                error="Daily rate limit exceeded",
            )

        import resend

        params: dict[str, Any] = {
            "from_": self._settings.resend_from_email,
            "to": [to] if isinstance(to, str) else to,
            "subject": subject,
            "html": html,
        }
        if reply_to:
            params["reply_to"] = reply_to
        if cc:
            params["cc"] = cc
        if tags:
            params["tags"] = tags

        try:
            loop = asyncio.get_running_loop()
            start = loop.time()
            result: Any = await asyncio.to_thread(
                resend.Emails.send,
                params,
            )
            elapsed = loop.time() - start
            RESEND_SEND_LATENCY_SECONDS.observe(elapsed)

            message_id: str = ""
            if isinstance(result, dict):
                message_id = result.get("id", "")
            else:
                message_id = getattr(result, "id", "")

            RESEND_EMAILS_SENT_TOTAL.labels(status="success").inc()
            RESEND_QUOTA_REMAINING.set(self._rate_limiter.remaining)
            logger.info(
                "resend_client.sent",
                to=to,
                subject=subject[:50],
                message_id=message_id,
            )
            return EmailResult(success=True, message_id=message_id)

        except resend.exceptions.ResendError as exc:
            RESEND_EMAILS_SENT_TOTAL.labels(status="error").inc()
            logger.error(
                "resend_client.send_failed",
                error=str(exc),
                to=to,
            )
            return EmailResult(success=False, error=str(exc))

    async def send_template(
        self,
        template_name: str,
        to: str | list[str],
        subject: str,
        context: dict[str, Any],
        **kwargs: Any,
    ) -> EmailResult:
        """Render a Jinja2 template and send via Resend.

        Args:
            template_name: Template name (without .html extension)
            to: Recipient email(s)
            subject: Email subject
            context: Template context variables
            **kwargs: Additional args passed to send_email
        """
        if self._jinja_env is None:
            return EmailResult(
                success=False,
                error="Template environment not available",
            )

        try:
            template = self._jinja_env.get_template(
                f"{template_name}.html",
            )
            start = time.monotonic()
            html = template.render(**context)
            elapsed = time.monotonic() - start
            RESEND_TEMPLATE_RENDER_SECONDS.observe(elapsed)
        except Exception as exc:
            logger.error(
                "resend_client.template_render_failed",
                template=template_name,
                error=str(exc),
            )
            return EmailResult(
                success=False,
                error=f"Template render failed: {exc}",
            )

        return await self.send_email(
            to=to,
            subject=subject,
            html=html,
            **kwargs,
        )

    @property
    def remaining_quota(self) -> int:
        """Remaining daily email quota."""
        return self._rate_limiter.remaining
