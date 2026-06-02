# External Swap Configuration Report — Ubuntu 24.04 Shared VPS

> **Report for**: STEP-P0-007 (Swap Configuration)
> **Target environment**: Ubuntu 24.04 LTS, kernel 6.8.x, ext4, 4C/16GB shared VPS, 85GB free disk
> **Current state**: 0B swap, swappiness=60, no swap file present
> **Scope**: Create 4GB swap file, tune swappiness=10 for Python/LLM workloads, co-hosted with Aizanta Docker containers
> **Date**: 2026-05-31
> **Classification**: TYPE D — Comprehensive Research

---

## 1. Swap File Creation: Best Practices for Ubuntu 24.04

### 1.1 Recommended Size

| VPS RAM | Recommended Swap | Reasoning |
|---|---|---|
| 16 GB+ | **2–4 GB** (0.125–0.25× RAM) | Fixed safety net for temporary spikes, not a RAM replacement |

**Sources**: [MassiveGRID VPS Swap Guide (2025)](https://www.massivegrid.com/blog/ubuntu-vps-swap-memory-management/), [cr0x.net SSD Swap Guide (2026)](https://cr0x.net/en/ubuntu-swap-on-ssd-safely/)

> **Recommendation for Guinevere**: **4 GB swap file** at `/swapfile`. With 16GB RAM, this provides a 25% safety buffer for LLM model loading spikes and temporary Docker memory pressure without wasting disk space. If the system is consistently using swap (check `vmstat 1` for `si`/`so` > 0), that signals insufficient RAM — upgrade, don't add more swap.

### 1.2 fallocate vs dd — Which Method?

| Method | Speed | Safety | Filesystem Compatibility |
|---|---|---|---|
| `fallocate -l` | **Instant** (preallocates blocks without zeroing) | Works on ext4 since kernel 5.8.0-25.26 (2020 fix) | ext4 ✅, XFS (since Linux 4.18) ✅, Btrfs ❌ (requires CoW disabled) |
| `dd if=/dev/zero` | Slow (~30s for 4GB) — writes every byte | **Most portable** — guaranteed no holes | All filesystems ✅ |

**Current status of fallocate on ext4**: The infamous "swapfile has holes" bug (kernel 5.7–5.8) was **fixed** in kernel 5.8.0-25.26 via `ext4: implement swap_activate aops using iomap` ([Launchpad Bug #1894910](https://bugs.launchpad.net/bugs/1894910), [Kernel Bugzilla #207585](https://bugzilla.kernel.org/show_bug.cgi?id=207585)). On Ubuntu 24.04 with kernel 6.8.x, **`fallocate` on ext4 is safe and recommended**.

**Verdict**: Use `fallocate` on this VPS. It's faster, avoids unnecessary SSD writes, and works correctly on ext4 with kernel 6.8.x. Fall back to `dd` only if `swapon` reports holes.

### 1.3 Creation Procedure (Step-by-Step)

```bash
# Step 1: Verify filesystem type (must be ext4 or xfs)
findmnt -no FSTYPE /

# Step 2: Verify no existing swap
swapon --show
# Expected: no output (confirms 0B swap)

# Step 3: Verify free disk space (need 4GB minimum)
df -h /

# Step 4: Create 4GB swap file using fallocate
sudo fallocate -l 4G /swapfile

# Step 5: Set restrictive permissions — CRITICAL for security
# Swap files contain sensitive memory pages (passwords, tokens, SSH keys)
# World-readable swap = security vulnerability
sudo chmod 600 /swapfile

# Step 6: Format as swap (creates swap signature + UUID)
sudo mkswap /swapfile
# Expected output: "Setting up swapspace version 1, size = 4 GiB"

# Step 7: Enable swap immediately
sudo swapon /swapfile

# Step 8: Verify activation
swapon --show
# Expected: /swapfile  file  4G  0B  -2

free -h
# Expected: Swap: total 4.0G, used 0B, free 4.0G
```

### 1.4 fstab Persistence

To survive reboots, add to `/etc/fstab`:

```
# /swapfile swap entry — added 2026-05-31
/swapfile none swap sw 0 0
```

**Field breakdown** (per [fstab(5)](https://manpages.ubuntu.com/manpages/noble/man5/fstab.5.html)):

| Field | Value | Meaning |
|---|---|---|
| fs_spec | `/swapfile` | Path to swap file |
| fs_file | `none` | Swap has no mount point |
| fs_vfstype | `swap` | Filesystem type |
| fs_mntops | `sw` | Standard swap options |
| fs_freq | `0` | No dump |
| fs_passno | `0` | No fsck |

**Optional**: Use `nofail` option to prevent boot failure if swap file is accidentally deleted:
```
/swapfile none swap sw,nofail 0 0
```

**Source**: [Ubuntu Community SwapFaq](https://help.ubuntu.com/community/SwapFaq/), [fstab(5) manpage](https://manpages.ubuntu.com/manpages/noble/man5/fstab.5.html)

---

## 2. Kernel Parameter Tuning for Python/LLM Workloads

### 2.1 Swappiness

The `vm.swappiness` parameter (range 0–200 on modern kernels, default 60) controls the kernel's tendency to swap anonymous memory pages to disk vs reclaiming page cache.

| Swappiness Value | Behavior | Use Case |
|---|---|---|
| 0 | Swap only under extreme OOM pressure; can cause surprising reclaim patterns | Not recommended for production |
| **1** | Almost never swap; keep everything in RAM | **Pure LLM inference** (avoid swapping model weights) |
| **10** | Swap only under severe memory pressure | **Database servers, app servers, ML training** |
| 20 | Moderate: prefer RAM but allow some swapping | General web application servers |
| 60 | Default balance | General desktop |
| 100 | Aggressive swapping | Never for servers |

**Sources**: [Linux Kernel docs — sysctl/vm](https://docs.kernel.org/admin-guide/sysctl/vm.html), [Oneuptime Swappiness Guide (2026)](https://oneuptime.com/blog/post/2026-03-02-how-to-understand-and-configure-swappiness-on-ubuntu/view), [LLM Kernel Optimization Guide (2026)](https://ai.islinux.com/articles/how-to-optimize-linux-kernel-llm-inference.html)

**Recommendation for Guinevere (Python + LLM + Docker)**: **swappiness=10**

**Rationale**:
- Python processes (FastAPI, Celery, monitoring agents) benefit from staying in RAM — swapping them causes latency spikes.
- LLM inference (if any) is extremely sensitive to swap — model weights must stay in physical memory.
- Docker containers on this shared host will share the swap pool; aggressive swapping (60) would cause all containers to slow down under pressure.
- A value of 10 provides a safety buffer for temporary spikes while keeping hot process memory in RAM.
- Setting it to 0 is **not recommended**: the kernel may exhibit "unpleasant reclaim patterns under pressure" ([cr0x.net](https://cr0x.net/en/ubuntu-swap-on-ssd-safely/)).

### 2.2 vfs_cache_pressure

Controls how aggressively the kernel reclaims memory used for caching filesystem directory and inode objects.

| Value | Behavior |
|---|---|
| 0 | Never reclaim dentry/inode cache (dangerous — can cause OOM) |
| **50** | Retain filesystem caches longer — good for workloads with many files |
| 100 | Default: fair rate of reclaim |
| 200+ | Aggressive reclaim; frees RAM but may slow file operations |

**Source**: [Linux Kernel docs — vfs_cache_pressure](https://docs.kernel.org/admin-guide/sysctl/vm.html)

**Recommendation**: **vfs_cache_pressure=50**

**Rationale**: Guinevere's workloads include Python agents, Docker containers with volume mounts, and file-heavy operations (logging, memory artifacts). Retaining inode/dentry cache reduces file lookup latency.

### 2.3 Application Procedure

```bash
# Apply immediately (takes effect now, lost on reboot)
sudo sysctl vm.swappiness=10
sudo sysctl vm.vfs_cache_pressure=50

# Verify
cat /proc/sys/vm/swappiness
# Expected: 10

cat /proc/sys/vm/vfs_cache_pressure
# Expected: 50

# Persist across reboots
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-guinevere-memory.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-guinevere-memory.conf

# Reload sysctl to confirm
sudo sysctl --system
```

**Source**: [DevOpsil Ubuntu 24.04 Production Setup (2026)](https://devopsil.com/articles/2026-04-02-ubuntu-24-04-server-production-setup), [Binadit Memory Optimization Guide (2026)](https://binadit.com/tutorials/configure-linux-memory-management-and-swap-optimization-for-high-performance-workloads)

---

## 3. Shared VPS Swap Considerations — Docker + cgroup Interaction

### 3.1 The Core Problem

On a shared VPS running Docker containers, swap introduces a critical interaction:

- **Without swap**: When a container hits its `--memory` limit, the kernel invokes the cgroup OOM killer inside the container. The container dies cleanly.
- **With swap (but no per-container swap limits)**: A container with `--memory=1g` can use up to **2GB total** (1GB RAM + 1GB swap by default) if `--memory-swap` is unset. Meaning: the container can swap 1GB of its pages to disk BEFORE hitting its memory limit. This masks memory oversubscription.
- **With unlimited swap**: A container with `--memory=1g` and `--memory-swap=-1` can swap until the host's swap file is full, causing a **host-wide swap storm**.

**Source**: [Docker Resource Constraints Docs](https://docs.docker.com/engine/containers/resource_constraints/), [cr0x.net Docker Swap Storms (2025)](https://cr0x.net/en/docker-swap-storms-host-melts/), [Kernel cgroup swap accounting](https://kernel-internals.org/mm/memcg-swap/)

### 3.2 cgroup v2 Swap Mechanics (Ubuntu 24.04)

Ubuntu 24.04 uses cgroup v2 (unified hierarchy). Key points:

| cgroup v2 Knob | Meaning |
|---|---|
| `memory.max` | Hard RAM limit for the cgroup |
| `memory.swap.max` | Hard swap-only limit (independent from memory.max) |
| `memory.high` | Soft throttle threshold — reclaim starts BEFORE hitting max |
| `memory.swap.high` | Soft swap throttle — reclaim swap BEFORE hitting swap.max |

When `memory.swap.max = 0`, the cgroup **cannot swap at all** — anonymous pages that would be swapped out trigger OOM directly. This is the behavior Docker achieves with `--memory=1g --memory-swap=1g`.

### 3.3 Docker Swap Flag Semantics

Docker's `--memory-swap` flag uses **combined (RAM+swap) semantics**, not swap-only:

| Docker Flags | cgroup v2 Equivalent | Container Behavior |
|---|---|---|
| `--memory=1g` (swap unset) | `memory.max=1G`, `memory.swap.max=1G` | Container can use 1G RAM + 1G swap = **2G total** |
| `--memory=1g --memory-swap=1g` | `memory.max=1G`, `memory.swap.max=0` | **No swap** — container cannot swap |
| `--memory=1g --memory-swap=2g` | `memory.max=1G`, `memory.swap.max=1G` | 1G RAM + 1G swap |
| `--memory=1g --memory-swap=-1` | `memory.max=1G`, `memory.swap.max=unlimited` | **Unlimited swap** — dangerous |

**Critical insight**: When `--memory-swap` is NOT set, the default is **twice** the memory limit. A container with `--memory=4g` can use **8GB total** (4 RAM + 4 swap) — completely saturating your 4GB swap file.

**Source**: [Docker Docs — memory-swap details](https://docs.docker.com/engine/containers/resource_constraints/), [Netdata Docker Memory Limits Guide](https://www.netdata.cloud/guides/docker/docker-memory-limits/)

### 3.4 Recommendation for Shared VPS with Aizanta

**Do these BEFORE creating swap:**

1. **Set explicit memory limits on ALL production containers** — no unlimited (`mem=0`) containers.
2. **Set `--memory-swap` equal to `--memory` for latency-sensitive containers** to prevent swap usage:
   ```
   docker run -d --memory=2g --memory-swap=2g aizanta-api
   ```
3. **Allow limited swap for batch/background containers** if needed:
   ```
   docker run -d --memory=512m --memory-swap=1g aizanta-worker
   ```
4. **Reserve host memory headroom** — Aizanta's containers should not sum to >12GB of the 16GB available (leaving 4GB for OS, page cache, monitoring, and swap overhead).

### 3.5 Monitoring Recommendations

```bash
# Check per-cgroup memory pressure (cgroup v2)
cat /sys/fs/cgroup/system.slice/docker-*/memory.current
cat /sys/fs/cgroup/system.slice/docker-*/memory.swap.current

# Watch for swap storms
vmstat 1 | grep -v '^procs'
# Watch 'si' (swap-in) and 'so' (swap-out) columns
# Consistently non-zero = thrashing = upgrade RAM

# Check PSI (Pressure Stall Information)
cat /proc/pressure/memory
# 'some avg10' and 'full avg10' should stay near 0
```

**Source**: [cr0x.net Docker Swap Storms (2025)](https://cr0x.net/en/docker-swap-storms-host-melts/), [Netdata Docker Memory Guide](https://www.netdata.cloud/guides/docker/docker-memory-limits/)

---

## 4. Swap Verification Commands

### 4.1 Pre-Creation Check

```bash
# Current swap state
swapon --show          # List active swap devices (should be empty)
free -h                # Check RAM and swap usage
cat /proc/swaps        # Kernel's swap table
sysctl vm.swappiness   # Check current swappiness value
```

### 4.2 Post-Creation Verification

```bash
# Verify swap file is active
swapon --show
# Expected: /swapfile  file  4G  0B  -2

# Verify total swap visible
free -h
# Expected: Swap:  total 4.0G  used 0B  free 4.0G

# Verify kernel parameter persistence
cat /proc/sys/vm/swappiness
# Expected: 10

cat /proc/sys/vm/vfs_cache_pressure
# Expected: 50

# Verify fstab entry
grep swap /etc/fstab
# Expected: /swapfile none swap sw 0 0

# Verify sysctl config file exists
cat /etc/sysctl.d/99-guinevere-memory.conf
```

### 4.3 Reboot Persistence Test

```bash
# After reboot, verify swap auto-mounts
swapon --show     # Should show /swapfile
free -h           # Should show 4GB swap
```

---

## 5. Rollback Procedure

### 5.1 Safe Swap Removal Sequence

```bash
# Step 1: Check current swap usage
free -h
# Ensure 'used' swap is low (or RAM has enough headroom to absorb it)

# Step 2: Check what's using swap (if any)
for pid in /proc/*/status; do
    [ -r "$pid" ] && awk '/^(Name|VmSwap):/ {printf "%s ", $2} END {print ""}' "$pid"
done | awk '$2>0'

# Step 3: Disable the swap file
sudo swapoff /swapfile
# This moves all swapped pages back to RAM
# WARNING: This may take time if swap is heavily used
# WARNING: May fail if RAM+swap usage exceeds available RAM

# Step 4: Verify swap is deactivated
swapon --show
# Expected: no output

free -h
# Expected: Swap:  total 0B  used 0B  free 0B

# Step 5: Remove from fstab
sudo sed -i '/^\/swapfile/d' /etc/fstab
# Or manually edit: sudo nano /etc/fstab — remove the /swapfile line

sudo systemctl daemon-reload  # systemd requires this after fstab changes

# Step 6: Delete the swap file
sudo rm /swapfile

# Step 7: Final verification
df -h /      # Confirm 4GB freed
free -h      # Confirm no swap
swapon --show  # Confirm no active swap
```

### 5.2 Rollback Failure Scenarios

| Symptom | Cause | Fix |
|---|---|---|
| `swapoff: cannot allocate memory` | Not enough free RAM to absorb swapped pages | Temporarily increase swappiness to 100 to force swap-in, try again, or reboot before removing |
| `swapoff: Invalid argument` | Swap file already disabled or corrupted | Check `swapon --show`, force with `swapoff -a` |
| Process using swap won't release | Long-running process with swapped anonymous pages | Stop the process first, then swapoff |

**Source**: [Rackspace Remove Swap File Guide](https://docs.rackspace.com/docs/create-remove-swap-file-in-ubuntu), [Red Hat Clear Swap Guide](https://www.redhat.com/en/blog/clear-swap-linux)

---

## 6. Known Issues and Gotchas

### 6.1 fallocate "swapfile has holes" — History and Resolution

| Kernel Version | Status | Details |
|---|---|---|
| < 5.6 | ✅ Working | fallocate swap files on ext4 worked |
| 5.6–5.7 | ❌ Broken | Commit `30460e1ea3e6` enabled hole detection; fallocate files on ext4 rejected by swapon |
| 5.8.0 before .25 | ❌ Broken | Same issue; `dmesg` shows "swapon: swapfile has holes" |
| 5.8.0-25.26+ | ✅ Fixed | Commit `424de74af0d0` added `ext4: implement swap_activate aops using iomap` |
| 6.8.x (Ubuntu 24.04) | ✅ Fixed | No known issues — fallocate works correctly on ext4 |

**Trigger conditions**: Only affected ext4 with `fallocate` (not `dd`). XFS was fixed earlier (Linux 4.18). Btrfs still requires special handling (disable CoW with `chattr +C`).

**Sources**: [Launchpad Bug #1894910](https://bugs.launchpad.net/bugs/1894910), [Kernel Bugzilla #207585](https://bugzilla.kernel.org/show_bug.cgi?id=207585), [Red Hat KB #4570081](https://access.redhat.com/solutions/4570081)

### 6.2 Docker + Swap OOM Behavior

**Problem**: Docker containers with memory limits but unconstrained swap can push the host into swap storms. Symptoms:
- Host `si`/`so` columns in `vmstat` are consistently non-zero
- High I/O wait (`wa` in `top`)
- Docker daemon becomes unresponsive
- `dmesg` shows host-level OOM events despite containers being within their RAM limits

**Root cause**: The container's `memory.max` is respected for RAM, but without `memory.swap.max`, the container can swap its anonymous pages to the host's swap file. Multiple containers doing this simultaneously exhaust swap and cause global memory pressure.

**Fix**: Set per-container swap limits via `--memory-swap`, or disable swap for latency-sensitive containers by setting `--memory-swap` equal to `--memory`.

**Source**: [cr0x.net Docker Swap Storms (2025)](https://cr0x.net/en/docker-swap-storms-host-melts/), [cr0x.net Docker OOM Limits (2026)](https://cr0x.net/en/docker-oom-memory-limits/)

### 6.3 cgroup v2 Swap Accounting Gap

On cgroup v2 (Ubuntu 24.04 default), if `memory.swap.max` is not set, swap usage is **unlimited** for that cgroup. A container with `--memory=1g` and no `--memory-swap` flag can potentially use all 4GB of your swap file, causing other containers to fail.

**Verification**: Check swap usage per cgroup:
```bash
find /sys/fs/cgroup/system.slice -name "memory.swap.current" -exec sh -c 'echo "{}: $(cat {})"' \;
```

### 6.4 Shared VPS: I/O Contention from Swap

On a shared VPS, swap I/O can impact not just your containers but **co-hosted tenants** (if the VPS uses shared storage). Swap writes are random I/O — the worst case for shared SSD storage.

**Mitigations**:
- Keep swappiness low (10) to minimize swap usage
- Monitor swap activity: if `si`/`so` are non-zero, reduce workload or increase RAM
- Consider `zram` (in-RAM compressed swap) as a first line, with disk swap as the second line

### 6.5 Btrfs/ZFS — Not Applicable Here

This VPS uses ext4, so Btrfs/ZFS swap file issues do not apply. For reference: Btrfs requires `chattr +C` (disable CoW) before creating a swap file; ZFS requires a dedicated ZVOL, not a swap file.

**Source**: [swapon(8) manpage](https://manpages.ubuntu.com/manpages/noble/man8/swapon.8.html)

---

## 7. Reference URLs

### 7.1 Official Ubuntu Documentation

| Resource | URL |
|---|---|
| Ubuntu Community SwapFaq | https://help.ubuntu.com/community/SwapFaq/ |
| swapon(8) manpage — Noble | https://manpages.ubuntu.com/manpages/noble/man8/swapon.8.html |
| mkswap(8) manpage — Noble | https://manpages.ubuntu.com/manpages/noble/man8/mkswap.8.html |
| fstab(5) manpage — Noble | https://manpages.ubuntu.com/manpages/noble/man5/fstab.5.html |
| proc_sys_vm(5) manpage — Noble | https://manpages.ubuntu.com/manpages/noble/man5/proc_sys_vm.5.html |

### 7.2 Kernel Documentation

| Resource | URL |
|---|---|
| Linux Kernel — sysctl/vm (swappiness, vfs_cache_pressure) | https://docs.kernel.org/admin-guide/sysctl/vm.html |
| cgroup v2 Memory Controller | https://www.kernel.org/doc/html/latest/admin-guide/cgroup-v2.html#memory |
| cgroup Swap Accounting | https://kernel-internals.org/mm/memcg-swap/ |

### 7.3 Docker Documentation

| Resource | URL |
|---|---|
| Docker Resource Constraints (memory, swap, swappiness) | https://docs.docker.com/engine/containers/resource_constraints/ |

### 7.4 Third-Party Guides (2025–2026)

| Resource | URL |
|---|---|
| MassiveGRID — Ubuntu VPS Swap & Memory Management (2025) | https://www.massivegrid.com/blog/ubuntu-vps-swap-memory-management/ |
| cr0x.net — Ubuntu 24.04 Swap on SSD Safely (2026) | https://cr0x.net/en/ubuntu-swap-on-ssd-safely/ |
| cr0x.net — Docker Swap Storms (2025) | https://cr0x.net/en/docker-swap-storms-host-melts/ |
| cr0x.net — Docker OOM Memory Limits (2026) | https://cr0x.net/en/docker-oom-memory-limits/ |
| DevOpsil — Ubuntu 24.04 Production Setup (2026) | https://devopsil.com/articles/2026-04-02-ubuntu-24-04-server-production-setup |
| Oneuptime — Swappiness Configuration (2026) | https://oneuptime.com/blog/post/2026-03-02-how-to-understand-and-configure-swappiness-on-ubuntu/view |
| Oneuptime — Swap Files on Ubuntu (2026) | https://oneuptime.com/blog/post/2026-03-02-how-to-create-and-manage-swap-files-on-ubuntu/view |
| AI.isLinux — LLM Kernel Optimization (2026) | https://ai.islinux.com/articles/how-to-optimize-linux-kernel-llm-inference.html |
| DEV Community — Zero-Latency LLM Kernel Tuning (2026) | https://dev.to/lyraalishaikh/zero-latency-local-ai-tuning-your-linux-kernel-for-llm-inference-5ch |
| Linux Hardened — Swap Management Deep Dive (2026) | https://www.linuxhardened.com/linux-swap-management-deep-dive/ |
| Binadit — Memory & Swap Optimization (2026) | https://binadit.com/tutorials/configure-linux-memory-management-and-swap-optimization-for-high-performance-workloads |
| TecAdmin — Add Swap in Ubuntu 24.04 (2024) | https://tecadmin.net/how-to-add-swap-in-ubuntu-24-04/ |
| Vultr Docs — Swap Memory in Ubuntu 24.04 (2024) | https://www.vultr.community/vultr-docs/how-to-add-swap-memory-in-ubuntu-24-04 |
| Rackspace — Create and Remove Swap Files | https://docs.rackspace.com/docs/create-remove-swap-file-in-ubuntu |
| Red Hat — How to Clear Swap Memory | https://www.redhat.com/en/blog/clear-swap-linux |

### 7.5 Bug Trackers (Historical — FIXED)

| Resource | URL |
|---|---|
| Launchpad Bug #1894910 — fallocate swapfile has holes on 5.8 ext4 | https://bugs.launchpad.net/bugs/1894910 |
| Kernel Bugzilla #207585 — Swap file has holes since 5.7 | https://bugzilla.kernel.org/show_bug.cgi?id=207585 |
| Red Hat KB — swapon failed: Invalid argument (fallocate) | https://access.redhat.com/solutions/4570081 |

---

## 8. Executive Summary — Recommended Configuration

### Target State

| Parameter | Current | Target | Rationale |
|---|---|---|---|
| Swap file | None (0B) | `/swapfile`, 4GB | Safety buffer for Docker/LLM spikes |
| vm.swappiness | 60 | **10** | Prefer RAM, swap only under pressure |
| vm.vfs_cache_pressure | 100 | **50** | Retain inode/dentry cache for file-heavy workloads |
| Aizanta container limits | Unknown | All with explicit `--memory` + `--memory-swap` | Prevent swap storms |
| Swap file permissions | N/A | **0600** (root-only) | Security: swap contains sensitive memory pages |

### One-Shot Implementation Commands

```bash
# 1. Create swap
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab

# 2. Tune kernel
sudo sysctl vm.swappiness=10
sudo sysctl vm.vfs_cache_pressure=50
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-guinevere-memory.conf
echo 'vm.vfs_cache_pressure=50' | sudo tee -a /etc/sysctl.d/99-guinevere-memory.conf

# 3. Verify
swapon --show
free -h
sysctl vm.swappiness vm.vfs_cache_pressure
```

### Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| fallocate creates holes on ext4 | **Near zero** — fixed in 5.8.0-25.26, 6.8.x has fix | High — swap won't activate | Verify with `dmesg` after swapon; fall back to `dd` if needed |
| Docker containers exhaust swap | **Medium** — depends on container limits | High — host-wide swap storm | Set explicit `--memory-swap` limits on all containers |
| Swap I/O contention on shared storage | **Low** — with swappiness=10, swap rarely used | Medium — affects Aizanta performance | Monitor `si`/`so` in `vmstat`; upgrade RAM if consistently non-zero |
| 4GB insufficient for workload | **Low** — normal usage fits 16GB RAM | Medium — OOM kills during spikes | Plan upgrade path: `swapoff`, resize with `fallocate`, `mkswap`, `swapon` |
| swapoff fails during rollback | **Low** — only if swap heavily used | Low — requires reboot | Ensure RAM has headroom before swapoff |

---

*Report generated 2026-05-31 by Guinevere (Librarian agent). All findings sourced from official Ubuntu/kernel documentation, recent community guides (2025–2026), and historical bug trackers (post-resolution). No remote commands executed.*