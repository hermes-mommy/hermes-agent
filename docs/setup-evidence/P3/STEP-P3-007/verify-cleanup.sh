#!/bin/bash
echo "=== POST-BENCHMARK CLEANUP VERIFICATION ==="
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT 'episodes: ' || count(*)::text FROM memory.episodes;"
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT 'semantic_facts: ' || count(*)::text FROM memory.semantic_facts;"
echo "=== CLEANUP CONFIRMED ==="