# Research: Guinevere VPS Scripts & Tools

| Field | Value |
|-------|-------|
| **Research Agent** | Explore |
| **Date** | 2026-05-31 |
| **Sources** | scripts/, tmp/, systemd units |
| **Verdict** | preflight-check.sh (467 lines) is the P1 gate |

---

## Core Production Scripts (scripts/)

| Script | Lines | Purpose | P1 Relevance |
|--------|-------|---------|-------------|
| `preflight-check.sh` | 467 | Pre-flight verification of ALL services | **MUST run before P1** |
| `guinevere-backup.sh` | 615 | Dual-repo restic backup (daily cron) | Not needed for P1 |
| `setup-restic.sh` | 143 | SOPS encryption guide (documentation) | Not needed for P1 |

## Systemd Units

- `guinevere-backup@.service` — Daily backup oneshot (root, hardened)
- `guinevere-backup@.timer` — Daily 02:00 WIB
- `guinevere-backup-weekly@.timer` — Sunday 04:00 WIB
- `guinevere-prune-weekly@.service` / `.timer` — Sunday 05:00 WIB

## Pre-flight Check Coverage (preflight-check.sh)

Checks: PostgreSQL 5433, PgBouncer 5434, Redis 6380, Caddy 8443/3443/9443, fail2ban, CrowdSec, UFW, Tailscale, Cloudflare Tunnel, SOPS encryption, disk/memory/load, Aizanta Docker containers (≥5), backup readiness. Exit 0 = all pass. Flags: `--verbose`, `--json`.

## Key VPS Connection

- **SSH**: `guinevere@100.94.104.22` (Tailscale required)
- **Local alias**: `guinevere-vps` in `~/.ssh/config`
- **Code path**: `/home/guinevere/code/guinevere/`

## Open P0 Items (from VPS Deployment Checklist)

| ID | Item | Status |
|----|------|--------|
| B1 | Encrypt + shred 3 plaintext secrets in secrets/backup/ | OPEN |
| B3-C | Docker group membership (sudo usermod -aG docker guinevere) | OPEN |
| B5#1 | Caddy file symlink | OPEN |
| B5#2 | Disable Caddy admin API port 2019 | OPEN |
| B5#3 | Verify Prometheus binding | OPEN |

## Not Found

- No Makefile, Justfile, Taskfile
- No Dockerfile or docker-compose.yml for Guinevere itself
- No environment templates

| Field | Value |
|-------|-------|
| **Source** | bg_74fc1c71 — VPS state scripts |
| **File** | research-reports/P1/vps-scripts-tools.md |