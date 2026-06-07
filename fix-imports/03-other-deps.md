# Other Deprecated Module Usages — Remaining Import Map

**Scope**: All 7 modules (`bot`, `startup`, `guild_setup`, `permissions`, `intents`, `session_adapter`, `memory_bridge`) excluding `_embed_helpers.py` and `commands.py` (handled separately).

**Method**: Direct grep of absolute imports (`from src.discord.X`, `import src.discord.X`, `from src.hermes.X`) plus relative imports within `src/discord/`.

---

## 1. `src.discord.bot` (D01) — Bot Entrypoint

### Production (absolute imports)

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No production file imports `src.discord.bot` via absolute path | ✅ |

**Note**: `bot.py` itself is the main entry point. Other production files reference it only in docstrings (shadow_pipeline.py, shadow_monitor.py, hermes_conversational.py, cmd_safeword.py, startup.py), not as code imports.

### Tests

| File | Line | Import | Replaceable? |
|------|------|--------|-------------|
| `tests/discord/test_bot.py` | 32 | `from src.discord.bot import GuinevereBot` | ❌ — Tests the main bot class |
| `tests/discord/test_bot.py` | 260 | `from src.discord.bot import main` | ❌ — Tests entrypoint |
| `tests/discord/test_bot.py` | 269 | `from src.discord.bot import main` | ❌ — Tests entrypoint |
| `tests/discord/test_bot.py` | 295 | `from src.discord import bot` | ❌ — Module-level style check |

### Verdict

**🔴 RED — 4 test import sites.** `bot.py` is the runtime entrypoint; it will likely persist indefinitely (not archived). Its dependencies (startup.py, intents.py, conversational_handler.py) need extraction. `test_bot.py` must be rewritten alongside any bot.py refactor.

---

## 2. `src.discord.startup` (D06) — On-Ready Startup Logic

### Production

| File | Line | Import | Kind | Status |
|------|------|--------|------|--------|
| `src/discord/bot.py` | 489 | `from .startup import on_ready as startup_on_ready` | Function-local import inside `async def on_ready()` | 🔴 RED |

No absolute import of `startup` exists in production code.

### Tests

| File | Line | Import | Replaceable? |
|------|------|--------|-------------|
| `tests/discord/test_startup.py` | 18 | `from src.discord.startup import (STARTUP_DESCRIPTION, STARTUP_FOOTER, ...)` (7 symbols) | ❌ — Dedicated test file |
| `tests/discord/test_startup.py` | 289 | `from src.discord.startup import on_ready` | ❌ |
| `tests/discord/test_startup.py` | 303 | `from src.discord.startup import on_ready` | ❌ |
| `tests/discord/test_startup.py` | 318 | `from src.discord.startup import on_ready` | ❌ |
| `tests/discord/test_startup.py` | 334 | `from src.discord.startup import on_ready` | ❌ |
| `tests/discord/test_startup.py` | 349 | `from src.discord.startup import on_ready` | ❌ |
| `tests/discord/test_startup.py` | 369 | `from src.discord import startup` | ❌ |
| `tests/discord/test_bot.py` | 167 | `import src.discord.startup` | ❌ — Validates import |

### Verdict

**🔴 RED — 9 import sites total (1 production + 8 test).** `bot.py` calls `startup.on_ready()` inside its `on_ready()` method. Cannot archive `startup.py` without extracting `on_ready` into `bot.py` directly or a new non-deprecated module. `test_startup.py` (7 sites) + `test_bot.py` (1 site) will fail.

---

## 3. `src.discord.guild_setup` (D05) — Guild Configuration Constants

### Production

| File | Line | Import | Kind | Status |
|------|------|--------|------|--------|
| `src/discord/permissions.py` | 18 | `from src.discord.guild_setup import CHANNELS, get_token` | Top-level module import | 🟡 YELLOW |

### Tests

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No test file imports `guild_setup` | ✅ |

### Verdict

**🟡 YELLOW — Inter-deprecated chain.** The only importer of `guild_setup.py` is `permissions.py` (D04), which is itself in the deprecated set. No external source or test file imports it directly. Can be archived together with permissions.py once other blockers are resolved.

---

## 4. `src.discord.permissions` (D04) — Discord Permission Helpers

### Production

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No production file imports `permissions` via absolute or relative path | ✅ |

### Tests

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No test file imports `permissions` | ✅ |

### Verdict

**🟢 GREEN — No external dependents.** `permissions.py` only imports from `guild_setup.py` (both deprecated). Safe to archive alongside `guild_setup.py` in a combined batch. No test impact.

---

## 5. `src.discord.intents` (D08) — Discord Intents Builder

### Production

| File | Line | Import | Kind | Status |
|------|------|--------|------|--------|
| `src/discord/bot.py` | 24 | `from .intents import get_intents` | **Top-level module import** | 🔴 RED |

### Tests

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No test file imports `intents` | ✅ |

### Verdict

**🔴 RED — Top-level import in bot.py.** `get_intents` is imported at module level in `bot.py:24` and called during `GuinevereBot.__init__`. Cannot archive without inlining the logic or moving to a new module. No test impact (0 sites).

---

## 6. `src.hermes.session_adapter` (D09) — Hermes Session Adapter

### Production

| File | Line | Import | Kind | Status |
|------|------|--------|------|--------|
| `src/hermes/adapter.py` | 24 | `from .session_adapter import HermesSessionAdapter` | `TYPE_CHECKING`-only block | 🟢 GREEN |
| `src/hermes/adapter.py` | 40 | `from .session_adapter import HermesSessionAdapter` | Lazy deferred inside `get_adapter()` function body | 🟢 GREEN |
| `src/hermes/__init__.py` | — | No import (clean — verified) | — | ✅ |

### Tests

| File | Line | Import | Status |
|------|------|--------|--------|
| *(none)* | — | No test file imports `session_adapter` directly | ✅ |

### Verdict

**🟢 GREEN — Already safely deferred.** All imports are in `adapter.py` only: one in `TYPE_CHECKING` (no runtime dep) and one lazy function-local import (only triggers on first call). The `__init__.py` is clean. No test impact. `session_adapter.py` can be archived independently after verifying `get_adapter()` behavior.

---

## 7. `src.hermes.memory_bridge` (D10) — Hermes Memory Bridge

### Production

| File | Line | Import | Kind | Status |
|------|------|--------|------|--------|
| `src/discord/hermes_conversational.py` | 132 | `from src.hermes.memory_bridge import HermesMemoryBridge` | Lazy import inside `_get_memory_bridge()` function | 🔴 RED |
| `src/discord/conversational_handler.py` | 155 | `from src.hermes.memory_bridge import HermesMemoryBridge` | Lazy import inside `_get_memory_bridge()` function | 🔴 RED |

### Tests

| File | Line | Import | Status |
|------|------|--------|--------|
| `tests/hermes/test_memory_bridge.py` | 15 | `from src.hermes.memory_bridge import HermesMemoryBridge` | ❌ — Dedicated test file |
| `tests/hermes/test_memory_bridge.py` | 321 | `@patch("src.hermes.memory_bridge._logger")` | ❌ — Mock path reference |

### Verdict

**🔴 RED — 2 active production + 2 test sites.** Both conversational handlers (`hermes_conversational.py` — the new one, and `conversational_handler.py` — the legacy one) import `HermesMemoryBridge` at function scope. `hermes_conversational.py` is a **non-deprecated** file that pulls in a deprecated module. Must replace with `GuinevereMemoryProvider` before archive. `test_memory_bridge.py` will also fail.

---

## Summary Table

| Module | File | Prod Absolute | Prod Relative | Test Sites | Blocker Severity |
|--------|------|:---:|:---:|:---:|:---:|
| `src.discord.bot` | D01 | 0 | — | 4 | 🔴 RED (4 test) |
| `src.discord.startup` | D06 | 0 | 1 (bot.py:489) | 8 | 🔴 RED (1 prod + 8 test) |
| `src.discord.guild_setup` | D05 | 1 (perms.py:18) | 0 | 0 | 🟡 YELLOW (inter-dep only) |
| `src.discord.permissions` | D04 | 0 | 0 | 0 | 🟢 GREEN (no external deps) |
| `src.discord.intents` | D08 | 0 | 1 (bot.py:24, top-level) | 0 | 🔴 RED (top-level import) |
| `src.hermes.session_adapter` | D09 | 0 | 2 (TYPE_CHECKING + lazy) | 0 | 🟢 GREEN (safely deferred) |
| `src.hermes.memory_bridge` | D10 | 3 (2 prod + 1 @patch) | 0 | 2 (1 file) | 🔴 RED (2 prod + 2 test) |

### Total Import Sites: 24

- **Production absolute**: 4 (`guild_setup` 1 + `memory_bridge` 3)
- **Production relative**: 3 (`startup` 1 + `intents` 1 + `session_adapter` 2)
- **Test absolute**: 16 (`bot` 4 + `startup` 8 + `memory_bridge` 4)

### RED Count: 4 modules (bot, startup, intents, memory_bridge)

| # | Module | Prod Sites | Test Sites | Safe Replacement Exists? |
|---|--------|:---:|:---:|:---|
| 1 | `startup.py` | 1 (bot.py) | 8 | ❌ — Must inline or extract `on_ready` logic |
| 2 | `intents.py` | 1 (bot.py, top-level) | 0 | ❌ — Must inline or extract `get_intents` |
| 3 | `memory_bridge.py` | 2 (both conversational handlers) | 2 | ⚠️ — `GuinevereMemoryProvider` exists as replacement target |
| 4 | `bot.py` | 0 (self) | 4 | N/A — entrypoint, not archive-target |

### YELLOW Count: 1 module (guild_setup) — inter-deprecated chain with permissions.py

### GREEN Count: 2 modules (permissions, session_adapter) — no external live dependents

---

## Dependency Graph (Collapsed)

```
bot.py (D01, entrypoint)
├── .intents → D08  [TOP-LEVEL] 🔴
├── .startup → D06  [function-local] 🔴
└── .conversational_handler → D02 [function-local] 🔴

hermes_conversational.py (non-deprecated, but used in production)
└── src.hermes.memory_bridge → D10  [function-local] 🔴

conversational_handler.py (D02, deprecated)
└── src.hermes.memory_bridge → D10  [function-local] 🔴

permissions.py (D04, deprecated)
└── src.discord.guild_setup → D05  [top-level] 🟡

adapter.py (non-deprecated, production)
├── .session_adapter (TYPE_CHECKING) → D09  🟢
└── .session_adapter (lazy) → D09  🟢
```

---

## Key Takeaways

1. **Only `permissions` (D04) and `session_adapter` (D09) are safe to archive right now** — zero external production dependents, zero test impact.

2. **`guild_setup` (D05) can be archived together with `permissions`** — they depend only on each other (inter-deprecated).

3. **Three RED modules require bot.py refactoring first**: `intents.py` (top-level), `startup.py` (function-local), and `conversational_handler.py` (excluded scope but same source file). Until `bot.py` stops importing them, they cannot be archived.

4. **`memory_bridge.py` (D10) has the most actionable path**: Replace its import in `hermes_conversational.py` (new handler, non-deprecated) with `GuinevereMemoryProvider`. The import in `conversational_handler.py` (deprecated) will be automatically resolved when that file is archived.

5. **Test file impact**: 5 test files will break (already documented in `01-remaining-imports.md`). `test_bot.py` (4 sites) and `test_startup.py` (8 sites) are the largest.
