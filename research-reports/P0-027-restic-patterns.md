# P0-027: Restic Backup Patterns — Production S3 Setup

**Date:** 2026-05-31
**Author:** Guinevere (research agent)
**Scope:** restic 0.18.1 on Ubuntu Linux VPS, S3-compatible backends, systemd timer orchestration, SOPS+age password management, pg_dump integration

---

## Table of Contents

1. [S3 Repository Initialization & Setup](#1-s3-repository-initialization--setup)
2. [Systemd Service & Timer Configuration](#2-systemd-service--timer-configuration)
3. [Dual-Repository (Primary + Secondary) Patterns](#3-dual-repository-patterns)
4. [SOPS + Age Password Management](#4-sops--age-password-management)
5. [Idcloudhost S3 Endpoint Specifics](#5-idcloudhost-s3-endpoint-specifics)
6. [Cloudflare R2 Endpoint Specifics](#6-cloudflare-r2-endpoint-specifics)
7. [pg_dump Integration](#7-pgdump-integration)
8. [Common S3 Gotchas & Pitfalls](#8-common-s3-gotchas--pitfalls)
9. [Recommended Retention Policies](#9-recommended-retention-policies)
10. [Monitoring & Health Checks](#10-monitoring--health-checks)
11. [Sources & References](#11-sources--references)

---

## 1. S3 Repository Initialization & Setup

### Environment Variables

Restic uses standard AWS environment variables for S3 authentication:

```bash
# Required for S3
export AWS_ACCESS_KEY_ID="<access-key>"
export AWS_SECRET_ACCESS_KEY="<secret-key>"

# Often required
export AWS_DEFAULT_REGION="us-east-1"    # Some providers require specific region

# Restic-specific
export RESTIC_REPOSITORY="s3:https://<endpoint>/<bucket-name>"
export RESTIC_PASSWORD_FILE="/etc/restic/password"
```

**Source:** [restic docs — Preparing a new repo (S3-compatible Storage)](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#s3-compatible-storage)

### URL Format

| Provider | URL Format |
|----------|-----------|
| AWS S3 | `s3:s3.<region>.amazonaws.com/<bucket>` |
| Generic S3-compatible | `s3:https://<endpoint>:<port>/<bucket>` |
| Idcloudhost IS3 | `s3:https://is3.cloudhost.id/<bucket>` |
| Cloudflare R2 | `s3:https://<account-id>.r2.cloudflarestorage.com/<bucket>` |

**Critical:** restic expects **path-style** URLs (`endpoint/bucket`), NOT virtual-hosted style (`bucket.endpoint`). For S3-compatible providers, use the full `https://` prefix.

### Init Command

```bash
# Standard init
restic init

# Init with custom chunker params for cross-repo dedup compatibility
restic init --copy-chunker-params --from-repo <primary-repo>

# Init with repository version 2 (compression, default since 0.14.0)
restic init --repository-version 2
```

**Source:** [restic docs — Preparing a new repo](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)

### Security: Split Credentials into Three Files

Production pattern — separate storage provider credentials, repo URL, and repo password:

```bash
# /etc/restic/env — provider credentials (root:root 600)
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
export AWS_DEFAULT_REGION="..."

# /etc/restic/repo — repository URL (root:root 600)
s3:https://is3.cloudhost.id/my-backup-bucket

# /etc/restic/password — restic password (root:root 600)
<generated-password>
```

**Source:** [Restic Backups on Backblaze B2 with NixOS](https://www.arthurkoziel.com/restic-backups-b2-nixos/) — Split repositoryFile, passwordFile, environmentFile into separate SOPS-encrypted files.

---

## 2. Systemd Service & Timer Configuration

### Service Unit: `/etc/systemd/system/restic-backup@.service`

Template-based service for multiple repos:

```ini
[Unit]
Description=Restic backup on %I
Wants=network-online.target
After=network-online.target

[Service]
Type=oneshot
EnvironmentFile=/etc/restic/%I.env
ExecStart=/usr/bin/restic backup \
  --files-from /etc/restic/%I.files \
  --exclude-file /etc/restic/%I.excludes \
  --tag %I \
  --verbose
ExecStartPost=/usr/bin/restic forget \
  --tag %I \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --prune
ExecStartPost=/usr/bin/restic check --read-data-subset=5%
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutSec=7200
Restart=no
```

**Source:** [Timur Demin — Restic with systemd](https://tdem.in/post/restic-with-systemd/) — Template-based `@` unit pattern for unlimited repos.

### Timer Unit: `/etc/systemd/system/restic-backup@.timer`

```ini
[Unit]
Description=Daily restic backup for %I

[Timer]
OnCalendar=*-*-* 02:30:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

### Enabling & Management

```bash
# Enable timer for a specific repo (e.g., "primary")
systemctl daemon-reload
systemctl enable --now restic-backup@primary.timer

# Manual run
systemctl start restic-backup@primary.service

# Check status
systemctl list-timers --all | grep restic
journalctl -eu restic-backup@primary.service

# Validate calendar expression
systemd-analyze calendar "*-*-* 02:30:00"
```

### Key systemd Parameters Explained

| Parameter | Value | Purpose |
|-----------|-------|---------|
| `Type=oneshot` | — | Run once and exit (not a daemon) |
| `Persistent=true` | — | Fire missed run on next boot if machine was off |
| `RandomizedDelaySec` | 15-30m | Prevent thundering herd when multiple servers use the same target |
| `Nice=19` | — | Lowest CPU priority (don't compete with applications) |
| `IOSchedulingClass=best-effort` | 7 | Low I/O priority (don't starve disk for other processes) |
| `TimeoutSec` | 3600-7200 | Allow long initial backups |
| `Wants=network-online.target` | — | Ensure network is actually up before starting |
| `After=network-online.target` | — | Order after network readiness |

**Source:** [DEV — Production-Ready Linux Backup Pipeline](https://dev.to/lyraalishaikh/a-production-ready-linux-backup-pipeline-with-restic-systemd-timers-5hmo), [ServerCrate — Automate Restic with systemd Timers](https://servercrate.net/restic-systemd-timer/)

### Hardened Service Unit (ArchWiki pattern)

For additional security sandboxing:

```ini
[Service]
Type=oneshot
EnvironmentFile=/etc/restic/%I.env
ExecStart=/usr/local/bin/restic-backup
ExecStop=bash -c 'if [[ -n "$MAINPID" ]]; then tail --pid="$MAINPID" -f /dev/null; fi'
Nice=19
IOSchedulingClass=best-effort
IOSchedulingPriority=7
TimeoutSec=7200
Restart=no

# Security hardening
ProtectSystem=strict
ProtectHome=yes
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectControlGroups=yes
RestrictNamespaces=yes
RestrictRealtime=yes
RestrictSUIDSGID=yes
SystemCallFilter=@system-service
UMask=0077
```

**Source:** [ArchWiki — Restic](https://wiki.archlinux.org/title/Restic)

---

## 3. Dual-Repository Patterns

### Recommended: `restic copy` approach

Backup to **primary** repo (idcloudhost S3), then **copy** snapshots to secondary repo (Cloudflare R2). Deduplication works across repos if chunker params match.

#### Step 1: Initialize secondary repo with same chunker params

```bash
restic -r <SECONDARY_REPO> init \
  --copy-chunker-params \
  --from-repo <PRIMARY_REPO>
```

#### Step 2: Copy snapshots periodically

```bash
# Copy all snapshots from primary to secondary
restic -r <SECONDARY_REPO> copy \
  --from-repo <PRIMARY_REPO>

# Copy only tagged snapshots
restic -r <SECONDARY_REPO> copy \
  --from-repo <PRIMARY_REPO> \
  --tag nightly
```

#### Step 3: Systemd timer for weekly copy

```ini
# /etc/systemd/system/restic-copy@secondary.timer
[Unit]
Description=Weekly restic copy to secondary

[Timer]
OnCalendar=Sun 03:00:00
Persistent=true
RandomizedDelaySec=15m

[Install]
WantedBy=timers.target
```

**Critical caveats:**
- `restic copy` **downloads then re-uploads** all data → bandwidth-heavy. Source/dest repos use different encryption keys.
- `--copy-chunker-params` at init time ensures deduplication between repos; without it, data occupies **up to 2× space** in destination.
- Copying process is **not yet optimized for performance** — processes one blob at a time.

**Source:** [restic docs — Working with repos (copy)](https://restic.readthedocs.io/en/v0.16.4/045_working_with_repos.html), [restic-copy man page](https://man.archlinux.org/man/restic-copy.1.en), [The Linux Club — Enterprise DR Guide](https://thelinuxclub.com/restic-encrypted-backups-to-backblaze-b2-enterprise-disaster-recovery-guide-2026/)

### Alternative: Dual-backup in script (simpler, double bandwidth)

Backup to both repos in sequence within the same script:

```bash
#!/bin/bash
set -euo pipefail

# Backup to PRIMARY
source /etc/restic/primary.env
restic backup /etc /var/lib --tag primary
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune

# Backup to SECONDARY
source /etc/restic/secondary.env
restic backup /etc /var/lib --tag secondary
restic forget --keep-daily 14 --keep-weekly 8 --keep-monthly 6 --prune
```

**Downside:** Uploads data twice on every run. No cross-repo dedup.

### Alternative: rclone sync (file-level copy of repo)

```bash
# After backup to primary, sync repo to secondary at file level
rclone sync /srv/restic-repo remote:backup-bucket/path
```

**Pros:** Fast (only differential file sync), works across any rclone-supported provider.
**Cons:** Repositories diverge if `prune` runs on only one copy; restic's internal structure must be consistent.

**Source:** [GitHub Issue #4432 — Backup to multiple repos](https://github.com/restic/restic/issues/4432)

---

## 4. SOPS + Age Password Management

### Pattern 1: SOPS-encrypted env file + RESTIC_PASSWORD_FILE

Encrypt the entire restic env config with SOPS:

```yaml
# .sops.yaml
creation_rules:
  - age: age1ql3z7hjy54pw3hyww5ayyfg7zqgvc7w3j2elw8zmrj2kg5sfn9aqmcac8p
```

```bash
# secrets/restic-primary.env (plaintext version)
RESTIC_REPOSITORY=s3:https://is3.cloudhost.id/my-bucket
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
RESTIC_PASSWORD=xxx
```

Encrypt:

```bash
sops --encrypt secrets/restic-primary.env > secrets/restic-primary.env.sops
```

In backup script, decrypt to temp file at runtime:

```bash
#!/bin/bash
set -euo pipefail

# Decrypt secrets to a temp file (auto-cleaned on exit)
SECRETS=$(mktemp)
trap 'rm -f "$SECRETS"' EXIT

sops --decrypt /etc/restic/primary.sops.env > "$SECRETS"
source "$SECRETS"

restic backup /etc /var/lib
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
```

**Source:** [vivo — restic orchestrator with SOPS-encrypted secrets](https://crates.io/crates/vivo), [SOPS docs — age encryption](https://getsops.io/docs/)

### Pattern 2: RESTIC_PASSWORD_COMMAND with sops

```bash
# /etc/restic/primary.env
RESTIC_REPOSITORY=s3:https://is3.cloudhost.id/my-bucket
AWS_ACCESS_KEY_ID=xxx
AWS_SECRET_ACCESS_KEY=xxx
RESTIC_PASSWORD_COMMAND="sops --decrypt /etc/restic/password.sops.env"
```

This way, the restic password never appears in plaintext in environment variables.

**Important:** Avoid pipes in `RESTIC_PASSWORD_COMMAND` — restic does NOT pass the command through a shell. Use a helper script or `bash -c` for complex commands:

```bash
# WRONG — pipes don't work:
RESTIC_PASSWORD_COMMAND="pass show restic | head -1"

# CORRECT — use explicit shell:
RESTIC_PASSWORD_COMMAND="bash -c 'pass show restic | head -1'"

# CORRECT — use helper script:
RESTIC_PASSWORD_COMMAND="/usr/local/bin/restic-get-password.sh"
```

**Source:** [GitHub Issue #5149 — Piped commands in RESTIC_PASSWORD_COMMAND](https://github.com/restic/restic/issues/5149)

### Pattern 3: SOPS-encrypted individual secrets (NixOS/sops-nix style)

Keep each secret in its own encrypted file:

```bash
/etc/restic/
├── repo.sops        # RESTIC_REPOSITORY value
├── password.sops    # RESTIC_PASSWORD value
├── aws-key.sops     # AWS_ACCESS_KEY_ID value
├── aws-secret.sops  # AWS_SECRET_ACCESS_KEY value
└── region.sops      # AWS_DEFAULT_REGION value
```

Then in the systemd service:

```ini
[Service]
EnvironmentFile=-/etc/restic/primary.env
ExecStartPre=/usr/local/bin/decrypt-restic-secrets.sh
```

**Source:** [NixOS Wiki — Restic + sops-nix](https://wiki.nixos.org/wiki/Restic)

### Pattern 4: RESTIC_PASSWORD_COMMAND with age directly (restic-age-key)

```bash
# Install: go install github.com/josh/restic-age-key@latest

export RESTIC_REPOSITORY=/path/to/repo
export RESTIC_PASSWORD_COMMAND='restic-age-key password --identity /etc/restic/key.txt'
export RESTIC_AGE_IDENTITY_FILE=/etc/restic/key.txt

restic backup /data
```

**Pros:** No plaintext password file at all. Uses asymmetric age keys.
**Cons:** Requires restic-age-key binary; one more dependency.

**Source:** [josh/restic-age-key](https://github.com/josh/restic-age-key)

---

## 5. Idcloudhost S3 Endpoint Specifics

### Endpoint Information

| Parameter | Value |
|-----------|-------|
| Endpoint | `is3.cloudhost.id` |
| URL format (path-style) | `s3:https://is3.cloudhost.id/<bucket-name>` |
| URL format (virtual-hosted) | `<bucket>.is3.cloudhost.id` |
| Region | Not specified (leave default `us-east-1` or omit) |
| Bucket lookup | Likely `path` style (verify with `-o s3.bucket-lookup=path`) |

### Known Issues (from user reports)

- **Documentation is sparse** — IDCloudHost's S3-compatible API is not fully documented. Some AWS S3 API features may not work.
- **Dashboard doesn't show endpoint URLs** — You need to infer them. Right-click a file in Cyberduck to get the URL pattern.
- **API stability uncertain** — Older reports (2021-2023) suggest migrating away due to incomplete S3 API support. **Verify with current version.**

### Recommended Configuration

```bash
export AWS_ACCESS_KEY_ID="<from-idcloudhost-console>"
export AWS_SECRET_ACCESS_KEY="<from-idcloudhost-console>"
export RESTIC_REPOSITORY="s3:https://is3.cloudhost.id/<bucket-name>"

# If bucket listing fails, try:
# -o s3.bucket-lookup=path

# Initialize
restic init
```

**Sources:**
- [S3cmd Config for IDCloudHost](https://sirius.miraheze.org/wiki/S3cmd:_Config_S3_IDCloudHost) — `is3.cloudhost.id` endpoint
- [IDCloudHost Cyberduck Guide](https://idcloudhost.com/panduan/cara-akses-object-storage-idcloudhost-menggunakan-cyberduck/) — Server: `is3.cloudhost.id`
- [Laravel Storage with IDCloudHost](https://bintangmfhd.medium.com/setting-up-laravel-storage-with-idcloudhost-object-storage-300bedd369a1) — `AWS_ENDPOINT=https://is3.cloudhost.id`

---

## 6. Cloudflare R2 Endpoint Specifics

### Endpoint Information

| Parameter | Value |
|-----------|-------|
| Endpoint | `https://<account-id>.r2.cloudflarestorage.com` |
| URL format | `s3:https://<account-id>.r2.cloudflarestorage.com/<bucket>` |
| Region | Must be `auto` |
| Special | No egress fees; S3-compatible |

### Required Configuration

```bash
export AWS_ACCESS_KEY_ID="<r2-access-key>"
export AWS_SECRET_ACCESS_KEY="<r2-secret-key>"
export RESTIC_REPOSITORY="s3:https://<account-id>.r2.cloudflarestorage.com/<bucket>"

# R2 requires region=auto
export AWS_DEFAULT_REGION="auto"
# OR
# -o s3.region="auto"

# R2 uses path-style by default; verify with:
# -o s3.bucket-lookup=auto

restic init
```

**Notes:**
- Generate R2 API tokens in Cloudflare Dashboard → R2 → Manage R2 API Tokens
- Account ID is found in Cloudflare Dashboard → R2 → Account ID
- R2 has **no egress fees**, making it ideal for secondary/cold backup
- R2 supports object locking for immutability

---

## 7. pg_dump Integration

### Pattern 1: Pipe directly to restic stdin (no temp file)

```bash
pg_dump -h localhost -U backup_user -d appdb \
  --format=custom \
  | restic backup --stdin \
    --stdin-filename "postgres/appdb-$(date +%Y%m%d).dump" \
    --tag postgres \
    --tag appdb
```

**Pros:** No temp file on disk, encrypted immediately.
**Cons:** Cannot validate dump before backup; one file per dump.

**Source:** [StackHarden — PostgreSQL Backups](https://stackharden.com/guides/postgres-backups/), [OSSAlt — Automated Server Backups](https://ossalt.com/guides/automated-server-backups-restic-rclone-2026)

### Pattern 2: Dump to file, validate, then backup

```bash
#!/bin/bash
set -euo pipefail

DUMP_DIR="/var/backups/postgres"
DUMP_FILE="${DUMP_DIR}/appdb-$(date +%Y%m%d-%H%M%S).dump"
mkdir -p "${DUMP_DIR}"

# 1) Create custom-format dump
pg_dump -h 127.0.0.1 -U backup_dumper -d appdb \
  --format=custom \
  --file="${DUMP_FILE}"

# 2) Validate dump archive
pg_restore -l "${DUMP_FILE}" > /dev/null 2>&1 || {
  echo "ERROR: dump validation failed"
  rm -f "${DUMP_FILE}"
  exit 1
}

# 3) Back up with restic
restic backup "${DUMP_FILE}" \
  --tag postgres \
  --tag appdb

# 4) Remove local dump after successful backup
rm -f "${DUMP_FILE}"
```

**Pros:** Validation step catches corrupt dumps; supports multiple dump files.
**Cons:** Temp file on disk (mitigated by immediate cleanup after backup).

**Source:** [Raff — PostgreSQL Restic Backup](https://rafftechnologies.com/learn/tutorials/back-up-postgresql-raff-object-storage-restic)

### Pattern 3: pg_dumpall for cluster-wide backup

```bash
# All databases, plain SQL format (portable)
pg_dumpall -U postgres \
  | gzip \
  | restic backup --stdin \
    --stdin-filename "postgres/alldbs-$(date +%Y%m%d).sql.gz" \
    --tag postgres \
    --tag alldbs
```

**Source:** [The Linux Club — Enterprise DR Guide](https://thelinuxclub.com/restic-encrypted-backups-to-backblaze-b2-enterprise-disaster-recovery-guide-2026/)

### Pattern 4: Per-container database dump (Docker)

```bash
for container in $(docker ps --filter "ancestor=postgres" --format "{{.Names}}"); do
  DB_NAME=$(docker exec "$container" env | grep POSTGRES_DB | cut -d= -f2)
  DB_USER=$(docker exec "$container" env | grep POSTGRES_USER | cut -d= -f2)
  
  docker exec "$container" pg_dump -U "$DB_USER" "$DB_NAME" \
    | restic backup --stdin \
      --stdin-filename "${container}-${DB_NAME}-$(date +%Y%m%d).sql" \
      --tag postgres \
      --tag docker \
      --tag "$container"
done
```

### PostgreSQL User Setup for Backups

```sql
CREATE ROLE backup_dumper WITH LOGIN PASSWORD 'strong-password';
GRANT CONNECT ON DATABASE appdb TO backup_dumper;
GRANT USAGE ON SCHEMA public TO backup_dumper;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO backup_dumper;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO backup_dumper;
```

Use `~/.pgpass` for auth without env vars:

```
# host:port:database:username:password
127.0.0.1:5432:appdb:backup_dumper:strong-password
```

Permissions: `chmod 600 ~/.pgpass`

---

## 8. Common S3 Gotchas & Pitfalls

### 8.1 Request Timeout on Large Repositories

**Symptom:**
```
List(data) returned error, retrying after 1s: [...]: request timeout
```

**Fix:** Increase stuck request timeout:
```bash
restic backup /data --stuck-request-timeout 10m
```

**Root cause:** Restic's default 5-minute timeout is too short for listing large repos on slow S3 providers.

**Source:** [restic FAQ — request timeout errors](https://restic.readthedocs.io/en/stable/faq.html#what-can-i-do-in-case-of-request-timeout-errors)

### 8.2 S3 503 / Rate Limiting

**Symptom:**
```
Save(<data/...>) returned error, retrying: The server is temporarily unavailable. Please try again later.
```

**Root cause:** Some S3 providers (especially budget ones) use HTTP 503 to throttle clients. Restic's exponential backoff eventually gives up.

**Mitigations:**
- Reduce concurrent connections: `-o s3.connections=3`
- Add retry wrapper in backup script (see example below)
- Use `--limit-upload` to cap bandwidth

**Source:** [GitHub Issue #4018 — restic gives up too fast on rate-limited S3](https://github.com/restic/restic/issues/4018)

### 8.3 Repository Lock Contention

**Symptom:**
```
unable to create lock in backend: repository is already locked
```

**Fix:**
```bash
# Check locks
restic list locks

# Remove stale locks
restic unlock

# Use retry-lock (restic 0.16+)
restic backup /data --retry-lock 2h
```

**Root cause:** Previous backup was killed/crashed leaving stale lock, or two backup jobs running concurrently.

**Best practice:** Use `--retry-lock 2h` in scheduled backups so overlapping runs wait instead of failing.

**Source:** [selfhosting.sh — Restic Repository Locked](https://selfhosting.sh/troubleshooting/restic-repository-locked/)

### 8.4 AWS IAM Performance Problem (Anonymous S3)

**Symptom:** Extremely slow operations on anonymous (public) S3 buckets.

**Root cause:** `minio-go` client evaluates all credential providers (including IAM) on every request, causing delays.

**Fix:** `-o s3.unsafe-anonymous-auth=true` (restic 0.17+)

**Source:** [GitHub Issue #4707 — Performance problems with anonymous S3](https://github.com/restic/restic/issues/4707)

### 8.5 "Access Denied" Causes Hangs

**Symptom:** `Save() failed: client.PutObject: Access Denied` — restic hangs instead of failing fast.

**Status:** Known issue (GitHub #5683). Temporary credentials expire during long backups.

**Mitigation:** Use long-lived credentials for backup users; monitor and rotate separately.

**Source:** [GitHub Issue #5683 — restic hangs on Access Denied](https://github.com/restic/restic/issues/5683)

### 8.6 Context Canceled During Prune

**Symptom:**
```
List(data) returned error, retrying after 1s: ... context canceled
```

**Mitigation:** `--stuck-request-timeout 30m` for large repos; split `forget` (daily) from `prune` (weekly).

**Source:** [GitHub Issue #4970 — Context canceled due to timeouts](https://github.com/restic/restic/issues/4970)

### 8.7 Prune Cannot Run Concurrently with Backup

`restic prune` acquires an exclusive lock. If `forget --prune` runs as `ExecStartPost`, it blocks the next scheduled backup.

**Mitigation for repos >100GB:**
- Daily: `forget` only (metadata-only, fast, no exclusive lock for long)
- Weekly: `forget --prune` (heavy, off-peak)

```bash
# Daily backup service: forget only
ExecStartPost=/usr/bin/restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12

# Weekly prune service (separate timer, Sunday 4am)
ExecStart=/usr/bin/restic prune
```

**Source:** [StackHarden — Encrypted Backups with restic](https://stackharden.com/guides/encrypted-backups-restic/)

### 8.8 First Backup Takes Forever

Expected behavior for initial backup. Subsequent runs are incremental.

```bash
# Cap upload bandwidth during business hours
restic backup /data --limit-upload 5000   # 5000 KB/s

# Increase parallel connections for faster initial backup
restic backup /data --pack-size 64 --read-concurrency 8
```

### 8.9 Wrong Password / Wrong Key

```
Fatal: wrong password or no key found
```

**Troubleshoot:**
1. `sudo systemctl cat restic-backup.service` — verify `EnvironmentFile=` path
2. Check file permissions (must be `600` or `400`)
3. Verify `restic snapshots` works manually

### 8.10 S3 Cold Storage Restore Issues

If using S3 Glacier/Deep Archive storage classes:

```bash
# Experimental feature flag required
RESTIC_FEATURES=s3-restore restic restore \
  -o s3.enable-restore=1 \
  -o s3.restore-days=7 \
  -o s3.restore-timeout=24h \
  latest --target /restore
```

**Caveat:** Still alpha; restores can take 1-42 hours depending on storage class.

**Source:** [restic FAQ — cold storages](https://restic.readthedocs.io/en/stable/faq.html#are-cold-storages-supported)

---

## 9. Recommended Retention Policies

### Standard Production

| Policy | Keep | Description |
|--------|------|-------------|
| Daily | 7 | Last 7 days of snapshots |
| Weekly | 4 | Last 4 weeks (~1 month) |
| Monthly | 12 | Last 12 months (~1 year) |

```bash
restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 12 --prune
```

### Extended Retention (Compliance)

| Policy | Keep | Description |
|--------|------|-------------|
| Hourly | 24 | Last 24 hours (for rapid recovery) |
| Daily | 30 | Last 30 days |
| Weekly | 8 | Last 8 weeks (~2 months) |
| Monthly | 12 | Last 12 months |
| Yearly | 7 | Last 7 years (compliance) |

```bash
restic forget \
  --keep-hourly 24 \
  --keep-daily 30 \
  --keep-weekly 8 \
  --keep-monthly 12 \
  --keep-yearly 7 \
  --prune
```

### Prune Scheduling by Repo Size

| Repo Size | Prune Frequency |
|-----------|----------------|
| < 100 GB | Daily (in backup script) |
| 100-500 GB | Weekly (separate timer) |
| > 500 GB | Monthly (separate timer, off-peak) |

**Source:** [StackHarden — restic prune and contention](https://stackharden.com/guides/encrypted-backups-restic/)

---

## 10. Monitoring & Health Checks

### Success Sentinel

```bash
# After successful backup
date +%s > /var/log/restic/last-success
```

Alert if `time() - last_success > 86400` (no backup in 24h).

### Restore Drill (Monthly)

```bash
#!/bin/bash
set -euo pipefail

# Restore latest snapshot to temp dir
restic restore latest --target /tmp/restore-drill --include /etc/nginx

# Verify against live
diff -r /etc/nginx /tmp/restore-drill/etc/nginx

# Cleanup
rm -rf /tmp/restore-drill
echo "Restore drill PASSED at $(date)"
```

### Repository Check

```bash
# Daily: metadata-only check (fast)
restic check

# Weekly: random 5% data verification
restic check --read-data-subset=5%

# Monthly: full data verification (can be expensive)
restic check --read-data
```

### Prometheus/Healthchecks Integration

```bash
#!/bin/bash
set -euo pipefail

HEALTHCHECKS_URL="https://hc.example.com/ping/restic-backup"

# Notify start
curl -fsS -m 10 --retry 5 "${HEALTHCHECKS_URL}/start"

# Run backup
/usr/local/sbin/restic-backup.sh || {
  curl -fsS -m 10 --retry 5 "${HEALTHCHECKS_URL}/fail"
  exit 1
}

# Notify success
curl -fsS -m 10 --retry 5 "${HEALTHCHECKS_URL}"
```

---

## 11. Sources & References

### Official Documentation
- [restic docs (stable)](https://restic.readthedocs.io/en/stable/) — Primary reference for all commands
- [restic docs — Preparing a new repo (S3)](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html#s3-compatible-storage)
- [restic docs — FAQ (timeouts, lock, passwords)](https://restic.readthedocs.io/en/stable/faq.html)
- [restic docs — Working with repos (copy)](https://restic.readthedocs.io/en/v0.16.4/045_working_with_repos.html)
- [restic-copy man page](https://man.archlinux.org/man/restic-copy.1.en)
- [restic GitHub](https://github.com/restic/restic)

### Systemd Configuration
- [DEV — Production-Ready Linux Backup Pipeline](https://dev.to/lyraalishaikh/a-production-ready-linux-backup-pipeline-with-restic-systemd-timers-5hmo) (2026-02)
- [ArchWiki — Restic (systemd timers)](https://wiki.archlinux.org/title/Restic)
- [ServerCrate — Automate Restic with systemd Timers](https://servercrate.net/restic-systemd-timer/) (2026-05)
- [Timur Demin — Restic with systemd](https://tdem.in/post/restic-with-systemd/)
- [Feldspaten — Automatic backups with restic and systemd](https://feldspaten.org/2025/03/24/Automatic-backups-with-restic-and-systemd-services/)
- [Fedora Magazine — Automate backups with restic and systemd](https://fedoramagazine.org/automate-backups-with-restic-and-systemd/)
- [larsks/restic-systemd-units](https://github.com/larsks/restic-systemd-units) (template-based patterns)

### Dual-Repo / Copy Patterns
- [The Linux Club — Enterprise DR Guide (3-2-1 with restic copy)](https://thelinuxclub.com/restic-encrypted-backups-to-backblaze-b2-enterprise-disaster-recovery-guide-2026/) (2026-03)
- [GitHub Issue #4432 — Backup to multiple repositories](https://github.com/restic/restic/issues/4432)
- [OSSAlt — Automated Server Backups with Restic and Rclone 2026](https://ossalt.com/guides/automated-server-backups-restic-rclone-2026) (2026-03)

### SOPS + Password Management
- [SOPS official docs](https://getsops.io/docs/)
- [vivo — restic orchestrator with SOPS-encrypted secrets](https://crates.io/crates/vivo)
- [josh/restic-age-key](https://github.com/josh/restic-age-key)
- [NixOS Wiki — Restic + sops-nix](https://wiki.nixos.org/wiki/Restic)
- [Arthur Koziel — Restic Backups on B2 with NixOS + agenix](https://www.arthurkoziel.com/restic-backups-b2-nixos/)
- [GitHub Issue #5149 — Piped commands in RESTIC_PASSWORD_COMMAND](https://github.com/restic/restic/issues/5149)

### pg_dump Integration
- [StackHarden — PostgreSQL Backups (logical + restic)](https://stackharden.com/guides/postgres-backups/) (2026-05)
- [Raff — PostgreSQL Restic Backup to Object Storage](https://rafftechnologies.com/learn/tutorials/back-up-postgresql-raff-object-storage-restic) (2026-05)
- [HostMyCode — VPS Backup Strategy 2026](https://www.hostmycode.com/blog/vps-backup-strategy-2026-restic-s3-verification-retention-fast-restore) (2026-04)
- [fgeck/gorestic-homelab — Go-based restic orchestrator with pg_dump](https://github.com/fgeck/gorestic-homelab)
- [stephane-klein/restic-pg_dump-docker — Docker pattern](https://github.com/stephane-klein/restic-pg_dump-docker)

### S3 Gotchas & Issues
- [GitHub Issue #4018 — Rate-limited S3 (HTTP 503)](https://github.com/restic/restic/issues/4018)
- [GitHub Issue #4193 — Timeouts for backend connections](https://github.com/restic/restic/issues/4193)
- [GitHub Issue #4970 — Context canceled during prune](https://github.com/restic/restic/issues/4970)
- [GitHub Issue #4707 — Anonymous S3 performance](https://github.com/restic/restic/issues/4707)
- [GitHub Issue #5683 — Access Denied hang](https://github.com/restic/restic/issues/5683)
- [GitHub PR #5660 — Cold storage restore fix](https://github.com/restic/restic/pull/5660)
- [StackHarden — Encrypted Backups with restic (gotchas)](https://stackharden.com/guides/encrypted-backups-restic/) (2026-05)
- [RDP.sh — Encrypted VPS Backups to S3 with Restic](https://rdp.sh/en/blog/encrypted-vps-backups-to-s3-with-restic) (2026-02)

### IDCloudHost S3
- [IDCloudHost Cyberduck Guide](https://idcloudhost.com/panduan/cara-akses-object-storage-idcloudhost-menggunakan-cyberduck/)
- [S3cmd Config for IDCloudHost](https://sirius.miraheze.org/wiki/S3cmd:_Config_S3_IDCloudHost)
- [IDCloudHost API Docs](https://api.idcloudhost.com/)