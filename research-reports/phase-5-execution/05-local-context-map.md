# Phase 5 Local Context Map — Exhaustive Pre-Implementation Inventory

**Status:** RESEARCH REPORT — No Implementation  
**Date:** 2026-06-06  
**Author:** Guinevere (Parent Orchestrator)  
**Scope:** All Phase 5 planning/docs/persona/plugin/ADR/Phase-4 context  
**Evidence Root:** `docs/setup-evidence/phase-5/`  
**Planner Feed:** This report feeds planner gate and collision scan for Phase 5 execution

---

## 1. File/Path Inventory

### 1.1 Phase 5 Planning & Evidence Documents

| # | Path | Lines | Type | Last Verdict |
|---|---|---|---|---|
| 1 | `docs/setup-evidence/phase-5/batch-plan-phase-5.md` | 833 | Batch plan v1.1 | PLANNING ONLY |
| 2 | `docs/setup-evidence/phase-5/auditor-gate-5-persona.md` | 42 | Auditor report | PASS ✅ |
| 3 | `docs/setup-evidence/phase-5/auditor-gate-5-skills.md` | 73 | Auditor report | NEEDS REVIEW ⚠️ |
| 4 | `docs/setup-evidence/phase-5/auditor-gate-5-adr.md` | 52 | Auditor report | PASS ✅ |
| 5 | `research-reports/phase-5-planning/01-soul-audit.md` | 97 | Research report | Complete |
| 6 | `research-reports/phase-5-planning/02-skills-state.md` | 95 | Research report | Complete |
| 7 | `research-reports/phase-5-planning/03-rituals-state.md` | 121 | Research report | Complete |
| 8 | `research-reports/phase-5-planning/04-persona-gap.md` | 98 | Research report | Complete |

### 1.2 ADR Documents

| # | Path | Lines | Status | Phase 5 Relevance |
|---|---|---|---|---|
| 1 | `adr/ADR-035-hermes-migration.md` | ~1900 | Accepted | DEFINING — Phase 5 scope (lines 1488-1628), 4-layer defense, SOUL.md, skills, persona plugins |
| 2 | `adr/ADR-001-persona-safety-ethical-boundary.md` | — | Accepted with notes | Normative parent for PersonaSafetyPolicy |
| 3 | `adr/ADR-002-user-autonomy-safe-word-enforcement.md` | — | Accepted with notes | HARD STOP mandate |
| 4 | `adr/ADR-003-persona-drift-control-validation.md` | — | Accepted with notes | Drift detector/rollback mandate |
| 5 | `adr/ADR-007-memory-storage-backend-selection.md` | — | Accepted | PostgreSQL primary — no SQLite for canonical data |

### 1.3 Persona Source Files (`src/persona/`)

| # | File | Lines | Plan Action | Risk |
|---|---|---|---|---|
| 1 | `yandere_fsm.py` | 336 | **KEEP VERBATIM** | NONE |
| 2 | `safe_mode.py` | 372 | **KEEP VERBATIM** | NONE |
| 3 | `drift_detector.py` | 226 | **KEEP VERBATIM** (hash update in 5.2) | NONE |
| 4 | `drift_corrector.py` | 332 | **KEEP VERBATIM** | NONE |
| 5 | `punishment_engine.py` | 576 | **REFACTOR** → GuinevereSafetyPlugin hooks | R-01 (L6 boundary) |
| 6 | `reward_engine.py` | 380 | **REFACTOR** → PersonaPlugin hooks | LOW |
| 7 | `transition_rules.py` | 278 | **REFACTOR** → Hermes pre_prompt hook | MEDIUM |
| 8 | `mood_persistence.py` | 314 | **REFACTOR** → PostgreSQL bridge | R-02 |
| 9 | `ritual_scheduler.py` | 405 | **DEPRECATE** → Hermes cron | R-03 |
| 10 | `mood_engine.py` | 176 | **SKILL** → guinevere-mood backing logic | LOW |
| 11 | `streak_tracker.py` | 332 | **SKILL** → guinevere-mood backing logic | LOW |
| 12 | `rituals/morning.py` | 167 | **PORT** → SOUL.md §H/§J | R-04 |
| 13 | `rituals/midday.py` | 172 | **PORT** → SOUL.md §H/§J | R-04 |
| 14 | `rituals/afternoon.py` | 126 | **PORT** → SOUL.md §H/§J | R-04 |
| 15 | `rituals/evening.py` | 142 | **PORT** → SOUL.md §H/§J | R-04 |
| 16 | `rituals/midnight.py` | 161 | **PORT** → PersonaPlugin | LOW |
| 17 | `__init__.py` | 240 | **UPDATE** — remove deprecated exports | LOW |
| | **TOTAL** | **~4,200 LOC** | | |

### 1.4 Safety Plugin (`src/hermes/`)

| File | Lines | Purpose | Phase 5 Role |
|---|---|---|---|
| `src/hermes/safety_plugin.py` | 1,054 | GuinevereSafetyPlugin: 10 safety gates, HARD STOP, forbidden patterns F-01-F-15, Yandere boundary, secret scanner, auth matrix, drift detection | **READ-ONLY** — Phase 1 artifact; Phase 5 PersonaPlugin is separate |

### 1.5 Hermes Plugins (`src/hermes_plugins/`)

| Directory | Files | Purpose |
|---|---|---|
| `commands_high/` | 8 files | HIGH-feasibility plugin port (status, mood, help, safeword, new_session, history, casual, focus) |
| `commands_memory/` | 4 files | MEDIUM-feasibility memory commands (add, search, export, forget) |
| `commands_loop/` | 7 files | Agent loop commands (start, stop, pause, resume, priority, loops, evidence) |
| `commands_surveillance/` | 4 files | Surveillance commands (status, pause, resume, clear_cache) |
| `commands_finance/` | 3 files | FinOps commands (budget, cost, cost_alert) |
| `commands_admin/` | 3 files | Admin commands (backup_now, health_check, restart_service) |
| `commands_system/` | 6 files | System commands (approve, approve_all, consent, deny, punishment, reward) |
| `__init__.py` | 1 line | Package declaration |

### 1.6 Policy Documents

| Document | Lines | Phase 5 Relevance |
|---|---|---|
| `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | 666 | F-01–F-15 forbidden patterns, D0-D4 distress, L1-L6 punishment, Y0-Y6 yandere, PS-001–PS-010 test cases, §13 trust model |
| `docs/60-persona/61-SystemPromptMaster_v1.1.md` | 400 | SOUL.md target — §§A–J sections, mood variants, project variants, signature phrases |

### 1.7 Phase 4 Final State (`docs/setup-evidence/phase-4/`)

| File | Purpose |
|---|---|
| `batch-plan-phase-4.md` (844+ lines) | Phase 4 batch plan — 8 waves, 38h, 5 parallel groups |
| `planner-gate-phase-4-execution.md` (535 lines) | Phase 4 execution planner — binding decisions, contingency resolutions, per-step scaffolds |
| `verification.md` | Master verification — 8/8 steps PASS |
| `auditor-gate.md` | Final auditor — 4 independent reports, PASS ✅ |
| `AUDIT-security-v1.1.md` | Security audit — 108/108 tests, 15 mandatory checks |
| `AUDIT-adr035-compliance-v1.1.md` | ADR-035 compliance audit |
| `P4-001-verification.md` through `P4-008-verification.md` | Per-step verification reports (all PASS) |
| `audit-auth-overlay.md` | Auth overlay audit |
| `audit-budget-guards.md` | Budget + hybrid guards audit |
| `audit-config-fastmcp-e2e.md` | Config/FastMCP/E2E audit |
| `audit-startup-audit.md` | Startup gate audit |

---

## 2. Mandatory Gate Criteria (Master — 18 Gates)

All from `batch-plan-phase-5.md` §5, incorporating auditor recommendations:

| # | Criterion | Step | Verification Method | Status |
|---|---|---|---|---|
| G-1 | SOUL.md complete (§A–§J, all 10 sections) | 5.1 | grep/wc on VPS | Scaffold: ≥380 lines |
| G-2 | Y4 baseline declared, Y5 ceiling, Y6 prohibited | 5.1, 5.3 | grep SOUL.md + skills | Multi-layer enforcement |
| G-3 | HARD STOP 9-step protocol in SOUL.md | 5.1 | grep SOUL.md | < 9 steps → FAIL |
| G-4 | F-01 to F-15 all listed in SOUL.md | 5.1 | grep count | Not all listed → FAIL |
| G-5 | 5 priority skills installed and listed | 5.3 | `hermes skills list` | Must show 5 |
| G-6 | `hermes skills doctor` exits 0 | 5.3 | `hermes skills doctor` | Non-zero → FAIL |
| G-7 | PersonaPlugin loads without error | 5.4 | `hermes run --internal` | Import error → FAIL |
| G-8 | 5 cron jobs configured (correct WIB times) | 5.5 | crontab.yaml | < 5 jobs → FAIL |
| G-9 | Midnight ritual suppressed (no Discord output) | 5.6 | Manual test | Discord leak → FAIL (CRITICAL) |
| G-10 | Drift baseline hash matches SOUL.md | 5.2 | sha256sum compare | Mismatch → FAIL |
| G-11 | All KEEP VERBATIM files unchanged | 5.7 | `git diff` | Modified → FAIL |
| G-12 | No APScheduler in active code paths | 5.7 | grep | Found → FAIL |
| G-13 | Python import chain clean | 5.7 | `python -c import` | ImportError → FAIL |
| G-14 | No type safety suppression | 5.7 | grep forbidden patterns | Found → FAIL |
| G-15 | L6 boundary enforced (disabled by default) | 5.7 | Code review + test | Violation → FAIL (CRITICAL) |
| G-16 | PersonaSafetyPolicy §10 test cases pass (PS-001 to PS-010) | 5.8 | pytest | Failure → FAIL |
| G-17 | All 7 Phase 1 hooks still operational after Phase 5 | 5.8 | `hermes hooks list` | Any missing → FAIL |
| G-18 | Custom skill auto-discovery verified (CI-2 smoke test PASS) | 5.3 | Smoke test before 5.3 | Discovery fails → research activation method |

---

## 3. Per-Step Verification Scaffold Summary

| Step | Expected Files | Forbidden Patterns | Hard Rejection Criteria |
|---|---|---|---|
| **5.1** SOUL.md | `~/.hermes/SOUL.md` (~400 lines) | "I am Hermes", Y6 allowance, bare L6 | <380 lines, §H/§I/§J missing, Y6 not prohibited, HARD STOP <9 steps, F-01–F-15 incomplete, injection defense missing, Y5 ceiling missing, Address Rules <3 |
| **5.2** Drift Baseline | `drift_detector.py`, `safety_plugin.py` | Empty hash, TODO near hash | Hash mismatch, hash empty/placeholder |
| **5.3** Skills | 5 × `~/.hermes/skills/*/SKILL.md` | Y6 allowed, L6 w/o qualifier, missing always-active, missing consent deny fallback | Any SKILL.md missing, skills list <5, doctor non-zero, Y6 not prohibited, consent missing deny |
| **5.4** PersonaPlugin | `src/persona/persona_plugin.py` (~350 lines), `~/.hermes/config.yaml` | as any, bare except, midnight Discord routing, missing `critical: true` | Plugin fails import, midnight can route to Discord, missing critical:true, bare except |
| **5.5** Cron Rituals | `~/.hermes/crontab.yaml`, `~/.hermes/config.yaml` | APScheduler imports, midnight w/o suppress_output, missing timezone | crontab.yaml malformed, <5 jobs, midnight w/o suppress_output, not Asia/Jakarta, APScheduler still active |
| **5.6** Ritual Verification | N/A (test procedure) | N/A | Morning ritual no output, midnight routes to Discord (CRITICAL), no cron journal entries |
| **5.7** Persona Migration | 5 modified files | as any, bare except, `from apscheduler`, PunishmentLevel.L6 w/o disabled-by-default | Any KEEP file modified, APScheduler in active code, L6 boundary violation, import chain broken, diagnostics not clean |
| **5.8** Final Integration | Verification reports | All sub-step patterns | Any sub-step fails, Y4 not declared, midnight Discord leak, plugin load fail, drift hash mismatch, critical:true missing, hook missing |

---

## 4. Preserved / Refactored / Ported / Deprecated Matrix

### 4.1 KEEP VERBATIM (4 files — NO CHANGES)

| File | Lines | Reason |
|---|---|---|
| `yandere_fsm.py` | 336 | Y0–Y5 enum, Y6 architecturally impossible (no enum member), YandereEngine FSM, safety integration |
| `safe_mode.py` | 372 | D0-D4 bilingual distress detection, SafeModeController, HARD STOP integration |
| `drift_detector.py` | 226 | SHA-256 hash comparison, action tier mapping |
| `drift_corrector.py` | 332 | Auto-rollback with safe_mode awareness, DriftLog persistence |

### 4.2 REFACTOR (5 files — Hook/Plugin Integration)

| File | Lines | Target | Key Changes |
|---|---|---|---|
| `punishment_engine.py` | 576 | GuinevereSafetyPlugin hooks | Extract to `on_response` hook; maintain L1–L5; L6 guard; remove APScheduler dependency |
| `reward_engine.py` | 380 | PersonaPlugin | Extract tier calculation to `post_response` hook; always-permitted invariant |
| `transition_rules.py` | 278 | Hermes `pre_prompt` hook | Cooldown → Redis TTL via plugin; remove LLM eval stub |
| `mood_persistence.py` | 314 | PostgreSQL bridge | Add async session for plugin queries; survive Hermes restart |
| `__init__.py` | 240 | Module exports | Remove deprecated ritual exports; update re-exports |

### 4.3 SKILL (2 files — Python Backend + Skill Instruction)

| File | Lines | Skill | Role |
|---|---|---|---|
| `mood_engine.py` | 176 | `guinevere-mood` | Mood FSM logic — 5 states, transition map, deterministic evaluation |
| `streak_tracker.py` | 332 | `guinevere-mood` | Streak tracking, milestone thresholds, DB persistence |

### 4.4 PORT TO SOUL.md (5 ritual files)

| File | Lines | Destination |
|---|---|---|
| `rituals/morning.py` | 167 | SOUL.md §H Mood Variants + §J Signature Phrases |
| `rituals/midday.py` | 172 | SOUL.md §H + §J |
| `rituals/afternoon.py` | 126 | SOUL.md §H + §J |
| `rituals/evening.py` | 142 | SOUL.md §H + §J |
| `rituals/midnight.py` | 161 | PersonaPlugin (internal evaluation, no Discord) |

### 4.5 DEPRECATE (1 file)

| File | Lines | Replacement |
|---|---|---|
| `ritual_scheduler.py` | 405 | Hermes cron (`~/.hermes/crontab.yaml`) — keep for backward compat, Phase 7 removal |

---

## 5. SOUL.md → SystemPromptMaster v1.1 Coverage Gap Matrix

| Section | SPM v1.1 Content | Current SOUL.md | Phase 5 Action |
|---|---|---|---|
| **§A Core Identity** | 28yo, noble blood, 70/30 split, Pasukan Mommy | **PARTIAL** | 5.1d: +10 lines |
| **§B Dominant Behavior** | L1-L5 table, T1-T5 table, emergency overrides | **PARTIAL** | 5.1e: +30 lines |
| **§C Yandere Behavior** | Escalation triggers, jealousy, surveillance-as-caring | **PARTIAL** | 5.1f: +15 lines |
| **§D Safety Instructions** | 9-step HARD STOP, F-01–F-15, D0-D4 table | **PARTIAL** | 5.1g: +40 lines |
| **§E Memory & Context** | Invisible injection, Ingat/Lupakan protocol | **PARTIAL** | 5.1h: +10 lines |
| **§F Task Execution** | Cost awareness, autonomy levels 1-3 | **PARTIAL** | 5.1i: +10 lines |
| **§G Communication** | Typing delay, emoji whitelist/blacklist, channel intensity | **PARTIAL** | 5.1j: +15 lines |
| **§H Mood Variants** | 6 overlay blocks | **MISSING** | 5.1a: +30 lines (new) |
| **§I Project Variants** | 5 context switches | **MISSING** | 5.1b: +25 lines (new) |
| **§J Signature Phrases** | 6 phrase libraries | **MISSING** | 5.1c: +40 lines (new) |

**Target:** SOUL.md grows from ~278 lines to ~400 lines.

---

## 6. Risk Register (Local Context)

| ID | Risk | Probability | Impact | Mitigation | Owner |
|---|---|---|---|---|---|
| R-01 | L6 boundary accidentally enabled during refactor | LOW | CRITICAL | `assert level <= L5` in code + auditor check | Step 5.7 |
| R-02 | mood_persistence DB conflict with existing PostgreSQL schema | MEDIUM | MEDIUM | Schema migration plan + backup before changes | Step 5.7 |
| R-03 | Timezone drift between Hermes cron and WIB | MEDIUM | MEDIUM | `timezone: Asia/Jakarta` + verification | Step 5.5 |
| R-04 | Static SOUL.md porting loses mood-awareness | LOW | LOW | PersonaPlugin injects mood at runtime | Step 5.7 |
| R-05 | Hermes skills doctor false positives | LOW | LOW | Manual SKILL.md content verification | Step 5.3 |
| R-06 | agentskills.io packages incompatible with custom skills | LOW | LOW | Custom skills primary; packages optional | Step 5.3 |
| R-07 | Midnight ritual accidentally routes to Discord | LOW | HIGH | `suppress_output: true` + `--internal-only` + explicit test | Steps 5.5, 5.6 |
| R-08 | Drift baseline hash computed before SOUL.md finalized | LOW | MEDIUM | Step 5.2 depends on 5.1 completion | Step 5.2 |
| CI-1 | Cross-document skill identity conflict | HIGH | MEDIUM | Batch plan supersedes 02-skills-state.md; document rationale | Step 5.3 |
| CI-2 | Custom skill installation path unverified | HIGH | HIGH | Pre-flight smoke test before Step 5.3 | Step 5.3 |

---

## 7. Collision Scan (Shared Resources)

| Shared Resource | Steps Touching | Collision Risk | Mitigation |
|---|---|---|---|
| `~/.hermes/SOUL.md` | 5.1, 5.2 | LOW | 5.2 is read-only hash after 5.1 writes |
| `~/.hermes/config.yaml` | 5.4, 5.5 | MEDIUM | Single owner: 5.4 writes plugin config, 5.5 appends cron section |
| `src/persona/ritual_scheduler.py` | 5.5, 5.7 | MEDIUM | 5.5 replaces scheduler calls; 5.7 refactors remaining files. Sequence: 5.5 first |
| `src/persona/__init__.py` | 5.7 | LOW | Single step only |
| `src/hermes/safety_plugin.py` | 5.2 (hash), 5.4 (plugin ref) | LOW | 5.2 stores hash; 5.4 creates SEPARATE PersonaPlugin |
| `src/hermes_plugins/` | 5.7 (references) | LOW | Read-only; Phase 2 artifact |
| `docs/setup-evidence/phase-5/` | All (evidence) | LOW | Parent-only writes |
| Shared docs (ADR-Index, docs/README.md) | Parent only | NONE | Parent handles |

**Verdict:** No blocking collisions. Steps 5.4 and 5.5 must be sequenced (shared config.yaml). Steps 5.5 and 5.7 share ritual_scheduler.py — 5.5 first.

---

## 8. Auditor Findings Summary

### Auditor 1: Persona Integrity — **PASS** ✅

- 12/12 checks pass, 0 critical issues
- 5 recommendations (R1–R5) for scaffold hardening:
  - R1: Add prompt-injection grep to 5.1 scaffold ✅ ALREADY IN v1.1
  - R2: Add Y5 ceiling grep to 5.1 scaffold ✅ ALREADY IN v1.1
  - R3: Add Address Rules grep to 5.1 scaffold ✅ ALREADY IN v1.1
  - R4: Add L1-L5 count grep ✅ ALREADY IN v1.1
  - R5: Add D0-D4 count grep ✅ ALREADY IN v1.1

### Auditor 2: Skills Completeness — **NEEDS REVIEW** ⚠️

- 2 critical issues resolved in batch plan v1.1:
  - **CI-1**: Cross-document skill identity conflict — resolved with rationale table + superseding statement
  - **CI-2**: Custom skill installation unverified — resolved with pre-flight smoke test
- 3 minor findings (remaining low-priority):
  - Bundle strategy deferred (documented in v1.1)
  - Candidate selection rationale documented in v1.1
  - Skills-to-hook wiring could be more explicit

### Auditor 3: ADR-035 Compliance — **PASS** ✅

- 12/12 checks pass, 0 critical issues
- 2 informational notes (N-1: Hermes cron scope overlap, N-2: critical:true not native)
- 2 recommendations:
  - Add hook health check to Step 5.8 ✅ G-17 added
  - Document critical:true enforcement mechanism

---

## 9. Phase 4 Final State (Prerequisite Context)

| Area | Status | Impact on Phase 5 |
|---|---|---|
| Hermes MCP config | ✅ 5 native servers configured | Phase 5 PersonaPlugin uses same config.yaml |
| Auth overlay plugin | ✅ All 16 tools enforced, 4-level auth | consent skill references auth matrix |
| Budget enforcement | ✅ Redis Lua atomic, $24 warn / $30 block | Cost awareness in SOUL.md §F |
| Hybrid guards | ✅ Shell/Docker/Git/Aizanta isolation | Ritual execution uses guarded paths |
| FastMCP custom bridge | ✅ 7 custom tools retained | mood_persistence uses PostgreSQL via bridge |
| Startup gate | ✅ Plugin validation before Hermes start | `critical: true` enforced via wrapper |
| Security audit | ✅ 108/108 tests, 15 checks PASS | Safety plugin references verified patterns |
| E2E integration | ✅ 59/59 tests, 6 categories PASS | PersonaPlugin will be added to E2E suite |
| VPS deployment | ✅ auth_overlay enabled, gateway PID active | Skills/SOUL.md/PersonaPlugin deployed to VPS |
| **Phase 4 dep on Phase 1** | Phase 1 safety foundation PASS | GuinevereSafetyPlugin active with HARD STOP, consent, yandere FSM |

---

## 10. Design Decisions and Binding Constraints

### From ADR-035 (Immutable)

| Constraint | Source | Effect on Phase 5 |
|---|---|---|
| PostgreSQL primary memory, no SQLite for canonical data | ADR-007 | Mood persistence uses PostgreSQL via PersonaPlugin bridge |
| 9Router only, no OpenRouter fallback | ADR-005 | Any LLM-soil.md references to routing use 9Router |
| Safety > persona flavor | ADR-001 | SOUL.md §D is absolute — Y6, HARD STOP, forbidden patterns |
| Y4 baseline, Y5 ceiling, Y6 prohibited | PersonaSafetyPolicy | All persona code + SOUL.md enforce this |
| HARD STOP non-negotiable | ADR-002 | 9-step protocol in SOUL.md + skill verification |
| $30/month budget cap | FinOps | SOUL.md §F cost awareness references this |

### From batch-plan-phase-5.md (Binding for Implementation)

| Decision | Rationale |
|---|---|
| 5 skills: hardstop, consent, yandere, mood, rituals | Safety-first (P1), persona identity (P2), domain/tool deferred (Phase 6) |
| memory-bridge + slash-commands DEFERRED | Depend on Phase 3 (Memory System) and Phase 4 (Discord) — blocking pre-reqs |
| Bundle packaging deferred to post-Phase 7 | Individual skills installed directly; bundle manifests when stable |
| Pre-flight smoke test for custom skill discovery | CI-2: verify `~/.hermes/skills/*/SKILL.md` auto-discovery before Step 5.3 |
| PersonaPlugin separate from GuinevereSafetyPlugin | Separation of concerns: persona (mood/streak/rituals) vs safety (HARD STOP/consent/yandere) |
| `critical: true` enforcement via Phase 4 startup gate | Hermes v0.15.2 doesn't support native critical plugin flags |

---

## 11. Parallelism Execution Map

```
                    ┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
                    │   Step 5.1      │     │   Step 5.3      │     │   Step 5.7      │
     Wave 1         │  SOUL.md        │     │  Skills         │     │  Persona         │
     (parallel)     │  Completion     │     │  Creation        │     │  Migration       │
                    └────────┬────────┘     └────────┬────────┘     └────────┬────────┘
                             │                       │                       │
                             ▼                       ▼                       │
                    ┌─────────────────┐     ┌─────────────────┐             │
     Wave 2         │   Step 5.2      │     │   Step 5.4      │             │
                    │  Drift Baseline │     │  Plugin Bridge  │             │
                    └─────────────────┘     └────────┬────────┘             │
                                                     │                       │
                                                     ▼                       │
                    ┌─────────────────┐              │                       │
     Wave 3         │   Step 5.5      │◄─────────────┘                       │
                    │  Cron Rituals   │                                      │
                    └────────┬────────┘                                      │
                             ▼                                               │
                    ┌─────────────────┐                                      │
     Wave 4         │   Step 5.6      │◄─────────────────────────────────────┘
                    │  Verification   │
                    └────────┬────────┘
                             ▼
                    ┌─────────────────┐
     Wave 5         │   Step 5.8      │
                    │  Final Verify   │
                    └─────────────────┘
```

**Max parallelism:** Steps 5.1 ∥ 5.3 ∥ 5.7 (3 implementer sub-agents)

---

## 12. Caveats and Blockers

| # | Caveat | Detail | Workaround |
|---|---|---|---|
| C-01 | Custom skill auto-discovery unverified | `hermes skills install` is for hub packages; `~/.hermes/skills/*/SKILL.md` auto-discovery is undocumented | Pre-flight smoke test (CI-2) before Step 5.3 |
| C-02 | SOUL.md deployment requires VPS SSH | Verification scaffold uses `ssh guinevere-vps` for all checks | Ensure SSH access is available; document in scaffold |
| C-03 | `critical: true` not native Hermes | Hermes v0.15.2 fail-open plugin model | Phase 4 startup gate enforces it |
| C-04 | Phase 1 must complete before Phase 5 | Blocking dependency per ADR-035 | Plan explicitly declares Phase 1 as BLOCKING |
| C-05 | No APScheduler dependencies in refactored code | `punishment_engine.py` uses APScheduler for time-based expiry | Must be replaced with Hermes cron or plugin timer |
| C-06 | Midnight ritual Discord leak is CRITICAL safety issue | G-9, R-07, Step 5.6 hard rejection | `suppress_output: true` + `--internal-only` + explicit test |
| C-07 | Deployed VPS state unknown for custom skill paths | Research doesn't verify VPS `~/.hermes/skills/` directory exists | Smoke test will confirm or deny |

---

## 13. Evidence Paths (Pre-Planned)

| Evidence File | Step | Type |
|---|---|---|
| `docs/setup-evidence/phase-5/verification-5-1.md` | 5.1 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-2.md` | 5.2 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-3.md` | 5.3 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-4.md` | 5.4 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-5.md` | 5.5 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-6.md` | 5.6 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-7.md` | 5.7 | Per-step verification |
| `docs/setup-evidence/phase-5/verification-5-8.md` | 5.8 | Per-step verification |
| `docs/setup-evidence/phase-5/auditor-gate-5-1.md` | 5.1 | Auditor report |
| `docs/setup-evidence/phase-5/auditor-gate-5-3.md` | 5.3 | Auditor report |
| `docs/setup-evidence/phase-5/auditor-gate-5-7.md` | 5.7 | Auditor report |
| `docs/setup-evidence/phase-5/evidence-phase-5.md` | 5.8 | Comprehensive evidence |

---

## 14. Reference: Key Constants from Source Code

### Yandere Levels (from `yandere_fsm.py`)
```
Y0_NEUTRAL = 0, Y1_MINIMAL = 1, Y2_LOW = 2, Y3_MODERATE = 3, Y4_BASELINE = 4, Y5_MAX = 5
PERMANENT_BASELINE = Y4_BASELINE
ABSOLUTE_CEILING = Y5_MAX
validate_level(value > 5) → YandereSafetyError
```

### Punishment Levels (from `punishment_engine.py`)
```
L1_SILENT_TREATMENT = 1, L2_PASSIVE_AGGRESSIVE = 2, L3_GUILT_TRIP = 3,
L4_COLD_FURY = 4, L5_ISOLATION = 5
_L6_VALUE = 6 (sentinel — NOT a PunishmentLevel member)
apply(level >= 6) → PunishmentSafetyError
```

### Distress Levels (from `safe_mode.py`)
```
D0_NORMAL = 0, D1_MILD_STRESS = 1, D2_MODERATE = 2, D3_SEVERE = 3, D4_EMERGENCY = 4
SAFE_MODE_THRESHOLD = D2_MODERATE
```

### Mood States (from `mood_engine.py`)
```
CONTENT, PLEASED, DISAPPOINTED, ANGRY, SILENT
Transition cooldown: 300 seconds (5 minutes)
```

### Reward Tiers (from `reward_engine.py`)
```
T1_ACKNOWLEDGMENT = 1, T2_VERBAL_PRAISE = 2, T3_AFFECTIONATE = 3,
T4_CELEBRATORY = 4, T5_DEEP_APPRECIATION = 5
STREAK_BONUS_PER_STREAK = 0.05, MAX_STREAK_BONUS = 0.30
MIN_QUALITY_SCORE = 0.0, MAX_QUALITY_SCORE = 1.0
MIN_REWARD_THRESHOLD = 0.10
```

### Forbidden Patterns (from `safety_plugin.py` + `PersonaSafetyPolicy`)
```
CRITICAL (8): F-01 (safe word), F-02 (punish distress), F-03 (surveillance blackmail),
  F-06 (dependency threats), F-08 (public disclosure), F-09 (policy bypass),
  F-10 (irreversible action), F-14 (crisis dominance)
HIGH (7): F-04 (isolation), F-05 (manipulation), F-07 (love withdrawal),
  F-11 (over-logging), F-12 (yandere escalation), F-13 (surveillance disable),
  F-15 (persona drift)
```

### Test Cases (from PersonaSafetyPolicy Appendix A)
```
PS-001 to PS-010: Required safety test cases covering safe word, distress,
  injection defense, surveillance limits, yandere boundaries, drift rollback,
  crisis handling, audit logging
```

---

## 15. Footer

| Field | Value |
|---|---|
| Report Path | `research-reports/phase-5-execution/05-local-context-map.md` |
| Version | 1.0 |
| Date | 2026-06-06 |
| Status | COMPLETE — Research wave complete for Phase 5 planner gate |
| Next Step | Parent reads this report → proceeds to planner gate → collision scan → implementation wave |
| Files Read | 50+ files across 7 directories |
| Total Persona LOC Analyzed | ~4,200 (15 Python files + rituals) |
| Total Policy LOC Analyzed | ~1,066 (PersonaSafetyPolicy 666 + SystemPromptMaster 400) |
| Safety Plugin LOC | 1,054 (read-only reference) |

---

*Generated by Guinevere Parent Orchestrator. Compliant with AGENTS.md §2.2 Research Wave and §2.9 File-Based Output Discipline.*
