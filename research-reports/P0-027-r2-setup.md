# P0-027: Restic + Cloudflare R2 Setup Research

**Date**: 2026-05-31
**Scope**: Production restic backups to Cloudflare R2 (S3-compatible secondary storage)
**Sources**: Cloudflare official R2 docs, restic docs, GitHub issues, production blog references
**Verdict**: R2 works with restic's S3 backend — straightforward, well-documented, confirmed working by multiple production users.

---

## 1. Endpoint URL

The single canonical S3-compatible endpoint format:

```
https://<ACCOUNT_ID>.r2.cloudflarestorage.com
```

- **Account ID** is found in the Cloudflare Dashboard → R2 → Overview page (also at bottom of "Create API Token" confirmation page).
- **Path-style** URLs are the default: `https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<BUCKET_NAME>`
- **Virtual-hosted style** also supported: `<BUCKET_NAME>.<ACCOUNT_ID>.r2.cloudflarestorage.com`
- restic uses **path-style** by default for non-Amazon endpoints (auto-detected).
- Never use AWS-style regional URLs like `s3.us-east-1.amazonaws.com` — those do not work with R2.

**Source**: [Cloudflare R2 S3 docs](https://developers.cloudflare.com/r2/get-started/s3/)

---

## 2. Environment Variables

### Required for restic + R2

| Variable | Value | Notes |
|---|---|---|
| `RESTIC_REPOSITORY` | `s3:https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<BUCKET_NAME>` | Uses restic's S3 backend |
| `AWS_ACCESS_KEY_ID` | `<R2_ACCESS_KEY_ID>` | From R2 API token |
| `AWS_SECRET_ACCESS_KEY` | `<R2_SECRET_ACCESS_KEY>` | From R2 API token |
| `RESTIC_PASSWORD` | `<LONG_RANDOM_PASSPHRASE>` | Encrypts the repository |

### Optional / Best Practice

| Variable | Value | Notes |
|---|---|---|
| `AWS_DEFAULT_REGION` | `auto` or `us-east-1` | R2 accepts `auto`, empty, or `us-east-1` |
| `AWS_REGION` | `auto` | Newer AWS SDK env var |
| `AWS_ENDPOINT_URL` | `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` | For AWS CLI compatibility |
| `RESTIC_HOST` | `<SERVER_NAME>` | Identifies this host in snapshots |

### Region semantics for R2

- Cloudflare R2's intended region value is **`auto`**.
- **`us-east-1`** and **empty string** also alias to `auto` for tool compatibility.
- restic defaults to `us-east-1` when no region is specified — this works fine with R2.
- Can override via `-o s3.region="auto"` or `AWS_DEFAULT_REGION=auto`.

**Sources**:
- [restic GitHub issue #3757 — confirmed working with `AWS_DEFAULT_REGION="us-east-1"`](https://github.com/restic/restic/issues/3757)
- [Cloudflare R2 auth docs — uses `AWS_REGION=auto`](https://developers.cloudflare.com/r2/examples/authenticate-r2-auth-tokens/index.md)
- [restic 0.18.1 docs — S3-compatible storage](https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html)

---

## 3. Bucket Creation & Access Policy

### Create the bucket

**Via Cloudflare Dashboard:**
1. Go to R2 → Overview → Create bucket
2. Enter name (3-63 chars, lowercase, hyphens allowed)
3. Choose location hint (optional: `apac`, `eeur`, `enam`, `weur`, `wnam`, `oc`)
4. Choose storage class: `Standard` or `InfrequentAccess`
5. Click Create

**Via wrangler CLI:**
```bash
npx wrangler r2 bucket create <bucket-name>
```

### Generate API credentials

1. In Cloudflare Dashboard → R2 → Manage R2 API tokens
2. Create API Token
3. Choose permission level:
   - **Object Read & Write** (per-bucket scope) — recommended for restic
   - **Admin-level** (all buckets) — only if needed
4. Select target bucket(s)
5. Copy **Access Key ID** and **Secret Access Key** immediately — secret is shown only once

### Access policy for restic

Minimum required permissions: **Object Read & Write** on the target bucket.

| Permission Group | Resource | What restic needs |
|---|---|---|
| Workers R2 Storage Bucket Item Write | Bucket | Create/update objects (backup writes) |
| Workers R2 Storage Bucket Item Read | Bucket | List/read objects (restore, check, prune) |
| Workers R2 Storage Bucket Item Write | Bucket | Delete objects (forget --prune) |

Token does **not** need Account-level permissions for restic to work — bucket-scoped tokens are sufficient.

**Source**: [Cloudflare R2 authentication docs](https://developers.cloudflare.com/r2/api/tokens/)

---

## 4. R2-Specific Gotchas

### Region / `GetBucketLocation` Error (HISTORICAL)

- Early restic versions (<0.12 era) hit `GetBucketLocation not implemented` on `restic init`.
- **Fixed** by minio-go library update (merged PR #1651). Modern restic (0.14+) works out of the box.
- If you encounter this: set `AWS_DEFAULT_REGION=us-east-1` explicitly.

### Rate Limits

| Limit | Value | Impact on restic |
|---|---|---|
| Bucket management ops | 50/sec | Not a concern — restic does these rarely |
| Concurrent writes to same key | 1/sec | restic writes different keys per snapshot/object, unlikely to hit this |
| Object size cap (single-part) | 5 GiB | restic packs data into ~several-MB pack files by default — well under limit |
| Object size cap (multi-part) | 4.995 TiB | Fine for any realistic backup |
| Max upload parts | 10,000 | Not an issue for restic's pack-file strategy |

**Real-world note**: restic's default pack size is tens of MB. Rate limits are unlikely to affect normal backup operations.

### Multipart Uploads

- restic's S3 backend uses the minio-go library which handles multipart uploads automatically.
- No special configuration needed for multipart.
- R2 charges per operation (Class A ops: PUT, POST, LIST, multipart upload initiation/completion). Each uploaded part in a multipart upload counts as a separate Class A operation — larger part sizes = fewer operations = lower cost.

### R2 `.r2.dev` domain rate limiting

- The auto-generated `r2.dev` subdomain has **variable rate limiting** and is **not for production**.
- For production, use a **custom domain** connected to the bucket.

### Token permission gotcha

- R2 API tokens with **bucket-scoped** permissions may fail on `bucket list` operations but succeed on individual object read/write.
- For restic, bucket-scoped Object Read & Write is sufficient — `restic init` creates the bucket path, it does not need to list all buckets.
- If using rclone: add `no_check_bucket = true` in config for bucket-scoped tokens.

**Sources**:
- [Cloudflare R2 limits page](https://developers.cloudflare.com/r2/platform/limits/)
- [restic issue #3757 — region fix discussion](https://github.com/restic/restic/issues/3757)
- [rclone forum — R2 multipart speed tuning](https://forum.rclone.org/t/how-to-maximize-single-file-multipart-upload-speed-to-cloudflare-r2-s3-compatible/34311)

---

## 5. Exact Commands — Production Pattern

### 5.1 Environment file (`/root/restic-env`)

```bash
export RESTIC_REPOSITORY="s3:https://<ACCOUNT_ID>.r2.cloudflarestorage.com/<BUCKET_NAME>"
export RESTIC_PASSWORD="<YOUR_LONG_RANDOM_PASSPHRASE>"
export AWS_ACCESS_KEY_ID="<R2_ACCESS_KEY_ID>"
export AWS_SECRET_ACCESS_KEY="<R2_SECRET_ACCESS_KEY>"
export RESTIC_HOST="<SERVER_NAME>"
```

Secure it:
```bash
sudo chmod 600 /root/restic-env
```

### 5.2 Initialize repository (run once)

```bash
source /root/restic-env
restic init
# Expected output: "created restic repository <hash> at s3:https://..."
```

### 5.3 First manual backup

```bash
source /root/restic-env
restic --verbose backup /etc /home /var/www \
  --exclude=/dev --exclude=/proc --exclude=/sys \
  --exclude=/run --exclude=/tmp --exclude=/mnt \
  --exclude=/media --exclude=/lost+found \
  --exclude=/var/cache --exclude=/var/tmp
```

### 5.4 Automated backup script (`/usr/local/bin/restic-backup.sh`)

```bash
#!/usr/bin/env bash
set -euo pipefail

source /root/restic-env

WWW_ROOT="/var/www"
DB_DUMP_DIR="/var/backups/db"
EXTRA_PATHS="/etc /home"

EXCLUDES=(
  --exclude=/dev
  --exclude=/proc
  --exclude=/sys
  --exclude=/run
  --exclude=/tmp
  --exclude=/mnt
  --exclude=/media
  --exclude=/lost+found
  --exclude=/var/cache
  --exclude=/var/tmp
)

restic backup \
  "${EXCLUDES[@]}" \
  "${WWW_ROOT}" \
  "${DB_DUMP_DIR}" \
  ${EXTRA_PATHS}

restic forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 12 \
  --prune

restic check --read-data-subset=1%
```

Make executable:
```bash
sudo chmod +x /usr/local/bin/restic-backup.sh
```

### 5.5 Systemd timer (run daily)

**Service file** (`/etc/systemd/system/restic-backup.service`):
```ini
[Unit]
Description=Restic backup to Cloudflare R2

[Service]
Type=oneshot
EnvironmentFile=/root/restic-env
ExecStart=/usr/local/bin/restic-backup.sh
Nice=10
IOSchedulingClass=best-effort
IOSchedulingPriority=7
```

**Timer file** (`/etc/systemd/system/restic-backup.timer`):
```ini
[Unit]
Description=Daily restic backup to Cloudflare R2

[Timer]
OnCalendar=daily
RandomizedDelaySec=3600
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:
```bash
sudo systemctl daemon-reload
sudo systemctl enable --now restic-backup.timer
```

### 5.6 Restore

```bash
source /root/restic-env
# List snapshots
restic snapshots

# Restore latest snapshot
restic restore latest --target /restore-destination

# Restore specific snapshot by ID
restic restore <SNAPSHOT_ID> --target /restore-destination

# Restore specific path from snapshot
restic restore latest --target / --include /etc/nginx
```

---

## 6. Key Sources

| Source | URL |
|---|---|
| Cloudflare R2 S3 docs | https://developers.cloudflare.com/r2/get-started/s3/ |
| Cloudflare R2 auth tokens | https://developers.cloudflare.com/r2/api/tokens/ |
| Cloudflare R2 limits | https://developers.cloudflare.com/r2/platform/limits/ |
| Cloudflare R2 CLI setup | https://developers.cloudflare.com/r2/get-started/cli/ |
| restic 0.18.1 S3 backend docs | https://restic.readthedocs.io/en/stable/030_preparing_a_new_repo.html |
| restic GitHub issue #3757 (R2 support) | https://github.com/restic/restic/issues/3757 |
| PixelRaider — VPS backups with restic+R2 (production guide) | https://pixelraider.com/vps-backups-with-restic-and-cloudflare-r2/ |
| YashGarg — Minecraft backups to R2 | https://yashgarg.dev/posts/minecraft-backup-r2/ |
| Dify discussion — automated restic+R2 | https://github.com/langgenius/dify/discussions/6791 |
| RcloneView — R2 troubleshooting | https://rcloneview.com/support/blog/fix-cloudflare-r2-upload-errors-rcloneview |

---

## 7. Bottom Line

- **Works reliably**: restic's S3 backend + R2 is production-verified by multiple sources.
- **Minimal config**: Only 4 env vars needed (`RESTIC_REPOSITORY`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `RESTIC_PASSWORD`).
- **Region**: `auto` or `us-east-1` — both work. Default restic behavior (`us-east-1`) works without explicit config.
- **Cost edge**: R2 charges per Class A operation. restic's deduplication means fewer writes over time, but initial backups trigger many PUT operations. No egress fees.
- **Gotchas**: Old minio-go library issue is long fixed. Bucket-scoped tokens are fine. No special multipart config needed. Use custom domain for production (avoid `r2.dev` rate limits).