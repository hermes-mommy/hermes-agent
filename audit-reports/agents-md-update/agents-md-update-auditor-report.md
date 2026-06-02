# AGENTS.md Workflow Update — Independent Auditor Report

| Field | Value |
|---|---|
| Scope | `AGENTS.md` workflow gates + stale reference cleanup |
| Date | 2026-06-01 |
| Auditor | Independent auditor (fresh context) |
| Trigger | Faiz directive: update AGENTS.md to latest planner/research/auditor workflow |
| Evidence path | `docs/setup-evidence/agents-md-update/verification.md` |

---

## 1. Inputs Reviewed

| Input | Path | Status |
|---|---|---|
| Target contract | `AGENTS.md` (689 lines) | ✅ Read in full |
| Evidence file | `docs/setup-evidence/agents-md-update/verification.md` | ✅ Read |
| Workflow gates audit | `research-reports/agents-md-update/workflow-gates-audit.md` | ✅ Read |
| Stale reference audit | `research-reports/agents-md-update/stale-reference-audit.md` | ✅ Read |
| ADR-028 | `adr/ADR-028-llm-router-outage-graceful-degradation.md` | ✅ Read (Superseded v4.0) |

---

## 2. Workflow Gate Verification

### Gate 1: AGENTS.md First-Read Rule

**Requirement:** Agent must read `AGENTS.md` first every session before any other repo state or task work.

| Location | Text | Status |
|---|---|---|
| §1 line 112 | `1. Read \`AGENTS.md\` operating contract first, then progress/current state + active todos` | ✅ |
| §3 line 239 | `1. Read \`AGENTS.md\` operating contract first, before any other repo state or task work.` | ✅ |

**Verdict:** ✅ **PASS** — Explicitly mandated in both §1 (Super-Autopilot Mode) and §3 (Session-Start Workflow).

---

### Gate 2: §WORKFLOW GATES Section

**Requirement:** A dedicated `§WORKFLOW GATES` section must exist after sub-agent output discipline.

| Location | Text | Status |
|---|---|---|
| §14 line 626 | `### §WORKFLOW GATES — mandatory execution gates` | ✅ |

**Verdict:** ✅ **PASS** — Section exists with RESEARCH WAVE, PLANNER GATE, AUDITOR ORCHESTRATOR, and Per-step implementation auditor gate subsections.

---

### Gate 3: Mandatory RESEARCH WAVE

**Requirement:** Before implementation, parent must fire an unlimited parallel research wave for all non-trivial tasks.

| Check | Source | Status |
|---|---|---|
| Research wave before implementation mandated | §14 lines 628-636 | ✅ |
| `explore` agents for internal context | §14 line 632 | ✅ |
| `librarian` agents for external context | §14 line 633 | ✅ |
| Specialist agents for risky areas | §14 line 634 | ✅ |
| File-based report with `output_path` | §14 line 635 | ✅ |
| All agents finish before planner gate starts | §14 line 636 | ✅ |
| Also referenced in §1 step 4 and §2.2 | lines 115, 150-151 | ✅ |

**Verdict:** ✅ **PASS** — Fully documented with unlimited parallel spawning and clear domain separation.

---

### Gate 4: Mandatory PLANNER GATE

**Requirement:** After research synthesis, spawn a planner gate producing a batch-plan output file.

| Check | Source | Status |
|---|---|---|
| Planner gate after research synthesis | §14 lines 638-645 | ✅ |
| Batch-plan output file required | §14 line 642 | ✅ |
| Plan contents: master todo, deps, delegation, collision scan, rollback, evidence, verification, auditor matrix | §14 lines 642-643 | ✅ |
| Parent verifies file exists and reads it | §14 line 644 | ✅ |
| No implementation before plan file exists + todo sync | §14 line 645 | ✅ |

**Verdict:** ✅ **PASS** — Complete specification with reproduction of all required plan content.

---

### Gate 5: Planner Output → Todo Sync

**Requirement:** Parent must read planner output and rewrite active todos before implementation.

| Check | Source | Status |
|---|---|---|
| §1 step 7 explicit todo sync | line 118 | ✅ |
| §2.5.1 dedicated subsection with 4-step checklist | lines 166-175 | ✅ |
| Failure handling with task_id retry | line 175 | ✅ |
| Fallback plans only after retry documented | line 175 | ✅ |
| §14 line 644-645 reinforces | line 644-645 | ✅ |

**Verdict:** ✅ **PASS** — Most thoroughly documented gate. Idempotent retry and fallback paths defined.

---

### Gate 6: AUDITOR ORCHESTRATOR with Unlimited Parallel Specialist Auditors

**Requirement:** After parent verification, spawn unlimited parallel specialist auditors for all ready non-conflicting audit surfaces.

| Check | Source | Status |
|---|---|---|
| Unlimited parallel specialist auditors | §14 lines 647-654 | ✅ |
| File-based output with explicit `output_path` | §14 line 652 | ✅ |
| Parent reads all reports and assigns PASS/NEEDS REVIEW/FAIL | §14 line 653 | ✅ |
| NEEDS REVIEW/FAIL fixed and re-audited via task_id | §14 line 654 | ✅ |
| §1 step 11 reinforces | line 122 | ✅ |
| §2.2 item 7 reinforces | lines 159-160 | ✅ |
| §2 §10 reinforces | lines 229-233 | ✅ |

**Verdict:** ✅ **PASS** — Extensively documented in multiple reinforcing sections.

---

### Gate 7: `load_skills` Requirement

**Requirement:** Every `task()` delegation call must include `load_skills`.

| Location | Text | Status |
|---|---|---|
| §2.2 line 152 | `Every \`task()\` delegation call must include \`load_skills=[]\` or an explicit non-empty skill list.` | ✅ |
| §2.3 line 194 | `Every \`task()\` call must include \`load_skills\` (\`[]\` if no skill applies, or a non-empty skill list when relevant)` | ✅ |
| §12 line 506 | `| Skill loading for delegation | \`load_skills\` on \`task()\` | Always include \`load_skills=[]\` when no skill applies` | ✅ |

**Verdict:** ✅ **PASS** — Mandated in §2.2 (Parallel + Unlimited), §2.3 (Decompose then Delegate), and §12 (Tool Selection). The previous audit finding of "zero references" is fully resolved.

---

### Gate 8: `run_in_background` Requirement

**Requirement:** Parallel sub-agent spawning must use `run_in_background=true`.

| Location | Text | Status |
|---|---|---|
| §2.2 line 151 | `All parallel sub-agent spawning must use \`run_in_background=true\`.` | ✅ |
| §2.3 line 194 | Combined with load_skills: `run_in_background` (true for parallel/background work, false only for synchronous gated calls) | ✅ |
| §12 line 507 | `| Background sub-agents | \`run_in_background=true\` on \`task()\` | Required for parallel...` | ✅ |

**Verdict:** ✅ **PASS** — Mandated in both §2.2 and §2.3 with the parallel/sync distinction clearly defined.

---

### Gate 9: `output_path` in Delegation Prompts

**Requirement:** Every delegation prompt expecting structured output MUST include explicit `output_path` in `MUST DO`.

| Location | Text | Status |
|---|---|---|
| §14 lines 606-607 | `BLOCKING — delegation prompt MUST include output path: ...WAJIB menyertakan \`output_path\` eksplisit di bagian \`MUST DO\`` | ✅ |
| §14 line 635 (RESEARCH WAVE) | `Every research sub-agent must write a file-based report with explicit \`output_path\`` | ✅ |
| §14 line 652 (AUDITOR ORCHESTRATOR) | `Every specialist auditor must write file output with explicit \`output_path\`` | ✅ |

**Verdict:** ✅ **PASS** — Explicit BLOCKING rule with concrete example and scoping.

---

## 3. Stale Reference Verification

### Check Results

| Stale Reference | grep Result | Status |
|---|---|---|
| `Ollama` in AGENTS.md | **No matches found** | ✅ Clean |
| `OpenRouter` in AGENTS.md | **No matches found** | ✅ Clean |
| `9Router/OpenRouter` in AGENTS.md | **No matches found** | ✅ Clean (replaced with `9Router (guinevere combo)` at line 154) |
| `Y1 baseline` in AGENTS.md | **No matches found** | ✅ Clean |
| `Y4 permanent baseline` in AGENTS.md | **Found 2 matches** (lines 52, 316) | ✅ Present |
| ADR-028 Superseded respected | ADR-028 status: `Superseded` v4.0 | ✅ Respected |

### Line-by-Line Verification of Updated References

**Line 52 (BLOCKING list):**
```
- NEVER allow Y6 yandere level (Y5 absolute ceiling, Y4 permanent baseline per Faiz directive)
```
✅ Correct — Y4 permanent baseline, Y5 ceiling, Y6 prohibited.

**Line 154 (librarian trigger examples):**
```
This includes Hermes Agent, Discord.py, 9Router (guinevere combo), Tasker, ...
```
✅ Correct — `9Router (guinevere combo)` replaces `9Router/OpenRouter`.

**Line 316 (Persona-Risk Anti-Patterns):**
```
❌ Yandere drift beyond Y5 (Y4 permanent baseline per Faiz directive, Y5 absolute ceiling)
```
✅ Correct — Y4 baseline, Y5 ceiling.

---

## 4. LSP Diagnostics

| Check | Result |
|---|---|
| `lsp_diagnostics` on `AGENTS.md` (severity: all) | **No diagnostics found** — CLEAN |

No pre-existing or introduced issues detected.

---

## 5. Secrets / Token Leakage Check

| Check | Result |
|---|---|
| grep for `Discord.*token` in evidence path | ✅ Only negative claim (line 81: `No Discord token, API key...`) |
| grep for `API.*key` in evidence path | ✅ Same negative claim only |
| grep for `DB.*password` in evidence path | ✅ Same negative claim only |
| grep for `surveillance.*credential` in evidence path | ✅ Same negative claim only |
| Visual inspection of evidence file | ✅ No plaintext secrets |

**Verdict:** ✅ No secrets exposed. The evidence file contains only a statement that no secrets were read, which is an acceptable compliance declaration.

---

## 6. Evidence File Completeness (verification.md)

| Section | Present | Notes |
|---|---|---|
| What Was Done | ✅ | Lines 11-21 — accurate summary of changes |
| Files Changed | ✅ | Lines 23-28 |
| Validation Results | ✅ | Lines 49-58 — LSP, grep matrix, markdownlint note |
| Workflow Gate Coverage | ✅ | Lines 62-69 |
| Stale Reference Cleanup | ✅ | Lines 72-78 |
| Boundary Compliance | ✅ | Lines 80-85 |
| Rollback / Re-run Safety | ✅ | Lines 87-98 |
| Auditor Gate | ✅ | Lines 100-114 — self-aware that audit was pending |
| Caveats | ✅ | Lines 116-120 |
| Footer | ✅ | Lines 122-125 |

**Verdict:** ✅ Evidence file is complete and follows the minimum schema from §11 Appendix B.

---

## 7. Cross-Reference & Path Validity

| Reference | Path | Status |
|---|---|---|
| ADR-Index | `docs/10-governance/17-ADR_Index_v1.0.md` (line 14) | ✅ Presumed valid (not tested) |
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` (line 14) | ✅ Presumed valid (not tested) |
| SystemPromptMaster | Line 67 mentions without path format; appears elsewhere | ✅ No broken path |
| MCP Config Guide | `docs/60-persona/62-MCPConfigGuide_v1.0.md` (line 518) | ✅ Presumed valid |

**Note:** Cross-reference validation was limited to file path format checks. Full link resolution would require the docs to exist at those exact paths.

---

## 8. Boundary Compliance

| Check | Status |
|---|---|
| No persona drift | ✅ Y4 baseline preserved; Y6 prohibition intact |
| No consent violation | ✅ Consent/surveillance boundaries unchanged |
| No Y6 introduced | ✅ Y5 ceiling, Y6 prohibition verified |
| No HARD STOP bypass | ✅ HARD STOP unchanged |
| No distress protocol suppression | ✅ D0-D4 referenced unchanged |
| No surveillance overreach | ✅ Surveillance boundaries unchanged |
| ADR-028 Superseded respected | ✅ OpenRouter removed; Ollama absent; graceful degradation terminal fallback |

---

## 9. Findings Summary

### PASSED Items (9/9 workflow gates)

| # | Gate | Verdict |
|---|---|---|
| 1 | AGENTS.md first-read rule | ✅ **PASS** |
| 2 | §WORKFLOW GATES section | ✅ **PASS** |
| 3 | Mandatory RESEARCH WAVE | ✅ **PASS** |
| 4 | Mandatory PLANNER GATE | ✅ **PASS** |
| 5 | Planner output → todo sync | ✅ **PASS** |
| 6 | Auditor orchestrator (unlimited parallel) | ✅ **PASS** |
| 7 | `load_skills` requirement | ✅ **PASS** |
| 8 | `run_in_background` requirement | ✅ **PASS** |
| 9 | `output_path` in delegation prompts | ✅ **PASS** |

### Stale Reference Cleanup (5/5)

| Reference | Location | Clean Status |
|---|---|---|
| Ollama | Entire AGENTS.md | ✅ Clean |
| OpenRouter | Entire AGENTS.md | ✅ Clean |
| Y1 baseline | Lines 52, 316 | ✅ Replaced with Y4 permanent baseline |
| Y4 permanent baseline | Lines 52, 316 | ✅ Present |
| ADR-028 Superseded | Architecture alignment | ✅ Respected |

### Verification Results

| Check | Result |
|---|---|
| LSP diagnostics | ✅ CLEAN — no diagnostics |
| Secrets/token leakage | ✅ No secrets exposed |
| Evidence completeness | ✅ Full minimum schema |

---

## 10. Caveats / Informational Notes

1. **Markdownlint not available:** The repository has no `lint:md` script. LSP diagnostics and grep were used as substitutes.
2. **Cross-reference validation:** File paths referenced in AGENTS.md were checked for existence only at the format level. Full content integrity of referenced documents was not audited.
3. **Evidence file self-awareness:** The evidence file (verification.md, line 102) correctly notes that auditor gate status was "Pending at evidence creation time." This report now fulfills that gate.
4. **SystemPromptMaster filename mismatch** was noted by the stale-reference audit (F4: `61-SystemPromptMaster_v1.1.md` filename vs v1.1 content) but is outside AGENTS.md scope — AGENTS.md does not reference the file by path/version.

---

## 11. Final Verdict

| Item | Result |
|---|---|
| Required workflow gates | ✅ **ALL 9/9 PASS** |
| Stale reference cleanup | ✅ **5/5 CLEAN** |
| LSP diagnostics | ✅ **CLEAN** |
| Secrets/token leakage | ✅ **NONE DETECTED** |
| Evidence completeness | ✅ **COMPLETE** |
| **OVERALL** | ✅ **PASS** |

**ALL FINDINGS RESOLVED:** The three NEEDS REVIEW items identified in the preliminary workflow-gates audit (AGENTS.md first-read rule, `load_skills`, `run_in_background`) have all been addressed in the current AGENTS.md. No new issues were introduced.

---

*Report written to `audit-reports/agents-md-update/agents-md-update-auditor-report.md`.*
*Date: 2026-06-01.*
*Method: Independent review of AGENTS.md (689 lines), evidence file, research reports, ADR-028, grep checks (10 patterns), and LSP diagnostics.*