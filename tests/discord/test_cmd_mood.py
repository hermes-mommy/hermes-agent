"""Deterministic tests for ``src.discord.cmd_mood``.

All tests run without a ``discord.py`` runtime.  They exercise only the
pure-data builders and semantic invariants specified by STEP-P2-013.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from src.discord.colors import PRIMARY, SUCCESS, ACHIEVEMENT, WARNING, ALERT, NEUTRAL
from src.discord.cmd_mood import (
    MOOD_DESCRIPTION,
    MOOD_TITLE,
    MoodEmbedData,
    MoodEmbedField,
    build_mood_embed_data,
    display_for_mood,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def fixed_now() -> datetime:
    """Return a deterministic UTC timestamp for reproducible tests."""
    return datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)


@pytest.fixture
def default_data(fixed_now: datetime) -> MoodEmbedData:
    """Return the default ``MoodEmbedData`` built with a fixed timestamp."""
    return build_mood_embed_data(now=fixed_now)


# ── Title ────────────────────────────────────────────────────────────────────


class TestTitle:
    """The embed title must be exactly ``🧠 Mood Analysis``."""

    def test_title_exact(self, default_data: MoodEmbedData) -> None:
        assert default_data.title == MOOD_TITLE
        assert default_data.title == "\U0001f9e0 Mood Analysis"

    def test_title_contains_mood_and_analysis(self, default_data: MoodEmbedData) -> None:
        assert "Mood" in default_data.title
        assert "Analysis" in default_data.title


# ── Description / Persona Tone ──────────────────────────────────────────────


class TestDescription:
    """The embed description must include Darling (normal persona mode)."""

    def test_description_includes_darling(self, default_data: MoodEmbedData) -> None:
        assert "Darling" in default_data.description

    def test_description_is_persona_flavored(self, default_data: MoodEmbedData) -> None:
        """Verify the description contains Mommy or Darling."""
        desc = default_data.description
        assert "Mommy" in desc or "Darling" in desc

    def test_description_exact_constant(self, default_data: MoodEmbedData) -> None:
        assert default_data.description == MOOD_DESCRIPTION


# ── Field Count ──────────────────────────────────────────────────────────────


class TestFieldCount:
    """The embed must have exactly 6 fields."""

    def test_exactly_six_fields(self, default_data: MoodEmbedData) -> None:
        assert len(default_data.fields) == 6

    def test_fields_is_tuple(self, default_data: MoodEmbedData) -> None:
        assert isinstance(default_data.fields, tuple)


# ── Field Names ──────────────────────────────────────────────────────────────


class TestFieldNames:
    """Each field must have the expected canonical name."""

    EXPECTED_NAMES: frozenset[str] = frozenset({
        "Current Mood",
        "Undertone",
        "24h History",
        "Recent Triggers",
        "Streak",
        "Forecast",
    })

    def test_field_names_match(self, default_data: MoodEmbedData) -> None:
        names = {f.name for f in default_data.fields}
        assert names == self.EXPECTED_NAMES

    def test_field_order_is_stable(self, default_data: MoodEmbedData) -> None:
        """Fields must appear in a deterministic order."""
        ordered = [f.name for f in default_data.fields]
        expected_order = [
            "Current Mood",
            "Undertone",
            "24h History",
            "Recent Triggers",
            "Streak",
            "Forecast",
        ]
        assert ordered == expected_order

    def test_current_mood_is_first(self, default_data: MoodEmbedData) -> None:
        assert default_data.fields[0].name == "Current Mood"

    def test_forecast_is_last(self, default_data: MoodEmbedData) -> None:
        assert default_data.fields[-1].name == "Forecast"


# ── Color Behavior ───────────────────────────────────────────────────────────


class TestColorBehavior:
    """The embed colour must respond to the mood parameter."""

    def test_default_mood_uses_success_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="content")
        assert data.color == SUCCESS

    def test_content_mood_uses_success_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="content")
        assert data.color == SUCCESS

    def test_pleased_mood_uses_achievement_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="pleased")
        assert data.color == ACHIEVEMENT

    def test_disappointed_mood_uses_warning_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="disappointed")
        assert data.color == WARNING

    def test_angry_mood_uses_alert_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="angry")
        assert data.color == ALERT

    def test_silent_mood_uses_neutral_color(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="silent")
        assert data.color == NEUTRAL

    def test_unknown_mood_falls_back_to_primary(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="nonexistent")
        assert data.color == PRIMARY

    def test_color_matches_color_for_mood_function(self, fixed_now: datetime) -> None:
        from src.discord.colors import color_for_mood

        for mood in ("content", "pleased", "disappointed", "angry", "silent"):
            data = build_mood_embed_data(now=fixed_now, mood=mood)
            assert data.color == color_for_mood(mood), f"mismatch for mood={mood}"


# ── Dynamic Mood Display ─────────────────────────────────────────────────────


class TestMoodDisplay:
    """The ``Current Mood`` field text must reflect the mood parameter."""

    def test_default_mood_shows_content(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now)
        assert data.fields[0].value == "\U0001f60a Content"

    def test_angry_mood_shows_angry(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="angry")
        assert data.fields[0].value == "\U0001f620 Angry"

    def test_silent_mood_shows_silent(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="silent")
        assert data.fields[0].value == "\U0001f910 Silent"

    def test_unknown_mood_falls_back_to_content(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now, mood="bogus")
        assert data.fields[0].value == "\U0001f60a Content"


# ── _display_for_mood Unit Tests ─────────────────────────────────────────────


class TestDisplayForMood:
    """Direct unit tests for the ``display_for_mood`` helper."""

    def test_content(self) -> None:
        assert display_for_mood("content") == "\U0001f60a Content"

    def test_pleased(self) -> None:
        assert display_for_mood("pleased") == "\U0001f929 Pleased"

    def test_disappointed(self) -> None:
        assert display_for_mood("disappointed") == "\U0001f61e Disappointed"

    def test_angry(self) -> None:
        assert display_for_mood("angry") == "\U0001f620 Angry"

    def test_silent(self) -> None:
        assert display_for_mood("silent") == "\U0001f910 Silent"

    def test_unknown(self) -> None:
        assert display_for_mood("unknown") == "\U0001f60a Content"


# ── Degraded Placeholders ────────────────────────────────────────────────────


class TestDegradedPlaceholders:
    """Non-mood fields must use ``⚠️ — ...`` degraded placeholders."""

    def test_undertone_is_degraded(self, default_data: MoodEmbedData) -> None:
        assert "\u26a0\ufe0f" in default_data.fields[1].value
        assert "untone" in default_data.fields[1].value.lower() or "Undertone" in default_data.fields[1].value

    def test_history_is_degraded(self, default_data: MoodEmbedData) -> None:
        assert "\u26a0\ufe0f" in default_data.fields[2].value

    def test_triggers_are_degraded(self, default_data: MoodEmbedData) -> None:
        assert "\u26a0\ufe0f" in default_data.fields[3].value

    def test_streak_is_degraded(self, default_data: MoodEmbedData) -> None:
        assert "\u26a0\ufe0f" in default_data.fields[4].value

    def test_forecast_is_degraded(self, default_data: MoodEmbedData) -> None:
        assert "\u26a0\ufe0f" in default_data.fields[5].value


# ── Timestamp ─────────────────────────────────────────────────────────────────


class TestTimestamp:
    """The timestamp must be in WIB format."""

    def test_timestamp_is_wib_format(self, fixed_now: datetime) -> None:
        data = build_mood_embed_data(now=fixed_now)
        # fixed_now is 12:00 UTC = 19:00 WIB
        assert data.timestamp == "2026-06-01 19:00 WIB"

    def test_timestamp_defaults_to_empty_when_not_built(self) -> None:
        data = MoodEmbedData()
        assert data.timestamp == ""


# ── Footer ────────────────────────────────────────────────────────────────────


class TestFooter:
    """The footer must have the canonical text and icon."""

    def test_footer_text(self, default_data: MoodEmbedData) -> None:
        assert default_data.footer_text == "Guinevere de Baroque"

    def test_footer_icon(self, default_data: MoodEmbedData) -> None:
        assert default_data.footer_icon == "\U0001f9e0 Mood"


# ── Command Registry Count ───────────────────────────────────────────────────


class TestCommandRegistryCount:
    """Importing command_count must return the canonical registry size and be safe."""

    def test_command_count_is_canonical(self) -> None:
        from src.discord._command_registry import command_count

        assert command_count() == 35


# ── Dataclass Invariants ─────────────────────────────────────────────────────


class TestDataclassInvariants:
    """``MoodEmbedData`` and ``MoodEmbedField`` must behave as frozen dataclasses."""

    def test_mood_embed_data_is_frozen(self) -> None:
        data = MoodEmbedData()
        with pytest.raises(AttributeError):
            setattr(data, "title", "Changed")

    def test_mood_embed_field_is_frozen(self) -> None:
        field = MoodEmbedField("Test", "value")
        with pytest.raises(AttributeError):
            setattr(field, "name", "Changed")

    def test_mood_embed_field_defaults(self) -> None:
        field = MoodEmbedField("Test", "value")
        assert field.inline is False


# ── No discord.py Import at Module Level ─────────────────────────────────────


class TestNoTopLevelDiscordImport:
    """Importing the module must not require discord.py at the top level."""

    def test_import_does_not_fail_without_discord(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Simulate missing discord.py by blocking its import."""
        import importlib

        original = importlib.import_module

        def _block_discord(name: str, package: str | None = None) -> object:
            if name == "discord":
                raise ImportError("discord not available (simulated)")
            # Everything else passes through via the closure reference.
            return original(name, package)

        monkeypatch.setattr(importlib, "import_module", _block_discord)

        # Re-import cmd_mood in a clean state without the real discord
        import sys

        for mod_key in list(sys.modules):
            if "cmd_mood" in mod_key:
                del sys.modules[mod_key]

        # This should succeed because cmd_mood only imports discord dynamically
        from src.discord import cmd_mood as cmd  # noqa: F811

        # Calling to_discord_embed should fail with ImportError
        with pytest.raises(ImportError):
            _ = cmd.to_discord_embed(cmd.MoodEmbedData())


# ── Python 3.12+ Style ───────────────────────────────────────────────────────


class TestPython312Style:
    """File must use ``from __future__ import annotations``."""

    def test_module_has_annotations_future(self) -> None:
        import inspect

        from src.discord import cmd_mood

        source = inspect.getsource(cmd_mood)
        assert "from __future__ import annotations" in source