#!/usr/bin/env bash
# ============================================================================
# P0-028 Pre-Flight Verification Script — Guinevere VPS
# ============================================================================
# Description:
#   Comprehensive read-only verification of ALL Guinevere production services,
#   connectivity, security, networking, encryption, resources, Aizanta
#   containers, and backup readiness before P1 can start.
#
# Usage:
#   ./preflight-check.sh               # Standard run
#   ./preflight-check.sh --verbose     # Show check details (all output)
#   ./preflight-check.sh --json        # JSON summary output
#
# Exit codes:
#   0  = ALL CHECKS PASSED
#   1  = At least one FAIL
# ============================================================================

set -euo pipefail

# ---- Config ---------------------------------------------------------------
VERBOSE=false
JSON_OUT=false
for arg in "$@"; do
    case "$arg" in
        --verbose) VERBOSE=true ;;
        --json)    JSON_OUT=true ;;
    esac
done

# ---- Globals --------------------------------------------------------------
PASS=0; FAIL=0; WARN=0
OVERALL_EXIT=0

# ---- Helpers --------------------------------------------------------------
log_pass() { echo "  [PASS] $*"; }
log_fail() { echo "  [FAIL] $*"; }
log_warn() { echo "  [WARN] $*"; }
log_info() { echo "  [....] $*"; }

check_cmd() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        log_pass "$name"
        ((PASS++))
    else
        log_fail "$name"
        ((FAIL++))
        OVERALL_EXIT=1
    fi
}

check_cmd_verbose() {
    local name="$1"; shift
    local rc=0 output
    output=$("$@" 2>&1) || rc=$?
    if [ "$rc" -eq 0 ]; then
        log_pass "$name"
        ((PASS++))
    else
        log_fail "$name"
        ((FAIL++))
        OVERALL_EXIT=1
    fi
    if $VERBOSE && [ -n "$output" ]; then
        echo "         $output" | head -5
    fi
}

check_cmd_output() {
    local name="$1"; shift
    local expected="$1"; shift
    local output
    output=$("$@" 2>&1) || true
    if echo "$output" | grep -q "$expected"; then
        log_pass "$name"
        ((PASS++))
    else
        log_fail "$name (expected: $expected, got: $(echo "$output" | head -1))"
        ((FAIL++))
        OVERALL_EXIT=1
    fi
    if $VERBOSE; then echo "         $output" | head -3; fi
}

check_warn() {
    local name="$1"; shift
    if "$@" >/dev/null 2>&1; then
        log_pass "$name"
        ((PASS++))
    else
        log_warn "$name"
        ((WARN++))
    fi
}

check_systemctl() {
    local svc="$1"
    local name="$2"
    if systemctl is-active --quiet "$svc" 2>/dev/null; then
        log_pass "$name"
        ((PASS++))
    else
        local state
        state=$(systemctl is-active "$svc" 2>/dev/null || echo "not-found")
        log_fail "$name (state: $state)"
        ((FAIL++))
        OVERALL_EXIT=1
    fi
}

require_bin() {
    command -v "$1" &>/dev/null || log_warn "Missing binary: $1 (some checks may fail)"
}

# ============================================================================
# SECTION 0 — Binary Prerequisites (informational only)
# ============================================================================
echo ""
echo "================================================================"
echo "  P0-028 GUINEVERE PRE-FLIGHT VERIFICATION"
echo "================================================================"
echo "  Started: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "  Host:    $(hostname 2>/dev/null || echo 'unknown')"
echo "  User:    $(whoami 2>/dev/null || echo 'unknown')"
echo "================================================================"
echo ""

log_info "Checking binary dependencies..."
for bin in pg_isready psql redis-cli ss ufw fail2ban-client cscli \
           tailscale cloudflared sops age-keygen restic docker systemctl; do
    require_bin "$bin"
done

# ============================================================================
# SECTION 1 — Services (systemctl is-active, INDIVIDUALLY)
# ============================================================================
echo ""
echo "--- SECTION 1: Services ----------------------------------------------"

check_systemctl "postgresql@17-guinevere.service"  "postgresql@17-guinevere.service → ACTIVE"
check_systemctl "pgbouncer.service"                "pgbouncer.service → ACTIVE"
check_systemctl "redis-guinevere.service"          "redis-guinevere.service → ACTIVE"
check_systemctl "fail2ban.service"                 "fail2ban.service → ACTIVE"
check_systemctl "crowdsec.service"                 "crowdsec.service → ACTIVE"
check_systemctl "caddy.service"                    "caddy.service → ACTIVE"
check_systemctl "tailscaled.service"               "tailscaled.service → ACTIVE"
check_systemctl "cloudflared.service"              "cloudflared.service → ACTIVE"
check_systemctl "chrony.service"                   "chrony.service → ACTIVE"

# ============================================================================
# SECTION 2 — Database Connectivity
# ============================================================================
echo ""
echo "--- SECTION 2: Database Connectivity ---------------------------------"

check_cmd "pg_isready -h 127.0.0.1 -p 5433 (accepting connections)" \
    pg_isready -h 127.0.0.1 -p 5433 -q

check_cmd "PgBouncer SHOW VERSION (pgbouncer admin db)" \
    psql -h 127.0.0.1 -p 5434 -U guinevere -d pgbouncer -c "SHOW VERSION;" -t -A

check_cmd "psql through PgBouncer: SELECT 1 (guineveredb)" \
    psql -h 127.0.0.1 -p 5434 -U guinevere -d guineveredb -c "SELECT 1;" -t -A

# ============================================================================
# SECTION 3 — Redis
# ============================================================================
echo ""
echo "--- SECTION 3: Redis -------------------------------------------------"

check_cmd "redis-cli -h 127.0.0.1 -p 6380 PING → PONG" \
    redis-cli -h 127.0.0.1 -p 6380 PING

# ============================================================================
# SECTION 4 — Caddy Ports
# ============================================================================
echo ""
echo "--- SECTION 4: Caddy Ports -------------------------------------------"

check_cmd "Caddy port 8443 listening" \
    bash -c 'ss -tlnp -H 2>/dev/null | grep -q ":8443 "'

check_cmd "Caddy port 3443 listening" \
    bash -c 'ss -tlnp -H 2>/dev/null | grep -q ":3443 "'

check_cmd "Caddy port 9443 listening" \
    bash -c 'ss -tlnp -H 2>/dev/null | grep -q ":9443 "'

# ============================================================================
# SECTION 5 — Security
# ============================================================================
echo ""
echo "--- SECTION 5: Security ----------------------------------------------"

check_cmd_output "UFW status: active" "Status: active" \
    ufw status

check_cmd_output "UFW: 22/tcp ALLOW" "22/tcp" \
    ufw status

check_cmd_output "fail2ban-client status sshd → Jail list: sshd" "Jail list" \
    fail2ban-client status sshd

check_cmd "CrowdSec LAPI status → running" \
    cscli lapi status

# ---- Port scan: only expected ports (+ system ports) ----
echo "  [....] Port scan: checking for unexpected listening ports..."
# Expected Guinevere application ports
EXPECTED_PORTS="22 5433 5434 6380 8443 3443 9443"
# Also allow common system/admin ports (currently implicit via port range logic)
# Collect all listening TCP ports (excluding loopback-only for some)
ALL_PORTS=$(ss -tlnp -n 2>/dev/null | awk 'NR>1{print $4}' | awk -F: '{print $NF}' | sort -n -u || true)
UNEXPECTED=""
for port in $ALL_PORTS; do
    case " $EXPECTED_PORTS " in
        *" $port "*) ;;  # expected
        *)
            # Skip high ephemeral ports (typically > 1024 and system-managed)
            # We only flag unexpected application ports
            if [ "$port" -le 1024 ] && [ "$port" != "22" ] && [ "$port" != "80" ] && [ "$port" != "443" ]; then
                UNEXPECTED="$UNEXPECTED $port"
            fi
            ;;
    esac
done

if [ -z "$UNEXPECTED" ]; then
    log_pass "Port scan: no unexpected privileged listening ports"
    ((PASS++))
else
    log_warn "Port scan: unexpected ports found: $UNEXPECTED (review if expected)"
    ((WARN++))
fi

# Port isolation: check that Aizanta ports (5432, 6379) are not consumed by Guinevere.
# NOTE: ss -tlnp shows ALL system ports including Aizanta Docker containers.
# Aizanta's own services WILL appear on 5432/6379 — that is expected.
# The actual Guinevere-specific verification: Section 2 confirms pg_isready :5433,
# Section 3 confirms redis-cli PING :6380. Those already prove correct port binding.
# Here we flag unexpected usage as WARN only (not FAIL) since Aizanta co-location
# naturally occupies those ports.
if echo "$ALL_PORTS" | grep -q "5432"; then
    log_warn "Port 5432 in use — may be Aizanta PostgreSQL (expected if Aizanta running). Guinevere confirmed on :5433 in Section 2."
    ((WARN++))
else
    log_pass "Port isolation: 5432 not bound (Aizanta PostgreSQL may be stopped)"
    ((PASS++))
fi

if echo "$ALL_PORTS" | grep -q "6379"; then
    log_warn "Port 6379 in use — may be Aizanta Redis (expected if Aizanta running). Guinevere confirmed on :6380 in Section 3."
    ((WARN++))
else
    log_pass "Port isolation: 6379 not bound (Aizanta Redis may be stopped)"
    ((PASS++))
fi

# ============================================================================
# SECTION 6 — Network
# ============================================================================
echo ""
echo "--- SECTION 6: Network -----------------------------------------------"

# Tailscale: process check + IP verification
check_cmd "tailscaled service (systemctl check done above — verifying process)" \
    pgrep -x tailscaled

check_warn "tailscale status → faiz-prod-01 connected (soft check)" \
    tailscale status 2>/dev/null

check_cmd_output "tailscale ip -4 → 100.94.104.22" "100.94.104.22" \
    tailscale ip -4 2>/dev/null

# Cloudflare Tunnel process
check_cmd "cloudflared process running" \
    bash -c 'ps aux 2>/dev/null | grep -v grep | grep -q cloudflared'

# ============================================================================
# SECTION 7 — SOPS / Encryption
# ============================================================================
echo ""
echo "--- SECTION 7: SOPS / Encryption -------------------------------------"

# sops version ≥ 3.8
SOPS_VER=$(sops --version 2>/dev/null | grep -oP '(\d+\.\d+\.\d+)' | head -1 || echo "0.0.0")
if command -v sops >/dev/null 2>&1; then
    log_pass "sops --version → $SOPS_VER"
    ((PASS++))
    # Check minimum version (semver comparison simplified: major.minor)
    if [ "$(echo "$SOPS_VER" | cut -d. -f1)" -ge 3 ] && [ "$(echo "$SOPS_VER" | cut -d. -f2)" -ge 8 ]; then
        log_pass "sops version ≥ 3.8 ($SOPS_VER)"
        ((PASS++))
    else
        log_warn "sops version < 3.8 (got $SOPS_VER) — upgrade recommended"
        ((WARN++))
    fi
else
    log_fail "sops binary not found"
    ((FAIL++))
    OVERALL_EXIT=1
fi

# SOPS decrypt check (requires SOPS_AGE_KEY_FILE to be set on VPS)
if [ -f /home/guinevere/secrets/age-key.txt ] 2>/dev/null; then
    check_cmd "sops --decrypt secrets/guinevere-secrets.yaml" \
        bash -c 'SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt secrets/guinevere-secrets.yaml > /dev/null'
elif [ -n "${SOPS_AGE_KEY_FILE:-}" ] && [ -f "$SOPS_AGE_KEY_FILE" ]; then
    check_cmd "sops --decrypt secrets/guinevere-secrets.yaml (using \$SOPS_AGE_KEY_FILE)" \
        bash -c 'sops --decrypt secrets/guinevere-secrets.yaml > /dev/null'
else
    log_warn "SOPS_AGE_KEY_FILE not accessible — skipping decrypt check"
    ((WARN++))
fi

# age public key
if [ -f /home/guinevere/secrets/age-key.txt ] 2>/dev/null; then
    AGE_PUBKEY=$(age-keygen -y /home/guinevere/secrets/age-key.txt 2>/dev/null || true)
    if [ -n "$AGE_PUBKEY" ]; then
        log_pass "age-keygen -y → public key: ${AGE_PUBKEY:0:20}..."
        ((PASS++))
    else
        log_fail "age-keygen -y failed to return public key"
        ((FAIL++))
        OVERALL_EXIT=1
    fi
else
    log_warn "age-key.txt not at /home/guinevere/secrets/ — skipping age-keygen check"
    ((WARN++))
fi

# ============================================================================
# SECTION 8 — Resources
# ============================================================================
echo ""
echo "--- SECTION 8: Resources ---------------------------------------------"

# Disk: Avail >= 40G
DISK_AVAIL=$(df -BG / 2>/dev/null | awk 'NR==2{print $4}' | tr -d 'G' || echo "0")
if [ "$DISK_AVAIL" -ge 40 ] 2>/dev/null; then
    log_pass "df -BG / → Avail ${DISK_AVAIL}G (>= 40G)"
    ((PASS++))
else
    log_fail "df -BG / → Avail ${DISK_AVAIL}G (< 40G)"
    ((FAIL++))
    OVERALL_EXIT=1
fi

# Memory: available >= 512M
MEM_AVAIL=$(free -m 2>/dev/null | awk '/^Mem:/{print $7}' || echo "0")
if [ "$MEM_AVAIL" -ge 512 ] 2>/dev/null; then
    log_pass "free -m → ${MEM_AVAIL}M available (>= 512M)"
    ((PASS++))
else
    log_fail "free -m → ${MEM_AVAIL}M available (< 512M)"
    ((FAIL++))
    OVERALL_EXIT=1
fi

# Load: load_1min < CPU cores
CPU_CORES=$(nproc 2>/dev/null || getconf _NPROCESSORS_ONLN 2>/dev/null || echo "1")
LOAD_1MIN=$(uptime 2>/dev/null | sed 's/.*average: //' | awk -F', ' '{print $1}' || echo "0")
LOAD_INT=${LOAD_1MIN%%.*}
if [ "$LOAD_INT" -lt "$CPU_CORES" ] 2>/dev/null; then
    log_pass "uptime → load ${LOAD_1MIN} < ${CPU_CORES} cores"
    ((PASS++))
else
    log_warn "uptime → load ${LOAD_1MIN} >= ${CPU_CORES} cores (high load)"
    ((WARN++))
fi

# ============================================================================
# SECTION 9 — Aizanta (Docker)
# ============================================================================
echo ""
echo "--- SECTION 9: Aizanta (Docker) --------------------------------------"

# Check Docker is running
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    # Container count
    AIZANTA_COUNT=$(docker ps --filter name=aizanta --format '{{.Names}}' 2>/dev/null | wc -l || echo "0")
    if [ "$AIZANTA_COUNT" -ge 5 ] 2>/dev/null; then
        log_pass "docker ps --filter name=aizanta → ${AIZANTA_COUNT} containers (>= 5)"
        ((PASS++))
    else
        log_fail "docker ps --filter name=aizanta → ${AIZANTA_COUNT} containers (< 5)"
        ((FAIL++))
        OVERALL_EXIT=1
    fi

    # Health check (all 5 healthy)
    AIZANTA_HEALTHY=$(docker ps --filter name=aizanta --filter health=healthy --format '{{.Names}}' 2>/dev/null | wc -l || echo "0")
    if [ "$AIZANTA_HEALTHY" -ge 5 ] 2>/dev/null; then
        log_pass "docker ps --filter health=healthy → ${AIZANTA_HEALTHY} healthy"
        ((PASS++))
    else
        log_warn "docker ps --filter health=healthy → ${AIZANTA_HEALTHY}/5 healthy (some may not have healthcheck)"
        ((WARN++))
    fi

    if $VERBOSE; then
        echo "         Aizanta containers:"
        docker ps --filter name=aizanta --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' 2>/dev/null
    fi
else
    log_warn "Docker not available — skipping Aizanta container checks"
    ((WARN++))
fi

# Aizanta port conflict: already checked in Section 5 port scan (5432, 6379)

# ============================================================================
# SECTION 10 — Backup
# ============================================================================
echo ""
echo "--- SECTION 10: Backup -----------------------------------------------"

check_cmd "restic --version" \
    restic --version

# Check systemd timer
TIMER_COUNT=$(systemctl list-timers 2>/dev/null | grep -c "guinevere-backup" || true)
if [ "$TIMER_COUNT" -gt 0 ]; then
    log_pass "systemctl list-timers | grep guinevere-backup → ${TIMER_COUNT} timer(s) listed"
    ((PASS++))
    if $VERBOSE; then
        systemctl list-timers 2>/dev/null | grep "guinevere-backup" || true
    fi
else
    log_fail "systemctl list-timers | grep guinevere-backup → no timers found"
    ((FAIL++))
    OVERALL_EXIT=1
fi

# Check backup script exists
if [ -f /opt/guinevere/scripts/guinevere-backup.sh ] 2>/dev/null; then
    log_pass "/opt/guinevere/scripts/guinevere-backup.sh EXISTS"
    ((PASS++))
else
    log_fail "/opt/guinevere/scripts/guinevere-backup.sh NOT FOUND"
    ((FAIL++))
    OVERALL_EXIT=1
fi

# ============================================================================
# SUMMARY
# ============================================================================
echo ""
echo "================================================================"
echo "  P0-028 PRE-FLIGHT SUMMARY"
echo "================================================================"
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  WARN: $WARN"
echo "================================================================"

if [ "$OVERALL_EXIT" -eq 0 ]; then
    echo "  RESULT: ALL CHECKS PASSED — System is ready for P1."
else
    echo "  RESULT: $FAIL check(s) FAILED — Review output before proceeding to P1."
fi
echo "  Completed: $(date -u '+%Y-%m-%dT%H:%M:%SZ')"
echo "================================================================"

exit "$OVERALL_EXIT"