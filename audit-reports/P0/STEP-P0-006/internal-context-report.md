# STEP-P0-006 — Internal Context Report (Phase 0 Research Synthesis)

**Step:** P0-006 — CrowdSec Setup (Community-Driven Threat Detection)
**Phase:** P0 Infrastructure Foundation (29 steps, step 6 of 29)
**Date:** 2026-05-31
**Status:** ⬜ Not Started (P0-000 through P0-005 complete)
**Scope:** Internal repo/doc/ADR context audit + execution planning
**Report type:** Pre-implementation internal research
**Downstream:** Parent will synthesize with external research

**Source files read (25+ internal):**
- PROGRESS.md, CHECKLIST.md, stepprompts/StepPrompts.md
- docs/IMPLEMENTATION_GUIDE.md, ADR-Index, AC-Catalog, SRS
- adr/ADR-018, ADR-019, ADR-026
- docs/20-security/20-SecurityPolicy_v1.0.md
- docs/40-operations/44-DeploymentGuide_v1.0.md, 45-InternalOpsManual_v1.0.md
- docs/00-core/02-TechnicalArchitecture_v2.0.md
- docs/10-governance/11-FeasibilityStudy_v1.0.md
- All P0-000 and P0-005 evidence files
- P0-004/P0-005 internal-context and auditor reports

**External research already available (same dir):**
- audit-reports/P0/STEP-P0-006/external-crowdsec-ubuntu-report.md
- audit-reports/P0/STEP-P0-006/external-crowdsec-bouncer-report.md

---

## 1. Step Definition (from StepPrompts.md lines 714-793)

| Field | Value |
|-------|-------|
| **Step ID** | P0-006 |
| **Type** | Security |
| **Risk** | Medium |
| **Status** | ⬜ Not Started |
| **Goal** | Install CrowdSec for community-driven threat detection |
| **Dependencies** | P0-005 (fail2ban configured) — ✅ Complete |
| **Cost Impact** | \/month |
| **ADR References** | ADR-018 (Security Architecture) |
| **Acceptance Criteria** | AC-SEC-001 |
| **Estimated Time** | 2 hours |
| **Git Commit** | chore(P0): pending |

### 1.1 Context

CrowdSec complements fail2ban with community-sourced IP reputation data.
It detects attack patterns beyond simple brute force, including port scans,
exploit attempts, and known-bad IPs.

### 1.2 Commands from StepPrompts

Install: curl -s https://install.crowdsec.net | sudo sh
Collections: crowdsecurity/linux, crowdsecurity/sshd, crowdsecurity/nginx
Bouncer: cscli bouncers add guinevere-ufw-bouncer
UFW package: crowdsec-firewall-bouncer-ufw (SEE SECTION 4 - THIS IS WRONG)
Verify: cscli metrics, cscli decisions list

### 1.3 Verification (from StepPrompts)

| Check | Command | Expected |
|-------|---------|----------|
| CrowdSec running | systemctl status crowdsec | active |
| SSH collection | cscli collections list | crowdsecurity/sshd present |
| Bouncer active | cscli bouncers list | guinevere-ufw-bouncer connected |
| Metrics | cscli metrics | parsed events |

### 1.4 Evidence Path (StepPrompts lines 772-773)

| Evidence | Path |
|----------|------|
| Status log | docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt |
| Collections | docs/setup-evidence/P0/STEP-P0-006/crowdsec-collections.txt |

### 1.5 Rollback (from StepPrompts)

Stop services, purge packages, remove /etc/crowdsec directory.
NOTE: package name in StepPrompts rollback is ALSO wrong - see section 4.

### 1.6 Notes

- Shared VPS: CrowdSec monitors ALL traffic, benefiting both Guinevere and Aizanta
- Community blocklists are free. Premium features not required.

---

## 2. Current Tracker State

### 2.1 PROGRESS.md (line 50)

- [ ] P0-006 CrowdSec setup (community-driven threat detection)

Overall: 6/257 (2.3%), P0: 6/29.

### 2.2 CHECKLIST.md (line 104)

- [ ] P0-006: sudo cscli metrics -> CrowdSec engine running, collections loaded

### 2.3 StepPrompts.md status

Line 717: Status: ⬜ Not Started.

### 2.4 Evidence directory

docs/setup-evidence/P0/STEP-P0-006/ — does not exist yet.

### 2.5 P0-005 Completion State

- P0-005 auditor verdict: PASS (auditor report confirmed)
- fail2ban active with 37 banned IPs, UFW ban action
- fail2ban ignoreip: 100.94.104.22 (VPS) and 100.112.201.124 (operator)
- P0-005 caveat: CrowdSec must account for existing fail2ban UFW action

---

## 3. VPS State Baseline

### 3.1 fail2ban State

- 1 jail: sshd, banaction: ufw, 37 IPs currently banned
- Config backup at /etc/fail2ban.backup.p0-005-20260531

### 3.2 UFW State

Active. Default deny incoming. Rules: SSH 22/tcp, Tailscale 41641/udp,
plus 37 fail2ban DENY rules.

### 3.3 Aizanta Services

aizanta-bot, aizanta-nginx (port 80 public), aizanta-frontend,
aizanta-postgres (127.0.0.1:5432), aizanta-redis (127.0.0.1:6379).
All Up 7 days (healthy).

### 3.4 Tailscale State

Version 1.98.3. VPS IP: 100.94.104.22. Operator IP: 100.112.201.124.
Netfilter mode: 'on' (traffic bypasses UFW INPUT chain).

### 3.5 VPS Identity

Hostname: faiz-prod-01. SSH port: 22.

---

## 4. 🔴 CRITICAL: StepPrompts Package Name Error

### The bouncer package crowdsec-firewall-bouncer-ufw DOES NOT EXIST

External research confirms:

| StepPrompts says | Actual package for Ubuntu 24.04 |
|----------------|-------------------------------|
| crowdsec-firewall-bouncer-ufw | crowdsec-firewall-bouncer-iptables |

Ubuntu 24.04 uses nftables (iptables-nft). UFW is a frontend for iptables.
The CrowdSec bouncer uses iptables/nftables natively.
Package crowdsec-firewall-bouncer-ufw was deprecated and removed upstream.

Impact on execution:
- REPLACE all instances of crowdsec-firewall-bouncer-ufw with crowdsec-firewall-bouncer-iptables
- The Rollback purge command must also use the correct package name
- The bouncer label (guinevere-ufw-bouncer) is just a display name - can stay as-is

---


## 5. ADR Constraints & Compliance Mapping

### 5.1 ADR-018 (Security Architecture) — CRITICAL

| Constraint | Impact |
|------------|--------|
| Layer 2: Host intrusion detection | CrowdSec is explicitly listed in defense-in-depth |
| Threat intelligence | Community-driven IP reputation via CrowdSec hub |
| SRS-NFR-014 fulfillment | P0-006 completes the UFW+fail2ban+CrowdSec triad |

P0-006 implements existing ADR-018. No ADR update needed.

### 5.2 ADR-019 (Access Control)

CrowdSec host-level protection complements Tailscale. SSH on port 22 is
temporarily public during P0. CrowdSec adds detection for this transitional state.

### 5.3 SRS-NFR-014

Guinevere must implement UFW + fail2ban + CrowdSec. P0-004 + P0-005 + P0-006
collectively satisfy. P0-006 is the final missing piece for threat intelligence.

---

## 6. Cross-Doc Contradictions & Ambiguities

### 🔴 C1: Package Name Error — StepPrompts vs Reality

| Source | Package |
|--------|---------|
| StepPrompts line 753 | crowdsec-firewall-bouncer-ufw |
| External research | crowdsec-firewall-bouncer-iptables |
| Ubuntu 24.04 reality | iptables-nft (nf_tables backend) |

**Severity: BLOCKING** — apt command will fail. Must correct.

### 🟡 C2: StepPrompts vs DeploymentGuide — Commands

| Aspect | StepPrompts | DeploymentGuide |
|--------|-------------|-----------------|
| Hub update | Not mentioned | cscli hub update |
| Parsers | None | syslog, sshd-logs |
| Service enable | After bouncer | enable --now crowdsec |

**Recommendation:** Augment StepPrompts with hub update and parsers.

### 🟡 C3: CHECKLIST.md Verification Insufficient

CHECKLIST only checks cscli metrics. StepPrompts defines 4 verification checks.
Recommended to expand after implementation.

### 🟡 C4: Evidence Path Incomplete

StepPrompts lists 2 evidence files. Prior P0 convention uses 5-7 files.
See Section 11 for recommended manifest.

### 🟡 C5: nginx Collection + Aizanta Docker nginx

Aizanta nginx runs in Docker. Standard /var/log/nginx/ may not exist.
Must verify log accessibility before installing crowdsecurity/nginx.
Do NOT modify Aizanta Docker config.

### 🟡 C6: Rollback Package Name Mismatch

StepPrompts rollback references crowdsec-firewall-bouncer-ufw.
Must be crowdsec-firewall-bouncer-iptables.

---

## 7. Safety Domains Assessment

| Domain | Touched? | Assessment |
|--------|----------|------------|
| Persona | ❌ No | Infrastructure step |
| Surveillance | ❌ No | No surveillance endpoints |
| Memory | ❌ No | No memory changes |
| Consent | ❌ No | No consent mechanisms |
| Safety policy | ❌ No | No policy changes |
| Encryption | ❌ No | No encryption changes |
| Distress protocol | ❌ No | Not relevant |
| Yandere boundary | ❌ No | Not relevant |
| Agent loop | ❌ No | Not relevant |
| Credentials | ❌ No | Bouncer API key auto-generated locally |
| **Security (IDS)** | ✅ Critical | Host-level ADR-018 Layer 2 |

**Safety risk summary:**
1. Package name error - apt install will fail if not corrected
2. Operator IP self-ban if whitelist not configured
3. CrowdSec RAM (~200MB) on shared VPS
4. Docker ports bypass UFW bans (pre-existing)
5. Aizanta nginx log access for crowdsecurity/nginx collection

---

## 8. Dependency Analysis

### Prerequisites

| Prerequisite | Status | Verification |
|-------------|--------|-------------|
| P0-005 complete | ✅ PASS | fail2ban active, 37 bans, auditor PASS |
| UFW active | ✅ P0-004 | SSH + Tailscale only |
| Internet access | ⚠️ Verify | curl to packagecloud.io |
| RAM: 200MB free | ⚠️ Verify | free -h |
| Disk: 500MB free | ⚠️ Verify | df -h / |
| Aizanta running | ✅ | 5 containers Up 7 days |

### Downstream Consumers

| Consumer | Dependency |
|----------|-----------|
| P0 Transition Checklist | CHECKLIST line 104 (cscli metrics) |
| P0-028 Pre-flight | Checks all P0 services |
| OpsManual health | Lists crowdsec as monitored service |
| SRS-NFR-014 | P0-006 completes the triad |

### Adjacent Steps (Independent)

P0-007 (Swap), P0-022 (Tailscale already active), P0-023 (Cloudflare) — 
no dependency on P0-006.

---

## 9. Shared Writers & Collision Scan

| Resource | Writers | Conflict? |
|----------|---------|-----------|
| /etc/crowdsec/ | P0-006 | Exclusive - new install |
| /etc/crowdsec/acquis.yaml | P0-006 | Exclusive |
| /etc/crowdsec/parsers/ | P0-006 | Exclusive |
| UFW ruleset | P0-004 (base), P0-005 (fail2ban), P0-006 (CS bouncer) | ⚠️ Shared - acceptable defense-in-depth |
| systemd services | crowdsec.service, crowdsec-firewall-bouncer.service | Exclusive - new |
| /home/guinevere/ | Not touched | CrowdSec is system-level |
| PROGRESS.md | Parent-only | Post-step update |
| CHECKLIST.md | Parent-only | Post-step update |
| StepPrompts.md | Parent-only | Status update |
| Evidence dir | P0-006 | Exclusive |

**No file-level collision.** Runtime UFW overlap with fail2ban is acceptable.

---

## 10. Blockers & Risks

### 🔴 BLOCKER-1: Wrong Bouncer Package Name

**Issue:** crowdsec-firewall-bouncer-ufw does not exist.
**Fix:** Use crowdsec-firewall-bouncer-iptables for Ubuntu 24.04.

### 🔴 BLOCKER-2: Operator IP Self-Ban Risk

**Issue:** CrowdSec may ban operator/VPS Tailscale IPs via community blocklists.
**Fix:** Create CrowdSec allowlist BEFORE enabling bouncer.
IPs to whitelist: 127.0.0.1/8, ::1, 100.94.104.22 (VPS), 100.112.201.124 (operator).

### 🟡 RISK-3: nginx Collection + Docker nginx

Aizanta nginx runs in Docker. Standard log path may not exist.
Do NOT modify Aizanta config. Skip nginx collection if logs inaccessible.

### 🟡 RISK-4: CrowdSec RAM (~200MB)

Manageable on 16GB VPS. Verify with free -h post-install.
Reduce collection count if >300MB.

### 🟡 RISK-5: Docker Published Ports Bypass

Pre-existing constraint (P0-004). Docker ports bypass UFW INPUT chain.
CrowdSec detects via logs but bans may not block Docker traffic.
Acceptable for P0.

### 🟡 RISK-6: Aizanta Health Check

Pre/post verification required: docker ps, systemctl, ss -tlnp.

### 🟡 RISK-7: Bouncer API Key Must Be Captured

cscli bouncers add prints key once. If lost, bouncer can't connect.
Capture in evidence (sensitive, not exposed in reports).

---

## 11. Decision Points for Parent

| # | Decision | Options | Recommended |
|---|----------|---------|-------------|
| 1 | Bouncer package | (a) ufw (WRONG - StepPrompts), (b) iptables (correct) | (b) |
| 2 | IP whitelist method | (a) cscli allowlists, (b) Parser YAML | (a) - modern, auditable |
| 3 | nginx collection | (a) install, (b) skip, (c) check first | (c) - verify log path first |
| 4 | Additional parsers | (a) only StepPrompts, (b) add syslog+sshd-logs | (b) - better detection |
| 5 | Evidence file count | (a) 2 files (StepPrompts), (b) full set (5-7) | (b) - match P0 convention |
| 6 | Hub update | (a) run, (b) skip | (a) - ensures latest collections |
| 7 | Bouncer display name | (a) guinevere-ufw-bouncer, (b) guinevere-iptables-bouncer | (a) - cosmetic, keep consistency |

---

## 12. Recommended Execution Plan (Synthesized)

### Stage 1: Pre-flight (read-only VPS checks)

Verify P0-005: systemctl is-active fail2ban, sudo fail2ban-client status sshd
Check RAM: free -h (need ~200MB free)
Check disk: df -h / (need ~500MB free)
Baseline UFW: sudo ufw status verbose
Baseline Aizanta: docker ps --filter name=aizanta, ss -tlnp
Check nginx logs: ls -la /var/log/nginx/ 2>/dev/null
Check iptables backend: iptables -V (expect nf_tables)
Verify internet: curl -s --connect-timeout 5 https://install.crowdsec.net

### Stage 2: Installation

1. Install CrowdSec: curl -s https://install.crowdsec.net | sudo sh
2. Verify: cscli version
3. Update hub: sudo cscli hub update
4. Install collections: sudo cscli collections install crowdsecurity/linux, crowdsecurity/sshd
5. Install parsers: sudo cscli parsers install crowdsecurity/syslog, crowdsecurity/sshd-logs
6. Enable engine: sudo systemctl enable --now crowdsec
7. Create allowlist via cscli allowlists for VPS+operator IPs
8. Add bouncer: sudo cscli bouncers add guinevere-ufw-bouncer [CAPTURE KEY]
9. Install bouncer: sudo apt install -y crowdsec-firewall-bouncer-iptables
10. Enable bouncer: sudo systemctl enable --now crowdsec-firewall-bouncer

### Stage 3: Verification

systemctl is-active crowdsec -> active
systemctl is-active crowdsec-firewall-bouncer -> active
sudo cscli metrics -> engine running, collections loaded
sudo cscli collections list -> linux, sshd present
sudo cscli bouncers list -> guinevere-ufw-bouncer connected
sudo cscli allowlists inspect guinevere-whitelist -> IPs present
sudo fail2ban-client status sshd -> still active, bans preserved
sudo ufw status verbose -> base rules intact
docker ps --filter name=aizanta -> all 5 healthy
ssh guinevere-vps echo OK -> SSH works
free -h -> CrowdSec within ~200MB
sudo journalctl -u crowdsec -n 10 --no-pager -> no errors

---

## 13. Evidence Manifest (Recommended)

Following prior P0 convention (P0-005 had 7 files):

| # | File | Content | In StepPrompts? |
|---|------|---------|----------------|
| 1 | docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt | systemctl status + cscli metrics | ✅ Yes |
| 2 | docs/setup-evidence/P0/STEP-P0-006/crowdsec-collections.txt | collections list + bouncers list | ✅ Yes |
| 3 | docs/setup-evidence/P0/STEP-P0-006/verification.md | Full verification report | ❌ Recommended |
| 4 | docs/setup-evidence/P0/STEP-P0-006/p0-006-summary.md | Summary, decisions, rollback | ❌ Recommended |
| 5 | docs/setup-evidence/P0/STEP-P0-006/aizanta-post-check.md | Aizanta health unchanged | ❌ Recommended |
| 6 | docs/setup-evidence/P0/STEP-P0-006/coexistence-proof.md | fail2ban + CrowdSec both active | ❌ Recommended |
| 7 | audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md | Independent auditor gate | ❌ Mandatory per AGENTS.md |

---

## 14. Post-Step Tracker Sync

| Tracker | Change | Expected Value |
|---------|--------|---------------|
| PROGRESS.md line 12 | Completed counter | 7 / 257 (2.7%) |
| PROGRESS.md line 27 | P0 count | 7/29 |
| PROGRESS.md line 50 | P0-006 checkbox | [x] |
| CHECKLIST.md line 104 | P0-006 checkbox | [x] |
| StepPrompts.md line 717 | Status | ✅ Completed |
| StepPrompts.md pre-flight | All checks | [x][x][x] |
| StepPrompts.md verification | All checks | [x][x][x][x] |

---

## 15. Recommended Verification Commands (Read-Only for Parent)

### CrowdSec checks
systemctl is-active crowdsec
systemctl is-active crowdsec-firewall-bouncer
sudo cscli metrics
sudo cscli collections list
sudo cscli bouncers list
sudo cscli decisions list
sudo cscli allowlists inspect guinevere-whitelist

### Coexistence with fail2ban
systemctl is-active fail2ban
sudo fail2ban-client status sshd

### Network state
sudo ufw status verbose
ssh guinevere-vps echo ok

### Aizanta unchanged
docker ps --filter name=aizanta

### Memory
free -h

### Logs (no errors)
sudo journalctl -u crowdsec -n 10 --no-pager
sudo journalctl -u crowdsec-firewall-bouncer -n 10 --no-pager

---

## 16. Verdict Summary

| Dimension | Status |
|-----------|--------|
| **Blocking issues** | **2** (B1: package name error; B2: operator IP whitelist) |
| **Cross-doc contradictions** | 6 (C1-C6, see Section 6) |
| **StepPrompts package error** | **🔴 crowdsec-firewall-bouncer-ufw is WRONG. Must be crowdsec-firewall-bouncer-iptables** |
| **Prerequisites** | P0-005 complete ✅; UFW active ✅; RAM/disk to verify |
| **Shared writer conflicts** | None file-level; UFW runtime shared with fail2ban (acceptable) |
| **ADR compliance** | ADR-018 aligned ✅ |
| **Safety boundaries** | Outside persona/surveillance/consent; host-level security |
| **Downstream dependencies** | CHECKLIST, P0-028, OpsManual health checks |
| **Ready for implementation** | **YES — after resolving both blockers** |
| **Need Samm input** | **NO** — IPs documented from P0-005 evidence |

### Pre-Execution Go/No-Go Checklist

- [ ] Blocker 1 resolved: use crowdsec-firewall-bouncer-iptables
- [ ] Blocker 2 resolved: CrowdSec allowlist created for operator/VPS IPs
- [ ] StepPrompts package name corrected in all commands and rollback
- [ ] Fresh free -h and df -h / verified on VPS
- [ ] nginx log path checked before installing collection
- [ ] Aizanta health snapshot taken before change
- [ ] fail2ban state snapshot taken before change
- [ ] UFW baseline snapshot taken before change
- [ ] Bouncer API key capture prepared
- [ ] Evidence directory created
- [ ] Rollback commands documented (correct package name)

---

## 17. Footer

- **Source task:** STEP-P0-006 internal context report (research wave output)
- **Date:** 2026-05-31
- **Implementer:** Guinevere (research phase for parent orchestrator)
- **Validation method:** Cross-document read of 25+ internal source files + 2 external research reports
- **Report type:** Pre-implementation internal context — read-only, no VPS changes made
- **Downstream:** Parent will synthesize this internal report with the two external research reports in the same directory before applying any changes
- **Key finding for parent:** The StepPrompts contains a BLOCKING package name error (crowdsec-firewall-bouncer-ufw does not exist). External research reports have the correct package name (crowdsec-firewall-bouncer-iptables) and detailed installation procedure.

