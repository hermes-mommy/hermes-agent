# P26: 9Router PM2 Cluster — Evidence

**Date**: 2026-06-26  
**Status**: COMPLETE

---

## What Was Done

Converted 9Router from single systemd service to PM2 cluster mode with 2 workers.

## Files Changed

| File | Change |
|---|---|
| `/root/9router/ecosystem.config.js` | Created — PM2 cluster config (2 workers, 1.8GB heap each) |
| `/etc/systemd/system/9router.service` | Stopped + disabled (kept as fallback) |
| PM2 dump | `/root/.pm2/dump.pm2` — auto-saved |
| `/etc/systemd/system/pm2-root.service` | Created — PM2 startup |

## ecosystem.config.js

```javascript
module.exports = {
  apps: [{
    name: '9router-vps',
    script: 'custom-server.js',
    cwd: '/root/9router/.next/standalone',
    exec_mode: 'cluster',
    instances: 2,
    node_args: '--max-old-space-size=1843',
    env_file: '/var/lib/9router/.env',
    max_memory_restart: '1900M',
    autorestart: true,
    max_restarts: 10,
    kill_timeout: 5000,
    listen_timeout: 30000,
    wait_ready: false,
    log_date_format: 'YYYY-MM-DD HH:mm:ss Z',
    error_file: '/root/.pm2/logs/9router-vps-error.log',
    out_file: '/root/.pm2/logs/9router-vps-out.log',
    merge_logs: true,
    instance_var: 'INSTANCE_ID'
  }]
};
```

## Verification Results

| Metric | Value |
|---|---|
| PM2 status | 2 workers online, 0 restarts |
| Worker count | 2 (PID 25397, 25404) |
| RAM/worker | 131MB / 130MB |
| Heap/worker | 1.8GB (max) |
| /v1/models | Returns all 74 models ✅ |
| 9Router version | v0.5.8 |
| Uptime | 35min+ |
| PM2 startup | pm2-root systemd enabled |
| pm2-logrotate | 10MB max, retain 10, compress |
| systemd 9router | inactive + disabled (fallback) |

## Rollback Path

```
systemctl enable 9router --now
pm2 delete 9router-vps
```

## PM2 Commands

| Command | Purpose |
|---|---|
| `pm2 status` | Check workers |
| `pm2 logs 9router-vps` | View logs |
| `pm2 restart 9router-vps` | Restart all workers |
| `pm2 reload 9router-vps` | Zero-downtime reload |
| `pm2 save` | Save current state |
| `pm2 startup` | Auto-start on boot |

## Multi-Worker Safety

| Concern | Status |
|---|---|
| SQLite WAL | ✅ journal_mode=wal |
| API key | ✅ Stateless HMAC-SHA256 |
| Streaming | ✅ Per-request SSE |
| Migration race | ✅ WeakSet guard |
| Memory | ✅ 1.9GB restart ceiling |

## Design Decisions

- PM2 cluster over Node cluster (process management, logging, auto-restart)
- 2 workers (1 per CPU core, 2 cores total)
- wait_ready: false (9Router has no `process.send('ready')`)
- systemd kept disabled as fallback (not deleted)
- Apache not touched (Faiz said skip)
- No load test (Faiz said skip)

## Caveats

- SQLITE_BUSY possible under high write load (not expected for single-user)
- PM2 restart clears pm2 dump — must `pm2 save` after any config change
- 9Router systemd service preserved at `/etc/systemd/system/9router.service` (disabled)