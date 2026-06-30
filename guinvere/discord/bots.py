"""Discord bot identities and factory for Guinevere.

Defines 3 bot identities (Guinevere, Pharsa, Company) and the
GuinevereBot class that wraps discord.py's commands.Bot. Provides
autonomous conversation initiation tied to M3 consciousness.

Only GuinevereBot is fully wired. Pharsa and Company are identity
definitions for future expansion.

D2 compliance: no live Discord tokens. Tests mock discord.py.
"""

from __future__ import annotations

import importlib
import logging
import os
from dataclasses import dataclass, field
from typing import Any, Protocol, cast

from guinevere.discord._infrastructure import get_intents, ShadowPipeline

logger = logging.getLogger(__name__)


# ── Bot Identity Definitions ─────────────────────────────────────────────


@dataclass(frozen=True)
class BotIdentity:
    """Describes a Discord bot identity."""

    name: str
    """Display name (e.g. 'Guinevere')."""

    command_prefix: str
    """Command prefix (e.g. '!')."""

    description: str
    """Short description of the bot's role."""

    channel_id: int | None = None
    """Primary channel ID for conversational output, if any."""

    status_text: str = ""
    """Presence status text."""

    active: bool = True
    """Whether this identity is actively implemented."""


BOT_IDENTITIES: tuple[BotIdentity, ...] = (
    BotIdentity(
        name="Guinevere",
        command_prefix="!",
        description="Primary AI companion — autonomous, emotional, Faiz-only.",
        channel_id=1_510_914_600_777_023_659,
        status_text="Darling \U0001f441",
        active=True,
    ),
    BotIdentity(
        name="Pharsa",
        command_prefix="!",
        description="Secondary persona — dark mirror, analytical, Faiz-only.",
        channel_id=1_510_914_600_777_023_659,
        status_text="Observer \U0001f441",
        active=False,
    ),
    BotIdentity(
        name="Company",
        command_prefix="!",
        description="Tertiary persona — corporate, formal, Faiz-only.",
        channel_id=1_510_914_600_777_023_659,
        status_text="Professional \U0001f441",
        active=False,
    ),
)


def get_identity(name: str) -> BotIdentity | None:
    """Look up a bot identity by name (case-insensitive)."""
    for identity in BOT_IDENTITIES:
        if identity.name.lower() == name.lower():
            return identity
    return None


# ── Bot Class ────────────────────────────────────────────────────────────

# Import discord.ext.commands dynamically to avoid shadowing by the
# project-local guinvere/discord/ package.
_commands_module: Any = importlib.import_module("discord.ext.commands")
commands = _commands_module
_BotBase: type = commands.Bot

GUILD_ID: int = 1_510_876_414_671_323_206


class GuinevereBot(_BotBase):
    """Primary Guinevere Discord bot.

    Wraps commands.Bot with:
    - 41 slash commands registered in setup_hook.
    - Auth guard (Faiz-only via guild owner check).
    - Autonomous conversation initiation hook (ties to M3 consciousness).
    - Shadow pipeline (disabled by default).
    - Startup greeting and presence management.
    """

    def __init__(self, identity: BotIdentity | None = None) -> None:
        """Initialize the bot with canonical intents and prefix.

        Args:
            identity: Bot identity to use. Defaults to Guinevere identity.
        """
        self.identity = identity or BOT_IDENTITIES[0]
        intents_obj = get_intents()
        super().__init__(
            command_prefix=self.identity.command_prefix,
            intents=cast(Any, intents_obj),
        )
        logger.info(
            "bot_init",
            extra={"identity": self.identity.name, "active": self.identity.active},
        )
        self._session_factory: object | None = None

        # Shadow pipeline — disabled by default, opt-in via env
        self.shadow_pipeline = ShadowPipeline(
            enabled=os.environ.get("SHADOW_ENABLED", "false").lower() == "true",
            traffic_pct=int(os.environ.get("SHADOW_TRAFFIC_PCT", "0")),
        )

        # Autonomous conversation initiation hook
        self._autonomous_initiator = AutonomousInitiator(self)

    # ── setup_hook ──────────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        """Register all 41 slash commands and guild-sync the command tree."""
        from guinevere.discord.commands import CommandRegistry

        registry = CommandRegistry(self)
        registry.register_all(self.tree)

        # Guild-scoped sync
        import discord

        guild = discord.Object(id=GUILD_ID)
        synced = await self.tree.sync(guild=guild)
        logger.info("commands_synced", extra={"count": len(synced)})

    # ── on_ready ────────────────────────────────────────────────────────

    async def on_ready(self) -> None:
        """Log readiness and set presence."""
        logger.info(
            "bot_ready",
            extra={
                "user": str(self.user) if self.user else "unknown",
                "guild_count": len(self.guilds),
                "latency_ms": round(self.latency * 1000, 2),
                "identity": self.identity.name,
            },
        )
        await self._set_presence()

    async def _set_presence(self) -> None:
        """Set bot presence to watching status."""
        import discord

        activity = discord.Activity(
            type=discord.ActivityType.watching,
            name=self.identity.status_text or "Darling \U0001f441",
        )
        await self.change_presence(activity=activity)

    # ── on_message ──────────────────────────────────────────────────────

    async def on_message(self, message: Any) -> None:
        """Process commands and conversational messages."""
        author = getattr(message, "author", None)
        if author is None:
            return
        if getattr(author, "bot", False):
            return

        await self.process_commands(message)

    # ── Session Factory ─────────────────────────────────────────────────

    def get_session_factory(self) -> object:
        """Return an async SQLAlchemy session factory, creating lazily."""
        if self._session_factory is None:
            database_url = os.environ.get("DATABASE_URL", "")
            if not database_url:
                logger.warning("session_factory_no_database_url")
                return None
            from sqlalchemy.ext.asyncio import (
                AsyncSession as _AsyncSession,
                async_sessionmaker as _async_sessionmaker,
                create_async_engine as _create_async_engine,
            )

            engine = _create_async_engine(database_url, echo=False, pool_pre_ping=True)
            self._session_factory = _async_sessionmaker(
                engine,
                class_=_AsyncSession,
                expire_on_commit=False,
            )
            logger.info("session_factory_initialized")
        return self._session_factory

    # ── Graceful Shutdown ───────────────────────────────────────────────

    async def close(self) -> None:
        """Graceful shutdown."""
        await super().close()


# ── Autonomous Conversation Initiation ───────────────────────────────────


class AutonomousInitiator:
    """Background task for autonomous conversation initiation.

    Ties into M3 consciousness to trigger proactive outreach to the
    #guinevere-chat channel. Disabled by default; enabled via
    AUTONOMOUS_CHAT env var.
    """

    CHANNEL_ID: int = 1_510_914_600_777_023_659

    def __init__(self, bot: GuinevereBot) -> None:
        self._bot = bot
        self._enabled: bool = os.environ.get("AUTONOMOUS_CHAT", "false").lower() == "true"
        self._interval_hours: int = int(os.environ.get("AUTONOMOUS_CHAT_INTERVAL_HOURS", "4"))
        self._task: Any | None = None

    @property
    def enabled(self) -> bool:
        """Whether autonomous initiation is enabled."""
        return self._enabled

    @property
    def interval_hours(self) -> int:
        """Hours between autonomous initiation attempts."""
        return self._interval_hours

    async def start(self) -> None:
        """Start the autonomous initiation background loop."""
        if not self._enabled:
            logger.info("autonomous_initiator_disabled")
            return

        try:
            from discord.ext import tasks

            @tasks.loop(hours=float(self._interval_hours))
            async def _autonomous_loop() -> None:
                await self._send_proactive_message()

            self._task = _autonomous_loop
            _autonomous_loop.start()
            logger.info(
                "autonomous_initiator_started",
                extra={"interval_hours": self._interval_hours},
            )
        except (ImportError, AttributeError) as exc:
            logger.warning("autonomous_initiator_start_failed", extra={"error": str(exc)})

    async def _send_proactive_message(self) -> None:
        """Send a proactive message to the primary channel.

        This is the hook point for M3 consciousness integration.
        Currently sends a check-in prompt; future implementations
        will query the consciousness state for mood/context.
        """
        channel = self._bot.get_channel(self.CHANNEL_ID)
        if channel is None:
            logger.warning("autonomous_channel_not_found", extra={"channel_id": self.CHANNEL_ID})
            return

        try:
            await channel.send(
                "*Mommy is checking in on you, Darling.* \U0001f441"
            )
            logger.info("autonomous_message_sent")
        except (OSError, RuntimeError) as exc:
            logger.warning("autonomous_send_failed", extra={"error": str(exc)})

    def stop(self) -> None:
        """Stop the autonomous initiation loop."""
        if self._task is not None:
            self._task.cancel()
            self._task = None


# ── Factory ──────────────────────────────────────────────────────────────


def create_bot(identity_name: str = "Guinevere") -> GuinevereBot:
    """Create a GuinevereBot instance for the given identity name.

    Args:
        identity_name: One of 'Guinevere', 'Pharsa', 'Company'.

    Returns:
        A configured GuinevereBot instance.

    Raises:
        ValueError: If the identity name is not recognized.
    """
    identity = get_identity(identity_name)
    if identity is None:
        valid = ", ".join(i.name for i in BOT_IDENTITIES)
        raise ValueError(f"Unknown bot identity '{identity_name}'. Valid: {valid}")
    return GuinevereBot(identity=identity)


async def main(identity_name: str = "Guinevere") -> None:
    """Read the bot token from environment and start the gateway connection.

    Args:
        identity_name: Bot identity to use.

    Raises:
        RuntimeError: If DISCORD_BOT_TOKEN is not set or empty.
    """
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError("DISCORD_BOT_TOKEN environment variable is required")

    bot = create_bot(identity_name)
    try:
        async with bot:
            await bot.start(token)
    except AttributeError:
        await bot.start(token)
