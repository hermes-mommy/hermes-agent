\timing on

BEGIN;

-- Insert 20 episodes
INSERT INTO memory.episodes (started_at, episode_type, title, summary, raw_content, embedding, importance)
SELECT
  now() - (i || ' hours')::interval,
  'benchmark_smoke',
  'Benchmark episode ' || i,
  'Auto-generated for HNSW smoke test.',
  'Raw content for benchmark episode ' || i || '. Testing pgvector HNSW ef_search.',
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
\echo '=== ef_search = 40 ==='
SET hnsw.ef_search = 40;
SELECT current_setting('hnsw.ef_search') AS ef_search;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.episodes
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.semantic_facts
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
\echo '=== ef_search = 100 ==='
SET hnsw.ef_search = 100;
SELECT current_setting('hnsw.ef_search') AS ef_search;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.episodes
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.semantic_facts
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
\echo '=== ef_search = 200 ==='
SET hnsw.ef_search = 200;
SELECT current_setting('hnsw.ef_search') AS ef_search;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.episodes
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.episodes ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

EXPLAIN (ANALYZE, BUFFERS)
SELECT id FROM memory.semantic_facts
ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536))
LIMIT 10;

SELECT '[q1]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q2]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q3]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q4]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;
SELECT '[q5]' FROM memory.semantic_facts ORDER BY embedding <=> (SELECT (array_agg(random()::float4))::vector FROM generate_series(1, 1536)) LIMIT 10;

\echo ''
ROLLBACK;

SELECT 'post_episodes: ' || count(*)::text FROM memory.episodes;
SELECT 'post_facts: ' || count(*)::text FROM memory.semantic_facts;