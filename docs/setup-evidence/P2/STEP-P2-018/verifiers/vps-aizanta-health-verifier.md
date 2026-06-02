# VPS / Aizanta Health Verifier — P2-018

## Verdict
N/A from local Windows environment; VPS is not accessible from this session.

## Scope
This verification is **local-only** and confirms that the VPS health check must be completed during the deployment window, not from the current Windows workstation.

## Required VPS Deployment Checklist
Run the following checks on the VPS at deployment time:

1. `docker ps | grep aizanta`
   - Must show **all Aizanta containers running**.
   - Expected result: the Aizanta stack is present and healthy in Docker.

2. `ss -tlnp | grep -E '5432|6379|80'`
   - Must show **Aizanta ports occupied**, not Guinevere services.
   - Expected result: the Aizanta deployment owns the intended ports on the VPS.

## Port Ownership Reference
Guinevere local/runtime ports must remain distinct from Aizanta VPS ports:

- PostgreSQL: `5433`
- PgBouncer: `5434`
- Redis: `6380`
- 9Router: `20128`

## Verification Note
VPS health verification **must be re-run at deployment time**. This report only records the local Windows constraint and the required checks.

## Release Gate
Confirm **Aizanta is intact before Guinevere Discord starts**. The Discord runtime must not begin until the VPS deployment has passed the checks above.

## Result
- Local environment: Windows
- VPS access: unavailable
- Verification status: deferred to deployment-time VPS validation
