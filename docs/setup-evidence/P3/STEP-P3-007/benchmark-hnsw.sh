#!/bin/bash
set -euo pipefail
OUTFILE="/tmp/hnsw-benchmark-output.txt"
exec > "$OUTFILE" 2>&1

echo "=== HNSW SMOKE BENCHMARK ==="
echo "Date: $(date -u -Iseconds)"
echo ""

echo "--- Pre-benchmark row counts ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -A -c "SELECT 'episodes: ' || count(*)::text FROM memory.episodes;"
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -A -c "SELECT 'semantic_facts: ' || count(*)::text FROM memory.semantic_facts;"
echo ""

echo "--- Running HNSW benchmark inside transaction ---"
echo ""

docker exec guinevere-postgres psql -U guinevere -d guinevere << 'BENCHSQL' 2>&1
\timing on

BEGIN;

-- Insert episodes (20 rows with random 1536-dim vectors)
INSERT INTO memory.episodes (started_at, episode_type, title, summary, raw_content, embedding, importance)
SELECT
  now() - (i || ' hours')::interval,
  'benchmark_smoke',
  'Benchmark episode ' || i,
  'Auto-generated for HNSW smoke benchmark.',
  'Raw content for benchmark episode ' || i || '. Text for pgvector HNSW testing.',
  (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)),
  5
FROM generate_series(1, 20) AS i;

INSERT INTO memory.semantic_facts (subject, predicate, object_val, fact_type, embedding, confidence)
SELECT
  'entity_' || (i % 4 + 1),
  'has_attribute',
  'value_' || i,
  'benchmark_smoke',
  (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)),
  0.8
FROM generate_series(1, 20) AS i;

ANALYZE memory.episodes;
ANALYZE memory.semantic_facts;

SELECT '[DATA] episodes: ' || count(*)::text FROM memory.episodes;
SELECT '[DATA] semantic_facts: ' || count(*)::text FROM memory.semantic_facts;

\echo ''
\echo '== ef_search=40 =='
SET hnsw.ef_search = 40;
SELECT '[CFG] ef_search=40, ' || current_setting('hnsw.ef_search');
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
\echo '== ef_search=100 =='
SET hnsw.ef_search = 100;
SELECT '[CFG] ef_search=100, ' || current_setting('hnsw.ef_search');
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
\echo '== ef_search=200 =='
SET hnsw.ef_search = 200;
SELECT '[CFG] ef_search=200, ' || current_setting('hnsw.ef_search');
EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS) SELECT id FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[Q]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
ROLLBACK;
\echo '=== ROLLED BACK ==='
SELECT 'post_episodes: ' || count(*)::text FROM memory.episodes;
SELECT 'post_facts: ' || count(*)::text FROM memory.semantic_facts;
\echo '=== DONE ==='
BENCHSQL

echo "--- Benchmark output written to $OUTFILE ---"