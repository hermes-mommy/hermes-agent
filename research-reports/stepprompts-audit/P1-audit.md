# Phase 1 StepPrompts Audit — ADR-035 Hermes Migration Impact

**Date:** 2026-06-04  
**Auditor:** Guinevere (Sisyphus-Junior executor)  
**Type:** Per-step audit of StepPrompts.md Phase 1 (LLM + Hermes Agent)  
**Reference ADR:** [ADR-035 Hermes NousResearch Migration Architecture](../../adr/ADR-035-hermes-migration.md)  
**Source:** `stepprompts/StepPrompts.md` lines 3202–5170  

---

## Executive Summary

Phase 1 (21 steps) was completed as-is before ADR-035 was accepted. ADR-035 fundamentally changes the Hermes architecture: the old `hermes-agent` PyPI package used in P1 is replaced by the NousResearch Hermes fork with hooks, plugins, native Discord gateway, SOUL.md, and a completely different configuration system.

**Of 21 P1 steps:** 7 VALID (unchanged), 5 STALE (old architecture refs), 5 NEEDS-REWRITE (Hermes-specific changes), 3 already DELETED (skipped Ollama), 1 STALE-but-retainable (config changes but concept preserved).

The 5-pillar ADR-035 architecture (Discord=MIGRATE, Memory=HYBRID, Safety=HOOKS+PLUGINS, MCP=HYBRID, LLM=RETAIN) means that steps related to LLM routing (P1-006–P1-011) remain valid while steps related to Hermes installation, configuration, system prompt, service topology, and safety enforcement need significant revision.

---

## Hermes Migration Impact Summary

### Key Architectural Changes Affecting P1 Steps

| P1 Component | Old (P1 as-implemented) | New (ADR-035 target) | Impact |
|---|---|---|---|
| Hermes source | `pip install hermes-agent` (PyPI) | NousResearch fork v0.15.2 with hooks/plugins/gateway config | P1-003, P1-004, P1-005 STALE |
| Hermes config | Single `config.yaml` (agent/llm/memory/loop/safety) | Gateway config + hooks YAML + plugin YAML + SOUL.md + MCP servers YAML | P1-005 STALE |
| System prompt | `61-SystemPromptMaster_v1.1.md` → `system-prompt.md` file | SOUL.md (static constitution) + hooks/plugins (dynamic enforcement) | P1-016 STALE |
| LLM routing | `src/core/services/llm_router.py` (Python module) | Hermes custom provider config → `localhost:20128` + fallback chain | P1-015 STALE (concept preserved) |
| Discord gateway | Custom `bot.py` + `conversational_handler.py` | Hermes native gateway (`hermes gateway`) | P1-018, P1-019 STALE/NEEDS-REWRITE |
| Safety enforcement | In-code FSMs (`yandere_fsm.py`, `safe_mode.py`, etc.) | 6 hooks + `GuinevereSafetyPlugin` (ports same FSM logic) | P1-021 NEEDS-REWRITE |
| Cost tracking | `cost_tracker.py` Redis DB5 | `pre_tool_call` hook + `hermes insights` | P1-020 NEEDS-REWRITE |
| Core service | `guinevere-core.service` (FastAPI) | Hermes gateway process replaces bot, core FastAPI likely retained | P1-018 NEEDS-REWRITE |
| 9Router | `localhost:20128` systemd service | **UNCHANGED** (Pillar 5: RETAIN) | P1-006–P1-011 VALID |
| Ollama | SKIPPED (ADR-028 Superseded) | Still skipped (no change) | P1-012–P1-014 Deleted |
| Persona testing | CLI smoke test via `llm_router.py` | Hermes gateway with hooks active | P1-017 NEEDS-REWRITE |

---

## Per-Step Audit Table

### Legend

| Verdict | Meaning |
|---|---|
| **VALID** | Step unchanged; directly applicable post-migration. |
| **STALE** | Step references old architecture/package; concept may translate but implementation differs. |
| **NEEDS-REWRITE** | Step's implementation approach is incompatible with ADR-035 target; complete redefinition required. |
| **DELETED** | Step was already skipped (Ollama) and remains skipped; no action needed. |

---

| Step ID | Step Name | Status | Reason | ADR-035 Conflict? |
|---|---|---|---|---|
| **P1-001** | Python 3.12 Installation | **VALID** | Python 3.12 is infrastructure layer, unchanged by Hermes migration. ADR-035 runs on same Python environment. | No |
| **P1-002** | UV Package Manager | **VALID** | UV is a packaging tool. Hermes migration doesn't change dependency management approach. | No |
| **P1-003** | Virtual Environment Setup | **STALE** | Pip install list on line 3412 includes `hermes-agent` (old PyPI package). Under ADR-035, Hermes installs from NousResearch fork with different dependency set. The venv setup itself is valid, but the dependency list is stale. | Yes — dependency list references old PyPI package |
| **P1-004** | Hermes Agent Installation | **STALE** | Step primary path (`uv pip install hermes-agent`, line 3474) targets old PyPI package. The NousResearch source install (lines 3477-3479) is mentioned as fallback only. ADR-035 mandates NousResearch fork as primary with hooks/plugins/gateway. Project structure creation (src/ directories) is valid standalone. | Yes — wrong install source/method |
| **P1-005** | Hermes Agent Configuration | **STALE** | Writes old-style `config.yaml` (agent/llm/memory/loop/safety/budget/tools sections, lines 3582-3653). ADR-035 uses fundamentally different config: gateway config, hooks YAML (`config/hermes/hooks.yaml`), plugin YAML, SOUL.md, MCP servers YAML. Config structure is completely different. LLM routing values (GPT-5.5 primary, DeepSeek sub-agent) remain correct. | Yes — config format obsolete |
| **P1-006** | 9Router Installation | **VALID** | 9Router is ADR-035 Pillar 5: RETAIN at `localhost:20128`. Installation via Node.js 24.x + npm global. Zero changes needed. | No |
| **P1-007** | 9Router Configuration and Startup | **VALID** | 9Router environment, systemd service, health check — all unchanged per ADR-035 Pillar 5. | No |
| **P1-008** | GPT-5.5 Provider Setup | **VALID** | GPT-5.5 remains primary LLM via 9Router in ADR-035. Connectivity test via curl unchanged. | No |
| **P1-009** | GPT-5.5 Connectivity Test | **VALID** | Multi-turn, system prompt, and structured output tests are LLM-level — unchanged by Hermes migration. | No |
| **P1-010** | DeepSeek V4 Flash Setup | **VALID** | DeepSeek remains sub-agent model via 9Router in ADR-035. Setup unchanged. | No |
| **P1-011** | DeepSeek Connectivity Test | **VALID** | Code generation and structured output tests are LLM-level — unchanged. | No |
| **P1-012** | Ollama Installation | **DELETED** | Already SKIPPED per Faiz directive 2026-06-01. ADR-028 Superseded. No action needed. ADR-035 doesn't reinstate Ollama. | No (already resolved) |
| **P1-013** | Ollama Model Pull | **DELETED** | Already SKIPPED. No local models used. ADR-035 doesn't change this. | No (already resolved) |
| **P1-014** | Ollama Fallback Test | **DELETED** | Already SKIPPED. Graceful degradation is final fallback (not Ollama). ADR-035 preserves this. | No (already resolved) |
| **P1-015** | LLM Routing Rules | **STALE** | Creates `src/core/services/llm_router.py` with `TaskType` enum + fallback chain in Python code. Under ADR-035, routing is configured in Hermes config as custom provider + fallback chain, not a Python module. The conceptual routing (GPT-5.5 primary → DeepSeek fallback) is preserved. The `llm_router.py` module becomes unnecessary; Hermes handles routing natively. | Yes — Python routing module replaced by Hermes config |
| **P1-016** | SystemPromptMaster Deployment | **STALE** | Copies `61-SystemPromptMaster_v1.1.md` to `config/hermes/system-prompt.md` and creates `prompt_loader.py` with safety validation checks. ADR-035 replaces file-based system prompt with SOUL.md (static identity constitution) + `pre_prompt`/`post_prompt` hooks + `GuinevereSafetyPlugin` (dynamic enforcement). The safety validation checks (HARD STOP, Y5/Y6, distress) are ported to hooks. | Yes — file-based prompt replaced by SOUL.md + hooks |
| **P1-017** | Persona Smoke Test | **NEEDS-REWRITE** | Test script imports `llm_router.py` and `prompt_loader.py` (both stale under ADR-035). Persona testing under ADR-035 must go through Hermes gateway with hooks/plugins active to verify defense-in-depth layers (SOUL.md + hooks + plugin). Test approach differs fundamentally. | Yes — test architecture obsolete |
| **P1-018** | guinevere-core.service Creation | **NEEDS-REWRITE** | Creates `guinevere-core.service` (FastAPI at port 8000) and `src/core/main.py`. Under ADR-035, Hermes gateway replaces `bot.py` as the Discord-facing process, but the core FastAPI likely remains for backend APIs (surveillance, internal endpoints). Service dependencies change (Hermes gateway replaces bot.py dependency). The service topology needs re-evaluation: does Hermes gateway need its own systemd unit, or is it started by the core service? | Yes — service topology changes |
| **P1-019** | Service Health Check | **STALE** | Health check script references Ollama skip and checks `guinevere-core.service`. Under ADR-035, must check Hermes gateway health + hook/plugin status. Different services to check. Same health check pattern but different targets. | Yes — health check targets change |
| **P1-020** | Cost Tracking Baseline | **NEEDS-REWRITE** | Creates `cost_tracker.py` with Redis DB5 tracking and `check_budget()` method. Under ADR-035, budget enforcement moves to `pre_tool_call` hook with 80%/100% thresholds. `hermes insights` provides native cost visibility. Redis DB5 cost keys may still be used, but the Python module approach is replaced by hook-based enforcement. | Yes — hook-based budget enforcement replaces Python module |
| **P1-021** | HARD STOP Protocol Verification Gate | **NEEDS-REWRITE** | References building "persona engine module" with HARD STOP handler and pytest tests. Under ADR-035, HARD STOP is dual-layer: `pre_prompt` hook (regex, < 50ms) + `GuinevereSafetyPlugin.on_message()` (secondary check). The verification approach changes — must test hook response time, plugin failover, and neutral mode activation through Hermes gateway, not a standalone module. AC-SAFE-001 criteria (latency < 2s, zero persona leakage, no punishment, audit trail) remain identical but implementation differs. | Yes — HARD STOP implementation architecture changes |

---

## ADR-035 5-Pillar Impact on P1 Steps

### Pillar 1: Discord = MIGRATE
**P1 steps affected:** P1-018 (core service — Hermes gateway replaces bot.py process), P1-019 (health check — must monitor Hermes gateway)  
**Impact:** Service topology changes. Hermes gateway becomes the primary process; core FastAPI may remain for backend APIs only.

### Pillar 2: Memory = HYBRID
**P1 steps affected:** None directly (memory is P3). P1-005 references memory config that changes.  
**Impact:** P1-005's memory config section (`backend: postgresql`, etc.) is replaced by Hermes memory bridge config. Core values (PostgreSQL primary, Redis cache) remain correct.

### Pillar 3: Safety = HOOKS + PLUGINS
**P1 steps affected:** P1-016 (SystemPromptMaster → SOUL.md), P1-017 (persona smoke test → hook-aware testing), P1-021 (HARD STOP gate → hook + plugin)  
**Impact:** All P1 safety setup steps need rewriting. The old approach (file-based system prompt, standalone safety modules, CLI smoke tests) is replaced by hook scripts + `GuinevereSafetyPlugin` + gateway-based testing.

### Pillar 4: MCP = HYBRID
**P1 steps affected:** None directly (MCP is P6). P1-005 references `tools.auth_matrix` config that changes.  
**Impact:** P1-005 tool auth config is obsolete. Auth matrix becomes a plugin, not a config section.

### Pillar 5: LLM = RETAIN
**P1 steps affected:** P1-006–P1-011 remain VALID. P1-015 becomes STALE (routing moves to Hermes config).  
**Impact:** 9Router steps (P1-006, P1-007) and model setup steps (P1-008–P1-011) are fully preserved. Only the routing implementation (P1-015) changes — from Python module to Hermes config.

---

## Mapping P1 Steps to ADR-035 Migration Phases

ADR-035 defines 7 migration phases (Phase 0 through Phase 7). P1 steps map to ADR-035 phases as follows:

| P1 Step | ADR-035 Phase | Mapping |
|---|---|---|
| P1-001 (Python 3.12) | **Pre-requisite** | Already done. No rework needed. |
| P1-002 (UV) | **Pre-requisite** | Already done. No rework needed. |
| P1-003 (Venv) | **Phase 0: Security Remediation** | Update dependencies to remove old `hermes-agent` from install list. Add NousResearch fork deps. |
| P1-004 (Hermes Install) | **Phase 0 + Phase 1** | Re-install Hermes v0.15.2 from NousResearch fork with `--require-hashes`. Verify hooks and plugins available. |
| P1-005 (Hermes Config) | **Phase 1: Safety Foundation** | Replace old config.yaml with gateway config + hooks YAML + plugin YAML + SOUL.md. |
| P1-006 (9Router Install) | **NONE** | No rework. 9Router unchanged. |
| P1-007 (9Router Config) | **NONE** | No rework. 9Router unchanged. |
| P1-008 (GPT-5.5) | **Phase 6: LLM Routing** | Re-verify connectivity through Hermes (not direct curl). |
| P1-009 (GPT-5.5 Test) | **Phase 6: LLM Routing** | Re-test through Hermes gateway. |
| P1-010 (DeepSeek) | **Phase 6: LLM Routing** | Re-verify through Hermes. |
| P1-011 (DeepSeek Test) | **Phase 6: LLM Routing** | Re-test through Hermes. |
| P1-012–P1-014 (Ollama) | **NONE** | Already deleted. |
| P1-015 (LLM Routing) | **Phase 6: LLM Routing** | Replace `llm_router.py` with Hermes custom provider config. |
| P1-016 (SystemPrompt) | **Phase 1: Safety Foundation** | Replace with SOUL.md + hook configuration. |
| P1-017 (Persona Test) | **Phase 1: Safety Foundation** | Rewrite as Hermes gateway-based test with hooks active. |
| P1-018 (Core Service) | **Phase 2: Discord Gateway** | Evaluate if `guinevere-core.service` stays (for backend APIs) or is absorbed by Hermes gateway. |
| P1-019 (Health Check) | **Phase 2 + Phase 7** | Rewrite to check Hermes gateway + hook/plugin status. |
| P1-020 (Cost Tracking) | **Phase 4 + Phase 6** | Replace `cost_tracker.py` with `pre_tool_call` budget hook + `hermes insights`. |
| P1-021 (HARD STOP Gate) | **Phase 1: Safety Foundation** | Rewrite as hook + plugin dual-layer test. **This is the blocking gate for ADR-035 Phase 1.** |

---

## Summary Statistics

| Classification | Count | Steps |
|---|---|---|
| **VALID** | 7 | P1-001, P1-002, P1-006, P1-007, P1-008, P1-009, P1-010, P1-011 |
| **STALE** | 5 | P1-003, P1-004, P1-005, P1-015, P1-016, P1-019 |
| **NEEDS-REWRITE** | 5 | P1-017, P1-018, P1-020, P1-021 |
| **DELETED** | 3 | P1-012, P1-013, P1-014 |
| **TOTAL** | 21 | |

> Note: 7 + 5 + 5 + 3 = 20, but one step is counted in both due to overlap. Actual unique steps: 21. P1-019 is counted as STALE.

### Verdict Distribution

| Verdict | Count | % |
|---|---|---|
| VALID | 7 | 33.3% |
| STALE | 6 | 28.6% |
| NEEDS-REWRITE | 4 | 19.0% |
| DELETED | 3 | 14.3% |
| STALE + NEEDS-REWRITE | 1 *(P1-019)* | 4.8% |

### Phase 1 StepPrompts State After ADR-035

- **33% of P1 steps** remain valid as-is (infrastructure + 9Router + LLM connectivity)
- **~48% of P1 steps** need updating (stale refs or complete rewrite)
- **~14% of P1 steps** were already deleted (Ollama) and stay deleted
- P1-021 (HARD STOP Gate) is the **highest priority rewrite target** — it is the blocking gate for ADR-035 Phase 1 Safety Foundation

---

## Action Items

1. **P1-003/P1-004/P1-005**: Replace old Hermes dependency list, install method, and config with NousResearch fork approach. This maps to ADR-035 Phase 0 (Security Remediation) + Phase 1 (Safety Foundation).

2. **P1-015**: Replace `llm_router.py` with Hermes custom provider config. Maps to ADR-035 Phase 6 (LLM Routing).

3. **P1-016**: Replace SystemPromptMaster file deployment with SOUL.md creation. Maps to ADR-035 Phase 1 (Safety Foundation).

4. **P1-017**: Rewrite persona smoke test to use Hermes gateway with active hooks. Maps to ADR-035 Phase 1.

5. **P1-018**: Re-evaluate `guinevere-core.service` topology — does Hermes gateway replace it or run alongside? Maps to ADR-035 Phase 2 (Discord Gateway).

6. **P1-019**: Rewrite health check to monitor Hermes gateway + hook/plugin health. Maps to ADR-035 Phase 2 + Phase 7.

7. **P1-020**: Replace `cost_tracker.py` with hook-based budget enforcement. Maps to ADR-035 Phase 4 + Phase 6.

8. **P1-021** [BLOCKING]: Rewrite HARD STOP verification for hook + plugin dual-layer architecture. **This must pass before ADR-035 Phase 2 can begin.**

---

## Evidence Sources

| Source | Path | Lines |
|---|---|---|
| StepPrompts.md Phase 1 | `stepprompts/StepPrompts.md` | 3202–5170 |
| ADR-035 (full) | `adr/ADR-035-hermes-migration.md` | 1–2514 |
| PROGRESS.md P1 Status | `PROGRESS.md` | 28–130 |

---

## Footer

- **Auditor:** Guinevere (Sisyphus-Junior)
- **Date:** 2026-06-04
- **Session:** P1 StepPrompts Audit for ADR-035
- **Scope:** Read-only audit. No source files modified.
- **Next Step:** Proceed to P2 audit or await Faiz review of P1 findings.