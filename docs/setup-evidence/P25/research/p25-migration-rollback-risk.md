# P25 — 9Router Migration & Rollback Risk Report

> **Author:** Guinevere Research Agent  
> **Date:** 2026-06-25  
> **Scope:** Migration of local Windows 9Router (v0.4.71) to a dedicated Ubuntu 24.04 VPS  
> **Status:** RESEARCH COMPLETE — awaiting operator approval

---

## 1. Executive Summary

This report analyses the risks, mitigations, and rollback procedures for migrating the local Windows 9Router instance (v0.4.71, 1.5 GB SQLite, 6 combos, 2 provider connections, 24 models) to a new dedicated VPS (Ubuntu 24.04, 2 vCPU / 4 GB RAM, Tailscale-only networking, systemd-managed).

**Key findings:**

- The migration is **low-risk overall** thanks to SQLite's platform-independent binary format and the simplicity of the rollback path (switch one environment variable back to localhost).
- The **highest-impact risks** are provider key mismatch and network reachability (Tailscale / UFW), both of which are caught by pre-migration verification gates before any client is switched.
- **Rollback is under 1 minute**: stop the VPS service, set `OPENAI_BASE_URL=http://localhost:20128/v1` on the local machine, and confirm the local 9Router health endpoint.
- The Hermes production VPS (guinevere-vps, guinevere-9router.service, guinevere-core.service) is **completely out of scope** and must not be touched.
- The local data.sqlite must not be deleted until the VPS has been verified in production for at least 24 hours.

**Recommendation:** Proceed with migration after completing the pre-migration checklist (Section 7). The risk profile is acceptable for a single-operator development environment.

---

## 2. Risk Matrix

| # | Risk | Likelihood | Impact | Severity | Mitigation Status |
|---|------|-----------|--------|----------|-------------------|
| 1 | Database migration failure | LOW | HIGH | MEDIUM | Mitigated — file copy + integrity check |
| 2 | Provider key mismatch | MEDIUM | HIGH | HIGH | Mitigated — SQLite copy preserves keys, verified by models endpoint |
| 3 | Version mismatch (0.4.71 vs 0.4.66) | LOW | MEDIUM | LOW | Mitigated — 9Router auto-migrates schema, backup before upgrade |
| 4 | CRLF line-ending corruption | MEDIUM | MEDIUM | MEDIUM | Mitigated — sed fix + hex verification |
| 5 | Port conflict on new VPS | LOW | LOW | LOW | Mitigated — ss check before start |
| 6 | Tailscale not configured | LOW | HIGH | MEDIUM | Mitigated — tailscale status + ip -4 verification |
| 7 | UFW blocks access | MEDIUM | HIGH | HIGH | Mitigated — explicit allow rule before testing |
| 8 | Memory exhaustion (OOM) | LOW | HIGH | MEDIUM | Mitigated — systemd MemoryMax + monitoring |
| 9 | SQLite WAL corruption | VERY LOW | HIGH | LOW | Mitigated — do not copy WAL/SHM, integrity check |
| 10 | Usage history table growth | HIGH | MEDIUM | MEDIUM | Post-migration concern — pruning cron job |

**Severity key:** LOW = accept as-is; MEDIUM = mitigated and monitored; HIGH = requires active mitigation before proceeding.

---

## 3. Detailed Risk Analysis

### 3.1 Risk 1 — Database Migration Failure

**Description:** The 1.5 GB SQLite database file fails to copy correctly, is truncated, or becomes corrupted during transfer.

**Likelihood:** LOW. SQLite is a single self-contained binary file. File-level copy (scp, rsync) is the recommended migration method for SQLite. There is no SQL dump/restore step that could introduce encoding errors.

**Impact:** HIGH. Without a valid database, the 9Router has no combo definitions, no provider connections, and no API keys. All LLM access for coding tools (Claude Code, OpenCode) would be unavailable.

**Mitigation:**
1. Copy `data.sqlite` as a raw file — never use `.dump`/restore.
2. Run `sqlite3 data.sqlite "PRAGMA integrity_check;"` on the source before copy.
3. Run the same integrity check on the destination after copy.
4. Keep the local 9Router running throughout migration as a hot fallback.
5. Do NOT delete the local `data.sqlite` until the VPS instance has been verified working for at least 24 hours.

**Residual risk:** Negligible. The integrity check is a hard gate; if it fails, stop and retry the copy.

---

### 3.2 Risk 2 — Provider Key Mismatch

**Description:** The VPS 9Router does not have valid API keys, causing all LLM API calls to fail with 401/403 errors.

**Likelihood:** MEDIUM. The local 9Router has real API keys embedded in its SQLite database. The Hermes production VPS 9Router (v0.4.66) has placeholder keys. If the wrong database is copied, or if the provider_connections table is empty, all calls fail.

**Impact:** HIGH. Complete loss of LLM access. Claude Code and OpenCode cannot function.

**Mitigation:**
1. The SQLite file copy preserves all provider keys — no manual re-entry needed.
2. After migration, verify with:
   ```bash
   curl -s http://<tailscale-ip>:20128/v1/models | jq '.data | length'
   ```
   Expect: 24 models returned.
3. Test a real chat completion before switching any client endpoints.
4. If models endpoint returns 0 or an error, stop — do not proceed.

**Residual risk:** Low. The models endpoint check is a hard gate.

---

### 3.3 Risk 3 — Version Mismatch

**Description:** The local 9Router is v0.4.71, but the latest published version on npmjs.com is v0.4.66. Installing v0.4.66 on the VPS may trigger schema migration or introduce behavioral differences.

**Likelihood:** LOW. 9Router has built-in schema migration that runs on startup using SQLite SAVEPOINT transactions. Downgrades (v0.4.71 → v0.4.66) are unusual but the migration system handles forward-compatible schemas.

**Impact:** MEDIUM. If schema migration fails, 9Router may refuse to start or may corrupt the database. Behavioral differences between versions could cause subtle issues.

**Mitigation:**
1. Back up `data.sqlite` before installing any version on the VPS.
2. If v0.4.71 `node_modules` are available locally, consider copying the entire package directory as a fallback.
3. If v0.4.66 is installed and migration runs successfully, verify all combos and providers are intact.
4. If migration fails, 9Router's SAVEPOINT mechanism auto-rolls back the schema changes.
5. Worst case: restore from backup and install the exact local version.

**Residual risk:** Low. The SAVEPOINT rollback mechanism provides a safety net.

---

### 3.4 Risk 4 — CRLF Line-Ending Corruption

**Description:** Files created on Windows may contain CRLF (`\r\n`) line endings. When copied to Linux, binary-sensitive files like `jwt-secret` (64-byte JWT signing key) and `machine-id` (64-byte identifier) will have an extra `\r` byte, causing authentication and sync failures.

**Likelihood:** MEDIUM. This is a well-known Windows-to-Linux migration issue. Whether scp/rsync preserves CRLF depends on the transfer mode and client configuration.

**Impact:** MEDIUM.
- `jwt-secret` with trailing `\r`: JWT signature verification fails → dashboard login broken, Cloud Sync auth fails.
- `machine-id` with trailing `\r`: Cloud Sync may identify the machine incorrectly or fail to authenticate.

**Mitigation:**
1. After copying files to the VPS, run:
   ```bash
   sed -i 's/\r$//' /var/lib/9router/jwt-secret
   sed -i 's/\r$//' /var/lib/9router/machine-id
   ```
2. Verify with hex dump:
   ```bash
   xxd /var/lib/9router/jwt-secret | tail -1
   ```
   Expect: line ends with `0a` (LF), NOT `0d 0a` (CRLF).
3. Verify file size:
   ```bash
   wc -c /var/lib/9router/jwt-secret
   ```
   Expect: exactly 64 bytes (or 65 with trailing LF — depends on 9Router's write format).

**Residual risk:** Negligible after verification.

---

### 3.5 Risk 5 — Port Conflict on New VPS

**Description:** Port 20128 is already in use on the new VPS by another service.

**Likelihood:** LOW. Port 20128 is not a well-known port and is unlikely to be claimed by default Ubuntu packages.

**Impact:** LOW. 9Router will fail to start with a clear "EADDRINUSE" error. No data loss.

**Mitigation:**
1. Check before starting:
   ```bash
   ss -tlnp | grep 20128
   ```
2. If port is in use, either stop the conflicting service or change the 9Router port in the env file.
3. systemd will report the failure clearly in `journalctl -u nine-router.service`.

**Residual risk:** Negligible.

---

### 3.6 Risk 6 — Tailscale Not Configured

**Description:** Tailscale is not installed, not running, or not connected to the correct tailnet on the new VPS.

**Likelihood:** LOW. Tailscale installation is straightforward and well-documented.

**Impact:** HIGH. Without Tailscale, the 9Router is unreachable from the local machine (it must NOT be exposed to the public internet). The entire migration is blocked.

**Mitigation:**
1. Verify after installation:
   ```bash
   tailscale status
   tailscale ip -4
   ```
2. Test from the local machine:
   ```bash
   curl http://<tailscale-ip>:20128/api/health
   ```
3. If Tailscale is down, troubleshoot before proceeding. Do NOT expose port 20128 to the public internet as a workaround.

**Residual risk:** Low once Tailscale is verified running.

---

### 3.7 Risk 7 — UFW Blocks Access

**Description:** Ubuntu's UFW firewall blocks inbound connections on port 20128, even over Tailscale.

**Likelihood:** MEDIUM. UFW is enabled by default on Ubuntu 24.04 and blocks all inbound ports unless explicitly allowed.

**Impact:** HIGH. Same as Risk 6 — the 9Router is unreachable from the local machine.

**Mitigation:**
1. Add UFW rule before testing:
   ```bash
   ufw allow in on tailscale0 to any port 20128 proto tcp comment "9Router Tailscale"
   ```
2. Verify:
   ```bash
   ufw status verbose
   ```
3. Test from local machine after adding the rule.
4. The rule is scoped to the `tailscale0` interface only — it does NOT expose port 20128 to the public internet.

**Residual risk:** Negligible after verification.

---

### 3.8 Risk 8 — Memory Exhaustion (OOM)

**Description:** The 9Router process exceeds the VPS's 4 GB RAM and is killed by the Linux OOM killer.

**Likelihood:** LOW. 9Router is a Node.js application with a typical footprint of 200-500 MB. The 4 GB VPS has ample headroom.

**Impact:** HIGH. 9Router is killed, all LLM access is lost until the service restarts.

**Mitigation:**
1. systemd unit uses `MemoryHigh=3G` (triggers reclaim) and `MemoryMax=3.5G` (hard kill with clear log message).
2. Node.js `--max-old-space-size=2048` limits V8 heap to 2 GB.
3. Monitor with:
   ```bash
   systemctl status nine-router.service
   journalctl -u nine-router.service --since "1 hour ago" | grep -i "oom\|memory\|heap"
   ```
4. If OOM occurs: reduce `--max-old-space-size` or upgrade the VPS to 8 GB.

**Residual risk:** Low. The 1.5 GB SQLite database is loaded lazily by SQLite, not fully into Node.js heap.

---

### 3.9 Risk 9 — SQLite WAL Corruption

**Description:** The Write-Ahead Log (`.wal`) and shared-memory (`.shm`) files from the local Windows instance are copied alongside `data.sqlite`, causing corruption on the Linux instance.

**Likelihood:** VERY LOW. WAL files are process-specific and should not be copied. This risk only materializes if the copy is done while 9Router is actively writing.

**Impact:** HIGH. Database corruption could require a restore from backup.

**Mitigation:**
1. Stop the local 9Router before copying `data.sqlite` to ensure WAL is checkpointed.
2. Do NOT copy `.wal` or `.shm` files — they are regenerated by SQLite on the new instance.
3. Run `PRAGMA integrity_check;` after migration.
4. Keep the original `data.sqlite` as a backup.

**Residual risk:** Negligible with the stop-before-copy procedure.

---

### 3.10 Risk 10 — Usage History Table Growth

**Description:** The `usageHistory` table in `data.sqlite` grows unboundedly, eventually filling the VPS disk and degrading SQLite query performance.

**Likelihood:** HIGH (over time). At moderate load (1000 requests/minute), the table grows at approximately 1.44 million rows per day (~288 MB/day, ~12 GB/month).

**Impact:** MEDIUM. Disk full → 9Router stops functioning. Slow queries → increased latency.

**Mitigation:**
1. This is a post-migration operational concern, not a migration blocker.
2. Implement a pruning cron job:
   ```bash
   0 3 * * * sqlite3 /var/lib/9router/data.sqlite "DELETE FROM usageHistory WHERE timestamp < datetime('now', '-30 days');"
   ```
3. Or, if 9Router supports it, configure a retention policy in the env file.
4. Monitor disk usage: `df -h /var/lib/9router`
5. Consider VACUUM periodically to reclaim space:
   ```bash
   sqlite3 /var/lib/9router/data.sqlite "VACUUM;"
   ```

**Residual risk:** Managed by cron job. Must be set up within the first week post-migration.

---

## 4. Hard Constraints

The following actions are **strictly prohibited** during this migration:

| # | Constraint | Rationale |
|---|-----------|-----------|
| H1 | MUST NOT touch Hermes VPS 9Router (`guinevere-9router.service`) | Production service, separate concern |
| H2 | MUST NOT touch `guinevere-core.service` | Hermes production core, out of scope |
| H3 | MUST NOT touch P20/guinevere production services | Production autonomy stack, out of scope |
| H4 | MUST NOT delete local `data.sqlite` before VPS is verified (24h minimum) | Rollback dependency |
| H5 | MUST NOT expose 9Router port 20128 to the public internet | Security — API keys in database |
| H6 | MUST NOT print or commit API keys, jwt-secret, or machine-id | Security — secret leakage |
| H7 | MUST NOT copy `.wal` or `.shm` files | SQLite corruption risk |
| H8 | MUST NOT install 9Router globally on the Hermes VPS | Isolation — new VPS only |

**Enforcement:** These constraints are checked at the pre-migration checklist (Section 7) and post-migration verification (Section 8).

---

## 5. Rollback Procedure

**Estimated time:** Under 1 minute.  
**Prerequisite:** Local 9Router must still be running (it is not stopped during migration).

### Step-by-step rollback

```
1. Stop the VPS 9Router service:
   ssh <vps> "systemctl stop nine-router.service"

2. Switch Claude Code endpoint back to local:
   export OPENAI_BASE_URL=http://localhost:20128/v1

3. Switch OpenCode endpoint back to local:
   export OPENAI_BASE_URL=http://localhost:20128/v1

4. Verify local 9Router is healthy:
   curl http://localhost:20128/api/health
   # Expect: {"status":"ok",...}

5. Test a chat completion:
   curl http://localhost:20128/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d '{"model":"<model-name>","messages":[{"role":"user","content":"ping"}]}'
   # Expect: 200 OK with a valid response

6. Confirm rollback is complete.
   # Local 9Router is serving all requests again.
```

### Rollback triggers

Roll back immediately if any of the following occur after switching to the VPS:

- `curl http://<tailscale-ip>:20128/api/health` returns non-200 or times out
- Chat completions return 401, 403, or 500 errors
- Claude Code or OpenCode cannot connect to the endpoint
- 9Router service crashes or enters a restart loop
- Any service on the Hermes VPS is accidentally affected

---

## 6. Migration Procedure (Reference)

This section provides the complete step-by-step migration procedure for reference. Detailed operational playbooks may be derived from this.

### Phase 1 — VPS Provisioning

```
1. Provision new VPS: Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB disk
2. SSH into VPS and update packages:
   sudo apt update && sudo apt upgrade -y
3. Install Tailscale:
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
4. Record Tailscale IP:
   tailscale ip -4
   # Save this IP — it is the 9Router endpoint
```

### Phase 2 — Node.js & 9Router Installation

```
5. Install Node.js 24.x:
   curl -fsSL https://deb.nodesource.com/setup_24.x | sudo -E bash -
   sudo apt install -y nodejs
6. Verify: node --version && npm --version
7. Install 9Router:
   npm install -g 9router@0.4.66
   # Or: npm install -g 9router (latest)
8. Verify: 9router --version
```

### Phase 3 — System User & Directories

```
9. Create system user:
   sudo useradd --system --shell /usr/sbin/nologin nine-router
10. Create data directory:
    sudo mkdir -p /var/lib/9router
11. Set ownership:
    sudo chown nine-router:nine-router /var/lib/9router
```

### Phase 4 — Database Migration

```
12. Stop local 9Router temporarily (ensures WAL checkpoint):
    # On local Windows machine
    # Stop the 9Router process

13. Copy data.sqlite to VPS:
    scp /path/to/data.sqlite <vps>:/tmp/data.sqlite
    # Or: rsync -avP /path/to/data.sqlite <vps>:/tmp/data.sqlite

14. Move into place:
    ssh <vps> "sudo mv /tmp/data.sqlite /var/lib/9router/data.sqlite"
    ssh <vps> "sudo chown nine-router:nine-router /var/lib/9router/data.sqlite"

15. Verify integrity:
    ssh <vps> "sqlite3 /var/lib/9router/data.sqlite 'PRAGMA integrity_check;'"
    # Expect: ok

16. Restart local 9Router (fallback is back online).

17. Copy or generate jwt-secret and machine-id:
    # Copy from local or generate new 64-byte files:
    ssh <vps> "openssl rand -base64 48 | head -c 64 > /var/lib/9router/jwt-secret"
    ssh <vps> "openssl rand -hex 32 > /var/lib/9router/machine-id"

18. Fix CRLF (critical!):
    ssh <vps> "sudo sed -i 's/\r$//' /var/lib/9router/jwt-secret"
    ssh <vps> "sudo sed -i 's/\r$//' /var/lib/9router/machine-id"

19. Verify CRLF fix:
    ssh <vps> "xxd /var/lib/9router/jwt-secret | tail -1"
    # Expect: line ends with 0a, NOT 0d 0a

20. Set permissions:
    ssh <vps> "sudo chown -R nine-router:nine-router /var/lib/9router"
    ssh <vps> "sudo chmod 600 /var/lib/9router/jwt-secret"
    ssh <vps> "sudo chmod 600 /var/lib/9router/machine-id"
```

### Phase 5 — Service Configuration

```
21. Create environment file:
    sudo mkdir -p /etc/9router
    sudo tee /etc/9router/env > /dev/null << 'EOF'
    PORT=20128
    DATA_DIR=/var/lib/9router
    NODE_ENV=production
    EOF

22. Create systemd slice (optional, for resource isolation):
    sudo tee /etc/systemd/system/nine-router.slice > /dev/null << 'EOF'
    [Slice]
    MemoryMax=3.5G
    MemoryHigh=3G
    CPUQuota=150%
    EOF

23. Create systemd unit:
    sudo tee /etc/systemd/system/nine-router.service > /dev/null << 'EOF'
    [Unit]
    Description=9Router LLM Gateway
    After=network-online.target tailscaled.service
    Wants=network-online.target

    [Service]
    Type=simple
    User=nine-router
    Group=nine-router
    EnvironmentFile=/etc/9router/env
    ExecStart=/usr/bin/node --max-old-space-size=2048 /usr/lib/node_modules/9router/dist/index.js
    Restart=on-failure
    RestartSec=5
    Slice=nine-router.slice

    MemoryHigh=3G
    MemoryMax=3.5G

    ProtectSystem=strict
    ProtectHome=true
    NoNewPrivileges=true
    PrivateTmp=true
    ReadWritePaths=/var/lib/9router

    [Install]
    WantedBy=multi-user.target
    EOF

24. Reload systemd:
    sudo systemctl daemon-reload
```

### Phase 6 — Firewall

```
25. Add UFW rule (Tailscale-only):
    sudo ufw allow in on tailscale0 to any port 20128 proto tcp comment "9Router Tailscale"

26. Verify:
    sudo ufw status verbose
```

### Phase 7 — Start & Verify

```
27. Start 9Router:
    sudo systemctl enable --now nine-router.service

28. Check status:
    systemctl status nine-router.service

29. Check logs:
    journalctl -u nine-router.service -f

30. Verify health (from VPS):
    curl http://localhost:20128/api/health

31. Verify models:
    curl -s http://localhost:20128/v1/models | jq '.data | length'
    # Expect: 24

32. Verify from local machine (Tailscale):
    curl http://<tailscale-ip>:20128/api/health

33. Verify models from local:
    curl -s http://<tailscale-ip>:20128/v1/models | jq '.data | length'
    # Expect: 24
```

### Phase 8 — Client Switch

```
34. Test a real chat completion from local:
    curl http://<tailscale-ip>:20128/v1/chat/completions \
      -H "Content-Type: application/json" \
      -d '{"model":"<model-name>","messages":[{"role":"user","content":"ping"}]}'
    # Expect: 200 OK

35. Switch Claude Code endpoint:
    export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1

36. Switch OpenCode endpoint:
    export OPENAI_BASE_URL=http://<tailscale-ip>:20128/v1

37. Test Claude Code with a simple prompt.
38. Test OpenCode with a simple prompt.

39. If all tests pass, migration is functionally complete.
```

---

## 7. Pre-Migration Checklist

Complete every item before starting the migration.

- [ ] **VPS provisioned:** Ubuntu 24.04, 2 vCPU, 4 GB RAM, 40 GB disk
- [ ] **Tailscale installed and connected:** `tailscale status` shows connected
- [ ] **Tailscale IP recorded:** `tailscale ip -4` returns a valid IP
- [ ] **Node.js 24.x installed:** `node --version` shows v24.x
- [ ] **9Router installed:** `9router --version` returns a version number
- [ ] **System user created:** `id nine-router` returns user info
- [ ] **Data directory exists:** `ls -la /var/lib/9router` shows directory
- [ ] **Local 9Router is running:** `curl http://localhost:20128/api/health` returns OK
- [ ] **Local data.sqlite integrity check passed:** `PRAGMA integrity_check` returns `ok`
- [ ] **Local data.sqlite size noted:** Record file size for post-copy comparison
- [ ] **Local 9Router version recorded:** Note exact version (v0.4.71)
- [ ] **Hermes VPS SSH session NOT open:** Close any SSH sessions to guinevere-vps
- [ ] **UFW rule added on new VPS:** `ufw allow in on tailscale0 to any port 20128 proto tcp`
- [ ] **Rollback procedure reviewed:** Section 5 read and understood
- [ ] **Hard constraints reviewed:** Section 4 read and understood

---

## 8. Post-Migration Verification Checklist

Complete every item after starting the VPS 9Router.

### VPS-side checks

- [ ] **Service is running:** `systemctl status nine-router.service` shows `active (running)`
- [ ] **No errors in logs:** `journalctl -u nine-router.service --since "5 min ago"` shows no ERROR/FATAL
- [ ] **Health endpoint responds:** `curl http://localhost:20128/api/health` returns 200
- [ ] **Models endpoint returns 24 models:** `curl -s http://localhost:20128/v1/models | jq '.data | length'`
- [ ] **Database integrity OK:** `sqlite3 /var/lib/9router/data.sqlite "PRAGMA integrity_check;"` returns `ok`
- [ ] **File permissions correct:** `ls -la /var/lib/9router/` shows `nine-router:nine-router` ownership
- [ ] **jwt-secret is 64 bytes, no CRLF:** `wc -c` and `xxd` verification
- [ ] **machine-id is 64 bytes, no CRLF:** `wc -c` and `xxd` verification
- [ ] **Memory usage normal:** `systemctl status nine-router.service` shows reasonable RSS (< 1 GB)
- [ ] **Disk usage recorded:** `df -h /var/lib/9router` noted for baseline

### Local-side checks

- [ ] **Tailscale connectivity:** `curl http://<tailscale-ip>:20128/api/health` returns 200
- [ ] **Models reachable from local:** `curl -s http://<tailscale-ip>:20128/v1/models | jq '.data | length'`
- [ ] **Chat completion works:** A real completion request returns a valid response
- [ ] **Claude Code works:** Send a test prompt, receive a response
- [ ] **OpenCode works:** Send a test prompt, receive a response

### Rollback readiness check

- [ ] **Local 9Router still running:** `curl http://localhost:20128/api/health` returns OK
- [ ] **Local data.sqlite intact:** File size matches pre-migration recording

---

## 9. Post-Migration Monitoring (24-Hour Watch)

Monitor the following for 24 hours after switching clients to the VPS 9Router.

### Hour 0-1: Active monitoring

| Check | Command | Expected | Frequency |
|-------|---------|----------|-----------|
| Service status | `systemctl status nine-router.service` | active (running) | Every 5 min |
| Error logs | `journalctl -u nine-router.service -p err --since "1h ago"` | Empty | Every 15 min |
| Memory usage | `ps -o rss= -p $(pgrep -f 9router)` | < 1 GB | Every 15 min |
| Health endpoint | `curl http://<tailscale-ip>:20128/api/health` | 200 OK | Every 15 min |
| Response latency | Time the health endpoint | < 500ms | Every 15 min |

### Hour 1-24: Periodic checks

| Check | Command | Expected | Frequency |
|-------|---------|----------|-----------|
| Service status | `systemctl status nine-router.service` | active (running) | Every 1h |
| Error logs | `journalctl -u nine-router.service -p err --since "1h ago"` | Empty | Every 1h |
| Disk usage | `df -h /var/lib/9router` | < 80% used | Every 6h |
| Database size | `ls -lh /var/lib/9router/data.sqlite` | Reasonable growth | Every 6h |

### Alert triggers (immediate rollback consideration)

- Service restarts unexpectedly (check `systemctl status` for restart count)
- Memory usage exceeds 2 GB RSS
- Health endpoint returns non-200 for more than 1 minute
- Error logs contain "OOM", "ENOSPC", "SQLITE_CORRUPT", or "ECONNREFUSED"
- Claude Code or OpenCode cannot complete a request

---

## 10. Disaster Recovery Scenarios

### Scenario A — VPS 9Router won't start

**Symptoms:** `systemctl start nine-router.service` fails immediately.

**Diagnosis:**
```bash
journalctl -u nine-router.service --since "1 min ago" --no-pager
```

**Possible causes and fixes:**
- Port in use → `ss -tlnp | grep 20128`, stop conflicting service
- Database corrupted → Restore from local backup, re-run integrity check
- Schema migration failed → Check logs for migration error, may need to install matching version
- Node.js not found → Verify `node --version`, fix PATH in systemd unit
- Permission denied → `chown -R nine-router:nine-router /var/lib/9router`

**Rollback:** Section 5.

---

### Scenario B — VPS 9Router starts but models endpoint returns 0

**Symptoms:** `curl /v1/models` returns `{"data":[]}` or similar empty response.

**Diagnosis:**
```bash
sqlite3 /var/lib/9router/data.sqlite "SELECT COUNT(*) FROM provider_connections;"
sqlite3 /var/lib/9router/data.sqlite "SELECT COUNT(*) FROM combos;"
```

**Possible causes:**
- Wrong database copied (e.g., empty/template database)
- Schema migration dropped tables
- API keys are placeholders (copied from Hermes VPS instead of local)

**Fix:** Re-copy `data.sqlite` from local, re-run integrity check.

**Rollback:** Section 5.

---

### Scenario C — VPS 9Router returns 401/403 on chat completions

**Symptoms:** Models endpoint works, but actual completions fail with auth errors.

**Diagnosis:**
```bash
sqlite3 /var/lib/9router/data.sqlite "SELECT provider, key FROM provider_connections;"
# Check that keys are real values, not "placeholder" or empty
```

**Possible causes:**
- API keys are expired or revoked
- Provider rate limits exceeded
- Network issue reaching the provider API from VPS

**Fix:**
- If keys are placeholders: re-copy from local
- If keys are expired: update in the database or dashboard
- If network issue: test `curl https://api.anthropic.com` from VPS

**Rollback:** Section 5.

---

### Scenario D — Tailscale connectivity lost

**Symptoms:** `curl http://<tailscale-ip>:20128/api/health` times out from local machine.

**Diagnosis:**
```bash
# On VPS:
tailscale status
systemctl status tailscaled

# On local:
tailscale status
ping <tailscale-ip>
```

**Possible causes:**
- Tailscale service stopped on VPS
- Tailscale key expired
- Local Tailscale disconnected
- Network firewall blocking Tailscale's WireGuard port (UDP 41641)

**Fix:**
- Restart Tailscale: `sudo systemctl restart tailscaled`
- Re-authenticate if needed: `sudo tailscale up`
- Check firewall: ensure UDP 41641 is open on both ends

**Rollback:** Section 5 (local 9Router doesn't use Tailscale).

---

### Scenario E — Accidental Hermes VPS modification

**Symptoms:** Hermes production services are affected.

**Immediate action:**
1. Stop any changes to the Hermes VPS immediately.
2. Check service status:
   ```bash
   ssh guinevere-vps "systemctl status guinevere-9router.service guinevere-core.service"
   ```
3. If services are down, restart them:
   ```bash
   ssh guinevere-vps "sudo systemctl start guinevere-9router.service guinevere-core.service"
   ```
4. If database was modified, restore from the latest Hermes backup.
5. File an incident report.

**Prevention:** This scenario should never happen. The migration uses a completely separate VPS. Do not SSH into guinevere-vps during migration.

---

### Scenario F — Local 9Router accidentally stopped

**Symptoms:** `curl http://localhost:20128/api/health` fails on the local machine.

**Diagnosis:** Check if the local 9Router process is still running.

**Fix:** Restart the local 9Router. If data.sqlite was not deleted, it will start normally.

**Impact:** Rollback (Section 5) is temporarily unavailable until the local 9Router is restarted.

**Prevention:** Do NOT stop the local 9Router during migration. It is the rollback target.

---

## 11. Footer

This report was generated as part of the P25 migration research phase. It is a planning document and does not constitute authorization to proceed. The operator must review and approve before any migration actions are taken.

**Next steps:**
1. Operator reviews this report
2. Complete pre-migration checklist (Section 7)
3. Execute migration procedure (Section 6)
4. Complete post-migration verification (Section 8)
5. Begin 24-hour monitoring (Section 9)
6. If stable for 24 hours, migration is complete

**References:**
- 9Router documentation: `npm info 9router`
- SQLite backup best practices: https://www.sqlite.org/backup.html
- Tailscale installation: https://tailscale.com/kb/1039/install-ubuntu
- systemd resource control: https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html

---

*End of report.*
