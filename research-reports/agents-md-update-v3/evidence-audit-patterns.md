# Research: Evidence & Audit Report Patterns for AGENTS.md v2.1 Update

| Field | Value |
|---|---|
| **Research Agent** | Explore (Guinevere parent) |
| **Date** | 2026-06-01 |
| **Scope** | Local \docs/setup-evidence/\, \udit-reports/\, \evidence/\, esearch-reports/agents-md-update/\ patterns |
| **Verdict** | Canonical schemas identified for verification.md (12-section), auditor report (13-15 section), and research report templates. Version table wording, footer convention, and path conventions documented below. |

---

## 1. Evidence Directory Structure Convention

### 1.1 \docs/setup-evidence/\ (Implementation Evidence - Canonical Pattern)

This is the **primary** evidence directory for active step-by-step implementation verification. Two naming conventions coexist depending on phase:

**Phase P0-P1 (early):** Files named \evidence.md\ using a 10-12 section schema.

\docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
├── evidence.md                         ← 10-12 section canonical schema
├── <check>.txt                         ← command output proofs
└── p{N}-{XXX}-summary.md              ← Step summary
\
**Phase P2 (later evolution):** Files renamed to \erification.md\ with a more detailed 12-13 section schema.

\docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
├── verification.md                     ← 12-13 section canonical schema
├── p{N}-{XXX}-implementation-summary.md ← Implementation summary (P2)
└── <artifact>.txt/.yaml                ← Proof files
\
**Root-level batch plans:**

\docs/setup-evidence/P{N}/batch-plan-{XXX}-{YYY}.md
\
**Non-step-specific evidence:**

\docs/setup-evidence/<topic>/verification.md
\
Existing examples:
| Path | Pattern |
|---|---|
| \docs/setup-evidence/P1/STEP-P1-016/evidence.md\ | P1 \evidence.md\ style (10 sections) |
| \docs/setup-evidence/P2/STEP-P2-010/verification.md\ | P2 \erification.md\ style (12 sections) |
| \docs/setup-evidence/agents-md-update/verification.md\ | Topic-based \erification.md\ style (12 sections) |
| \docs/setup-evidence/caveats-resolution/verification.md\ | Topic-based \erification.md\ style (12 sections) |
| \docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md\ | Topic-based standalone file |

### 1.2 Root \evidence/\ (Historical Reorganization / Bulk Evidence - Not Active Steps)

This directory stores historical/bulk evidence - not used for active step verification.

\evidence/<topic>/<date>-<description>.md
\
**Critical distinction:** For AGENTS.md update, use \docs/setup-evidence/agents-md-update-v3/\ (not \evidence/\). The root \evidence/\ directory is for historical bulk records; active per-step verification goes in \docs/setup-evidence/\.

---
## 2. Verification.md / evidence.md - Canonical Content Schema

Based on P2 verification.md (12 sections) and P1 evidence.md (10 sections):

### P2 Verification.md 12-Section Schema (Canonical for AGENTS.md update)

| # | Section | Required | Notes |
|---|---|---|---|
| 1 | **What Was Done** | YES | High-level summary + approach. List changes made with bullet points. |
| 2 | **Files Changed** | YES | Table: Path | Change. Include the evidence file itself. |
| 3 | **Validation Results** | YES | Diagnostics, grep checks, LSP, deterministic checks. Table with PASS/FAIL. |
| 4 | **Evidence Artifacts** | YES | Table: Artifact | Path | Purpose/Status |
| 5 | **Doc-Sync Impact** | YES | PROGRESS.md, CHECKLIST.md, StepPrompts.md - or explicit N/A |
| 6 | **Boundary Compliance** | YES | Table: Check | Status. Persona drift, consent, surveillance, Y4/Y5/Y6, HARD STOP, distress, secrets. |
| 7 | **Rollback / Re-run Safety** | YES | Rollback path (commands), idempotency notes |
| 8 | **Design Decisions / Caveats** | YES | Why choices made, deferred items, accepted false-positives |
| 9 | **Auditor Gate** | YES | Status + expected report path |
| 10 | **Security Scan** | OPTIONAL | Token regex scan results (include if any files changed) |
| 11 | **Acceptance Criteria Mapping** | OPTIONAL | Table: Requirement | Status |
| 12 | **Footer** | YES | Source task, date, implementer, validation method |

### Header Format (Standard)

For topic-based evidence (like AGENTS.md updates), the header format is:

`markdown
# <Topic> Verification

| Field | Value |
|---|---|
| Scope | \AGENTS.md\ - description of scope |
| Date | 2026-06-01 |
| Implementer | Guinevere |
| Trigger | Faiz directive: ... |
| Evidence path | \docs/setup-evidence/<scope>/verification.md\ |
`

Alternative simpler header (from caveats-resolution verification.md):

`markdown
# <Topic> Evidence

**Source Task**: ...
**Date**: ...
**Implementer**: ...
**Validation Method**: ...
**Evidence Root**: docs/setup-evidence/<scope>/
**Auditor Gate**: audit-reports/<scope>/<auditor-report.md>
`

### Footer Format (Standard)

`markdown
## Footer

**Source task**: <task description>
**Date**: 2026-06-01
**Implementer**: Guinevere
**Validation method**: <method>
**Evidence Root**: docs/setup-evidence/<scope>/
`

---
## 3. Audit Reports - Canonical Schema

### 3.1 Naming Conventions

Two naming conventions coexist:

**Per-step pattern (P0-P2):**
`
audit-reports/P{N}/STEP-P{N}-{XXX}/step-p{N}-{XXX}-auditor-report.md
`

**Topic-based pattern (non-step):**
`
audit-reports/<topic>/<topic>-auditor-report.md
`
or (for direct-root audits):
`
audit-reports/<date>-<description>.md
`

Existing topic-based examples:
| Path | Description |
|---|---|
| audit-reports/agents-md-update/agents-md-update-auditor-report.md | Previous AGENTS.md auditor report |
| audit-reports/caveats-resolution/caveats-resolution-auditor-report.md | Caveats resolution auditor |
| audit-reports/2026-05-30-agents-contract-audit.md | Root-level AGENTS contract audit |
| audit-reports/2026-05-31-stepprompts-full-audit.md | Root-level step prompts audit |

**Recommended for AGENTS.md v2.1:**
`
audit-reports/agents-md-update-v3/agents-md-v2.1-auditor-report.md
`

### 3.2 Auditor Report Schema (P2 style - 13 to 15 sections)

Based on the most evolved examples (P2-009, P0-004):

| # | Section | Required | Notes |
|---|---|---|---|
| 1 | **Header** | YES | Step, Auditor, Date, Method, Verdict |
| 2 | **Files Audited** | YES | Table: # | Path | Type (evidence/source/report) |
| 3 | **Acceptance Criteria Check** | YES | Table: # | Criterion | Expected | Actual | Verdict |
| 4 | **Evidence File Inventory** | YES | Table: File | Exists | Content Verified | Status |
| 5 | **Secret Hygiene Verification** | YES | Grep for tokens, API keys, passwords |
| 6 | **Code Quality / Unsafe Pattern Scan** | YES | Grep for type: ignore, as any, except: pass, Any |
| 7 | **Cross-Reference Validation** | OPTIONAL | Table: Reference | Source File | Target | Valid? |
| 8 | **Boundary Compliance Verification** | YES | Table: Boundary | Evidence Says | Audit Verification | Verdict |
| 9 | **Auditor Recommendations** | YES | Table: # | Recommendation | Severity | Action Required |
| 10 | **Introduced vs Pre-existing Issues** | OPTIONAL | Type/Description/Severity table |
| 11 | **Rollback Safety Check** | YES | Is rollback path documented and safe? |
| 12 | **Diagnostics Check** | YES | LSP diagnostics on all changed files |
| 13 | **Verdict Summary** | YES | Table: Area | Result. Final PASS/NEEDS REVIEW/FAIL |
| 14 | **Follow-Up (if re-audit)** | OPTIONAL | Post-fix verification + resolution section |
| 15 | **Footer** | YES | Source task, date, auditor, files audited, validation method, report path |

### 3.3 Verdict Format

| Verdict | Symbol | When |
|---|---|---|
| PASS | green check icon | All criteria satisfied, no blocking findings |
| PASS (non-blocking) | green check + notes | All pass, minor caveats documented |
| PASS (re-audit) | green check after warning | Initial NEEDS REVIEW, issues fixed, re-verified |
| NEEDS REVIEW | yellow warning | Findings exist that should be resolved |
| FAIL | red cross | Step cannot be marked complete |

### 3.4 Auditor Report Footer Format

`markdown
## Footer

| Field | Value |
|---|---|
| **Source task** | AGENTS.md v2.1 update - evidence gate |
| **Date** | 2026-06-01 |
| **Auditor** | Guinevere (independent gate) |
| **Files audited** | N (list types) |
| **Validation method** | File-based read audit + grep pattern scan + cross-reference check |
| **Report path** | audit-reports/agents-md-update-v3/agents-md-v2.1-auditor-report.md |
| **Next action** | (what operator should do next) |
`

---
## 4. Research Report Patterns

### 4.1 Naming Convention

`
research-reports/<topic>/<description>.md
`

Existing AGENTS.md research reports:
| Path | Purpose |
|---|---|
| research-reports/agents-md-update/workflow-gates-audit.md | Gate-by-gate workflow audit |
| research-reports/agents-md-update/stale-reference-audit.md | Stale reference detection |

### 4.2 Research Report Schema (Workflow-Gates style)

| # | Section | Used In |
|---|---|---|
| 1 | **Header** | Both |
| 2 | **Gate-by-gate** or **Finding-by-finding** breakdown | Workflow-gates: 10 gates; Stale-refs: 4 findings |
| 3 | **Boundary Compliance** | Both (checklist table) |
| 4 | **Summary Table** | Both (verdict + action required) |
| 5 | **Footer** | Both |

---

## 5. Version Table Wording Convention

### 5.1 AGENTS.md Footer Version Table

Current AGENTS.md v2.0 uses this footer format:

`markdown
## Section 13 Footer

### Versioning

| Version | Date | Author | Changes |
|---|---|---|---|
| 2.0 | 2026-05-31 | Faiz + Guinevere | Full rewrite following Aizanta Future template structure. |
| 1.0 | 2026-05-30 | Hephaestus / Guinevere | Initial Guinevere project operating contract. |

### Maintenance

- Update when new Guinevere doc or ADR is added.
- ...

### Operator Sign-Off

Approved by Faiz via session instruction.
`

### 5.2 Evidence File Version Table Wording

Evidence files use a simpler version table at the bottom (when versioned):

`markdown
| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere | Initial evidence report for ... |
`

### 5.3 Style Rules Observed

- **Date format**: ISO YYYY-MM-DD consistently.
- **Author field**: Uses operator name or agent name + role (e.g., Faiz + Guinevere, Guinevere, Hephaestus / Guinevere).
- **Changes field**: Detailed summary in complete sentences. Past tense. Starts with action verb (e.g., Full rewrite, Initial creation).
- **No emoji in version tables.**
- **Version increment**: v1.0 for new, v1.1 for minor changes, v2.0 for major rewrites.
- **Maintenance bullets**: dash prefix. Present tense for rules, future tense for planned actions.

---

## 6. Path Conventions Summary for AGENTS.md v2.1 Update

| Artifact | Recommended Path | Convention Source |
|---|---|---|
| Verification evidence | docs/setup-evidence/agents-md-update-v3/verification.md | Precedent: docs/setup-evidence/agents-md-update/verification.md |
| Auditor report | audit-reports/agents-md-update-v3/agents-md-v2.1-auditor-report.md | Precedent: audit-reports/agents-md-update/agents-md-update-auditor-report.md |
| Research report | research-reports/agents-md-update-v3/evidence-audit-patterns.md | Precedent: research-reports/agents-md-update/ |

---

## 7. Recommended Content Outline

### 7.1 Verification.md - docs/setup-evidence/agents-md-update-v3/verification.md

**12 sections** following P2 convention:

1. **What Was Done** - Summary of AGENTS.md v2.1 changes
2. **Files Changed** - Table: Path | Change
3. **Validation Results** - LSP diagnostics, grep checks for stale refs
4. **Evidence Artifacts** - Report paths
5. **Doc-Sync Impact** - PROGRESS.md, CHECKLIST.md, StepPrompts.md (likely N/A)
6. **Boundary Compliance** - Y4/Y5/Y6, consent, surveillance, HARD STOP, secrets
7. **Rollback / Re-run Safety** - Git revert AGENTS.md
8. **Design Decisions / Caveats** - Why specific changes were made
9. **Auditor Gate** - Status: Pending; expected path
10. **Security Scan** - Token regex on AGENTS.md
11. **Acceptance Criteria Mapping** - Requirements driving the update
12. **Footer** - Source task, date, implementer, validation method

### 7.2 Auditor Report - audit-reports/agents-md-update-v3/agents-md-v2.1-auditor-report.md

**13 sections** following P2 auditor convention:

1. **Header** - Step, Auditor, Date, Method, Verdict
2. **Files Audited** - AGENTS.md + evidence + research reports
3. **Acceptance Criteria Check** - Table: Criterion | Expected | Actual | Verdict
4. **Evidence File Inventory** - Existence + content validity of verification.md
5. **Secret Hygiene** - Token regex, age key, API key patterns
6. **Code Quality / Stale Reference Scan** - Grep for known stale patterns
7. **Cross-Reference Validation** - Internal doc links, ADR references
8. **Boundary Compliance** - Y4 baseline preserved, Y6 prohibited, HARD STOP intact
9. **Auditor Recommendations** - Any findings with severity + action
10. **Diagnostics Check** - LSP on AGENTS.md and verification.md
11. **Rollback Safety** - Rollback via git revert
12. **Verdict Summary** - Final PASS/NEEDS REVIEW/FAIL
13. **Footer** - Source, date, auditor, method, report path

---
## 8. Key Constraints to Follow

1. **Evidence path**: docs/setup-evidence/agents-md-update-v3/verification.md (not evidence/ or docs/setup-evidence/agents-md-update/)
2. **Auditor path**: audit-reports/agents-md-update-v3/agents-md-v2.1-auditor-report.md (following topic-based convention, not per-step prefix)
3. **Footer**: Every evidence and auditor file must end with a ## Footer section
4. **Version table**: If versioned, use the exact table format from section 5.2
5. **Header table**: Use the | Field | Value | table format for verification.md header metadata
6. **No secrets**: Evidence must never contain tokens, API keys, DB passwords, or SOPS/age private keys
7. **ISO dates**: All dates in YYYY-MM-DD format
8. **Boundary compliance**: Mandatory section in both verification.md and auditor report

---

## 9. Source References

| Source | Used For | Path |
|---|---|---|
| P2 verification.md | 12-section schema | docs/setup-evidence/P2/STEP-P2-010/verification.md |
| P1 evidence.md | 10-section schema | docs/setup-evidence/P1/STEP-P1-016/evidence.md |
| Previous AGENTS verification.md | Topic-based template | docs/setup-evidence/agents-md-update/verification.md |
| Caveats resolution | Topic-based template | docs/setup-evidence/caveats-resolution/verification.md |
| P2-009 auditor report | Auditor report template | audit-reports/P2/STEP-P2-009/step-p2-009-auditor-report.md |
| P0-004 auditor report | Auditor report template | audit-reports/P0/STEP-P0-004/step-p0-004-auditor-report.md |
| Previous agents contract audit | Auditor report template | audit-reports/2026-05-30-agents-contract-audit.md |
| Auditor pattern research | P1 auditor guidance | research-reports/P1/auditor-report-patterns.md |
| Evidence pattern research | P1 evidence guidance | research-reports/P1/evidence-patterns.md |
| Enterprise reorg evidence | Version table wording | evidence/reorg/2026-05-31-enterprise-folder-reorg.md |
| AGENTS.md v2.0 | Version table wording | AGENTS.md Section 13 Footer |

---

## Footer

| Field | Value |
|---|---|
| Source task | Research: evidence/audit patterns for AGENTS.md v2.1 update |
| Date | 2026-06-01 |
| Implementer | Guinevere (parent) |
| Validation method | File read + grep/glob inventory of 200+ evidence/audit/research files |
| Files analyzed | 25+ (10 verification.md/evidence.md + 5 auditor reports + 5 research reports + 5 evidence/ directory files) |
| Report path | research-reports/agents-md-update-v3/evidence-audit-patterns.md |
| Next action | Parent should read this report before updating AGENTS.md, then create verification.md and spawn auditor gate |
