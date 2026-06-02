# Internal Context Report — STEP-P0-022: Tailscale Configuration

**Date**: 2026-05-31
**Step**: P0-022 — Tailscale VPN Mesh
**Phase**: P0 Infrastructure (step 22/29)
**Status**: ⬜ Not Started (Tailscale binary already installed and running)
**Risk**: Medium
**ADR**: ADR-019 (Access Control & VPN Mesh Strategy)
**Dependencies**: P0-004 (UFW configured — Tailscale UDP 41641 port)
**P0-023 Dependency**: Cloudflare Tunnel (P0-023) depends on P0-022 being complete
**Cost**: $0/month (Tailscale free tier, up to 100 devices)
**Estimated Time**: 2 hours (reduced — install step is already done)
**Evidence Root**: docs/setup-evidence/P0/STEP-P0-022/
**Report Purpose**: Pre-implementation intelligence consolidation for ACL rule design and verification planning

---

## 1. Current State — PROGRESS.md

### Counters
| Field | Value |
|---|---|
| Total Steps | 257 |
| Completed | 22 / 257 (8.6%) |
| P0 Steps | 22 / 29 |
| P0-022 | [ ] unchecked |

### Phase Summary (P0 row)
| P0 | Infrastructure | 22/29 | $0 | 58-116h | None | None |

### P0-022 Entry
- [ ] P0-022 Tailscale VPN mesh (zero public ports, per ADR-019)

**Context**: All prior P0 steps (P0-000 through P0-021) are complete. P0-023 and beyond block on P0-022.

---

## 2. Current State — CHECKLIST.md (Line 122)

- [ ] P0-022: `tailscale status` -> VPS online; `tailscale ip -4` -> 100.x.y.z assigned

**Critical observation**: The CHECKLIST.md verification command **already presumes Tailscale is installed and running** (`tailscale status` and `tailscale ip -4` are live commands, not install commands). This confirms Tailscale was installed during or before P0-000 (VPS audit) and has been running ever since.

**Current CHECKLIST gap**: Only 2 verification items exist for P0-022 — no coverage of:
- ACL policy deployment
- Device tags (tag:server, tag:operator-device, etc.)
- MagicDNS status
- Auth key expiry configuration
- No public ports (`ss -tlnp` zero-public check)
- Lockout recovery procedure

---

## 3. StepPrompts.md — P0-022 Section (Lines 2373-2456)

### Full Command List (from StepPrompts)

```bash
# 1. Install Tailscale
curl -fsSL https://tailscale.com/install.sh | sh

# 2. Authenticate
sudo tailscale up --hostname=guinevere-vps --accept-routes

# 3. Verify connection
tailscale status
tailscale ip

# 4. Test connectivity from operator device
# ping guinevere-vps

# 5. Configure as exit node (optional)
# sudo tailscale up --advertise-exit-node

# 6. Verify UFW still secure
sudo ufw status

# 7. Capture Tailscale IP for service binding
TAILSCALE_IP=$(tailscale ip -4)
echo "Tailscale IP: $TAILSCALE_IP"

# 8. Verify no public exposure
ss -tlnp | grep -v "127.0.0.1" | grep -v "$TAILSCALE_IP" | grep -v "::1"
```

### Verification Checklist (from StepPrompts)
- [ ] Tailscale connected -> `tailscale status` shows guinevere-vps as online
- [ ] Tailscale IP assigned -> `tailscale ip` returns 100.x.x.x
- [ ] Pingable from operator -> `ping guinevere-vps` from Tailscale-connected device works
- [ ] No public admin ports -> `ss -tlnp` shows only localhost + Tailscale bindings
- [ ] UFW intact -> `sudo ufw status` shows SSH + Tailscale UDP only

### Rollback Commands
```bash
sudo tailscale down
sudo tailscale logout
sudo apt purge -y tailscale
```

### Evidence (from StepPrompts)
- Log: docs/setup-evidence/P0/STEP-P0-022/tailscale-status.txt
- Screenshot: docs/setup-evidence/P0/STEP-P0-022/tailscale-network.png

---

## 4. ADR-019 — Key Requirements

**Status**: Accepted with notes
**Risk Level**: HIGH

### Core Decisions

| Requirement | Detail | Status |
|---|---|---|
| Zero public ports | All VPS admin surfaces are Tailscale-internal only. Public integrations use outbound channels only. | P0-004 (UFW) has SSH only. Need to verify no additional public ports. |
| Tailscale mesh for all devices | Faiz workstations, Android HP, Windows Laptop, VPS all join the tailnet. | VPS already on tailnet. Need to verify all devices. |
| Internal services via Tailscale-internal addresses | Grafana, Prometheus, PostgreSQL admin only over Tailscale. | Not yet implemented — services still bind to localhost or Docker. |

### Implementation Notes (from ADR-019 review record)

| Note | Detail | Action Required |
|---|---|---|
| Tailscale ACL | Document ACL policy file structure with device tags (e.g., tag:admin, tag:service) and auto-approvers. | Write ACL policy JSON |
| Auth key expiry | Device keys expire after 180 days by default. Headless nodes (VPS) require auth key with appropriate expiry or disabled expiry. Document renewal procedure. | Verify guinevere-vps key expiry setting |
| Lockout recovery | Emergency access path if VPN misconfig locks out: VPS console (cloud provider), Tailscale recovery auth key stored offline, or DERP relay fallback. | Document recovery procedure |
| DERP/Control plane | DERP relay fallback throttles 30-100 Mbps. Control plane is US-hosted (AWS). | Informational — no action |
| Subnet routing | Tailscale does not bypass host firewalls. Security groups must allow inbound from Tailscale subnet router IPs. | UFW already configured |
| Overlapping CIDRs | Plan non-overlapping subnets across all tailnet members. | Verify once all devices are known |

---

## 5. Contradictions & Blockers

### Contradiction A: StepPrompts Assumes Fresh Install vs. Live Reality

| Aspect | StepPrompts Says | Live Reality | Impact |
|---|---|---|---|
| Tailscale installed? | Install script — first command | Already installed and running | Step 1 is DONE. Skip install command. |
| Auth method | `sudo tailscale up` with interactive URL | May already be authenticated | Check `tailscale status` first; may need re-auth with ACL tags |
| Hostname | `--hostname=guinevere-vps` | May already have a hostname | Check current hostname via `tailscale status` |
| UFW 41641 | Not mentioned in StepPrompts commands (only in pre-flight) | Need to verify | P0-004 may have it; check `sudo ufw status verbose` |

### Contradiction B: StepPrompts vs. ADR-019 Scope

| Capability | StepPrompts Includes | ADR-019 Requires | Gap |
|---|---|---|---|
| ACL policy JSON | No mention | Document ACL with device tags and auto-approvers | Major — ACL policy is the main deliverable |
| Device tags | No tag flag in `tailscale up` | tag:server, tag:operator-device, tag:surveillance-device | Major — need to re-auth with tags |
| Auth key | Interactive URL only | Auth key for headless nodes with expiry management | Major — need auth key for headless operation |
| MagicDNS | Not mentioned | MagicDNS for service discovery | Needs verification in admin panel |
| SSH lockdown to tailscale0 | Not mentioned | SSH only over Tailscale | Future P10 step; not required now |
| Lockout recovery | No procedure | Document emergency access path | Procedure to document |
| Key expiry renewal | No mention | 180-day default, headless node renewal | Needs procedure documented |

### Contradiction C: Deployment Guide vs. Security Policy ACL Schema

| Aspect | Deployment Guide (Section 4.2) | Security Policy (Section 9.3) | Impact |
|---|---|---|---|
| Tags | tag:server, tag:operator, tag:monitoring | tag:vps, tag:operator-device, tag:surveillance-device | Need to pick one schema |
| Groups | group:admin with faiz@example.com | autogroup:admin | Different, need to reconcile |
| SSH ACL | Separate ssh block with users: ["faiz", "guinevere"] | Not in Security Policy ACL | Deployment Guide more detailed |
| ACL structure | 3 rules (operator->server, server->server) | 3 rules (operator-device->vps, surveillance-device->vps:8000/8443, vps->vps) | Security Policy has port-specific surveillance ACL |
| Auto-approvers | 10.0.0.0/24 routes | Same 10.0.0.0/24 routes | Consistent |
| Exit node | "exitNode": [] | Not mentioned | Deployment Guide more complete |

**Recommendation**: Prefer the Deployment Guide ACL schema as it is more detailed and has SSH + exit node coverage. Enrich with Surveillance Device port restrictions from Security Policy.

---

## 6. Deployment Guide (Section 4.2) — Detailed Tailscale Commands

### Install & Auth (Reference — install step is already done)
```bash
# Install Tailscale from official repo (NOT Snap)
curl -fsSL https://tailscale.com/install.sh | sh
systemctl enable --now tailscaled

# Authenticate with auth key and tag
# Generate reusable auth key: https://login.tailscale.com/admin/settings/keys
tailscale up \
  --authkey=tskey-auth-XXXXX \
  --advertise-tags=tag:server \
  --hostname=guinevere-vps \
  --ssh \
  --accept-dns=true
```

### Reference ACL Policy (Deployment Guide version)
```json
{
  "groups": { "group:admin": ["faiz@example.com"] },
  "tagOwners": {
    "tag:server": ["group:admin"],
    "tag:operator": ["group:admin"],
    "tag:monitoring": ["group:admin"]
  },
  "acls": [
    { "action": "accept", "src": ["tag:operator", "group:admin"], "dst": ["tag:server:*"] },
    { "action": "accept", "src": ["tag:server"], "dst": ["tag:server:*"] }
  ],
  "ssh": [
    { "action": "accept", "src": ["tag:operator", "group:admin"], "dst": ["tag:server"], "users": ["faiz", "guinevere"] }
  ],
  "autoApprovers": { "routes": { "10.0.0.0/24": ["tag:server"] }, "exitNode": [] }
}
```

### Reference UFW Rules (from Deployment Guide Section 4.3)
```bash
ufw allow 41641/udp comment "Tailscale WireGuard"
ufw allow in on tailscale0 comment "All Tailscale interface traffic"
```

---

## 7. Security Policy (Section 9.3) — Tailscale ACL Reference

### Reference ACL Policy (Security Policy version)
```json
{
  "acls": [
    {
      "action": "accept",
      "src": ["tag:operator-device"],
      "dst": ["tag:vps:*"]
    },
    {
      "action": "accept",
      "src": ["tag:surveillance-device"],
      "dst": ["tag:vps:8000", "tag:vps:8443"]
    },
    {
      "action": "accept",
      "src": ["tag:vps"],
      "dst": ["tag:vps:*"]
    }
  ],
  "tagOwners": {
    "tag:vps": ["autogroup:admin"],
    "tag:operator-device": ["autogroup:admin"],
    "tag:surveillance-device": ["autogroup:admin"]
  },
  "autoApprovers": {
    "routes": { "10.0.0.0/24": ["tag:vps"] }
  }
}
```

**Key controls from Security Policy**:
- Device authorization: pre-approved devices only
- Key expiry: 180-day default with renewal notification
- Tag-based ACLs: devices tagged by role (vps, operator-device, surveillance-device)
- No exit nodes configured
- MagicDNS enabled for service discovery
- UFW: 41641/UDP Public (required), all other services Tailscale interface only

### UFW Rules from Security Policy
```bash
# Tailscale (required for mesh networking)
ufw allow in on tailscale0 to any port 22
ufw allow in on tailscale0 to any port 80
ufw allow in on tailscale0 to any port 443

# Tailscale UDP for mesh connectivity
ufw allow 41641/udp

# Service ports (Tailscale interface only)
ufw allow in on tailscale0 to any port 3000
ufw allow in on tailscale0 to any port 8000
ufw allow in on tailscale0 to any port 9090
ufw allow in on tailscale0 to any port 3001

# SSH brute force protection via Tailscale
ufw limit in on tailscale0 to any port 22
```

**Note**: The UFW rules in Security Policy are more granular than Deployment Guide. For P0-022, these service-port rules (3000, 8000, 9090, 3001) are **preparatory** — actual services will bind to these ports in later steps. The P0-022 step should at minimum configure:
- `ufw allow 41641/udp` (if not already done in P0-004)
- `ufw allow in on tailscale0` (catch-all for Tailscale interface)
- Verify no public exposure with `ss -tlnp`

---

## 8. Shared VPS Guardrails for P0-022

### Cardinal Rule
**Do not touch Aizanta services, containers, databases, or files.**

| Resource | Guinevere | Aizanta | P0-022 Impact |
|---|---|---|---|
| Linux user | guinevere | aizanta | Tailscale runs as root (tailscaled) — no user conflict |
| Docker network | guinevere-net | aizanta-net | Tailscale not Docker-related |
| Systemd services | guinevere-* | aizanta-* | tailscaled is a standard service, not Guinevere-specific |
| Port space | 6380, 5433, etc. | 6379, 5432, etc. | Tailscale uses 41641/UDP — check no Aizanta conflict |
| Network | Docker bridge | Docker bridge | Tailscale creates tailscale0 interface — isolated |

### Pre-existing P0 Step Safety (from P0-021 auditor evidence)
- Aizanta 5/5 containers healthy (bot, nginx, frontend, postgres, redis)
- Aizanta Redis on 127.0.0.1:6379 (separate from Guinevere 6380)
- Aizanta PostgreSQL on 127.0.0.1:5432 (separate from Guinevere 5433)
- Aizanta port 80 (nginx) on 100.94.104.22 (Tailscale IP) — verified no conflict

### P0-022 Specific Guards
1. **Don't break SSH**: Do not modify UFW SSH rules or SSH config. If SSH runs on port 22 (non-standard for Tailscale-only), document but do not change (that is P10).
2. **Don't touch Aizanta networking**: Do not modify Aizanta Docker networks or IP tables.
3. **UFW 41641**: Verify `ufw allow 41641/udp` is already configured from P0-004. If not, add it.
4. **Don't mess with Aizanta Tailscale**: If Aizanta has its own Tailscale setup, leave it alone. Guinevere uses the same tailscaled instance (system-level) but different tags/rules.
5. **Verify after every change**: Run Aizanta health check (`systemctl status aizanta-*`, `docker ps --filter "name=aizanta"`).

### Aizanta Health Check Commands (run after each P0-022 sub-step)
```bash
systemctl status aizanta-*
docker ps --filter "name=aizanta"
redis-cli -n 10 PING
psql -U aizanta -d aizanta -c "SELECT 1"
```

---

## 9. Evidence Path Convention

### Directory
docs/setup-evidence/P0/STEP-P0-022/

### Required Artifacts (from StepPrompts + prior P0 pattern)
| File | Source | Description |
|---|---|---|
| tailscale-status.txt | StepPrompts | `tailscale status` output showing all tailnet members |
| tailscale-network.png | StepPrompts | Screenshot of Tailscale admin panel (network map) |
| tailscale-acl.json | ADDED | ACL policy JSON applied to tailnet |
| tailscale-ip.txt | ADDED | `tailscale ip -4` and `tailscale ip -6` output |
| magicdns-status.txt | ADDED | MagicDNS verification and DNS resolution |
| public-ports-check.txt | ADDED | `ss -tlnp` filtered output showing no public exposure |
| ufw-status.txt | ADDED | `sudo ufw status verbose` showing Tailscale rules |
| verification.md | Prior P0 pattern | Full verification report |
| summary.md | Prior P0 pattern | High-level summary |
| aizanta-post-check.md | Prior P0 pattern | Aizanta health after Tailscale changes |

### Prior P0 Evidence Pattern (from P0-021)

verification.md structure:
```markdown
# STEP-P0-022 — Verification

**Step**: P0-022 — Tailscale Configuration
**Date**: 2026-05-31
**Status**: PASS, independent auditor gate passed

## 1. What Was Done
[Summary of ACL config, MagicDNS, auth key, verification]

## 2. Files Changed
**Local**: [evidence files created]
**Remote (VPS)**: [Tailscale ACL, config changes, etc.]

## 3. Validation Results
### Tailscale Status
### ACL Users/Groups/Tags
### MagicDNS
### No Public Ports
### UFW Rules

## 4. Evidence Artifacts
[List of artifact files]

## 5. Shared VPS Impact
- Aizanta health status
- No Aizanta networks/containers modified

## 6. ADR Compliance
- ADR-019: zero public ports, ACL policy, auth key, device tags
- ADR-014: resource isolation

## 7. Rollback / Re-run Safety
[How to undo Tailscale config changes]

## 8. Design Decisions / Caveats
[ACL schema choice, tag naming, etc.]

## 9. Evidence Gate
[Parent verification, LSP, Aizanta guardrails, auditor]

## 10. Footer
```

---

## 10. Recommended Verification Commands (Adapted for Live State)

### Pre-flight (Verify Tailscale Already Running)
```bash
# Check if Tailscale is installed and running
which tailscale
systemctl status tailscaled
tailscale status
tailscale ip -4

# Check current hostname and tags
tailscale status --json | grep -E '"HostName"|"Tags"|"Online"'

# Check UFW 41641
sudo ufw status verbose | grep 41641

# Check current public exposure
ss -tlnp
```

### Core Configuration Steps
```bash
# 1. Authenticate with auth key and tags (if not already tagged)
#    Generate auth key: https://login.tailscale.com/admin/settings/keys
#    Options: --advertise-tags=tag:server --hostname=guinevere-vps --ssh --accept-dns=true
sudo tailscale up --authkey=tskey-auth-XXXXX --advertise-tags=tag:server --hostname=guinevere-vps --ssh --accept-dns=true

# 2. Verify new config
tailscale status
tailscale ip -4
```

### Verification Commands
```bash
# Tailscale status
tailscale status
tailscale status --json | head -50

# IP assignment
tailscale ip -4
tailscale ip -6

# MagicDNS (guinevere-vps should resolve)
getent hosts guinevere-vps 2>/dev/null || host guinevere-vps 2>/dev/null || dig +short guinevere-vps 2>/dev/null

# Ping test from operator device (run locally, not on VPS)
# ping guinevere-vps

# No public ports
ss -tlnp | grep -v "127.0.0.1" | grep -v "$(tailscale ip -4)" | grep -v "::1"

# UFW intact
sudo ufw status verbose

# Aizanta health
systemctl status aizanta-*
docker ps --filter "name=aizanta"
```

### ACL Verification
```bash
# Verify ACL via Tailscale API (requires API key)
# curl -s https://api.tailscale.com/api/v2/tailnet/-/acl -u "${TS_API_KEY}:"

# Or check via admin panel: https://login.tailscale.com/admin/acls
# Verify:
# - tag:server exists with VPS tagged
# - ACL rules allow operator->server and server->server
# - SSH ACL allows faiz and guinevere users
# - Auto-approvers configured for 10.0.0.0/24
```

### Yes/No Verification Checklist
- [ ] `tailscale status` -> guinevere-vps online
- [ ] `tailscale ip -4` -> 100.x.x.x assigned
- [ ] `tailscale status --json | grep Tags` -> tag:server present
- [ ] `getent hosts guinevere-vps` -> resolves to 100.x.x.x (MagicDNS)
- [ ] `ss -tlnp` -> only localhost + Tailscale IP ports (no public 0.0.0.0)
- [ ] `sudo ufw status verbose` -> 41641/udp ALLOW, tailscale0 ALLOW
- [ ] ACL JSON applied via admin panel
- [ ] Auth key configured with appropriate expiry (tag:server tagOwners)
- [ ] Device key expiry: disabled or extended for guinevere-vps
- [ ] Lockout recovery procedure documented
- [ ] Aizanta 5/5 containers healthy
- [ ] Ping from operator device succeeds

---

## 11. ACL Design Decision Points

### Tag Schema Decision

Two competing schemas exist in the codebase. Faiz must pick one or a hybrid:

**Option A: Deployment Guide schema** (more detailed, SSH support)
- Tags: tag:server, tag:operator, tag:monitoring
- Groups: group:admin (faiz@example.com)

**Option B: Security Policy schema** (port-specific surveillance)
- Tags: tag:vps, tag:operator-device, tag:surveillance-device
- Groups: autogroup:admin

**Recommendation**: Use Option A (Deployment Guide) as base, enriched with Option B surveillance device port restriction. This gives:
- tag:server for guinevere-vps
- tag:operator for Faiz devices
- tag:surveillance for Android HP + Windows Laptop (surveillance ingest)
- tag:monitoring for monitoring-only access (future)
- group:admin = Faiz identity
- Surveillance devices restricted to port 8000 and 8443
- SSH ACL for faiz and guinevere users via tag:server

### Proposed ACL Rules
```json
{
  "groups": {
    "group:admin": ["faiz@example.com"]
  },
  "tagOwners": {
    "tag:server": ["autogroup:admin"],
    "tag:operator": ["autogroup:admin"],
    "tag:surveillance": ["autogroup:admin"],
    "tag:monitoring": ["autogroup:admin"]
  },
  "acls": [
    { "action": "accept", "src": ["tag:operator", "group:admin"], "dst": ["tag:server:*"] },
    { "action": "accept", "src": ["tag:surveillance"], "dst": ["tag:server:8000", "tag:server:8443"] },
    { "action": "accept", "src": ["tag:server"], "dst": ["tag:server:*"] },
    { "action": "accept", "src": ["tag:monitoring"], "dst": ["tag:server:9090", "tag:server:3000"] }
  ],
  "ssh": [
    { "action": "check", "src": ["tag:operator", "group:admin"], "dst": ["tag:server"], "users": ["faiz", "guinevere"] }
  ],
  "autoApprovers": {
    "routes": { "10.0.0.0/24": ["tag:server"] },
    "exitNode": []
  }
}
```

---

## 12. Action Plan Summary

### What is Already Done (Do Not Repeat)
1. Tailscale installed (tailscale binary exists)
2. tailscaled service running
3. VPS connected to tailnet (CHECKLIST.md expects `tailscale status` to work)
4. UFW 41641/udp likely configured from P0-004 (verify)

### What Needs to Be Done
1. Verify live state: `tailscale status`, `tailscale ip -4`, `sudo ufw status`
2. Determine current hostname and tag assignment
3. Generate auth key and re-authenticate with `--advertise-tags=tag:server --ssh --accept-dns=true`
4. Write and apply ACL JSON policy (reconcile Deployment Guide vs Security Policy)
5. Enable MagicDNS and verify DNS resolution
6. Configure key expiry: disable for guinevere-vps (headless node)
7. Verify zero public ports: `ss -tlnp`
8. Verify UFW rules: 41641/udp + tailscale0 interface
9. Document lockout recovery procedure
10. Verify Aizanta unaffected
11. Capture evidence artifacts
12. Run auditor gate

### What to Defer (P10 Hardening)
- SSH lockdown to Tailscale only (change SSH port to 2222, bind to tailscale0 only)
- Service binding to Tailscale IP (Grafana:3000, Prometheus:9090 — these do not exist yet)

### Blockers
- ACL schema decision: need Faiz to pick tag naming convention
- Auth key: need access to Tailscale admin panel to generate key
- Email address for group:admin membership

---

## 13. Appendix: File Reference Map

| File | Lines | Relevance |
|---|---|---|
| PROGRESS.md | Line 66 | P0-022 unchecked entry |
| CHECKLIST.md | Line 122 | P0-022 verification (basic status check only) |
| stepprompts/StepPrompts.md | Lines 2373-2456 | P0-022 full step prompt (install-focused) |
| adr/ADR-019-access-control-vpn-mesh-strategy.md | Full (142 lines) | Zero public ports, ACL, auth key, lockout recovery |
| docs/40-operations/44-DeploymentGuide_v1.0.md | Lines 1917-1969 | Tailscale install, auth, ACL, UFW rules |
| docs/20-security/20-SecurityPolicy_v1.0.md | Lines 1943-1992 | Tailscale ACL policy, port exposure matrix |
| docs/IMPLEMENTATION_GUIDE.md | Full (560 lines) | Step execution workflow, evidence system, shared VPS rules |
| docs/setup-evidence/P0/STEP-P0-021/verification.md | Full (89 lines) | Prior P0 evidence pattern (verification template) |
| docs/setup-evidence/P0/STEP-P0-021/p0-021-summary.md | Full (28 lines) | Prior P0 evidence pattern (summary template) |
| audit-reports/P0/STEP-P0-021/step-p0-021-auditor-report.md | Full (144 lines) | Prior P0 auditor report pattern |
| docs/setup-evidence/P0/STEP-P0-020/verification.md | Full (104 lines) | Prior P0 evidence pattern |
| docs/setup-evidence/P0/STEP-P0-020/p0-020-summary.md | Full (34 lines) | Prior P0 summary pattern |

---

*Report generated for pre-implementation planning of STEP-P0-022 (Tailscale Configuration). Based on reading of 12+ source documents. Send to Faiz for ACL schema decision before proceeding to implementation.*
