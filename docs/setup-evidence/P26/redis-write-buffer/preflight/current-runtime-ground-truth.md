# P26.1 Current Runtime Ground Truth

| Field | Value |
|---|---|
| Task | P26.1 9Router Redis Stream Write Buffer / DB Write Offload |
| Scope | Read-only preflight evidence for production 9Router VPS |
| Target host | `root@49.12.82.34 -p 39999` |
| Tailscale IP | `100.104.210.75` |
| Public IPv4 | `49.12.82.34` |
| 9Router endpoint | `http://100.104.210.75:20128/v1` |
| Capture time | `2026-06-28T00:17:49+07:00` |

## Verdict

PASS for read-only preflight.

Production 9Router is healthy before any Redis write-buffer change:

- PM2 is running exactly 2 `9router` workers in cluster mode.
- `tailscaled` is active.
- `http://127.0.0.1:20128/v1/models` returns HTTP 200 on the VPS.
- `http://100.104.210.75:20128/v1/models` returns HTTP 200 from the operator machine.
- `http://49.12.82.34:20128/v1/models` is blocked by firewall and does not expose the app publicly.
- Redis is not installed or active on the 9Router VPS yet.
- SQLite is present at `/var/lib/9router/db/data.sqlite`.

## Observed Runtime State

### PM2

```text
pm2 list -> 2 online 9router workers, cluster mode
pm2 describe 9router -> custom-server.js, cwd /root/9router/.next/standalone
```

### Network

```text
tailscaled -> active
listening -> 0.0.0.0:20128 owned by PM2
firewall -> venet0 DROP for :20128, tailscale0 ACCEPT for :20128
```

### Redis

```text
systemctl is-active redis-server redis valkey -> inactive / inactive / inactive
ss -ltnp -> no 6379 listener
```

### SQLite

```text
canonical DB -> /var/lib/9router/db/data.sqlite
WAL -> active
usageHistory rows -> 8573
usageDaily rows -> 3
requestDetails rows -> 1000
```

## Boundary Notes

- No service restart was performed for this preflight.
- No firewall rule was changed.
- No SQLite write, delete, checkpoint, or vacuum was performed.
- No secrets, raw request bodies, response bodies, or payload blobs were printed.

## Evidence Inputs

- `docs/setup-evidence/P26/redis-write-buffer/research/write-path-inventory.md`
- `docs/setup-evidence/P26/redis-write-buffer/research/sqlite-schema-usage-inventory.md`
- `docs/setup-evidence/P26/redis-write-buffer/research/dashboard-usage-query-analysis.md`
- `docs/setup-evidence/P26/redis-write-buffer/research/deploy-safety-rollback-research.md`

## Footer

This file is the preflight baseline for P26.1. It exists to anchor the later deploy, runtime, and rollback evidence.
