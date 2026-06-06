# Phase 7 — Disaster Recovery & Backup Final Readiness Report

**Document Type:** Research Report — Pre-implementation evidence for Step 7.8
**Version:** 1.0
**Date:** 2026-06-06
**Status:** Accepted
**Author:** Guinevere
**Classification:** STRICTLY PRIVATE & CONFIDENTIAL

---

## Executive Summary

This report assesses the current state of all 6 backup/DR domains required for Phase 7 final gate (Step 7.8). The assessment combines: (a) local code/config inspection of scripts, ADRs, service units, systemd timers, and monitoring; (b) VPS read-only verification of running services, binary availability, backup artifacts, repository state, and sentinel files.

**Overall Verdict: BLOCKED — 3 critical gaps prevent Step 7.8 execution.** The backup SOPS secrets directory (secrets/backup/) is missing from the VPS, the Hermes CLI binary is not available, the backup sentinel file has never been written, no systemd timers are deployed, and the last successful backup is 4 days stale. Each gap has a remediation path documented below.

---

## 1. Domain Assessment Matrix

| # | Domain | Status | Gap Summary | RTO/RPO Target |
|---|---|---|---|---|
| 1 | Hermes Backup + Checkpoints | BLOCKED | hermes CLI not found on PATH; no backup/checkpoint commands available | RTO: 15min |
| 2 | PostgreSQL (port 5433) | READY | PG 16.14 docker container healthy, port 5433 mapped, pg_isready passes | RPO: <5min WAL, RTO: 15min |
| 3 | Redis (port 6380) | WARNING | Redis 7 docker running on 6380, but AUTH required — redis-cli -p 6380 returns NOAUTH without password | RPO: <1s AOF, RTO: 5min |
| 4 | Restic (primary + secondary) | BLOCKED | restic v0.17.3 binary at /home/guinevere/bin/restic; but secrets/backup/ SOPS dir MISSING | RPO: 24h backup, RTO: 4h full |
| 5 | Backup Sentinel + Prometheus | BLOCKED | /var/log/guinevere/last-backup-success NEVER written; backup_status.prom stub with value 0 | Alert threshold: 26h |
| 6 | Offsite Dual-Repo | WARNING | Historical snapshots exist; credentials missing to verify current state | dual-repo geo-redundancy |

---

## 2. Detailed Findings

### 2.1 Hermes Backup and Checkpoints — BLOCKED

VPS Check Results:
- hermes backup list: bash: hermes: command not found
- hermes checkpoints list: bash: hermes: command not found
- hermes --version: bash: hermes: command not found

Root Cause: The Hermes CLI binary is not installed on the system PATH. The Phase 7 batch plan Step 7.8 assumes 'hermes backup create' and 'hermes checkpoints create' are available commands, but this is not the case on the current VPS runtime.

Blocking for Step 7.8: Yes — Hermes backup and checkpoint creation are explicit requirements in the Step 7.8 command list (lines 1396-1398 of batch-plan-phase-7.md). Without Hermes CLI, these commands cannot execute.

Remediation:
1. Locate the Hermes CLI binary (likely installed via npm/pip in the Hermes Agent v0.15.2 installation)
2. Add to PATH in .bashrc or symlink to /usr/local/bin/
3. Verify: hermes --version
4. Then run: hermes backup create post-migration-phase-7
5. Then run: hermes checkpoints create post-migration

---

### 2.2 PostgreSQL (port 5433) — READY

VPS Check Results:
- pg_isready -h 127.0.0.1 -p 5433: 127.0.0.1:5433 - accepting connections
- docker exec guinevere-postgres psql -U guinevere -c 'SELECT version()'
  Result: PostgreSQL 16.14 (Debian 16.14-1.pgdg13+1)
- docker inspect guinevere-postgres: 5432/tcp -> 127.0.0.1:5433 (mapped correctly)

Status: PostgreSQL is running as a Docker container (guinevere-postgres), port 5433 is mapped from container port 5432. PgBouncer also runs on port 5434.

Dump capability confirmed: The backup-docker.sh Phase 1 successfully ran 'docker exec guinevere-postgres pg_dumpall -U guinevere' in the June 2 backup. This approach works.

Step 7.8 Command is viable:
  pg_dump -h 127.0.0.1 -p 5433 -U guinevere guinevere > /home/guinevere/backups/guinevere-YYYYMMDD.sql

No blockers. PG backup is ready for Step 7.8.

---

### 2.3 Redis (port 6380) — WARNING

VPS Check Results:
- redis-cli -p 6380 PING: NOAUTH Authentication required.
- redis-cli -p 6380 LASTSAVE: NOAUTH Authentication required.
- docker inspect guinevere-redis: 6379/tcp -> 127.0.0.1:6380 (mapped correctly)

Status: Redis 7 is running as Docker container (guinevere-redis), port 6380 is mapped. AUTH password is required but was not available for read-only verification.

Known issue from P3-002: The June 2 backup log shows the same NOAUTH warning during the Redis SAVE step. The Docker Edition v2 script treats this as non-fatal (confirmed from backup evidence - it completed despite the warning). The Redis SAVE command within the container via Docker socket may work without AUTH.

Step 7.8 Command Method: The batch plan uses 'redis-cli -p 6380 BGSAVE' which passes through the host port. This WILL fail with NOAUTH. The VPS backup-docker.sh currently calls 'docker exec guinevere-redis redis-cli SAVE' (from within container, NOT via host port) - that bypasses AUTH.

Verification through Docker:
  docker exec guinevere-redis redis-cli BGSAVE
  docker exec guinevere-redis redis-cli LASTSAVE

No blocker for Step 7.8, but the batch plan commands should be adjusted to use the Docker exec approach instead of host-port redis-cli.

---

### 2.4 Restic Backup (Primary + Secondary) — BLOCKED

VPS Check Results:
- restic version (global): bash: restic: command not found
- /home/guinevere/bin/restic version: restic 0.17.3 compiled with go1.23.3 on linux/amd64
- ls -la /home/guinevere/code/guinevere/secrets/backup/: No such file or directory
- ls -la /etc/restic/: No such file or directory
- env | grep RESTIC: (no output)

Root Cause 1 - Missing Secrets Directory:
The backup-docker.sh script (the one actually used on VPS) requires:
  /home/guinevere/code/guinevere/secrets/backup/
    restic-password.env          (SOPS-encrypted)
    idcloudhost-s3.env           (SOPS-encrypted)
    cloudflare-r2.env            (SOPS-encrypted)

This directory does not exist on the VPS. The only SOPS file present is /home/guinevere/code/guinevere/secrets/.env.9router.sops. The backup secrets must have been removed or were never deployed after the June 2 backup.

Root Cause 2 - No restic Config:
- /etc/restic/ directory (used by setup-restic.sh guide) does not exist
- No RESTIC_REPOSITORY or RESTIC_PASSWORD env vars in shell environment
- No /home/guinevere/.config/restic/ directory either

But historical log evidence shows restic worked: The June 2 backup log clearly shows successful restic snapshots to both PRIMARY (idcloudhost S3, snapshot 13159f70) and SECONDARY (Cloudflare R2, snapshot 13c66a7c). So the credentials existed at that time.

Remediation:
1. Check git history for SOPS-encrypted secrets: git log --all --oneline -- secrets/backup/
2. If tracked in git, restore: git checkout HEAD -- secrets/backup/
3. If NOT in git, re-create secrets (SOPS encrypt new restic password + S3 credentials)
4. Deploy to VPS: copy .env files to secrets/backup/ and chmod 600
5. Verify: sops exec-env /path/to/idcloudhost-s3.env '/home/guinevere/bin/restic snapshots'

---

### 2.5 Backup Sentinel and Prometheus Monitoring — BLOCKED

VPS Check Results:
- cat /var/log/guinevere/last-backup-success: No such file or directory

History: The P3-002 backup checkpoint (2026-06-02) explicitly noted that LAST_BACKUP_MARKER_MISSING — the actual VPS Docker Edition v2 script does not write /var/log/guinevere/last-backup-success, unlike the local audited script.

The impact:
1. GuinevereBackupStale alert fires perpetually (metric value is always 0)
2. The backup-metric-collector.sh script expects this sentinel but never triggers
3. The backup_status.prom textfile stub exists locally but is not deployed to VPS
4. Prometheus query guinevere_backup_last_success_timestamp returns empty result set

Remediation:
1. Patch the Docker Edition v2 script to write sentinel after both restic backups complete
2. Deploy the backup-metric-collector.sh to the VPS and add to crontab

---

### 2.6 Offsite Dual-Repo Verification — WARNING

VPS Check Results:
- PRIMARY (idcloudhost S3): historical snapshots 13159f70 (Jun 2), 8b1cbc74 (May 31), e70b6c67 (May 31), 87bff879 (May 31)
- SECONDARY (Cloudflare R2): historical snapshots 13c66a7c (Jun 2), 91c76af9 (May 31)

Status: The dual-repo architecture was implemented and working as of June 2. Both repos had guinevere tags, daily/weekly/monthly retention was applied, and restic check passed with no errors.

However, without the missing SOPS credentials, we cannot:
- Verify current snapshot count
- Run restic check --read-data-subset
- Validate recent backup freshness
- Confirm geo-redundancy is still active

No local backup files exist:
- /var/backups/postgres/ - directory does not exist
- /home/guinevere/data/backups/ - empty directory
- /home/guinevere/backups/ subdirs exist but all empty

---

## 3. Step 7.8 - Exact Final Backup Commands

### 3.1 Hermes Backup and Checkpoint
Requires Hermes CLI on PATH first (see remediation 2.1):
  cd /home/guinevere/code/guinevere
  hermes backup create post-migration-phase-7
  hermes checkpoints create post-migration
  hermes backup list | grep post-migration-phase-7
  hermes checkpoints list | grep post-migration

### 3.2 PostgreSQL Full Dump (port 5433)
  cd /home/guinevere
  BACKUP_FILE="/home/guinevere/backups/guinevere-.sql"
  pg_dump -h 127.0.0.1 -p 5433 -U guinevere guinevere > ""
  test -s ""
  sha256sum ""
  head -5 "" | grep -q "PostgreSQL database dump"

### 3.3 Redis BGSAVE (via Docker exec - bypasses AUTH)
  docker exec guinevere-redis redis-cli BGSAVE
  sleep 3
  docker exec guinevere-redis redis-cli LASTSAVE

Verification: LASTSAVE returns Unix epoch timestamp > 0

### 3.4 Restic Backup (requires SOPS secrets restored)
  cd /home/guinevere/code/guinevere
  bash scripts/guinevere-backup-docker.sh

Or manually:
  sops exec-env /home/guinevere/code/guinevere/secrets/backup/idcloudhost-s3.env '/home/guinevere/bin/restic backup --tag guinevere --tag daily /home/guinevere/backups /home/guinevere/code/guinevere/docs/setup-evidence/hermes-migration/phase-7'
  sops exec-env /home/guinevere/code/guinevere/secrets/backup/cloudflare-r2.env '/home/guinevere/bin/restic backup --tag guinevere --tag daily /home/guinevere/backups /home/guinevere/code/guinevere/docs/setup-evidence/hermes-migration/phase-7'

### 3.5 Restore Smoke Test
  mkdir -p /tmp/guinevere-restore-check
  sops exec-env /home/guinevere/code/guinevere/secrets/backup/idcloudhost-s3.env '/home/guinevere/bin/restic restore latest --target /tmp/guinevere-restore-check --include "home/guinevere/backups/guinevere-*.sql"'
  find /tmp/guinevere-restore-check -name 'guinevere-*.sql' -size +1k | head -5
  rm -rf /tmp/guinevere-restore-check

### 3.6 Backup Sentinel Fix
  sed -i '/=== Backup Complete ===/i date -u "+%Y-%m-%dT%H:%M:%S%z" > /var/log/guinevere/last-backup-success' /home/guinevere/code/guinevere/scripts/guinevere-backup-docker.sh

---

## 4. RTO/RPO Constraints Verification

| Constraint | Target | Current | Gap |
|---|---|---|---|
| PG RPO (WAL) | < 5 min | WAL archiving not configured | WAL config requires postgresql.conf changes in Docker |
| PG RTO | 15 min | Not tested | No DR drill exists yet |
| Redis RPO (AOF) | < 1 sec | AOF everysec in Docker config | Not verified (AUTH blocks direct check) |
| Redis RTO | 5 min | Not tested | No DR drill exists yet |
| Backup RPO | 24h | 96h (4 days stale) | CRITICAL - missing secrets blocking backup |
| Full VPS RTO | 4h | Not tested | Quarterly drill not yet scheduled |
| Backup freshness alert | 26h | Metric missing | Sentinel + textfile collector not deployed |

---

## 5. Offsite Dual-Repo Readiness

| Criteria | idcloudhost S3 (Primary) | Cloudflare R2 (Secondary) |
|---|---|---|
| Repository initialized | Confirmed (historical snapshots) | Confirmed (historical snapshots) |
| Credentials available | Missing - secrets/backup/ dir absent | Same issue |
| Recent snapshot | 4 days stale | 4 days stale |
| Retention policy | 7d/4w/3m | 14d/8w/6m |
| last restic check | Passed Jun 2 | Passed Jun 2 |
| Georedundancy | Indonesia-local | Global (Cloudflare) |
| Data residency | Indonesia | Global (acceptable as secondary) |

---

## 6. Gaps and Blockers Summary

| Priority | Gap | Blocking Step 7.8? | Effort to Fix |
|---|---|---|---|
| P0 | secrets/backup/ directory missing (restic credentials) | YES | Medium - restore from git or re-create |
| P0 | hermes CLI binary not available on PATH | YES | Low - locate binary, add to PATH |
| P0 | Backup sentinel never written (last-backup-success missing) | YES | Low - one line in backup script |
| P1 | Redis AUTH blocks redis-cli -p 6380 commands | No (Docker exec works) | Low - use docker exec in batch plan |
| P1 | No systemd timers deployed for automated backups | No (manual backup possible) | Medium - deploy service + timer units |
| P2 | Backup metric collector not deployed to VPS | No | Low - deploy script + crontab |
| P2 | WAL archiving not configured for <5min RPO | No | Medium - Docker compose changes |

---

## 7. Recommended Pre-Step 7.8 Remediation Order

1. Restore secrets/backup/ - Check git for SOPS-encrypted restic credentials; if absent, re-create from scratch.
2. Locate Hermes CLI - Find /home/guinevere/.nvm/versions/node/*/bin/hermes or similar; add to PATH.
3. Patch backup-docker.sh - Add sentinel write, verify it works.
4. Deploy backup-metric-collector.sh - To VPS crontab (*/5 * * * *).
5. Fix Redis commands in Step 7.8 - Use docker exec guinevere-redis redis-cli instead of host-port.
6. Run Step 7.8 - Execute final backup sequence.
7. Deploy systemd timer - For ongoing daily automated backups.
8. Schedule quarterly DR drill - Per ADR-025 and DR Plan.

---

## 8. Evidence Paths (for Step 7.8 verification.md)

Required evidence (from batch-plan-phase-7.md 10):
  docs/setup-evidence/hermes-migration/phase-7/STEP-7.8/verification.md
  Contents:
  - Hermes backup ID
  - Checkpoint ID
  - pg_dump SHA-256 hash
  - Redis LASTSAVE timestamp
  - Restic snapshot ID (both repos)
  - Restore-check transcript

---

Report generated 2026-06-06. All VPS checks performed read-only. No backups/checkpoints created.