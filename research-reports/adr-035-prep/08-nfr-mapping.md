# 08 — NFR Mapping: Hermes Migration Non-Functional Requirements

> **Purpose:** Map all 8 NFR categories to the Hermes NousResearch migration (v0.15.2). Define targets, measurement methods, and migration impact per NFR.
> **Generated:** 2026-06-04
> **Source:** MASTER-RESTRUCTURE-PLAN.md, Reports 03/15/16, ADRs 017/018/025/029, PROGRESS.md, ObservabilitySpec v1.0, SLO/SLA v1.0, SecurityPolicy v1.0
> **Status:** Complete — ready for ADR-035 integration

---

## Table of Contents

1. [Performance](#1-performance)
2. [Reliability](#2-reliability)
3. [Security](#3-security)
4. [Scalability](#4-scalability)
5. [Maintainability](#5-maintainability)
6. [Observability](#6-observability)
7. [Cost](#7-cost)
8. [Compatibility](#8-compatibility)
9. [Degradation Summary](#9-degradation-summary)
10. [Migration Phase Mapping](#10-migration-phase-mapping)
11. [Measurement Methods Reference](#11-measurement-methods-reference)

---

## 1. Performance

### 1.1 Response Latency

| Metric | Current Baseline | Post-Migration Target | Hermes Impact | Measurement Method |
|---|---|---|---|---|
| Discord message → first token | Not measured (no streaming) | **< 2s** | **IMPROVES** — streaming delivers first token immediately | `hermes gateway status` latency metrics; Prometheus `guinevere_llm_latency_seconds` histogram for p50 |
| Discord message → full response | Not measured (batch only) | **< 5s** | **IMPROVES** — progressive edit at ~1.2s intervals replaces full-batch wait | `hermes insights` timing breakdown; Prometheus `guinevere_llm_latency_seconds` histogram for p95 |
| HARD STOP interception | Not measured (< 1 message loop) | **< 50ms** | **NEUTRAL** — `pre_gateway_dispatch` hook fires before auth+dispatch, same pre-LLM position | Timestamp diff: message arrival → hook completion; Prometheus `guinevere_safe_word_events_total` latency bucket |
| Memory recall | p95 < 2s (ADR-009 benchmark) | **< 500ms** (warm) | **NEUTRAL** — PostgreSQL+pgvector unchanged as primary write authority; Hermes read-only supplement doesn't change recall path | `guinevere_memory_recall_duration_seconds` histogram (ObservabilitySpec §4.9) |
| Tool execution | Varies per tool (P6 benchmarks) | **No degradation** (within 10% of current) | **NEUTRAL** — 5 tools migrate to Hermes native, 7 stay custom, auth overlay adds negligible overhead | `hermes debug` per-tool timing; Prometheus per-tool duration metrics |

**Why streaming improves latency:** Current bot.py delivers the full response after all tokens are generated. Hermes native gateway delivers tokens progressively via Discord edit (~1.2s intervals, respecting 5 edits/5s Discord limit). This means Faiz sees content sooner — the first meaningful text appears well before the 2s target.

### 1.2 Throughput

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Messages per second | 1-2 (single-user Faiz, no scale concern) | **NEUTRAL** — neither system bottlenecks at single-user load | `hermes gateway status` message throughput |
| Concurrent sessions | 1 (single-user) | **NEUTRAL** — `group_sessions_per_user: true` isolates per-user sessions | `hermes gateway status` active sessions |

### 1.3 Resource Usage

| Metric | Constraint | Hermes Impact | Measurement |
|---|---|---|---|
| CPU | Shared VPS (4 cores, Guinevere allocated 2-3 cores) | **NEUTRAL** — same Python ecosystem, same LLM routing, less custom code | `guinevere_node_cpu_utilization_ratio` (ObservabilitySpec §4.3) |
| RAM | 8GB cgroup cap (P0-009) | **IMPROVES** — 59% code reduction (-5,528 lines) means fewer objects in memory; no separate bot.py process | `guinevere_node_memory_utilization_ratio` |
| Disk | Shared VPS disk | **IMPROVES** — Hermes built-in SQLite is lightweight supplement; PDF/ephemeral cache reduction from fewer custom processes | `guinevere_node_disk_utilization_ratio` |

### 1.4 Streaming

| Metric | Current | Post-Migration | Impact | Measurement |
|---|---|---|---|---|
| Progressive edit interval | None (batch) | ~1.2s, 5 edits/5s Discord limit | **IMPROVES** — streaming is a net-new capability | Manual UX testing; `hermes debug` streaming logs |

### 1.5 Performance Risk: Auth Overlay

| Risk | Mitigation |
|---|---|
| Auth matrix plugin adds latency to every tool call | Auth overlay is a `pre_tool_call` hook — metadata lookup only. READ_AUTO tools pass through with zero added latency. DESTRUCTIVE_APPROVAL adds webhook round-trip (acceptable for rare destructive ops). |

---

## 2. Reliability

### 2.1 Uptime

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Core service uptime | **99.5%** monthly (SLO/SLA §2.2 initial operational target) | **NEUTRAL** — single VPS constraint unchanged; Hermes gateway runs as systemd service like bot.py | `guinevere_systemd_unit_state` gauge (ObservabilitySpec §4.3); Grafana `guinevere-overview` dashboard |
| Long-term aspiration | 99.9% (BRD v2.0 business target) | **NEUTRAL** — requires dedicated monitoring VPS (post-MVP, per ADR-017) | Monthly SLO scorecard per SLO/SLA spec |
| Minimum floor | 99.0% — breach triggers mandatory postmortem | Same as above | Monthly scorecard |

### 2.2 Migration Uptime

| Phase | Downtime Target | Impact | Measurement |
|---|---|---|---|
| Shadow mode (Phase 2, 48hr+) | **Zero** — both bot.py and Hermes gateway run in parallel | **IMPROVES** — shadow mode guarantees no interruption | Side-by-side output comparison; parity report |
| Cutover (Phase 2, step 2.11) | **< 5 min** — disable bot.py, enable Hermes gateway exclusively | **NEUTRAL** — acceptable brief interruption with rollback available | `hermes gateway start` timing; manual Faiz verification |
| All other phases | **Zero** — no gateway restart needed for Phase 3-7 changes | **IMPROVES** — hooks/plugins loaded without gateway restart | `hermes gateway status` uptime timer |

### 2.3 Circuit Breaker & Fallback

| Mechanism | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Rate limit handling (429) | Auto-pause, exponential backoff | **IMPROVES** — Hermes has built-in circuit breaker vs custom implementation in bot.py | `hermes debug` rate-limit events; Prometheus `guinevere_llm_rate_limit_total` |
| LLM fallback (GPT-5.5 → DeepSeek V4 Flash) | Automatic on timeout/rate-limit/connection-error | **NEUTRAL** with GAP — Hermes `fallback` for custom providers is undocumented; may need custom plugin (Report 15 §3.2, Option B) | `hermes fallback` verification; manual fail test |
| 9Router entirely down | Both models fail → escalate to operator | **NEUTRAL** — same failure mode as current | `GuinevereServiceDown` SEV1 alert |
| DeepSeek V4 Flash also fails | Halt all LLM calls, notify operator | **NEUTRAL** — same escalation | `GuinevereLLMLatencyDegraded` SEV2/SEV3 alert |

### 2.4 Session Persistence

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| No session loss during gateway restart | Zero session loss | **IMPROVES** — Hermes native session management with `group_sessions_per_user: true` + PostgreSQL bridge for long-term storage; Redis DB4 elimination reduces failure surface | `hermes gateway restart` session continuity test; PostgreSQL session audit |
| Redis DB4 session TTL | Eliminated | **IMPROVES** — Hermes sessions do not depend on Redis 2hr TTL; PostgreSQL bridge provides durable storage | No Redis DB4 dependency post-migration |

### 2.5 Reliability Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Hermes native fallback doesn't work with custom provider (9Router) | **Medium** | Implement custom plugin fallback (Report 15 §3.2 Option B); test before cutover |
| Discord gateway instability after cutover | **Low** | 48hr+ shadow mode; circuit breaker; manual rollback to bot.py in < 5 min |
| Performance regression > 10% | **Low** | Phase 7 benchmark; rollback via `hermes checkpoints` |

---

## 3. Security

### 3.1 Vulnerability Remediation (BLOCKER — Phase 0)

| Target | Current State | Required State | Hermes Impact | Measurement |
|---|---|---|---|---|
| HIGH severity | 1 (ecdsa timing attack) | 0 HIGH | **DEGRADES** (initially) — Hermes carries 11 vulns; Phase 0 must remediate before migration | `hermes security` → 0 HIGH |
| MODERATE severity | 4 (aiohttp x2, pip x2) | 0 MODERATE | **DEGRADES** (initially) — must upgrade aiohttp + add `--require-hashes` | `hermes security` → 0 MODERATE |
| UNKNOWN (PyJWT x4) | 4 UNKNOWN | 0 UNKNOWN → triaged to 0 or accepted | **DEGRADES** (initially) — triage needed; may not affect Guinevere if PyJWT unused internally | `hermes security` output; dependency tree analysis |
| `hermes doctor` | Not passing (missing .env, config path) | All checks pass | Pre-migration prerequisite | `hermes doctor` → clean |

### 3.2 Auth Matrix

| Target | Current State | Post-Migration State | Hermes Impact | Measurement |
|---|---|---|---|---|
| READ_AUTO enforcement | 100% on all 16 tools | 100% via auth overlay plugin | **NEUTRAL** — Hermes has no auth level concept; custom plugin wraps `pre_tool_call` to enforce all 4 levels | Plugin integration test: READ_AUTO tools pass through, non-READ_AUTO blocked |
| WRITE_NOTIFY enforcement | 100% | 100% via auth overlay plugin | **NEUTRAL** — plugin sends Discord notification + allows | WRITE_NOTIFY test: notification sent |
| DESTRUCTIVE_APPROVAL | 100% | 100% via auth overlay + Discord webhook (5-min timeout) | **NEUTRAL** — plugin blocks + webhook approval flow | DESTRUCTIVE_APPROVAL test: webhook sent, approval works |
| FORBIDDEN enforcement | 100% | 100% via auth overlay plugin | **NEUTRAL** — plugin blocks + logs | FORBIDDEN test: tool blocked |
| Auth overlay bypass | Zero bypasses | Zero bypasses | Risk: plugin disabled → all auth lost. Mitigation: `pre_tool_call` hook on_failure=block (fail-closed) | Security audit: auth overlay cannot be bypassed |

### 3.3 Consent Gate

| Target | Hermes Impact | Measurement |
|---|---|---|
| **Fail-closed** — WITHDRAWN blocks ALL tool calls, zero bypasses | **NEUTRAL** — consent gate ported to `pre_tool_call` hook; same fail-closed behavior, same Redis DB2 + PostgreSQL backend | AC-SAFE-003: withdraw consent → all tool calls in 16-tool matrix blocked |
| Consent state integrity | **NEUTRAL** — PostgreSQL consent_ledger unchanged; Hermes hooks read from same source | Consent gate test: Redis DB2 cache + PostgreSQL authoritative |

### 3.4 Secret Scanner

| Target | Hermes Impact | Measurement |
|---|---|---|
| Zero credential leaks in responses | **IMPROVES** — secret scanner ported to `transform_llm_output` hook + Hermes secrets encryption for API keys (currently plaintext .env) | Credential leak test: simulated secret in output → redacted |
| API key storage | **IMPROVES** — `hermes secrets` encrypts at rest vs current plaintext .env | `hermes secrets list` → encrypted; `hermes secrets get` → requires auth |

### 3.5 Data Classification

| Target | Hermes Impact | Measurement |
|---|---|---|
| Fail-closed for unknown data | **NEUTRAL** — classification plugin unchanged, ported to memory plugin | Classification test: unclassified Critical → fails closed without sanitized_summary |
| 5-level classification enforced | **NEUTRAL** — PostgreSQL schema unchanged (47 tables, 12 schemas, 5 levels) | Classification audit: all paths enforce classification ceiling |

### 3.6 HARD STOP

| Target | Hermes Impact | Measurement |
|---|---|---|
| **100% SLO, zero tolerance** — any miss is SEV0 | **NEUTRAL** — `pre_gateway_dispatch` hook returns `{action: "skip"}` before auth+dispatch, matching current `_on_message_listener` position | `GuinevereSafeWordBypassDetected` SEV0 alert; manual "HARD STOP" test: neutral response, no LLM call, no persona |
| Interception latency | **< 50ms** (same as Performance §1.1) | Timestamp diff: message arrival → hook skip-action |

### 3.7 Combined Security Posture

| Domain | Hermes Alone | Hermes + Guinevere Security | Impact |
|---|---|---|---|
| API key storage | Good (encrypted) | Good (encrypted) | **IMPROVES** |
| API key pooling | Good (multi-key) | Good (multi-key) | **IMPROVES** |
| Consent enforcement | None | Strong (fail-closed) | **NEUTRAL** (ported) |
| Credential leak prevention | None | Strong (regex scanner) | **NEUTRAL** (ported) |
| Persona integrity (drift) | None | Strong (SHA-256) | **NEUTRAL** (ported) |
| HARD STOP | None | Strong (pre-LLM gate) | **NEUTRAL** (ported) |
| Budget enforcement | None | Adequate (hook-based) | **NEUTRAL** (ported, with gap) |
| Dependency vulns | Moderate (11 vulns) | Improved (remediated) | **DEGRADES** initially → **IMPROVES** after Phase 0 |
| Backup/recovery | Good | Good | **IMPROVES** (hermes backup + checkpoints added) |

---

## 4. Scalability

### 4.1 Current Scale

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Concurrent users | 1 (Faiz only) | **NEUTRAL** — no scaling needed; single-user design unchanged | N/A (single-user) |
| Session concurrency | 1-2 sessions max | **NEUTRAL** — `group_sessions_per_user: true` isolates per-user without adding overhead | `hermes gateway status` session count |
| Discord guilds | 1 (Guinevere's Domain) | **NEUTRAL** — single guild config unchanged | `hermes gateway list` |
| Discord channels | 13 (P2-006) | **NEUTRAL** — channel_prompts configurable per-channel | `hermes gateway setup` channel allowlist |

### 4.2 Memory Growth

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| PostgreSQL memory growth | Unlimited (47 tables, 12 schemas handle unbounded growth) | **IMPROVES** — Hermes compression (50%/20%) reduces context window pressure; PostgreSQL remains primary write authority | `guinevere_postgres_connections_active`; TimescaleDB hypertable growth |
| Hermes SQLite | N/A (read-only supplement) | **NEUTRAL** — Hermes built-in SQLite for session search is lightweight, no scaling concern | `hermes session_search` response times |

### 4.3 Future Multi-Channel (ADR-022)

| Channel | Hermes Impact | Readiness |
|---|---|---|
| Discord (primary) | **IMPROVES** — native gateway vs custom bot.py; no scaling concern at single-user | Production-ready |
| WhatsApp (secondary, ADR-022) | **IMPROVES** — Hermes multi-platform gateway supports WhatsApp via BAW (Baileys WebSocket) natively | Future (P11, not part of migration) |

---

## 5. Maintainability

### 5.1 Code Reduction

| Metric | Current | Post-Migration | Impact | Measurement |
|---|---|---|---|---|
| Total lines of custom code | ~9,378 lines | ~3,850 lines | **IMPROVES** — **59% reduction (-5,528 lines)** | `wc -l` on eliminated files: bot.py (603), conversational_handler.py (614), session_adapter.py (366), MCP manager (1,800), memory bridge (145), persona files (2,000) |
| Files eliminated | 5 major files + 33 command handlers | bot.py, conversational_handler.py, session_adapter.py, commands.py, MCP manager partial | **IMPROVES** — maintenance burden reduced | File count audit post-migration |

### 5.2 Framework Updates

| Operation | Current | Post-Migration | Impact | Measurement |
|---|---|---|---|---|
| Dependency update | Manual `pip install -r requirements.txt` across custom files | `hermes update` — single command | **IMPROVES** — centralized update, no manual tracking | `hermes update` success |
| Version pinning | Manual requirements.txt | Hermes manages own deps; Guinevere plugins pinned with hashes | **IMPROVES** | `hermes doctor` version check |
| Rollback | Manual git revert + restart | `hermes checkpoints` — create/restore named snapshots | **IMPROVES** | `hermes checkpoints restore` within 60s |

### 5.3 Debugging & Diagnostics

| Tool | Current | Hermes | Impact |
|---|---|---|---|
| Health check | Custom FastAPI /health endpoint | `hermes doctor` — environment + config + dependency checks | **IMPROVES** — unified diagnostic |
| Debug mode | `GUINEVERE_DEBUG=1` env var | `hermes debug` — verbose logging mode | **IMPROVES** — standardized |
| State dump | Manual log grep | `hermes dump` — full system state export | **IMPROVES** — structured state snapshot |
| Log access | Systemd journalctl | `hermes logs` — agent.log, errors.log, gateway.log | **IMPROVES** — categorized log files |

### 5.4 Configuration

| Aspect | Current | Post-Migration | Impact | Measurement |
|---|---|---|---|---|
| Config format | Multiple files (config.yaml, .env, session_adapter.py hardcoded) | Single `config.yaml` + SOPS-encrypted secrets via `hermes secrets` | **IMPROVES** — unified config surface | `hermes config` validation; single source of truth |
| Secret management | Plaintext `.env` file | `hermes secrets` encrypted at rest | **IMPROVES** — encryption, key rotation support | `hermes secrets list` → encrypted |

### 5.5 Skills Ecosystem

| Capability | Current | Post-Migration | Impact |
|---|---|---|---|
| Community skills | None (all custom) | `agentskills.io` — search, install, curate | **IMPROVES** — access to community-maintained skills |
| Skill management | Manual | `hermes curator` — update, version, dependency resolution | **IMPROVES** — automated lifecycle |

---

## 6. Observability

### 6.1 Logging

| Metric | Current | Hermes | Impact | Measurement |
|---|---|---|---|---|
| Structured logs | Loki + Promtail + journalctl (P8) | `hermes logs` (agent.log, errors.log, gateway.log) | **IMPROVES** — additional categorized log files supplement Loki | `hermes logs --level error` count; Loki query parity |
| Log levels | Python logging levels | `hermes logs` severity filtering | **NEUTRAL** — equivalent capability | Log filtering test |
| Log redaction | Sentry scrubber + classification-aware logging | Same (Sentry unchanged) + Hermes `hermes debug` may expose data → must verify | **DEGRADES risk** — `hermes debug` verbose mode needs PII audit | `hermes debug` output scan for secrets/PII |

### 6.2 Metrics

| Metric | Current | Hermes | Impact | Measurement |
|---|---|---|---|---|
| Prometheus metrics | All `guinevere_*` metrics per ObservabilitySpec | Unchanged — Prometheus scrapes same services | **NEUTRAL** | `guinevere_llm_requests_total`, `guinevere_loop_state`, etc. |
| Token/cost tracking | `cost_tracker.py` → Redis DB5 | `hermes insights` + `cost_tracker.py` for enforcement | **IMPROVES** — dual visibility: real-time insights + budget enforcement | `hermes insights` output; Prometheus `guinevere_llm_cost_usd_total` |
| Gateway metrics | Limited (bot.py internal) | `hermes gateway status` — uptime, throughput, sessions | **IMPROVES** — dedicated gateway observability | `hermes gateway status` |

### 6.3 Monitoring (ADR-017)

| Component | Current | Post-Migration | Impact |
|---|---|---|---|
| Prometheus | Docker, 15s scrape, 7 jobs | **Unchanged** — same scrape config, same targets | **NEUTRAL** |
| Grafana | Docker, 12 dashboards as-code | **Unchanged** — same dashboards, same provisioning | **NEUTRAL** |
| Loki + Promtail | Docker, 720h retention | **Unchanged** — same log pipeline | **NEUTRAL** |

### 6.4 Alerting

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| SEV0 delivery | Discord + Gotify urgent, immediate | **NEUTRAL** — Alertmanager unchanged | `GuinevereSafeWordBypassDetected` synthetic test |
| Post-migration monitoring (first 7 days) | Response latency <2x baseline, error rate <5%, budget within 20% baseline, HARD STOP 100% | **NEUTRAL** — same alert thresholds, same routes | Master Plan §9 "Post-Migration Monitoring" thresholds |
| New alert needed | Hermes gateway down | **IMPROVES** — need `GuinevereHermesGatewayDown` alert | Alertmanager rule: `hermes gateway status` → down |

### 6.5 Backup & Recovery (ADR-025)

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Backup creation | Daily (ADR-025 formal policy) | **IMPROVES** — `hermes backup` for agent state + `hermes checkpoints` for rollback points | `guinevere_backup_last_success_timestamp_seconds` |
| Restore drill | Monthly (ADR-025) | **NEUTRAL** — same requirement, Hermes adds checkpoint restore | `guinevere_restore_drill_last_success_timestamp_seconds` |
| Backup targets | PostgreSQL + config + secrets + agent state | **IMPROVES** — Hermes adds session state, skills state, gateway config | `hermes backup` creates successfully |

---

## 7. Cost

### 7.1 Budget

| Metric | Target | Hermes Impact | Measurement |
|---|---|---|---|
| Monthly LLM budget | **$30/mo hard cap** | **NEUTRAL** with GAP — Hermes `insights` tracks but does NOT enforce. Budget enforcement requires custom `pre_tool_call` hook (Report 15 §3.3) | `hermes config set budget.monthly_limit 30.00` + budget_check hook; Prometheus `guinevere_llm_cost_usd_total` |
| Budget alert threshold | 80% ($24) | **NEUTRAL** — same threshold via budget_check hook | `GuinevereLLMCostSpike` SEV2 alert |
| Hard cap behavior | Block all LLM calls at $30 | **NEUTRAL** — hook returns `{action: "block"}` on budget exceeded | Budget enforcement test: $29.99 → allowed; $30.01 → blocked |

### 7.2 Cost Visibility

| Metric | Hermes Impact | Measurement |
|---|---|---|
| Per-request token tracking | **IMPROVES** — `hermes insights` provides aggregated view; `cost_tracker.py` kept for per-request granularity and enforcement | `hermes insights` output; Redis DB5 cost keys |
| Per-model cost breakdown | **IMPROVES** — `hermes insights` shows per-model (GPT-5.5 vs DeepSeek V4 Flash) | `hermes insights --json` (if supported) |
| Historical cost data | **NEUTRAL** — PostgreSQL historical audit trail unchanged | PostgreSQL cost tracking queries |

### 7.3 Infrastructure Cost

| Component | Current Cost | Post-Migration Cost | Impact |
|---|---|---|---|
| VPS (hostdata.id 4C/16GB) | Existing (shared) | Existing (shared) | **NEUTRAL** |
| Hermes license | $0 (open-source) | $0 | **NEUTRAL** |
| Total infrastructure | Part of $30/mo total | Part of $30/mo total | **NEUTRAL** |

### 7.4 Cost Risk: Budget Enforcement Gap

| Risk | Severity | Mitigation |
|---|---|---|
| Hermes has no native budget enforcement | **High** — without the hook, costs could exceed $30/mo | Implement budget_check hook before Phase 6 cutover; test at 80%, 90%, 100% thresholds |

---

## 8. Compatibility

### 8.1 ADR-007: PostgreSQL Primary Memory

| Requirement | Hermes Impact | Measurement |
|---|---|---|
| PostgreSQL + pgvector is **primary write authority** for all memory | **NEUTRAL** — Hermes built-in SQLite is read-only supplement only. Hybrid mode (Option C from Report 07) preserves PostgreSQL write path | Memory write test: data written to PostgreSQL, NOT Hermes SQLite |
| Hermes compression/session-search is read-only | **NEUTRAL** — no writes to Hermes memory; no risk of data loss or drift | `hermes session_search` returns PostgreSQL data, no duplicate stores |

### 8.2 ADR-013: Guinevere MCP Native

| Requirement | Hermes Impact | Measurement |
|---|---|---|
| Guinevere MCP native replaces opencode | **NEUTRAL** — Hermes MCP is compatible extension, not replacement. 5 tools migrate to Hermes native MCP, 7 remain custom | All 16 tool capabilities available post-migration |
| Auth matrix preserved | **NEUTRAL** — custom auth overlay plugin wraps all tool calls | Auth matrix test: 4 levels enforced on all 16 tools |

### 8.3 ADR-005: 9Router Only

| Requirement | Hermes Impact | Measurement |
|---|---|---|
| All LLM routing through 9Router (localhost:20128) | **NEUTRAL** — Hermes configured with `base_url: http://localhost:20128/v1` as OpenAI-compatible custom provider | `hermes model show` → provider: custom, base_url: localhost:20128 |
| No OpenRouter, no direct API | **NEUTRAL** — Hermes custom provider config respects this; 9Router is sole route | LLM request audit: all requests to localhost:20128 |
| GPT-5.5 primary, DeepSeek V4 Flash fallback | **NEUTRAL** — Hermes `fallback` config (or custom plugin if native unsupported) | Model routing test: GPT-5.5 primary, DeepSeek on failure |

### 8.4 ADR-022: Discord Primary, WhatsApp Secondary

| Requirement | Hermes Impact | Measurement |
|---|---|---|
| Discord as primary communication channel | **IMPROVES** — Hermes native Discord gateway with streaming, RBAC, auto-threading | All 33 slash commands functional; streaming active |
| WhatsApp as secondary (future P11) | **IMPROVES** — Hermes multi-platform gateway natively supports WhatsApp via BAW (Baileys WebSocket) | Future: `hermes gateway setup` → WhatsApp configured |

### 8.5 Other ADR Compatibilities

| ADR | Requirement | Hermes Impact |
|---|---|---|
| ADR-017 (Monitoring) | Prometheus + Grafana on primary VPS | **NEUTRAL** — monitoring stack unchanged |
| ADR-018 (Defense-in-Depth) | 7-layer security architecture | **NEUTRAL** — all layers preserved; Hermes adds `hermes security`, `hermes secrets` |
| ADR-025 (Backup/DR) | Formal backup policy with restore validation | **IMPROVES** — `hermes backup` + `hermes checkpoints` add agent-state backup |
| ADR-029 (Self-Modification) | Automated testing with safety-gated rollback | **NEUTRAL** — Hermes hooks don't change the SDLC loop; `hermes checkpoints` improve rollback speed |
| ADR-015 (Secrets) | SOPS + age encryption | **IMPROVES** — additional `hermes secrets` encryption layer for API keys |

---

## 9. Degradation Summary

### 9.1 NFRs That DEGRADE (Require Mitigation)

| NFR | Degradation | Severity | Mitigation | Phase |
|---|---|---|---|---|
| **Security: Dependency vulnerabilities** | 11 known vulns (1 HIGH, 4 MODERATE) introduced by Hermes | **HIGH** — blocks any migration | Phase 0 remediation: upgrade aiohttp, add --require-hashes, triage PyJWT | Phase 0 |
| **Security: Budget enforcement** | Hermes lacks native budget enforcement; $30/mo cap not enforced by framework | **HIGH** — risk of cost overrun | Implement budget_check hook via `pre_tool_call` (Report 15 §3.3) | Phase 6 |
| **Reliability: LLM fallback** | Hermes `fallback` for custom providers is undocumented; may not work with 9Router | **MEDIUM** — fallback chain may break | Test native fallback first; if unsupported, implement custom plugin (Report 15 §3.2 Option B) | Phase 6 |
| **Observability: Debug verbosity** | `hermes debug` may expose PII/secrets in verbose output | **LOW** — only in debug mode | Audit `hermes debug` output for secrets; add to Sentry scrubber | Phase 7 |
| **Security: Plugin sandboxing** | Hermes plugins run in-process with full privileges | **LOW** — defense-in-depth concern | OS-level isolation (dedicated user, cgroup limits), plugin code review, signed plugins | Phase 1 |

### 9.2 NFRs That IMPROVE

| NFR | Improvement | Confidence |
|---|---|---|
| **Performance: Streaming** | First token delivery, progressive edits — net-new capability | HIGH |
| **Performance: Resource usage** | 59% code reduction means fewer objects, less memory | HIGH |
| **Maintainability: Code reduction** | -5,528 lines (59%), 5 major files eliminated | HIGH |
| **Maintainability: Framework management** | `hermes update`, `hermes doctor`, `hermes checkpoints` | HIGH |
| **Maintainability: Secrets management** | `hermes secrets` encrypted at rest vs plaintext .env | HIGH |
| **Observability: Backup/Recovery** | `hermes backup` + `hermes checkpoints` for agent state | MEDIUM |
| **Cost: Visibility** | `hermes insights` for real-time cost visibility | MEDIUM |
| **Compatibility: Multi-channel** | Hermes native WhatsApp support for future P11 | MEDIUM (future) |
| **Reliability: Session persistence** | No Redis DB4 dependency; PostgreSQL bridge for durability | HIGH |
| **Security: API key pooling** | Multi-key rotation via `hermes auth` | MEDIUM |

### 9.3 NFRs That Are NEUTRAL

| NFR | Reason |
|---|---|
| HARD STOP interception | Same pre-LLM position via `pre_gateway_dispatch` hook |
| Consent gate | Same Redis DB2 + PostgreSQL backend, same fail-closed behavior |
| Auth matrix | Custom plugin enforces all 4 levels; same behavior |
| Memory recall | PostgreSQL+pgvector unchanged as primary write authority |
| 9Router routing | Unchanged — Hermes is just a client config pointing to localhost:20128 |
| Prometheus/Grafana/Loki | Monitoring stack unchanged |
| Uptime | Same single VPS constraint |
| Budget cap | Same $30/mo enforced via custom hook |
| Single-user scaling | No change needed |

---

## 10. Migration Phase Mapping

Each NFR is affected by specific migration phases:

| Phase | Phase Name | NFRs Affected | NFRs NOT Affected |
|---|---|---|---|
| **Phase 0** | Security Remediation | **Security** (vulns), **Compatibility** (blocker gate) | Performance, Scalability, Cost |
| **Phase 1** | Safety Foundation | **Security** (all 15+ safety features ported), **Performance** (HARD STOP latency) | Cost, Scalability |
| **Phase 2** | Discord Gateway Migration | **Performance** (streaming, latency), **Reliability** (shadow mode, cutover downtime), **Maintainability** (code elimination) | Security, Cost |
| **Phase 3** | Memory Bridge Enhancement | **Performance** (recall latency), **Scalability** (memory growth), **Compatibility** (ADR-007) | Cost |
| **Phase 4** | Tool/MCP Migration | **Security** (auth overlay), **Performance** (tool latency) | Cost, Scalability |
| **Phase 5** | Skills & Persona | **Maintainability** (skills ecosystem) | Security, Performance, Cost |
| **Phase 6** | LLM Routing & Budget | **Cost** (budget enforcement, insights), **Reliability** (fallback chain), **Compatibility** (ADR-005) | Scalability |
| **Phase 7** | Hardening & Monitoring | **Observability** (new alerts, debug audit), **Reliability** (benchmark), **Security** (final audit) | Cost |

---

## 11. Measurement Methods Reference

### 11.1 Automated Measurement Tools

| Measurement | Tool/Command | Source |
|---|---|---|
| Response latency | `hermes gateway status` + Prometheus `guinevere_llm_latency_seconds` | ObservabilitySpec §4.7 |
| HARD STOP latency | Timestamp diff: message → hook completion; Prometheus histogram | Custom instrumentation |
| Memory recall latency | Prometheus `guinevere_memory_recall_duration_seconds` | ObservabilitySpec §4.9 |
| CPU/RAM/Disk | Prometheus `guinevere_node_*` metrics | ObservabilitySpec §4.3 |
| Uptime | Prometheus `guinevere_systemd_unit_state` | ObservabilitySpec §4.3 |
| Vulnerability count | `hermes security` | Report 16 §1.1 |
| Dependency health | `hermes doctor` | Report 16 §2.1 |
| API key storage | `hermes secrets list` | Report 16 §8.2 |
| Budget enforcement | `hermes config` + budget_check hook | Report 15 §3.3 |
| Token/cost tracking | `hermes insights` + Redis DB5 cost keys | Report 15 §2.5 |
| Code line count | `wc -l` on eliminated/modified files | Master Plan §2 |
| Backup freshness | Prometheus `guinevere_backup_last_success_timestamp_seconds` | ObservabilitySpec §4.11 |
| Restore drill | `guinevere_restore_drill_last_success_timestamp_seconds` | ObservabilitySpec §4.11 |

### 11.2 Manual Verification Tests

| Measurement | Test Method | Source |
|---|---|---|
| auth matrix enforcement | Integration test: 16 tools × 4 levels = 64 assertions | P6-018 |
| Consent gate fail-closed | AC-SAFE-003: withdraw consent → all tools blocked | Report 14 §5.2 |
| HARD STOP interception | "HARD STOP" message → neutral response, no LLM call | P4-017 |
| Secret scanner | Simulated credential in output → redacted | Report 14 §5.10 |
| Classification fail-closed | Unclassified Critical → blocked without sanitized_summary | P3-009 |
| Fallback chain | Simulate GPT-5.5 failure → DeepSeek activates | Report 15 §6 |
| Shadow mode parity | 48hr parallel run, compare outputs | Master Plan §4 |
| Streaming delivery | Progressive edits visible, ~1.2s intervals | Manual UX |
| `hermes debug` PII audit | Scan debug output for secrets, safe-word, intimate content | Report 16 §9.3 |

### 11.3 Post-Migration Monitoring (First 7 Days)

| Metric | Threshold | Alert | Source |
|---|---|---|---|
| Response latency | < 2× current average | Discord #ops | Master Plan §9 |
| Safety feature trigger rate | Within 20% of baseline | Discord #ops | Master Plan §9 |
| Error rate | < 5% of messages | Discord #ops | Master Plan §9 |
| Budget consumption | Within 20% of baseline | Discord #ops | Master Plan §9 |
| Memory recall relevance | Manual spot-check 20 queries | Faiz review | Master Plan §9 |
| HARD STOP success rate | 100% (zero tolerance) | Immediate alert | Master Plan §9 |

---

## Appendix A: NFR Impact Summary Matrix

| NFR Category | Sub-Category | Impact | Confidence | Phase |
|---|---|---|---|---|
| **Performance** | Streaming latency | IMPROVES | HIGH | Phase 2 |
| **Performance** | Resource usage (RAM, CPU) | IMPROVES | HIGH | Phase 2 |
| **Performance** | HARD STOP latency | NEUTRAL | MEDIUM | Phase 1 |
| **Performance** | Memory recall latency | NEUTRAL | HIGH | Phase 3 |
| **Performance** | Tool execution latency | NEUTRAL | MEDIUM | Phase 4 |
| **Reliability** | Shadow mode uptime | IMPROVES | HIGH | Phase 2 |
| **Reliability** | Cutover downtime | NEUTRAL | HIGH | Phase 2 |
| **Reliability** | LLM fallback chain | DEGRADES (gap) | MEDIUM | Phase 6 |
| **Reliability** | Session persistence | IMPROVES | HIGH | Phase 2 |
| **Security** | Dependency vulns | DEGRADES → IMPROVES | HIGH | Phase 0 |
| **Security** | Auth matrix | NEUTRAL | HIGH | Phase 4 |
| **Security** | Consent gate | NEUTRAL | HIGH | Phase 1 |
| **Security** | Secret scanner | IMPROVES | HIGH | Phase 1 |
| **Security** | API key encryption | IMPROVES | HIGH | Phase 6 |
| **Security** | HARD STOP | NEUTRAL | HIGH | Phase 1 |
| **Scalability** | Single-user | NEUTRAL | HIGH | All |
| **Scalability** | Memory growth | IMPROVES | MEDIUM | Phase 3 |
| **Scalability** | Multi-channel (future) | IMPROVES | MEDIUM | Future |
| **Maintainability** | Code reduction | IMPROVES | HIGH | Phase 2-5 |
| **Maintainability** | Framework updates | IMPROVES | HIGH | All |
| **Maintainability** | Debugging/diagnostics | IMPROVES | HIGH | Phase 7 |
| **Maintainability** | Configuration unification | IMPROVES | HIGH | Phase 0-2 |
| **Maintainability** | Skills ecosystem | IMPROVES | MEDIUM | Phase 5 |
| **Observability** | Logging | IMPROVES | MEDIUM | Phase 7 |
| **Observability** | Metrics | NEUTRAL | HIGH | Phase 7 |
| **Observability** | Monitoring stack | NEUTRAL | HIGH | All |
| **Observability** | Backup/recovery | IMPROVES | MEDIUM | Phase 7 |
| **Observability** | Debug PII risk | DEGRADES (risk) | LOW | Phase 7 |
| **Cost** | Budget enforcement | DEGRADES (gap) | HIGH | Phase 6 |
| **Cost** | Cost visibility | IMPROVES | MEDIUM | Phase 6 |
| **Cost** | Infrastructure cost | NEUTRAL | HIGH | All |
| **Compatibility** | ADR-007 (PostgreSQL) | NEUTRAL | HIGH | Phase 3 |
| **Compatibility** | ADR-013 (MCP) | NEUTRAL | HIGH | Phase 4 |
| **Compatibility** | ADR-005 (9Router) | NEUTRAL | HIGH | Phase 6 |
| **Compatibility** | ADR-022 (Discord/WhatsApp) | IMPROVES | HIGH | Phase 2 + Future |

### Totals

| Impact | Count |
|---|---|
| IMPROVES | 17 |
| NEUTRAL | 18 |
| DEGRADES (requires mitigation) | 4 |
| DEGRADES → IMPROVES (phased) | 1 |

**Net assessment:** The migration improves 17 NFRs, keeps 18 neutral, and degrades 4 (all with documented mitigations). The 1 phased item (security vulnerabilities) starts degraded but improves after Phase 0 remediation. **No NFR is permanently degraded without mitigation.**

---

## Appendix B: Source Document Traceability

| Document | NFR Categories Informed |
|---|---|
| `MASTER-RESTRUCTURE-PLAN.md` | Performance, Reliability, Maintainability, Phase mapping |
| `03-DISCORD-GATEWAY.md` | Performance (streaming), Reliability (shadow mode, cutover) |
| `15-LLM-ROUTING.md` | Reliability (fallback), Cost (budget enforcement gap) |
| `16-SECURITY-POSTURE.md` | Security (vulns, auth, secrets), Observability (debug audit) |
| `ADR-017-monitoring-stack-selection.md` | Observability (Prometheus, Grafana) |
| `ADR-018-security-architecture-defense-in-depth.md` | Security (defense layers) |
| `ADR-025-backup-disaster-recovery-strategy.md` | Reliability (backup/DR), Observability (backup metrics) |
| `ADR-029-self-modification-automated-testing.md` | Compatibility (self-modification rollback) |
| `40-ObservabilityAlertingSpec_v1.0.md` | Observability (metrics, alerts, dashboards) |
| `41-SLO_SLA_ErrorBudget_v1.0.md` | Reliability (uptime SLO targets) |
| `20-SecurityPolicy_v1.0.md` | Security (defense-in-depth, safety-first ordering) |
| `PROGRESS.md` | Cost (budget), Performance (P3/P6 benchmarks), Scalability (single-user) |

---

> **End of NFR Mapping Report** — All 8 categories mapped with measurable targets, measurement methods, impact assessment, and migration phase assignment. Ready for ADR-035 integration.