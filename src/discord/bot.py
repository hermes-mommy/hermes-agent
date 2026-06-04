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
    from src.surveillance.safe_mode import SurveillanceSafeModeGuard

from .intents import get_intents
from src.discord.shadow_pipeline import ShadowPipeline


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

_STUB_PHASE: dict[str, int] = {}
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
    - Slash command tree (13 wired + 20 stubs) registered in ``setup_hook``.
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

        # S2.1: Shadow pipeline — disabled by default, opt-in via env
        self.shadow_pipeline: ShadowPipeline = ShadowPipeline(
            enabled=os.environ.get("SHADOW_ENABLED", "false").lower() == "true",
            traffic_pct=int(os.environ.get("SHADOW_TRAFFIC_PCT", "0")),
        )

        # P7.5-C5: Wire surveillance safe mode guard
        from src.surveillance.safe_mode import SurveillanceSafeModeGuard
        from .cmd_safeword import _get_handler

        self._surveillance_guard = SurveillanceSafeModeGuard(
            safety_state_getter=lambda: _get_handler().state
        )

    # ── Surveillance Guard ───────────────────────────────────────────────────────

    @property
    def surveillance_guard(self) -> SurveillanceSafeModeGuard:
        """Return the surveillance safe-mode guard."""
        return self._surveillance_guard

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

        13 wired callbacks (status, mood, help, safeword, memory-search,
        memory-add, loop-start, loop-stop, surveillance-status,
        surveillance-pause, surveillance-resume, cost, budget) are imported
        lazily from their respective modules.  The remaining commands get
        placeholder stubs.
        """
        # ── 13 Original Wired ──────────────────────────────────────────────────
        from .cmd_status import status_callback
        from .cmd_mood import mood_callback
        from .cmd_help import help_callback
        from .cmd_safeword import safeword_callback
        from .cmd_memory_search import memory_search_callback
        from .cmd_memory_add import memory_add_callback
        from .cmd_loop_start import loop_start_callback
        from .cmd_loop_stop import loop_stop_callback
        from .cmd_surveillance_status import surveillance_status_callback
        from .cmd_surveillance_pause import surveillance_pause_callback
        from .cmd_surveillance_resume import surveillance_resume_callback
        from .cmd_cost import cost_callback
        from .cmd_budget import budget_callback

        # ── 20 Batch D Wired (RG-010..RG-014) ────────────────────────────────
        from .cmd_memory_forget import memory_forget_callback
        from .cmd_memory_export import memory_export_callback
        from .cmd_cost_alert import cost_alert_callback
        from .cmd_approve import approve_callback
        from .cmd_deny import deny_callback
        from .cmd_approve_all import approve_all_callback
        from .cmd_focus import focus_callback
        from .cmd_casual import casual_callback
        from .cmd_consent import consent_callback
        from .cmd_punishment import punishment_callback
        from .cmd_reward import reward_callback
        from .cmd_restart_service import restart_service_callback
        from .cmd_backup_now import backup_now_callback
        from .cmd_health_check import health_check_callback
        from .cmd_clear_cache import clear_cache_callback
        from .cmd_loop_pause import loop_pause_callback
        from .cmd_loop_resume import loop_resume_callback
        from .cmd_loops import loops_callback
        from .cmd_evidence import evidence_callback
        from .cmd_loop_priority import loop_priority_callback

        # ── Hermes Phase 1: Conversation Session Commands ────────────────
        from .cmd_new_session import new_session_callback
        from .cmd_history import history_callback

        # Lazy import commands module for spec iteration
        from . import commands as cmds

        # Register wired callbacks
        self.tree.command(
            name="status",
            description="Show Mommy's current system, loop, and safety status.",
            guild=discord.Object(id=GUILD_ID),
        )(status_callback)
        self.tree.command(
            name="mood",
            description="Show or update Guinevere's current mood state.",
            guild=discord.Object(id=GUILD_ID),
        )(mood_callback)
        self.tree.command(
            name="help",
            description="Show the Guinevere command guide.",
            guild=discord.Object(id=GUILD_ID),
        )(help_callback)
        self.tree.command(
            name="safeword",
            description="Trigger the configured safety boundary workflow.",
            guild=discord.Object(id=GUILD_ID),
        )(safeword_callback)
        self.tree.command(
            name="memory-search",
            description="Search Guinevere's memories by query.",
            guild=discord.Object(id=GUILD_ID),
        )(memory_search_callback)
        self.tree.command(
            name="memory-add",
            description="Manually add a memory note to Guinevere's store.",
            guild=discord.Object(id=GUILD_ID),
        )(memory_add_callback)
        self.tree.command(
            name="loop-start",
            description="Start a supervised Guinevere work loop.",
            guild=discord.Object(id=GUILD_ID),
        )(loop_start_callback)
        self.tree.command(
            name="loop-stop",
            description="Stop the active Guinevere work loop safely.",
            guild=discord.Object(id=GUILD_ID),
        )(loop_stop_callback)
        self.tree.command(
            name="surveillance-status",
            description="Show surveillance system status and consent state.",
            guild=discord.Object(id=GUILD_ID),
        )(surveillance_status_callback)
        self.tree.command(
            name="surveillance-pause",
            description="Pause surveillance data collection.",
            guild=discord.Object(id=GUILD_ID),
        )(surveillance_pause_callback)
        self.tree.command(
            name="surveillance-resume",
            description="Resume surveillance data collection.",
            guild=discord.Object(id=GUILD_ID),
        )(surveillance_resume_callback)
        self.tree.command(
            name="cost",
            description="Show Guinevere cost usage for a given period.",
            guild=discord.Object(id=GUILD_ID),
        )(cost_callback)
        self.tree.command(
            name="budget",
            description="Show or update budget cap and current spend.",
            guild=discord.Object(id=GUILD_ID),
        )(budget_callback)

        # ── RG-010: Memory Commands ─────────────────────────────────────────
        self.tree.command(
            name="memory-forget",
            description="Request deletion of a Guinevere memory item.",
            guild=discord.Object(id=GUILD_ID),
        )(memory_forget_callback)
        self.tree.command(
            name="memory-export",
            description="Export approved Guinevere memory metadata.",
            guild=discord.Object(id=GUILD_ID),
        )(memory_export_callback)

        # ── RG-011: Finance Command ─────────────────────────────────────────
        self.tree.command(
            name="cost-alert",
            description="Show or update Guinevere cost alert thresholds.",
            guild=discord.Object(id=GUILD_ID),
        )(cost_alert_callback)

        # ── RG-012: System Commands ─────────────────────────────────────────
        self.tree.command(
            name="approve",
            description="Approve a pending Guinevere action.",
            guild=discord.Object(id=GUILD_ID),
        )(approve_callback)
        self.tree.command(
            name="deny",
            description="Deny a pending Guinevere action.",
            guild=discord.Object(id=GUILD_ID),
        )(deny_callback)
        self.tree.command(
            name="approve-all",
            description="Approve all safe pending Guinevere actions.",
            guild=discord.Object(id=GUILD_ID),
        )(approve_all_callback)
        self.tree.command(
            name="focus",
            description="Switch Guinevere into focused engineering mode.",
            guild=discord.Object(id=GUILD_ID),
        )(focus_callback)
        self.tree.command(
            name="casual",
            description="Switch Guinevere into lighter casual mode.",
            guild=discord.Object(id=GUILD_ID),
        )(casual_callback)
        self.tree.command(
            name="consent",
            description="Show or update consent boundaries.",
            guild=discord.Object(id=GUILD_ID),
        )(consent_callback)
        self.tree.command(
            name="punishment",
            description="Record or show the bounded punishment state.",
            guild=discord.Object(id=GUILD_ID),
        )(punishment_callback)
        self.tree.command(
            name="reward",
            description="Record or show the bounded reward state.",
            guild=discord.Object(id=GUILD_ID),
        )(reward_callback)

        # ── RG-013: Admin Commands ──────────────────────────────────────────
        self.tree.command(
            name="restart-service",
            description="Prepare a guarded service restart request.",
            guild=discord.Object(id=GUILD_ID),
        )(restart_service_callback)
        self.tree.command(
            name="backup-now",
            description="Request an immediate Guinevere backup run.",
            guild=discord.Object(id=GUILD_ID),
        )(backup_now_callback)
        self.tree.command(
            name="health-check",
            description="Run Guinevere service health checks.",
            guild=discord.Object(id=GUILD_ID),
        )(health_check_callback)
        self.tree.command(
            name="clear-cache",
            description="Request a guarded cache clear operation.",
            guild=discord.Object(id=GUILD_ID),
        )(clear_cache_callback)

        # ── RG-014: Loop Commands ───────────────────────────────────────────
        self.tree.command(
            name="loop-pause",
            description="Pause the active Guinevere work loop.",
            guild=discord.Object(id=GUILD_ID),
        )(loop_pause_callback)
        self.tree.command(
            name="loop-resume",
            description="Resume a paused Guinevere work loop.",
            guild=discord.Object(id=GUILD_ID),
        )(loop_resume_callback)
        self.tree.command(
            name="loops",
            description="List current and recent Guinevere work loops.",
            guild=discord.Object(id=GUILD_ID),
        )(loops_callback)
        self.tree.command(
            name="evidence",
            description="Fetch evidence for a step or active work loop.",
            guild=discord.Object(id=GUILD_ID),
        )(evidence_callback)
        self.tree.command(
            name="loop-priority",
            description="Set the priority for a Guinevere work loop.",
            guild=discord.Object(id=GUILD_ID),
        )(loop_priority_callback)

        # ── Hermes Phase 1: Conversation Session Commands ────────────────
        self.tree.command(
            name="new",
            description="Reset conversation history and start fresh.",
            guild=discord.Object(id=GUILD_ID),
        )(new_session_callback)
        self.tree.command(
            name="history",
            description="Show recent conversation turns with Mommy.",
            guild=discord.Object(id=GUILD_ID),
        )(history_callback)

        # ── Stubs (none remaining — all wired) ────────────────────────────
        core_names: tuple[str, ...] = (
            # Original 13
            "status", "mood", "help", "safeword",
            "memory-search", "memory-add",
            "loop-start", "loop-stop",
            "surveillance-status", "surveillance-pause", "surveillance-resume",
            "cost", "budget",
            # RG-010: Memory
            "memory-forget", "memory-export",
            # RG-011: Finance
            "cost-alert",
            # RG-012: System
            "approve", "deny", "approve-all",
            "focus", "casual", "consent", "punishment", "reward",
            # RG-013: Admin
            "restart-service", "backup-now", "health-check", "clear-cache",
            # RG-014: Loop
            "loop-pause", "loop-resume", "loops", "evidence", "loop-priority",
            # Hermes Phase 1: Conversation session
            "new", "history",
        )
        for spec in cmds.COMMAND_SPECS:
            if spec.name in core_names:
                continue  # Already wired above
            phase = _STUB_PHASE.get(spec.name, 4)
            cb = _make_stub_callback(spec.name, phase)
            self.tree.command(name=spec.name, description=spec.description, guild=discord.Object(id=GUILD_ID))(cb)

        # ── Guild-Scoped Sync ────────────────────────────────────────────────
        guild = discord.Object(id=GUILD_ID)
        synced = await self.tree.sync(guild=guild)
        logger.info(
            "commands_synced",
            extra={"count": len(synced)},
        )

    # ── Graceful Shutdown ──────────────────────────────────────────────────────

    async def close(self) -> None:
        """Graceful shutdown."""
        await super().close()

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

        After the safe-mode check, the conversational handler is tried for
        messages in ``#guinevere-chat``.  If the conversational handler
        absorbs the message, command processing is skipped.

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

        # Try conversational handler first (only for #guinevere-chat)
        from .conversational_handler import handle_conversation

        handled = await handle_conversation(self, message)
        if handled:
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