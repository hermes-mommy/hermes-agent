# STEP-P0-005 Evidence & Status Sync Pattern Report

**Step:** P0-005 — fail2ban Configuration
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Purpose:** Document exact evidence/tracker sync patterns from prior P0 steps (P0-002 through P0-004) to inform STEP-P0-005 evidence creation, verification schema, auditor gate, and counter updates
**Scope:** Read-only pattern analysis — no files modified outside this report

---

## 1. Evidence Location Convention

### Canonical Path Pattern (CONFIRMED)

The canonical evidence path for all P0 steps is:

\`\`\`
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
\`\`\`

For P0-005 specifically:

| Component | Value |
|-----------|-------|
| Step evidence root | \`docs/setup-evidence/P0/STEP-P0-005/\` |
| Auditor report root | \`audit-reports/P0/STEP-P0-005/\` |

**This is the pattern used by all executed P0 steps** (P0-000 through P0-004). No conflict remains — CHECKLIST.md\'s old \`evidence/phase-N/\` convention is outdated and must NOT be followed.

### Fix F-21 Application

Fix F-21 replaced all \`evidence/phase-N/step-NNN/\` paths with \`docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/\` across all 257 steps in StepPrompts.md. P0-005\'s entry already uses the correct path:

\`\`\`
docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt
\`\`\`

---

## 2. Prior P0 Evidence Artifacts — Exact Inventory

### 2.1 STEP-P0-000 (VPS Audit) — 3 files

| File | Path | Purpose |
|------|------|---------|
| \`p0-000-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-000/p0-000-summary.md\` | Summary: what was audited, key findings, outcome |
| \`service-inventory.md\` | \`docs/setup-evidence/P0/STEP-P0-000/service-inventory.md\` | Aizanta services, ports, running containers |
| \`vps-audit-2026-05-31.txt\` | \`docs/setup-evidence/P0/STEP-P0-000/vps-audit-2026-05-31.txt\` | Raw audit output log |

### 2.2 STEP-P0-001 (Guinevere Linux User) — 4 files

| File | Path | Purpose |
|------|------|---------|
| \`p0-001-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-001/p0-001-summary.md\` | Summary: what was done, files changed, security boundary, rollback |
| \`user-creation.log\` | \`docs/setup-evidence/P0/STEP-P0-001/user-creation.log\` | User creation command outcomes, uid/gid, home dir, password status |
| \`sudoers-config.txt\` | \`docs/setup-evidence/P0/STEP-P0-001/sudoers-config.txt\` | Full rule text, visudo validation, sudo -l output |
| \`aizanta-post-check.md\` | \`docs/setup-evidence/P0/STEP-P0-001/aizanta-post-check.md\` | Post-action Aizanta health check |

### 2.3 STEP-P0-002 (SSH Config Update) — 6 files

| File | Path | Purpose |
|------|------|---------|
| \`verification.md\` | \`docs/setup-evidence/P0/STEP-P0-002/verification.md\` | **Comprehensive verification report** (362 lines, canonical template, introduced in P0-002) |
| \`p0-002-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md\` | Summary: what, files changed, security boundary, rollback |
| \`ssh-test.log\` | \`docs/setup-evidence/P0/STEP-P0-002/ssh-test.log\` | Connection test outputs |
| \`ssh-config.txt\` | \`docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt\` | Local ~/.ssh/config content |
| \`aizanta-post-check.md\` | \`docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md\` | Post-action Aizanta health check |
| \`ssh-hardening-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md\` | VPS-side SSH hardening details |

### 2.4 STEP-P0-003 (Directory Structure) — 5 files

| File | Path | Purpose |
|------|------|---------|
| \`verification.md\` | \`docs/setup-evidence/P0/STEP-P0-003/verification.md\` | Comprehensive verification report (357 lines) |
| \`p0-003-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md\` | Summary: what, paths, safety, rollback |
| \`directory-tree.txt\` | \`docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt\` | \`find /home/guinevere -type d | sort\` output |
| \`permissions.txt\` | \`docs/setup-evidence/P0/STEP-P0-003/permissions.txt\` | Ownership and permission capture for all dirs |
| \`aizanta-post-check.md\` | \`docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md\` | Post-action Aizanta health check |

### 2.5 STEP-P0-004 (UFW Firewall Rules) — 6 files

| File | Path | Purpose |
|------|------|---------|
| \`verification.md\` | \`docs/setup-evidence/P0/STEP-P0-004/verification.md\` | Comprehensive verification report (468 lines, refined schema) |
| \`p0-004-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md\` | Summary: what, rules, boundary, rollback |
| \`ufw-status.txt\` | \`docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt\` | Baseline, dry-run, applied rule, final UFW state, \`ufw show added\` |
| \`aizanta-post-check.md\` | \`docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md\` | Aizanta containers + ports + HTTP before and after |
| \`port-scan.txt\` | \`docs/setup-evidence/P0/STEP-P0-004/port-scan.txt\` | nmap unavailable proof + Test-NetConnection fallback results |
| \`nmap-scan.png\` | \`docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png\` | Screenshot-style artifact documenting fallback scan |

### 2.6 Pattern Observations Across All P0 Steps

| Aspect | Pattern |
|--------|---------|
| Summary file naming | \`p0-{XXX}-summary.md\` |
| Aizanta health check | \`aizanta-post-check.md\` — **always** included after infrastructure changes |
| Raw log/command output | \`.txt\` or \`.log\` extension |
| Structured documentation | \`.md\` extension |
| Verification report | \`verification.md\` — standard since P0-002, carried forward |
| Evidence file count | 5-6 files per step (P0-002=6, P0-003=5, P0-004=6) |
| Pre/post state capture | Before-state AND after-state captured for all mutable operations |
| Dry-run proof | Included when destructive operations are possible (P0-004 used \`ufw --dry-run\`) |

---

## 3. verification.md Schema Analysis

The \`verification.md\` file was introduced in P0-002 and refined through P0-003 and P0-004. It is the **canonical verification schema** for all P0 infrastructure steps.

### Canonical Schema Sections

| # | Section | Content | Required? |
|---|---------|---------|-----------|
| 1 | **Header** | Step, Date, Implementer, Evidence root, Status (PASS after auditor gate) | Required |
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

### P0-004 Refinements Worth Carrying Forward

| Refinement | Description |
|------------|-------------|
| Dry-run proof | \`ufw --dry-run\` output captured before applying |
| Idempotency verification | Re-run command shows \`Skipping adding existing rule\` |
| nmap/workaround documentation | Transparently documented when tooling unavailable |
| Docker/UFW caveat | Pre-existing shared-VPS constraint documented as known risk |

---

## 4. Status / Counter Update Patterns

### 4.1 PROGRESS.md Update Pattern

**Expected changes for P0-005 completion:**

| Element | Location | Current Value (Pre-P0-005) | Expected After P0-005 |
|---------|----------|---------------------------|----------------------|
| P0-005 checkbox | Line 49 | \`- [ ] **P0-005** fail2ban configuration ...\` | \`- [x] **P0-005** fail2ban configuration ...\` |
| Total completed | Line 12 | \`5 / 257 (1.9%)\` | \`6 / 257 (2.3%)\` |
| P0 step count | Line 27 | \`5/29\` | \`6/29\` |

**Counter math verification:**
- Previous total: 5 (P0-000 through P0-004)
- After P0-005: 6
- Percentage: 6/257 = 2.334...% (round to 2.3%)
- Phase P0: 6/29

### 4.2 CHECKLIST.md Update Pattern

| Element | Location | Current (Pre-P0-005) | Expected After P0-005 |
|---------|----------|----------------------|----------------------|
| P0-005 verification | Line 103 | \`- [ ] P0-005: sudo fail2ban-client status sshd...\` | \`- [x] P0-005: sudo fail2ban-client status sshd...\` |

### 4.3 StepPrompts.md Update Pattern

**P0-005 entry spans lines 609-687 in StepPrompts.md.**

| Element | Location | Current | Expected After P0-005 |
|---------|----------|---------|----------------------|
| Status field | Line 613 | \`\U0001f7ac Not Started\` or \`**Status:** \U0001f7ac Not Started\` | \`\U0001f7fe Completed\` |
| Pre-flight 1 (P0-004 complete) | ~Line 627 | \`[ ] P0-004 complete\` | \`[x] P0-004 complete\` |
| Pre-flight 2 (SSH access) | ~Line 628 | \`[ ] SSH access confirmed\` | \`[x] SSH access confirmed\` |
| Verification 1 (fail2ban running) | ~Line 663 | \`[ ] fail2ban running\` | \`[x] fail2ban running\` |
| Verification 2 (SSH jail active) | ~Line 664 | \`[ ] SSH jail active\` | \`[x] SSH jail active\` |
| Verification 3 (ban action UFW) | ~Line 665 | \`[ ] Ban action is UFW\` | \`[x] Ban action is UFW\` |

### 4.4 Cross-Tracker Consistency Must-Haves

All three trackers must be updated **atomically**:

1. **PROGRESS.md** — checkbox + total counter (5 to 6) + phase counter (5/29 to 6/29)
2. **CHECKLIST.md** — step verification checkbox (line 103)
3. **stepprompts/StepPrompts.md** — status + all pre-flight + all verification checkboxes

No step should be marked complete in any tracker unless all three are updated.

---

## 5. Prior Auditor Report Patterns

### 5.1 P0-002 Auditor Report (step-p0-002-auditor-report.md - 251 lines)

**Path:** \`audit-reports/P0/STEP-P0-002/step-p0-002-auditor-report.md\`
**Verdict:** PASS

| Section | Content |
|---------|---------|
| Header | Report type, step, phase, date, auditor |
| 1. Scope & Method | Files read, live SSH checks, secret scan, boundary analysis |
| 2. DoD Verification Matrix | Table: #, DoD Item, Result, Evidence |
| 3. Independent SSH Verification | Live SSH commands + output + PASS/FAIL per check |
| 4. Status Sync Verification | PROGRESS/CHECKLIST/StepPrompts tables with expected/actual/status |
| 5. Secrets & Credential Safety | Pattern scan results table, key material exposure check |
| 6. Boundary & Safety Analysis | Aizanta safety + access control + SSH config + hidden destructive ops |
| 7. Minor Findings | Non-blocking findings with assessment |
| 8. Root Break-Glass Caveat | Acceptance rationale for preserved root access |
| 9. Final Verdict | PASS with table of criteria + next actions |
| Footer | Source, date, auditor, validation methods |

### 5.2 P0-003 Auditor Report (step-p0-003-auditor-report.md - 226 lines)

**Path:** \`audit-reports/P0/STEP-P0-003/step-p0-003-auditor-report.md\`
**Verdict:** PASS

| Section | Content |
|---------|---------|
| Header | Report type, step, phase, date, auditor, parent claim |
| 1. Scope | Files read table, Live read-only SSH checks table, LSP Diagnostics table |
| 2. DoD Verification Matrix | Criterion, evidence source, verdict (18 criteria) |
| 3. Caveat Inspection | Systemd wildcard placeholder documented |
| 4. Cross-Doc Consistency Check | Table: document, status, matches implementation |
| 5. Parent Verification Cross-Check | Parent claims vs auditor verification with match/mismatch |
| 6. Boundary Compliance | Persona/consent/Y6/HARD STOP/secrets table |
| 7. Findings | Blocking (0) + Non-blocking with severity/recommendation |
| 8. Shared VPS Safety | Constraint table with evidence |
| 9. Summary | Dimension table + overall verdict |
| 10. Evidence Artifacts List | All file paths with checkmarks |
| Footer | Source, date, auditor, validation method, verdict |

### 5.3 P0-004 Auditor Report (step-p0-004-auditor-report.md - 295 lines)

**Path:** \`audit-reports/P0/STEP-P0-004/step-p0-004-auditor-report.md\`
**Verdict:** PASS (with follow-up caveat resolution section)

Key additions over P0-003:
- Live UFW state verification table
- \`ufw show added\` verification
- Idempotency verification
- Secrets scan across evidence + research reports
- Non-blocking caveats with explicit recommendation text
- Follow-up audit section (sections 13-15) showing post-audit caveat resolution

### 5.4 Auditor Gate - Required Sections Summary for P0-005

For the P0-005 auditor gate, the report should minimally include:

1. **Scope** - files read, live SSH checks performed, LSP diagnostics
2. **DoD Verification Matrix** - criteria from StepPrompts + implementation specifics
3. **Live fail2ban State Verification** - \`fail2ban-client status\`, \`systemctl status\`, jail config
4. **Cross-Doc Consistency** - PROGRESS/CHECKLIST/StepPrompts status
5. **Parent Verification Cross-Check** - claims vs independent check
6. **Boundary Compliance** - persona/consent/Y6/HARD STOP/secrets
7. **Findings** - blocking + non-blocking with recommendations
8. **Shared VPS Safety** - Aizanta container/port verification
9. **Summary** - dimension table + overall verdict
10. **Evidence Artifacts List** - all paths with checkmarks
11. **Footer** - source, date, auditor, validation method, verdict

---

## 6. StepPrompts P0-005 - Exact Reference

From \`stepprompts/StepPrompts.md\` lines 609-687:

### Step Metadata

| Field | Value |
|-------|-------|
| Type | Security |
| Status | \U0001f7ac Not Started |
| Risk | Medium |
| Goal | Protect SSH from brute-force attacks with automatic IP banning |
| Dependencies | P0-004 (UFW configured) |
| Cost Impact | $0/month |
| ADR References | ADR-018 |
| Acceptance Criteria | AC-SEC-001 |
| Estimated Time | 1 hour |

### Pre-flight Checks (lines 627-628)

1. [ ] P0-004 complete (UFW active)
2. [ ] SSH access confirmed

### Commands (lines 631-660)

\`\`\`bash
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
\`\`\`

### Verification Checks (lines 663-665)

1. [ ] fail2ban running -> \`systemctl status fail2ban\` shows active
2. [ ] SSH jail active -> \`fail2ban-client status sshd\` shows jail enabled
3. [ ] Ban action is UFW -> config shows \`banaction = ufw\`

### Evidence (line 668)

- Log: \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt\`

### Rollback (lines 670-676)

\`\`\`bash
sudo systemctl stop fail2ban
sudo systemctl disable fail2ban
sudo apt purge -y fail2ban
sudo rm /etc/fail2ban/jail.local
\`\`\`

### Troubleshooting (lines 678-682)

- **Issue:** fail2ban won't start - Check \`journalctl -u fail2ban -n 50\`. Common: logpath not found. Use \`backend = systemd\`.
- **Issue:** Banned yourself - \`sudo fail2ban-client set sshd unbanip <your-ip>\`

### Notes (lines 684-687)

- Ban time is 24 hours for SSH brute force. Adjust if needed.
- Monitor with \`sudo fail2ban-client status sshd\` periodically.

---

## 7. Recommended Minimal Evidence Artifacts for STEP-P0-005

### Required by StepPrompts (Minimum)

| # | File | Path | Purpose | Precedent |
|---|------|------|---------|-----------|
| 1 | \`fail2ban-status.txt\` | \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt\` | StepPrompts requirement: fail2ban status output, jail status, config dump | StepPrompts requirement |

### Recommended (Based on Prior P0 Pattern Convergence)

| # | File | Path | Purpose | Precedent |
|---|------|------|---------|-----------|
| 2 | \`verification.md\` | \`docs/setup-evidence/P0/STEP-P0-005/verification.md\` | Full canonical verification report | P0-002/P0-003/P0-004 |
| 3 | \`p0-005-summary.md\` | \`docs/setup-evidence/P0/STEP-P0-005/p0-005-summary.md\` | Implementation summary, boundary, rollback | All prior steps |
| 4 | \`aizanta-post-check.md\` | \`docs/setup-evidence/P0/STEP-P0-005/aizanta-post-check.md\` | Aizanta containers + ports unchanged after install | Always after infra change |

### Recommended for fail2ban-Specific Evidence Quality

| # | File | Path | Purpose | Rationale |
|---|------|------|---------|-----------|
| 5 | \`fail2ban-jail-config.txt\` | \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-jail-config.txt\` | Redacted jail.local config (banaction, bantime, maxretry, backend) | P0-002 ssh-config.txt precedent - document the config |
| 6 | \`fail2ban-test.log\` | \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-test.log\` | Dry-run/test proof: \`fail2ban-client status sshd\` output, \`journalctl -u fail2ban -n 20\` to show it started clean | P0-002 ssh-test.log precedent - live test output |
| 7 | \`fail2ban-whitelist-proof.txt\` | \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-whitelist-proof.txt\` | Evidence that Samm's IP is whitelisted (if whitelist is configured) | Safety: prevent accidental self-ban |

### Recommended Artifacts Summary for fail2ban (Fail2ban-Specific)

| Artifact | What It Proves | How to Generate |
|----------|---------------|-----------------|
| Status logs | fail2ban service is active, SSH jail is enabled | \`sudo systemctl status fail2ban\`, \`sudo fail2ban-client status\`, \`sudo fail2ban-client status sshd\` |
| Jail config redacted | banaction=ufw, maxretry=3, bantime=86400, backend=systemd | \`cat /etc/fail2ban/jail.local\` (config, not secrets) |
| Whitelist proof | Operator IP is excluded from banning | \`sudo fail2ban-client get sshd ignoreip\` or show \`ignoreip\` in config |
| Dry-run/test proof | fail2ban actually works (simulated ban) | \`sudo fail2ban-client set sshd banip 10.0.0.1\` then \`status sshd\` shows banned count, then \`set sshd unbanip 10.0.0.1\` |
| Aizanta post-check | fail2ban didn't disrupt Aizanta containers/ports | \`docker ps | grep aizanta\`, \`ss -tlnp | grep -E '5432|6379|80'\` |
| Rollback proof | Rollback procedure verified | Document and test rollback commands |

### File Naming Convention

All files go under: \`docs/setup-evidence/P0/STEP-P0-005/\`

| Pattern | Extension | Use Case |
|---------|-----------|----------|
| \`p0-005-*.md\` | \`.md\` | Structured documentation |
| \`fail2ban-*.txt\` | \`.txt\` | Raw command output, log captures |
| \`verification.md\` | \`.md\` | Canonical verification report (keep exact name) |
| \`aizanta-post-check.md\` | \`.md\` | Aizanta health check (keep exact name) |

---

## 8. Audit Report Files for STEP-P0-005

### Pre-Implementation Reports

Based on prior P0 patterns (4 reports for P0-002, 2 reports for P0-003, 5 reports for P0-004):

| # | File | Path | Purpose | When Created |
|---|------|------|---------|-------------|
| 1 | \`evidence-pattern-report.md\` | \`audit-reports/P0/STEP-P0-005/evidence-pattern-report.md\` | **(this file)** evidence/tracker sync pattern analysis | Before implementation |
| 2 | \`internal-context-report.md\` | \`audit-reports/P0/STEP-P0-005/internal-context-report.md\` | Pre-implementation: StepPrompts analysis, tracker state, ADR constraints, collision scan | Before implementation |
| 3 | \`external-fail2ban-safety-report.md\` | \`audit-reports/P0/STEP-P0-005/external-fail2ban-safety-report.md\` | External research: fail2ban best practices, shared VPS safety, banaction=ufw implications | Before implementation |
| 4 | \`step-p0-005-auditor-report.md\` | \`audit-reports/P0/STEP-P0-005/step-p0-005-auditor-report.md\` | Per-step independent implementation auditor gate | After implementation + parent verification |

---

## 9. Counter Math Verification - Exact Numbers

### Current State (Pre-P0-005)

| Counter | Location | Value |
|---------|----------|-------|
| Total completed | PROGRESS.md line 12 | 5 / 257 (1.9%) |
| P0 phase count | PROGRESS.md line 27 | 5/29 |
| P0-005 checkbox | PROGRESS.md line 49 | \`- [ ]\` unchecked |
| P0-005 verification | CHECKLIST.md line 103 | \`- [ ]\` unchecked |

### Expected State (Post-P0-005)

| Counter | Value | Calculation |
|---------|-------|-------------|
| Total completed | 6 / 257 (2.3%) | 5 + 1 = 6; 6/257 = 2.334% truncated to 2.3% |
| P0 phase count | 6/29 | 5 + 1 = 6 |

### Line Reference Table for Edits

| Tracker | Element | Line | Change |
|---------|---------|------|--------|
| PROGRESS.md | P0-005 checkbox | 49 | \`- [ ]\` to \`- [x]\` |
| PROGRESS.md | Total completed | 12 | \`5 / 257 (1.9%)\` to \`6 / 257 (2.3%)\` |
| PROGRESS.md | P0 phase count | 27 | \`5/29\` to \`6/29\` |
| CHECKLIST.md | P0-005 verification | 103 | \`- [ ]\` to \`- [x]\` |
| StepPrompts.md | Status field | 613 | \`\U0001f7ac Not Started\` to \`\U0001f7fe Completed\` |
| StepPrompts.md | Pre-flight 1 | ~627 | \`[ ]\` to \`[x]\` |
| StepPrompts.md | Pre-flight 2 | ~628 | \`[ ]\` to \`[x]\` |
| StepPrompts.md | Verification 1 | ~663 | \`[ ]\` to \`[x]\` |
| StepPrompts.md | Verification 2 | ~664 | \`[ ]\` to \`[x]\` |
| StepPrompts.md | Verification 3 | ~665 | \`[ ]\` to \`[x]\` |

---

## 10. Files to NOT Touch

| File | Reason |
|------|--------|
| \`docs/setup-evidence/P0/STEP-P0-000/*\` through \`STEP-P0-004/*\` | Prior step evidence, read-only |
| \`audit-reports/P0/STEP-P0-004/*\` | Prior audit reports, read-only |
| \`audit-reports/P0/STEP-P0-003/*\` | Prior audit reports, read-only |
| \`audit-reports/P0/STEP-P0-002/*\` | Prior audit reports, read-only |
| \`adr/*\` | No ADR changes required for P0-005 |
| VPS \`/etc/fail2ban/*\` | Server-side config, not tracked in repo |
| VPS systemd state | Live state, captured in evidence logs only |

---

## 11. P0-005 Specific Considerations

### 11.1 Shared VPS - fail2ban Impact Analysis

fail2ban in this configuration:
- Uses \`banaction = ufw\` - bans are applied at the firewall level
- Monitors SSH auth logs via \`backend = systemd\`
- Maxretry = 3 within findtime = 600s (10 minutes) triggers 24-hour ban

**Safety considerations for shared VPS:**
- fail2ban banning via UFW applies to the entire host, including Aizanta's SSH access. If Aizanta's operators get banned, they lose access too.
- **Critical**: Add \`ignoreip\` for Samm's Tailscale IP and any known Aizanta operator IPs before enabling fail2ban.
- fail2ban itself has negligible resource usage (< 50MB RAM) - safe to run alongside Aizanta.

### 11.2 ADR Compliance for P0-005

| ADR | Relevance | Expected Compliance |
|-----|-----------|---------------------|
| ADR-014 (Shared VPS) | fail2ban runs system-wide, protects both Guinevere and Aizanta | Document that fail2ban is additive, does not modify Aizanta services, containers, or ports |
| ADR-018 (Security - Defense-in-Depth) | fail2ban adds brute-force protection layer | Aligned - fail2ban with UFW banaction is a standard defense-in-depth practice |
| ADR-019 (Access Control) | banaction=ufw interacts with existing UFW rules | Verify that fail2ban UFW bans do not interfere with existing SSH/Tailscale allow rules |
| ADR-030 (Redis) | No impact | No Redis changes |
| ADR-031 (Database naming) | No impact | No database changes |

### 11.3 Acceptance Criteria Reference

| AC | Description | Covered by P0-005? |
|----|-------------|-------------------|
| AC-SEC-001 | Secure access control, including defense against brute-force | Yes - fail2ban directly contributes by auto-banning brute-force sources |

### 11.4 Rollback Safety

The StepPrompts rollback (stop, disable, purge, remove config) is complete and safe. Additional consideration:
- **Test rollback** before claiming completion: verify that \`sudo systemctl stop fail2ban\` does not affect Aizanta or SSH access.
- **Self-ban recovery**: document the unban procedure (\`sudo fail2ban-client set sshd unbanip <ip>\`) in case the operator accidentally triggers a ban during testing.

### 11.5 Idempotency

- \`sudo apt install -y fail2ban\` is idempotent - re-running returns "already installed".
- Writing the same \`jail.local\` is idempotent if using \`tee\` (overwrites with same content).
- \`sudo systemctl enable fail2ban\` and \`sudo systemctl start fail2ban\` are idempotent.
- Re-running verification commands is always safe.

---

## 12. Implementation Checklist for Downstream

### Phase 1: Pre-Implementation Research

- [ ] Create \`audit-reports/P0/STEP-P0-005/evidence-pattern-report.md\` (this file)
- [ ] Create \`audit-reports/P0/STEP-P0-005/internal-context-report.md\`
- [ ] Create \`audit-reports/P0/STEP-P0-005/external-fail2ban-safety-report.md\` (external research)

### Phase 2: Implementation

- [ ] Verify P0-004 complete (UFW active)
- [ ] SSH into VPS as root
- [ ] Install fail2ban: \`sudo apt update && sudo apt install -y fail2ban\`
- [ ] Create \`/etc/fail2ban/jail.local\` with \`banaction = ufw\`, \`backend = systemd\`, \`maxretry = 3\`, \`bantime = 86400\` for SSH
- [ ] Add \`ignoreip\` for Samm's Tailscale IP before enabling
- [ ] Enable and start fail2ban: \`sudo systemctl enable --now fail2ban\`
- [ ] Verify with \`sudo fail2ban-client status\`, \`sudo fail2ban-client status sshd\`
- [ ] Test with simulated ban then unban to prove functionality

### Phase 3: Evidence Creation (6-7 files)

- [ ] \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-status.txt\`
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-jail-config.txt\` (redacted)
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-test.log\` (includes test ban + unban proof)
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/fail2ban-whitelist-proof.txt\`
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/aizanta-post-check.md\`
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/p0-005-summary.md\`
- [ ] \`docs/setup-evidence/P0/STEP-P0-005/verification.md\`

### Phase 4: Tracker Sync

- [ ] PROGRESS.md: checkbox [x], 5/257 to 6/257 (2.3%), P0 5/29 to 6/29
- [ ] CHECKLIST.md: line 103 [x]
- [ ] StepPrompts.md: status to Completed, all checkboxes [x]

### Phase 5: Auditor Gate

- [ ] Create \`audit-reports/P0/STEP-P0-005/step-p0-005-auditor-report.md\`
- [ ] Include: live verification, DoD matrix, secret scan, boundary compliance, cross-doc consistency
- [ ] Fix any findings until PASS or accepted false-positive

---

## 13. Summary of Patterns for Parent Implementation

### Evidence Convention

| Pattern | Value |
|---------|-------|
| Evidence root for P0 | \`docs/setup-evidence/P0/STEP-P0-005/\` |
| Summary file | \`p0-005-summary.md\` |
| Aizanta health check | \`aizanta-post-check.md\` (always include) |
| Verification report | \`verification.md\` (canonical 12-section schema) |
| Raw log artifacts | \`.txt\` or \`.log\` |
| StepPrompts-required file | \`fail2ban-status.txt\` |
| Recommended total files | 6-7 files (StepPrompts minimum + canonical + safety) |

### Verification Schema (verification.md)

1. Header (step, date, implementer, evidence root)
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

### Status Sync - 3 Trackers + StepPrompts

All must be updated atomically:
1. **PROGRESS.md** - checkbox line 49 + total 5 to 6 + P0 5/29 to 6/29
2. **CHECKLIST.md** - checkbox line 103
3. **stepprompts/StepPrompts.md** - status to Completed + all 5 checkboxes

### Auditor Gate - Required After Implementation

- Report at \`audit-reports/P0/STEP-P0-005/step-p0-005-auditor-report.md\`
- Must include: evidence file inventory, live fail2ban checks, DoD matrix, cross-doc consistency, boundary compliance, findings table, shared VPS safety, verdict
- Fresh context, independent from parent

### Counter Math Summary

| Counter | Pre | Post |
|---------|-----|------|
| Total completed | 5/257 (1.9%) | 6/257 (2.3%) |
| P0 step count | 5/29 | 6/29 |

---

*Generated 2026-05-31 for STEP-P0-005 downstream evidence creation. Report path: \`audit-reports/P0/STEP-P0-005/evidence-pattern-report.md\`*
