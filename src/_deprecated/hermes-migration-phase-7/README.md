# Hermes Migration Phase 7 Deprecated Archive

This directory contains the archived Discord/Hermes migration files from ADR-035 Phase 7c B3.

## Archive policy

- Files were moved with `git mv`; they were not deleted.
- This directory is a non-importable tombstone archive. The hyphenated path is intentional.
- Active runtime and tests must not import from this directory.
- `src/core/services/llm_router.py` is intentionally not archived because it remains active for Phase 6/7 LLM routing and CostTracker behavior.

## Archived files

| Archived file | Former path | Replacement / active home |
|---|---|---|
| `bot.py` | `src/discord/bot.py` | `src/discord/_entrypoint.py` |
| `conversational_handler.py` | `src/discord/conversational_handler.py` | `src/discord/hermes_conversational.py` |
| `commands.py` | `src/discord/commands.py` | `src/discord/_command_registry.py`, `src/discord/_auth_guard.py`, `src/hermes_plugins/command_catalog.py` |
| `permissions.py` | `src/discord/permissions.py` | No active runtime importer after Phase 7c import migration |
| `guild_setup.py` | `src/discord/guild_setup.py` | No active runtime importer after Phase 7c import migration |
| `startup.py` | `src/discord/startup.py` | `src/discord/_startup.py` |
| `_embed_helpers.py` | `src/discord/_embed_helpers.py` | `src/discord/_embed_utils.py` |
| `intents.py` | `src/discord/intents.py` | `src/discord/_intents.py` |
| `session_adapter.py` | `src/hermes/session_adapter.py` | `src/hermes/_session_adapter.py` |
| `memory_bridge.py` | `src/hermes/memory_bridge.py` | `src/hermes/_memory_bridge.py` |

## Boundary note

This archive does not mark ADR-035 as implemented by itself. Final Phase 7 completion still depends on the remaining migration gates and auditor sign-off.
