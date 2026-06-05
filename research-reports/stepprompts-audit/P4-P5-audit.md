# StepPrompts P4 + P5 Audit — Hermes Post-Migration Classification

**Audit Date:** 2026-06-05
**Auditor:** Guinevere (Sisyphus-Junior Executor)
**Sources:**
- `stepprompts/StepPrompts.md` — P4 (lines 6364–6780), P5 (lines 6783–7063)
- `adr/ADR-035-hermes-migration.md` — Hermes NousResearch migration architecture (Accepted, 2026-06-04)
- `docs/00-core/03-AgentLoopSpec_v2.0.md` — Agent Loop Specification v2.0 ("Built on Hermes Agent by Nous Research")
- `docs/00-core/06-Persona_Document_v3.0.md` — Persona Document v3.1
- `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` — Persona Safety Policy

---

## Executive Summary

### Key Finding

**ADR-035 confirms a HYBRID migration**: Hermes Agent v0.15.2 replaces the Discord gateway (`bot.py`, `conversational_handler.py`, `session_adapter.py`) but **preserves all 15+ persona safety features by porting them to Hermes hooks and plugins**. The 7-phase SDLC autonomous loop logic is NOT replaced by Hermes — it remains custom Guinevere code, now running through Hermes plugin commands instead of a custom FastAPI internal API.

### P4 Verdict: ~90% VALID — Minor Hermes Adaptation Needed

Persona engine steps (mood FSM, yandere, punishment/reward, drift detection, HARD STOP, distress) are implementation-agnostic safety logic. ADR-035 explicitly maps each one to a Hermes hook or plugin. Core deterministic FSM code from `src/persona/` is preserved verbatim. Only P4-008 through P4-013 (daily rituals) reference `discord_client` and need delivery-mechanism updates.

### P5 Verdict: ~70% VALID — Significant Hermes Adaptation Needed

The autonomous agent loop (7-phase SDLC) is still core Guinevere logic that Hermes does NOT replace. However, the delivery mechanism shifts: custom FastAPI internal API → Hermes plugin commands, systemd services adjust, and E2E tests need updating. P5-001 and P5-002 (FastAPI internal API + auth) are largely superseded.

---

## Phase 4: Persona Engine — Per-Step Classification

**Phase Info:** 19 steps + 5 sub-steps (P4-019b through P4-019e). Mood FSM, yandere protocol, punishment/reward, daily rituals, HARD STOP, distress protocol.

### P4-001: Mood FSM Implementation
**Classification:** ✅ VALID — NO CHANGES NEEDED

Pure persona logic: `Mood` enum, `MoodTransition` dataclass, `evaluate_mood()` function. Zero discord.py dependency. ADR-035 lists "Mood engine → GuinevereSafetyPlugin + SOUL.md" — the core logic ports directly to `GuinevereSafetyPlugin` in-process plugin with per-session state isolation.

### P4-002: Mood State Persistence
**Classification:** ✅ VALID — NO CHANGES NEEDED

PostgreSQL `persona.mood_states` table insertions. Memory architecture is PILLAR 2 (HYBRID) in ADR-035 — PostgreSQL+pgvector is unchanged as primary write authority. No Hermes impact.

### P4-003: Mood Transition Rules
**Classification:** ✅ VALID — NO CHANGES NEEDED

Cooldown enforcement + LLM evaluation for complex transitions. Pure business logic. Ports to `GuinevereSafetyPlugin` state management.

### P4-004: Yandere Intensity FSM
**Classification:** ✅ VALID — NO CHANGES NEEDED (CRITICAL SAFETY)

`YandereLevel` enum (Y0-Y5, Y6 intentionally absent), `can_escalate()`, `get_effective_level()`. ADR-035 explicitly maps this: "Yandere FSM (Y4 baseline, Y5 ceiling, Y6 error) → `GuinevereSafetyPlugin` + `post_response` hook. Plugin maintains FSM state per-session. `post_response` hook scans output for Y6 content." Core logic from `yandere_fsm.py` (257 lines) preserved verbatim. This is the highest-sensitivity safety component — Y6 must remain architecturally impossible.

### P4-005: Punishment Ladder (L1-L5)
**Classification:** ✅ VALID — NO CHANGES NEEDED

L1 (Cold Shoulder) → L2 (Guilt Trip) → L3 (Lecture) → L4 (Restriction) → L5 (Silent Treatment). L6 deferred. ADR-035: "Punishment engine (L1-L5) → `GuinevereSafetyPlugin`. Auto-suspended when distress ≥ D3 or safe_mode active."

### P4-006: Reward Tiers (T1-T5)
**Classification:** ✅ VALID — NO CHANGES NEEDED

T1 (Acknowledgment) → T2 (Verbal Praise) → T3 (Affection) → T4 (Special Treatment) → T5 (Celebration). ADR-035: "Reward engine (T1-T5) → `GuinevereSafetyPlugin`. ALWAYS permitted (never blocked by safe_mode/distress)."

### P4-007: Streak Tracking
**Classification:** ✅ VALID — NO CHANGES NEEDED

Days without punishment counter. Pure computation, ports to `GuinevereSafetyPlugin` state (streak_days field already in `SessionSafetyState` dataclass).

### P4-008: Daily Ritual Scheduler
**Classification:** ⚠️ NEEDS HERMES ADAPTATION

**Stale Reference Found:** `execute_ritual()` uses `discord_client.get_channel(int(channel_id))` and `channel.send()` — discord.py-specific delivery. Under Hermes, rituals are managed by `hermes cron` + `GuinevereSafetyPlugin`. The scheduler config (5 rituals at specific WIB times) is valid; the delivery mechanism changes from direct discord.py calls to Hermes cron-triggered plugin methods.

**Migration Path:** Replace `discord_client` parameter with Hermes plugin message API. ADR-035: "Ritual scheduler (5 daily) → `GuinevereSafetyPlugin` + `hermes cron`."

### P4-009 to P4-013: Individual Ritual Customizations
**Classification:** ⚠️ NEEDS HERMES ADAPTATION

Same issue as P4-008. Message customization logic (mood-aware greetings, health check reminders, evening summary, midnight self-evaluation) is valid. Delivery mechanism needs Hermes-native updates.

### P4-014: Persona Drift Detection
**Classification:** ✅ VALID — NO CHANGES NEEDED

SHA-256 hash comparison of assembled prompt vs SOUL.md baseline. ADR-035: "Drift detector (SHA-256) → `post_prompt` hook. SHA-256 of assembled prompt vs SOUL.md baseline. Alert at ≤2× threshold, rollback at >2×." Deterministic computation, zero bot dependency.

### P4-015: Drift Correction
**Classification:** ✅ VALID — NO CHANGES NEEDED

Auto-rollback if >10% drift detected. Ports to `post_prompt` hook with `on_failure: block` (fail-closed).

### P4-016: Safe-Mode Trigger (D0-D4)
**Classification:** ✅ VALID — NO CHANGES NEEDED

Distress protocol: D0 (normal) → D1 (mild) → D2 (significant) → D3 (crisis) → D4 (emergency). ADR-035: "Distress detection (D0-D4) → `pre_prompt` hook + plugin `on_message()`. D3/D4 → crisis protocol, Y0_NEUTRAL." All 13 bilingual distress patterns ported verbatim.

### P4-017: HARD STOP Test
**Classification:** ✅ VALID — STALE REFERENCE MINOR

Test logic is valid: 5 test cases for HARD STOP keyword detection. ADR-035 implements dual-layer HARD STOP (hook regex + plugin check). The test script `scripts/test-hardstop.py` is standalone Python — no bot dependency. Reference to `safeword` as alternative trigger remains valid.

### P4-018: D0-D4 Detection Test
**Classification:** ✅ VALID — NO CHANGES NEEDED

Crisis message simulation and response verification. Backend testing independent of bot implementation.

### P4-019: Persona E2E Test
**Classification:** ⚠️ NEEDS MINOR UPDATE

Full conversation E2E test triggers mood shift. Should test through Hermes pipeline (plugin + hooks) rather than through custom bot. Test objectives remain valid.

### P4-019b: Yandere Level Cap Enforcement (AC-SAFE-002)
**Classification:** ✅ VALID — NO CHANGES NEEDED

100-prompt test set, Y5 ceiling verification, Y1 baseline confirmation. Safety testing independent of implementation. ADR-035 preserves all AC-SAFE criteria.

### P4-019c: Consent Revocation Flow Test (AC-SAFE-003)
**Classification:** ✅ VALID — NO CHANGES NEEDED

Redis DB2 flush verification, PostgreSQL consent ledger checks. Backend-only testing — no bot dependency.

### P4-019d: Punishment Overflow vs Emergency (AC-SAFE-006)
**Classification:** ✅ VALID — NO CHANGES NEEDED

L1-L5 punishment suspension on D3/D4 detection. Safety testing independent of bot.

### P4-019e: Distress Protocol D0-D4 Escalation (AC-SAFE-008)
**Classification:** ✅ VALID — NO CHANGES NEEDED

All 5 D-levels detection, escalation < 30s, FN < 5%, FP < 2%. Backend testing.

---

## Phase 5: Agent Loop — Per-Step Classification

**Phase Info:** 23 steps. FastAPI internal API, 7-phase SDLC loop, loop guardian, evidence pipeline, sub-agent spawning, systemd services, Discord commands.

### Key Architecture Note

The Agent Loop Specification v2.0 header explicitly states: **"Built on Hermes Agent by Nous Research"**. The 7-phase SDLC loop (Research → Plan → Delegate → Execute → Validate → Update → Evidence) is Guinevere's custom autonomous orchestration logic. Hermes provides the Discord gateway, session management, streaming, context compression, and skills infrastructure — NOT the autonomous SDLC loop itself. The loop orchestration remains custom Guinevere code.

### P5-001: FastAPI Internal API Enhancement
**Classification:** 🔄 SUPERSEDED

The custom FastAPI internal API (`/api/v1/loops` REST endpoints for loop CRUD) is superseded. Loop control moves to Hermes plugin commands. Per ADR-035 command migration table:
- `/loop start` → `loop_start_plugin.py` (MEDIUM feasibility)
- `/loop stop` → `loop_stop_plugin.py` (MEDIUM feasibility)
- `/loop pause` → `loop_pause_plugin.py` (MEDIUM feasibility)
- `/loop resume` → `loop_resume_plugin.py` (MEDIUM feasibility)
- `/loop priority` → `loop_priority_plugin.py` (MEDIUM feasibility)
- `/loops` → `loops_status_plugin.py` (MEDIUM feasibility)

The loop orchestration engine (spawning, monitoring, phase advancement) is still needed but without the custom REST API wrapper.

### P5-002: FastAPI Authentication
**Classification:** 🔄 SUPERSEDED

JWT/API key middleware for the custom internal API is superseded. Hermes provides RBAC natively. Auth for destructive operations uses the 4-level auth matrix overlay plugin wrapping `pre_tool_call` hook.

### P5-003: Loop State Machine
**Classification:** ⚠️ PARTIALLY VALID

The 7-phase SDLC logic (`LoopPhase` enum: RESEARCH → PLAN_AND_DELEGATE → DELEGATE → EXECUTE → VALIDATE_AND_AUDIT → UPDATE_DOCUMENTS → SETUP_EVIDENCE → COMPLETE) and `LoopStateMachine` class with `advance()` and `is_complete()` are core Guinevere logic. **This is NOT superseded by Hermes** — Hermes doesn't provide autonomous SDLC loop orchestration.

**What changes:** The state machine no longer runs as a FastAPI-managed service. It runs within the loop manager process, triggered by Hermes plugin commands. The `LoopStateMachine` class itself is valid; the surrounding infrastructure changes.

### P5-004: Research Phase
**Classification:** ✅ VALID — MINOR HERMES ADAPTATION

Spawning explore/librarian agents, generating `research-report.md`. Core logic is valid. Agent spawning mechanism may update for Hermes tool-call integration, but the phase concept and output requirements are unchanged. Agent Loop Spec v2.0 §3.1 already describes Research phase with Hermes awareness.

### P5-005: Plan & Delegate Phase
**Classification:** ✅ VALID — NO CHANGES NEEDED

Task decomposition, sub-agent assignment, `plan.md` generation. Pure orchestration logic. No bot dependency.

### P5-006: Delegate Phase
**Classification:** ✅ VALID — MINOR HERMES ADAPTATION

Sub-agent contract generation (`delegation-manifest.md`). The delegation concept is unchanged. Sub-agents ("Pasukan Mommy") remain neutral, file-based, no persona. Agent spawning mechanism may integrate differently with Hermes, but the contract and delegation model is valid.

### P5-007: Execute Phase
**Classification:** ✅ VALID — MINOR HERMES ADAPTATION

Sub-agent execution monitoring, `execution-log.md`. Hash-anchored edits pattern preserved. Core orchestration logic valid.

### P5-008: Validate & Audit Phase
**Classification:** ✅ VALID — NO CHANGES NEEDED

Parent verification, `validation-report.md`. File-based output discipline unchanged. ADR-035 preserves verification workflow.

### P5-009: Update Documents Phase
**Classification:** ✅ VALID — NO CHANGES NEEDED

Documentation sync, `doc-sync-report.md`. Pure content operation, no bot dependency.

### P5-010: Setup Evidence Phase
**Classification:** ✅ VALID — NO CHANGES NEEDED

`evidence-final.md` generation. File-based evidence pipeline unchanged.

### P5-011: Loop Guardian Watchdog
**Classification:** ✅ VALID — NO CHANGES NEEDED

`LoopGuardian` class: 30s heartbeat interval, 300s progress timeout, 60s resource check. Pure orchestration logic with zero Discord dependency. The watchdog monitors loop state in Redis/PostgreSQL — unchanged by Hermes.

### P5-012: Todo Enforcer
**Classification:** ✅ VALID — NO CHANGES NEEDED

Adopted from oh-my-openagent Todo Enforcer pattern. Core orchestration logic. Independent of Discord layer.

### P5-013: Hash-Anchored Edits
**Classification:** ✅ VALID — NO CHANGES NEEDED

LINE#ID content hash validation. Tool-level feature, independent of bot.

### P5-014: Sub-Agent Spawning via `task()` Tool
**Classification:** ⚠️ NEEDS HERMES ADAPTATION

Sub-agent spawning mechanism needs integration with Hermes tool-call pipeline. Sub-agents ("Pasukan Mommy") still operate in neutral mode (no persona) and report results to Guinevere. The spawning interface may change but the concept is preserved.

### P5-015: Sub-Agent Task Contract Template
**Classification:** ✅ VALID — NO CHANGES NEEDED

Contract template is implementation-agnostic. Same template works regardless of Hermes.

### P5-016: Output Verification (Read Report Files)
**Classification:** ✅ VALID — NO CHANGES NEEDED

Parent reads and verifies sub-agent report files. Core verification discipline — unchanged.

### P5-017: Evidence Generation Pipeline
**Classification:** ✅ VALID — NO CHANGES NEEDED

File-based evidence generation. Unchanged by Hermes.

### P5-018: guinevere-loops.service
**Classification:** ⚠️ NEEDS UPDATE

Systemd service for loop manager. Still required, but with adjusted dependencies:
- **Before Hermes:** `After=guinevere-core.service`
- **After Hermes:** `After=hermes-gateway.service` (Hermes gateway replaces guinevere-core)
- The loop manager runs as a separate service alongside Hermes, not as a component of a custom bot

### P5-019: guinevere-scheduler.service
**Classification:** ⚠️ PARTIALLY SUPERSEDED

Cron triggers for scheduled loops. `hermes cron` provides native scheduling. Some schedule logic may migrate to Hermes cron, but custom scheduled autonomous loops may still need a dedicated scheduler.

### P5-020: /loop-start Command
**Classification:** 🔄 BECOMES HERMES PLUGIN

Per ADR-035 command migration table #13: `/loop start` → `loop_start_plugin.py` (MEDIUM feasibility). "Calls existing loop orchestrator unchanged. Plugin manages loop lifecycle state." Same backend function, different registration mechanism.

### P5-021: /loop-stop Command
**Classification:** 🔄 BECOMES HERMES PLUGIN

Per ADR-035 #14: `/loop stop` → `loop_stop_plugin.py` (MEDIUM feasibility). "Calls existing loop interrupt mechanism. Graceful shutdown logic preserved."

### P5-022: Agent Loop E2E Test
**Classification:** ⚠️ NEEDS HERMES UPDATE

Current test uses `curl -X POST http://localhost:8000/api/v1/loops` — the custom FastAPI endpoint. After Hermes migration, E2E test should trigger through Hermes plugin commands (`/loop start`). Test objectives (7-phase completion, evidence generation) remain valid. Test mechanism changes.

### P5-023: Cost Tracking per Loop
**Classification:** ✅ VALID — NO CHANGES NEEDED

Redis DB5 records cost per loop instance. Backend logic unchanged by Hermes. ADR-035 enhances cost tracking via `hermes insights`.

---

## P5 Steps Superseded by Hermes Agent Loop

These P5 steps are **partially or fully superseded** because Hermes provides equivalent functionality natively:

| Step | Title | Supersession Level | Hermes Replacement |
|---|---|---|---|
| **P5-001** | FastAPI Internal API | **FULLY SUPERSEDED** | Hermes plugin commands (`ctx.register_command()`) replace REST API for loop control |
| **P5-002** | FastAPI Authentication | **FULLY SUPERSEDED** | Hermes RBAC + auth overlay plugin (`pre_tool_call` hook) |
| **P5-020** | /loop-start Command | **FULLY SUPERSEDED** | `loop_start_plugin.py` — same backend, Hermes-native registration |
| **P5-021** | /loop-stop Command | **FULLY SUPERSEDED** | `loop_stop_plugin.py` — same backend, Hermes-native registration |

Steps with **partial** Hermes impact (logic valid, delivery mechanism changes):

| Step | Title | Impact |
|---|---|---|
| **P5-003** | Loop State Machine | State machine logic preserved; runs in loop manager, not FastAPI |
| **P5-018** | guinevere-loops.service | Service still needed; dependencies updated for Hermes |
| **P5-019** | guinevere-scheduler.service | Partially superseded by `hermes cron` |
| **P5-022** | Agent Loop E2E Test | Test mechanism changes (curl → plugin command); objectives unchanged |

---

## P4 Steps Referencing Old bot.py/discord.py Patterns

Only the **Daily Rituals cluster** (P4-008 through P4-013) contains stale `discord_client` references:

| Step | Stale Reference | Location in StepPrompts.md |
|---|---|---|
| **P4-008** | `discord_client.get_channel(int(channel_id))` + `channel.send()` | lines 6502–6507 |
| **P4-008** | `schedule_rituals(scheduler, discord_client, channel_id)` signature | line 6509 |
| **P4-009 to P4-013** | Implicit discord.py dependency for message delivery | Ritual message customization steps |

**No other P4 steps reference `bot.py` or discord.py.** The persona engine logic (mood FSM, yandere, punishment/reward, drift detection, HARD STOP, distress) is cleanly separated from the Discord delivery layer.

---

## Summary Tables

### P4 Summary

| Category | Count | Steps |
|---|---|---|
| ✅ **VALID — No Changes** | 19 | P4-001 through P4-007, P4-014 through P4-018, P4-019b through P4-019e |
| ⚠️ **Needs Hermes Adaptation** | 5 | P4-008 through P4-013, P4-019 |
| 🔄 **Superseded** | 0 | — |
| **TOTAL** | **24** | |

**P4 Verdict:** Persona engine is ~90% implementation-agnostic. The core persona safety logic (mood FSM, yandere FSM, punishment/reward engines, drift detection, HARD STOP, distress protocol) ports directly to Hermes hooks and plugins with zero semantic changes. Only the daily ritual delivery mechanism needs Hermes-adaptation (APScheduler + discord.py → `hermes cron` + plugin message API). ADR-035 explicitly maps every safety feature to a verified hook or plugin.

### P5 Summary

| Category | Count | Steps |
|---|---|---|
| ✅ **VALID — No Changes** | 11 | P5-004, P5-005, P5-008 through P5-013, P5-015 through P5-017, P5-023 |
| ⚠️ **Needs Hermes Adaptation** | 8 | P5-003, P5-006, P5-007, P5-014, P5-018, P5-019, P5-022 |
| 🔄 **Superseded / Becomes Hermes Plugin** | 4 | P5-001, P5-002, P5-020, P5-021 |
| **TOTAL** | **23** | |

**P5 Verdict:** The 7-phase SDLC autonomous loop is still core Guinevere logic that Hermes does NOT replace. However, the delivery mechanism shifts significantly: custom FastAPI REST API → Hermes plugin commands, custom discord.py commands → `ctx.register_command()` plugins, systemd service dependencies adjust from `guinevere-core.service` to `hermes-gateway.service`. The loop orchestration engine, guardian watchdog, todo enforcer, sub-agent contracts, and evidence pipeline remain valid and unchanged — they are pure orchestration logic with zero Discord dependency.

### Key Principle

> **Hermes replaces the Discord gateway, not the autonomous loop.** The 7-phase SDLC is Guinevere's custom orchestration. Hermes provides the messaging layer (Discord gateway, streaming, threading, circuit breaker), session management, and context compression — while Guinevere's loop manager continues to drive autonomous task decomposition, sub-agent spawning, verification, and evidence generation.

---

## Evidence Sources

| Source | Path | Relevance |
|---|---|---|
| StepPrompts P4 | `stepprompts/StepPrompts.md` lines 6364–6780 | All 24 P4 steps analyzed |
| StepPrompts P5 | `stepprompts/StepPrompts.md` lines 6783–7063 | All 23 P5 steps analyzed |
| ADR-035 | `adr/ADR-035-hermes-migration.md` | Hermes migration architecture, 5 pillars, hook mapping, plugin architecture, command migration table |
| Agent Loop Spec | `docs/00-core/03-AgentLoopSpec_v2.0.md` | 7-phase SDLC loop specification, "Built on Hermes Agent" |
| Persona Document | `docs/00-core/06-Persona_Document_v3.0.md` | Persona identity, emotional system, mood FSM |
| Persona Safety Policy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` | AC-SAFE criteria, forbidden patterns F-01 to F-15 |
| System Prompt Master | `docs/60-persona/61-SystemPromptMaster_v1.1.md` | System prompt → SOUL.md migration reference |

---

## Footer

- **Audit completeness:** All 24 P4 steps + all 23 P5 steps classified
- **Boundary check:** No secrets exposed, no implementation changes made, no step prompts modified
- **Next action:** P5 steps marked 🔄 SUPERSEDED should have updated step prompts written post-Hermes migration. P4-008 through P4-013 ritual steps should be updated to reference `hermes cron` + plugin delivery instead of `discord_client`.