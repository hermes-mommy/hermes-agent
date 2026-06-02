# SystemPromptMaster Filename Rename — Reference Audit Report

**Task**: Rename `docs/60-persona/61-SystemPromptMaster_v1.1.md` → `docs/60-persona/61-SystemPromptMaster_v1.1.md`

**Date**: 2026-06-01  
**Scope**: Full-repo grep for `61-SystemPromptMaster_v1.1.md` and `SystemPromptMaster_v1.1` path references  
**Source file**: `docs/60-persona/61-SystemPromptMaster_v1.1.md` (header says v1.1, changelog shows v1.0→v1.1 transition, filename is v1.0)

---

## 1. Files Requiring Active Update (path will break after rename)

These files contain literal paths/commands that reference `61-SystemPromptMaster_v1.1.md`. After rename they must be updated or they will break (broken links, failed cp commands, wrong solution instructions).

| # | File | Lines | Nature of Reference | Recommended Action |
|---|---|---|---|---|
| **1** | `docs/README.md` | 181, 284 | Hyperlink `(60-persona/61-SystemPromptMaster_v1.1.md)` + version table (labels as v1.0) | Update link path to `61-SystemPromptMaster_v1.1.md`; update version column to v1.1 |
| **2** | `README.md` (root) | 119 | Key documents table — hyperlink to `(docs/60-persona/61-SystemPromptMaster_v1.1.md)` | Update link path |
| **3** | `stepprompts/StepPrompts.md` | 4573, 4578, 4655 | (a) Check-item: `docs/60-persona/61-SystemPromptMaster_v1.1.md`; (b) `cp` command source path; (c) Solution error text | Update all 3 occurrences |
| **4** | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | filename itself | File must be renamed to `61-SystemPromptMaster_v1.1.md` | **Rename the file** (filename mismatch known — content already says v1.1) |

### 1.1 Active-Action Details

**`docs/README.md` (line 181)**:
```
| 61 | [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md) | v1.0 | Diterima | 22.5 KB |
```
→ Change path to `61-SystemPromptMaster_v1.1.md` and version to `v1.1`.

**`docs/README.md` (line 284)**:
```
6. [System Prompt Master](60-persona/61-SystemPromptMaster_v1.1.md) ...
```
→ Change path.

**`README.md` (line 119)**:
```
| 9 | [System Prompt Master](docs/60-persona/61-SystemPromptMaster_v1.1.md) | System prompt yang di-deploy ke model LLM |
```
→ Change path.

**`stepprompts/StepPrompts.md` (line 4573)**:
```
- [ ] SystemPromptMaster document available at `docs/60-persona/61-SystemPromptMaster_v1.1.md`
```
→ Change path.

**`stepprompts/StepPrompts.md` (line 4578)**:
```
cp /home/guinevere/code/guinevere/docs/60-persona/61-SystemPromptMaster_v1.1.md \
```
→ Change path (VPS path + local path both affected).

**`stepprompts/StepPrompts.md` (line 4655)**:
```
- **Solution:** Ensure docs/60-persona/61-SystemPromptMaster_v1.1.md exists.
```
→ Change path.

---

## 2. Historical/Evidence Files (should update for accuracy)

These files reference the `v1.0.md` path in documents that are historical records, evidence artifacts, or research reports. While they won't "break" in the same way (they are snapshots), updating them improves accuracy and prevents confusion.

### 2.1 Evidence Files

| # | File | Lines | Nature | Recommended Action |
|---|---|---|---|---|
| **5** | `docs/setup-evidence/persona-calibration/v3.1-beyond-brutal.md` | 19, 47, 49 | Evidence of v1.0→v1.1 calibration; includes `lsp_diagnostics SystemPromptMaster_v1.1.md` and `grep` commands | Update paths in evidence; or document as snapshot-of-time |
| **6** | `docs/setup-evidence/P1/STEP-P1-016/evidence.md` | 8 | Source doc declaration: `docs/60-persona/61-SystemPromptMaster_v1.1.md` | Update path (this is active evidence, not historical) |
| **7** | `docs/setup-evidence/agents-md-update/verification.md` | 36-37, 119 | Verification that v1.1 filename didn't exist; references v1.0.md | Update after rename, or document as pre-rename snapshot |
| **8** | `evidence/reorg/2026-05-31-enterprise-folder-reorg.md` | 87 | Reorganization mapping table | Update mapping to show new filename |

### 2.2 Research Reports

| # | File | Lines | Nature | Recommended Action |
|---|---|---|---|---|
| **9** | `research-reports/P1/system-prompt-master-safety-inventory.md` | 8, 30, 499, 508 | Full safety inventory; explicitly recommends rename (line 499) | Update path; the rename recommendation becomes resolved |
| **10** | `research-reports/P1/p1-final-audit-safety.md` | 19, 235 | Audit references + finding D-01 (filename mismatch) | Update path; D-01 becomes resolved after rename |
| **11** | `research-reports/P1/internal-context-persona-safety.md` | 19, 461, 620, 649 | Multiple path references + config suggestion | Update all v1.0 paths |
| **12** | `research-reports/P1/hard-stop-protocol-inventory.md` | 69, 405 | HARD STOP protocol cross-reference table | Update path |
| **13** | `research-reports/P1/vps-state-pre-p1-015-016.md` | 234 | Pre-deployment verification checklist | Update path |
| **14** | `research-reports/agents-md-update/stale-reference-audit.md` | 6, 39, 71, 77, 101, 108 | Stale reference audit; Finding F4 is the rename issue | Update path; F4 becomes resolved |

### 2.3 Audit Reports

| # | File | Lines | Nature | Recommended Action |
|---|---|---|---|---|
| **15** | `audit-reports/stepprompts-audit/D9-D10-D11-D12-evidence-persona-loop-memory.md` | 8 | Reference doc declaration | Update path |
| **16** | `audit-reports/P1/STEP-P1-016/step-p1-016-auditor-report.md` | 7 | Source doc field | Update path |
| **17** | `audit-reports/P1/P1-FINAL/05-safety-compliance.md` | 19, 61 | Authority doc reference + check item | Update path |
| **18** | `audit-reports/agents-md-update/agents-md-update-auditor-report.md` | 308 | Notes F4 as outside scope | Update path comment |

### 2.4 Backup File

| # | File | Lines | Nature | Recommended Action |
|---|---|---|---|---|
| **19** | `stepprompts/StepPrompts.md.bak` | 4280, 4285, 4362 | Backup copy of StepPrompts; mirrors StepPrompts.md | Update paths (if backup is kept in sync) |

---

## 3. Files with Generic/Non-Versioned SystemPromptMaster References (NO action needed)

These files reference `SystemPromptMaster` generically — by name, concept, or `v1.1` version label — without using the `_v1.0.md` filename path. They will not break after rename.

| File | Nature of Reference | Why No Action Needed |
|---|---|---|
| `AGENTS.md` | **No references found** | Clean |
| `adr/` directory | **No references found** | Clean |
| `CHECKLIST.md` (line 361) | `SystemPromptMaster deployed (P1-016)` | Generic, no path |
| `PROGRESS.md` (line 111) | `P1-016 SystemPromptMaster deployment` | Generic, no path |
| `src/core/services/prompt_loader.py` | Module docstring + function docstring | Say "SystemPromptMaster" generically |
| `src/core/services/hard_stop_handler.py` | Module docstring | Say "SystemPromptMaster §D" generically |
| `tests/safety/test_hard_stop_model.py` | Comment + docstring | Say "SystemPromptMaster v1.1" — already correct version |
| `tests/smoke/conftest.py` | Reads `/home/guinevere/config/hermes/system-prompt.md` | Deployed copy path, not source path |
| `qa-inputs/Guinevere_Persona_QA_Comprehensive.md` (line 877) | Generic reference | No path |
| `qa-inputs/Guinevere_3Doc_QA_Answers.md` (line 5) | Scope description | Generic |
| `audit-reports/2026-05-31-qa-consistency-audit.md` | Multiple generic references | No versioned path |
| `audit-reports/2026-05-31-persona-prompt-mcp-discord-audit.md` | Multiple generic/v1.0 references as document title | References doc title (SystemPromptMaster v1.0), not filename path |
| `audit-reports/2026-05-31-implementation-synthesis.md` (line 162) | Generic reference | No path |
| `audit-reports/P1/P1-FINAL-AUDIT.md` (line 143) | `SystemPromptMaster v1.1` | Already correct version |
| `audit-reports/P1/P1-FINAL/01-completeness-inventory.md` (line 51) | `SystemPromptMaster deployed` | Generic |
| `audit-reports/P1/STEP-P1-005/step-p1-005-auditor-report.md` (line 104) | `SystemPromptMaster v1.1 (§C)` | Already correct version |
| `docs/setup-evidence/P1/batch-plan-004-005.md` | Multiple `SystemPromptMaster v1.1` references | Already correct version label |
| `docs/setup-evidence/P1/batch-plan-006-007.md` (line 232) | `SystemPromptMaster v1.1` | Already correct |
| `docs/setup-evidence/P1/batch-plan-017-019.md` (line 6) | `P1-016 (SystemPromptMaster)` | Generic |
| `docs/setup-evidence/P1/STEP-P1-017/evidence.md` | `SystemPromptMaster v1.1` | Already correct |
| `docs/setup-evidence/P1/STEP-P1-004/evidence.md` (line 100) | `SystemPromptMaster Y4` | Generic |
| `tmp/verify_p1_016.py` | Generic + system-prompt.md path | Deployed copy, not source path |
| `tmp/p1-017-section.md` (line 86) | Generic | No path |
| `tmp/debug_raw_9router.py` (line 5) | system-prompt.md path | Deployed copy |

---

## 4. Verification Commands (to be run after rename)

```bash
# Verify NO remaining references to old v1.0 filename path
grep -r "61-SystemPromptMaster_v1.1.md" . --include="*.md"

# Expected result: 0 matches (no remaining stale references)

# Verify new v1.1 filename is referenced correctly
grep -r "61-SystemPromptMaster_v1.1.md" . --include="*.md"

# Expected result: matches in docs/README.md, README.md, StepPrompts.md, and any updated evidence/research/audit files

# Validate that the renamed file actually exists at new path
ls docs/60-persona/61-SystemPromptMaster_v1.1.md

# Expected result: file exists

# Verify old path no longer exists
ls docs/60-persona/61-SystemPromptMaster_v1.1.md

# Expected result: "No such file" (after rename)

# Check that no broken links exist in the two index files
grep "SystemPromptMaster" docs/README.md README.md

# Expected result: all references use v1.1 path
```

---

## 5. Summary

| Category | Count | Action |
|---|---|---|
| **Active (must update)** | 4 files | `docs/README.md`, `README.md`, `stepprompts/StepPrompts.md`, `docs/60-persona/61-SystemPromptMaster_v1.1.md` (rename) |
| **Historical/Evidence (should update)** | 15 files | Evidence + research reports + audit reports + backup |
| **Generic/No action** | ~25 files | Already correct or no versioned path reference |
| **Clean (no references)** | AGENTS.md, adr/ directory | Verified no SystemPromptMaster path references |

### Execution Order Recommended

1. Rename the source file: `61-SystemPromptMaster_v1.1.md` → `61-SystemPromptMaster_v1.1.md`
2. Update active references (Section 1) — these will break immediately
3. Update evidence files (Section 2.1) — active evidence should reflect current state
4. Update research reports (Section 2.2) and audit reports (Section 2.3) — accuracy improvement
5. Run verification commands (Section 4) to confirm clean state

---

*Report generated 2026-06-01 via full-repo grep audit. Sources: combined grep for `SystemPromptMaster_v1.1`, `61-SystemPromptMaster_v1.1.md`, and `SystemPromptMaster` patterns across all files.*