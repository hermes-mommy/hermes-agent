# STEP-P0-004 Aizanta Post-Check

Date: 2026-05-31
Host: faiz-prod-01 / 100.94.104.22
Step: P0-004 UFW firewall rules

## Result

PASS — Aizanta containers stayed healthy and protected ports stayed unchanged after the UFW additive rule.

## Aizanta containers before UFW change

Command:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta"
```

Output:
```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

## Protected ports before UFW change

Command:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:
```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

## Aizanta containers after UFW change

Command:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "docker ps --format '{{.Names}} {{.Status}} {{.Ports}}' | grep aizanta"
```

Output:
```text
aizanta-bot Up 7 days (healthy) 8000/tcp
aizanta-nginx Up 7 days (healthy) 100.94.104.22:80->80/tcp
aizanta-frontend Up 7 days (healthy) 3000/tcp
aizanta-postgres Up 7 days (healthy) 127.0.0.1:5432->5432/tcp
aizanta-redis Up 7 days (healthy) 127.0.0.1:6379->6379/tcp
```

## Protected ports after UFW change

Command:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:
```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

## Aizanta HTTP reachability after UFW change

Command:
```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "curl -I --max-time 10 http://100.94.104.22/"
```

Output excerpt:
```text
HTTP/1.1 200 OK
Server: nginx
Content-Type: text/html; charset=utf-8
X-Frame-Options: DENY
X-Content-Type-Options: nosniff
X-Request-ID: 248e76db8505cfa67b9964c39d1dbf0a
```

## Notes

- `systemctl list-units --type=service --state=running | grep aizanta` returned no output because Aizanta services are Docker containers, not systemd services on this VPS.
- UFW was not reset; the change was additive (`41641/udp` only), so existing SSH and Aizanta runtime state was preserved.
- Docker-published ports can bypass UFW INPUT-chain rules; Aizanta port binding remains documented as `100.94.104.22:80` for nginx and localhost-only for PostgreSQL/Redis.
