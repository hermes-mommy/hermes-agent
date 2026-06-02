"""Guinevere Discord Bot — Main Entrypoint (P2-017).

Provides the overarching GuinevereBot class wrapping ``commands.Bot``,
HARD STOP guard via ``on_message`` listener, slash command registration,
and the ``main()`` entrypoint for VPS deployment with systemd.

Token is read from ``os.environ["DISCORD_BOT_TOKEN"]`` — never hardcoded.
"""

from __future__ import annotations

import asyncio
import importlib
import logging
import os
from typing import Any, cast, TYPE_CHECKING

import discord

if TYPE_CHECKING:
    import discord.ext.commands as commands_discord

from .intents import get_intents


# Dynamically import discord.ext.commands to avoid shadowing by the
# project-local ``src/discord/`` package.  The conftest pre-caches
# the real discord module so this importlib call resolves correctly.
_commands_module: Any = importlib.import_module("discord.ext.commands")
commands = _commands_module  # alias for class-definition access
_BotBase: type = commands.Bot  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# ── Guild ────────────────────────────────────────────────────────────────────

GUILD_ID: int = 1_510_876_414_671_323_206
"""Canonical guild ID from ``guild_setup.py``."""


# ── Stub Phase Map ───────────────────────────────────────────────────────────

_STUB_PHASE: dict[str, int] = {
    # Memory → Phase 3
    "memory-forget": 3,
    "memory-export": 3,
    # Finance, System, Admin → Phase 4
    "cost": 4,
    "budget": 4,
    "cost-alert": 4,
    "approve": 4,
    "deny": 4,
    "approve-all": 4,
    "focus": 4,
    "casual": 4,
    "consent": 4,
    "punishment": 4,
    "reward": 4,
    "restart-service": 4,
    "backup-now": 4,
    "health-check": 4,
    "clear-cache": 4,
    # Loop → Phase 5
    "loop-pause": 5,
    "loop-resume": 5,
    "loops": 5,
    "evidence": 5,
    "loop-priority": 5,
    # Surveillance → Phase 7
    "surveillance-status": 7,
    "surveillance-pause": 7,
    "surveillance-resume": 7,
}
"""Maps stub command names to their deployment phase."""


# ── Stub Callback Factory ────────────────────────────────────────────────────


def _make_stub_callback(command_name: str, phase: int) -> Any:
    """Create a placeholder slash command callback.

    Args:
        command_name: The slash command name.
        phase: The deployment phase number.

    Returns:
        An async callback that replies with a "not yet implemented" message.
    """

    async def callback(interaction: Any) -> None:
        """Stub response — not yet implemented."""
        msg = (
            f"Command ``{command_name}`` not yet implemented. "
            f"Coming in Phase {phase}."
        )
        await interaction.response.send_message(msg, ephemeral=True)

    return callback


# ── Bot Class ────────────────────────────────────────────────────────────────


class GuinevereBot(_BotBase):
    """Main Guinevere Discord bot.

    Wraps ``commands.Bot`` with:
    - Slash command tree (8 wired + 25 stubs) registered in ``setup_hook``.
    - HARD STOP guard via ``on_message`` listener.
    - Startup greeting via ``on_ready`` -> ``startup.on_ready()``.
    """

    def __init__(self) -> None:
        """Initialise the bot with canonical intents and prefix."""
        intents_obj = get_intents()
        super().__init__(
            command_prefix="!",
            intents=cast(discord.Intents, cast(object, intents_obj)),
        )
        logger.info("guinevere_bot_init")
        self._session_factory: object | None = None
        self._register_hard_stop_listener()

    # ── HARD STOP Listener ──────────────────────────────────────────────────────

    def _register_hard_stop_listener(self) -> None:
        """Register the ``on_message`` listener for HARD STOP detection.

        Listeners fire BEFORE the main ``on_message`` event handler,
        providing the earliest possible intercept for safe-word detection.
        """
        self.listen("on_message")(self._on_message_listener)

    async def _on_message_listener(self, message: Any) -> None:
        """HARD STOP guard — fires BEFORE main ``on_message``.

        Lazy-imports ``cmd_safeword`` to avoid circular imports.

        Args:
            message: The ``discord.Message`` the bot received.
        """
        # Skip bot messages to prevent self-trigger loops
        author = getattr(message, "author", None)
        if author is None:
            return
        if getattr(author, "bot", False):
            return

        from .cmd_safeword import handle_safeword_message_async

        consumed = await handle_safeword_message_async(message)
        if consumed:
            # Safe word triggered — block further processing
            return

    # ── setup_hook ──────────────────────────────────────────────────────────────

    async def setup_hook(self) -> None:
        """Register slash commands and guild-sync the command tree.

        8 wired callbacks (status, mood, help, safeword, memory-search,
        memory-add, loop-start, loop-stop) are imported lazily from their
        respective modules.  The remaining 25 commands get placeholder stubs.
        """
        # ── 8 Wired ───────────────────────────────────────────────────────────
        from .cmd_status import status_callback
        from .cmd_mood import mood_callback
        from .cmd_help import help_callback
        from .cmd_safeword import safeword_callback
        from .cmd_memory_search import memory_search_callback
        from .cmd_memory_add import memory_add_callback
        from .cmd_loop_start import loop_start_callback
        from .cmd_loop_stop import loop_stop_callback

        # Lazy import commands module for spec iteration
        from . import commands as cmds

        # Register wired callbacks
        self.tree.command(
            name="status",
            description="Show Mommy's current system, loop, and safety status.",
        )(status_callback)
        self.tree.command(
            name="mood",
            description="Show or update Guinevere's current mood state.",
        )(mood_callback)
        self.tree.command(
            name="help",
            description="Show the Guinevere command guide.",
        )(help_callback)
        self.tree.command(
            name="safeword",
            description="Trigger the configured safety boundary workflow.",
        )(safeword_callback)
        self.tree.command(
            name="memory-search",
            description="Search Guinevere's memories by query.",
        )(memory_search_callback)
        self.tree.command(
            name="memory-add",
            description="Manually add a memory note to Guinevere's store.",
        )(memory_add_callback)
        self.tree.command(
            name="loop-start",
            description="Start a supervised Guinevere work loop.",
        )(loop_start_callback)
        self.tree.command(
            name="loop-stop",
            description="Stop the active Guinevere work loop safely.",
        )(loop_stop_callback)

        # ── 25 Stubs ──────────────────────────────────────────────────────────
        core_names: tuple[str, ...] = (
            "status", "mood", "help", "safeword",
            "memory-search", "memory-add",
            "loop-start", "loop-stop",
        )
        for spec in cmds.COMMAND_SPECS:
            if spec.name in core_names:
                continue  # Already wired above
            phase = _STUB_PHASE.get(spec.name, 4)
            cb = _make_stub_callback(spec.name, phase)
            self.tree.command(name=spec.name, description=spec.description)(cb)

        # ── Guild-Scoped Sync ────────────────────────────────────────────────
        guild = discord.Object(id=GUILD_ID)
        synced = await self.tree.sync(guild=guild)
        logger.info(
            "commands_synced",
            extra={"count": len(synced)},
        )

    # ── Session Factory ───────────────────────────────────────────────────────

    def get_session_factory(self) -> object:
        """Return an async SQLAlchemy session factory, creating lazily if needed.

        Returns a callable that produces AsyncSession instances.
        Requires DATABASE_URL environment variable.

        Returns:
            An async session factory, or None if DATABASE_URL is not set.
        """
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

            engine = _create_async_engine(
                database_url, echo=False, pool_pre_ping=True,
            )
            self._session_factory = _async_sessionmaker(
                engine,
                class_=_AsyncSession,
                expire_on_commit=False,
            )
            logger.info("session_factory_initialized")

        return self._session_factory

    # ── on_ready ────────────────────────────────────────────────────────────────

    async def on_ready(self) -> None:
        """Log readiness and call the startup greeting handler.

        Logs ``bot_ready`` with user, guild count, and latency.
        Delegates greeting + presence to ``startup.on_ready()``.
        """
        logger.info(
            "bot_ready",
            extra={
                "user": str(self.user) if self.user else "unknown",
                "guild_count": len(self.guilds),
                "latency_ms": round(self.latency * 1000, 2),
            },
        )

        from .startup import on_ready as startup_on_ready

        await startup_on_ready(self)

    # ── on_message ──────────────────────────────────────────────────────────────

    async def on_message(self, message: Any) -> None:
        """Process commands ONLY if not in HARD STOP safe mode.

        The ``_on_message_listener`` (registered via ``@bot.listen``) fires
        first and handles safe-word trigger detection.  This method runs
        afterwards and checks whether safe mode is active before forwarding
        to ``process_commands``.  Non-recovery messages are blocked while
        in safe mode.

        Args:
            message: The ``discord.Message`` the bot received.
        """
        if message.author.bot:
            return

        from .cmd_safeword import _get_handler

        handler = _get_handler()
        if handler.is_safe:
            # Safe mode active — check for recovery, block non-recovery messages
            handler.check_recovery(message.content)
            return

        await self.process_commands(message)


# ── Entrypoint ────────────────────────────────────────────────────────────────


async def main() -> None:
    """Read the bot token from environment and start the gateway connection.

    Raises:
        RuntimeError: If ``DISCORD_BOT_TOKEN`` is not set or empty.
    """
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise RuntimeError(
            "DISCORD_BOT_TOKEN environment variable is required"
        )

    bot = GuinevereBot()
    try:
        async with bot:
            await bot.start(token)
    except AttributeError:
        # Fallback for discord.py versions that do not support
        # the async context manager pattern.
        await bot.start(token)


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(name)s [%(levelname)s] %(message)s",
    )
    asyncio.run(main())