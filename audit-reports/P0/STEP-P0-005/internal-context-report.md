# STEP-P0-005 — Internal Context Report (Phase 0 Research Synthesis)

**Step:** P0-005 — fail2ban Configuration (SSH brute force protection)
**Phase:** P0 Infrastructure Foundation (29 steps, step 5 of 29)
**Date:** 2026-05-31
**Status:** ⬜ Not Started (P0-000 through P0-004 complete)
**Scope:** Internal repo/doc/ADR context audit + execution planning — read-only, no VPS, SSH, UFW, fail2ban, Docker, Aizanta, or secrets changes
**Report type:** Pre-implementation internal research (research wave output for parent orchestrator)
**Downstream:** Parent will synthesize with external research before implementing fail2ban changes

**Source files read:**
- PROGRESS.md
- CHECKLIST.md
- stepprompts/StepPrompts.md (P0-005 section, lines 609-686; P0-006 section lines 690-769 for dependency cross-refs; P0-028 lines 3008-3046+ for pre-flight verification)
- docs/IMPLEMENTATION_GUIDE.md
- docs/10-governance/17-ADR_Index_v1.0.md
- docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
- adr/ADR-018-security-architecture-defense-in-depth.md
- adr/ADR-019-access-control-vpn-mesh-strategy.md
- docs/20-security/20-SecurityPolicy_v1.0.md (Section 1.2 Layer 2 Host, Section 6 Network Security)
- docs/40-operations/44-DeploymentGuide_v1.0.md (Section 2.2 Step 8: Intrusion Detection (fail2ban))
- docs/40-operations/45-InternalOpsManual_v1.0.md (fail2ban status references)
- docs/00-core/02-TechnicalArchitecture_v2.0.md
- docs/setup-evidence/P0/STEP-P0-000/vps-audit-2026-05-31.txt
- docs/setup-evidence/P0/STEP-P0-000/service-inventory.md
- docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt
- docs/setup-evidence/P0/STEP-P0-004/verification.md
- docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md
- docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md
- audit-reports/P0/STEP-P0-004/internal-context-report.md (P0-004 pattern reference)
- audit-reports/P0/STEP-P0-004/evidence-pattern-report.md (evidence pattern reference)
- audit-reports/P0/STEP-P0-004/external-tailscale-ufw-report.md (Tailscale/UFW coexistence research)
- audit-reports/P0/STEP-P0-004/external-ufw-safety-report.md (UFW safety research, includes fail2ban integration 9.4)
- Prior P0 evidence files under docs/setup-evidence/P0/STEP-P0-00{0,1,2,3,4}/

---

## 1. Step Definition (from StepPrompts.md lines 609-686)

| Field | Value |
|-------|-------|
| **Step ID** | P0-005 |
| **Type** | Security |
| **Risk** | Medium |
| **Status** | ⬜ Not Started |
| **Goal** | Protect SSH from brute-force attacks with automatic IP banning |
| **Dependencies** | P0-004 (UFW configured) — ✅ Complete |
| **Cost Impact** | /month |
| **ADR References** | ADR-018 (Security Architecture) |
| **Acceptance Criteria** | AC-SEC-001 |
| **Estimated Time** | 1 hour |
| **Git Commit** | chore(P0): pending |

### 1.1 Context (from StepPrompts)

> fail2ban monitors authentication logs and bans IPs that show malicious signs. Combined with UFW, it provides a strong first line of defense against automated attacks on the shared VPS.

### 1.2 Commands (from StepPrompts lines 632-660)

`ash
# Install fail2ban
sudo apt update && sudo apt install -y fail2ban

# Create local configuration
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd
banaction = ufw

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = %(sshd_log)s
maxretry = 3
bantime = 86400
EOF

# Enable and start fail2ban
sudo systemctl enable fail2ban
sudo systemctl start fail2ban

# Verify status
sudo fail2ban-client status
sudo fail2ban-client status sshd
`

### 1.3 Verification (from StepPrompts)

| Check | Command | Expected |
|-------|---------|----------|
| fail2ban running | systemctl status fail2ban | active |
| SSH jail active | fail2ban-client status sshd | jail enabled |
| Ban action is UFW | config shows banaction = ufw | banaction = ufw |

### 1.4 Evidence Path (from StepPrompts - note the pattern deviation)

StepPrompts line 668 shows: evidence/phase-0/step-005/fail2ban-status.txt
Prior P0 convention (confirmed by evidence-pattern-report.md): docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt

**Decision:** Use prior P0 convention (docs/setup-evidence/...).

### 1.5 Rollback

`ash
sudo systemctl stop fail2ban
sudo systemctl disable fail2ban
sudo apt purge -y fail2ban
sudo rm /etc/fail2ban/jail.local
`

---

## 2. Current Tracker State

### 2.1 PROGRESS.md (line 49)

`
- [ ] **P0-005** fail2ban configuration (SSH brute force protection)
`

Status: **NOT checked** — ready for execution. Overall: 5/257 steps complete, P0: 5/29.

### 2.2 CHECKLIST.md (line 103)

`
- [ ] P0-005: sudo fail2ban-client status sshd -> jail active, banned count listed
`

Also (line 140): UFW: only SSH allowed; ss -tlnp: no public ports beyond 22

Status: **NOT checked**.

### 2.3 StepPrompts.md status

Line 612: **Status:** ⬜ Not Started — update to ✅ after execution.

### 2.4 Evidence directory

docs/setup-evidence/P0/STEP-P0-005/ — **does not exist yet** (no prior evidence).

---

## 3. VPS Audit Baseline (from P0-000 Evidence)

### 3.1 CRITICAL FINDING: fail2ban is ALREADY INSTALLED AND RUNNING

The P0-000 VPS audit file (vps-audit-2026-05-31.txt, line 28) shows:

`
fail2ban.service            loaded active running Fail2Ban Service
`

This is a **critical deviation** from the StepPrompts assumption that fail2ban is not yet installed. The StepPrompts commands expect to install from scratch (sudo apt install -y fail2ban), but the VPS already has fail2ban active.

**Implications:**
- The installation command is redundant — apt will report "already installed / newest version"
- The existing configuration must be read before overwriting with jail.local
- The existing fail2ban config may already have jails configured (possibly for Aizanta)
- We must check what jails are currently active and what ban action is configured
- Rollback may need to account for restoring the original config if the new one breaks something

### 3.2 Current UFW State (from P0-004 evidence)

After P0-004, UFW state is:

`
Status: active
Default: deny (incoming), allow (outgoing), deny (routed)
22/tcp        ALLOW IN    Anywhere       # SSH key-only
41641/udp     ALLOW IN    Anywhere       # Tailscale
22/tcp (v6)   ALLOW IN    Anywhere (v6)  # SSH key-only
41641/udp (v6) ALLOW IN  Anywhere (v6)   # Tailscale
`

**Key:** UFW is active with only SSH and Tailscale allowed — the expected precondition for fail2ban.

### 3.3 Aizanta Services (from P0-004 evidence)

`
aizanta-bot         Up 7 days (healthy)  8000/tcp
aizanta-nginx       Up 7 days (healthy)  100.94.104.22:80->80/tcp
aizanta-frontend    Up 7 days (healthy)  3000/tcp
aizanta-postgres    Up 7 days (healthy)  127.0.0.1:5432->5432/tcp
aizanta-redis       Up 7 days (healthy)  127.0.0.1:6379->6379/tcp
`

### 3.4 Tailscale State

- Tailscale version: 1.98.3
- Tailscale IP: 100.94.104.22 (IPv4)
- Operator workstation Tailscale IP (from P0-004): 100.112.201.124
- Netfilter mode: default 'on' (automatic rule insertion)

Tailscale's automatic netfilter rules (post-PR #10370) mean Tailscale traffic bypasses UFW's INPUT chain. This means fail2ban's anaction = ufw will NOT block Tailscale IPs — the ban action operates on UFW rules which are bypassed by Tailscale's auto-inserted iptables rules.

**Consequence:** Public SSH is protected by fail2ban+UFW. Tailscale SSH is not blocked by fail2ban+UFW (desirable — Tailscale authenticates at the mesh level).

### 3.5 Current VPS Identity

- Hostname: faiz-prod-01
- SSH port: 22 (standard)
- Public IP: (bound to eth0, not explicitly documented in evidence — only Tailscale IP 100.94.104.22 is documented)

---

## 4. ADR Constraints & Compliance Mapping

### 4.1 ADR-018 (Security Architecture & Defense-in-Depth)

| Constraint | Impact on P0-005 |
|------------|------------------|
| Layer 2: Host — VPS-level hardening | fail2ban is explicitly listed as a Layer 2 control (Security Policy 1.2) |
| Ban action integration | StepPrompts uses banaction = ufw — aligns with defense-in-depth (UFW is Layer 1, fail2ban Layer 2) |
| Fail2ban monitors auth logs | Uses backend = systemd and logpath = %(sshd_log)s — standard SSH auth monitoring |
| Layer 1 (UFW) prerequisite | P0-005 depends on P0-004 being complete — ✅ confirmed |

### 4.2 ADR-019 (Access Control & VPN Mesh)

The Tailscale zero-trust mesh provides identity-aware access control independent of fail2ban. ADR-019 target state is "zero public admin surfaces" — in the end state, SSH would be Tailscale-only, making fail2ban's SSH jail less critical. However, for P0 (transitional state where SSH is still publicly allowed), fail2ban is essential.

**Collision noted:** fail2ban with banaction = ufw cannot effectively ban IPs connecting over Tailscale. This is actually desirable behavior.

### 4.3 Security Policy References

Security Policy 1.2 Layer 2 (Host) controls list: "Ubuntu 24.04 hardened, SSH key-only auth, fail2ban, unattended-upgrades, systemd service sandboxing"

SRS-NFR-014: "Guinevere must implement UFW firewall + fail2ban + CrowdSec: port rules enforced, brute force blocked, threat intelligence feeds active."

---

## 5. Cross-Doc Contradictions & Ambiguities

### 🔴 C1: fail2ban Already Installed — StepPrompts Assumes Clean Install

| Source | Detail |
|--------|--------|
| StepPrompts P0-005 commands | sudo apt install -y fail2ban — assumes fresh install |
| VPS audit (P0-000) line 28 | ail2ban.service loaded active running Fail2Ban Service |

**Impact:** fail2ban is already installed and running. Running pt install is harmless (apt handles reinstall gracefully). However, **overwriting jail.local without reading the existing config could break existing Aizanta fail2ban rules or the current operational config.**

**Severity: 🔴 BLOCKING** — Must read existing fail2ban configuration before writing jail.local.

### 🟡 C2: StepPrompts vs DeploymentGuide — Fail2ban Config Mismatch

| Aspect | StepPrompts P0-005 | DeploymentGuide 2.2 Step 8 |
|--------|--------------------|---------------------------|
| DEFAULT bantime | 3600 (1 hour) | 3600 (1 hour) |
| DEFAULT findtime | 600 (10 min) | Not set (uses default 600) |
| DEFAULT maxretry | 3 | 5 |
| DEFAULT banaction | ufw | ufw |
| sshd maxretry | 3 | 3 |
| sshd bantime | 86400 (24 hours) | 86400 (24 hours) |
| Additional jails | None | guinevere-core-auth (maxretry=3, bantime=86400), guinevere-surveillance (maxretry=10, bantime=1800) |
| Custom filters | None | filter.d/fastapi-auth.conf |

DeploymentGuide extra jails reference services that don't exist yet. **Defer to when services are deployed.**

### 🟡 C3: Evidence Path Convention Mismatch

StepPrompts line 668 uses evidence/phase-0/step-005/ while prior P0 convention is docs/setup-evidence/P0/STEP-P0-005/. Follow prior P0 convention.

### 🟡 C4: UFW Rate Limiting Overlap with fail2ban

P0-004 external-ufw-safety-report.md (9.2) recommends sudo ufw limit ssh/tcp — this overlaps with fail2ban's SSH jail but is complementary defense-in-depth.

### 🟡 C5: P0-006 CrowdSec Dependency

StepPrompts P0-006 (line 698) dependency on P0-005 is correct. CrowdSec complements fail2ban.

### 🟡 C6: P0-028 Pre-Flight Verification

P0-028 checks systemctl is-active fail2ban — correct for verifying fail2ban state.

---

## 6. Acceptance Criteria Detail

### 6.1 AC-SEC-001 (AcceptanceCriteriaCatalog)

> RBAC/ABAC must enforce default deny across human, agent, sub-agent, service, database, Redis, object storage, API, filesystem, systemd, Tailscale, crypto, backup, export, and break-glass surfaces.

P0-005 contribution: fail2ban is a host-level access control supporting the broader "default deny" posture by banning repeated SSH brute-force offenders.

### 6.2 SRS-NFR-014 (SRS v1.0)

> Guinevere must implement UFW firewall + fail2ban + CrowdSec: port rules enforced, brute force blocked, threat intelligence feeds active.

P0-004 (UFW) + P0-005 (fail2ban) + P0-006 (CrowdSec) collectively satisfy SRS-NFR-014.

### 6.3 Phase 0 Transition Checklist

- [ ] sudo fail2ban-client status sshd -> jail active, banned count listed
- [ ] sudo systemctl is-active fail2ban -> active

---

## 7. Safety Domains Assessment

Per AGENTS.md 2 (Consent-Safety Mandate) and 5 (Anti-Pattern Catalog):

| Domain | Touched by P0-005? | Assessment |
|--------|--------------------|------------|
| Persona | ❌ No | Infrastructure step, no persona changes |
| Surveillance | ❌ No | No surveillance endpoints exposed |
| Memory | ❌ No | No memory system changes |
| Consent | ❌ No | No consent mechanisms modified |
| Safety policy | ❌ No | No safety policy changes |
| Encryption | ❌ No | No encryption changes |
| Distress protocol | ❌ No | No distress mechanisms modified |
| Yandere boundary | ❌ No | No persona code touched |
| Agent loop | ❌ No | No loop changes |
| Credentials | ❌ No | No secrets/credentials exposed |
| **Security (host hardening)** | **✅ Critical** | **Host-level intrusion prevention — ADR-018 Layer 2** |

**Verdict:** Outside the most sensitive safety domains, but security-critical. Main safety risk is banning the operator's own IP or disrupting existing fail2ban configuration for Aizanta.

---

## 8. Dependency Analysis

### Prerequisites

| Prerequisite | Status | Verification Method |
|-------------|--------|-------------------|
| P0-004 complete (UFW active) | ✅ Complete | UFW status confirmed: active with SSH+Tailscale |
| fail2ban already installed | ⚠️ Must verify pre-overwrite | Read existing config before writing jail.local |
| Existing fail2ban jails | ⚠️ Must inventory | sudo fail2ban-client status |
| Current ban action | ⚠️ Must verify | sudo fail2ban-client get sshd banaction |
| Operator's SSH IP known | ⚠️ Must identify | Check SSH_CLIENT env or who -m |

### Downstream Consumers

| Step | Depends on P0-005 | Reason |
|------|-------------------|--------|
| P0-006 CrowdSec | ✅ **Yes** | Explicit dependency (StepPrompts line 698) |
| P0-028 Pre-flight verification | ✅ Includes fail2ban check | systemctl is-active fail2ban check |
| P0 Transition Checklist | ✅ Includes fail2ban check | sudo fail2ban-client status sshd check |

---

## 9. Shared Writers & Collision Scan

| Resource | Writer | Conflict Risk |
|----------|--------|--------------|
| /etc/fail2ban/jail.local | P0-005 (writing) | **Exclusive** — but **must read existing first** (fail2ban already installed) |
| /etc/fail2ban/filter.d/ | P0-005 (no filter changes) | Not touched by StepPrompts |
| Systemd (fail2ban service) | P0-005 (enable/start) | Exclusive |
| UFW ruleset | P0-005 (via banaction=ufw) | Shared — fail2ban adds dynamic UFW rules for banned IPs |
| PROGRESS.md | Parent-only | Update after completion |
| CHECKLIST.md | Parent-only | Update after completion |
| StepPrompts.md | Parent-only | Update status |
| docs/setup-evidence/P0/STEP-P0-005/ | P0-005 | Exclusive |

**No file-level collision risk.** Runtime collision: fail2ban's banaction = ufw will add UFW rules dynamically — this interacts with the existing P0-004 ruleset but is the intended behavior.

---

## 10. Blockers & Risks

### 🔴 BLOCKER-1: fail2ban Already Installed — Existing Config Must Be Preserved

**Issue:** The VPS already has fail2ban active with unknown configuration. Overwriting jail.local blindly could:
1. Remove existing jails configured for Aizanta
2. Change ban actions that Aizanta depends on
3. Break the current operational state

**Required pre-flight:**
`ash
# Check current fail2ban status
sudo fail2ban-client status

# Check existing jail.local
cat /etc/fail2ban/jail.local 2>/dev/null || echo "No jail.local"

# List all active jails
sudo fail2ban-client status

# Check current ban action for sshd
sudo fail2ban-client get sshd banaction 2>/dev/null || echo "sshd jail not yet active"

# Check Aizanta-specific jails
sudo fail2ban-client status | grep -i aizanta
`

**Mitigation:** Backup existing fail2ban config before writing jail.local:
`ash
sudo cp -a /etc/fail2ban /etc/fail2ban.backup.
`

### 🔴 BLOCKER-2: Operator IP Whitelist — Risk of Self-Ban

**Issue:** fail2ban with maxretry = 3 and bantime = 86400 could ban the operator's own IP with 3 failed SSH attempts.

**No explicit Samm/Tailscale IP whitelist is documented locally.** The only reference to "Tailscale IP whitelist" in TechnicalArchitecture_v2.0.md is about application-layer auth, not fail2ban.

**Available IP info from P0-004 evidence:**
- VPS Tailscale IP: 100.94.104.22
- Operator workstation Tailscale IP: 100.112.201.124
- SSH port: 22 (public)

**Recommendation:** Add ignoreip with operator's Tailscale IP:
`
ignoreip = 127.0.0.1/8 ::1 100.112.201.124
`
This is safe because Tailscale traffic bypasses UFW anyway, and the operator can always connect via Tailscale SSH.

### 🟡 RISK-3: fail2ban banaction = ufw — Tailscale Limitation

fail2ban with banaction = ufw adds UFW DENY rules. Tailscale's automatic netfilter rules evaluate before UFW rules, so Tailscale SSH is NOT blocked by fail2ban+UFW. This is **acceptable** — Tailscale provides identity-based ACLs, and the operator can always fall back to Tailscale SSH.

### 🟡 RISK-4: P0-006 CrowdSeg May Create Jail Conflicts

CrowdSec (P0-006) will also monitor SSH auth and manage bans. Dual monitoring is valid defense-in-depth but may produce overlapping UFW rules. Document in evidence.

### 🟡 RISK-5: Purge Rollback Is Destructive

StepPrompts rollback includes sudo apt purge -y fail2ban — this would remove fail2ban entirely, affecting any Aizanta jails. **Better rollback:** restore from backup instead of purge.

### 🟡 RISK-6: Journald Log Growth

Using backend = systemd is fine for Ubuntu 24.04. No significant performance concern.

---

## 11. Decision Points for Parent Orchestrator

| # | Decision | Options | Recommended |
|---|----------|---------|-------------|
| 1 | Existing fail2ban config approach | (a) Backup + overwrite, (b) Merge sshd jail into existing, (c) Only add if not exists | **Option (a)** |
| 2 | Operator IP whitelist | (a) ignoreip with Tailscale IP, (b) No whitelist, (c) Whitelist at UFW level | **Option (a)** |
| 3 | Additional jails from DeploymentGuide | (a) Only SSH, (b) Add guinevere-core-auth, (c) Add future jails now | **Option (a)** — core API doesn't exist yet |
| 4 | UFW limit ssh/tcp addition | (a) Add as part of P0-005, (b) Defer | **Option (a)** — complementary |
| 5 | bantime for SSH jail | (a) 86400 (24h), (b) 3600 (1h), (c) 604800 (1 week) | **Option (a)** — 24h standard |
| 6 | Aizanta jails | (a) Do NOT create, (b) Check if Aizanta uses fail2ban | **Option (a)** — Aizanta manages its own security |

---

## 12. Recommended Execution Plan

### Pre-flight (verify on VPS before changes)

`ash
# 1. Check existing fail2ban state
sudo fail2ban-client status
systemctl is-active fail2ban

# 2. Check existing configs
ls -la /etc/fail2ban/
cat /etc/fail2ban/jail.local 2>/dev/null || echo "no jail.local"
sudo fail2ban-client get sshd banaction 2>/dev/null || echo "sshd jail not active"

# 3. Backup existing configuration
sudo cp -a /etc/fail2ban /etc/fail2ban.backup.

# 4. Check operator's current connection IP
echo "SSH_CLIENT: "
who -m

# 5. Confirm UFW active and has allow SSH
sudo ufw status verbose

# 6. Verify Aizanta health BEFORE changes
docker ps --filter "name=aizanta"
`

### Execution (synthesized from StepPrompts + findings)

`ash
# 1. Configure fail2ban with SSH jail
sudo tee /etc/fail2ban/jail.local << 'EOF'
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 3
backend = systemd
banaction = ufw
ignoreip = 127.0.0.1/8 ::1 100.112.201.124

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = %(sshd_log)s
maxretry = 3
bantime = 86400
EOF

# 2. Enable and restart fail2ban
sudo systemctl enable fail2ban
sudo systemctl restart fail2ban

# 3. (Optional) Add UFW rate limiting for defense-in-depth
sudo ufw limit 22/tcp
`

### Verification (post-execution)

`ash
# 1. Service status
systemctl is-active fail2ban                    # Expected: active

# 2. Jail status
sudo fail2ban-client status                     # Expected: shows sshd jail
sudo fail2ban-client status sshd                # Expected: enabled, 0 banned

# 3. Config verification
sudo fail2ban-client get sshd banaction         # Expected: ufw
sudo fail2ban-client get sshd maxretry          # Expected: 3
sudo fail2ban-client get sshd bantime           # Expected: 86400
sudo fail2ban-client get sshd findtime          # Expected: 600

# 4. Aizanta health check
docker ps --filter "name=aizanta"               # Expected: unchanged

# 5. SSH still works (from SECOND terminal)
ssh guinevere-vps "echo 'SSH still works'"

# 6. Check fail2ban logs for errors
sudo journalctl -u fail2ban -n 20 --no-pager
`

---

## 13. Tailscale IP Whitelist Assessment

### 13.1 Is Samm/Tailscale IP Whitelist Documented Anywhere?

**No explicit fail2ban IP whitelist** is documented anywhere in the local repository.

| Source | Content |
|--------|---------|
| TechnicalArchitecture_v2.0.md 7.1 | "JWT + API keys + Tailscale IP whitelist" — application-layer auth, not fail2ban |
| SecurityPolicy_v1.0.md 6 | Network security discussion, no fail2ban whitelist |
| StepPrompts P0-005 | No mention of ignoreip or whitelist |
| IMPLEMENTATION_GUIDE | No mention of IP whitelist in fail2ban section |
| DeploymentGuide 2.2 Step 8 | No IP whitelist in the fail2ban config example |

### 13.2 What Must Be Inferred from P0-004 Evidence

- **VPS Tailscale IP:** 100.94.104.22
- **Operator workstation Tailscale IP:** 100.112.201.124 (from Test-NetConnection in P0-004 verification)
- **Whitelist recommendation:** ignoreip = 127.0.0.1/8 ::1 100.112.201.124

The operator should verify access from each of their devices after implementation.

---

## 14. Evidence Manifest (Recommended)

Following the P0-004 evidence pattern (5-6 files):

| # | File | Content Source |
|---|------|---------------|
| 1 | docs/setup-evidence/P0/STEP-P0-005/p0-005-summary.md | Step summary: what, config details, rollback |
| 2 | docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt | sudo fail2ban-client status + status sshd |
| 3 | docs/setup-evidence/P0/STEP-P0-005/fail2ban-config.txt | cat /etc/fail2ban/jail.local |
| 4 | docs/setup-evidence/P0/STEP-P0-005/aizanta-post-check.md | Aizanta health unchanged post-fail2ban |
| 5 | docs/setup-evidence/P0/STEP-P0-005/verification.md | Full verification report (canonical schema) |
| 6 | audit-reports/P0/STEP-P0-005/step-p0-005-auditor-report.md | Per-step implementation auditor gate |

File naming: docs/setup-evidence/P0/STEP-P0-005/{name} — consistent with prior P0 steps.

---

## 15. Recommended Verification Commands

### Safe (read-only) Commands for Parent to Run

`ash
systemctl status fail2ban
systemctl is-active fail2ban
sudo fail2ban-client status
sudo fail2ban-client status sshd
cat /etc/fail2ban/jail.local 2>/dev/null || cat /etc/fail2ban/jail.conf
sudo fail2ban-client get sshd banaction
docker ps --filter "name=aizanta"
ssh guinevere-vps "echo ok"
`

### Post-Implementation Verification (from Checklist)

`ash
# From CHECKLIST.md line 103:
sudo fail2ban-client status sshd   # jail active, banned count listed

# Extended:
systemctl is-active fail2ban              # active
sudo fail2ban-client get sshd banaction   # ufw
sudo fail2ban-client get sshd maxretry    # 3
sudo fail2ban-client get sshd bantime     # 86400
sudo journalctl -u fail2ban -n 10         # no ERROR entries
`

---

## 16. Verdict Summary

| Dimension | Status |
|-----------|--------|
| **Blocking issues** | **2** (B1: fail2ban already installed with unknown config; B2: operator IP whitelist) |
| **Cross-doc contradictions** | 6 (C1-C6, see 5) |
| **Prerequisites** | P0-004 complete (UFW active); fail2ban already installed on VPS |
| **Shared writer conflicts** | None file-level; fail2ban adds dynamic UFW rules (expected) |
| **ADR compliance** | ADR-018 (Layer 2 Host) aligned; ADR-019 (Tailscale) noted |
| **Safety boundaries** | Outside persona/surveillance/consent/credentials; host-level security |
| **Downstream dependencies** | P0-006 (CrowdSec), P0-028 (pre-flight verification) |
| **Ready for implementation** | **YES — after resolving Blockers 1 and 2** |
| **Need Samm input** | **YES — operator IP whitelist for ignoreip** |

### Pre-Execution Go/No-Go

- [ ] Blocker 1 resolved: existing fail2ban config read and backed up
- [ ] Blocker 2 resolved: operator IP whitelist confirmed with Samm
- [ ] Decision points in 11 settled by parent orchestrator
- [ ] Fresh sudo fail2ban-client status and cat /etc/fail2ban/jail.local verified on VPS
- [ ] Aizanta health snapshot taken before change
- [ ] Backup of existing /etc/fail2ban/ created
- [ ] Rollback commands documented
- [ ] Evidence directory created

---

## 17. Footer

- **Source task:** STEP-P0-005 internal context report (research wave output)
- **Date:** 2026-05-31
- **Implementer:** Guinevere (research phase for parent orchestrator)
- **Validation method:** Cross-document read of 20+ source files, VPS audit data analysis, ADR compliance mapping, collision scan, evidence pattern analysis
- **Report type:** Pre-implementation internal context — read-only, no VPS changes made
- **Downstream:** Parent will synthesize with external fail2ban research before applying any changes
