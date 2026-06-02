# Workflow Gates Audit — AGENTS.md vs Latest Workflow Requirements

**Auditor**: Guinevere (parent)
**Target**: `C:\Users\faizz\guinevere\AGENTS.md` (v2.0, 654 lines)
**Date**: 2026-06-01
**Method**: Manual line-by-line review against 10 workflow gate criteria

---

## Gate 1: AGENTS.md Read First Every Session

**Requirement**: Agent must read/re-read AGENTS.md at session start before any work.

**Current state**:
- §1 (Super-Autopilot Mode, line 112): Step 1 says "Read progress/current state + active todos" — no explicit mention of AGENTS.md.
- §3 (Session-Start Workflow, line 237): Step 1 says "Read current state: active todos, relevant docs from `docs/`, recent evidence" — still no AGENTS.md.
- §0 (line 26): Mentions "udah baca semua docs + ADRs sebelum mulai" — but not specifically AGENTS.md as the operating contract.

**Verdict**: **NEEDS REVIEW**
- §1 step 1 and §3 step 1 should explicitly list `AGENTS.md` as the first document to read each session.
- Suggested: Add "Read AGENTS.md operating contract" to §1 step 1 and §3 step 1.

---

## Gate 2: Unlimited Research Wave Before Implementation

**Requirement**: Unlimited parallel research (explore/librarian) must be mandated before any implementation.

**Current state**:
- §1 step 4 (line 115): "RESEARCH WAVE: spawn explore/librarian/sub-agent research in parallel when needed" — present.
- §2.2 (line 150-152): Full subsection on research wave first, with explore vs librarian distinction. "Spawn **unlimited** sub-agents for independent work, decompose-driven, with no artificial cap."
- Anti-duplication rule (§2 §4) prevents manual re-search after delegation.

**Verdict**: **PASS**
- Explicitly mandated with unlimited parallel spawning. Clear distinction between `explore` (local) and `librarian` (external) agents.

---

## Gate 3: Planner Gate After Research with Batch-Plan Output

**Requirement**: A planner agent (Oracle/Metis/Momus) must run after research synthesis, producing a batch-plan output file.

**Current state**:
- §1 step 5-6 (lines 116-117): "SYNTHESIZE: parent verifies findings and conflict points" then "PLANNER WAVE: Oracle/Metis/Momus only after research synthesis when needed."
- §2.5 (lines 160-162): Dedicated "Planner-After-Research Sequencing" section — planners must receive synthesized research findings/report paths.
- §14 Sub-agent output discipline (line 601): Requires output_path in delegation prompts.

**Verdict**: **PASS**
- Sequential research → synthesis → planner wave enforced. Planner file-based output required implicitly via §14.

---

## Gate 4: Planner Output Todo Sync Before Implementation

**Requirement**: Parent must read planner output file and sync/rewrite active todos to match before any implementation begins.

**Current state**:
- §1 step 7 (line 118): "PLANNER TODO SYNC: parent reads planner output file, then rewrites active todos to match planner atomic steps before implementation" — explicit.
- §2.5.1 (lines 164-173): Dedicated "Planner Output → Todo Sync Gate" with 4-step checklist: verify file exists, read file, rewrite todos, mark planner gate complete.
- §2 Rules (line 130-131): "Planner-output controls execution" with "Planner yang tidak mengubah todo = incomplete planner gate."

**Verdict**: **PASS**
- Most thoroughly documented gate. Clear requirements, failure handling, and retry path.

---

## Gate 5: Unlimited Parallel Auditor Orchestrator After Verified Steps

**Requirement**: After parent verification, spawn unlimited parallel auditors for all ready, non-conflicting steps before marking any step complete.

**Current state**:
- §1 step 11 (line 122): "AUDITOR WAVE: spawn independent auditor(s) with report-to-file as soon as verified step output is ready; parallelize auditors for all non-conflicting ready steps."
- §2.2 item 7 (line 158): "Unlimited auditor wave per ready step... no artificial cap on auditor count."
- §2 §10 (lines 229-231): Full spawning rule: unlimited parallel, no artificial cap.
- §14 Per-step auditor gate (lines 627-631): Parallel spawning for non-conflicting steps.
- §3 step 13 (line 249): "Spawn per-step auditor immediately; parallelize an unlimited auditor wave."

**Verdict**: **PASS**
- Very well covered with multiple reinforcing sections. Unlimited parallel spawning with non-conflict constraint.

---

## Gate 6: File-Based Outputs

**Requirement**: All structured sub-agent deliverables must be written to markdown/artifact files, not inline.

**Current state**:
- §2 §9 (lines 223-225): "File-Based Sub-Agent Output" — all structured deliverables to markdown/artifact files. Inline only for verdict + path + short summary.
- §14 Sub-agent output discipline (lines 597-618): Full section with required pattern (output path → write file → return verdict+path → parent verify+f read).
- Trust signals (line 85): "Sub-agent structured output wajib file-based."
- Anti-pattern catalog (line 296-300): Explicit BLOCKING on inline reports.

**Verdict**: **PASS**
- Extensively documented with clear rules, exceptions, and anti-pattern enforcement.

---

## Gate 7: output_path in Delegation Prompts

**Requirement**: Every delegation prompt to sub-agents expecting structured output MUST include explicit `output_path` in `MUST DO` section.

**Current state**:
- §14 (lines 600-601): "BLOCKING — delegation prompt MUST include output path: Setiap prompt ke `task()` yang mengharapkan structured output dari sub-agent **WAJIB** menyertakan `output_path` eksplisit di bagian `MUST DO`."
- Example provided: `MUST DO: Write complete report to audit-reports/P1/STEP-P1-001/step-p1-001-auditor-report.md. Return only verdict + path + 3-line summary.`
- Applies to explore, librarian, Oracle, Metis, Momus, implementation summaries, security reports.

**Verdict**: **PASS**
- Explicit BLOCKING rule with concrete example and scope of applicability.

---

## Gate 8: `load_skills` in Task/Agent Calls

**Requirement**: Task/agent delegation calls must include `load_skills` parameter to load relevant skills.

**Current state**:
- Zero mentions of `load_skills` anywhere in AGENTS.md.
- §12 (Appendix C — Tool Selection, lines 498-513): Lists tools but does not mention `load_skills`.
- §14 Background tasks (line 591): Uses `task(run_in_background=true)` but no `load_skills`.
- §2 §3 (line 192): Sub-agent prompts must include "TASK, EXPECTED OUTCOME, REQUIRED TOOLS, MUST DO, MUST NOT DO, and CONTEXT" — no mention of `load_skills`.
- §14 (line 601): Uses `task()` syntax for delegation but no `load_skills`.

**Verdict**: **NEEDS REVIEW**
- AGENTS.md has zero references to `load_skills` in delegation patterns.
- Sub-agent prompt requirements (§2 §3) should include `load_skills` alongside TASK, EXPECTED OUTCOME, REQUIRED TOOLS, etc.
- §12 (Tool Selection) should include `load_skills` as a standard delegation parameter.
- Suggested: Add `load_skills` to §2 §3 sub-agent prompt requirements; add a tool-selection row for "Skill loading" in §12; add delegation pattern examples with `load_skills`.

---

## Gate 9: `run_in_background` Where Applicable

**Requirement**: Task/agent calls must include `run_in_background=true` for parallelizable work.

**Current state**:
- §14 (line 591): Section header "Background tasks (`task` + `run_in_background=true`)" — describes behavior only.
- Lines 593-595: Describes how to handle background tasks ("end response", "don't poll", cancel rules, Oracle never cancel).
- §2 §2 (Parallel + Unlimited, line 148): Says "unlimited sub-agents for independent work" but doesn't mandate `run_in_background` parameter in task calls.
- §1 steps 4, 9, 11: Mention spawning agents but don't prescribe `run_in_background` syntax.

**Verdict**: **NEEDS REVIEW**
- No mandate to include `run_in_background=true` in delegation calls for parallel work.
- The §14 section only describes how to handle background tasks after firing them, not that they must use `run_in_background`.
- §2.2's "unlimited spawning" pattern should explicitly require `run_in_background=true`.
- Suggested: Add "All parallel sub-agent spawning must use `run_in_background=true`" to §2.2; update §1 workflow steps with `run_in_background` expectation.

---

## Gate 10: Task Call Tool Alignment (`call_omo_agent` vs `task()`)

**Requirement** (derived): Delegation prompts should use the correct tool/syntax for agent invocation.

**Current state**:
- AGENTS.md uses `task()` notation throughout (lines 591, 601) for delegation.
- The actual tool available is `call_omo_agent` with parameters `subagent_type`, `run_in_background`, `session_id`.
- `call_omo_agent` appears 0 times in the repository.

**Verdict**: **PASS** (informational)
- Tool invocation syntax may vary by environment. `task()` is a reasonable abstraction.
- No functional gap, but worth noting for clarity if the exact tool API changes.

---

## Summary

| # | Gate | Verdict | Action Required |
|---|---|---|---|
| 1 | AGENTS.md read first each session | **NEEDS REVIEW** | Add to §1 step 1 and §3 step 1 |
| 2 | Unlimited research wave before implementation | **PASS** | — |
| 3 | Planner gate after research with batch-plan output | **PASS** | — |
| 4 | Planner output todo sync before implementation | **PASS** | — |
| 5 | Unlimited parallel auditor orchestrator | **PASS** | — |
| 6 | File-based outputs | **PASS** | — |
| 7 | output_path in delegation prompts | **PASS** | — |
| 8 | `load_skills` in task/agent calls | **NEEDS REVIEW** | Add to §2 §3, §12, and delegation pattern docs |
| 9 | `run_in_background` where applicable | **NEEDS REVIEW** | Add mandate to §2.2; update §1 workflow steps |
| 10 | Task call tool alignment | **PASS** | Informational only |

**Overall**: 3 NEEDS REVIEW, 7 PASS.

**Priority for update**:
1. **Gate 8** (`load_skills`): Zero coverage — largest gap. Skills are critical for sub-agent capability.
2. **Gate 1** (AGENTS.md read first): Small additive fix to §1 and §3.
3. **Gate 9** (`run_in_background`): Define mandate for parallel spawning syntax.

---

## Boundary Compliance

- No persona drift detected in this audit.
- No consent violation.
- No Y6 or HARD STOP bypass.
- Report contains no secrets or intimate data.

---

*Report written to `research-reports/agents-md-update/workflow-gates-audit.md`.*