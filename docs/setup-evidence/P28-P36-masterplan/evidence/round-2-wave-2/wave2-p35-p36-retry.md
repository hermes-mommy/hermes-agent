---
title: "Wave 2 — P35 + P36 Phase Plans Update (Retry)"
status: "Complete"
date: "2026-06-28"
author: "Sisyphus-Junior (retry agent)"
scope: "P35 and P36 phase plans — brainstorm decision integration"
---

# Wave 2 — P35 + P36 Phase Plans Update (Retry)

## What Was Done

Updated 4 phase plan files (P35 + P36) with brainstorm decisions from the 2026-06-28 alignment session (65 decisions). This is a retry of a failed agent that previously timed out.

## Files Changed

### P35/plan.md
- **Version**: 1.0 → 1.1
- Added section "15. Brainstorm Decisions (2026-06-28)" with 19-row decision table
- Changed "Deploy" → "Configure and deploy" in Objective
- Changed "implementation" → "configuration" in scope (L1-L5 model)
- Added T1-T5 mutability ladder configuration detail in scope
- Added consent annotation + P24 native infrastructure note in scope
- Added decommissioning = hard fork + rebuild in OUT of scope
- Added memory = all permanent, self-modification scope, P24 native fork in OUT of scope
- Added **P24 v2.0 PASS** as HARD DEPENDENCY in dependency map
- Changed "Implement" → "Configure" in 6 step task descriptions (P35-001, 002, 003, 005, 007, 010)
- Added ADR-062 annotation to HARD STOP reference in section 11
- Added ADR-062 consent annotation to consent revocation reference in section 11
- Updated footer with change description

### P35/README.md
- **Version**: 1.0 → 1.1
- Added **P24 v2.0 PASS** as HARD DEPENDENCY in Prerequisites
- Changed "Implement" → "Configure" in 7 Goals bullets; "Build" → "Deploy" in 1 Goals bullet
- Added sub-agents, self-modification scope, T5 emergency, decommissioning, memory permanence to Goals
- Added ADR-062 annotation to HARD STOP reference in Locked Decisions
- Added ADR-062 consent annotation to consent revocation reference in Locked Decisions
- Added section "Brainstorm Decisions (2026-06-28)" with 13 bullet decisions
- Updated footer with change description

### P36/plan.md
- **Version**: 1.0 → 1.1
- **CRITICAL**: Changed "24-hour society-wide soak test" → "Permanent operation validation — NO SOAK TEST" in Step P36-009
- Updated all P36-009 details: task description, files, forbidden patterns, required commands, hard rejection
- Updated verification scaffold row for P36-009
- Updated auditor matrix row for P36-009
- Updated execution checklist for soak → permanent operation
- Updated boundary audit step P36-011: removed all "soak" references, replaced with "operation"
- Updated rollback plan: "24h soak rollback" → "Permanent operation rollback"
- Updated evidence requirements: "pre-soak vs post-soak" → "pre-operation vs post-operation"
- Updated locked decisions: ADR-062 annotation on HARD STOP, consent annotation, "soak" → "operation"
- Updated per-step audit trail: P36-009 events changed from soak to operation, P36-011 "during soak" → "during operation"
- Added **P24 v2.0 PASS** as HARD DEPENDENCY in dependency map
- Changed "Implement" → "Configure" in step tasks (P36-006, P36-008)
- Added brainstorm decisions to Objective: 6 circuit breakers, P24 hard dependency, Tailscale-first, auto-scaling, competitor monitoring
- Added scope items: circuit breakers, Tailscale-first detail, competitor monitoring, P24 native infrastructure
- Added section "14. Brainstorm Decisions (2026-06-28)" with 16-row decision table
- Updated footer with change description

### P36/README.md
- **Version**: 1.0 → 1.1
- **CRITICAL**: Changed "24-hour society-wide soak under full load" → "permanent continuous production operation from day 1 (NO soak test)" in Overview
- Updated Goals: "Implement" → "Configure", removed soak test line, added circuit breakers + Tailscale-first
- Updated Key Deliverables: "soak test" → "permanent operation validation"
- Updated Exit Criteria: "soak test PASS" → "permanent operation PASS" + ADR-062 annotation
- Updated Hard Rejection: "soak is not performed" → "permanent operation validation is not performed"
- Updated Implementation Wave Estimate: "24h society-wide soak test" → "permanent operation validation — NO soak test"
- Updated Locked Decisions: ADR-062 annotations, "soak proceeds" → "operation proceeds", "mid-soak" → "mid-operation"
- Updated Failure Modes: "24h soak alert fires" → "Permanent operation alert fires"
- Updated Open Questions: "24h soak" → "permanent operation"
- Added **P24 v2.0 PASS** as HARD DEPENDENCY in Prerequisites
- Added section "Brainstorm Decisions (2026-06-28)" with 14 bullet decisions
- Updated footer with change description

## Summary of Brainstorm Decisions Applied

| Decision Category | Changes Applied |
|---|---|
| NO soak test | All "24h soak"/"soak test" references replaced with "permanent operation" across all 4 files |
| T1-T5 mutability ladder | Added to P35 scope, Goals, and Brainstorm Decisions section |
| Personality drift bebas tanpa batas | Already present; verified in P35 Brainstorm Decisions table |
| Y6 prevention = NONE AT ALL | Already present; added to Brainstorm Decision tables |
| Y4/Y5 dev-workflow-only (ADR-067) | Already present; added to Brainstorm Decision tables |
| Drift monitoring saling monitor | Already present; added to Brainstorm Decision tables |
| Self-modification scope = everything except T5 | Added to P35 scope and Goals |
| T5 emergency = hard fork | Added to P35 scope and Brainstorm Decisions |
| Decommissioning = hard fork + rebuild | Added to P35 OUT of scope and Brainstorm Decisions |
| Memory = all permanent | Added to P35 scope and Goals |
| Sub-agents = native Hermes, limit 10 | Added to P35 Objective and Brainstorm Decisions |
| P24 v2.0 = HARD DEPENDENCY | Added to all 4 files (dependency map/prerequisites) |
| Fork-agnostic → P24 native fork | Added to P35 OUT of scope and Brainstorm Decisions |
| ADR-062 disclaimer | Added to all HARD STOP references in all 4 files |
| ADR-067 disclaimer | Added to Y-level references in Brainstorm Decision tables |
| Consent annotation (dev workflow only) | Added to all consent references in all 4 files |
| Implement → Configure/Deploy | Changed in P35 (6 steps + Goals), P36 (2 steps + Goals) |
| VPS security Tailscale-first | Added to P36 Objective, scope, Goals |
| 6 circuit breakers (P24 v2.0) | Added to P36 Objective, scope, Goals, Brainstorm Decisions |
| Auto-upgrade VPS scaling | Added to P36 Objective, Brainstorm Decisions |
| Competitor monitoring active | Added to P36 Objective, scope, Brainstorm Decisions |
| End-state = Full autonomy + Faiz as client | Added to P36 Brainstorm Decisions |
| Hotfix in production (no rollback) | Added to P36 Brainstorm Decisions |

## Validation

- All 4 files read before editing
- All edits were targeted (exact string replacement via filesystem_edit_file)
- No full-file rewrites
- No files outside P35/P36 scope were touched (except this report)
- All "soak" references in P35/P36 plans have been replaced
- ADR-062 annotations added to all HARD STOP references
- ADR-067 annotations present in Y-level references
- P24 v2.0 added as HARD DEPENDENCY in all 4 files
- Footer versions bumped from 1.0 to 1.1 in all 4 files

## Caveats

- Some "Implement" references in P35/plan.md step descriptions were kept where the step is genuinely about building/wiring (e.g., "Wire `src/evals/rec_eval.py`") rather than configuring existing infrastructure
- The P36-011 boundary audit step was updated to remove all "soak" references including file names and command-line flags
- P36/README.md "HARD STOP" reference in Exit Criteria now carries the ADR-062 annotation inline

## Report Path

`docs/setup-evidence/P28-P36-masterplan/evidence/round-2-wave-2/wave2-p35-p36-retry.md`
