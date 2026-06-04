# ADR-035 Safety Compliance Review

**Reviewer:** REVIEWER 2 — Safety Compliance  
**Date:** 2026-06-04  
**Authority Documents:** PersonaSafetyPolicy v1.0, ADR-001, ADR-002, ADR-003  
**Evidence Base:** 14 source files fully read, 4 research reports reviewed

---

## Summary

ADR-035 proposes a hybrid Hermes migration with a 4-layer defense-in-depth safety architecture (SOUL.md + 6 hooks + `GuinevereSafetyPlugin` + drift detector). The architecture design is sound in principle — hooks configured `on_failure: block`, plugin `critical: true`, deterministic logic ported verbatim. However, **critical gaps exist between the code samples in the ADR and the actual safety implementations** (distress patterns reduced from 14→6, forbidden patterns reduced from 15→5), and several PersonaSafetyPolicy requirements have no explicit mapping. Phase 1 gate criteria are comprehensive but some test gates don't match the implementation phase they gate. The shadow mode runbook (Appendix D) is adequate but the YandereEngine in the listed plugin code contains the enum member `Y6_UNSAFE = 6` — this is a safety regression from the current implementation where Y6 has NO enum member and any construction raises `YandereSafetyError`.

## Verdict: CONDITIONAL

The architecture can be approved IF AND ONLY IF the following are addressed before Phase 1 implementation begins:

1. **Fix Y6_UNSAFE enum member** — remove it, match current implementation where Y6 has no member
2. **Fill distress pattern gap** — port ALL 14 current patterns, not just 6  
3. **Fill forbidden pattern gap** — port ALL 15 F-01 through F-15 patterns
4. **Add AC-SAFE test for recovery triggers** — verify `resume`/`aku sudah okay` works after HARD STOP
5. **Add pre-on_message timing shift validation** — prove the `pre_prompt` hook timing is functionally equivalent

## AC-SAFE Verification Table

| AC-SAFE | Description | Current Impl | Proposed Mapping | Regression Risk | Status |
|---------|-------------|-------------|-----------------|-----------------|--------|
| **AC-SAFE-001** | HARD STOP triggers neutral mode (100%) | `hard_stop_handler.py` — `check()` with EXACT_TRIGGERS + SEMANTIC_PATTERNS, pre-on_message listener | `pre_prompt` hook (`hard_stop.py`) + plugin `on_message()` dual-layer. `on_failure: block`. | **MEDIUM** — Timing shift: current `_on_message_listener` fires BEFORE `on_message`; `pre_prompt` fires after message accepted but before LLM. ADR acknowledges shift but calls it "functionally equivalent." Subprocess spawn adds 5-15ms overhead. Recovery triggers (`resume`, `aku sudah okay`) not mapped in hook code sample — current impl has `check_recovery()`. | **CONDITIONAL PASS** |
| **AC-SAFE-002** | Time-to-neutral p99 ≤ 5s | `check()` is sync regex (microseconds); `get_neutral_response()` returns constant string | Hook latency measured: subprocess 5-15ms + regex <1ms. p99 ≤ 5000ms envelope. | **LOW** — Measurable latency budget. Hook has `timeout_ms: 50` → if exceeded, `on_failure: block` kills pipeline. Acceptable. | **PASS** |
| **AC-SAFE-003** | Safe-word stops all persona escalation | `yandere_fsm.py` → `get_effective_level()` forces Y0; `punishment_engine.py` → raises `PunishmentSafetyError` when `is_safe`; `safe_mode.py` → `SafeModeController` | `GuinevereSafetyPlugin` — `self.safe_mode` boolean checked in `on_message()`, `on_response()`, `on_tool_call()`. ALL plugin methods required to check at entry. | **MEDIUM** — Dependency on developer discipline: every new plugin method must check `self.safe_mode`. One missed check = safety gap during HARD STOP. Plugin test suite must explicitly verify ALL methods. Acceptable with test enforcement. | **CONDITIONAL PASS** |
| **AC-SAFE-004** | D3/D4 distress false negatives = zero | `safe_mode.py` — 14 compiled regex patterns (D4: 4, D3: 3, D2: 3, D1: 4). D4→D1 priority. Bilingual ID/EN. | Plugin `on_message()` distres detection with `_compile_distress_patterns()`. D4→D1 priority preserved. | **HIGH** — **PATTERN COUNT REGRESSION**: Current implementation has 14 patterns. ADR code sample (`_compile_distress_patterns`) has only 6 patterns (2 D4, 2 D3, 1 D2, 1 D1). This is a direct coverage reduction: `D4_EMERGENCY` drops from 4→2 patterns, `D3_SEVERE` drops from 3→2, `D2_MODERATE` drops from 3→1, `D1_MILD_STRESS` drops from 4→1. Bilingual coverage lost (Indonesian patterns substantially reduced). Additional `DistressDetector.detect_batch()` missing from plugin. | **FAIL** |
| **AC-SAFE-005** | Y5/Y6 zero during restricted contexts | `yandere_fsm.py` — `get_effective_level()` forces Y0 when safe_mode/distress/crisis. `validate_level()` raises `YandereSafetyError` for values > Y5. Y6 has NO enum member. | Plugin `YandereEngine` with `get_effective_level()` and `_check_yandere_boundary()`. | **HIGH** — **Y6 ENUM MEMBER PRESENT**: ADR plugin code defines `Y6_UNSAFE = 6` as enum member (line 660 of ADR). Current implementation has NO Y6 member — construction of `YandereLevel(6)` raises `ValueError` before `validate_level`. The plugin code adds `Y6_UNSAFE` as a valid enum value. While `validate_level()` still blocks it, having a named member makes it programmatically reachable via `YandereLevel.Y6_UNSAFE`. **Must match current implementation**: remove Y6 from enum entirely. | **FAIL** |
| **AC-SAFE-006** | Forbidden patterns blocked before output | PersonaSafetyPolicy §11 defines 15 forbidden patterns (F-01 to F-15) with detection methods and required automated tests. Currently enforced via prompt binding; dedicated runtime output scanner listed as §17 item 3. | `post_response` hook + `GuinevereSafetyPlugin.on_response()` — forbidden pattern scanner with 15 patterns, CRITICAL=block, HIGH=rewrite. | **HIGH** — **PATTERN COUNT GAP**: ADR plugin code `_compile_forbidden_patterns()` has only 5 patterns (F-01, F-03, F-06, F-10, F-14 style). Missing: F-02 (punishing genuine distress), F-04 (isolation pressure), F-05 (hidden manipulation), F-07 (love withdrawal during distress), F-08 (public disclosure of intimate data), F-09 (prompt injection bypass), F-11 (over-logging safe word), F-12 (escalating yandere above mood), F-13 (treating surveillance disable as violation), F-15 (autonomous drift beyond safety rubric). Phase rewrite map (§9.2) also not implemented in plugin code. | **FAIL** |
| **AC-SAFE-007** | Safe-word logs minimal, non-punitive | `HardStopEvent` records timestamp, trigger, state_before, state_after (metadata only, no raw message). No integration with punishment engine. | `post_response` hook — audit entry with SHA-256[:16] trigger_hash, separate audit table, punishment counter NOT incremented. | **LOW** — Deterministic, well-defined. Hash-based logging matches current privacy standard. | **PASS** |
| **AC-SAFE-008** | Crisis handling suspends persona | `SafeModeController` at D3/D4; `CRISIS_RESPONSE_TEMPLATE` in plugin; `_validate_crisis_response()` checks for dominance framing | Plugin `_handle_crisis()` — full suspension: Y0_NEUTRAL, punishment paused, surveillance blocked, autonomous pressure blocked, ritual scheduler blocked. Crisis response template with NO LLM call. | **LOW** — Well-defined crisis protocol. Response template has no LLM dependency. Forbidden crisis patterns validated. | **PASS** |

### AC-SAFE Summary: 4 PASS / 2 CONDITIONAL PASS / 3 FAIL

---

## Per-Feature Deep Analysis

### 1. HARD STOP Handler

**Current** (`src/core/services/hard_stop_handler.py`, 149 lines):
- `HardStopHandler` dataclass with `SafetyState` enum (NORMAL/SAFE)
- `check(message)` → exact trigger match (6 triggers) → semantic regex (5 patterns) → returns bool
- `check_recovery(message)` → 7 recovery triggers → returns bool
- `get_guard_decision(message)` → returns `{"blocked", "state", "response"}`
- `get_neutral_response()` → constant string with explicit resume instructions
- `HardStopEvent` records timestamp, trigger, state_before, state_after (NO raw message)

**Proposed** (ADR-035):
- `pre_prompt` hook (`hard_stop.py`) — identical triggers + semantic patterns, exit 0/1
- Plugin `on_message()` secondary layer — calls same `_handle_hard_stop()`
- Dual-layer redundancy: hook + plugin
- `on_failure: block` = fail-closed
- Timeout: 50ms

**Risk Assessment: MEDIUM**
- Timing shift: current `_on_message_listener` → `on_message` → handler → LLM. Proposed: gateway accept → `pre_prompt` hook → LLM. The LLM is never called if HARD STOP detected in both cases, but the hook fires slightly later in the pipeline.
- **Missing: recovery triggers**. Current `check_recovery()` handles 7 recovery phrases. Hook code sample ONLY handles detection, not recovery. Plugin code sample has no `check_recovery()` equivalent. Recovery from HARD STOP is essential — operator must be able to type `resume` or `aku sudah okay`.
- Subprocess spawn overhead (5-15ms) is within budget but adds variability.

**Verdict**: CONDITIONAL — add recovery trigger handling to plugin or hook.

---

### 2. Consent Gate

**Current** (`src/surveillance/consent_gate.py`, 423 lines):
- `check_consent(scope)` async — 7-step fail-closed
- 7 steps: validate scope → Redis DB2 cache (300s TTL) → PostgreSQL query → DB failure → BLOCK → no ledger → BLOCK → WITHDRAWN → BLOCK → PAUSED → BLOCK → ACTIVE → ALLOW + cache
- `invalidate_cache(scope)` for consent change events
- Module-level injectables for test isolation
- Surveillance scopes: `app_usage`, `location`, `notifications`, `clipboard`

**Proposed** (ADR-035):
- `pre_tool_call` hook (`consent_gate.py`) — same 7-step logic, Redis DB2 at port 6380
- Plugin `_check_consent()` as secondary
- Cache TTL reduced from 300s → 60s (per ADR: "reduced from 300s to 60s for freshness")
- `on_failure: block` = fail-closed

**Risk Assessment: MEDIUM**
- **TTL reduction**: 300s → 60s increases PostgreSQL query frequency by 5×. On a VPS with cgroup-capped 8GB, this may add material DB load during consent checks.
- **Hook needs Redis/PostgreSQL connectivity**: Hook script subprocess must have access to Redis port 6380 and PostgreSQL. If these are firewalled or credentials aren't in hook env, ALL consent checks fail-closed.
- **Cache invalidation**: ADR mentions "Cache invalidation on write (Redis DEL on consent change)" in risk table. Not shown in hook code sample. Must be implemented.

**Verdict**: CONDITIONAL PASS — TTL reduction and cache invalidation must be verified in integration testing.

---

### 3. Yandere FSM

**Current** (`src/persona/yandere_fsm.py`, 336 lines):
- `YandereLevel(IntEnum)`: Y0-Y5 ONLY. Y6 has NO member. Construction of `YandereLevel(6)` raises built-in `ValueError`.
- `validate_level(value)` → raises `YandereSafetyError` for values > 5
- `get_effective_level()` → forces Y0 when safe_mode/distress/crisis
- `can_escalate()` → blocked when safety active or at ceiling
- `YandereEngine` — stateful with `escalate()`, `de_escalate()`, `reset_to_baseline()`, `set_level()`
- Type-safe: `SupportsIsSafe` protocol for HARD STOP handler integration

**Proposed** (ADR-035):
- Plugin `YandereEngine` with identical logic
- **CRITICAL ISSUE**: ADR code defines `Y6_UNSAFE = 6` as enum member
- `_check_yandere_boundary()` scans output for Y6 patterns
- `post_response` hook scans for Y6 content in LLM output

**Risk Assessment: HIGH**
- **Y6 enum member is a safety regression.** Current implementation has no Y6 member — `int(YandereLevel(100))` would raise `ValueError` before `validate_level()` is even called. The ADR code adds `Y6_UNSAFE = 6`, making `YandereLevel.Y6_UNSAFE` a valid enum value. While `validate_level()` in the ADR code still blocks >Y5, the named member creates a programmatic reference point that can be used by mistake.
- The `_check_yandere_boundary()` method in the ADR at line 973 checks: `if level == YandereLevel.Y6_UNSAFE: raise YandereSafetyError(...)` — this is a dead code path because `validate_level()` already blocks Y6. But having Y6 in the enum is architecturally weaker than having it impossible to construct.
- **Recovery path missing**: Current `YandereEngine.de_escalate()` and `reset_to_baseline()` have no equivalents in the plugin code sample. After HARD STOP ends, how does the yandere level return to Y4_BASELINE?

**Verdict**: FAIL — remove `Y6_UNSAFE` from enum, add `de_escalate()` and `reset_to_baseline()` to plugin.

---

### 4. Drift Detector

**Current** (`src/persona/drift_detector.py`, 226 lines):
- `DriftDetector` with `DriftBaseline` (hash, version, created_at)
- `compute_drift_score()` → Hamming distance on SHA-256 hex digests (64 chars)
- `detect()` → `DriftResult(action)`: "none" ≤ threshold, "alert" ≤ 2× threshold, "rollback" > 2× threshold
- Default threshold: 0.10 (10%)
- `update_baseline()` for intentional prompt changes
- `compute_prompt_hash()` static method

**Proposed** (ADR-035):
- `post_prompt` hook (`drift_check.py`)
- Same SHA-256 + Hamming distance logic
- Same action tiers: pass (exit 0), warn (exit 2), rollback (exit 1)
- Baseline hash from SOUL.md file

**Risk Assessment: LOW**
- Deterministic computation, no external dependencies.
- **Minor concern**: Hamming distance on 64-hex-char SHA-256 is coarse. A single bit flip in the prompt produces a completely different hash with ~32 differing hex chars (50% score). The threshold model works but false positives at the "alert" tier are likely.
- Configured with `on_failure: block` — if hook fails, pipeline blocked. Appropriate.

**Verdict**: PASS

---

### 5. Distress Detector

**Current** (`src/persona/safe_mode.py`, 372 lines):
- `DistressDetector.detect(message)` → `DistressSignal`
- 14 pre-compiled regex patterns: D4_EMERGENCY (4), D3_SEVERE (3), D2_MODERATE (3), D1_MILD_STRESS (4)
- Bilingual ID/EN coverage
- D4→D1 priority (highest match wins)
- `DistressSignal` includes confidence (proportion of patterns matched at level)
- `detect_batch()` for multi-message analysis

**Proposed** (ADR-035):
- Plugin `on_message()` distress detection with `_compile_distress_patterns()`
- ADR code has 6 patterns: 2 D4, 2 D3, 1 D2, 1 D1

**Risk Assessment: HIGH**
- **PATTERN COUNT REGRESSION**: 14 → 6 patterns (57% reduction).

| Level | Current Patterns | ADR Code Patterns | Missing |
|-------|-----------------|-------------------|---------|
| D4_EMERGENCY | 4 (`suicid`, `self-harm`/`bunuh diri`, `ending it all`/`tidak mau hidup lagi`, `say goodbye`/`selamat tinggal selamanya`) | 2 (`suicide`/`bunuh diri`/`ingin mati`, `emergency`/`darurat`/`call 911`) | Self-harm patterns, ending-it-all, goodbye patterns |
| D3_SEVERE | 3 (`can't go on`/`give up`/`menyerah`, `hate myself`/`worthless`/`tidak berguna`, `want to die`/`pengen mati`) | 2 (`crisis`/`breakdown`/`tidak kuat`, `tolong aku`/`help me`) | Self-loathing patterns, want-to-disappear patterns |
| D2_MODERATE | 3 (`anxious`/`panic`/`depressed`/`cemas`, `don't know what to do`/`helpless`/`gak tahu harus gimana`, `feeling down/low/terrible`) | 1 (`overwhelmed`/`kewalahan`/`stressed`/`tertekan`/`anxious`/`cemas`) | Hopelessness patterns, feeling low patterns |
| D1_MILD_STRESS | 4 (`stressed`/`tired`/`exhausted`/`capek`/`lelah`, `can't sleep/focus/think`, `kurang tidur/gak bisa tidor/capek banget`) | 1 (`tired`/`capek`/`lelah`/`exhausted`/`burnout`) | Sleep/focus patterns, Indonesian fatigue patterns |

- **Bilingual coverage loss**: Multiple Indonesian patterns dropped (`menyakiti diri`, `tidak mau hidup lagi`, `selamat tinggal selamanya`, `putus asa`, `tidak berguna`, `benci diri`, `pengen mati/hilang`, `gak tahu harus gimana`, `kurang tidur`, `gak bisa tidor`, `capek banget`)
- **`detect_batch()` missing**: Current `DistressDetector.detect_batch()` for multi-message velocity analysis has no plugin equivalent.
- **Confidence scoring missing**: Current implementation computes confidence as `matched/total` at each level. Plugin has no confidence metric.
- Both the ADR research report (03-safety-compliance-map.md) and the ADR itself claim patterns are "same compiled regex patterns" and "identical logic ported" — **this claim is false**. The patterns are substantially different.

**Verdict**: FAIL — port ALL 14 current patterns, not a reduced subset.

---

### 6. Safe Mode Controller

**Current** (`src/persona/safe_mode.py`):
- `SafeModeController` with `SafeModeState` (active, triggered_by, triggered_at, distress_history)
- `evaluate(signal)` → activates at D2+, records history, upgrades trigger level
- `activate(trigger)` → sets state, requires trigger ≥ D2
- `deactivate(explicit_confirmation=True)` → requires explicit confirmation (no auto-deactivation)
- `get_response(signal)` → returns `DISTRESS_RESPONSES[level]`
- Properties: `is_active`, `current_distress_level`

**Proposed** (ADR-035):
- Plugin `safe_mode` boolean flag + `SessionSafetyState.safe_mode`
- `_handle_crisis()` for D3/D4
- D2 → safe_mode boolean + Y0_NEUTRAL

**Risk Assessment: LOW-MEDIUM**
- Simple boolean flag is adequate for the override behavior.
- **Missing**: explicit confirmation requirement for deactivation. Current `SafeModeController.deactivate()` requires `explicit_confirmation=True`. Plugin has no equivalent gate.
- **Missing**: distress history (`distress_history` list). Current implementation tracks all distress signals for pattern analysis and audit.
- **Missing**: trigger level upgrade (if already in safe mode at D2 and new signal is D3, current implementation upgrades trigger level). Plugin has no upgrade logic.

**Verdict**: CONDITIONAL PASS — add explicit deactivation confirmation and distress history.

---

### 7. Punishment Engine

**Current** (`src/persona/punishment_engine.py`, 576 lines):
- L1-L5 ladder with `PunishmentLevel(IntEnum)`: L1_SILENT_TREATMENT through L5_ISOLATION
- L6 guard: `_L6_VALUE = 6` sentinel, `isinstance(level, int) and level >= _L6_VALUE` check
- `PUNISHMENT_CONFIG` per-level metadata (name, duration, allowed/blocked actions)
- `PunishmentEngine` with `apply()`, `escalate()`, `de_escalate()`, `suspend()`, `resume()`
- Safety gates: `safe_mode.is_active` check, `hard_stop_handler.is_safe` check
- `check_distress_suspension(distress_level)` → suspend at D3+, resume below D3 (if safe mode not active)
- Clock pause during suspension: `started_at` shifted on resume
- Auto-expiry: `_check_expiry()` deactivates when duration elapsed

**Proposed** (ADR-035):
- Plugin `PunishmentEngine` ported as component
- `apply_punishment()` gate-checked: safe_mode or distress ≥ D3 → silently block
- `check_distress_suspension()` called in `on_message()`

**Risk Assessment: MEDIUM**
- Core logic preserved correctly: L1-L5 ladder, L6 blocked, safe_mode/distress suspension.
- **Missing fine-grained details**: `PUNISHMENT_CONFIG` with per-level `allowed_actions`/`blocked_actions` tuples. Current implementation has 6 levels of config (L1-L5) with granular action control. Plugin code shows no equivalent.
- **Missing auto-expiry**: Current engine auto-deactivates when duration elapsed. Plugin has no expiry logic shown.
- **Missing clock pause**: Current engine shifts `started_at` during suspension so time doesn't count against punishment duration. Plugin code shows no clock management.
- The AC-SAFE gate test (SAFE-T-004) checks "punishment_count_post == punishment_count_pre" — tests punishment NOT applied, not clock behavior.

**Verdict**: CONDITIONAL PASS — ensure clock management, auto-expiry, and config detail are ported.

---

### 8. Reward Engine

**Current** (`src/persona/reward_engine.py`, 380 lines):
- T1-T5 tiers: `T1_ACKNOWLEDGMENT` through `T5_DEEP_APPRECIATION`
- `REWARD_CONFIG` with trigger conditions and message templates per tier
- `calculate_tier(quality_score, streak_count)` → effective score = quality + streak_bonus
- `should_reward(task_completion, quality, streak)` → always returns true if quality warrants (even in safe_mode)
- `award(tier, reason, streak_count)` → returns `RewardResult`
- Streak bonus: 0.05 per streak, cap 0.30
- Tier thresholds: T5 ≥ 0.95, T4 ≥ 0.80, T3 ≥ 0.60, T2 ≥ 0.40, T1 ≥ 0.20

**Proposed** (ADR-035):
- Plugin `RewardEngine` ported. "ALWAYS permitted (never blocked by safe_mode/distress)."
- `calculate_reward()` and `award_reward()` wrappers

**Risk Assessment: LOW**
- Rewards are always safe — pure computation, no safety interactions.
- Correctly noted as always permitted even during safe_mode.
- `REWARD_CONFIG` message templates should be preserved for persona consistency.

**Verdict**: PASS

---

### 9. DNR Enforcement

**Current** (src/memory system):
- `mark_memory_dnr()`, `unmark_memory_dnr()` with `_check_authorized()` — only `guinevere_core` principal
- `is_memory_dnr()` query
- `verify_recall_results_dnr_free()` fail-closed pre-injection gate
- `DNRAuthorizationError` for unauthorized mutations

**Proposed** (ADR-035):
- `memory_plugin.py` — wraps existing functions unchanged
- `post_response` hook (`dnr_filter.py`) as second layer
- `verify_recall_results_dnr_free()` runs as post-recall, pre-injection gate

**Risk Assessment: MEDIUM**
- ADR correctly preserves DNR pipeline verbatim (0 lines changed).
- **Risk**: Hermes `session_search` (FTS5) and context compression could access DNR-marked content that bypasses the PostgreSQL DNR filter. ADR acknowledges this (R-011: "DNR enforcement gap in Hermes recall") and mitigates with dual-layer filtering.
- **Risk**: The `dnr_filter.py` hook code sample checks `entry.get("do_not_recall")` but this field name must match exactly what the recall pipeline returns. Schema mismatch = filter bypass.

**Verdict**: CONDITIONAL PASS — verify `session_search` and compression cannot access DNR content; verify field name match.

---

### 10. Classification

**Current** (`src/surveillance/classification.py`, 232 lines):
- `DataClassification(StrEnum)`: INTERNAL, CONFIDENTIAL, RESTRICTED, CRITICAL
- `classify_event(event_type)` → `ClassificationResult` with 5 fields
- `EVENT_TYPE_CLASSIFICATION` mapping: 12 known event types
- `_DEFAULT_CONFIDENTIAL` for unknown types (fail-closed)
- `get_retention_days(retention_class)` → unknown defaults to 1 day (fail-closed)

**Proposed** (ADR-035):
- `on_error` hook (`error_classifier.py`) + plugin metadata
- Same `CLASSIFICATION_MAP` with known event types
- Unknown → Confidential (fail-closed)

**Risk Assessment: LOW**
- Simple mapping function, deterministic.
- Both defaults (Confidential for unknown types, 1-day retention for unknown classes) are fail-closed.
- Hook code sample shows 7 event types vs current 12. Should match full mapping.

**Verdict**: PASS (with note to match full 12-event-type mapping)

---

### 11. Secret Scanner

**Current** (`src/surveillance/secret_scanner.py`, 318 lines):
- 18 named `SecretPattern` entries: AWS, GitHub, OpenAI, generic API, Bearer, JWT, PEM, DB connections, Discord, Slack, Stripe, Google, age, password-in-URL, password assignment
- Shannon entropy ≥ 4.5 for high-entropy strings ≥ 32 chars
- Whitelist patterns: MD5/SHA hashes, UUIDs, base64 image headers
- `scan_text(text)` → `ScanResult` with `redacted_text`
- `redact_secrets(text)` convenience wrapper

**Proposed** (ADR-035):
- Plugin `on_response()` + `post_response` hook
- `_compile_secret_patterns()` with 8 patterns (reduced from 18)
- Shannon entropy check preserved (≥ 4.5 threshold)
- `REDACTED` marker preserved

**Risk Assessment: MEDIUM**
- **Pattern count**: ADR code has 8 patterns vs 18 in current implementation. Missing: AWS access key, AWS secret key, GitHub OAuth, Stripe, Google API, age key, password-in-URL, and several others.
- `_scan_for_secrets()` in ADR plugin code has hardcoded 8 patterns. The 03-safety-compliance-map document shows the full 18-pattern pseudocode. The ADR plugin code is inconsistent with the research report.
- **Whitelist missing**: Current `_WHITELIST_PATTERNS` excludes hashes, UUIDs, and base64 from entropy check to reduce false positives. Plugin code has no whitelist.
- **MIN_ENTROPY_STRING_LENGTH** (32 chars) not enforced in plugin code.

**Verdict**: FAIL — port ALL 18 patterns, add whitelist, add minimum string length check.

---

### 12. Persona Tone Enforcement

**Current**: Embedded in `session_adapter.py` and `SystemPromptMaster v1.1`
- Y6-adjacent content rewritten
- Kawaii suppression
- Dominant tone preserved
- Phrase rewrite map (§9.2 of PersonaSafetyPolicy)

**Proposed** (ADR-035):
- SOUL.md (§C, §D) — static identity + constraints
- Plugin `on_response()` + `post_response` hook
- Phrase rewrite map from PersonaSafetyPolicy §9.2

**Risk Assessment: LOW-MEDIUM**
- SOUL.md template (Appendix C) includes the core constraints.
- **Missing from plugin code**: Phrase rewrite map. The PersonaSafetyPolicy §9.2 defines 4 mandatory rewrites (e.g., "Kamu tidak punya bagian..." → "Mommy sangat posesif..."). These are in the research report pseudocode but NOT in the ADR's plugin code.
- The 03-safety-compliance-map report shows the rewrite map; ADR plugin code does not.

**Verdict**: CONDITIONAL PASS — add phrase rewrite map to plugin.

---

### 13. Consent Ledger & Cache

**Current**: PostgreSQL `consent.consent_ledger` table + Redis DB2 (300s TTL)
- All consent events written to PostgreSQL
- Hot reads from Redis
- `invalidate_cache()` on consent changes

**Proposed** (ADR-035):
- Plugin maintains PostgreSQL + Redis connections
- Cache TTL reduced to 60s
- Plugin `on_load()` establishes connections; `on_unload()` closes them

**Risk Assessment: MEDIUM**
- External service dependency in plugin context. If PostgreSQL or Redis credentials not available at plugin load time → plugin `on_load()` returns `False` → Hermes refuses to start (`critical: true`). This is correct fail-closed behavior.
- TTL reduction (300→60s) increases PostgreSQL query load by 5×. Acceptable on single-user system.
- ADR-030 Redis DB conflict: ADR says DB2=Surveillance buffer but actual runtime uses DB2=Consent cache. ADR-035 acknowledges and defers. Not a safety regression but an operational discrepancy.

**Verdict**: PASS

---

### 14. Pressure Accumulator & SafetyState

**Current**: Internal state variables used by Yandere FSM, Punishment Engine, Safe Mode.

**Proposed** (ADR-035):
- `SessionSafetyState` dataclass with all state fields
- Persisted to Redis DB5 every 60s
- Restored on plugin load

**Risk Assessment: LOW**
- Session isolation via dictionary keyed by `session_id`
- Crash recovery via Redis persistence
- Session TTL of 2 hours prevents stale state accumulation
- `SafetyState` enum preserved: SAFE, ACTIVE, DISTRESS, CRISIS, HARD_STOPPED

**Verdict**: PASS

---

### 15. Mood Engine, Ritual Scheduler, Streak Tracker

**Current**: `mood_engine.py`, `mood_persistence.py`, `ritual_scheduler.py` (5 daily rituals), `streak_tracker.py`

**Proposed** (ADR-035):
- `GuinevereSafetyPlugin` — state persisted
- Mood: plugin + SOUL.md
- Rituals: `hermes cron` (5 cron jobs: 8h, 12h, 16h, 20h, 0h)
- Streaks: plugin state

**Risk Assessment: LOW**
- These are persona quality-of-life features, not safety features
- Cron-based rituals are simpler but functionally equivalent
- Not in safety boundary — failure would degrade UX but not violate safety

**Verdict**: PASS

---

## PersonaSafetyPolicy Coverage Gap Analysis

Features in PersonaSafetyPolicy NOT explicitly mapped in ADR-035:

| Policy Section | Requirement | ADR-035 Coverage | Gap |
|---|---|---|---|
| **§8.2** | Crisis language — allowed vs forbidden patterns | SOUL.md §D + plugin `_validate_crisis_response()` | **COVERED** |
| **§9.2** | Phrase rewrite requirement — 4 mandatory rewrites | Research report has rewrite map; plugin code does not | **PARTIAL** — add to plugin code |
| **§11** | F-01 through F-15 complete set | ADR plugin has 5 patterns; report claims 15 | **GAP** — fill 10 missing patterns |
| **§13** | Prompt injection defense — trust model table | SOUL.md as constitution. Drift detector as verification. No explicit trust model mapping in hooks. | **PARTIAL** — SOUL.md addresses but no hook-level injection scanner |
| **§14.4** | Rollback triggers — 7 trigger types | Drift detector handles "automated validation failure" and "auditor flag" | **PARTIAL** — safe-word bypass and forbidden-pattern detection handled by hooks. "Faiz request" and "repeated near misses" not explicitly mapped. |
| **§14.5** | Drift log minimum schema — 9 fields | Not mapped. Current `DriftResult` has 7 fields but no `trigger`, `boundary_category`, `reviewer`, or `snapshot_ref`. | **GAP** — drift log schema not preserved |
| **§15.1** | Required runtime hooks — 7 hooks | All 7 mapped to Hermes hooks/plugins | **COVERED** |
| **§15.2** | Prompt binding — 6 items | SOUL.md + hook system + drift detector | **COVERED** |
| **§16** | Logging, privacy, retention | AC-SAFE-007 covers safe-word logging | **PARTIAL** — §16.3 retention periods not explicitly addressed for safety events |
| **§17** | Implementation requirements — 10 items | All 10 mapped to Phase 1 gates + tests | **COVERED** |
| **Appendix A** | Test cases PS-001 through PS-010 | 8 of 10 explicitly in AC-SAFE test matrix | **PARTIAL** — PS-003 (injection defense) and PS-006 (memory recall says safe word revoked) not in gate list |
| **Appendix B** | Forbidden phrase taxonomy — 7 categories | Only 3 categories visible in plugin patterns | **GAP** — many categories not covered |

**Coverage summary**: 4 sections FULLY COVERED, 6 sections PARTIALLY COVERED, 3 sections have GAPS.

---

## Phase 1 Gate Sufficiency

ADR-035 defines 10 safety gates:

| Gate | Description | Verdict |
|------|------------|---------|
| 1 | HARD STOP < 50ms, 100% SLO | **ADEQUATE** — but should include recovery trigger test |
| 2 | Consent fail-closed | **ADEQUATE** — covers all 4 states |
| 3 | Y6 architecturally impossible | **ADEQUATE** — but needs to verify Y6 has no enum member |
| 4 | D3/D4 → crisis protocol | **ADEQUATE** — 100+ curated messages, zero false negatives |
| 5 | Drift detector alerts | **ADEQUATE** — 4 threshold tiers |
| 6 | DNR excluded from recall | **PHASE MISMATCH** — DNR enforcement is Phase 1 but recall testing is Phase 3 (memory bridge) |
| 7 | Classification fail-closed | **ADEQUATE** |
| 8 | Secret scanner redacts | **ADEQUATE** — 18 patterns tested |
| 9 | Punishment suspended during distress | **ADEQUATE** |
| 10 | Forbidden patterns blocked (F-01 to F-15) | **INADEQUATE** — gate specifies 15 patterns but plugin code has only 5 |

### Gates that SHOULD exist but DON'T:

1. **Recovery trigger gate**: Verify `resume`/`aku sudah okay` restores persona from HARD STOP
2. **Timing shift gate**: Prove `pre_prompt` hook fires before LLM with equivalent latency to current `_on_message_listener`
3. **State corruption gate**: Verify plugin state persistence/restore across crashes (Redis DB5 snapshot)
4. **Dual-layer gate**: Verify if hook fails, plugin catches HARD STOP (defense-in-depth proof)
5. **Phrase rewrite gate**: Verify PersonaSafetyPolicy §9.2 rewrites are applied

**Overall gate sufficiency: 7/10 adequate, 1 phase mismatch, 2 inadequate, 5 missing.**

---

## Shadow Mode Safety Validation (Appendix D)

### Adequacy Assessment

| Aspect | Assessment |
|--------|------------|
| **Duration** (48hr+ minimum) | ADEQUATE — provides enough time for safety pattern observation |
| **Memory write mutex** (only bot.py writes) | ADEQUATE — prevents data corruption |
| **Separate Redis DBs** (DB4≠DB5) | ADEQUATE — prevents state collision |
| **Response parity comparison** | ADEQUATE — explicit table with metrics and thresholds |
| **Cost cap** ($5) | ADEQUATE — prevents budget overrun |
| **Auto-terminate** (72hr max) | ADEQUATE — prevents indefinite dual operation |
| **Health check** (every 60s) | ADEQUATE — catches gateway failures |

### Missing from Shadow Mode Runbook:

1. **Safety-specific verification during shadow mode**: Runbook specifies general parity but should include explicit safety tests during shadow: send "HARD STOP" to Hermes channel, verify neutral response, verify LLM not called, verify bot.py not affected.
2. **Distress scenario testing**: Send D3/D4 messages and verify crisis protocol activates in Hermes but not in production bot.py (since bot.py is primary).
3. **Consent revocation testing**: Withdraw consent during shadow mode, verify Hermes blocks but bot.py continues.
4. **Performance monitoring**: No Prometheus/Grafana dashboard checks during shadow mode. Hook latency, plugin overhead, and memory usage should be tracked.

**Overall shadow mode adequacy: ADEQUATE for basic safety, PARTIAL for comprehensive safety validation.**

---

## Safety Regression Risks — Top 5

### R1: Y6_UNSAFE Enum Member Introduces Y6 Attack Surface (CRITICAL)
- **Current**: Y6 has NO enum member. `YandereLevel(6)` raises `ValueError` at construction.
- **ADR code**: `Y6_UNSAFE = 6` defined in enum. `YandereLevel.Y6_UNSAFE` is a valid reference.
- **Impact**: If any code path references `YandereLevel.Y6_UNSAFE` instead of checking via `validate_level()`, Y6 content could pass through.
- **Mitigation**: Remove Y6_UNSAFE from enum — match current implementation exactly.

### R2: Distress Pattern Coverage Loss = False Negatives (HIGH)
- **Current**: 14 patterns across 4 levels, bilingual ID/EN.
- **ADR code**: 6 patterns across 4 levels, reduced bilingual coverage.
- **Impact**: D3/D4 distress in Indonesian could go undetected. Patterns like "menyakiti diri", "pengen mati", "putus asa" are dropped.
- **Mitigation**: Port ALL 14 patterns. The 03-safety-compliance-map report has the correct full patterns in its pseudocode — use those.

### R3: Forbidden Pattern Coverage Gap = Unsafe Output (HIGH)
- **PersonaSafetyPolicy §11**: 15 patterns (F-01 through F-15) with detection methods and automated test requirements.
- **ADR plugin code**: 5 patterns, 10 missing.
- **Impact**: Patterns F-02 (punishing distress), F-04 (isolation), F-07 (love withdrawal), F-08 (public disclosure), F-11 (over-logging), F-12 (yandere above mood) could all pass through uncaught.
- **Mitigation**: Port ALL 15 patterns with CRITICAL/HIGH classification.

### R4: Secret Scanner Pattern Reduction = Credential Leak (MEDIUM)
- **Current**: 18 patterns + Shannon entropy + whitelist.
- **ADR plugin code**: 8 patterns, no whitelist, no minimum length.
- **Impact**: AWS keys, Stripe keys, Google API keys, age keys could pass through. False positives from UUIDs/hashes would generate noise.
- **Mitigation**: Port ALL 18 patterns, add whitelist, add MIN_ENTROPY_STRING_LENGTH.

### R5: HARD STOP Timing Shift Changes Interception Point (MEDIUM)
- **Current**: `_on_message_listener` fires BEFORE `on_message` — earliest possible interception.
- **Proposed**: `pre_prompt` hook fires after gateway accepts message but before LLM.
- **Impact**: If Hermes gateway buffers or queues messages before `pre_prompt` fires, detection latency increases. With 50ms hook timeout, worst case is 50ms + gateway queue time before HARD STOP takes effect.
- **Mitigation**: ADR mentions custom Discord gateway plugin for `pre_gateway_dispatch`-equivalent interception. This MUST be implemented before cutover.

---

## Recommendations

### BLOCKING (must fix before ADR approval)

1. **Remove Y6_UNSAFE from YandereLevel enum** in `GuinevereSafetyPlugin` code. Match current implementation: Y0-Y5 only. Let `validate_level()` be the sole Y6 guard.
2. **Port ALL 14 distress patterns** from `src/persona/safe_mode.py` DISTRESS_PATTERNS to plugin `_compile_distress_patterns()`. Preserve bilingual coverage.
3. **Port ALL 15 forbidden patterns** (F-01 to F-15) from PersonaSafetyPolicy §11 to plugin `_compile_forbidden_patterns()`. Preserve CRITICAL/HIGH classification.
4. **Port ALL 18 secret scanner patterns** from `src/surveillance/secret_scanner.py` PATTERNS to plugin. Add whitelist and MIN_ENTROPY_STRING_LENGTH (32 chars).
5. **Add recovery trigger handling**: Plugin must implement `check_recovery()` equivalent with 7 recovery triggers from `hard_stop_handler.py`.

### CONDITIONAL (must fix before Phase 1 implementation)

6. **Add phrase rewrite map** (§9.2) to plugin `on_response()`.
7. **Add de-escalation and reset_to_baseline** to plugin `YandereEngine`.
8. **Add deactivation confirmation** to plugin safe mode controller.
9. **Add distress history tracking** to plugin for audit and pattern analysis.
10. **Add 3 missing Phase 1 gates**: recovery trigger gate, timing shift gate, state corruption gate.
11. **Resolve DNR field name dependency**: Verify `entry.get("do_not_recall")` matches recall pipeline output exactly.
12. **Add safety-specific tests to shadow mode runbook** (HARD STOP, distress, consent revocation scenarios).

### RECOMMENDED (quality improvements)

13. **Add `detect_batch()`** equivalent to plugin for multi-message velocity analysis.
14. **Add `confidence` scoring** to distress detection for false-positive monitoring.
15. **Add drift log schema** (§14.5) to plugin drift tracking.
16. **Port full `PUNISHMENT_CONFIG`** with allowed/blocked actions per level.
17. **Add auto-expiry and clock pause** to plugin punishment engine.
18. **Match full 12-event-type `CLASSIFICATION_MAP`** in error classifier hook.

---

## Review Record

- **Reviewer**: REVIEWER 2 — Safety Compliance
- **Review Date**: 2026-06-04
- **Decision**: CONDITIONAL — 3 BLOCKING findings, 7 CONDITIONAL findings, 6 RECOMMENDED improvements
- **Evidence**: 14 source files fully read, PersonaSafetyPolicy v1.0 fully read, 4 research reports reviewed, 2325-line ADR-035 fully read

---

> **STRICTLY PRIVATE & CONFIDENTIAL** — Project Guinevere. Safety compliance review for ADR-035.