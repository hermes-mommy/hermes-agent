# P26 9Router VPS SQLite Lock Analysis

Date: 2026-06-27  
Role: read-only SQLite auditor sub-agent  
Host: `ninerouter-vps` via `root@49.12.82.34 -p 39999`  
Scope: 9Router SQLite lock/readiness audit only  
Output path: `docs/setup-evidence/P26/highend-2worker-tuning/research/sqlite-lock-analysis.md`

## Verdict

`PASS WITH RECOMMENDATIONS`: SQLite is already in WAL mode and the app source already attempts a reasonable PRAGMA set, but recent PM2 logs contain real `SQLITE_BUSY` and `SQLITE_BUSY_SNAPSHOT` evidence under the current 2-worker PM2 topology. The safest next tuning is not only DB-level PRAGMA confirmation; it should also adjust connection-level busy timeout/retry behavior and reduce checkpoint contention from the per-worker `wal_checkpoint(TRUNCATE)` timer.

## Safety Boundary

- Read `C:\Users\faizz\guinevere\AGENTS.md` before substantive work.
- No VPS mutation was performed.
- No service restart, firewall change, Tailscale change, database write, provider/key mutation, or non-output file edit was performed.
- Secret-like log fragments were not included in this report. Some runtime logs showed masked key/account fragments; those are intentionally omitted here.
- The only local file written by this sub-agent is this markdown report.

## Commands Run

Local:

```powershell
Get-Content -LiteralPath 'C:\Users\faizz\guinevere\AGENTS.md'
rg -n "sqlite|SQLITE_BUSY|database is locked|\.db|journal_mode|busy_timeout|9router|nine|router" -S .
rg --files -g "*.md" -g "*.py" -g "*.service" -g "*.env.example" -g "*.toml" -g "*.yaml" -g "*.yml"
Get-Content -LiteralPath 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\9router-hightraffic-tuning-2026-06-27.md'
Get-Content -LiteralPath 'C:\Users\faizz\guinevere\vps-mirror\systemd-live\guinevere-9router.service'
Get-Content -LiteralPath 'C:\Users\faizz\guinevere\ecosystem.config.js'
Test-Path -LiteralPath 'C:\Users\faizz\guinevere\docs\setup-evidence\P26\highend-2worker-tuning\research'
```

Remote read-only inspection:

```bash
hostname
date -Is
ps -eo pid,ppid,user,stat,etime,cmd --sort=pid | grep -E '([p]m2|[9]router|custom-server|next)'
systemctl is-active pm2-root.service
systemctl show pm2-root.service -p FragmentPath -p DropInPaths -p ActiveState -p NRestarts -p ExecMainPID --no-pager
ls -ld /root/9router /root/9router/.next/standalone /var/lib/9router /root/.pm2/logs
find /root/9router /var/lib/9router /root/.pm2 -xdev -type f \( -name '*.db' -o -name '*.sqlite' -o -name '*.sqlite3' -o -name '*sqlite*' \) -printf '%p\t%s bytes\t%TY-%Tm-%Td %TH:%TM:%TS\n'
journalctl --no-pager --since '24 hours ago' | grep -Ei 'SQLITE_BUSY|SQLITE_LOCKED|database is locked|database locked|SQLITE_BUSY_SNAPSHOT'
grep -RInE 'SQLITE_BUSY|SQLITE_LOCKED|database is locked|database locked|SQLITE_BUSY_SNAPSHOT' /root/.pm2/logs
command -v sqlite3
sqlite3 --version
stat -c '%n size=%s mode=%a owner=%U:%G mtime=%y' /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm
lsof -nP /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA database_list; PRAGMA journal_mode; PRAGMA synchronous; PRAGMA busy_timeout; PRAGMA wal_autocheckpoint; PRAGMA locking_mode; PRAGMA temp_store; PRAGMA cache_size; PRAGMA mmap_size; PRAGMA page_size; PRAGMA page_count; PRAGMA foreign_keys; PRAGMA auto_vacuum; PRAGMA integrity_check;'
grep -RInE 'pragma|journal_mode|busy_timeout|wal_autocheckpoint|better-sqlite3|sqliteRuntime|timeout' /root/9router/cli /root/9router/src /root/9router/.next/standalone
sed -n '1,80p' /root/9router/src/lib/db/schema.js
sed -n '1,90p' /root/9router/src/lib/db/adapters/betterSqliteAdapter.js
sed -n '1,90p' /root/9router/src/lib/db/driver.js
sed -n '1,120p' /root/9router/src/lib/db/paths.js
sed -n '1,140p' /root/9router/src/lib/dataDir.js
grep -RInE '\[DB\] Driver|file: /var/lib/9router|data.sqlite' /root/.pm2/logs
ls -ld /root/.9router /root/.9router/db
stat -c '%n size=%s inode=%i dev=%d mtime=%y' /root/.9router/db/data.sqlite /root/.9router/db/data.sqlite-wal /root/.9router/db/data.sqlite-shm /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite-wal /var/lib/9router/db/data.sqlite-shm
readlink -f /root/.9router/db/data.sqlite /var/lib/9router/db/data.sqlite
findmnt -T /root/.9router/db/data.sqlite
findmnt -T /var/lib/9router/db/data.sqlite
sqlite3 'file:/root/.9router/db/data.sqlite?mode=ro' 'PRAGMA database_list; PRAGMA journal_mode; PRAGMA synchronous; PRAGMA busy_timeout; PRAGMA wal_autocheckpoint; PRAGMA locking_mode; PRAGMA temp_store; PRAGMA cache_size; PRAGMA mmap_size; PRAGMA page_size; PRAGMA page_count; PRAGMA foreign_keys; PRAGMA auto_vacuum; PRAGMA integrity_check;'
ls -l /root/.9router/db /var/lib/9router/db
stat -L -c '%n size=%s inode=%i dev=%d mtime=%y' /root/.9router/db/data.sqlite /var/lib/9router/db/data.sqlite
find /root/.9router /var/lib/9router -maxdepth 3 -type f \( -name '*.sqlite' -o -name '*.sqlite-wal' -o -name '*.sqlite-shm' -o -name '*.db' \) -printf '%p\t%s bytes\t%TY-%Tm-%Td %TH:%TM:%TS\n'
stat -c '%n mtime=%y size=%s' /root/.pm2/logs/9router-error-0.log /root/.pm2/logs/9router-out-1.log
nl -ba /root/.pm2/logs/9router-error-0.log | sed -n '180,220p'
nl -ba /root/.pm2/logs/9router-out-1.log | sed -n '2696,2732p'
```

## DB Path Discovery Method

Discovery used three independent signals:

1. Runtime process topology:
   - PM2 daemon PID `24174`.
   - Two Next.js workers: PIDs `31108` and `31121`.
   - `pm2-root.service` is active, `NRestarts=0`, with drop-in `/etc/systemd/system/pm2-root.service.d/limits.conf`.
2. File discovery:
   - `/var/lib/9router/db/data.sqlite`
   - `/var/lib/9router/db/data.sqlite-shm`
   - `/var/lib/9router/db/data.sqlite-wal`
3. App path resolution:
   - `/root/9router/src/lib/dataDir.js` uses `process.env.DATA_DIR`, otherwise `~/.9router`.
   - `/root/9router/src/lib/db/paths.js` defines `DATA_FILE = path.join(DATA_DIR, "db", "data.sqlite")`.
   - PM2 logs report app driver path as `/root/.9router/db/data.sqlite`.
   - `/root/.9router/db/data.sqlite` is a symlink to `/var/lib/9router/db/data.sqlite`.

Confirmed symlink:

```text
/root/.9router/db/data.sqlite -> /var/lib/9router/db/data.sqlite
```

Confirmed both paths resolve to the same target:

```text
/root/.9router/db/data.sqlite size=963706880 inode=920567
/var/lib/9router/db/data.sqlite size=963706880 inode=920567
```

Canonical current DB path for commands:

```text
/var/lib/9router/db/data.sqlite
```

Application-facing path:

```text
/root/.9router/db/data.sqlite
```

## Current DB State

SQLite CLI:

```text
/usr/bin/sqlite3
3.45.1
```

Database files:

```text
/var/lib/9router/db/data.sqlite size=963706880 mode=644 owner=root:root
/var/lib/9router/db/data.sqlite-wal size=0 mode=644 owner=root:root
/var/lib/9router/db/data.sqlite-shm size=32768 mode=644 owner=root:root
```

Recent DB backups exist:

```text
/var/lib/9router/db/data.sqlite.before-rifalos-aliases-20260627-151125.bak
/var/lib/9router/db/data.sqlite.before-router9-aliases-20260627-151635.bak
/var/lib/9router/db/data.sqlite.pre-import.bak
/var/lib/9router/db/backups/upgrade-0.5.4-to-0.5.8-0.5.8-20260626-172853/data.sqlite
```

`lsof` produced no open-handle rows during the sampled instant. This is not proof that the app is disconnected; it only means the one-time sample did not catch open file handles or `lsof` had no matching output.

## Current PRAGMAs

Read using:

```bash
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA database_list; PRAGMA journal_mode; PRAGMA synchronous; PRAGMA busy_timeout; PRAGMA wal_autocheckpoint; PRAGMA locking_mode; PRAGMA temp_store; PRAGMA cache_size; PRAGMA mmap_size; PRAGMA page_size; PRAGMA page_count; PRAGMA foreign_keys; PRAGMA auto_vacuum; PRAGMA integrity_check;'
```

Observed output:

```text
database_list: 0|main|/var/lib/9router/db/data.sqlite
journal_mode: wal
synchronous: 2
busy_timeout: 0
wal_autocheckpoint: 1000
locking_mode: normal
temp_store: 0
cache_size: -2000
mmap_size: 0
page_size: 4096
page_count: 235280
foreign_keys: 0
auto_vacuum: 0
integrity_check: ok
```

Interpretation caveat:

- `journal_mode=wal` is a database-level state and is meaningful for the current DB.
- `busy_timeout`, `synchronous`, `temp_store`, `cache_size`, `mmap_size`, and `foreign_keys` are connection-level or connection-observed. The read-only CLI connection showed its own defaults, not necessarily the active 9Router worker connection state.
- The app source executes `PRAGMA_SQL` during adapter initialization, so the active better-sqlite3 connections should be closer to the source PRAGMA block than the read-only CLI connection output.

## Current App PRAGMA Source

Source file inspected:

```text
/root/9router/src/lib/db/schema.js
```

Current `PRAGMA_SQL` block:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 30000000;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

Adapter behavior inspected:

```text
/root/9router/src/lib/db/adapters/betterSqliteAdapter.js
```

Important behavior:

- 9Router is using `better-sqlite3`.
- The adapter calls `db.exec(PRAGMA_SQL)` at initialization.
- Each worker has its own process and DB connection.
- A periodic checkpoint timer runs every 60 seconds.
- The timer calls `wal_checkpoint(TRUNCATE)`.
- Shutdown also calls `wal_checkpoint(TRUNCATE)`.

This matters because two PM2 workers can both try to checkpoint/truncate WAL independently. `TRUNCATE` is more disruptive than `PASSIVE` and can contend with active readers/writers.

## Recent Lock Evidence

Journal scan:

```text
No matching `SQLITE_BUSY`, `SQLITE_LOCKED`, `database is locked`, or `SQLITE_BUSY_SNAPSHOT` lines found in system journal during the sampled 24-hour window.
```

PM2 log scan found lock evidence:

```text
/root/.pm2/logs/9router-error-0.log: SqliteError: database is locked
/root/.pm2/logs/9router-error-0.log: code: 'SQLITE_BUSY'
/root/.pm2/logs/9router-out-1.log: Error creating provider: SqliteError: database is locked
/root/.pm2/logs/9router-out-1.log: code: 'SQLITE_BUSY'
/root/.pm2/logs/9router-out-1.log: code: 'SQLITE_BUSY_SNAPSHOT'
```

Log file mtimes:

```text
/root/.pm2/logs/9router-error-0.log mtime=2026-06-27 17:33:43 +0700
/root/.pm2/logs/9router-out-1.log mtime=2026-06-27 17:59:49 +0700
```

Representative sanitized context:

```text
SqliteError: database is locked
  at Object.run (...)
  at sqliteTransaction (...)
  at Object.transaction (...)
  at async onRequestSuccess (...)
code: 'SQLITE_BUSY'

Error creating provider: SqliteError: database is locked
  at Object.run (...)
  at Object.transaction (...)
  at async providers route (...)
code: 'SQLITE_BUSY'

Error creating provider: SqliteError: database is locked
code: 'SQLITE_BUSY_SNAPSHOT'
```

Meaning:

- There is real SQLite lock contention, not only perceived slowness.
- The lock appears in both usage/request success persistence and provider creation paths.
- `SQLITE_BUSY_SNAPSHOT` suggests a read transaction tried to promote to write after the underlying DB changed; retrying the whole transaction is usually required.

## Safe High-Concurrency PRAGMAs for Current DB

Recommended connection-level PRAGMA block for 2 PM2 workers sharing one SQLite DB:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;
PRAGMA wal_autocheckpoint = 10000;
```

Rationale:

- `journal_mode=WAL`: already active; keep it.
- `synchronous=NORMAL`: already in app source; good WAL throughput/safety tradeoff for this workload.
- `busy_timeout=30000`: current app source is `5000`; 30s is safer for bursty 2-worker writes and provider/config operations.
- `wal_autocheckpoint=10000`: raises checkpoint threshold from default 1000 pages to about 40 MiB at 4096-byte pages, reducing checkpoint frequency under write bursts.
- `mmap_size=268435456`: 256 MiB memory mapping can improve read-heavy workloads on a roughly 964 MiB DB without changing data semantics.
- `cache_size=-64000`: app already sets about 64 MiB page cache; safe to keep.
- `temp_store=MEMORY`: app already sets this; safe for transient temp operations.

Important:

- Most of these must be applied on every app DB connection. A one-time `sqlite3` command will not permanently change connection-local settings for future better-sqlite3 connections.
- For durable effect, update 9Router's app PRAGMA initialization and redeploy/restart through the approved P26 deployment gate.

## Recommended Code-Level Changes

1. In `PRAGMA_SQL`, change:

```sql
PRAGMA mmap_size = 30000000;
PRAGMA busy_timeout = 5000;
```

to:

```sql
PRAGMA mmap_size = 268435456;
PRAGMA busy_timeout = 30000;
PRAGMA wal_autocheckpoint = 10000;
```

2. In the better-sqlite3 adapter, replace periodic cross-worker `wal_checkpoint(TRUNCATE)` with either:

```js
db.pragma("wal_checkpoint(PASSIVE)");
```

or make checkpointing leader-only so only one worker performs it.

3. Add bounded retry around write transactions that can safely retry:

- Retry on `SQLITE_BUSY`.
- Retry the whole transaction on `SQLITE_BUSY_SNAPSHOT`.
- Use small jittered backoff, for example 25ms, 75ms, 150ms, 300ms, 600ms, max 5 attempts.
- Do not retry non-idempotent external side effects unless the DB write is clearly separated from the external action.

4. Keep provider/account/token values out of logs. Existing logs showed masked key fragments, but DB lock diagnostics should not include any credential material.

## Exact Recommended Commands

These are recommended future commands only. They were not executed by this audit.

### Preflight Read-Only

```bash
ssh -p 39999 root@49.12.82.34
date -Is
systemctl is-active pm2-root.service
pm2 status
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' \
  'PRAGMA journal_mode; PRAGMA wal_autocheckpoint; PRAGMA page_size; PRAGMA page_count; PRAGMA integrity_check;'
grep -RInE 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked' /root/.pm2/logs | tail -n 80
```

### Backup Before Any Mutation

Use SQLite's backup API, not a raw copy of a live WAL database:

```bash
ts="$(date +%Y%m%d-%H%M%S)"
sqlite3 /var/lib/9router/db/data.sqlite ".backup '/var/lib/9router/db/backups/pre-sqlite-tuning-${ts}.sqlite'"
sqlite3 'file:/var/lib/9router/db/backups/pre-sqlite-tuning-'"${ts}"'.sqlite?mode=ro' 'PRAGMA integrity_check;'
```

### Apply App PRAGMA Source Change

Preferred: edit source/release artifact through the normal deployment workflow. The target PRAGMA block should be:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 30000;
PRAGMA wal_autocheckpoint = 10000;
```

### Optional DB-Level Confirmation

Run only during the approved maintenance/apply step:

```bash
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA journal_mode=WAL; PRAGMA wal_autocheckpoint=10000; PRAGMA integrity_check;'
```

Note: `busy_timeout`, `mmap_size`, `cache_size`, `temp_store`, `foreign_keys`, and `synchronous` still need app connection initialization because they are not reliable as one-time persistent DB settings.

### Post-Apply Verification

```bash
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' \
  'PRAGMA journal_mode; PRAGMA wal_autocheckpoint; PRAGMA page_size; PRAGMA page_count; PRAGMA integrity_check;'

pm2 logs 9router --lines 200 --nostream | grep -Ei 'SQLITE_BUSY|SQLITE_BUSY_SNAPSHOT|database is locked' || true

hey -n 1000 -c 100 http://127.0.0.1:20128/v1/models
```

For write-path verification, use an approved non-secret, non-destructive app route/test that exercises provider/settings write behavior. Do not use real provider credentials in logs or evidence.

## Rollback

Rollback should restore both the application PRAGMA behavior and, if needed, the database backup.

### Roll Back App Change

Restore previous PRAGMA block:

```sql
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 30000000;
PRAGMA cache_size = -64000;
PRAGMA foreign_keys = ON;
PRAGMA busy_timeout = 5000;
```

Then redeploy/restart only through the approved P26 gate.

### Roll Back DB File

Only if the DB itself is damaged or the apply step created unexpected DB-level behavior:

```bash
systemctl stop pm2-root.service
cp -a /var/lib/9router/db/data.sqlite "/var/lib/9router/db/data.sqlite.bad-rollback-$(date +%Y%m%d-%H%M%S)"
cp -a /var/lib/9router/db/backups/pre-sqlite-tuning-YYYYMMDD-HHMMSS.sqlite /var/lib/9router/db/data.sqlite
sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check;'
systemctl start pm2-root.service
```

This stop/start is a future rollback command and was not run by this audit.

## Risks

| Risk | Impact | Mitigation |
|---|---|---|
| Two PM2 workers share one SQLite writer lane | WAL still permits only one writer at a time | Longer busy timeout plus write retry/queueing |
| `SQLITE_BUSY_SNAPSHOT` | Transaction fails even with WAL if stale read snapshot promotes to write | Retry the full transaction |
| Per-worker `wal_checkpoint(TRUNCATE)` timer | Can compete with active reads/writes every minute | Use `PASSIVE` or leader-only checkpoint |
| Larger `mmap_size` | More virtual address mapping; usually not resident RSS until touched | 256 MiB is conservative for current VPS and DB size |
| Longer busy timeout | Requests may wait longer instead of failing fast | Combine with metrics and bounded retries |
| One-time SQLite PRAGMA command gives false confidence | Many PRAGMAs are connection-local | Update app initialization, then verify runtime behavior |

## Acceptance Criteria Mapping

| Requirement | Result |
|---|---|
| Read AGENTS.md first | PASS |
| Do not mutate VPS | PASS |
| Discover DB path | PASS |
| Include DB path discovery method | PASS |
| Include current PRAGMAs if readable | PASS |
| Include recent lock evidence | PASS |
| Include safe high-concurrency PRAGMAs | PASS |
| Include risks | PASS |
| Include exact recommended commands | PASS |
| Include rollback/verification | PASS |
| Do not print secrets in report | PASS |

## Final Recommendation

Do not treat kernel/NOFILE tuning as sufficient for this issue. The current evidence points at SQLite write contention inside the 2-worker app. Apply app-level SQLite tuning in the next approved P26 step:

1. Raise `busy_timeout` from 5s to 30s.
2. Add `wal_autocheckpoint=10000`.
3. Increase `mmap_size` to 256 MiB.
4. Replace per-worker `wal_checkpoint(TRUNCATE)` timer with `PASSIVE` or leader-only checkpointing.
5. Add bounded retry for `SQLITE_BUSY` and full transaction retry for `SQLITE_BUSY_SNAPSHOT`.

Footer: P26 9Router highend 2-worker tuning SQLite read-only audit, generated 2026-06-27.
