# S1/S2 Current State Analysis — Phase 7c Pre-Refactoring

> Generated: 2026-06-06
> Target: command_catalog.py, adapter.py, session_adapter.py, hermes/__init__.py, help.py

## 1. command_catalog.py — Exports & command_count

**File:** /src/hermes_plugins/command_catalog.py (51 lines)

### Exports
| Symbol | Type | Description |
|---|---|---|
| _COMMAND_CATEGORIES | Final[dict[str, tuple[str, ...]]] | Private constant — 7 categories with command tuples |
| command_categories() | () -> dict[str, tuple[str, ...]] | Public function — returns a **copy** of _COMMAND_CATEGORIES |
| command_count() | () -> int | Public function — returns sum(len(cmds) for cmds in _COMMAND_CATEGORIES.values()) |

### command_count() Equivalent
**Yes, it exists** as a public function command_count() at line 49. It computes total commands by summing the length of all category tuples.

### Categories and commands defined:
- **core**: status, mood, help, safeword, new, history (6)
- **loop**: loop-start, loop-stop, loop-pause, loop-resume, loops, evidence, loop-priority (7)
- **memory**: memory-search, memory-add, memory-forget, memory-export (4)
- **surveillance**: surveillance-status, surveillance-pause, surveillance-resume (3)
- **finance**: cost, budget, cost-alert (3)
- **system**: approve, deny, approve-all, focus, casual, consent, punishment, reward (8)
- **admin**: restart-service, backup-now, health-check, clear-cache (4)

**Total: 35 commands.**

### Discord dependency
The docstring says "Mirrors the data from src.discord.commands" but the **actual code has zero imports from src.discord** — it is a completely standalone catalog.

---

## 2. adapter.py vs session_adapter.py — What Moved vs What Remained

### adapter.py (NEW — S2 extraction)
**File:** src/hermes/adapter.py (51 lines)

Contains **only** the get_adapter() singleton factory function. This was extracted from the old hermes/__init__.py to allow deferred loading.

Key characteristics:
- Imports Redis from edis.asyncio eagerly.
- Uses TYPE_CHECKING guard for HermesSessionAdapter import (deferred to first get_adapter() call).
- Holds _adapter_instance module-level singleton (HermesSessionAdapter | None).
- get_adapter() lazily instantiates HermesSessionAdapter with:
  - edis_client=Redis() (default connection to localhost:6379 DB0)
  - llm_config with base_url http://localhost:20128/v1, model ds/deepseek-v4-flash, provider 9router, api_key sk-local
- **No class definitions.** Just the function.

### session_adapter.py (ORIGINAL — remains after S1/S2)
**File:** src/hermes/session_adapter.py (366 lines)

Contains **everything else** — all the heavy lifting:

- **Constants:** REDIS_HOST, REDIS_PORT (6380 — non-standard!), REDIS_DB (4), REDIS_USERNAME, SESSION_TTL, MAX_HISTORY_TURNS, etc.
- **_hash_user_id() helper** — SHA-256 hash truncation for safe logging.
- **HermesSessionAdapter class** (line 74):
  - __init__(self, redis_client, llm_config) — creates a **dedicated** ioredis.Redis() connection to DB4 (ignores the passed edis_client for API compat)
  - _build_key(user_id) — Redis key generation
  - send_message() — the main public method (line 173) — sends messages, manages sessions, cost tracking
  - Internal methods for session crud, history management, AIAgent lifecycle
- **No get_adapter() function** in this file — that was fully extracted to dapter.py.
- **No redundant adapter class** — HermesSessionAdapter is defined only here.

### Key difference: Redis connection
- dapter.py passes Redis() (default — localhost:6379 DB0) to the constructor
- session_adapter.py's __init__ **ignores** the passed edis_client and creates its own connection to localhost:6380 DB4 with REDIS_USERNAME auth

This means dapter.py's get_adapter() passes a dummy Redis client that is never used — a known API-compat pattern noted in the docstring.

---

## 3. hermes/__init__.py — Current State

**File:** src/hermes/__init__.py (16 lines)

### What it does:
- Contains only a docstring and rom __future__ import annotations.
- **No imports** of session_adapter, memory_bridge, or anything else.
- **No exports** — the package is effectively empty at init-time.
- The docstring explicitly deprecates the old get_adapter() accessor and directs users to rom src.hermes.adapter import get_adapter.

### What it used to have (before S1/S2):
Based on the docstring, get_adapter() was previously defined here. It was extracted to dapter.py as a separate module to avoid pulling in session_adapter and memory_bridge at package-init time.

### Present package members:
| Module | Path | Role |
|---|---|---|
| __init__.py | src/hermes/__init__.py | Empty — docstring only |
| dapter.py | src/hermes/adapter.py | get_adapter() singleton factory (S2) |
| session_adapter.py | src/hermes/session_adapter.py | HermesSessionAdapter class (366 lines) |
| memory_bridge.py | src/hermes/memory_bridge.py | Memory bridge |
| safety_plugin.py | src/hermes/safety_plugin.py | Safety plugin |
| plugins/__init__.py | src/hermes/plugins/__init__.py | Plugins sub-package |
| plugins/persona_plugin.py | src/hermes/plugins/persona_plugin.py | Persona plugin |

---

## 4. help.py — Discord References

**File:** src/hermes_plugins/commands_high/help.py (134 lines)

### Discord dependency check
- **No imports from src.discord.commands** — confirmed with zero grep matches.
- **No imports from src.discord** at all — zero grep matches for src\.discord, rom src\.discord, or rom discord\b.
- The only external import is:
  `python
  from src.hermes_plugins.command_catalog import command_categories as _command_categories
  `
  This is the **Hermes-native** catalog, not the old Discord one.

### How it gets command data
- Imports command_categories() (aliased as _command_categories) from command_catalog.py.
- Defines its own private helper _compute_command_count() which sums tuple lengths — a **local re-implementation** (line 71-73), **not** using command_catalog.command_count().
- Categories are displayed using _CATEGORY_DISPLAY mapping (7 categories with emoji names).

### Plugin registration pattern
- Uses _HermesPluginCtx Protocol (lines 20-26) — defines a minimal ctx interface with egister_command.
- The egister(ctx) function (line 115) is the standard Hermes plugin entry point.
- Registers a single /help command that returns markdown-formatted text.

### Note: Local _compute_command_count vs command_catalog.command_count()
help.py defines its own _compute_command_count() that does the same thing as command_catalog.command_count() (sum category tuple lengths). However, it accepts categories as a parameter, so it works with either the catalog's output or a passed-in dict. The _format_help_markdown() function calls _command_categories() (from catalog) to get categories, then passes them to _compute_command_count().

---

## 5. Summary: S1 vs S2 Extraction Boundaries

### S1 (likely extracted):
| What | From | To |
|---|---|---|
| get_adapter() function | hermes/__init__.py | hermes/adapter.py |
| Package-init imports removed | hermes/__init__.py | Deleted from __init__ |

### S2 (likely extracted):
| What | From | To |
|---|---|---|
| command_catalog.py (standalone) | src.discord.commands (mirror) | hermes_plugins/command_catalog.py |
| help.py migrates to catalog | src.discord.cmd_help.py | hermes_plugins/commands_high/help.py |
| _COMMAND_CATEGORIES data | src.discord.commands (assumed) | hermes_plugins/command_catalog.py |

### Remaining old code:
- src/discord/ directory **still exists** with 50 Python files — the old commands, commands.py, cmd_help.py, etc. are still present.
- src/discord/commands.py presumably still has its own copy of the command definitions (which command_catalog.py mirrors).

---

## 6. Key Observations for Phase 7c

1. **command_count() exists in command_catalog.py** — help.py doesn't use it; it re-implements _compute_command_count() locally. This is a minor inconsistency that could be refactored.

2. **adapter.py passes a dummy Redis client** — Redis() (default connection) is passed to HermesSessionAdapter.__init__(), which immediately creates its own DB4 connection. The parameter is dead weight.

3. **hermes/__init__.py is truly empty** — no imports, no re-exports, just a deprecation notice docstring.

4. **Old src/discord/ is untouched** — all 50 files still exist. The Phase 2 migration (S2) extracted only the catalog and help command. The rest of the commands (status, mood, loops, memory, surveillance, finance, system, admin) still live only in src/discord/cmd_*.py as Discord-native slash commands.

5. **help.py has zero Discord imports** — fully migrated to the Hermes plugin system.
