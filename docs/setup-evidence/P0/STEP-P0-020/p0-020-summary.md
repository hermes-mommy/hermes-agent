# P0-020 Summary — Redis 7 Setup

**Date**: 2026-05-31
**Step**: P0-020
**ADR**: ADR-030 (Redis DB Assignments)

## What Was Done
Deployed Redis 7.4.9 as a Docker container (redis:7.4-alpine) on guinevere-net, listening on 127.0.0.1:6380. Configured with RDB+AOF dual persistence, 2GB maxmemory, allkeys-lru eviction, and SOPS-encrypted master password.

## Runtime Changes (VPS)
- Container: guinevere-redis on guinevere-net
- Port: 127.0.0.1:6380->6379/tcp
- Volume: /home/guinevere/data/redis → /data
- SOPS: /home/guinevere/secrets/redis-password.yaml

## Files Created (Local)
- secrets/redis-password.yaml — SOPS encrypted

## ADR Compliance
- ADR-030: Redis on port 6380, 16 databases (DB0-DB5 for Guinevere, DB6-DB15 reserved)
- ADR-014: Docker deployment, resource limits (1 CPU, 3GB RAM cap)
- ADR-015: SOPS+age encryption, no plaintext in repo

## Key Config Highlights
- maxmemory 2GB (Faiz override — StepPrompts had 512MB)
- RDB save 900/1 300/10 60/10000
- AOF appendonly yes, appendfsync everysec
- FLUSHALL, FLUSHDB, CONFIG disabled
- requirepass set, SOPS encrypted

## Caveats
- ACL configuration deferred to P0-021
- No replication/cluster (standalone, adequate for single VPS)
- AOF rewrite not tuned yet