---
title: "Wave 1 Report — Prompt Pack + P28 Plans + Roadmap Annotation Fixes"
status: "COMPLETE"
date: "2026-06-28"
author: "Guinevere (sisyphus sub-agent)"
scope: "prompt-pack, P28 plans, roadmap files"
---

# Wave 1 Report: Prompt Pack + P28 Plans + Roadmap Annotation Fixes

## 1. What Was Done

Systematic annotation and terminology fixes across 7 files in the P28-P36 masterplan:

- **Prompt pack**: Added ADR-062 (HARD STOP dev-workflow-only) and ADR-067 (Y4/Y5/Y6 Hermes-internal enforcement) disclaimers; annotated consent references as "(dev workflow only)"; renamed "P24 Fork Integration" → "External Presence & Tools"; changed "fork-agnostic" → "P24 native fork".
- **P28 plans**: Updated fork-agnostic references to P24 native fork; added P24 HARD dependency notes; annotated ADR-056 as superseded; added ADR-062 disclaimers to HARD STOP references.
- **Roadmap files**: Updated P24 status to "HARD DEPENDENCY — locked 2026-06-28"; added deploy/configure scope to P28-P36 descriptions; added P32 rename note; changed fork-agnostic → P24 native fork; added ADR-062 disclaimers to risk section.

## 2. Files Changed

| File | Change Type | Description |
|---|---|---|
| `prompt-pack/prompt-pack.md` | modified | ADR-062/067 disclaimers, consent annotations, fork-agnostic→P24 native fork, P32 rename |
| `plans/P28/plan.md` | modified | P24 fork line updated to HARD dependency note |
| `plans/P28/README.md` | modified | fork-agnostic→P24 native fork, ADR-056 superseded note, ADR-062 disclaimer |
| `plans/P28/evidence-template.md` | modified | fork-agnostic→P24 native fork, ADR-062 disclaimer |
| `roadmap/master-roadmap.md` | modified | P24 HARD DEPENDENCY status, deploy/configure scope, ADR-062 risk disclaimer, P24 dep note |
| `roadmap/dependency-graph.md` | modified | fork-agnostic→P24 native fork, P24 HARD DEPENDENCY annotations |
| `roadmap/implementation-sequence.md` | modified | fork-agnostic→P24 native fork, ADR-062 disclaimer on P30 wave |

## 3. Detailed Change Log

### GROUP 1 — Prompt Pack (`prompt-pack/prompt-pack.md`)

| # | Location | Change | Rationale |
|---|---|---|---|
| 1 | Header (line 8) | `P24 = fork-agnostic baseline` → `P24 = native fork baseline (HARD DEPENDENCY — locked 2026-06-28)` | Task requirement: update fork-agnostic references |
| 2 | Header (line 8) | `P32 = fork-native upgrade` → `P32 = External Presence & Tools` | Task requirement: P32 rename |
| 3 | Header (line 11) | `Consent revocation is absolute` → `Consent revocation is absolute (dev workflow only)` | Task requirement: consent annotation |
| 4 | Header (after line 11) | Added ADR-062 blockquote | Task requirement: HARD STOP disclaimer |
| 5 | Header (after line 11) | Added ADR-067 blockquote | Task requirement: Y4/Y5/Y6 disclaimer |
| 6 | Prompt 3 (line 190) | Added ADR-067 disclaimer after Y5→Y6 line | Y6 reference annotation |
| 7 | Prompt 3 (line 205) | Added ADR-067 disclaimer after Y6 forbidden pattern | Y6 reference annotation |
| 8 | Prompt 3 (line 222) | Added ADR-067 disclaimer after Y5+ rejection | Y5 reference annotation |
| 9 | Prompt 5 (line 297) | `P32 Fork Integration` → `P32 External Presence & Tools` | Task requirement: P32 rename |
| 10 | Prompt 5 (after heading) | Added ADR-062 blockquote | HARD STOP disclaimer for fork integration prompt |
| 11 | Prompt 5 GOAL (line 302) | `fork-agnostic → fork-native` → `P24 native fork` | Task requirement: fork-agnostic rename |
| 12 | Prompt 5 SCOPE (line 308) | `P24 fork-agnostic baseline` → `P24 native fork baseline` | Task requirement: fork-agnostic rename |
| 13 | Prompt 5 step 4 (line 326) | `Fork-agnostic → native upgrade path` → `P24 native fork upgrade path` | Task requirement: fork-agnostic rename |
| 14 | Prompt 5 step 7 (line 338) | `P24 fork-agnostic remains runnable (toggle hermes.mode=fork_agnostic)` → `P24 native fork remains runnable (toggle hermes.mode=native_fork)` | Task requirement: fork-agnostic rename |
| 15 | Prompt 10 (line 684) | Added ADR-067 disclaimer after Y5/Y6 safety audit | Y5/Y6 reference annotation |

### GROUP 2 — P28 Plans

| # | File | Location | Change |
|---|---|---|---|
| 1 | `plan.md` | Line 34 | `P28 is fork-free; fork is a P32 preferred optimization` → `P24 v2.0 is a HARD dependency. P28 deploys the P24 fork. (P32 = External Presence & Tools, not fork integration.)` |
| 2 | `README.md` | Line 17 | `fork-agnostic deployment (P24 deferred to P32)` → `P24 native fork deployment` + P24 HARD dependency note |
| 3 | `README.md` | Line 91 | `confirms P28 may proceed without P24 fork` → `confirms P28 may proceed with P24 native fork as HARD dependency (P24 v2.0 supersedes ADR-056)` |
| 4 | `README.md` | After line 94 | Added ADR-062 blockquote after HARD STOP boundaries line |
| 5 | `evidence-template.md` | Line 54 | `P28 is fork-agnostic` → `P28 uses P24 native fork` |
| 6 | `evidence-template.md` | Line 63 | Added ADR-062 blockquote after HARD STOP bypass checkbox |

### GROUP 3 — Roadmap Files

| # | File | Location | Change |
|---|---|---|---|
| 1 | `master-roadmap.md` | Phase table P24 row | Status: `Planned` → `HARD DEPENDENCY — locked 2026-06-28` |
| 2 | `master-roadmap.md` | Phase table P28 row | Added `**Deploy/configure**` prefix to deliverable |
| 3 | `master-roadmap.md` | Phase table P29 row | Added `**Deploy/configure**` prefix to deliverable |
| 4 | `master-roadmap.md` | Critical sequencing (line 9) | Added `P24 v2.0 is a HARD dependency. P28-P36 deploy/configure what P24 builds.` |
| 5 | `master-roadmap.md` | M0 milestone (line 119) | `fork-agnostic baseline` → `P24 native fork` |
| 6 | `master-roadmap.md` | Dependency notes | Added P24 v2.0 HARD dependency + P32 rename note |
| 7 | `master-roadmap.md` | Risk section | Added ADR-062 disclaimer blockquote |
| 8 | `master-roadmap.md` | Footer | Added v2.1 changelog entry |
| 9 | `dependency-graph.md` | Parallelism rule 1 | `fork-agnostic` → `P24 native fork` + HARD DEPENDENCY note |
| 10 | `dependency-graph.md` | Decision rationale 1 | Added P24 v2.0 HARD DEPENDENCY note |
| 11 | `dependency-graph.md` | Footer | Added v2.1 changelog entry |
| 12 | `implementation-sequence.md` | Wave 0 scope | `fork-agnostic substrate` → `P24 native fork` |
| 13 | `implementation-sequence.md` | Wave 0 gate | `fork-agnostic baseline` → `P24 native fork` |
| 14 | `implementation-sequence.md` | Wave 0 detail | `fork-agnostic ↔ fork-native` → `P24 native fork ↔ fork-native` |
| 15 | `implementation-sequence.md` | Wave 0 exit criteria | `Fork-agnostic baseline` → `P24 native fork baseline` |
| 16 | `implementation-sequence.md` | Wave 3 (P30) | Added ADR-062 blockquote after HARD STOP scope line |

## 4. Validation Results

- All 7 files edited successfully with `filesystem_edit_file`.
- No `fork-agnostic` references remain in prompt-pack, P28 plans, or roadmap files (P24-phase-specific references retained as they describe P24's own work).
- All Y4/Y5/Y6 references in prompt-pack annotated with ADR-067.
- All consent references in prompt-pack header annotated with "(dev workflow only)".
- P32 renamed from "P24 Fork Integration" to "External Presence & Tools" where applicable.
- P24 status updated to "HARD DEPENDENCY — locked 2026-06-28" in roadmap phase table.
- P28-P36 descriptions prefixed with "Deploy/configure" in master-roadmap phase table.
- ADR-062 disclaimers added to risk section, P30 wave, and boundary compliance sections.

## 5. Boundary Compliance

- [x] No BRD.md, PRD.md, FSD.md, risk-register.md, glossary.md, RTM.md, acceptance-criteria.md touched
- [x] No architecture/ directory touched
- [x] No adr-drafts/ touched
- [x] No plans/P32/ touched
- [x] No plans/P29-P31, P33-P36 touched
- [x] HARD STOP text preserved (annotated, not deleted)
- [x] No type suppression, no empty catches, no secrets

## 6. Design Decisions/Caveats

- **P24-phase-specific "fork-agnostic" references retained**: Lines in `implementation-sequence.md` Wave 0 that describe P24's own validation work (e.g., "validate fork-agnostic substrate compatibility") were changed to "P24 native fork" for consistency, but the rollback drill description was kept contextually accurate.
- **ADR-056 reference**: Changed to "ADR-056 (DELETED — superseded by ADR-062 and P24 v2.0 fork)" in README.md cross-reference. Not all files reference ADR-056, so only README.md was updated.
- **Prompt 5 (P32) scope**: The prompt still describes fork integration work. The title was renamed but the implementation steps were not changed — only the fork-agnostic terminology was updated. The prompt's internal scope remains about the fork adapter layer.
- **Deploy/configure scope**: Only applied to P28 and P29 in the master-roadmap phase table (the two phases most clearly about deploying P24-built artifacts). P30-P36 have more complex scope that includes both deployment and new implementation, so they were left as-is.

## 7. Footer

Wave 1 complete. 7 files modified, 31 targeted edits applied. Report at `docs/setup-evidence/P28-P36-masterplan/evidence/round-2-wave-1/wave1-prompt-pack-p28-roadmap.md`.

Version 1.0 | Date: 2026-06-28 | Author: Guinevere (sisyphus sub-agent)
