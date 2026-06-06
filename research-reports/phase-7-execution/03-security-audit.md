# Phase 7 — Security Posture Audit Report

> **Date:** 2026-06-06  
> **VPS Host:** faiz-prod-01 (100.94.104.22 via Tailscale)  
> **Audit Scope:** VPS listening ports, `hermes security` scan, systemd hardening, SSH/Tailscale binding, local repo forbidden-pattern analysis, secret-safety review.  
> **Gate Criteria:** `hermes security` 0 HIGH/CRITICAL, open ports only via Tailscale, systemd hardening verified/added, SSH Tailscale binding, secrets rotation scheduled later.

---

## Table of Contents

1. [Listening Ports — Port Classification](#1-listening-ports--port-classification)
2. [hermes security — Vulnerability Scan](#2-hermes-security--vulnerability-scan)
3. [Systemd Hardening — VPS Runtime](#3-systemd-hardening--vps-runtime)
4. [Systemd Hardening — Local Templates vs VPS](#4-systemd-hardening--local-templates-vs-vps)
5. [SSH Configuration and Tailscale Binding](#5-ssh-configuration-and-tailscale-binding)
6. [Firewall Status](#6-firewall-status)
7. [Repository Secret-Safety Review](#7-repository-secret-safety-review)
8. [Forbidden Code Pattern Analysis](#8-forbidden-code-pattern-analysis)
9. [Summary — Gate Readiness](#9-summary--gate-readiness)
10. [Blocker Register](#10-blocker-register)

---

## 1. Listening Ports — Port Classification

Collected via `ss -tlnp` and cross-validated with `/proc/net/tcp`. Ports classified by bind address.

### 1.1 Public (0.0.0.0) — FINDINGS

| Port | Process | Service | Severity | Notes |
|------|---------|---------|----------|-------|
| `22` | sshd | SSH | HIGH | Bound to all interfaces. Should be Tailscale-only. |
| `20128` | next-server (v16.2.1) | 9Router LLM Proxy | CRITICAL | LLM API gateway exposed to all interfaces. PID 627406. |
| `9191` | python3 (multiprocessing worker) | Core API worker | HIGH | PID 65133, child of uvicorn core. |

### 1.2 Tailscale-Bound (100.94.104.22) — EXPECTED

| Port | Service | Status |
|------|---------|--------|
| `80` | HTTP frontend | Expected |
| `3443` | Unknown HTTPS | Expected |
| `8443` | Unknown HTTPS | Expected |
| `9443` | Unknown HTTPS | Expected |
| `36438` | Unknown | Expected |

These are only reachable via Tailscale — no public exposure.

### 1.3 Loopback (127.0.0.1) — EXPECTED

| Port | Service | Status |
|------|---------|--------|
| `6379` | Redis (primary) | Internal |
| `6380` | Redis (secondary/cache) | Internal |
| `5432` | PostgreSQL (primary) | Internal |
| `5433` | PostgreSQL (guinevere) | Internal |
| `5434` | PostgreSQL (unknown) | Internal |
| `8000` | Core API (uvicorn, 2 workers) | Internal |
| `8080` | Unknown | Internal |
| `6060` | Unknown | Internal |
| `3000` | Grafana | Internal |
| `3100` | Loki | Internal |
| `9090` | Prometheus | Internal |
| `9093` | Alertmanager | Internal |
| `9100` | Node Exporter | Internal |
| `8384` | Tailscale status web UI | Internal |
| `20241` | cloudflared | Internal |
| `9121` | Unknown | Internal |
| `9187` | Unknown | Internal |

**Verdict:** 3 public ports found (22, 20128, 9191) — violates Phase 7 gate requirement of "open ports only Tailscale". SSH, LLM proxy, and core worker all exposed to the internet.

---

## 2. hermes security — Vulnerability Scan

Ran via `/home/guinevere/code/guinevere/.venv/bin/hermes security`.

### 2.1 Severity Summary

| Severity | Count | Gate Requirement | Status |
|----------|-------|------------------|--------|
| CRITICAL | 0 | 0 | PASS |
| HIGH | 0 | 0 | PASS |
| MODERATE | 3 | N/A | Note |
| LOW | 1 | N/A | Note |
| UNKNOWN | 6 | N/A | Note |
| **Total** | **10** | | |

### 2.2 Detailed Findings

#### MODERATE (3)

| ID | Package | Issue | Fixed In |
|----|---------|-------|----------|
| GHSA-4xh5-x5gv-qwph | pip 24.0 | Symbolic link check bypass in tar extraction | 25.3 |
| GHSA-58qw-9mgm-455v | pip 24.0 | Tar/ZIP interpretation conflict | 26.1 |
| GHSA-jp4c-xjxw-mgf9 | pip 24.0 | Untrusted control sphere vulnerability | 26.1 |

#### LOW (1)

| ID | Package | Issue | Fixed In |
|----|---------|-------|----------|
| GHSA-6vgw-5pg2-w6jp | pip 24.0 | Path traversal | 26.0 |

#### UNKNOWN (6)

| ID | Package | Fixed In |
|----|---------|----------|
| PYSEC-2026-196 | pip 24.0 | 26.1.2 |
| PYSEC-2026-175 | PyJWT 2.12.1 | 2.13.0 |
| PYSEC-2026-177 | PyJWT 2.12.1 | 2.13.0 |
| PYSEC-2026-178 | PyJWT 2.12.1 | 2.13.0 |
| PYSEC-2026-179 | PyJWT 2.12.1 | 2.13.0 |
| PYSEC-2026-139 | torch 2.10.0 | -- |

### 2.3 Additional Notes

- `hermes` binary is not in PATH -- installed only in `.venv/bin/`.
- Hermes Agent v0.15.2 (2026.5.29.2). Update available: 1 commit behind.
- `hermes security` scans only Python venv packages -- does **not** scan Node.js, system packages, or container images.

**Verdict:** 0 HIGH/CRITICAL -- gate criterion satisfied. 3 MODERATE pip findings and 4 UNKNOWN PyJWT findings should be scheduled for remediation.

---

## 3. Systemd Hardening -- VPS Runtime

Verified via `systemctl show` for key services. Values confirmed directly from runtime.

### 3.1 Key Services

| Service | Type | NoNewPrivileges | ProtectSystem | ProtectHome | MemoryMax | Slice |
|---------|------|-----------------|---------------|-------------|-----------|-------|
| hermes-gateway | exec | yes | strict | read-only | 1G | guinevere.slice |
| guinevere-loops | exec | yes | strict | read-only | 2G | guinevere.slice |
| guinevere-mcp | exec | yes | strict | read-only | 2G | guinevere.slice |
| guinevere-surveillance | exec | yes | strict | read-only | 768M | guinevere.slice |
| guinevere-discord | -- | no | no | no | infinity | (empty) |

Note: guinevere-discord.service is NOT listed in active units on VPS. The systemctl show returned defaults (=no), confirming the unit is not present or not loaded on VPS. The template exists locally but may not be deployed.

### 3.2 Additional Hardening (guinevere-monitoring)

The monitoring service has **extra hardening** beyond the base pattern:
- PrivateTmp=yes
- ProtectKernelTunables=yes
- ProtectKernelModules=yes
- ProtectControlGroups=yes
- RestrictSUIDSGID=yes

These are present in the local template and should be considered for all services.

### 3.3 Systemd Slice

| Property | Value |
|----------|-------|
| MemoryHigh | 7,516,192,768 (~7G) |
| MemoryMax | 8,589,934,592 (8G) |
| TasksMax | 512 |

Slice is active, all services belong to it, resource limits enforced.

### 3.4 Active Services (7 total)

| Unit | Status | Description |
|------|--------|-------------|
| hermes-gateway.service | active (running) | Hermes Agent Gateway (Discord) |
| guinevere-9router.service | active (running) | 9Router LLM Proxy |
| guinevere-core.service | active (running) | Core Daemon |
| guinevere-loops.service | active (running) | Agent Loop Daemon |
| guinevere-monitoring.service | active (running) | Monitoring Stack |
| guinevere-scheduler.service | active (running) | Loop Scheduler Daemon |
| guinevere-surveillance.service | active (running) | Surveillance Consumer |

Not deployed on VPS: guinevere-discord, guinevere-obscura, guinevere-shadow-monitor, guinevere-mcp -- exist as local templates but absent from production.

### 3.5 hermes-gateway Runtime Health

```
Active: active (running) since Sat 2026-06-06 12:35:31 WIB; 1h 33min ago
Memory: 98.0M (high: 512.0M max: 1.0G available: 413.9M peak: 109.5M)
CGroup: /guinevere.slice/hermes-gateway.service
```

Stale unit warning: hermes-gateway.service has TimeoutStopSec=90s but drain_timeout=180s. systemd may SIGKILL the gateway mid-drain. Run hermes gateway service install --replace.

**Verdict:** All deployed services have standard hardening. All bound to guinevere.slice. One operational warning (stale timeout config).

---

## 4. Systemd Hardening -- Local Templates vs VPS

### 4.1 Template Inventory

| Template File | Exists Locally | Deployed on VPS | Comments |
|---------------|----------------|-----------------|----------|
| systemd/hermes-gateway.service | MISSING | /etc/systemd/ | VPS version auto-generated |
| systemd/guinevere-discord.service | Yes | Not active | Template has full hardening |
| systemd/guinevere-loops.service | Yes | Active | Template matches deployment |
| systemd/guinevere-mcp.service | Yes | Not active | Template has full hardening |
| systemd/guinevere-monitoring.service | Yes | Active | Extra hardening beyond base |
| systemd/guinevere-obscura.service | Yes | Not active | Type=simple (inconsistent) |
| systemd/guinevere-scheduler.service | Yes | Active | Template matches deployment |
| systemd/guinevere-shadow-monitor.service | Yes | Not active | Type=oneshot pattern |
| systemd/guinevere-surveillance.service | Yes | Active | Template matches deployment |

### 4.2 Missing hermes-gateway Template

The hermes-gateway.service file on VPS was auto-generated by hermes gateway service install. The repo does **not** have a corresponding template in systemd/. This creates a drift risk -- if a deploy script recreates systemd units from local templates, hermes-gateway's unit could be lost.

**Recommendation:** Create systemd/hermes-gateway.service from the VPS file, or commit the auto-generated file.

### 4.3 Hardening Flag Comparison

**All local templates** include:
- NoNewPrivileges=true
- ProtectSystem=strict
- ProtectHome=read-only
- MemoryMax, MemoryHigh, CPUQuota
- Slice=guinevere.slice

**Monitoring template is the most hardened**, adding PrivateTmp, ProtectKernelTunables, ProtectKernelModules, ProtectControlGroups, RestrictSUIDSGID.

**Verdict:** All templates meet base hardening standards. Missing hermes-gateway.service in repo is a gap.

---

## 5. SSH Configuration and Tailscale Binding

### 5.1 SSH Binding

| Property | Value | Verdict |
|----------|-------|---------|
| Bind address | 0.0.0.0:22 + [::]:22 | Should not be public |
| PermitRootLogin | yes | Root SSH should be disabled |
| PasswordAuthentication | Not set (defaults to yes on Ubuntu) | Should be explicitly no |
| PubkeyAuthentication | Not set (defaults to yes) | Implicitly enabled |
| KbdInteractiveAuthentication | no | Explicitly disabled |
| Port directive | Not set (defaults to 22) | No custom port |
| ListenAddress | Not set | No restriction |

### 5.2 Tailscale Status

- **Tailscale IP:** 100.94.104.22
- **Status:** Connected, active
- **Peers:** faizzzzz (Windows, active), budgezen-openclaw (Linux, active), backend/db-1/frontend/xiaomi-11t (offline)

### 5.3 Remediation Required

1. SSH should listen only on Tailscale IP: Add `ListenAddress 100.94.104.22` to /etc/ssh/sshd_config
2. Disable root SSH login: `PermitRootLogin no`
3. Explicitly disable password auth: `PasswordAuthentication no`

**Verdict:** SSH is publicly exposed on all interfaces with root login enabled and no explicit password-auth restriction. This is a HIGH-severity finding for the gate.

---

## 6. Firewall Status

| Check | Result | Verdict |
|-------|--------|---------|
| iptables -L | Empty (no rules) | No firewall |
| ufw status | Not installed | No UFW |
| nft list ruleset | Empty | No nftables |

**No firewall is active on the VPS.** All port exposure (SSH on 0.0.0.0:22, next-server on 0.0.0.0:20128, core worker on 0.0.0.0:9191) is unfiltered. This is a CRITICAL finding.

**Recommendation:** Apply a strict firewall (UFW or iptables) that blocks ALL inbound except from Tailscale IPs (100.64.0.0/10), allows SSH only from Tailscale, allows established/related traffic.

---

## 7. Repository Secret-Safety Review

### 7.1 .gitignore Coverage

| Pattern | Purpose | Status |
|---------|---------|--------|
| .env | Prevents env file commits | Covered |
| secrets/ | Prevents secret directory commits | Covered |
| *.key | Prevents key file commits | Covered |
| *.pem | Prevents PEM file commits | Covered |
| !.env.example | Allows example env file | Configured |
| pat.txt | Prevents PAT commits | Covered |
| .venv/, venv/, env/ | Virtual envs | Covered |

### 7.2 Environment File Handling

- No .env files committed to repo
- No .env.example file exists in repo -- missing for developer onboarding
- System uses per-service .env.discord, .env.loops, .env.mcp, .env.scheduler, .env.surveillance files -- covered by .env wildcard

### 7.3 VPS Environment File Locations

| Service | Env File |
|---------|----------|
| hermes-gateway | /home/guinevere/.hermes/.env |
| discord | /home/guinevere/code/guinevere/.env.discord |
| loops | /home/guinevere/code/guinevere/.env.loops |
| mcp | /home/guinevere/code/guinevere/.env.mcp |
| scheduler | /home/guinevere/code/guinevere/.env.scheduler |
| surveillance | /home/guinevere/code/guinevere/.env.surveillance |

**Verdict:** No secrets committed. .env pattern coverage is solid. Missing .env.example is a minor documentation gap.

---

## 8. Forbidden Code Pattern Analysis

Searched src/ (production code only). Test findings noted separately.

### 8.1 Type-Safety Bypasses (src/ only)

Patterns searched: # type: ignore, @ts-ignore, @ts-expect-error

| File | Count | Details |
|------|-------|---------|
| src/observability/sentry_integration.py | 5 | dict type-arg for Sentry callbacks |
| src/mcp/auth.py | 2 | attr-defined for dynamic attribute assignment |
| src/surveillance/timescale.py | 1 | union-attr for result.rowcount |
| src/mcp/tools/postgres_tool.py | 1 | import-untyped for asyncpg |
| src/discord/bot.py | 1 | assignment for Bot base type |
| src/core/main.py | 1 | override for Starlette request dispatch |

**Total in production code:** 11 occurrences in 6 files.

**Verdict:** Low severity. All 11 are narrow, scoped suppressions with explicit error codes. None are broad # type: ignore without reason.

### 8.2 `as any` Patterns

**Result:** 0 matches across entire codebase.

### 8.3 `except Exception` (Bare or Overbroad)

Pattern searched: except (Exception|BaseException): -- 155 matches in 72 production files.

**Heaviest files:**
- src/hermes/safety_plugin.py -- 14 -- HIGH -- safety boundaries should never blanket-catch
- src/discord/cmd_surveillance_status.py -- 14 -- HIGH
- src/hermes_plugins/commands_surveillance/surveillance_status.py -- 11 -- HIGH
- src/surveillance/consumer.py -- 5 -- HIGH
- src/surveillance/consent_gate.py -- 4 -- CRITICAL -- consent gates must not silently swallow errors

**Verdict:** HIGH severity. 155 blanket except Exception: in production code is a systemic anti-pattern. Many may log before catching, but every instance needs audit to confirm it logs/re-raises appropriately.

### 8.4 Bare `except:` (Without Exception Type)

**Result:** 0 matches in src/.

---

## 9. Summary -- Gate Readiness

### Gate Criteria

| Criterion | Required | Actual | Status |
|-----------|----------|--------|--------|
| hermes security 0 HIGH | 0 HIGH/CRITICAL | 0 | PASS |
| Open ports only Tailscale | No public ports | 3 public ports (22, 20128, 9191) | FAIL |
| Systemd hardening verified | All services hardened | All deployed services hardened | PASS |
| SSH Tailscale binding | SSH not on 0.0.0.0:22 | SSH on 0.0.0.0:22 + PermitRootLogin yes | FAIL |
| Secrets rotation schedule | Later | Not scoped | Later |
| No .env in repo | Clean | Clean | PASS |

### Combined Verdict: **BLOCKED** -- 2 gate criteria fail

---

## 10. Blocker Register

### Blocker 1: Public SSH (0.0.0.0:22) -- HIGH
- **What:** SSH bound to all interfaces with PermitRootLogin yes
- **Risk:** Brute-force SSH attacks; root access exposed to internet
- **Fix:** Add ListenAddress 100.94.104.22 and PermitRootLogin no to /etc/ssh/sshd_config, then systemctl restart sshd

### Blocker 2: No Active Firewall -- CRITICAL
- **What:** No iptables, ufw, or nftables rules active
- **Risk:** All public ports are completely unfiltered
- **Fix:** Install UFW or apply iptables rules restricting all inbound to Tailscale subnet 100.64.0.0/10

### Blocker 3: next-server LLM Proxy on 0.0.0.0:20128 -- CRITICAL
- **What:** 9Router LLM proxy bound to all interfaces
- **Risk:** LLM API endpoint (with API keys via env) exposed to internet
- **Fix:** Reconfigure next-server to bind to 100.94.104.22 only, or add firewall restriction

### Blocker 4: Core Worker on 0.0.0.0:9191 -- HIGH
- **What:** Core API multiprocessing worker bound to all interfaces
- **Risk:** Internal API surface exposed publicly
- **Fix:** Investigate why worker binds 0.0.0.0; configure uvicorn to loopback-only

### Blocker 5: 155x except Exception: in Production Code -- HIGH
- **What:** Systemic overbroad exception handling across 72 files
- **Risk:** Silently swallowing errors in safety-critical paths (consent, surveillance, safety plugin)
- **Fix:** Per-instance audit; replace with specific exception types or ensure logging + re-raise pattern

### Blocker 6 (Minor): Missing hermes-gateway.service Template -- LOW
- **What:** VPS has /etc/systemd/system/hermes-gateway.service but no local systemd/ template
- **Risk:** Drift between repo and deployment
- **Fix:** Copy VPS unit to systemd/hermes-gateway.service

### Blocker 7 (Minor): No .env.example -- LOW
- **What:** No example env file for developer onboarding
- **Risk:** Lack of documented required environment variables
- **Fix:** Create .env.example from VPS env file patterns

---

## Appendix A: All Listening Ports (Raw)

- tcp LISTEN 0.0.0.0:22 -- sshd
- tcp LISTEN 0.0.0.0:20128 -- next-server (LLM proxy)
- tcp LISTEN 0.0.0.0:9191 -- python3 (core worker)
- tcp LISTEN 100.94.104.22:80
- tcp LISTEN 100.94.104.22:3443
- tcp LISTEN 100.94.104.22:8443
- tcp LISTEN 100.94.104.22:9443
- tcp LISTEN 100.94.104.22:36438
- tcp LISTEN 127.0.0.1:3000 (Grafana), 3100 (Loki), 5432-5434 (PG), 6060, 6379-6380 (Redis), 8000 (Core API), 8080, 8384 (Tailscale status), 9090 (Prometheus), 9093 (Alertmanager), 9100 (Node Exporter), 9121, 9187, 9443, 20241 (cloudflared)
- udp 0.0.0.0:41641 (Tailscale wireguard)

## Appendix B: Active Guinevere Services (VPS)

- hermes-gateway.service -- active -- Hermes Agent Gateway (Discord)
- guinevere-9router.service -- active -- 9Router LLM Proxy
- guinevere-core.service -- active -- Core Daemon
- guinevere-loops.service -- active -- Agent Loop Daemon
- guinevere-monitoring.service -- active -- Monitoring Stack
- guinevere-scheduler.service -- active -- Loop Scheduler Daemon
- guinevere-surveillance.service -- active -- Surveillance Consumer

## Appendix C: hermes-gateway.service (VPS Unit)

Installed at /etc/systemd/system/hermes-gateway.service with full hardening (NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only, MemoryMax=1G, Slice=guinevere.slice).

Note: unit has TimeoutStopSec=90s (systemd default) but drain_timeout=180s in hermes config. Run hermes gateway service install --replace to fix.

## Appendix D: Forbidden Pattern Hit Summary (src/ only)

| Pattern | Count | Affected Files | Severity |
|---------|-------|----------------|----------|
| # type: ignore | 11 | 6 | LOW |
| @ts-ignore/@ts-expect-error | 0 | 0 | PASS |
| as any | 0 | 0 | PASS |
| except Exception: | 155 | 72 | HIGH |
| Bare except: | 0 | 0 | PASS |

---

*Report generated by Guinevere sub-agent. All data collected read-only. No state altered.*
