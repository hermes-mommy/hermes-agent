# B6+B7 Backup State Diagnosis — guinevere-vps

> **Date:** 2026-06-07  
> **Scope:** restic presence/version, backup scripts, S3/restic config, secrets inventory, ADR-032 compliance  
> **Host:** guinevere-vps (Tailscale 100.94.104.22, user guinevere)  
> **Commands:** All run via `ssh guinevere-vps "<command>"`

---

## 1. Restic Binary Presence

| Check | Result |
|-------|--------|
| `which restic` | **Not in PATH** — command not found |
| `restic version` | **Not in PATH** — command not found |
| Binary at `/home/guinevere/bin/restic` | **PRESENT** — `restic 0.17.3 compiled with go1.23.3 on linux/amd64` |
| Binary at `/home/guinevere/C:Usersfaizz/bin/restic` | **PRESENT** — identical binary (26501272 bytes, same Go BuildID) |
| `/home/guinevere/.cache/restic/` | **PRESENT** — active cache with 3 repo IDs cached |
| PATH includes `/home/guinevere/bin` | **NO** — PATH is empty/unset in SSH session |

**Verdict:** restic 0.17.3 is installed as a standalone binary but not added to PATH. Needs `export PATH="$HOME/bin:$PATH"` or symlink to `/usr/local/bin`.

---

## 2. Restic Repositories — Historical Activity

From the restic cache at `/home/guinevere/.cache/restic/`, three repository cache directories exist:

| Cache Hash | Last Modified | Notes |
|---|---|---|
| `2d0aa91136df348e...` | 2026-05-31 23:00 | Earliest repo interaction |
| `6b865e83cff4aa6e...` | 2026-06-02 06:29 | Snapshots and index present |
| `c8c1a5bc09a5e655...` | 2026-06-02 06:27 | Third repo cache |

The backup logs confirm **two restic repositories were actively used**:

- **PRIMARY** (idcloudhost S3): endpoint `s3:https://is3.cloudhost.id/...` — 4 snapshots on record
- **SECONDARY** (Cloudflare R2): Cloudflare S3-compatible endpoint — 2 snapshots on record

Both repos passed `restic check --read-data-subset=5%` with **no errors** on their last run.

---

## 3. Backup Scripts

### 3a. Main Production Script

**Path:** `/home/guinevere/code/guinevere/scripts/guinevere-backup.sh`
**Present:** YES
**Status:** Written but **NEVER EXECUTED** based on log analysis

This is the canonical dual-repo script that does:
1. PostgreSQL dump (pg_dumpall via port 5433) -> gzip -> validate
2. restic backup -> PRIMARY (idcloudhost S3, tag: primary)
3. restic forget --prune PRIMARY (7d + 4w + 3m)
4. restic check --read-data-subset=5% PRIMARY
5. restic backup -> SECONDARY (Cloudflare R2, tag: secondary)
6. restic forget --prune SECONDARY (14d + 8w + 6m)
7. Write success timestamp

Uses `sops exec-env` — decrypts secrets in-memory, never writes plaintext.

### 3b. Docker Edition Script (Actually Used)

**Path:** `/home/guinevere/code/guinevere/scripts/guinevere-backup-docker.sh`
**Present:** YES
**Status:** WAS USED for all historical backups (based on log timestamps)

This script differs from the production version:
- Uses `docker exec guinevere-postgres pg_dumpall` instead of direct psql
- Sources secrets via `sops --decrypt` then `source <(...)` pattern
- Backs up `/home/guinevere/config` and `/home/guinevere/data` instead of `/etc` and `/opt/guinevere`
- Uses temporary directories for dump files
- Does NOT write success marker file

### 3c. Setup Guide Script

**Path:** `/home/guinevere/code/guinevere/scripts/setup-restic.sh`
**Present:** YES
**Status:** Documentation only — all commands are commented out

Documents the encryption/deployment/initialization workflow. References `secrets/backup/` for SOPS-encrypted env files.

### 3d. Scripts Directory Scan (grep for S3/restic/backup/AWS/R2)

```
$ grep -rn -i 'S3\|restic\|backup\|RESTIC\|AWS\|R2\|IDCloud' scripts/
    (All three scripts above matched, no other files)
```

---

## 4. S3/Restic Config References

### 4a. Backup Directories

| Path | Contents | Status |
|------|----------|--------|
| `/home/guinevere/backups/local/` | empty | **Empty** |
| `/home/guinevere/backups/s3/` | empty | **Empty** |
| `/home/guinevere/backups/r2/` | empty | **Empty** |
| `/home/guinevere/backups/scripts/` | `startup_gate.py` (11.8 KB) | Non-backup file |
| `/home/guinevere/backups/src/` | `mcp/custom_manager.py` | Non-backup file |
| `/home/guinevere/backups/phase-6/` | `llm_router.py.20260606_114227`, `main.py.20260606_114227` | Phase-6 file backups |
| `/home/guinevere/data/backups/` | empty | **Empty** |

**Total size:** 68 KB across all backup directories.

### 4b. Config Directories

| Path | Exists? |
|------|---------|
| `/home/guinevere/.config/restic/` | **NO** |
| `/home/guinevere/.restic/` | **NO** |
| `/etc/restic/` | **NO** |

### 4c. Environment Files (grep for restic/AWS/S3/R2/backup/bucket)

No matches found — none of the `.env.*` files in `/home/guinevere/code/guinevere/` contain backup credentials.

---

## 5. Secrets Inventory — Backup-Related

### 5a. Full Secrets Directory Listing

```
/home/guinevere/secrets/
?? age-key.txt                    (189 bytes)
?? age-key.txt.compromised-20260531 (189 bytes)
?? db-passwords.yaml              (2004 bytes)
?? github-pat.yaml                (1192 bytes)
?? redis-acl-passwords.yaml       (2071 bytes)
?? redis-password.yaml            (1241 bytes)

/home/guinevere/code/guinevere/secrets/
?? .env.9router                   (436 bytes)
?? .env.9router.sops              (1720 bytes)
```

### 5b. Backup Secrets — MISSING

The following are **REQUIRED BY SCRIPT** but **DO NOT EXIST**:

| Expected Path | Required By | Status |
|---|---|---|
| `secrets/backup/idcloudhost-s3-plaintext.env` | `guinevere-backup.sh` | **MISSING** |
| `secrets/backup/cloudflare-r2-plaintext.env` | `guinevere-backup.sh` | **MISSING** |
| `secrets/backup/restic-password-plaintext.env` | `setup-restic.sh` | **MISSING** |
| `secrets/backup/idcloudhost-s3.env` (SOPS-encrypted) | `guinevere-backup-docker.sh` | **MISSING** |
| `secrets/backup/cloudflare-r2.env` (SOPS-encrypted) | `guinevere-backup-docker.sh` | **MISSING** |
| `secrets/backup/restic-password.env` (SOPS-encrypted) | setup docs | **MISSING** |
| `/etc/restic/idcloudhost-s3.env` | `setup-restic.sh` alternative path | **MISSING** |
| `/etc/restic/cloudflare-r2.env` | `setup-restic.sh` alternative path | **MISSING** |
| `/etc/restic/restic-password.env` | `setup-restic.sh` alternative path | **MISSING** |

### 5c. Critical Observation

The backup logs show backups **WERE WORKING** on May 31 and June 2 using `guinevere-backup-docker.sh`, which sourced from `$SECRET_DIR/restic-password.env`, `$SECRET_DIR/idcloudhost-s3.env`, and `$SECRET_DIR/cloudflare-r2.env`. These SOPS-encrypted files existed at some point but are now **gone** — the `secrets/backup/` directory does not exist at all.

---

## 6. ADR-032 Compliance Assessment

**ADR-032** (`adr/ADR-032-backup-storage-strategy.md`) — Status: **Accepted** (2026-05-31):
- Primary: idcloudhost S3 (`guinevere-dr-backups` bucket)
- Secondary: Cloudflare R2 (`guinevere-dr-backups` bucket)
- Retention: 7 daily + 4 weekly + 3 monthly (primary), 14 daily + 8 weekly + 6 monthly (secondary)
- Dual-repo design matches the `guinevere-backup.sh` script exactly

**Compliance Status:**

| ADR-032 Requirement | Current State | Compliant? |
|---|---|---|
| restic >= 0.17.0 | 0.17.3 present | **YES** |
| idcloudhost S3 primary | Repos initialized, last backup 2026-06-02, **secrets missing** | **PARTIAL** |
| Cloudflare R2 secondary | Repos initialized, last backup 2026-06-02, **secrets missing** | **PARTIAL** |
| PostgreSQL dump before backup | pg_dumpall via Docker (4318 bytes last run) | **YES** |
| Retention 7d/4w/3m primary | Policy configured in script | **YES** (config only) |
| Retention 14d/8w/6m secondary | Policy configured in script | **YES** (config only) |
| Success marker | Script writes it, but never deployed | **NO** |
| Scheduled execution (systemd timer) | No cron, no systemd timer, no systemd service | **NO** |
| Restore test documented | Not in any script | **NO** |

---

## 7. Backup History Timeline

| Date | Script Used | PRIMARY | SECONDARY | Secrets Present? | Status |
|---|---|---|---|---|---|
| 2026-05-31 23:04 | `guinevere-backup-docker.sh` | Initialized | N/A | YES | First backup (36 MB /tmp) |
| 2026-05-31 23:10 | `guinevere-backup-docker.sh` | Snapshot saved | N/A | YES | config + data |
| 2026-05-31 23:12 | `guinevere-backup-docker.sh` | Snapshot saved | Snapshot saved | YES | Dual-repo established |
| 2026-06-02 06:27 | `guinevere-backup-docker.sh` | Snapshot saved | Snapshot saved | YES | **Last successful backup** |
| 2026-06-07 | - | No backup | No backup | **MISSING** | **5 days without backup** |

---

## 8. What Actually Works vs What's Missing

### Works Now
- restic 0.17.3 binary present (`/home/guinevere/bin/restic`)
- Both idcloudhost S3 and Cloudflare R2 repos were initialized
- Backup scripts exist (`guinevere-backup.sh` canonical, `guinevere-backup-docker.sh` proven)
- PostgreSQL accessible via Docker (`docker exec guinevere-postgres pg_dumpall`)
- SOPS + age key present (`/home/guinevere/secrets/age-key.txt`)
- ADR-032 accepted with correct provider choices

### Missing / Broken
- **Backup secrets are MISSING** -- `secrets/backup/` directory + contents entirely absent
- No scheduled execution (cron / systemd timer)
- No restore test or recovery runbook
- restic not in PATH
- Success marker file (`/var/log/guinevere/last-backup-success`) never created
- `guinevere-backup.sh` (canonical) never executed -- only `-docker.sh` variant was used
- `guinevere-backup.sh` expects paths `/etc`, `/opt/guinevere` but Docker script backs up `/home/guinevere/config`, `/home/guinevere/data`

---

## 9. Recommendation — Viable Backup Path

**The only viable backup path right now is restic+S3/R2**, because:

1. **restic binary exists** and works (v0.17.3)
2. **Both repos are initialized** and known-good (passed health checks)
3. **Scripts are written** -- the full dual-repo workflow is automated
4. **SOPS infrastructure is ready** -- age key present, encryption/decryption works

**What's blocking execution:**

The **sole blocker** is the missing `secrets/backup/` directory with SOPS-encrypted env files. Without them, both scripts fail immediately because they can't get `RESTIC_REPOSITORY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `RESTIC_PASSWORD`.

**Recovery path (two options):**

1. **Recreate backup secrets from known credentials** -- if the idcloudhost S3 and Cloudflare R2 access keys are known (e.g., from password manager or provider dashboard), create new `-plaintext.env` files and encrypt them with `sops --encrypt`.

2. **Re-initialize from scratch** -- if credentials are lost, create new S3 buckets and R2 buckets, generate new credentials, encrypt, and run `restic init` on both targets.

**Not recommended:** Hermes/PG/Redis fallback is not a backup strategy -- it covers data persistence but not off-site DR. The restic+S3/R2 path already has scripts, proven repos, and ADR-032 alignment.

---

## 10. Commands Executed

All commands below ran via `ssh guinevere-vps`:

```bash
# restic presence
which restic
restic version 2>/dev/null

# scripts
cat scripts/guinevere-backup.sh 2>/dev/null | head -30
ls scripts/
grep -rn -i 'S3\|restic\|backup\|RESTIC\|AWS\|R2\|IDCloud' scripts/

# secrets
ls secrets/ | grep -i backup
ls -la secrets/
ls -la /home/guinevere/code/guinevere/secrets/backup/ 2>&1
ls -la /home/guinevere/code/guinevere/secrets/

# restic config
ls -la ~/.config/restic/ 2>&1
ls -la /etc/restic/ 2>&1
ls -la /home/guinevere/.restic/ 2>&1
/home/guinevere/bin/restic version

# backup dirs
ls -la /home/guinevere/backups/
ls -la /var/backups/postgres/ 2>&1
ls -la /var/log/guinevere/
cat /var/log/guinevere/backup-20260602_062732.log

# ADR grep (local)
# adr/ADR-032-backup-storage-strategy.md -- read fully
```

---

*Report generated by Guinevere (Sisyphus-Junior) during B6+B7 diagnostic phase. No files modified.*
