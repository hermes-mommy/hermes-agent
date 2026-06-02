# P1-019 Service Health Check Evidence

## What Was Done

Created `scripts/health-check-p1.sh` and executed comprehensive P1 service health verification on the VPS. All 4 core services were verified: guinevere-core (FastAPI), guinevere-9router (LLM routing), PostgreSQL (Docker container), Redis (Docker container with ACL auth). The script also documents the graceful degradation decision (Ollama skipped per ADR-028).

### Redis ACL Fix

The initial StepPrompts template used `redis-cli --pass <password> PING` with the `redis_master_password` from `redis-password.yaml`. This failed because Redis on the VPS uses **ACL authentication** — the `guinevere_core` user requires `--user guinevere_core --pass <password>` with the password from `redis-acl-passwords.yaml`. The health check script was corrected to use the proper ACL credentials.

## Files Changed

- `scripts/health-check-p1.sh` — new, comprehensive health check script
- `docs/setup-evidence/P1/STEP-P1-019/health-check.txt` — captured output
- `docs/setup-evidence/P1/STEP-P1-019/evidence.md` — this file

## Validation Results

| Service | Check | Result |
|---------|-------|--------|
| guinevere-core | `curl http://localhost:8000/health` | ✅ PASS |
| guinevere-9router | `curl http://localhost:20128/api/health` | ✅ PASS |
| Graceful degradation | Ollama skipped per ADR-028 Superseded | ✅ PASS (documented) |
| PostgreSQL | `SELECT 1` via docker exec | ✅ PASS |
| Redis | `PING` via guinevere_core ACL user | ✅ PASS |
| **Summary** | 0 failures | ✅ ALL PASS |

## Evidence Artifacts

- Health check script: `scripts/health-check-p1.sh`
- Health check output: `docs/setup-evidence/P1/STEP-P1-019/health-check.txt`
- Evidence: `docs/setup-evidence/P1/STEP-P1-019/evidence.md`

## Doc-Sync Impact

- No docs/README.md changes required
- StepPrompts P1-019 verification checklist satisfied (6/6 checks pass)
- ADR-028 (Superseded) — graceful degradation documented

## Boundary Compliance

- ✅ No secrets exposed in health check output
- ✅ No Aizanta resources touched
- ✅ All services within guinevere.slice
- ✅ Core + 9Router bound to localhost only
- ✅ Docker containers (PostgreSQL + Redis) are isolated from Aizanta

## Rollback / Re-run Safety

Safe to re-run anytime:
```bash
bash /home/guinevere/code/guinevere/scripts/health-check-p1.sh
```

Read-only verification — no state is modified. Output is captured to stdout only.

## Design Decisions / Caveats

1. **Redis ACL auth**: The VPS Redis uses ACL users (`guinevere_core`, `guinevere_admin`, etc.) with individual passwords from `redis-acl-passwords.yaml`. The `redis-password.yaml` `redis_master_password` is not valid for direct `redis-cli` authentication.
2. **Docker exec for PostgreSQL/Redis**: Both databases are Docker containers accessed via `docker exec` rather than TCP — avoids exposing database ports externally.
3. **SOPS decryption**: Requires `SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` to be set.
4. **No secrets in output**: The script captures PASS/FAIL only — passwords are passed as shell variables, not echoed.

## Auditor Gate

Pending. Auditor report path target:

`audit-reports/P1/STEP-P1-019/step-p1-019-auditor-report.md`

## Footer

- Source task: P1-019 Service Health Check (StepPrompts L4894-4968)
- Date: 2026-06-01
- Implementer: Guinevere
- Validation method: bash script with 5 service checks against live VPS state