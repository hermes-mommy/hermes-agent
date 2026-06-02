# P0-021 Summary — Redis ACL Configuration

**Date**: 2026-05-31
**Step**: P0-021
**ADR**: ADR-030 (Redis DB assignments), ADR-015 (SOPS)

## What Was Done
Created 6 Redis ACL users with least-privilege access on the Guinevere Redis instance (7.4.9-alpine, 127.0.0.1:6380). Each user has +@all -@dangerous permissions (full command set minus destructive/admin commands). guinevere_admin retains full +@all. Default user disabled, requirepass removed.

## Runtime Changes (VPS)
- 6 ACL users created: guinevere_admin, guinevere_core, guinevere_session, guinevere_cache, guinevere_scheduler, guinevere_surveillance
- Default user disabled
- requirepass removed (superseded by ACL)
- BGSAVE executed for persistence
- Container NOT restarted

## Files Created (Local)
- `docs/setup-evidence/P0/STEP-P0-021/` — evidence artifacts (NEW)
- `secrets/redis-acl-passwords.yaml` — SOPS encrypted (600, guinevere:guinevere)

## Implementation Notes
- redis-py's acl_setuser() helper corrupts passwords; raw execute_command() used
- All auth tests executed via redis-py inside Docker container

## Caveats
- aclfile not configured (ACL state persists via RDB)
- Keyspace (DB) restrictions not yet applied (requires redis.conf edit)
- ACL reload needed if container restarts and RDB is stale