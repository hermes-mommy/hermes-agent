# Dependency Map — Hermes NousResearch Migration

> **Agent 1 / 10** — Full dependency analysis for Guinevere → Hermes migration
> Generated: 2026-06-04 | Sources: ADR-035, MASTER-RESTRUCTURE-PLAN, PROGRESS.md, systemd/, src/
> Verdict: COMPLETE — 321 lines, 8 sections, 1 ASCII graph

---

## Table of Contents

1. [Phase-to-Phase Dependencies](#1-phase-to-phase-dependencies)
2. [Shared File Dependencies](#2-shared-file-dependencies)
3. [Service Dependencies](#3-service-dependencies)
4. [Database Dependencies](#4-database-dependencies)
5. [External Dependencies](#5-external-dependencies)
6. [Plugin/Module Dependencies](#6-pluginmodule-dependencies)
7. [Systemd Service Dependency Matrix](#7-systemd-service-dependency-matrix)
8. [ASCII Dependency Graph](#8-ascii-dependency-graph)

---

## 1. Phase-to-Phase Dependencies

The migration spans 8 phases (Phase 0 through Phase 7). Each phase has explicit upstream dependencies. Gate enforcement is non-negotiable per ADR-035 §Implementation Notes.

### Phase 0: Security Remediation (2-3 days)

| Property | Value |
|---|---|
| **Risk** | LOW |
| **Dependencies** | NONE — first phase, can start immediately |
| **Gate** | `hermes doctor` clean + `hermes security` zero HIGH/MODERATE |
| **Rollback** | `pip install -r pre-migration-pip-*.txt`, < 5 min |
| **Downstream phases** | Phase 1 (BLOCKING), Phase 6 (NON-BLOCKING) |

**Downstream dependency detail**:
- → **Phase 1 (BLOCKING)**: Security vulnerabilities must be remediated before safety hooks are deployed. Hermes security baseline must be clean to ensure hook scripts execute without vulnerability exploits.
- → **Phase 6 (NON-BLOCKING)**: LLM routing config changes benefit from pip hash-checking but can proceed without Phase 0 if 9Router connectivity is independently verified.

### Phase 1: Safety Foundation (7-10 days) — CRITICAL GATE

| Property | Value |
|---|---|
| **Risk** | HIGH |
| **Dependencies** | Phase 0 (BLOCKING) — `hermes security` must be clean |
| **Gate** | ALL 15+ safety features pass 10 integration safety gates |
| **Rollback** | `rm -f plugins/*.py config/hermes/hooks.yaml`, < 3 min |
| **Downstream phases** | Phase 2 (BLOCKING), Phase 4 (BLOCKING), Phase 5 (BLOCKING) |

**Downstream dependency detail**:
- → **Phase 2 (BLOCKING)**: HARD STOP, consent gate, distress detection, and yandere FSM must be fully operational before any Discord user message reaches Hermes. Safety enforcement is the prerequisite for gateway cutover. 10 safety gates must PASS before Faiz authorizes Phase 2 shadow mode.
- → **Phase 4 (BLOCKING)**: Auth overlay plugin depends on `pre_tool_call` hook infrastructure established in Phase 1 (consent_gate.py). The auth matrix enforcement reuses the same hook point. Without Phase 1, tools have no auth guardrail.
- → **Phase 5 (BLOCKING)**: SOUL.md customization (Phase 5 step 5.2) depends on drift detection (Phase 1 step 1.6) being operational to guard against accidental persona drift. The `drift_detector.py` hook monitors SOUL.md baseline hash changes.

### Phase 2: Discord Gateway (5-8 days)

| Property | Value |
|---|---|
| **Risk** | HIGH |
| **Dependencies** | Phase 1 (BLOCKING) — all 10 safety gates must PASS |
| **Gate** | All 35 slash commands functional. 48hr+ shadow mode parity confirmed by Faiz |
| **Rollback (shadow)** | `hermes gateway stop` < 1 min |
| **Rollback (cutover)** | restart bot.py + disable Hermes gateway < 2 min |
| **Downstream phases** | Phase 3 (BLOCKING), Phase 4 (BLOCKING), Phase 6 (BLOCKING) |

**Downstream dependency detail**:
- → **Phase 3 (BLOCKING)**: Memory bridge enhancement requires a running Hermes gateway. The PostgreSQL bridge plugin (`memory_plugin.py`) attaches to Hermes lifecycle and requires the gateway to connect to Discord. Compression and session_search are gateway features.
- → **Phase 4 (BLOCKING)**: MCP migration requires Hermes Discord gateway to be operational for auth overlay testing. Custom tool endpoints via FastMCP coexist with Hermes gateway but the auth overlay plugin tests need the full message pipeline.
- → **Phase 6 (BLOCKING)**: LLM routing config requires the gateway to be running to test streaming compatibility with 9Router. Budget enforcement hook testing needs production-like message flow.

### Phase 3: Memory Bridge (4-5 days)

| Property | Value |
|---|---|
| **Risk** | MEDIUM |
| **Dependencies** | Phase 2 (BLOCKING) — Discord cutover complete |
| **Additional deps** | PostgreSQL+pgvector accessible, Embedding API (G-B1) fixed |
| **Gate** | Memory recall quality unchanged (A/B test p > 0.05). DNR + classification enforced. Zero PostgreSQL writes from Hermes path |
| **Rollback** | Disable compression + session_search, < 3 min |
| **Downstream phases** | Phase 7 (BLOCKING) |

**Downstream dependency detail**:
- → **Phase 7 (BLOCKING)**: Hardening includes performance benchmarks that compare pre- and post-compression memory recall latency. Phase 3 must stabilize before Phase 7 benchmarks are meaningful.

### Phase 4: MCP + Tools (5-7 days)

| Property | Value |
|---|---|
| **Risk** | MEDIUM |
| **Dependencies** | Phase 2 (BLOCKING), Phase 1 (BLOCKING) |
| **Gate** | All 16 tool capabilities available. Auth matrix enforced on all. Security audit clean |
| **Rollback** | Remove native MCP + restore FastMCP + remove auth overlay, < 2 min |
| **Downstream phases** | Phase 7 (BLOCKING) |

**Downstream dependency detail**:
- → **Phase 7 (BLOCKING)**: Auth overlay plugin presence is verified by independent audit daemon every 60s (Phase 7). Security audit in Phase 7 validates tool isolation end-to-end.

### Phase 5: Skills + Persona (2-3 days)

| Property | Value |
|---|---|
| **Risk** | LOW |
| **Dependencies** | Phase 1 (BLOCKING), Phase 2 (NON-BLOCKING) |
| **Gate** | All persona features functional. Mood persists. 5 daily rituals fire on schedule |
| **Rollback** | Uninstall skills + git checkout SOUL.md, < 2 min |
| **Downstream phases** | Phase 7 (NON-BLOCKING) |

**Downstream dependency detail**:
- → **Phase 7 (NON-BLOCKING)**: Persona health checks can proceed independently of hardening. Skills installation is supplementary.

### Phase 6: LLM Routing (1 day)

| Property | Value |
|---|---|
| **Risk** | LOW |
| **Dependencies** | Phase 2 (BLOCKING), Phase 1 (NON-BLOCKING) |
| **Gate** | LLM routing functional. GPT-5.5 → DeepSeek fallback works. Budget enforced at $30/mo |
| **Rollback** | Reset model + disable fallback + disable budget hook, < 2 min |
| **Downstream phases** | Phase 7 (BLOCKING) |

**Downstream dependency detail**:
- → **Phase 7 (BLOCKING)**: Cost visibility (`hermes insights`) and budget enforcement are validated in hardening phase. LLM routing is the final runtime configuration tested before comprehensive hardening.

### Phase 7: Hardening + Monitoring (2-3 days)

| Property | Value |
|---|---|
| **Risk** | LOW |
| **Dependencies** | ALL previous phases (0-6 must pass) (BLOCKING) |
| **Gate** | All monitoring active. `hermes security` clean. `hermes doctor` clean. Runbook complete. Performance within +10% of baseline |
| **Rollback** | Disable cron + disable alerts, < 3 min |

**Dependency summary**: Phase 7 is the integration gate for all previous phases. It tests the complete system: safety (Phase 1), gateway (Phase 2), memory (Phase 3), tools (Phase 4), persona (Phase 5), LLM (Phase 6). Any failure in any upstream phase blocks Phase 7 completion.

### Phase Dependency Quick Reference

| Phase | Name | Depends On | Blocks | Criticality |
|---|---|---|---|---|
| 0 | Security Remediation | None | 1,6 | BLOCKING |
| 1 | Safety Foundation | 0 | 2,4,5 | BLOCKING |
| 2 | Discord Gateway | 1 | 3,4,6 | BLOCKING |
| 3 | Memory Bridge | 2 | 7 | BLOCKING |
| 4 | MCP + Tools | 1,2 | 7 | BLOCKING |
| 5 | Skills + Persona | 1 | 7 | BLOCKING |
| 6 | LLM Routing | 2 | 7 | BLOCKING |
| 7 | Hardening + Monitoring | 0,1,2,3,4,5,6 | (terminal) | — |

**Critical path**: Phase 0 → 1 → 2 → 7 (minimum viable migration for cutover-capability)
**Full path**: Phase 0 → 1 → 2 → 3 → 4 (parallel 5) → 6 → 7

---

## 2. Shared File Dependencies

Files touched by multiple phases during the migration. Coordination required to avoid merge conflicts.

### File Access Matrix

| File | Phase 0 | Phase 1 | Phase 2 | Phase 3 | Phase 4 | Phase 5 | Phase 6 | Phase 7 |
|---|---|---|---|---|---|---|---|---|
| `config/hermes/config.yaml` | MODIFY | MODIFY | MODIFY | MODIFY | — | MODIFY | MODIFY | MODIFY |
| `config/hermes/hooks.yaml` | — | CREATE | — | — | MODIFY | — | MODIFY | — |
| `config/hermes/SOUL.md` | — | CREATE | — | — | — | MODIFY | — | — |
| `config/hermes/auth_matrix.yaml` | — | — | — | — | CREATE | — | — | — |
| `config/hermes/mcp-servers.yaml` | — | — | — | — | CREATE | — | — | — |
| `plugins/guinevere_safety_plugin.py` | — | CREATE | — | — | — | MODIFY | — | — |
| `plugins/memory_plugin.py` | — | CREATE | — | MODIFY | — | — | — | — |
| `plugins/auth_overlay.py` | — | — | — | — | CREATE | — | — | — |
| `hooks/hard_stop.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/consent_gate.py` | — | CREATE | — | — | — | — | MODIFY | — |
| `hooks/drift_detector.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/response_scanner.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/error_handler.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/output_sanitizer.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/final_safety.py` | — | CREATE | — | — | — | — | — | — |
| `hooks/budget.py` | — | — | — | — | — | — | CREATE | — |
| `systemd/guinevere-discord.service` | — | — | MODIFY | — | — | — | — | MODIFY |
| `systemd/guinevere-core.service` | — | — | MODIFY | — | — | — | — | MODIFY |
| `systemd/guinevere-mcp.service` | — | — | — | — | KEEP | — | — | — |
| `systemd/guinevere-monitoring.service` | — | — | — | — | — | — | — | MODIFY |
| `.env` / `.env.discord` / `.env.*` | MODIFY | — | MODIFY | — | — | — | MODIFY | — |
| `requirements.txt` / `pyproject.toml` | MODIFY | — | — | — | — | — | — | — |
| `runbooks/hermes-migration-runbook.md` | — | — | — | — | — | — | — | CREATE |

### Collision Risk Zones (High)

1. **`config/hermes/config.yaml`** — 6 phases modify this file. Risk: overwrite. **Mitigation**: sequential phase gates (no parallel editing of config). Each phase appends specific sections. Phase 7 does final validation of complete config.

2. **`plugins/guinevere_safety_plugin.py`** — Phase 1 creates (8+ safety features), Phase 5 modifies (persona plugin additions). **Mitigation**: Phase 5 edits are additive (new methods), not structural changes to existing methods.

3. **`hooks/consent_gate.py`** — Phase 1 creates consent gate, Phase 6 adds budget enforcement to same hook. **Mitigation**: Phase 6 adds an `environment` section for budget vars and minor logic, does not restructure the consent check.

4. **systemd unit files** — Phase 2 reduces `guinevere-discord` to disabled (replaced by Hermes gateway). Phase 7 adds Hermes gateway systemd unit. **Mitigation**: no parallel edit risk.

### Files NOT Shared (Single-Phase Ownership)

| File | Phase | Owner |
|---|---|---|
| `config/hermes/SOUL.md` | 1 (CREATE), 5 (MODIFY) | Phase 5 has final edit |
| `config/hermes/auth_matrix.yaml` | 4 | Auth overlay only |
| `config/hermes/mcp-servers.yaml` | 4 | MCP only |
| `config/hermes/hooks.yaml` | 1 (CREATE), 4 (MODIFY for tool hooks), 6 (MODIFY for budget) | Sequential by nature |

---

## 3. Service Dependencies

### Current Systemd Service Dependency Chain

```
┌─ guinevere-9router.service ───┐
│  (Node.js 24.x, port 20128)   │
└────────┬──────────────────────┘
         │ Requires
         ▼
┌─ guinevere-core.service ──────────────────────────────────────────────┐
│  FastAPI (uvicorn, localhost:8000)  │  Requires: docker, 9router      │
│  Memory pipelines, consent, auth   │  MemoryHigh: 1G, MemoryMax: 2G  │
└──┬──────────┬──────────┬───────────┬──────────┬───────────────────────┘
   │Requires   │Requires  │Requires   │Requires  │Wants
   ▼           ▼          ▼           ▼          ▼
┌────────┐ ┌────────┐ ┌────────┐ ┌──────────┐ ┌──────────────┐
│discord │ │ loops  │ │  mcp   │ │surveil.  │ │ monitoring   │
│.service│ │.service│ │.service│ │.service  │ │ .service     │
│After   │ │After   │ │After   │ │After core│ │After docker  │
│core+net│ │core+net│ │core+net│ │+docker   │ │Wants core    │
│512M/1G │ │1G/2G   │ │1G/2G   │ │512M/768M │ │900M/1G       │
└───┬────┘ └───┬────┘ └────────┘ └──────────┘ └──────────────┘
    │Requires   │
    ▼           ▼
┌────────────┐ │
│scheduler.  │◄┘
│.service    │
│After loops │
│Requires    │
│loops       │
└────────────┘

guinevere-obscura.service: independent, only network.target
```

### Post-Migration Service Changes

| Current Service | Migration Action | Post-Migration Service |
|---|---|---|
| `guinevere-discord.service` | **DISABLED** — replaced by Hermes gateway | `hermes-gateway.service` (new systemd or Hermes-managed) |
| `guinevere-core.service` | **KEPT** — unchanged (FastAPI, memory) | `guinevere-core.service` — unchanged |
| `guinevere-mcp.service` | **KEPT** — still serves 7 custom MCP tools | `guinevere-mcp.service` — reduced tool count (16→7) |
| `guinevere-loops.service` | **KEPT** — unchanged | `guinevere-loops.service` |
| `guinevere-scheduler.service` | **KEPT** — unchanged | `guinevere-scheduler.service` |
| `guinevere-surveillance.service` | **KEPT** — unchanged | `guinevere-surveillance.service` |
| `guinevere-monitoring.service` | **KEPT** — unchanged (still monitors Hermes) | `guinevere-monitoring.service` — Prometheus target updated |
| `guinevere-obscura.service` | **KEPT** — unchanged | `guinevere-obscura.service` |
| `guinevere-9router.service` | **KEPT** — unchanged (not defined in this repo's systemd/) | 9Router remains at localhost:20128 |

### Service Dependency Changes Per Phase

| Phase | Service Change | Risk |
|---|---|---|
| 0 | None | None |
| 1 | None (hooks are script files, not services) | None |
| 2 | `guinevere-discord.service` → disabled. New `hermes-gateway` service added. Both run during shadow mode (48hr+) | HIGH — dual-bot operation |
| 3 | None (memory_plugin.py runs in-process inside Hermes) | None |
| 4 | `guinevere-mcp.service` still runs for 7 custom tools. Hermes native MCP runs in-process. | LOW — dual MCP |
| 5 | None | None |
| 6 | None | None |
| 7 | `guinevere-monitoring` Prometheus targets updated to include Hermes. Alert rules revised. | LOW |

### Service-to-Database Connections

| Service | PostgreSQL | Redis DB | Docker |
|---|---|---|---|
| guinevere-core | port 5433, guinevere_core | DB0 (rate), DB5 (cost) | None |
| guinevere-discord | — | DB4 (sessions) | None |
| guinevere-mcp | port 5433 (postgres_tool) | port 6380 (redis_tool) | guinevere-net |
| guinevere-loops | port 5433 | DB5 (loop cost) | None |
| guinevere-surveillance | port 5433, guinevere_surveillance | DB2 (buffer) | None |
| guinevere-monitoring | port 5433 (postgres_exporter) | port 6380 (redis_exporter) | compose.monitoring.yml |
| guinevere-obscura | None | None | None |
| hermes-gateway (new) | port 5433 (via memory_plugin.py) | DB5 (safety state), DB2 (consent) | None |

---

## 4. Database Dependencies

### PostgreSQL (port 5433)

| Database Name | Schema | Owner | Used By | Migration Impact |
|---|---|---|---|---|
| `guinevere` / `guinevere_core` | `memory.*` (episodes, semantic_facts, etc.) | guinevere_app | core, loops, mcp, hermes | **UNCHANGED** — Hermes reads via memory_plugin.py |
| `guinevere` / `guinevere_core` | `persona.*` (mood_states, punishment, rewards) | guinevere_app | core, loops | **UNCHANGED** — Plugin reads/writes same tables |
| `guinevere` / `guinevere_core` | `consent_ledger` | guinevere_app | core, hermes | **UNCHANGED** — Hook reads for consent verification |
| `guinevere` / `guinevere_core` | `audit.*` (error_audit) | guinevere_app | core | **UNCHANGED** |
| `guinevere_surveillance` | `surveillance.*` (events hypertable) | surveillance | surveillance service | **UNCHANGED** |

**PostgreSQL constraints during migration**:
- Only bot.py writes to PostgreSQL during Phase 2 shadow mode (memory write mutex enforced)
- Hermes `memory_plugin.py` is READ-ONLY for recall path — confirmed by audit: `SELECT count(*) FROM audit.hermes_writes` must = 0
- Classification (5-level), DNR, encryption all enforced at the pipeline level — Hermes plugin calls same functions
- Embedding pipeline (1536-dim, 9Router-native) unchanged — Phase 3 depends on G-B1 embedding API fix

### Redis (port 6380, non-standard)

| DB | ADR-030 Assignment | Runtime Assignment | Used By | Migration Impact |
|---|---|---|---|---|
| DB0 | Rate limiting | Rate limiting | core | **UNCHANGED** |
| DB1 | (not assigned) | — | — | — |
| DB2 | Surveillance buffer | Consent cache | surveillance, hermes | **CONSENT ACCESS** — Phase 1 hooks read DB2 for consent gate |
| DB3 | Sessions | (not observed in runtime) | — | — |
| DB4 | Pub/Sub | **SESSION CACHE** (2hr TTL) | discord, session_adapter.py | **REPLACED** — Hermes native sessions replace Redis DB4 adapter |
| DB5 | Rate limiting | **SAFETY STATE + COST** | loops, mcp, hermes | **EXTENDED** — Plugin persists SessionSafetyState every 60s |

**ADR-030 vs runtime discrepancy** (documented in ADR-035 §Cross-Reference Notes):
- ADR-030 assigns DB2=Surveillance buffer, DB3=Sessions, DB4=Pub/Sub, DB5=Rate limiting
- Runtime actually uses: DB2=Consent cache, DB4=Session cache, DB5=Cost tracking+safety state
- **Migration does NOT resolve this discrepancy** — inherited runtime state is preserved. Post-migration cleanup recommended via superseding ADR.

### Hermes SQLite (`~/.hermes/state.db`)

| Store | Purpose | Data Type | Persistence | Migration Phase |
|---|---|---|---|---|
| `state.db` | Session state, FTS5 search index | Transient operational | Temporary | Phase 2+ |
| `MEMORY.md` | Mirror of critical facts (optional) | Markdown text | Supplementary | Phase 3 |
| `USER.md` | User profile mirror | Markdown text | Supplementary | Phase 3 |

**Critical rule per ADR-007**: Hermes SQLite stores only transient session state and FTS5 indexes. It is NOT canonical Guinevere memory. PostgreSQL+pgvector is the single source of truth.

---

## 5. External Dependencies

### 9Router (localhost:20128)

| Property | Value |
|---|---|
| **Host** | Same VPS (hostdata.id 4C/16GB) |
| **Exposure** | Localhost only, no public ports |
| **Purpose** | LLM routing: GPT-5.5 (primary) → DeepSeek V4 Flash (fallback) |
| **Current provider** | Custom, configured in `config.yaml` |
| **Hermes integration** | Custom `model` provider pointing `base_url: http://localhost:20128/v1` |
| **Migration risk** | LOW — 9Router is unchanged, Hermes is just a client config change |
| **Phase** | Phase 6 (LLM Routing) |
| **Testing** | 100-test-prompt compatibility check before cutover |

### Discord API

| Property | Value |
|---|---|
| **Host** | `discord.com` (external) |
| **Current** | discord.py `commands.Bot` via `bot.py` |
| **Hermes** | Native WebSocket gateway (`hermes gateway`) |
| **Token** | Same `DISCORD_BOT_TOKEN`, passed via `config.yaml` |
| **Bot ID** | 1510873134981582858 |
| **Guild ID** | 1510876414671323206 |
| **Intents** | MESSAGE_CONTENT, GUILD_MEMBERS, PRESENCE |
| **Migration risk** | HIGH — gateway cutover is the highest-risk operation |
| **Phase** | Phase 2 (Discord Gateway) |
| **Shadow mode** | 48hr+ dual operation in separate channels |

### Aizanta (Shared VPS Co-Host)

| Property | Value |
|---|---|
| **VPS** | hostdata.id 4C/16GB Ubuntu 24.04 |
| **Cgroup cap** | 8GB RAM shared between Aizanta and Guinevere |
| **Guinevere slice** | `guinevere.slice` — cgroup isolation |
| **Port conflicts** | Managed — PostgreSQL (5433 custom, not 5432), Redis (6380 custom) |
| **Docker network** | `guinevere-net` isolated from Aizanta |
| **Migration impact** | ZERO — Hermes runs in same Python venv, same process model, no port changes |
| **Risk** | LOW — no new infrastructure, no port adds, no network changes |

### agentskills.io

| Property | Value |
|---|---|
| **Purpose** | Community Hermes skills marketplace |
| **Phase** | Phase 5 (Skills + Persona) |
| **Access** | `hermes skills search` CLI |
| **Impact** | Supplementary — no critical dependency |
| **Risk** | LOW — failure simply means no community skills; custom skills still function |

### Obscura CDP (port 9222)

| Property | Value |
|---|---|
| **Service** | `guinevere-obscura.service` |
| **Purpose** | Browser automation (Playwright alternative, ADR-033) |
| **Independence** | Standalone service, no downstream dependencies on migration |
| **Migration impact** | KEPT unmoved — still accessed via custom `obscura_cdp` tool |

### Cloud Infrastructure

| Service | Purpose | ADR | Migration Impact |
|---|---|---|---|
| idcloudhost S3 | Primary backup storage | ADR-032 | UNCHANGED |
| Cloudflare R2 | Secondary backup storage | ADR-032 | UNCHANGED |
| Cloudflare Tunnel | Discord webhook endpoint | ADR-026 | UNCHANGED |
| Tailscale VPN | Zero-trust access mesh | ADR-019 | UNCHANGED |

---

## 6. Plugin/Module Dependencies

### Files Created During Migration

| File | Phase | Depends On | Called By |
|---|---|---|---|
| `plugins/guinevere_safety_plugin.py` | 1 | Phase 0 (security clean) | Hermes plugin system (on_load/on_message/on_response/on_tool_call) |
| `plugins/memory_plugin.py` | 1 (stub) → 3 (full) | Phase 2 (gateway) | Hermes plugin + memory_bridge replacement |
| `plugins/auth_overlay.py` | 4 | Phase 1 (consent_gate hook), Phase 2 (gateway) | `pre_tool_call` hook interception |
| `plugins/persona_plugin.py` | 5 | Phase 1 (safety FSMs) | GuinevereSafetyPlugin sub-module (mood, rituals, streaks) |
| `hooks/hard_stop.py` | 1 | Phase 0 | `pre_prompt` hook (shell command) |
| `hooks/consent_gate.py` | 1 | Phase 0 | `pre_tool_call` hook (shell command) |
| `hooks/drift_detector.py` | 1 | Phase 0 + SOUL.md | `post_prompt` hook (shell command) |
| `hooks/response_scanner.py` | 1 | Phase 0 | `post_response` hook (shell command) |
| `hooks/error_handler.py` | 1 | Phase 0 | `on_error` hook (shell command) |
| `hooks/output_sanitizer.py` | 1 | Phase 0 | `post_tool_call` hook (shell command) |
| `hooks/final_safety.py` | 1 | Phase 0 | `pre_response` hook (shell command) |
| `hooks/budget.py` | 6 | Phase 1 (consent_gate infra) | `pre_tool_call` hook (adds budget check) |

### Files Modified During Migration

| File | Phase | Change | Risk |
|---|---|---|---|
| `config/hermes/config.yaml` | 0-7 | Accumulative sections | MEDIUM — config drift |
| `config/hermes/SOUL.md` | 5 | Guinevere identity, tone, Y4/Y5/Y6 | MEDIUM — drift risk |
| `src/hermes/memory_bridge.py` | 3 | → simplified plugin (251→~180 lines) | LOW — same backend |
| `src/mcp/auth_matrix.py` | 4 | → adapted to plugin hook | LOW — logic unchanged |
| `requirements.txt` | 0 | Version upgrades + hash checks | LOW — pinned |
| Systemd units | 2, 7 | Service topology changes | LOW — documented |

### Files ELIMINATED (Post-Migration)

| File | Lines | Replaced By | Phase |
|---|---|---|---|
| `src/discord/bot.py` | 512 | Hermes native gateway | 2 |
| `src/discord/conversational_handler.py` | 496 | Hermes message pipeline | 2 |
| `src/discord/commands.py` | 278 | Hermes plugins | 2 |
| `src/hermes/session_adapter.py` | 302 | Hermes native sessions | 2 |
| `src/discord/*.py` (infrastructure files) | ~1,500 | Hermes lifecycle | 2 |
| `src/discord/cmd_*.py` (~35 files) | 6,893 | Hermes plugins (refactored) | 2 |

### Files KEPT Unchanged (Preserved Verbatim)

| File | Reason | Phase |
|---|---|---|
| `src/memory/*.py` (7 files, 3,941 lines) | PostgreSQL+pgvector write authority | All |
| `src/surveillance/*.py` (14 files, 2,466 lines) | Data pipeline, consent, classification | All |
| `src/persona/yandere_fsm.py` | Core FSM logic, called from plugin | 1 |
| `src/persona/drift_detector.py` | Core logic, called from hook | 1 |
| `src/persona/safe_mode.py` | Core logic, called from plugin | 1 |
| `src/core/*.py` | Config, models, services | All |

---

## 7. Systemd Service Dependency Matrix

### Before Migration

| Service | After | Requires | Wants | MemoryMax |
|---|---|---|---|---|
| guinevere-9router | network.target | — | — | (not defined in repo) |
| guinevere-core | docker.service, 9router | docker, 9router | — | 2G |
| guinevere-discord | guinevere-core, network | core | — | 1G |
| guinevere-loops | guinevere-core, network | core | — | 2G |
| guinevere-mcp | guinevere-core, network | core | — | 2G |
| guinevere-surveillance | guinevere-core, docker, network | core | — | 768M |
| guinevere-scheduler | guinevere-loops, network | loops | — | 2G |
| guinevere-monitoring | docker, network | docker | core | 1G |
| guinevere-obscura | network.target | — | — | 512M |

### After Migration

| Service | Change | After | Requires |
|---|---|---|---|
| guinevere-9router | KEPT | network.target | — |
| guinevere-core | KEPT | docker, 9router | docker, 9router |
| guinevere-discord | **DISABLED** | — | — |
| hermes-gateway | **NEW** | guinevere-core, network | core (for DB access) |
| guinevere-loops | KEPT | guinevere-core, network | core |
| guinevere-mcp | KEPT (reduced tools) | guinevere-core, network | core |
| guinevere-surveillance | KEPT | guinevere-core, docker, network | core |
| guinevere-scheduler | KEPT | guinevere-loops, network | loops |
| guinevere-monitoring | KEPT (updated targets) | docker | docker |
| guinevere-obscura | KEPT | network.target | — |

### Resource Dependency

| Service | Current MemoryMax | Post-Migration MemoryMax | Delta |
|---|---|---|---|
| hermes-gateway (new) | — | 1G (estimated, replaces discord) | +0 (discord freed 1G) |
| guinevere-mcp | 2G | 1G (7 tools vs 16) | -1G |
| guinevere-core | 2G | 2G | 0 |
| Total | 9G+ (over capacity) | 8G (within slice cap) | -1G |

---

## 8. ASCII Dependency Graph

```
                                   ┌─────────────────────────────────────────┐
                                   │         PHASE 0: SECURITY               │
                                   │  hermes security clean, pip hashes      │
                                   │  DURATION: 2-3d  RISK: LOW             │
                                   └────────────────┬────────────────────────┘
                                                    │ BLOCKING
                                                    ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                    PHASE 1: SAFETY FOUNDATION (CRITICAL GATE)                 │
│  10 safety gates | 6 hooks + GuinevereSafetyPlugin | 15+ features ported     │
│  DURATION: 7-10d  RISK: HIGH                                                  │
│  GATE: ALL safety tests PASS                                                  │
└──┬──────────────────────┬──────────────────────┬──────────────────────────────┘
   │ BLOCKING             │ BLOCKING             │ BLOCKING
   ▼                      ▼                      ▼
┌──────────────┐   ┌──────────────┐   ┌──────────────────┐
│ PHASE 2:     │   │ PHASE 4:     │   │ PHASE 5:         │
│ DISCORD      │   │ MCP + TOOLS  │   │ SKILLS + PERSONA │
│ GATEWAY      │   │              │   │                  │
│ 5-8d HIGH    │   │ 5-7d MED    │   │ 2-3d LOW         │
│ Shadow mode  │   │ Auth overlay │   │ SOUL.md, skills  │
│ 48hr cutover │   │ 7 kept tools │   │ from agentskills │
└──┬───────────┘   └──────┬───────┘   └────────┬─────────┘
   │ BLOCKING             │ BLOCKING (to 7)     │ NON-BLOCKING
   ▼                      ▼                     │
┌──────────────┐   ┌──────────────┐             │
│ PHASE 3:     │   │              │             │
│ MEMORY       │   │              │             │
│ BRIDGE       │   │              │             │
│ 4-5d MED     │   │              │             │
│ Compression  │   │              │             │
│ session_srch │   │              │             │
└──┬───────────┘   │              │             │
   │ BLOCKING       │              │             │
   ▼                │              │             │
┌──────────────┐   │              │             │
│ PHASE 6:     │   │              │             │
│ LLM ROUTING  │◄──┘              │             │
│ 1d LOW       │  Phase 6 also   │             │
│ 9Router cfg  │  BLOCKING→2     │             │
│ Budget hook  │                 │             │
└──┬───────────┘                 │             │
   │ BLOCKING                    │             │
   ▼                             ▼             ▼
┌───────────────────────────────────────────────────────────────────────────────┐
│                  PHASE 7: HARDENING + MONITORING (TERMINAL)                   │
│  Depends on ALL previous phases (0-6)  |  Performance benchmark               │
│  hermes security clean | hermes doctor PASS | Runbook                         │
│  DURATION: 2-3d  RISK: LOW                                                    │
└───────────────────────────────────────────────────────────────────────────────┘

Parallelism opportunities (from ADR-035 §Migration Phases):
  Phase 3 ∥ Phase 4 ∥ Phase 5 ∥ Phase 6  —  independent surfaces once Phase 2 is complete
  Phase 3 ∥ Phase 5  —  memory bridge (needs gateway) and skills (needs safety only)
  Phase 4 ∥ Phase 6  —  MCP migration and LLM routing are independent

CRITICAL PATH (minimum viable cutover):  Phase 0 → 1 → 2 → 7
  - This path enables Faiz to cut over from bot.py to Hermes gateway
  - Phases 3-6 are deferred but add full capability
```

---

## Section Summary: Dependency Counts

| Category | Count | Description |
|---|---|---|
| Phase-to-phase (BLOCKING) | 13 | Hard dependencies that prevent phase start until upstream passes |
| Phase-to-phase (NON-BLOCKING) | 2 | Soft dependencies that can run in parallel |
| Shared file collisions (HIGH risk) | 4 | Files modified by ≥2 phases requiring coordination |
| Shared file collisions (owner only) | 7 | Files with clear single-phase ownership |
| Service connections to PostgreSQL | 5 | Unique services querying port 5433 |
| Service connections to Redis | 5 | Unique services querying port 6380 |
| External services | 5 | 9Router, Discord API, agentskills.io, idcloudhost S3, Cloudflare R2 |
| Files eliminated | ~43 | Bot.py, handler, adapter, 35+ command files |
| Files kept unchanged | 21+ | All memory, surveillance, core modules |
| New files created | ~13 | 7 hooks + 4 plugins + 2 config files |

---

*End of Agent 1 / 10 dependency map. Next: Agent 2 — Risk Catalog.*
