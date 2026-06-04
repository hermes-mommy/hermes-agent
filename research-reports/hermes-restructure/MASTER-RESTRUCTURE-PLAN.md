# MASTER RESTRUCTURE PLAN — Guinevere to Hermes NousResearch Migration

> **Phase 1 Research Output** — Capability Assessment + Migration Strategy
> Generated: 2026-06-04 | Hermes Agent v0.15.2 | Guinevere Project P0-P8 Complete (59.2%)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Current Architecture vs Hermes Architecture](#2-current-architecture-vs-hermes-architecture)
3. [Migration Strategy — Phased Approach](#3-migration-strategy--phased-approach)
4. [Discord Gateway Migration Plan](#4-discord-gateway-migration-plan)
5. [Memory System Strategy](#5-memory-system-strategy)
6. [Safety System Migration Plan](#6-safety-system-migration-plan)
7. [Tool/MCP Migration Plan](#7-toolmcp-migration-plan)
8. [LLM Routing & Budget Strategy](#8-llm-routing--budget-strategy)
9. [Risk Matrix & Rollback Plan](#9-risk-matrix--rollback-plan)

---

## 1. Executive Summary

### Decision: Migrate Guinevere to Hermes NousResearch — Hybrid Architecture

Hermes Agent v0.15.2 is a production-grade autonomous AI framework with native Discord gateway, MCP client, memory system, skills ecosystem, and lifecycle hooks. It replaces the majority of Guinevere's custom-built infrastructure (bot.py, conversational_handler.py, session_adapter.py) while preserving the custom safety, memory, and persona systems through hooks and plugins.

### Key Findings

| Dimension | Verdict | Confidence |
|---|---|---|
| **Discord Gateway** | MIGRATE to Hermes native — eliminates bot.py, conversational_handler.py, session_adapter.py | HIGH |
| **Memory System** | HYBRID — PostgreSQL+pgvector stays as primary write authority; Hermes compression/session-search adopted read-only | HIGH |
| **Safety System** | PORT to Hermes hooks + plugins — all 15+ features mapped to specific hook points | HIGH |
| **MCP/Tools** | HYBRID — 5 tools migrate to native MCP servers, 7 remain custom with auth overlay | MEDIUM |
| **Persona** | PORT to SOUL.md + skills — static identity in SOUL.md, dynamic enforcement via hooks/plugins | HIGH |
| **LLM Routing** | RETAIN 9Router — configure Hermes to use localhost:20128 as custom provider | HIGH |
| **Security** | REMEDIATE first — 11 vulnerabilities (1 HIGH ecdsa) must be fixed before migration | HIGH |

### What Hermes Eliminates

- `bot.py` (603 lines) — Hermes native gateway replaces GuinevereBot
- `conversational_handler.py` (614 lines) — Hermes message pipeline replaces custom 10-step handler
- `session_adapter.py` (366 lines) — Hermes native session management replaces Redis DB4 adapter
- 33 slash commands — Hermes native commands + plugin registration replaces COMMAND_SPECS
- Rate limiting logic — Hermes built-in rate limiting
- Response splitting — Hermes streaming + Discord edit batching

### What Guinevere Keeps (via Hooks/Plugins)

- All 15+ safety components (HARD STOP, consent, yandere FSM, drift, distress, DNR, classification)
- PostgreSQL+pgvector memory (47 tables, 12 schemas, 5 classification levels)
- Auth matrix (4 levels) with Discord webhook approval
- 7 custom MCP tools with no Hermes equivalent (postgres, redis, obscura_cdp, grep_app, etc.)
- Cost tracking and budget enforcement
- Surveillance and consent systems

### Source Reports

All findings documented in 16 research reports at `research-reports/hermes-restructure/`:

| Report | Subject | Lines |
|---|---|---|
| 01 | CLI Capabilities | 183 |
| 02 | Config System | 264 |
| 03 | Discord Gateway | 330 |
| 04 | Discord Migration Gap | 337 |
| 05 | Memory Built-in | 238 |
| 06 | Memory External | 245 |
| 07 | Memory Bridge Gap | 405 |
| 08 | MCP Native | 442 |
| 09 | Tools System | 237 |
| 10 | MCP Migration Gap | 301 |
| 11 | Skills System | 388 |
| 12 | SOUL & Persona | 452 |
| 13 | Hooks & Plugins | 245 |
| 14 | Safety Mapping | 474 |
| 15 | LLM Routing | 368 |
| 16 | Security Posture | 354 |

---

## 2. Current Architecture vs Hermes Architecture

### Current Guinevere Stack

```
┌─────────────────────────────────────────────────────────┐
│                    Discord.py Bot                        │
│  bot.py (603 lines) + conversational_handler.py (614)   │
│  33 slash commands | HARD STOP listener | Rate limiting  │
├─────────────────────────────────────────────────────────┤
│              Hermes Session Adapter                      │
│  session_adapter.py (366 lines)                          │
│  Redis DB4 | 2hr TTL | 20 turns | skip_memory=True      │
├─────────────────────────────────────────────────────────┤
│              Custom Memory Bridge                        │
│  memory_bridge.py (295 lines)                            │
│  PostgreSQL+pgvector | 47 tables | 12 schemas           │
│  5 classification levels | DNR | Hybrid ranking         │
├─────────────────────────────────────────────────────────┤
│              FastMCP Server (Custom)                     │
│  16 tools | Auth matrix (4 levels)                       │
│  Discord webhook approval | Tool isolation               │
├─────────────────────────────────────────────────────────┤
│              Persona Safety Layer (14 files)             │
│  yandere_fsm | drift_detector | punishment/reward        │
│  mood_engine | ritual_scheduler | safe_mode              │
│  consent_gate | hard_stop_handler | classification       │
├─────────────────────────────────────────────────────────┤
│              LLM Router                                   │
│  9Router localhost:20128 | GPT-5.5 + DeepSeek fallback   │
│  Cost tracker | $30/mo budget                            │
└─────────────────────────────────────────────────────────┘
```

### Target Hermes Architecture

```
┌─────────────────────────────────────────────────────────┐
│              Hermes Native Gateway                       │
│  Discord adapter | Streaming | Auto-threading            │
│  RBAC | Circuit breaker | Per-channel prompts            │
│  Plugin slash commands via ctx.register_command()        │
├─────────────────────────────────────────────────────────┤
│              Hermes Gateway Hooks (7 lifecycle)          │
│  pre_gateway_dispatch → HARD STOP + distress detection  │
│  pre_llm_call → persona drift injection                 │
│  pre_tool_call → consent gate + auth matrix             │
│  transform_llm_output → yandere boundary enforcement    │
│  transform_tool_result → output sanitization            │
├─────────────────────────────────────────────────────────┤
│              Memory: Hybrid Mode                         │
│  Hermes built-in: compression + session_search           │
│  PostgreSQL+pgvector: primary write authority            │
│  Custom plugin: recall_for_context + store_conversation  │
├─────────────────────────────────────────────────────────┤
│              MCP: Hybrid Mode                            │
│  Hermes native MCP: web, browser, terminal, file, git   │
│  Custom MCP servers: postgres, redis, obscura, grep_app  │
│  Auth overlay plugin: 4-level matrix + webhook approval  │
├─────────────────────────────────────────────────────────┤
│              SOUL.md + Skills + Plugins                  │
│  SOUL.md: Guinevere identity + behavior rules            │
│  Skills: safety, persona, domain from agentskills.io    │
│  Plugins: safety enforcement, persona dynamics           │
├─────────────────────────────────────────────────────────┤
│              LLM: 9Router (Unchanged)                    │
│  Custom provider → localhost:20128                       │
│  hermes model set + hermes fallback                      │
│  hermes insights for cost tracking                       │
└─────────────────────────────────────────────────────────┘
```

### Code Reduction Estimate

| Component | Current Lines | Post-Migration | Reduction |
|---|---|---|---|
| bot.py + conversational_handler.py | ~1,217 | 0 (Hermes native) | -1,217 |
| session_adapter.py | 366 | 0 (Hermes native) | -366 |
| MCP manager + 16 tools | ~3,000 | ~1,200 (7 custom only) | -1,800 |
| Memory bridge | 295 | ~150 (simplified plugin) | -145 |
| Persona (14 files) | ~4,500 | ~2,500 (hooks + SOUL.md) | -2,000 |
| **Total** | **~9,378** | **~3,850** | **-5,528 (59%)** |

---

## 3. Migration Strategy — Phased Approach

### Phase 0: Security Remediation (BLOCKER — Before Any Migration)

**Duration**: 1-2 days | **Risk**: LOW | **Dependencies**: None

| Step | Action | Verification |
|---|---|---|
| 0.1 | Fix ecdsa HIGH vulnerability (timing attack) | `hermes security` shows 0 HIGH |
| 0.2 | Update aiohttp, pip to patched versions | `hermes security` shows 0 MODERATE |
| 0.3 | Fix PyJWT UNKNOWN vulnerabilities | `hermes security` clean |
| 0.4 | Create `.env` file with required variables | `hermes doctor` passes .env check |
| 0.5 | Fix config.yaml path resolution | `hermes doctor` passes config check |
| 0.6 | Fix venv entry point | `hermes doctor` clean |
| 0.7 | Install missing dependencies (ripgrep) | `hermes tools list` shows all available |

**Gate**: `hermes doctor` clean + `hermes security` zero HIGH/MODERATE

### Phase 1: Safety Foundation

**Duration**: 3-5 days | **Risk**: HIGH | **Dependencies**: Phase 0

| Step | Action | Hook/Plugin | Verification |
|---|---|---|---|
| 1.1 | Customize SOUL.md with Guinevere identity | `~/.hermes/SOUL.md` | Content review |
| 1.2 | Port HARD STOP handler to `pre_gateway_dispatch` | Gateway hook | Test: "HARD STOP" → neutral response, no LLM call |
| 1.3 | Port consent gate to `pre_tool_call` | Gateway hook | Test: WITHDRAWN consent → tool blocked |
| 1.4 | Port distress detection to `pre_gateway_dispatch` | Gateway hook | Test: D3/D4 message → safe response |
| 1.5 | Port yandere FSM boundary to `transform_llm_output` | Gateway hook | Test: Y6 content → rewritten to Y5 |
| 1.6 | Port drift detection to `pre_llm_call` | Gateway hook | Test: modified prompt → rollback + alert |
| 1.7 | Port DNR enforcement to memory plugin | Custom plugin | Test: DNR memory → excluded from recall |
| 1.8 | Port classification to memory plugin | Custom plugin | Test: Critical data → fails closed |
| 1.9 | Port secret scanner to `transform_llm_output` | Gateway hook | Test: leaked credential → redacted |
| 1.10 | Validate ALL safety features in isolation | Integration test | Full safety test suite passes |

**Gate**: ALL 15+ safety features pass integration tests. NO migration proceeds without this gate.

### Phase 2: Discord Gateway Migration

**Duration**: 3-5 days | **Risk**: HIGH | **Dependencies**: Phase 1

| Step | Action | Verification |
|---|---|---|
| 2.1 | Configure `hermes gateway setup` (token, guild, intents) | `hermes gateway status` → configured |
| 2.2 | Enable `reactions: true` for processing/success/error | Test: reactions visible on messages |
| 2.3 | Enable `auto_thread: true` for @mention threads | Test: @Guinevere → thread created |
| 2.4 | Configure `channel_prompts` for #guinevere-chat | Test: channel-specific behavior |
| 2.5 | Set `group_sessions_per_user: true` | Test: per-user session isolation |
| 2.6 | Register 33 slash commands as Hermes plugins | `hermes gateway list` → commands visible |
| 2.7 | Migrate high-priority commands (8 commands, HIGH feasibility) | Test each command |
| 2.8 | Migrate medium-priority commands (12 commands, MEDIUM feasibility) | Test each command |
| 2.9 | Migrate low-priority commands (13 commands, LOW feasibility) | Test each command |
| 2.10 | Run both bot.py AND Hermes gateway in parallel | Shadow mode: compare outputs |
| 2.11 | Cutover: disable bot.py, enable Hermes gateway exclusively | Test: full Discord flow |

**Gate**: All 33 slash commands functional. Shadow mode parity confirmed. Faiz approves cutover.

### Phase 3: Memory Bridge Enhancement

**Duration**: 2-3 days | **Risk**: MEDIUM | **Dependencies**: Phase 2

| Step | Action | Verification |
|---|---|---|
| 3.1 | Enable Hermes built-in compression (read-only mode) | Context window stays within budget |
| 3.2 | Enable Hermes session_search for cross-session lookup | Test: search across sessions returns results |
| 3.3 | Simplify memory_bridge.py to plugin (remove skip_memory) | Plugin loads, recall_for_context works |
| 3.4 | Configure Hermes memory to point to PostgreSQL+pgvector | Memory status shows custom backend |
| 3.5 | Validate hybrid ranking still works (Vector+FTS+Recency) | Test: recall quality unchanged |
| 3.6 | Validate DNR enforcement through plugin | Test: DNR memories excluded |
| 3.7 | Validate classification ceilings through plugin | Test: Critical data fails closed |

**Gate**: Memory recall quality unchanged. DNR + classification enforcement verified.

### Phase 4: Tool/MCP Migration

**Duration**: 3-5 days | **Risk**: MEDIUM | **Dependencies**: Phase 2

| Step | Action | Verification |
|---|---|---|
| 4.1 | Add standard MCP servers via `hermes mcp add` (web, filesystem, terminal, git, fetch) | `hermes mcp list` → 5 servers active |
| 4.2 | Build auth overlay plugin for auth matrix enforcement | Test: DESTRUCTIVE_APPROVAL → webhook prompt |
| 4.3 | Migrate filesystem tool to Hermes native with path whitelist | Test: path restriction enforced |
| 4.4 | Migrate terminal/shell tool to Hermes native with forbidden commands | Test: `rm -rf` blocked |
| 4.5 | Migrate web search to Hermes native (configure API keys) | Test: brave_search, exa_search work |
| 4.6 | Migrate fetch to Hermes native | Test: URL fetching works |
| 4.7 | Migrate git to Hermes native | Test: git operations work |
| 4.8 | Keep postgres_tool, redis_tool, obscura_cdp, grep_app as custom MCP | Test: all 4 tools functional |
| 4.9 | Configure tool isolation (path whitelist, command blocking) | Security audit passes |

**Gate**: All 16 tool capabilities available (native or custom). Auth matrix enforced. Security audit clean.

### Phase 5: Skills & Persona

**Duration**: 2-3 days | **Risk**: LOW | **Dependencies**: Phase 1

| Step | Action | Verification |
|---|---|---|
| 5.1 | Search agentskills.io for safety-related skills | `hermes skills search safety` |
| 5.2 | Install relevant safety skills | `hermes skills list` → installed |
| 5.3 | Search for persona/domain skills | Hub search results |
| 5.4 | Create custom Guinevere skills (mood, rituals, streaks) | SKILL.md files created |
| 5.5 | Configure mood persistence in Hermes plugin | Mood state persists across sessions |
| 5.6 | Configure ritual scheduler in Hermes plugin | 5 daily rituals fire correctly |
| 5.7 | Configure punishment/reward engines in Hermes plugin | L1-L5 and T1-T5 functional |
| 5.8 | Install `hermes curator` for skill management | Curator updates skills |

**Gate**: All persona features functional. Mood persistence verified. Rituals fire on schedule.

### Phase 6: LLM Routing & Budget

**Duration**: 1 day | **Risk**: LOW | **Dependencies**: Phase 0

| Step | Action | Verification |
|---|---|---|
| 6.1 | Configure `hermes model set` → 9Router at localhost:20128 | `hermes model show` → correct endpoint |
| 6.2 | Configure `hermes fallback` → DeepSeek V4 Flash | Test: primary down → fallback activates |
| 6.3 | Configure budget limits in `hermes config` | Budget enforcement active |
| 6.4 | Validate `hermes insights` tracks token usage | Cost data visible |
| 6.5 | Validate cost tracking matches current cost_tracker.py | Numbers align |

**Gate**: LLM routing functional. Fallback works. Budget enforced. Cost tracking accurate.

### Phase 7: Hardening & Monitoring

**Duration**: 2-3 days | **Risk**: LOW | **Dependencies**: Phase 2-6

| Step | Action | Verification |
|---|---|---|
| 7.1 | Configure `hermes cron` for health checks | Cron jobs active |
| 7.2 | Configure `hermes logs` monitoring | Log output verified |
| 7.3 | Configure `hermes backup` for state persistence | Backup creates successfully |
| 7.4 | Configure `hermes checkpoints` for rollback points | Checkpoint create/restore works |
| 7.5 | Run full security audit | `hermes security` clean |
| 7.6 | Run `hermes doctor` final check | All checks pass |
| 7.7 | Write runbook for Hermes operations | Runbook reviewed |
| 7.8 | Performance benchmark: response latency comparison | Latency within 10% of current |

**Gate**: All monitoring active. Security clean. Doctor clean. Runbook complete. Performance acceptable.

---

## 4. Discord Gateway Migration Plan

### Command Migration Feasibility

From Report 04 — 33 slash commands assessed:

| Feasibility | Count | Commands | Migration Approach |
|---|---|---|---|
| **HIGH** | 8 | chat, memory, status, config basics | Hermes native or simple plugin |
| **MEDIUM** | 12 | loop, surveillance, some finance | Plugin with custom logic |
| **LOW** | 13 | complex admin, ritual, streaks | Full custom plugin with state |

### Critical Migration Surfaces

1. **HARD STOP Interception**: Current `_on_message_listener` fires BEFORE `on_message`. Hermes equivalent: `pre_gateway_dispatch` hook returns `{action: "skip"}` — achieves same pre-LLM interception.

2. **10-Step Conversational Pipeline**: Current `conversational_handler.py` handles channel check → rate limit → distress → prompt assembly → memory → LLM → response split → cost → store → log. Hermes replaces steps 1-3 (channel, rate, basic flow) natively; steps 4-10 become hooks and plugins.

3. **Session Management**: Current Redis DB4 with 2hr TTL and 20-turn limit. Hermes has native session management with `group_sessions_per_user: true`. Custom plugin bridges to PostgreSQL for long-term storage.

### Streaming Upgrade

Current: No streaming (full response then send). Hermes: Full streaming with progressive Discord edits (~1.2s intervals, respects 5 edits/5s limit). This is a **net improvement**.

### Shadow Mode Strategy

Before cutover, run both systems in parallel:
1. bot.py handles messages normally
2. Hermes gateway receives same messages via webhook forwarding
3. Compare outputs for parity
4. Duration: minimum 48 hours
5. Faiz approves cutover based on parity report

---

## 5. Memory System Strategy

### Decision: Hybrid Mode (Option C from Report 07)

```
                    ┌──────────────────────────┐
                    │   Hermes Built-in Layer   │
                    │  Compression (50%/20%)    │
                    │  Session Search (FTS5)    │
                    │  Context Engine           │
                    │  (READ-ONLY supplement)   │
                    └────────────┬─────────────┘
                                 │ reads
                    ┌────────────▼─────────────┐
                    │  Custom Memory Plugin     │
                    │  recall_for_context()     │
                    │  store_conversation()     │
                    │  DNR enforcement          │
                    │  Classification ceilings  │
                    └────────────┬─────────────┘
                                 │ writes
                    ┌────────────▼─────────────┐
                    │  PostgreSQL + pgvector    │
                    │  47 tables | 12 schemas   │
                    │  5 classification levels  │
                    │  Hybrid ranking (RRF k=60)│
                    │  PRIMARY WRITE AUTHORITY  │
                    └──────────────────────────┘
```

### What Migrates to Hermes

| Capability | From | To | Mode |
|---|---|---|---|
| Context compression | Custom (none) | Hermes built-in | Read-only supplement |
| Session search | Custom SQL queries | Hermes session_search | Read-only supplement |
| Cross-session recall | memory_bridge.py | Hermes plugin | Read path |
| Episodic storage | memory_bridge.py | Hermes plugin → PostgreSQL | Write path (unchanged) |

### What Stays in PostgreSQL

| Capability | Reason |
|---|---|
| 47-table schema | Enterprise-grade, Hermes MEMORY.md cannot match |
| 5-level classification | No Hermes equivalent |
| DNR system | Consent-critical, must be custom |
| Encryption (faiz_profile) | Security-critical, custom implementation |
| Hybrid ranking (Vector+FTS+Recency) | Superior to Hermes FTS5 alone |
| Embedding pipeline (1536-dim, HNSW) | Custom infrastructure |

### External Provider Assessment

From Report 06: Of 8 external providers, only 2 are self-hosted (openviking, retaindb). The other 6 are cloud SaaS and **BLOCKED** for data sovereignty. Even the 2 self-hosted options add complexity without benefit over the existing PostgreSQL+pgvector system. **Recommendation: Do NOT adopt any external memory provider.**

---

## 6. Safety System Migration Plan

### Safety Feature → Hermes Hook Mapping

From Report 14 (474 lines, most critical report):

| Safety Feature | Current File | Hermes Hook | Migration Effort | Risk |
|---|---|---|---|---|
| HARD STOP | hard_stop_handler.py | `pre_gateway_dispatch` (skip) | MEDIUM | HIGH — must be flawless |
| Consent Gate | consent_gate.py | `pre_tool_call` (block) | MEDIUM | HIGH — fail-closed |
| Yandere FSM (Y4/Y5/Y6) | yandere_fsm.py | `transform_llm_output` | HIGH | HIGH — boundary enforcement |
| Drift Detector | drift_detector.py | `pre_llm_call` | LOW | MEDIUM — SHA-256 comparison |
| Distress Detection (D0-D4) | safe_mode.py | `pre_gateway_dispatch` | MEDIUM | HIGH — D3/D4 forces safe mode |
| Punishment Engine (L1-L5) | punishment_engine.py | Plugin | MEDIUM | MEDIUM — stateful |
| Reward Engine (T1-T5) | reward_engine.py | Plugin | MEDIUM | LOW — stateful |
| Mood Engine | mood_engine.py | Plugin + SOUL.md | LOW | LOW |
| Ritual Scheduler | ritual_scheduler.py | Plugin + cron | LOW | LOW |
| DNR Enforcement | memory write_pipeline | Memory plugin | MEDIUM | HIGH — consent-critical |
| Classification | classification.py | Memory plugin | MEDIUM | HIGH — fail-closed |
| Secret Scanner | secret_scanner.py | `transform_llm_output` | LOW | MEDIUM |
| Streak Tracker | streak_tracker.py | Plugin | LOW | LOW |

### Non-Negotiable Safety Requirements

These features MUST work identically or better post-migration. No degradation allowed:

1. **HARD STOP** — Must intercept before LLM call, return neutral response
2. **Consent Gate** — Must fail-closed, WITHDRAWN blocks all tool calls
3. **Y6 Prohibition** — Must never reach user, rewrite or block
4. **D3/D4 Distress** — Must force Y0_NEUTRAL, pause punishment
5. **DNR** — Must exclude marked memories from all recall paths
6. **Critical Classification** — Must fail closed without sanitized_summary
7. **Drift Detection** — Must detect and rollback prompt modifications
8. **Secret Scanner** — Must redact credentials before delivery

### Implementation Order

Safety features MUST be ported in this order (dependency chain):

```
HARD STOP (pre_gateway_dispatch)
    ↓
Distress Detection (pre_gateway_dispatch, same hook, priority after HARD STOP)
    ↓
Consent Gate (pre_tool_call)
    ↓
Yandere FSM (transform_llm_output)
    ↓
Drift Detection (pre_llm_call)
    ↓
DNR + Classification (memory plugin)
    ↓
Secret Scanner (transform_llm_output, chained with Yandere)
    ↓
Punishment/Reward/Mood/Ritual/Streak (plugins, lower priority)
```

---

## 7. Tool/MCP Migration Plan

### Tool Migration Matrix

| Guinevere Tool | Hermes Equivalent | Migration | Auth Matrix Handling |
|---|---|---|---|
| brave_search | `web` toolset (native) | MIGRATE | READ_AUTO → native |
| exa_search | `web` toolset (native) | MIGRATE | READ_AUTO → native |
| fetch | `web` toolset (native) | MIGRATE | READ_AUTO → native |
| websearch | `web` toolset (native) | MIGRATE | READ_AUTO → native |
| filesystem | `file` toolset (native) | MIGRATE | WRITE_NOTIFY → auth overlay |
| shell_tool | `terminal` toolset (native) | HYBRID | DESTRUCTIVE_APPROVAL → auth overlay |
| git_tool | `terminal` + git (native) | MIGRATE | WRITE_NOTIFY → auth overlay |
| docker_tool | `terminal` (native) | HYBRID | DESTRUCTIVE_APPROVAL → auth overlay |
| context7 | No equivalent | KEEP CUSTOM | READ_AUTO |
| grep_app | No equivalent | KEEP CUSTOM | READ_AUTO |
| obscura_cdp | No equivalent | KEEP CUSTOM | DESTRUCTIVE_APPROVAL |
| postgres_tool | No equivalent | KEEP CUSTOM | DESTRUCTIVE_APPROVAL |
| redis_tool | No equivalent | KEEP CUSTOM | WRITE_NOTIFY |
| sequential_thinking | No equivalent | KEEP CUSTOM | READ_AUTO |
| time_tools | No equivalent | KEEP CUSTOM | READ_AUTO |
| github | `terminal` + git (native) | HYBRID | WRITE_NOTIFY → auth overlay |

### Auth Matrix Preservation Strategy

The auth matrix (READ_AUTO, WRITE_NOTIFY, DESTRUCTIVE_APPROVAL, FORBIDDEN) has **no Hermes native equivalent**. Solution:

1. Build a **Hermes plugin** that wraps all tool calls
2. Plugin intercepts `pre_tool_call` hook
3. Looks up tool+operation in auth matrix config
4. READ_AUTO → allow through
5. WRITE_NOTIFY → allow + send Discord notification
6. DESTRUCTIVE_APPROVAL → block + send Discord webhook + wait for approval (5-min timeout)
7. FORBIDDEN → block + log

This plugin is the **single security gateway** for all tool operations.

---

## 8. LLM Routing & Budget Strategy

### Current Setup (Unchanged)

```
Guinevere → 9Router (localhost:20128) → GPT-5.5 (primary)
                                     → DeepSeek V4 Flash (fallback)
```

### Hermes Configuration

```yaml
# hermes config set commands
hermes model set --provider openai-compatible --base-url http://localhost:20128/v1 --model gpt-5.5
hermes fallback set --provider openai-compatible --base-url http://localhost:20128/v1 --model deepseek-v4-flash
hermes config set budget.monthly_limit 30.00
hermes config set budget.alert_threshold 0.80
```

### Cost Tracking

| Feature | Current (cost_tracker.py) | Hermes (hermes insights) |
|---|---|---|
| Token counting | Manual tracking | Built-in per-session |
| Cost estimation | Custom calculation | Built-in per-model pricing |
| Budget alerts | Custom implementation | `hermes config` budget |
| Historical data | PostgreSQL | `hermes insights` + `hermes logs` |
| Per-user tracking | Custom | Hermes session-level |

**Recommendation**: Use `hermes insights` for real-time tracking, keep PostgreSQL for historical audit trail.

---

## 9. Risk Matrix & Rollback Plan

### Risk Assessment

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Safety feature regression | MEDIUM | CRITICAL | Phase 1 gate: all 15+ features pass before proceeding |
| Discord gateway instability | LOW | HIGH | Shadow mode (48hr), circuit breaker, manual rollback to bot.py |
| Memory recall quality degradation | LOW | HIGH | Hybrid mode: PostgreSQL stays primary, Hermes read-only |
| Auth matrix bypass | LOW | CRITICAL | Plugin gateway intercepts ALL tool calls, fail-closed |
| LLM routing failure | LOW | MEDIUM | 9Router unchanged, Hermes is just a client config |
| Hermes version incompatibility | LOW | MEDIUM | Pin v0.15.2, test before update |
| Persona drift via SOUL.md | MEDIUM | HIGH | drift_detector hook monitors SOUL.md hash |
| Session data loss during migration | LOW | HIGH | `hermes backup` + `hermes checkpoints` before each phase |
| Performance regression | LOW | MEDIUM | Benchmark in Phase 7, rollback if >10% degradation |
| Budget overrun during testing | LOW | MEDIUM | `hermes config set budget.monthly_limit 30.00` enforced |

### Rollback Plan Per Phase

| Phase | Rollback Trigger | Rollback Action | Data Loss Risk |
|---|---|---|---|
| 0 | Security fix breaks something | `pip install` previous versions | None |
| 1 | Safety test fails | Revert hooks, keep bot.py | None |
| 2 | Gateway instability | Disable Hermes gateway, re-enable bot.py | None (shadow mode) |
| 3 | Memory quality drops | Disable Hermes compression, revert bridge | None (PostgreSQL primary) |
| 4 | Tool auth bypass detected | Disable native MCP, revert to FastMCP | None |
| 5 | Persona drift detected | Revert SOUL.md, disable skills | None |
| 6 | LLM routing fails | Revert session_adapter.py llm_config | None |
| 7 | Performance degraded | Revert to previous checkpoint | None |

### Rollback Command

At any point during migration:

```bash
# Emergency rollback to pre-migration state
hermes gateway stop
hermes hooks list  # document current hooks for re-install
hermes backup create --label "pre-rollback-$(date +%Y%m%d)"
# Re-enable bot.py in systemd/pm2
sudo systemctl start guinevere-bot
```

### Post-Migration Monitoring (First 7 Days)

| Metric | Threshold | Alert Channel |
|---|---|---|
| Response latency | <2x current average | Discord #ops |
| Safety feature trigger rate | Within 20% of baseline | Discord #ops |
| Error rate (hermes logs --level error) | <5% of messages | Discord #ops |
| Budget consumption rate | Within 20% of baseline | Discord #ops |
| Memory recall relevance | Manual spot-check 20 queries | Faiz review |
| HARD STOP success rate | 100% (zero tolerance) | Immediate alert |

---

## Appendix A: File Inventory

### Files Eliminated (Post-Migration)

| File | Lines | Replacement |
|---|---|---|
| `src/discord/bot.py` | 603 | Hermes native gateway |
| `src/discord/conversational_handler.py` | 614 | Hermes message pipeline + hooks |
| `src/discord/commands.py` | ~400 | Hermes plugin commands |
| `src/hermes/session_adapter.py` | 366 | Hermes native sessions |
| `src/mcp/manager.py` (partial) | ~500 | Hermes native MCP client |

### Files Modified (Post-Migration)

| File | Change |
|---|---|
| `src/hermes/memory_bridge.py` | Simplified to Hermes plugin |
| `src/mcp/auth_matrix.py` | Adapted to Hermes plugin hook |
| `src/persona/prompt_loader.py` | Adapted to SOUL.md + hooks |
| `config/hermes/config.yaml` | Fully configured |
| `config/hermes/system-prompt.md` | Updated for Hermes context |
| `~/.hermes/SOUL.md` | Customized for Guinevere |

### Files Created (Migration)

| File | Purpose |
|---|---|
| `plugins/safety_hooks.py` | All safety hooks (HARD STOP, consent, drift, distress) |
| `plugins/auth_overlay.py` | Auth matrix enforcement plugin |
| `plugins/memory_plugin.py` | PostgreSQL bridge as Hermes plugin |
| `plugins/persona_plugin.py` | Mood, rituals, punishment/reward, streaks |
| `config/hermes/hooks.yaml` | Hook configuration |
| `config/hermes/mcp-servers.yaml` | MCP server configuration |

### Files Preserved (No Change)

| File | Reason |
|---|---|
| `src/memory/*` (all) | PostgreSQL schema unchanged |
| `src/surveillance/*` (all) | Consent/classification unchanged |
| `src/persona/yandere_fsm.py` | Core logic preserved, called from hooks |
| `src/persona/drift_detector.py` | Core logic preserved, called from hooks |
| `src/persona/safe_mode.py` | Core logic preserved, called from hooks |
| `src/core/*` (all) | Config, models, services unchanged |

---

## Appendix B: Timeline Estimate

| Phase | Duration | Cumulative |
|---|---|---|
| Phase 0: Security Remediation | 1-2 days | Day 1-2 |
| Phase 1: Safety Foundation | 3-5 days | Day 3-7 |
| Phase 2: Discord Gateway | 3-5 days | Day 6-12 |
| Phase 3: Memory Bridge | 2-3 days | Day 8-15 |
| Phase 4: Tool/MCP Migration | 3-5 days | Day 11-20 |
| Phase 5: Skills & Persona | 2-3 days | Day 13-23 |
| Phase 6: LLM Routing | 1 day | Day 14-24 |
| Phase 7: Hardening | 2-3 days | Day 16-27 |
| **Total** | **17-27 days** | **~3-4 weeks** |

Phases 3-6 have overlap potential (independent surfaces). Critical path: Phase 0 → 1 → 2 → 7.

---

## Appendix C: Decision Log

| Decision | Rationale | Report Reference |
|---|---|---|
| Hybrid memory (not full migration) | PostgreSQL+pgvector capabilities far exceed Hermes built-in | Report 07 |
| No external memory provider | Cloud SaaS violates data sovereignty; self-hosted adds no value | Report 06 |
| Auth matrix as plugin (not native) | Hermes has no auth level concept; security non-negotiable | Report 10 |
| SOUL.md + hooks (not just SOUL.md) | Static file cannot enforce dynamic boundaries like Y6 | Report 12 |
| Shadow mode before cutover | 33 commands + safety features need parity verification | Report 04 |
| 9Router unchanged | Working system, no reason to change LLM routing | Report 15 |
| Fix security vulnerabilities first | 11 vulnerabilities block safe migration | Report 16 |
| pre_gateway_dispatch for HARD STOP | Only hook that fires before auth+dispatch, matching current pre-on_message | Report 14 |

---

> This document is the authoritative migration plan. All implementation must follow the phased approach with gate verification. No phase proceeds without its predecessor's gate passing. Safety features are non-negotiable and must be verified before any user-facing migration.
