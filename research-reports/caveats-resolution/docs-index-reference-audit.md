# Docs Index & Governance Reference Audit

**Audit Scope**: docs/README.md, ADR Index, IMPLEMENTATION_GUIDE.md, StepPrompts, PROGRESS.md, CHECKLIST.md, Hermes evidence, and all cross-reference sources for workflow template (opencode-master-template-v3) and SystemPromptMaster filename/version consistency.

**Date**: 2026-06-01
**Caveats**: C1 (workflow template) + C2 (SystemPromptMaster renaming)
**Auditor**: Guinevere

---

## 1. Workflow Template: `docs/workflow/opencode-master-template-v3.md`

### Finding: FILE DOES NOT EXIST

| Check | Result |
|---|---|
| File exists at `docs/workflow/opencode-master-template-v3.md`? | ❌ **Not found** |
| `docs/workflow/` directory exists? | ❌ **Does not exist** |
| Any file with `opencode-master-template` in name? | ❌ None found |
| Any file with `opencode-master-template` in content? | ❌ Only in `verification.md` confirming it's missing |
| Any reference in docs/README.md? | ❌ None |
| Any reference in ADR Index? | ❌ None |
| Any reference in IMPLEMENTATION_GUIDE.md? | ❌ None |
| Any reference in StepPrompts? | ❌ None |
| Any reference in PROGRESS.md or CHECKLIST.md? | ❌ None |
| Any reference in audit reports? | ❌ Only `docs/setup-evidence/agents-md-update/verification.md` noting absence |
| Any reference in evidence files? | ❌ Only noting absence |
| Any reference in `adr/` directory? | ❌ None |

**Context**: The `docs/setup-evidence/agents-md-update/verification.md` (line 35, 118) already documents that this file "was requested but is not present in the repository."

### Verdict: No index updates needed — file does not exist yet

Since `docs/workflow/opencode-master-template-v3.md` was never created:
- If it **will be created**, then docs/README.md and any relevant governance docs **will need updates** at creation time.
- If it **has been superseded** or was planned but never realized, **no update needed**.
- **Recommended**: Either create the file and update indexes, or document the decision to drop the plan.

---

## 2. SystemPromptMaster Filename/Version Mismatch

### Finding: FILENAME DECLARES v1.0, CONTENT IS v1.1

The file `docs/60-persona/61-SystemPromptMaster_v1.1.md` has mismatched identity:

| Attribute | Declared Value | Line |
|---|---|---|
| Filename | `61-SystemPromptMaster_v1.1.md` | — |
| Header H1 | `# Guinevere SystemPromptMaster v1.1` | L1 |
| Version field | `1.1` | L6 |
| Status | `Canonical — Ready for Runtime Injection` | L7 |
| Changelog v1.0 | Initial — 2026-05-31 | L397 |
| Changelog v1.1 | Y1→Y4 recalibration — 2026-05-31 | L398 |
| Footer | `Guinevere SystemPromptMaster v1.0` | L400 (inconsistent) |

**Already documented in**:
- `research-reports/P1/system-prompt-master-safety-inventory.md` (L30, L499): Recommends rename
- `research-reports/agents-md-update/stale-reference-audit.md` (F4): LOW severity
- `docs/setup-evidence/P1/STEP-P1-016/evidence.md` (L84): Acknowledged caveat
- `docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md` (L54): "rename deferred"
- `audit-reports/agents-md-update/agents-md-update-auditor-report.md` (L308): Noted as outside AGENTS.md scope

### Impact Analysis If File Is Renamed to `61-SystemPromptMaster_v1.1.md`

| File | References | Impact | Action Required |
|---|---|---|---|
| `docs/README.md` | 3 references (L181 table, L231 cross-ref map, L284 reading path) | **3 broken links** | Update all 3 references to v1.1 path |
| `README.md` (project root) | 1 reference in Dokumen Kunci table | **1 broken link** | Update to v1.1 path |
| `stepprompts/StepPrompts.md` | Multiple in P1-016: L4554 header, L4573 pre-flight, L4578 SCP cmd, L4655 troubleshooting | **4+ broken references** | Update all v1.0 path references |
| `stepprompts/StepPrompts.md.bak` | Same as above (backup copy) | Same impact | Update if backup maintained |
| `research-reports/P1/system-prompt-master-safety-inventory.md` | L8: source doc path; multiple section references | **File path reference stale** | Update source doc path on L8 |
| `docs/setup-evidence/P1/STEP-P1-016/evidence.md` | L8: source doc path | **1 broken reference** | Update source doc path |
| `docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md` | L19: path reference | **1 broken reference** | Update path |
| `docs/setup-evidence/agents-md-update/verification.md` | L36-37: scan for file existence | **False negative in future scans** | Update or acknowledge |
| `audit-reports/2026-05-31-persona-prompt-mcp-discord-audit.md` | L5, L89, L107, multiple | **4+ stale references** | Update source doc annotation |
| `audit-reports/P1/STEP-P1-016/step-p1-016-auditor-report.md` | L7: source doc, L93 | **Stale source path** | Update |
| `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md` | L8: reference path | **1 stale reference** | Update |
| `audit-reports/P1/P1-FINAL/05-safety-compliance.md` | L19: source path | **1 stale reference** | Update |
| `audit-reports/agents-md-update/agents-md-update-auditor-report.md` | L246: mentions without path format | ✅ No direct path fragment — OK |
| `PROGRESS.md` | L111: mentions "SystemPromptMaster deployment" | ✅ No version/path — OK |
| `CHECKLIST.md` | L361: mentions "SystemPromptMaster deployed" | ✅ No version/path — OK |
| `AGENTS.md` | No direct path/version references | ✅ No impact (per stale-reference-audit.md) |
| `ADR Index` (`17-ADR_Index_v1.0.md`) | No references to SystemPromptMaster | ✅ No impact |
| `IMPLEMENTATION_GUIDE.md` | No references to SystemPromptMaster | ✅ No impact |
| `adr/` directory | No references to SystemPromptMaster | ✅ No impact |

**Total affected files (if renamed)**: 9 files, ~20+ reference points

### Verdict on C2

The filename `61-SystemPromptMaster_v1.1.md` is **persistently inconsistent** with the document's declared v1.1 content. Previous evidence (persona-calibration/v3.1-beyond-brutal.md L54) deferred the rename "to avoid breaking cross-references."

- **If not renamed**: No updates needed to any index or cross-reference. The filename stays v1.0, content is v1.1. Inconsistency remains but is documented and stable.
- **If renamed**: Requires updating **9 files** with **~20 reference points**. All cross-reference files listed above must be updated atomically.
- **Recommended action**: Keep the filename as-is until a dedicated batch rename is scoped. Document the mismatch in a single visible location (e.g., docs/README.md addendum or ADR entry) so future readers don't treat it as an oversight.

---

## 3. docs/README.md — Current State

### SystemPromptMaster References (3 total)

| Line | Content | Stale? |
|---|---|---|
| L181 | `| 61 | [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md) | v1.0 | Diterima | 22.5 KB |` | ✅ Filename matches reality; version field says v1.0 (matches filename) |
| L231 | `├─► System Prompt Master (61)` | ✅ Name-only reference in cross-reference map |
| L284 | `6. [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md)` | ✅ Filename matches reality |

**Verdict**: All 3 references are internally consistent with the current filename. The displayed version field (v1.0) matches the filename, though the document's actual content is v1.1.

### Workflow Template References (0 total)

**Verdict**: No references to `opencode-master-template-v3.md` exist in docs/README.md. If the template is created, a new entry in the document registry and cross-reference map would be needed.

---

## 4. ADR Index (17-ADR_Index_v1.0.md) — Current State

| Reference Type | Workflow Template | SystemPromptMaster |
|---|---|---|
| Direct mention | None | None |
| Implicit relation | None | None |
| Backlog items | None | None |

**Verdict**: ADR Index references neither item. No updates needed for either caveat.

---

## 5. IMPLEMENTATION_GUIDE.md — Current State

| Reference Type | Workflow Template | SystemPromptMaster |
|---|---|---|
| Direct mention | None | None |
| Stepprompt references | Points to `stepprompts/StepPrompts.md` (which references P1-016) | Indirect via Stepprompt workflow |

**Verdict**: No direct references. No updates needed.

---

## 6. StepPrompts — Current State

| Reference Type | Workflow Template | SystemPromptMaster |
|---|---|---|
| Direct mention | None | Uses `61-SystemPromptMaster_v1.1.md` path in P1-016 step (6 occurrences) |
| Impact if renamed | None | **Requires update** to all 6 path references |

**Verdict**: If SystemPromptMaster is renamed, StepPrompts.md is the most critical file to update as it contains executable commands that reference the v1.0 path.

---

## 7. Hermes Config / Evidence — Current State

| Reference Type | Workflow Template | SystemPromptMaster |
|---|---|---|
| Deployed prompt path | N/A | `/home/guinevere/config/hermes/system-prompt.md` (content v1.1) |
| Source path in evidence | N/A | `docs/60-persona/61-SystemPromptMaster_v1.1.md` (v1.0 filename) |
| Runtime | N/A | Content is v1.1 regardless of source filename |

**Verdict**: The deployed system prompt on VPS is **not affected** by the filename — it's copied as content. Renaming the source file would not impact the deployed prompt, but evidence files referencing the source path would need updates.

---

## 8. Comprehensive Update Table

### If `docs/workflow/opencode-master-template-v3.md` IS created:

| File | Update Needed | Type |
|---|---|---|
| `docs/README.md` | Add to 60-persona document table + cross-reference map | Registration entry |
| `docs/README.md` | Update total_document count (37→38) | Frontmatter metadata |
| `docs/60-persona/` (index) | Add entry if index file exists | Registration |
| StepPrompts (if applicable) | Add step for template usage | Implementation step |

### If SystemPromptMaster IS NOT renamed:

| File | Update Needed | Rationale |
|---|---|---|
| None | No urgent updates | Mismatch is documented in 3+ existing reports; filename is stable |

### If SystemPromptMaster IS renamed (batch operation):

| File | Action |
|---|---|
| `docs/README.md` | 3 reference path updates (L181, L231, L284) |
| `README.md` (project root) | 1 reference path update |
| `stepprompts/StepPrompts.md` | 6+ reference updates in P1-016 |
| `stepprompts/StepPrompts.md.bak` | Same as above (if maintained) |
| `research-reports/P1/system-prompt-master-safety-inventory.md` | Source path update (L8) |
| `docs/setup-evidence/P1/STEP-P1-016/evidence.md` | Source path update (L8) |
| `docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md` | Path update (L19) |
| `docs/setup-evidence/agents-md-update/verification.md` | Update scan expectations |
| `audit-reports/2026-05-31-persona-prompt-mcp-discord-audit.md` | Source doc annotation updates |
| `audit-reports/P1/STEP-P1-016/step-p1-016-auditor-report.md` | Source path update (L7) |
| `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md` | Source path update (L8) |
| `audit-reports/P1/P1-FINAL/05-safety-compliance.md` | Source path update (L19) |
| Final check: `AGENTS.md`, `PROGRESS.md`, `CHECKLIST.md`, `ADR Index`, `IMPLEMENTATION_GUIDE.md` | ✅ No path/version — no changes |

---

## 9. Final Recommendations

### C1 (Workflow Template)
- **Decision needed**: Is `docs/workflow/opencode-master-template-v3.md` still planned or cancelled?
- If **planned**: Create the file first, then update docs/README.md with a new registry entry + cross-reference link.
- If **cancelled**: Document the cancellation explicitly (e.g., in ADR, decisions log, or caveat resolution report).
- **No index updates required until the file exists.**

### C2 (SystemPromptMaster Filename)
- **Recommended: Do NOT rename as standalone operation.** The filename mismatch affects 9+ files with ~20 reference points. A rename should be scoped as a coordinated batch operation with a single session plan.
- **Until rename happens**: All indexes are internally consistent with the current filename. The content-vs-filename mismatch is already documented in 3+ independent reports.
- **If rename is done**: Use the table in §8 above as the full inventory of affected files.

---

## 10. Boundary Compliance

| Check | Result |
|---|---|
| No persona drift | ✅ Recommendations preserve Y4 baseline |
| No consent violation | ✅ No consent boundaries touched |
| No Y6 introduced | ✅ Y6 prohibition unchanged |
| No secrets exposed | ✅ No credentials or tokens in scope |
| No destructive ops recommended | ✅ Read-only audit |
| HARD STOP protocol preserved | ✅ Not affected by filename or template |
| Distress protocol unchanged | ✅ Not affected |

---

*Report generated 2026-06-01 for caveat resolution C1+C2 and auditor gate. Source: grep + glob + read audit of all index files, governance references, evidence, audit reports, and StepPrompts.*