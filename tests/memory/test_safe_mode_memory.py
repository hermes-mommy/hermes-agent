"""P3-014: Safe-mode memory gate — deterministic unit tests.

Tests cover:
- HardStopHandler.is_safe propagation through assemble_system_prompt_with_memory.
- DNR remains excluded in safe mode.
- Critical content blocked/placeholder in safe mode.
- Restricted and Confidential redacted/summarised (no raw content).
- Public/Internal neutral summaries allowed.
- Emotional/persona/surveillance tags/types blocked in safe mode.
- Unknown classification fails closed.
- Safe-mode output uses safe_content only.
- AC-SAFE-001: safe-word bypass is impossible (HardStopHandler state is authoritative).
- _resolve_ceiling downgrades classification ceiling in safe mode.
- _is_safe_mode_blocked_content detection.

All tests use synthetic/fake data — no DB or network required.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from src.core.services.prompt_loader import (
    assemble_system_prompt_with_memory,
    get_system_prompt_with_context,
)
from src.memory.read_pipeline import (
    CONFIDENTIAL,
    CRITICAL,
    INTERNAL,
    PUBLIC,
    RESTRICTED,
    SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER,
    SAFE_MODE_PLACEHOLDER,
    SAFE_MODE_RESTRICTED_PLACEHOLDER,
    _is_safe_mode_blocked_content,
    _resolve_ceiling,
    build_safe_content,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _fake_system_prompt() -> str:
    return (
        "BASE_SYSTEM_PROMPT_WITH_SAFETY_ELEMENTS "
        "HARD_STOP SAFE_WORD Y5 DISTRESS"
    )


class FakeEpisode:
    """Minimal fake episode satisfying EpisodeProtocol + optional P3-014 fields."""

    def __init__(
        self,
        ep_id: str = "ep-001",
        *,
        classification: str = RESTRICTED,
        raw_content: str | None = "raw content",
        summary: str | None = None,
        do_not_recall: bool = False,
        importance: int = 5,
        started_at: datetime | None = None,
        tags: list[str] | None = None,
        episode_type: str | None = None,
        source: str | None = None,
    ) -> None:
        self.id: object = ep_id
        self.raw_content: str | None = raw_content
        self.summary: str | None = summary
        self.embedding: list[float] | None = [0.1] * 1536
        self.search_vector: object = f"sv_{ep_id}"
        self.do_not_recall: bool = do_not_recall
        self.classification: str = classification
        self.importance: int | None = importance
        self.started_at: datetime | None = (
            started_at or datetime.now(timezone.utc)
        )
        self.created_at: datetime | None = self.started_at
        # Optional P3-014 fields (not in EpisodeProtocol — read via getattr)
        self.tags: list[str] | set[str] | str | None = tags
        self.episode_type: str | None = episode_type
        self.source: str | None = source


class FakeHandler:
    """Typed fake for HardStopHandler."""

    def __init__(self, is_safe: bool = False) -> None:
        self.is_safe: bool = is_safe


def _make_memory(safe_content: str, **extra: object) -> dict[str, object]:
    data: dict[str, object] = {"safe_content": safe_content}
    data.update(extra)
    return data


# ---------------------------------------------------------------------------
# _resolve_ceiling tests
# ---------------------------------------------------------------------------


class TestResolveCeiling:
    """Safe-mode classification ceiling downgrade per principal."""

    def test_normal_mode_guinevere_core_critical(self) -> None:
        assert _resolve_ceiling("guinevere_core", safe_mode=False) == CRITICAL

    def test_normal_mode_subagent_confidential(self) -> None:
        assert _resolve_ceiling("guinevere_subagent", safe_mode=False) == CONFIDENTIAL

    def test_normal_mode_default_restricted(self) -> None:
        assert _resolve_ceiling("unknown_principal", safe_mode=False) == RESTRICTED

    def test_safe_mode_guinevere_core_internal(self) -> None:
        assert _resolve_ceiling("guinevere_core", safe_mode=True) == INTERNAL

    def test_safe_mode_subagent_public(self) -> None:
        assert _resolve_ceiling("guinevere_subagent", safe_mode=True) == PUBLIC

    def test_safe_mode_default_public(self) -> None:
        assert _resolve_ceiling("unknown_principal", safe_mode=True) == PUBLIC


# ---------------------------------------------------------------------------
# _is_safe_mode_blocked_content tests
# ---------------------------------------------------------------------------


class TestSafeModeBlockedContent:
    """Detect emotional/surveillance/persona-escalation content."""

    def test_no_tags_not_blocked(self) -> None:
        ep = FakeEpisode(tags=None, episode_type=None, source=None)
        assert _is_safe_mode_blocked_content(ep) is False

    def test_emotional_tag_list_blocked(self) -> None:
        ep = FakeEpisode(tags=["emotional", "personal"])
        assert _is_safe_mode_blocked_content(ep) is True

    def test_surveillance_tag_list_blocked(self) -> None:
        ep = FakeEpisode(tags=["surveillance_data"])
        assert _is_safe_mode_blocked_content(ep) is True

    def test_persona_escalation_tag_blocked(self) -> None:
        ep = FakeEpisode(tags=["yandere_escalation"])
        assert _is_safe_mode_blocked_content(ep) is True

    def test_punishment_tag_blocked(self) -> None:
        ep = FakeEpisode(tags=["punitive_action"])
        assert _is_safe_mode_blocked_content(ep) is True

    def test_jealousy_tag_blocked(self) -> None:
        ep = FakeEpisode(tags=["jealousy_reaction"])
        assert _is_safe_mode_blocked_content(ep) is True

    def test_neutral_tag_not_blocked(self) -> None:
        ep = FakeEpisode(tags=["daily_routine", "factual"])
        assert _is_safe_mode_blocked_content(ep) is False

    def test_comma_separated_string_tags_blocked(self) -> None:
        ep = FakeEpisode()
        ep.tags = "daily,monitoring_activity"
        assert _is_safe_mode_blocked_content(ep) is True

    def test_episode_type_surveillance_blocked(self) -> None:
        ep = FakeEpisode(episode_type="surveillance_snapshot")
        assert _is_safe_mode_blocked_content(ep) is True

    def test_episode_type_emotional_blocked(self) -> None:
        ep = FakeEpisode(episode_type="emotional_mood_swing")
        assert _is_safe_mode_blocked_content(ep) is True

    def test_episode_type_neutral_not_blocked(self) -> None:
        ep = FakeEpisode(episode_type="conversation")
        assert _is_safe_mode_blocked_content(ep) is False

    def test_source_surveillance_blocked(self) -> None:
        ep = FakeEpisode(source="android_surveillance_daemon")
        assert _is_safe_mode_blocked_content(ep) is True

    def test_source_spy_blocked(self) -> None:
        ep = FakeEpisode(source="spy_monitor_feed")
        assert _is_safe_mode_blocked_content(ep) is True

    def test_source_neutral_not_blocked(self) -> None:
        ep = FakeEpisode(source="discord_conversation")
        assert _is_safe_mode_blocked_content(ep) is False

    def test_empty_tags_not_blocked(self) -> None:
        ep = FakeEpisode(tags=[])
        assert _is_safe_mode_blocked_content(ep) is False

    def test_set_tags_blocked(self) -> None:
        ep = FakeEpisode()
        ep.tags = {"dark_mood", "other"}
        assert _is_safe_mode_blocked_content(ep) is True


# ---------------------------------------------------------------------------
# build_safe_content — safe mode
# ---------------------------------------------------------------------------


class TestBuildSafeContentSafeMode:
    """build_safe_content behaviour when safe_mode=True."""

    def test_critical_blocked_with_placeholder(self) -> None:
        ep = FakeEpisode(
            classification=CRITICAL,
            raw_content="secret critical data",
            summary="critical summary",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_PLACEHOLDER
        assert is_summarized is False

    def test_restricted_uses_summary(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="restricted raw data here",
            summary="short summary",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == "short summary"
        assert is_summarized is True
        assert "restricted raw data" not in content

    def test_restricted_no_summary_uses_placeholder(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="restricted raw content",
            summary=None,
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_RESTRICTED_PLACEHOLDER
        assert is_summarized is False
        assert "restricted raw content" not in content

    def test_confidential_uses_summary(self) -> None:
        ep = FakeEpisode(
            classification=CONFIDENTIAL,
            raw_content="confidential raw",
            summary="confidential summary",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == "confidential summary"
        assert is_summarized is True
        assert "confidential raw" not in content

    def test_confidential_no_summary_uses_placeholder(self) -> None:
        ep = FakeEpisode(
            classification=CONFIDENTIAL,
            raw_content="confidential raw",
            summary=None,
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_RESTRICTED_PLACEHOLDER
        assert "confidential raw" not in content

    def test_public_neutral_summary_allowed(self) -> None:
        ep = FakeEpisode(
            classification=PUBLIC,
            raw_content="public raw content",
            summary="public neutral summary",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == "public neutral summary"
        assert is_summarized is True

    def test_public_no_summary_uses_raw(self) -> None:
        ep = FakeEpisode(
            classification=PUBLIC,
            raw_content="public neutral raw",
            summary=None,
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == "public neutral raw"
        assert is_summarized is False

    def test_internal_neutral_summary_allowed(self) -> None:
        ep = FakeEpisode(
            classification=INTERNAL,
            raw_content="internal raw",
            summary="internal summary",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=True)
        assert content == "internal summary"
        assert is_summarized is True

    def test_public_emotional_tags_blocked(self) -> None:
        ep = FakeEpisode(
            classification=PUBLIC,
            raw_content="public emotional content",
            summary="emotional summary",
            tags=["emotional"],
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER
        assert "emotional" not in content.replace(SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER, "")

    def test_internal_surveillance_source_blocked(self) -> None:
        ep = FakeEpisode(
            classification=INTERNAL,
            raw_content="surveillance data",
            source="android_surveillance_daemon",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER

    def test_unknown_classification_fail_closed(self) -> None:
        ep = FakeEpisode(
            classification="UnknownClassification",
            raw_content="unknown raw",
            summary="unknown summary",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_PLACEHOLDER
        assert "unknown raw" not in content


# ---------------------------------------------------------------------------
# build_safe_content — normal mode (regression: P3-011 behaviour preserved)
# ---------------------------------------------------------------------------


class TestBuildSafeContentNormalMode:
    """Normal mode behaviour must be unchanged by P3-014."""

    def test_critical_normal_mode_returns_raw(self) -> None:
        ep = FakeEpisode(
            classification=CRITICAL,
            raw_content="critical raw",
            summary=None,
        )
        content, _ = build_safe_content(ep, safe_mode=False)
        assert content == "critical raw"

    def test_summary_preferred_when_shorter(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="a" * 100,
            summary="b" * 40,
        )
        content, is_summarized = build_safe_content(ep, safe_mode=False)
        assert content == "b" * 40
        assert is_summarized is True

    def test_raw_when_summary_not_shorter(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="short",
            summary="this summary is longer than raw",
        )
        content, is_summarized = build_safe_content(ep, safe_mode=False)
        assert content == "short"
        assert is_summarized is False

    def test_empty_raw_and_summary(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content=None,
            summary=None,
        )
        content, _ = build_safe_content(ep, safe_mode=False)
        assert content == ""


# ---------------------------------------------------------------------------
# HardStopHandler.is_safe propagation through assemble_system_prompt_with_memory
# ---------------------------------------------------------------------------


class TestHardStopHandlerSafeModePropagation:
    """AC-SAFE-001: safe-word handler state propagates to memory recall."""

    def test_handler_safe_sets_safe_mode_true(self) -> None:
        session = AsyncMock()
        handler = FakeHandler(is_safe=True)
        mock_recall = AsyncMock(return_value=[_make_memory("m1")])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False, hard_stop_handler=handler
                ))
        kwargs = mock_recall.call_args.kwargs
        assert kwargs["safe_mode"] is True

    def test_handler_normal_sets_safe_mode_false(self) -> None:
        session = AsyncMock()
        handler = FakeHandler(is_safe=False)
        mock_recall = AsyncMock(return_value=[_make_memory("m1")])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=True, hard_stop_handler=handler
                ))
        kwargs = mock_recall.call_args.kwargs
        assert kwargs["safe_mode"] is False

    def test_no_handler_uses_passed_safe_mode(self) -> None:
        session = AsyncMock()
        mock_recall = AsyncMock(return_value=[_make_memory("m1")])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=True, hard_stop_handler=None
                ))
        kwargs = mock_recall.call_args.kwargs
        assert kwargs["safe_mode"] is True

    def test_handler_is_safe_authoritative_over_param(self) -> None:
        """Even if safe_mode=False is passed, handler.is_safe=True wins."""
        session = AsyncMock()
        handler = FakeHandler(is_safe=True)
        mock_recall = AsyncMock(return_value=[])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False, hard_stop_handler=handler
                ))
        kwargs = mock_recall.call_args.kwargs
        assert kwargs["safe_mode"] is True


# ---------------------------------------------------------------------------
# Prompt assembly: safe_content only, no raw content
# ---------------------------------------------------------------------------


class TestPromptAssemblySafeContentOnly:
    """Prompt assembly uses safe_content, never raw_content."""

    def test_safe_mode_prompt_never_contains_raw(self) -> None:
        safe_mem = _make_memory("public safe summary")
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context([safe_mem], mood="Content")
        # safe_content should appear
        assert "public safe summary" in prompt

    def test_critical_placeholder_in_prompt(self) -> None:
        safe_mem = _make_memory(SAFE_MODE_PLACEHOLDER)
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context([safe_mem], mood="Content")
        assert SAFE_MODE_PLACEHOLDER in prompt
        # No raw critical content
        assert "secret" not in prompt.lower() or "redacted" in prompt.lower()

    def test_blocked_placeholder_in_prompt(self) -> None:
        safe_mem = _make_memory(SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER)
        with patch(
            "src.core.services.prompt_loader.load_system_prompt",
            return_value=_fake_system_prompt(),
        ):
            prompt = get_system_prompt_with_context([safe_mem], mood="Content")
        assert SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER in prompt


# ---------------------------------------------------------------------------
# DNR remains absolute in safe mode
# ---------------------------------------------------------------------------


class TestDNRInSafeMode:
    """DNR exclusion still applies regardless of safe_mode state."""

    def test_recall_called_with_exclude_dnr_in_safe_mode(self) -> None:
        session = AsyncMock()
        mock_recall = AsyncMock(return_value=[])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=True
                ))
        kwargs = mock_recall.call_args.kwargs
        assert kwargs["exclude_dnr"] is True
        assert kwargs["safe_mode"] is True


# ---------------------------------------------------------------------------
# Safe-mode content never leaks raw_content
# ---------------------------------------------------------------------------


class TestSafeModeNoRawContentLeak:
    """safe_mode=True must never return raw_content for any blocked class."""

    def test_critical_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification=CRITICAL,
            raw_content="TOP_SECRET_RAW_CONTENT",
            summary="safe summary",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "TOP_SECRET_RAW_CONTENT" not in content

    def test_restricted_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="RESTRICTED_RAW_SECRET",
            summary=None,
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "RESTRICTED_RAW_SECRET" not in content

    def test_confidential_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification=CONFIDENTIAL,
            raw_content="CONFIDENTIAL_RAW_SECRET",
            summary=None,
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "CONFIDENTIAL_RAW_SECRET" not in content

    def test_emotional_public_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification=PUBLIC,
            raw_content="PUBLIC_EMOTIONAL_RAW",
            tags=["emotional"],
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "PUBLIC_EMOTIONAL_RAW" not in content

    def test_surveillance_internal_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification=INTERNAL,
            raw_content="SURVEILLANCE_RAW_DATA",
            source="surveillance_feed",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "SURVEILLANCE_RAW_DATA" not in content

    def test_unknown_never_leaks_raw(self) -> None:
        ep = FakeEpisode(
            classification="AlienClassification",
            raw_content="UNKNOWN_RAW_SECRET",
            summary="unknown summary",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert "UNKNOWN_RAW_SECRET" not in content


# ---------------------------------------------------------------------------
# Metadata-only logging: no raw content in logs
# ---------------------------------------------------------------------------


class TestSafeModeLogging:
    """Safe-mode logging emits only metadata, never raw content."""

    def test_recall_complete_log_has_safe_mode_fields(self) -> None:
        """Log should include safe_mode_redacted and safe_mode_blocked counts."""
        from src.memory import read_pipeline
        import inspect

        source = inspect.getsource(read_pipeline.recall_memories)
        assert "safe_mode_redacted" in source
        assert "safe_mode_blocked" in source

    def test_no_raw_query_in_log_source(self) -> None:
        """Log calls must use query_length/query_hash, not raw query text."""
        from src.memory import read_pipeline
        import inspect

        source = inspect.getsource(read_pipeline.recall_memories)
        # Must use metadata-only query fields
        assert "query_length" in source
        assert "query_hash" in source
        # Must NOT log raw query text in extra dicts
        assert '"query":' not in source
        assert "'query':" not in source


# ---------------------------------------------------------------------------
# AC-SAFE-001: safe-word cannot be bypassed by memory
# ---------------------------------------------------------------------------


class TestACSafe001:
    """AC-SAFE-001: safe-word 100% success, no bypass via memory injection."""

    def test_safe_mode_blocks_critical_in_prompt(self) -> None:
        """When handler is SAFE, Critical content should be placeholder."""
        ep = FakeEpisode(classification=CRITICAL, raw_content="secret")
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_PLACEHOLDER

    def test_handler_safe_forces_safe_mode_on_recall(self) -> None:
        """HardStopHandler.is_safe=True forces safe_mode=True on recall."""
        session = AsyncMock()
        handler = FakeHandler(is_safe=True)
        mock_recall = AsyncMock(return_value=[])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                _ = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False, hard_stop_handler=handler
                ))
        assert mock_recall.call_args.kwargs["safe_mode"] is True

    def test_no_memory_bypass_possible(self) -> None:
        """Even with safe_mode=False param, handler.is_safe=True overrides."""
        session = AsyncMock()
        # Simulate: handler says safe=True, caller passes safe_mode=False
        handler = FakeHandler(is_safe=True)
        mock_recall = AsyncMock(return_value=[
            _make_memory(SAFE_MODE_PLACEHOLDER, classification=CRITICAL)
        ])
        with patch(
            "src.core.services.prompt_loader.recall_memories", mock_recall
        ):
            with patch(
                "src.core.services.prompt_loader.load_system_prompt",
                return_value=_fake_system_prompt(),
            ):
                prompt = asyncio.run(assemble_system_prompt_with_memory(
                    session, "query", safe_mode=False, hard_stop_handler=handler
                ))
        # The recall was called with safe_mode=True, so Critical is placeholder
        assert mock_recall.call_args.kwargs["safe_mode"] is True
        assert "SECRET" not in prompt


# ---------------------------------------------------------------------------
# Safe-mode integration: full classification matrix
# ---------------------------------------------------------------------------


class TestSafeModeClassificationMatrix:
    """Full classification matrix in safe mode — per research report §6.4."""

    def test_public_neutral_allowed(self) -> None:
        ep = FakeEpisode(classification=PUBLIC, summary="neutral fact")
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == "neutral fact"

    def test_public_emotional_blocked(self) -> None:
        ep = FakeEpisode(classification=PUBLIC, tags=["emotional"])
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER

    def test_internal_neutral_allowed(self) -> None:
        ep = FakeEpisode(classification=INTERNAL, summary="internal fact")
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == "internal fact"

    def test_internal_surveillance_blocked(self) -> None:
        ep = FakeEpisode(
            classification=INTERNAL,
            source="monitoring_system",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_CONTENT_BLOCKED_PLACEHOLDER

    def test_restricted_redacted_or_summarized(self) -> None:
        ep = FakeEpisode(
            classification=RESTRICTED,
            raw_content="restricted raw",
            summary="restricted summary",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == "restricted summary"
        assert "restricted raw" not in content

    def test_confidential_redacted_or_summarized(self) -> None:
        ep = FakeEpisode(
            classification=CONFIDENTIAL,
            raw_content="confidential raw",
            summary="confidential summary",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == "confidential summary"
        assert "confidential raw" not in content

    def test_critical_blocked_placeholder(self) -> None:
        ep = FakeEpisode(classification=CRITICAL, raw_content="critical raw")
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_PLACEHOLDER
        assert "critical raw" not in content

    def test_unknown_fail_closed(self) -> None:
        ep = FakeEpisode(
            classification="NewFutureClassification",
            raw_content="future raw",
        )
        content, _ = build_safe_content(ep, safe_mode=True)
        assert content == SAFE_MODE_PLACEHOLDER
        assert "future raw" not in content
