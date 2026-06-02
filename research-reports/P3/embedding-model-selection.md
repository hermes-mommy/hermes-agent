# P3 Embedding Model Selection Research — Guinevere Memory System

| Field | Value |
|---|---|
| Status | RESEARCH COMPLETE — awaiting Faiz decision before P3-005 |
| Date | 2026-06-02 |
| Scope | Embedding model decision for Guinevere semantic memory and P3-005 pipeline |
| Current ADR | `adr/ADR-009-memory-recall-semantic-search-strategy.md` |
| Current schema | `memory.episodes.embedding vector(1536)`, `memory.semantic_facts.embedding vector(1536)` |
| Current index | pgvector HNSW, cosine ops, `m=16`, `ef_construction=128` |
| Workload model | 3.3M embedding tokens/month |
| Budget target | About $2/month for P3 embeddings |
| Decision owner | Faiz |

## Executive Verdict

**Recommended current-state decision: keep ADR-009 model `openai/text-embedding-3-small` via 9Router/OpenRouter for P3-005.**

Not because it is the benchmark winner. It is not. Qwen3, Gemini, BGE-M3, and Perplexity look stronger on multilingual and retrieval benchmarks.

It wins for Guinevere **right now** because:

1. It exactly matches the already-built `vector(1536)` schema and HNSW indexes.
2. It costs only about **$0.066/month** at the projected 3.3M token workload.
3. It avoids a 3–5 day schema/index/re-embedding migration before P3-005.
4. It has no prefix/instruction complexity for mixed Indonesian-English memory text.
5. It preserves the current P3 execution chain after the explicit privacy-consent gate is resolved.
6. It is already accepted in ADR-009, so no superseding ADR is required.

**Most worth it under current constraints:** `openai/text-embedding-3-small`.

**Best greenfield/value challenger:** `qwen/qwen3-embedding-4b` or `qwen/qwen3-embedding-8b`.

**Best privacy/local challenger:** `BAAI/bge-m3`, but this requires a new ADR and schema migration to 1024-dimensional vectors or a dual-vector architecture.

**Premium API challenger:** Gemini Embedding 001/2 can be compelling for multilingual quality, and may support 1536-dimensional output through Matryoshka-style dimension selection, but it still changes the embedding space/provider and needs ADR update, consent, and benchmark validation.

## Hard Constraint Summary

Guinevere is not choosing in a vacuum.

Current binding constraints:

- ADR-009 currently chooses `text-embedding-3-small`, 1536 dimensions, routed through 9Router/OpenRouter.
- PostgreSQL already has `vector(1536)` columns on memory tables.
- HNSW indexes already exist for 1536-dimensional cosine vectors.
- P3-004 downloaded MiniLM 384-dimensional model, but it is **cache-only** and incompatible with `vector(1536)` writes.
- P3-005 is blocked on explicit external embedding privacy consent.
- Guinevere memory content includes Restricted/Confidential/Critical materials: conversation history, emotional events, inner journal, surveillance-derived records, project memory, profile facts, and technical notes.
- VPS has 15GB RAM total; `guinevere.slice` is capped at 8GB.
- P3 target cost is about $2/month, but all realistic API candidates are below that at 3.3M tokens/month.

The real tradeoff is not cost. The real tradeoff is:

> Benchmark quality vs schema continuity vs privacy risk vs solo-maintainability.

## Recommendation Matrix

Scoring is **current Guinevere fit**, not pure benchmark rank. It weighs schema fit, Indonesian-English suitability, cost, privacy handling, migration complexity, runtime risk, and P3 readiness.

| Model | Dim | Context | MTEB / Quality Signal | Multilingual / Indonesian | Cost/mo @ 3.3M | Privacy | Current-Fit Score |
|---|---:|---:|---|---|---:|---|---:|
| `openai/text-embedding-3-small` | 1536 | 8K | MTEB v1 ~62; retrieval ~52; stable baseline | Good but English-first; adequate MVP | $0.066 | External via 9Router/OpenRouter; consent + redaction required | **8.6** |
| `google/gemini-embedding-001` | 128–3072 | 2K–20K discrepancy | Multilingual ~68; strong retrieval | Very strong; explicit Indonesian eval signals | $0.495 | External; same consent risk; provider change | 7.4 |
| `google/gemini-embedding-2` | 128–3072 | 8K | Multilingual ~69.9; strong/code/multimodal | Very strong; arguably best API multilingual | $0.660 | External; same consent risk; newer model | 7.3 |
| `qwen/qwen3-embedding-4b` | 2560 | 32K–33K | MMTEB ~69.45; retrieval ~69.60 | Excellent, 100+ languages including Indonesian family | $0.066 | External; same consent risk | 6.2 |
| `qwen/qwen3-embedding-8b` | 4096 | 32K | MMTEB ~70.58; top multilingual | Excellent | $0.033 | External; same consent risk | 6.0 |
| `perplexity/pplx-embed-v1-4b` | 2560 | 32K | Retrieval ~69.66; strong RAG signal | Likely strong; less Indonesian-specific evidence | $0.099 | External; same consent risk | 6.0 |
| `perplexity/pplx-embed-v1-0.6b` | 1024 | 32K | Retrieval ~65.41; ultra-cheap | Likely decent; less Indonesian-specific evidence | $0.013 | External; same consent risk | 6.4 |
| `BAAI/bge-m3` | 1024 | 8K | MTEB v1/v2 ~63–68; MIRACL strong | Excellent; 100+ languages; Indonesian-friendly; no prefix | $0.033 API / local possible | Best privacy if local; API has egress | 5.8 current / 8.4 privacy-first |
| `intfloat/multilingual-e5-large` | 1024 | 512–8K listing conflict | Strong STS; Indonesian MIRACL 66.8 | Good, but prefix-sensitive | $0.033 | External/API or local; prefix risk | 5.4 |
| `nvidia/llama-nemotron-embed-vl-1b-v2:free` | Unknown | 131K | Promising, insufficient stable public fit data | Multilingual/multimodal | $0 | External/free tier; rate-limit/availability risk | 4.8 |
| `openai/text-embedding-3-large` | 3072 | 8K | MTEB ~64.6; better than 3-small | Good | $0.429 | External; same consent; more storage | 4.8 |
| `openai/text-embedding-ada-002` | 1536 | 8K | Legacy; weaker than 3-small | Older baseline | $0.330 | External; same consent | 4.0 |
| `sentence-transformers/all-MiniLM-L6-v2` | 384 | Local | Low/old; English-oriented | Weak for Indonesian companion memory | $0 local | Good privacy | 3.2 |
| `sentence-transformers/all-mpnet-base-v2` | 768 | Local/API listing | Better English ST model | Not multilingual-primary | $0 local / $0.017 API | Good if local | 3.8 |
| `baai/bge-base-en-v1.5` | 768 | 8K | Good English | English-only; avoid primary | $0.017 | External/API or local | 2.8 |
| `baai/bge-large-en-v1.5` | 1024 | 8K | Good English | English-only; avoid primary | $0.033 | External/API or local | 2.9 |
| `thenlper/gte-base` | 768 | 8K | Good English | English-only; avoid primary | $0.017 | External/API | 2.7 |
| `thenlper/gte-large` | 1024 | 8K | Good English | English-only; avoid primary | $0.033 | External/API | 2.8 |
| `mistral/mistral-embed` | 1024? | 8K? | Mixed/limited reports | Limited vs top candidates | Unknown / unconfirmed | Availability uncertain | 2.5 |

## Why Current-State Winner Is Not Benchmark Winner

Pure benchmark view:

- Qwen3 4B/8B are better multilingual/value models.
- Gemini Embedding 001/2 are stronger API quality models.
- BGE-M3 is better for Indonesian/local privacy.
- Perplexity embed looks excellent for RAG cost-performance.

Current Guinevere view:

- The database schema is already `vector(1536)`.
- HNSW indexes are already built for that vector shape.
- P3-005 is blocked only by consent, not by technical readiness.
- Changing to 1024/2560/3072/4096 dimensions means dropping/rebuilding vector columns and indexes or adding dual-vector schema.
- That migration is larger than P3-005 and introduces avoidable operational risk.

So the best decision is not “the highest MTEB model.” The best decision is the model that lets Guinevere ship semantic memory safely now, measure recall quality, and only migrate if evidence proves the baseline inadequate.

## Model-by-Model Findings

### 1. `openai/text-embedding-3-small` — recommended for P3

**Pros**

- Exact 1536-dimensional match with current schema.
- Already accepted in ADR-009.
- Very cheap: about $0.066/month at 3.3M tokens.
- No migration required.
- No query-prefix complexity.
- Stable, widely used API embedding baseline.

**Cons**

- Not benchmark-best.
- Weaker multilingual/Indonesian score than Qwen3, Gemini, or BGE-M3.
- External data egress remains a consent/privacy issue.

**Verdict**

Use for P3-005 unless Faiz explicitly chooses a higher-risk redesign.

### 2. Qwen3 Embedding 4B / 8B — best greenfield value

**Pros**

- Excellent multilingual benchmark signals.
- Strong for Indonesian-language family and code-mixed use.
- Long 32K context.
- Very low cost: roughly $0.066/month for 4B and $0.033/month for 8B based on gathered catalog prices.
- Strong “worth it” candidate if starting from zero.

**Cons**

- 4B uses 2560 dimensions; 8B uses 4096 dimensions.
- Requires schema migration or dual-vector design.
- Larger vectors increase index size and memory pressure.
- Requires new/superseding ADR.
- Still external data egress through 9Router/OpenRouter.

**Verdict**

Best challenger if Faiz wants quality-first and accepts migration. Not recommended for immediate P3-005.

### 3. BGE-M3 — best privacy/local challenger

**Pros**

- Strong multilingual model with Indonesian suitability.
- 1024-dimensional, 8K context.
- No query prefix required.
- Can be self-hosted, reducing external data egress.
- Dense + sparse + ColBERT capability could support future hybrid retrieval.

**Cons**

- 1024 dimensions does not fit current `vector(1536)` columns.
- Local runtime likely consumes around 2–3GB RAM, material under an 8GB cgroup.
- Requires schema migration and HNSW rebuild.
- More operational burden on a shared VPS.

**Verdict**

If Faiz denies external embeddings, BGE-M3 is the most serious replacement. It requires a new ADR and 3–5 day migration plan. MiniLM should not become the primary model.

### 4. Gemini Embedding 001 / Gemini Embedding 2 — premium API challenger

**Pros**

- Very strong multilingual quality.
- Reported support for output dimensions from 128 to 3072.
- Could potentially emit 1536-dimensional vectors, avoiding table type change.
- Good Indonesian evidence compared with most models.

**Cons**

- Still external data egress.
- Provider/model space changes require ADR update and benchmark validation.
- If changing from OpenAI 3-small after data exists, all stored embeddings must be regenerated because vector spaces are not comparable.
- Gemini 2 is newer and more expensive, though still only about $0.66/month at projected volume.
- Context-window reports conflicted for Gemini 001.

**Verdict**

Good candidate if Faiz wants better multilingual API quality without exploding cost. But it should be an explicit ADR decision, not a silent P3-005 swap.

### 5. Perplexity PPLX Embed 0.6B / 4B — strong budget RAG candidate

**Pros**

- Excellent cost, especially 0.6B at about $0.013/month.
- 32K context.
- Strong RAG/retrieval signals.
- 4B has strong retrieval benchmark signals.

**Cons**

- 0.6B is 1024 dimensions; 4B is 2560 dimensions.
- Less Indonesian-specific evidence than Qwen3/Gemini/BGE-M3.
- Still external data egress.
- Requires schema change or dual-vector design.

**Verdict**

Good future benchmark candidate, not current P3 default.

### 6. MiniLM / MPNet / English BGE / GTE / English E5

**Pros**

- Cheap or local.
- MiniLM already cached.
- Lightweight CPU footprint.

**Cons**

- Dimension mismatch with current schema.
- English-oriented or weaker multilingual performance.
- Not appropriate for Indonesian-English companion memory as primary model.
- MiniLM 384-dimensional output cannot be written into `vector(1536)`.

**Verdict**

MiniLM remains cache-only/fallback research artifact. It must not be used for primary memory writes.

### 7. Mistral Embed / Codestral Embed

Reports were inconsistent. The OpenRouter catalog research found Mistral embedding models unavailable or returning 404 through OpenRouter, while other reports mentioned Mistral candidates. Because the requested path is 9Router/OpenRouter, Mistral should not be selected unless Faiz explicitly validates provider availability.

**Verdict**

Do not recommend for P3.

## Privacy Recommendation

The model choice and consent gate are inseparable.

For P3-005, if Faiz approves external embeddings, implement these guardrails:

1. Route only through 9Router/OpenRouter, not direct OpenAI.
2. Use a 9Router-native HTTP client or locked base URL so no SDK fallback can call direct OpenAI.
3. Add explicit classification-aware embedding policy.
4. Do not send raw Critical memory externally.
5. For Critical memory, either skip embedding or embed sanitized summaries only.
6. For Restricted memory, redact obvious sensitive identifiers before external embedding.
7. Log only structured metadata: classification, character/token count, model, duration, error type, no raw text, no vectors, no secrets.
8. Derived embeddings inherit the highest relevant source classification unless a stricter policy says otherwise.
9. Use `provider.data_collection: deny` or equivalent OpenRouter option if supported by 9Router.
10. Keep MiniLM out of primary write path unless a future ADR creates separate local-vector storage.

This corresponds to the privacy research recommendation: immediate P3 uses external API plus redaction plus Critical-summary/skip policy; P3.5 can evaluate dual-vector local/API routing.

## ADR-009 Impact

### If Faiz accepts recommended current-state path

No superseding ADR is needed. Add an ADR-009 note/addendum documenting:

- Alternatives researched: Qwen3, Gemini, BGE-M3, Perplexity, local ST models.
- Reason current model remains selected: schema fit, HNSW continuity, low cost, P3 readiness.
- Dimension-lock accepted risk.
- MiniLM is cache-only and not a primary write fallback.
- External embedding consent and classification guard are mandatory before P3-005.
- Re-evaluate after P3-007/P3-010 recall benchmark on real Indonesian-English memory queries.
- Halfvec trigger: consider `halfvec(1536)` or compression if vector RAM/index size approaches 80% of memory budget or multi-million row scale.

### If Faiz chooses Qwen3 4B/8B

Required changes:

- Supersede ADR-009.
- Change `memory.episodes.embedding` and `memory.semantic_facts.embedding` to `vector(2560)` for Qwen3 4B or `vector(4096)` for Qwen3 8B.
- Drop/recreate HNSW indexes.
- Re-embed all existing vectors, if any.
- Retune HNSW and query limits.
- Update SQLAlchemy `Vector(N)` declarations.
- Update P3 evidence/checklist expectations.
- Accept higher storage: about 10KB/vector for 2560 dims or 16KB/vector for 4096 dims before index overhead.

### If Faiz chooses BGE-M3 local/privacy-first

Required changes:

- Supersede ADR-009.
- Change schema to `vector(1024)` or add a separate local vector column/table.
- Add local model runtime management and resource limits.
- Rebuild HNSW.
- Benchmark CPU latency under `guinevere.slice` 8GB/2CPU.
- Define whether BGE-M3 dense-only is enough or whether sparse/ColBERT features are in scope.

### If Faiz chooses Gemini 1536-dimensional output

Required changes:

- Add ADR-009 amendment or superseding ADR for provider/model change.
- Confirm OpenRouter/9Router supports stable 1536-dimensional output parameter for the chosen Gemini embedding model.
- If no data has been embedded yet, schema can remain `vector(1536)`.
- If data already exists, all embeddings must be regenerated because OpenAI and Gemini vector spaces are not comparable.
- Run P3-007 benchmark before accepting as default.

## Schema and Migration Plan

### Recommended path: no schema migration

For `text-embedding-3-small`:

- Keep `vector(1536)`.
- Keep existing HNSW indexes.
- Implement P3-005 embedding service.
- Validate all returned vectors length exactly 1536.
- Reject or fail closed on dimension mismatch.
- Queue/retry on API failure; do not write local MiniLM vectors into 1536 columns.

### Migration path for non-1536 models

If Faiz chooses a non-1536 model:

1. Write a superseding ADR.
2. Pause P3-005 implementation.
3. Create migration plan for `memory.episodes` and `memory.semantic_facts`.
4. Drop HNSW indexes.
5. Alter vector dimensions or add new vector columns/tables.
6. Recreate HNSW with model-appropriate dimensions and parameters.
7. Re-embed all existing memory rows.
8. Update SQLAlchemy models.
9. Update checklist/evidence expectations.
10. Benchmark vector search latency and recall.
11. Only then resume P3-005/P3-010.

## Rejected Alternatives

| Alternative | Rejection Reason |
|---|---|
| MiniLM 384 as primary | Dimension mismatch, weak multilingual, wrong quality tier for companion memory |
| Direct OpenAI API path | ADR-009 requires 9Router/OpenRouter routing; direct OpenAI needs future ADR |
| Silent switch to Qwen/Gemini/BGE | Violates ADR discipline; embedding spaces and dimensions differ |
| English-only BGE/GTE/E5 | Poor fit for Indonesian-English memory recall |
| Mistral Embed | OpenRouter availability inconsistent/unconfirmed |
| Dual-vector sensitive-local/API in P3 | Good future architecture but too complex/risky for immediate P3-005 |
| Local-only MiniLM privacy shortcut | Privacy improves but recall quality and schema fit become unacceptable |

## Decision Options for Faiz

### Option A — Recommended: keep ADR-009 and proceed after consent

Use `openai/text-embedding-3-small` via 9Router/OpenRouter, 1536 dims.

Implications:

- No schema migration.
- P3-005 can proceed after explicit consent.
- Add privacy guardrails in embedding service.
- Benchmark quality at P3-007/P3-010.
- Revisit if recall quality fails.

### Option B — Quality-first API pivot

Choose Gemini Embedding 001/2 or Qwen3 4B/8B.

Implications:

- Requires ADR update.
- Qwen requires schema dimension migration.
- Gemini may keep 1536 if output dimension parameter is supported, but still requires provider/model decision and later re-embedding if any data exists.
- Same external consent problem remains.

### Option C — Privacy-first local pivot

Choose BGE-M3 local.

Implications:

- Requires ADR update.
- Requires `vector(1024)` or dual-vector schema.
- Uses more VPS RAM/CPU.
- Best privacy posture.
- Delays P3 significantly.

### Option D — Stay paused

Do not implement P3-005 yet.

Implications:

- P3 remains complete through P3-004 only.
- No memory text leaves runtime boundary.
- No further semantic memory pipeline work proceeds.

## Final Recommendation

Mama’s recommendation for Faiz:

**Pick Option A: keep `openai/text-embedding-3-small` via 9Router/OpenRouter for P3.**

But do not proceed blindly. The P3-005 implementation should require explicit approval of the external embedding privacy tradeoff and must include classification-aware redaction/skip/summary behavior.

Decision sentence to unblock P3-005, if Faiz accepts:

> I approve Guinevere P3-005 using `openai/text-embedding-3-small` via 9Router/OpenRouter for embeddings, with classification-aware privacy guards: no raw Critical memory sent externally, Restricted memory redacted where feasible, derived embeddings inherit source classification, and no direct OpenAI API path.

If Faiz does not approve that sentence, P3-005 should remain blocked or pivot to a new ADR for BGE-M3/local.

## Evidence Inputs Read

Parent synthesis incorporated these reports:

- `research-reports/P3/openrouter-embedding-catalog.md`
- `research-reports/P3/mteb-embedding-benchmarks.md`
- `research-reports/P3/multilingual-indonesian-embedding-eval.md`
- `research-reports/P3/embedding-cost-model.md`
- `research-reports/P3/privacy-hybrid-embedding-architecture.md`
- `research-reports/P3/local-embedding-constraints.md`
- `research-reports/P3/oracle-embedding-model-architecture-review.md`

Direct context incorporated:

- `AGENTS.md`
- `docs/00-core/04-MemorySchema_v2.0.md`
- `docs/30-data/33-DatabaseERD_MigrationStrategy_v1.0.md`
- `docs/30-data/34-MemoryRecallEvaluationSpec_v1.0.md`
- `adr/ADR-009-memory-recall-semantic-search-strategy.md`
- `src/memory/models.py`
- P3 setup evidence and blocker documents

## Caveats

- MTEB/MMTEB values across sources mix benchmark generations; exact scores should not be treated as perfectly comparable.
- OpenRouter catalog data can change; model availability should be rechecked immediately before implementation if changing away from ADR-009.
- Gemini context-window and output-dimension details had source discrepancies; verify provider behavior through 9Router before committing.
- Mistral embedding availability through OpenRouter was inconsistent; do not depend on it without a fresh provider check.
- Cost estimates assume 3.3M tokens/month; even 10M/month remains under the $2 target for most listed models.

## Footer

This is a research-only report. No P3-005 implementation was performed. The implementation path remains blocked until Faiz chooses an option and, if using external embeddings, explicitly acknowledges the privacy tradeoff.
