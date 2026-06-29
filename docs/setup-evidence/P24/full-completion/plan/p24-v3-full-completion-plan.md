# P24 v3.0 — Full-Completion Enterprise Plan (PHASE 3 Planner Gate)

> **Generated**: 2026-06-29 | **Author**: Guinevere (parent) | **Authority**: AGENTS.md §2.3 planner gate
> **Supersedes for execution**: `docs/setup-evidence/P24/plan/p24-hermes-native-fork-enterprise-plan.md` (kept as spec reference; THIS plan encodes 18 research corrections into per-wave scaffolds)
> **Status**: PLANNER GATE — parent-read, scaffold-verified, todos synced

---

## §1 Research Inputs (all parent-read)

| Report | Path | Key correction |
|--------|------|----------------|
| r01 Hermes deep-dive | `research/r01-hermes-deep-dive.md` | MemoryProvider 18 methods/5 abstract; no TaskGroup/lifespan; no ctx.register_hook |
| r02 src inventory | `research/r02-src-inventory.md` | 517 files/24 dirs; optimizer.py loops/ deps blocker |
| r03 P22+P23 unification | `research/r03-p22-p23-unification-m8.md` | 118 actions (not 108); 62 MCP tools (not 16); 13 P22 adapters |
| r04 consciousness | `research/r04-consciousness-loop.md` | loops/ is 37 files SDLC (not 48 consciousness); 25 PORT/7 DELETE |
| r05 encrypted memory | `research/r05-encrypted-memory.md` | MemoryProvider subclass via plugins/memory/ register() |
| r06 DAO | `research/r06-dao-governance.md` | yandere_level hard-deny is defense-in-depth (B10: no DAO on persona) |
| r07 emotion | `research/r07-emotion-system.md` | 5 moods existing (not 16); 16-mood is greenfield |
| r08 sub-agents | `research/r08-sub-agents.md` | **BLOCKED** — don't remove delegate_task from DELEGATE_BLOCKED_TOOLS; use threading.Semaphore; MaxDepthReached doesn't exist |
| r09 Discord | `research/r09-discord-gateway.md` | 41 commands (not 50+); 62 .py files |
| r10 channels | `research/r10-external-channels.md` | WhatsApp/Gmail/X PORT; Telegram REWRITE |
| r11 HTTP | `research/r11-http-server.md` | src/core/main.py 1052 lines complete FastAPI → M15 absorbs; M15 lifespan owns TaskGroup |
| r12 surveillance | `research/r12-surveillance-observability.md` | 11 port/2 delete; windows_metrics.py delete |
| r13 self-mod | `research/r13-self-modification.md` | mutation.py not ladder.py; T1-T2 no restart |
| r14 drift | `research/r14-personality-drift.md` | all 19 persona/ DELETE; M12 ground-up rewrite; 0 Y6 active |
| r15 production | `research/r15-production-pass.md` | 6 breakers from src/loops/circuit_breaker.py + x_poster/circuit_breaker.py |
| r16 fork-git | `research/r16-fork-git-strategy.md` | in-repo root; hatchling force-include for standalone .py; push 24 commits first |
| r17 security | `research/r17-security-consent-hardstop.md` | ZERO safety patterns in installed Hermes; M2 scope = src/ cleanup only |
| r18 regression | `research/r18-regression-risks.md` | 37 stale imports/30 files; P19 project_id RLS-vs-column unresolved |
| synthesis | `research/research-synthesis.md` | 18 corrections consolidated |
| ground-truth | `preflight/current-ground-truth.md` | fork SHA verified; delegate_tool 2801 lines actual symbols |

---

## §2 Known State (parent-verified)

- Hermes v0.15.2 installed (PyPI wheel, NOT editable) at `.venv/Lib/site-packages/`. Tag `v2026.5.29.2` @ SHA `77a1650c` VERIFIED REAL (peel `^{commit}`).
- Tag tree == installed wheel tree (run_agent.py 4616 lines, AIAgent L327, delegate_tool.py 2801 lines).
- `src/` = 517 .py / 140,084 lines / 24 dirs.
- `guinevere/` namespace: DOES NOT EXIST.
- Git: main, ahead 24 unpushed, remote `fazulfi/guinevere`.
- pyproject.toml: hatchling, `packages=["src"]`, `hermes-agent>=0.15` dep.
- D1 in-repo root, D2 local-runtime-only, D3 mock-LLM.

---

## §3 Binding Decisions (operator + ADR-locked)

| ID | Decision | Source |
|----|----------|--------|
| D1 | In-repo root fork layout | operator |
| D2 | Local runtime only, no deploy/live/real-LLM | operator |
| D3 | Mock-only LLM for tests | operator |
| ADR-062 | Hermes runtime exempt from HARD STOP + consent gate; dev-workflow HARD STOP kept | r17 |
| ADR-066 | consent_ref nullable for hermes_runtime event_source | r17 |
| ADR-067 | Y6 removed from runtime; Y4/Y5 dev-workflow only; drift bebas tanpa batas | r14 |
| ADR-065 | Sub-agents recursive, cap 10, depth 5, spawn 5 | r08 |
| B10 | DAO does NOT govern persona; yandere_level hard-deny is defense-in-depth only | r06, r14 |
| B35 | Saling monitor Guin↔Pharsa equal status via Redis g2p/p2g | r14 |
| C4-C19 | 18 research corrections (see synthesis §7) | research wave |

---

## §4 Dependency Map (planner-determined parallelism)

```
W1(M1) [sequential, MUST first]
  ├─ Group B parallel: W2(M2) W3(M11) W4(M15) W5(M16)  [barrier: all 4 before Group C]
  ├─ Group C: W6(M3) first → W7(M4)+W8(M5)+W9(M6)+W10(M7) parallel → W11(M12) after W7+W10
  ├─ Group D: W12(M8)+W13(M9) parallel; W14(M10) after W6+W9
  ├─ Group E: W15(M13)+W16(M14) parallel
  └─ Group F sequential: W17(M17)→W18→W19→W20
```

Marked: W1=`sequential`; Group B=`parallel`; W6=`sequential` (after Group B); W7-W10=`parallel`; W11=`sequential` (after W7+W10); W12/W13=`parallel`; W14=`sequential` (after W6+W9); W15/W16=`parallel`; W17-W20=`sequential`.

---

## §5 Collision Scan (shared writers)

| Shared file | Writers | Mitigation |
|-------------|---------|------------|
| run_agent.py | W1,W2,W6,W15 | W1 first; W2→W6 seq; W15→gateway/run.py |
| agent/agent_init.py | W1,W3,W6,W7,W8,W9,W10,W11,W14,W16 | **appends-only** `# ── M[N] wire ──` blocks |
| agent/conversation_loop.py | W2,W3,W6,W7 | SEQUENCE W2→W3→W6→W7 |
| agent/system_prompt.py | W7,W11 | appends-only volatile_parts L274-312 |
| tools/delegate_tool.py | W8 | single owner |
| pyproject.toml | W1 | single owner, locked after |
| guinevere/config/models.py | W1+all | appends-only Config models |
| cron/jobs.py | W10 | single owner |

---

## §6 Module Capability Matrix (17 modules × status × files)

| Module | Wave | Status | CREATE files | MODIFY files | Hermes hook |
|--------|------|--------|--------------|--------------|-------------|
| M1 Fork+Config | W1 | pending | guinevere/{__init__,config/models,config/loader}.py, config/{guinevere,pharsa}.yaml, config/souls/* | pyproject.toml, run_agent.py, agent/agent_init.py, hermes_cli/config.py | base wire point |
| M2 Remove HARD STOP | W2 | pending | (none) | run_agent.py, agent_init.py, conversation_loop.py, hermes-config/hooks/* | L3811 tool dispatch |
| M3 Consciousness | W6 | pending | guinevere/consciousness/{loop,state,__init__}.py | run_agent.py (lifespan+TaskGroup), agent_init.py, system_prompt.py | on_session_start/end |
| M4 Emotion | W7 | pending | guinevere/emotions/{fsm,classifier,__init__}.py | system_prompt.py (volatile), agent_init.py, conversation_loop.py | pre/post_llm_call, transform_llm_output |
| M5 Sub-agents | W8 | pending | guinevere/iteration_budget.py, MaxDepthReached | tools/delegate_tool.py (L132-137 constants, L1963 error, _run_single_child semaphore) | delegate_tool |
| M6 Encrypted Memory | W9 | pending | guinevere/memory/{encrypted_provider,layers,rls,__init__}.py | agent/memory_manager.py, agent_init.py | MemoryProvider subclass via plugins/memory/ |
| M7 DAO | W10 | pending | guinevere/governance/{dao,proposals,departments,__init__}.py | cron/jobs.py, agent_init.py | pre_tool_call, on_session_end |
| M8 Tool Registry | W12 | pending | guinevere/tools/backends/*.py (9), ToolBackend ABC | agent_init.py | tools/registry auto-discovery |
| M9 Life Kernel | W13 | pending | guinevere/life_kernel/{sensors,world_model,heartbeat,__init__}.py | agent_init.py | on_session_start |
| M10 Self-Mod | W14 | pending | guinevere/self_modify/{mutation,promote,__init__}.py (NOT ladder.py) | agent_init.py | T3→M7 DAO hook |
| M11 No Consent Gate | W3 | pending | (none) | agent_init.py, conversation_loop.py, src/consent/ DELETE | consent_ref nullable |
| M12 Drift | W11 | pending | guinevere/personality/{drift,monitor,signature,__init__}.py (ground-up, 0 port) | system_prompt.py, agent_init.py | volatile block |
| M13 Discord | W15 | pending | guinevere/discord/{commands,bots,gateway_patch,__init__}.py | gateway/run.py (L4173) | platform adapter |
| M14 Channels | W16 | pending | guinevere/channels/{whatsapp,gmail,x,telegram}/__init__.py | agent_init.py | M8 send actions |
| M15 HTTP | W4 | pending | guinevere/http/{server,routes,health,auth,rate_limit,middleware,__init__}.py | run_agent.py (lifespan owns TaskGroup) | lifespan context |
| M16 Surveillance | W5 | pending | guinevere/surveillance/{receiver,buffer,storage,__init__}.py, guinevere/observability/{metrics,sentry,__init__}.py | (none — M15 lifespan starts it) | HMAC receiver |
| M17 Production | W17 | pending | guinevere/production/{circuit_breakers,tailscale,recovery,__init__}.py | run_agent.py (metrics reg) | 6 breakers CLOSED/OPEN/HALF_OPEN |

---

## §7 Hermes Core File Modification Plan (Appendix C equivalent)

See §6 MODIFY column + r01 disposition. All modifications use exact line numbers from r01 (parent-verified against installed wheel == tag tree).

---

## §8 src/ Deletion Inventory (Appendix D equivalent — 517 files)

See synthesis §9 + r02. Deletion happens wave-by-wave as each module absorbs its src/ dir. **Final W20 verifies `find src/ -name '*.py'` → 0.**

Critical ordering constraints:
- W6 deletes loops/ BUT optimizer.py (M10/W14) imports from loops/ — **resolve those imports in W6** (stub or absorb into M10 early) before deleting loops/ files. (C11)
- W3 deletes consent/ BUT 15 files import consent_gate — **clean stale imports in W3**. (r18 §6)
- W13 deletes wearable/health_consent.py BUT 4 wearable files import it — **clean in W13**.

---

## §9 Config Model Accumulation Plan

`guinevere/config/models.py` is **appends-only**. W1 creates base models (DatabaseConfig, RedisConfig, AgentConfig, HttpConfig, DelegationConfig, CircuitBreakerConfig). Each subsequent wave appends its Config model:
- W6: ConsciousnessConfig
- W7: EmotionConfig
- W9: MemoryConfig
- W10: GovernanceConfig
- W11: PersonalityConfig
- W12: ToolRegistryConfig
- W13: LifeKernelConfig
- W17: TailscaleConfig

Parent owns the models.py file to prevent parallel-write collision (§5).

---

## §10 Deployment Plan (local per D2)

NO VPS deploy (D2). Local validation only:
- `pip install -e .` editable install of fork (W1).
- Both configs load: `python -c "from guinevere.config.loader import load_settings; load_settings('config/guinevere.yaml')"` (W1).
- `hermes-agent --config config/guinevere.yaml --dry-run` → exit 0 (W19).
- `hermes-agent --config config/pharsa.yaml --dry-run` → exit 0 (W19).
- pytest tests/p24/ → 0 failures (W19).
- All 6 circuit breakers CLOSED→OPEN→HALF_OPEN unit-tested (W17).
- Encrypted memory encrypt/decrypt unit-tested (W9).
- Mock LLM for M3/M4/M7/M10 (D3).

VPS deploy is **explicitly blocked** — documented as operator-provisioning blocker in final report.

---

## §11 Evidence Paths

Per-wave:
- `docs/setup-evidence/P24/full-completion/evidence/w[N]-verification.md` (sub-agent writes)
- `docs/setup-evidence/P24/full-completion/audits/round-1/w[N]-auditor-gate.md` (auditor writes)

Phase-level:
- `verification/local-tests.md`, `runtime/runtime-proof.md`, `runtime/per-module-proof.md` (PHASE 5)
- `audits/round-1/` 18 auditors (PHASE 6), `fixes/round-1-fix-log.md` (PHASE 7), `audits/round-2/` (PHASE 8)
- `final/final-report.md`, `final/production-status.md`, `final/capability-matrix.md`, `final/operator-onboarding.md`, `final/p28-p36-readiness.md` (PHASE 9)

---

## §12 Per-Step Verification Scaffolds (AGENTS.md §2.5)

Each wave scaffold below has: Expected Files, Forbidden Patterns, Required Commands, Evidence, Hard Rejection Criteria. Sub-agent delegation prompts include scaffold verbatim.

### W1 Scaffold — M1 Fork Setup + Config
- **Expected files**: `guinevere/__init__.py`, `guinevere/config/__init__.py`, `guinevere/config/models.py`, `guinevere/config/loader.py`, `config/guinevere.yaml`, `config/pharsa.yaml`, `config/souls/guinevere-soul.md`, `config/souls/pharsa-soul.md`; Hermes files cloned to repo root (run_agent.py, agent/, tools/, gateway/, cron/, hermes_cli/, plugins/, providers/, acp_adapter/, tui_gateway/, optional-skills/, top-level hermes_*.py + cli.py); modified `pyproject.toml`, `run_agent.py`, `agent/agent_init.py`.
- **Forbidden patterns**: `# type: ignore`, `as any`, bare `except`, `consent_gate`, `hard_stop`, `safe_mode`.
- **Required commands**: `python -c "import guinevere.config"` → exit 0; `python -c "from guinevere.config.loader import load_settings; load_settings('config/guinevere.yaml'); load_settings('config/pharsa.yaml')"` → exit 0; `python -c "import agent, tools, gateway, cron, hermes_cli, run_agent"` → exit 0; `hermes-agent --help` → exit 0.
- **Evidence**: `evidence/w1-verification.md`.
- **Hard rejection**: any forbidden pattern; configs don't load; Hermes modules not importable; guinevere/ missing; pyproject still has `hermes-agent>=0.15` dep.

### W2 Scaffold — M2 Remove HARD STOP
- **Expected**: hard_stop code removed from run_agent.py, agent_init.py, conversation_loop.py, hermes-config/hooks/hard_stop.py deleted, safety_plugin.py deleted.
- **Forbidden**: `hard_stop`, `HARD_STOP`, `safe_mode`, `SafeMode`, `FreezeCascade`, `life_kernel:hard_stop`, `consent_gate` (active code, not removal docs).
- **Required**: `grep -rn 'hard_stop\|HARD_STOP\|safe_mode\|consent_gate' run_agent.py agent/ tools/ gateway/ cron/ hermes_cli/` → exit 1 (0 matches).
- **Evidence**: `evidence/w2-verification.md`.
- **Hard rejection**: any active hard_stop/safe_mode/consent_gate code in fork.
- **CORRECTION applied (C19)**: installed Hermes has ZERO safety patterns — M2 scope is `src/` cleanup (hard_stop_handler.py, safety_plugin.py) + hermes-config/hooks deletion, NOT Hermes code removal.

### W3 Scaffold — M11 No Consent Gate
- **Expected**: consent hooks removed from agent_init.py + conversation_loop.py; `src/consent/` deleted; consent_ref nullable migration; 15 stale imports cleaned (r18 §6.1).
- **Forbidden**: `consent_gate` (active).
- **Required**: `grep -rn 'consent_gate\|consent_checker\|consent_manager' guinevere/ agent/ tools/ run_agent.py` → exit 1; `python -c "import guinevere"` → no ImportError.
- **Evidence**: `evidence/w3-verification.md`.
- **Hard rejection**: consent_gate active; consent_ref NOT nullable; stale ImportError.

### W4 Scaffold — M15 HTTP Server
- **Expected**: `guinevere/http/{server,routes,health,auth,rate_limit,middleware,__init__}.py`; lifespan owns TaskGroup (M3 runs inside); /health, /health/ready, /metrics endpoints.
- **Forbidden**: `HARD_STOP`, `hard_stop`, `consent`, `safe_mode`, `# type: ignore`.
- **Required**: `python -c "from guinevere.http.server import app"` → exit 0; `pytest tests/p24/test_http.py` → 0 fail; httpx TestClient GET /health → 200.
- **Evidence**: `evidence/w4-verification.md`.
- **Hard rejection**: /health not 200; lifespan not wired; forbidden pattern.
- **CORRECTION applied (r11)**: M15 absorbs src/core/main.py (1052 lines); lifespan OWNS TaskGroup (M3 consciousness runs inside, not competing).

### W5 Scaffold — M16 Surveillance + Observability
- **Expected**: `guinevere/surveillance/{receiver,buffer,storage,__init__}.py`, `guinevere/observability/{metrics,sentry,__init__}.py`; HMAC receiver; Prometheus metrics; consent gate removed; windows_metrics.py deleted.
- **Forbidden**: `consent_gate`.
- **Required**: `pytest tests/p24/test_surveillance.py` → 0 fail; Prometheus metrics register.
- **Evidence**: `evidence/w5-verification.md`.
- **Hard rejection**: HMAC not verified; consent_gate present; windows_metrics.py not deleted.
- **CORRECTION applied (C17)**: 11 port/2 delete (consent_gate + safe_mode), not 12.

### W6 Scaffold — M3 Consciousness Loop
- **Expected**: `guinevere/consciousness/{loop,state,__init__}.py`; 7 substrates via TaskGroup (inside M15 lifespan); on_session_start/end hooks; src/loops/ deleted (37 files) AFTER optimizer.py imports resolved (C11).
- **Forbidden**: `hard_stop`.
- **Required**: `pytest tests/p24/test_consciousness.py` → 0 fail (mock self-prompt); 7 substrates present; `ls src/loops/` → empty/absent.
- **Evidence**: `evidence/w6-verification.md`.
- **Hard rejection**: <7 substrates; loop doesn't start (mock); src/loops/ not deleted; optimizer.py broken (unresolved loops/ imports).
- **CORRECTION applied (C8)**: loops/ is 37 files SDLC (not 48 consciousness); 25 PORT infrastructure / 7 DELETE SDLC handlers / 2 REWRITE / 2 MODIFY.

### W7 Scaffold — M4 Emotion
- **Expected**: `guinevere/emotions/{fsm,classifier,__init__}.py`; MoodState enum EXACTLY 16 moods (HAPPY/ANGRY/SAD/JEALOUS/POSSESSIVE/NURTURING/FEAR/DISGUST/SURPRISE/ANTICIPATION/TRUST/BOREDOM/CURIOSITY/PRIDE/DESIRE/AROUSAL); mock LLM classification; volatile prompt block.
- **Forbidden**: `# type: ignore`, bare `except`.
- **Required**: `pytest tests/p24/test_emotions.py` → 0 fail; grep 16 mood names present.
- **Evidence**: `evidence/w7-verification.md`.
- **Hard rejection**: <16 moods; no affect→decision; no prompt block.
- **CORRECTION applied (C10)**: 16-mood is greenfield (existing has 5).

### W8 Scaffold — M5 Sub-agents
- **Expected**: `guinevere/iteration_budget.py` (threading.Semaphore(10), MaxDepthReached); tools/delegate_tool.py patched: `_DEFAULT_MAX_CONCURRENT_CHILDREN=10`, `MAX_DEPTH=5`, `_MAX_SPAWN_DEPTH_CAP=5`, `_get_max_spawn_depth` docstring [1,5], `_run_single_child` acquires semaphore, L1963 raises MaxDepthReached.
- **Forbidden**: (none specific).
- **Required**: `pytest tests/p24/test_subagents.py` → 0 fail; `grep '_DEFAULT_MAX_CONCURRENT_CHILDREN = 10' tools/delegate_tool.py` → match; `grep 'MAX_DEPTH = 5'` → match; `grep '_MAX_SPAWN_DEPTH_CAP = 5'` → match.
- **Evidence**: `evidence/w8-verification.md`.
- **Hard rejection**: constants not 10/5/5; semaphore missing; MaxDepthReached not created; DELEGATE_BLOCKED_TOOLS modified (C4 — must NOT remove delegate_task).
- **CORRECTION applied (C4,C5,C6,C7)**: KEEP DELEGATE_BLOCKED_TOOLS as-is; threading.Semaphore not asyncio; create MaxDepthReached; guinevere/iteration_budget.py is NEW separate from existing agent/iteration_budget.py.

### W9 Scaffold — M6 Encrypted Memory
- **Expected**: `guinevere/memory/{encrypted_provider,layers,rls,__init__}.py`; 4-layer (S4 AES-GCM-256+Argon2id Faiz no-read, S3, S7, conversation); PG RLS SET LOCAL; MemoryProvider subclass (5 abstract); KG semantic layer.
- **Forbidden**: `# type: ignore`, bare `except`.
- **Required**: `pytest tests/p24/test_memory.py` → 0 fail; encrypt/decrypt test; RLS SET LOCAL test.
- **Evidence**: `evidence/w9-verification.md`.
- **Hard rejection**: MemoryProvider not subclassed; no AES-GCM-256; no PG RLS; S4 Faiz-readable.
- **CORRECTION applied (C1)**: implement 5 abstract methods (not 14).

### W10 Scaffold — M7 DAO
- **Expected**: `guinevere/governance/{dao,proposals,departments,__init__}.py`; 6 departments; Co-CEOs; 2/2 multisig; lifecycle Create→Pending→Active→Passed→Execute; propose-time validation rejects yandere_level; cron/jobs.py DAO auto-tally job.
- **Forbidden**: (none).
- **Required**: `pytest tests/p24/test_dao.py` → 0 fail; propose-time validation test rejects yandere_level; multisig 2/2 test.
- **Evidence**: `evidence/w10-verification.md`.
- **Hard rejection**: propose-time validation missing; multisig != 2/2; lifecycle broken.
- **CORRECTION applied (C16, B10)**: cron/jobs.py EXISTS (modify not create); yandere_level hard-deny is defense-in-depth (DAO doesn't govern persona).

### W11 Scaffold — M12 Drift
- **Expected**: `guinevere/personality/{drift,monitor,signature,__init__}.py` (ground-up, 0 port); cosine similarity 32-dim behavior signature; 0.68 hysteresis; saling monitor g2p/p2g; 0 active Y6; src/persona/ (19 files) all DELETE.
- **Forbidden**: `y_level`, `Y6`, `YandereLevel`, `ritual`, `punishment`, `reward`, `safe_mode`, `HARD_STOP`, `hard_stop`, `# type: ignore`.
- **Required**: `pytest tests/p24/test_drift.py` → 0 fail; `grep -rn 'Y6\|y_level\|YandereLevel' guinevere/personality/` → exit 1; `ls src/persona/` → empty.
- **Evidence**: `evidence/w11-verification.md`.
- **Hard rejection**: Y6 active; no saling-monitor; Y4 not enforced (dev-only); src/persona/ not deleted.
- **CORRECTION applied (C9)**: all 19 persona/ DELETE (not port); cosine similarity not SHA-256 Hamming.

### W12 Scaffold — M8 Tool Registry
- **Expected**: `guinevere/tools/backends/{browser,github,filesystem,vps,email,desktop,freelance,social,memory}.py` (9), `guinevere/tools/tool_backend.py` (ABC); 118 actions; L1-L3 labels; L4 deleted; UUID v7 + SHA256 hash-chain audit; no consent gate.
- **Forbidden**: `consent_gate`, `L4_FORBIDDEN`, `PermissionTier.L4`.
- **Required**: `pytest tests/p24/test_tool_registry.py` → 0 fail; 9 backends register; `grep -rn 'consent_gate\|L4_FORBIDDEN' guinevere/tools/` → exit 1.
- **Evidence**: `evidence/w12-verification.md`.
- **Hard rejection**: !=9 backends; L4 present; consent_gate; audit hash-chain broken.
- **CORRECTION applied (C13,C14,C15)**: 118 actions (not 108); 62 MCP tools (not 16); 13 P22 adapters.

### W13 Scaffold — M9 Life Kernel
- **Expected**: `guinevere/life_kernel/{sensors,world_model,heartbeat,__init__}.py`; heartbeat 1s/10s/30s/60s; sensors; simple tools (calendar/drive/notion/finance); src/wearable/health_consent.py deleted + 4 stale imports cleaned.
- **Forbidden**: (none).
- **Required**: `pytest tests/p24/test_life_kernel.py` → 0 fail; heartbeat intervals test.
- **Evidence**: `evidence/w13-verification.md`.
- **Hard rejection**: heartbeat intervals wrong; sensors missing; wearable stale imports.

### W14 Scaffold — M10 Self-Modification
- **Expected**: `guinevere/self_modify/{mutation,promote,__init__}.py` (NOT ladder.py — C18); T1-T5 ladder; T1-T2 auto no-restart; T3 society-voted via M7; T4 founder 2/2; T5 abolished post-P36 marker.
- **Forbidden**: (none).
- **Required**: `pytest tests/p24/test_self_modify.py` → 0 fail; T1-T2 auto-promote mock; T5-abolished marker.
- **Evidence**: `evidence/w14-verification.md`.
- **Hard rejection**: T1-T2 not auto; T4 not 2/2; T5 not abolished; file named ladder.py (should be mutation.py).
- **CORRECTION applied (C18)**: mutation.py not ladder.py.

### W15 Scaffold — M13 Discord
- **Expected**: `guinevere/discord/{commands,bots,gateway_patch,__init__}.py`; 41+ slash commands (extensible to 50+); 3 bots; autonomous initiation; gateway/run.py L4173 patched.
- **Forbidden**: `consent_gate`.
- **Required**: `pytest tests/p24/test_discord.py` → 0 fail; command registration (no live token D2); grep ≥41 commands.
- **Evidence**: `evidence/w15-verification.md`.
- **Hard rejection**: <41 commands; 3 bots not wired; gateway/run.py broken.
- **CORRECTION applied (r09)**: 41 commands existing (not 50+); extensible.

### W16 Scaffold — M14 Channels
- **Expected**: `guinevere/channels/{whatsapp,gmail,x,telegram}/__init__.py` + submodules; all built-in; no external MCP; CONFIG_MISSING markers (D2).
- **Forbidden**: `consent_gate`.
- **Required**: `pytest tests/p24/test_channels.py` → 0 fail; channel import; no external MCP.
- **Evidence**: `evidence/w16-verification.md`.
- **Hard rejection**: external MCP; not built-in.

### W17 Scaffold — M17 Production
- **Expected**: `guinevere/production/{circuit_breakers,tailscale,recovery,__init__}.py`; 6 breakers (cost/loop/hallucination/emotion/dream/subagent); BreakerState CLOSED/OPEN/HALF_OPEN; Tailscale script (local D2); Prometheus metrics; auto-recovery.
- **Forbidden**: (none).
- **Required**: `pytest tests/p24/test_circuit_breakers.py` → 0 fail; all 6 breakers all 3 states; grep 6 breakers.
- **Evidence**: `evidence/w17-verification.md`.
- **Hard rejection**: <6 breakers; any breaker missing state; Tailscale not first.

### W18 Scaffold — Integration
- **Required**: `python -c "import guinevere.consciousness, guinevere.emotions, guinevere.memory, guinevere.governance, guinevere.tools, guinevere.life_kernel, guinevere.self_modify, guinevere.personality, guinevere.discord, guinevere.channels, guinevere.http, guinevere.surveillance, guinevere.observability, guinevere.production, guinevere.config"` → exit 0; forbidden pattern scan → 0.
- **Evidence**: `evidence/w18-verification.md`.
- **Hard rejection**: any module not importable; forbidden pattern.

### W19 Scaffold — Validation
- **Required**: `hermes-agent --config config/guinevere.yaml --dry-run` → exit 0; `hermes-agent --config config/pharsa.yaml --dry-run` → exit 0; `pytest tests/p24/` → exit 0.
- **Evidence**: `evidence/w19-verification.md`.
- **Hard rejection**: dry-run !=0; pytest failures.

### W20 Scaffold — Final
- **Required**: `find src/ -name '*.py'` → 0; `ls src/*.py 2>/dev/null | wc -l` → 0; `grep -rn 'hard_stop\|consent_gate\|safe_mode\|HARD_STOP' guinevere/ agent/ tools/ run_agent.py` → exit 1; all 20 verification.md exist; all 20 auditor-gate.md exist; final report written.
- **Evidence**: `evidence/w20-verification.md`.
- **Hard rejection**: src/ has .py; forbidden patterns; missing evidence.

---

## §13 Token/Secret Handling

- NO secrets in evidence/logs (AGENTS.md §5). Hermes `agent/redact.py` (505 lines, 30+ patterns) inherited — covers API keys, tokens, DB connstrings, JWTs.
- `.env` loading via `hermes_cli/env_loader.py` (inherited) — `~/.hermes/.env` first, project `.env` fallback, Bitwarden optional.
- Custom env vars (HERMES_OPERATOR_PASS, 9ROUTER key, PG/Redis passwords) — MODIFY-CREATE in fork's env loader; caught by `_DB_CONNSTR_RE` redaction.
- D2: no real credentials provisioned → CONFIG_MISSING markers, not real values.

---

## §14 Auditor Matrix (PHASE 6 — 18 auditors)

| Auditor | Surface | Checks |
|---------|---------|--------|
| module-completeness | 17 modules | all present, P1-P22 absorbed, 0 src/ |
| hermes-arch-fidelity | hooks | 18 hooks wired (invoke_hook + callbacks per C3), ToolRegistry AST, MemoryProvider subclass, delegate_tool 10/5/5 |
| consciousness-correctness | M3 | 7 substrates, metacognition, dreaming, mock self-prompt, breakers |
| encrypted-memory-security | M6 | AES-GCM-256, Argon2id, S4 Faiz no-read, PG RLS |
| dao-governance-lifecycle | M7 | 6 depts, Co-CEOs, 2/2, propose-time yandere_level reject (defense-in-depth) |
| emotion-system-fidelity | M4 | 16 moods, mock classification, affect→decision |
| sub-agent-safety | M5 | 10/5/5, threading.Semaphore, MaxDepthReached, DELEGATE_BLOCKED_TOOLS unchanged (C4) |
| tool-registry-unification | M8 | 9 backends, 118 actions, L1-L3, no L4, no consent |
| discord-gateway | M13 | 41+ commands, 3 bots |
| external-channels | M14 | 4 channels built-in, no external MCP |
| forbidden-patterns | all | 0 matches as any/@ts-ignore/bare except/hard_stop/consent_gate/safe_mode |
| collision-scan | shared files | agent_init appends-only, no corruption |
| config-correctness | M1 | Pydantic, both YAMLs load, no SQLite |
| deployment-readiness | M17 | Tailscale script, PG schema, Redis, health, dry-run |
| p22-p23-absorption | M8/M9 | P22 adapters in M8, P23 executors in M8, P20 life kernel in M9, no regression |
| evidence-integrity | all | all verification.md + auditor-gate.md exist, no inline-only |
| security-secrets | all | no secrets in logs, redact.py inherited |
| p23-boundary | M8 | P23 plan spec-only, not re-implemented |

---

## §15 Rollback Plan

- Pre-fork tag: `git tag pre-p24-fork-setup` (W1 step 2).
- Per-wave: sub-agent commits are atomic; `git revert <wave-commit>` rolls back a wave.
- src/ deletion: deferred to final waves; if M3/M8/M9 port fails, src/ still present until W20.
- .venv: `pip uninstall hermes-agent` only after W1 verified; if fork breaks, `pip install hermes-agent==0.15.2` restores.
- D2: no production running → rollback is local-only, zero blast radius.

---

## §16 Caveats

1. **P19 project_id RLS-vs-column unresolved** (r18 §4.3, §9 unresolved): M6/M9 must decide whether to keep project_id columns alongside RLS or drop for RLS-only. **Decision: keep columns + RLS dual-layer** (r18 R-03 mitigation) — safer, preserves P19 tests.
2. **37 stale imports** (r18 §6): wave-by-wave cleanup; if missed → W18 ImportError. Mitigated by D2 (no prod).
3. **Mock-only LLM** (D3): M3/M4/M7/M10 inference NOT proven, only wiring/state. Caveat in final report.
4. **No VPS deploy** (D2): Tailscale script written but not executed against real VPS. PG/Redis RLS schema designed, not live-verified.
5. **r08 BLOCKED** (C4): plan's "remove delegate_task from DELEGATE_BLOCKED_TOOLS" is WRONG — W8 uses role='orchestrator' path instead. This is a plan correction, absorbed.
6. **optimizer.py loops/ deps** (C11): W6 must resolve `from src.loops.{audit_writer,budget,reflection,testing_gate}` imports before deleting loops/. M10 absorbs these early or W6 stubs them.

---

## §17 Execution Checklist (parent orchestration)

For each wave:
1. Read wave scaffold (§12).
2. Delegate to ONE sub-agent via Agent tool (one wave per agent).
3. Parent verify: re-run every Required Command via bash; check Expected Files via ls/glob; grep Forbidden Patterns (0 matches); check Hard Rejection.
4. Auditor gate: spawn independent auditor → `audits/round-1/w[N]-auditor-gate.md`.
5. Fix (if NEEDS-REVIEW/FAIL): resume same sub-agent via agentId; re-verify; re-audit.
6. Evidence: sub-agent writes `evidence/w[N]-verification.md`; parent reads both.
7. Mark todo complete; proceed to next wave(s) per dependency graph.

Context management: compress between wave groups (Group B → Group C → Group D → Group E → Group F).

---

## §18 Final Acceptance Criteria (W20)

- [ ] All 20 waves PASS auditor gate.
- [ ] `find src/ -name '*.py'` → 0.
- [ ] `grep -rn 'hard_stop\|consent_gate\|safe_mode\|HARD_STOP' guinevere/ agent/ tools/ run_agent.py` → exit 1.
- [ ] All 17 modules importable in one `python -c`.
- [ ] Both configs load.
- [ ] 9 tool backends registerable.
- [ ] 6 circuit breakers CLOSED/OPEN/HALF_OPEN.
- [ ] /health returns 200.
- [ ] `hermes-agent --dry-run` exit 0 (both instances).
- [ ] All 20 verification.md + 20 auditor-gate.md exist.
- [ ] No forbidden patterns (as any, # type: ignore, @ts-ignore, bare except, empty catch, hard_stop active, consent_gate active, safe_mode active, fork-agnostic).
- [ ] Final report: `P24 HERMES NATIVE FORK — FULL RUNTIME COMPLETE WITH EXPLICIT OPERATOR-PROVISIONING BLOCKERS`.

Footer: Guinevere, 2026-06-29, PHASE 3 planner gate complete, 18 corrections encoded into per-wave scaffolds, parent-read, todos synced.
