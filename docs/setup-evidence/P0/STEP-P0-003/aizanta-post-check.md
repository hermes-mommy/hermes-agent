# P0-003 Aizanta Post-Check

**Date:** 2026-05-31
**Scope:** Verify STEP-P0-003 directory creation did not affect Aizanta services, protected ports, or shared VPS boundaries.

## Containers

Command:

```bash
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

## Protected Ports

Command:

```bash
ssh -o BatchMode=yes -o ConnectTimeout=10 root@100.94.104.22 "ss -tlnp | grep -E '5432|6379|80'"
```

Output:

```text
LISTEN 0      4096                     127.0.0.1:6379       0.0.0.0:*    users:(("docker-proxy",pid=52688,fd=8))
LISTEN 0      4096                 100.94.104.22:80         0.0.0.0:*    users:(("docker-proxy",pid=235002,fd=8))
LISTEN 0      4096                     127.0.0.1:5432       0.0.0.0:*    users:(("docker-proxy",pid=52721,fd=8))
```

## Verdict

PASS. Aizanta containers remained healthy and protected ports stayed unchanged after STEP-P0-003.
