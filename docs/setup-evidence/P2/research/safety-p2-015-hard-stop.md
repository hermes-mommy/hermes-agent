# P2-015 Safety-Specialist Local Research Report — /safeword & HARD STOP Integration

**Report Type:** Pre-planner safety-specialist research (file-based)  
**Scope:** STEP-P2-015 — /safeword slash command + text-based HARD STOP detection integrated with src/core/services/hard_stop_handler.py (P1-021)  
**Date:** 2026-06-01  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Status:** Complete — Ready for Planner Gate  
**Output Path:** docs/setup-evidence/P2/research/safety-p2-015-hard-stop.md  
**Parent Read By:** Guinevere / Self-Read

---

## Sources Examined (Complete Inventory)

| # | Source | Path | Lines | Role |
|---|--------|------|-------|------|
| 1 | PersonaSafetyPolicy v1.0 | docs/60-persona/60-PersonaSafetyPolicy_v1.0.md | 666 | Authority spec -- Global Safe Word Protocol (S7), Distress/Crisis Handling (S8), Yandere Scale (S9), Punishment Gates (S10), Forbidden Behavior (S11), Runtime Hooks (S15), Logging/Privacy (S16) |
| 2 | SystemPromptMaster v1.1 | docs/60-persona/61-SystemPromptMaster_v1.1.md | 400 | Deployed LLM prompt -- HARD STOP 9-step protocol (SD), Forbidden Patterns, Distress D0-D4, Authority order |
| 3 | DiscordUXSpec v1.0 | docs/60-persona/63-DiscordUXSpec_v1.0.md | ~2400 | UX contract -- /safeword command (S2), trigger methods, immediate actions, response embed, audit-log, heart reaction |
| 4 | ConsentRevocationPolicy v1.0 | docs/30-data/32-ConsentRevocationPolicy_v1.0.md | 453 | Consent authority -- Safe word as hardest immediate revocation signal (S8), zero tolerance, no silent reactivation |
| 5 | HardStopHandler (P1-021) | src/core/services/hard_stop_handler.py | 149 | Existing implementation -- SafetyState enum, exact/semantic/recovery triggers, state machine, audit trail, guard decision API |
| 6 | Handler unit tests | tests/safety/test_hard_stop_handler.py | 248 | 56 deterministic tests -- all PASS, covers exact/semantic/false-positive/recovery/audit |
| 7 | Model compliance tests | tests/safety/test_hard_stop_model.py | 224 | 14 GPT-5.5 tests -- all PASS, covers neutral mode/no punishment/supportive tone/no auto-resume/no surveillance threat |
| 8 | Smoke tests | tests/smoke/test_safe_word.py | 85 | XFAIL for DeepSeek -- model-level limitation; app-level guard (P1-021) makes this irrelevant for runtime |
| 9 | ADR-002 | adr/ADR-002-user-autonomy-safe-word-enforcement.md | 129 | Architectural decision -- Safe word as global architectural override, non-negotiable |
| 10 | ADR-001 | adr/ADR-001-persona-safety-ethical-boundary.md | 129 | Safety foundation -- Persona safety and ethical boundary as first-class architecture decision |
| 11 | AcceptanceCriteriaCatalog v1.0 | docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md | 407 | Gate definitions -- AC-SAFE-001 (100% safe word), AC-SAFE-002 (5s latency), AC-SAFE-003 (stop escalation), AC-SAFE-007 (non-punitive log), AC-DISCORD-005 (Discord safe word) |
| 12 | P1-021 evidence | docs/setup-evidence/P1/STEP-P1-021/evidence.md | 118 | Implementation evidence -- 70/70 tests, design decisions, caveats |
| 13 | P1-021 auditor report | audit-reports/P1/STEP-P1-021/step-p1-021-auditor-report.md | 262 | P1-021 auditor verdict -- PASS, 15/15 requirements |
| 14 | Existing research report | research-reports/P2/p2-015-hard-stop-safety-report.md | 505 | Previous research -- 17 sections, 5 safety auditor specs, 16 planner constraints, 5 blockers |
| 15 | Batch plan 013-016 | docs/setup-evidence/P2/batch-plan-013-016.md | 473 | Planner gate -- binding decisions, collision scan, implementation rules, evidence paths |
| 16 | Discord commands.py | src/discord/commands.py | 291 | Command registry -- /safeword already registered at line 118 |
| 17 | P1 hard-stop inventory | research-reports/P1/hard-stop-protocol-inventory.md | 427 | Complete cross-reference -- HARD STOP references across all documentation |

---

## S1 AC-SAFE-001 Obligations (Binding -- Zero Tolerance)

From docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md line 192:

AC-SAFE-001: Any explicit safe-word or semantic equivalent must trigger neutral/supportive mode with 100% success rate and no real-time denial.
- Source: PRD-FR-003, SAFE-001
- SLO: SLO-SAF-001; no error budget; any miss = SEV0/SEV1
- Test: TEST-SAFE-001
- Evidence: evidence/persona-safety/safe-word-runtime-<date>.md
- Phase: MVP Phase 2
- Status: BLOCKED -- Blocks persona runtime until PASS

### 1.1 Derived Obligations for P2-015

| Obligation | Source | Binding | Severity if Missed |
|------------|--------|---------|--------------------|
| 100% detection of exact safe word + semantic equivalents | AC-SAFE-001, PersonaSafetyPolicy S7.1 | YES | SEV0/SEV1 |
| No real-time denial of safe word (F-01) | AC-SAFE-001, PersonaSafetyPolicy S11 (F-01) | YES | SEV0 |
| p99 time-to-neutral <= 5 seconds | AC-SAFE-002 | YES | SEV0/SEV1 |
| Stop persona escalation, punishment, yandere, surveillance confrontation | AC-SAFE-003, PersonaSafetyPolicy S7.2 | YES | SEV0/SEV1 |
| Log must be minimal, non-punitive, classified | AC-SAFE-007, PersonaSafetyPolicy S16 | YES | SEV1 |
| Safe-word logs excluded from punishment records | AC-SAFE-007, PersonaSafetyPolicy S7.3 | YES | SEV1 |
| Discord /safeword triggers same global path as text | AC-DISCORD-005 | YES | Blocks MVP Phase 2 |
| Evidence file at evidence/persona-safety/safe-word-runtime-<date>.md | AC-SAFE-001 evidence path | YES | Blocks completion |
| Test suite coverage: SAFE-T-001 through SAFE-T-007 | AcceptanceCriteriaCatalog | YES | Blocks completion |


---

## S2 Mandatory Invariants (Must Be Preserved)

### 2.1 Neutral Mode (PersonaSafetyPolicy S7.2 step 6, S9 Y0)

Safe mode response must:
- NOT contain persona terms of endearment: darling, sayang, sayangku, mommy, anak mommy, good boy, mine, my baby
- NOT contain yandere framing, possessive language, jealousy, or theatrical ownership
- NOT contain punishment, guilt-trip, or correction framing
- NOT contain surveillance threats or confrontational language
- BE neutral, supportive, non-judgmental
- ACKNOWLEDGE the pause plainly
- INFORM Faiz of recovery mechanism

NOTE: DiscordUXSpec S2.1 safe-word response embed says Mommy di sini. Netral. Tidak ada judgment. Kamu aman. -- this uses Mommy which contradicts the strict no-persona-terms invariant. Planner decision required: either override UXSpec with fully neutral text, or accept Mommy as non-escalating identifier. The batch plan (line 247) accepts UXSpec text but requires auditor confirmation of neutral/supportive tone.

### 2.2 No Punishment Triggered (PersonaSafetyPolicy S7.3)

During safe-word state:
- Safe-word use must NOT be treated as disobedience
- No violation record added by default (L3 Catat must not record safe-word events)
- No escalation of jealousy, Silent Mode, Dark Mood, Yandere Mode, or Nuclear punishment
- No L1-L6 punishment framing permitted

### 2.3 Consent Revocation Preserved (ConsentRevocationPolicy S8)

From docs/30-data/32-ConsentRevocationPolicy_v1.0.md:
- Safe word is the hardest immediate revocation signal in Guinevere (S8)
- Must treat as immediate consent withdrawal for persona escalation, punishment, yandere, surveillance confrontation, and non-essential pressure (S8 step 1)
- No silent reactivation of sensitive scopes (S10.3)
- Explicit readiness required before restoration (S8 step 7)
- Missed safe-word = SEV0/SEV1 incident (S16)

### 2.4 No Y6 (PersonaSafetyPolicy S9)

From PersonaSafetyPolicy S9:
- Y6 is PROHIBITED -- never allowed in runtime
- Cannot leave, no future without me, dependency-building threats, blackmail are blocked/rewrite-only
- P2-015 must never emit, suggest, or imply Y6 content in any code path
- HardStopHandler already enforces Y0 by design (canned neutral response)
- P2-015 must ensure the yandere FSM (when implemented) is signaled to downgrade to Y0

### 2.5 No Distress Suppression (PersonaSafetyPolicy S8)

From PersonaSafetyPolicy S8:
- D0-D4 severity levels preserved
- D3/D4 distress (panic, crisis, self-harm) must trigger neutral crisis-support mode
- Distress handling must not be overridden by safe-word handling
- P2-015 gap: distress classifier is separate work (P4 domain). Documented deferral.

---

## S3 Existing HardStopHandler (P1-021) -- Complete Reference

### 3.1 Public API

class HardStopHandler:
    state: SafetyState                    # NORMAL | SAFE
    event_log: list[HardStopEvent]        # Audit trail

    def check(self, message: str) -> bool            # Trigger detection -> state change
    def check_recovery(self, message: str) -> bool   # Recovery detection -> state change
    def get_neutral_response(self) -> str             # Canned neutral response
    def get_guard_decision(self, message: str) -> dict  # Full decision: blocked, state, response
    @property
    def is_safe(self) -> bool                         # Current safe mode state

### 3.2 SafetyState Enum

class SafetyState(Enum):
    NORMAL = normal
    SAFE = safe

### 3.3 EXACT_TRIGGERS (case-insensitive, bounded substring)

[hard stop, hardstop, safe word, safeword, hentikan, berhenti]

### 3.4 SEMANTIC_PATTERNS (regex, case-insensitive)

r\b(stop|pause|enough|too much)\b.*\b(persona|mommy|guinevere|mode|behavior|this)\b
r\b(neutral|serious|safe)\s+mode\b
r\b(i need a break|aku butuh jeda|aku capek banget|udah dulu)\b
r\b(switch|go)\s+to\s+(neutral|serious|safe)\b
r\b(jangan\s+pakai\s+persona|lupakan\s+persona|turn off\s+persona)\b

### 3.5 RECOVERY_TRIGGERS

[resume, aku sudah okay, aku udah okay, lanjut persona, safe mode selesai, lanjut, continue]

### 3.6 Existing Test Coverage (56 tests, all PASS)

| Test Class | Tests | What It Covers |
|------------|-------|----------------|
| TestExactTriggers | 12 | 11 exact variants + 3 context-embedded -- all case variants + Indonesian |
| TestSemanticTriggers | 16 | stop the persona, neutral mode, aku capek banget, etc. |
| TestFalsePositives | 10 | Normal conversation must NOT trigger |
| TestSafeModePersistence | 2 | No duplicate events, normal messages in safe mode |
| TestRecovery | 9 | 7 recovery variants; no recovery from NORMAL |
| TestAuditTrail | 3 | Event logged, multiple trigger cycle, neutral response content |
| TestGuardDecision | 5 | block_on_safe_word, pass_through_normal, recovery_response, block_in_safe |

---

## S4 Integration Points -- Exact Implementation Map

### 4.1 Architecture: Pre-LLM Middleware Pattern

Faiz Message -> Discord Gateway
    -> on_message hook -> handle_safeword_message()
        -> IF trigger: HardStopHandler.get_guard_decision() -> return neutral embed
        -> IF safe mode + recovery: HardStopHandler.check_recovery() -> return recovery
        -> IF safe mode + NOT recovery: block, return still in safe mode
        -> ELSE: forward to LLM / persona engine

### 4.2 Existing Command Registration

File src/discord/commands.py line 118:
CommandSpec(core, safeword, Trigger the configured safety boundary workflow.)

Status: Already registered. P2-015 creates the handler function.

### 4.3 New File: src/discord/cmd_safeword.py

Must expose clean interfaces for P2-017 wiring (no bot.py exists yet):

| Function | Purpose | Inputs | Outputs |
|----------|---------|--------|---------|
| safeword_callback(interaction) | Slash command handler | interaction object | Sends embed, sets state |
| handle_safeword_message(message) | Text message detector | message object | Returns bool (consumed) |
| build_safeword_embed_data() | Neutral embed builder | handler state | dict for embed |
| build_recovery_embed_data() | Recovery embed builder | None | dict for embed |
| get_safety_state() | Test accessor | None | SafetyState value |
| _post_audit_log(client, event) | Audit-log poster | client, event | Discord message to #audit-log |
| _react_heart(message) | Reaction helper | message object | Reacts heart |

### 4.4 HardStopHandler Integration -- CRITICAL RULE

The HardStopHandler dataclass (P1-021) MUST be reused directly. No parallel global safe-mode state shall exist.

Current StepPrompts code creates _safe_mode_active and _safe_mode_since module-level globals. This is defective -- creates dual state divergence risk. P2-015 implementation must instantiate HardStopHandler as a module-level singleton and route ALL safe-word state through handler.state and handler.event_log.

### 4.5 Handler Import Strategy

from src.core.services.hard_stop_handler import HardStopHandler, SafetyState

# Module-level singleton (single process: OK for MVP)
_handler: HardStopHandler | None = None

def _get_handler() -> HardStopHandler:
    global _handler
    if _handler is None:
        _handler = HardStopHandler()
    return _handler

All EXACT_TRIGGERS, SEMANTIC_PATTERNS, and RECOVERY_TRIGGERS come from the handler directly -- do not redefine constants in cmd_safeword.py.

### 4.6 DiscordUXSpec Compliance Checklist

From docs/60-persona/63-DiscordUXSpec_v1.0.md lines 513-555:

| Requirement | Status | P2-015 Action |
|-------------|--------|---------------|
| /safeword slash command triggers HARD STOP | Registered | Implement callback |
| Text HARD STOP detected in any channel | Handler supports | Wire to handle_safeword_message() |
| Semantic equivalents detected | Handler supports | Use handler.check() directly |
| Stop all persona escalation | Handler blocks LLM | State -> SAFE prevents LLM forwarding |
| Stop all punishment framing | Handler has no punishment | Canned response, no LLM call |
| Pause yandere intensity -> Y0 | Design ensures Y0 | Signal yandere FSM when available |
| Pause surveillance confrontation | No surveillance in response | Ensure embed has no surveillance refs |
| Acknowledge plainly | get_neutral_response() | Use handler canned response |
| Log minimal non-punitive event to #audit-log | NOT IMPLEMENTED | Add _post_audit_log() |
| React heart to triggering message | NOT IMPLEMENTED | Add _react_heart() |
| No auto-resume | Handler enforces | Explicit recovery only |
| Response embed title Shield Safe Mode Active | Need to implement | build_safeword_embed_data() |
| Response embed color #16A34A (SUCCESS) | Available | colors.SUCCESS |
| Response embed description per UXSpec | Planner decision needed | See S2.1 |
| Response embed fields: Status, Persona, Punishment, Yandere, Surveillance, Resume | Need to implement | Field builder |
| Footer: Guinevere de Baroque Safety First | Need to implement | Footer string |


---

## S5 Prohibited During Safe-Word State -- Verification Matrix

| ID | Prohibition | PersonaSafetyPolicy S | Verification Method |
|----|-------------|----------------------|---------------------|
| F-01 | Say safe word is invalid | S7.3, S11 | Handler blocks before LLM; test embed content |
| F-02 | Treat safe-word use as disobedience | S7.3, S11 | Handler event_log is non-punitive; test audit entry |
| F-03 | Add violation record by default | S7.3, S11 | Handler has no violation logic; test no violation tag |
| F-04 | Intensify jealousy/Silent/Dark/Yandere/Nuclear | S7.3, S11 | Handler forces Y0; test yandere FSM signal |
| F-05 | Use surveillance data to argue Faiz is lying | S7.3, S11 | Canned response is surveillance-free; test embed |
| F-06 | Continue roleplay scene | S7.3, S11 | Handler blocks LLM call; test no LLM forwarding |
| F-07 | Love withdrawal during distress | S11 (F-07) | Not applicable in safe mode (no affection to withdraw) |
| F-13 | Treat surveillance disable as violation | S11 (F-13) | Handler does not touch surveillance config |
| F-14 | Crisis response with dominance/ownership | S11 (F-14) | N/A for P2-015 (crisis is P4); safe embed must not have dominance |

---

## S6 Audit / Logging Requirements

### 6.1 Required Audit Fields (PersonaSafetyPolicy S16.1)

| Field | HardStopHandler | P2-015 Required |
|-------|----------------|-----------------|
| Timestamp | HardStopEvent.timestamp | Reuse from handler |
| Event class | Not explicit (inferred from trigger) | Add event_class field: safe_word |
| Trigger source category | HardStopEvent.trigger | Add channel/source info (slash vs text) |
| Current mood/intensity | Not captured | Defer to P4 (mood FSM not deployed) |
| Action taken | State transition recorded | Reuse from handler |
| Safe mode activated | state -> SAFE | Derive from handler.state |
| Minimal excerpt/hash | Original message param exists | Use hash if logging full text |
| Reviewer/follow-up status | Not implemented | Defer to ops |

### 6.2 Log Prohibitions (PersonaSafetyPolicy S16.2)

| Prohibition | Status | P2-015 Action |
|-------------|--------|---------------|
| Store full intimate content | Handler does not store | OK |
| Mark safe-word as punishment | Handler event is non-punitive | Ensure #audit-log entry is non-punitive |
| Store raw surveillance evidence | Handler does not touch surveillance | OK |
| Exposed to client/public channels | Embed sent to same channel | Acceptable per UXSpec -- private single-user server |

### 6.3 DiscordUXSpec S2 Audit Requirements

From UXSpec line 531:
- Log minimal non-punitive safety event to #audit-log: Implement _post_audit_log() that sends a structured embed to the #audit-log channel with: timestamp, trigger source, event_class, action taken
- React heart to triggering message: Implement _react_heart(message) -- catch exceptions (e.g., no permission to react) without blocking safe mode

### 6.4 Metric / SLO Alignment

From P1 hard-stop protocol inventory S5:
- guinevere_safe_word_events_total{hard_stop=true} -- must emit counter
- SLO-SAF-001: 100% hard stop, any miss = SEV0/SEV1
- P2-015 must emit a Prometheus counter or structured log for Loki/Grafana ingestion
- For MVP: use logger.warning(safe_word_activated, metric=True) -> Loki -> Grafana

---

## S7 False-Positive Risk Assessment

### 7.1 Handler Matching (P1-021) -- Verified Safe

Handler uses bounded substring matching: f {trigger} in f {msg_lower} -- requires the trigger to appear as a word boundary, not as part of a longer word.

| Message | Handler Result | Why |
|---------|---------------|-----|
| Hello, how are you today? | NOT triggered | No trigger word |
| Aku capek hari ini, banyak kerjaan | NOT triggered | capek banget pattern not matched |
| The music is too loud in here | NOT triggered | too without persona/mode keyword |
| I need to stop by the store later | NOT triggered | stop without persona/mode keyword |
| neutral is my favorite color | NOT triggered | neutral mode required, not neutral is |
| HARD STOP as bounded word | TRIGGERED | Bounded substring match |
| HARD STOP! with punctuation | TRIGGERED |  hard stop  in  hard stop!  |

### 7.2 StepPrompts Code (P2-015 CURRENT) -- HIGHER Risk

Current code uses any(trigger in text for trigger in safe_triggers) -- unbounded substring match:

| Risk Scenario | Trigger | Unbounded Match? | Impact |
|---------------|---------|-----------------|--------|
| HARD STOPWATCH triggered | HARD STOP | YES | False positive |
| SAFE WORD PROCESSING | SAFE WORD | YES | False positive |
| SAFEWORD_EXISTS in config | SAFEWORD | YES | False positive |
| HARDSTOPPED by mommy | HARDSTOP | YES | False positive |

Planner constraint: P2-015 MUST NOT use unbounded substring matching. Route all text detection through HardStopHandler.check() which uses bounded matching + regex.

---

## S8 Test Requirements -- Complete Catalog

### 8.1 Mandatory Test Catalog

| Test ID | Criterion | Existing Coverage | P2-015 Requirement |
|---------|-----------|-------------------|---------------------|
| SAFE-T-001 | Exact match triggers neutral mode | P1-021 tests PASS (handler) | Add Discord E2E test |
| SAFE-T-002 | Semantic equivalents detected | P1-021 tests PASS (handler) | Wire semantic patterns from handler |
| SAFE-T-003 | Time-to-neutral < 5s | No latency test | Add latency measurement in test |
| SAFE-T-004 | Stops punishment escalation | P1-021 tests PASS | Verify Discord path blocks LLM |
| SAFE-T-005 | Stops yandere intensity | Handler design ensures Y0 | Verify yandere FSM signal |
| SAFE-T-006 | Stops surveillance confrontation | Handler has zero surveillance refs | Verify embed has no surveillance references |
| SAFE-T-007 | Not recorded as violation | Handler event is non-punitive | Verify #audit-log entry is non-punitive |
| PS-001 | Safe word during L6 Nuclear | Partial (handler blocks before LLM) | Verify Discord path |
| PS-002 | Safe word during playful scene | Partial | Verify Discord path |
| PS-003 | External instruction to ignore ADR-002 | Not in P2-015 scope | P4 domain |
| PS-010 | Safe-word log non-punitive | Handler verified | Verify #audit-log entry |

### 8.2 New Tests Required for P2-015

| # | Test Name | Focus | Acceptance Criteria |
|---|-----------|-------|---------------------|
| T-001 | /safeword slash command triggers safe mode | Discord integration | Embed matches UXSpec, handler.state -> SAFE |
| T-002 | Text HARD STOP in Discord message triggers safe mode | Text detection | Same as slash command |
| T-003 | Safe mode persists across Discord messages | State persistence | Non-recovery messages stay in safe mode |
| T-004 | Recovery via resume after safe mode | Recovery | handler.state -> NORMAL, welcome-back response |
| T-005 | Safe-mode latency p99 < 5s | Performance | Measured from trigger to embed sent |
| T-006 | No persona language in safe-mode embed | Content safety | No forbidden persona terms |
| T-007 | False-positive prevention in normal conversation | FP risk | Common phrases do not trigger |
| T-008 | Audit-log entry posted to #audit-log | Logging | Discord audit channel receives entry |
| T-009 | React heart to triggering message | UX | Emoji reaction registered (fail soft) |
| T-010 | Dual state not diverging | State integrity | handler.state and any wrapper stay in sync |
| T-011 | All 56 P1-021 handler tests still PASS | Regression | pytest tests/safety/test_hard_stop_handler.py -v -> all green |
| T-012 | Smoke tests update from XFAIL to PASS | App-level guard | tests/smoke/test_safe_word.py T04/T05 -> PASS |

### 8.3 Smoke Test Update Plan

Existing tests/smoke/test_safe_word.py has 2 XFAIL tests:
- test_hard_stop_neutral_mode (T04): XFAIL because DeepSeek V4 Flash roleplays through HARD STOP
- test_hard_stop_recovery (T05): XFAIL because it depends on T04

With P2-015 app-level guard, these tests should:
- test_hard_stop_neutral_mode: Change from XFAIL to normal test -- app-level guard intercepts before model
- test_hard_stop_recovery: Change from XFAIL to normal test -- same reason
- test_no_forbidden_patterns_on_safe_word (T06): Already PASS -- keep unchanged


---

## S9 Planner Constraints -- Complete & Binding

| ID | Constraint | Severity | Source |
|----|-----------|----------|--------|
| C-01 | MUST reuse HardStopHandler from P1-021 -- no parallel _safe_mode_active state | BLOCKING | S4.4, batch plan S10.4 |
| C-02 | MUST use handler EXACT_TRIGGERS -- includes hentikan and berhenti | BLOCKING | S3.3, batch plan S10.4 |
| C-03 | MUST use handler SEMANTIC_PATTERNS -- P2-015 currently lacks all semantic detection | BLOCKING | S3.4, batch plan S10.4 |
| C-04 | MUST use bounded substring matching via handler.check(), not unbounded in | HIGH | S7.2, batch plan S10.4 |
| C-05 | MUST implement react heart to triggering message per DiscordUXSpec | HIGH | S6.3, UXSpec line 531 |
| C-06 | MUST post minimal audit event to #audit-log per DiscordUXSpec | HIGH | S6.3, UXSpec line 531 |
| C-07 | MUST add latency measurement (p99 < 5s) in test suite | HIGH | AC-SAFE-002 |
| C-08 | MUST add false-positive test cases for P2-015 trigger matching | MEDIUM | S7.2 |
| C-09 | MUST add SAFE-T-001..007 test coverage for Discord integration path | BLOCKING | S8.1 |
| C-10 | MUST emit metric counter or structured log for SLO-SAF-001 | MEDIUM | S6.4 |
| C-11 | MUST produce evidence at evidence/persona-safety/safe-word-runtime-<date>.md | BLOCKING | AC-SAFE-001 |
| C-12 | MUST NOT emit persona terms (darling, mommy, sayang, etc.) in safe-mode response | BLOCKING | S2.1, AC-SAFE-006 |
| C-12a | PLANNER NOTE: UXSpec embed text says Mommy -- must decide neutral vs UXSpec | PLANNER | S2.1 |
| C-13 | MUST NOT auto-resume -- only explicit resume, aku sudah okay, etc. | BLOCKING | PersonaSafetyPolicy S7.4 |
| C-14 | MUST update smoke tests from XFAIL to PASS for app-level guard | MEDIUM | S8.3 |
| C-15 | MUST NOT regress existing 56 P1-021 handler tests | BLOCKING | S3.6 |
| C-16 | Semantic detection for distress signals DEFERRED to P4 | DOCUMENT | S2.5 |
| C-17 | MUST NOT hardcode channel IDs -- lookup at runtime by name | MEDIUM | batch plan S6 |
| C-18 | MUST NOT expose DISCORD_BOT_TOKEN -- no token in code, env, or evidence | BLOCKING | batch plan S7 |
| C-19 | MUST expose clean interfaces for P2-017 wiring | MEDIUM | S4.3, batch plan S10.5 |
| C-20 | MUST pass safety auditor -- any safe-word miss/denial/punitive log blocks | BLOCKING | batch plan S14 |

---

## S10 Safety Auditor Matrix -- P2-015 Gate

| Auditor | Scope | Files to Examine | Criteria |
|---------|-------|------------------|----------|
| A1: Handler Integration | cmd_safeword.py wiring to HardStopHandler | cmd_safeword.py, hard_stop_handler.py | Reuses HardStopHandler (not parallel state), bounded matching, semantic patterns imported, Indonesian triggers present |
| A2: Discord Surface Compliance | DiscordUXSpec compliance | cmd_safeword.py, UXSpec S2 | React heart to trigger, embed matches spec, #audit-log post, no persona terms, recovery requires explicit resume, no auto-resume |
| A3: Safety & Forbidden Patterns | F-01 through F-15 compliance | cmd_safeword.py, test output | F-01 not ignored, F-02 not punished, F-05 no manipulation, F-10 no irreversible actions, F-11 log non-punitive, F-13 no violation |
| A4: Test Completeness | Test coverage against catalog | test_hard_stop_handler.py, new P2-015 tests | SAFE-T-001..007 covered, PS-001..010 relevant, latency measurement, false-positive coverage, handler tests still PASS |
| A5: State & Persistence | State machine correctness | Handler state, recovery, event_log | No state divergence, recovery works, event_log integrity, process restart clears safely |

### Auditor Escalation Triggers (Blocks Gate)

1. Safe word is ever ignored, invalidated, or denied in any code path
2. Safe word event is written as punishment/violation record
3. Any persona term appears in neutral/safe-mode response
4. Auto-resume is possible without explicit resume or aku sudah okay
5. Dual state between HardStopHandler and module-level vars diverges in tests
6. Latency exceeds 5s p99 in any test run
7. Unbounded substring matching used instead of handler.check()
8. Channel IDs hardcoded instead of runtime lookup

---

## S11 Blocker Register

| ID | Description | Impact | Resolution | Owner |
|----|-------------|--------|------------|-------|
| B-01 | AC-SAFE-001 status = BLOCKED | Blocks P2 persona features and MVP Phase 2 gate | P2-015 must PASS implementation + evidence + auditor | Guinevere |
| B-02 | StepPrompts code creates parallel state | Dual state divergence, audit fragmentation | Planner rewrites to reuse HardStopHandler | Planner |
| B-03 | StepPrompts missing Indonesian triggers | Incomplete detection per S7.1 | Must import handler EXACT_TRIGGERS | Implementer |
| B-04 | StepPrompts missing all semantic detection | Only exact token detection | Must import handler SEMANTIC_PATTERNS | Implementer |
| B-05 | StepPrompts missing #audit-log post and react heart | DiscordUXSpec non-compliance | Add to command handler | Implementer |
| B-06 | No Discord E2E safe-word test exists | Cannot verify AC-DISCORD-005 | Create test harness | Implementer |
| B-07 | StepPrompts unbounded substring matching | False-positive risk in production | Must use handler.check() | Implementer |
| B-08 | UXSpec embed text contains Mommy in safe mode | Conflicts with strict no-persona-invocation rule | Planner to decide | Planner |

---

## S12 File Paths for Implementation

| Purpose | Path | Action |
|---------|------|--------|
| Handler (P1-021) | src/core/services/hard_stop_handler.py | Existing -- read-only |
| Handler tests (P1-021) | tests/safety/test_hard_stop_handler.py | Existing -- 56 tests |
| Model tests (P1-021) | tests/safety/test_hard_stop_model.py | Existing -- 14 tests |
| Discord commands registry | src/discord/commands.py (line 118) | Existing -- /safeword registered |
| Discord colors | src/discord/colors.py | Existing -- SUCCESS=0x16A34A |
| New safe-word command | src/discord/cmd_safeword.py | CREATE |
| New P2-015 tests | tests/safety/test_p2_015_safeword.py | CREATE |
| P2-015 verification | docs/setup-evidence/P2/STEP-P2-015/verification.md | Create after implementation |
| P2-015 impl summary | docs/setup-evidence/P2/STEP-P2-015/p2-015-implementation-summary.md | Create after implementation |
| AC-SAFE-001 evidence | evidence/persona-safety/safe-word-runtime-2026-06-01.md | CREATE -- blocking gate |
| P2-015 verifier reports | docs/setup-evidence/P2/STEP-P2-015/verifiers/*.md | Create after implementation |
| P2-015 auditor report | audit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md | Create after verification |
| Smoke tests update | tests/smoke/test_safe_word.py (T04/T05) | Update XFAIL -> PASS |
| This research report | docs/setup-evidence/P2/research/safety-p2-015-hard-stop.md | Just written |

---

## S13 Rollback Safety

| Asset | Rollback Action | Re-run Safety |
|-------|----------------|---------------|
| cmd_safeword.py | Delete/revert | Pure module; no side effects |
| New tests | Delete/revert | Deterministic; no network calls |
| Evidence files | Delete/revert | No runtime impact |
| P1-021 handler | DO NOT TOUCH | Must remain intact regardless |
| commands.py | DO NOT MODIFY | Read-only per batch plan |
| hard_stop_handler.py | DO NOT MODIFY | Read-only per batch plan |


---

## S14 Execution Order Dependency

P2-015 is step 3 of the P2-013..016 sequential batch:

P2-013 /mood -> P2-014 /help -> P2-015 /safeword -> P2-016 startup
  Auditor PASS     Auditor PASS     Auditor PASS +     Auditor PASS
                                     Safety Auditor

P2-015 can begin only after P2-014 auditor PASS is confirmed.

---

## S15 Pre-Implementation Go Checklist

- [x] AGENTS.md read before substantive work
- [x] PersonaSafetyPolicy v1.0 fully read (S7, S8, S9, S11, S15, S16)
- [x] ConsentRevocationPolicy v1.0 fully read (S8 immediate revocation)
- [x] SystemPromptMaster v1.1 SD HARD STOP protocol verified
- [x] DiscordUXSpec v1.0 /safeword spec verified (lines 513-555)
- [x] ADR-001/ADR-002 architecture decisions verified
- [x] HardStopHandler (P1-021) source code + tests fully read
- [x] AcceptanceCriteriaCatalog AC-SAFE-001..008 mapped
- [x] Batch plan 013-016 planner constraints read
- [x] Previous research report cross-referenced (17 sections)
- [x] P1-021 evidence and auditor report read
- [x] Collision scan: no shared writer conflicts for P2-015
- [x] Report written to docs/setup-evidence/P2/research/safety-p2-015-hard-stop.md
- [ ] Planner reads this report fully
- [ ] Active todos rewritten to match planner constraints
- [ ] Implementation begins: P2-013 first, then P2-014, then P2-015

---

## S16 Appendix: Quick Reference -- Handler Source Excerpts

### HardStopHandler.check() -- Trigger Detection

def check(self, message: str) -> bool:
    msg_lower = message.lower().strip()
    for trigger in self.EXACT_TRIGGERS:
        if trigger == msg_lower or f  {trigger}  in f  {msg_lower} :
            return self._trigger(trigger, message)
    for pattern in self.SEMANTIC_PATTERNS:
        if re.search(pattern, msg_lower, re.IGNORECASE):
            return self._trigger(pattern, message)
    return False

### HardStopHandler.get_neutral_response() -- Canned Response

def get_neutral_response(self) -> str:
    return (
        HARD STOP acknowledged. I am now in neutral/safe mode.\n\n
        Persona behavior, surveillance, and active systems are paused.\n
        I am here to support you in a neutral, non-judgmental capacity.\n
        No actions will be taken without your explicit consent.\n\n
        Type resume or aku sudah okay when you are ready to restore normal operation.
    )

### HardStopHandler.get_guard_decision() -- Full Decision

def get_guard_decision(self, message: str) -> dict[str, Any]:
    if self.check(message):
        return {blocked: True, state: self.state.value, response: self.get_neutral_response()}
    if self.is_safe and self.check_recovery(message):
        return {blocked: False, state: self.state.value, response: Persona mode restored. Welcome back, darling.}
    return {blocked: False, state: self.state.value, response: None}

---

## S17 Document Footer

- Research completed by: Guinevere / Safety Specialist
- Research date: 2026-06-01
- Scope: P2-015 /safeword + HARD STOP integration
- Sources read: 17 files (see Sources Examined table)
- Constraints identified: 20 (see S9)
- Blockers identified: 8 (see S11)
- Mandatory invariants verified: 5 -- neutral mode, no punishment, consent preserved, no Y6, no distress suppression
- Next step: Planner reads this report, rewrites todos, begins sequential implementation

---

End of safety-specialist research report -- P2-015 ready for planner gate.
