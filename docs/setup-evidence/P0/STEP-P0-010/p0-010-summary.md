# STEP-P0-010 — Docker Network Isolation Summary

## What Was Done

Created `guinevere-net` — an isolated Docker bridge network (172.28.0.0/16) for Guinevere containers, separate from Aizanta's aizanta_aizanta-internal (172.18.0.0/16).

## Runtime Changes (VPS)

| Change | Value |
|---|---|
| Network | `guinevere-net` |
| Driver | bridge |
| Subnet | 172.28.0.0/16 |
| IPs available | 65,533 |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-010/docker-network.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-010/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-010/p0-010-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-010/verification.md` | Created |
| `PROGRESS.md` | Updated: 10→11/257, P0 10→11/29 |
| `CHECKLIST.md` | P0-010 checked |
| `stepprompts/StepPrompts.md` | P0-010 status → ✅ Completed |

## Validation

- guinevere-net exists: `docker network ls` shows guinevere-net bridge local
- Subnet correct: 172.28.0.0/16 with 65533 available IPs
- No conflict: Aizanta uses 172.18.0.0/16, Docker default bridge 172.17.0.0/16
- Aizanta: 5/5 healthy, ports unchanged
- SSH: guinevere-vps connects

## Network Isolation

Docker enforces network isolation via nftables FORWARD chain rules. Containers on guinevere-net cannot reach containers on aizanta_aizanta-internal or the default bridge, and vice versa.

## Caveats

1. **172.28.0.0/16 in Docker default pools**: Docker's auto-allocation range includes 172.28.0.0/14. Creating this network pre-allocates from that pool. If future docker-compose files try to auto-allocate without explicit subnet, Docker will skip the used range. This is documented, not a conflict.
2. **Docker bypasses UFW**: Published ports on guinevere-net containers will bypass UFW via Docker's PREROUTING rules. Mitigation via DOCKER-USER chain at container deployment time.
3. **/16 vs /24**: StepPrompts uses /16 (65,534 addresses). Industry best practice is /24 (254 addresses). /16 is acceptable for pre-production planning; can be tightened when actual container count is known.

## Rollback

```bash
docker network rm guinevere-net
```