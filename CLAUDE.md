# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Read This First

- **`AGENTS.md` is the binding operating contract** (28 KB, versioned v2.3). It defines the super-autopilot workflow, BLOCKING rules, per-step planner verification scaffold, and the auditor gate. Follow it before any substantive work. It overrides generic assistant defaults for this repo.
- **`README.md`** is in Bahasa Indonesia and is the project overview (architecture diagram, ADR summary, tech stack, emergency procedures). The safe word `HARD STOP` (typed in Discord) instantly neutralizes the persona.
- The git root is `C:/Users/faizz/hermes-agent/` — the parent of the working directory. The working dir `guinevere/` is one subpackage, not the repo root. Run commands from the git root.

## What This Repo Is

A **vendored fork of Hermes v0.15.2** (Nous Research agent framework, vendored at SHA 77a1650c — no longer pip-installed) extended with the **Guinevere** layer: an autonomous AI companion + engineering agent for a single operator (Faiz). Runs 24/7 on an Ubuntu VPS via systemd, with PostgreSQL + Redis (DB0–DB5), Prometheus/Grafana/Loki, Discord as primary interface, and a surveillance layer (Android Tasker + Windows daemon).

Persona is a "sugar-mommy" companion (Bahasa Indonesia) bounded by a strict consent/safety framework. The persona is real and load-bearing — the `HARD STOP` safe word, the Y4-baseline yandere ceiling (Y5 absolute max, Y6 forbidden), and consent-revocation rules are enforced in code, not just prose.

## Critical Naming Trap — `guinevere/` vs `guinevere/`

Both directories exist at the repo root. **This is an ongoing P24 port and the naming is inverted from what you'd expect:**

- **`guinevere/`** (typo, no second `e`) is the **canonical, active** Guinevere package — 586 imports across 204 files, 15 subpackages. The P24 port moved all active code here.
- **`guinevere/`** (correct spelling) is a **stale legacy subset** — 66 imports across 35 files.

**Live wiring discrepancy (verify before touching wiring):** `agent/agent_init.py:1652-1785` wires Guinevere modules via `from guinevere.*` (correct spelling), but the active code lives in `guinevere/` (typo). Recent commits (e.g. `7f5850d`) are actively fixing these path mismatches. **Before editing any `wire(agent)` integration or plugin-loader path, grep both spellings and confirm which dir is actually imported at runtime** — do not assume. `[tool.hatch.build.targets.wheel]` packages list `"guinevere"` (typo) as the built package.

## Two Layered Agent Loops

This repo contains **two distinct agent loops**. Don't confuse them:

### 1. Hermes Conversation Loop (core, synchronous)
- **`agent/conversation_loop.py:364`** — `run_conversation()` (~3,900 lines). The parent `AIAgent.run_conversation` (`run_agent.py:4360`) forwards here.
- Main `while` loop at `conversation_loop.py:780`: iterates up to `max_iterations` (default 90) / `iteration_budget`. Each iteration = one tool-calling cycle: sanitize messages → call LLM via transport adapter → if `tool_calls`, dispatch via `agent/tool_executor.py` → `model_tools.py:handle_function_call()` → `tools/registry.py` → handler; if no tool_calls, response is final.
- **Sub-agent dispatch:** `tools/delegate_tool.py` — spawns a fresh `AIAgent` per child (`_build_child_agent:880`) in a `ThreadPoolExecutor`, restricted toolset (blocks `delegate_task`, `clarify`, `memory`, `send_message`, `execute_code`), parent blocks until children return summaries.
- Four tools (`todo`, `memory`, `session_search`, `delegate_task`) are intercepted by the loop itself (`_AGENT_LOOP_TOOLS`, `model_tools.py:495`) because they need agent-level state.

### 2. Guinevere 7-Phase SDLC Loop (autonomous, async)
- **`guinevere/loops/`** — Guinevere's autonomous SDLC engine (ADR-011). 7 phases: Research → Plan & Delegate → Delegate → Execute → Validate & Audit → Update Docs → Setup Evidence → COMPLETE (`guinevere/loops/state_machine.py:25-35`).
- `LoopManager` (`guinevere/loops/manager.py:43`) runs `_run_loop()` (`:201`) as an `asyncio.Task`, calling `create_phase_handler(phase, …).execute(...)` per phase via `EvidencePipeline`.
- **Bridge to Hermes:** `guinevere/loops/hermes_bridge.py` listens to Redis DB5 pub/sub `hermes:cron:results` (HMAC-SHA256 verified) and triggers loops from Hermes cron results.
- `guinevere/loops/conversation.py` is an alternative dynamic REASON→ACT→OBSERVE→REPEAT loop.

## Guinevere → Hermes Wiring (three mechanisms)

The Guinevere layer attaches to the base Hermes agent three ways:

1. **Direct `wire(agent)` calls** in `agent/agent_init.py:1652-1785` — after `AIAgent` init, `init_agent()` calls ~12 fail-soft `wire()` functions in dependency order (Groups C–G: emotions, DAO, personality drift, tools, life_kernel, self_modify, discord, channels, production, consciousness, surveillance, observability). Each attaches runtime state (e.g. `agent._emotion_engine`). **Every wire is independently fail-soft** — a broken module never aborts `init_agent`.
2. **Hermes plugin hooks** — three plugins register via `register(ctx)` → `register_hook(name, callback)`:
   - `hermes-config/plugins/guinevere_persona/` → loads `guinevere/hermes/plugins/persona_plugin.py` — `pre_llm_call`/`post_llm_call`/`pre_tool_call`/`on_session_start` hooks; injects a `[PERSONA STATE]` block (15 keys from Redis DB5: mood, yandere level, punishment, reward, distress, relationship stage, corruption mode) into the system prompt. Consent- and HARD STOP-gated.
   - `hermes-config/plugins/auth_overlay/` → `pre_tool_call` hook; 4-level tool auth (READ_AUTO / WRITE_NOTIFY / DESTRUCTIVE_APPROVAL / FORBIDDEN), persists destructive approvals in Redis DB5 with 5-min TTL. Fail-closed.
   - `.hermes/plugins/guinevere-safety/` → loads `guinevere/hermes/safety_plugin.py` — 10 safety gates across 6 hooks (HARD STOP exact + semantic, distress, recovery, drift, forbidden content, secret leakage, yandere semantic, auth matrix, consent/safe-mode).
3. **FastAPI lifespan** — `guinevere/core/main.py` boots the full autonomous runtime (HermesBrain, LoopManager, HeartbeatService, surveillance consumer, KG ingestion cron, P22 Integration Hub, dashboard writer).

## Common Commands

Run from the git root (`C:/Users/faizz/hermes-agent/`). The project is **uv-managed** (`uv.lock` present, 654 KB).

### Setup / install
```bash
uv sync                        # preferred — recreates env from uv.lock
uv pip install -e ".[test]"    # editable install + test extras (pytest-cov, pytest-asyncio)
```
Python **>=3.12** required. No Makefile/justfile/pre-commit — commands are run directly.

### Tests (`testpaths=["tests"]`, `asyncio_mode="auto"`)
```bash
pytest                                                  # all tests
pytest tests/test_e2e_loop.py                           # one file
pytest tests/test_e2e_loop.py::test_function_name       # one function
pytest --cov                                            # with coverage (fail_under=80, branch=true)
```
`asyncio_mode = "auto"` means async tests need no `@pytest.mark.asyncio` decorator (though many still have it). Coverage sources: `agent`, `tools`, `gateway`, `hermes_cli`, `cron`, `guinevere`.

### Lint / format / typecheck
```bash
ruff check .        # lint (line-length=100, target py312)
ruff format .       # format
mypy .              # typecheck (strict=true) — no type-suppression allowed (see AGENTS.md §5)
```

### Run the agent
Three console scripts (`[project.scripts]`):
```bash
hermes                # interactive chat REPL (default subcommand; hermes_cli.main:main)
hermes-agent          # standalone runner, Google fire CLI (run_agent:main) — e.g. hermes-agent --query="…" --model="…"
hermes-acp            # ACP JSON-RPC server for editor integration (acp_adapter.entry:main)
hermes gateway        # long-running daemon for Discord/Telegram/WhatsApp (gateway/run.py)
hermes doctor         # validate config + dependencies
hermes setup          # interactive setup wizard (closest thing to a bootstrap)
```
Config-driven: `hermes --config hermes-config/config.yaml gateway`. Production runs via systemd units in `systemd/` (e.g. `hermes-gateway.service`, `guinevere-discord.service` → `python -m src.discord._entrypoint`). A startup gate lives at `scripts/startup_gate.py` (validates critical plugins before gateway launch).

### Config & secrets
- Config: `hermes-config/config.yaml` (Hermes), `config/guinevere.yaml` + `config/pharsa.yaml` (instances). Guinevere uses **pydantic-settings** (`guinevere/config/models.py:147` — `GuinevereConfig`, `env_nested_delimiter="__"`, `env_file=".env"`). Hermes uses `python-dotenv` (`~/.hermes/.env`).
- Required env vars (from `hermes-config/.env.template`): `DISCORD_BOT_TOKEN`, `NINEROUTER_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, `REDIS_URL`, `DATABASE_URL`, `DISCORD_ALLOWED_USERS`, `DISCORD_ALLOWED_CHANNELS`.
- Secrets: **SOPS + age** (`.sops.yaml`). Decrypt: `SOPS_AGE_KEY_FILE=~/secrets/age-key.txt sops --decrypt secrets/<file>.enc.yaml`. Per-service `.env.*` files generated by `bash scripts/setup-service-envs.sh`. The `secrets/` dir is gitignored and lives on the VPS at `~/secrets/` — it is **not** in the repo.

### DB migrations (Alembic, async, PostgreSQL)
```bash
alembic upgrade head
```
**No `alembic.ini` is committed** — it's expected to exist on the VPS / be generated. `alembic/env.py` is async (`async_engine_from_config`), reads `GUINEVERE_DB_PASSWORD` from env to replace a `:****@` DSN placeholder, and manages 12 schemas (`memory`, `persona`, `surveillance`, `financial`, `projects`, `social`, `agents`, `consent`, `security`, `audit`, `ops`, `extensions`; version table in `ops`). Raw SQL migrations also live in `migrations/` (not alembic-managed).

### Useful scripts (`scripts/`)
`preflight-check.sh` (read-only VPS health), `health-check-p1.sh`, `setup-service-envs.sh` (SOPS→`.env.*`), `startup_gate.py` (plugin validation), `bench_memory.py`, `ab_test_recall.py`, `test_alert_routing.sh`, `test_log_pipeline.sh`.

## Architecture Map (packages)

**Hermes framework (vendored):**
- `agent/` — core runtime: conversation loop, model adapters (`anthropic_adapter.py`, `bedrock_adapter.py`, `codex_responses_adapter.py`, `gemini_native_adapter.py`, `chat_completion_helpers.py`), `tool_executor.py`, `memory_manager.py`, context compression, prompt building, `error_classifier.py`.
- `tools/` — tool implementations, self-registering via `tools/registry.py` (`discover_builtin_tools()` AST-scans `tools/*.py`).
- `gateway/` — long-running daemon for messaging platforms; `gateway/run.py` (~923 KB).
- `providers/` — declarative `ProviderProfile` (`providers/base.py:39`): `api_mode`, `base_url`, `env_vars`, `fallback_models`. Lazy-discovered from `plugins/model-providers/` + user plugins + legacy `providers/<name>.py`.
- `agent/auxiliary_client.py` — side-task router (compression, vision, web extraction): main provider → OpenRouter → Nous Portal → custom → native Anthropic → direct API-key providers. HTTP 402 triggers auto-fallback.
- `acp_adapter/`, `hermes_cli/`, `cron/`, `tui_gateway/` — CLI, ACP server, scheduling, TUI.
- `hermes_state.py` (`SessionDB:346`) — SQLite session storage (WAL, FTS5, schema v13) at `~/.hermes/state.db`; compression-triggered `parent_session_id` chains.

**Guinevere layer (in `guinevere/`):** `channels/` (WhatsApp/Gmail/X/Telegram adapters, lazy `CONFIG_MISSING` registry — never fake success), `consciousness/` (ADR-063 7-substrate loop), `consent/` (revocation handler), `core/` (FastAPI master orchestrator), `discord/` (41 slash commands, 3 bot identities), `emotions/` (`EmotionEngine` FSM), `finance/`, `gamification/` (XP/levels), `gmail/`, `governance/` (ADR-064 DAO, 2/2 multisig — Ethereum mocked), `hermes/` (session adapter + `safety_plugin.py` + `plugins/persona_plugin.py` — the bridge), `hermes_plugins/` (command catalog by privilege tier), `http/`, `knowledge_graph/` (P16, RRF/PPR fusion, consent-aware RLS), `life_integrations/` (P22 unified registry, L1–L4 permissions), `life_kernel/` (24/7 LangGraph observe-decide-act, `HermesBrain`, heartbeat 1s/10m/30m/1h/5m/1h), `loops/` (7-phase SDLC), `mcp/` (4-level auth), `memory/` (4-layer AES-GCM-256 encrypted, Argon2id, PG RLS), `observability/` (Sentry + Prometheus), `persona/` (legacy FSM — mood/yandere/punishment/reward/ritual/drift/safe-mode/streak), `personality/` (P24 M12 rewrite — `BehaviorSignature` 32-dim cosine, `DriftDetector` 0.68 hysteresis, `PeerMonitor` Guin↔Pharsa via Redis DB7), `production/` (6 circuit breakers), `projects/` (P19 registry), `self_modify/` (T1–T5 mutability ladder), `surveillance/` (HMAC ingest, 4-class classification, secret scanner), `tools/` (M8 unified registry, ~118 actions, L1–L3), `wearable/` (P14 Mi Fitness → TimescaleDB → GHI → mood; never drives yandere FSM), `x_poster/` (P13 autonomous X scheduling).

**Surveillance layer:** server-side ingest is in `guinevere/surveillance/` (`receiver.py` HMAC-verified webhook → Redis DB2 buffer → `consumer.py` → PostgreSQL/TimescaleDB). The Android Tasker profiles and Windows daemon clients are **not in this repo** — they live on the devices.

## P24 Production Status (2026-07-03)

P24 Hermes Native Fork v3.0 tool backends are **production-complete**:

- **127 tool actions** across 9 backends (filesystem, vps, memory, browser, desktop, github, social, email, freelance)
- **379+ tests passing** (backend-specific + registry tests)
- **Security audit passed** — command injection fixes, tarfile path traversal patched, type annotations added
- **Performance audit passed** — filesystem 0.1ms/call, memory benchmarked, VPS/browser deferred to production
- **VPS production verified** — `uv sync` completed, all backends load, tests pass on VPS
- **Dual-path sync** — `guinevere/` (canonical) and `guinevere/` (legacy) paths synchronized

**What remains for full P24 production pass:**
- D2 blocker resolved (production already running P24 via `guinevere-core.service`)
- D3 blocker resolved (9Router connected at `localhost:20128`, 64 models available)
- Discord live-connect: pending (requires bot token provisioning)

**Next phase:** P27+ (Hermes Society Foundation) can begin once Discord is connected.

## Key Docs (read for substantive work)

`docs/00-core/` (BRD v2.0, PRD v2.2, Technical Architecture v2.0, **Agent Loop Spec v2.0**, **Memory Schema v2.0**, Persona v3.0) · `docs/10-governance/17-ADR_Index_v1.0.md` + `adr/` (33 ADRs) · `docs/20-security/20-SecurityPolicy_v1.0.md` · `docs/60-persona/60-PersonaSafetyPolicy_v1.0.md` + `61-SystemPromptMaster_v1.1.md` · `docs/40-operations/43-DisasterRecoveryPlan_v1.0.md`. Per-phase setup evidence lives in `docs/setup-evidence/`.

## Binding Tie-Breakers (from AGENTS.md §8)

Persona behavior → Persona Document v3.0 + PersonaSafetyPolicy · Architecture → ADR-Index + `adr/` · Safety boundary → PersonaSafetyPolicy + ADR-001/002 · Consent/surveillance → ConsentRevocationPolicy + SurveillanceDataPolicy · Security/auth → Security Policy + RBAC/ABAC Matrix · Evidence path → task scope + `evidence/` / `docs/setup-evidence/` convention.
