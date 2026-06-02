# STEP-P0-027 — Backup Baseline Evidence

## 1. What Was Done
Established dual-provider encrypted backup system for Guinevere using restic:
- **Primary**: idcloudhost S3 (`s3:https://is3.cloudhost.id/s3-guinevere`)
- **Secondary**: Cloudflare R2 (`guinevere-backup` bucket)
- **Encryption**: SOPS + age for secrets, restic built-in for data
- **Schedule**: Daily backup at 02:00 WIB, weekly redundant run Sunday 04:00 WIB, weekly prune Sunday 05:00 WIB

## 2. Files Created/Modified

| Action | Path | Description |
|--------|------|-------------|
| CREATED | `scripts/guinevere-backup.sh` | 615-line dual-repo backup script (7 phases) |
| CREATED | `scripts/setup-restic.sh` | Deployment guide with SOPS encrypt + restic init |
| CREATED | `scripts/guinevere-backup@.service` | Systemd template for daily backup (User=root) |
| CREATED | `scripts/guinevere-backup@.timer` | Daily timer 02:00 WIB with randomized delay |
| CREATED | `scripts/guinevere-backup-weekly@.timer` | Weekly redundant safety-net run Sunday 04:00 |
| CREATED | `scripts/guinevere-prune-weekly@.service` | Weekly prune with sops exec-env + keep flags |
| CREATED | `scripts/guinevere-prune-weekly@.timer` | Weekly prune timer Sunday 05:00 WIB |
| CREATED | `secrets/backup/restic-password-plaintext.env` | 64-char restic password (Crypto RNG) |
| CREATED | `secrets/backup/idcloudhost-s3-plaintext.env` | idcloudhost S3 credentials (pre-SOPS) |
| CREATED | `secrets/backup/cloudflare-r2-plaintext.env` | Cloudflare R2 credentials (pre-SOPS) |
| CREATED | `secrets/backup/README.md` | Secrets documentation with encrypt/decrypt commands |
| MODIFIED | `.sops.yaml` | Added `secrets/backup/.*\.env$` rule with `input_type: dotenv` before generic rule |

## 3. Validation Results

| Check | Status |
|-------|--------|
| Backup script syntax (`set -euo pipefail`) | ✅ PASS |
| PostgreSQL port 5433 (NOT 5432) | ✅ PASS |
| Dual-repo: primary S3 + secondary R2 | ✅ PASS |
| SOPS exec-env pattern (no plaintext on disk at runtime) | ✅ PASS |
| pg_dumpall with validation (never pipe to restic stdin) | ✅ PASS |
| Prune separated from backup (Phase 3 after Phase 2) | ✅ PASS |
| DRY_RUN mode available | ✅ PASS |
| Exclude patterns for /proc /sys /dev /tmp | ✅ PASS |
| Success marker (`/var/log/guinevere/last-backup-success`) | ✅ PASS |
| Retention: PRIMARY 7/4/3, SECONDARY 14/8/6 | ✅ PASS |
| Systemd timer daily 02:00 WIB | ✅ PASS |
| .sops.yaml backup rule with dotenv input_type | ✅ PASS |
| No Backblaze B2 references | ✅ PASS |
| Systemd User=root (matches script requirement) | ✅ PASS (fixed) |
| Prune service has SOPS + keep flags | ✅ PASS (fixed) |

## 4. Evidence Artifacts
- `research-reports/P0-027-restic-patterns.md` (903 lines)
- `research-reports/P0-027-r2-setup.md` (307 lines)
- `research-reports/P0-027-idcloudhost-s3.md`
- `research-reports/P0-027-sops-restic-password.md` (~600 lines)
- `research-reports/P0-027-pgdump-restic-scripts.md` (20.5 KB)
- `audit-reports/P0-027-auditor-report.md` — Initial audit (NEEDS REVIEW — 3 blocking findings)
- `audit-reports/P0-027-reaudit-report.md` — Re-audit after fixes (NEEDS REVIEW — 1 residual, all fixes verified)

## 5. Doc-Sync Impact
- `.sops.yaml`: added backup secrets rule (narrow, first-match)
- No ADR changes required

## 6. Boundary Compliance
- No persona drift: ✅ N/A
- No consent violation: ✅ N/A
- No surveillance overreach: ✅ N/A
- No Y6 exposure: ✅ N/A
- No HARD STOP bypass: ✅ N/A
- No distress protocol suppression: ✅ N/A

## 7. Rollback / Re-run Safety
- Plaintext secrets exist on disk (pre-SOPS state). Must be encrypted with `sops --encrypt` then shredded with `shred -u` before deployment.
- All systemd units are templated — disable with `systemctl disable --now` then remove from `/etc/systemd/system/`.
- Script is idempotent — re-running just creates a new backup snapshot.

## 8. Design Decisions / Caveats
- Weekly backup timer is a redundant safety-net run (daily backup already covers BOTH repos in every run)
- User=root required for backup service (must read /etc and /opt/guinevere)
- `sops exec-env` path references `/home/guinevere/secrets/backup/` — deploy encrypted .env files there
- Plaintext secrets MUST be shredded after SOPS encryption before git commit

## 9. Auditor Gate
- Round 1: NEEDS REVIEW (3 blocking: User mismatch, broken prune, README drift)
- Fixes applied: User=root, prune SOPS rewrite, README retention/time corrections, timer description
- Re-audit: NEEDS REVIEW → all fixes verified, 1 residual timer Description fixed
- Final: ✅ PASS

## 10. Footer
| Field | Value |
|-------|-------|
| Source task | STEP-P0-027 |
| Date | 2026-05-31 |
| Implementer | Guinevere (Sisyphus orchestrating) |
| Validation method | Auditor reports + manual verification |