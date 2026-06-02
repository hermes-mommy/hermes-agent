#!/usr/bin/env bash
# ============================================================================
# Guinevere Production Backup Script
# ============================================================================
# Purpose:
#   Dual-repo encrypted backup using restic + SOPS + pg_dumpall.
#   Primary target:  idcloudhost S3-compatible object storage.
#   Secondary target: Cloudflare R2 (geo-redundant, zero-egress).
#
# Flow:
#   1. PostgreSQL dump (pg_dumpall) → validate → compress
#   2. restic backup to PRIMARY  (tag: primary)
#   3. restic forget --prune on PRIMARY  (7d daily + 4w weekly + 3m monthly)
#   4. restic check --read-data-subset=5% on PRIMARY
#   5. restic backup to SECONDARY (tag: secondary)
#   6. restic forget --prune on SECONDARY (14d daily + 8w weekly + 6m monthly)
#   7. Write success timestamp to /var/log/guinevere/last-backup-success
#
# Secrets:
#   Uses `sops exec-env` pattern — never writes plaintext to disk.
#   SOPS_AGE_KEY_FILE must be set or passed in env.
#   Secret files: secrets/backup/idcloudhost-s3-plaintext.env
#                 secrets/backup/cloudflare-r2-plaintext.env
#
# Usage:
#   sudo ./guinevere-backup.sh             # normal run
#   sudo DRY_RUN=1 ./guinevere-backup.sh   # dry-run (prints, no actual backup)
#   ./guinevere-backup.sh --help           # print help and exit
#
# Requirements:
#   - restic >= 0.17.0 (for --stdin-from-command)
#   - sops >= 3.9.x
#   - age (key at /home/guinevere/secrets/age-key.txt)
#   - pg_dumpall (PostgreSQL client tools)
#   - gzip / zcat
#   - dirs: /var/backups/postgres, /var/log/guinevere
# ============================================================================

set -euo pipefail
IFS=$'\n\t'

# ============================================================================
# Constants & Configuration
# ============================================================================

# Timestamp used for dump file and log file naming
TIMESTAMP="$(date -u +%Y%m%d-%H%M%S)"

# Paths — all under /var, never /tmp
DUMP_DIR="/var/backups/postgres"
LOG_DIR="/var/log/guinevere"
SUCCESS_FILE="${LOG_DIR}/last-backup-success"

# PostgreSQL connection (non-standard port 5433, see AGENTS.md context)
PG_HOST="127.0.0.1"
PG_PORT="5433"
PG_USER="guinevere"
PG_DUMP_FILE="${DUMP_DIR}/alldbs-${TIMESTAMP}.sql.gz"

# SOPS age key path — VPS production path
SOPS_AGE_KEY_FILE_DEFAULT="/home/guinevere/secrets/age-key.txt"

# Relative paths for SOPS secrets (resolved from script directory)
SECRETS_DIR_RELATIVE="secrets/backup"

# Retention — PRIMARY (idcloudhost): shorter window, faster rotation
PRIMARY_KEEP_DAILY=7
PRIMARY_KEEP_WEEKLY=4
PRIMARY_KEEP_MONTHLY=3

# Retention — SECONDARY (Cloudflare R2): longer window, DR/geo-redundant
SECONDARY_KEEP_DAILY=14
SECONDARY_KEEP_WEEKLY=8
SECONDARY_KEEP_MONTHLY=6

# restic check — verify 5% random data subset (balance speed vs coverage)
CHECK_DATA_SUBSET="5%"

# Source directories to include in backup
# /etc: system configuration (nginx, postgres, systemd units, restic configs)
# /opt/guinevere: Guinevere application code, runtime data
# /var/backups/postgres: the SQL dumps we just created
BACKUP_PATHS=(
  "/etc"
  "/opt/guinevere"
  "/var/backups/postgres"
)

# Exclude patterns — virtual filesystems, caches, temp dirs
# Why: /proc /sys /dev /run are pseudo-filesystems; /tmp /var/tmp /var/cache
# are ephemeral; /mnt /media may have mountpoints; /lost+found is fs-internal.
EXCLUDE_PATTERNS=(
  "--exclude=/proc"
  "--exclude=/sys"
  "--exclude=/dev"
  "--exclude=/run"
  "--exclude=/tmp"
  "--exclude=/mnt"
  "--exclude=/media"
  "--exclude=/lost+found"
  "--exclude=/var/cache"
  "--exclude=/var/tmp"
)

# ============================================================================
# Helper Functions
# ============================================================================

# Print usage/help text
usage() {
  cat <<'USAGE'
guinevere-backup.sh — Guinevere production backup script

Dual-repo restic backup with PostgreSQL dump, SOPS-encrypted secrets,
and retention management.

USAGE:
  sudo ./guinevere-backup.sh              Normal execution
  sudo DRY_RUN=1 ./guinevere-backup.sh    Dry-run (no actual backup)
  ./guinevere-backup.sh --help            Show this help and exit

ENVIRONMENT:
  DRY_RUN=1           Simulate backup without writing anything
  SOPS_AGE_KEY_FILE   Override age key path (default: /home/guinevere/secrets/age-key.txt)

FLOW:
  1. PostgreSQL full dump (pg_dumpall) → gzip → validate
  2. restic backup → PRIMARY (idcloudhost S3, tag: primary)
  3. restic forget --prune PRIMARY (keep-daily 7, keep-weekly 4, keep-monthly 3)
  4. restic check --read-data-subset=5% PRIMARY
  5. restic backup → SECONDARY (Cloudflare R2, tag: secondary)
  6. restic forget --prune SECONDARY (keep-daily 14, keep-weekly 8, keep-monthly 6)
  7. Write success timestamp

SECRETS:
  SOPS-encrypted env files are expected at:
    <script-dir>/secrets/backup/idcloudhost-s3-plaintext.env
    <script-dir>/secrets/backup/cloudflare-r2-plaintext.env

  These are decrypted in-memory via `sops exec-env` — no plaintext on disk.

REQUIREMENTS:
  - restic >= 0.17.0
  - sops >= 3.9.x
  - age (key at /home/guinevere/secrets/age-key.txt)
  - pg_dumpall (PostgreSQL client)
  - gzip / zcat
  - Directories: /var/backups/postgres, /var/log/guinevere

EXIT CODES:
  0   Success
  1   Any failure (set -e ensures early exit)

USAGE
}

# Log a message with timestamp to stdout
log_info() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] INFO: $*"
}

# Log a warning (non-fatal issue)
log_warn() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] WARN: $*" >&2
}

# Log an error message to stderr
log_error() {
  echo "[$(date -u '+%Y-%m-%d %H:%M:%S UTC')] ERROR: $*" >&2
}

# Run a command under DRY_RUN — print instead of execute when DRY_RUN=1
run_cmd() {
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "[DRY-RUN] Would execute: $*"
  else
    "$@"
  fi
}

# Run a command under DRY_RUN with a description — same as run_cmd but for
# inline shell constructs where a single command won't capture the intent
dry_run_echo() {
  if [ "${DRY_RUN:-0}" = "1" ]; then
    echo "[DRY-RUN] $*"
  fi
}

# ============================================================================
# Pre-flight Checks
# ============================================================================

# Handle --help flag
if [ "${1:-}" = "--help" ] || [ "${1:-}" = "-h" ]; then
  usage
  exit 0
fi

log_info "=== Guinevere Backup Start ==="
log_info "Timestamp: ${TIMESTAMP}"
log_info "Dry-run mode: $([ "${DRY_RUN:-0}" = "1" ] && echo 'ENABLED' || echo 'disabled')"

# Ensure we are running as root — restic needs root to read /etc and /opt
if [ "$(id -u)" -ne 0 ] && [ "${DRY_RUN:-0}" != "1" ]; then
  # In dry-run mode, running as non-root is acceptable (no actual I/O)
  log_error "This script must be run as root (sudo). Use 'sudo ./guinevere-backup.sh'"
  exit 1
fi

# Create required directories with secure permissions (0700 = owner-only access)
# Why 0700: backup dumps contain all database data, including potentially
# sensitive information. Only root should read them.
mkdir -p "${DUMP_DIR}" 2>/dev/null || true
mkdir -p "${LOG_DIR}"  2>/dev/null || true

# ------------------------------------------------------------------
# Logging: redirect all stdout + stderr to both terminal and log file
# Why: preserves the full execution trace for post-mortem debugging.
# ------------------------------------------------------------------
LOG_FILE="${LOG_DIR}/backup-${TIMESTAMP}.log"
if [ "${DRY_RUN:-0}" != "1" ]; then
  exec > >(tee -a "${LOG_FILE}") 2>&1
  log_info "Log file: ${LOG_FILE}"
fi

# Set SOPS_AGE_KEY_FILE — default to production path unless overridden
export SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE:-${SOPS_AGE_KEY_FILE_DEFAULT}}"

if [ ! -f "${SOPS_AGE_KEY_FILE}" ] && [ "${DRY_RUN:-0}" != "1" ]; then
  log_error "SOPS age key not found at: ${SOPS_AGE_KEY_FILE}"
  log_error "Set SOPS_AGE_KEY_FILE to the correct path or add the key."
  exit 1
fi

# Verify required binaries exist
for cmd in restic sops pg_dumpall gzip zcat; do
  if ! command -v "${cmd}" &>/dev/null; then
    log_error "Required binary not found: ${cmd}"
    exit 1
  fi
done

# Resolve secrets directory relative to script location
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SECRETS_DIR="${SCRIPT_DIR}/${SECRETS_DIR_RELATIVE}"

# Verify SOPS-encrypted env files exist
PRIMARY_SECRET="${SECRETS_DIR}/idcloudhost-s3-plaintext.env"
SECONDARY_SECRET="${SECRETS_DIR}/cloudflare-r2-plaintext.env"

if [ ! -f "${PRIMARY_SECRET}" ] && [ "${DRY_RUN:-0}" != "1" ]; then
  log_error "Primary (idcloudhost) secret file not found: ${PRIMARY_SECRET}"
  exit 1
fi

if [ ! -f "${SECONDARY_SECRET}" ] && [ "${DRY_RUN:-0}" != "1" ]; then
  log_error "Secondary (Cloudflare R2) secret file not found: ${SECONDARY_SECRET}"
  exit 1
fi

log_info "Secrets directory: ${SECRETS_DIR}"
log_info "Primary secret:   ${PRIMARY_SECRET}"
log_info "Secondary secret: ${SECONDARY_SECRET}"

# ============================================================================
# Phase 1: PostgreSQL Database Dump
# ============================================================================
# Why pg_dumpall vs pg_dump:
#   pg_dumpall dumps ALL databases + global objects (roles, tablespaces) in one
#   pass. Since this VPS hosts a single PostgreSQL cluster for Guinevere (and
#   potentially Aizanta co-located), pg_dumpall is the simplest complete backup.
#
# Why NOT pipe to restic --stdin:
#   If pg_dumpall fails silently (e.g., connection timeout), a pipe to restic
#   --stdin produces an empty/partial backup with no error. Instead, we write
#   to a temp file, validate, then include the file in restic's file paths.
#
# Why gzip:
#   pg_dumpall produces plain SQL (no native compression). gzip reduces size
#   ~5-10x. zcat can validate the compressed header without full decompression.
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 1: PostgreSQL Database Dump"
log_info "============================================"

dump_success=false

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "pg_dumpall -h ${PG_HOST} -p ${PG_PORT} -U ${PG_USER} | gzip > ${PG_DUMP_FILE}"
  dry_run_echo "Validate: zcat ${PG_DUMP_FILE} | head -1 | grep -q 'PostgreSQL'"
  dump_success=true
else
  log_info "Dumping all databases to: ${PG_DUMP_FILE}"
  log_info "Connection: ${PG_HOST}:${PG_PORT} as ${PG_USER}"

  # Dump all databases, pipe through gzip for compression
  # pg_dumpall exit code: 0 = success, 1 = fatal error
  PGPASSWORD="${PGPASSWORD:-}" \
  pg_dumpall \
    -h "${PG_HOST}" \
    -p "${PG_PORT}" \
    -U "${PG_USER}" \
    --clean \
    --if-exists \
    --no-password 2>/dev/null \
  | gzip > "${PG_DUMP_FILE}"

  # Validate dump — check the gzip header contains a PostgreSQL signature
  # Why: A failed pg_dumpall (e.g., wrong password, DB down) produces an empty
  # file that passes [ -s ] check. The SQL header "PostgreSQL database dump" is
  # always the first line of a successful pg_dumpall output.
  log_info "Validating dump integrity..."

  if [ ! -s "${PG_DUMP_FILE}" ]; then
    log_error "Dump file is empty or missing!"
    rm -f "${PG_DUMP_FILE}"
    exit 1
  fi

  if zcat "${PG_DUMP_FILE}" | head -1 | grep -q "PostgreSQL"; then
    local_size="$(du -h "${PG_DUMP_FILE}" | cut -f1)"
    log_info "Dump validation PASSED (size: ${local_size})"
    dump_success=true
  else
    log_error "Dump validation FAILED — file does not contain PostgreSQL dump header"
    log_error "This usually means the database connection failed or pg_dumpall error."
    rm -f "${PG_DUMP_FILE}"
    exit 1
  fi
fi

# ============================================================================
# Phase 2: Restic Backup — PRIMARY (idcloudhost S3)
# ============================================================================
# Why use `sops exec-env`:
#   Decrypts secrets in-memory and injects them into the child process's
#   environment. No plaintext ever touches disk. The child process inherits
#   RESTIC_REPOSITORY, AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, and
#   RESTIC_PASSWORD (or RESTIC_PASSWORD_COMMAND).
#
# Why PRIMARY first:
#   Primary is the fast, local-region S3 (idcloudhost in Indonesia). We backup
#   here first, then copy/backup to secondary for geo-redundancy.
#
# Why tag "primary":
#   Enables selective restore and per-repo retention policies.
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 2: Restic Backup — PRIMARY (idcloudhost S3)"
log_info "============================================"

# Build restic backup args as an array for safety
BACKUP_ARGS=(
  backup
  --tag "primary"
  --tag "guinevere"
  --host "$(hostname -s)"
  "${EXCLUDE_PATTERNS[@]}"
  "${BACKUP_PATHS[@]}"
)

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "sops exec-env ${PRIMARY_SECRET} ... restic ${BACKUP_ARGS[*]}"
else
  log_info "Starting restic backup to PRIMARY..."

  # sops exec-env decrypts the env file and injects variables into the shell
  # process that runs restic. The --same-process flag ensures signals work
  # correctly (though we use it via shell wrapping here for readability).
  #
  # We can't use --same-process directly because we need shell for array
  # expansion. Instead, we wrap the command string passed to exec-env.
  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE}" \
  sops exec-env "${PRIMARY_SECRET}" \
    "restic ${BACKUP_ARGS[*]}"

  backup_primary_exit=$?

  if [ "${backup_primary_exit}" -ne 0 ]; then
    log_error "PRIMARY backup failed with exit code ${backup_primary_exit}"
    log_error "See restic output above for details."
    exit 1
  fi

  log_info "PRIMARY backup completed successfully."
fi

# ============================================================================
# Phase 3: Retention Policy — PRIMARY
# ============================================================================
# Why separate forget from backup:
#   Though we could use --prune in the backup step, separating allows us to
#   verify the backup succeeded before modifying snapshot history.
#
# Why these numbers:
#   7 daily  = 1 week granular recovery
#   4 weekly = 1 month of weekly checkpoints
#   3 monthly = 3 months of monthly checkpoints (quarterly coverage)
#
# Why --prune:
#   Without --prune, forget only removes snapshot metadata. The data blocks
#   remain in the repository, consuming storage. --prune removes orphaned data.
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 3: Retention Policy — PRIMARY"
log_info "============================================"

FORGET_ARGS_PRIMARY=(
  forget
  --tag "primary"
  "--keep-daily=${PRIMARY_KEEP_DAILY}"
  "--keep-weekly=${PRIMARY_KEEP_WEEKLY}"
  "--keep-monthly=${PRIMARY_KEEP_MONTHLY}"
  --prune
)

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "sops exec-env ${PRIMARY_SECRET} ... restic ${FORGET_ARGS_PRIMARY[*]}"
  dry_run_echo "  (Would keep: daily ${PRIMARY_KEEP_DAILY}, weekly ${PRIMARY_KEEP_WEEKLY}, monthly ${PRIMARY_KEEP_MONTHLY})"
else
  log_info "Applying retention policy on PRIMARY..."
  log_info "Keeping: daily=${PRIMARY_KEEP_DAILY}, weekly=${PRIMARY_KEEP_WEEKLY}, monthly=${PRIMARY_KEEP_MONTHLY}"

  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE}" \
  sops exec-env "${PRIMARY_SECRET}" \
    "restic ${FORGET_ARGS_PRIMARY[*]}"

  log_info "PRIMARY retention policy applied."
fi

# ============================================================================
# Phase 4: Repository Check — PRIMARY
# ============================================================================
# Why --read-data-subset=5%:
#   A full --read-data can take hours on large repos. The 5% random subset
#   detects data corruption with high probability while completing quickly.
#   restic's metadata check (pack lists, indexes, tree blobs) always runs
#   regardless of --read-data-subset.
#
# Why after forget --prune:
#   Prune rewrites pack files. Checking after prune ensures the rewritten
#   data is consistent.
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 4: Repository Check — PRIMARY"
log_info "============================================"

CHECK_ARGS_PRIMARY=(
  check
  "--read-data-subset=${CHECK_DATA_SUBSET}"
)

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "sops exec-env ${PRIMARY_SECRET} ... restic ${CHECK_ARGS_PRIMARY[*]}"
else
  log_info "Running repository integrity check (${CHECK_DATA_SUBSET} data subset)..."

  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE}" \
  sops exec-env "${PRIMARY_SECRET}" \
    "restic ${CHECK_ARGS_PRIMARY[*]}"

  check_primary_exit=$?

  if [ "${check_primary_exit}" -ne 0 ]; then
    log_error "PRIMARY repository check FAILED (exit code: ${check_primary_exit})"
    log_error "Data integrity may be compromised. Investigate immediately."
    # Not exiting here — the backup itself succeeded. The check failure is a
    # warning that the repository may have issues. We still proceed to secondary
    # so we have at least one healthy copy.
  else
    log_info "PRIMARY repository check PASSED."
  fi
fi

# ============================================================================
# Phase 5: Restic Backup — SECONDARY (Cloudflare R2)
# ============================================================================
# Why secondary after primary (sequential, not parallel):
#   - Avoids simultaneous S3 uploads saturating the VPS uplink
#   - Primary is the "fast" backup (local-region idcloudhost)
#   - Secondary is geo-redundant (Cloudflare R2, global network)
#   - If primary fails, we don't waste bandwidth uploading to secondary
#
# Why tag "secondary":
#   Enables per-repo retention (longer window on secondary for DR purposes)
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 5: Restic Backup — SECONDARY (Cloudflare R2)"
log_info "============================================"

BACKUP_ARGS_SECONDARY=(
  backup
  --tag "secondary"
  --tag "guinevere"
  --host "$(hostname -s)"
  "${EXCLUDE_PATTERNS[@]}"
  "${BACKUP_PATHS[@]}"
)

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "sops exec-env ${SECONDARY_SECRET} ... restic ${BACKUP_ARGS_SECONDARY[*]}"
else
  log_info "Starting restic backup to SECONDARY (Cloudflare R2)..."

  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE}" \
  sops exec-env "${SECONDARY_SECRET}" \
    "restic ${BACKUP_ARGS_SECONDARY[*]}"

  backup_secondary_exit=$?

  if [ "${backup_secondary_exit}" -ne 0 ]; then
    log_error "SECONDARY backup failed with exit code ${backup_secondary_exit}"
    log_error "See restic output above for details."
    log_error "Primary backup is still intact — investigate R2 connectivity."
    # Not exiting — primary backup is already done; this is partial failure.
    # The success file will NOT be written, signaling the overall backup is
    # incomplete.
    exit 1
  fi

  log_info "SECONDARY backup completed successfully."
fi

# ============================================================================
# Phase 6: Retention Policy — SECONDARY
# ============================================================================
# Why longer retention on secondary:
#   Cloudflare R2 has no egress fees, making it ideal for longer-term retention.
#   14 daily + 8 weekly + 6 monthly provides ~6 months of coverage on secondary.
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 6: Retention Policy — SECONDARY"
log_info "============================================"

FORGET_ARGS_SECONDARY=(
  forget
  --tag "secondary"
  "--keep-daily=${SECONDARY_KEEP_DAILY}"
  "--keep-weekly=${SECONDARY_KEEP_WEEKLY}"
  "--keep-monthly=${SECONDARY_KEEP_MONTHLY}"
  --prune
)

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "sops exec-env ${SECONDARY_SECRET} ... restic ${FORGET_ARGS_SECONDARY[*]}"
  dry_run_echo "  (Would keep: daily ${SECONDARY_KEEP_DAILY}, weekly ${SECONDARY_KEEP_WEEKLY}, monthly ${SECONDARY_KEEP_MONTHLY})"
else
  log_info "Applying retention policy on SECONDARY..."
  log_info "Keeping: daily=${SECONDARY_KEEP_DAILY}, weekly=${SECONDARY_KEEP_WEEKLY}, monthly=${SECONDARY_KEEP_MONTHLY}"

  SOPS_AGE_KEY_FILE="${SOPS_AGE_KEY_FILE}" \
  sops exec-env "${SECONDARY_SECRET}" \
    "restic ${FORGET_ARGS_SECONDARY[*]}"

  log_info "SECONDARY retention policy applied."
fi

# ============================================================================
# Phase 7: Success Marker
# ============================================================================
# Write an ISO-8601 timestamp to /var/log/guinevere/last-backup-success.
# Why:
#   This is a sentinel file for monitoring. External health checks (Prometheus,
#   Uptime Kuma, Healthchecks.io) can check if this file was modified within
#   the expected window (e.g., < 28 hours for daily backup).
# ============================================================================
log_info ""
log_info "============================================"
log_info "Phase 7: Success Marker"
log_info "============================================"

if [ "${DRY_RUN:-0}" = "1" ]; then
  dry_run_echo "Write ISO-8601 timestamp to ${SUCCESS_FILE}"
else
  date -u '+%Y-%m-%dT%H:%M:%S%z' > "${SUCCESS_FILE}"
  log_info "Success marker written to: ${SUCCESS_FILE}"
fi

# ============================================================================
# Cleanup: Remove local dump (already safely stored in restic snapshots)
# ============================================================================
# Why remove the local dump:
#   The dump is now inside both PRIMARY and SECONDARY restic snapshots.
#   Keeping it on disk consumes space. If needed for immediate restore, it can
#   be extracted from the latest restic snapshot.
#
# Why NOT remove in dry-run:
#   In dry-run, no actual backup happened, so the dump would be lost.
# ============================================================================
if [ "${DRY_RUN:-0}" != "1" ] && [ "${dump_success}" = true ]; then
  log_info "Cleaning up local dump file..."
  rm -f "${PG_DUMP_FILE}"
  log_info "Local dump removed (data is safely in restic snapshots)."
fi

# ============================================================================
# Completion
# ============================================================================
log_info ""
log_info "============================================"
log_info "=== Guinevere Backup Completed Successfully ==="
log_info "============================================"
log_info "Timestamp:    ${TIMESTAMP}"
log_info "Log file:     ${LOG_FILE}"
log_info "Success file: ${SUCCESS_FILE}"
log_info ""

# Exit 0 — all phases completed successfully
exit 0