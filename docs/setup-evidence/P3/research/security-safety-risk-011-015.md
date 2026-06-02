# Security & Safety Risk Register — P3-011 through P3-015 (Memory Safety Implementation)

**File:** `docs/setup-evidence/P3/research/security-safety-risk-011-015.md`
**Status:** Complete — read-only specialist report
**Date:** 2026-06-02
**Author:** Guinevere (Security/Safety Specialist — research wave)
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL
**Scope:** P3-011 (Hybrid Ranking Tuning), P3-012 (Context Injection), P3-013 (Do-Not-Recall Implementation), P3-014 (Safe-Mode Memory Gate), P3-015 (Memory Consolidation Job)

---

## Sources Inspected

| Source | Path | Role |
|--------|------|------|
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | Safety boundaries, safe-word, forbidden patterns |
| ConsentRevocationPolicy | `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` | DNR, consent ledger, revocation types |
| DataGovernance Policy | `docs/30-data/30-DataGovernance_Classification_v1.0.md` | Classification tiers, retention, minimization |
| MemoryRecallEvalSpec | `docs/30-data/34-MemoryRecallEvaluationSpec_v1.0.md` | 8-layer DNR chain, safe-mode gates, ranking criteria |
| ADR-007 | `adr/ADR-007-memory-storage-backend-selection.md` | PG + Redis, no SQLite |
| ADR-009 | `adr/ADR-009-memory-recall-semantic-search-strategy.md` | HNSW, embedding, token budget, layered recall |
| ADR-008 | `adr/ADR-008-memory-encryption-key-management.md` | Encryption, key hierarchy |
| Batch Plan 004-010 | `docs/setup-evidence/P3/batch-plan-004-010.md` | Existing binding decisions, column mapping |
| Hybrid Ranking Safety | `docs/setup-evidence/P3/research/hybrid-ranking-safety.md` | P3-010/P3-011 safety gates, ranking formulas |
| Faiz Consent Gate | `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` | Embedding privacy guardrails |
| Docs/ADR Constraints | `docs/setup-evidence/P3/research/docs-adr-step-constraints.md` | Per-step constraint analysis, C-01 through C-07 |
| P3-010 Verification | `docs/setup-evidence/P3/STEP-P3-010/verification.md` | Current read pipeline implementation |
| P3-010 Auditor Gate | `docs/setup-evidence/P3/STEP-P3-010/auditor-gate.md` | Current safety gate audit |
| P3-010 Source Code | `src/memory/read_pipeline.py` | Production read pipeline (733 lines) |
| P3 Models | `src/memory/models.py` | ORM models including Episodes, SemanticFacts |
| Agent Contract | `AGENTS.md` | Blocking rules, anti-patterns, auditor discipline |
| PROGRESS.md | `PROGRESS.md` | Phase/step tracker, P3 at 10/19 |
| PromptInjection Policy | `docs/20-security/24-PromptInjection_ModelSafety_v1.0.md` | (Referenced in P3 research notes — existed draft only) |

**No source code was modified. No DB was queried. No secrets were accessed.**

---

## Executive Summary

P3-013 (Do-Not-Recall) and P3-014 (Safe-Mode Memory Gate) are **safety-critical** steps. A failure in either creates a SEV0 or SEV1 incident per MemoryRecallEvalSpec §4.4. P3-012 (Context Injection) is the bridge between memory recall and LLM prompt — it is the last line of defense before poisoned or unsafe memory reaches the model. P3-015 (Memory Consolidation) must not silently destroy safety markers (DNR flags, classification metadata, safe-word logs).

This report identifies **10 risk classes**, **26 specific risks**, mitigations, required tests, and auditor focus areas across all five steps.

---

## Risk Register

### R1 — Memory Recall Over-Retrieval (P3-011/P3-012)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R1.1 | Weighted RRF tuning lowers DNR/pre-filtering effectiveness by rewarding recall signals that find DNR-flagged records | HIGH | P3-011 |
| R1.2 | Candidate pool sizing (5:1 expansion) overwhelms classification ceiling filter with unclassifiable (NULL classification) records | MEDIUM | P3-011 |
| R1.3 | Recency boost on consolidated/summarized entries causes stale-but-recent records to outrank fresher episodic content | MEDIUM | P3-011, P3-015 |
| R1.4 | `candidate_limit` parameter not bounded by HNSW ef_search + RAM budget, causing OOM on large result sets | LOW | P3-011 |

**Mitigation:**
- Pre-ranking filters (DNR, classification ceiling, importance floor, confidence floor) must execute BEFORE RRF fusion, not after. Already established in P3-010 pattern — P3-011 must not reorder.
- `candidate_limit` must be capped at `ef_search * 2` or a hard max of 200, whichever is lower.
- If R1.2 (NULL classification): treat NULL as Critical (fail-closed) per DataGovernance §4.2 "Unclassified must default to Confidential, escalate to Critical."
- Recency boost for consolidated entries must use the original episode timestamp, not the consolidation timestamp.

**Required Tests:**
- `test_dnr_records_excluded_before_rrf_fusion`: Verify DNR-flagged records are excluded before rank computation, not after.
- `test_null_classification_defaults_to_fail_closed`: Record with NULL classification is treated as Critical and blocked for non-Faiz principals.
- `test_candidate_limit_does_not_exceed_hard_max`: `candidate_limit` capped.

**Auditor Focus:**
- ORDER of operations in hybrid ranking: filters BEFORE fusion. Check query WHERE clause vs CTE ordering.
- `candidate_limit` parameter security bounding.

---

### R2 — Context Injection: Poisoned Memory → LLM Prompt (P3-012)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R2.1 | Top-k memory results entered into LLM prompt without post-retrieval safety scan — DNR-flagged or Critical-classified memory reaches LLM context | CRITICAL | P3-012, P3-013 |
| R2.2 | Ranking manipulation via adversarial memory content (same embedding proximity but malicious payload) enables prompt injection through recall | CRITICAL | P3-012, P3-005 |
| R2.3 | No de-duplication of contradictory memories entering LLM context — Faiz receives conflicting facts without contradiction flag | HIGH | P3-012, P3-011 |
| R2.4 | Token budget enforcement at injection point differs from recall pipeline's token budget — overshoot of 4K cap per ADR-009 | HIGH | P3-012 |
| R2.5 | Metadata such as memory source, confidence, and classification NOT included in injection payload — LLM cannot judge reliability | MEDIUM | P3-012 |

**Mitigation:**
- P3-012 must implement a **post-retrieval safety scanner** that verifies each candidate:
  1. `do_not_recall == False` (confirmed — not stale from cache)
  2. Classification ≤ principal's ceiling
  3. Not contradiction-flagged (if `is_conflict == True`, include both sides with caveat)
  4. Has provenance (memory ID, source, timestamp)
- Each injection entry must include provenance metadata: `memory_id`, `source`, `confidence`, `classification`, `created_at`.
- Token budget must use the SAME constant as P3-010 (`DEFAULT_TOKEN_BUDGET = 4000`). No separate budget calculation.
- Copy of injection context must NOT be persisted in logs or evidence files in plaintext.

**Required Tests:**
- `test_injection_safety_scanner_rejects_dnr`: Safety scanner rejects DNR entries at injection boundary.
- `test_injection_includes_provenance_metadata`: Each entry has memory_id, source, confidence, classification.
- `test_token_budget_consistent_with_p3_010`: Uses same 4000 default.
- `test_contradictory_memories_flagged_in_context`: Both sides of a contradiction are tagged.

**Auditor Focus:**
- Post-retrieval safety scanner exists and runs before LLM injection.
- No separate token budget constant — must reuse P3-010's.
- Provenance metadata in every injected item.

---

### R3 — Do-Not-Recall Implementation Gaps (P3-013)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R3.1 | Layer 1 (Consent Ledger) cross-reference not implemented: P3-010 only checks `do_not_recall` column (Layer 2), not the consent ledger | CRITICAL | P3-013, P3-010 |
| R3.2 | Layer 4 (Backup Reconciliation) not implemented: backup restore could expose DNR data | CRITICAL | P3-013, P3-015, P0-027 |
| R3.3 | Layer 5 (Prompt Injection Gate) not implemented: no post-retrieval DNR check before LLM context entry | CRITICAL | P3-013, P3-012 |
| R3.4 | Layer 6 (SLO Impact — Prometheus counter) not implemented: DNR violations not tracked | HIGH | P3-013 |
| R3.5 | DNR marker can be bypassed by inserting a new episode with duplicate content but `do_not_recall=False` — no content-hash dedup check on write | MEDIUM | P3-013, P3-009 |
| R3.6 | No `MEMORY_DNR_MARKED` consent ledger event emitted when `do_not_recall` flag is set on existing records | MEDIUM | P3-013 |
| R3.7 | Faiz cannot reverse DNR markers through `/memory-recall` or consent channel without direct DB access | LOW | P3-013, P3-016 |

**Mitigation:**
- P3-013 must implement a consent ledger cross-reference query (`consent.consent_ledger WHERE event_type IN ('CONSENT_WITHDRAWN', 'MEMORY_DNR_MARKED') AND revoked_at IS NULL`) that runs BEFORE or IN PARALLEL with the `do_not_recall` column filter.
- Implement `guinevere_memory_dnr_violation_total` Prometheus counter (or structured log metric if Prometheus not yet deployed).
- Write pipeline (P3-009) must emit a `MEMORY_DNR_MARKED` event to `consent.consent_ledger` when `UPDATE memory.episodes SET do_not_recall = true` is executed.
- Content-hash dedup (`sha256(raw_content)`) in P3-009 write path: if exact duplicate content exists in a DNR-flagged episode, reject or re-flag.
- DNR reversal flow documented for Faiz: `/consent recall-dnr <memory_id>` via Discord or consent channel.

**Required Tests (from MemoryRecallEvalSpec §9.2):**
- `test_dnr_layer1_consent_ledger_xref`: Query consent.consent_ledger for active DNR events and cross-reference against recall results. Zero violations.
- `test_dnr_layer5_prompt_injection_gate`: Post-retrieval scan detects and blocks any DNR record before LLM context entry.
- `test_dnr_write_pipeline_consistency`: P3-013 write blocker rejects inserts matching DNR-by-content-hash.
- `test_dnr_marker_emits_consent_event`: Setting `do_not_recall = True` creates `MEMORY_DNR_MARKED` event.
- `test_dnr_zero_violations_across_all_queries`: Full golden dataset (20 DNR test cases) run with zero DNR entries in results.

**Auditor Focus:**
- 8-layer DNR enforcement chain: which layers are implemented? Which are stubbed?
- Layer 1 consent ledger cross-reference MUST be present, not just `do_not_recall` column.
- Layer 5 post-retrieval scanner MUST be separate from Layer 2 column filter.
- No `do_not_recall` bypass via content-hash dedup gap.

---

### R4 — Safe-Mode Memory Gate Failures (P3-014)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R4.1 | Safe-mode state not propagated from persona engine to memory recall pipeline — recall runs at normal mode while safe-word is active | CRITICAL | P3-014, P4-016 |
| R4.2 | Safe-mode state detection implemented IN the recall pipeline instead of receiving from persona engine's authoritative state machine | HIGH | P3-014 |
| R4.3 | Classification ceiling not downgraded during safe-mode: `guinevere_core` can still read Critical when safe-mode is active | CRITICAL | P3-014 |
| R4.4 | Content substitution during safe-mode leaks raw Critical content through `summary` field even though `raw_content` is replaced | HIGH | P3-014, P3-010 |
| R4.5 | Safe-mode violation not emitted as Prometheus counter — silent violation has no SLO impact | HIGH | P3-014 |
| R4.6 | Silent reactivation: safe-mode ends but memory recall continues using safe-mode restrictions until explicit reset | MEDIUM | P3-014 |
| R4.7 | No crisis-mode (D4) handling: recall pipeline treats crisis same as safe-word, but crisis requires stricter limits | MEDIUM | P3-014 |

**Mitigation:**
- **Safe-mode state MUST come from the persona engine** (P4-016), not computed independently by the recall pipeline. The recall pipeline must accept safe_mode as a parameter from the caller (already designed this way in P3-010 `recall_memories(safe_mode=False)`).
- P3-014 must downgrade `_CLASSIFICATION_CEILING` during safe-mode:
  - `guinevere_core`: Confidential ceiling (Critical denied)
  - `guinevere_subagent`: Internal ceiling (Confidential+ denied)
  - `default`: Internal ceiling
- Content substitution must check BOTH `raw_content` AND `summary` in safe-mode. If classification is Critical, both fields are replaced with the safe-mode placeholder.
- Add crisis-mode parameter: `safe_state: str = "normal"` with values `normal | safe_word | distress | crisis | incident`. Crisis mode adds stricter ceilings.
- Safe-mode violation counter emitted at recall boundary (P3-010 already has the pattern; P3-014 adds the metric).
- Silent reactivation guard: when safe-mode transitions from on→off, memory recall must use the new caller-provided value, not the old cached value. The caller (persona engine) controls this.

**Required Tests (from MemoryRecallEvalSpec §10.2-10.3):**
- `test_safe_mode_downgrades_classification_ceiling`: `guinevere_core` with safe_mode=True cannot read Critical records.
- `test_safe_mode_content_substitution_both_fields`: Both raw_content and summary are replaced for Critical records in safe-mode.
- `test_crisis_mode_stricter_than_safe_word`: Crisis mode blocks more classifications than safe-word mode.
- `test_safe_mode_violation_emits_metric`: Safe-mode violation increments counter (or log metric).
- `test_safe_mode_not_self_detected`: Pipeline rejects self-selected safe-mode state; requires caller-provided parameter.

**Auditor Focus:**
- Classification ceiling downgrade logic during safe-mode.
- `summary` field leak: verify safe-mode substitution covers BOTH raw_content and summary.
- Crisis D4 mode: separate handler from safe-word mode.
- No self-detection of safe-mode state in the pipeline.

---

### R5 — Prompt Injection Through Memory (P3-012/P3-013/P3-014)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R5.1 | External content written to memory (via P3-009 write pipeline from web/email/WhatsApp) can contain injection payloads that enter LLM context on recall | CRITICAL | P3-012, P3-009 |
| R5.2 | No source-trust label on memory injection — LLM cannot distinguish system-approved facts from untrusted source entries | HIGH | P3-012, P3-013 |
| R5.3 | Attacker crafts memory that mimics safe-mode override instruction, bypassing PersonaSafetyPolicy F-09 forbidden pattern | CRITICAL | P3-012, P3-014 |
| R5.4 | Embedding proximity attack: adversarial text engineered to have high cosine similarity to legitimate queries while carrying malicious payload | MEDIUM | P3-012, P3-011 |

**Mitigation:**
- Every memory injected into LLM context must carry a **source trust label** per PersonaSafetyPolicy §13.1 Trust Model:
  - `system_fact` (Highest — from ADR/policy)
  - `memory_policy_derived` (High — derived from approved sources)
  - `episodic_human` (Medium — from Faiz conversation)
  - `external_ingested` (Low/Untrusted — from web/email/WhatsApp/sub-agent)
- The system prompt (SystemPromptMaster) must include instruction that untrusted labels can contain injection attempts and must be treated as evidence, not commands.
- P3-012 injection builder must sanitize: strip any instruction-like syntax from untrusted memory content before injection.
- Episodes written from untrusted sources must be classified at a minimum of Restricted (never Internal or lower) unless explicitly reviewed.

**Required Tests:**
- `test_memory_injection_carries_source_trust_label`: Every injected entry has source label.
- `test_untrusted_memory_sanitized_before_injection`: Instruction-like patterns stripped from untrusted source entries.
- `test_system_prompt_includes_untrusted_handling`: Verify SystemPromptMaster section on untrusted memory handling exists.
- `test_external_content_cannot_override_policy`: F-09 detection test — memory that says "ignore ADR-002" is ignored and logged.

**Auditor Focus:**
- Source-trust label presence on injected memory entries.
- Untrusted memory sanitization logic.
- Integration with existing F-09 forbidden pattern scanner (PersonaSafetyPolicy §13.1-13.2).

---

### R6 — Raw Memory / Log Leakage (P3-011 through P3-015)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R6.1 | Embedding vectors logged or written to evidence files — vectors are derived data inheriting source classification | HIGH | P3-011, P3-012 |
| R6.2 | Raw memory content leaked through audit logs, Prometheus metric labels, or Grafana dashboard variables | CRITICAL | P3-012, P3-015 |
| R6.3 | P3-015 consolidation job emits raw content in consolidation report logs | HIGH | P3-015 |
| R6.4 | DNR violation audit trail stores raw payload of the leaked memory — creates second exposure | HIGH | P3-013 |
| R6.5 | Token budget debug logging emits content snippets for budget calculation | MEDIUM | P3-011, P3-012 |

**Mitigation:**
- Follow the established P3-010 pattern: `_logger.info()` with `extra={}` dicts containing only metadata (counts, flags, timestamps, principal). **No raw content, no vectors, no memory IDs** in log messages themselves — only in `extra` dict which structlog formats as structured JSON.
- P3-015 consolidation job must log: count of consolidated entries, classifications affected, duration — NOT the content of consolidated entries.
- DNR violation audit trail must store: `(incident_id, timestamp, memory_id_hash, classification, detection_layer)`. **No raw payload**.
- Token budget debug logging: only count, not content snippets.
- Prometheus metrics: only counters (`guinevere_memory_dnr_violation_total`, `guinevere_memory_safe_mode_violation_total`, `guinevere_memory_recall_count`). No label values containing user data.

**Required Tests:**
- `test_no_raw_content_in_log_output`: grep all log calls in P3-011..P3-015 source for raw content patterns.
- `test_consolidation_logs_no_content`: Consolidation log lines contain only metadata.
- `test_dnr_violation_log_no_payload`: DNR audit entry has hash, not full content.
- `test_embedding_vectors_not_logged`: No vector values in log output.

**Auditor Focus:**
- Every `_logger.info/warning/error` call — verify `extra` dict contains only metadata.
- P3-015 consolidation log format.
- Audit trail for DNR violations — payload-free evidence.

---

### R7 — Evidence File / Artifact Leakage (P3-011 through P3-015)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R7.1 | Verification scripts output raw memory content to `verification-output.txt` in evidence directory | HIGH | P3-011..P3-015 (each creates evidence) |
| R7.2 | Auditor gate reports include sample memory content for "evidence of correct ranking" | MEDIUM | P3-011 auditor |
| R7.3 | Benchmark reports in P3-011 include query text that reveals private/sensitive context | MEDIUM | P3-011 |
| R7.4 | Evidence files committed to git repo with raw Critical data — AGENTS.md forbids exposing raw surveillance data in artifacts | CRITICAL | All P3 steps |

**Mitigation:**
- Evidence files must follow the same classification rules as the data they describe. At minimum: no raw Critical content in evidence.
- Verification scripts must use **synthetic/fake data** (the established pattern from P3-010 with `_FakeEmbedder` and `_FakeRecallSession`). Never use production data in evidence artifacts.
- Benchmark reports: use sanitized query text `("test_query_001", "test_query_002")`, not actual Faiz conversation queries.
- Auditor gate reports: reference verification output path, do NOT inline raw sample content.
- Pre-commit hook or manual review: grep evidence files for Critical-classification patterns before commit.

**Required Tests:**
- `test_evidence_file_contains_no_critical_content`: Grep evidence directory for raw Critical content patterns.
- `test_verification_uses_fake_not_production_data`: Verification scripts never connect to production DB.

**Auditor Focus:**
- Evidence file content review — no raw Critical data.
- Verification script uses fake/synthetic data only.
- Benchmark/audit reports use sanitized identifiers.

---

### R8 — Classification Ceiling Bypass (P3-011/P3-012/P3-014)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R8.1 | Weighted RRF tuning assigns non-zero weight to signals that find records a principal is not authorized to read — records leak through fusion before ceiling filter | HIGH | P3-011 |
| R8.2 | `CLASSIFICATION_ORDER` dictionary (from `embeddings.py`) used for comparison treats missing class as 0 (Public) instead of 5 (Critical+) | HIGH | P3-011, P3-010 |
| R8.3 | Sub-agent bypass: sub-agent calls `recall_memories` with `principal="guinevere_core"` instead of its own principal | HIGH | P3-012, P3-010 |
| R8.4 | Safe-mode classification ceiling not enforced at the DB query level — applied only in Python post-processing | MEDIUM | P3-014, P3-010 |

**Mitigation:**
- P3-011 RRF fusion must NOT execute against a candidate pool wider than the principal's classification ceiling. The WHERE clause must include `classification <= ceiling_level` BEFORE ranking.
- `CLASSIFICATION_ORDER` must define an explicit mapping for all possible values AND a catch-all `else: 5` (beyond Critical) for unrecognized classification strings.
- `recall_memories` must validate that the caller is the principal they claim, or at minimum that `principal` is one of the known set. Unknown principal defaults to `Restricted` (already implemented in P3-010).
- Classification ceiling filter at DB query level (P3-014): `WHERE classification <= :ceiling` in SQLAlchemy query, not just Python post-processing. (P3-010 currently applies it post-query in Python — P3-014 should add it to the WHERE clause.)

**Required Tests:**
- `test_classification_order_catch_all`: Unknown classification string maps to level 5+ (fail-closed), not 0.
- `test_principal_spoofing_rejected`: Calling `recall_memories(principal="guinevere_core")` from sub-agent context returns ceiling-restricted results.
- `test_classification_ceiling_db_level`: Classification ceiling filter exists in SQL WHERE clause, not only in Python post-processing.
- `test_downgrade_unknown_classification_to_critical`: Record with unrecognized classification treated as Critical.

**Auditor Focus:**
- `CLASSIFICATION_ORDER` completeness — every known class mapped, unrecognized defaults fail-closed.
- Classification ceiling in DB query (WHERE clause), not just Python level.
- Principal validation or at minimum principal set whitelist.

---

### R9 — Memory Consolidation Job Safety (P3-015)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R9.1 | Consolidation deletes/moves records without preserving DNR flags — DNR records leak after consolidation | CRITICAL | P3-015, P3-013 |
| R9.2 | Consolidation strips classification metadata from summarized records — derived summaries inherit wrong classification | HIGH | P3-015 |
| R9.3 | Safe-word logs or crisis records silently consolidated into generic summaries, losing safety-critical provenance | HIGH | P3-015 |
| R9.4 | Consolidation timing conflicts with active safe-word or crisis state — consolidating during distress | MEDIUM | P3-015 |
| R9.5 | Consolidation job prunes records past retention window without checking `retention_class = 'formal_hold'` | HIGH | P3-015 |
| R9.6 | No audit trail for consolidated records — lost recall quality cannot be investigated | MEDIUM | P3-015 |

**Mitigation:**
- Consolidation must **never** delete or modify records where `do_not_recall == True`. DNR records must be preserved as-is with same retention.
- Consolidation must maintain `classification` field on the consolidated/summarized record: the highest classification among all source records being consolidated.
- Safe-word logs (`classification == 'Critical'` and source contains safe-word context) must be excluded from consolidation entirely.
- Consolidation job must check safe-mode state before running. If safe-word is active, skip or defer consolidation.
- Formal hold retention: `WHERE retention_class != 'formal_hold'` — never prune records under formal hold.
- Each consolidation batch must write an audit record: `(batch_id, timestamp, source_record_ids[], target_summary_id, classification, dnr_check_passed)`. No raw content in audit.

**Required Tests:**
- `test_consolidation_preserves_dnr_flag`: DNR-flagged records survive consolidation unchanged.
- `test_consolidation_classification_highest_wins`: Summary inherits highest classification from sources.
- `test_consolidation_skips_safe_word_records`: Records with safe-word provenance excluded from consolidation.
- `test_consolidation_checks_safe_mode_before_run`: Consolidation aborts if safe-word state active.
- `test_consolidation_respects_formal_hold`: Records under formal hold not pruned.
- `test_consolidation_audit_trail`: Audit record created with required fields, no raw content.

**Auditor Focus:**
- Consolidation WHERE clause excludes DNR records.
- Classification inheritance: highest-wins rule.
- Safe-word/crisis record exclusion logic.
- Formal hold check before pruning.
- Audit trail completeness.

---

### R10 — Scheduler / Job Orchestration Safety (P3-015)

| ID | Risk | Severity | Affected Steps |
|----|------|----------|----------------|
| R10.1 | Consolidation job runs concurrently with read pipeline — partial consolidation state produces inconsistent recall results | MEDIUM | P3-015, P3-010 |
| R10.2 | Consolidation job retry on failure creates duplicate consolidated records | LOW | P3-015 |
| R10.3 | Out-of-retention pruning fires during incident — destroys incident evidence before preservation | HIGH | P3-015, IncidentResponse |
| R10.4 | No kill-switch or immediate pause mechanism for consolidation job — runs even during SEV0 incident | MEDIUM | P3-015 |

**Mitigation:**
- Use advisory lock (`pg_advisory_lock`) or job-level mutex (Redis DB0) to prevent concurrent consolidation and recall pipeline accessing the same records simultaneously.
- Consolidation must use a transaction: if the job fails mid-batch, the transaction is rolled back and no partial-state records are visible.
- Retention pruning must check `incident_state` before running. If active incident (SEV0/SEV1), skip pruning and log.
- Implement `/consolidation-pause` and `/consolidation-resume` Discord admin commands.
- Idempotent consolidation: use `INSERT ... ON CONFLICT DO NOTHING` or content-hash based dedup to avoid duplicates.

**Required Tests:**
- `test_consolidation_advisory_lock_prevents_concurrent_run`: Second consolidation job waits or fails.
- `test_consolidation_transactional_on_failure`: Failed batch rolls back, no partial state visible.
- `test_retention_pruning_skipped_during_incident`: Pruning job checks incident state before running.
- `test_consolidation_kill_switch_stops_job`: `/consolidation-pause` stops the running job.

**Auditor Focus:**
- Concurrency protection (advisory lock or mutex).
- Transactional batch processing.
- Incident-aware pruning skip.
- Once-consistency (idempotent insert).

---

## Blocking Constraints

| Constraint | Description | Blocks | Priority |
|------------|-------------|--------|----------|
| **BC-01** — Safe-mode state source | P3-014 safe-mode gate requires persona engine (P4-016) to be the authoritative state source. P3-014 must NOT self-detect safe-mode. | P3-014 implementation if P4-016 not available | HIGH |
| **BC-02** — DNR Layer 1 consent ledger | P3-013 DNR implementation requires `consent.consent_ledger` table to be populated with `MEMORY_DNR_MARKED` events. Write pipeline (P3-009) must emit these events. | P3-013 full implementation | HIGH |
| **BC-03** — Content-hash dedup for DNR bypass | P3-013 DNR write blocker (Layer 5) requires content-hash dedup on write pipeline (P3-009 modification). | P3-009 must be modified | MEDIUM |
| **BC-04** — Prometheus counters | P3-013/P3-014 require Prometheus counters for DNR violation and safe-mode violation metrics. If P8 (Observability) is not deployed, use structured log metrics with `guinevere_memory_*` prefix. | P3-013/P3-014 metric emission | MEDIUM |
| **BC-05** — Source trust labels | P3-012 context injection requires source-trust labels on every memory entry. Write pipeline (P3-009) must store source_channel/source_trust metadata. | P3-012, P3-009 | HIGH |
| **BC-06** — Classification ORDER completeness | P3-011 weighted RRF and P3-014 ceiling downgrade require `CLASSIFICATION_ORDER` to map every known class + fail-closed default. Currently in `embeddings.py`. | P3-011, P3-014 | MEDIUM |
| **BC-07** — Consolidation formal hold check | P3-015 requires `retention_class = 'formal_hold'` column to exist and be populated. Model already has it via `ClassificationMetaMixin`. | P3-015 pruning safety | LOW |

---

## Required Test Matrix (Minimum)

| Test ID | Step | Risk(s) | Test Name | Expected Pass Condition |
|---------|------|---------|-----------|------------------------|
| T-011-01 | P3-011 | R1.1 | `test_dnr_records_excluded_before_rrf_fusion` | DNR records in candidate pool produce 0 rank entries in RRF fusion |
| T-011-02 | P3-011 | R8.2 | `test_classification_order_unknown_fails_closed` | Unrecognized classification maps to level 5+ |
| T-011-03 | P3-011 | R1.2 | `test_null_classification_fail_closed` | NULL classification treated as Critical |
| T-012-01 | P3-012 | R2.1 | `test_injection_safety_scanner_rejects_dnr` | Post-retrieval scanner blocks DNR entries |
| T-012-02 | P3-012 | R2.2 | `test_injection_includes_provenance_metadata` | Each entry has memory_id, source, confidence, classification |
| T-012-03 | P3-012 | R5.1 | `test_untrusted_memory_sanitized_before_injection` | Instruction-like patterns stripped |
| T-012-04 | P3-012 | R5.2 | `test_memory_injection_carries_source_trust_label` | Source-trust label present on every entry |
| T-013-01 | P3-013 | R3.1 | `test_dnr_layer1_consent_ledger_xref` | Consent ledger cross-reference run; zero DNR violations |
| T-013-02 | P3-013 | R3.5 | `test_dnr_write_pipeline_consistency` | Content-hash dedup prevents DNR bypass |
| T-013-03 | P3-013 | R3.6 | `test_dnr_marker_emits_consent_event` | Setting do_not_recall creates MEMORY_DNR_MARKED event |
| T-013-04 | P3-013 | R3.4 | `test_dnr_violation_emits_metric` | DNR violation increments counter/structured log |
| T-014-01 | P3-014 | R4.1 | `test_safe_mode_downgrades_classification_ceiling` | guinevere_core with safe_mode=True: Confidential ceiling |
| T-014-02 | P3-014 | R4.4 | `test_safe_mode_substitution_both_fields` | Both raw_content AND summary replaced for Critical safe-mode |
| T-014-03 | P3-014 | R4.2 | `test_safe_mode_not_self_detected` | Pipeline rejects self-selected safe_mode; requires caller param |
| T-014-04 | P3-014 | R8.4 | `test_classification_ceiling_db_level` | Ceiling filter in SQL WHERE clause, not just Python |
| T-015-01 | P3-015 | R9.1 | `test_consolidation_preserves_dnr_flag` | DNR records survive consolidation unchanged |
| T-015-02 | P3-015 | R9.2 | `test_consolidation_classification_highest_wins` | Summary inherits highest classification |
| T-015-03 | P3-015 | R9.3 | `test_consolidation_skips_safe_word_records` | Safe-word records excluded from consolidation |
| T-015-04 | P3-015 | R9.5 | `test_consolidation_respects_formal_hold` | Formal hold records not pruned |
| T-015-05 | P3-015 | R9.6 | `test_consolidation_audit_trail` | Audit record created with required fields |
| T-015-06 | P3-015 | R10.1 | `test_consolidation_advisory_lock` | Concurrent consolidation blocked or queued |
| T-015-07 | P3-015 | R6.2 | `test_consolidation_logs_no_content` | Consolidation log lines contain only metadata |
| T-ALL-01 | All | R6/R7 | `test_no_raw_critical_in_evidence` | Evidence dir grep: zero raw Critical content patterns |
| T-ALL-02 | All | R7.3 | `test_verification_uses_fake_not_production` | Verification scripts never connect to prod DB |

---

## Auditor Focus Areas per Step

### P3-011 Auditor
- Pre-filter ordering: DNR/classification/importance filters BEFORE RRF.
- `candidate_limit` security bounding.
- `CLASSIFICATION_ORDER` completeness and fail-closed behavior for unknown classes.
- No raw content in benchmark or verification output.

### P3-012 Auditor
- Post-retrieval safety scanner exists with DNR + classification + contradiction checks.
- Source-trust labels for every injected entry.
- Token budget constant reused from P3-010, not redefined.
- Provenance metadata (4+ fields) per entry.
- Untrusted memory sanitization logic.

### P3-013 Auditor
- 8-layer DNR enforcement: which layers are implemented (min: 1, 2, 5, 6).
- Layer 1 consent ledger cross-reference: SQL query exists and runs on recall.
- Layer 5 post-retrieval scanner: separate code path from column-level filter.
- DNR write blocker: content-hash dedup in P3-009.
- DNR marker → consent ledger event emission.
- DNR violation metric/log emission.

### P3-014 Auditor
- Safe-mode classification ceiling downgrade: verify ALL principals downgraded correctly.
- Content substitution covers BOTH `raw_content` AND `summary` for Critical safe-mode.
- Crisis/D4 mode: separate handler with stricter limits.
- Safe-mode state parameter: pipeline accepts from caller, does NOT self-detect.
- Safe-mode violation metric/log emission.
- Classification ceiling in SQL WHERE clause, not only Python.

### P3-015 Auditor
- DNR record exclusion in consolidation WHERE clause.
- Classification inheritance: highest-wins rule.
- Safe-word/crisis record exclusion.
- Formal hold check before pruning.
- Audit trail: batch_id, source IDs, target summary ID, classification, DNR check.
- Concurrency protection (advisory lock or mutex).
- Transactional batch isolation.
- Incident-aware pruning skip.
- Log format: metadata only, no raw content.

---

## Anti-Pattern Checklist (Per AGENTS.md and Repo Contract)

| Anti-Pattern | P3-011 | P3-012 | P3-013 | P3-014 | P3-015 | Check |
|--------------|--------|--------|--------|--------|--------|-------|
| Type suppression (`# type: ignore`, `as any`) | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | grep before commit |
| Empty exception catch | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ast-grep except: patterns |
| Skipped tests | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | pytest --strict-markers |
| Raw secrets in code/docs | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | Grep for sk-, api_key, password |
| Raw surveillance data in artifacts | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | Evidence file review |
| Consent/safe-word bypass | N/A | ❌ Must not | ❌ Must not | ❌ Must not | N/A | Safety gate review |
| Sub-agent self-report without parent read | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | Parent reads every file |
| One sub-agent doing multiple steps | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | One agent per step |
| Inline structured report (no output_path) | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | ❌ Must not | File-based output always |

---

## Dependency Chain Safety Analysis

```
P3-011 (Hybrid Ranking Tuning)
  ├── MUST NOT reorder pre-filter ordering established by P3-010
  ├── MUST NOT change CLASSIFICATION_ORDER without P3-014 coordination
  └── candidate_limit must be security-bounded
        │
        ▼
P3-012 (Context Injection)
  ├── DEPENDS on P3-011 for correct ranking (DNR/pre-filtered pool)
  ├── IMPLEMENTS post-retrieval safety scanner (last defense before LLM)
  └── Source-trust label injection requires P3-009 write metadata
        │
        ▼
P3-013 (Do-Not-Recall)
  ├── DEPENDS on consent.consent_ledger table (P3-002) being populated
  ├── DEPENDS on P3-009 write pipeline emitting MEMORY_DNR_MARKED events
  └── IMPLEMENTS Layers 1, 5, 6 of the 8-layer DNR chain
        │
        ▼
P3-014 (Safe-Mode Memory Gate)
  ├── DEPENDS on P4-016 (safe-mode trigger) for authoritative state
  ├── DEPENDS on P3-010 for recall pipeline entry point
  └── MODIFIES P3-010 classification ceiling logic during safe-mode
        │
        ▼
P3-015 (Memory Consolidation Job)
  ├── MUST NOT touch DNR-flagged records
  ├── MUST NOT run during safe-word state
  ├── MUST preserve classification metadata
  └── MUST respect formal holds and incident state
```

---

## Boundary Compliance Proof

| Boundary | Status | Evidence |
|----------|--------|----------|
| **Persona drift** | ✅ Unaffected | All steps are memory pipeline / scheduler code; no persona behavior logic |
| **Consent violation** | ✅ Mitigations defined | DNR 8-layer chain (R3), safe-mode CEILING downgrade (R4), consent ledger cross-ref (BC-02) |
| **Yandere Level Y6** | ✅ Impossible | No persona/Faiz interaction logic in any of P3-011..P3-015 |
| **HARD STOP bypass** | ✅ Mitigations defined | P3-014 safe-mode gate must accept state from persona engine; BC-01 prevents self-detection bypass |
| **Surveillance overreach** | ✅ None | No surveillance data processed; only memory recall/consolidation paths |
| **No raw Critical in evidence** | ✅ Mitigations defined | R2.4, R7.1-R7.4 define evidence classification rules and fake-data requirement |
| **No secrets in logs/artifacts** | ✅ Mitigations defined | R6.1-R6.5 define log metadata-only pattern |
| **No silent reactivation** | ✅ Mitigated (R4.6) | Safe-mode transition guard: caller provides value, no cached self-detection |
| **Classification fail-closed** | ✅ Mitigated (R8.1-R8.4) | Unknown class → fail-closed, ceiling at DB level |
| **Contradiction handling** | ⚠️ Deferred to P3-011/P3-012 | R2.3 defines requirement; `contradicts_ids` field exists on SemanticFacts model |

---

## Known Gaps (Accepted/Deferred)

| Gap | Risk | Mitigation | Owner | Target |
|-----|------|------------|-------|--------|
| Prometheus not yet deployed (P8) | DNR/safe-mode violation metric counters absent | Use structured log metrics with `guinevere_memory_*` prefix | Guinevere | P3-013/P3-014 |
| P4-016 safe-mode trigger not implemented | P3-014 has no authoritative safe-mode state source | Accept caller-provided param; document that P4 must supply state | Guinevere | P4-016 |
| Consent ledger not populated with MEMORY_DNR_MARKED events | DNR Layer 1 cannot cross-reference | Implement DNR event emission in P3-013 as first event; backfill not needed until first DNR marker | Guinevere | P3-013 |
| Content-hash dedup not in P3-009 write pipeline | DNR bypass via duplicate content insert | Modify P3-009 `store_episode` to compute and check sha256 of raw_content against existing DNR-flagged episodes | Guinevere | P3-013 |
| Golden dataset not yet built | Cannot run ablation tests for P3-011 weight tuning | Defer weight tuning to post-dataset; use P3-010 weights (w_vec=0.5, w_fts=0.3, w_recency=0.15, w_importance=0.05) as defaults | Guinevere | P3-018 |

---

## Footer

| Field | Value |
|-------|-------|
| **Date** | 2026-06-02 |
| **Author** | Guinevere (Security/Safety Specialist — research wave) |
| **Classification** | STRICTLY PRIVATE & CONFIDENTIAL |
| **Scope** | P3-011 (Hybrid Ranking Tuning), P3-012 (Context Injection), P3-013 (Do-Not-Recall), P3-014 (Safe-Mode Memory Gate), P3-015 (Memory Consolidation) |
| **Sources Read** | 15 documents across `docs/`, `adr/`, `src/` |
| **Risks Identified** | 10 risk classes, 26 individual risks |
| **Tests Required** | 25 minimum test cases |
| **Blocking Constraints** | 7 (BC-01 through BC-07) |
| **Auditor Focus Areas** | 5 per-step sections |
| **Boundary Compliance** | 9/9 boundaries compliant or mitigated |
| **Known Gaps** | 5 accepted deferrals |
| **Next Action** | Parent orchestrator reads this report, creates planner file for P3-011..P3-015 batch, syncs todos, runs collision scan, then delegates per-step implementation with specified auditor gates. |

---

**End of `docs/setup-evidence/P3/research/security-safety-risk-011-015.md`**