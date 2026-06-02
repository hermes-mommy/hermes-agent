# AGENTS.md v2.1 — Concise Structure Blueprint

> **Status**: Refactor proposal (read-only analysis — no edits to AGENTS.md)
> **Target line budget**: 350–400 lines (from 689)
> **Goal**: Eliminate all duplicate workflow/safety/auditor rules while preserving every mandatory section, BLOCKING item, workflow gate, safety boundary, reference table, evidence schema, tool hierarchy, §13 Footer, and §14 Tooling Notes.

---

## 1. Current Structure Audit

| Section | Lines | Lines % | Content |
|---|---|---|---|
| Header/Preamble | 1–16 | 2.3% | Project metadata, authority boundary |
| **§0 Identity** | 18–99 | 11.9% | Persona prose, interaction rules, BLOCKING list, bypass mode, trust signals |
| **§1 Super-Autopilot Mode** | 103–136 | 5.1% | Flow diagram + 8 rules |
| **§2 Execution Mandates** | 138–233 | 14.1% | 10 mandates (consent, parallel spawn, planner sequencing, collision scan, decompose, anti-dup, verification, continuation, idempotency, session coord, file-based output, auditor gate) |
| **§3 Session-Start Workflow** | 235–254 | 2.9% | 16-step session start procedure |
| **§4 Post-Step Checklist** | 256–269 | 2.0% | 10-item completion checklist |
| **§5 Anti-Pattern Catalog** | 271–332 | 9.0% | 7 categories of BLOCKING anti-patterns |
| **§6 Escalation Rules** | 334–364 | 4.5% | 5 trigger conditions |
| **§7 Operator Protocol** | 366–402 | 5.4% | Command table, auto-handle list, ask-faiz list |
| **§8 Reference Tables** | 404–444 | 5.9% | 3 reference tables (doc families, tie-breakers, suite files) |
| **§9 Repository Isolation** | 446–470 | 3.6% | Isolation policy (never share, allowed reuse) |
| **§10 Appendix A** | 472–484 | 1.9% | Full autonomous task template |
| **§11 Appendix B** | 486–499 | 2.0% | Evidence minimum schema |
| **§12 Appendix C** | 501–518 | 2.6% | Tool selection hierarchy table |
| **§13 Footer** | 520–544 | 3.6% | Versioning, maintenance, operator sign-off, closing quote |
| **§14 Tooling Notes** | 546–689 | 20.9% | 8 practical tool rules + WORKFLOW GATES + auditor gate duplicate |

**Total: ~689 lines**

---

## 2. Duplication Map

### 2.1 Auditor Rules — 6 locations, ~150 lines of overlap

| Location | Content | Proposed Action |
|---|---|---|
| §0 (BLOCKING) | "NEVER skip auditor gate" | Keep 1-line cross-ref, remove full rule text |
| §0 (Trust signals) | "auditor gate selalu di-spawn" | Remove entire Trust signals block (merge into §2) |
| §1 (Rules) | "auditors parallel + unlimited", "one step not complete until auditor passes" | Keep first mention, remove redundant expansion |
| §2.2 (step 7) | "unlimited auditor wave" | Consolidate into §2.10 single source |
| §2.10 | Per-step implementation auditor gate (full) | **KEEP as authoritative §2.10** |
| §3 (step 14) | "spawn per-step auditor" | Keep cross-ref to §2.10 |
| §4 (item 9) | "auditor gate: PASS or accepted" | Keep cross-ref to §2.10 |
| §14 (WORKFLOW GATES) | AUDITOR ORCHESTRATOR (lines 647–655) | **REMOVE** — fully redundant with §2.10 |
| §14 (Per-step auditor gate) | Full duplicate of §2.10 (lines 656–684) | **REMOVE** — verbatim re-duplication, replace with cross-ref to §2.10 |

### 2.2 Planner → Todo Sync — 4 locations, ~40 lines of overlap

| Location | Content | Proposed Action |
|---|---|---|
| §1 (Flow step 7) | "parent rewrites todos" | Keep in flow diagram (1 line) |
| §1 (Rules) | "planner-output controls execution" | **KEEP** as the authoritative rule |
| §2.5.1 | Planner output → todo sync gate (full) | **CONSOLIDATE** into §2.5, remove sub-section |
| §3 (step 9) | "read planner, rewrite todos" | Keep cross-ref to §2.5 |

### 2.3 Research Wave — 4 locations, ~35 lines

| Location | Content | Proposed Action |
|---|---|---|
| §1 (Flow step 4) | "RESEARCH WAVE" | Keep in flow diagram (1 line) |
| §2.2 (step 1) | Research wave details + tool-specific instructions | **KEEP** as authoritative §2.2.1 |
| §3 (step 7) | "Fire research wave if needed" | Keep cross-ref, remove detail |
| §14 (RESEARCH WAVE) | Full research wave gate (lines 628–636) | **REMOVE** — redundant with §2.2.1 |

### 2.4 Collision Scan — 3 locations, ~30 lines

| Location | Content | Proposed Action |
|---|---|---|
| §1 (Flow step 8) | "COLLISION SCAN" | Keep in flow diagram (1 line) |
| §2.6 | Implementation Collision Scan table | **KEEP** as authoritative §2.6 |
| §3 (step 10) | "Run collision scan before implementation" | Keep cross-ref to §2.6 |

### 2.5 File-Based Sub-Agent Output — 3 locations, ~50 lines of overlap

| Location | Content | Proposed Action |
|---|---|---|
| §0 (Trust signals) | "structured output wajib file-based" | **REMOVE** (merge into §2.9) |
| §2.9 | File-Based Sub-Agent Output | **KEEP** as authoritative |
| §14 (Sub-agent discipline) | Full duplication of §2.9 with tool-specific context (lines 602–624) | **KEEP ONLY tool-specific examples**, remove the rule text that duplicates §2.9. Keep the "BLOCKING — delegation prompt MUST include output path" as a tooling-specific enforcement note. |

### 2.6 Safety-Affecting Domains — 4 locations, ~15 lines of overlap

| Location | Content | Proposed Action |
|---|---|---|
| §0 (Yang aku jagain) | Domain list in prose | Remove, cross-ref to §2.1 |
| §0 (Bypass mode) | Domain list in safety-affecting changes | Remove, cross-ref to §2.1 |
| §2.1 | **KEEP** as single authoritative source | — |
| §6 Trigger 3 | Domain list re-listed | Remove, cross-ref to §2.1 |

### 2.7 BLOCKING Items — 2 locations, ~80 lines total overlap

| Location | Content | Proposed Action |
|---|---|---|
| §0 | "Yang aku gak pernah lakuin" — 12 NEVER items | **KEEP condensed** to 3-line summary + cross-ref to §5 |
| §5 | Full anti-pattern catalog with examples | **KEEP** as authoritative §5 |

---

## 3. Proposed v2.1 Section Structure

### Target: ~380 lines total

```text
Header/Preamble     (~10 lines)   Lines  1-10
§0 Identity          (~35 lines)   Lines  11-45
§1 Flow & Rules      (~20 lines)   Lines  46-65
§2 Mandates          (~75 lines)   Lines  66-140
§3 Session Workflow  (~12 lines)   Lines 141-152
§4 Post-Step Check   (~10 lines)   Lines 153-162
§5 Anti-Patterns     (~55 lines)   Lines 163-217
§6 Escalation        (~22 lines)   Lines 218-239
§7 Operator Protocol (~25 lines)   Lines 240-264
§8 Reference Tables  (~30 lines)   Lines 265-294
§9 Isolation         (~18 lines)   Lines 295-312
§10 Task Template    (~10 lines)   Lines 313-322
§11 Evidence Schema  (~10 lines)   Lines 323-332
§12 Tool Hierarchy   (~12 lines)   Lines 333-344
§13 Footer           (~15 lines)   Lines 345-359
§14 Tooling Notes    (~40 lines)   Lines 360-399
```
*Target total: ~399 lines*

### Rationale per section

#### Header/Preamble (~10 lines) — from 16
- Keep lines 1-3 (hero quote), lines 7-14 (project metadata, authority boundary)
- Remove the first `---` separator duplication (line 5 and 16), keep just one

#### §0 Identity (~35 lines) — from 82
- **Keep** (condensed): Opening persona paragraph (6 lines → 4 lines)
- **Keep** (condensed): "Mode operasi: dominasi absolut" (3 lines → 2 lines)
- **Keep** (condensed): "Cara aku ngomong sama kamu" — 9 bullets → 5 bullets covering: language mix, to-the-point, match mood, dominasi penuh (health check), sayang tapi no compromise
- **Keep**: "Yang aku gak pernah lakuin" — but condensed: keep as a **3-line summary** of the BLOCKING categories with cross-ref: *"Full expanded catalog with examples → §5 Anti-Pattern Catalog"*
- **Keep**: Bypass mode section — permissions, lifecycle, sticky default, auto-flag triggers, eject anytime (~15 lines, unique content)
- **Remove**: "Yang aku jagain selalu" (lines 24-31) — each point duplicates a mandate in §2
- **Remove**: "Trust signals" (lines 83-92) — duplicates §2 mandates
- **Remove**: "Apa yang aku rasain partner sama kamu" (lines 94-99) → either cut entirely or keep 1-2 lines as closing warmth

#### §1 Super-Autopilot Mode (~20 lines) — from 34
- **Keep**: Flow diagram (13 lines) — but remove line 112 "Read AGENTS.md operating contract first" (moved to §3)
- **Keep**: 4 flow-unique rules:
  - "Plan first: no implementation without decomposition"
  - "Planner-output controls execution" (but condensed to 3 lines)
  - "Delegate by default / parallel when independent"
  - "Shared docs parent-only"
- **Remove** from rules: "Auditors parallel + unlimited" (moved to §2), "One step not complete until auditor passes" (moved to §2), "No autonomous destructive ops" (moved to §5 BLOCKING)

#### §2 Execution Mandates (~75 lines) — from 96

This is the **consolidation core**. The 10 existing mandates stay but are restructured and deduplicated:

| # | Mandate | Lines | Notes |
|---|---|---|---|
| 2.1 | Consent-Safety Mandate | ~6 | Single authoritative source for safety domains list |
| 2.2 | Workflow Gates | ~18 | **NEW** — merge §2.2 (parallel spawn) + §14 RESEARCH/PLANNER/AUDITOR gates into one subsection with clear sequence |
| 2.3 | Decompose then Delegate | ~4 | Keep as-is (unique content) |
| 2.4 | Anti-Duplication Rule | ~2 | Keep as-is |
| 2.5 | Planner Sequencing & Todo Sync | ~6 | Consolidate §2.5 + §2.5.1 into one single rule |
| 2.6 | Implementation Collision Scan | ~8 | Keep table (unique content) |
| 2.7 | Parent Verification Protocol | ~7 | Keep 8-item checklist |
| 2.8 | Continuation via task_id | ~2 | Keep as-is |
| 2.9 | Idempotency & Re-run Safety | ~2 | Keep as-is |
| 2.10 | Parallel Session Coordination | ~2 | Keep as-is |
| 2.11 | File-Based Sub-Agent Output | ~8 | Consolidate §2.9 + §14 sub-agent discipline: keep the rule and BLOCKING about output_path, cross-ref to §14 for tool-specific examples |
| 2.12 | Per-Step Auditor Gate | ~10 | **SINGLE AUTHORITATIVE** — consolidate §2.10 + §14 auditor orchestrator + §14 per-step auditor gate |

**Savings achieved here:**
- §14 WORKFLOW GATES removed entirely (replaced by §2.2)
- §14 Per-step auditor gate removed entirely (replaced by §2.12)
- §14 Sub-agent discipline merged into §2.11

#### §3 Session-Start Workflow (~12 lines) — from 20
- Keep 16-step sequence but condense each to 1 line
- Replace inline details with cross-refs to §2 mandates

#### §4 Post-Step Checklist (~10 lines) — from 14
- Keep 10 items but condense descriptions
- Replace "Auditor gate: independent per-step auditor PASS" with "Auditor gate (§2.12): PASS or documented false-positive"

#### §5 Anti-Pattern Catalog (~55 lines) — from 62
- **Keep** all 7 categories and all ❌/✅ items
- Add cross-ref at top: "§0 Identity lists a condensed BLOCKING summary; this section is authoritative."

#### §6 Escalation Rules (~22 lines) — from 31
- Keep all 5 triggers
- Remove duplicate domain list in Trigger 3 (cross-ref to §2.1 instead)

#### §7 Operator Protocol (~25 lines) — from 37
- Keep all three subsections (unique content)

#### §8 Reference Tables (~30 lines) — from 41
- Keep all 3 tables with minor trimming

#### §9 Repository Isolation (~18 lines) — from 25
- Keep both tables as-is

#### §10 Full Task Template (~10 lines) — from 13
- Keep template + 3 relaxation rules

#### §11 Evidence Schema (~10 lines) — from 14
- Keep all 10 sections with 1-line descriptions

#### §12 Tool Hierarchy (~12 lines) — from 18
- Keep table, trim descriptions, remove consent-safety trailing line (covered by §2.1)

#### §13 Footer (~15 lines) — from 25
- **KEEP AS-IS**: Versioning table, maintenance checklist, operator sign-off, closing quote

#### §14 Tooling Notes (~40 lines) — from 144

| Subsection | Current Lines | Target Lines | Action |
|---|---|---|---|
| File writing | 550-570 (21) | ~12 | Keep, minor trimming |
| Editing files | 572-576 (5) | ~4 | Keep |
| Reading files | 578-582 (5) | ~4 | Keep |
| Searching | 584-588 (5) | ~4 | Keep |
| Question tool | 590-594 (5) | ~4 | Keep |
| Background tasks | 596-600 (5) | ~4 | Keep |
| Sub-agent output | 602-624 (23) | ~8 | Keep only BLOCKING + cross-ref to §2.11 |
| §WORKFLOW GATES | 626-655 (30) | **0** | **REMOVE** — redundant with §2.2 |
| Per-step auditor | 656-684 (29) | **0** | **REMOVE** — redundant with §2.12 |
| Markdown tables | 686-689 (4) | ~4 | Keep |

---

## 4. Detailed Section-by-Section Merge Plan

### Merge Plan A: Auditor Rules → Single Source in §2.12

1. Create §2.12 "Per-Step Implementation Auditor Gate" as single authoritative source containing:
   - Core rule (from current §2.10 lines 229-231)
   - Gate order 1-6 (from current §14 lines 660-667)
   - Auditor requirements (from current §14 lines 669-676)
   - Verdict handling table (from current §14 lines 678-684)
   - Parallel spawning: "unlimited wave for non-conflicting ready surfaces" (from current §2.2 step 7)
2. Replace all other auditor occurrences with cross-ref: "→ see §2.12"

### Merge Plan B: Workflow Gates → Consolidated §2.2

1. Create §2.2 "Workflow Gates" containing:
   - Prerequisite: task decomposition complete
   - **Research Wave gate** (from current §14 lines 630-636)
   - **Synthesize by parent** (from current §2.2 step 2)
   - **Planner Gate** (from current §14 lines 640-645)
   - **Collision Scan** (cross-ref to §2.6)
   - **Implementation Wave** (from current §2.2 step 5)
   - **Parent Verify** (from current §2.2 step 6)
   - **Auditor Wave** (cross-ref to §2.12)
   - **Fix/Re-audit** (cross-ref to §2.12)
   - Sub-agent spawning: run_in_background=true, load_skills, explore vs librarian routing

### Merge Plan C: File-Based Output → §2.11

1. Create §2.11 "File-Based Sub-Agent Output" containing:
   - **Core rule**: structured output → file, inline only for verdict/path/short summary
   - **BLOCKING**: delegation prompt MUST include output_path in MUST DO section
   - **Applies-to list** (from current §14 lines 610-614)
   - **Required pattern** (from current §14 lines 618-622)
   - **Allowed inline exception** (from current §14 line 624)
2. Tool-specific examples stay in §14, NOT in §2.11

### Merge Plan D: Safety Domains → Single Source in §2.1

1. §2.1 "Consent-Safety Mandate" is single authoritative source
2. All other occurrences → cross-ref to §2.1

### Merge Plan E: BLOCKING → §0 summary + §5 authoritative

1. §0 "Yang aku gak pernah lakuin" → condensed to 3-line overview with cross-ref
2. §5 stays as authoritative reference with all examples

---

## 5. Line Budget Summary

| Section | Current Lines | Target Lines | Saved |
|---|---|---|---|
| Header | 16 | 10 | 6 |
| §0 Identity | 82 | 35 | 47 |
| §1 Flow | 34 | 20 | 14 |
| §2 Mandates | 96 | 75 | 21 |
| §3 Session | 20 | 12 | 8 |
| §4 Checklist | 14 | 10 | 4 |
| §5 Anti-Patterns | 62 | 55 | 7 |
| §6 Escalation | 31 | 22 | 9 |
| §7 Operator | 37 | 25 | 12 |
| §8 Reference | 41 | 30 | 11 |
| §9 Isolation | 25 | 18 | 7 |
| §10 Template | 13 | 10 | 3 |
| §11 Evidence | 14 | 10 | 4 |
| §12 Tool Table | 18 | 12 | 6 |
| §13 Footer | 25 | 15 | 10 |
| §14 Tooling | 144 | 40 | 104 |
| **TOTAL** | **689** | **399** | **290 (42%)** |

---

## 6. Sections to Preserve UNCHANGED (or near-unchanged)

| Section | Preservation Level | Notes |
|---|---|---|
| **§13 Footer** | **100% retained** | Versioning table, maintenance checklist, operator sign-off, closing quote |
| **§14 Tooling Notes** | **Tool-specific content retained** | File writing, edit, read, grep/glob, question tool, background tasks, markdown tables — all unique tooling guidance preserved. Only removed: WORKFLOW GATES and per-step auditor gate. |
| **BLOCKING rules (§5)** | **100% retained** | All 7 categories, all ❌/✅ items |
| **Workflow gates** | **Consolidated into §2.2** | Content preserved, just moved |
| **Safety boundaries** | **Consolidated into §2.1** | Content preserved, just moved |
| **Evidence schema (§11)** | **100% retained** | All 10 sections |
| **Reference tables (§8)** | **Nearly retained** | Minor trimming only |

---

## 7. Sections Receiving Cross-Reference Links

| Section | Cross-ref Target | What to replace |
|---|---|---|
| §0 "Yang aku gak pernah lakuin" | → §5 | Remove 12-line BLOCKING list, replace with 3-line summary + cross-ref |
| §0 "Trust signals" | → §2.2, §2.11, §2.12 | Remove entire block |
| §0 "Yang aku jagain" | → §2.7 | Remove entire block |
| §1 Rule "auditors parallel" | → §2.12 | Replace 2-line rule with 1-line cross-ref |
| §3 Step 7 | → §2.2 | "Fire research wave (§2.2)" |
| §3 Step 8-9 | → §2.5 | "Planner + todo sync (§2.5)" |
| §3 Step 10 | → §2.6 | "Collision scan (§2.6)" |
| §3 Step 14 | → §2.12 | "Auditor gate (§2.12)" |
| §4 Item 9 | → §2.12 | "Auditor gate (§2.12)" |
| §6 Trigger 3 | → §2.1 | "Safety domain list in §2.1" |
| §14 Sub-agent | → §2.11 | "See §2.11 for authoritative rule" |
| §14 WORKFLOW | → §2.2, §2.12 | **REMOVED**, cross-ref to §2 |
| §14 Auditor gate | → §2.12 | **REMOVED**, cross-ref to §2 |

---

## 8. Collision Scan

| File | Writer | Notes |
|---|---|---|
| `AGENTS.md` | **Parent-only** | Per §1 rules: shared docs (AGENTS.md IS the operating contract) are parent-only. No sub-agent may edit AGENTS.md. |
| `research-reports/agents-md-refactor/concise-structure-blueprint.md` | Parent (this file) | Single writer, no collision. |

**Decision**: AGENTS.md v2.1 refactor implementation must be done by parent directly, not delegated to sub-agents.

---

## 9. Implementation Steps (for when refactor is greenlit)

1. **Pre-flight**: Backup current AGENTS.md → AGENTS.md.v2.0-backup
2. **Create new file**: Write AGENTS.md from scratch following this blueprint
3. **Preservation checklist**: Verify every BLOCKING item from §0 and §5 exists
4. **Preservation checklist**: Verify §13 footer exact content retained
5. **Preservation checklist**: Verify §14 tool-specific rules retained
6. **Verification**: grep for key terms across both files to confirm no content loss: HARD STOP, consent, Y6, Y5, DR, SOPS, as any, @ts-ignore, empty catch, auditor, planner, collision, research wave, bypass mode, Sticky default, evidence schema, Never Share, Hermes Agent, Playwright, filesystem_write_file, run_in_background
7. **Cross-reference validation**: Check all → §X.Y cross-refs resolve correctly
8. **Line count check**: Verify within 350-400 range

---

## 10. Verdict

**Path**: `research-reports/agents-md-refactor/concise-structure-blueprint.md`

**Verdict**: Ready for Faiz review.

**3-line summary**:
- AGENTS.md v2.1 can be reduced from 689→~399 lines (42% savings) by centralizing 7 duplication clusters into single authoritative sections, primarily §2 Execution Mandates.
- §0 Identity retains strong persona but drops 6 duplicate blocks; §14 Tooling Notes drops 59 lines of redundant gates/auditor rules while keeping all unique tool guidance.
- No BLOCKING, workflow gate, safety boundary, evidence schema, tool hierarchy, §13 Footer, or §14 practical rule is removed — only relocated or cross-referenced.
