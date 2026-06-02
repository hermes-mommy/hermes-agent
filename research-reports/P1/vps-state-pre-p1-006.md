# VPS State — Pre P1-006 (9Router Installation)
**Date**: 2026-06-01
**Host**: guinevere-vps (100.94.104.22 via Tailscale)
**User**: guinevere

---

## 1. Node.js Presence

| Check | Result |
|---|---|
| which node | 
ode: command not found |
| 
ode --version | Not found |
| dpkg -l | grep node | Not installed via apt |
| 
vm | Not installed (~/.nvm/ does not exist) |
| snap | Installed but no Node package |
| /usr/local/bin/ | No node binary |
| ~/bin/ | Empty |

**Verdict**: ❌ Node.js is NOT installed. Must be installed from scratch.

---

## 2. npm Presence

| Check | Result |
|---|---|
| which npm | 
pm: command not found |
| 
pm --version | Not found |
| 
pm ls -g --depth=0 | Not found |

**Verdict**: ❌ npm is NOT installed. Will be bundled with Node.js installation.

---

## 3. Port Availability

| Port | Service | Status |
|---|---|---|
| **20128** (9Router target) | Not in use | ✅ **FREE** |
| **3000** (common Node.js dev) | Not in use | ✅ **FREE** |

**Verdict**: ✅ Port 20128 is free and available for 9Router binding.

---

## 4. Existing Systemd Services

Command: ls /etc/systemd/system/guinevere-*

**Verdict**: No guinevere-* services exist. No existing pattern to follow — will need to create a new service file from scratch.

---

## 5. Disk Space

| Filesystem | Size | Used | Available | Use% |
|---|---|---|---|---|
| /dev/vda1 | 99G | 16G | **78G** | 17% |

**Verdict**: ✅ 78G free — ample disk space for Node.js, npm, 9Router, and future data.

---

## 6. Docker Containers (Aizanta Health)

| Container | Status | Health |
|---|---|---|
| guinevere-redis | Up 12 hours | — |
| guinevere-pgbouncer | Up 13 hours | — |
| guinevere-postgres | Up 15 hours | — |
| aizanta-bot | Up 8 days | **healthy** |
| aizanta-nginx | Up 8 days | **healthy** |
| aizanta-frontend | Up 8 days | **healthy** |
| aizanta-postgres | Up 8 days | **healthy** |
| aizanta-redis | Up 8 days | **healthy** |
| objective_buck | Up 8 days | — |
| elastic_beaver | Up 8 days | — |

**Verdict**: ✅ All Aizanta services healthy (8 days uptime). Guinevere infrastructure containers (redis, pgbouncer, postgres) all running. Two anonymous docker-compose containers (objective_buck, elastic_beaver) present but no indication of issues.

---

## 7. Memory

| Metric | Value |
|---|---|
| Total | 15 GiB |
| Used | 1.5 GiB |
| Free | 2.5 GiB |
| Buff/Cache | 11 GiB |
| Available | **13 GiB** |
| Swap Total | 4.0 GiB |
| Swap Used | 0 B |

**Verdict**: ✅ 13 GiB available memory — plenty for Node.js/9Router runtime.

---

## 8. Existing /usr/local/bin Binaries

| Binary | Details |
|---|---|
| cloudflared | Symlink → /usr/bin/cloudflared (May 31) |
| sops | 43 MB binary (May 24) |

**Verdict**: No Node/npm/9router binaries present. sops and cloudflared pre-existing are unrelated.

---

## 9. Available Package Managers / Tools

| Tool | Path |
|---|---|
| curl | /usr/bin/curl |
| wget | /usr/bin/wget |
| snap | /usr/bin/snap |

**Verdict**: ✅ curl and wget available for downloading Node.js binaries or using NodeSource/nvm scripts.

---

## Summary for P1-006

| Prerequisite | Status | Action Required |
|---|---|---|
| Node.js | ❌ Not installed | Install via nvm, NodeSource, or binary download |
| npm | ❌ Not installed | Comes with Node.js install |
| Port 20128 | ✅ Free | No action needed |
| Disk space | ✅ 78G free | No action needed |
| Memory | ✅ 13Gi available | No action needed |
| Systemd pattern | ❌ No existing service | Create new guinevere-9router.service |
| curl/wget | ✅ Available | Use for download |

**Recommended approach**: Install Node.js via NodeSource official binary distribution (or nvm) since curl and wget are available. Install LTS version (20.x or 22.x) to maximize compatibility. Port 20128 is free for 9Router binding.
