# P25 Enterprise-Grade 9Router VPS Migration Plan v3.0

> **Status**: PLAN — Pending Audit  
> **Date**: 2026-06-26  
> **Author**: Guinevere (research synthesis)  
> **Scope**: Full migration of local 9Router to dedicated VPS with enterprise optimizations

---

## 0. Executive Summary

Migrate 9Router v0.5.4 from local Windows to dedicated HostData.id VPS (OpenVZ 7, Ubuntu 24.04, 2 vCPU / 4 GB RAM / 50 GB NVME). Target: sustainable **1000+ req/min** with Prometheus monitoring, S3 backup, and Tailscale-only access.

**Key constraint**: OpenVZ 7 — systemd cgroup limits (MemoryMax, CPUQuota) may not work. Must test on boot.

---

## 1. VPS Specifications

| Attribute | Value |
|---|---|
| Provider | HostData.id NAT 4GB EU NVME |
| Cost | Rp50K/month (Rp600K/year) |
| CPU | 2 vCPU (burst, not guaranteed) |
| RAM | 4 GB (host-enforced limit) |
| Disk | 50 GB NVME (shared) |
| Bandwidth | 4 TB/month |
| Virtualization | OpenVZ 7 |
| IP | NAT (shared IPv4) |
| OS | Ubuntu 24.04 LTS (supported until 2029) |
| SSH | NAT port forwarding (port 39999 → 22) |
| Tailscale | Required (no public internet exposure) |

---

## 2. Critical Research Findings

### 2.1 Memory Leak (BLOCKING — Issue #1245)

9Router has a **confirmed linear memory leak** that grows to 4.8 GB+ over ~3 days. No upstream fix exists.

**Mitigation**: Scheduled process restart every 12 hours via systemd timer.

```ini
# /etc/systemd/system/ninerouter-restart.timer
[Timer]
OnCalendar=*-*-* 03:00:00
OnCalendar=*-*-* 15:00:00
Persistent=true

[Install]
WantedBy=timers.target
```

### 2.2 Node.js v24 Incompatibility (Issue #1469)

`Readable is not defined` error during stream fallback on Node.js v24. **Risk**: User selected NodeSource 24.x.

**Mitigation**: Test 9Router v0.5.4 on Node.js 24 immediately after install. If broken, downgrade to Node.js 22 LTS.

### 2.3 OpenVZ 7 Limitations

| Feature | Works? | Mitigation |
|---|---|---|
| systemd cgroup (MemoryMax, CPUQuota) | ❌ May not work | Test on boot; remove if fails |
| Docker | ❌ No cgroup v2 | Bare metal systemd only |
| BBR congestion control | ❌ Kernel 3.10 | Use cubic (default) |
| TUN/TAP for Tailscale | ⚠️ Must be enabled | Contact provider if missing |
| sysctl tuning | ⚠️ Partial | Tune what works |
| Custom kernel | ❌ | N/A |

### 2.4 SQLite Performance — NOT a Bottleneck

SQLite with WAL mode + PRAGMA tuning handles **3,900+ mixed ops/sec** on a $5 VPS. 1000 req/min = 17 req/sec = **230x headroom**. SQLite is not the bottleneck.

### 2.5 Tailscale — Direct P2P Required

| Mode | Throughput | Latency |
|---|---|---|
| Direct P2P | 200-1000+ Mbps | +1-5ms |
| DERP relay | 2-50 Mbps | +50-200ms |

**Must ensure direct P2P connection**. If DERP fallback triggers, performance drops 20-500x.

### 2.6 No Built-in Prometheus Metrics

9Router has NO `/metrics` endpoint. Custom `prom-client` instrumentation required for enterprise monitoring.

### 2.7 usageHistory Unbounded Growth

At 1000 req/min, `usageHistory` table grows ~1.44M rows/day (~1.4 GB/day). **Must add pruning cron**.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│                    Windows (Local)                       │
│                                                         │
│  OpenCode ──→ Tailscale ──→ VPS 9Router                │
│  Claude Code ──→ Tailscale ──→ VPS 9Router             │
│                                                         │
│  Local 9Router: STOPPED (kept as rollback)              │
└─────────────────────────────┬───────────────────────────┘
                              │ Tailscale (encrypted P2P)
                              ▼
┌─────────────────────────────────────────────────────────┐
│              HostData.id VPS (OpenVZ 7)                  │
│  Ubuntu 24.04, 2 vCPU, 4 GB RAM, 50 GB NVME           │
│                                                         │
│  ┌──────────────┐  ┌────────────┐  ┌──────────────┐   │
│  │ 9Router      │  │ Prometheus │  │ Grafana      │   │
│  │ :20128       │  │ :9090      │  │ :3000        │   │
│  │ Node.js 24   │  │ Scrape 15s │  │ Dashboards   │   │
│  │ 2048 MB heap │  │ 30d retain │  │              │   │
│  └──────────────┘  └────────────┘  └──────────────┘   │
│                                                         │
│  ┌──────────────┐  ┌────────────┐                      │
│  │ node_exporter│  │ Backup Cron│                      │
│  │ :9100        │  │ Daily → S3 │                      │
│  └──────────────┘  └────────────┘                      │
│                                                         │
│  UFW: deny all except Tailscale                         │
│  Tailscale: auth-only access                            │
└─────────────────────────────────────────────────────────┘
```

---

## 4. RAM Budget (4 GB)

| Component | Allocation | Notes |
|---|---|---|
| OS + system | 500 MB | Ubuntu baseline |
| 9Router (heap) | 2048 MB | NINEROUTER_NODE_HEAP_MB=2048 |
| 9Router (RSS overhead) | ~300 MB | Beyond heap: C++ addons, buffers |
| Prometheus | 512 MB | ~1000 active series, 30d retention |
| Grafana | 256 MB | Dashboard rendering |
| node_exporter | 32 MB | System metrics |
| Tailscale | 64 MB | VPN daemon |
| **Total** | **~3.7 GB** | **~300 MB headroom** |

---

## 5. Migration Waves

### Wave 1: VPS Provisioning (~15 min)

1. Purchase HostData.id NAT 4GB EU NVME
2. Configure server form:
   - Hostname: `ninerouter-vps`
   - Root Password: generate 16+ char strong password
   - NS1/NS2: default
   - OS: Ubuntu 24.04
   - All checkboxes: ✅
3. Create Domain Forwarding rule: TCP, source port 39999, destination port 22
4. Wait for provisioning email
5. SSH test: `ssh root@<nat-public-ip> -p 39999`

**Exit criteria**: SSH access confirmed, `uname -a` shows Ubuntu 24.04.

### Wave 2: System Preparation (~20 min)

```bash
# Update system
apt update && apt upgrade -y

# Install essentials
apt install -y curl wget git sqlite3 ufw unattended-upgrades

# Node.js 24.x via NodeSource
curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
apt install -y nodejs

# Verify
node -v  # Should show v24.x
npm -v

# Timezone
timedatectl set-timezone Asia/Jakarta

# Auto-updates
dpkg-reconfigure -plow unattended-upgrades  # Select Yes
```

**OpenVZ-specific test** (CRITICAL):

```bash
# Test if cgroup limits work
systemctl set-property system.slice MemoryMax=3G
systemctl show system.slice | grep MemoryMax
# If MemoryMax=infinity or empty → cgroup limits don't work
# Record result for systemd service config

# Test TUN/TAP
ls /dev/net/tun
# If missing → contact provider to enable TUN/TAP (required for Tailscale)

# Test sysctl tuning
sysctl -w net.core.somaxconn=65535 2>/dev/null && echo "somaxconn OK" || echo "somaxconn BLOCKED"
sysctl -w net.core.rmem_max=16777216 2>/dev/null && echo "rmem OK" || echo "rmem BLOCKED"
```

**Exit criteria**: Node.js installed, timezone set, OpenVZ capabilities tested and recorded.

### Wave 3: Tailscale Setup (~10 min)

```bash
# Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# Start and authenticate
tailscale up --hostname=ninerouter-vps --authkey=<AUTH_KEY>

# Verify
tailscale status  # Should show ninerouter-vps
tailscale ip -4   # Get Tailscale IP (100.x.y.z)

# Test P2P connection (from Windows)
# On Windows: tailscale ping ninerouter-vps
# Should show "pong from ninerouter-vps via DERP(xxx)" initially, then direct IP

# Ensure direct P2P (not DERP)
tailscale netcheck  # Check preferred DERP region
```

**Exit criteria**: Tailscale connected, `tailscale ping` shows direct P2P (not DERP).

### Wave 4: 9Router Installation (~15 min)

```bash
# Install 9Router globally
npm install -g 9router@0.5.4

# Create data directory
mkdir -p /root/9router
chmod 700 /root/9router

# Verify install
9router --version  # Should show 0.5.4
```

**Exit criteria**: `9router --version` returns 0.5.4.

### Wave 5: Live DB Sync (~30 min for 1.5 GB)

**On Windows (local)**:

```powershell
# Step 1: Live backup (NO shutdown needed)
sqlite3 "C:\Users\faizz\AppData\Roaming\9router\data.sqlite" ".backup 'C:\Users\faizz\guinevere\temp\data.sqlite.bak'"

# Step 2: Export secrets
type "C:\Users\faizz\AppData\Roaming\9router\jwt-secret"
type "C:\Users\faizz\AppData\Roaming\9router\machine-id"

# Step 3: Export API keys from DB (all providers with real keys)
sqlite3 "C:\Users\faizz\AppData\Roaming\9router\data.sqlite" "SELECT id, apiKey FROM providers WHERE apiKey != '' AND apiKey != 'placeholder';" > C:\Users\faizz\guinevere\temp\provider-keys.txt

# Step 4: SCP to VPS via Tailscale
scp -P 39999 "C:\Users\faizz\guinevere\temp\data.sqlite.bak" root@<nat-public-ip>:/root/9router/data.sqlite
```

**On VPS**:

```bash
# Step 5: Place files
cp /root/9router/data.sqlite /root/9router/data.sqlite.original  # backup

# Step 6: Set secrets (copy exact values from local)
echo -n "<JWT_SECRET_VALUE>" > /root/9router/jwt-secret
echo -n "<MACHINE_ID_VALUE>" > /root/9router/machine-id

# Step 7: Fix line endings (CRLF → LF)
sed -i 's/\r$//' /root/9router/jwt-secret
sed -i 's/\r$//' /root/9router/machine-id

# Step 8: Verify DB integrity
sqlite3 /root/9router/data.sqlite "PRAGMA integrity_check;"
# Should return: ok

# Step 9: Verify data
sqlite3 /root/9router/data.sqlite "SELECT COUNT(*) FROM providers;"
sqlite3 /root/9router/data.sqlite "SELECT COUNT(*) FROM combos;"
# Should match local counts
```

**Exit criteria**: DB integrity check passes, provider/combo counts match local.

### Wave 6: systemd Service (~10 min)

**IMPORTANT**: Adapt based on Wave 2 OpenVZ test results. If cgroup limits don't work, remove MemoryHigh/MemoryMax/CPUQuota lines.

```ini
# /etc/systemd/system/ninerouter.service
[Unit]
Description=9Router AI Gateway
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/9router

# CRITICAL: Use NINEROUTER_NODE_HEAP_MB, NOT NODE_OPTIONS
Environment=NINEROUTER_NODE_HEAP_MB=2048
Environment=DATA_DIR=/root/9router
Environment=NODE_ENV=production
Environment=PORT=20128

ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update

Restart=always
RestartSec=5

# Resource limits (REMOVE IF OpenVZ DOESN'T SUPPORT)
MemoryHigh=3584M
MemoryMax=3840M
CPUQuota=180%

# File descriptors
LimitNOFILE=65536

# Security (REMOVE IF OpenVZ DOESN'T SUPPORT)
ProtectSystem=strict
PrivateTmp=true
NoNewPrivileges=true
ReadWritePaths=/root/9router

# Health check
ExecStartPost=/bin/bash -c 'for i in $(seq 1 30); do curl -sf http://127.0.0.1:20128/api/health && exit 0; sleep 1; done; exit 1'

[Install]
WantedBy=multi-user.target
```

```ini
# /etc/systemd/system/ninerouter-restart.timer
[Unit]
Description=9Router Scheduled Restart (Memory Leak Mitigation)

[Timer]
OnCalendar=*-*-* 03:00:00 Asia/Jakarta
OnCalendar=*-*-* 15:00:00 Asia/Jakarta
Persistent=true

[Install]
WantedBy=timers.target
```

```ini
# /etc/systemd/system/ninerouter-restart.service
[Unit]
Description=Restart 9Router (scheduled)

[Service]
Type=oneshot
ExecStart=/usr/bin/systemctl restart ninerouter.service
```

```bash
# Enable and start
systemctl daemon-reload
systemctl enable --now ninerouter.service
systemctl enable --now ninerouter-restart.timer

# Verify
systemctl status ninerouter.service
curl http://127.0.0.1:20128/api/health
```

**Exit criteria**: Service running, health check returns `{"ok":true}`, timer active.

### Wave 7: Firewall (~5 min)

```bash
# UFW: deny all, allow only Tailscale
ufw default deny incoming
ufw default allow outgoing

# Get Tailscale interface
TAILSCALE_IFACE=$(ip route show | grep "100.64" | awk '{print $3}')
ufw allow in on $TAILSCALE_IFACE

# Allow SSH via NAT port (from host, not container — may not apply)
# ufw allow 22/tcp  # Skip if NAT handles this at host level

ufw enable
ufw status verbose
```

**Exit criteria**: `ufw status` shows deny-all with Tailscale exception only.

### Wave 8: Monitoring Stack (~20 min)

```bash
# Install Prometheus
apt install -y prometheus prometheus-node-exporter

# Configure Prometheus scrape
cat > /etc/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  scrape_timeout: 10s
  evaluation_interval: 15s

scrape_configs:
  - job_name: '9router'
    static_configs:
      - targets: ['localhost:20128']
    metrics_path: '/metrics'
    scrape_interval: 15s

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['localhost:9100']
    scrape_interval: 30s
EOF

# Tune Prometheus for 4GB VPS
mkdir -p /etc/default
cat > /etc/default/prometheus << 'EOF'
ARGS="--storage.tsdb.retention.time=30d --storage.tsdb.retention.size=2GB --storage.tsdb.wal-compression --web.enable-lifecycle"
EOF

# Install Grafana
apt install -y apt-transport-https software-properties-common
wget -q -O /usr/share/keyrings/grafana.key https://apt.grafana.com/gpg.key
echo "deb [signed-by=/usr/share/keyrings/grafana.key] https://apt.grafana.com stable main" > /etc/apt/sources.list.d/grafana.list
apt update && apt install -y grafana

# Enable services
systemctl enable --now prometheus prometheus-node-exporter grafana-server

# Verify
curl http://127.0.0.1:9090/-/healthy
curl http://127.0.0.1:9100/metrics | head -5
```

**Note**: 9Router has no `/metrics` endpoint. Grafana can use 9Router's `/api/usage/stats` as a JSON data source, or we add prom-client instrumentation later.

**Exit criteria**: Prometheus scraping, node_exporter metrics flowing, Grafana accessible via Tailscale.

### Wave 9: Backup System (~15 min)

```bash
# Install dependencies
apt install -y zstd awscli

# Create backup script
cat > /root/9router/backup.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

BACKUP_DIR="/tmp/9router-backup"
S3_BUCKET="<S3_BUCKET_NAME>"
S3_ENDPOINT="https://is3.cloudhost.id"
DATE=$(date +%Y%m%d-%H%M%S)
DB_PATH="/root/9router/data.sqlite"

mkdir -p "$BACKUP_DIR"

# Live backup (safe, no shutdown needed)
sqlite3 "$DB_PATH" ".backup '$BACKUP_DIR/data.sqlite'"

# Compress with zstd (level 3: best speed/ratio balance)
zstd -3 "$BACKUP_DIR/data.sqlite" -o "$BACKUP_DIR/data-$DATE.sqlite.zst"

# Upload to S3
AWS_ACCESS_KEY_ID=<KEY> AWS_SECRET_ACCESS_KEY=<SECRET> \
  aws s3 cp "$BACKUP_DIR/data-$DATE.sqlite.zst" \
  "s3://$S3_BUCKET/9router/data-$DATE.sqlite.zst" \
  --endpoint-url "$S3_ENDPOINT"

# Retention: delete backups older than 7 days
aws s3 ls "s3://$S3_BUCKET/9router/" --endpoint-url "$S3_ENDPOINT" | \
  awk '{print $NF}' | sort -r | tail -n +8 | \
  while read f; do
    AWS_ACCESS_KEY_ID=<KEY> AWS_SECRET_ACCESS_KEY=<SECRET> \
      aws s3 rm "s3://$S3_BUCKET/9router/$f" --endpoint-url "$S3_ENDPOINT"
  done

# Cleanup
rm -rf "$BACKUP_DIR"

echo "Backup complete: data-$DATE.sqlite.zst"
SCRIPT

chmod +x /root/9router/backup.sh

# Daily cron
cat > /etc/cron.d/9router-backup << 'CRON'
0 2 * * * root /root/9router/backup.sh >> /var/log/9router-backup.log 2>&1
CRON
```

**Exit criteria**: Manual backup test succeeds, file appears in S3, cron registered.

### Wave 10: usageHistory Pruning (~5 min)

```bash
# Create pruning script
cat > /root/9router/prune-usage.sh << 'SCRIPT'
#!/bin/bash
set -euo pipefail

DB_PATH="/root/9router/data.sqlite"
RETAIN_DAYS=7

sqlite3 "$DB_PATH" "DELETE FROM usageHistory WHERE timestamp < datetime('now', '-$RETAIN_DAYS days');"
sqlite3 "$DB_PATH" "VACUUM;"
sqlite3 "$DB_PATH" "PRAGMA optimize;"

echo "Pruned usageHistory older than $RETAIN_DAYS days"
SCRIPT

chmod +x /root/9router/prune-usage.sh

# Weekly cron
cat > /etc/cron.d/9router-prune << 'CRON'
0 4 * * 0 root /root/9router/prune-usage.sh >> /var/log/9router-prune.log 2>&1
CRON
```

**Exit criteria**: Pruning script runs, reduces DB size, cron registered.

### Wave 11: Verification & Stress Test (~60 min)

**Functional verification**:

```bash
# From Windows via Tailscale
curl http://<TAILSCALE_IP>:20128/api/health
curl http://<TAILSCALE_IP>:20128/v1/models  # Should show 24+ models

# Test chat completion (via OpenCode or direct curl)
curl http://<TAILSCALE_IP>:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-4o-mini","messages":[{"role":"user","content":"Hi"}],"stream":false}'
```

**Stress test** (push to breaking point):

```bash
# Install k6 on VPS
apt install -y k6

# Create load test script
cat > /root/9router/stress-test.js << 'K6SCRIPT'
import http from 'k6/http';
import { check, sleep } from 'k6';

export const options = {
  stages: [
    { duration: '2m', target: 50 },    // Ramp to 50 VUs
    { duration: '5m', target: 100 },   // Ramp to 100 VUs
    { duration: '5m', target: 200 },   // Ramp to 200 VUs
    { duration: '5m', target: 500 },   // Push to 500 VUs
    { duration: '2m', target: 0 },     // Ramp down
  ],
};

const BASE_URL = 'http://127.0.0.1:20128';

export default function () {
  const res = http.post(`${BASE_URL}/v1/chat/completions`, JSON.stringify({
    model: 'gpt-4o-mini',
    messages: [{ role: 'user', content: 'Say hello in 5 words' }],
    max_tokens: 20,
    stream: false,
  }), {
    headers: { 'Content-Type': 'application/json' },
    timeout: '30s',
  });

  check(res, {
    'status 200': (r) => r.status === 200,
    'has response': (r) => r.json('choices[0].message.content') !== undefined,
  });

  sleep(0.5);
}
K6SCRIPT

# Run stress test
k6 run /root/9router/stress-test.js

# Monitor during test
watch -n 1 'systemctl status ninerouter.service && free -m && cat /proc/loadavg'
```

**Record results**: Max sustainable RPS, p99 latency, memory growth rate, first failure point.

**Exit criteria**: Stress test complete, results documented, no service crash.

### Wave 12: Client Switch (~5 min)

**OpenCode** (primary client):

```bash
# On Windows — update OpenCode config
# Change OPENAI_BASE_URL from localhost:20128 to <TAILSCALE_IP>:20128
# Restart OpenCode session

# Verify
# Send a chat completion through OpenCode
```

**Claude Code** (secondary client):

```bash
# Same — update OPENAI_BASE_URL to <TAILSCALE_IP>:20128
```

**Exit criteria**: Both clients successfully complete chat via VPS 9Router.

### Wave 13: Stop Local 9Router (~5 min)

```powershell
# On Windows — stop local 9Router (keep installed as rollback)
# Stop the process/service
# DO NOT uninstall — keep for instant rollback
```

**Exit criteria**: Local 9Router stopped, VPS is sole active endpoint.

---

## 6. Rollback Plan

| Trigger | Action | Time |
|---|---|---|
| VPS unreachable | Revert OPENAI_BASE_URL to localhost | <10 sec |
| VPS performance bad | Revert + investigate | <10 sec |
| DB corruption | Restore from S3 backup | <15 min |
| Memory leak OOM | Auto-restart by systemd | ~5 sec |
| Tailscale DERP fallback | Restart Tailscale on both ends | ~30 sec |

---

## 7. Post-Migration Optimization Roadmap

### Phase 2 (Week 1-2): Monitoring

1. Add prom-client instrumentation to 9Router (custom `/metrics` endpoint)
2. Create Grafana dashboards (request rate, latency, provider errors, memory)
3. Set up alerting rules (high error rate, memory growth, service down)
4. Monitor memory leak rate — adjust restart timer if needed

### Phase 2 (Week 2-4): Performance

1. Tune SQLite PRAGMAs (cache_size, mmap_size, temp_store)
2. Tune TCP buffers (if sysctl allows on OpenVZ)
3. Add usageHistory pruning monitoring
4. Benchmark actual throughput vs stress test results

### Phase 3 (Month 2+): Scaling

1. Evaluate if single instance is sufficient
2. If needed: PM2 cluster mode (2 instances on 2 cores)
3. If needed: nginx reverse proxy in front of instances
4. Evaluate KVM upgrade when budget allows

---

## 8. OpenVZ Risk Register

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| cgroup limits don't work | High | Medium | Test in Wave 2, adapt systemd |
| TUN/TAP not enabled | Medium | High | Contact provider, or use SSH tunnel |
| CPU overselling (noisy neighbor) | High | Medium | Monitor steal%, request migration if >5% |
| Shared IOPS contention | Medium | Low | 9Router is I/O light (SQLite only) |
| Tailscale DERP fallback | Low | High | Test direct P2P in Wave 3, monitor |
| Node.js v24 stream bug | Medium | High | Test immediately, fallback to v22 LTS |

---

## 9. Success Criteria

| Metric | Target | Measurement |
|---|---|---|
| Availability | 99.9% (43 min downtime/month max) | Prometheus up metric |
| Throughput | 1000+ req/min sustained | k6 stress test |
| p50 latency | <5s (including upstream) | Prometheus histogram |
| p99 latency | <30s (including upstream) | Prometheus histogram |
| Memory | Stable (restart controls leak) | node_exporter RSS |
| Backup | Daily, verified | Cron log + S3 listing |
| Security | Tailscale-only, no public exposure | UFW status |

---

## 10. Cost Summary

| Item | Monthly | Annual |
|---|---|---|
| HostData.id VPS | Rp50,000 | Rp600,000 |
| S3 backup (IDCLOUDHOST) | ~Rp2,500 (~$0.25) | ~Rp30,000 |
| **Total** | **~Rp52,500** | **~Rp630,000** |

---

## 11. Files to Create (Execution Checklist)

- [ ] `/etc/systemd/system/ninerouter.service`
- [ ] `/etc/systemd/system/ninerouter-restart.timer`
- [ ] `/etc/systemd/system/ninerouter-restart.service`
- [ ] `/root/9router/backup.sh`
- [ ] `/root/9router/prune-usage.sh`
- [ ] `/root/9router/stress-test.js`
- [ ] `/etc/prometheus/prometheus.yml`
- [ ] `/etc/default/prometheus`
- [ ] `/etc/cron.d/9router-backup`
- [ ] `/etc/cron.d/9router-prune`
- [ ] UFW rules
- [ ] Tailscale configuration

---

## 12. Appendix: Environment Variables

| Variable | Value | Purpose |
|---|---|---|
| NINEROUTER_NODE_HEAP_MB | 2048 | V8 heap limit (MB) |
| DATA_DIR | /root/9router | Data directory |
| NODE_ENV | production | Production mode |
| PORT | 20128 | HTTP port |
| JWT_SECRET | (from local) | Dashboard auth |

---

## 13. Version History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-06-26 | Initial plan (KVM-based) |
| 2.0 | 2026-06-26 | OpenVZ adjustments, all user decisions |
| 3.0 | 2026-06-26 | Enterprise-grade: 8 research findings integrated |
