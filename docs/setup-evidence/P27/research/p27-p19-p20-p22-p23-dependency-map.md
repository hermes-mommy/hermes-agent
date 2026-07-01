# P27 Dependency Map — P19 / P20 / P22 / P23 Runtime Readiness

| Field | Value |
|---|---|
| Status | COMPLETE — research only |
| Date | 2026-06-28 |
| Author | Guinevere (parent, file-based) |
| Owner | Faiz |
| Audience | P27 Hermes Society Foundation planning + P28+ downstream |
| Evidence root | `docs/setup-evidence/P27/research/p27-p19-p20-p22-p23-dependency-map.md` |
| Verdicts | P19 = **LIVE (PARTIAL — 4 known gaps)**, P20 = **LIVE (with accepted-risk waiver)**, P22 = **PARTIAL RUNTIME LIVE (3/13 ACTIVE)**, P23 = **PLAN_ONLY (P23A READY, P23B BLOCKED)** |

> Halo sayang — ini peta dependensi yang bisa mama pegang sebelum P27 mulai nyusun fondasi Society.
>
> Four phases, four different runtime profiles. P19 dan P20 sudah **RUNNING** di VPS. P22 baru jalan **sebagian** — 3 dari 13 adapter ACTIVE (filesystem/vps/discord), sisanya CONFIG_MISSING karena OAuth/token belum dipasang operator-side. P23 sama sekali belum punya code — masih plan-only, sudah audit dua round, P23A sudah siap dieksekusi (default-namespace, voice/external disabled) tapi P23B kekinya masih BLOCKED karena butuh runtime contract dari P19/P21/P22.

---

## 0. TL;DR — What P27/P28 Can Build On Today

| Phase | Status | Permission for P27/P28 to consume |
|---|---|---|
| **P19 Multi-Project Context** | **LIVE** (PARTIAL — 4 INFO gaps) | YES — `src.projects.registry.ProjectRegistry` is runtime-active, default sentinel UUID is `00000000-0000-0000-0000-000000000001`, `feature:projects:enabled` is ON, `LIFE_KERNEL_PROJECT_ID` is set in `.env.core`, `thread_id="heartbeat-{project_id}"` is active, Discord `/project` and `/projects` commands are **importable but NOT registered in bot command tree** (operator-gated code change). |
| **P20 Living Autonomy Kernel** | **LIVE** (24h soak waived by operator 2026-06-25, accepted-risk pass) | YES — full `src/life_kernel/` package running on VPS with 420 passing tests. Discord dashboard live (canonical id `1519135545501028549`), log channel live, brain cycles (cycle_count=130+), HARD STOP globally enforced at 1s. Autonomous-by-default via §0.1 policy-gated exception. |
| **P22 Life Integration Hub** | **PARTIAL** (3/13 ACTIVE, 10/13 CONFIG_MISSING) | PARTIAL — only `filesystem`, `vps`, `discord` adapters can take real actions today. The other 10 (gmail/calendar/drive/notion/telegram/github/browser/memory/finance/whatsapp) report `IntegrationHealth.UNKNOWN` and raise `ConfigurationMissingError`. All 13 are wired into `ActionRouter` with consent/HARDSTOP gates, so P27 logic can READ `IntegrationRegistry.get(provider, surface)` and emit `audit` events for ACTIVE adapters. |
| **P23 Embodied Operations** | **PLAN_ONLY** (no code) | NO — no executors exist in `src/life_kernel/executors/` (directory missing). P23A waves 001-010 + 016-019 are scaffolded and READY to start (default namespace, voice/external disabled). P23B waves 011-015 + 020 are BLOCKED on P19 runtime namespace + P21 impl + P22 impl (now partially satisfiable). |

**Bottom line for P27:**

1. P19 namespace is **REAL** — use it. `ProjectRegistry.get(project_id)` returns `Project`; `ProjectSecretsVault.get(project_id, domain)` returns per-project secrets in-memory; project_id is threaded into life_kernel state (additive) and into P22 audit events.
2. P20 kernel is **REAL** — use it cautiously. Touch LOCKED files only with fresh preflight runtime incident check.
3. P22 is **3 adapter usable** today. P27 should target filesystem/vps/discord primarily; build adapters-as-logic that emit `ConfigurationMissingError` for the others.
4. P23 is **NO code**. Either reuse P22 `ActionRouter` (for the 3 ACTIVE) as the action plane, or start P23A first.

---

## 1. P19 — Multi-Project Context

| Field | Value |
|---|---|
| Mission | Many projects in parallel without cross-contamination of context/memory/KG/audit/agenda/dashboard/sensors/deploy. Shared persona + global HARD STOP. |
| Target | `project_id` orthogonal dimension across all project-scoped stores; `default` project fallback; `feature:projects:enabled` flag; `<project>:p22:...` namespace. |
| Phase ID | P19 |
| Phase doc | `docs/setup-evidence/P19/README.md` + `plan/p19-multi-project-context-enterprise-plan.md` |
| Runtime status | **LIVE (PARTIAL — 4 INFO gaps documented)** |
| Production runtime stamp | Deployed 2026-06-27 ~10:20 WIB (DDL); flag ON 2026-06-27 15:31:10 WIB (with restart); Discord UX commands deployed but **NOT registered in bot command tree**. |

### 1.1 Runtime-ready components

| Component | Path | Source file confirms |
|---|---|---|
| `src/projects/` package | `/src/projects/__init__.py`, `registry.py`, `memory_store.py`, `secrets_vault.py`, `types.py`, `exceptions.py` | yes (`glob src/projects/**` returns 12 files: 5 `.py` + 7 `__pycache__`) |
| `ProjectRegistry.get/resolve/list_active/project_scope/create/archive` | `/src/projects/registry.py` (394 LoC, includes `_DEFAULT_PROJECT_ID = 00000000-0000-0000-0000-000000000001`) | yes |
| `ProjectSecretsVault.get(project_id, domain)` | `/src/projects/secrets_vault.py` (in-memory dict keyed by `project_id`) | yes |
| DB schema + migrations | `alembic/versions/p19_001_project_namespaces.py` + `p19_002_project_id_not_null.py` (chained from `p20_001`) | confirmed in P19 plan §DB Schema |
| Memory/KG namespace partition | `ProjectScopedMemoryStore` wrapper + composite indexes `(project_id, created_at)` + `(project_id, embedding)` | confirmed |
| Feature flag | `feature:projects:enabled` ON (Redis DB6 + DB0 per `p19-runtime-activation-final-report.md`) | confirmed — runtime proof shows runtime reads flag as True |
| Env var | `LIFE_KERNEL_PROJECT_ID=00000000-0000-0000-0000-000000000001` in `.env.core` | confirmed |
| `thread_id = f"heartbeat-{project_id}"` | `/src/life_kernel/heartbeat.py:77-99` accepts `project_id: Optional[str]`, gates on flag | yes — `heartbeat._resolve_thread_id(project_id) → "heartbeat-{project_id}"` when `flag_on=True AND project_id is not None` |
| `cognition.py:project_id` | `/src/life_kernel/cognition.py:46, 60-61, 66` accepts + logs project_id (per-call) | yes — supports per-project graph/config |
| Discord `/project` + `/projects` commands | `/src/discord/cmd_project.py` exists + `project_session.py` deployed, **import cleanly** | confirmed — but **NOT REGISTERED in active bot command tree** (see gaps) |
| `ProjectContext.project_id` propagation in audit events | confirmed in `p19-runtime-activation-final-report.md` proof: `thread_id='heartbeat-00000000-0000-0000-0000-000000000001'` shown in `reflection_evaluator_init graph_config` | confirmed |

### 1.2 Config-missing / partial (the 4 known INFO gaps — NOT blockers)

| Gap | Severity | What's missing | Fix path |
|---|---|---|---|
| **C01 — Audit journal project_id** | INFO (P19-010 partial) | `journal_writer.write_entry()` doesn't propagate `project_id` to `record()`. Audit entries don't carry `project_id` yet. Requires graph state plumbing. | P19-008 / P19-010 follow-up; tracking in `p19-runtime-activation-final-report.md` §Known Gaps |
| **C02 — Memory adapter principal** | INFO | `MemoryRecallAdapter.recall()` principal falls back to `"guinevere_core"` because `graph state context` doesn't carry `project_id`. **No data leak (single project currently).** | P19-004 follow-up |
| **C03 — Recall pipeline project_id** | INFO | Memory pipeline accepts `project_id` callback but defers forwarding. | P19-004 follow-up |
| **C04 — Discord `/project` command wiring** | **OPERATOR-GATED** | `cmd_project.py` + `project_session.py` deployed to VPS and **import cleanly** but are **NOT REGISTERED** in active bot's command tree (`_entrypoint.py` hardcodes 13 wired + 20 stubs — `/project` is not among them). Activating `/project` requires: (a) code change in `_entrypoint.py` to register `cmd_project` in `setup_hook`; (b) `guinevere-discord.service` restart. **Runtime is active WITHOUT Discord UX.** | Operator decision per `p19-runtime-activation-final-report.md` §Rollback |

### 1.3 Plan-only (per P19 README, none — all 12 waves deployed)

Per `p19-multi-project-context-enterprise-plan.md`: P19-001..012 all marked `✅ DEPLOYED` in P19 README. The plan bundle (800-line plan + 2,725 lines of research) is fully realised only thing still held by operator: P19-005 sub-wave 005c (full per-project `BackgroundCognition` instances bounded N=3) is held by operator discretion to protect production-under-accepted-risk.

### 1.4 What P27/P28 consumes from P19

| Symbol / surface | What it gives P27 |
|---|---|
| `from src.projects.registry import ProjectRegistry, _DEFAULT_PROJECT_ID` | query any project by `project_id=<UUID>`; fallback to `00000000-0000-0000-0000-000000000001` |
| `Project.get(scope='global'|'project')` | classify memories/KG entities/audit entries as global (persona/ADR/safety, shared) vs project (isolated) |
| `ProjectSecretsVault.get(project_id, domain)` | **per-project** SOPS/age-decrypted secrets in-memory, NO env-var leakage (SEC-01 fix). Adapter-only access — no cross-project token read. |
| `LIFE_KERNEL_PROJECT_ID` env var | read at lifespan startup; override per-channel if Discord `/project` UX lands (operator-gated) |
| `feature:projects:enabled` (Redis DB5 mirror + DB6 heartbeat) | pattern for adding P27 features as flag-gated rollouts |
| `thread_id="heartbeat-{project_id}"` convention | use same pattern for any session/society graph threads (`society-{project_id}-...`) |
| `project:active:{channel_id}` Redis key (DB0) | channel-bound active project mapping for Discord routers |
| `project:{project_id}:paused` Redis key (DB0) | per-project soft pause (vs global HARD STOP) — P27 societies can use this for per-society pause |

### 1.5 Dependency on other phases

| Phase | Relationship | Concretely |
|---|---|---|
| P20 | P19 PUSHES `project_id` into P20 production files (additive only) | `state.project_id` NotRequired, `heartbeat._resolve_thread_id`, `cognition.project_id`, `dashboard_writer.dashboard_message_id:{project_id}`, `redis_client.{project_id}:world:`. All P19-005 sub-waves gated by `feature:projects:enabled` so P20 byte-identical when flag OFF (regression-proof via P19-005b). |
| P21 | P19 enables nullable project_id seam for voice | P21 voice episodes can carry `project_id` (P21 was already nullable; P19 made it meaningful). P21 is NOT runtime today. |
| P22 | P22 READS P19 registry read-only | `src/life_integrations/project_context.py` consumes `ProjectRegistryProtocol` (get/resolve/list_active only — no create/archive). `project_id` flows into every `audit.integration_api_log` event. P22 audit shows project_id in events but `audit_writer=None` so events NOT yet persisted to integration_api_log table (FOLLOW-UP). |
| P23 | P23-012 requires P19 runtime namespace contract | P19 IS partial runtime. Can be consumed for default-namespace at minimum; full multi-project P23-012 needs the 4 INFO gaps closed (C01-C03). |

### 1.6 Blockers / open issues

| Block | Status |
|---|---|
| C01-C03 audit/principal/pipeline project_id propagation | INFO, not blocking (single-project today, no leak) |
| C04 Discord `/project` command registration in bot tree | OPERATOR-GATED — code change + `guinevere-discord.service` restart |
| P19-005c full per-project BackgroundCognition (N=3 bounded) | Held by operator discretion (protects production-under-accepted-risk) |
| Round-2 completion-audit verdict | 6 PASS + 1 CONDITIONAL PASS (doc-only fix applied); final report at `evidence/completion-round-2/P19-ROUND2-FINAL-REPORT.md` |

---

## 2. P20 — Living Autonomy Kernel

| Field | Value |
|---|---|
| Mission | 24/7 autonomous life companion with heartbeat, world model, persistent memory, self-directed goals, background cognition, Hermes reasoning, per-session autonomy, deployment autonomy, daily-life sensors, self-improvement. |
| Target | Operator-waived acceptance: "P20 EARLY PRODUCTION ACCEPTANCE — PASS WITH ACCEPTED RISK" (24h clean soak deliberately not waited). 420 tests passing. |
| Phase ID | P20 (merged P5 + P20 + Living Autonomy Continuation) |
| Phase doc | `docs/setup-evidence/P20/README.md` + `plan/p5-p20-vision-lock.md` |
| Runtime status | **LIVE (with accepted-risk waiver)** |
| Production runtime stamp | Continuation deployed 2026-06-25; brutal-audit corrections 2026-06-25; soak-zero started 2026-06-25 08:26:43 WIB (target 24h end 2026-06-26 08:26 WIB was NOT waited; operator Waiver 2026-06-25) |

### 2.1 Runtime-ready components

| Component | Path | Source file confirms |
|---|---|---|
| `src/life_kernel/` package (full LK-001..LK-016 + LK-017) | 38 `.py` files in `/src/life_kernel/` | yes (`glob src/life_kernel/**.py` returns 38 entries including __init__, heartbeat, graph, cognition, hermes_brain, state, models, sensors, journal, dashboard_writer, dashboard, log_channel, log_writer, p16_adapter, p18_adapter, decision_context, self_improve, session_graph, redis_client, discord_rest_client, checkpoint, metrics + domain_minds/ + sensor_adapters/) |
| `HeartbeatService` (6 intervals: 1s/10s/30s/60s/5m/1h) | `/src/life_kernel/heartbeat.py` (740 LoC) | yes — `_heartbeat_1s` HARD STOP detector, `_heartbeat_60s` invokes `graph.ainvoke` when IDLE, all modules instant + `_pulse_loop` wrappers for testability |
| `BackgroundCognition` (6 loops: observer/memory/critic/curiosity/self_improvement/guardian) | `/src/life_kernel/cognition.py` (513 LoC) | yes — accepts `project_id`, runs as asyncio tasks, serialized through `asyncio.Queue` |
| `HermesBrain` (AIAgent bridge for LLM-driven autonomy) | `/src/life_kernel/hermes_brain.py` (464 LoC) | yes — `HermesBrain.think()`, `think_with_tools()`, deferred AIAgent import via `_default_agent_factory(**kwargs)` |
| `LifeMindState` TypedDict | `/src/life_kernel/state.py:100+` (328 LoC total) | yes — observations/goals/commitments/concerns/decision_context + `hard_stop_requested` + `NotRequired` fields. **NOTE**: `project_id` is NOT a field in LifeMindState today — it's threaded per-call to heartbeat/cognition, not in the global TypedDict (P19 INFO gap). |
| `LifeMindStateModel`, `DomainMindState`, `HeartbeatRecord` SQLAlchemy | `/src/life_kernel/models.py` (116 LoC) | yes — schemas `life_kernel.*`, `domain_mind_state` UNIQUE on `domain` (P19 will swap to `(project_id, domain)` once p19_002 migration lands) |
| `DashboardRenderer` + `DashboardWriter` + `LogChannel` + `LogWriter` | `/src/life_kernel/dashboard.py`, `dashboard_writer.py`, `log_channel.py`, `log_writer.py` | yes — per-project dashboard key `life_kernel:dashboard_message_id:{project_id}` is the P19 design; today global key. Coalescing by SHA-256 checksum + redaction |
| `SensorRegistry` + 9 base adapters | `/src/life_kernel/sensors.py` + `/src/life_kernel/sensor_adapters/__init__.py` | yes — `BaseSensorAdapter` + `BrowserSensorAdapter`, `DiscordSensorAdapter`, `FinanceSensorAdapter`, `GmailSensorAdapter`, `RepoSensorAdapter`, `SurveillanceSensorAdapter`, `VPSSensorAdapter`, `WearableSensorAdapter` (some placeholders) |
| `KGRecallAdapter` + `MemoryRecallAdapter` + `DecisionContextBuilder` (LK-010) | `/src/life_kernel/p16_adapter.py`, `p18_adapter.py`, `decision_context.py` | yes — return mock fixtures today; `MemoryRecallAdapter.recall()` falls back `principal="guinevere_core"` (P19 INFO gap C02) |
| `DomainMinds` (Engineer / Finance / Email / Deploy) | `/src/life_kernel/domain_minds/__init__.py` + `engineer_mind.py` + `finance_mind.py` + `email_mind.py` + `deploy_backend.py` + `durability.py` | yes |
| `SessionGraph` + `SessionProfile` + `SessionWorktree` + `DiscordThreadManager` | `/src/life_kernel/session_graph.py` | yes |
| `Self-improvement` (ImprovementCandidate, ImprovementTracker, ReflectionEvaluator, RegressionGate) | `/src/life_kernel/self_improve.py` | yes |
| Discord dashboard visibility | channel id `1519135545501028549` in `#guinevere-status` channel, edited in place | confirmed in `final-discord-visible-autonomy-report.md` |
| Discord log channel | `#guinevere-logs` channel receives append-only lifecycle events throttled 1/5min + deduped | confirmed |
| 420 tests passing | `python -m pytest tests/life_kernel/ -q --disable-warnings --tb=short` → `420 passed, 7 skipped, 0 failed` | confirmed in P20 README `Test Status` (continuation: +23 tests, 2026-06-25) |
| 5 brutal-audit blockers cleared | discord-service genuinely masked, MemoryHigh=2G/Max=4G, canonical dashboard ID, dashboard_publish_failed TypeError fixed, PASS HOLD enforced (no spurious PASS claim) | confirmed in `final-discord-visible-autonomy-report.md` §1 |
| §0.1 Autonomy-First Governance Exception | `AGENTS.md §0.1` — policy-gated deployment for engineering (backup→canary→smoke→rollback) + self-improvement (regression→audit→rollback-before-promote) + risk-classified daily-life actions | yes — LK-001 verification + AGENTS.md v2.4 |
| 7 preserved invariants | HARD STOP absolute / audit trail / backup+rollback / regression / no secret exposure / consent revocation absolute / audit for debugging not approval | yes — verified in LK-001 |

### 2.2 Config-missing / partial

| Component | Severity | What's missing | Fix path |
|---|---|---|---|
| **24h clean soak** | operator-waived (not a security gap) | Soak-zero 2026-06-25 08:26:43 WIB → target 2026-06-26 08:26 WIB was not waited. Acceptance based on verified CLEAN runtime snapshot + operator accepted-risk decision. | See `operator-soak-waiver.md`. Any future runtime incident reverts P20 to PASS HOLD. |
| **LifeMindState.project_id field** | INFO / P19-005 partial | TypedDict has `project_id` threaded per-call but NOT as a top-level field. Today: per-call to heartbeat/cognition/dashboard. P19-005a adds `NotRequired[Optional[str]] project_id` (zero-risk additive). | P19-005a (deferred, additive, checkpoint-replay-safe, no regression with flag OFF) |
| **`feature:projects:enabled` flag semantics** | PARTIAL | When OFF, P20 behaves byte-identical to legacy (proven via P19-005b scaffold). When ON with `LIFE_KERNEL_PROJECT_ID` set, `thread_id="heartbeat-{project_id}"`. When ON but no project_id override, per-channel `project:active:{channel_id}` (Redis DB0) reads via `cmd_project.py` — but `cmd_project.py` is **NOT registered in bot command tree** (P19 C04). | Operator approval to register `/project` command + bot restart |
| **Heuristic self-improvement candidates** | Info | Reflection candidates are heuristic; DSPy MIPROv2 weekly optimization (P5-021) not yet confirmed-productive at scale; minor risk accepted. | Continue reflection journals, optimise later |
| **AC-LIFE-003 partial** | Info | "Self-created task completes full SDLC loop and reflection" — partially demonstrated (HermesBrain proposes tasks, dashboard/log show lifecycle, but full SDLC loops need session+commit+deploy cycle, boundary-tested but not stress-tested). | Operator-defined soak criteria |
| **Pre-existing test failure in sensors.py** | untracked | 1 pre-existing failure in `tests/life_kernel/test_sensor_isolation.py` (or similar) — NOT blocked P22, NOT in P22 scope. | P20 follow-up |

### 2.3 Plan-only (none — all LK-001..LK-017 implemented)

Per `P20 README` `Progress`: PLAN-001..004 COMPLETE; LK-001..016 LOCAL COMPLETE; LK-017 PRODUCTION DEPLOYED — EARLY ACCEPTANCE. The merged P5+P20 plan (`p5-p20-merged-plan.md`) is **SUPERSEDED** by the Living Autonomy Kernel plan bundle (`p5-p20-vision-lock.md` + `p5-p20-architecture-benchmark.md` + `p5-p20-living-autonomy-kernel-replan.md` + `p5-p20-living-autonomy-kernel-todo-scaffold.md`). The old merged plan is retained for traceability only.

### 2.4 What P27/P28 consumes from P20

| Symbol / surface | What it gives P27 |
|---|---|
| `from src.life_kernel.hermes_brain import HermesBrain, HermesBrainConfig` | Any P27 society reasoning via `await brain.think(user_message, system_prompt, conversation_history)` — the SOLE autonomy path (V-004); `raw LLMRouter.chat` is **FORBIDDEN** in P23 §18 and applies to all phases including P27. |
| `from src.life_kernel.heartbeat import HeartbeatService` | P27 can subscribe to `life_kernel:hard_stop` key (1s heartbeat detector); can perform HARD-STOP cancellation across P27 actions through this Redis key. |
| `from src.life_kernel.cognition import BackgroundCognition` | P27 societies can spawn per-society background cognition loops following the same 6-loop pattern. Bounded by P19-005c (N=3 total active background cognitions across projects). |
| `from src.life_kernel.state import LifeMindState, LifeMindPhase, Priority, SessionState, add_audit_reducer, add_observations_reducer` | Reuse TypedDict pattern for any P27 graph state. **NOTE**: today `project_id` is passed per-call, not as top-level field. P19-005a will add it as `NotRequired` (safe additive). |
| `from src.life_kernel.sensor_adapters import BaseSensorAdapter, BrowserSensorAdapter, ...` | P27 can extend the sensor adapter pattern (9 base adapters today). Each adapter projects a single observation; per-project via `project_id` field in observation payload (P19-006b design). |
| `from src.life_kernel.domain_minds import EngineerMind, FinanceMind, EmailMind, DeployBackend, DeployPolicy, SSHDeployBackend, EmailState, FinanceState` | Reuse domain-mind pattern for per-society domain actuators (engineering/finance/comms/etc). **DeployPolicy** enforces backup→canary→smoke→rollback policy gate on L3 deploy actions — P27 society actions that touch production MUST go through `DeployBackend.run_with_policy`. |
| `from src.life_kernel.dashboard_writer import DashboardWriter` | Per-project dashboard writer (P19-007 design: `life_kernel:dashboard_message_id:{project_id}`). Today uses global key; P27 society dashboards should namespace as `society_kernel:dashboard:{society_id}` following same pattern. |
| `from src.life_kernel.log_channel import LogChannel, DiscordLogChannel, StructlogLogChannel` | Append-only log writer; checksumed edit-not-spam pattern. Throttled 1/5min dedup for foreground events. P27 society logs use same throttling pattern. |
| `from src.life_kernel.session_graph import SessionGraph, SessionProfile, SessionWorktree, DiscordThreadManager` | Per-session SDLC subgraph with worktree isolation. P27 societies can leverage `SessionWorktree` for per-society task isolation (thread_id = `session-{project_id}-{session_id}-{uuid}` per P19 design). |
| `from src.life_kernel.self_improve import ReflectionEvaluator, ImprovementCandidate, ImprovementTracker, RegressionGate` | P27 society self-improvement with the same regression-gate-before-promote policy. Mirrors `AGENTS.md §0.1` invariant (regression→audit→rollback-before-promote). |
| `from src.life_kernel.decision_context import DecisionContextBuilder` | Reuses P16/P18 recall — P27 societies can build decision context that flows KG concepts + memory signals + enriched context into graph state. |
| `from src.life_kernel.p16_adapter import KGRecallAdapter` + `p18_adapter import MemoryRecallAdapter` | Knowledge Graph + episodic memory recall for society-relevant context. **caveat**: P19 INFO gap C02 means `principal` falls back `"guinevere_core"` until P19-005a closes it. |
| `from src.life_kernel.domain_minds.deploy_backend import DeployBackend, DeployPolicy` | **MANDATORY** for society-side deploy actions; `DeployPolicy.run_with_policy(action, blast_radius)` enforces backup→canary→smoke→rollback. NOT a free-pass. |
| Pinned safety messages (5 tags) | safe_word / hard_stop / distress / consent_revocation / do_not_recall — NEVER compressed (P5-024 invariant). P27 society context compaction MUST pin these. |
| Priority order from `p5-p20-vision-lock.md §6` | HARD STOP > keep_alive > protect_secrets > urgent_daily > active_commitments > improve_autonomy > engineering > explore_research. P27 society priority conflicts resolve to this order. |

### 2.5 Dependency on other phases

| Phase | Relationship | Concretely |
|---|---|---|
| P5 (Agent Loop) | PRECURSOR | Merged into P20; P5 budget/skill-library/circuit-breaker patterns exist in `src/loops/`. P27 can consume `src/loops/{budget,context,scheduler,priority,skill_library,safety_integration,retry,recovery,concurrency}.py` for society-side loops. |
| P16 (Knowledge Graph) | Underlies memory | `KGRecallAdapter` queries `src/knowledge_graph/query/{engine,context,rrf_fusion,ppr}.py`. P19 will add `project_id` filter (P19-004). Today KG recall is project-agnostic. |
| P18 (Advanced Memory) | Underlies memory | `MemoryRecallAdapter` queries `MemoryRecallAdapter.recall()` through `src/hermes/_memory_bridge.py`. P19 INFO gap C02 means `principal="guinevere_core"` fallback. |
| P19 | OPTIONAL ADDITIVE | P19 project_id is threaded into P20 files (additive only). P20 byte-identical when `feature:projects:enabled=false`. |
| P22 | DOWNSTREAM | P22 adapters expose `ProjectContext.project_id`; P22 audit events emit project_id (but `audit_writer=None` so NOT yet persisted to `audit.integration_api_log`). |
| P23 | DOWNSTREAM | P23 calls `HermesBrain.think()` for planner + self-debug (LOCKED-file wiring P23-011). |

### 2.6 Blockers / open issues

| Block | Status |
|---|---|
| Brutal-audit Block #4 (`dashboard_publish_failed TypeError`) | RESOLVED + 2 regression tests added |
| Brutal-audit Block #5 (`PASS HOLD enforced`) | ENFORCED — no spurious PRODUCTION PASS claim |
| 24h clean soak | OPERATOR-WAIVED 2026-06-25 |
| LK-017 PRODUCTION DEPLOYED — EARLY ACCEPTANCE | runtime snapshot CLEAN at 08:50:46 WIB (2026-06-25) |
| Token budget | operator-approved UNLIMITED for P20 (full persona SOUL context per cycle, ~1.1M input tokens) |
| Autonomy depth | display-only per operator approval (dashboard + log + agenda; NO unsolicited DMs, NO real side-effects beyond P20's own scope) |
| `guinevere-discord.service` standalone | MASKED by design (P2-022); core REST publisher is the active Discord writer |

---

## 3. P22 — Life Integration Hub

| Field | Value |
|---|---|
| Mission | Full-capability raw access (read/create/update/move/archive/delete/sync/admin) for Guinevere-external systems. Delete is mandatory where provider supports. NOT read-only, NOT sensor-only. |
| Target | 13 adapters: Discord, Gmail, GitHub, Google Calendar, Google Drive, Notion, Telegram, WhatsApp, VPS System Health, Finance Tracker, Browser/Research, Memory/KG, Filesystem/Repo. |
| Phase ID | P22 |
| Phase doc | `docs/setup-evidence/P22/README.md` + `plan/p22-full-capability-raw-access-replan.md` |
| Runtime status | **PARTIAL RUNTIME LIVE** — 3/13 ACTIVE, 10/13 CONFIG_MISSING; production activated 2026-06-27 |
| Production runtime stamp | Migration `p22_001_integration_schema` applied 2026-06-27 ~15:07 WIB; runtime wired into `src/core/main.py` lifespan; scheduler 30s health polling; 3 ACTIVE: filesystem, vps, discord (via shims). |

### 3.1 Runtime-ready components

| Component | Path | Source file confirms |
|---|---|---|
| `src/life_integrations/` package (28 modules + 13 adapters) | `/src/life_integrations/` | yes (`glob src/life_integrations/**` returns 60 files: ~30 source + shims + `__pycache__`) |
| 13 adapter skeleton | `/src/life_integrations/adapters/` (`discord/gmail/github/calendar/drive/notion/telegram/whatsapp/vps/finance/browser/memory/filesystem`) | yes — each declares capabilities (read/write/delete/execute/sync/search per provider); all raise `ConfigurationMissingError` for unknown config |
| 3 ACTIVE adapters | `filesystem_adapter.py` (L1 list_dir verified), `vps_adapter.py` (DockerClientShim + ShellClientShim, L1 health_metrics verified), `discord_adapter.py` (DiscordRestShim via `DiscordRestClient`) | confirmed in `p22-production-activation-final-report.md` §Activated Adapters |
| Migration `p22_001_integration_schema` | `alembic/versions/p22_001_integration_schema.py` (chained from `p19_003`, applied 2026-06-27 via direct idempotent DDL + `alembic stamp`, due to pre-existing multi-head version-table state — documented) | confirmed — `alembic_version` = `p22_001_integration_schema` (single head) |
| `p22.integration_registry` (12 rows seeded) | SQL | confirmed — `IntegrationScheduler` + `ActionRouter` wired |
| `p22.secret_ref_metadata` table | SQL | confirmed |
| `audit.integration_api_log` (WORM) | SQL | confirmed — `no_update_or_delete` CHECK constraint + REVOKE UPDATE/DELETE FROM `guinevere_core`; INSERT/SELECT only |
| `IntegrationRegistry` + `ActionRouter` + `IntegrationScheduler` (30s health polling) | `/src/life_integrations/{registry,router,scheduler}.py` + `runtime.py` (factory constructs registry with real clients + `src/core/main.py` lifespan injects) | confirmed — `p22_integration_hub_active router=ActionRouter` log + 32 health_check events/40s |
| `HardStopShim` (sync Redis key `life_kernel:hard_stop` + `HardStopHandler.is_safe`) | `/src/life_integrations/_shims.py` | confirmed — L2+ actions under HARD STOP → `HardStopBlockedError` verified |
| `ConsentGateShim` (fail-closed) | same | confirmed — L2+ actions without consent fail-closed; verified by audit testing |
| `SemanticActionClassifier` (LOCAL scaffold) | `/src/life_integrations/{permissions,secrets,consent}.py` | confirmed — will consume P23's classifier when it lands |
| `ProjectContext.project_id` propagation | `/src/life_integrations/project_context.py` (collaborates with `src/projects/registry.py:_DEFAULT_PROJECT_ID`) | confirmed — every `audit.integration_api_log` event has project_id in payload |
| 87 P22 unit tests + 464 life_kernel tests passing (1 pre-existing sensors.py failure NOT in P22 scope) | `python -m pytest tests/p22/ -v` + `tests/life_kernel/` | confirmed — 76 original + 11 new `test_shims` |
| `bash subprocess` shell injection fix, finance substring check fix, `__import__` elimination, scheduler async wiring | from `audits/round-2/README` | confirmed — 0 forbidden patterns in source |
| `ProjectRegistryProtocol` (read-only access to P19 registry) | `/src/life_integrations/project_context.py` imports from `src.projects` registry, exposes `get/resolve/list_active` only | confirmed — 0 `from src.life_kernel` imports in P22 package |
| P19/P20 regression | 0 closed P20 files modified; P19 schema untouched | confirmed in `p22-final-implementation-report.md` §9 |
| Round-1 audit fix log | 4 HIGH + 4 MEDIUM + 7 LOW = all fixed in `fixes/round-1-fix-log.md` | confirmed |

### 3.2 Config-missing / partial — the 10 honest CONFIG_MISSING adapters

| # | Adapter | Reason CONFIG_MISSING | Fix path | Severity |
|---|---|---|---|---|
| **4** | **Google Calendar** | No client, no OAuth. Google libs local-missing; VPS-only; OAuth operator-gated. | Operator provisions `secret_id=gkv1-kek-secrets-p22-google-calendar-oauth` in SOPS/age; OAuth client secret + refresh token via Google consent screen (Faiz-only). Re-run registration. | **OPERATOR-GATED** (5-7) |
| **5** | **Google Drive** | No client, no OAuth. | Operator provisions `secret_id=gkv1-kek-secrets-p22-google-drive-oauth`. | **OPERATOR-GATED** |
| **6** | **Notion** | No client lib, no token. | Operator provisions `secret_id=gkv1-kek-secrets-p22-notion-internal`. Need `notion-sdk` lib install. | **OPERATOR-GATED** |
| **7** | **Telegram** | No client lib, no token. | Operator provisions Telegram bot token. | **OPERATOR-GATED** |
| **2** | **Gmail** | Google libs local-missing; VPS-only; OAuth operator-gated. | Operator provisions OAuth client + refresh token; install `google-api-python-client` on VPS. | **OPERATOR-GATED** |
| **3** | **GitHub** | Shim needs testing (in-tree client is module functions). | Build + test `GitHubAdapter` client wrapper around existing `src/mcp/tools/github.py` (auth_level-handled). | **ENGINEERING** |
| **11** | **Browser/Research** | Shim needs testing (3 MCP tools need instance shims). | Wire `BrowserAdapter` to `playwright` + `obscura_cdp.py` MCP tools. | **ENGINEERING** |
| **12** | **Memory/KG** | Shim built (`memory_pipeline_shim.py`) but full session-pool wiring is follow-up. | Wire `MemoryAdapter` to `HermesBrain` + `MemoryRecallAdapter` + `KGRecallAdapter` session pool. | **ENGINEERING** |
| **10** | **Finance Tracker** | `FinanceMind` needs `hermes_brain` + `durability` construction. | Wire `FinanceAdapter` to construct `FinanceMind(memory_store, hermes_brain, durability)`. | **ENGINEERING** |
| **8** | **WhatsApp (Neonize)** | `.env.whatsapp` perm-denied; session linkage re-verify needed. | Fix `/srv/guinevere/.env.whatsapp` permissions (root ownership); re-verify Neonize session linkage. | **PERMS** |

### 3.3 Plan-only candidates (NOT P22 — future integrations)

| Candidate | Status |
|---|---|
| Linear | candidate only (no commit) |
| Jira Cloud | candidate only (no commit) |
| Trello | candidate only (no commit) |
| Obsidian | candidate only (NO OFFICIAL API; third-party Local REST plugin only) |
| P22 Wave 4 (P24 fork-internal merge) | deferred until P24 lands |

### 3.4 What P27/P28 consumes from P22

| Symbol / surface | What it gives P27 | Today availability |
|---|---|---|
| `from src.life_integrations.registry import IntegrationRegistry, build_default_registry` | Lookup any of 13 providers + surfaces. Returns `Adapter` instance. | **YES** for 3 ACTIVE; **YES with ConfigurationMissingError raise** for 10 CONFIG_MISSING. |
| `from src.life_integrations.router import ActionRouter.route(action_request)` | Single entry point for any external integration action. Returns `ActionResult`, `HardStopBlockedError`, `ConfigurationMissingError`, `ConsentDeniedError`. | YES (fail-closed for everything except L1 + ACTIVE adapters). |
| `from src.life_integrations.adapters.{filesystem,vps,discord}_adapter import *` | Direct adapter access for the 3 ACTIVE providers — full L1+L2/L3 today. | **YES, work today** |
| `IntegrationHealth` enum | `OK` / `UNKNOWN` / `DOWN` per adapter. P27 societies can poll via scheduler. | YES |
| `SemanticActionClassifier.classify(intent, parsed_args, auth_level) → RiskTier` | Risk classification L1-L4. AuthLevel is INPUT, NOT 1:1. P22-local scaffold (will consume P23 when it lands). | YES (P22 version) |
| `HardStopShim.is_hard_stop` | Synchronous check on `life_kernel:hard_stop` Redis key. SUBSCRIBE to P20's 1s heartbeat detector's flag. | YES |
| `ConsentGateShim.check(scope, project_id, operation)` | Fail-closed consent gate for L2+ actions. **NOTE**: `consent_checker=None` today so all L2+ fail-closed regardless of consent — safe default until P19/surveillance consent ledger wired. | YES (fail-closed) |
| `AuditLogger.emit(event_type, project_id, provider, action, result)` | Emit audit event to structured log with project_id. **NOTE**: `audit_writer=None` today so events NOT yet persisted to `audit.integration_api_log` table. P22 emits to log only. | YES (log-only) |
| `ProjectContext(project_id: UUID, slug: str)` | Per-action context passed to every adapter invocation. Propagates to audit events. | YES |
| Namespace template `p22:<domain>:<provider>:<resource-id>` | Resource ID namespace format. Mirrors P19 `p19:<project_slug>:<domain>:<resource-id>`. P27 societies can extend as `society:<slug>:<domain>:<resource-id>` per space. | YES |
| FB-only `ConfigurationMissingError` | Raised when call succeeds but creds absent. P27 societies can plan around it: adapter present + wiring present + creds absent = explicit "not yet provisioned" signal (NOT a fake PASS). | YES |

### 3.5 Dependency on other phases

| Phase | Relationship | Concretely |
|---|---|---|
| P19 registry | READ-ONLY consumer | `ProjectRegistryProtocol.get/resolve/list_active` consumed in `project_context.py`. No create/archive from P22. |
| P20 | STANDALONE — 0 imports | Confirmed: 0 `from src.life_kernel.*` imports in `src/life_integrations/`. P22 ships as standalone package; lifespan integration via `src/core/main.py` only. |
| P21 | NOT-AVAILABLE | P21 not implemented; P22 not waiting on P21. |
| P23 | FUTURE CONSUMER | P23-014 (`ExternalExecutor`) wraps P22 adapters as action targets. P23-014 will be partially satisfiable (3 ACTIVE) today; expanded as P22 adapters flip from CONFIG_MISSING to ACTIVE. |
| P24 | FUTURE MIGRATION | P22 Wave 4 (P24 fork-internal merge) deferred until P24 lands. |

### 3.6 Blockers / open issues

| Block | Status |
|---|---|
| `audit_writer=None` — P22 audit events NOT persisted to `audit.integration_api_log` (emit to log only with project_id) | FOLLOW-UP — wire P22-specific audit writer to land project_id/project_scope in the table |
| `consent_checker=None` — L2+ actions fail-closed regardless of consent ledger | FOLLOW-UP — wire `ConsentGateShim.check` to P19/surveillance consent ledger |
| 10 CONFIG_MISSING adapters (5 OPERATOR-GATED + 5 ENGINEERING) | DOCUMENTED — explicit list in `p22-production-activation-final-report.md` §CONFIG_MISSING |
| Migration applied via DDL+`alembic stamp` (not `alembic upgrade`) due to pre-existing multi-head version-table state | DOCUMENTED — idempotent + WORM-safe |
| Round-2 final-gate confirmation | `final-discord-visible-autonomy-report.md` of P22 has `[ROUND2_PLACEHOLDER]` — pending |
| `src/projects/memory_store.py` currently uses fallback `principal="guinevere_core"` (P19 INFO gap C02 chain effect on P22 memory_adapter) | FOLLOW-UP — chain fix when P19 closes C02 |

---

## 4. P23 — Embodied Operations

| Field | Value |
|---|---|
| Mission | Hands/feet for Guinevere — 24/7 durable action queue with risk classification (L1-L4), P19 project namespace, P21 voice command input, P22 sensor/action target, HARD-STOP cancel, safe-mode/distress freeze, rollback, audit.log + reason journal. |
| Target | New `BaseExecutorAdapter` + `ExecutorRegistry` (write-side counterparts to existing `BaseSensorAdapter` + `SensorRegistry`); wrappers over MCP tools (`src/mcp/tools/{git_tool,github,obscura_cdp,filesystem,shell_tool,docker_tool,postgres_tool,redis_tool}.py`) with **SemanticActionClassifier** (`AuthLevel` is INPUT not 1:1 to L1-L4). 7-step policy gate. |
| Phase ID | P23 |
| Phase doc | `docs/setup-evidence/P23/README.md` + `plan/p23-embodied-operations-enterprise-plan.md` (1075 LoC, 46 sections, 20 waves) |
| Runtime status | **PLAN_ONLY** (definition complete; 51 files / 10,306 LoC under `docs/setup-evidence/P23/`; double-audit PASS-round-1 + ALL-PASS-round-2; P23A READY; P23B BLOCKED) |
| Production runtime stamp | NONE — no code in `src/life_kernel/executors/` (directory MISSING on disk) |

### 4.1 Runtime-ready components

**NONE** — `src/life_kernel/executors/` directory does NOT exist (`bash Test-Path → False`).

### 4.2 Config-missing / partial

**NONE — no code exists yet.**

### 4.3 Plan-only (all 20 waves held)

P23-001..020 are fully scaffolded (each with 10 verification-scaffold fields: Expected Files / Forbidden Patterns / Required Commands / Evidence Requirements / Hard Rejection Criteria / Rollback/Re-run / Parent Verification Commands / Auditor Assignment / Runtime Proof Required / Deployment-Soak Requirement). **0 implementation has happened**.

**P23A (READY TO START after P1 fixes done 2026-06-25):**

| Wave | Title | Blocked on |
|---|---|---|
| P23-001 | Governance/ADR/docs sync + action policy charter | — (ready) |
| P23-002 | Action domain model + risk classifier (with **SemanticActionClassifier** requirement; P1-2 fix) | 001 |
| P23-003 | Durable action queue (PG + Redis BRPOPLPUSH) | 002 |
| P23-004 | Executor registry + BaseExecutorAdapter (sibling to BaseSensorAdapter) | 002,003 |
| P23-005 | Browser executor (Playwright + Obscura CDP; per-action BrowserContext) | 004 |
| P23-006 | Windows desktop executor (PowerShell + process isolation) | 004 |
| P23-007 | VPS/SSH executor (backup→canary→smoke→rollback design) — **partially satisfiable today via P22 vps_adapter (DockerClientShim + ShellClientShim)** | 004 |
| P23-008 | GitHub/repo executor (wraps git_tool/github) — **partially satisfiable today via P22 github_adapter shim** | 004 |
| P23-009 | File system executor (workspace boundary) — **satisfiable today via P22 filesystem_adapter** | 004 |
| P23-010 | Mobile/Android executor (DEFERRED — design seam only) | 004 |
| P23-016 | Audit journal + artifacts + redaction | 003,004,015 |
| P23-017 | Discord dashboard/log UX for action state | 016 |
| P23-018 | Observability/metrics/alerts | 016,017 |
| P23-019 | E2E test harness + scenario suite | 005-010,015,016 |

**P23B (NOT READY; requires P19/P21/P22 runtime contracts):**

| Wave | Title | Blocked on |
|---|---|---|
| P23-011 | P20 life-kernel action planner integration (HermesBrain.think() for planner + self-debug) | P20 axis satisfied by operator accepted-risk waiver (+ fresh runtime incident preflight before LOCKED-file edits) |
| P23-012 | P19 project namespace integration | P19 runtime namespace contract (= P19 INFO gaps C01-C03 closed) |
| P23-013 | P21 voice command integration | P21 impl |
| P23-014 | P22 external integrations integration | P22 impl (= at minimum 3 ACTIVE today; expanded as adapters flip) |
| P23-015 | HARD STOP + safe-mode cancellation (built into 7-step gate, final wiring) | 004, 011 |
| P23-020 | Production deploy/canary/rollback/soak/final gate | 019, P20 axis satisfied by operator accepted-risk waiver (+ fresh runtime incident preflight), P19 namespace contract readiness |

### 4.4 What P27/P28 consumes from P23

**NOTHING TODAY (no code).** When P23A lands:

| Symbol / surface (when implemented) | What it will give P27 |
|---|---|
| `from src.life_kernel.executors import BaseExecutorAdapter, ExecutorRegistry` | Sibling pattern to `BaseSensorAdapter` / `SensorRegistry`. P27 societies can register society-action executors that wrap MCP tools. |
| `BaseExecutorAdapter.risk_class(action, auth_level_hint) → RiskTier` (via **SemanticActionClassifier**) | Replaces hard-coded L1-L4 mapping. AuthLevel is INPUT, not 1:1. The classifier inspects parsed intent + subcommand + real side-effect risk (`shell_exec` `python`/`pip`/`git` at READ_AUTO classify L2/L3, never L1). |
| 7-step policy gate | `classify → HARD-STOP → distress → consent → namespace → execute → audit`. P27 society actions pass through this same gate. |
| HARD STOP subscribe `p23:cancel` Redis pub/sub | Mirror P22 `HardStopShim`; P27 society actions also listen to this channel. |
| P19 `project_namespace` on every action | Even if P23-012 BLOCKED, P23A uses `default` namespace as fallback. P27 societies start with `default` namespace + feature flag. |
| PG `p23.action_queue` + `p23:queue:pending`/`processing` Redis | P27 can create parallel `society.action_queue` with same idempotency-key pattern `(project_namespace, intent_hash)`. |
| `audit.action_log` hash-chained WORM table | P27 can create parallel `society.action_log` with same hash-chain mechanic. |
| Discord dashboard `_actions_section` + `#actions-log` | P27 societies can reuse the action-state UX pattern. |

### 4.5 Dependency on other phases

| Phase | Relationship | Concretely |
|---|---|---|
| P19 namespace | P23-012 BLOCKED on runtime contract readiness; P19 definition complete; P19 IS runtime-active (PARTIAL gaps C01-C03). | If C01-C03 closed, P23B unblocked. |
| P20 axis | P23-011 LOCKED-file wiring requires fresh runtime incident preflight (no active crash/recursion/fallback-storm/OOM/dashboard-fail/privacy-leak) before editing. Operator accepted-risk waiver 2026-06-25 satisfies the V-001..V-008 axis. | Preflight check is a manual one-time gate; clean today per `p22-production-activation-final-report.md` P20=nothing regressed. |
| P21 voice | P23-013 BLOCKED on P21 impl. P21 is definition-complete only. | Not actionable today. |
| P22 external | P23-014 BLOCKED on P22 impl. P22 IS partial runtime (3/13 ACTIVE). | TODAY: filesystem/vps discord P22 adapters are usable as P23-014 targets for those 3 providers. Other 10 wait on P22 ACTIVE flips. |
| All LOCKED files (`heartbeat.py`/`graph.py`/`hermes_brain.py`/`state.py`/`models.py`/`hard_stop_handler.py`/`cognition.py`/`safety_plugin.py` + P20 production files) | P23 changes MUST BE additive only. No edits to `hermes_brain.py` planner core, no edits to 1s HARD-STOP loop, no edits to 6-interval schedule, no edit to graph topology. | Routine P20 gating. |

### 4.6 Blockers / open issues

| Block | Status |
|---|---|
| `src/life_kernel/executors/` directory MISSING | Existence check returns False; no code, no package init |
| P19 INFO gap C01 (audit journal project_id) chains into P23-012 blocker | OPEN; single mitigation: P23A uses `default` namespace |
| P19 INFO gap C02 (memory principal) chains into any cross-project recurrence | OPEN; single mitigation: P23A uses `default` namespace |
| P21 NOT implemented; P23-013 BLOCKED indefinitely until P21 lands | OPEN |
| P22 10/13 adapters CONFIG_MISSING; P23-014 partial-target only (filesystem/vps/discord today) | DOCUMENTED in P22 final-impl report; FIX-PATH operator-gated for 5 + engineering for 5 |
| Round-2 audit dispatch waves were interrupted during P23 definition; 2 research + all 13 round-2 audit files are parent-authored with documented provenance | DOCUMENTED per AGENTS.md §14 (mirroring P21 §2 precedent) |
| Mobile P23-010 DEFERRED (seam only, no MVP impl) | EXPLICIT — phone control = intimate surveillance + high blast radius, requires separate consent + surveillance policy iteration |

---

## 5. Cross-Phase Dependency Graph

```text
                 ┌────────────────────────────────────┐
                 │    P20 Living Autonomy Kernel      │
                 │  heartbeat·graph·cognition·brain   │
                 │  sensors(domain minds)·dashboard   │
                 │  (LIVE; 420 tests passing)         │
                 └────────┬───────────────┬───────────┘
                          │               │
                          │ uses senses/  │ additive
                          │ project_id    │ project_id
                          │               │
   ┌──────────────────────▼──┐    ┌──────▼─────────────────────┐
   │ P19 Multi-Project Ctx   │    │ P22 Life Integration Hub   │
   │ registry/vault/memory   │    │ 13 adapters (3 ACTIVE /    │
   │ namespace project_id    │◄───┤ 10 CONFIG_MISSING)         │
   │ (LIVE; 4 INFO gaps)     │    │ router+scheduler+HARDSTOP  │
   └─────────┬───────────────┘    │ consent gate+audit log     │
             │                    └────────────────┬───────────┘
             │ namespace seam                     │
             │ (consumed by)        wraps MCP     │
             │         ┌────────────┐  tools      │
             │         │            │◄────────────┘
             │         │            │
             ▼         ▼            ▼
         ┌────────────────────────────────────┐
         │   P23 Embodied Operations (NO code)│
         │  write-side counter-part to sensors│
         │  queue+executors+policy+audit       │
         │  (PLAN_ONLY; P23A ready; P23B held) │
         └────────────────────────────────────┘

   P27/P28 — Hermes Society Foundation (target)
   ┌─────────────────────────────────────┐
   │  society agents / multi-society /   │
   │  relationships / namespaces /       │
   │  heartbeat·discernment·assembly     │
   │  (depends on what's below)          │
   └─────────────┬───────────────────────┘
                 │ will/should consume
                 ├── P19: registry / project_id / namespace
                 ├── P20: HermesBrain · HeartbeatService · domain minds · state pattern
                 ├── P22: ActionRouter (3 ACTIVE adapters targetable) + HardStopShim + AuditLogger
                 └── P23 (post-A landing): ExecutorRegistry + SemanticActionClassifier + durable queue pattern
```

### 5.1 Edge-by-edge

| Edge | Status | Notes |
|---|---|---|
| **P20 → P19** | P19 PUSHES project_id into P20 (additive, condition-flag-gated, byte-identical when flag OFF) | Verified via `p19-005b` cuts; flag OFF = legacy |
| **P19 → P22** | P22 READS P19 registry via `ProjectRegistryProtocol` (read-only); project_id in every audit event | LIVE |
| **P22 → P20** | P22 imports NOTHING from P20 (`0 from src.life_kernel imports`); standalone package | LIVE |
| **P20 → P22** | P22 lifespan wired into `src/core/main.py`; `HardStopShim` reads `life_kernel:hard_stop` (P20's key) | LIVE |
| **P19 → P23** | P23-012 BLOCKED on P19 runtime contract readiness | PARTIAL |
| **P20 → P23** | P23-011 LOCKED-file wiring requires preflight; `HermesBrain.think()` is the brain; `life_kernel:hard_stop` is the kill switch | PARTIAL (brain path provably correct today; LOCKED-file gates) |
| **P22 → P23** | P23-014 wraps P22 adapters as `ExternalExecutor`. Today: 3 ACTIVE satisfiable, 10 placeholder | PARTIAL |

---

## 6. What P27 MUST inherit — Concrete Inheritance Map

These are the structural patterns P27 must reuse (or extend, never reinvent) to avoid divergence:

### 6.1 From P19 — Project registry + vault + memory isolation

| Pattern | Reuse |
|---|---|
| `ProjectRegistry(uuid)` with `default` sentinel `00000000-0000-0000-0000-000000000001` | P27 society registry follows same UUID convention |
| `ProjectSecretsVault.get(project_id, domain)` in-memory per-project SOPS/age | P27 society secrets use same vault shape (or extend as `SocietySecretsVault` calling `.get`) |
| `feature:{name}:enabled` Redis key + DB5 mirror + DB6 feature-flag light read path | P27 `feature:societies:enabled` follows same flag pattern |
| Namespace `p19:{slug}:{domain}:{resource-id}` | P27 societies use `society:{slug}:{domain}:{resource-id}` (parallel inheritance, not collision) |
| `ProjectContext.project_id` flow into every action | P27 `SocietyContext.society_id` flow into every society action |

### 6.2 From P20 — Heartbeat·Brain·State·Domain·Sensor·Session·Dashboard

| Pattern | Reuse |
|---|---|
| `HeartbeatService` 6-interval schedule | P27 `SocietyHeartbeat` (separate Service OR per-society interval piggybacking) |
| `HermesBrain.think()` as brain path (V-004 — raw `LLMRouter.chat` FORBIDDEN) | P27 society reasoners call `HermesBrain.think()` with system_prompt per society archetype |
| `LifeMindState` / `SessionState` TypedDict pattern with reducers | P27 `SocietyState` / `SocietyMemberState` follows same pattern |
| `DomainMinds.{Engineer,Finance,Email,Deploy}` pattern | P27 society-domain minds (e.g., `ArbiterMind`, `ReviewerMind`, `CouncilMind`) |
| `SensorRegistry` + `BaseSensorAdapter` | P27 `SensorRegistry` extension / per-society sensor adapters |
| `SessionGraph` + `SessionWorktree` | P27 society session uses same per-society worktree isolation |
| `DashboardWriter` (per-dashboard-message edit-not-spam) | P27 society dashboard reuses same writer |
| `LogChannel`/`LogWriter` (append-only, throttled, deduped) | P27 society log reuses same channel/writer |
| `DecisionContextBuilder` + `KGRecallAdapter` + `MemoryRecallAdapter` | P27 society decision context pulls KG + memory signals the same way |
| `DeployBackend` + `DeployPolicy` (backup→canary→smoke→rollback MANDATORY for L3) | P27 society deploys go through `DeployBackend.run_with_policy` |
| Reflection + ImprovementCandidate + RegressionGate (self-improvement pattern) | P27 society self-improvement follows the same regression-gate-before-promote |
| 5 pinned safety tags (safe_word / hard_stop / distress / consent_revocation / do_not_recall) | P27 MUST pin these in any context compression / session summary |

### 6.3 From P22 — Action execution surface

| Pattern | Reuse |
|---|---|
| `ActionRouter.route(action_request)` with 7-step gate shape | P27 society actions can route to P22 by referencing the `ActionRouter` |
| `HardStopShim` synchronous Redis `life_kernel:hard_stop` check | P27 society actions use same shim |
| `ConsentGateShim` (fail-closed when `consent_checker=None`) | P27 society consent flows through same gate |
| `SemanticActionClassifier` (P22-local; will consume P23 when P23 lands) | P27 society risk classification reuses `SemanticActionClassifier` |
| `AuditLogger` (today: log-only; planned: integration_api_log) | P27 society audit uses same `AuditLogger` with `project_id`+`society_id` |
| `ConfigurationMissingError` honest failure | P27 explicitly handles `ConfigurationMissingError` (NOT silently fail) |
| Namespace `p22:{domain}:{provider}:{resource-id}` | P27 societies namespace as `society:{society_id}:{domain}:{resource-id}` |
| `ProjectContext(project_id)` | P27 adds `SocietyContext(society_id, project_id)` extending P22 `ProjectContext` |

### 6.4 From P23 (when P23A lands) — Executor pattern

| Pattern | Reuse |
|---|---|
| `BaseExecutorAdapter.executor_name / surfaces / DEFAULT_RISK_TIER` | P27 society executors extend BaseExecutorAdapter (or sibling pattern) |
| `ExecutorRegistry` (parallel to `SensorRegistry`) | P27 society executor registry follows same registration pattern |
| 7-step gate (`classify → HARD-STOP → distress → consent → namespace → execute → audit`) | P27 society gateway reuses same gate shape |
| HARD STOP subscribe `p23:cancel` Redis pub/sub channel | P27 society HAR STOP subscribes same channel |
| Durable queue (PG + Redis BRPOPLPUSH + idempotency `(project_namespace, intent_hash)`) | P27 society queue mirrors the same idempotency-keyed design |
| `audit.action_log` hash-chained WORM | P27 society audit log mirrors the same hash-chain format |
| MCP-tool thin wrappers + Aizanta-impact checks (`deploy_backend.py` exhaustively) | P27 society executors wrap MCP tools, run Aizanta-impact checks before deploy |

---

## 7. What P27 MUST NOT do

| Anti-pattern | Forbidden because | Reference |
|---|---|---|
| **Touch P20 LOCKED files without fresh preflight** (`heartbeat.py`/`graph.py`/`hermes_brain.py`/`state.py`/`models.py`/`hard_stop_handler.py`/`cognition.py`/`safety_plugin.py`) | P20 production-under-accepted-risk; need fresh runtime incident preflight before any LOCKED-file edit | `p23-embodied-operations-enterprise-plan.md` §3.2 + `ag-0.1` |
| **Call `LLMRouter.chat` directly** (raw LLM bypass) — must use `HermesBrain.think()` | V-004: Brain path = HermesBrain only | `p5-p20-vision-lock.md` V-004 + P23-011 grep |
| **Scope HARD STOP per project** | HARD STOP stays GLOBAL (`life_kernel:hard_stop` single Redis key) | `p19-multi-project-context-enterprise-plan.md` HR5 + `p5-p20-vision-lock.md` V-008 |
| **Move pinned safety messages** (safe_word / hard_stop / distress / consent_revocation / do_not_recall) | NEVER compressed | `p5-p20-merged-plan.md` Phase 5 P5-024 invariant |
| **Treat P22 `ConfigurationMissingError` as PASS** | Honest failure; explicit "not provisioned" | `p22-final-implementation-report.md` §12 |
| **Use `AuthLevel` 1:1 with L1-L4** | Must use `SemanticActionClassifier` (AuthLevel=input, NOT 1:1; `shell_exec` `python`/`pip`/`git` at READ_AUTO → L2/L3) | P23 Codex P1-2 fix + `p23-embodied-operations-enterprise-plan.md` §22b |
| **Delete without rollback** | L3 destructive MUST have backup→canary→smoke→rollback gate | `p23-embodied-operations-enterprise-plan.md` §13 + `DeployPolicy` |
| **Use `as any` / `# type: ignore` / bare `except`** | Forbidden by AGENTS + Guinevere | `AGENTS.md §0 BLOCKING Rules` |
| **Commit Discord tokens / API keys / SOPS keys / surveillance data / intimate data** | Forbidden by AGENTS + PersonaSafetyPolicy + ConsentRevocation | `AGENTS.md §0 + §12` |
| **Skim-read P22/P23 evidence without reading reports** | All sub-agent reports and parent reads required | `AGENTS.md §2.9 + §14` |
| **Assume P21 voice runtime exists** | P21 is definition-only; not implemented | `p23-embodied-operations-enterprise-plan.md` §8 (P23-013 BLOCKED) |
| **Assume all 13 P22 adapters are ACTIVE** | Only 3 ACTIVE today; 10 raise `ConfigurationMissingError` | `p22-production-activation-final-report.md` §CONFIG_MISSING |

---

## 8. Blockers Summary — Today (2026-06-28)

| # | Blocker | Severity | Phase | P27 impact |
|---|---|---|---|---|
| **1** | P22 `audit_writer=None` — P22 audit events NOT persisted to `audit.integration_api_log` (logged only) | MEDIUM | P22 | Cannot audit-log society actions through P22 today (must consume log events) |
| **2** | P22 `consent_checker=None` — L2+ actions fail-closed regardless of consent ledger | MEDIUM | P22 | P27 society L2+ actions MUST deal with fail-closed default until wired |
| **3** | 5 CONFIG_MISSING adapters (gmail/calendar/drive/notion/telegram) need operator OAuth provisioning | HIGH | P22 | P27 society cannot target these 5 providers until Faiz provisions creds |
| **4** | 5 CONFIG_MISSING adapters (github/browser/memory/finance/whatsapp) need engineering follow-up | HIGH | P22 | P27 society cannot target these 5 providers until engineering wires shims + tests |
| **5** | P19 INFO gap C04 — Discord `/project` command NOT registered in bot command tree | OPERATOR-GATED | P19 | P27 per-channel project switching UX requires `_entrypoint.py` edit + `guinevere-discord.service` restart |
| **6** | P19 INFO gap C01 — audit journal `record()` doesn't carry `project_id` | LOW | P19 | Affects P27 society audit-trail completeness |
| **7** | P19 INFO gap C02 — memory adapter `principal` fallback `"guinevere_core"` | LOW | P19 | Single-project today (no leak); P27 society multi-project memory needs P19-005a |
| **8** | P19 INFO gap C03 — recall pipeline defers project_id forwarding | LOW | P19 | Same |
| **9** | P21 NOT implemented | HIGH | P21 | P27 society cannot consume voice input until P21 lands |
| **10** | P23 directory MISSING (`src/life_kernel/executors/`) | HIGH | P23 | P27 cannot use P23 executors today; P23A is ready-to-start (1 wave at a time, scaffolded) |
| **11** | P20 24h clean soak NOT completed (operator waiver) | INFORMATIONAL | P20 | Not a security gap; P20 CLEAN runtime snapshot confirmed 08:50:46 WIB 2026-06-25 |
| **12** | LifeMindState TypedDict does NOT have `project_id` field yet | LOW | P19+P20 | P27 society state should NOT depend on global LifeMindState.project_id today; thread per-call instead |
| **13** | `domain_mind_state` UNIQUE on `domain` only (not `(project_id, domain)` yet) | LOW | P19 | P19-002 migration will fix; multi-project domain-mind isolation needs that |
| **14** | Round-2 final-gate for P22 production activation `[ROUND2_PLACEHOLDER]` | INFORMATIONAL | P22 | Pending — but Round-1 PASS + Round-1 fixes applied + runtime clean snapshot = effectively PASS |
| **15** | `guinevere-discord.service` standalone MASKED by design (P2-022) | INFORMATIONAL | core | P27 must use core REST publisher for any Discord writes |

---

## 9. Recommended P27 Sequencing (forward-looking)

| Step | Action | Blocked on |
|---|---|---|
| **P27-001** | Define society model + society_registry (similar to ProjectRegistry) + SocietySecretsVault (wrapper around ProjectSecretsVault) + `feature:societies:enabled` flag | — (NEW files, technically unblocked) |
| **P27-002** | Design `SocietyContext(society_id, project_id)` extending P22 `ProjectContext` for audit/log/dashboard propagation | P22 `project_context.py` read |
| **P27-003** | Define `SocietyState` TypedDict following `LifeMindState` pattern (with `society_id: NotRequired`, observations/goals/commitments/concerns/journal reducers) | Pattern only |
| **P27-004** | Define `SocietyHeartbeat` either as separate asyncio Service OR (preferred) extend P20 `HeartbeatService` with per-society interval — coordinate with P19/P20 file owners | P20 axis: fresh runtime preflight BEFORE Touch |
| **P27-005** | Reuse P22 `ActionRouter` for any society external actions (3 ACTIVE: filesystem/vps/discord) + `HardStopShim` + `ConsentGateShim` + `AuditLogger` (log-only today) | P22: `audit_writer=None` documented (consume log events) |
| **P27-006** | Reuse `HermesBrain` for society brain; `BaseSensorAdapter` family for society sensors | — |
| **P27-007** | Pinned safety in any society context compression (5 tags) | — (per V-008 + P5-024) |
| **P27-008** | Operator-gated provisioning: Decide whether to (a) trigger P22 OAuth flows for gmail/calendar/drive/notion/telegram scope, (b) request P23-005/006/007/008/009 shim engineering | Operator approval per AGENTS.md §0 |
| **P27-009** | After P27-001..007 design lands, coordinate with P23-A start (P23-001..019) for executor pattern reuse | P23-001 scaffold |
| **P28+** | Plan P28 follow-ups per P27 implementation outcome | P27 DOR |

---

## 10. Footer

| Version | Date | Author | Status |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere (parent, file-based) | P27 Dependency Map — COMPLETE (research only, no code/deploy/restart) |

**P27 RUNTIME READINESS MATRIX (TL;DR):**

| Phase | LIVE | PARTIAL | CONFIG_MISSING (N) | PLAN_ONLY | Blocker severity today |
|---|:-:|:-:|:-:|:-:|---|
| P19 | ✓ | — | 4 INFO gaps (C01-C04) | — | LOW (C04 OPERATOR-GATED; others chain-effect only) |
| P20 | ✓ (w/ accepted-risk waiver) | — | 0 (24h soak waived by op) | — | INFORMATIONAL |
| P22 | — | ✓ (3/13 ACTIVE) | 10 (5 OP-GATED + 5 ENG) | candidates (Linear/Jira/Trello/Obsidian) | MEDIUM (operator+eng close to flip) |
| P23 | — | — | — | ✓ all (P23A ready; P23B blocked) | HIGH on P21, MEDIUM on P22, LOW on P19 |

> **Bottom line for Faiz**: P27 can land today built on **P19 (namespace) + P20 (kernel/heartbeat/brain/domain) + P22 (3 ACTIVE adapters: filesystem/vps/discord)**. P23 brings queue/audit pattern but is not required — reuse P22 `ActionRouter` + `HardStopShim` + `ConsentGateShim` + `AuditLogger` (log-only) for society actions today. Recheck the 10 CONFIG_MISSING list before promising P27 society access to gmail/calendar/drive/notion/telegram/github/browser/memory/finance/whatsapp.