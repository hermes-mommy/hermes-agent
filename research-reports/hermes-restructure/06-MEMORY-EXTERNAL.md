# 06 — Hermes External Memory Providers

> **Date**: 2026-06-04
> **Scope**: All 8 external memory providers available to Hermes Agent — byterover, hindsight, holographic, honcho, mem0, openviking, retaindb, supermemory
> **Series**: Guinevere Hermes NousResearch Migration Assessment
> **Cross-references**: 05-MEMORY-BUILTIN.md, 07-MEMORY-BRIDGE-GAP.md

---

## Executive Summary

Hermes Agent supports **8 external memory providers** that extend the built-in FTS5-based memory with specialized capabilities: vector search, knowledge graph construction, long-term retention, embedding pipelines, and holographic associative memory. These providers are configured via Hermes CLI or config files and operate **alongside** the always-active built-in memory — they supplement, never replace.

The `hermes memory status` command displays all active providers. Guinevere currently uses **none** of these providers, instead running a custom PostgreSQL+pgvector pipeline. This report catalogs each provider's purpose, integration method, capabilities, limitations, and relevance to Guinevere's migration options.

---

## 1. Provider Overview Matrix

| Provider | Memory Type | Search Method | Storage Backend | Integration | PyPI Extra |
|---|---|---|---|---|---|
| **byterover** | Episodic/Conversation | Semantic + keyword | Cloud (ByteRover SaaS) | CLI config | N/A |
| **hindsight** | Episodic/Pattern | LLM-compressed summaries | Cloud (Hindsight SaaS) | CLI config | `hindsight` |
| **holographic** | Associative | Vector + holographic encoding | Local/cloud vector DB | CLI config | N/A |
| **honcho** | User profile + episodic | Semantic + structured query | Cloud (Honcho SaaS) | CLI config | `honcho` |
| **mem0** | Episodic + semantic | Vector similarity | Cloud (Mem0 SaaS) | CLI config | N/A |
| **openviking** | Episodic | FTS + vector (open-source) | Self-hosted (PostgreSQL) | CLI config | N/A |
| **retaindb** | Episodic + structured | Relational query | Self-hosted (PostgreSQL) | CLI config | N/A |
| **supermemory** | Episodic + semantic | Vector + knowledge graph | Cloud (Supermemory SaaS) | CLI config | N/A |

---

## 2. Individual Provider Deep-Dives

### 2.1 byterover

| Attribute | Detail |
|---|---|
| **Purpose** | Episodic memory with conversation-level storage and retrieval |
| **Storage** | ByteRover cloud SaaS |
| **Search** | Semantic similarity + keyword search |
| **Integration** | Configured via Hermes CLI; provider auto-connects at agent startup |
| **Key capability** | Stores full conversation transcripts with metadata; retrieves contextually relevant past conversations |
| **Configuration** | `hermes memory configure byterover` or config file entry |
| **Strengths** | Simple cloud-based setup; no infrastructure to manage |
| **Limitations** | Cloud dependency (latency, availability, data sovereignty); limited to episodic data; no schema customization |
| **Guinevere relevance** | Low — Guinevere already has episodic storage in `memory.episodes` with richer schema (mood, emotional tone, faiz_behavior, importance, tags). ByteRover adds no capability Guinevere lacks. |
| **Data sovereignty** | Data leaves VPS to ByteRover cloud — violates Guinevere's self-hosted/data-sovereignty requirement |

### 2.2 hindsight

| Attribute | Detail |
|---|---|
| **Purpose** | Pattern extraction from episodic memory; LLM-compressed summaries |
| **Storage** | Hindsight cloud SaaS |
| **Search** | Summarized pattern lookup; compression-based retrieval |
| **Integration** | CLI config + PyPI extra `hindsight` (`pip install hermes-agent[hindsight]`) |
| **Key capability** | Uses LLM to compress raw conversations into structured patterns and retrievable summaries. Builds a "hindsight layer" of distilled knowledge. |
| **Configuration** | `hermes memory configure hindsight` or config file entry |
| **Strengths** | LLM-powered summarization reduces token waste on raw transcripts; pattern extraction enables abstract recall |
| **Limitations** | Cloud dependency; additional LLM cost per compression pass; summaries may lose nuance; data sovereignty concerns |
| **Guinevere relevance** | Moderate — Guinevere's auto-store uses naive `content[:200]` truncation for summaries (see gap G10 in `hermes-phase2/04-memory-injection-gap.md`). Adopting Hindsight's LLM-based summarization approach (even if not the Hindsight SaaS itself) would improve summary quality. However, Guinevere's `key_insights` JSONB column and `summary` field in `memory.episodes` already serve a similar purpose. |
| **Data sovereignty** | Data leaves VPS to Hindsight cloud |

### 2.3 holographic

| Attribute | Detail |
|---|---|
| **Purpose** | Associative/holographic memory with vector encoding |
| **Storage** | Local or cloud vector database |
| **Search** | Vector similarity with holographic associative encoding |
| **Integration** | CLI config |
| **Key capability** | Holographic memory encoding allows retrieval of associated memories through partial cues — like recalling a whole conversation from a single keyword. Different from standard vector search because associations are explicitly encoded. |
| **Configuration** | `hermes memory configure holographic` |
| **Strengths** | Associative recall superior to pure vector search for context reconstruction; can retrieve linked memory chains |
| **Limitations** | New/experimental technology; unclear production maturity; may require significant compute for encoding |
| **Guinevere relevance** | Low-to-moderate — Guinevere's `memory.episodes` has `related_ids UUID[]` for cross-referencing episodes, which provides explicit association. Holographic encoding would add implicit associative discovery. However, the technology's maturity for production use is uncertain. |
| **Data sovereignty** | Depends on self-hosted vs cloud deployment |

### 2.4 honcho

| Attribute | Detail |
|---|---|
| **Purpose** | User profile construction + episodic memory with semantic query |
| **Storage** | Honcho cloud SaaS |
| **Search** | Semantic similarity + structured user profile queries |
| **Integration** | CLI config + PyPI extra `honcho` (`pip install hermes-agent[honcho]`) |
| **Key capability** | Builds and maintains a structured user profile (derived user identity) alongside episodic memory. Can answer "what does the agent know about this user?" with structured data. |
| **Configuration** | `hermes memory configure honcho` |
| **Strengths** | Dedicated user profile storage; structured queries for profile data; semantic search across episodes |
| **Limitations** | Cloud dependency; profile construction is Honcho-managed (less control); data sovereignty concerns |
| **Guinevere relevance** | Moderate — Guinevere has `memory.faiz_profile` (encrypted preferences), `faiz_behavior` JSONB in episodes, and behavioral prediction in the memory schema. Honcho's user profile model is simpler but more integrated with Hermes. Guinevere's profile system is more comprehensive (encrypted, consent-aware, surveillance-integrated) but harder to query because it spans multiple tables. |
| **Data sovereignty** | Data leaves VPS to Honcho cloud — **critical violation** for `memory.faiz_profile` which contains encrypted intimate data |

### 2.5 mem0

| Attribute | Detail |
|---|---|
| **Purpose** | Episodic + semantic memory with vector similarity search |
| **Storage** | Mem0 cloud SaaS |
| **Search** | Vector similarity (embedding-based) |
| **Integration** | CLI config |
| **Key capability** | Stores and retrieves memories using embeddings for semantic similarity. Adds vector search capability on top of Hermes built-in FTS5. |
| **Configuration** | `hermes memory configure mem0` |
| **Strengths** | Drop-in semantic search; no embedding pipeline to manage; cloud-hosted vector DB |
| **Limitations** | Cloud dependency; no customization of embedding model; limited to what Mem0's API exposes; data sovereignty concerns |
| **Guinevere relevance** | Low — Guinevere already has pgvector with 1536-dim embeddings (via `text-embedding-3-small`), HNSW indexing, and custom embedding pipeline in `src/memory/embeddings.py`. Mem0 would be a downgrade from Guinevere's existing vector search capability (when embeddings are functional). |
| **Data sovereignty** | Data leaves VPS to Mem0 cloud |

### 2.6 openviking

| Attribute | Detail |
|---|---|
| **Purpose** | Episodic memory with FTS + vector search, self-hosted |
| **Storage** | Self-hosted PostgreSQL |
| **Search** | FTS + vector (pgvector-compatible) |
| **Integration** | CLI config |
| **Key capability** | Open-source, self-hosted episodic memory. Uses PostgreSQL with pgvector for hybrid search (FTS + vector). Closest to Guinevere's existing architecture. |
| **Configuration** | `hermes memory configure openviking` with PostgreSQL connection details |
| **Strengths** | Self-hosted (data sovereignty preserved); PostgreSQL+pgvector matches Guinevere's stack; open-source; no cloud dependency |
| **Limitations** | Requires PostgreSQL infrastructure (already present); may duplicate functionality Guinevere already has; schema may differ from Guinevere's 47-table design |
| **Guinevere relevance** | **High** — OpenViking is the most architecturally aligned provider. Both use PostgreSQL+pgvector for hybrid FTS+vector search. Key question: does OpenViking's schema add capabilities Guinevere lacks, or would it be redundant? |
| **Data sovereignty** | Fully self-hosted — data stays on VPS |
| **Migration fit** | Strong candidate for hybrid approach — could replace or complement Guinevere's `memory.episodes` while staying within the PostgreSQL ecosystem |

### 2.7 retaindb

| Attribute | Detail |
|---|---|
| **Purpose** | Episodic + structured memory with relational query capability |
| **Storage** | Self-hosted PostgreSQL |
| **Search** | Relational SQL queries + FTS |
| **Integration** | CLI config |
| **Key capability** | Provides structured, queryable memory with relational schema. Unlike flat episodic stores, RetainDB supports JOINs, aggregations, and complex filtering. |
| **Configuration** | `hermes memory configure retaindb` |
| **Strengths** | Self-hosted (data sovereignty); relational queries enable complex memory analysis; PostgreSQL-native |
| **Limitations** | Requires PostgreSQL; schema is RetainDB-defined (may not match Guinevere's); no mentioned vector search support |
| **Guinevere relevance** | **High** — RetainDB's relational approach mirrors Guinevere's 47-table design. Both support structured queries. However, Guinevere's schema is purpose-built for its domain (persona, surveillance, financial, projects, consent) — RetainDB's generic schema would lack these specialized domains. RetainDB could serve as a simpler alternative for teams that don't need Guinevere's full schema complexity. |
| **Data sovereignty** | Fully self-hosted |

### 2.8 supermemory

| Attribute | Detail |
|---|---|
| **Purpose** | Episodic + semantic memory with knowledge graph construction |
| **Storage** | Supermemory cloud SaaS |
| **Search** | Vector similarity + knowledge graph traversal |
| **Integration** | CLI config |
| **Key capability** | Builds a knowledge graph from episodic memories, enabling graph-based traversal queries (e.g., "find all conversations related to project X through any connection path"). Combines vector search with graph relationships. |
| **Configuration** | `hermes memory configure supermemory` |
| **Strengths** | Knowledge graph enables relationship discovery beyond keyword/vector matching; graph traversal for multi-hop memory queries |
| **Limitations** | Cloud dependency; knowledge graph construction may be slow for large datasets; more complex than pure vector search; data sovereignty concerns |
| **Guinevere relevance** | Moderate — Guinevere's `memory.semantic_facts` table stores triplets (subject-predicate-object) which form a basic knowledge graph, and `memory.episodes.related_ids` provides explicit episode linking. Supermemory would add automatic graph construction and traversal. However, Guinevere's existing triplet store (when populated) provides similar capability with better data sovereignty. |
| **Data sovereignty** | Data leaves VPS to Supermemory cloud |

---

## 3. Provider Selection Decision Matrix

| Criteria | byterover | hindsight | holographic | honcho | mem0 | openviking | retaindb | supermemory |
|---|---|---|---|---|---|---|---|---|
| **Self-hosted** | No | No | Optional | No | No | Yes | Yes | No |
| **Vector search** | Partial | No | Yes | Yes | Yes | Yes | No | Yes |
| **FTS** | Partial | No | No | No | No | Yes | Yes | No |
| **Structured schema** | No | No | No | Yes (profile) | No | Partial | Yes | Yes (graph) |
| **Knowledge graph** | No | No | Associative | No | No | No | No | Yes |
| **LLM summarization** | No | Yes | No | No | No | No | No | No |
| **Open source** | Unknown | Unknown | Unknown | Unknown | No | Yes | Yes | No |
| **Guinevere stack match** | Low | Low | Low | Low | Low | **High** | **High** | Low |
| **Data sovereignty** | Violated | Violated | Conditional | Violated | Violated | Preserved | Preserved | Violated |

---

## 4. How External Providers Interact with Built-in Memory

### 4.1 Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Hermes AIAgent                        │
│                                                         │
│  ┌──────────────────────────────────────────────────┐   │
│  │            Memory Orchestrator                    │   │
│  │                                                  │   │
│  │  ┌──────────────┐  ┌──────────────┐              │   │
│  │  │  Built-in    │  │  External    │              │   │
│  │  │  (Always On) │  │  Providers   │              │   │
│  │  │              │  │  (Configured)│              │   │
│  │  │  MEMORY.md   │  │  honcho      │              │   │
│  │  │  USER.md     │  │  mem0        │              │   │
│  │  │  FTS5        │  │  openviking  │              │   │
│  │  │  sessions    │  │  ...etc      │              │   │
│  │  └──────────────┘  └──────────────┘              │   │
│  │                                                  │   │
│  │  Memory status = built-in + active externals     │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

### 4.2 Interaction Rules

1. **Built-in is always active** — External providers cannot disable MEMORY.md/USER.md/FTS5.
2. **Providers are additive** — Each configured provider contributes its own memory store and search capability.
3. **Query fanout** — When the agent needs to recall, it queries all active providers in parallel (or cascading — implementation-dependent).
4. **Result merging** — Results from multiple providers are merged. Deduplication strategy is implementation-specific.
5. **Provider priority** — If multiple providers return conflicting information about the same topic, Hermes applies its own conflict resolution (specifics undocumented).
6. **Memory status** — `hermes memory status` lists all active providers with their health/connection status.

### 4.3 Configuration Patterns

```bash
# CLI-based configuration
hermes memory configure honcho
hermes memory configure openviking

# Check active providers
hermes memory status
# Expected output: built-in (always active), honcho (connected), openviking (connected)

# Config file pattern (hermes config)
# memory:
#   providers:
#     honcho:
#       api_key: ${HONCHO_API_KEY}
#     openviking:
#       connection_string: postgresql://...
```

---

## 5. Guinevere's Current Position vs External Providers

### 5.1 What Guinevere Already Has (No Provider Needed)

| Capability | Guinevere Implementation | Closest Provider | Provider Would Be Downgrade? |
|---|---|---|---|
| Episodic storage | `memory.episodes` with 20+ columns | byterover, openviking, retaindb | Yes — Guinevere's schema is richer |
| Vector search | pgvector HNSW, 1536-dim | mem0, openviking | No — but equivalent functionality |
| FTS | TSVECTOR + GIN index | openviking, retaindb | No — equivalent |
| User profile | `memory.faiz_profile` (encrypted) | honcho | Yes — Guinevere's is encrypted and consent-aware |
| Semantic facts | `memory.semantic_facts` triplets | supermemory | Partial — knowledge graph vs triplets |
| Classification | 5-level classification system | None | Guinevere has no equivalent provider |
| DNR | mark/unmark/verify pipeline | None | Guinevere has no equivalent provider |
| Hybrid ranking | RRF fusion (vector+FTS+recency) | None | Guinevere has no equivalent provider |
| Encryption | Encrypted profile + redaction pipeline | None | Guinevere has no equivalent provider |

### 5.2 What Guinevere Lacks (External Provider Could Fill)

| Gap | Best Provider Match | Alternative |
|---|---|---|
| LLM-based summarization | hindsight | Build custom LLM summarization in write_pipeline.py |
| Knowledge graph traversal | supermemory | Extend `memory.semantic_facts` with graph queries |
| Automatic skill creation from experience | None (Hermes core feature) | Requires re-enabling Hermes memory |
| Session-level browsing/scrolling | None (Hermes built-in session_search) | Build custom session browser on memory.episodes |

---

## 6. Recommendations

### 6.1 Do Not Adopt Cloud Providers

**All cloud-based providers (byterover, hindsight, honcho, mem0, supermemory) are incompatible with Guinevere's requirements:**

- **Data sovereignty**: Guinevere's VPS is self-hosted by design. Sending memory data to external SaaS violates architectural principles.
- **Faiz profile data**: `memory.faiz_profile` contains encrypted intimate data. Sending this to any cloud provider is a **BLOCKING** violation.
- **Surveillance data**: `surveillance.*` schemas contain real-time activity data that must never leave the VPS.
- **Cost**: Cloud providers add ongoing SaaS costs on top of existing infrastructure.

### 6.2 Evaluate Self-Hosted Providers

| Provider | Recommendation |
|---|---|
| **openviking** | **Strong candidate** — PostgreSQL+pgvector matches Guinevere's stack. Evaluate whether OpenViking's schema adds capabilities Guinevere lacks or if it would be redundant. If OpenViking provides better Hermes integration (agent can natively query it), adoption could simplify the memory bridge. |
| **retaindb** | **Candidate for simplification** — If Guinevere ever wants to reduce schema complexity (47 tables is heavy), RetainDB offers a simpler relational model. However, this would mean losing specialized schemas (persona, surveillance, financial). Not recommended for current architecture. |
| **holographic (self-hosted)** | **Monitor** — Holographic associative memory is promising for future capabilities, but technology maturity is unclear. Not recommended for immediate adoption. |

### 6.3 Recommended Path

```
Phase 1 (Current): Keep PostgreSQL+pgvector as sole memory backend
                   keep skip_memory=True
                   keep custom memory bridge

Phase 2 (Near-term): Evaluate OpenViking for Hermes-native integration
                     Keep Guinevere's schema as primary
                     Use OpenViking only if it improves agent-native memory access

Phase 3 (Future): Add LLM-based summarization to write_pipeline
                  (inspired by Hindsight's approach, but self-hosted)
                  Extend semantic_facts with graph traversal
                  (inspired by Supermemory's approach, but PostgreSQL-native)
```

---

## 7. Footer

| Field | Value |
|---|---|
| Report | 06-MEMORY-EXTERNAL.md |
| Series | Guinevere Hermes NousResearch Migration Assessment |
| Date | 2026-06-04 |
| Status | Complete |
| Sources | Hermes Agent official docs, Hermes CLI `hermes memory status` research, Guinevere Memory Schema v2.0, Guinevere source code (embeddings.py, read_pipeline.py, write_pipeline.py, session_adapter.py), Hermes Phase 2 research reports |