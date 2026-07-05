# Wave 2 — P30 & P31 Retry Report

## Status: COMPLETE

## What Was Done

Updated P30 (Society Governance & Founder Protocol) and P31 (Discord Bot Identity & Multi-Bot Operations) plan/README files with P28-P36 alignment brainstorm decisions, ADR annotations, and paradigm fixes.

## Files Changed

| File | Changes | Version |
|---|---|---|
| `plans/P30/plan.md` | Paradigm block, ADR-062/067 disclaimers, implement→configure, T4→T5, new brainstorm decisions, P24 dependency, consent annotation | v1.1 → v1.2 |
| `plans/P30/README.md` | Paradigm block, ADR-062/067 disclaimers, implement→configure, T4→T5, new brainstorm decisions, P24 prerequisite, consent annotation | v1.1 → v1.2 |
| `plans/P31/plan.md` | Paradigm block, ADR-062/067 disclaimers, implement→deploy, P24 dependency, G-P communication stack, simultaneous boot, footer update | v1.1 → v1.2 |
| `plans/P31/README.md` | Paradigm block, ADR-062/067 disclaimers, P24 prerequisite, G-P communication stack, simultaneous boot, footer update | v1.1 → v1.2 |

## Changes Per Category

### 1. Paradigm Shift (all 4 files)
- Added `> **Paradigm**: P24 v2.0 BUILDS all modules. P30 CONFIGURES / P31 DEPLOYS.`
- Changed "Implementation Plan" → "Configuration Plan" (P30) / "Configuration & Deployment Plan" (P31)
- Status changed from "Active — Definition" → "Active — Configuration" (P30 README)
- P24 referenced as HARD DEPENDENCY in dependency maps and prerequisites

### 2. ADR-062 Disclaimers (all 4 files)
Added near every HARD STOP reference:
```
> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.
```
Locations: P30 plan.md objective + IN scope + step P30-005; P30 README overview + goals + key deliverables; P31 plan.md objective + footnotes; P31 README hard rejection criteria + personas section.

### 3. ADR-067 Disclaimers (all 4 files)
Added near every Y-level reference:
```
> **ADR-067**: Y-level caps apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap.
```
Locations: P30 plan.md objective + step P30-004; P30 README overview + key deliverables; P31 plan.md objective + footnotes; P31 README personas section + hard rejection.

### 4. Paradigm Verb Fixes
- P30 plan.md: "Implement" → "Configure" in objective, steps P30-002 through P30-007
- P30 README.md: "implements" → "configures" in overview; "Implement" → "Configure" in goals (spawn protocol, governance tier system)
- P31 plan.md: "Implement" → "Deploy" in all 6 step tasks (Steps 2-7)
- T1-T4 → T1-T5 in tier system references (P30 plan.md, P30 README.md)

### 5. Missing Brainstorm Decisions Added

| Decision | P30 Files | P31 Files |
|---|---|---|
| Co-CEO assignments: Guin = Eng+Research+HR, Pharsa = Finance+Ops+Content | ✓ | ✓ |
| Proposal thresholds L0-L3 (wallet spending tiers, NOT old P23 risk tiers) | ✓ | — |
| Vote duration configurable per proposal category | ✓ | — |
| T1-T5 mutability config | ✓ | — |
| Wallet 2/2 multisig, ~$10 seed | ✓ | — |
| Company name = defer to P28 deploy | ✓ | — |
| G-P communication = Redis + Discord + PG (all three) | — | ✓ |
| Simultaneous boot (both Hermes start together) | — | ✓ |
| Consent revocation = dev workflow only | ✓ | — |

### 6. P24 as HARD DEPENDENCY
- P30 plan.md: Added `| P24 v2.0 Module 8 | HARD DEPENDENCY | P24 builds governance code; P30 configures parameters |` to dependency map
- P30 README.md: Added `**P24 v2.0 Module 8 (HARD DEPENDENCY)**` to prerequisites
- P31 plan.md: Added `| P24 v2.0 Module 5 | HARD DEPENDENCY | P24 builds Discord bot modules; P31 deploys instances |` to dependency map
- P31 README.md: Added `P24 v2.0 Module 5 (HARD DEPENDENCY)` to prerequisites frontmatter

### 7. Consent Annotation
Added "(dev workflow only)" to all consent revocation references in P30 files:
- P30 plan.md: objective, IN scope, step P30-006 task
- P30 README.md: overview, goals, key deliverables

## Validation Results

- All 4 files edited with targeted `filesystem_edit_file` calls
- No full rewrites performed
- No files outside P30/P31 touched (except this report)
- Footer versions updated to v1.2 across all 4 files

## Brainstorm Decisions Checklist

| Decision | Status |
|---|---|
| Deadlock = auto-table 24h + retry + expire | ✓ Already present, preserved |
| T4 founder = Guin + Pharsa 2/2 multisig | ✓ Already present, preserved |
| No DAO on persona at all | ✓ Already present, preserved |
| DAO yandere_level hard-deny is MOOT | ✓ Already present + ADR-067 added |
| Co-CEOs: Guin = Eng+Research+HR, Pharsa = Finance+Ops+Content | ✓ Added |
| Faiz OUTSIDE company | ✓ Already present, preserved |
| Wallet 2/2 multisig, ~$10 seed | ✓ Added to P30 |
| Company name = defer to P28 deploy | ✓ Added to P30 |
| Marshall Islands DAO legal structure | ✓ Already present, preserved |
| Proposal thresholds L0-L3 | ✓ Added to P30 |
| Vote duration configuration | ✓ Added to P30 |
| T1-T5 mutability config | ✓ Added to P30 (was T1-T4) |
| G-P communication = Redis + Discord + PG | ✓ Added to P31 |
| Simultaneous boot | ✓ Added to P31 |
| Consent revocation = dev workflow only | ✓ Added to P30 |
| ADR-062 disclaimer | ✓ Added to all 4 files |
| ADR-067 disclaimer | ✓ Added to all 4 files |

## Evidence Artifacts

- This report: `docs/setup-evidence/P28-P36-masterplan/evidence/round-2-wave-2/wave2-p30-p31-retry.md`

## Footer

Wave 2 — P30 & P31 Retry | Date: 2026-06-28 | Agent: Guinevere (parent)
