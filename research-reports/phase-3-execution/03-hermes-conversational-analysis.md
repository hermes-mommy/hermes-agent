# Hermes Conversational Quality &amp; Session State Analysis

**Date:** 2026-06-05  
**VPS:** guinevere-vps (100.94.104.22)  
**Inspector:** Sisyphus-Junior  
**Phase:** 3 — Memory Bridge Migration pre-assessment  
**Report ID:** RPT-03-HERMES-CONV-20260605

---

## 1. Executive Summary

Hermes is operational on the VPS with a single Discord user (Ssnford) actively conversing as of today. The gateway is unstable (13+ restarts observed), the **Phase 3 PostgreSQL memory migration has NOT been started** (no `guinevere_memory` database, no tables, no `pgvector`), and the memory bridge is partially functional with embedding always falling back to keyword (producing zero semantic recall results). Conversation quality is good when running: 85% prefix cache hit rate, avg 5.3s response time, coherent multi-turn exchanges. However, the system lacks any persistent memory storage beyond Hermes' native SQLite session state.

---

## 2. Session Data

### 2.1 Storage: SQLite (`state.db`)

| Metric | Value |
|---|---|
| Database | `/home/guinevere/.hermes/state.db` |
| Size | 106 KB (+ 1.3 MB WAL) |
| Sessions table | 2 rows |
| Messages table | 26 rows |
| FTS indexes | FTS5 (default + trigram) |

### 2.2 Session Records

| Session ID | Source | User | Model | Title | Msgs | Tokens (in/out) | Status |
|---|---|---|---|---|---|---|---|
| `20260605_102308_b4846761` | discord | `1146...4264` | deepseek-v4-flash | Child Asking for Mommy's Help | 11 | 23,477 / 891 | Active |
| `20260605_092059_6dc1af91` | discord | `1146...4264` | deepseek-v4-flash | Mommy Offering Help | 15 | 21,118 / 536 | Ended (session_reset) |

### 2.3 Message Distribution

| Role | Count | Avg Content Length |
|---|---|---|
| user | 14 | 18.4 chars |
| assistant | 10 | 270.5 chars |
| session_meta | 2 | 0 chars |

### 2.4 Message Metadata Sample (most recent 10)

All messages are text-only, zero tool calls (`tool_name` is empty for all 26). Session pattern: user → assistant alternating pairs, with `session_meta` marker on session start.

| Msg ID | Session Fragment | Role | Content Len | Unix Timestamp |
|---|---|---|---|---|
| 26 | `...b4846761` | assistant | 590 | 1780630014 |
| 25 | `...b4846761` | user | 48 | 1780630014 |
| 24 | `...b4846761` | assistant | 573 | 1780629976 |
| 23 | `...b4846761` | user | 34 | 1780629976 |
| 22 | `...b4846761` | assistant | 235 | 1780629881 |
| 21 | `...b4846761` | user | 18 | 1780629881 |
| 20 | `...b4846761` | assistant | 160 | 1780629857 |
| 19 | `...b4846761` | user | 40 | 1780629857 |
| 18 | `...b4846761` | session_meta | 0 | 1780629823 |
| 17 | `...b4846761` | assistant | 60 | 1780629823 |

### 2.5 Sessions JSON File

| File | Size | Keys |
|---|---|---|
| `/home/guinevere/.hermes/sessions/sessions.json` | 1,326 bytes | 1 active session |
| `/home/guinevere/.hermes/sessions/request_dump_20260605_092059_*.json` | 68,762 bytes | Cold dump from terminated session |

Session JSON structure: `session_key`, `session_id`, `created_at`, `updated_at`, `display_name`, `platform`, `chat_type`, token counters, cost tracking, `origin` (platform/chat details).

---

## 3. Redis Session Data

| Attribute | Value |
|---|---|
| Port | `127.0.0.1:6380` |
| Auth | ACL-based (6 users: admin, core, session, cache, scheduler, surveillance) |
| DB5 (cost tracking) | 11 keys |
| DB4 (surveillance) | NOT ACCESSIBLE (requires ACL auth — SOPS-encrypted passwords) |
| DB1 (sessions) | NOT ACCESSIBLE (requires ACL auth) |
| Data size | ~4 KB on disk |

**Note:** `MEMORY_BACKEND=redis` is set in `.env`, but Redis ACL prevents unauthenticated access. The `guinevere_session` ACL user is intended for DB1. Session keys could not be enumerated without SOPS decryption of `/home/guinevere/secrets/redis-acl-passwords.yaml`.

**Redis Cost Tracking Keys (DB5):**

| Key | Value |
|---|---|
| `budget:monthly_cap` | 30.00 |
| `budget:daily_alert` | 1.00 |
| `budget:warning_threshold` | 15.00 |
| `budget:critical_threshold` | 25.00 |
| `budget:hard_stop` | 30.00 |
| `cost:current_month` | 0.00 |
| `cost:current_day` | 0.00 |
| `cost:by_model:gpt-5.5` | 0.00 |
| `cost:by_model:deepseek-v4-flash` | 0.00 |

---

## 4. Memory Ingestion Log Analysis

### 4.1 Memory Bridge Operations (from `agent.log`)

**Timeline:**

| Date | Event | Detail |
|---|---|---|
| Jun 3 22:38 | `auxiliary_client` | No provider available → compression, summarization, memory flush disabled |
| Jun 3 22:53 | `tool_executor` | Tool memory returned error: "Memory is not available" (×4 occurrences) |
| Jun 3 23:45 | `tool_executor` | Tool memory returned error: "Memory is not available" (×2 occurrences) |
| Jun 4 05:25 | `read_pipeline` | `embedding_fallback_keyword` → `recall_no_results` (×4 cycles) |
| Jun 4 06:26 | `memory_bridge` | `bridge_store_error` then `bridge_recall_success` (embedding fallback) |
| Jun 4 06:38 | `write_pipeline` | `episode_stored` + `bridge_store_success` — first successful write |
| Jun 4 06:39 | `write_pipeline` | 2 more `episode_stored` + `bridge_store_success` |
| Jun 5 | — | **No memory operations logged** (gateway APM `[MEMORY]` entries are process RSS, not semantic memory) |

### 4.2 Embedding Analysis

| Metric | Count |
|---|---|
| `embedding_fallback_keyword` warnings | At least 6 |
| `recall_no_results` events | At least 6 |
| `episode_stored` (success) | 3 |
| `bridge_store_error` | 3 |
| `bridge_store_success` | 3 |

**Pattern:** Every recall operation falls back from embedding → keyword search, and every keyword search returns zero results. Embedding generation is failing entirely. Only 3 episodes were successfully stored (at 06:38-06:39 Jun 4), all via the Python memory bridge (`src.memory.write_pipeline`), not through Hermes' native `store_conversation` tool.

### 4.3 store_conversation: NOT FOUND

No `store_conversation` events appear in any log. The Hermes memory tool is returning "Memory is not available" errors. The only successful writes came from the Python-side memory bridge (`src.memory.write_pipeline`), which is separate from Hermes' tool system.

---

## 5. PostgreSQL Memory Storage: NOT DEPLOYED

| Check | Result |
|---|---|
| `guinevere_memory` database | **Does not exist** |
| `episodic_memories` table | **Does not exist** |
| `dnr_entries` table | **Does not exist** |
| `semantic_memories` table | **Does not exist** |
| `dnr_audit` table | **Does not exist** |
| `pgvector` extension | **Not installed** |
| Available PG instance | PostgreSQL 16.14 + TimescaleDB on port 5433 |
| Databases present | `postgres`, `template0`, `template1`, `guinevere`, `guinevere_core` |
| Tables in `guinevere_core` | **0** (empty database) |
| Tables in `guinevere` | **0** (empty database) |

**Conclusion:** Phase 3 Memory Bridge Migration has **not been initiated**. The PostgreSQL target infrastructure exists (port 5433, TimescaleDB-enabled) but schema migrations, pgvector installation, and table creation are all pending.

---

## 6. Gateway Stability

### 6.1 Restart Pattern

| Metric | Value |
|---|---|
| Gateway restarts in log | 13 |
| Total log lines | 599 |
| Restart-to-restart ratio | 1 restart per ~46 lines |

**Notable instability:** Several rapid restart cycles observed:
- 09:41 → 09:56 (942s runtime then SIGTERM)
- 09:57 → 09:57 (11s then SIGTERM)
- 09:57 → 09:57 (21s then SIGTERM) — rapid cycling
- 10:08 → 10:08 (12s then SIGTERM)

**Warning:** `Stale systemd unit detected: hermes-gateway.service has TimeoutStopSec=90s but drain_timeout=180s (expected >=210s). systemd may SIGKILL the gateway mid-drain.`

### 6.2 Memory Footprint (Process RSS)

| Phase | RSS |
|---|---|
| Baseline | 161 MB |
| After 5 min | ~206 MB |
| Steady state (1h+) | 214-218 MB |
| GC stats | Gen0: 200-400, Gen1: 4-5, Gen2: 4 (stable) |
| Thread count | 2 → 13 (grows over uptime) |

Memory growth is moderate and plateaus. No memory leak indication.

---

## 7. DNR Enforcement

### 7.1 DNR Filter Hook

| Metric | Value |
|---|---|
| DNR filter log entries | **1** |
| Only entry | `ALLOWED | tool=terminal | user= | result_len=0 | elapsed_ms=0.07` |
| Timestamp | 2026-06-05T01:38:58 UTC |

### 7.2 Consent Gate Hook

| Metric | Value |
|---|---|
| Consent gate log entries | **1** |
| Only entry | `ALLOWED (no consent needed) | tool=file_write | user= | elapsed_ms=0.05` |

### 7.3 Hard Stop Hook

| Metric | Value |
|---|---|
| Hard stop log entries | 9 |
| Pattern | Safe word resolved from "hardcoded fallback" |
| Error | `Failed to read stdin: invalid or empty JSON` (1 occurrence) |
| All decisions | ALLOWED (prompt_len=0) |

### 7.4 DNR Audit Trail (PostgreSQL)

**Not available** — `dnr_audit` table does not exist. DNR enforcement is currently hook-based only (shell hooks calling `dnr_filter.py`), with no persistent audit trail in PostgreSQL.

---

## 8. Conversation Quality Metrics

### 8.1 Response Performance

| Metric | Value |
|---|---|
| Total inbound messages | 14 |
| Total responses | 13 |
| Response ratio | 92.9% |
| Avg response time | 5.3s |
| Min response time | 1.5s |
| Max response time | 21.8s (first response after cold start) |
| Model | deepseek-v4-flash (via 9Router custom provider) |
| API call latency | 2.3s – 6.3s |
| Prefix cache hit rate | **85%** (12,672-12,928 / 14,800-15,191 tokens) |

### 8.2 Conversation Loop Events

| Event | Count | Notes |
|---|---|---|
| `text_response(finish_reason=stop)` | All turns | All responses are text, no tool usage |
| `tool_turns=0` | All turns | No tool calls in any turn |
| Message alternation violations repaired | 4 | Session `6dc1af91` had 4 violations repaired |
| System prompt null rebuild | 1 | "Stored system prompt is null; rebuilding from scratch" |
| SOUL.md blocked (prompt_injection) | 2 | Sessions `6dc1af91` and `b4846761` |
| 401 Authentication errors | 8 | 2x OpenRouter, 1x 9Router (token_invalidated), 4x in conversation_loop |
| API call budget | 1-5 / 90 per session | Far below limit |

### 8.3 Conversation Flow Quality

The conversations show natural multi-turn engagement:
- Session `6dc1af91`: 7 user/assistant pairs (14 messages + 1 meta), ended by user-initiated `/reset` slash command
- Session `b4846761`: 5 user/assistant pairs (10 messages + 1 meta), active at time of inspection
- Response lengths vary appropriately (57 to 590 chars) depending on user input complexity
- No tool-based interactions — purely conversational

---

## 9. Errors &amp; Warning Summary

| Category | Count | Severity |
|---|---|---|
| MCP server connection failures (web, filesystem, terminal, git, fetch) | ~135 warnings | **Medium** — all 5 MCP servers failing identically ("no 'command' in config") |
| Authentication errors (401) | 8 | **High** — 9Router token invalidated, OpenRouter missing auth |
| "No module" errors | 35 | **Low** — import issues |
| SOUL.md blocked (prompt_injection) | 2 | **Medium** — false positive? SOUL.md is Guinevere's persona doc |
| Message alternation violations | 4 | **Low** — self-healing |
| System prompt null rebuild | 1 | **Medium** — cache miss consequence |
| Auxiliary client unavailable | 12+ | **Medium** — compression/summarization disabled |
| Stale systemd unit | 1 per restart | **Medium** — risk of SIGKILL mid-drain |

### 9.1 Critical: MCP Server Configuration

All 5 MCP servers (web, filesystem, terminal, git, fetch) fail on every Hermes start with:
```
MCP server 'X' has no 'command' in config
```
This means Hermes agents cannot use MCP tools. The MCP config section in `config.yaml` needs the `command` field populated for each server.

### 9.2 Critical: 9Router Token Invalidated

```
[codex/gpt-5.5] [401]: "Your authentication token has been invalidated. Please try signing in again."
```
The NINEROUTER_API_KEY in `.env` may need rotation. Despite this, the model fallback to `deepseek-v4-flash` via custom provider works.

---

## 10. Last N Memory Writes (Metadata Only)

Only 3 successful writes detected (all from Python memory bridge, none from Hermes tool system):

| # | Timestamp | Pipeline | Result |
|---|---|---|---|
| 1 | 2026-06-04 06:38:53 | `src.memory.write_pipeline` | `episode_stored` → `bridge_store_success` |
| 2 | 2026-06-04 06:39:02 | `src.memory.write_pipeline` | `episode_stored` → `bridge_store_success` |
| 3 | 2026-06-04 06:39:19 | `src.memory.write_pipeline` | `episode_stored` → `bridge_store_success` |

**Note:** Without the PostgreSQL `episodic_memories` table, the storage destination for these writes is unclear — possibly Redis or local file. The `memories/` directory at `/home/guinevere/.hermes/memories/` is empty.

---

## 11. Monitoring &amp; Metrics

| Check | Result |
|---|---|
| Prometheus metrics (port 9191) | **Empty** — no metrics returned |
| `/home/guinevere/logs/guinevere/` | **Empty** directory |
| `/home/guinevere/logs/loops/` | **Empty** directory |
| `/home/guinevere/logs/surveillance/` | **Empty** directory |
| Project logs at `code/guinevere/logs/` | **Empty** directory |

No operational monitoring is active beyond Hermes' built-in `memory_monitor` (process RSS/GC every 300s).

---

## 12. Key Findings &amp; Recommendations

### 12.1 Blocking Issues for Phase 3

1. **No `guinevere_memory` database.** PostgreSQL 16.14 + TimescaleDB is running on port 5433 but schema migration has not been executed. `pgvector` extension not installed.

2. **Embedding pipeline is broken.** Every recall falls back to keyword search with zero results. Embedding generation isn't working — likely missing an embedding provider/model configuration.

3. **No persistent memory storage.** The 3 successful writes from the Python bridge have no visible destination (PG tables don't exist, Redis DB5 only has cost keys).

4. **Redis ACL blocks direct inspection.** Session/memory keys cannot be enumerated without SOPS decryption.

### 12.2 Recommendations

| Priority | Action |
|---|---|
| **P0** | Create `guinevere_memory` database with pgvector extension and schema migration |
| **P0** | Configure an embedding provider (OpenAI, local, or 9Router endpoint) |
| **P1** | Fix MCP server configurations (add `command` fields for web, filesystem, terminal, git, fetch) |
| **P1** | Rotate 9Router API key (token_invalidated error) |
| **P1** | Regenerate systemd unit to fix TimeoutStopSec mismatch |
| **P2** | Set up Prometheus metrics endpoint or verify why port 9191 is empty |
| **P2** | Enable auxiliary client (OPENROUTER_API_KEY or local model) for compression/summarization |
| **P3** | Investigate SOUL.md prompt_injection false positive blocking |

---

## 13. Command Execution Log

| Check | Status | Notes |
|---|---|---|
| `find .hermes -name "*session*"` | ✓ | Found `sessions/` dir, `sessions.json`, `request_dump_*.json` |
| `find .hermes -name "*.db"` | ✓ | Found `state.db` (106KB), `kanban.db` (106KB) |
| `sqlite3 state.db .tables` | ✓ | `sessions`, `messages`, `state_meta`, FTS5 indexes |
| `sqlite3 state.db "SELECT count(*) FROM sessions"` | ✓ | 2 sessions |
| `sqlite3 state.db "SELECT count(*) FROM messages"` | ✓ | 26 messages |
| `redis-cli -p 6380 -n 4 KEYS "*"` | ✗ | NOAUTH — requires ACL credentials |
| `redis-cli -p 6380 -n 5 DBSIZE` | ✗ | NOAUTH — requires ACL credentials |
| `redis-cli -p 6380 -n 5 KEYS "*"` | ✗ | NOAUTH — requires ACL credentials |
| `sudo -u postgres psql -p 5433` | ✗ | No `postgres` system user — PG runs as `caddy` |
| `psql -U guinevere_core -p 5433 -d guinevere_memory` | ✗ | Database `guinevere_memory` does not exist |
| `psql -U guinevere_core -p 5433 -d guinevere_core \dt` | ✓ | 0 tables (empty database) |
| `psql -U guinevere_core -p 5433 -d guinevere \dt` | ✓ | 0 tables (empty database) |
| `grep memory\|recall\|embed agent.log` | ✓ | 31 matching lines — memory bridge operations found |
| `grep store_conversation gateway.log` | ✓ | 0 matches — not used |
| `tail dnr_filter.log` | ✓ | 1 entry (ALLOWED) |
| `tail consent_gate.log` | ✓ | 1 entry (ALLOWED) |
| `tail hard_stop.log` | ✓ | 9 entries, 1 error (Failed to read stdin) |
| `curl localhost:9191/metrics` | ✗ | Empty response — no metrics endpoint |
| `find -name "*metric*\|*monitor*\|*health*"` | ✓ | None found beyond memory_monitor in gateway |

---

## 14. Evidence &amp; Artifacts

| Artifact | Path |
|---|---|
| Session state DB | `/home/guinevere/.hermes/state.db` |
| Session JSON | `/home/guinevere/.hermes/sessions/sessions.json` |
| Gateway log | `/home/guinevere/.hermes/logs/gateway.log` (599 lines) |
| Agent log | `/home/guinevere/.hermes/logs/agent.log` |
| Error log | `/home/guinevere/.hermes/logs/errors.log` (1043 entries) |
| DNR filter log | `/home/guinevere/.hermes/logs/hooks/dnr_filter.log` |
| Consent gate log | `/home/guinevere/.hermes/logs/hooks/consent_gate.log` |
| Hard stop log | `/home/guinevere/.hermes/logs/hooks/hard_stop.log` |
| Hermes config | `/home/guinevere/.hermes/config.yaml` |
| Hermes env | `/home/guinevere/.hermes/.env` |
| Redis data | `/home/guinevere/data/redis/` (4KB) |
| SOPS secrets | `/home/guinevere/secrets/redis-acl-passwords.yaml` |
| Redis ACL evidence | `docs/setup-evidence/P0/STEP-P0-021/redis-acl-users.txt` |

---

## 15. Footer

| Field | Value |
|---|---|
| Inspector | Sisyphus-Junior (unspecified-high agent) |
| Scope | VPS inspection only — no modifications made |
| Data sensitivity | HIGH — report contains only metadata, hashed IDs, and counts. No raw conversation content, no secrets, no passwords. |
| Boundary compliance | PersonaSafetyPolicy observed — no raw surveillance data, no intimate content |
| Re-run safety | Fully idempotent — read-only inspection |
| Next action | Initiate Phase 3 schema migration: create `guinevere_memory` DB, install pgvector, run Alembic migrations |