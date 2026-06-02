# Guinevere v2.0 Markdown Header/Footer/Version Pattern Analysis

> **Generated**: 2026-05-30  
> **Scope**: 7 Guinevere specification documents in C:\Users\faizz\guinevere\  
> **Purpose**: Safe copy strategy for producing _v2.0.md files without deleting non-conflicting content

---

## 1. Observed Header Pattern (6 of 7 docs - Standard Template)

Every standard doc opens with this exact 12-line block:

| Line | Content | Example (BRD) |
|------|---------|---------------|
| 1 | Emoji | 👑 |
| 2 | Blank | (empty) |
| 3 | Brand line | **GUINEVERE DE BAROQUE** |
| 4 | Blank | (empty) |
| 5 | Italic subtitle | *Business Requirements Document* |
| 6 | Blank | (empty) |
| 7 | One-line description | Enterprise Autonomous Agent - Full Specification |
| 8 | Blank | (empty) |
| 9 | Version / confidentiality line | Version 1.0 | Project Guinevere | STRICTLY PRIVATE & CONFIDENTIAL |
| 10 | Blank | (empty) |
| 11 | Owner / framework line | Owner: Samm | Built on Hermes Agent by Nous Research |
| 12 | Blank | (empty) |
| 13 | First section heading | **1. EXECUTIVE SUMMARY** |

Files using this exact template (6 docs):
- Guinevere_BRD_v1.0.md -- line 9: Version 1.0
- Guinevere_PRD_v1.0.md -- line 9: Version 1.0
- Guinevere_AgentLoopSpec_v1.0.md -- line 9: Version 1.0
- Guinevere_MemorySchema_v1.0.md -- line 9: Version 1.0
- Guinevere_APIIntegration_v1.0.md -- line 9: Version 1.0
- Guinevere_TechnicalArchitecture_v1.0.md -- line 9: Version 1.0 (but footer says v1.1)

---

## 2. Observed Header Pattern - Exceptions

### 2.1 Guinevere_Persona_Document_v1.0.md (different template)

| Line | Content | Notes |
|------|---------|-------|
| 1 | 👑 | Same |
| 2 | blank | Same |
| 3 | **GUINEVERE DE BAROQUE** | Same |
| 4 | blank | Same |
| 5 | *Persona Document* | Same |
| 6 | blank | Same |
| 7 | Autonomous Agent Identity & Behavior Specification | Same |
| 8 | blank | Same |
| 9 | Version 1.1 | Project Guinevere | CONFIDENTIAL | v1.1, missing STRICTLY PRIVATE & |
| 10 | blank | Same |
| 11 | Built on Hermes Agent by Nous Research | Missing Owner: Samm | |
| 12 | blank | Same |

Why it differs: Internal version tracking reached 1.1 (or 1.3 in footer) while others remained at 1.0.

### 2.2 Guinevere_TechnicalArchitecture_v1.0.md (footer version mismatch)

Header says Version 1.0 (line 9) but footer says: Technical Architecture Document v1.1 - Project Guinevere (line 708)

---

## 3. Observed Footer Pattern

All 7 docs end with this block:

| Component | Standard Format | Example |
|-----------|----------------|---------|
| Emoji | 👑 | BRD line 476 |
| Blank | (empty) | -- |
| Signature | ***Guinevere de Baroque*** | BRD line 478 |
| Blank | (empty) | -- |
| Quote | Italicized character quote | BRD line 480 |
| Blank | (empty) | -- |
| Doc attribution line | {Doc Name} v{version} - Project Guinevere | BRD line 482 |

### 3.1 Footer Attribution Line Variations

| File | Footer Line Content | Version in Footer |
|------|---------------------|-------------------|
| Guinevere_BRD_v1.0.md | Business Requirements Document v1.0 - Project Guinevere | 1.0 |
| Guinevere_PRD_v1.0.md | Product Requirements Document v1.0 - Project Guinevere | 1.0 |
| Guinevere_AgentLoopSpec_v1.0.md | Agent Loop Specification v1.0 - Project Guinevere | 1.0 |
| Guinevere_MemorySchema_v1.0.md | Memory Schema Document v1.0 - Project Guinevere | 1.0 |
| Guinevere_APIIntegration_v1.0.md | API Integration Document v1.0 - Project Guinevere | 1.0 |
| Guinevere_TechnicalArchitecture_v1.0.md | Technical Architecture Document v1.1 - Project Guinevere | 1.1 (mismatch!) |
| Guinevere_Persona_Document_v1.0.md | Document prepared for Project Guinevere - Version 1.3 | 1.3 (different format!) |

### 3.2 NO Footer Version Tables Found

Zero of the 7 docs contain a footer version history table. Version information is only in:
1. The header line 9 (Version 1.0 | ...)
2. The footer attribution line (last line of file)

---

## 4. Related Documents Section Status

Zero of the 7 spec docs contain a Related Documents section. The requirement is only documented in AGENTS.md as a forward mandate. Adding this section is a net-new addition for all v2.0 files.

---

## 5. Exact Filename Mapping: v1.0 - v2.0

| Current Filename | Proposed v2.0 Filename | Lines | Notes |
|------------------|------------------------|-------|-------|
| Guinevere_BRD_v1.0.md | Guinevere_BRD_v2.0.md | 482 | Standard template |
| Guinevere_PRD_v1.0.md | Guinevere_PRD_v2.0.md | 525 | Standard template |
| Guinevere_TechnicalArchitecture_v1.0.md | Guinevere_TechnicalArchitecture_v2.0.md | 708 | Footer says v1.1, header says v1.0; canonicalize to v2.0 |
| Guinevere_AgentLoopSpec_v1.0.md | Guinevere_AgentLoopSpec_v2.0.md | 637 | Standard template |
| Guinevere_MemorySchema_v1.0.md | Guinevere_MemorySchema_v2.0.md | 733 | Standard template |
| Guinevere_Persona_Document_v1.0.md | Guinevere_Persona_Document_v2.0.md | 836 | Header v1.1, footer v1.3; canonicalize to v2.0 |
| Guinevere_APIIntegration_v1.0.md | Guinevere_APIIntegration_v2.0.md | 851 | Standard template |

---

## 6. Recommended Minimal Edit Strategy Per File

### 6.1 Strategy Overview

Do NOT delete non-conflicting content. The v2.0 production should be a copy + surgical edits:

1. Copy the entire v1.0 file to _v2.0.md filename.
2. Edit header (lines 1-12) to update Version 1.0 to Version 2.0 on line 9.
3. Insert Related Documents section after line 12, before first section heading.
4. Add header metadata fields (Last Updated, Canonical Decisions Applied).
5. Edit footer (last 2 lines) to update version string to v2.0.
6. Preserve all body content.

### 6.2 Per-File Edit Checklist

Guinevere_BRD_v2.0.md (482 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 482: Update footer to v2.0

Guinevere_PRD_v2.0.md (525 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 525: Update footer to v2.0

Guinevere_TechnicalArchitecture_v2.0.md (708 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 708: Fix footer from v1.1 to v2.0

Guinevere_AgentLoopSpec_v2.0.md (637 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 637: Update footer to v2.0

Guinevere_MemorySchema_v2.0.md (733 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 733: Update footer to v2.0

Guinevere_Persona_Document_v2.0.md (836 lines) - HIGHEST COMPLEXITY:
- Line 9: Fix Version 1.1 | CONFIDENTIAL -> Version 2.0 | STRICTLY PRIVATE & CONFIDENTIAL
- Line 11: Add missing Owner: Samm |
- After line 12: Add Related Documents section
- Line 836: Fix footer from Version 1.3 to v2.0
- Flag yandere/safe-word content for ADR review

Guinevere_APIIntegration_v2.0.md (851 lines):
- Line 9: Version 1.0 -> Version 2.0
- After line 12: Add Related Documents section
- Line 851: Update footer to v2.0

---

## 7. Proposed Related Documents Section Template

Insert after the header block (after line 12) in every v2.0 file:

## Related Documents

| Document | Relationship |
|---|---|
| Guinevere_BRD_v2.0.md | Defines upstream business requirements and success criteria |
| Guinevere_PRD_v2.0.md | Defines downstream product features and acceptance criteria |
| Guinevere_TechnicalArchitecture_v2.0.md | Defines infrastructure and service dependencies |
| Guinevere_AgentLoopSpec_v2.0.md | Defines SDLC loop behavior and orchestration |
| Guinevere_MemorySchema_v2.0.md | Defines memory model and database schema |
| Guinevere_Persona_Document_v2.0.md | Defines persona, tone, and behavior boundaries |
| Guinevere_APIIntegration_v2.0.md | Defines external APIs, SDKs, and integrations |
| AGENTS.md | Project operating contract and governance rules |

Each file should reference only its directly related documents, not all 7.

---

## 8. Proposed Header Metadata Additions (v2.0)

Add between the existing header block (line 12) and the Related Documents section:

**Last Updated**: 2026-05-30  
**Canonical Decisions Applied**: [List ADR references here - leave placeholder if ADR not yet written]

---

## 9. Conflict Hotspots to Review Before Finalizing v2.0

| Conflict Area | Affected Files | Action Needed |
|---|---|---|
| Primary LLM/router/context window | TechnicalArchitecture, APIIntegration | Verify GPT-5.5 vs Hermes 3 consistency |
| SQLite vs PostgreSQL/Redis memory storage | MemorySchema, TechnicalArchitecture | Confirm PostgreSQL as canonical |
| 7-phase vs 8-phase SDLC loop | AgentLoopSpec, BRD | AgentLoopSpec says 8 phases; BRD may reference different count |
| Service inventory and systemd units | TechnicalArchitecture, APIIntegration | Cross-check service lists |
| Mood taxonomy and yandere/persona states | Persona, PRD | Persona has v1.3 content; PRD may have earlier mood definitions |
| Surveillance scope and consent | BRD, Persona, MemorySchema | Consent assumptions differ in tone vs legal framing |
| OpenCode replacement vs optional turbo mode | TechnicalArchitecture, PRD | TechArch says optional turbo mode; PRD says replace OpenCode CLI sepenuhnya |

These are flagged for ADR review, not resolved in this report.

---

## 10. Summary of Findings

| Metric | Value |
|--------|-------|
| Total spec docs inventoried | 7 |
| Docs with standard header template | 6 |
| Docs with version mismatch (header!=footer) | 2 (TechArch, Persona) |
| Docs containing footer version tables | 0 |
| Docs containing Related Documents section | 0 |
| Docs with Last Updated header field | 0 |
| Docs with Canonical Decisions Applied header field | 0 |
| Unique version strings found | 1.0 (5 docs), 1.1 (1 doc header + 1 doc footer), 1.3 (1 doc footer) |
| Safe copy strategy | Copy file, edit 3 lines per doc (header version, add Related Documents, footer version) |

---

## 11. Recommended Execution Order

1. Copy all 7 v1.0 files to _v2.0.md filenames (no edits yet).
2. Apply header edits (version bump + metadata) to all 7 in parallel.
3. Add Related Documents section to each, with file-specific references.
4. Apply footer edits (version bump) to all 7.
5. Do NOT resolve the 7 conflict hotspots during this pass - flag them for ADR.
6. Run a consistency check after all v2.0 files are written to verify no v1.0 content was accidentally deleted.

---

*Report generated by Guinevere research agent. Read-only analysis - no files modified.*
