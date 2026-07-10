"""B5 Loop-Driven Discord Behavior — test suite.

Verifies the ThoughtStream → ActionExecutor → Discord pipeline:
  - AffectVector → tone directive (compute_affect_tone)
  - High-confidence COGNITION/PLANNING thought → Discord message
  - Low-confidence or non-actionable thought → NOT sent
  - discord_send_callback resolves channel via ChannelConfig
  - set_action_executor / set_bot_reference store references
  - handle_conversation signature accepts action_executor

All Discord sends are mocked — no real Discord API calls.
"""

from __future__ import annotations

import asyncio
import inspect
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from guinevere.consciousness.thought import Thought, ThoughtType
from guinevere.discord.hermes_conversational import (
    compute_affect_tone,
    create_discord_send_callback,
    handle_conversation,
    process_thought_for_discord,
    set_action_executor,
    set_bot_reference,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_affect(
    valence: float = 0.5,
    arousal: float = 0.5,
    dominance: float = 0.5,
    curiosity: float = 0.5,
    confidence: float = 0.5,
    serenity: float = 0.5,
) -> MagicMock:
    """Create a mock AffectVector with the given dimension values."""
    affect = MagicMock()
    affect.valence = valence
    affect.arousal = arousal
    affect.dominance = dominance
    affect.curiosity = curiosity
    affect.confidence = confidence
    affect.serenity = serenity
    affect.as_dict.return_value = {
        "valence": valence,
        "arousal": arousal,
        "dominance": dominance,
        "curiosity": curiosity,
        "confidence": confidence,
        "serenity": serenity,
    }
    return affect


def _make_thought(
    thought_type: ThoughtType = ThoughtType.COGNITION,
    content: str = "I am thinking about helping Faiz",
    confidence: float = 0.85,
) -> Thought:
    """Create a Thought with the given parameters."""
    return Thought(
        type=thought_type,
        content=content,
        confidence=confidence,
    )


# ---------------------------------------------------------------------------
# TestAffectTone — compute_affect_tone
# ---------------------------------------------------------------------------


class TestAffectTone:
    """compute_affect_tone must map AffectVector to tone directives."""

    def test_high_valence_warm_positive(self) -> None:
        """High valence (>0.6) → 'warm and positive' in tone."""
        affect = _make_affect(valence=0.8)
        tone = compute_affect_tone(affect)
        assert "warm and positive" in tone

    def test_low_valence_empathetic(self) -> None:
        """Low valence (<0.4) → 'gentle and empathetic' in tone."""
        affect = _make_affect(valence=0.2)
        tone = compute_affect_tone(affect)
        assert "gentle and empathetic" in tone

    def test_high_arousal_energetic(self) -> None:
        """High arousal (>0.7) → 'energetic' in tone."""
        affect = _make_affect(arousal=0.9)
        tone = compute_affect_tone(affect)
        assert "energetic" in tone

    def test_low_arousal_calm(self) -> None:
        """Low arousal (<0.3) → 'calm and measured' in tone."""
        affect = _make_affect(arousal=0.1)
        tone = compute_affect_tone(affect)
        assert "calm and measured" in tone

    def test_high_curiosity_exploratory(self) -> None:
        """High curiosity (>0.7) → 'curious and exploratory'."""
        affect = _make_affect(curiosity=0.9)
        tone = compute_affect_tone(affect)
        assert "curious and exploratory" in tone

    def test_neutral_affect_empty_tone(self) -> None:
        """All-neutral affect (0.5) → empty string (no directive)."""
        affect = _make_affect()
        tone = compute_affect_tone(affect)
        assert tone == ""

    def test_none_affect_returns_empty(self) -> None:
        """None affect → empty string."""
        tone = compute_affect_tone(None)
        assert tone == ""

    def test_multiple_dimensions_combined(self) -> None:
        """Multiple extreme dimensions → all appear in tone."""
        affect = _make_affect(valence=0.9, arousal=0.8, curiosity=0.9)
        tone = compute_affect_tone(affect)
        assert "warm and positive" in tone
        assert "energetic" in tone
        assert "curious and exploratory" in tone
        assert tone.startswith("Tone: ")
        assert tone.endswith(".")

    def test_high_serenity_composed(self) -> None:
        """High serenity (>0.7) → 'serene and composed'."""
        affect = _make_affect(serenity=0.9)
        tone = compute_affect_tone(affect)
        assert "serene and composed" in tone

    def test_high_confidence_assertive(self) -> None:
        """High confidence (>0.7) → 'confident'."""
        affect = _make_affect(confidence=0.9)
        tone = compute_affect_tone(affect)
        assert "confident" in tone

    def test_low_confidence_tentative(self) -> None:
        """Low confidence (<0.3) → 'humble and tentative'."""
        affect = _make_affect(confidence=0.1)
        tone = compute_affect_tone(affect)
        assert "humble and tentative" in tone


# ---------------------------------------------------------------------------
# TestProcessThoughtForDiscord — process_thought_for_discord
# ---------------------------------------------------------------------------


class TestProcessThoughtForDiscord:
    """process_thought_for_discord must evaluate and route thoughts."""

    @pytest.mark.asyncio
    async def test_no_executor_returns_false(self) -> None:
        """Without an executor, returns False."""
        # Reset module state.
        import guinevere.discord.hermes_conversational as mod

        old = mod._action_executor
        mod._action_executor = None
        try:
            thought = _make_thought(confidence=0.9)
            result = await process_thought_for_discord(thought)
            assert result is False
        finally:
            mod._action_executor = old

    @pytest.mark.asyncio
    async def test_high_confidence_cognition_sends_to_discord(self) -> None:
        """COGNITION thought with confidence > 0.8 → sent to Discord."""
        from guinevere.consciousness.action_executor import ActionExecutor

        mock_send = AsyncMock(return_value=True)
        executor = ActionExecutor(
            llm_router=MagicMock(),
            config={"confidence_threshold": 0.8},
        )
        executor._discord_send_callback = mock_send

        thought = _make_thought(
            thought_type=ThoughtType.COGNITION,
            content="send message to Faiz about the deployment",
            confidence=0.92,
        )

        result = await process_thought_for_discord(
            thought, action_executor=executor,
        )

        assert result is True
        mock_send.assert_called_once()
        call_args = mock_send.call_args
        assert call_args[0][0] == "general"  # target channel from payload
        assert "deployment" in call_args[0][1]  # content

    @pytest.mark.asyncio
    async def test_high_confidence_planning_sends_to_discord(self) -> None:
        """PLANNING thought with confidence > 0.8 → sent to Discord."""
        from guinevere.consciousness.action_executor import ActionExecutor

        mock_send = AsyncMock(return_value=True)
        executor = ActionExecutor(
            llm_router=MagicMock(),
            config={"confidence_threshold": 0.8},
        )
        executor._discord_send_callback = mock_send

        thought = _make_thought(
            thought_type=ThoughtType.PLANNING,
            content="notify Faiz about the new feature plan",
            confidence=0.85,
        )

        result = await process_thought_for_discord(
            thought, action_executor=executor,
        )

        assert result is True
        mock_send.assert_called_once()

    @pytest.mark.asyncio
    async def test_low_confidence_not_sent(self) -> None:
        """Thought with confidence <= 0.8 → NOT sent."""
        from guinevere.consciousness.action_executor import ActionExecutor

        mock_send = AsyncMock(return_value=True)
        executor = ActionExecutor(
            llm_router=MagicMock(),
            config={"confidence_threshold": 0.8},
        )
        executor._discord_send_callback = mock_send

        thought = _make_thought(
            thought_type=ThoughtType.COGNITION,
            content="send message to Faiz",
            confidence=0.7,  # Below threshold
        )

        result = await process_thought_for_discord(
            thought, action_executor=executor,
        )

        assert result is False
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_dreaming_type_not_sent(self) -> None:
        """DREAMING type is not actionable → NOT sent even at high confidence."""
        from guinevere.consciousness.action_executor import ActionExecutor

        mock_send = AsyncMock(return_value=True)
        executor = ActionExecutor(
            llm_router=MagicMock(),
            config={"confidence_threshold": 0.8},
        )
        executor._discord_send_callback = mock_send

        thought = _make_thought(
            thought_type=ThoughtType.DREAMING,
            content="what if the deployment had failed",
            confidence=0.95,
        )

        result = await process_thought_for_discord(
            thought, action_executor=executor,
        )

        assert result is False
        mock_send.assert_not_called()

    @pytest.mark.asyncio
    async def test_heartbeat_type_not_sent(self) -> None:
        """HEARTBEAT type is not actionable → NOT sent."""
        from guinevere.consciousness.action_executor import ActionExecutor

        mock_send = AsyncMock(return_value=True)
        executor = ActionExecutor(
            llm_router=MagicMock(),
            config={"confidence_threshold": 0.8},
        )
        executor._discord_send_callback = mock_send

        thought = _make_thought(
            thought_type=ThoughtType.HEARTBEAT,
            content="system alive",
            confidence=0.9,
        )

        result = await process_thought_for_discord(
            thought, action_executor=executor,
        )

        assert result is False
        mock_send.assert_not_called()


# ---------------------------------------------------------------------------
# TestDiscordSendCallback — create_discord_send_callback
# ---------------------------------------------------------------------------


class TestDiscordSendCallback:
    """create_discord_send_callback must resolve channels and send."""

    def test_returns_callable(self) -> None:
        """create_discord_send_callback returns an async callable."""
        callback = create_discord_send_callback(MagicMock())
        assert callable(callback)
        assert inspect.iscoroutinefunction(callback)

    @pytest.mark.asyncio
    async def test_sends_to_correct_channel(self) -> None:
        """Callback resolves channel via ChannelConfig and sends."""
        mock_channel = AsyncMock()
        mock_channel.id = 111111111111111111
        mock_channel.send = AsyncMock()

        mock_guild = MagicMock()
        mock_guild.get_channel.return_value = mock_channel

        mock_bot = MagicMock()
        mock_bot.guilds = [mock_guild]

        mock_config = MagicMock()
        mock_config.general = 111111111111111111
        mock_bot.channel_config = mock_config

        callback = create_discord_send_callback(mock_bot)
        result = await callback("general", "Hello from consciousness!")

        assert result is True
        mock_channel.send.assert_called_once_with("Hello from consciousness!")

    @pytest.mark.asyncio
    async def test_returns_false_no_bot(self) -> None:
        """Callback returns False when no bot reference."""
        import guinevere.discord.hermes_conversational as mod

        old_bot = mod._bot_ref
        mod._bot_ref = None
        try:
            callback = create_discord_send_callback(None)
            result = await callback("general", "test")
            assert result is False
        finally:
            mod._bot_ref = old_bot

    @pytest.mark.asyncio
    async def test_returns_false_channel_not_found(self) -> None:
        """Callback returns False when guild.get_channel returns None."""
        mock_guild = MagicMock()
        mock_guild.get_channel.return_value = None

        mock_bot = MagicMock()
        mock_bot.guilds = [mock_guild]

        mock_config = MagicMock()
        mock_config.general = 111111111111111111
        mock_bot.channel_config = mock_config

        callback = create_discord_send_callback(mock_bot)
        result = await callback("general", "test message")

        assert result is False


# ---------------------------------------------------------------------------
# TestSetReferences — set_action_executor / set_bot_reference
# ---------------------------------------------------------------------------


class TestSetReferences:
    """Module-level reference setters must store values."""

    def test_set_action_executor(self) -> None:
        """set_action_executor stores the executor reference."""
        import guinevere.discord.hermes_conversational as mod

        old = mod._action_executor
        mock_exec = MagicMock()
        try:
            set_action_executor(mock_exec)
            assert mod._action_executor is mock_exec
        finally:
            mod._action_executor = old

    def test_set_bot_reference(self) -> None:
        """set_bot_reference stores the bot reference."""
        import guinevere.discord.hermes_conversational as mod

        old = mod._bot_ref
        mock_bot = MagicMock()
        try:
            set_bot_reference(mock_bot)
            assert mod._bot_ref is mock_bot
        finally:
            mod._bot_ref = old


# ---------------------------------------------------------------------------
# TestHandleConversationSignature — B5 param acceptance
# ---------------------------------------------------------------------------


class TestHandleConversationSignature:
    """handle_conversation must accept action_executor parameter."""

    def test_accepts_action_executor_param(self) -> None:
        """handle_conversation signature includes action_executor."""
        sig = inspect.signature(handle_conversation)
        params = list(sig.parameters.keys())
        assert "action_executor" in params

    def test_action_executor_defaults_to_none(self) -> None:
        """action_executor parameter defaults to None."""
        sig = inspect.signature(handle_conversation)
        param = sig.parameters["action_executor"]
        assert param.default is None
