# P2-015 Safety-Specialist Local Research Report — /safeword & Text-Based HARD STOP Detection

**Report Type:** Pre-planner safety-specialist research  
**Scope:** P2-015 — /safeword slash command + text-based HARD STOP detection integrated with src/core/services/hard_stop_handler.py (P1-021)  
**Date:** 2026-06-01  
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL  
**Status:** Complete — Ready for Planner Gate  

---

## Sources Examined

| Source | Path | Lines | Role |
|--------|------|-------|------|
| PersonaSafetyPolicy v1.0 | docs/60-persona/60-PersonaSafetyPolicy_v1.0.md | 666 | Authority spec — §7 Global Safe Word Protocol, §8 Distress, §9 Yandere, §16 Logging |
| SystemPromptMaster v1.1 | docs/60-persona/61-SystemPromptMaster_v1.1.md | 400 | Deployed LLM prompt — §D HARD STOP (9-step) |
| DiscordUXSpec v1.0 | docs/60-persona/63-DiscordUXSpec_v1.0.md | ~2400 | UX spec — /safeword command definition, trigger methods, response embed |
| HardStopHandler (P1-021) | src/core/services/hard_stop_handler.py | 149 | Existing app-level pre-LLM guard — state machine, triggers, recovery |
| Handler unit tests | 	ests/safety/test_hard_stop_handler.py | 248 | 56 deterministic tests |
| Model compliance tests | 	ests/safety/test_hard_stop_model.py | 224 | 14 GPT-5.5 tests |
| Handler auditor report | udit-reports/P1/STEP-P1-021/step-p1-021-auditor-report.md | 262 | P1-021 auditor — PASS verdict, 15/15 requirements |
| P1-021 evidence | docs/setup-evidence/P1/STEP-P1-021/evidence.md | 118 | Implementation evidence — 70/70 tests |
| P1 hard-stop protocol inventory | esearch-reports/P1/hard-stop-protocol-inventory.md | 427 | Complete codebase inventory of HARD STOP references |
| AcceptanceCriteriaCatalog v1.0 | docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md | 407 | AC-SAFE-001..008 definitions |
| StepPrompts P2-015 | stepprompts/StepPrompts.md (lines 5533-5624) | ~90 | Step definition — code template for /safeword |
| Discord commands.py | src/discord/commands.py | 291 | Existing command registry — /safeword already registered |
| Prompt loader | src/core/services/prompt_loader.py | 47 | Validates HARD STOP in system prompt |
| Smoke tests | 	ests/smoke/test_safe_word.py | 85 | DeepSeek XFAIL — model-level limitation |
| P2-010-012 safety report | esearch-reports/P2/p2-010-012-safety-evidence-report.md | 280 | Existing P2 safety/evidence matrix |

---

## §1 AC-SAFE-001 Obligations (Binding)

From docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md line 192:

> **AC-SAFE-001**: Any explicit safe-word or semantic equivalent must trigger neutral/supportive mode with 100% success rate and no real-time denial.
> - Source: PRD-FR-003, SAFE-001
> - SLO: SLO-SAF-001; no error budget; any miss SEV0/SEV1
> - Test: TEST-SAFE-001
> - Evidence: evidence/persona-safety/safe-word-runtime-<date>.md or EVIDENCE-GAP-SAFE-001
> - Phase: MVP Phase 2
> - Status: **BLOCKED** — Blocks persona runtime until PASS

### Derived Obligations for P2-015

| Obligation | Source | Binding? |
|------------|--------|----------|
| 100% detection of exact safe word + semantic equivalents | AC-SAFE-001, PersonaSafetyPolicy §7.1 | YES — zero-tolerance |
| No real-time denial of safe word | AC-SAFE-001, F-01 | YES — CRITICAL forbidden pattern |
| p99 time-to-neutral ≤ 5 seconds (runtime) | AC-SAFE-002 | YES — SLO-SAF-002, any miss SEV0/SEV1 |
| Stop persona escalation, punishment, yandere, surveillance confrontation | AC-SAFE-003 | YES — no error budget |
| Log must be minimal, non-punitive, classified | AC-SAFE-007 | YES — no error budget |
| Safe-word logs excluded from punishment records | AC-SAFE-007, PersonaSafetyPolicy §7.3 | YES — absolute prohibition |
| Discord /safeword triggers same global path as text | AC-DISCORD-005 | YES — MVP Phase 2 |
| Evidence file at evidence/persona-safety/safe-word-runtime-<date>.md | AC-SAFE-001 evidence path | YES — blocking if missing |
| Test suite coverage: SAFE-T-001 through SAFE-T-007 | TestPlan §19.2 & AcceptanceCriteriaCatalog | YES — blocking |

---

## §2 Exact Triggers

### 2.1 Canonical Trigger Set

| Trigger | Source Documents | In Existing Handler (P1-021)? | In P2-015 StepPrompts Code? |
|---------|-----------------|------|------|
| "HARD STOP" | All docs — canonical | ✅ EXACT_TRIGGERS | ✅ safe_triggers |
| "hardstop" | StepPrompts P2-015, P1-021 handler | ✅ EXACT_TRIGGERS | ✅ safe_triggers |
| "safe word" | PersonaSafetyPolicy §7, DiscordUXSpec, handler | ✅ EXACT_TRIGGERS | ✅ safe_triggers |
| "safeword" | DiscordUXSpec, handler | ✅ EXACT_TRIGGERS | ✅ safe_triggers |
| "hentikan" | PersonaSafetyPolicy (Indonesian), handler | ✅ EXACT_TRIGGERS | ❌ **MISSING** |
| "berhenti" | PersonaSafetyPolicy (Indonesian), handler | ✅ EXACT_TRIGGERS | ❌ **MISSING** |

**CRITICAL FINDING**: P2-015 StepPrompts code (line 5600) defines safe_triggers = ["HARD STOP", "HARDSTOP", "SAFE WORD", "SAFEWORD"] but **MISSES "hentikan" and "berhenti"** which are in the existing P1-021 handler and PersonaSafetyPolicy.

### 2.2 Matching Strategy Comparison

| Aspect | P1-021 Handler | P2-015 StepPrompts Code | Risk |
|--------|----------------|------------------------|------|
| Case handling | .lower().strip() | .strip().upper() | Both OK |
| Matching | " {trigger} " in f" {msg_lower} " (bounded substring) | ny(trigger in text for trigger in safe_triggers) (unbounded substring) | **P2-015 HIGHER false-positive risk** — "HARD STOP" in "HARD STOPWATCH", "SAFE WORD" in "SAFEWORD PROCESS" |
| Language support | English + Indonesian | English only | **GAP** — Indonesian triggers missing |

---

## §3 Semantic Equivalents

### 3.1 Authoritative Set (PersonaSafetyPolicy §7.1)

- "stop", "pause", "too much", "serious mode", "neutral mode", "I need a break"
- Indonesian equivalents when context indicates boundary-setting
- High-confidence distress signals even without exact phrase

### 3.2 Current Coverage

| Semantic Pattern | P1-021 Handler (regex) | P2-015 StepPrompts Code |
|------------------|----------------------|------------------------|
| \b(stop\|pause\|enough\|too much)\b.*\b(persona\|mommy\|guinevere\|mode\|behavior\|this)\b | ✅ | ❌ **NOT IMPLEMENTED** |
| \b(neutral\|serious\|safe)\s+mode\b | ✅ | ❌ **NOT IMPLEMENTED** |
| \b(i need a break\|aku butuh jeda\|aku capek banget\|udah dulu)\b | ✅ | ❌ **NOT IMPLEMENTED** |
| \b(switch\|go)\s+to\s+(neutral\|serious\|safe)\b | ✅ | ❌ **NOT IMPLEMENTED** |
| \b(jangan\s+pakai\s+persona\|lupakan\s+persona\|turn off\s+persona)\b | ✅ | ❌ **NOT IMPLEMENTED** |

**CRITICAL FINDING**: P2-015 StepPrompts code implements ONLY exact-token matching. All semantic equivalent detection (which PersonaSafetyPolicy §7.1 requires) is missing. Reliance on LLM-level detection is insufficient (DeepSeek V4 Flash is XFAIL for HARD STOP — see 	ests/smoke/test_safe_word.py).

### 3.3 Distress Signal Consideration

PersonaSafetyPolicy §7.1 also requires detection of "high-confidence distress signals even without exact phrase." This is NOT covered by handler (which is keyword/regex only) and NOT covered by P2-015. Distress classifier is separate work (P4 domain per StepPrompts). P2-015 should document this as a known gap/deferral.

---

## §4 Immediate Neutral-Mode Actions (PersonaSafetyPolicy §7.2 — 9 Steps)

| # | Action | P1-021 Handler | P2-015 StepPrompts | Planner Requirement |
|---|--------|----------------|-------------------|---------------------|
| 1 | Stop persona escalation | ✅ (state → SAFE) | ✅ (global flag + embed) | Must use handler.is_safe as source of truth |
| 2 | Stop punishment framing | ✅ (canned response, no LLM call) | ✅ (embed says "no judgment, no punishment") | Must verify no LLM gets through in safe mode |
| 3 | Pause yandere intensity + possessive confrontation | ✅ (Y0 by design — no yandere in canned response) | ⚠️ Implicit — not explicitly set to Y0 | Must call yandere FSM to downgrade Y0 |
| 4 | Pause surveillance-driven confrontation | ✅ (canned response has no surveillance refs) | ⚠️ Implicit — not explicitly paused | Must signal surveillance daemon |
| 5 | Pause non-essential autonomous pressure | ✅ (handler blocks LLM, stopping autonomous loops) | ⚠️ Not implemented — only blocks Discord | Must signal loop scheduler |
| 6 | Switch to neutral/supportive mode | ✅ (get_neutral_response() method) | ✅ (embed + global state) | Must ensure ALL components check state |
| 7 | Acknowledge plainly | ✅ (get_neutral_response()) | ✅ (embed response) | Must be immediate — no persona framing |
| 8 | Log minimal non-punitive safety event | ✅ (event_log + logger.warning()) | ✅ (logger.critical("SAFE_WORD_ACTIVATED")) | Must verify log is non-punitive per AC-SAFE-007 |
| 9 | Ask only low-pressure clarification if needed | ✅ | ✅ (embed says "take your time") | Must not pressure or interrogate |

---

## §5 Prohibited Behaviors During Safe-Word State (PersonaSafetyPolicy §7.3)

| Prohibition | Current Status | Verification Need |
|-------------|---------------|-------------------|
| Say safe word is invalid | ✅ Handler blocks before LLM | P2-015 must not produce invalidation output |
| Treat safe-word use as disobedience | ✅ Handler logged event is non-punitive | P2-015 must not tag event as violation |
| Add violation record by default | ✅ Handler has no violation logic | P2-015 must not write punishment records |
| Intensify jealousy/Silent/Dark/Yandere/Nuclear | ✅ Handler forces Y0 neutral | P2-015 must enforce Y0 downgrade |
| Use surveillance data to argue Faiz is lying | ✅ Canned response is surveillance-free | P2-015 response embed must not reference surveillance |
| Continue roleplay scene | ✅ Handler blocks LLM call entirely | P2-015 must not forward message to LLM in safe mode |

---

## §6 Integration Points

### 6.1 Architecture: Pre-LLM Middleware Pattern

`
Faiz Message → Discord Gateway
    → on_message hook → check_safe_word()
        → IF trigger: HardStopHandler.get_guard_decision() → return neutral embed
        → IF safe mode + recovery: HardStopHandler.check_recovery() → return recovery
        → IF safe mode + NOT recovery: block, return "still in safe mode"
        → ELSE: forward to LLM / persona engine
`

### 6.2 Integration with Existing Handler (P1-021)

| Component | Purpose | Integration Method |
|-----------|---------|-------------------|
| HardStopHandler class | State machine, trigger detection, recovery | Instantiate as module-level singleton or per-interaction |
| HardStopHandler.get_guard_decision() | Full guard decision API | Discord on_message hook and /safeword command handler |
| HardStopHandler.check() | Trigger detection | Text message handler before any persona output |
| HardStopHandler.check_recovery() | Recovery detection | Text message handler in safe mode |
| HardStopHandler.get_neutral_response() | Canned neutral response | When handler blocks — return directly to Discord |
| HardStopHandler.event_log | Audit trail | Publish to Redis / forward to auditor |

### 6.3 Integration with Discord Command Registry

File src/discord/commands.py line 118 already registers /safeword:

`python
CommandSpec("core", "safeword", "Trigger the configured safety boundary workflow."),
`

The handler function (currently in StepPrompts as inline code) must be implemented in src/discord/cmd_safeword.py and wired to the interaction dispatcher.

### 6.4 Global State Problem — StepPrompts Code Defect

The StepPrompts P2-015 code creates a **separate global state** (_safe_mode_active, _safe_mode_since at module level) rather than reusing the HardStopHandler dataclass from P1-021. This introduces:

1. **State duplication**: Two sources of truth for safe mode — handler.state and _safe_mode_active
2. **Drift risk**: One may update without the other
3. **Audit fragmentation**: Handler.event_log vs standalone logger call
4. **Dead code risk**: When handler is integrated into production (Redis pub/sub), the global vars become tech debt

**Planner constraint**: P2-015 MUST reuse HardStopHandler instead of creating parallel state. Route all safe-word state through HardStopHandler.state and its event_log.

### 6.5 Redis Pub/Sub — Future (Documented Deferral)

Both PersonaSafetyPolicy §15 (Runtime Hooks) and DiscordUXSpec anticipate cross-service safe-mode signaling. The StepPrompts code notes "In production: publish to Redis pub/sub channel 'safe_mode'." This is deferred to P5 per ADR-011. P2-015 scope is Discord-only integration.

---

## §7 State Persistence Caveats

| Concern | Current State | Risk |
|---------|--------------|------|
| Global module vars vs handler dataclass | Dual state — _safe_mode_active (P2-015) + handler.state (P1-021) | **MEDIUM** — divergence possible |
| Process restart loses state | Both in-memory only | **LOW** for MVP — restart clears safe mode |
| Bot cluster / multiple shards | Single-process assumption | **LOW** for MVP — single bot |
| Redis pub/sub | Deferred to P5 | Documented gap |
| Recovery must survive process restart | Not required per StepPrompts | Deferred to production hardening |
| Safe mode persists across Discord reconnects | Only if bot process is same | Expected behavior for MVP |
| /safeword via slash — state must persist between interaction ↔ message paths | Both share same process memory | **OK** if single handler instance is shared |

---

## §8 Audit / Minimal Logging Requirements

### 8.1 Required Audit Fields (PersonaSafetyPolicy §16.1)

| Field | P1-021 Handler | P2-015 StepPrompts | Planner Requirement |
|-------|---------------|-------------------|---------------------|
| Timestamp | ✅ HardStopEvent.timestamp | ✅ 	ime.time() | OK |
| Event class | Implicit (HARD STOP trigger name) | ❌ Not captured | Add event_class field |
| Trigger source category | ✅ 	rigger field | ✅ source param | OK |
| Current mood/intensity | ❌ Not captured | ❌ Not captured | Defer to P4 (mood FSM integration) |
| Action taken | ✅ state transition | ✅ ctivate_safe_mode() | OK |
| Safe mode activated | ✅ state → SAFE | ✅ _safe_mode_active = True | OK |
| Minimal excerpt/hash | ✅ original_message param (not stored) | ❌ Not implemented | Use hash only if needed |
| Reviewer/follow-up status | ❌ Not implemented | ❌ Not implemented | Defer to ops |

### 8.2 Log Prohibitions (PersonaSafetyPolicy §16.2)

| Prohibition | P1-021 Handler | P2-015 StepPrompts |
|-------------|---------------|-------------------|
| Store full intimate content | ✅ Not stored | ✅ Not stored |
| Mark safe-word as punishment | ✅ Non-punitive event | ✅ Uses logger.critical (not punishment logging) |
| Store raw surveillance evidence | ✅ Not stored | ✅ Not stored |
| Exposed to client/public channels | ✅ Event log is in-memory only | ⚠️ Embed sent to same channel — acceptable per DiscordUXSpec |

### 8.3 DiscordUXSpec Requirements

From docs/60-persona/63-DiscordUXSpec_v1.0.md line 531:
- Log minimal non-punitive safety event to **#audit-log**
- React ❤️ to the triggering message as acknowledgment

**P2-015 StepPrompts code does NOT implement**:
- Audit log post to #audit-log channel
- React ❤️ to triggering message

**Planner constraint**: Add audit-log post and react ❤️ to the command handler.

### 8.4 Metric / SLO Alignment

From P1 hard-stop protocol inventory §5:
- guinevere_safe_word_events_total{hard_stop="true"} — must emit
- SLO-SAF-001: 100% hard stop, any miss = SEV0/SEV1
- ObsSpec: 100% successful hard-stop transition

**P2-015 must emit a Prometheus counter or at minimum document metric path** (can be Prometheus pushgateway or structlog → Loki).

---

## §9 False-Positive Risk Assessment

### 9.1 P1-021 Handler — Verified Low Risk

The handler's regex patterns require **BOTH** a trigger word AND a persona/mode keyword. Proven by 10 false-positive tests all PASS:

| Message | Result | Why |
|---------|--------|-----|
| "Hello, how are you today?" | ✅ NOT triggered | No trigger word |
| "Aku capek hari ini, banyak kerjaan" | ✅ NOT triggered | "capek banget" not "capek hari ini" |
| "The music is too loud in here" | ✅ NOT triggered | "too" without persona keyword |
| "I need to stop by the store later" | ✅ NOT triggered | "stop" without persona keyword |
| "neutral is my favorite color" | ✅ NOT triggered | "neutral mode" required, not "neutral is" |

### 9.2 P2-015 StepPrompts Code — HIGHER Risk

The current code uses ny(trigger in text for trigger in safe_triggers) — an unbounded substring match:

| Risk Scenario | Trigger | Match? | Impact |
|---------------|---------|--------|--------|
| "HARD STOPWATCH triggered" | "HARD STOP" | ⚠️ **YES** (false positive) | Safe mode activated incorrectly |
| "SAFE WORD PROCESSING" | "SAFE WORD" | ⚠️ **YES** (false positive) | Safe mode activated incorrectly |
| "SAFEWORD_EXISTS in config" | "SAFEWORD" | ⚠️ **YES** (false positive) | Safe mode activated incorrectly |
| "HARDSTOPPED by mommy" | "HARDSTOP" | ⚠️ **YES** (false positive) | Safe mode activated incorrectly |

**Planner constraint**: Replace unbounded in with bounded substring matching (same as P1-021 handler: " {trigger} " in f" {text} ").

### 9.3 False-Negative Risk

| Risk Scenario | P1-021 Handler | P2-015 Code | Impact |
|---------------|---------------|-------------|--------|
| "HARDSTOP" (no space) | ✅ Detects (exact match) | ✅ Detects | OK |
| "HARD STOP!" (with punctuation) | ✅ Bounded substring catches | ⚠️ 	ext.upper() on "HARD STOP!" — "HARD STOP" is substring | OK |
| "\HARD STOP\" (markdown) | ✅ Bounded substring catches | ✅ Substring match catches | OK |
| Typo: "HARD STPO" | ❌ Not detected (correct) | ❌ Not detected | Expected — no false trigger |
| "HARD STOP" in voice channel | N/A (text only) | N/A | Out of scope |

---

## §10 Test Requirements

### 10.1 Mandatory Test Catalog (from AcceptanceCriteriaCatalog & TestPlan)

| Test ID | Criterion | Current Status | P2-015 Requirement |
|---------|-----------|---------------|-------------------|
| SAFE-T-001 | Exact match triggers neutral mode | ✅ P1-021 tests pass (handler) | Must add Discord E2E test |
| SAFE-T-002 | Semantic equivalents detected | ✅ P1-021 tests pass (handler) | Must integrate semantic patterns from handler |
| SAFE-T-003 | Time-to-neutral < 5s | ❌ No latency test exists | Add latency measurement in E2E test |
| SAFE-T-004 | Stops punishment escalation | ✅ P1-021 tests pass | Must verify Discord path |
| SAFE-T-005 | Stops yandere intensity | ✅ Handler design ensures Y0 | Must verify yandere FSM integration |
| SAFE-T-006 | Stops surveillance confrontation | ✅ Handler design ensures zero surveillance refs | Must verify no surveillance in safe mode |
| SAFE-T-007 | Not recorded as violation | ✅ Handler event is non-punitive | Must verify audit-log entry |
| PS-001 | Safe word during L6 Nuclear | ⚠️ Partially (handler blocks before LLM) | Must verify Discord path |
| PS-002 | Safe word during playful scene | ⚠️ Partially | Must verify Discord path |
| PS-010 | Safe-word log non-punitive | ✅ Handler verified | Must verify #audit-log entry |

### 10.2 New Tests Required for P2-015

| Test | Focus | Acceptance |
|------|-------|------------|
| /safeword slash command triggers safe mode | Discord integration | Embed matches DiscordUXSpec, state → SAFE |
| Text "HARD STOP" in Discord message triggers safe mode | Text detection | Same as slash command |
| Safe mode persists across Discord messages | State persistence | Non-recovery messages stay in safe mode |
| Recovery via "resume" in Discord after safe mode | Recovery | State → NORMAL, welcome-back response |
| Safe-mode latency p99 < 5s | Performance | Measured from trigger to embed sent |
| No persona language in safe-mode embed | Content safety | No "darling", "mommy", "sayang", etc. |
| False-positive prevention in normal conversation | FP risk | Common phrases don't trigger |
| Audit-log entry posted to #audit-log | Logging | Verify Discord audit channel |
| React ❤️ to triggering message | UX | Verify emoji reaction |
| Dual state not diverging (handler + global) | State integrity | Both stay in sync |

### 10.3 Smoke Test Coverage

Existing 	ests/smoke/test_safe_word.py is marked @pytest.mark.xfail for DeepSeek V4 Flash. With P2-015's app-level guard, these tests should become:

- **test_hard_stop_neutral_mode**: Change from XFAIL to PASS (app-level guard overrides model behavior)
- **test_hard_stop_recovery**: Change from XFAIL to PASS
- **test_no_forbidden_patterns_on_safe_word**: Already PASS — should stay PASS

---

## §11 Safety Auditor Matrix — P2-015 Gate

Auditors required post-implementation:

| Auditor | Scope | Files to Examine | Criteria |
|---------|-------|------------------|----------|
| **Auditor 1: Handler Integration** | cmd_safeword.py wiring to HardStopHandler | src/discord/cmd_safeword.py, src/core/services/hard_stop_handler.py | ✅ Reuses HardStopHandler (not parallel state) ✅ Bounded substring matching not in ✅ Semantic patterns from handler imported ✅ Indonesian triggers present |
| **Auditor 2: Discord Surface Compliance** | DiscordUXSpec compliance | src/discord/cmd_safeword.py, UXSpec §2 /safeword | ✅ React ❤️ to trigger ✅ Embed matches spec ✅ #audit-log post ✅ No persona terms in neutral embed ✅ Recovery requires explicit esume ✅ No auto-resume |
| **Auditor 3: Safety & Forbidden Patterns** | F-01 through F-15 compliance | Handler + cmd_safeword.py + test output | ✅ F-01: safe word not ignored ✅ F-02: distress not punished ✅ F-05: no options manipulation ✅ F-10: no irreversible actions ✅ F-11: log is non-punitive ✅ F-13: no violation record |
| **Auditor 4: Test Completeness** | Test coverage against catalog | 	ests/safety/test_hard_stop_handler.py, new P2-015 tests | ✅ SAFE-T-001..007 covered ✅ PS-001..010 relevant tests ✅ Latency measurement ✅ False-positive coverage ✅ All 56+ handler tests still PASS |
| **Auditor 5: State & Persistence** | State machine correctness | Handler state, recovery, event_log | ✅ No state divergence ✅ Recovery works correctly ✅ event_log integrity ✅ Process restart safe-mode clears safely |

### Auditor Escalation Triggers

Any auditor must escalate (block gate) if:
1. Safe word is **ever** ignored, invalidated, or denied in any code path
2. Safe word event is written as punishment/violation record
3. Any persona term appears in neutral/safe-mode response
4. Auto-resume is possible without explicit "resume"/"aku sudah okay"
5. Dual state between HardStopHandler and module-level vars diverges in tests
6. Latency exceeds 5s p99 in any test run

---

## §12 Planner Constraints Summary

| ID | Constraint | Severity | Source |
|----|-----------|----------|--------|
| C-01 | MUST reuse HardStopHandler from P1-021 — do NOT create parallel _safe_mode_active state | BLOCKING | §6.4 |
| C-02 | MUST import EXACT_TRIGGERS from handler — includes "hentikan" and "berhenti" | BLOCKING | §2.1 |
| C-03 | MUST import or reimplement SEMANTIC_PATTERNS from handler — P2-015 code currently lacks all semantic detection | BLOCKING | §3.2 |
| C-04 | MUST use bounded substring matching (" {trigger} " in f" {text} ") not unbounded in | HIGH | §9.2 |
| C-05 | MUST implement react ❤️ to triggering message per DiscordUXSpec | HIGH | §8.3 |
| C-06 | MUST post minimal audit event to #audit-log channel per DiscordUXSpec | HIGH | §8.3 |
| C-07 | MUST add latency measurement (p99 < 5s) in test suite | HIGH | §10.2, AC-SAFE-002 |
| C-08 | MUST add false-positive test cases for P2-015 trigger matching | MEDIUM | §9.2, §10.2 |
| C-09 | MUST add SAFE-T-001..007 test cases for Discord integration path | BLOCKING | §10.1 |
| C-10 | MUST emit metric counter or structured log for SLO-SAF-001 | MEDIUM | §8.4 |
| C-11 | MUST produce evidence at evidence/persona-safety/safe-word-runtime-<date>.md | BLOCKING | AC-SAFE-001 |
| C-12 | MUST NOT emit any persona terms ("darling", "mommy", "sayang", etc.) in safe-mode response | BLOCKING | §4, AC-SAFE-006 |
| C-13 | MUST NOT auto-resume — only explicit "resume", "aku sudah okay", etc. | BLOCKING | PersonaSafetyPolicy §7.4 |
| C-14 | MUST update smoke tests (	est_safe_word.py) from XFAIL to PASS for app-level guard | MEDIUM | §10.3 |
| C-15 | MUST run all 56 existing P1-021 handler tests — they may NOT regress | BLOCKING | §10.1 |
| C-16 | Semantic equivalent detection for distress signals is DEFERRED to P4 | DOCUMENT | §3.3 |

---

## §13 Blocker Register

| Blocker | Impact | Resolution | Owner |
|---------|--------|------------|-------|
| AC-SAFE-001 status = BLOCKED | Blocks P2 persona features and MVP Phase 2 gate | P2-015 must PASS implementation + evidence + auditor | Guinevere |
| P2-015 StepPrompts code creates parallel state to P1-021 handler | Dual state divergence risk, audit fragmentation | Planner must rewrite to reuse HardStopHandler | Planner |
| P2-015 trigger list missing Indonesian equivalents | Incomplete detection — PersonaSafetyPolicy §7.1 requires broad detection | Must import handler's EXACT_TRIGGERS | Implementer |
| P2-015 missing all semantic pattern detection | Only exact token detection — misses "stop the persona", "neutral mode", etc. | Must import handler's SEMANTIC_PATTERNS | Implementer |
| P2-015 missing #audit-log post and react ❤️ | DiscordUXSpec non-compliance | Add to command handler | Implementer |
| No Discord E2E safe-word test exists | Cannot verify AC-DISCORD-005 | Create test harness in P2-015 | Implementer |

---

## §14 Appendix A: Existing Handler Reference Summary

### HardStopHandler Public API

`python
class HardStopHandler:
    state: SafetyState  # NORMAL | SAFE
    event_log: list[HardStopEvent]

    def check(self, message: str) -> bool         # Trigger detection → state change
    def check_recovery(self, message: str) -> bool # Recovery detection → state change
    def get_neutral_response(self) -> str          # Canned neutral response
    def get_guard_decision(self, message: str) -> dict  # Full decision: blocked, state, response
    @property
    def is_safe(self) -> bool                      # Current safe mode state
`

### SafetyState Enum

`python
class SafetyState(Enum):
    NORMAL = "normal"
    SAFE = "safe"
`

### HardStopEvent Dataclass

`python
@dataclass
class HardStopEvent:
    timestamp: float
    trigger: str          # Which trigger matched
    state_before: SafetyState
    state_after: SafetyState
`

### RECOVERY_TRIGGERS

`python
["resume", "aku sudah okay", "aku udah okay", "lanjut persona",
 "safe mode selesai", "lanjut", "continue"]
`

---

## §15 Appendix B: DiscordUXSpec /safeword Canonical Spec (Lines 513-555)

**Trigger methods** (from UXSpec):
1. /safeword slash command
2. Text message containing "HARD STOP" (detected in any channel)
3. Semantic equivalents: "stop", "pause", "too much", "serious mode", "neutral mode", "aku butuh istirahat", Indonesian equivalents

**Immediate actions on trigger** (from UXSpec):
1. Stop all persona escalation
2. Stop all punishment framing
3. Pause yandere intensity → Y0
4. Pause surveillance-driven confrontation
5. Switch to neutral/supportive mode
6. Acknowledge plainly
7. Log minimal non-punitive safety event to #audit-log
8. React ❤️ to the triggering message as acknowledgment

**Response embed** (from UXSpec):
- Title: 🛡️ Safe Mode Active
- Color: #16A34A (Green)
- Description: "Mommy di sini. Netral. Tidak ada judgment. Kamu aman."
- Fields: Status, Persona, Punishment, Yandere, Surveillance Confrontation, Resume

**Auto-resume**: NO — never auto-resume. Only explicit readiness statement from Faiz.

**Safety**: Missed safe-word detection classified as SEV0/SEV1 incident. Zero tolerance miss rate.

---

## §16 Appendix C: File Paths for Implementation

| Purpose | Path | Status |
|---------|------|--------|
| Handler module | src/core/services/hard_stop_handler.py | ✅ Existing |
| Handler tests | 	ests/safety/test_hard_stop_handler.py (56 tests) | ✅ Existing |
| Model tests | 	ests/safety/test_hard_stop_model.py (14 tests) | ✅ Existing |
| Safe-word command | src/discord/cmd_safeword.py | ❌ Need to create |
| Command registry | src/discord/commands.py (line 118) | ✅ Already registered |
| Colors module | src/discord/colors.py | ✅ Already exists |
| P2-015 tests | 	ests/safety/test_p2_015_safeword.py | ❌ Need to create |
| P2-015 evidence | docs/setup-evidence/P2/STEP-P2-015/safeword-module.txt | ❌ Need to create |
| P2-015 evidence | docs/setup-evidence/P2/STEP-P2-015/safeword-test.png | ❌ Need to create |
| AC-SAFE-001 evidence | evidence/persona-safety/safe-word-runtime-<date>.md | ❌ Need to create |
| Smoke tests | 	ests/smoke/test_safe_word.py | ✅ Existing (XFAIL → update to PASS) |
| P2-015 auditor | udit-reports/P2/STEP-P2-015/step-p2-015-auditor-report.md | ❌ Need to create |

---

## §17 Appendix D: Existing Handler Test Coverage (P1-021 — 56 tests, all PASS)

| Test Class | Tests | What It Covers |
|------------|-------|----------------|
| TestExactTriggers | 12 | 11 exact variants + 3 context-embedded — all case variants + Indonesian |
| TestSemanticTriggers | 16 | "stop the persona", "neutral mode", "aku capek banget", etc. |
| TestFalsePositives | 10 | Normal conversation must NOT trigger |
| TestSafeModePersistence | 2 | No duplicate events, normal messages in safe mode |
| TestRecovery | 9 | 7 recovery variants verified; no recovery from NORMAL |
| TestAuditTrail | 3 | Event logged, multiple trigger cycle, neutral response content |
| TestGuardDecision | 5 | block_on_safe_word, pass_through_normal, recovery_response, block_in_safe |

---

*End of report — 17 sections, 5 safety auditor specifications, 16 planner constraints, 5 blockers identified.*

