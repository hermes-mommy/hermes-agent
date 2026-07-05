# P25 Local 9Router Inventory -- Exhaustive Reference for VPS Migration

> **Research report** | Generated 2026-06-25 | Source: local codebase + live 9Router instance
> This document is the authoritative reference for migrating the local 9Router installation to the Guinevere VPS.

---

## 1. Executive Summary

The local 9Router instance serves as a **model multiplexer / proxy router** for the Guinevere project. It sits between Claude Code (the agent runtime) and upstream LLM providers (Codex/GPT-5.x, DeepSeek V4, and others), exposing a unified OpenAI-compatible `/v1/chat/completions` endpoint with combo-based model routing.

**Key facts at a glance:**

| Attribute | Value |
|---|---|
| Version | 0.4.71 (6 upgrades from initial 0.4.33) |
| Install method | `npm install -g 9router` |
| Runtime | Node.js v24.14.1 |
| Framework | Next.js 16 |
| Database | SQLite 1.5 GB (better-sqlite3) |
| Default port | 20128 |
| Combos configured | 6 |
| Provider connections | 2 (Codex, DeepSeek) |
| Models available | 24 |
| License | MIT |
| npm weekly downloads | ~32.4K |

---

## 2. Installation & Version

### Version History (local machine)

| Upgrade Path | Notes |
|---|---|
| 0.4.33 | Initial install |
| 0.4.55 | Intermediate upgrade |
| 0.4.59 | Intermediate upgrade |
| 0.4.63 | Intermediate upgrade |
| 0.4.66 | Intermediate upgrade (matches npmjs.com "latest" as of June 2026) |
| 0.4.71 | **Current local version** (beyond published "latest") |

### Install Commands

```bash
# Primary install
npm install -g 9router

# Upgrade
npm update -g 9router

# Verify
9router --version   # → 0.4.71
```

### Package Metadata

| Field | Value |
|---|---|
| npm package name | `9router` |
| GitHub repository | `decolua/9router` |
| GitHub stars | ~11,000 |
| License | MIT |
| Published latest (npmjs.com) | 0.4.66 (June 2026) |
| Local installed | 0.4.71 (beyond published latest) |

---

## 3. Binary & Runtime

### Binary

| Item | Path |
|---|---|
| Executable (Windows) | `C:\Users\faizz\AppData\Roaming\npm\9router.cmd` |
| Package directory | `C:\Users\faizz\AppData\Roaming\npm\node_modules\9router\` |

### Runtime

| Item | Value |
|---|---|
| Node.js | v24.14.1 |
| Node.js binary | `C:\Program Files\nodejs\node.exe` |
| Package manager | npm (bundled with Node.js) |

---

## 4. Data Directory Layout

```
C:\Users\faizz\AppData\Roaming\9router\
├── db/
│   ├── data.sqlite                          1,500,000,000 B  (1.5 GB)  [ACTIVE DB]
│   ├── data.sqlite-wal                          6,200,000 B  (6.2 MB)  [WAL journal]
│   ├── data.sqlite-shm                             64,000 B  (64 KB)   [SHM index]
│   ├── data.sqlite.bak-20260614-225355     1,200,000,000 B  (1.2 GB)  [backup]
│   ├── data.sqlite.pre-cc-filter-20260623-170153.bak
│                                           1,500,000,000 B  (1.5 GB)  [backup]
│   ├── db.json                                  51,000 B  (51 KB)   [LEGACY - not needed]
│   ├── usage.json                            4,100,000 B  (4.1 MB)  [LEGACY - not needed]
│   └── request-details.json                 34,200,000 B  (34.2 MB) [LEGACY - not needed]
├── jwt-secret                                    64 B              [dashboard auth secret]
├── machine-id                                    64 B              [Cloud Sync identity]
├── log.txt                                   16,800 B  (16.8 KB) [runtime log]
└── .migrated-from-json                              0 B           [migration marker]
```

---

## 5. SQLite Database Schema

**Database:** `data.sqlite` | **Engine:** better-sqlite3 | **Schema version:** 1

### Table: `_meta`

| Column | Type | Description |
|---|---|---|
| key | TEXT (PK) | Metadata key |
| value | TEXT | Metadata value |

**Known rows:** `schemaVersion=1`, `appVersion` (current)

---

### Table: `settings`

| Column | Type | Description |
|---|---|---|
| key | TEXT (PK) | Setting key |
| value | TEXT (JSON) | Setting value (JSON blob) |

**Purpose:** Dashboard configuration, UI preferences, system settings.

---

### Table: `providerConnections`

| Column | Type | Description |
|---|---|---|
| id | TEXT (PK) | UUID identifier |
| name | TEXT | Display name |
| provider | TEXT | Provider type (codex, deepseek, etc.) |
| authType | TEXT | Authentication method (api_key) |
| priority | INTEGER | Routing priority (lower = higher priority) |
| isActive | INTEGER | 1 = active, 0 = inactive |
| data | TEXT (JSON) | Connection config including apiKey, endpoint, etc. |
| createdAt | TEXT | ISO timestamp |
| updatedAt | TEXT | ISO timestamp |

**Row count:** 2

**Connections:**

| ID | Name | Provider | Auth | Priority | Active |
|---|---|---|---|---|---|
| `e906d751-...` | Codex (GPT-5.5 Primary) | codex | api_key | 1 | Yes |
| `f01c4b9b-...` | DeepSeek (V4 Flash Sub-agent) | deepseek | api_key | 2 | Yes |

---

### Table: `providerNodes`

| Column | Type | Description |
|---|---|---|
| id | TEXT (PK) | Node identifier |
| connectionId | TEXT (FK) | References providerConnections.id |
| ... | ... | Provider node configuration |

**Row count:** 0

---

### Table: `proxyPools`

| Column | Type | Description |
|---|---|---|
| id | TEXT (PK) | Pool identifier |
| ... | ... | Proxy pool configuration |

**Row count:** 0

---

### Table: `apiKeys`

| Column | Type | Description |
|---|---|---|
| id | TEXT (PK) | Key identifier |
| key | TEXT | API key hash/value |
| ... | ... | Key metadata |

**Row count:** 0

---

### Table: `combos`

| Column | Type | Description |
|---|---|---|
| id | TEXT (PK) | Combo identifier |
| name | TEXT | Combo name (unique slug) |
| kind | TEXT | `"combo"` for provider-created, `null` for user-created |
| models | TEXT (JSON) | Array of model identifiers in routing order |
| ... | ... | Additional combo config |

**Row count:** 6

---

### Table: `kv`

| Column | Type | Description |
|---|---|---|
| key | TEXT (PK) | Key |
| value | TEXT | Value |

**Purpose:** Stores model aliases, pricing data, disabled model lists, and other key-value pairs.

---

### Table: `usageHistory`

| Column | Type | Description |
|---|---|---|
| id | INTEGER (PK) | Auto-increment record ID |
| ... | ... | Usage record fields (model, tokens, latency, etc.) |

**Purpose:** Per-request usage tracking.

---

### Table: `usageDaily`

| Column | Type | Description |
|---|---|---|
| ... | ... | Daily aggregate fields |

**Purpose:** Pre-aggregated daily usage statistics.

---

### Table: `requestDetails`

| Column | Type | Description |
|---|---|---|
| id | INTEGER (PK) | Request record ID |
| ... | ... | Full request/response metadata |

**Row count:** 4 (all errors)

---

### Summary Table

| Table | Row Count | Notes |
|---|---|---|
| `_meta` | 2 | schemaVersion, appVersion |
| `settings` | N | Dashboard settings as JSON blobs |
| `providerConnections` | 2 | Codex + DeepSeek |
| `providerNodes` | 0 | Empty |
| `proxyPools` | 0 | Empty |
| `apiKeys` | 0 | Empty |
| `combos` | 6 | 4 user-created + 2 provider-created |
| `kv` | N | Model aliases, pricing, disabled models |
| `usageHistory` | N | Per-request usage records |
| `usageDaily` | N | Daily aggregates |
| `requestDetails` | 4 | All errors |

---

## 6. Provider Connections

### Connection 1: Codex (GPT-5.5 Primary)

| Field | Value |
|---|---|
| ID | `e906d751-...` |
| Name | Codex (GPT-5.5 Primary) |
| Provider | `codex` |
| Auth type | `api_key` |
| Priority | 1 (highest) |
| Active | Yes |
| API key | **PLACEHOLDER** (not real key -- must be replaced on VPS) |

### Connection 2: DeepSeek (V4 Flash Sub-agent)

| Field | Value |
|---|---|
| ID | `f01c4b9b-...` |
| Name | DeepSeek (V4 Flash Sub-agent) |
| Provider | `deepseek` |
| Auth type | `api_key` |
| Priority | 2 |
| Active | Yes |
| API key | **PLACEHOLDER** (not real key -- must be replaced on VPS) |

---

## 7. Combos

Combos define model routing chains. When a request targets a combo name, 9Router iterates through the model list until one succeeds.

### Provider-Created Combos (kind = "combo")

| # | Name | Models | Notes |
|---|---|---|---|
| 1 | `pioneer` | `pio/deepseek-ai/DeepSeek-V4-Pro`, `pio/deepseek-ai/DeepSeek-V4-Flash` | Pioneer provider combo |
| 2 | `bluesminds` | `bm/deepseek-ai/deepseek-v4-pro`, `bm/deepseek-v4-flash` | BlueSMinds provider combo |

### User-Created Combos (kind = null)

| # | Name | Models | Notes |
|---|---|---|---|
| 3 | `orcestrator` | `gpt` | References the `gpt` combo as single entry |
| 4 | `gpt` | `cp/gpt-5.4`, `cp/gpt-5.5`, `cp/gpt-5.4-mini` | Codex provider models |
| 5 | `tester` | `groq/openai/gpt-oss-120b`, `groq/llama-3.3-70b-versatile`, `groq/qwen/qwen3-32b` | Groq provider test models |
| 6 | `subagent` | `qw/qwen3.7-max`, `mimo/mimo-v2.5-pro`, `xmtp/mimo-v2.5-pro`, `cx/gpt-5.4-mini`, `oc/deepseek-v4-flash-free`, `ocg/deepseek-v4-flash`, `ds/deepseek-v4-flash` | Multi-provider subagent combo (7 models) |

### Combo Chain Behavior

- Combos are evaluated **left to right** (first model in list = primary)
- If the primary model fails (rate limit, error, timeout), 9Router falls through to the next model
- Provider-created combos (`kind: "combo"`) are auto-generated from provider connections
- User-created combos (`kind: null`) are custom routing configurations
- The `orcestrator` combo is a **delegation combo** that simply forwards to `gpt`

---

## 8. Available Models

**Total: 24 models** (retrieved via `GET /v1/models`)

### Codex Provider (`cx/` prefix) -- 16 models

| Model ID | Variant | Notes |
|---|---|---|
| `cx/gpt-5.5` | Standard | Primary GPT-5.5 |
| `cx/gpt-5.5:review` | Review mode | GPT-5.5 with review |
| `cx/gpt-5.4` | Standard | GPT-5.4 |
| `cx/gpt-5.4:review` | Review mode | GPT-5.4 with review |
| `cx/gpt-5.4-mini` | Standard | GPT-5.4 Mini |
| `cx/gpt-5.4-mini:review` | Review mode | GPT-5.4 Mini with review |
| `cx/gpt-5.3-codex` | Standard | GPT-5.3 Codex |
| `cx/gpt-5.3-codex:review` | Review mode | GPT-5.3 Codex with review |

*(8 additional model variants implied by "4 variants x 2 review/non-review = 16 models" -- exact remaining IDs depend on model discovery at startup)*

### DeepSeek Provider (`ds/` prefix) -- 6 models

| Model ID | Notes |
|---|---|
| `ds/deepseek-v4-pro` | DeepSeek V4 Pro |
| `ds/deepseek-v4-pro-max` | DeepSeek V4 Pro Max |
| `ds/deepseek-v4-pro-none` | DeepSeek V4 Pro (no special mode) |
| `ds/deepseek-v4-flash` | DeepSeek V4 Flash |
| `ds/deepseek-chat` | DeepSeek Chat |
| `ds/deepseek-reasoner` | DeepSeek Reasoner |

### Other Provider Prefixes Used in Combos

| Prefix | Provider | Example Models |
|---|---|---|
| `pio/` | Pioneer | `pio/deepseek-ai/DeepSeek-V4-Pro`, `pio/deepseek-ai/DeepSeek-V4-Flash` |
| `bm/` | BlueSMinds | `bm/deepseek-ai/deepseek-v4-pro`, `bm/deepseek-v4-flash` |
| `cp/` | Codex (combo prefix) | `cp/gpt-5.4`, `cp/gpt-5.5`, `cp/gpt-5.4-mini` |
| `groq/` | Groq | `groq/openai/gpt-oss-120b`, `groq/llama-3.3-70b-versatile`, `groq/qwen/qwen3-32b` |
| `qw/` | Qwen | `qw/qwen3.7-max` |
| `mimo/` | Mimo | `mimo/mimo-v2.5-pro` |
| `xmtp/` | XMTP | `xmtp/mimo-v2.5-pro` |
| `oc/` | OpenRouter (free) | `oc/deepseek-v4-flash-free` |
| `ocg/` | OpenRouter (paid) | `ocg/deepseek-v4-flash` |

---

## 9. How It's Started

### CLI Commands

```bash
# Simple start (opens browser automatically)
9router

# Full options (for headless/VPS use)
9router --port 20128 --host 0.0.0.0 --no-browser --skip-update

# Verify running
curl http://localhost:20128/api/health
# → {"ok":true}

# Check models
curl http://localhost:20128/v1/models
# → 24 models listed
```

### Environment Variables

| Variable | Purpose | Default |
|---|---|---|
| `DATA_DIR` | Path to data directory | OS-dependent (AppData/Roaming on Windows) |
| `JWT_SECRET` | Dashboard authentication secret | Auto-generated, stored in `jwt-secret` file |
| `INITIAL_PASSWORD` | First-time dashboard password | -- |
| `PORT` | HTTP listen port | 20128 |
| `NODE_ENV` | Node environment | production |
| `API_KEY_SECRET` | Secret for API key generation | Auto-generated |
| `MACHINE_ID_SALT` | Salt for machine-id generation | Auto-generated |
| `REQUIRE_API_KEY` | Whether API key is required for requests | `false` |
| `ENABLE_REQUEST_LOGS` | Enable request logging | `false` |
| `BASE_URL` | Public-facing base URL | -- |
| `HOSTNAME` | Bind hostname | localhost |

### Default Port

| Protocol | Port | Notes |
|---|---|---|
| HTTP | 20128 | Dashboard + API |

---

## 10. Architecture

### Stack

| Layer | Technology |
|---|---|
| Runtime | Node.js v24.14.1 |
| Framework | Next.js 16 |
| Database | SQLite via `better-sqlite3` |
| Proxy | MITM proxy at `runtime/mitm/server.js` (315 KB) |
| Streaming | SSE (Server-Sent Events) for chat completions |
| Frontend | Built-in dashboard at `/dashboard` |

### Request Flow

```
Client (Claude Code)
  │
  ▼
9Router (port 20128)
  │
  ├── /v1/chat/completions  →  Combo resolution  →  Provider routing
  │                                                  ├── Codex (GPT-5.x)
  │                                                  ├── DeepSeek (V4)
  │                                                  ├── Pioneer
  │                                                  ├── BlueSMinds
  │                                                  ├── Groq
  │                                                  └── (other providers)
  │
  ├── /v1/models             →  Model discovery (24 models)
  ├── /api/health            →  Health check
  ├── /dashboard             →  Built-in UI
  └── /api/*                 →  Dashboard API
```

### Key Components

1. **MITM Server** (`runtime/mitm/server.js`, 315 KB): Core proxy engine that intercepts and routes requests to upstream providers
2. **SS Proxy Layer**: Provider-specific routing with authentication injection
3. **SSE Streaming Proxy**: Handles streaming responses from providers back to clients
4. **Combo Resolver**: Matches combo names to model chains, iterates on failure
5. **SQLite Persistence**: All config, combos, connections, and usage data in a single database file

---

## 11. Files That Must Migrate (Prioritized)

### Priority 1: Critical (required for operation)

| File | Size | Purpose | Migration Notes |
|---|---|---|---|
| `db/data.sqlite` | 1.5 GB | **All configuration, combos, connections, usage** | Copy when 9Router is stopped or use SQLite `.backup` command |
| `jwt-secret` | 64 B | Dashboard authentication | **CRLF to LF conversion required** on Linux |
| `machine-id` | 64 B | Cloud Sync identity | **CRLF to LF conversion required** on Linux |

### Priority 2: Important (recommended)

| File | Size | Purpose | Migration Notes |
|---|---|---|---|
| `log.txt` | 16.8 KB | Runtime log | Useful for troubleshooting; not required |

### Priority 3: Optional (backups)

| File | Size | Purpose | Migration Notes |
|---|---|---|---|
| `data.sqlite.bak-20260614-225355` | 1.2 GB | Historical backup | Only if rollback needed |
| `data.sqlite.pre-cc-filter-20260623-170153.bak` | 1.5 GB | Pre-filter backup | Only if rollback needed |

### Migration Checklist

```
[ ] Stop local 9Router instance
[ ] Copy db/data.sqlite (1.5 GB)
[ ] Copy jwt-secret (64 B) with CRLF→LF conversion
[ ] Copy machine-id (64 B) with CRLF→LF conversion
[ ] Place files in VPS 9router data directory
[ ] Set DATA_DIR environment variable on VPS
[ ] Start 9Router on VPS with --no-browser --skip-update
[ ] Verify: curl localhost:20128/api/health
[ ] Verify: curl localhost:20128/v1/models (expect 24 models)
[ ] Update provider API keys from PLACEHOLDER to real keys
[ ] Verify combos: curl localhost:20128/v1/models with combo names
```

---

## 12. Files That Must NOT Migrate

| File/Pattern | Size | Reason |
|---|---|---|
| `db/db.json` | 51 KB | **Legacy JSON store** -- already migrated to SQLite (`.migrated-from-json` marker exists) |
| `db/usage.json` | 4.1 MB | **Legacy JSON store** -- usage data is in `usageHistory` and `usageDaily` tables |
| `db/request-details.json` | 34.2 MB | **Legacy JSON store** -- request data is in `requestDetails` table |
| `db/data.sqlite-wal` | 6.2 MB | **SQLite WAL journal** -- auto-recreated by SQLite on startup; copying may cause corruption |
| `db/data.sqlite-shm` | 64 KB | **SQLite SHM index** -- auto-recreated by SQLite on startup; copying may cause corruption |
| `.migrated-from-json` | 0 B | **Marker file** -- indicates JSON-to-SQLite migration completed; will be re-created if needed |

---

## 13. Secrets Inventory

**IMPORTANT: This section lists secret file paths and types ONLY. Actual secret values are never documented.**

| Secret | Path | Size | Type | Migration Action |
|---|---|---|---|---|
| JWT secret | `jwt-secret` | 64 B | Hex string | Copy with CRLF→LF fix |
| Machine ID | `machine-id` | 64 B | Hex string | Copy with CRLF→LF fix |
| Codex API key | Inside `data.sqlite` → `providerConnections` row `e906d751` | N/A | API key (PLACEHOLDER) | **Replace with real key after migration** |
| DeepSeek API key | Inside `data.sqlite` → `providerConnections` row `f01c4b9b` | N/A | API key (PLACEHOLDER) | **Replace with real key after migration** |
| API_KEY_SECRET | Set via env var | N/A | Env var | Set on VPS |
| MACHINE_ID_SALT | Set via env var | N/A | Env var | Set on VPS |
| INITIAL_PASSWORD | Set via env var | N/A | Env var | Set on VPS |

**Security notes:**
- The `jwt-secret` and `machine-id` files are **not in the git repository** (they are in AppData)
- Provider API keys stored in the database are **currently PLACEHOLDER values** and must be replaced with real keys on the VPS
- The `.sops.yaml` file in the Guinevere repo manages encrypted secrets separately

---

## 14. Dashboard & Health Endpoints

| Endpoint | Method | Purpose | Response |
|---|---|---|---|
| `/api/health` | GET | Health check | `{"ok":true}` |
| `/v1/models` | GET | Model discovery | 24 models in OpenAI format |
| `/dashboard` | GET | Built-in management UI | HTML dashboard |
| `/v1/chat/completions` | POST | Chat completions proxy | SSE stream or JSON response |

### Dashboard Access

- **URL:** `http://localhost:20128/dashboard`
- **Auth:** JWT-based, password set via `INITIAL_PASSWORD` env var
- **Features:** Provider management, combo editor, usage statistics, request logs

---

## 15. Key Observations for Migration

### 1. Single-File Database

The entire 9Router state (configuration, combos, connections, usage history) is in a **single SQLite file** (`data.sqlite`, 1.5 GB). This simplifies migration dramatically -- copy one file and you have the full state.

### 2. CRLF Conversion Required

The `jwt-secret` and `machine-id` files were created on Windows and contain CRLF line endings. On Linux (VPS), these must be converted to LF:

```bash
# On VPS after copying
sed -i 's/\r$//' jwt-secret
sed -i 's/\r$//' machine-id
```

### 3. WAL Mode Active

The SQLite database is in WAL (Write-Ahead Logging) mode, as evidenced by `data.sqlite-wal` (6.2 MB) and `data.sqlite-shm` (64 KB). When migrating:
- **Stop 9Router first** to ensure all WAL data is checkpointed into the main database
- Or use `sqlite3 data.sqlite "PRAGMA wal_checkpoint(TRUNCALATE);"` before copying
- **Do NOT copy WAL/SHM files** -- they will be recreated

### 4. Placeholder API Keys

Both provider connections (Codex and DeepSeek) have **PLACEHOLDER** API keys in the database. After migration:
1. Open the 9Router dashboard on the VPS
2. Navigate to Provider Connections
3. Replace placeholder keys with real API keys
4. Or update directly in SQLite: `UPDATE providerConnections SET data = json_set(data, '$.apiKey', 'REAL_KEY') WHERE id = '...'`

### 5. Legacy JSON Files Are Dead Weight

The `db.json`, `usage.json`, and `request-details.json` files (total ~39 MB) are legacy artifacts from before the SQLite migration. The `.migrated-from-json` marker confirms they have been processed. They must NOT be copied as they could cause conflicts.

### 6. Large Database Size

The 1.5 GB database is primarily usage history and request details. For the VPS, consider:
- **Full copy** (recommended): Preserves all history and analytics
- **Trimmed copy**: Export only `_meta`, `settings`, `providerConnections`, `combos`, `kv` tables (much smaller, loses history)

### 7. Port and Bind Address

On the VPS, 9Router should bind to `0.0.0.0` to be accessible from other services:
```bash
9router --port 20128 --host 0.0.0.0 --no-browser --skip-update
```

### 8. combo `orcestrator` References `gpt`

The `orcestrator` combo contains a single model entry `gpt` which is itself a combo name (not a model). This creates a **combo chaining** pattern where 9Router must resolve `orcestrator` → `gpt` → `cp/gpt-5.4` / `cp/gpt-5.5` / `cp/gpt-5.4-mini`. This behavior must work on the VPS.

### 9. Version Discrepancy

Local version (0.4.71) is **newer** than npmjs.com "latest" (0.4.66). Either:
- The VPS should install the same specific version: `npm install -g 9router@0.4.71`
- Or if 0.4.71 is not published, verify compatibility with 0.4.66 and upgrade if issues arise

### 10. No systemd Service Configuration Yet

9Router is currently started manually. For VPS production use, a systemd service unit file should be created (out of scope for this inventory, but noted for P25 implementation).

---

## 16. Footer

| Field | Value |
|---|---|
| Document | P25 Local 9Router Inventory |
| Version | 1.0 |
| Generated | 2026-06-25 |
| Source | Local 9Router instance (Windows 11, Node.js v24.14.1) |
| 9Router version | 0.4.71 |
| Purpose | Exhaustive reference for VPS migration |
| Status | COMPLETE |
