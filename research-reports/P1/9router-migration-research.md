# 9Router v0.4.66 — Windows → Linux Migration Research

**Date**: 2026-06-01
**Source**: decolua/9router (master branch), multiple forks, GitHub issues
**Scope**: Data directory structure, SQLite schema, jwt-secret/machine-id, migration considerations, platform compatibility

---

## 1. Data Directory Structure

### 1.1 Default Path Resolution

From `src/lib/dataDir.js` (source):

| Platform | Default Path | Falls Back To |
|----------|-------------|---------------|
| **Windows** | `%APPDATA%\9router\` → `C:\Users\<user>\AppData\Roaming\9router\` | `os.homedir() + \AppData\Roaming\9router` |
| **macOS/Linux** | `~/.9router/` → `/home/<user>/.9router/` | — |
| **Docker** | `/app/data/` (via `DATA_DIR=/app/data`) | — |
| **Custom** | Whatever `DATA_DIR` env var is set to | Falls back to default if not writable |

**Source**: [`src/lib/dataDir.js`](https://github.com/decolua/9router/blob/master/src/lib/dataDir.js)

```js
function defaultDir() {
  if (process.platform === "win32") {
    return path.join(process.env.APPDATA || path.join(os.homedir(), "AppData", "Roaming"), APP_NAME);
  }
  return path.join(os.homedir(), `.${APP_NAME}`);
}
```

### 1.2 Complete Data Directory Layout

Based on [`DOCKER.md`](https://github.com/decolua/9router/blob/master/DOCKER.md), [`src/lib/db/paths.js`](https://github.com/decolua/9router/blob/master/src/lib/db/paths.js), and runtime observation:

```
$DATA_DIR/                          # e.g., ~/.9router/ or %APPDATA%\9router\
├── db/
│   ├── data.sqlite                 # ⭐ MAIN SQLite database — ALL persistent state
│   ├── data.sqlite-wal             # SQLite WAL (write-ahead log) — safe to skip
│   ├── data.sqlite-shm             # SQLite shared memory — safe to skip
│   └── backups/                    # Auto-generated backups during upgrades
│       ├── migrate-from-json-<ts>/ # Backup of legacy JSON files (one-time)
│       ├── upgrade-<old>-to-<new>/ # Backup of data.sqlite before app upgrade
│       └── schema-<from>-to-<to>/  # Backup of data.sqlite before schema upgrade
├── jwt-secret                      # 🔑 Auto-generated JWT secret (if JWT_SECRET env not set)
├── machine-id                      # 🆔 Machine identity (used for Cloud Sync)
├── .migrated-from-json             # Marker file: indicates legacy JSON → SQLite migration was done
├── .env                            # ⚙️ Runtime env overrides (optional, user-created)
```

### 1.3 Legacy JSON Files (pre-SQLite, v0.4.x)

These files exist if the installation was upgraded from an older version. In v0.4.66, the SQLite migration already runs on first boot and imports these into `data.sqlite`. **They are no longer read by the runtime (v0.4.66 — `usageDb.js` is a shim re-exporting from SQLite).**

```
$DATA_DIR/
├── db.json                         # Legacy: providers, combos, aliases, keys, settings
├── usage.json                      # Legacy: usage history, daily summaries
├── disabledModels.json             # Legacy: disabled models per provider
├── request-details.json            # Legacy: request details (if ENABLE_REQUEST_LOGS)
├── request-details.sqlite          # Legacy: request details in SQLite
├── log.txt                         # Legacy: rolling request log
```

**Source**: [`src/lib/db/migrate.js` — `LEGACY_FILES`](https://github.com/decolua/9router/blob/master/src/lib/db/migrate.js#L5-L10)

```js
export const LEGACY_FILES = {
  main: path.join(DATA_DIR, "db.json"),
  usage: path.join(DATA_DIR, "usage.json"),
  disabled: path.join(DATA_DIR, "disabledModels.json"),
  details: path.join(DATA_DIR, "request-details.json"),
};
```

---

## 2. SQLite Database Schema (`data.sqlite`)

**Source**: [`src/lib/db/schema.js`](https://github.com/decolua/9router/blob/master/src/lib/db/schema.js)

### 2.1 Tables and What They Store

| Table | Purpose | Contains API Keys? | Path-Sensitive? |
|-------|---------|-------------------|-----------------|
| `_meta` | Key-value metadata (schemaVersion, appVersion, migratedAt, totalRequestsLifetime) | No | No |
| `settings` | Dashboard settings (cloudEnabled, password_hash, stickyRoundRobin, etc.) as JSON blob | No | No |
| `providerConnections` | ⭐ **Provider auth connections** — OAuth tokens, API keys, provider configs | **YES — all provider API keys and tokens in `data` column** | No |
| `providerNodes` | Custom compatible node endpoints (baseUrl, apiType, prefix) | No | **Contains `baseUrl` endpoint URLs but no local filesystem paths** |
| `proxyPools` | Proxy pool configurations | **YES — proxy auth in `data` column** | No |
| `apiKeys` | ⭐ **9Router local API keys** for CLI tool auth | **YES — full API keys in `key` column** | No |
| `combos` | Model combo definitions (ordered fallback sequences) | No | No |
| `kv` | Generic key-value store (modelAliases, customModels, mitmAlias, pricing, disabledModels) | No | No |
| `usageHistory` | Per-request usage history (tokens, costs, provider, model) | Partial — `apiKey` column stores key identifier | No |
| `usageDaily` | Daily usage summary aggregates | No | No |
| `requestDetails` | Detailed request logs (if enabled) | Partial — embedded in `data` blob | No |

### 2.2 Where Provider API Keys Live

In `providerConnections` table, the `data` column (TEXT/JSON blob) stores all provider-specific auth:

- `apiKey` — API key for key-based providers (OpenRouter, GLM, MiniMax, etc.)
- `accessToken` — OAuth access token
- `refreshToken` — OAuth refresh token
- `expiresAt` — Token expiry timestamp
- `providerSpecificData` — Provider-specific config (JSON)

### 2.3 Where Local API Keys Live

In `apiKeys` table:
- `key` column — The actual API key used by CLI tools to authenticate with 9Router
- `machineId` column — Associates key with a machine identity (for Cloud Sync)

### 2.4 Schema Version & Migrations

- Current `SCHEMA_VERSION`: **1**
- Migration system in [`src/lib/db/migrate.js`](https://github.com/decolua/9router/blob/master/src/lib/db/migrate.js) is **skip-version safe**: applies all pending migrations sequentially
- Versioned migrations in `src/lib/db/migrations/index.js`
- Additive schema sync (`syncSchemaFromTables`) auto-adds missing columns/indexes without dropping anything

---

## 3. jwt-secret & machine-id — Purpose

### 3.1 `jwt-secret` file

| Aspect | Detail |
|--------|--------|
| **Location** | `$DATA_DIR/jwt-secret` |
| **Purpose** | Auto-generated JWT signing secret for dashboard auth cookie |
| **Override** | Set `JWT_SECRET` env var to override file-based secret |
| **Regenerable?** | **YES — but will invalidate all existing dashboard sessions** |
| **Migration critical?** | **YES — MUST preserve OR set JWT_SECRET env var** or you'll be logged out |

**Source**: [rsorrentino/9router fork README](https://github.com/rsorrentino/9router) and `.env.example`:

> `JWT_SECRET` — Auto-generated (`~/.9router/jwt-secret`) | JWT signing secret for dashboard auth cookie (override to share across instances)

### 3.2 `machine-id` file

| Aspect | Detail |
|--------|--------|
| **Purpose** | Stable machine identity for Cloud Sync feature |
| **Override** | `MACHINE_ID_SALT` env var controls the hashing salt |
| **Regenerable?** | **YES — but will break Cloud Sync device identity** |
| **Migration critical?** | Only if using Cloud Sync; otherwise regenerable |

From [`.env.example`](https://github.com/decolua/9router/blob/master/.env.example):

> `MACHINE_ID_SALT=endpoint-proxy-salt` — Salt for stable machine ID hashing

The machine ID is used by Cloud Sync endpoints: `POST /sync/{machineId}` and related APIs. If you're using Cloud Sync, preserving the machine-id ensures continuity.

---

## 4. Migration/Built-in Backup Behavior

9Router's [`src/lib/db/migrate.js`](https://github.com/decolua/9router/blob/master/src/lib/db/migrate.js) has a built-in automatic backup system:

### 4.1 Backup Triggers

| Event | Backup Created | Backup Location |
|-------|---------------|-----------------|
| Legacy JSON → SQLite import (one-time) | ✅ `migrate-from-json-<ts>/` backup of all legacy JSON files | `$DATA_DIR/db/backups/` |
| App version bump (e.g., v0.4.65 → v0.4.66) | ✅ `upgrade-<oldVer>-to-<newVer>/` backup of `data.sqlite` | `$DATA_DIR/db/backups/` |
| Schema migration only | ✅ `schema-<from>-to-<to>/` backup of `data.sqlite` | `$DATA_DIR/db/backups/` |

### 4.2 Safety Mechanisms

- **Atomic migration**: Runs inside a SQLite SAVEPOINT transaction — rollback on failure
- **Row-count assertions**: `importWithAssertion()` verifies all rows inserted before COMMIT
- **Marker file** (`.migrated-from-json`): Prevents re-importing legacy JSON if SQLite is wiped
- **Old backup pruning**: Automatic (configurable retention)

---

## 5. Windows → Linux Migration: File Classification

### 5.1 ESSENTIAL — Must Migrate (Contains secrets/state)

| File | Why Essential | Platform-Sensitive? |
|------|--------------|-------------------|
| `db/data.sqlite` | ⭐ **ALL provider API keys, tokens, combos, settings, usage** | **No** — SQLite stores IDs and JSON, no platform paths |
| `jwt-secret` | Dashboard auth; regenerating = force logout | No — plain text secret |
| `machine-id` | Cloud Sync device identity (if used) | No — plain text |

### 5.2 CACHE/DERIVED — Safe to Regenerate

| File | Reason |
|------|--------|
| `db/data.sqlite-wal` | SQLite WAL — created on next SQLite open |
| `db/data.sqlite-shm` | SQLite shared memory — created on next SQLite open |
| `db/backups/` | Auto-regenerated on next upgrade trigger |
| `.migrated-from-json` | Marker — v0.4.66 already has data in SQLite |

### 5.3 LEGACY (v0.4.x JSON files) — Safe to Skip

| File | Status on v0.4.66 |
|------|-------------------|
| `db.json` | Already migrated into SQLite; kept as backup |
| `usage.json` | Already migrated into SQLite; kept as backup |
| `disabledModels.json` | Already migrated into SQLite; kept as backup |
| `request-details.json` | Already migrated into SQLite; kept as backup |
| `request-details.sqlite` | Separate SQLite DB (if `ENABLE_REQUEST_LOGS` was on) |
| `log.txt` | Rolling log — disposable |

### 5.4 Platform-Specific Notes

| Item | Risk | Mitigation |
|------|------|-----------|
| **SQLite WAL files** | WAL checkpoint may contain uncommitted writes | Run `PRAGMA wal_checkpoint(TRUNCATE)` before copying, or simply delete .wal/.shm after safe copy — SQLite recovers on next open |
| **Windows line endings (CRLF)** in `jwt-secret` / `machine-id` | **Potential issue** — trailing `\r\n` vs `\n` | Use `sed -i 's/\r$//'` on these files after migration, or regenerate on Linux side |
| **File permissions** | `data.sqlite` must be readable by 9Router process | Set `chmod 600` for sensitive files, `chmod 755` for directories |
| **DATA_DIR env var** | On Linux, default is `~/.9router` not `%APPDATA%` | Set `DATA_DIR=/home/guinevere/.9router` explicitly for Ubuntu |

---

## 6. KNOWN BUG: Issue #138 — usageDb/requestDetailsDb Ignore DATA_DIR

**Critical context for your migration**:

**Source**: [GitHub Issue #138](https://github.com/decolua/9router/issues/138)

### 6.1 Bug Summary

**Status**: Closed (2026-05-17) — **Not Planned** (won't fix in current architecture)

In v0.4.x (legacy JSON storage), `usageDb.js` and `requestDetailsDb.js` used `os.homedir()` to resolve storage paths, **ignoring the `DATA_DIR` env variable**. This meant:

| Module | Legacy File | Storage Path | Respects DATA_DIR? |
|--------|------------|-------------|-------------------|
| `src/lib/localDb.js` | `db.json` | `${DATA_DIR}/db.json` | ✅ Yes |
| `src/lib/usageDb.js` | `usage.json` | `~/.9router/usage.json` | ❌ **No** |
| `src/lib/usageDb.js` | `log.txt` | `~/.9router/log.txt` | ❌ **No** |
| `src/lib/requestDetailsDb.js` | `request-details.sqlite` | `~/.9router/request-details.sqlite` | ❌ **No** |

### 6.2 Status in v0.4.66 (SQLite-based)

**PARTIALLY FIXED**: In v0.4.66, `usageDb.js` is a **shim** that re-exports from `@/lib/db/index.js` — the SQLite-based layer. Usage data is now stored in `data.sqlite` (which respects `DATA_DIR`).

**However**, if `ENABLE_REQUEST_LOGS=true`, the legacy `requestDetailsDb.js` may still write outside `DATA_DIR`.

### 6.3 Migration Implication

**For your migration** (Windows → Ubuntu VPS):
- **If you use DATA_DIR**: Main SQLite (`data.sqlite`) goes where `DATA_DIR` points. Everything in SQLite is safe.
- **Watch out for**: The `~/.9router/` symlink behavior in Docker (docs mention `/root/.9router -> /app/data` symlink).
- **Safe approach**: Set `DATA_DIR=/home/guinevere/.9router` explicitly. Copy the entire `C:\Users\faizz\AppData\Roaming\9router\` directory to `/home/guinevere/.9router/`.

---

## 7. Migration Step-by-Step Recommendations

### Recommended Procedure

```bash
# ON WINDOWS (before stopping 9Router):
# 1. Ensure SQLite WAL is checkpointed
#    (9Router uses periodic WAL checkpoints every 60s, but run this to be safe)
#    → Just copy the files; SQLite handles recovery automatically

# 2. Copy the entire data directory
#    Source: C:\Users\faizz\AppData\Roaming\9router\
#    → Contains: db/, jwt-secret, machine-id, .migrated-from-json, legacy *.json

# ON UBUNTU (target VPS):
# 3. Create target directory
mkdir -p /home/guinevere/.9router/db/backups

# 4. Copy files (via scp, rsync, or whatever method)
#    scp -r 'C:\Users\faizz\AppData\Roaming\9router\*' guinevere@vps:/home/guinevere/.9router/

# 5. Fix line endings (Windows CRLF → Linux LF)
sed -i 's/\r$//' /home/guinevere/.9router/jwt-secret
sed -i 's/\r$//' /home/guinevere/.9router/machine-id

# 6. Set correct permissions
chmod 755 /home/guinevere/.9router
chmod 755 /home/guinevere/.9router/db
chmod 600 /home/guinevere/.9router/jwt-secret
chmod 600 /home/guinevere/.9router/machine-id
chmod 600 /home/guinevere/.9router/db/data.sqlite

# 7. Start 9Router with exact DATA_DIR
export DATA_DIR=/home/guinevere/.9router
export JWT_SECRET=$(cat /home/guinevere/.9router/jwt-secret)
npm run start
```

### Minimal Migration (if you just want the secrets)

Only these files are **absolutely required**:

1. **`db/data.sqlite`** — All provider connections with API keys, settings, combos
2. **`jwt-secret`** — Dashboard login continuity (or set `JWT_SECRET` env var to override)

Everything else is regenerable or already migrated into SQLite.

---

## 8. Source References

| Document | URL |
|----------|-----|
| DOCKER.md (data layout) | https://github.com/decolua/9router/blob/master/DOCKER.md |
| .env.example (env vars) | https://github.com/decolua/9router/blob/master/.env.example |
| src/lib/dataDir.js (path resolution) | https://github.com/decolua/9router/blob/master/src/lib/dataDir.js |
| src/lib/db/paths.js (file paths) | https://github.com/decolua/9router/blob/master/src/lib/db/paths.js |
| src/lib/db/schema.js (SQLite schema) | https://github.com/decolua/9router/blob/master/src/lib/db/schema.js |
| src/lib/db/migrate.js (migration logic) | https://github.com/decolua/9router/blob/master/src/lib/db/migrate.js |
| src/lib/usageDb.js (v0.4.66 shim) | https://github.com/decolua/9router/blob/master/src/lib/usageDb.js |
| docs/ARCHITECTURE.md (system design) | https://github.com/fdkgenie/9router/blob/HEAD/docs/ARCHITECTURE.md |
| Issue #138 (usageDb/DATA_DIR bug) | https://github.com/decolua/9router/issues/138 |
| README.md (env vars table) | https://github.com/decolua/9router/blob/master/README.md |

---

## 9. Summary

| Question | Answer |
|----------|--------|
| **Essential files to migrate?** | `db/data.sqlite` + `jwt-secret` + optionally `machine-id` |
| **What's in data.sqlite?** | All provider credentials (API keys/tokens), combos, settings, usage history — 11 tables |
| **What are cache/derived?** | `.wal`/`.shm` files, backups dir, legacy JSON files (already migrated), `.migrated-from-json` marker |
| **jwt-secret purpose?** | JWT signing secret for dashboard auth; preserve it or set `JWT_SECRET` env var |
| **machine-id purpose?** | Cloud Sync device identity; regenerate ok if not using Cloud Sync |
| **Platform-sensitive paths in SQLite?** | **No** — all IDs and JSON data; no absolute filesystem paths are stored |
| **Windows CRLF risk?** | **Yes** — `jwt-secret` and `machine-id` files may have trailing `\r`; run `sed -i 's/\r$//'` |
| **WAL checkpoint?** | 9Router auto-checks every 60s; safe to copy .sqlite file directly (SQLite recovers) |
| **Migration exists in 9Router?** | Built-in: `migrate.js` handles JSON→SQLite + versioned migrations + auto-backups |
| **Recommendation?** | Copy entire `%APPDATA%\9router\` → `~/.9router/`, fix CRLF, set `DATA_DIR` explicitly |