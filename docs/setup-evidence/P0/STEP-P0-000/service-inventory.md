# P0-000 Service Inventory

## Aizanta services detected
- `aizanta-bot` — healthy, Docker port 8000/tcp
- `aizanta-nginx` — healthy, host port 80 mapped to Tailscale IP
- `aizanta-frontend` — healthy, port 3000/tcp
- `aizanta-postgres` — healthy, `127.0.0.1:5432->5432/tcp`
- `aizanta-redis` — healthy, `127.0.0.1:6379->6379/tcp`

## Other running containers
- `objective_buck` — `python:3.12-slim`, no mapped ports
- `elastic_beaver` — `python:3.12-slim`, no mapped ports

## Local listening ports
- `127.0.0.1:5432` — PostgreSQL (Aizanta)
- `127.0.0.1:6379` — Redis (Aizanta)
- `100.94.104.22:80` — nginx (Aizanta)
- `0.0.0.0:22` — SSH
- `100.94.104.22:36438` and `[fd7a:...]` — Tailscale-related endpoints

## Notes
- No Guinevere services were installed at audit time.
- No PostgreSQL or Redis packages were installed on the host outside Docker containers.
- The host has sufficient resources for Guinevere, but port conflicts must be avoided using the offset port plan.
