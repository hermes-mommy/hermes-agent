# Aizanta Post-Check — STEP-P0-017

**Date**: 2026-05-31
**Step**: P0-017 — Database Users, Schemas, and Least Privilege

## Container Health
| Container | Status |
|---|---|
| aizanta-bot | Up 7 days (healthy) |
| aizanta-nginx | Up 7 days (healthy) |
| aizanta-frontend | Up 8 days (healthy) |
| aizanta-postgres | Up 8 days (healthy) |
| aizanta-redis | Up 8 days (healthy) |

All 5/5 Aizanta containers healthy.

## Protected Ports
| Port | Binding | Service |
|---|---|---|
| 127.0.0.1:6379 | docker-proxy | Aizanta Redis |
| 100.94.104.22:80 | docker-proxy | Aizanta nginx |
| 127.0.0.1:5432 | docker-proxy | Aizanta PostgreSQL |

No Aizanta ports changed. CrowdSec local API on 127.0.0.1:8080 also unchanged.

## Shared VPS Impact
- No Aizanta containers restarted or touched
- No Aizanta Docker networks modified
- No Aizanta PostgreSQL/Redis accessed
- `/home/aizanta/` untouched
- guinevere-postgres container NOT restarted — user/schema creation via SQL only