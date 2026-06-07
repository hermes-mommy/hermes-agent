"""P3-012: Context injection — unit tests for prompt_loader.py.

Tests cover:
- get_system_prompt_with_context: dict results, safe_content only,
  empty safe_content skipped, token budget truncation, default token budget 4000,
  metadata-only logging (no raw content in logs).
- assemble_system_prompt_with_memory: recall integration, exclude_dnr=True,
  safe_mode propagation, hard_stop_handler.is_safe override, principal/limit/token_budget
  pass-through, empty recall returns prompt without memories, ReadPipelineSafetyError
  returns prompt without memories (discardable).
"""
from __future__ import annotations

from unittest.mock import AsyncMock, patch

from src.core.services.prompt_loader import (
    assemble_system_prompt_with_memory,
    get_system_prompt_with_context,
)
from src.memory.read_pipeline import (
    ReadPipelineSafetyError,
    RecallSession,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _fake_system_prompt() -> str:
    return "BASE_SYSTEM_PROMPT_WITH_SAFETY_ELEMENTS_HARD_STOP_SAFE_WORD_Y5_DISTRESS"


def _make_memory(safe_content: str, **extra: object) -> dict[str, object]:
    data: dict[str, object] = {"safe_content": safe_content}
    data.update(extra)
    return data


class _FakeHandler:
    """Typed fake for HardStopHandler — avoids broad MagicMock in type checking."""

    def __init__(self, is_safe: bool = False) -> None:
        self.is_safe: bool = is_safe


# ---------------------------------------------------------------------------
# get_system_prompt_with_context tests
# ---------------------------------------------------------------------------

class TestGetSystemPromptWithContext:
    """Unit tests for the prompt context assembler."""

    def test_none_memories_returns_base_and_mood(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(None, mood="Content")
        assert "BASE_SYSTEM_PROMPT" in prompt
        assert "## Current Mood: Content" in prompt
        assert "## Recalled Memories" not in prompt

    def test_empty_list_returns_base_and_mood(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context([], mood="Content")
        assert "## Recalled Memories" not in prompt
        assert "## Current Mood: Content" in prompt

    def test_string_memories_backward_compat(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                ["memory one", "memory two"], mood="Content"
            )
        assert "- (Restricted) memory one" in prompt
        assert "- (Restricted) memory two" in prompt

    def test_dict_memories_formatted_with_safe_content(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                [
                    _make_memory("alpha"),
                    _make_memory("beta"),
                    _make_memory("gamma"),
                ],
                mood="Content",
            )
        assert "- (Restricted) alpha" in prompt
        assert "- (Restricted) beta" in prompt
        assert "- (Restricted) gamma" in prompt

    def test_empty_safe_content_skipped(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                [
                    _make_memory("keep"),
                    _make_memory(""),
                    _make_memory("also keep"),
                ],
                mood="Content",
                token_budget=4000,
            )
        assert "- (Restricted) keep" in prompt
        assert "- (Restricted) also keep" in prompt
        # Empty entry should not appear
        assert "- (Restricted) " not in prompt.replace("- (Restricted) keep", "").replace("- (Restricted) also keep", "")

    def test_raw_content_never_injected(self) -> None:
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                [
                    _make_memory("safe", raw_content="SECRET_RAW"),
                    _make_memory("safe2", raw_content="MORE_SECRET"),
                ],
                mood="Content",
            )
        assert "SECRET_RAW" not in prompt
        assert "MORE_SECRET" not in prompt
        assert "safe" in prompt
        assert "safe2" in prompt

    def test_token_budget_truncates_memories(self) -> None:
        # Each memory is 100 chars -> 25 tokens at CHARS_PER_TOKEN=4.
        # Budget 100 tokens allows 4 memories; 5th should be dropped.
        memories = [_make_memory("x" * 100) for _ in range(5)]
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                memories, mood="Content", token_budget=100
            )
        assert "- (Restricted) " in prompt
        assert prompt.count("- (Restricted) ") == 3

    def test_token_budget_zero_drops_all_memories(self) -> None:
        memories = [_make_memory("alpha"), _make_memory("beta")]
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context(
                memories, mood="Content", token_budget=0
            )
        assert "[RECENT MEMORIES]" in prompt
        assert "alpha" not in prompt
        assert "beta" not in prompt

    def test_default_token_budget_is_4000(self) -> None:
        memories = [_make_memory("x" * 100) for _ in range(5)]
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            # Should not raise; default budget should accommodate small memories
            prompt = get_system_prompt_with_context(memories, mood="Content")
        assert prompt.count("- (Restricted) ") == 5

    def test_logger_called_with_metadata_only(self) -> None:
        memories = [_make_memory("alpha")]
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            with patch(
                "src.core.services.prompt_loader.logger.info",
            ) as mock_info:
                _ = get_system_prompt_with_context(memories, mood="Content")
        assert mock_info.called
        for call in mock_info.call_args_list:
            args, kwargs = call
            for arg in args:
                assert "alpha" not in str(arg)
            extra = kwargs.get("extra")
            if isinstance(extra, dict):
                for value in extra.values():
                    if isinstance(value, str):
                        assert "alpha" not in value


# ---------------------------------------------------------------------------
# assemble_system_prompt_with_memory tests
# ---------------------------------------------------------------------------

class TestAssembleSystemPromptWithMemory:
    """Unit tests for the memory-aware prompt assembler."""

    def test_recall_called_with_exclude_dnr_true(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False
                ))
            mock_recall.assert_called_once()
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["exclude_dnr"] is True

    def test_safe_mode_propagated_true(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=True
                ))
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["safe_mode"] is True

    def test_hard_stop_handler_overrides_safe_mode(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        handler = _FakeHandler(is_safe=True)
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False, hard_stop_handler=handler
                ))
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["safe_mode"] is True

    def test_hard_stop_handler_false_overrides_passed_safe_mode(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        handler = _FakeHandler(is_safe=False)
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=True, hard_stop_handler=handler
                ))
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["safe_mode"] is False

    def test_principal_limit_token_budget_passed_through(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session,
                    "query",
                    principal="guinevere_subagent",
                    limit=7,
                    token_budget=2000,
                ))
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["principal"] == "guinevere_subagent"
            assert kwargs["limit"] == 7
            assert kwargs["token_budget"] == 2000

    def test_empty_recall_returns_prompt_without_memories(self) -> None:
        session = AsyncMock(spec=RecallSession)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            new_callable=AsyncMock,
            return_value=[],
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                prompt = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", mood="Content"
                ))
        assert "## Recalled Memories" not in prompt
        assert "## Current Mood: Content" in prompt

    def test_recall_safety_error_returns_prompt_without_memories(self) -> None:
        session = AsyncMock(spec=RecallSession)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            new_callable=AsyncMock,
            side_effect=ReadPipelineSafetyError("blocked"),
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                with patch(
                    "src.core.services.prompt_loader.logger.info",
                ) as mock_info:
                    import asyncio
                    prompt = asyncio.run(assemble_system_prompt_with_memory(
                        session, "query"
                    ))
        assert "## Recalled Memories" not in prompt
        assert "## Current Mood: Content" in prompt
        # Metadata-only log emitted for blocked recall
        assert mock_info.called
        call_args = mock_info.call_args_list[0]
        kwargs = call_args.kwargs
        extra = kwargs.get("extra", {})
        # Log should not contain raw query text or memory content
        assert "query" not in str(extra).lower()

    def test_default_limit_is_3(self) -> None:
        session = AsyncMock(spec=RecallSession)
        fake_results = [_make_memory("m1")]
        mock_recall = AsyncMock(return_value=fake_results)
        with patch(
            "src.core.services.prompt_loader.recall_memories",
            mock_recall,
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                import asyncio
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query"
                ))
            kwargs = mock_recall.call_args.kwargs
            assert kwargs["limit"] == 3
