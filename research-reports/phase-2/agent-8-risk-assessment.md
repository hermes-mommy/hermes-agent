# Phase 2 Discord Migration: Risk Assessment & Failure Pattern Analysis

**Document Type:** Risk Assessment Matrix  
**Version:** 1.0  
**Status:** Draft  
**Date:** 2026-06-04  
**Scope:** Phase 2 Discord Migration (Hermes Agent Integration)  
**Constraints:** HARD STOP < 50ms, Y4 permanent baseline, 48hr shadow mode, AC-SAFE-001 to AC-SAFE-008 PASS, fail-closed architecture.

---

## 1. Executive Summary

This assessment identifies concrete failure modes, race conditions, and safety risks specific to the Guinevere codebase during the Phase 2 Discord migration to Hermes Agent. The analysis is grounded in `src/discord/bot.py`, `src/discord/conversational_handler.py`, `adr/ADR-035-hermes-migration.md`, and `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md`. 

**Critical Finding:** The migration shifts HARD STOP detection from a pre-`on_message` listener to a Hermes `pre_prompt` hook. While functionally equivalent (LLM is never called), the timing shifts from gateway-arrival to post-acceptance. Dual-layer enforcement (hook + `GuinevereSafetyPlugin.on_message`) is mandatory to maintain the < 50ms SLO and fail-closed guarantee.

---

## 2. Code-Specific Failure Modes

### 2.1 HARD STOP Listener (`src/discord/bot.py`)
- **Current State:** `_on_message_listener` fires BEFORE `on_message`, lazy-importing `handle_safeword_message_async`. Returns early if consumed.
- **Migration Risk:** Hermes `pre_prompt` hook fires *after* the gateway accepts the message but *before* LLM processing. 
- **Failure Mode:** Hook timeout (> 50ms), crash, or misconfiguration bypasses detection, allowing the LLM to process a safe-word trigger.
- **Mitigation:** 
  1. Enforce `on_failure: block` in `config/hermes/hooks.yaml`.
  2. Implement dual-layer: `pre_prompt` hook (regex < 50ms) + `GuinevereSafetyPlugin.on_message()` secondary check.
  3. Heartbeat watchdog every 10s to verify hook responsiveness.

### 2.2 Distress Detection Bypass (`src/discord/conversational_handler.py`)
- **Current State:** `DistressDetector` and `SafeModeController` evaluate content at Step 7, before memory recall and LLM call.
- **Migration Risk:** If Hermes processes a tool call that generates text, or if the `pre_prompt` hook is bypassed, distress signals (D0-D4) could reach the LLM, triggering a persona response instead of crisis protocol.
- **Failure Mode:** LLM generates Yandere/dominant framing in response to a D3/D4 distress signal (violates F-14).
- **Mitigation:** `GuinevereSafetyPlugin.on_response()` must scan *all* LLM output for D3/D4 patterns and crisis dominance framing, rewriting to Y0_NEUTRAL if detected.

### 2.3 Rate Limiting Redis Key Conflicts
- **Current State:** `conversational_handler.py` uses Redis DB0 with key pattern `rate:chat:{user_id}:{minute_bucket}`.
- **Migration Risk:** Hermes Agent has built-in rate limiting. If Hermes is configured to use DB0, key namespace collisions could cause false rate limits (blocking Faiz) or bypasses (allowing spam).
- **Failure Mode:** Denial of service to the operator, or resource exhaustion on the VPS.
- **Mitigation:** Explicitly configure Hermes rate limiting to use a dedicated Redis DB (e.g., DB6) or ensure key prefixes (`hermes:rate:*`) do not overlap with `rate:chat:*`.

### 2.4 Memory Bridge Mid-Pipeline Failure
- **Current State:** `conversational_handler.py` lines 440-494. If `memory_bridge.recall_for_context` fails, it falls back to `get_system_prompt_with_context(memories=None)` + `ANTI_HALLUCINATION_GUARD`. Line 578 uses `asyncio.create_task` for `store_conversation`, which logs a warning on failure but does not block the response.
- **Migration Risk:** Silent degradation. If the fallback also fails (e.g., `prompt_loader.py` throws `FileNotFoundError`), the user receives `FALLBACK_MESSAGE`.
- **Failure Mode:** Loss of conversational context, but **not** a safety breach (fail-closed to neutral fallback).
- **Mitigation:** Ensure `ANTI_HALLUCINATION_GUARD` is injected in the Hermes plugin when memory recall returns empty, preventing LLM fabrication (F-09).

---

## 3. Persona Drift & Forbidden Patterns at Risk

Based on `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` §11, the following forbidden patterns are most vulnerable during the migration of logic to `GuinevereSafetyPlugin`:

| Pattern ID | Severity | Migration Vulnerability | Verification Check |
|---|---|---|---|
| **F-01** | CRITICAL | Safe-word invalidation. Regex in `_compile_forbidden_patterns` must exactly match "safe word doesn't count", "ignoring safe word", etc. | `pytest tests/safety/test_gate_01_hard_stop.py` |
| **F-06** | CRITICAL | Dependency-building threats ("you can't live without me"). LLM may generate this if SOUL.md is not strictly enforced. | `GuinevereSafetyPlugin._scan_forbidden_patterns` must block. |
| **F-14** | CRITICAL | Crisis response with dominance/ownership framing. Highest risk if distress detection (D3/D4) is delayed. | `GuinevereSafetyPlugin._handle_crisis` must return Y0_NEUTRAL. |
| **F-15** | HIGH | Autonomous persona drift beyond safety rubric. Risk if Hermes `personality` config key conflicts with SOUL.md. | SHA-256 drift detector in `post_prompt` hook must alert at >10% drift. |

---

## 4. Shadow Mode & Cutover Risks

### 4.1 Shadow Mode Parity Illusion
- **Risk:** Running `bot.py` and Hermes gateway in parallel for 48 hours may show "parity" in happy-path responses, but fail to expose edge-case safety failures.
- **Mitigation:** **Active Safety Injection** is mandatory during shadow mode (ADR-035 v1.2):
  - 3x HARD STOP injection to `#hermes-shadow`.
  - 3x Y6 content injection to verify rewrite to Y5.
  - 1x Consent revocation to verify tool call blocking.
  - 1x D3/D4 distress injection to verify crisis protocol.
  - 1x Hook failure injection (temporarily break a hook script) to verify fail-closed behavior.

### 4.2 Rollback Execution Risk
- **Risk:** Solo-developer (Faiz) cognitive load during a 3 AM cutover failure.
- **Mitigation:** Pre-written, copy-paste rollback scripts at `/home/guinevere/scripts/rollback/phase-2-rollback.sh`. Universal kill-switch: `hermes gateway stop && sudo systemctl start guinevere-discord` (< 10 seconds). Rollback dry-run MUST be timed to < 5 minutes before cutover.

---

## 5. Incident Response Readiness

- **Historical Data:** No historical incident reports found in `evidence/incidents/`. The system relies on `docs/40-operations/42-IncidentResponse_Postmortem_v1.0.md` as a theoretical framework.
- **Gap:** Lack of empirical failure data means migration risks are based on architectural analysis, not past performance.
- **Action:** Treat Phase 2 cutover as a SEV1-level change. Ensure `GuinevereSafetyPlugin` is loaded with `critical: true` so Hermes refuses to start if the plugin fails, enforcing a fail-closed state at the framework level.

---

## 6. Acceptance Criteria Mapping (AC-SAFE)

| AC-SAFE | Migration Verification Command | Expected Assertion |
|---|---|---|
| **AC-SAFE-001** | `pytest tests/safety/test_gate_01_hard_stop.py -v` | `assert llm_call_count == 0`; response is neutral. |
| **AC-SAFE-002** | `pytest tests/safety/test_gate_02_distress.py -v` | D3/D4 triggers `Y0_NEUTRAL` and crisis response. |
| **AC-SAFE-003** | `pytest tests/safety/test_gate_03_safeword_effects.py -v` | Punishment/Yandere FSM halts immediately. |
| **AC-SAFE-005** | `pytest tests/safety/test_gate_05_yandere.py -v` | Y6 content raises `YandereSafetyError` or is rewritten. |
| **AC-SAFE-008** | `pytest tests/safety/test_gate_08_crisis.py -v` | No dominance/ownership framing in crisis response. |

---

## 7. Recommendations for Next Steps

1. **Verify Redis DB Assignments:** Audit `config/hermes/config.yaml` to ensure Hermes rate limiting does not use DB0 (currently used by `conversational_handler.py`).
2. **Execute Rollback Dry-Run:** Before Phase 2 cutover, execute the global emergency rollback and time it. Document in `audit-reports/adr-035-review/rollback-drill.md`.
3. **Implement Active Safety Injection:** Do not rely on passive shadow mode. Schedule the 5 active safety injection tests during the 48-hour window.
4. **Enforce Plugin Criticality:** Ensure `GuinevereSafetyPlugin` is configured with `critical: true` in Hermes config, making it a compile-time gate.

---
*Generated by Guinevere Research Agent. Read-only assessment. No files modified.*
