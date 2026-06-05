#!/bin/bash
set -euo pipefail

echo "=== Pre-Cutover Backup ==="

# Source env
source /home/guinevere/code/guinevere/.env.discord

# Extract PG password from DATABASE_URL
PG_PASS=$(echo "$DATABASE_URL" | grep -oP '(?<=://[^:]*:)[^@]+')

echo "=== pg_dump ==="
export PGPASSWORD="$PG_PASS"
pg_dump -U guinevere_core -h localhost -p 5433 guinevere -Fc -f /tmp/guinevere-pre-cutover.dump
echo "pg_dump exit: $?"
ls -lh /tmp/guinevere-pre-cutover.dump

echo ""
echo "=== Redis BGSAVE ==="
# Try port 6380 with password
redis-cli -p 6380 -a "$REDIS_PASSWORD" BGSAVE 2>/dev/null || echo "Redis 6380 with REDIS_PASSWORD failed"
# Try port 6379 with password
redis-cli -p 6379 -a "$REDIS_PASSWORD" BGSAVE 2>/dev/null || echo "Redis 6379 with REDIS_PASSWORD failed"
# Try without auth on both
redis-cli -p 6380 BGSAVE 2>/dev/null || echo "Redis 6380 no auth failed"
redis-cli -p 6379 BGSAVE 2>/dev/null || echo "Redis 6379 no auth failed"

echo ""
echo "=== Hermes backup/checkpoint ==="
/home/guinevere/code/guinevere/.venv/bin/hermes backup --checkpoint 2>&1 || echo "Hermes backup not available (non-blocking)"

echo ""
echo "=== Backup Complete ==="
