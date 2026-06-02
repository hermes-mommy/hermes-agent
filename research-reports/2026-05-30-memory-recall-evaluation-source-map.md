# Memory Recall Evaluation Specification — Foundation Source Map

**Document Type:** Research / Source-Map Report  
**Version:** 1.0  
**Date:** 2026-05-30  
**Status:** Complete  
**Owner:** Guinevere  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  

---

## Related Documents

| Document | Relationship |
|---|---|
| `Guinevere_MemorySchema_v2.0.md` | Primary memory architecture, schema, injection pipeline, memory types, encryption tiers |
| `Guinevere_DataGovernance_ClassificationPolicy_v1.0.md` | Data classification, retention, do-not-recall, encryption, incident, Samm rights |
| `Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md` | Access control, safe-mode restrictions, sub-agent data ceilings, ABAC rules |
| `Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md` | Recall quality SLOs, SLIs, error budgets, burn-rate alerts, freeze policy |
| `Guinevere_ConsentRevocationPolicy_v1.0.md` | Do-not-recall consent scope, safe word as revocation, consent ledger, data rights |
| `adr/ADR-009-memory-recall-semantic-search-strategy.md` | Layered recall strategy, pgvector/HNSW config, embedding model, evaluation metrics, token budget cap |
| `adr/ADR-007-memory-storage-backend-selection.md` | PostgreSQL + Redis decision, no SQLite, operational implications |
| `Guinevere_AcceptanceCriteriaCatalog_v1.0.md` | AC-MEM criteria, test gaps, evidence gaps, phase gate blockers, safety zero-tolerance register |

---

## 1. Scope and Authority

### 1.1 Specification Authority Chain

The Memory Recall Evaluation Specification sits at the intersection of three authority streams:

```
ADR-009 (Memory Recall & Semantic Search Strategy)
  +-- Decision: Layered recall with safety and relevance filtering
  +-- Requires: precision@k, recall@k, MRR regression tests
  +-- Requires: token budget cap per recall cycle
  +-- Requires: HNSW index with ef_search tuning

MemorySchema_v2.0 (Memory Architecture)
  +-- Defines: 12 memory types with injection pipeline (8.1)
  +-- Defines: Embedding (vector(1536)), importance, confidence fields
  +-- Defines: 6 recall methods (date range, FTS5, semantic, importance, tag, emotional)
  +-- Defines: Encrypted tiers (regular/sensitive/intimate/double-encrypted)

DataGovernance_ClassificationPolicy_v1.0
  +-- Defines: 5 classification tiers (0-4)
  +-- Defines: Retention classes (Transient through Formal Hold)
  +-- Defines: Do-not-recall state as deletion_state value
  +-- Defines: 20 required metadata fields including classification, purpose, retention

SLO_SLA_ErrorBudgetSpec_v1.0
  +-- Defines: SLI-QLT-005 (recall quality), SLI-QLT-006 (contradiction ceiling)
  +-- Defines: SLO-QLT-005 (>=95% precision monthly), SLO-QLT-006 (<=2% contradiction)
  +-- Defines: Safe-mode recall violation as SLO-QLT-007 (zero tolerance)
  +-- Identifies: SLO-BG-006 (no eval dataset yet)

AcceptanceCriteriaCatalog_v1.0
  +-- AC-MEM-004: Recall injection must use minimum necessary context + redact Critical data
  +-- AC-MEM-005: Do-not-recall flags prevent records from entering LLM context
  +-- AC-MEM-006: Recall quality must be evaluated for precision, relevance, safety, minimization
  +-- TEST-GAP-MEM-001/002: Missing recall evaluation tests
  +-- EVIDENCE-GAP-MEM-001/006: No recall proof yet
  +-- GAP-AC-002: Recall eval spec is a high-severity blocker

ConsentRevocationPolicy_v1.0
  +-- consent.memory.do_not_recall_override: Denied by default
  +-- Memory do-not-recall: Blocks recall of specific memories or derived facts
  +-- Section 14: Samm data rights include do-not-recall
  +-- Appendix C: Do-not-recall applies to memories and derived facts
```

### 1.2 Authority Order for Evaluation Specification

1. Platform/system safety requirements.
2. Safe-word, distress, crisis, incident state (override recall if conflict).
3. Accepted ADRs (ADR-009, ADR-007, ADR-008, ADR-024).
4. Guinevere_PersonaSafetyPolicy_v1.0.md for safe-mode recall restrictions.
5. Guinevere_DataGovernance_ClassificationPolicy_v1.0.md for data class ceilings.
6. Guinevere_AccessControl_RBAC_ABAC_Matrix_v1.0.md for access gates.
7. Guinevere_SLO_SLA_ErrorBudgetSpec_v1.0.md for quality targets.
8. Guinevere_ConsentRevocationPolicy_v1.0.md for consent-bound recall.
9. Guinevere_MemorySchema_v2.0.md for schema and injection order.
10. Guinevere_AcceptanceCriteriaCatalog_v1.0.md for pass/fail gates.

**Mandatory constraint:** Safety outranks recall quality. No recall quality improvement may weaken safe-mode recall restrictions, do-not-recall enforcement, or Critical data access controls.

---

## 2. Requirements Map

### 2.1 Recall Quality Metrics

| Metric | Source | Current Status |
|---|---|---|
| precision@k | ADR-009 | Gap: no k value specified yet |
| recall@k | ADR-009 | Gap: no k value specified yet |
| MRR (Mean Reciprocal Rank) | ADR-009 | Gap: target unspecified |
| Semantic cosine similarity threshold | ADR-009 | Gap: threshold unspecified |
| recall quality (SLI-QLT-005) | SLO Spec | Gap: correct/incorrect rubric unspecified |
| contradiction rate (SLI-QLT-006) | SLO Spec | Gap: detection method unspecified |
| Precision (SLO-QLT-005) | SLO Spec | Target defined: >=95% |
| Contradiction ceiling (SLO-QLT-006) | SLO Spec | Target defined: <=2% |
| Safe-mode recall violation (SLO-QLT-007) | SLO Spec | Target defined: zero, SEV1 on miss |
| Confidence score accuracy | MemorySchema | Gap: no accuracy eval |
| Importance score calibration | MemorySchema | Gap: no calibration eval |
| pgvector recall latency (SLI-LAT-005) | SLO Spec | Target defined: p95 <=2s |

### 2.2 Recall Quality Thresholds per Memory Type

| Memory Type | Source Table | Precision Target | Authority |
|---|---|---|---|
| Episodic | memory.episodes | >=90% | User constraint |
| Semantic | memory.semantic_facts | >=95% | User constraint |
| Financial | financial.transactions | >=98% | User constraint |
| Procedural | memory.procedural_skills | >=95% | User constraint |
| Emotional | memory.emotional_events | >=90% (proposed) | Gap |
| Samm Profile | memory.samm_profile | >=95% (proposed) | Gap |
| Persona Drift | persona.drift_log | >=90% (proposed) | Gap |
| Client | projects.clients | >=95% (proposed) | Gap |
| Surveillance-derived | surveillance.* | >=90% (proposed) | Gap |

### 2.3 Golden Dataset Requirements

| Requirement | Source |
|---|---|
| Held-out validation set | ADR-009 |
| Minimum 200 MVP cases | User constraint |
| Per-type coverage from MemorySchema taxonomy | MemorySchema |
| Classification diversity (Internal through Critical) | DataGovernance |
| Safe-mode test cases | AccessControl |
| Do-not-recall test cases | ConsentRevocation, AC-MEM-005 |
| Contradiction detection cases | SLO Spec SLI-QLT-006 |
| Stale context cases | AC-MEM-006 |
| Edge cases (false intimacy, over-recall) | ADR-009 |

### 2.4 Evaluation Cadence

| Cadence | Source |
|---|---|
| Per-deploy regression | ADR-009 |
| Weekly batch evaluation | ADR-009 |
| Monthly scorecard | SLO Spec |
| Monthly quality SLO | SLO Spec SLO-QLT-005/006 |
| Continuous safety monitoring | SLO Spec SLO-QLT-007 |
| Incident-triggered evaluation | DataGovernance |

---

## 3. Ranking and Injection Pipeline

### 3.1 Memory Injection Pipeline

| Priority | Component | Token Budget | Type | Eval Priority |
|---|---|---|---|---|
| 1 | Core persona definition | ~2,000 | ALWAYS | Medium |
| 2 | Current mood state | ~200 | ALWAYS | Medium |
| 3 | Active violations/rewards | ~300 | ALWAYS | High (safety-gated) |
| 4 | Samm profile summary | ~1,000 | ALWAYS | High |
| 5 | Persona drift log (7 days) | ~500 | ALWAYS | Medium |
| 6 | Current task context | ~500 | IF TASK ACTIVE | Medium |
| 7 | Surveillance context | ~300 | REAL-TIME | High (minimization check) |
| 8 | Relevant episodes (semantic) | ~1,000 | DYNAMIC | Highest |
| 9 | Relevant semantic facts | ~500 | DYNAMIC | Highest |
| 10 | Working memory (conversation) | ~2,000 | DYNAMIC | High |
| **Total** | | **~8,300** | | |
| Token budget cap | ADR-009 | e.g., 4,000 tokens per cycle | | Gap: exact cap unspecified |

### 3.2 Ranking Criteria to Define

| Criterion | Must Define in Spec | Source |
|---|---|---|
| Semantic similarity threshold | Cosine distance for relevance | ADR-009 |
| Importance floor | Minimum importance without explicit query | MemorySchema |
| Time decay function | Freshness weighting | MemorySchema |
| Confidence floor | Minimum confidence for recall | MemorySchema |
| Contradiction penalty | How conflicts affect ranking | MemorySchema |
| Safe-mode gate | Classification ceiling block | AccessControl |
| Consent gate | Do-not-recall ledger check | ConsentRevocation |
| HNSW ef_search | 64-128 for production | ADR-009 |
| Max results per type | Limit per injection level | MemorySchema |

---

## 4. Classification-Aware Filtering

### 4.1 Classification Ceilings

| Memory Type | Default Class | Escalates To | Safe-Mode Recall Limit |
|---|---|---|---|
| Episodic | Restricted | Critical | Critical raw denied |
| Semantic | Confidential | Restricted/Critical by source | Source-tracked |
| Emotional | Critical | Always Critical | Supportive summaries only |
| Inner Journal | Critical | Always Critical | Highly restricted |
| Samm Profile (identity) | Confidential | Critical (intimate) | Field-level |
| Samm Profile (intimate) | Critical | Always Critical | Double-encrypted |
| Safe-word logs | Critical | Always Critical | Minimal, non-punitive |
| Financial | Restricted | Critical (credentials) | Summarized only |
| Client | Restricted | Critical | Task-scoped |
| Surveillance raw | Restricted | Critical | Raw blocked in safe-mode |
| Persona drift | Restricted | Critical | Redacted |

### 4.2 Minimum Necessary Context

- DataGovernance §9.3: LLM prompts must include minimum data; Critical redacted unless required
- AC-MEM-004: Recall injection must redact Critical unless governed purpose
- AccessControl §15: Sub-agents get redacted Restricted, denied Critical by default

### 4.3 Do-Not-Recall Enforcement Chain

| Layer | Source | Requirement |
|---|---|---|
| Consent ledger | ConsentRevocation | do_not_recall_override denied by default |
| Memory marker | DataGovernance | deletion_state = do_not_recall |
| Retention class | DataGovernance | Long-Term Curated supports DNR |
| Backup reconciliation | DataGovernance | Restore reapplies DNR markers |
| Prompt injection | AC-MEM-005 | DNR flags prevent LLM context entry |
| SLO impact | SLO Spec | Zero tolerance for violations |
| Samm rights | ConsentRevocation | Samm may mark memories DNR |
| Incident trigger | DataGovernance | Unsafe intimate-memory recall = incident |

**Zero tolerance:** DNR violations must never occur. Any violation is SEV0/SEV1.

---

## 5. Critical Recall Constraints

| Rule | Source |
|---|---|
| Critical data not for persona flavor | DataGovernance §7.2 |
| Sub-agent Critical denied by default | AccessControl §15 |
| Safe-mode Critical recall denied | AccessControl §7 |
| Critical raw recall must be minimum necessary | DataGovernance §9.3 |
| Critical access must be logged | DataGovernance §10.1 |
| Double-encryption for Critical categories | DataGovernance §8.2 |
| Break-glass Critical access SEV0/SEV1 only | AccessControl §18 |

**Distress state recall behavior** (AccessControl §7):
- Normal: Task-scoped recall allowed
- Safe-word/Distress: Critical/intimate raw denied; supportive summaries only
- Crisis: Minimal supportive context only
- Incident: Deny except incident evidence

---

## 6. Correction Workflow Requirements

| Requirement | Source |
|---|---|
| Samm correction right | DataGovernance §10.4 |
| Episodic/semantic memory correctable | DataGovernance §6.2 |
| Semantic fact versioning (version INTEGER) | MemorySchema §3.1 |
| Version history table | MemorySchema §8.4 |
| Conflict detection (is_conflict, contradicts_ids) | MemorySchema §3.1 |
| Confidence decay (last_verified, verified_count) | MemorySchema §3.1 |
| Fact merge on similar detection | MemorySchema §8.2 |
| Review metadata after correction | DataGovernance §4.3 |

---

## 7. Staleness and Conflict Requirements

| Requirement | Source |
|---|---|
| last_verified, verified_count fields | MemorySchema §3.1 |
| is_conflict, contradicts_ids, conflict_resolved | MemorySchema §3.1 |
| Contradiction SLO <=2% | SLO Spec §6.3 |
| Stale recall = incorrect event | SLI-QLT-005 |
| Consolidation schedule (daily/weekly/monthly) | MemorySchema §8.2 |
| Confidence range 0.0-1.0, decays without verification | MemorySchema §3.1 |

---

## 8. Token Budget Constraints

| Constraint | Source | Value/Status |
|---|---|---|
| Total pipeline budget | MemorySchema §8.1 | ~8,300 tokens |
| Recall cycle cap | ADR-009 | Gap: exact cap unspecified (example: 4,000) |
| Embedding dimension | ADR-009 | 1536 (text-embedding-3-small) |
| halfvec potential | ADR-009 | ~50% memory savings, <1% recall loss |
| Metric: injection tokens | ObservabilitySpec | guinevere_memory_injection_tokens |

---

## 9. Metric Catalog

### 9.1 Prometheus Metrics

| Metric | Type | Labels | Source |
|---|---|---|---|
| guinevere_memory_injection_tokens | Histogram | purpose, data_class | ObservabilitySpec |
| guinevere_memory_recall_duration_seconds | Histogram | memory_type, status | ObservabilitySpec |
| guinevere_pgvector_search_duration_seconds | Histogram | index_type, status | ObservabilitySpec |
| guinevere_memory_recall_eval_total | Counter | memory_type, result | SLO Spec |

### 9.2 Evaluation Metrics

| Metric | Calculation | Target | Source |
|---|---|---|---|
| Recall precision | correct / (correct + incorrect) per type | >=95% overall; per-type thresholds | SLO Spec, user constraints |
| Contradiction rate | contradiction / total_evaluated | <=2% | SLO Spec |
| Safe-mode violation rate | violations / total_safe_mode_recalls | 0 (zero) | SLO Spec |
| Stale context rate | stale / total_evaluated | <=5% (proposed) | Gap |
| DNR escape rate | blocked_records_that_entered / total_dnr_attempts | 0 (zero) | AC-MEM-005 |
| Token budget compliance | recall_token_count / budget_cap | <=100% | ADR-009 |
| Retrieval latency p95 | histogram_quantile(0.95) | <=2s | SLO Spec |
| pgvector recall@k | relevant_in_top_k / total_relevant | >=90% (proposed) | ADR-009 |

### 9.3 Dashboard Panels Required

| Dashboard | Data Class | Source |
|---|---|---|
| DB-SLO-004 Agent Loop Quality | Confidential | SLO Spec |
| DB-SLO-005 Safety Invariants | Restricted/Critical metadata | SLO Spec |
| DB-SLO-008 Monthly Scorecard | Confidential | SLO Spec |

### 9.4 Alert Rules Required

| Alert | Condition | Severity | Source |
|---|---|---|---|
| SafeWordMiss | safe-word miss > 0 | SEV0 | SLO Spec |
| DistressFalseNegative | D3/D4 false negatives > 0 | SEV0 | SLO Spec |
| EvidenceCompletenessMiss | evidence ratio < 1 | SEV2 | SLO Spec |
| SafeModeRecallViolation | violation count > 0 | SEV1 | SLO Spec (SLO-QLT-007) |

---

## 10. Accuracy Thresholds Summary

| Memory Type | Precision Target | Severity on Miss |
|---|---|---|
| Episodic | >=90% | SEV3 |
| Semantic | >=95% | SEV3 |
| Financial | >=98% | SEV2 |
| Procedural | >=95% | SEV3 |
| Emotional | >=90% (proposed) | SEV3 |
| Samm Profile | >=95% (proposed) | SEV2 |
| Persona Drift | >=90% (proposed) | SEV3 |
| Surveillance-derived | >=90% (proposed) | SEV3 |
| Client | >=95% (proposed) | SEV2 |

**Cross-cutting zero-tolerance constraints:**
- Safe-mode recall violation: 0, SEV1
- Do-not-recall violation: 0, SEV0/SEV1
- Critical unsafe recall: 0, SEV1

---

## 11. Gate Map from Acceptance Criteria Catalog

### 11.1 Blocking Criteria

| AC ID | Criterion | Phase | Status |
|---|---|---|---|
| AC-MEM-004 | Recall injection minimum necessary + redact Critical | Phase 2 | BLOCKED |
| AC-MEM-005 | Do-not-recall flags prevent record inclusion | Phase 2 | NOT-RUN |
| AC-MEM-006 | Recall quality evaluation for precision/relevance/safety | Phase 2 | BLOCKED |
| AC-PHASE-003 | Phase 2 Persona & Memory MVP criteria | Phase 2 | BLOCKED |
| AC-PHASE-006 | MVP go-live criteria | MVP | BLOCKED |

### 11.2 Test and Evidence Gaps

| Gap ID | Missing | Blocks |
|---|---|---|
| TEST-GAP-MEM-001 | Recall precision/relevance/safety/minimization evaluation | Memory MVP |
| EVIDENCE-GAP-MEM-001 | PostgreSQL/Redis memory baseline and recall proof | Memory MVP |
| EVIDENCE-GAP-MEM-006 | Recall quality evaluation evidence | Memory MVP |
| GAP-AC-002 | Memory recall evaluation spec missing | Memory MVP |
| SLO-BG-006 | Memory recall eval dataset not built | Recall scorecard |

---

## 12. Evidence Path Patterns

| Evidence | Path Pattern | AC Source |
|---|---|---|
| Recall evaluation report | evidence/memory/recall-eval-<date>.md | AC-MEM-004, AC-MEM-006 |
| Do-not-recall verification | evidence/memory/do-not-recall-<date>.md | AC-MEM-005 |
| Memory baseline | evidence/memory/backend-verify-<date>.md | AC-MEM-001 |
| Classification metadata | evidence/memory/classification-<date>.md | AC-MEM-002 |
| Encryption verification | evidence/security/memory-encryption-<date>.md | AC-MEM-003 |
| SLO scorecard (monthly) | evidence/slo/<YYYY-MM>/scorecard.md | SLO Spec |
| Safety invariants | evidence/slo/<YYYY-MM>/safety-invariants.md | SLO Spec |
| Incident evidence | evidence/incidents/<incident-id>/ | DataGovernance |
| Consent ledger | evidence/consent/ledger/<YYYY-MM>/ | ConsentRevocation |
| Data rights | evidence/data-rights/<request-id>/ | ConsentRevocation |
| Correction evidence | evidence/data-governance/export-correction-<date>.md | AC-DATA-003 |

---

## 13. Gap Register

| ID | Description | Severity | Owner | Resolution Trigger |
|---|---|---|---|---|
| GAP-001 | No golden dataset defined | HIGH | Guinevere | Before memory MVP |
| GAP-002 | Per-type precision targets incomplete | HIGH | Guinevere | Within spec |
| GAP-003 | Evaluation methodology undefined | HIGH | Guinevere | Within spec |
| GAP-004 | Token budget cap per recall cycle unspecified | MEDIUM | Guinevere | Within spec |
| GAP-005 | Contradiction detection algorithm unspecified | MEDIUM | Guinevere | Within spec |
| GAP-006 | Stale detection criteria undefined | MEDIUM | Guinevere | Within spec |
| GAP-007 | Confidence accuracy evaluation method missing | MEDIUM | Guinevere | Within spec |
| GAP-008 | Importance score calibration not defined | LOW | Guinevere | Within spec |
| GAP-009 | halfvec migration eval criteria not defined | LOW | Guinevere | Post-MVP |
| GAP-010 | HNSW vs IVFFlat selection criteria | LOW | Guinevere | Operational |
| GAP-011 | Memory recall recording rules undefined | MEDIUM | Guinevere | Before runtime |
| GAP-012 | Evaluation dashboard panels undefined | MEDIUM | Guinevere | Before monthly scorecard |

---

## 14. Spec Acceptance Criteria (Self-Check)

| # | Criterion | Source |
|---|---|---|
| 1 | Related Documents section with cross-references | AGENTS.md |
| 2 | Stable ID taxonomy (AC-ID or equivalent) | ACCatalog |
| 3 | Normative must language throughout; zero should | User constraint |
| 4 | Concrete evaluation methodology (precision@k, recall@k, MRR) | ADR-009 |
| 5 | Golden dataset spec minimum 200 MVP cases | User constraint |
| 6 | Per-type accuracy thresholds (episodic >=90%, semantic >=95%, financial >=98%, procedural >=95%) | User constraint |
| 7 | Cadence: per-deploy + weekly + monthly + incident-triggered | ADR-009, SLO Spec |
| 8 | Classification-aware filtering (ceilings, safe-mode gate) | DataGovernance, AccessControl |
| 9 | Do-not-recall enforcement (zero tolerance) | ACCatalog |
| 10 | Safe-mode recall gate (zero tolerance) | ACCatalog |
| 11 | Token budget compliance check | ADR-009 |
| 12 | Correction workflow (versioning, conflict resolution) | MemorySchema, DataGovernance |
| 13 | Staleness/conflict detection (confidence decay, verified_count) | MemorySchema, SLO Spec |
| 14 | Critical recall constraints (no persona flavor, safe-mode denial) | DataGovernance, AccessControl |
| 15 | Distress handling (supportive summaries only) | AccessControl |
| 16 | Metrics catalog (Prometheus + eval metrics) | ObservabilitySpec, SLO Spec |
| 17 | Dashboard panels defined | SLO Spec |
| 18 | Alert rules defined | SLO Spec |
| 19 | Tests and drills defined | ADR-009, SLO Spec |
| 20 | Evidence path patterns defined | ACCatalog |
| 21 | Gap register documented | Best practice |
| 22 | Samm Review Record (Status: Accepted) | User constraint |
| 23 | All controls use must; zero should | User constraint |
| 24 | Safety primacy over recall quality | Multiple sources |

---

## 15. Recommended Document Structure

1. Purpose and Scope
2. Related Documents (cross-reference matrix)
3. Memory Taxonomy (types, classification, encryption)
4. Recall Quality Metrics (precision@k, recall@k, MRR, similarity thresholds, token compliance)
5. Per-Type Accuracy Thresholds
6. Golden Dataset Specification (min 200 cases, per-type coverage)
7. Evaluation Cadence
8. Ranking and Injection Pipeline (injection order, HNSW parameters, ef_search)
9. Classification-Aware Filtering (ceilings, safe-mode gate, minimum necessary)
10. Do-Not-Recall Enforcement (zero-tolerance verification)
11. Safe-Mode Recall Gate (restricted states, Critical data)
12. Critical Recall Constraints
13. Distress Handling
14. Correction Workflow
15. Staleness and Conflict Detection
16. Token Budget Constraints
17. Metrics Catalog (Prometheus + eval metrics + recording rules)
18. Dashboard Panels
19. Alert Rules
20. Tests and Drills
21. Evidence Paths
22. Gap Register
23. Acceptance Criteria (self-validation)
24. Samm Review Record
25. Appendices (metric summary, threshold table, evidence index)

---

## 16. Verification Evidence

| Check | Result |
|---|---|
| All 8 foundation documents read | PASS |
| Cross-references from MemorySchema_v2.0 | PASS |
| Cross-references from DataGovernance | PASS |
| Cross-references from AccessControl | PASS |
| Cross-references from SLO Spec | PASS |
| Cross-references from ConsentRevocation | PASS |
| Cross-references from ADR-009 | PASS |
| Cross-references from ADR-007 | PASS |
| Cross-references from AcceptanceCriteriaCatalog | PASS |
| RTM and ObservabilitySpec cross-references | PASS |
| 16 major mapping sections complete | PASS |
| Gap register populated with 12 entries | PASS |
| Spec acceptance criteria defined (24 criteria) | PASS |
| User constraints preserved (all must, zero should, thresholds, dataset size, safety primacy) | PASS |
| No source docs modified | PASS |
| Output file written | PASS |

---

## Review Record

| Field | Value |
|---|---|
| Author | Guinevere (via Hephaestus) |
| Date | 2026-05-30 |
| Status | Complete |
| Recommended Next Action | Author Guinevere_MemoryRecallEvaluationSpec_v1.0.md using this source map as foundation |

---

*End of research-reports/2026-05-30-memory-recall-evaluation-source-map.md*
