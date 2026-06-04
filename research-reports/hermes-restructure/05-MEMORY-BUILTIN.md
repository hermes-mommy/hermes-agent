# 05 — Hermes Built-in Memory Architecture

> **Date**: 2026-06-04
> **Scope**: Hermes Agent native memory subsystem — MEMORY.md, USER.md, FTS5, context compression, session search
> **Series**: Guinevere Hermes NousResearch Migration Assessment
> **Cross-references**: 06-MEMORY-EXTERNAL.md, 07-MEMORY-BRIDGE-GAP.md, 08-MCP-NATIVE.md

---

## Executive Summary

Hermes Agent ships with a file-based, always-active persistent memory system built on SQLite FTS5. It consists of two core files (`MEMORY.md` and `USER.md`), a full-text search engine, session-level search capabilities, and an automatic context compression mechanism. The built-in memory is **always active** — external memory providers supplement rather than replace it. Guinevere currently **disables** this entire subsystem via `skip_memory=True` in `session_adapter.py:132`, replacing it with a custom PostgreSQL+pgvector pipeline.

This report catalogs the full Hermes built-in memory architecture: its components, configuration, runtime behavior, and strengths/limitations relative to Guinevere's requirements.

---

## 1. Component Architecture

### 1.1 System Diagram

```
Hermes Built-in Memory
├── MEMORY.md          ── Persistent key-value store for agent self-knowledge
├── USER.md            ── Persistent key-value store for user profile data
├── FTS5 Engine        ── SQLite full-text search across all memory content
├── Session Search     ── Cross-session lookup via session_search tool
├── Context Compression ── Automatic token budget management (50% threshold)
└── Memory Status      ── Introspection command for active providers
```

### 1.2 Storage Backend

| Attribute | Value |
|---|---|
| Database engine | SQLite (local file) |
| Search index | FTS5 (full-text search 5) |
| Primary files | `~/.hermes/MEMORY.md`, `~/.hermes/USER.md` |
| Session store | `~/.hermes/state.db` (SQLite) |
| Session index | `~/.hermes/sessions/sessions.json` |

The SQLite database stores per-session data: session ID, source platform, user ID, session title, model name and configuration, system prompt snapshot, full message history (role, content, tool calls, tool results), token counts, timestamps, and parent session ID.

---

## 2. MEMORY.md and USER.md

### 2.1 MEMORY.md — Agent Self-Knowledge

MEMORY.md is a file-based persistent memory store that Hermes reads and writes during operation. It holds:
- Agent self-knowledge and learned facts
- Skill libraries created from experience
- Persistent notes the agent chooses to save across sessions
- Key insights extracted from conversations

The format is markdown-based, appended and updated by Hermes autonomously. The agent decides what to persist based on importance signals and conversation context.

### 2.2 USER.md — User Profile

USER.md stores accumulated knowledge about the user:
- User preferences and behavioral patterns
- Personal details learned over time
- Relationship context and history
- Behavioral predictions built across sessions

### 2.3 Always-Active Principle

Both MEMORY.md and USER.md are **always active** regardless of external memory provider configuration. The `hermes memory status` command shows built-in memory as permanently enabled alongside any configured external providers. This design means external providers cannot disable or replace the built-in layer — they can only extend it.

### 2.4 Command Interface

```bash
# Show memory status (built-in + external providers)
hermes memory status

# Built-in memory is always listed as active
# External providers show their configured state
```

---

## 3. Context Compression Mechanism

### 3.1 Configuration Parameters

| Parameter | Default | Description |
|---|---|---|
| Compression threshold | 50% | Trigger compression when context reaches 50% of model window |
| Compression target | 20% | Reduce context to 20% of model window after compression |
| Protected messages | Last 20 | Most recent 20 messages are never compressed |
| Enabled by default | Yes | Context compression is active unless explicitly disabled |

### 3.2 Operational Behavior

```
Context Window Usage
─────────────────────────────────────────────────────────────
████████████████████████░░░░░░░░░░░░░░░░░  Normal operation
██████████████████████████████░░░░░░░░░░░  Approaching threshold
██████████████████████████████████████░░░░  >50% → compression triggered
████████░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  After compression (20% target)
████████  ← last 20 messages (always protected)
```

1. Hermes monitors total token consumption against the model's context window.
2. When context exceeds the 50% threshold, compression activates.
3. The compression target is 20% of the model's context window.
4. The most recent 20 messages are **never** compressed — this is a hard protection boundary.
5. Older messages are summarized/compressed into condensed representations.
6. Compression preserves semantic meaning while reducing token count.

### 3.3 Relevance to Guinevere

Guinevere currently has **no equivalent mechanism**. The `session_adapter.py` prunes conversation history to 20 turns (40 messages) via simple truncation (`_prune_history()` at line 141-156), but has no semantic compression. This means:

- Oldest turns are **discarded entirely** rather than summarized
- The 20-turn window is a fixed limit, not adaptive to context utilization
- With GPT-5.5's 1M token context window, 20 turns is only ~2.5% utilization — extremely conservative

---

## 4. Session Search Capabilities

### 4.1 session_search Tool

Hermes provides a built-in `session_search` tool for cross-session memory lookup:

```python
# Discovery mode — search across all sessions
session_search(query="auth refactor", limit=3)

# Scroll mode — browse within a specific session
session_search(session_id="20260510_174648_805cc2", around_message_id=590803, window=10)

# Browse mode — list recent sessions
session_search()
```

### 4.2 Return Data Structure

Discovery results include per-session metadata:

| Field | Description |
|---|---|
| `session_id` | Unique session identifier |
| `title` | Session title (auto-generated or user-set) |
| `when` | Timestamp of session creation |
| `source` | Platform source (discord, cli, telegram, etc.) |
| `snippet` | Context snippet around the match |
| `bookend_start` | Opening messages of the session |
| `messages` | Matched message content |
| `bookend_end` | Closing messages of the session |
| `match_message_id` | ID of the specific matched message |
| `messages_before` | Messages preceding the match |
| `messages_after` | Messages following the match |

### 4.3 Guinevere Cross-Session Equivalent

Guinevere's equivalent is `memory.episodes` in PostgreSQL, queried via the `recall_memories()` pipeline in `read_pipeline.py`. Key differences:

| Capability | Hermes session_search | Guinevere memory.episodes |
|---|---|---|
| Search method | FTS5 on SQLite | TSVECTOR + GIN on PostgreSQL |
| Semantic search | No (FTS5 only) | Yes (pgvector cosine, when embeddings work) |
| Session boundaries | Hermes-managed sessions | Episode boundaries (started_at/ended_at) |
| Query API | Tool invoked by agent | HTTP/function call via read_pipeline |
| Result format | Session-contextual | Top-N scored episodes with safe_content |
| Conversation scroll | Yes (around_message_id, window) | No |

---

## 5. Memory Configuration

### 5.1 Disabling Memory (What Guinevere Does)

```python
# session_adapter.py:127-138 — Guinevere's AIAgent construction
AIAgent(
    base_url=llm_config["base_url"],
    model=llm_config["model"],
    provider=llm_config["provider"],
    api_key=llm_config.get("api_key", ""),
    skip_memory=True,           # ← ALL built-in memory disabled
    skip_context_files=True,    # ← AGENTS.md loading disabled
    quiet_mode=True,
    max_iterations=1,
    enabled_toolsets=[],
    disabled_toolsets=["*"],    # ← ALL tools disabled
)
```

When `skip_memory=True`:
- MEMORY.md is not read or written
- USER.md is not read or written
- FTS5 search is not performed
- Session search is not available to the agent
- Context compression is not active (but also irrelevant with 20-turn limit)
- The agent operates as a **stateless LLM wrapper** with externally-managed history

### 5.2 Enabling Memory (Hypothetical)

```python
AIAgent(
    model="...",
    skip_memory=False,          # Re-enable built-in memory
    skip_context_files=False,   # Re-enable AGENTS.md context
)
```

If re-enabled, Hermes would:
1. Read MEMORY.md and USER.md at session start
2. Inject accumulated knowledge into the system prompt
3. Update MEMORY.md during/after conversation
4. Perform FTS5 searches for relevant past context
5. Apply context compression when approaching model limits

---

## 6. Strengths and Limitations

### 6.1 Strengths

| Strength | Detail |
|---|---|
| **Zero configuration** | Works out of the box; no database setup, no embedding API keys |
| **Always active** | Cannot be accidentally disabled by external provider misconfiguration |
| **FTS5 performance** | SQLite FTS5 is fast for local single-user workloads |
| **Self-managing** | Agent autonomously decides what to persist and when to compress |
| **File-based portability** | MEMORY.md and USER.md are plain files — backup, version, diff |
| **Session search** | Rich cross-session lookup with scrolling and contextual snippets |
| **Context compression** | Adaptive token budget management; protects recent messages |
| **No external dependencies** | Everything runs locally on SQLite; no PostgreSQL, no vector DB |

### 6.2 Limitations

| Limitation | Detail | Impact on Guinevere |
|---|---|---|
| **No vector search** | FTS5 is keyword-only; no semantic similarity | Cannot do "find conversations about my mood" without exact keywords |
| **Single-user design** | MEMORY.md/USER.md are global; not per-user | No multi-user isolation (Guinevere is single-user anyway) |
| **No classification levels** | All memory is flat; no Public/Internal/Restricted/Confidential/Critical tiers | Cannot enforce data governance policies |
| **No DNR (Do Not Remember)** | No mechanism to mark data as forgettable or verify removal | Cannot comply with consent revocation |
| **No encryption at rest** | MEMORY.md and USER.md are plaintext on disk | Critical/Confidential data is exposed on filesystem |
| **No hybrid ranking** | Search results are single-signal (FTS5) | No RRF fusion, no recency decay, no importance weighting |
| **No structured schema** | Free-form markdown; no enforced schema for facts, episodes, or profiles | Cannot query structured data (e.g., "all conversations where mood=pleased") |
| **No external provider required** | External providers add capabilities but the built-in layer has hard ceilings | Built-in alone cannot meet Guinevere's enterprise requirements |
| **No embedding pipeline** | No way to generate or store vector embeddings | Semantic search impossible without external provider |
| **No retention policy** | No automated expiration or archival of old memories | Data grows unbounded without governance |
| **Agent-managed only** | The agent (not the system) decides what to persist | No systematic guarantee of memory completeness |

---

## 7. Feature Comparison: Hermes Built-in vs Guinevere Current

| Feature | Hermes Built-in | Guinevere Current (PostgreSQL+pgvector) |
|---|---|---|
| **Storage** | SQLite + markdown files | PostgreSQL 47 tables, 12 schemas |
| **Search** | FTS5 keyword only | TSVECTOR+GIN (FTS) + pgvector HNSW (vector) |
| **Semantic search** | No | Yes (1536-dim embeddings, when functional) |
| **Hybrid ranking** | No | RRF fusion (vector + FTS + recency) |
| **Classification** | None (flat) | 5 levels: Public/Internal/Restricted/Confidential/Critical |
| **DNR support** | No | Yes (mark/unmark/verify, guinevere_core only) |
| **Encryption** | None | Faiz profile encrypted; Restricted+ data redacted before embedding |
| **Context compression** | Yes (50% threshold, 20% target) | No (simple truncation to 20 turns) |
| **Session search** | Yes (session_search tool) | Custom via memory.episodes queries |
| **Per-user isolation** | Global only | Per-user via user_id hash |
| **Importance scoring** | Agent-determined | Schema-level importance (1-10) with multiplier in ranking |
| **Recency decay** | No | Yes (90-day half-life exponential decay) |
| **Token budget** | Adaptive (compression-based) | Fixed (400 tokens hardcoded) |
| **Self-managing** | Agent autonomously persists | Write pipeline stores everything programmatically |

---

## 8. Recommendations

### 8.1 Do Not Re-enable Built-in Memory Alone

Re-enabling Hermes built-in memory (`skip_memory=False`) without also addressing Guinevere's enterprise requirements would create a **regression**:

- Lose 5-level classification system
- Lose DNR/consent revocation compliance
- Lose hybrid vector+FTS+recency ranking
- Lose structured schema (47 tables, 12 schemas)
- Lose encryption for sensitive profile data
- Gain context compression (positive)
- Gain session search tool (positive)

### 8.2 Potential Hybrid Approach

The most viable path is to keep Guinevere's PostgreSQL pipeline as the **primary memory system** while selectively adopting Hermes capabilities:

| Adopt from Hermes | How |
|---|---|
| Context compression | Adapt the compression algorithm for Guinevere's pipeline; set at 50% threshold, protect most recent messages |
| Session search | Use Hermes `session_search` for browse/scroll; keep PostgreSQL for structured queries |
| MEMORY.md auto-update | Mirror critical PostgreSQL facts into MEMORY.md as a portable summary |

### 8.3 Risk of Skip-Memory Forever

Keeping `skip_memory=True` indefinitely means Guinevere foregoes:
- Automatic context compression (currently has none)
- Built-in session search capability
- Agent self-improvement loop (skill creation from experience)

However, these are **acceptable tradeoffs** given that Guinevere's PostgreSQL pipeline provides enterprise-grade capabilities (classification, DNR, encryption, hybrid search) that Hermes built-in memory cannot match.

---

## 9. Footer

| Field | Value |
|---|---|
| Report | 05-MEMORY-BUILTIN.md |
| Series | Guinevere Hermes NousResearch Migration Assessment |
| Date | 2026-06-04 |
| Status | Complete |
| Sources | Hermes Agent official docs (hermes-agent.nousresearch.com/docs), Guinevere session_adapter.py, Guinevere read_pipeline.py, Guinevere write_pipeline.py, Hermes Phase 2 research reports |