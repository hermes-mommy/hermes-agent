---
title: "Rail Count Consistency Audit — Round 2"
audit_id: "P27-R2-01"
scope: "Phase 7 rail count fix verification (3-rail → 4-rail)"
files_audited:
  - "docs/setup-evidence/P27/plan/p27-hermes-society-foundation-plan.md"
  - "docs/setup-evidence/P27/plan/p27-p28-p36-master-roadmap.md"
  - "docs/setup-evidence/P27/plan/p28-dual-autonomous-hermes-blueprint.md"
verdict: "PASS"
date: "2026-06-28"
auditor: "Guinevere"
---

# Rail Count Consistency Audit — Round 2

## 1. Audit Objective

Verify that Phase 7 fixes correctly changed all "3-rail" references to "4-rail" for the P28 simplified life-loop, with the 4 rails consistently named: **perception, peer_dialogue, reflection_simple, safety_envelope**. Ensure 7-rail references for P29+ remain untouched.

---

## 2. Check 1 — Old Rail References (3-rail / three-rail)

**Expected:** ZERO matches claiming P28 uses a 3-rail system.

**Result:** 1 match found.

| File | Line | Content | Verdict |
|---|---|---|---|
| `p28-dual-autonomous-hermes-blueprint.md` | 2410 | `The 3 rails **absent in P28** (Inner Dialogue, Desire/Goal, Initiative/Proactivity) are deferred because they require:` | **PASS — contextual false positive** |

**Analysis:** This line says "3 rails **absent** in P28" — it counts the 3 rails that are *missing* from the full 7-rail set, not that P28 uses 3 rails. The math is correct: 7 total − 3 absent = 4 present. This is consistent with the 4-rail claim and actually *reinforces* it. No fix needed.

**No remaining "3-rail" claims exist in any file.**

---

## 3. Check 2 — New Rail References (4-rail / four-rail)

**Expected:** All occurrences correctly reference P28 simplified life-loop.

**Result:** 16 matches across all 3 files. All PASS.

### p27-hermes-society-foundation-plan.md (4 matches)

| Line | Content | Context | Verdict |
|---|---|---|---|
| 646 | `enable_7_rail: true   # P28 starts with simplified 4-rail (perception, peer_dialogue, reflection_simple, safety_envelope)` | Config comment | ✅ |
| 3718 | `Each agent has its own 4-rail MinimalScheduler (perception, peer_dialogue, reflection_simple, safety_envelope)` | P28 deliverable table | ✅ |
| 3743 | `4 rails (perception, peer_dialogue, reflection_simple, safety_envelope) \| Full 7 rails` | P28 vs P29 comparison | ✅ |
| 3787 | `Implement per-instance 4-rail MinimalScheduler (perception, peer_dialogue, reflection_simple, safety_envelope).` | Implementation task | ✅ |

### p28-dual-autonomous-hermes-blueprint.md (9 matches)

| Line | Content | Context | Verdict |
|---|---|---|---|
| 45 | `Own autonomy loop (simplified 4-rail, NOT full 7-rail)` | Critical capabilities table | ✅ |
| 257 | `Simplified 4-rail scheduler` | Deliverable table | ✅ |
| 271 | `wraps P20 heartbeat into 4-rail scheduler` | Implementation plan | ✅ |
| 426 | `scheduler_class: MinimalScheduler # P28 simplified 4-rail; full 7-rail = P29` | Config YAML | ✅ |
| 1750 | `4 rails (perception, peer_dialogue, reflection_simple, safety_envelope) instead of the full 7-rail` | Step 11 spec goal | ✅ |
| 1759 | `MinimalScheduler follows P27 §4.5 bootstrap sequence but with only 4 rails. The 4 rails are:` | Rail enumeration intro | ✅ |
| 2399 | `P28 uses a **simplified 4-rail loop** (NOT the full 7-rail). Full 7-rail deferred to P29.` | FAQ section | ✅ |
| 2444 | `MinimalScheduler.start() — launches 4 rail tasks.` | Bootstrap sequence | ✅ |
| 2668 | `MinimalScheduler: 4 rails tick at specified cadence; HARD STOP cancellation within 100ms` | Verification table | ✅ |

### p27-p28-p36-master-roadmap.md (3 matches)

| Line | Content | Context | Verdict |
|---|---|---|---|
| 113 | `Per-instance 4-rail MinimalScheduler (Perception, Peer_Dialogue, Reflection_Simple, Safety_Envelope)` | Deliverable D12 | ✅ |
| 240 | `D12 (4-rail scheduler) \| P27 §13 Life-Loop Architecture (P29 = full 7-rail)` | Provenance table | ✅ |
| 313 | `Society retains 4-rail scheduler from P28` | FAQ / proceed-without-P29 | ✅ |

---

## 4. Check 3 — Rail Name Consistency

**Expected:** The 4 rails are always: **perception, peer_dialogue, reflection_simple, safety_envelope**.

**Result:** PASS — all 16 occurrences name the same 4 rails in the same order.

| Rail Name | Occurrences | Files | Consistent |
|---|---|---|---|
| perception | 6 explicit listings | All 3 files | ✅ |
| peer_dialogue | 6 explicit listings | All 3 files | ✅ |
| reflection_simple | 6 explicit listings | All 3 files | ✅ |
| safety_envelope | 6 explicit listings | All 3 files | ✅ |

The rail array in the blueprint config (line 427) reads:
```yaml
rails: [perception, peer_dialogue, reflection_simple, safety_envelope]
```

This matches every prose reference across all 3 files.

---

## 5. Check 4 — 7-Rail References for P29+

**Expected:** 7-rail references remain intact for P27 full architecture and P29 full MacroStateScheduler.

**Result:** 30 matches across all 3 files. All correctly scoped.

| File | 7-rail count | Scoping | Verdict |
|---|---|---|---|
| `p27-hermes-society-foundation-plan.md` | 20 | P27 full architecture, §7 Life-Loop, P29 upgrade | ✅ |
| `p28-dual-autonomous-hermes-blueprint.md` | 5 | Comparison context ("NOT full 7-rail", "full 7-rail = P29") | ✅ |
| `p27-p28-p36-master-roadmap.md` | 5 | P29 scope, cross-rail HARD STOP, provenance | ✅ |

**No accidental downgrades of P29+ from 7-rail to 4-rail detected.**

---

## 6. Check 5 — Blueprint Authoritative Statement

**Expected:** The P28 blueprint (authoritative source for P28) says 4-rail with correct rail names.

**Result:** PASS.

Key authoritative statements in the blueprint:

| Line | Statement |
|---|---|
| 45 | `Own autonomy loop (simplified 4-rail, NOT full 7-rail)` |
| 426-427 | `scheduler_class: MinimalScheduler # P28 simplified 4-rail; full 7-rail = P29` / `rails: [perception, peer_dialogue, reflection_simple, safety_envelope]` |
| 1750 | `A minimal scheduler wrapping P20 heartbeat with **4 rails** (perception, peer_dialogue, reflection_simple, safety_envelope) instead of the full 7-rail` |
| 2399 | `P28 uses a **simplified 4-rail loop** (NOT the full 7-rail). Full 7-rail deferred to P29.` |

The blueprint correctly and consistently claims 4-rail for P28 with the exact rail names.

---

## 7. Summary

| Check | Criteria | Result |
|---|---|---|
| 1. No old "3-rail" claims | 0 matches claiming P28 = 3-rail | ✅ PASS (1 contextual "3 absent" — correct) |
| 2. All "4-rail" correct context | 16 matches, all P28 simplified | ✅ PASS |
| 3. Rail names consistent | perception, peer_dialogue, reflection_simple, safety_envelope | ✅ PASS |
| 4. 7-rail preserved for P29+ | 30 matches, all correctly scoped | ✅ PASS |
| 5. Blueprint authoritative | 4-rail with correct names | ✅ PASS |

---

## 8. Verdict

**PASS** — Phase 7 rail count fixes are fully consistent across all 3 plan files. Zero stale "3-rail" claims remain. All 16 "4-rail" references are correctly contextualized for P28. The 4 rails are consistently named. 7-rail references for P29+ are untouched. The blueprint authoritatively states 4-rail with the correct rail names.

---

*Audit performed: 2026-06-28 | Auditor: Guinevere | Phase: P27 Round 2*
