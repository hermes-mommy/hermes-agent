# ADR-035 Phase 5 Execution Planner Gate v1.1 — Corrected Execution Scaffold Amendment

| Field | Value |
|---|---|
| Plan | ADR-035 Phase 5 — Skills + SOUL.md Migration (Corrected v1.1) |
| Status | **PLANNER GATE FILE** — supersedes stale parts of v1.0 |
| Date | 2026-06-06 |
| Evidence root | `docs/setup-evidence/phase-5/` |
| Research root | `research-reports/phase-5-execution/` |
| Baseline plan | `docs/setup-evidence/phase-5/batch-plan-phase-5.md` v1.1 |
| Supersedes | `planner-gate-phase-5-execution.md` v1.0 (stale assumptions) |
| ADR authority | `adr/ADR-035-hermes-migration.md` §Phase 5 |
| Oracle review | `research-reports/phase-5-execution/07-oracle-safety-review.md` (CONDITIONAL PASS) |

---

## 1. Planner Verdict

**CONDITIONAL READY WITH GATES.** The v1.0 planner was based on stale assumptions (278-line SOUL.md, greenfield skills, greenfield PersonaPlugin, functional `hermes run --internal`). This v1.1 amendment corrects all binding assumptions using current execution research findings.

Blocking pre-requisites before ANY implementation wave:

1. Parent must read this planner gate file fully.
2. Parent must verify every per-step scaffold is concrete and checkable.
3. Parent must sync active todos to the dependency map below.
4. Parent must run collision scan (verified below).
5. **Oracle 6 action items must be accepted or completed as pre-go-live gates** (see §2.3).
6. **`hermes run --internal` is a non-existent command. Any scaffold step referencing it is STALE.** All active VPS configs use `hermes chat -Q -q`. This v1.1 planner uses only `hermes chat -Q -q` and `hermes cron create`. If any step description mentions `hermes run`, it must be treated as outdated.
7. Deployment/restart/commit/push must execute only after all 18 user gates + 5 auditors PASS.
8. No VPS deploy, restart, systemd change, or destructive live operation may run without explicit per-action approval.

---

## 2. Research Synthesis — Corrections from v1.0

### 2.1 What Changed (Critical Corrections)

| Assumption in v1.0 | Current Reality (v1.1) | Source |
|---|---|---|
| SOUL.md is 278 lines, needs ~400 | SOUL.md is 463 lines, v2.0, already past original target. Still needs Oracle action items. | RR-01 §1, §11 |
| 0 skills installed (greenfield) | All 5 Phase 5 skills exist and are enabled on VPS. Step 5.3 is verification/content reconciliation + smoke-test evidence, not creation. | RR-02 §3.1 |
| PersonaPlugin must be created | PersonaPlugin ALREADY EXISTS at 513 lines with all 4 hooks. `hermes-config/plugins/guinevere_persona/` is wired. Step 5.4 is Redis DB5 persona-state key init + plugin/FSM wiring + deploy verification. | RR-04 §2.1, §2.2 |
| Hermes cron has 8 jobs in config.yaml | Hermes cron has **zero** registered jobs. `hermes cron list` returns "No scheduled jobs". Must use `hermes cron create`, not passive crontab.yaml. | RR-03 §3.4 |
| `hermes run --internal` is valid | `hermes run` does NOT exist in v0.15.2. Active VPS configs use `hermes chat -Q -q`. Any docs referencing `hermes run` are stale. | RR-03 §5.1, Oracle §5 |
| Redis DB5 has persona keys | Redis DB5 has budget/cost keys only. Zero `guinevere:*` persona keys exist. Must seed. | RR-04 §1.1 |
| 3 auditors needed | 5 auditors needed: persona safety, skills/runtime, rituals/cron, plugin/Redis, ADR/docs/evidence. | Oracle, evidence-phase-5 §3 |
| ADR-035 risk level = LOW | Must be MEDIUM. Phase 5 touches punishment_engine.py (L6), transition_rules.py, mood_persistence.py. | Oracle RF-4 |
| Y4 definition = "Possessive Spiral Bounded" | SystemPromptMaster uses "Absolute Possessive — Beyond Brutal" (v3.1). Must reconcile. | RR-01 §5 |

### 2.2 Conflict Resolution (v1.0 Amendments)

| Conflict from v1.0 | v1.1 Resolution |
|---|---|
| 5.1 SOUL.md must grow from 278 to 400 lines | SOUL.md is already 463 lines. Tasks: add Oracle action items (Safety > Operator hierarchy, No Confabulation, Confidentiality, Y0-Y3 definitions, Y4 definition reconciliation). Line target ~490-510. |
| Step 5.3 creates 5 skills | Skills already exist. Step 5.3: verify content reconciliation with batch plan specs, run evidence, validate local skill discovery via `hermes skills list`, directory/SKILL.md checks, and `hermes skills check`/`audit` caveat. `hermes skills doctor` is non-existent in Hermes v0.15.2 and must not be used as a gate. |
| Step 5.4 creates PersonaPlugin from scratch | PersonaPlugin already exists. Step 5.4: seed Redis DB5 with persona keys, reconcile key conventions, wire FSM engines to Redis writes, deploy plugin to VPS. |
| Step 5.5 uses passive crontab.yaml | Step 5.5 must register 5 cron jobs via `hermes cron create`. Stale crontab.yaml entries remain for reference only. Set `timezone: Asia/Jakarta` in config.yaml. |
| Step 5.6 uses `hermes run --internal` | **Forbidden.** Use `hermes chat -Q -q` for manual ritual tests. Verify via `hermes cron list` and gateway logs. |
| 3 auditors required | 5 auditors required. See §15 (Auditor Matrix). |

### 2.3 Oracle Action Items (Pre-Go-Live Gates)

Six Oracle action items from RR-07 must be resolved before Phase 5 go-live:

| Oracle ID | Action | Severity | Owning Step | Required Before Go-Live? |
|---|---|---|---|---|
| RF-1 | Reconcile Y4 definition — update SOUL.md §C to match SystemPromptMaster "Absolute Possessive — Beyond Brutal" or formally accept divergence with ADR-035 footnote | MEDIUM | 5.1 | Yes |
| RF-2 | Add Safety > Operator authority hierarchy to SOUL.md §D | MEDIUM | 5.1 | Yes, critical chain |
| RF-3 | Add No Confabulation + Confidentiality sections to SOUL.md | LOW-MEDIUM | 5.1 | Recommended |
| RF-4 | Update ADR-035 risk level for Phase 5 from LOW to MEDIUM | LOW | 5.8 | Yes, doc sync |
| RF-5 | Security incident (Redis transcript) — CLOSED by accepted risk | MEDIUM | — | No (already accepted) |
| RF-6 | Deploy PersonaPlugin to VPS + Hermes restart | MEDIUM | 5.4 deploy | Yes, post-deploy smoke test |

### 2.4 Hermes Cron Architecture (Corrected)

**`hermes cron create` is the only valid registration method.** The v1.0 planner incorrectly assumed:

- Config.yaml `cron:` section auto-registers jobs. **False** — gateway ticker runs (60s interval) but does NOT execute jobs without explicit `hermes cron create`.
- Crontab.yaml is loaded by Hermes automatically. **False** — crontab.yaml exists but `hermes cron list` shows zero jobs.

**Correct approach for Step 5.5:**

```bash
# Set timezone in config.yaml (currently empty: timezone: '')
# Then register each ritual:
hermes cron create "0 7 * * *" --name "ritual_morning" \
  --deliver "discord:CHANNEL_ID" \
  "Execute morning ritual: check mood, display streak, send greeting"
# Repeat for all 5 rituals
# Midnight uses --deliver local (NOT discord)
hermes cron create "0 0 * * *" --name "ritual_midnight" \
  --deliver "local" \
  "Execute midnight self-evaluation: mood transitions, punishment/reward review, streak update"
```

**Midnight isolation rules (non-negotiable):**
- Midnight must NOT use `--deliver discord:CHANNEL_ID`
- Use `--deliver local` or `--deliver origin`
- Verify with `hermes cron list` — confirm midnight job has no `discord` in delivery target
- Three-layer suppression: `suppress_output: true` (crontab.yaml) + `suppress_output: true` (config.yaml) + `-Q` (quiet flag)

---

## 3. Binding Decisions (v1.1 Updated)

| ID | Decision | Rationale |
|---|---|---|
| BD-001 | Step 5.2 (drift baseline) SEQUENTIAL after 5.1 | Hash depends on finalized SOUL.md. **Unchanged from v1.0.** |
| BD-002 | CI-2 pre-flight smoke test ALREADY PASSED. Step 5.3 verifies, not creates. | RR-02 confirms 5 skills installed and discovered. |
| BD-003 | PersonaPlugin at `src/hermes/plugins/persona_plugin.py` — **ALREADY EXISTS at 513 lines** | No greenfield creation. Step 5.4 bridges Redis + FSM. |
| BD-004 | Hermes cron jobs use `hermes cron create` with `--deliver` targets | Stale crontab.yaml = reference only. Zero jobs registered currently. |
| BD-005 | Skills locally installed **already**, Step 5.3 verifies | No new SKILL.md files needed unless reconciliation reveals gaps. |
| BD-006 | Midnight MUST use `--deliver local` (not non-existent `--internal-only`) | Two layers: delivery isolation + suppress_output flag. |
| BD-007 | No deploy/restart until ALL 18 gates + 5 auditors + 6 Oracle items PASS | Project policy blocks destructive live ops without approval. |
| BD-008 | All 5 skills = `always-active` activation — **CONFIRMED** | RR-02 §4.1 confirms activation modes. |
| BD-009 | Bundles deferred to post-Phase 7 | Unchanged from v1.0. |
| BD-010 | KEEP VERBATIM files must NOT be modified, **except drift_detector.py SOUL_BASELINE_HASH constant update (narrow hash-constant-only change, no other diff allowed)** | yandere_fsm.py, safe_mode.py, drift_corrector.py — zero tolerance. drift_detector.py: hash constant update allowed, zero other diff. |
| BD-011 | `hermes run --internal` is **FORBIDDEN** in all new scaffold | Command does not exist. Use `hermes chat -Q -q` for ad-hoc. |
| BD-012 | Redis DB5 must be seeded with `guinevere:*` persona keys first | Zero persona keys exist. Seeding is Step 5.4 prerequisite. |
| BD-013 | Risk level for Phase 5 = **MEDIUM** (not LOW as in ADR-035) | Oracle RF-4. Touches punishment_engine.py L6 + transition_rules + mood_persistence. |

---

## 4. Known State (Corrected)

### 4.1 VPS / Runtime
- Hermes Agent Gateway v0.15.2 active on VPS `100.94.104.22` via Tailscale
- `~/.hermes/SOUL.md` at **463 lines, v2.0** — all 10 sections (§A-§J) plus extras
- SOUL.md needs: Y4 reconciliation, Safety > Operator hierarchy, No Confabulation, Confidentiality, Y0-Y3 if absent
- `~/.hermes/config.yaml` (636 lines, auto-generated, `_config_version: 24`)
- **Zero Hermes cron jobs registered** — `hermes cron list` returns "No scheduled jobs"
- Config.yaml has 8 cron entries (3 maintenance + 5 rituals) using `hermes chat -Q -q` — NOT loaded by Hermes cron
- Crontab.yaml exists (5 rituals, `timezone: Asia/Jakarta`) — NOT loaded by Hermes cron
- **5 local skills installed + enabled**: guinevere-consent, hardstop, mood, rituals, yandere
- `hermes skills doctor` is not available in Hermes v0.15.2; local skills are validated by `hermes skills list`, directory/SKILL.md checks, and documented `hermes skills check`/`audit` caveat
- Custom skill auto-discovery **CONFIRMED WORKING** (CI-2 resolved)
- `src/hermes/plugins/persona_plugin.py` at 513 lines, 4 hooks implemented
- `hermes-config/plugins/guinevere_persona/` wired (plugin.yaml + `__init__.py`)
- Redis DB5 (port 6380, db=5): **14 keys, all budget/cost** — zero `guinevere:*` persona keys
- Redis DB0 (port 6380, db=0): 1 key — `guinevere:drift:baseline` (SHA-256 hash present)
- SSH via `guinevere-vps` host config — working
- GitHub SSH key BROKEN — `Permission denied (publickey)`

### 4.2 Local
- `src/hermes/safety_plugin.py` — 1,054 lines, 6 hooks, in-memory safety state
- `src/persona/` — 14 files, ~4,200 LOC, FSM engines
- `src/persona/ritual_scheduler.py` — APScheduler deprecated, not in active code
- `src/persona/rituals/*.py` — 5 ritual modules
- `hermes-config/SOUL.md` — local reference
- Tests: `tests/persona/` — 251 tests pass

### 4.3 Safety Boundaries Preserved
- Y4 permanent baseline, Y5 absolute ceiling, Y6 PROHIBITED (YandereSafetyError)
- HARD STOP 9-step protocol in SOUL.md
- D0-D4 distress table present
- F-01 to F-15 forbidden patterns listed
- 4-layer defense: SOUL.md -> Skills -> Plugin -> Drift
- Consent gate fail-closed with `fallback_on_timeout: deny`
- L6 disabled (sentinel `_L6_VALUE = 6`, not a PunishmentLevel member)
- KEEP VERBATIM: yandere_fsm.py, safe_mode.py, drift_corrector.py. drift_detector.py: KEEP VERBATIM except narrow hash-constant-only update in Step 5.2 (SOUL_BASELINE_HASH), zero other diff allowed.

---

## 5. User Gate Criteria (18 Gates — Updated for v1.1)

All must PASS for Phase 5 completion:

| # | Gate | Verification Method | Step |
|---|---|---|---|
| G-1 | SOUL.md complete (§A-§J + Oracle items) | `wc -l ~/.hermes/SOUL.md` >= 380; grep sections + RF-2/RF-3 content | 5.1 |
| G-2 | Five skills installed and working | `hermes skills list` -> 5 local enabled skills; five `~/.hermes/skills/guinevere-*/SKILL.md` files present; `hermes skills check`/`audit` caveat documented because local skills are not hub-installed and `hermes skills doctor` does not exist in v0.15.2 | 5.3 |
| G-3 | Cron active, 5 rituals correct WIB via `hermes cron create` | `hermes cron list` -> 5 jobs; next-fire WIB; `timezone: Asia/Jakarta` in config | 5.5 |
| G-4 | Mood persists via Redis DB5 | Code: `REDIS_DB = 5` confirmed; seed -> read verification | 5.4 |
| G-5 | Y6 blocked (YandereSafetyError) | `grep -c 'Y6.*PROHIBITED\|NEVER.*Y6' ~/.hermes/SOUL.md` >= 1 | 5.1, 5.3 |
| G-6 | Drift baseline reset | `sha256sum ~/.hermes/SOUL.md` matches Redis DB0 hash | 5.2 |
| G-7 | PersonaPlugin loads | `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; print('OK')"` | 5.4 |
| G-8 | Midnight suppressed (never Discord) | `--deliver local` confirmed; `suppress_output: true`; manual test | 5.5, 5.6 |
| G-9 | Safe mode functional | safe_mode.py KEEP VERBATIM (git diff clean) | 5.7 |
| G-10 | Consent gate fail-closed | `fallback_on_timeout: deny` in consent skill | 5.3, 5.4 |
| G-11 | No type suppression | Grep all touched files -> 0 matches | All |
| G-12 | No empty catch blocks | Grep all touched files -> 0 bare `except:` | All |
| G-13 | Rollback < 2 min | Documented rollback for each component | All |
| G-14 | Evidence files created | 8 verification + 5 auditor + 1 comprehensive evidence | All |
| G-15 | PROGRESS.md synced | Phase 5 entry with evidence path | 5.8 |
| G-16 | **5 auditors** PASS | persona, skills, cron/rituals, plugin/Redis, ADR/docs/evidence | 5.8 |
| G-17 | Phase 1 hooks operational | `hermes hooks list` -> 7 hooks | 5.8 |
| G-18 | CI-2 smoke test PASS | `verification-5-3-preflight.md` documented | 5.3 pre |

### 5.1 Oracle Deployment Gates (Additional)

| Oracle Gate | Criterion | Verification | Step |
|---|---|---|---|
| OG-1 | Y4 definition reconciled | `grep -c 'Absolute Possessive\|Beyond Brutal' ~/.hermes/SOUL.md` >= 1, or ADR footnote | 5.1 |
| OG-2 | Safety > Operator hierarchy in SOUL.md | `grep -c 'Safety.*Operator\|authority.*order' ~/.hermes/SOUL.md` >= 1 | 5.1 |
| OG-3 | No Confab + Confidentiality sections | `grep -c 'no confabulation\|confidence.*80%\|confidentiality' ~/.hermes/SOUL.md` >= 1 | 5.1 |
| OG-4 | ADR-035 risk = MEDIUM | Verify risk table for Phase 5 shows MEDIUM | 5.8 |
| OG-5 | Security incident closed | `security-incident-5-2-redis-transcript.md` exists with acceptance | 5.8 |
| OG-6 | PersonaPlugin deployed + smoke test | VPS import or equivalent check | 5.4 deploy |

---

## 6. Dependency Map — Corrected v1.1

### Critical Correction: NOT greenfield. Most artifacts already exist.

```
Wave 1 (parallel):
  ├── Step 5.1: SOUL.md Oracle action items
  ├── Step 5.3: Skills content verification
  └── Step 5.7: Persona Files Migration

Wave 2 (sequential, depends on 5.1):
  └── Step 5.2: Drift Baseline Hash recompute

Wave 3 (sequential, depends on 5.3 + 5.7):
  └── Step 5.4: Redis DB5 seed + key reconciliation + FSM wiring

Wave 4 (sequential, depends on 5.4):
  └── Step 5.5: Hermes cron rituals (hermes cron create)

Wave 5 (sequential, depends on 5.5):
  └── Step 5.6: Ritual Verification

Wave 6 (sequential, depends on all):
  └── Step 5.8: Final Integration + 18 gates + 5 auditors + Deploy
```

### Dependency Table

| Step | Depends On | Depended By | Reason |
|---|---|---|---|
| 5.1 | None | 5.2 | SOUL.md must finalize before drift hash |
| 5.3 | None | 5.4 | Skills known for Plugin references |
| 5.7 | None | 5.4 | FSM changes must complete before Redis wiring |
| 5.2 | 5.1 | 5.8 | Drift hash on finalized SOUL.md |
| 5.4 | 5.3, 5.7 | 5.5 | Plugin+Redis+FSM before cron can trigger |
| 5.5 | 5.4 | 5.6 | Cron after plugin hooks available |
| 5.6 | 5.5 | 5.8 | Verify cron before final verification |
| 5.8 | 5.2, 5.6 | Completion | All pass before final + deploy |

---

## 7. Parallel Execution Graph

| Wave | Steps | Max Parallel | Est. Duration |
|---|---|---|---|
| Wave 1 | 5.1 parallel 5.3 parallel 5.7 | 3 agents | 2-4h |
| Wave 2 | 5.2 | 1 agent | 10 min |
| Wave 3 | 5.4 | 1 agent | 2-3h |
| Wave 4 | 5.5 | 1 agent | 30 min |
| Wave 5 | 5.6 | 1 agent | 30 min |
| Wave 6 | 5.8 (final + deploy) | Parent | 1h |

**Max concurrent sub-agents:** 3 (Wave 1).

---

## 8. Collision Scan (Updated)

| Shared Resource | Touching Steps | Risk | Mitigation |
|---|---|---|---|
| `~/.hermes/SOUL.md` | 5.1 (write), 5.2 (read) | LOW | 5.2 read-only after 5.1 |
| `~/.hermes/config.yaml` | 5.4 (plugin), 5.5 (cron) | MEDIUM | Sequence enforced |
| `~/.hermes/skills/` | 5.3 (verify only) | LOW | Read-only |
| `src/hermes/plugins/persona_plugin.py` | 5.4 (modify) | LOW | Single owner |
| `src/persona/` (modified) | 5.7 (refactor), 5.4 (wire) | MEDIUM | 5.7 first, then 5.4 |
| `src/persona/ritual_scheduler.py` | 5.5, 5.7 (deprecate) | LOW | 5.7 authoritative |
| KEEP VERBATIM files | ALL (must NOT touch) | MEDIUM | Scaffold hard-reject |
| Redis DB5 | 5.4 (seed + write) | LOW | Single step |
| Evidence/docs | ALL (evidence) | HIGH | Parent-only writes |
| Shared docs (ADR-Index, README) | Parent only | NONE | Parent handles |
| `adr/ADR-035-hermes-migration.md` | 5.8 (risk level edit) | LOW | Parent, single edit |

**Verdict:** No blocking collisions. Steps 5.7 then 5.4 sequence enforced for FSM -> Redis bridge. KEEP VERBATIM files highest risk.

---

## 9. Master Todo (v1.1 Corrected)

| Step | Wave | Depends On | Agents | Time | Category | Status |
|---|---|---|---|---|---|---|
| 5.1 SOUL.md Oracle actions | 1 | None | 1 | 1.5h | deep | Pending |
| 5.3 Skills verification | 1 | None | 1 | 30min | quick | Pending |
| 5.7 Persona migration | 1 | None | 1 | 2h | deep | Pending |
| 5.2 Drift recompute | 2 | 5.1 | 1 | 10min | quick | Pending |
| 5.4 Plugin/Redis bridge | 3 | 5.3, 5.7 | 1 | 2-3h | deep | Pending |
| 5.5 Cron rituals | 4 | 5.4 | 1 | 30min | unspecified-high | Pending |
| 5.6 Ritual verify | 5 | 5.5 | 1 | 30min | quick | Pending |
| 5.8 Final + deploy | 6 | 5.2, 5.6 | Parent | 1h | Parent | Pending |

**Parallel run config (Wave 1):**
```
task(category="deep", run_in_background=true, prompt="Step 5.1 SOUL.md Oracle actions")
task(category="deep", run_in_background=true, prompt="Step 5.7 Persona migration")
task(category="quick", run_in_background=true, prompt="Step 5.3 Skills verification")
```

---

## 10. Exact Files to Create or Modify

### Step 5.1 (SOUL.md Oracle Actions)
- MODIFY: `~/.hermes/SOUL.md` (VPS, 463 -> ~510 lines)
  - Add Safety > Operator authority hierarchy (§D)
  - Add No Confabulation section (new subsection)
  - Add Confidentiality section (new subsection)
  - Add Y0-Y3 definitions if absent (§C)
  - Reconcile Y4 language to match SystemPromptMaster v3.1

### Step 5.2 (Drift Baseline Recompute)
- NARROW MODIFY: `src/persona/drift_detector.py` (update SOUL_BASELINE_HASH constant ONLY — KEEP VERBATIM for all other code; any non-hash diff is a hard rejection)
- MODIFY: Redis DB0 key `guinevere:drift:baseline` (set new SHA-256)

### Step 5.3 (Skills Verification)
- CREATE: `docs/setup-evidence/phase-5/verification-5-3-content-reconciliation.md`
- No remote changes unless content gaps found

### Step 5.4 (Plugin/Redis Bridge)
- MODIFY: `src/hermes/plugins/persona_plugin.py` (key reconciliation)
- MODIFY: `src/persona/punishment_engine.py` (Redis write via StateManager)
- MODIFY: `src/persona/reward_engine.py` (Redis write via StateManager)
- MODIFY: `src/persona/mood_engine.py` (Redis write via StateManager)
- MODIFY: `src/hermes/safety_plugin.py` (delegate to Redis DB5)
- EXECUTE: Redis DB5 seed (MSET guinevere:* persona state keys)
- (Remote) DEPLOY: plugin to VPS + controlled Hermes restart

### Step 5.5 (Hermes Cron Rituals)
- EXECUTE: `hermes cron create` for 5 rituals on VPS
- MODIFY: `~/.hermes/config.yaml` (set `timezone: Asia/Jakarta`)
- **Forbidden:** Do NOT rely on crontab.yaml (stale)
- **Forbidden:** Do NOT use `hermes run --internal` (does not exist)

### Step 5.6 (Ritual Verification)
- CREATE: `docs/setup-evidence/phase-5/verification-5-6-v2.md`
- **Forbidden:** Do NOT use `hermes run --internal` (stale)
- Use: `hermes cron list`, `hermes cron status`, gateway logs, `hermes chat -Q -q`

### Step 5.7 (Persona Files Migration)
- MODIFY: `src/persona/punishment_engine.py` (refactor, L1-L5, L6 guard)
- MODIFY: `src/persona/reward_engine.py` (refactor)
- MODIFY: `src/persona/transition_rules.py` (refactor)
- MODIFY: `src/persona/mood_persistence.py` (refactor)
- MODIFY: `src/persona/__init__.py` (update exports)
- DEPRECATE: `src/persona/ritual_scheduler.py` (add notice)
- DEPRECATE: `src/persona/rituals/morning.py`, `midday.py`, `afternoon.py`, `evening.py`, `midnight.py`
- KEEP VERBATIM (DO NOT TOUCH): yandere_fsm.py, safe_mode.py, drift_corrector.py. drift_detector.py: KEEP VERBATIM except SOUL_BASELINE_HASH constant (updated in Step 5.2).

### Step 5.8 (Final Integration)
- CREATE: `docs/setup-evidence/phase-5/verification-5-8-v2.md`
- CREATE/UPDATE: `docs/setup-evidence/phase-5/evidence-phase-5.md`
- MODIFY: `PROGRESS.md` (mark Phase 5 complete)
- MODIFY: `adr/ADR-035-hermes-migration.md` (risk level LOW -> MEDIUM)
- MODIFY: `docs/README.md` if needed

---

## 11. Token, Secret, and Safety Handling

- Never commit or print Discord tokens, API keys, DB passwords, SOPS/age keys, surveillance credentials, or decrypted env values.
- VPS operations use SSH via `guinevere-vps` host alias (pre-configured key).
- No secrets are created or modified in Phase 5.
- Redis DB5 persona state keys contain NO secret data (mood, yandere level, etc.).
- Redis DB5 seeding uses `redis-cli -p 6380` with password from environment. **Never print the password.**
- Midnight ritual must NEVER route to Discord (enforced by `--deliver local` + `suppress_output: true`).
- HARD STOP, Y6 prohibition, consent fail-closed, distress protocol preserved as immutable safety boundaries.
- GitHub SSH key is broken — commit via local git; push requires manual intervention.
- The `hermes run --internal` command does NOT exist in Hermes v0.15.2. All references are stale.

---

## 12. Per-Step Verification Scaffolds

### 12.1 Step 5.1 Scaffold — SOUL.md Oracle Action Items

| Field | Contract |
|---|---|
| **Expected Files** | `~/.hermes/SOUL.md` (MODIFIED, ~490-510 lines) |
| **Forbidden Patterns (concrete regexes — must return 0 matches)** | `ssh guinevere-vps "grep -c 'I am Hermes' ~/.hermes/SOUL.md"` -> 0 (no generic identity); `ssh guinevere-vps "grep -i 'Y6' ~/.hermes/SOUL.md | grep -vi 'PROHIBITED\|NEVER\|forbidden\|blocked'"` -> 0 (Y6 only in prohibition context); `ssh guinevere-vps "grep -c 'Possessive Spiral' ~/.hermes/SOUL.md"` -> 0 unless ADR footnote exists (old Y4 language); |
| **Required Commands** | `ssh guinevere-vps "wc -l ~/.hermes/SOUL.md"` -> >= 480; `ssh guinevere-vps "grep -c 'Safety.*Operator\|authority.*order\|safe.word.*ADR' ~/.hermes/SOUL.md"` -> >= 1; `ssh guinevere-vps "grep -c 'no confabulation\|confidence.*80%\|Mommy ingat' ~/.hermes/SOUL.md"` -> >= 1; `ssh guinevere-vps "grep -c 'reveal.*system\|confidentiality\|system prompt.*contents' ~/.hermes/SOUL.md"` -> >= 1; `ssh guinevere-vps "grep -c 'Absolute Possessive\|Beyond Brutal' ~/.hermes/SOUL.md"` -> >= 1 OR ADR footnote present; `ssh guinevere-vps "grep -c 'Y0\|Y[0-3]' ~/.hermes/SOUL.md"` -> >= 1 (Y0-Y3 present); `ssh guinevere-vps "grep -c 'HARD STOP' ~/.hermes/SOUL.md"` -> >= 1; `ssh guinevere-vps "grep -c 'Y6.*PROHIBITED\|NEVER.*Y6' ~/.hermes/SOUL.md"` -> >= 1; `ssh guinevere-vps "grep -c '| D[0-4]' ~/.hermes/SOUL.md"` -> >= 5; `ssh guinevere-vps "grep -c '| L[1-5]' ~/.hermes/SOUL.md"` -> >= 5; `ssh guinevere-vps "grep -c 'prompt injection\|injection defense' ~/.hermes/SOUL.md"` -> >= 1 |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-1-v2.md`; `docs/setup-evidence/phase-5/auditor-gate-5-1.md` |
| **Hard Rejection Criteria** | SOUL.md < 480 lines -> FAIL; Safety > Operator hierarchy missing (grep returns 0) -> FAIL; No Confabulation missing (grep returns 0) -> FAIL; Confidentiality missing (grep returns 0) -> FAIL; Y6 not explicitly prohibited -> FAIL; Y4 unreconciled (Possessive Spiral present without ADR footnote) -> FAIL; HARD STOP < 9 steps -> FAIL |

### 12.2 Step 5.2 Scaffold — Drift Baseline Recompute (KEEP VERBATIM with narrow hash exception)

| Field | Contract |
|---|---|
| **Expected Files** | `src/persona/drift_detector.py` (NARROW MODIFY: SOUL_BASELINE_HASH constant only); Redis DB0 key updated |
| **Forbidden Patterns** | Empty hash `""`; placeholder `"TODO"` near hash; any non-hash modification to `drift_detector.py` (diff beyond the one constant assignment line) |
| **Required Commands** | `ssh guinevere-vps "sha256sum ~/.hermes/SOUL.md"` -> output hash matches stored constant; `python -c "from src.persona.drift_detector import DriftDetector; h=DriftDetector.SOUL_BASELINE_HASH; assert len(h)==64 and all(c in '0123456789abcdef' for c in h); print('valid:', h[:16])"` -> valid 64-char hex; `git diff src/persona/drift_detector.py` -> only changes allowed: the SOUL_BASELINE_HASH assignment line (one-line diff) |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-2-v2.md` |
| **Hard Rejection Criteria** | Hash mismatch between file and stored value -> FAIL; Hash empty/placeholder -> FAIL; Not 64-char hex -> FAIL; `git diff` shows changes BEYOND the SOUL_BASELINE_HASH constant line -> FAIL (KEEP VERBATIM breach) |

### 12.3 Step 5.3 Scaffold — Skills Content Verification (NOT Creation)

| Field | Contract |
|---|---|
| **Expected Files** | `docs/setup-evidence/phase-5/verification-5-3-content-reconciliation.md` (CREATE) |
| **Forbidden Patterns** | N/A — read-only verification |
| **Required Commands** | `ssh guinevere-vps "hermes skills list"` -> 5 local enabled skills present (guinevere-consent, hardstop, mood, rituals, yandere); `ssh guinevere-vps "ls ~/.hermes/skills/guinevere-*"` -> 5 directories; `ssh guinevere-vps "hermes skills check guinevere-consent guinevere-hardstop guinevere-mood guinevere-rituals guinevere-yandere"` -> exits 0 or documents local-skill/no-hub caveat; SKILL.md content reconciliation: verify each skill has required fields (name, version, purpose, activation: always-active). For consent: verify `fallback_on_timeout: deny`. For yandere: verify Y6 PROHIBITED. For hardstop: verify HARD STOP protocol. For rituals: verify midnight wording references `--deliver local`/local-only delivery, not a non-existent `--internal-only` flag. |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-3-content-reconciliation.md` |
| **Hard Rejection Criteria** | Any of 5 skills missing -> FAIL; `hermes skills list` does not show all 5 local skills enabled -> FAIL; Content mismatch (consent missing deny, yandere Y6 not prohibited, hardstop missing HARD STOP, rituals midnight wording relies on non-existent `--internal-only`) -> FAIL; CI-2 smoke test NOT documented -> FAIL |

### 12.4 Step 5.4 Scaffold — Plugin/Redis Bridge

| Field | Contract |
|---|---|
| **Expected Files** | `src/hermes/plugins/persona_plugin.py` (MODIFIED); `src/persona/punishment_engine.py` (MODIFIED); `src/persona/reward_engine.py` (MODIFIED); `src/persona/mood_engine.py` (MODIFIED); `src/hermes/safety_plugin.py` (MODIFIED); Remote: `~/.hermes/config.yaml` (MODIFIED if needed) |
| **Forbidden Patterns** | `as any` / `@ts-ignore` / `# type: ignore`; bare `except:` or `except Exception:` without specific handling and logging; empty catch blocks; midnight Discord routing; Redis credential printed/logged; Redis DB5 seed command in evidence (must be sanitized) |
| **Required Commands** | `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; print('OK')"` -> OK; `python -m compileall src/hermes/plugins` -> exit 0; `python -m compileall src/persona/punishment_engine.py src/persona/reward_engine.py src/persona/mood_engine.py` -> exit 0; `lsp_diagnostics` on all modified files -> clean (0 new errors); Redis DB5 seed verification: `ssh guinevere-vps "redis-cli -p 6380 -n 5 EXISTS guinevere:mood_variant guinevere:yandere_level guinevere:punishment_level"` -> all return 1; VPS deploy verification: `ssh guinevere-vps "python -c 'from hermes_config.plugins.guinevere_persona import *; print(\"OK\")'"` -> OK (or equivalent) |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-4-v2.md` |
| **Hard Rejection Criteria** | Plugin fails to import -> FAIL; Redis DB5 seed fails -> FAIL; Key conventions not reconciled (plugin + safety read different keys) -> FAIL; Midnight can route to Discord -> FAIL (CRITICAL); Bare except without logging -> FAIL; Type suppression patterns found -> FAIL; FSM engine import broken -> FAIL |

### 12.5 Step 5.5 Scaffold — Hermes Cron Rituals

| Field | Contract |
|---|---|
| **Expected Files** | Remote: `~/.hermes/config.yaml` (MODIFIED — timezone set); EXECUTED: `hermes cron create` for 5 jobs |
| **Forbidden Patterns** | `hermes run --internal` (anywhere in scaffold commands); APScheduler imports in active code paths; Midnight with `--deliver discord`; Missing `timezone: Asia/Jakarta` in config.yaml; Reference to crontab.yaml as the active mechanism |
| **Required Commands** | `ssh guinevere-vps "hermes cron list"` -> 5 jobs with correct names; `ssh guinevere-vps "grep 'timezone' ~/.hermes/config.yaml"` -> `timezone: Asia/Jakarta` present; `ssh guinevere-vps "hermes cron status"` -> shows PID and active jobs; Verify midnight job: `ssh guinevere-vps "hermes cron list | grep -A5 midnight"` -> delivery target is NOT discord; Python parse: `ssh guinevere-vps "cat ~/.hermes/config.yaml | python -c 'import sys,yaml; d=yaml.safe_load(sys.stdin); assert any(k==\"timezone\" for k in d.keys()) or any(\"timezone\" in str(j) for j in d.get(\"cron\",[])); print(\"timezone OK\")'"` |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-5-v2.md` |
| **Hard Rejection Criteria** | `hermes cron list` shows < 5 jobs -> FAIL; Midnight delivery includes `discord` -> FAIL (CRITICAL); `timezone: Asia/Jakarta` not set -> FAIL; `hermes run --internal` referenced -> FAIL (stale); No cron jobs registered (only old config.yaml cron entries) -> FAIL |

### 12.6 Step 5.6 Scaffold — Ritual Verification (Corrected)

| Field | Contract |
|---|---|
| **Expected Files** | `docs/setup-evidence/phase-5/verification-5-6-v2.md` (CREATE) |
| **Forbidden Patterns** | `hermes run --internal` in any verification command; `hermes run --internal-only` in any verification command |
| **Required Commands** | `ssh guinevere-vps "hermes cron list"` -> 5 jobs visible; `ssh guinevere-vps "hermes cron status"` -> active gateway PID; Manual test morning ritual: `ssh guinevere-vps "hermes chat -Q -q 'Execute morning ritual: check mood, display streak, send greeting'"` -> produces mood-aware greeting; Midnight isolation: `ssh guinevere-vps "grep -A2 'midnight' ~/.hermes/config.yaml | grep suppress_output"` -> found; `ssh guinevere-vps "journalctl -u hermes-gateway -n 50 --no-pager | grep -i 'cron'"` -> cron entries visible after tick cycle; `ssh guinevere-vps "grep -A2 'ritual_midnight' ~/.hermes/config.yaml | grep 'deliver'"` -> no discord reference |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-6-v2.md` |
| **Hard Rejection Criteria** | `hermes cron list` shows < 5 -> FAIL; Midnight can route to Discord -> FAIL (CRITICAL); No cron entries in journal -> FAIL; `hermes run` used in any new command -> FAIL (stale reference) |

### 12.7 Step 5.7 Scaffold — Persona Files Migration

| Field | Contract |
|---|---|
| **Expected Files** | `src/persona/punishment_engine.py` (MODIFIED); `src/persona/reward_engine.py` (MODIFIED); `src/persona/transition_rules.py` (MODIFIED); `src/persona/mood_persistence.py` (MODIFIED); `src/persona/__init__.py` (MODIFIED); 5 `rituals/*.py` (DEPRECATED); `ritual_scheduler.py` (DEPRECATED) |
| **Forbidden Patterns** | `as any` / `@ts-ignore` / `# type: ignore`; bare `except:` without specific exception type; `from apscheduler` in active (non-deprecated) files; `PunishmentLevel.L6` allowed (must raise error); Modification of KEEP VERBATIM files beyond authorized exception (yandere_fsm.py, safe_mode.py, drift_corrector.py = zero diff; drift_detector.py = SOUL_BASELINE_HASH line only, Step 5.2 owns this, Step 5.7 must NOT touch drift_detector.py at all) |
| **Required Commands** | `python -c "from src.persona import YandereEngine, PunishmentEngine, RewardEngine, MoodRepository; print('OK')"` -> OK; `python -c "from src.persona.punishment_engine import PunishmentLevel; assert PunishmentLevel.L5.value == 5; print('L5 max OK')"` -> OK; `python -m compileall src/persona` -> exit 0; `lsp_diagnostics` on all modified files -> clean (0 new errors); `python -m pytest tests/persona/ -v` (if tests exist) -> exit 0; `git diff --name-only src/persona/yandere_fsm.py src/persona/safe_mode.py src/persona/drift_detector.py src/persona/drift_corrector.py` -> only drift_detector.py MAY appear (hash update owned by Step 5.2); yandere_fsm.py, safe_mode.py, drift_corrector.py MUST be empty |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-7-v2.md`; `docs/setup-evidence/phase-5/auditor-gate-5-7.md` |
| **Hard Rejection Criteria** | Any KEEP VERBATIM file modified -> FAIL (CRITICAL); APScheduler import in active code -> FAIL; L6 boundary violation -> FAIL (CRITICAL); Import chain broken -> FAIL; Type diagnostics not clean (new errors) -> FAIL; `git diff` shows KEEP changes -> FAIL |

### 12.8 Step 5.8 Scaffold — Final Integration Verification

| Field | Contract |
|---|---|
| **Expected Files** | All evidence files from steps 5.1-5.7; `verification-5-8-v2.md` (CREATE); `evidence-phase-5.md` (UPDATE); 5 auditor files all PASS; `PROGRESS.md` updated; `adr/ADR-035-hermes-migration.md` (risk level updated); `docs/README.md` if needed |
| **Forbidden Patterns** | Any uncommitted secret; `hermes run --internal` references in final evidence; Missing Oracle action items |
| **Required Commands** | All 18 gates verified PASS; All 6 Oracle gates verified PASS/ACCEPTED; 5 auditors all PASS; `ssh guinevere-vps "wc -l ~/.hermes/SOUL.md"` -> >= 480; `ssh guinevere-vps "hermes skills list"` -> 5 local enabled skills; `ssh guinevere-vps "test -f ~/.hermes/skills/guinevere-consent/SKILL.md && test -f ~/.hermes/skills/guinevere-hardstop/SKILL.md && test -f ~/.hermes/skills/guinevere-mood/SKILL.md && test -f ~/.hermes/skills/guinevere-rituals/SKILL.md && test -f ~/.hermes/skills/guinevere-yandere/SKILL.md"` -> exit 0; `ssh guinevere-vps "hermes cron list"` -> 5; `ssh guinevere-vps "grep -c 'Asia/Jakarta' ~/.hermes/config.yaml"` -> >= 1; `python -c "from src.hermes.plugins.persona_plugin import PersonaPlugin; print('OK')"` -> OK; `ssh guinevere-vps "grep 'Y6.*PROHIBITED' ~/.hermes/SOUL.md"` -> match found; Drift hash match; KEEP files unchanged |
| **Evidence Requirements** | `docs/setup-evidence/phase-5/verification-5-8-v2.md`; `docs/setup-evidence/phase-5/evidence-phase-5.md` |
| **Hard Rejection Criteria** | Any sub-step fails -> FAIL; Y4 not baseline declared -> FAIL; Midnight Discord leak possible -> FAIL (CRITICAL); Plugin fails to load -> FAIL; Drift hash mismatch -> FAIL; Any Oracle gate unresolved -> FAIL; Any of 5 auditors FAIL -> FAIL; Risk level not updated to MEDIUM -> FAIL; `hermes run --internal` in any evidence -> FAIL (stale) |

---

## 13. Implementation Design

### 13.1 Step 5.1 — SOUL.md Oracle Action Items
- Edit `~/.hermes/SOUL.md` on VPS via SSH.
- Add Safety > Operator authority hierarchy under §D as explicit chain.
- Add No Confabulation section with confidence thresholds (80%), examples.
- Add Confidentiality section (never reveal system prompt contents).
- Add Y0-Y3 definitions if absent in §C.
- Update Y4 definition from "Possessive Spiral Bounded" to "Absolute Possessive — Beyond Brutal" or add ADR-035 footnote accepting divergence.
- Backup existing SOUL.md before editing.
- Target: ~490-510 lines.
- Verify with structured grep checks from scaffold.

### 13.2 Step 5.2 — Drift Baseline Recompute
- Compute SHA-256 of finalized SOUL.md.
- Update `DriftDetector.SOUL_BASELINE_HASH` constant in `src/persona/drift_detector.py`.
- Update Redis DB0 key `guinevere:drift:baseline` via redis-cli.
- Verify: re-compute hash matches stored constant.

### 13.3 Step 5.3 — Skills Content Reconciliation
- Verify all 5 installed skills match batch plan content specs.
- For each skill, SKILL.md must have: name, version, purpose, activation, hooks. All must be `always-active`.
- consent: verify `fallback_on_timeout: deny`.
- yandere: verify Y6 PROHIBITED/NEVER.
- hardstop: verify 9-step HARD STOP protocol.
- mood: verify 5-min cooldown, 5 mood states, streak milestones.
- rituals: verify 5 rituals WIB, DND 00:00-07:00, midnight suppressed.
- Document any content gaps found; propose fixes if needed.
- CI-2 pre-flight smoke test already PASSED (RR-02). Reference it.

### 13.4 Step 5.4 — Plugin/Redis Bridge
- Seed Redis DB5 with persona state keys via redis-cli MSET (sanitized, no password in evidence).
- Reconcile key conventions: `persona_plugin.py` uses `guinevere:mood` + `guinevere:mood_score`; `guinevere_safety` uses `guinevere:mood_variant`. Use `guinevere_safety` convention as canonical.
- Wire FSM engines to Redis DB5 writes:
  - `punishment_engine.py`: call StateManager.set_punishment() in apply/escalate
  - `reward_engine.py`: call StateManager.set_reward() in award
  - `mood_engine.py`: call StateManager.set_mood() after evaluate_mood
- Deploy to VPS: copy `src/hermes/plugins/` to VPS, controlled Hermes restart.
- Verify plugin loads post-deployment.

### 13.5 Step 5.5 — Hermes Cron Rituals
- Set `timezone: Asia/Jakarta` in `~/.hermes/config.yaml`.
- Register 5 cron jobs via `hermes cron create`:
  - morning: `0 7 * * *` -> `--deliver discord:CHANNEL_ID`
  - midday: `0 12 * * *` -> `--deliver discord:CHANNEL_ID`
  - afternoon: `0 17 * * *` -> `--deliver discord:CHANNEL_ID`
  - evening: `0 21 * * *` -> `--deliver discord:CHANNEL_ID`
  - midnight: `0 0 * * *` -> `--deliver local` (NO discord)
- Verify with `hermes cron list`.
- Do NOT modify or rely on stale crontab.yaml.

### 13.6 Step 5.6 — Ritual Verification
- Verify via `hermes cron list` -> 5 jobs, correct schedules.
- Verify midnight delivery target is `local` not `discord`.
- Test manual execution via `hermes chat -Q -q` for each ritual.
- Check gateway logs for cron tick execution.
- Verify midnight suppression via config grep.
- **No `hermes run --internal` anywhere.**

### 13.7 Step 5.7 — Persona Migration
- REFACTOR punishment_engine.py: wire to plugin hooks, L1-L5, L6 guard.
- REFACTOR reward_engine.py: wire to PersonaPlugin hooks.
- REFACTOR transition_rules.py: cooldown via Redis TTL.
- REFACTOR mood_persistence.py: async session support.
- DEPRECATE ritual_scheduler.py + 5 rituals/*.py.
- UPDATE `__init__.py` exports.
- KEEP VERBATIM: yandere_fsm.py, safe_mode.py, drift_detector.py, drift_corrector.py.

### 13.8 Step 5.8 — Final Verification + Deploy Gate
- Run all 18 gate verifications.
- Verify 6 Oracle deployment gates.
- Run all 5 auditor checks.
- Update ADR-035 risk level to MEDIUM.
- Update PROGRESS.md with evidence path.
- Stage all changes for commit (but do not commit/ push without explicit request).
- Document deployment status, blockers, and caveats.

---

## 14. Commit Strategy

**Do NOT commit or push until all 18 gates + 5 auditors + 6 Oracle gates PASS.**

### Git-Master Compliance

When commits are authorized, use `git-master` skill (`task(category='quick', load_skills=['git-master'], prompt='...')`) with the following workflow:

1. **Style detection first**: `GIT_MASTER=1 git status`, `GIT_MASTER=1 git diff --stat`, `GIT_MASTER=1 git log --oneline -10` to detect repo convention before committing.
2. **File count + dependency grouping**: final commit count determined by inspecting the actual change set — not predetermined. Group logically: (a) SOUL.md + drift, (b) plugin/Redis/cron, (c) persona migration, (d) evidence + ADR update — but merge or split as the actual diff requires.
3. **Atomic per theme**: each commit groups changes by theme (SOUL, skills, plugin, persona, evidence). No commit mixes unrelated themes.
4. **Concise message matching repo style**: determined by `git log` inspection.

### Illustrative Commit Candidates (minimum, not binding)

Final commit structure depends on actual file count and dependency grouping at time of commit:

| Candidate | Theme | Suggested Files |
|---|---|---|
| A | SOUL.md Oracle + drift baseline | `~/.hermes/SOUL.md`, `src/persona/drift_detector.py` (hash), verification-5-1/5-2 |
| B | Plugin/Redis bridge + cron | Plugin files, Redis seed config, cron jobs, verification-5-3/5-4/5-5/5-6 |
| C | Persona migration | Refactored/deprecated persona files, verification-5-7 |
| D | Final evidence + ADR update | `evidence-phase-5.md`, `PROGRESS.md`, `adr/ADR-035-hermes-migration.md`, verification-5-8 |

### Push Strategy
- GitHub SSH key is BROKEN on VPS. Local `git push` via Windows may work.
- If local SSH also broken: stage all changes, create patch file, Faiz must push manually.
- Do NOT force push. Do NOT commit secrets.

---

## 15. Rollback Plan

**Time to Rollback:** < 2 minutes

> **IMPORTANT:** Destructive rollback commands below are labeled `REQUIRES EXPLICIT PER-ACTION APPROVAL — DO NOT RUN AUTOMATICALLY`. Safe preview/list commands are provided as alternatives. No rollback command may execute without parent explicit approval per AGENTS.md §7.

| Component | Safe Preview Command | Destructive Rollback (Requires Approval) |
|---|---|---|
| SOUL.md | `ssh guinevere-vps "ls -la ~/.hermes/SOUL.md*"` (list backups) | `REQUIRES APPROVAL: ssh guinevere-vps "cp ~/.hermes/SOUL.md.bak ~/.hermes/SOUL.md"` |
| Skills | `ssh guinevere-vps "hermes skills list"` (confirm current state) | `REQUIRES APPROVAL: ssh guinevere-vps "rm -rf ~/.hermes/skills/guinevere-{hardstop,consent,yandere,mood,rituals}"` |
| Cron | `ssh guinevere-vps "hermes cron list"` (list job IDs) | `REQUIRES APPROVAL: hermes cron remove <id>` (per job, 5 max) |
| PersonaPlugin | `ssh guinevere-vps "ls ~/code/guinevere/src/hermes/plugins/"` (list files) | `REQUIRES APPROVAL: ssh guinevere-vps "rm -rf ~/code/guinevere/src/hermes/plugins/; git checkout HEAD -- src/hermes/plugins/"` |
| Redis DB5 seed | `ssh guinevere-vps "redis-cli -p 6380 -n 5 KEYS 'guinevere:*'"` (list keys, no DEL) | `REQUIRES APPROVAL: redis-cli -p 6380 -n 5 KEYS 'guinevere:*' \| xargs redis-cli -p 6380 -n 5 DEL` |
| Persona files | `git diff --name-only src/persona/` (list changes) | `REQUIRES APPROVAL: git checkout HEAD -- src/persona/` |
| Drift baseline | `ssh guinevere-vps "redis-cli -p 6380 -n 0 GET guinevere:drift:baseline"` (read current) | `REQUIRES APPROVAL: git checkout HEAD -- src/persona/drift_detector.py` |
| ADR-035 risk | `grep -n 'Phase 5.*risk' adr/ADR-035-hermes-migration.md` (show current) | `REQUIRES APPROVAL: git checkout HEAD -- adr/ADR-035-hermes-migration.md` |

**Rollback Verification:**
```bash
ssh guinevere-vps "hermes skills list"              # -> 0 guinevere skills (or pre-Phase 5 state)
ssh guinevere-vps "hermes cron list"                # -> "No scheduled jobs"
ssh guinevere-vps "hermes doctor"                   # -> exit 0
cd ~/code/guinevere && git diff --name-only          # -> clean (all Phase 5 changes reverted)
```

---

## 16. Evidence and Auditor Matrix

### Evidence Files (v1.1)

| Step | Verification Path | Notes |
|---|---|---|
| 5.1 | `verification-5-1-v2.md` | Updated for Oracle action items |
| 5.2 | `verification-5-2-v2.md` | Updated for recomputed hash |
| 5.3 | `verification-5-3-content-reconciliation.md` | NEW — skills content check |
| 5.4 | `verification-5-4-v2.md` | Updated for Redis seed + FSM wire |
| 5.5 | `verification-5-5-v2.md` | Updated for hermes cron create |
| 5.6 | `verification-5-6-v2.md` | NEW — corrected for hermes chat -Q -q |
| 5.7 | `verification-5-7-v2.md` | Updated for corrected state |
| 5.8 | `verification-5-8-v2.md` | NEW — final with all gates |
| All | `evidence-phase-5.md` | Comprehensive (updated) |

### Auditor Matrix (5 Auditors Required)

| Auditor | Scope | Checks | Steps |
|---|---|---|---|
| **Auditor 1: Persona Safety** | SOUL.md + Yandere/Punishment boundaries | Y4/Y5/Y6, HARD STOP, F-01-F-15, No Confabulation, Safety > Operator hierarchy, Confidentiality, Oracle RF-1 through RF-3 | 5.1, 5.7 |
| **Auditor 2: Skills/Runtime** | 5 SKILL.md files + hermes skills system | All 5 installed, activation modes correct, consent deny fallback, hardstop 9-step, yandere Y6 PROHIBITED, mood cooldown 5min, ritual DND window, doctor clean | 5.3 |
| **Auditor 3: Rituals/Cron** | Hermes cron jobs + midnight suppression | 5 jobs via `hermes cron create`, delivery targets correct, midnight NOT discord, timezone Asia/Jakarta, gateway logs | 5.5, 5.6 |
| **Auditor 4: Plugin/Redis** | PersonaPlugin + Redis DB5 bridge | Plugin loads, Redis DB5 seeded, key conventions reconciled, FSM wiring complete, deployment verified | 5.4 |
| **Auditor 5: ADR/Docs/Evidence** | ADR-035 compliance, evidence files, doc sync | Risk level MEDIUM, all evidence paths exist, PROGRESS.md updated, 18 gates PASS, 6 Oracle gates resolved, stale `hermes run` refs eliminated | 5.8 |

**All 5 auditors must PASS. NEEDS REVIEW -> investigate + fix. FAIL -> block completion.**

---

## 17. Parent-Verification Checklist for This File

Before treating this planner as accepted:

- [ ] Parent has read this file fully (all 17 sections).
- [ ] Parent verified every per-step scaffold has concrete, checkable fields (Expected Files, Forbidden Patterns, Required Commands with expected outputs, Evidence Requirements, Hard Rejection Criteria).
- [ ] Parent confirmed no `hermes run --internal` references appear in any scaffold command.
- [ ] Parent confirmed Oracle action items are integrated as pre-go-live gates.
- [ ] Parent confirmed 5-auditor matrix (not 3).
- [ ] Parent confirmed MEDIUM risk level designation.
- [ ] Parent confirmed Redis DB5 seeding is Step 5.4 prerequisite.
- [ ] Parent confirmed KEEP VERBATIM files protected in all scaffolds.
- [ ] Parent confirmed midnight isolation enforced via `--deliver local`, not non-existent `--internal-only`.
- [ ] Parent confirmed collision scan includes 5.7 -> 5.4 sequence dependency.
- [ ] Parent has run markdown lint on this file (if available).
- [ ] Parent has synced active todos to match the dependency map.

---

## 18. Caveats and Blockers

| # | Caveat | Detail | Workaround |
|---|---|---|---|
| C-01 | PersonaPlugin deployment requires Hermes restart | Plugin registered locally; VPS activation needs controlled restart (5 min downtime) | Schedule during low-activity window. Hardstop fallback remains active during restart. |
| C-02 | GitHub SSH key broken on VPS | Cannot push from VPS. Commit locally; push may need Faiz assistance. | Stage all changes, create patch if needed. |
| C-03 | `hermes run --internal` does not exist | v1.0 planner references this extensively. All v1.0 scaffolds are stale by default. | This v1.1 planner uses only `hermes cron create` and `hermes chat -Q -q`. |
| C-04 | Crontab.yaml is NOT loaded by Hermes cron | Jobs defined there are not executing. File exists but is not referenced. | Use `hermes cron create` exclusively. Keep crontab.yaml as reference only. |
| C-05 | Redis DB5 key convention conflict | `guinevere_safety` uses 11 keys (canonical), `persona_plugin` uses 6 different keys. | Reconcile to `guinevere_safety` convention. Update `persona_plugin.py`. |
| C-06 | ADR-035 risk level incorrectly LOW | Phase 5 touches punishment FSM boundaries (L6) and safety-critical refactors. | Update to MEDIUM during Step 5.8. |
| C-07 | Security incident (Redis credential) | Exposed in transcript. Repo artifacts clean. Faiz accepted risk. | Document in evidence. Do not rotate unless Faiz requests. |

---

## 19. Execution Checklist

- [ ] Parent read this planner gate file fully.
- [ ] Parent verified every scaffold field is concrete and checkable.
- [ ] Todos synced to planner wave order.
- [ ] Collision scan confirmed before implementation.
- [ ] One implementation sub-agent per step (max 3 parallel in Wave 1).
- [ ] Each delegation includes the relevant scaffold verbatim.
- [ ] Parent verifies claimed files and re-runs scaffold commands (does NOT accept self-report).
- [ ] Per-step verification files created ONLY after implementation passes.
- [ ] **No `hermes run --internal` references in any delegation or verification.**
- [ ] Redis DB5 seed command executed securely (no password in evidence).
- [ ] Independent auditor wave (5 auditors) run after parent verification per step.
- [ ] All valid auditor findings fixed and re-audited via `task_id` continuation.
- [ ] 18 user gates (G-1 to G-18) verified PASS.
- [ ] 6 Oracle deployment gates (OG-1 to OG-6) verified PASS/ACCEPTED.
- [ ] 5 auditors all PASS.
- [ ] Deployment/restart/commit/push performed only after all gates + auditors PASS.
- [ ] ADR-035 risk level updated to MEDIUM.
- [ ] Git commit via git-master workflow: style detection, file count analysis, atomic theme grouping (not predetermined commit count).
- [ ] PROGRESS.md updated with Phase 5 completion and evidence path.
- [ ] Final report includes changed files, verification results, evidence paths, auditor verdicts, caveats, and next action.

---

## 20. Footer

This planner gate v1.1 supersedes stale parts of `planner-gate-phase-5-execution.md` v1.0. It corrects 9 stale assumptions (SOUL.md line count, greenfield skills, greenfield PersonaPlugin, passive cron, non-existent `hermes run` command, empty Redis DB5, 3 vs 5 auditors, LOW risk level, Y4 definition mismatch) using 7 current execution research reports and the Oracle safety review. It adds 6 Oracle action items as pre-go-live deployment gates and requires 5 independent auditors.

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.1 | 2026-06-06 | Guinevere (Parent Orchestrator) | Corrected stale assumptions from v1.0: SOUL.md 463 lines (not 278), skills exist (not greenfield), PersonaPlugin exists (not new), cron uses `hermes cron create` (not passive), `hermes run` forbidden, Redis DB5 must be seeded, 5 auditors (not 3), risk MEDIUM (not LOW), Oracle 6 action items as gates, Y4 reconciliation, corrected scaffolds. |
| 1.1a | 2026-06-06 | Guinevere (Parent Orchestrator) | Parent-verification fixes: Resolved drift_detector.py KEEP VERBATIM contradiction via narrow hash-only allowance (Option A); fixed invalid Step 5.8 timezone command; replaced destructive rollback commands with approval-gated labels + safe previews; replaced fixed 3-commit strategy with git-master compliant detection-based workflow; converted Step 5.1 prose forbidden patterns to concrete grep+regex checks. |
| 1.0 | 2026-06-05 | Guinevere | Initial planner gate file (now stale — preserved for reference only). |

**Planner version:** 1.1a
**Date:** 2026-06-06
**Author:** Guinevere (Parent Orchestrator)
**Status:** PENDING PARENT VERIFICATION (v1.1a) — Parent-verification fixes applied. Re-verify this file before proceeding.
