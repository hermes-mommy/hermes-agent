# Phase 3 Memory Safety Compliance Report

**Generated**: 2026-06-04  
**Scope**: Phase 3 Memory Bridge Migration Safety Boundary Review  
**Target**: docs/60-persona/60-PersonaSafetyPolicy_v1.0.md (F-01..F-15), DNR, Classification Ceilings, Consent Mandates  

---

## Executive Summary

The Guinevere memory system implements a **defense-in-depth safety architecture** with 10 distinct enforcement layers. Phase 3 Memory Bridge migration introduces a facade (HermesMemoryBridge) that correctly delegates all safety decisions to the underlying ead_pipeline and write_pipeline. No safety boundaries are bypassed; however, Phase 3 planners must ensure that any new memory ingestion paths explicitly pass principal="guinevere_core", classification=RESTRICTED, and exclude_dnr=True.

---

## 1. DNR (Do Not Recall) Enforcement

**Status**: ✅ Enforced at Query, API, and Hook levels.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/memory/dnr.py | 61-418 | Defines DNRAuthorizationError, DNRStateError, DNRViolationError. Only principal == "guinevere_core" can mark/unmark. | **Low**: API is strictly gated. |
| src/memory/dnr.py | 385-418 | erify_recall_results_dnr_free(): Fail-closed guard that raises DNRViolationError if any candidate has do_not_recall=True. | **Low**: Called post-query as a secondary safety net. |
| src/memory/read_pipeline.py | 403 | DNR exclusion handled at SQL query level (WHERE do_not_recall IS false). | **Medium**: Phase 3 custom queries must include exclude_dnr=True. |
| hermes-config/hooks/dnr_filter.py | 120-173 | Post-tool call hook checking static/dynamic DNR patterns. Blocks tool results containing DNR keywords. | **Low**: Hermes-level enforcement. |
| hermes-config/plugins/guinevere_safety/state_manager.py | 486-519 | Redis DB5 key guinevere:dnr_list manages dynamic DNR topics. | **Low**: Read-only for safety checks. |

---

## 2. Classification Enforcement (Ceiling & Fail-Closed)

**Status**: ✅ Enforced at Write, Read, and Embedding layers.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/memory/write_pipeline.py | 275-304 | _guard_critical(): Fails closed if classification == CRITICAL and sanitized_summary is empty/whitespace. | **Medium**: Phase 3 writes to Critical must provide sanitized_summary. |
| src/memory/read_pipeline.py | 332-445 | classification_level(): Unknown/null classification maps to level 5 (fail-closed). _resolve_ceiling() enforces principal limits (guinevere_core → CRITICAL, default → RESTRICTED). | **Low**: Robust fail-closed logic. |
| src/memory/read_pipeline.py | 67-90 | Safe-mode substitution: SAFE_MODE_RESTRICTED_PLACEHOLDER or SAFE_MODE_CRITICAL_PLACEHOLDER replaces raw content. | **Low**: Prevents raw content leakage in safe mode. |
| src/memory/embeddings.py | 103-282 | _validate_classification(): Rejects unknown classifications. CRITICAL requires sanitized_summary. RESTRICTED/CONFIDENTIAL auto-redacts via _redact_sensitive(). | **Medium**: Phase 3 embedding calls must pass valid classification. |
| src/surveillance/classification.py | 37-200 | DataClassification enum (INTERNAL, CONFIDENTIAL, RESTRICTED, CRITICAL) with strict mapping to retention and encryption profiles. | **Low**: Surveillance layer is isolated. |

---

## 3. Anti-Hallucination Patterns

**Status**: ✅ Enforced via prompt injection on empty recall.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/discord/conversational_handler.py | 459-461, 473, 486 | Injects ANTI_HALLUCINATION_GUARD into system_prompt when memories list is empty or recall fails. | **Low**: Standardized guard in place. |
| src/discord/hermes_conversational.py | 80, 518 | Identical EMPTY_RECALL_ANTI_HALLUCINATION_PROMPT injection for Hermes conversational paths. | **Low**: Consistent across entry points. |
| 	ests/memory/test_prompt_context_injection.py | 309 | Unit test verifying empty recall returns prompt without memories, preventing fabrication. | **N/A**: Test coverage exists. |

---

## 4. Consent-Related Code

**Status**: ✅ Fail-closed gate at ingestion; explicit revocation supported.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/surveillance/consent_gate.py | 179-285 | check_consent(scope): Queries consent.consent_ledger with Redis DB2 cache. Returns llowed=False for PAUSED, WITHDRAWN, or missing entries. | **Low**: Surveillance-specific, not memory recall. |
| src/surveillance/consumer.py | 175-193 | Drops events immediately if check_consent returns llowed=False or raises an exception (fail-closed). | **Low**: Ingestion layer only. |
| src/discord/cmd_consent.py | 67-165 | /consent command allows operator to view, grant, or revoke consent boundaries in Redis consent:grants. | **Low**: Operator-controlled. |
| src/memory/models.py | 889-938 | Schema: consent.consent_ledger and consent.revocation_log tables with strict foreign keys. | **Low**: Database schema is stable. |

---

## 5. HARD STOP / Distress Protocol (D0-D4)

**Status**: ✅ Multi-layered detection and neutralization.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/core/services/hard_stop_handler.py | 40-139 | HardStopHandler: Detects "hard stop", "safeword", "hentikan", "stop the persona". Sets SafetyState.SAFE. | **Low**: Core safety service. |
| src/persona/safe_mode.py | 89-92, 463-469 | DistressDetector: D0 (Normal) to D4 (Emergency). D2+ activates safe_mode, forcing persona neutralization. | **Low**: Integrated into conversational handler (Step 7). |
| src/persona/punishment_engine.py | 555-609 | check_distress_suspension(): Auto-suspends active punishment at D3+ distress. Auto-resumes only when distress drops below D3 AND safe_mode is inactive. | **Low**: Prevents punishment during crisis. |
| hermes-config/hooks/hard_stop.py | 120-167 | Pre-LLM hook checking for safe word. Blocks LLM call entirely if triggered. | **Low**: Hermes-level enforcement. |

---

## 6. Yandere Level Enforcement (Y0-Y6)

**Status**: ✅ Y4 Baseline, Y5 Ceiling, Y6 PROHIBITED.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/persona/yandere_fsm.py | 59-159 | YandereLevel enum (Y0-Y5). alidate_level() raises YandereSafetyError if value > 5 (Y6 prohibition). | **Low**: Hardcoded ceiling. |
| src/persona/yandere_fsm.py | 130-141 | get_effective_level(): Forces Y0_NEUTRAL if safe_mode, distress, or crisis is True. | **Low**: Critical safety override. |
| hermes-config/plugins/guinevere_safety/state_manager.py | 364-398 | get_yandere_level() always returns 4. set_yandere_level() **ALWAYS REJECTS** mutations. Y4 is IMMUTABLE baseline. | **Low**: Prevents runtime drift. |
| hermes-config/hooks/safety_scan.py | 184-257 | Y6_PATTERNS: Regex checks for Y6-adjacent content (e.g., "cannot leave", "no future", "blackmail"). Blocks response. | **Low**: Post-generation safety net. |

---

## 7. Data Sanitization (PII / Secrets)

**Status**: ✅ Deterministic redaction before external transmission or logging.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/surveillance/secret_scanner.py | 226-318 | scan_text() / edact_secrets(): Detects AWS, GitHub, OpenAI, JWT, PEM, DB connections, Discord tokens, age keys, high-entropy strings. Replaces with [REDACTED]. | **Low**: Applied to clipboard events. |
| src/memory/embeddings.py | 156-188 | _redact_sensitive(): Strips emails, phone numbers, API keys, and credential URLs before sending text to external embedding services. | **Medium**: Phase 3 must ensure all external API calls use this. |
| src/observability/sentry_integration.py | 53-179 | _redact_value() / _redact_dict(): Scrubs PII, secrets, and safe-word mentions from Sentry events and breadcrumbs before transmission. | **Low**: Observability safety. |

---

## 8. Mood / Persona Drift in Memory Context

**Status**: ✅ Tracked, detected, and corrected.

| File | Line(s) | Enforcement Point | Phase 3 Risk |
|---|---|---|---|
| src/persona/drift_detector.py | 51+ | DriftDetector: Compares prompt hashes to detect unauthorized persona drift. | **Low**: Drift monitoring. |
| src/persona/drift_corrector.py | 69+ | DriftCorrector: Evaluates drift and performs auto-rollback when threshold is exceeded. | **Low**: Self-healing mechanism. |
| src/core/services/prompt_loader.py | 43-109 | get_system_prompt_with_context(): Injects ## Current Mood: {mood} into the assembled system prompt to maintain persona consistency across memory recalls. | **Low**: Standardized context injection. |
| src/memory/read_pipeline.py | 81-84 | FTS indexing includes tags: "emotional", "mood", "dark_mood", "persona_escalation". | **Low**: Enables mood-aware recall filtering. |

---

## 9. conversational_handler.py Safety Enforcement Points

### Step 9: Recall (Lines 433-494)
- **Enforcement**: Calls ridge.recall_for_context() with principal="guinevere_core", safe_mode=safe_mode_activated, and 	oken_budget=800.
- **Anti-Hallucination**: Explicitly checks if not memories: and appends ANTI_HALLUCINATION_GUARD to system_prompt (Lines 460-461, 473, 486).
- **Fallback**: Catches all exceptions, falls back to base prompt + guard, preventing crash-induced safety bypass.

### Step 12b: Store (Lines 585-613)
- **Enforcement**: Calls ridge.store_conversation() asynchronously (syncio.create_task).
- **Delegation**: Passes user_message, ssistant_response, user_id_hash, and safe_mode=safe_mode_activated.
- **Risk**: Fire-and-forget pattern means store failures are logged but do not block the conversational response. This is acceptable for memory persistence but requires monitoring.

---

## 10. memory_bridge.py Safety Delegation Analysis

**Status**: ✅ Correctly delegates; no safety logic duplicated or bypassed.

| File | Line(s) | Finding | Phase 3 Risk |
|---|---|---|---|
| src/hermes/memory_bridge.py | 7-8, 49-50 | Docstring explicitly states: *"All safety decisions — DNR exclusion, classification ceiling, safe-mode, token budget — are delegated to the underlying pipelines."* | **Low**: Clear architectural intent. |
| src/hermes/memory_bridge.py | 94-150 | ecall_for_context(): Hardcodes principal="guinevere_core" and passes safe_mode directly to ecall_memories(). | **Low**: Ensures highest classification ceiling and DNR exclusion. |
| src/hermes/memory_bridge.py | 195-224 | store_conversation(): Imports RESTRICTED from write_pipeline and hardcodes classification=RESTRICTED for all conversational storage. | **Medium**: Phase 3 planners must ensure no new paths default to PUBLIC or INTERNAL for user conversations. |

---

## Phase 3 Risk Assessment & Recommendations

### 🔴 High Risk Areas (Require Planner Attention)
1. **Custom Memory Ingestion**: Any new Phase 3 memory ingestion path (e.g., from new surveillance tools or external APIs) **must** explicitly call store_episode with classification=RESTRICTED (or higher) and principal="guinevere_core". Defaulting to PUBLIC is a safety violation.
2. **Embedding Pipeline**: If Phase 3 introduces new embedding calls, they **must** pass through _redact_sensitive() or prepare_embedding_text() to prevent PII/secret leakage to external LLM providers.
3. **Critical Classification**: If Phase 3 introduces classification=CRITICAL writes, the planner must ensure a valid, non-empty sanitized_summary is provided, or the write will fail-closed.

### 🟡 Medium Risk Areas (Monitor During Implementation)
1. **Fire-and-Forget Store**: Step 12b in conversational_handler.py uses syncio.create_task for store_conversation. While safe for UX, ensure Phase 3 does not rely on synchronous memory availability immediately after a conversational turn.
2. **Unknown Classification Fail-Closed**: Ensure Phase 3 data pipelines do not pass None or empty strings for classification, as classification_level() maps these to level 5 (fail-closed), which may silently drop valid memories.

### 🟢 Low Risk Areas (Verified Safe)
- DNR exclusion is enforced at the SQL query level and validated post-query.
- Yandere Y6 is mathematically impossible (enum max is 5, alidate_level raises on >5, set_yandere_level always rejects).
- HARD STOP / Distress D2+ correctly forces Y0_NEUTRAL and suspends punishment.
- Consent gate is fail-closed for surveillance ingestion.

---

## Auditor Gate Checklist for Phase 3 Planner

Before approving any Phase 3 memory-related implementation step, the planner scaffold must verify:
- [ ] exclude_dnr=True is present in all ecall_memories or ecall_for_context calls.
- [ ] principal="guinevere_core" is explicitly passed for classification ceiling resolution.
- [ ] classification is never None, "", or "Unknown" in write operations.
- [ ] classification=CRITICAL writes include a non-empty sanitized_summary.
- [ ] No new code uses # type: ignore, s any, or empty except: blocks around memory/safety operations.
- [ ] ANTI_HALLUCINATION_GUARD is injected when memory context is empty.

---
*Report generated by Guinevere Safety Audit Sub-Agent. Compliant with AGENTS.md §2.9 (File-Based Output Discipline) and §2.11 (Evidence Minimum Schema).*
