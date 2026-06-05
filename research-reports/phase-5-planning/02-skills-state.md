# Phase 5 Skills System State & Migration Plan

**Date:** 2026-06-05
**Author:** Guinevere
**Subject:** Hermes Skills Architecture Analysis for Phase 5 Migration
**Status:** RESEARCH REPORT
**Cross-Reference:** 11-SKILLS-SYSTEM.md, ADR-035, phase-5-skills.md

---

## 1. Current State Analysis

| Aspect | Finding |
|---|---|
| **Installed Skills** | **0** (Greenfield opportunity) |
| **SKILL.md Schema** | Header (Name, Version, Author, Category), Dependencies, Platforms, Tags, Purpose, Instructions, Tools Required, Configuration, Resources |
| **agentskills.io Status** | Hub reachable, search functional, multiple safety/persona results found. No proprietary Guinevere skills published yet. |
| **Proposed Bundles** | `guinevere-core`, `guinevere-safety`, `guinevere-surveillance`, `guinevere-devops` |

---

## 2. Skill Candidates (from 11-SKILLS-SYSTEM.md)

*(Note: Prompt specifies 24 candidates, but listed categories sum to 28. All listed candidates are included below.)*

| Category | Skill Candidates |
|---|---|
| **Persona (8)** | `guinevere-yandere-fsm`, `guinevere-drift-detector`, `guinevere-punishment-engine`, `guinevere-reward-engine`, `guinevere-mood-engine`, `guinevere-ritual-scheduler`, `guinevere-streak-tracker`, `guinevere-transition-rules` |
| **Safety (6)** | `guinevere-hard-stop`, `guinevere-distress-detector`, `guinevere-safe-mode`, `guinevere-consent-guard`, `guinevere-forbidden-patterns`, `guinevere-y6-prohibition` |
| **Domain (8)** | `guinevere-sdlc-workflow`, `guinevere-auditor-gate`, `guinevere-planner-gate`, `guinevere-evidence-generator`, `guinevere-subagent-delegation`, `guinevere-collision-scan`, `guinevere-research-wave`, `guinevere-doc-sync` |
| **Tool (6)** | `guinevere-postgres-wrapper`, `guinevere-redis-wrapper`, `guinevere-docker-wrapper`, `guinevere-git-workflow`, `guinevere-github-api`, `guinevere-discord-webhook` |

---

## 3. Phase 5 Priority Mapping (User's 5 Priorities)

| User Priority | Maps To (Candidates) | Backing `src/` Module | Required SKILL.md Content | Integration with `GuinevereSafetyPlugin` |
|---|---|---|---|---|
| **guinevere-hardstop** | `guinevere-hard-stop` (Safety) | `src/persona/hard_stop_handler.py` | Pre-LLM exact + semantic triggers, dual-layer detection, fail-closed block rules. | Hook `pre_prompt` + `GuinevereSafetyPlugin.on_message()` for redundancy. |
| **guinevere-memory-bridge** | `memory-guardian` (Marketplace) / Domain | `src/memory/` (DNR, classification) | DNR pipeline helpers, 5-level classification rules, hybrid read-only access constraints. | `pre_tool_call` hook consent gate + plugin DNR state enforcement. |
| **guinevere-slash-commands** | `guinevere-discord-webhook` + Plugin Arch | `src/discord/commands.py` (35 cmds) | Hermes `ctx.register_command()` patterns, auth matrix overlay rules, ephemeral response formatting. | Auth matrix validation via plugin before command execution. |
| **guinevere-consent** | `guinevere-consent-guard` (Safety) | `src/persona/consent_gate.py` (Redis DB2 / PG) | 7-step fail-closed consent verification, Redis cache fallback logic, surveillance boundary rules. | `pre_tool_call` hook reads plugin consent state; blocks if WITHDRAWN/PAUSED. |
| **guinevere-yandere** | `guinevere-yandere-fsm` (Persona) | `src/persona/yandere_fsm.py`, `mood_engine.py` | Y0-Y5 state machine, Y6 absolute prohibition, transition logging, mood decay rules. | `post_response` hook (Y6 rewrite) + plugin state tracking for Y4 baseline enforcement. |

---

## 4. Phase 5 Skill Installation Plan Mapping

From `phase-5-skills.md` Step 5.1, the 5 agentskills.io packages map to the user's priorities as **complementary enablers**, not 1:1 replacements:

| agentskills.io Package | Supports User Priority | Role in Phase 5 |
|---|---|---|
| `safety-pack` | `guinevere-hardstop`, `guinevere-consent` | Provides baseline safety enforcement helpers and fail-closed templates. |
| `persona-rituals` | `guinevere-yandere` | Supplies 5 daily ritual templates (WIB schedule) integrated into cron. |
| `mood-tracker` | `guinevere-yandere` | Handles mood analysis and persistence, feeding the Yandere FSM. |
| `memory-guardian` | `guinevere-memory-bridge` | Directly provides DNR + classification helpers for memory operations. |
| `guinevere-tone` | `guinevere-yandere` | Enforces 75/25 ID/EN ratio, address rules, and anti-kawaii suppression. |

*Note: The user's 5 priorities are architectural domains requiring custom Python backends. The agentskills.io packages are declarative instruction layers that configure the agent to use those backends correctly.*

---

## 5. Key Limitation Analysis

> *"Skills cannot express complex Python logic — keep Python backends, skills as instruction layer"*

**Architectural Implications for Phase 5:**
1. **No Logic Migration to Markdown**: Complex stateful logic (Yandere Y0-Y5 FSM, 7-step consent gate, DNR pipeline, mood decay) **must remain** in `src/persona/*.py` and `plugins/guinevere_safety_plugin.py`. SKILL.md cannot execute this.
2. **Skills as Declarative Triggers**: SKILL.md files will only contain behavioral constraints (e.g., "NEVER allow Y6"), trigger conditions (e.g., "On `pre_prompt`, invoke `hard_stop_handler.py`"), and configuration schemas (e.g., WIB cron schedules).
3. **Plugin as the Bridge**: `GuinevereSafetyPlugin` acts as the runtime bridge. The skill instructs the agent *what* to enforce; the plugin executes the Python logic and returns the verdict to the Hermes hook system.
4. **State Persistence**: Skills cannot hold state. All state (mood, streaks, consent status, yandere level) must be read/written via the plugin to PostgreSQL/Redis, not stored in the skill's local context.

---

## 6. Priority Matrix for Phase 5 Execution

| Priority | Skill / Component | Complexity | Risk | Execution Order |
|---|---|---|---|---|
| **P1** | `guinevere-hard-stop` + `safety-pack` | HIGH | CRITICAL | 1 (Blocking) |
| **P2** | `guinevere-consent` + `memory-guardian` | HIGH | CRITICAL | 2 (Blocking) |
| **P3** | `guinevere-yandere` + `mood-tracker`/`rituals` | MEDIUM | HIGH | 3 |
| **P4** | `guinevere-memory-bridge` (DNR/Classification) | MEDIUM | MEDIUM | 4 |
| **P5** | `guinevere-slash-35` (Plugin conversion) | LOW | LOW | 5 |

---

## 7. Footer

| Field | Value |
|---|---|
| **Report ID** | PH5-SKILLS-02 |
| **Version** | 1.0 |
| **Date** | 2026-06-05 |
| **Status** | COMPLETE |
| **Next Action** | Proceed to Phase 5 Step 5.1: Install priority skills and finalize SOUL.md |
