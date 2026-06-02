# STEP-P0-004 Evidence & Tracker Sync Pattern Report

**Step:** P0-004 — UFW Firewall Rules
**Phase:** P0 Infrastructure Foundation
**Date:** 2026-05-31
**Purpose:** Document exact evidence/tracker sync patterns from prior P0 steps (P0-000 through P0-003) to inform STEP-P0-004 downstream evidence creation
**Scope:** Read-only pattern analysis — no files modified

---

## 1. Evidence Location Convention

### Canonical Path Pattern

The canonical evidence path for all P0 steps is:

\\\
docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/
\\\

For P0-004 specifically:

| Component | Value |
|-----------|-------|
| Step evidence root | \docs/setup-evidence/P0/STEP-P0-004/\ |
| Auditor report root | \udit-reports/P0/STEP-P0-004/\ |

**This is the pattern used by all executed P0 steps:** P0-000, P0-001, P0-002, P0-003 all use \docs/setup-evidence/P0/STEP-P0-{XXX}/\.

### Conflict Status (Resolved)

| Source | Pattern | Status |
|--------|---------|--------|
| **StepPrompts.md (fixed)** | \docs/setup-evidence/P{N}/STEP-P{N}-{XXX}/\ | **Canonical — use this** |
| **CHECKLIST.md** | \evidence/phase-N/\ | Outdated — do NOT follow |
| **IMPLEMENTATION_GUIDE** | \evidence/phase-N/step-MMM/\ | Not used — ignore |
| **All executed P0 steps** | \docs/setup-evidence/P0/STEP-P0-{XXX}/\ | Confirmed canonical |

**Decision:** STEP-P0-004 MUST use \docs/setup-evidence/P0/STEP-P0-004/\.

## 2. Prior P0 Evidence Artifacts — Exact Inventory

### 2.1 STEP-P0-000 (VPS Audit) — 3 files

| File | Path | Purpose |
|------|------|---------|
| \p0-000-summary.md\ | \docs/setup-evidence/P0/STEP-P0-000/p0-000-summary.md\ | Summary: what was audited, key findings, outcome |
| \service-inventory.md\ | \docs/setup-evidence/P0/STEP-P0-000/service-inventory.md\ | Aizanta services, ports, running containers |
| \ps-audit-2026-05-31.txt\ | \docs/setup-evidence/P0/STEP-P0-000/vps-audit-2026-05-31.txt\ | Raw audit output log |

### 2.2 STEP-P0-001 (Guinevere Linux User) — 4 files

| File | Path | Purpose |
|------|------|---------|
| \p0-001-summary.md\ | \docs/setup-evidence/P0/STEP-P0-001/p0-001-summary.md\ | Summary: what was done, files changed, security boundary, rollback |
| \user-creation.log\ | \docs/setup-evidence/P0/STEP-P0-001/user-creation.log\ | User creation command outcomes, uid/gid, home dir, password status |
| \sudoers-config.txt\ | \docs/setup-evidence/P0/STEP-P0-001/sudoers-config.txt\ | Full rule text, visudo validation, sudo -l output |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-001/aizanta-post-check.md\ | Post-action Aizanta health check |

### 2.3 STEP-P0-002 (SSH Config Update) — 6 files

| File | Path | Purpose |
|------|------|---------|
| \p0-002-summary.md\ | \docs/setup-evidence/P0/STEP-P0-002/p0-002-summary.md\ | Summary: what, files changed, security boundary, rollback |
| \ssh-test.log\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-test.log\ | Connection test outputs |
| \ssh-config.txt\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-config.txt\ | Local \~/.ssh/config\ content |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-002/aizanta-post-check.md\ | Post-action Aizanta health check |
| \ssh-hardening-summary.md\ | \docs/setup-evidence/P0/STEP-P0-002/ssh-hardening-summary.md\ | VPS-side SSH hardening details |
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-002/verification.md\ | **Comprehensive verification report** (362 lines, canonical template) |

### 2.4 STEP-P0-003 (Directory Structure) — 5 files

| File | Path | Purpose |
|------|------|---------|
| \p0-003-summary.md\ | \docs/setup-evidence/P0/STEP-P0-003/p0-003-summary.md\ | Summary: what, paths, safety, rollback |
| \directory-tree.txt\ | \docs/setup-evidence/P0/STEP-P0-003/directory-tree.txt\ | \ind /home/guinevere -type d | sort\ output |
| \permissions.txt\ | \docs/setup-evidence/P0/STEP-P0-003/permissions.txt\ | Ownership and permission capture for all dirs |
| \izanta-post-check.md\ | \docs/setup-evidence/P0/STEP-P0-003/aizanta-post-check.md\ | Post-action Aizanta health check |
| \erification.md\ | \docs/setup-evidence/P0/STEP-P0-003/verification.md\ | **Comprehensive verification report** (357 lines) |

### 2.5 Pattern Observations Across All P0 Steps

| Aspect | Pattern |
|--------|---------|
| Summary file naming | \p0-{XXX}-summary.md\ |
| Aizanta health check | \izanta-post-check.md\ — always included after infrastructure changes |
| Raw log/command output | \.txt\ or \.log\ extension |
| Structured documentation | \.md\ extension |
| Verification report | \erification.md\ — **new in P0-002, carried forward** |
| Evidence file count | 3–6 files per step (growing: P0-000=3, P0-001=4, P0-002=6, P0-003=5) |

## 3. verification.md Schema Analysis

The \erification.md\ file was introduced in P0-002 and refined in P0-003. It is the **canonical verification schema** for P0 steps.

### P0-002 verification.md Schema (362 lines)

| Section | Content |
|---------|---------|
| **Header** | Step, Date, Implementer, Evidence root, Status |
| **What Was Done** | Narrative of actions taken, blockers discovered, fixes applied |
| **Files Changed** | Local machine files + VPS files |
| **Validation Results** | Commands, outputs, PASS/FAIL for each verification point |
| **Evidence Artifacts** | List of all evidence/audit files produced |
| **Shared VPS Impact** | Aizanta containers, protected ports after changes |
| **ADR Compliance** | ADR-014, ADR-015, ADR-019, ADR-030, ADR-031 checks |
| **AC Reference** | AC items satisfied |
| **Rollback / Re-run Safety** | Rollback commands, idempotency notes |
| **Design Decisions / Caveats** | Rationale for deferrals, deviations from StepPrompts |
| **Evidence Gate** | Parent verification summary + independent auditor verdict |
| **Footer** | Source task, date, implementer, validation method |

### P0-003 verification.md Schema (357 lines)

Same schema as P0-002, with these additional refinements:

| Refinement | Description |
|------------|-------------|
| Pre-flight output | Aizanta containers + protected ports captured BEFORE change |
| Implementation commands | Exact SSH commands used to execute the step |
| Correction commands | Commands used to fix issues found during verification |
| World-writable scan | Added \ind /home/guinevere -type d -perm /o+w\ |
| Directory count + tree | Full sorted output with COUNT= tag |
| Ownership/permissions per dir | \stat -c '%U:%G %a %n'\ for every directory |
| Systemd placeholder caveat | Explicit documentation of literal \*\ dir |

### What verification.md Does NOT Include

- **StepPrompts checkbox state** (not repeated in verification.md — checked in auditor report)
- **Status sync details** (PROGRESS/CHECKLIST/StepPrompts counters — checked in auditor report)
- **Introduced vs pre-existing diagnostics** (checked in auditor report)
- **LSP diagnostics output** (checked in auditor report)

**Decision:** P0-004 verification.md should follow the P0-002/P0-003 schema.
## 4. Status / Counter Update Patterns

### 4.1 PROGRESS.md Update Pattern

**Location:** PROGRESS.md within the repo.

| Element | Location | Current (Pre-P0-004) | Expected After |
|---------|----------|----------------------|----------------|
| P0-004 checkbox | Line 48 | - [ ] **P0-004** ... | - [x] **P0-004** ... |
| Total completed | Line 12 | 4 / 257 (1.6%) | 5 / 257 (1.9%) |
| P0 step count | Line 27 | 4/29 | 5/29 |

### 4.2 CHECKLIST.md Update Pattern

**Location:** CHECKLIST.md within the repo.

| Element | Location | Current | Expected After |
|---------|----------|---------|----------------|
| P0-004 checkbox | Line 101 | [ ] P0-004: sudo ufw status ... | [x] P0-004: ... |

### 4.3 StepPrompts.md Update Pattern

**Location:** stepprompts/StepPrompts.md (lines 518-605)

| Element | Location | Current | Expected After |
|---------|----------|---------|----------------|
| Status field | Line 521 | Not Started | Completed |
| Pre-flight 1 | Line 536 | unchecked | checked |
| Pre-flight 2 | Line 537 | unchecked | checked |
| Pre-flight 3 | Line 538 | unchecked | checked |
| Verification 1 | Line 569 | unchecked | checked |
| Verification 2 | Line 570 | unchecked | checked |
| Verification 3 | Line 571 | unchecked | checked |
| Verification 4 | Line 572 | unchecked | checked |

### 4.4 Cross-Tracker Consistency

All three trackers must be updated atomically:
1. PROGRESS.md - checkbox + total counter + phase counter
2. CHECKLIST.md - step verification checkbox
3. stepprompts/StepPrompts.md - status + all pre-flight + all verification checkboxes

## 5. StepPrompts P0-004 Checkboxes Reference

### Pre-flight Checks (lines 536-538)

The StepPrompts defines 3 pre-flight checkboxes:
- [ ] Current SSH session is active (don't lock yourself out)
- [ ] UFW installed (which ufw)
- [ ] SSH port identified (default 22 or custom)

### Verification Checks (lines 569-572)

4 verification checkboxes:
- [ ] UFW active -> sudo ufw status shows "Status: active"
- [ ] Only SSH + Tailscale allowed -> no other ALLOW rules
- [ ] SSH works -> ssh guinevere-vps "echo ok" returns ok
- [ ] PostgreSQL blocked -> external nmap -p 5433 shows filtered

### Evidence Paths (lines 575-576)

- Log: docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt
- Screenshot: docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png

### Aizanta Impact Assessment (lines 599-604)

The StepPrompts has a specific Aizanta Impact Assessment block:
1. Check Aizanta's required ports: sudo ss -tlnp | grep aizanta
2. Document current Aizanta services: sudo systemctl list-units | grep aizanta
3. Ensure Aizanta ports remain allowed after UFW changes
4. Test Aizanta connectivity after UFW reload: curl -s http://localhost:<aizanta-port>/health

## 6. Recommended Evidence Files for STEP-P0-004

### Minimum Required (based on StepPrompts + prior pattern convergence)

| # | File | Purpose | Format | Precedent |
|---|------|---------|--------|-----------|
| 1 | p0-004-summary.md | Summary: what was done, UFW rules, security boundary, rollback | Markdown | All prior steps |
| 2 | ufw-status.txt | sudo ufw status verbose output | Plaintext | StepPrompts requirement |
| 3 | nmap-scan.png | External port scan screenshot | PNG | StepPrompts requirement |
| 4 | aizanta-post-check.md | Aizanta health unchanged post-UFW | Markdown | P0-001/P0-002/P0-003 |
| 5 | verification.md | Full verification report following canonical schema | Markdown | P0-002/P0-003 |

### Recommended But Optional

| # | File | Purpose | Precedent |
|---|------|---------|-----------|
| 6 | ufw-rules-before.txt | Snapshot of UFW rules before reset | Best practice (ssh-backup in P0-002) |
| 7 | port-scan-before.txt | ss -tlnp before change | P0-002/P0-003 captured before-state |
| 8 | aizanta-pre-check.md | Aizanta + port state before UFW change | P0-003 pre-flight verification |

### File Naming Convention

All files go under: docs/setup-evidence/P0/STEP-P0-004/

Patterns observed from prior steps:
- Summary: p0-004-summary.md
- Raw output: .txt or .log
- Structured docs: .md
- Screenshots: .png

## 7. Audit Report Files for STEP-P0-004

### Pre-Implementation Reports

Based on P0-002 pattern (4 reports) and P0-003 pattern (2 reports):

| # | File | Purpose | When Created |
|---|------|---------|-------------|
| 1 | internal-context-report.md | Pre-implementation: StepPrompts analysis, tracker state, ADR constraints, collision scan | Before implementation |
| 2 | external-readiness-report.md | External research: UFW best practices, Aizanta port preservation, lockout safety | Before implementation |
| 3 | evidence-pattern-report.md | (this file) evidence/tracker sync pattern analysis | Before implementation |
| 4 | step-p0-004-auditor-report.md | Per-step implementation auditor gate | After implementation + parent verification |

### Auditor Report Schema (from P0-003 auditor report, 226 lines)

| Section | Content |
|---------|---------|
| Header | Report type, step, phase, date, auditor |
| 1. Scope | Files read, live SSH checks, LSP diagnostics |
| 2. DoD Verification Matrix | Criterion, evidence source, PASS/FAIL |
| 3. Caveat Inspection | StepPrompts anomalies |
| 4. Cross-Doc Consistency Check | PROGRESS/CHECKLIST/StepPrompts status |
| 5. Parent Verification Cross-Check | Parent claims vs independent verification |
| 6. Boundary Compliance | Persona/consent/surveillance/Y6/HARD STOP/secrets |
| 7. Findings | Blocking + non-blocking |
| 8. Shared VPS Safety | Aizanta impact verification |
| 9. Summary | Dimension table + overall verdict |
| 10. Evidence Artifacts List | All file paths with checkmarks |
| Footer | Source, date, auditor, validation method, verdict |

## 8. Recommended Minimal Files to Touch

### Files to CREATE (6 minimum)

| # | File | Path |
|---|------|------|
| 1 | p0-004-summary.md | docs/setup-evidence/P0/STEP-P0-004/p0-004-summary.md |
| 2 | ufw-status.txt | docs/setup-evidence/P0/STEP-P0-004/ufw-status.txt |
| 3 | nmap-scan.png | docs/setup-evidence/P0/STEP-P0-004/nmap-scan.png |
| 4 | aizanta-post-check.md | docs/setup-evidence/P0/STEP-P0-004/aizanta-post-check.md |
| 5 | verification.md | docs/setup-evidence/P0/STEP-P0-004/verification.md |
| 6 | step-p0-004-auditor-report.md | audit-reports/P0/STEP-P0-004/step-p0-004-auditor-report.md |

### Files to UPDATE (3 minimum)

| # | File | Change |
|---|------|--------|
| 1 | PROGRESS.md | P0-004 checkbox, total 4/257 to 5/257, P0 4/29 to 5/29 |
| 2 | CHECKLIST.md | Line 101: P0-004 checkbox checked |
| 3 | stepprompts/StepPrompts.md | Status to Completed, all 7 checkboxes checked |

### Files to NOT TOUCH

| File | Reason |
|------|--------|
| docs/setup-evidence/P0/STEP-P0-000/* | Prior step evidence, read-only |
| docs/setup-evidence/P0/STEP-P0-001/* | Prior step evidence, read-only |
| docs/setup-evidence/P0/STEP-P0-002/* | Prior step evidence, read-only |
| docs/setup-evidence/P0/STEP-P0-003/* | Prior step evidence, read-only |
| docs/setup-evidence/README.md | Does not exist; deferred |
| audit-reports/P0/STEP-P0-001-auditor-report.md | Prior audit, read-only |
| audit-reports/P0/STEP-P0-002/* | Prior audit reports, read-only |
| audit-reports/P0/STEP-P0-003/* | Prior audit reports, read-only |

## 9. P0-004 Specific Considerations

### UFW Reset and Aizanta Impact

The StepPrompts command \sudo ufw --force reset\ removes all existing UFW rules. The P0-000 audit showed Aizanta uses:

| Aizanta Service | Port | Exposure |
|-----------------|------|----------|
| nginx | 80/tcp | 100.94.104.22:80 (Tailscale IP) |
| PostgreSQL | 5432/tcp | 127.0.0.1:5432 (local) |
| Redis | 6379/tcp | 127.0.0.1:6379 (local) |

After ufw reset + default deny incoming + allow 22/tcp + allow 41641/udp:
- 127.0.0.1-bound services (PG 5432, Redis 6379) are on localhost, unaffected by UFW.
- Aizanta nginx on 100.94.104.22:80 is bound to Tailscale IP. If UFW blocks this, Aizanta's web service may be inaccessible via Tailscale.

**Critical check:** After applying UFW rules, verify curl to Aizanta health endpoint still works.

### Lockout Safety

The StepPrompts includes sudo ufw --force enable. If SSH (22/tcp) is not explicitly allowed before enable, the operator will be locked out. Required sequence:
1. First: ufw allow 22/tcp
2. Then: ufw allow 41641/udp (Tailscale)
3. Then: ufw --force enable
4. Then: ssh guinevere-vps "echo ok" from separate session

### Evidence: nmap-scan.png

This is the first step requiring a screenshot. If Playwright/browser tooling is unavailable, capture nmap output as text in ufw-status.txt and note the screenshot as deferred.

### UFW Reset Window

Between ufw --force reset and ufw default deny incoming, there is a brief window where traffic is unfiltered. Recommended: capture before-state with sudo ufw status verbose > before.rules before reset.

## 10. Summary of Patterns for Downstream Implementation

### Evidence Convention

| Pattern | Value |
|---------|-------|
| Evidence root for P0 steps | docs/setup-evidence/P0/STEP-P0-{XXX}/ |
| Summary file | p0-{XXX}-summary.md |
| Aizanta health check | aizanta-post-check.md (always include) |
| Verification report | verification.md (canonical schema from P0-002/P0-003) |
| Raw log artifacts | .txt or .log |
| StepPrompts-required files | ufw-status.txt + nmap-scan.png |
| Evidence count | 5-6 files per step |

### Verification Schema (verification.md)

1. Header (step, date, implementer, evidence root)
2. What Was Done
3. Files Changed (local + VPS)
4. Validation Results (commands, outputs, PASS/FAIL)
5. Evidence Artifacts (list of all files created)
6. Shared VPS Impact (Aizanta containers + protected ports)
7. ADR Compliance (ADR-018, ADR-019 for P0-004)
8. AC Reference (AC-CORE-002, AC-SEC-001)
9. Rollback / Re-run Safety
10. Design Decisions / Caveats
11. Evidence Gate (parent + auditor verdicts)
12. Footer

### Status Sync - 3 Trackers + StepPrompts

All must be updated atomically:
1. PROGRESS.md - checkbox + total counter + phase counter
2. CHECKLIST.md - step verification checkbox
3. stepprompts/StepPrompts.md - status + all pre-flight + all verification checkboxes

### Auditor Gate - Required After Implementation

- Auditor report at audit-reports/P0/STEP-P0-004/step-p0-004-auditor-report.md
- Must include: evidence file inventory, live SSH checks, DoD matrix, cross-doc consistency, boundary compliance, findings table, shared VPS safety, verdict
- Fresh context, independent from parent

---

*Generated 2026-05-31 for STEP-P0-004 downstream evidence creation. Report path: audit-reports/P0/STEP-P0-004/evidence-pattern-report.md*
