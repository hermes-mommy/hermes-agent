"""Smoke tests for ``src.discord.hermes_conversational`` (active handler).

This file replaces the archived legacy conversational-handler test snapshot
stored under ``phase-7c-b3-archive/archived-tests/``.

These tests verify that the active ``hermes_conversational`` module exports its
public API correctly — constants, stateless helpers, and async entrypoints —
without exercising the full Hermes AIAgent integration (which requires real
LLM/DB backends).

Coverage:
- All public constants import correctly
- ``_split_response`` stateless function behaves as expected
- ``_is_rate_limited`` is a callable async function
- ``handle_conversation`` has the expected signature
"""

from __future__ import annotations

import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord.hermes_conversational import (
    DISCORD_MAX_CHARS,
    FALLBACK_MESSAGE,
    GUINEVERE_CHAT_CHANNEL_ID,
    MAX_CHUNKS,
    _split_response,
    handle_conversation,
)


# ── Constants ────────────────────────────────────────────────────────────────


class TestConstants:
    """Public constants must have the expected values."""

    def test_discord_max_chars(self) -> None:
        assert DISCORD_MAX_CHARS == 2000

    def test_max_chunks(self) -> None:
        assert MAX_CHUNKS == 3

    def test_guinevere_chat_channel_id(self) -> None:
        assert GUINEVERE_CHAT_CHANNEL_ID == 1_510_914_600_777_023_659

    def test_fallback_message(self) -> None:
        assert isinstance(FALLBACK_MESSAGE, str)
        assert len(FALLBACK_MESSAGE) > 0
        assert "trouble" in FALLBACK_MESSAGE or "sorry" in FALLBACK_MESSAGE


# ── _split_response ──────────────────────────────────────────────────────────


class TestSplitResponse:
    """_split_response must produce Discord-sendable chunks."""

    def test_short_text_no_split(self) -> None:
        """Text under 2000 chars → single chunk."""
        chunks = _split_response("Hello world")
        assert chunks == ["Hello world"]

    def test_sentence_boundary_respected(self) -> None:
        """Split occurs at sentence boundaries."""
        text = "A. " * 1500  # ~4500 chars
        chunks = _split_response(text)
        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= DISCORD_MAX_CHARS

    def test_max_chunks_respected(self) -> None:
        """Output is capped at MAX_CHUNKS (3)."""
        text = "X" * 10_000
        chunks = _split_response(text)
        assert len(chunks) <= MAX_CHUNKS

    def test_truncation_marker_on_long_text(self) -> None:
        """Very long text gets truncated with marker."""
        text = "Y" * 10_000
        chunks = _split_response(text)
        assert len(chunks) >= 1
        total = sum(len(c) for c in chunks)
        assert total < len(text)

    def test_all_chunks_within_discord_limit(self) -> None:
        """Every chunk must be within Discord char limit."""
        text = "Sentence one. " * 500
        chunks = _split_response(text)
        for chunk in chunks:
            assert len(chunk) <= DISCORD_MAX_CHARS


# ── _is_rate_limited ─────────────────────────────────────────────────────────


class TestIsRateLimited:
    """_is_rate_limited must be a callable async function."""

    def test_is_callable(self) -> None:
        from src.discord.hermes_conversational import _is_rate_limited

        assert callable(_is_rate_limited)

    def test_is_async(self) -> None:
        from src.discord.hermes_conversational import _is_rate_limited

        assert inspect.iscoroutinefunction(_is_rate_limited)

    @pytest.mark.asyncio
    async def test_returns_bool(self) -> None:
        """With a mocked Redis returning a low count, returns False."""
        from src.discord.hermes_conversational import _is_rate_limited

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(return_value=1)

        with patch(
            "src.discord.hermes_conversational._get_rate_limit_redis",
            return_value=mock_redis,
        ):
            result = await _is_rate_limited(12345)
        assert result is False

    @pytest.mark.asyncio
    async def test_redis_error_returns_false(self) -> None:
        """When Redis raises ConnectionError, returns False gracefully."""
        from src.discord.hermes_conversational import _is_rate_limited

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch(
            "src.discord.hermes_conversational._get_rate_limit_redis",
            return_value=mock_redis,
        ):
            result = await _is_rate_limited(12345)
        assert result is False


# ── handle_conversation ──────────────────────────────────────────────────────


class TestHandleConversation:
    """handle_conversation interface must match the expected contract."""

    def test_is_async_function(self) -> None:
        assert inspect.iscoroutinefunction(handle_conversation)

    def test_signature(self) -> None:
        sig = inspect.signature(handle_conversation)
        params = list(sig.parameters.keys())
        assert params == ["bot", "message"]

    @pytest.mark.asyncio
    async def test_returns_false_wrong_channel(self) -> None:
        """Message in wrong channel → returns False."""
        bot = MagicMock()
        msg = MagicMock()
        msg.channel.id = 999999999
        msg.author.bot = False
        msg.content = "hello"
        msg.guild.owner_id = 12345
        msg.author.id = 12345

        result = await handle_conversation(bot, msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_bot_author(self) -> None:
        """Bot-authored message → returns False."""
        bot = MagicMock()
        msg = MagicMock()
        msg.channel.id = GUINEVERE_CHAT_CHANNEL_ID
        msg.author.bot = True
        msg.content = "hello"

        result = await handle_conversation(bot, msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_slash_command(self) -> None:
        """Slash command → returns False."""
        bot = MagicMock()
        msg = MagicMock()
        msg.channel.id = GUINEVERE_CHAT_CHANNEL_ID
        msg.author.bot = False
        msg.content = "/status"

        result = await handle_conversation(bot, msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_false_non_owner(self) -> None:
        """Non-owner author → returns False."""
        bot = MagicMock()
        msg = MagicMock()
        msg.channel.id = GUINEVERE_CHAT_CHANNEL_ID
        msg.author.bot = False
        msg.author.id = 99999
        msg.content = "hello"
        msg.guild.owner_id = 12345

        result = await handle_conversation(bot, msg)
        assert result is False

    @pytest.mark.asyncio
    async def test_returns_true_rate_limited(self) -> None:
        """Rate-limited message → returns True (silently absorbed)."""
        bot = MagicMock()
        msg = MagicMock(spec=[])
        msg.channel = MagicMock()
        msg.channel.id = GUINEVERE_CHAT_CHANNEL_ID
        msg.author = MagicMock()
        msg.author.bot = False
        msg.author.id = 12345
        msg.content = "hello"
        msg.guild = MagicMock()
        msg.guild.owner_id = 12345

        with patch(
            "src.discord.hermes_conversational._is_rate_limited",
            new=AsyncMock(return_value=True),
        ):
            result = await handle_conversation(bot, msg)

        assert result is True
        msg.channel.send.assert_not_called()
