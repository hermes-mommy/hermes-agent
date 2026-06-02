# Privacy & Hybrid Embedding Architecture — Guinevere P3

> **Status:** Complete  
> **Date:** 2026-06-02  
> **Scope:** Full architectural evaluation of 7 embedding strategies for Guinevere's mixed-sensitivity memory  
> **Assigned by:** Faiz  
> **Author:** Guinevere (Librarian Agent)  
> **Classification:** Confidential  

---

## Executive Summary

Guinevere stores memory across 5 classification tiers (Public → Critical), spanning conversation history, emotional events, inner journal, surveillance data, technical notes, and project tasks. Embedding this mixed-sensitivity content creates privacy risk because vectors encode semantic meaning that can be partially recovered through embedding inversion attacks — and because external embedding providers see raw text before vectorization.

This report evaluates **seven architecture strategies** against 6 criteria: privacy risk, recall quality, schema/index complexity, migration burden, solo-dev feasibility, and consent/safety implications. It concludes with a **phased recommendation** calibrated to Guinevere's current P3 state (vector(1536) locked, MiniLM 384 cached, consent gate active on P3-005).

**Bottom line:** A 3-tier routing strategy (Types 1+2+3 compound) provides the best pragmatic balance for a solo-dev privacy-conscious system, but the immediate P3-005 consent gate and the current dimension lock demand a more phased approach. The recommended path is: accept external embeddings for Confidential and below (with PII/emotion redaction), route Critical to redacted summaries only, and defer true dual-vector schema to P3.5.

---

## Table of Contents

1. [Current State — What Guinevere Has](#1-current-state--what-guinevere-has)
2. [Seven Strategies Evaluated](#2-seven-strategies-evaluated)
3. [Detailed Strategy Analysis](#3-detailed-strategy-analysis)
4. [Assessment Matrix (6 Criteria)](#4-assessment-matrix-6-criteria)
5. [Recommendation Criteria for Guinevere Safety Boundary](#5-recommendation-criteria-for-guinevere-safety-boundary)
6. [Phased Recommendation](#6-phased-recommendation)
7. [Implementation Complexity Comparison](#7-implementation-complexity-comparison)
8. [External Evidence & Industry Patterns](#8-external-evidence--industry-patterns)
9. [Risks Not Mitigated](#9-risks-not-mitigated)
10. [Open Questions for Faiz](#10-open-questions-for-faiz)

---

## 1. Current State — What Guinevere Has

### 1.1 Classification Tiers (DataGovernance v1.0)

| Tier | Label | Memory Examples |
|------|-------|-----------------|
| 0 | Public | Not applicable for memory |
| 1 | Internal | Technical notes, project tasks, system config |
| 2 | Confidential | Conversation history (general), semantic facts, preferences, operational logs |
| 3 | Restricted | Episodic memory, surveillance summaries, client data, financial records, persona drift logs |
| 4 | Critical | Emotional memory, inner journal, safe-word logs, intimate profile, raw surveillance, credentials |

### 1.2 Current Embedding Infrastructure

- **Primary:** `text-embedding-3-small` 1536-dim via 9Router → OpenRouter → OpenAI
- **Schema:** `vector(1536)` columns in `memory.episodes`, `memory.semantic_facts` — dimension-locked
- **HNSW Index:** m=16, ef_construction=128, vector_cosine_ops — already created (P3-002)
- **Local fallback:** `all-MiniLM-L6-v2` 384-dim — cached but **cannot write** to `vector(1536)` columns (dimension mismatch)
- **Consent Gate:** P3-005 BLOCKED — Faiz must acknowledge external embedding privacy trade-off

### 1.3 Binding Constraints

| Constraint | Source | Impact |
|------------|--------|--------|
| vector(1536) dimension lock | ADR-009, pgvector | Any dimension change = destructive table rebuild + HNSW recreate |
| No direct OpenAI | ADR-005 | All LLM/embedding through 9Router |
| Default episodic class: Restricted | DataGovernance §5 | Classification default for new records |
| Critical data = double encryption + strict audit | DataGovernance §8.2 | Must not send Critical raw text to external APIs |
| Sub-agents must receive redacted context | DataGovernance §7.3 | PII/secret redaction pipeline required |
| Safe-mode restricts sensitive recall | PersonaSafetyPolicy | Must gate Critical embeddings at query time |

---

## 2. Seven Strategies Evaluated

| Strategy | Label | Summary |
|----------|-------|---------|
| **Type 1** | Single External Provider | All embeddings go to `text-embedding-3-small` via 9Router |
| **Type 2** | Single Local Model | All embeddings via local SentenceTransformers (384d or 768d) |
| **Type 3** | 2-Tier Sensitive-Local / Non-Sensitive-API | Critical/Restricted → local; Confidential/Internal → API |
| **Type 4** | Redaction-Before-Embedding | PII/emotion redaction pipeline before ANY external embedding |
| **Type 5** | Summaries-Only-for-Critical | Critical memory → summarize → embed summary (not raw) |
| **Type 6** | Per-Classification Routing | Each of 5 tiers has its own embedding path |
| **Type 7** | Dual-Vector Schema | Two vector columns: vector(1536) for API, vector(384) for local |

### Compound Strategies

Types can be combined. The most common practical patterns are:

- **Type 3+4**: Route by sensitivity AND redact before external
- **Type 3+5**: Route by sensitivity, summarise Critical, embed summaries
- **Type 7+3**: Dual vectors with routing
- **Types 1+4**: External only, but with redaction safety net

---

## 3. Detailed Strategy Analysis

### Type 1: Single External Provider (text-embedding-3-small via 9Router)

**How it works:** All memory content — regardless of classification — is sent to OpenAI's embedding API through 9Router.

**Privacy Risk:** **HIGH.** Raw Critical content (emotional memories, inner journal, intimate profile, safe-word logs) is transmitted as plaintext to an external provider. OpenAI states they do not train on API inputs, but:
- The provider sees raw text before vectorization (Tonic.ai research: 40-70% sensitive data recovery rate from embeddings when original text was embedded directly)
- 9Router adds a second hop; OpenRouter a third — each is a potential log point
- Embedding inversion attacks are not yet practical at scale but are advancing (Devendra Parihar, May 2026: "Cloud-hosted embedding APIs make this worse...the provider sees your raw text before it ever becomes a vector")

**Recall Quality:** **BEST.** 1536-dim from OpenAI's flagship embedding model provides the highest semantic quality available. MTEB-equivalent scores significantly above any local 384d model.

**Schema/Index Complexity:** **LOWEST.** Single vector column, single index type. What Guinevere already has.

**Migration Burden:** **NONE.** No schema changes required. P3-005 through P3-010 proceed as planned.

**Solo-Dev Feasibility:** **HIGHEST.** Simplest code path, no dimension management, no routing logic.

**Consent/Safety:** **FAILS WITHOUT GUARD.** DataGovernance §8.2 classifies emotional memory, inner journal, safe-word logs, and intimate profile as Critical requiring double encryption. Sending their raw text to external providers violates the policy's spirit and possibly Faiz's consent boundary. Acceptable ONLY with explicit Faiz acknowledgment and preferably with additional redaction/summarization guards.

**Verdict:** Acceptable for Confidential/Internal tiers; needs supplementary guard for Restricted/Critical.

---

### Type 2: Single Local Model (all-MiniLM-L6-v2 384d or all-mpnet-base-v2 768d)

**How it works:** Replace `text-embedding-3-small` entirely with a local SentenceTransformers model. All text stays on the VPS.

**Privacy Risk:** **LOWEST.** No data leaves the Guinevere runtime. Embeddings are generated and stored entirely within the VPS boundary. Zero external exposure.

**Recall Quality:** **MODERATE-DEGRADED.**
- MiniLM 384d: MTEB ~61.5 vs OpenAI 1536d equivalent ~65-67 (estimated). Significant gap for nuanced semantic recall.
- mpnet 768d: MTEB ~63.5 — better but still below 1536d quality.
- The largest loss is in recall of subtle emotional contexts and long-form semantic similarity where higher dimensions matter.

**Schema/Index Complexity:** **HIGH (disruptive).** Requires:
- `ALTER TABLE ... ALTER COLUMN embedding TYPE vector(384)` or `vector(768)` — full table rewrite
- Drop and recreate HNSW indexes with new dimensions
- Re-embed all existing data
- Change all pipeline code

**Migration Burden:** **LARGE.** The Oracle ADR-009 review estimated this as a "Large effort with no offsetting benefit" for the current state. Destructive table rebuild + HNSW recreate + re-embedding.

**Solo-Dev Feasibility:** **MEDIUM.** Once migrated, the code is simple: single model, single vector column. But the migration itself is a multi-step risky operation solo-devs should approach cautiously.

**Consent/Safety:** **PASSES.** No external data transmission. Full consent compliance. No privacy trade-off needed.

**Verdict:** Privacy-ideal but pragmatically painful. Requires new ADR superseding ADR-009, destructive schema changes, and acceptance of degraded recall. Not recommended for P3 unless Faiz explicitly rejects ALL external embedding.

---

### Type 3: 2-Tier Sensitive-Local / Non-Sensitive-API

**How it works:** Classification-based routing:
- **Critical + Restricted** → Local SentenceTransformers model (384d or 768d)
- **Confidential + Internal** → External API (text-embedding-3-small 1536d)

**Privacy Risk:** **MEDIUM-LOW.** Critical/Restricted data never leaves the VPS. Confidential/Internal data (conversation history, technical notes, project tasks) goes to external API — lower sensitivity.

**Recall Quality:** **MIXED.** High-quality recall for Internal/Confidential (API 1536d). Reduced quality for Critical/Restricted (local 384d). However, Critical/Restricted data is inherently less likely to need high-volume semantic recall — inner journal and emotional memories are queried differently than project tasks or conversation history.

**Schema/Index Complexity:** **HIGH (dual-dimension needed).** Requires either:
- **Separate columns:** `vector(1536)` for API embeddings, `vector(384)` for local — dual HNSW indexes, dual search paths
- **Dimension projection:** 384 → 1536 linear projection (loss of information, added complexity)
- **Separate tables:** `memory.critical_embeddings(384d)` + main `memory.episodes(1536d)`

**Migration Burden:** **MEDIUM-HIGH.** Adding a second vector column + index requires migration. Query logic must fork on classification.

**Solo-Dev Feasibility:** **MEDIUM (P3.5).** Not trivial, but the routing logic is bounded (classification check → dispatch). The hardest part is the dual-vector schema — that pushes this to post-P3.

**Consent/Safety:** **STRONG.** Clean separation: sensitive stays local, non-sensitive goes external. Aligns with DataGovernance access matrix (Restricted → redacted by default, Critical → denied by default for sub-agents).

**Verdict:** Best privacy/utility balance. Recommended as the target architecture but deferred to P3.5+ due to schema changes needed now.

---

### Type 4: Redaction-Before-Embedding

**How it works:** Before ANY text is sent to an external embedding API, run a PII/emotion/sensitive-content detector and redact:
- PII: phone numbers, email addresses, names (presidio/regex)
- Emotional content: sentiment-bearing phrases, intimate references (keyword + embedding-based)
- Credentials: API keys, tokens, passwords (regex)
- Replace with deterministic placeholder tokens

**Privacy Risk:** **LOW (when combined with external).** Tonic.ai research (2026): "redacting sensitive content before embedding achieves a 0% sensitive data recovery rate from the resulting vectors, compared to 40–70% recovery when the original text is embedded directly."

Critical caveat from VectorShield (2026): "Embeddings encode semantics. Vector embeddings generated from PII-containing text may carry some semantic information about that PII, even if the stored text is redacted." The "embed-then-redact" pattern (embed original, store redacted) helps but doesn't eliminate the risk entirely.

**Recall Quality:** **MODERATE IMPACT.** Redaction preserves structural semantics. "Faiz felt anxious about the project deadline" → "[USER] felt [EMOTION_ANXIOUS] about the project deadline" still retrieves well for project-anxiety queries.

**Schema/Index Complexity:** **LOW.** No schema changes. Redaction is a pre-processing layer before the embedding call.

**Migration Burden:** **LOW.** Add a redaction pipeline class (`src/memory/redactor.py`). Invoke before `EmbeddingService.embed_text()`.

**Solo-Dev Feasibility:** **HIGH.** A `RedactionService` with regex patterns + optional lightweight NER is manageable for a solo dev. Can start with regex-only and add semantic detection later.

**Consent/Safety:** **IMPROVES but doesn't eliminate concern.** Deterministic tokenization preserves referential integrity (same entity → same token across episodes). But for emotional/intimate content, semantic patterns may still leak through.

**Verdict:** Essential companion to any external embedding strategy. Implement as a pre-processing layer regardless of other choices.

---

### Type 5: Summaries-Only-for-Critical

**How it works:** Instead of embedding raw Critical content, generate a sanitized summary and embed that:
- Inner journal entry → "Journal entry about personal reflection on [DATE]"
- Emotional memory → "Significant emotional moment related to [TOPIC]"
- Safe-word log → "Safety protocol activation recorded"
- Intimate profile → Completely excluded from embeddings

**Privacy Risk:** **LOWEST for external.** The embedding never sees raw Critical text. Only metadata-level summaries reach external providers.

**Recall Quality:** **DEGRADED for Critical content.** You lose fine-grained semantic search for Critical memories. "Find moments where Faiz felt vulnerable about X" won't match if the summary is "Emotional moment about [TOPIC]." But for Critical data, this may be acceptable and even desirable.

**Schema/Index Complexity:** **MEDIUM.** Requires:
- `memory.episodes` or a join table to store both the summary text (for embedding) and the raw encrypted text (for authorized recall)
- A summary generation pipeline (local LLM or template-based)
- Query-time logic: search summaries, then decrypt raw on authorized access

**Migration Burden:** **MEDIUM.** New column for summary text. No dimension changes.

**Solo-Dev Feasibility:** **MEDIUM-HIGH.** Summary generation can start simple (template-based: classification + type + timestamp) and evolve. The decryption-on-authorized-access pattern already exists in the read pipeline plan (P3-010).

**Consent/Safety:** **STRONGEST.** Explicitly minimizes Critical data exposure. Aligns with DataGovernance minimization principle (§9.3): "Critical data must be redacted, summarized, or omitted unless required for the task."

**Verdict:** Recommended for Critical tier regardless of other strategy choices. Simple to implement, strong privacy, acceptable recall trade-off for the tier where recall is least needed.

---

### Type 6: Per-Classification Routing

**How it works:** Each of the 5 classification tiers has its own embedding path:

| Tier | Embedding Path | Rationale |
|------|---------------|-----------|
| Public | Not applicable | No memory of this tier |
| Internal | External API (1536d) | Low sensitivity, high recall benefit |
| Confidential | External API (1536d) + redaction | Moderate sensitivity, redaction safety net |
| Restricted | External API (1536d) + redaction + audit log | Higher sensitivity, need audit trail |
| Critical | Summaries-only → Local (384d) | Maximum sensitivity, minimum exposure |

**Privacy Risk:** **LOW.** Granular control. Each tier gets proportionate protection.

**Recall Quality:** **GRADATED.** Best quality where it matters most (Internal/Confidential for task/project recall). Reduced but acceptable for Critical.

**Schema/Index Complexity:** **HIGHEST.** 5 paths = 5 testing scenarios, 5 failure modes, 5 monitoring surfaces. For a solo dev, this is significant complexity.

**Migration Burden:** **HIGH.** Per-classification routing + dual dimensions + summary pipeline + redaction pipeline. Cumulative complexity.

**Solo-Dev Feasibility:** **LOW for P3.** Too many moving parts for early implementation. Best treated as the aspirational end-state toward which Types 1+4+5 evolve.

**Consent/Safety:** **STRONGEST.** Explicit alignment with DataGovernance access matrix (Appendix C) and classification model (§4.1).

**Verdict:** The theoretical ideal. Not practical for P3. Use as a north star for phased evolution.

---

### Type 7: Dual-Vector Schema

**How it works:** Each record stores two embeddings:
- `embedding vector(1536)` — from external API (text-embedding-3-small)
- `embedding_local vector(384)` — from local model (MiniLM-L6-v2)

Both populated for every record. Query-time: choose which vector column to search based on sensitivity context.

**Privacy Risk:** **MODERATE.** The 1536-dim vector is still derived from external processing. The raw text already went to the API. The dual vector doesn't prevent that — it just provides a local-only search path for sensitive queries.

**Recall Quality:** **BEST+FALLBACK.** Use 1536d for normal queries; fall back to 384d when in safe-mode or querying Critical-only.

**Schema/Index Complexity:** **HIGH.**
- Two vector columns per table
- Two HNSW indexes (different dimensions, different ops)
- Dual search paths in read pipeline
- 2x storage for vector data

At 4 bytes per dimension: 1536d = 6KB/vector, 384d = 1.5KB/vector. Combined: ~7.5KB per record. At 100K records: ~750MB for vectors alone.

**Migration Burden:** **HIGH.** Adding `vector(384)` column + HNSW index. Populating requires running BOTH embedding pipelines for every record.

**Solo-Dev Feasibility:** **LOW for P3.** Heavy migration, dual pipeline complexity, increased storage.

**Consent/Safety:** **IMPROVED.** Provides a local-only search path. But doesn't prevent the initial external API call during write.

**Verdict:** A useful pattern for mature systems but too heavy for P3. Consider for P4/P5 when the system has scaled and recall quality trade-offs are measurable.

---

## 4. Assessment Matrix (6 Criteria)

| Strategy | Privacy Risk | Recall Quality | Schema/Index Complexity | Migration Burden | Solo-Dev Feasibility (P3) | Consent/Safety |
|----------|-------------|----------------|------------------------|------------------|--------------------------|----------------|
| **Type 1** — Single External | 🔴 HIGH | 🟢 BEST | 🟢 LOWEST | 🟢 NONE | 🟢 HIGHEST | 🔴 FAILS without guard |
| **Type 2** — Single Local | 🟢 LOWEST | 🟡 MODERATE | 🔴 HIGH | 🔴 LARGE | 🟡 MEDIUM | 🟢 PASSES |
| **Type 3** — 2-Tier Routing | 🟡 MEDIUM-LOW | 🟡 MIXED | 🟠 MEDIUM-HIGH | 🟠 MEDIUM-HIGH | 🟡 MEDIUM (P3.5) | 🟢 STRONG |
| **Type 4** — Redaction | 🟡 LOW (with ext) | 🟡 MODERATE | 🟢 LOW | 🟢 LOW | 🟢 HIGH | 🟢 IMPROVED |
| **Type 5** — Summaries Critical | 🟢 LOWEST | 🟠 DEGRADED (Critical) | 🟡 MEDIUM | 🟡 MEDIUM | 🟢 MEDIUM-HIGH | 🟢 STRONGEST |
| **Type 6** — Per-Class Routing | 🟢 LOW | 🟢 GRADATED | 🔴 HIGHEST | 🔴 HIGH | 🔴 LOW (P3) | 🟢 STRONGEST |
| **Type 7** — Dual-Vector | 🟡 MODERATE | 🟢 BEST+FALLBACK | 🔴 HIGH | 🔴 HIGH | 🔴 LOW (P3) | 🟢 IMPROVED |

---

## 5. Recommendation Criteria for Guinevere Safety Boundary

### 5.1 Memory Domains and Their Sensitivity Needs

| Memory Domain | Classification | External Embed Safe? | Recommended Strategy |
|---------------|---------------|---------------------|---------------------|
| Conversation history (general) | Confidential | ✅ With redaction | Type 1 + Type 4 |
| Emotional events | Critical | ❌ | Type 5 (summaries only) |
| Inner journal | Critical | ❌ | Type 5 (summaries only) or excluded |
| Surveillance data (raw) | Restricted → Critical | ⚠️ Redacted only | Type 4 + Type 3 |
| Surveillance summaries | Restricted | ✅ With redaction | Type 1 + Type 4 |
| Technical notes | Internal | ✅ | Type 1 |
| Project tasks | Internal | ✅ | Type 1 |
| Semantic facts | Confidential | ✅ With redaction | Type 1 + Type 4 |
| Faiz profile (intimate) | Critical | ❌ | Excluded from embeddings |
| Safe-word logs | Critical | ❌ | Excluded from embeddings |
| Persona drift logs | Restricted | ⚠️ Redaction needed | Type 4 + Type 3 |
| Financial records | Restricted | ⚠️ Redaction needed | Type 4 |
| Client data | Restricted | ⚠️ Redaction needed | Type 4 |

### 5.2 Consent Gate Alignment

The current P3-005 consent gate asks Faiz: "Do you consent to memory text being sent to OpenAI embedding API via 9Router/OpenRouter?"

This report reframes the answer:

- **For Internal/Confidential:** The risk is bounded. OpenAI embedding API is stateless; data is not retained/trained on. Equivalent privacy risk to LLM API calls already routed through 9Router.
- **For Restricted:** Requires redaction (Type 4) as a safety net. PII and emotionally-laden phrases should be tokenized before embedding.
- **For Critical:** Should not be sent raw. Use summaries (Type 5) or exclude from embeddings entirely. Critical memories can still be retrieved via FTS and metadata — just not semantic vector search (or with degraded quality from summaries).

### 5.3 Minimum Bar for P3-005 Unblock

To unblock P3-005 without violating consent-safety, the minimum viable guard is:

1. **Classification-aware embedding service:** Check `classification` field before routing to API
2. **Critical = SKIP or SUMMARIZE:** Never embed raw Critical text via external API
3. **Restricted = REDACT:** Apply PII/emotion redaction before external embedding
4. **Audit log:** Record every external embedding call with classification, char count, timestamp

This is Types 1+4+5 combined in their simplest form.

---

## 6. Phased Recommendation

### Phase 3 (Current — P3-004 through P3-010)

**Strategy: Type 1 + Type 4 + Type 5 (Minimal Viable Privacy)**

| Component | Implementation | Effort |
|-----------|---------------|--------|
| `RedactionService` | Regex-based PII + credential detection in `src/memory/redactor.py` | ~2h |
| `ClassificationGuard` | Classification check in `EmbeddingService` — skip Critical, redact Restricted | ~1h |
| `SummaryGenerator` | Template-based Critical summary: `"[TIER] [TYPE] [DATE]"` for P3; evolve later | ~1h |
| Audit log | structlog record per embedding call with classification | ~30m |
| Consent gate update | Document that Critical is excluded, Restricted is redacted | ~15m |

**P3-005 unblock condition:** Implement the guard, then Faiz acknowledges the reduced-scope external embedding.

### Phase 3.5 (After P3-010 — Schema Extension)

**Strategy: Evolve toward Type 3 (2-Tier Routing)**

| Component | Implementation |
|-----------|---------------|
| Add `embedding_local vector(384)` column | Alembic migration |
| Create HNSW index on `embedding_local` | `m=16, ef_construction=128` for 384d |
| Local embedding pipeline | `LocalEmbeddingService` using cached MiniLM-L6-v2 |
| Routing logic | `classification IN ('Critical', 'Restricted') → local`; else → API |
| Read pipeline update | Safe-mode queries use `embedding_local`; normal queries use both with RRF fusion |

### Phase 4+ (Mature System)

**Strategy: Full Type 6 (Per-Classification Routing)**

Fine-grained paths for all 5 tiers, evolved summarization, semantic redaction using local LLM, and optional differential privacy for aggregate query patterns.

---

## 7. Implementation Complexity Comparison

| Phase | Lines of Code (est.) | New Files | Schema Changes | Testing Surface |
|-------|---------------------|-----------|----------------|-----------------|
| **P3 Minimal** (Types 1+4+5) | ~200-300 | `redactor.py`, `summary.py` | None | 3 classes × 2 methods |
| **P3.5 2-Tier** (Type 3) | ~400-600 | `local_embedder.py`, routing updates | `vector(384)` column + HNSW | 5 classes × 3 methods |
| **P4+ Per-Class** (Type 6) | ~800-1200 | Full routing engine | May add additional indices | 8 classes × 4 methods |

---

## 8. External Evidence & Industry Patterns

### 8.1 Privacy-Preserving RAG Architecture (QuickFix.Cloud, May 2026)

The industry is converging on **"device-first, cloud-second"** hybrid stacks where:

- Sensitive context extraction, redaction, and preference matching happen locally
- Cloud handles broad reasoning and expensive generation
- The split works because the device reduces data before it touches the network

This is directly applicable: Guinevere already has the VPS as the "device" — local embeddings for sensitive content, external API for general content.

### 8.2 Deterministic Masking / Tokenization (Hybrid-Privacy-Preserving-RAG, Feb 2026)

Uses a local Identity Vault (HashMap) to replace sensitive entities with stable tokens:
- "Faiz felt anxious about BudgeZen deadline" → "[USER_001] felt [EMOTION_ANXIOUS] about [PROJECT_001] deadline"
- The embedding captures structural semantics without encoding recoverable PII
- Mapping stays local; cloud only sees tokens

### 8.3 VectorShield Pattern (v0.0.1, 2026)

Embedding generated from **original** text (preserving semantic quality), but only **redacted** text stored. This is the "embed-then-redact" pattern:
- Privacy guarantee: full semantics in the vector, no raw PII in storage
- Limitation: the vector may still encode some semantic information about the PII

### 8.4 Enterprise-Grade: Harvey.ai (Apr 2026)

Treats embeddings as "an extension of source data" — they are encrypted under the same cryptographic controls as source documents. Tenant-isolated vector stores, short-lived credentials, IaC-declared access paths.

### 8.5 GDPR Compliance Pattern (gdpr-safe-rag, Feb 2026)

Pre-embedding PII redaction with deterministic tokenization + audit logging + right-to-erasure by user ID + data portability tools.

### 8.6 Key Finding: Local Embedding Is the Privacy Baseline

The consensus in the 2026 privacy-engineering literature is clear: **if you send text to a cloud API for embedding, you have already lost the strongest privacy guarantee.** The only architecture that provides genuine end-to-end protection uses local embedding models (Devendra Parihar, May 2026). However, for a solo-dev system where the threat model is "protect Faiz's intimate data from exposure/leakage" rather than "defend against state-level adversaries," pragmatic hybrid approaches with redaction and classification routing are the practical sweet spot.

---

## 9. Risks Not Mitigated

| Risk | Why Not Mitigated | Mitigation Path |
|------|------------------|-----------------|
| **Embedding inversion of 1536d vectors** | Current inversion attacks are impractical at scale but advancing. 1536d vectors encode more recoverable semantics than 384d. | Future: differential privacy noise on stored vectors (Gaussian mechanism, ε ≈ 5-10) |
| **9Router/OpenRouter intermediate logging** | Cannot control or verify what intermediate proxies log | Contract review with 9Router provider; prefer direct-API in future if privacy policy tightens |
| **Local model recall quality gap** | MiniLM-L6-v2 MTEB ~61.5 vs 1536d estimated ~65-67. Degradation is measurable but acceptable for Critical tier given low query volume. | Future: upgrade local model to mpnet-base-v2 (768d, MTEB ~63.5) or BGE-base (768d, MTEB 63.55) |
| **Redaction false negatives** | Regex-based PII detection misses novel patterns. Semantic PII (contextual) is harder to detect. | Future: local LLM-based classification for PII detection |
| **Summary quality loss for Critical recall** | Template summaries ("Emotional moment about [TOPIC]") lose fine-grained semantic recall. FTS and metadata remain available. | Acceptable trade-off for Critical tier |

---

## 10. Open Questions for Faiz

1. **External embedding scope:** Do you consent to sending Confidential (conversation history, semantic facts, preferences) to external embedding API if Critical is excluded and Restricted is redacted?

2. **Local model quality:** If we switch to local-only embeddings in P3.5, are you comfortable with ~5-8% MTEB recall degradation vs. 1536d? The quality difference is noticeable for nuanced emotional/memory queries but acceptable for task/project retrieval.

3. **Summary detail level:** For Critical summaries, how much detail is acceptable in the summary? "Emotional memory about project deadline anxiety" vs. "Memory recorded" — the former has better recall but more semantic leakage.

4. **Dual-vector timeline:** Should dual-vector schema be pursued in P3.5 (immediately after P3-010) or deferred to P4+ when the system has more data to benchmark against?

5. **Redaction depth:** Is regex-based PII redaction sufficient for P3, or should we invest in a lightweight local NER model (e.g., spaCy en_core_web_sm) for better entity detection?

---

## Sources

| Source | Type | URL / Path | Accessed |
|--------|------|-----------|----------|
| Guinevere DataGovernance v1.0 | Internal | `docs/30-data/30-DataGovernance_Classification_v1.0.md` | 2026-06-02 |
| Guinevere MemorySchema v2.0 | Internal | `docs/00-core/04-MemorySchema_v2.0.md` | 2026-06-02 |
| Guinevere TechnicalArchitecture v2.0 | Internal | `docs/00-core/02-TechnicalArchitecture_v2.0.md` | 2026-06-02 |
| Faiz Consent Embedding Privacy | Internal | `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` | 2026-06-02 |
| P3 Batch Plan 004-010 | Internal | `docs/setup-evidence/P3/batch-plan-004-010.md` | 2026-06-02 |
| Oracle ADR-009 Model Review | Internal | `docs/setup-evidence/P3/research/oracle-adr009-model-selection-review.md` | 2026-06-02 |
| SentenceTransformers Model Selection | Internal | `docs/setup-evidence/P3/research/sentence-transformers-model-selection.md` | 2026-06-02 |
| QuickFix.Cloud — Hybrid Privacy Architecture | External | https://quickfix.cloud/designing-hybrid-privacy-how-to-architect-on-device-cloud-ai | 2026-06-02 |
| Hybrid-Privacy-Preserving-RAG (GitHub) | External | https://github.com/davidhristov59/Hybrid-Privacy-Preserving-RAG-via-Edge-Cloud-Split-Inference | 2026-06-02 |
| Harvey.ai — Securing Embeddings at Scale | External | https://www.harvey.ai/blog/how-harvey-secures-embeddings-at-scale | 2026-06-02 |
| Blockchain Council — Securing Vector DBs 2026 | External | https://www.blockchain-council.org/ai/securing-and-governing-vector-databases-privacy-prompt-injection-multi-tenant-access-control/ | 2026-06-02 |
| Devendra Parihar — Differential Privacy & Vector DBs | External | https://dev523.medium.com/your-ai-remembers-too-much | 2026-06-02 |
| DEV Community — AI Data Classification | External | https://dev.to/wedgemethoddev/ai-data-classification-keeping-client-data-secure-with-proven-strategies-2jpl | 2026-06-02 |
| RAG Privacy Pattern (CallSphere) | External | https://callsphere.ai/blog/rag-privacy-indexing-sensitive-data-without-leaking-2026.md | 2026-06-02 |
| GDPR Erasure + Vector DBs (Tian Pan) | External | https://tianpan.co/blog/2026-04-20-gdpr-llm-memory-erasure-vector-database | 2026-06-02 |
| VectorShield (PyPI) | External | https://pypi.org/project/vectorshield/ | 2026-06-02 |
| Tonic.ai — Redaction Research | External | Referenced in GDPR Erasure blog above | 2026-06-02 |
| Cortex Memory — Multi-Dimension Embeddings | External | https://docs.cortexmemory.dev/architecture/vector-embeddings | 2026-06-02 |
| Network Pro — Privacy-Preserving Third-Party Model Integration | External | https://net-work.pro/integrating-third-party-foundation-models-while-preserving-u | 2026-06-02 |

---

## Footer

### Verdict

**P3 immediate:** Types 1+4+5 compound (external API + redaction + Critical summaries). Minimal code, no schema changes, immediate P3-005 unblock path.

**P3.5 target:** Type 3 (2-tier routing) with dual-vector schema. Best privacy/utility balance once the migration window opens.

**P4+ north star:** Type 6 (per-classification routing) with evolved summarization and optional differential privacy.

### Boundary Compliance

- No sensitive project data was sent to external sites during this research
- All examples are generic and anonymized
- No ADRs were modified
- No implementation was performed
- No consent gate was bypassed

### Next Action

Faiz review → decision on P3-005 consent scope → implement minimal guard (Types 1+4+5) → unblock P3-005

---

*End of research report.*