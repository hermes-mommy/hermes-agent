# STEP-P0-007 — Aizanta Post-Check

## Aizanta Containers (post-swap)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All containers **healthy**, no restarts triggered by swap or sysctl changes.

## Protected Ports (unchanged)

```
$ ss -tlnp | grep -E '5432|6379|80'
LISTEN 127.0.0.1:6379        docker-proxy
LISTEN 100.94.104.22:80      docker-proxy
LISTEN 127.0.0.1:8080        crowdsec (loopback only, P0-006)
LISTEN 127.0.0.1:5432        docker-proxy
```

All Aizanta-protected ports unchanged. CrowdSec local API (127.0.0.1:8080) remains loopback-only.

## SSH

```
$ ssh guinevere-vps "whoami && hostname"
guinevere
faiz-prod-01
```

## Impact Assessment

- **Aizanta**: No impact. Swap is a kernel-level resource; Docker containers use host swap transparently. No Aizanta containers, networks, files, databases, or Redis touched.
- **Guinevere**: 4GB swap added, swappiness tuned to 10 (low — favors RAM over swap), vfs_cache_pressure to 50 (balanced).
- **Shared VPS**: No resource contention introduced; swap is shared kernel resource but 4GB is well within the 85GB free disk.