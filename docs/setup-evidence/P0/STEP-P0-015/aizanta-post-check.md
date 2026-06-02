# STEP-P0-015 — Aizanta Post-Check

## Aizanta Containers

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 8 days (healthy)
aizanta-nginx Up 8 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All Aizanta containers **healthy**, unchanged by pgvector installation.

## Protected Ports

```
$ ss -tlnp | grep -E '5432|6379|80'
LISTEN 127.0.0.1:6379     docker-proxy (Aizanta Redis)
LISTEN 100.94.104.22:80   docker-proxy (Aizanta nginx)
LISTEN 127.0.0.1:5432     docker-proxy (Aizanta PostgreSQL)
```

All Aizanta ports unchanged. Guinevere PostgreSQL still on 127.0.0.1:5433.

## Shared VPS Impact

- **Aizanta**: No impact. Aizanta postgres:16-alpine container untouched. Only guinevere-postgres was stopped/restarted.
- **Guinevere**: pgvector 0.8.2 installed in container, data volume preserved, no data loss.
- **Network**: guinevere-net unchanged, container IP 172.28.0.2 preserved.
- **Container**: Old `guinevere-postgres` removed, new `guinevere-postgres` with pgvector running on same image:tag.