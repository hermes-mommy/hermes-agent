#!/bin/bash
echo "=== GUC CHECK 2 ==="
echo "--- Try SET hnsw.ef_search ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SET hnsw.ef_search = 100; SHOW hnsw.ef_search;" 2>&1
echo ""
echo "--- Try SET LOCAL ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SET LOCAL hnsw.ef_search = 100; SHOW hnsw.ef_search;" 2>&1
echo ""
echo "--- Check vector functions ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT proname FROM pg_proc WHERE proname LIKE '%hnsw%' OR proname LIKE '%ivfflat%';" 2>&1
echo ""
echo "--- Check pgvector version function ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT * FROM pgvector_config();" 2>&1
echo ""
echo "--- Check if ivfflat exists ---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT * FROM pg_indexes WHERE indexdef LIKE '%ivfflat%';" 2>&1
echo "=== GUC CHECK 2 COMPLETE ==="