"""Discord email consent management commands.

Three text-prefix commands:
  - ``!email-consent-grant`` — grant email processing consent (Faiz-only)
  - ``!email-consent-revoke`` — revoke email processing consent (Faiz-only)
  - ``!email-reauth`` — force OAuth token refresh (Faiz-only)

All commands gate on Faiz-only access and delegate consent logic to
:class:`EmailConsentManager`.  Token refresh is delegated to
:class:`TokenManager`.

Design decisions:
- **Delegation, not duplication**: every handler delegates the actual
  consent/token operation to the injected manager.
- **Pre-check before mutating**: ``handle_consent_grant`` and
  ``handle_consent_revoke`` query the current consent status before
  calling the mutating method, so duplicate or no-op calls return an
  informational response instead of a misleading success.
- **Fail-graceful**: any exception from the manager or token layer is
  caught and returned as a user-friendly string.  The exception is
  logged via ``structlog`` for observability.
- **Actor extraction**: both message objects (``discord.Message``) and
  interaction objects (``discord.Interaction``) are supported via
  duck-typed attribute access in ``_resolve_user_id()`` and
  ``_resolve_actor_name()``.
"""

from __future__ import annotations

import os
from typing import Any

import structlog

from guinvere.gmail.consent_manager import EmailConsentManager
from guinvere.gmail.exceptions import GmailError
from guinvere.gmail.token_manager import TokenManager

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Discord user ID for Faiz (the sole operator).
# Set via GMAIL_FAIZ_USER_ID env var.  Must be non-zero for commands to work.
_FAIZ_USER_ID: int = int(os.environ.get("GMAIL_FAIZ_USER_ID", "0"))


# ---------------------------------------------------------------------------
# EmailConsentCommands
# ---------------------------------------------------------------------------


class EmailConsentCommands:
    """Discord command handlers for email consent management.

    Each handler accepts a ``message_or_interaction`` duck-typed Discord
    payload and returns a response string suitable for a Discord text
    channel (under 2000 characters).

    Args:
        consent_manager: An ``EmailConsentManager`` instance.
        token_manager: A ``TokenManager`` instance.
    """

    def __init__(
        self,
        consent_manager: EmailConsentManager,
        token_manager: TokenManager,
    ) -> None:
        self._consent: EmailConsentManager = consent_manager
        self._token: TokenManager = token_manager

    # ------------------------------------------------------------------
    # Public command handlers
    # ------------------------------------------------------------------

    async def handle_consent_grant(self, message_or_interaction: Any) -> str:
        """Handle ``!email-consent-grant`` — grant email processing consent.

        Checks current consent status first.  If consent is already active
        an informational message is returned without calling the mutating
        method.  Otherwise delegates to ``EmailConsentManager.grant_consent()``.

        Args:
            message_or_interaction: A ``discord.Message`` or
                ``discord.Interaction`` payload.

        Returns:
            A user-facing response string (under 2000 characters).
        """
        user_id = self._resolve_user_id(message_or_interaction)
        if not self._check_faiz(user_id):
            return "Only Faiz can use this command."

        actor = self._resolve_actor_name(message_or_interaction)

        try:
            # Check current status — avoid duplicate grant.
            current = await self._consent.check_email_consent()
            if current.allowed:
                logger.info(
                    "email_consent_already_granted",
                    actor=actor,
                    user_id=user_id,
                )
                return (
                    "ℹ️ Email consent was already granted."
                )

            success = await self._consent.grant_consent(actor)
            if success:
                logger.info(
                    "email_consent_granted",
                    actor=actor,
                    user_id=user_id,
                )
                return (
                    "✅ Email consent granted. "
                    "Gmail monitoring will now process incoming emails."
                )

            logger.warning(
                "email_consent_grant_failed",
                actor=actor,
                user_id=user_id,
            )
            return (
                "❌ Failed to grant email consent. "
                "The surveillance consent ledger may not confirm the grant."
            )

        except GmailError as exc:
            logger.warning(
                "email_consent_grant_error",
                actor=actor,
                user_id=user_id,
                error=str(exc),
            )
            return f"❌ Consent grant failed: {exc}"
        except Exception:
            logger.exception(
                "email_consent_grant_crash",
                actor=actor,
                user_id=user_id,
            )
            return "❌ An unexpected error occurred while granting email consent."

    async def handle_consent_revoke(self, message_or_interaction: Any) -> str:
        """Handle ``!email-consent-revoke`` — revoke email processing consent.

        Checks current consent status first.  If consent is already inactive
        an informational message is returned.  Otherwise delegates to
        ``EmailConsentManager.revoke_consent()``.

        Args:
            message_or_interaction: A ``discord.Message`` or
                ``discord.Interaction`` payload.

        Returns:
            A user-facing response string (under 2000 characters).
        """
        user_id = self._resolve_user_id(message_or_interaction)
        if not self._check_faiz(user_id):
            return "Only Faiz can use this command."

        actor = self._resolve_actor_name(message_or_interaction)

        try:
            # Check current status — avoid no-op revoke.
            current = await self._consent.check_email_consent()
            if not current.allowed:
                logger.info(
                    "email_consent_already_revoked",
                    actor=actor,
                    user_id=user_id,
                )
                return "ℹ️ Email consent was not currently granted."

            success = await self._consent.revoke_consent(actor)
            if success:
                logger.info(
                    "email_consent_revoked",
                    actor=actor,
                    user_id=user_id,
                )
                return (
                    "🛑 Email consent revoked. "
                    "Gmail monitoring will stop processing new emails."
                )

            logger.warning(
                "email_consent_revoke_failed",
                actor=actor,
                user_id=user_id,
            )
            return "❌ Failed to revoke email consent. Check logs for details."

        except GmailError as exc:
            logger.warning(
                "email_consent_revoke_error",
                actor=actor,
                user_id=user_id,
                error=str(exc),
            )
            return f"❌ Consent revoke failed: {exc}"
        except Exception:
            logger.exception(
                "email_consent_revoke_crash",
                actor=actor,
                user_id=user_id,
            )
            return "❌ An unexpected error occurred while revoking email consent."

    async def handle_reauth(self, message_or_interaction: Any) -> str:
        """Handle ``!email-reauth`` — force OAuth token refresh.

        Delegates to ``TokenManager.force_refresh()`` and reports the
        resulting token age.

        Args:
            message_or_interaction: A ``discord.Message`` or
                ``discord.Interaction`` payload.

        Returns:
            A user-facing response string (under 2000 characters).
        """
        user_id = self._resolve_user_id(message_or_interaction)
        if not self._check_faiz(user_id):
            return "Only Faiz can use this command."

        try:
            await self._token.force_refresh()
            age = self._token.token_age_seconds

            logger.info(
                "email_token_refreshed",
                user_id=user_id,
                token_age_seconds=round(age, 1),
            )

            return (
                f"✅ OAuth token refreshed. Token age: {age:.0f}s. "
                "Next refresh in ~7 days."
            )

        except GmailError as exc:
            logger.warning(
                "email_reauth_failed",
                user_id=user_id,
                error=str(exc),
            )
            return f"❌ Token refresh failed: {exc}"
        except Exception:
            logger.exception(
                "email_reauth_crash",
                user_id=user_id,
            )
            return "❌ An unexpected error occurred during token refresh."

    # ------------------------------------------------------------------
    # Faiz gate
    # ------------------------------------------------------------------

    def _check_faiz(self, user_id: int) -> bool:
        """Check whether *user_id* belongs to Faiz.

        Fail-closed: returns ``False`` if ``_FAIZ_USER_ID`` is zero
        (unconfigured) so no command is ever accidentally opened to
        everyone.

        Args:
            user_id: The Discord user ID to check.

        Returns:
            ``True`` if the user ID matches the configured Faiz ID.
        """
        if _FAIZ_USER_ID == 0:
            logger.warning(
                "faiz_user_id_not_configured",
                hint="Set GMAIL_FAIZ_USER_ID env var.",
            )
            return False
        return user_id == _FAIZ_USER_ID

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _resolve_user_id(message_or_interaction: Any) -> int:
        """Extract the Discord user ID from a message or interaction.

        Handles both ``discord.Message`` (has ``author.id``) and
        ``discord.Interaction`` (has ``user.id``) via duck-typing.

        Args:
            message_or_interaction: A Discord message or interaction.

        Returns:
            The user ID as an integer, or ``0`` if it cannot be resolved.
        """
        # discord.Message
        author = getattr(message_or_interaction, "author", None)
        if author is not None:
            return getattr(author, "id", 0)
        # discord.Interaction
        user = getattr(message_or_interaction, "user", None)
        if user is not None:
            return getattr(user, "id", 0)
        return 0

    @staticmethod
    def _resolve_actor_name(message_or_interaction: Any) -> str:
        """Extract a human-readable actor identifier for audit logging.

        Falls back to ``"discord_user_{id}"`` when no display name is
        available, and finally to ``"unknown"``.

        Args:
            message_or_interaction: A Discord message or interaction.

        Returns:
            A string identifying the actor.
        """
        # discord.Message
        author = getattr(message_or_interaction, "author", None)
        if author is not None:
            name = getattr(author, "global_name", None) or getattr(author, "name", None)
            if name:
                return str(name)
            return f"discord_user_{getattr(author, 'id', 0)}"

        # discord.Interaction
        user = getattr(message_or_interaction, "user", None)
        if user is not None:
            name = getattr(user, "global_name", None) or getattr(user, "name", None)
            if name:
                return str(name)
            return f"discord_user_{getattr(user, 'id', 0)}"

        return "unknown"


# ---------------------------------------------------------------------------
# Module exports
# ---------------------------------------------------------------------------

__all__ = [
    "EmailConsentCommands",
]
