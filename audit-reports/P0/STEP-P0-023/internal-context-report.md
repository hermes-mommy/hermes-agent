# STEP-P0-023 — Internal Context Report

**Step:** P0-023 — Cloudflare Tunnel Setup
**Phase:** P0 (Infrastructure Foundation, step 23 of 29)
**Report Type:** Internal Context — pre-implementation audit and synthesis
**Date:** 2026-05-31
**Prepared for:** Implementation planning of cloudflared deployment, ingress rules, and verification

---

## 1. Exact Scope

### 1.1 From StepPrompts (P0-023, lines 2459–2560)

**Goal:** Create Cloudflare Tunnel for the single public-facing endpoint (Discord webhook receiver).

**Exact command list (in order):**

1. Download and install cloudflared via .deb from GitHub releases
2. cloudflared --version — verify installation
3. cloudflared tunnel login — browser-based auth flow with Cloudflare account
4. cloudflared tunnel create guinevere-webhook — create tunnel, note tunnel ID + credentials path
5. Create config directory: mkdir -p /home/guinevere/.cloudflared
6. Write config.yml with ingress: webhook.guinevere.internal -> http://localhost:8000/webhook/discord + 404 fallback
7. cloudflared tunnel route dns guinevere-webhook webhook.guinevere.internal
8. sudo cloudflared service install
9. sudo systemctl enable cloudflared + sudo systemctl start cloudflared
10. Verify: systemctl status cloudflared, cloudflared tunnel list, cloudflared tunnel info

**Verification assertions:**
- cloudflared --version shows version
- cloudflared tunnel list shows guinevere-webhook
- 
slookup webhook.guinevere.internal resolves
- systemctl status cloudflared shows active
- curl https://webhook.guinevere.internal/healthz returns 200

**Evidence path (from StepPrompts):** docs/setup-evidence/P0/STEP-P0-023/cloudflared-status.txt, docs/setup-evidence/P0/STEP-P0-023/tunnel-config.yml

**Rollback commands:**
`
sudo systemctl stop cloudflared
sudo cloudflared service uninstall
cloudflared tunnel delete guinevere-webhook
sudo apt purge -y cloudflared
`

---

## 2. Current Tracker State

### 2.1 PROGRESS.md (line 67)

`
- [ ] P0-022  Tailscale VPN mesh (zero public ports, per ADR-019)
- [ ] P0-023  Cloudflare Tunnel (Discord webhook only, per ADR-026)
`

- Both steps unchecked.
- P0 completed count: 22/29 (75.8%).
- P0-023 has explicit dependency annotation: "(Discord webhook only, per ADR-026)".

### 2.2 CHECKLIST.md (line 123)

`
- [ ] P0-023: cloudflared tunnel list -> only Discord webhook; tunnel info -> localhost:8000/discord/webhook only
`

- The verification assertion expects a SINGLE webhook at /discord/webhook.
- This is the security criteria the final tunnel must satisfy: only one endpoint exposed.

### 2.3 Audit-Reports Structure

- Directory udit-reports/P0/STEP-P0-023/ exists but was empty (now contains this report).
- Directory udit-reports/P0/STEP-P0-022/ exists but is empty (P0-022 not started).
- All prior steps P0-001 through P0-021 have populated report directories.

### 2.4 Setup-Evidence

- Directory docs/setup-evidence/P0/STEP-P0-022/ does NOT exist — no Tailscale evidence yet.
- P0-023 evidence path docs/setup-evidence/P0/STEP-P0-023/ also does NOT exist yet.

---

## 3. ADR Requirements

### 3.1 ADR-026 — Public Endpoint via Cloudflare Tunnel (Primary)

| Aspect | Requirement |
|--------|------------|
| Endpoint | Only Discord webhook endpoint exposed |
| Method | Cloudflare Tunnel (cloudflared) as systemd service on primary VPS |
| TLS | Cloudflare handles TLS termination — no manual cert management |
| Cost | Free tier sufficient for single webhook endpoint |
| Credentials | Store tunnel credentials via SOPS + age (ADR-015) |
| Auth | Application-layer webhook signature validation required |
| Monitoring | Tunnel health via Prometheus + Grafana (ADR-017) |
| Failover | If cloudflared stops, webhook delivery fails but NO other services affected |
| Attack surface | Only Discord webhook endpoint — no other ports or services |

**Key quote from ADR-026 (Review Notes):**
> "Scope: Only Discord webhook endpoint exposed. No other services (API, admin, monitoring) are publicly accessible."

### 3.2 ADR-019 — Zero Public Ports (Constraint)

| Aspect | Requirement |
|--------|------------|
| Baseline | Zero public ports on VPS. All admin surfaces Tailscale-internal only. |
| Exception | ADR-026 is the sole exception for the Discord webhook endpoint |
| Public integrations | Discord, GitHub, 9Router use outbound/external provider channels |
| Definition | "No public VPS ingress is permitted" — this ADR explicitly forbids any other public endpoint |

**Key quote from ADR-019 (Review Notes):**
> "Zero public ports: All VPS admin surfaces are Tailscale-internal only. Public integrations (Discord, GitHub) use outbound/external provider channels. No public VPS ingress is permitted."

---

## 4. Shared VPS Guardrails

### 4.1 Aizanta Coexistence

| Factor | Constraint |
|--------|-----------|
| nginx on port 80 | Aizanta likely uses port 80/443 for nginx. Cloudflare Tunnel does NOT bind locally to these ports. It connects outbound to Cloudflare edge. **No port conflict expected.** |
| User isolation | cloudflared typically runs as root (standard). Must not interfere with Aizanta processes. Could run as guinevere with proper config. |
| Resource impact | cloudflared uses minimal CPU/RAM (~50MB). No impact on Aizanta cgroup. |
| Firewall | UFW unchanged — cloudflared connects outbound only, no inbound rule needed. |
| Docker network | Not applicable — cloudflared is not a Docker container. |

### 4.2 General Shared VPS Rules

- Port conflicts: Check ss -tlnp before binding
- Resource limits: Under 50% CPU/RAM
- User isolation: All services as guinevere user (cloudflared may need root for service install)
- Aizanta check after step: systemctl status aizanta-* must show all running

---

## 5. Evidence Path Convention

Previous steps use structured evidence with multiple files:

| Path | Content | Status |
|------|---------|--------|
| docs/setup-evidence/P0/STEP-P0-023/cloudflared-status.txt | Verification output | Pending |
| docs/setup-evidence/P0/STEP-P0-023/tunnel-config.yml | Final active config | Pending |
| udit-reports/P0/STEP-P0-023/internal-context-report.md | This file | ✅ Written now |
| udit-reports/P0/STEP-P0-023/external-cloudflared-install-report.md | Install method research | Pending |
| udit-reports/P0/STEP-P0-023/external-headless-auth-report.md | Headless auth alternatives | Pending |
| udit-reports/P0/STEP-P0-023/step-p0-023-auditor-report.md | Post-implementation audit | Pending |

---

## 6. Identified Contradictions

### CONTRADICTION 1 (CRITICAL): Browser auth on headless VPS

- **StepPrompts (line 2492):** cloudflared tunnel login — opens browser for OAuth.
- **Problem:** Runs on headless VPS — no display, no browser.
- **Deployment Guide workaround (lines 1867-1869):** Run login on local machine, then SCP cert.pem to VPS.
- **Recommended:** Run cloudflared tunnel login on Faiz laptop, copy ~/.cloudflared/cert.pem to VPS via SCP. Documented in Deployment Guide section 4.1.

### CONTRADICTION 2 (CRITICAL): Deployment Guide exposes grafana endpoint

- **Deployment Guide (lines 1895-1896):**
  `
  ingress:
    - hostname: webhook.yourdomain.com
      path: /webhook/.*
      service: http://127.0.0.1:8000
    - hostname: grafana.yourdomain.com     # VIOLATES ADR-026
      service: http://127.0.0.1:3000        # VIOLATES ADR-026
    - service: http_status:404
  `
- **What ADR-026 requires:** "Only Discord webhook endpoint exposed. No other services."
- **What ADR-019 requires:** "No public VPS ingress is permitted."
- **Impact:** Exposing Grafana via Cloudflare Tunnel violates both ADRs.
- **Resolution:** Tunnel MUST have exactly ONE ingress rule. The Grafana entry MUST NOT be used.

### CONTRADICTION 3 (MEDIUM): Wrong hostname in StepPrompts

- **StepPrompts (line 2508):** hostname: webhook.guinevere.internal
- **Problem:** guinevere.internal is a Tailscale MagicDNS name, not a public domain. Cloudflare DNS cannot manage it.
- **Deployment Guide uses:** webhook.yourdomain.com (placeholder).
- **Resolution:** Replace with real domain managed on Cloudflare (e.g., webhook.guinevere.app).

### CONTRADICTION 4 (MEDIUM): Install method mismatch

- **StepPrompts:** Direct .deb download from GitHub releases.
- **Deployment Guide:** APT repo (pkg.cloudflare.com).
- **Resolution:** Use APT repo method — enables automatic updates via unattended-upgrades.

### CONTRADICTION 5 (LOW): Tunnel name mismatch

- **StepPrompts:** guinevere-webhook
- **Deployment Guide:** guinevere
- **Resolution:** Use guinevere-webhook for clarity.

### CONTRADICTION 6 (LOW): Config file location mismatch

- **StepPrompts:** /home/guinevere/.cloudflared/config.yml
- **Deployment Guide:** /etc/cloudflared/config.yml
- **Resolution:** Verify cloudflared service install default behavior. The systemd unit generated by cloudflared service install typically expects config in /etc/cloudflared/config.yml.

---

## 7. Deployment Guide Cross-Reference

### 7.1 Section 4.1 Cloudflare Tunnel (lines 1858-1915)

| Aspect | Deployment Guide | StepPrompts |
|--------|-----------------|-------------|
| Install method | APT repo (cloudflare-main.gpg) | Direct .deb download |
| Auth flow | Local machine -> SCP cert.pem | 	unnel login on VPS (broken) |
| Tunnel name | guinevere | guinevere-webhook |
| Ingress rules | webhook + grafana (ADR violation) | webhook.guinevere.internal (wrong domain) |
| Config file | /etc/cloudflared/config.yml | /home/guinevere/.cloudflared/config.yml |
| DNS route | webhook.yourdomain.com | webhook.guinevere.internal |
| Service install | cloudflared service install | sudo cloudflared service install |
| Verification | tunnel info, tunnel list | Same + curl + nslookup |

### 7.2 Architecture Implication (Deployment Guide diagram)

The Deployment Guide architecture diagram (section 1.1) shows:
`
CF[Cloudflare Tunnel] --> Caddy reverse proxy --> Services
`

But StepPrompts P0-023 configures cloudflared to proxy DIRECTLY to localhost:8000 — bypassing Caddy.

**Recommendation:** Follow StepPrompts for the direct proxy path. Cloudflare Tunnel already terminates TLS and handles origin request. Adding Caddy as an intermediary for the webhook endpoint is unnecessary complexity. Caddy can still be used for internal service routing (P0-024).

### 7.3 Other Deployment Guide References

| Line | Content |
|------|---------|
| 62 | Lists cloudflared as a managed service |
| 64 | "Tailscale mesh (zero public ports) + Cloudflare Tunnel (Discord webhook endpoint)" |
| 76 | "Cloudflare Tunnel for Discord webhook with full ingress rules as systemd service" |
| 176 | Service table: cloudflared, root user, network-online, Always restart |
| 191 | "Cloudflare Tunnel webhook.domain.com HTTPS (outbound) — Discord webhook only" |

---

## 8. Recommended Approach

### 8.1 Prerequisites (Must Complete First)

1. **P0-022 (Tailscale)** — hard dependency. StepPrompts line 2467: "Dependencies: P0-022 (Tailscale configured)". Must complete before Cloudflare Tunnel setup.
2. **Domain selection** — Faiz must decide which domain to use (e.g., webhook.guinevere.app or personal domain on Cloudflare).
3. **Cloudflare account** — must have domain added to Cloudflare DNS.
4. **Faiz laptop access** — needed for browser-based cloudflared tunnel login.

### 8.2 Execution Plan

| # | Action | Detail |
|---|--------|--------|
| 1 | Install cloudflared | APT repo method (auto-updates) |
| 2 | Authenticate | Run cloudflared tunnel login on Faiz laptop, SCP cert.pem to VPS |
| 3 | Create tunnel | cloudflared tunnel create guinevere-webhook |
| 4 | Write config | /etc/cloudflared/config.yml with ONE ingress rule |
| 5 | Route DNS | cloudflared tunnel route dns guinevere-webhook webhook.<domain> |
| 6 | Install service | cloudflared service install, enable, start |
| 7 | SOPS credentials | Encrypt credentials-file JSON via SOPS+age |
| 8 | Verify | tunnel connected, DNS resolves, healthz responds |

### 8.3 Ingress Rule (Only One Allowed)

`yaml
ingress:
  - hostname: webhook.<domain>
    path: /webhook/discord
    service: http://localhost:8000
    originRequest:
      connectTimeout: 10s
  - service: http_status:404
`

**Absolutely NO:**
- grafana.<domain> — violates ADR-026
- prometheus.<domain> — violates ADR-019
- pi.<domain> — violates ADR-019
- *.<domain> — violates both ADRs

### 8.4 Security Checklist

- [ ] Only ONE ingress rule (Discord webhook) — NO grafana, admin, or API exposure
- [ ] Tunnel credentials stored in SOPS-encrypted file (ADR-015)
- [ ] Webhook signature validation at application layer (Discord's ed25519 signing)
- [ ] systemd service uses Slice=guinevere.slice for resource limits
- [ ] UFW unchanged — cloudflared connects outbound only
- [ ] Tunnel health monitoring configured (ADR-017)
- [ ] Aizanta unaffected — verify after tunnel setup

---

## 9. Downstream Dependencies

| Step | Relationship |
|------|-------------|
| P0-022 (Tailscale) | Hard dependency — must complete first |
| P0-024 (Caddy) | Can proceed after tunnel — configures internal HTTPS only |
| P0-028 (Pre-flight verification) | Will verify tunnel is active and serving correct endpoint |
| P2-010/P2-021 (Discord commands) | Discord bot uses webhook for event delivery |
| P5-001 (FastAPI internal API) | The webhook endpoint at localhost:8000 must exist |
| P7-001 (Surveillance receiver) | Could share FastAPI port 8000 |

---

## 10. Summary

| Item | Value |
|------|-------|
| Step | P0-023 |
| Status | Unchecked (not started) |
| Dependency | P0-022 (Tailscale) — also unchecked |
| Cost | /month (Cloudflare free tier) |
| Risk | Medium |
| ADR primary | ADR-026 |
| ADR constraint | ADR-019 (zero public ports, tunnel is the exception) |
| Evidence path | docs/setup-evidence/P0/STEP-P0-023/ |
| Audit path | udit-reports/P0/STEP-P0-023/ |
| Executor | Guinevere (autonomous) |
| Estimated time | 2 hours |
| Domain needed | Real domain on Cloudflare (TBD by Faiz) |
| Key contradiction | Browser auth on headless VPS — use local machine login + SCP |
| Key ADR violation risk | Deployment Guide includes grafana endpoint — MUST NOT USE |
| StepPrompts hostname bug | Uses webhook.guinevere.internal (not a real domain) |
