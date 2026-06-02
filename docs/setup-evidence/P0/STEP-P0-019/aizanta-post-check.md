# Aizanta Post-Check — STEP-P0-019

**Date**: 2026-05-31
**Step**: P0-019 — PgBouncer Connection Pooling

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

No Aizanta ports changed.

## New Guinevere Port
| Port | Binding | Service |
|---|---|---|
| 127.0.0.1:5434 | docker-proxy | Guinevere PgBouncer |

## Shared VPS Impact
- No Aizanta containers restarted or touched
- PgBouncer on guinevere-net (172.28.0.3), isolated from aizanta-net
- PgBouncer only listens on 127.0.0.1:5434 — no external exposure