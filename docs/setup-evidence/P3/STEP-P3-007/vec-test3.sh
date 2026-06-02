#!/bin/bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT (array_agg(random()::float4))::vector::text FROM generate_series(1, 5);" 2>&1
echo "---"
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT pg_typeof((array_agg(random()::float4))::vector) FROM generate_series(1, 5);" 2>&1