# STEP-P0-007 — Swap Configuration Verification

| Field | Value |
|---|---|
| **Step** | P0-007 |
| **Type** | Infrastructure |
| **Date** | 2026-05-31 |
| **Implementer** | Guinevere (parent orchestrator) |
| **Status** | PASS, independent auditor gate passed |

## What Was Done

Created a 4GB swap file (`/swapfile`) on the shared VPS and tuned kernel VM parameters (`vm.swappiness=10`, `vm.vfs_cache_pressure=50`) via `/etc/sysctl.d/99-guinevere.conf`. Persisted swap in `/etc/fstab`. Backed up pre-change fstab.

## Files Changed

### Remote (VPS)
| File | Action |
|---|---|
| `/swapfile` | Created (4GB, 0600) |
| `/etc/sysctl.d/99-guinevere.conf` | Created |
| `/etc/fstab` | Appended `/swapfile none swap sw 0 0` |
| `/etc/fstab.backup.p0-007-20260531` | Created (pre-change backup) |

### Local (repo)
| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-007/swap-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/p0-007-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/verification.md` | Created |
| `PROGRESS.md` | Updated counters, checked P0-007 |
| `CHECKLIST.md` | Checked P0-007 line |
| `stepprompts/StepPrompts.md` | Updated P0-007 status/checks |

## Validation Results

### Swap Active
```
$ swapon --show
NAME      TYPE SIZE USED PRIO
/swapfile file   4G   0B   -2

$ free -h | grep Swap
Swap:          4.0Gi          0B       4.0Gi
```

### Kernel Parameters
```
$ cat /proc/sys/vm/swappiness
10

$ cat /proc/sys/vm/vfs_cache_pressure
50
```

### Fstab Persistence
```
$ grep swap /etc/fstab
/swapfile none swap sw 0 0
```

### Aizanta Health
```
$ docker ps --format '{{.Names}} {{.Status}}' | grep aizanta
aizanta-bot Up 7 days (healthy)
aizanta-nginx Up 7 days (healthy)
aizanta-frontend Up 8 days (healthy)
aizanta-postgres Up 8 days (healthy)
aizanta-redis Up 8 days (healthy)
```

### Protected Ports (unchanged)
```
127.0.0.1:6379    docker-proxy (Aizanta Redis)
100.94.104.22:80  docker-proxy (Aizanta nginx)
127.0.0.1:5432    docker-proxy (Aizanta PostgreSQL)
```

### SSH
```
$ ssh guinevere-vps "whoami && hostname"
guinevere  faiz-prod-01
```

## Evidence Artifacts

| File | Description |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-007/swap-status.txt` | Swap state, sysctl, fstab, rollback |
| `docs/setup-evidence/P0/STEP-P0-007/aizanta-post-check.md` | Aizanta health post-swap |
| `docs/setup-evidence/P0/STEP-P0-007/p0-007-summary.md` | Human-readable summary |
| `docs/setup-evidence/P0/STEP-P0-007/verification.md` | This file |
| `audit-reports/P0/STEP-P0-007/external-swap-report.md` | External research report |

## Shared VPS Impact

- **Aizanta containers**: All 5 containers healthy, no restarts. Swap is a kernel-level resource; Docker containers use host swap transparently.
- **Aizanta networks/ports/files**: None touched.
- **Guinevere**: 4GB swap added at <5% of free disk. No port conflict.
- **Resource allocation**: Swap is shared; 4GB total on 15GB RAM + 85GB free disk is safe.

## ADR Compliance

| ADR | Status |
|---|---|
| ADR-014 (VPS/container architecture) | Compliant — shared resource, no Aizanta impact |
| ADR-015 (Secrets management) | N/A — no secrets involved |
| ADR-018 (Defense-in-depth) | Compliant — improves system stability under memory pressure |
| ADR-019 (Access control/VPN mesh) | N/A — no access change |

## AC Reference

| AC | Status |
|---|---|
| AC-CORE-001 (systemd-managed core daemon) | N/A — kernel-level tuning, relevant for future daemon stability |
| AC-CORE-002 (service resilience) | Compliant — swap improves memory-pressure resilience |

## Rollback / Re-run Safety

**Rollback**:
```bash
sudo swapoff /swapfile
sudo sed -i '/^\/swapfile /d' /etc/fstab
sudo rm /swapfile
sudo rm /etc/sysctl.d/99-guinevere.conf
sysctl -w vm.swappiness=60
sysctl -w vm.vfs_cache_pressure=100
```

**Re-run safety**: `fallocate` on existing `/swapfile` would fail (file exists). Remove first or use different path.

**Fstab backup**: `/etc/fstab.backup.p0-007-20260531`

## Design Decisions / Caveats

1. **4GB vs 8GB**: StepPrompts specifies 4GB; DeploymentGuide/TechArch references 8GB. Chose 4GB for shared VPS safety. Can increase if monitoring shows pressure.
2. **swappiness=10**: Low swappiness is ideal for Python/LLM workloads (keep hot memory in RAM, only swap cold pages).
3. **No Docker --memory-swap set yet**: Docker containers will inherit default behavior (swap = 2× memory limit if set, or unlimited if no memory limit). This will be configured in container deployment steps (P1+).
4. **`fallocate` safe**: ext4 on kernel 6.8.x supports `fallocate` for swap file creation without the `dd` overhead.

## Evidence Gate

| Gate | Status |
|---|---|
| Parent verification | PASS — live checks confirm swap active, swappiness=10, vfs_cache_pressure=50, fstab persists, Aizanta healthy, SSH works |
| Evidence files | 4 evidence files created |
| Diagnostics | Clean |
| Secret scan | No matches |
| Tracker sync | PROGRESS, CHECKLIST, StepPrompts synced |
| Independent auditor gate | PASS — `audit-reports/P0/STEP-P0-007/step-p0-007-auditor-report.md` |

**Auditor summary**: All 10 DoD items verified against live VPS state. Swap 4GB active, swappiness=10, vfs_cache_pressure=50, fstab persistent, Aizanta healthy, SSH works, no secrets, diagnostics clean, ADR-014 compliant. One non-blocking finding: Docker `--memory-swap` limits not yet set (deferred to P1+).

## Footer

**Source task**: STEP-P0-007 (from `stepprompts/StepPrompts.md`)
**Date**: 2026-05-31
**Implementer**: Guinevere (parent orchestrator, via direct SSH)
**Validation method**: Live SSH command execution + output capture