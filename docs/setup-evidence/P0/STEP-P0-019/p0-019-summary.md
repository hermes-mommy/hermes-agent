# P0-019 Summary — PgBouncer Connection Pooling

**Date**: 2026-05-31
**Step**: P0-019
**ADR**: ADR-027 (PostgreSQL)

## What Was Done
Deployed PgBouncer as a Docker container on guinevere-net to provide connection pooling for PostgreSQL. Used auth_file mode with SCRAM-SHA-256 hashes extracted from PostgreSQL pg_authid.

## Runtime Changes (VPS)
- Container: guinevere-pgbouncer (percona/percona-pgbouncer:1.25.2)
  - Network: guinevere-net (172.28.0.3)
  - Port: 127.0.0.1:5434->5432/tcp
- Config: /home/guinevere/config/pgbouncer/pgbouncer.ini
  - pool_mode: transaction
  - auth_type: scram-sha-256
  - 6 users in userlist.txt

## Why auth_file (not auth_query)
auth_query approach repeatedly failed with "password authentication failed" for the auth_user when connecting to PostgreSQL, despite the password being correct. Switched to auth_file with SCRAM hashes extracted directly from pg_authid.rolpassword — PgBouncer uses these hashes for SCRAM exchange with clients.

## ADR Compliance
- ADR-027: PostgreSQL connection pooling, Docker deployment
- Authentication: SCRAM-SHA-256 throughout

## Caveats
- PgBouncer admin_users set to guinevere (superuser) only — monitoring needs superuser access
- userlist.txt must be regenerated if PostgreSQL passwords change
- No SSL between PgBouncer and PostgreSQL (same Docker network)