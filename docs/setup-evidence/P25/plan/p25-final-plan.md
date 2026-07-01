# P25 9Router VPS Migration — Final Plan

> **Status**: PLAN — Awaiting Review  
> **Date**: 2026-06-26  
> **VPS**: HostData.id NAT 4GB, Ubuntu 24.04, 49.12.82.34:39999

---

## 1. What Gets Installed

| # | Component | Why |
|---|---|---|
| 1 | SSH key | No password, Tailscale-only access |
| 2 | Node.js 24.x | Required by 9Router v0.5.4 |
| 3 | Tailscale | `tailscale up` — already installed |
| 4 | 9Router v0.5.4 | Fresh install from npm |
| 5 | UFW | Deny all, allow Tailscale only |
| 6 | sqlite3, zstd, curl, wget, git | Dependencies |
| 7 | S3 backup (awscli) | Daily backup to IDCLOUDHOST |

## 2. What Gets SKIPPED

| Component | Reason |
|---|---|
| Prometheus + Grafana | User said no |
| Memory leak restart timer | User said no |
| usageHistory pruning | User said no |
| Heap limit | Maximize — no NINEROUTER_NODE_HEAP_MB limit |

## 3. Execution Order

### Step 1: SSH Key
- Copy `~/.ssh/id_ed25519.pub` to VPS `~/.ssh/authorized_keys`
- Test: `ssh ninerouter-vps` (no password)

### Step 2: Node.js 24.x
- NodeSource setup_24.x
- Verify: `node -v`

### Step 3: Tailscale
- `tailscale up --hostname=ninerouter-vps`
- Get auth key from Windows: `tailscale status`
- Verify: `tailscale ping ninerouter-vps`

### Step 4: 9Router v0.5.4
- `npm install -g 9router@0.5.4`
- Verify: `9router --version`

### Step 5: Live DB Sync
- On Windows: `sqlite3 data.sqlite ".backup"` 
- SCP backup to VPS via Tailscale
- Copy secrets: jwt-secret, machine-id
- Verify: `PRAGMA integrity_check`

### Step 6: systemd Service
- `ninerouter.service` at `/etc/systemd/system/`
- Bind 0.0.0.0:20128, no heap limit
- Enable + start

### Step 7: UFW
- Deny incoming, allow outgoing
- Allow Tailscale interface only
- Enable

### Step 8: S3 Backup
- Create `/root/9router/backup.sh`
- zstd compress, aws s3 cp to is3.cloudhost.id
- Daily cron

### Step 9: Stress Test
- k6 on VPS, push to breaking point
- Record max throughput

### Step 10: Client Switch
- Update OPENAI_BASE_URL to Tailscale IP
- Test: chat completion works

### Step 11: Stop Local 9Router
- Disable Windows service
- Keep installed for rollback

## 4. Rollback

Revert OPENAI_BASE_URL to localhost:20128. Time: <10 seconds.

## 5. User Decisions Reference

| Decision | Value |
|---|---|
| Prometheus | No |
| Grafana | No |
| Memory leak restart | No |
| usageHistory pruning | No |
| Heap limit | None (maximize) |
| Stress test | Yes |
| S3 backup | Yes |
| Local 9Router | Stop, keep installed |
| UFW | Tailscale only |
| SSH | Key auth, no password |