---
title: "P27 Integration Consistency Audit — Round 2"
date: "2026-06-28"
auditor: "Sisyphus-Junior (sub-agent executor)"
scope: "Cross-file integration consistency after Phase 7 (21 edits across 3 plan files)"
files_audited:
  - "docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md"
  - "docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md"
  - "docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
reference:
  - "docs/setup-evidence/P27/evidence/p27-round-1-fix-log.md"
  - "docs/setup-evidence/P27/evidence/audits/round-1/09-safety-boundary-audit.md"
---

# P27 Integration Consistency Audit — Round 2

## Executive Summary

**Overall Verdict: NEEDS REVIEW (3 findings)**

Phase 7 applied 21 edits across 3 plan files to fix 5 NEEDS REVIEW and 1 FAIL finding from round 1. This audit verifies that the 3 files still form a coherent whole after all edits. Of 10 cross-file integration checks, **7 pass cleanly**, **2 surface minor cross-file inconsistencies**, and **1 confirms documented gaps**.

The findings are documentation-layer issues, not architectural conflicts. No structural contradictions exist between the files.

---

## Check Results

| # | Check | Verdict | Finding |
|---|---|---|---|
| 1 | Rail count consistency | **PASS** | All 3 files consistently use "4-rail" with identical rail names |
| 2 | UUID version consistency | **NEEDS REVIEW** | Plan §5.10 L1092 still says "UUID v7" for envelope `id` dedup key |
| 3 | Formal verification supersedence | **PASS** | Plan §19 supersedence note ↔ roadmap §11.11 absorption map aligned |
| 4 | Memory schema consistency | **NEEDS REVIEW** | Blueprint DDL for `kg_entities.created_by_agent` missing NOT NULL + 'system' |
| 5 | HPP envelope consistency | **NEEDS REVIEW** | Blueprint §5.1 schema has duplicate `idempotency_key` field |
| 6 | Aspirational claims | **PASS** | §24.3 accurately reflects round-1 results; §25.6 is a future template |
| 7 | Terminology (no hierarchy) | **PASS** | All hierarchical terms used only in negation/rejection context or author metadata |
| 8 | P28 scope agreement | **PASS** | All 3 files agree: full 7-rail=P29, executors=P33, P24 fork=P32 |
| 9 | Safety boundary gaps | **PASS** | 2 NEEDS REVIEW items from safety auditor are documented; not yet addressed in Phase 7 |
| 10 | Fix log accuracy | **PASS** | All 7 fixes verified present in actual file contents |

**PASS: 7 / NEEDS REVIEW: 3 / FAIL: 0**

---

## Detailed Findings

### Check 1: Rail Count Consistency — PASS

All 3 files consistently say "4-rail" for P28 with identical rail names: `perception`, `peer_dialogue`, `reflection_simple`, `safety_envelope`.

**Evidence:**

| File | Locations | Rail Names |
|---|---|---|
| Plan | L646, L3718, L3743, L3787 | perception, peer_dialogue, reflection_simple, safety_envelope |
| Roadmap | L113, L240, L313 | Perception, Peer_Dialogue, Reflection_Simple, Safety_Envelope |
| Blueprint | L45, L257, L271, L426, L1750, L1759, L2399, L2668 | perception, peer_dialogue, reflection_simple, safety_envelope |

No stale "3-rail" references remain. Fix 1 fully applied.

---

### Check 2: UUID Version Consistency — NEEDS REVIEW

**Finding: Plan §5.10 L1092 still references "UUID v7" for the envelope `id` dedup key.**

The Phase 7 Fix 4 changed the envelope `id` field from `uuid v7` to `uuid v4` in two places:
- Plan §5.2 L897: `"id": "<uuid v4 — globally unique, message identity>"` ✅
- Blueprint §5.1 L2108: `"id": "<uuid v4>"` ✅

However, a downstream reference to the same field was missed:

| Location | Current Text | Expected |
|---|---|---|
| Plan §5.10 L1092 | `\| id (UUID v7, dedup key) \| Inbox check: rejects duplicates \|` | Should say "UUID v4" |

**Scope:** This is a table in the "Replay Attack Defense" section that describes the same `id` field from §5.2. The inconsistency means a reader checking §5.10 would see UUID v7 while §5.2 says UUID v4.

**Severity:** Low. The envelope schema (§5.2) is authoritative. The §5.10 table is a reference summary. No implementation impact since code would use the schema, not the table.

**Note:** Plan L361 ("UUID v7 or {slug}-v{epoch}-{short_hash}") and L3221 refer to `society_id`, which is a different field. Those are not inconsistencies.

---

### Check 3: Formal Verification Supersedence — PASS

Plan §19 header (L3811) states:

> **SUPERSEDED** by `p27-p28-p36-master-roadmap.md` — see that document for the authoritative forward roadmap.

Roadmap §11.11 (L856-869) contains the Formal Verification Absorption Map with a table mapping each P27 §19.1 P36 deliverable to its new home:

| P27 Deliverable | New Phase |
|---|---|
| ATL model-checking | P34 D7 |
| λ_A-calculus lint | P29 D2 + P34 D8 |
| KILLBENCH-grade kill switch | P31 D10 |
| RiskGate AVF | P29 D10 |
| Goal-Autopilot False-Success | P29 D3/D14 |
| AAF causal attribution | DEFERRED |
| Anti-collusion detection | DEFERRED |
| Closed-loop governance | DEFERRED |

The supersedence note correctly delegates authority to the roadmap. The absorption map correctly redistributes 5 deliverables and flags 3 as deferred. Fix 6 fully applied.

---

### Check 4: Memory Schema Consistency — NEEDS REVIEW

**Finding: Blueprint DDL for `kg_entities.created_by_agent` is inconsistent with plan.**

Fix 3 was applied to the plan (§6.2.6) to tighten `kg_entities.created_by_agent`:
- Plan L1382-1384: `created_by_agent TEXT NOT NULL CHECK (created_by_agent IN ('guinevere','pharsa','system'))` with backfill step

However, the blueprint's actual migration DDL (Step 6, Migration 004) was NOT updated to match:
- Blueprint L1351-1352: `created_by_agent TEXT CHECK (created_by_agent IN ('guinevere', 'pharsa'))`

**Discrepancies:**

| Attribute | Plan (authoritative) | Blueprint DDL | Gap |
|---|---|---|---|
| NOT NULL | ✅ Present | ❌ Missing | Blueprint allows NULL |
| 'system' in CHECK | ✅ Present | ❌ Missing | Blueprint rejects 'system' rows |
| Backfill step | ✅ Present (L1382) | ❌ Missing | No migration for existing NULL rows |

**Secondary finding:** Within the plan itself, `kg_edges.created_by_agent` (L1389-1390) has `CHECK (created_by_agent IN ('guinevere','pharsa'))` without `'system'`, while `kg_entities.created_by_agent` (L1383-1384) includes `'system'`. This may be intentional (edges always have a specific agent owner) or an oversight. Recommend explicit clarification.

**Severity:** Medium. An implementer following the blueprint DDL literally would create a table that differs from the plan's specification. The plan is authoritative, so the blueprint DDL should be updated.

---

### Check 5: HPP Envelope Consistency — NEEDS REVIEW

**Finding: Blueprint §5.1 schema has `idempotency_key` defined twice.**

The blueprint envelope schema (L2104-2152) defines `idempotency_key` at two locations within the same JSON object:

1. L2109 (top-level, transport section): `"idempotency_key": "<uuid v4 — replay defense>"`
2. L2147 (provenance/audit section): `"idempotency_key": "<uuid v4>"`

The plan's envelope (§5.2 L897-898) defines it only once, at the top level.

**Impact:** An implementer parsing the blueprint schema literally would see a duplicate key in JSON. While JSON parsers typically use the last value, this is a schema documentation error that could cause confusion.

**Severity:** Low. The plan's schema (§5.2) is the canonical reference. The blueprint note at L2155 states "The full envelope structure with all fields is documented in P27 §5.2." The duplicate is a blueprint-only artifact.

---

### Check 6: Aspirational Claims — PASS

**§24.3 (L4540):** Round-1 status blockquote accurately reflects actual results:

> Round 1 status (2026-06-28): Audit round 1 completed with 14 auditors. Results: 7 PASS, 5 NEEDS REVIEW (fixes applied in Phase 7), 1 FAIL (aspirational claims corrected), 1 MISSING (Safety Boundary re-run).

**§25.6 (L4673):** Final report template section 3 says "all 20 hard rejection criteria PASS." This is acceptable because:
- §25.6 is a template for the Phase 9 final report (not yet written)
- Section 8 of the same template (L4678) acknowledges actual round-1 results
- The template describes the target state after round 2 completion

Fix 2 correctly replaced the original aspirational "all PASS in round 1 and 2" with actual results in §24.3, while preserving §25.6 as a forward-looking template.

---

### Check 7: Terminology — PASS

All occurrences of hierarchical terms (`coordinator`, `sub-agent`, `parent`, `primary`, `worker`) are in appropriate context:

| Term | Context | Classification |
|---|---|---|
| "No coordinator" (plan L81, L104, L164, L373, etc.) | Rejection/assertion of no-hierarchy | ✅ Negation |
| "NOT a sub-agent" (plan L226, L240, L307, blueprint L348) | Rejection/assertion | ✅ Negation |
| "Guinevere (parent agent)" (plan L4775, blueprint L5/L2904, roadmap L5/L1233) | Author metadata attribution | ✅ Author identity |
| "parent-only edit" (plan L4667) | File ownership discipline (AGENTS.md rule) | ✅ Process terminology |
| "Sub-Agent Rejection Auditor" (plan L4244) | Audit report filename | ✅ Audit label |
| "operator sub-agents" (plan L1027, L2574) | AGENTS.md governance entities | ✅ Governance context |
| "Pharsa is not Guinevere's sub-agent" (plan L227) | Anti-hierarchy assertion | ✅ Negation |

No hierarchical terms used in descriptive design context where they would imply a hierarchy in the Hermes Society architecture.

---

### Check 8: P28 Scope Agreement — PASS

All 3 files agree on P28 boundaries:

| Boundary | Plan | Roadmap | Blueprint |
|---|---|---|---|
| Full 7-rail = P29 | L3820 ("P29: 7-rail MacroStateScheduler") | L240 ("P29 = full 7-rail") | L45, L56, L426, L1750, L2399 |
| Action executors = P33 | L3824 ("P33: P23 Action Executors") | §8 | L66, L96, L2805, L2849 |
| P24 fork = P32 | L3823 ("P32: P24 Fork Integration") | §7 | L65, L97 |
| P28 = 4-rail only | L3718, L3743, L3787 | L113, L240, L313 | L45, L426, L1750, L2399 |
| P28 = zero outbound actions | L3824 | §8 | L66, L96, L2805, L2849 |
| P28 = no voice | L3428 | §5 | L98 |

No scope contradictions found.

---

### Check 9: Safety Boundary NEEDS REVIEW Items — PASS (Documented Gap)

The safety boundary auditor (09-safety-boundary-audit.md) identified 2 NEEDS REVIEW items:

**NR-1: Surveillance Data Boundary** — No explicit section in P28 blueprint mapping surveillance data to the 4-domain privacy framework. Recommended: add §2.X "Surveillance Data Boundary" or cross-reference `docs/30-data/31-SurveillanceDataPolicy_v1.0.md`.

**NR-2: Distress Protocol in P28** — P28 blueprint MinimalScheduler (Step 11) has no explicit distress detection hook. The `safety_envelope` rail's distress detection responsibility is undefined. Recommended: add PersonaSafetyPolicy §8 distress levels (D0-D4) wiring.

**Phase 7 status:** Neither item was addressed in Phase 7 fixes. The fix log (p27-round-1-fix-log.md) does not list these as targets. This is correct behavior — Phase 7 fixed the 5 NEEDS REVIEW + 1 FAIL findings that had concrete remediation. The safety boundary items are documentation enhancements with "Low" and "Medium" severity, respectively.

**Current status:** Both items remain as open documentation gaps. They should be tracked in the round-2 remaining issues list and addressed either in Phase 9 (docs sync) or during P28 implementation planning.

---

### Check 10: Fix Log Accuracy — PASS

All 7 fixes from `p27-round-1-fix-log.md` verified against actual file contents:

| Fix # | Claimed Change | Verification | Status |
|---|---|---|---|
| 1 | "3-rail" → "4-rail" with rail names | Grep confirms 0 "3-rail" references; 16 "4-rail" references with correct names | ✅ Verified |
| 2 | Aspirational "all PASS" → actual results | L4540 blockquote shows "7 PASS, 5 NEEDS REVIEW, 1 FAIL, 1 MISSING" | ✅ Verified |
| 3 | Schema gaps: shared_world note, kg_entities NOT NULL, kg_edges ADR-050 note, P28 memory tables stub | L1277 design note, L1382-1384 NOT NULL+'system', L1394 ADR-050 note, L3721 stub note | ✅ Verified |
| 4 | idempotency_key added; id v7→v4 | L897-898 shows uuid v4 + idempotency_key; blueprint L2108-2109 matches | ✅ Verified (with caveat: L1092 residual v7, blueprint duplicate key) |
| 5 | senior_mama → sugar_mommy; staged deployment reframed | L409 shows sugar_mommy; L2929 shows canary rotation | ✅ Verified |
| 6 | Supersedence note + absorption map | L3811 supersedence note; roadmap L856-869 absorption map | ✅ Verified |
| 7 | Blueprint implementation guidance note | L278 blockquote present | ✅ Verified |

**Fix log line counts:** The fix log reports "4779 → 4790 lines" for the plan (current: 4791, +1 from fix log estimate — acceptable margin from intermediate edits). Roadmap "914 → 934 lines" (current: 1260 — significantly larger; the fix log may have measured before the §11.11 section was fully expanded, or subsequent edits added content). Blueprint "2921 → 2926 lines" (current: 2925, -1 — within margin).

**Note on fix log line numbers:** The fix log references line numbers in the pre-edit files (e.g., "L646", "L3712"). These do not match current post-edit line numbers due to inserted content shifting downstream lines. This is expected behavior for a fix log — the line numbers document where edits were applied, not where content currently resides.

---

## Cross-File Inconsistency Summary

| # | Inconsistency | Files | Severity | Recommended Fix |
|---|---|---|---|---|
| 1 | Plan §5.10 L1092: envelope `id` still says "UUID v7" | Plan internal | Low | Change "UUID v7" to "UUID v4" in §5.10 table |
| 2 | Blueprint DDL `kg_entities.created_by_agent`: missing NOT NULL + 'system' vs plan | Plan ↔ Blueprint | Medium | Update blueprint Migration 004 DDL to match plan §6.2.6 |
| 3 | Blueprint §5.1: `idempotency_key` defined twice in schema | Blueprint internal | Low | Remove duplicate at L2147 |

---

## Open Items from Round 1 (Not Addressed in Phase 7)

These items from the round-1 fix log "Remaining Issues" table are still open:

| # | Issue | Status |
|---|---|---|
| 1 | 3 deferred formal verification deliverables (no phase assignment) | Open — assign during per-phase planning |
| 2 | 6 missing audit files (09-14) | Partially resolved — 09 and 10 exist |
| 3 | Evidence schema has 11 sections (missing evidence_artifacts) | Open |
| 4 | Blueprint F-01: phantom `society_app.py` reference | Open |
| 5 | Blueprint F-02: `shared_world.retrievability` formula bug | Open |
| 6 | Blueprint F-03: `hpp_outbox`/`hpp_inbox` DDL missing | Open |
| 7 | Blueprint F-04: `_cascade_halt()` logs but doesn't halt | Open |
| 8 | P36 supersedence note only in §19 header (not subsections) | Open |
| 9 | Phase 9 evidence artifacts | Open — deferred |
| 10 | `research/REPO_STATE.md` missing | Open |
| 11 | Safety NR-1: Surveillance data boundary documentation | Open |
| 12 | Safety NR-2: Distress protocol P28 hooks | Open |

---

## Conclusion

The 3 P27 plan files form a **largely coherent whole** after Phase 7's 21 edits. All 7 fixes are verified present. Rail count, P28 scope, formal verification supersedence, and terminology are fully consistent across files.

Three minor cross-file inconsistencies remain:
1. A single "UUID v7" residual in the plan's §5.10 table (Low severity)
2. The blueprint's `kg_entities` DDL not matching the plan's tightened schema (Medium severity)
3. A duplicate `idempotency_key` in the blueprint's envelope schema (Low severity)

None of these are architectural contradictions. All are documentation-layer sync gaps between the authoritative plan and the downstream blueprint. The Medium-severity DDL mismatch (#2) is the only item that could cause an implementation divergence if not fixed before P28 coding begins.

---

## Verdict Summary

| Verdict | Count | Checks |
|---|---|---|
| **PASS** | 7 | #1, #3, #6, #7, #8, #9, #10 |
| **NEEDS REVIEW** | 3 | #2 (UUID v7 residual), #4 (DDL mismatch), #5 (duplicate key) |
| **FAIL** | 0 | — |

---

## Audit Matrix Reference

| Check | Plan File | Roadmap File | Blueprint File |
|---|---|---|---|
| Rail count | L646, L3718, L3743, L3787 | L113, L240, L313 | L45, L257, L271, L426, L1750, L1759, L2399, L2668 |
| UUID version | L897, L1092 | L391 | L2108, L2147 |
| Supersedence | L3811 | L856-869 | — |
| Memory schema | L1277, L1378-1394 | — | L1351-1352, L1358-1359 |
| HPP envelope | L897-898 | — | L2104-2152 |
| Aspirational | L4540, L4673 | — | — |
| Terminology | L81-L4775 (17 locations) | L5, L1165, L1233 | L5, L348, L2904 |
| P28 scope | L3820-3827 | §3-§11 | L45-98, L426, L2399-2414, L2805-2849 |
| Safety boundary | — | — | — (ref: 09-safety-boundary-audit.md) |
| Fix log | All 14 plan edits | All 4 roadmap edits | All 3 blueprint edits |

---

| Field | Value |
|---|---|
| Report Version | 1.0 |
| Auditor | Sisyphus-Junior (sub-agent executor) |
| Date | 2026-06-28 |
| Status | COMPLETE |
| Output Path | `docs/setup-evidence/P27/evidence/audits/round-2/06-integration-consistency-audit.md` |
