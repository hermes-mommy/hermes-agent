---
title: "P29 Evidence Template — Multi-Agent Cognition & Memory"
status: "Template — per-step evidence"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P29 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
---

# P29 Step {NN} Evidence Template — Multi-Agent Cognition & Memory

> Replace `{NN}` with the step number, e.g. P29-001 → step-001.md.

## 1. What Was Done

Brief paragraph: name the new objects (tables, indexes, functions, modules), name the test outcomes (precision@10, cross-agent isolation test, etc.), and cite the step ID `P29-{NN}` from `docs/setup-evidence/P28-P36-masterplan/plans/P29/plan.md`. State entrance conditions and observed results concretely.

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `infra/db/12-pgvector-extension.sql` | created | CREATE EXTENSION vector |
| `infra/db/13-agent-guinevere-vectors.sql` | created | per-agent memory_vectors table + HNSW index for guinevere |
| `src/hermes/cognition/recall.py` | created | 3-tier recall router |
| `src/hermes/cognition/recall_authorizer.py` | created | per-agent namespace isolation at recall layer |
| `tests/test_recall.py` | created | recall unit tests + negative cross-agent test |
| ... | ... | ... |

## 3. Validation Results

- **Diagnostics**: PASS (`lsp_diagnostics` clean on new Python files).
- **Tests**: PASS (`python -m pytest tests/test_recall.py tests/test_namespace_isolation.py -v` shows all PASS; include `precision_at_10` from `tests/bench/recall_quality.py` if relevant).
- **Build**: PASS.
- **Runtime probes**: psql `\dx vector` returns 1 row; HNSW index used in EXPLAIN; cross-agent recall returns 0; consolidation emits `consolidation_tick` event.
- **Concrete metrics**: e.g. `precision_at_10 = 0.78`, `HNSW_used = true`, `cross_agent_blocked_events = 1`, `consolidation_tick_count = 4`.

## 4. Evidence Artifacts

| Artifact | Path | Status |
|---|---|---|
| Per-step evidence | `docs/setup-evidence/P29/evidence/step-{NN}.md` | Created |
| Audit report | `docs/setup-evidence/P29/evidence/audits/step-{NN}-audit.md` | Created |
| Test transcript | `docs/setup-evidence/P29/evidence/transcripts/step-{NN}-pytest.txt` | Captured |
| Recall benchmark | `docs/setup-evidence/P29/evidence/recall_quality_report.md` | Captured (if step is 003 or 010) |
| Soak report | `docs/setup-evidence/P29/evidence/soak-24h-recall-report.md` | Captured (step 010) |

## 5. Doc-Sync Impact

- `docs/setup-evidence/P28-P36-masterplan/plans/P29/README.md` exit criteria should be updated as each step completes.
- No new ADR required for P29; cognition layer is implementation detail. (Optional post-P30 ADR-056 cognition architecture).
- Cross-reference `adr/ADR-054-p27-hermes-society-foundation.md` — P29 must NOT modify ADR-054; if conflicts emerge, escalate per AGENTS.md §6.

## 6. Boundary Compliance

- [ ] No persona drift — Guinevere/Pharsa cognition state cannot alter Y4 baseline; if BDI revision escalates rapport, the FSM gates reject.
- [ ] No consent violation — recall of intimacy requires fresh consent; cross-agent recall is always denied regardless of consent (no path exists in code).
- [ ] No surveillance overreach — recall logs do NOT contain query content verbatim when blocked; only count.
- [ ] No Y6 — POMDP policy does not include `increase_rapport` action; FSM gates remain authoritative.
- [ ] No HARD STOP bypass — HARD STOP remains a global Redis key; cognition layer can listen but cannot override.
- [ ] No secret/intimate data exposure — pgcrypto ciphertext remains ciphertext in vector columns; intimacy_journal is BYTEA only.

## 7. Rollback/Re-run Safety

- PG extensions: `DROP EXTENSION IF EXISTS vector CASCADE` (safe because cascades are intentional).
- Tables: `DROP TABLE IF EXISTS agent_<id>.memory_vectors CASCADE` — drops the table, the index, and any dependent views/sequences.
- Graphiti: idempotent — re-running `kg.add_fact` on same triple within the same `valid_at` window is a no-op (dedupe by `(subject, predicate, object, valid_at)` unique index).
- Cron: `consolidation.tick(agent_id)` is idempotent — re-ticking a fully consolidated agent produces 0 changes and emits 0 events.
- Audit re-run: re-emitting events is blocked by `hermes.events.event_id` BIGSERIAL idempotency.

## 8. Design Decisions/Caveats

- **Vector dimension = 1536**: matches OpenAI text-embedding-3-small output; alternative embeddings must adapt.
- **HNSW over IVFFlat**: HNSW gives better recall@10 for our corpus (< 10k vectors per agent) and is the 2026 default for sub-100k-vector workloads.
- **RRF over score-based fusion**: reciprocal rank fusion avoids score-scale mismatches across tiers (cosine, recency, exact-match have incomparable scales).
- **BDI rationale NOT NULL**: forcing a rationale on every belief revision keeps the audit trail honest and prevents silent drift.
- **POMDP policy is deterministic**: chose determinism over stochasticity for reproducibility and safety audit; stochastic sampling is a future P32 self-evolution item.
- **Blackboard RLS via session setting `hermes.agent_id`**: chosen over per-agent users because (a) we already use this in P22.1 audit_writer, (b) memoizing the setting across connections is cheaper than reconnecting per query.

## 9. Auditor Gate

- **Auditor type**: per plan §9.
- **Verdict**: PASS / NEEDS-REVIEW / FAIL.
- **Report path**: `docs/setup-evidence/P29/evidence/audits/step-{NN}-audit.md`.
- **Findings**: list each finding with severity (critical / major / minor) and re-audit delta.

## 10. Security Scan

- **Cross-namespace recall test**: PASS or FAIL (with metrics: `cross_agent_blocked_events` count).
- **Content leak test**: PASS or FAIL (audit events on cross-agent blocks contain only count, never content).
- **RLS enabled check**: PASS or FAIL (`SELECT relrowsecurity FROM pg_class WHERE relname='blackboard'` = `t`).
- **Ciphertext in vector columns**: PASS or FAIL (vectors encode non-intimate text only; intimacy stays in `intimacy_journal`).
- **Query verbatim logging**: PASS or FAIL (recall logs never log the full query; only hash).
- **Vulnerability scan**: PASS or FAIL (no known CVEs in pinned pgvector / Graphiti / sentence-transformers versions).

## 11. Acceptance Criteria Mapping

| Criterion (from plan §4 + §10) | Status | Evidence |
|---|---|---|
| Step P29-{NN}-001 acceptance (e.g. pgvector installed) | PASS | `\dx vector` transcript |
| ... | ... | ... |
| Cross-agent isolation test | PASS or FAIL | negative-test output captured |
| Recall precision@10 ≥ 0.7 | PASS or FAIL | tests/bench/recall_quality.py output |
| 24h soak (if step 010) | PASS or FAIL | soak-24h-recall-report.md |
| 4 consolidation_tick events in 24h | PASS or FAIL | `SELECT COUNT(*) FROM hermes.events WHERE event_type='consolidation_tick' AND occurred_at > NOW() - INTERVAL '24 hours'` |

## 12. Footer

Version 1.0 | Date: 2026-06-28 | Author: Guinevere + Faiz | Step P29-{NN}
