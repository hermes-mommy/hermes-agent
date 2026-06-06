#!/bin/bash
# Phase 6 Step 9 - Run 100-prompt VPS integration test
set -e

cd /home/guinevere/code/guinevere

# Source env vars
export GUINEVERE_9ROUTER_API_KEY=$(grep GUINEVERE_9ROUTER_API_KEY .env.core | cut -d= -f2)
export REDIS_PASSWORD="[REDACTED_REDIS_PASSWORD]"
# LLMRouter reads NINEROUTER_API_KEY env var
export NINEROUTER_API_KEY="$GUINEVERE_9ROUTER_API_KEY"

echo "=== ENV CHECK ==="
echo "NINEROUTER_API_KEY set: $([ -n \"$NINEROUTER_API_KEY\" ] && echo YES || echo NO)"
echo "REDIS_PASSWORD set: $([ -n \"$REDIS_PASSWORD\" ] && echo YES || echo NO)"
echo ""

echo "=== REDIS DB5 BEFORE ==="
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:*'
echo "---"
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 MGET cost:current_month cost:current_day cost:monthly:2026-06 budget:monthly_cap
echo "---"
for k in $(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:by_model:*' 2>/dev/null); do
  v=$(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 GET "$k" 2>/dev/null)
  echo "  $k = $v"
done
echo ""

echo "=== METRICS BEFORE ==="
curl -s http://localhost:9191/metrics | grep '^hermes_'
echo ""

echo "=== RUNNING 100 PROMPT TEST ==="
/home/guinevere/code/guinevere/.venv/bin/python3 /tmp/phase6_100_prompt_test.py \
  2>&1 | tee /tmp/phase6_test_output.txt

echo ""
echo "=== REDIS DB5 AFTER ==="
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:*'
echo "---"
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 MGET cost:current_month cost:current_day cost:monthly:2026-06 budget:monthly_cap
echo "---"
for k in $(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:by_model:*' 2>/dev/null); do
  v=$(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 GET "$k" 2>/dev/null)
  echo "  $k = $v"
done
echo ""

echo "=== METRICS AFTER ==="
curl -s http://localhost:9191/metrics | grep '^hermes_'
echo ""

echo "=== DONE ==="
