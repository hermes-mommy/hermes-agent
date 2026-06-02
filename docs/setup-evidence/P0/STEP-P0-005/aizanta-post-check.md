# STEP-P0-005 Aizanta Post-Check

Date: 2026-05-31
Host: faiz-prod-01 / 100.94.104.22

## Scope

P0-005 configured fail2ban for SSH brute-force protection. Shared VPS policy requires Aizanta health and protected port checks before and after every infrastructure action.

## Final Aizanta Container Health

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

## Final Protected Port Check

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

## SSH Access Check

Command from local Windows client:

```powershell
ssh -o BatchMode=yes -o ConnectTimeout=10 guinevere-vps "whoami && hostname"
```

Output:

```text
guinevere
faiz-prod-01
```

## Impact Assessment

- No Aizanta containers were restarted or edited.
- No Aizanta Docker networks were touched.
- No Aizanta PostgreSQL or Redis data was touched.
- No `/home/aizanta/` files were touched.
- Protected ports remained unchanged: Aizanta PostgreSQL on `127.0.0.1:5432`, Aizanta Redis on `127.0.0.1:6379`, Aizanta nginx on `100.94.104.22:80`.
- Existing Aizanta fail2ban file `/etc/fail2ban/jail.d/aizanta-sshd.local` was read but not edited.
