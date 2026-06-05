#!/bin/bash
# Guinevere Backup Script (Docker Edition)
set -euo pipefail

LOG_DIR=/var/log/guinevere
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG=$LOG_DIR/backup-$TIMESTAMP.log
TMPDIR=$(mktemp -d)
DRY_RUN=${DRY_RUN:-0}

# Source secrets (auto-export via set -a)
export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
SECRET_DIR=/home/guinevere/code/guinevere/secrets/backup

set -a
source <(sops --decrypt $SECRET_DIR/restic-password.env)
source <(sops --decrypt $SECRET_DIR/idcloudhost-s3.env)
AWS_PRIMARY=$RESTIC_REPOSITORY
source <(sops --decrypt $SECRET_DIR/cloudflare-r2.env)
AWS_SECONDARY=$RESTIC_REPOSITORY
set +a

RESTIC=$HOME/bin/restic
export RESTIC_PASSWORD
export AWS_ACCESS_KEY_ID
export AWS_SECRET_ACCESS_KEY
export RESTIC_REPOSITORY

log() { echo "$(date -Iseconds) $1" | tee -a $LOG; }

cleanup() {
    rm -rf $TMPDIR
    log "Cleanup done"
}
trap cleanup EXIT

log "=== Guinevere Backup Start ==="
log "Timestamp: $TIMESTAMP"
log "DRY_RUN: $DRY_RUN"

# Phase 1: PostgreSQL dump via Docker
log "Phase 1: pg_dumpall via Docker..."
DUMP_FILE=$TMPDIR/pg_dumpall-$TIMESTAMP.sql.gz
docker exec guinevere-postgres pg_dumpall -U guinevere 2>/dev/null | gzip > $DUMP_FILE
DUMP_SIZE=$(stat -c%s $DUMP_FILE 2>/dev/null || echo 0)
log "pg_dumpall: $DUMP_SIZE bytes"

if [ $DUMP_SIZE -lt 100 ]; then
    log "ERROR: pg_dumpall too small ($DUMP_SIZE bytes) — aborting"
    exit 1
fi

# Phase 2: Backup to PRIMARY (idcloudhost S3)
log "Phase 2: restic backup to PRIMARY (idcloudhost S3)..."
RESTIC_REPOSITORY=$AWS_PRIMARY $RESTIC backup \
    --tag guinevere --tag daily --tag $TIMESTAMP \
    $TMPDIR /home/guinevere/data /home/guinevere/config \
    --exclude '*.pid' --exclude '*.sock' --exclude '*.lock' 2>&1 | tee -a $LOG

# Phase 3: Forget + Prune PRIMARY
log "Phase 3: forget --prune PRIMARY..."
RESTIC_REPOSITORY=$AWS_PRIMARY $RESTIC forget \
    --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --prune 2>&1 | tee -a $LOG

# Phase 4: Health check PRIMARY
log "Phase 4: restic check PRIMARY..."
RESTIC_REPOSITORY=$AWS_PRIMARY $RESTIC check \
    --read-data-subset=5% 2>&1 | tee -a $LOG

# Phase 5: Backup to SECONDARY (Cloudflare R2)
log "Phase 5: restic backup to SECONDARY (Cloudflare R2)..."
RESTIC_REPOSITORY=$AWS_SECONDARY AWS_DEFAULT_REGION=auto $RESTIC backup \
    --tag guinevere --tag daily --tag $TIMESTAMP \
    $TMPDIR /home/guinevere/data /home/guinevere/config \
    --exclude '*.pid' --exclude '*.sock' --exclude '*.lock' 2>&1 | tee -a $LOG

# Phase 6: Forget + Prune SECONDARY
log "Phase 6: forget --prune SECONDARY..."
RESTIC_REPOSITORY=$AWS_SECONDARY AWS_DEFAULT_REGION=auto $RESTIC forget \
    --keep-daily 14 --keep-weekly 8 --keep-monthly 6 --prune 2>&1 | tee -a $LOG

log "=== Backup Complete ==="
log "PG dump: $DUMP_SIZE bytes | Target: PRIMARY + SECONDARY"

echo ""
echo "=== SNAPSHOTS (PRIMARY) ==="
RESTIC_REPOSITORY=$AWS_PRIMARY $RESTIC snapshots --latest 3 2>&1
echo ""
echo "=== SNAPSHOTS (SECONDARY) ==="
RESTIC_REPOSITORY=$AWS_SECONDARY AWS_DEFAULT_REGION=auto $RESTIC snapshots --latest 3 2>&1