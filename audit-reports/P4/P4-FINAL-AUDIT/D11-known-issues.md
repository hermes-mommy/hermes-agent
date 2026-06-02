# D11 — Known Issues Documentation Audit: P4 Persona Engine

> **Dimension**: D11 — Known Issues Documentation
> **Scope**: P4 Persona Engine (STEP-P4-001 through STEP-P4-023)
> **Date**: 2026-06-02
> **Auditor**: Guinevere (autonomous audit agent)
> **Method**: Full document review + source code verification
> **Documents reviewed**: PROGRESS.md, CHECKLIST.md, batch-plan-001-023.md, D02-code-quality.md, D04-tests-safety.md, all 9 P4-FINAL-AUDIT reports

---

## Overall Verdict: **FAIL** — 6 of 11 issues lack documentation or remediation plan

| Category | Count | Status |
|---|---|---|
| Fully documented with remediation | **1** | ✅ |
| Partially documented (mentioned but incomplete) | **4** | ⚠️ |
| Undocumented | **6** | ❌ |

---

## Issue Inventory

---

### Issue #1: 14 pre-existing errors in `test_hard_stop_model.py` (hardcoded Linux path)

| Field | Value |
|---|---|
| **Severity** | HIGH |
| **Classification** | Known limitation (VPS-only deployment) |
| **Root cause** | `src/core/services/prompt_loader.py` line 16: `SYSTEM_PROMPT_PATH = Path("/home/guinevere/config/hermes/system-prompt.md")` — hardcoded VPS path. `tests/smoke/conftest.py` line 9: same path. When `test_hard_stop_model.py` imports `prompt_loader`, it inherits this path, causing 14 collection/import errors on non-VPS environments (Windows, CI). |
| **Files affected** | `src/core/services/prompt_loader.py:16`, `tests/smoke/conftest.py:9`, `tests/safety/test_hard_stop_model.py` (fixture imports prompt_loader) |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| PROGRESS.md | ✅ YES | Line 193: "1449 tests passed, 0 failed (14 pre-existing errors in `test_hard_stop_model.py` unrelated to P4)." |
| CHECKLIST.md | ❌ NO | No mention of pre-existing errors or path issue. |
| batch-plan caveats | ❌ NO | Section 14 does not mention this. |
| D04-tests-safety.md | ⚠️ PARTIAL | Notes `sys.path.insert(0, "src")` is fragile (F3), but does not mention the hardcoded `/home/guinevere` path as the underlying cause. |

**Remediation plan**: ❌ **NONE documented.** Should use `os.environ.get("SYSTEM_PROMPT_PATH", "/home/guinevere/config/hermes/system-prompt.md")` or `conftest.py` override.

---

### Issue #2: `drift_corrector.py` uses `db: Any` (3×) — should use TYPE_CHECKING-guarded AsyncSession

| Field | Value |
|---|---|
| **Severity** | LOW |
| **Classification** | Code quality advisory |
| **Root cause** | `drift_corrector.py` lines 104, 190, 272: `db: Any` parameters documented as "duck-typed AsyncSession" instead of using `TYPE_CHECKING`-guarded `AsyncSession` import. |
| **Files affected** | `src/persona/drift_corrector.py` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| D02-code-quality.md | ✅ YES | ADV-03 (lines 338–347): explicit recommendation to use `AsyncSession` from `sqlalchemy.ext.asyncio` with `TYPE_CHECKING` import, matching pattern in `streak_tracker.py` lines 33–34. |
| PROGRESS.md | ❌ NO | Not mentioned. |
| batch-plan caveats | ❌ NO | Not mentioned. |

**Remediation plan**: ✅ **YES** — D02 ADV-03 specifies exact fix: use `TYPE_CHECKING`-guarded import pattern from `streak_tracker.py`.

---

### Issue #3: `mood_persistence.py` has 2× `# type: ignore[assignment]` for SQLAlchemy JSONB

| Field | Value |
|---|---|
| **Severity** | LOW |
| **Classification** | Known limitation (SQLAlchemy JSONB untyped column) |
| **Root cause** | Lines 111, 265: `row.state_value` is a SQLAlchemy JSONB column returning `object` at runtime. The `# type: ignore[assignment]` suppression is the correct and minimal fix for this well-known SQLAlchemy limitation. |
| **Files affected** | `src/persona/mood_persistence.py:111, :265` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| D02-code-quality.md | ✅ YES | Criterion #6 (lines 20–21, 116–128): fully documented with justification, code example, and "documented-unavoidable" classification. |
| PROGRESS.md | ❌ NO | Not mentioned (expected — low severity). |

**Remediation plan**: ✅ **NONE NEEDED** — Accepted as-is. SQLAlchemy JSONB is a well-known limitation. The suppression is minimal, scoped (`[assignment]`), and properly documented.

---

### Issue #4: CHECKLIST.md §6.5 Rollback Test is unchecked (manual test)

| Field | Value |
|---|---|
| **Severity** | MEDIUM |
| **Classification** | Known gap (VPS-dependent manual test) |
| **Root cause** | CHECKLIST.md line 412: `- [ ] DELETE FROM persona.mood_states -> DELETE FROM persona.streaks -> ... -> systemctl restart guinevere-scheduler`. This is a manual VPS deployment test that requires running services. |
| **Files affected** | `CHECKLIST.md` §6.5 |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| CHECKLIST.md | ✅ YES (self-documenting) | The unchecked box itself IS the documentation — it transparently shows this has not been tested. |
| PROGRESS.md | ❌ NO | Not explicitly mentioned. |
| batch-plan caveats | ❌ NO | Rollback plan (§11) documents deletion steps but not the untested status. |

**Remediation plan**: ⚠️ **IMPLICIT** — Deferred to VPS deployment. Same pattern as P0–P3 rollback tests (all unchecked in CHECKLIST.md). No explicit remediation timeline.

---

### Issue #5: Dual safe-mode systems (HardStopHandler vs SafeModeController) not bridged

| Field | Value |
|---|---|
| **Severity** | HIGH |
| **Classification** | Known architectural limitation / technical debt |
| **Root cause** | `src/core/services/hard_stop_handler.py` (HardStopHandler — HARD STOP safe word detection) and `src/persona/safe_mode.py` (SafeModeController — D0-D4 distress detection) are two independent systems with no shared state, no bridge, and no mutual awareness. Tests verify cross-module integration via mock/duck-typing, but production code has no wiring. |
| **Files affected** | `src/core/services/hard_stop_handler.py`, `src/persona/safe_mode.py` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| batch-plan §5 Known State | ⚠️ PARTIAL | Lists both `hard_stop_handler.py` and `safe_mode.py` as existing code but does not flag the architectural gap. Collision scan says "Read-only, integrate via safe_mode.py" but no integration code exists. |
| D04-tests-safety.md | ⚠️ PARTIAL | Notes test overlap between `test_hard_stop_handler.py` and `test_hard_stop_comprehensive.py` but does not flag the production-code architectural gap. |
| PROGRESS.md | ❌ NO | Not mentioned. |
| CHECKLIST.md | ❌ NO | Not mentioned. |

**Remediation plan**: ❌ **NONE documented.** This is a significant architectural gap — HARD STOP safe word and D0-D4 distress are conceptually related safety mechanisms that should share state awareness.

---

### Issue #6: `cmd_mood.py` still shows "P4 not deployed" placeholders

| Field | Value |
|---|---|
| **Severity** | MEDIUM |
| **Classification** | Known limitation (integration deferred) |
| **Root cause** | `src/discord/cmd_mood.py` lines 75, 81: hardcoded placeholder strings `"⚠️ — 24h history (P4 not deployed)"` and `"⚠️ — Streak tracking (P4 not deployed)"`. P4 engine code exists but Discord command was not updated to use it. |
| **Files affected** | `src/discord/cmd_mood.py:75, :81` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| batch-plan caveats | ✅ YES | Caveat #5 (line 284): "Discord integration: P4 builds the engine only. Discord bot integration (cmd_mood, cmd_safeword) is deferred to future integration work." |
| PROGRESS.md | ❌ NO | Not mentioned. P4 is marked ✅ complete without noting the placeholder gap. |
| CHECKLIST.md | ❌ NO | Not mentioned. |

**Remediation plan**: ⚠️ **IMPLICIT** — Deferred to "future integration work" per batch-plan caveat #5. No explicit ticket, step number, or timeline.

---

### Issue #7: PunishmentEngine doesn't persist to PunishmentLog table

| Field | Value |
|---|---|
| **Severity** | HIGH |
| **Classification** | Missing feature / known limitation |
| **Root cause** | `src/persona/punishment_engine.py` operates entirely in-memory. The `PunishmentLog` table exists in `src/memory/models.py` but is never referenced by the engine. No DB import, no persist/write calls. Punishment state is lost on process restart. |
| **Files affected** | `src/persona/punishment_engine.py` (no reference to `PunishmentLog`), `src/memory/models.py` (table exists, unused by engine) |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| PROGRESS.md | ❌ NO | Not mentioned. P4-005 marked ✅ complete. |
| CHECKLIST.md | ❌ NO | Not mentioned. |
| batch-plan caveats | ❌ NO | Not mentioned. |
| Any audit report | ❌ NO | Not flagged in D01–D07. |

**Remediation plan**: ❌ **NONE documented.** The DB table exists but is dead code for the persona engine. This means punishment state cannot survive restarts.

---

### Issue #8: RewardEngine doesn't persist to RewardLog table

| Field | Value |
|---|---|
| **Severity** | MEDIUM |
| **Classification** | Missing feature / known limitation |
| **Root cause** | `src/persona/reward_engine.py` operates entirely in-memory. The `RewardLog` table exists in `src/memory/models.py` but is never referenced by the engine. Only one occurrence of "mood" in the file — a description string, not a DB operation. |
| **Files affected** | `src/persona/reward_engine.py` (no reference to `RewardLog`), `src/memory/models.py` (table exists, unused by engine) |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| PROGRESS.md | ❌ NO | Not mentioned. P4-006 marked ✅ complete. |
| CHECKLIST.md | ❌ NO | Not mentioned. |
| batch-plan caveats | ❌ NO | Not mentioned. |
| Any audit report | ❌ NO | Not flagged in D01–D07. |

**Remediation plan**: ❌ **NONE documented.** Same pattern as Issue #7.

---

### Issue #9: YandereEngine doesn't persist state (lost on restart)

| Field | Value |
|---|---|
| **Severity** | HIGH |
| **Classification** | Missing feature / known limitation |
| **Root cause** | `src/persona/yandere_fsm.py` has no persistence methods (`persist`, `save_state`, `restore_state`, `pickle`, `json.dump` — all absent). YandereLevel and escalation state exists only in process memory. On restart, the engine resets to Y4 baseline regardless of runtime state. |
| **Files affected** | `src/persona/yandere_fsm.py` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| PROGRESS.md | ❌ NO | Not mentioned. P4-004 marked ✅ complete. |
| CHECKLIST.md | ❌ NO | Not mentioned. |
| batch-plan caveats | ❌ NO | Not mentioned. |
| Any audit report | ❌ NO | Not flagged in D01–D07. |

**Remediation plan**: ❌ **NONE documented.** Yandere level is a safety-critical state variable (Y4 baseline, Y5 ceiling). Losing it on restart means the engine always starts at Y4 even if the operator was at a different level.

---

### Issue #10: `bot.py` `on_message` doesn't run DistressDetector

| Field | Value |
|---|---|
| **Severity** | HIGH |
| **Classification** | Missing feature (deferred integration) |
| **Root cause** | `src/discord/bot.py` `_on_message_listener` (line 135–155) only calls `handle_safeword_message_async` for HARD STOP detection. The `on_message` method (line 292–315) only checks `handler.is_safe` for safe-mode blocking. Neither invokes `DistressDetector` from `src/persona/safe_mode.py` for D0-D4 distress analysis of incoming messages. |
| **Files affected** | `src/discord/bot.py:135–155, 292–315` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| batch-plan caveats | ⚠️ PARTIAL | Caveat #5 (line 284) says "Discord bot integration... is deferred to future integration work." But does not specifically mention DistressDetector or D0-D4 detection. |
| PROGRESS.md | ❌ NO | Not mentioned. |
| CHECKLIST.md | ❌ NO | Not mentioned. |

**Remediation plan**: ⚠️ **IMPLICIT ONLY** — Covered by generic "Discord integration deferred" caveat. No explicit step or plan for wiring DistressDetector into the message pipeline. This is a safety-relevant gap: D0-D4 distress detection should run on every user message to detect emotional distress.

---

### Issue #11: `prompt_loader` doesn't receive P4 mood value

| Field | Value |
|---|---|
| **Severity** | MEDIUM |
| **Classification** | Missing feature (deferred integration) |
| **Root cause** | `src/core/services/prompt_loader.py` accepts `mood: str = "Content"` parameter (lines 43, 123) and injects it into the system prompt (`## Current Mood: {mood}`). However, no caller from P4 or any Discord command passes the actual runtime mood value. The default "Content" is always used. |
| **Files affected** | `src/core/services/prompt_loader.py:43, :123` |

**Documentation status:**

| Document | Covered? | Detail |
|---|---|---|
| batch-plan §6 Collision Scan | ⚠️ PARTIAL | Lists `prompt_loader.py` as "No edits in P4 — integration deferred." Acknowledges deferral but does not flag the consequence (mood always defaults to "Content"). |
| PROGRESS.md | ❌ NO | Not mentioned. |
| CHECKLIST.md | ❌ NO | Not mentioned. |

**Remediation plan**: ⚠️ **IMPLICIT ONLY** — Deferred alongside other Discord integration work. No explicit step.

---

## Documentation Coverage Matrix

| # | Issue | PROGRESS.md | CHECKLIST.md | batch-plan | D02/D04 Audit | Overall Documented | Remediation Plan |
|---|---|---|---|---|---|---|---|
| 1 | Hardcoded Linux path | ✅ | ❌ | ❌ | ⚠️ | ⚠️ PARTIAL | ❌ NONE |
| 2 | `db: Any` (3×) | ❌ | ❌ | ❌ | ✅ | ✅ YES | ✅ YES |
| 3 | `# type: ignore` JSONB | ❌ | ❌ | ❌ | ✅ | ✅ YES | ✅ N/A (accepted) |
| 4 | Rollback test unchecked | ❌ | ✅ (self-doc) | ❌ | ❌ | ✅ YES | ⚠️ IMPLICIT |
| 5 | Dual safe-mode systems | ❌ | ❌ | ⚠️ | ⚠️ | ⚠️ PARTIAL | ❌ NONE |
| 6 | cmd_mood placeholders | ❌ | ❌ | ✅ | ❌ | ⚠️ PARTIAL | ⚠️ IMPLICIT |
| 7 | PunishmentEngine no persist | ❌ | ❌ | ❌ | ❌ | ❌ NO | ❌ NONE |
| 8 | RewardEngine no persist | ❌ | ❌ | ❌ | ❌ | ❌ NO | ❌ NONE |
| 9 | YandereEngine no persist | ❌ | ❌ | ❌ | ❌ | ❌ NO | ❌ NONE |
| 10 | on_message no DistressDetector | ❌ | ❌ | ⚠️ | ❌ | ⚠️ PARTIAL | ⚠️ IMPLICIT |
| 11 | prompt_loader no mood value | ❌ | ❌ | ⚠️ | ❌ | ⚠️ PARTIAL | ⚠️ IMPLICIT |

---

## Severity Summary

| Severity | Count | Issues |
|---|---|---|
| **HIGH** | 5 | #1 (hardcoded path), #5 (dual safe-mode), #7 (punishment persist), #9 (yandere persist), #10 (no DistressDetector) |
| **MEDIUM** | 4 | #4 (rollback unchecked), #6 (cmd_mood placeholders), #8 (reward persist), #11 (prompt_loader mood) |
| **LOW** | 2 | #2 (db: Any), #3 (type: ignore) |

---

## Critical Gaps

### Gap 1: P4 engine is entirely in-memory (Issues #7, #8, #9)

Three of the 11 known issues relate to **missing persistence** in P4 engines:
- PunishmentEngine → PunishmentLog table exists but unused
- RewardEngine → RewardLog table exists but unused
- YandereEngine → No persistence at all

This means **all persona state is lost on process restart**. The DB tables (`PunishmentLog`, `RewardLog`, `PersonaState`) were created in P3 but never wired to P4 engines. This is the most significant undocumented gap.

**Recommendation**: Create a dedicated tracking item (e.g., P4-INTEG-001) covering persistence wiring for all three engines.

### Gap 2: Discord integration surface entirely deferred (Issues #6, #10, #11)

Three issues relate to Discord bot not being wired to P4:
- `cmd_mood.py` still shows "P4 not deployed" placeholders
- `bot.py` `on_message` doesn't run DistressDetector
- `prompt_loader` never receives actual P4 mood value

The batch-plan caveat #5 acknowledges this generically ("Discord integration deferred"), but the safety-critical nature of Issue #10 (DistressDetector not running) means D0-D4 distress detection is **non-functional in production** — it exists as code but is never invoked on real messages.

**Recommendation**: Elevate Issue #10 to a safety-priority integration task, separate from cosmetic issues #6 and #11.

### Gap 3: Hardcoded VPS path blocks cross-environment testing (Issue #1)

The `/home/guinevere/config/hermes/system-prompt.md` path in `prompt_loader.py` line 16 is the root cause of 14 pre-existing test errors. While PROGRESS.md acknowledges the errors, no remediation plan exists. This blocks CI/CD adoption and cross-platform development.

**Recommendation**: Use environment variable with fallback: `Path(os.environ.get("SYSTEM_PROMPT_PATH", "/home/guinevere/config/hermes/system-prompt.md"))`.

### Gap 4: Dual safety architecture without bridge (Issue #5)

HardStopHandler (HARD STOP safe word) and SafeModeController (D0-D4 distress) are two independent safety systems with no shared state. In production, triggering HARD STOP via safe word does not automatically activate D0-D4 safe mode in the persona engine. The tests bridge them via mock objects, but the production code does not.

**Recommendation**: Create a `SafetyCoordinator` or wire `HardStopHandler` as a dependency of `SafeModeController` to ensure HARD STOP triggers full safe-mode activation.

---

## Classification Verification

| # | Classified As | Correct? | Notes |
|---|---|---|---|
| 1 | Known limitation | ✅ | VPS-only path is a known deployment constraint |
| 2 | Code quality advisory | ✅ | Non-blocking style issue |
| 3 | Known limitation | ✅ | SQLAlchemy JSONB is a well-known constraint |
| 4 | Known gap | ✅ | Manual test deferred to VPS |
| 5 | Known limitation | ⚠️ | Should be classified as **architectural debt** — higher priority |
| 6 | Known limitation | ✅ | Integration deferred by design |
| 7 | Missing feature | ⚠️ | Should be classified as **bug** — table exists, engine doesn't use it |
| 8 | Missing feature | ⚠️ | Should be classified as **bug** — table exists, engine doesn't use it |
| 9 | Missing feature | ⚠️ | Should be classified as **bug** — state lost on restart |
| 10 | Missing feature | ⚠️ | Should be classified as **safety bug** — D0-D4 non-functional |
| 11 | Known limitation | ✅ | Integration deferred by design |

---

## Recommendations

| Priority | Action | Scope |
|---|---|---|
| **P0 — IMMEDIATE** | Document Issues #7, #8, #9 in PROGRESS.md as known limitations with explicit "P4-INTEG" tracking item | PROGRESS.md |
| **P0 — IMMEDIATE** | Document Issue #10 (DistressDetector) as safety-priority integration gap | PROGRESS.md + CHECKLIST.md |
| **P0 — IMMEDIATE** | Document Issue #5 (dual safe-mode) as architectural debt | PROGRESS.md + ADR |
| **P1 — HIGH** | Add remediation plan for Issue #1 (env var fallback) | PROGRESS.md known-issues section |
| **P1 — HIGH** | Add remediation plan for Issues #7, #8, #9 (persistence wiring) | batch-plan or new integration plan |
| **P1 — HIGH** | Document Issue #10 as separate safety task, not bundled with cosmetic Discord work | batch-plan caveats |
| **P2 — MEDIUM** | Update batch-plan caveats to list all 11 issues explicitly | batch-plan §14 |
| **P3 — LOW** | Add Issues #7–#11 to CHECKLIST.md §17 Known Blockers | CHECKLIST.md |

---

## Conclusion

The P4 Persona Engine implementation is **functionally complete** at the unit/integration test level (1449 tests, 0 failures). However, the known-issues documentation has significant gaps:

- **6 of 11 issues** have no documentation in any primary tracking document (PROGRESS.md, CHECKLIST.md, or batch-plan caveats).
- **5 HIGH-severity issues** lack any remediation plan.
- **3 persistence bugs** (#7, #8, #9) are entirely undocumented — the DB tables exist but engines never use them.
- **1 safety bug** (#10) is buried under a generic "Discord integration deferred" caveat without highlighting that D0-D4 distress detection is non-functional in production.

The documentation that does exist is accurate where present (D02-code-quality.md, batch-plan caveats). The gap is **completeness**, not accuracy.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-02 | Guinevere (audit agent) | Initial D11 known-issues audit. |
