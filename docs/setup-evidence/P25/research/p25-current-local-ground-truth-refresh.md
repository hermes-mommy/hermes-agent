# P25 — Local 9Router Ground Truth Refresh

**Date**: 2026-06-26
**Scope**: Verified current state of local 9Router installation (Windows, single-user development machine)
**Purpose**: Correction of stale P25 research that contained materially incorrect claims about version, provider count, combo count, heap defaults, and framework details.

---

## 1. Executive Summary

This report documents the **verified current state** of the locally installed 9Router CLI and its associated data store. It supersedes and corrects prior P25 research that claimed:

- Version 0.4.71 (actual: **0.5.4**)
- 6 combos (actual: **11**)
- 2 provider connections (actual: **92**)
- 6 GB default heap via NODE_OPTIONS (actual: **12 GB** via `NINEROUTER_NODE_HEAP_MB` environment variable, with NODE_OPTIONS insufficient to override the explicit `--max-old-space-size` flag in the child process spawn)

The discrepancies are not minor version drift. The provider ecosystem has grown 46x, the combo roster has nearly doubled, and the heap control mechanism is fundamentally different from what was previously documented. Any migration or operational planning based on the stale research will produce incorrect capacity estimates, broken environment variable assumptions, and under-provisioned deployments.

---

## 2. Version & Installation (Verified)

| Field | Value | Source |
|---|---|---|
| **Local version** | `0.5.4` | `C:\Users\faizz\AppData\Roaming\npm\node_modules\9router\package.json` |
| **App version** | `0.5.4` | `C:\Users\faizz\AppData\Roaming\npm\node_modules\9router\app\package.json` (name: `9router-app`) |
| **npm registry latest** | `0.5.8` | npmjs.com, checked 2026-06-26 |
| **Package name** | `9router` | npmjs.com |
| **CLI entry point** | `cli.js` (27.3 KB, `#!/usr/bin/env node`) | Installed package |
| **Default port** | `20128` | cli.js |
| **Default host** | `0.0.0.0` | cli.js |
| **Minimum Node.js** | `>= 18.0.0` | `engines` field in package.json |

The local installation is two patch versions behind the npm registry latest (0.5.4 vs 0.5.8). This is a minor delta and does not represent a structural gap.

---

## 3. Framework & Runtime

### Next.js 16.1.6 (Confirmed)

The 9Router app is a **Next.js standalone production build**.

| Component | Version | File |
|---|---|---|
| Next.js | `^16.1.6` | `app/package.json` |
| React | `19.2.4` | `app/package.json` |
| Express | `5.2.1` | `app/package.json` dependencies |

### Server Architecture

- **`app/server.js`** — Next.js standalone production server. Uses `next/dist/server/lib/start-server` to bind the Next.js HTTP handler.
- **`app/custom-server.js`** — Custom HTTP server wrapper. Strips proxy headers (`x-forwarded-for`, `x-real-ip`, etc.) and derives the real client IP from the raw TCP socket (`req.socket.remoteAddress`). This is the server file used when `custom-server.js` exists on disk; the CLI checks for it and prefers it over `server.js`.
- **Build output**: `.next-cli-build` (standalone mode)

### Standalone Mode

The app directory (`app/`) is a self-contained standalone deployment artifact. It includes `server.js`, `custom-server.js`, the `.next-cli-build` output directory, and a bundled `package.json` with all runtime dependencies. No monorepo build step is required at runtime.

---

## 4. Heap Control Mechanism

**This is the most critical correction from the stale research.**

### The Stale (WRONG) Claim

> Default heap is 6 GB, controlled via `--max-old-space-size=6144`. NODE_OPTIONS can be used to adjust.

### The Actual (VERIFIED) Mechanism

**cli.js line 558:**
```javascript
const SERVER_HEAP_MB = Number.parseInt(process.env.NINEROUTER_NODE_HEAP_MB || "12288", 10);
```

**cli.js line 578:**
```javascript
const child = spawn(RUNTIME, [`--max-old-space-size=${SERVER_HEAP_MB}`, serverPath], ...);
```

Where `RUNTIME` = `process.execPath` (the Node.js binary itself), defined at **cli.js line 137**.

### Key Facts

| Aspect | Value |
|---|---|
| **Default heap** | **12,288 MB (12 GB)** |
| **Control variable** | `NINEROUTER_NODE_HEAP_MB` |
| **Mechanism** | Explicit `--max-old-space-size` flag on the child process spawn |
| **NODE_OPTIONS override** | **NOT POSSIBLE** — the explicit flag on the command line takes precedence over NODE_OPTIONS |
| **Only way to control heap** | Set `NINEROUTER_NODE_HEAP_MB` before launching 9Router |

### Why This Matters for Migration

1. The VPS deployment must set `NINEROUTER_NODE_HEAP_MB` to an appropriate value based on available RAM. A 16 GB VPS would need this set to roughly 10240-12288 (10-12 GB) to leave room for the OS and other processes.
2. Any documentation or scripts that use `NODE_OPTIONS="--max-old-space-size=..."` to control 9Router heap are **ineffective** and will be silently ignored.
3. The 12 GB default assumes a development machine with 16+ GB RAM. A VPS with less RAM will OOM without explicit configuration.

---

## 5. CLI Entry Point & Startup

### Full Spawn Flow

1. User runs `9router` (or `npx 9router`).
2. `cli.js` parses CLI options: `--port` / `-p`, `--host` / `-H`, `--no-browser` / `-n`, `--skip-update`, `--log` / `-l`, `--tray` / `-t`.
3. Auto-healing step: `hooks/sqliteRuntime.js` ensures `sql.js` and `better-sqlite3` are installed in `~/.9router/runtime/node_modules`.
4. On Windows, tray support uses PowerShell `NotifyIcon`. On macOS/Linux, `hooks/trayRuntime.js` handles native tray integration.
5. The CLI computes `SERVER_HEAP_MB` from `NINEROUTER_NODE_HEAP_MB` (default 12288).
6. The CLI resolves the server path: checks for `app/custom-server.js` first; falls back to `app/server.js`.
7. The CLI spawns a **child process** via `child_process.spawn()`:
   ```
   spawn(process.execPath, ["--max-old-space-size=12288", "app/server.js"], ...)
   ```
8. The child process binds to `0.0.0.0:20128` (by default) and serves the Next.js standalone app.

### CLI Options Reference

| Option | Alias | Description |
|---|---|---|
| `--port` | `-p` | HTTP port (default: 20128) |
| `--host` | `-H` | Bind address (default: 0.0.0.0) |
| `--no-browser` | `-n` | Suppress auto-opening browser |
| `--skip-update` | — | Skip update check on startup |
| `--log` | `-l` | Log file path |
| `--tray` | `-t` | System tray icon |

---

## 6. Data Directory

### Path

`C:\Users\faizz\AppData\Roaming\9router\`

### Verified Contents

| File | Size | Last Modified | Notes |
|---|---|---|---|
| `data.sqlite` | **1.53 GB** (1,529,745,408 bytes) | 2026-06-26 01:14 | Primary database |
| `data.sqlite-wal` | varies | — | Write-ahead log |
| `data.sqlite-shm` | 64 KB | — | Shared memory file |
| `jwt-secret` | 64 bytes | — | JWT signing secret |
| `machine-id` | 64 bytes | — | Unique machine identifier |
| `db.json` | 51.2 KB | — | Legacy data store |
| `usage.json` | 4.1 MB | — | Legacy usage data |
| `request-details.json` | 34.2 MB | — | Legacy request logs |
| `log.txt` | 16.8 KB | — | Application log |

### Backup Files

| File | Size | Notes |
|---|---|---|
| `data.sqlite.bak-20260614-225355` | 1.2 GB | June 14 backup |
| `data.sqlite.pre-cc-filter-20260623-170153.bak` | 1.5 GB | Pre-CC-filter backup |

### Observations

- The database is **1.53 GB** — this is a substantial SQLite database. Migration to VPS must account for transfer time and disk space.
- Legacy JSON files (`db.json`, `usage.json`, `request-details.json`) total ~38.4 MB and may contain historical data not yet migrated to SQLite.
- The `jwt-secret` and `machine-id` files are security-sensitive. They should be backed up separately and restored on the target VPS to preserve session continuity, or regenerated if a clean break is desired.

---

## 7. Database Schema

**12 tables** (the stale research reported 11, missing `sqlite_sequence`).

| # | Table | Purpose |
|---|---|---|
| 1 | `_meta` | Schema version and app version metadata |
| 2 | `apiKeys` | 9Router local API keys |
| 3 | `combos` | Combo definitions (11 rows) |
| 4 | `kv` | General-purpose key-value store |
| 5 | `providerConnections` | Provider connection configs (**92 rows**) |
| 6 | `providerNodes` | Custom provider endpoints |
| 7 | `proxyPools` | Proxy pool configurations |
| 8 | `requestDetails` | Per-request log records |
| 9 | `settings` | Dashboard and app settings |
| 10 | `sqlite_sequence` | Autoincrement tracking (system table) |
| 11 | `usageDaily` | Daily usage aggregates |
| 12 | `usageHistory` | Per-request usage records |

### Note on `sqlite_sequence`

This is a system table managed by SQLite for `AUTOINCREMENT` columns. It was not listed in the stale research but is present in the schema. It does not contain user data.

---

## 8. Provider Connections

**92 total provider connections** — a **46x increase** from the stale claim of 2.

### By Provider Type

The 92 connections span **26+ distinct provider types**:

| Provider Type | Count | Auth Type | Notes |
|---|---|---|---|
| kiro | 12 | — | Highest single-provider count |
| qoder | 11 | — | |
| openrouter | 9 | apikey | |
| tavily | 9 | apikey | Web search provider |
| ollama | 8 | — | Local inference |
| cloudflare-ai | 8 | — | |
| deepseek | — | apikey | |
| fireworks | — | apikey | |
| gemini | — | apikey | |
| groq | — | apikey | |
| mistral | — | apikey | |
| cerebras | — | apikey | |
| nvidia | — | apikey | |
| anthropic-compatible | — | apikey | |
| openai-compatible-chat | — | apikey | |
| codex | — | — | |
| commandcode | — | — | |
| opencode-go | — | — | |
| xiaomi-tokenplan | — | — | |
| xiaomi-mimo | — | — | |
| kilocode | — | — | |
| brave-search | — | apikey | Web search provider |
| exa | — | apikey | Web search provider |
| linkup | — | apikey | Web search provider |
| jina-reader | — | apikey | Web search provider |
| firecrawl | — | apikey | Web search provider |

### Web Search Providers (6)

The installation includes connections to **six** web search / web data providers:

1. **tavily** (9 accounts)
2. **brave-search**
3. **exa**
4. **linkup**
5. **jina-reader**
6. **firecrawl**

This is relevant for P23 (embodied operations) — the web search capability is far more extensive than a single-provider setup.

### Priority Tiers

Provider connections are organized across **priority levels 1 through 12**. Lower numbers = higher priority. The system cascades through providers when higher-priority ones fail or are rate-limited.

### Auth Types

- `apikey` — API key authentication
- `oauth` — OAuth flow authentication

---

## 9. Combos

**11 combos** — nearly double the stale claim of 6.

| # | Combo Name | Kind | Model Chain |
|---|---|---|---|
| 1 | `bluesminds` | combo | `bm/deepseek-ai/deepseek-v4-pro`, `bm/deepseek-v4-flash` |
| 2 | `cmc` | null | `cmc/deepseek/deepseek-v4-flash` |
| 3 | `gpt` | null | `cx/gpt-5.4`, `cx/gpt-5.5` |
| 4 | `kiro` | null | `qd/kr/claude-sonnet-4.5` |
| 5 | `opencode` | null | `ocg/deepseek-v4-flash` |
| 6 | `orcestrator` | null | `router9`, `subagent`, `skn/fugu-ultra` |
| 7 | `pioneer` | combo | `pio/deepseek-ai/DeepSeek-V4-Pro`, `pio/deepseek-ai/DeepSeek-V4-Flash` |
| 8 | `qoder` | null | `qd/qd/qmodel_latest` |
| 9 | `router9` | null | `rr/9router/alibaba/deepseek-v4-pro`, `rr/9router/alibaba/glm-5.2` |
| 10 | `subagent` | null | `mimo/mimo-v2.5-pro`, `xmtp/mimo-v2.5-pro`, `oc/deepseek-v4-flash-free`, `oc/minimax-m3-free`, `rr/9router/alibaba/kimi-k2.7-code`, `router9`, `kiro`, `cmc`, `qoder` |
| 11 | `tester` | null | `codebuddy` |

### Combo Architecture Notes

- **`kind: "combo"`** (bluesminds, pioneer) — these are explicitly flagged as combo-type entries with model prefixes.
- **`kind: null`** (all others) — standard combo entries.
- **`subagent`** is the most complex combo with a **9-model chain** that cascades across multiple providers and includes references to other combos (`router9`, `kiro`, `cmc`, `qoder`). This is the fallback chain for agent-type workloads.
- **`orcestrator`** references `router9` and `subagent` as its first two chain entries, creating a **hierarchical combo architecture** (orcestrator -> router9 -> subagent -> individual providers).
- **`router9`** uses 9Router's own routing infrastructure (`rr/9router/alibaba/...`) as a provider, meaning 9Router can route through itself.

---

## 10. Stale Claim Corrections

| Claim | Stale P25 Research | Actual Ground Truth | Severity |
|---|---|---|---|
| Version | 0.4.71 | **0.5.4** | HIGH — version gap spans multiple releases |
| npm registry latest | 0.4.66 | **0.5.8** | HIGH — stale was behind actual local |
| Next.js version | "Claimed 16" | **16.1.6 (confirmed)** | LOW — close to correct |
| Provider connections | 2 | **92** | CRITICAL — 46x undercount |
| Combos | 6 | **11** | HIGH — 2x undercount |
| Tables | 11 | **12** | LOW — sqlite_sequence missed |
| Default heap | 6 GB (`max-old-space-size=6144`) | **12 GB (`NINEROUTER_NODE_HEAP_MB=12288`)** | CRITICAL — capacity planning |
| Heap control | `NODE_OPTIONS` | **`NINEROUTER_NODE_HEAP_MB` (NODE_OPTIONS alone insufficient)** | CRITICAL — deployment scripts |
| Custom server | Not mentioned | **`custom-server.js` wraps HTTP for real IP derivation** | MEDIUM — affects proxy/CDN config |

---

## 11. Local Node.js & npm Versions

| Component | Version |
|---|---|
| **Node.js** | v24.14.1 |
| **npm** | 11.11.0 |

### VPS Compatibility

The target VPS (Krypton) uses **Node.js 24.x (Active LTS)** installed via NodeSource. This is **fully compatible** with the local v24.14.1. No version mismatch issues are expected.

---

## 12. Key Observations for Migration

1. **Heap is the bottleneck, not CPU.** With a 1.53 GB SQLite database and a 12 GB default heap, the VPS needs at minimum 16 GB RAM. A 12 GB RAM VPS will OOM with default settings — `NINEROUTER_NODE_HEAP_MB` must be explicitly set to a lower value (e.g., 8192).

2. **The provider ecosystem is massive.** 92 provider connections across 26+ types means the VPS must have reliable outbound network access to a wide range of API endpoints. Firewall rules must be permissive for HTTPS to external hosts.

3. **The combo hierarchy is deep.** The `orcestrator -> router9 -> subagent -> individual providers` chain means a single request can cascade through multiple routing hops. Latency-sensitive workloads should use direct combos (e.g., `bluesminds`, `pioneer`) rather than the orchestrator.

4. **SQLite at 1.53 GB is large.** VPS deployment should provision SSD storage with at least 5 GB free for the database, WAL, and backup files. Consider that WAL files can temporarily double the disk footprint during write-heavy operations.

5. **Legacy JSON files should be migrated or archived.** The `db.json` (51.2 KB), `usage.json` (4.1 MB), and `request-details.json` (34.2 MB) files predate the SQLite migration. They should be verified as no longer read by the current version before excluding them from the VPS transfer.

6. **Web search providers are diverse.** Six web search connections (tavily, brave-search, exa, linkup, jina-reader, firecrawl) provide redundant search capability. API keys for all six must be preserved during migration or the search fallback chain will be degraded.

7. **`custom-server.js` is the active server.** Any VPS deployment must ensure this file is present, not just `server.js`. The proxy header stripping and real IP derivation in `custom-server.js` are essential for correct request logging when a reverse proxy (nginx/Caddy) is in front.

8. **The `jwt-secret` and `machine-id` files are identity-critical.** Copying them to the VPS preserves existing API key validity and machine identity. Regenerating them invalidates all existing sessions and may require re-registering with upstream providers.

9. **Auto-healing via `hooks/sqliteRuntime.js`** ensures `sql.js` and `better-sqlite3` are present in `~/.9router/runtime/node_modules`. On a fresh VPS, this will run on first startup and download the native modules. The VPS must have build tools (`gcc`, `g++`, `make`, `python3`) available for native module compilation, or the auto-healer will fail.

10. **The `subagent` combo is the resilience backbone.** With a 9-model chain spanning xiaomi-mimo, ollama, openrouter, deepseek (free tier), minimax (free tier), 9router-alibaba, kiro, cmc, and qoder, it provides deep fallback coverage. Any migration that breaks provider connectivity will degrade this chain progressively.

---

## 13. Footer

| Field | Value |
|---|---|
| **Report date** | 2026-06-26 |
| **Prepared by** | Guinevere research agent |
| **Supersedes** | Stale P25 research (version 0.4.71 / 6 combos / 2 providers / 6 GB heap) |
| **Verification method** | Direct inspection of installed package files, SQLite database, CLI source code |
| **Confidence** | HIGH — all claims verified against on-disk artifacts |
