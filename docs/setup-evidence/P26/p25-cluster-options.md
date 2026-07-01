# P26: 9Router Cluster Mode — Options Analysis

**Date**: 2026-06-26  
**Output**: `docs/setup-evidence/P26/p25-cluster-options.md`

---

## 1. Option Matrix

| # | Option | Workers | Tool | Complexity | Risk | Recommendation |
|---|---|---|---|---|---|---|
| 1 | **PM2 cluster** | 2 | PM2 | Low | Low | ✅ RECOMMENDED |
| 2 | Node.js built-in cluster | 2 | `cluster` module | Medium | Medium | Viable |
| 3 | systemd template units | 2 | systemd `@` | High | High | Not recommended |

---

## 2. Option 1: PM2 Cluster (RECOMMENDED)

### How It Works
- PM2 spawns 2 child processes, both listening on port 20128
- PM2 acts as internal load balancer (round-robin)
- `ecosystem.config.js` defines the config

### Configuration
```js
// /root/9router/ecosystem.config.js
module.exports = {
  apps: [{
    name: '9router',
    script: 'custom-server.js',
    cwd: '/root/9router/.next/standalone',
    exec_mode: 'cluster',
    instances: 2,
    node_args: '--max-old-space-size=1792',  // 1.75GB per worker (2×1.75 = 3.5GB)
    env: {
      NODE_ENV: 'production',
      PORT: 20128
    },
    kill_timeout: 10000,
    listen_timeout: 15000,
    max_restarts: 5,
    max_memory_restart: '2G'
  }]
};
```

### Migration Steps
1. Stop systemd service: `systemctl stop 9router`
2. Install PM2: `npm install -g pm2`
3. Kill Apache: `systemctl stop apache2 && systemctl disable apache2` (free ~10MB)
4. Start with PM2: `pm2 start ecosystem.config.js`
5. Save PM2 state: `pm2 save`
6. Enable PM2 startup: `pm2 startup systemd`
7. Verify: `curl -s http://localhost:20128/v1/models | jq '.data | length'`

### Pros
- Zero-downtime reload: `pm2 reload 9router`
- Built-in monitoring: `pm2 monit`
- Log management: `pm2-logrotate`
- Auto-restart on crash
- Widely tested in production

### Cons
- New dependency (pm2 npm package)
- systemd integration is indirect (pm2 → systemd, not systemd → 9router)
- 2 workers each have their own V8 heap (total ~3.5GB, within 3.9GB RAM)

### Rollback
```bash
pm2 stop 9router
pm2 delete 9router
systemctl start 9router  # fall back to systemd
```

---

## 3. Option 2: Node.js Built-in Cluster

### Configuration
```js
// /root/9router/cluster-server.js
const cluster = require('cluster');
const os = require('os');

if (cluster.isMaster) {
  for (let i = 0; i < 2; i++) {
    cluster.fork();
  }
  cluster.on('exit', (worker) => {
    cluster.fork();  // auto-restart
  });
} else {
  require('./custom-server.js');  // or server.js
}
```

### Pros
- No external dependency
- Full control over worker lifecycle
- Direct systemd integration

### Cons
- Custom code needed (not in 9Router source)
- No built-in log management
- No zero-downtime reload
- Higher maintenance burden

---

## 4. Option 3: systemd Template Units

### Configuration
```ini
# /etc/systemd/system/9router@.service
[Service]
Type=simple
WorkingDirectory=/root/9router/.next/standalone
ExecStart=/usr/bin/node custom-server.js
Environment="NODE_OPTIONS=--max-old-space-size=1792"
Environment="PORT=20128"
```

Then run 2 instances: `9router@1`, `9router@2`.

### Cons
- Port conflict: 2 processes can't bind to same port 20128
- Would need reverse proxy (nginx) to split traffic — adds complexity
- NOT recommended for this use case

---

## 5. Multi-Worker Safety Analysis

### SQLite WAL Mode
- ✅ Already enabled: `journal_mode=wal`
- ✅ WAL allows concurrent readers + 1 writer
- ✅ `busy_timeout=5000ms` handles SQLITE_BUSY gracefully
- ⚠️ 2 workers each run their own 60s WAL checkpoint timer (redundant, not harmful)
- ⚠️ Migration race: both workers try to migrate on first start. WeakSet guard per-process only. Fix: run migration once before cluster start

### API Key
- ✅ Stateless HMAC-SHA256 — no session state shared between workers
- ✅ Per-request SQLite lookup — stateless

### Streaming
- ✅ Per-request SSE — stateless, no shared state
- ✅ Each request has its own connection

### JWT
- ✅ JWT_SECRET is a static hash — same across workers
- ✅ No in-memory session store

### Port Binding
- ✅ PM2 handles port sharing automatically (SO_REUSEADDR + cluster module)
- ✅ Both workers listen on 20128, PM2 distributes incoming connections

### Migration Fix
Before starting cluster, run migration once:
```bash
cd /root/9router/.next/standalone
node -e "require('./server.js')" --run-migration-only
```

---

## 6. Heap Allocation

| Config | Per Worker | Total | VPS RAM | Margin |
|---|---|---|---|---|
| Current (single) | 3.5GB | 3.5GB | 3.9GB | 400MB |
| Cluster (2 workers) | 1.75GB | 3.5GB | 3.9GB | 400MB |
| Cluster (conservative) | 1.5GB | 3.0GB | 3.9GB | 900MB |

**Recommendation**: 1.75GB per worker. Under P25 load test, single worker used 1.5GB RAM at 16K requests. 1.75GB gives headroom.

---

## 7. Apache Status

Apache is running on port 80 with 2 processes (~10MB RSS). It serves no purpose on this VPS. Recommendation: **kill Apache** before cluster migration to free RAM.

```bash
systemctl stop apache2
systemctl disable apache2
```

---

## 8. Open Questions for Question Gate

1. **Heap**: 1.75GB per worker (2 × 1.75 = 3.5GB total) or 1.5GB per worker (2 × 1.5 = 3.0GB)?
2. **Apache**: Kill now or during cluster migration?
3. **Migration**: Run migration separately before cluster, or let first worker handle it?
4. **systemd**: Keep systemd service as fallback, or remove after PM2 confirmed?
5. **Load test**: Same 16K req benchmark, or different target?
6. **Logs**: PM2 logrotate (10MB × 10 files) or keep stdout?
7. **Rollback trigger**: What threshold triggers rollback? (errors > 0, CPU > 80%, RAM > 3.5GB?)