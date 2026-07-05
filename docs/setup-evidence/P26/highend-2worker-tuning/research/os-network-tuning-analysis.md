# P26 High-End 2-Worker Tuning: OS/Network Auditor Analysis

**Date**: 2026-06-27  
**Role**: OS/network auditor, read-only research sub-agent  
**Workspace**: `C:\Users\faizz\guinevere`  
**SSH target**: `root@49.12.82.34 -p 39999`  
**Output path**: `docs/setup-evidence/P26/highend-2worker-tuning/research/os-network-tuning-analysis.md`  
**Mutation status**: No VPS mutation performed. No service restart, firewall change, Tailscale change, or non-output repo edit performed.

## 1. Scope and Method

This report audits the VPS OS/network surface for safe 9Router high-traffic tuning under the P26 high-end 2-worker PM2 cluster. The audit is intentionally conservative:

- Only read-only SSH commands were used.
- No secrets, env files, provider keys, request payloads, or raw application logs were printed.
- Recommendations are limited to sysctl keys confirmed as supported by this VPS/container kernel.
- Unsupported common Linux tuning keys are explicitly excluded.

## 2. OS and Kernel Snapshot

Observed via `uname -a` and `/etc/os-release`:

| Item | Observed value |
|---|---|
| Hostname | `ninerouter-vps` |
| OS | Ubuntu 24.04.4 LTS (Noble Numbat) |
| Kernel | `Linux 6.8.0 #1 SMP Tue Jan 25 12:49:12 MSK 2022 x86_64` |
| CPU | 2 cores |
| Memory | 3.9 GiB total, about 3.3 GiB available at audit time |
| Swap | 0 B |
| Primary interface | `venet0` |
| Interface type | `BROADCAST,POINTOPOINT,NOARP,UP,LOWER_UP` |
| MTU | 1500 |
| qdisc | `noqueue` on `lo` and `venet0` |
| Default route | `default dev venet0 scope link` |

Interpretation:

- This looks like a constrained VPS/container network surface using `venet0`, not a fully exposed bare-metal NIC.
- qdisc is `noqueue`; queue discipline tuning such as `fq`, `fq_codel`, `cake`, or BBR pairing is not currently actionable from the exposed host surface.
- The kernel/sysctl surface is much narrower than a normal Ubuntu 24.04 VM.

## 3. Current Runtime Signals

Observed read-only:

| Signal | Value |
|---|---|
| `fs.file-max` | `12979898` |
| `fs.nr_open` | `1048576` |
| interactive `ulimit -n` | `1024` |
| systemd `DefaultLimitNOFILE` | `524288` |
| `pm2-root.service` `LimitNOFILE` | `65535` |
| `pm2-root.service` drop-in | `/etc/systemd/system/pm2-root.service.d/limits.conf` |
| `ss -s` TCP established | `7` |
| `ss -s` TCP timewait | about `1842` |
| `/proc/net/sockstat` TCP mem | `799` |

Existing P26 evidence also records:

- PM2 cluster: 2 workers.
- 9Router v0.5.8.
- Persistent PM2 NOFILE limit already added.
- Live PM2 and worker NOFILE limits raised to `65535`.
- Apache was stopped/disabled in later high-traffic tuning evidence.
- `/etc/sysctl.d/99-9router-hightraffic.conf` exists and currently contains only `net.core.somaxconn = 4096`.

## 4. Supported Sysctl Surface

The VPS exposes only a small subset of common network sysctls. These were observed through `sysctl` or `/proc/sys`.

### 4.1 Supported Network Core Values

| Key | Current value | Recommendation |
|---|---:|---|
| `net.core.somaxconn` | `4096` | Keep at `4096`; already suitable for 9Router listener backlog. |

The following common `net.core` tuning keys were not exposed in `sysctl -a` or `/proc/sys/net/core` and should not be configured on this host:

- `net.core.netdev_max_backlog`
- `net.core.rmem_max`
- `net.core.wmem_max`
- `net.core.rmem_default`
- `net.core.wmem_default`
- `net.core.default_qdisc`
- `net.core.optmem_max`
- `net.core.busy_poll`
- `net.core.busy_read`

### 4.2 Supported IPv4/TCP Values

| Key | Current value | Recommendation |
|---|---:|---|
| `net.ipv4.ip_forward` | `1` | Do not change during 9Router tuning. It may be related to VPS/Tailscale/container routing. |
| `net.ipv4.ip_forward_use_pmtu` | `0` | Keep default; no evidence this is bottlenecking 9Router. |
| `net.ipv4.ip_local_port_range` | `32768 60999` | Optional safe expansion to `10240 65535` if outbound provider fan-out grows. Not urgent at current load. |
| `net.ipv4.tcp_ecn` | `2` | Keep; modern default-like behavior and not a current bottleneck. |
| `net.ipv4.tcp_fastopen` | `0` | Do not enable by default; benefit is uncertain for this proxy and can create middlebox/client compatibility risk. |
| `net.ipv4.tcp_keepalive_time` | `7200` | Optional reduce only if stale long-lived sockets become visible. Not needed for current low established count. |
| `net.ipv4.tcp_keepalive_intvl` | `75` | Keep unless changing keepalive policy intentionally. |
| `net.ipv4.tcp_keepalive_probes` | `9` | Keep unless changing keepalive policy intentionally. |
| `net.ipv4.tcp_mem` | `3078249 4104335 6156498` | Kernel-managed memory thresholds; do not override. |
| `net.ipv4.tcp_min_snd_mss` | supported, current not queried | No tuning recommended. |

The following common TCP tuning keys were not present and must not be persisted on this host:

- `net.ipv4.tcp_rmem`
- `net.ipv4.tcp_wmem`
- `net.ipv4.tcp_congestion_control`
- `net.ipv4.tcp_available_congestion_control`
- `net.ipv4.tcp_max_syn_backlog`
- `net.ipv4.tcp_tw_reuse`
- `net.ipv4.tcp_fin_timeout`
- `net.ipv4.tcp_mtu_probing`
- `net.ipv4.tcp_slow_start_after_idle`
- `net.ipv4.tcp_notsent_lowat`
- `net.ipv4.tcp_no_metrics_save`
- `net.ipv4.tcp_syncookies`
- `net.ipv4.tcp_timestamps`
- `net.ipv4.tcp_sack`
- `net.ipv4.tcp_window_scaling`

### 4.3 IPv6 Values

| Key | Current value | Recommendation |
|---|---:|---|
| `net.ipv6.conf.all.disable_ipv6` | `0` | Keep; no 9Router-specific reason to disable. |
| `net.ipv6.conf.default.disable_ipv6` | `0` | Keep. |
| `net.ipv6.conf.all.forwarding` | `0` | Keep. |
| `net.ipv6.conf.default.forwarding` | `0` | Keep. |

## 5. Safe Sysctl Recommendations

### Recommended Persistent Baseline

The existing persistent file is the right location:

`/etc/sysctl.d/99-9router-hightraffic.conf`

Recommended baseline content:

```conf
# P26 9Router high-traffic tuning
# Supported on ninerouter-vps constrained kernel/sysctl surface.
net.core.somaxconn = 4096
```

Rationale:

- Already present and active.
- Supported by the host.
- Low-risk and directly relevant to HTTP listener backlog under bursty local/Tailscale traffic.
- Does not touch firewall, routes, Tailscale, qdisc, provider credentials, or application config.

### Optional Future Add-on

Only if load tests or production metrics show ephemeral port pressure during heavy outbound provider fan-out:

```conf
# Optional: wider outbound ephemeral port range for high fan-out provider traffic.
net.ipv4.ip_local_port_range = 10240 65535
```

Rationale:

- Supported on the host.
- Reversible.
- Useful if 9Router opens many short-lived outbound TCP connections to upstream providers.

Why not apply immediately:

- Current `ss -s` snapshot shows only single-digit established TCP connections.
- The main P26 evidence suggests local endpoint latency was likely app/upstream-provider related, not local OS port exhaustion.
- Wider port range is safe but not necessary without a symptom.

### Conditional Keepalive Policy

Only if stale long-lived streaming/client sockets accumulate and application-level cleanup is insufficient:

```conf
# Optional stale-connection cleanup policy; do not apply without socket evidence.
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
```

Why not apply immediately:

- The current established connection count is low.
- Aggressive keepalives can add background probe traffic and may interfere with legitimate long-running streams if upstream/client networks are flaky.
- Application-level HTTP timeout behavior should be understood first.

## 6. Explicit Non-Recommendations

Do not add these to sysctl persistence on this VPS:

```conf
net.core.default_qdisc = fq
net.ipv4.tcp_congestion_control = bbr
net.core.netdev_max_backlog = 250000
net.core.rmem_max = 134217728
net.core.wmem_max = 134217728
net.ipv4.tcp_rmem = 4096 87380 134217728
net.ipv4.tcp_wmem = 4096 65536 134217728
net.ipv4.tcp_max_syn_backlog = 8192
net.ipv4.tcp_tw_reuse = 1
net.ipv4.tcp_fin_timeout = 15
```

Reason:

- These keys were not exposed by this VPS/container kernel surface during audit.
- Persisting unsupported keys creates noisy boot/sysctl reload failures and false confidence.
- The network device is `venet0` with `noqueue`; queue/congestion-control recipes from normal KVM/bare-metal Linux hosts do not map cleanly here.

## 7. Risks

| Risk | Severity | Notes |
|---|---|---|
| Unsupported sysctl persistence | Medium | Boot/reload warnings and misleading evidence if generic tuning recipes are copied. |
| Changing `ip_forward` | High | Current value is `1`; changing it could break VPS/container/Tailscale routing assumptions. |
| Enabling TCP Fast Open | Medium | Requires compatible clients/path; benefit uncertain for 9Router API proxy traffic. |
| Over-tuning keepalive | Medium | Could disrupt long-running streams or add unnecessary probe traffic. |
| qdisc/BBR tuning attempts | Medium | qdisc is `noqueue`, and BBR/congestion-control knobs are not exposed. |
| Swap absence | Medium | 2 workers with high V8 heap on 3.9 GiB RAM can hit hard OOM if memory spikes. This is not a network sysctl issue but should remain in P26 capacity risk tracking. |

## 8. Exact Commands Used for Read-Only Audit

These commands were run or equivalent data was collected through them:

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "uname -a; sed -n '1,12p' /etc/os-release; nproc; free -h"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "ip -br link; ip route show default; tc qdisc show 2>/dev/null || true"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "sysctl net.core.somaxconn net.ipv4.tcp_fastopen net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes net.ipv4.ip_local_port_range net.ipv4.ip_forward net.ipv6.conf.all.disable_ipv6 net.ipv6.conf.default.disable_ipv6 fs.file-max fs.nr_open 2>/dev/null"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "sysctl -a 2>/dev/null | grep -E '^net\\.core\\.|^net\\.ipv4\\.|^net\\.ipv6\\.conf\\.(all|default)\\.'"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "cat /proc/net/sockstat; cat /proc/net/sockstat6 2>/dev/null || true; ss -s"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "systemctl show pm2-root.service --property LimitNOFILE --property LimitNPROC --property FragmentPath --property DropInPaths 2>/dev/null || true"
```

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=10 root@49.12.82.34 \
  "sed -n '1,80p' /etc/sysctl.d/99-9router-hightraffic.conf 2>/dev/null || true"
```

## 9. Exact Commands for Proposed Apply

Do not run automatically. Run only after parent planner/auditor approval.

### Baseline Persistence

If the file ever needs to be recreated:

```bash
cat >/etc/sysctl.d/99-9router-hightraffic.conf <<'EOF'
# P26 9Router high-traffic tuning
# Supported on ninerouter-vps constrained kernel/sysctl surface.
net.core.somaxconn = 4096
EOF
sysctl --system
sysctl net.core.somaxconn
```

### Optional Ephemeral Port Expansion

Only if evidence shows outbound ephemeral port pressure:

```bash
cp -a /etc/sysctl.d/99-9router-hightraffic.conf /etc/sysctl.d/99-9router-hightraffic.conf.bak-$(date +%Y%m%d-%H%M%S)
cat >>/etc/sysctl.d/99-9router-hightraffic.conf <<'EOF'

# Optional P26 outbound fan-out headroom.
net.ipv4.ip_local_port_range = 10240 65535
EOF
sysctl --system
sysctl net.ipv4.ip_local_port_range
```

### Optional Keepalive Policy

Only if stale socket evidence exists:

```bash
cp -a /etc/sysctl.d/99-9router-hightraffic.conf /etc/sysctl.d/99-9router-hightraffic.conf.bak-$(date +%Y%m%d-%H%M%S)
cat >>/etc/sysctl.d/99-9router-hightraffic.conf <<'EOF'

# Optional stale socket cleanup; apply only with socket evidence.
net.ipv4.tcp_keepalive_time = 600
net.ipv4.tcp_keepalive_intvl = 60
net.ipv4.tcp_keepalive_probes = 5
EOF
sysctl --system
sysctl net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes
```

## 10. Rollback Commands

### Roll Back to Baseline File

```bash
cat >/etc/sysctl.d/99-9router-hightraffic.conf <<'EOF'
# P26 9Router high-traffic tuning
# Supported on ninerouter-vps constrained kernel/sysctl surface.
net.core.somaxconn = 4096
EOF
sysctl --system
```

### Roll Back from Timestamped Backup

Use the exact backup created during the apply step:

```bash
cp -a /etc/sysctl.d/99-9router-hightraffic.conf.bak-YYYYMMDD-HHMMSS /etc/sysctl.d/99-9router-hightraffic.conf
sysctl --system
```

### Runtime Verification After Rollback

```bash
sysctl net.core.somaxconn
sysctl net.ipv4.ip_local_port_range net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes 2>/dev/null || true
ss -s
systemctl is-active pm2-root.service
pm2 status
curl -fsS http://127.0.0.1:20128/v1/models >/dev/null && echo "9Router local models endpoint OK"
```

## 11. Verification Plan for Any Future Change

Before change:

```bash
date -Is
sysctl net.core.somaxconn net.ipv4.ip_local_port_range net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes 2>/dev/null || true
ss -s
systemctl show pm2-root.service --property LimitNOFILE --property DropInPaths
curl -fsS http://127.0.0.1:20128/v1/models >/dev/null && echo "precheck OK"
```

After change:

```bash
sysctl --system
sysctl net.core.somaxconn net.ipv4.ip_local_port_range net.ipv4.tcp_keepalive_time net.ipv4.tcp_keepalive_intvl net.ipv4.tcp_keepalive_probes 2>/dev/null || true
ss -s
curl -fsS http://127.0.0.1:20128/v1/models >/dev/null && echo "postcheck OK"
```

Load validation, if parent scope approves:

```bash
hey -n 1000 -c 100 http://127.0.0.1:20128/v1/models
```

Acceptance threshold should stay aligned with prior P26 evidence:

- HTTP errors: `0`.
- 9Router PM2 workers remain online.
- No new service restarts except those explicitly approved for the test plan.
- No firewall, Tailscale, route, provider, endpoint, or secret changes.

## 12. Auditor Verdict

PASS for read-only OS/network research.

Recommended current state:

- Keep `/etc/sysctl.d/99-9router-hightraffic.conf` minimal with `net.core.somaxconn = 4096`.
- Keep PM2 NOFILE persistence via systemd drop-in; it is already present.
- Do not add generic BBR/qdisc/buffer/sysctl recipes to this VPS.
- Consider `net.ipv4.ip_local_port_range = 10240 65535` only if later metrics show outbound ephemeral port pressure.
- Consider TCP keepalive reductions only if stale socket accumulation is proven.

## 13. Boundary Compliance

- No VPS mutation performed.
- No services restarted.
- No firewall rules changed.
- Tailscale was not stopped or modified.
- No secrets printed.
- No non-output repository files edited.
- Output written only to the requested markdown path.

