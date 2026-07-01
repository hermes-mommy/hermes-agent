# P16 — Knowledge Graph: Index

**Status:** ✅ COMPLETE (Deployed + Active on VPS)
**Date:** 2026-06-19
**Phase:** Expansion
**ADR:** [ADR-050 — Knowledge Graph Architecture](../../adr/ADR-050-knowledge-graph-architecture.md)

## Summary

Phase 16 introduces a structured knowledge graph layer for Guinevere, enabling
entity-relationship reasoning over memories via pure PostgreSQL RCTE + pgvector.
The graph complements the existing relational memory schema by exposing
traversable relationships (people, places, projects, events, topics) and
supporting multi-hop recall queries integrated as a 4th RRF signal.

**Architecture:** Pure PostgreSQL RCTE (zero external services, bare-metal).
**Sub-repo:** `src/knowledge_graph/` (46 Python files, 8 subdirectories).
**Integration:** 4 production hooks (consolidation, recall, prompt_loader, memory_bridge).
**DB Tables:** 6 tables + 3 views in `memory.kg_*` namespace.

## Directory Structure

```
P16/
├── README.md                    ← You are here
├── plan/                        ← (future)
├── evidence/                    ← Per-step evidence (future)
└── research/                    ← Research artifacts (future)
```

## Production Code Location

| Artifact | Path |
|---|---|
| Package | `src/knowledge_graph/` |
| DB Migration | `migrations/p16_001_kg_schema.sql` |
| ADR | `adr/ADR-050-knowledge-graph-architecture.md` |
| Deployment Report | `evidence/p16-kg/P16-FINAL-DEPLOYMENT-REPORT.md` |

## Progress

| Step | Status | Description |
|---|---|---|
| P16-001 | ✅ | Graph schema + node/edge taxonomy (6 tables, DDL v4, sub-repo skeleton) |
| P16-002 | ✅ | Ingestion pipeline from memory tables (post-consolidation hook, cron 03:30 ICT) |
| P16-003 | ✅ | Query API + multi-hop reasoning (RCTE, PPR, RRF fusion weight=0.20, token budget=1000) |
| P16-004 | ✅ | Backfill strategy + historical migration (checkpoint, resume, rollback) |
| P16-005 | ✅ | Recall evaluation (golden set, metrics, A/B comparison framework) |
| P16-006 | ✅ | Entity resolution/dedup (L1 canonical SHA-256, L2 rapidfuzz, L3 deferred) |
| P16-007 | ✅ | NER+RE extractor (rule-based + LLM hybrid, patterns.py) |
| P16-008 | ✅ | Consent + RLS (manager, RLS policies, audit trail, HARD STOP/DNR) |
| P16-009 | ✅ | Observability (Prometheus metrics, structured logging, tracing) |
| P16-010 | ✅ | Backfill validation (6 integrity checks, coverage metrics) |
| P16-011 | ✅ | Bridge integration (consolidation.py, read_pipeline.py, prompt_loader.py, _memory_bridge.py) |
| P16-012 | ✅ | Adversarial safety tests (consent revocation, tombstone, DNR, HARD STOP, surveillance creep) |

## Integration Hooks (All Active)

| Hook | File | Parameter | Default |
|---|---|---|---|
| Post-consolidation | `src/memory/consolidation.py` | `kg_ingestion_enabled` | `True` |
| Recall RRF signal | `src/memory/read_pipeline.py` | `kg_enabled` | `True` |
| Prompt context | `src/core/services/prompt_loader.py` | `kg_context_enabled` | `True` |
| Bridge enrichment | `src/hermes/_memory_bridge.py` | `kg_enabled` | `True` |

## Key Decisions (Locked by Faiz)

1. Embeddings deferred to P17+ (L1+L2 dedup only)
2. KG RRF weight = 0.20
3. Agent loop integration OUT OF SCOPE for P16
4. Sub-repo: `src/knowledge_graph/`
5. POLE+O + Guinevere extensions taxonomy
6. 50-100 golden test cases (10 sample created)
7. Soft-delete on consent revocation
8. ADR-050 (not ADR-040 — conflict with RBAC slot)
9. Option A: KG derived from `semantic_facts`
10. Full historical backfill

## Bugs Fixed During Deployment: 13

| # | Severity | Bug |
|---|----------|-----|
| 1 | CRITICAL | consolidation.py invalid constructor (6 collaborators missing) |
| 2 | CRITICAL | read_pipeline.py wrong session type |
| 3 | HIGH | prompt_loader.py session closing (BorrowedSession fix) |
| 4 | HIGH | eval/runner.py `# type: ignore` → `cast()` |
| 5 | HIGH | `_EDGE_INSERT_SQL` column name mismatch |
| 6 | HIGH | Missing `await` on `_lookup_facts_from_consolidation` |
| 7 | HIGH | UUID/VARCHAR mismatch → ORM select |
| 8 | MEDIUM | `kg_episode_id` FK violation → set NULL |
| 9 | MEDIUM | Frozen dataclass `KGLogContext` |
| 10 | MEDIUM | `PersonalizedPageRank` constructor mismatch |
| 11 | MEDIUM | `batch_processor.py` `deleted_at` → `deletion_state` |
| 12 | MEDIUM | `batch_processor.py` scalars → ORM objects |
| 13 | MEDIUM | `register_kg_ingestion_job` requires `pipeline` arg |

## Audit Results

| Auditor | Verdict |
|---------|---------|
| Code Quality | ✅ PASS |
| Security + Consent | ✅ PASS (after fixes) |
| Integration Correctness | ✅ PASS |

## VPS State (Post-Deployment)

- `guinevere-core.service`: ACTIVE on :8000
- `guinevere-health-check.service`: PASSING
- KG Cron (03:30 ICT): Registered via APScheduler
- DB: kg_entities=6, kg_edges=3, semantic_facts=5, episodes=3 (test data)
