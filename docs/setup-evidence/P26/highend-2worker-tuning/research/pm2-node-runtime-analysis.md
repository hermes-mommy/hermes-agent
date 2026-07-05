# P26 High-End 2-Worker Tuning — PM2 / Node Runtime Analysis

**Date**: 2026-06-27  
**Role**: Read-only PM2/Node runtime auditor  
**Workspace**: `C:\Users\faizz\guinevere`  
**SSH target**: `root@49.12.82.34 -p 39999`  
**Output path**: `docs/setup-evidence/P26/highend-2worker-tuning/research/pm2-node-runtime-analysis.md`

---

## 1. Scope and Safety Boundary

This was a read-only runtime audit for the P26 9Router VPS tuning track.

Actions performed:

- Read `C:\Users\faizz\guinevere\AGENTS.md` before runtime inspection.
- Queried PM2, Node, systemd, process limits, memory, CPU, listener, and health status.
- Sanitized environment handling by collecting environment key names only and not printing secret values.
- Wrote this markdown report as the only output artifact.

Actions not performed:

- No VPS mutation.
- No service restart or reload.
- No PM2 save/start/delete/reload/scale action.
- No firewall changes.
- No Tailscale changes.
- No env value dump.
- No non-output file edits.

---

## 2. Executive Verdict

**Verdict: PASS for current 2-worker topology, with tuning recommendations.**

The VPS is already running 9Router as two PM2 cluster workers on a 2-vCPU / 4-GB host. Both workers are online, healthy, and using a controlled Node heap flag of `--max-old-space-size=1843`. Runtime memory is moderate at approximately 243 MB and 313-328 MB per worker, with system available memory around 3.38 GB at the audit time.

The main tuning improvement is not worker count; it is configuration explicitness and operational guardrails:

- Keep `instances=2` for this 2-vCPU host.
- Keep 9Router in PM2 `cluster_mode`.
- Keep per-worker heap around `1536-1843 MB`; do not use the 9Router default heap.
- Keep `max_memory_restart` near `1900 MB` per worker.
- Preserve systemd/PM2 `LimitNOFILE=65535`; the shell default `ulimit -n=1024` is misleading and not the effective worker limit.
- Add a documented, reversible command plan for future tuning rather than applying changes ad hoc.

---

## 3. Host Snapshot

| Field | Observed Value |
|---|---|
| Hostname | `ninerouter-vps` |
| Audit time | `2026-06-27T17:59:32+07:00` |
| Kernel | `Linux 6.8.0 x86_64` |
| CPU | `2` vCPU |
| CPU model | `AMD EPYC 7401P 24-Core Processor` |
| Memory | `4000 MB total`, `3378 MB available` |
| Swap | `0 MB` |
| Load average | `0.13 0.14 0.12` |
| Node.js | `v22.23.1` |
| npm | `10.9.8` |
| PM2 | `7.0.1` |
| Interactive shell `ulimit -n` | `1024` |

Memory snapshot:

```text
Mem: 4000 total, 621 used, 1396 free, 1982 buff/cache, 3378 available
Swap: 0 total, 0 used, 0 free
```

Interpretation:

- The host is a small high-performance 2-vCPU / 4-GB node.
- Two Node cluster workers match available CPU cores.
- No swap means heap and restart thresholds must remain conservative enough to avoid host-level OOM.

---

## 4. PM2 Status Snapshot

Sanitized `pm2 status --no-color` summary:

| PM2 id | Name | Version | Mode | PID | Uptime | Restarts | Status | CPU | Memory | User | Watching |
|---:|---|---:|---|---:|---|---:|---|---:|---:|---|---|
| `0` | `9router` | `0.5.8` | `cluster` | `31108` | `7h` | `4` | `online` | `0%` | `242.6 MB` | `root` | `disabled` |
| `1` | `9router` | `0.5.8` | `cluster` | `31121` | `7h` | `4` | `online` | `0%` | `313.2 MB` | `root` | `disabled` |
| `2` | `pm2-logrotate` | `3.0.0` | module/fork | `28823` | online | `3` | `online` | `0%` | `71.4 MB` | `root` | n/a |

Worker count and mode:

- 9Router worker count: **2**
- PM2 execution mode: **cluster mode**
- PM2 instance setting: **2**
- PM2 watch mode: **disabled**
- PM2 autorestart: **enabled**

---

## 5. PM2 Describe Summary, Sanitized

Sanitized `pm2 describe 0 --no-color` and `pm2 describe 1 --no-color` observations:

| Field | Worker 0 | Worker 1 |
|---|---|---|
| Status | `online` | `online` |
| Name | `9router` | `9router` |
| Namespace | `default` | `default` |
| Version | `0.5.8` | `0.5.8` |
| Restarts | `4` | `4` |
| Unstable restarts | `0` | `0` |
| Max memory restart | `1992294400` bytes, about `1900 MB` | `1992294400` bytes, about `1900 MB` |
| Uptime | about `7h` | about `7h` |
| Script | `/root/9router/.next/standalone/custom-server.js` | `/root/9router/.next/standalone/custom-server.js` |
| Interpreter | `node` | `node` |
| Interpreter args | `--max-old-space-size=1843` | `--max-old-space-size=1843` |
| Exec cwd | `/root/9router/.next/standalone` | `/root/9router/.next/standalone` |
| Exec mode | `cluster_mode` | `cluster_mode` |
| Node env | `production` | `production` |
| Node.js version | `22.23.1` | `22.23.1` |
| Watch and reload | disabled | disabled |
| Created at | `2026-06-27T03:04:08.704Z` | `2026-06-27T03:04:08.862Z` |

PM2 code metrics at the audit time:

| Metric | Worker 0 | Worker 1 |
|---|---:|---:|
| Heap Size | `96.17 MiB` | `91.53 MiB` |
| Used Heap Size | `76.65 MiB` | `80.94 MiB` |
| Heap Usage | `79.7%` | `88.43%` |
| Active requests | `0` | `0` |
| Active handles | `1` | `2` |
| Event Loop Latency | `0.38 ms` | `0.25 ms` |
| Event Loop Latency p95 | `1.06 ms` | `1.05 ms` |
| HTTP rate | `0.02-0.03 req/min` | `0.02-0.03 req/min` |
| HTTP Mean Latency | `13 ms` | `73 ms` |
| HTTP P95 Latency | high historical value reported by PM2 | high historical value reported by PM2 |

The high PM2 HTTP P95 values appear to be historical metric artifacts or sparse-sample effects under very low request volume; they should not be treated as a tuning blocker without a separate controlled load test.

---

## 6. Sanitized Environment Key Inventory

Environment values were not collected. Only key names were inspected from PM2 metadata.

Common 9Router worker env keys observed:

```text
9router
HOME
HOSTNAME
LOGNAME
NODE_APP_INSTANCE
NODE_ENV
PATH
PM2_HOME
PM2_JSON_PROCESSING
PM2_USAGE
PORT
PWD
SHELL
SHLVL
SSH_CLIENT
SSH_CONNECTION
USER
_
_pm2_version
_tree_pids
automation
autorestart
autostart
axm_dynamic
axm_monitor
created_at
cwd
env
env_file
exec_interpreter
exec_mode
exit_code
filter_env
instance_var
instances
kill_retry_time
kill_timeout
km_link
max_memory_restart
max_restarts
merge_logs
name
namespace
node_args
node_version
pm_cwd
pm_exec_path
pm_id
pm_pid_path
pm_uptime
pmx
prev_restart_delay
restart_delay
restart_time
status
treekill
unique_id
unstable_restarts
username
version
vizion_running
windowsHide
```

Secret-like key names detected by conservative pattern matching:

```text
PM2_USAGE
PWD
```

Notes:

- No secret values were printed or stored in this report.
- The apparent secret-like keys above are PM2/system metadata key names, not necessarily application credentials.
- PM2 `describe` showed only divergent SSH-related env entries, not full application secrets.

---

## 7. Process Memory, FD, and Limit Observations

Per-process `/proc` observations:

| Field | Worker PID `31108` | Worker PID `31121` |
|---|---:|---:|
| VmRSS | `251588 kB`, about `246 MB` | `320352 kB`, about `313 MB` |
| VmHWM | `300500 kB`, about `293 MB` | `351468 kB`, about `343 MB` |
| Threads | `11` | `11` |
| FDSize | `128` | `128` |
| Open FDs | `24` | `25` |
| Max open files | `65535 soft / 65535 hard` | `65535 soft / 65535 hard` |
| Max processes | `62987 soft / 62987 hard` | `62987 soft / 62987 hard` |
| Max address space | `unlimited` | `unlimited` |
| Max locked memory | `524288000 bytes` | `524288000 bytes` |

Process table:

| PID | PPID | RSS | VSZ | Command |
|---:|---:|---:|---:|---|
| `24174` | `1` | `69344 KB` | `1133388 KB` | `PM2 v7.0.1: God Daemon` |
| `31108` | `24174` | `251588 KB` | `22469756 KB` | `next-server (v16.2.9)` |
| `31121` | `24174` | `320352 KB` | `22534352 KB` | `next-server (v16.2.9)` |

Interpretation:

- Effective worker `NOFILE` is healthy at 65535.
- Open FD usage is tiny relative to the limit.
- Worker RSS is well below the PM2 restart threshold.
- The large VSZ is normal for modern Node/V8 address reservation and should not be treated as physical memory consumption.

---

## 8. systemd / NOFILE Observations

PM2 is managed by `pm2-root.service`.

Observed systemd properties:

| Field | Value |
|---|---|
| Unit | `pm2-root.service` |
| LoadState | `loaded` |
| ActiveState | `active` |
| SubState | `running` |
| FragmentPath | `/etc/systemd/system/pm2-root.service` |
| ExecMainPID | `24174` |
| Restart | `on-failure` |
| MemoryMax | `infinity` |
| CPUQuota | `infinity` |
| TasksMax | `infinity` |
| LimitNOFILE | `65535` |
| LimitNOFILESoft | `65535` |

Unit file observations:

```ini
[Service]
Type=forking
User=root
LimitNOFILE=infinity
LimitNPROC=infinity
LimitCORE=infinity
Environment=PM2_HOME=/root/.pm2
PIDFile=/root/.pm2/pm2.pid
Restart=on-failure
ExecStart=/usr/lib/node_modules/pm2/bin/pm2 resurrect
ExecReload=/usr/lib/node_modules/pm2/bin/pm2 reload all
ExecStop=/usr/lib/node_modules/pm2/bin/pm2 kill
```

Drop-in observed:

```ini
[Service]
LimitNOFILE=65535
```

Interpretation:

- The effective process limit is correct even though an interactive shell reports `ulimit -n=1024`.
- Future verification should check `/proc/<worker-pid>/limits` or `systemctl show pm2-root.service`, not just shell `ulimit`.
- The unit has no systemd memory cap; PM2's `max_memory_restart` is the active memory guardrail.

---

## 9. Health and Listener Observations

Health checks:

| Check | Result |
|---|---|
| `http://127.0.0.1:20128/api/health` | `{"ok":true}` |
| `http://127.0.0.1:20128/v1/models` | HTTP `200` |

Listener:

```text
LISTEN 0 128 0.0.0.0:20128 0.0.0.0:* users:(("PM2 v7.0.1: God",pid=24174,fd=22))
```

Interpretation:

- 9Router is reachable locally on port `20128`.
- PM2 cluster is accepting the shared socket through the PM2 daemon.
- Public exposure posture was not audited here; this report does not alter firewall or Tailscale state.

---

## 10. Memory and Restart Headroom

Observed memory:

- Host available memory: about `3378 MB`.
- 9Router workers total RSS: about `246 MB + 313 MB = 559 MB`.
- PM2 daemon RSS: about `68 MB`.
- pm2-logrotate memory: about `71 MB`.
- Approximate 9Router + PM2 runtime RSS: about `700 MB`.

Current memory guards:

- Per-worker Node old-space heap: `1843 MB`.
- Per-worker PM2 `max_memory_restart`: about `1900 MB`.
- Two workers at max threshold could consume around `3.8 GB` RSS-like memory before PM2 restarts them, which is close to total host RAM.

Practical interpretation:

- Current idle/normal memory headroom is excellent.
- Current worst-case `max_memory_restart` is aggressive for a 4-GB no-swap host if both workers grow simultaneously.
- If P26 expects high concurrency or large streaming workloads, reduce per-worker heap slightly or add swap as an ops-level safety buffer. Do not increase workers beyond 2 on this host.

---

## 11. Recommended 2-Worker Tuning Values

Recommended target for this exact VPS shape:

| Setting | Recommended Value | Reason |
|---|---:|---|
| PM2 instances | `2` | Matches 2 vCPU; avoids context switching and duplicate heap pressure. |
| PM2 exec mode | `cluster` | Already correct; allows shared listen socket and multi-core use. |
| Node old-space heap | `1536-1843 MB` per worker | Leaves OS/PM2/cache headroom on 4 GB RAM. Current `1843` is acceptable but near upper bound. |
| PM2 max memory restart | `1800-1900M` per worker | Current about `1900 MB`; acceptable upper bound. Prefer `1800M` if load tests show correlated worker growth. |
| `NODE_ENV` | `production` | Already correct. |
| Watch mode | `false` / disabled | Already correct for production. |
| PM2 autorestart | `true` | Already correct. |
| systemd `LimitNOFILE` | `65535` | Already correct. Preserve. |
| systemd `Restart` | `on-failure` | Already correct for PM2 daemon. |
| Swap | Optional `1-2 GB` | Useful safety buffer for no-swap 4-GB host, but not required by current idle state. |
| Log rotation | Keep `pm2-logrotate` | Already present; prevents runaway log files. |

Important 9Router-specific note from prior verified P25 research:

- 9Router heap control is normally driven through `NINEROUTER_NODE_HEAP_MB` at CLI launch time.
- In this PM2 deployment, the active runtime already shows explicit Node args `--max-old-space-size=1843`.
- Future operators should verify whether this comes from the PM2 ecosystem config, startup script, or direct PM2 process definition before changing it.

Recommended steady-state configuration goal:

```text
instances: 2
exec_mode: cluster
node_args: ["--max-old-space-size=1536"]  # conservative option
max_memory_restart: "1800M"
watch: false
autorestart: true
NODE_ENV: production
PORT: 20128
```

Alternative current-compatible upper-bound configuration:

```text
instances: 2
exec_mode: cluster
node_args: ["--max-old-space-size=1843"]
max_memory_restart: "1900M"
watch: false
autorestart: true
NODE_ENV: production
PORT: 20128
```

I recommend starting with the conservative `1536/1800M` pair only if load testing shows memory spikes or OOM risk. If current P26 evidence only needs the high-end 2-worker topology, the existing `1843/1900M` pair can be preserved.

---

## 12. Exact Read-Only Commands Used

These commands were used for inspection only:

```bash
ssh -p 39999 -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@49.12.82.34 \
  "hostname; date -Is; uname -a; node -v 2>/dev/null || true; npm -v 2>/dev/null || true; pm2 -v 2>/dev/null || true; nproc; free -m; lscpu | sed -n 's/^CPU(s):/CPU(s):/p; s/^Model name:/Model name:/p'; ulimit -n"
```

```bash
ssh -p 39999 -o BatchMode=yes -o StrictHostKeyChecking=accept-new root@49.12.82.34 \
  "pm2 status --no-color 2>/dev/null || pm2 status 2>/dev/null || true"
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 \
  "pm2 describe 0 --no-color; pm2 describe 1 --no-color"
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 \
  "echo PID=31108; grep -E 'Max open files|Max processes|Max locked memory|Max address space' /proc/31108/limits; grep -E 'VmRSS|VmHWM|Threads|FDSize' /proc/31108/status; echo FD_COUNT_31108; ls /proc/31108/fd | wc -l; echo PID=31121; grep -E 'Max open files|Max processes|Max locked memory|Max address space' /proc/31121/limits; grep -E 'VmRSS|VmHWM|Threads|FDSize' /proc/31121/status; echo FD_COUNT_31121; ls /proc/31121/fd | wc -l"
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 \
  "ps -o pid,ppid,ni,pri,stat,etime,rss,vsz,comm,args -p 24174,31108,31121 --cols 220"
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 \
  "systemctl list-units --type=service --all --no-pager --no-legend | grep -Ei 'pm2|9router|ninerouter' || true; systemctl show pm2-root.service 2>/dev/null | grep -E '^(Id|Names|LoadState|ActiveState|SubState|FragmentPath|ExecMainPID|Restart|LimitNOFILE|TasksMax|MemoryMax|CPUQuota|Environment=)' || true; systemctl cat pm2-root.service 2>/dev/null | sed -E 's/(TOKEN|KEY|SECRET|PASSWORD|PASS|PWD|AUTH|COOKIE|CREDENTIAL|PRIVATE|DATABASE_URL|REDIS_URL|DSN)=([^[:space:]]+)/\1=<redacted>/Ig' || true"
```

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 \
  "printf 'health_api='; curl -fsS --max-time 3 http://127.0.0.1:20128/api/health 2>/dev/null || true; printf '\nmodels_http_code='; curl -sS -o /dev/null -w '%{http_code}' --max-time 3 http://127.0.0.1:20128/v1/models 2>/dev/null || true; printf '\nlisteners='; ss -ltnp 2>/dev/null | grep ':20128' || true; printf '\nloadavg='; cat /proc/loadavg"
```

Sanitized env-key extraction command:

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 "node <<'NODE'
const {execSync}=require('child_process');
function sh(cmd){try{return execSync(cmd,{encoding:'utf8',stdio:['ignore','pipe','pipe']}).trim()}catch(e){return (e.stdout||'').toString().trim()}}
const raw=sh('pm2 jlist');
let arr=[];
try{arr=JSON.parse(raw)}catch(e){console.log(JSON.stringify({error:'pm2 jlist parse failed'})); process.exit(0)}
const secretRe=/(TOKEN|KEY|SECRET|PASSWORD|PASS|PWD|AUTH|COOKIE|CREDENTIAL|PRIVATE|SOPS|AGE|DATABASE_URL|REDIS_URL|DSN)/i;
const out=arr.map(p=>{
  const env=p.pm2_env||{};
  const keys=Object.keys(env).filter(k=>!['axm_options','axm_actions','vizion','pm_out_log_path','pm_err_log_path'].includes(k)).sort();
  const secretKeys=keys.filter(k=>secretRe.test(k));
  return {
    pm_id:p.pm_id,
    name:p.name,
    namespace:env.namespace,
    version:env.version,
    status:env.status,
    exec_mode:env.exec_mode,
    instances:env.instances,
    node_version:env.node_version,
    pm2_version:env.pm2_version,
    pid:p.pid,
    restart_time:env.restart_time,
    unstable_restarts:env.unstable_restarts,
    uptime_ms: env.pm_uptime ? Date.now()-env.pm_uptime : null,
    created_at:env.created_at,
    memory_mb:p.monit&&p.monit.memory ? Math.round(p.monit.memory/1024/1024*10)/10 : null,
    cpu_percent:p.monit&&typeof p.monit.cpu==='number'?p.monit.cpu:null,
    watching:!!env.watch,
    autorestart:env.autorestart,
    max_memory_restart:env.max_memory_restart || null,
    script:env.pm_exec_path ? env.pm_exec_path.replace(process.env.HOME||'/root','~') : null,
    cwd:env.pm_cwd ? env.pm_cwd.replace(process.env.HOME||'/root','~') : null,
    node_args:env.node_args || [],
    args:env.args || [],
    env_keys:keys,
    secret_like_env_keys:secretKeys
  }
});
console.log(JSON.stringify(out,null,2));
NODE"
```

---

## 13. Future Change Commands, Not Run

The following are proposed commands for a future implementation step. They were **not** run in this audit.

First, locate the PM2 process definition:

```bash
pm2 describe 9router
pm2 jlist | jq '.[] | select(.name=="9router") | {pm_id, name, exec_mode: .pm2_env.exec_mode, instances: .pm2_env.instances, node_args: .pm2_env.node_args, max_memory_restart: .pm2_env.max_memory_restart, pm_exec_path: .pm2_env.pm_exec_path, pm_cwd: .pm2_env.pm_cwd}'
```

If an ecosystem file exists, edit it through the approved implementation workflow to use one of these target pairs:

```javascript
instances: 2,
exec_mode: "cluster",
node_args: ["--max-old-space-size=1536"],
max_memory_restart: "1800M",
watch: false,
autorestart: true,
env: {
  NODE_ENV: "production",
  PORT: "20128"
}
```

or preserve the current upper-bound pair:

```javascript
instances: 2,
exec_mode: "cluster",
node_args: ["--max-old-space-size=1843"],
max_memory_restart: "1900M",
watch: false,
autorestart: true,
env: {
  NODE_ENV: "production",
  PORT: "20128"
}
```

Apply with a reload only after backup and approval:

```bash
pm2 reload 9router --update-env
pm2 save
systemctl status pm2-root.service --no-pager
```

If the process was originally launched directly instead of from an ecosystem file, a future controlled change would use an explicit command shaped like:

```bash
cd /root/9router/.next/standalone
pm2 start custom-server.js \
  --name 9router \
  -i 2 \
  --max-memory-restart 1800M \
  --node-args="--max-old-space-size=1536" \
  --time
```

That direct start command should not be used until the current PM2 definition has been backed up and the rollback target is known.

---

## 14. Rollback Plan for Future Tuning

Rollback prerequisites before any future runtime mutation:

```bash
pm2 jlist > /root/pm2-jlist-before-p26-$(date +%Y%m%d-%H%M%S).json
pm2 save
cp -a /root/.pm2/dump.pm2 /root/.pm2/dump.pm2.before-p26-$(date +%Y%m%d-%H%M%S)
systemctl cat pm2-root.service > /root/pm2-root-before-p26-$(date +%Y%m%d-%H%M%S).service.txt
```

Rollback commands if a future tuning change misbehaves:

```bash
pm2 reload 9router --update-env
```

If reload does not restore the previous stable process definition:

```bash
cp -a /root/.pm2/dump.pm2.before-p26-<timestamp> /root/.pm2/dump.pm2
pm2 resurrect
```

If PM2 daemon state is broken:

```bash
systemctl restart pm2-root.service
pm2 status
```

Rollback acceptance:

- `pm2 status` shows two `9router` workers online.
- `pm2 describe 0` and `pm2 describe 1` show expected node args and memory restart threshold.
- `/api/health` returns `{"ok":true}`.
- `/v1/models` returns HTTP `200`.
- `/proc/<pid>/limits` shows `Max open files 65535`.

---

## 15. Verification Commands for Future Implementation

Run after any future approved tuning change:

```bash
pm2 status --no-color
pm2 describe 0 --no-color
pm2 describe 1 --no-color
```

```bash
node -v
pm2 -v
free -m
cat /proc/loadavg
```

```bash
curl -fsS --max-time 3 http://127.0.0.1:20128/api/health
curl -sS -o /dev/null -w "%{http_code}\n" --max-time 3 http://127.0.0.1:20128/v1/models
```

```bash
for p in $(pm2 pid 9router); do
  echo "PID=$p"
  grep -E 'Max open files|Max processes|Max address space' /proc/$p/limits
  grep -E 'VmRSS|VmHWM|Threads|FDSize' /proc/$p/status
  ls /proc/$p/fd | wc -l
done
```

```bash
systemctl show pm2-root.service | grep -E '^(ActiveState|SubState|LimitNOFILE|LimitNOFILESoft|MemoryMax|TasksMax|Restart=)'
```

Expected verification result:

- Exactly two 9Router PM2 workers online.
- Exec mode remains `cluster`.
- Node args match the selected heap target.
- PM2 `max_memory_restart` matches the selected guardrail.
- Health endpoint passes.
- Models endpoint returns HTTP 200.
- Effective worker `NOFILE` remains `65535`.
- No unstable restarts increase after the change.

---

## 16. Caveats

- This audit did not run a load test, so throughput and tail latency recommendations are topology-based rather than benchmark-based.
- This audit did not inspect secret values or application provider configuration.
- This audit did not change runtime state, so future implementation must still verify the actual source of the current PM2 process definition before applying changes.
- PM2 HTTP P95 metric looked anomalously high under sparse traffic; treat it as a signal for load-test verification, not as standalone proof of a runtime bottleneck.

---

## 17. Acceptance Mapping

| Requirement | Result |
|---|---|
| Read `AGENTS.md` first | PASS |
| PM2 status/describe sanitized | PASS |
| Worker count | PASS: `2` |
| Cluster mode | PASS: `cluster_mode` |
| Env keys without secret values | PASS |
| Memory/restart/headroom | PASS |
| NOFILE/systemd observations | PASS |
| Recommended 2-worker tuning values | PASS |
| Exact commands | PASS |
| Rollback/verification | PASS |
| No VPS mutation | PASS |
| No service restart | PASS |
| No secret printing | PASS |
| No firewall/Tailscale changes | PASS |

---

## 18. Footer

Prepared for Guinevere P26 high-end 2-worker tuning. This report is evidence-only and read-only.
