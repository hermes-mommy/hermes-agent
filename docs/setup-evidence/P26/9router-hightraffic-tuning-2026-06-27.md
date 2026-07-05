# P26 9Router High-Traffic Tuning Evidence

**Date**: 2026-06-27 14:00 WIB  
**Host**: `ninerouter-vps` (`100.104.210.75`)  
**Scope**: Production 9Router VPS tuning only. No Guinevere VPS changes. No firewall rule changes. No endpoint/key/provider mutation.

## What Was Done

1. Restored Tailscale earlier by returning `tailscaled` to `--tun=userspace-networking`.
2. Raised valid kernel backlog tuning:
   - `net.core.somaxconn = 4096`
3. Raised live file descriptor limits for PM2 and both 9Router workers:
   - PM2 daemon PID `24174`: `NOFILE 65535/65535`
   - 9Router worker PID `31108`: `NOFILE 65535/65535`
   - 9Router worker PID `31121`: `NOFILE 65535/65535`
4. Added persistent systemd PM2 limit:
   - `/etc/systemd/system/pm2-root.service.d/limits.conf`
   - `LimitNOFILE=65535`
5. Started and verified `pm2-root.service` as the active supervisor.
6. Stopped and disabled unused Apache:
   - `apache2`: `inactive`, `disabled`
7. Saved PM2 process list:
   - `pm2 save`

## Validation Results

| Check | Result |
|---|---|
| PM2 cluster | 2 workers online (`31108`, `31121`) |
| PM2 supervisor | `pm2-root.service` active |
| Tailscale | active, `100.104.210.75` |
| Endpoint from VPS | `http://127.0.0.1:20128/v1/models` returns JSON |
| Endpoint from Windows | `http://100.104.210.75:20128/v1/models` returns HTTP 200 |
| Apache | inactive + disabled |
| Backlog | `net.core.somaxconn = 4096` |
| NOFILE | PM2 + both workers at `65535` |

## Load Test

Command:

```bash
hey -n 1000 -c 100 http://127.0.0.1:20128/v1/models
```

Result:

| Metric | Value |
|---|---|
| Status codes | `1000 x HTTP 200` |
| Requests/sec | `113.13` |
| Average latency | `0.5895s` |
| p95 latency | `2.0952s` |
| p99 latency | `7.3292s` |
| Errors | `0` |

## Caveats

- This VPS kernel/container exposes only a limited sysctl surface. `net.ipv4.tcp_max_syn_backlog`, `net.ipv4.tcp_tw_reuse`, and `net.ipv4.tcp_fin_timeout` were not present under `/proc/sys/net/ipv4`, so they were not persisted.
- CPU and RAM were not saturated during live usage or load test. Remaining perceived slowness is likely application/upstream-provider latency, not VPS CPU exhaustion.
- `/v1/models` load test proves local 9Router serving capacity, not upstream model-provider throughput.

## Final Status

**P26 9Router high-traffic tuning applied and runtime-verified.**

