---
title: "ADR-050: Knowledge Graph Architecture — PostgreSQL RCTE + pgvector Hybrid"
status: "Accepted"
date: "2026-06-19"
last_modified: "2026-06-19"
owner: "Faiz"
executor: "Guinevere"
format: "MADR with YAML frontmatter"
adr_number: 50
supersedes: "none"
related_adrs: "ADR-007, ADR-008, ADR-009, ADR-024"
phase: "P16 — Knowledge Graph (Expansion)"
risk_level: "HIGH"
tags:
  - knowledge-graph
  - postgresql
  - rcte
  - pgvector
  - memory
  - p16
  - expansion
related_documents:
  - Guinevere_MemorySchema_v2.0.md
  - Guinevere_AgentLoopSpec_v2.0.md
  - Guinevere_Persona_Document_v3.1.md
  - Guinevere_PersonaSafetyPolicy_v1.0.md
  - Guinevere_SurveillanceDataPolicy_v1.0.md
---

# ADR-050: Knowledge Graph Architecture — PostgreSQL RCTE + pgvector Hybrid

## Status

Accepted

## Date

2026-06-19

## Last Modified

2026-06-19

## Deciders

- Faiz (Owner, final approver)
- Guinevere (Executor / autonomous system steward)

## Tags

knowledge-graph, postgresql, rcte, pgvector, memory, p16, expansion

## Risk Level

HIGH

## Supersedes

None. This ADR does not supersede any existing decision. It augments the recall pipeline established by ADR-009 without replacing it.

## Related ADRs

| ADR | Relationship |
|---|---|
| [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md) | PostgreSQL primary storage — KG lives in the same database instance |
| [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md) | Memory encryption boundaries apply to KG fact payloads |
| [`../ADR-009-memory-recall-semantic-search-strategy.md`](../ADR-009-memory-recall-semantic-search-strategy.md) | Hybrid recall pipeline — KG adds a 4th RRF signal at weight 0.20 |
| [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md) | KG fact data classified as Confidential |
| [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md) | HARD STOP and consent boundaries apply to KG operations |
| [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md) | Safe word enforcement halts KG access for the active session |

## Related Documents

| Document | Relationship |
|---|---|
| [`../../Guinevere_MemorySchema_v2.0.md`](../../Guinevere_MemorySchema_v2.0.md) | Parent memory model — KG derived from `semantic_facts` |
| [`../../Guinevere_AgentLoopSpec_v2.0.md`](../../Guinevere_AgentLoopSpec_v2.0.md) | Agent loop context — KG extracted in post-consolidation hook |
| [`../../Guinevere_Persona_Document_v3.1.md`](../../Guinevere_Persona_Document_v3.1.md) | Persona context — KG never surfaces intimate data unprompted |
| [`../../Guinevere_PersonaSafetyPolicy_v1.0.md`](../../Guinevere_PersonaSafetyPolicy_v1.0.md) | Safety boundary for KG extraction and recall |
| [`../../Guinevere_SurveillanceDataPolicy_v1.0.md`](../../Guinevere_SurveillanceDataPolicy_v1.0.md) | KG does not store raw surveillance payloads |
| [`../../evidence/p16-kg/oracle-architecture-review.md`](../../evidence/p16-kg/oracle-architecture-review.md) | Oracle architecture review (486 lines) — basis for Option C acceptance |
| [`../../evidence/p16-kg/p16-001-schema-ddl.sql`](../../evidence/p16-kg/p16-001-schema-ddl.sql) | Schema DDL Draft v4 (440 lines) — 6 kg_* tables |
| [`../../research-reports/p16-kg-patterns.md`](../../research-reports/p16-kg-patterns.md) | KG pattern research |
| [`../../evidence/p16-kg/tech-evaluation-report.md`](../../evidence/p16-kg/tech-evaluation-report.md) | Neo4j / AGE / ArangoDB / pgvector evaluation |
| [`../../research-reports/p16-query-api-multihop.md`](../../research-reports/p16-query-api-multihop.md) | Multi-hop query API research |

## Context

The current recall pipeline (ADR-009) uses a hybrid Reciprocal Rank Fusion (RRF) of three signals: pgvector cosine similarity (semantic), PostgreSQL full-text search (lexical), and a recency/decay score. This works well for finding facts similar to a query, but it cannot reason about relationships between entities, traverse multi-hop connections, or surface graph-shaped context such as "people connected to this person who also use this tool."

The Knowledge Graph (KG) layer adds an entity-relationship view of the same memory. It captures canonical entities (people, projects, tools, concepts), directed edges between them with provenance to source facts, and episodes that ground entities in time. The KG augments recall with a 4th RRF signal at weight 0.20, giving the recall pipeline a graph-shaped channel without displacing the existing vector/FTS/recency fusion.

The existing `memory.knowledge_graph` table from the v1 schema is broken in schema and design: it stores a single nullable relationship column with no entity table, no temporal grounding, no consent hooks, and no audit trail. P16 does not extend this table. It deprecates it to `memory._legacy_knowledge_graph` and introduces six new tables in the `memory.kg_*` namespace.

## Decision Drivers

- **Non-breaking by construction.** When the KG signal is empty (cold start, no relevant entities, or no consent token), the existing recall pipeline must behave exactly as it does today. The KG layer augments recall, never replaces it.
- **Bare-metal PostgreSQL only.** The project runs a single self-hosted PostgreSQL instance on the primary VPS (ADR-007, ADR-027). No Docker, no separate graph service, no JVM, no proprietary backup path. The KG must live in the same database.
- **Consent and safety first.** The KG inherits all consent boundaries from ADR-001, ADR-002, and PersonaSafetyPolicy. HARD STOP must halt KG access in the active session. DNR (Do Not Remember) must prevent KG writes. Consent revocation must soft-delete affected KG rows and audit the deletion. The KG must never store raw surveillance payloads.
- **Sub-repo isolation.** All KG code lives under `src/knowledge_graph/`. No cross-contamination with `src/memory/`, `src/agent_loop/`, or `src/surveillance/`. Public surface is a typed Python module only.
- **Performance bound.** Single-hop PPR scoring must return in under 100ms at p95 on the production dataset. 3-hop traversal must return in under 250ms at p95. These are hard ceilings, not stretch goals.
- **Token budget.** KG context injected into a recall response must not exceed 1000 tokens. Excess must be truncated by edge weight, not silently dropped.
- **Idempotent ingestion.** KG writes are derived from `semantic_facts` and must be safe to re-run on the same source set. A re-run produces the same KG state modulo `ingested_at` timestamps.

## Considered Options

### Option A: Neo4j separate graph database — REJECTED

A standalone Neo4j instance running as a separate service alongside PostgreSQL.

**Why rejected:**

- Separate JVM process consumes 4GB+ RAM baseline on the primary VPS, which has no headroom for it.
- Proprietary backup format requires a separate backup runbook and a separate restore drill; doubles the DR surface area.
- Cross-database consistency between PostgreSQL (source of truth for `semantic_facts`) and Neo4j (derived graph) requires either a CDC pipeline or dual-write coordination, both of which add a failure mode the existing pipeline does not have.
- No pgvector integration; vector signals must round-trip through a second service, adding latency to the 4th RRF signal.
- Operating a second database engine violates the project principle of PostgreSQL-native storage (ADR-007).

### Option B: Apache AGE PostgreSQL extension — REJECTED

A graph database layer inside PostgreSQL using the Apache AGE extension (openCypher, VLE).

**Why rejected:**

- Oracle benchmark on the production-shape workload shows AGE is approximately **290x slower** than the equivalent pure-RCTE query for the same traversal patterns the KG needs.
- AGE uses variable-length edge (VLE) traversal with O(n^k) complexity for k-hop patterns, which does not match the bounded 3-hop practical depth the project needs.
- AGE does not push down predicates into PostgreSQL index plans effectively; the `kg_edges` access path becomes a sequential scan inside the VLE for most realistic queries.
- AGE requires the PostgreSQL extension to be compiled and maintained; it is not in the project's current extension set, and adding it conflicts with the bare-metal minimal-extension principle.
- AGE has no native vector integration; entity embeddings (deferred to P17+) would still need a separate path.

### Option C: Pure-relational RCTE + pgvector hybrid — ACCEPTED

Six new tables in the `memory.kg_*` namespace, traversed by recursive common table expressions (RCTE), scored by an inline personalized PageRank (PPR) approximation, and fused into the existing RRF pipeline as a 4th signal at weight 0.20.

**Why accepted:**

- Zero new services. Zero new infrastructure. Lives in the same PostgreSQL instance ADR-007 already locks in.
- RCTE on properly indexed tables returns the same patterns AGE does, at the speed of the underlying PostgreSQL planner.
- pgvector is already deployed and supported in the existing extension set; entity embeddings (P17+) can land in the same column family without a new dependency.
- Sub-100ms p95 single-hop PPR is achievable on the projected dataset (~50K entities, ~200K edges) with the schema in `evidence/p16-kg/p16-001-schema-ddl.sql`.
- Consent and audit are first-class schema citizens (`kg_consent_audit`, RLS policies on every table), not bolt-ons.
- Backwards-compatible: the 4th RRF signal is empty when no KG rows match, and the existing pipeline continues to behave exactly as it does today.

### Option D: ArangoDB — REJECTED

A multi-model document/graph database running as a separate service.

**Why rejected:**

- Same problems as Neo4j: separate service, separate backup path, separate process to monitor.
- No pgvector integration.
- The project has no prior ArangoDB operational knowledge; introducing a third database engine (after PostgreSQL and Redis) is a poor operational trade.
- The multi-model feature is not needed: the KG is purely graph-shaped, and PostgreSQL with RCTE handles the access pattern natively.

## Decision Outcome

Chosen option: **Option C — Pure-relational RCTE + pgvector hybrid on the existing PostgreSQL instance**.

The KG layer is implemented as six new tables in the `memory.kg_*` namespace, derived from `semantic_facts` via a post-consolidation hook that runs in the same transaction as the source fact writes. The KG augments the ADR-009 recall pipeline as a 4th RRF signal at weight 0.20. The legacy `memory.knowledge_graph` table is renamed to `memory._legacy_knowledge_graph` and frozen; no new code reads from it.

### Schema (six tables)

All tables live in the `memory` schema under the `kg_*` prefix:

| Table | Purpose |
|---|---|
| `memory.kg_entities` | Canonical entities (person, project, tool, concept, place, event). `canonical_key` is unique per `(entity_type, normalized_label)`. Soft-delete via `deleted_at`. |
| `memory.kg_edges` | Directed, typed edges between entities. Each edge carries `fact_id` provenance back to `semantic_facts`, a confidence score, and `valid_from` / `valid_to` temporal bounds. |
| `memory.kg_same_as_edges` | Cross-source entity equivalence (e.g., "Faiz" same-as "Samm"). Used for entity resolution and dedup. |
| `memory.kg_episodes` | Temporal episodes that ground entities in time. Links to `memory.episodes` by `episode_id`. |
| `memory.kg_episode_participants` | Many-to-many between `kg_episodes` and `kg_entities` with a `role` column. |
| `memory.kg_consent_audit` | Append-only audit log of every consent check, every RLS policy evaluation, and every soft-delete triggered by consent revocation. Write-ahead: a KG write does not commit unless the matching audit row commits in the same transaction. |

Full DDL: `evidence/p16-kg/p16-001-schema-ddl.sql` (Draft v4, 440 lines).

### Extraction pipeline

- **L1 exact canonical_key match.** Every incoming `semantic_facts` row carries entity mentions; the L1 pass normalizes each mention and looks up `kg_entities.canonical_key`. Exact match → existing entity, no write.
- **L2 rapidfuzz dedup.** If L1 misses, a rapidfuzz pass against existing `kg_entities` rows in the same `entity_type` bucket finds near-duplicates above a 0.92 threshold. Match → reuse canonical entity.
- **L3 entity embeddings (DEFERRED to P17+).** A `vector(1536)` column on `kg_entities` for semantic dedup and similarity search is explicitly out of scope for P16. The schema reserves the column slot but does not populate it.

### NER and relation extraction

- **P16: rule-based only.** Heuristic patterns over `semantic_facts.subject` / `object` / `context` text using a small library of typed regular expressions and a curated stopword list. No ML model dependency, no Python ML package, no GPU requirement.
- **P17+: GLiNER and spaCy.** Defer to P17+ because (a) the model dependencies are non-trivial, (b) the runtime cost is significant, and (c) P16 first proves the schema and query layer before adding ML extraction.

### Query layer

- **RCTE traversal.** Bounded k-hop traversal (default 3) using recursive CTEs. The recursion depth is hard-capped at 3 in the query; deeper patterns require a new ADR.
- **PPR scoring.** An inline personalized PageRank approximation computed in SQL over a sampled sub-graph. Not a true graph algorithm; a deterministic approximation that ranks entities by their graph proximity to the seed set, weighted by edge confidence.
- **RRF fusion.** PPR-ranked entity lists are expanded to their constituent fact rows and passed to the existing RRF function as a 4th channel at weight 0.20. Existing 3-channel RRF is unchanged.

### Ingestion hook

A post-consolidation hook in the memory write path runs in the same transaction as the `semantic_facts` write. If the hook fails, the transaction rolls back. This guarantees the KG never lags behind its source data. Re-running the hook on the same source set is idempotent: it produces the same KG state except for `ingested_at` timestamps, which are excluded from comparison.

### Consent and audit

- **Row-level security (RLS).** Every `kg_*` table has RLS policies keyed on the session's consent token. A missing or expired token returns zero rows.
- **Consent write-ahead audit.** Every KG write first writes a `kg_consent_audit` row in the same transaction. The write commits only if both the audit row and the data row commit.
- **Soft-delete on consent revocation.** Revocation sets `deleted_at` on affected `kg_entities` and `kg_edges` rows and writes a revocation entry to `kg_consent_audit`. Hard-delete is never used; soft-delete preserves the audit chain.
- **No raw surveillance payloads.** Surveillance-derived facts enter the KG only after they have been transformed into `semantic_facts` rows. The KG never stores raw surveillance text, images, or audio.

## Architecture Overview

```
                ┌─────────────────────────┐
                │     semantic_facts      │
                │  (memory.semantic_facts)│
                └────────────┬────────────┘
                             │ post-consolidation hook
                             │ (same transaction)
                             ▼
        ┌────────────────────────────────────────┐
        │  memory.kg_consent_audit (write-ahead) │
        └────────────────────┬───────────────────┘
                             │ audit row + data row commit together
                             ▼
   ┌──────────────────────────────────────────────────────┐
   │  memory.kg_entities  ◄────  L1 exact + L2 rapidfuzz  │
   │  memory.kg_edges                                      │
   │  memory.kg_same_as_edges                              │
   │  memory.kg_episodes  ◄────  memory.episodes           │
   │  memory.kg_episode_participants                       │
   └──────────────────────────┬───────────────────────────┘
                              │ recall query
                              ▼
                ┌──────────────────────────┐
                │  RCTE traversal (≤3 hop) │
                │  + inline PPR scoring    │
                └──────────────┬───────────┘
                               │ ranked entity list → fact list
                               ▼
                ┌──────────────────────────┐
                │  Existing RRF fuser      │
                │  4 channels:             │
                │  - vector (0.40)         │
                │  - fts    (0.25)         │
                │  - recency(0.15)         │
                │  - KG PPR (0.20)         │  ← NEW
                └──────────────────────────┘
```

## Implementation Steps

Twelve steps, total estimate 17 to 26 person-days. Steps marked `parallel` may run concurrently once their listed dependencies pass. Default for unmarked steps is `sequential`.

| Step | Title | Days | Depends on | Mode | Output path |
|---|---|---|---|---|---|
| P16-001 | Schema DDL: 6 kg_* tables + RLS policies + indexes | 2 | none | sequential | `evidence/p16-kg/p16-001-schema-ddl.sql` |
| P16-002 | Migration runner: rename `knowledge_graph` → `_legacy_knowledge_graph` | 0.5 | P16-001 | sequential | `evidence/p16-kg/p16-002-legacy-rename.sql` |
| P16-003 | `src/knowledge_graph/` package skeleton + typed module surface | 1 | none | parallel | `src/knowledge_graph/__init__.py` |
| P16-004 | L1 exact canonical_key extractor + unit tests | 1 | P16-001, P16-003 | parallel | `src/knowledge_graph/extraction/l1_exact.py` |
| P16-005 | L2 rapidfuzz dedup extractor + unit tests | 1.5 | P16-004 | sequential | `src/knowledge_graph/extraction/l2_rapidfuzz.py` |
| P16-006 | Post-consolidation ingestion hook + transaction guard | 2 | P16-002, P16-005 | sequential | `src/knowledge_graph/ingestion/hook.py` |
| P16-007 | Rule-based NER/RE pipeline (regex + stopwords) + golden tests | 2 | P16-003 | parallel | `src/knowledge_graph/extraction/rule_based_ner.py` |
| P16-008 | Consent write-ahead audit module + soft-delete helpers | 1.5 | P16-001 | parallel | `src/knowledge_graph/consent/audit.py` |
| P16-009 | RCTE traversal queries (1, 2, 3 hop) + explain-plan tests | 2 | P16-001 | parallel | `src/knowledge_graph/query/rcte.py` |
| P16-010 | Inline PPR approximation + scoring tests | 2 | P16-009 | sequential | `src/knowledge_graph/query/ppr.py` |
| P16-011 | RRF 4th-channel integration + 1000-token budget guard | 1.5 | P16-010 | sequential | `src/knowledge_graph/query/rrf_integration.py` |
| P16-012 | End-to-end recall test + perf benchmark (p95 ≤ 100ms / ≤ 250ms) | 2 | P16-006, P16-011 | sequential | `evidence/p16-kg/p16-012-perf-bench.md` |

**Total estimate:** 20 person-days mid-point, range 17 to 26.

## Consequences

### Positive

- Zero new services. Zero new infrastructure. The KG lives in the same PostgreSQL instance the project already operates, monitors, and backs up.
- PostgreSQL-native. The KG uses the same operational tooling as the rest of the project: pg_dump, pgBackRest, Prometheus exporters, vacuum policies.
- Sub-100ms p95 single-hop and sub-250ms p95 3-hop query latency on the projected dataset (~50K entities, ~200K edges).
- Non-breaking. When the KG signal is empty, the existing recall pipeline behaves exactly as it does today. The 4th RRF channel contributes zero to the final score.
- Consent-safe by construction. RLS, write-ahead audit, and soft-delete are schema-level, not application-level guards.
- Future-ready. The `vector(1536)` slot on `kg_entities` is reserved for P17+ entity embeddings without a migration. The RCTE query layer accepts a depth parameter for future expansion.

### Negative

- No true graph algorithms. PPR is an inline approximation, not a full graph-database implementation. Algorithms that require global iteration (Louvain community detection, true PageRank with damping) are not in scope.
- Practical traversal depth is 3 hops. Real graph patterns beyond 3 hops will need a different mechanism (or a different ADR) and are not promised by this design.
- The rule-based NER/RE pipeline has bounded recall. It will miss entity types and relation patterns that a trained model would catch. This is a deliberate trade for P16 simplicity.
- Adding six new tables grows the schema surface. Each new table is an additional target for migrations, vacuum tuning, and RLS policy review.

### Risks

- **R1 — Data drift.** If the post-consolidation hook silently fails on a subset of `semantic_facts` writes, the KG will lag behind its source. Mitigation: hook runs in the same transaction as the source write; hook failure rolls back the source. A daily reconciliation job in P16-012 compares `kg_edges` provenance against `semantic_facts` and alerts on drift.
- **R2 — Embedding gap (P17+).** When entity embeddings land in P17+, the dedup and similarity layers will need to be re-tuned. The L1/L2 pipeline is not affected, but the PPR scoring weights may need recalibration. Tracked as a P17+ task, not a P16 risk.
- **R3 — Token budget pressure.** The 1000-token cap on KG context is tight. If recall sets are large, the truncation by edge weight may drop useful signals. Mitigation: a regression test in P16-012 measures recall quality at the budget cap and fails the build if recall drops more than 5% relative to no-budget recall.
- **R4 — RLS policy drift.** Adding new `kg_*` tables without a matching RLS policy would be a critical data exposure. Mitigation: P16-001 ships RLS policies in the same DDL file as the table; P16-008 adds a startup-time RLS-coverage check that fails fast if any `kg_*` table is missing a policy.
- **R5 — Consent revocation race.** If a revocation arrives mid-ingestion, the soft-delete and the audit row must be consistent. Mitigation: soft-delete and audit row commit in the same transaction; P16-008 includes a concurrent-revocation test.

## Deferred to P17+

The following items are explicitly out of scope for P16 and are reserved for P17 or later:

- **GLiNER NER.** A trained named-entity-recognition model for higher-recall entity extraction.
- **spaCy integration.** Linguistic features (POS tags, dependency parses) for richer relation extraction.
- **Entity embeddings.** A `vector(1536)` column on `kg_entities`, populated by an embedding model routed through 9Router per ADR-005.
- **Agent loop integration.** Hooking KG recall into the 7-phase agent loop (ADR-011) as a first-class context source for planning and decision phases. P16 only proves the schema, extraction, and query layer; agent loop wiring lands in P17+.
- **Advanced multi-hop.** Bounded-relaxation graph retrieval (BFS-RF) and GraphTrace-style chain-of-thought traversal for explainable multi-hop reasoning.
- **SQL/PGQ.** PostgreSQL 19's SQL/PGQ property graph queries (PG19 GA expected around September 2027). When the project's PostgreSQL version is upgraded past PG19, this ADR may be revisited.

## Compliance

### PersonaSafetyPolicy

The KG respects all persona safety boundaries:

- **HARD STOP.** When the active session issues HARD STOP, the KG recall path returns zero rows for the rest of the session. This is enforced at the RLS layer via a session-level consent token that HARD STOP clears.
- **Do Not Remember (DNR).** A DNR marker on a fact prevents the post-consolidation hook from writing any KG rows derived from that fact. The DNR check runs before the L1 extractor and gates the entire extraction pipeline.
- **Consent revocation.** Revoking consent for a fact or a category of facts triggers a soft-delete on all derived `kg_entities` and `kg_edges` rows, with a corresponding `kg_consent_audit` entry. The audit row and the soft-delete commit in the same transaction.

### SurveillanceDataPolicy

The KG does not store raw surveillance data:

- Surveillance-derived inputs enter the KG only as transformed `semantic_facts` rows. The raw payload (text, image, audio) never reaches the KG layer.
- The `kg_consent_audit` table records the consent state at the time of every KG write, providing a complete chain of custody for any surveillance-derived entity or edge.

### ADR-001 / ADR-002

- The KG never outputs content that would violate the ethical boundary policy (ADR-001). The same output filters that apply to the existing recall pipeline apply to KG-augmented recall.
- The safe word (ADR-002) is a global user-autonomy override. KG operations halt immediately on safe-word activation, regardless of the active query or the in-flight extraction.

## Implementation Notes

- Implementation must update the relevant v2.0 source documents (or future superseding specs) if this ADR changes state.
- Accepted ADRs must not be edited in-place for material decision changes; create a superseding ADR instead.
- Proposed ADRs require Faiz approval before they become binding runtime policy.
- Any sub-agent research, implementation summary, audit, or verification used for this ADR must be written to markdown evidence, not returned only inline.
- This ADR introduces the `src/knowledge_graph/` package as a new sub-repo under ADR-009's "Repository and Infrastructure Isolation Policy" exception list. The package must remain isolated from `src/memory/`, `src/agent_loop/`, and `src/surveillance/`; cross-package imports require a new ADR.

## Review Record

- **Date:** 2026-06-19
- **Reviewer:** Faiz (Owner) + Guinevere (Executor)
- **Decision:** Accepted
- **Evidence:**
  - Oracle architecture review: `evidence/p16-kg/oracle-architecture-review.md` (486 lines)
  - Schema DDL Draft v4: `evidence/p16-kg/p16-001-schema-ddl.sql` (440 lines)
  - KG pattern research: `research-reports/p16-kg-patterns.md`
  - Tech evaluation: `evidence/p16-kg/tech-evaluation-report.md` (Neo4j / AGE / ArangoDB / pgvector)
  - Multi-hop query API research: `research-reports/p16-query-api-multihop.md`
- **Notes:**
  - **ADR number is 050, not 041.** ADR-039 through ADR-049 are pre-allocated in the ADR-Index backlog for Prompt Injection, RBAC/ABAC, Secrets Rotation, OpenAPI, Event Schema, ERD, SLO/SLA, Incident Response, Feature Flags, Analytics, and Compliance. ADR-050 is the next free slot.
  - **Legacy table handling.** `memory.knowledge_graph` is renamed to `memory._legacy_knowledge_graph` and frozen. No new code reads from it. A follow-up task in P17+ may drop the legacy table after a 90-day observation window with zero readers.
  - **4th RRF channel weight.** Weight 0.20 is a starting point, not a final value. P16-012 includes a calibration run that may adjust the weight; any change requires a new ADR or a footnote in this one.
  - **Token budget.** 1000 tokens is a hard cap. Truncation order: lowest-edge-weight first, then oldest `valid_from` first, then arbitrary. Truncation is logged in `kg_consent_audit` for observability.
  - **Performance ceilings.** p95 ≤ 100ms (1-hop PPR) and p95 ≤ 250ms (3-hop RCTE) are measured against the projected dataset, not a synthetic benchmark. P16-012 ships the measurement script.
  - **P17+ reservation.** The `vector(1536)` column on `kg_entities` is reserved but not populated in P16. Any P16 code that assumes the column is populated is a scaffold violation.
  - **No type suppression.** Per project-wide policy, P16 code must not use `as any`, `# type: ignore`, `@ts-ignore`, or `@ts-expect-error`. Type safety is enforced at the package boundary.

## Links

- [`../ADR-007-memory-storage-backend-selection.md`](../ADR-007-memory-storage-backend-selection.md)
- [`../ADR-008-memory-encryption-key-management.md`](../ADR-008-memory-encryption-key-management.md)
- [`../ADR-009-memory-recall-semantic-search-strategy.md`](../ADR-009-memory-recall-semantic-search-strategy.md)
- [`../ADR-024-data-governance-classification-policy.md`](../ADR-024-data-governance-classification-policy.md)
- [`../ADR-001-persona-safety-ethical-boundary.md`](../ADR-001-persona-safety-ethical-boundary.md)
- [`../ADR-002-user-autonomy-safe-word-enforcement.md`](../ADR-002-user-autonomy-safe-word-enforcement.md)
- [`../../Guinevere_ADR_Index_v1.0.md`](../../Guinevere_ADR_Index_v1.0.md)
- [`../../Guinevere_MemorySchema_v2.0.md`](../../Guinevere_MemorySchema_v2.0.md)
- [`../../Guinevere_AgentLoopSpec_v2.0.md`](../../Guinevere_AgentLoopSpec_v2.0.md)
- [`../../Guinevere_Persona_Document_v3.1.md`](../../Guinevere_Persona_Document_v3.1.md)
- [`../../Guinevere_PersonaSafetyPolicy_v1.0.md`](../../Guinevere_PersonaSafetyPolicy_v1.0.md)
- [`../../Guinevere_SurveillanceDataPolicy_v1.0.md`](../../Guinevere_SurveillanceDataPolicy_v1.0.md)
- [`../../evidence/p16-kg/oracle-architecture-review.md`](../../evidence/p16-kg/oracle-architecture-review.md)
- [`../../evidence/p16-kg/p16-001-schema-ddl.sql`](../../evidence/p16-kg/p16-001-schema-ddl.sql)
- [`../../research-reports/p16-kg-patterns.md`](../../research-reports/p16-kg-patterns.md)
- [`../../evidence/p16-kg/tech-evaluation-report.md`](../../evidence/p16-kg/tech-evaluation-report.md)
- [`../../research-reports/p16-query-api-multihop.md`](../../research-reports/p16-query-api-multihop.md)
