# P0-028 Pre-Flight Verification Patterns

> **Goal**: Systematic pre-flight verification checklist and shell script patterns for Linux VPS production deployments.
> **Stack**: PostgreSQL (5433), PgBouncer (5434), Redis (6380), Caddy (8443/3443/9443), fail2ban, CrowdSec, UFW, Tailscale, Cloudflare Tunnel.
> **Date**: 2026-05-31

---

## Table of Contents

1. [Multi-Service Health Check Architecture](#1-multi-service-health-check-architecture)
2. [Service-Specific Checks](#2-service-specific-checks)
3. [Resource Verification](#3-resource-verification)
4. [Complete Integration Script](#4-complete-integration-script)
5. [Source References](#5-source-references)

---

## 1. Multi-Service Health Check Architecture

### 1.1 Exit Code Aggregation Pattern

The canonical pattern for checking multiple services while collecting all failures (not failing fast):

```bash
#!/usr/bin/env bash
set -euo pipefail

# ---- Exit code aggregation ----
OVERALL_EXIT=0

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        echo "[PASS] $name"
    else
        echo "[FAIL] $name"
        OVERALL_EXIT=1
    fi
}

# Usage: check "description" command arg1 arg2
check "PostgreSQL on 5433" pg_isready -h localhost -p 5433
check "Redis on 6380"      redis-cli -h localhost -p 6380 PING

exit "$OVERALL_EXIT"
```

**Key design notes** (from blog.bariskode.com and deployhq.com):
- Each check returns 0 (pass) or non-zero (fail)
- `OVERALL_EXIT` is set to 1 if any single check fails
- All checks run regardless of previous failures — no short-circuit
- Context-rich pass/fail messages per check
- Non-zero exit on preflight failure is confirmed in scheduler logs

### 1.2 Critical: `systemctl is-active` with Multiple Args Has Pitfall

From systemd/systemd issue #11826:

> `systemctl is-active svc1 svc2` returns 0 if **at least one** is active, not only when all are active.

**Workaround**: Check each service individually:

```bash
# WRONG — returns 0 if just one is active
systemctl is-active --quiet postgresql redis-server && echo "all good"

# CORRECT — check individually
for svc in postgresql redis-server caddy; do
    systemctl is-active --quiet "$svc" || {
        echo "FAIL: $svc is not active"
        OVERALL_EXIT=1
    }
done
```

### 1.3 Dependency Check Pattern

Before any service checks, verify required binaries exist:

```bash
require() {
    command -v "$1" &>/dev/null || {
        printf 'Missing required binary: %s\n' "$1" >&2
        exit 1
    }
}
require pg_isready
require redis-cli
require psql
require curl
require ss
```

---

## 2. Service-Specific Checks

### 2.1 PostgreSQL (port 5433)

**Primary tool**: `pg_isready` (PostgreSQL documentation)

```bash
# Basic check on non-standard port
pg_isready -h localhost -p 5433

# Quiet mode for scripting
pg_isready -h localhost -p 5433 -q

# Return codes:
#   0 = accepting connections
#   1 = rejecting connections (startup)
#   2 = no response
#   3 = invalid parameters
```

**Wait-loop pattern** (from reemus.dev):

```bash
wait_for_postgres() {
    local retries=10 interval=3
    local count=0
    until pg_isready -h localhost -p 5433 -q 2>/dev/null; do
        count=$((count + 1))
        if [ "$count" -ge "$retries" ]; then
            echo "PostgreSQL not ready after ${retries} attempts"
            return 1
        fi
        echo "Waiting for PostgreSQL... attempt ${count}"
        sleep "$interval"
    done
    return 0
}
```

**Deep connection check via psql**:

```bash
# Verify actual query execution through connection pool
psql -h localhost -p 5433 -U postgres -d postgres -c "SELECT 1" >/dev/null 2>&1

# PgBouncer passes SELECT 1 through, so this validates the full chain
```

### 2.2 PgBouncer (port 5434)

**Connect to admin database** (pgbouncer.org/usage.html):

```bash
SHOW_HELP="
  SHOW HELP|CONFIG|DATABASES|POOLS|CLIENTS|SERVERS|USERS|VERSION
  SHOW STATS|STATS_TOTALS|STATS_AVERAGES|TOTALS
  SET key = arg
  RELOAD
  PAUSE [<db>]
  RESUME [<db>]
  DISABLE <db>
  ENABLE <db>
"

# Check PgBouncer is alive via admin console
psql -h localhost -p 5434 -U pgbouncer_admin -d pgbouncer -c "SHOW VERSION;" >/dev/null 2>&1
```

**Pool health check** (from OneUptime and CubePath):

```bash
# Show pool status
psql -h localhost -p 5434 -U pgbouncer_admin -d pgbouncer -c "SHOW POOLS;"

# Will show columns: database, user, cl_active, cl_waiting, sv_active, sv_idle, pool_mode

# Check for clients waiting (might indicate pool saturation)
psql -h localhost -p 5434 -U pgbouncer_admin -d pgbouncer -t -A \
  -c "SELECT SUM(cl_waiting) FROM pgbouncer.pools;" 2>/dev/null
```

**Simple health check via psql query passthrough** (from OneUptime):

```bash
# Connect THROUGH PgBouncer (port 5434) to app database, validate pass-through
RESULT=$(psql -h localhost -p 5434 -U myapp_user -d myapp -t -A -c "SELECT 1" 2>/dev/null)
if [ "$RESULT" = "1" ]; then
    echo "PgBouncer OK"
fi
```

**TCP port probe** (from Deliveroo pgbouncer-healthcheck):

```bash
# Simple port-probe fallback
timeout 3 bash -c 'echo >/dev/tcp/localhost/5434' 2>/dev/null
```

### 2.3 Redis (port 6380)

**PING on non-standard port** (redis.io/docs):

```bash
# -h defaults to 127.0.0.1, -p specifies port
redis-cli -h localhost -p 6380 PING
# Returns "PONG" + exit 0 on success

# For scripting: suppress output, check exit code
redis-cli -h localhost -p 6380 PING >/dev/null 2>&1
```

**Advanced health check** (from OneUptime):

```bash
check_redis() {
    local host="${REDIS_HOST:-localhost}"
    local port="${REDIS_PORT:-6380}"

    # 1. Connectivity check
    PING=$(redis-cli -h "$host" -p "$port" PING 2>&1)
    if [ "$PING" != "PONG" ]; then
        echo "FAIL: Redis not responding to PING (got: $PING)"
        return 1
    fi

    # 2. Memory check (optional)
    MEM_PCT=$(redis-cli -h "$host" -p "$port" INFO memory | \
              grep "^used_memory_rss:" | cut -d: -f2)
    # Compare against maxmemory if configured

    # 3. Key count check
    KEYS=$(redis-cli -h "$host" -p "$port" DBSIZE)
    echo "Redis OK | keys=$KEYS"

    return 0
}
```

**Write/read verification** (production-grade):

```bash
redis-cli -h localhost -p 6380 SET healthcheck "ok" EX 30 >/dev/null
VALUE=$(redis-cli -h localhost -p 6380 GET healthcheck)
if [ "$VALUE" != "ok" ]; then
    echo "FAIL: Redis write/read test failed"
    exit 1
fi
```

### 2.4 Caddy (ports 8443/3443/9443)

**Admin API health check** (from caddyserver/caddy issue #6033):

```bash
# Caddy exposes admin API on localhost:2019 by default
# A simple GET to /config/ or any endpoint confirms it's running
curl -sf http://localhost:2019/config/ >/dev/null 2>&1

# If using HTTPS mode on non-standard ports, check via curl
curl -sf -o /dev/null -w "%{http_code}" https://localhost:8443/ 2>/dev/null
# Returns 000 if connection refused, 200+ if Caddy responds

# Check port bindings
ss -tlnp | grep -E '(8443|3443|9443)'
```

**Port listening verification** (from test-caddyfile.sh):

```bash
# Verify Caddy is listening by port
timeout 3 bash -c 'echo >/dev/tcp/localhost/8443' 2>/dev/null && \
    echo "Caddy on 8443: listening"

timeout 3 bash -c 'echo >/dev/tcp/localhost/3443' 2>/dev/null && \
    echo "Caddy on 3443: listening"

timeout 3 bash -c 'echo >/dev/tcp/localhost/9443' 2>/dev/null && \
    echo "Caddy on 9443: listening"
```

**Health check endpoint pattern** (caddy works with `/.well-known/caddy/health`):

```bash
# If a health endpoint is configured in Caddyfile
curl -sf https://localhost:8443/.well-known/caddy/health >/dev/null 2>&1
```

### 2.5 fail2ban

**Status checks** (from Arch man pages and LuKrlier/secure-vps-setup):

```bash
# Systemd service status
systemctl is-active --quiet fail2ban

# Fail2ban server ping
fail2ban-client ping
# Returns "pong" if server is alive

# SSH jail status
fail2ban-client status sshd
# Shows: Status, Total banned, Currently banned, Total found

# Check specific jail
systemctl is-active --quiet fail2ban && \
    fail2ban-client status sshd >/dev/null 2>&1

# Get banned IPs count
BANNED=$(sudo fail2ban-client get sshd banned 2>/dev/null)
echo "fail2ban sshd: $BANNED currently banned IPs"
```

### 2.6 CrowdSec

**Health checks** (from crowdsec.net/docs):

```bash
# Systemd service
systemctl is-active --quiet crowdsec

# LAPI status (Local API)
cscli lapi status 2>/dev/null
# Returns OK if LAPI is responding

# Health endpoint (if configured on default port 8081)
curl -sf http://localhost:8081/health 2>/dev/null
# Returns {"status":"up"}

# Metrics check
cscli metrics 2>/dev/null | head -20

# Check installed scenarios/hub status
cscli hub list 2>/dev/null | head -10
```

**Docker healthcheck pattern** (from crowdsec PR #4161):

```bash
# The healthcheck registered in CrowdSec Docker images:
cscli lapi status
# If this exits 0, LAPI is healthy
```

### 2.7 UFW

**Status and rule verification**:

```bash
# Check UFW is active
ufw status | grep -q "Status: active"

# Verbose status with rules
ufw status verbose

# Check specific port rules
ufw status | grep -q "5433"
ufw status | grep -q "5434"
ufw status | grep -q "6380"

# Check default deny policy
ufw status verbose | grep -q "deny (incoming)"

# Verify Tailscale interface rule (if applicable)
ufw status | grep -q "tailscale0"
```

### 2.8 Tailscale

**Status checks** (from Tailscale docs and homelab.codes):

```bash
# Daemon running
systemctl is-active --quiet tailscaled

# Tailscale connection status
tailscale status
# Shows all connected nodes with their IPs and online status

# Get Tailscale IP
tailscale ip -4

# JSON status for scripting
tailscale status --json | jq -r '.Self.Online'

# Check connection state via systemctl
systemctl status tailscaled | grep -q "Status.*Connected"

# Simple online check
if tailscale status >/dev/null 2>&1; then
    echo "Tailscale connected"
    tailscale ip -4
else
    echo "Tailscale not connected"
fi
```

**Comprehensive check** (from homelab.codes Tailscale monitoring):

```bash
check_tailscale() {
    if ! systemctl is-active --quiet tailscaled; then
        echo "FAIL: tailscaled daemon not running"
        return 1
    fi

    local ip
    ip=$(tailscale ip -4 2>/dev/null)
    if [ -z "$ip" ]; then
        echo "FAIL: No Tailscale IP assigned"
        return 1
    fi

    if systemctl status tailscaled | grep -q "Status.*Connected"; then
        echo "PASS: Tailscale connected (IP: $ip)"
        return 0
    else
        echo "FAIL: Tailscale not showing connected status"
        return 1
    fi
}
```

### 2.9 Cloudflare Tunnel (cloudflared)

**Status checks** (from developerdocs.cloudflare.com):

```bash
# Systemd service
systemctl is-active --quiet cloudflared

# Tunnel list
cloudflared tunnel list

# Tunnel info (replace <tunnel-name>)
cloudflared tunnel info <tunnel-name>

# Ready endpoint (requires metrics enabled)
cloudflared tunnel ready

# Metrics endpoint health check (if metrics exposed on port 60123)
curl -sf http://localhost:60123/ready 2>/dev/null

# Daemon logs for connection status
journalctl -u cloudflared -n 20 --no-pager

# External DNS verification
dig +short CNAME <your-domain>  # should point to <tunnel-id>.cfargotunnel.com
```

**Comprehensive check** (from wiunix.com):

```bash
check_cloudflare_tunnel() {
    # 1. Service running
    systemctl is-active --quiet cloudflared || {
        echo "FAIL: cloudflared not running"
        return 1
    }

    # 2. Tunnel status via CLI
    cloudflared tunnel list 2>/dev/null | grep -q "healthy" || {
        echo "WARN: Tunnel may not be healthy"
        # Not returning 1 — could be transient
    }

    # 3. External endpoint check
    curl -sf -o /dev/null -w "%{http_code}" https://<your-domain>/ 2>/dev/null

    return 0
}
```

---

## 3. Resource Verification

### 3.1 Disk Space

**Standard pattern** (from deployhq.com and techstackguide.com):

```bash
DISK_WARN=${DISK_WARN:-80}
DISK_CRIT=${DISK_CRIT:-90}

check_disk() {
    local rc=0
    while read -r filesystem size used avail percent mount; do
        local pct="${percent%\%}"
        if [ "$pct" -ge "$DISK_CRIT" ]; then
            echo "CRITICAL: $mount at ${pct}%"
            rc=2
        elif [ "$pct" -ge "$DISK_WARN" ]; then
            echo "WARNING: $mount at ${pct}%"
            [ "$rc" -lt 1 ] && rc=1
        fi
    done < <(df -h -x tmpfs -x devtmpfs -x squashfs | tail -n +2)
    return $rc
}
```

### 3.2 Memory

```bash
MEM_WARN=${MEM_WARN:-75}
MEM_CRIT=${MEM_CRIT:-90}

check_memory() {
    local total used pct
    total=$(free -b | awk '/^Mem:/{print $2}')
    used=$(free -b | awk '/^Mem:/{print $3}')
    pct=$(( 100 * used / total ))

    if [ "$pct" -ge "$MEM_CRIT" ]; then
        echo "CRITICAL: Memory at ${pct}%"
        return 2
    elif [ "$pct" -ge "$MEM_WARN" ]; then
        echo "WARNING: Memory at ${pct}%"
        return 1
    fi
    echo "OK: Memory at ${pct}%"
    return 0
}

# Alternative: check available memory in MB
check_memory_avail() {
    local avail_mb
    avail_mb=$(free -m | awk '/^Mem:/{print $7}')
    if [ "$avail_mb" -lt 200 ]; then
        echo "CRITICAL: Only ${avail_mb}MB available"
        return 2
    fi
    echo "OK: ${avail_mb}MB available"
    return 0
}
```

### 3.3 CPU Load

```bash
CPU_WARN=${CPU_WARN:-1.5}  # load per core
CPU_CRIT=${CPU_CRIT:-3.0}

check_cpu_load() {
    local cores load_1min
    cores=$(nproc)
    load_1min=$(awk '{print $1}' /proc/loadavg)

    local load_per_core
    load_per_core=$(echo "scale=2; $load_1min / $cores" | bc 2>/dev/null || echo 0)

    if (( $(echo "$load_per_core > $CPU_CRIT" | bc -l) )); then
        echo "CRITICAL: Load ${load_1min} (${load_per_core}/core)"
        return 2
    elif (( $(echo "$load_per_core > $CPU_WARN" | bc -l) )); then
        echo "WARNING: Load ${load_1min} (${load_per_core}/core)"
        return 1
    fi
    echo "OK: Load ${load_1min} (${load_per_core}/core)"
    return 0
}
```

### 3.4 File Descriptors & Resource Limits

```bash
check_limits() {
    echo "=== File Descriptors ==="
    local used max
    read -r used free max < /proc/sys/fs/file-nr
    echo "  Open FDs: $used / $max"
    if [ "$used" -gt $(( max * 90 / 100 )) ]; then
        echo "  WARNING: FD usage above 90%"
    fi

    echo "=== System Limits ==="
    echo "  ulimit -n: $(ulimit -n)"
    echo "  ulimit -u: $(ulimit -u)"
    echo "  Max PID: $(cat /proc/sys/kernel/pid_max)"
    echo "  Processes: $(ps aux | wc -l)"

    # Check specific service limits (example for postgres)
    for svc in postgres caddy; do
        local pid
        pid=$(pgrep -x "$svc" 2>/dev/null | head -1)
        if [ -n "$pid" ]; then
            echo "  $svc (PID $pid): $(grep 'Max open files' /proc/$pid/limits 2>/dev/null || echo 'N/A')"
        fi
    done
}
```

### 3.5 Port Binding Verification

```bash
check_port_bindings() {
    local ports=(5433 5434 6380 8443 3443 9443 2019 8081)
    for port in "${ports[@]}"; do
        if ss -tlnp | grep -q ":$port "; then
            local proc
            proc=$(ss -tlnp | grep ":$port " | awk '{print $7}' | tr -d '()"' | head -1)
            echo "  Port $port: LISTEN ($proc)"
        else
            echo "  Port $port: NOT LISTENING"
        fi
    done
}
```

---

## 4. Complete Integration Script

Below is a skeleton integrating all patterns. Adapt paths, ports, and thresholds as needed.

```bash
#!/usr/bin/env bash
# P0-028 Pre-Flight Verification Script
# Usage: ./preflight-check.sh [--verbose]
set -euo pipefail

OVERALL_EXIT=0
VERBOSE=false
[[ "${1:-}" == "--verbose" ]] && VERBOSE=true

log() {
    local level="$1" msg="$2"
    echo "[${level}] ${msg}"
}

check() {
    local name="$1"
    shift
    if "$@" >/dev/null 2>&1; then
        log "PASS" "$name"
    else
        log "FAIL" "$name"
        OVERALL_EXIT=1
    fi
}

# ============================================================
# Phase 1: Binary Dependencies
# ============================================================
log "INFO" "=== Phase 1: Binary Dependencies ==="
for cmd in pg_isready redis-cli psql curl ss ufw tailscale fail2ban-client; do
    command -v "$cmd" >/dev/null 2>&1 || log "WARN" "Missing binary: $cmd"
done

# ============================================================
# Phase 2: systemd Service Status
# ============================================================
log "INFO" "=== Phase 2: Systemd Services ==="
for svc in postgresql pgbouncer redis-server caddy fail2ban crowdsec tailscaled cloudflared; do
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log "PASS" "systemd: $svc"
    else
        log "FAIL" "systemd: $svc"
        OVERALL_EXIT=1
    fi
done

# Check for any failed units
if systemctl --failed --no-legend | grep -q .; then
    log "FAIL" "Failed systemd units exist"
    systemctl --failed --no-legend
    OVERALL_EXIT=1
fi

# ============================================================
# Phase 3: Port Bindings
# ============================================================
log "INFO" "=== Phase 3: Port Bindings ==="
for port in 5433 5434 6380 8443 3443 9443 2019; do
    check "Port $port listening" ss -tlnp src ":${port}"
done

# ============================================================
# Phase 4: Database Layer
# ============================================================
log "INFO" "=== Phase 4: Databases ==="
check "PostgreSQL (pg_isready -p 5433)" pg_isready -h localhost -p 5433 -q
check "PgBouncer (SHOW VERSION)" psql -h localhost -p 5434 -U pgbouncer_admin -d pgbouncer -c "SHOW VERSION;"
check "Redis PING :6380" redis-cli -h localhost -p 6380 PING

# ============================================================
# Phase 5: Web Layer
# ============================================================
log "INFO" "=== Phase 5: Web Layer ==="
check "Caddy admin API" curl -sf http://localhost:2019/config/
# Selective HTTPS checks (skip if certs not yet configured)
if pgrep -x caddy >/dev/null; then
    for caddy_port in 8443 3443 9443; do
        timeout 3 bash -c "echo >/dev/tcp/localhost/${caddy_port}" 2>/dev/null && \
            log "PASS" "Caddy HTTPS port ${caddy_port}" || \
            log "WARN" "Caddy port ${caddy_port} not reachable (might be TLS)"
    done
fi

# ============================================================
# Phase 6: Security Layer
# ============================================================
log "INFO" "=== Phase 6: Security ==="
check "UFW active" ufw status verbose
check "fail2ban ping" fail2ban-client ping
check "CrowdSec LAPI" cscli lapi status

# ============================================================
# Phase 7: Network Layer
# ============================================================
log "INFO" "=== Phase 7: Network ==="
check "Tailscale daemon" systemctl is-active --quiet tailscaled
if systemctl is-active --quiet tailscaled 2>/dev/null; then
    check "Tailscale IP assigned" tailscale ip -4
fi
check "Cloudflared service" systemctl is-active --quiet cloudflared

# ============================================================
# Phase 8: Resources
# ============================================================
log "INFO" "=== Phase 8: Resources ==="
DISK_PCT=$(df / | awk 'NR==2{print $5}' | tr -d '%')
if [ "$DISK_PCT" -gt 90 ]; then
    log "FAIL" "Disk usage critical: ${DISK_PCT}%"
    OVERALL_EXIT=1
else
    log "PASS" "Disk usage: ${DISK_PCT}%"
fi

MEM_AVAIL=$(free -m | awk '/^Mem:/{print $7}')
if [ "$MEM_AVAIL" -lt 200 ]; then
    log "WARN" "Low memory: ${MEM_AVAIL}MB available"
fi

# ============================================================
# Summary
# ============================================================
echo ""
if [ "$OVERALL_EXIT" -eq 0 ]; then
    log "PASS" "ALL CHECKS PASSED — System is ready for P1"
else
    log "FAIL" "SOME CHECKS FAILED — Review output above before proceeding to P1"
fi
exit "$OVERALL_EXIT"
```

---

## 5. Source References

| Topic | Source | URL |
|-------|--------|-----|
| Preflight checks philosophy | Baris Kode — Shell Script Preflight Checks on Linux | https://blog.bariskode.com/blog/shell-script-preflight-checks-linux-automation-reliability-guide/ |
| pg_isready docs | PostgreSQL Documentation — app-pg-isready | https://www.postgresql.org/docs/current/app-pg-isready.html |
| pg_isready wait-loop | reemus.dev — Check & Wait For PostgreSQL | https://reemus.dev/tldr/postgres-wait-for-ready-bash-script.mdx |
| PgBouncer admin console | pgbouncer.org — usage.html | https://www.pgbouncer.org/usage.html |
| PgBouncer monitoring | CubePath — Database connection pooling with PgBouncer | https://cubepath.com/docs/database-advanced/database-connection-pooling-with-pgbouncer |
| PgBouncer health check | OneUptime — How to Set Up PgBouncer | https://oneuptime.com/blog/post/2026-02-20-postgresql-connection-pooling-pgbouncer/view |
| redis-cli reference | Redis Docs — CLI | https://redis.io/docs/latest/develop/tools/cli/ |
| Redis health check | OneUptime — Redis Health Check Script | https://oneuptime.com/blog/post/2026-03-31-redis-health-check-script/view |
| Caddy admin API | caddyserver/caddy issue #6033 | https://github.com/caddyserver/caddy/issues/6033 |
| Caddy admin health | Caddy Documentation — Getting Started | https://caddyserver.com/docs/getting-started |
| Caddy HTTPS ports | Caddy Documentation — Global Options | https://caddyserver.com/docs/caddyfile/options |
| fail2ban-client | Arch man pages — fail2ban-client | https://man.archlinux.org/man/extra/fail2ban/fail2ban-client.1.en |
| CrowdSec health | CrowdSec Docs — cscli lapi status | https://docs.crowdsec.net/docs/observability/cscli/ |
| CrowdSec /health | crowdsecurity/crowdsec PR #881 | https://github.com/crowdsecurity/crowdsec/pull/881 |
| Tailscale monitoring | homelab.codes — Tailscale Health Monitoring | https://homelab.codes/blog/2024-12-30-tailscale-monitoring-uptime-kuma |
| Tailscale + UFW | Tailscale Docs — Secure Ubuntu with UFW | https://tailscale.com/docs/how-to/secure-ubuntu-server-with-ufw |
| Cloudflare Tunnel monitoring | Cloudflare Docs — Monitoring | https://developers.cloudflare.com/tunnel/monitoring/ |
| Cloudflared ready | cloudflare/cloudflared issue #204 | https://github.com/cloudflare/cloudflared/issues/204 |
| systemctl is-active pitfall | systemd/systemd issue #11826 | https://github.com/systemd/systemd/issues/11826 |
| Deploy pre-check script | DeployHQ — Essential Linux server commands | https://www.deployhq.com/blog/essential-linux-server-commands-for-deployment |
| System health toolkit | Bubobot-Team/sysadmin-toolkit | https://github.com/Bubobot-Team/sysadmin-toolkit |
| Bash production toolkit | fidpa/bash-production-toolkit | https://github.com/fidpa/bash-production-toolkit |
| VPS secure setup | LuKrlier/secure-vps-setup | https://github.com/LuKrlier/secure-vps-setup |
| Complete VPS setup | buildplan/du_setup | https://github.com/buildplan/du_setup |
| Resource limits guide | Binadit — Linux Resource Limits | https://binadit.com/tutorials/configure-linux-system-resource-limits-with-systemd-and-ulimit-for-application-performance |
| Disk/memory health check | commandinline.com — Shell Script Server Health Check | https://www.commandinline.com/shell-script-server-health-check/ |
| Automated health check | OneUptime — Automated Health Check Ubuntu | https://oneuptime.com/blog/post/2026-03-02-how-to-create-automated-health-check-scripts-on-ubuntu/view |
| Defensive bash scripting | iliaal/compound-engineering-plugin — Linux Bash Scripting SKILL | https://github.com/iliaal/compound-engineering-plugin |