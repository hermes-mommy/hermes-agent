# VPS / Aizanta Health Verifier — P2-019

## Verdict
N/A from local Windows. VPS is not accessible from this environment, so live container/port verification must be performed on the VPS at deployment time.

## Scope
P2-019 is notification routing only and does not change infrastructure. This verifier records the required VPS health checks that must be confirmed before production rollout.

## Required VPS Deployment Checklist
Run these checks directly on the VPS during deployment:

1. Confirm all Aizanta containers are running:
   ```bash
   docker ps | grep aizanta
   ```

2. Confirm Aizanta production ports are occupied:
   ```bash
   ss -tlnp | grep -E '5432|6379|80'
   ```

3. Confirm Guinevere service ports are reserved separately and not colliding with Aizanta:
   - PostgreSQL: `5433`
   - Redis: `6380`
   - 9Router: `20128`

## Deployment Safety Note
VPS verification must be re-run at deployment time. Do not rely on this local report as proof of live infrastructure health.

## Operational Requirement
Aizanta must remain intact and healthy before Guinevere Discord starts. If Aizanta is degraded, do not start Guinevere Discord until the VPS state is verified and stable.

## Evidence Status
- Environment checked: local Windows
- Live VPS access: unavailable
- Container status: not verified locally
- Port occupancy: not verified locally

## Footer
Generated for P2-019 verification record.
