# B2 — ChannelConfig + ChannelPermissions Implementation Report

## What Was Done

Created the `ChannelConfig` and `ChannelPermissions` module for Guinevere's Discord bot, providing per-channel command gating logic. The module is pure data — no Discord API calls, no gateway connections.

### Core Components

| Component | Description |
|---|---|
| `ChannelConfig` | Frozen dataclass mapping 5 logical channel keys to Discord snowflake int IDs |
| `ChannelConfig.from_env()` | Classmethod reading `DISCORD_CHANNEL_*` env vars (no defaults — all required) |
| `ChannelConfig.from_dict(d)` | Classmethod for YAML/dict config loading |
| `ChannelConfig.channel_id_to_key(id)` | Reverse lookup: snowflake → config key |
| `ChannelPermissions` | Frozen dataclass mapping channel keys to `frozenset[str]` of allowed command names |
| `CHANNEL_COMMAND_ALLOW` | Module-level default permission mapping |
| `build_default_permissions()` | Factory for default `ChannelPermissions` instance |
| `is_command_allowed()` | Gate function: `channel_id + command_name → bool` |

### Default Permission Matrix

| Channel | Allowed Commands |
|---|---|
| `general` | `status`, `mood`, `help`, `casual`, `safeword` |
| `commands_hq` | `__all__` (every command) |
| `media_gallery` | `mood`, `help`, `memory-search` |
| `notifications` | ∅ (empty — bot-only posting) |
| `admin_internal` | `__all__` (every command) |

### Design Decisions

- **Unknown channels default-allow**: If a `channel_id` doesn't match any configured channel, `is_command_allowed()` returns `True` and logs a warning. This prevents bot lockout when new channels are added before config is updated.
- **`__all__` sentinel**: A set containing `"__all__"` grants access to all commands. This is checked before the exact-match path.
- **Empty set = deny all**: An empty frozenset means no commands are permitted — used for notifications/bot-only channels.
- **Frozen dataclasses**: Both `ChannelConfig` and `ChannelPermissions` are frozen for runtime safety.
- **No hardcoded IDs**: All channel snowflakes arrive via env vars or dict config.
- **No `type: ignore` or `Any`**: Clean typing throughout.

## Files Changed

| File | Action | Lines |
|---|---|---|
| `guinevere/discord/channel_config.py` | Created | ~180 |
| `guinevere/discord/__init__.py` | Updated exports | Added 5 imports + 5 `__all__` entries |
| `tests/discord/test_channel_config.py` | Created | ~370 |
| `evidence/discord-refactor/B2/implementation-report.md` | Created | This file |

## Validation Results

### Import Test
```
$ python -c "from guinevere.discord.channel_config import ChannelConfig; print('OK')"
OK
```

### Pytest (45/45 passed)
```
$ python -m pytest tests/discord/test_channel_config.py -v -x --timeout=30

tests/discord/test_channel_config.py::TestChannelConfigInit::test_init_direct PASSED
tests/discord/test_channel_config.py::TestChannelConfigInit::test_frozen PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromEnv::test_from_env_success PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromEnv::test_from_env_missing_vars PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromEnv::test_from_env_invalid_int PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromDict::test_from_dict_success PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromDict::test_from_dict_missing_key PASSED
tests/discord/test_channel_config.py::TestChannelConfigFromDict::test_from_dict_wrong_type PASSED
tests/discord/test_channel_config.py::TestChannelIdToKey::test_resolves_general PASSED
tests/discord/test_channel_config.py::TestChannelIdToKey::test_resolves_commands_hq PASSED
tests/discord/test_channel_config.py::TestChannelIdToKey::test_resolves_admin_internal PASSED
tests/discord/test_channel_config.py::TestChannelIdToKey::test_unconfigured_returns_none PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_default_permissions_contain_all_keys PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_default_general_allows_status PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_default_general_allows_safeword PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_default_general_denies_loop_start PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_commands_hq_is_wildcard PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_media_gallery_limited PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_notifications_empty PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_admin_internal_is_wildcard PASSED
tests/discord/test_channel_config.py::TestChannelPermissions::test_unknown_key_returns_empty PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_general_allows_status PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_general_allows_safeword PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_general_denies_loop_start PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_commands_hq_allows_any PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_commands_hq_allows_memory_search PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_media_gallery_allows_mood PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_media_gallery_denies_loop_start PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_notifications_denies_status PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_admin_internal_allows_any PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowed::test_unknown_channel_defaults_to_allow PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowedCustomPerms::test_empty_set_blocks_all PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowedCustomPerms::test_wildcard_allows_everything PASSED
tests/discord/test_channel_config.py::TestIsCommandAllowedCustomPerms::test_specific_set_respected PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_keys_match_channel_keys PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_commands_hq_is_wildcard PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_admin_internal_is_wildcard PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_notifications_is_empty PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_general_subset PASSED
tests/discord/test_channel_config.py::TestChannelCommandAllowConstant::test_media_gallery_subset PASSED
tests/discord/test_channel_config.py::TestPackageExports::test_import_channel_config PASSED
tests/discord/test_channel_config.py::TestPackageExports::test_import_channel_permissions PASSED
tests/discord/test_channel_config.py::TestPackageExports::test_import_is_command_allowed PASSED
tests/discord/test_channel_config.py::TestPackageExports::test_import_channel_command_allow PASSED
tests/discord/test_channel_config.py::TestPackageExports::test_import_build_default_permissions PASSED

45 passed, 1 warning in 0.35s
```

### LSP Diagnostics
basedpyright is not installed in this environment — no LSP diagnostics available. Code was manually verified against type annotations.

## Next Steps

1. **Integrate into bot dispatch**: Wire `is_command_allowed()` into the bot's slash-command dispatch handler (e.g. `@bot.tree.error` or a before-invoke hook) to reject commands in unconfigured/restricted channels with an ephemeral response.
2. **YAML config file**: Create a `config.yaml` or `channels.yaml` that can be loaded with `ChannelConfig.from_dict(yaml.safe_load(...))`.
3. **Set env vars on VPS**: Configure the 5 `DISCORD_CHANNEL_*` environment variables with actual Discord snowflake IDs in the systemd service unit.
4. **Permission override admin command**: Consider a `/channel-permissions` admin command to modify `ChannelPermissions` at runtime (future enhancement).
