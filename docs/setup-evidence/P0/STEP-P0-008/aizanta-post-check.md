# STEP-P0-008 — Aizanta Post-Check

## Aizanta Containers (post-timezone/NTP)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All containers **healthy**, no restarts triggered.

## Protected Ports (unchanged)

```
127.0.0.1:6379    docker-proxy (Aizanta Redis)
100.94.104.22:80  docker-proxy (Aizanta nginx)
127.0.0.1:8080    crowdsec (loopback only, P0-006)
127.0.0.1:5432    docker-proxy (Aizanta PostgreSQL)
```

## SSH

```
$ ssh guinevere-vps "whoami && hostname && date"
guinevere
faiz-prod-01
Sun May 31 01:16:40 PM WIB 2026
```

## Impact Assessment

- **Aizanta**: No impact. Timezone change is host-level; Docker containers run in UTC by default and do not inherit host TZ unless explicitly configured.
- **Guinevere**: Timezone set to Asia/Jakarta (WIB, UTC+7). Chrony uses Indonesian NTP pools. systemd-timesyncd masked.
- **Services restarted**: fail2ban, crowdsec, crowdsec-firewall-bouncer, rsyslog. All recovered normally.
- **Shared VPS**: No resource change. Time config is host-level, benefits both projects.