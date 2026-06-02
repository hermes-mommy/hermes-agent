# Oracle Architectural Judgment — Embedding Model Selection for Guinevere Memory System

**File:** `research-reports/P3/oracle-embedding-model-architecture-review.md`
**Status:** Final — Binding Recommendation for ADR-009 supersession decision
**Date:** 2026-06-02
**Reviewer:** Guinevere (Senior Architect Oracle — Read-Only)
**Scope:** Embedding model trade-off across 7 candidate paths, pgvector dimension lock, privacy/consent, multilingual quality, resource budget, solo-dev maintainability
**Authority Boundary:** ADR-009 (Accepted), ADR-005 (Router Policy), PersonaSafetyPolicy, DataGovernance ADR-024, ConsentRevocationPolicy

---

## Bottom Line

**Keep ADR-009 as-is: `text-embedding-3-small` 1536-dim via 9Router/OpenRouter. Do not change the embedding model.** The dimension lock on `vector(1536)` columns across `memory.episodes` and `memory.semantic_facts` makes any model switch a destructive operation — full table rebuild, HNSW index drop/recreate, re-embedding of all existing data. The $0.02/1M-token API cost is negligible ($0.10-0.50/mo at projected volume), and the privacy risk is *lower* than the LLM text already flowing through 9Router (embeddings are stateless, non-stored, non-trained-on per OpenAI API policy). The **only real blocker is Faiz consent** for the external API path — resolving that consent gate unblocks P3-005 through P3-010 and costs $0 in migration effort.

---

## Action Plan

1. **Resolve the consent gate** — Faiz explicitly acknowledges (in `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`) that memory text may transit 9Router→OpenRouter for embedding. This is a lower-risk path than existing LLM API calls (no prompt retention, no training, ephemeral vector output). The embedding API is **stateless**: OpenAI does not retain or train on `text-embedding-3-small` inputs per their API data usage policy. Document, date-stamp, and lift the P3-005 block.

2. **Document the dimension lock as accepted risk** — Add a note to ADR-009 operational caveats that the 1536-dim lock is binding until vector count exceeds 3M entries and/or RAM pressure hits 80% of the 8GB cgroup. At that trigger, evaluate `halfvec(1536)` migration (~50% RAM reduction, <1% recall loss) per ADR-009 §Implementation Notes — not a model change.

3. **Adopt 9Router-native HTTP client, not OpenAI SDK** — Replace `openai.OpenAI(base_url=...)` with bare `httpx` calls to 9Router's `/v1/embeddings` endpoint. This enforces ADR-005's "no direct OpenAI" rule and prevents SDK version drift or silent fallback to `api.openai.com`.

4. **Fix P3-004 fallback strategy** — Remove the dimension-mismatched `all-MiniLM-L6-v2` 384-dim path from the primary write pipeline. The 384-dim vector **cannot** be inserted into `vector(1536)` columns — pgvector rejects dimension mismatch at write time. Keep the local model cached only for a future separate `halfvec(384)` fallback table if offline capability becomes a hard requirement. For now, queue failed API embeddings and retry; do not silently switch dimension.

5. **Reject all alternative model proposals in this review** — Document the rejection rationale in ADR-009 footnotes. List them with cost/benefit summary: BGE-M3, multilingual-e5, Gemini embeddings, Qwen/OpenRouter embeddings, local MiniLM-only, and hybrid sensitive-local/API. None justify the schema-migration + index-rebuild + re-embedding cost given the working API path.

---

## Effort Estimate: **Quick** (~30m)

| Task | Effort | Details |
|------|--------|---------|
| Document consent acknowledgment | ~10m | Update `faiz-consent-embedding-privacy.md` with Faiz's explicit choice |
| Add dimension-lock accepted risk note | ~10m | Footnote in ADR-009 or planner gate |
| Reject alternative models in planning | ~10m | One-paragraph table in batch plan |

No code changes needed — the P3-005 pipeline as written (9Router→text-embedding-3-small) is architecturally correct. The consent gate is the only genuine blocker.

---

## Why This Approach

- **The dimension lock is absolute.** pgvector `vector(1536)` columns enforce dimensionality at write time (`ERROR: vector dimension mismatch`). Changing to 1024 (BGE-M3), 768 (mpnet/BGE-base), or 384 (MiniLM/e5-small) requires: `ALTER COLUMN ... SET TYPE` → full table rewrite → drop + recreate HNSW indexes → re-embed all existing rows. This is a **Large** effort (3-5 days) with no recall improvement over the current path.

- **No local model matches 1536-dim natively.** Every practical SentenceTransformers model outputs 384 (MiniLM, BGE-small, e5-small), 768 (mpnet, BGE-base, e5-base, nomic-embed), or 1024 (BGE-large, BGE-M3). None produce 1536 dims. Adapting via linear projection (384→1536) introduces quality loss, maintenance burden, and an untrained layer to tune.

- **BGE-M3 (1024-dim multilingual) is tempting but not worth the migration.** BGE-M3 supports 100+ languages and would improve Indonesian recall. However: (a) 1024 ≠ 1536 → table rebuild required; (b) BGE-M3 is 2.2GB+ on disk, ~3GB RAM at inference — 38% of the 8GB cgroup per model alone; (c) running BGE-M3 locally adds CPU + RAM pressure that competes with HNSW index memory and LLM inference; (d) the local model still requires data to leave the VPS for initial download (HuggingFace); (e) MTEB multilingual score is 64.9 vs text-embedding-3-small's 62.3 on English — marginal gain for massive infra cost.

- **Gemini embeddings (768-dim via API) require the same consent gate** plus a new provider dependency. They also need a dimension change (768 ≠ 1536). The same privacy argument applies (external API) without any structural advantage.

- **The hybrid path (sensitive data → local MiniLM, general → API) is architecturally dangerous for solo-dev.** Dual embedding columns (`vector(1536)` + `vector(384)`) = dual HNSW indexes = double the RAM pressure. Dual write pipelines = dual failure modes = twice the maintenance surface. The distinction between "sensitive" and "general" in memory is fuzzy — semantic facts about Faiz's psychological profile could match either category depending on context. The classification system (Public/Internal/Confidential/Restricted/Critical) already gates access; a second embedding path adds no security benefit beyond what RLS + encryption + classification already provide.

- **Indonesian-English quality from text-embedding-3-small is adequate.** OpenAI's embedding models are trained on multilingual data and perform respectably on Indonesian text in practice (MTEB Indonesian subsets not published, but community benchmarks show within 5% of English recall). The primary recall mechanism is cosine similarity, which is language-agnostic once vectors are in the same space. If Indonesian quality proves insufficient during P3-007 benchmarking (recall@5 < 85%), the correct fix is to add bilingual instruction prefixes or query expansion — not a full model migration.

---

## Alternative Paths — Rejected

| Path | Dimensions | Effort | Cost/mo | RAM Impact | Why Rejected |
|------|-----------|--------|---------|------------|-------------|-------------|
| **A. Keep ADR-009 (recommended)** | 1536 | None | ~$0.10-0.50 | None | Working schema, lowest risk, consent is only blocker |
| **B. BGE-M3 local** | 1024 | Large (3-5d) | $0 (local) | ~3GB (38% of cgroup) | Schema rebuild + 38% RAM for marginal multilingual gain |
| **C. multilingual-e5-large local** | 1024 | Large (3-5d) | $0 (local) | ~2.5GB | Same as BGE-M3, worse Indonesian coverage |
| **D. Gemini embedding API** | 768 | Large (3-5d) | ~$0.10 | None | Same consent gate + new provider + dimension mismatch |
| **E. MiniLM-only (384-dim)** | 384 | Medium (1-2d) | $0 (local) | ~250MB | Severe recall regression for mixed Indonesian-English; no multilingual training |
| **F. Hybrid: sensitive-local, general-API** | 384 + 1536 | Large (3-5d) | ~$0.05-0.25 | ~550MB (dual) | Dual schema, dual indexes, fuzzy sensitivity boundary, twice the failure modes for solo-dev |
| **G. OpenRouter/Qwen/Perplexity embeddings** | varies | Medium (1-2d) | varies | None | Each has different dimension; none match 1536 without adaptation; adding provider risk with no benefit over 9Router's existing OpenRouter path |

---

## Watch Out For

- **Consent gate is the only true blocker — not technology.** The embedding privacy concern (data leaving VPS) already exists for every LLM API call through 9Router. Embedding calls are strictly *lower risk*: no conversation stored, no training, no retention. Frame the consent decision accordingly — it's not new risk, it's existing accepted risk applied to a lower-risk operation.

- **Dual embedding columns create a hidden maintenance trap.** If you implement a separate `vector(384)` fallback column, every future schema change (new memory type, classification migration, TimescaleDB chunk rebalancing) must handle both columns. Each new index = more autovacuum pressure on already dimension-sensitive tables. Solo-dev overhead is real.

- **`halfvec(1536)` is NOT a model change — it's a storage optimization.** ADR-009 already recommends this. It does not change dimensions (1536 remains); it halves storage. This is the *correct* RAM pressure relief valve, not a model migration. Document the trigger: migrate to `halfvec` when vector count exceeds 3M or when P3-019 benchmarking shows index RAM >80% of cgroup.

- **BGE-M3 requires HuggingFace download at first load.** The 2.2GB model download from HuggingFace means data still leaves the VPS boundary. If the objection is "data must never leave my VPS," then local models don't fully satisfy it either — you're trusting HuggingFace CDN and the model distribution infrastructure. The first load exposes the VPS IP and downloads model weights. This is different from sending *memory content* to an API, but it's not a zero-trust boundary either.

---

## Edge Cases

- **Escalation to local-only: if Faiz explicitly denies the external embedding path.** In this case, the ONLY viable path is BGE-M3 (1024-dim) as a local replacement — it has the best multilingual support and acceptable recall. The migration plan would be: (1) create new ADR superseding ADR-009 specifying BGE-M3 1024-dim, (2) write migration to `ALTER COLUMN ... SET TYPE vector(1024)`, (3) drop and recreate all HNSW indexes with adjusted `m` parameter (m=12 for 1024-dim recommended), (4) re-embed all existing data in batches, (5) update `src/memory/models.py` to `Vector(1024)`, (6) update all query pipelines. This is a **Large** (~3-5 days) effort. Do not attempt MiniLM-only (384-dim) — the multilingual recall regression for Indonesian text will make semantic search essentially random.

- **Escalation to halfvec migration: if RAM pressure exceeds 80% of the 8GB cgroup.** The ADR-009 operational note already covers this. Use `ALTER TABLE memory.episodes ALTER COLUMN embedding TYPE halfvec(1536)` — no dimension change, no model change, just storage format. This is a **Short** (~1-2h) operation with zero recall loss for cosine similarity. Document in runbooks.

- **Deferred fallback table: if offline capability becomes a hard requirement.** Create a separate table `memory.fallback_embeddings(episode_id UUID, embedding halfvec(384))` with its own HNSW index. Only write to this table when 9Router is unreachable for >30s. On reconnect, re-embed via API and backfill the primary `vector(1536)` column. This keeps the primary path clean while handling edge-case offline. Effort: **Medium** (~3-4h) but justified only if 9Router outages are frequent (evidence from monitoring, not hypothetical).

---

## ADR/Schema Migration Implications

**If keeping ADR-009 (recommended path):**
- ADR-009: No change needed. Add a footnote: "Dimension lock accepted; halfvec migration trigger at 3M vectors or 80% RAM."
- Schema: No change. All `vector(1536)` columns, HNSW indexes, and model definitions stay.
- SQLAlchemy models: No change. `Vector(1536)` remains.
- Existing migrations: No re-run needed. P3-002 auditor already verified 1536-dim compliance.
- P3-005 implementation: Unblocked once consent gate lifts.

**If switching to BGE-M3 (1024-dim) — only if external API denied:**
- New ADR required: Supersede ADR-009 with "Local Embedding Model: BGE-M3 1024-dim"
- Schema migration: `ALTER TABLE memory.episodes ALTER COLUMN embedding TYPE vector(1024) CASCADE` (full table rewrite + index drop)
- HNSW index recreate: Drop existing, recreate with `m=12, ef_construction=128` for 1024-dim
- Data migration: Re-embed all existing `memory.episodes` and `memory.semantic_facts` rows in batches of 100
- SQLAlchemy models: Change to `Vector(1024)` in all embedding columns
- Query pipelines: Update all `<=>` operators (no syntax change, but ef_search may need retuning)
- Budget impact: $0/mo (local), +~3GB RAM consumption

---

## References

| Source | Key Content |
|--------|-------------|
| `adr/ADR-009-memory-recall-semantic-search-strategy.md` | Current binding: text-embedding-3-small 1536 via 9Router; dimension lock caveat |
| `docs/setup-evidence/P3/research/oracle-adr009-model-selection-review.md` | Oracle verdict: APPROVED WITH CONDITIONS; consent gate required |
| `docs/setup-evidence/P3/research/sentence-transformers-model-selection.md` | All local models 384/768/1024-dim; none match 1536; MiniLM 80MB/250MB RAM |
| `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` | BLOCKED status; consent acknowledgment absent |
| `docs/setup-evidence/P3/research/openai-compatible-embedding-api.md` | OpenAI SDK + 9Router routing; dimension validation patterns |
| `docs/setup-evidence/P3/batch-plan-004-010.md` | Sequential execution mandate; P3-005 gate blocks steps 005-010 |
| `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md` | All embedding columns `vector(1536)`; HNSW `m=16, ef_construction=128` |
| `docs/00-core/04-MemorySchema_v2.0.md` | `memory.episodes.embedding` and `memory.semantic_facts.embedding` both `vector(1536)` |
| `docs/00-core/02-TechnicalArchitecture_v2.0.md` | 4C/16GB VPS; guinevere.slice 8GB cgroup; PostgreSQL 4GB allocation |
| `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | P3 memory budget: $2/mo; total $30/mo hard cap |
| `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf` | `MemoryMax=8G`, `CPUQuota=200%` enforced via systemd cgroup |

---

*This is a read-only architectural judgment. No files were modified. No implementation was performed. No consent was assumed.*