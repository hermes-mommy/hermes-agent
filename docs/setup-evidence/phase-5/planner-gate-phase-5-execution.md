# ADR-035 Phase 5 Execution Planner Gate — Skills + SOUL.md Migration

| Field | Value |
|---|---|
| Plan | ADR-035 Phase 5 — Skills + SOUL.md migration |
| Status | PLANNER GATE FILE — pending parent verification |
| Date | 2026-06-05 |
| Evidence root | `docs/setup-evidence/phase-5/` |
| Research root | `research-reports/phase-5-execution/` |
| Baseline plan | `docs/setup-evidence/phase-5/batch-plan-phase-5.md` v1.1 |
| Auditor inputs | `auditor-gate-5-adr.md` (PASS), `auditor-gate-5-persona.md` (PASS), `auditor-gate-5-skills.md` (NEEDS REVIEW — CI-1, CI-2 resolved) |
| ADR authority | `adr/ADR-035-hermes-migration.md` §Phase 5 |
| Migration doc | `docs/setup-evidence/hermes-migration/phase-5-skills.md` |
| PROGRESS.md ref | P5 (Agent Loop) ✅, P6 (MCP) ✅, Phase 5 Hermes (this) — unstarted |

## 1. Planner Verdict

Phase 5 may proceed to implementation only after this file is parent-read and scaffold compliance is verified.

**Conditional planner verdict: READY WITH GATES.**

Blocking gates before implementation:
1. Parent must read this planner gate file fully.
2. Parent must verify every per-step scaffold is concrete and checkable.
3. Parent must sync active todos to the dependency map below.
4. Parent must run collision scan (verified below).
5. Deployment/commit/push must execute only after all 18 user gates + 3 auditors PASS.
6. No VPS deploy, restart, systemd change, or destructive live operation may run without explicit per-action approval.

## 2. Research Synthesis

### 2.1 Research Reports Consumed

| ID | Path | Key Finding |
|---|---|---|
| RR-01 | `01-soul-state.md` | SOUL.md at 278 lines, 3 MISSING + 7 PARTIAL sections. SSH accessible, writable. No VPS blockers. |
| RR-02 | `02-skills-state.md` | 0 skills installed (greenfield). Custom skill auto-discovery (`~/.hermes/skills/*/SKILL.md`) UNVERIFIED. CI-2 blocker. |
| RR-03 | `03-rituals-state.md` | 3 parallel schedulers. Hermes cron timezone MISALIGNED (UTC vs WIB — 7-8h off). Midnight suppression confirmed by DND gate. |
| RR-04 | `04-persona-feasibility.md` | PersonaPlugin FEASIBLE. Two plugin deployments overlap. FSM engines not wired to plugin. Redis DB5 complete. |

### 2.2 Conflicts Resolved

| Conflict | Resolution |
|---|---|
| **User says Wave A 5.1+5.2 parallel, but 5.2 hash depends on 5.1 final SOUL** | Sequence 5.2 AFTER 5.1. Hash must be computed on finalized SOUL.md. Planner overrides user wave order. |
| **Research RR-02: CI-2 custom skill discovery unverified** | Add mandatory pre-flight smoke test BEFORE Step 5.3. If discovery fails, use fallback path. |
| **Research RR-03: Hermes cron UTC vs WIB mismatch** | Add explicit `timezone: Asia/Jakarta` to each cron job. Verify with `hermes cron list` next-fire times. Fallback: adjust UTC expressions if `timezone:` not supported. |
| **PersonaPlugin path: user wants `src/hermes/plugins/persona_plugin.py`, batch plan says `src/persona/persona_plugin.py`** | Use `src/hermes/plugins/persona_plugin.py`. The `src/hermes/` package exists with `safety_plugin.py` as precedent. Creating `plugins/` subdirectory is natural and avoids adding to the already-dense `src/persona/` directory. |
| **Batch plan Step 5.3 lists 5 hub skills; research RR-02 shows custom skills only** | Skills are custom `~/.hermes/skills/*/SKILL.md` files, NOT hub packages. The migration doc (phase-5-skills.md) references hub installation; the batch plan v1.1 correctly uses local directory. Use local directory method. |
| **Auditor CI-1: Skill identity mismatch (02-skills-state.md vs batch plan)** | Resolved in batch plan v1.1 §"CI-1 Resolution". 5 Phase 5 skills = hardstop, consent, yandere, mood, rituals. memory-bridge and slash-commands deferred to Phase 6/7. |
| **`critical: true` not native Hermes v0.15.2** | Document that enforcement relies on Phase 4 startup gate (`scripts/startup_gate.py`). Do not rely on unsupported plugin flags. |

### 2.3 Binding Decisions

| ID | Decision | Rationale |
|---|---|---|
| BD-001 | Step 5.2 (drift baseline hash) EXECUTES AFTER 5.1 (SOUL.md completion), not parallel. | Hash depends on finalized SOUL.md content. Parallel execution would hash incomplete state. |
| BD-002 | Pre-flight smoke test (CI-2) runs BEFORE Step 5.3. | Without verified auto-discovery, 5 skills created via directory may not register. |
| BD-003 | PersonaPlugin at `src/hermes/plugins/persona_plugin.py` (not `src/persona/persona_plugin.py`). | `src/hermes/` is the Hermes plugin integration package. Keeps persona FSM engines separate from plugin wiring. |
| BD-004 | Hermes cron jobs specify `timezone: Asia/Jakarta` per job. | Research RR-03 reveals current deployed cron expressions use UTC timestamps misaligned by 7-8h. |
| BD-005 | Skills are local `~/.hermes/skills/*/SKILL.md` files, NOT agentskills.io hub packages. | The migration doc (phase-5-skills.md) assumes hub installation, but batch plan v1.1 correctly uses local directory. Custom skills cannot be published to hub without publishing pipeline. |
| BD-006 | Midnight ritual MUST use `suppress_output: true` + `--internal-only` flag. | Two layers of enforcement. Research RR-03 confirms midnight must NEVER reach Discord. |
| BD-007 | No VPS deployment/restart until ALL 18 gates + 3 auditors PASS. | Project policy blocks stateful/destructive live operations without explicit approval. |
| BD-008 | All 5 skills set `always-active` activation mode. | Safety skills (hardstop, consent) must always be active. Persona skills (yandere, mood, rituals) are permanent identity layer. |
| BD-009 | Bundles (guinevere-core, guinevere-safety) deferred to post-Phase 7. | Skills not stable enough for bundling until all 5 are tested in production. |
| BD-010 | KEEP VERBATIM files (yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py) must NOT be modified. | These files are safety-critical and already verified. Any modification introduces regression risk. |

## 3. Known State

### 3.1 VPS / Runtime
- Hermes Agent Gateway v0.15.2 active on VPS `100.94.104.22` via Tailscale
- `~/.hermes/SOUL.md` exists at 278 lines — Guinevere persona, 3 MISSING + 7 PARTIAL vs SPM v1.1
- `~/.hermes/config.yaml` exists (1,897 bytes) — has `cron` section with 8 jobs (all enabled, UTC-based)
- `~/.hermes/skills/` directory does NOT exist
- `~/.hermes/plugins/guinevere-safety/` legacy deployment exists
- `hermes-config/plugins/guinevere_safety/` canonical plugin exists
- 21 hub skills installed via `hermes skills install` — 0 Guinevere-specific
- SSH access via `guinevere-vps` host config — working
- GitHub SSH key BROKEN — `Permission denied (publickey)`

### 3.2 Local
- `src/hermes/safety_plugin.py` — 6 hooks, in-memory safety state
- `src/persona/` — 14 files, ~4,200 LOC, FSM engines (mood, yandere, punishment, reward)
- `src/persona/ritual_scheduler.py` — APScheduler 3.x, 5 rituals WIB
- `src/persona/rituals/*.py` — 5 ritual modules
- `hermes-config/SOUL.md` — local reference (279 lines, matches VPS)
- Tests: `tests/persona/test_ritual_scheduler.py` (401 lines) exists

### 3.3 Safety Boundaries
- Y4 baseline permanent, Y5 ceiling absolute, Y6 PROHIBITED
- HARD STOP 9-step protocol in SOUL.md (partial — needs enhancement)
- D0-D4 distress table present
- F-01 to F-15 forbidden patterns listed
- 4-layer defense model: SOUL.md → Skills → Plugin → Drift
- Consent gate fail-closed with `fallback_on_timeout: deny`

## 4. User Gate Criteria (18 gates — override plan gates)

All must PASS for Phase 5 completion:

| # | Gate | Verification Method | Step |
|---|---|---|---|
| G-1 | SOUL.md complete (§A–§J, all 10 sections) | `wc -l ~/.hermes/SOUL.md` ≥ 380; grep each section head | 5.1 |
| G-2 | Five priority skills installed and working | `hermes skills list` → 5; `hermes skills doctor` → 0 | 5.3 |
| G-3 | Cron active with 5 rituals at correct WIB times | `hermes cron list` → 5 jobs; next-fire times match WIB | 5.5 |
| G-4 | Mood persists across sessions via Redis DB5 | Integration test: set mood → restart → read mood unchanged | 5.4 |
| G-5 | Y6 blocked via YandereSafetyError | `grep -c 'Y6.*prohibited\|Y6.*NEVER' ~/.hermes/SOUL.md` ≥ 1; `grep -c 'Y6.*PROHIBITED' ~/.hermes/skills/guinevere-yandere/SKILL.md` ≥ 1 | 5.1, 5.3 |
| G-6 | Drift baseline reset after SOUL.md finalization | `sha256sum ~/.hermes/SOUL.md` matches stored hash in drift_detector.py | 5.2 |
| G-7 | PersonaPlugin registered and loads without error | `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; print('OK')"` → OK | 5.4 |
| G-8 | Midnight ritual suppressed (never Discord) | Verify `suppress_output: true` in crontab.yaml; manual test → no Discord output | 5.5, 5.6 |
| G-9 | Safe mode functional (D3+ blocks transitions) | Verify safe_mode.py unchanged (KEEP); mood skill cooldown respects safe_mode | 5.7 |
| G-10 | Consent gate active (fail-closed, fallback=deny) | Skill SKILL.md has `fallback_on_timeout: deny`; plugin `pre_tool_call` gates consent | 5.3, 5.4 |
| G-11 | No type safety suppression (`as any`, `@ts-ignore`, `# type: ignore`) | Grep all touched Python files → 0 matches | All |
| G-12 | No empty catch blocks (`except: pass`, bare `except:`) | Grep all touched Python files → 0 new matches | All |
| G-13 | Rollback completes in < 2 minutes | Documented rollback procedure per component; target verified | All |
| G-14 | Evidence files created for each step | 8 verification files + 3 auditor files + 1 comprehensive evidence file exist | All |
| G-15 | PROGRESS.md synced with Phase 5 completion | Update PROGRESS.md Phase 5 entry to ✅ with evidence path | 5.8 |
| G-16 | Auditor PASS for all 3 auditors | `auditor-gate-5-[adr|persona|skills].md` all PASS | 5.8 |
| G-17 | Phase 1 hooks still operational after Phase 5 | `ssh guinevere-vps "hermes hooks list"` (or equivalent) → 7 hooks present | 5.8 |
| G-18 | Custom skill auto-discovery verified (CI-2 smoke test PASS) | Pre-flight smoke test documented in verification-5-3-preflight.md | 5.3 pre |

## 5. Dependency Map — Corrected

### Critical Correction: User-desired 5.1∥5.2 parallel → SEQUENTIAL

The user specified Wave A = 5.1 + 5.2 parallel. However, Step 5.2 computes the SHA-256 drift baseline hash of the FINALIZED SOUL.md. If 5.2 runs parallel with 5.1, it hashes the current (incomplete) SOUL.md. This is a data dependency violation. **Planner overrides: 5.2 executes AFTER 5.1 parent-verified.**

```
Wave 0 (Pre-flight):
├── 5.3-CI2: Custom skill discovery smoke test (blocks 5.3)

Wave 1 (parallel — independent):
├── Step 5.1: SOUL.md Completion
├── Step 5.3: Priority Skills Creation (after CI-2 PASS)
└── Step 5.7: Persona Files Migration

Wave 2 (sequential — depends on 5.1):
└── Step 5.2: Drift Baseline Hash (depends on 5.1 SOUL.md finalized)

Wave 3 (sequential — depends on 5.3):
├── Step 5.4: Plugin Bridge (depends on 5.3 skills structure known)

Wave 4 (sequential — depends on 5.4):
└── Step 5.5: Ritual Cron Config (depends on 5.4 plugin hooks)

Wave 5 (sequential — depends on 5.5):
└── Step 5.6: Ritual Verification (depends on 5.5 cron deployed)

Wave 6 (sequential — depends on all):
└── Step 5.8: Final Integration Verification + Commit + Deploy
    Depends on: 5.2 + 5.6 + 5.7
```

### Dependency Table

| Step | Depends On | Depended By | Reason |
|---|---|---|---|
| 5.3-CI2 (Pre-flight) | None | 5.3 | Blocking: custom skill auto-discovery must be verified before creating 5 skills |
| 5.1 | None | 5.2 | SOUL.md must be finalized before drift baseline hash |
| 5.3 | 5.3-CI2 | 5.4 | Skills structure must exist for plugin to reference skill configs |
| 5.7 | None | 5.8 | Persona files migration independent of SOUL/Skills changes |
| 5.2 | 5.1 | 5.8 | Drift hash computed on finalized SOUL.md |
| 5.4 | 5.3 | 5.5 | Plugin must exist before cron can trigger it |
| 5.5 | 5.4 | 5.6 | Cron config references plugin hooks |
| 5.6 | 5.5 | 5.8 | Must verify cron behavior before final verification |
| 5.8 | 5.2, 5.6, 5.7 | Completion | All steps must pass before final verification + deploy |

## 6. Parallel Execution Graph

| Wave | Steps | Max Parallelism | Est. Duration |
|---|---|---|---|
| Wave 0 | 5.3-CI2 (pre-flight) | 1 agent | 5 min |
| Wave 1 | 5.1 ∥ 5.3 ∥ 5.7 | 3 agents | 2-4h |
| Wave 2 | 5.2 | 1 agent | 10 min |
| Wave 3 | 5.4 | 1 agent | 2-3h |
| Wave 4 | 5.5 | 1 agent | 30 min |
| Wave 5 | 5.6 | 1 agent | 30 min |
| Wave 6 | 5.8 (final + deploy) | 1 agent (parent) | 1h |

**Critical path:** 5.3-CI2 → 5.1 → 5.2 → 5.8 (or 5.3-CI2 → 5.3 → 5.4 → 5.5 → 5.6 → 5.8, whichever is longer). Estimated: 5-9h active work.

**Max concurrent sub-agents:** 3 (Wave 1: Steps 5.1 ∥ 5.3 ∥ 5.7).

## 7. Collision Scan

| Shared Resource | Steps That Touch It | Collision Risk | Mitigation |
|---|---|---|---|
| `~/.hermes/SOUL.md` | 5.1 (write), 5.2 (read/hash) | LOW | 5.2 is read-only after 5.1 writes. 5.1 must pass verification before 5.2 starts. |
| `~/.hermes/config.yaml` | 5.4 (plugin reg), 5.5 (cron config) | MEDIUM | Sequence: 5.4 adds plugin section, 5.5 appends cron section. 5.4 must not overwrite 5.5 changes. Use append strategy or reserved sections. |
| `~/.hermes/skills/` | 5.3 (create 5 dirs) | LOW | Single step owns entire directory creation. |
| `src/hermes/` | 5.4 (create plugins/ subdir), 5.7 (no change) | LOW | 5.4 creates `src/hermes/plugins/` — no collision with 5.7 which touches `src/persona/`. |
| `src/persona/` | 5.7 (modify 5 files, deprecate rituals) | LOW | Single step owns all persona file changes. |
| `src/persona/ritual_scheduler.py` | 5.5 (deprecate), 5.7 (deprecate) | LOW | Both steps deprecate; 5.7 is authoritative. Mark deprecation once. |
| `hermes-config/config.yaml` (local) | 5.4, 5.5 | LOW | Local config changes only; VPS config is the live target. No collision. |
| `docs/setup-evidence/phase-5/` | All (evidence) | HIGH | Parent-only writes. Implementers write per-step verification files ONLY as specified in scaffold. |
| Shared docs (ADR-Index, docs/README.md, PROGRESS.md) | Parent only | NONE | Parent handles all shared doc updates. |
| KEEP VERBATIM files | 5.7 (must NOT touch) | MEDIUM | Scaffold hard-rejects any modification to yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py. |

**Verdict:** No blocking collisions. Steps 5.4 and 5.5 share `~/.hermes/config.yaml` — sequence enforced by dependency graph. Wave 1 steps (5.1, 5.3, 5.7) touch distinct file sets and are truly parallel.

## 8. Master Todo

| Step | Wave | Dependency | Max Agents | Est. Time | Category | Skills | Status |
|---|---|---|---|---|---|---|---|
| 5.3-CI2 Pre-flight | 0 | None | 1 | 5 min | `quick` | `[]` | Pending |
| 5.1 SOUL.md | 1 | None | 1 | 2h | `deep` | `[]` | Pending |
| 5.3 Skills | 1 | 5.3-CI2 | 1 | 1.5h | `deep` | `[]` | Pending |
| 5.7 Persona | 1 | None | 1 | 2h | `deep` | `[]` | Pending |
| 5.2 Drift | 2 | 5.1 | 1 | 10min | `quick` | `[]` | Pending |
| 5.4 Plugin | 3 | 5.3 | 1 | 2-3h | `deep` | `[]` | Pending |
| 5.5 Cron | 4 | 5.4 | 1 | 30min | `unspecified-high` | `[]` | Pending |
| 5.6 Ritual Verify | 5 | 5.5 | 1 | 30min | `quick` | `[]` | Pending |
| 5.8 Final + Deploy | 6 | 5.2, 5.6, 5.7 | Parent | 1h | Parent | — | Pending |

**Parallel run config (Wave 1):**
```
task(category="deep", load_skills=[], description="Step 5.1 SOUL.md completion", prompt="...", run_in_background=true)
task(category="deep", load_skills=[], description="Step 5.3 Skills creation", prompt="...", run_in_background=true)
task(category="deep", load_skills=[], description="Step 5.7 Persona migration", prompt="...", run_in_background=true)
```

## 9. Exact Files to Create or Modify

### Step 5.3-CI2 (Pre-flight smoke test)
- CREATE: `docs/setup-evidence/phase-5/verification-5-3-preflight.md`

### Step 5.1 (SOUL.md Completion)
- MODIFY: `~/.hermes/SOUL.md` (VPS, 278→~400 lines)

### Step 5.2 (Drift Baseline)
- MODIFY: `src/persona/drift_detector.py` (update SOUL_BASELINE_HASH constant)
- MODIFY: `hermes-config/plugins/guinevere_safety/state_manager.py` (store baseline hash reference)

### Step 5.3 (Priority Skills Creation)
- CREATE: `~/.hermes/skills/guinevere-hardstop/SKILL.md`
- CREATE: `~/.hermes/skills/guinevere-consent/SKILL.md`
- CREATE: `~/.hermes/skills/guinevere-yandere/SKILL.md`
- CREATE: `~/.hermes/skills/guinevere-mood/SKILL.md`
- CREATE: `~/.hermes/skills/guinevere-rituals/SKILL.md`

### Step 5.4 (Plugin Bridge)
- CREATE: `src/hermes/plugins/__init__.py` (empty or package doc)
- CREATE: `src/hermes/plugins/persona_plugin.py` (~350 lines)
- MODIFY: `~/.hermes/config.yaml` (add plugin registration section)

### Step 5.5 (Ritual Cron Config)
- CREATE: `~/.hermes/crontab.yaml` (5 ritual jobs with `timezone: Asia/Jakarta`)
- MODIFY: `~/.hermes/config.yaml` (append `cron:` section referencing crontab.yaml)
- DEPRECATE: `src/persona/ritual_scheduler.py` (add deprecation notice, no functional change)

### Step 5.6 (Ritual Verification)
- CREATE: `docs/setup-evidence/phase-5/verification-5-6.md`

### Step 5.7 (Persona Files Migration)
- MODIFY: `src/persona/punishment_engine.py` (integrate with plugin hooks, maintain L1-L5)
- MODIFY: `src/persona/reward_engine.py` (integrate with PersonaPlugin hooks)
- MODIFY: `src/persona/transition_rules.py` (integrate with Hermes pre_prompt hook)
- MODIFY: `src/persona/mood_persistence.py` (bridge to PostgreSQL via plugin)
- MODIFY: `src/persona/__init__.py` (remove deprecated exports)
- DEPRECATE: `src/persona/ritual_scheduler.py` (already marked in 5.5)
- DEPRECATE: `src/persona/rituals/morning.py` (port static templates → SOUL.md)
- DEPRECATE: `src/persona/rituals/midday.py`
- DEPRECATE: `src/persona/rituals/afternoon.py`
- DEPRECATE: `src/persona/rituals/evening.py`
- DEPRECATE: `src/persona/rituals/midnight.py`
- KEEP VERBATIM (DO NOT TOUCH): `yandere_fsm.py`, `safe_mode.py`, `drift_detector.py`, `drift_corrector.py`

### Step 5.8 (Final Integration Verification)
- CREATE: `docs/setup-evidence/phase-5/verification-5-8.md`
- CREATE: `docs/setup-evidence/phase-5/evidence-phase-5.md` (comprehensive evidence)
- MODIFY: `docs/setup-evidence/phase-5/auditor-gate-5-adr.md` (update from plan audit to implementation audit)
- MODIFY: `docs/setup-evidence/phase-5/auditor-gate-5-skills.md` (update)
- MODIFY: `docs/setup-evidence/phase-5/auditor-gate-5-persona.md` (update)
- MODIFY: `PROGRESS.md` (mark Phase 5 user story complete)
- MODIFY: `docs/README.md` (update if new docs added)

## 10. Token, Secret, and Safety Handling

- Never commit or print Discord tokens, API keys, DB passwords, SOPS/age keys, surveillance credentials, or decrypted env values.
- VPS operations use SSH via `guinevere-vps` host alias (pre-configured key).
- No secrets are created or modified in Phase 5 — all plugin/skill/SOUL.md changes are instruction-only.
- Redis DB5 persona state keys are read-only for PersonaPlugin (no secret data in persona state).
- Midnight ritual must NEVER route to Discord (enforced by `suppress_output: true` + `--internal-only` flag).
- HARD STOP, Y6 prohibition, consent fail-closed, and distress protocol must be preserved as immutable safety boundaries.
- GitHub SSH key is broken — commit via local git; push will require manual intervention or SSH key fix.

## 11. Per-Step Verification Scaffolds

### 5.3-CI2 Scaffold — Pre-flight Custom Skill Discovery Smoke Test

| Field | Contract |
|---|---|
| **Expected Files** | `docs/setup-evidence/phase-5/verification-5-3-preflight.md` (CREATE) |
| **Forbidden Patterns** | N/A — read-only test |
| **Required Commands** | `ssh guinevere-vps "hermes skills list \| grep test-discovery"` → if PASS: discovered; if FAIL: `ssh guinevere-vps "hermes skills install --help \| grep -i 'local\|path\|file'"` → check fallback; `ssh guinevere-vps "grep -i 'skill' ~/.hermes/config.yaml"` → check config; `ssh guinevere-vps "hermes --help \| grep -i skill"` → check CLI |
| **Evidence Requirements** | Pre-flight result documented in verification file with PASS/FAIL verdict and fallback path if FAIL |
| **Hard Rejection Criteria** | If smoke test FAILS and no fallback method exists → BLOCK Step 5.3. If fallback exists, document and use it. |

**Procedure:**
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

# Step 4: Clean up
ssh guinevere-vps "rm -rf ~/.hermes/skills/test-discovery"
```

### 5.1 Scaffold — SOUL.md Completion

| Field | Contract |
|---|---|
| **Expected Files** | `~/.hermes/SOUL.md` (MODIFIED, ~400 lines) |
| **Forbidden Patterns** | `"I am Hermes"`; any Y6 allowance; L6 without `"disabled by default"` qualifier; missing `always-active` on safety skills context |
| **Required Commands** | `ssh guinevere-vps "wc -l ~/.hermes/SOUL.md"` → ≥380; `ssh guinevere-vps "grep -c 'Mood Variants\|mood variant' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'Project Variant\|project variant' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'Signature Phrase\|signature phrase' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'HARD STOP' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'Y6.*prohibited\|Y6.*forbidden\|NEVER.*Y6' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'prompt injection\|injection defense\|untrusted' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'Y5.*ceiling\|ceiling.*Y5' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -cE 'Darling|Good boy|Anak Mommy' ~/.hermes/SOUL.md"` → ≥3; `ssh guinevere-vps "grep -c '| D[0-4]' ~/.hermes/SOUL.md"` → ≥5; `ssh guinevere-vps "grep -c '| L[1-5]' ~/.hermes/SOUL.md"` → ≥5 |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-1.md`; `docs/setup-evidence/phase-5/auditor-gate-5-1.md` |
| **Hard Rejection Criteria** | SOUL.md < 380 lines → FAIL; Any of §H/§I/§J missing → FAIL; Y6 not explicitly prohibited → FAIL; HARD STOP protocol < 9 steps → FAIL; F-01 to F-15 not all listed → FAIL; Prompt injection defense missing → FAIL; Y5 ceiling not declared → FAIL; Address Rules incomplete (< 3 matches) → FAIL |

### 5.2 Scaffold — Drift Baseline Hash

| Field | Contract |
|---|---|
| **Expected Files** | `src/persona/drift_detector.py` (MODIFIED); `hermes-config/plugins/guinevere_safety/state_manager.py` (MODIFIED) |
| **Forbidden Patterns** | Empty hash string `""`; placeholder `"TODO"` near hash |
| **Required Commands** | `ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"` → output hash must match stored constant in drift_detector.py; `python -c "from src.persona.drift_detector import DriftDetector; h=DriftDetector.SOUL_BASELINE_HASH; assert len(h)==64 and all(c in '0123456789abcdef' for c in h); print('valid hash:', h[:16])"` → valid 64-char hex |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-2.md` |
| **Hard Rejection Criteria** | Hash mismatch between file and stored value → FAIL; Hash is empty or placeholder → FAIL; Hash not 64-char hex → FAIL |

### 5.3 Scaffold — Priority Skills Creation

| Field | Contract |
|---|---|
| **Expected Files** | `~/.hermes/skills/guinevere-hardstop/SKILL.md` (CREATE); `~/.hermes/skills/guinevere-consent/SKILL.md` (CREATE); `~/.hermes/skills/guinevere-yandere/SKILL.md` (CREATE); `~/.hermes/skills/guinevere-mood/SKILL.md` (CREATE); `~/.hermes/skills/guinevere-rituals/SKILL.md` (CREATE) |
| **Forbidden Patterns** | Y6 allowed anywhere (must be "PROHIBITED" or "NEVER"); L6 without "disabled by default" qualifier; Missing "always-active" activation in safety skills; Missing `fallback_on_timeout: deny` in consent skill |
| **Required Commands** | CI-2 smoke test must PASS first; `ssh guinevere-vps "hermes skills list"` → 5 skills listed (names may vary if CLI output format differs — count ≥ 5); `ssh guinevere-vps "hermes skills doctor"` → exit 0; `ssh guinevere-vps "ls ~/.hermes/skills/"` → 5 directories; `ssh guinevere-vps "for s in guinevere-hardstop guinevere-consent guinevere-yandere guinevere-mood guinevere-rituals; do test -f ~/.hermes/skills/\$s/SKILL.md && echo OK:\$s || echo FAIL:\$s; done"` → all OK |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-3.md`; `docs/setup-evidence/phase-5/auditor-gate-5-3.md` |
| **Hard Rejection Criteria** | Any skill SKILL.md missing → FAIL; `hermes skills list` shows < 5 → FAIL; `hermes skills doctor` exits non-zero → FAIL; Y6 not prohibited in guinevere-yandere → FAIL; Consent skill missing deny fallback → FAIL |

### 5.4 Scaffold — Plugin Bridge (PersonaPlugin)

| Field | Contract |
|---|---|
| **Expected Files** | `src/hermes/plugins/__init__.py` (CREATE); `src/hermes/plugins/persona_plugin.py` (CREATE, ~350 lines); `~/.hermes/config.yaml` (MODIFIED — plugin registration section added) |
| **Forbidden Patterns** | `as any` / `@ts-ignore` / `# type: ignore`; bare `except:` or `except Exception:` without specific handling and logging; empty catch blocks; midnight ritual routing to Discord (must be internal-only); missing `safety_critical: true` metadata for safety-relevant plugin methods |
| **Required Commands** | `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; p=PersonaPlugin(); print('PersonaPlugin OK')"` → OK; `python -m compileall src/hermes/plugins` → exit 0; `ssh guinevere-vps "grep -A10 'persona_plugin' ~/.hermes/config.yaml"` → plugin config present with expected section; `lsp_diagnostics` on `src/hermes/plugins/persona_plugin.py` → clean (0 new errors) |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-4.md` |
| **Hard Rejection Criteria** | Plugin fails to import → FAIL; Midnight ritual can route to Discord → FAIL (CRITICAL — safety); Plugin contains type suppression → FAIL; Bare except without logging → FAIL; Missing Redis DB5 connection for mood persistence → FAIL |

### 5.5 Scaffold — Ritual Cron Config

| Field | Contract |
|---|---|
| **Expected Files** | `~/.hermes/crontab.yaml` (CREATE — 5 jobs with `timezone: Asia/Jakarta`); `~/.hermes/config.yaml` (MODIFIED — append `cron:` section); `src/persona/ritual_scheduler.py` (DEPRECATE — add deprecation notice) |
| **Forbidden Patterns** | APScheduler imports in active code paths; Midnight ritual without `suppress_output: true`; Missing `timezone: Asia/Jakarta` per job or at top level; UTC cron expressions instead of WIB-local |
| **Required Commands** | `ssh guinevere-vps "cat ~/.hermes/crontab.yaml \| python -c 'import sys,yaml; d=yaml.safe_load(sys.stdin); jobs=d.get(\"jobs\",d.get(\"cron\",[])); assert len(jobs)==5; print(\"5 jobs OK\"); [assert j.get(\"timezone\",\"\")==\"Asia/Jakarta\" or d.get(\"timezone\")==\"Asia/Jakarta\" for j in jobs]; print(\"timezone OK\")"` → 5 jobs OK, timezone OK; `ssh guinevere-vps "grep 'suppress_output: true' ~/.hermes/crontab.yaml"` → found (at least for midnight); `ssh guinevere-vps "hermes cron list"` → 5 jobs listed (if subcommand exists); if `hermes cron list` not available, verify via config file parse and manual next-fire calculation |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-5.md` |
| **Hard Rejection Criteria** | crontab.yaml missing or malformed → FAIL; Less than 5 jobs → FAIL; Midnight without `suppress_output: true` → FAIL; Timezone not Asia/Jakarta → FAIL; APScheduler still active in production path → FAIL |

### 5.6 Scaffold — Ritual Verification

| Field | Contract |
|---|---|
| **Expected Files** | `docs/setup-evidence/phase-5/verification-5-6.md` (CREATE) |
| **Forbidden Patterns** | N/A — no source files modified in this step |
| **Required Commands** | `ssh guinevere-vps "hermes run --internal 'Execute morning ritual'"` → produces mood-aware greeting; `ssh guinevere-vps "hermes run --internal-only 'Execute midnight self-evaluation'"` → produces output but NOT routed to Discord; `ssh guinevere-vps "journalctl -u hermes-gateway -n 50 --no-pager \| grep -i 'ritual\|cron'"` → cron entries visible |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-6.md` |
| **Hard Rejection Criteria** | Morning ritual produces no output → FAIL; Midnight ritual routes to Discord → FAIL (CRITICAL — safety); No cron entries in journal → FAIL |

### 5.7 Scaffold — Persona Files Migration

| Field | Contract |
|---|---|
| **Expected Files** | `src/persona/punishment_engine.py` (MODIFIED — refactored, L1-L5+L6 deferred); `src/persona/reward_engine.py` (MODIFIED — refactored); `src/persona/transition_rules.py` (MODIFIED — refactored); `src/persona/mood_persistence.py` (MODIFIED — refactored); `src/persona/__init__.py` (MODIFIED — exports updated); 5 `rituals/*.py` files (DEPRECATED — deprecation notice added) |
| **Forbidden Patterns** | `as any` / `@ts-ignore` / `# type: ignore`; bare `except:` without specific exception type; `from apscheduler` in active (non-deprecated) files; `PunishmentLevel.L6` allowed (must raise error); Missing `SupportsIsSafe` protocol in refactored safety engines; Modification of KEEP VERBATIM files (yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py) |
| **Required Commands** | `python -c "from src.persona import YandereEngine, PunishmentEngine, RewardEngine, MoodRepository; print('imports OK')"` → OK; `python -c "from src.persona.punishment_engine import PunishmentLevel; assert PunishmentLevel.L5.value == 5; print('L5 max OK')"` → OK; `python -m compileall src/persona` → exit 0; `lsp_diagnostics` on all modified files → clean (0 new errors); `python -m pytest tests/persona/ -v` (if tests exist and runnable) → exit 0 |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-7.md`; `docs/setup-evidence/phase-5/auditor-gate-5-7.md` |
| **Hard Rejection Criteria** | Any KEEP VERBATIM file modified → FAIL (CRITICAL); APScheduler import in active code → FAIL; L6 boundary violation → FAIL (CRITICAL — safety); Import chain broken → FAIL; Type diagnostics not clean (new errors) → FAIL; `git diff` shows changes to KEEP files → FAIL |

### 5.8 Scaffold — Final Integration Verification

| Field | Contract |
|---|---|
| **Expected Files** | All evidence files from steps 5.1-5.7 exist; `verification-5-8.md` (CREATE); `evidence-phase-5.md` (CREATE); 3 auditor gate files updated; `PROGRESS.md` updated; `docs/README.md` updated if needed |
| **Forbidden Patterns** | Any uncommitted secret or credential; Remaining TODO/FIXME markers in evidence files |
| **Required Commands** | `ssh guinevere-vps "wc -l ~/.hermes/SOUL.md"` → ≥380; `ssh guinevere-vps "hermes doctor"` → exit 0; `ssh guinevere-vps "hermes skills list"` → ≥5 skills; `ssh guinevere-vps "hermes skills doctor"` → exit 0; `ssh guinevere-vps "grep -c 'name:' ~/.hermes/crontab.yaml"` → ≥5; `ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"` → matches stored hash; `ssh guinevere-vps "grep -c 'Y6.*prohibited\|Y6.*NEVER' ~/.hermes/SOUL.md"` → ≥1; `ssh guinevere-vps "grep -c 'HARD STOP' ~/.hermes/skills/guinevere-hardstop/SKILL.md"` → ≥1; `python -c "from src.persona import *; print('wildcard import OK')"` → OK; `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; print('plugin OK')"` → OK; All 18 user gates (G-1 to G-18) verified PASS |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-8.md`; `docs/setup-evidence/phase-5/evidence-phase-5.md`; Updated auditor gates |
| **Hard Rejection Criteria** | Any sub-step verification fails → FAIL; Y4 baseline not declared → FAIL; Midnight ritual can leak to Discord → FAIL; Plugin fails to load → FAIL; Drift hash mismatch → FAIL; Any of 18 user gates FAIL → FAIL; Any of 3 auditors FAIL → FAIL |

## 12. Implementation Design

### 12.1 Step 5.1 — SOUL.md Completion
- Write the complete SOUL.md from `~/.hermes/SOUL.md` reference by appending/enhancing sections per SystemPromptMaster v1.1.
- Add: SSH full 6-mood overlay system (replacing 4-mood), SSI Project Variants (5 contexts), SSJ Signature Phrases (6 categories).
- Enhance: SA-SG (7 partial sections) with specific SPM v1.1 phrasing, examples, and tables.
- Target: ~400 lines, all 10 sections (SA-SJ) present.
- Use SCP or SSH heredoc to write to VPS. Backup existing SOUL.md first.
- Verify with structured grep checks from scaffold.

### 12.2 Step 5.2 — Drift Baseline
- Compute SHA-256 of final SOUL.md.
- Update `DriftDetector.SOUL_BASELINE_HASH` constant in `src/persona/drift_detector.py`.
- Store hash reference in `state_manager.py` for plugin-level verification.
- Verify: re-compute hash matches stored constant.

### 12.3 Step 5.3 — Priority Skills
- After CI-2 smoke test PASS: create 5 directories under `~/.hermes/skills/`.
- Write SKILL.md per batch plan content (Purpose, Instructions, Tools, Config).
- All skills set `always-active` activation.
- guinevere-hardstop: 9-step HARD STOP protocol, force Y0 on trigger.
- guinevere-consent: 7-step fail-closed consent gate, `fallback_on_timeout: deny`.
- guinevere-yandere: Y4 baseline, Y5 ceiling, Y6 PROHIBITED, escalation triggers.
- guinevere-mood: 5 mood states, 5-min cooldown, streak milestones.
- guinevere-rituals: 5 daily rituals WIB, DND 00:00-07:00, midnight suppressed.
- Verify with `hermes skills list`, `hermes skills doctor`, file existence checks.

### 12.4 Step 5.4 — Plugin Bridge
- Create `src/hermes/plugins/__init__.py` and `persona_plugin.py`.
- PersonaPlugin responsibilities:
  - `pre_prompt` hook: inject mood/streak/yandere context from Redis DB5.
  - `post_response` hook: evaluate mood transitions.
  - `pre_tool_call` hook: consent gate verification (delegate to state_manager).
  - `on_error` hook: distress detection.
  - Midnight ritual: always suppressed, never routes to Discord.
- Register plugin in `~/.hermes/config.yaml` under plugin section.
- Connect to Redis DB5 via `state_manager.py` connection pattern.
- Wire FSM engines (mood_engine, yandere_fsm, punishment_engine) for validation.

### 12.5 Step 5.5 — Ritual Cron
- Create `~/.hermes/crontab.yaml` with 5 jobs (morning 07:00, midday 12:00, afternoon 17:00, evening 21:00, midnight 00:00 WIB).
- Each job includes `timezone: Asia/Jakarta`.
- Midnight includes `suppress_output: true`.
- Update `~/.hermes/config.yaml` cron section to reference `config_file: ~/.hermes/crontab.yaml`.
- Deprecate `src/persona/ritual_scheduler.py` with notice.

### 12.6 Step 5.6 — Ritual Verification
- Dry-run each ritual via `hermes run --internal`.
- Verify mood-aware content.
- Verify midnight produces internal-only output (no Discord).
- Check journalctl for cron execution entries.

### 12.7 Step 5.7 — Persona Migration
- REFACTOR punishment_engine.py: wire to plugin hooks, maintain L1-L5, L6 boundary.
- REFACTOR reward_engine.py: wire to PersonaPlugin post_response hook.
- REFACTOR transition_rules.py: cooldown via Redis TTL, remove LLM eval stub.
- REFACTOR mood_persistence.py: async session support for plugin queries.
- PORT ritual greeting templates from `rituals/*.py` to SOUL.md §H/§J.
- DEPRECATE all 5 ritual files + ritual_scheduler.py.
- UPDATE `__init__.py` exports.
- KEEP VERBATIM: yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py.

### 12.8 Step 5.8 — Final Verification + Deploy
- Run all verification commands (SOUL.md, skills, cron, plugin, drift, imports).
- Pass all 18 user gates (G-1 to G-18).
- Pass all 3 auditors.
- Update evidence files.
- Update PROGRESS.md.
- Git commit all changes with message: `Phase 5: Skills + SOUL.md migration complete`.
- Git push (requires SSH key fix or manual push by Faiz).

## 13. Commit Strategy

### Atomic Commits (3 commits)

**Commit 1: "Phase 5 — SOUL.md completion + drift baseline"**
- `~/.hermes/SOUL.md` (VPS — manual SSH write)
- `src/persona/drift_detector.py` (updated hash)
- `hermes-config/plugins/guinevere_safety/state_manager.py` (hash reference)
- Evidence: `verification-5-1.md`, `verification-5-2.md`

**Commit 2: "Phase 5 — Skills creation + plugin bridge + cron"**
- `~/.hermes/skills/*/SKILL.md` (5 files — VPS)
- `src/hermes/plugins/__init__.py`
- `src/hermes/plugins/persona_plugin.py`
- `~/.hermes/crontab.yaml` (VPS)
- `~/.hermes/config.yaml` (plugin + cron sections — VPS)
- `src/persona/ritual_scheduler.py` (deprecation notice)
- Evidence: `verification-5-3.md`, `verification-5-4.md`, `verification-5-5.md`, `verification-5-6.md`

**Commit 3: "Phase 5 — Persona files migration + final evidence"**
- `src/persona/punishment_engine.py`
- `src/persona/reward_engine.py`
- `src/persona/transition_rules.py`
- `src/persona/mood_persistence.py`
- `src/persona/__init__.py`
- `src/persona/rituals/*.py` (deprecation notices)
- `PROGRESS.md`
- `docs/README.md` (if needed)
- All evidence files
- All auditor gate updates

### Push Strategy
- GitHub SSH key is BROKEN on VPS. Local `git push` via Windows may work if local SSH key is configured.
- If local SSH key also broken: stage all changes, create patch file, Faiz must push manually.
- Do NOT force push. Do NOT commit secrets.

## 14. Rollback Plan

**Time to Rollback:** < 2 minutes

| Component | Rollback Action | Command |
|---|---|---|
| SOUL.md | Restore from backup | `ssh guinevere-vps "cp ~/.hermes/SOUL.md.bak.\$(date +%Y%m%d) ~/.hermes/SOUL.md"` |
| Skills | Remove all 5 skill dirs | `ssh guinevere-vps "rm -rf ~/.hermes/skills/guinevere-{hardstop,consent,yandere,mood,rituals}"` |
| Cron | Remove crontab.yaml + config | `ssh guinevere-vps "rm ~/.hermes/crontab.yaml; sed -i '/^cron:/,/^[a-z]/d' ~/.hermes/config.yaml"` |
| PersonaPlugin | Remove plugin + config | `ssh guinevere-vps "rm -rf ~/code/guinevere/src/hermes/plugins/; sed -i '/persona_plugin/d' ~/.hermes/config.yaml"` |
| Persona files | Git checkout | `cd ~/code/guinevere && git checkout HEAD -- src/persona/` |
| Drift baseline | Revert hash | `cd ~/code/guinevere && git checkout HEAD -- src/persona/drift_detector.py` |

**Rollback Verification:**
```bash
ssh guinevere-vps "hermes skills list"              # → 0 guinevere skills
ssh guinevere-vps "hermes doctor"                    # → exit 0
ssh guinevere-vps "grep -c 'timezone: Asia/Jakarta' ~/.hermes/crontab.yaml" # → 0 (file gone)
cd ~/code/guinevere && git diff --name-only          # → clean
```

## 15. Evidence and Auditor Matrix

| Step | Verification Path | Auditor Surface |
|---|---|---|
| 5.3-CI2 Pre-flight | `verification-5-3-preflight.md` | Skills completeness |
| 5.1 | `verification-5-1.md` | Persona Integrity + ADR compliance |
| 5.2 | `verification-5-2.md` | ADR compliance |
| 5.3 | `verification-5-3.md` | Skills completeness + ADR compliance |
| 5.4 | `verification-5-4.md` | Persona Integrity + ADR compliance |
| 5.5 | `verification-5-5.md` | ADR compliance |
| 5.6 | `verification-5-6.md` | ADR compliance |
| 5.7 | `verification-5-7.md` | Persona Integrity + ADR compliance |
| 5.8 | `verification-5-8.md`, `evidence-phase-5.md` | All 3 auditors + 18 user gates |
| Auditor 1 (Persona) | `auditor-gate-5-persona.md` | Y4/Y5/Y6, HARD STOP, F-01-F-15, address rules, mood, drift |
| Auditor 2 (Skills) | `auditor-gate-5-skills.md` | 5 skills installed, activation modes, consent fallback, hook bindings |
| Auditor 3 (ADR) | `auditor-gate-5-adr.md` | ADR-035 compliance, 4-layer defense, code reduction, rollback |

**All 3 auditors must PASS. NEEDS REVIEW → investigate + fix. FAIL → block completion.**

## 16. Tracker Sync Plan

After parent verification of this file:
1. Mark planner gate todo completed.
2. Rewrite active todos to match planner wave order:
   - Wave 0: 5.3-CI2 (pre-flight smoke test)
   - Wave 1: 5.1 + 5.3 + 5.7 (parallel — 3 agents)
   - Wave 2: 5.2 (after 5.1 verified)
   - Wave 3: 5.4 (after 5.3 verified)
   - Wave 4: 5.5 (after 5.4 verified)
   - Wave 5: 5.6 (after 5.5 verified)
   - Wave 6: 5.8 final verification + commit + deploy (after all verified)
3. Keep deployment/push todos but mark blocked pending all gates + auditors PASS.
4. Ensure CI-2 smoke test runs BEFORE Wave 1 if not already completed.

## 17. Caveats and Blockers

- **GitHub SSH key broken on VPS** — commit locally; push requires key fix or manual Faiz intervention.
- **`critical: true` not native Hermes v0.15.2** — enforcement relies on Phase 4 startup gate (`scripts/startup_gate.py`). Scaffold references are documentation-level only.
- **Transition Rules refactor may affect mood cooldown** — ensure 5-min cooldown preserved. Test with `test_persona_mood.py` if it exists.
- **Hermes cron `hermes cron list` may not exist** — the CLI subcommand may not yet be implemented in v0.15.2. If unavailable, verify via crontab.yaml config parse + manual schedule calculation.
- **PersonaPlugin Redis DB5 connection** — use existing `state_manager.py` connection pool. Do not create new connection.
- **Phase 1 dependency** — batch plan states Phase 1 (Hermes Gateway) is a BLOCKING prerequisite. If Phase 1 hooks not fully operational, Plugin Bridge (5.4) will fail.
- **Two plugin deployments** — Standardize on `hermes-config/plugins/guinevere_safety/` as canonical. Do NOT modify `.hermes/plugins/guinevere-safety/` legacy deployment.
- **mood_persistence uses PostgreSQL** — not Redis DB5. Phase 5 migration aligns to Redis DB5 for runtime state (fast) and PostgreSQL for history (durable). This is a non-trivial change gated by Step 5.7.

## 18. Execution Checklist

- [ ] Parent read this planner gate file fully.
- [ ] Parent verified every scaffold field is concrete and checkable.
- [ ] Todos synced to planner wave order (corrected: 5.2 after 5.1).
- [ ] Collision scan confirmed before implementation.
- [ ] CI-2 pre-flight smoke test executed before Wave 1.
- [ ] One implementation sub-agent per step (max 3 parallel in Wave 1).
- [ ] Each delegation includes the relevant scaffold verbatim.
- [ ] Parent verifies claimed files and re-runs scaffold commands (does NOT accept self-report).
- [ ] Per-step verification files created ONLY after implementation passes.
- [ ] Independent auditor wave run after parent verification per step.
- [ ] All valid auditor findings fixed and re-audited via `task_id` continuation.
- [ ] 18 user gates (G-1 to G-18) verified PASS.
- [ ] 3 auditors all PASS.
- [ ] Deployment/commit/push performed only after all gates + auditors PASS.
- [ ] Git commit via 3 atomic commits (SOUL.md+drift, Skills+plugin+cron, Persona migration+evidence).
- [ ] PROGRESS.md updated with Phase 5 completion and evidence path.
- [ ] Final report includes changed files, verification results, evidence paths, auditor verdicts, caveats, and next action.

## 19. Footer

This planner gate resolves 4 execution research reports, 3 auditor gates, the existing batch plan v1.1, migration docs, and ADR-035 §Phase 5 into a machine-checkable implementation contract. It corrects the user-proposed 5.1∥5.2 parallel dependency (overridden to sequential), reconciles the PersonaPlugin path conflict, flags CI-2 as a Wave 0 preflight blocker, and requires all 18 user gates + 3 auditors PASS before deployment/commit/push.

**Planner version:** 1.0
**Date:** 2026-06-05
**Author:** Guinevere (Parent Orchestrator)
**Status:** PENDING PARENT VERIFICATION — Do not implement until parent-read and todos synced.
