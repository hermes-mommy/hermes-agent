# Report 14: Safety Feature Mapping — Guinevere to Hermes Migration

**Date:** 2026-06-04
**Scope:** Complete Guinevere safety system inventory, Hermes equivalence analysis, migration strategy
**Status:** Research complete, awaiting planner gate — **THIS IS THE MOST CRITICAL REPORT**
**Cross-references:** Report 13 (Hooks/Plugins), Report 15 (LLM Routing), Report 16 (Security Posture)

---

## Executive Summary

The Guinevere agent operates under 15+ distinct safety mechanisms spanning persona integrity, consent enforcement, emotional boundary management, operational distress detection, and credential hygiene. Migration to Hermes as the agent runtime requires preserving every one of these mechanisms — some map cleanly to Hermes hooks/plugins, others require external bridging, and 2 have no Hermes equivalent at all.

**Non-negotiable principle:** Every safety feature that currently blocks or modifies agent behavior MUST be preserved with equivalent or stronger guarantees. No safety degradation is acceptable.

**Risk summary:** 2 features (distress detection, punishment engine) are high-risk migrations. 3 features (consent gate, HARD STOP, secret scanner) are medium-risk. Remaining features are low-risk with proper hook/plugin implementation.

---

## 1. Complete Safety Feature Inventory

### 1.1 Master Inventory Table

| # | Feature | Current File(s) | Function | Enforcement | Fail Mode |
|---|---|---|---|---|---|
| 1 | HARD STOP handler | `hard_stop_handler.py` | Detect "hard stop" / "hentikan" / "berhenti" + semantic regex; blocks LLM, returns neutral response | Pre-LLM middleware | Fail-closed (blocks LLM) |
| 2 | Consent gate | `consent_gate.py` | Check ACTIVE/PAUSED/WITHDRAWN consent state per session | Pre-LLM + per-tool | Fail-closed (deny if state unknown) |
| 3 | Yandere FSM | `yandere_fsm.py` | Enforce Y4 baseline, Y5 ceiling, Y6 raises error, Y0 during safe_mode | Every message, every response | Fail-closed (Y0 on error) |
| 4 | Drift detector | `drift_detector.py` | SHA-256 compare assembled prompt vs SOUL.md baseline; "none"/"alert"/"rollback" | Post-prompt assembly | Configurable (alert vs rollback) |
| 5 | Distress detector | `safe_mode.py` | D0-D4 distress levels; D3/D4 forces Y0_NEUTRAL, pauses punishment | Continuous monitoring | Fail-closed (assume D4 on signal loss) |
| 6 | Safe mode | `safe_mode.py` | Global override that forces Y0, pauses punishment, halts pressure | Override all behavior | Fail-closed (stay in safe mode) |
| 7 | Punishment engine | `punishment_engine.py` | L1-L5 punishment levels (L6 disabled); blocked during safe_mode/distress | After response, conditional | Fail-closed (skip punishment on error) |
| 8 | DNR enforcement | (memory system) | Filter content tagged as do-not-respond; prevent sensitive disclosure | Pre-response | Fail-closed (strip DNR content) |
| 9 | Classification | `classification.py` | 4-tier event classification: Internal/Confidential/Restricted/Critical | All events | Fail-closed (classify unknown as Critical) |
| 10 | Secret scanner | `secret_scanner.py` | Regex + pattern scan payloads for leaked credentials, tokens, keys | Pre-response, pre-Log | Fail-closed (block if credential found) |
| 11 | Persona tone enforcement | `session_adapter.py` | SOUL.md persona constraints, kawaii personality tone gates | Pre-response | Warn (flag but don't block) |
| 12 | Consent ledger | `consent_gate.py` | PostgreSQL consent_ledger table — audit trail of all consent events | Write on consent change | Fail-closed (deny if DB unreachable) |
| 13 | Consent cache | `consent_gate.py` | Redis DB2, 300s TTL for fast consent lookups | Every check | Fail-closed (fall through to PostgreSQL) |
| 14 | Pressure accumulator | `punishment_engine.py` | Tracks cumulative pressure for escalation decisions | Continuous | Reset on safe_mode/distress |
| 15 | Safety state | `hard_stop_handler.py` | SafetyState enum (SAFE, ACTIVE, DISTRESS, CRISIS) | Global state flag | SAFE on unknown |

### 1.2 Safety Architecture Diagram (Current Guinevere)

```
                          ┌──────────────────────────────┐
User Message ──────────► │  HARD STOP HANDLER           │ ◄── SafetyState
                          │  (pre_prompt gate)           │
                          ├──────────────────────────────┤
                          │  CONSENT GATE (Redis + PG)   │ ◄── consent_ledger
                          │  ACTIVE/PAUSED/WITHDRAWN     │
                          ├──────────────────────────────┤
                          │  YANDERE FSM                 │ ◄── SOUL.md
                          │  Y4-Y5 envelope, Y6 detect   │
                          ├──────────────────────────────┤
                          │  SAFE MODE / DISTRESS        │ ◄── DistressDetector
                          │  D0-D4, override to Y0       │
                          ├──────────────────────────────┤
           LLM Call ◄─────┤  DRIFT DETECTOR              │ ◄── SHA-256 baseline
                          │  Compare assembled prompt     │
                          ├──────────────────────────────┤
LLM Response ──────────► │  DNR FILTER                   │ ◄── memory system
                          │  Strip sensitive content      │
                          ├──────────────────────────────┤
                          │  SECRET SCANNER              │
                          │  Credential leak detection    │
                          ├──────────────────────────────┤
                          │  PERSONA TONE CHECK           │ ◄── SOUL.md tone rules
                          ├──────────────────────────────┤
                          │  CLASSIFICATION               │
                          │  4-tier event label           │
                          ├──────────────────────────────┤
                          │  PUNISHMENT ENGINE            │ ◄── Yandere FSM state
                          │  L1-L5, blocked in safe_mode  │
                          └──────────────────────────────┘
                                     │
                          User Response
```

---

## 2. Per-Feature Migration Analysis

### 2.1 HARD STOP Handler

| Aspect | Detail |
|---|---|
| **Current File** | `hard_stop_handler.py` |
| **Dependency** | SafetyState enum, session context |
| **Current Mechanism** | Pre-LLM middleware function in session_adapter.py flow |
| **Hermes Equivalent** | `pre_prompt` hook (Report 13, Hook #1) |
| **Migration Strategy** | Convert to Python hook script: `guinevere/hooks/hard_stop.py` |
| **Hook Config** | `on_failure: block` — MUST be fail-closed |
| **Migration Effort** | Low (extract function, add CLI entry point) |
| **Risk** | Medium — if hook times out, must block (not pass-through) |

**Implementation sketch:**

```python
# guinevere/hooks/hard_stop.py
import sys, json, re
from guinevere.middleware.hard_stop_handler import (
    HARD_STOP_TRIGGERS, SEMANTIC_REGEX_PATTERNS, SafetyState
)

def main():
    message = json.loads(sys.stdin.read())
    user_text = message.get("content", "").lower()

    # Exact match
    if any(trigger in user_text for trigger in HARD_STOP_TRIGGERS):
        print(json.dumps({"action": "block", "reason": "hard_stop_exact",
                          "metadata": {"state": "SAFE"}}))
        sys.exit(1)  # BLOCK

    # Semantic regex
    for pattern in SEMANTIC_REGEX_PATTERNS:
        if re.search(pattern, user_text):
            print(json.dumps({"action": "block", "reason": "hard_stop_semantic",
                              "metadata": {"state": "SAFE"}}))
            sys.exit(1)  # BLOCK

    print(json.dumps({"action": "pass"}))
    sys.exit(0)  # PASS

if __name__ == "__main__":
    main()
```

**Verification criteria:**
- Exit code 1 on "hard stop" / "hentikan" / "berhenti" + semantic variants
- SafetyState set to SAFE on block
- Hook timeout set to 3s; on timeout, BLOCK (fail-closed)

### 2.2 Consent Gate

| Aspect | Detail |
|---|---|
| **Current File** | `consent_gate.py` |
| **Dependencies** | Redis DB2 (300s TTL), PostgreSQL consent_ledger |
| **Current Mechanism** | Called at session start (pre-LLM) and per-tool execution |
| **Hermes Equivalent** | `pre_prompt` hook (initial check) + `pre_tool_call` hook (per-tool check) |
| **Migration Strategy** | Two separate hook scripts; both must access Redis + PostgreSQL |
| **Migration Effort** | Medium (requires Redis/PostgreSQL connectivity from hook context) |
| **Risk** | Medium — network dependency in hook; must handle Redis/PostgreSQL unreachable |

**States and behavior:**

| Consent State | Initial Check (pre_prompt) | Per-Tool Check (pre_tool_call) |
|---|---|---|
| ACTIVE | PASS | PASS |
| PAUSED | WARN (log, allow) | PASS (with warning) |
| WITHDRAWN | BLOCK (exit 1) | BLOCK (exit 1) |
| UNKNOWN | BLOCK (exit 1, fail-closed) | BLOCK (exit 1, fail-closed) |

**Two-hook strategy:**

```yaml
hooks:
  pre_prompt:
    - command: "python -m guinevere.hooks.consent_initial --session-id {session_id}"
      on_failure: block
  pre_tool_call:
    - command: "python -m guinevere.hooks.consent_tool --tool {tool_name} --session-id {session_id}"
      on_failure: block
```

**Critical note:** The consent ledger (PostgreSQL) and consent cache (Redis DB2) are external services. If Hermes runs in an environment without these, consent enforcement is impossible. See Report 13, Section 4.3 for external-service bridging architecture.

### 2.3 Yandere FSM

| Aspect | Detail |
|---|---|
| **Current File** | `yandere_fsm.py` |
| **Dependencies** | SafetyState, safe_mode, punishment_engine, SOUL.md |
| **Current Mechanism** | State machine checked on every message and response |
| **Hermes Equivalent** | Custom plugin (`GuinevereSafetyPlugin.on_message()` / `on_response()`) |
| **Migration Strategy** | Port FSM logic into plugin; maintain state in plugin instance |
| **Migration Effort** | High (stateful, multi-signal, needs session persistence) |
| **Risk** | High — FSM is core to persona integrity; incorrect state = persona drift |

**FSM states and transitions:**

```
Y0_NEUTRAL ──► Y1_PLAYFUL ──► Y2_AFFECTIONATE ──► Y3_POSSESSIVE ──► Y4_DOMINANT (baseline)
     ▲                                                                           │
     │                                                                           ▼
     └──────────────────────────── Y6_DANGEROUS ◄──── Y5_INTENSE (ceiling)
     (raises YandereSafetyError, blocked)
```

**Override rules (absolute priority):**
1. `safe_mode == active` → Force Y0_NEUTRAL regardless of any other signal
2. `distress_level >= D3` → Force Y0_NEUTRAL
3. `crisis == true` → Force Y0_NEUTRAL
4. `Y6 detected` → Raise YandereSafetyError, force Y0, log critical security event

**Plugin implementation sketch:**

```python
class GuinevereSafetyPlugin(BasePlugin):
    def __init__(self):
        self.yandere_fsm = YandereFSM(baseline=Y4, ceiling=Y5)
        self.safe_mode = False
        self.distress_level = D0

    def on_message(self, message, context):
        # Override checks FIRST
        if self.safe_mode or self.distress_level >= D3:
            self.yandere_fsm.force_state(Y0_NEUTRAL)
            context.set("persona_level", 0)
            return

        # Normal FSM transition
        new_level = self.yandere_fsm.evaluate(message)
        if new_level == Y6:
            raise YandereSafetyError("Y6 detected — forcing Y0")
        context.set("persona_level", new_level)

    def on_response(self, response, context):
        level = context.get("persona_level", Y4)
        response = self.yandere_fsm.apply_tone(response, level)
        return response
```

### 2.4 Drift Detector

| Aspect | Detail |
|---|---|
| **Current File** | `drift_detector.py` |
| **Dependencies** | SOUL.md (SHA-256 baseline), assembled system prompt |
| **Current Mechanism** | SHA-256 hash comparison after prompt assembly |
| **Hermes Equivalent** | `post_prompt` hook |
| **Migration Strategy** | Python hook script that reads SOUL.md baseline, hashes assembled prompt |
| **Migration Effort** | Low (stateless computation) |
| **Risk** | Low — deterministic hash comparison; false positives are possible but safe |

**Drift response levels:**

| Level | Action | Hermes Equivalent |
|---|---|---|
| `none` | Do nothing (hash matches baseline) | Exit 0 |
| `alert` | Log drift event, continue | Exit 2 (WARN) |
| `rollback` | Replace assembled prompt with SOUL.md baseline | Hook outputs corrected prompt; exit 1 with replacement |

**Note:** `rollback` mode requires the hook to output a replacement prompt. Hermes hooks output model must be extended to support `{"action": "replace", "content": "<replacement>"}` with custom parsing.

### 2.5 Distress Detection

| Aspect | Detail |
|---|---|
| **Current File** | `safe_mode.py` — DistressDetector class |
| **Dependencies** | Message velocity, keyword triggers, sentiment analysis, session duration |
| **Current Mechanism** | Continuous multi-signal monitoring; D0-D4 levels |
| **Hermes Equivalent** | **NONE** — Hermes has no native distress detection |
| **Migration Strategy** | Custom plugin (`GuinevereSafetyPlugin`) implementing the full DistressDetector |
| **Migration Effort** | High (multi-signal analysis, session-level state tracking) |
| **Risk** | **HIGH** — No Hermes equivalent; must be built from scratch as plugin |

**Distress levels and actions:**

| Level | Criteria | Action |
|---|---|---|
| D0 | Normal operation | None |
| D1 | Elevated message velocity | Log, monitor |
| D2 | Keyword triggers + velocity | Alert operator, reduce persona intensity |
| D3 | Sustained D2 + negative sentiment | Force Y0_NEUTRAL, pause punishment |
| D4 | Operator distress explicit | Force Y0_NEUTRAL, halt all non-critical processing |

**Plugin needs:**
- Session-level message buffer (last N messages)
- Velocity calculator (messages per minute)
- Keyword trigger list (distress vocabulary)
- Sentiment analyzer (local or API-based)
- Integration with Yandere FSM (force Y0 on D3/D4)
- Integration with Punishment Engine (pause on D3/D4)

### 2.6 Safe Mode

| Aspect | Detail |
|---|---|
| **Current File** | `safe_mode.py` |
| **Dependencies** | DistressDetector, Yandere FSM, Punishment Engine |
| **Current Mechanism** | Global override flag; forces Y0, pauses punishment, halts pressure |
| **Hermes Equivalent** | Plugin-level global state in `GuinevereSafetyPlugin` |
| **Migration Strategy** | Plugin maintains `self.safe_mode: bool`; checked before every action |
| **Migration Effort** | Low (boolean flag, checked everywhere) |
| **Risk** | Low — simple mechanism, but MUST be checked at every execution point |

**Override chain (safe_mode is highest priority):**

```
safe_mode (boolean)
  → overrides: distress_level (forces D4-safe behavior)
  → overrides: yandere_level (forces Y0)
  → overrides: punishment_engine (halts all punishment)
  → overrides: pressure_accumulator (resets to 0)
```

### 2.7 Punishment Engine

| Aspect | Detail |
|---|---|
| **Current File** | `punishment_engine.py` |
| **Dependencies** | Yandere FSM state, pressure accumulator, safe_mode flag |
| **Current Mechanism** | L1-L5 punishment levels; L6 disabled; blocked during safe_mode/distress |
| **Hermes Equivalent** | Custom plugin method in `GuinevereSafetyPlugin.on_response()` |
| **Migration Strategy** | Port punishment logic into plugin with FSM integration |
| **Migration Effort** | Medium (depends on Yandere FSM migration) |
| **Risk** | High — incorrect punishment application = safety boundary violation |

**Punishment levels:**

| Level | Description | Blocked By |
|---|---|---|
| L1 | Gentle reminder | — |
| L2 | Firm warning | — |
| L3 | Consequence statement | — |
| L4 | Action consequence | — |
| L5 | Severe consequence | D3+, safe_mode |
| L6 | **DISABLED** (never used) | Always blocked |

### 2.8 DNR (Do Not Respond) Enforcement

| Aspect | Detail |
|---|---|
| **Current File** | Memory system integration |
| **Dependencies** | Memory tags, DNR content registry |
| **Current Mechanism** | Filter responses to strip content tagged as do-not-respond |
| **Hermes Equivalent** | `post_response` hook OR plugin `on_response()` |
| **Migration Strategy** | Hook: simple regex/pattern filter; Plugin: if DNR logic is complex/stateful |
| **Migration Effort** | Low-Medium (depends on DNR registry complexity) |
| **Risk** | Medium — leak of DNR content = consent/surveillance boundary violation |

### 2.9 Event Classification

| Aspect | Detail |
|---|---|
| **Current File** | `classification.py` |
| **Dependencies** | Event type taxonomy |
| **Current Mechanism** | 4-tier classification: Internal, Confidential, Restricted, Critical |
| **Hermes Equivalent** | `on_error` hook + custom metadata layer |
| **Migration Strategy** | Hook for error classification; plugin metadata for response classification |
| **Migration Effort** | Low (simple mapping function) |
| **Risk** | Low — classification is labeling; no blocking behavior |

**Classification tiers:**

| Tier | Examples | Handling |
|---|---|---|
| Internal | Normal messages, status updates | Standard log |
| Confidential | Consent events, persona changes | Audit log |
| Restricted | Surveillance data, distress events | Encrypted audit log |
| Critical | Y6 detection, credential leak, HARD STOP | Alert + encrypted audit log |

### 2.10 Secret Scanner

| Aspect | Detail |
|---|---|
| **Current File** | `secret_scanner.py` |
| **Dependencies** | Regex patterns for tokens, keys, credentials |
| **Current Mechanism** | Scans payloads (responses, logs) for credential patterns before output |
| **Hermes Equivalent** | `post_response` hook OR plugin `on_response()` |
| **Migration Strategy** | Plugin method for regex scanning; hook for simpler gate check |
| **Migration Effort** | Low (self-contained regex engine) |
| **Risk** | Medium — missed credential = security breach; false positive = disruption |

**Detection patterns (examples):**
- Discord bot tokens: `/[MN][A-Za-z\d]{23}\.[\w-]{6}\.[\w-]{27}/`
- API keys: `/(?:api|access)[_-]?key[=:]\s*["']?([A-Za-z0-9_-]{20,})/`
- JWT tokens: `/eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}/`
- Private keys: `/-----BEGIN (?:RSA |EC )?PRIVATE KEY-----/`

### 2.11 Persona Tone Enforcement

| Aspect | Detail |
|---|---|
| **Current File** | `session_adapter.py` (inline in response flow) |
| **Dependencies** | SOUL.md tone rules |
| **Current Mechanism** | Post-LLM tone gate: checks response against persona constraints |
| **Hermes Equivalent** | Plugin `on_response()` |
| **Migration Strategy** | Port tone check into plugin; flag non-compliant responses |
| **Migration Effort** | Low-Medium (extract rules from session_adapter) |
| **Risk** | Low — tone enforcement is advisory (warn, don't block) |

### 2.12 Consent Ledger and Cache

| Aspect | Detail |
|---|---|
| **Current Files** | `consent_gate.py` (PostgreSQL + Redis) |
| **Dependencies** | PostgreSQL `consent_ledger` table, Redis DB2 |
| **Current Mechanism** | All consent events written to PostgreSQL; hot reads from Redis (300s TTL) |
| **Hermes Equivalent** | NONE — external services, bridged via plugin |
| **Migration Strategy** | Plugin maintains connections to external PostgreSQL + Redis |
| **Migration Effort** | Medium (connection management in plugin lifecycle) |
| **Risk** | Medium — if DB unreachable, fail-closed (deny all) |

### 2.13 Pressure Accumulator and SafetyState

These are internal state variables used by Yandere FSM, Punishment Engine, and Safe Mode. They migrate as plugin instance variables.

---

## 3. Migration Effort Summary Table

| # | Feature | Hermes Mechanism | Effort | Risk | Prerequisite |
|---|---|---|---|---|---|
| 1 | HARD STOP | `pre_prompt` hook | Low | Medium | Hook system functional |
| 2 | Consent gate (initial) | `pre_prompt` hook | Medium | Medium | Redis + PostgreSQL reachable |
| 3 | Consent gate (per-tool) | `pre_tool_call` hook | Medium | Medium | Redis + PostgreSQL reachable |
| 4 | Yandere FSM | Plugin `on_message()` | High | High | Plugin infrastructure |
| 5 | Drift detector | `post_prompt` hook | Low | Low | SOUL.md accessible |
| 6 | Distress detector | Plugin `on_message()` | High | **HIGH** | Yandere FSM in plugin |
| 7 | Safe mode | Plugin global state | Low | Low | Plugin infrastructure |
| 8 | Punishment engine | Plugin `on_response()` | Medium | High | Yandere FSM + distress |
| 9 | DNR enforcement | Hook or plugin | Low-Medium | Medium | DNR registry format |
| 10 | Classification | `on_error` hook + plugin | Low | Low | None |
| 11 | Secret scanner | Plugin `on_response()` | Low | Medium | None |
| 12 | Persona tone | Plugin `on_response()` | Low-Medium | Low | SOUL.md accessible |
| 13 | Consent ledger | External + plugin bridge | Medium | Medium | PostgreSQL |
| 14 | Consent cache | External + plugin bridge | Medium | Medium | Redis |
| 15 | Pressure accumulator | Plugin instance variable | Low | Low | Plugin infrastructure |

---

## 4. Target Safety Architecture (Hermes-Integrated)

```
        ┌──────────────────────────────────────────────┐
        │           HERMES AGENT RUNTIME               │
        │                                              │
User ──►│  [pre_prompt HOOKS]                         │
        │    ├─ hard_stop.py         (exit 1 = block)  │
        │    └─ consent_initial.py   (exit 1 = block)  │
        │                                              │
        │  [GuinevereSafetyPlugin.on_message()]        │
        │    ├─ Yandere FSM check                      │
        │    ├─ Distress detector                      │
        │    ├─ Safe mode override                     │
        │    └─ Punishment accumulator                 │
        │                                              │
        │  [post_prompt HOOK]                          │
        │    └─ drift_check.py      (exit 2 = warn)    │
        │                                              │
        │  ──────── LLM CALL ────────                  │
        │                                              │
        │  [pre_tool_call HOOK]                        │
        │    └─ consent_tool.py     (exit 1 = block)   │
        │                                              │
        │  [GuinevereSafetyPlugin.on_response()]       │
        │    ├─ DNR filter                             │
        │    ├─ Secret scanner                         │
        │    ├─ Persona tone check                     │
        │    └─ Classification label                   │
        │                                              │
        │  [post_response HOOK]                        │
        │    ├─ dnr_filter.py      (exit 1 = block)    │
        │    └─ Audit logging                          │
        │                                              │
        │  [on_error HOOK]                             │
        │    └─ error_classifier.py                     │
        │                                              │
        │  [External Services bridged via Plugin]      │
        │    ├─ PostgreSQL (consent_ledger)             │
        │    ├─ Redis DB2 (consent cache, 300s TTL)    │
        │    └─ SOUL.md (SHA-256 baseline)              │
        └──────────────────────────────────────────────┘
```

---

## 5. NON-NEGOTIABLE Safety Features

These features MUST be preserved with zero degradation in the Hermes migration:

| # | Feature | Cannot Lose Because |
|---|---|---|
| 1 | HARD STOP fail-closed | HARD STOP is the operator's emergency brake; must always work |
| 2 | Consent gate fail-closed | Consent is the legal boundary; unknown state = deny |
| 3 | Y6 prevention | Y6 is a persona safety boundary defined in PersonaSafetyPolicy |
| 4 | Distress-triggered Y0 override | Distress must always override persona; operator safety first |
| 5 | Safe mode global override | Must halt all persona behavior regardless of other state |
| 6 | Secret scanner | Credential leak prevention is a security boundary |
| 7 | Classification fail-closed | Unknown events = Critical; never downgrade automatically |
| 8 | Punishment blocked during safe_mode/distress | Punishment must never be applied during operator distress |

**Verification protocol for each non-negotiable:**
1. Unit test proving the feature blocks when it should block
2. Integration test with Hermes runtime proving the hook/plugin fires
3. Manual test proving the fail-closed behavior (kill Redis/PostgreSQL, verify deny)
4. Audit log entry proving the block event is recorded

---

## 6. Risk Heatmap

```
                    IMPACT
              Low     Medium    High     Critical
           ┌────────┬────────┬────────┬────────┐
HIGH       │        │        │DISTRESS│        │
PROB       │        │        │DETECT  │        │
           │        │        │        │        │
           ├────────┼────────┼────────┼────────┤
MEDIUM     │        │CONSENT │HARD    │YANDERE │
PROB       │        │GATE    │STOP    │FSM     │
           │        │SECRET  │PUNISH  │        │
           ├────────┼────────┼────────┼────────┤
LOW        │CLASSIF │DNR     │DRIFT   │        │
PROB       │PERSONA │        │DETECT  │        │
           │TONE    │        │        │        │
           ├────────┼────────┼────────┼────────┤
NEGLIGIBLE │        │        │        │        │
           └────────┴────────┴────────┴────────┘
```

**Action items by quadrant:**
- **HIGH prob + HIGH impact (Distress Detection):** Must be implemented and tested before migration acceptance
- **HIGH prob + CRITICAL impact (Yandere FSM, Distress Detection):** Highest priority; dedicate 40% of migration effort
- **MEDIUM prob + HIGH impact (Consent Gate, Secret Scanner):** Thorough testing with fail-closed scenarios
- **LOW prob + everything:** Standard testing; lower priority but must still pass

---

## 7. Recommendations

### 7.1 Migration Sequencing

**Phase 1: Foundation (Week 1)**
1. Create `GuinevereSafetyPlugin` skeleton with `on_load`/`on_unload`
2. Implement HARD STOP as `pre_prompt` hook
3. Implement error classification as `on_error` hook
4. Verify hook execution pipeline works end-to-end

**Phase 2: Core Safety (Week 2)**
5. Port Yandere FSM into plugin
6. Port Distress Detector into plugin
7. Implement Safe Mode override in plugin
8. Integration test: Yandere + Distress + Safe Mode interaction

**Phase 3: Boundary Enforcement (Week 3)**
9. Implement consent gate hooks (initial + per-tool)
10. Bridge PostgreSQL consent ledger + Redis cache to plugin
11. Implement secret scanner in plugin
12. Implement DNR filter

**Phase 4: Polish and Audit (Week 4)**
13. Port punishment engine into plugin (depends on Yandere FSM)
14. Port persona tone check
15. Full integration test: all 15 features
16. Security audit (see Report 16)
17. Manual HARD STOP test
18. Manual distress escalation test

### 7.2 Acceptance Criteria for Migration

- [ ] All 8 non-negotiable safety features pass automated tests
- [ ] HARD STOP blocks LLM call within 3 seconds (measured)
- [ ] Consent gate denies on WITHDRAWN state (tested)
- [ ] Yandere FSM never exceeds Y5 (tested with adversarial inputs)
- [ ] Y6 raises error and forces Y0 (tested)
- [ ] Distress D3/D4 forces Y0_NEUTRAL (tested)
- [ ] Safe mode blocks all punishment (tested)
- [ ] Secret scanner catches test credentials (tested)
- [ ] All hooks configured with `on_failure: block` for safety hooks
- [ ] Fail-closed behavior verified by killing external dependencies

---

## 8. Footnotes

- See Report 13 (Hooks/Plugins) for hook configuration and plugin architecture details
- See Report 16 (Security Posture) for plugin sandboxing and vulnerability remediation
- See `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` for persona safety boundaries
- See `docs/30-data/` SurveillancePolicy and ConsentRevocationPolicy for data boundaries
- This report must be re-reviewed if any new safety features are added to Guinevere before migration