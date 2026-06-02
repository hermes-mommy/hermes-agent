# STEP-P3-002 Backup Checkpoint — Runtime Backup Executed

**Date:** 2026-06-02
**Step:** P3-002 — All 47 tables migration
**Verdict:** PASS WITH MARKER CAVEAT

## 1. Approval Context

Faiz explicitly approved running the P0-027 backup command before P3-002:

```bash
ssh guinevere-vps
cd /home/guinevere/code/guinevere
bash scripts/guinevere-backup.sh
cat /var/log/guinevere/backup-$(date +%Y-%m-%d)*.log | tail -20
restic -r s3:https://is3.cloudhost.id/s3-guinevere snapshots
```

Faiz's approval condition:

> Kalau backup sukses → snapshot ID muncul → approve P3-002 lanjut.

## 2. Pre-Flight Checks

Security consultation returned **GO** with constraints:

- Do not expose secrets.
- Do not run migration unless backup succeeds and snapshot ID is visible.
- Confirm script targets Guinevere, not Aizanta.
- If backup fails/non-zero, stop.

Local audited script was different from the actual VPS script. Actual VPS script inspected before execution:

- Path: `/home/guinevere/code/guinevere/scripts/guinevere-backup.sh`
- Version header: `Guinevere Backup Script (Docker Edition) — v2`
- PostgreSQL dump source: `docker exec guinevere-postgres pg_dumpall -U guinevere`
- Aizanta port 5432 is not targeted.
- Secrets are sourced from SOPS-decrypted env files into process environment; no secret values were printed in evidence.

## 3. Backup Command Run

```bash
ssh guinevere-vps "cd /home/guinevere/code/guinevere; bash scripts/guinevere-backup.sh"
```

## 4. Backup Output Summary

Important non-secret output:

```text
2026-06-02T06:27:32+07:00 === Guinevere Backup Start ===
2026-06-02T06:27:32+07:00 Timestamp: 20260602_062732
2026-06-02T06:27:32+07:00 Phase 1: pg_dumpall via Docker...
2026-06-02T06:27:33+07:00 pg_dumpall: 4318 bytes
snapshot 13159f70 saved
no errors were found
snapshot 13c66a7c saved
2026-06-02T06:27:44+07:00 === Backup Complete ===
2026-06-02T06:27:44+07:00 PG dump: 4318 bytes | Target: PRIMARY + SECONDARY
```

Observed warning:

```text
NOAUTH Authentication required.
```

This came from the Redis `SAVE` step and the script treats it as non-fatal. PostgreSQL dump and both restic backups completed.

## 5. Snapshot Verification

Primary repository direct listing was verified via a temporary remote script (deleted after execution) to avoid PowerShell local expansion and avoid printing secrets.

Command intent:

```bash
/home/guinevere/bin/restic -r s3:https://is3.cloudhost.id/s3-guinevere snapshots
```

Verified primary snapshot:

```text
13159f70  2026-06-02 06:27:33  faiz-prod-01  guinevere,daily,20260602_062732  /home/guinevere/config  31.718 KiB
                                                                              /tmp/tmp.hquCXrm65a
```

Secondary snapshot from backup output:

```text
13c66a7c  2026-06-02 06:27:40  faiz-prod-01  guinevere,daily,20260602_062732  /home/guinevere/config  31.718 KiB
                                                                              /tmp/tmp.hquCXrm65a
```

## 6. Log Tail Verification

Latest fixed log tail from `/var/log/guinevere/backup-20260602_062732.log` included:

```text
no errors were found
snapshot 13c66a7c saved
2026-06-02T06:27:44+07:00 === Backup Complete ===
2026-06-02T06:27:44+07:00 PG dump: 4318 bytes | Target: PRIMARY + SECONDARY
2026-06-02T06:27:47+07:00 Cleanup done
```

## 7. Marker Caveat

`/var/log/guinevere/last-backup-success` is still missing because the actual VPS Docker Edition v2 script does not write that marker, unlike the local audited script.

Verification command result:

```text
LAST_BACKUP_MARKER_MISSING
```

This is a tracker/script-sync caveat, not a blocker for this batch because Faiz's explicit unblock condition was **backup succeeds + snapshot ID appears**, and the primary snapshot ID `13159f70` appeared and was independently listed.

Recommended follow-up outside P3-002: patch the Docker Edition v2 script to write `/var/log/guinevere/last-backup-success` after both restic backups complete.

## 8. Database and Safety Boundary

- Backup targeted Guinevere Docker containers (`guinevere-postgres`, `guinevere-redis`).
- No migration was run during backup checkpoint creation.
- Aizanta PostgreSQL 5432 was not modified.
- No plaintext credentials were written to evidence.
- Temporary restic verification script was removed after execution.

## 9. Decision

P3-002 backup guard is satisfied under Faiz's explicit approval condition:

- Backup command completed.
- Primary snapshot ID visible: `13159f70`.
- Secondary snapshot ID visible: `13c66a7c`.
- Primary restic snapshot listing confirms `13159f70`.

P3-002 may resume.
