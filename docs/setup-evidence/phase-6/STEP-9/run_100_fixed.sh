#!/bin/bash
set -e

cd /home/guinevere/code/guinevere

# Load env vars
GUINEVERE_KEY=$(grep GUINEVERE_9ROUTER_API_KEY .env.core | cut -d= -f2)
export NINEROUTER_API_KEY="$GUINEVERE_KEY"
export REDIS_PASSWORD="[REDACTED_REDIS_PASSWORD]"

echo "=== ENV CHECK ==="
if [ -n "$NINEROUTER_API_KEY" ]; then echo "NINEROUTER_API_KEY: YES"; else echo "NINEROUTER_API_KEY: NO"; fi
if [ -n "$REDIS_PASSWORD" ]; then echo "REDIS_PASSWORD: YES"; else echo "REDIS_PASSWORD: NO"; fi

echo ""
echo "=== REDIS DB5 BEFORE ==="
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:*' 2>&1 | grep -v Warning
echo "---"
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 MGET cost:current_month cost:current_day cost:monthly:2026-06 budget:monthly_cap 2>&1 | grep -v Warning
echo "---"
echo "by_model values:"
for k in $(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:by_model:*' 2>/dev/null | grep -v Warning); do
  v=$(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 GET "$k" 2>/dev/null | grep -v Warning)
  echo "  $k = $v"
done

echo ""
echo "=== METRICS BEFORE ==="
curl -s http://localhost:9191/metrics | grep '^hermes_' || echo "(no hermes metrics data yet)"

echo ""
echo "=== RUNNING 100 PROMPT TEST ==="
/home/guinevere/code/guinevere/.venv/bin/python3 /tmp/phase6_100_prompt_test.py 2>&1 | tee /tmp/phase6_test_output.txt
TEST_EXIT=${PIPESTATUS[0]}
echo "Test exit code: $TEST_EXIT"

echo ""
echo "=== REDIS DB5 AFTER ==="
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:*' 2>&1 | grep -v Warning
echo "---"
docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 MGET cost:current_month cost:current_day cost:monthly:2026-06 budget:monthly_cap 2>&1 | grep -v Warning
echo "---"
echo "by_model values:"
for k in $(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 KEYS 'cost:by_model:*' 2>/dev/null | grep -v Warning); do
  v=$(docker exec guinevere-redis redis-cli -a "$REDIS_PASSWORD" -n 5 GET "$k" 2>/dev/null | grep -v Warning)
  echo "  $k = $v"
done

echo ""
echo "=== METRICS AFTER ==="
curl -s http://localhost:9191/metrics | grep '^hermes_' || echo "(no hermes metrics data yet)"

echo ""
echo "=== DONE ==="
