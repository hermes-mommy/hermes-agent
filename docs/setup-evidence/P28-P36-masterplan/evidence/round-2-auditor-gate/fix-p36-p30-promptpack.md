---
title: "Round 2 Auditor Gate — Fix P36 Templates, P30 Files, Prompt-Pack Body"
status: "Complete"
date: "2026-06-28"
author: "Guinevere (executor)"
triggered_by: "Auditor 03 + Auditor 07 findings"
scope: "P36 templates, P30 files, prompt-pack body annotations"
---

# Fix Report: P36 Templates, P30 Files, Prompt-Pack Body

> Fixes for auditor findings 03 and 07. All changes are annotation/renaming only — no substantive content rewrites.

## 1. What Was Done

Three groups of fixes applied:

- **Group 1 (P36 Templates)**: Replaced all "soak" references with "permanent operation validation" terminology (per brainstorm decision 2026-06-28 — NO SOAK TEST). Added ADR-062/066 disclaimers to HARD STOP and consent references in verification and evidence templates.
- **Group 2 (P30 Files)**: Added file-level ADR-062/067 disclaimer to all 4 P30 files (plan.md, README.md, evidence-template.md, verification-template.md). Added body-level ADR annotations to evidence-template and verification-template where missing.
- **Group 3 (Prompt-Pack)**: Added per-prompt HTML comment annotations for all HARD STOP, consent, and Y-level references in the body. 8 prompts annotated with appropriate ADR-062, ADR-062/066, and ADR-067 HTML comments.

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `plans/P36/verification-template.md` | modified | Replaced 12 soak/24h-soak refs with "permanent operation validation" terminology; added ADR-062/066 disclaimers to HARD STOP + consent checklist items |
| `plans/P36/evidence-template.md` | modified | Replaced 9 soak refs with "permanent operation" terminology; added ADR-062/066/067 disclaimers to Boundary Compliance section and Design Decisions section |
| `plans/P30/plan.md` | modified | Added file-level ADR-062/067 disclaimer after title heading |
| `plans/P30/README.md` | modified | Added file-level ADR-062/067 disclaimer after title heading |
| `plans/P30/evidence-template.md` | modified | Added file-level ADR-062/067 disclaimer; added body annotations to Boundary Compliance (Y5/Y6/HARD STOP/consent) and Design Decisions (HARD STOP) |
| `plans/P30/verification-template.md` | modified | Added file-level ADR-062/067 disclaimer; added HTML comment annotations to Female+dominant, HARD STOP, Consent sections; added inline annotations to Parent Checklist |
| `prompt-pack/prompt-pack.md` | modified | Added HTML comment annotations to 8 prompts: P28 (ADR-062 + consent), P29 (ADR-062 + consent), P30 (ADR-062 + consent + Y-level), P32 (ADR-062), P35 (ADR-062), P36 (ADR-062), Society Audit (ADR-062 + consent + Y-level), Scale-Out (ADR-062 + consent) |

## 3. Changes Detail

### Group 1: P36 Templates — Soak Ref Replacements

**verification-template.md** (12 replacements):
- `test_p36_24h_soak.py` → `test_p36_permanent_op.py`
- `24h soak harness` → `permanent operation validation harness`
- `Soak < 24h` → `Permanent op validation failed`
- `(Soak step)` → `(Permanent operation step)`
- `For the 24h soak step` → `For the permanent operation validation step`
- `at end of soak` → `at end of operation validation`
- `pre-soak vs post-soak` → `pre-operation vs post-operation`
- `for the soak window` → `for the operation validation window`
- `during soak` → `during operation validation`
- `soak window matches` → `operation validation window matches`
- `24h society soak` → `permanent operation validation`
- `24h society soak PASS` → `permanent operation validation PASS`

**evidence-template.md** (9 replacements + 5 disclaimers):
- `soak` → `permanent operation validation` (in 5 context lines)
- `24h soak rollback` → `24h permanent operation rollback`
- `24h society soak` → `24h society permanent operation`
- `Soak-time` → `Operation-time`
- `24h society soak PASS` → `24h society permanent operation PASS`
- Added ADR-062 disclaimer to `No HARD STOP bypass`
- Added ADR-062/066 disclaimer to `No consent violation`
- Added ADR-067 disclaimer to `No Y6 violation`
- Added ADR-062 disclaimers to HARD STOP design decisions

**ADR disclaimers added to P36 templates:**
- `Confirmed HARD STOP would halt all Hermeses` → `*(ADR-062: dev-workflow agent ONLY)*`
- `Confirmed consent revocation would block` → `*(ADR-062/066: dev-workflow ONLY)*`
- `No consent violation` → `*(ADR-062/066: dev-workflow ONLY)*`
- `No Y6 violation` → `*(ADR-067: dev-workflow ONLY)*`
- `No HARD STOP bypass` → `*(ADR-062: dev-workflow agent ONLY)*`

### Group 2: P30 Files — File-Level + Body Disclaimers

**File-level disclaimer (added to all 4 files):**
```
> **ADR-062/067 Disclaimer**: HARD STOP, consent gate, and Y-level cap references in this document apply to the dev-workflow agent (Guinevere in Claude) ONLY. Hermes runtime (P24 fork) is exempt per ADR-062 and ADR-067.
```

**Body annotations added:**
- `evidence-template.md`: Boundary Compliance section — ADR-062/066 on consent, ADR-067 on Y6, ADR-062 on HARD STOP, ADR-067 on Y5 persona drift. Design Decisions section — ADR-062 on both HARD STOP items.
- `verification-template.md`: HTML comments on Female+dominant section (ADR-067), HARD STOP section (ADR-062), Consent revocation section (ADR-062/066). Inline annotations on Parent Checklist items (HARD STOP cascade, recovery runbook, PersonaSafetyPolicy).

### Group 3: Prompt-Pack — Per-Prompt HTML Comment Annotations

| Prompt | Annotations Added |
|---|---|
| Prompt 1 (P28) | `<!-- ADR-062: HARD STOP... -->` + `<!-- ADR-062/066: Consent gate... -->` |
| Prompt 2 (P29) | `<!-- ADR-062: HARD STOP... -->` + `<!-- ADR-062/066: Consent gate... -->` |
| Prompt 3 (P30) | `<!-- ADR-062: HARD STOP... -->` + `<!-- ADR-062/066: Consent gate... -->` + `<!-- ADR-067: Y-level caps... -->` |
| Prompt 5 (P32) | `<!-- ADR-062: HARD STOP... -->` |
| Prompt 8 (P35) | `<!-- ADR-062: HARD STOP... -->` |
| Prompt 9 (P36) | `<!-- ADR-062: HARD STOP... -->` |
| Prompt 10 (Audit) | `<!-- ADR-062: HARD STOP... -->` + `<!-- ADR-062/066: Consent gate... -->` + `<!-- ADR-067: Y-level caps... -->` |
| Prompt 12 (Scale-Out) | `<!-- ADR-062: HARD STOP... -->` + `<!-- ADR-062/066: Consent gate... -->` |

## 4. Validation

- **Grep for "soak" in P36 templates**: 0 matches in `verification-template.md`, 0 matches in `evidence-template.md` ✅
- **Grep for ADR-062 in P30 files**: present in all 4 files (file-level + body) ✅
- **Grep for ADR-062/067 in prompt-pack**: 22 total references (5 pre-existing inline + 2 header + 15 new HTML comments) ✅
- **No prompts rewritten**: all changes are annotation-only (blockquote or HTML comments) ✅
- **No HARD STOP text deleted**: only annotated ✅

## 5. Auditor Fix Mapping

| Auditor Finding | Fix Applied |
|---|---|
| Auditor 03: P36 templates still reference "soak" | All 21 soak/24h-soak references replaced with "permanent operation validation" terminology |
| Auditor 03: P36 templates missing ADR-062/067 disclaimers | Added ADR-062 to HARD STOP, ADR-062/066 to consent, ADR-067 to Y-level refs in both templates |
| Auditor 07: P30 files missing file-level ADR-062 disclaimer | Added to all 4 P30 files |
| Auditor 07: P30 files missing body-level ADR disclaimers | Added to evidence-template (Boundary Compliance + Design Decisions) and verification-template (3 sections + parent checklist) |
| Auditor 07: Prompt-pack body missing per-line annotations | Added HTML comment annotations to 8 prompts covering all HARD STOP, consent, and Y-level refs |

## 6. Files NOT Touched (Out of Scope)

- `plans/P32/` — owned by another agent
- `plans/P35/` — owned by another agent
- `adr-drafts/` — owned by another agent
- `docs/` core docs — owned by another agent
- `plans/P36/README.md` and `plans/P36/plan.md` — contextual "NO soak test" references are correct (they explain the brainstorm decision, not promote soak testing)

## 7. Boundary Compliance

- [x] No persona drift
- [x] No consent violation
- [x] No surveillance overreach
- [x] No secret/intimate data exposure
- [x] All annotations are dev-workflow-only scoped per ADR-062/067

## Footer

Report version 1.0 | Date: 2026-06-28 | Author: Guinevere (executor)
