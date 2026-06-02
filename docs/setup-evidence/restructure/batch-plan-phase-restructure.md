# Batch Plan — Post-MVP Phase Restructure (P0-P11 → P0-P22)

**Plan ID:** BP-PHASE-RESTRUCTURE-001
**Author:** Guinevere (planner)
**Date:** 2026-06-03
**Status:** READY FOR EXECUTION
**Evidence Root:** `docs/setup-evidence/restructure/`
**Total Atomic Tasks:** 13
**Estimated Duration:** 6-8 waves (3-5 hours wall-clock with parallelism)

---

## 1. Master Todo

| Task ID | Description | Depends On | Type | Step Agent |
|---------|-------------|-----------|------|------------|
| T1 | PROGRESS.md — rewrite P9/P10/P11 → P9/P10 + P11-P22 (canonical source) | None | sequential | implementation |
| T2 | ADR-033 — fix P11→P13 X auto-poster references | None | parallel | quick |
| T3 | CHECKLIST.md — restructure sections 11/12/13, reconcile step counts, add P11-P22 | T1 | sequential | implementation |
| T4 | StepPrompts.md — replace P9/P10/P11, add P11-P22 stubs, update header stats | T1 | sequential | implementation |
| T5 | IMPLEMENTATION_GUIDE.md — update phase table, step/phase counts, post-MVP refs | T3, T4 | sequential | implementation |
| T6 | ADR_Index_v1.0.md — add ADR-034 entry for this restructure | None | parallel | writing |
| T7 | BRD_v2.0.md — add P11-P22 expansion phase overview section | None | parallel | writing |
| T8 | AcceptanceCriteriaCatalog_v1.0.md — add P9-P10 exit gates + P11-P22 entry criteria | None | parallel | writing |
| T9 | Cost_FinOps_Model_v1.1.md — update cost tracking for P9-P22, add disambiguation | None | parallel | writing |
| T10 | docs/README.md — minor index reference updates | T5 | parallel | writing |
| T11 | adr/README.md — fix "first 25 ADRs" → "first 33 ADRs", add ADR-034 | T6 | parallel | quick |
| T12 | Cross-file verification — 9 grep checks across all modified files | T1-T11 | sequential | testing |
| T13 | Auditor orchestrator — spawn parallel auditors for all modified surfaces | T12 | audit-batch | review |

---

## 2. Dependency Map

```
T1 (PROGRESS.md ─ canonical)
├── T3 (CHECKLIST.md ── uses canonical counts)
│   └── T5 (IMPLEMENTATION_GUIDE ─ uses final counts)
├── T4 (StepPrompts.md ─ uses canonical counts)
│   └── T5 (shared)
│
T2 (ADR-033 ─ independent file) ─ no dependents
│
T6 (ADR_Index) ── T11 (adr/README ─ references ADR-034)
T7 (BRD ─ expansion section) ─ no dependents
T8 (AcceptanceCriteria ─ gate criteria) ─ no dependents
T9 (FinOps ─ cost tracking) ─ no dependents
T10 (docs/README ─ minor) ─ depends on T5 for final counts
│
All (T1-T11) ── T12 (verification grep) ── T13 (auditor)
```

### Dependency Graph Table

| Task | Depends On | Reason |
|------|-----------|--------|
| T1 | None | Starting point; PROGRESS.md is canonical source of truth |
| T2 | None | ADR-033 is independent file; zero shared content with any other target |
| T3 | T1 | Must match canonical step counts (P9=12, P10=19) and phase names from PROGRESS.md |
| T4 | T1 | Must match canonical counts and phase names; header "12 phases → 23 phases" requires T1 output |
| T5 | T3, T4 | Requires final reconciled step counts and phase counts from both tracker files |
| T6 | None | ADR_Index is independent governance doc; ADR-034 content is self-contained |
| T7 | None | BRD expansion section is independent; does not reference tracker counts |
| T8 | None | AcceptanceCriteria gate additions are independent governance content |
| T9 | None | FinOps cost model is independent; disambiguation is self-contained |
| T10 | T5 | Uses final phase structure summary (P11-P22 vs old P11) from IMPLEMENTATION_GUIDE |
| T11 | T6 | References ADR-034 which must exist in ADR_Index first |
| T12 | T1-T11 | Verification runs across all modified files |
| T13 | T12 | Auditor wave runs after all files pass verification |

---

## 3. Parallel Execution Graph

### Wave 1 (Start Immediately — Zero Dependencies)

```
├── T1: PROGRESS.md restructure (sequential — canonical source)
├── T2: ADR-033 fix (parallel — independent file)
├── T6: ADR_Index v1.0 (parallel — independent governance doc)
├── T7: BRD v2.0 (parallel — independent core doc)
├── T8: AcceptanceCriteria (parallel — independent governance doc)
└── T9: FinOps Model (parallel — independent FinOps doc)
```

**6 tasks fire in parallel.** T1 is the only one that blocks downstream tasks.

### Wave 2 (After T1 + Wave 1 Governance Docs Complete)

```
├── T3: CHECKLIST.md restructure (depends: T1)
├── T4: StepPrompts.md restructure (depends: T1)
└── T11: adr/README.md (depends: T6)
```

### Wave 3 (After T3 + T4 Complete)

```
├── T5: IMPLEMENTATION_GUIDE.md (depends: T3, T4)
└── T10: docs/README.md (depends: T5)
```

### Wave 4 (After All T1-T11 Complete)

```
└── T12: Cross-file verification (depends: T1-T11)
```

### Wave 5 (After T12 PASS)

```
└── T13: Auditor orchestrator (depends: T12)
```

### Critical Path
`T1 → T3 → T5 → T12 → T13`

### Estimated Parallel Speedup
Governance docs (T6-T9) run concurrent with tracker trio (T1-T4), saving ~60% time vs sequential.

---

## 4. Research Inputs

All five research reports read and synthesized before planning:

| # | Report | Path | Key Findings |
|---|--------|------|-------------|
| 1 | Impact Map | `research-reports/restructure/impact-map.md` | Master synthesis; phase taxonomy; discrepancy catalog; P13 spec; verification strategy |
| 2 | P9/P10/P11 References | `research-reports/restructure/p9-p10-p11-references.md` | 28 files with true phase references; exact line numbers for every P9/P10/P11 occurrence; false positive catalog |
| 3 | Post-MVP References | `research-reports/restructure/post-mvp-references.md` | 282 matches across 97 files; "post-MVP" boilerplate in 23 ADR files; special cases (ADR-021 filename, ADR-033 path refs) |
| 4 | Governance Phase References | `research-reports/restructure/governance-phase-references.md` | Four distinct "phase" concepts requiring disambiguation; BRD naming conflict (out of scope) |
| 5 | Feature Name References | `research-reports/restructure/feature-name-references.md` | Feature-to-phase redistribution map; old P11 steps → new phases; keyword occurrence counts |

---

## 5. Known State

### Current State of Each Target File

#### Priority 1 Files (Tracker Trio + Guide)

| File | Lines | Current P9 | Current P10 | Current P11 | Phase Count | Step Count |
|------|-------|-----------|-------------|-------------|-------------|------------|
| `PROGRESS.md` | 466 | 12 steps | 19 steps | 25 steps | "12 phases" implied | 257 total (113 complete) |
| `CHECKLIST.md` | 1034 | 15 steps (discrepancy) | 20 steps (discrepancy) | 25 steps | Sections 11/12/13 | N/A |
| `stepprompts/StepPrompts.md` | 8028 | 12 steps | 18+1 gate | 25 steps | "12 (P0-P11)" | "252" claimed |
| `docs/IMPLEMENTATION_GUIDE.md` | 572 | 12 steps | 18 steps | 25 steps | "12 phases (P0-P11)" | "252 steps" |

#### Priority 2 Files (Governance/Core)

| File | Lines | Current State |
|------|-------|--------------|
| `docs/10-governance/17-ADR_Index_v1.0.md` | 137 | 33 ADRs listed; Backlog has ADR-034 for "RTM Governance" (needs repurpose) |
| `docs/00-core/00-BRD_v2.0.md` | 495 | Phase 0-5 delivery plan; "post-MVP" refs at lines 186, 198, 256, 365, 395, 451 |
| `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` | 407 | Phase Gate Checklist §12: Phase 0-5 + MVP gate; AC-PHASE-008 for "Post-MVP expansion" |
| `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | 661 | §4.1 uses "Phase 1/2/3" for BUDGET phases (not delivery phases); cost tracking for P9-P11 only |
| `docs/README.md` | 321 | Document index; no phase-specific content to update significantly |
| `adr/README.md` | 136 | Line 20: "first 25 technical-core ADRs" (stale); Backlog ADR-034 listed; ADR count 33 |

#### Side Target

| File | Lines | Current State |
|------|-------|--------------|
| `adr/ADR-033-browser-automation-obscura.md` | 212 | Lines 73, 80, 152: "P11" referencing X auto-poster; line 212: path ref `docs/post-mvp/` |

---

## 6. Binding Decisions

These are the **canonical values** that ALL files must use. Any deviation is a scaffold violation.

### Canonical Step Counts

| Phase | Steps | Status |
|-------|-------|--------|
| P0 | 29 | UNCHANGED |
| P1 | 21 | UNCHANGED |
| P2 | 21 | UNCHANGED |
| P3 | 19 | UNCHANGED |
| P4 | 23 | UNCHANGED |
| P5 | 23 | UNCHANGED |
| P5.5 | (10 fixes) | UNCHANGED |
| P6 | 21 | UNCHANGED |
| P7 | 22 | UNCHANGED |
| P8 | 23 | UNCHANGED |
| **P9** | **12** | **CANONICAL (matches PROGRESS.md)** |
| **P10** | **19** | **CANONICAL (matches PROGRESS.md)** |
| P11-P22 | TBD | New phases, step counts to be determined |

### Canonical Phase Names

| Phase | Canonical Name |
|-------|---------------|
| P9 | Financial Tracking |
| P10 | Production Hardening |
| P11 | WhatsApp Integration |
| P12 | Gmail/Email Integration |
| P13 | X Auto Poster |
| P14 | Wearable/Xiaomi Watch |
| P15 | Windows Daemon + WebSocket |
| P16 | Knowledge Graph |
| P17 | Cross-Device Sync |
| P18 | Advanced Memory |
| P19 | Multi-Project Context |
| P20 | Self-Improvement Loop |
| P21 | Voice Interface |
| P22 | Additional Integrations TBD |

### Canonical Category Labels

| Old Label | New Label |
|-----------|-----------|
| "post-MVP" / "Post-MVP" | "Stabilization" (P9-P10) or "Expansion" (P11-P22) |
| "P9-P11" phase range | "P9-P10" (Stabilization) or "P11-P22" (Expansion) |
| "Phase 11: Advanced Integrations" | "Phase 11: WhatsApp Integration" |
| "12 phases" | "23 phases" |
| "252 steps" | "202 (MVP) + 31 (Stabilization) + TBD (Expansion)" |
| "P11 X auto-poster" (ADR-033) | "P13 X Auto Poster" |

### Canonical Dependency Map

| Phase | Depends On |
|-------|-----------|
| P9 | P8 (MVP) |
| P10 | P8 (MVP) |
| P11 | P5 + P8 |
| P12 | P5 + P8 |
| P13 | P5 + P6 + P7 + P8 |
| P14 | P7 + P8 |
| P15 | P5 + P8 |
| P16 | P3 + P5 + P8 |
| P17 | P15 + P8 |
| P18 | P3 + P8 |
| P19 | P3 + P5 + P8 |
| P20 | P5 + P8 |
| P21 | P2 + P8 |
| P22 | P8 |

### Disambiguation Rules (Enforced in All Modified Files)

1. **"Step Phase P9"** or just **"P9"** — implementation step phases (this restructure's domain)
2. **"Governance Phase 3"** or **"Delivery Phase 3"** — Charter/AcceptanceCriteria phases
3. **"SDLC Phase 4"** or **"Loop Phase 4"** — agent loop phases
4. **"Budget Phase 2"** — FinOps storage rollout phases (§4.1)
5. **"Priority P0"** — SRS/TDD/PRD test priority levels

### Out of Scope (Explicitly Excluded)

- BRD Phase 0-5 naming conflict (separate restructure task)
- SDLC loop phase definitions
- Priority labels P0-P5 in SRS/TDD/PRD
- Persona/ADR boilerplate "post-MVP" in 23 ADR files (separate task)
- `stepprompts/StepPrompts.md.bak` (stale backup — not modified)
- `audit-reports/` historical files (not modified — add addendum only if referenced)

---

## 7. Collision Scan

### Shared File Collision Detection

| File | Tasks That Edit It | Collision? | Mitigation |
|------|-------------------|------------|------------|
| `PROGRESS.md` | T1 only | No | Single owner |
| `ADR-033` | T2 only | No | Single owner |
| `CHECKLIST.md` | T3 only | No | Single owner |
| `StepPrompts.md` | T4 only | No | Single owner |
| `IMPLEMENTATION_GUIDE.md` | T5 only | No | Single owner |
| `ADR_Index_v1.0.md` | T6 only | No | Single owner |
| `BRD_v2.0.md` | T7 only | No | Single owner |
| `AcceptanceCriteriaCatalog` | T8 only | No | Single owner |
| `Cost_FinOps_Model_v1.1.md` | T9 only | No | Single owner |
| `docs/README.md` | T10 only | No | Single owner |
| `adr/README.md` | T11 only | No | Single owner |

**Verdict: ZERO shared-writer collisions.** Every file has exactly one owner task. All tasks that are independent at the file level can run in parallel.

### Shared Content Collision Detection

| Content | Used By | Collision? | Mitigation |
|---------|---------|-----------|------------|
| Canonical step counts (P9=12, P10=19) | T1, T3, T4, T5 | Sequential dependency | T3/T4 depend on T1; T5 depends on T3/T4 |
| "23 phases" header count | T4, T5 | Sequential | T5 depends on T4 |
| ADR-034 existence | T6, T11 | Sequential | T11 depends on T6 |
| P11-P22 phase names | T1, T3, T4, T7, T8 | Parallel with scaffold | Each task uses canonical names from Binding Decisions §6 |

---

## 8. Files to Create/Modify

### Files Modified (11)

| # | File | Task | Scope | Lines Changed (est.) |
|---|------|------|-------|---------------------|
| 1 | `PROGRESS.md` | T1 | Major rewrite | ~80 |
| 2 | `adr/ADR-033-browser-automation-obscura.md` | T2 | Targeted fix | ~4 |
| 3 | `CHECKLIST.md` | T3 | Major rewrite | ~200 |
| 4 | `stepprompts/StepPrompts.md` | T4 | Major rewrite | ~300 |
| 5 | `docs/IMPLEMENTATION_GUIDE.md` | T5 | Targeted updates | ~30 |
| 6 | `docs/10-governance/17-ADR_Index_v1.0.md` | T6 | Add ADR entry | ~10 |
| 7 | `docs/00-core/00-BRD_v2.0.md` | T7 | Add section | ~30 |
| 8 | `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` | T8 | Add criteria | ~60 |
| 9 | `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` | T9 | Targeted updates | ~30 |
| 10 | `docs/README.md` | T10 | Minor | ~5 |
| 11 | `adr/README.md` | T11 | Targeted fix | ~5 |

### Files Created (14 evidence + 1 ADR stub)

| # | File | Purpose |
|---|------|---------|
| E1-E11 | `docs/setup-evidence/restructure/verification-T{N}.md` | Per-task verification evidence |
| E12 | `docs/setup-evidence/restructure/cross-file-verification.md` | T12 grep check results |
| E13 | `docs/setup-evidence/restructure/auditor-synthesis.md` | T13 auditor synthesis |

---

## 9. Implementation Design — Per-File Change Specification

### T1: PROGRESS.md

**Sections to modify:**
1. **Header stats** (lines 10-12): Update "11 phases" implied context; add "23 phases (P0-P22)" to metadata
2. **Quick Start** (line 20): Replace `P9-P11 are post-MVP` with `P9-P10 are Stabilization. P11-P22 are Expansion — deferrable under budget pressure.`
3. **Phase Summary table** (lines 36-38): Replace P11 row "Integrations" with P11-P22 rows (12 new rows, each with TBD steps)
4. **P9 section** (lines 329-343): Remove "— Post-MVP" suffix; keep steps intact
5. **P10 section** (lines 345-366): Remove "— Post-MVP" suffix; keep steps intact
6. **P11 section** (lines 368-395): ***DELETE*** entire old P11 section. Replace with P11-P22 sections, each with TBD step count, proper dependency list, phase name, and placeholder `- [ ] **P{N}-001** TBD` entry
7. **Cost Tracking table** (lines 412-414): Replace P11 row with P11-P22 rows (budget TBD)
8. **Cost alert thresholds** (line 417): Replace `defer P9-P11` with `defer P9-P10 or P11-P22`
9. **Dependencies** (line 427): Replace `P9-P11 require P8 (post-MVP)` with `P9-P10 require P8 (Stabilization). P11-P22 require P8 (Expansion).`
10. **Risk table** (line 431): Replace `P9-P11 deferred` with `P9-P10 or P11-P22 deferred`
11. **Timeline table** (lines 452-458): Replace P11 row with P11-P22 rows (TBD); update post-MVP total

### T2: ADR-033

**Lines to modify (4 occurrences):**
- Line 73: `X auto-poster (P11)` → `X auto-poster (P13)`
- Line 80: `X auto-poster (P11)` → `X auto-poster (P13)`
- Line 152: `X auto-poster (P11)` → `X auto-poster (P13)`
- Line 212: `[Post-MVP: X Auto-Poster (P11)](../docs/post-mvp/)` → `[Expansion: X Auto-Poster (P13)](../docs/post-mvp/)`

### T3: CHECKLIST.md

**Sections to modify:**
1. **Budget Tracking table** (lines 36-38): Replace P11 row with P11-P22 rows
2. **Section 11: Phase 9** (lines 708-744): Fix step count `P9-001 through P9-015 (15 steps)` → `P9-001 through P9-012 (12 steps)`. Remove extra steps P9-013 through P9-015. Reconcile step verifications to match PROGRESS.md P9-001 through P9-012.
3. **Section 12: Phase 10** (lines 747-783): Fix step count `P10-001 through P10-020 (20 steps)` → `P10-001 through P10-019 (19 steps)`. Verify step verifications match PROGRESS.md P10-001 through P10-019 (note: P10-019 is MVP Acceptance Gate; CHECKLIST lists P10-020 as final; must be reconciled).
4. **Section 13: Phase 11** (lines 786-823): ***DELETE*** old Section 13 entirely. Replace with Sections 13-24 for P11-P22, each with:
   - Phase header with canonical name and step count (TBD)
   - Prerequisites section
   - Placeholder verification steps
   - Phase Complete Criteria
5. **Section 16: Post-MVP Validation** (line 983): Rename to "Post-MVP & Expansion Validation"
6. **Budget table and cross-references**: Update "Post-MVP" language throughout

### T4: StepPrompts.md

**Sections to modify:**
1. **Header** (lines 10-11): `Total Steps: 252` → `Total Steps: 202 (MVP) + 31 (Stabilization) + TBD (Expansion)`; `Total Phases: 12 (P0-P11)` → `Total Phases: 23 (P0-P22)`
2. **Shared VPS note** (line 28): `P3-P7, P9-P11` → `P3-P7, P9-P22`
3. **Step ID Convention** (line 80): `0-11` → `0-22`
4. **Phase Dependency Graph** (lines 97-119): Rewrite ASCII diagram for P0-P22. Add P11-P22 dependency branches.
5. **Phase 9 section** (lines 7597-7644): Remove "Post-MVP" from header. Keep steps P9-001 to P9-012 intact.
6. **Phase 10 section** (lines 7648-7766): Remove "Post-MVP" from header. Fix step count `18` → `19`. Add P10-019 step if missing. Keep P10-018b gate.
7. **Phase 11 section** (lines 7769-7833): ***DELETE*** entirely. Replace with stubs for P11-P22:
   - Each phase gets: header, goal, step count (TBD), cost, dependencies, placeholder steps, verification, evidence path
   - P13 gets expanded spec: Obscura CDP, S3 queue, LLM captions, 3h heartbeat, Discord notifications, PostgreSQL state
8. **Phase Transition Checklists** (lines 7837-7861): Replace `Before P8 → P9 (Post-MVP Gate)` with `Before P8 → P9 (Stabilization Gate)`. Replace `Before P9 → P10 → P11` with `Before P9 → P10` and `Before P10 → P11 (Expansion Gate)`.
9. **Parallel Work Guide** (lines 7866-7873): Update collision matrix for new phases.
10. **Budget Tracking Summary** (lines 7964-7979): Replace P11 row with P11-P22 rows.
11. **MVP Acceptance Gate** (line 7994): Replace `Phase 11 (Post-MVP)` with `Expansion phases (P11-P22)`

### T5: IMPLEMENTATION_GUIDE.md

**Sections to modify:**
1. **Line 3**: `252 steps across 12 phases (P0-P11)` → `202 MVP + 31 Stabilization + TBD Expansion steps across 23 phases (P0-P22)`
2. **Line 13**: `12 phases (P0-P11) with 252 atomic steps` → `23 phases (P0-P22) with 202 MVP + 31 Stabilization + TBD Expansion steps`
3. **Phase Overview table** (lines 42-44): Replace P11 row with P11-P22 rows
4. **Line 254**: `P9-P11 are post-MVP and deferrable` → `P9-P10 (Stabilization) and P11-P22 (Expansion) are deferrable under budget pressure`
5. **Evidence directory** (line 170): `0-11` → `0-22`

### T6: ADR_Index_v1.0.md

**Changes:**
1. Update `adr_count: 33` → `adr_count: 34` in frontmatter
2. Update line 17: "first 33 technical-core ADRs" → "first 34 technical-core ADRs"
3. Add ADR-034 to ADR Register table (after ADR-033 row)
4. Add ADR-034 to Canonical Decision Map if applicable
5. Remove ADR-034 from Backlog for Future ADRs (lines 115)
6. Add ADR-034 entry:

```markdown
| ADR-034 | Post-MVP Phase Restructure — P0-P11 → P0-P22 | Accepted | MEDIUM | phase, restructure, roadmap | [`ADR-034-post-mvp-phase-restructure.md`](adr/ADR-034-post-mvp-phase-restructure.md) |
```

**Note:** Since the actual ADR-034 markdown file doesn't exist yet, T6 also creates a minimal ADR-034 stub at `adr/ADR-034-post-mvp-phase-restructure.md` or references the batch plan as evidence.

### T7: BRD_v2.0.md

**Changes:**
1. Add new section after §5 (Phased Delivery Plan) or within §5:
   - Section title: `5.6 Expansion Phases (P11-P22) — Post-Stabilization`
   - Brief overview paragraph explaining expansion follows stabilization (P9-P10)
   - Table with all 12 expansion phases: number, name, brief description, dependencies
2. Update "post-MVP" references in Phase 2 (line 186, 365) and Phase 4 (lines 198, 256, 395, 451) to use "Expansion (P11-P22)" or "Stabilization (P9-P10)" as appropriate
3. **DO NOT TOUCH** Phase 0-5 naming (out of scope)

### T8: AcceptanceCriteriaCatalog_v1.0.md

**Changes:**
1. Add AC-PHASE-009: P9 Financial Tracking Exit Gate
2. Add AC-PHASE-010: P10 Production Hardening Exit Gate
3. Add AC-PHASE-011: P11-P22 Expansion Phase Entry Gate
4. Update AC-PHASE-008 description to clarify it applies to P11-P22 expansion (not generic "Post-MVP")
5. Extend Phase Gate Checklist §12 to include P9-P10 stabilization gates and P11-P22 expansion gate
6. Update all "Post-MVP" references in Phase column to "Stabilization" or "Expansion" as appropriate
7. Add AC IDs for expansion-specific criteria as TBD placeholders

### T9: Cost_FinOps_Model_v1.1.md

**Changes:**
1. Add disambiguation note at §4.1: "Budget Phase 1/2/3" are storage rollout phases, NOT delivery step phases P1/P2/P3
2. Add cost tracking rows for P11-P22 in budget tables (TBD costs)
3. Update §10 "Guinevere-Specific FinOps Constraints" to reference P11-P22 expansion
4. Add cost governance principle: each expansion phase must fit within budget envelope
5. Update line 108: "Post-MVP only" → "Stabilization/Expansion only"
6. Add note: P13 X Auto Poster may incur additional costs (Obscura CDP runtime, S3 storage, LLM caption generation)

### T10: docs/README.md

**Changes:**
1. If any phase descriptions changed in document registries, update accordingly
2. Review for stale phase references — likely minimal changes needed
3. Update "total_dokumen" if new ADR-034 file created

### T11: adr/README.md

**Changes:**
1. Line 10: `adr_count: 33` → `adr_count: 34`
2. Line 20: `first 25 technical-core ADRs` → `first 34 technical-core ADRs`
3. Add ADR-034 to Backlog for Future ADRs list → remove from backlog, add to ADR Register if T6 created it
4. Sync with ADR_Index changes from T6

---

## 10. Token/Secret Handling

N/A — This is a documentation-only task. No secrets, API keys, tokens, or credentials are involved. All modified files are plain markdown documentation. If ADR-034 references any architecture decisions involving credentials, those references should use ADR numbers, not actual values.

---

## 11. Evidence Paths

All evidence files go under `docs/setup-evidence/restructure/`:

| Task | Evidence File |
|------|--------------|
| T1 | `docs/setup-evidence/restructure/verification-T1-progress.md` |
| T2 | `docs/setup-evidence/restructure/verification-T2-adr033.md` |
| T3 | `docs/setup-evidence/restructure/verification-T3-checklist.md` |
| T4 | `docs/setup-evidence/restructure/verification-T4-stepprompts.md` |
| T5 | `docs/setup-evidence/restructure/verification-T5-impl-guide.md` |
| T6 | `docs/setup-evidence/restructure/verification-T6-adr-index.md` |
| T7 | `docs/setup-evidence/restructure/verification-T7-brd.md` |
| T8 | `docs/setup-evidence/restructure/verification-T8-acceptance.md` |
| T9 | `docs/setup-evidence/restructure/verification-T9-finops.md` |
| T10 | `docs/setup-evidence/restructure/verification-T10-docs-readme.md` |
| T11 | `docs/setup-evidence/restructure/verification-T11-adr-readme.md` |
| T12 | `docs/setup-evidence/restructure/cross-file-verification.md` |
| T13 | `docs/setup-evidence/restructure/auditor-synthesis.md` |

Each per-task evidence file must follow the 12-section evidence schema from AGENTS.md §11.

---

## 12. Auditor Matrix

| Auditor | Checks | Surfaces | Severity Threshold |
|---------|--------|----------|-------------------|
| Oracle — Phase Structure | All 23 phases present in all tracker files; canonical counts match; no old phase names | PROGRESS.md, CHECKLIST.md, StepPrompts.md | FAIL on any mismatch |
| Oracle — Cross-Reference | P11-P22 refs consistent across all 11 files; old "P11 Advanced Integrations" absent; P13 X Auto Poster present | All 11 modified files | FAIL on stale ref |
| Oracle — Governance | ADR-034 properly registered; AcceptanceCriteria gates valid; FinOps disambiguation present | ADR_Index, AcceptanceCriteria, FinOps | NEEDS REVIEW on ambiguity |
| Security — Safety Boundary | No safety-affecting changes; no persona drift; no consent changes | Persona references in modified files | FAIL on any safety change |
| review — Text Quality | Markdown syntax valid; table alignment correct; no broken links | All 11 modified files | NEEDS REVIEW on formatting issues |

Each auditor writes a markdown report to `docs/setup-evidence/restructure/auditor-{name}.md`.

---

## 13. Rollback Plan

### Git-Based Rollback (Preferred)

```bash
git checkout -- PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md
git checkout -- docs/IMPLEMENTATION_GUIDE.md
git checkout -- docs/10-governance/17-ADR_Index_v1.0.md
git checkout -- docs/00-core/00-BRD_v2.0.md
git checkout -- docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
git checkout -- docs/70-finops/70-Cost_FinOps_Model_v1.1.md
git checkout -- docs/README.md adr/README.md
git checkout -- adr/ADR-033-browser-automation-obscura.md
```

### If ADR-034 file was created

```bash
rm adr/ADR-034-post-mvp-phase-restructure.md
```

### Pre-Restructure Snapshot

Before any changes, create a git commit of current state:

```bash
git add -A
git commit -m "chore: pre-restructure snapshot before P0-P11 → P0-P22 phase restructure"
```

This provides a single revert point if full rollback is needed.

---

## 14. Tracker Sync Plan

The three tracker files (PROGRESS.md, CHECKLIST.md, StepPrompts.md) must maintain consistency. Strategy:

1. **T1 (PROGRESS.md)** runs first — produces canonical phase names, step counts, dependencies, costs
2. **T3 (CHECKLIST.md)** reads T1 output — copies canonical counts, creates verification sections matching canonical step lists
3. **T4 (StepPrompts.md)** reads T1 output — copies canonical phase structure, creates step prompt stubs matching T1
4. **T12 (verification)** cross-checks all three:
   - Phase names match across all three files
   - Step count claims match across all three files (within TBD tolerance)
   - Dependency lists match
   - Cost claims match

Sync check commands:
```bash
# Extract phase names from all three files and diff
grep -oP 'P\d+.*?(?= \|)' PROGRESS.md | sort > /tmp/progress-phases.txt
grep -oP 'Phase \d+:' CHECKLIST.md | sort > /tmp/checklist-phases.txt
grep -oP 'Phase \d+:' stepprompts/StepPrompts.md | sort > /tmp/stepprompts-phases.txt
diff /tmp/progress-phases.txt /tmp/checklist-phases.txt
diff /tmp/progress-phases.txt /tmp/stepprompts-phases.txt
```

---

## 15. Caveats

1. **BRD Phase 0-5 naming conflict**: Explicitly OUT OF SCOPE. The BRD uses different phase names than Charter/AcceptanceCriteria. This is a separate restructure task (Faiz confirmed).
2. **ADR boilerplate**: 23 ADR files contain identical "wearable integrations post-MVP" boilerplate in their status lines. Updating these is a separate bulk-replace task. Only ADR-033 (which has specific P11→P13 refs) is in scope.
3. **audit-reports/**: Historical audit reports reference "P9-P11", "12 phases", "252 steps". These are NOT modified — they are historical records. A future task may add addenda.
4. **StepPrompts.md.bak**: The backup file contains stale P9-P11 references. It is NOT modified — it's a historical backup.
5. **TBD step counts**: P11-P22 step counts are TBD. This is intentional. Detailed step planning for expansion phases is a separate future task.
6. **P13 X Auto Poster spec**: Included as described in the research — Obscura CDP, S3 queue, LLM captions, 3h heartbeat, Discord notifications, PostgreSQL state. Actual step decomposition is TBD.
7. **P20 Self-Improvement Loop**: Mentioned in BRD Phase 5 as "autonomous skill creation". No detailed spec exists yet — placeholder only.
8. **P21 Voice Interface**: No spec exists — placeholder only.
9. **P22 Additional Integrations**: Catch-all phase — placeholder only.
10. **FinOps "Phase 1/2/3"**: These are budget/storage rollout phases, NOT delivery step phases. They must be renamed to "Budget Phase 1/2/3" in the FinOps model to avoid collision. This is a targeted change within §4.1 only.

---

## 16. Execution Checklist

### Pre-Flight (Before Any Task)

- [ ] Read this batch plan completely
- [ ] Read all 5 research reports in `research-reports/restructure/`
- [ ] Read all 11 target files (current state verified above)
- [ ] Verify no uncommitted changes in any target file: `git status`
- [ ] Create pre-restructure git commit snapshot
- [ ] Confirm `docs/setup-evidence/restructure/` directory exists

### Wave 1 — Fire 6 Tasks in Parallel

- [ ] **T1**: PROGRESS.md restructure → `verification-T1-progress.md`
- [ ] **T2**: ADR-033 fix → `verification-T2-adr033.md`
- [ ] **T6**: ADR_Index update → `verification-T6-adr-index.md`
- [ ] **T7**: BRD expansion section → `verification-T7-brd.md`
- [ ] **T8**: AcceptanceCriteria gates → `verification-T8-acceptance.md`
- [ ] **T9**: FinOps updates → `verification-T9-finops.md`

### Wave 2 — After Wave 1 Completes

- [ ] **T3**: CHECKLIST.md restructure → `verification-T3-checklist.md`
- [ ] **T4**: StepPrompts.md restructure → `verification-T4-stepprompts.md`
- [ ] **T11**: adr/README.md update → `verification-T11-adr-readme.md`

### Wave 3 — After Wave 2 Completes

- [ ] **T5**: IMPLEMENTATION_GUIDE.md → `verification-T5-impl-guide.md`
- [ ] **T10**: docs/README.md → `verification-T10-docs-readme.md`

### Wave 4 — After All Tasks Complete

- [ ] **T12**: Cross-file verification → `cross-file-verification.md`
  - Run all 9 grep checks
  - Run sync check across tracker trio
  - All checks must PASS before advancing

### Wave 5 — After T12 PASS

- [ ] **T13**: Auditor orchestrator → spawn 5 parallel auditors
  - Read all auditor reports
  - Fix any NEEDS REVIEW or FAIL findings
  - Re-audit until PASS or accepted false-positive

### Post-Flight

- [ ] All 11 evidence files exist and are complete
- [ ] All 5 auditor reports exist with PASS verdicts
- [ ] Git diff reviewed for unintended changes
- [ ] Report final status to Faiz

---

## 17. Per-Step Verification Scaffolds

### Scaffold for T1: PROGRESS.md

**Expected Files:**
- `PROGRESS.md` (modified)
- `docs/setup-evidence/restructure/verification-T1-progress.md` (created)

**Forbidden Patterns (grep MUST return 0):**
```bash
grep -n "P11.*Advanced Integration" PROGRESS.md
grep -n "P11.*Integrations" PROGRESS.md         # old name (case insensitive)
grep -n "post-MVP" PROGRESS.md                   # in P9/P10/P11 sections
grep -n "P9-P11" PROGRESS.md                     # old range
grep -n "P9.*15 steps\|P10.*20 steps" PROGRESS.md # wrong counts
```

**Required Patterns (grep MUST return matches):**
```bash
grep -n "P11.*WhatsApp" PROGRESS.md              # new name
grep -n "P13.*X Auto Poster" PROGRESS.md         # new phase
grep -n "P9.*12 steps\|P9.*12\b" PROGRESS.md     # canonical P9 count
grep -n "P10.*19 steps\|P10.*19\b" PROGRESS.md   # canonical P10 count
grep -n "P11-P22\|P11-P22" PROGRESS.md           # new expansion range
grep -n "Stabilization" PROGRESS.md              # new category label
grep -n "Expansion" PROGRESS.md                  # new category label
```

**Required Commands:**
```bash
# Verify P22 entry exists
grep -c "P22.*Additional" PROGRESS.md  # expected: >=1

# Count phase entries in Phase Summary table
grep -c "^| P[0-9]" PROGRESS.md        # expected: >=23

# Verify no orphaned P11-0xx step IDs (old P11 steps)
grep -c "P11-0[0-9][0-9]" PROGRESS.md  # expected: 0 (old P11 steps removed)
```

**Hard Rejection Criteria:**
- Any `post-MVP` string in P9/P10/P11-P22 sections = FAIL
- `P11.*Advanced Integration` found = FAIL
- `P9-P11` old range found in tracker content = FAIL
- P11 section heading still says "Integrations" = FAIL
- P9 step count != 12 = FAIL
- P10 step count != 19 = FAIL
- Fewer than 23 phases in summary table = FAIL

### Scaffold for T2: ADR-033

**Expected Files:**
- `adr/ADR-033-browser-automation-obscura.md` (modified)
- `docs/setup-evidence/restructure/verification-T2-adr033.md` (created)

**Forbidden Patterns:**
```bash
grep -n "P11.*auto.poster\|X auto-poster (P11)" adr/ADR-033-browser-automation-obscura.md
```

**Required Patterns:**
```bash
grep -n "P13.*auto.poster\|X auto-poster (P13)" adr/ADR-033-browser-automation-obscura.md
grep -c "P13" adr/ADR-033-browser-automation-obscura.md  # expected: >=4
```

**Hard Rejection Criteria:**
- Any remaining `P11` reference to X auto-poster = FAIL

### Scaffold for T3: CHECKLIST.md

**Expected Files:**
- `CHECKLIST.md` (modified)
- `docs/setup-evidence/restructure/verification-T3-checklist.md` (created)

**Forbidden Patterns:**
```bash
grep -n "P11.*Advanced Integration" CHECKLIST.md
grep -n "P9-015\|P10-020" CHECKLIST.md             # extra steps
grep -n "P9-001 through P9-015" CHECKLIST.md        # wrong range
grep -n "P10-001 through P10-020" CHECKLIST.md      # wrong range
grep -n "13\. Phase 11:" CHECKLIST.md               # old section 13
```

**Required Patterns:**
```bash
grep -n "P9-001 through P9-012" CHECKLIST.md        # canonical range
grep -n "P10-001 through P10-019" CHECKLIST.md      # canonical range
grep -n "Phase 11: WhatsApp" CHECKLIST.md           # new name
grep -n "Phase 13: X Auto Poster" CHECKLIST.md      # new phase section
grep -n "Phase 22:" CHECKLIST.md                    # last new phase
```

**Required Commands:**
```bash
# Count new section headers for P11-P22 (should be 12 new sections)
grep -c "^## [0-9][0-9]\. Phase 1[1-9]:\|^## [0-9][0-9]\. Phase 2[0-2]:" CHECKLIST.md  # expected: 12
```

**Hard Rejection Criteria:**
- P9 step count range shows "through P9-015" = FAIL
- P10 step count range shows "through P10-020" = FAIL
- Old Section 13 "Phase 11: Advanced Integrations" remains = FAIL
- Fewer than 12 new P11-P22 sections = FAIL
- P9 verification items reference P9-013 through P9-015 = FAIL

### Scaffold for T4: StepPrompts.md

**Expected Files:**
- `stepprompts/StepPrompts.md` (modified)
- `docs/setup-evidence/restructure/verification-T4-stepprompts.md` (created)

**Forbidden Patterns:**
```bash
grep -n "Total Phases: 12" stepprompts/StepPrompts.md
grep -n "Total Steps: 252" stepprompts/StepPrompts.md
grep -n "12 phases" stepprompts/StepPrompts.md
grep -n "Phase 11: Advanced Integrations" stepprompts/StepPrompts.md
grep -n "P11-001.*P11-025" stepprompts/StepPrompts.md
grep -n "P9-P11" stepprompts/StepPrompts.md         # old range
grep -n "post-MVP" stepprompts/StepPrompts.md        # in phase headers
```

**Required Patterns:**
```bash
grep -n "Total Phases: 23" stepprompts/StepPrompts.md
grep -n "Phase 11: WhatsApp" stepprompts/StepPrompts.md
grep -n "Phase 13: X Auto Poster" stepprompts/StepPrompts.md
grep -n "P10-019" stepprompts/StepPrompts.md         # new canonical last step
grep -n "Stabilization" stepprompts/StepPrompts.md
grep -n "Expansion" stepprompts/StepPrompts.md
grep -n "Obscura CDP" stepprompts/StepPrompts.md     # P13 spec detail
```

**Hard Rejection Criteria:**
- "Total Phases: 12" or "Total Steps: 252" still present = FAIL
- "Phase 11: Advanced Integrations" heading remains = FAIL
- P11-001 through P11-025 old steps still listed = FAIL
- P13 section missing Obscura CDP spec = FAIL
- P10 step count shows 18 instead of 19 = FAIL

### Scaffold for T5: IMPLEMENTATION_GUIDE.md

**Expected Files:**
- `docs/IMPLEMENTATION_GUIDE.md` (modified)
- `docs/setup-evidence/restructure/verification-T5-impl-guide.md` (created)

**Forbidden Patterns:**
```bash
grep -n "252 steps" docs/IMPLEMENTATION_GUIDE.md
grep -n "12 phases" docs/IMPLEMENTATION_GUIDE.md
grep -n "P9-P11 are post-MVP" docs/IMPLEMENTATION_GUIDE.md
```

**Required Patterns:**
```bash
grep -n "23 phases" docs/IMPLEMENTATION_GUIDE.md
grep -n "P13.*X Auto Poster\|P11.*WhatsApp" docs/IMPLEMENTATION_GUIDE.md
grep -n "Stabilization" docs/IMPLEMENTATION_GUIDE.md
grep -n "Expansion" docs/IMPLEMENTATION_GUIDE.md
```

**Hard Rejection Criteria:**
- "252 steps" or "12 phases" still present = FAIL
- "P9-P11 are post-MVP" still present = FAIL
- P11 row shows "Integrations" instead of "WhatsApp" = FAIL
- Phase overview table has fewer than 23 rows = FAIL

### Scaffold for T6: ADR_Index_v1.0.md

**Expected Files:**
- `docs/10-governance/17-ADR_Index_v1.0.md` (modified)
- `docs/setup-evidence/restructure/verification-T6-adr-index.md` (created)

**Forbidden Patterns:**
```bash
grep -n "adr_count: 33" docs/10-governance/17-ADR_Index_v1.0.md
```

**Required Patterns:**
```bash
grep -n "adr_count: 34" docs/10-governance/17-ADR_Index_v1.0.md
grep -n "ADR-034" docs/10-governance/17-ADR_Index_v1.0.md
grep -n "Phase Restructure\|phase.restructure\|P0-P22" docs/10-governance/17-ADR_Index_v1.0.md
```

**Hard Rejection Criteria:**
- ADR-034 not present in ADR Register table = FAIL
- ADR-034 still listed in Backlog for Future ADRs = FAIL

### Scaffold for T7: BRD_v2.0.md

**Expected Files:**
- `docs/00-core/00-BRD_v2.0.md` (modified)
- `docs/setup-evidence/restructure/verification-T7-brd.md` (created)

**Forbidden Patterns:**
```bash
grep -n "post-MVP.*wearable\|wearable.*post-MVP" docs/00-core/00-BRD_v2.0.md
```

**Required Patterns:**
```bash
grep -n "P11-P22\|Expansion Phase\|Expansion (P11-P22)" docs/00-core/00-BRD_v2.0.md
grep -n "WhatsApp\|X Auto Poster\|Wearable" docs/00-core/00-BRD_v2.0.md
```

**Hard Rejection Criteria:**
- No expansion phase overview section added = FAIL
- Phase 0-5 names modified (out of scope) = FAIL

### Scaffold for T8: AcceptanceCriteriaCatalog_v1.0.md

**Expected Files:**
- `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` (modified)
- `docs/setup-evidence/restructure/verification-T8-acceptance.md` (created)

**Forbidden Patterns:**
```bash
grep -n "Post-MVP expansion" docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
```

**Required Patterns:**
```bash
grep -n "AC-PHASE-009\|AC-PHASE-010\|AC-PHASE-011" docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
grep -n "Stabilization\|Expansion" docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
```

**Hard Rejection Criteria:**
- No P9-P10 exit gate criteria (AC-PHASE-009, AC-PHASE-010) added = FAIL
- No P11-P22 entry gate criteria (AC-PHASE-011) added = FAIL
- AC-PHASE-008 still says "Post-MVP expansion" without clarification = NEEDS REVIEW

### Scaffold for T9: Cost_FinOps_Model_v1.1.md

**Expected Files:**
- `docs/70-finops/70-Cost_FinOps_Model_v1.1.md` (modified)
- `docs/setup-evidence/restructure/verification-T9-finops.md` (created)

**Forbidden Patterns:**
- (None catastrophic — this is additive)

**Required Patterns:**
```bash
grep -n "Budget Phase\|storage rollout phase" docs/70-finops/70-Cost_FinOps_Model_v1.1.md
grep -n "P11-P22\|Expansion" docs/70-finops/70-Cost_FinOps_Model_v1.1.md
grep -n "Stabilization" docs/70-finops/70-Cost_FinOps_Model_v1.1.md
```

**Hard Rejection Criteria:**
- No disambiguation between Budget Phase 1/2/3 and delivery Step Phases = NEEDS REVIEW
- No P11-P22 cost tracking rows = NEEDS REVIEW

### Scaffold for T10: docs/README.md

**Expected Files:**
- `docs/README.md` (modified)
- `docs/setup-evidence/restructure/verification-T10-docs-readme.md` (created)

**Required Commands:**
```bash
# Verify no broken internal links
grep -oP '\[.*?\]\(.*?\.md\)' docs/README.md | while read link; do echo "$link"; done
```

**Hard Rejection Criteria:**
- Broken links introduced = FAIL
- Stale "post-MVP" references in navigation = NEEDS REVIEW

### Scaffold for T11: adr/README.md

**Expected Files:**
- `adr/README.md` (modified)
- `docs/setup-evidence/restructure/verification-T11-adr-readme.md` (created)

**Forbidden Patterns:**
```bash
grep -n "first 25" adr/README.md
grep -n "adr_count: 33" adr/README.md
```

**Required Patterns:**
```bash
grep -n "first 34" adr/README.md
grep -n "adr_count: 34" adr/README.md
grep -n "ADR-034" adr/README.md
```

**Hard Rejection Criteria:**
- "first 25" still present = FAIL
- ADR-034 not listed = FAIL

### Scaffold for T12: Cross-File Verification

**Expected Files:**
- `docs/setup-evidence/restructure/cross-file-verification.md` (created)

**Required Commands (9 Grep Checks — ALL MUST PASS):**

```bash
# Check 1: No "P11.*Advanced Integration" in priority-1 files
grep -rn "P11.*Advanced Integration\|Advanced Integrations.*P11" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md docs/IMPLEMENTATION_GUIDE.md
# Expected: 0 matches

# Check 2: No "P9.*P10.*P11" old triple pattern
grep -rn "P9.*P10.*P11\|P9-P11" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md docs/IMPLEMENTATION_GUIDE.md
# Expected: 0 matches (except in caveats/disclaimer sections)

# Check 3: P13 X Auto Poster references present
grep -rn "P13.*X Auto Poster\|P13.*auto.poster\|P13.*Auto Poster" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md
# Expected: >=3 matches total

# Check 4: No "252 steps\|12 phases" stale counts
grep -rn "252 steps\|12 phases" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md docs/IMPLEMENTATION_GUIDE.md
# Expected: 0 matches

# Check 5: "P9-P11" old range absent in priority-1
grep -rn "P9-P11" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md docs/IMPLEMENTATION_GUIDE.md
# Expected: 0 matches (except explicit caveats)

# Check 6: Canonical step counts present
grep -rn "P9.*12 steps\|P10.*19 steps" PROGRESS.md CHECKLIST.md
# Expected: >=2 matches each

# Check 7: "P11-P22" expansion range present
grep -rn "P11-P22\|P11.*P22" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md
# Expected: >=3 matches total

# Check 8: ADR-034 referenced
grep -rn "ADR-034" docs/10-governance/17-ADR_Index_v1.0.md adr/README.md
# Expected: >=2 matches

# Check 9: Cross-reference: all P11-P22 phases in all three tracker files
for phase in P11 P12 P13 P14 P15 P16 P17 P18 P19 P20 P21 P22; do
  echo "Checking $phase..."
  grep -c "$phase" PROGRESS.md CHECKLIST.md stepprompts/StepPrompts.md
done
# Expected: Each phase appears in all three files
```

**Hard Rejection Criteria:**
- Any Check 1-9 returns unexpected results = FAIL
- Any P11-P22 phase missing from any tracker file = FAIL
- "252 steps" or "12 phases" still present in any priority-1 file = FAIL

---

## 18. Commit Strategy

### Atomic Commits (One Per Wave)

```bash
# Wave 1 commit (6 files)
git add PROGRESS.md \
        adr/ADR-033-browser-automation-obscura.md \
        docs/10-governance/17-ADR_Index_v1.0.md \
        docs/00-core/00-BRD_v2.0.md \
        docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md \
        docs/70-finops/70-Cost_FinOps_Model_v1.1.md
git commit -m "docs: restructure P0-P11 -> P0-P22 — Wave 1 (PROGRESS, ADR-033, governance docs)"

# Wave 2 commit (3 files)
git add CHECKLIST.md stepprompts/StepPrompts.md adr/README.md
git commit -m "docs: restructure P0-P11 -> P0-P22 — Wave 2 (CHECKLIST, StepPrompts, adr/README)"

# Wave 3 commit (2 files)
git add docs/IMPLEMENTATION_GUIDE.md docs/README.md
git commit -m "docs: restructure P0-P11 -> P0-P22 — Wave 3 (IMPLEMENTATION_GUIDE, docs/README)"

# Wave 4-5 commit (evidence files)
git add docs/setup-evidence/restructure/
git commit -m "docs: restructure P0-P11 -> P0-P22 — evidence and verification"
```

If a wave fails verification, fix within that wave before committing. Do not commit failed changes.

---

## 19. TDD-Oriented Planning

### Test-First Verification Strategy

1. **Define expected state** (scaffold grep patterns) BEFORE editing
2. **Edit files** per implementation design
3. **Run scaffold commands** after each file edit
4. **FAIL → fix → re-run** until PASS
5. **Commit only after PASS**

This ensures every file change is verified against machine-checkable criteria before being considered complete.

---

## TODO List (ADD THESE)

### Wave 1 (Start Immediately — No Dependencies)

- [ ] **T1. PROGRESS.md restructure**
  - What: Rewrite P9/P10/P11 sections → P9(12 steps) + P10(19 steps) + P11-P22(12 phases, TBD steps). Update Phase Summary table, Cost Tracking, Timeline, Quick Start, Dependencies, Risk table. Replace "post-MVP" → "Stabilization" (P9-P10) / "Expansion" (P11-P22).
  - Depends: None
  - Blocks: T3, T4
  - Category: `implementation`
  - Skills: [`ocs-markdown-autofix`]
  - QA: Run scaffold T1 grep checks; all forbidden patterns = 0; phase count >= 23

- [ ] **T2. ADR-033 P11→P13 fix**
  - What: Replace all 4 occurrences of "X auto-poster (P11)" with "X auto-poster (P13)" in `adr/ADR-033-browser-automation-obscura.md`. Update link text on line 212.
  - Depends: None
  - Blocks: None
  - Category: `quick`
  - Skills: []
  - QA: `grep -c "P13" adr/ADR-033-browser-automation-obscura.md` → >=4; `grep "P11.*auto"` → 0

- [ ] **T6. ADR_Index_v1.0 add ADR-034**
  - What: Update `adr_count: 34`. Add ADR-034 row to ADR Register table. Remove ADR-034 from backlog. Create minimal ADR-034 stub file if needed.
  - Depends: None
  - Blocks: T11
  - Category: `writing`
  - Skills: []
  - QA: `grep -c "ADR-034" docs/10-governance/17-ADR_Index_v1.0.md` → >=2; `grep "adr_count: 34"` → 1

- [ ] **T7. BRD_v2.0 add expansion section**
  - What: Add §5.6 "Expansion Phases (P11-P22)" with overview table of 12 phases. Update "post-MVP" refs to "Stabilization/Expansion". DO NOT modify Phase 0-5 names.
  - Depends: None
  - Blocks: None
  - Category: `writing`
  - Skills: []
  - QA: `grep -c "P11-P22\|Expansion Phase" docs/00-core/00-BRD_v2.0.md` → >=2; Phase 0-5 names unchanged

- [ ] **T8. AcceptanceCriteria add P9-P10 exit gates + P11-P22 entry criteria**
  - What: Add AC-PHASE-009 (P9 exit), AC-PHASE-010 (P10 exit), AC-PHASE-011 (P11-P22 entry). Update AC-PHASE-008 description. Extend Phase Gate Checklist §12.
  - Depends: None
  - Blocks: None
  - Category: `writing`
  - Skills: []
  - QA: `grep -c "AC-PHASE-009\|AC-PHASE-010\|AC-PHASE-011" docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` → >=3

- [ ] **T9. FinOps Model update cost tracking + disambiguation**
  - What: Add disambiguation note at §4.1 (Budget Phase vs Step Phase). Add P11-P22 cost rows. Update §10 constraints. Add P13 cost note. Change "Post-MVP only" → "Stabilization/Expansion only".
  - Depends: None
  - Blocks: None
  - Category: `writing`
  - Skills: []
  - QA: `grep -c "Budget Phase\|storage rollout" docs/70-finops/70-Cost_FinOps_Model_v1.1.md` → >=1; `grep -c "P11-P22"` → >=1

### Wave 2 (After Wave 1 Completes)

- [ ] **T3. CHECKLIST.md restructure**
  - What: Fix P9 step count 15→12. Fix P10 step count 20→19. Delete Section 13 "Advanced Integrations". Add Sections 13-24 for P11-P22 with placeholder verifications. Reconcile step verification items. Update budget table.
  - Depends: T1
  - Blocks: T5
  - Category: `implementation`
  - Skills: [`ocs-markdown-autofix`]
  - QA: Run scaffold T3 grep checks; P9 range "through P9-012"; P10 range "through P10-019"; 12 new P11-P22 sections

- [ ] **T4. StepPrompts.md restructure**
  - What: Update header (12→23 phases, 252→202+31+TBD steps). Rewrite Phase 11 section → P11-P22 stubs. Update dependency graph ASCII. Fix P10 count 18→19. Update transition checklists, budget table, parallel guide, acceptance gate.
  - Depends: T1
  - Blocks: T5
  - Category: `implementation`
  - Skills: [`ocs-markdown-autofix`]
  - QA: Run scaffold T4 grep checks; "Total Phases: 23"; "Phase 11: WhatsApp"; no old P11-001..P11-025

- [ ] **T11. adr/README.md update**
  - What: Fix "first 25" → "first 34". Update `adr_count: 34`. Add ADR-034 to register if not in backlog. Sync with T6 output.
  - Depends: T6
  - Blocks: None
  - Category: `quick`
  - Skills: []
  - QA: `grep "first 25" adr/README.md` → 0; `grep "first 34"` → >=1; `grep "ADR-034"` → >=1

### Wave 3 (After Wave 2 Completes)

- [ ] **T5. IMPLEMENTATION_GUIDE.md update**
  - What: Update "252 steps across 12 phases" → new counts. Replace phase table P11 row with P11-P22 rows. Update "P9-P11 are post-MVP" → Stabilization/Expansion language. Fix evidence dir range 0-11→0-22.
  - Depends: T3, T4
  - Blocks: T10
  - Category: `implementation`
  - Skills: []
  - QA: Run scaffold T5 grep checks; "23 phases"; no "252 steps"; no "12 phases"

- [ ] **T10. docs/README.md minor updates**
  - What: Update document index references if any phase descriptions changed. Verify no broken links. Update total_dokumen if ADR-034 created.
  - Depends: T5
  - Blocks: None
  - Category: `writing`
  - Skills: []
  - QA: No broken links; no stale phase refs

### Wave 4 (After All Tasks Complete)

- [ ] **T12. Cross-file verification**
  - What: Run all 9 grep checks from scaffold T12 against all 11 modified files. Run tracker trio sync check. Document all results.
  - Depends: T1-T11
  - Blocks: T13
  - Category: `testing`
  - Skills: []
  - QA: All 9 grep checks PASS

### Wave 5 (After T12 PASS)

- [ ] **T13. Auditor orchestrator**
  - What: Spawn 5 parallel auditors: Oracle (Phase Structure), Oracle (Cross-Reference), Oracle (Governance), Security (Safety Boundary), review (Text Quality). Read all reports. Fix findings. Re-audit until PASS.
  - Depends: T12
  - Blocks: None
  - Category: `review`
  - Skills: [`review-work`]
  - QA: All 5 auditor reports = PASS; auditor-synthesis.md documents final verdicts

## Execution Instructions

1. **Pre-flight**: `git add -A && git commit -m "chore: pre-restructure snapshot"`

2. **Wave 1**: Fire 6 tasks in parallel
   ```
   task(category="implementation", load_skills=["ocs-markdown-autofix"], run_in_background=false, prompt="T1: PROGRESS.md restructure...")
   task(category="quick", load_skills=[], run_in_background=false, prompt="T2: ADR-033 P11→P13 fix...")
   task(category="writing", load_skills=[], run_in_background=false, prompt="T6: ADR_Index add ADR-034...")
   task(category="writing", load_skills=[], run_in_background=false, prompt="T7: BRD add expansion section...")
   task(category="writing", load_skills=[], run_in_background=false, prompt="T8: AcceptanceCriteria add gates...")
   task(category="writing", load_skills=[], run_in_background=false, prompt="T9: FinOps update + disambiguation...")
   ```

3. **Wave 2**: After Wave 1, fire 3 tasks in parallel
   ```
   task(category="implementation", load_skills=["ocs-markdown-autofix"], ...)
   task(category="implementation", load_skills=["ocs-markdown-autofix"], ...)
   task(category="quick", ...)
   ```

4. **Wave 3**: After Wave 2, fire 2 tasks sequential
   ```
   task(category="implementation", ...)  # T5 first
   task(category="writing", ...)          # T10 after T5
   ```

5. **Wave 4**: After Wave 3, run verification
   ```
   task(category="testing", ...)  # T12
   ```

6. **Wave 5**: After T12 PASS, spawn auditors
   ```
   task(category="review", load_skills=["review-work"], ...)
   ```

---

*End of Batch Plan — BP-PHASE-RESTRUCTURE-001*