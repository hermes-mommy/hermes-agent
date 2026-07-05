# Wave 1 Evidence — Core Docs BRD/PRD/FSD Annotation

> Agent: core-docs-brd-prd-fsd
> Date: 2026-06-28
> Task: P28-P36 alignment — HARD STOP annotations + consent revocation annotations + Y-level caps + P32 renames

---

## What Was Done

Three core P28-P36 masterplan documents were annotated with ADR-062 disclaimers, consent revocation "(dev workflow only)" markers, ADR-067 Y-level cap disclaimers, and P32 reference renames.

---

## Files Changed

| File | Size | Edits Applied |
|---|---|---|
| `brd-business-requirements-document.md` | ~58 KB | 8 edits |
| `prd-product-requirements-document.md` | ~58 KB | 6 edits |
| `fsd-functional-specification-document.md` | ~56 KB | 4 edits |

---

## Fix 1 — HARD STOP Annotations (ADR-062 Disclaimer Blockquotes)

### BRD

| Section | Location | Annotation Added |
|---|---|---|
| §1 Executive Summary | After first HARD STOP mention (runtime Hermes paragraph) | ADR-062 blockquote after "AGENTS.md HARD STOP absolut hanya berlaku untuk development workflow" paragraph |
| §5.1 BR-001 | After "Faiz tidak punya HARD STOP authority di runtime" bullet | ADR-062 blockquote after BR-001 description |
| §7.2 Safety Constraints | After S-01 through S-14 table | ADR-062 blockquote + ADR-067 blockquote after table (annotations added post-table to preserve table integrity) |

### PRD

| Section | Location | Annotation Added |
|---|---|---|
| §1.3 Product Principles | After principles 1-2 (HARD STOP mentions) | ADR-062 blockquote between principle 2 and principle 3 |
| §5.2 NFR-001 | After intro paragraph | ADR-062 blockquote before S-INV table |

### FSD

| Section | Location | Annotation Added |
|---|---|---|
| §2.2 Cross-Cutting Boundaries | After META bullet point | ADR-062 blockquote with consent revocation note |
| UC-010 PoliteSTOP | After preconditions text | ADR-062 blockquote for UC-010 |
| §5.2 Key Event Types | After event table (post `audit.consent_violation` row) | ADR-062 + ADR-067 blockquotes |

---

## Fix 2 — Consent Revocation Annotations

| File | Section | Change |
|---|---|---|
| BRD | §7.2 S-02 | "Consent revocation absolute, autonomy cannot bypass" → added "(dev workflow only)" |
| BRD | §10 Glossary | Consent Revocation entry → added "(dev workflow only)" + Hermes exemption note |
| BRD | §7.2 post-table | Added note: "Consent revocation in S-02 applies to dev-workflow events only; Hermes runtime events are exempt per ADR-062 and ADR-066." |
| BRD | §10 Glossary post-table | Added: "Consent revocation applies to dev-workflow events only; Hermes runtime events are exempt per ADR-062 and ADR-066." |
| PRD | §5.2 S-INV-04 | "Consent revocation absolute" → added "(dev workflow only)" |
| PRD | §5.2 post-table | Added: "Consent revocation in S-INV-04 applies to dev-workflow events only; Hermes runtime events are exempt per ADR-062 and ADR-066." |
| FSD | §2.2 META | Added consent revocation note in ADR-062 disclaimer block |
| FSD | §5.2 event types | Added: "Consent revocation (`audit.consent_violation`) applies to dev-workflow events only; Hermes runtime events are exempt per ADR-062 and ADR-066." |

---

## Fix 3 — Y-Level Cap Annotations (ADR-067)

| File | Section | Change |
|---|---|---|
| BRD | §7.2 post-table | Added: "ADR-067: Y-level caps (S-03) apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap." |
| BRD | §10 Glossary post-table | Added: "ADR-067: Y-level caps (Y4/Y5/Y6) apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap." |
| PRD | §5.2 post-table | Added: "ADR-067: Y-level caps (S-INV-13) apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap." |
| FSD | §5.2 post-table | Added: "ADR-067: Y-level caps (Y5 prevention) apply to dev-workflow agent ONLY. Hermes runtime has no Y-level cap." |

---

## Fix 4 — P32 Reference Renames

| File | Line | Before | After |
|---|---|---|---|
| BRD | 418 | `P24 fork integration \| P32` | `External Presence & Tools \| P32` |
| BRD | 418 | `fork integration if P24 PASS` | `external presence if P24 PASS` |
| BRD | 445 | `P28 fork-agnostic (zero hard dependency on P24)` | `P28 P24 native fork (zero hard dependency on P24)` |
| PRD | 52 | `**Fork-Agnostic:** P28 does NOT depend on P24 fork` | `**P24 native fork:** P28 does NOT depend on P24 fork` |
| PRD | 137 | `P24 Fork Integration` | `External Presence & Tools` |
| PRD | 166 | `P32 P24 Fork` | `P32 External` |
| FSD | 35 | `fork-agnostic per ADR-054` | `P24 native fork per ADR-054` |

---

## Validation Results

### Table Integrity
All three files contain markdown tables. Annotations were placed:
- **Before or after tables** (not between rows) to preserve table structure
- **Post-table footnotes** where the table contains relevant content (§7.2, §5.2, §10 Glossary)

### Annotation Count Per Section (One per section rule)
| Document | Section | HARD STOP Annotations | Consent Annotations | Y-Level Annotations |
|---|---|---|---|---|
| BRD | §1 Executive Summary | 1 | — | — |
| BRD | §5.1 BR-001 | 1 | — | — |
| BRD | §7.2 Safety Constraints | 1 | 1 (post-table) | 1 (post-table) |
| BRD | §10 Glossary | — (already disclaimed) | 1 (post-table) | 1 (post-table) |
| PRD | §1.3 Product Principles | 1 | — | — |
| PRD | §5.2 NFR-001 | 1 | 1 (post-table) | 1 (post-table) |
| FSD | §2.2 Cross-Cutting | 1 | 1 (inline) | — |
| FSD | UC-010 PoliteSTOP | 1 | — | — |
| FSD | §5.2 Event Types | 1 | 1 (post-table) | 1 (post-table) |

---

## Pre-existing Disclaimer Analysis

All three documents (BRD v2.0, PRD v2.0, FSD v1.2) already contained extensive inline disclaimers distinguishing "development workflow" from "runtime Hermes" semantics. The existing text was written during the v2.0 paradigm shift and consistently:
- Identifies HARD STOP as development-workflow-only
- Carves out Hermes runtime from HARD STOP/consent semantics
- References ADR-062 inline in prose

This task adds the **standardized blockquote format** for cross-document consistency and round-2 paradigm-shift alignment evidence.

---

## Doc-Sync Impact

No cross-references broken. All additions are additive blockquotes/annotations. No section numbering changed.

---

## Boundary Compliance

- No HARD STOP text deleted (only annotated)
- No secrets/credentials touched
- No consent/surveillance boundary violated
- Annotations preserve original semantics

---

## Rollback/Re-run Safety

All edits are additive blockquotes and inline modifications. Reverting restores original v2.0 content exactly. No structural changes to document flow.

---

## Design Decisions/Caveats

1. **Table sections**: Annotations placed post-table (not between rows) to preserve markdown table integrity.
2. **Duplicate disclaimers**: Some sections already had extensive inline ADR-062 references. Added standardized blockquote format for consistency with the round-2 alignment template, even where inline text already existed.
3. **P32 rename "P24 native fork"**: The original text said "fork-agnostic" (meaning: doesn't depend on fork). The rename to "P24 native fork" changes semantic direction. This was applied per task instruction literally. A semantic review may be needed.
4. **PRD §3.2 dependency graph**: ASCII art box for "P32 P24 Fork" was shortened to "P32 External" — the second line "Integration" was preserved from the original to maintain box alignment.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | core-docs-brd-prd-fsd agent | Initial wave 1 annotations for P28-P36 alignment. |
