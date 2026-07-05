from __future__ import annotations

"""Discord embed + reaction-based draft approval flow.

Presents draft replies as Discord embeds with ✅/❌/✏️ reactions,
enforcing Faiz-only approval before any draft is sent. State is
persisted to Redis HASH keys with TTL matching the draft timeout.
"""

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Final

import structlog

from ..config import get_gmail_settings, GmailSettings
from ..exceptions import GmailDraftError, DraftExpiredError
from ..metrics import record_draft_approved, record_draft_rejected

if TYPE_CHECKING:
    import discord

logger = structlog.get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DRAFT_REDIS_PREFIX: Final[str] = "guinevere:gmail:draft:"
REACTION_APPROVE: Final[str] = "\u2705"
REACTION_REJECT: Final[str] = "\u274c"
REACTION_EDIT: Final[str] = "\u270f\ufe0f"
EMBED_COLOR: Final[int] = 0x2ECC71
EMBED_DESC_TRUNCATE: Final[int] = 1024
EMBED_TITLE_TRUNCATE: Final[int] = 50
EMBED_FIELD_TRUNCATE: Final[int] = 1024

_HTML_TAG_RE: Final[re.Pattern[str]] = re.compile(r"<[^>]+>")


def _strip_html(text: str) -> str:
    """Remove HTML tags for safe plain-text display."""
    return _HTML_TAG_RE.sub("", text).strip()


# ---------------------------------------------------------------------------
# Approval context
# ---------------------------------------------------------------------------


@dataclass
class ApprovalContext:
    """Tracks the full lifecycle state of a single draft approval.

    Serialised to/from JSON inside a Redis HASH so it survives restarts.
    """

    draft_id: str
    message_id: str
    thread_id: str
    subject: str
    body_html: str
    reasoning: str
    discord_message_id: int | None = None
    channel_id: int = 0
    state: str = "pending"
    """One of ``pending``, ``approved``, ``rejected``, ``edited``, ``expired``."""
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc) + timedelta(hours=24),
    )


# ---------------------------------------------------------------------------
# Approval flow
# ---------------------------------------------------------------------------


class DraftApprovalFlow:
    """Discord embed + reaction-based draft approval for Faiz-only sending.

    Usage::

        flow = DraftApprovalFlow(redis=app.state.redis)
        ctx = await flow.present_for_approval(
            draft_id=..., subject=..., body_html=..., reasoning=...,
            message_id=..., thread_id=..., channel=discord_channel,
        )
        new_state = await flow.handle_reaction(draft_id, emoji, user_id)
    """

    def __init__(
        self,
        redis,
        settings: GmailSettings | None = None,
    ) -> None:
        """Initialise the approval flow.

        Args:
            redis: An async Redis client (``redis.asyncio.Redis``).
            settings: Optional ``GmailSettings``. Falls back to singleton.
        """
        self._redis = redis
        self._settings = settings or get_gmail_settings()
        self._owner_user_id: int = self._resolve_owner_id()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def present_for_approval(
        self,
        draft_id: str,
        subject: str,
        body_html: str,
        reasoning: str,
        message_id: str,
        thread_id: str,
        channel,
    ) -> ApprovalContext:
        """Post a Discord embed, add reactions, and persist state to Redis.

        Raises:
            GmailDraftError: If the embed or reactions could not be sent,
                or state could not be persisted.
        """
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=self._settings.draft_timeout_hours)

        ctx = ApprovalContext(
            draft_id=draft_id,
            message_id=message_id,
            thread_id=thread_id,
            subject=subject,
            body_html=body_html,
            reasoning=reasoning,
            created_at=now,
            expires_at=expires_at,
            state="pending",
        )

        try:
            discord_message = await channel.send(embed=self._build_embed(ctx))
        except Exception as exc:
            raise GmailDraftError(
                f"Failed to send approval embed for draft {draft_id}: {exc}",
            ) from exc

        ctx.discord_message_id = discord_message.id
        ctx.channel_id = channel.id

        try:
            await discord_message.add_reaction(REACTION_APPROVE)
            await discord_message.add_reaction(REACTION_REJECT)
            await discord_message.add_reaction(REACTION_EDIT)
        except Exception as exc:
            raise GmailDraftError(
                f"Failed to add reactions to draft {draft_id}: {exc}",
            ) from exc

        await self._save(ctx)

        logger.info(
            "gmail.draft.presented",
            draft_id=draft_id,
            message_id=message_id,
            discord_message_id=discord_message.id,
            timeout_hours=self._settings.draft_timeout_hours,
        )

        return ctx

    async def handle_reaction(
        self,
        draft_id: str,
        reaction_emoji: str,
        user_id: int,
    ) -> str:
        """Process a reaction on a draft approval embed.

        Only the configured ``owner_user_id`` may approve, reject, or
        request edits. Other reactors are logged and ignored.

        Returns:
            The new state: ``approved``, ``rejected``, ``edited``,
            ``ignored``, or ``not_found``.

        Raises:
            DraftExpiredError: If the draft's expiry window has passed.
        """
        if user_id != self._owner_user_id:
            logger.warning(
                "gmail.draft.reaction_ignored",
                draft_id=draft_id,
                user_id=user_id,
                reason="not_owner",
            )
            return "ignored"

        ctx = await self.get_context(draft_id)
        if ctx is None:
            logger.warning("gmail.draft.not_found", draft_id=draft_id)
            return "not_found"

        now = datetime.now(timezone.utc)
        if now > ctx.expires_at:
            await self._transition_state(draft_id, "expired")
            raise DraftExpiredError(draft_id)

        if ctx.state != "pending":
            logger.info(
                "gmail.draft.already_processed",
                draft_id=draft_id,
                state=ctx.state,
            )
            return ctx.state

        if reaction_emoji == REACTION_APPROVE:
            await self.on_approved(draft_id)
            return "approved"
        if reaction_emoji == REACTION_REJECT:
            await self.on_rejected(draft_id)
            return "rejected"
        if reaction_emoji == REACTION_EDIT:
            await self.on_edit_requested(draft_id)
            return "edited"

        logger.debug(
            "gmail.draft.unexpected_reaction",
            draft_id=draft_id,
            emoji=reaction_emoji,
        )
        return "ignored"

    async def on_approved(self, draft_id: str) -> ApprovalContext:
        """Transition to ``approved`` and record metric."""
        ctx = await self._transition_state(draft_id, "approved")
        record_draft_approved()
        logger.info("gmail.draft.approved", draft_id=draft_id)
        return ctx

    async def on_rejected(self, draft_id: str) -> ApprovalContext:
        """Transition to ``rejected`` and record metric."""
        ctx = await self._transition_state(draft_id, "rejected")
        record_draft_rejected()
        logger.info("gmail.draft.rejected", draft_id=draft_id)
        return ctx

    async def on_edit_requested(self, draft_id: str) -> ApprovalContext:
        """Transition to ``edited`` state."""
        ctx = await self._transition_state(draft_id, "edited")
        logger.info("gmail.draft.edit_requested", draft_id=draft_id)
        return ctx

    async def get_context(self, draft_id: str) -> ApprovalContext | None:
        """Load the approval context from Redis. Returns ``None`` if missing."""
        key = self._redis_key(draft_id)
        raw = await self._redis.hgetall(key)
        if not raw:
            return None

        data: dict[str, object] = {}
        for k_bytes, v_bytes in raw.items():
            ks = k_bytes.decode() if isinstance(k_bytes, bytes) else k_bytes
            vs = v_bytes.decode() if isinstance(v_bytes, bytes) else v_bytes
            data[ks] = json.loads(vs)

        return self._from_dict(data)

    async def clean_expired(self) -> int:
        """Mark all expired pending drafts as ``expired`` and return count."""
        now = datetime.now(timezone.utc)
        cleaned = 0

        async for key in self._redis.scan_iter(match=f"{DRAFT_REDIS_PREFIX}*"):
            raw = await self._redis.hgetall(key)
            if not raw:
                continue

            data: dict[str, object] = {}
            for k_bytes, v_bytes in raw.items():
                ks = k_bytes.decode() if isinstance(k_bytes, bytes) else k_bytes
                vs = v_bytes.decode() if isinstance(v_bytes, bytes) else v_bytes
                data[ks] = json.loads(vs)

            if data.get("state", "pending") != "pending":
                continue

            expires_str = data.get("expires_at")
            if not expires_str:
                continue

            expires = datetime.fromisoformat(str(expires_str))
            if now >= expires:
                await self._redis.hset(
                    self._redis_key(str(data.get("draft_id", str(key)))),
                    "state",
                    json.dumps("expired"),
                )
                cleaned += 1

        if cleaned:
            logger.info("gmail.draft.clean_expired", count=cleaned)

        return cleaned

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_owner_id(self) -> int:
        """Get the Discord user ID authorised to approve drafts.

        Resolution order: ``GmailSettings.owner_user_id`` (future),
        ``GMAIL_OWNER_USER_ID`` env var, fallback ``0``.
        """
        raw = (
            getattr(self._settings, "owner_user_id", None)
            or os.environ.get("GMAIL_OWNER_USER_ID", "")
        )
        if raw:
            return int(raw)

        logger.warning(
            "gmail.draft.owner_not_configured",
            message="GMAIL_OWNER_USER_ID not set; all reactions ignored.",
        )
        return 0

    def _redis_key(self, draft_id: str) -> str:
        return f"{DRAFT_REDIS_PREFIX}{draft_id}"

    def _build_embed(self, ctx: ApprovalContext) -> discord.Embed:
        """Build the Discord embed for a draft approval card."""
        short_title = (
            ctx.subject[:EMBED_TITLE_TRUNCATE]
            if len(ctx.subject) > EMBED_TITLE_TRUNCATE
            else ctx.subject
        )
        description = _strip_html(ctx.body_html)[:EMBED_DESC_TRUNCATE]
        hours = max(
            0,
            int((ctx.expires_at - datetime.now(timezone.utc)).total_seconds() / 3600),
        )

        embed = discord.Embed(
            title=f"\u2709\ufe0f Draft Reply \u2014 {short_title}",
            description=description,
            color=EMBED_COLOR,
        )
        embed.add_field(name="From", value=ctx.message_id, inline=False)
        embed.add_field(
            name="Subject",
            value=ctx.subject[:EMBED_FIELD_TRUNCATE],
            inline=False,
        )
        embed.add_field(
            name="Reasoning",
            value=ctx.reasoning[:EMBED_FIELD_TRUNCATE],
            inline=False,
        )
        embed.set_footer(
            text=(
                f"React {REACTION_APPROVE} to send"
                f" \u2502 {REACTION_REJECT} to reject"
                f" \u2502 {REACTION_EDIT} to edit"
                f" \u2502 Expires in {hours}h"
            ),
        )
        return embed

    async def _save(self, ctx: ApprovalContext) -> None:
        """Persist context to a Redis HASH with TTL."""
        key = self._redis_key(ctx.draft_id)
        serialised = {
            k: json.dumps(v) for k, v in self._to_dict(ctx).items()
        }
        await self._redis.hset(key, mapping=serialised)

        remaining = (ctx.expires_at - datetime.now(timezone.utc)).total_seconds()
        await self._redis.expire(key, max(1, int(remaining)))

    async def _transition_state(self, draft_id: str, new_state: str) -> ApprovalContext:
        """Atomically update the state field in Redis and return fresh context.

        Raises:
            GmailDraftError: If the draft does not exist in Redis.
        """
        key = self._redis_key(draft_id)
        if not await self._redis.exists(key):
            raise GmailDraftError(
                f"Cannot transition draft {draft_id}: not found in Redis",
            )

        await self._redis.hset(key, "state", json.dumps(new_state))

        ctx = await self.get_context(draft_id)
        if ctx is None:
            raise GmailDraftError(
                f"Draft {draft_id} disappeared after state transition",
            )
        return ctx

    # ------------------------------------------------------------------
    # Serialisation
    # ------------------------------------------------------------------

    @staticmethod
    def _to_dict(ctx: ApprovalContext) -> dict[str, object]:
        """Convert ``ApprovalContext`` to a JSON-safe dictionary."""
        return {
            "draft_id": ctx.draft_id,
            "message_id": ctx.message_id,
            "thread_id": ctx.thread_id,
            "subject": ctx.subject,
            "body_html": ctx.body_html,
            "reasoning": ctx.reasoning,
            "discord_message_id": ctx.discord_message_id,
            "channel_id": ctx.channel_id,
            "state": ctx.state,
            "created_at": ctx.created_at.isoformat(),
            "expires_at": ctx.expires_at.isoformat(),
        }

    @staticmethod
    def _from_dict(data: dict[str, object]) -> ApprovalContext:
        """Rehydrate ``ApprovalContext`` from a JSON-safe dictionary."""
        raw_discord = data.get("discord_message_id")
        discord_message_id: int | None = (
            raw_discord if isinstance(raw_discord, int) else None
        )
        raw_channel = data.get("channel_id", 0)
        channel_id: int = raw_channel if isinstance(raw_channel, int) else 0

        return ApprovalContext(
            draft_id=str(data["draft_id"]),
            message_id=str(data["message_id"]),
            thread_id=str(data["thread_id"]),
            subject=str(data["subject"]),
            body_html=str(data["body_html"]),
            reasoning=str(data["reasoning"]),
            discord_message_id=discord_message_id,
            channel_id=channel_id,
            state=str(data.get("state", "pending")),
            created_at=datetime.fromisoformat(str(data["created_at"])),
            expires_at=datetime.fromisoformat(str(data["expires_at"])),
        )


__all__ = [
    "ApprovalContext",
    "DraftApprovalFlow",
]
