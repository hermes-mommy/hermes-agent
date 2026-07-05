"""Send approved drafts via Gmail API with pre-send safety validation."""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Final

import structlog

from guinevere.gmail.client import AsyncGmailClient
from guinevere.gmail.config import get_gmail_settings, GmailSettings
from guinevere.gmail.envelope import GmailDeliveryEnvelope
from guinevere.gmail.exceptions import (
    DraftSendError,
    PersonaLeakError,
    PIIDetectedError,
    SecretDetectedError,
)
from guinevere.gmail.metrics import record_draft_approved
from guinevere.gmail.sanitization import ContentSanitizer, SanitizationResult
from guinevere.gmail.secret_scanner import CombinedScanner

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_PERSONA_LEAK_PATTERNS: Final[dict[str, re.Pattern[str]]] = {
    "system_prompt": re.compile(r"(?i)system\s+prompt"),
    "guinevere": re.compile(r"(?i)guinevere"),
    "hermes": re.compile(r"(?i)hermes"),
    "surveillance": re.compile(r"(?i)surveillance"),
    "as_an_ai": re.compile(r"(?i)as\s+an\s+AI"),
    "im_just_an_ai": re.compile(r"(?i)I'm\s+just\s+an\s+AI"),
}

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SendResult:
    """Result metadata for a successfully sent draft."""

    sent_message_id: str
    draft_id: str
    thread_id: str
    target_email: str
    sent_at: datetime


# ---------------------------------------------------------------------------
# Pipeline
# ---------------------------------------------------------------------------


class DraftSendPipeline:
    """Pre-send validation pipeline for approved Gmail drafts.

    1. ContentSanitizer injection detection
    2. CombinedScanner secret + PII scan
    3. Length constraints
    4. Persona leak detection

    If all checks pass, builds a ``GmailDeliveryEnvelope``, converts to
    raw MIME, and sends via ``AsyncGmailClient.send_message()``.
    """

    def __init__(
        self,
        gmail_client: AsyncGmailClient,
        sanitizer: ContentSanitizer,
        scanner: CombinedScanner,
        settings: GmailSettings | None = None,
    ) -> None:
        """Initialize the send pipeline."""
        self._client: AsyncGmailClient = gmail_client
        self._sanitizer: ContentSanitizer = sanitizer
        self._scanner: CombinedScanner = scanner
        self._settings: GmailSettings = settings or get_gmail_settings()

    async def send(
        self,
        draft_id: str,
        target_email: str,
        subject: str,
        body_html: str,
        thread_id: str | None = None,
        in_reply_to: str | None = None,
    ) -> SendResult:
        """Validate and send the approved draft.

        Runs pre-send validation, builds a ``GmailDeliveryEnvelope``,
        converts to raw MIME, and dispatches via the Gmail API.

        Args:
            draft_id: The Gmail draft ID to send.
            target_email: Recipient email address.
            subject: Email subject line.
            body_html: HTML body content to send.
            thread_id: Optional thread ID for threading.
            in_reply_to: Optional message ID this is a reply to.

        Returns:
            SendResult with sent message metadata.

        Raises:
            SecretDetectedError: Secrets found in body.
            PIIDetectedError: PII found in body.
            DraftSendError: Length validation or API call failure.
            PersonaLeakError: Persona-internal patterns detected.
        """
        logger.info(
            "draft_send_started",
            draft_id=draft_id,
            target_email=target_email,
            thread_id=thread_id,
            body_length=len(body_html),
        )

        # Pre-send validation
        await self._presend_validate(draft_id, body_html)

        # Build delivery envelope
        envelope = GmailDeliveryEnvelope(
            target_email=target_email,
            subject=subject,
            body_html=body_html,
            thread_id=thread_id,
            in_reply_to=in_reply_to,
            draft_id=draft_id,
        )

        # Convert envelope to raw MIME message for the Gmail API
        raw_message = self._build_raw_message(envelope)

        # Send via API
        try:
            response = await self._client.send_message(
                raw_message,
            )
        except DraftSendError:
            # Re-raise typed exceptions from validation as-is
            raise
        except Exception as exc:
            logger.error(
                "draft_send_api_failed",
                draft_id=draft_id,
                target_email=target_email,
                thread_id=thread_id,
                error=str(exc),
            )
            raise DraftSendError(
                draft_id=draft_id,
                reason=f"Gmail API send failed: {exc}",
            ) from exc

        sent_message_id: str = response.get("id", "")
        sent_thread_id: str = response.get(
            "threadId", thread_id or "",
        )
        sent_at = datetime.now(timezone.utc)

        record_draft_approved()

        logger.info(
            "draft_send_success",
            draft_id=draft_id,
            sent_message_id=sent_message_id,
            thread_id=sent_thread_id,
            target_email=target_email,
        )

        return SendResult(
            sent_message_id=sent_message_id,
            draft_id=draft_id,
            thread_id=sent_thread_id,
            target_email=target_email,
            sent_at=sent_at,
        )

    async def _presend_validate(
        self, draft_id: str, body_html: str,
    ) -> None:
        """Run pre-send safety validation (injection, secrets, PII, length, persona)."""
        # Step 1: ContentSanitizer injection check
        sanitized: SanitizationResult = self._sanitizer.sanitize(
            text="", html=body_html,
        )
        if sanitized.injection_detected or not sanitized.is_safe:
            logger.warning(
                "draft_validation_injection_detected",
                draft_id=draft_id,
                risk_score=sanitized.risk_score,
                body_length=len(body_html),
            )
            raise DraftSendError(
                draft_id=draft_id,
                reason=(
                    f"Injection detected (risk_score="
                    f"{sanitized.risk_score})"
                ),
            )

        # Step 2: CombinedScanner secret + PII scan
        secret_result, pii_result = self._scanner.scan_email(body_html)

        if secret_result.has_secrets:
            logger.warning(
                "draft_validation_secrets_detected",
                draft_id=draft_id,
                secret_types=secret_result.secret_types,
                body_length=len(body_html),
            )
            raise SecretDetectedError(secret_result.secret_types)

        if pii_result.has_pii:
            logger.warning(
                "draft_validation_pii_detected",
                draft_id=draft_id,
                pii_types=pii_result.pii_types,
                body_length=len(body_html),
            )
            raise PIIDetectedError(pii_result.pii_types)

        # Step 3: Length validation
        body_len = len(body_html)
        if body_len < self._settings.draft_min_length:
            raise DraftSendError(
                draft_id=draft_id,
                reason=(
                    f"Body too short: {body_len} < "
                    f"{self._settings.draft_min_length}"
                ),
            )
        if body_len > self._settings.draft_max_length:
            raise DraftSendError(
                draft_id=draft_id,
                reason=(
                    f"Body too long: {body_len} > "
                    f"{self._settings.draft_max_length}"
                ),
            )

        # Step 4: Persona leak check
        leaked = self._check_persona_leak(body_html)
        if leaked:
            logger.warning(
                "draft_validation_persona_leak",
                draft_id=draft_id,
                leaked_patterns=leaked,
                body_length=len(body_html),
            )
            raise PersonaLeakError(leaked)

        logger.debug(
            "draft_validation_passed",
            draft_id=draft_id,
            body_length=body_len,
        )

    def _check_persona_leak(self, body_html: str) -> list[str]:
        """Scan *body_html* for persona-internal patterns that must not leak."""
        matched: list[str] = []
        for name, pattern in _PERSONA_LEAK_PATTERNS.items():
            if pattern.search(body_html):
                matched.append(name)
        return matched

    # ------------------------------------------------------------------
    # MIME construction
    # ------------------------------------------------------------------

    @staticmethod
    def _build_raw_message(
        envelope: GmailDeliveryEnvelope,
    ) -> dict[str, str]:
        """Build a base64url-encoded raw MIME dict from *envelope*."""
        msg = MIMEMultipart("alternative")
        msg["To"] = envelope.target_email
        msg["Subject"] = envelope.subject

        if envelope.in_reply_to:
            msg["In-Reply-To"] = envelope.in_reply_to

        if envelope.thread_id:
            # Include thread header for Gmail threading
            msg["References"] = envelope.thread_id

        # Attach HTML body
        html_part = MIMEText(envelope.body_html, "html", "utf-8")
        msg.attach(html_part)

        raw_bytes = msg.as_bytes()
        encoded = base64.urlsafe_b64encode(raw_bytes).decode("ascii")

        return {"raw": encoded}


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "DraftSendPipeline",
    "SendResult",
]
