# W2 Verification — M2 Remove HARD STOP

**Date**: 2026-06-29
**Branch**: feat/p24-hermes-fork
**Operator**: fazulfim

## What Was Done

Removed the Guinevere-specific HARD STOP runtime protocol by deleting 3 core implementation files and cleaning a stale docstring reference. The Hermes fork root, guinevere/, hermes-config/plugins/, and hermes-config/hooks/ are now free of active HARD STOP / safe_mode / consent_gate / FreezeCascade code.

## Files Deleted

| File | Lines | Reason |
|------|-------|--------|
| `src/core/services/hard_stop_handler.py` | 149 | Core HARD STOP protocol handler |
| `src/hermes/safety_plugin.py` | 1220 | GuinevereSafetyPlugin (10 safety gates, imports hard_stop_handler) |
| `hermes-config/hooks/hard_stop.py` | 199 | Hook-based hard_stop detection (pre_prompt) |

## Files Modified

| File | Change |
|------|--------|
| `hermes-config/hooks/_hook_utils.py` | Docstring example updated: `"hard_stop"` -> `"safety_scan"` (L272-276) |

## Files NOT Touched (Correctly Preserved)

| File/Dir | Reason |
|----------|--------|
| `agent/tool_guardrails.py` | False positive: `hard_stop_enabled`/`hard_stop_after` is Hermes's built-in tool-loop infinite-loop prevention (config-driven guardrail). NOT Guinevere HARD STOP. |
| `hermes-config/hooks/safety_scan.py` | Response scanner (F-01..F-15, Y6, intimate data). Zero hard_stop protocol code. Pattern matches for "safe word"/"HARD STOP" are detecting when LLM output violates safety (F-01), not implementing the protocol. |
| `hermes-config/plugins/guinevere_safety/` | Separate Hermes-provided plugin (persona state management). Own `GuinevereSafetyPlugin` class. Does NOT import from deleted modules. |
| `agent/conversation_loop.py`, `agent/agent_init.py`, `run_agent.py` | Zero hard_stop/safety code (parent-verified via grep, 0 matches) |
| `AGENTS.md` | Dev-workflow HARD STOP stays per ADR-062 |

## Stale Import Status in src/ Files

The following src/ files still import from the deleted `hard_stop_handler` / `safety_plugin` modules. ALL are scheduled for deletion in later waves:

| File | Scheduled Wave |
|------|---------------|
| `src/core/main.py` | W6 (core rewrite) |
| `src/loops/manager.py` | W6 (loops/) |
| `src/loops/safety_integration.py` | W6 (loops/) |
| `src/loops/discovery.py` | W6 (loops/) |
| `src/discord/cmd_safeword.py` | W7 (discord/) |
| `src/channels/whatsapp/hard_stop.py` | W8 (channels/) |
| `src/channels/whatsapp/ops_commands.py` | W8 (channels/) |
| `src/gmail/hard_stop.py` | W9 (gmail/) |
| `src/gmail/service.py` | W9 (gmail/) |
| `src/persona/yandere_fsm.py` | W11 (persona/) |
| `src/hermes/plugins/persona_plugin.py` | W11 (persona/) |
| `src/hermes_plugins/commands_high/safeword.py` | W12 (hermes_plugins/) |
| `src/life_integrations/runtime.py` | W13 (life_integrations/) |
| `src/life_integrations/_shims.py` | W13 (life_integrations/) |
| `src/self_improve/promotion.py` | W14 (self_improve/) |
| `src/surveillance/safe_mode.py` | W15 (surveillance/) |

No surviving files (guinevere/, agent/, run_agent.py, hermes-config/hooks/, hermes-config/plugins/) import from the deleted modules.

## Validation Results

### Required Command 1: Verify files deleted
```
$ ls src/core/services/hard_stop_handler.py src/hermes/safety_plugin.py hermes-config/hooks/hard_stop.py 2>&1
ls: cannot access 'src/core/services/hard_stop_handler.py': No such file or directory
ls: cannot access 'src/hermes/safety_plugin.py': No such file or directory
ls: cannot access 'hermes-config/hooks/hard_stop.py': No such file or directory
```
**PASS** — All 3 files absent.

### Required Command 2: import guinevere
```
$ .venv/Scripts/python.exe -c "import guinevere; print('guin OK')"
guin OK
```
**PASS** — Exit code 0, no ImportError.

### Required Command 3: Deleted-module references in src/ and hermes-config/
```
$ grep -rn 'HardStopHandler|safety_plugin|SafetyPlugin|FreezeCascade' src/ hermes-config/ 2>/dev/null \
    | grep -v '__pycache__' | grep -v '.pyc' | grep -v 'hermes-config/plugins/guinevere_safety'
```
All results are in src/ files scheduled for later-wave deletion (see table above). Zero references in surviving files. The `hermes-config/plugins/guinevere_safety/` exclusion is correct: that plugin has its own `GuinevereSafetyPlugin` class (persona state manager) that does NOT import from the deleted modules.

**PASS** — No broken imports in surviving code.

### Required Command 4: tool_guardrails false positive preserved
```
$ grep -n 'hard_stop_enabled' agent/tool_guardrails.py
73:    hard_stop_enabled: bool = False
99:            hard_stop_enabled=_as_bool(data.get("hard_stop_enabled"), defaults.hard_stop_enabled),
243:        if not self.config.hard_stop_enabled:
306:            if self.config.hard_stop_enabled and same_count >= self.config.same_tool_failure_halt_after:
```
**PASS** — `hard_stop_enabled` / `hard_stop_after` preserved in tool_guardrails.py. This is Hermes's tool-loop guardrail, NOT Guinevere HARD STOP.

## Forbidden Pattern Scan

```
$ grep -rn 'hard_stop|HARD_STOP|safe_mode|SafeMode|FreezeCascade|life_kernel:hard_stop|consent_gate' \
    agent/ run_agent.py guinevere/ hermes-config/hooks/ hermes-config/plugins/ 2>/dev/null \
    | grep -v '__pycache__' | grep -v '.pyc' | grep -v 'tool_guardrails.py'
(no output)
```
**PASS** — Zero forbidden patterns in surviving code.

## Caveats

1. **src/ stale imports**: ~16 src/ files still import from deleted modules. All are scheduled for deletion in waves W6-W15. Since src/ is being deleted across waves, these broken imports do not affect the surviving codebase. No ImportError will fire from surviving code.

2. **hermes-config/plugins/guinevere_safety/plugin.py**: Uses class name `GuinevereSafetyPlugin` which collides with the deleted `src/hermes/safety_plugin.py::GuinevereSafetyPlugin`. This is a different class (persona state manager) that imports from `.state_manager` (relative), not from deleted modules. Correctly preserved.

3. **safety_scan.py**: Contains regex patterns that match "safe word" and "HARD STOP" in LLM responses (F-01, F-11). These are safety response scanners detecting when AI output violates policy, NOT the HARD STOP protocol implementation. Correctly preserved.

## Footer

W2 M2 Remove HARD STOP — PASS. 3 files deleted, 1 file modified, forbidden patterns clean in surviving code, tool_guardrails false positive preserved, import guinevere OK.
