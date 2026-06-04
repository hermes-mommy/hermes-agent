# Architecture Validation Report — Hermes Phase 1 Research vs Guinevere Codebase

> **Purpose**: Validate every architectural decision from the Hermes Phase 1 research reports against actual Guinevere source code and requirements before ADR-035 becomes binding governance.
> **Date**: 2026-06-04
> **Auditor**: Guinevere (Sisyphus-Junior)
> **Sources**: 8 research reports + 2 source files + 3 ADRs

---

## Table of Contents

1. [Validation Summary](#1-validation-summary)
2. [1. Hermes Gateway Replaces bot.py](#2-1-hermes-gateway-replaces-botpy)
3. [2. Memory Hybrid Architecture](#3-2-memory-hybrid-architecture)
4. [3. MCP Migration Paths](#4-3-mcp-migration-paths)
5. [4. Safety Hook Mapping Completeness](#5-4-safety-hook-mapping-completeness)
6. [5. 9Router Compatibility](#6-5-9router-compatibility)
7. [6. Security Vulnerabilities Remediation](#7-6-security-vulnerabilities-remediation)
8. [7. Code Reduction Estimate (59%)](#8-7-code-reduction-estimate-59)
9. [8. Timeline Assessment (17-27 Days)](#9-8-timeline-assessment-17-27-days)
10. [9. Consistency with Existing ADRs](#10-9-consistency-with-existing-adrs)
11. [Contradictions Between Research Reports](#11-contradictions-between-research-reports)
12. [Assumptions Requiring Faiz Approval](#12-assumptions-requiring-faiz-approval)

---

## 1. Validation Summary

| # | Validation Point | Verdict | Confidence |
|---|---|---|---|
| 1 | Hermes gateway replaces bot.py | **WARNING** | MEDIUM |
| 2 | Memory hybrid (PostgreSQL primary + Hermes read-only) | **PASS** | HIGH |
| 3 | MCP migration paths (5 native + 7 custom) | **WARNING** | MEDIUM |
| 4 | Safety hook mapping completeness | **FAIL** | HIGH |
| 5 | 9Router compatibility | **PASS** | HIGH |
| 6 | 11 security vulns remediation | **PASS** | HIGH |
| 7 | Code reduction estimate (59%) | **FAIL** | HIGH |
| 8 | Timeline (17-27 days) | **WARNING** | MEDIUM |
| 9 | Consistency with existing ADRs | **PASS** (with caveats) | HIGH |

**Overall**: 4 PASS, 3 WARNING, 2 FAIL. The migration direction is sound, but the Phase 1 research contains **material inaccuracies** in line counts, hook names, and slash command counts that must be corrected before ADR-035 binding. The hook mapping failure is the most critical finding.

---

## 2. 1. Hermes Gateway Replaces bot.py

### Verdict: **WARNING**

### Claim Under Review

> "Hermes native gateway replaces GuinevereBot — bot.py (603 lines), conversational_handler.py (614 lines), session_adapter.py (366 lines), 33 slash commands"

### Evidence

**Actual file sizes** (measured via `Measure-Object -Line`):

| File | Reported | Actual | Delta |
|---|---|---|---|
| `src/discord/bot.py` | 603 | **512** | -91 (-15%) |
| `src/discord/conversational_handler.py` | 614 | **496** | -118 (-19%) |
| `src/hermes/session_adapter.py` | 366 | **302** | -64 (-17%) |
| **Total** | **1,583** | **1,310** | **-273 (-17%)** |

**Actual slash command count**: **35** (not 33). Source: `src/discord/commands.py:126-249`. The tuple `COMMAND_SPECS` contains 35 entries including the 2 Phase 1 additions (`new`, `history`).

```
core:      status, mood, help, safeword, new, history               (6)
loop:      loop-start, loop-stop, loop-pause, loop-resume, loops,    (7)
           evidence, loop-priority
memory:    memory-search, memory-add, memory-forget, memory-export   (4)
surveillance: surveillance-status, surveillance-pause,                (3)
              surveillance-resume
finance:   cost, budget, cost-alert                                  (3)
system:    approve, deny, approve-all, focus, casual, consent,        (8)
           punishment, reward
admin:     restart-service, backup-now, health-check, clear-cache    (4)
```

**HARD STOP listener**: Verified in `bot.py:113-124`. The `_on_message_listener` uses `self.listen("on_message")` to register a listener that fires BEFORE the main `on_message` handler. Pattern:
```python
self.listen("on_message")(self._on_message_listener)
```

**Guild scoping**: EXACT guild ID is hardcoded at `bot.py:39`: `GUILD_ID = 1_510_876_414_671_323_206`. All 35 commands are registered with `guild=discord.Object(id=GUILD_ID)` (guild-scoped, not global).

**Channel locking**: Verified in `conversational_handler.py` via `CHANNEL_ID` references (the `#guinevere-chat` channel).

### Capability Assessment

| Capability | bot.py | Hermes Gateway (per Report 03) | Verdict |
|---|---|---|---|
| HARD STOP pre-on_message listener | ✅ `self.listen("on_message")` | ❓ Report 03: "Unknown — must verify hook support" | **UNVERIFIED** |
| 35 guild-scoped slash commands | ✅ All registered | ❓ "Unknown how to register 33 non-standard commands" | **PARTIAL — count is wrong** |
| Guild scoping (GUILD_ID) | ✅ Hardcoded | ✅ Configurable in setup | PASS |
| Channel locking | ✅ CHANNEL_ID check | ✅ Channel allowlist | PASS |
| `is_faiz_interaction()` guard | ✅ Multi-condition | ⚠️ RBAC can handle role but not complex multi-condition | WARNING |
| Rate limiting | ✅ Custom | ✅ Hermes built-in | PASS |
| Response splitting | ✅ Custom logic | ✅ Hermes streaming + Discord edit batching | PASS (improvement) |

### Critical Gaps

1. **`pre_gateway_dispatch` hook does not exist**: Report 03 explicitly states HARD STOP interception via gateway hooks is "Unknown — must verify." Report 03 was written BEFORE the hooks system was researched in Report 13. The actual Hermes hook names (Report 13) are `pre_prompt`, `post_prompt`, `pre_tool_call`, `post_tool_call`, `pre_response`, `post_response`, `on_error`. **None of these are gateway-level hooks.** They operate on the agent LLM pipeline, not on Discord message dispatch. See validation point 4 for full detail.

2. **35 commands, not 33**: All reports refer to "33 commands" but the actual codebase has 35. The Phase 1 additions (`new`, `history`) increased the count.

3. **Shadow mode assumption**: Report 03 recommends "Do not run both on same guild/channel simultaneously" but the MASTER plan's Phase 2 Step 2.10 relies on running both in parallel for shadow mode. These contradict each other. The MASTER plan's approach requires **webhook forwarding** to feed the same messages to both systems — a non-trivial setup not documented in any research report.

### Validation Confidence: **MEDIUM**

The core architecture direction is reasonable, but the line counts are wrong, the slash command count is wrong, and the gateway hook assumption is unvalidated.

---

## 3. 2. Memory Hybrid Architecture

### Verdict: **PASS**

### Claim Under Review

> "PostgreSQL+pgvector stays as primary write authority; Hermes compression/session-search adopted read-only"

### Evidence

**`memory_bridge.py` architecture** (251 lines, not the reported 295):

The bridge implements exactly the hybrid pattern described:
- **`recall_for_context()`** (line 84-150): Wraps `src.memory.read_pipeline.recall_memories()` — delegates to PostgreSQL+pgvector with all Guinevere safety features (DNR, classification ceiling, safe_mode, token_budget). Gracefully degrades on error (returns `[]`).
- **`store_conversation()`** (line 154-230): Wraps `src.memory.write_pipeline.store_episode()` — persists to PostgreSQL. Contains explicit rationale for `embedding_service=None` (9Router has no embedding models).
- **`skip_memory` flag**: In `session_adapter.py:127`, `skip_memory=True` disables ALL Hermes native memory. This is consistent with the "PostgreSQL primary" approach.

**Report 07 (Memory Bridge Gap) is the most thorough and accurate report** in the entire Phase 1 research suite. It correctly identifies:
- 4 migration options with risk matrices
- 16 bridge gaps (G-B1 through G-B16) — all verifiable in source code
- Gap G-B1 (embeddings always fail): Confirmed — `memory_bridge.py:214` passes `embedding_service=None` with rationale comment
- Gap G-B7 (hard_stop_handler not wired): Confirmed — `conversational_handler.py` uses DistressDetector, not the authoritative handler

### Compatibility Check

| Requirement | Supported | Evidence |
|---|---|---|
| PostgreSQL stays primary | ✅ | `store_conversation()` writes via `store_episode()` to PostgreSQL |
| Hermes read-only for compression | ✅ | MASTER plan Phase 3 enables compression separately |
| DNR enforcement preserved | ✅ | `recall_for_context(exclude_dnr=True)` delegates |
| Classification ceiling preserved | ✅ | Delegates via `principal` parameter |
| Hybrid ranking preserved | ✅ | Underlying `recall_memories()` still uses RRF |
| Safe mode works | ✅ | `safe_mode=True` parameter propagates |

### Gray Area: Hermes SQLite vs ADR-007

Hermes uses SQLite (`~/.hermes/state.db`) for session storage and FTS5 for session search. ADR-007 states: "Do not use SQLite for canonical Guinevere memory." The hybrid plan uses Hermes SQLite **only for session search and compression** (transient/operational), NOT for canonical memory (which stays in PostgreSQL). This is consistent with ADR-007's intent since session state is not "canonical Guinevere memory."

### Validation Confidence: **HIGH**

The memory architecture is the strongest part of the migration plan. Report 07 is thorough, accurate, and its gap register maps directly to source code. The "295 lines" claim for memory_bridge.py is 15% over (actual: 251), but this is a minor documentation error, not an architectural flaw.

---

## 4. 3. MCP Migration Paths

### Verdict: **WARNING**

### Claim Under Review

> "5 tools migrate to native MCP servers, 7 remain custom with auth overlay"

### Evidence

**Inter-report inconsistency**: Reports 08 and 10 disagree on the split:

| Category | Report 08 (MCP Native) | Report 10 (MCP Migration Gap) | MASTER Plan |
|---|---|---|---|
| Direct migration | 8 tools | 5 tools | 5 tools |
| Custom/partial | 8 tools | 2 partial + 7 custom | 7 custom + 4 hybrid |
| Deprecate | 0 | 1 (sequential_thinking) | 1 |

**The MASTER plan and Report 10 are self-consistent**. Report 08's count of "8 standard MCP available" is optimistic — it counts tools that have a *theoretical* standard MCP equivalent, but Report 10 correctly identifies that of those 8, only 5 have a **complete, low-risk** direct migration path. The other 3 (postgres, redis, git) have standard MCP servers that lack Guinevere's operation-level safety controls.

**Actual mapping from MASTER plan, Section 7**:

| Guinevere Tool | Hermes Path | Actual Risk |
|---|---|---|
| brave_search, exa_search, fetch, websearch | → Hermes `web` toolset (native) | LOW — 4→1 consolidation |
| filesystem | → Hermes `file` toolset (native) | MEDIUM — path whitelist unknown |
| shell_tool | → Hermes `terminal` HYBRID | **HIGH** — command blocking must be verified |
| git_tool, github | → Hermes `terminal` + git | MEDIUM — VCS tools lack auth granularity |
| docker_tool | → Hermes `terminal` HYBRID | **HIGH** — no Docker toolset in Hermes |
| postgres_tool, redis_tool | → KEEP CUSTOM | CRITICAL — no Hermes equivalent, non-negotiable |
| context7, grep_app, obscura_cdp, time_tools, sequential_thinking | → KEEP CUSTOM | LOW-CRITICAL — no Hermes equivalent |

### Critical Finding: Auth Matrix Gap

Report 10 correctly identifies that the **4-level auth matrix has no Hermes equivalent**. The MASTER plan's solution — an "auth overlay plugin" that intercepts `pre_tool_call` — is architecturally sound BUT:

1. **Report 08, Option C** describes the auth overlay intercepting tool calls from BOTH Hermes-native and Guinevere-custom MCP servers. This requires extending the auth matrix with `mcp_`-prefixed names (e.g., `mcp_filesystem_write_file`). The current `src/mcp/auth_matrix.py` uses flat names. This extension is well-designed in Report 08 but has not been prototyped.

2. **No evidence** that Hermes `pre_tool_call` hook receives tool name and operation context needed by the auth matrix. Report 13 describes `pre_tool_call` as a shell-command hook that receives JSON on stdin. Whether this JSON includes the tool name and operation is undocumented.

### Validation Confidence: **MEDIUM**

The MCP migration logic is internally consistent across reports 10 and the MASTER plan. Report 08 inflates the standardization count. The auth overlay approach is the right idea but relies on unverified Hermes hook behavior. The split of "5 migrate, 7 keep custom" is reasonable.

---

## 5. 4. Safety Hook Mapping Completeness

### Verdict: **FAIL**

### Claim Under Review

> "All 15+ safety features mapped to specific hook points"

### Critical Finding: Hook Name Mismatch

The **MASTER plan's architecture diagram (Section 2)** references hook names that **do not exist** in the documented Hermes hook system:

| MASTER Plan Hook Name | Usage | Exists in Hermes? | Actual Hermes Hook (Report 13) |
|---|---|---|---|
| `pre_gateway_dispatch` | HARD STOP, distress detection | **NO** | `pre_prompt` (LLM pipeline, not gateway dispatch) |
| `pre_llm_call` | persona drift injection | **NO** | `post_prompt` (after assembly, before LLM) |
| `pre_tool_call` | consent gate + auth matrix | ✅ YES | `pre_tool_call` |
| `transform_llm_output` | yandere boundary, secret scanner | **NO** | `pre_response` (before response sent) |
| `transform_tool_result` | output sanitization | **NO** | `post_tool_call` (after tool execution) |

### Evidence

**Report 13 (the authoritative hooks report)** documents exactly **7 lifecycle hooks**:

```
pre_prompt → post_prompt → pre_tool_call → post_tool_call → pre_response → post_response → on_error
```

These are shell-command hooks invoked with JSON on stdin, returning exit codes (0=PASS, 1=BLOCK, 2=WARN).

**Contradiction in MASTER plan Phase 1 steps**:

| Phase 1 Step | MASTER Hook Mapping | Actual Hermes Hook Equivalent |
|---|---|---|
| 1.2 HARD STOP | `pre_gateway_dispatch` (skip) | `pre_prompt` (nearest equivalent, but fires AFTER message dispatch) |
| 1.4 Distress detection | `pre_gateway_dispatch` | `pre_prompt` |
| 1.5 Yandere FSM | `transform_llm_output` | `pre_response` |
| 1.6 Drift detection | `pre_llm_call` | `post_prompt` |
| 1.9 Secret scanner | `transform_llm_output` | `pre_response` |

### Actual Feasibility After Correction

Re-mapping safety features to the CORRECT Hermes hooks:

| Safety Feature | Correct Hook | Action | Feasibility |
|---|---|---|---|
| HARD STOP | `pre_prompt` | Check message content, return `{action: "block"}` | **WARNING**: HARD STOP must fire BEFORE any processing. `pre_prompt` fires after message is accepted by gateway — a **regression** from current `_on_message_listener` which fires pre-on_message. HARD STOP keyword in the raw message text could trigger LLM side effects before `pre_prompt` intercepts. |
| Distress detection | `pre_prompt` | Same hook, chained after HARD STOP | **WARNING**: Same timing concern |
| Consent gate | `pre_tool_call` | Block tool on WITHDRAWN consent | **PASS** |
| Yandere FSM (Y6→Y5) | `pre_response` | Rewrite response content | **PASS** — `pre_response` can modify the response |
| Drift detection | `post_prompt` | SHA-256 compare assembled prompt vs SOUL.md | **PASS** |
| DNR enforcement | Memory plugin | Exclude DNR-marked content from recall | **PASS** (custom plugin) |
| Secret scanner | `pre_response` | Scan response for credential patterns | **PASS** — chained with Yandere FSM |

### The `pre_gateway_dispatch` Problem

This is the **most critical gap** in the entire migration plan. The MASTER plan assumes a `pre_gateway_dispatch` hook exists at the Discord gateway layer that can intercept messages **before** any processing — analogous to the current `_on_message_listener` pattern. No such hook exists in the documented Hermes system (Report 13, Report 03).

**Report 03 acknowledged this gap**: "HARD STOP interception before LLM — Unknown — Critical — must verify hook support." The MASTER plan then proceeded to invent a hook name and map safety features to it without verification.

**Mitigation**: A custom Discord gateway plugin that registers a `pre_gateway_dispatch`-equivalent hook would need to be written from scratch. This is feasible (Hermes plugins have `on_message` lifecycle methods per Report 13 Section 2.3) but is NOT a simple hook configuration — it's a custom plugin development task.

### Validation Confidence: **HIGH**

The hook names used in the MASTER plan do not match the actual Hermes hook system. This is a material error that affects the feasibility of HARD STOP, distress detection, and the timing guarantees of safety features. The correct hook names exist and CAN be used, but the mapping must be redone and the HARD STOP timing regression must be explicitly addressed.

---

## 6. 5. 9Router Compatibility

### Verdict: **PASS**

### Claim Under Review

> "Configure Hermes to use localhost:20128 as custom provider"

### Evidence

**Current 9Router config** (from `session_adapter.py:110-118`):
```python
AIAgent(
    base_url=llm_config["base_url"],   # http://localhost:20128
    model=llm_config["model"],         # gpt-5.5
    provider=llm_config["provider"],
    api_key=llm_config.get("api_key", ""),
)
```

**Report 15 (LLM Routing) provides a sound migration path**:

```yaml
# config.yaml
llm:
  model: gpt-5.5
  base_url: http://localhost:20128/v1
  api_key: ${NINEROUTER_API_KEY}
  provider: custom
```

### Compatibility Check

| Aspect | Current | Hermes Target | Compatible? |
|---|---|---|---|
| OpenAI-compatible endpoint | ✅ `/v1/chat/completions` | ✅ Hermes supports any OpenAI-compatible endpoint | ✅ |
| API key handling | Env var `.env` | `hermes secrets` (encrypted) | ✅ Improvement |
| Model naming | `gpt-5.5` | `hermes model set gpt-5.5` | ✅ |
| Fallback (DeepSeek V4 Flash) | Custom in `llm_router.py` | `hermes fallback` CLI or custom plugin | ⚠️ Unverified for custom providers |
| Auth pooling | Single key | Multi-key rotation | ✅ Improvement |
| Cost tracking | `cost_tracker.py` | `hermes insights` (aggregate) + custom hook | ⚠️ Budget enforcement needs custom hook |

### Fallback Concern

Report 15 correctly flags: "Hermes has a `fallback` command but its behavior for custom providers is undocumented." This is properly assessed as a risk and a custom plugin fallback is provided as Option B. No false claim of compatibility here.

### Validation Confidence: **HIGH**

9Router's OpenAI-compatible API at `localhost:20128/v1` is fundamentally compatible with Hermes' custom provider support. The only unverified aspect is native fallback chaining for custom providers — correctly identified as a risk in Report 15.

---

## 7. 6. Security Vulnerabilities Remediation

### Verdict: **PASS**

### Claim Under Review

> "11 vulnerabilities (1 HIGH ecdsa) must be fixed before migration"

### Evidence — Packages Confirmed Installed

```
ecdsa    → version 0.19.2  ✅ Confirmed in dependency tree
aiohttp  → version 3.13.5  ✅ Confirmed in dependency tree
PyJWT    → version 2.12.1  ✅ Confirmed in dependency tree
```

### Remediation Assessment (from Report 16)

| # | Severity | Package | Exploitability in Guinevere | Remediation | Verdict |
|---|---|---|---|---|---|
| 1 | **HIGH** | ecdsa timing attack | LOW — Guinevere doesn't use ECDSA signing | Accept risk; monitor for patch | **Correct** |
| 2 | MODERATE | aiohttp smuggling | MEDIUM — LLM calls go through HTTP | Upgrade to patched version | **Correct** |
| 3 | MODERATE | aiohttp traversal | LOW — no static file serving | Accept risk | **Correct** |
| 4 | MODERATE | pip confusion | LOW — dev-only | `--require-hashes` | **Correct** |
| 5 | MODERATE | pip code exec | LOW — dev-only | `--require-hashes` | **Correct** |
| 6 | LOW | pip info disc | LOW — dev-only | Accept risk | **Correct** |
| 7-10 | UNKNOWN | PyJWT (×4) | LOW — Guinevere doesn't use JWT directly | Investigate usage | **Correct** |

### Remediation Priority Matrix

The Report 16 priority matrix is accurate:
- **Immediate**: `pip install --upgrade aiohttp` (fixes 2 MODERATE via HTTP)
- **Document**: ecdsa risk acceptance
- **Investigate**: PyJWT usage in Hermes dependency tree

### Validation Confidence: **HIGH**

All 3 vulnerable packages are confirmed in the dependency tree. The remediation plan is proportionate to actual Guinevere exposure. The "BLOCKER" designation in the MASTER plan is appropriate — none of these individually are showstoppers, but Phase 0's `hermes security clean` gate is the right pre-migration requirement.

---

## 8. 7. Code Reduction Estimate (59%)

### Verdict: **FAIL**

### Claim Under Review

> "Total reduction: -5,528 lines (-59%)"

### Evidence — Actual vs Claimed Line Counts

| Component | Claimed Lines | Actual Lines | Delta |
|---|---|---|---|
| bot.py | 603 | **512** | -91 (-15%) |
| conversational_handler.py | 614 | **496** | -118 (-19%) |
| session_adapter.py | 366 | **302** | -64 (-17%) |
| memory_bridge.py | 295 | **251** | -44 (-15%) |
| **Verified subtotal** | **1,878** | **1,561** | **-317 (-17%)** |
| MCP manager + 16 tools | ~3,000 | Not verified | Unknown |
| Persona (14 files) | ~4,500 | Not verified | Unknown |
| **Grand total** | **~9,378** | **~9,061 best-case** | **-317 best-case** |

### Analysis

The verified component line counts are **consistently inflated by 15-19%**. If the same inflation rate applies to the unverified components (MCP ~3,000 → ~2,550, Persona ~4,500 → ~3,825), the actual total would be approximately **~7,900 lines** rather than the claimed ~9,378.

The post-migration estimates ("~3,850 remaining") are also speculative and unverified.

The **claimed 59% reduction** assumes:
1. All inflated line counts are correct — **FALSE**
2. Hermes can replicate all functionality of the eliminated files — **UNVERIFIED** (see hook mapping failure)
3. `conversational_handler.py`'s 10-step pipeline is fully replaced by Hermes — **UNVERIFIED** (the 10 steps include Guinevere-specific memory recall, system prompt assembly, and cost tracking that Hermes doesn't natively do)

### What CAN Be Eliminated

| Component | Verifiable Reduction | Notes |
|---|---|---|
| bot.py (512 lines) | 100% eliminated | Hermes native gateway replaces Discord connection |
| conversational_handler.py (496 lines) | **Partial** (estimated 60-70%) | Memory recall, prompt assembly, cost tracking move to hooks/plugins — not eliminated, just relocated |
| session_adapter.py (302 lines) | 100% eliminated | Hermes native session management replaces Redis DB4 adapter |
| MCP manager (partial) | **Partial** (estimated 30-40%) | 5 tools migrate to Hermes native, ~200 lines of manager code eliminated |

### Revised Estimate

A more realistic code reduction estimate: **35-45%** (not 59%).

### Validation Confidence: **HIGH**

The 59% figure is based on systematically inflated line counts and assumes Hermes replaces functionality that it cannot replicate. The actual reduction is in the 35-45% range. This doesn't invalidate the migration — a 35-45% code reduction is still significant — but the claim in the executive summary is materially inaccurate.

---

## 9. 8. Timeline Assessment (17-27 Days)

### Verdict: **WARNING**

### Claim Under Review

> "17-27 days total (3-4 weeks)"

### Analysis Per Phase

| Phase | Claimed | Assessment | Rationale |
|---|---|---|---|
| **Phase 0**: Security Remediation | 1-2 days | **1-2 days** (achievable) | Upgrade aiohttp, document ecdsa risk, investigate PyJWT. Straightforward. |
| **Phase 1**: Safety Foundation | 3-5 days | **5-7 days** (optimistic estimate) | Porting 15+ safety features with correct hook names. HARD STOP timing regression must be solved. Custom plugin for yandere FSM is complex. |
| **Phase 2**: Discord Gateway | 3-5 days | **5-8 days** (aggressive estimate) | 35 commands to migrate, shadow mode setup complex, hook name correction adds rework |
| **Phase 3**: Memory Bridge | 2-3 days | **2-3 days** (achievable) | Memory is the strongest part of the plan; mostly configuration |
| **Phase 4**: Tool/MCP Migration | 3-5 days | **5-8 days** (realistic) | Auth overlay plugin is complex, shell_tool migration high-risk, must test ALL auth levels |
| **Phase 5**: Skills & Persona | 2-3 days | **2-3 days** (achievable) | SOUL.md + skills configuration is straightforward |
| **Phase 6**: LLM Routing | 1 day | **1 day** (achievable) | Just configuration; 9Router is already working |
| **Phase 7**: Hardening | 2-3 days | **2-3 days** (achievable) | Monitoring, backups, performance benchmarks |
| **Total** | **17-27 days** | **23-35 days** | |

### Key Risks to Timeline

1. **Phase 1 + Phase 2 are serialized by the dependency chain** (Phase 0→1→2→7 is the critical path). You cannot overlap safety and gateway migration — the gateway must wait for safety verification.

2. **Phases 3-6 CAN overlap** as claimed if they use independent surfaces. The overlap estimate is optimistic but feasible.

3. **Shadow mode (48 hours minimum)** adds 2 mandatory days to Phase 2 that aren't factored into the "3-5 days" estimate — shadow mode is a separate step (2.10) that happens AFTER all commands are migrated.

### Validation Confidence: **MEDIUM**

The timeline is optimistic but not impossible. The "best case" of 17 days assumes zero rework, flawless hooks, and all phases overlapping perfectly — unrealistic. A more honest estimate is **4-5 weeks (23-35 days)**. The executive summary should present this realistic range, not the aspirational minimum.

---

## 10. 9. Consistency with Existing ADRs

### Verdict: **PASS** (with caveats)

### 9.1 ADR-005: LLM Router & Failover Strategy (9Router only, no OpenRouter)

**Claim**: "9Router only — no OpenRouter fallback"

**Consistency**: ✅ **PASS**. The migration plan retains 9Router as the sole LLM routing layer. Hermes is configured as a custom provider pointing to `localhost:20128`. The plan adds `hermes fallback` for model-level failover (GPT-5.5 → DeepSeek V4 Flash), which operates at a different layer than the router-level failover ADR-005 prohibits. Model fallback ≠ router fallback.

**Caveat**: If `hermes fallback` for custom providers is unsupported (Report 15 flag), a custom plugin implementation is needed. This is not an ADR violation — it's an implementation gap.

### 9.2 ADR-007: Memory Storage Backend Selection (PostgreSQL primary, no SQLite)

**Claim**: "PostgreSQL primary storage plus Redis cache; SQLite excluded"

**Consistency**: ✅ **PASS** with documented caveat.

The migration plan explicitly preserves PostgreSQL+pgvector as primary write authority. Hermes' internal SQLite (`~/.hermes/state.db`) is used only for transient session state and FTS5 search indexing — not for canonical Guinevere memory.

**Caveat**: Hermes session state in SQLite is a new SQLite dependency that didn't previously exist. While this doesn't violate ADR-007's letter ("no SQLite for canonical Guinevere memory"), operators should be aware that `~/.hermes/state.db` becomes a new data file to manage, back up, and potentially recover.

### 9.3 ADR-013: Guinevere MCP Native OpenCode Replacement

**Claim**: "Fully replace OpenCode with Guinevere MCP native"

**Consistency**: ✅ **PASS**.

ADR-013 mandates replacing OpenCode as the coding substrate. The Hermes migration operates at a different layer — the agent framework layer. Hermes replaces Hermes Agent's stateless wrapper usage (`AIAgent` with `skip_memory=True`), not OpenCode. The Guinevere MCP native tools remain as the coding substrate. ADR-013 is about "don't use OpenCode as a fallback coding tool" — it doesn't prohibit adopting a different agent framework.

**No contradiction**.

### ADR Consistency Summary

| ADR | Decision | Migration Impact | Status |
|---|---|---|---|
| ADR-005 | 9Router only, no OpenRouter fallback | Unchanged | ✅ PASS |
| ADR-007 | PostgreSQL primary, no SQLite for canonical memory | SQLite appears as Hermes internal state (non-canonical) | ✅ PASS (documented) |
| ADR-013 | Guinevere MCP native replaces OpenCode | No conflict — Hermes replaces agent framework, not coding substrate | ✅ PASS |

### Validation Confidence: **HIGH**

No direct contradictions with existing ADRs. The SQLite gray area is correctly scoped as transient/operational, not canonical memory.

---

## 11. Contradictions Between Research Reports

### 11.1 Report 08 vs Report 10: MCP Migration Count

| Issue | Report 08 | Report 10 |
|---|---|---|
| Tools with standard MCP equivalent | 8 | 5 |
| Direct migration count | 8 | 5 |

**Resolution**: Report 10 is more conservative and accurate. Report 08 counts theoretical equivalents; Report 10 counts feasible, low-risk migrations. The MASTER plan follows Report 10's count. **Recommendation**: Update Report 08's executive summary to align with Report 10.

### 11.2 Report 03 vs MASTER Plan: Shadow Mode

| Issue | Report 03 | MASTER Plan |
|---|---|---|
| Running both bots simultaneously | "Do not run both on same guild/channel simultaneously" | "Run both bot.py AND Hermes gateway in parallel" (Phase 2.10) |

**Resolution**: Report 03's warning is correct for naive parallel operation (both bots receiving the same Discord events). The MASTER plan's shadow mode requires webhook forwarding — Hermes receives forwarded copies of messages, not raw Discord events. This is feasible but requires explicit implementation that the MASTER plan doesn't detail. **Recommendation**: Add shadow mode architecture to the MASTER plan before Phase 2.

### 11.3 Report 03 vs Report 13: Hook System

| Issue | Report 03 | Report 13 |
|---|---|---|
| HARD STOP interception | "Unknown — must verify hook support" | Documents 7 hooks (`pre_prompt` through `on_error`) — none match the "pre_gateway_dispatch" name |
| Gateway-level hooks | "Unknown" | No gateway-level hooks documented |

**Resolution**: Report 03 correctly flagged this as unknown. Report 13 documented the actual hook system. The MASTER plan then invented hook names (`pre_gateway_dispatch`, `transform_llm_output`) that don't exist in either report. This is the most critical contradiction and must be resolved by re-mapping to the correct hook names.

### 11.4 MASTER Plan Section 2 vs Section 6: Hook Names

| Issue | Section 2 (Architecture Diagram) | Section 6 (Safety Mapping Detail) |
|---|---|---|
| HARD STOP hook | `pre_gateway_dispatch` | `pre_gateway_dispatch` |
| Yandere FSM hook | `transform_llm_output` | `transform_llm_output` |

**Resolution**: Both sections use the same invented hook names. The architecture diagram and the safety mapping table are internally consistent with each other but both are wrong relative to the actual Hermes hook system. Both need correction.

---

## 12. Assumptions Requiring Faiz Approval

These assumptions are embedded in the migration plan but have not been explicitly validated:

| # | Assumption | Risk if Wrong | Report Reference |
|---|---|---|---|
| A1 | Hermes `pre_tool_call` hook receives tool name and operation context | Auth matrix cannot enforce operation-level access | Report 10, Report 13 |
| A2 | Hermes Discord gateway can register 35 custom slash commands via plugin API | Only standard Hermes commands will be available | Report 03, Report 04 |
| A3 | Hermes `pre_response` hook can modify/rewrite response content (needed by yandere FSM for Y6→Y5 rewrite) | Yandere boundary enforcement fails silently | Report 13 |
| A4 | Hermes fallback mechanism supports custom providers (9Router) | Model failover breaks; needs custom plugin | Report 15 |
| A5 | Hermes native gateway's RBAC can replicate `is_faiz_interaction()` multi-condition guard | Authorization gaps in admin/surveillance commands | Report 03 |
| A6 | Shadow mode can be implemented via webhook forwarding (not raw Discord event sharing) | Cannot safely parallel-run both systems for parity testing | Report 03, MASTER Plan |
| A7 | 59% code reduction is directionally aspirational, not binding | Unrealistic expectations; timeline pressure to cut corners | MASTER Plan |
| A8 | Hermes plugins run with the same OS privileges as the agent process (no sandbox) — acceptable risk | Plugin bug = full process compromise | Report 16 |

---

## Appendix: Verification Methodology

### Files Verified

| File | Verification Method |
|---|---|
| `src/discord/bot.py` | Full read + `Measure-Object -Line` for line count + grep for HARD STOP, GUILD_ID, guild scoping |
| `src/discord/conversational_handler.py` | Full read + `Measure-Object -Line` for line count |
| `src/hermes/session_adapter.py` | Full read + `Measure-Object -Line` for line count |
| `src/hermes/memory_bridge.py` | Full read + `Measure-Object -Line` for line count |
| `src/discord/commands.py` | Read lines 126-249 for COMMAND_SPECS tuple; manual count of 35 entries |
| Dependency tree | `pip show ecdsa aiohttp pyjwt` — all 3 packages confirmed installed |

### Research Reports Verified

| Report | Verification |
|---|---|
| MASTER-RESTRUCTURE-PLAN.md | Line counts cross-checked against actual files; hook names cross-checked against Report 13 |
| 03-DISCORD-GATEWAY.md | Hook support flag ("Unknown") noted; used to flag MASTER plan inconsistency |
| 07-MEMORY-BRIDGE-GAP.md | Gap register cross-checked against session_adapter.py and memory_bridge.py source |
| 08-MCP-NATIVE.md | Tool mapping cross-checked against Report 10 for consistency |
| 10-MCP-MIGRATION-GAP.md | Tool count cross-checked against Report 08 |
| 13-HOOKS-AND-PLUGINS.md | Definitive source for actual Hermes hook names; used to validate MASTER plan mappings |
| 15-LLM-ROUTING.md | 9Router config verified against session_adapter.py |
| 16-SECURITY-POSTURE.md | Package presence verified via pip show |

### ADRs Verified

| ADR | Verification |
|---|---|
| ADR-005 | "9Router only, no OpenRouter" — confirmed no OpenRouter references in migration plan |
| ADR-007 | "PostgreSQL primary, no SQLite for canonical memory" — confirmed PostgreSQL remains primary; SQLite scope is transient |
| ADR-013 | "Guinevere MCP native replaces OpenCode" — confirmed Hermes migration operates at different layer |

---

## Footer

| Field | Value |
|---|---|
| Report ID | RR-ADR035-PREP-01 |
| Date | 2026-06-04 |
| Status | Complete |
| Validation Verdict | **4 PASS, 3 WARNING, 2 FAIL** |
| Critical Blockers | Hook name mismatch (#4), inflated line counts (#7) |
| Author | Guinevere (Sisyphus-Junior) |
| Next Action | Correct MASTER plan hook names; re-estimate code reduction; obtain Faiz approval on 8 assumptions |