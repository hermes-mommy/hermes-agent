# Local Embedding Model Constraints — Guinevere Memory System

**File:** `research-reports/P3/local-embedding-constraints.md`
**Date:** 2026-06-02
**Scope:** Binding constraints from local docs, code, schema, budget, privacy/consent, and infrastructure that govern embedding model selection.
**Purpose:** Decide whether to keep ADR-009 `text-embedding-3-small` or switch to a different OpenRouter model, and what schema/ADR changes would be needed.

---

## Executive Summary

The embedding model decision is **already bound** by a dimension lock at `vector(1536)` across two production tables (`memory.episodes`, `memory.semantic_facts`), with HNSW indexes already created at P3-002/P3-003. Any model change to a different dimension requires a **full destructive migration** (ALTER COLUMN → table rebuild → index drop/recreate → re-embed all data). The Oracle architectural judgment (oracle-embedding-model-architecture-review.md) recommends **keeping ADR-009 as-is** and resolving the consent gate. This report confirms that recommendation with evidence from all local constraint sources.

---

## 1. ADR-009 Binding Constraints

**Source:** `adr/ADR-009-memory-recall-semantic-search-strategy.md`

| Constraint | Value | Binding Level |
|---|---|---|
| Embedding model | `text-embedding-3-small` | **Accepted ADR — binding** |
| Dimensions | 1536 | Enforced by pgvector at write time |
| Routing | Via 9Router → OpenRouter backend | ADR-005 routing policy |
| Index type | HNSW (mandatory default) | **Accepted ADR — binding** (IVFFlat deprecated per ERD doc C-002) |
| HNSW parameters | `m=16`, `ef_construction=128` | Coded in src/memory/models.py |
| ef_search | 64–128 for production | Configurable, not hard-bound |
| Dimension lock | pgvector enforces at write time; changing models later requires table rebuild | Explicit operational caveat in ADR-009 |
| halfvec migration | Plan migration to halfvec(1536) for RAM savings (~50%) with <1% recall loss | Recommended but not yet triggered |
| Token budget cap | 4,000 tokens per recall cycle | Hard cap |
| Query method | `ORDER BY embedding <=> query_vector LIMIT N` with `vector_cosine_ops` | Coded in HNSW index DDL |

**Key consequence:** The ADR-009 dimension lock means any model producing non-1536-dimensional embeddings requires a full schema migration. No practical SentenceTransformers or OpenRouter embedding model outputs exactly 1536 dimensions natively — all alternatives are 384, 768, 1024, 2560, 3072, or 4096.

---

## 2. Schema & Migration Constraints

**Sources:** `src/memory/models.py`, `docs/00-core/04-MemorySchema_v2.0.md`, `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md`

### 2.1 Tables with `vector(1536)` columns

| Table | Column | Index | Classification |
|---|---|---|---|
| `memory.episodes` | `embedding vector(1536)` | `ix_episodes_embedding_hnsw` (HNSW, m=16, ef_construction=128) | Inherits source (Restricted) |
| `memory.semantic_facts` | `embedding vector(1536)` | `ix_semantic_facts_embedding_hnsw` (HNSW, m=16, ef_construction=128) | Inherits source (Confidential) |

Confirmed in `src/memory/models.py` lines 118-119 and 179-181: `embedding: Mapped[Optional[list[float]]] = mapped_column(Vector(1536), nullable=True)`.

### 2.2 Migration Impact if Dimensions Change

If switching to any model with non-1536 dimensions, the required changes are:

| Action | Effort | Risk |
|---|---|---|
| `ALTER TABLE memory.episodes ALTER COLUMN embedding TYPE vector(N)` CASCADE | Full table rewrite, drops HNSW index | HIGH |
| `ALTER TABLE memory.semantic_facts ALTER COLUMN embedding TYPE vector(N)` CASCADE | Full table rewrite, drops HNSW index | HIGH |
| Recreate HNSW indexes with adjusted `m` parameter | Index build time proportional to rows | MEDIUM |
| Re-embed all existing rows (both tables) | N batches of 100 with API calls | LARGE |
| Update SQLAlchemy `Vector(N)` in models.py | Code change | LOW |
| Update query pipelines (ef_search may need retuning) | Tuning + benchmark | MEDIUM |

**Total migration effort estimate: 3–5 days** (Oracle judgment).

### 2.3 Existing Migration State

- P3-001: Alembic installed, baseline migration applied
- P3-002: All 47 tables migrated (12 schemas) — verified
- P3-003: 61 indexes including 2 HNSW — verified
- P3-004: MiniLM `all-MiniLM-L6-v2` (384-dim) cached but NOT used for vector(1536) writes

**Current P3 state:** Schema is locked at vector(1536). The MiniLM cache is dimension-incompatible; any attempt to write 384-dim vectors into vector(1536) columns will be rejected by pgvector at write time.

---

## 3. Current Implementation State (P3 Progress)

**Source:** `PROGRESS.md`

| Step | Status | Notes |
|---|---|---|
| P3-001 Alembic setup | PASS | Migration framework ready |
| P3-002 47 tables migration | PASS | 12 schemas, all tables migrated |
| P3-003 Migration verification | PASS | 61 indexes, 2 HNSW, 11 FKs |
| P3-004 SentenceTransformers cache | PASS | MiniLM 384-dim cached, NOT for vector(1536) writes |
| **P3-005 Embedding pipeline** | **BLOCKED** | **Blocked by external embedding privacy consent gate** |
| P3-006 HNSW index tuning | Pending P3-005 | Sequential dependency |
| P3-007 HNSW benchmark | Pending P3-005 | Sequential dependency |
| P3-008 FTS setup | Pending P3-005 | Sequential dependency |
| P3-009 Memory write pipeline | Pending P3-005 | Sequential dependency |
| P3-010 Memory read pipeline | Pending P3-005 | Sequential dependency |
| P3-011 through P3-019 | Pending | All downstream of P3-005 |

**Critical finding:** P3-005 through P3-010 are BLOCKED by the consent gate. Since P3-005 is the embedding pipeline (text → 1536-dim via text-embedding-3-small), no memory recall steps can proceed until the consent gate is resolved.

---

## 4. Privacy/Consent Constraints

**Source:** `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`, `docs/30-data/32-ConsentRevocationPolicy_v1.0.md`

### 4.1 Consent Gate (P3-005 Blocker)

Status: **BLOCKED** — explicit Faiz acknowledgment not yet recorded.

Faiz must choose one of:
1. **Approve** external embedding processing via 9Router/OpenRouter for ADR-009 1536-dimensional embeddings.
2. **Deny** external embedding processing and request a local-only redesign (including ADR/schema changes).
3. **Pause** P3 memory implementation at P3-004.

### 4.2 Privacy Trade-Off Requiring Acknowledgment

The following points require explicit Faiz acknowledgment:
1. Memory text or memory-derived text may leave the Guinevere runtime boundary through the 9Router/OpenRouter embedding path.
2. The text may include Restricted or Confidential memory material unless later filters redact or classify it before embedding.
3. The returned embedding vector is derived data and inherits the highest relevant source classification.
4. The local MiniLM model (P3-004) is 384-dimensional and incompatible with vector(1536) storage.
5. Continuing without this acknowledgment would violate the consent-safety mandate.

### 4.3 Risk Comparison with Existing LLM Path

The Oracle review notes that the embedding API is **lower risk** than existing LLM API calls:
- Embedding calls are **stateless**: OpenAI does not retain or train on text-embedding-3-small inputs per their API data usage policy.
- No conversation is stored, no training on inputs, no retention of prompt content.
- Embedding is a one-shot vector transformation with no memory of prior calls.

### 4.4 Data Classification of Embeddings

Per `docs/30-data/30-DataGovernance_Classification_v1.0.md`: "Derived embeddings and summaries inherit the highest classification of the source unless a documented redaction/anonymization process downgrades them." So `memory.episodes.embedding` inherits Restricted/Critical; `memory.semantic_facts.embedding` inherits Confidential/Restricted/Critical.

---

## 5. Budget Constraints

**Sources:** `PROGRESS.md`, `docs/70-finops/70-Cost_FinOps_Model_v1.1.md`

| Constraint | Value | Source |
|---|---|---|
| Total monthly budget | **$30/month hard cap** | FinOps, AC-FIN-001 |
| P3 memory system budget | **$2/month** | PROGRESS.md |
| text-embedding-3-small cost | **$0.02/1M tokens** (batch: $0.01) | MTEB report |
| Projected monthly embedding cost | **$0.10–$0.50/month** | Oracle judgment |
| Current cumulative spend | **$17/month** (P0=$0 + P1=$15 + P2=$0 + P3=$2) | PROGRESS.md |

**Key finding:** The text-embedding-3-small API cost is negligible at projected volume ($0.10–0.50/mo). Budget is NOT a constraint for keeping ADR-009.

### 5.1 Alternative Model Costs

| Model | $/1M tokens | Monthly est. |
|---|---|---|
| text-embedding-3-small (current) | $0.02 | $0.10–$0.50 |
| qwen/qwen3-embedding-4b | $0.02 | $0.10–$0.50 |
| qwen/qwen3-embedding-8b | $0.01 | $0.05–$0.25 |
| perplexity/pplx-embed-v1-0.6b | $0.004 | $0.02–$0.10 |
| google/gemini-embedding-001 | $0.15 | $0.75–$3.75 |
| baai/bge-m3 (via OpenRouter) | $0.01 | $0.05–$0.25 |

**All alternatives require dimension change** (1024, 2560, 3072, 4096 — none match 1536), so API cost comparison is moot without the schema migration effort.

---

## 6. Infrastructure & RAM Constraints

**Sources:** `docs/00-core/02-TechnicalArchitecture_v2.0.md`, PROGRESS.md

| Resource | Limit | Source |
|---|---|---|
| VPS | Shared 4C/16GB Ubuntu 24.04 | hostdata.id VPS |
| cgroup memory | **8GB** (MemoryMax=8G) | P0-009 systemd slice |
| cgroup CPU | 200% (2 cores) | P0-009 systemd slice |
| PostgreSQL allocation | ~4GB | Technical Architecture v2.0 |

### 6.1 RAM Pressure Analysis

At current zero-vector state, RAM is not a constraint. Projected at scale:

| Vector count | FP32 1536-dim | halfvec(1536) |
|---|---|---|
| 10K | 60 MB | 30 MB |
| 100K | 600 MB | 300 MB |
| 500K | 3 GB | 1.5 GB |
| 1M | 6 GB | 3 GB |
| 3M | 18 GB | 9 GB (exceeds cgroup) |

**Trigger documented in ADR-009:** Migrate to halfvec(1536) when vector count exceeds 3M or when index RAM exceeds 80% of the 8GB cgroup. This is NOT a model change.

### 6.2 Impact of Switching to Local Models

| Model | RAM | Disk | Note |
|---|---|---|---|
| BGE-M3 (568M params) | ~3GB | ~2.2GB | 38% of 8GB cgroup |
| all-MiniLM-L6-v2 (22M) | ~250MB | ~80MB | Poor multilingual, 384-dim |
| multilingual-e5-large (335M) | ~2.5GB | ~1.3GB | 1024-dim |

---

## 7. Current MiniLM Status (P3-004)

- MiniLM `all-MiniLM-L6-v2` (384-dim) downloaded and cached via HuggingFace hub
- Status: **Cache-only, NOT compatible with vector(1536) storage**
- The 384-dim vector CANNOT be inserted into any current vector(1536) column

**Oracle recommendation:** Remove the dimension-mismatched MiniLM path from the primary write pipeline. Keep cached only for a future separate halfvec(384) fallback table if offline capability becomes a hard requirement.

---

## 8. Multilingual Quality Constraints

**Source:** `research-reports/P3/mteb-embedding-benchmarks.md`

### 8.1 Indonesian-English Recall

| Model | MTEB Retrieval | Multilingual |
|---|---|---|
| text-embedding-3-small | ~52.0 (v1) | Limited (English-best) |
| qwen/qwen3-embedding-4b | 69.60 (MMTEB) | ~119 langs |
| google/gemini-embedding-001 | 67.71 (MMTEB) | ~100+ langs |
| perplexity/pplx-embed-v1-4b | 69.66 (MMTEB) | ~100+ langs |

**Oracle's position:** "If Indonesian quality proves insufficient during P3-007 benchmarking (recall@5 < 85%), the correct fix is to add bilingual instruction prefixes or query expansion — not a full model migration."

### 8.2 Precision/Recall Targets

| Memory Type | Precision | Recall |
|---|---|---|
| Episodic | >=90% | >=85% |
| Semantic Facts | >=95% | >=90% |
| Emotional | >=90% | >=85% |
| Faiz Profile | >=95% | >=90% |

These are the quality thresholds the embedding model must support. ADR-009 text-embedding-3-small has not been benchmarked yet (P3-007 not started).

---

## 9. ADR Update Requirements

### 9.1 If Keeping ADR-009 (Recommended Path)

| Change | Required | Effort |
|---|---|---|
| ADR-009 text change | No — accepted as-is | $0 |
| ADR-009 footnote addition | Optional — document dimension lock risk, halfvec trigger | ~10m |
| Schema change | None | $0 |
| SQLAlchemy models change | None | $0 |
| Consent gate resolution | Required — update faiz-consent-embedding-privacy.md | ~10m |
| P3-005 implementation | Unblocked once consent gate lifts | Normal |

### 9.2 If Switching to Non-1536 Model

| Change | Required | Effort |
|---|---|---|
| New ADR | Required — supersede ADR-009 | ~1-2h |
| Schema migration | ALTER COLUMN on two tables | Full table rewrite |
| HNSW index recreate | Drop + recreate with adjusted m | Index build |
| Data migration | Re-embed all rows in batches | Large (3-5 days) |
| SQLAlchemy models | Change Vector(N) | Code change |

---

## 10. Decision Matrix

| Path | Dimensions | Effort | Cost/mo | RAM | ADR Change | Verdict |
|---|---|---|---|---|---|---|
| **A. Keep ADR-009** | 1536 | **None** | ~$0.10-0.50 | None | Footnotes only | **Recommended** |
| B. BGE-M3 (OpenRouter) | 1024 | Large (3-5d) | $0.01/M | ~3GB | Supersede ADR-009 | Not worth migration |
| C. BGE-M3 self-host | 1024 | Large (3-5d) | $0 | ~3GB | Supersede ADR-009 | 38% cgroup RAM |
| D. Gemini embedding API | 3072 | Large (3-5d) | ~$0.15/M | None | Supersede ADR-009 | Same consent + dim mismatch |
| E. MiniLM-only (384-dim) | 384 | Medium (1-2d) | $0 | ~250MB | Supersede ADR-009 | Severely degraded recall |
| F. Hybrid (local + API) | 384+1536 | Large (3-5d) | ~$0.05-0.25 | ~550MB | Supersede ADR-009 | Dual failure modes |
| G. Qwen/Perplexity via OR | 2560/1024 | Large (3-5d) | Varies | None | Supersede ADR-009 | Dim mismatch |

---

## 11. Edge Cases

### 11.1 Faiz Denies External Embedding Path

If Faiz explicitly denies the external embedding path, the ONLY viable local replacement is **BGE-M3 (1024-dim)**. Migration plan:
1. Create new ADR superseding ADR-009
2. ALTER COLUMN TYPE vector(1024) on two tables
3. Drop + recreate HNSW indexes with m=12, ef_construction=128
4. Re-embed all data, update models.py, retune query pipelines

**Do NOT attempt MiniLM-only (384-dim)** — multilingual recall regression for Indonesian text will make semantic search essentially random.

### 11.2 RAM Pressure => halfvec Migration

When vector count exceeds 3M or index RAM exceeds 80% of 8GB cgroup: ALTER COLUMN TYPE halfvec(1536). No dimension change. Effort: ~1-2h.

### 11.3 Offline Fallback Table

If 9Router outages are proven frequent: create memory.fallback_embeddings with halfvec(384) and separate HNSW. Only write to it when 9Router is unreachable for >30s. Effort: Medium (~3-4h).

---

## 12. Decision

**Recommendation: Keep ADR-009 as-is. Do not change the embedding model.**

Single blocker: **consent gate** — Faiz must explicitly acknowledge memory text may transit 9Router→OpenRouter for embedding.

**Required actions:**
1. Resolve consent gate in `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` (~10m)
2. Add ADR-009 footnote: dimension lock risk, halfvec(1536) trigger at 3M vectors or 80% RAM (~10m)
3. Remove MiniLM 384-dim from primary write pipeline (keep cached for potential offline fallback)
4. Proceed with P3-005 implementation (9Router -> text-embedding-3-small)

**Total effort to unblock:** ~20m documentation. Zero code, schema, or migration changes.

---

## References

| Source | Key Content |
|---|---|
| `adr/ADR-009-memory-recall-semantic-search-strategy.md` | Current binding: text-embedding-3-small 1536 via 9Router; dimension lock |
| `src/memory/models.py` | Vector(1536) on Episodes and SemanticFacts; HNSW m=16, ef_construction=128 |
| `docs/00-core/04-MemorySchema_v2.0.md` | Two embedding columns at vector(1536) |
| `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` | HNSW mandatory; embedding columns; classification matrix |
| `docs/30-data/30-DataGovernance_Classification_v1.0.md` | Derived embeddings inherit source classification |
| `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | Consent gate for external processing |
| `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` | BLOCKED consent gate |
| `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | $30/month hard cap; P3 budget $2/mo |
| `research-reports/P3/mteb-embedding-benchmarks.md` | All alternatives have dimension mismatch |
| `research-reports/P3/oracle-embedding-model-architecture-review.md` | Binding recommendation: keep ADR-009 |
| `PROGRESS.md` | P3-004 PASS; P3-005 BLOCKED; P3-006..P3-010 pending |
| `CHECKLIST.md` | P3 verification checklist; sequential dependency chain |
| `docs/30-data/34-MemoryRecallEvaluationSpec_v1.0.md` | Per-type precision/recall/MRR targets |
