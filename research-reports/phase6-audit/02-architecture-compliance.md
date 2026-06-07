# ADR-035 Post-Migration Architecture Compliance Audit

Date: 2026-06-07
Scope: Post-migration compliance check against ADR-035 five-pillar architecture.

## Method

Static repo inspection only, plus local service checks where possible. No code changes made. No external network calls.

## Evidence Summary

- ADR-035 canonical architecture: `adr/ADR-035-hermes-migration.md`
- Hermes config: `hermes-config/config.yaml`
- Hermes persona baseline: `hermes-config/SOUL.md`
- Memory write/read pipelines: `src/memory/write_pipeline.py`, `src/memory/read_pipeline.py`
- Hermes safety/plugin layer: `src/hermes/safety_plugin.py`, `src/hermes/plugins/persona_plugin.py`, `src/hermes/adapter.py`
- MCP layer: `src/mcp/manager.py`, `src/mcp/custom_manager.py`, `src/mcp/auth.py`, `src/mcp/tools/`
- Local service probe: `sc.exe query guinevere-discord`, `sc.exe query hermes-gateway`

---

## Pillar 1 — Discord = Hermes gateway

**Verdict: CONDITIONAL**

### Findings

1. `hermes-config/config.yaml` shows Hermes Discord gateway config is present and points at a single allowed channel:
   - `discord.allowed_channels` lines 17-20
   - `discord.require_mention: false` lines 21-22
   - `discord.free_response_channels` lines 24-26

2. Hermes gateway / 9Router runtime config is present in the same file:
   - `model.provider: ninerouter` line 47
   - `model.base_url: http://localhost:20128/v1` line 48
   - `providers.ninerouter.base_url` line 54

3. SOUL baseline exists and is explicitly deployed as Hermes persona constitution:
   - `hermes-config/SOUL.md:1-5`
   - `SOUL.md` says dynamic state is managed by the safety plugin via Redis DB5.

4. Discord custom code is still present in `src/discord/` and is not fully absent from the active code path. Static grep found many `discord.py`-dependent modules in `src/discord/` (for example `src/discord/_entrypoint.py:25-32`, `src/discord/notifications.py:208-240`, `src/discord/hermes_conversational.py:315-446`). This means the repo still contains legacy Discord code, even if it may be deprecated in runtime.

5. Local service checks failed to confirm the runtime state of the services on this machine:
   - `sc.exe query guinevere-discord` → service does not exist (1060)
   - `sc.exe query hermes-gateway` → service does not exist (1060)
   - `systemctl` is not available in this environment, so live systemd status could not be verified.

### Evidence

- `hermes-config/config.yaml:12-29, 46-69`
- `hermes-config/SOUL.md:1-5`
- `src/discord/_entrypoint.py:25-32`
- `src/discord/notifications.py:208-240`
- `src/discord/hermes_conversational.py:315-446`

### Assessment

Architecture intent is documented, but runtime cutover cannot be proven from this environment. Legacy Discord code remains in the repo, and service state is unverified. That is not enough for PASS.

---

## Pillar 2 — Memory = Hybrid

**Verdict: CONDITIONAL**

### Findings

1. PostgreSQL is the sole write authority in the write pipeline:
   - `src/memory/write_pipeline.py:111-227` stores episodes through ORM `Episodes(...)` and `session.add(...)` / `session.flush()`.
   - No direct file/db writes outside the SQLAlchemy session are present in this pipeline.

2. Hermes memory bridge routes writes through the memory write pipeline:
   - `src/hermes/_memory_bridge.py:182-202` wraps `store_episode()` from `src.memory.write_pipeline`.
   - This is consistent with PostgreSQL-primary write authority.

3. Hermes read pipeline includes FTS fallback / hybrid recall:
   - `src/memory/read_pipeline.py:533-556` builds `plainto_tsquery(...)` / `ts_rank(...)` FTS queries.
   - `src/memory/read_pipeline.py:559-579` provides recency fallback.
   - `src/memory/read_pipeline.py:803-804` explicitly notes keyword-only fallback when embedding is unavailable.

4. `GuinevereMemoryProvider` was not found under the inspected paths in this audit pass. I did not find a matching symbol in the checked directories during the available static scan, so provider presence is not confirmed here.

5. I did not find evidence of Hermes directly writing to the database under `src/hermes/` during the checked scan. The visible code points to bridge-mediated writes rather than direct DB mutation.

6. The bridge RBAC SQL file requested by the audit prompt was not located in the inspected results. Because I could not read `migrations/phase-3/004-hermes-memory-bridge-rbac.sql`, SELECT-only enforcement for that role is not directly evidenced here.

### Evidence

- `src/memory/write_pipeline.py:111-227`
- `src/hermes/_memory_bridge.py:182-202`
- `src/memory/read_pipeline.py:533-579, 803-804`

### Assessment

Memory architecture is broadly consistent with hybrid PostgreSQL-primary design, but the audit prompt asked for explicit provider and migration SQL evidence that I could not confirm from the available files. Therefore not PASS.

---

## Pillar 3 — Safety = Hooks + Plugins

**Verdict: CONDITIONAL**

### Findings

1. `GuinevereSafetyPlugin` exists and is the main safety gate:
   - `src/hermes/safety_plugin.py:225-242` documents all 10 gates.
   - `src/hermes/safety_plugin.py:229-290` initializes the plugin and logs gate availability.

2. Gate implementations are present:
   - `G01-G10` are documented at `src/hermes/safety_plugin.py:233-242`.
   - Hook implementations are present for `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `transform_llm_output`, `api_request_error`, `on_session_start` at `src/hermes/safety_plugin.py:450-1101`.

3. However, the hook names in the audit prompt do not exactly match the code. The code uses Hermes hook names and explicitly notes `api_request_error` is not a valid Hermes v0.15.2 hook:
   - `src/hermes/safety_plugin.py:1018-1102`
   - `src/hermes/safety_plugin.py:1111-1117`
   - `src/hermes/safety_plugin.py:17` states `api_request_error` is not a valid Hermes hook.

4. `persona_plugin.py` is active and registered for enrichment-only persona injection:
   - `src/hermes/plugins/persona_plugin.py:333-367` describes the plugin.
   - `src/hermes/plugins/persona_plugin.py:390-465` implements `pre_llm_call` persona injection.
   - `src/hermes/plugins/persona_plugin.py:558-578` registers `pre_llm_call`, `post_llm_call`, `pre_tool_call`, `on_session_start`.

5. The safety plugin does not register `persona_plugin` itself; it enforces safety while persona remains a separate plugin.

6. `hermes-config/config.yaml` shows safety hooks are configured in YAML for defense-in-depth, including budget and consent hooks:
   - `hermes-config/config.yaml:118-173`
   - `pre_tool_call` budget and consent hooks are listed with blocking semantics.

### Evidence

- `src/hermes/safety_plugin.py:225-242, 450-1102, 1111-1117`
- `src/hermes/plugins/persona_plugin.py:333-367, 390-465, 558-578`
- `hermes-config/config.yaml:118-173`

### Assessment

Safety subsystem is largely in place, but the audit prompt’s exact hook list cannot be fully confirmed because Hermes v0.15.2 does not treat `api_request_error` as a valid hook. That is a documentation/runtime mismatch, so this pillar is CONDITIONAL rather than PASS.

---

## Pillar 4 — MCP = Hybrid

**Verdict: CONDITIONAL**

### Findings

1. Native Hermes MCP server exists:
   - `src/mcp/manager.py:1-95` defines a FastMCP server factory and registers all tools through `register_all_tools(server)`.

2. Custom FastMCP bridge exists for KEEP-7 tools:
   - `src/mcp/custom_manager.py:1-25` and `:49-60` document exactly seven custom tool families.
   - `src/mcp/custom_manager.py:93-101` lists the KEEP-7 tool families.

3. Auth matrix is Python-authoritative:
   - `src/mcp/auth.py:1-11` defines the 4 approval levels.
   - `src/mcp/auth.py:148-220` implements `require_approval()` with auth checks and forbidden blocking.
   - `hermes-config/config.yaml:193-196` explicitly says Python `src/mcp/auth_matrix.py` is the sole runtime auth source.

4. Aizanta isolation evidence is present in the broader repo, but within the requested scan the relevant isolation proof for MCP-specific port references was only indirectly visible. The config notes canonical ports and isolation assumptions:
   - `hermes-config/config.yaml:198-200` lists canonical ports including Redis 6380, Postgres 5433, 9Router 20128.
   - The local audit prompt asked for grep of `5432/6379` references in `src/mcp/`; I did not extract a direct source line proving the absence of those ports in the current run.

5. The tool inventory exists as `src/mcp/tools/` with 16 tool files plus `__init__.py`:
   - filesystem listing returned 17 entries total, indicating 16 tool modules in addition to `__init__.py`.
   - This supports the hybrid MCP architecture, but the prompt’s “5 native tools via Hermes” count was not independently derivable from a single authoritative source file in the inspected evidence.

6. `FORBIDDEN` operations are blocked by the auth layer:
   - `src/mcp/auth.py:42-49` defines `FORBIDDEN`
   - `src/mcp/auth.py:194-198` raises `ForbiddenOperationError` for forbidden operations.

### Evidence

- `src/mcp/manager.py:1-95`
- `src/mcp/custom_manager.py:1-25, 49-60, 93-101`
- `src/mcp/auth.py:1-11, 42-49, 148-220`
- `hermes-config/config.yaml:193-200`
- `src/mcp/tools/` directory listing (17 entries total)

### Assessment

Hybrid MCP architecture is strongly supported, but the audit prompt requires a precise native/custom count and explicit isolation grep result that I could not fully substantiate from the available static evidence. CONDITIONAL.

---

## Pillar 5 — LLM = 9Router

**Verdict: PASS**

### Findings

1. Hermes config is pinned to localhost 9Router only:
   - `hermes-config/config.yaml:46-55` sets `provider: ninerouter` and `base_url: http://localhost:20128/v1`.
   - `hermes-config/config.yaml:61-69` defines fallback providers that also target `http://localhost:20128/v1`.

2. Hermes adapter also uses 9Router localhost base URL:
   - `src/hermes/adapter.py:45-52` constructs the LLM config with `base_url: http://localhost:20128/v1` and `provider: 9router`.

3. No direct cloud provider endpoints were found in the Hermes adapter path inspected here. The visible configuration only references the local 9Router endpoint.

4. Budget configuration is present:
   - `hermes-config/config.yaml:71-76` sets `monthly_limit: 30.00`, `alert_threshold: 0.80`, `block_threshold: 1.00`.

5. Cost tracking exists in MCP-side code:
   - `src/mcp/cost.py:1-21` documents per-tool cost tracking.
   - `src/mcp/budget.py:1-5, 68-70` documents budget enforcement and fallback routing.

### Evidence

- `hermes-config/config.yaml:46-76`
- `src/hermes/adapter.py:45-52`
- `src/mcp/cost.py:1-21`
- `src/mcp/budget.py:1-5, 68-70`

### Assessment

The LLM pillar is the strongest match in the current evidence set: local 9Router base URL only, fallback chain local, and $30/month budget data present. PASS.

---

## Overall Architecture Compliance Verdict

**Overall verdict: CONDITIONAL**

### Why not PASS

- Pillar 1 runtime service state could not be confirmed in this environment; `guinevere-discord` and `hermes-gateway` were not discoverable via local service queries here.
- Pillar 2 lacks direct confirmation for `GuinevereMemoryProvider` and the requested bridge RBAC SQL file in the available evidence set.
- Pillar 3 has a documented Hermes hook-name mismatch (`api_request_error` is explicitly not a valid Hermes v0.15.2 hook), so the exact prompt requirements are not fully satisfied as written.
- Pillar 4 hybrid MCP architecture is present, but the prompt’s exact “5 native / 7 custom” count and Aizanta port-isolation grep were not fully proven with file evidence in this run.

### Why not FAIL

- The core post-migration architecture is largely represented in code and config:
  - Hermes Discord gateway config exists.
  - Memory write/read pipelines align with PostgreSQL-primary hybrid design.
  - Safety plugin and persona plugin are both present.
  - MCP native/custom split exists.
  - 9Router-only LLM routing is explicitly configured.

### Final statement

The repo shows substantial alignment with ADR-035, but the audit standard requested concrete evidence for every pillar. Based on the evidence available in this environment, the architecture is **not fully PASS** yet; it is **CONDITIONAL** pending runtime service verification and a few missing artifact-level confirmations.
