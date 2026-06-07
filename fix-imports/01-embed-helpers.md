# `_embed_helpers.py` — Current Usage Map

**Date**: 2026-06-06  
**Task**: Map exact current usage of `src/discord/_embed_helpers.py` across `src/` and `tests/`, list all defined functions/classes, identify a safe non-deprecated home.  
**Verdict**: **22 exclusive callers in `src/discord/cmd_*.py` — no test usage, no hermes_plugins usage. No existing non-deprecated home found.**  

---

## 1. File Under Analysis

| Property | Value |
|---|---|
| Path | `src/discord/_embed_helpers.py` |
| Lines | 304 |
| Role | Shared Discord embed protocols, dataclasses, and helper functions for all `cmd_*.py` modules |
| Deprecated | Designated D07 in ADR-035 Phase 7c (not yet archived) |

---

## 2. Functions/Classes Defined (`__all__` = 20 symbols)

| # | Symbol | Kind | Description |
|---|--------|------|-------------|
| 1 | `WIB` | Final[timezone] | Asia/Bangkok/WIB timezone offset (+07:00) |
| 2 | `FOOTER_TEXT` | Final[str] | `"Guinevere de Baroque"` |
| 3 | `DiscordEmbedProtocol` | Protocol | Minimal `discord.Embed` protocol (`add_field`, `set_footer`) |
| 4 | `DiscordEmbedFactory` | Protocol | Callable for `discord.Embed(...)` |
| 5 | `DiscordColourFactory` | Protocol | Callable for `discord.Colour(...)` |
| 6 | `DiscordEmbedModule` | Protocol | Subset of `discord` module (Embed + Colour) |
| 7 | `DiscordResponseProtocol` | Protocol | `discord.Interaction.response` protocol |
| 8 | `DiscordFollowupProtocol` | Protocol | `discord.Interaction.followup` protocol |
| 9 | `DiscordUserProtocol` | Protocol | `discord.User` / `discord.Member` protocol |
| 10 | `DiscordInteractionProtocol` | Protocol | Full `discord.Interaction` protocol |
| 11 | `EmbedField` | @dataclass(frozen=True) | Single embed field definition (`name`, `value`, `inline`) |
| 12 | `EmbedData` | @dataclass(frozen=True) | Deterministic embed data (`title`, `description`, `color`, `fields`, `footer_text`, `footer_icon`, `timestamp`) |
| 13 | `get_discord_module` | function | Dynamic `importlib.import_module("discord")` with typed return |
| 14 | `format_wib_timestamp` | function | Format datetime as `"2026-06-01 15:30 WIB"` |
| 15 | `now_wib_str` | function | Current UTC time formatted as WIB string |
| 16 | `get_option_value` | function | Extract slash-command option value from interaction.data |
| 17 | `to_discord_embed` | function | Convert `EmbedData` → `discord.Embed` object |
| 18 | `send_denied` | async function | Send ephemeral "Hanya Faiz" denial message |
| 19 | `defer_ephemeral` | async function | Defer interaction response ephemerally |
| 20 | `followup_send` | async function | Send ephemeral followup message (with embed/content/file) |

---

## 3. All Usages (Excluding `_deprecated`)

### 3.1 Production Source Files — 22 files, all in `src/discord/`

Every consumer uses the same relative import pattern:
```python
from ._embed_helpers import (
    EmbedData,
    EmbedField,
    defer_ephemeral,
    followup_send,
    now_wib_str,
    send_denied,
    to_discord_embed,
    # get_option_value — imported by subset below
)
```

| # | File | Import Line | Imports `get_option_value`? |
|---|------|-------------|-----------------------------|
| 1 | `src/discord/cmd_approve.py` | 16 | ✅ Yes |
| 2 | `src/discord/cmd_approve_all.py` | 16 | ❌ No |
| 3 | `src/discord/cmd_backup_now.py` | 18 | ❌ No |
| 4 | `src/discord/cmd_casual.py` | 17 | ❌ No |
| 5 | `src/discord/cmd_clear_cache.py` | 20 | ✅ Yes |
| 6 | `src/discord/cmd_consent.py` | 22 | ✅ Yes |
| 7 | `src/discord/cmd_cost_alert.py` | 18 | ✅ Yes |
| 8 | `src/discord/cmd_deny.py` | 16 | ✅ Yes |
| 9 | `src/discord/cmd_evidence.py` | 19 | ✅ Yes |
| 10 | `src/discord/cmd_focus.py` | 17 | ✅ Yes |
| 11 | `src/discord/cmd_health_check.py` | 18 | ❌ No |
| 12 | `src/discord/cmd_history.py` | 17 | ❌ No |
| 13 | `src/discord/cmd_loops.py` | 16 | ❌ No |
| 14 | `src/discord/cmd_loop_pause.py` | 16 | ✅ Yes |
| 15 | `src/discord/cmd_loop_priority.py` | 16 | ✅ Yes |
| 16 | `src/discord/cmd_loop_resume.py` | 16 | ✅ Yes |
| 17 | `src/discord/cmd_memory_export.py` | 19 | ✅ Yes |
| 18 | `src/discord/cmd_memory_forget.py` | 19 | ✅ Yes |
| 19 | `src/discord/cmd_new_session.py` | 17 | ❌ No |
| 20 | `src/discord/cmd_punishment.py` | 22 | ✅ Yes |
| 21 | `src/discord/cmd_restart_service.py` | 20 | ✅ Yes |
| 22 | `src/discord/cmd_reward.py` | 21 | ✅ Yes |

**Summary by symbol usage:**

| Symbol | Used by | Files |
|--------|---------|-------|
| `EmbedData` | 22/22 | All cmd_*.py |
| `EmbedField` | 22/22 | All cmd_*.py |
| `defer_ephemeral` | 22/22 | All cmd_*.py |
| `followup_send` | 22/22 | All cmd_*.py |
| `now_wib_str` | 22/22 | All cmd_*.py |
| `send_denied` | 22/22 | All cmd_*.py |
| `to_discord_embed` | 22/22 | All cmd_*.py |
| `get_option_value` | 14/22 | See table above |

### 3.2 Other `src/discord/` Files — 0 references

| File | References `_embed_helpers`? |
|------|------------------------------|
| `bot.py` | ❌ |
| `commands.py` | ❌ |
| `conversational_handler.py` | ❌ |
| `hermes_conversational.py` | ❌ |
| `startup.py` | ❌ |
| `intents.py` | ❌ |
| `permissions.py` | ❌ |
| `guild_setup.py` | ❌ |

### 3.3 Test Files — 0 references

No test file in `tests/` imports from or references `_embed_helpers.py`.

### 3.4 `src/hermes_plugins/` — 0 references

No hermes_plugins file imports from `_embed_helpers.py`. Hermes plugins define their own local `WIB` timezone constant and `_format_wib_timestamp()` function inline — they do not use any embed-specific symbols (`EmbedData`, `EmbedField`, `to_discord_embed`, `defer_ephemeral`, `followup_send`, `send_denied`) at all.

### 3.5 Research Reports / Evidence Docs — informational only

- `research-reports/phase-7c-execution/01-import-deps.md` — documents the blocker
- `research-reports/phase-7c-b3-b8/01-remaining-imports.md` — re-confirms 22 callers
- `research-reports/phase-7-execution/05-deprecated-files.md` — lists as archive candidate
- `research-reports/p14-expansion/discord-patterns.md` — documents the embed pattern
- `docs/setup-evidence/` — various verification/audit reports reference it
- `stepprompts/StepPrompts.md` — step prompt templates mention it

---

## 4. Existing Non-Deprecated Home — None

| Candidate | Exists? | Notes |
|-----------|---------|-------|
| `src/discord/_embed_utils.py` | ❌ No | **Recommended by prior reports** (Phase 7c B3.1 suggests this name) |
| `src/discord/embed_utils.py` | ❌ No | Untested alternative |
| `src/hermes_plugins/embed_utils.py` | ❌ No | Not suitable — hermes_plugins don't use Discord embed helpers |
| `src/core/embeds.py` | ❌ No | Doesn't exist |
| `src/memory/embeddings.py` | ✅ Exists | Unrelated — this is for vector embeddings, not Discord embeds |

### Recommendation (from prior research reports)

The previous Phase 7c reports consistently recommend extracting `_embed_helpers.py` symbols into a **co-located non-deprecated sibling** at `src/discord/_embed_utils.py`. This preserves the relative import structure (`from ._embed_utils import ...` instead of `from ._embed_helpers import ...`) and avoids entanglement with `src/hermes_plugins/` (which has no Discord embed usage).

---

## 5. Summary

| Metric | Value |
|--------|-------|
| Symbols defined | 20 (`__all__`) |
| Production source callers | 22 (`cmd_*.py`) |
| Test callers | 0 |
| hermes_plugins callers | 0 |
| Other `src/discord/` callers | 0 |
| Cross-package callers | 0 |
| Existing non-deprecated home | ❌ None |
| **Proposed extraction target** | `src/discord/_embed_utils.py` |
| **Import path change** | `from ._embed_helpers import` → `from ._embed_utils import` (22 files) |
| **Risk** | HIGH — 22 files must be updated identically |

---

## Footer

Generated by Sisyphus for Guinevere ADR-035 Phase 7c B3/B8 research. Read-only investigation. No files modified.
