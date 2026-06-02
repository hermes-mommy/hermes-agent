# External Research Report: cgroup v2 + systemd Slice Best Practices for Ubuntu 24.04

**Purpose**: Authoritative guidance for STEP-P0-009 — implementing `guinevere.slice` with resource limits on a shared VPS (16GB RAM, 4 cores, Ubuntu 24.04, systemd 255.x, kernel 6.8.x).

**Date**: 2026-05-31
**Source Task**: STEP-P0-009
**Researcher**: Guinevere (THE LIBRARIAN agent)

---

## Table of Contents

1. [cgroup v2 Status on Ubuntu 24.04](#1-cgroup-v2-status-on-ubuntu-2404)
2. [systemd Slice Architecture](#2-systemd-slice-architecture)
3. [Key Resource Control Directives](#3-key-resource-control-directives)
4. [Proposed `guinevere.slice` Validation](#4-proposed-guinevereslice-validation)
5. [Shared VPS: Aizanta Service Coexistence](#5-shared-vps-aizanta-service-coexistence)
6. [Docker + cgroup v2 Integration](#6-docker--cgroup-v2-integration)
7. [Verification Commands](#7-verification-commands)
8. [Common Pitfalls](#8-common-pitfalls)
9. [Safety Recommendations](#9-safety-recommendations)
10. [Rollback & Recovery](#10-rollback--recovery)
11. [References](#11-references)

---

## 1. cgroup v2 Status on Ubuntu 24.04

### 1.1 Default Mode

**Ubuntu 24.04 defaults to cgroup v2 (unified hierarchy).** This is confirmed by multiple sources:

- Ubuntu 22.04+ ships cgroup v2 as default.
- The containerd book confirms: "Examples were checked on Ubuntu 24.04 with kernel 6.8 and systemd 255 in cgroup v2 unified mode."
- Kernel 6.8.x (shipped with Ubuntu 24.04) enforces cgroup v2 strictly, including tighter `memory.high`/`memory.max` accounting compared to 5.x kernels.

### 1.2 Verification Commands

Run these on the VPS to confirm cgroup v2 mode:

```bash
# Method 1: Check filesystem type (MUST return "cgroup2fs")
stat -fc %T /sys/fs/cgroup/
# Output: cgroup2fs

# Method 2: Check mount
mount | grep cgroup2
# Output: cgroup2 on /sys/fs/cgroup type cgroup2 (rw,nosuid,nodev,noexec,relatime)

# Method 3: Confirm systemd hierarchy
systemd-analyze --version | grep hierarchy
# Output should include: default-hierarchy=unified

# Method 4: List available controllers
cat /sys/fs/cgroup/cgroup.controllers
# Expected: cpuset cpu io memory hugetlb pids rdma misc
```

### 1.3 If NOT cgroup v2

If you see multiple `cgroup` mounts (v1/hybrid mode), force unified:

```bash
# /etc/default/grub
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash systemd.unified_cgroup_hierarchy=1 cgroup_no_v1=all"
# Then: sudo update-grub && sudo reboot
```

**Do not do this on a running production VPS without a maintenance window** — it requires a full reboot.

---

## 2. systemd Slice Architecture

### 2.1 The Hierarchy

Slices form the inner nodes of the cgroup tree. They do NOT hold processes directly — they hold child slices, services, and scopes. The default hierarchy:

```
-.slice (root)
├── init.scope (PID 1)
├── system.slice (all system services)
│   ├── nginx.service
│   ├── docker.service
│   └── containerd.service
├── user.slice (all user sessions)
│   ├── user-1000.slice
│   └── user@1000.service
└── machine.slice (VMs/containers via systemd-machined)
```

### 2.2 Nesting via Dash Convention

Slices nest using dash-separated naming. A slice named `guinevere-worker.slice` is automatically a child of `guinevere.slice`. No explicit `Slice=` directive needed for parent-child nesting.

```text
-.slice
└── guinevere.slice               ← MemoryMax=8G
    ├── guinevere-worker.slice     ← inherits parent constraints
    └── guinevere-api.service      ← Slice=guinevere.slice
```

**Key reference**: From `systemd.slice(5)` — "Slices are organized hierarchically in a tree. The name of the slice unit encodes the location in the tree. The name consists of a dash-separated series of names, which describes the path to the slice from the root slice."

### 2.3 Implicit Dependencies

When a service unit has `Slice=guinevere.slice`, systemd automatically adds:
- `Requires=guinevere.slice`
- `After=guinevere.slice`

This means `guinevere.slice` must exist before the service can start.

### 2.4 Purely Declarative — No Immediate Impact

> **CRITICAL**: Creating a systemd slice unit file (`/etc/systemd/system/guinevere.slice`) has **zero immediate impact** on running processes. The limits in the slice unit only apply to services that explicitly opt into the slice via `Slice=guinevere.slice`.

**Evidence**: systemd only creates the cgroup node and applies `cgroup.subtree_control` when a service or scope is placed in the slice. Merely defining the slice file does not move any PID into it.

**What happens after `systemctl daemon-reload`:**
1. The slice unit is known to systemd but **not active**.
2. The cgroup directory `/sys/fs/cgroup/guinevere.slice/` does NOT exist yet.
3. `systemctl status guinevere.slice` will show it as inactive (dead).
4. On first `systemctl start guinevere-*.service` with `Slice=guinevere.slice`, the slice activates and its limits take effect.

---

## 3. Key Resource Control Directives

### 3.1 MemoryMax (Hard Limit)

**Directive**: `MemoryMax=8G`
**cgroup v2 file**: `memory.max`
**Behavior**:
- Absolute hard limit. If memory usage exceeds this and cannot be reclaimed, the **OOM killer** is invoked inside the cgroup.
- The kernel makes 16 reclaim attempts before invoking OOM.
- **The child cannot exceed the parent's limit even if the child sets a higher value.** The effective limit is the minimum across the ancestor chain.
- Per the official man page: "It is recommended to use `MemoryHigh=` as the main control mechanism and use `MemoryMax=` as the last line of defense."

### 3.2 MemoryHigh (Soft/Throttling Limit)

**Directive**: `MemoryHigh=7G`
**cgroup v2 file**: `memory.high`
**Behavior**:
- When memory usage exceeds this limit, processes are **throttled and put under heavy reclaim pressure**.
- **Going over `memory.high` NEVER invokes the OOM killer.**
- Usage may temporarily breach the high limit under extreme conditions.
- Default value is `max` (disabled).
- This is the recommended primary control mechanism — MemoryMax is the safety net.

**The golden rule**: `MemoryHigh` (7G) < `MemoryMax` (8G). This creates a 1GB buffer where throttling kicks in before OOM, giving operators time to investigate before processes get killed.

### 3.3 CPUQuota (Per-Core!)

**Directive**: `CPUQuota=200%`
**cgroup v2 file**: `cpu.max` (format: `$QUOTA $PERIOD`)
**Behavior**:
- **Percentage is relative to ONE CPU.** NOT total system CPU.
- `CPUQuota=200%` on a 4-core system = processes can use up to 2 full CPU cores.
- Under the hood: `cpu.max = "200000 100000"` (200ms quota per 100ms period = 2 CPUs).
- This is NOT a soft weight — it's a hard bandwidth cap. Even if the other 2 cores are idle, the slice gets throttled to 2 cores max.
- **Hierarchical**: A child's effective quota is the minimum of its own quota and the parent's quota. If parent sets `CPUQuota=100%`, child cannot exceed 100% even with `CPUQuota=200%`.

**Correction for your proposed config**: `CPUQuota=200%` on a 4-core VPS means the Guinevere slice can use up to 2 of 4 cores. The remaining 2 cores are available for Aizanta. If Guinevere is expected to sometimes need all 4 cores, set `CPUQuota=400%` or leave it unset and rely on `CPUWeight=` for fair scheduling.

### 3.4 IOWeight (Relative Priority)

**Directive**: `IOWeight=50`
**cgroup v2 file**: `io.weight`
**Behavior**:
- Range: `1` to `10000`. Default: `100`.
- This is a **weight** (relative share), NOT an absolute limit. When there's I/O contention between sibling cgroups, they split bandwidth proportional to their weights.
- `IOWeight=50` means the Guinevere slice gets **half** the I/O share of a default-weight sibling when under contention.
- When there's NO contention, IOWeight has no effect — the slice can use all available I/O.
- **Important**: `io.weight` only works with the `io.cost` (CONFIG_BLK_CGROUP_IOCOST) or `bfq` I/O scheduler. Verify with: `cat /sys/block/sda/queue/scheduler`.

### 3.5 TasksMax (Fork Bomb Protection)

**Directive**: `TasksMax=512`
**cgroup v2 file**: `pids.max`
**Behavior**:
- Limits total threads/processes in the cgroup and all its descendants.
- Upstream systemd default is 15% of `kernel.pid_max` per service unit.
- Ubuntu 24.04 may ship with `DefaultTasksMax=infinity` (common for server distros).
- If Docker containers run under this slice, 512 may be too low — each container creates multiple threads. **Recommendation**: Monitor Docker container thread counts before locking this in. A single `node` process can create dozens of threads; docker-compose stacks with 5+ containers can easily exceed 512.

**Warning sign**: `Failed to fork (Resources temporarily unavailable)` or `Can't create thread to handle new connection` in logs = TasksMax too low.

### 3.6 Directives Not in Current Config (Consider Adding)

| Directive | Recommended Value | Why |
|-----------|-------------------|-----|
| `MemorySwapMax=2G` | Optional | Prevents swap from inflating beyond 2G (kernel 6.8 enforces this strictly) |
| `CPUWeight=100` | Default anyway | Explicit for documentation |
| `OOMPolicy=stop` | Stop (not kill) | Prevents cascading kills if used with `MemoryMax` |

---

## 4. Proposed `guinevere.slice` Validation

### 4.1 Your Current Proposal

```ini
# /etc/systemd/system/guinevere.slice
[Unit]
Description=Guinevere AI Companion Resource Slice
Before=slices.target

[Slice]
MemoryMax=8G
MemoryHigh=7G
CPUQuota=200%
IOWeight=50
TasksMax=512
```

### 4.2 Analysis Against Official Docs

| Directive | Value | Verdict | Notes |
|-----------|-------|---------|-------|
| `MemoryMax=8G` | 8 GB (of 16 GB) | ✅ Reasonable | 50% of total RAM; leaves 8GB for Aizanta + system |
| `MemoryHigh=7G` | 7 GB | ✅ Good buffer | 1GB between throttle and OOM; within range |
| `CPUQuota=200%` | 2 of 4 cores | ⚠️ Check intent | Is Guinevere expected to use up to 4 cores? If yes, this is restrictive |
| `IOWeight=50` | Half of default | ✅ Reasonable | Gerakan disk tidak prioritas tinggi; Aizanta gets more I/O under contention |
| `TasksMax=512` | 512 tasks | ⚠️ Check Docker | If Guinevere runs many Docker containers, 512 may be insufficient |

### 4.3 Missing: Slice Activation

The slice definition alone is inert. Guinevere services must opt in:

```ini
# In any Guinevere service unit:
[Service]
Slice=guinevere.slice
```

Or for transient units:
```bash
systemd-run --scope --slice=guinevere.slice -- my-command
```

### 4.4 Cgroup Files Created

After a service joins the slice, these files appear:

```bash
# Expected cgroup path
/sys/fs/cgroup/guinevere.slice/

# Core control files
memory.max          # = 8589934592 (8GiB)
memory.high         # = 7516192768 (7GiB)
cpu.max             # = "200000 100000" (200% of 1 CPU)
io.weight           # = 50
pids.max            # = 512

# Accounting files (read-only)
memory.current      # Current memory usage
cpu.stat            # CPU usage stats
io.stat             # I/O usage stats
pids.current        # Current task count

# Tree control
cgroup.procs        # PIDs in this cgroup
cgroup.controllers  # Enabled controllers
cgroup.subtree_control  # Controllers delegated to children
```

---

## 5. Shared VPS: Aizanta Service Coexistence

### 5.1 Hierarchical Enforcement

cgroup v2 enforces limits at EVERY level of the hierarchy. The kernel walks up the ancestor chain on every memory charge:

```
Charge path (simplified, from mm/memcontrol.c):
  try_charge():
    1. Check memory.max at leaf cgroup → reclaim/OOM if hit
    2. Check memory.max at parent cgroup → reclaim/OOM if hit
    3. Continue up to root
```

**Implication**: If Aizanta runs in `system.slice` (default) and Guinevere runs in `guinevere.slice`, they are **sibling slices**. Memory/Max CPUQuota on `guinevere.slice` does NOT affect Aizanta's `system.slice` — they compete independently based on their remaining headroom under the root slice.

### 5.2 What Happens When Resources Are Tight

- **If Guinevere hits its `MemoryMax=8G`**: Only processes in `guinevere.slice` and its descendants get OOM-killed. Aizanta services in `system.slice` are **unaffected**.
- **If Guinevere hits its `CPUQuota=200%`**: Guinevere's processes get throttled. Aizanta can still use the other 2 cores.
- **If the VPS runs out of physical RAM (16GB total)**: The global OOM killer may kill any process regardless of slice. This is a VPS-level constraint, not a cgroup constraint.

### 5.3 Checking Aizanta Resources

To verify Aizanta has enough headroom AFTER Guinevere slice is active:

```bash
# Total memory used by Aizanta (system.slice)
cat /sys/fs/cgroup/system.slice/memory.current
# Compare against: 16GB - 8GB(Guinevere) = 8GB available for Aizanta + system

# Check Aizanta's current OOM events
grep -r oom /sys/fs/cgroup/system.slice/*/memory.events 2>/dev/null

# Monitor overall VPS pressure
cat /proc/pressure/memory
```

### 5.4 Docker Containers Under systemd

If Aizanta uses Docker with the **systemd cgroup driver** (recommended on Ubuntu 24.04), Docker containers appear under `system.slice/docker-<id>.scope` or under a custom `docker.slice`. They are children of `system.slice`, NOT `guinevere.slice`, so they inherit `system.slice` limits — not Guinevere's.

**To verify Docker's cgroup placement**:
```bash
# Check Docker cgroup driver
docker info | grep -i cgroup
# Expected: Cgroup Driver: systemd, Cgroup Version: 2

# See Docker's cgroup path
systemctl show docker.service | grep ControlGroup
# Usually: /system.slice/docker.service
```

---

## 6. Docker + cgroup v2 Integration

### 6.1 Systemd Cgroup Driver (Required for v2)

Docker MUST use the `systemd` cgroup driver on Ubuntu 24.04 with cgroup v2:

```json
// /etc/docker/daemon.json
{
  "exec-opts": ["native.cgroupdriver=systemd"],
  "cgroup-parent": "docker.slice"  // optional
}
```

Without this, Docker uses `cgroupfs` driver, which conflicts with systemd's single-writer ownership of the cgroup tree, causing "permission denied" or "no such file or directory" errors on v2.

### 6.2 Delegate=yes

Docker's systemd service must have `Delegate=yes` so Docker can create per-container cgroups underneath:

```bash
# Verify
systemctl show docker.service --property=Delegate
# Must be: Delegate=yes
```

This is typically set automatically when Docker is installed via apt on Ubuntu 24.04.

### 6.3 Docker Containers Under Guinevere Slice

If Guinevere runs Docker containers and you want them under `guinevere.slice`:

```yaml
# docker-compose.yml for Guinevere services
services:
  guinevere-worker:
    cgroup_parent: guinevere.slice
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
```

Or via `docker run`:
```bash
docker run --cgroup-parent=guinevere.slice --memory=2g --cpus=1 my-image
```

### 6.4 Kernel 6.8 Strictness

Kernel 6.8 (Ubuntu 24.04 default) changed cgroup v2 memory enforcement compared to 5.x:
- Limits that were "loosely enforced" on 5.x are **strictly enforced** on 6.x.
- If Docker Compose files omit memory limits, containers inherit the parent slice limit.
- **Explicit swap accounting**: If `MemorySwapMax` is not set, containers may be OOM-killed even when swap is available. This is a common post-upgrade surprise.

**Fix**: Either set `MemorySwapMax=` in the slice or override Docker's service memory limit to `infinity`:

```bash
# /etc/systemd/system/docker.service.d/memory-override.conf
[Service]
MemoryMax=infinity
MemoryHigh=infinity
```

---

## 7. Verification Commands

### 7.1 Pre-Implementation Checks

```bash
# 1. Confirm cgroup v2
stat -fc %T /sys/fs/cgroup/         # must be cgroup2fs
cat /sys/fs/cgroup/cgroup.controllers  # must include cpu, memory, io, pids

# 2. Confirm systemd hierarchy
systemd-analyze --version | grep "default-hierarchy"
# Should show "unified"

# 3. Check current state — no guinevere.slice should exist
ls /sys/fs/cgroup/guinevere.slice/ 2>/dev/null && echo "EXISTS!" || echo "OK - does not exist"
systemctl is-active guinevere.slice 2>/dev/null || echo "OK - not active"

# 4. Current VPS resource overview
free -h               # total RAM/swap
nproc                 # CPU core count
cat /proc/sys/kernel/pid_max   # max PIDs (for TasksMax percentage context)
```

### 7.2 Post-Implementation Checks (after daemon-reload + service start)

```bash
# After systemctl daemon-reload && systemctl start <guinevere-service>:

# 1. Slice is active
systemctl is-active guinevere.slice

# 2. Cgroup directory exists
ls -la /sys/fs/cgroup/guinevere.slice/

# 3. Limits are written correctly
cat /sys/fs/cgroup/guinevere.slice/memory.max
# Expected: 8589934592

cat /sys/fs/cgroup/guinevere.slice/memory.high
# Expected: 7516192768

cat /sys/fs/cgroup/guinevere.slice/cpu.max
# Expected: 200000 100000

cat /sys/fs/cgroup/guinevere.slice/io.weight
# Expected: default 50

cat /sys/fs/cgroup/guinevere.slice/pids.max
# Expected: 512

# 4. Verify with systemctl
systemctl show guinevere.slice --property=MemoryMax,MemoryHigh,CPUQuotaPerSecUSec,TasksMax,IOWeight
```

### 7.3 Ongoing Monitoring

```bash
# Real-time cgroup resource monitor
systemd-cgtop

# Filter to guinevere.slice only (if systemd-cgtop doesn't support filtering well)
watch -n 5 'cat /sys/fs/cgroup/guinevere.slice/memory.current | numfmt --to=iec'

# Check OOM events in the slice
cat /sys/fs/cgroup/guinevere.slice/memory.events

# Check task count vs limit
echo "Current: $(cat /sys/fs/cgroup/guinevere.slice/pids.current) / Max: $(cat /sys/fs/cgroup/guinevere.slice/pids.max)"

# View hierarchy
systemd-cgls /guinevere.slice
```

---

## 8. Common Pitfalls

### 8.1 CPUQuota = Per-Core, Not System-Wide

| Setting | On 4-core VPS | Meaning |
|---------|---------------|---------|
| `CPUQuota=25%` | 0.25 cores | 1/16th of total system capacity |
| `CPUQuota=100%` | 1 full core | 1/4 of total system capacity |
| `CPUQuota=200%` | 2 full cores | Half of system (your proposed config) |
| `CPUQuota=400%` | 4 full cores | Full system |

**Common mistake**: Thinking `CPUQuota=200%` means 200% of ALL CPUs (i.e., 8 cores on 4-core). It doesn't. It means 2.0 CPUs worth of bandwidth.

### 8.2 MemoryMax Kills Before MemoryHigh Throttles (Misconception)

The **correct** order is:
1. Memory usage exceeds `MemoryHigh` → throttling + aggressive reclaim (NO kills)
2. If throttling/reclaim can't keep up, memory usage exceeds `MemoryMax` → OOM killer invoked

`MemoryMax` is the harder backstop. `MemoryHigh` gives the kernel room to throttle before resorting to kills.

**But**: There is NO notification when `MemoryHigh` is breached. You must monitor `memory.events` (the `high` counter) proactively. Without monitoring, `MemoryHigh` throttling may go unnoticed until `MemoryMax` OOM-kills.

### 8.3 TasksMax Too Low for Docker Workloads

A Docker container with a Node.js app + database + sidecar can easily consume 200-300 threads. Two such containers hit 512 quickly. Docker itself uses threads for container management.

**Symptoms** of TasksMax too low:
- `Resource temporarily unavailable` in application logs
- Docker containers fail to start with fork errors
- `can't create thread to handle new connection` from web servers

**Recommendation**: If Guinevere runs Docker under this slice, start `TasksMax` at 1024–2048 and monitor `pids.current`.

### 8.4 Forgetting Slice= in Service Units

The slice definition alone does nothing. If services don't include `Slice=guinevere.slice`, they remain in `system.slice` and the Guinevere slice stays inactive.

### 8.5 Child Limit Larger Than Parent

This is ALLOWED in cgroup v2 (no error when writing), but the effective limit for the child is `min(child_limit, parent_limit)`. If `guinevere.slice` has `MemoryMax=8G` and a child service sets `MemoryMax=12G`, the child's effective max is 8G.

### 8.6 IOWeight Is Weight, Not Limit

`IOWeight=50` does NOT cap I/O. It only matters during I/O contention. If Aizanta is idle, Guinevere can use all disk bandwidth regardless of `IOWeight`. For hard I/O limits, use `IOReadBandwidthMax=` and `IOWriteBandwidthMax=`.

### 8.7 systemctl set-property Creates Drop-ins

```bash
systemctl set-property guinevere.slice MemoryMax=10G
```

This creates a drop-in file at `/etc/systemd/system/guinevere.slice.d/50-MemoryMax.conf`. If you also have `MemoryMax=8G` in the main `.slice` file, the drop-in overrides it (last-write-wins). Use `--runtime` for non-persistent changes:

```bash
systemctl set-property --runtime guinevere.slice MemoryMax=10G
```

---

## 9. Safety Recommendations

### 9.1 Implementation Order

```
1. Create /etc/systemd/system/guinevere.slice (unit file only)
2. systemctl daemon-reload                         # systemd reads the file
3. systemctl status guinevere.slice                # should show "inactive (dead)"
4. Verify NO cgroup directory at /sys/fs/cgroup/guinevere.slice/
5. Verify Aizanta services are healthy
6. Start ONE Guinevere service with Slice=guinevere.slice
7. Verify limits via /sys/fs/cgroup/guinevere.slice/
8. Monitor for 5-10 minutes before starting more services
```

### 9.2 Start Conservative, Tighten Later

| Directive | Start With | Tighten To | Rationale |
|-----------|-----------|------------|-----------|
| `MemoryMax` | `10G` | `8G` | Give 2GB headroom initially; tighten after monitoring |
| `MemoryHigh` | `8G` | `7G` | More generous throttle threshold at first |
| `CPUQuota` | `400%` | `200%` | Allow full 4 cores initially; restrict after baseline |
| `IOWeight` | `100` | `50` | Start at default weight; lower if needed |
| `TasksMax` | `2048` | `512` | Start high; reduce once thread count baseline is known |

### 9.3 Backout Procedure

```bash
# If things go wrong:
# 1. Move services back to system.slice (remove Slice= from service files)
# 2. systemctl daemon-reload
# 3. Restart affected services
# 4. Stop the slice (stops any remaining services in it)
systemctl stop guinevere.slice
# 5. The cgroup directory automatically cleans up when empty
```

### 9.4 Never Do These

- ❌ `Delegate=yes` on a slice unit (systemd rejects this; delegation only on services/scopes)
- ❌ Write directly to `/sys/fs/cgroup/` (violates single-writer rule; systemd owns the tree)
- ❌ `systemctl set-property system.slice MemoryMax=...` (affects ALL system services including Aizanta)
- ❌ Create Docker containers directly under `guinevere.slice` without understanding cgroup nesting implications

---

## 10. Rollback & Recovery

### 10.1 Clean Removal

```bash
# 1. Stop all services in the slice
systemctl stop guinevere.slice

# 2. Remove slice unit file
rm /etc/systemd/system/guinevere.slice
rm -rf /etc/systemd/system/guinevere.slice.d/

# 3. Reload systemd
systemctl daemon-reload

# 4. Verify cleanup
ls /sys/fs/cgroup/guinevere.slice/ 2>/dev/null && echo "STILL EXISTS - check for lingering processes" || echo "Cleaned"

# 5. If cgroup directory persists, check for processes still attached:
cat /sys/fs/cgroup/guinevere.slice/cgroup.procs 2>/dev/null
# Kill or move these processes, then the directory will auto-cleanup
```

### 10.2 Recovery from OOM Kill Spiral

If `MemoryMax=8G` is too low and Guinevere services keep getting OOM-killed:

```bash
# Immediate relief (runtime only, lost on reboot):
systemctl set-property --runtime guinevere.slice MemoryMax=12G

# Or temporarily disable the limit:
systemctl set-property --runtime guinevere.slice MemoryMax=infinity

# Then investigate what caused the spike
cat /sys/fs/cgroup/guinevere.slice/memory.events
journalctl -u guinevere-*.service --since "10 minutes ago" | grep -i oom
```

---

## 11. References

| Source | URL | Key Content |
|--------|-----|-------------|
| systemd.resource-control(5) | <https://www.man7.org/linux/man-pages/man5/systemd.resource-control.5.html> | All resource directives, controller enablement, examples |
| systemd.slice(5) | <https://www.freedesktop.org/software/systemd/man/latest/systemd.slice.html> | Slice hierarchy, dash-naming, ConcurrencyHardMax |
| cgroup v2 kernel docs | <https://docs.kernel.org/admin-guide/cgroup-v2.html> | memory.max, memory.high, cpu.max, io.weight, pids.max semantics |
| systemd CGROUP_DELEGATION | <https://github.com/systemd/systemd/blob/main/docs/CGROUP_DELEGATION.md> | Single-writer rule, Delegate= restrictions |
| runc systemd cgroup driver | <https://github.com/opencontainers/runc/blob/main/docs/systemd.md> | Runtime spec → systemd property mapping table |
| containerd cgroup v2 chapter | <https://thecontainerdbook.com/chapters/part-2/05-cgroups-v2> | Confirmed Ubuntu 24.04 + kernel 6.8 + systemd 255 |
| memcg hierarchy | <https://kernel-internals.org/mm/memcg-hierarchy/> | Hierarchical limit enforcement, effective max = min(ancestor chain) |
| CPU bandwidth control | <https://kernel-internals.org/sched/cpu-bandwidth/> | cpu.max quota/period; CPUQuota=200% = 200ms/100ms = 2 CPUs |
| cgroup hierarchy | <https://kernel-internals.org/cgroups/systemd-cgroups/> | systemd owns the tree; Delegate=yes for containerd/Docker |
| Docker cgroup v2 fix path | <https://cr0x.net/en/docker-cgroups-v2-fix-path/> | Systemd driver MUST be used on v2; Delegate=yes verification |
| Ubuntu 24.04 kernel 6.8 Docker breakage | <https://vipinpg.com/blog/debugging-linux-kernel-6x-cgroup-v2-memory-limits-breaking-legacy-docker-compose-stacks-after-ubuntu-2404-upgrade/> | Kernel 6.8 strictness; swap accounting, systemd overrides |
| Docker-Compose cgroup v2 | <https://unix.stackexchange.com/questions/789556/how-to-configure-cgroup-v2-limits-on-docker-compose-containers> | `cgroup_parent: docker.slice` in compose files |
| MemoryHigh vs MemoryMax | <https://serverfault.com/questions/1192733/actual-sequence-of-events-from-memory-pressure-to-oom-for-cgroups-v2> | 16 reclaim attempts before OOM; MemoryHigh never OOMs |

---

## Appendix A: Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│              guinevere.slice QUICK REFERENCE              │
├──────────────────┬──────────────────┬───────────────────┤
│ Directive        │ cgroup v2 file   │ Ops Command        │
├──────────────────┼──────────────────┼───────────────────┤
│ MemoryMax=8G     │ memory.max       │ cat …/memory.max   │
│ MemoryHigh=7G    │ memory.high      │ cat …/memory.high  │
│ CPUQuota=200%    │ cpu.max          │ cat …/cpu.max      │
│ IOWeight=50      │ io.weight        │ cat …/io.weight    │
│ TasksMax=512     │ pids.max         │ cat …/pids.max     │
├──────────────────┴──────────────────┴───────────────────┤
│ Verify:        systemctl show guinevere.slice -p MemoryMax
│ Monitor:       systemd-cgtop
│ Hierarchy:     systemd-cgls /guinevere.slice
│ OOM events:    cat …/guinevere.slice/memory.events
│ Emergency:     systemctl set-property --runtime \
│                  guinevere.slice MemoryMax=infinity
└─────────────────────────────────────────────────────────┘
```

---

*Report generated by THE LIBRARIAN agent for STEP-P0-009.*
*All claims backed by upstream documentation and Ubuntu 24.04-verified sources.*