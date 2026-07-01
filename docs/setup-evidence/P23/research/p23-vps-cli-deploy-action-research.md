# P23 Research — VPS/SSH/CLI/Deploy Action (Backup→Canary→Smoke→Rollback)

> Status: RESEARCH. Date: 2026-06-25.

---

## 1. Objective

Define the P23 "Embodied Operations / Personal OS Action Layer" executor for VPS/SSH/CLI/deploy actions. This research grounds the design in existing Guinevere infrastructure (systemd services, backup scripts, deploy patterns) and official tooling documentation, then maps the exact L3 deploy gate (backup → canary → smoke → promote/rollback), isolation from co-hosted Aizanta, and failure/self-debug/rollback behavior required by AGENTS.md §0.1.

Key questions answered:
- What is the existing deploy/ops surface (services, scripts, backup/restore tooling)?
- What are the safe VPS action primitives and their official semantics?
- How is the L3 deploy gate sequenced end-to-end?
- How do we prove Aizanta is never touched?
- What is the failure/rollback/self-debug loop for deploy actions?
- What must the planner know before implementation?

---

## 2. Sources Consulted

### 2.1 Local Ground Truth

| Source | Path | Relevant Lines | Authority Topic |
|---|---|---|---|
| AGENTS.md §0.1 | `AGENTS.md` | 57-91 | P20 autonomy exception; engineering deployment gate = backup→canary→smoke→rollback |
| AGENTS.md §2.11 | `AGENTS.md` | 226-228 | Idempotency / re-run-safe or one-shot documented |
| IMPLEMENTATION_GUIDE §6 | `docs/IMPLEMENTATION_GUIDE.md` | 592-637 | Shared VPS isolation matrix; Aizanta never touched; cgroup limits |
| ADR-014 | `adr/ADR-014-vps-container-architecture.md` | 1-122 | Single primary VPS, Ubuntu 24.04, systemd + selective containers |
| ADR-016 | `adr/ADR-016-cicd-autonomous-deployment-strategy.md` | 1-141 | Autonomous preparation + governed deployment gates; self-deploy via cron + git pull |
| ADR-025 | `adr/ADR-025-backup-disaster-recovery-strategy.md` | 1-131 | Backup/DR policy with restore validation |
| ADR-032 | `adr/ADR-032-backup-storage-strategy.md` | 1-225 | idcloudhost S3 primary + Cloudflare R2 secondary; rclone remotes |
| ADR-035 | `adr/ADR-035-hermes-migration.md` | 1-2516 | Sentinel `/home/guinevere/.backup/last-success` (B11) |
| Backup script | `scripts/guinevere-backup.sh` | 1-615 | pg_dumpall → gzip → restic → S3 + R2; sentinel file |
| Backup timers | `scripts/guinevere-backup@.timer`, `guinevere-backup@.service` | — | systemd timer-based backup scheduling |
| systemd units | `systemd/guinevere-*.service` | — | Service definitions, cgroups, slice=guinevere.slice |
| Deploy backend | `src/life_kernel/domain_minds/deploy_backend.py` | 1-354 | `SSHDeployBackend` dry-run/reference impl; systemctl/ssh/scp patterns |
| Sibling research | `docs/setup-evidence/P23/research/p23-rollback-idempotency-research.md` | 1-745 | L3 deploy gate sequence, rollback payload, durable queue, audit |
| Sibling research | `docs/setup-evidence/P23/research/p23-policy-gate-risk-classification-research.md` | 1-335 | L1-L4 risk tiers, consent scopes, self-debug loop |
| P20 deploy inventory | `research-reports/p20-production-deploy-inventory.md` | — | Existing production deploy/service inventory |

### 2.2 Official Docs Consulted (Retrieved 2026-06-25)

| Tool | Topic | URL | Retrieval |
|---|---|---|---|
| systemd | `systemctl` — start/stop/restart/enable/status | https://www.freedesktop.org/software/systemd/man/latest/systemctl.html | 2026-06-25 |
| systemd | `journalctl` — query logs | https://www.freedesktop.org/software/systemd/man/latest/journalctl.html | 2026-06-25 |
| PostgreSQL | `pg_dump` — logical backups | https://www.postgresql.org/docs/current/app-pgdump.html | 2026-06-25 |
| PostgreSQL | `pg_restore` — restore logical backups | https://www.postgresql.org/docs/current/app-pgrestore.html | 2026-06-25 |
| PostgreSQL | `pg_dumpall` — cluster-wide dumps | https://www.postgresql.org/docs/current/app-pg-dumpall.html | 2026-06-25 |
| OpenSSH | `ssh` — remote shell | https://man.openbsd.org/ssh | 2026-06-25 |
| OpenSSH | `scp` — secure copy | https://man.openbsd.org/scp | 2026-06-25 |
| rclone | `rclone copyto/copy/sync/check` — S3/R2 transfers | https://rclone.org/commands/ | 2026-06-25 |
| rclone | S3 provider config (idcloudhost / R2) | https://rclone.org/s3/ | 2026-06-25 |
| AWS CLI | `aws s3 cp/sync` — S3 operations | https://awscli.amazonaws.com/v2/documentation/api/latest/ | 2026-06-25 |

---

## 3. Findings

### 3.1 Existing Infra Map

#### 3.1.1 systemd Services (Guinevere)

All production services live in `systemd/` and share `Slice=guinevere.slice`. Current units include:

| Unit | Type | User | Resource Caps | Purpose |
|---|---|---|---|---|
| `guinevere-core.service` | exec | guinevere | MemoryMax=2G, CPUQuota=200% | Core FastAPI / life_kernel entrypoint |
| `guinevere-discord.service` | exec | guinevere | MemoryMax=1G, CPUQuota=100% | Discord bot |
| `guinevere-loops.service` | exec | guinevere | MemoryMax=2G, CPUQuota=200% | Agent loop daemon |
| `guinevere-scheduler.service` | exec | guinevere | — | Ritual/scheduler tasks |
| `guinevere-mcp.service` | exec | guinevere | — | MCP server |
| `guinevere-monitoring.service` | exec | guinevere | — | Prometheus/Grafana probes |
| `guinevere-surveillance.service` | exec | guinevere | — | Surveillance pipeline |
| `guinevere-obscura.service` | exec | guinevere | — | Browser automation |
| `guinevere-shadow-monitor.service` | timer/service | guinevere | — | Shadow-mode checks |
| `guinevere-wearable-analysis.service` | timer/service | guinevere | — | Wearable health analysis |
| `guinevere-wearable-sync.service` | timer/service | guinevere | — | Wearable sync |

Common security hardening seen in these units: `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only`, explicit `ReadWritePaths`, `Slice=guinevere.slice`. This is the surface that P23 VPS actions operate on.

#### 3.1.2 Deploy / Ops Scripts

| Script | Path | Role |
|---|---|---|
| `guinevere-backup.sh` | `scripts/guinevere-backup.sh` | Production dual-target restic backup (pg_dumpall + file snapshot → idcloudhost S3 + R2) |
| `setup-restic.sh` | `scripts/setup-restic.sh` | Documentation-style restic/SOPS setup guide |
| `preflight-check.sh` | `scripts/preflight-check.sh` | Read-only preflight: services, DB, Redis, security, Aizanta, backup |
| `health-check-p1.sh` | `scripts/health-check-p1.sh` | Smoke tests for core / 9Router / Postgres / Redis |
| `vps_db_check.sh` | `scripts/vps_db_check.sh` | Guinevere DB tables/extensions + Redis DB0-5 sizes |
| `run-discord-verify.sh` | `scripts/run-discord-verify.sh` | Decrypt SOPS + run Discord verification scripts |
| `startup_gate.py` / `startup_gate_test.py` | `scripts/` | Service startup gate logic |

#### 3.1.3 Backup/Restore Tooling

| Tool | Use in Repo | Notes |
|---|---|---|
| `pg_dumpall` | `guinevere-backup.sh` | Full cluster dump; used because Aizanta may share the PostgreSQL instance |
| `restic` | `guinevere-backup.sh`, `setup-restic.sh` | Primary backup tool to idcloudhost S3 + R2; `sops exec-env` for secrets |
| `rclone` | ADR-032 | Documented for S3/R2 copy/sync; not yet the primary backup script |
| `aws-cli` | Not currently in scripts | Could be used as an alternative to rclone for S3 operations |
| Sentinel file | `/home/guinevere/.backup/last-success` | ADR-035 B11 — verified marker of last successful backup/rollback target |

### 3.2 VPS Action Primitive Table

| Primitive | Example Command | Risk Tier | Safety Rule | Official Reference |
|---|---|---|---|---|
| `systemctl status <svc>` | `systemctl status guinevere-core.service` | L1 (read/idempotent) | Allowed autonomously; never alters state | systemd systemctl docs |
| `systemctl is-active <svc>` | `systemctl is-active --quiet guinevere-core.service` | L1 | Health probe; safe | systemd systemctl docs |
| `systemctl start <svc>` | `systemctl start guinevere-core.service` | L2/L3 | L2 if non-critical; L3 if production core | systemd systemctl docs |
| `systemctl stop <svc>` | `systemctl stop guinevere-core.service` | L2/L3 | L3 for core services; require backup gate | systemd systemctl docs |
| `systemctl restart <svc>` | `systemctl restart guinevere-core.service` | L3 | Full deploy gate required | systemd systemctl docs |
| `systemctl enable <svc>` | `systemctl enable guinevere-core.service` | L2 | Notify after; persistence change | systemd systemctl docs |
| `systemctl disable <svc>` | `systemctl disable guinevere-core.service` | L3 | Full gate; can brick service | systemd systemctl docs |
| `systemctl revert <svc>` | `systemctl revert guinevere-core.service` | L3 | Rollback primitive; revert unit overrides | systemd systemctl docs |
| `systemctl daemon-reload` | `systemctl daemon-reload` | L2/L3 | L3 when changing unit files | systemd systemctl docs |
| `journalctl -u <svc>` | `journalctl -u guinevere-core.service -n 50` | L1 | Read-only debug | systemd journalctl docs |
| `ssh <host> <cmd>` | `ssh guinevere@localhost systemctl status guinevere-core` | L1/L2/L3 | Read=L1; write=L2/L3; only guinevere@localhost or Tailscale | OpenSSH ssh docs |
| `scp <src> <dst>` | `scp src/life_kernel/* guinevere@localhost:/opt/guinevere/src/...` | L2/L3 | Write/notify or deploy gate | OpenSSH scp docs |
| `pg_dump` | `pg_dump -U guinevere_core -d guinevere_core ...` | L1/L3 | Read backup; L3 if used for rollback restore prep | PostgreSQL pg_dump docs |
| `pg_dumpall` | `pg_dumpall -h 127.0.0.1 -p 5433 -U guinevere ...` | L1/L3 | Cluster dump; used by backup script | PostgreSQL pg_dumpall docs |
| `pg_restore` | `pg_restore -d guinevere_core /tmp/dump.gz` | L3 | Destructive restore; gate + approval | PostgreSQL pg_restore docs |
| `rclone copyto` | `rclone copyto file s3:bucket/path` | L2/L3 | Upload/download backup artifacts | rclone commands docs |
| `aws s3 cp` | `aws s3 cp file s3://bucket/path` | L2/L3 | Alternative to rclone for S3 | AWS CLI docs |
| `docker ps` / `docker logs` | `docker ps --filter name=guinevere` | L1 | Read-only container inspection | Docker docs |
| `docker restart <ct>` | `docker restart guinevere-postgres` | L2/L3 | L3 for stateful containers | Docker docs |
| `apt` (install/update/remove) | `apt install ...` | L3 only | Never autonomously run; Faiz approval required | apt docs |

### 3.3 L3 Deploy Gate Sequence

Per AGENTS.md §0.1 and the sibling P23 rollback/idempotency research, every L3 VPS/deploy action must follow:

```
┌─────────────────────────────────────────────────────────────────────────┐
│  L3 DEPLOY GATE (backup → canary → smoke → promote / rollback)         │
├─────────────────────────────────────────────────────────────────────────┤
│  1. BACKUP                                                               │
│     ├─ pg_dump guinevere_core → /tmp/deploy_{action_id}.sql.gz        │
│     ├─ tar -czf files_{action_id}.tar.gz /home/guinevere/code/guinevere │
│     ├─ restic backup OR rclone copyto to idcloudhost S3 + R2            │
│     ├─ verify backup (restic check / rclone check)                      │
│     └─ record backup_ref in rollback_payload                            │
│  2. CANARY                                                               │
│     ├─ deploy artifact to canary (separate port / temp service)        │
│     ├─ systemctl is-active guinevere-core@canary                        │
│  3. SMOKE                                                                │
│     ├─ curl -sf http://localhost:8001/health → 200                      │
│     ├─ psql -U guinevere_core -c "SELECT 1" → 1                         │
│     ├─ redis-cli -n 0 PING → PONG                                       │
│     ├─ pytest tests/ -v --tb=short (regression gate per ADR-029)       │
│     └─ verify Aizanta still healthy                                     │
│  4. PROMOTE or ROLLBACK                                                  │
│     ├─ PROMOTE: systemctl restart guinevere-core; update sentinel       │
│     └─ ROLLBACK: restore backup, systemctl revert, restart, verify      │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3.4 Isolation / Aizanta-Impact Proof

IMPLEMENTATION_GUIDE §6 is the binding rule. For every P23 VPS action the executor must assert:

```bash
# Before any destructive operation, prove Aizanta is untouched:
systemctl status aizanta-*        # no guinevere action touches these
redis-cli -n 10 PING              # never use DBs 10-15
psql -U aizanta -d aizanta -c "SELECT 1"   # never connect to aizanta DB
docker ps --filter "name=aizanta" # only inspect; do not modify
```

Rules encoded in the executor:
- Linux user must be `guinevere`; never `aizanta` or root.
- systemd operations only on `guinevere-*` services.
- Docker operations only on `guinevere-*` containers/networks (`guinevere-net` only).
- PostgreSQL only `guinevere*` databases/users; never `aizanta` DB/user.
- Redis only DBs 0-5; never DBs 10-15.
- Filesystem only under `/home/guinevere/`; never `/home/aizanta/`.
- SSH only to `guinevere@localhost` or Tailscale nodes; never to Aizanta hosts.

If any Aizanta-touch is attempted, the action is hard-rejected (L4) and logged to audit.

### 3.5 Backup / Restore Design

Current production backup (`scripts/guinevere-backup.sh`) already implements:
- `pg_dumpall` on non-standard PostgreSQL port 5433.
- gzip compression and validation (`zcat | head | grep PostgreSQL`).
- Dual-target restic backup: idcloudhost S3 primary, Cloudflare R2 secondary.
- Retention: primary 7d/4w/3m; secondary 14d/8w/6m.
- `sops exec-env` for in-memory secret injection.
- Success marker `/var/log/guinevere/last-backup-success`.

For P23 L3 deploy gate, the backup step should reuse this script or its sub-operations, but add:
- Action-scoped backup id (not just timestamp).
- Backup reference captured in `rollback_payload.backup_ref`.
- Pre-action and post-action sentinel verification (`/home/guinevere/.backup/last-success`).
- Verification smoke after restore.

Restore/rollback path:
1. Stop affected `guinevere-*` service(s).
2. `pg_restore` or `psql -f` from the action-scoped dump.
3. `rclone copy` / `restic restore` for file artifacts.
4. `systemctl revert <service>` if unit overrides were changed.
5. `systemctl restart <service>`.
6. Smoke tests (health, DB, Redis, Aizanta-unaffected).
7. Update sentinel if rollback succeeded; else escalate.

### 3.7 Concrete CLI Examples (L1/L2/L3)

The following snippets are the canonical forms P23 executor should emit. All are run as `guinevere` user on the VPS or via SSH as `guinevere@localhost`.

#### L1 — Read / Idempotent

```bash
# Service status (L1)
ssh guinevere@localhost systemctl status guinevere-core.service --no-pager

# Journal tail (L1)
ssh guinevere@localhost journalctl -u guinevere-core.service -n 50 --no-pager

# Resource inspection (L1)
ssh guinevere@localhost systemctl show --property=ActiveState,MemoryMax,CPUQuota guinevere-core.service

# Redis health (L1)
redis-cli -p 6380 -n 0 PING

# PostgreSQL health (L1)
psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core -c "SELECT 1"

# Docker read-only inspection (L1)
docker ps --filter "name=guinevere" --format "table {{.Names}}\t{{.Status}}"
```

#### L2 — Write / Notify

```bash
# Restart a non-critical dev service after notify (L2)
ssh guinevere@localhost systemctl restart guinevere-shadow-monitor.service
# then notify: Discord webhook / Gotify

# Append a log entry (L2)
logger -t guinevere-p23 "Action 12345 completed"

# Create a dated evidence directory (L2)
ssh guinevere@localhost mkdir -p /home/guinevere/evidence/p23/$(date +%Y-%m-%d)
```

#### L3 — Backup / Canary / Smoke / Promote / Rollback

```bash
# BACKUP — action-scoped dump
ACTION_ID="p23-$(date -u +%Y%m%d-%H%M%S)-$(uuidgen | cut -d- -f1)"
DUMP_FILE="/tmp/${ACTION_ID}-guinevere_core.sql.gz"
ssh guinevere@localhost \
  "pg_dump -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core --clean --if-exists | gzip > ${DUMP_FILE}"

# BACKUP — file snapshot
FILES_TGZ="/tmp/${ACTION_ID}-files.tar.gz"
ssh guinevere@localhost \
  "tar -czf ${FILES_TGZ} /home/guinevere/code/guinevere /home/guinevere/config /home/guinevere/evidence 2>/dev/null"

# BACKUP — upload to primary + secondary (restic path from guinevere-backup.sh)
ssh guinevere@localhost "sops exec-env secrets/backup/idcloudhost-s3-plaintext.env 'restic backup --tag p23-deploy ${DUMP_FILE} ${FILES_TGZ}'"
ssh guinevere@localhost "sops exec-env secrets/backup/cloudflare-r2-plaintext.env 'restic backup --tag p23-deploy ${DUMP_FILE} ${FILES_TGZ}'"

# CANARY — start canary instance (assumes guinevere-core@canary template exists)
ssh guinevere@localhost systemctl start guinevere-core@canary.service
ssh guinevere@localhost systemctl is-active guinevere-core@canary.service

# SMOKE
ssh guinevere@localhost "curl -sf http://localhost:8001/health"   # 200
ssh guinevere@localhost "psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core -c 'SELECT 1'"
ssh guinevere@localhost "redis-cli -p 6380 -n 0 PING"            # PONG
ssh guinevere@localhost "cd /home/guinevere/code/guinevere && pytest tests/ -q"

# PROMOTE
ssh guinevere@localhost systemctl restart guinevere-core.service
ssh guinevere@localhost systemctl is-active guinevere-core.service
ssh guinevere@localhost "echo '${ACTION_ID}' > /home/guinevere/.backup/last-success"

# ROLLBACK — stop, restore, revert, restart, verify
ssh guinevere@localhost "systemctl stop guinevere-core.service"
ssh guinevere@localhost "zcat ${DUMP_FILE} | psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core"
ssh guinevere@localhost "tar -xzf ${FILES_TGZ} -C /"
ssh guinevere@localhost "systemctl revert guinevere-core.service && systemctl daemon-reload"
ssh guinevere@localhost "systemctl start guinevere-core.service"
# smoke again; if pass, update sentinel, else escalate
```

### 3.8 Aizanta-Impact Proof Checklist

For every L3 action, the executor records before/after state and asserts:

| Check | Before Action | After Action | Reject If |
|---|---|---|---|
| systemd | `systemctl is-active aizanta-*` listed (informational) | Same active set | Any `aizanta-*` service stopped or failed |
| Docker | `docker ps --filter name=aizanta` count | Same count ±0 | Count decreased or container removed |
| Redis DBs | `redis-cli -n 10 PING` → `PONG` | Same | PING fails or DB10-15 modified |
| PostgreSQL | `psql -U aizanta -d aizanta -c "SELECT 1"` | Same | Connection fails or data changed |
| Filesystem | `ls /home/aizanta` timestamp hash (read-only) | Same | Any write to `/home/aizanta/` |
| Network | `ss -tlnp | grep -E '5432|6379'` baseline | Same | Ports lost unexpectedly |

If any check degrades, the executor immediately HALTs, rolls back Guinevere, and documents in `evidence/incidents/`.

### 3.9 Official Doc Snippets (Key Options)

From the official docs retrieved 2026-06-25, the options we rely on are:

- **systemctl**: `start`, `stop`, `restart`, `status`, `is-active`, `enable`, `disable`, `revert`, `daemon-reload`. `systemctl revert <unit>` is the canonical way to drop runtime overrides and return to the vendor/unit-file state.
- **journalctl**: `-u <unit>` filters by unit; `-n <count>` limits lines; `--since/--until` time-bound logs.
- **pg_dump**: `--clean` and `--if-exists` generate DROP … IF EXISTS statements; `-Fc` custom format is smaller and faster for pg_restore; `-f` output file.
- **pg_restore**: `--clean`, `--if-exists`, `-d dbname`, `-1` single transaction. Custom-format restores are preferred for large databases.
- **pg_dumpall**: cluster-wide roles/tablespaces; used in `guinevere-backup.sh` because Aizanta may share the cluster.
- **rclone**: `copyto` for single files; `copy` for directories; `sync` only when exact mirror is intended (dangerous); `check` verifies source/dest hash equality.
- **aws-cli**: `aws s3 cp` / `aws s3 sync` are the S3 equivalents if rclone is unavailable; requires configured credentials.
- **OpenSSH**: `ssh -o StrictHostKeyChecking=accept-new` for first-connect automation (use with known-host pinning); `scp -r` for recursive copy.

### 3.10 Failure / Self-Debug / Rollback

| Failure | Detection | Auto-Response | Self-Debug |
|---|---|---|---|
| Service won't start | `systemctl is-active` fails / `systemctl status` shows error | Rollback to last known-good; alert Faiz | `journalctl -u <svc> -n 200`; HermesBrain.think with error context |
| Backup fails | restic/rclone exit != 0 or sentinel missing | Halt deploy; re-queue or escalate | Check network, SOPS age key, bucket credentials, disk space |
| Canary smoke fails | curl/health/DB/Redis check fails | Do not promote; rollback immediately | Compare canary vs stable env; inspect logs |
| Aizanta affected | `systemctl status aizanta-*` degraded after Guinevere action | HARD STOP Guinevere operations; rollback; verify Aizanta | Incident evidence in `evidence/incidents/` |
| SSH/SCP fails | non-zero exit, timeout, host key change | Retry once with backoff; then escalate | Check Tailscale/IP, firewall, key auth |
| pg_restore fails | invalid dump, dependency error, permissions | Rollback from verified backup; alert | Check dump integrity, target DB, extensions |
| HARD STOP triggered | `life_kernel:hard_stop` Redis key set | All running executors checkpoint and halt; queued actions remain queued | Journal/audit; resume after clear only for non-L3/L4 |

Self-debug loop (per P23 policy-gate research):
1. Capture context (stderr, return code, correlation_id, tier, consent, distress).
2. Call `HermesBrain.think()` to propose fix/rollback/escalate.
3. If fix: re-run within the same policy gate; still require L3 approval for promotion.
4. If rollback: restore from last known-good (sentinel), verify, log, notify.
5. If escalate: queue for Faiz review; do not retry destructive ops autonomously.

---

## 4. Implications for P23 Design

1. **Executor Adapter**: Build a `VPSExecutor` class implementing the P23 durable-queue interface (`backup`, `canary`, `smoke_test`, `deploy`, `rollback`) mirroring `src/life_kernel/domain_minds/deploy_backend.py`.
2. **Dry-Run Default**: The existing `SSHDeployBackend` defaults to `dry_run=True`; P23 should keep the same default and gate real execution behind L3 policy + Faiz approval.
3. **Reuse Production Backup Script**: The L3 backup step should invoke `scripts/guinevere-backup.sh` (or its extracted primitives) rather than reimplementing pg_dumpall/restic logic.
4. **Sentinel Integration**: Every successful backup and rollback updates `/home/guinevere/.backup/last-success` per ADR-035 B11.
5. **Aizanta Guardrails**: The executor must include pre/post Aizanta-unaffected checks as a hard gate; any degradation aborts and rolls back.
6. **Journal + Audit**: All commands, outputs, and rollback decisions flow to `audit.p23_action_log` (hash-chained WORM per P22/P23 research) and `src/life_kernel/journal.py`.
7. **Resource Limits**: Actions respect the shared-VPS cgroup (`MemoryMax=8G`, `CPUQuota=200%`) and never run as root or aizanta.

---

## 5. Risks / Open Questions

| ID | Risk / Open Question | Suggested Follow-Up |
|---|---|---|
| RQ-01 | Encrypted backup restore is blocked until ADR-035 B10 (offline age-key recovery / `secrets/backup/`) is resolved. | Document as blocker; plaintext pg_dump restore works now. |
| RQ-02 | No existing canary service/port (e.g., 8001) is defined; canary deploy semantics are still conceptual. | Define `guinevere-core@canary` systemd template and port/env isolation. |
| RQ-03 | `rclone` is documented in ADR-032 but the production backup script uses `restic`; should P23 use rclone, restic, or both? | Standardize on one primary restore path; keep restic for full backups, rclone for ad-hoc artifact copies. |
| RQ-04 | `aws-cli` is not currently installed/configured; using it would add a new dependency. | Decide whether to add aws-cli or stay with rclone/restic. |
| RQ-05 | Long-running DB restores can stall the action queue. | Use a dedicated L3 worker pool with long timeout and status polling. |
| RQ-06 | Root privileges may be required for `systemctl` operations on Guinevere units if policies change; current services run as `guinevere` user. | Confirm sudoers / polkit rules; design executor to run unprivileged where possible. |
| RQ-07 | Self-debug may propose a destructive "fix"; must not bypass L3 approval. | Enforce that HermesBrain proposals for L3 are re-evaluated by the 7-step policy gate. |

---

## 6. Recommendations to Planner

1. **Adopt the existing `SSHDeployBackend` interface** as the starting point for P23 VPS executor; extend it with real backup/canary/smoke/rollback steps.
2. **Reuse `scripts/guinevere-backup.sh`** for the L3 backup step rather than reimplementing.
3. **Implement Aizanta-unaffected checks** as mandatory pre/post conditions for every L3 action.
4. **Define the canary service** (`guinevere-core@canary` on port 8001) before any production deploy.
5. **Use the sentinel path `/home/guinevere/.backup/last-success`** as the rollback target marker per ADR-035 B11.
6. **Standardize restore tooling**: prefer restic/rclone over aws-cli to match ADR-032; if aws-cli is needed, justify separately.
7. **Integrate with P23 durable queue and policy gate**: every VPS action is an `action_queue` row with risk tier L3, backup_ref, and rollback_payload.
8. **Add regression tests** for the full L3 gate (backup→canary→smoke→rollback) before declaring P23 complete.

---

## 7. Verdict

P23 VPS/SSH/CLI/deploy action research is **ACCEPTED for planner input**. The existing Guinevere infrastructure (systemd services, backup script, deploy backend) provides a solid substrate; the L3 deploy gate, Aizanta isolation, and failure/rollback patterns are now clearly defined and consistent with AGENTS.md §0.1, ADR-014/016/025/032/035, and IMPLEMENTATION_GUIDE §6.

---

*File: `docs/setup-evidence/P23/research/p23-vps-cli-deploy-action-research.md`*
