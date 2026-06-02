# STEP-P0-016 — Aizanta Post-Check

## Aizanta Containers (post-TimescaleDB)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All containers **healthy**. Only `guinevere-postgres` was restarted — Aizanta containers untouched.

## Protected Ports

```
127.0.0.1:6379    docker-proxy (Aizanta Redis)
100.94.104.22:80  docker-proxy (Aizanta nginx)
127.0.0.1:8080    crowdsec (loopback only)
127.0.0.1:5432    docker-proxy (Aizanta PostgreSQL)
127.0.0.1:5433    docker-proxy (Guinevere PostgreSQL)
```

## Impact

- **guinevere-postgres**: Restarted once (AL3R SYSTEM + shared_preload_libraries activation)
- **Aizanta-postgres**: NOT restarted — 8 days uptime preserved
- **Data**: All PostgreSQL data preserved through volume mount at `/home/guinevere/data/postgres`