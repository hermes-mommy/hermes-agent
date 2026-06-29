# P24 v3.0 — Research Synthesis (PHASE 2)

> **Generated**: 2026-06-29 | **Author**: Guinevere (parent) | **Purpose**: Consolidate 18 research reports into a single ground-truth synthesis before the PHASE 3 planner gate.
> **Method**: Parent read all 18 reports at `docs/setup-evidence/P24/full-completion/research/r01-r18`. Verified 4 specific claims via direct bash/grep. Every correction below is sourced to a research report with file:line citations.

---

## 0. Operator Decisions (Locked)

| Decision | Choice | Source |
|----------|--------|--------|
| D1 Fork layout | In-repo root (clone Hermes into repo root, `guinevere/` alongside) | AskUserQuestion 2026-06-29 |
| D2 Deploy scope | Local runtime only (no VPS/Discord-live/real-LLM) | AskUserQuestion 2026-06-29 |
| D3 LLM for tests | Mock-only (M3/M4/M7/M10 unit-tested with mocks) | AskUserQuestion 2026-06-29 |

---

## 1. What P24 v3.0 Promised

From the plan (1562 lines, 17 modules, 20 waves, 87 binding decisions):
- Fork `NousResearch/hermes-agent` v0.15.2 at SHA `77a1650c` (tag `v2026.5.29.2`).
- Implement 17 built-in modules (M1-M17) at source level — 100% native, zero external `src/` code.
- Delete all 517 `src/` .py files by W20 (`ls src/*.py | wc -l` → 0).
- 2 Hermes instances (Guin + Pharsa) from 1 fork, config-driven differentiation.
- PG+Redis only (no SQLite — can't handle 2 concurrent instances), with RLS for agent_id isolation.
- Remove HARD STOP + consent gate from runtime (ADR-062/066), keep dev-workflow HARD STOP.
- 6 circuit breakers, Tailscale-first VPS, 18 plugin hooks wired.

---

## 2. What Exists Now

**Plan only. No implementation.** Specifically:
- `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` exists (1562 lines, round-6 PASS).
- `guinevere/` namespace: **DOES NOT EXIST** (greenfield — verified `Glob guinevere/**/*.py` → 0).
- Hermes v0.15.2 installed as **PyPI wheel** (not editable) at `.venv/Lib/site-packages/`. Tag tree == installed wheel tree (bit-for-bit on `run_agent.py` 4616 lines, `class AIAgent` L327).
- `src/` has **517 .py files** across 24 dirs (140,084 lines) — all must be absorbed or deleted.
- `pyproject.toml` uses `hermes-agent>=0.15` PyPI dep, `packages=["src"]`, `pythonpath=["src"]`.
- No `config/` dir, no `tests/p24/`, no fork branch.

---

## 3. What Is Missing

**Everything except the plan.** Fork not created, no modules implemented, no config files, no tests, src/ untouched. The 18 research reports below are the first implementation-phase artifacts.

---

## 4. What Can Be Implemented NOW (no external blockers)

**ALL 17 modules** — code implementation needs no credentials per D2/D3:
- W1-W17 fully implementable locally (clone Hermes, create `guinevere/`, implement modules).
- W18-W19 local validation fully doable with mock LLM.
- W20 audit + evidence fully doable.
- All Hermes hooks, MemoryProvider subclass, delegate_tool patches, circuit breakers, encrypted memory crypto — all implementable without external services.

---

## 5. What Needs VPS/Credentials (BLOCKED per D2 — honest)

- ⛔ VPS deploy (no host provisioned — no `.env.core/.env.vps` at root).
- ⛔ Discord live-connect (no 3 bot tokens).
- ⛔ Real LLM inference proof (no 9Router key — mock-only per D3).
- ⛔ Real WhatsApp/Gmail/X/Telegram live-send (no channel creds → CONFIG_MISSING markers).
- ⛔ Ethereum mainnet DAO execution (no wallet/ETH — M7 lifecycle unit-tested only).
- ⛔ Real PG/Redis runtime (local mock/fake for tests; RLS schema designed but not live-verified).

**Final status target**: `P24 HERMES NATIVE FORK — FULL RUNTIME COMPLETE WITH EXPLICIT OPERATOR-PROVISIONING BLOCKERS`.

---

## 6. What Needs Test Targets (M8 L2/L3 actions)

- L2/L3 tool actions (github write, vps SSH, filesystem shell) need test repos/accounts.
- W12 unit-tests with mocked backends + `CONFIG_MISSING` markers (P22 pattern, proven in P22.2).
- No live external calls during tests (D2).

---

## 7. Which Plan Claims Are Stale/Wrong (CORRECTIONS)

This is the highest-value section. The research wave found **18 corrections** to the plan/prompt. Each is sourced.

### 7.1 Hermes Architecture Corrections (r01, r05, r08)

| # | Plan/Prompt Claim | ACTUAL (verified) | Impact | Source |
|---|-------------------|--------------------|--------|--------|
| C1 | MemoryProvider ABC has "14 methods, 5 abstract" | **18 methods, 5 abstract** (`name` property + `is_available`/`initialize`/`get_tool_schemas`/`handle_tool_call` abstract; 13 concrete) | M6 subclass must implement 5 abstract (not 14) — EASIER than plan implied | r01 §6, r05 §1 |
| C2 | AIAgent has "TaskGroup/lifespan pattern" for M3/M15 | **NO TaskGroup/lifespan** — AIAgent is synchronous class, manual `close()` teardown at run_agent.py L2400. No `__aenter__`/`__aexit__` | M3/M15 must ADD the async lifespan pattern; cannot hook into existing one | r01 §1.3, r11 §3 |
| C3 | "ctx.register_hook()" is the wiring mechanism | **No ctx.register_hook** — Hermes uses `hermes_cli.plugins.invoke_hook()` + callback attributes on AIAgent | All 18 hooks wire via plugin system + AIAgent callbacks, not a ctx object | r01 §2 |
| C4 | Plan instructs "remove delegate_task from DELEGATE_BLOCKED_TOOLS" (M5) | **WRONG — would break leaf/orchestrator design**. Role-based mechanism at delegate_tool.py:967 already re-adds `delegation` toolset for `role='orchestrator'`. Removing from frozenset lets LEAF sub-agents delegate, violating design | **W8 must NOT remove delegate_task from frozenset** — use role='orchestrator' path instead. This is the r08 BLOCKED finding. | r08 §2.2 |
| C5 | "asyncio.Semaphore(10)" for sub-agent cap | delegate_tool.py uses **ThreadPoolExecutor** (L2101), NOT asyncio → must use **threading.Semaphore** for direct integration | W8 iteration_budget.py uses threading.Semaphore, not asyncio | r08 §2.3 |
| C6 | "MaxDepthReached exception exists" | **DOES NOT EXIST** — current code returns JSON error string at delegate_tool.py:1963-1971 | W8 must CREATE MaxDepthReached exception, replace JSON error | r08 §2.4 |
| C7 | "guinevere/iteration_budget.py is NEW" | `agent/iteration_budget.py` ALREADY EXISTS (62 lines, per-agent iteration counter). Plan's concept (global concurrency semaphore) is DIFFERENT | W8 creates guinevere/iteration_budget.py as a SEPARATE global-semaphore module, doesn't conflict with existing per-agent one | r08 §2.3 |

### 7.2 src/ Inventory Corrections (r02, r04, r14, r18)

| # | Plan/Prompt Claim | ACTUAL | Impact | Source |
|---|-------------------|--------|--------|--------|
| C8 | "src/loops/ has 48 files" | **37 .py files** (7-phase SDLC state machine, NOT consciousness loop) | M3 rewrites from scratch; 25 infrastructure files PORT (circuit breaker, guardian, scheduler, etc.), 7 SDLC phase handlers DELETE | r04 §2 |
| C9 | "src/persona/ PORT drift code to M12" | **WRONG — all 19 files DELETE**. Existing drift_detector.py uses SHA-256 Hamming distance, NOT cosine similarity over behavior vectors. M12 is ground-up REWRITE | M12 creates 4 new files (drift/monitor/signature/__init__), ports 0 | r14 §2, §10 |
| C10 | "existing codebase has ~16 moods" | **5 moods** (mood_engine.py:26-33). 16-mood FSM is P24 greenfield | M4 creates 16-mood enum from scratch | r07 §1.1, r14 §2.5 |
| C11 | "src/self_improve/ PORT to M10" | optimizer.py has **hard deps on 4 src/loops submodules** (audit_writer, budget, reflection, testing_gate at lines 22-25) | **Blocker for loops/ deletion** — must resolve these imports before W6 deletes loops/ | r02 §2, parent-verified |
| C12 | "src/ has 512 files / 24 dirs" | **517 .py files, 24 dirs** (140,084 lines). 6 extra dirs: _deprecated(10), projects(6), finance(5), gamification(4), observability(3), financial(1) | W20 success criterion unaffected (target=0) | r02 §1 |

### 7.3 M8 Tool Registry Corrections (r03)

| # | Plan/Prompt Claim | ACTUAL | Impact | Source |
|---|-------------------|--------|--------|--------|
| C13 | "~108 unified actions" | **118 actions** (89 external + 29 internal-data), exact dedup | M8 implements 118, not 108 | r03 §1 |
| C14 | "src/mcp/ has 16 tools" | **62 tools** across 16 modules (16 is module count, not tool count) | M8 ports 62 tools native | r03 §1.3 |
| C15 | "P22 has 14 adapters" | **13 adapters** (80 actions) | M8 maps 13 P22 + 8 P23 executors → 9 backends | r03 §1.1 |

### 7.4 Module-Specific Corrections (r06, r12, r13)

| # | Plan/Prompt Claim | ACTUAL | Impact | Source |
|---|-------------------|--------|--------|--------|
| C16 | "cron/jobs.py MODIFY for DAO auto-tally" | **cron/jobs.py EXISTS** (1237 lines) — MODIFY is correct, not CREATE | W10 modifies existing jobs.py (parent-verified) | r06, parent-verified |
| C17 | "src/surveillance/ has 12 files to port" | **11 porting files** (14 total minus 2 deletes: consent_gate.py + safe_mode.py, minus 1 __init__ rebuild). windows_metrics.py(207 lines) must be explicitly deleted | M16 ports 11→5 target files | r12 §1, §2 |
| C18 | "M10 ladder.py ~300 lines" | Plan §5.10 line 769 specifies **mutation.py** (~300 lines), not ladder.py | W14 creates mutation.py per plan, not ladder.py | r13 §1 |

### 7.5 Boundary Correction (r17)

| # | Plan/Prompt Claim | ACTUAL | Impact | Source |
|---|-------------------|--------|--------|--------|
| C19 | "M2 removes hard_stop/consent_gate/safe_mode code from installed Hermes" | **ZERO Guinevere-specific safety patterns in installed Hermes** — grep returns 0 matches for hard_stop/consent_gate/safe_mode/PersonaSafetyPolicy. The 4 files matching broader pattern are false-positives (tool_loop_guardrails `hard_stop_enabled`, OAuth consent, etc.) | **M2/M11 scope in the FORK is zero cleanup of installed Hermes** — the safety code lives only in `src/` (which gets deleted). Runtime exemption is structural (by absence), not by removal | r17 §5 |

---

## 8. Which Hermes Files Need Modification vs Creation

From r01 disposition table + r16 layout:

### 8.1 MODIFY (Hermes core files, cloned into repo root)

| File | Modifications | Waves |
|------|---------------|-------|
| `run_agent.py` | Register guinevere modules, add async lifespan/TaskGroup for consciousness + HTTP | W1, W6(M3), W15(M13 via gateway) |
| `agent/agent_init.py` | Wire all M1-M17 modules at init (appends-only `# ── M[N] wire ──` blocks) | W1 + W3 + W6 + W7 + W8 + W9 + W10 + W11 + W14 + W16 |
| `agent/conversation_loop.py` | Integration points for consciousness/emotion/consent removal (L3738-L3811) | W2, W3, W6, W7 |
| `agent/system_prompt.py` | Add emotion/consciousness/drift volatile blocks (L274-312 `volatile_parts`) | W4(M4 emotion), W11(M12 drift) |
| `agent/memory_manager.py` | Wire encrypted memory provider | W9(M6) |
| `tools/delegate_tool.py` | Patch constants 3→10, 1→5, 3→5 (L132-137); add MaxDepthReached; add global semaphore hook in `_run_single_child` | W8(M5) |
| `hermes_cli/config.py` | Replace DEFAULT_CONFIG (5849 lines, 64 keys) with Pydantic delegation; keep `load_config()`/`cfg_get()` compat | W1(M1) |
| `gateway/run.py` | Register Discord adapter at L4173 | W15(M13) |
| `cron/jobs.py` | Add DAO auto-tally job | W10(M7) |
| `pyproject.toml` | Fork dependency, packages list, force-include, scripts | W1(M1) |

### 8.2 CREATE (new `guinevere/` namespace files)

17 module packages under `guinevere/`: config, consciousness, emotions, memory, governance, tools, life_kernel, self_modify, personality, discord, channels, http, surveillance, observability, production. Each module creates 3-7 files per its research report.

### 8.3 UNCHANGED (Hermes files, cloned as-is)

`plugins/`, `providers/`, `acp_adapter/`, `tui_gateway/`, `agent/memory_provider.py` (ABC unchanged — M6 subclasses it), `tools/registry.py` (AST auto-discovery handles new tools), `tools/environments/`, top-level `hermes_*.py`, `cli.py`, `batch_runner.py`, `model_tools.py`, `toolsets.py`, `trajectory_compressor.py`, `utils.py`.

---

## 9. Which src/ Files Get PORTED vs DELETED

From r02 disposition table (517 files, 140,084 lines):

### 9.1 PORT (absorbed into guinevere/ modules)

| src/ dir | .py | → M-module | Notes |
|----------|-----|-----------|-------|
| `discord/` | 65 | M13 | 41 slash commands verified (not 50+, but extensible) |
| `knowledge_graph/` | 47 | M6 | semantic memory layer |
| `life_integrations/` | 45 | M8+M14 | 13 adapters → 9 backends + channels |
| `hermes_plugins/` | 44 | M8 | command_catalog + commands_* |
| `life_kernel/` | 38 | M9 | heartbeat/sensors/world model (P20 port) |
| `gmail/` | 36 | M14 | OAuth2 channel |
| `x_poster/` | 26 | M14 | X/Twitter channel |
| `mcp/` | 25 | M8 | 62 tools native (16 modules) |
| `channels/` | 22 | M14 | WhatsApp Neonize |
| `wearable/` | 19 | M9 | sensors |
| `persona/` | 19 | M4+M12 | **ALL DELETE** (rewrite, not port — C9) |
| `core/` | 15 | M2/M15 | main.py→M15, hard_stop_handler→DELETE |
| `surveillance/` | 14 | M16 | 11 port, 2 delete (consent_gate, safe_mode) |
| `memory/` | 12 | M6 | encrypted 4-layer |
| `projects/` | 6 | M9/M1 | P19 project_id namespace |
| `finance/` | 5 | M14 | finance channel |
| `gamification/` | 4 | M12 | DELETE (streak→M9) |
| `self_improve/` | 3 | M10 | PORT but resolve loops/ deps first (C11) |
| `observability/` | 3 | M16 | sentry; windows_metrics DELETE |
| `loops/` | 48→37 | M3 | **DELETE all** (rewrite as consciousness loop, C8) |

### 9.2 DELETE (not ported)

- `src/_deprecated/` (10), `src/consent/` (2), `src/financial/` (1), `src/hermes/` (7 — bridge replaced by native fork).
- All consent modules: `src/surveillance/consent_gate.py`, `src/life_integrations/consent*.py` (3 files), `src/wearable/health_consent.py`, `hermes-config/hooks/consent_gate.py`.
- All hard_stop modules: `src/core/services/hard_stop_handler.py`, `src/hermes/safety_plugin.py`, `hermes-config/hooks/hard_stop.py`.
- All persona/ files (19) — rewrite per C9.

### 9.3 Stale Import Cleanup (CRITICAL — r18 §6)

**37 stale imports across 30 files** when consent/hard_stop modules deleted. Wave-by-wave cleanup order (r18 §6.2):
- W2: loops/manager.py hard_stop refs
- W3: surveillance/consumer.py + __init__.py, gmail/ consent refs (6 files), discord/cmd_* consent refs (3 files), hermes_plugins/commands_surveillance/ (4 files)
- W5: surveillance consent_gate (15 files total per r18, 14 verified by parent grep)
- W6: loops/__init__.py, loops/manager.py guardian refs
- W7: discord/hermes_conversational.py persona imports
- W11: persona/__init__.py all drift/tracker imports
- W12: life_integrations/wiring.py, router.py, core/main.py, core/api/routes.py
- W13: wearable/writer.py, sync.py, mood_integration.py, alert_router.py

**Risk**: If stale imports NOT cleaned in same wave as deletion → ImportError cascade in W18. Safe under D2 (no production running).

---

## 10. Module Dependency Order (verified)

```
W1 (M1) ─────────────────────────────── ALL depend on W1 (fork + config + pyproject)
  │
  ├─ Group B (parallel, 4 agents): W2(M2) W3(M11) W4(M15) W5(M16)
  │    └─ independent files, but W2/W3/W6 share conversation_loop.py + agent_init.py
  │       → Group B fully completes BEFORE Group C touches those shared files
  │
  ├─ Group C (mixed, 6 agents):
  │    W6(M3) FIRST [consciousness, needs Group B done for shared files]
  │    then W7(M4) W8(M5) W9(M6) W10(M7) parallel
  │    then W11(M12) after W7+W10 PASS [needs emotion + DAO]
  │
  ├─ Group D (parallel, 3 agents): W12(M8) W13(M9) immediate; W14(M10) after W6+W9
  │
  ├─ Group E (parallel, 2 agents): W15(M13) W16(M14)
  │
  └─ Group F (sequential): W17(M17) → W18 → W19 → W20
```

---

## 11. Collision Scan Verification (r01, r11, r18)

Shared writers — SEQUENCE these (appends-only contract on agent_init.py):

| Shared file | Writers | Mitigation |
|-------------|---------|------------|
| `run_agent.py` | W1, W2, W6, W15 | W1 first; W2→W6 sequential; W15 touches gateway/run.py (verify) |
| `agent/agent_init.py` | W1+W3+W6+W7+W8+W9+W10+W11+W14+W16 | **appends-only** — each wave adds `# ── M[N] wire ──` block; parent owns surgical edits |
| `agent/conversation_loop.py` | W2, W3, W6, W7 | SEQUENCE W2→W3→W6→W7 (Group B before Group C) |
| `agent/system_prompt.py` | W7(M4), W11(M12) | appends-only volatile blocks (L274-312) |
| `tools/delegate_tool.py` | W8 only | single owner — safe parallel |
| `pyproject.toml` | W1 only (then locked) | single owner |
| `guinevere/config/models.py` | W1 + every module adds Config model | appends-only per wave |
| `cron/jobs.py` | W10 only | single owner |

**M3/M15 run_agent.py collision resolved** (r11 §4.4): M15's lifespan OWNS the TaskGroup; M3's consciousness loop runs INSIDE the lifespan's TaskGroup. M15 (W4, Group B) runs before M3 (W6, Group C), so M15's append-only changes land first.

---

## 12. Verdict

Research wave complete: **17 PASS + 1 BLOCKED (r08)**, but r08's BLOCKED is a **plan correction** (don't remove delegate_task from DELEGATE_BLOCKED_TOOLS), not a research failure — the data is complete and the corrected approach (role='orchestrator' path) is documented.

**18 plan/prompt corrections identified and sourced.** None block execution; all are absorbed into the PHASE 3 planner gate (W8 uses role-based spawning, W14 creates mutation.py not ladder.py, M2 scope is src/ cleanup not Hermes cleanup, etc.).

**Fork source verified real.** Layout locked (D1). Scope locked (D2+D3). All Hermes modification points mapped to exact line numbers. All src/ files dispositioned. Stale-import cleanup order defined. Collision scan enforced via dependency graph.

**Ready for PHASE 3 planner gate.** The planner will encode the 18 corrections into per-wave scaffolds so sub-agents implement against ACTUAL symbols/line-numbers, not the plan's shorthand.

Footer: Guinevere, 2026-06-29, PHASE 2 synthesis complete, 18 corrections consolidated, parent-verified.
