# P25: 9Router VPS Migration — Replan v2

**Date**: 2026-06-26  
**Status**: REPLAN FIXED — READY FOR MAMA APPROVAL  
**Scope**: Install 9Router on VPS, migrate providerConnections, update client endpoints, verify

---

## 0. Binding Decisions (from Faiz)

| Decision | Value |
|---|---|
| VPS | root@49.12.82.34:39999 |
| SSH access | `ssh root@49.12.82.34 -p 39999` (SSH key) — never use password, never log password |
| 9Router on VPS | primary after verification |
| Local 9Router | shutdown after verification |
| Service user | root |
| Access model | **bind 0.0.0.0 + firewall Tailscale-only** (see §7.1) |
| Firewall | add-only, never flush, never reset, never delete SSH rule, no SSH lockout |
| Migration scope | providerConnections + config tables only |
| Implementation | WAIT for Faiz approval before any action |

---

## 1. Pre-Flight Checklist

Before any VPS action:

- [ ] SSH to VPS works: `ssh ninerouter-vps`
- [ ] VPS has Node.js 18+ (`node -v`)
- [ ] VPS has `npm` available
- [ ] VPS has `sqlite3` CLI available
- [ ] Tailscale installed on VPS
- [ ] Capture current VPS firewall state: `ufw status verbose`, `iptables -L INPUT -n --line-numbers`

---

## 2. Step-by-Step Execution Plan

### Step 1: Export Local 9Router Config (SAFE — INSERT-only, no CREATE TABLE)

**ON WINDOWS LOCAL** — generate INSERT statements only, not full DDL. This avoids CREATE TABLE conflicts on the target.

```powershell
# Export each table as INSERT-only (no schema DDL)
sqlite3 "C:\Users\faizz\AppData\Roaming\9router\db\data.sqlite" ^
  ".mode insert providerConnections" "SELECT * FROM providerConnections;" ^
  ".mode insert settings" "SELECT * FROM settings;" ^
  ".mode insert combos" "SELECT * FROM combos;" ^
  ".mode insert apiKeys" "SELECT * FROM apiKeys;" ^
  ".mode insert providerNodes" "SELECT * FROM providerNodes;" ^
  ".mode insert proxyPools" "SELECT * FROM proxyPools;" ^
  ".mode insert kv" "SELECT * FROM kv;" ^
  ".mode insert _meta" "SELECT * FROM _meta;" | Out-File -Encoding utf8 9router-migrate.sql
```

Expected output: ~100-200KB .sql file with INSERT statements only, no CREATE TABLE/INDEX.

**Verify**: Row counts before export:
```
providerConnections: 92 | settings: 1 | combos: 11 | apiKeys: 2
providerNodes: 4 | proxyPools: 20 | kv: 59 | _meta: 1
```

### Step 2: Copy to VPS

```powershell
scp -P 39999 9router-migrate.sql root@49.12.82.34:/root/
```

### Step 3: Install 9Router on VPS (DETERMINISTIC — exact version pinned)

SSH into VPS, then:

```bash
# Install Node.js 22 if not present
curl -fsSL https://deb.nodesource.com/setup_22.x | bash -
apt install -y nodejs

# Install 9Router — EXACT VERSION PINNED
npm install -g 9router@0.5.8

# RECORD installed version for evidence
npm list -g 9router --depth=0 > /root/9router-installed-version.txt

# Install build tools for native SQLite (better-sqlite3)
apt install -y python3 make g++

# Create data directory
mkdir -p /var/lib/9router

# Create .env with generated secrets
JWT_SECRET=$(openssl rand -hex 32)
API_KEY_SECRET=$(openssl rand -hex 32)
MACHINE_ID_SALT=$(openssl rand -hex 32)

cat > /var/lib/9router/.env <<EOF
JWT_SECRET=${JWT_SECRET}
INITIAL_PASSWORD=<INITIAL_PASSWORD>
DATA_DIR=/var/lib/9router
PORT=20128
HOSTNAME=0.0.0.0
NODE_ENV=production
BASE_URL=http://localhost:20128
API_KEY_SECRET=${API_KEY_SECRET}
MACHINE_ID_SALT=${MACHINE_ID_SALT}
REQUIRE_API_KEY=true
EOF
```

> **Note**: `HOSTNAME=0.0.0.0` — see §7.1 for network model rationale. Firewall enforces Tailscale-only access, not application binding.

### Step 4: Run 9Router Once to Create Fresh DB

```bash
9router --host 0.0.0.0 --port 20128 --no-browser &
NINEROUTER_PID=$!
sleep 5
kill $NINEROUTER_PID
```

This creates the empty DB at `/var/lib/9router/db/data.sqlite` with the correct schema for version 0.5.8.

### Step 5: Import Config Data (SAFE — transaction, backup, verify)

```bash
# Step 5a: Backup the fresh target DB BEFORE any import
cp /var/lib/9router/db/data.sqlite /var/lib/9router/db/data.sqlite.pre-import.bak

# Step 5b: Import in a single transaction
sqlite3 /var/lib/9router/db/data.sqlite <<'SQL'
BEGIN TRANSACTION;
.read /root/9router-migrate.sql
COMMIT;
SQL

# Step 5c: Verify row counts match source
sqlite3 /var/lib/9router/db/data.sqlite "SELECT 'providerConnections', count(*) FROM providerConnections UNION ALL SELECT 'settings', count(*) FROM settings UNION ALL SELECT 'combos', count(*) FROM combos UNION ALL SELECT 'apiKeys', count(*) FROM apiKeys;"
# Expected: providerConnections:92, settings:1, combos:11, apiKeys:2

# Step 5d: If any count mismatch → ROLLBACK to pre-import backup
# cp /var/lib/9router/db/data.sqlite.pre-import.bak /var/lib/9router/db/data.sqlite
```

### Step 6: Create systemd Service

```bash
cat > /etc/systemd/system/9router.service <<'EOF'
[Unit]
Description=9Router AI Gateway
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=/var/lib/9router
EnvironmentFile=/var/lib/9router/.env
ExecStart=/usr/bin/9router --host 0.0.0.0 --port 20128 --no-browser
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable 9router
systemctl start 9router
systemctl status 9router
```

### Step 7: VPS Smoke Test — Verify 9Router Running

```bash
# Basic health check
curl -s http://localhost:20128/v1/models | head -c 200

# Verify provider count
curl -s http://localhost:20128/v1/models | python3 -c "import sys,json; d=json.load(sys.stdin); print(f'Models: {len(d.get(\"data\",[]))}')"
```

Should return valid JSON with model list.

### Step 8: VPS Load Test — Real Load, Real Evidence

```bash
# Install load-test tool (hey — single binary, no deps)
curl -sL https://storage.googleapis.com/hey-releases/hey_linux_amd64 -o /usr/local/bin/hey
chmod +x /usr/local/bin/hey

# Phase 0: Simple model request (functional test — MUST return 200)
echo "=== PHASE 0: FUNCTIONAL ===" > /root/9router-loadtest.txt
curl -s -X POST http://localhost:20128/v1/chat/completions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <API_KEY>" \
  -d '{"model":"gpt-4o","messages":[{"role":"user","content":"say hi"}],"max_tokens":10}' | head -c 300
echo "" >> /root/9router-loadtest.txt

# Phase 1: Warmup (50 concurrent, 100 requests)
echo "=== PHASE 1: WARMUP ===" >> /root/9router-loadtest.txt
hey -n 100 -c 50 -o csv http://localhost:20128/v1/models 2>&1 | tee -a /root/9router-loadtest.txt

# Phase 2: Medium load (100 concurrent, 500 requests)
echo "=== PHASE 2: MEDIUM ===" >> /root/9router-loadtest.txt
hey -n 500 -c 100 -o csv http://localhost:20128/v1/models 2>&1 | tee -a /root/9router-loadtest.txt

# Phase 3: Real model request load (50 concurrent, 200 requests)
echo "=== PHASE 3: REAL MODEL ===" >> /root/9router-loadtest.txt
# Use hey for real chat completions — note: this tests 9Router routing, not just listing
hey -n 200 -c 50 -m POST -H "Content-Type: application/json" -H "Authorization: Bearer <API_KEY>" -d '{"model":"gpt-4o","messages":[{"role":"user","content":"hi"}],"max_tokens":5}' http://localhost:20128/v1/chat/completions 2>&1 | tee -a /root/9router-loadtest.txt

# Capture system metrics during load
echo "=== CPU/MEM AT PEAK ===" >> /root/9router-loadtest.txt
top -b -n 1 | head -5 >> /root/9router-loadtest.txt

# Acceptance criteria (check loadtest output):
# - ALL phases: 0 errors (non-2xx responses)
# - Phase 3: p99 latency < 2000ms
# - Phase 3: CPU < 80%, RAM < 2GB
# If any criterion fails → STOP, investigate, do NOT proceed to firewall
```

### Step 9: S3 Backup — After Smoke & Load Test Pass

```bash
# Check if S3 backup secrets exist
if [ ! -f /root/secrets/backup/restic-s3.env ]; then
  echo "ERROR: S3 backup secrets not found at /root/secrets/backup/"
  echo "S3 backup is REQUIRED for final PASS. Cannot proceed."
  echo "Restore secrets/backup/ from source, then re-run this step."
  exit 1
fi

# If secrets exist, run backup (provider/config only, no logs/history)
restic -r s3:https://s3.idcloudhost.com/guinevere-dr-backups \
  backup /var/lib/9router/db/data.sqlite \
  --tag p25-9router-migration \
  --exclude "*.sqlite-wal" \
  --exclude "*.sqlite-shm" \
  --exclude "usageHistory" \
  --exclude "requestDetails" \
  --exclude "usageDaily"

# Verify object exists
restic -r s3:https://s3.idcloudhost.com/guinevere-dr-backups snapshots --tag p25-9router-migration
```

> **S3 backup is REQUIRED for final PASS.** If backup secrets are missing, this step BLOCKS. Escalate to Faiz.

### Step 10: Tailscale Setup

```bash
# Install if not present
curl -fsSL https://tailscale.com/install.sh | sh

# Connect with netfilter control — nodivert prevents auto-allow-all on tailscale0
tailscale up --netfilter-mode=nodivert --hostname=vps-9router

# Get Tailscale IP
TAILSCALE_IP=$(tailscale ip -4)
echo "Tailscale IP: $TAILSCALE_IP"
```

### Step 11: Firewall — TRUE Add-Only (CHECK FIRST, NEVER RESET)

**Rule: never `ufw reset`, never `ufw --force enable`, never `iptables -F`, never delete SSH rule.**

```bash
# === PHASE A: CAPTURE PRE-EXISTING STATE ===
ufw status verbose > /root/firewall-before.txt
iptables -L INPUT -n --line-numbers >> /root/firewall-before.txt
iptables -L FORWARD -n --line-numbers >> /root/firewall-before.txt
nft list ruleset > /root/firewall-nft-before.txt 2>/dev/null || true

# === PHASE B: CHECK UFW STATUS ===
UFW_STATUS=$(ufw status | head -1)

if echo "$UFW_STATUS" | grep -q "inactive"; then
  # UFW is inactive — set defaults BEFORE enabling
  ufw default deny incoming
  ufw default allow outgoing
  ufw allow 39999/tcp comment 'SSH non-standard port'
  ufw allow in on tailscale0 comment 'Tailscale interface'
  ufw enable
else
  # UFW is active — ADD ONLY, never change defaults
  # Check if SSH rule exists before adding
  if ! ufw status | grep -q "39999/tcp"; then
    ufw allow 39999/tcp comment 'SSH non-standard port'
  fi
  # Check if tailscale0 rule exists before adding
  if ! ufw status | grep -q "tailscale0"; then
    ufw allow in on tailscale0 comment 'Tailscale interface'
  fi
fi

# === PHASE C: iptables — ADD ONLY (port 20128 on tailscale0) ===
# Check if rule already exists
if ! iptables -C INPUT -i tailscale0 -p tcp --dport 20128 -j ACCEPT 2>/dev/null; then
  iptables -A INPUT -i tailscale0 -p tcp --dport 20128 -j ACCEPT
fi

# Block 20128 on public interface (whatever it's named)
PUBLIC_IFACE=$(ip route get 1.1.1.1 | grep -oP 'dev \K\S+')
if ! iptables -C INPUT -i "$PUBLIC_IFACE" -p tcp --dport 20128 -j DROP 2>/dev/null; then
  iptables -A INPUT -i "$PUBLIC_IFACE" -p tcp --dport 20128 -j DROP
fi

# === PHASE D: MAKE PERSISTENT ===
apt-get install -y iptables-persistent
netfilter-persistent save

# === PHASE E: VERIFY ===
ufw status verbose > /root/firewall-after.txt
iptables -L INPUT -n --line-numbers >> /root/firewall-after.txt

# === PHASE F: VERIFY SSH STILL WORKS ===
# Open a NEW SSH session in a separate terminal before proceeding
# If SSH fails: the rules are append-only so the old session should still work
# Use the old session to fix: iptables -D INPUT -i <iface> -p tcp --dport 20128 -j DROP
```

### Step 12: Verify Access — Three-Way Test

```bash
# === TEST 1: Localhost (always works) ===
curl -s http://localhost:20128/v1/models | head -c 100
echo "TEST 1 PASS: localhost OK"

# === TEST 2: Tailscale (MUST work) ===
curl -s --max-time 5 http://${TAILSCALE_IP}:20128/v1/models | head -c 100
echo "TEST 2 PASS: Tailscale IP OK"

# === TEST 3: Public IP (MUST FAIL) ===
# NOTE: This test runs from the VPS itself — self-curl to public IP is NOT a
# definitive public-block proof (traffic may loop back differently).
# External proof (e.g., curl from Windows local to public IP:20128) must be
# performed separately. If that external test fails, public-block is NOT
# confirmed and migration is BLOCKED.
PUBLIC_IP=$(curl -s --max-time 5 ifconfig.me 2>/dev/null || curl -s --max-time 5 icanhazip.com)
echo "VPS public IP: ${PUBLIC_IP}"
echo "=== TEST 3a: Self-curl from VPS (preliminary only) ==="
if curl -s --max-time 5 http://${PUBLIC_IP}:20128/v1/models > /dev/null 2>&1; then
  echo "TEST 3a WARN: Self-curl reached 9Router (may be loopback). External test required."
else
  echo "TEST 3a: Self-curl blocked (promising, but external proof still required)"
fi

echo "=== TEST 3b: External proof REQUIRED ==="
echo "Run from Windows local: curl --max-time 5 http://${PUBLIC_IP}:20128/v1/models"
echo "If this returns data → PUBLIC-BLOCK FAILED → DO NOT PROCEED"
echo "If this times out/refused → PUBLIC-BLOCK PASS"
```

### Step 13: Update Client Endpoints

**On Windows local**, update ONLY the base URL. Do NOT overwrite `ANTHROPIC_AUTH_TOKEN`.

1. **`C:\Users\faizz\.config\opencode\opencode.json`** — line 120: change `baseURL` from `http://localhost:20128/v1` to `http://<TAILSCALE_IP>:20128/v1`
   - Do NOT touch `apiKey` — it stays `<API_KEY>` (placeholder, never in plan/evidence)
2. **`C:\Users\faizz\.claude\settings.json`** — change `ANTHROPIC_BASE_URL` from `http://127.0.0.1:20128/v1` to `http://<TAILSCALE_IP>:20128/v1`
   - Do NOT touch `ANTHROPIC_AUTH_TOKEN` — it stays the same API key
3. **Windows env vars**: update `ANTHROPIC_BASE_URL` only. Do NOT change `ANTHROPIC_AUTH_TOKEN`.

### Step 14: Final Verification

1. OpenCode works with new endpoint — test a simple prompt
2. Claude Code works with new endpoint — test a simple prompt
3. All providers show active in 9Router dashboard at `http://<TAILSCALE_IP>:20128`

### Step 15: Shutdown Local 9Router

```powershell
Stop-Process -Id <local-9router-pid>
```

Or via Task Manager.

---

## 3. Network Model — §7.1 Clarification

**Decision: Bind 0.0.0.0 + firewall enforces Tailscale-only.**

Why not bind to Tailscale IP directly:
- Tailscale IP can change on reconnect
- Binding to a specific IP complicates the systemd unit (env var injection ordering)
- 9Router's `HOSTNAME` env var is read at startup — if Tailscale isn't up yet, binding fails

**How Tailscale-only is enforced**:
1. iptables rule DROPs port 20128 on the public interface
2. iptables rule ACCEPTs port 20128 on tailscale0
3. UFW allows tailscale0 interface traffic
4. `--netfilter-mode=nodivert` prevents Tailscale's auto-allow-all bypass

**Public internet blocked**: Verified by Test 3 in Step 12. If Test 3 fails (public IP can reach 9Router), the migration is BLOCKED until fixed.

---

## 4. Known Caveats

| Issue | Impact | Mitigation |
|---|---|---|
| OAuth tokens (kiro, qoder, codex) likely expired | ~23 OAuth connections need re-auth | Re-auth from VPS 9Router dashboard after migration |
| API keys are plaintext in SQL | Migration file contains raw keys | Delete `9router-migrate.sql` from both machines after import |
| 9Router binds 0.0.0.0, not Tailscale IP | Application listens on all interfaces | Firewall blocks public interface, allows only tailscale0 |
| S3 backup secrets may be missing | Can't run automated S3 backup → BLOCKED | Escalate to Faiz; S3 backup is required for final PASS |
| Tailscale IP can change | Client endpoints break | Use MagicDNS (`vps-9router.<tailnet>.ts.net`) as stable hostname |
| Local SQLite has native `better-sqlite3` | VPS needs build tools | Install `python3 make g++` in Step 3 |
| `modelLock_*` error-state timestamps | May trigger false rate-limit | Auto-clears on successful request |

---

## 5. Rollback Plan

If anything breaks:

1. Stop VPS 9Router: `systemctl stop 9router`
2. Restore client endpoints to `localhost:20128`
3. Start local 9Router
4. Debug VPS separately
5. VPS DB is backed up at `/var/lib/9router/db/data.sqlite.pre-import.bak` — restore if needed

---

## 6. Evidence

All evidence goes to `docs/setup-evidence/P25/evidence/`:
- `step1-export.txt` — row counts before export
- `step3-version.txt` — installed 9Router version
- `step5-verify.txt` — row counts after import
- `step8-loadtest.txt` — load test results
- `step9-backup.txt` — S3 backup snapshot ID
- `step11-firewall-before.txt` — pre-change firewall state
- `step11-firewall-after.txt` — post-change firewall state
- `step12-access-test.txt` — three-way access test results

---

**Status**: REPLAN FIXED — READY FOR MAMA APPROVAL  
**Next**: Mama approval → execute step-by-step with verification at each gate