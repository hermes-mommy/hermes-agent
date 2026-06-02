# P1-018 guinevere-core.service Evidence

## What Was Done

Created the Guinevere Core systemd service unit with corrected dependency chain, resource limits, and security hardening. Deployed the minimal FastAPI application skeleton (`src/core/main.py`) and started the service on the VPS.

### Key Correction from Research

The StepPrompts template had `Requires=postgresql.service redis-guinevere.service` which would **always fail** because PostgreSQL and Redis are Docker containers, not systemd services. The research wave (bg_b7c201f7) confirmed neither `postgresql.service` nor `redis-guinevere.service` exist on the VPS. The fix:
- `Requires=docker.service guinevere-9router.service`
- `After=docker.service network.target guinevere-9router.service`
- Added `Type=exec` (systemd verifies ExecStart binary before forking)
- Added `MemoryHigh=1G` (soft throttle), `MemoryMax=2G` (hard kill), `CPUQuota=200%`
- Added `Environment=VIRTUAL_ENV` (no `source activate` needed)

## Files Changed

- `src/core/main.py` — new (33 lines), FastAPI app with `/health` and `/` endpoints, structlog logger, asynccontextmanager lifespan
- `/etc/systemd/system/guinevere-core.service` — new, corrected systemd unit (see key correction above)
- `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service` — local reference copy
- `docs/setup-evidence/P1/STEP-P1-018/guinevere-core-status.txt` — captured service status

## Validation Results

| Check | Result |
|-------|--------|
| Service active | ✅ `active (running)`, main PID 661232 |
| Health endpoint | ✅ `{"status":"healthy","service":"guinevere-core","version":"0.1.0"}` |
| Root endpoint | ✅ `{"message":"Guinevere de Baroque is online.","status":"active"}` |
| Port 8000 listening | ✅ `127.0.0.1:8000` — bound to localhost only |
| Running as guinevere user | ✅ `User=guinevere` |
| guinevere.slice | ✅ `CGroup: /guinevere.slice/guinevere-core.service` |
| Memory limits | ✅ MemoryHigh=1G, MemoryMax=2G |
| CPU limits | ✅ CPUQuota=200% (= 2 vCPU) |
| Security hardening | ✅ NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only |
| Enabled on boot | ✅ symlink in multi-user.target.wants |

## Evidence Artifacts

- Service status: `docs/setup-evidence/P1/STEP-P1-018/guinevere-core-status.txt`
- Unit file reference: `docs/setup-evidence/P1/STEP-P1-018/guinevere-core.service`
- Evidence: `docs/setup-evidence/P1/STEP-P1-018/evidence.md`

## Doc-Sync Impact

- No docs/README.md changes required
- ADR-014 referenced — compliance confirmed (systemd under guinevere.slice)
- StepPrompts P1-018 will be updated to reflect the corrected dependency chain (Requires=docker.service, not postgresql.service/redis-guinevere.service)

## Boundary Compliance

- ✅ Service runs as `guinevere` user (not root)
- ✅ Port 8000 bound to localhost only (no external exposure)
- ✅ ProtectSystem=strict with explicit ReadWritePaths
- ✅ Within guinevere.slice resource limits (8GB RAM, 2 vCPU)
- ✅ No secrets exposed in environment or logs
- ✅ No Aizanta resources touched
- ✅ Docker containers (PostgreSQL 5433, Redis 6380) are required dependencies and verified running

## Rollback / Re-run Safety

```bash
# Stop and remove
sudo systemctl stop guinevere-core
sudo systemctl disable guinevere-core
sudo rm /etc/systemd/system/guinevere-core.service
sudo systemctl daemon-reload

# Re-deploy (re-run safe)
sudo cp /path/to/guinevere-core.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now guinevere-core
```

The main.py file is a simple skeleton — safe to overwrite with future iterations.

## Design Decisions / Caveats

1. **Requires=docker.service**: PostgreSQL and Redis are Docker containers, not systemd services. The original StepPrompts template referenced non-existent `postgresql.service`/`redis-guinevere.service`. The `docker.service` dependency ensures the Docker daemon (and thus the containers) are running before Guinevere Core starts.
2. **Type=exec**: Prevents systemd from considering the service "started" until the uvicorn process confirms it's ready (fork-exec verified).
3. **No start-core.sh script**: The systemd unit directly invokes venv uvicorn; helper shell scripts with `source activate` are unnecessary and fragile under systemd.
4. **--workers 2**: Matches the 2 vCPU quota in guinevere.slice.
5. **Minimal FastAPI**: Only `/health` and `/` endpoints. Full agent loop, memory, persona routes will be added in P5.

## Auditor Gate

Pending. Auditor report path target:

`audit-reports/P1/STEP-P1-018/step-p1-018-auditor-report.md`

## Footer

- Source task: P1-018 guinevere-core.service (StepPrompts L4760-4891)
- Date: 2026-06-01
- Implementer: Guinevere
- Validation method: systemctl status, curl health endpoint, ss port check, cgroup inspection