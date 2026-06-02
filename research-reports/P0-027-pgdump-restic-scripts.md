# P0-027: pg_dump + restic Production Backup Patterns

**Date**: 2026-05-31
**Context**: Guinevere project — PostgreSQL on port 5433 (non-standard), co-located with Aizanta on same VPS.
**Sources**: PostgreSQL 18 docs, restic 0.18.1 docs, production backup scripts from HostMyCode, Raff Technologies, OSSAlt, Fuzz Notes, buildplan/restic-backup-script, several GitHub repos.

---

## 1. Core Architecture Pattern

### 1.1 The Battle-Tested Flow

Every production script surveyed follows the same 4-phase pipeline:

```
Phase 1: DB Dump     → pg_dumpall to temp file (or --stdin-from-command)
Phase 2: Restic Backup → restic backup /etc /opt/guinevere /var/backups/postgres
Phase 3: Retention    → restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --prune
Phase 4: Verify       → restic check --read-data-subset=5%
```

**Sources**:
- [HostMyCode — VPS Backup Strategy 2026](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore) — complete production template
- [Raff Technologies — PostgreSQL Restic Backup](https://rafftechnologies.com/learn/tutorials/back-up-postgresql-raff-object-storage-restic) — step-by-step with validation
- [buildplan/restic-backup-script](https://github.com/buildplan/restic-backup-script) — 1500+ line battle-tested script with pre-flight checks
- [stephane-klein/restic-pg_dump-docker/backup.sh](https://github.com/stephane-klein/restic-pg_dump-docker/blob/master/backup.sh) — retry loop pattern

### 1.2 pg_dumpall vs pg_dump per Database

| Approach | Pros | Cons | Use Case |
|---|---|---|---|
| `pg_dumpall > file` | Single command, includes globals (roles, tablespaces) | Plain SQL only, single file, no parallel restore | Small to medium clusters |
| `pg_dump -Fc` per DB + `pg_dumpall -g` | Custom format (compressed, parallel restore, selective restore), separate globals | More script complexity | Production with multiple DBs |
| `pg_dump --stdin-from-command` via restic | No temp file, exit code respected | Single-database only, harder to debug | Single-DB setups |

**Guinevere recommendation**: Use **pg_dumpall** for simplicity (all Guin + Aizanta DBs in one pass), since both clusters live on same PostgreSQL instance. If DBs grow large, switch to per-DB `pg_dump -Fc` with `pg_dumpall -g` for globals.

Source: [PostgreSQL 18: pg_dumpall docs](https://www.postgresql.org/docs/current/app-pg-dumpall.html)

---

## 2. Non-Standard Port (5433) — Auth Patterns

### 2.1 Specifying Port 5433

Three equivalent ways to tell pg_dumpall to connect on port 5433:

```bash
# Option A: Command-line argument (most explicit)
pg_dumpall -p 5433 -U postgres -h 127.0.0.1 -f /var/backups/postgres/guinevere-full.sql

# Option B: Environment variable
export PGPORT=5433
pg_dumpall -U postgres -h 127.0.0.1 -f /var/backups/postgres/guinevere-full.sql

# Option C: Connection string (pg_dump only, not pg_dumpall)
pg_dump --dbname=postgresql://postgres:password@127.0.0.1:5433/guinevere -Fc
```

**Important**: pg_dumpall does NOT support the connection string URI format for the `--dbname` option (it ignores the database name in the string since it dumps all DBs). Use `-p 5433` explicitly.

Sources: [PostgreSQL 18: pg_dumpall](https://www.postgresql.org/docs/current/app-pg-dumpall.html), [PostgreSQL 18: pg_dump](https://www.postgresql.org/docs/18/app-pgdump.html)

### 2.2 .pgpass File Format

```bash
# File: ~/.pgpass  (chmod 0600)
# Format: hostname:port:database:username:password
# Wildcard * matches anything

# For Guinevere (non-standard port 5433):
127.0.0.1:5433:*:postgres:supersecret

# Or with wildcard for host/port:
*:5433:*:postgres:supersecret

# Or match all local connections:
127.0.0.1:*:*:backup_user:password
```

**Critical rules**:
1. `chmod 0600 ~/.pgpass` — file is ignored if permissions are looser
2. `export PGPASSFILE=/etc/restic/pgpass` — use alternate location for scripts running as root
3. Five colon-separated fields: `hostname:port:database:username:password`
4. Escaping: `\:` for literal colon, `\\` for literal backslash

**.pgpass is preferred over PGPASSWORD environment variable** because:
- `PGPASSWORD` is visible via `ps` to other users
- `.pgpass` supports multiple credentials per host/port/db
- pg_dumpall needs to connect multiple times — `.pgpass` handles all connections silently

Sources: [PostgreSQL 18: The Password File](https://www.postgresql.org/docs/current/libpq-pgpass.html)

### 2.3 Dedicated Backup Role

```sql
-- Run as superuser once:
CREATE ROLE backup_user WITH LOGIN PASSWORD 'CHANGE_ME' REPLICATION;
GRANT pg_read_all_data TO backup_user;
```

> Using `pg_read_all_data` (PostgreSQL 14+) grants read access to all tables, sequences, and functions without per-table grants.

For older PostgreSQL versions, explicit grants are needed per database.

Source: [HostMyCode backup guide](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore)

---

## 3. Multi-Source Backup Pattern (PostgreSQL + Files + Config)

### 3.1 Master Backup Script Template

Synthesized from multiple production scripts:

```bash
#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Guinevere Production Backup Script
# Backs up: PostgreSQL (port 5433), /etc, /opt/guinevere
# Uses: pg_dumpall + restic + S3-compatible storage
# ============================================================

# --- Configuration ---
RESTIC_ENV="/etc/restic/guinevere.env"
PGPASS_FILE="/etc/restic/pgpass"
LOCK_FILE="/var/lock/restic-guinevere.lock"
LOG_FILE="/var/log/restic-guinevere-backup.log"
DUMP_DIR="/var/backups/postgres"
TS="$(date -u +%Y-%m-%dT%H-%M-%SZ)"
HOSTNAME_TAG="$(hostname -s)"

# Exclude patterns for restic (avoid backing up virtual filesystems)
EXCLUDES=(
  --exclude /proc
  --exclude /sys
  --exclude /dev
  --exclude /run
  --exclude /tmp
  --exclude /var/tmp
  --exclude /var/cache
  --exclude /var/log
  --exclude /lost+found
)

# --- Logging and Lock ---
exec > >(tee -a "$LOG_FILE") 2>&1
echo "[$TS] === Guinevere backup started ==="

# Lock: prevent overlapping runs
if ! ( set -o noclobber; echo "$$" > "$LOCK_FILE" ) 2>/dev/null; then
  echo "[$TS] WARNING: Lock exists ($LOCK_FILE). Another backup is running. Exiting."
  exit 0
fi
trap 'rm -f "$LOCK_FILE"' EXIT

# Source restic credentials (never inline passwords)
source "$RESTIC_ENV"

# --- Phase 1: PostgreSQL Dump ---
export PGPASSFILE="$PGPASS_FILE"
export PGPORT=5433  # Non-standard port

mkdir -p "$DUMP_DIR"
DUMP_FILE="${DUMP_DIR}/guinevere-all-${TS}.sql"

echo "[$TS] Creating PostgreSQL full dump (port 5433)..."
pg_dumpall \
  -h 127.0.0.1 \
  -p 5433 \
  -U backup_user \
  --clean \
  --if-exists \
  -f "$DUMP_FILE"

# Validate: check file is non-empty and has SQL content
if [ ! -s "$DUMP_FILE" ]; then
  echo "[$TS] ERROR: pg_dumpall produced empty file!"
  exit 1
fi

# Verify dump integrity with head/tail check
head -5 "$DUMP_FILE" | grep -q "PostgreSQL database dump" \
  || { echo "[$TS] ERROR: Dump file doesn't look valid"; exit 1; }

echo "[$TS] Dump created: $(du -h "$DUMP_FILE" | cut -f1)"

# --- Phase 2: Restic Backup (multi-source) ---
echo "[$TS] Running restic backup..."
restic backup \
  --tag guinevere \
  --tag "$HOSTNAME_TAG" \
  --tag "$TS" \
  "${EXCLUDES[@]}" \
  /etc \
  /opt/guinevere \
  "$DUMP_DIR"

restic_exit=$?
if [ $restic_exit -eq 1 ]; then
  echo "[$TS] FATAL: restic backup failed with exit code 1 (no snapshot created)"
  exit 1
elif [ $restic_exit -eq 3 ]; then
  echo "[$TS] WARNING: restic backup had source read errors (snapshot created with warnings)"
  # Continue — snapshot exists but some files may be missing
fi

# --- Phase 3: Retention Policy ---
echo "[$TS] Applying retention policy..."
restic forget \
  --tag guinevere \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune

# --- Phase 4: Repository Verification ---
echo "[$TS] Checking repository integrity (5% data sample)..."
restic check --read-data-subset=5%

# --- Cleanup ---
# Keep only the most recent local dump for fast restore
# Older dumps exist in restic snapshots
find "$DUMP_DIR" -name "guinevere-all-*.sql" -type f -not -name "*${TS}*" -delete

echo "[$TS] === Guinevere backup completed successfully ==="
```

**Sources**:
- [HostMyCode script](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore) (locked logging, pgpass, excludes, 4-phase flow)
- [Raff Technologies tutorial](https://rafftechnologies.com/learn/tutorials/back-up-postgresql-raff-object-storage-restic) (dump validation with pg_restore -l)
- [buildplan/restic-backup-script](https://github.com/buildplan/restic-backup-script) (pre-flight checks, lock file, exit codes)

---

## 4. restic forget — Exact Retention Command

### 4.1 Requested Retention: Daily 7 + Weekly 4 + Monthly 3

```bash
# Exact command as requested:
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --prune

# With tagging for multi-project isolation:
restic forget \
  --tag guinevere \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune

# Dry-run (preview without deleting):
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --dry-run
```

### 4.2 Retention Policy Explained

| Flag | Keeps | Behavior |
|---|---|---|
| `--keep-daily 7` | 7 most recent daily snapshots | Counts from latest, back 7 days |
| `--keep-weekly 4` | 4 most recent weekly snapshots | Counts from latest, back 4 weeks |
| `--keep-monthly 3` | 3 most recent monthly snapshots | Counts from latest, back 3 months |
| `--prune` | — | **Required** to actually free storage space |

**Without `--prune`**, `forget` only removes snapshot metadata — the data blocks remain in the repository. `--prune` removes unreferenced data.

### 4.3 Alternative: Keep-Within (Time-Based)

```bash
# Keep all snapshots from last 30 days, plus weekly for 3 months:
restic forget --keep-within 30d --keep-within-weekly 3m --prune
```

### 4.4 Retry Pattern (Network Resilience)

From [stephane-klein/restic-pg_dump-docker](https://github.com/stephane-klein/restic-pg_dump-docker/blob/master/backup.sh):

```bash
retry_count=0
max_retries=5
while ! restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune; do
  retry_count=$((retry_count + 1))
  if [ $retry_count -ge $max_retries ]; then
    echo "Reached max retries. Exiting."
    exit 1
  fi
  echo "Sleeping 10s before retry..."
  sleep 10
done
```

**Sources**:
- [GitHub: arthurgeek/vaultwarden-fly-template/scripts/restic-backup.sh](https://github.com/arthurgeek/vaultwarden-fly-template/blob/main/scripts/restic-backup.sh#L90) — exact `--keep-daily 7 --keep-weekly 4 --keep-monthly 3 --keep-yearly 3` in production
- [GitHub: frkrueger/rpow/ops/backup.sh](https://github.com/frkrueger/rpow/blob/main/ops/backup.sh#L14) — `restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 6 --prune`
- [buildplan/restic-backup-script](https://github.com/buildplan/restic-backup-script) — configuration-driven retention

---

## 5. restic check / Verify Patterns

### 5.1 Check Levels

| Command | What It Checks | Time | Frequency |
|---|---|---|---|
| `restic check` | Metadata integrity (index, packs, trees) | Fast (seconds) | Daily |
| `restic check --read-data-subset=5%` | Metadata + 5% random data blocks | Medium | Daily |
| `restic check --read-data-subset=1/50` | Metadata + 1/50 fraction of data | Medium | Daily |
| `restic check --read-data-subset=100%` | Full data read — every byte | Slow (hours) | Monthly or quarterly |

### 5.2 Recommended Check Schedule for Guinevere

```bash
# Daily backup script — lightweight metadata + 5% data sample:
restic check --read-data-subset=5%
# (Takes ~1-2 min for small repos, scales with repo size)

# Monthly maintenance — full integrity check:
# Run as separate systemd service, not inline with backup:
restic check --read-data-subset=100%

# If check fails, run full check manually:
restic check
```

Source: [HostMyCode verification section](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore)

### 5.3 Scheduled Separate Check (systemd)

The `prune` operation locks the repository. Run check separately:

```ini
# /etc/systemd/system/restic-guinevere-check.service
[Unit]
Description=Monthly full restic check for Guinevere
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/guinevere.env
ExecStart=/usr/bin/restic check --read-data-subset=100%
Nice=19
IOSchedulingClass=idle

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/restic-guinevere-check.timer
[Unit]
Description=Monthly restic integrity check for Guinevere

[Timer]
OnCalendar=Sun *-*-1..7 03:00:00
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

### 5.4 Restore Verification (Proof That Backups Work)

```bash
# Monthly restore drill — create scratch restore and test
mkdir -p /tmp/restore-test-guinevere

# Restore latest snapshot
restic restore latest --tag guinevere --target /tmp/restore-test-guinevere

# Validate PostgreSQL dump
LATEST_DUMP=$(ls -1 /tmp/restore-test-guinevere/var/backups/postgres/*.sql | tail -1)
sudo -u postgres createdb guinevere_restore_test
psql -d guinevere_restore_test -f "$LATEST_DUMP"
sudo -u postgres psql -d guinevere_restore_test \
  -c "SELECT count(*) FROM information_schema.tables;"

# Cleanup
sudo -u postgres dropdb guinevere_restore_test
rm -rf /tmp/restore-test-guinevere
```

**Source**: [HostMyCode restore drill](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore)

---

## 6. Error Handling & Safety Patterns

### 6.1 Critical: `--stdin-from-command` vs Piped `--stdin`

**DO NOT** pipe pg_dump directly to restic stdin:
```bash
# ❌ DANGEROUS — pg_dump failure produces empty backup
pg_dumpall -p 5433 -U postgres | restic backup --stdin --stdin-filename dump.sql
# If pg_dumpall fails, restic creates a snapshot with an empty file!
```

**DO** use `--stdin-from-command` (available in restic 0.17.0+):
```bash
# ✅ SAFE — restic respects the command exit code
restic backup \
  --stdin-filename guinevere-db-$(date +%Y%m%d).sql \
  --stdin-from-command \
  --tag guinevere,db \
  -- pg_dumpall -h 127.0.0.1 -p 5433 -U backup_user
```

**OR** use the temp file approach (more reliable for pg_dumpall):
```bash
# ✅ SAFE — separate validation before restic
pg_dumpall -p 5433 -U backup_user -f /tmp/dump.sql
[ -s /tmp/dump.sql ] && head -1 /tmp/dump.sql | grep -q "PostgreSQL"
restic backup /tmp/dump.sql /etc /opt/guinevere
```

Source: [restic 0.18.1 docs — Reading data from a command](https://restic.readthedocs.io/en/stable/040_backup.html#reading-data-from-a-command)

### 6.2 Bash Safety Checklist

From all surveyed production scripts:

| Pattern | Purpose |
|---|---|
| `set -euo pipefail` | Exit on error, undefined vars, pipe failures |
| `exec > >(tee -a "$LOG_FILE") 2>&1` | Capture all output to log |
| Lock file with `noclobber` | Prevent overlapping backup runs |
| `trap 'rm -f "$LOCK_FILE"' EXIT` | Clean up lock even on failure |
| Source env file (not inline secrets) | Keep credentials out of scripts |
| Validate dump before restic | Catch DB failures early |
| Check restic exit code (0/1/3) | Handle warnings without exiting fatally |
| `find ... -delete` old local dumps | Prevent disk filling up |

### 6.3 Stale Lock Recovery

```bash
# Check for stale locks:
restic list locks

# Remove stale lock (confirm no backup is running first):
restic unlock
```

---

## 7. Systemd Timer (Recommended over Cron)

### 7.1 Service Unit

```ini
# /etc/systemd/system/restic-guinevere-backup.service
[Unit]
Description=Guinevere nightly restic backup
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/guinevere-backup.sh
StandardOutput=journal
StandardError=journal
```

### 7.2 Timer Unit

```ini
# /etc/systemd/system/restic-guinevere-backup.timer
[Unit]
Description=Nightly Guinevere backup
Requires=restic-guinevere-backup.service

[Timer]
OnCalendar=daily
RandomizedDelaySec=1h
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable restic-guinevere-backup.timer
sudo systemctl start restic-guinevere-backup.timer
```

**Source**: [HostMyCode — systemd vs cron](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore)

---

## 8. Key GitHub References

| Repository | File | Highlights |
|---|---|---|
| [buildplan/restic-backup-script](https://github.com/buildplan/restic-backup-script) | `restic-backup.sh` | 1500+ lines, pre-flight validation, exit codes 1-20, lock files, notifications, config-driven |
| [stephane-klein/restic-pg_dump-docker](https://github.com/stephane-klein/restic-pg_dump-docker) | `backup.sh` | Retry loop (5x) for forget, restic unlock fallback, retention config via env vars |
| [lobaro/restic-backup-docker](https://github.com/lobaro/restic-backup-docker) | `check.sh` | `--read-data-subset` via env var, separate check script |
| [frkrueger/rpow](https://github.com/frkrueger/rpow) | `ops/backup.sh` | `--keep-daily 7 --keep-weekly 4 --keep-monthly 6` + `--read-data-subset=5%` |
| [arthurgeek/vaultwarden-fly-template](https://github.com/arthurgeek/vaultwarden-fly-template) | `scripts/restic-backup.sh` | Exact requested retention: `--keep-daily 7 --keep-weekly 4 --keep-monthly 3` |
| [nadercas/supafast](https://github.com/nadercas/supafast) | `supabase-backup.sh` | `restic check --read-data-subset=10%`, structured backup functions |
| [vineethkrishnan/backupctl](https://github.com/vineethkrishnan/backupctl) | Full project | Multi-project orchestration, retry with backoff, crash recovery, audit trail |

---

## 9. Summary of Key Decisions for Guinevere

| Decision | Recommendation | Rationale |
|---|---|---|
| Port 5433 | `-p 5433` CLI arg or `PGPORT=5433` env | Non-standard port; pg_dumpall can't use URI connstrings |
| Auth | `.pgpass` at `/etc/restic/pgpass` with `PGPASSFILE` env | pg_dumpall connects multiple times; more secure than PGPASSWORD |
| Dump method | pg_dumpall to temp file → check → restic backup | Most reliable for multi-DB; validation possible before restic |
| Dump format | Plain SQL (pg_dumpall default) | pg_dumpall only outputs plain SQL; for per-DB, use `-Fc` custom |
| Restic stdin | **Avoid** pipe to `--stdin`; use temp file approach or `--stdin-from-command` | Pipe masks pg_dumpall failures → empty backups |
| Retention | `--keep-daily 7 --keep-weekly 4 --keep-monthly 3` | 7 days granular + 4 weeks weekly + 3 months monthly |
| Prune | Always include `--prune` with `forget` | Without prune, storage is never reclaimed |
| Check | `--read-data-subset=5%` daily, full check monthly | Balance between verification speed and thoroughness |
| Multi-source | Single restic backup call: `/etc /opt/guinevere /var/backups/postgres` | Deduplication across all data; tags for selective restore |
| Scheduling | systemd timer (not cron) | Better logging, failure handling, missed-run detection |
| Lock file | `/var/lock/restic-guinevere.lock` with `noclobber` | Prevent overlapping runs from long backups |
| Auth user | Dedicated `backup_user` role with `pg_read_all_data` | Least privilege; no superuser in backup script |

---

## 10. Environment File Template

```bash
# /etc/restic/guinevere.env
# Restic repository
RESTIC_REPOSITORY=s3:s3.eu-central-1.wasabisys.com/guinevere-backups
RESTIC_PASSWORD_FILE=/etc/restic/guinevere-repo-password

# S3 credentials
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key

# Restic options
RESTIC_COMPRESSION=auto
RESTIC_PACK_SIZE=16
```

Chmod: `sudo chmod 0600 /etc/restic/guinevere.env`

---

## 11. Quick Reference: Exact Commands

```bash
# Init repo (one-time):
restic -r s3:s3.amazonaws.com/bucket/guinevere init

# Manual backup run:
sudo /usr/local/sbin/guinevere-backup.sh

# List snapshots:
restic snapshots --tag guinevere

# Restore latest:
restic restore latest --tag guinevere --target /tmp/restore

# Restore specific file from latest:
restic dump latest /etc/guinevere/config.yaml

# Check retention dry-run:
restic forget --tag guinevere --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --dry-run

# Full integrity check:
restic check

# Unlock stale repo:
restic unlock

# View stats:
restic stats --tag guinevere
```