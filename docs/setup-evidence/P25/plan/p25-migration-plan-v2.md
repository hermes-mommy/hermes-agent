# P25 Migration Plan v2 — 9Router to Dedicated VPS (OpenVZ)

> **Document ID:** P25-PLAN-V2-001
> **Date:** 2026-06-26
> **Status:** READY FOR EXECUTION
> **Supersedes:** P25-PLAN-REFRESH-001 (v1 — KVM-assumed design)
> **VPS Provider:** HostData.id NAT 4GB EU NVME (Rp50K/month)
> **Virtualization:** OpenVZ 7
> **OS:** Ubuntu 24.04 LTS
> **Execution:** One-shot by Guinevere

---

## 1. Executive Summary

Migration of local 9Router v0.5.4 (Windows, 92 providers, 11 combos, 1.5 GB SQLite DB) to a new dedicated VPS on HostData.id (OpenVZ 7, Ubuntu 24.04, 2 vCPU / 4 GB RAM / 50 GB NVME).

**Key differences from v1 plan:**
- OpenVZ 7 (not KVM) — systemd cgroup limits may not work
- Root user (not dedicated `nine-router` user)
- Install path: `/root/9router/` (not `/var/lib/9router/`)
- Service name: `ninerouter.service` (not `nine-router.service`)
- SSH via NAT port forwarding (port 39999 → 22)
- Live DB sync (no shutdown) via `sqlite3 .backup` + `scp`
- Hard switch (single endpoint, no fallback)
- Prometheus monitoring on same VPS
- Daily backup to S3 IDCLOUDHOST (7 days retention)
- Stress test load testing (push to breaking point)

**Key constraint:** Local 9Router remains running throughout migration. Rollback = revert `OPENAI_BASE_URL` (<10 detik).

---

## 2. Infrastructure Specifications

| Component | Value |
|---|---|
| **Provider** | HostData.id |
| **Plan** | NAT 4GB EU NVME (Rp50K/month) |
| **Virtualization** | OpenVZ 7 |
| **OS** | Ubuntu 24.04 LTS |
| **CPU** | 2 vCPU |
| **RAM** | 4 GB (no swap) |
| **Disk** | 50 GB NVME |
| **Bandwidth** | 4 TB/month |
| **Network** | NAT IP (shared IPv4: 49.12.82.34) |
| **SSH Port** | 39999 (NAT forwarded → 22) |
| **Tailscale Name** | ninerouter-vps |
| **Timezone** | Asia/Jakarta (WIB) |
| **Auto Updates** | unattended-upgrades enabled |

---

## 3. OpenVZ Adjustments from v1 Plan

| Aspect | v1 Plan (KVM) | v2 Plan (OpenVZ) | Reason |
|---|---|---|---|
| **cgroup limits** | MemoryMax=3584M, MemoryHigh=3072M, CPUQuota=180% | **REMOVED** — test if they work, fallback to no limits | OpenVZ enforces at host level; container cgroups may be ignored |
| **User** | Dedicated `nine-router` user | **Root** | Simpler, single-purpose VPS |
| **Install path** | `/var/lib/9router/` | `/root/9router/` | Root-owned, simpler permissions |
| **Security hardening** | ProtectSystem=strict, PrivateTmp, etc. | **Simplified** — remove directives that don't work on OpenVZ | OpenVZ container limitations |
| **Heap control** | NINEROUTER_NODE_HEAP_MB=2048 | **Same** | Still correct for 9Router v0.5.4 |
| **Performance target** | 1000+ req/min | **500-800 req/min** | OpenVZ shared I/O |

---

## 4. Migration Waves

### Wave 1: VPS Provisioning & Initial Access

**Goal:** VPS ready, SSH accessible, Tailscale joined, Node.js installed.

**Steps:**

1. SSH into VPS via NAT:
   ```bash
   ssh root@49.12.82.34 -p 39999
   ```

2. Update system:
   ```bash
   apt-get update && apt-get upgrade -y
   ```

3. Set timezone:
   ```bash
   timedatectl set-timezone Asia/Jakarta
   ```

4. Install Tailscale:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```

5. Join tailnet:
   ```bash
   tailscale up --hostname=ninerouter-vps
   ```

6. Record Tailscale IP:
   ```bash
   tailscale ip -4
   ```

7. Install Node.js 24.x:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
   apt-get install -y nodejs
   ```

8. Verify:
   ```bash
   node --version   # expect v24.x.x
   npm --version    # expect 11.x.x
   ```

9. Install 9Router:
   ```bash
   npm install -g 9router@0.5.4
   ```

10. Verify:
    ```bash
    9router --version   # expect 0.5.4
    ```

**Exit criteria:** `9router --version` returns `0.5.4`. Tailscale IP recorded. SSH via Tailscale works.

---

### Wave 2: Directory Setup & Environment

**Goal:** Directory structure and environment file ready.

**Steps:**

1. Create directory:
   ```bash
   mkdir -p /root/9router/db/backups
   ```

2. Create environment file `/root/9router/env`:
   ```bash
   cat > /root/9router/env << 'ENVEOF'
   DATA_DIR=/root/9router
   PORT=20128
   HOSTNAME=0.0.0.0
   JWT_SECRET=<REPLACE-WITH-MIGRATED-JWT-SECRET>
   INITIAL_PASSWORD=<SET-SECURE-PASSWORD>
   REQUIRE_API_KEY=false
   ENABLE_REQUEST_LOGS=false
   ENVEOF
   ```

3. Set permissions:
   ```bash
   chmod 600 /root/9router/env
   ```

**Exit criteria:** Directory exists, env file created with correct HOSTNAME=0.0.0.0.

---

### Wave 3: Live Data Migration (No Shutdown)

**Goal:** Transfer SQLite DB, JWT secret, machine-id from local to VPS without stopping local 9Router.

**CRITICAL:** Local 9Router MUST NOT be stopped. Use `sqlite3 .backup` for live copy.

**Steps (run on LOCAL Windows machine):**

1. Export live DB backup:
   ```bash
   sqlite3 "C:\Users\faizz\AppData\Roaming\9router\data\data.sqlite" ".backup 'C:\Users\faizz\AppData\Roaming\9router\data\data-backup.sqlite'"
   ```

2. Copy DB to VPS via Tailscale:
   ```bash
   scp "C:\Users\faizz\AppData\Roaming\9router\data\data-backup.sqlite" root@<vps-tailscale-ip>:/root/9router/db/data.sqlite
   ```

3. Copy JWT secret:
   ```bash
   scp "C:\Users\faizz\AppData\Roaming\9router\data\jwt-secret" root@<vps-tailscale-ip>:/root/9router/jwt-secret
   ```

4. Copy machine-id:
   ```bash
   scp "C:\Users\faizz\AppData\Roaming\9router\data\machine-id" root@<vps-tailscale-ip>:/root/9router/machine-id
   ```

**Steps (run on VPS):**

5. Fix CRLF line endings:
   ```bash
   sed -i 's/\r$//' /root/9router/jwt-secret
   sed -i 's/\r$//' /root/9router/machine-id
   ```

6. Set permissions:
   ```bash
   chmod 600 /root/9router/jwt-secret
   chmod 600 /root/9router/machine-id
   chmod 600 /root/9router/db/data.sqlite
   ```

7. Update env file with actual JWT secret:
   ```bash
   JWT_CONTENT=$(cat /root/9router/jwt-secret)
   sed -i "s|<REPLACE-WITH-MIGRATED-JWT-SECRET>|${JWT_CONTENT}|" /root/9router/env
   ```

8. Verify DB integrity:
   ```bash
   sqlite3 /root/9router/db/data.sqlite "PRAGMA integrity_check"
   ```
   **Expected:** `ok`

9. Verify provider count:
   ```bash
   sqlite3 /root/9router/db/data.sqlite "SELECT COUNT(*) FROM providerConnections"
   ```
   **Expected:** `92`

10. Verify combo count:
    ```bash
    sqlite3 /root/9router/db/data.sqlite "SELECT COUNT(*) FROM combos"
    ```
    **Expected:** `11`

11. Verify JWT secret length:
    ```bash
    wc -c /root/9router/jwt-secret
    ```
    **Expected:** `64`

12. Verify machine-id length:
    ```bash
    wc -c /root/9router/machine-id
    ```
    **Expected:** `64`

13. Verify no CRLF:
    ```bash
    file /root/9router/jwt-secret
    file /root/9router/machine-id
    ```
    **Expected:** Should NOT say "CRLF"

**Exit criteria:** Integrity check `ok`. Provider count = 92. Combo count = 11. Secrets = 64 bytes, no CRLF.

---

### Wave 4: systemd Service Setup

**Goal:** Create systemd service with correct heap configuration.

**Service Unit: `/etc/systemd/system/ninerouter.service`**

```ini
[Unit]
Description=9Router API Gateway
Documentation=https://github.com/9router/9router
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/9router

# ── ENVIRONMENT ──────────────────────────────────────────────────
EnvironmentFile=/root/9router/env

# ── CRITICAL: HEAP CONFIGURATION ─────────────────────────────────
Environment=NINEROUTER_NODE_HEAP_MB=2048

# ── EXECUTION ────────────────────────────────────────────────────
ExecStart=/usr/bin/9router
Restart=on-failure
RestartSec=10
StartLimitBurst=5
StartLimitIntervalSec=60

# ── TIMEOUTS ─────────────────────────────────────────────────────
TimeoutStartSec=180
TimeoutStopSec=30

# ── LOGGING ──────────────────────────────────────────────────────
StandardOutput=journal
StandardError=journal
SyslogIdentifier=ninerouter

[Install]
WantedBy=multi-user.target
```

**Note:** cgroup limits (MemoryMax, MemoryHigh, CPUQuota) REMOVED for OpenVZ. Test if they work after service starts; add back if supported.

**Steps:**

1. Create service file:
   ```bash
   cat > /etc/systemd/system/ninerouter.service << 'EOF'
   [Unit]
   Description=9Router API Gateway
   Documentation=https://github.com/9router/9router
   After=network-online.target
   Wants=network-online.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/root/9router
   EnvironmentFile=/root/9router/env
   Environment=NINEROUTER_NODE_HEAP_MB=2048
   ExecStart=/usr/bin/9router
   Restart=on-failure
   RestartSec=10
   StartLimitBurst=5
   StartLimitIntervalSec=60
   TimeoutStartSec=180
   TimeoutStopSec=30
   StandardOutput=journal
   StandardError=journal
   SyslogIdentifier=ninerouter

   [Install]
   WantedBy=multi-user.target
   EOF
   ```

2. Reload systemd:
   ```bash
   systemctl daemon-reload
   ```

3. Enable service:
   ```bash
   systemctl enable ninerouter.service
   ```

4. Start service:
   ```bash
   systemctl start ninerouter.service
   ```

5. Check status:
   ```bash
   systemctl status ninerouter.service
   ```
   **Expected:** `active (running)`

6. Check logs:
   ```bash
   journalctl -u ninerouter.service -n 50 --no-pager
   ```

**Exit criteria:** Service active and running. Logs show clean startup.

---

### Wave 5: UFW Firewall (Tailscale Only)

**Goal:** Restrict 9Router access to Tailscale-only.

**Steps:**

1. Allow SSH:
   ```bash
   ufw allow 22/tcp comment "SSH"
   ```

2. Allow 9Router on Tailscale interface:
   ```bash
   ufw allow in on tailscale0 to any port 20128 proto tcp comment "9Router Tailscale-only"
   ```

3. Deny 9Router on public:
   ```bash
   ufw deny 20128/tcp comment "9Router deny public"
   ```

4. Enable UFW:
   ```bash
   ufw --force enable
   ```

5. Verify:
   ```bash
   ufw status verbose
   ```

6. Test from local via Tailscale:
   ```bash
   curl -s http://<vps-tailscale-ip>:20128/api/health
   ```
   **Expected:** `{"ok":true}`

**Exit criteria:** Health endpoint reachable via Tailscale. UFW enabled.

---

### Wave 6: Verification

**Goal:** Comprehensive verification of migrated 9Router.

**Checklist:**

- [ ] Health check: `{"ok":true}`
- [ ] Model listing returns models
- [ ] 92 providers active
- [ ] 11 combos available
- [ ] Chat completion works
- [ ] Remote access via Tailscale works
- [ ] Heap correctly set (NINEROUTER_NODE_HEAP_MB=2048 in child process args)
- [ ] Dashboard accessible via Tailscale

**Heap verification:**
```bash
systemctl show ninerouter.service -p Environment | grep NINEROUTER_NODE_HEAP_MB
ps aux | grep 9router | grep max-old-space-size=2048
```

**Exit criteria:** All checks pass.

---

### Wave 7: Client Switch (Hard Switch)

**Goal:** Point clients to VPS 9Router.

**Steps:**

1. Update `OPENAI_BASE_URL` in OpenCode:
   ```
   OPENAI_BASE_URL=http://<vps-tailscale-ip>:20128/v1
   ```

2. Update `OPENAI_BASE_URL` in Claude Code:
   ```
   OPENAI_BASE_URL=http://<vps-tailscale-ip>:20128/v1
   ```

3. Test OpenCode with simple prompt.

4. Test Claude Code with simple prompt.

5. Verify requests appear in VPS logs:
   ```bash
   journalctl -u ninerouter.service -f
   ```

**Exit criteria:** Both clients successfully complete requests through VPS.

---

### Wave 8: Prometheus Monitoring

**Goal:** Prometheus running on VPS, scraping 9Router metrics.

**Steps:**

1. Install Prometheus (TBD — separate document).

2. Configure scrape target for 9Router built-in metrics.

3. Verify metrics endpoint accessible.

**Exit criteria:** Prometheus scraping 9Router metrics successfully.

---

### Wave 9: S3 Backup Setup

**Goal:** Daily backup to S3 IDCLOUDHOST, 7 days retention.

**Steps:**

1. Create backup script `/root/9router/backup.sh`:
   ```bash
   #!/bin/bash
   DATE=$(date +%Y-%m-%d)
   BACKUP_DIR="/root/9router/db/backups"
   S3_BUCKET="<S3_BUCKET_NAME>"
   S3_ENDPOINT="<S3_IDCLOUDHOST_ENDPOINT>"
   S3_ACCESS_KEY="<S3_ACCESS_KEY>"
   S3_SECRET_KEY="<S3_SECRET_KEY>"

   # Live backup
   sqlite3 /root/9router/db/data.sqlite ".backup '${BACKUP_DIR}/data-${DATE}.sqlite'"

   # Upload to S3
   aws s3 cp "${BACKUP_DIR}/data-${DATE}.sqlite" "s3://${S3_BUCKET}/9router-backups/data-${DATE}.sqlite" \
     --endpoint-url "${S3_ENDPOINT}" \
     --access-key "${S3_ACCESS_KEY}" \
     --secret-key "${S3_SECRET_KEY}"

   # Cleanup old backups (keep 7 days)
   find ${BACKUP_DIR} -name "data-*.sqlite" -mtime +7 -delete
   ```

2. Make executable:
   ```bash
   chmod +x /root/9router/backup.sh
   ```

3. Add cron job (daily at 3 AM WIB):
   ```bash
   crontab -e
   # Add: 0 3 * * * /root/9router/backup.sh >> /root/9router/db/backups/backup.log 2>&1
   ```

**Exit criteria:** Backup script runs successfully. S3 upload verified. Cron job scheduled.

---

### Wave 10: Load Test (Stress Test)

**Goal:** Push VPS to breaking point, validate stability.

**Approach:**
1. Mock upstream test first (avoid burning API credits).
2. Sustained load: 1000 req/min for 5 minutes.
3. Push beyond: increase until failure.
4. Record breaking point.

**Pass/Fail thresholds:**
- Error rate < 1% (at target load)
- P95 latency < 5 seconds
- Memory does not exceed 3.5 GB
- No OOM kills in dmesg
- CPU does not sustain > 90% for > 30 seconds

**Post-test checks:**
```bash
journalctl -u ninerouter.service | grep -i error
dmesg | grep -i oom
free -h
```

**Exit criteria:** Load test completed. Breaking point documented. No permanent damage.

---

### Wave 11: 24-Hour Soak

**Goal:** Confirm stability over 24 hours.

**Monitoring:**
- Memory: `free -h` every 4 hours. Flag if RSS > 3 GB.
- CPU: `top -bn1 | grep 9router` every 4 hours. Flag if > 50% sustained.
- Errors: `journalctl -u ninerouter.service --since "1 hour ago"` every 4 hours.
- Health endpoint: `curl http://localhost:20128/api/health` every hour.

**Exit criteria:** No OOM, no crashes, no unexpected errors, health endpoint consistently OK.

---

## 5. Rollback Procedure

**Instant rollback (<10 detik):**

1. Revert `OPENAI_BASE_URL` on clients:
   ```
   OPENAI_BASE_URL=http://localhost:20128/v1
   ```

2. Local 9Router remains running — never stopped during migration.

**Cleanup (optional):**
```bash
# On VPS:
systemctl stop ninerouter.service
systemctl disable ninerouter.service
```

**Rollback triggers:**
- Any wave exit criteria fails
- Health endpoint errors
- Provider/combo count mismatch
- Heap not correctly applied
- OOM kills
- Load test failures
- Soak test anomalies

---

## 6. Hard Constraints (MUST NOT)

| # | Constraint | Reason |
|---|---|---|
| 1 | **MUST NOT** touch Hermes VPS 9Router | Separate production instance |
| 2 | **MUST NOT** stop local 9Router during migration | Rollback depends on it |
| 3 | **MUST NOT** delete local `data.sqlite` before VPS verified | Rollback depends on it |
| 4 | **MUST NOT** skip `NINEROUTER_NODE_HEAP_MB=2048` | OOM risk |
| 5 | **MUST NOT** bind to `127.0.0.1` | Tailscale won't work |
| 6 | **MUST NOT** expose to public internet | UFW deny on non-tailscale0 |
| 7 | **MUST NOT** run load test against real providers at scale | Burns API credits |
| 8 | **MUST NOT** use `NODE_OPTIONS` for heap | Ignored by 9Router child process |
| 9 | **MUST NOT** proceed if provider count != 92 | Incomplete migration |
| 10 | **MUST NOT** commit secrets to repo | JWT secret, machine-id, S3 credentials |

---

## 7. Time Estimate

| Wave | Description | Time | Depends On |
|---|---|---|---|
| 1 | VPS Provisioning | 15-20 min | None |
| 2 | Directory & Environment | 5 min | Wave 1 |
| 3 | Live Data Migration | 10-20 min | Wave 2 |
| 4 | systemd Service | 10 min | Wave 3 |
| 5 | UFW Firewall | 5 min | Wave 4 |
| 6 | Verification | 10-15 min | Wave 5 |
| 7 | Client Switch | 5 min | Wave 6 |
| 8 | Prometheus | 15-30 min | Wave 6 |
| 9 | S3 Backup | 10 min | Wave 6 |
| 10 | Load Test | 15-30 min | Wave 7 |
| 11 | 24-Hour Soak | 24 hours | Wave 10 |
| | **Total active time** | **~90-150 min** | |
| | **Total wall-clock** | **~25-26 hours** | |

---

## 8. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | OOM crash (wrong heap) | High (if NODE_OPTIONS used) | Critical | Use NINEROUTER_NODE_HEAP_MB=2048. Verify child process args. |
| R2 | CRLF corruption | Medium (Windows source) | High | sed -i 's/\r$//'. Verify with `file` command. |
| R3 | Incomplete data migration | Low | Critical | Verify provider count (92) and combo count (11). |
| R4 | Tailscale connectivity failure | Low | High | Test Tailscale IP before proceeding. |
| R5 | Public internet exposure | Low (if UFW skipped) | Critical | UFW rules. Verify deny rule active. |
| R6 | JWT secret mismatch | Low | High | Copy exact bytes, verify 64-byte length. |
| R7 | OpenVZ cgroup limits not working | Medium | Low | Test after service starts. Remove if not supported. |
| R8 | SQLite corruption during transfer | Low | Critical | `PRAGMA integrity_check` in Wave 3. |
| R9 | Disk space exhaustion | Low | High | 50 GB NVME. DB is 1.5 GB, logs grow slowly. |
| R10 | Load test OOM | Medium | Medium | Mock upstream first. Monitor memory in real-time. |
| R11 | Local 9Router stopped accidentally | Low | Critical | DO NOT stop local 9Router. Rollback depends on it. |

---

## 9. Footer

**Related documents:**
- `p25-local-9router-inventory.md` — Local 9Router inventory
- `p25-9router-runtime-node-analysis.md` — Runtime analysis
- `p25-claudecode-opencode-endpoint-wiring.md` — Client endpoint wiring

**Revision history:**

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-06-26 | 2.0 | OpenVZ adjustment | Root user, /root/9router/, ninerouter.service, OpenVZ cgroup removal, live DB sync, Prometheus, S3 backup, hard switch, stress test |
| 2026-06-26 | 1.0 | Ground-truth refresh | Corrected version (0.5.4), heap config, provider count (92), combo count (11) |

---

*End of P25 Migration Plan v2*
