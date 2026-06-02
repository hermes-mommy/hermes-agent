#!/bin/bash
set -e

PW=$(SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt sops --decrypt /home/guinevere/secrets/db-passwords.yaml | grep -oP 'guinevere_core:\s*\K.*')
if [ -z "$PW" ]; then
  echo "ERROR: guinevere_core password not found" >&2
  exit 1
fi
export PGPASSWORD="$PW"
PG="psql -h 127.0.0.1 -p 5433 -U guinevere_core -d guinevere"

echo "=== 1. Column verification ==="
$PG -c "
SELECT column_name, data_type, udt_name, is_nullable, column_default
FROM information_schema.columns
WHERE table_schema = 'memory' AND table_name = 'episodes'
  AND column_name IN ('search_vector', 'do_not_recall');
"

echo ""
echo "=== 2. GIN index verification ==="
$PG -c "
SELECT indexname, indexdef
FROM pg_indexes
WHERE tablename = 'episodes' AND indexname = 'ix_episodes_search_vector_gin';
"

echo ""
echo "=== 3. FTS query test ==="
$PG -c "
SELECT to_tsvector('english', 'Guinevere remembers everything') @@ to_tsquery('english', 'remember') AS fts_works;
"

echo ""
echo "=== 4. Generated column test (rollback) ==="
$PG -c "
BEGIN;
INSERT INTO memory.episodes (started_at, episode_type, title, summary, raw_content)
VALUES (NOW(), 'test', 'Hello World', 'A test summary', 'Guinevere remembers everything about Faiz');
SELECT id, title, search_vector::text, do_not_recall FROM memory.episodes WHERE episode_type = 'test';
ROLLBACK;
"

echo ""
echo "=== 5. do_not_recall default verification ==="
$PG -c "
BEGIN;
INSERT INTO memory.episodes (started_at, episode_type)
VALUES (NOW(), 'test_dnr');
SELECT do_not_recall FROM memory.episodes WHERE episode_type = 'test_dnr';
ROLLBACK;
"

echo ""
echo "=== 6. Alembic revision check ==="
cd /home/guinevere/code/guinevere
source .venv/bin/activate
export GUINEVERE_DB_PASSWORD="$PW"
alembic current 2>&1

echo ""
echo "=== VERIFICATION COMPLETE ==="