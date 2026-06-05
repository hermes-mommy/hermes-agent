# Memory Safety Audit Report — Phase 3 Planner Gate v1.1

**Auditor**: Independent Memory Safety Auditor  
**Date**: 2026-06-05  
**Document Reviewed**: `docs/setup-evidence/phase-3/batch-plan-phase-3.md` (v1.1, 726 lines)  
**Previous Audit Reference**: `docs/setup-evidence/phase-3/audit-safety-v1.1.md` (PASS, focused on S1–S5)  
**Policies Consulted**:
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (666 lines)
- `docs/30-data/32-ConsentRevocationPolicy_v1.0.md` (453 lines)  
**Code Consulted**:
- `src/memory/read_pipeline.py` (963 lines)
- `src/memory/write_pipeline.py` (359 lines)
- `src/memory/dnr.py` (418 lines)
- `src/memory/embeddings.py` (CLASSIFICATION_ORDER, lines 107-113)
- `src/hermes/memory_bridge.py` (295 lines)

---

## Overall Verdict: NEEDS REVIEW

**Rationale**: 9 of 10 audit criteria PASS. One criterion (S10 — Data Exfiltration via state.db) requires correction: the RLS classification ceiling SQL references a non-existent column name (`classification_level`) and uses string comparison that would not correctly enforce the numeric classification ordering. This is a concrete planning error in the SQL migration DDL that must be corrected before P3-004 execution. Zero criteria FAIL.

---

## S1: Consent Gate (P3-001) — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| Consent gate in BOTH prefetch() and sync_turn() | P3-001 Section 8 "Consent Gate (NEW)": "prefetch() and sync_turn() MUST check consent state before delegating to pipelines." | PASS |
| Fail-closed (unknown = block) | "if consent state cannot be determined, block the operation and log an audit event." | PASS |
| Checked BEFORE pipeline delegation | "Consent gate is checked BEFORE pipeline delegation — not inside pipelines" | PASS |
| Safe-word detection connected to sync_turn skip | "When a safe-word is detected, the plugin's sync_turn must NOT store that conversation turn." | PASS |
| Concrete consent state store defined | "Redis DB2 or config" — acknowledged as net-new; Caveat 7 documents pre-requisite. | PASS |

### Recommendation
None. The consent gate specification is complete and safety-correct. The unresolved consent state store is a legitimate pre-requisite (Caveat 7), not a plan flaw.

---

## S2: DNR Enforcement (P3-003) — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| DNR ID cache from PG, refresh every 5 min | P3-003 Safety Gate 1: Load `SELECT id FROM memory.episodic_memory WHERE do_not_recall = true` into `set[str]`, refresh every 5 min via daemon thread. | PASS |
| Cache fail-closed | "If DNR cache load fails, block ALL session_search results (fail-closed)." | PASS |
| Post-recall DNR cross-reference on ALL Hermes recall paths | Architecture diagram shows "DNR Cache Cross-Reference (remove DNR-marked IDs)" before "Inject into LLM Context." | PASS |
| Thread safety | Not explicitly specified beyond "background daemon thread." Locking mechanism TBD at implementation. | IMPL DETAIL |

### Recommendation
None. DNR ID cache approach is safety-correct. The 5-minute stale-cache window is documented as accepted risk (observation N1 from prior safety audit). Thread safety mechanism is an implementation detail to verify during P3-003 code review.

---

## S3: Classification Ceiling (P3-003) — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| PG enrichment via batch SELECT | P3-003 Safety Gate 2: `SELECT id, classification FROM memory.episodic_memory WHERE id IN (...)` batch query, max 20 IDs. | PASS |
| Enrichment fail-closed | "If PG enrichment query fails, treat all results as Critical (fail-closed = return empty)." | PASS |
| Principal ceiling guinevere_core = Critical | Filter: `classification_level(result) <= principal_ceiling(guinevere_core)`. Existing code confirms `guinevere_core` maps to `CRITICAL`. | PASS |
| Classification ordering correct | Verified in `src/memory/embeddings.py` lines 107-113: `PUBLIC=0 < INTERNAL=1 < RESTRICTED=2 < CONFIDENTIAL=3 < CRITICAL=4`. Unknown labels map to 5 (beyond Critical, fail-closed). | PASS |

### Confirmed Code
```python
# src/memory/embeddings.py lines 107-113
CLASSIFICATION_ORDER: dict[str, int] = {
    PUBLIC: 0,        # "Public"
    INTERNAL: 1,      # "Internal"
    RESTRICTED: 2,    # "Restricted"
    CONFIDENTIAL: 3,  # "Confidential"
    CRITICAL: 4,      # "Critical"
}
# classification_level() returns CLASSIFICATION_ORDER.get(label, 5) — unknown → 5
```

### Recommendation
None. Classification enrichment approach is sound and defense-in-depth: even if FTS5 returns a Critical-classified episode (leaked before RLS was active), the enrichment query runs under `hermes_memory_bridge` role with RLS policies — so Critical rows won't be returned by the enrichment query, triggering fail-closed → result removed.

---

## S4: Anti-Hallucination Guard — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| Guard injected when memories empty after ALL filtering | P3-003 Architecture: "Anti-Hallucination Guard (if empty after all filters)" before "Inject into LLM Context." P3-003 scaffold Hard Rejection: "FAIL if: anti-hallucination guard not injected on empty results." | PASS |
| Prevents LLM from fabricating memories | Guard is the last step before LLM context injection. If all results are filtered out, the guard replaces an empty list with an explicit instruction to the LLM. | PASS |

### Recommendation
None. The guard is correctly positioned in the safety pipeline. During P3-003 implementation, verify the exact guard text is present.

---

## S5: Safe-Mode Content Substitution (P3-003) — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| Safe-mode handled for Critical/Restricted results | P3-003 Safety Gate 4: "Replace raw content with safe-mode placeholders for Critical/Restricted results when safe_mode=True." | PASS |
| Substitution applied BEFORE LLM injection | Architecture diagram shows "Safe-Mode Substitution" before "Inject into LLM Context." | PASS |
| Existing pipeline has robust safe-mode | `read_pipeline.py` already implements `build_safe_content()`, `_SAFE_MODE_CEILING`, `_is_safe_mode_blocked_content()`, three placeholder types. | PASS |

### Recommendation
None. The P3-003 safety_gates.py should delegate to or mirror the existing `build_safe_content()` logic from `read_pipeline.py` for consistency.

---

## S6: Surveillance Isolation (P3-004) — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| RLS policy for surveillance isolation | P3-004 SQL Migration: `CREATE POLICY hermes_surveillance_isolation ON memory.episodic_memory FOR SELECT TO hermes_memory_bridge USING (source != 'surveillance');` | PASS |
| `source != 'surveillance'` filter | Explicitly in the USING clause. Simple string inequality — no lexicographic ambiguity. | PASS |
| FORCE ROW LEVEL SECURITY applied | `ALTER TABLE memory.episodic_memory FORCE ROW LEVEL SECURITY;` — applies to ALL sessions including table owner. | PASS |
| Scaffold verification commands | `SELECT tablename, policyname FROM pg_policies WHERE schemaname='memory' AND rolename='hermes_memory_bridge'` must return >= 4 policies. | PASS |

### Recommendation
None. Surveillance isolation is correctly specified with both the RLS policy and scaffold verification commands.

---

## S7: HARD STOP / Distress Protocol — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| HARD STOP protocol preserved | Enforced by independent `GuinevereSafetyPlugin` at Hermes agent layer. Phase 3 does not modify safety_plugin.py. | PASS |
| Distress D2+ to Y0 enforcement preserved | Safety plugin's G02 DistressDetector + G07 YandereEngine. Untouched by Phase 3. | PASS |
| No Phase 3 steps bypass safety_plugin.py | P3-001 Safety Delegation: all safety decisions delegated to read/write pipelines. Plugin operates BELOW the safety layer. Memory context flows through LLM gated by safety_plugin. | PASS |
| P3-008 checklist verification | "HARD STOP / distress protocol unaffected" explicitly checked. | PASS |

### Recommendation
None. HARD STOP and distress protocols are enforced by independent safety infrastructure, not by the memory plugin.

---

## S8: Yandere Boundaries — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| Y4 baseline / Y5 ceiling preserved | Enforced by `GuinevereSafetyPlugin` G07 YandereEngine (caps at Y5, raises `YandereSafetyError` if >5). Untouched by Phase 3. | PASS |
| Memory plugin cannot influence yandere level | Memory plugin provides RECALL CONTEXT (memories) to the LLM prompt. Yandere intensity is set by safety_plugin based on mood/safety state, not by memory recall results. | PASS |
| P3-008 checklist verification | "Yandere Y4 baseline/Y5 ceiling preserved" explicitly checked. | PASS |

### Recommendation
None. Yandere boundaries are structurally separated from memory operations.

---

## S9: Safe-Word Logging — PASS

### Evidence
| Requirement | Plan Specification | Status |
|---|---|---|
| Safe-word detected turns logged to DNR audit trail | P3-008 checklist: "safe-word detected turns logged to DNR audit trail, sync_turn skips storage for safe-word turns." | PASS |
| sync_turn skips storage for safe-word turns | P3-001: "the plugin's sync_turn must NOT store that conversation turn. Safe-word detection is handled by the independent safety_plugin; the memory plugin checks a shared safe-word flag." | PASS |
| Existing DNR audit infrastructure | `dnr.py` provides `mark_memory_dnr()`, `_emit_audit_event()`. Metadata-only audit trail (no raw content logged). | PASS |

### Observation (N2 from prior safety audit)
The "shared safe-word flag" mechanism (storage location, set/clear lifecycle, race conditions) is unspecified. Prior auditor classified this as LOW-MEDIUM observation for implementation. Acceptance criteria are clear even if mechanism is TBD.

### Recommendation
During P3-001 implementation, specify the safe-word flag mechanism before claiming scaffold completion.

---

## S10: Data Exfiltration via state.db — NEEDS REVIEW

### Finding S10-A: RLS Classification Ceiling SQL Has Column Name and Type Issues (MEDIUM)

**Evidence**: P3-004 SQL Migration (plan v1.1):

```sql
CREATE POLICY hermes_classification_ceiling ON memory.episodic_memory
  FOR SELECT TO hermes_memory_bridge
  USING (classification_level <= 'Restricted');
```

**Problem 1 — Column name mismatch**: The Episodes ORM model stores classification as a string column named `classification`, NOT `classification_level`. The SQL column name `classification_level` does not exist in the current schema.

**Problem 2 — String comparison won't enforce numeric ordering**: Even if corrected to `classification`, PostgreSQL string comparison is lexicographic: `Confidential < Critical < Internal < Public < Restricted` alphabetically. With `classification <= 'Restricted'`:
- `Confidential` (C < R alphabetically) → BLOCKED incorrectly? Actually C < R, so PASSES when it SHOULD be BLOCKED.
- `Critical` (C < R) → PASSES when it SHOULD be BLOCKED
- `Internal` (I < R) → PASSES (correct)
- `Public` (P < R) → PASSES (correct)
- `Restricted` (R = R) → PASSES (correct)

This means the RLS policy as written would INCORRECTLY allow Confidential and Critical data through.

**Verified Classification Order** (from `src/memory/embeddings.py` lines 107-113):
`PUBLIC=0, INTERNAL=1, RESTRICTED=2, CONFIDENTIAL=3, CRITICAL=4`

**Required Fix**: The RLS policy must correctly enforce the boundary. Two approaches:

**Option A — IN clause (simpler, no schema change)**:
```sql
CREATE POLICY hermes_classification_ceiling ON memory.episodic_memory
  FOR SELECT TO hermes_memory_bridge
  USING (classification IN ('Public', 'Internal', 'Restricted'));
```
This is lexicographically unambiguous — exact string matching.

**Option B — Generated integer column (cleaner for future RLS policies)**:
```sql
ALTER TABLE memory.episodic_memory ADD COLUMN classification_level integer
  GENERATED ALWAYS AS (
    CASE classification
      WHEN 'Public' THEN 0
      WHEN 'Internal' THEN 1
      WHEN 'Restricted' THEN 2
      WHEN 'Confidential' THEN 3
      WHEN 'Critical' THEN 4
      ELSE 5
    END
  ) STORED;

CREATE POLICY hermes_classification_ceiling ON memory.episodic_memory
  FOR SELECT TO hermes_memory_bridge
  USING (classification_level <= 2);  -- 2 = Restricted
```
This aligns the database with the Python `CLASSIFICATION_ORDER` mapping and future-proofs all RLS policies.

**Severity**: MEDIUM. Planning intent is correct (block Confidential+Critical), but SQL as written would FAIL to enforce the intent. Must be corrected before P3-004 execution.

### Finding S10-B: Residual State.db Risk from Discord-Sourced Conversations (LOW)

**Analysis**: The RLS ceiling protects the PostgreSQL to Hermes READ path. However, Hermes processes ALL Discord conversations as the LLM framework before the memory plugin stores them. Hermes writes compressed data to `~/.hermes/state.db` natively.

- The write pipeline stores with `classification=RESTRICTED` (default, per P3-001). If Faiz shares Critical information in Discord, it exists in state.db regardless of RLS.
- Caveat 10 acknowledges: "If Critical-classified data is processed through Hermes (even transiently), it may be cached in state.db."
- The RLS mitigation is effective for the PG READ path but does not protect against Discord-sourced content in state.db.

**Severity**: LOW — acknowledged, documented, verification gate at P3-008.

### Recommendation for S10
1. **Before P3-004 execution**: Correct the RLS classification ceiling SQL using Option A (IN clause) or Option B (generated integer column). The plan's scaffold commands will verify policy existence, but the SQL syntax must be correct to actually enforce the ceiling.
2. **During P3-008**: Verify state.db contents do not contain Critical-classified data as documented in Caveat 10.

---

## All 10 Criteria Summary

| Criterion | Verdict | Notes |
|---|---|---|
| S1 — Consent Gate | **PASS** | Fail-closed consent gate in prefetch/sync_turn. Store pre-requisite documented. |
| S2 — DNR Enforcement | **PASS** | DNR ID cache with fail-closed. 5-min stale window accepted risk. |
| S3 — Classification Ceiling | **PASS** | PG enrichment with fail-closed. guinevere_core=Critical confirmed. |
| S4 — Anti-Hallucination Guard | **PASS** | Guard positioned between filtering and LLM injection. |
| S5 — Safe-Mode Substitution | **PASS** | Correctly positioned before LLM injection. |
| S6 — Surveillance Isolation | **PASS** | RLS policy `source != 'surveillance'` with FORCE RLS. |
| S7 — HARD STOP / Distress | **PASS** | Independent safety_plugin enforcement. Untouched by Phase 3. |
| S8 — Yandere Boundaries | **PASS** | Y4/Y5 enforced by safety_plugin. Memory plugin provides context only. |
| S9 — Safe-Word Logging | **PASS** | Explicit sync_turn skip + DNR audit trail. Flag mechanism TBD at impl. |
| S10 — Data Exfiltration | **NEEDS REVIEW** | RLS SQL has column name + type issues. Correct before P3-004. |

---

## Prior Audit Cross-Reference

The prior consent-safety re-audit (`audit-safety-v1.1.md`, PASS verdict) verified 5 original findings (S1–S5). This audit independently verifies those same domains plus 5 additional criteria (S6–S10).

| Prior Finding | Prior Verdict | This Audit | Notes |
|---|---|---|---|
| S1 — Consent gate | RESOLVED | PASS | Agreement |
| S2 — DNR post-recall gate | RESOLVED | PASS | Agreement |
| S3 — Classification ceiling | RESOLVED | PASS | Agreement |
| S4 — Surveillance isolation | RESOLVED | PASS | Agreement |
| S5 — Safe-word logging | RESOLVED | PASS | Agreement |
| S6–S9 | Not audited | PASS | New criteria, all pass |
| S10 | Not audited | NEEDS REVIEW | New finding: RLS SQL syntax error |

---

## Conclusion

The v1.1 planner gate is APPROVED for Wave 1 execution with one pre-condition: **correct the RLS classification ceiling SQL in P3-004 before DDL execution**. The plan is otherwise safety-complete with 9 of 10 criteria passing and zero failures.

The classification ceiling SQL issue is a MEDIUM-severity planning bug — the intent is correct but the implementation syntax is wrong. Fixing it requires changing one DDL statement (either use `IN ('Public', 'Internal', 'Restricted')` or add a generated integer column). No other plan sections need modification.

All other safety boundaries are correctly specified: consent gate (fail-closed), DNR enforcement (cache with fail-closed), classification ceiling (PG enrichment with fail-closed), anti-hallucination guard, safe-mode substitution, surveillance isolation (RLS), HARD STOP/distress (independent safety_plugin), yandere boundaries (independent safety_plugin), and safe-word logging (sync_turn skip + DNR audit trail).

---

## Footer

| Field | Value |
|---|---|
| Auditor | Independent Memory Safety Auditor (read-only) |
| Report Path | `docs/setup-evidence/phase-3/auditor-gate-P3-memory-safety-v1.1.md` |
| Subject | Phase 3 Planner Gate v1.1 — Memory Safety Boundary Compliance |
| Policies Verified | PersonaSafetyPolicy v1.0, ConsentRevocationPolicy v1.0 |
| Code Verified | read_pipeline.py, write_pipeline.py, dnr.py, embeddings.py, memory_bridge.py |
| Verdict | NEEDS REVIEW (1 finding, zero failures) |
| Blocks Execution | No — fix is trivial (one SQL DDL statement). Wave 1 can proceed after correction. |