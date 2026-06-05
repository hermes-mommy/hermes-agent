# Phase 5 Skills Subsystem — Readiness & Smoke-Test Assessment

**Date:** 2026-06-05
**Author:** Guinevere (Sisyphus-Junior, Parent)
**Subject:** VPS Hermes Skills subsystem state, discovery behavior, smoke-test feasibility for Phase 5
**Status:** RESEARCH REPORT — Read-Only, No Implementation
**Cross-Reference:** 11-SKILLS-SYSTEM.md, phase-5-skills.md, batch-plan-phase-5.md, auditor-gate-5-skills.md, 02-skills-state.md (planning phase)

---

## 1. Executive Summary

The Hermes skills subsystem on the Guinevere VPS is **greenfield**: 0 skills installed, hub search functional, but **custom skill auto-discovery is UNVERIFIED** and the planned installation method (directory-based `~/.hermes/skills/*/SKILL.md`) has **no evidence of support** in Hermes v0.15.2. This is the single highest-risk item for Phase 5 Step 5.3.

**Blocker (CI-2 from audit):** Batch plan assumes Hermes auto-discovers `~/.hermes/skills/*/SKILL.md`, but all documented CLI commands (`hermes skills install`) target the agentskills.io hub. No documentation or code evidence exists for local/custom skill directory registration.

**Critical Fix Required Before Step 5.3:** Run the pre-flight smoke test to verify whether directory-based discovery works, or find the correct custom skill registration method.

---

## 2. Current Installed Skills

### 2.1 VPS State: 0 Installed

Confirmed across multiple research reports:

| Source | Evidence | Date |
|---|---|---|
| `11-SKILLS-SYSTEM.md` §2.3 | `hermes skills list → "No skills installed."` | 2026-06-04 |
| `02-skills-state.md` (planning) §1 | `Installed Skills: 0 (Greenfield opportunity)` | 2026-06-05 |
| VPS git status (untracked `.hermes/`) | No `.hermes/skills/` directory in untracked files | 2026-06-05 |

**VPS `.hermes/` directory structure** (from git untracked list + local `.hermes/`):

```
~/.hermes/
├── plugins/
│   └── guinevere-safety/
│       ├── plugin.yaml          # Hooks: pre_llm_call, post_llm_call, pre_tool_call, post_tool_call, transform_llm_output, on_session_start
│       └── __init__.py
├── config.yaml                  # Gateway config (Discord, LLM, hooks, MCP, cron, observability, auth_matrix)
├── SOUL.md                      # ~278 lines, Guinevere persona identity + constraints
├── crontab.yaml                 # 5 ritual cron jobs + 3 system maintenance jobs (in config.yaml, not separate file yet)
├── .env                         # (deployed from .env.template — not in repo)
├── hooks/                       # Shell hooks directory
│   ├── consent_gate.py
│   ├── dnr_filter.py
│   ├── hard_stop.py
│   ├── drift_check.py
│   ├── safety_scan.py
│   ├── error_classifier.py
│   ├── budget_check.py
│   ├── budget_lua.py
│   ├── budget_lua_extended.py
│   ├── _hook_utils.py
│   └── __pycache__/
└── state.db                     # Hermes SQLite state (104 KB, 26 messages, 2 sessions)
```

**No `~/.hermes/skills/` directory exists on the VPS.**

### 2.2 agentskills.io Hub Search

From `11-SKILLS-SYSTEM.md` §2.3:

```
$ hermes skills search "safety"
[OFFICIAL] hermes/safety-guard       - Safety boundary enforcement
[OFFICIAL] hermes/content-filter     - Content moderation rules
[COMMUNITY] community/roleplay-safety - RP safety protocols
```

The hub is reachable and search functional. However, **no proprietary Guinevere skills have been published** to agentskills.io, and no `hermes skills install` has ever been run.

---

## 3. Hermes CLI Skills Commands — Documented Reference

From `11-SKILLS-SYSTEM.md` §2.1–2.2, the documented Hermes skills CLI:

| Command | Purpose | Evidence |
|---|---|---|
| `hermes skills list` | List installed skills | Documented in research report |
| `hermes skills search <term>` | Search agentskills.io hub | Functional on VPS |
| `hermes skills install <name>` | Install from hub | Never executed |
| `hermes skills uninstall <name>` | Remove installed skill | Never executed |
| `hermes skills info <name>` | Show skill details | Never executed |
| `hermes curator check` | Check for updates | Never executed |
| `hermes curator update <name>` / `--all` | Update installed skills | Never executed |
| `hermes bundles list` | List available bundles | Never executed |
| `hermes bundles install <name>` | Install bundle | Never executed |

**Critical observation:** There is NO documented command for registering a local/custom skill. No `hermes skills register`, `hermes skills add-local`, `hermes skills link`, or `hermes skills import` subcommand exists in any research report.

---

## 4. Custom Skill Discovery — The Unverified Assumption

### 4.1 The Assumption

The batch plan (`batch-plan-phase-5.md` §Step 5.3) and the migration doc (`phase-5-skills.md`) assume that placing a `SKILL.md` file in `~/.hermes/skills/<skill-name>/SKILL.md` will cause Hermes to auto-discover it, and `hermes skills list` will show it.

**Source of this assumption:** The `11-SKILLS-SYSTEM.md` §3 SKILL.md format is described as a "standardized skill packaging" mechanism, and §6.3 describes an activation model with "always-active" skills loaded at startup. However, §2.2 only documents hub-based installation commands. **No research report has actually verified directory-based auto-discovery.**

### 4.2 What We Know About Hermes Skill Storage

From the available research:

1. **Hermes config.yaml does NOT have a `skills:` section.** The current `config.yaml` on VPS (read in full) has: `discord`, `model`, `providers`, `budget`, `agent`, `memory`, `hooks`, `mcp_servers`, `cron`, `observability`, `auth_matrix`, `approval`, `audit`. No `skills` key exists.

2. **`~/.hermes/skills/` does not exist** on the VPS. If Hermes relies on this directory for auto-discovery, it has never been tested.

3. **The `hermes skills install` flow** presumably writes to some internal state store (likely `~/.hermes/state.db` or a dedicated skill manifest). The skill content would be downloaded from the hub, not read from a local directory.

4. **No source code** for Hermes v0.15.2 skill management is available in this repo to verify discovery behavior.

### 4.3 Possible Custom Skill Registration Methods

| Method | Likelihood | Verification Needed |
|---|---|---|
| **Directory auto-discovery** (`~/.hermes/skills/*/SKILL.md`) | UNKNOWN — assumption in batch plan | Smoke test: create dummy, run `hermes skills list` |
| **Config.yaml `skills:` section** adding local paths | POSSIBLE — common pattern in similar tools | Check Hermes docs for `skills_path` config key |
| **`hermes skills install --local <path>`** | POSSIBLE — check `--help` for hidden flags | Run `hermes skills install --help` on VPS |
| **Manual state.db registration** | UNLIKELY — fragile, unsupported | Avoid unless desperate |
| **Only hub packages supported** | POSSIBLE — worst case | Would require publishing to agentskills.io |

---

## 5. Smoke-Test Feasibility

### 5.1 Pre-Flight Smoke Test (CI-2 Resolution)

This is the **mandatory first action** before any Phase 5 skill creation. The test is non-destructive and reversible.

**Proposed procedure** (from batch-plan-phase-5.md §Step 5.3 Pre-Flight):

```bash
# Step 1: Create dummy skill directory
ssh guinevere-vps "mkdir -p ~/.hermes/skills/test-discovery"

# Step 2: Create minimal SKILL.md
ssh guinevere-vps "cat > ~/.hermes/skills/test-discovery/SKILL.md << 'EOF'
---
name: test-discovery
version: 0.0.1
purpose: Smoke test for custom skill auto-discovery
---
EOF"

# Step 3: Check if Hermes discovers it
ssh guinevere-vps "hermes skills list"
# EXPECTED (if discovery works): "test-discovery" appears in list
# EXPECTED (if discovery fails): "No skills installed."

# Step 4: Clean up
ssh guinevere-vps "rm -rf ~/.hermes/skills/test-discovery"
```

**Prerequisites for smoke test:**
- SSH access to VPS (confirmed working — `guinevere-vps` alias)
- `hermes` binary in PATH on VPS (confirmed — Hermes gateway running)
- Write access to `~/.hermes/` (confirmed — user `guinevere` owns the directory)

### 5.2 Fallback Discovery Paths

If directory auto-discovery **fails**, investigate in order:

1. **Check `hermes skills install --help`** for `--local`, `--path`, or `--file` flags:
   ```bash
   ssh guinevere-vps "hermes skills install --help"
   ```

2. **Check Hermes config for `skills_path`** or `custom_skills_dir`:
   ```bash
   ssh guinevere-vps "grep -i skill ~/.hermes/config.yaml"
   ssh guinevere-vps "hermes --help | grep -i skill"
   ```

3. **Check if `~/.hermes/config.yaml` accepts a `skills:` section:**
   ```bash
   # No current evidence of this; would need experimentation
   ```

4. **Check GitHub issues / Hermes NousResearch docs** for custom skill registration patterns.

5. **Fallback: Publish skills as private packages** to agentskills.io and install via `hermes skills install`.

### 5.3 agentskills.io Hub Package Installation

If custom skills must be installed from the hub, the 5 Phase 5 priority skills would need to be:
1. Written as proper SKILL.md packages
2. Published to agentskills.io (potentially as private packages if the hub supports it)
3. Installed via `hermes skills install <name>`

This is a **significantly heavier workflow** and would add publishing + authentication steps to Phase 5.

---

## 6. Phase 5 Smoke Test Sequence Requirements

### 6.1 Required Smoke Tests

The batch plan defines these verification commands for Step 5.3. Their feasibility depends on discovery working:

| Smoke Test | Command | Feasibility | Blockers |
|---|---|---|---|
| **Discovery** (pre-flight) | `hermes skills list | grep test-discovery` | ✅ (if discovery works) | CI-2 blocker — must test first |
| **Count** | `hermes skills list` → 5 skills | ✅ (if discovery works) | Depends on pre-flight |
| **Doctor** | `hermes skills doctor` → exit 0 | ✅ | Depends on skills installed |
| **Directory existence** | `ls ~/.hermes/skills/` → 5 dirs | ✅ (unrelated to Hermes) | None |
| **File existence** | Loop testing `SKILL.md` per dir | ✅ (pure filesystem check) | None |
| **hub search** | `hermes skills search safety` | ✅ (already functional) | None |

### 6.2 Required Base State

Before running Phase 5 Step 5.3, the VPS must have:

- [ ] SSH access working (✅ confirmed via earlier research reports)
- [ ] `hermes` binary in PATH (✅ — gateway running as systemd service)
- [ ] `~/.hermes/` directory writable (✅ — owned by guinevere user)
- [ ] `~/.hermes/skills/` directory does not pre-exist (✅ — confirmed, but will be created in step)
- [ ] Custom skill discovery **verified** (❌ — CI-2 not yet resolved)

### 6.3 Risks

| Risk | Impact | Likelihood | Mitigation |
|---|---|---|---|
| Directory discovery fails entirely | Phase 5 skills cannot be installed as planned | MEDIUM | Fallback to hub publishing or config-based registration |
| `hermes skills doctor` reports false positives | Verification passes but skills are not active | LOW | Manual content verification per SKILL.md |
| Skill conflict with existing hooks | Safety regression from overlapping hook registrations | LOW | Skills are instruction-only; hooks are in Python plugins |
| SSH key rotation breaks access mid-phase | Cannot execute any VPS commands | LOW | Multiple SSH sessions; test connectivity before batch |

---

## 7. Phase 5 Priority Skills — Current Readiness

### 7.1 Skill Content Readiness

| Skill | SKILL.md Content Defined | Backing Python Module | Hook Integration Specified |
|---|---|---|---|
| `guinevere-hardstop` | ✅ (batch plan §5.3.1) | `yandere_fsm.py`, `safe_mode.py` | ❌ (hook binding not explicit in SKILL.md; implied `pre_prompt`) |
| `guinevere-consent` | ✅ (batch plan §5.3.2) | `GuinevereSafetyPlugin` | ❌ (implied `pre_tool_call` but not named in SKILL.md) |
| `guinevere-yandere` | ✅ (batch plan §5.3.3) | `yandere_fsm.py`, `transition_rules.py` | ❌ (hook not specified) |
| `guinevere-mood` | ✅ (batch plan §5.3.4) | `mood_engine.py`, `streak_tracker.py` | ❌ (hook not specified) |
| `guinevere-rituals` | ✅ (batch plan §5.3.5) | `ritual_scheduler.py`, `rituals/*.py` | ❌ (hook not specified) |

**Finding:** All 5 SKILL.md content skeletons are defined in the batch plan, but none explicitly name which Hermes hook (`pre_prompt`, `post_prompt`, `pre_tool_call`, etc.) triggers their instructions. This was flagged by Auditor 2 (Finding #3) as "NEEDS REVIEW". For Phase 5 execution, the SKILL.md files should include explicit hook binding annotations.

### 7.2 agentskills.io Enabler Packages

| Skill | Enabler Package | Enabler Needed? | Notes |
|---|---|---|---|
| `guinevere-hardstop` | `safety-pack` | Optional | Safety guards are custom — enabler is supplementary |
| `guinevere-consent` | `safety-pack` | Optional | Consent logic is custom — enabler is supplementary |
| `guinevere-yandere` | — (none) | N/A | Uniquely Guinevere-specific |
| `guinevere-mood` | `mood-tracker` | Optional | Mood analysis helpers |
| `guinevere-rituals` | `persona-rituals` | Optional | Ritual templates |

**Finding:** All enabler packages are optional (the batch plan correctly treats them as "complementary enablers, not 1:1 replacements" per `02-skills-state.md` §4). They can be installed after custom skills are confirmed working.

---

## 8. Bundle Readiness (Deferred)

Per `11-SKILLS-SYSTEM.md` §4.1, two bundles logically cover the Phase 5 skills:

| Bundle | Contains | Status |
|---|---|---|
| `guinevere-core` | yandere, mood, rituals (+ future soul-loader, drift-detector) | **DEFERRED** to post-Phase 7 |
| `guinevere-safety` | hardstop, consent (+ future punishment, reward, distress, safe-mode) | **DEFERRED** to post-Phase 7 |

No bundle manifests exist. Individual skills are installed directly in Phase 5.

---

## 9. Skill Catalog vs. Phase 5 Scope

From `11-SKILLS-SYSTEM.md` §5, the full candidate catalog has 28 skills across 4 categories:

| Category | Total Candidates | In Phase 5 | Deferred |
|---|---|---|---|
| Persona | 8 | 3 (yandere, mood, rituals) | 5 (soul-loader, drift-detector, punishment, reward, transition-rules) |
| Safety | 6 | 2 (hardstop, consent) | 4 (distress-detector, safe-mode, forbidden-patterns, y6-prohibition) |
| Domain | 8 | 0 | 8 (all deferred) |
| Tool | 6 | 0 | 6 (all deferred) |
| **Total** | **28** | **5** | **23** |

The `02-skills-state.md` (planning phase) §3 "User's 5 Priorities" listed a partially different set (hardstop, memory-bridge, slash-commands, consent, yandere). The batch plan resolves this discrepancy (see batch-plan-phase-5.md §Step 5.3 "Skill Selection Rationale"): memory-bridge and slash-commands depend on Phase 3/Phases 3+4 which have blocking prerequisites not yet executed. Mood and rituals were added because they are persona-identity core with zero external dependencies.

---

## 10. VPS Access Status

| Requirement | Status | Evidence |
|---|---|---|
| Host | `faiz-prod-01` (100.94.104.22 via Tailscale) | VPS state reports |
| User | `guinevere` | SSH config |
| SSH alias | `guinevere-vps` configured | Multiple research reports |
| SSH key | ✅ Working | Phase 3, P2, P1 reports all used SSH successfully |
| GitHub SSH | ❌ **BROKEN** (`Permission denied (publickey)`) | git-sync/01-vps-git-state.md |
| `hermes` in PATH | ✅ Running as systemd service | `hermes-gateway.service` running |
| `~/.hermes/` | ✅ Exists, writable | Confirmed in VPS git state |
| `~/.hermes/skills/` | ❌ Does not exist | No such directory in untracked files |
| agentskills.io reachable | ✅ `hermes skills search safety` returns results | 11-SKILLS-SYSTEM.md §2.3 |

---

## 11. Blocker Summary

| # | Blocker | Severity | Affected Step | Resolution |
|---|---|---|---|---|
| **B-1 (CI-2)** | Custom skill auto-discovery UNVERIFIED — `~/.hermes/skills/*/SKILL.md` may not be recognized by Hermes | **CRITICAL** | Step 5.3 | Pre-flight smoke test (see §5.1) before any skill creation |
| B-2 | SKILL.md skeletons lack explicit hook binding annotations | MEDIUM | Step 5.3 (content quality) | Add `Hook: <event>` annotation to each SKILL.md before writing |
| B-3 | Cross-document skill identity mismatch resolved (batch plan vs 02-skills-state.md) but evidence/docs should be updated | LOW | Step 5.3 (documentation) | Already resolved in batch plan v1.1; ensure planning doc updated |
| B-4 | `hermes skills doctor` behavior unknown (has never been run) | LOW | Step 5.3 (verification) | Accept first-run output; document for future reference |
| B-5 | VPS cannot push/pull from GitHub (SSH key broken) | MEDIUM | Post-Phase 5 sync | Not blocking Phase 5 execution; blocks git-based rollback via origin |

---

## 12. Recommendations for Phase 5 Execution

### Pre-Step-5.3 (Mandatory)

1. **Run pre-flight smoke test** immediately before any skill creation (see §5.1). This is the single most critical unknown.
2. **Document the smoke test result** in `docs/setup-evidence/phase-5/verification-5-3-preflight.md`.

### If Smoke Test PASSES (directory discovery works)

3. Create `~/.hermes/skills/` with 5 subdirectories and SKILL.md files per batch plan.
4. Add explicit hook binding to each SKILL.md (e.g., `Hook: pre_prompt` for hardstop).
5. Run `hermes skills list` and `hermes skills doctor` for verification.
6. Proceed with Step 5.4 (Plugin Bridge).

### If Smoke Test FAILS (directory discovery doesn't work)

3. Check `hermes skills install --help` for local install flags.
4. Check Hermes config for `skills_path` setting.
5. If no local method exists, skills must either be:
   - Published to agentskills.io (private repo if supported), OR
   - Handled differently (e.g., instructions added to SOUL.md instead)
6. Update the batch plan's Step 5.3 scaffold to use the correct registration method.

### General

7. After skill installation, explicitly test that installed skills are actually loaded in agent context — `hermes skills list` showing them is not proof of runtime loading.
8. Skills are an instruction layer only — all complex stateful logic remains in Python backends. Do not attempt to port Python logic into SKILL.md.

---

## 13. References

| Document | Section | Relevance |
|---|---|---|
| `research-reports/hermes-restructure/11-SKILLS-SYSTEM.md` | Full doc | Skills architecture, CLI commands, SKILL.md format, bundles, candidate catalog |
| `docs/setup-evidence/hermes-migration/phase-5-skills.md` | Step 5.1 | Skill installation procedure (hub-based) |
| `docs/setup-evidence/phase-5/batch-plan-phase-5.md` | Step 5.3 | Priority skills definition, SKILL.md content, pre-flight smoke test, scaffold |
| `docs/setup-evidence/phase-5/auditor-gate-5-skills.md` | Finding #5 (CI-2) | Auditor-flagged custom skill installation issue |
| `research-reports/phase-5-planning/02-skills-state.md` | Full doc | Planning-phase skills analysis (partially superseded by batch plan) |
| `research-reports/phase-3-execution/01-vps-memory-state.md` | Full doc | VPS SSH access, PostgreSQL/Redis state |
| `research-reports/git-sync/01-vps-git-state.md` | Full doc | VPS git state, SSH key status for GitHub |
| `docs/setup-evidence/phase-5/evidence-phase-5.md` | — | Comprehensive Phase 5 evidence (future) |

---

## 14. Footer

| Field | Value |
|---|---|
| **Report ID** | PH5-EXEC-02-SKILLS-STATE |
| **Version** | 1.0 |
| **Date** | 2026-06-05 |
| **Status** | COMPLETE — Read-Only Assessment |
| **Blocking Issue** | B-1 (CI-2): Custom skill auto-discovery unverified |
| **Next Action** | Run pre-flight smoke test on VPS before Phase 5 Step 5.3 |
