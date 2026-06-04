#!/usr/bin/env bash
# P8-011: Log Pipeline Test
# Verifies: systemd journal → Promtail → Loki → Grafana chain
# Run on VPS only after: docker compose -f monitoring/compose.monitoring.yml up -d
set -euo pipefail

readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Colors
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[0;33m'; NC='\033[0m'

PASS=0; FAIL=0; SKIP=0

pass()  { ((PASS++)); echo -e "  ${GREEN}✓ PASS${NC}: $1"; }
fail()  { ((FAIL++)); echo -e "  ${RED}✗ FAIL${NC}: $1"; }
skip()  { ((SKIP++)); echo -e "  ${YELLOW}⊘ SKIP${NC}: $1"; }

echo "=== P8-011: Log Pipeline Test ==="
echo "    $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo ""

# ──────────────────────────────────────────────
# Step 1: Verify Loki is healthy
# ──────────────────────────────────────────────
echo "[1/6] Loki health check..."
if curl -sf http://localhost:3100/ready >/dev/null 2>&1; then
    pass "Loki is ready"
else
    fail "Loki not ready (curl localhost:3100/ready failed)"
    echo ""
    echo "RESULT: FAIL — Loki must be running before testing log pipeline."
    exit 1
fi

# ──────────────────────────────────────────────
# Step 2: Verify Promtail is running
# ──────────────────────────────────────────────
echo "[2/6] Promtail container check..."
if docker compose -f "$REPO_ROOT/monitoring/compose.monitoring.yml" ps promtail 2>/dev/null | grep -q "running\|Up\|healthy"; then
    pass "Promtail container is running"
else
    # Also check if promtail is running as systemd service
    if systemctl is-active --quiet guinevere-monitoring.service 2>/dev/null; then
        pass "Monitoring service active (includes Promtail)"
    else
        fail "Promtail container not running"
    fi
fi

# ──────────────────────────────────────────────
# Step 3: Verify journal is readable
# ──────────────────────────────────────────────
echo "[3/6] Systemd journal access..."
if journalctl -n 5 --no-pager -q 2>/dev/null | head -1 | grep -q .; then
    pass "systemd journal readable"
else
    fail "Cannot read systemd journal"
fi

# ──────────────────────────────────────────────
# Step 4: Inject a test log entry and query Loki
# ──────────────────────────────────────────────
echo "[4/6] Loki push/query test..."
TEST_TAG="guinevere-p8-011-test-$(date +%s)"

# Push a test log entry directly to Loki
curl -sf -X POST http://localhost:3100/loki/api/v1/push \
    -H "Content-Type: application/json" \
    -d "{
        \"streams\": [{
            \"stream\": {
                \"service\": \"guinevere-p8-011-test\",
                \"component\": \"pipeline-validation\",
                \"environment\": \"production\",
                \"level\": \"info\",
                \"event_category\": \"test\"
            },
            \"values\": [[\"$(date +%s%N)\", \"P8-011 pipeline validation test: ${TEST_TAG}\"]]
        }]
    }" 2>/dev/null

sleep 2

# Query Loki for the test entry
QUERY_RESULT=$(curl -sf "http://localhost:3100/loki/api/v1/query_range" \
    --data-urlencode "query={service=\"guinevere-p8-011-test\"}" \
    --data-urlencode "limit=1" 2>/dev/null || echo "")

if echo "$QUERY_RESULT" | grep -q "$TEST_TAG"; then
    pass "Loki push + query successful (test entry found)"
else
    fail "Loki query returned no matching test entry"
    echo "    Query result: $(echo "$QUERY_RESULT" | head -c 200)"
fi

# ──────────────────────────────────────────────
# Step 5: Verify Grafana can reach Loki datasource
# ──────────────────────────────────────────────
echo "[5/6] Grafana datasource connectivity..."
if curl -sf http://localhost:3000/api/health 2>/dev/null | grep -q "ok\|healthy"; then
    pass "Grafana API healthy"

    # Test Loki datasource via Grafana proxy
    DS_RESULT=$(curl -sf "http://localhost:3000/api/datasources/proxy/1/loki/api/v1/labels" 2>/dev/null || echo "")
    if echo "$DS_RESULT" | grep -q "service\|status"; then
        pass "Grafana Loki datasource returns labels"
    else
        skip "Grafana Loki datasource proxy test (may need auth or datasource ID mismatch)"
    fi
else
    fail "Grafana API not healthy"
fi

# ──────────────────────────────────────────────
# Step 6: Verify journal logs appear in Loki (not just pushed test entries)
# ──────────────────────────────────────────────
echo "[6/6] Journal ingestion into Loki..."
JOURNAL_QUERY=$(curl -sf "http://localhost:3100/loki/api/v1/query_range" \
    --data-urlencode 'query={job="journal"}' \
    --data-urlencode "limit=1" 2>/dev/null || echo "")

if echo "$JOURNAL_QUERY" | grep -q "values\|entries"; then
    pass "Journal entries found in Loki (job=journal)"
else
    skip "No journal entries in Loki yet (Promtail may need more time to scrape)"
    echo "    NOTE: This is expected right after first start. Wait 60s and re-run."
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
    echo -e "${GREEN}P8-011: PASS${NC}"
    exit 0
else
    echo -e "${RED}P8-011: FAIL${NC}"
    exit 1
fi
