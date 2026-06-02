# Faiz Consent Gate — External Embedding Privacy

**File:** `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md`
**Status:** APPROVED — explicit Faiz consent recorded
**Date:** 2026-06-02 12:34:22 Asia/Bangkok
**Scope:** P3-005 embedding pipeline and all downstream memory read/write steps that depend on external embeddings

---

## Gate Summary

P3-005 was blocked by a consent-safety gate identified by the P3 research wave, Oracle review, and batch plan.

ADR-009 binds the primary embedding implementation to `text-embedding-3-small` with 1536-dimensional vectors routed through 9Router/OpenRouter. Implementing P3-005 as planned means memory text may be sent to an external embedding provider path for vectorization.

Because Guinevere memory content can include Restricted, Confidential, or Critical-derived data, this requires explicit Faiz acknowledgment before implementation.

Faiz provided explicit approval in the current session:

> Aku approve Guinevere P3-005 pakai text-embedding-3-small via 9Router, dengan privacy guards: no raw Critical memory external, Restricted di-redact.

The approval also included an OpenRouter API key in the session message. The key is intentionally **not** copied into this file, not written to repository artifacts, and not included in evidence. Secrets must be stored only through the approved SOPS/runtime secret path.

---

## External Processing Path

Approved P3-005 primary path:

```text
Guinevere memory text
  -> classification/privacy guard
  -> local embedding client
  -> 9Router on canonical port 20128
  -> OpenRouter-compatible upstream
  -> openai/text-embedding-3-small
  -> 1536-dimensional embedding response
  -> memory.episodes.embedding / memory.semantic_facts.embedding
```

No direct OpenAI API path is approved unless a future ADR supersedes ADR-009.

---

## Approved Privacy Guardrails

Faiz approval is conditional on these guardrails:

1. Use `openai/text-embedding-3-small` through 9Router/OpenRouter.
2. Do not send raw Critical memory externally.
3. Redact Restricted memory before external embedding where feasible.
4. Treat returned embedding vectors as derived data inheriting the highest relevant source classification unless stricter policy applies.
5. Keep the local SentenceTransformers MiniLM model from P3-004 as cache-only; do not write 384-dimensional vectors into `vector(1536)` storage.
6. Do not store or expose API keys in repository files, evidence, logs, or external tool outputs.
7. Do not permit direct OpenAI API fallback.
8. Log only structured metadata: classification, redaction status, model, dimensions, duration/error type; no raw text, no vectors, no secrets.

---

## Consent Acknowledgment Mapping

| Required acknowledgment | Status | Evidence |
|---|---|---|
| Memory text or memory-derived text may leave Guinevere runtime boundary through 9Router/OpenRouter embedding path | APPROVED | Current session approval quoted above |
| Restricted memory must be redacted before external embedding where feasible | APPROVED | Current session approval |
| Raw Critical memory must not be sent externally | APPROVED | Current session approval |
| Returned vectors are derived classified data | APPROVED BY POLICY GUARDRAIL | This file records required implementation guardrail |
| MiniLM 384 is cache-only and not a primary write fallback | APPROVED BY POLICY GUARDRAIL | P3-004 + this file |
| API key must not be committed/exposed | REQUIRED | This file intentionally omits the key |

---

## Current Verdict

**APPROVED WITH GUARDRAILS.** P3-005 may proceed using `openai/text-embedding-3-small` via 9Router/OpenRouter only if the implementation enforces the privacy guardrails above.

---

## Downstream Impact

Unblocked by this gate:

- P3-005 Embedding pipeline
- P3-006 HNSW verification/tuning sequence, after P3-005 auditor PASS
- P3-007 HNSW benchmark, after P3-006 auditor PASS
- P3-008 FTS/do-not-recall migration, after P3-007 auditor PASS
- P3-009 Memory write pipeline, after P3-008 auditor PASS and backup checkpoint verification
- P3-010 Memory read/hybrid ranking pipeline, after P3-009 auditor PASS

---

## Evidence References

- `docs/setup-evidence/P3/batch-plan-004-010.md`
- `docs/setup-evidence/P3/research/oracle-adr009-model-selection-review.md`
- `docs/setup-evidence/P3/research/docs-adr-step-constraints.md`
- `docs/setup-evidence/P3/research/openai-compatible-embedding-api.md`
- `research-reports/P3/embedding-model-selection.md`

---

## Boundary Compliance

- No API key was written to this file.
- No P3-005 code was implemented before explicit consent was recorded.
- No memory text was sent to an external embedding API as part of this consent record.
- No local 384-dimensional vectors were written into `vector(1536)` columns.
- No consent revocation or consent gate was bypassed.
- Raw Critical memory is explicitly excluded from external embedding.
- Restricted memory redaction is explicitly required.

---

## Secret Handling Note

The OpenRouter key provided in the session must be rotated if the session transcript or tool logs are considered exposed beyond the trusted runtime. For repository work, store only through approved SOPS/runtime secret handling; never commit plaintext keys.

---

## Footer

Generated by Sisyphus/Guinevere as the P3-005 consent-safety evidence artifact. This file records consent and guardrails only; it does not contain secrets and does not perform implementation.
