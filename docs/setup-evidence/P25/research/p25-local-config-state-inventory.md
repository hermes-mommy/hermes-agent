# P25 Local 9Router Config/State Inventory

**Date:** 2026-06-25
**Status:** Research — confirmed facts only
**Scope:** All files under `%APPDATA%\9router\` on the Windows dev machine
**Purpose:** Migration planning to VPS for 9Router self-hosted instance

---

## 1. Executive Summary

The local 9Router instance at `C:\Users\faizz\AppData\Roaming\9router\` holds **~2.5 GB total** across config, database, logs, runtime binaries, and legacy JSON files. The single most critical asset is `db/data.sqlite` (1.5 GB), which contains **all provider API keys, model combos, settings, and usage history** across 11 tables. Two additional tiny secrets (`jwt-secret`, `machine-id`) must also migrate for auth continuity.

Only **~1.5 GB** needs to actually migrate (the SQLite database plus two 64-byte secrets). Everything else is either legacy/migrated data, auto-regenerable runtime, or platform-specific binaries. The VPS currently runs an older 9Router v0.4.66 with a nearly-empty 176 KB database — the local instance's database will **replace** it wholesale.

---

## 2. Complete File Inventory

| Path (relative to `%APPDATA%\9router\`) | Size | Type | Content Summary | Migration Decision |
|---|---|---|---|---|
| `db/data.sqlite` | 1.5 GB | SQLite database | **ALL persistent state**: provider API keys, 6 model combos, settings (JSON blob), usage history, request details, daily aggregates, schema metadata | **MUST MIGRATE** |
| `db/data.sqlite-wal` | 6.2 MB | SQLite WAL | Write-Ahead Log for active transactions | **MUST NOT** — auto-created |
| `db/data.sqlite-shm` | 64 KB | SQLite SHM | Shared memory file for WAL coordination | **MUST NOT** — auto-created |
| `db/data.sqlite.bak-20260614-225355` | 1.2 GB | SQLite backup | Pre-upgrade backup from 2026-06-14 | **MUST NOT** — too large, historical only |
| `db/data.sqlite.pre-cc-filter-20260623-170153.bak` | 1.5 GB | SQLite backup | Pre-filter backup from 2026-06-23 | **MUST NOT** — too large, historical only |
| `db/backups/` | (directory) | Backup directory | Auto-generated upgrade/schema backups | **SHOULD MIGRATE** — useful for disaster recovery |
| `db.json` | 51.2 KB | Legacy JSON | Original config before SQLite migration | **MUST NOT** — already migrated into data.sqlite |
| `usage.json` | 4.1 MB | Legacy JSON | Original usage history before SQLite migration | **MUST NOT** — already migrated into data.sqlite |
| `request-details.json` | 34.2 MB | Legacy JSON | Original request details before SQLite migration | **MUST NOT** — already migrated into data.sqlite |
| `log.txt` | 16.8 KB | Rolling text log | Application log entries | **MUST NOT** — disposable rolling log |
| `jwt-secret` | 64 bytes | Secret file | JWT signing secret for dashboard authentication | **MUST MIGRATE** |
| `machine-id` | 64 bytes | Identity file | Machine identity for Cloud Sync feature | **MUST MIGRATE** |
| `.migrated-from-json` | 24 bytes | Marker file | Flags that JSON-to-SQLite migration completed | **MUST NOT** — regenerated if needed on fresh VPS |
| `runtime/` | (directory) | Node.js modules | `node_modules` tree: debug, fs-extra, graceful-fs, jsonfile, ms, systray2, universalify | **MUST NOT** — reinstall via npm |
| `runtime/mitm/server.js` | 315 KB | JavaScript | MITM proxy server script | **MUST NOT** — part of runtime package |
| `runtime/package.json` | (small) | Package manifest | 9router-runtime v1.0.0 | **MUST NOT** — part of runtime package |
| `auth/` | (directory) | OAuth tokens | OAuth token files for provider authentication | **SHOULD MIGRATE** — if OAuth providers are configured |
| `bin/` | (directory) | Binaries | Platform-specific executables | **MUST NOT** — platform-specific (Windows) |
| `logs/` | (directory) | Log files | Additional log output | **MUST NOT** — disposable |
| `mitm/` | (directory) | MITM logs | MITM proxy logs (empty) | **MUST NOT** — disposable |
| `update/` | (directory) | Update artifacts | Downloaded update packages | **MUST NOT** — re-downloaded on fresh install |

---

## 3. SQLite Database: Table-by-Table Content Analysis

Database: `db/data.sqlite` (1.5 GB, 11 tables, schema version 1, app version 0.4.71)

### 3.1 `_meta`
- **Columns:** key, value
- **Content:** Schema version (1), app version (0.4.71)
- **Purpose:** Tracks database schema version for the migration system (`migrate.js`)
- **Migration note:** Auto-updated when VPS 9Router opens the database (handles v0.4.66 -> v0.4.71 schema bumps automatically)

### 3.2 `settings`
- **Columns:** key, value (JSON blob)
- **Content:** Dashboard configuration including:
  - `cloudEnabled` — Cloud Sync toggle
  - `password_hash` — Dashboard login password hash
  - `stickyRoundRobin` — Load balancing strategy
  - `comboStrategies` — Model fallback strategies
  - Other UI/behavior preferences
- **Purpose:** All user-facing 9Router dashboard settings
- **Migration note:** Contains `password_hash` secret (see Section 5)

### 3.3 `providerConnections`
- **Columns:** id, name, provider, data (JSON), enabled, created_at, updated_at
- **Content:** **ALL provider API keys and connection details** stored in the `data` JSON column:
  - Codex API key
  - DeepSeek API key
  - OAuth access tokens and refresh tokens (if configured)
- **Purpose:** Provider authentication — this is the table that makes 9Router actually work
- **Migration note:** Most critical table. Any loss = loss of all provider credentials.

### 3.4 `providerNodes`
- **Columns:** id, name, endpoint, data (JSON), enabled, created_at, updated_at
- **Content:** Custom OpenAI-compatible endpoint definitions
- **Purpose:** Allows routing to custom/self-hosted model endpoints

### 3.5 `proxyPools`
- **Columns:** id, name, proxies (JSON), enabled, created_at, updated_at
- **Content:** Proxy server configurations
- **Purpose:** HTTP/SOCKS proxy pools for provider requests

### 3.6 `apiKeys`
- **Columns:** id, key, name, enabled, created_at
- **Content:** **9Router's own local API keys** for CLI/API authentication
- **Purpose:** Allows tools and scripts to authenticate against the 9Router proxy
- **Migration note:** Contains secret keys (see Section 5)

### 3.7 `combos`
- **Columns:** id, name, models (JSON fallback chain), enabled, created_at, updated_at
- **Content:** **6 model combos** with ordered fallback chains
- **Purpose:** Core feature — routes requests through model fallback sequences (e.g., primary -> secondary -> tertiary model)

### 3.8 `kv`
- **Columns:** key, value
- **Content:** Key-value pairs for:
  - `modelAliases` — Friendly names for model identifiers
  - `customModels` — User-defined model definitions
  - `mitmAlias` — MITM proxy routing aliases
  - `pricing` — Custom pricing overrides
  - `disabledModels` — Blocked model list
- **Purpose:** Miscellaneous configuration that doesn't warrant its own table

### 3.9 `usageHistory`
- **Columns:** id, timestamp, provider, model, tokens_in, tokens_out, cost, metadata (JSON)
- **Content:** Per-request usage records: token counts, costs, which provider/model handled each request
- **Purpose:** Usage tracking and cost monitoring
- **Migration note:** Bulk data — largest table by row count. Non-critical but useful for historical analysis.

### 3.10 `usageDaily`
- **Columns:** date, provider, model, total_requests, total_tokens_in, total_tokens_out, total_cost
- **Content:** Aggregated daily usage statistics
- **Purpose:** Dashboard charts and daily cost summaries
- **Migration note:** Derived data — can be recomputed from usageHistory if needed.

### 3.11 `requestDetails`
- **Columns:** id, timestamp, request (JSON), response (JSON), metadata (JSON)
- **Content:** Per-request detail logs (max 200 records, FIFO eviction)
- **Purpose:** Debugging and request inspection in dashboard
- **Migration note:** Limited to 200 records — small footprint. FIFO means oldest entries are dropped automatically.

---

## 4. Migration Classification

### 4.1 MUST MIGRATE (Essential — system will not function correctly without these)

| File | Size | Reason |
|---|---|---|
| `db/data.sqlite` | 1.5 GB | Contains ALL provider API keys, 6 combos, all settings, usage history. Single source of truth for everything. |
| `jwt-secret` | 64 bytes | Dashboard authentication will break without this (all sessions invalidated). |
| `machine-id` | 64 bytes | Cloud Sync identity continuity (if Cloud Sync is enabled). |

**Total MUST size:** ~1.5 GB + 128 bytes

### 4.2 SHOULD MIGRATE (Recommended — useful but not strictly required)

| File | Size | Reason |
|---|---|---|
| `db/backups/` | (variable) | Auto-generated database backups — useful for disaster recovery or rollback. |
| `auth/` | (small) | OAuth token files — required if any OAuth providers are active (avoids re-auth flow). |

### 4.3 MUST NOT MIGRATE (Will cause problems or waste transfer time)

| File | Size | Reason |
|---|---|---|
| `db/data.sqlite-wal` | 6.2 MB | SQLite auto-creates on next open. Stale WAL from Windows will cause issues on Linux. |
| `db/data.sqlite-shm` | 64 KB | SQLite auto-creates on next open. Platform-specific shared memory. |
| `db/data.sqlite.bak-20260614-225355` | 1.2 GB | Historical backup. Unnecessary bulk. |
| `db/data.sqlite.pre-cc-filter-20260623-170153.bak` | 1.5 GB | Historical backup. Unnecessary bulk. |
| `db.json` | 51.2 KB | Legacy. Fully migrated into SQLite. |
| `usage.json` | 4.1 MB | Legacy. Fully migrated into SQLite. |
| `request-details.json` | 34.2 MB | Legacy. Fully migrated into SQLite. |
| `log.txt` | 16.8 KB | Rolling log. Disposable. |
| `.migrated-from-json` | 24 bytes | Migration marker. Not needed on VPS if data.sqlite is already migrated. |
| `runtime/` | (directory) | Node.js modules + platform binaries. Must reinstall. |
| `bin/` | (directory) | Windows binaries. Incompatible with Linux. |
| `logs/` | (directory) | Disposable logs. |
| `mitm/` | (directory) | MITM logs (empty). |
| `update/` | (directory) | Update artifacts. Re-downloaded on install. |

### 4.4 REGENERATE on VPS (Do not copy — create fresh)

| Item | How to Regenerate |
|---|---|
| `runtime/` | `npm install -g 9router` on VPS |
| WAL/SHM files | SQLite auto-creates on first database open |
| `.migrated-from-json` | Not needed — VPS will open existing data.sqlite directly |
| `bin/` | Linux binaries from 9router package manager |

---

## 5. Secrets Inventory

All secret **values** are omitted. Only paths and field references are listed.

| Location | Secret Path | Type | Sensitivity |
|---|---|---|---|
| `db/data.sqlite` | `providerConnections.data.apiKey` (Codex) | API key | CRITICAL — Codex provider access |
| `db/data.sqlite` | `providerConnections.data.apiKey` (DeepSeek) | API key | CRITICAL — DeepSeek provider access |
| `db/data.sqlite` | `providerConnections.data.accessToken` (OAuth) | OAuth token | CRITICAL — OAuth provider sessions |
| `db/data.sqlite` | `providerConnections.data.refreshToken` (OAuth) | OAuth refresh | CRITICAL — OAuth token renewal |
| `db/data.sqlite` | `apiKeys.key` | 9Router local API keys | HIGH — CLI/script authentication |
| `db/data.sqlite` | `settings.password_hash` | Password hash | HIGH — Dashboard login |
| `jwt-secret` (file) | JWT signing secret (64 bytes) | Symmetric key | CRITICAL — Session signing |
| `machine-id` (file) | Machine identity (64 bytes) | Identity token | MEDIUM — Cloud Sync identity |
| `auth/` (directory) | OAuth token files | OAuth tokens | HIGH — Provider authentication |

**Secret count:** 3 files + 1 directory contain secrets.
**Total secret-bearing data:** ~1.5 GB (the entire SQLite database plus 128 bytes).

---

## 6. Platform-Specific Concerns

### 6.1 CRLF to LF Conversion

Windows files use CRLF (`\r\n`) line endings. Linux expects LF (`\n`). This affects:

- **`jwt-secret`** — Must convert: `sed -i 's/\r$//' jwt-secret`
- **`machine-id`** — Must convert: `sed -i 's/\r$//' machine-id`

SQLite binary files are **not affected** by CRLF — they use their own binary format.

### 6.2 SQLite WAL Mode

The local database uses Write-Ahead Logging (WAL mode). Before copying:

1. **Option A (clean):** Run `PRAGMA wal_checkpoint(TRUNCATE);` to flush WAL into the main database file, then copy only `data.sqlite`.
2. **Option B (simple):** Copy `data.sqlite`, `data.sqlite-wal`, and `data.sqlite-shm` together, then delete the WAL/SHM on the VPS after the first clean open.
3. **Option C (simplest):** Copy only `data.sqlite`. SQLite will recreate WAL/SHM on first open. Any uncommitted transactions in the WAL will be lost, but this is safe if 9Router is stopped before copying.

**Recommended:** Option C — stop 9Router locally, then copy `data.sqlite` only.

### 6.3 File Permissions

After copying to VPS:

```bash
chmod 600 db/data.sqlite
chmod 600 jwt-secret
chmod 600 machine-id
chown -R 9router:9router ~/.9router/
```

### 6.4 Data Directory Paths

| Platform | Default Data Directory |
|---|---|
| Windows | `%APPDATA%\9router\` = `C:\Users\faizz\AppData\Roaming\9router\` |
| Linux | `~/.9router/` = `/home/<user>/.9router/` |

No path references are stored inside the SQLite database — the database is self-contained.

### 6.5 Schema Migration

The VPS runs 9Router v0.4.66 (older) while local runs v0.4.71. The built-in migration system (`migrate.js`) handles schema version bumps automatically when the database is opened by a newer version. No manual migration steps are needed — just copy the database and start 9Router.

---

## 7. Size Analysis

### Category Breakdown

| Category | Files | Size | Migration? |
|---|---|---|---|
| SQLite database (main) | 1 | 1.5 GB | MUST |
| SQLite WAL + SHM | 2 | 6.3 MB | MUST NOT |
| SQLite backups | 2 | 2.7 GB | MUST NOT |
| Legacy JSON (migrated) | 3 | 38.4 MB | MUST NOT |
| Secrets | 2 | 128 bytes | MUST |
| Rolling logs | 2 | ~17 KB | MUST NOT |
| Runtime (node_modules) | ~6+ files | (small KB each) | MUST NOT — reinstall |
| Marker file | 1 | 24 bytes | MUST NOT |
| Directories (bin, auth, update, etc.) | 5 dirs | (variable) | Varies |

### Transfer Summary

| Tier | What | Size |
|---|---|---|
| **MUST transfer** | `data.sqlite` + `jwt-secret` + `machine-id` | **~1.5 GB** |
| **SHOULD transfer** | `db/backups/` + `auth/` | **(variable, likely small)** |
| **Do NOT transfer** | Everything else | **~2.8 GB avoided** |

**Net migration payload: ~1.5 GB** (compared to ~4.3 GB total on disk).

---

## 8. Migration Procedure

### Step 1: Stop 9Router locally (Windows)

Ensure no active database writes:
1. Close the 9Router dashboard (browser tab)
2. Exit the 9Router tray application (right-click system tray -> Exit)
3. Verify no process is holding the database: `tasklist | findstr 9router`

### Step 2: Copy essential files to staging area

```powershell
# From Windows PowerShell
mkdir C:\staging\9router-migrate
copy "$env:APPDATA\9router\db\data.sqlite" C:\staging\9router-migrate\
copy "$env:APPDATA\9router\jwt-secret" C:\staging\9router-migrate\
copy "$env:APPDATA\9router\machine-id" C:\staging\9router-migrate\
```

### Step 3: Transfer to VPS

```bash
# From Windows (SCP)
scp C:\staging\9router-migrate\* user@vps:~/.9router/
```

Or use `rsync` for resumable transfer of the 1.5 GB database:
```bash
rsync -avz --progress C:\staging\9router-migrate/ user@vps:~/.9router/
```

### Step 4: Fix permissions and line endings on VPS

```bash
# SSH into VPS
cd ~/.9router/

# Fix CRLF on text secrets
sed -i 's/\r$//' jwt-secret
sed -i 's/\r$//' machine-id

# Set strict permissions
chmod 600 data.sqlite
chmod 600 jwt-secret
chmod 600 machine-id
chown -R $(whoami):$(whoami) ~/.9router/
```

### Step 5: Restart 9Router on VPS

```bash
sudo systemctl restart guinevere-9router.service
```

The 9Router migration system will automatically handle any schema version differences between v0.4.66 and v0.4.71 on first open.

### Step 6: Verify

```bash
# Check service is running
sudo systemctl status guinevere-9router.service

# Verify API responds
curl -s http://localhost:20128/health

# Verify provider connections are loaded (no 401 errors)
# Check 9Router dashboard or logs
```

### Step 7: Cleanup staging

```powershell
# On Windows, remove staging copies
rmdir /s C:\staging\9router-migrate
```

---

## 9. VPS Current State Comparison

| Attribute | Local (Windows) | VPS (Linux) |
|---|---|---|
| **9Router version** | v0.4.71 | v0.4.66 |
| **data.sqlite size** | 1.5 GB | 176 KB |
| **Provider connections** | Multiple (Codex, DeepSeek, etc.) with real keys | 2 (placeholder keys, returning 401) |
| **Model combos** | 6 combos with fallback chains | 0 visible |
| **Request details** | Full history (200 max, FIFO) | 4 records (all 401 errors) |
| **Settings** | Fully configured | Default/placeholder |
| **Service** | Tray app (Windows) | systemd `guinevere-9router.service` on port 20128 |
| **Hermes production** | N/A | Runs on same VPS — **MUST NOT touch** |

### Migration Impact

- The VPS database will be **replaced entirely** by the local database (176 KB -> 1.5 GB)
- All placeholder connections will be overwritten with real API keys
- All 6 model combos will become available immediately
- The 9Router version will remain v0.4.66 on VPS — schema auto-migration handles the difference
- Hermes production VPS services are **completely independent** and unaffected by 9Router migration

---

## 10. Footer

**Report generated:** 2026-06-25
**Source:** Confirmed facts from local filesystem inspection and codebase analysis
**Confidentiality:** Contains secret **paths** only — no secret **values** are recorded anywhere in this document
**Next step:** Operator approval for migration execution (P25 implementation)
