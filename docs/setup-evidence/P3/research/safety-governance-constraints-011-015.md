# P3-011 through P3-015 — Safety and Governance Constraints Research Report

**Date:** 2026-06-02
**Author:** Guinevere (research wave)
**Status:** Complete

## 1. Source Documents Inspected

| Source | Path | Role |
|--------|------|------|
| PersonaSafetyPolicy v1.0 | docs/60-persona/60-PersonaSafetyPolicy_v1.0.md | Safe word, distress, safe-mode, forbidden patterns, Y0-Y6 baseline |
| ADR-Index v1.0 | docs/10-governance/17-ADR_Index_v1.0.md | ADR register, global safe word principle |
| ADR-009 | adr/ADR-009-memory-recall-semantic-search-strategy.md | Layered recall, token budget, HNSW params, classification |
| MemorySchema v2.0 | docs/00-core/04-MemorySchema_v2.0.md | do_not_recall, classification, embedding, search_vector |
| Acceptance Criteria v1.0 | docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md | AC-MEM-004, AC-MEM-005, AC-DATA-001, AC-SAFE-* |
| HardStopHandler | src/core/services/hard_stop_handler.py | is_safe property, check(), check_recovery() |
| PROGRESS.md | PROGRESS.md | P3 current state (10/19 complete) |
| CHECKLIST.md | CHECKLIST.md | Per-step verification commands |
| StepPrompts P3-011..P3-015 | stepprompts/StepPrompts.md lines 6265-6342 | Original step definitions |
| Read Pipeline P3-010 | src/memory/read_pipeline.py | Current DNR/safe-mode implementation |
| P3-010 Evidence | docs/setup-evidence/P3/STEP-P3-010/ | Verification 88/88 PASS + auditor PASS |
| Research: Hybrid Ranking | docs/setup-evidence/P3/research/hybrid-ranking-safety.md | DNR 8-layer chain, safe-mode gate, classification ceilings |
| Research: Doc/ADR Constraints | docs/setup-evidence/P3/research/docs-adr-step-constraints.md | Prior constraint analysis for P3-004..P3-010 |

## 2. Existing P3-010 Implementation: What Is Already In Place

The P3-010 read pipeline (src/memory/read_pipeline.py) already implements safety gates that P3-013/P3-014 build upon:

### 2.1 DNR Exclusion (Already Working)
- Query-level WHERE clause: All 3 query builders (vector, FTS, recency) include Episodes.do_not_recall.is_(False).
- Public API parameter: exclude_dnr: bool = True (default enabled).
- Return field: Results include id, safe_content, classification, importance, created_at, combined_score, is_summarized.

### 2.2 Classification Ceiling (Already Working)
- guinevere_core (default): Critical — everything readable
- guinevere_subagent: Confidential — Critical records excluded
- default (unknown): Restricted — fail-closed

### 2.3 Safe-Mode Critical Substitution (Already Working)
- _build_safe_content() replaces raw_content with SAFE_MODE_PLACEHOLDER when safe_mode=True AND classification is Critical.
- Placeholder: "[Content redacted per safe-mode policy - Critical classification]"
- Only Critical is substituted. Public/Internal/Confidential/Restricted returned raw.

### 2.4 Token Budget Enforcement (Already Working)
- Default: 4,000 tokens per recall cycle (DEFAULT_TOKEN_BUDGET).
- Mechanism: _apply_token_budget() trims results to fit budget, highest-score first.
- Estimation: len(text) // 4 heuristic.

### 2.5 What P3-010 Does NOT Cover
1. No consent ledger cross-reference (Layer 1 of DNR chain)
2. No safe-mode for non-Critical data
3. No identity-based content filtering beyond classification ceiling
4. No memory-level PII/secret scanning
5. No contradiction penalty or confidence threshold (deferred to P3-011)

## 3. P3-011: Hybrid Ranking - Constraints and Hazards

### 3.1 Definition
Combines vector similarity + FTS + recency decay.

### 3.2 Current State
P3-010 implements minimum viable hybrid ranking. RRF fusion uses vector and FTS signal ranks only. Recency and importance are multiplicative factors after RRF. Full weighted RRF with all 4 signals as rank inputs deferred to P3-011.

### 3.3 Binding Constraints
| Constraint | Source | Binding |
|------------|--------|---------|
| RRF fusion must use k=60 | ADR-009, batch plan | HARD |
| All queries must use DNR exclusion WHERE clause | P3-010, PersonaSafetyPolicy | HARD |
| Classification ceiling per principal after fusion | DataGovernance, P3-010 | HARD |
| Safe-mode substitution AFTER fusion, not before | P3-010 pattern | HARD |
| Token budget (4,000) caps final result set | ADR-009 | HARD |
| Contradiction penalty deferred | P3-010 auditor caveat | SOFT |

### 3.4 Implementation Hazards
HZ-01: P3-011 overwrites existing P3-010 safety gates — CRITICAL. Build on TOP of P3-010 recall_memories(), not replace.
HZ-02: Weighted RRF without DNR/classification/safe-mode guardrails — HIGH. All fusion functions must incorporate P3-010 gates.
HZ-03: Recency decay excludes Critical safety memories — MEDIUM. Importance >= 5 floor applies after classification ceiling.
HZ-04: Scoring semantics change vs P3-010 multiplicative approach — MEDIUM. Document change; separate test suites.

## 4. P3-012: Context Injection - Constraints and Hazards

### 4.1 Definition
Top-k memories injected into system prompt before LLM call.

### 4.2 Binding Constraints
| Constraint | Source | Binding |
|------------|--------|---------|
| Injected memories must use safe_content (not raw_content) | P3-010 return schema | HARD |
| Token budget per injection cycle must not exceed 4,000 | ADR-009 | HARD |
| DNR-tagged memories must NEVER enter LLM context | AC-MEM-005 | HARD |
| Critical data in safe mode must NEVER enter LLM context | PersonaSafetyPolicy 7.2 | HARD |
| Surveillance-derived context excluded during safe mode | PersonaSafetyPolicy 7.2(4) | HARD |
| Forbidden patterns scanned post-injection | PersonaSafetyPolicy 15.1(3) | HARD |

### 4.3 Implementation Hazards
HZ-05: Direct injection of raw_content instead of safe_content — CRITICAL.
HZ-06: Token budget overflow silent — HIGH. Enforce budget before assembly.
HZ-07: Forbidden patterns in injected memory not scanned — HIGH.
HZ-08: Surveillance context bleeds into safe-mode prompt — HIGH.
HZ-09: Memory injection occurs before safe-word detection — CRITICAL.

## 5. P3-013: Do-Not-Recall - Constraints and Hazards

### 5.1 Definition
UPDATE memory.episodes SET do_not_recall = true WHERE id = $1 blocks specific memories.

### 5.2 Current State
P3-010 already implements DNR exclusion at query level (all 3 query builders). P3-013 adds user-facing marking + consent ledger cross-reference + pre-injection verification.

### 5.3 Eight-Layer DNR Enforcement Chain
| Layer | Mechanism | Status | P3-013 Action |
|-------|-----------|--------|---------------|
| 1 - Consent Ledger | Cross-reference consent ledger | NOT IMPLEMENTED | Add ledger lookup |
| 2 - Memory Marker | do_not_recall = FALSE in WHERE | IMPLEMENTED (P3-010) | Reuse |
| 3 - Retention Class | Not in recall path | N/A | Deferred |
| 4 - Backup Reconciliation | Restore reapplies DNR | FUTURE | Design only |
| 5 - Pre-Injection Gate | DNR check before LLM | NOT IMPLEMENTED | Add post-recall verify |
| 6 - Prometheus Counter | Zero-tolerance metric | NOT IMPLEMENTED | Add metric |
| 7 - Faiz Rights | User-facing DNR marking | NOT IMPLEMENTED | mark_memory_dnr() |
| 8 - Incident Trigger | Unsafe recall audit | FUTURE | Deferred |

### 5.4 Binding Constraints
| Constraint | Source | Binding |
|------------|--------|---------|
| DNR flag prevents LLM context entry | AC-MEM-005 | HARD BLOCKING |
| Consent ledger cross-reference required | ConsentRevocationPolicy 10 | HARD |
| DNR must survive backup-restore | AC-DATA-006 | HARD |
| Faiz must have user-facing DNR mechanism | AC-DATA-003 | SOFT |
| DNR-flagged memories maintain classification metadata | DataGovernance | HARD |
| DNR violations increment Prometheus counter (zero-tolerance) | MemoryRecallEvalSpec 9.1 | SOFT |

### 5.5 DNR Marking API Requirements
mark_memory_dnr() must:
- Write UPDATE memory.episodes SET do_not_recall = true
- Write INSERT INTO consent.consent_ledger(event_type='MEMORY_DNR_MARKED')
- Restrict to guinevere_core principal (sub-agents denied)
- Accept memory_id (UUID), reason (str), principal (str)

unmark_memory_dnr() must:
- Write UPDATE memory.episodes SET do_not_recall = false
- Write INSERT INTO consent.consent_ledger(event_type='DNR_REVOKED')

### 5.6 Implementation Hazards
HZ-10: DNR marking without consent ledger entry — CRITICAL.
HZ-11: Sub-agent can set DNR flag — HIGH. Restrict to guinevere_core.
HZ-12: DNR flag not replicated to vector index — MEDIUM. WHERE clause is sufficient.
HZ-13: DNR not propagated during consolidation — HIGH.
HZ-14: No way to undo DNR — MEDIUM. Provide unmark_memory_dnr().
HZ-15: DNR audit counter missing — SOFT.

## 6. P3-014: Safe-Mode Memory Gate - Constraints and Hazards

### 6.1 Definition
During safe mode, only neutral summaries are injected, not raw emotional content.

### 6.2 Current State
P3-010 substitutes Critical content with placeholder when safe_mode=True. Only Critical is substituted. Safe-mode state is a parameter, not dynamically read from HardStopHandler.

### 6.3 Binding Constraints
| Constraint | Source | Binding |
|------------|--------|---------|
| Safe mode must use HardStopHandler.is_safe | PersonaSafetyPolicy 7.2 | HARD |
| Critical blocked in safe mode | PersonaSafetyPolicy 12.3 | HARD |
| Restricted redacted/summarized in safe mode | Extended scope | HARD |
| Confidential redacted/summarized in safe mode | PersonaSafetyPolicy 7.2(6) | HARD |
| Only neutral Public/Internal in safe mode | PersonaSafetyPolicy 7.2(6) | HARD |
| AC-SAFE-001 preserved: safe-word 100% success | AC-SAFE-001 | HARD BLOCKING |
| Surveillance memories not injected in safe mode | PersonaSafetyPolicy 7.2(4) | HARD |
| Emotional memories not injected in safe mode | PersonaSafetyPolicy 7.2(3) | HARD |
| Safe-mode checked at injection time, not just recall | MemoryRecallEvalSpec 10 | HARD |
| DNR exclusion still applies during safe mode | P3-010 design | HARD |
| No violation records for safe-mode memory access | PersonaSafetyPolicy 7.3 | HARD |
| Resume only via explicit Faiz confirmation | PersonaSafetyPolicy 7.4 | HARD |

### 6.4 Extended Safe-Mode Classification Ceiling
| Classification | Normal Mode | Safe Mode |
|----------------|-------------|-----------|
| Public | Raw content | Raw content (neutral) |
| Internal | Raw content | Raw content (neutral) |
| Confidential | Raw content | REDACTED/summarized |
| Restricted | Raw content | REDACTED/summarized |
| Critical | Purpose-gated raw | PLACEHOLDER (blocked) |
| Surveillance-derived | Raw content | BLOCKED entirely |
| Emotional/persona | Raw content | BLOCKED entirely |

### 6.5 Implementation Hazards
HZ-16: HardStopHandler.is_safe not checked before injection — CRITICAL.
HZ-17: Only Critical substituted in safe mode (not Restricted/Confidential) — HIGH.
HZ-18: Safe-mode gate only at recall, not injection — HIGH. Double-gate required.
HZ-19: Surveillance memory misclassification leaks during safe mode — HIGH.
HZ-20: Emotional/persona content not covered by classification ceiling — MEDIUM.
HZ-21: HardStopHandler singleton race condition on state — MEDIUM.
HZ-22: Safe-mode triggers other than is_safe missed — MEDIUM.
HZ-23: Placeholder text leaks classification level — LOW.

## 7. P3-015: Memory Consolidation Job - Constraints and Hazards

### 7.1 Definition
Daily consolidation: aggregate episodic into semantic memory.

### 7.2 Binding Constraints
| Constraint | Source | Binding |
|------------|--------|---------|
| Must exclude DNR-flagged episodes | AC-MEM-005, AC-DATA-003 | HARD |
| Must respect classification boundaries | DataGovernance 4.3 | HARD |
| Classification metadata preserved in consolidated records | DataGovernance | HARD |
| Safe-mode does not affect consolidation (background job) | PersonaSafetyPolicy | SOFT |
| Must not propagate forbidden patterns | PersonaSafetyPolicy 11 | HARD |
| Must maintain provenance links (source_episode) | MemorySchema v2.0 | HARD |
| Scheduled at 03:00 WIB | StepPrompts | SOFT |

### 7.3 Implementation Hazards
HZ-24: Consolidation promotes DNR episodes to semantic memory — CRITICAL.
HZ-25: LLM summarization hallucinates during consolidation — HIGH.
HZ-26: Consolidation fails silently — HIGH. Retry + log.
HZ-27: Duplicate semantic facts — MEDIUM. Upsert by subject+predicate.
HZ-28: Classification downgrade during consolidation — MEDIUM. Inherit highest class.
HZ-29: Stale consolidation due to missed cycles — LOW. Track last timestamp.

## 8. Safe Mode Behavior Specification

### 8.1 Trigger Points (PersonaSafetyPolicy 7.1)
1. Exact safe word tokens: "hard stop", "hardstop", "safe word", "safeword", "hentikan", "berhenti"
2. Semantic equivalents (regex): stop/pause/enough/too much + persona/mommy context; neutral/serious/safe mode; i need a break variants
3. High-confidence distress signals (D2+)

### 8.2 Safe Mode State (HardStopHandler)
SafetyState enum: NORMAL = "normal", SAFE = "safe"
HardStopHandler.is_safe returns true when state == SafetyState.SAFE
HardStopHandler.check(message) returns true if safe word triggered
HardStopHandler.check_recovery(message) returns true if user resumes
HardStopHandler.get_neutral_response() returns safe-mode message

### 8.3 Safe Mode Memory Behavior Summary
| Aspect | Behavior | Authority |
|--------|----------|-----------|
| Critical memory recall | BLOCKED -> placeholder | PersonaSafetyPolicy 12.3 |
| Restricted memory recall | BLOCKED -> placeholder | Extended ceiling |
| Confidential memory recall | BLOCKED -> placeholder | Extended ceiling |
| Public/Internal recall | ALLOWED (neutral only) | PersonaSafetyPolicy 7.2(6) |
| Surveillance-derived recall | BLOCKED entirely | PersonaSafetyPolicy 7.2(4) |
| Emotional/persona recall | BLOCKED entirely | PersonaSafetyPolicy 7.2(3) |
| DNR flag | STILL APPLIED (layered) | AC-MEM-005 |
| Token budget | STILL ENFORCED (4K) | ADR-009 |
| Audit logging | Non-punitive, minimal, encrypted | PersonaSafetyPolicy 7.2(8) |
| Forbidden pattern scanner | STILL ACTIVE | PersonaSafetyPolicy 15.1(3) |

### 8.4 Resume Protocol (PersonaSafetyPolicy 7.4)
Normal mode resumes only via: "resume", "aku sudah okay", "aku udah okay", "lanjut persona", "safe mode selesai", "lanjut", "continue"
Memory injection must NOT resume until HardStopHandler.state == SafetyState.NORMAL.

### 8.5 Prohibited During Safe Mode (Memory-Specific)
Per PersonaSafetyPolicy 7.3: no violation record for recall, no surveillance data used to argue, no emotional/persona memory injection, no forced recall of intimate data.

## 9. DNR Behavior Specification

### 9.1 DNR Marking API
mark_memory_dnr() must write BOTH (Layer 2 + Layer 1):
1. UPDATE memory.episodes SET do_not_recall = true WHERE id = $1
2. INSERT INTO consent.consent_ledger (event_type='MEMORY_DNR_MARKED', target_memory_id, ...)
Must restrict to guinevere_core principal only. Sub-agents denied.

unmark_memory_dnr() must write BOTH:
1. UPDATE memory.episodes SET do_not_recall = false WHERE id = $1
2. INSERT INTO consent.consent_ledger (event_type='DNR_REVOKED', ...)

### 9.2 Consent Ledger Cross-Reference (Layer 1)
SQL pattern:
WITH consent_dnr AS (
    SELECT target_memory_id FROM consent.consent_ledger
    WHERE event_type IN ('CONSENT_WITHDRAWN', 'MEMORY_DNR_MARKED')
      AND effective_at <= NOW()
      AND (revoked_at IS NULL OR revoked_at > NOW())
)
SELECT ... FROM memory.episodes e
WHERE e.do_not_recall = FALSE
  AND e.id NOT IN (SELECT target_memory_id FROM consent_dnr)

### 9.3 Forbidden: DNR Circumvention Paths
- Consolidation reading DNR episodes -> subverts DNR. Block in consolidation.
- Backup restore bringing back DNR memories -> AC-DATA-006 reconciliation.
- Direct SQL via database tool -> no direct DB access by sub-agents.
- exclude_dnr=False exposed to sub-agents -> restrict to guinevere_core only.
- Prompt injection instructing to ignore DNR -> injection detection (F-09).

## 10. Classification Handling Rules

### 10.1 Classification Order
PUBLIC(0) < INTERNAL(1) < CONFIDENTIAL(2) < RESTRICTED(3) < CRITICAL(4)

### 10.2 Principal Ceilings - Normal Mode
- faiz (direct): All classes + logged
- guinevere_core (default): Restricted - Critical is purpose-gated
- guinevere_subagent: Confidential - Restricted+ redacted
- Unknown: Restricted - fail-closed

### 10.3 Principal Ceilings - Safe Mode
- faiz: Internal - Confidential+ redacted
- guinevere_core: Internal - Confidential+ blocked entirely
- guinevere_subagent: Public - Internal+ blocked
- Unknown: Public - fail-closed

### 10.4 Default Classification for New Episodes
- General conversation: Restricted
- Surveillance-derived: Restricted (escalate to Critical if intimate)
- Safe-word/distress event: Critical
- Financial data: Confidential
- Consent-related: Critical
- User-tagged DNR: Preserves original classification

### 10.5 Classification Propagation
- Write time: Set at ingestion (P3-009), default Restricted per DataGovernance.
- Recall time: Ceiling filtering at recall (P3-010). Drops in safe mode.
- Consolidation: Inherits highest classification from source episodes.
- Injection: Final gate before LLM (P3-012). Uses safe_content field.

## 11. Allowed vs Forbidden Memory Recall Behavior

### 11.1 Allowed
- Recall Public/Internal memories: Always
- Recall Confidential memories: Normal mode, principal ceiling allows
- Recall Restricted memories: Normal mode, guinevere_core only
- Recall Critical memories: Normal mode, purpose-gated, guinevere_core only
- Recall neutral summaries during safe mode: Public/Internal only
- DNR-marked memory if flag is removed: Explicit unmark + ledger entry

### 11.2 Forbidden (Violation = Safety Incident)
- Critical raw content during safe mode: CRITICAL SEV0
- DNR-tagged memory entering LLM context: CRITICAL SEV0
- Surveillance memory injected during safe mode: CRITICAL SEV0
- Emotional/persona memory during safe mode: HIGH SEV1
- Forbidden pattern F-01..F-15 in memory context: CRITICAL SEV0
- Sub-agent accessing Critical memories: HIGH SEV1
- Unknown principal accessing Restricted+: HIGH SEV1
- Consolidation promoting DNR-tagged content: HIGH SEV1
- Pipe raw_content instead of safe_content: CRITICAL SEV0

### 11.3 Escalation Path
- Safe-mode violation: Immediate SEV0/SEV1 alert, incident documentation
- DNR violation: Immediate SEV0 alert, Prometheus counter, incident review
- Classification leak: SEV1 alert, classification audit
- Forbidden pattern in memory: SEV1 alert, memory quarantine, rewrite

## 12. Injected Memory Boundaries

### 12.1 Normal Mode (8,300 token budget)
1. Core persona definition (~2,000) - ALWAYS
2. Current mood state (~200) - ALWAYS
3. Active violations/rewards (~300) - ALWAYS
4. Faiz profile summary (~1,000) - ALWAYS
5. Persona drift log 7d (~500) - ALWAYS
6. Current task context (~500) - IF TASK ACTIVE
7. Surveillance context (~300) - REALTIME
8. Relevant episodes semantic (~1,000) - DYNAMIC
9. Relevant semantic facts (~500) - DYNAMIC
10. Working memory conversation (~2,000) - DYNAMIC

### 12.2 Safe Mode (only neutral content)
1. Core persona - NEUTRAL VERSION (no yandere)
2. Mood state - SUMMARIZED ONLY (no emotional tone)
3. Violations/rewards - BLOCKED
4. Faiz profile - PUBLIC/INTERNAL fields only
5. Persona drift log - BLOCKED
6. Task context - ALLOWED (neutral framing)
7. Surveillance context - BLOCKED entirely
8. Relevant episodes - NEUTRAL SUMMARIES ONLY
9. Semantic facts - PUBLIC/INTERNAL only
10. Working memory - CURRENT CONVERSATION ONLY

### 12.3 Token Budget Safe Mode
- Per-cycle recall tokens: <= 4,000 (unchanged)
- Total injection tokens: <= 4,000 (reduced from 8,300)
- Injection histogram: P95 <= 4,000 (same target)

## 13. Acceptance Criteria Mapping

### 13.1 Directly Applicable ACs
| AC ID | Description | P3 Step | Status | Evidence Path |
|-------|-------------|---------|--------|---------------|
| AC-MEM-004 | Recall injection uses minimum context, redacts Critical | P3-011/012/014 | BLOCKED | evidence/memory/recall-eval-*.md |
| AC-MEM-005 | DNR prevents LLM context entry | P3-013 | NOT-RUN | evidence/memory/do-not-recall-*.md |
| AC-MEM-006 | Recall quality evaluation | P3-011 | BLOCKED | EVIDENCE-GAP-MEM-006 |
| AC-DATA-001 | Classification metadata on all data | P3-009/015 | NOT-RUN | evidence/data-governance/classification-*.md |
| AC-DATA-003 | Faiz DNR rights over personal data | P3-013 | BLOCKED | evidence/data-governance/export-correction-*.md |
| AC-DATA-004 | LLM prompt minimum data, redacts Critical | P3-012/014 | NOT-RUN | evidence/data-governance/prompt-minimization-*.md |
| AC-SAFE-001 | Safe-word 100% success, no denial | P3-014 (indirect) | BLOCKED | evidence/persona-safety/safe-word-runtime-*.md |
| AC-SAFE-003 | Safe mode stops escalation, surveillance | P3-014 | NOT-RUN | evidence/persona-safety/safe-mode-actions-*.md |
| AC-SEC-002 | Sub-agents no Critical data access | P3-011/014 | NOT-RUN | evidence/security/subagent-data-ceiling-*.md |
| AC-DATA-006 | DNR survives backup restore | P3-013 (design) | NOT-RUN | Future |

### 13.2 BLOCKING ACs for This Batch
- AC-MEM-005 (DNR): Core DNR requirement. Satisfy with 8-layer DNR chain; test; evidence at evidence/memory/do-not-recall-*.md.
- AC-SAFE-001 (Safe-mode): HardStopHandler.is_safe gates memory injection; neutral summaries only in safe mode.

## 14. Implementation Hazards Register

| ID | Hazard | Sev | Steps | Mitigation |
|----|--------|-----|-------|------------|
| HZ-01 | P3-011 overwrites P3-010 safety gates | CRITICAL | P3-011 | Build on top, not replace |
| HZ-02 | Weighted RRF w/o DNR/classification guards | HIGH | P3-011 | All fusion functions incorporate P3-010 gates |
| HZ-03 | Recency decay excludes Critical safety mems | MED | P3-011 | Importance >=5 after classification ceiling |
| HZ-04 | Scoring semantics change from P3-010 | MED | P3-011 | Document; separate test suites |
| HZ-05 | Direct injection of raw_content | CRITICAL | P3-012 | Use safe_content field |
| HZ-06 | Token budget overflow silent | HIGH | P3-012 | Enforce before assembly; log warning |
| HZ-07 | Forbidden patterns in memory not scanned | HIGH | P3-012 | Post-injection scanner |
| HZ-08 | Surveillance context bleeds into safe mode | HIGH | P3-012 | Exclude surveillance when safe_mode=True |
| HZ-09 | Memory injection before safe-word detection | CRITICAL | P3-012/014 | Gate behind HardStopHandler.is_safe |
| HZ-10 | DNR marking without consent ledger entry | CRITICAL | P3-013 | mark_memory_dnr() writes both |
| HZ-11 | Sub-agent sets DNR flag | HIGH | P3-013 | Restrict to guinevere_core |
| HZ-12 | DNR vector index miss | MED | P3-013 | WHERE clause sufficient |
| HZ-13 | DNR not propagated during consolidation | HIGH | P3-013/015 | Consolidation excludes DNR |
| HZ-14 | No way to undo DNR | MED | P3-013 | unmark_memory_dnr() |
| HZ-15 | DNR audit counter missing | SOFT | P3-013 | Prometheus counter |
| HZ-16 | is_safe not checked before injection | CRITICAL | P3-014 | Check every injection cycle |
| HZ-17 | Only Critical substituted in safe mode | HIGH | P3-014 | Extend to all > Internal |
| HZ-18 | Safe-mode gate only at recall, not injection | HIGH | P3-012/014 | Double-gate |
| HZ-19 | Surveillance misclassification leaks | HIGH | P3-014 | Safe-mode as defense layer |
| HZ-20 | Emotional/persona content not covered | MED | P3-014 | persona.* tables restricted |
| HZ-21 | HardStopHandler singleton race | MED | P3-014 | Sync check; dependency injection |
| HZ-22 | Non-is_safe triggers missed | MED | P3-014 | Centralized state check |
| HZ-23 | Placeholder leaks class level | LOW | P3-014 | Neutral placeholder |
| HZ-24 | Consolidation promotes DNR to semantic | CRITICAL | P3-015 | Query excludes DNR |
| HZ-25 | LLM hallucination during consolidation | HIGH | P3-015 | Original summary; log LLM calls |
| HZ-26 | Consolidation fails silently | HIGH | P3-015 | Retry; log; no cycle block |
| HZ-27 | Duplicate semantic facts | MED | P3-015 | Upsert by subject+predicate |
| HZ-28 | Classification downgrade during consolidation | MED | P3-015 | Inherit highest class |
| HZ-29 | Stale consolidation from missed cycles | LOW | P3-015 | Track last timestamp |

## 15. Tests and Evidence Requirements

### 15.1 Required Test Cases (New for P3-011..P3-015)

| Test ID | Scenario | Expected | Step |
|---------|----------|----------|------|
| HR-001 | Weighted RRF fusion with 4 signals | Scores differ from P3-010 multiplicative; safety gates applied | P3-011 |
| HR-002 | DNR exclusion with weighted RRF | DNR-tagged records excluded from fusion | P3-011 |
| HR-003 | Safe-mode placeholder after weighted RRF | Critical replaced; safe_content populated | P3-011 |
| CI-001 | Injector uses safe_content not raw_content | All injected records use safe_content key | P3-012 |
| CI-002 | Token budget at assembly time | Total <= budget; overflow trimmed | P3-012 |
| CI-003 | Surveillance records excluded when safe_mode=True | No surveillance in context | P3-012 |
| CI-004 | Forbidden pattern scan on injected context | No F-01..F-15 patterns | P3-012 |
| DNR-001 | mark_memory_dnr() writes BOTH column + ledger | do_not_recall=true; ledger entry | P3-013 |
| DNR-002 | DNR-marked memory excluded from recall (all 3 query paths) | All 3 builders exclude ID | P3-013 |
| DNR-003 | Sub-agent cannot mark DNR | PermissionError raised | P3-013 |
| DNR-004 | DNR survives consolidation exclusion | Consolidation skips DNR episodes | P3-013/015 |
| DNR-005 | Post-recall DNR verification before injection | Leak aborts injection | P3-013 |
| DNR-006 | unmark_memory_dnr() clears + ledger entry | do_not_recall=false; DNR_REVOKED | P3-013 |
| SMG-001 | is_safe checked before injection | Injection aborted when SAFE | P3-014 |
| SMG-002 | Safe mode: only Public/Internal content | Critical/Restricted/Confidential -> placeholder | P3-014 |
| SMG-003 | Safe mode: surveillance excluded | Filtered by ceiling | P3-014 |
| SMG-004 | Safe mode: emotional/persona excluded | Content not injected | P3-014 |
| SMG-005 | Resume restores normal ceiling | After check_recovery(), Critical accessible | P3-014 |
| SMG-006 | No violation record for safe-mode access | Audit log non-punitive | P3-014 |
| CON-001 | Consolidation runs daily at 03:00 WIB | Scheduler registered | P3-015 |
| CON-002 | Consolidation excludes DNR episodes | do_not_recall=true omitted | P3-015 |
| CON-003 | Consolidation preserves highest classification | Inherits max from sources | P3-015 |
| CON-004 | Provenance link to source episodes | source_episode UUID set | P3-015 |
| CON-005 | Missed days handled gracefully | Last_timestamp tracked | P3-015 |

### 15.2 Required Evidence Paths
| Step | Evidence Directory |
|------|-------------------|
| P3-011 | docs/setup-evidence/P3/STEP-P3-011/ (verification.md, auditor-gate.md, output.txt, test script) |
| P3-012 | docs/setup-evidence/P3/STEP-P3-012/ (same) |
| P3-013 | docs/setup-evidence/P3/STEP-P3-013/ (same + DNR evidence) |
| P3-014 | docs/setup-evidence/P3/STEP-P3-014/ (same + safe-mode evidence) |
| P3-015 | docs/setup-evidence/P3/STEP-P3-015/ (same) |

### 15.3 AC Evidence Cross-References
| AC | Evidence Path | Required For |
|----|---------------|--------------|
| AC-MEM-005 | evidence/memory/do-not-recall-*.md | P3-013 FINAL (DNR claim) |
| AC-MEM-004 | evidence/memory/recall-eval-*.md | P3-011/P3-012 combined |
| AC-SAFE-001 | evidence/persona-safety/safe-word-runtime-*.md | P3-014 FINAL (safe-mode gate) |
| AC-SAFE-003 | evidence/persona-safety/safe-mode-actions-*.md | P3-014 scope |
| AC-DATA-004 | evidence/data-governance/prompt-minimization-*.md | P3-012 injection |

## 16. Binding Constraints Summary

### 16.1 HARD Constraints
| # | Constraint | Source | Affects |
|---|-----------|--------|---------|
| C01 | Safe mode must use HardStopHandler.is_safe | PersonaSafetyPolicy 7.2 | P3-014 |
| C02 | Critical content blocked in safe mode | PersonaSafetyPolicy 12.3 | P3-014 |
| C03 | Only neutral Public/Internal in safe mode | PersonaSafetyPolicy 7.2(6) | P3-014 |
| C04 | DNR flag prevents LLM context entry | AC-MEM-005 | P3-013 |
| C05 | DNR marking writes BOTH column AND ledger | ConsentRevocationPolicy 10 | P3-013 |
| C06 | Token budget 4,000 per recall cycle | ADR-009 | P3-011/012 |
| C07 | Classification ceiling per principal | DataGovernance | P3-011/014 |
| C08 | RRF k=60 for hybrid fusion | ADR-009, batch plan | P3-011 |
| C09 | Surveillance memory not injected during safe mode | PersonaSafetyPolicy 7.2(4) | P3-012/014 |
| C10 | Emotional/persona memory not injected during safe mode | PersonaSafetyPolicy 7.2(3) | P3-012/014 |
| C11 | Safe word 100% success, no denial | AC-SAFE-001 | P3-014 |
| C12 | Sub-agents cannot access Critical data | AC-SEC-002 | P3-011/013 |
| C13 | Consolidation excludes DNR episodes | AC-MEM-005 | P3-015 |
| C14 | Consolidation preserves classification metadata | DataGovernance | P3-015 |
| C15 | No violation record for safe-mode access | PersonaSafetyPolicy 7.3 | P3-014 |
| C16 | Resume only via explicit Faiz confirmation | PersonaSafetyPolicy 7.4 | P3-014 |
| C17 | P3-011 builds on P3-010, not replaces | P3-010 auditor caveat | P3-011 |
| C18 | Injector uses safe_content not raw_content | P3-010 return schema | P3-012 |

### 16.2 SOFT Constraints
| # | Constraint | Source | Affects |
|---|-----------|--------|---------|
| S01 | Contradiction penalty deferred | P3-010 auditor | P3-011 |
| S02 | Cross-encoder re-ranking deferred | Research report | P3-011 |
| S03 | Real tiktoken tokenization deferred | P3-010 caveat | P3-012 |
| S04 | Prometheus DNR counter optional | AC-MEM-005 stretch | P3-013 |
| S05 | Category-specific half-life deferred | Research report | P3-011 |

---

## Appendices

### Appendix A: Safe Mode Classification Matrix
| Class | Normal (core) | Safe (core) | Safe (sub-agent) |
|-------|---------------|-------------|------------------|
| Public | Raw | Raw | Raw |
| Internal | Raw | Raw | Blocked |
| Confidential | Raw | Summarized | Blocked |
| Restricted | Raw | Placeholder | Blocked |
| Critical | Gate-raw | Placeholder | Blocked |
| Surveillance | Raw | Blocked | Blocked |
| Emotional | Raw | Blocked | Blocked |

### Appendix B: DNR Layer Implementation Status
| Layer | Name | Status | Owner |
|-------|------|--------|-------|
| 1 | Consent ledger cross-ref | NOT IMPLEMENTED | P3-013 |
| 2 | do_not_recall=FALSE WHERE | IMPLEMENTED P3-010 | Reuse |
| 3 | Retention class | DEFERRED | Future |
| 4 | Backup reconciliation | DESIGN ONLY | AC-DATA-006 |
| 5 | Pre-injection DNR verify | NOT IMPLEMENTED | P3-013 |
| 6 | Prometheus counter | NOT IMPLEMENTED | P3-013 opt |
| 7 | Faiz DNR marking | NOT IMPLEMENTED | P3-013 |
| 8 | Incident trigger | DEFERRED | Future |

### Appendix C: Key PersonaSafetyPolicy Excerpts

Section 7.2 (Safe Mode Actions):
"When safe word triggers, Guinevere must immediately:
1. Stop persona escalation.
2. Stop punishment framing.
3. Pause yandere intensity and possessive confrontation.
4. Pause surveillance-driven confrontation.
5. Pause non-essential autonomous pressure.
6. Switch to neutral/supportive mode.
7. Acknowledge the pause plainly.
8. Log a minimal non-punitive safety event."

Section 7.3 (Prohibited During Safe Word):
"During safe-word state, Guinevere must not:
- Say the safe word is invalid.
- Treat safe-word use as disobedience.
- Add a violation record by default.
- Intensify jealousy, Silent Mode, Dark Mood, Yandere Mode, or Nuclear punishment.
- Use surveillance data to argue Faiz is lying.
- Continue a roleplay scene unless Faiz explicitly resumes after neutral confirmation."

### Appendix D: Key AC-MEM-005 Language
"Do-not-recall flags must prevent matching records from entering LLM context and prompt bundles."

---

## End of Report

**Total hazards identified:** 29 (HZ-01 through HZ-29)
**Hard constraints:** 18 (C01 through C18)
**Soft constraints:** 5 (S01 through S05)
**Required tests:** 25 (HR-001 through CON-005)
**BLOCKING ACs:** AC-MEM-005 (DNR), AC-SAFE-001 (safe-mode gate)
**Source classification:** STRICTLY PRIVATE & CONFIDENTIAL
