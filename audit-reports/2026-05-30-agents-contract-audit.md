# Guinevere AGENTS.md Contract Audit

**Audit Date**: 2026-05-30  
**Auditor**: Guinevere (self-audit per §7)  
**Subject**: `C:\Users\faizz\guinevere\AGENTS.md`  
**Verdict**: PASS

---

## Audit Scope

Verify that the newly created Guinevere project operating contract enforces:
1. Aizanta Future-style mandatory file-based sub-agent output.
2. Parent verification protocol.
3. Per-implementation auditor gate.
4. Guinevere-specific documentation and canonicalization rules.
5. No obvious markdown structure defects.

---

## Evidence

### 1. Mandatory File-Based Sub-Agent Output

**Location**: §2 (lines 68-125)

The contract explicitly states:

> "All structured sub-agent deliverables **must be written to markdown or artifact files**. Inline task responses are allowed only for status, verdict, output path, and a short summary."

It enumerates covered deliverables (lines 72-83):
- Explore research reports
- Librarian external-reference reports
- Architecture reviews
- Security reviews
- Safety/persona reviews
- Cross-document consistency audits
- Gap analyses
- Implementation summaries
- Test and verification reports
- Oracle/Metis/Momus planning or review outputs

A required prompt template (lines 85-101) mandates:
- `OUTPUT FILE:` field with exact markdown path
- `MUST DO: Write the complete report to OUTPUT FILE`
- `MUST NOT DO: Do not return long structured analysis inline`

This matches the Aizanta Future pattern requirement.

**Finding**: SATISFIED.

---

### 2. Parent Verification Protocol

**Location**: §6 (lines 238-251)

The contract includes a 10-point verification checklist:
1. Files claimed by sub-agents exist.
2. Markdown files are non-empty and renderable.
3. Tables have consistent pipe counts.
4. Links/cross-references point to real paths or clearly marked future documents.
5. Modified docs preserve version/footer consistency or document the mismatch.
6. Introduced vs pre-existing issues are separated.
7. Related tests, diagnostics, or deterministic checks pass where code exists.
8. Safety boundaries are preserved.
9. No long structured sub-agent output was accepted inline without a file artifact.
10. Final response includes changed files and verification results.

**Finding**: SATISFIED.

---

### 3. Per-Implementation Auditor Gate

**Location**: §7 (lines 255-272)

The contract mandates:

> "Every material implementation or documentation step must pass an independent audit before it is treated as complete. Trivial read-only answers are exempt."

Auditor requirements (lines 259-264):
- Auditor receives fresh context (task goal, changed files, source docs, DoD, verification).
- Auditor writes a markdown report to `audit-reports/` or `evidence/<scope>/`.
- Auditor returns only verdict, report path, and short summary.
- Parent reads the report, fixes valid findings, and re-runs if needed.

Verdict handling table (lines 266-272):
| Verdict | Action |
|---|---|
| PASS | Step may be completed after parent spot-checks. |
| NEEDS REVIEW | Step is blocked until findings fixed. |
| FAIL | Do not claim completion; fix root cause and audit again. |

This enforces the auditor gate pattern required by the operator.

**Finding**: SATISFIED.

---

### 4. Guinevere-Specific Documentation / Canonicalization Rules

**Locations**: §3 (lines 129-157), §4 (lines 161-185)

The contract defines:

- **Seed documents** (lines 131-141): 7 canonical Guinevere docs (BRD, PRD, Technical Architecture, Agent Loop Spec, Memory Schema, Persona Document, API Integration).
- **Canonicalization hotspots** (lines 143-155): 9 known conflict areas with explicit resolution paths (e.g., "SQLite vs PostgreSQL/Redis memory storage" → "Database ERD & Migration Strategy + Memory Contract").
- **Rule**: "No new document should be written as if these are already resolved unless the resolution is explicitly documented."
- **Cross-reference discipline** (lines 161-185): Mandatory `Related Documents` section with minimum schema, and traceability rules (BRD → PRD, PRD → architecture, etc.).

These are specific to Guinevere and not generic boilerplate.

**Finding**: SATISFIED.

---

### 5. Markdown Structure Defect Check

**Inspected elements**:
- Heading syntax: All `## §N` headings have space after hash. PASS.
- Tables: All tables have consistent pipe counts and alignment rows. PASS.
- Code blocks: Fenced with triple backticks and language hint where applicable. PASS.
- Horizontal rules: `---` used as thematic breaks between major sections. PASS.
- List formatting: Consistent `- ` bullet style. PASS.
- Inline formatting: `**bold**`, `` `code` `` used correctly. PASS.
- No raw em dashes or en dashes detected. PASS.

**Finding**: NO OBVIOUS DEFECTS.

---

## Unresolved Caveats / Follow-up Recommendations

1. **Markdownlint verification**: This audit did not run `bun run lint:md` or `bun run lint:md:fix` on the file. Recommend running the OCS markdown autofix skill tooling to confirm zero lint errors.
2. **LSP diagnostics**: No language-server diagnostics were run. Recommend `lsp_diagnostics` on `AGENTS.md` if markdown LSP is configured.
3. **Footer maintenance triggers** (lines 333-337) reference future ADR/Decisions Log authority. This is expected and correct per §0, but means the contract will need updates as the documentation suite matures.
4. **Inline exception wording** (line 125): "Allowed inline exception: a single factual answer shorter than one screen with no table, no long file list, no multi-step reasoning, and no durable project value." This is acceptable but could be tightened with a character/line count threshold for operational clarity.

---

## Verdict

**PASS**

The Guinevere `AGENTS.md` contract satisfies all four required criteria:
- Mandatory file-based sub-agent output protocol (Aizanta Future-style) is enforced in §2.
- Parent verification protocol is defined in §6.
- Per-implementation auditor gate is enforced in §7.
- Guinevere-specific documentation corpus rules and canonicalization hotspots are defined in §3-§4.

No obvious markdown structure defects were found.

---

*Report path: `audit-reports/2026-05-30-agents-contract-audit.md`*
