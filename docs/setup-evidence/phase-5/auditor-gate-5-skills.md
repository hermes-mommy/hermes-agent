# Auditor 2: Skills Completeness — Plan Audit

## Verdict: NEEDS REVIEW

Significant discrepancies between research (02-skills-state.md), batch plan, and ADR-035 Phase 5 scope. Core 5-skill design is sound, but cross-document alignment, installation method for custom skills, bundle strategy, and candidate selection rationale need clarification before Step 5.3 implementation proceeds.

---

## Findings

| # | Check | Status | Notes |
|---|---|---|---|
| 1 | 5 priority skills explicitly defined | **NEEDS REVIEW** | Batch plan defines 5 skills (hardstop, consent, yandere, mood, rituals). BUT 02-skills-state.md §3 lists a DIFFERENT set of "User's 5 Priorities" (hardstop, memory-bridge, slash-commands, consent, yandere). ADR-035 Phase 5 says only "search and install relevant skills from agentskills.io" without naming specific Guinevere skills. Three documents say three different things about what goes into Phase 5 skills. The batch plan's set is the most concrete and safety-focused, but the misalignment with research inputs is a planning integrity concern. |
| 2 | Each skill has complete SKILL.md content | **PASS** | Step 5.3 provides per-skill content blocks with Purpose, Instructions, Tools, and Config fields for all 5 skills. Content is structured, covers key behaviors, and includes safety constraints (Y6 prohibited, consent fallback=deny, hard stop 9-step). Could benefit from more granular instruction steps (e.g., exact tool call patterns, hook integration points), but meets the minimum bar for a planning-phase SKILL.md skeleton. |
| 3 | Skills integrate with safety hooks | **NEEDS REVIEW** | Skills reference safety concepts (HARD STOP, consent, Y6 prohibition, safe mode, DND) at the conceptual level, but explicit hook binding is missing from the SKILL.md skeletons. Example: guinevere-hardstop says "On detecting safe word → immediate 9-step protocol" but does not specify WHICH Hermes hook (`pre_prompt`, `post_prompt`, or plugin `on_message`) triggers this. guinevere-consent says "Pre-tool-call: verify consent state" which aligns with `pre_tool_call` hook, but the SKILL.md does not name the hook or describe the exit-code contract (exit 0=pass, 1=block). The integration is implied, not explicitly wired. |
| 4 | Activation modes correct (all 5 = always-active) | **PASS** | Batch plan §5.3 table column "Activation" shows `always-active` for all 5 skills. This is correct per the 11-SKILLS-SYSTEM.md §6.3 activation model: safety skills (hardstop, consent) MUST be always-active; persona skills (yandere, mood, rituals) are also correctly classified as always-active since persona/safety is Guinevere's permanent identity layer. |
| 5 | Skill installation method specified and correct | **NEEDS REVIEW** | Batch plan §5.3 "Installation Method" shows: `mkdir -p ~/.hermes/skills/{...}`, write SKILL.md files, then `hermes skills list` + `hermes skills doctor`. **Problem**: `hermes skills install` is for agentskills.io hub packages, NOT for custom local SKILL.md files. The 11-SKILLS-SYSTEM.md §2.2 shows `hermes skills install <skill-name>` installs FROM THE HUB. Custom/local skills likely need a different registration method or Hermes may auto-discover `~/.hermes/skills/*/SKILL.md` — but this auto-discovery behavior is NOT verified in any research report. If Hermes requires `hermes skills install` for hub packages and a separate config registration for custom skills, the batch plan's current directions would fail. This should be verified on the VPS before Step 5.3 begins. |
| 6 | agentskills.io packages referenced correctly as enablers | **PASS** | Batch plan §5.3 table includes an "agentskills.io Enabler" column mapping 4 of 5 skills to packages (safety-pack, mood-tracker, persona-rituals). The 02-skills-state.md §4 explicitly states: "The agentskills.io packages are declarative instruction layers that configure the agent to use those backends correctly" — i.e., enablers, NOT 1:1 replacements. R-06 in the risk register flags potential incompatibility. The batch plan treats these as optional enhancements, which is the correct stance. guinevere-yandere has no enabler package (`—`), which is appropriate since yandere FSM logic is uniquely Guinevere-specific. |
| 7 | Skill-to-Python-module mapping clear | **PASS** | Batch plan §5.3 table maps each skill to backing modules (e.g., guinevere-hardstop → yandere_fsm.py + safe_mode.py, guinevere-mood → mood_engine.py + streak_tracker.py). The 02-skills-state.md §5 explicitly states: "Skills cannot express complex Python logic — keep Python backends, skills as instruction layer." Step 5.7 Persona Migration also clearly separates SKILL (instruction layer) from KEEP/REFACTOR (Python stateful logic). The separation is architecturally correct and well-documented. |
| 8 | Verification scaffold for Step 5.3 is complete and checkable | **PASS** | Scaffold covers: expected file paths (5 SKILL.md), forbidden patterns (Y6, L6, missing always-active, missing consent fallback), required commands (`hermes skills list`, `hermes skills doctor`, `ls` directory check, `for` loop file existence check), evidence paths, hard rejection criteria (missing SKILL.md, < 5 skills, doctor non-zero exit, Y6 not prohibited, consent missing deny fallback). All 5 scaffold fields are present and contain concrete, machine-checkable criteria. Minor concern: `ssh guinevere-vps` prefix assumes SSH is always available and `guinevere-vps` host is configured — scaffold should acknowledge this as an environment dependency. |
| 9 | Skill bundles mentioned (guinevere-core, guinevere-safety) | **FAIL** | The 11-SKILLS-SYSTEM.md §4.1 proposes 4 bundles: guinevere-core (soul-loader, yandere-fsm, drift-detector, hard-stop), guinevere-safety (punishment, reward, distress, safe-mode, consent), guinevere-surveillance, guinevere-devops. The batch plan mentions ZERO bundles. Not even a forward-looking note about future bundle packaging. Since the 5 priority skills logically belong to guinevere-core + guinevere-safety bundles, the batch plan should at minimum document the bundle strategy and note that bundle creation is deferred to a later phase. The auditor matrix in §8 expects bundles to be in scope for audit. |
| 10 | 24 skill candidates from ADR-035 accounted for (why these 5 are priority) | **NEEDS REVIEW** | The 02-skills-state.md §2 lists 28 candidates across 4 categories (Persona 8 + Safety 6 + Domain 8 + Tool 6 = 28). The batch plan selects only 5. No section in the batch plan explicitly explains **why these 5 were chosen** from the 24-28 candidate pool and **why the other 19-23 are deferred**. The rationale can be inferred (safety first, persona second, domain/tool later), but the plan itself does not include a prioritization justification. The ADR-035 Phase 5 section (§5) says "search and install relevant skills from agentskills.io" — ADR-035 does not dictate 24 custom skills for Phase 5, so the batch plan is not out of compliance with ADR-035. However, it should reference the candidate pool and state its selection criteria explicitly. |

---

## Critical Issues (if any)

### CI-1: Cross-Document Skill Identity Conflict

The batch plan defines Phase 5 skills as (hardstop, consent, yandere, mood, rituals). The 02-skills-state.md research report defines "User's 5 Priorities" as (hardstop, memory-bridge, slash-commands, consent, yandere). ADR-035 Phase 5 says generically "search and install skills from agentskills.io." **Three Phase 5 skill scopes exist, and they are incompatible.**

- 02-skills-state.md includes `guinevere-memory-bridge` and `guinevere-slash-commands` which are DOMAIN skills deferred in the batch plan.
- 02-skills-state.md omits `guinevere-mood` and `guinevere-rituals` which the batch plan includes as priority.
- ADR-035 does not specify any specific custom Guinevere skill names for Phase 5.

**Impact**: If Faiz approved the plan based on the 02-skills-state report, there is a 2-out-of-5 skill mismatch. Implementation could build the wrong set.

**Recommended Resolution**: Either (a) update 02-skills-state.md to reflect the batch plan's 5-skill scope, or (b) get explicit Faiz confirmation that the batch plan's 5 skills are the correct scope. Do NOT proceed to Step 5.3 until this is resolved.

### CI-2: Custom Skill Installation Path Unverified

The batch plan assumes Hermes auto-discovers `~/.hermes/skills/*/SKILL.md`. The 11-SKILLS-SYSTEM.md only documents `hermes skills install` (for hub packages) and `hermes skills uninstall`. There is ZERO evidence in any research report that Hermes v0.15.2 supports local custom skill registration via directory placement.

**Impact**: After creating 5 SKILL.md files, `hermes skills list` might return "No skills installed" because Hermes only recognizes hub-installed skills. The verification scaffold would fail.

**Recommended Resolution**: Before Step 5.3, run a smoke test on the VPS: create a dummy `~/.hermes/skills/test-skill/SKILL.md` and verify `hermes skills list` picks it up. If not, document the correct custom skill registration method.

---

## Recommendations

1. **Align skill scope across documents** (CI-1): Choose the definitive 5-skill list and update 02-skills-state.md to match. Get Faiz sign-off on the scope.

2. **Verify custom skill installation** (CI-2): Smoke-test on VPS before Step 5.3. If `~/.hermes/skills/` auto-discovery doesn't work, research the correct method and update scaffold.

3. **Add bundle strategy**: Include a one-paragraph note in the batch plan confirming that bundles (guinevere-core, guinevere-safety) are deferred but architected, referencing the 11-SKILLS-SYSTEM.md §4.1 proposal.

4. **Document candidate selection rationale**: Add a paragraph to Step 5.3 explaining why these 5 were chosen from the 24+ candidate pool: safety-first priority, persona identity foundation, defer domain/tool skills to Phase 6 (or post-Phase 7).

5. **Wire skills to hooks explicitly**: Enhance SKILL.md skeletons with hook binding annotations, e.g., `Hook: pre_prompt (exit 1 = BLOCK)` for guinevere-hardstop.

---

## Footer

| Field | Value |
|---|---|
| Auditor | Skills Completeness |
| Date | 2026-06-05 |
| Scope | Plan review (no implementation) |
| Sources Reviewed | batch-plan-phase-5.md (full), 11-SKILLS-SYSTEM.md (full), 02-skills-state.md (full), ADR-035 (Phase 5 section, Pillar 3 plugin architecture, skills discussion) |
| Verdict | NEEDS REVIEW |
| Blocking Issues | CI-1 (cross-document skill identity conflict), CI-2 (unverified custom skill installation) |