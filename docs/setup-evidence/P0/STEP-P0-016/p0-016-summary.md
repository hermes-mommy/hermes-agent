# STEP-P0-016 — TimescaleDB Extension Installation Summary

## What Was Done

Installed TimescaleDB 2.27.1 Community Edition inside the `guinevere-postgres` container (postgres:16-trixie custom image). Configured `shared_preload_libraries` and enabled the extension.

## Runtime Changes (VPS)

| Change | Detail |
|---|---|
| TimescaleDB apt repo | `/etc/apt/sources.list.d/timescaledb.list` (inside container) |
| Package | `timescaledb-2-postgresql-16` (2.27.1) |
| shared_preload_libraries | `timescaledb` (via ALTER SYSTEM → `postgresql.auto.conf`) |
| Container restart | `docker restart guinevere-postgres` only |
| Extension | `CREATE EXTENSION timescaledb CASCADE` → 2.27.1 |

## Validation

- Extensions: plpgsql 1.0, timescaledb 2.27.1, vector 0.8.2
- Hypertable test: PASS (create, insert 2 rows, count 2, drop)
- shared_preload_libraries: shows `timescaledb`
- pg_isready: accepting connections
- Aizanta: 5/5 healthy, no containers restarted
- Protected ports: unchanged

## Rollback

```bash
docker exec guinevere-postgres psql -U guinevere -d guinevere -c 'DROP EXTENSION timescaledb CASCADE'
docker exec guinevere-postgres su - postgres -c "psql -c 'ALTER SYSTEM RESET shared_preload_libraries'"
docker restart guinevere-postgres
docker exec guinevere-postgres apt-get remove -y timescaledb-2-postgresql-16
```

## Caveats

- TimescaleDB Community Edition — no compression or continuous aggregates (requires Apache 2 Edition)
- guinevere-postgres restart was required for shared_preload_libraries — duration ~2 seconds
- PostgreSQL data preserved through Docker volume mount