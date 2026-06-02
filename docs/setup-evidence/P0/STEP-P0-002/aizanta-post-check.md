# P0-002 Aizanta Post-Action Check

Date: 2026-05-31
Step: P0-002 SSH Config Update

## Docker containers after P0-002

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

## Protected listening ports after P0-002

Command:
```bash
ss -tlnp | grep -E '5432|6379|80'
```

Output:
```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

## Result

Aizanta remained healthy after P0-002. Protected ports stayed unchanged:

- PostgreSQL: `127.0.0.1:5432`
- Redis: `127.0.0.1:6379`
- Nginx: `100.94.104.22:80`

No Aizanta files, Docker networks, databases, Redis DBs, or service definitions were changed.
