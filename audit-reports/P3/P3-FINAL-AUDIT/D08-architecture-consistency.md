# P3 FINAL AUDIT — Dimension 8: Architecture Consistency

**Date:** 2026-06-02
**Auditor:** Guinevere (Sisyphus-Junior)
**Scope:** All P3 memory sources + Discord command canonical pattern compliance
**Canonical References:** `cmd_status.py`, `cmd_mood.py`

---

## Overall Verdict: **PASS** (13/13 checkpoints PASS, 0 FAIL)

All 13 architectural consistency checkpoints pass. Memory commands (`cmd_memory_search.py`, `cmd_memory_add.py`) faithfully replicate the canonical Discord command pattern established in `cmd_status.py` / `cmd_mood.py`. Memory pipeline files (`write_pipeline.py`, `read_pipeline.py`) use consistent Protocol-based session interfaces and route all embeddings through `EmbeddingService` (9Router-native). No architectural drift detected.

---

## Checkpoint 1: Discord Command Pattern — Protocol + Frozen Dataclass + importlib

| File | `DiscordEmbedProtocol` | `DiscordEmbedFactory` | `DiscordColourFactory` | `DiscordEmbedModule` | `importlib.import_module("discord")` |
|---|---|---|---|---|---|
| `cmd_status.py` (canonical) | ✓ | ✓ | ✓ | ✓ | ✓ (line 141) |
| `cmd_mood.py` (canonical) | ✓ | ✓ | ✓ | ✓ | ✓ (line 151) |
| `cmd_memory_search.py` | ✓ (line 54) | ✓ (line 76) | ✓ (line 90) | ✓ (line 98) | ✓ (line 111) |
| `cmd_memory_add.py` | ✓ (line 51) | ✓ (line 73) | ✓ (line 87) | ✓ (line 95) | ✓ (line 108) |

**Verdict: PASS**

Both memory commands define the full 4-protocol cascade (`DiscordEmbedProtocol` → `DiscordEmbedFactory` → `DiscordColourFactory` → `DiscordEmbedModule`) identically to the canonical references. The `_get_discord_embed_module()` helper uses `importlib.import_module("discord")` plus double `cast()` — exact same pattern as canonical files.

---

## Checkpoint 2: Discord Interaction Protocols — @runtime_checkable

| File | `DiscordInteractionProtocol` | `DiscordResponseProtocol` | `DiscordFollowupProtocol` | All `@runtime_checkable`? |
|---|---|---|---|---|
| `cmd_status.py` | ✓ (line 179) | ✓ (line 149) | ✓ (line 170) | Yes |
| `cmd_mood.py` | ✓ (line 189) | ✓ (line 159) | ✓ (line 180) | Yes |
| `cmd_memory_search.py` | ✓ (line 149) | ✓ (line 119) | ✓ (line 140) | Yes |
| `cmd_memory_add.py` | ✓ (line 146) | ✓ (line 116) | ✓ (line 137) | Yes |

All protocols have identical method signatures:
- `DiscordResponseProtocol`: `defer(ephemeral)`, `is_done()`, `send_message(**kwargs)`
- `DiscordFollowupProtocol`: `send(**kwargs)`
- `DiscordInteractionProtocol`: `response`, `followup` attributes

**Verdict: PASS**

---

## Checkpoint 3: Frozen Dataclass with `fields: tuple[Field, ...]`

| File | Dataclass Name | `@dataclass(frozen=True)` | `fields` type | Field count |
|---|---|---|---|---|
| `cmd_status.py` | `StatusEmbedData` | ✓ | `tuple[StatusEmbedField, ...]` | 11 default fields |
| `cmd_mood.py` | `MoodEmbedData` | ✓ | `tuple[MoodEmbedField, ...]` | 6 default fields |
| `cmd_memory_search.py` | `MemorySearchEmbedData` | ✓ (line 178) | `tuple[MemorySearchEmbedField, ...]` | Dynamic |
| `cmd_memory_add.py` | `MemoryAddEmbedData` | ✓ (line 175) | `tuple[MemoryAddEmbedField, ...]` | 3 fields |

Both memory dataclasses have:
- `title`, `description`, `color`, `fields`, `footer_text`, `footer_icon`, `timestamp` attributes
- Frozen (`@dataclass(frozen=True)`)
- Default values for all fields
- Companion frozen field dataclass (`MemorySearchEmbedField`, `MemoryAddEmbedField`)

**Verdict: PASS**

---

## Checkpoint 4: `is_faiz_interaction()` Guard

### Implementation (`commands.py` lines 245-256):

```python
def is_faiz_interaction(interaction: object) -> bool:
    guild = getattr(interaction, "guild", None)
    user = getattr(interaction, "user", None)
    owner_id = getattr(guild, "owner_id", None)
    user_id = getattr(user, "id", None)
    return isinstance(owner_id, int) and isinstance(user_id, int) and owner_id == user_id
```

**Key properties verified:**
- No hardcoded user ID ✓
- Fail-closed: returns `False` if any attribute is missing ✓
- Uses runtime attribute access (`getattr`), not static typing ✓
- Compares `guild.owner_id` with `user.id` — Discord's built-in ownership mechanism ✓

### Usage in memory commands:

| File | Import | Guard Check | Line |
|---|---|---|---|
| `cmd_memory_search.py` | `from .commands import is_faiz_interaction` | `if not is_faiz_interaction(interaction): await _send_denied(interaction); return` | 358-362 |
| `cmd_memory_add.py` | `from .commands import is_faiz_interaction` | `if not is_faiz_interaction(interaction): await _send_denied(interaction); return` | 338-342 |

Both files:
- Lazy-import inside the callback function (not at module level) ✓
- Guard is the FIRST check in the callback ✓
- Calls `_send_denied` on failure — identical to canonical pattern ✓

**Verdict: PASS**

---

## Checkpoint 5: Deferred Ephemeral Response → Followup Send Pattern

| File | Defer | Build | Followup | Line Range |
|---|---|---|---|---|
| `cmd_status.py` | `await _defer_ephemeral(interaction)` | `build_status_embed_data()` | `await _followup_send(interaction, embed=embed)` | 386-391 |
| `cmd_mood.py` | `await _defer_ephemeral(interaction)` | `build_mood_embed_data()` | `await _followup_send(interaction, embed=embed)` | 384-389 |
| `cmd_memory_search.py` | `await _defer_ephemeral(interaction)` (line 364) | `build_memory_search_embed_data(results, query)` (line 418) | `await _followup_send(interaction, embed=embed)` (line 420) | 364-420 |
| `cmd_memory_add.py` | `await _defer_ephemeral(interaction)` (line 344) | `build_memory_add_embed_data(episode_id, note)` (line 398) | `await _followup_send(interaction, embed=embed)` (line 403) | 344-403 |

All files use identical helper signatures:
- `_send_denied(interaction)` — handles both `is_done()` and fresh responses
- `_defer_ephemeral(interaction)` — `ephemeral=True`
- `_followup_send(interaction, embed=..., content=...)` — `ephemeral=True`

**Verdict: PASS**

---

## Checkpoint 6: `to_discord_embed(data)` Converter + `build_*_embed_data()` Builder

| File | Builder Function | Converter Function |
|---|---|---|
| `cmd_status.py` | `build_status_embed_data(now=None)` → `StatusEmbedData` | `to_discord_embed(data: StatusEmbedData)` → `DiscordEmbedProtocol` |
| `cmd_mood.py` | `build_mood_embed_data(now=None, mood=DEFAULT_MOOD)` → `MoodEmbedData` | `to_discord_embed(data: MoodEmbedData)` → `DiscordEmbedProtocol` |
| `cmd_memory_search.py` | `build_memory_search_embed_data(results, query, *, now=None)` → `MemorySearchEmbedData` | `to_discord_embed(data: MemorySearchEmbedData)` → `DiscordEmbedProtocol` |
| `cmd_memory_add.py` | `build_memory_add_embed_data(episode_id, note, classification, *, now=None)` → `MemoryAddEmbedData` | `to_discord_embed(data: MemoryAddEmbedData)` → `DiscordEmbedProtocol` |

Common pattern in all converters:
1. Call `_get_discord_embed_module()`
2. Construct `d.Embed(title=..., description=..., colour=d.Colour(...))`
3. Loop over `data.fields` → `embed.add_field(name=..., value=..., inline=...)`
4. Build footer line: `f"{data.footer_text} • {data.timestamp} • {data.footer_icon}"`
5. Return embed

**Verdict: PASS**

---

## Checkpoint 7: `logger.exception()` in Broad Except Handler

| File | Logger Declaration | Exception Handler | Line |
|---|---|---|---|
| `cmd_status.py` | **Not present** | `except Exception:` (no logging) | 392 |
| `cmd_mood.py` | `logger = logging.getLogger(__name__)` | `logger.exception("mood_callback...")` | 391 |
| `cmd_memory_search.py` | `logger = logging.getLogger(__name__)` (line 25) | `logger.exception("memory_search_callback")` | 422 |
| `cmd_memory_add.py` | `logger = logging.getLogger(__name__)` (line 25) | `logger.exception("memory_add_callback")` | 405 |

**Note:** `cmd_status.py` does not log exceptions in its broad except handler. Both memory commands follow `cmd_mood.py`'s more complete pattern — they declare a module-level logger and call `logger.exception()` before sending the degraded fallback. This is an improvement over `cmd_status.py` and is architecturally sound.

**Verdict: PASS** (follows the more complete canonical pattern from `cmd_mood.py`)

---

## Checkpoint 8: Module Ordering Compliance

Canonical ordering: Module docstring → imports → logger → colors → WIB timezone → string constants → embed protocols → interaction protocols → data types → helpers → builder → converter → callback → _send_denied → _defer_ephemeral → _followup_send

### cmd_memory_search.py (493 lines):
| Section | Lines | Status |
|---|---|---|
| Module docstring | 1-16 | ✓ |
| Imports (`from __future__`, stdlib, typing) | 18-23 | ✓ |
| Logger | 25-26 | ✓ |
| Colors import | 28 | ✓ |
| WIB timezone | 31-34 | ✓ |
| String constants | 37-48 | ✓ |
| Embed protocols | 52-112 | ✓ |
| Interaction protocols | 116-157 | ✓ |
| Data types | 161-201 | ✓ |
| Helpers | 205-239 | ✓ |
| Embed Builder | 243-303 | ✓ |
| discord.py Conversion | 307-340 | ✓ |
| Interaction Callback | 344-428 | ✓ |
| _send_denied | 432-457 | ✓ |
| _defer_ephemeral | 460-469 | ✓ |
| _followup_send | 472-493 | ✓ |

### cmd_memory_add.py (487 lines):
| Section | Lines | Status |
|---|---|---|
| Module docstring | 1-16 | ✓ |
| Imports | 18-23 | ✓ |
| Logger | 25-26 | ✓ |
| Colors import | 28 | ✓ |
| WIB timezone | 31-34 | ✓ |
| String constants | 37-45 | ✓ |
| Embed protocols | 49-109 | ✓ |
| Interaction protocols | 113-154 | ✓ |
| Data types | 158-198 | ✓ |
| Helpers | 202-236 | ✓ |
| Embed Builder | 240-283 | ✓ |
| discord.py Conversion | 287-320 | ✓ |
| Interaction Callback | 324-422 | ✓ |
| _send_denied | 426-451 | ✓ |
| _defer_ephemeral | 454-463 | ✓ |
| _followup_send | 466-487 | ✓ |

**Verdict: PASS** — Both files match the canonical ordering exactly.

---

## Checkpoint 9: EmbeddingService Consistency

| File | Import | Usage | Method Called |
|---|---|---|---|
| `cmd_memory_search.py` | `from src.memory.embeddings import EmbeddingService` (line 402) | `EmbeddingService()` lazy init | `embedding_service.aembed()` via recall |
| `cmd_memory_add.py` | `from src.memory.embeddings import EmbeddingService` (line 382) | `EmbeddingService()` lazy init | `embedding_service.aembed()` via store |
| `write_pipeline.py` | `from src.memory.embeddings import (...)` (line 22) | Accepts `EmbeddingClient` Protocol | `service.aembed(text, classification, ...)` |
| `read_pipeline.py` | `from src.memory.embeddings import (...)` (line 30) | Accepts `EmbeddingClient` Protocol | `embedding_service.aembed(text, classification, ...)` |

**Key findings:**
- `EmbeddingService` is instantiated as a singleton (no constructor args) in the Discord commands ✓
- Memory pipeline files accept `EmbeddingClient` protocol — decoupled from concrete class ✓
- The `EmbeddingService.aembed()` async method is used everywhere (not sync `embed()`) ✓
- Classification constants (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`, `CRITICAL`) are re-exported by `write_pipeline.py` and `read_pipeline.py` from `embeddings.py` ✓

**Verdict: PASS**

---

## Checkpoint 10: No Direct OpenAI SDK Usage

Grep pattern `import openai|from openai` across entire `src/` directory: **0 matches.**

The only reference to "openai" anywhere is in `embeddings.py` line 84:
```python
DEFAULT_MODEL = "openai/text-embedding-3-small"
```
This is a MODEL NAME STRING routed through 9Router's OpenRouter-compatible path (`http://localhost:20128/v1`). It is NOT an import of the OpenAI SDK.

**Verdict: PASS**

---

## Checkpoint 11: AsyncSessionProtocol Pattern

| File | Protocol Name | Methods | Definition |
|---|---|---|---|
| `write_pipeline.py` | `EpisodeSession` | `add(obj)`, `async flush()` | Line 70 |
| `read_pipeline.py` | `RecallSession` | `async execute(statement)` → `ScalarResult` | Line 214 |
| `read_pipeline.py` | `ScalarResult` | `scalars()` → `Iterable[EpisodeProtocol]` | Line 206 |
| `read_pipeline.py` | `EpisodeProtocol` | 10 read-only attributes | Line 191 |
| `embeddings.py` | `EmbeddingClient` (via write_pipeline/read_pipeline) | `async aembed(text, classification, ...)` → `list[float]` | Line 80/234 |

Each file defines its own minimal Protocol matching exactly the SQLAlchemy surface it needs:
- **write_pipeline**: Only needs `add()` + `flush()` (WRITE operations) ✓
- **read_pipeline**: Only needs `execute()` → `scalars()` (READ operations) ✓
- No file imports the actual `AsyncSession` type at type-check level ✓
- `consolidation.py` uses `AsyncSessionProtocol` with `execute()` + `__aenter__`/`__aexit__` ✓

**Verdict: PASS** — Protocol-per-use-case pattern is consistent and minimal.

---

## Checkpoint 12: bot.py Wiring

### 12a: `core_names` tuple includes memory commands

```python
# bot.py line 206-209
core_names: tuple[str, ...] = (
    "status", "mood", "help", "safeword",
    "memory-search", "memory-add",
)
```
✓ Both memory-search and memory-add are in `core_names`.

### 12b: `_STUB_PHASE` no longer has memory-search or memory-add

```python
# bot.py lines 43-75
_STUB_PHASE: dict[str, int] = {
    "memory-forget": 3,    # Still stubbed
    "memory-export": 3,    # Still stubbed
    # ... other stubs for P4/P5/P7
}
```
✓ `memory-search` and `memory-add` are NOT in `_STUB_PHASE` — they are wired, not stubbed.

### 12c: `get_session_factory()` lazy init pattern

```python
# bot.py lines 227-258
def get_session_factory(self) -> object:
    if self._session_factory is None:
        database_url = os.environ.get("DATABASE_URL", "")
        if not database_url:
            logger.warning("session_factory_no_database_url")
            return None
        # ... creates async engine + sessionmaker
        logger.info("session_factory_initialized")
    return self._session_factory
```
✓ Lazy init ✓ Returns None when DATABASE_URL not set ✓ Used by both memory commands via `interaction.client.get_session_factory`.

### 12d: Both callbacks imported and registered

```python
# bot.py lines 173-174 (imports)
from .cmd_memory_search import memory_search_callback
from .cmd_memory_add import memory_add_callback

# bot.py lines 196-203 (registration)
self.tree.command(
    name="memory-search",
    description="Search Guinevere's memories by query.",
)(memory_search_callback)
self.tree.command(
    name="memory-add",
    description="Manually add a memory note to Guinevere's store.",
)(memory_add_callback)
```
✓ Both imported ✓ Both registered ✓ Descriptions differ slightly from `commands.py` specs but that's fine (bot descriptions are user-facing, `COMMAND_SPECS` are REST payloads).

**Verdict: PASS**

---

## Checkpoint 13: Metadata-Only Logging

### Discord commands:

| File | Log Call | Raw Content? |
|---|---|---|
| `cmd_memory_search.py` line 422 | `logger.exception("memory_search_callback")` | No — only function name |
| `cmd_memory_add.py` line 405 | `logger.exception("memory_add_callback")` | No — only function name |

### write_pipeline.py:

| Line | Message | Extra Fields | Raw Content? |
|---|---|---|---|
| 215-225 | `"episode_stored"` | `episode_id`, `classification`, `source`, `episode_type`, `has_embedding`, `char_count` | No — only metadata |

### read_pipeline.py:

| Line | Message | Extra Fields | Raw Content? |
|---|---|---|---|
| 479-490 | `"token_budget_trimmed"` | `budget`, `total_before`, `returned_after`, `discarded` | No |
| 834-838 | `"recall_no_results"` | `query_length`, `query_hash` | No — hash, not raw query |
| 892-895 | `"recall_token_budget_empty"` | `budget`, `limit` | No |
| 897-911 | `"recall_complete"` | `query_length`, `query_hash`, `candidates`, `filtered`, `returned`, `principal`, `safe_mode`, `exclude_dnr`, `safe_mode_redacted`, `safe_mode_blocked` | No — all metadata |

**Key privacy compliance:** `read_pipeline.py` uses `hashlib.sha256(query_text).hexdigest()[:16]` to log `query_hash` instead of the raw query text (line 793-796). The `query_length` is also logged instead of the actual content.

**Verdict: PASS**

---

## Checkpoint 14: Channel Lookup Pattern

Neither `cmd_memory_search.py` nor `cmd_memory_add.py` contain any channel lookup code. Grep for `channel|get_channel|channel_id` returned **0 matches** in both files.

This is correct: Discord slash commands operate on the `Interaction` object directly — they respond in the same channel and to the same user that invoked the command. No channel ID lookup is needed.

**Verdict: PASS (N/A — no channel lookup required for slash commands)**

---

## Summary

| # | Checkpoint | Verdict |
|---|---|---|
| 1 | Protocol + frozen dataclass + importlib | PASS |
| 2 | @runtime_checkable interaction protocols | PASS |
| 3 | Frozen dataclass fields tuple | PASS |
| 4 | is_faiz_interaction() guard | PASS |
| 5 | Deferred ephemeral → followup send | PASS |
| 6 | to_discord_embed + build_*_embed_data | PASS |
| 7 | logger.exception() in except handler | PASS |
| 8 | Module ordering compliance | PASS |
| 9 | EmbeddingService consistency | PASS |
| 10 | No direct OpenAI SDK usage | PASS |
| 11 | Protocol-based session interfaces | PASS |
| 12 | bot.py wiring | PASS |
| 13 | Metadata-only logging | PASS |
| 14 | Channel lookup (N/A for slash commands) | PASS |

**Final Verdict: PASS**

### Minor Observations (non-blocking):

1. **`cmd_status.py` does not log exceptions** in its broad `except Exception:` handler (line 392), while `cmd_mood.py` and both memory commands do. This is a minor inconsistency in the canonical references but does not affect the memory commands — they follow the more complete pattern.

2. **`cmd_memory_add.py` has special `WritePipelineCriticalError` handling** (lines 406-422) that goes beyond the canonical pattern. This is a domain-specific enhancement, not a pattern violation.

3. **Session factory access pattern** (`interaction.client.get_session_factory`) is novel to memory commands but is consistent across both `cmd_memory_search.py` and `cmd_memory_add.py`.

### Files Audited:

| File | Lines | Purpose |
|---|---|---|
| `src/discord/cmd_status.py` | 461 | Canonical reference — /status command |
| `src/discord/cmd_mood.py` | 460 | Canonical reference — /mood command |
| `src/discord/cmd_memory_search.py` | 493 | /memory-search command |
| `src/discord/cmd_memory_add.py` | 487 | /memory-add command |
| `src/discord/commands.py` | 291 | Command specs + is_faiz_interaction() |
| `src/discord/bot.py` | 339 | Bot class + wiring |
| `src/memory/embeddings.py` | 775 | EmbeddingService (9Router-native) |
| `src/memory/write_pipeline.py` | 359 | Memory write pipeline |
| `src/memory/read_pipeline.py` | 959 | Memory read/recall pipeline |

### Methodology:

- Full-file read of all 9 source files
- Targeted grep for logging patterns, OpenAI imports, channel lookups, protocol usage
- Side-by-side comparison of canonical pattern vs memory commands
- Line-by-line verification of module ordering