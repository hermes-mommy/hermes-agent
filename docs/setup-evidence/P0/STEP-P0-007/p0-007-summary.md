# STEP-P0-007 — Swap Configuration Summary

## What Was Done

Created a 4GB swap file and tuned kernel VM parameters for Guinevere on the shared VPS.

## Runtime Changes (VPS)

| Change | Path | Value |
|---|---|---|
| Swap file | `/swapfile` | 4 GB, 0600, UUID `be6bd904-e3cb-4c65-892b-6d2e813de105` |
| Sysctl | `/etc/sysctl.d/99-guinevere.conf` | `vm.swappiness=10`, `vm.vfs_cache_pressure=50` |
| Fstab | `/etc/fstab` | `/swapfile none swap sw 0 0` |
| Fstab backup | `/etc/fstab.backup.p0-007-20260531` | Pre-change copy |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-007/swap-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/p0-007-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-007/verification.md` | Created |
| `PROGRESS.md` | Updated: 7→8/257, P0 7→8/29 |
| `CHECKLIST.md` | P0-007 checked |
| `stepprompts/StepPrompts.md` | P0-007 status → ✅ Completed |

## Validation

- `swapon --show`: `/swapfile file 4G 0B -2`
- `free -h`: Swap 4.0Gi
- `cat /proc/sys/vm/swappiness`: 10
- `cat /proc/sys/vm/vfs_cache_pressure`: 50
- Aizanta containers: all healthy, ports unchanged
- SSH: `guinevere-vps` connects

## Security

- No secrets in this step.
- Swap file is owned by root (0600) — no user-level access to swap contents.

## Rollback

```bash
sudo swapoff /swapfile
sudo sed -i '/^\/swapfile /d' /etc/fstab
sudo rm /swapfile
sudo rm /etc/sysctl.d/99-guinevere.conf
sysctl -w vm.swappiness=60
sysctl -w vm.vfs_cache_pressure=100
```

## Caveats

- Docker containers need explicit `--memory-swap` limits to use this swap space. If not set, containers' swap = 2× memory.
- Swap size (4GB) can be increased later if monitoring shows pressure; 85GB free available.