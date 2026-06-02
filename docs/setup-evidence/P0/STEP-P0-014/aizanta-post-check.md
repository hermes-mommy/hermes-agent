# STEP-P0-014 — Aizanta Post-Check

## Aizanta Containers (post-PostgreSQL deployment)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All 5 Aizanta containers **healthy** — no restarts, no impact from Guinevere PostgreSQL deployment.

## Protected Ports (unchanged)

```
$ ss -tlnp | grep -E '5432|6379|80'
LISTEN 127.0.0.1:6379        docker-proxy (Aizanta Redis)
LISTEN 100.94.104.22:80      docker-proxy (Aizanta nginx)
LISTEN 127.0.0.1:5432        docker-proxy (Aizanta PostgreSQL)
LISTEN 127.0.0.1:5433        docker-proxy (Guinevere PostgreSQL — NEW, expected)
```

Aizanta's PostgreSQL (5432), Redis (6379), and nginx (80) remain on their original ports. Guinevere PostgreSQL binds **127.0.0.1:5433** — no conflict.

## Docker Networks

```
$ docker network ls
NETWORK ID     NAME                    DRIVER    SCOPE
cbc79adf9a9b   aizanta_aizanta-internal bridge    local (Aizanta, 172.18.0.0/16)
2ec73d366b97   bridge                  bridge    local (Docker default, 172.17.0.0/16)
6cd7f11a784c   guinevere-net           bridge    local (Guinevere, 172.28.0.0/16)
```

No overlap between Aizanta (172.18.0.0/16) and Guinevere (172.28.0.0/16) networks.

## SSH

```
$ ssh guinevere-vps "whoami && hostname"
guinevere
faiz-prod-01
```

## Impact Assessment

- **Aizanta**: Zero impact. Separate Docker network, separate PostgreSQL port, separate Linux user.
- **Guinevere**: PostgreSQL 16 deployed, loopback-only, ready for extensions (pgvector P0-015, TimescaleDB P0-016).
- **Resource**: ~27MB volume initially, ~150MB RAM (shared_buffers=1GB allocated but not yet used), negligible CPU.