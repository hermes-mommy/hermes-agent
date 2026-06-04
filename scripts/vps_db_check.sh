#!/bin/bash
set -e
export SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt

echo "=== DB TABLES ==="
eval $(sops -d /home/guinevere/secrets/db-passwords.yaml 2>/dev/null | grep guinevere_core_password | sed 's/: /=/')
PGPASSWORD=$guinevere_core_password psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core -t -c "SELECT schemaname || '.' || tablename FROM pg_tables WHERE schemaname NOT IN ('pg_catalog','information_schema') ORDER BY 1;" 2>/dev/null

echo "=== DB EXTENSIONS ==="
PGPASSWORD=$guinevere_core_password psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere_core -t -c "SELECT extname, extversion FROM pg_extension ORDER BY extname;" 2>/dev/null

echo "=== REDIS KEYSPACE ==="
RPASS=$(sops -d /home/guinevere/secrets/redis-password.yaml 2>/dev/null | grep redis_master_password | awk -F': ' '{print $2}')
for db in 0 1 2 3 4 5; do
  COUNT=$(redis-cli -p 6380 -a "$RPASS" --no-auth-warning -n "$db" DBSIZE 2>/dev/null)
  echo "DB$db: $COUNT"
done

echo "=== DB5 COST KEYS ==="
redis-cli -p 6380 -a "$RPASS" --no-auth-warning -n 5 KEYS 'cost:*' 2>/dev/null

echo "=== DB5 BUDGET KEYS ==="
redis-cli -p 6380 -a "$RPASS" --no-auth-warning -n 5 KEYS 'budget:*' 2>/dev/null

echo "=== OBS CURA CHECK ==="
ls -la /usr/local/bin/obscura 2>/dev/null || echo "obscura binary NOT FOUND"
which obscura 2>/dev/null || echo "obscura not in PATH"
