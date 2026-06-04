# 07 — Memory Bridge Gap Analysis

> **Date**: 2026-06-04
> **Scope**: Side-by-side comparison of Guinevere PostgreSQL+pgvector memory vs Hermes built-in memory; current bridge architecture; gap analysis; migration options with risk assessment
> **Series**: Guinevere Hermes NousResearch Migration Assessment
> **Cross-references**: 05-MEMORY-BUILTIN.md, 06-MEMORY-EXTERNAL.md, 08-MCP-NATIVE.md

---

## Executive Summary

Guinevere maintains a sophisticated enterprise-grade memory system (PostgreSQL + pgvector, 47 tables, 12 schemas, 5 classification levels, DNR pipeline, hybrid ranking) while using Hermes Agent purely as a stateless LLM wrapper (`skip_memory=True`). The current `HermesMemoryBridge` (not yet implemented as a formal class, but functionally embodied across `session_adapter.py`, `read_pipeline.py`, and `write_pipeline.py`) bridges Guinevere's memory with Hermes conversation management.

The fundamental gap is bidirectional: Guinevere has capabilities Hermes lacks (classification, DNR, encryption, structured schemas, hybrid ranking), and Hermes has capabilities Guinevere lacks (context compression, session search tooling, agent self-improvement loop, skill creation). The bridge currently sacrifices Hermes memory capabilities entirely to preserve Guinevere's enterprise requirements — a correct architectural decision given current constraints, but one that leaves value on the table.

This report provides an exhaustive side-by-side comparison, gap register, bridge architecture analysis, three migration options with risk assessment, and a recommended path.

---

## 1. Side-by-Side Architecture Comparison

### 1.1 Storage and Schema

| Dimension | Guinevere (Current) | Hermes Built-in |
|---|---|---|
| **Database** | PostgreSQL 5433 | SQLite `~/.hermes/state.db` |
| **Tables** | 47 across 12 schemas | ~5 (sessions, messages, memory keys, attachments, users) |
| **Schemas** | memory, persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions | Flat (no schema concept) |
| **Vector extension** | pgvector with HNSW index | None (no vector support) |
| **FTS engine** | PostgreSQL TSVECTOR + GIN | SQLite FTS5 |
| **Key tables** | `memory.episodes` (episodic), `memory.semantic_facts` (triplets), `memory.faiz_profile` (encrypted), `memory.procedural_skills`, `memory.emotional_events` | `MEMORY.md` (agent knowledge), `USER.md` (user profile) |
| **Session store** | Redis DB4 (`hermes:session:{user_id}`) | SQLite `state.db` sessions table |
| **Portability** | Requires PostgreSQL+Redis infrastructure | Self-contained SQLite+markdown files |

### 1.2 Search and Retrieval

| Dimension | Guinevere | Hermes |
|---|---|---|
| **Vector search** | pgvector cosine distance (`<=>`), 1536-dim, HNSW index | None |
| **Full-text search** | `plainto_tsquery('english', ...)` with `ts_rank()` | FTS5 with built-in ranking |
| **Hybrid ranking** | RRF fusion (vector + FTS + recency) with both-signal bonus (1.25x) | FTS5 only (single-signal) |
| **Recency decay** | 90-day half-life exponential: `1.0 + 0.10 * exp(-days * ln(2) / 90)` | None |
| **Importance boost** | `0.5 + 0.5 * (importance/10)` multiplier | None |
| **Cross-session search** | `recall_memories()` via `memory.episodes` queries | `session_search(...)` tool with browse/scroll/discover |
| **Semantic similarity** | Yes (when embeddings are functional) | No (keyword-only) |
| **Cross-lingual** | Embedding model is English-biased; FTS uses English tokenizer | FTS5 only (English tokenizer by default) |
| **Both-signal scoring** | 1.25x bonus when episode found by both vector and FTS | N/A (single signal) |

### 1.3 Data Governance and Privacy

| Dimension | Guinevere | Hermes |
|---|---|---|
| **Classification levels** | 5: Public, Internal, Restricted, Confidential, Critical | None |
| **Classification enforcement** | Ceiling-based filtering in recall; Critical fails closed without `sanitized_summary` | None |
| **DNR (Do Not Remember)** | Full pipeline: mark, unmark, verify; guinevere_core principal only | None |
| **Consent revocation** | Integrated with ConsentRevocationPolicy; DNR marking on revocation | None |
| **Encryption** | `memory.faiz_profile` encrypted; embedding redaction for Restricted/Confidential | None (plaintext files) |
| **Privacy guards** | Deterministic regex redaction before embedding API calls | None |
| **Safe mode** | Classification ceiling downgrade (Critical->Internal); safe content building | Not applicable |
| **Audit trail** | `audit.*` schema with operation logging | None |

### 1.4 Memory Types and Richness

| Memory Type | Guinevere Schema | Hermes Equivalent |
|---|---|---|
| Episodic | `memory.episodes` (20+ columns: mood, emotional_tone, faiz_behavior, key_insights, related_ids, tags, importance) | Sessions in SQLite (basic: messages, timestamps, token counts) |
| Semantic | `memory.semantic_facts` (subject-predicate-object triplets, confidence, validation) | MEMORY.md (free-form markdown) |
| Faiz profile | `memory.faiz_profile` (encrypted preferences, behavioral predictions) | USER.md (free-form markdown) |
| Procedural | `memory.procedural_skills` (lessons, best practices, workflows) | Skills library (Hermes native feature, but disabled) |
| Emotional | `memory.emotional_events` (significant moments, subjective experience) | None |
| Persona drift | `persona.drift_log` (evolution tracking, projected future) | None |
| Inner journal | `persona.inner_journal` (private reflections, curated reveals) | None |
| Financial | `financial.*` (transactions, patterns, predictive model) | None |
| Project | `projects.*` (tasks, decisions, technical debt, health) | None |
| Client | `projects.clients` (dossiers, negotiation tactics) | None |
| Social map | `social.social_map` (contacts, call frequency, relationships) | None |
| Surveillance | `surveillance.*` (activity, location, health time-series) | None |

### 1.5 Context Management

| Dimension | Guinevere | Hermes |
|---|---|---|
| **Context compression** | None — simple truncation to 20 turns (40 messages) | Yes — 50% threshold, 20% target, protect last 20 messages |
| **Token budget** | Fixed 400 tokens (hardcoded) | Adaptive (based on model context window) |
| **Total context tracking** | No mechanism; base prompt + history + memories unbounded | Actively monitored against model window |
| **History pruning** | Oldest-first truncation (discards, no summarization) | Compressed summarization (preserves meaning) |
| **System prompt size** | No size check (could be 5000+ tokens) | Included in context tracking |
| **Double budget pass** | Yes — `recall_memories()` applies 400 tokens, then `get_system_prompt_with_context()` applies again (redundant) | Single-pass compression |

---

## 2. Current Bridge Architecture

### 2.1 System Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                    Guinevere Discord Message                     │
│                         (Faiz in #guinevere-chat)                 │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│  conversational_handler.py                                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │  1. DistressDetector → safe_mode_activated                │  │
│  │  2. Mood = "Content" (HARDCODED — GAP)                    │  │
│  │  3. ┌──────────────────────────────────────────────────┐  │  │
│  │     │        MEMORY RECALL (Guinevere Pipeline)         │  │  │
│  │     │  PostgreSQL DB session → recall_memories()        │  │  │
│  │     │    ├─ EmbeddingService.aembed(query) → FAILS      │  │  │
│  │     │    ├─ FTS query (TSVECTOR + GIN)                  │  │  │
│  │     │    ├─ Recency query (started_at DESC)             │  │  │
│  │     │    ├─ RRF fusion (2/3 signals)                    │  │  │
│  │     │    ├─ Classification ceiling filter               │  │  │
│  │     │    ├─ DNR exclusion                               │  │  │
│  │     │    ├─ Safe content building                       │  │  │
│  │     │    └─ Token budget trim (400 tokens)              │  │  │
│  │     └──────────────────────────────────────────────────┘  │  │
│  │  4. System prompt assembly (base + memories + mood)       │  │
│  │  5. ┌──────────────────────────────────────────────────┐  │  │
│  │     │        HERMES CALL (Stateless)                     │  │  │
│  │     │  session_adapter.send_message()                   │  │
│  │     │    ├─ Redis DB4: load conversation history        │  │  │
│  │     │    ├─ AIAgent.run_conversation()                  │  │  │
│  │     │    │   skip_memory=True                            │  │  │
│  │     │    │   disabled_toolsets=["*"]                      │  │  │
│  │     │    │   max_iterations=1                             │  │  │
│  │     │    ├─ Extract final_response                       │  │  │
│  │     │    └─ Redis DB4: save history (TTL 2h)            │  │  │
│  │     └──────────────────────────────────────────────────┘  │  │
│  │  6. ┌──────────────────────────────────────────────────┐  │  │
│  │     │        AUTO-STORE (Guinevere Pipeline)             │  │  │
│  │     │  PostgreSQL DB session → store_episode()          │  │  │
│  │     │    ├─ EmbeddingService.aembed() → FAILS             │  │  │
│  │     │    ├─ store_episode() FAILS entirely               │  │  │
│  │     │    └─ Episode NOT stored (silent failure)          │  │  │
│  │     └──────────────────────────────────────────────────┘  │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

### 2.2 Key Bridge Points

| Component | File | Role | Hermes Memory Touchpoint |
|---|---|---|---|
| `HermesSessionAdapter` | `src/hermes/session_adapter.py` | Stateless LLM wrapper | `skip_memory=True` — ALL Hermes memory disabled |
| `recall_memories()` | `src/memory/read_pipeline.py` | Guinevere memory recall | Bypasses Hermes memory entirely |
| `store_episode()` | `src/memory/write_pipeline.py` | Guinevere memory storage | Bypasses Hermes memory entirely |
| `assemble_system_prompt_with_memory()` | `src/core/services/prompt_loader.py` | Memory injection into system prompt | Injects Guinevere memories, not Hermes memories |
| `EmbeddingService` | `src/memory/embeddings.py` | Embedding generation | Not connected to Hermes at all |
| Redis DB4 | `session_adapter.py` | Conversation history | Replaces Hermes session storage |
| `HermesMemoryBridge` | (Planned, not yet implemented) | Unified bridge API | Would encapsulate all memory operations |

### 2.3 What `skip_memory=True` Disables

```python
# session_adapter.py:127-138
AIAgent(
    skip_memory=True,           # ❌ MEMORY.md read/write
                                # ❌ USER.md read/write
                                # ❌ FTS5 search
                                # ❌ Context compression
                                # ❌ Session search tool
                                # ❌ Skill creation loop
    skip_context_files=True,    # ❌ AGENTS.md loading
    disabled_toolsets=["*"],    # ❌ ALL tools (web, terminal, MCP, etc.)
    max_iterations=1,           # ❌ Multi-turn tool calling
)
```

---

## 3. Gap Register

### 3.1 What Guinevere Has That Hermes Lacks

| ID | Capability | Guinevere Implementation | Hermes Gap | Criticality |
|---|---|---|---|---|
| G-G1 | **5-level classification** | Public/Internal/Restricted/Confidential/Critical with ceiling enforcement | No classification concept | **Critical** — data governance |
| G-G2 | **DNR pipeline** | mark/unmark/verify with principal restrictions | No forget mechanism | **Critical** — consent compliance |
| G-G3 | **Encrypted profile** | `memory.faiz_profile` encrypted; redaction pipeline for Restricted+ data | Plaintext files | **Critical** — privacy |
| G-G4 | **Hybrid ranking** | RRF fusion (vector + FTS + recency) with importance boost | FTS5 only | **High** — recall quality |
| G-G5 | **Rich episodic schema** | 20+ columns: mood, emotional_tone, faiz_behavior, key_insights, related_ids, importance | Basic session metadata | **High** — context richness |
| G-G6 | **Semantic facts** | `memory.semantic_facts` triplets with confidence and validation | Free-form markdown | **High** — structured knowledge |
| G-G7 | **12 specialized schemas** | persona, surveillance, financial, projects, social, agents, consent, security, audit, ops, extensions | Single SQLite database | **High** — domain coverage |
| G-G8 | **Safe mode** | Classification ceiling downgrade + safe content building | Not applicable | **High** — safety |
| G-G9 | **Consent integration** | ConsentRevocationPolicy linked to DNR marking | No consent concept | **High** — compliance |
| G-G10 | **Audit trail** | `audit.*` schema with operation logging | No audit trail | **Medium** — compliance |
| G-G11 | **Multi-dimensional recall** | 6 recall methods (date, FTS, semantic, importance, tag, emotional) | FTS5 only | **Medium** — recall flexibility |
| G-G12 | **Surveillance integration** | `surveillance.*` timeseries data with real-time ingestion | No surveillance concept | **Medium** — context awareness |

### 3.2 What Hermes Has That Guinevere Lacks

| ID | Capability | Hermes Implementation | Guinevere Gap | Criticality |
|---|---|---|---|---|
| G-H1 | **Context compression** | 50% threshold, 20% target, protect last 20 messages | Simple truncation (discards old turns) | **High** — context quality |
| G-H2 | **Session search tool** | `session_search()` with browse/scroll/discover | Custom PostgreSQL queries only | **High** — agent usability |
| G-H3 | **Skill creation loop** | Agent creates skills from experience, self-improves | Disabled entirely | **Medium** — agent capability |
| G-H4 | **Agent-managed memory** | Agent autonomously decides what to persist | Programmatic storage (write_pipeline) | **Medium** — memory relevance |
| G-H5 | **Adaptive token budget** | Based on model context window | Fixed 400 tokens | **Medium** — efficiency |
| G-H6 | **Memory introspection** | `hermes memory status` shows all providers | No unified status command | **Low** — operations |
| G-H7 | **External provider ecosystem** | 8 providers for extensibility | Single custom pipeline | **Low** — flexibility |
| G-H8 | **Self-improving loop** | Skills refine during use, 40% faster repeat tasks | No skill refinement | **Low** — future capability |

### 3.3 Current Bridge Gaps (Operational)

| ID | Gap | Location | Impact | Severity |
|---|---|---|---|---|
| G-B1 | **Embeddings always fail** | `embeddings.py` → 9Router HTTP 400 | Vector recall never works; auto-store silently fails | **Critical** |
| G-B2 | **61s retry latency** | `embeddings.py:382-394` | User waits 1-2 min for failed embedding calls | **Critical** |
| G-B3 | **Auto-store fails entirely** | `write_pipeline.py:181-187` | Conversations not persisted when embedding unavailable | **Critical** |
| G-B4 | **No bridge abstraction** | `conversational_handler.py` | Handler directly orchestrates session_factory, embedding, recall, store | **High** |
| G-B5 | **Double session creation** | `conversational_handler.py:413,537` | Two DB connections per message | **Medium** |
| G-B6 | **Mood hardcoded** | `conversational_handler.py:398` | Always "Content" — no dynamic mood evaluation | **High** |
| G-B7 | **hard_stop_handler not wired** | `conversational_handler.py:414` | HARD STOP protocol relies on DistressDetector, not authoritative handler | **Critical** |
| G-B8 | **Importance hardcoded to 3** | `conversational_handler.py:542` | All auto-stored conversations get same importance | **Medium** |
| G-B9 | **Classification hardcoded Restricted** | `conversational_handler.py:531` | No dynamic classification of content | **High** |
| G-B10 | **Summary is naive truncation** | `conversational_handler.py:535` | `content[:200]` — not a real summary | **High** |
| G-B11 | **No total context window management** | `session_adapter.py` | Base prompt + history + memories unbounded | **High** |
| G-B12 | **Double token budget pass** | `read_pipeline.py` + `prompt_loader.py` | Redundant 400-token check in two places | **Low** |
| G-B13 | **No cross-episode dedup** | `read_pipeline.py` | Same topic in multiple episodes → all injected | **Medium** |
| G-B14 | **Memory format wastes tokens** | `prompt_loader.py:80-102` | No temporal context, importance, or source in injected memories | **High** |
| G-B15 | **EmbeddingService not centralized** | `conversational_handler.py:114-125` | Each handler creates own singleton | **Medium** |
| G-B16 | **No consent check on auto-store** | `conversational_handler.py:525-562` | Conversations auto-stored without per-message consent verification | **High** |

---

## 4. Migration Options

### 4.1 Option A: Keep Custom Bridge (Status Quo + Improvements)

**Description**: Keep `skip_memory=True`, maintain Guinevere's PostgreSQL+pgvector pipeline. Fix operational gaps (embedding failure, auto-store resilience) without changing architectural approach.

**Changes Required**:

| Change | Effort | Impact |
|---|---|---|
| Fix embedding API (direct OpenAI or local model) | Low | Restore vector search |
| Make auto-store resilient to embedding failure | Low | Conversations always persisted |
| Implement `HermesMemoryBridge` class | Medium | Clean abstraction |
| Wire hard_stop_handler | Low | Safety compliance |
| Add dynamic mood evaluation | Medium | Persona richness |
| Implement LLM-based summarization | Medium | Better memory quality |
| Add dynamic classification and importance | Medium | Better data governance |
| Adopt [RECENT MEMORIES] format | Low | Token efficiency (+52%) |
| Increase token budget to 800 | Trivial | Better recall context |
| Add total context window tracking | Medium | Prevent overflow |

**Advantages**:
- Preserves all enterprise capabilities (classification, DNR, encryption, hybrid ranking)
- No migration risk to existing data
- No dependency on Hermes memory subsystem stability
- Full control over memory behavior
- Data sovereignty preserved

**Disadvantages**:
- Foregoes Hermes native capabilities (context compression, session search, skill creation)
- Must independently build features Hermes provides natively
- Bridge maintenance burden (Hermes API changes may break adapter)
- Misses Hermes self-improvement loop entirely

**Risk Assessment**:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Hermes API breaking change | Medium | High | Version pinning; adapter abstraction layer |
| Embedding costs at scale | Medium | Medium | Local embedding model (sentence-transformers) |
| Bridge complexity grows | High | Medium | Extract to `HermesMemoryBridge` class with clear interface |
| Missing Hermes improvements | High | Low | Monitor Hermes releases; adopt selectively |

### 4.2 Option B: Adopt Hermes Memory + Extend

**Description**: Re-enable Hermes memory (`skip_memory=False`), configure external providers for capabilities Guinevere needs, and extend Hermes memory with custom hooks for classification, DNR, and encryption. Migrate PostgreSQL data to Hermes-compatible formats.

**Changes Required**:

| Change | Effort | Impact |
|---|---|---|
| Re-enable `skip_memory=False` | Trivial | All Hermes memory activates |
| Configure openviking or retaindb | Low | PostgreSQL-backed external provider |
| Build classification layer on Hermes | **High** | Custom middleware for classification |
| Build DNR pipeline on Hermes | **High** | Custom middleware for consent |
| Build encryption layer | **High** | Custom encryption wrapper |
| Migrate 47 tables to Hermes schema | **Very High** | Data migration with schema loss |
| Rewrite recall pipeline on Hermes API | **High** | Replace read_pipeline.py |
| Rewrite write pipeline on Hermes API | **High** | Replace write_pipeline.py |
| Rebuild surveillance/financial/projects schemas | **Very High** | Domain schemas have no Hermes equivalent |
| Adopt Hermes context compression | Trivial | Built-in feature activates |

**Advantages**:
- Gains context compression, session search, skill creation
- Gains external provider ecosystem
- Reduces custom code maintenance (Hermes handles memory lifecycle)
- Gains agent self-improvement loop

**Disadvantages**:
- **Loses 5-level classification** — must rebuild from scratch
- **Loses DNR pipeline** — must rebuild from scratch
- **Loses encrypted profile** — must rebuild from scratch
- **Loses 12 specialized schemas** — surveillance, financial, projects, social, persona have no Hermes equivalent
- **Massive migration risk** — 47 tables to different schema
- **Hermes memory API surface is smaller** — less control over memory behavior
- **External provider dependency** — replaces self-contained PostgreSQL architecture

**Risk Assessment**:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Data loss during migration | High | **Critical** | Full backup; phased migration; dual-write period |
| Classification regression | Certain | **Critical** | Custom middleware — complex, fragile |
| DNR/consent regression | Certain | **Critical** | Custom middleware — complex, fragile |
| Surveillance data incompatibility | Certain | **Critical** | No Hermes equivalent for timeseries surveillance |
| Hermes memory API changes | Medium | High | Version pinning |
| External provider availability | Medium | High | Self-hosted providers only (openviking, retaindb) |
| Schema richness loss | Certain | High | 12 schemas condensed to flat Hermes model |

### 4.3 Option C: Hybrid Approach (Recommended)

**Description**: Keep Guinevere's PostgreSQL+pgvector as primary memory backend. Enable Hermes memory in **read-only / supplementary mode**. Use Hermes for context compression, session search, and skill creation while routing all persistent storage through Guinevere's enterprise pipeline.

**Changes Required**:

| Change | Effort | Impact |
|---|---|---|
| Fix embedding API | Low | Restore vector search |
| Make auto-store resilient | Low | Conversations always persisted |
| Implement `HermesMemoryBridge` class | Medium | Clean abstraction |
| Wire hard_stop_handler | Low | Safety compliance |
| Enable Hermes context compression | Low | Adaptive token management |
| Enable Hermes session_search | Low | Cross-session browsing |
| Mirror critical facts to MEMORY.md/USER.md | Medium | Hermes can self-improve from Guinevere data |
| Enable skill creation (read-only memory) | Medium | Agent learns from experience |
| Add total context window tracking | Medium | Combine Guinevere budget + Hermes compression |
| Adopt [RECENT MEMORIES] format | Low | Token efficiency |
| Dynamic mood/classification/importance | Medium | Richer context |
| Keep PostgreSQL as write authority | Trivial | Data sovereignty preserved |

**Architecture**:

```
┌─────────────────────────────────────────────────────────────┐
│                    Hybrid Memory Bridge                       │
│                                                             │
│  ┌──────────────────────────┐  ┌──────────────────────────┐ │
│  │  Guinevere PostgreSQL    │  │  Hermes Memory            │ │
│  │  (PRIMARY — Write Auth)  │  │  (SUPPLEMENTARY — Read)   │ │
│  │                          │  │                          │ │
│  │  • 47 tables, 12 schemas │  │  • MEMORY.md mirror      │ │
│  │  • Classification        │  │  • USER.md mirror        │ │
│  │  • DNR pipeline          │  │  • Context compression   │ │
│  │  • Encryption            │  │  • Session search        │ │
│  │  • Hybrid ranking        │  │  • Skill creation        │ │
│  │  • Audit trail           │  │  • Self-improvement      │ │
│  │  • Surveillance          │  │                          │ │
│  │  • Financial             │  │  Read-only; writes go    │ │
│  │  • Projects              │  │  through Guinevere       │ │
│  └──────────┬───────────────┘  └──────────┬───────────────┘ │
│             │                              │                 │
│             └──────────┬───────────────────┘                 │
│                        │                                     │
│              ┌─────────▼─────────┐                          │
│              │  HermesMemoryBridge│                          │
│              │  recall_for_context│                          │
│              │  store_conversation│                          │
│              │  compress_context  │                          │
│              │  search_sessions   │                          │
│              │  mirror_to_hermes  │                          │
│              └────────────────────┘                          │
└─────────────────────────────────────────────────────────────┘
```

**Advantages**:
- Preserves ALL enterprise capabilities (classification, DNR, encryption, hybrid ranking, 12 schemas)
- Gains context compression — adapt Guinevere's fixed 20-turn window
- Gains session search — supplement PostgreSQL queries with browse/scroll
- Gains skill creation — agent improves from experience (using mirrored MEMORY.md)
- PostgreSQL remains single source of truth — no data sovereignty compromise
- Incremental adoption — can enable Hermes features one at a time
- Rollback safety — can disable Hermes features without data loss

**Disadvantages**:
- Increased complexity (two memory systems to maintain)
- Mirror synchronization overhead (PostgreSQL → MEMORY.md)
- Dual memory model may confuse agent (which memories to trust?)
- Hermes skill creation may be lower quality without full memory access

**Risk Assessment**:

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| Mirror inconsistency | Medium | Medium | Eventual consistency; PostgreSQL always authoritative |
| Agent confused by dual memory | Medium | Medium | Clear system prompt instructions; PostgreSQL priority |
| Mirror performance overhead | Low | Low | Async mirroring; batch updates |
| Hermes writes to memory directly | Medium | High | Configure Hermes memory as read-only; intercept writes |
| Increased code complexity | Medium | Medium | Clean `HermesMemoryBridge` interface; comprehensive tests |
| Skill creation quality degraded | Medium | Low | Monitor skill quality; adjust mirror frequency |

---

## 5. Recommendation: Option C (Hybrid) with Phased Rollout

### 5.1 Phase 1: Fix Critical Gaps (Immediate)

```
Priority: CRITICAL
Duration: 1-2 days
─────────────────────────────────────────
1. Fix embedding API (direct OpenAI or local model)
2. Make auto-store resilient to embedding failure
3. Wire hard_stop_handler through bridge
4. Implement HermesMemoryBridge class
```

### 5.2 Phase 2: Bridge Improvements (Short-term)

```
Priority: HIGH
Duration: 3-5 days
─────────────────────────────────────────
5. Increase token budget to 800
6. Adopt [RECENT MEMORIES] format
7. Add dynamic mood evaluation
8. Implement LLM-based summarization
9. Add total context window tracking
10. Single session lifecycle per message
```

### 5.3 Phase 3: Hermes Supplementary Integration (Medium-term)

```
Priority: MEDIUM
Duration: 5-10 days
─────────────────────────────────────────
11. Enable Hermes context compression (skip_memory=False for compression only)
12. Enable Hermes session_search tool
13. Mirror critical PostgreSQL facts to MEMORY.md (read-only for Hermes)
14. Enable Hermes skill creation with mirrored data
15. Add PostgreSQL → Hermes mirror sync daemon
```

### 5.4 Phase 4: Advanced Features (Long-term)

```
Priority: LOW
Duration: 10-20 days
─────────────────────────────────────────
16. Dynamic classification of auto-stored content
17. Dynamic importance assessment
18. Cross-episode content deduplication
19. Knowledge graph traversal on semantic_facts
20. Full self-improvement loop integration
```

---

## 6. Migration Risk Summary

| Risk | Option A | Option B | Option C |
|---|---|---|---|
| Data loss | None | **High** | None |
| Classification regression | None | **Certain** | None |
| DNR/consent regression | None | **Certain** | None |
| Encryption regression | None | **Certain** | None |
| Surveillance data loss | None | **Certain** | None |
| Operational complexity | Medium | Medium | **High** |
| Bridge maintenance burden | Medium | Low | Medium |
| Missing Hermes capabilities | Permanent | Resolved | Partial |
| Hermes API breaking change | Medium | Medium | Medium |
| Rollback difficulty | Easy | **Very Hard** | Easy |

---

## 7. Footer

| Field | Value |
|---|---|
| Report | 07-MEMORY-BRIDGE-GAP.md |
| Series | Guinevere Hermes NousResearch Migration Assessment |
| Date | 2026-06-04 |
| Status | Complete |
| Sources | Guinevere Memory Schema v2.0, Guinevere source code (session_adapter.py, read_pipeline.py, write_pipeline.py, embeddings.py, conversational_handler.py, prompt_loader.py, auth_matrix.py), Hermes Agent official docs, Hermes Phase 2 research reports (01-current-memory-flow.md, 03-embedding-status.md, 04-memory-injection-gap.md), 05-MEMORY-BUILTIN.md, 06-MEMORY-EXTERNAL.md |
| Recommendation | **Option C (Hybrid)** — Keep PostgreSQL as primary, adopt Hermes for compression/session-search/skills |