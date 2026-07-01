# P26 RequestDetails Autoprune — systemd/Cron Research

**Date:** 2026-06-27  
**Scope:** Read-only research for automatic pruning of 9Router `requestDetails` rows on `root@49.12.82.34 -p 39999`.  
**Output Path:** `docs/setup-evidence/P26/requestdetails-autoprune/research/systemd-timer-analysis.md`  
**Operator Constraint:** Read-only only on VPS. No unit creation, no `daemon-reload`, no service/timer enablement, no pruning executed.

---

## 1. Verdict

**Recommend a systemd timer that runs a small oneshot SQLite maintenance service, not cron.**

The safest production mechanism is:

1. Keep 9Router's built-in `requestDetails` cap as the first line of defense.
2. Add a systemd timer as an independent backstop that enforces the same row cap against the canonical SQLite DB path.
3. Use SQLite-native locking with `busy_timeout`, a bounded `DELETE`, WAL checkpointing, and no shell globbing or broad filesystem cleanup.

Cron is acceptable for simple periodic commands, but systemd timer is safer here because it provides first-class logs, exit status, dependency ordering, missed-run behavior through `Persistent=true`, resource controls, and hardening directives.

---

## 2. Read-Only VPS Facts

### 2.1 Host and Scheduler State

| Item | Observed Value |
|---|---|
| Hostname | `ninerouter-vps` |
| OS | Ubuntu 24.04.4 LTS, Noble |
| systemd | `systemd 255 (255.4-1ubuntu8.16)` |
| Cron daemon | Installed and active: `/usr/sbin/cron`, `cron.service` running |
| Existing custom timer match | No `*guinevere*timer`, `*9router*timer`, or `*request*timer` unit files found |
| Existing 9Router unit | `9router.service` exists, disabled unit-file state but running via systemd/PM2 context was observable |

### 2.2 Existing 9Router Service

Read-only `systemctl cat 9router.service` showed:

```ini
[Unit]
Description=9Router AI Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/9router/.next/standalone
EnvironmentFile=/var/lib/9router/.env
Environment=NODE_OPTIONS=--max-old-space-size=3584
ExecStart=/usr/bin/node /root/9router/.next/standalone/custom-server.js
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 2.3 9Router Version and RequestDetails Code

VPS source at `/root/9router/package.json` reports app version `0.5.8`.

`/root/9router/src/lib/db/repos/requestDetailsRepo.js` contains a built-in retention cap:

- `DEFAULT_MAX_RECORDS = 200`
- Configurable by settings or `OBSERVABILITY_MAX_RECORDS`
- Batched writes with `DEFAULT_BATCH_SIZE = 20`
- Flush interval `DEFAULT_FLUSH_INTERVAL_MS = 5000`
- After each flush, the repo checks `SELECT COUNT(*) as c FROM requestDetails`
- If count exceeds configured max, it deletes the oldest rows by `timestamp`

Relevant behavior, paraphrased from source:

```js
const cnt = db.get(`SELECT COUNT(*) as c FROM requestDetails`);
if (cnt && cnt.c > config.maxRecords) {
  db.run(
    `DELETE FROM requestDetails WHERE id IN (SELECT id FROM requestDetails ORDER BY timestamp ASC LIMIT ?)`,
    [cnt.c - config.maxRecords]
  );
}
```

This means an external auto-prune job should be a conservative backstop, not the primary writer.

### 2.4 SQLite Runtime State

Read-only SQLite inspection found:

| Path | Finding |
|---|---|
| `/var/lib/9router/db/data.sqlite` | Canonical populated DB path |
| `/root/.9router/db/data.sqlite` | Symlink/path indirection observed; `readlink -f` resolves to `/var/lib/9router/db/data.sqlite` |
| `requestDetails` rows | `1000` |
| `usageHistory` rows | `5965` |
| `journal_mode` | `wal` |
| `page_count` | `235280` |
| `freelist_count` | `79170` |
| `page_size` | `4096` |

The row count being exactly `1000` suggests the runtime settings or environment already cap observability rows at 1000, despite the source default being 200.

### 2.5 Data Sensitivity

`requestDetails.data` is a JSON blob and may contain request/response content. The source sanitizes obvious header secrets such as authorization, API key, cookie, and token headers before persistence, but payload content can still be sensitive. The prune job must not log row contents, dump JSON, or copy data to external tools.

---

## 3. Mechanism Comparison

| Mechanism | Pros | Cons | Recommendation |
|---|---|---|---|
| 9Router built-in cap | Already implemented; runs inside app transaction; knows configured max | Only runs on requestDetails flush; cannot recover if app path changes or cap logic regresses | Keep enabled as primary retention |
| systemd timer + oneshot service | Journaled, auditable, hardenable, missed runs supported, can be resource-limited | Requires unit installation and daemon reload during implementation | Best independent backstop |
| cron | Simple and already available | Weak observability, no native hardening, no dependency model, poorer missed-run behavior | Avoid unless systemd timer is unavailable |
| App code change | Best semantic control | Higher blast radius; requires build/deploy of 9Router | Not needed for P26 auto-prune backstop |

---

## 4. Recommended Design

### 4.1 Retention Policy

Use a conservative fixed cap:

```text
KEEP_ROWS=1000
```

Rationale:

- VPS currently has exactly 1000 `requestDetails` rows.
- Keeping 1000 preserves current operator-visible behavior.
- The job becomes idempotent: if rows are already at or below 1000, it deletes nothing.
- This avoids surprise loss of recent observability data.

If disk pressure becomes the main driver, lower in a separate reviewed change, for example to 500 or 200.

### 4.2 Schedule

Recommended timer:

```text
OnCalendar=*:0/15
RandomizedDelaySec=120
Persistent=true
```

Rationale:

- 15-minute cadence is frequent enough to bound growth if app-side pruning stops.
- Randomized delay avoids bunching with other hourly/daily maintenance.
- `Persistent=true` catches missed runs after reboot.

### 4.3 SQLite Operation

Use one bounded transaction:

```sql
PRAGMA busy_timeout=30000;
BEGIN IMMEDIATE;
WITH doomed AS (
  SELECT id
  FROM requestDetails
  ORDER BY timestamp DESC
  LIMIT -1 OFFSET 1000
)
DELETE FROM requestDetails
WHERE id IN (SELECT id FROM doomed);
COMMIT;
PRAGMA wal_checkpoint(TRUNCATE);
PRAGMA optimize;
```

Notes:

- `busy_timeout=30000` waits up to 30 seconds if 9Router is writing.
- `BEGIN IMMEDIATE` obtains the write lock before selecting doomed rows, avoiding a stale selection between count and delete.
- `ORDER BY timestamp DESC LIMIT -1 OFFSET 1000` keeps the newest 1000 rows and deletes older rows.
- `wal_checkpoint(TRUNCATE)` bounds WAL growth after deletion.
- `PRAGMA optimize` is low-risk routine SQLite maintenance.
- Do not run frequent full `VACUUM`; it requires more I/O and stronger write-lock behavior. Use full `VACUUM` only as a manual maintenance action after backup and a planned stop window.

---

## 5. Proposed Unit Content

These are proposed files only. They were **not** created on the VPS.

### 5.1 `/etc/systemd/system/9router-requestdetails-prune.service`

```ini
[Unit]
Description=Prune 9Router requestDetails SQLite rows
Documentation=internal:P26-requestdetails-autoprune
Wants=9router.service
After=9router.service

[Service]
Type=oneshot
User=root
Group=root
Environment=DB_PATH=/var/lib/9router/db/data.sqlite
Environment=KEEP_ROWS=1000
ExecCondition=/usr/bin/test -f ${DB_PATH}
ExecStart=/usr/bin/sqlite3 ${DB_PATH} "PRAGMA busy_timeout=30000; BEGIN IMMEDIATE; WITH doomed AS (SELECT id FROM requestDetails ORDER BY timestamp DESC LIMIT -1 OFFSET ${KEEP_ROWS}) DELETE FROM requestDetails WHERE id IN (SELECT id FROM doomed); COMMIT; PRAGMA wal_checkpoint(TRUNCATE); PRAGMA optimize;"

# Hardening. SQLite needs write access to the DB file and its directory for WAL/SHM/lock files.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/9router/db
ReadOnlyPaths=/usr/bin/sqlite3 /usr/lib /lib /lib64
PrivateDevices=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictRealtime=true
LockPersonality=true
MemoryDenyWriteExecute=true
SystemCallArchitectures=native
SystemCallFilter=@system-service
RestrictAddressFamilies=AF_UNIX

# Operational bounds.
TimeoutStartSec=60
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
```

### 5.2 `/etc/systemd/system/9router-requestdetails-prune.timer`

```ini
[Unit]
Description=Run 9Router requestDetails pruning every 15 minutes
Documentation=internal:P26-requestdetails-autoprune

[Timer]
OnBootSec=5min
OnCalendar=*:0/15
RandomizedDelaySec=120
Persistent=true
Unit=9router-requestdetails-prune.service

[Install]
WantedBy=timers.target
```

---

## 6. Hardening Compatibility Notes

### 6.1 Why `ProtectSystem=strict` Is Compatible

`ProtectSystem=strict` makes most of the filesystem read-only for the service. The explicit exception:

```ini
ReadWritePaths=/var/lib/9router/db
```

allows SQLite to write:

- `data.sqlite`
- `data.sqlite-wal`
- `data.sqlite-shm`
- temporary lock-related files in the same directory if needed

### 6.2 Why Use Canonical `/var/lib/9router/db/data.sqlite`

The VPS exposes path indirection from `/root/.9router/db/data.sqlite` to `/var/lib/9router/db/data.sqlite`. The prune service should use the canonical `/var/lib/9router/db/data.sqlite` path so `ProtectHome=true` can remain enabled and the unit does not need write access under `/root`.

### 6.3 Why `RestrictAddressFamilies=AF_UNIX`

The service only needs local filesystem access to SQLite. It should not need IPv4/IPv6 networking. `AF_UNIX` is enough for normal local Unix operations.

### 6.4 Why Not `DynamicUser=true`

`DynamicUser=true` complicates write access to an existing root-owned SQLite directory. The current 9Router service runs as `root`, and the DB is owned by `root:root`, so the least-surprise implementation is a root oneshot with strong filesystem and syscall restrictions.

Future improvement: create a dedicated `9router` system user and migrate the app service plus DB ownership together. Do not do that as part of this prune-only change unless explicitly scoped.

---

## 7. Verification Commands

All commands below are proposed implementation verification commands. The research pass did not create units or run pruning.

### 7.1 Preflight

```bash
systemd-analyze verify /etc/systemd/system/9router-requestdetails-prune.service /etc/systemd/system/9router-requestdetails-prune.timer
systemctl cat 9router.service
test -f /var/lib/9router/db/data.sqlite
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA quick_check;'
sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) AS requestDetails_count FROM requestDetails;"
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA journal_mode;'
```

Expected:

- `systemd-analyze verify` exits `0`.
- `PRAGMA quick_check` returns `ok`.
- DB exists at `/var/lib/9router/db/data.sqlite`.
- `journal_mode` is `wal`.

### 7.2 Dry-Run Candidate Count

```bash
sqlite3 /var/lib/9router/db/data.sqlite "SELECT MAX(COUNT(*) - 1000, 0) AS rows_that_would_be_deleted FROM requestDetails;"
sqlite3 /var/lib/9router/db/data.sqlite "SELECT MIN(timestamp) AS oldest_kept_after_prune FROM (SELECT timestamp FROM requestDetails ORDER BY timestamp DESC LIMIT 1000);"
```

Expected:

- If count is `1000`, `rows_that_would_be_deleted` is `0`.
- The oldest-kept timestamp should be plausible and recent enough for operational needs.

### 7.3 First Manual Run After Installation

Only after explicit approval to install units:

```bash
systemctl daemon-reload
systemctl start 9router-requestdetails-prune.service
systemctl status 9router-requestdetails-prune.service --no-pager
journalctl -u 9router-requestdetails-prune.service -n 50 --no-pager
sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) AS requestDetails_count FROM requestDetails;"
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA quick_check;'
```

Expected:

- Service exits successfully.
- Row count is `<= 1000`.
- `quick_check` returns `ok`.
- Journal contains no row content or payload data.

### 7.4 Timer Activation Verification

Only after explicit approval to enable timer:

```bash
systemctl enable --now 9router-requestdetails-prune.timer
systemctl list-timers 9router-requestdetails-prune.timer --all --no-pager
systemctl status 9router-requestdetails-prune.timer --no-pager
```

Expected:

- Timer is enabled and active.
- Next run is scheduled.

### 7.5 Ongoing Health Checks

```bash
journalctl -u 9router-requestdetails-prune.service --since '24 hours ago' --no-pager
sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM requestDetails;"
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA wal_checkpoint(PASSIVE);'
systemctl is-active 9router.service
```

Expected:

- No repeated SQLite busy/lock failures.
- Row count remains bounded.
- 9Router remains active.

---

## 8. Rollback

### 8.1 Disable Only the Timer

```bash
systemctl disable --now 9router-requestdetails-prune.timer
```

This stops future automatic prune runs without touching the service file or DB.

### 8.2 Remove Units

Only after timer is disabled:

```bash
rm /etc/systemd/system/9router-requestdetails-prune.timer
rm /etc/systemd/system/9router-requestdetails-prune.service
systemctl daemon-reload
systemctl reset-failed 9router-requestdetails-prune.service 9router-requestdetails-prune.timer
```

This is a destructive file removal and requires explicit per-action approval under repo rules.

### 8.3 Data Rollback

Pruned `requestDetails` rows are intentionally deleted telemetry. SQLite cannot restore those rows unless a DB backup exists from before the prune.

Recommended before first enablement:

```bash
mkdir -p /var/lib/9router/db/backups
sqlite3 /var/lib/9router/db/data.sqlite ".backup '/var/lib/9router/db/backups/data-before-requestdetails-prune-$(date +%Y%m%d%H%M%S).sqlite'"
sqlite3 /var/lib/9router/db/backups/data-before-requestdetails-prune-YYYYMMDDHHMMSS.sqlite 'PRAGMA quick_check;'
```

Restore procedure, only during planned downtime:

```bash
systemctl stop 9router.service
cp /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite.rollback-copy
cp /var/lib/9router/db/backups/data-before-requestdetails-prune-YYYYMMDDHHMMSS.sqlite /var/lib/9router/db/data.sqlite
systemctl start 9router.service
systemctl status 9router.service --no-pager
sqlite3 /var/lib/9router/db/data.sqlite 'PRAGMA quick_check;'
```

Because the database contains provider/API configuration and request telemetry, backup files must remain local to the VPS, permission-restricted, and excluded from repo artifacts.

---

## 9. Safer Alternatives and Enhancements

### 9.1 Prefer Runtime Setting When Available

If 9Router exposes `OBSERVABILITY_MAX_RECORDS` through `/var/lib/9router/.env` or dashboard settings, prefer setting it to `1000` there and using the timer only as a backstop. Do not print or archive the full env file because it may contain secrets.

Read-only check:

```bash
grep -E '^(OBSERVABILITY_MAX_RECORDS|OBSERVABILITY_ENABLED|OBSERVABILITY_BATCH_SIZE|OBSERVABILITY_FLUSH_INTERVAL_MS)=' /var/lib/9router/.env
```

Do not include unrelated env values in evidence.

### 9.2 Add Metrics Later

A future implementation could expose a textfile metric:

```text
9router_requestdetails_rows 1000
9router_requestdetails_prune_last_success_timestamp_seconds 178...
```

Do this only if there is already a node-exporter textfile collector directory and ownership model.

### 9.3 Avoid Full Vacuum on Timer

The current DB has a large freelist count. A full `VACUUM` could reclaim disk, but it is not suitable for frequent timer execution because it rewrites the database and can hold locks longer. Use a one-time manual maintenance window instead.

---

## 10. Risks and Mitigations

| Risk | Impact | Mitigation |
|---|---|---|
| SQLite write lock contention with 9Router | Prune run fails or delays app write briefly | `busy_timeout=30000`, short transaction, timer retry on next interval |
| Deletes useful observability rows | Loss of older request details | Keep newest 1000, pre-enable backup, do not prune `usageHistory` |
| Hardening blocks DB writes | Service fails | Use canonical `/var/lib/9router/db` with `ReadWritePaths` |
| Full DB copied into repo/evidence | Secret or request payload exposure | Never copy DB or row payloads into repo artifacts |
| Cron job silently fails | Unbounded row growth | Use systemd timer and journal instead of cron |
| Frequent `VACUUM` causes I/O spike | App latency or downtime | Do not run full `VACUUM` in timer |

---

## 11. Acceptance Criteria Mapping

| Requirement | Status |
|---|---|
| Read `AGENTS.md` first | PASS |
| Read-only only on VPS | PASS |
| No unit creation | PASS |
| No daemon reload | PASS |
| Recommend safest auto-prune mechanism | PASS — systemd timer backstop plus built-in cap |
| Include service/timer unit content | PASS |
| Include hardening compatible with SQLite file access | PASS |
| Include verification commands | PASS |
| Include rollback | PASS |
| Avoid secrets/request payload exposure | PASS |
| Write full markdown to exact path | PASS |

---

## 12. Footer

| Field | Value |
|---|---|
| Evidence Type | Research report |
| VPS Action Level | Read-only inspection only |
| Files Modified Locally | `docs/setup-evidence/P26/requestdetails-autoprune/research/systemd-timer-analysis.md` |
| Server Files Modified | None |
| Boundary Compliance | No secrets copied, no raw request rows copied, no daemon reload, no unit creation, no pruning |
| Final Recommendation | Use `9router-requestdetails-prune.timer` + hardened oneshot SQLite service as a conservative backstop; keep 1000 newest rows; pre-backup before first enablement |
