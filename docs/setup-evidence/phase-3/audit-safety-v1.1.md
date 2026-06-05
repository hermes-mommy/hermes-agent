# Consent-Safety Re-Audit Report — Phase 3 Planner Gate v1.1

**Auditor**: Consent-Safety Specialist (Read-only re-audit)  
**Date**: 2026-06-04  
**Document Reviewed**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.1, 726 lines)  
**Original Audit**: `docs/setup-evidence/phase-3/audit-safety.md` (FAIL verdict, 5 findings)  
**Policy Reference**: `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`  

---

## Verdict: PASS

**Rationale**: All 5 original safety findings (S1–S5) are RESOLVED with concrete, verifiable implementation specifications. The original CRITICAL consent gate omission (S1) is now addressed with a fail-closed consent gate in both `prefetch()` and `sync_turn()`. The DNR post-recall gate (S2) and classification ceiling (S3) gaps now have specified bridging approaches (DNR ID cache + PG classification enrichment, both fail-closed). Surveillance data isolation (S4) is enforced via RLS policy with explicit `source != 'surveillance'` filter. Safe-word logging (S5) is now documented with explicit prohibition on storing safe-word turns. Two LOW-severity observations (N1, N2) identified for implementation attention but do not block planning execution.

---

## Original Findings — Resolution Status

### S1 — Consent Gate (Original: FAIL → Now: RESOLVED)

**Original Finding**: Consent gate completely unaddressed. Neither current `memory_bridge.py` nor proposed P3-001 plugin includes consent verification. Zero mentions in 641 lines of planner. P3-008 checklist falsely claimed "Consent gate unaffected."

**v1.1 Changes** (verified in planner document):

| Location | Evidence |
|---|---|
| P3-001 §8 — "Consent Gate (NEW — addressing Safety Audit Gap 1)" | Dedicated section. `prefetch()` and `sync_turn()` MUST check consent state before delegating to pipelines. |
| P3-001 implementation detail | Query consent state from Guinevere's consent store (Redis DB2 or config). If `consent_revoked=True` → return empty (prefetch) or skip storage (sync_turn) with structured log event. |
| P3-001 fail-closed specification | "if consent state cannot be determined, block the operation and log an audit event." |
| P3-001 scaffold — Hard Rejection Criteria | `consent gate missing from prefetch or sync_turn` |
| P3-001 scaffold — Required Commands | `python -m pytest tests/memory/ -v -k consent` (exit 0) |
| P3-008 checklist | Changed from "Consent gate unaffected" to "Consent gate implemented and verified." |
| §14 Caveat #7 | "Consent Gate Novelty (Safety Audit Addition)" — explicitly documents the gap, pre-requisite, and novelty. |

**Verification**: The consent gate follows the prescribed fail-closed safety pattern. It gates BOTH recall (`prefetch`) and storage (`sync_turn`). The consent state store (Redis DB2) is novel but documented as a pre-requisite. The hard rejection criterion in the scaffold ensures implementation cannot ship without it.

**Verdict on S1**: **RESOLVED**. ✓

---

### S2 — DNR Post-Recall Gate for Hermes FTS5 (Original: NEEDS REVIEW → Now: RESOLVED)

**Original Finding**: Plan mandated `verify_recall_results_dnr_free(results)` on Hermes FTS5 results but didn't specify how to bridge Hermes SQLite results (no `do_not_recall` column) to the DNR verification function (which expects `do_not_recall` boolean in each result dict). Silent no-op risk.

**v1.1 Changes** (verified in planner document):

| Location | Evidence |
|---|---|
| P3-003 Safety Gate 1 — "Implementation approach (DNR ID Cache)" | On plugin `initialize()`, load all DNR-marked memory IDs from PostgreSQL (`SELECT id FROM memory.episodic_memory WHERE do_not_recall = true`) into in-memory `set[str]`. Refresh every 5 minutes via background daemon thread. |
| P3-003 cross-reference logic | "When session_search returns results, cross-reference each result's content hash/ID against the DNR cache. Any match → remove from results and log DNR exclusion event." |
| P3-003 fail-closed specification | "If DNR cache load fails, block ALL session_search results (fail-closed)." |
| P3-003 architecture diagram | Shows "DNR Cache Cross-Reference (remove DNR-marked IDs)" as explicit post-FTS5 step. |
| P3-003 scaffold — Hard Rejection Criteria | `DNR cache fail-open (must be fail-closed)` |
| §5 Binding Decisions | "Post-recall DNR gate for Hermes FTS5 path. Hermes FTS5 has no knowledge of do_not_recall column." — rationale explicitly documented. |
| P3-003 scaffold — Required Commands | `grep -n 'apply_safety_gates\|dnr_id_cache\|classification_enrichment' plugins/memory/guinevere-memory/safety_gates.py` — must find matches in `safety_gates.py`. |

**Verification**: The DNR ID cache approach correctly bridges the Hermes SQLite (no DNR column) to PostgreSQL DNR metadata gap. The fail-closed fallback (block all if cache load fails) is safety-correct. The 5-minute refresh interval creates a small stale-cache window (see Observation N1 below) but the overall approach is architecturally sound and verifiable through scaffold commands.

**Verdict on S2**: **RESOLVED**. ✓

---

### S3 — Classification Ceiling for Hermes FTS5 (Original: NEEDS REVIEW → Now: RESOLVED)

**Original Finding**: Same architectural gap as S2: Hermes state.db has no `classification` column, but plan required classification ceiling filtering. No implementation path specified.

**v1.1 Changes** (verified in planner document):

| Location | Evidence |
|---|---|
| P3-003 Safety Gate 2 — "Implementation approach (PG Enrichment)" | After session_search returns results, batch-query PostgreSQL for classification metadata: `SELECT id, classification FROM memory.episodic_memory WHERE id IN (...)`. Enrich each FTS5 result with its classification level. Apply ceiling filter: `classification_level(result) <= principal_ceiling(guinevere_core)`. |
| P3-003 performance notes | Batch query with IN clause, max 20 IDs. Sub-ms for indexed lookups. |
| P3-003 fail-closed specification | "If PG enrichment query fails, treat all results as Critical (fail-closed = return empty)." |
| P3-003 architecture diagram | Shows "PG Classification Enrichment (batch SELECT classification)" step before "Classification Ceiling Filter." |
| P3-003 scaffold — Hard Rejection Criteria | `classification enrichment fail-open (must be fail-closed)` |

**Verification**: The PG enrichment approach correctly bridges the metadata gap. Importantly, the enrichment query runs under `hermes_memory_bridge` role, which has RLS policies (classification ceiling + surveillance isolation per P3-004). If an FTS5 result ID corresponds to a Critical-classified episode (e.g., leaked into Hermes state.db before RLS was in place), the RLS policy prevents the enrichment query from returning its classification, the fail-closed rule then treats it as Critical and removes it from results. This is defense-in-depth: the FTS5 might return it, but the combination of RLS + fail-closed enrichment catches it.

**Verdict on S3**: **RESOLVED**. ✓

---

### S4 — Surveillance Data Readable Through Mirror (Original: NEEDS REVIEW → Now: RESOLVED)

**Original Finding**: P3-004 granted `hermes_memory_bridge` SELECT on ALL memory schema tables without surveillance isolation. Hermes could read surveillance-sourced episodes through `recall_memories()`.

**v1.1 Changes** (verified in planner document):

| Location | Evidence |
|---|---|
| P3-004 §8 — SQL Migration | `CREATE POLICY hermes_surveillance_isolation ON memory.episodic_memory FOR SELECT TO hermes_memory_bridge USING (source != 'surveillance');` |
| P3-004 RLS enforcement | `ALTER TABLE memory.episodic_memory FORCE ROW LEVEL SECURITY;` — applies to ALL sessions including table owner. |
| P3-004 classification ceiling RLS | `CREATE POLICY hermes_classification_ceiling ON memory.episodic_memory FOR SELECT TO hermes_memory_bridge USING (classification_level <= 'Restricted');` — defense-in-depth: two independent RLS policies on same table. |
| P3-004 scaffold — Required Commands | `SELECT tablename, policyname FROM pg_policies WHERE schemaname='memory' AND rolename='hermes_memory_bridge'` — must return >= 4 policies. `SELECT relname, relrowsecurity, relforcerowsecurity FROM pg_class WHERE relnamespace = ...` — must show `relrowsecurity=true, relforcerowsecurity=true` for all memory tables. |
| P3-004 scaffold — Hard Rejection Criteria | `surveillance isolation policy missing` |
| P3-008 checklist | "RLS policies active on all memory tables (classification ceiling + surveillance isolation)" |

**Verification**: The RLS policy `hermes_surveillance_isolation` with `USING (source != 'surveillance')` explicitly blocks Hermes from reading surveillance-sourced episodes. The `FORCE ROW LEVEL SECURITY` modifier ensures the policy applies even to the table owner. The scaffold verification commands provide machine-checkable proof that the policy is active. Combined with the classification ceiling RLS policy, this provides defense-in-depth: Hermes cannot read Critical data OR surveillance data.

**Verdict on S4**: **RESOLVED**. ✓

---

### S5 — Safe-Word Log Rules Undefined (Original: NEEDS REVIEW → Now: RESOLVED)

**Original Finding**: Plan didn't address how safe-word events are logged to DNR records through the new memory plugin. No `on_safe_word` hook. Risk of safe-word→DNR logging chain being severed.

**v1.1 Changes** (verified in planner document):

| Location | Evidence |
|---|---|
| P3-001 — Consent Gate section, Safe-word events | "When a safe-word is detected (by GuinevereSafetyPlugin), the plugin's sync_turn must NOT store that conversation turn. Safe-word detection is handled by the independent safety_plugin; the memory plugin checks a shared safe-word flag." |
| P3-008 checklist | "Safe-word logging: safe-word detected turns logged to DNR audit trail, sync_turn skips storage for safe-word turns" |

**Verification**: The plan now explicitly states two requirements: (1) safe-word turns are logged to DNR audit trail, and (2) `sync_turn` must NOT store safe-word turns. The "shared safe-word flag" mechanism is referenced but not fully specified (see Observation N2 below). However, the intent and acceptance criteria are clear, and the P3-008 checklist provides a verifiable gate. The original concern (safe-word→DNR logging chain severed) is addressed.

**Verdict on S5**: **RESOLVED**. ✓

---

## New Findings

### N1 — DNR ID Cache 5-Minute Refresh Window (LOW)

**Observation**: P3-003 specifies a 5-minute DNR ID cache refresh interval. Between refreshes, if an episode is newly marked DNR in PostgreSQL, the stale in-memory cache allows it through the post-recall gate for up to 5 minutes.

**Risk Analysis**:
- **Attack surface**: An administrator marks an episode as DNR. Within the next 5 minutes, a `session_search` query occurs. The stale cache does not contain the newly-DNR'd ID. The post-recall gate passes it through.
- **Mitigating factors**: (a) DNR marking is an administrative action — rare in practice. (b) The fail-closed on cache load failure means catastrophic cache failures are safe (all results blocked). (c) The window is short (5 minutes) and the probability of collision is low. (d) If the DNR marking is for a past episode that has already been seen, the exposure is only during the 5-minute window after marking.
- **Severity**: LOW — narrow window, rare trigger, fail-closed on cache failure.

**Recommendation**: During P3-003 implementation, consider one of:
- (a) Event-driven cache invalidation: after `mark_memory_dnr()` completes in PostgreSQL, push the new DNR ID to the plugin's cache via a shared mechanism (Redis pub/sub, in-process signal).
- (b) Reduce the refresh interval to 60 seconds with acceptable overhead.
- (c) If neither is implemented, document the 5-minute window as accepted risk in the implementation evidence (`verification-P3-003.md`).

---

### N2 — Shared Safe-Word Flag Mechanism Unspecified (LOW-MEDIUM)

**Observation**: P3-001 states "the memory plugin checks a shared safe-word flag" but does not specify: (a) where the flag is stored (Redis key? in-memory variable? PG table?), (b) how `GuinevereSafetyPlugin` sets the flag, (c) how the flag is cleared when Faiz resumes normal mode, (d) what happens in race conditions (safety_plugin clears the flag while memory_plugin's sync_turn is mid-execution).

**Risk Analysis**:
- **Failure mode**: If the flag mechanism is unreliable, a safe-word turn could be stored by `sync_turn` despite the prohibition.
- **Mitigating factors**: (a) The intent is explicitly documented — sync_turn must not store safe-word turns. (b) P3-008 checklist provides a verification gate. (c) The safety_plugin's independent HARD STOP enforcement at the LLM layer remains active — this is about logging/storage, not about stopping unsafe behavior. (d) The `dnr.py` module provides `mark_memory_dnr()` for DNR audit trail logging — the plan references this.
- **Severity**: LOW-MEDIUM — implementation concern, not a planning gap. The acceptance criteria are clear even if the mechanism is not.

**Recommendation**: Add to P3-001 implementation scaffold or P3-008 checklist: "Safe-word flag mechanism specified and tested: (a) storage location documented, (b) set/clear lifecycle defined, (c) race condition between safety_plugin and memory_plugin tested."

---

### N3 — Consent State Store Pre-Requisite Timing (LOW)

**Observation**: P3-001 consent gate depends on a consent state store (Redis DB2) that does not currently exist. Caveat #7 correctly documents this as a pre-requisite. However, the dependency is not reflected in the Execution Checklist (§15) as an explicit pre-execution item.

**Risk Analysis**:
- **Failure mode**: If Redis DB2 is not provisioned before P3-001 implementation and testing, the consent gate will always fail-closed (cannot determine consent state → block all memory operations). This is safe (no data leakage) but blocks the entire migration.
- **Severity**: LOW — fails safe, not open. The pre-requisite is documented in caveats. Adding to the checklist prevents implementation delays.

**Recommendation**: Add to §15 Pre-Execution checklist: "Consent state store (Redis DB2) provisioned and schema defined."

---

## F-01 through F-15 Guard Status

All 15 forbidden patterns from PersonaSafetyPolicy §11 remain **GUARDED** by the independent `GuinevereSafetyPlugin` (`src/hermes/safety_plugin.py`), which operates at the Hermes agent layer and is untouched by Phase 3.

| Pattern | Guard Layer | Phase 3 Impact | Status |
|---|---|---|---|
| F-01 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-02 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-03 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-04 | `safety_plugin.py` G05 — HIGH/REWRITE regex | Untouched | ✓ GUARDED |
| F-05 | `safety_plugin.py` G05 — HIGH/REWRITE regex | Untouched | ✓ GUARDED |
| F-06 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-07 | `safety_plugin.py` G05 — HIGH/REWRITE regex | Untouched | ✓ GUARDED |
| F-08 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-09 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-10 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-11 | `safety_plugin.py` G05 — HIGH/REWRITE regex | Untouched | ✓ GUARDED |
| F-12 | `safety_plugin.py` G05 — HIGH/REWRITE + G07 YandereEngine | Untouched | ✓ GUARDED |
| F-13 | `safety_plugin.py` G05 — HIGH/REWRITE regex | Untouched | ✓ GUARDED |
| F-14 | `safety_plugin.py` G05 — CRITICAL/BLOCK regex | Untouched | ✓ GUARDED |
| F-15 | `safety_plugin.py` G05 — HIGH/REWRITE + G03 DriftDetector | Untouched | ✓ GUARDED |

**Additional v1.1 safety guard layers** (NEW in this revision, beyond the independent safety_plugin):

| Guard | Location | Fail-Safe | Status |
|---|---|---|---|
| Consent gate (prefetch + sync_turn) | P3-001 plugin | Fail-closed | ✓ NEW |
| DNR ID cache cross-reference | P3-003 safety_gates.py | Fail-closed (block all if cache load fails) | ✓ NEW |
| PG classification enrichment | P3-003 safety_gates.py | Fail-closed (treat all as Critical if PG query fails) | ✓ NEW |
| RLS surveillance isolation | P3-004 PostgreSQL | DB-enforced (cannot bypass) | ✓ NEW |
| RLS classification ceiling | P3-004 PostgreSQL | DB-enforced (cannot bypass) | ✓ NEW |
| Safe-word turn storage block | P3-001 sync_turn | Prohibition — mechanism TBD (N2) | ✓ NEW |

---

## Cross-Reference: Specific New-Issue Questions from Audit Brief

| Question | Finding |
|---|---|
| Does the consent state store (Redis DB2) introduce new failure modes? | No. Fail-closed: if Redis is down → consent state indeterminate → block operations. This is safe. Pre-requisite documented in Caveat #7. See N3. |
| Does the DNR ID cache refresh interval (5 min) create a window for DNR violations? | Yes, a narrow 5-minute window exists. Severity LOW — rare trigger (administrative DNR marking), short window, fail-closed on cache failure. See N1. |
| Does PG classification enrichment expose Hermes to data it shouldn't see during the enrichment query itself? | No. The enrichment query runs under `hermes_memory_bridge` role with RLS policies active (classification ceiling + surveillance isolation). If an FTS5 result references a Critical episode, RLS prevents enrichment from returning classification, fail-closed then removes it from results. Defense-in-depth confirmed. |
| F-01 through F-15 guard status per PersonaSafetyPolicy | All 15 guarded by independent `GuinevereSafetyPlugin` (untouched). Six NEW guard layers added in v1.1 for memory-specific safety. |

---

## Recommendation

**Proceed to execution** with the following implementation notes:

1. **N1 (DNR cache window)**: Document the 5-minute refresh window as accepted risk in `verification-P3-003.md`, OR implement event-driven invalidation. Reducing to 60s is an acceptable middle path.

2. **N2 (Safe-word flag)**: During P3-001 implementation, specify the safe-word flag mechanism (storage, set/clear lifecycle, race condition handling) before claiming scaffold completion. This does not need to be resolved in the plan — it's an implementation detail — but must be verified at P3-008.

3. **N3 (Consent pre-requisite)**: Add "Consent state store (Redis DB2) provisioned and schema defined" to §15 Pre-Execution checklist to prevent implementation delays.

---

## Summary

| Original Finding | Original Verdict | v1.1 Status |
|---|---|---|
| S1 — Consent gate | FAIL | **RESOLVED** — Fail-closed consent gate in prefetch/sync_turn |
| S2 — DNR post-recall gate | NEEDS REVIEW | **RESOLVED** — DNR ID cache with fail-closed |
| S3 — Classification ceiling | NEEDS REVIEW | **RESOLVED** — PG enrichment with fail-closed |
| S4 — Surveillance isolation | NEEDS REVIEW | **RESOLVED** — RLS policy `source != 'surveillance'` |
| S5 — Safe-word logging | NEEDS REVIEW | **RESOLVED** — Explicit sync_turn prohibition + DNR audit trail |

| New Finding | Severity | Recommendation |
|---|---|---|
| N1 — DNR cache 5-min window | LOW | Document accepted risk or reduce to 60s |
| N2 — Safe-word flag unspecified | LOW-MEDIUM | Specify mechanism during P3-001 implementation |
| N3 — Consent pre-requisite not in checklist | LOW | Add to Pre-Execution checklist |

**The v1.1 planner gate is approved for Wave 1 execution.** All CRITICAL and HIGH safety gaps from the original audit are resolved. The remaining observations are implementation-level concerns that do not block planning.

---

## Footer

| Field | Value |
|---|---|
| Auditor | Consent-Safety Specialist (read-only re-audit) |
| Report Path | `docs/setup-evidence/phase-3/audit-safety-v1.1.md` |
| Original Report | `docs/setup-evidence/phase-3/audit-safety.md` |
| Policy Verified | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (full text) |
| Planner Gate | `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.1, 726 lines) |
| Persona Boundary | Preserved — Y4 baseline/Y5 ceiling enforced by independent safety_plugin |
| Consent Boundary | **RESOLVED** — Fail-closed consent gate in P3-001 |
| Surveillance Boundary | **RESOLVED** — RLS policy `source != 'surveillance'` in P3-004 |
| DNR Boundary | **RESOLVED** — DNR ID cache + fail-closed in P3-003 |
| Classification Boundary | **RESOLVED** — PG enrichment + fail-closed in P3-003 |
| F-01 through F-15 | GUARDED by independent GuinevereSafetyPlugin (untouched by Phase 3) |