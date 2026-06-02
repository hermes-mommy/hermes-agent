# P0-018 Summary — PostgreSQL Hardening

**Date**: 2026-05-31
**Step**: P0-018
**ADR**: ADR-018 (Defense-in-Depth), ADR-027 (PostgreSQL)

## What Was Done
Hardened pg_hba.conf from all-trust to scram-sha-256 for all non-admin access. Set connection limits per user role. Enabled connection and slow-query logging.

## Runtime Changes
- pg_hba.conf: trust→scram-sha-256 (except guinevere superuser local socket for docker exec admin)
- 172.28.0.0/16 subnet added for upcoming PgBouncer
- Connection limits: core=30, surveillance=10, scheduler=10, readonly=15, backup=5
- Logging: connections on, disconnections on, DDL statements, 1s slow-query threshold
- Reloaded via pg_ctl (no container restart)

## Files
- `/home/guinevere/data/postgres/pg_hba.conf` — hardened (backup at .pre-P0-018)
- ALTER SYSTEM settings persist in postgresql.auto.conf

## ADR Compliance
- ADR-018: Defense-in-depth authentication hardening
- ADR-027: PostgreSQL security hardening, least privilege
- ADR-015: Passwords already SCRAM-SHA-256 encrypted in SOPS

## Caveats
- SSL not enabled (internal Docker network only, deferred)
- PgBouncer subnet 172.28.0.0/16 added but PgBouncer not yet deployed
- guinevere superuser retains local trust for docker exec admin convenience