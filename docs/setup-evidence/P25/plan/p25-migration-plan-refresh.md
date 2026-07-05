# P25 Migration Plan Refresh — 9Router to Dedicated VPS

> **Document ID:** P25-PLAN-REFRESH-001
> **Date:** 2026-06-26
> **Status:** RESEARCH ONLY — No Implementation
> **Supersedes:** Previous P25 plan (stale version/config data)

---

## 1. Executive Summary

This document defines the corrected migration plan for moving the local 9Router
instance (v0.5.4) from the developer workstation to a new dedicated VPS on the
existing Tailscale tailnet.

The previous P25 plan was based on stale ground-truth data: it referenced
9Router v0.4.71 (actual: v0.5.4), used the wrong heap configuration mechanism
(NODE_OPTIONS instead of NINEROUTER_NODE_HEAP_MB), and assumed only 2 providers
and 6 combos (actual: 92 providers, 11 combos). These errors would have caused
OOM crashes and incomplete data migration in production.

This refresh corrects all known inaccuracies, adds missing verification steps
(especially heap confirmation), and provides a complete 10-wave migration
procedure with rollback capability at every stage.

**Key constraint:** The local 9Router remains running throughout the entire
migration. Rollback is instant (< 1 second) by reverting OPENAI_BASE_URL.

---

## 2. Key Corrections from Previous Plan

| Aspect | Previous Plan (WRONG) | Corrected Plan (THIS) | Impact |
|---|---|---|---|
| 9Router version | 0.4.71 | **0.5.4** | Different API surface, config keys |
| Heap control | `NODE_OPTIONS=--max-old-space-size=2048` | **`NINEROUTER_NODE_HEAP_MB=2048`** | Previous method is IGNORED by 9Router — would OOM |
| Provider count | 2 | **92** | 46x more data to verify post-migration |
| Combo count | 6 | **11** | Combo routing requires all 11 present |
| Database size | Not specified | **1.5 GB** | Affects transfer time, disk provisioning |
| Custom server | Not mentioned | **custom-server.js exists** | Must not conflict with systemd service |
| Heap verification | Not in plan | **Verify child process args** | Critical safety gate |
| Load test approach | Not specified | **Mock upstream + k6** | Realistic load without burning API credits |
| Next.js version | Not specified | **16.1.6** | Confirmed, no action needed |

**Why the heap correction is critical:** 9Router v0.5.4 reads
`NINEROUTER_NODE_HEAP_MB` from the environment and passes it as
`--max-old-space-size=<value>` to its child Node.js process. Setting
`NODE_OPTIONS=--max-old-space-size=2048` at the systemd level does NOT propagate
to the 9Router-spawned child process. Without the correct variable, the child
defaults to ~512 MB heap and will OOM under load with 92 providers and a 1.5 GB
SQLite database.

---

## 3. Migration Waves

### Wave 1: VPS Provisioning

**Goal:** Fresh Ubuntu 24.04 VPS with Tailscale and Node.js 24.x ready.

**Steps:**

1. Provision a new VPS (Ubuntu 24.04 LTS, minimum 2 vCPU / 4 GB RAM / 40 GB disk).
2. SSH into the new VPS.
3. Install Tailscale:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   ```
4. Join the existing tailnet:
   ```bash
   tailscale up
   ```
   (Authenticate via the Tailscale web flow in the browser.)
5. Record the Tailscale IP:
   ```bash
   tailscale ip -4
   ```
   **Expected:** A `100.x.x.x` address. Record this — all client configuration
   depends on it.
6. Install Node.js 24.x via NodeSource:
   ```bash
   curl -fsSL https://deb.nodesource.com/setup_24.x | bash -
   apt-get install -y nodejs
   ```
7. Verify Node.js:
   ```bash
   node --version   # expect v24.x.x
   npm --version    # expect 11.x.x
   ```
8. Install 9Router globally:
   ```bash
   npm install -g 9router@0.5.4
   ```
9. Verify installation:
   ```bash
   which 9router         # expect /usr/bin/9router or similar
   9router --version      # expect 0.5.4
   ```

**Exit criteria:** `9router --version` returns `0.5.4`. Tailscale IP recorded.

---

### Wave 2: User & Directory Setup

**Goal:** Dedicated service account and directory structure for 9Router.

**Steps:**

1. Create the service user:
   ```bash
   useradd --system --no-create-home --shell /usr/sbin/nologin nine-router
   ```
2. Create the data directory tree:
   ```bash
   mkdir -p /var/lib/9router/db/backups
   ```
3. Create the environment configuration directory:
   ```bash
   mkdir -p /etc/9router/
   ```
4. Set ownership:
   ```bash
   chown -R nine-router:nine-router /var/lib/9router
   ```
5. Set directory permissions:
   ```bash
   chmod 755 /var/lib/9router
   ```
6. Verify:
   ```bash
   ls -la /var/lib/9router/
   # Should show: drwxr-xr-x ... nine-router:nine-router ... db/
   ls -la /var/lib/9router/db/
   # Should show: drwxr-xr-x ... nine-router:nine-router ... backups/
   ls -la /etc/9router/
   # Should show: drwxr-xr-x ... root:root ... . (empty is fine at this stage)
   ```

**Exit criteria:** Directories exist with correct ownership.

---

### Wave 3: Data Migration

**Goal:** Transfer the SQLite database, JWT secret, and machine ID from local
to VPS with integrity verification.

**Steps:**

1. Copy `data.sqlite` from local machine to VPS:
   ```bash
   # From local machine (adjust source path to actual 9Router data directory):
   scp /path/to/local/9router/data/data.sqlite root@<vps-tailscale-ip>:/var/lib/9router/db/
   ```
   **Note:** File is 1.5 GB. Transfer time depends on bandwidth. Over Tailscale
   this should complete in 2-10 minutes.

2. Copy `jwt-secret` from local to VPS:
   ```bash
   scp /path/to/local/9router/data/jwt-secret root@<vps-tailscale-ip>:/var/lib/9router/
   ```

3. Copy `machine-id` from local to VPS:
   ```bash
   scp /path/to/local/9router/data/machine-id root@<vps-tailscale-ip>:/var/lib/9router/
   ```

4. Fix CRLF line endings (Windows-to-Linux corruption):
   ```bash
   sed -i 's/\r$//' /var/lib/9router/jwt-secret
   sed -i 's/\r$//' /var/lib/9router/machine-id
   ```

5. Set file permissions:
   ```bash
   chmod 600 /var/lib/9router/jwt-secret
   chmod 600 /var/lib/9router/machine-id
   chmod 600 /var/lib/9router/db/data.sqlite
   ```

6. Set ownership on all migrated files:
   ```bash
   chown nine-router:nine-router /var/lib/9router/jwt-secret
   chown nine-router:nine-router /var/lib/9router/machine-id
   chown nine-router:nine-router /var/lib/9router/db/data.sqlite
   ```

7. Verify database integrity:
   ```bash
   sqlite3 /var/lib/9router/db/data.sqlite "PRAGMA integrity_check"
   ```
   **Expected:** `ok`

8. Verify provider count:
   ```bash
   sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM providerConnections"
   ```
   **Expected:** `92`

9. Verify combo count:
   ```bash
   sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM combos"
   ```
   **Expected:** `11`

10. Verify JWT secret is exactly 64 bytes:
    ```bash
    wc -c /var/lib/9router/jwt-secret
    ```
    **Expected:** `64 /var/lib/9router/jwt-secret`

11. Verify machine-id is exactly 64 bytes:
    ```bash
    wc -c /var/lib/9router/machine-id
    ```
    **Expected:** `64 /var/lib/9router/machine-id`

12. Verify no CRLF remnants:
    ```bash
    file /var/lib/9router/jwt-secret
    # Should NOT say "CRLF" — should say "data" or "ASCII text"
    file /var/lib/9router/machine-id
    # Same check
    ```

**Exit criteria:** Integrity check returns `ok`. Provider count = 92.
Combo count = 11. All secrets are 64 bytes with no CRLF.

---

### Wave 4: Environment Configuration

**Goal:** Create the 9Router environment file with all required variables.

**Steps:**

1. Create `/etc/9router/env`:
   ```bash
   cat > /etc/9router/env << 'ENVEOF'
   DATA_DIR=/var/lib/9router
   PORT=20128
   HOSTNAME=0.0.0.0
   JWT_SECRET=<REPLACE-WITH-CONTENT-OF-MIGRATED-JWT-SECRET>
   INITIAL_PASSWORD=<SET-A-SECURE-PASSWORD>
   REQUIRE_API_KEY=false
   ENABLE_REQUEST_LOGS=false
   ENVEOF
   ```
   **CRITICAL:** Replace `<REPLACE-WITH-CONTENT-OF-MIGRATED-JWT-SECRET>` with
   the actual contents of `/var/lib/9router/jwt-secret`. The JWT secret MUST
   match the one used by the local instance, or all existing auth tokens will be
   invalidated (which would break the database's stored API keys).

   **CRITICAL:** Set `<SET-A-SECURE-PASSWORD>` to a strong password for the
   9Router dashboard. This is the operator's admin credential.

2. Set permissions:
   ```bash
   chown root:nine-router /etc/9router/env
   chmod 640 /etc/9router/env
   ```

3. Verify:
   ```bash
   ls -la /etc/9router/env
   # Expected: -rw-r----- 1 root nine-router ... /etc/9router/env
   ```

4. Verify HOSTNAME is `0.0.0.0` (NOT `127.0.0.1`):
   ```bash
   grep '^HOSTNAME=' /etc/9router/env
   # Expected: HOSTNAME=0.0.0.0
   ```
   **Why:** Tailscale interfaces bind to a `100.x.x.x` address. If 9Router
   listens on `127.0.0.1`, Tailscale traffic will be refused.

**Exit criteria:** Env file exists, readable by nine-router group, HOSTNAME is
`0.0.0.0`.

---

### Wave 5: systemd Service Setup

**Goal:** Create a systemd service unit with correct resource controls, heap
configuration, and security hardening.

**Detailed in Section 4 below.**

**Steps (summary):**

1. Create `/etc/systemd/system/nine-router.slice` for resource control.
2. Create `/etc/systemd/system/nine-router.service` with:
   - `NINEROUTER_NODE_HEAP_MB=2048` (NOT NODE_OPTIONS)
   - Security hardening (NoNewPrivileges, ProtectSystem, etc.)
   - EnvironmentFile pointing to `/etc/9router/env`
   - Restart policy (on-failure, 10s delay, max 5 restarts)
   - 180s startup timeout (large DB needs time on cold start)
3. Reload systemd:
   ```bash
   systemctl daemon-reload
   ```
4. Enable the service:
   ```bash
   systemctl enable nine-router.service
   ```
5. Start the service:
   ```bash
   systemctl start nine-router.service
   ```
6. Check status:
   ```bash
   systemctl status nine-router.service
   ```
   **Expected:** `active (running)`

7. Check logs:
   ```bash
   journalctl -u nine-router.service -n 50 --no-pager
   ```
   **Expected:** 9Router startup output, no errors, listening on port 20128.

**Exit criteria:** Service is active and running. Logs show clean startup.

---

### Wave 6: UFW & Tailscale Firewall

**Goal:** Restrict 9Router access to Tailscale-only, denying all public
internet access.

**Steps:**

1. Allow 9Router on the Tailscale interface only:
   ```bash
   ufw allow in on tailscale0 to any port 20128 proto tcp comment "9Router Tailscale-only"
   ```

2. Deny 9Router on all other interfaces:
   ```bash
   ufw deny 20128/tcp comment "9Router deny public"
   ```

3. Ensure UFW is enabled:
   ```bash
   ufw status verbose
   ```

4. Test from local machine via Tailscale:
   ```bash
   curl -s http://<vps-tailscale-ip>:20128/api/health
   ```
   **Expected:** `{"ok":true}`

5. Test that direct public IP is blocked (if a public IP exists):
   ```bash
   # From the VPS itself or another machine NOT on tailnet:
   curl --connect-timeout 3 http://<vps-public-ip>:20128/api/health
   ```
   **Expected:** Connection refused or timeout.

**Exit criteria:** Health endpoint reachable via Tailscale. Unreachable via
public IP.

---

### Wave 7: Verification

**Goal:** Comprehensive verification that the migrated 9Router instance is
fully operational.

**Detailed in Section 5 below.**

**Summary checklist:**

- [ ] Health check: `{"ok":true}`
- [ ] Model listing returns models
- [ ] 92 providers are active
- [ ] 11 combos are available
- [ ] Chat completion works with a real model
- [ ] Remote access via Tailscale works
- [ ] Heap is correctly set to 2048 MB in child process
- [ ] NINEROUTER_NODE_HEAP_MB=2048 appears in systemd environment
- [ ] Dashboard is accessible via Tailscale

**Exit criteria:** All items above pass.

---

### Wave 8: Client Switch

**Goal:** Point Claude Code and OpenCode at the new VPS-hosted 9Router.

**Steps:**

1. Update Claude Code environment:
   ```
   OPENAI_BASE_URL=http://<vps-tailscale-ip>:20128/v1
   ```

2. Update OpenCode environment:
   ```
   OPENAI_BASE_URL=http://<vps-tailscale-ip>:20128/v1
   ```

3. Test Claude Code with a simple prompt:
   ```
   > What is 2 + 2?
   ```
   **Expected:** Valid response, no connection errors, no auth errors.

4. Test OpenCode with a simple prompt:
   ```
   > Write a hello world in Python
   ```
   **Expected:** Valid response, no connection errors, no auth errors.

5. Verify the requests appear in 9Router logs on the VPS:
   ```bash
   journalctl -u nine-router.service -f
   ```

**Exit criteria:** Both clients successfully complete requests through the VPS
9Router.

---

### Wave 9: Load Test

**Goal:** Validate that the VPS can handle production traffic loads without
errors or memory issues.

**Detailed in:** `p25-load-test-design-refresh.md` (separate document).

**Steps:**

1. **Mock upstream test first:** Configure a mock upstream to avoid burning real
   API credits during the load test. The mock returns a fixed response with
   realistic latency (200-500ms).

2. **Sustained load:** 1000 requests/minute sustained for 5 minutes using k6
   or equivalent.

3. **Real provider smoke test:** 10-20 requests through real providers to
   confirm end-to-end routing works under the new deployment.

4. **Pass/Fail thresholds:**
   - Error rate < 1%
   - P95 latency < 5 seconds
   - Memory does not exceed 3.5 GB (of 4 GB total)
   - No OOM kills in dmesg
   - CPU does not sustain > 90% for > 30 seconds

5. **Post-test checks:**
   - `journalctl -u nine-router.service` — no errors
   - `dmesg | grep -i oom` — no OOM kills
   - `free -h` — memory returned to baseline within 60 seconds

**Exit criteria:** All thresholds pass. No OOM kills. Memory returns to
baseline after load stops.

---

### Wave 10: 24-Hour Soak

**Goal:** Confirm the VPS-hosted 9Router is stable over a full day of
operation.

**Steps:**

1. Monitor for 24 hours with periodic checks:
   - **Memory:** `free -h` every 4 hours. Flag if RSS > 3 GB.
   - **CPU:** `top -bn1 | grep 9router` every 4 hours. Flag if > 50% sustained.
   - **Errors:** `journalctl -u nine-router.service --since "1 hour ago"` every
     4 hours. Flag any unexpected errors.
   - **File descriptors:** `ls /proc/$(pgrep -f 9router)/fd | wc -l` every
     8 hours. Flag if > 1000.
   - **Health endpoint:** `curl http://localhost:20128/api/health` every hour.
     Must return `{"ok":true}`.

2. Check for unexpected HTTP errors in 9Router logs:
   ```bash
   journalctl -u nine-router.service | grep -E '"status":(401|403|5[0-9]{2})'
   ```
   **Expected:** No matches (or only known/expected ones).

3. Verify dashboard is still accessible via Tailscale:
   ```
   http://<vps-tailscale-ip>:20128
   ```

4. If all clear after 24 hours: **migration complete.**

**Exit criteria:** No OOM, no crashes, no unexpected errors, health endpoint
consistently returns OK, memory is stable.

---

## 4. Wave 5 Detail: systemd with NINEROUTER_NODE_HEAP_MB

This section provides the complete systemd configuration.

### 4.1 Resource Slice: `/etc/systemd/system/nine-router.slice`

```ini
[Unit]
Description=9Router slice

[Slice]
MemoryMax=3584M
MemoryHigh=3072M
CPUQuota=180%
TasksMax=256
```

**Rationale:**
- `MemoryMax=3584M` — hard cap at 3.5 GB of 4 GB total, leaving 512 MB for OS.
- `MemoryHigh=3072M` — soft pressure at 3 GB, encouraging the kernel to reclaim
  memory before hitting the hard limit.
- `CPUQuota=180%` — allows near-full use of 2 vCPUs without starving the system.
- `TasksMax=256` — 92 providers with connection pools need headroom.

### 4.2 Service Unit: `/etc/systemd/system/nine-router.service`

```ini
[Unit]
Description=9Router API Gateway
Documentation=https://github.com/9router/9router
After=network-online.target
Wants=network-online.target
Requires=network.target

[Service]
Type=simple
User=nine-router
Group=nine-router
WorkingDirectory=/var/lib/9router

# ── ENVIRONMENT ──────────────────────────────────────────────────
EnvironmentFile=/etc/9router/env

# ── CRITICAL: HEAP CONFIGURATION ─────────────────────────────────
# 9Router v0.5.4 reads NINEROUTER_NODE_HEAP_MB and passes it as
# --max-old-space-size=<value> to its child Node.js process.
#
# DO NOT USE:  Environment=NODE_OPTIONS=--max-old-space-size=2048
# That variable does NOT propagate to 9Router's child process and
# the child will default to ~512 MB heap → OOM with 92 providers
# and a 1.5 GB SQLite database.
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

# ── SECURITY HARDENING ───────────────────────────────────────────
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
PrivateTmp=true
ProtectKernelTunables=true
ProtectKernelModules=true
ProtectControlGroups=true
RestrictSUIDSGID=true
RestrictNamespaces=true
ReadWritePaths=/var/lib/9router

# ── RESOURCE CONTROL (via slice) ────────────────────────────────
Slice=nine-router.slice

# ── LOGGING ──────────────────────────────────────────────────────
StandardOutput=journal
StandardError=journal
SyslogIdentifier=nine-router

[Install]
WantedBy=multi-user.target
```

### 4.3 Why NINEROUTER_NODE_HEAP_MB

9Router v0.5.4 is a Node.js application that spawns a child process for its
main server. The child process's heap size must be controlled via the
`NINEROUTER_NODE_HEAP_MB` environment variable, which 9Router reads and
translates to `--max-old-space-size=<value>` when launching the child.

**What happens with NODE_OPTIONS (WRONG):**

```
systemd → 9router (parent) → child node process
                  ↑
    NODE_OPTIONS is set HERE,
    but 9router does NOT inherit it
    when spawning the child process
```

The child process gets Node.js defaults (~512 MB on a 4 GB system). With 92
providers and a 1.5 GB database, the heap will fill rapidly under load and
trigger an OOM crash.

**What happens with NINEROUTER_NODE_HEAP_MB (CORRECT):**

```
systemd → 9router (parent, reads env) → child node process
                  ↓
    NINEROUTER_NODE_HEAP_MB=2048
    → passes --max-old-space-size=2048 to child
```

The child gets a 2048 MB heap, sufficient for 92 providers + 1.5 GB database.

### 4.4 Verification Commands for Heap

After starting the service, verify the heap is correctly applied:

```bash
# Method 1: Check the systemd environment
systemctl show nine-router.service -p Environment
# Expected output includes: NINEROUTER_NODE_HEAP_MB=2048

# Method 2: Check the child process command line
ps aux | grep 9router
# Look for: --max-old-space-size=2048 in the child node process args

# Method 3: More precise process inspection
pgrep -a -f 9router
# Or:
cat /proc/$(pgrep -f "9router.*child" || pgrep -f 9router)/cmdline | tr '\0' '\n'
```

**If `--max-old-space-size=2048` does NOT appear in the child process args:**
STOP. The heap is not correctly configured. Do not proceed to load testing.

---

## 5. Wave 7 Detail: Verification Checklist

### 5.1 Health Endpoint

```bash
curl -s http://localhost:20128/api/health | jq .
```

**Expected:**
```json
{
  "ok": true
}
```

### 5.2 Model Listing

```bash
curl -s http://localhost:20128/v1/models | jq '.data | length'
```

**Expected:** Non-zero number of models.

```bash
curl -s http://localhost:20128/v1/models | jq '.data[].id' | head -20
```

**Expected:** List of model identifiers (e.g., `ds/deepseek-v4-flash`).

### 5.3 Provider Count Verification

```bash
sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM providerConnections"
```

**Expected:** `92`

### 5.4 Combo Count Verification

```bash
sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM combos"
```

**Expected:** `11`

### 5.5 Chat Completion Test

```bash
curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "ds/deepseek-v4-flash",
    "messages": [{"role": "user", "content": "hi"}],
    "stream": false,
    "max_tokens": 10
  }' | jq .
```

**Expected:** Valid chat completion response with `choices[0].message.content`.

### 5.6 Remote Access via Tailscale

```bash
# From local machine:
curl -s http://<vps-tailscale-ip>:20128/api/health | jq .
```

**Expected:** `{"ok":true}`

### 5.7 Heap Verification

```bash
# Check systemd environment
systemctl show nine-router.service -p Environment | grep NINEROUTER_NODE_HEAP_MB
```

**Expected:** `NINEROUTER_NODE_HEAP_MB=2048`

```bash
# Check child process args
ps aux | grep 9router | grep max-old-space-size
```

**Expected:** Line containing `--max-old-space-size=2048`

### 5.8 Dashboard Access

Open in browser:
```
http://<vps-tailscale-ip>:20128
```

**Expected:** 9Router dashboard loads. Login with INITIAL_PASSWORD.

### 5.9 Complete Verification Script

```bash
#!/bin/bash
# P25 Wave 7 — Run on VPS
set -euo pipefail

PASS=0
FAIL=0

check() {
    local desc="$1"
    local result="$2"
    if [ "$result" = "PASS" ]; then
        echo "  [PASS] $desc"
        ((PASS++))
    else
        echo "  [FAIL] $desc"
        ((FAIL++))
    fi
}

echo "=== P25 Wave 7 Verification ==="
echo ""

# Health
HEALTH=$(curl -s http://localhost:20128/api/health)
echo "$HEALTH" | grep -q '"ok":true' && check "Health endpoint" "PASS" || check "Health endpoint" "FAIL"

# Models
MODEL_COUNT=$(curl -s http://localhost:20128/v1/models | jq '.data | length' 2>/dev/null)
[ "${MODEL_COUNT:-0}" -gt 0 ] && check "Model listing ($MODEL_COUNT models)" "PASS" || check "Model listing" "FAIL"

# Providers
PROVIDER_COUNT=$(sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM providerConnections" 2>/dev/null)
[ "${PROVIDER_COUNT:-0}" -eq 92 ] && check "Provider count ($PROVIDER_COUNT)" "PASS" || check "Provider count (expected 92, got $PROVIDER_COUNT)" "FAIL"

# Combos
COMBO_COUNT=$(sqlite3 /var/lib/9router/db/data.sqlite "SELECT COUNT(*) FROM combos" 2>/dev/null)
[ "${COMBO_COUNT:-0}" -eq 11 ] && check "Combo count ($COMBO_COUNT)" "PASS" || check "Combo count (expected 11, got $COMBO_COUNT)" "FAIL"

# Chat completion
CHAT=$(curl -s http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"ds/deepseek-v4-flash","messages":[{"role":"user","content":"hi"}],"stream":false,"max_tokens":10}')
echo "$CHAT" | grep -q 'choices' && check "Chat completion" "PASS" || check "Chat completion" "FAIL"

# Heap env
HEAP_ENV=$(systemctl show nine-router.service -p Environment 2>/dev/null)
echo "$HEAP_ENV" | grep -q 'NINEROUTER_NODE_HEAP_MB=2048' && check "Heap env variable" "PASS" || check "Heap env variable" "FAIL"

# Heap child process
ps aux | grep 9router | grep -q 'max-old-space-size=2048' && check "Heap child process args" "PASS" || check "Heap child process args" "FAIL"

# Service status
systemctl is-active nine-router.service >/dev/null 2>&1 && check "Service active" "PASS" || check "Service active" "FAIL"

echo ""
echo "=== Results: $PASS PASS, $FAIL FAIL ==="
[ "$FAIL" -eq 0 ] && echo "ALL CHECKS PASSED" || echo "SOME CHECKS FAILED — DO NOT PROCEED"
```

---

## 6. Rollback Procedure

Rollback is available at **any wave** and takes **< 1 second**.

### Instant Rollback

1. On the local machine, revert the environment variable:
   ```
   OPENAI_BASE_URL=http://localhost:20128/v1
   ```

2. This applies to both Claude Code and OpenCode.

3. The local 9Router remains running throughout the entire migration. It is
   **never stopped**. Rollback simply points clients back at it.

### Cleanup (optional, after rollback)

If the VPS is no longer needed:
```bash
# On the VPS:
systemctl stop nine-router.service
systemctl disable nine-router.service
# Then destroy the VPS via provider dashboard.
```

### Rollback triggers

- Any wave exit criteria fails
- Health endpoint returns errors
- Provider count mismatch
- Heap not correctly applied
- OOM kills observed
- Load test failures
- Soak test anomalies

---

## 7. Hard Constraints (MUST NOT)

| # | Constraint | Reason |
|---|---|---|
| 1 | **MUST NOT** touch Hermes VPS 9Router (`guinevere-9router.service`) | Separate production instance; different purpose |
| 2 | **MUST NOT** touch `guinevere-core.service` | Unrelated service on Hermes VPS |
| 3 | **MUST NOT** touch P20/Discord services | Unrelated; could break bot functionality |
| 4 | **MUST NOT** delete local `data.sqlite` before VPS verification | Rollback depends on local data |
| 5 | **MUST NOT** skip `NINEROUTER_NODE_HEAP_MB=2048` | OOM risk under load |
| 6 | **MUST NOT** bind to `127.0.0.1` | Tailscale won't work; remote access fails |
| 7 | **MUST NOT** expose to public internet | UFW deny on non-tailscale0 interfaces |
| 8 | **MUST NOT** run load test against real providers at scale | Burns API credits; use mock upstream |
| 9 | **MUST NOT** use `NODE_OPTIONS` for heap control | Ignored by 9Router child process (see Section 4.3) |
| 10 | **MUST NOT** proceed if provider count != 92 | Incomplete data migration |

---

## 8. Time Estimate

| Wave | Description | Estimated Time | Depends On |
|---|---|---|---|
| 1 | VPS Provisioning | 15-20 min | None |
| 2 | User & Directory Setup | 5 min | Wave 1 |
| 3 | Data Migration | 10-20 min | Wave 2 |
| 4 | Environment Configuration | 5 min | Wave 3 |
| 5 | systemd Service Setup | 10 min | Wave 4 |
| 6 | UFW & Tailscale Firewall | 5 min | Wave 5 |
| 7 | Verification | 10-15 min | Wave 6 |
| 8 | Client Switch | 5 min | Wave 7 |
| 9 | Load Test | 15-30 min | Wave 8 |
| 10 | 24-Hour Soak | 24 hours | Wave 9 |
| | **Total active time** | **~80-120 min** | |
| | **Total wall-clock time** | **~25-26 hours** | |

**Note:** Waves 1-8 can be completed in a single session (~90 minutes).
Wave 9 (load test) requires ~15-30 minutes. Wave 10 (soak) is passive
monitoring over 24 hours.

---

## 9. Risk Register

| # | Risk | Probability | Impact | Mitigation |
|---|---|---|---|---|
| R1 | OOM crash due to wrong heap config | **High** (if NODE_OPTIONS used) | **Critical** | Use NINEROUTER_NODE_HEAP_MB=2048. Verify child process args in Wave 7. |
| R2 | CRLF corruption in secrets | **Medium** (Windows source) | **High** | sed -i 's/\r$//' in Wave 3. Verify with `file` command. |
| R3 | Incomplete data migration | **Low** | **Critical** | Verify provider count (92) and combo count (11) post-migration. |
| R4 | Tailscale connectivity failure | **Low** | **High** | Test Tailscale IP in Wave 1 before proceeding. |
| R5 | Public internet exposure | **Low** (if UFW skipped) | **Critical** | UFW rules in Wave 6. Verify deny rule active. |
| R6 | JWT secret mismatch | **Low** | **High** | Copy exact bytes, verify 64-byte length, no CRLF. |
| R7 | 9Router version mismatch | **Low** | **Medium** | Pin `9router@0.5.4` in npm install. Verify with `--version`. |
| R8 | SQLite corruption during transfer | **Low** | **Critical** | `PRAGMA integrity_check` in Wave 3. |
| R9 | Disk space exhaustion on VPS | **Low** | **High** | Provision 40 GB minimum. DB is 1.5 GB, logs grow slowly. |
| R10 | Load test OOM | **Medium** | **Medium** | Run mock upstream first. Monitor memory in real-time during test. |
| R11 | Local 9Router stopped accidentally | **Low** | **Critical** | DO NOT stop local 9Router at any point. Rollback depends on it. |
| R12 | custom-server.js conflict | **Low** | **Medium** | Documented but not blocking; service uses standard `9router` binary. |

---

## 10. Footer

This document is part of the P25 migration effort for the Guinevere project.
It supersedes the previous P25 plan which contained stale version and
configuration data.

**Related documents:**
- `p25-load-test-design-refresh.md` — Load test specifications
- `p25-systemd-service-design.md` — Original systemd design (use this refresh
  for the NINEROUTER_NODE_HEAP_MB correction)

**Revision history:**

| Date | Version | Author | Changes |
|---|---|---|---|
| 2026-06-26 | 1.0 | Ground-truth refresh | Corrected version (0.5.4), heap config (NINEROUTER_NODE_HEAP_MB), provider count (92), combo count (11), added verification steps, load test design |

---

*End of P25 Migration Plan Refresh*
