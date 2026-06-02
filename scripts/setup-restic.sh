#!/usr/bin/env bash
# =============================================================================
# setup-restic.sh — Restic Backup Deployment Guide
# =============================================================================
# This is a DOCUMENTATION script. Do NOT run it directly.
# Commands are commented out — uncomment and adapt for your environment.
# Target: VPS Ubuntu (user: guinevere)
# =============================================================================
set -euo pipefail
IFS=$'\n\t'

echo "=== Restic Backup Setup Guide ==="
echo "Run commands manually by uncommenting sections below."
echo ""
echo "Prerequisites:"
echo "  - SOPS installed (go install github.com/getsops/sops/v3/cmd/sops@latest)"
echo "  - age installed (apt install age or go install filippo.io/age/cmd/...@latest)"
echo "  - restic installed (apt install restic)"
echo "  - Age key at ~/.config/sops/age/keys.txt"
echo "  - .sops.yaml configured at repo root"
echo ""

# =============================================================================
# STEP 1: Encrypt secrets with SOPS+age
# =============================================================================
# Source files are at: secrets/backup/*-plaintext.env
# Encrypted files will replace them (same filename, SOPS-encrypted content).
#
# Commands:
<<COMMENT
# --- Encrypt restic password ---
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/restic-password-plaintext.env \
  > secrets/backup/restic-password.env

# --- Encrypt idcloudhost S3 credentials ---
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/idcloudhost-s3-plaintext.env \
  > secrets/backup/idcloudhost-s3.env

# --- Encrypt Cloudflare R2 credentials ---
sops --encrypt \
  --input-type dotenv \
  --output-type dotenv \
  secrets/backup/cloudflare-r2-plaintext.env \
  > secrets/backup/cloudflare-r2.env

# --- Shred plaintext files after encryption ---
shred -u secrets/backup/*-plaintext.env

# Verify encrypted files decrypt correctly:
sops --decrypt --output-type dotenv secrets/backup/restic-password.env
sops --decrypt --output-type dotenv secrets/backup/idcloudhost-s3.env
sops --decrypt --output-type dotenv secrets/backup/cloudflare-r2.env
COMMENT

# =============================================================================
# STEP 2: Deploy encrypted secrets to VPS
# =============================================================================
# Copy encrypted .env files to VPS /etc/restic/ (as root)
#
# Commands:
<<COMMENT
# On workstation:
scp secrets/backup/restic-password.env guinevere@<vps-host>:/tmp/
scp secrets/backup/idcloudhost-s3.env guinevere@<vps-host>:/tmp/
scp secrets/backup/cloudflare-r2.env guinevere@<vps-host>:/tmp/

# On VPS:
sudo mkdir -p /etc/restic
sudo mv /tmp/restic-password.env /etc/restic/
sudo mv /tmp/idcloudhost-s3.env /etc/restic/
sudo mv /tmp/cloudflare-r2.env /etc/restic/
sudo chown root:root /etc/restic/*.env
sudo chmod 600 /etc/restic/*.env
COMMENT

# =============================================================================
# STEP 3: Initialize restic repositories
# =============================================================================
# Commands:
<<COMMENT
# --- Initialize idcloudhost S3 (primary) ---
sops exec-env /etc/restic/idcloudhost-s3.env \
  'restic init --repository-version 2 --verbose'

# --- Initialize Cloudflare R2 (secondary) with matching chunker params ---
sops exec-env /etc/restic/cloudflare-r2.env \
  'restic init \
    --repository-version 2 \
    --copy-chunker-params \
    --from-repo s3:https://is3.cloudhost.id/s3-guinevere \
    --verbose'

# Verify initialization — list snapshots (should be empty):
sops exec-env /etc/restic/idcloudhost-s3.env \
  'restic snapshots'

sops exec-env /etc/restic/cloudflare-r2.env \
  'restic snapshots'
COMMENT

# =============================================================================
# STEP 4: Test backup & restore
# =============================================================================
# Commands:
<<COMMENT
# --- Test backup to primary ---
sops exec-env /etc/restic/idcloudhost-s3.env \
  'restic backup --verbose /etc/hostname'

# --- Copy snapshot to secondary ---
sops exec-env /etc/restic/cloudflare-r2.env \
  'restic copy \
    --from-repo s3:https://is3.cloudhost.id/s3-guinevere \
    --from-password-command "sops --decrypt --output-type dotenv /etc/restic/idcloudhost-s3.env | grep RESTIC_PASSWORD | cut -d= -f2" \
    --verbose'

# --- Restore test ---
sops exec-env /etc/restic/idcloudhost-s3.env \
  'restic restore latest --target /tmp/restic-test --verbose'
ls -la /tmp/restic-test
rm -rf /tmp/restic-test

# --- Cleanup test snapshot ---
sops exec-env /etc/restic/idcloudhost-s3.env \
  'restic forget --keep-daily 1 --prune'
COMMENT

# =============================================================================
# STEP 5: Schedule with systemd timers (post-deployment)
# =============================================================================
# See research-reports/P0-027-restic-patterns.md for systemd service/timer
# templates. Deploy to /etc/systemd/system/restic-backup@.service and
# /etc/systemd/system/restic-backup@.timer on the VPS.

echo "=== Guide complete ==="
echo "See secrets/backup/README.md for file documentation."
echo "See research-reports/P0-027-restic-patterns.md for full patterns."