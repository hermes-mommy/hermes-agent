# Research: Evidence & Audit Report Style for AGENTS.md v2.1 Refactor

| Field | Value |
|---|---|
| **Research Agent** | Explore (Guinevere parent) |
| **Date** | 2026-06-01 |
| **Scope** | Local `docs/setup-evidence/`, `audit-reports/`, `evidence/`, `research-reports/agents-md-update*/` patterns |
| **Verdict** | Canonical schemas confirmed: 12-section verification.md, 13-15 section auditor report. Path convention: `docs/setup-evidence/agents-md-refactor/verification.md` and `audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md`. Markdown table caveats documented below. |

---

## 1. Evidence Directory Structure Convention (Confirmed via Fresh Scan)

### 1.1 Primary Implementation Evidence: `docs/setup-evidence/`

This is the **active** evidence directory. Two naming conventions confirmed from 100+ files inventoried:

**Phase P0-P1 (early):** Files named `evidence.md` using 10-12 section schema:
```
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
  evidence.md               ← 10-12 sections
  p{N}-{XXX}-summary.md     ← Step summary
```

**Phase P2 (later evolution):** Files renamed to `verification.md` with 12-13 section schema:
```
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
  verification.md           ← 12-13 sections (canonical for current use)
  p{N}-{XXX}-implementation-summary.md
```

**Topic-based (non-step, like AGENTS.md updates):**
```
docs/setup-evidence/<topic>/
  verification.md           ← 12-section topic schema
```

**Existing topic-based examples confirmed:**
| Path | Pattern |
|---|---|
| `docs/setup-evidence/agents-md-update/verification.md` | 12 sections, topic header table |
| `docs/setup-evidence/caveats-resolution/verification.md` | 12 sections |
| `docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md` | Standalone topic file |

### 1.2 Root `evidence/` Directory (Historical Only - NOT for Active Steps)

Confirmed: `evidence/reorg/`, `evidence/finops/`, `evidence/canonicalization/`, `evidence/document-generation/`, `evidence/adr-generation/` - historical bulk records only. **Do not use for AGENTS.md v2.1 active step evidence.**

### 1.3 Critical Distinction

> For AGENTS.md v2.1, use `docs/setup-evidence/agents-md-refactor/` (NOT `evidence/`). Active per-step verification goes in `docs/setup-evidence/`.

---

## 2. Verification.md - Canonical 12-Section Schema

Based on fresh read of P2-012 verification.md (295 lines), agents-md-update verification.md (125 lines), and the existing research report from agents-md-update-v3:

### Header Format (Topic-based, confirmed from agents-md-update/verification.md)

```markdown
# <Topic> Verification

| Field | Value |
|---|---|
| Scope | `AGENTS.md` v2.1 refactor - description of scope |
| Date | 2026-06-01 |
| Implementer | Guinevere |
| Trigger | Faiz directive: ... |
| Evidence path | `docs/setup-evidence/<scope>/verification.md` |
```

### 12 Required Sections

| # | Section | Required | Notes |
|---|---|---|---|
| 1 | **What Was Done** | YES | High-level summary + approach. List changes made with bullet points. |
| 2 | **Files Changed** | YES | Table: Path | Change. Include the evidence file itself. |
| 3 | **Validation Results** | YES | LSP diagnostics, grep checks, deterministic checks. Table with PASS/FAIL. |
| 4 | **Evidence Artifacts** | YES | Table: Artifact | Path | Purpose/Status |
| 5 | **Doc-Sync Impact** | YES | PROGRESS.md, CHECKLIST.md, StepPrompts.md - or explicit N/A |
| 6 | **Boundary Compliance** | YES | Table: Check | Status. Persona drift, consent, surveillance, Y4/Y5/Y6, HARD STOP, distress, secrets. |
| 7 | **Rollback / Re-run Safety** | YES | Rollback path (git revert), idempotency notes |
| 8 | **Design Decisions / Caveats** | YES | Why choices made, deferred items, accepted false-positives |
| 9 | **Auditor Gate** | YES | Status: Pending; expected report path |
| 10 | **Security Scan** | OPTIONAL | Token regex scan results (include if files changed) |
| 11 | **Acceptance Criteria Mapping** | OPTIONAL | Table: Requirement | Status |
| 12 | **Footer** | YES | Source task, date, implementer, validation method |

### Footer Format (Confirmed from P2-012 and agents-md-update)

Two formats observed. P2-012 uses table footer:
```markdown
## 12. Footer

| Field | Value |
|---|---|
| **Source task** | <description> |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (implementation sub-agent) |
| **Validation method** | <method> |
| **Secret handling** | <statement> |
| **Boundary compliance** | <checklist> |
```

agents-md-update uses simpler text footer:
```markdown
## 12. Footer

Source task: <description>.
Validation method: <method>.
```

### Recommended Evidence Structure for `docs/setup-evidence/agents-md-refactor/verification.md`

The `verification.md` file should follow the 12-section schema exactly:
1. What Was Done - summary of AGENTS.md v2.1 refactor changes
2. Files Changed - table: `AGENTS.md`, this `verification.md`
3. Validation Results - LSP diagnostics on AGENTS.md, grep checks
4. Evidence Artifacts - report paths (research reports, audit reports)
5. Doc-Sync Impact - PROGRESS.md (likely N/A for doc-only refactor)
6. Boundary Compliance - Y4/Y5/Y6, consent, surveillance, HARD STOP, secrets
7. Rollback / Re-run Safety - git revert AGENTS.md
8. Design Decisions / Caveats - why specific changes made
9. Auditor Gate - Status: Pending; path: `audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md`
10. Security Scan - token regex on AGENTS.md
11. Acceptance Criteria Mapping - requirements driving the update
12. Footer - source task, date, implementer, validation method

---

## 3. Auditor Report - Canonical Schema (13-15 Sections)

### 3.1 Naming Convention (Confirmed)

**Topic-based pattern (for non-step audits like AGENTS.md):**
`
audit-reports/<topic>/<topic>-auditor-report.md
`

**Confirmed existing examples:**
| Path | Description |
|---|---|
| udit-reports/agents-md-update/agents-md-update-auditor-report.md | Previous AGENTS.md auditor (329 lines, 11 sections) |
| udit-reports/caveats-resolution/caveats-resolution-auditor-report.md | Caveats resolution auditor |
| udit-reports/2026-05-30-agents-contract-audit.md | Root-level AGENTS contract audit |

### 3.2 Recommended Report Path

`
audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md
`

### 3.3 Recommended 13-Section Schema

Based on P2 auditor reports (P2-010, P2-009) and the previous agents-md-update auditor:

| # | Section | Required | Notes |
|---|---|---|---|
| 1 | **Header** | YES | Step, Auditor, Date, Method, Verdict |
| 2 | **Files Audited** | YES | Table: # or Pipe or Path or Pipe or Type (evidence/source/report) |
| 3 | **Acceptance Criteria Check** | YES | Table: # or Pipe or Criterion or Pipe or Expected or Pipe or Actual or Pipe or Verdict |
| 4 | **Evidence File Inventory** | YES | Table: File or Pipe or Exists or Pipe or Content Verified or Pipe or Status |
| 5 | **Secret Hygiene Verification** | YES | Grep for tokens, API keys, passwords |
| 6 | **Code Quality / Stale Reference Scan** | YES | Grep for stale patterns, unsafe patterns |
| 7 | **Cross-Reference Validation** | OPTIONAL | Table: Reference or Pipe or Source File or Pipe or Target or Pipe or Valid? |
| 8 | **Boundary Compliance Verification** | YES | Table: Boundary or Pipe or Evidence Says or Pipe or Audit Verification or Pipe or Verdict |
| 9 | **Auditor Recommendations** | YES | Table: # or Pipe or Recommendation or Pipe or Severity or Pipe or Action Required |
| 10 | **Diagnostics Check** | YES | LSP diagnostics on all changed files |
| 11 | **Rollback Safety Check** | YES | Is rollback path documented and safe? |
| 12 | **Verdict Summary** | YES | Table: Area or Pipe or Result. Final PASS/NEEDS REVIEW/FAIL |
| 13 | **Footer** | YES | Source task, date, auditor, files audited, validation method, report path |

### 3.4 Verdict Format (Confirmed)

| Verdict | When |
|---|---|
| PASS | All criteria satisfied, no blocking findings |
| PASS with notes | All pass, minor caveats documented |
| NEEDS REVIEW | Findings exist that should be resolved |
| FAIL | Step cannot be marked complete |

### 3.5 Auditor Report Footer (from agents-md-update pattern)

`
## [13]. Footer

| Field | Value |
|---|---|
| **Source task** | AGENTS.md v2.1 refactor - auditor gate |
| **Date** | 2026-06-01 |
| **Auditor** | Guinevere (independent gate) |
| **Files audited** | N (list types) |
| **Validation method** | File-based read audit + grep pattern scan + cross-reference check |
| **Report path** | audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md |
| **Next action** | (what operator should do next) |
`

---

## 4. Exact GREP Verification List for AGENTS.md v2.1 Refactor

Based on the previous agents-md-update verification checks and the current AGENTS.md content:

### 4.1 Stale Reference Verification (from agents-md-update precedent)

| Check | Grep Pattern | Expected Result |
|---|---|---|
| No stale Y1 baseline | grep -n "Y1 baseline" AGENTS.md | No match (should be Y4) |
| No stale OpenRouter refs | grep -n "OpenRouter" AGENTS.md | No match (should be 9Router) |
| No stale Ollama refs | grep -n "Ollama" AGENTS.md | No match (ADR-028 superseded) |
| load_skills mandate present | grep -n "load_skills" AGENTS.md | Multiple matches |
| run_in_background mandate present | grep -n "run_in_background" AGENTS.md | Multiple matches |
| WORKFLOW GATES section present | grep -n "WORKFLOW GATES" AGENTS.md | Match in section 14 |
| AGENTS.md first-read rule | grep -n "AGENTS.md.*first" AGENTS.md | Match in section 1 and section 3 |
| Planner todo sync gate | grep -n "todo.*sync" AGENTS.md | Multiple matches |

### 4.2 Anti-Pattern Verification (from P2 verification precedent)

| Check | Grep Pattern | Expected Result |
|---|---|---|
| No as any | grep -n "as any" AGENTS.md | No match (code tool listing may have) |
| No type: ignore | grep -n "type: ignore" AGENTS.md | No match |
| No except: pass | grep -n "except: pass" AGENTS.md | No match |
| Y6 prohibited | grep -n "Y6" AGENTS.md | Y6 should only appear in prohibitions |
| HARD STOP referenced | grep -n "HARD STOP" AGENTS.md | Present in sections 0, 5, 6 |
| Consent/surveillance boundary | grep -n "consent" AGENTS.md | Present in multiple sections |

### 4.3 Token/Security Scan (from P2 verification precedent)

| Check | Grep Pattern | Expected Result |
|---|---|---|
| Discord bot token pattern | None should match | No secrets in AGENTS.md |
| Generic API key pattern | None should match | No secrets in AGENTS.md |
| age private key | None should match | No secrets in AGENTS.md |

---

## 5. Markdown Table Caveats for AGENTS.md Refactor

### 5.1 Pipe Table Structural Rules

From observing the existing AGENTS.md (689 lines) and 200+ evidence/audit files:

1. **Header pipe count must match content pipe count.** Every row in a pipe table must have the same number of pipe separators. Mismatches break rendering.

2. **Escaping pipe inside cells.** If a cell contains a literal pipe character, it must be escaped with backslash or HTML entity.

3. **Avoid backticks inside complex table cells.** Backtick-delimited inline code inside pipe table cells can break preview. Use plain text or separate code blocks outside tables.

4. **Long cell content must stay on one line.** Pipe tables auto-wrap visually but source line must not break in the middle of a table row.

5. **Colon alignment.** Use |---|---|---| for consistent left-aligned columns.

6. **Empty cells.** Use a space or explicit dash or N/A marker for clarity.

### 5.2 AGENTS.md-Specific Table Risks

The current AGENTS.md has multiple tables (tool selection section 12, version table section 13, reference tables section 8). During refactoring:

- **Version table**: Must not wrap the "Changes" column across lines. Flagged as medium risk.
- **Tool Selection table**: Contains backtick code references. Ensure no pipe characters appear inside code references.
- **Reference tables**: Long document paths checked for proper escaping.

### 5.3 Safe Table Pattern from agents-md-update/verification.md

`
| Check | Result |
|---|---|
| LSP diagnostics on AGENTS.md | PASS - no diagnostics found |
| Grep Ollama in AGENTS.md | PASS - no stale matches |
`

Backticks inside pipe table cells for code references are **safe to use** (confirmed in 45+ table instances).

---

## 6. Footer and Version Table Wording Conventions (Confirmed)

### 6.1 AGENTS.md Footer Version Table

Current v2.0 format:
`
| Version | Date | Author | Changes |
|---|---|---|---|
| 2.0 | 2026-05-31 | Faiz + Guinevere | Full rewrite following Aizanta Future template structure. |
| 1.0 | 2026-05-30 | Hephaestus / Guinevere | Initial Guinevere project operating contract. |
`

### 6.2 Evidence File Version Convention

When versioned, evidence files use:
`
| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-05-31 | Guinevere | Initial evidence report for ... |
`

### 6.3 Style Rules Observed (Across 200+ Files)

- **Date format**: ISO YYYY-MM-DD consistently across all files.
- **Author field**: Uses operator name or agent name plus role.
- **Changes field**: Detailed summary, past tense, starts with action verb.
- **No emoji in version tables** (emoji only used in non-table content).
- **Version increment**: v1.0 for new, v1.1 for minor, v2.0 for major.
- **Maintenance bullets**: Dash prefix, present tense for rules.

---

## 7. Path Conventions Summary for AGENTS.md v2.1 Refactor

| Artifact | Recommended Path | Convention Source |
|---|---|---|
| Verification evidence | docs/setup-evidence/agents-md-refactor/verification.md | Precedent: docs/setup-evidence/agents-md-update/verification.md |
| Auditor report | audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md | Precedent: audit-reports/agents-md-update/agents-md-update-auditor-report.md |
| Research report | research-reports/agents-md-refactor/evidence-audit-style.md | Precedent: research-reports/agents-md-update-v3/evidence-audit-patterns.md |

---

## 8. Key Constraints for AGENTS.md v2.1 Refactor

1. **Evidence path**: docs/setup-evidence/agents-md-refactor/verification.md (not evidence/).
2. **Auditor path**: audit-reports/agents-md-refactor/agents-md-refactor-auditor-report.md.
3. **Footer**: Every evidence and auditor file must end with a ## Footer section.
4. **Version table**: Use the exact 4-column table format.
5. **Header table**: Use Field | Value format for verification.md metadata.
6. **No secrets**: Evidence must never contain tokens, API keys, DB passwords, or SOPS/age private keys.
7. **ISO dates**: All dates in YYYY-MM-DD format.
8. **Boundary compliance**: Mandatory section in both verification.md and auditor report.
9. **12-section schema**: verification.md must have all 12 sections.
10. **Auditor report** must include secret hygiene scan, stale reference scan, and cross-reference validation.

---

## 9. Source References

| Source | Used For | Path |
|---|---|---|
| P2-012 verification.md | 12-section schema + footer format | docs/setup-evidence/P2/STEP-P2-012/verification.md |
| agents-md-update verification.md | Topic-based template + grep list | docs/setup-evidence/agents-md-update/verification.md |
| agents-md-update auditor report | Auditor report template + verdict format | audit-reports/agents-md-update/agents-md-update-auditor-report.md |
| 2026-05-30 agents contract audit | Auditor report template | audit-reports/2026-05-30-agents-contract-audit.md |
| evidence-audit-patterns.md (v3) | Schema reference | research-reports/agents-md-update-v3/evidence-audit-patterns.md |
| evidence-patterns.md (P1) | 12-section schema | research-reports/P1/evidence-patterns.md |
| agents-md-insertion-map.md | Markdown table risks | research-reports/agents-md-update-v3/agents-md-insertion-map.md |
| AGENTS.md v2.0 | Version table wording | AGENTS.md |

---

## Footer

| Field | Value |
|---|---|
| **Source task** | Research: evidence/audit style patterns for AGENTS.md v2.1 refactor |
| **Date** | 2026-06-01 |
| **Implementer** | Guinevere (parent) |
| **Validation method** | File read + grep/glob inventory of 200+ evidence/audit/research files across P0, P1, P2, agents-md-update, and agents-md-update-v3 |
| **Files analyzed** | 15+ (verification.md, auditor reports, research reports, AGENTS.md) |
| **Report path** | research-reports/agents-md-refactor/evidence-audit-style.md |
| **Next action** | Parent should read this report before refactoring AGENTS.md, then create verification.md and spawn auditor gate |
