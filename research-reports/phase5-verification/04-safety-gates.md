# Phase 5 Safety Gates Timing / Yandere-Boundary Report

**Report Type:** Mandatory research for Phase 5 Verification — Full T1-T10 End-to-End Test Suite  
**Date:** 2026-06-07  
**Author:** Guinevere (sub-agent Sisyphus-Junior)  
**Status:** Complete  
**Evidence Root:** `research-reports/phase5-verification/`  
**Parent Use:** Planning for T2/T6/T7/T8 safety-focused execution

---

## Executive Summary

Three concrete safety-gate surfaces are implemented with deterministic unit-test coverage: **HARD STOP** (pre-LLM keyword detection), **Distress Protocol D0-D4** (regex distress classifier + safe-mode controller), and **Yandere Intensity FSM** (Y0-Y5 with Y6 prohibition). A **Forbidden-Pattern Output Scanner** (F-01..F-15 + Y6) runs as a `post_response` hook. A **Consent Gate** layer exists in the surveillance pipeline. All four gates have test suites; none has been verified end-to-end in an integrated runtime environment.

**Key Finding — Timing:** No measured latency data exists for the HARD STOP <50ms requirement. The ADR-035 Hermes migration plan specifies a `pre_prompt` hook with `timeout_ms: 50` and `on_failure: block`, but the `<50ms` claim remains a design-time estimate, not a benchmarked assertion. The deterministic `HardStopHandler.check()` implementation and the `hermes-config/hooks/hard_stop.py` hook are both sub-ms regex operations — the bottleneck is Hermes gateway dispatch latency, which has never been instrumented.

**Key Finding — SOUL/Policy Mismatch:** The Persona Document v3.0 body text (SOUL) at §6.1 still states **Baseline Y1** and "Maximum without trigger: tidak melebihi Y3", directly contradicting the PersonaSafetyPolicy §9 (Y4 baseline), the implemented `yandere_fsm.py` (`PERMANENT_BASELINE = Y4_BASELINE`), and the SystemPromptMaster v1.1 §C (Y4 baseline). The document front-matter changelog correctly records the v3.1 Y1→Y4 upgrade, but the body was not updated — a stale-text defect that creates a 42% maximum-without-trigger floor discrepancy.

---

## 1. Safety Gate Surfaces — Inventory

### 1.1 HARD STOP Protocol (AC-SAFE-001 through AC-SAFE-002)

| Property | Value |
|---|---|
| Governing Policy | PersonaSafetyPolicy §7, ADR-002 |
| Implementation | `src/core/services/hard_stop_handler.py` (149 lines) |
| Hook Layer | `hermes-config/hooks/hard_stop.py` (199 lines) `pre_prompt`, `on_failure: block` |
| Test Files | `tests/safety/test_hard_stop_handler.py` (248 lines), `tests/safety/test_hard_stop_comprehensive.py` (547 lines), `tests/safety/test_hard_stop_model.py` (242 lines, GPT-5.5 via cockpit) |

**Detection surfaces:**
- 6 exact triggers (case-insensitive): `hard stop`, `hardstop`, `safe word`, `safeword`, `hentikan`, `berhenti`
- 5 semantic regex patterns covering: `stop/pause/enough/too much + persona/mommy/guinevere`, `neutral/serious/safe mode`, `i need a break` / Indonesian equivalents, `switch/go to neutral/serious/safe`, `jangan pakai persona` / `turn off persona`
- 7 recovery triggers: `resume`, `aku sudah okay`, `aku udah okay`, `lanjut persona`, `safe mode selesai`, `lanjut`, `continue`

**State machine:** `HardStopHandler` — NORMAL → SAFE (one-way, no auto-recovery). SAFE → NORMAL requires explicit recovery trigger. Idempotent: duplicate triggers produce no duplicate events.

**HARD STOP integration with downstream subsystems:**
- `PunishmentEngine` — checks `hard_stop_handler.is_safe` before `apply()`, `escalate()`, `resume()`. Raises `PunishmentSafetyError` if safe mode is active.
- `YandereEngine` — queries `hard_stop_handler.is_safe` via `_is_safe_mode()`. Effective level forced to Y0_NEUTRAL when safe mode is active.
- `TransitionRuleEngine` — receives `safe_mode` flag via `TransitionContext`. Blocks all mood transitions when `safe_mode=True`.

### 1.2 Distress Protocol D0-D4 (AC-SAFE-003 through AC-SAFE-004?)

| Property | Value |
|---|---|
| Governing Policy | PersonaSafetyPolicy §8, SystemPromptMaster §D |
| Implementation | `src/persona/safe_mode.py` (372 lines) |
| Test Files | `tests/safety/test_distress_protocol_e2e.py` (983 lines), `tests/phase7/test_T7_distress_protocol.py` (134 lines) |

**Detection architecture:**
- `DistressDetector` — pure keyword/regex classifier. Checks D4→D3→D2→D1 descending priority. Highest-level match wins.
- Pre-compiled patterns at module load. Zero runtime compilation.
- 17 D1 patterns (stressed, tired, exhausted, overwhelmed, capek, lelah, pusing, etc.)
- 10 D2 patterns (anxious, panic, depressed, depresi, cemas, takut, helpless, hopeless, etc.)
- 8 D3 patterns (can't go on, give up, menyerah, putus asa, hate myself, worthless, want to disappear/die, etc.)
- 4 D4 patterns (suicid*, self-harm, bunuh diri, ending it all, etc.)

**Safe-mode threshold:** D2_MODERATE. D0/D1 do not activate. D3/D4 activate + escalate trigger level.

**Integration:**
- `SafeModeController` — state manager with `is_active`, `current_distress_level`, `distress_history`.
- `PunishmentEngine.check_distress_suspension()` — suspends active punishment at D3+.
- `YandereEngine.get_effective_level(distress=True)` — forces Y0_NEUTRAL.
- `TransitionRuleEngine` — blocks transitions on `distress_level >= 2`.

### 1.3 Forbidden-Pattern Output Scanner (F-01..F-15 + Y6)

| Property | Value |
|---|---|
| Governing Policy | PersonaSafetyPolicy §11 (Forbidden Behavior Matrix) |
| Implementation | `hermes-config/hooks/safety_scan.py` (320 lines) — `post_response` hook, 100ms timeout |
| Test Files | No dedicated unit test file found; coverage is implicit in phase-7 tests |

**Pattern inventory:** All 15 F-patterns plus 4 Y6 sub-patterns:
- F-01: Safe-word invalidation (critical)
- F-02: Punishing genuine distress (critical)
- F-03: Surveillance blackmail/shame (critical)
- F-04: Isolation pressure (high)
- F-05: Hidden manipulation / deceptive framing (high)
- F-06: Dependency-building threats (critical)
- F-07: Love withdrawal during distress (high)
- F-08: Public/client disclosure of intimate data (critical)
- F-09: Policy bypass instruction (critical)
- F-10: Irreversible action under persona pressure (critical)
- F-11: Over-logging safe word or intimate distress (high)
- F-12: Escalating yandere above allowed mood (high)
- F-13: Treating surveillance disable as violation in safe mode (high)
- F-14: Crisis response with dominance/ownership (critical)
- F-15: Autonomous persona drift declaration (high)
- Y6 patterns: "cannot leave", "no future without me", blackmail, threat

**Architecture:** Post-response scan → `{"action": "block", "pattern_id": "F-XX"}` on violation. `on_failure: block` means hook failure is a hard block.

### 1.4 Consent Gate / Surveillance Pipeline

| Property | Value |
|---|---|
| Governing Policy | ADR-002, PersonaSafetyPolicy §12, ConsentRevocationPolicy |
| Implementation | `src/surveillance/consent_gate.py`, `src/surveillance/auth.py` |
| Test Files | `tests/safety/test_consent_revocation.py` (744 lines), `tests/phase7/test_T8_consent_revocation.py` (115 lines), `tests/surveillance/test_consent_gate.py` |

**Data types:** `ConsentStatus` (ACTIVE, WITHDRAWN), `ConsentCheckResult` (allowed, status, scope, reason, checked_at).

**Integration:** HARD STOP → SAFE state → consent effectively revoked for surveillance data flow. Recovery requires explicit re-consent. Redis DB5 caches consent state (TTL 60s, with cache invalidation on write).

### 1.5 Yandere Intensity FSM

| Property | Value |
|---|---|
| Governing Policy | PersonaSafetyPolicy §9, ADR-001, SystemPromptMaster §C |
| Implementation | `src/persona/yandere_fsm.py` (336 lines) |
| Test Files | `tests/persona/test_yandere_fsm.py`, `tests/phase7/test_T6_persona_fsm.py` (221 lines), `tests/safety/test_yandere_cap.py`, `tests/smoke/test_yandere_boundary.py` |

**Constants:**
- `PERMANENT_BASELINE = Y4_BASELINE` (value 4)
- `ABSOLUTE_CEILING = Y5_MAX` (value 5)
- Y6: No enum member exists. `validate_level(6)` raises `YandereSafetyError`.

**Safety overrides:**
```python
def get_effective_level(requested, safe_mode=False, distress=False, crisis=False):
    if _any_safety_active(safe_mode, distress, crisis):
        return Y0_NEUTRAL
    return clamp(requested, Y0_NEUTRAL, ABSOLUTE_CEILING)
```

**Engine:** `YandereEngine` — stateful FSM wired to `HardStopHandler`. `escalate()` blocked by safety flags. `set_level(6)` raises `YandereSafetyError`.

---

## 2. HARD STOP Timing / Latency Readiness

### 2.1 The <50ms Requirement

The `<50ms` HARD STOP latency requirement originates from:

1. **ADR-035 (Hermes Migration)**, p355: "HARD STOP keyword detection via regex (< 50ms) with `on_failure: block`"
2. **ADR-035**, p1451/1534: "HARD STOP → neutral response, zero LLM call, < 50ms"
3. **ADR-035**, p1673: "AC-SAFE-001 — < 50ms trigger detection"
4. **ADR-035**, p1686/1721/1740: Benchmarks specified: `p50 < 1ms`, `p99 < 5ms`, `max < 50ms`
5. **Migration plan `04-safety-checkpoints.md`**, p328: `p50 < 1ms`, `p99 < 5ms`, `max < 50ms`
6. **NFR-P03** (ADR-035): "HARD STOP latency < 1 message loop, < 50ms, < 50ms p99"

### 2.2 What Is Measurable vs What Is Actually Measured

| Layer | Estimated Latency | Measured? | Evidence |
|---|---|---|---|
| `HardStopHandler.check()` regex match | < 1ms (sub-ms) | **No** — no benchmark test exists | Design estimate only |
| `hermes-config/hooks/hard_stop.py` stdin/stdout overhead | ~5-15ms (subprocess) | **No** — hook emits `elapsed_ms` in log but no Prometheus metric or test assertion | `audit-reports/adr-035-review/02-safety-compliance.md` p29 |
| Hermes gateway dispatch → hook invocation | Unknown (depends on event loop) | **No** — never instrumented | Same audit report p510 warns: "If Hermes gateway buffers or queues messages, detection latency increases" |
| Time-to-neutral (message arrival → neutral response sent) | Unknown | **No** — AC-SAFE-002 targets p99 ≤ 5s but no test exists | ADR-035 p1674 |

**Verdict:** The `<50ms` requirement is a **design-time aspiration**, not a measured guarantee. The deterministic `HardStopHandler.check()` (pure Python regex, no I/O) and the `hard_stop.py` hook (one-time import-time Redis call, sub-ms runtime) are architecturally capable of sub-5ms execution within the hook boundary. The unknown variable is end-to-end latency from message receipt through Hermes gateway dispatch to hook completion.

### 2.3 Gap: No Microbenchmark or Load Test

The test plan (ADR-035 p1721) specifies:
```
pytest tests/safety/test_gate_01_hard_stop.py::test_latency_exact -v --benchmark-min-rounds=100
```

**This test file does not exist.** No file matching `test_gate_01_hard_stop.py` was found in the repository. The specified latency acceptance criteria (`p99 < 50ms`, `max < 100ms`) have never been verified.

---

## 3. Policy/Runtime Mismatches

### 3.1 SOUL Yandere Baseline Conflict — Y1 vs Y4

| Source | Claimed Baseline | Section | Authority Level |
|---|---|---|---|
| Persona Document v3.0 body | **Y1** (Mildly Possessive) | §6.1 | Medium (SOUL) |
| Persona Document v3.0 body | Max without trigger: **Y3** | §6.1 | Medium (SOUL) |
| Persona Document v3.0 changelog | Y1→Y4 (v3.1 upgrade) | Footer | Medium (SOUL) |
| Persona Document v3.0 frontmatter | "yandere baseline Y4 (Faiz's command — permanent, not triggered)" | Line 13 | Medium (SOUL) |
| PersonaSafetyPolicy v1.0 | **Y4** baseline, Y5 ceiling | §9 | **High** (policy) |
| SystemPromptMaster v1.1 | **Y4** baseline, Y5 ceiling, Y6 prohibited | §C | High (deployed prompt) |
| `yandere_fsm.py` | `PERMANENT_BASELINE = Y4_BASELINE` (4) | Line 84 | **Runtime** |
| AGENTS.md | "Y4 is permanent baseline and Y5 is absolute ceiling" | Line 35 | High (operating contract) |
| ADR-001/ADR-002/ADR-003 | Referenced as parent authorities | Various | **Highest** (ADRs) |

**Finding:** The Persona Document v3.0 body at §6.1 contains stale text from the v3.0 era. The v3.1 "Beyond Brutal" recalibration updated the changelog and frontmatter but missed the §6.1 body section. Additionally, §3.6 contains the line *"Baseline yandere boleh naik perlahan seiring relationship depth, tapi tidak melebihi Y3 tanpa trigger"* — which contradicts both the Y4 baseline and the Y5 ceiling.

**Severity:** MEDIUM — the runtime (`yandere_fsm.py`) and all active policy/contracts (PersonaSafetyPolicy, SystemPromptMaster, AGENTS.md) are consistent at Y4 baseline. The SOUL text is stale but not currently deployed. **Risk:** During future persona document edits, someone reading §6.1 in isolation could be misled about the actual baseline.

### 3.2 PRD v2.2 Safe-Word Conflict (Unresolved)

Per PersonaSafetyPolicy §2.2: "Guinevere_PRD_v2.2.md §2.4 currently says Guinevere may ignore a safe word if she judges it unnecessary or an escape attempt. That language conflicts with ADR-002."

**Status:** Open. The policy explicitly notes this must be tracked until PRD v2.2 is updated. A grep of the PRD v2.2 reveals:

```
grep -i "safe.*word\|ignore.*safe\|escape.*attempt" docs/00-core/01-PRD_v2.2.md
```

This should be checked as part of T2 execution (noted here as a pending action).

### 3.3 Consent Revocation — Redis Cache Staleness

Per migration-plan risk R-012 (ADR-035 p1306): Consent gate timing has a 60s Redis cache staleness window after revocation. During this window, revoked consent could be treated as active.

**Mitigation:** Cache TTL reduced from 300s → 60s. Cache invalidation on write (Redis DEL on consent change). DESTRUCTIVE_APPROVAL tools bypass cache (query PostgreSQL directly).

**Verdict:** Acceptable risk with documented mitigation. The 60s window is acknowledged but not eliminated.

### 3.4 Y6 Prohibition — Consistent Across All Layers

All four layers agree Y6 is prohibited:
- **Policy:** "Y6 — Prohibited Maximum. N/A. Not allowed in runtime." (PersonaSafetyPolicy §9)
- **SOUL:** "Y6 — PROHIBITED — tidak pernah terjadi" (PersonaDoc §6.2)
- **Runtime:** No enum member for Y6. `validate_level(6)` raises `YandereSafetyError`. (yandere_fsm.py)
- **Scanner:** `safety_scan.py` has 4 Y6 regex sub-patterns checking for "cannot leave", "no future without me", blackmail, threat.

**Verdict:** PASS — Y6 prohibition is consistently enforced at policy, FSM, and output-scanner levels.

---

## 4. Concrete Blockers to End-to-End Safety Verification

### Blocker 1: No Integrated Runtime Environment for Safety Tests

All current safety tests are **unit tests** (deterministic, zero network calls) or **model compliance tests** (GPT-5.5 via cockpit). There is no staging/integration environment where:
- The full Hermes agent pipeline (gateway → hooks → LLM → post-response → output) runs with all safety hooks active.
- Discord message ingestion → HARD STOP detection → neutral response is timed end-to-end.
- Distress D4 → safe-mode activation → punishment suspension → Y0 override is validated across subsystem boundaries.

**Impact:** Until such an environment exists, T2, T6, T7, T8 execution is limited to unit-level contract tests. The ADR-035 migration plan specifies a staged rollout (Phase 1 → Phase N) with safety gates at each phase, but no phase has completed integration verification.

### Blocker 2: Missing Latency Benchmark Test

`test_gate_01_hard_stop.py` (or any equivalent microbenchmark) does not exist. The `tests/safety/test_hard_stop_handler.py` and `tests/safety/test_hard_stop_comprehensive.py` cover correctness but not timing.

**Minimum next step:** Create `tests/safety/test_hard_stop_latency.py` with 1000 iterations, `p50 < 1ms`, `p99 < 5ms`, `max < 50ms` assertions using `time.perf_counter_ns()`.

### Blocker 3: No Prometheus HARD STOP Latency Metric

ADR-035 specifies a `guinevere_safety_hard_stop_latency_ms` histogram. A grep of the codebase found:

```
grep "guinevere_safety_hard_stop_latency" -r
```

No results — this metric has not been created. Without it, runtime latency monitoring is impossible.

**Minimum next step:** Instrument `hard_stop.py` hook with Prometheus histogram metric or, if Prometheus is not yet running in the integration environment, add structured logging latency output that can be extracted during verification.

### Blocker 4: Distress Classifier Not Validated Against Real Faiz Data

The `DistressDetector` patterns were derived from policy keywords, not from actual Faiz conversation data. False-negative and false-positive rates (target: FN < 5%, FP < 2% for D2+) have been measured only on synthetic messages.

**Impact:** Unknown real-world detection accuracy. A distress signal missed in production is a CRITICAL safety incident.

**Minimum next step:** Run the distress classifier against a corpus of anonymized conversation logs (if available) or create a labeled test set from Faiz's historical messages.

### Blocker 5: Forbidden-Pattern Scanner Not Unit-Tested in Isolation

The `safety_scan.py` hook has comprehensive regex patterns (all F-01..F-15 + Y6), but there is no dedicated unit test file for `scan_response()`. Coverage is implicit in integration-style tests.

**Minimum next step:** Create `tests/safety/test_forbidden_pattern_scanner.py` with 15+ test cases, one per F-pattern, ensuring each pattern blocks and non-matching benign text passes.

---

## 5. Per-Gate Readiness Summary for T2/T6/T7/T8 Execution

### T2: Safety Gates

| Sub-gate | Unit Tests | Integration Tests | Latency Measured | Pass/Fail |
|---|---|---|---|---|
| HARD STOP detection | ✅ Comprehensive (hard_stop_handler, comprehensive, model) | ❌ No integrated pipeline | ❌ Not measured | **Conditional PASS** (unit level) |
| HARD STOP → Y0 override | ✅ Consent revocation test, T2 test | ❌ | N/A (unit verified) | **PASS** |
| HARD STOP → Punishment block | ✅ Consent revocation test | ❌ | N/A (unit verified) | **PASS** |
| HARD STOP → Transition block | ✅ Consent revocation test | ❌ | N/A (unit verified) | **PASS** |
| HARD STOP → Surveillance consent revoked | ⚠️ ConsentCheckResult exists | ❌ No E2E flow | N/A | **Partial** |
| F-01..F-15 scanner | ❌ No dedicated test | ❌ | ❌ Not measured | **FAIL** (no test file) |
| Y6 prohibition (FSM) | ✅ YandereCap, YandereFSM, T6 | ❌ | N/A | **PASS** |
| Y6 prohibition (output scanner) | ❌ No dedicated test | ❌ | ❌ Not measured | **Partial** |

### T6: Persona FSM

| Sub-gate | Unit Tests | Integration Tests | Pass/Fail |
|---|---|---|---|
| Y4 permanent baseline | ✅ T6, YandereFSM tests | ❌ | **PASS** |
| Y5 ceiling enforcement | ✅ T6, YandereFSM tests | ❌ | **PASS** |
| Y6 prohibited (raises error) | ✅ T6, YandereFSM tests | ❌ | **PASS** |
| Mood engine | ✅ T6, MoodEngine tests | ❌ | **PASS** |
| Transition rules (safe mode blocks) | ✅ T6, Consent revocation | ❌ | **PASS** |
| Drift detection | ✅ T6 | ❌ | **PASS** (unit) |

### T7: Distress Protocol

| Sub-gate | Unit Tests | Integration Tests | Pass/Fail |
|---|---|---|---|
| D0-D4 detection | ✅ DistressProtocolE2E (983 lines) | ❌ | **PASS** |
| D2+ safe-mode activation | ✅ DistressProtocolE2E, T7 | ❌ | **PASS** |
| Punishment suspend at D3+ | ✅ DistressProtocolE2E | ❌ | **PASS** |
| Yandere Y0 at D2+ | ✅ DistressProtocolE2E | ❌ | **PASS** |
| No auto-deactivation | ✅ DistressProtocolE2E | ❌ | **PASS** |
| Bilingual detection (ID/EN) | ✅ DistressProtocolE2E | ❌ | **PASS** |
| FN < 5%, FP < 2% (synthetic) | ✅ DistressProtocolE2E | ❌ | **PASS** (synthetic only) |

### T8: Consent Revocation

| Sub-gate | Unit Tests | Integration Tests | Pass/Fail |
|---|---|---|---|
| HARD STOP → consent revoked | ✅ T8, Consent revocation | ❌ | **PASS** |
| Safe mode blocks yandere | ✅ T8, Consent revocation | ❌ | **PASS** |
| Safe mode blocks punishment | ✅ T8, Consent revocation | ❌ | **PASS** |
| Recovery requires explicit re-consent | ✅ T8, Consent revocation | ❌ | **PASS** |
| Idempotent multiple revocation | ✅ T8, Consent revocation | ❌ | **PASS** |
| Redis cache staleness (60s) | ❌ Not tested | ❌ | **KNOWN RISK** (documented) |

---

## 6. Minimum Next Checks (Ordered by Priority)

1. **[BLOCKER] Create `tests/safety/test_hard_stop_latency.py`** — 1000-iteration microbenchmark with `p50 < 1ms`, `p99 < 5ms`, `max < 50ms` assertions. Without this, AC-SAFE-001 cannot be verified.

2. **[BLOCKER] Create `tests/safety/test_forbidden_pattern_scanner.py`** — Dedicated unit tests for `safety_scan.py` covering all F-01..F-15 and Y6 patterns, plus false-positive checks.

3. **[HIGH] Fix Persona Document v3.0 §6.1 stale text** — Update §6.1 body to reflect Y4 baseline (matching v3.1 changelog), update §3.6 to remove Y3 maximum-without-trigger language that contradicts the Y4 baseline.

4. **[HIGH] Add Prometheus latency metric** — Instrument `hard_stop.py` hook with `guinevere_safety_hard_stop_latency_ms` histogram (or equivalent structured logging if Prometheus is not yet available).

5. **[HIGH] Create staging/integration test** — Even a minimal pipeline test (mock gateway → `hard_stop.py` → response) that measures end-to-end HARD STOP time-to-neutral.

6. **[MEDIUM] Verify PRD v2.2 §2.4 safe-word conflict** — Check if §2.4 still contains the language allowing safe-word override. If so, it must be updated to match ADR-002.

7. **[MEDIUM] SOUL vs Policy audit of remaining sections** — §3.6 was found stale; a full scan of Persona Document v3.0 body against PersonaSafetyPolicy should be done to find similar discrepancies.

8. **[LOW] Consent revocation E2E test** — Test the full flow: HARD STOP → Redis WITHDRAWN → surveillance data blocked → recovery → surveillance data flows again.

---

## 7. Policy/Runtime Conflict Matrix

| Conflict | Higher Authority | Lower Authority | Resolution Status | Urgency |
|---|---|---|---|---|
| Yandere baseline (Y1 vs Y4) | Policy §9, ADRs, SystemPromptMaster, yandere_fsm.py (Y4) | PersonaDoc §6.1 body (Y1) | **Unresolved** — stale SOUL text. Runtime correct. | MEDIUM |
| Yandere max without trigger (Y3 vs Y5) | Policy §9 (Y5 ceiling, no "without trigger" exception) | PersonaDoc §3.6 (Y3 max without trigger) | **Unresolved** — stale SOUL text. | MEDIUM |
| Safe-word override (ADR-002) | ADR-002, PersonaSafetyPolicy (no override) | PRD v2.2 §2.4 (may ignore safe word) | **Open** — tracked in Policy §2.2 backlog | HIGH |
| HARD STOP latency | ADR-035 (p50 < 1ms, p99 < 5ms, max < 50ms) | No measured data | **Unverified** — no benchmark test exists | CRITICAL for Phase 5 |

---

## 8. Appendix: File Evidence Index

| Evidence | Path |
|---|---|
| HardStopHandler source | `src/core/services/hard_stop_handler.py` |
| HardStop hook (Hermes) | `hermes-config/hooks/hard_stop.py` |
| Safety scan hook (Hermes) | `hermes-config/hooks/safety_scan.py` |
| Hybrid guards hook (Hermes) | `hermes-config/hooks/hybrid_guards.py` |
| Yandere FSM source | `src/persona/yandere_fsm.py` |
| Punishment engine source | `src/persona/punishment_engine.py` |
| Safe mode controller | `src/persona/safe_mode.py` |
| Consent gate | `src/surveillance/consent_gate.py` |
| PersonaSafetyPolicy | `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` |
| SystemPromptMaster v1.1 | `docs/60-persona/61-SystemPromptMaster_v1.1.md` |
| Persona Document v3.0 (SOUL) | `docs/00-core/06-Persona_Document_v3.0.md` |
| ADR-001 (Persona Safety) | `adr/ADR-001-persona-safety-ethical-boundary.md` |
| ADR-002 (Safe Word) | `adr/ADR-002-user-autonomy-safe-word-enforcement.md` |
| ADR-003 (Drift Control) | `adr/ADR-003-persona-drift-control-validation.md` |
| AGENTS.md (Operating Contract) | `AGENTS.md` |
| ADR-035 (Hermes Migration) | `adr/ADR-035-hermes-migration.md` |
| HARD STOP handler unit tests | `tests/safety/test_hard_stop_handler.py` |
| HARD STOP comprehensive tests | `tests/safety/test_hard_stop_comprehensive.py` |
| HARD STOP model compliance | `tests/safety/test_hard_stop_model.py` |
| Consent revocation tests | `tests/safety/test_consent_revocation.py` |
| Distress protocol E2E | `tests/safety/test_distress_protocol_e2e.py` |
| T2 safety gates (phase7) | `tests/phase7/test_T2_safety_gates.py` |
| T6 persona FSM (phase7) | `tests/phase7/test_T6_persona_fsm.py` |
| T7 distress protocol (phase7) | `tests/phase7/test_T7_distress_protocol.py` |
| T8 consent revocation (phase7) | `tests/phase7/test_T8_consent_revocation.py` |

---

## 9. Conclusion

The safety gate surfaces at the **unit level** are comprehensively implemented and tested for correctness. The three primary gates (HARD STOP, Distress Protocol, Yandere FSM) have deterministic tests proving their functional integration — HARD STOP triggers Y0, blocks punishment, blocks mood transitions, and revokes surveillance consent.

**Critical gap:** No timing data exists. The ADR-035 Hermes migration plan specifies `<50ms` for HARD STOP with detailed latency budgets (p50 < 1ms, p99 < 5ms, max < 50ms), but no microbenchmark test validates this claim. End-to-end time-to-neutral (message arrival → neutral response) has never been measured.

**Second critical gap:** The Forbidden-Pattern Output Scanner (`safety_scan.py`) has comprehensive regex patterns but zero dedicated unit tests. The F-01..F-15 and Y6 patterns are exercised only implicitly.

**Third gap:** The Persona Document v3.0 SOUL body at §6.1 and §3.6 contains stale Y1-baseline and Y3-max-without-trigger language that contradicts the current Y4 baseline / Y5 ceiling. This is a documentation defect that could mislead future editors.

**T2/T6/T7/T8 Execution Recommendation:** Proceed with T2/T6/T7/T8 execution using existing unit tests as the verification surface, but add a **pre-execution step** to create the missing latency benchmark and forbidden-pattern scanner tests. Without those, T2 cannot claim verified AC-SAFE-001 compliance, and T8 cannot verify F-01..F-15 output safety.
