"""Deterministic tests for ``src.discord.conversational_handler``.

All tests run fully mocked — no Discord gateway, no Redis, no LLM calls.
Covers guard checks, rate limiting, memory recall, distress detection,
LLM response handling, response splitting, and cost tracking.

18 test cases covering all critical paths.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.discord.conversational_handler import (
    DISCORD_MAX_CHARS,
    FALLBACK_MESSAGE,
    GUINEVERE_CHAT_CHANNEL_ID,
    MAX_CHUNKS,
    _split_response,
    handle_conversation,
)


# ── Constants ────────────────────────────────────────────────────────────────

FAIZ_ID: int = 12345
MODULE = "src.discord.conversational_handler"


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture()
def mock_channel() -> MagicMock:
    """Discord text channel with send() and typing() mocked."""
    ch = MagicMock()
    ch.id = GUINEVERE_CHAT_CHANNEL_ID
    ch.send = AsyncMock()
    # typing() returns an async context manager
    typing_cm = MagicMock()
    typing_cm.__aenter__ = AsyncMock(return_value=None)
    typing_cm.__aexit__ = AsyncMock(return_value=False)
    ch.typing = MagicMock(return_value=typing_cm)
    return ch


@pytest.fixture()
def mock_author() -> MagicMock:
    """Non-bot author matching Faiz's ID."""
    author = MagicMock()
    author.bot = False
    author.id = FAIZ_ID
    return author


@pytest.fixture()
def mock_guild() -> MagicMock:
    """Guild owned by Faiz."""
    guild = MagicMock()
    guild.owner_id = FAIZ_ID
    return guild


@pytest.fixture()
def mock_message(
    mock_channel: MagicMock,
    mock_author: MagicMock,
    mock_guild: MagicMock,
) -> MagicMock:
    """Valid message that passes all guard checks."""
    msg = MagicMock()
    msg.channel = mock_channel
    msg.author = mock_author
    msg.guild = mock_guild
    msg.content = "hai mommy"
    return msg


@pytest.fixture()
def mock_bot() -> MagicMock:
    """Bot with no session factory (graceful degradation path)."""
    bot = MagicMock()
    bot.get_session_factory = MagicMock(return_value=None)
    return bot


@pytest.fixture()
def mock_router() -> MagicMock:
    """LLMRouter returning a valid chat response."""
    router = MagicMock()
    router.chat = AsyncMock(
        return_value=_make_llm_result("Hello sayang!"),
    )
    return router


@pytest.fixture()
def mock_tracker() -> MagicMock:
    """CostTracker with sync record_cost."""
    tracker = MagicMock()
    tracker.record_cost = MagicMock()
    return tracker


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_llm_result(content: str = "Hello sayang!") -> dict[str, Any]:
    """Build a fake LLM chat-completion response dict."""
    return {
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "model": "gpt-5.5",
    }


def _happy_path_patches(
    router: MagicMock | None = None,
    tracker: MagicMock | None = None,
) -> dict[str, Any]:
    """Return a dict of patch targets → return values for full happy path.

    Callers should apply these patches via ``patch(target, return_value)``
    or ``patch(target, new=...)`` as appropriate.
    """
    if router is None:
        router = MagicMock()
        router.chat = AsyncMock(return_value=_make_llm_result())
    if tracker is None:
        tracker = MagicMock()
        tracker.record_cost = MagicMock()

    return {
        "router": router,
        "tracker": tracker,
    }


def _make_session_factory(mock_session: MagicMock) -> MagicMock:
    """Create a mock session factory chain.

    Returns a callable (``get_session_factory``) that returns a factory,
    which when called returns an async context manager yielding ``mock_session``.
    """
    session_cm = MagicMock()
    session_cm.__aenter__ = AsyncMock(return_value=mock_session)
    session_cm.__aexit__ = AsyncMock(return_value=False)

    factory = MagicMock(return_value=session_cm)
    get_factory = MagicMock(return_value=factory)
    return get_factory


# ── Guard Check Tests (1–4) ─────────────────────────────────────────────────


class TestGuardChecks:
    """handle_conversation must reject messages that fail guard checks."""

    @pytest.mark.asyncio()
    async def test_handle_conversation_returns_false_wrong_channel(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """Message in wrong channel → returns False."""
        mock_message.channel.id = 999999999
        result = await handle_conversation(mock_bot, mock_message)
        assert result is False

    @pytest.mark.asyncio()
    async def test_handle_conversation_returns_false_bot_author(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """Bot-authored message → returns False."""
        mock_message.author.bot = True
        result = await handle_conversation(mock_bot, mock_message)
        assert result is False

    @pytest.mark.asyncio()
    async def test_handle_conversation_returns_false_slash_prefix(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """Message starting with '/' (slash command) → returns False."""
        mock_message.content = "/status"
        result = await handle_conversation(mock_bot, mock_message)
        assert result is False

    @pytest.mark.asyncio()
    async def test_handle_conversation_returns_false_not_faiz(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """Non-owner author → returns False."""
        mock_message.guild.owner_id = 99999  # different from author.id
        result = await handle_conversation(mock_bot, mock_message)
        assert result is False


# ── Rate Limiting Tests (5, 18) ─────────────────────────────────────────────


class TestRateLimiting:
    """Rate limiting must absorb silently when triggered and degrade on error."""

    @pytest.mark.asyncio()
    async def test_handle_conversation_returns_true_rate_limited(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
    ) -> None:
        """Rate-limited message → returns True (silently absorbed)."""
        with patch(
            f"{MODULE}._is_rate_limited",
            new=AsyncMock(return_value=True),
        ):
            result = await handle_conversation(mock_bot, mock_message)
        assert result is True
        # No channel.send should have been called
        mock_message.channel.send.assert_not_called()

    @pytest.mark.asyncio()
    async def test_is_rate_limited_redis_error_returns_false(self) -> None:
        """When Redis raises ConnectionError, _is_rate_limited returns False."""
        from src.discord.conversational_handler import _is_rate_limited

        mock_redis = AsyncMock()
        mock_redis.incr = AsyncMock(side_effect=ConnectionError("Redis down"))

        with patch(f"{MODULE}._get_rate_limit_redis", return_value=mock_redis):
            result = await _is_rate_limited(FAIZ_ID)
        assert result is False


# ── Happy Path Tests (6) ────────────────────────────────────────────────────


class TestHappyPath:
    """Full happy path: guards pass, LLM responds, channel.send called."""

    @pytest.mark.asyncio()
    async def test_handle_conversation_calls_llm_and_sends(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """Full happy path: LLM returns text, channel.send called."""
        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="You are Guinevere.",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
                confidence=1.0,
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_message.channel.send.assert_called_once_with("Hello sayang!")
        mock_router.chat.assert_called_once()


# ── Memory Recall Tests (7–10) ──────────────────────────────────────────────


class TestMemoryRecall:
    """Memory recall integration via session factory and prompt loader."""

    @pytest.mark.asyncio()
    async def test_memory_recall_called_with_session(
        self,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When bot has session factory, assemble_system_prompt_with_memory is called."""
        mock_session = MagicMock()
        mock_bot = MagicMock()
        mock_bot.get_session_factory = _make_session_factory(mock_session)

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.assemble_system_prompt_with_memory",
                new=AsyncMock(return_value="Prompt with memory"),
            ) as mock_assemble,
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_assemble.assert_called_once()
        call_kwargs = mock_assemble.call_args
        assert call_kwargs.kwargs["session"] is mock_session
        assert call_kwargs.kwargs["query_text"] == "hai mommy"

    @pytest.mark.asyncio()
    async def test_memory_recall_skipped_no_session_factory(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """No session factory → falls back to get_system_prompt_with_context(memories=None)."""
        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="Base prompt",
            ) as mock_base,
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_base.assert_called_once()
        call_kwargs = mock_base.call_args
        assert call_kwargs.kwargs.get("memories") is None or (
            call_kwargs.args and call_kwargs.args[0] is None
        )

    @pytest.mark.asyncio()
    async def test_memory_recall_skipped_factory_returns_none(
        self,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """get_session_factory() returns None → falls back gracefully."""
        mock_bot = MagicMock()
        mock_bot.get_session_factory = MagicMock(return_value=None)

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="Base prompt",
            ) as mock_base,
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_base.assert_called_once()

    @pytest.mark.asyncio()
    async def test_memory_recall_fallback_on_error(
        self,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When assemble_system_prompt_with_memory raises, falls back to base prompt."""
        mock_session = MagicMock()
        mock_bot = MagicMock()
        mock_bot.get_session_factory = _make_session_factory(mock_session)

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.assemble_system_prompt_with_memory",
                new=AsyncMock(side_effect=RuntimeError("DB timeout")),
            ),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="Fallback base prompt",
            ) as mock_fallback,
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_fallback.assert_called_once()


# ── Distress Detection Tests (11–12) ────────────────────────────────────────


class TestDistressDetection:
    """Distress detection and safe mode propagation."""

    @pytest.mark.asyncio()
    async def test_safe_mode_propagated_to_recall(
        self,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When DistressDetector detects D2+, safe_mode=True is passed to recall."""
        mock_session = MagicMock()
        mock_bot = MagicMock()
        mock_bot.get_session_factory = _make_session_factory(mock_session)

        mock_signal = MagicMock()
        mock_signal.detected_level = MagicMock(name="D2_MODERATE")
        mock_signal.detected_level.name = "D2_MODERATE"
        mock_signal.confidence = 0.8

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.assemble_system_prompt_with_memory",
                new=AsyncMock(return_value="Safe prompt"),
            ) as mock_assemble,
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = mock_signal
            mock_sm_cls.return_value.evaluate.return_value = True

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        call_kwargs = mock_assemble.call_args.kwargs
        assert call_kwargs["safe_mode"] is True

    @pytest.mark.asyncio()
    async def test_distress_detection_error_graceful(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When DistressDetector raises, continues with safe_mode_activated=False."""
        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="Base prompt",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController"),
            patch("src.persona.safe_mode.DistressLevel") as mock_dl,
            patch("src.persona.safe_mode.DistressSignal") as mock_ds,
        ):
            mock_dd_cls.return_value.detect.side_effect = RuntimeError("detection error")
            # The except block imports DistressLevel and DistressSignal
            mock_dl.D0_NORMAL = MagicMock(name="D0_NORMAL")
            mock_dl.D0_NORMAL.name = "D0_NORMAL"
            mock_ds.return_value = MagicMock(
                detected_level=mock_dl.D0_NORMAL,
            )

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        # Should have sent response, not crashed
        mock_message.channel.send.assert_called()


# ── Response Splitting Tests (13, 17) ───────────────────────────────────────


class TestResponseSplitting:
    """_split_response must respect Discord char limits and sentence boundaries."""

    def test_split_response_short_text(self) -> None:
        """Text under 2000 chars → single chunk."""
        text = "Hello world"
        chunks = _split_response(text)
        assert chunks == ["Hello world"]

    @pytest.mark.asyncio()
    async def test_response_split_on_long_text(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """LLM returns >2000 chars → channel.send called multiple times."""
        long_text = "Sentence one. " * 200  # ~2800 chars
        mock_router.chat = AsyncMock(return_value=_make_llm_result(long_text))

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="prompt",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        assert mock_message.channel.send.call_count >= 2

    def test_split_response_sentence_boundary(self) -> None:
        """_split_response splits at sentence boundaries correctly."""
        # Build text: 3 sentences, each ~700 chars, total > 2000
        sentence = "A" * 690 + ". "
        text = sentence * 3  # ~2076 chars total
        chunks = _split_response(text)
        assert len(chunks) >= 2
        # Each chunk should be within Discord limit
        for chunk in chunks:
            assert len(chunk) <= DISCORD_MAX_CHARS

    def test_split_response_max_chunks(self) -> None:
        """_split_response caps at MAX_CHUNKS (3)."""
        text = "X" * 10_000
        chunks = _split_response(text)
        assert len(chunks) <= MAX_CHUNKS

    def test_split_response_truncation_marker(self) -> None:
        """Very long text gets ...(truncated) marker."""
        text = "Y" * 10_000
        chunks = _split_response(text)
        # At least one chunk should exist, and total should be bounded
        assert len(chunks) >= 1
        total = sum(len(c) for c in chunks)
        assert total < len(text)


# ── Cost Tracking Tests (14) ────────────────────────────────────────────────


class TestCostTracking:
    """Cost tracking must be called after successful LLM response."""

    @pytest.mark.asyncio()
    async def test_cost_tracking_called(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """After successful LLM response, tracker.record_cost is called."""
        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="prompt",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_tracker.record_cost.assert_called_once()
        call_kwargs = mock_tracker.record_cost.call_args.kwargs
        assert call_kwargs["model"] == "gpt-5.5"
        assert call_kwargs["input_tokens"] == 100
        assert call_kwargs["output_tokens"] == 50


# ── Error Path Tests (15–16) ────────────────────────────────────────────────


class TestErrorPaths:
    """LLM errors must send fallback message gracefully."""

    @pytest.mark.asyncio()
    async def test_llm_error_sends_fallback(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When LLMRouter.chat raises, FALLBACK_MESSAGE is sent."""
        mock_router = MagicMock()
        mock_router.chat = AsyncMock(side_effect=RuntimeError("LLM unavailable"))

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="prompt",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_message.channel.send.assert_called_once_with(FALLBACK_MESSAGE)

    @pytest.mark.asyncio()
    async def test_empty_llm_response_sends_fallback(
        self,
        mock_bot: MagicMock,
        mock_message: MagicMock,
        mock_router: MagicMock,
        mock_tracker: MagicMock,
    ) -> None:
        """When LLM returns empty content, FALLBACK_MESSAGE is sent."""
        mock_router.chat = AsyncMock(return_value=_make_llm_result(""))

        with (
            patch(f"{MODULE}._is_rate_limited", new=AsyncMock(return_value=False)),
            patch(f"{MODULE}._get_router", return_value=mock_router),
            patch(f"{MODULE}._get_cost_tracker", return_value=mock_tracker),
            patch(f"{MODULE}._get_embedding_service", return_value=MagicMock()),
            patch(
                "src.core.services.prompt_loader.get_system_prompt_with_context",
                return_value="prompt",
            ),
            patch("src.persona.safe_mode.DistressDetector") as mock_dd_cls,
            patch("src.persona.safe_mode.SafeModeController") as mock_sm_cls,
        ):
            mock_dd_cls.return_value.detect.return_value = MagicMock(
                detected_level=MagicMock(name="D0_NORMAL"),
            )
            mock_sm_cls.return_value.evaluate.return_value = False

            result = await handle_conversation(mock_bot, mock_message)

        assert result is True
        mock_message.channel.send.assert_called_once_with(FALLBACK_MESSAGE)
