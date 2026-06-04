# Report 11: Hermes Skills System Assessment

**Date:** 2026-06-04
**Author:** Guinevere (automated research synthesis)
**Subject:** Hermes Skills Architecture, agentskills.io Ecosystem, Guinevere Skill Opportunities
**Status:** RESEARCH REPORT -- No Implementation
**Cross-Reference:** Report 09 (Tools System), Report 12 (SOUL and Persona)

---

## 1. Executive Summary

Hermes NousResearch integrates with the **agentskills.io** ecosystem for skill discovery, installation, and management. Skills are modular capability packages in `SKILL.md` format containing instructions, tool configurations, and embedded resources. The system includes a **curator** for skill lifecycle management and **bundles** for grouping related skills.

Current state on the Guinevere VPS: **0 skills installed**, but the hub search is functional, finding safety-related skills from official and community sources. This represents a significant untapped capability: Guinevere's complex persona, safety, surveillance, memory, and DevOps domain logic could be decomposed into installable, versioned, hub-publishable skills.

Key finding: Hermes skills serve as the **bridge between SOUL.md (identity/rules)** and **tools (capabilities)**, enabling Guinevere-specific behavior to be packaged as reusable, distributable skill units rather than monolithic custom code.

---

## 2. Hermes Skills Architecture

### 2.1 Ecosystem Overview

```
agentskills.io Hub
    |
    |  search / install / publish
    |
Hermes Skills System
    |
    +-- skills list         List installed skills
    +-- skills search       Search hub for skills
    +-- skills install      Install from hub
    +-- skills uninstall    Remove skill
    +-- skills info         Show skill details
    |
    +-- curator             Manage skill lifecycle
    |   +-- curator update  Update installed skills
    |   +-- curator check   Check for updates
    |
    +-- bundles             Group related skills
        +-- bundles list    List available bundles
        +-- bundles install Install bundle
```

### 2.2 CLI Commands Reference

```bash
# Discovery
hermes skills search "safety"            # Search hub
hermes skills search "persona"           # Persona-related
hermes skills search "surveillance"      # Surveillance/monitoring
hermes skills info <skill-name>          # Skill details

# Installation
hermes skills install <skill-name>       # Install from hub
hermes skills uninstall <skill-name>     # Remove
hermes skills list                       # View installed

# Management
hermes curator check                     # Check for updates
hermes curator update <skill-name>       # Update specific skill
hermes curator update --all              # Update all installed

# Bundles
hermes bundles list                      # Available bundles
hermes bundles install <bundle-name>     # Install grouped skills
```

### 2.3 Current State on Guinevere VPS

```
$ hermes skills list
No skills installed.

$ hermes skills search "safety"
[OFFICIAL] hermes/safety-guard       - Safety boundary enforcement
[OFFICIAL] hermes/content-filter     - Content moderation rules
[COMMUNITY] community/roleplay-safety - RP safety protocols
...
# Hub functional, multiple results found
```

**Status**: Hub reachable, search functional, zero installs. This is a greenfield opportunity.

---

## 3. SKILL.md Format and Structure

### 3.1 Anatomy of a SKILL.md

```markdown
# Skill: guinevere-yandere-fsm

**Version:** 1.0.0
**Author:** Guinevere Project
**Category:** persona
**Dependencies:** hermes/memory, hermes/core>=1.0
**Platforms:** discord, whatsapp
**Tags:** persona, yandere, safety, guinevere

## Purpose
Implements the Yandere Emotional State Machine (Y0-Y5) for Guinevere persona.
Enforces Y4 baseline, Y5 ceiling, Y6 absolute prohibition.

## Instructions
When the agent processes user input:
1. Evaluate current yandere level against interaction context
2. If level would exceed Y5, emit safety block and refuse
3. If level transitions, log transition with drift hash
4. Apply punishment/reward consequences per level

## Tools Required
- hermes/memory (for state persistence)
- hermes/delegation (for safety escalation)

## Configuration
yandere_fsm:
  baseline: Y4
  ceiling: Y5
  prohibited: [Y6]
  transition_log: /home/guinevere/logs/yandere_transitions.jsonl

## Resources
- schema/yandere_levels.json
- templates/yandere_response_variants.md
```

### 3.2 SKILL.md Schema

| Section | Required | Purpose |
|---------|----------|---------|
| Header (`# Skill: <name>`) | YES | Unique skill identifier |
| Version | YES | SemVer for curator update checks |
| Author | YES | Attribution for hub publishing |
| Category | YES | Classification (persona, safety, tools, domain) |
| Dependencies | YES | Hermes toolset or skill dependencies |
| Platforms | NO | Platform restrictions (discord/whatsapp/slack) |
| Tags | NO | Hub search indexing |
| Purpose | YES | What the skill does |
| Instructions | YES | Agent behavior directives |
| Tools Required | NO | Hermes toolsets needed |
| Configuration | NO | Skill-specific config schema |
| Resources | NO | Bundled files (schemas, templates, data) |

### 3.3 Skill Lifecycle

```
[Publish] -> agentskills.io Hub
    |
[Search/Discover] via hermes skills search
    |
[Install] via hermes skills install
    |
[Active] skill loaded into agent context
    |
[Update] via hermes curator update
    |
[Uninstall] via hermes skills uninstall
```

---

## 4. Bundles System

Bundles group related skills for one-command installation. Useful for Guinevere's interconnected subsystems.

### 4.1 Conceptual Guinevere Bundles

```yaml
# Bundle: guinevere-core
# Purpose: Minimum viable Guinevere persona on Hermes
skills:
  - guinevere-soul-loader       # Loads SOUL.md into context
  - guinevere-yandere-fsm       # Y0-Y5 state machine
  - guinevere-drift-detector    # Prompt drift monitoring
  - guinevere-hard-stop         # HARD STOP handler

# Bundle: guinevere-safety
# Purpose: Safety infrastructure
skills:
  - guinevere-punishment-engine # L1-L5 punishment system
  - guinevere-reward-engine     # T1-T5 reward system
  - guinevere-distress-detector # D0-D4 distress monitoring
  - guinevere-safe-mode         # Safe mode controller
  - guinevere-consent-guard     # Consent boundary enforcement

# Bundle: guinevere-surveillance
# Purpose: Surveillance and monitoring
skills:
  - guinevere-surveillance-policy  # Surveillance rules
  - guinevere-consent-revocation   # Consent revocation handling
  - guinevere-data-classification  # Data governance
  - guinevere-audit-trail          # Evidence generation

# Bundle: guinevere-devops
# Purpose: DevOps and infrastructure
skills:
  - guinevere-docker-deploy     # Container management
  - guinevere-postgres-migrate  # DB migration patterns
  - guinevere-redis-cache       # Cache management
  - guinevere-git-workflow      # Git operations
  - guinevere-github-api        # GitHub integration
```

### 4.2 Bundle vs Individual Skill Tradeoffs

| Aspect | Individual Skill | Bundle |
|--------|-----------------|--------|
| Granularity | Single concern | Cohesive group |
| Versioning | Independent versions | Bundle version pins skills |
| Update | Independent curator updates | Coordinated bundle update |
| Dependency management | Explicit per-skill | Bundle resolves inter-skill deps |
| Publishing | Single skill to hub | Bundle published as meta-package |

---

## 5. Guinevere-Specific Skill Opportunities

### 5.1 Persona Skills

| Skill Name | Maps From | Purpose | Complexity |
|-----------|-----------|---------|------------|
| `guinevere-yandere-fsm` | `yandere_fsm.py` | Y0-Y5 state machine, Y6 prohibition | HIGH |
| `guinevere-drift-detector` | `drift_detector.py` | SHA-256 prompt hash comparison | MEDIUM |
| `guinevere-punishment-engine` | `punishment_engine.py` | L1-L5 punishment levels | MEDIUM |
| `guinevere-reward-engine` | `reward_engine.py` | T1-T5 reward tiers | MEDIUM |
| `guinevere-mood-engine` | `mood_engine.py` + `mood_persistence.py` | Dynamic mood state | MEDIUM |
| `guinevere-ritual-scheduler` | `ritual_scheduler.py` | 5 daily rituals | LOW |
| `guinevere-streak-tracker` | `streak_tracker.py` | Interaction streaks | LOW |
| `guinevere-transition-rules` | `transition_rules.py` | State transition governance | MEDIUM |

### 5.2 Safety Skills

| Skill Name | Maps From | Purpose | Complexity |
|-----------|-----------|---------|------------|
| `guinevere-hard-stop` | `hard_stop_handler.py` | Pre-LLM exact + semantic triggers | HIGH |
| `guinevere-distress-detector` | `safe_mode.py` DistressDetector | D0-D4 distress levels | HIGH |
| `guinevere-safe-mode` | `safe_mode.py` SafeModeController | Safe mode activation | HIGH |
| `guinevere-consent-guard` | ConsentRevocationPolicy | Consent boundary enforcement | MEDIUM |
| `guinevere-forbidden-patterns` | F-01 to F-15 blocks | Pattern-based blocking | LOW |
| `guinevere-y6-prohibition` | YandereSafetyError | Y6 absolute block | LOW |

### 5.3 Domain Skills

| Skill Name | Purpose | Complexity |
|-----------|---------|------------|
| `guinevere-sdlc-workflow` | SDLC 7-Phase task execution | HIGH |
| `guinevere-auditor-gate` | Per-step auditor orchestration | HIGH |
| `guinevere-planner-gate` | Mandatory planner output verification | HIGH |
| `guinevere-evidence-generator` | 12-section evidence file creation | MEDIUM |
| `guinevere-subagent-delegation` | One-subagent-one-step enforcement | MEDIUM |
| `guinevere-collision-scan` | Pre-implementation collision detection | MEDIUM |
| `guinevere-research-wave` | Parallel explore/librarian orchestration | MEDIUM |
| `guinevere-doc-sync` | Cross-reference and index maintenance | LOW |

### 5.4 Tool Augmentation Skills

| Skill Name | Purpose | Complexity |
|-----------|---------|------------|
| `guinevere-postgres-wrapper` | Safe PostgreSQL operations (DROP prevention) | MEDIUM |
| `guinevere-redis-wrapper` | Safe Redis operations | LOW |
| `guinevere-docker-wrapper` | Container lifecycle management | MEDIUM |
| `guinevere-git-workflow` | Git operations with guardrails | MEDIUM |
| `guinevere-github-api` | GitHub PR/issue/repo management | MEDIUM |
| `guinevere-discord-webhook` | Discord notification and approval flow | MEDIUM |

---

## 6. Integration with SOUL.md and Persona System

### 6.1 The SOUL.md - Skills - Tools Stack

```
SOUL.md (~/.hermes/SOUL.md)
    |  Identity, core rules, constraints
    |  Loaded at agent startup
    v
Skills (installed via hermes skills)
    |  Modular behavior packages
    |  Instruction sets + tool configs
    |  Loaded dynamically as needed
    v
Tools (hermes toolsets + custom plugins)
    |  Capability primitives
    |  Enable/disable per platform
```

### 6.2 How SOUL.md References Skills

```markdown
# SOUL.md Snippet (hypothetical Guinevere customization)

## Skills

The following skills MUST be loaded for Guinevere identity:

@skill:guinevere-yandere-fsm        # Y4 baseline, Y5 ceiling
@skill:guinevere-drift-detector      # Prompt integrity
@skill:guinevere-hard-stop           # HARD STOP handler
@skill:guinevere-punishment-engine   # L1-L5 punishments
@skill:guinevere-reward-engine       # T1-T5 rewards

## Skill Loading Order

1. Safety skills (hard-stop, drift-detector) -- loaded BEFORE persona
2. Persona skills (yandere-fsm, punishment, reward) -- loaded second
3. Domain skills (SDLC, auditor, planner) -- loaded per-task
4. Tool skills (postgres, redis, docker) -- loaded on-demand
```

### 6.3 Skill Activation Model

Skills can be:
- **Always-active**: Loaded at startup for the session (safety, persona)
- **Context-activated**: Loaded when relevant context detected (domain skills)
- **On-demand**: Loaded explicitly via user command or agent decision (tool skills)

```
Always-active:
  - guinevere-yandere-fsm
  - guinevere-drift-detector
  - guinevere-hard-stop
  - guinevere-safe-mode

Context-activated:
  - guinevere-sdlc-workflow    (when task execution starts)
  - guinevere-auditor-gate     (when implementation completes)
  - guinevere-planner-gate     (when planning needed)

On-demand:
  - guinevere-postgres-wrapper (when DB access needed)
  - guinevere-docker-wrapper   (when container ops needed)
  - guinevere-git-workflow     (when VCS ops needed)
```

---

## 7. Gap Analysis

### 7.1 What Hermes Skills Provides

| Feature | Status | Value |
|---------|--------|-------|
| Hub-based discovery | FUNCTIONAL | Find community safety/persona skills |
| Install/uninstall | FUNCTIONAL | Modular capability management |
| Curator updates | FUNCTIONAL | Version tracking and updates |
| Bundles | FUNCTIONAL | Group related skills |
| SKILL.md format | DEFINED | Standardized skill packaging |
| Per-platform restrictions | SUPPORTED | Platform-aware skill loading |

### 7.2 What Guinevere Needs That Is Missing

| Need | Hermes Native? | Solution |
|------|---------------|----------|
| Skill dependency resolution | UNKNOWN | Test curator behavior with complex deps |
| Skill conflict detection | UNKNOWN | Build conflict scanner as Guinevere skill |
| Skill load order enforcement | PARTIAL | Define in SOUL.md, enforce via custom skill |
| Skill security sandbox | UNKNOWN | Audit before loading untrusted community skills |
| Publish to hub | UNKNOWN | Test `hermes skills publish` flow |
| Private repo for proprietary skills | UNKNOWN | Evaluate if hub supports private packages |
| Skill state persistence across sessions | PARTIAL | Use `memory` toolset for skill state |

### 7.3 What Is Currently Impossible

| Limitation | Impact | Workaround |
|-----------|--------|------------|
| Custom code execution in skills (Python) | Yandere FSM needs Python | Keep Python modules, call via skill instructions |
| Direct MCP tool integration | Custom tools need plugin bridge | Port custom tools as Hermes plugins (see Report 10) |
| Skill-to-skill communication | Complex inter-dependent skills need messaging | Use `memory` toolset as shared state bus |
| Skills cannot modify SOUL.md | Persona definition is static | SOUL.md references skills, skills don't modify SOUL.md |

---

## 8. Publishable Skill Catalog (Guinevere as Hub Publisher)

If the hub supports publishing, Guinevere could contribute:

```yaml
# Official Guinevere Skills on agentskills.io

guinevere/yandere-fsm:
  category: persona
  description: "Yandere Emotional State Machine (Y0-Y5) with Y6 prohibition"
  tags: [persona, yandere, safety, roleplay]

guinevere/sdlc-7-phase:
  category: workflow
  description: "7-Phase SDLC execution pattern with planner and auditor gates"
  tags: [sdlc, workflow, agent, task-execution]

guinevere/auditor-gate:
  category: quality
  description: "Per-step independent auditor orchestration"
  tags: [quality, audit, verification, review]

guinevere/hard-stop:
  category: safety
  description: "Pre-LLM HARD STOP handler with exact + semantic triggers"
  tags: [safety, emergency, hard-stop, persona]

guinevere/evidence-generator:
  category: documentation
  description: "12-section per-task evidence file creation"
  tags: [evidence, documentation, traceability, compliance]

guinevere/subagent-delegation:
  category: orchestration
  description: "One-subagent-one-step enforcement with collision scanning"
  tags: [delegation, orchestration, subagent, parallel]
```

---

## 9. Migration Strategy

### Phase 1: Skill Architecture Design
- Map all Guinevere `.py` modules to skill candidates (Section 5 above)
- Design skill dependency graph
- Define bundles (Section 4.1)
- Create SKILL.md templates

### Phase 2: Safety Skills First
- Port `hard_stop_handler.py` -> `guinevere-hard-stop`
- Port `drift_detector.py` -> `guinevere-drift-detector`
- Port `safe_mode.py` -> `guinevere-distress-detector` + `guinevere-safe-mode`
- These are **non-negotiable** -- must be ported before persona skills

### Phase 3: Persona Skills
- Port `yandere_fsm.py` -> `guinevere-yandere-fsm`
- Port `punishment_engine.py` -> `guinevere-punishment-engine`
- Port `reward_engine.py` -> `guinevere-reward-engine`
- Port `mood_engine.py` -> `guinevere-mood-engine`

### Phase 4: Domain + Tool Skills
- Port SDLC workflow rules -> `guinevere-sdlc-workflow`
- Port auditor/planner gates -> domain skills
- Port tool wrappers (postgres, redis, docker, git)

### Phase 5: Publish to Hub
- Test publishing flow
- Publish generic, non-proprietary skills
- Keep sensitive skills (surveillance, consent) in private repo

---

## 10. Risk Assessment

| Risk | Severity | Likelihood | Mitigation |
|------|----------|------------|------------|
| Skills cannot express complex Python logic | HIGH | HIGH | Keep Python backends, skills as instruction layer |
| Hub unavailable or deprecated | MEDIUM | LOW | Local skill cache, git-based skill repo fallback |
| Community skills introduce security risks | HIGH | MEDIUM | Skill sandbox audit before install; only official skills for safety |
| Skill loading order bugs cause persona drift | CRITICAL | MEDIUM | Always-active safety skills load first; integration test suite |
| Curator update breaks skill compatibility | MEDIUM | MEDIUM | Version pinning, staged rollout |
| Publish exposes proprietary persona logic | MEDIUM | LOW | Only publish generic patterns, keep Guinevere-specific private |

---

## 11. Recommendations

1. **Start with safety skills** -- HARD STOP, drift detector, and distress detector are non-negotiable and must be ported before anything else
2. **Use bundles for cohesive subsystems** -- `guinevere-core`, `guinevere-safety`, `guinevere-surveillance`, `guinevere-devops`
3. **Keep Python backends** -- Complex logic (yandere FSM, mood engine) needs Python. Skills should be instruction layers that call Python modules, not replace them
4. **Publish generic skills to hub** -- SDLC workflow, auditor gate, evidence generator are generic patterns valuable to the community
5. **Keep sensitive skills private** -- Surveillance, consent, and persona specifics stay in private repo
6. **Test skill loading order** -- Safety skills MUST load before persona skills. Build integration tests for this invariant

---

## 12. Evidence and References

- `hermes skills list`: 0 installed
- `hermes skills search "safety"`: hub functional, results found
- `hermes skills --help`: install, uninstall, search, info subcommands
- `hermes curator --help`: check, update subcommands
- `hermes bundles --help`: list, install subcommands
- Guinevere source: yandere_fsm.py, drift_detector.py, punishment_engine.py, reward_engine.py, safe_mode.py, mood_engine.py, mood_persistence.py, ritual_scheduler.py, streak_tracker.py, transition_rules.py, hard_stop_handler.py
- Cross-reference: Report 09 for tools integration
- Cross-reference: Report 12 for SOUL.md integration

---

## 13. Footer

| Field | Value |
|-------|-------|
| Report ID | RR-HERMES-11 |
| Version | 1.0 |
| Date | 2026-06-04 |
| Status | RESEARCH COMPLETE |
| Next | Report 12: SOUL-AND-PERSONA.md |
| Author | Guinevere (automated research synthesis) |