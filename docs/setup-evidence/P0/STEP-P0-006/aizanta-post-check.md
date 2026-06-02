# STEP-P0-006 Aizanta Post-Check

Date: 2026-05-31
Host: `faiz-prod-01` / `100.94.104.22`

## Aizanta Containers

Command:

```bash
docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta
```

Output:

```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

## Protected Ports

Command:

```bash
ss -tlnp | grep -E '5432|6379|80'
```

Output:

```text
LISTEN 0 4096 127.0.0.1:6379      0.0.0.0:* users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0 4096 100.94.104.22:80    0.0.0.0:* users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0 4096 127.0.0.1:8080      0.0.0.0:* users:(("crowdsec",pid=73662,fd=21))
LISTEN 0 4096 127.0.0.1:5432      0.0.0.0:* users:(("docker-proxy",pid=52721,fd=8))
```

`127.0.0.1:8080` is CrowdSec Local API and is loopback-only, not an Aizanta protected port conflict.

## SSH Access

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

## Shared VPS Impact

- No Aizanta container, Docker network, database, Redis, nginx config, or `/home/aizanta/` file was modified.
- Docker did not need container restart during CrowdSec repository/package installation.
- CrowdSec bouncer uses nftables tables `crowdsec` and `crowdsec6`, separate from UFW/fail2ban state.
- Aizanta Docker-published port 80 remained bound to the Tailscale IP `100.94.104.22:80`.
