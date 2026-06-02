---
adr: 009
title: "Memory Recall & Semantic Search Strategy"
status: "Accepted with notes"
date: "2026-05-30"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - memory
  - recall
  - pgvector
  - semantic-search
risk_level: "HIGH"
supersedes: "N/A"
related_documents:
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_Persona_Document_v2.0.md
---

# ADR-009: Memory Recall & Semantic Search Strategy

## Status

Accepted with notes

## Date

2026-05-30

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

memory, recall, pgvector, semantic-search

## Risk Level

HIGH

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md) | Guinevere_MemorySchema_v2.0.md |
| [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md) | Guinevere_AgentLoopSpec_v2.0.md |
| [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md) | Guinevere_Persona_Document_v2.0.md |
| [`../ADR-004-primary-llm-model-selection.md`](../ADR-004-primary-llm-model-selection.md) | ADR-004 — Primary LLM Model Selection |
| [`../ADR-005-llm-router-failover-strategy.md`](../ADR-005-llm-router-failover-strategy.md) | ADR-005 — LLM Router & Failover Strategy |
| [`../ADR-006-sub-agent-llm-model-strategy.md`](../ADR-006-sub-agent-llm-model-strategy.md) | ADR-006 — Sub-Agent LLM Model Strategy |
| [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md) | ADR-007 — Memory Storage Backend Selection |
| [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md) | ADR-008 — Memory Encryption & Key Management |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | ADR-024 — Data Governance & Classification Policy |

## Context

The memory schema includes episodic memory, semantic facts, profile memory, emotional events, procedural lessons, and vector embeddings. Recall quality affects persona continuity, coding context, and safety decisions.

This ADR is part of the first Guinevere technical-core ADR batch and inherits these locked project decisions unless explicitly stated otherwise:

- Primary LLM is GPT-5.5 via 9Router with 1M context window.
- Sub-agent LLM is DeepSeek V4 Flash via 9Router.
- All LLM routing goes through 9Router; OpenRouter is not a fallback path.
- Memory uses PostgreSQL primary storage plus Redis cache; SQLite is excluded.
- Autonomous SDLC uses exactly 7 phases: Research; Plan & Delegate; Delegate; Execute; Validate & Audit; Update Documents; Setup Evidence.
- Guinevere MCP native fully replaces OpenCode/opencode for the project coding substrate.
- Prometheus + Grafana run on the primary VPS first.
- Wearable integrations are post-MVP and must not be treated as active dependencies.
- Browser automation uses obscura as primary and Playwright as fallback.

## Decision Drivers

- Canonical v2.0 documentation must remain internally consistent.
- Faiz is the sole owner and final approver; Guinevere may propose and execute but not silently change accepted decisions.
- Safety, consent, privacy, and recoverability outrank persona flavor and automation speed.
- The decision must be auditable through file-based evidence and linked source documents.

## Considered Options

1. Inject all available memory
2. Use only semantic vector search
3. Use layered recall with safety and relevance filtering

## Decision Outcome

Chosen option: **Use layered recall with safety and relevance filtering**.

Use a layered recall strategy combining explicit profile facts, recent working memory, pgvector semantic retrieval, time-weighted episodic memory, safety filters, and task-specific memory contracts. Memory injection must be observable and bounded by relevance, privacy, and token budget.

## Consequences

### Positive

- Improves relevance while controlling token usage
- Supports safety-sensitive memory suppression
- Makes recall evaluation possible

### Negative

- Requires scoring, calibration, and regression tests
- May omit relevant memories if thresholds are wrong

### Risks

- Bad recall can create false intimacy or wrong decisions
- Over-recall can expose private data unnecessarily

## Implementation Notes

- Implementation must update the relevant v2.0 source documents or future superseding specs if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.

## Review Record

- **Date:** 2026-05-30
- **Reviewer:** Senior Architect Reviewer / Guinevere
- **Decision:** Accepted with notes
- **Evidence:** Reviewed against Guinevere_MemorySchema_v2.0.md, Guinevere_AgentLoopSpec_v2.0.md, Guinevere_Persona_Document_v2.0.md, ADR-004, ADR-005, ADR-006, ADR-007, ADR-008, ADR-024, and batch-2 research reports (2026-05-30-adr-batch2-map.md, 2026-05-30-adr-batch2-consistency.md, 2026-05-30-adr-batch2-technical-sanity.md).
- **Notes:**
  - **Embedding model:** Use OpenAI `text-embedding-3-small` with 1536 dimensions. Route through 9Router via OpenRouter backend, consistent with ADR-005. No direct OpenAI API calls unless a future ADR explicitly supersedes this routing policy.
  - **Index type:** HNSW is recommended for production recall quality. IVFFlat may be considered only if vector count exceeds ~1M rows and memory is constrained. HNSW defaults: `m=16` for 1536-dim vectors; `m=32–64` for 1M–10M+ rows; `ef_construction=128–256` during build for graph quality.
  - **Query tuning:** Set `ef_search` to balance recall vs. latency (e.g., 64–128 for production). For IVFFlat, set `probes` to 10–20. Queries must use `ORDER BY embedding <=> query_vector LIMIT N` with `vector_cosine_ops` operator class to ensure index usage.
  - **Vector storage location:** Embeddings stored in PostgreSQL per Guinevere_MemorySchema_v2.0.md (`memory.episodes` and `memory.semantic_facts` columns defined as `vector(1536)`). Naming must align with existing schema.
  - **Evaluation metrics:** Define regression tests for precision@k, recall@k, and MRR on a held-out validation set. Test cadence: per-deploy or weekly.
  - **Token budget cap:** Hard cap on injected memory tokens per recall cycle (e.g., 4,000 tokens) to prevent context window exhaustion.
  - **Operational caveats:**
    - **halfvec:** Plan migration to `halfvec` (16-bit) for memory savings (~50%) with <1% recall loss for `text-embedding-3-small`.
    - **autovacuum:** Tune autovacuum per table; vector index bloat degrades silently without it.
    - **Rate limits:** OpenAI batch embeddings support up to 100 per call. Implement exponential backoff and token-bucket rate limiting to handle HTTP 429.
    - **Dimension lock:** pgvector enforces dimension at write time; changing models later requires table rebuild.
    - **Memory-bound failure:** HNSW indexes must fit in RAM at scale (5M+ vectors) or query latency degrades to disk I/O.

## Links

- [`../Guinevere_MemorySchema_v2.0.md`](../Guinevere_MemorySchema_v2.0.md)
- [`../Guinevere_AgentLoopSpec_v2.0.md`](../Guinevere_AgentLoopSpec_v2.0.md)
- [`../Guinevere_Persona_Document_v2.0.md`](../Guinevere_Persona_Document_v2.0.md)
- [`../Guinevere_ADR_Index_v1.0.md`](../Guinevere_ADR_Index_v1.0.md)
