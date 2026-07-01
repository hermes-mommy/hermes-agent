# P27 Research: Hermes Native Runtime Inventory

**Date:** 2026-06-28
**Scope:** Inventory the Hermes Agent runtime as installed in the Guinevere repo today — language/runtime, package structure, entrypoints, extension points, Discord architecture, single-instance assumptions, multi-instance gaps, and deployment topology.
**Source-of-truth priors:** pyproject.toml; live pip listing of hermes-agent; src/life_kernel/, src/hermes/, src/discord/, src/core/main.py, src/loops/hermes_bridge.py; hermes-config/config.yaml + .env.template; systemd/*.service; P24 research files (installed-runtime-surface, extension-points, upstream-identity); P24 plan + README.

**Purpose:** Feed P27 Hermes Society Foundation. Determine whether current runtime supports multiple Hermes instances natively, OR whether P24 fork work is a prerequisite.

---

## 1. Language and Runtime

| Item | Value |
|---|---|
| Language | Python |
| requires-python | >=3.12 (pyproject.toml; strict per tool.mypy python_version=3.12) |
| Active interpreter (dev box) | Python 3.14 (C:\Users\faizz\AppData\Roaming\Python\Python314) |
| Hermes package | hermes-agent 0.15.2 (installed, not vendored) |
| Pinned dep | pyproject.toml L31: hermes-agent>=0.15 |
| Hermes file location | C:\Users\faizz\AppData\Roaming\Python\Python314\site-packages\run_agent.py (single file, 202,842 bytes) |
| Author / license | Nous Research / MIT (per p24-hermes-upstream-identity-research.md, FORKABLE) |
| Hermes runtime deps (17, transitive) | croniter, fire, httpx, jinja2, openai, prompt_toolkit, psutil, pydantic, PyJWT, python-dotenv, pyyaml, requests, rich, ruamel.yaml, tenacity, tzdata |
| Guinevere deps that matter for Hermes | langgraph>=0.2, langgraph-checkpoint-postgres>=2.0, langgraph-checkpoint-redis>=2.0, discord.py>=2.4, apscheduler>=3, sqlalchemy[asyncio]>=2, redis>=5, pydantic>=2, psycopg[binary,pool]>=3.1, httpx>=0.28, tenacity>=9, structlog>=24, prometheus-client>=0.21, mcp>=1.0, sentry-sdk[fastapi]>=2 |
| Test stack | pytest-cov>=7, pytest-asyncio>=0.23, asyncio_mode=auto, coverage fail_under=80 |
| Build | hatchling.build; wheel packages src |

**Verdict:** Python 3.12+ project. Hermes is a MIT-licensed pip dependency. Guinevere's only direct import is from run_agent import AIAgent (lazy + injectable, see §3).

---

## 2. Package Structure — fork or wrapper?

**Not a fork today.** P24 round-1 audit (p24-hermes-upstream-identity-research.md) confirms hermes-agent 0.15.2 is FORKABLE upstream (MIT, GitHub source available). P24 owner directive prefers OWNED FORK full convergence, but:

- P24 is on IMPLEMENTATION HOLD (docs/setup-evidence/P24/README.md: IMPL HOLD UNTIL MAMA NEXT AUDIT PASS/APPROVAL).
- No local fork source exists (no hermes-agent/, hermes_fork/, or overlay/ in src, hermes-config, or vps-mirror).
- P24-002 source-verification step is not yet PASSed (it gates the first internal patch design).

Today the integration is **hybrid adapter** per p24-installed-runtime-surface-inventory.md:

`
Hermes-Aware Local Code
- hermes-config/                       (Guinevere-owned bundle)
    config.yaml   (394 lines)
    .env.template (47 lines)
    SOUL.md       (persona constitution)
    hooks/        (12 shell hooks: finance, budget, consent, dnr,
                   drift, hard_stop, hybrid_guards, error_classifier,
                   budget_lua, budget_lua_extended, _hook_utils)
    plugins/      (3 in-proc: auth_overlay, guinevere_persona,
                   guinevere_safety)
- src/hermes/                          (adapter layer, NOT a fork)
    __init__.py            (deprecation pointer)
    adapter.py             (singleton get_adapter())
    _session_adapter.py    (390 LOC, wraps AIAgent, Redis DB4)
    _memory_bridge.py      (P18 conversation memory)
    safety_plugin.py       (in-process persona+safety)
- src/loops/hermes_bridge.py           (P5-023 superseded, still loads at boot)
- src/discord/hermes_conversational.py (#guinevere-chat Hermes LLM path)
- src/discord/_entrypoint.py           (GuinevereBot discord.py)
`

P24 round-1 counts (verified against current repo):

| Surface | Count |
|---|---|
| from run_agent import AIAgent direct imports | 1 (src/life_kernel/hermes_brain.py, lazy) |
| src/hermes/*.py non-cache files | 7 |
| hermes-config/hooks/*.py | 12 |
| hermes-config/plugins | 3 |
| src/hermes_plugins/ Discord command plugins | 44 |
| from hermes / import hermes framework imports | 0 |
| hermes gateway CLI invocations | 1 in TEMPLATE (systemd/hermes-gateway.service, not deployed) |

Verdict: Hybrid adapter + extension-points-only today. No source-tree fork. P24 fork-first remains a future state on hold.

---

## 3. Entry Points — how does the system start?

Guinevere is poly-service: no single main(). Production runtime is **two parallel systemd services** + shared PostgreSQL/Redis + the Hermes CLI gateway (rarely invoked).

### 3.1 FastAPI core service — guinevere-core.service

- src/core/main.py:645-649: app = FastAPI(title=Guinevere Core, version=0.1.0, lifespan=lifespan).
- systemd exec: python -m uvicorn src.core.main:app (per vps-mirror/systemd-live/guinevere-core.service).
- The lifespan function IS the actual main(): builds every long-lived singleton the kernel depends on (src/core/main.py:60-642).

Lifespan boot order (failing soft at every step):

1. Alias 9ROUTER_API_KEY from GUINEVERE_9ROUTER_API_KEY so the AIAgent provider resolver finds it before fork (main.py:20-21).
2. Sentry init (P8-012).
3. LLM metrics server on localhost:9191.
4. **Construct ONE HermesBrain** with hard-coded config: base_url=http://localhost:20128/v1, model=guinevere, provider=9router, max_iterations=5 (main.py:85-93). Stored on app.state.hermes_brain.
5. LoopManager(llm_router=None) — llm_router=None is intentional (P20/P24): ALL autonomous LLM calls go through HermesBrain.think(), NOT through LLMRouter.chat.
6. HardStopHandler wiring (F-05).
7. Start loop_manager.guardian.monitor() as guardian-monitor task.
8. APScheduler monthly cost report.
9. SurveillanceConsumer (Redis DB2 + Postgres) (RG-004).
10. KG ingestion cron at 03:30 ICT daily (P16-002).
11. P20 Living Kernel boot (main.py:209-509):
    - create_postgres_checkpointer(dsn) (AsyncPostgresSaver).
    - recall_memories + KGQueryEngine.search_entities wrapped into per-call closures -> KGRecallAdapter (p16_adapter.py) + MemoryRecallAdapter (p18_adapter.py). Both fail-soft (_degraded=True).
    - JournalWriter wired to PostgresAuditJournal schema life_kernel/audit_journal.
    - graph = create_life_mind_graph(checkpointer, hermes_brain, kg_adapter, memory_adapter, journal_writer).
    - Redis client redis://guinevere_core:***@localhost:6380/6.
    - DiscordRestClient() with DISCORD_BOT_TOKEN env -> dashboard + log channel REST publisher (no gateway).
    - If LIFE_KERNEL_DASHBOARD_CHANNEL_ID + LIFE_KERNEL_LOG_CHANNEL_ID + token present: build DashboardWriter + DiscordLogChannel; else StructlogLogChannel fallback.
    - HeartbeatService started.
    - P22 Integration Hub: build_runtime_registry + IntegrationScheduler 30s poll.
    - P19 Multi-Project Context: cognition_registry = ProjectAwareCognitionRegistry(max_active=3) — the only existing multi-instance scaffold.
12. P5-023 LoopsHermesBridge started for backwards compat (hermes_bridge_started_superseded_by_kernel).
13. Resume pending loops + boot EnvironmentMonitor.

Lifespan shutdown: heartbeat -> cognition -> DiscordRest -> life_kernel_engine.dispose() -> audit_journal engine.dispose() -> hermes_brain.dispose() -> hermes_bridge.stop() -> surveillance consumer/engine -> guardian.

### 3.2 Discord bot service — guinevere-discord.service

systemd/guinevere-discord.service:
`
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.discord._entrypoint
EnvironmentFile=/home/guinevere/code/guinevere/.env.discord
`

src/discord/_entrypoint.py:758-785:
`
async def main() -> None:
    token = os.environ.get(DISCORD_BOT_TOKEN)
    if not token: raise RuntimeError(DISCORD_BOT_TOKEN required)
    bot = GuinevereBot()
    async with bot: await bot.start(token)
`

GuinevereBot is discord.ext.commands.Bot with ONE guild hard-coded (GUILD_ID = 1_510_876_414_671_323_206). setup_hook registers ~50 wired slash commands. on_message delegates to hermes_conversational.handle_conversation for #guinevere-chat.

### 3.3 Hermes gateway service — hermes-gateway.service (TEMPLATE ONLY)

systemd/hermes-gateway.service: ExecStart=.../hermes --config .../hermes-config/config.yaml gateway.

File's own header: Repository template... VPS unit may be generated or managed by the Hermes install process... Hermes Migration Phase 7b local hardening — **no live deployment claim**.

vps-mirror/systemd-live/hermes-gateway.service alternates: hermes gateway run --accept-hooks.

Verdict: **ONE** active FastAPI process, **ONE** active Discord bot, **ONE** Hermes gateway TEMPLATE (not deployed). No multiple parallel Guinevere stacks.

### 3.4 Other top-level services

11+ guinevere-*.service files: gmail, x-poster, mcp, loops, scheduler, surveillance, obscura, wearable-sync, wearable-analysis, monitoring, shadow-monitor, prune-weekly@ (cron template), backup@ (cron template). All single-instance templates.

### 3.5 Docker

- Dockerfile.sandbox only.
- docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml (P2 history).
- **No production Docker.** Systemd only.

---

## 4. Extension Points — how can new agents/instances be added?

Per p24-extension-points-hooks-plugins-research.md (verified against current hermes-config/config.yaml): **EXTENSION-ONLY VIABLE.** Guinevere touches NO Hermes source. Full extension surface:

| Mechanism | Count | Type |
|---|---|---|
| config.yaml top-level sections | 9 | declarative (discord, model, providers, fallback_providers, agent, memory, hooks, mcp_servers, cron; plus observability, approval, audit, auth_matrix) |
| Distinct lifecycle HOOK EVENTS | **17** | event-driven (pre_llm_call, post_llm_call, pre_tool_call, post_tool_call, transform_llm_output, transform_tool_result, transform_terminal_output, on_session_start, on_session_end, on_session_finalize, on_session_reset, pre_gateway_dispatch, pre_api_request, post_api_request, pre_approval_request, post_approval_response, subagent_stop) |
| Shell hook scripts | 12 | external command |
| In-process plugin manifests | 3 | register(ctx) API (auth_overlay, guinevere_persona, guinevere_safety) |
| MCP server registrations | 2 declared (1 active) | process spawn |
| Cron entries | 8 | declarative schedule |
| Plugin manifest shapes | 2 | plugin.yaml + manifest.yaml |
| **Total distinct extension points** | **~40** | mixed |

Per-instance customisation at the AIAgent constructor level (src/life_kernel/hermes_brain.py:230-242):
`
AIAgent(
    base_url=...,
    model=...,
    provider=...,
    api_key=...,
    skip_memory=False,         # ENABLE memory
    skip_context_files=False,  # ENABLE kernel world context
    quiet_mode=True,
    max_iterations=5,
    enabled_toolsets=[core, web],
    disabled_toolsets=[dangerous, system],
)
`

HermesBrainConfig(base_url, model, provider, api_key, max_iterations=5) is a frozen dataclass — one config -> one instance.

Plus an injection point already exists via agent_factory: Callable[[dict], Any] | None. Today it's used to inject MagicMock for tests; the same signature would accept any AIAgent subclass/wrapper — multi-instance customisation is a 1-line constructor change away for the brain layer.

---

## 5. Discord Bot Architecture

| Item | Value |
|---|---|
| Library | discord.py>=2.4 |
| Bot class | GuinevereBot(discord.ext.commands.Bot) (src/discord/_entrypoint.py:86) |
| Token source | os.environ[DISCORD_BOT_TOKEN] ONLY (RuntimeError if absent) |
| Token policy | Never logged / persisted / written to state (src/life_kernel/discord_rest_client.py:18-21) |
| Guild | Hardcoded GUILD_ID = 1_510_876_414_671_323_206 (_entrypoint.py:48) |
| Hardcoded greeting channel | #guinevere-status (_startup.py:339) |
| Hermes chat channel | Hardcoded GUINEVERE_CHAT_CHANNEL_ID = 1_510_914_600_777_023_659 (#guinevere-chat, hermes_conversational.py:51) |
| hermes-config/config.yaml allowed_channels | #guinevere-chat, #finance |
| hermes-config/config.yaml allowed_users | 1146639950654214264 (Faiz — single user) |
| Slash commands registered | ~50 wired (RG-010..014 + Hermes Phase 1 + P12 + P14 + P18 + P5 + P19); 0 stubs as of report date |
| Bot intents | get_intents() (src/discord/_intents.py) |
| HARD STOP listener | _on_message_listener via @bot.listen (fires before on_message) |
| Conversational handler | src/discord/hermes_conversational.py — Hermes-native AIAgent path via get_adapter() |
| Module-level singletons (hermes_conversational.py lines 87-99) | _cost_tracker, _embedding_service, _memory_bridge, _rate_limit_redis |
| HermesSessionAdapter singleton | from src.hermes.adapter import get_adapter() returns the cached adapter (src/hermes/_session_adapter.py). Per-user AIAgent cache in-memory. Redis DB4: 2hr TTL, 20-turn |
| Shadow bot (second bot, same code) | DISCORD_SHADOW_BOT_TOKEN + DISCORD_SHADOW_CHANNEL_ID. ShadowPipeline (src/discord/shadow_pipeline.py) runs in parallel for Hermes shadow testing — does NOT serve production. SHADOW_ENABLED=false by default. |
| Bot-update topology | guinevere-discord.service (one), NOT hermes-gateway.service (one, template-only) |

**Multi-bot precedent:** ShadowPipeline already runs an additional bot off the same code with a different (DISCORD_SHADOW_BOT_TOKEN, DISCORD_SHADOW_CHANNEL_ID). This is the architectural pattern P27 could reuse — **but only if each Hermes instance is assigned its own (bot_token, channel_id) tuple + its own chat handler entry**. Today there is exactly ONE such tuple.

---

## 6. Single-Instance Assumptions in Code

The following code-shape constraints limit native multi-instance operation. Each is an explicit single-instance anchor:

### 6.1 Brain/LLM singletons

| Anchor | Where | What it pins |
|---|---|---|
| app.state.hermes_brain | src/core/main.py:93-94, 446 | ONE HermesBrain built once at lifespan; hardcoded base_url=http://localhost:20128/v1, model=guinevere, provider=9router |
| HermesBrain(llm_config=brain_config) kwargs | src/core/main.py:85-93 | literal-typed, not driven by env or DB row |
| _default_agent_factory | src/life_kernel/hermes_brain.py:95-111 | global, returns AIAgent(**kwargs) from run_agent |
| HermesSessionAdapter.get_adapter() | src/hermes/adapter.py + _session_adapter.py:30 | ONE cached adapter; per-user AIAgent cache but ONE bot/policy context |

### 6.2 Discord / interaction singletons

| Anchor | Where | What it pins |
|---|---|---|
| _entrypoint.GUILD_ID | src/discord/_entrypoint.py:48 | one guild snowflake |
| main() reads DISCORD_BOT_TOKEN | src/discord/_entrypoint.py:764-768 | one token |
| GuinevereBot singleton | src/discord/_entrypoint.py:758-785 | one bot process per service |
| _memory_bridge module singleton | src/discord/hermes_conversational.py:97-99, 131-139 | shared across all chat |
| _cost_tracker module singleton | src/discord/hermes_conversational.py:88-89, 101-108 | shared across all chat |
| _embedding_service module singleton | src/discord/hermes_conversational.py:94-95, 111-118 | shared across all chat |
| _rate_limit_redis module singleton | src/discord/hermes_conversational.py:91-92, 142-161 | one Redis DB0 client |
| _get_hermes() -> get_adapter() | src/discord/hermes_conversational.py:164-178 | ONE Hermes adapter for the chat channel |
| GUINEVERE_CHAT_CHANNEL_ID | src/discord/hermes_conversational.py:51 | one chat channel |
| DiscordRestClient._token | src/life_kernel/discord_rest_client.py:85-86 | one token, one httpx client shared across DashboardWriter + LogChannel |

### 6.3 Graph / state singletons

| Anchor | Where | What it pins |
|---|---|---|
| ONE compiled life_mind_graph | src/core/main.py:385-398 | passed to HeartbeatService + BackgroundCognition |
| ONE LoopManager(llm_router=None) | src/core/main.py:103-104 | global loop stack |
| ONE LoopGuardian | src/core/main.py:115-119 | global guardian task |
| ONE HardStopHandler | src/core/main.py:107-110 | global HARD STOP sink |
| ONE Redis client for kernel | src/core/main.py:399-403 | redis://guinevere_core:***@localhost:6380/6 |
| ONE PostgreSQL checkpointer DSN | src/core/main.py:222-229 | one DSN |
| ONE life_mind_graph import surface | src/life_kernel/__init__.py:17 | create_life_mind_graph is the only factory |

### 6.4 Inferred / concurrency-assumed shapes

| Anchor | Where | What it pins |
|---|---|---|
| new_instance_per_invocation: true | hermes-config/config.yaml:92 | comment: AIAgent is NOT thread-safe; per-call AIAgent creation is the current contract, not process-level martialling |
| _make_stub_callback uses phase int | src/discord/_entrypoint.py:60-80 | phase int is single-instance metadata |
| asyncio.Queue for serialized graph writes | src/life_kernel/cognition.py:69, 207-234 | one queue, one write task per BackgroundCognition |
| feature:projects:enabled | src/life_kernel/cognition.py:435-446; src/life_kernel/heartbeat.py:149-172 | single Redis flag gating multi-project; max_active=3 cap (P19) |

### 6.5 P19 — only existing multi-instance scaffold in life_kernel

This is what is already in place for more-than-one-agent at the kernel layer (NOT more-than-one-Hermes):

| Component | File | What it does |
|---|---|---|
| LifeMindState.project_id (NotRequired) | src/life_kernel/state.py:265-272 | per-project state namespace |
| ProjectAwareCognitionRegistry(max_active=3) | src/life_kernel/cognition.py:419-513 | bounded concurrent BackgroundCognition instances keyed by project_id |
| _resolve_thread_id(project_id) | src/life_kernel/heartbeat.py:131-172 | reads feature:projects:enabled flag; returns heartbeat-{project_id} if ON+project_id else heartbeat |
| KGRecallAdapter / MemoryRecallAdapter | src/life_kernel/p16_adapter.py, p18_adapter.py | already project-scoped (project_id kwarg from main.py:294-314, 331-345) |
| LIFE_KERNEL_PROJECT_ID env | src/core/main.py:416-417 | passed to HeartbeatService(project_id=...) |

**This is the closest thing to multi-instance today**, but it is bounded (max 3) and ONLY registered for cognition loops. It does NOT create multiple HermesBrain instances.

---

## 7. What Would Need to Change for Multi-Instance Support

For P27 (multiple coexisting Hermes instances), the inventory identifies these blockers + the extension hooks that already exist:

### 7.1 Must-add (blockers)

| Blocker | Today | Multi-instance shape |
|---|---|---|
| HermesBrain constructed once at lifespan | app.state.hermes_brain (hardcoded localhost:20128 / guinevere / 9router) | Per-instance HermesBrain keyed by instance_id — registry similar to ProjectAwareCognitionRegistry. Dataclass+factory injection point already exists: HermesBrain(llm_config: dict | HermesBrainConfig, agent_factory: Callable | None = None) |
| Discord can't host multiple instances under one bot | ONE token, ONE guild, ONE chat channel | Per-instance (DISCORD_TOKEN_*, GUILD_ID_*, ALLOWED_CHANNEL_*) — pattern already proven by ShadowPipeline |
| DiscordRestClient has one httpx client/token | src/life_kernel/discord_rest_client.py:85-86 | Per-instance DiscordRestClient or per-instance REST pool |
| _memory_bridge / _cost_tracker / _embedding_service / _rate_limit_redis are MODULE singletons | src/discord/hermes_conversational.py:88-99, 101-161 | Must be parameterised by instance_id, not global |
| HermesSessionAdapter singleton via get_adapter() | src/hermes/adapter.py | Per-instance adapter — or refactor to a registry like get_adapter(instance_id) |
| GUINEVERE_CHAT_CHANNEL_ID is a constant | src/discord/hermes_conversational.py:51 | Per-instance chat channel — likely separate Discord bots (ShadowPipeline pattern) |
| GUILD_ID is a Python literal | src/discord/_entrypoint.py:48 | Per-instance guild via env var passed to _entrypoint.main() |
| hermes-config/config.yaml has ONE Discord config + ONE provider block | hermes-config/config.yaml:14-71 | If instances share one gateway: per-instance config overlays. If separate gateways: per-instance config.yaml copy + hermes-gateway@.service template |

### 7.2 Already in place (hooks that need only data setup)

| Available today | What it means for multi-instance |
|---|---|
| HermesBrainConfig(base_url, model, provider, api_key, max_iterations=5) (frozen dataclass) | Per-instance LLM config — no schema change |
| HermesBrain(agent_factory=Callable[[dict], Any]) injection point | Per-instance AIAgent subclass swap |
| LifeMindState.project_id + BackgroundCognition.project_id + per-call closure scope | Per-instance graph state — but only at cognition level, not at brain level |
| feature:projects:enabled Redis flag | Multi-project gating; ProjectAwareCognitionRegistry has the shape P27 could reuse |
| ShadowPipeline architecture | Multi-bot parallel precedent |
| 17 lifecycle hook events, 3 plugins, MCP servers registry | Per-process-scoped. Multi-instance = each instance loads its own config + plugins. BUT config.yaml paths are hardcoded to absolute VPS paths today — would need to be templated per instance |
| Lazy AIAgent import + injectable agent_factory (hermes_brain.py:75-111) | Per-instance AIAgent(...) does not require process restart |
| _default_agent_factory(**kwargs) and life_kernel _default_agent_factory | Perfect for many-brains-one-process |
| Memory adapter already project-scoped | MemoryRecallAdapter + KGRecallAdapter project_id-aware out of box. So per-Hermes memory domain is ALREADY supported — only the LLM/brain layer isn't |

### 7.3 Hard forks required if P24 OWNED FORK is in scope

If P27 needs per-instance Hermes-side customisation of the gateway process itself (not just adapter-level), then P24 fork-first work IS a prerequisite. P24 is on IMPL HOLD today. P24-002 source-verification wave is the gate that decides whether the first Hermes core-patch is needed.

For society-of-bots: current upstream Hermes v0.15.2 + the local adapter layer SUFFICE if each instance has its own (bot, channel, channel_id, gateway config overlay, brain config). Pathway: **no fork needed** — only Guinevere-side refactor.

For society-of-agent-processes: one hermes-gateway@<instance>.service systemd template + per-instance config.yaml. P24-018 canary template already uses .venv-hermes-canary isolated env; P27 could mirror that pattern.

---

## 8. Hermes Brain Bridge — how does it connect to the LLM/agent layer?

Source-of-truth: src/life_kernel/hermes_brain.py (464 LOC).

### 8.1 Bridge contract

`
HermesBrain(
    llm_config: dict[str, Any] | HermesBrainConfig,
    agent_factory: Callable[[dict[str, Any]], Any] | None = None,
)
`

HermesBrainConfig (frozen dataclass):
- base_url: str (today: http://localhost:20128/v1)
- model: str (today: guinevere)
- provider: str (today: 9router)
- api_key: str (today: 9ROUTER_API_KEY aliased from GUINEVERE_9ROUTER_API_KEY)
- max_iterations: int = 5

Frozen constants (hermes_brain.py:116-120): MAX_ITERATIONS=5, QUIET_MODE=True.

### 8.2 AIAgent wiring (lazy + injectable)

`
def _load_aiagent() -> Any:
    from run_agent import AIAgent
    return AIAgent

def _default_agent_factory(**kwargs) -> Any:
    AIAgent = _load_aiagent()
    return AIAgent(**kwargs)
`

AIAgent instantiated via _agent_instance lazy property on first .agent access:
`
self._agent_instance = self._agent_factory(
    base_url=...,
    model=...,
    provider=...,
    api_key=...,
    skip_memory=False,         # ENABLE memory for kernel context
    skip_context_files=False,  # ENABLE kernel world context
    quiet_mode=QUIET_MODE,
    max_iterations=MAX_ITERATIONS,
    enabled_toolsets=[core, web],
    disabled_toolsets=[dangerous, system],
)
`

Key bridging property: the agent_factory parameter is the ONLY thing standing between a single Guinevere and a society of Hermes. Replacing _default_agent_factory with a registry or a per-instance pick is the surgical multi-instance seam.

### 8.3 Reasoning call shape

async def think(user_message, system_prompt, conversation_history) -> dict[str, Any]:
- Calls agent.run_conversation(user_message, system_message, conversation_history) via asyncio.to_thread.
- Required response keys: final_response, input_tokens, output_tokens, total_tokens, model, estimated_cost_usd.
- Returns _fallback_response on failure (graceful degraded return, not raise).

async def think_with_tools(...): same shape plus tools= kwarg.

async def dispose(): no real close protocol on AIAgent; clears _agent_instance.

### 8.4 Custom exception

HermesBrainError(Exception): carries (message, error); logs via structlog; never exposes secrets.

### 8.5 Brain -> Graph wiring in production

From src/core/main.py:78-94:

`
hermes_brain = HermesBrain(llm_config=HermesBrainConfig(
    base_url=http://localhost:20128/v1,
    model=guinevere,
    provider=9router,
    api_key=os.getenv(9ROUTER_API_KEY, os.getenv(GUINEVERE_9ROUTER_API_KEY, )),
    max_iterations=5,
))
`

This single hermes_brain is then passed:
- to create_life_mind_graph(... hermes_brain=hermes_brain ...) (main.py:387) — drives observe_node / decide_node LLM calls.
- to HeartbeatService(... hermes_brain=hermes_brain ...) (main.py:446) — reserved for graph builder; heartbeat does NOT call brain directly.
- to ReflectionEvaluator(... hermes_brain=self._hermes_brain) (heartbeat.py:691) — hourly reflection for candidate generation.

Today's data flow:

`
HeartbeatService (1s/10s/30s/60s/5m/1h)
  -> graph.ainvoke(...)
       -> observe_node / decide_node / etc.
            -> HermesBrain.think()
                 -> asyncio.to_thread(agent.run_conversation(...))
                      -> AIAgent(**kwargs) <- run_agent.AIAgent
                           -> provider='9router' -> HTTP -> localhost:20128/v1
                           -> OpenAI-compatible chat completion
                           -> response -> token counts -> log -> return

BackgroundCognition (observer/memory/critic/curiosity/self_improvement/guardian)
  -> graph.ainvoke({observations: [obs]}) per loop
       -> HermesBrain NOT invoked by placeholder logic (cognition.py:354-368)
          Real Hermes-driven curiosity arrives in LK-014
`

The brain is always the LLM gateway; never the LLMRouter (which is None-initialized and documented as dormant).

---

## 9. Service / Deployment Topology

| Service | Active? | ExecStart | Purpose |
|---|---|---|---|
| guinevere-core.service | YES (FastAPI) | python -m uvicorn src.core.main:app (per vps-mirror/systemd-live/guinevere-core.service) | Primary runtime: lifespan boots HermesBrain + Heartbeat + Graph + Cognition + LoopManager + Guardian + HardStop + monthly cost + KG cron + surveillance consumer + P22 Integration Hub + P19 cognition registry. Port 9191 LLM metrics. /metrics Prometheus. |
| guinevere-discord.service | YES | .venv/bin/python -m src.discord._entrypoint (per systemd/guinevere-discord.service) | One Discord bot (~50 slash commands, conversational handler for #guinevere-chat via Hermes AIAgent, shadow pipeline on token/env opt-in) |
| hermes-gateway.service (TEMPLATE) | NO — repository template only (per its own header comment) | .venv/bin/hermes --config .../hermes-config/config.yaml gateway (systemd/hermes-gateway.service) OR hermes gateway run --accept-hooks (vps-mirror variant) | Would be the upstream Hermes gateway reading hermes-config/config.yaml. NOT deployed. ADR-035 Phase 7b local hardening passed but no claims of live deployment. |
| 11+ other guinevere-*.service | single-instance templates | each its own ExecStart | gmail, x-poster, mcp, loops, scheduler, surveillance, obscura, wearable-sync, wearable-analysis, monitoring, shadow-monitor, prune-weekly@ (cron template), backup@ (cron template) |

### 9.1 Slice & security

- All guinevere units share Slice=guinevere.slice.
- Resource caps: MemoryHigh=512M, MemoryMax=1G, CPUQuota=100%.
- Standard hardening: NoNewPrivileges=true, ProtectSystem=strict, ProtectHome=read-only, PrivateTmp=true, ProtectKernel{Tunables,Modules}=true, ProtectControlGroups=true, RestrictSUIDSGID=true, explicit ReadWritePaths=/home/guinevere/code/guinevere[/hermes-config].
- SyslogIdentifier=hermes-gateway for Hermes.

### 9.2 Environment files

- .env.discord for the bot.
- .env.hermes for the gateway (referenced by systemd EnvironmentFile=).
- .env.core for core (carries GUINEVERE_9ROUTER_API_KEY).
- .env.example documents repo-wide variables (line 281: GUINEVERE_REPO_ROOT default /home/guinevere/code/guinevere).

### 9.3 Docker

- Only Dockerfile.sandbox and docs/setup-evidence/P2/STEP-P2-020/docker-compose.yml. No production Docker. All production is systemd on Ubuntu VPS.

### 9.4 Top-level Hermes env vars

From hermes-config/.env.template + grep across .env*:

- DISCORD_BOT_TOKEN (main bot), DISCORD_SHADOW_BOT_TOKEN + DISCORD_SHADOW_BOT_ID + DISCORD_SHADOW_CHANNEL_ID + SHADOW_ENABLED + SHADOW_TRAFFIC_PCT (shadow bot)
- DISCORD_ALLOWED_USERS, DISCORD_ALLOWED_CHANNELS, DISCORD_REQUIRE_MENTION, DISCORD_FREE_RESPONSE_CHANNELS, DISCORD_AUTO_THREAD (gateway allowlist)
- NINEROUTER_API_KEY (alias 9ROUTER_API_KEY / GUINEVERE_9ROUTER_API_KEY)
- LLM_BASE_URL=http://localhost:20128/v1, LLM_MODEL=gpt-5.5, LLM_FALLBACK_MODEL, LLM_MAX_TOKENS=16384, LLM_TEMPERATURE=0.7, LLM_BUDGET_MONTHLY=30
- REDIS_URL=redis://localhost:6380/5, DATABASE_URL=postgresql://hermes_app:*@localhost:5433/guinevere
- MEMORY_BACKEND=redis, GROUP_SESSIONS_PER_USER=true
- PROMETHEUS_METRICS_PORT=9191, LOG_LEVEL=info, LOG_FORMAT=json
- DISCORD_APPROVAL_WEBHOOK
- HERMES_BRIDGE_SECRET (for src/loops/hermes_bridge.py HMAC; not used in new architecture)
- GUINEVERE_REPO_ROOT, GUINEVERE_9ROUTER_API_KEY, LIFE_KERNEL_DASHBOARD_CHANNEL_ID, LIFE_KERNEL_LOG_CHANNEL_ID, LIFE_KERNEL_PROJECT_ID, LIFE_KERNEL_SAFE_RECALL (kernel env)
- REDIS_PASSWORD (Redis auth)

---

## 10. Verdict — Multi-Instance Readiness Decision Inputs

### 10.1 Inventory summary

- **Single-brained, single-bot, single-gateway today.** One FastAPI process, one Discord bot, one Hermes gateway TEMPLATE (not deployed).
- **No fork today.** Hermes is hermes-agent 0.15.2 from PyPI (MIT, Nous Research). P24 fork is on IMPL HOLD.
- **Adapter pattern is the integration.** Guinevere wraps run_agent.AIAgent via src/life_kernel/hermes_brain.HermesBrain (P20) and via src/hermes/_session_adapter.HermesSessionAdapter (legacy P5/P2-022).
- **Extension surface is rich (~40 points).** 17 hook events, 3 in-process plugins, 12 shell hooks, 2 MCP servers, 8 cron jobs, configurable model/providers/fallback_providers, agent-runtime knobs (max_iterations, new_instance_per_invocation), per-instance AIAgent kwargs (base_url, model, provider, api_key, skip_memory, skip_context_files, enabled_toolsets, disabled_toolsets).
- **Single-instance anchors are concentrated in module-level singletons and Python constants.** _memory_bridge, _cost_tracker, _embedding_service, _rate_limit_redis, _get_hermes(), GUINEVERE_CHAT_CHANNEL_ID, GUILD_ID, app.state.hermes_brain, LoopManager, LoopGuardian, HardStopHandler, the single life_mind_graph, the single Redis client, the single PostgreSQL checkpointer DSN.
- **P19 already paved the multi-instance design vocabulary.** LifeMindState.project_id, KGRecallAdapter(project_id), MemoryRecallAdapter(project_id), BackgroundCognition(project_id), HeartbeatService(project_id), ProjectAwareCognitionRegistry(max_active=3) — SAME namespace P27 needs but only at the cognition layer.
- **Per-instance swing-points:** HermesBrain(agent_factory=...) injection (already callable-typed), HermesBrainConfig(base_url, model, provider, api_key, max_iterations) (already dataclass), ShadowPipeline (demonstrates multi-bot parallel pattern).

### 10.2 Decision input for P27 fork-vs-no-fork

Verdict candidates (per docs/setup-evidence/P24/README.md Allowed Verdicts):

1. **FORK REQUIRED — implementation ready.** Implies Hermes core itself must change to natively support multiple instances (Society Gateway mode). Required if the upstream Hermes gateway CLI takes a single config.yaml AND refuses to multi-process within one gate. Not yet verified — the Hermes CLI is not running; the upstream Hermes source was not opened (run_agent.py is monolithic 202 KB and not yet read top-to-bottom).
2. **HYBRID FORK REQUIRED.** Adapter + small upstream patch + Guinevere-side registry. P27 society is the natural place for HYBRID.
3. **NO FORK** if society is satisfied by Guinevere-side refactor only. Evidence FOR no fork: injection seam agent_factory=Callable[[dict], Any] + HermesBrainConfig dataclass + ShadowPipeline multi-bot pattern. Evidence AGAINST no fork: every bot needs its own hermes-config/config.yaml or a templated generator; gateway config.yaml has ABSOLUTE paths hardcoded; module-level singletons in hermes_conversational.py are not factoryed.

### 10.3 Action items feeding the P27 plan

1. **Decide fork target first.** If fork is in scope (per P24 owner directive), P27 must run AFTER P24 fork is built. If not, P27 can run on current hybrid adapter.
2. **Refactor module-level singletons.** _memory_bridge / _cost_tracker / _embedding_service / _rate_limit_redis need to become per-instance (likely _get_chat_dependencies(instance_id) factory).
3. **Refactor GUINEVERE_CHAT_CHANNEL_ID and GUILD_ID** into per-instance constants via env vars or registry.
4. **Build HermesInstanceRegistry** mirroring ProjectAwareCognitionRegistry(max_active=N) shape, owning per-instance HermesBrain, HermesSessionAdapter, DiscordRestClient, chat channel, guild, token.
5. **Per-instance hermes-config/config.yaml templates.** Move absolute paths to relative-to-instance; allow hermes-gateway@<instance>.service systemd template.
6. **Validate via shadow_pipeline parallelism.** Reuse ShadowPipeline as the regression smoke-test for the society (run 2-3 Hermes instances in parallel, verify isolation).
7. **Re-evaluate P24-002 gate.** If the first Hermes core-patch must support multi-instance natively, that gate is a direct dependency of P27. Otherwise P27 can run on pure Guinevere-side refactor.

---

## Appendix A — Key files (absolute paths)

### Source-of-truth (Guinevere-owned)

- C:\Users\faizz\guinevere\pyproject.toml (hermes-agent dep)
- C:\Users\faizz\guinevere\src\life_kernel\hermes_brain.py (464 LOC, brain bridge)
- C:\Users\faizz\guinevere\src\life_kernel\p16_adapter.py (123 LOC, KG adapter)
- C:\Users\faizz\guinevere\src\life_kernel\p18_adapter.py (115 LOC, memory adapter)
- C:\Users\faizz\guinevere\src\life_kernel\heartbeat.py (740 LOC, 6-interval clock)
- C:\Users\faizz\guinevere\src\life_kernel\cognition.py (513 LOC, background loops + project-aware registry)
- C:\Users\faizz\guinevere\src\life_kernel\state.py (328 LOC, state schema, project_id field)
- C:\Users\faizz\guinevere\src\life_kernel\models.py (116 LOC, SQLAlchemy persistence)
- C:\Users\faizz\guinevere\src\life_kernel\__init__.py (127 LOC, exports)
- C:\Users\faizz\guinevere\src\life_kernel\discord_rest_client.py (263 LOC, REST publisher, single token)
- C:\Users\faizz\guinevere\src\core\main.py (841 LOC, FastAPI lifespan boots ONE of everything)
- C:\Users\faizz\guinevere\src\discord\_entrypoint.py (785 LOC, ONE discord bot, single guild)
- C:\Users\faizz\guinevere\src\discord\hermes_conversational.py (700 LOC, module-level singletons: _memory_bridge, _cost_tracker, _embedding_service, _rate_limit_redis)
- C:\Users\faizz\guinevere\src\discord\_startup.py (352 LOC, presence + greeting)
- C:\Users\faizz\guinevere\src\discord\shadow_pipeline.py (multi-bot precedent)
- C:\Users\faizz\guinevere\src\hermes\adapter.py (55 LOC, singleton get_adapter())
- C:\Users\faizz\guinevere\src\hermes\_session_adapter.py (390 LOC, AIAgent wrapper, Redis DB4)
- C:\Users\faizz\guinevere\src\hermes\_memory_bridge.py (P18 conversation memory)
- C:\Users\faizz\guinevere\src\hermes\safety_plugin.py
- C:\Users\faizz\guinevere\src\loops\hermes_bridge.py (315 LOC, Redis DB5 pub/sub, P5-023 superseded)
- C:\Users\faizz\guinevere\hermes-config\config.yaml (394 LOC, gateway config)
- C:\Users\faizz\guinevere\hermes-config\.env.template (47 LOC, env shape)
- C:\Users\faizz\guinevere\hermes-config\SOUL.md (persona constitution)
- C:\Users\faizz\guinevere\hermes-config\hooks\ (12 shell hooks)
- C:\Users\faizz\guinevere\hermes-config\plugins\ (3 in-process plugins)
- C:\Users\faizz\guinevere\systemd\hermes-gateway.service (68 LOC, TEMPLATE ONLY)
- C:\Users\faizz\guinevere\systemd\guinevere-discord.service (33 LOC, ONE bot)
- C:\Users\faizz\guinevere\systemd\guinevere-core.service (FastAPI uvicorn)
- C:\Users\faizz\guinevere\vps-mirror\systemd-live\hermes-gateway.service (31 LOC, alt CLI variant — template)
- C:\Users\faizz\guinevere\vps-mirror\systemd-live\guinevere-core.service
- C:\Users\faizz\guinevere\Dockerfile.sandbox (sandbox only)
- C:\Users\faizz\guinevere\docs\setup-evidence\P2\STEP-P2-020\docker-compose.yml

### Research priors read end-to-end

- C:\Users\faizz\guinevere\docs\setup-evidence\P24\README.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-installed-runtime-surface-inventory.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-extension-points-hooks-plugins-research.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-hermes-upstream-identity-research.md (FORKABLE, MIT)
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-p1-p18-capability-inventory.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-p1-p18-hermes-convergence-map.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-fork-feasibility-maintenance-research.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\plan\p24-hermes-fork-first-full-convergence-plan.md
- C:\Users\faizz\guinevere\docs\setup-evidence\P24\research\p24-no-fork-vs-hybrid-vs-full-fork-benchmark.md

### Pip-installed (NOT vendored)

- C:\Users\faizz\AppData\Roaming\Python\Python314\site-packages\hermes_agent\ (metadata dist-info)
- C:\Users\faizz\AppData\Roaming\Python\Python314\site-packages\run_agent.py (202,842 bytes, monolithic, single-file upstream)

---
## Appendix B — P27 decision matrix (single-page)

Quick reference for the P27 Hermes Society Foundation plan writer.

### B.1 What multi-instance needs but doesn't have today

BLOCKER                                                              CURRENT SINGLE-INSTANCE OWNER                  NEEDED FOR SOCIETY
- Per-instance HermesBrain                                            app.state.hermes_brain                          HermesInstanceRegistry.get(instance_id)
- Per-instance DiscordRestClient (one httpx per token)                src/life_kernel/discord_rest_client instance    pool of clients
- Per-instance Discord bot + guild + chat channel                     _entrypoint.GUILD_ID constant                  env-driven; or per-instance _entrypoint.main(instance_id)
- Per-instance module-level singletons                                _memory_bridge, _cost_tracker, _embedding_service, _rate_limit_redis (hermes_conversational.py)
                                                                            factory take instance_id
- Per-instance HermesSessionAdapter                                   src/hermes/adapter.get_adapter()                get_adapter(instance_id)
- Per-instance hermes-config/config.yaml                              single config.yaml with absolute VPS paths   templated per instance OR shared config with 
- Per-instance hermes-gateway.service                                 ONE .service template                          hermes-gateway@<instance>.service template
- Per-instance cogs (already there)                                   ProjectAwareCognitionRegistry(max_active=3)    reuse shape for HermesInstanceRegistry

### B.2 What is already multi-instance-ready (just needs to be parameterized)

- HermesBrainConfig(base_url, model, provider, api_key, max_iterations) — frozen dataclass already per-instance
- HermesBrain(agent_factory=Callable[[dict], Any]) — injection point already supports subclass swap
- AIAgent constructor kwargs (base_url, model, provider, api_key, skip_memory, skip_context_files, enabled_toolsets, disabled_toolsets)
- memory.py and kg.py adapters — already project-scoped (project_id kwarg)
- 17 lifecycle hook events — already enumerable per-instance
- ShadowPipeline — already a multi-bot parallel precedent (DISCORD_SHADOW_BOT_TOKEN + DISCORD_SHADOW_CHANNEL_ID)

### B.3 Multi-instance entry-point depending on strategy

STRATEGY                                PATHWAY                                      P24 FORK DEPENDENCY
- Society of LMS-only (one Discord bot, multi-context)   No code fork; add HermesInstanceRegistry + factory pattern  NO (extension-only)
- Society of bots (multiple Discord bots)               Per-instance env + ShadowPipeline-style Discord multiplexing  NO (extension-only)
- Society of gateway processes (hermes-gateway@<n>)      Per-instance hermes-gateway@<n>.service + .venv-hermes-<n> isolation  LIKELY NO (still pure-Config)
- Society of fork-modified Hermes cores                 Each instance is a patched run_agent build                 YES (P24 fork-first prerequisite)

---

**Verdict:** **Partial multi-instance readiness.** The brain-layer is single-instance and the Discord-layer is single-token, both via module-level singletons and Python constants. The P19 cognition registry (max_active=3) is the only existing multi-instance scaffold, and it stops at the cognition layer. Per-instance config injection points already exist (HermesBrainConfig dataclass, agent_factory callable, AIAgent kwargs, ShadowPipeline multi-bot precedent), BUT P27 needs Guinevere-side refactor of hermes_conversational._memory_bridge / _cost_tracker / _embedding_service / _rate_limit_redis singletons, the _entrypoint.GUILD_ID constant, and a HermesInstanceRegistry (suggest reusing the ProjectAwareCognitionRegistry shape). P24 fork-first is NOT strictly required for the society today, but P24-002 source-verification + a small upstream CLI multi-config test are recommended preflight gates before committing P27 to a fork-first architecture.

---

## Appendix C — Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Buffy (codebase search specialist, sub-agent ninerouter/subagent) | Initial inventory. Verified against live pyproject.toml, pip-installed hermes-agent 0.15.2, src/life_kernel/{hermes_brain,p16_adapter,p18_adapter,heartbeat,cognition,state,models}.py, src/hermes/*.py, src/discord/{_entrypoint,hermes_conversational,shadow_pipeline,_startup}.py, src/core/main.py (FastAPI lifespan), src/loops/hermes_bridge.py, hermes-config/config.yaml (394 LOC), hermes-config/.env.template, systemd/{hermes-gateway,guinevere-discord}.service, vps-mirror/systemd-live/*, P24 round-1 research files including installed-runtime-surface-inventory and extension-points-hooks-plugins. All paths absolute. No secrets captured. |

---

*Generated 2026-06-28 for P27 Hermes Society Foundation planning. Inventory complete.*
