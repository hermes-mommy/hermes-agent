# STEP-MAINT-01 — VPS Cleanup & Weekly Maintenance

**Step:** Cleanup CUDA dead weight + Setup Weekly Maintenance Cron
**Date:** 2026-06-08
**Auditor:** Guinevere
**Status:** ✅ FIXED

---

## 1. What Was Done

Audit found ~6.6 GB of CUDA/NVIDIA dead weight in `.venv` (no GPU on VPS — Cirrus Logic GD 5446 virtual). Also found Docker cache bloat and no regular maintenance schedule.

### Cleanup:

1. **Removed CUDA stack from `.venv`** (21 packages):
   - `torch`, `torchgen`, `triton` — PyTorch + GPU compiler (no GPU)
   - `nvidia-*` (18 packages) — CUDA libraries: cublas, cudnn, cufft, curand, cusolver, cusparse, nccl, nvtx, etc.
   - `cuda-bindings`, `cuda-pathfinder`
   - `sentence-transformers` (depends on torch, not used in `src/`)
   - **Result:** `.venv` 7.4 GB → **700 MB** (hemat ~6.6 GB)

2. **Docker system prune** (performed on first run):
   - Reclaimed **2.591 GB** from unused Docker build cache/images

3. **Cleaned __pycache__** (445 directories on first run)

### Maintenance Automation:

4. **Created script** (`~/.hermes/scripts/vps_weekly_maintenance.sh`):
   - Disk usage check + alert if >80%
   - Memory & swap report
   - Uptime & load check
   - Docker system prune (images >24h unused)
   - Docker volume prune (dangling)
   - Temp file cleanup (/tmp, files >7d)
   - Python cache cleanup (__pycache__, *.pyc)
   - Outputs formatted plaintext report

5. **Created dedicated channel** `#weekly-maintenance` via Discord Bot API (id: 1513383817925230774)

6. **Scheduled cron job** `vps-weekly-maintenance` (281aa89889ed):
   - **Schedule:** `0 8 * * 0` (every Sunday 08:00 WIB)
   - **Mode:** `no_agent=True` (script-only, zero LLM token cost)
   - **Deliver:** `discord:#weekly-maintenance`
   - **Next run:** 2026-06-14T08:00:00+07:00

### Known Limitations:
- Journald logs (3.7 GB) & apt cache — cannot clean without root (VPS has `NoNewPrivs` + `Seccomp: 2` — sudo blocked at kernel level)

---

## 2. Files Changed

| Path | Change |
|------|--------|
| `.venv/lib/python3.12/site-packages/torch/` | **DELETED** (~1.7 GB) |
| `.venv/lib/python3.12/site-packages/nvidia/` | **DELETED** (~4.3 GB) |
| `.venv/lib/python3.12/site-packages/triton/` | **DELETED** (~639 MB) |
| `.venv/lib/python3.12/site-packages/sentence_transformers/` | **DELETED** |
| `~/.hermes/scripts/vps_weekly_maintenance.sh` | **NEW** |
| Cron: vps-weekly-maintenance (281aa89889ed) | **NEW** — weekly |
| Discord: #weekly-maintenance (1513383817925230774) | **NEW** — dedicated channel |

---

## 3. Verification

### Script execution test:

```
==========================================
  🧹 VPS Weekly Maintenance
  2026-06-08 10:27 WIB
==========================================

=== 1. DISK USAGE ===
  Total: 99G | Used: 33G | Avail: 61G | 36%
  ✅ Disk sehat (< 80%)

=== 2. MEMORY ===
Mem:            15Gi       5.1Gi       858Mi       102Mi       9.7Gi        10Gi
Swap:          4.0Gi       1.1Mi       4.0Gi

=== 3. UPTIME & LOAD ===
  up 2 weeks, 1 day, 23 hours, 52 minutes
  Load: 0.67 0.82 0.70

=== 4. DOCKER CLEANUP ===
  Containers running: 18
  All containers: 18
  Images: 17
  Volumes: 3
  Pruning unused Docker resources...Total reclaimed space: 0B
  Pruning dangling volumes...Total reclaimed space: 0B

=== 5. CLEANUP TEMP ===
  /tmp: 20K → 20K

=== 6. PYTHON CACHE ===
  __pycache__ dirs removed: 9

==========================================
  ✅ VPS Weekly Maintenance Selesai
==========================================
```

### Cleanup verification:

- `pip list | grep -iE "torch|nvidia|triton|cuda|sentence"` → **empty** (all removed)
- `.venv` size: 7.4 GB → **700 MB**
- Disk used: **36 GB → 33 GB** (after first docker prune took effect)

### Channel tests (2026-06-08 10:30 WIB):

All 11 channels verified — direct message test + automation script execution:

| Channel | Method | Result |
|---------|--------|--------|
| `#guinevere-planning` | send_message test | ✅ msg: 1513385517272797295 |
| `#guinevere-status` | send_message test | ✅ msg: 1513385523794673674 |
| `#guinevere-logs` | send_message test | ✅ msg: 1513385530383929485 |
| `#audit-log` | send_message test | ✅ msg: 1513385536910528633 |
| `#evidence-log` | send_message test | ✅ msg: 1513385544388841615 |
| `#guinevere-evidence` | send_message test | ✅ msg: 1513385551502508102 |
| `#hermes-shadow` | send_message test | ✅ msg: 1513385626802585701 |
| `#system-health` | `health_check_post.py` execution | ✅ msg: 1513385595416612915 |
| `#cost-tracker` | `cost_tracker_post.py` execution | ✅ msg: 1513385603025076305 |
| `#weekly-maintenance` | send_message test | ✅ msg: 1513383892814532778 |
| `#guinevere-chat` | (this channel) | ✅ active (conversational) |

**All 11 channels ✅ fully operational.**

### Cron job config:

```
deliver:         discord:1510876414671323206:1513383817925230774
schedule:        0 8 * * 0
no_agent:        true
script:          vps_weekly_maintenance.sh
next_run_at:     2026-06-14T08:00:00+07:00
```

---

## 4. Caveats

- **Journald logs (3.7 GB)** still present — requires root (`sudo` blocked by `NoNewPrivs` + seccomp)
- **apt cache** — same root limitation
- **Pip http cache (83 MB)** — on read-only filesystem, cannot be cleaned; negligible size
- **NoNewPrivs flag** — VPS security hardening, intentional, not a bug
