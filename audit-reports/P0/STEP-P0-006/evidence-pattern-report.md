# STEP-P0-006 Evidence & Status Sync Pattern Report

**Step:** P0-006 -- CrowdSec Setup (Community-Driven Threat Detection)
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Purpose:** Document exact evidence/tracker sync patterns from prior P0 steps (P0-003 through P0-005) to inform STEP-P0-006 evidence creation, verification schema, auditor gate, and counter updates.
**Scope:** Read-only pattern analysis -- no files modified.

---

## 1. Evidence Location Convention

### Canonical Path Pattern (CONFIRMED -- ALL PRIOR STEPS)

The canonical evidence path for all P0 steps, used consistently by **every executed step** (P0-000 through P0-005):

```
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
```

For P0-006 specifically:

| Component | Value |
|-----------|-------|
| Step evidence root | \docs/setup-evidence/P0/STEP-P0-006/\ |
| Auditor report root | \udit-reports/P0/STEP-P0-006/\ |

**Confirmed:** This pattern is used by all executed P0 steps. No conflict remains -- CHECKLIST.md's old \evidence/phase-N/\ convention is outdated and was already ruled out in prior evidence-pattern reports (P0-004, P0-005).

---

## 2. Prior P0 Evidence Artifacts -- Exact Inventory

### 2.1 STEP-P0-000 (VPS Audit) -- 3 files

| File | Path | Purpose |
|------|------|---------|
| \p0-000-summary.md\ | \docs/setup-evidence/P0/STEP-P0-000/p0-000-summary.md\ | Summary: what was audited, key findings, outcome |
| \service-inventory.md\ | \docs/setup-evidence/P0/STEP-P0-000/service-inventory.md\ | Aizanta services, ports, running containers |
| \ps-audit-2026-05-31.txt\ | \docs/setup-evidence/P0/STEP-P0-000/vps-audit-2026-05-31.txt\ | Raw audit output log |

### 2.2 STEP-P0-001 (Guinevere Linux User) -- 4 files

| File | Path | Purpose |
|------|------|---------|
| \p0-001-summary.md\ | \docs/setup-evidence/P0/STEP-P0-001/p0-001-summary.md\ | Summary: what was done, files changed, security boundary, rollback |
| \user-creation.log\ | \docs/setup-evidence/P0/STEP-P0-001/user-creation.log\ | User creation command outcomes, uid/gid, home dir |
| \sudoers-config.txt\ | \docs/setup-evidence/P0/STEP-P0-001/sudoers-config.txt\ | Full rule text, visudo validation, sudo -l output |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-001/aizanta-post-check.md\ | Post-action Aizanta health check |

### 2.3 STEP-P0-002 (SSH Config Update) -- 6 files

| File | Path | Purpose |
|------|------|---------|
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-002/verification.md\ | Comprehensive verification report (362 lines, canonical template -- first introduced) |
| \p0-002-summary.md\ | \docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md\ | Summary: what, files changed, security boundary, rollback |
| \ssh-test.log\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-test.log\ | Connection test outputs |
| \ssh-config.txt\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt\ | Local ~/.ssh/config content |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md\ | Post-action Aizanta health check |
| \ssh-hardening-summary.md\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md\ | VPS-side SSH hardening details |

### 2.4 STEP-P0-003 (Directory Structure) -- 5 files

| File | Path | Purpose |
|------|------|---------|
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-003/verification.md\ | Comprehensive verification report (357 lines, refined schema) |
| \p0-003-summary.md\ | \docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md\ | Summary: what, paths, safety, rollback |
| \directory-tree.txt\ | \docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt\ | \ind /home/guinevere -type d | sort\ output |
| \permissions.txt\ | \docs/setup-evidence/P0/STEP-P0-003/permissions.txt\ | Ownership and permission capture for all dirs |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md\ | Post-action Aizanta health check |

### 2.5 STEP-P0-004 (UFW Firewall Rules) -- 6 files

| File | Path | Purpose |
|------|------|---------|
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-004/verification.md\ | Comprehensive verification report (468 lines, refined schema with dry-run proof) |
| \p0-004-summary.md\ | \docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md\ | Summary: what, rules, boundary, rollback |
| \ufw-status.txt\ | \docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt\ | Baseline, dry-run, applied rule, final UFW state, \ufw show added\ |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md\ | Aizanta containers + ports + HTTP before and after |
| \port-scan.txt\ | \docs/setup-evidence/P0/STEP-P0-004/port-scan.txt\ | nmap unavailable proof + Test-NetConnection fallback results |
| \
map-scan.png\ | \docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png\ | Screenshot-style artifact documenting fallback scan |

### 2.6 STEP-P0-005 (fail2ban Configuration) -- 7 files

| File | Path | Purpose |
|------|------|---------|
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-005/verification.md\ | Comprehensive verification report (336 lines, canonical 12-section schema) |
| \p0-005-summary.md\ | \docs/setup-evidence/P0/STEP-P0-005/p0-005-summary.md\ | Implementation summary, boundary, rollback |
| \ail2ban-status.txt\ | \docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt\ | StepPrompts requirement: fail2ban service/jail/config dump |
| \ail2ban-jail-config.txt\ | \docs/setup-evidence/P0/STEP-P0-005/fail2ban-jail-config.txt\ | Runtime drop-in content, Aizanta config preservation |
| \ail2ban-whitelist-proof.txt\ | \docs/setup-evidence/P0/STEP-P0-005/fail2ban-whitelist-proof.txt\ | ignoreip safety proof for localhost/VPS/operator Tailscale IPs |
| \ail2ban-test.log\ | \docs/setup-evidence/P0/STEP-P0-005/fail2ban-test.log\ | Safe TEST-NET ban/unban proof and cleanup |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-005/aizanta-post-check.md\ | Aizanta containers + ports health after P0-005 |

### 2.7 Pattern Observations Across All P0 Steps

| Aspect | Pattern |
|--------|---------|
| Summary file naming | \p0-{XXX}-summary.md\ |
| Aizanta health check | \izanta-post-check.md\ -- always included after infrastructure changes |
| Raw log/command output | \.txt\ or \.log\ extension |
| Structured documentation | \.md\ extension |
| Verification report | \erification.md\ -- standard since P0-002, carried forward |
| Evidence file count | 3-7 files per step, growing with complexity |
| Pre/post state capture | Before-state AND after-state captured for all mutable operations |
| StepPrompts-required file | Single file per StepPrompts (ufw-status.txt, fail2ban-status.txt) |
| verification.md file size | 336-468 lines, growing with complexity |

---

## 3. verification.md Schema Analysis

The \erification.md\ file was introduced in P0-002 and refined through P0-003, P0-004, and P0-005. It is the **canonical verification schema** for all P0 infrastructure steps.

### Canonical Schema Sections (12 sections, all required)

| # | Section | Content | Required? |
|---|---------|---------|-----------|
| 1 | **Header** | Step, Date, Host, Status (PASS after auditor gate), Implementer | Required |
| 2 | **What Was Done** | Narrative of actions taken, blockers discovered, fixes applied | Required |
| 3 | **Files Changed** | Local machine files + VPS files (both created and touched) | Required |
| 4 | **Validation Results** | Commands, exact outputs, PASS/FAIL for each verification point | Required |
| 5 | **Evidence Artifacts** | List of all evidence/audit files produced | Required |
| 6 | **Shared VPS Impact** | Aizanta containers + protected ports before and after changes | Required |
| 7 | **ADR Compliance** | ADR-014, ADR-015, ADR-018, ADR-019 checks (relevant to step) | Required |
| 8 | **AC Reference** | AC items satisfied by this step | Required |
| 9 | **Rollback / Re-run Safety** | Rollback commands, idempotency notes | Required |
| 10 | **Design Decisions / Caveats** | Rationale for deferrals, deviations from StepPrompts | Required |
| 11 | **Evidence Gate** | Parent verification summary + independent auditor verdict + report path | Required |
| 12 | **Footer** | Source task, date, implementer, validation method | Required |

### What verification.md Does NOT Include

- StepPrompts checkbox state (checked in auditor report instead)
- Status sync counter details (checked in auditor report)
- Introduced vs pre-existing diagnostics split (checked in auditor report)
- LSP diagnostics raw output (checked in auditor report)

### P0-004/P0-005 Refinements Worth Carrying Forward

| Refinement | Description |
|------------|-------------|
| Before/after baseline capture | Pre-change state captured (containers, ports, SSH) before any VPS mutation |
| Dry-run proof | \ufw --dry-run\ output captured before applying (P0-004) |
| Idempotency verification | Re-run command shows idempotent behavior |
| Tooling fallback documentation | Transparently documented when tooling unavailable |
| Preserve-existing approach | Documented why fresh install/purge was skipped (P0-005) |
| Safe test-and-cleanup | TEST-NET IP ban/unban with cleanup proof |
| Whitelist/safety proof | Operator IP whitelisted in fail2ban to prevent lockout |

---

## 4. Status / Counter Update Patterns

### 4.1 Current State (Pre-P0-006) -- From PROGRESS.md

| Counter | Current Value |
|---------|---------------|
| Total completed | **6 / 257 (2.3%)** |
| P0 phase count | **6/29** |
| P0-006 checkbox (line 50) | \- [ ]\ unchecked |

### 4.2 Expected State (Post-P0-006)

| Counter | Value | Calculation |
|---------|-------|-------------|
| Total completed | **7 / 257 (2.7%)** | 6 + 1 = 7; 7/257 = 2.723% truncated to 2.7% |
| P0 phase count | **7/29** | 6 + 1 = 7 |

### 4.3 PROGRESS.md Update Pattern

| Element | Line | Current | Expected After P0-006 |
|---------|------|---------|----------------------|
| P0-006 checkbox | 50 | \- [ ] **P0-006** CrowdSec setup ...\ | \- [x] **P0-006** CrowdSec setup ...\ |
| Total completed | 12 | \6 / 257 (2.3%)\ | \7 / 257 (2.7%)\ |
| P0 phase count | 27 | \6/29\ | \7/29\ |

**Counter math verification:**
- Previous total: 6 (P0-000 through P0-005)
- After P0-006: 7
- Percentage: 7/257 = 2.7237% truncates to **2.7%**
- Phase P0: 7/29

### 4.4 CHECKLIST.md Update Pattern

| Element | Line | Current | Expected After P0-006 |
|---------|------|---------|----------------------|
| P0-006 verification | 104 | \- [ ] P0-006: sudo cscli metrics\ | \- [x] P0-006: sudo cscli metrics\ |

### 4.5 StepPrompts.md Update Pattern

**P0-006 entry spans lines 714-793 in StepPrompts.md.**

| Element | Line | Current | Expected After P0-006 |
|---------|------|---------|----------------------|
| Status field | 717 | \ Not Started\ | \ Completed\ |
| Pre-flight 1 (P0-005 complete) | 732 | [x] P0-005 complete | Already checked |
| Pre-flight 2 (Sufficient RAM) | 733 | [ ] Sufficient RAM | [x] Sufficient RAM |
| Pre-flight 3 (Internet access) | 734 | [ ] Internet access | [x] Internet access |
| Verification 1 (CrowdSec running) | 766 | [ ] CrowdSec running | [x] CrowdSec running |
| Verification 2 (SSH collection) | 767 | [ ] SSH collection installed | [x] SSH collection installed |
| Verification 3 (Bouncer active) | 768 | [ ] Bouncer active | [x] Bouncer active |
| Verification 4 (Metrics available) | 769 | [ ] Metrics available | [x] Metrics available |

Note: Pre-flight 1 (P0-005 complete, line 732) is already checked by the P0-005 follow-up audit.

### 4.6 Cross-Tracker Consistency Must-Haves

All three trackers must be updated **atomically**:

1. **PROGRESS.md** -- checkbox (line 50) + total counter (6 to 7, line 12) + phase counter (6/29 to 7/29, line 27)
2. **CHECKLIST.md** -- step verification checkbox (line 104)
3. **stepprompts/StepPrompts.md** -- status to Completed + all 6 checkboxes

---

## 5. StepPrompts P0-006 -- Exact Reference

From \stepprompts/StepPrompts.md\ lines 714-793:

### Step Metadata

| Field | Value |
|-------|-------|
| Type | Security |
| Status | Not Started |
| Risk | Medium |
| Goal | Install CrowdSec for community-driven threat detection and collaborative IP reputation |
| Dependencies | P0-005 (fail2ban configured) |
| Cost Impact | /month |
| ADR References | ADR-018 |
| Acceptance Criteria | AC-SEC-001 |
| Estimated Time | 2 hours |

### Pre-flight Checks (lines 732-734)

1. [x] P0-005 complete (already checked by P0-005 follow-up audit)
2. [ ] Sufficient RAM (CrowdSec ~200MB)
3. [ ] Internet access for downloading CrowdSec

### Commands (lines 737-762)

```bash
# Install CrowdSec
curl -s https://install.crowdsec.net | sudo sh

# Verify installation
cscli version

# Install essential collections
sudo cscli collections install crowdsecurity/linux
sudo cscli collections install crowdsecurity/sshd
sudo cscli collections install crowdsecurity/nginx

# Install UFW bouncer
sudo cscli bouncers add guinevere-ufw-bouncer
sudo cscli bouncers list

# Install crowdsec-firewall-bouncer
sudo apt install -y crowdsec-firewall-bouncer-ufw

# Configure bouncer
sudo systemctl enable crowdsec-firewall-bouncer
sudo systemctl start crowdsec-firewall-bouncer

# Verify
sudo cscli metrics
sudo cscli decisions list
```

### Verification Checks (lines 766-769)

1. [ ] CrowdSec running -- \systemctl status crowdsec\ shows active
2. [ ] SSH collection installed -- \cscli collections list\ shows crowdsecurity/sshd
3. [ ] Bouncer active -- \cscli bouncers list\ shows guinevere-ufw-bouncer connected
4. [ ] Metrics available -- \cscli metrics\ shows parsed events

### StepPrompts Evidence requirement (lines 772-773)

- Log: \docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt\"
WL 

### StepPrompts Rollback (lines 776-780)

```bash
sudo systemctl stop crowdsec crowdsec-firewall-bouncer
sudo apt purge -y crowdsec crowdsec-firewall-bouncer-ufw
sudo rm -rf /etc/crowdsec
```

---

## 6. Command-Output Capture Expectations

Based on prior patterns, each verification command in P0-006 must be executed and its **exact output** captured in evidence:

| # | Verification Point | Where Captured |
|---|-------------------|----------------|
| 1 | P0-005 complete | verification.md + aizanta-post-check.md |
| 2 | CrowdSec installed | crowdsec-status.txt |
| 3 | CrowdSec service active | crowdsec-status.txt |
| 4 | SSH collection | crowdsec-collections.txt |
| 5 | Linux collection | crowdsec-collections.txt |
| 6 | nginx collection | crowdsec-collections.txt |
| 7 | Bouncer registered | crowdsec-status.txt |
| 8 | Metrics available | crowdsec-status.txt |
| 9 | Decisions list | crowdsec-status.txt |
| 10 | UFW rules intact | verification.md |
| 11 | Aizanta containers | aizanta-post-check.md |
| 12 | Protected ports | aizanta-post-check.md |
| 13 | Fail2ban still active | verification.md |
| 14 | SSH still works | verification.md |

### Safety Commands (Pre-Change Baseline -- MUST capture before installing CrowdSec)

| Command | Purpose |
|---------|---------|
| ssh guinevere-vps whoami && hostname | SSH access baseline |
| docker ps | grep aizanta | Aizanta container baseline |
| ss -tlnp | grep -E 5432/6379/80 | Protected port baseline |
| ufw status verbose | UFW rule baseline |
| fail2ban-client status sshd | fail2ban baseline |

---

## 7. Recommended Evidence Artifacts for STEP-P0-006

### StepPrompts Minimum (2 files required by StepPrompts lines 772-773)

| # | File | Purpose |
|---|------|---------|
| 1 | crowdsec-status.txt | StepPrompts requirement: version, service status, bouncer list, metrics, decisions |
| 2 | crowdsec-collections.txt | StepPrompts requirement: cscli collections list output |

### Canonical Evidence (Based on Prior P0 Pattern Convergence)

| # | File | Purpose | Precedent |
|---|------|---------|-----------|
| 3 | verification.md | Full canonical 12-section verification report | P0-002 through P0-005 |
| 4 | p0-006-summary.md | Implementation summary, boundary, rollback | All prior steps |
| 5 | aizanta-post-check.md | Aizanta containers + ports + HTTP unchanged | Always after infrastructure change |

### Recommended for CrowdSec-Specific Evidence Quality

| # | File | Purpose | Rationale |
|---|------|---------|-----------|
| 6 | crowdsec-bouncer-proof.txt | Bouncer API key + connection status, crowdsec-firewall-bouncer service state | P0-005 fail2ban-test.log precedent |
| 7 | crowdsec-rollback-test.txt | Rollback command verification | P0-005 fail2ban-whitelist-proof.txt precedent |

### File Naming Convention

All files go under: docs/setup-evidence/P0/STEP-P0-006/

| Pattern | Extension | Use Case |
|---------|-----------|----------|
| p0-006-*.md | .md | Structured documentation |
| crowdsec-*.txt | .txt | Raw command output, log captures |
| verification.md | .md | Canonical verification report |
| aizanta-post-check.md | .md | Aizanta health check |

### Total Evidence Files: 7 recommended

---

## 8. Audit Report Files for STEP-P0-006

### Pre-Implementation Reports

Based on prior P0 patterns:

| # | File | Purpose | When Created |
|---|------|---------|-------------|
| 1 | evidence-pattern-report.md | (this file) evidence/tracker sync pattern analysis | Before implementation |
| 2 | internal-context-report.md | Pre-implementation: StepPrompts analysis, tracker state, ADR constraints, collision scan | Before implementation |
| 3 | external-crowdsec-setup-report.md | External research: CrowdSec install guide, UFW bouncer config, shared VPS safety | Before implementation |
| 4 | step-p0-006-auditor-report.md | Per-step independent implementation auditor gate | After implementation + parent verification |

### Auditor Report Schema (from P0-005 auditor report, 417 lines -- the most mature precedent)

| # | Section | Content |
|---|---------|---------|
| 1 | Header + Verdict | Report type, step, phase, date, auditor, parent claim, verdict |
| 2 | Scope & Method | Files read table, live SSH checks table, LSP diagnostics |
| 3 | DoD Verification Matrix | Criterion, source, PASS/FAIL (with evidence column) |
| 4 | Live CrowdSec State Verification | Independent live checks: service status, collections, bouncer, metrics |
| 5 | Implementation Rationale | Deviations from StepPrompts with justification |
| 6 | Parent Verification Cross-Check | Parent claims vs independent verification |
| 7 | Secrets & Safety Scan | Pattern scan for token, key, password, api_key in evidence |
| 8 | Boundary Compliance | Persona/consent/surveillance/Y6/HARD STOP table |
| 9 | Operator IP Safety | Whitelist check, no operator IP in test data |
| 10 | Cross-Doc Consistency Check | PROGRESS.md, CHECKLIST.md, StepPrompts.md status tables |
| 11 | Findings | Blocking (0 expected) + non-blocking with recommendations |
| 12 | Shared VPS Safety -- Aizanta | Container/port/HTTP verification |
| 13 | Summary | Dimension table + overall verdict box |
| 14 | Evidence Artifacts Inventory | All file paths with line counts |
| 15 | Footer | Source, date, auditor, validation method, verdict |

---

## 9. Exact Line Reference Table for Tracker Edits

| Tracker | Element | Line | Change |
|---------|---------|------|--------|
| PROGRESS.md | P0-006 checkbox | 50 | - [ ] to - [x] |
| PROGRESS.md | Total completed | 12 | 6/257 (2.3%) to 7/257 (2.7%) |
| PROGRESS.md | P0 phase count | 27 | 6/29 to 7/29 |
| CHECKLIST.md | P0-006 verification | 104 | - [ ] to - [x] |
| stepprompts/StepPrompts.md | Status field | 717 | Not Started to Completed |
| stepprompts/StepPrompts.md | Pre-flight 2 (RAM) | 733 | [ ] to [x] |
| stepprompts/StepPrompts.md | Pre-flight 3 (Internet) | 734 | [ ] to [x] |
| stepprompts/StepPrompts.md | Verification 1 | 766 | [ ] to [x] |
| stepprompts/StepPrompts.md | Verification 2 | 767 | [ ] to [x] |
| stepprompts/StepPrompts.md | Verification 3 | 768 | [ ] to [x] |
| stepprompts/StepPrompts.md | Verification 4 | 769 | [ ] to [x] |

Note: Pre-flight 1 (P0-005 complete, line 732) is already checked.

---

## 10. Files to NOT Touch

| File/Directory | Reason |
|----------------|--------|
| docs/setup-evidence/P0/STEP-P0-000 through STEP-P0-005 | Prior step evidence, read-only |
| audit-reports/P0/STEP-P0-002 through STEP-P0-005 | Prior audit reports, read-only |
| adr/ | No ADR changes required for P0-006 |
| VPS runtime config (/etc/crowdsec/, /etc/fail2ban/, UFW state) | Server-side; captured in evidence logs only |
| docs/README.md | Not in scope for this step |
| AGENTS.md | Not in scope for this step |

---

## 11. Patterns That MUST Be Avoided -- Anti-Patterns from Prior Steps

### ANTI-PATTERN 1: Fake or Placeholder Fallback Evidence

**Observed in:** P0-004 (nmap-scan.png was a screenshot of Test-NetConnection fallback, not a real nmap scan).

**Rule for P0-006:** If a tool is unavailable (e.g., cscli not found on local workstation), do NOT create fake evidence. Instead:
- Document the unavailable tool transparently.
- Run the commands on the VPS via SSH and capture output as .txt.
- If cscli metrics shows zero decisions initially (fresh install), document that as expected -- do NOT fabricate artificial data.

### ANTI-PATTERN 2: Destructive Broad Operations Without Shared-VPS Safety

**Observed in:** StepPrompts draft for P0-004 included sudo ufw --force reset which would have disrupted Aizanta.

**Rule for P0-006:** The StepPrompts Rollback (sudo apt purge -y crowdsec + sudo rm -rf /etc/crowdsec) is destructive. Before executing:
- Verify Aizanta containers are healthy first.
- Do NOT purge if Aizanta depends on CrowdSec (unlikely, but verify).
- Document the rollback path with Aizanta safety checks preceding each destructive step.

### ANTI-PATTERN 3: Overwriting Existing Service Config Without Preserving Backups

**Observed in:** P0-005 existing fail2ban was preserved via backup (/etc/fail2ban.backup) and a late-loading drop-in instead of jail.local.

**Rule for P0-006:** CrowdSec installs via curl | sudo sh which may modify existing config. Before installation:
- Take a backup of /etc/ or relevant config directories.
- If cscli collections or existing bouncers are already configured, catalog them first.
- Use --dry-run if available.

### ANTI-PATTERN 4: Operator IP Used for Test/Destructive Actions

**Observed in:** P0-005 explicitly used RFC 5737 TEST-NET IP 198.51.100.99 for ban testing, never the operator's Tailscale IP.

**Rule for P0-006:** Do NOT use the operator's Tailscale IP (100.112.201.124) or VPS Tailscale IP (100.94.104.22) as test IPs in CrowdSec decisions or bouncer tests.

### ANTI-PATTERN 5: Silent Deviation From StepPrompts Without Documentation

**Observed in:** P0-004 and P0-005 both deviated from StepPrompts -- both were documented in verification.md Design Decisions/Caveats.

**Rule for P0-006:** If the actual implementation deviates from StepPrompts commands, document the deviation explicitly in verification.md. Do NOT silently follow or silently deviate.

### ANTI-PATTERN 6: Claiming Success Without Live Verification

**Observed in:** All prior P0 steps performed live SSH commands to verify runtime state. No step relied solely on theoretical claims.

**Rule for P0-006:** Every verification point in verification.md must include the exact command run and its exact output.







| ADR | Relevance | Expected Compliance |
|-----|-----------|---------------------|
| ADR-014 (Shared VPS) | CrowdSec runs system-wide, protects both Guinevere and Aizanta | Document that CrowdSec is additive, does not modify Aizanta services |
| ADR-018 (Defense-in-Depth) | CrowdSec adds community-driven threat detection | Aligned -- complements fail2ban as second detection layer |
| ADR-019 (Access Control) | UFW bouncer interacts with existing UFW rules | Verify CrowdSec bans do not interfere with SSH/Tailscale/fail2ban |
| ADR-030 (Redis) | No impact | No Redis changes |
| ADR-031 (Database naming) | No impact | No database changes |


| AC | Description | Covered by P0-006? |
|----|-------------|-------------------|
| AC-SEC-001 | Secure access control, defense against brute-force | Yes -- CrowdSec adds community-sourced IP reputation |



| Counter | Location | Value |
|---------|----------|-------|
| Total completed | PROGRESS.md line 12 | 6 / 257 (2.3%) |
| P0 phase count | PROGRESS.md line 27 | 6/29 |
| P0-006 checkbox | PROGRESS.md line 50 | - [ ] unchecked |
| P0-006 verification | CHECKLIST.md line 104 | - [ ] unchecked |


| Counter | Value | Calculation |
|---------|-------|-------------|
| Total completed | 7 / 257 (2.7%) | 6 + 1 = 7; 7/257 = 2.723% truncated to 2.7% |
| P0 phase count | 7/29 | 6 + 1 = 7 |





















| Pattern | Value |
|---------|-------|
| Evidence root for P0 | docs/setup-evidence/P0/STEP-P0-006/ |
| Summary file | p0-006-summary.md |
| Aizanta health check | aizanta-post-check.md (always include) |
| Verification report | verification.md (canonical 12-section schema) |
| Raw log artifacts | .txt or .log |
| StepPrompts-required files | crowdsec-status.txt + crowdsec-collections.txt |
| Recommended total files | 7 |








| Counter | Pre-P0-006 | Post-P0-006 |
|---------|------------|-------------|
| Total completed | 6/257 (2.3%) | 7/257 (2.7%) |
| P0 step count | 6/29 | 7/29 |



| # | Anti-Pattern | Avoidance |
|---|-------------|-----------|
| AP1 | Fake placeholder evidence | Transparently document unavailable tools; use real VPS outputs |
| AP2 | Destructive ops without shared-VPS safety | Always capture Aizanta baseline before mutations |
| AP3 | Overwriting existing config without backup | Backup relevant /etc/ directories before install |
| AP4 | Using operator IP in test actions | Use RFC 5737 TEST-NET IPs (e.g., 198.51.100.99) |
| AP5 | Silent deviation from StepPrompts | Document all deviations in verification.md with reasoning |
| AP6 | Claiming success without live output | Every verification point must show exact command + output |


---

*Generated 2026-05-31 for STEP-P0-006 downstream evidence creation. Report path: audit-reports/P0/STEP-P0-006/evidence-pattern-report.md*

## 12. P0-006 Specific Considerations

### 12.1 Shared VPS -- CrowdSec Impact Analysis

CrowdSec in this configuration:
- Monitors ALL traffic on the VPS via Linux audit/parser collections.
- Uses crowdsec-firewall-bouncer-ufw to add UFW deny rules for malicious IPs.
- Will also monitor SSH auth (via crowdsecurity/sshd collection) -- overlapping with fail2ban.

**Safety considerations for shared VPS:**
- **Dual UFW interaction:** Both fail2ban (P0-005) and CrowdSec (P0-006) add UFW deny rules for SSH brute-force. Verify no conflicts.
- **Bouncer API key:** The cscli bouncers add command generates an API key. Store SOPS-encrypted, not in plaintext evidence.
- **Resource usage:** CrowdSec ~200MB RAM. Verify this doesn't push VPS over 16GB total limit.
- **nginx collection:** Will monitor Aizanta's nginx as well (shared VPS). Acceptable mutual benefit.

### 12.2 ADR Compliance for P0-006

| ADR | Relevance | Expected Compliance |
|-----|-----------|---------------------|
| ADR-014 | Shared VPS isolation | Document CrowdSec is additive, does not modify Aizanta services |
| ADR-018 | Defense-in-depth | Aligned -- complements fail2ban as second detection layer |
| ADR-019 | Access Control | Verify CrowdSec bans do not interfere with SSH/Tailscale/fail2ban |
| ADR-030 | Redis | No impact |
| ADR-031 | Database naming | No impact |

### 12.3 Acceptance Criteria Reference

| AC | Description | Covered? |
|----|-------------|----------|
| AC-SEC-001 | Secure access control, defense against brute-force | Yes -- CrowdSec adds community IP reputation |

### 12.4 Counter Math Verification -- Exact Numbers

**Current State (Pre-P0-006):**

| Counter | Location | Value |
|---------|----------|-------|
| Total completed | PROGRESS.md line 12 | 6 / 257 (2.3%) |
| P0 phase count | PROGRESS.md line 27 | 6/29 |
| P0-006 checkbox | PROGRESS.md line 50 | - [ ] unchecked |
| P0-006 verification | CHECKLIST.md line 104 | - [ ] unchecked |

**Expected State (Post-P0-006):**

| Counter | Value | Calculation |
|---------|-------|-------------|
| Total completed | 7 / 257 (2.7%) | 6 + 1 = 7; 7/257 = 2.723% truncated to 2.7% |
| P0 phase count | 7/29 | 6 + 1 = 7 |

### 12.5 Idempotency & Re-run Safety

- curl | sudo sh -- NOT idempotent. Re-running attempts reinstall.
- cscli collections install -- idempotent if collection already installed.
- cscli bouncers add -- NOT idempotent. Re-running creates duplicate entries.
- apt install -y crowdsec-firewall-bouncer-ufw -- idempotent.
- Verification commands are always safe to re-run.

**Recommendation:** Check cscli version first to detect prior installation.

### 12.6 StepPrompts Command Edition Caveat

The StepPrompts P0-006 commands assume CrowdSec is not installed (curl | sudo sh). If CrowdSec is already present, switch to a preserve-existing approach similar to P0-005's deviation.

---

## 13. Implementation Checklist for Downstream

### Phase 1: Pre-Implementation Research

- [x] Create audit-reports/P0/STEP-P0-006/evidence-pattern-report.md (this file)
- [ ] Create audit-reports/P0/STEP-P0-006/internal-context-report.md
- [ ] Create audit-reports/P0/STEP-P0-006/external-crowdsec-setup-report.md

### Phase 2: Implementation

- [ ] Verify P0-005 complete and fail2ban active
- [ ] Capture pre-change baseline: SSH, Aizanta containers, protected ports, UFW, fail2ban
- [ ] Check if CrowdSec is already installed
- [ ] If new install: curl -s https://install.crowdsec.net | sudo sh
- [ ] If already installed: verify version, preserve existing config
- [ ] Install collections: linux, sshd, nginx
- [ ] Create UFW bouncer: sudo cscli bouncers add guinevere-ufw-bouncer
- [ ] Install firewall bouncer: sudo apt install -y crowdsec-firewall-bouncer-ufw
- [ ] Enable and start: sudo systemctl enable --now crowdsec + bouncer
- [ ] Verify: cscli metrics, cscli decisions list
- [ ] Post-change check: SSH, Aizanta, fail2ban, UFW all intact

### Phase 3: Evidence Creation (7 files)

- [ ] docs/setup-evidence/P0/STEP-P0-006/crowdsec-status.txt
- [ ] docs/setup-evidence/P0/STEP-P0-006/crowdsec-collections.txt
- [ ] docs/setup-evidence/P0/STEP-P0-006/crowdsec-bouncer-proof.txt
- [ ] docs/setup-evidence/P0/STEP-P0-006/aizanta-post-check.md
- [ ] docs/setup-evidence/P0/STEP-P0-006/p0-006-summary.md
- [ ] docs/setup-evidence/P0/STEP-P0-006/verification.md
- [ ] docs/setup-evidence/P0/STEP-P0-006/crowdsec-rollback-test.txt (recommended)

### Phase 4: Tracker Sync

- [ ] PROGRESS.md: checkbox [x] (line 50), total 6/257 to 7/257 (2.7%) (line 12), P0 6/29 to 7/29 (line 27)
- [ ] CHECKLIST.md: line 104 [x]
- [ ] StepPrompts.md: status to Completed (line 717), all 6 checkboxes [x]

### Phase 5: Auditor Gate

- [ ] Create audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md
- [ ] Include: live SSH verification, DoD matrix, secret scan, boundary compliance, cross-doc consistency
- [ ] Fix any findings until PASS or accepted false-positive

---

## 14. Summary of Patterns for Parent Implementation

### Evidence Convention

| Pattern | Value |
|---------|-------|
| Evidence root | docs/setup-evidence/P0/STEP-P0-006/ |
| Summary file | p0-006-summary.md |
| Aizanta health check | aizanta-post-check.md (always include) |
| Verification report | verification.md (12-section canonical schema) |
| Raw log artifacts | .txt or .log |
| StepPrompts-required | crowdsec-status.txt + crowdsec-collections.txt |
| Recommended total | 7 files |

### Verification Schema (verification.md) -- 12 Required Sections

1. Header (step, date, host, status, implementer)
2. What Was Done
3. Files Changed (local + VPS)
4. Validation Results (commands, outputs, PASS/FAIL)
5. Evidence Artifacts
6. Shared VPS Impact (Aizanta containers + protected ports)
7. ADR Compliance (ADR-014, ADR-018, ADR-019)
8. AC Reference (AC-SEC-001)
9. Rollback / Re-run Safety
10. Design Decisions / Caveats
11. Evidence Gate (parent + auditor verdicts)
12. Footer

### Status Sync -- 3 Trackers + StepPrompts

All must be updated atomically:
1. PROGRESS.md -- checkbox line 50 + total 6 to 7 + P0 6/29 to 7/29
2. CHECKLIST.md -- checkbox line 104
3. stepprompts/StepPrompts.md -- status to Completed + all 6 checkboxes

### Auditor Gate -- Required After Implementation

- Report at audit-reports/P0/STEP-P0-006/step-p0-006-auditor-report.md
- Must include: evidence file inventory, live SSH checks, DoD matrix, secret scan, boundary compliance, findings, shared VPS safety, verdict
- Fresh context, independent from parent
- Follow-up audit section for post-audit doc-sync changes (matching P0-004/P0-005 pattern)

### Counter Math Summary

| Counter | Pre-P0-006 | Post-P0-006 |
|---------|------------|-------------|
| Total completed | 6/257 (2.3%) | 7/257 (2.7%) |
| P0 step count | 6/29 | 7/29 |

---

### Anti-Patterns Quick Reference

| # | Anti-Pattern | Avoidance |
|---|-------------|-----------|
| AP1 | Fake placeholder evidence | Transparently document unavailable tools |
| AP2 | Destructive ops no shared-VPS safety | Always capture Aizanta baseline first |
| AP3 | Overwriting config without backup | Backup /etc/ before install |
| AP4 | Using operator IP in tests | Use RFC 5737 TEST-NET IPs (198.51.100.99) |
| AP5 | Silent deviation from StepPrompts | Document in verification.md with reasoning |
| AP6 | Claiming success without live output | Every point must show exact command + output |


---

*Generated 2026-05-31 for STEP-P0-006 downstream evidence creation. Report path: audit-reports/P0/STEP-P0-006/evidence-pattern-report.md*


