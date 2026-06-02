#!/bin/bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT (array_agg(random()::real)::text || '') IS NOT NULL FROM generate_series(1, 5);" 2>&1
echo "---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT pg_typeof(''::vector);" 2>&1
echo "---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -c "SELECT ARRAY[1,2,3]::float4[]::vector::text;" 2>&1