# VPS 9Router Current State — Pre-Migration Snapshot

**Date**: 2026-06-01
**VPS Host**: guinevere-vps (100.94.104.22 via Tailscale)
**User**: guinevere
**Task**: P1 — Pre-migration audit of 9Router configuration

---

## 1. Service Status

- **Service**: `guinevere-9router.service`
- **State**: Active (running), enabled
- **Uptime**: Started Mon 2026-06-01 07:09:02 WIB (~15 min ago at capture time)
- **Binary**: `/usr/bin/9router` v0.4.66
- **Command**: `node /usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update`
- **Memory**: 92.5M (peak 135.0M, high watermark 1.0G)
- **Health**: `{"ok":true}` via `http://localhost:20128/api/health`
- **PID**: 591603

## 2. Directory Structure

```
/home/guinevere/.9router/
├── db/
│   ├── backups/             (empty)
│   ├── data.sqlite          (176,128 bytes)
│   ├── data.sqlite-shm      (32,768 bytes)
│   └── data.sqlite-wal      (0 bytes)
├── logs/
│   └── mitm/                (empty)
├── runtime/
│   ├── mitm/
│   │   └── server.js        (315,065 bytes — Node.js MITM proxy server)
│   ├── node_modules/        (debug, fs-extra, graceful-fs, jsonfile, ms, systray2, universalify)
│   └── package.json         (9router-runtime v1.0.0)
├── machine-id               (64 bytes — present)
└── [jwt-secret]             (NOT FOUND — does not exist)
```

## 3. Database Schema (SQLite — `data.sqlite`)

### Tables

| Table | Rows | Purpose |
|---|---|---|
| `_meta` | 2 | schemaVersion=1, appVersion=0.4.66 |
| `settings` | 0 | Application settings |
| `providerConnections` | 2 | API provider configs |
| `providerNodes` | 0 | Provider node routing |
| `proxyPools` | 0 | Proxy configuration |
| `apiKeys` | 0 | 9Router API keys |
| `combos` | 0 | Model combos |
| `kv` | 0 | Key-value store |
| `usageHistory` | 0 | Usage records |
| `usageDaily` | 0 | Daily usage aggregates |
| `requestDetails` | 4 | Request logs (all errors) |

### Provider Connections (PLACEHOLDER KEYS)

#### Connection 1: Codex (GPT-5.5 Primary)
| Field | Value |
|---|---|
| `id` | `e906d751-dfd5-46af-8dbb-1e3d4b739e3e` |
| `provider` | `codex` |
| `authType` | `api_key` |
| `name` | `GPT-5.5 (Primary)` |
| `priority` | 1 |
| `isActive` | 1 |
| `data.apiKey` | `PLACEHOLDER_GPT55_API_KEY` |
| `data.testStatus` | `unavailable` |
| `data.lastError` | `[401]: Could not parse your authentication token` |
| `data.modelLock_gpt-5.5` | `2026-06-01T00:14:47.168Z` |
| `data.backoffLevel` | 0 |
| `createdAt` | `2026-06-01T00:09:02.000Z` |
| `updatedAt` | `2026-06-01T00:12:47.168Z` |

#### Connection 2: DeepSeek (DeepSeek V4 Flash Sub-agent)
| Field | Value |
|---|---|
| `id` | `f01c4b9b-5ab6-4a01-af6d-1dd4ec49fadf` |
| `provider` | `deepseek` |
| `authType` | `api_key` |
| `name` | `DeepSeek V4 Flash (Sub-agent)` |
| `priority` | 2 |
| `isActive` | 1 |
| `data.apiKey` | `PLACEHOLDER_DEEPSEEK_API_KEY` |
| `data.testStatus` | `unavailable` |
| `data.lastError` | `[401]: Your api key: ****_KEY is invalid` |
| `data.modelLock_deepseek-v4-flash` | `2026-06-01T00:14:50.336Z` |
| `data.backoffLevel` | 0 |
| `createdAt` | `2026-06-01T00:09:02.000Z` |
| `updatedAt` | `2026-06-01T00:12:50.336Z` |

### Request History (4 error requests)

All 4 requests failed with 401 errors — 2 per provider, test patterns:
1. Codex: `Say hello in one word` -> 401 auth parse failure
2. DeepSeek: `Say hello in one word` -> 401 invalid API key
3. Codex: `hi` -> 401 auth parse failure
4. DeepSeek: `hi` -> 401 invalid API key

## 4. Models Available

9Router exposes 24 models from 2 placeholder provider prefixes:

- **cx/**: gpt-5.5, gpt-5.4, gpt-5.4-mini, gpt-5.3-codex (4 variants x 2 review/non-review = 16 models)
- **ds/**: deepseek-v4-pro, deepseek-v4-pro-max, deepseek-v4-pro-none, deepseek-v4-flash, deepseek-chat, deepseek-reasoner (6 models)

Total: **24 models**

## 5. Security Artifacts

| Artifact | Path | Status |
|---|---|---|
| JWT secret | `/home/guinevere/.9router/jwt-secret` | **NOT FOUND** (never created) |
| Machine ID | `/home/guinevere/.9router/machine-id` | **Present** — `c602ec9a1cd85e62c3626d795677f5e1493c5e6d45cb52f0a8f55109b9d738a3` |
| Age key | `/home/guinevere/secrets/age-key.txt` | **Present** — 189 bytes, `-rw-------` (guinevere only) |
| Age key | `/home/guinevere/.age/key.txt` | **NOT FOUND** |

## 6. System Resources

| Resource | Value |
|---|---|
| Disk total | 99G |
| Disk used | 16G |
| Disk available | 78G (18% used) |
| RAM total | 15Gi |
| RAM used | 1.7Gi |
| RAM available | 13Gi |
| Swap | 4.0Gi (0 used) |

## 7. Docker Containers (Aizanta + Guinevere Stack)

| Container | Status |
|---|---|
| `guinevere-postgres` | Up 15 hours |
| `guinevere-pgbouncer` | Up 14 hours |
| `guinevere-redis` | Up 13 hours |
| `aizanta-bot` | Up 8 days (healthy) |
| `aizanta-nginx` | Up 8 days (healthy) |
| `aizanta-frontend` | Up 16 minutes (healthy) |
| `aizanta-postgres` | Up 8 days (healthy) |
| `aizanta-redis` | Up 8 days (healthy) |
| `objective_buck` | Up 8 days |
| `elastic_beaver` | Up 8 days |

## 8. MITM Proxy

- **Server file**: `/home/guinevere/.9router/runtime/mitm/server.js` (315KB)
- Present but logs directory (`logs/mitm/`) is empty — no MITM activity yet.

## 9. Key Migration Considerations

### What to Backup (from VPS BEFORE overwriting)
1. `machine-id` — 64-byte identity token
2. `secrets/age-key.txt` — SOPS/age encryption key for secrets
3. `data.sqlite` + `data.sqlite-shm` + `data.sqlite-wal` — full DB (present state)

### What to Overwrite (from laptop config)
1. **`providerConnections` table** — replace PLACEHOLDER keys with real Codex + DeepSeek API keys
2. **`jwt-secret`** — if laptop has one, create it on VPS (currently absent)
3. **`machine-id`** — if laptop has a different machine-id, decide whether to keep VPS one or overwrite

### What to Verify After Migration
1. `curl http://localhost:20128/api/health` -> `{"ok":true}`
2. Provider test status transitions from `unavailable` -> `available`
3. Models endpoint returns same 24 models
4. No 401 errors in request history
5. Service restarts cleanly

### Current Weaknesses
1. No JWT secret -> API key auth may be non-functional or default
2. PLACEHOLDER keys in database -> all provider calls fail with 401
3. Machine ID already set — will need to coordinate if laptop config expects a specific machine ID

---

*Report generated by Guinevere — Pre-migration audit of VPS 9Router v0.4.66.*
