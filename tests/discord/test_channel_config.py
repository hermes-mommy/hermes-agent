"""Tests for guinevere.discord.channel_config — ChannelConfig, ChannelPermissions,
is_command_allowed, and build_default_permissions."""

from __future__ import annotations

import os
import pytest

from guinevere.discord.channel_config import (
    CHANNEL_COMMAND_ALLOW,
    CHANNEL_KEYS,
    ChannelConfig,
    ChannelPermissions,
    build_default_permissions,
    is_command_allowed,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

# Fake snowflake IDs for testing (must look like Discord IDs: 17-19 digits)
_FAKE_GENERAL = 111111111111111111
_FAKE_CMDS = 222222222222222222
_FAKE_MEDIA = 333333333333333333
_FAKE_NOTIF = 444444444444444444
_FAKE_ADMIN = 555555555555555555


@pytest.fixture()
def channel_config() -> ChannelConfig:
    return ChannelConfig(
        general=_FAKE_GENERAL,
        commands_hq=_FAKE_CMDS,
        media_gallery=_FAKE_MEDIA,
        notifications=_FAKE_NOTIF,
        admin_internal=_FAKE_ADMIN,
    )


@pytest.fixture()
def default_perms() -> ChannelPermissions:
    return build_default_permissions()


# ---------------------------------------------------------------------------
# ChannelConfig — construction
# ---------------------------------------------------------------------------


class TestChannelConfigInit:
    """Basic construction and frozen invariant."""

    def test_init_direct(self) -> None:
        cfg = ChannelConfig(
            general=1, commands_hq=2, media_gallery=3,
            notifications=4, admin_internal=5,
        )
        assert cfg.general == 1
        assert cfg.commands_hq == 2
        assert cfg.media_gallery == 3
        assert cfg.notifications == 4
        assert cfg.admin_internal == 5

    def test_frozen(self, channel_config: ChannelConfig) -> None:
        with pytest.raises(AttributeError):
            channel_config.general = 999  # type: ignore[misc]


class TestChannelConfigFromEnv:
    """ChannelConfig.from_env() reads DISCORD_CHANNEL_* variables."""

    def test_from_env_success(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_CHANNEL_GENERAL", str(_FAKE_GENERAL))
        monkeypatch.setenv("DISCORD_CHANNEL_COMMANDS_HQ", str(_FAKE_CMDS))
        monkeypatch.setenv("DISCORD_CHANNEL_MEDIA_GALLERY", str(_FAKE_MEDIA))
        monkeypatch.setenv("DISCORD_CHANNEL_NOTIFICATIONS", str(_FAKE_NOTIF))
        monkeypatch.setenv("DISCORD_CHANNEL_ADMIN_INTERNAL", str(_FAKE_ADMIN))

        cfg = ChannelConfig.from_env()
        assert cfg.general == _FAKE_GENERAL
        assert cfg.commands_hq == _FAKE_CMDS
        assert cfg.media_gallery == _FAKE_MEDIA
        assert cfg.notifications == _FAKE_NOTIF
        assert cfg.admin_internal == _FAKE_ADMIN

    def test_from_env_missing_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        # Clear all channel env vars
        for key in (
            "DISCORD_CHANNEL_GENERAL",
            "DISCORD_CHANNEL_COMMANDS_HQ",
            "DISCORD_CHANNEL_MEDIA_GALLERY",
            "DISCORD_CHANNEL_NOTIFICATIONS",
            "DISCORD_CHANNEL_ADMIN_INTERNAL",
        ):
            monkeypatch.delenv(key, raising=False)

        with pytest.raises(EnvironmentError, match="Missing required"):
            ChannelConfig.from_env()

    def test_from_env_invalid_int(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("DISCORD_CHANNEL_GENERAL", "not_a_number")
        monkeypatch.setenv("DISCORD_CHANNEL_COMMANDS_HQ", str(_FAKE_CMDS))
        monkeypatch.setenv("DISCORD_CHANNEL_MEDIA_GALLERY", str(_FAKE_MEDIA))
        monkeypatch.setenv("DISCORD_CHANNEL_NOTIFICATIONS", str(_FAKE_NOTIF))
        monkeypatch.setenv("DISCORD_CHANNEL_ADMIN_INTERNAL", str(_FAKE_ADMIN))

        with pytest.raises(EnvironmentError, match="valid integer"):
            ChannelConfig.from_env()


class TestChannelConfigFromDict:
    """ChannelConfig.from_dict() reads from a plain dict."""

    def test_from_dict_success(self) -> None:
        d = {
            "general": _FAKE_GENERAL,
            "commands_hq": _FAKE_CMDS,
            "media_gallery": _FAKE_MEDIA,
            "notifications": _FAKE_NOTIF,
            "admin_internal": _FAKE_ADMIN,
        }
        cfg = ChannelConfig.from_dict(d)
        assert cfg.general == _FAKE_GENERAL

    def test_from_dict_missing_key(self) -> None:
        d = {"general": _FAKE_GENERAL, "commands_hq": _FAKE_CMDS}
        with pytest.raises(KeyError, match="Missing required"):
            ChannelConfig.from_dict(d)

    def test_from_dict_wrong_type(self) -> None:
        d: dict[str, object] = {
            "general": "not_int",
            "commands_hq": _FAKE_CMDS,
            "media_gallery": _FAKE_MEDIA,
            "notifications": _FAKE_NOTIF,
            "admin_internal": _FAKE_ADMIN,
        }
        with pytest.raises(TypeError, match="must be an int"):
            ChannelConfig.from_dict(d)  # type: ignore[arg-type]


class TestChannelIdToKey:
    """channel_config.channel_id_to_key() resolution."""

    def test_resolves_general(self, channel_config: ChannelConfig) -> None:
        assert channel_config.channel_id_to_key(_FAKE_GENERAL) == "general"

    def test_resolves_commands_hq(self, channel_config: ChannelConfig) -> None:
        assert channel_config.channel_id_to_key(_FAKE_CMDS) == "commands_hq"

    def test_resolves_admin_internal(self, channel_config: ChannelConfig) -> None:
        assert channel_config.channel_id_to_key(_FAKE_ADMIN) == "admin_internal"

    def test_unconfigured_returns_none(self, channel_config: ChannelConfig) -> None:
        assert channel_config.channel_id_to_key(999999999999999999) is None


# ---------------------------------------------------------------------------
# ChannelPermissions
# ---------------------------------------------------------------------------


class TestChannelPermissions:
    """ChannelPermissions dataclass and allowed_commands()."""

    def test_default_permissions_contain_all_keys(self) -> None:
        perms = build_default_permissions()
        for key in CHANNEL_KEYS:
            _ = perms.allowed_commands(key)  # should not raise

    def test_default_general_allows_status(self, default_perms: ChannelPermissions) -> None:
        assert "status" in default_perms.allowed_commands("general")

    def test_default_general_allows_safeword(self, default_perms: ChannelPermissions) -> None:
        assert "safeword" in default_perms.allowed_commands("general")

    def test_default_general_denies_loop_start(self, default_perms: ChannelPermissions) -> None:
        assert "loop-start" not in default_perms.allowed_commands("general")

    def test_commands_hq_is_wildcard(self, default_perms: ChannelPermissions) -> None:
        allowed = default_perms.allowed_commands("commands_hq")
        assert "__all__" in allowed

    def test_media_gallery_limited(self, default_perms: ChannelPermissions) -> None:
        allowed = default_perms.allowed_commands("media_gallery")
        assert "mood" in allowed
        assert "help" in allowed
        assert "memory-search" in allowed
        assert "loop-start" not in allowed

    def test_notifications_empty(self, default_perms: ChannelPermissions) -> None:
        allowed = default_perms.allowed_commands("notifications")
        assert len(allowed) == 0

    def test_admin_internal_is_wildcard(self, default_perms: ChannelPermissions) -> None:
        allowed = default_perms.allowed_commands("admin_internal")
        assert "__all__" in allowed

    def test_unknown_key_returns_empty(self) -> None:
        perms = build_default_permissions()
        assert len(perms.allowed_commands("nonexistent")) == 0


# ---------------------------------------------------------------------------
# is_command_allowed — default permissions
# ---------------------------------------------------------------------------


class TestIsCommandAllowed:
    """is_command_allowed() with the default ChannelPermissions."""

    def test_general_allows_status(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_GENERAL, "status", channel_config, default_perms) is True

    def test_general_allows_safeword(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_GENERAL, "safeword", channel_config, default_perms) is True

    def test_general_denies_loop_start(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_GENERAL, "loop-start", channel_config, default_perms) is False

    def test_commands_hq_allows_any(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_CMDS, "loop-start", channel_config, default_perms) is True

    def test_commands_hq_allows_memory_search(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_CMDS, "memory-search", channel_config, default_perms) is True

    def test_media_gallery_allows_mood(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_MEDIA, "mood", channel_config, default_perms) is True

    def test_media_gallery_denies_loop_start(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_MEDIA, "loop-start", channel_config, default_perms) is False

    def test_notifications_denies_status(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_NOTIF, "status", channel_config, default_perms) is False

    def test_admin_internal_allows_any(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
    ) -> None:
        assert is_command_allowed(_FAKE_ADMIN, "restart-service", channel_config, default_perms) is True

    def test_unknown_channel_defaults_to_allow(
        self, channel_config: ChannelConfig, default_perms: ChannelPermissions,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        unknown_id = 999999999999999999
        with caplog.at_level("WARNING"):
            result = is_command_allowed(unknown_id, "status", channel_config, default_perms)
        assert result is True
        assert "unconfigured channel" in caplog.text


# ---------------------------------------------------------------------------
# is_command_allowed — custom permissions
# ---------------------------------------------------------------------------


class TestIsCommandAllowedCustomPerms:
    """is_command_allowed() with bespoke ChannelPermissions overrides."""

    def test_empty_set_blocks_all(self, channel_config: ChannelConfig) -> None:
        perms = ChannelPermissions(permissions={
            "general": frozenset(),
            "commands_hq": frozenset(),
            "media_gallery": frozenset(),
            "notifications": frozenset(),
            "admin_internal": frozenset(),
        })
        assert is_command_allowed(_FAKE_GENERAL, "status", channel_config, perms) is False

    def test_wildcard_allows_everything(self, channel_config: ChannelConfig) -> None:
        perms = ChannelPermissions(permissions={
            "general": frozenset({"__all__"}),
            "commands_hq": frozenset(),
            "media_gallery": frozenset(),
            "notifications": frozenset(),
            "admin_internal": frozenset(),
        })
        assert is_command_allowed(_FAKE_GENERAL, "loop-start", channel_config, perms) is True
        assert is_command_allowed(_FAKE_GENERAL, "restart-service", channel_config, perms) is True

    def test_specific_set_respected(self, channel_config: ChannelConfig) -> None:
        perms = ChannelPermissions(permissions={
            "general": frozenset({"mood"}),
            "commands_hq": frozenset(),
            "media_gallery": frozenset(),
            "notifications": frozenset(),
            "admin_internal": frozenset(),
        })
        assert is_command_allowed(_FAKE_GENERAL, "mood", channel_config, perms) is True
        assert is_command_allowed(_FAKE_GENERAL, "status", channel_config, perms) is False


# ---------------------------------------------------------------------------
# CHANNEL_COMMAND_ALLOW constant sanity
# ---------------------------------------------------------------------------


class TestChannelCommandAllowConstant:
    """Verify the module-level constant has the expected shape."""

    def test_keys_match_channel_keys(self) -> None:
        assert set(CHANNEL_COMMAND_ALLOW.keys()) == set(CHANNEL_KEYS)

    def test_commands_hq_is_wildcard(self) -> None:
        assert "__all__" in CHANNEL_COMMAND_ALLOW["commands_hq"]

    def test_admin_internal_is_wildcard(self) -> None:
        assert "__all__" in CHANNEL_COMMAND_ALLOW["admin_internal"]

    def test_notifications_is_empty(self) -> None:
        assert len(CHANNEL_COMMAND_ALLOW["notifications"]) == 0

    def test_general_subset(self) -> None:
        expected = {"status", "mood", "help", "casual", "safeword"}
        assert CHANNEL_COMMAND_ALLOW["general"] == expected

    def test_media_gallery_subset(self) -> None:
        expected = {"mood", "help", "memory-search"}
        assert CHANNEL_COMMAND_ALLOW["media_gallery"] == expected


# ---------------------------------------------------------------------------
# Imports from __init__
# ---------------------------------------------------------------------------


class TestPackageExports:
    """Verify that channel_config symbols are exported from guinevere.discord."""

    def test_import_channel_config(self) -> None:
        from guinevere.discord import ChannelConfig as CC
        assert CC is ChannelConfig

    def test_import_channel_permissions(self) -> None:
        from guinevere.discord import ChannelPermissions as CP
        assert CP is ChannelPermissions

    def test_import_is_command_allowed(self) -> None:
        from guinevere.discord import is_command_allowed as ica
        assert ica is is_command_allowed

    def test_import_channel_command_allow(self) -> None:
        from guinevere.discord import CHANNEL_COMMAND_ALLOW as cca
        assert cca is CHANNEL_COMMAND_ALLOW

    def test_import_build_default_permissions(self) -> None:
        from guinevere.discord import build_default_permissions as bdp
        assert bdp is build_default_permissions
