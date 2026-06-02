#!/bin/bash
echo "=== PRESTEP HEALTH CHECKS ==="
echo "Date: $(date -u -Iseconds)"
echo ""
echo "=== System Resources ==="
free -h
echo ""
echo "--- uptime ---"
uptime
echo ""
echo "--- disk free ---"
df -h / | tail -1
echo ""
echo "=== Aizanta PG 5432 ==="
pg_isready -h 127.0.0.1 -p 5432
echo ""
echo "=== Guinevere PG 5433 ==="
pg_isready -h 127.0.0.1 -p 5433
echo ""
echo "=== PgBouncer 5434 ==="
pg_isready -h 127.0.0.1 -p 5434
echo ""
echo "=== Redis 6380 ==="
redis-cli -p 6380 PING 2>&1
echo ""
echo "=== 9Router 20128 ==="
curl -s -o /dev/null -w "HTTP %{http_code}" http://localhost:20128/v1/models
echo ""
echo "=== Docker containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}"
echo ""
echo "=== guinevere-core ==="
systemctl is-active guinevere-core
echo ""
echo "=== guinevere-9router ==="
systemctl is-active guinevere-9router
echo ""
echo "=== Aizanta containers ==="
docker ps --format "table {{.Names}}\t{{.Status}}" | head -10
echo ""
echo "=== PRESTEP COMPLETE ==="