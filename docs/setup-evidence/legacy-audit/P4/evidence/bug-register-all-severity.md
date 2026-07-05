# P4 Persona Engine — Bug Register (All Severity)

**Date:** 2026-06-26 (corrected 2026-06-26 — live VPS reconciliation)
**Audit:** Legacy Implementation Audit (read-only) + Live VPS Reconciliation
**Source:** Research phase + Wave-1 (7 dimensions) + Wave-2 (adversarial verification) + Live VPS journal/systemctl

---

## CRITICAL (1)

### B-CRIT-01: P4-020 Consent Revocation Has No Source-Level Integration
- **Severity:** CRITICAL
- **Classification:** CONFIRMED_CURRENT_SOURCE (unchanged by live VPS reconciliation)
- **Claim:** CHECKLIST.md line 405: `[x] P4-020: Consent Revocation Flow Test — all escalation halted on revocation (AC-SAFE-003) ✅`
- **Reality:** No consent-aware code exists in `src/persona/`. transition_rules.py TransitionContext has no consent parameter. yandere_fsm.py can_escalate/get_effective_level have no consent parameter. punishment_engine.py "consent" appears only as example violation_type string. safe_mode.py has no consent gate. The safety_plugin's Gate 10 is explicitly deferred: `"gate_10_consent_deferred"` at `src/hermes/safety_plugin.py:900`.
- **Evidence:** Source maps in `research/p4-persona-source-map.md` §4 (lines 325-339), `audits/round-1/persona-safety-hardstop-consent.md` §3, `audits/round-1/architecture-implementation.md` line 40.
- **Impact:** P4-020 CHECKLIST claim is source-false. Consent revocation does NOT halt persona escalation. The external consent system (consent_ledger, consent_gate.py) exists but the persona engine does not consume it.
- **Wave-2 verification:** CONFIRMED — refutation failed.

### ~~B-CRIT-02: PersonaPlugin NOT REGISTERED~~ — REFUTED_BY_VPS (2026-06-26)
- **Previous claim:** "PersonaPlugin (src/hermes/plugins/persona_plugin.py) is NOT REGISTERED in any Hermes config. The entire persona context injection system is dead."
- **Reality:** PersonaPlugin IS registered and injecting live. VPS journal shows 3,086 combined `persona_plugin_inject` events on 2026-06-25 (hermes-gateway: 45, guinevere-core: 3,041) with `mood_variant=Y4_PLAYFUL`, `yandere_level=4`, `punishment_level=0`, `reward_tier=0`, `distress_state=0`. Registration via `hermes-config/plugins/guinevere_persona/__init__.py` → `register(ctx)`.
- **Evidence:** `evidence/p4-live-vps-reconciliation-audit.md` §Persona Plugin Live Evidence.
- **Remaining concern:** The behavioral engines (punishment_engine, reward_engine, streak_tracker, mood_persistence, transition_rules, drift_corrector) are not directly instantiated by any runtime caller. The PersonaPlugin reads from Redis DB5, not from these engines. The 6 behavioral engines remain dead code. See B-HIGH-09.

---

## HIGH (9)

### B-HIGH-01: P4-015 Drift "Rollback" Is Record-Keeping Only
- **Severity:** HIGH
- **Claim:** CHECKLIST line 399: "Persona drift correction (>10% → alert + rollback)"
- **Reality:** `DriftCorrector.rollback()` at `drift_corrector.py:188-268` records baseline hash as "restored state" in DriftLog. Does NOT reload or replace the actual system prompt. The docstring admits: "Does **not** modify persona content." This is a log entry, not a real rollback.
- **Evidence:** `research/p4-persona-source-map.md` §16 (lines 248-259), `audits/round-1/architecture-implementation.md` line 34.
- **Wave-2 verification:** CONFIRMED.

### B-HIGH-02: P4-008 Through P4-013 Rituals Deprecated, Not Noted in Checklist
- **Severity:** HIGH
- **Claim:** CHECKLIST marks P4-008-013 `[x] ✅` complete with no deprecation note.
- **Reality:** All 6 ritual modules (ritual_scheduler + 5 rituals) are deprecated Phase 5, scheduled removal Phase 7. Removal never happened. Deprecation warnings suppressed in `__init__.py:128-129`. Hermes cron replacement exists but is stripped-down (simple `hermes chat -Q` calls, not the same ritual logic). The CHECKLIST claims 6 of 23 steps as complete for code that is explicitly marked for deletion.
- **Evidence:** `research/p4-persona-source-map.md` §9-14 (lines 160-226), `audits/round-1/ritual-scheduler-drift-correction.md`.
- **Wave-2 verification:** CONFIRMED.

### B-HIGH-03: R-03 KNOWN-ISSUES Entry Factually False
- **Severity:** HIGH
- **Claim:** KNOWN-ISSUES.md v1.1 says R-03 RESOLVED — "Enum renamed to SOUL.md names: L1_GENTLE_REMINDER, L2_SOFT_CORRECTION..."
- **Reality:** Source has original names (L1_SILENT_TREATMENT through L5_ISOLATION). The SOUL.md rename was never applied to any commit. L5 duration is still (48, 72) hours, not SOUL.md "Max 24h". This is a documentation integrity issue — the KNOWN-ISSUES registry claims a fix that does not exist in source.
- **Evidence:** `research/p4-known-issues-reconciliation.md` §R-03 (lines 47-55), `audits/round-1/evidence-docs-consistency.md`.
- **Wave-2 verification:** CONFIRMED.

### B-HIGH-04: 5 of 7 Test-Only Verification Files Reference Wrong Test Paths
- **Severity:** HIGH
- **Claim:** P4-017, P4-020, P4-021, P4-022, P4-023 verification.md files claim test files at `tests/persona/test_*.py`.
- **Reality:** Actual test files are at `tests/safety/test_*.py`. The verification.md paths are wrong. A verification report pointing to non-existent files is not valid evidence.
- **Evidence:** `audits/round-1/architecture-implementation.md` lines 37-42.
- **Wave-2 verification:** CONFIRMED.

### B-HIGH-05: SOUL_BASELINE_HASH Hardcoded with No Verification
- **Severity:** HIGH
- **Claim:** P4-014 drift detection uses SHA-256 hamming distance against baseline.
- **Reality:** `drift_detector.py:62` has hardcoded `SOUL_BASELINE_HASH = "b8d55fe72f657c93b497e8f5001c7035faf4fa7ab7174b68a25c2ee1cafe9740"`. No mechanism verifies this hash matches the current SystemPromptMaster document. The baseline may be stale — if the SystemPromptMaster was updated, drift detection would false-positive on every check.
- **Evidence:** `research/p4-persona-source-map.md` §15 (line 239-243), `audits/round-1/ritual-scheduler-drift-correction.md`.

### B-HIGH-06: Two SafeModeController Instances with No Shared State
- **Severity:** HIGH
- **Claim:** Safe mode is a global safety mechanism.
- **Reality:** Two independent SafeModeController instances exist: `safety_plugin.py:455` (Hermes agent loop) and `hermes_conversational.py:457` (Discord conversational handler). They cannot share state. HARD STOP triggered in the plugin is invisible to the conversational handler unless the handler independently detects it. This creates a split-brain safety risk.
- **Evidence:** `research/p4-runtime-readiness-readonly.md` lines 163-164, `audits/round-1/architecture-implementation.md` §4.

### B-HIGH-07: PunishmentEngine HARD STOP Guard Is Conditional on Constructor Wiring — RECLASSIFIED MEDIUM
- **Severity:** MEDIUM (downgraded from HIGH 2026-06-26 — DESIGN_RISK_DORMANT)
- **Claim:** HARD STOP blocks all punishment.
- **Reality:** The guard at `punishment_engine.py:276-281` is `if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe`. If PunishmentEngine is constructed without `hard_stop_handler` (default: None), the guard is silently skipped. However, since PunishmentEngine is dead code (not instantiated at runtime), this is a dormant design risk.
- **Evidence:** `research/p4-known-issues-reconciliation.md` §(d) (lines 263-271), `audits/round-1/persona-safety-hardstop-consent.md` §2.
- **VPS reconciliation:** DESIGN_RISK_DORMANT — would become active only if PunishmentEngine were ever wired.

### B-HIGH-08: check_distress_suspension() Never Auto-Invoked
- **Severity:** HIGH
- **Claim:** Punishment is suppressed during emergency (distress >= D3).
- **Reality:** `check_distress_suspension()` at `punishment_engine.py:584-608` correctly suspends punishment at D3+. But it has ZERO callers — no code path auto-invokes it. The suspension mechanism is dead code. Emergency punishment suppression only works through the safe_mode guard path (which blocks new punishment but doesn't suspend active punishment).
- **Evidence:** `audits/round-1/persona-safety-hardstop-consent.md` §4, `audits/round-1/mood-punishment-reward-runtime.md`.

### B-HIGH-09: 6 Behavioral Engines Dead Code (Punishment, Reward, Streak, Mood Persistence, Transition Rules, Drift Correction)
- **Severity:** HIGH
- **Classification:** CONFIRMED_CURRENT_SOURCE (split from refuted B-CRIT-02)
- **Claim:** CHECKLIST/PROGRESS mark all 23 P4 steps `[x] ✅` complete, implying all engines are operational.
- **Reality:** 6 behavioral engines have no runtime callers: mood_persistence, transition_rules, punishment_engine, reward_engine, streak_tracker, drift_corrector. PersonaPlugin IS live and injecting (reads Redis DB5), but these engines are not the source of the Redis data. The Redis keys appear to contain default values (punishment_level=0, reward_tier=0).
- **Impact:** Persona behavioral state (mood transitions, punishment escalation, reward tiers, streak tracking, drift correction) is not being actively computed by the engines. The PersonaPlugin injects whatever is in Redis — which may be defaults or set by Discord commands directly.
- **NEEDS RUNTIME VERIFICATION:** Redis DB5 key inspection to confirm whether values are live or default.
- **Evidence:** `research/p4-runtime-readiness-readonly.md` lines 180-244, `evidence/p4-live-vps-reconciliation-audit.md`.

---

## MEDIUM (12)

### B-MED-01: P4-002 Wrong Table Name in Documentation
- CHECKLIST/PROGRESS say `persona.mood_states`. Actual table is `persona.persona_state` with `state_key="current_mood"`. Source: `mood_persistence.py:24,107,149`. `memory/models.py:414`.

### B-MED-02: P4-001 FSM Label Misleading
- CHECKLIST says "Content → Pleased → Disappointed → Angry → Silent" (linear). Actual FSM allows Content→Disappointed directly and Silent→Content directly. Source: `mood_engine.py:39-45`.

### B-MED-03: L5 Punishment Duration Contradicts SOUL.md
- Code: L5 Isolation (48-72) hours at `punishment_engine.py:175-188`. SOUL.md: "Max 24h". 3x violation.

### B-MED-04: milestone_engine.py Unclaimed, with Architectural Risks
- 872 lines, not in P4 checklist, not imported by __init__.py. Hardcoded Redis/PostgreSQL params, daemon threads, no DI. Source: `milestone_engine.py`.

### B-MED-05: 23/23 Steps Lack evidence/ Subfolders
- Every STEP-P4-NNN dir contains only verification.md. No evidence/ subfolder, no raw command outputs, no CI logs. The project pattern requires evidence/ subfolders.

### B-MED-06: 23/23 Steps Lack auditor-gate.md
- P4-016 and P4-017 verification.md explicitly claim "mandatory auditor gate" but no auditor-gate.md exists in any step.

### B-MED-07: D04-tests-batch2.md Empty (0 bytes)
- `audit-reports/P4/P4-FINAL-AUDIT/D04-tests-batch2.md` is an empty file. Missing audit evidence.

### B-MED-08: A02 Missing from NEW-AUDIT-2026
- `audit-reports/P4/NEW-AUDIT-2026/` jumps from A01 to A03. A02 is missing.

### B-MED-09: D10 Missing from P4-FINAL-AUDIT
- `audit-reports/P4/P4-FINAL-AUDIT/` jumps from D09 to D11. D10 is missing.

### B-MED-10: Dual-Write Risk (Redis vs PostgreSQL)
- Mood state exists in both Redis DB5 (`guinevere:mood_variant`) and PostgreSQL (`persona.persona_state`). If both were active, they'd diverge. Currently only Redis is active, PostgreSQL is dead.

### B-MED-11: External Channels Hardcode mood="Content"
- WhatsApp bridge (`channels/whatsapp/bridge.py:163`) and Gmail bridge (`gmail/bridge.py:530,584`) both pass `mood="Content"` — never the live persona mood. Persona behavior does not flow to external channels.

### B-MED-12: __init__.py Deprecation Suppression
- `warnings.catch_warnings()` + `simplefilter("ignore")` at `__init__.py:128-129` silently suppresses DeprecationWarning for all ritual imports. Downstream code can use deprecated symbols without any warning.

---

## LOW (5)

### B-LOW-01: Stale Wearable Import
- `wearable/alert_router.py:25` imports `is_safe_mode_active` from `yandere_fsm` — symbol does not exist. Try/except sets to None, falls back to Redis key. Degrades gracefully but is stale code.

### B-LOW-02: A01-A04 KNOWN-ISSUES Advisories Unresolved
- A01 (RitualResult naming collision), A02 (3 missing exports from __init__.py), A03 (mutable result types in ritual modules), A04 (drift_corrector.py uses `db: Any`). All still applicable.

### B-LOW-03: AC-PERSONA References Missing from PROGRESS.md
- CHECKLIST.md has 16 AC-PERSONA references. PROGRESS.md has zero. Inconsistent tracking.

### B-LOW-04: Test Count Contradiction
- PROGRESS.md says 1449 tests PASS. CHECKLIST.md says 1460. Actual persona collection is 1160. Whole-repo is 5478. Stale numbers in tracking docs.

### B-LOW-05: Third "Phase 4" Entity in Acceptance Criteria Catalog
- `docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md` line 243 defines a third "Phase 4" (Surveillance & Financial MVP) that is neither P4 Persona Engine nor phase-4 ADR-035 MCP migration.

---

## COSMETIC (2)

### B-COS-01: Transitions Map Duplicated
- `mood_engine.py:39-45` and `transition_rules.py:57-63` both define the same transitions map independently. No single source of truth.

### B-COS-02: Angry → "caring" Mood Variant Undocumented
- `mood_engine.py:98` maps Angry → "caring" variant. This choice is not documented or explained anywhere.

---

## Summary

| Severity | Count | Notes |
|----------|-------|-------|
| CRITICAL | 1 | P4-020 consent. B-CRIT-02 (PersonaPlugin NOT REGISTERED) REFUTED_BY_VPS 2026-06-26 |
| HIGH | 9 | B-HIGH-01 through B-HIGH-08 + B-HIGH-09 (6 behavioral engines dead code, split from refuted B-CRIT-02) |
| MEDIUM | 13 | Includes B-HIGH-07 downgraded to DESIGN_RISK_DORMANT |
| LOW | 5 | |
| COSMETIC | 2 | |
| **TOTAL** | **30** | 1 refuted, 1 downgraded, 1 added (split) |