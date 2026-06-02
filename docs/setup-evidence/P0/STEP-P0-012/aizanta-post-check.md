# STEP-P0-012 — Aizanta Post-Check

## Aizanta Containers (post age key generation)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All containers **healthy**. No impact from key generation — only a single file (age-key.txt) created under `/home/guinevere/secrets/`.

## Protected Ports (unchanged)

```
127.0.0.1:6379    docker-proxy (Aizanta Redis)
100.94.104.22:80  docker-proxy (Aizanta nginx)
127.0.0.1:5432    docker-proxy (Aizanta PostgreSQL)
```

## SSH

```
$ ssh guinevere-vps "whoami && hostname"
guinevere
faiz-prod-01
```

## Impact Assessment

- **Aizanta**: Zero impact. Only `/home/guinevere/secrets/age-key.txt` created.
- **Guinevere**: Age key generated (189 bytes). No service changes.
- **Shared VPS**: No resource contention. No Docker/network/port changes.