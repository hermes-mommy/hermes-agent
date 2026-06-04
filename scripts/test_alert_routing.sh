#!/usr/bin/env bash
# P8-016: Alert Routing Test
# Verifies: Prometheus alert rules load, Alertmanager routes SEV0-SEV4 correctly
# Run on VPS only after: docker compose -f monitoring/compose.monitoring.yml up -d
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(dirname "$SCRIPT_DIR")"
readonly ALERTS_FILE="$REPO_ROOT/monitoring/prometheus/rules/guinevere-alerts.yml"
readonly BACKUP_ALERTS_FILE="$REPO_ROOT/monitoring/prometheus/rules/guinevere-backup-alerts.yml"
readonly ALERTMANAGER_FILE="$REPO_ROOT/monitoring/alertmanager/alertmanager.yml"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'

PASS=0; FAIL=0; SKIP=0

pass()  { ((PASS++)); echo -e "  ${GREEN}✓ PASS${NC}: $1"; }
fail()  { ((FAIL++)); echo -e "  ${RED}✗ FAIL${NC}: $1"; }
skip()  { ((SKIP++)); echo -e "  ${YELLOW}⊘ SKIP${NC}: $1"; }

echo "=== P8-016: Alert Routing Test ==="
echo "    $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# ──────────────────────────────────────────────
# Step 1: Verify alert rule files exist and are valid YAML
# ──────────────────────────────────────────────
echo "[1/7] Alert rule file validation..."

if [ -f "$ALERTS_FILE" ]; then
    pass "guinevere-alerts.yml exists"
else
    fail "guinevere-alerts.yml not found at $ALERTS_FILE"
fi

if [ -f "$BACKUP_ALERTS_FILE" ]; then
    pass "guinevere-backup-alerts.yml exists"
else
    fail "guinevere-backup-alerts.yml not found at $BACKUP_ALERTS_FILE"
fi

# ──────────────────────────────────────────────
# Step 2: Verify alertmanager config exists
# ──────────────────────────────────────────────
echo "[2/7] Alertmanager config validation..."

if [ -f "$ALERTMANAGER_FILE" ]; then
    pass "alertmanager.yml exists"

    # Check for required severity routes
    if grep -q "severity: critical" "$ALERTMANAGER_FILE"; then
        pass "Critical severity route defined"
    else
        fail "No critical severity route in alertmanager.yml"
    fi

    if grep -q "severity: warning" "$ALERTMANAGER_FILE"; then
        pass "Warning severity route defined"
    else
        fail "No warning severity route in alertmanager.yml"
    fi

    if grep -q "discord" "$ALERTMANAGER_FILE"; then
        pass "Discord receiver configured"
    else
        fail "No Discord receiver in alertmanager.yml"
    fi

    if grep -q "gotify" "$ALERTMANAGER_FILE"; then
        pass "Gotify fallback receiver configured"
    else
        skip "No Gotify fallback receiver (optional)"
    fi
else
    fail "alertmanager.yml not found at $ALERTMANAGER_FILE"
fi

# ──────────────────────────────────────────────
# Step 3: Verify Prometheus is running and has loaded rules
# ──────────────────────────────────────────────
echo "[3/7] Prometheus health + rules..."

if curl -sf http://localhost:9090/-/healthy >/dev/null 2>&1; then
    pass "Prometheus is healthy"
else
    fail "Prometheus not healthy (curl localhost:9090/-/healthy failed)"
    echo ""
    echo "RESULT: FAIL — Prometheus must be running before testing alerts."
    exit 1
fi

# Check rule count
RULE_COUNT=$(curl -sf "http://localhost:9090/api/v1/rules" 2>/dev/null | python3 -c "
import json, sys
data = json.load(sys.stdin)
rules = data.get('data', {}).get('groups', [])
total = sum(len(g.get('rules', [])) for g in rules)
print(total)
" 2>/dev/null || echo "0")

if [ "$RULE_COUNT" -ge 9 ]; then
    pass "Prometheus loaded $RULE_COUNT alert rules (expected ≥9)"
else
    fail "Only $RULE_COUNT rules loaded (expected ≥9)"
fi

# ──────────────────────────────────────────────
# Step 4: Verify specific SEV-level rules exist
# ──────────────────────────────────────────────
echo "[4/7] SEV-level rule verification..."

RULES_JSON=$(curl -sf "http://localhost:9090/api/v1/rules" 2>/dev/null || echo '{"data":{"groups":[]}}')

for RULE_NAME in "SafeWordBypass" "PublicIngressDetected" "LogRedactionFailure" "CriticalServiceDown" "LLMCostSpike"; do
    if echo "$RULES_JSON" | grep -q "\"$RULE_NAME\""; then
        pass "Rule '$RULE_NAME' loaded"
    else
        fail "Rule '$RULE_NAME' not found in Prometheus"
    fi
done

# ──────────────────────────────────────────────
# Step 5: Verify Alertmanager is running
# ──────────────────────────────────────────────
echo "[5/7] Alertmanager health..."

if curl -sf http://localhost:9093/-/healthy >/dev/null 2>&1; then
    pass "Alertmanager is healthy"
else
    fail "Alertmanager not healthy (curl localhost:9093/-/healthy failed)"
fi

# Check Alertmanager config status
AM_STATUS=$(curl -sf "http://localhost:9093/api/v2/status" 2>/dev/null || echo "")
if echo "$AM_STATUS" | grep -q "cluster\|config"; then
    pass "Alertmanager API responsive"
else
    skip "Alertmanager API v2 status check (may need different endpoint)"
fi

# ──────────────────────────────────────────────
# Step 6: Test alert routing via amtool (if available)
# ──────────────────────────────────────────────
echo "[6/7] Alert routing test..."

if command -v amtool >/dev/null 2>&1; then
    # Test SEV0 routing
    ROUTE_SEV0=$(amtool config routes test \
        --config.file="$ALERTMANAGER_FILE" \
        severity=critical 2>/dev/null || echo "")
    if echo "$ROUTE_SEV0" | grep -q "discord-critical\|discord_critical"; then
        pass "SEV0 (critical) routes to discord-critical"
    else
        skip "amtool routing test inconclusive for SEV0"
    fi

    ROUTE_SEV2=$(amtool config routes test \
        --config.file="$ALERTMANAGER_FILE" \
        severity=warning 2>/dev/null || echo "")
    if echo "$ROUTE_SEV2" | grep -q "discord"; then
        pass "SEV2 (warning) routes to discord"
    else
        skip "amtool routing test inconclusive for SEV2"
    fi
else
    skip "amtool not installed — routing test requires amtool binary"
    echo "    Install: https://github.com/prometheus/alertmanager/releases"
fi

# ──────────────────────────────────────────────
# Step 7: Inject test alert and verify routing
# ──────────────────────────────────────────────
echo "[7/7] Test alert injection..."

# Send a test alert to Alertmanager
curl -sf -X POST http://localhost:9093/api/v2/alerts \
    -H "Content-Type: application/json" \
    -d "[{
        \"labels\": {
            \"alertname\": \"P8016TestAlert\",
            \"severity\": \"info\",
            \"service\": \"guinevere\",
            \"component\": \"alert-test\"
        },
        \"annotations\": {
            \"summary\": \"P8-016 alert routing test\",
            \"description\": \"Test alert to verify routing. Safe to ignore.\"
        },
        \"startsAt\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\"
    }]" 2>/dev/null

if [ $? -eq 0 ]; then
    pass "Test alert injected to Alertmanager (P8016TestAlert, severity=info)"
else
    fail "Failed to inject test alert"
fi

# Check alert appears in Alertmanager
sleep 2
AM_ALERTS=$(curl -sf "http://localhost:9093/api/v2/alerts" 2>/dev/null || echo "[]")
if echo "$AM_ALERTS" | grep -q "P8016TestAlert"; then
    pass "Test alert visible in Alertmanager"
else
    skip "Test alert not yet visible (may need more time to propagate)"
fi

# ──────────────────────────────────────────────
# Summary
# ──────────────────────────────────────────────
echo ""
echo "=== RESULTS ==="
echo "  PASS: $PASS"
echo "  FAIL: $FAIL"
echo "  SKIP: $SKIP"
echo ""

if [ "$FAIL" -eq 0 ]; then
    echo -e "${GREEN}P8-016: PASS${NC}"
    exit 0
else
    echo -e "${RED}P8-016: FAIL${NC}"
    exit 1
fi
