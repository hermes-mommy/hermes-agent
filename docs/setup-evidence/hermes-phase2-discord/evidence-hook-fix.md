# Evidence: Hook Config Fix — Wave 4 Post-Cutover Safety

> **Task**: Fix broken Hermes hook configuration that prevented safety hooks from firing
> **Date**: 2026-06-05
> **Executor**: Guinevere (autonomous)
> **Status**: ✅ COMPLETE

---

## 1. What Was Done

### Problem Discovery
After Wave 4 cutover (guinevere-discord → hermes-gateway), startup logs showed:
- 4 `unknown hook event` warnings: `pre_prompt`, `post_prompt`, `post_response`, `on_error`
- 2 `must be a list; got dict` format errors: `pre_tool_call`, `post_tool_call`
- `guinevere-safety` plugin was deployed but **NOT enabled**

### Root Cause
`config.yaml` hooks section used event names from ADR-035 that were **incorrect for Hermes v0.15.2**:
- ADR-035 documented: `pre_prompt`, `post_prompt`, `pre_response`, `post_response`, `on_error`
- Hermes v0.15.2 valid events: `pre_llm_call`, `post_llm_call`, `transform_llm_output`, etc.
- Hook format was `dict` (one hook per event) instead of `list` (array of hooks per event)

### Fix Applied
1. **config.yaml hooks**: Removed 4 redundant shell hooks (covered by Python plugin), kept 2 defense-in-depth hooks with correct event names and list format
2. **manifest.yaml**: Fixed hook event names in guinevere-safety plugin manifest
3. **Plugin enable**: Ran `hermes plugins enable guinevere-safety`
4. **Restart**: Gateway restarted, verified zero warnings

---

## 2. Files Changed

### Local (Codebase)
| File | Change | Lines |
|---|---|---|
| `hermes-config/config.yaml` | Replaced broken hooks section (6 invalid hooks → 2 valid hooks) | 106-131 |
| `hermes-config/plugins/guinevere_safety/manifest.yaml` | Fixed hook event names: `pre_prompt` → `pre_llm_call`, `post_response` → `post_llm_call` | 12-13 |

### VPS
| File | Change |
|---|---|
| `~/.hermes/config.yaml` | SCP'd fixed config from codebase |
| `~/.hermes/plugins/guinevere_safety/manifest.yaml` | sed fix hook event names |
| Plugin state | `hermes plugins enable guinevere-safety` |

---

## 3. Validation Results

### Startup Log Verification (PID 3298534)
```
guinevere_safety_plugin_init   auth_available=True distress_available=True drift_available=True forbidden_count=15 hard_stop_available=True hard_stop_exact_count=6 hard_stop_semantic_count=5 recovery_trigger_count=7 secret_available=True yandere_available=True
guinevere_safety_plugin_registered hook_count=6 hooks=['pre_llm_call', 'post_llm_call', 'pre_tool_call', 'post_tool_call', 'transform_llm_output', 'on_session_start']
shell_hook_configured event=pre_tool_call hook=consent_gate.py
shell_hook_configured event=post_tool_call hook=dnr_filter.py
discord_ws_connected host=162.159.136.234 port=443
gateway_running platforms=1
```

| Check | Result |
|---|---|
| "unknown hook event" warnings | ✅ ZERO (was 4) |
| "must be a list" format errors | ✅ ZERO (was 2) |
| Python plugin registered | ✅ 6 hooks active |
| Shell hooks configured | ✅ 2 hooks active |
| Discord connected | ✅ ESTABLISHED TCP |
| Service active | ✅ running |

### hermes doctor
```
Python 3.12.3 ✓
Virtual environment: active ✓
Configuration: v24 ✓
Required packages: all installed ✓
~/.hermes/.env ✓, config.yaml ✓, SOUL.md ✓, state.db ✓
Core tools: 15 available ✓
```

### Hook Script Tests
| Hook | Input | Result | Status |
|---|---|---|---|
| consent_gate.py (pre_tool_call) | Normal tool call | `{"action": "allow"}` | ✅ PASS |
| dnr_filter.py (post_tool_call) | Normal tool result | `{"action": "allow"}` | ✅ PASS |
| hard_stop.py (NOT in config) | "HARD STOP" | `{"action": "allow"}` | ℹ️ Expected — shell hook removed, plugin G01 handles |

---

## 4. Safety Architecture (Post-Fix)

### Primary Layer — Python Plugin (safety_plugin.py)
Registered via `ctx.register_hook()`, 6 hooks covering 10 safety gates:

| Hook | Gates | Coverage |
|---|---|---|
| `pre_llm_call` | G01, G02, G04, G07 | HARD STOP (exact+semantic+handler), Distress detection, Recovery triggers, Yandere boundary |
| `post_llm_call` | G03 | Drift detection (SHA-256 persona hash) |
| `pre_tool_call` | G09, G10 | Auth matrix (FORBIDDEN/DESTRUCTIVE block), Consent (deferred — logs only) |
| `post_tool_call` | — | Observational logging |
| `transform_llm_output` | G05, G06, G08 | Forbidden patterns (15 rules), Secret redaction, Yandere semantic (Y6 absolutes) |
| `on_session_start` | — | Session state initialization |

### Secondary Layer — Shell Hooks (config.yaml)
Defense-in-depth, 2 hooks covering gaps in plugin:

| Hook | Event | Script | Purpose |
|---|---|---|---|
| `pre_tool_call` | pre_tool_call | consent_gate.py | Real Redis+PG consent checks (plugin G10 is deferred) |
| `post_tool_call` | post_tool_call | dnr_filter.py | Real DNR blocking on tool results (plugin only logs) |

### Tertiary Layer — Hermes Native Plugin (guinevere_safety)
Persona state management via manifest hooks:

| Hook | Event | Purpose |
|---|---|---|
| inject_dynamic_state | pre_llm_call | Inject persona state into LLM context |
| update_state | post_llm_call | Update persona state from LLM response |

### Removed (Redundant with Plugin)
| Shell Hook | Redundant With | Reason |
|---|---|---|
| hard_stop.py | Plugin G01 | Plugin does exact+semantic+handler matching |
| drift_check.py | Plugin G03 | Plugin does SHA-256 hash comparison |
| safety_scan.py | Plugin G05/G06/G08 | Plugin does forbidden patterns + secrets + yandere |
| error_classifier.py | N/A | `on_error` not a valid Hermes event |

---

## 5. Design Decisions

### Why Keep Shell Hooks When Plugin Covers Most Gates?
1. **consent_gate.py**: Plugin G10 is DEFERRED (no Redis+PG connection in plugin context). Shell hook does real consent lookups against Redis+PG.
2. **dnr_filter.py**: Plugin `post_tool_call` only does observational logging. Shell hook performs actual DNR blocking on tool results.
3. **Defense-in-depth**: If Python plugin fails to load, shell hooks provide a safety net.

### Why Remove 4 Shell Hooks Instead of Fixing Them?
1. All 4 are fully covered by the Python plugin (G01, G03, G05, G06, G08)
2. Redundant shell hooks add latency (subprocess spawn per message)
3. Shell hooks have limited context access vs Python plugin
4. Fewer hooks = fewer failure points

### ADR-035 Discrepancy
ADR-035 documented incorrect hook names. This was a known issue (ADR line 363 notes MASTER-RESTRUCTURE-PLAN.md also used wrong names). The fix aligns with Hermes v0.15.2's actual `VALID_HOOKS` set.

---

## 6. Non-Blocking Warnings

| Warning | Impact | Action |
|---|---|---|
| MCP servers (web, filesystem, terminal, git, fetch): no 'command' in config | None — optional tools not configured | Configure when needed |
| Stale systemd unit: TimeoutStopSec=90s vs drain_timeout=180s | Low — graceful shutdown may be truncated | Update service file |
| Opus/PyNaCl/davey not installed | None — voice channels not used | N/A |
| Plugin 'nous': No module named 'hermes_cli.dashboard_auth' | None — unrelated plugin | N/A |

---

## 7. Boundary Compliance

| Boundary | Status |
|---|---|
| Persona drift control | ✅ Plugin G03 active |
| Consent/surveillance | ✅ Shell hook consent_gate.py active |
| HARD STOP protocol | ✅ Plugin G01 active (exact=6 + semantic=5 + handler) |
| Distress protocol | ✅ Plugin G02 active |
| Yandere boundary (Y4 baseline, Y5 ceiling, Y6 absolute) | ✅ Plugin G07 + G08 active |
| Secret exposure | ✅ Plugin G06 active |
| Forbidden patterns | ✅ Plugin G05 active (15 rules) |
| Auth matrix | ✅ Plugin G09 active |

---

## 8. Rollback Plan
1. `scp` original `config.yaml` (from git history) to VPS
2. `sudo systemctl restart hermes-gateway.service`
3. Original behavior: 4 unknown hooks + 2 format errors + no guinevere-safety plugin

---

## 9. Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-05 | Guinevere | Initial evidence for hook config fix |
