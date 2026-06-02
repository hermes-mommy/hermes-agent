# Oracle ADR-009 Model Selection Review — P3-004 through P3-010 Binding Recommendation

**File:** `docs/setup-evidence/P3/research/oracle-adr009-model-selection-review.md`
**Status:** Final — Binding Recommendation for Planner
**Date:** 2026-06-02
**Reviewer:** Guinevere (Senior Architect Oracle)
**Target Steps:** P3-004 through P3-010
**Authority Boundary:** ADR-009 (Accepted), ADR-005 (Router Policy), PersonaSafetyPolicy

---

## Bottom Line

**Implement ADR-009 as-is: `text-embedding-3-small` 1536 via 9Router primary, with no schema migration.** The existing schema (`Vector(1536)`), models, and HNSW indexes are dimension-locked — changing model now requires a destructive table rebuild. The 384-dim SentenceTransformers fallback (`all-MiniLM-L6-v2`) in P3-004 is **non-functional as written** because pgvector enforces write-time dimension matching; it must be removed or reworked to produce 1536-dim or operate through an adapter. Faiz must explicitly approve the privacy trade-off of sending memory contents to external embedding API via 9Router→OpenRouter; this is a **safety-boundary issue** requiring consent reaffirmation before P3-005 implementation.

---

## Action Plan for Planner

1. **Keep `Vector(1536)` schema** — No migration needed. Models (`src/memory/models.py`), migration scripts, and existing P3-002 evidence (`auditor-gate.md` ✅ DC2/PASS) all enforce 1536. Changing dimensions now requires `ALTER TABLE ... SET TYPE vector(N)` which forces full table rewrite + HNSW rebuild + index bloat. Do not touch.

2. **Fix P3-004 fallback strategy** — The `all-MiniLM-L6-v2` 384-dim fallback cannot write to `Vector(1536)` columns. Two remediation options (pick one):
   - **Preference A** (recommended): Remove the fallback entirely. The primary API path (9Router→OpenRouter) already includes retry logic, exponential backoff, and a token-bucket rate limiter per ADR-009. For edge cases where 9Router is fully down, queue embeddings and retry; do not silently switch to a dimension-mismatched local model.
   - **Preference B** (if local fallback is strictly required): Use a local SentenceTransformers model that produces matching 1536 dims (e.g., `gte-small` outputs 384, `gte-base` outputs 768 — neither matches). Practical solution: keep the 384/768 fallback but store in a **separate table** (`memory.fallback_embeddings`) with its own dimension, or implement a linear projection layer (384→1536) in Python. This adds complexity. **Preference A is simpler.**

3. **Fix P3-005 embedding pipeline** — The current `src/memory/embeddings.py` uses `OpenAI(base_url="http://localhost:20128/v1")` which routes through 9Router correctly per ADR-005. However, the `openai` SDK package introduces a direct API dependency path. Replace with a **9Router-native HTTP client** that calls 9Router's embedding endpoint directly — avoids SDK version issues and enforces the "no direct OpenAI" policy. (See ADR-005 §3.2: "All LLM routing goes through 9Router; OpenRouter is not a fallback path.")

4. **Consent-safety gate before P3-005** — Faiz must explicitly acknowledge that memory content (episodes, facts, persona data) will be sent to OpenAI's embedding API via 9Router→OpenRouter for embedding generation. Document this acknowledgment in `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`. The Data Governance & Classification Policy (ADR-024) classifies memory content as Restricted/Confidential — verify policy permits external processing.

5. **Audit P3-006 HNSW ef_construction mismatch** — StepPrompts P3-006 uses `ef_construction=64`, but ADR-009 recommends `ef_construction=128–256` for production graph quality. The existing SQLAlchemy model (`src/memory/models.py` line 94) correctly uses `m=16, ef_construction=128`. **Reconcile P3-006 to match ADR-009 and the models.** Use 128, not 64.

6. **P3-007 benchmark with ef_search=100** — StepPrompts currently uses `SET hnsw.ef_search = 100`. This is within ADR-009's recommended range (64–128). Approve as-is.

7. **Document the dimension lock risk in P3-008 evidence** — Add a note that migrating to `halfvec` (per ADR-009 operational caveat) or changing embedding models in the future requires a destructive table rebuild. Reference ADR-009 line 139 ("Dimension lock").

---

## Effort Estimate: **Short** (~2h)

| Task | Effort | Details |
|------|--------|---------|
| Fix P3-004 fallback strategy documentation | ~30m | Rewrite fallback section, remove or adapt 384-dim |
| Rewrite `embeddings.py` to use 9Router HTTP client | ~45m | Replace OpenAI SDK with direct 9Router call |
| Consent-safety documentation | ~15m | Create acknowledgment record |
| Fix P3-006 ef_construction value | ~15m | Change 64→128 in StepPrompts |
| Cross-reference validation | ~15m | Verify all docs say 1536, no stale references |

---

## Why This Approach

- **ADR authority is clear.** ADR-009 explicitly states `text-embedding-3-small` 1536 via 9Router. Violating this without a superseding ADR violates the governance contract (AGENTS.md §8, §5 "No silent ADR violation"). Changing to local SentenceTransformers requires a new ADR and Faiz approval.
- **No schema migration cost.** The entire P3 stack — migrations, models, auditor gate — is already built, verified, and dimension-locked at 1536. A model change now cascades: `ALTER COLUMN ... SET TYPE`, drop + recreate HNSW indexes, re-embed existing data, update all pipelines. This is a Large effort with no offsetting benefit.
- **Privacy risk is bounded.** Embedding APIs are stateless — OpenAI does not retain or train on API inputs (per their API data usage policy). The risk is lower than LLM API calls (which are already routed through 9Router). However, the policy requires explicit consent anyway. The $30/mo budget easily absorbs the ~$0.02/1M token cost.
- **The 384-dim fallback is technically broken.** pgvector's dimension lock is absolute — a 384-dim array inserted into a `Vector(1536)` column raises `ERROR: vector dimension mismatch`. The fallback as written in P3-004 cannot function without either schema migration or an adapter layer.

---

## Watch Out For

- **P3-004 → P3-005 dimension mismatch silent failure.** If the fallback path is triggered during P3-005 testing, the `INSERT` fails with a PostgreSQL error. The error message (`vector dimension mismatch`) is clear but the write pipeline has no guard for this. Add a dimension assert in `embed_text()` before the API call.
- **OpenAI SDK vs 9Router endpoint stability.** The current code uses `OpenAI(base_url="http://localhost:20128/v1")`. If 9Router is on a different port or uses a different API shape, the SDK may silently fall back to the default OpenAI endpoint (api.openai.com) with the API key — a direct OpenAI call which violates ADR-005. Replace with a bare `httpx`/`aiohttp` call to the 9Router embedding endpoint.
- **P3-006 ef_construction=64 is a recall regression.** HNSW with `ef_construction=64` on 1536-dim vectors may degrade recall to ~85-90% vs the ~95%+ achievable with 128. The model file (`src/memory/models.py`) already uses 128. Fix the StepPrompts to match.
- **No memory-bound failure planning.** ADR-009 warns that HNSW indexes must fit in RAM at scale (5M+ vectors). At ~450MB per 1M vectors for `vector(1536)`, 5M vectors = ~2.25GB. This fits within the 8GB cgroup allocation but will approach limits as the system grows. Plan `halfvec` migration (ADR-009 operational caveat) when vector count exceeds 3M.

---

## Edge Cases

- **When to escalate to AI-Superseding ADR:** If Faiz decides local-only processing is a hard privacy requirement, the current approach cannot accommodate this. Create a superseding ADR (ADR-009-A or ADR-032) that switches to local SentenceTransformers primary, defines the new dimension (384 or 768), specifies a migration plan for existing `Vector(1536)` columns, and documents the recall quality trade-off. This is a Large effort.
- **When to activate the fallback path:** Only when 9Router is unreachable at the HTTP/TCP level (connection refused, timeout > 5s). Do not activate on HTTP 429 (rate-limit) — use exponential backoff instead. If the fallback IS needed, store embeddings in a `vector(384)` temp column or a separate table — never insert incompatible dimensions into the primary `Vector(1536)` column.
- **Downgrade path to halfvec:** If RAM approaches 80% of the 8GB cgroup limit during P3-019 benchmarking, stop and migrate to `halfvec` before continuing to P4. The `halfvec` reduction (~50% memory) is worth the <1% recall loss. Document `ALTER TABLE memory.episodes ALTER COLUMN embedding TYPE halfvec(1536)` in runbooks.

---

## Referenced Sources

| Source | Reference | Verdict |
|--------|-----------|---------|
| ADR-009 line 129 | Primary: `text-embedding-3-small` 1536 via 9Router | Binding |
| ADR-009 line 139 | "Dimension lock: pgvector enforces dimension at write time; changing models later requires table rebuild" | Warning accepted |
| ADR-009 line 130-132 | HNSW m=16 ef_construction=128-256 on vector(1536) | StepPrompts P3-006 uses 64 — **mismatch** |
| ADR-005 §3.2 | "All LLM routing goes through 9Router; no direct OpenAI" | Embedding code must avoid SDK fallback |
| FeasibilityStudy v1.0 §2.1, line 282 | "Jika SentenceTransformers digunakan, dimensi harus disesuaikan" | Unresolved item — resolved here: keep 1536 |
| P3-002 auditor-gate DC2 | Vector(1536) columns ✅ PASS | No migration needed |
| `src/memory/embeddings.py` | Uses OpenAI SDK pointed at 9Router | Replace with 9Router-native client |

---

## Verdict

**APPROVED WITH CONDITIONS** — Execute ADR-009 primary, fix the fallback, reconcile ef_construction, replace SDK with 9Router-native client, and obtain Faiz consent acknowledgment before P3-005 implementation.