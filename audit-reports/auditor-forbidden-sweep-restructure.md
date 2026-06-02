# Auditor Report: Forbidden Pattern Sweep — Phase Restructure Task

**Auditor:** Independent forbidden-pattern auditor  
**Date:** 2026-06-03  
**Scope:** All `.md` files under `C:\Users\faizz\guinevere\` EXCLUDING `_archive/`, `research-reports/`, `docs/setup-evidence/`, `audit-reports/`  
**Verdict:** **NEEDS REVIEW**

---

## Executive Summary

| Pattern | Source/Gov Matches | Excluded Matches | NEEDS REVIEW | Sub-Verdict |
|---|---|---|---|---|
| P1: `post-MVP` | **31** (26 ADR files) | ~140 | 2 (`qa-inputs/`) | FAIL* |
| P2: `P9-P11` | 0 | ~60 | 1 (`fixes/`) | NEEDS REVIEW |
| P3: `Total Phases: 12` | 0 | 8 | 0 | PASS |
| P4: `252 steps` / `Total Steps: 252` | 0 | ~60 | 4 (`fixes/`) | NEEDS REVIEW |
| P5: `Phase 11: Advanced Integrations` | 0 | 12 | 0 | PASS |

**Overall Verdict: NEEDS REVIEW** — The 10 target files (PROGRESS.md, CHECKLIST.md, StepPrompts.md, IMPLEMENTATION_GUIDE.md, docs/README.md, docs/00-core/*, docs/10-governance/*, stepprompts/*) are clean of all 5 forbidden patterns. **However**, `post-MVP` (lowercase p) appears in 26 ADR files as standard boilerplate unrelated to phase structure, and 2 non-target files (`qa-inputs/`, `fixes/`) contain stale references.

---

## Pattern 1: `post-MVP` (case-sensitive, lowercase p)

**Expected:** 0 in source/governance docs  
**Acceptable:** `_archive/`, `research-reports/`, evidence, audit reports  
**NOTE:** `Post-MVP` (capital P) is acceptable in ADR titles/filenames.

### Category: FAIL — Governance Docs (adr/)

All 26 ADR files in `adr/` contain `post-MVP` in lowercase. These are **NOT phase-structure references** — they are the ADR-021 canonical decision boilerplate classifying wearable integration and monitoring VPS as deferred past MVP. Semantically distinct from the old "P9-P11 post-MVP" grouping this audit targets.

| # | File | Line | Context |
|---|---|---|---|
| 1 | `adr/ADR-001-persona-safety-ethical-boundary.md` | 69 | `Wearable integrations are post-MVP and must not be treated as active dependencies.` |
| 2 | `adr/ADR-002-user-autonomy-safe-word-enforcement.md` | 69 | Same boilerplate |
| 3 | `adr/ADR-003-persona-drift-control-validation.md` | 74 | Same boilerplate |
| 4 | `adr/ADR-004-primary-llm-model-selection.md` | 69 | Same boilerplate |
| 5 | `adr/ADR-005-llm-router-failover-strategy.md` | 69 | Same boilerplate |
| 6 | `adr/ADR-006-sub-agent-llm-model-strategy.md` | 69 | Same boilerplate |
| 7 | `adr/ADR-007-memory-storage-backend-selection.md` | 69 | Same boilerplate |
| 8 | `adr/ADR-008-memory-encryption-key-management.md` | 69 | Same boilerplate |
| 9 | `adr/ADR-009-memory-recall-semantic-search-strategy.md` | 75 | Same boilerplate |
| 10 | `adr/ADR-010-surveillance-data-retention-policy.md` | 71 | Same boilerplate |
| 11 | `adr/ADR-011-sdlc-loop-phase-specification.md` | 69 | Same boilerplate |
| 12 | `adr/ADR-012-sub-agent-orchestration-governance.md` | 69 | Same boilerplate |
| 13 | `adr/ADR-013-guinevere-mcp-native-opencode-replacement.md` | 71 | Same boilerplate |
| 14 | `adr/ADR-014-vps-container-architecture.md` | 69 | Same boilerplate |
| 15 | `adr/ADR-015-secrets-management-strategy.md` | 69 | Same boilerplate |
| 16 | `adr/ADR-016-cicd-autonomous-deployment-strategy.md` | 74 | Same boilerplate |
| 17 | `adr/ADR-017-monitoring-stack-selection.md` | 69, 89 | Boilerplate + `separate monitoring VPS is post-MVP` |
| 18 | `adr/ADR-018-security-architecture-defense-in-depth.md` | 68 | Same boilerplate |
| 19 | `adr/ADR-019-access-control-vpn-mesh-strategy.md` | 74 | Same boilerplate |
| 20 | `adr/ADR-020-browser-automation-strategy.md` | 69 | Same boilerplate |
| 21 | `adr/ADR-021-wearable-integration-post-mvp.md` | 60, 71, 85, 89, 91 | **Canonical decision file** — defines wearable as post-MVP |
| 22 | `adr/ADR-022-communication-channel-strategy.md` | 75 | Same boilerplate |
| 23 | `adr/ADR-023-financial-data-integration-strategy.md` | 77 | Same boilerplate |
| 24 | `adr/ADR-024-data-governance-classification-policy.md` | 71 | Same boilerplate |
| 25 | `adr/ADR-025-backup-disaster-recovery-strategy.md` | 70 | Same boilerplate |
| 26 | `adr/ADR-029-self-modification-automated-testing.md` | 79 | Same boilerplate |

**Assessment:** 25 of 26 ADR files have exactly 1 match each (the standard "Wearable integrations are post-MVP" boilerplate). ADR-017 has 2 matches (boilerplate + monitoring VPS). ADR-021 has 7 matches (the canonical wearable decision document itself). **Every single ADR match is about wearable/monitoring deferral (ADR-021 decision), NOT about phase structure.** These would need a separate, deliberate task to sweep if desired — they are not phase-restructure stragglers.

### Category: NEEDS REVIEW — `qa-inputs/`

| # | File | Line | Context |
|---|---|---|---|
| 1 | `qa-inputs/Guinevere_QA_Answers_Samm.md` | 210 | `- **Phase 3**: Wearable post-MVP` |
| 2 | `qa-inputs/Guinevere_QA_Answers_Samm.md` | 409 | `health data (steps, sleep — post-MVP).` |

**Assessment:** QA answers file referencing wearable deferral. Not in excluded directories, not in 10 target files. Low risk — these are wearable-deferral references, not phase-structure references.

### Category: Excluded Directories (Acceptable)

Approximately ~140 matches across:
- `research-reports/2026-05-30-*.md` (~15 files)
- `research-reports/restructure/*.md` (3 files)
- `docs/_archive/Guinevere_PRD_v2.*.md` (2 files)
- `docs/setup-evidence/restructure/*.md` (8 files)
- `audit-reports/` (various)

All excluded — no action needed.

---

## Pattern 2: `P9-P11` (old phase range)

**Expected:** 0 in source/governance docs  
**Acceptable:** archive/evidence/audit

### Category: NEEDS REVIEW — `fixes/`

| # | File | Line | Context |
|---|---|---|---|
| 1 | `fixes/2026-05-31-stepprompts-fixes.md` | 466 | `\| H-24 \| P9-P11 grouped \| Accept as design decision (document rationale) \|` |

**Assessment:** Single reference in a historical fixes document. Not in 10 target files, not in core governance. Low risk but should be noted.

### Category: Excluded Directories (Acceptable)

Approximately ~60 matches across:
- `research-reports/restructure/p9-p10-p11-references.md` (catalog of all references)
- `research-reports/restructure/impact-map.md`
- `audit-reports/stepprompts-audit/D6-D7-completeness-acceptance.md`
- `audit-reports/stepprompts-audit/D3-D4-security-sharedvps.md`
- `audit-reports/2026-05-31-stepprompts-full-audit.md`
- `audit-reports/2026-05-31-stepprompts-fixes-applied.md`
- `audit-reports/2026-05-31-implementation-synthesis.md`
- `docs/setup-evidence/restructure/*.md` (6 files)

All excluded — no action needed.

---

## Pattern 3: `Total Phases: 12`

**Expected:** 0 in source/governance docs

### Category: PASS

**0 matches in source/governance docs.** All 8 matches are in excluded directories:
- `docs/setup-evidence/restructure/verification-T4-stepprompts.md` (verification evidence — PASS check)
- `docs/setup-evidence/restructure/verification-T12-cross-file.md` (verification evidence — PASS check)
- `docs/setup-evidence/restructure/evidence-phase-restructure.md` (evidence — PASS check)
- `docs/setup-evidence/restructure/batch-plan-phase-restructure.md` (batch plan instructions)

**Verdict: PASS**

---

## Pattern 4: `252 steps` / `Total Steps: 252`

**Expected:** 0 in source/governance docs

### Category: NEEDS REVIEW — `fixes/`

| # | File | Line | Context |
|---|---|---|---|
| 1 | `fixes/2026-05-31-stepprompts-fixes.md` | 250 | `**Scope:** ALL 252 steps` |
| 2 | `fixes/2026-05-31-stepprompts-fixes.md` | 264 | `**Scope:** ALL 252 steps` |
| 3 | `fixes/2026-05-31-stepprompts-fixes.md` | 270 | `**Scope:** ALL 252 steps` |
| 4 | `fixes/2026-05-31-stepprompts-fixes.md` | 281 | `**Scope:** ALL 252 steps` |

**Assessment:** 4 references in historical fixes document describing the scope of StepPrompts fixes (pre-restructure). Not in 10 target files, not in core governance. Low risk.

### Category: Excluded Directories (Acceptable)

Approximately ~60 matches across:
- `research-reports/restructure/p9-p10-p11-references.md`
- `research-reports/restructure/impact-map.md`
- `audit-reports/stepprompts-audit/*.md` (5 files)
- `audit-reports/2026-05-31-stepprompts-full-audit.md`
- `docs/setup-evidence/restructure/*.md` (6 files)

All excluded — no action needed.

---

## Pattern 5: `Phase 11: Advanced Integrations`

**Expected:** 0 in source/governance docs

### Category: PASS

**0 matches in source/governance docs.** All 13 matches are in excluded directories:
- `research-reports/restructure/p9-p10-p11-references.md` (2 matches — reference catalog)
- `docs/setup-evidence/restructure/verification-T4-stepprompts.md` (verification — PASS check)
- `docs/setup-evidence/restructure/verification-T5-implementation-guide.md` (verification — PASS check)
- `docs/setup-evidence/restructure/verification-T3-checklist.md` (verification — PASS check)
- `docs/setup-evidence/restructure/verification-T12-cross-file.md` (verification — PASS check)
- `docs/setup-evidence/restructure/evidence-phase-restructure.md` (evidence — PASS check)
- `docs/setup-evidence/restructure/batch-plan-phase-restructure.md` (batch plan instructions)

**Verdict: PASS**

---

## Summary of Non-Excluded Matches

### Files Requiring Action

| File | Patterns | Severity | Recommended Action |
|---|---|---|---|
| `adr/ADR-001` through `adr/ADR-029` (26 files) | `post-MVP` (31 matches) | Technical FAIL — semantically distinct | Defer to separate ADR boilerplate sweep task; NOT phase-restructure stragglers |
| `qa-inputs/Guinevere_QA_Answers_Samm.md` | `post-MVP` (2 matches) | Low | Replace with "Stabilization" or "Expansion" if phase-related; leave if wearable-deferral |
| `fixes/2026-05-31-stepprompts-fixes.md` | `P9-P11` (1), `252 steps` (4) | Low | Historical fixes file — add addendum noting post-restructure context |

### Clean Verification

The **10 target files** of the phase restructure task pass ALL 5 patterns:
- `PROGRESS.md` — PASS
- `CHECKLIST.md` — PASS
- `stepprompts/StepPrompts.md` — PASS
- `docs/IMPLEMENTATION_GUIDE.md` — PASS
- `docs/README.md` — PASS
- `docs/00-core/*` — PASS
- `docs/10-governance/*` (ADR-Index, Charter, etc.) — PASS

No forbidden pattern appears in any of the 10 target files or the core documentation suite (outside `adr/`).

---

## Final Verdict: NEEDS REVIEW

**Rationale:**

1. **Patterns 3 and 5: PASS** — Zero matches in any non-excluded directory.
2. **Patterns 2 and 4: NEEDS REVIEW** — Stale references isolated to `fixes/2026-05-31-stepprompts-fixes.md` (historical document). Not present in any target or governance file.
3. **Pattern 1: NEEDS REVIEW (technical FAIL on ADRs)** — 26 ADR files contain lowercase `post-MVP` as standard wearable-deferral boilerplate (ADR-021 canonical decision). These are semantically distinct from the phase-structure "post-MVP P9-P11" grouping. A blanket grep-based replacement would be dangerous here — these ADR references are about wearable/monitoring classification, not phase structure. Recommend a separate, deliberate ADR boilerplate sweep task if this needs cleanup.

**The phase restructure task's 10 target files are verified clean of all 5 forbidden patterns.**

---

*Audit completed: 2026-06-03 | No files modified.*