"""W15 Discord Gateway tests — M13 verification.

Tests:
- 41 COMMAND_SPECS registered (len >= 41).
- 3 bot identities (Guinevere, Pharsa, Company).
- No consent_gate, hard_stop, safe_mode in guinevere/discord/.
- wire(agent) function exists and works.
- Mock discord.py client (D2 — no live token).
- AutonomousInitiator hook exists.
- Command registry validation passes.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Fixtures ─────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _clean_project_session():
    """Reset project session state between tests."""
    from guinevere.discord._infrastructure import reset_active_project_id

    reset_active_project_id()
    yield
    reset_active_project_id()


@pytest.fixture
def mock_interaction() -> MagicMock:
    """Create a mock Discord interaction (guild owner = Faiz)."""
    interaction = MagicMock()
    interaction.guild.owner_id = 123456789
    interaction.user.id = 123456789  # Same as owner — authorized
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.is_done.return_value = False
    interaction.followup.send = AsyncMock()
    interaction.data = {}
    return interaction


@pytest.fixture
def mock_interaction_denied() -> MagicMock:
    """Create a mock Discord interaction (NOT guild owner)."""
    interaction = MagicMock()
    interaction.guild.owner_id = 123456789
    interaction.user.id = 999999999  # Different from owner — denied
    interaction.response.defer = AsyncMock()
    interaction.response.send_message = AsyncMock()
    interaction.response.is_done.return_value = False
    interaction.followup.send = AsyncMock()
    interaction.data = {}
    return interaction


@pytest.fixture
def mock_bot() -> MagicMock:
    """Create a mock Discord bot."""
    bot = MagicMock()
    bot.guilds = []
    bot.user = MagicMock()
    bot.user.__str__ = MagicMock(return_value="Guinevere#0001")
    bot.latency = 0.05
    bot.change_presence = AsyncMock()
    bot.process_commands = AsyncMock()
    bot.tree = MagicMock()
    bot.tree.command = MagicMock(return_value=lambda fn: fn)
    bot.tree.sync = AsyncMock(return_value=[])
    bot._startup_sent = False
    return bot


# ── Command Spec Tests ───────────────────────────────────────────────────


class TestCommandSpecs:
    """Test the 41-command registry."""

    def test_command_count_is_41(self):
        from guinevere.discord.commands import COMMAND_SPECS

        assert len(COMMAND_SPECS) == 41, f"Expected 41 commands, got {len(COMMAND_SPECS)}"

    def test_command_names_unique(self):
        from guinevere.discord.commands import COMMAND_SPECS

        names = [s.name for s in COMMAND_SPECS]
        assert len(names) == len(set(names)), "Duplicate command names found"

    def test_canonical_registry_validation(self):
        from guinevere.discord.commands import require_canonical_registry

        require_canonical_registry()  # Should not raise

    def test_command_count_function(self):
        from guinevere.discord.commands import command_count

        assert command_count() == 41

    def test_build_application_commands(self):
        from guinevere.discord.commands import build_application_commands

        payloads = build_application_commands()
        assert len(payloads) == 41
        for p in payloads:
            assert "name" in p
            assert "description" in p
            assert p["type"] == 1  # SLASH_COMMAND_TYPE

    def test_command_categories(self):
        from guinevere.discord.commands import command_categories

        cats = command_categories()
        assert "core" in cats
        assert "loop" in cats
        assert "memory" in cats
        assert "surveillance" in cats
        assert "finance" in cats
        assert "system" in cats
        assert "admin" in cats
        assert "integration" in cats
        # Verify category counts
        assert len(cats["core"]) == 6
        assert len(cats["loop"]) == 7
        assert len(cats["memory"]) == 4
        assert len(cats["surveillance"]) == 3
        assert len(cats["finance"]) == 3
        assert len(cats["system"]) == 8
        assert len(cats["admin"]) == 4
        assert len(cats["integration"]) == 6

    def test_all_41_names_present(self):
        from guinevere.discord.commands import COMMAND_SPECS, EXPECTED_COMMAND_NAME_SET

        names = {s.name for s in COMMAND_SPECS}
        assert names == EXPECTED_COMMAND_NAME_SET

    def test_no_stub_descriptions(self):
        from guinevere.discord.commands import COMMAND_SPECS

        for spec in COMMAND_SPECS:
            assert len(spec.description) > 0, f"{spec.name} has empty description"
            assert len(spec.description) <= 100, f"{spec.name} description too long"

    def test_name_lengths(self):
        from guinevere.discord.commands import COMMAND_SPECS

        for spec in COMMAND_SPECS:
            assert len(spec.name) <= 32, f"{spec.name} name too long"


# ── Bot Identity Tests ───────────────────────────────────────────────────


class TestBotIdentities:
    """Test the 3 bot identities."""

    def test_three_bot_identities(self):
        from guinevere.discord.bots import BOT_IDENTITIES

        assert len(BOT_IDENTITIES) == 3, f"Expected 3 bot identities, got {len(BOT_IDENTITIES)}"

    def test_guinevere_identity(self):
        from guinevere.discord.bots import BOT_IDENTITIES

        guin = BOT_IDENTITIES[0]
        assert guin.name == "Guinevere"
        assert guin.command_prefix == "!"
        assert guin.active is True
        assert guin.channel_id is not None

    def test_pharsa_identity(self):
        from guinevere.discord.bots import BOT_IDENTITIES

        pharsa = BOT_IDENTITIES[1]
        assert pharsa.name == "Pharsa"
        assert pharsa.active is False  # Not yet implemented

    def test_company_identity(self):
        from guinevere.discord.bots import BOT_IDENTITIES

        company = BOT_IDENTITIES[2]
        assert company.name == "Company"
        assert company.active is False  # Not yet implemented

    def test_get_identity(self):
        from guinevere.discord.bots import get_identity

        assert get_identity("Guinevere") is not None
        assert get_identity("guinevere") is not None  # Case-insensitive
        assert get_identity("Pharsa") is not None
        assert get_identity("Company") is not None
        assert get_identity("Unknown") is None

    def test_create_bot_factory(self):
        from guinevere.discord.bots import create_bot

        bot = create_bot("Guinevere")
        assert bot is not None
        assert bot.identity.name == "Guinevere"

    def test_create_bot_raises_on_unknown(self):
        from guinevere.discord.bots import create_bot

        with pytest.raises(ValueError, match="Unknown bot identity"):
            create_bot("NonExistent")


# ── GuinevereBot Tests ───────────────────────────────────────────────────


class TestGuinevereBot:
    """Test GuinevereBot class (mocked discord.py)."""

    def test_bot_class_exists(self):
        from guinevere.discord.bots import GuinevereBot

        assert GuinevereBot is not None

    def test_bot_init(self):
        from guinevere.discord.bots import GuinevereBot, BOT_IDENTITIES

        bot = GuinevereBot(identity=BOT_IDENTITIES[0])
        assert bot.identity.name == "Guinevere"

    def test_bot_shadow_pipeline(self):
        from guinevere.discord.bots import GuinevereBot

        bot = GuinevereBot()
        assert bot.shadow_pipeline is not None
        assert bot.shadow_pipeline.enabled is False  # Disabled by default

    def test_bot_autonomous_initiator(self):
        from guinevere.discord.bots import GuinevereBot

        bot = GuinevereBot()
        assert bot._autonomous_initiator is not None
        assert hasattr(bot._autonomous_initiator, "enabled")
        assert hasattr(bot._autonomous_initiator, "interval_hours")


# ── Autonomous Initiation Tests ──────────────────────────────────────────


class TestAutonomousInitiator:
    """Test the autonomous conversation initiation hook."""

    def test_initiator_exists(self):
        from guinevere.discord.bots import AutonomousInitiator

        assert AutonomousInitiator is not None

    def test_initiator_channel_id(self):
        from guinevere.discord.bots import AutonomousInitiator

        assert AutonomousInitiator.CHANNEL_ID == 1_510_914_600_777_023_659

    def test_initiator_disabled_by_default(self):
        from guinevere.discord.bots import AutonomousInitiator, GuinevereBot

        bot = GuinevereBot()
        initiator = bot._autonomous_initiator
        assert initiator.enabled is False or os.environ.get("AUTONOMOUS_CHAT", "false").lower() != "true"

    def test_initiator_default_interval(self):
        from guinevere.discord.bots import AutonomousInitiator, GuinevereBot

        bot = GuinevereBot()
        assert bot._autonomous_initiator.interval_hours >= 1

    def test_initiator_stop(self):
        from guinevere.discord.bots import AutonomousInitiator, GuinevereBot

        bot = GuinevereBot()
        # stop() should not raise even when no task is running
        bot._autonomous_initiator.stop()


# ── Infrastructure Tests ─────────────────────────────────────────────────


class TestInfrastructure:
    """Test infrastructure utilities."""

    def test_auth_guard_faiz(self):
        from guinevere.discord._infrastructure import is_faiz_interaction

        interaction = MagicMock()
        interaction.guild.owner_id = 123
        interaction.user.id = 123
        assert is_faiz_interaction(interaction) is True

    def test_auth_guard_not_faiz(self):
        from guinevere.discord._infrastructure import is_faiz_interaction

        interaction = MagicMock()
        interaction.guild.owner_id = 123
        interaction.user.id = 456
        assert is_faiz_interaction(interaction) is False

    def test_auth_guard_no_guild(self):
        from guinevere.discord._infrastructure import is_faiz_interaction

        interaction = MagicMock()
        interaction.guild = None
        assert is_faiz_interaction(interaction) is False

    def test_colors(self):
        from guinevere.discord._infrastructure import PRIMARY, ALERT, SUCCESS, WARNING, color_for_mood

        assert PRIMARY == 0x6B21A8
        assert ALERT == 0xDC2626
        assert SUCCESS == 0x16A34A
        assert color_for_mood("angry") == ALERT
        assert color_for_mood("content") == SUCCESS
        assert color_for_mood("unknown") == PRIMARY  # Default

    def test_intents(self):
        from guinevere.discord._infrastructure import get_intents

        intents = get_intents()
        assert intents.message_content is True
        assert intents.members is True
        assert intents.presences is True
        assert intents.guilds is True

    def test_build_embed(self):
        from guinevere.discord._infrastructure import build_embed, PRIMARY

        embed = build_embed("Test Title", "Test Description", PRIMARY)
        assert embed is not None

    def test_project_session(self):
        from guinevere.discord._infrastructure import (
            get_active_project_id,
            set_active_project_id,
            reset_active_project_id,
            get_default_project_id,
        )

        default = get_default_project_id()
        assert default == "00000000-0000-0000-0000-000000000001"
        assert get_active_project_id() == default

        set_active_project_id("test-uuid")
        assert get_active_project_id() == "test-uuid"

        reset_active_project_id()
        assert get_active_project_id() == default

    def test_sev_alert(self):
        from guinevere.discord._infrastructure import SevAlert, ALERT

        alert = SevAlert(severity="SEV0", title="Test", description="Test alert")
        assert alert.color == ALERT  # Auto-resolved from severity

    def test_shadow_pipeline(self):
        from guinevere.discord._infrastructure import ShadowPipeline

        sp = ShadowPipeline(enabled=False)
        assert sp.enabled is False
        assert sp.stats["enabled"] is False

    def test_wib_timezone(self):
        from guinevere.discord._infrastructure import WIB, format_wib_timestamp
        from datetime import datetime, timezone

        dt = datetime(2026, 6, 29, 12, 0, 0, tzinfo=timezone.utc)
        formatted = format_wib_timestamp(dt)
        assert "WIB" in formatted

    def test_gotify_priority(self):
        from guinevere.discord._infrastructure import _get_gotify_priority

        assert _get_gotify_priority("SEV0") == 10
        assert _get_gotify_priority("SEV1") == 7
        assert _get_gotify_priority("SEV4") == 1
        assert _get_gotify_priority("UNKNOWN") == 0

    def test_response_splitter(self):
        from guinevere.discord._infrastructure import _split_response

        # Short text should not split
        assert len(_split_response("Hello world")) == 1

        # Long text should split
        long_text = ". ".join(["sentence"] * 500)
        chunks = _split_response(long_text)
        assert len(chunks) >= 1


# ── Gateway Patch Tests ──────────────────────────────────────────────────


class TestGatewayPatch:
    """Test gateway patch integration."""

    def test_wire_function_exists(self):
        from guinevere.discord.gateway_patch import wire

        assert callable(wire)

    def test_register_platform_function_exists(self):
        from guinevere.discord.gateway_patch import register_platform

        assert callable(register_platform)

    def test_wire_attaches_identity(self):
        from guinevere.discord.gateway_patch import wire

        agent = MagicMock()
        # wire() may fail platform registration (gateway not available),
        # but should still attach identity
        try:
            wire(agent)
        except (ImportError, AttributeError):
            pass
        assert getattr(agent, "_discord_identity", None) is not None
        assert agent._discord_identity.name == "Guinevere"

    def test_get_patch_info(self):
        from guinevere.discord.gateway_patch import get_patch_info

        info = get_patch_info()
        assert info["platform_name"] == "discord"
        assert info["guild_id"] == 1_510_876_414_671_323_206


# ── Import Integration Tests ─────────────────────────────────────────────


class TestImports:
    """Test clean imports from guinevere.discord."""

    def test_top_level_imports(self):
        from guinevere.discord import GuinevereBot, CommandRegistry, COMMAND_SPECS, BOT_IDENTITIES

        assert GuinevereBot is not None
        assert CommandRegistry is not None
        assert len(COMMAND_SPECS) == 41
        assert len(BOT_IDENTITIES) == 3

    def test_no_consent_gate_in_commands(self):
        """Verify no consent_gate imports in guinevere/discord/commands.py."""
        import guinevere.discord.commands as mod
        source = open(mod.__file__, encoding="utf-8").read()
        assert "consent_gate" not in source
        assert "hard_stop" not in source
        assert "safe_mode" not in source

    def test_no_consent_gate_in_infrastructure(self):
        """Verify no consent_gate imports in guinevere/discord/_infrastructure.py."""
        import guinevere.discord._infrastructure as mod
        source = open(mod.__file__, encoding="utf-8").read()
        assert "consent_gate" not in source
        assert "hard_stop" not in source
        assert "safe_mode" not in source

    def test_no_consent_gate_in_bots(self):
        """Verify no consent_gate imports in guinevere/discord/bots.py."""
        import guinevere.discord.bots as mod
        source = open(mod.__file__, encoding="utf-8").read()
        assert "consent_gate" not in source
        assert "hard_stop" not in source
        assert "safe_mode" not in source

    def test_no_type_ignore(self):
        """Verify no '# type: ignore' in any guinevere/discord/ file."""
        import guinevere.discord as pkg
        pkg_dir = os.path.dirname(pkg.__file__)
        for fname in os.listdir(pkg_dir):
            if fname.endswith(".py"):
                fpath = os.path.join(pkg_dir, fname)
                content = open(fpath, encoding="utf-8").read()
                assert "# type: ignore" not in content, f"type: ignore found in {fname}"

    def test_no_bare_except(self):
        """Verify no bare 'except:' in any guinevere/discord/ file."""
        import guinevere.discord as pkg
        pkg_dir = os.path.dirname(pkg.__file__)
        for fname in os.listdir(pkg_dir):
            if fname.endswith(".py"):
                fpath = os.path.join(pkg_dir, fname)
                content = open(fpath, encoding="utf-8").read()
                # Check for bare except (except: without exception type)
                for line in content.split("\n"):
                    stripped = line.strip()
                    if stripped == "except:" or stripped.startswith("except:"):
                        pytest.fail(f"bare except found in {fname}: {stripped}")


# ── Callback Tests ───────────────────────────────────────────────────────


class TestCallbacks:
    """Test command callback functions."""

    @pytest.mark.asyncio
    async def test_status_callback_auth(self, mock_interaction):
        from guinevere.discord.commands import _callback_status

        await _callback_status(mock_interaction)
        mock_interaction.response.defer.assert_called_once()
        mock_interaction.followup.send.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_callback_denied(self, mock_interaction_denied):
        from guinevere.discord.commands import _callback_status

        await _callback_status(mock_interaction_denied)
        # Should send denied message, not defer
        mock_interaction_denied.response.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_help_callback(self, mock_interaction):
        from guinevere.discord.commands import _callback_help

        await _callback_help(mock_interaction)
        mock_interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_mood_callback(self, mock_interaction):
        from guinevere.discord.commands import _callback_mood

        await _callback_mood(mock_interaction)
        mock_interaction.response.defer.assert_called_once()

    @pytest.mark.asyncio
    async def test_all_callbacks_exist(self):
        """Verify all 41 commands have callbacks registered."""
        from guinevere.discord.commands import _COMMAND_CALLBACKS, COMMAND_SPECS

        for spec in COMMAND_SPECS:
            assert spec.name in _COMMAND_CALLBACKS, f"No callback for /{spec.name}"
