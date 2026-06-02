#!/bin/bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -t -c "SELECT array_to_vector(array_agg(random()::real))::text FROM generate_series(1, 5);"