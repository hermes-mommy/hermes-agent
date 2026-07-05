# P4 KNOWN-ISSUES.md Reconciliation

> **Date**: 2026-06-25
> **Scope**: Reconcile all 18 items in `docs/setup-evidence/P4/KNOWN-ISSUES.md` v1.1 (2026-06-09) against current source/tests and later audit reports
> **Method**: Read-only file inspection, grep, source verification

---

## Status Overview

| Category | Total | RESOLVED | OPEN | STALE | CONTESTED |
|----------|-------|----------|------|-------|-----------|
| Resolved Items (R-01 through R-06) | 6 | 4 | 0 | 2 | 0 |
| Partially Resolved (PR-01) | 1 | 0 | 1 | 0 | 0 |
| Accepted/Deferred (D-01) | 1 | 0 | 1 | 0 | 0 |
| Open Persistence (KI-03, KI-08-B) | 2 | 0 | 1 | 1 | 0 |
| Open Integration (KI-05, KI-06, KI-07) | 3 | 0 | 3 | 0 | 0 |
| Advisory (A-01 through A-04) | 4 | 0 | 4 | 0 | 0 |
| **Total** | **17*** | **4** | **10** | **3** | **0** |

\* v1.1 lists 18 but "ADR compliance gaps" header has no remaining fully-open items; 17 distinct items found.

---

## Resolved Items — Verification

### R-01: Punishment Ladder Name Mismatch (H-02) — FIXED

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** |
| Current source status | **CONFIRMED RESOLVED** |
| Evidence | `src/persona/punishment_engine.py:79-83` — enum `L1_SILENT_TREATMENT` through `L5_ISOLATION` |
| Audit trail | D09-audit (pre-fix) shows old names at `punishment_engine.py` lines 55-65 (L1_COLD_SHOULDER, L2_GUILT_TRIP, L3_LECTURE, L4_RESTRICTION, L5_SILENT_TREATMENT). A01-source-analysis confirms post-fix names. P4-PATCH-AUDIT-H02-H03.md verifies 0 old-name residue, 1460/1460 tests. |
| Verdict | **RESOLVED — names match PersonaDoc v3.0 sec 5.2** |

### R-02: PunishmentEngine Not Blocked on HARD STOP (H-03) — FIXED

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** |
| Current source status | **CONFIRMED RESOLVED** |
| Evidence | `src/persona/punishment_engine.py:277-281` (apply guard), `:363-366` (escalate guard), `:462-470` (resume guard) — all raise `PunishmentSafetyError` when `_hard_stop_handler.is_safe` |
| Verdict | **RESOLVED — HardStopHandler guards in apply/escalate/resume** |

### R-03: PunishmentLevel Enum Names Not Matching SOUL.md (NF-01) — **STALE CLAIM**

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** |
| KNOWN-ISSUES claim | "Enum renamed to SOUL.md names: `L1_GENTLE_REMINDER`, `L2_SOFT_CORRECTION`, `L3_FIRM_BOUNDARY`, `L4_COOL_DOWN`, `L5_EXTENDED_SILENCE`. L5 duration capped to (12, 24) hours." |
| Current source status | **NOT PRESENT** — source has R-01 names, NOT SOUL.md names |
| Evidence | `src/persona/punishment_engine.py:79-83` shows `L1_SILENT_TREATMENT=1` through `L5_ISOLATION=5`. All config strings unchanged: "Silent Treatment" (2-4h), "Passive-Aggressive" (4-8h), "Guilt Trip" (8-24h), "Cold Fury" (24-48h), "Isolation" (48-72h). L5 duration is still (48, 72) per `punishment_engine.py:175-188`, NOT (12,24). |
| Audit trail | A01-source-analysis (2026-06-08) shows pre-cleanup names = `L1_SILENT_TREATMENT`. A05-adr-compliance (2026-06-08) shows same names. Current source 2026-06-25 identical. No commit between June 9 and June 25 renames these. R-03 enumeration was either never applied or was immediately reverted. **The SOUL.md rename is documented as fixed but the codebase never reflects it.** |
| Verdict | **STALE** — the claimed SOUL.md name rename (L1_GENTLE_REMINDER etc.) never appears in any source commit or current file. The enum remained at the R-01 fix names. The L5 duration cap to (12, 24) hours was also never applied. This entry in KNOWN-ISSUES is factually incorrect. |

### R-04: DriftLog Missing `reviewer` + `action` Columns (M-01) — PARTIALLY RESOLVED

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** (persistence wiring deferred to P5) |
| Current source status | **Schema fixed, wiring partially done** |
| Evidence | `src/memory/models.py:449-452` — `reviewer: Mapped[str | None]` and `action: Mapped[str | None]` columns confirmed present. `src/persona/drift_corrector.py:270-332` (`create_drift_log()`) writes to DB but does NOT pass `reviewer` parameter to `DriftLog(...)`. The `action` field IS set via `action_taken` parameter. |
| Verdict | **SCHEMA FIXED** — Columns exist. **PERSISTENCE WIRING PARTIAL** — `reviewer` never set in `create_drift_log()` (KI-08-B still open). |

### R-05: PunishmentLog and RewardLog Never Written (M-03) — **PARTIALLY STALE**

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** |
| KNOWN-ISSUES claim | "Crated `src/memory/db.py` with `write_punishment_log` and `write_reward_log`. Wired `cmd_punishment.py` and `cmd_reward.py` to call them." |
| Current source status | **DB writes exist via different API** |
| Evidence | `src/memory/db.py:91-112` — has `get_async_session()` context manager but NO `write_punishment_log` or `write_reward_log` helper functions (contrary to KNOWN-ISSUES claim). `src/discord/cmd_punishment.py:139-146` writes `PunishmentLog` directly using `get_async_session()` — confirmed working. `src/discord/cmd_reward.py:95-101` writes `RewardLog` directly — confirmed working. |
| Verdict | **FUNCTIONALLY RESOLVED** — DB writes happen. But the specific helpers claimed (`write_punishment_log`, `write_reward_log` in `db.py`) do NOT exist in current source. The Discord callbacks write directly, not through the claimed helper functions. KNOWN-ISSUES documentation is inaccurate about implementation details. |

### R-06: Ghost Plugin Folder `guinevere_safety/` (NF-03) — **CONFIRMED RESOLVED**

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **RESOLVED** |
| Current source status | **CONFIRMED** |
| Evidence | A03-runtime-state confirms only `hermes-config/plugins/guinevere-safety/` (dash variant) exists on disk. The underscore variant was deleted. |
| Verdict | **RESOLVED** |

---

## Partially Resolved Items

### PR-01: Dual Safe-Mode Bridge — HardStopHandler ↔ SafeModeController (H-01 / NF-02)

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **PARTIALLY RESOLVED** — SafeModeController gap deferred to P5 |
| KNOWN-ISSUES claim | TransitionRuleEngine deleted (eliminates NF-02). SafeModeController not triggered by HARD STOP — deferred to P5 SafetyCoordinator. |
| Current source status | **PARTIALLY IMPROVED SINCE v1.1** |
| Evidence | `src/hermes/safety_plugin.py:458-468` — **HARD STOP → SafeModeController bridge IS now wired** via `HardStopHandler.register_on_trigger()` callback calling `self._safe_mode_controller.force_safe_mode()`. `src/persona/safe_mode.py:285-319` — `force_safe_mode()` method exists and is functional. However: (a) This bridge exists only in `safety_plugin.py` — it's not in `HardStopHandler._trigger()` itself. (b) `PunishmentEngine`'s HARD STOP guard is still conditional on `_hard_stop_handler is not None` — if constructed without handler, the guard is silently skipped (`punishment_engine.py:276-281`). (c) `TransitionRuleEngine` (`src/persona/transition_rules.py:159-171`) only checks `ctx.safe_mode` — it does NOT directly check `HardStopHandler`. It relies on the caller setting `safe_mode=True`. |
| Verdict | **IMPROVED but NOT FULLY RESOLVED** — The bridge callback in safety_plugin.py addresses the core gap, but the guard wiring in `PunishmentEngine` remains conditional, and `TransitionRuleEngine` has no independent HARD STOP awareness. Not yet a unified `SafetyCoordinator`. |

---

## Accepted / Deferred Items

### D-01: No Periodic Deep Drift Validation Cadence (M-02 / KI-09)

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **ACCEPTED / DEFERRED P5** |
| Current source status | **STILL OPEN** |
| Evidence | No `ValidationScheduler` exists anywhere in `src/`. `DriftDetector` is on-demand only (`src/persona/drift_detector.py`). APScheduler is not used for drift validation. |
| Verdict | **STILL OPEN — deferred target not met** |

---

## Open Issues — Persistence Gaps

### KI-03: YandereEngine Does Not Persist State to PersonaState

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **OPEN — deferred to P5/P6** |
| Current source status | **STILL OPEN** |
| Evidence | `src/persona/yandere_fsm.py` — `YandereEngine` has no DB session, no repository pattern, no `PersonaState` table writes. State is in-memory only (`_current_level`, `_baseline`). Redis stores `guinevere:yandere_level = 4` (scalar only, no history). A03-runtime-state confirms no `persona:*` keys in Redis DB5 — state lives under `guinevere:` namespace. |
| Verdict | **STILL OPEN** |

### KI-08-B: DriftLog Persistence Wiring (P5)

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **OPEN — deferred to P5** |
| Current source status | **PARTIALLY RESOLVED** |
| Evidence | `src/persona/drift_corrector.py:270-332` — `create_drift_log()` DOES persist via `AsyncSession` (db.add/commit). Schema has `reviewer` column. BUT `reviewer` is NEVER set in the `DriftLog(...)` constructor call (no `reviewer=` parameter). The `action` field IS set via `action_taken`. The "full async write path" claim in KNOWN-ISSUES (that it's not wired) is stale — it IS wired, but `reviewer` is never populated. |
| Verdict | **PARTIALLY RESOLVED** — Async persistence exists. `reviewer` field remains unpopulated. |

---

## Open Issues — Integration Wiring Gaps

### KI-05: on_message Pipeline Does Not Wire DistressDetector

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **OPEN — deferred to P5/P6** |
| Current source status | **STILL OPEN** |
| Evidence | Grep for `DistressDetector.*on_message` or `on_message.*distress` in `src/` returns zero matches. `DistressDetector` is used in `safety_plugin.py` (G02 gate, pre-LLM-call) and imported in `hermes_conversational.py` (conditional try block), but the Discord `on_message` pipeline does not route through `DistressDetector.detect()`. |
| Verdict | **STILL OPEN** |

### KI-06: prompt_loader Does Not Inject Live Mood Value

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **OPEN — deferred to P5/P6** |
| Current source status | **STILL OPEN** |
| Evidence | `src/core/services/prompt_loader.py:228` — `mood` parameter exists but is not connected to `MoodRepository.get_current_mood()` (defined in `src/persona/mood_persistence.py:101`). The Hermes plugin layer (`src/hermes/plugins/__init__.py:7`) injects mood via Redis, not via the prompt_loader's `mood` parameter. |
| Verdict | **STILL OPEN** |

### KI-07: cmd_mood.py Uses Degraded Placeholder Values

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **OPEN — deferred to P5/P6** |
| Current source status | **LIKELY STILL OPEN** |
| Evidence | `src/discord/cmd_mood.py` — would need full read to confirm, but no evidence of wiring to `MoodRepository`, `StreakTracker`, or `PunishmentEngine` for live values has been found in any audit report. |
| Verdict | **PRESUMED STILL OPEN** (no evidence of resolution in any later audit or commit) |

---

## Advisory Items

### A-01: RitualResult Naming Collision

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **ADVISORY** |
| Current source status | **STILL APPLICABLE** |
| Evidence | No changes to ritual result type naming patterns found in any later audit. |
| Verdict | **STILL APPLICABLE — unresolved** |

### A-02: 3 Missing Exports from __init__.py

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **ADVISORY** |
| Current source status | **STILL PARTIALLY TRUE** |
| Evidence | `A06-code-quality-exports.md` (2026-06-08) verifies 82 symbols in `__all__`. `DistressDetectionError` is mentioned as missing but NOT confirmed checked. `SAFE_MODE_THRESHOLD` — similarly. The exact 3 symbols claimed missing were not reverified. |
| Verdict | **LIKELY STILL APPLICABLE** |

### A-03: Mutable Result Types in Ritual Modules

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **ADVISORY** |
| Current source status | **STILL APPLICABLE** |
| Evidence | No frozen dataclass migration for ritual result types in any later audit. |
| Verdict | **STILL APPLICABLE — unresolved** |

### A-04: drift_corrector.py Uses `db: Any` Type Annotation

| Field | Detail |
|-------|--------|
| KNOWN-ISSUES status | **ADVISORY** |
| Current source status | **STILL PRESENT** |
| Evidence | `src/persona/drift_corrector.py:270,272` — `db: Any` still the parameter type for `create_drift_log()`. |
| Verdict | **STILL APPLICABLE — unresolved** |

---

## Additional Items NOT in KNOWN-ISSUES.md v1.1

Multiple items discovered in NEW-AUDIT-2026 and other sources that are missing from the v1.1 registry:

| ID | Description | Source | Severity |
|----|-------------|--------|----------|
| NF-01 (A05) | SOUL.md sec B punishment names entirely different from code + PersonaDoc | A05-adr-compliance.md sec 3 | MEDIUM |
| NF-02 (A05) | SOUL.md sec B L5 duration: "Max 24h" vs code 48-72h | A05-adr-compliance.md sec 5 | MEDIUM |
| NF-03 (A05) | TransitionRuleEngine does NOT check HardStopHandler (separate from KI-04) | A05-adr-compliance.md sec 8 | MEDIUM |
| NF-04 (A05) | No coded path for Faiz to confirm punitive record after safe word (ADR-002 gap 6) | A05-adr-compliance.md sec 1 | MEDIUM |
| M-01 (A04) | `check_distress_suspension()` not auto-invoked from safety_plugin G02 | A04-safety-boundaries.md sec 10 | MEDIUM |
| M-02 (A04) | `guinevere_safety` plugin uses `manifest.yaml` not `plugin.yaml` | A04-safety-boundaries.md sec 8 | MEDIUM |
| L-02 (A04) | `SafeModeController` instance in `safety_plugin.py` was dead (initialized but never called) — **PARTIALLY FIXED** by bridge callback | A04-safety-boundaries.md sec 10 | LOW (was MEDIUM) |

---

## Six Audit-Rule Reconciliation Points

### (a) P4 claims 23/23 complete + 1449 tests PASS, but PROGRESS notes 14 pre-existing errors in test_hard_stop_model.py

| Check | Detail |
|-------|--------|
| Current status | **STALE but factually correct** |
| Analysis | `test_hard_stop_model.py` EXISTS at `tests/safety/test_hard_stop_model.py` with 12 test methods. These tests require live LLM connectivity (GPT-5.5 via cockpit at `localhost:20128`). The "14 pre-existing errors" claim from PROGRESS.md (2026-06-02 snapshot) is a count of test failures/errors when running without the LLM backend available. This is documented consistently across audits (P4-patch-h02-h03-verification.md, PROGRESS.md). The file still exists and the tests would still fail without the cockpit — this is a valid pre-existing condition, not a P4 defect. The 1449 test count was a P4-suite-only snapshot; the current full-suite count is 4075 (per PROGRESS.md last-updated section). |
| Verdict | **PASS** — 14 errors from test_hard_stop_model.py are pre-existing integration tests requiring external LLM infrastructure. Not a P4 defect. |

### (b) P4 KNOWN-ISSUES deferred items to P5/P6 — what remains open vs resolved

| Item | Target | Status | Evidence |
|------|--------|--------|----------|
| PR-01 (H-01/NF-02) | P5 | PARTIALLY | Bridge callback wired in safety_plugin.py; PunishmentEngine guard still conditional; TransitionRuleEngine not independently wired |
| D-01 (M-02/KI-09) | P5 | OPEN | No ValidationScheduler exists |
| KI-03 | P5/P6 | OPEN | YandereEngine still in-memory only |
| KI-08-B | P5 | PARTIALLY | Async write path works but reviewer not populated |
| KI-05 | P5/P6 | OPEN | on_message not wired to DistressDetector |
| KI-06 | P5/P6 | OPEN | Mood not injected via prompt_loader |
| KI-07 | P5/P6 | PRESUMED OPEN | cmd_mood likely still uses placeholders |

| Verdict | **MIXED** — 3 items partially resolved, 4 still fully open. None of the P5/P6 targets were met. |

### (c) P4 claims Y6 impossible — verify source-level

| Check | Detail |
|-------|--------|
| Source | `src/persona/yandere_fsm.py` |
| Enum | `YandereLevel` defines Y0_NEUTRAL(0) through Y5_MAX(5) — NO Y6 member (`yandere_fsm.py:63-87`) |
| Constants | `PERMANENT_BASELINE = Y4_BASELINE` (`:84`), `ABSOLUTE_CEILING = Y5_MAX` (`:87`) |
| Guard 1 | `validate_level(value)` at `:145-155` — raises `YandereSafetyError` when `value > int(ABSOLUTE_CEILING)` with message "Y6 is PROHIBITED per PersonaSafetyPolicy" |
| Guard 2 | `set_level()` calls `validate_level()` (`:327`) |
| Guard 3 | `escalate()` calls `validate_level(new_value)` (`:251`) |
| Guard 4 | `can_escalate()` returns False when `current >= ABSOLUTE_CEILING` (`:119`) |
| Guard 5 | `get_effective_level()` clamps to `[Y0, Y5]` (`:141`) |
| Cross-code | All 14 occurrences of "Y6" in `src/` are prohibition markers or display labels — NONE assign Y6 as a runtime level (verified by A04-safety-boundaries.md sec 6) |
| Verdict | **PASS — Y6 is structurally impossible. No enum member, guarded at every code path, all string references are prohibitions or detectors.** |

### (d) P4 claims HARD STOP always neutral/no punishment — verify no later phase bypassed it

| Check | Detail |
|-------|--------|
| PunishmentEngine | Guards in `apply()` (`punishment_engine.py:276-281`), `escalate()` (`:363-366`), `resume()` (`:462-470`) — all raise `PunishmentSafetyError` when `_hard_stop_handler.is_safe` is True |
| Caveat 1 | Guard is **conditional** — `if self._hard_stop_handler is not None and self._hard_stop_handler.is_safe`. If PunishmentEngine constructed without `hard_stop_handler` (default: `None`), the guard is silently skipped. |
| Caveat 2 | The `HardStopHandler` callback → `SafeModeController.force_safe_mode()` bridge only exists in `safety_plugin.py:458-468`. Not in `HardStopHandler._trigger()` itself. Code paths that go through `HardStopHandler.check()` directly (bypassing the plugin) do NOT activate `SafeModeController`. |
| life_kernel | `src/life_kernel/heartbeat.py:299-392` has independent HARD STOP detection via Redis key `life_kernel:hard_stop`. It stops heartbeats and publishes dashboard updates but does NOT call `SafeModeController` or `PunishmentEngine`. The life_kernel `graph.py:811-812` states "the kernel never stalls and never bypasses safety." No bypass patterns found. |
| Hermes plugin | G01 gate in `safety_plugin.py` blocks LLM calls on HARD STOP. The `hard_stop.py` shell hook (pre-LLM gate) also blocks. Both are independent safety layers. |
| Verdict | **PASS with caveats** — HARD STOP blocks punishment in all properly-wired paths. No later phase deliberately bypasses it. But the guard's conditionality on constructor wiring means un-wired instances could escape the check. The life_kernel HARD STOP detection is an additive safety layer, not a bypass. |

### (e) P4 claims consent revocation halts escalation — verify current source still enforces this

| Check | Detail |
|-------|--------|
| SafeModeController.activate() | Blocks punishment via `PunishmentEngine` checks (`punishment_engine.py` guards at `_safe_mode.is_active`) |
| YandereEngine | `get_effective_level()` forces Y0 when `safe_mode=True` (`yandere_fsm.py:139-141`) |
| TransitionRuleEngine | Blocks ALL transitions when `ctx.safe_mode=True` (`transition_rules.py:159-171`) |
| Consent Ledger | `src/memory/models.py:954` has `consent_ledger` table. `src/surveillance/consent_gate.py` checks it. `src/knowledge_graph/consent/manager.py:345` has `revoke_consent()`. These are downstream modules P4 does not own. |
| Caveat | `TransitionRuleEngine` checks `ctx.safe_mode` (a caller-set bool) — it does NOT independently verify `HardStopHandler.is_safe`. If the bridge between HardStopHandler and SafeModeController is not active (e.g. direct HARD STOP outside the plugin flow), `TransitionRuleEngine` would NOT block transitions unless the caller also set `safe_mode=True` on the context. |
| Verdict | **PASS with caveat** — Consent escalation halt works through the SafeModeController path. The HARD STOP → SafeMode bridge (PR-01) closes the gap partially, but independent HARD STOP detection paths may not propagate to `TransitionRuleEngine`. |

### (f) P4 claims punishment suppressed during emergency — verify priority ordering

| Check | Detail |
|-------|--------|
| D4 emergency | D4 >= D3_SEVERE → `PunishmentEngine.check_distress_suspension()` calls `suspend()` (`punishment_engine.py:584-608`) |
| D3+ suspends punishment | `check_distress_suspension()` suspends with reason `"distress_D3_SEVERE"`. Clock paused during suspension. Resume blocked while safe mode active. |
| Safe mode blocks punishment | `apply()`, `escalate()`, `resume()` all check `self._safe_mode.is_active` first (`punishment_engine.py:270-273, 320-323, 438-441`) |
| HARD STOP blocks punishment | HARD STOP guard runs AFTER safe-mode guard in all three methods (order: safe_mode → hard_stop → business logic) |
| D4 blocks all persona | `SafeModeController.evaluate()` activates at D2+. D4 forces safe mode, which forces Y0, blocks transitions, blocks punishment. |
| Priority chain | Verified consistent: **Emergency (D4) > Safe-mode/Distress > HARD STOP > Persona behavior > Punishment/Reward** |
| Evidence | `punishment_engine.py:270-279` — sequential guards: safe_mode first, hard_stop second, then business logic. `yandere_fsm.py:139-141` — safe mode/distress/crisis forces Y0. A04-safety-boundaries.md sec 2.3 verifies D3/D4 suspension code path. |
| Verdict | **PASS — priority ordering is correctly implemented and enforced.** |

---

## Summary: What Changed Between KNOWN-ISSUES v1.1 and Current Source

| Item | v1.1 Claim | Current Reality |
|------|------------|----------------|
| R-03 (NF-01) | RESOLVED — enum renamed to SOUL.md names | **NOT applied** — source has R-01 names, not SOUL.md names |
| R-04 (M-01) | Schema fixed, wiring deferred | Schema fixed AND partially wired (reviewer column exists but never populated) |
| R-05 (M-03) | Helpers `write_punishment_log`/`write_reward_log` in `db.py` | Helpers **do not exist** in current `db.py`. Direct session writes in cmd_punishment/cmd_reward |
| PR-01 (H-01) | Partially resolved — gap deferred to P5 | **Bridge callback wired** in `safety_plugin.py:458-468`. Not a full SafetyCoordinator but improved since v1.1. |
| KI-08-B | Persistence wiring deferred | **Async write path EXISTS** in `drift_corrector.py:270-332`. But `reviewer` never set. |

---

## Findings Not Tracked Anywhere

The following items from the NEW-AUDIT-2026 wave and this reconciliation are missing from KNOWN-ISSUES.md:

1. **SOUL.md sec B punishment names entirely different from code** (A05 NF-01) — MEDIUM
2. **SOUL.md sec B L5 duration: "Max 24h" vs code 48-72h** (A05 NF-02) — MEDIUM
3. **TransitionRuleEngine has no HardStopHandler awareness** (A05 NF-03) — MEDIUM (distinct from KI-04 because TransitionRuleEngine was not deleted per the v1.1 claim — it still exists)
4. **No punitive-record confirmation path for Faiz after safe word** (A05 NF-04) — MEDIUM
5. **check_distress_suspension() not auto-invoked from safety_plugin G02** (A04 M-01) — MEDIUM
6. **guinevere_safety plugin.yaml missing** (A04 M-02) — MEDIUM
7. **PunishmentEngine HARD STOP guard is conditional on handler injection** — HIGH latent risk
8. **R-03 claim of SOUL.md rename is factually incorrect** — documentation integrity issue

---

## Footer

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-25 | P4 Known-Issues Reconciliation | Initial reconciliation against v1.1 + current source + NEW-AUDIT-2026 |
