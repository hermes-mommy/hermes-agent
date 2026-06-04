# Tier 1 Step Prompt Template — Research Report

**Research Date:** 2026-06-04
**Source File:** stepprompts/StepPrompts.md (38,979 lines)
**File Version:** 1.1 (Updated 2026-06-03)
**Research Scope:** Canonical 10-section Tier 1 template + P9-P13 examples

---

## 1. Canonical Tier 1 Step Prompt Template

Every step in the StepPrompts.md file follows a **10-section canonical template**. This template is used consistently across all 316+ steps (MVP P0-P8, Stabilization P9-P10, Expansion P11-P13).

### Template Structure

\\\markdown
### Step P[N]-[MMM]: Step Title

**Type:** [Infrastructure|Application|Security|...]
**Status:** [Not Started|In Progress|Completed|... ]
**Risk:** [Low|Medium|High]
**Git Commit:** \eat(PN): pending\

**Goal:** [One-sentence description of what this step accomplishes.]
**Dependencies:** [Prerequisite steps or conditions.]
**Cost Impact:** [/month or /month + brief note]
**ADR References:** [ADR-XXX, ADR-YYY]
**Acceptance Criteria:** [AC-XXX, AC-YYY]
**Estimated Time:** [X hours]

#### Context

[Multi-paragraph description providing background, rationale, architecture context,
design decisions, and why this step exists. Includes relevant codebase state, existing
infrastructure references, and what will exist after this step completes.]

#### Pre-flight Checks
- [ ] [Check condition 1]
- [ ] [Check condition 2]
- [ ] [Check condition N]

#### Commands

\\\ash
# Numbered, commented bash commands
# 1. ...
command1

# 2. ...
command2
\\\

#### Verification
- [ ] [Verification check 1]
- [ ] [Verification check 2]
- [ ] [Verification check N]

#### Evidence
- \docs/setup-evidence/PN/STEP-PN-MMM/artifact-name.md\: Description
- \docs/setup-evidence/PN/STEP-PN-MMM/another-artifact.txt\: Description

#### Rollback

\\\ash
# Rollback commands to undo changes made in this step
command1
command2
\\\

#### Troubleshooting
- **Issue:** [Description of potential problem]
  - **Solution:** [How to resolve it]
- **Issue:** [Another potential problem]
  - **Solution:** [How to resolve it]

#### Notes
- [Design decision, cross-reference, constraint, or important context]
- [Another note]
- [Shared VPS constraint note if applicable]

---
\\\

### The 10 Sections (Numbered)

| # | Section | Heading Format | Required | Notes |
|---|---------|---------------|----------|-------|
| 1 | **Header** | \### Step P[N]-[MMM]: Title\ + 4 metadata fields | Yes | Type, Status, Risk, Git Commit |
| 2 | **Goal** | \**Goal:**\ + 5 inline metadata fields | Yes | Dependencies, Cost Impact, ADR References, Acceptance Criteria, Estimated Time |
| 3 | **Context** | \#### Context\ | Yes | Multi-paragraph narrative |
| 4 | **Pre-flight Checks** | \#### Pre-flight Checks\ or \#### Pre-flight Checklist\ | Yes | Checkbox list |
| 5 | **Implementation Commands** | \#### Commands\ or \#### Implementation Commands\ | Yes | Bash code block with numbered comments |
| 6 | **Verification** | \#### Verification\ | Yes | Checkbox list |
| 7 | **Evidence** | \#### Evidence\ or \#### Evidence Requirements\ | Yes | File paths with descriptions |
| 8 | **Rollback** | \#### Rollback\ or \#### Rollback Plan\ | Yes | Bash code block |
| 9 | **Troubleshooting** | \#### Troubleshooting\ | Yes | Issue/Solution pairs |
| 10 | **Notes** | \#### Notes\ | Yes | Design decisions, cross-references, constraints |

### Section Heading Variations Found

Across 38,979 lines, the following heading variations exist:

| Canonical Name | Variations Found |
|---------------|-----------------|
| Pre-flight Checks | \#### Pre-flight Checks\, \#### Pre-flight Checklist\ |
| Implementation Commands | \#### Commands\, \#### Implementation Commands\ |
| Evidence | \#### Evidence\, \#### Evidence Requirements\ |
| Rollback | \#### Rollback\, \#### Rollback Plan\ |
| Troubleshooting | \#### Troubleshooting\ (consistent) |
| Notes | \#### Notes\ (consistent) |

---

## 2. Representative Examples by Phase

### 2.1 P0-000: VPS Audit (Lines 168-291) — EARLIEST EXAMPLE

**Type:** Infrastructure | **Status:** Completed | **Risk:** Low

This is the very first step in the document and establishes the template pattern. It is an audit-only (read-only) step with minimal commands and rollback. Key characteristics:
- Simple, concise Context (1 paragraph)
- 3 Pre-flight Checks
- ~15 numbered bash commands (system audit commands)
- 5 Verification checkboxes
- 2 Evidence artifacts
- Minimal rollback (echo statement, no system changes)
- 3 Troubleshooting entries
- 3 Notes items

### 2.2 P0-001: Create guinevere Linux User (Lines 293-378)

**Type:** Security | **Status:** Completed | **Risk:** High

Shows the template for a security-affecting step with higher risk:
- 3 Pre-flight Checks
- ~10 numbered bash commands (user creation, sudoers, permissions)
- 5 Verification checkboxes
- 3 Evidence artifacts
- Rollback includes user removal and sudoers cleanup
- 3 Troubleshooting entries
- 3 Notes items

### 2.3 P9-001: Financial Data Model + Schema Audit (Lines 7619-7729)

**Type:** Application | **Status:** Not Started | **Risk:** Medium

Shows the template for a code-level application step:
- 6 Pre-flight Checks
- 10 numbered bash commands (schema inspection, migration, CRUD stub creation)
- 7 Verification checkboxes (includes lsp_diagnostics check)
- 4 Evidence artifacts
- Rollback includes alembic downgrade and file removal
- 4 Troubleshooting entries
- 7 Notes items (includes shared VPS constraints)

### 2.4 P10-001: Security Audit (Lines 11533-11715)

**Type:** Security | **Status:** Not Started | **Risk:** High

Shows the template for a comprehensive security scanning step:
- 8 Pre-flight Checks (tool availability checks)
- 12 numbered command groups (nmap, lynis, bandit, semgrep, trivy, pip-audit, Tailscale, UFW, secrets grep, file permissions, findings report)
- 11 Verification checkboxes
- 14 Evidence artifacts
- Read-only rollback (cleanup scan artifacts only)
- 6 Troubleshooting entries
- 7 Notes items (includes shared VPS Aizanta exception notes)

### 2.5 P11-001: Neonize Dependency Setup (Lines 19505-20008)

**Type:** Application | **Status:** Not Started | **Risk:** Medium

Shows the template for a library/dependency installation step:
- 10 Pre-flight Checks
- 8+ numbered commands (import verification, pip install, directory creation)
- Verification and Evidence sections follow canonical format
- Includes ADR revision note (ADR-022 from Baileys to Neonize)

### 2.6 P12-001: GCP Project + API Enablement (Lines 25854-26037)

**Type:** Infrastructure | **Status:** Not Started | **Risk:** Low

Notable variation: Uses \#### Pre-flight Checklist\ and \#### Implementation Commands\ instead of the shorter forms. Also uses \#### Evidence Requirements\ and \#### Rollback Plan\. This is the most explicitly labeled variant.

**Key characteristics:**
- 9 Pre-flight Checks
- 16 numbered commands (gcloud project creation, API enablement, IAM, SOPS encryption, Pub/Sub)
- 10 Verification checkboxes
- 6 Evidence artifacts
- 7-step Rollback Plan (including irreversible project deletion, commented out)
- 6 Troubleshooting entries
- 7 Notes items (includes cross-references to P12-002 and P12-005)

### 2.7 P13-001: S3 Queue Setup (Lines 34330-34514)

**Type:** Infrastructure | **Status:** Not Started | **Risk:** Medium

Shows the template with additional metadata fields not present in all steps:
\**Phase:** P13\
\**Integration:** whatsapp-adjacent expansion input pipeline\
\**Default Language:** English\
\**LLM Defaults:** Gemini Flash primary; Gemini Pro fallback\

**Key characteristics:**
- 8 Pre-flight Checks
- Multi-section commands (S3 prefix creation, IAM policy, lifecycle rules, SOPS storage)
- Canonical Verification, Evidence, Rollback, Troubleshooting, Notes sections

---

## 3. Template Consistency Analysis

### Consistent Elements (All Steps)
- \### Step P[N]-[MMM]: Title\ heading format
- 4 header metadata fields: Type, Status, Risk, Git Commit
- 5 inline metadata fields: Goal, Dependencies, Cost Impact, ADR References, Acceptance Criteria
- \#### Context\ with multi-paragraph narrative
- Checkbox-style Pre-flight Checks
- Numbered bash Commands in code blocks
- Checkbox-style Verification
- File-path Evidence artifacts
- Bash Rollback commands
- Issue/Solution Troubleshooting pairs
- Bullet-point Notes
- \---\ separator between steps

### Variable Elements
- Estimated Time: Always present, but P13-001 adds extra fields (Phase, Integration, Language, LLM Defaults)
- Pre-flight Checks vs Pre-flight Checklist: Both used interchangeably
- Commands vs Implementation Commands: Both used interchangeably
- Evidence vs Evidence Requirements: Both used interchangeably
- Rollback vs Rollback Plan: Both used interchangeably

### File Statistics
- **Total lines:** 38,979
- **Total phases:** 23 (P0-P22)
- **Total steps defined:** 202 (MVP) + 34 (Stabilization P9-P10) + 80 (Expansion P11-P13) + TBD (P14-P22) = 316+ defined
- **Steps with full 10-section format:** All defined steps (P0-P13)
- **P14-P22:** TBD (not yet written, would follow same template)

---

## 4. Usage Notes for P14+ Step Creation

When creating new Tier 1 steps for P14 (Wearable/Xiaomi Watch) or later phases:

1. **Follow the canonical 10-section template** exactly
2. **Use consistent heading names**: \#### Context\, \#### Pre-flight Checks\, \#### Commands\, \#### Verification\, \#### Evidence\, \#### Rollback\, \#### Troubleshooting\, \#### Notes\
3. **Evidence paths**: Use \docs/setup-evidence/P14/STEP-P14-MMM/\ pattern
4. **Git commit prefix**: Use \eat(P14):\ convention
5. **Shared VPS notes**: Include if infrastructure is affected; otherwise note \"minimal shared VPS impact\"
6. **ADR references**: Create new ADRs if needed; reference existing ones
7. **Acceptance criteria**: Define AC codes for the new phase (e.g., AC-WEAR-001)
8. **Step separator**: Always end with \---\ before the next step

---

## 5. Key File Locations

| Item | Location |
|------|----------|
| Step Prompts file | \C:\\Users\\faizz\\guinevere\\stepprompts\\StepPrompts.md\ |
| Backup file | \C:\\Users\\faizz\\guinevere\\stepprompts\\StepPrompts.md.bak\ |
| Evidence root | \docs/setup-evidence/\ |
| Research reports | \esearch-reports/\ |
| ADR index | \docs/10-governance/17-ADR_Index_v1.0.md\ |
| AGENTS.md (workflow rules) | \AGENTS.md\ |

---

*Research completed by autonomous scan of StepPrompts.md (38,979 lines).*
*Report location: research-reports/p14-expansion/template-research.md*
