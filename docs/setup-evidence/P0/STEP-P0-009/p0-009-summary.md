# STEP-P0-009 — Cgroup Resource Limits Summary

## What Was Done

Created a systemd slice unit for Guinevere services enforcing resource limits per ADR-014 shared VPS allocation.

## Runtime Changes (VPS)

| Change | Value |
|---|---|
| Slice file | `/etc/systemd/system/guinevere.slice` |
| MemoryMax | 8 GiB |
| MemoryHigh | 7 GiB |
| CPUQuota | 200% (2 cores) |
| IOWeight | 50 |
| TasksMax | 512 |
| State | active, 0 tasks assigned |

## Local Changes

| File | Action |
|---|---|
| `docs/setup-evidence/P0/STEP-P0-009/guinevere-slice.conf` | Created (copy of deployed file) |
| `docs/setup-evidence/P0/STEP-P0-009/cgroup-status.txt` | Created |
| `docs/setup-evidence/P0/STEP-P0-009/aizanta-post-check.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-009/p0-009-summary.md` | Created |
| `docs/setup-evidence/P0/STEP-P0-009/verification.md` | Created |
| `PROGRESS.md` | Updated: 9→10/257, P0 9→10/29 |
| `CHECKLIST.md` | P0-009 checked |
| `stepprompts/StepPrompts.md` | P0-009 status → ✅ Completed |

## Validation

- Cgroup v2 memory.max: 8589934592 (8G)
- Cgroup v2 memory.high: 7516192768 (7G)
- Cgroup v2 cpu.max: 200000 100000 (200%)
- Cgroup v2 io.weight: default 50
- Cgroup v2 pids.max: 512
- Aizanta: 5/5 healthy, ports unchanged
- SSH: guinevere-vps connects

## Caveats

1. **TasksMax=512**: Research suggests this may be low for Docker containers (one Node.js + sidecar can use 200-300 threads). Recommend monitoring and increasing to 2048 if needed at service creation time.
2. **CPUQuota=200%**: Matches ADR-014 allocation (2 of 4 cores). If Guinevere needs burst to 4 cores, can increase to 400% later.
3. **No MemorySwapMax set**: On cgroup v2, swap is unlimited for this slice. Recommend setting `MemorySwapMax=12G` at service creation time.
4. **Slice is empty**: No processes currently assigned. Enforcement begins when services are created in P1-P8 with `Slice=guinevere.slice`.

## Rollback

```bash
sudo systemctl stop guinevere.slice
sudo rm /etc/systemd/system/guinevere.slice
sudo systemctl daemon-reload
```