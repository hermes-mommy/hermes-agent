#!/bin/bash
# P1-019 Service Health Check for Guinevere
# Run: bash scripts/health-check-p1.sh

echo "=== P1 SERVICE HEALTH CHECK ==="
FAILS=0

echo "--- Core ---"
if curl -sf http://localhost:8000/health > /dev/null 2>&1; then
    echo "[PASS] guinevere-core health endpoint responds"
else
    echo "[FAIL] guinevere-core health endpoint"
    FAILS=$((FAILS + 1))
fi

echo "--- 9Router ---"
if curl -sf http://localhost:20128/api/health > /dev/null 2>&1; then
    echo "[PASS] guinevere-9router health endpoint responds"
else
    echo "[FAIL] guinevere-9router health endpoint"
    FAILS=$((FAILS + 1))
fi

echo "--- Graceful Degradation ---"
echo "[INFO] Ollama skipped per Faiz directive 2026-06-01; final fallback is graceful degradation"

echo "--- PostgreSQL ---"
if echo "SELECT 1;" | docker exec -i guinevere-postgres psql -U guinevere -d guinevere > /dev/null 2>&1; then
    echo "[PASS] PostgreSQL SELECT 1 succeeded"
else
    echo "[FAIL] PostgreSQL connectivity"
    FAILS=$((FAILS + 1))
fi

echo "--- Redis ---"
export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt
REDIS_PASS=$(sops -d /home/guinevere/secrets/redis-acl-passwords.yaml 2>/dev/null | grep guinevere_core | awk '{print $2}')
if [ -n "$REDIS_PASS" ]; then
    if docker exec -i guinevere-redis redis-cli --user guinevere_core --pass "$REDIS_PASS" PING 2>/dev/null | grep -q PONG; then
        echo "[PASS] Redis PONG received (guinevere_core ACL user)"
    else
        echo "[FAIL] Redis PING"
        FAILS=$((FAILS + 1))
    fi
else
    echo "[FAIL] Could not decrypt Redis ACL password"
    FAILS=$((FAILS + 1))
fi

echo ""
echo "=== P1 HEALTH CHECK COMPLETE ==="
echo "Failures: $FAILS"
if [ "$FAILS" -eq 0 ]; then
    echo "Status: ALL PASS"
    exit 0
else
    echo "Status: $FAILS FAILURE(S)"
    exit 1
fi