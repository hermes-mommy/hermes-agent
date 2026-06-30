"""
Cross-channel HARD STOP integration for the Gmail pipeline.

Checks the shared Redis HARD STOP flag before any email processing and can
trigger HARD STOP from the email channel when dangerous content is detected
(phishing with injection, consent revoked during processing, critical secrets
found in incoming email).

Fail-closed: if the underlying HardStopHandler raises, the checker defaults
to blocking email processing.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import structlog

from guinvere.core.services.hard_stop_handler import HardStopHandler, SafetyState
from guinvere.gmail.config import GmailSettings
from guinvere.gmail.exceptions import GmailError

logger = structlog.get_logger(__name__)

__all__ = [
    "EmailHardStopChecker",
    "HardStopError",
    "TRIGGER_SPAM_PHISHING",
    "TRIGGER_CONSENT_REVOKED",
    "TRIGGER_CRITICAL_SECRET",
]

# ---------------------------------------------------------------------------
# Constants — trigger reason strings used by engage_from_email()
# ---------------------------------------------------------------------------

TRIGGER_SPAM_PHISHING: str = "SPAM_PHISHING_WITH_INJECTION"
"""Phishing email with injection_detected=True and risk_score > 0.8."""

TRIGGER_CONSENT_REVOKED: str = "CONSENT_REVOKED_DURING_PROCESSING"
"""Consent was revoked while the email pipeline was actively processing."""

TRIGGER_CRITICAL_SECRET: str = "CRITICAL_SECRET_DETECTED"
"""SecretScanner found a critical secret (e.g. OpenAI key, Discord token)."""

# ---------------------------------------------------------------------------
# Protocol — expected HardStopHandler interface
# ---------------------------------------------------------------------------


@runtime_checkable
class _HardStopHandlerProtocol(Protocol):
    """Protocol describing the expected HardStopHandler interface.

    The injected handler must provide these async methods for cross-channel
    HARD STOP coordination.  The concrete :class:`HardStopHandler` will be
    updated to conform to this protocol in a separate implementation wave.
    """

    async def is_hard_stop_active(self) -> bool: ...

    async def engage_hard_stop(self, *, reason: str, source: str) -> bool: ...

    async def release_hard_stop(self) -> bool: ...


# ---------------------------------------------------------------------------
# Exception
# ---------------------------------------------------------------------------


class HardStopError(GmailError):
    """Raised when a HARD STOP operation fails or is rejected.

    This is distinct from handler-level errors; it signals that the Gmail
    module's interaction with the HARD STOP system encountered a failure
    (e.g., Redis unreachable during engage).
    """


# ---------------------------------------------------------------------------
# EmailHardStopChecker
# ---------------------------------------------------------------------------


class EmailHardStopChecker:
    """Cross-channel HARD STOP gate for the Gmail pipeline.

    Wraps the application-level :class:`HardStopHandler` with Gmail-specific
    semantics: failure to check defaults to *blocking* email processing
    (fail-closed), and engagement from the email channel logs the reason
    and source for audit traceability.

    The caller (Gmail router / pipeline) is responsible for evaluating
    trigger conditions (see the ``TRIGGER_*`` constants) — this class
    only provides the gate and the engagement interface.

    **Typical usage**::

        checker = EmailHardStopChecker(handler, settings)

        # At the start of each processing cycle:
        if await checker.check_before_processing():
            return  # skip all email work

        # On dangerous content detected:
        await checker.engage_from_email(TRIGGER_SPAM_PHISHING)
    """

    def __init__(
        self,
        hard_stop_handler: _HardStopHandlerProtocol,
        settings: GmailSettings,
        source: str = "gmail",
    ) -> None:
        """Initialize the EmailHardStopChecker.

        Args:
            hard_stop_handler: The application-level HardStopHandler
                managing the shared Redis HARD STOP flag. Must conform
                to :class:`_HardStopHandlerProtocol`.
            settings: Gmail module settings, expected to carry
                a ``HARD_STOP_ENABLED`` field.
            source: Channel source identifier passed to the handler
                on engage. Defaults to ``"gmail"``.
        """
        self._handler: _HardStopHandlerProtocol = hard_stop_handler
        self._settings: GmailSettings = settings
        self._source: str = source

        # Use getattr for backward compat if the config field hasn't
        # been added to GmailSettings yet.
        self._enabled: bool = getattr(settings, "HARD_STOP_ENABLED", True)

        logger.info(
            "gmail.hard_stop.initialized",
            source=self._source,
            enabled=self._enabled,
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def check_before_processing(self) -> bool:
        """Check whether HARD STOP is active before email processing.

        The router/pipeline should call this as the very first step
        in the email processing loop and skip all work when ``True``.

        Returns:
            ``True`` if email processing should be **blocked** (HARD STOP
            is active or the check failed — fail-closed). ``False`` if
            processing may proceed.
        """
        if not self._enabled:
            return False

        try:
            active: bool = await self._handler.is_hard_stop_active()
        except Exception:
            logger.exception(
                "gmail.hard_stop.check_failed_fail_closed",
                source=self._source,
            )
            return True  # fail-closed → block

        if active:
            logger.warning(
                "gmail.hard_stop.blocked_processing",
                source=self._source,
            )
        else:
            logger.info(
                "gmail.hard_stop.processing_allowed",
                source=self._source,
            )

        return active

    async def engage_from_email(self, reason: str) -> bool:
        """Trigger HARD STOP from the email channel.

        Args:
            reason: One of the ``TRIGGER_*`` constants (or an arbitrary
                reason string for extensibility). Logged for audit.

        Returns:
            ``True`` if the HARD STOP was engaged (or was already
            active). ``False`` if engagement was refused.

        Raises:
            HardStopError: If the underlying handler raises (indicating
                a system-level failure rather than a policy rejection).
        """
        logger.warning(
            "gmail.hard_stop.engaging_from_email",
            reason=reason,
            source=self._source,
        )

        try:
            result: bool = await self._handler.engage_hard_stop(
                reason=reason,
                source=self._source,
            )
        except Exception as exc:
            logger.exception(
                "gmail.hard_stop.engage_failed",
                reason=reason,
                source=self._source,
            )
            raise HardStopError(
                f"Failed to engage HARD STOP from email channel: {reason}"
            ) from exc

        if result:
            logger.warning(
                "gmail.hard_stop.engaged",
                reason=reason,
                source=self._source,
            )
        else:
            logger.warning(
                "gmail.hard_stop.engage_refused",
                reason=reason,
                source=self._source,
                detail="Handler returned False (already active or refused)",
            )

        return result

    async def release(self) -> bool:
        """Release HARD STOP and return to normal operation.

        Delegates directly to ``HardStopHandler.release_hard_stop()``.

        Returns:
            ``True`` if the release was successful. ``False`` if
            HARD STOP was not active or the handler declined.

        Raises:
            HardStopError: If the underlying handler raises.
        """
        logger.info(
            "gmail.hard_stop.releasing",
            source=self._source,
        )

        try:
            result: bool = await self._handler.release_hard_stop()
        except Exception as exc:
            logger.exception(
                "gmail.hard_stop.release_failed",
                source=self._source,
            )
            raise HardStopError(
                "Failed to release HARD STOP from email channel"
            ) from exc

        if result:
            logger.info(
                "gmail.hard_stop.released",
                source=self._source,
            )
        else:
            logger.warning(
                "gmail.hard_stop.release_noop",
                source=self._source,
                detail="HARD STOP was not active or could not be released",
            )

        return result

    async def is_blocked(self) -> bool:
        """Convenience wrapper around the handler's HARD STOP flag.

        Returns ``True`` if email processing should be blocked.
        Fail-closed: returns ``True`` if the underlying check raises.
        """
        if not self._enabled:
            return False

        try:
            return await self._handler.is_hard_stop_active()
        except Exception:
            logger.exception(
                "gmail.hard_stop.is_blocked_failed_fail_closed",
                source=self._source,
            )
            return True  # fail-closed → block
