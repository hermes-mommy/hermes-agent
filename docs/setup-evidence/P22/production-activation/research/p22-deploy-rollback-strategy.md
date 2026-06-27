# P22 — Deploy + Backup + Rollback Strategy (Production Activation)

**Author:** Deploy/Rollback Strategy Auditor (sub-agent, READ-ONLY)
**Date:** 2026-06-27
**Scope:** P22 Life Integration Hub library + migration + (no) startup wiring change
**Target:** VPS `faiz-prod-01` (`ssh guinevere-vps` → user `guinevere`; alt `guinevere-root`)
**Hard scope guard:** Only `guinevere-core` restarts. **9Router (LLM proxy + Tailscale sidecar) and P26 are NEVER touched.**

> All findings in this plan are grounded in live VPS discovery (this audit run), not
> in repo memory. Operator must run the deploy themselves; this document is the
> exact procedure, not an action.

---

## 1. VPS Layout (verified 2026-06-27)

| Item | Value | Source |
|---|---|---|
| Project root | `/home/guinevere/code/guinevere` | `systemctl cat guinevere-core.service` → `WorkingDirectory=` |
| Repo origin | `https://github.com/fazulfi/guinevere.git` (branch `main`) | `git remote -v` |
| Last commit on VPS | `123a31a fix(p11): persist neonize device store in session dir` | `git log -1` |
| Working tree status | DIRTY — `git status -s` shows modified: `alembic/env.py`, `alembic/versions/p5_add_loop_indexes.py`, `pyproject.toml`, `src/__init__.py`, `src/core/main.py`, `src/core/api/routes.py`, `src/core/services/llm_metrics.py`, `src/core/services/prompt_loader.py`, `src/discord/_command_registry.py`, `src/discord/_entrypoint.py` (and many docs in `docs/`). | `git status` |
| Venv | `/home/guinevere/code/guinevere/.venv` (Python 3.12) | `ls .venv/bin/python*` |
| Alembic | `alembic.ini` + `alembic/env.py`; migrations in `alembic/versions/` | `ls alembic/` |
| Local P22 library | NOT on VPS yet — `src/life_integrations/` missing | `ls src/life_integrations` → empty |
| Local P22 migration | `alembic/versions/p22_001_integration_schema.py` (NOT on VPS yet) | local `alembic/versions/` listing |
| Backup target | `/home/guinevere/data/backups/` (currently empty; 39 GB free on `/`) | `df -h /home/guinevere` |
| Slice | `guinevere.slice` (1 GB high / 2 GB max, 200% CPU quota) | `systemctl show guinevere.slice` |
| Sealed env files | `.env.core .env.discord .env.gmail .env.hermes .env.loops .env.mcp .env.monitoring .env.scheduler .env.surveillance .env.wearable .env.x_poster` (all `chmod 600`, owned by `guinevere`) | `ls -la .env*` |
| Existing backup script | `~/code/guinevere/scripts/guinevere-backup-docker.sh` (canonical pattern: `docker exec guinevere-postgres pg_dumpall -U guinevere \| gzip`) | read of script |

### Active services to PRESERVE (do-not-touch)

```
guinevere-9router.service         Guinevere 9Router LLM Proxy (/usr/bin/9router :20128)
9router-proxy.service             9Router Tailscale Proxy (localhost:20128 -> Tailscale:20130)
cloudflared.service               Cloudflare Tunnel (Discord webhook)
guinevere-discord.service         Discord bot
guinevere-mcp.service             MCP Gateway Server
guinevere-monitoring.service      Prometheus / Grafana / Loki / Promtail / Alertmanager
guinevere-obscura.service         Obscura CDP Server
guinevere-whatsapp.service        WhatsApp channel (Neonize)
guinevere-x-poster.service        X Poster service
```

Only **`guinevere-core.service`** is the deploy target.

---

## 2. `guinevere-core` Unit Analysis

**Unit file:** `/etc/systemd/system/guinevere-core.service`

```
[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
Environment=PYTHONPATH=/home/guinevere/code/guinevere
Environment=PYTHONDONTWRITEBYTECODE=1
Environment=VIRTUAL_ENV=/home/guinevere/code/guinevere/.venv
EnvironmentFile=/home/guinevere/code/guinevere/.env.core
ExecStart=/home/guinevere/code/guinevere/.venv/bin/uvicorn src.core.main:app \
            --host 127.0.0.1 --port 8000 --workers 2
Restart=always
RestartSec=10
Slice=guinevere.slice
MemoryHigh=1G
MemoryMax=2G
CPUQuota=200%
ProtectSystem=full
ReadWritePaths=/home/guinevere/code/guinevere
ReadWritePaths=/home/guinevere/data
ReadWritePaths=/home/guinevere/logs
ReadWritePaths=/home/guinevere/evidence
ReadWritePaths=/home/guinevere/.hermes
```

**Critical unit details:**

- `Requires=docker.service guinevere-9router.service` — restarting `guinevere-core` does **NOT** restart 9Router, but the unit **cannot start** unless 9Router is up. (As of audit, both are `active`.)
- `Requires=docker.service` — Docker must remain up.
- `User=guinevere` — service runs as `guinevere`, not root. **All backup/restore commands must run as `guinevere`** (or `guinevere-root` if elevated). `sudo -u postgres` is **NOT** available (no `postgres` Unix user on the host — PG is containerized).
- `EnvironmentFile=/home/guinevere/code/guinevere/.env.core` — secrets live here. File is `chmod 600` and contains: `GUINEVERE_9ROUTER_API_KEY`, `REDIS_PASSWORD`, `REDIS_URL`, `DATABASE_URL`, `DISCORD_BOT_TOKEN`, `DISCORD_HOME_CHANNEL`. **(Values redacted; never echoed.)**
- `Restart=always` + `RestartSec=10` — `systemctl restart` is safe; a crash inside the unit will auto-recover.

### **Pre-deploy finding (CRITICAL): DB password in `.env.core` is stale**

`alembic current` from inside the venv fails with `asyncpg.exceptions.InvalidPasswordError: password authentication failed for user "guinevere_core"` when authenticating with the password that is currently in `.env.core` (the same DSN that is hard-coded into `alembic.ini` via `sqlalchemy.url = postgresql+asyncpg://guinevere_core:****@localhost:5433/guinevere` and substituted at runtime via `GUINEVERE_DB_PASSWORD` env var).

**Why this matters for P22 deploy:**

- `alembic upgrade head` from the deploy shell will fail with the same `InvalidPasswordError` if it relies on `.env.core`'s `DATABASE_URL`. The P22 migration **MUST NOT** be applied blind.
- The running `guinevere-core` service is healthy (verified `/health/detailed` → 200, all components `ok`). The application must therefore be reading the correct password from a different source (likely `SystemD` EnvironmentFile combined with a different `.env` loader, or the `pglisten` role differs from `alembic.ini`). This must be reconciled **before** the migration step (see §5 mitigation A).
- The `ops.alembic_version` table currently has **4 rows** (`p19_001, p19_002, p19_003, p20_001`) — an unusual multi-head state. The schema for `audit.audit_trail.chain_version` and `project_id` exists, and `life_kernel.*` tables exist, so the schema migrations **were applied** in the past. `alembic upgrade head` may be a no-op (if all heads are present) or may try to reapply (if revision graph is split). Investigate BEFORE running `alembic upgrade head` (see §5 mitigation B).

> These two pre-deploy findings are the biggest risks in the entire plan. Operator MUST resolve them before executing the migration step.

---

## 3. DB Backup Procedure

### 3.1 DB engine + identity

- **Engine:** PostgreSQL 16, running in Docker container `guinevere-postgres` (image `guinevere-postgres-pgvector:16`).
- **Host port mapping:** `127.0.0.1:5433` (host) → `5432` (container).
- **DB name:** `guinevere`
- **Roles used by the app:** `guinevere_core` (read+write app role), `guinevere` (DB superuser used by `pg_dumpall` in the canonical backup script).
- **DB size:** 5,584 MB (`pg_database_size` of `guinevere`).
- **Constraint:** `guinevere_core` role does **NOT** have `LOCK` permission on most schemas (verified — `pg_dump` as `guinevere_core` fails immediately on `LOCK TABLE ... IN ACCESS SHARE MODE` for `audit.audit_trail`, `health.*`, `persona.*`, `memory.*`, `surveillance.*`, etc.). The canonical backup role is **`guinevere`**.

### 3.2 Backup command (exact)

```bash
# Run on VPS as user guinevere
# Step 1: pre-flight
mkdir -p /home/guinevere/data/backups
TS=$(date -u +%Y%m%dT%H%M%SZ)
DUMP=/home/guinevere/data/backups/guinevere-p22-predeploy-${TS}.sql.gz

# Step 2: pg_dumpall via container (role 'guinevere' is a DB superuser)
#   This is the EXACT pattern from scripts/guinevere-backup-docker.sh
docker exec guinevere-postgres pg_dumpall -U guinevere \
  --schema-only=false \
  --no-role-passwords \
  2>/tmp/guinevere-p22-predeploy-${TS}.pgerr \
| gzip -9 > "$DUMP"

# Step 3: size sanity (must be > 1 GB; a healthy gzip dump of a 5.6 GB DB
#         is roughly 1.5-2.5 GB. Reference: a recent raw dump observed is
#         ~37 GB SQL → ~10-12 GB gzipped.)
SIZE=$(stat -c%s "$DUMP" 2>/dev/null || echo 0)
if [ "$SIZE" -lt 1000000000 ]; then
  echo "BACKUP TOO SMALL ($SIZE bytes) — ABORT DEPLOY" | tee -a /tmp/guinevere-p22-predeploy-${TS}.pgerr
  exit 1
fi

# Step 4: record in ops.backup_log (operator can do this manually after deploy
#         with proper credentials; the deploy script does NOT need it to be
#         atomic with the dump itself)
sha256sum "$DUMP" > "${DUMP}.sha256"
echo "Backup written: $DUMP ($SIZE bytes)"
```

> **Why `pg_dumpall` and not `pg_dump`?**
> `pg_dumpall` is the canonical pattern in `scripts/guinevere-backup-docker.sh` and
> it preserves **roles, tablespaces, and grants** in addition to schema/data.
> For a pre-deploy snapshot, role information is exactly what you want preserved
> in case of a destructive schema downgrade.

### 3.3 What if `docker exec` fails?

`docker exec guinevere-postgres pg_dumpall -U guinevere` was observed working
on this audit run (returned valid SQL with `SET default_transaction_read_only = off`,
`SET client_encoding = 'UTF8'`, etc.). If it fails:

- **Fallback A:** `docker exec -u postgres guinevere-postgres pg_dumpall -U postgres` (the container's superuser). Requires container to have `postgres` Unix user (it does — `postgres:16-alpine` parent image).
- **Fallback B:** Use a per-schema `pg_dump` as `guinevere_core` (no LOCK) for schemas you have permission on (`ops`, `extensions`). This is a **partial** backup — not recommended as the primary.

### 3.4 Code-side backup (no secrets)

```bash
# Mirror the project tree, EXCLUDING .env files and venv (saves ~500 MB of pyc).
# Use the .hermes, evidence, data, logs volumes separately — they're outside the
# repo tree.
TS=$(date -u +%Y%m%dT%H%M%SZ)
sudo -n cp -a /home/guinevere/code/guinevere \
        /home/guinevere/data/backups/guinevere-code-bak-${TS}
# Remove .env files from the snapshot (they have secrets); do NOT keep them in backup.
find /home/guinevere/data/backups/guinevere-code-bak-${TS} -name ".env*" -delete
# Strip the venv to keep size manageable.
rm -rf /home/guinevere/data/backups/guinevere-code-bak-${TS}/.venv
# Echo the path.
echo "Code snapshot: /home/guinevere/data/backups/guinevere-code-bak-${TS}"
```

> **Note:** `cp -a` requires read access to all files. Some `.env*` files are `chmod 600`
> owned by `guinevere` — `cp -a` as `guinevere` will succeed; if escalated to root,
> secrets will be captured (operator should keep secrets out of any backup that
> leaves the host). The `find ... -delete` step enforces this regardless.

---

## 4. Code Deploy Procedure

### 4.1 Method: `git pull` (preferred)

The VPS tracks the same GitHub repo as the local workspace. Git pull is the
**cleanest** deploy — it is atomic, leaves `.env` files untouched, and the
operator can review the diff with `git status` after.

**CAUTION: working tree is dirty** (see §1). The dirty files are
documentation and bug-fix files (`alembic/env.py`, `src/core/main.py`,
`src/discord/_*.py`, etc.) that are NOT related to P22. There are two paths:

**Path A (preferred): commit the dirty files locally and push, then `git pull` on VPS.**

```bash
# On LOCAL machine, in repo root C:/Users/faizz/guinevere
cd C:/Users/faizz/guinevere
git add -A
git commit -m "deploy(p22): pre-deploy snapshot $(date -Iseconds) — preserves P22 staging"
git push origin main
```

**Path B: stash the dirty files on VPS, then `git pull` (lose the dirty edits, but the VPS working tree returns to origin).**

```bash
# On VPS
cd /home/guinevere/code/guinevere
git status -s | head     # review what's dirty
git stash push -u -m "p22-predeploy-stash-$(date +%s)" -- \
    $(git status -s | awk '{print $2}' | grep -v '^\(src/life_integrations\|alembic/versions/p22\|alembic/versions/p19_003\)' )
# Note: the filter excludes P22 files from the stash so the P22 work is preserved.
git pull --ff-only origin main
```

> Operator MUST verify after `git pull` that the only NEW files are:
> - `src/life_integrations/__init__.py` + 14 modules
> - `src/life_integrations/adapters/`
> - `alembic/versions/p22_001_integration_schema.py`
> - and that `alembic/versions/p19_003_audit_chain_version.py` is present (it is already referenced in the DB).

### 4.2 Method: `rsync` (alternative, narrower)

If `git pull` is too disruptive, transfer **only the changed/new files** from
local to VPS via `rsync` (preserves perms, runs over SSH, no `.env` required):

```bash
# On LOCAL machine
rsync -avz --chmod=u+rw \
    --exclude='__pycache__' \
    C:/Users/faizz/guinevere/src/life_integrations/ \
    guinevere-vps:/home/guinevere/code/guinevere/src/life_integrations/

rsync -avz --chmod=u+rw \
    C:/Users/faizz/guinevere/alembic/versions/p22_001_integration_schema.py \
    guinevere-vps:/home/guinevere/code/guinevere/alembic/versions/

# Also transfer p19_003 if missing on VPS
rsync -avz --chmod=u+rw \
    C:/Users/faizz/guinevere/alembic/versions/p19_003_audit_chain_version.py \
    guinevere-vps:/home/guinevere/code/guinevere/alembic/versions/
```

> Verify post-rsync:
> `ssh guinevere-vps 'ls /home/guinevere/code/guinevere/src/life_integrations | wc -l'` → must be `15` (14 modules + `adapters/`).
> `ssh guinevere-vps 'ls /home/guinevere/code/guinevere/alembic/versions/p22_001_integration_schema.py'` → must exist.

### 4.3 No startup wiring change required (verified)

`grep -n "life_integrations" src/core/main.py` on the local repo returns **no matches**.
The P22 deploy is library + migration only. The new modules will not be **imported**
by `guinevere-core` until a follow-up wiring change is made (which is out of scope
for this deploy). This is good — it means the restart is a no-op from the application
standpoint if the migration is the only thing that needs to apply.

---

## 5. Migration Apply Procedure

### 5.1 The migration chain (verified by reading files)

```
p19_001_project_namespaces  (p19_001, p19_002 already on VPS schema)
   ↓
p19_002_project_id_not_null
   ↓
p19_003_audit_chain_version  (adds audit.audit_trail.chain_version column)
   ↓
p22_001_integration_schema   (creates audit.integration_api_log + p22.integration_registry)
```

`p22_001_integration_schema` `down_revision = "p19_003_audit_chain_version"`.

**On the VPS, `ops.alembic_version` already contains all four of these** (verified
on this audit). This means the **schema is already applied** — `alembic upgrade head`
should be a no-op for these four revisions. The only effect of running the P22
deploy migration step is to make the file presence in `alembic/versions/` match
the DB, so that future `alembic` commands work cleanly.

### 5.2 The DB password problem (mitigation)

`alembic` reads `sqlalchemy.url` from `alembic.ini` and substitutes the password
from `GUINEVERE_DB_PASSWORD` env var. The password in `.env.core` does NOT work
for `alembic` (the running service must use a different DSN or different auth
method, e.g. trust auth or a different password set in a parent config). Until
this is reconciled, `alembic upgrade head` will fail.

**Mitigation A (preferred): use the working auth path.**

```bash
# On VPS, find what the running service is using
ssh guinevere-vps 'sudo systemctl show guinevere-core -p Environment -p EnvironmentFiles 2>/dev/null'
# Look for GUINEVERE_DB_PASSWORD in the actual env. If absent, the service is
# using pg_hba.conf trust auth for 'guinevere_core' from localhost.

# If trust-auth is enabled, you can run alembic with no password
ssh guinevere-vps 'cd /home/guinevere/code/guinevere \
  && unset GUINEVERE_DB_PASSWORD \
  && unset DATABASE_URL \
  && .venv/bin/alembic upgrade head 2>&1 | tail -20'
```

**Mitigation B: confirm schema is already applied, skip `alembic upgrade head`.**

```bash
# If trust-auth fails or the migration is already applied, just stamp the
# alembic_version table to the new head so future alembic invocations are clean.
# The DB already has the four rows; this is a no-op verification.

ssh guinevere-vps 'cd /home/guinevere/code/guinevere \
  && .venv/bin/alembic current 2>&1 | tail -3'
# Expected: shows one of the four revision IDs.
```

**Mitigation C: use the existing `p19_003` row already in `alembic_version` as the
source of truth.** Since the table has 4 rows, the schema is in a "all heads applied"
state. The P22 migration is the only NEW file. If `alembic upgrade head` insists
on rewriting the version table, use `--sql` to dry-run first:

```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere \
  && .venv/bin/alembic upgrade head --sql 2>&1 | head -50'
# This produces SQL without executing. If the output is empty or only
# "statement_break", the schema is already at head.
```

### 5.3 What to do if the migration **fails** mid-way

- **Do NOT** continue to restart. Stay in the failed-migration state.
- `audit.integration_api_log` is a NEW table (no rows yet on VPS) — failing
  to create it leaves NO data loss.
- `audit.audit_trail.chain_version` column was added by p19_003 — if
  p19_003 re-runs and fails partway, the column may exist with a partial
  backfill. `alembic stamp p19_002_project_id_not_null` will revert the
  version pointer; this is **safe** because the column data is still there.
- The `alembic_version` table is multi-headed with 4 rows; an additional
  failed run will likely add a 5th row pointing to p22_001. This is also
  benign (the schema will already exist or partially exist).

> **Operator must collect the alembic stderr before deciding rollback.**

---

## 6. Restart Procedure (guinevere-core ONLY)

```bash
# On VPS, as user guinevere (use guinevere-root only for sudo, never root directly)
ssh guinevere-vps 'sudo systemctl restart guinevere-core'

# Wait for the unit to settle (RestartSec=10, plus uvicorn worker boot)
sleep 15

# Confirm the unit is up
ssh guinevere-vps 'systemctl is-active guinevere-core'
# Expected: "active"

# Confirm the application is serving
ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/health'
# Expected: {"status":"active",...}

ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/health/detailed'
# Expected: 9router, redis, postgresql all "ok"
```

**Service-impact isolation:**

`guinevere-core` restart takes ~5-15s. Other services are **not** affected
because they do not depend on `guinevere-core.service` (verified — none of the
other 10 services have `Requires=` or `After=guinevere-core.service` in their
unit files).

---

## 7. Other-Services Do-Not-Touch List (verified)

| Service | DO NOT | Why |
|---|---|---|
| `guinevere-9router.service` | Restart, stop, reload | LLM proxy on `:20128`; core depends on it (`Requires=guinevere-9router.service`) — restart would block core from starting. |
| `9router-proxy.service` | Restart, stop, reload | Tailscale sidecar at `127.0.0.1:20128 -> Tailscale:20130`. |
| `cloudflared.service` | Restart, stop, reload | Discord webhook tunnel — independent of P22. |
| `guinevere-discord.service` | Restart, stop, reload | P22 has no Discord wiring change. |
| `guinevere-mcp.service` | Restart, stop, reload | MCP gateway independent. |
| `guinevere-monitoring.service` | Restart, stop, reload | Prom/Grafana/Loki/Alertmanager. |
| `guinevere-obscura.service` | Restart, stop, reload | CDP server. |
| `guinevere-whatsapp.service` | Restart, stop, reload | WhatsApp channel. |
| `guinevere-x-poster.service` | Restart, stop, reload | X/Twitter poster. |
| `docker.service` | Restart, stop | PG container + 9Router container depend on it. |
| `guinevere-postgres` (docker) | Stop, restart, drop, migrate outside alembic | The container is the actual DB. |
| Tailscale / `tailscaled` | Restart, reauth | Out of deploy scope. |
| UFW / `ufw` | Disable, modify | Out of deploy scope. |
| Any P26 / P23 / P19 systemd units | Restart, stop, reload | Out of P22 scope. |

**Verification after restart:**

```bash
ssh guinevere-vps 'for s in guinevere-9router 9router-proxy cloudflared \
  guinevere-discord guinevere-mcp guinevere-monitoring guinevere-obscura \
  guinevere-whatsapp guinevere-x-poster docker tailscaled; do
  echo "$s: $(systemctl is-active $s 2>/dev/null || echo "n/a")"
done'
# Expected: every line ends in "active" (or "n/a" for tailscaled if not present).
```

---

## 8. Rollback Procedure

### 8.1 Code rollback

```bash
# On VPS, restore the code snapshot
ssh guinevere-vps 'cd /home/guinevere && \
  rm -rf /home/guinevere/code/guinevere.failed-p22 && \
  mv /home/guinevere/code/guinevere /home/guinevere/code/guinevere.failed-p22 && \
  cp -a /home/guinevere/data/backups/guinevere-code-bak-<TS> /home/guinevere/code/guinevere && \
  chown -R guinevere:guinevere /home/guinevere/code/guinevere'
# (Replace <TS> with the timestamp from §3.4.)
```

> Alternative: `git checkout HEAD~1 -- src/life_integrations alembic/versions/p22_001_integration_schema.py` if the prior commit is acceptable.

### 8.2 Migration rollback — **WORM AUDIT TABLE CAVEAT**

The P22 migration creates **one new table** (`audit.integration_api_log`) and
**modifies NO existing tables** (other than via p19_003, which adds the
`chain_version` column to `audit.audit_trail`).

| Table | Created/modified by | Downgrade drops | Data loss if downgraded after rows exist? |
|---|---|---|---|
| `audit.integration_api_log` | p22_001 (NEW) | `DROP TABLE audit.integration_api_log` | YES — all P22 audit rows. **WORM hash-chain will be broken for those rows anyway** because they were hash-chained to other rows; on DROP, the chain is severed. |
| `p22.integration_registry` | p22_001 (NEW) | `DROP TABLE p22.integration_registry` | YES — all P22 integration metadata. |
| `audit.audit_trail.chain_version` column | p19_003 | `ALTER TABLE audit.audit_trail DROP COLUMN chain_version` | YES — column values lost; existing hash chain re-validates only if recomputed. **Inherits existing rows' hash**. |
| `audit.audit_trail.project_id` column | p19_002 | `ALTER TABLE audit.audit_trail DROP COLUMN project_id` | YES — column values lost. **p19_002 downgrade explicitly warns: "base rows are preserved, but project_id partitioning data is lost on downgrade (columns dropped). Use only in test/rollback."** |

### 8.3 The hard rule

> **If the migration has been applied and audit tables contain data, do NOT
> downgrade the audit tables. Roll back the CODE only and investigate.**

**Why:**

- The P22 audit log is **WORM** (Write-Once-Read-Many, hash-chained).
- Once `audit.integration_api_log` has rows, dropping it destroys the chain.
- Even if `audit.integration_api_log` is empty, the table's existence
  may be referenced by `audit_writer` and other app code that has been
  wired to it (in subsequent deploys).
- `audit.audit_trail` rows with `chain_version=2` reference the column
  in their hash input. Dropping the column breaks re-validation.

**Recommended rollback sequence when migration has been applied:**

```bash
# 1. Restore code (see §8.1)
# 2. Leave schema AS-IS — do NOT run alembic downgrade
# 3. Restart guinevere-core
ssh guinevere-vps 'sudo systemctl restart guinevere-core'
sleep 15
# 4. Verify with smoke (§9)
# 5. Document the schema state in the rollback evidence:
#    "p22_001_integration_schema applied at <TS>; rows in
#     audit.integration_api_log: <N>; p22.integration_registry rows: <N>;
#     code rolled back; schema retained by operator decision per WORM policy."
```

**Only consider `alembic downgrade p19_002_project_id_not_null`** (which
removes p19_003 + p22_001 in one shot) **if** both of the following hold:
- `audit.integration_api_log` is empty.
- `p22.integration_registry` is empty.
- `audit.audit_trail.chain_version` rows have no downstream verifier
  that requires the column (the local `AuditWriter` does; if running
  service imports `audit_writer`, do NOT drop the column).

Even then, **prefer to leave the schema and roll back the code only.**

### 8.4 If the migration FAILED before fully applying

The P22 migration uses `CREATE TABLE IF NOT EXISTS` and `CREATE INDEX IF NOT EXISTS` — it is **idempotent**. A partial application is recoverable by re-running `alembic upgrade head` after fixing the auth issue, or by `alembic stamp p19_003_audit_chain_version` followed by a fresh `alembic upgrade head` to re-run only p22_001.

---

## 9. Post-Deploy Smoke Gate (must pass before "done")

After `systemctl restart guinevere-core` and `sleep 15`, run **all of the following**:

```bash
# G1. Service is up
ssh guinevere-vps 'systemctl is-active guinevere-core'                     # active
ssh guinevere-vps 'systemctl is-active guinevere-9router'                  # active (untouched)
ssh guinevere-vps 'systemctl is-active guinevere-discord'                  # active (untouched)

# G2. HTTP health
ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/health | head -c 200'
# Expected: {"message":"Guinevere de Baroque is online.","status":"active"}

ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/health/detailed | head -c 600'
# Expected: postgresql:ok, redis:ok, 9router:ok, loop_manager:ok, guardian:ok

ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/status | head -c 400'
# Expected: services[].healthy=true for redis, postgresql, 9router

# G3. P20 heartbeat still alive (loop / life_kernel evidence)
ssh guinevere-vps 'curl -fsS http://127.0.0.1:8000/api/v1/loops | head -c 200'
# Expected: {"loops":...} JSON, 200 OK

# G4. No traceback in 2 minutes of journal
ssh guinevere-vps 'sudo journalctl -u guinevere-core --since "2 minutes ago" --no-pager | grep -iE "traceback|exception|error" | head -20'
# Expected: empty, or only "expected" warnings (e.g. hermes_brain_init_failed is OK
#            if P20 brain is intentionally not wired)

# G5. Other services undisturbed (sanity recheck)
ssh guinevere-vps 'for s in guinevere-9router 9router-proxy guinevere-discord guinevere-mcp guinevere-monitoring guinevere-obscura guinevere-whatsapp guinevere-x-poster cloudflared docker; do
  s_active=$(systemctl is-active $s 2>/dev/null)
  echo "$s: $s_active"
  if [ "$s_active" != "active" ]; then echo "FAIL: $s not active"; fi
done'
# Expected: every line "active" and zero "FAIL" lines

# G6. P22 library is importable from the venv (new check)
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "
import importlib
for m in [\"src.life_integrations\", \"src.life_integrations.router\", \"src.life_integrations.consent\", \"src.life_integrations.audit\", \"src.life_integrations.registry\", \"src.life_integrations.wiring\", \"src.life_integrations.scheduler\", \"src.life_integrations.project_context\", \"src.life_integrations.permissions\", \"src.life_integrations.secrets\", \"src.life_integrations.types\", \"src.life_integrations.errors\", \"src.life_integrations.base\"]:
    importlib.import_module(m)
    print(f\"OK: {m}\")
"'
# Expected: 13 "OK: ..." lines, no ImportError

# G7. DB connectivity after restart (audit_writer / future P22 wiring)
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "
import asyncio, asyncpg, os
async def main():
    conn = await asyncpg.connect(
        host=\"localhost\", port=5433, user=\"guinevere_core\",
        password=os.environ.get(\"GUINEVERE_DB_PASSWORD\", \"\"),
        database=\"guinevere\"
    )
    rows = await conn.fetch(\"SELECT current_database(), current_user\")
    print(rows)
    await conn.close()
asyncio.run(main())
" 2>&1 | tail -3'
# Expected: [{'guinevere', 'guinevere_core'}] (auth working) OR ImportError auth diagnosis
```

**Smoke gate decision:**

- If **G1, G2, G5 pass** → deploy is "live and healthy" at the integration level.
- If **G3 fails** → P20 loop is broken; rollback immediately (§8.1 + §8.3, code only).
- If **G4 shows tracebacks** → investigate; rollback if P22 module load is implicated.
- If **G6 fails** (P22 import errors) → `src/life_integrations/` was not transferred correctly. Re-do §4.1/§4.2. Rollback may be needed.
- If **G7 fails** → the DB password in `.env.core` is still stale. Roll back the .env (you did back up `cp -a` BEFORE the deploy? — no, the deploy plan does NOT touch `.env.core`; this is a pre-existing condition).

---

## 10. Operator-Gated Steps

These steps require operator action or a credential that the deploy script
cannot perform alone:

| Step | Why gated | Mitigation |
|---|---|---|
| `docker exec guinevere-postgres pg_dumpall -U guinevere` | Requires `guinevere` to be in the `docker` group (verified: yes — `id guinevere` shows `988(docker)`). No sudo needed. | Run as `guinevere`. |
| `sudo systemctl restart guinevere-core` | Requires NOPASSWD sudo (verified: `guinevere` has `(ALL) NOPASSWD: ALL`). | Run as `guinevere`. |
| `cp -a` of `.env*` files | These are `chmod 600` and contain secrets. | Done by `guinevere` (owner). For the snapshot, `find ... -delete .env*` strips them. |
| `alembic upgrade head` | Requires working DB password. The current password in `.env.core` does NOT authenticate via asyncpg (verified). | Operator must reconcile the DB password before this step. See §5.2 Mitigation A/B/C. |
| Reading `.env.core` | File is `chmod 600` and contains live secrets. | `sudo -n cat` is acceptable, but values MUST be redacted in any evidence file. |
| `git pull` on VPS with dirty tree | Dirty files must be either committed (local) or stashed (VPS). | Operator decision. |
| Destructive operations: `rm -rf`, `DROP TABLE`, `alembic downgrade base` | BLOCKED by AGENTS.md §0.1 — never run without explicit per-action operator approval. | Rollback in §8 uses `mv`, not `rm`. |

---

## 11. Risks

| # | Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|---|
| R1 | `.env.core` `DATABASE_URL` password is stale (verified during this audit) | **Confirmed** | Alembic cannot apply migration; service was already running with a different DSN/password source | §5.2 Mitigation A/B/C. Do not skip. |
| R2 | `ops.alembic_version` has 4 rows (multi-head state) | **Confirmed** | `alembic upgrade head` may error or rewrite the table | §5.2 Mitigation B: use `alembic current` and `alembic upgrade head --sql` to dry-run. |
| R3 | VPS working tree is dirty (10+ modified files unrelated to P22) | **Confirmed** | `git pull` will fail or merge unexpected changes | Use Path A (commit + push) or Path B (stash + filter). Document what is stashed. |
| R4 | P22 migration creates `audit.integration_api_log` WORM table; if rollback drops it, audit chain is severed | Medium | Loss of audit trail; integrity check will fail | §8.3 hard rule: do NOT downgrade audit tables. |
| R5 | `guinevere-core` requires `guinevere-9router.service` (unit `Requires=`) | Low | If 9Router restarts for any reason during deploy, `guinevere-core` will fail to start | Verify 9Router is up BEFORE the restart. |
| R6 | `pg_dumpall` returns 37 GB raw / ~10-12 GB gzipped; 39 GB free disk | Low | Disk could fill up if other writes happen concurrently | Confirm `df -h /` BEFORE the dump; abort if < 15 GB free. |
| R7 | `src/life_integrations/` library is added but `src/core/main.py` does NOT import it (verified) | **Confirmed** | Restart is a no-op from the application standpoint — the new code is loaded by Python, but no route uses it | Smoke G6 confirms imports work. The P22 wiring is a separate follow-up deploy. |
| R8 | `alembic.ini` has `sqlalchemy.url = postgresql+asyncpg://guinevere_core:****@localhost:5433/guinevere` (the `****` is a literal placeholder, replaced by `GUINEVERE_DB_PASSWORD` env var) | Low | Confusing for ops reading the file | Document in evidence that `****` is intentional. |
| R9 | `guinevere-core` runs as `User=guinevere`; if operator does `sudo -i` to `root` and runs `systemctl restart`, the unit's `User=guinevere` is preserved but env may differ | Low | Could miss `EnvironmentFile` if shell does not re-load | Always run via `ssh guinevere-vps '...'` (not `ssh -t guinevere-vps -i`). |
| R10 | `cp -a` of `/home/guinevere/code/guinevere` includes `.venv/` (heavy, ~500 MB) | Low | Backup slow | The §3.4 procedure removes `.venv/` after copy. |
| R11 | The DB contains data in `audit.audit_trail` with `chain_version=2` (post-p19_003) | **Confirmed (column exists, but row count of chain_version=2 unverified)** | Dropping the column would invalidate any verifier that requires it | §8.3: do not drop audit tables. |
| R12 | `DISCORD_BOT_TOKEN` and `GUINEVERE_9ROUTER_API_KEY` are present in `.env.core` | **Confirmed (file exists; values redacted)** | Echoing the file in evidence would leak secrets | Never `cat .env.core` in evidence. Use `grep ... | sed 's/=.*$/=REDACTED/'` if summary is needed. |
| R13 | `pg_dumpall` captures the running `guinevere_core` role's grants and password | **Confirmed** | Backup file contains a role password | Backup is stored in `/home/guinevere/data/backups/` (only `guinevere` readable) and is NOT offloaded to a public place. If offloaded, encrypt. |
| R14 | `restart guinevere-core` triggers 2-worker uvicorn reload; 5-15s of HTTP 502/connection-refused | Low | Brief HTTP gap; not a service outage | Run smoke gate AFTER the gap closes. |
| R15 | `9router` config in `secrets/.env.9router` (separate from `.env.core`) | Medium | Re-deploy could re-trigger P20 soak if not careful | Do NOT touch `secrets/.env.9router`. |

---

## 12. Sequencing — Single-Operator Runbook (TL;DR)

```
Pre-flight (read-only):
  [ ] §1 — verify paths and unit (this document)
  [ ] §1 — verify `ops.alembic_version` has 4 rows (p19_001, p19_002, p19_003, p20_001)
  [ ] §2 — confirm GUINEVERE_DB_PASSWORD works for `alembic current`; if not, §5.2 Mit A/B/C
  [ ] §11 R6 — confirm `df -h /` shows >= 15 GB free
  [ ] §11 R3 — decide Path A (commit+push) or Path B (stash+filter) for the dirty tree
  [ ] §11 R5 — confirm 9Router is active (it is)

Step A — Backup (write):
  [ ] §3.2 — docker exec guinevere-postgres pg_dumpall -U guinevere | gzip -9
  [ ] §3.4 — cp -a code snapshot (no .env, no .venv)

Step B — Code deploy:
  [ ] §4.1 — git pull (Path A or B)
  [ ] §4.2 (alt) — rsync src/life_integrations/ + p22_001_integration_schema.py + p19_003_audit_chain_version.py

Step C — Migration (gated):
  [ ] §5.2 — alembic upgrade head --sql (dry-run)
  [ ] §5.2 — alembic upgrade head (real)
  [ ] If fails, do NOT restart; collect stderr; see §5.3

Step D — Restart (single service):
  [ ] §6 — sudo systemctl restart guinevere-core
  [ ] sleep 15

Step E — Verify (do-not-touch list):
  [ ] §7 — all other services still active
  [ ] §9 G1-G7 — smoke gate

If smoke gate fails:
  [ ] §8.1 — restore code snapshot
  [ ] §8.3 — DO NOT downgrade audit tables; restart; re-smoke
  [ ] Document schema state in evidence; investigate before next attempt
```

---

## 13. Verdict

**DEPLOY IS FEASIBLE but BLOCKED on two confirmed pre-deploy findings** that
require operator action before the migration step:

1. **R1**: `.env.core` `DATABASE_URL` password is stale. `alembic` will fail
   to authenticate until this is reconciled.
2. **R3**: VPS working tree is dirty. `git pull` will fail or merge
   unrelated changes. Path A (commit+push) or Path B (stash+filter)
   must be chosen by the operator.

The deploy itself (backup → code deploy → migration → restart → smoke) is
otherwise low-risk because:

- The P22 deployment adds a library with no startup wiring change in
  `src/core/main.py` (verified).
- The P22 migration is idempotent (`CREATE TABLE IF NOT EXISTS`).
- The P22 migration creates a NEW audit table; it does not modify
  existing audit tables, so a code-only rollback is safe.
- The only service that restarts is `guinevere-core`. No other service
  has `Requires=guinevere-core.service`, so they remain undisturbed.
- 9Router (`guinevere-9router.service` + `9router-proxy.service`) and
  P26 are explicitly excluded from the do-not-touch list and from the
  deploy scope.

If R1 and R3 are resolved before the deploy, the plan in §12 can be
executed by a single operator in under 30 minutes (dominated by the
~10 GB pg_dump gzip).

---

*End of strategy document. Operator must execute; this auditor did not.*
