# P26 RequestDetails Autoprune Research — Safe Prune Design

| Field | Value |
|---|---|
| Scope | 9Router SQLite `requestDetails` autoprune design |
| Mode | Research/design only; no live database mutation performed |
| Output Path | `docs/setup-evidence/P26/requestdetails-autoprune/research/requestdetails-prune-design.md` |
| Date | 2026-06-27 |
| Target Retention | Keep latest 300 `requestDetails` rows ordered by `timestamp DESC, id DESC` |

## 1. Verdict

Safest strategy: prune only `requestDetails` through a single-writer maintenance command guarded by OS `flock`, preceded by a SQLite online backup and preflight row/schema checks, then execute a small transactional delete that preserves the 300 newest rows by `timestamp DESC, id DESC`. Never prune or rewrite `usageHistory`, `usageDaily`, `providerConnections`, `apiKeys`, `providerNodes`, `combos`, `settings`, or unrelated tables. Run `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, `PRAGMA wal_checkpoint(PASSIVE)`, and `PRAGMA optimize` after the mutation; log counts and IDs/timestamps only, never `data` payloads.

## 2. Evidence Inputs Read

| Source | Relevant Finding |
|---|---|
| `AGENTS.md` | Requires evidence-first workflow, secrets protection, no destructive live mutation without explicit approval, no payload exposure. |
| `research-reports/p25-current-state.md` | Local 9Router state had `requestDetails = 1,000`, `usageHistory = 270,511`, `usageDaily = 50`, provider/settings/key/combos tables present and sensitive. |
| `research-reports/P1/9router-migration-research.md` | `data.sqlite` stores provider credentials/API keys/settings/usage/request details; `requestDetails.data` may contain partial sensitive request details. |
| `docs/setup-evidence/P26/highend-2worker-tuning/implementation/sqlite-tuning.md` | P26 runtime used WAL, `wal_autocheckpoint=10000`, passive checkpoint patterns, and backup-before-mutation discipline. |
| `docs/setup-evidence/P26/highend-2worker-tuning/fixes/sqlite-repair-log.md` | Prior SQLite corruption/repair makes integrity gates mandatory before and after any DB maintenance. |
| Local read-only SQLite schema probe | `requestDetails(id TEXT PRIMARY KEY, timestamp TEXT NOT NULL, provider TEXT, model TEXT, connectionId TEXT, status TEXT, data TEXT NOT NULL)` with `idx_rd_ts ON requestDetails(timestamp DESC)`. |

## 3. Non-Negotiable Safety Constraints

1. Mutate only table `requestDetails`.
2. Keep latest 300 rows ordered by `timestamp DESC, id DESC`.
3. Never delete from, update, vacuum, rebuild, truncate, or otherwise touch:
   - `usageHistory`
   - `usageDaily`
   - `providerConnections`
   - `apiKeys`
   - `providerNodes`
   - `combos`
   - `settings`
4. Treat `requestDetails.data`, provider connection data, API keys, OAuth tokens, proxy credentials, and request payloads as sensitive.
5. Create a restorable database backup before mutation.
6. Use OS-level `flock` so only one prune job runs at a time.
7. Use a SQLite transaction with explicit pre/post counts.
8. Use `PRAGMA wal_checkpoint(PASSIVE)`, not `TRUNCATE`, to avoid aggressive writer disruption.
9. Use `PRAGMA optimize`, not `VACUUM`, for the scheduled autoprune path.
10. Log metadata only: counts, oldest/newest timestamps, hashes or truncated IDs if needed; never log payloads.

## 4. Recommended Operational Shape

### 4.1 Runtime Assumptions

| Item | Expected |
|---|---|
| DB path | `/var/lib/9router/db/data.sqlite` on VPS, or configured via `DATA_DIR/db/data.sqlite` |
| Service | 9Router PM2 cluster with SQLite WAL mode |
| Maintenance user | Same user that owns the DB, or root with ownership preserved |
| Lock path | `/var/lock/9router-requestdetails-prune.lock` |
| Backup root | `/root/p26-requestdetails-autoprune-backups/<timestamp>/` |

If the live DB path differs, resolve it from the service environment before running. Do not hardcode a path in permanent automation unless the service unit/PM2 env confirms it.

### 4.2 Why This Is Safest

- `requestDetails` has no observed child table dependency; deleting old log rows should not affect usage aggregates or provider state.
- Retention is deterministic even if two rows share the same timestamp because `id DESC` provides a stable tie-breaker.
- `flock` prevents overlapping maintenance jobs from competing with each other.
- SQLite `busy_timeout` lets the prune wait for active app writes instead of immediately failing under load.
- Online `.backup` creates a consistent DB copy without copying a hot WAL file manually.
- `wal_checkpoint(PASSIVE)` requests checkpoint progress without blocking active readers/writers aggressively.
- `PRAGMA optimize` refreshes planner statistics opportunistically without rewriting the whole database.

## 5. Exact SQL

### 5.1 Preflight SQL — Read-Only

Run before any backup or mutation. PASS only if every expected condition is true.

```sql
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;

SELECT 'schema_requestDetails',
       sql
FROM sqlite_master
WHERE type = 'table'
  AND name = 'requestDetails';

SELECT 'protected_row_counts_before',
       (SELECT COUNT(*) FROM usageHistory) AS usageHistory,
       (SELECT COUNT(*) FROM usageDaily) AS usageDaily,
       (SELECT COUNT(*) FROM providerConnections) AS providerConnections,
       (SELECT COUNT(*) FROM apiKeys) AS apiKeys,
       (SELECT COUNT(*) FROM providerNodes) AS providerNodes,
       (SELECT COUNT(*) FROM combos) AS combos,
       (SELECT COUNT(*) FROM settings) AS settings;

SELECT 'requestDetails_before',
       COUNT(*) AS total_rows,
       COUNT(DISTINCT id) AS distinct_ids,
       COUNT(timestamp) AS nonnull_timestamps,
       MIN(timestamp) AS oldest_timestamp,
       MAX(timestamp) AS newest_timestamp
FROM requestDetails;

SELECT 'candidate_delete_count',
       COUNT(*)
FROM requestDetails
WHERE id NOT IN (
  SELECT id
  FROM requestDetails
  ORDER BY timestamp DESC, id DESC
  LIMIT 300
);

PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

### 5.2 Backup SQL

Use SQLite's backup API from the CLI, not filesystem copy of a hot DB.

```sql
.timeout 30000
PRAGMA busy_timeout = 30000;
.backup '/root/p26-requestdetails-autoprune-backups/YYYYMMDD-HHMMSS/data.sqlite.backup'
```

Then verify the backup:

```sql
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;
PRAGMA integrity_check;
PRAGMA foreign_key_check;

SELECT 'backup_requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'backup_protected_counts',
       (SELECT COUNT(*) FROM usageHistory),
       (SELECT COUNT(*) FROM usageDaily),
       (SELECT COUNT(*) FROM providerConnections),
       (SELECT COUNT(*) FROM apiKeys),
       (SELECT COUNT(*) FROM providerNodes),
       (SELECT COUNT(*) FROM combos),
       (SELECT COUNT(*) FROM settings);
```

### 5.3 Mutation SQL — Delete Only Old `requestDetails`

```sql
.timeout 30000
PRAGMA busy_timeout = 30000;
PRAGMA foreign_keys = ON;

BEGIN IMMEDIATE;

CREATE TEMP TABLE prune_keep_requestDetails (
  id TEXT PRIMARY KEY
) WITHOUT ROWID;

INSERT INTO prune_keep_requestDetails (id)
SELECT id
FROM requestDetails
ORDER BY timestamp DESC, id DESC
LIMIT 300;

SELECT 'pre_delete_requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'pre_delete_keep_count', COUNT(*) FROM prune_keep_requestDetails;
SELECT 'pre_delete_delete_count',
       (SELECT COUNT(*) FROM requestDetails)
       - (SELECT COUNT(*) FROM prune_keep_requestDetails);

DELETE FROM requestDetails
WHERE NOT EXISTS (
  SELECT 1
  FROM prune_keep_requestDetails keep
  WHERE keep.id = requestDetails.id
);

SELECT 'changes_after_delete', changes();
SELECT 'post_delete_requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'post_delete_oldest_kept', MIN(timestamp) FROM requestDetails;
SELECT 'post_delete_newest_kept', MAX(timestamp) FROM requestDetails;

DROP TABLE prune_keep_requestDetails;

COMMIT;

PRAGMA integrity_check;
PRAGMA foreign_key_check;
PRAGMA wal_checkpoint(PASSIVE);
PRAGMA optimize;
```

### 5.4 Post-Mutation Protected Table Verification SQL

Compare these counts to the preflight counts. They must be identical.

```sql
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;

SELECT 'protected_row_counts_after',
       (SELECT COUNT(*) FROM usageHistory) AS usageHistory,
       (SELECT COUNT(*) FROM usageDaily) AS usageDaily,
       (SELECT COUNT(*) FROM providerConnections) AS providerConnections,
       (SELECT COUNT(*) FROM apiKeys) AS apiKeys,
       (SELECT COUNT(*) FROM providerNodes) AS providerNodes,
       (SELECT COUNT(*) FROM combos) AS combos,
       (SELECT COUNT(*) FROM settings) AS settings;

SELECT 'requestDetails_after',
       COUNT(*) AS total_rows,
       COUNT(DISTINCT id) AS distinct_ids,
       COUNT(timestamp) AS nonnull_timestamps,
       MIN(timestamp) AS oldest_timestamp,
       MAX(timestamp) AS newest_timestamp
FROM requestDetails;

SELECT 'newer_than_kept_boundary_violation',
       COUNT(*)
FROM requestDetails rd
WHERE 300 < (
  SELECT COUNT(*)
  FROM requestDetails newer_or_equal
  WHERE newer_or_equal.timestamp > rd.timestamp
     OR (
       newer_or_equal.timestamp = rd.timestamp
       AND newer_or_equal.id > rd.id
     )
);

PRAGMA integrity_check;
PRAGMA foreign_key_check;
```

The boundary-violation query should return `0`; it confirms the remaining rows form a top-300 set under the selected ordering.

## 6. Exact Shell Wrapper Design

This wrapper is the recommended shape for a one-shot manual run or cron/systemd timer body. It intentionally avoids printing payload data.

```bash
#!/usr/bin/env bash
set -euo pipefail

DB_PATH="${DB_PATH:-/var/lib/9router/db/data.sqlite}"
LOCK_PATH="${LOCK_PATH:-/var/lock/9router-requestdetails-prune.lock}"
BACKUP_ROOT="${BACKUP_ROOT:-/root/p26-requestdetails-autoprune-backups}"
TS="$(date +%Y%m%d-%H%M%S)"
RUN_DIR="${BACKUP_ROOT}/${TS}"
LOG_PATH="${RUN_DIR}/requestdetails-prune.log"
BACKUP_PATH="${RUN_DIR}/data.sqlite.backup"

mkdir -p "$RUN_DIR"
chmod 700 "$RUN_DIR"

exec 9>"$LOCK_PATH"
if ! flock -n 9; then
  printf '%s status=SKIP reason=lock-held\n' "$(date --iso-8601=seconds)" >> "$LOG_PATH"
  exit 0
fi

printf '%s status=START db=%s backup=%s\n' "$(date --iso-8601=seconds)" "$DB_PATH" "$BACKUP_PATH" >> "$LOG_PATH"

sqlite3 "$DB_PATH" <<'SQL' >> "$LOG_PATH"
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;
SELECT 'requestDetails_before', COUNT(*), COUNT(DISTINCT id), COUNT(timestamp), MIN(timestamp), MAX(timestamp) FROM requestDetails;
SELECT 'protected_before',
       (SELECT COUNT(*) FROM usageHistory),
       (SELECT COUNT(*) FROM usageDaily),
       (SELECT COUNT(*) FROM providerConnections),
       (SELECT COUNT(*) FROM apiKeys),
       (SELECT COUNT(*) FROM providerNodes),
       (SELECT COUNT(*) FROM combos),
       (SELECT COUNT(*) FROM settings);
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SQL

sqlite3 "$DB_PATH" ".timeout 30000" "PRAGMA busy_timeout = 30000;" ".backup '$BACKUP_PATH'"

sqlite3 "$BACKUP_PATH" <<'SQL' >> "$LOG_PATH"
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;
SELECT 'backup_requestDetails', COUNT(*), COUNT(DISTINCT id), COUNT(timestamp), MIN(timestamp), MAX(timestamp) FROM requestDetails;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SQL

sqlite3 "$DB_PATH" <<'SQL' >> "$LOG_PATH"
.timeout 30000
PRAGMA busy_timeout = 30000;
PRAGMA foreign_keys = ON;
BEGIN IMMEDIATE;
CREATE TEMP TABLE prune_keep_requestDetails (id TEXT PRIMARY KEY) WITHOUT ROWID;
INSERT INTO prune_keep_requestDetails (id)
SELECT id
FROM requestDetails
ORDER BY timestamp DESC, id DESC
LIMIT 300;
SELECT 'pre_delete_requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'pre_delete_keep_count', COUNT(*) FROM prune_keep_requestDetails;
SELECT 'pre_delete_delete_count', (SELECT COUNT(*) FROM requestDetails) - (SELECT COUNT(*) FROM prune_keep_requestDetails);
DELETE FROM requestDetails
WHERE NOT EXISTS (
  SELECT 1
  FROM prune_keep_requestDetails keep
  WHERE keep.id = requestDetails.id
);
SELECT 'changes_after_delete', changes();
SELECT 'post_delete_requestDetails_count', COUNT(*) FROM requestDetails;
SELECT 'post_delete_oldest_kept', MIN(timestamp) FROM requestDetails;
SELECT 'post_delete_newest_kept', MAX(timestamp) FROM requestDetails;
DROP TABLE prune_keep_requestDetails;
COMMIT;
PRAGMA integrity_check;
PRAGMA foreign_key_check;
PRAGMA wal_checkpoint(PASSIVE);
PRAGMA optimize;
SQL

sqlite3 "$DB_PATH" <<'SQL' >> "$LOG_PATH"
.timeout 30000
PRAGMA query_only = ON;
PRAGMA busy_timeout = 30000;
SELECT 'protected_after',
       (SELECT COUNT(*) FROM usageHistory),
       (SELECT COUNT(*) FROM usageDaily),
       (SELECT COUNT(*) FROM providerConnections),
       (SELECT COUNT(*) FROM apiKeys),
       (SELECT COUNT(*) FROM providerNodes),
       (SELECT COUNT(*) FROM combos),
       (SELECT COUNT(*) FROM settings);
SELECT 'requestDetails_after', COUNT(*), COUNT(DISTINCT id), COUNT(timestamp), MIN(timestamp), MAX(timestamp) FROM requestDetails;
SELECT 'newer_than_kept_boundary_violation',
       COUNT(*)
FROM requestDetails rd
WHERE 300 < (
  SELECT COUNT(*)
  FROM requestDetails newer_or_equal
  WHERE newer_or_equal.timestamp > rd.timestamp
     OR (
       newer_or_equal.timestamp = rd.timestamp
       AND newer_or_equal.id > rd.id
     )
);
PRAGMA integrity_check;
PRAGMA foreign_key_check;
SQL

printf '%s status=END log=%s\n' "$(date --iso-8601=seconds)" "$LOG_PATH" >> "$LOG_PATH"
```

## 7. Logging Policy

Allowed log fields:

- Start/end timestamps.
- DB path and backup path.
- RequestDetails row counts before/after.
- Protected table row counts before/after.
- Oldest/newest timestamps in retained `requestDetails`.
- SQLite `integrity_check`, `foreign_key_check`, `wal_checkpoint(PASSIVE)`, and `optimize` status.
- Exit status and high-level error class.

Forbidden log fields:

- `requestDetails.data`.
- Request or response bodies.
- Authorization headers.
- Provider API keys, OAuth access tokens, OAuth refresh tokens.
- Full `providerConnections.data`.
- `apiKeys.key`.
- Raw payload snippets, even for failed requests.

If row identity evidence is needed, log at most an HMAC or SHA-256 hash of `id` with a run-local salt stored only in the backup directory. Do not log raw payload.

## 8. Pass/Fail Criteria

### 8.1 Preflight PASS

| Check | PASS Criteria | FAIL Action |
|---|---|---|
| DB exists/readable | `data.sqlite` opens with sqlite3 | Halt; do not backup/mutate |
| Schema present | `requestDetails` table exists with `id`, `timestamp`, `data` columns | Halt; schema drift needs manual review |
| Timestamp usable | `COUNT(timestamp) = COUNT(*)` for `requestDetails` | Halt; ordering is unsafe |
| Integrity | `PRAGMA integrity_check` returns exactly `ok` | Halt; repair/restore before prune |
| Foreign keys | `PRAGMA foreign_key_check` returns no rows | Halt; investigate DB consistency |
| Protected tables exist | All protected tables can be counted | Halt; DB is not expected 9Router schema |

### 8.2 Backup PASS

| Check | PASS Criteria | FAIL Action |
|---|---|---|
| Backup file created | Backup path exists and size > 0 | Halt; do not mutate |
| Backup integrity | Backup `PRAGMA integrity_check` returns `ok` | Halt; do not mutate |
| Backup row parity | Backup protected counts and `requestDetails` count match preflight | Halt; do not mutate |
| Backup permissions | Backup dir mode `0700`; backup not world-readable | Fix permissions before continuing |

### 8.3 Mutation PASS

| Check | PASS Criteria | FAIL Action |
|---|---|---|
| Lock acquired | `flock -n` succeeds, or job exits `SKIP` with no mutation | If lock held, skip safely |
| Transaction | `BEGIN IMMEDIATE` through `COMMIT` completes | Rollback automatically; restore only if integrity fails |
| Target table only | SQL contains only `DELETE FROM requestDetails`; no protected-table DML | Reject script |
| Retention count | Post-prune `requestDetails` count is `MIN(before_count, 300)` | Restore backup and investigate |
| Keep ordering | Boundary violation query returns `0` | Restore backup and investigate |
| Protected counts | All protected table counts exactly match preflight | Restore backup immediately |
| Integrity after | `PRAGMA integrity_check` returns `ok` | Restore backup or run repair workflow |
| FK after | `PRAGMA foreign_key_check` returns no rows | Restore backup and investigate |
| Checkpoint | `PRAGMA wal_checkpoint(PASSIVE)` returns normally | Warn if busy; do not fail if DB integrity/counts pass |
| Optimize | `PRAGMA optimize` returns normally | Warn if unavailable; do not fail if DB integrity/counts pass |

### 8.4 Logging PASS

| Check | PASS Criteria | FAIL Action |
|---|---|---|
| No payload | Log has no `requestDetails.data` values or request bodies | Delete/redact log; rotate evidence |
| No secrets | Log has no API keys/tokens/auth headers | Treat as incident; rotate affected secrets if exposed |
| Sufficient evidence | Log includes counts, integrity, FK, checkpoint, optimize | Re-run read-only verification and append metadata-only evidence |

## 9. Rollback Strategy

Rollback is needed if post-prune checks fail, protected table counts change, or 9Router exhibits DB-related failures after prune.

```bash
pm2 stop 9router
cp -a /var/lib/9router/db/data.sqlite "/root/p26-requestdetails-autoprune-backups/rollback-bad-$(date +%Y%m%d-%H%M%S).sqlite"
cp -a "/root/p26-requestdetails-autoprune-backups/YYYYMMDD-HHMMSS/data.sqlite.backup" /var/lib/9router/db/data.sqlite
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check;'
pm2 start 9router
```

Rollback PASS:

- Restored DB `PRAGMA integrity_check` returns `ok`.
- 9Router starts and health/model endpoint smoke test passes.
- Protected table counts match the backup/preflight counts.
- Incident log records reason for rollback without payloads/secrets.

## 10. Automation Recommendation

Use a systemd timer or cron job with conservative cadence, such as hourly or daily. The prune is idempotent:

- If `requestDetails <= 300`, delete count is `0`.
- If another job is running, `flock` exits cleanly with `SKIP`.
- If preflight or backup fails, mutation never begins.

Do not run this as part of every request path. Keep it out-of-band so user-facing request latency is unaffected and failures are isolated to maintenance.

## 11. Final Design Decision

Adopt metadata-only, backup-gated, lock-guarded SQLite maintenance:

1. Acquire `flock`.
2. Run read-only preflight counts and integrity checks.
3. Create and verify SQLite `.backup`.
4. In one transaction, keep latest 300 `requestDetails` by `timestamp DESC, id DESC` and delete only older `requestDetails`.
5. Verify protected table counts are unchanged.
6. Run `PRAGMA integrity_check`, `PRAGMA foreign_key_check`, `PRAGMA wal_checkpoint(PASSIVE)`, and `PRAGMA optimize`.
7. Log only metadata, never payload/secrets.

This satisfies the requested retention behavior while minimizing risk to provider credentials, API keys, usage accounting, combo routing, and settings.

## 12. Footer

Research artifact only. No live database mutation, service restart, deployment, destructive operation, or secret/payload extraction was performed while producing this design.
