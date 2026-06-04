# Phase 3 Memory Bridge: Recall Quality Metrics & A/B Testing Infrastructure Audit

**Date**: 2026-06-04  
**Author**: Guinevere (Autonomous Engineering System)  
**Target**: Phase 3 Planner (ADR-035 A/B Testing, 100 queries, p > 0.05 recall quality gate)  
**Status**: COMPLETE  

---

## 1. Executive Summary

The codebase contains **robust ranking logic** and **comprehensive evaluation specifications**, but **zero implemented A/B testing harnesses, statistical testing libraries, or golden datasets**. 

The recall quality gate (100 queries, p > 0.05) specified in ADR-035 is currently a **planned artifact, not an implemented capability**. To execute Phase 3 safely, the A/B testing infrastructure, statistical evaluation tooling, and golden dataset must be built before the migration cutover.

---

## 2. Existing Test Files Related to Memory Recall

| File Path | Purpose | Coverage |
|---|---|---|
| `C:\Users\faizz\guinevere\tests\memory\test_read_pipeline_hybrid.py` | Deterministic unit tests for hybrid ranking | RRF fusion (k=60), both-signal bonus (x1.25), recency boost (max 10%), importance normalization, DNR pre-filter WHERE clauses, classification fail-closed, stable ordering. |
| `C:\Users\faizz\guinevere\tests\hermes\test_memory_bridge.py` | Unit tests for `recall_for_context()` wrapper | Mocks `recall_memories`; verifies parameter forwarding (`limit`, `token_budget`, `safe_mode`, `principal`, `embedding_service`) and error handling (empty query, DB errors). |
| `C:\Users\faizz\guinevere\tests\memory\test_memory_e2e.py` | End-to-end memory pipeline tests | Basic write/read flow, no quality metric evaluation. |
| `C:\Users\faizz\guinevere\tests\memory\test_safe_mode_memory.py` | Safe-mode recall restrictions | Verifies Critical/Restricted content redaction and blocking in safe mode. |
| `C:\Users\faizz\guinevere\docs\setup-evidence\P3\STEP-P3-010\verify_read_pipeline.py` | P3-010 Read Pipeline Verification Script | Validates function signatures, RRF k=60, 90-day half-life recency decay, importance factor, DNR exclusion, classification ceiling, safe-mode substitution, and token budget enforcement via fake sessions. |

**Gap**: All existing tests verify **functional correctness and safety gates**, not **recall quality metrics** (precision, recall, MRR, NDCG).

---

## 3. Existing Recall Quality Metrics & Specifications

The canonical source for recall quality metrics is fully specified but not implemented in code:
- **Specification**: `C:\Users\faizz\guinevere\docs\30-data\34-MemoryRecallEvaluationSpec_v1.0.md`
- **Defined Metrics**:
  - **Precision@k**: `TP@k / k` (Target: ≥90% for Episodic, ≥95% for Semantic/Faiz Profile/Financial/Project/Client)
  - **Recall@k**: `TP@k / total_relevant` (Target: ≥85% Episodic, ≥90% Semantic)
  - **MRR (Mean Reciprocal Rank)**: `mean(1 / rank_of_first_relevant)` (Target: ≥0.80 Episodic, ≥0.88 Semantic)
  - **NDCG@k**: Normalized Discounted Cumulative Gain with graded relevance (0-3 scale). (Target: ≥0.75 Episodic, ≥0.82 Semantic)
  - **Contradiction Rate**: ≤2% (SLO-QLT-006)
  - **Stale Rate**: ≤5%
  - **Hallucination Rate**: 0% (Zero tolerance)
- **Relevance Grading Scale**: 0 (Irrelevant), 1 (Tangential), 2 (Relevant), 3 (Essential).

**Gap**: The spec defines a 200-query golden dataset requirement, but **no golden dataset JSON file exists** in `evidence/memory-eval/dataset/`.

---

## 4. A/B Testing & Split-Testing Infrastructure

**Status: NOT IMPLEMENTED (Planned Only)**

ADR-035 and migration plans explicitly reference an A/B test:
> *"A/B test memory recall on 100 queries. Recall quality unchanged (p-value > 0.05 on recall precision; DNR enforced)."*

However, searches for `ab_test`, `split_test`, `A/B`, and related scripts reveal:
- `scripts/ab_test_recall.py` is listed in migration plans as `CREATE (~100 lines)` — **it does not exist**.
- `tests/memory/test_hermes_recall_quality.py` is listed as `CREATE (~150 lines)` — **it does not exist**.
- The concept is documented in `docs/setup-evidence/hermes-migration/phase-3-memory.md` and `research-reports/migration-plan/07-test-suite.md`, but the tooling is absent.

**Gap**: No A/B testing harness exists to run 100 queries against dual pipelines (or before/after config changes) and compute statistical significance.

---

## 5. Evaluation of `recall_for_context()` Testing

Current testing of `recall_for_context()` (in `test_memory_bridge.py`) is **purely functional**:
- ✅ Verifies empty query raises `ReadPipelineQueryError`.
- ✅ Verifies DB errors return `[]`.
- ✅ Verifies `safe_mode`, `principal`, `limit`, `token_budget`, and `embedding_service` are forwarded correctly to `recall_memories`.
- ❌ **Does NOT evaluate** whether the returned results are actually relevant, precise, or correctly ranked.

---

## 6. Recall Scoring & Ranking System (`read_pipeline.py`)

The ranking system is fully implemented and mathematically sound (`C:\Users\faizz\guinevere\src\memory\read_pipeline.py`):
- **Signals**: Vector cosine similarity + FTS (`ts_rank`) + Recency + Importance.
- **RRF Fusion**: `RRF_K = 60`.
- **Both-Signal Bonus**: `BOTH_SIGNAL_BONUS = 1.25` applied when an episode is found by both vector AND FTS.
- **Recency Decay**: 90-day half-life exponential decay, capped at `RECENCY_MAX_BOOST = 0.10` (10% max boost) to ensure recency never dominates relevance.
- **Importance**: Normalized 1-10 to 0.1-1.0, applied as `0.5 + 0.5 * normalized_importance`.
- **Candidate Pool**: Hard capped at `MAX_CANDIDATE_POOL = 200` to prevent unbounded CPU/memory usage.
- **Safety Gates**: DNR pre-filter (`do_not_recall IS false`), classification ceiling filtering, safe-mode content substitution, token budget trimming (4,000 tokens default).

**Gap**: The pipeline computes `combined_score`, but there is **no code to measure or log the quality** of these scores against ground truth.

---

## 7. Statistical Testing Code (scipy, numpy, t-test, chi-square, p-value)

**Status: NONE FOUND**

Extensive searches for `scipy`, `numpy`, `ttest`, `t_test`, `chi2`, `chi_square`, `p_value`, and `pvalue` returned **zero matches** in Python files (only false positives for `unittest.mock`). 

**Gap**: The codebase has no statistical testing library installed or imported. Calculating a p-value > 0.05 for the A/B test is currently impossible without adding `scipy` (e.g., `scipy.stats.ttest_ind` or `scipy.stats.chi2_contingency`).

---

## 8. Logging & Metrics Collection on Recall Results

**Current State**:
- **Structured Logging**: `read_pipeline.py` emits `_logger.info` / `_logger.warning` for:
  - `embedding_fallback_keyword`
  - `recall_no_results`
  - `token_budget_trimmed` (logs budget, total_before, returned_after, discarded)
  - `recall_token_budget_empty`
  - `recall_complete` (logs `query_length`, `query_hash`, `candidates`, `filtered`, `returned`, `principal`, `safe_mode`, `exclude_dnr`, `safe_mode_redacted`, `safe_mode_blocked`).
- **Benchmarking**: `C:\Users\faizz\guinevere\scripts\bench_memory.py` (P3-019) measures **latency** (p50, p90, p95, p99) for vector, FTS, hybrid, and write operations against ADR-009 targets. It does **not** measure recall quality.

**Specified but Missing Prometheus Metrics** (per `34-MemoryRecallEvaluationSpec_v1.0.md`):
- `guinevere_memory_recall_eval_total` (labels: `memory_type`, `result`)
- `guinevere_memory_recall_duration_seconds`
- `guinevere_memory_dnr_violation_total`
- `guinevere_safe_mode_recall_violation_total`
- `guinevere_memory_hallucination_total`
- `guinevere_memory_contradiction_detected_total`
- `guinevere_memory_stale_detected_total`

**Gap**: No hit rate, cache hit, or recall quality metrics are currently emitted to Prometheus.

---

## 9. Testing Gaps Summary

| Gap ID | Description | Severity | Impact on Phase 3 |
|---|---|---|---|
| **G-01** | No statistical testing library (`scipy`/`statsmodels`) | HIGH | Cannot compute p-value > 0.05 for A/B test gate. |
| **G-02** | No golden dataset (`evidence/memory-eval/dataset/golden-dataset-v1.0.json`) | CRITICAL | A/B test has no ground truth to compare against. |
| **G-03** | No A/B testing harness (`scripts/ab_test_recall.py`) | CRITICAL | Cannot execute the 100-query A/B test mandated by ADR-035. |
| **G-04** | No LLM-as-a-judge evaluation pipeline | MEDIUM | Cannot automate faithfulness/contradiction scoring within the $3/month evaluation budget. |
| **G-05** | Prometheus recall quality metrics not implemented | MEDIUM | Cannot monitor recall quality degradation in production post-migration. |
| **G-06** | Embedding API (G-B1) pre-existing failure | CRITICAL | If vector search is broken, A/B test only measures FTS+Recency, invalidating the vector quality gate. |

---

## 10. What Needs to Be Built for A/B Testing (Action Plan)

To satisfy the ADR-035 recall quality gate (100 queries, p > 0.05), the following must be built **before Phase 3 execution**:

### Step 1: Add Statistical Dependencies
- Add `scipy` to `requirements.txt` or `pyproject.toml` for statistical hypothesis testing (e.g., paired t-test or McNemar's test for precision comparison).

### Step 2: Construct the Golden Dataset
- Create `evidence/memory-eval/dataset/golden-dataset-v1.0.json` with **100 MVP queries** (minimum for A/B test, spec calls for 200 total).
- Each query must include: `query_text`, `memory_type`, `candidate_memory_ids`, and `ground_truth` with graded relevance (0-3) and `do_not_recall_ids`.

### Step 3: Build the A/B Testing Harness
- Create `scripts/ab_test_recall.py` that:
  1. Loads the golden dataset.
  2. Executes recall via the current pipeline (Baseline A).
  3. Executes recall via the Hermes-augmented pipeline or new config (Variant B).
  4. Computes Precision@10, Recall@10, MRR, and NDCG@10 for both.
  5. Uses `scipy.stats` to compute the p-value for the difference in Precision@10.
  6. Fails the script (exit code 1) if `p < 0.05` OR if any `do_not_recall_ids` appear in Variant B results.

### Step 4: Fix Embedding API (Pre-requisite)
- Verify that `embedding_service.aembed()` returns valid 1536-dim vectors (HTTP 200, <2s latency). If G-B1 is still broken, the A/B test is invalid and must be blocked.

### Step 5: Implement Prometheus Quality Metrics (Post-Migration)
- Add metric emitters to `read_pipeline.py` for `guinevere_memory_recall_eval_total` and `guinevere_memory_recall_duration_seconds` to enable continuous monitoring post-cutover.

---

## 11. Footer

**Verification**: This report was generated via exhaustive `glob`, `grep`, and `read` tool searches across the entire workspace. All paths are absolute. No inline confabulation; all claims are backed by file evidence.  
**Next Action**: Review this report. If approved, delegate the creation of `scripts/ab_test_recall.py` and `golden-dataset-v1.0.json` as the first atomic steps of the Phase 3 planner.
