# STEP-P0-023 Aizanta Post-Check

Date: 2026-05-31
Host: faiz-prod-01 (100.94.104.22)

## Aizanta Containers

All 5 Aizanta containers healthy after Cloudflare Tunnel setup:

- aizanta-bot: Up 7 days (healthy), 8000/tcp
- aizanta-nginx: Up 7 days (healthy), 100.94.104.22:80->80/tcp
- aizanta-frontend: Up 8 days (healthy), 3000/tcp
- aizanta-postgres: Up 8 days (healthy), 127.0.0.1:5432->5432/tcp
- aizanta-redis: Up 8 days (healthy), 127.0.0.1:6379->6379/tcp

## Protected Ports

Protected Aizanta/Guinevere ports unchanged:

- 127.0.0.1:6379 -> Aizanta Redis
- 127.0.0.1:6380 -> Guinevere Redis
- 100.94.104.22:80 -> Aizanta nginx
- 127.0.0.1:8080 -> CrowdSec local API
- 127.0.0.1:5432 -> Aizanta PostgreSQL

## Shared VPS Impact

- No Aizanta containers restarted
- No Aizanta Docker networks touched
- No Aizanta database or Redis touched
- No `/home/aizanta/` files touched
- Cloudflared runs in `guinevere.slice` as user `guinevere`
- Tunnel uses outbound QUIC/HTTPS only; no public inbound VPS firewall port opened
