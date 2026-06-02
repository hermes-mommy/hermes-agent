# STEP-P0-010 — Aizanta Post-Check

## Aizanta Containers (post-network creation)

```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

All containers **healthy**. No impact from guinevere-net creation.

## Network Isolation

| Network | Subnet | Owner |
|---|---|---|
| aizanta_aizanta-internal | 172.18.0.0/16 | Aizanta |
| bridge | 172.17.0.0/16 | Docker default |
| guinevere-net | 172.28.0.0/16 | Guinevere |

Docker containers on different bridge networks **cannot communicate** by default. Network isolation is enforced by Docker's nftables rules in the FORWARD chain.

## Protected Ports

Protected Aizanta ports remain unchanged:
- 127.0.0.1:6379 (Aizanta Redis)
- 100.94.104.22:80 (Aizanta nginx)
- 127.0.0.1:5432 (Aizanta PostgreSQL)

## SSH

```
$ ssh guinevere-vps "whoami && hostname"
guinevere  faiz-prod-01
```

## Impact Assessment

- **Aizanta**: Zero impact. Aizanta containers use aizanta_aizanta-internal (172.18.0.0/16). guinevere-net is a separate bridge network with no routing between them.
- **Guinevere**: guinevere-net created, ready for future container deployment.
- **Shared VPS**: No resource contention. Docker bridge networks are lightweight (no overhead per network beyond iptables/nftables rules).