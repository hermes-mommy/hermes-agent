"""Deterministic tests for ``src.discord.bot``.

All tests run without establishing a Discord gateway connection.
The bot class is instantiated with real ``discord.py`` but API-calling
methods (``tree.sync``, ``start``) are mocked at the method level.

Key test surfaces:
- ``GuinevereBot`` instantiation succeeds with canonical intents.
- ``setup_hook`` registers exactly 33 slash commands.
- Handler imports (cmd_safeword, startup, commands) resolve without error.
- ``on_message`` listener skips bot-authored messages.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def bot() -> Any:
    """Create a ``GuinevereBot`` instance without starting a connection.

    The bot is imported lazily so that any missing import errors are
    surfaced as test failures rather than module-level crashes.
    """
    from src.discord.bot import GuinevereBot

    instance = GuinevereBot()
    return instance


@pytest.fixture
def mocked_bot(bot: Any) -> Any:
    """Return a bot with key API methods (start, tree.sync) mocked."""
    bot.start = AsyncMock()  # type: ignore[method-assign]
    bot.tree.sync = AsyncMock(return_value=[])  # type: ignore[method-assign]
    return bot


# ── Class Instantiation ─────────────────────────────────────────────────────


class TestInstantiation:
    """``GuinevereBot`` must instantiate cleanly."""

    def test_bot_is_not_none(self, bot: Any) -> None:
        assert bot is not None

    def test_bot_is_instance(self, bot: Any) -> None:
        from discord.ext import commands

        assert isinstance(bot, commands.Bot)

    def test_command_prefix_is_exclamation(self, bot: Any) -> None:
        assert bot.command_prefix == "!"


# ── Intents ──────────────────────────────────────────────────────────────────


class TestIntents:
    """Bot must have the required gateway intents."""

    def test_intents_not_none(self, bot: Any) -> None:
        assert bot.intents is not None

    def test_guilds_intent(self, bot: Any) -> None:
        assert bot.intents.guilds is True

    def test_members_intent(self, bot: Any) -> None:
        assert bot.intents.members is True

    def test_message_content_intent(self, bot: Any) -> None:
        assert bot.intents.message_content is True

    def test_messages_intent(self, bot: Any) -> None:
        assert bot.intents.messages is True

    def test_presences_intent(self, bot: Any) -> None:
        assert bot.intents.presences is True

    def test_reactions_intent(self, bot: Any) -> None:
        assert bot.intents.reactions is True

    def test_voice_states_intent(self, bot: Any) -> None:
        assert bot.intents.voice_states is True


# ── setup_hook ────────────────────────────────────────────────────────────────


class TestSetupHook:
    """``setup_hook`` must register exactly 33 slash commands."""

    @pytest.mark.asyncio
    async def test_register_33_commands(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        registered = mocked_bot.tree.get_commands()
        assert len(registered) == 33, (
            f"Expected 33 commands, got {len(registered)}"
        )

    @pytest.mark.asyncio
    async def test_all_names_are_strings(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        for cmd in mocked_bot.tree.get_commands():
            assert isinstance(cmd.name, str), f"Name is not str: {cmd.name}"

    @pytest.mark.asyncio
    async def test_all_descriptions_are_strings(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        for cmd in mocked_bot.tree.get_commands():
            assert isinstance(cmd.description, str), (
                f"Description is not str for {cmd.name}"
            )

    @pytest.mark.asyncio
    async def test_core_commands_are_present(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        names = {cmd.name for cmd in mocked_bot.tree.get_commands()}
        for expected in ("status", "mood", "help", "safeword"):
            assert expected in names, f"Missing core command: {expected}"

    @pytest.mark.asyncio
    async def test_stub_commands_present(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        names = {cmd.name for cmd in mocked_bot.tree.get_commands()}
        for expected in (
            "loop-start",
            "memory-search",
            "surveillance-status",
            "cost",
            "approve",
            "restart-service",
        ):
            assert expected in names, f"Missing stub command: {expected}"

    @pytest.mark.asyncio
    async def test_sync_called_once(self, mocked_bot: Any) -> None:
        await mocked_bot.setup_hook()

        assert mocked_bot.tree.sync.await_count == 1


# ── Handler Imports ───────────────────────────────────────────────────────────


class TestHandlerImports:
    """Handler modules must import without error."""

    def test_import_cmd_safeword(self) -> None:
        import src.discord.cmd_safeword
        assert hasattr(src.discord.cmd_safeword, "handle_safeword_message_async")

    def test_import_startup(self) -> None:
        import src.discord.startup
        assert hasattr(src.discord.startup, "on_ready")

    def test_import_commands(self) -> None:
        import src.discord.commands
        assert src.discord.commands.command_count() == 33

    def test_import_cmd_status(self) -> None:
        import src.discord.cmd_status
        assert hasattr(src.discord.cmd_status, "status_callback")

    def test_import_cmd_mood(self) -> None:
        import src.discord.cmd_mood
        assert hasattr(src.discord.cmd_mood, "mood_callback")

    def test_import_cmd_help(self) -> None:
        import src.discord.cmd_help
        assert hasattr(src.discord.cmd_help, "help_callback")


# ── on_message Listener ───────────────────────────────────────────────────────


class TestOnMessageListener:
    """The HARD STOP listener must skip bot messages."""

    @pytest.mark.asyncio
    async def test_listener_skips_bot_message(self, bot: Any) -> None:
        """Listener should return early for bot-authored messages."""
        mock_message = MagicMock()
        mock_message.author.bot = True
        mock_message.content = "HARD STOP"

        # The listener should not raise even with a trigger message
        # because bot messages are skipped.
        await bot._on_message_listener(mock_message)

    @pytest.mark.asyncio
    async def test_listener_handles_no_author(self, bot: Any) -> None:
        """Listener must not crash when message has no author."""
        mock_message = MagicMock(spec=[])
        del mock_message.author

        await bot._on_message_listener(mock_message)

    @pytest.mark.asyncio
    async def test_main_on_message_skips_bot(self, bot: Any) -> None:
        """Main ``on_message`` should return early for bot-authored messages."""
        mock_message = MagicMock()
        mock_message.author.bot = True

        await bot.on_message(mock_message)

    @pytest.mark.asyncio
    async def test_main_on_message_skips_in_safe_mode(
        self,
        bot: Any,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Main ``on_message`` should block if safe mode is active."""
        mock_message = MagicMock()
        mock_message.author.bot = False
        mock_message.content = "some message"

        # Mock handler to be in safe mode
        mock_handler = MagicMock()
        mock_handler.is_safe = True

        # Patch _get_handler to return our mock
        import src.discord.cmd_safeword

        monkeypatch.setattr(
            src.discord.cmd_safeword,
            "_get_handler",
            lambda: mock_handler,
        )

        # Should process the recovery check but not crash
        await bot.on_message(mock_message)

        assert mock_handler.check_recovery.called


# ── Entrypoint ────────────────────────────────────────────────────────────────


class TestEntrypoint:
    """The ``main()`` entrypoint must require the token environment variable."""

    def test_main_raises_without_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``main()`` must raise ``RuntimeError`` if token is missing."""
        monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)

        from src.discord.bot import main

        with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
            asyncio_run(main())

    def test_main_raises_with_empty_token(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """``main()`` must raise ``RuntimeError`` if token is empty."""
        monkeypatch.setenv("DISCORD_BOT_TOKEN", "")

        from src.discord.bot import main

        with pytest.raises(RuntimeError, match="DISCORD_BOT_TOKEN"):
            asyncio_run(main())


def asyncio_run(coro: Any) -> Any:
    """Run a coroutine in a new event loop (helper for sync test functions)."""
    import asyncio as _asyncio

    loop = _asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Python 3.12+ Style ───────────────────────────────────────────────────────


class TestPython312Style:
    """File must use ``from __future__ import annotations``."""

    def test_module_has_annotations_future(self) -> None:
        import inspect

        from src.discord import bot

        source = inspect.getsource(bot)
        assert "from __future__ import annotations" in source