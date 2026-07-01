# P26.1 Redis Write Buffer Deployment Safety and Rollback Research

| Field | Value |
|---|---|
| Task | P26.1 deployment safety researcher |
| Output path | `docs/setup-evidence/P26/redis-write-buffer/research/deploy-safety-rollback-research.md` |
| Workspace | `C:\Users\faizz\guinevere` |
| Production target | `root@49.12.82.34 -p 39999` |
| Hostname observed | `ninerouter-vps` |
| Research timestamp | 2026-06-28T00:17+07:00 |
| Mode | Read-only; no production mutation |
| Verdict | PASS for planning; Redis/write-buffer addition must be separate, backup-first, localhost-only, and must not change 9Router PM2 worker count |

## 1. Scope and Read-Only Boundary

This research inspected current PM2, systemd, firewall, Tailscale, local evidence, and existing Redis-related code patterns to recommend a safe Redis/write-buffer deployment plan for the production 9Router VPS.

Allowed actions performed:

- Read local `AGENTS.md`, ADR Index, PersonaSafetyPolicy, and P26 evidence.
- Queried production with read-only commands: `systemctl show/list-units/cat`, `pm2 status/describe`, `ss`, `iptables -S`, `ip6tables -S`, `tailscale` status/version/IP, local HTTP health probe, operator HTTP probes.
- Checked whether Redis/Valkey services are active.
- Read ecosystem wiring shape without intentionally changing services.
- Created this local markdown artifact only.

Actions not performed:

- No package install.
- No Redis install/start/restart.
- No PM2 restart/reload/scale/save/delete.
- No firewall, SSH, Tailscale, systemd daemon reload, or provider-network changes.
- No environment file dump was intentionally performed.
- No SQLite mutation, migration, checkpoint, or write-path action.

Boundary note:

- A legacy `/root/ecosystem.config.js` contains inline secret-like values. It must not be used as an evidence artifact or copied into reports. This research artifact intentionally does not include those values. Future deployment work should prefer env-file-only config and should treat legacy inline-secret config cleanup/rotation as a separate security task.

## 2. Current PM2/Systemd/Ecosystem Wiring

### 2.1 Production PM2 State

Fresh read-only PM2 status showed:

| PM2 id | Name | Version | Mode | PID | Uptime | Restarts | Status | Memory | User | Watching |
|---:|---|---|---|---:|---|---:|---|---:|---|---|
| 0 | `9router` | `0.5.8` | `cluster` | `43086` | about 5h | 5 | online | about 301 MB | root | disabled |
| 1 | `9router` | `0.5.8` | `cluster` | `43093` | about 5h | 5 | online | about 305 MB | root | disabled |
| 2 | `pm2-logrotate` | `3.0.0` | module | `28823` | online | 3 | online | about 58 MB | root | n/a |

Required invariant: **9Router must remain exactly 2 PM2 cluster workers.**

`pm2 describe 9router --no-color` confirmed:

| Field | Observed value |
|---|---|
| Script path | `/root/9router/.next/standalone/custom-server.js` |
| Exec cwd | `/root/9router/.next/standalone` |
| Exec mode | `cluster_mode` |
| Interpreter | `node` |
| Interpreter args | `--max-old-space-size=1843` |
| Node.js | `22.23.1` |
| Node env | `production` |
| PM2 max memory restart | `1992294400` bytes, about 1900 MB |
| Watch/reload | disabled |
| Unstable restarts | 0 |

### 2.2 systemd Wiring

`pm2-root.service` is the active supervisor:

| Field | Observed value |
|---|---|
| Unit | `pm2-root.service` |
| LoadState | `loaded` |
| ActiveState | `active` |
| SubState | `running` |
| FragmentPath | `/etc/systemd/system/pm2-root.service` |
| DropInPaths | `/etc/systemd/system/pm2-root.service.d/limits.conf` |
| ExecMainPID | `24174` |
| Restart | `on-failure` |
| LimitNOFILE | `65535` |
| LimitNOFILESoft | `65535` |

Unit behavior:

```ini
ExecStart=/usr/lib/node_modules/pm2/bin/pm2 resurrect
ExecReload=/usr/lib/node_modules/pm2/bin/pm2 reload all
ExecStop=/usr/lib/node_modules/pm2/bin/pm2 kill
Environment=PM2_HOME=/root/.pm2
```

Important implication:

- PM2 resurrects from `/root/.pm2/dump.pm2`, not from a single guaranteed ecosystem file.
- Any future config change must back up `/root/.pm2/dump.pm2`, identify the authoritative ecosystem/source, and avoid `pm2 save` until post-canary checks pass.

### 2.3 Ecosystem Files Found

Read-only file discovery found:

```text
/root/.pm2/dump.pm2
/root/9router/.next/standalone/ecosystem-debug.config.js
/root/9router/.next/standalone/ecosystem.config.js
/root/ecosystem.config.js
/root/p26-highend-2worker-tuning-backups/20260627-180750/system/dump.pm2
```

Current local workspace `ecosystem.config.js` mirrors the desired safe shape:

```js
module.exports = {
  apps: [{
    name: "9router",
    script: "custom-server.js",
    cwd: "/root/9router/.next/standalone",
    exec_mode: "cluster",
    instances: 2,
    node_args: "--max-old-space-size=1843",
    env: {
      NODE_ENV: "production",
      PORT: "20128",
      HOSTNAME: "0.0.0.0"
    },
    env_file: "/var/lib/9router/.env",
    kill_timeout: 5000,
    max_memory_restart: "1900M",
    autorestart: true,
    max_restarts: 10,
    restart_delay: 4000
  }]
};
```

Deployment implication:

- The future Redis/writer plan should not scale or replace the `9router` PM2 app.
- Add any writer as a separate process/service with a different name, such as `9router-redis-writer`, or as a systemd timer/service outside the PM2 app. Do not merge it into the two-worker cluster.

## 3. Current Network, Firewall, and Tailscale Ground Truth

### 3.1 Tailscale

Read-only checks showed:

| Check | Observed value |
|---|---|
| Tailscale version | `1.98.4` |
| Tailscale IPv4 | `100.104.210.75` |
| Tailscale self node | `vps-9router` |
| `tailscaled.service` | active/running |
| FragmentPath | `/usr/lib/systemd/system/tailscaled.service` |
| DropInPaths | `/etc/systemd/system/tailscaled.service.d/override.conf` |

Prior P26 evidence says Tailscale uses userspace networking. Do not change this mode as part of Redis/write-buffer work.

### 3.2 Firewall

Current filter rules:

```text
-P INPUT ACCEPT
-A INPUT -i tailscale0 -p tcp -m tcp --dport 20128 -j ACCEPT
-A INPUT -i venet0 -p tcp -m tcp --dport 20128 -j DROP
```

IPv6 input policy:

```text
-P INPUT ACCEPT
```

Current listeners relevant to this task:

```text
0.0.0.0:22     sshd
0.0.0.0:20128  PM2 / 9Router
[::]:22        sshd
```

No Redis listener on `6379` was observed.

Operator probes:

| Probe | Result |
|---|---|
| `http://100.104.210.75:20128/v1/models` | HTTP 200 over Tailscale |
| `http://49.12.82.34:20128/v1/models` | curl exit 7 / no connection |
| `http://127.0.0.1:20128/v1/models` from VPS | HTTP 200 |

Required invariant: **public IPv4 `49.12.82.34:20128` must remain blocked.**

## 4. Redis Current State

Read-only service checks:

```text
systemctl is-active redis-server redis valkey
inactive
inactive
inactive
```

No `6379` listener was present in `ss -ltnp`.

Implication:

- Redis is not currently an active local dependency for the production 9Router VPS.
- Installing/enabling Redis is a state-changing operation and must wait for an implementation plan, backups, canary, and rollback.
- Redis must be installed only on the 9Router VPS if approved; do not introduce shared Redis from unrelated Guinevere infrastructure.

## 5. Recommended Safe Redis/Writer Addition

### 5.1 Architecture Recommendation

Use a sidecar-style local Redis write buffer, not a PM2 worker-count change.

Recommended shape:

```text
9Router PM2 cluster: exactly 2 workers
  ├─ worker 0: handles HTTP / LLM routing
  └─ worker 1: handles HTTP / LLM routing

Local Redis/Valkey on 9Router VPS only
  └─ bind 127.0.0.1 only; no public/Tailscale listener required

Separate writer/drainer
  └─ single writer process drains Redis list/stream into SQLite or final store
```

Why:

- Keeps PM2 cluster exactly 2.
- Reduces SQLite write contention by funneling high-volume writes through one writer.
- Redis absorbs bursts while HTTP workers return faster.
- Writer can be canaried independently and stopped without changing public endpoint binding.

### 5.2 Redis Binding and Security Posture

Recommended Redis deployment constraints:

| Setting | Required value |
|---|---|
| Bind | `127.0.0.1 ::1` or `127.0.0.1` only |
| Protected mode | enabled |
| Port | default `6379` acceptable only if loopback-only; alternative local port acceptable |
| Persistence | AOF every second or RDB depending on data durability target |
| Systemd | `redis-server.service` or `valkey.service`, active only after approval |
| External access | none |
| Firewall | no firewall changes required if loopback-only |
| Secrets | no credentials in repo/evidence; if password/ACL used, store only in env file/secret manager |

Do not expose Redis on:

- `0.0.0.0:6379`
- `100.104.210.75:6379`
- public IPv4
- IPv6 wildcard

### 5.3 Queue/Buffer Semantics

Use Redis Streams or a list with explicit dead-letter behavior.

Preferred: Redis Streams.

```text
stream: 9router:write_buffer
group: 9router-writer
consumer: writer-1
dead-letter: 9router:write_buffer:dead_letter
```

Minimum safety behavior:

- Enqueue must be bounded or backpressure-aware.
- Payloads must not contain raw provider credentials, Authorization headers, cookies, API keys, or env values.
- Writer must acknowledge only after durable SQLite/store write succeeds.
- Failed records go to dead-letter with sanitized error metadata.
- Writer must log counts and error classes, not raw sensitive payloads.
- Enqueue failure policy must be explicit:
  - conservative option: fall back to existing synchronous SQLite write and log a warning;
  - high-throughput option: return success only if loss-tolerant data, otherwise fail closed.

### 5.4 Writer Process Placement

Recommended process manager:

| Option | Recommendation | Reason |
|---|---|---|
| systemd unit `9router-redis-writer.service` | Preferred | Separates writer lifecycle from PM2 worker count |
| PM2 app `9router-redis-writer` in fork mode | Acceptable | Operationally visible in PM2, but must not be counted as 9Router worker |
| Additional PM2 `9router` cluster instance | Forbidden | Violates exactly-2-worker invariant |
| In-process per-worker drainer | Not recommended | Two drainers can reintroduce write contention unless carefully locked |

If PM2 is used for the writer, acceptance must distinguish:

- exactly two `name == "9router"` cluster workers;
- optional one `name == "9router-redis-writer"` fork process.

## 6. Backup, Canary, and Rollback Plan

### 6.1 Pre-Implementation Backups

Run only in the future approved implementation window, before any package install or runtime change:

```bash
TS=$(date +%Y%m%d-%H%M%S)
BACKUP_ROOT=/root/p26-redis-write-buffer-backups/$TS
mkdir -p "$BACKUP_ROOT"/{pm2,systemd,redis,db,app}

pm2 status --no-color > "$BACKUP_ROOT/pm2/status-before.txt"
pm2 describe 9router --no-color > "$BACKUP_ROOT/pm2/describe-9router-before.txt"
cp -a /root/.pm2/dump.pm2 "$BACKUP_ROOT/pm2/dump.pm2.before"
cp -a /root/9router/.next/standalone/ecosystem.config.js "$BACKUP_ROOT/app/ecosystem.standalone.before.js" 2>/dev/null || true
cp -a /root/ecosystem.config.js "$BACKUP_ROOT/app/ecosystem.root.before.js" 2>/dev/null || true

systemctl cat pm2-root.service > "$BACKUP_ROOT/systemd/pm2-root.service.before.txt"
systemctl show pm2-root.service --no-pager > "$BACKUP_ROOT/systemd/pm2-root.show.before.txt"
systemctl cat tailscaled.service > "$BACKUP_ROOT/systemd/tailscaled.service.before.txt"
iptables-save > "$BACKUP_ROOT/systemd/iptables-save.before.txt"
ip6tables-save > "$BACKUP_ROOT/systemd/ip6tables-save.before.txt"

sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check; PRAGMA journal_mode;' > "$BACKUP_ROOT/db/sqlite-pragmas-before.txt"
sqlite3 /var/lib/9router/db/data.sqlite ".backup '$BACKUP_ROOT/db/data.sqlite.before'"
```

Notes:

- `iptables-save` here is backup/read output only. Do not restore or persist firewall state unless rollback requires it and Faiz explicitly approves.
- Do not dump `/var/lib/9router/.env` into evidence. If a protected backup is required, place it under root-only backup storage and do not copy it to repo.

### 6.2 Canary Sequence

Future canary should be staged:

1. Install Redis/Valkey without starting application integration.
2. Configure Redis loopback-only.
3. Start Redis and verify no public/Tailscale listener.
4. Start writer in dry-run or disabled-drain mode if available.
5. Enable enqueue for a narrow non-critical write path or percentage-gated traffic.
6. Verify queue depth, writer ack rate, SQLite integrity, endpoint health, and PM2 worker count.
7. Only after canary passes, persist PM2/systemd state if needed.

Minimum canary metrics:

| Metric | Pass condition |
|---|---|
| `9router` PM2 worker count | exactly 2 online |
| `9router` exec mode | `cluster_mode` |
| Public IPv4 `:20128` | blocked / no app response |
| Tailscale `:20128` | HTTP 200 |
| Local `:20128` | HTTP 200 |
| Redis bind | loopback-only |
| Redis ping | `PONG` locally |
| Queue depth | bounded and draining |
| Dead-letter count | zero or reviewed |
| SQLite integrity | `ok` |
| PM2 unstable restarts | no increase |

### 6.3 Rollback Plan

Fast rollback for app integration:

```bash
# Disable enqueue feature flag or remove REDIS_WRITE_BUFFER_ENABLED from runtime config.
# Then reload only if the planned implementation requires runtime env reload.
pm2 reload 9router --update-env
```

Rollback writer:

```bash
systemctl stop 9router-redis-writer.service
systemctl disable 9router-redis-writer.service
```

or if PM2-managed:

```bash
pm2 stop 9router-redis-writer
pm2 delete 9router-redis-writer
```

Rollback Redis:

```bash
systemctl stop redis-server
systemctl disable redis-server
```

Rollback PM2 if process definition changes misbehave:

```bash
cp -a /root/p26-redis-write-buffer-backups/<TS>/pm2/dump.pm2.before /root/.pm2/dump.pm2
pm2 resurrect
```

Rollback acceptance:

- `pm2 status` shows exactly two `9router` workers online.
- `curl http://127.0.0.1:20128/v1/models` returns HTTP 200.
- operator Tailscale probe returns HTTP 200.
- operator public IPv4 probe fails to connect or returns no app data.
- Redis is stopped or loopback-only.
- SQLite integrity check returns `ok`.
- No firewall, SSH, or Tailscale mode changed.

## 7. Required Verification Commands

### 7.1 Current Read-Only Verification Commands

Production:

```bash
hostname
date -Is
systemctl show pm2-root.service --property=Id,LoadState,ActiveState,SubState,FragmentPath,DropInPaths,ExecMainPID,Restart,LimitNOFILE,LimitNOFILESoft --no-pager
systemctl list-units --type=service --all --no-pager --no-legend | grep -Ei 'pm2|9router|redis|valkey|tailscale|ssh' || true
pm2 status --no-color
pm2 describe 9router --no-color
tailscale version | head -n 3
tailscale ip -4
tailscale status --self --peers=false
systemctl show tailscaled --property=ActiveState,SubState,ExecMainPID,FragmentPath,DropInPaths --no-pager
iptables -S INPUT
ip6tables -S INPUT
ss -H -ltnp | grep -E ':(20128|6379|22) ' || true
curl -sS -o /dev/null -w 'local_models=%{http_code} time=%{time_total}\n' --max-time 5 http://127.0.0.1:20128/v1/models
systemctl is-active redis-server redis valkey 2>/dev/null || true
```

Operator machine:

```powershell
curl.exe -sS -o NUL -w "tailscale_models=%{http_code} time=%{time_total}`n" --max-time 8 http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "public_ipv4_models=%{http_code} exit=%{exitcode} time=%{time_total}`n" --max-time 8 http://49.12.82.34:20128/v1/models
```

### 7.2 Future Post-Redis Verification Commands

Production:

```bash
pm2 status --no-color
pm2 describe 9router --no-color | sed -n '1,160p'
test "$(pm2 jlist | jq '[.[] | select(.name=="9router" and .pm2_env.status=="online")] | length')" -eq 2
pm2 jlist | jq -r '.[] | select(.name=="9router") | "\(.name) \(.pm_id) \(.pm2_env.exec_mode) \(.pm2_env.status) \(.pid)"'

systemctl is-active pm2-root tailscaled ssh
systemctl is-active redis-server redis valkey 2>/dev/null || true
systemctl is-active 9router-redis-writer.service 2>/dev/null || true

ss -H -ltnp | grep -E ':(20128|6379|22) ' || true
ss -H -ltnp | grep ':6379' | grep -Ev '127\.0\.0\.1|\[::1\]' && exit 1 || true

redis-cli -h 127.0.0.1 -p 6379 PING
redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:write_buffer 2>/dev/null || true
redis-cli -h 127.0.0.1 -p 6379 XLEN 9router:write_buffer:dead_letter 2>/dev/null || true

sqlite3 'file:/var/lib/9router/db/data.sqlite?mode=ro' 'PRAGMA integrity_check; PRAGMA journal_mode;'
curl -sS -o /dev/null -w 'local_models=%{http_code} time=%{time_total}\n' --max-time 5 http://127.0.0.1:20128/v1/models
iptables -S INPUT
ip6tables -S INPUT
```

Operator machine:

```powershell
ssh -p 39999 -o BatchMode=yes -o StrictHostKeyChecking=yes root@49.12.82.34 "hostname; date -Is"
curl.exe -sS -o NUL -w "tailscale_models=%{http_code} time=%{time_total}`n" --max-time 8 http://100.104.210.75:20128/v1/models
curl.exe -sS -o NUL -w "public_ipv4_models=%{http_code} exit=%{exitcode} time=%{time_total}`n" --max-time 8 http://49.12.82.34:20128/v1/models
```

## 8. Risks

| Risk | Why it matters | Mitigation |
|---|---|---|
| PM2 worker count drift | Requirement says exactly 2 workers; adding writer incorrectly can scale app or confuse acceptance | Add writer under distinct name; test exactly two `name=="9router"` online |
| Redis public exposure | Redis on public/Tailscale interface is credential/data exposure risk | Loopback-only bind; verify `ss` has no non-loopback `6379` |
| Firewall/Tailscale breakage | Existing access depends on targeted `venet0` DROP and userspace Tailscale | Do not touch firewall/Tailscale; verify pre/post |
| Public app port exposure | App listens on `0.0.0.0:20128`; public block is firewall-dependent | Operator public IPv4 probe must fail before and after |
| SQLite/Redis dual-write inconsistency | Enqueue success but writer failure can lose usage data or create backlog | Use stream ack-after-write, dead-letter, bounded queue, idempotency keys |
| Redis memory growth | Burst traffic can fill memory on 4 GB no-swap VPS | Set `maxmemory`, monitor queue depth, define backpressure |
| Secrets in ecosystem configs | Legacy ecosystem file contains inline secret-like values | Do not copy to evidence; migrate to env-file-only in separate security task; rotate if exposure is suspected |
| Package install changes service state | Installing Redis can auto-start services | Plan for install behavior; immediately verify bind and service state |
| PM2 resurrect mismatch | systemd uses `pm2 resurrect`; runtime may not match edited ecosystem file | Back up and verify `/root/.pm2/dump.pm2`; do not `pm2 save` until canary passes |
| Writer duplicates | Multiple drainers can reintroduce concurrency issues | One writer consumer unless stream group semantics are fully tested |

## 9. Hard Stops

Stop the future implementation immediately if any of these occur:

1. PM2 shows anything other than exactly two online `9router` workers.
2. `9router` leaves `cluster_mode`.
3. `pm2-root.service`, `tailscaled.service`, or `ssh.service` becomes inactive.
4. `http://127.0.0.1:20128/v1/models` stops returning HTTP 200.
5. `http://100.104.210.75:20128/v1/models` stops returning HTTP 200 from the operator host.
6. `http://49.12.82.34:20128/v1/models` returns HTTP 200 or any application response.
7. Redis listens on `0.0.0.0`, public IPv4, Tailscale IP, or wildcard IPv6.
8. Any firewall rule is flushed, default policy changed, or firewall persistence is altered.
9. Any Tailscale auth/login/logout/up/set/reset/mode change is attempted.
10. Any SSH config, root-login, password-auth, port, or provider NAT behavior is changed.
11. Any env file, API key, token, Redis password, SSH private key, Tailscale state, or provider credential appears in repo evidence.
12. Queue depth grows without draining during canary.
13. Dead-letter entries appear without reviewed classification.
14. SQLite integrity check returns anything other than `ok`.
15. PM2 unstable restarts increase after the change.

## 10. Recommendation

Proceed to planning only, not production mutation, with this design:

- Keep current 9Router PM2 app untouched at exactly 2 cluster workers.
- Install Redis/Valkey only on the 9Router VPS in a future approved implementation window.
- Configure Redis loopback-only and verify no external listener before integrating app code.
- Add a single separate writer process, preferably systemd-managed, with one consumer and dead-letter handling.
- Gate the app integration behind an explicit feature flag such as `REDIS_WRITE_BUFFER_ENABLED=false` by default.
- Canary with queue metrics and endpoint/network checks before persisting PM2 state.
- Keep rollback simple: disable feature flag, stop writer, stop Redis, restore PM2 dump only if necessary.

## 11. Acceptance Mapping

| Requirement | Result |
|---|---|
| Identify current PM2 wiring | PASS |
| Identify current systemd wiring | PASS |
| Identify ecosystem wiring | PASS, with secret-handling caveat |
| Recommend Redis/writer addition without breaking 2 workers | PASS |
| Include backup plan | PASS |
| Include canary plan | PASS |
| Include rollback plan | PASS |
| Include firewall verification commands | PASS |
| Include Tailscale verification commands | PASS |
| Include worker-count verification commands | PASS |
| Include risks | PASS |
| Include hard stops | PASS |
| No production changes | PASS |
| No install/restart/firewall/env dump in artifact | PASS |

## 12. Footer

P26.1 deployment safety research completed as read-only planning evidence. This document does not authorize Redis installation, PM2 reload/restart/save, firewall edits, SSH edits, Tailscale edits, or production deployment.
