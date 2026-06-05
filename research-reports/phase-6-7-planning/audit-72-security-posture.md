# Auditor 7-2 Report: Security Posture Audit

> **Auditor ID**: A7-2 (Security Posture Specialist)  
> **Phase**: Phase 7 — Hardening + Monitoring (Terminal Phase)  
> **Target**: `batch-plan-phase-7.md` — Security Hardening & Operational Resilience  
> **Date**: 2026-06-05  
> **Status**: COMPLETE  

---

## Executive Summary

Auditor 7-2 conducted a full security posture audit of `batch-plan-phase-7.md` against the 20-point checklist defined by the auditor gate. The batch plan demonstrates **strong security awareness** with comprehensive steps for vulnerability scanning, port auditing, SOPS/age verification, SSL/TLS expiry checks, Redis and PostgreSQL security reviews, and operational runbooks.

**However, 4 critical gaps prevent a PASS verdict:**

1. **Steps 7.6–7.9 are MISSING from the file** — The batch plan jumps directly from section 7 (Step 7.5: Security Audit) to section 12 (Runbook). Steps 7.6 (Deprecated Files Cleanup), 7.7 (ADR-029 Tests), 7.8 (Final Backup), and 7.9 (Documentation Update) are declared in the ToC and executive summary but have **no implementation content**. This is a structural completeness failure.

2. **No systemd hardening verification step** — The plan checks that systemd services are active (2.2.2) but never verifies `NoNewPrivileges=true`, `ProtectSystem=strict`, or `ProtectHome=read-only` across service files. The research report (10-security-hardening.md §3.4) mandates this verification.

3. **Port audit allows SSH port 22 without Tailscope binding check** — The allowed ports set includes 22 (SSH). Zero-public-ports goal (ADR-019) requires ports bound to Tailscale IPs only. The verification script does not check `ss -tlnp` output for Tailscale binding (`100.x.x.x` vs `0.0.0.0`).

4. **No secrets rotation step** — The plan verifies SOPS/age decryption and offsite age key backups but does not include a scheduled secrets rotation (e.g., invoking the Secrets Rotation Runbook at `docs/20-security/23-SecretsRotationRunbook_v1.0.md`). Hardening should validate the rotation process, not just current decryption.

**FINAL VERDICT: NEEDS REVIEW** — The plan is structurally sound for the sections it covers but is incomplete and has hardening gaps that must be resolved before Phase 7 execution.

---

## Checklist Results

---

### DOMAIN 1: 0 HIGH Vulnerabilities

#### 1a. Does plan include `hermes security audit` step?

**Result: PASS**

Evidence:
- Step 7.5.1 (line 801–818) explicitly defines: `hermes security --format json --output /tmp/hermes-security-audit.json`
- A Python script reads the JSON, filters for HIGH severity, asserts `len(high) == 0`, and prints PASS/FAIL
- Gate G02 (line 1179–1182) requires 0 HIGH findings as a binary gate

#### 1b. Does plan verify 0 HIGH findings?

**Result: PASS**

Evidence:
- Step 7.5.1 assertion: `assert len(high) == 0, f"{len(high)} HIGH findings"`
- Gate G02 (section 15.2): "0 HIGH findings — len(HIGH) == 0"
- Executive summary success criteria (line 73): "hermes security — 0 HIGH findings"
- On-failure block (lines 820–834) prints details of each HIGH finding for investigation

#### 1c. Does plan include remediation for any findings?

**Result: NEEDS REVIEW**

Evidence:
- Step 7.5.1 On Failure (lines 820–834) iterates through HIGH findings and prints details — this provides **diagnosis** but not **remediation**
- Risk R7-09 (line 1312): "Fix each finding; document accepted risks" — reactive approach
- No pre-defined remediation playbooks for common Hermes vulnerability patterns (e.g., insecure plugin config, exposed debug endpoints, dependency CVEs)

**Rationale**: While the plan documents the escalation path for findings, "remediation" implies structured corrective action procedures. The plan treats vulnerability remediation as ad-hoc ("fix each finding") rather than having pre-defined remediations for known vulnerability classes. For Phase 7 hardening, which should be thorough, this is a gap worth noting but not blocking.

---

### DOMAIN 2: VPS Hardening Complete

#### 2a. Does plan check open ports (`ss -tlnp`)?

**Result: PASS**

Evidence:
- Step 7.5.2 (lines 836–854): `sudo ss -tlnp` executed, output parsed in Python
- Allowed port set defined: `{22, 5433, 6380, 8000, 9090, 9093, 3000, 3100, 9080, 9100, 9121, 9187, 9191, 20128, 20129, 3443}`
- Unexpected ports flagged: `if unexpected: print(f"Unexpected: {unexpected}")`

#### 2b. Are only Tailscale ports exposed (no public ports)?

**Result: NEEDS REVIEW**

Evidence:
- Research report (10-security-hardening.md §1.4) states: "ADR-019 mandates **zero public ports** on the VPS. All admin and service surfaces are Tailscale-internal only."
- Step 7.5.2 defines an allowed port set that **includes port 22 (SSH)**
- The verification script checks if ports are **in the allowed set** but does NOT check if they are bound to Tailscale IP (100.x.x.x) vs 0.0.0.0
- Research report §3.3 requires: "Zero public ports verified via external port scan (e.g., nmap or canyouseeme.org)" — this is not in the batch plan

**Rationale**: SSH port 22 being "allowed" contradicts the zero-public-ports goal. The script should verify binding addresses: `ss -tlnp | grep 22` should show `100.x.x.x:22` or `127.0.0.1:22`, not `0.0.0.0:22`. The plan needs either (a) port 22 removed from allowed set with explicit Tailscale SSH check, or (b) an external port scan step to confirm no public exposure.

#### 2c. Is systemd hardening verified (NoNewPrivileges, ProtectSystem)?

**Result: FAIL**

Evidence:
- Research report §3.4 mandates: "All 13 systemd .service files verified to contain: NoNewPrivileges=true, ProtectSystem=strict, ProtectHome=read-only, MemoryMax, CPUQuota"
- The batch plan checks service **activity** (2.2.2: `for svc in guinevere-* hermes-gateway; do systemctl is-active`) but does NOT verify hardening directives
- No grep/search step for `NoNewPrivileges`, `ProtectSystem`, or `ProtectHome` anywhere in the batch plan steps

**Verification from file system** (for reference, not counted as plan completeness):
- All 13 `.service` files in `systemd/` and `deploy/discord/` and `scripts/` DO contain the hardening directives
- But the batch plan does not OPERATIONALIZE this verification

**Impact**: If a future modification removes hardening directives, there is no Phase 7 regression check to catch it. The plan must include:
```bash
ssh guinevere-vps 'grep -E "NoNewPrivileges|ProtectSystem|ProtectHome" systemd/*.service'
```

---

### DOMAIN 3: Secrets Rotation Scheduled

#### 3a. Is SOPS secrets rotation included?

**Result: NEEDS REVIEW**

Evidence:
- Step 7.5.3 (lines 857–869): Verifies SOPS decryption, age key existence, age key offsite backups — this is **verification**, not **rotation**
- Research report G-03 (line 97): "No SOPS bootstrap template in repo" — HIGH-priority gap
- G-03 Required Action: "Add `secrets/.env.sops.example.yaml` (with dummy encrypted values or clear instructions) to repo"
- Batch plan does NOT include this template creation step
- No reference to `docs/20-security/23-SecretsRotationRunbook_v1.0.md` anywhere in the plan

**Rationale**: The plan verifies the current state of SOPS/age but does not (a) rotate any secrets, (b) create a SOPS bootstrap template, or (c) reference the existing Secrets Rotation Runbook. For a "hardening" phase, verifying but not rotating is a gap.

#### 3b. Is age key backup verified?

**Result: PASS**

Evidence:
- Step 7.5.3 (lines 866–867):
  ```bash
  rclone ls idcloudhost:guinevere-dr-backups/ | grep age-key
  rclone ls r2:guinevere-dr-backups/ | grep age-key
  ```
- Both primary (idcloudhost S3) and secondary (Cloudflare R2) offsite backups are checked
- Pre-condition 2.4.6 (line 126): SOPS + age key operational via `sops --decrypt` test

#### 3c. SSL/TLS certificate expiry checked?

**Result: PASS**

Evidence:
- Step 7.5.4 (lines 872–885): Scans Caddy certificate files, parses expiry dates, calculates days remaining
- If no certificate found, the script gracefully handles it (no crash)
- Evidence path: `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/cert-expiry.txt`

#### 3d. Redis AUTH strength checked?

**Result: PASS**

Evidence:
- Step 7.5.5 (lines 888–898):
  ```bash
  redis-cli -p 6380 ACL LIST
  redis-cli -p 6380 CONFIG GET protected-mode
  redis-cli -p 6380 CONFIG GET bind
  ```
- Evidence path: `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/redis-security.txt`

**Note**: Research report G-07 (line 106) notes that Redis ACLs are not explicitly configured in code. The plan checks current config but does not enforce ACL configuration in deployment scripts. This is a MEDIUM gap acknowledged in the research report as backlog.

#### 3e. PostgreSQL pg_hba.conf reviewed?

**Result: PASS**

Evidence:
- Step 7.5.6 (lines 901–911):
  ```bash
  sudo cat /etc/postgresql/16/main/pg_hba.conf | grep -v "^#" | grep -v "^$"
  sudo -u postgres psql -c "SHOW max_connections;"
  sudo -u postgres psql -c "SHOW ssl;"
  ```
- Evidence path: `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/pg-hba-review.txt`

---

### DOMAIN 4: DR Plan Actionable

#### 4a. Are recovery procedures documented?

**Result: PASS**

Evidence:
- Section 12 (lines 924–1051): 9 operational runbooks (R01–R09) with exact recovery steps for:
  - R01: Hermes Gateway Crash + Restart
  - R02: Memory Recall Degraded
  - R03: Safety Hook Failure
  - R04: 9Router Unreachable
  - R05: Discord Token Expired (with SOPS re-encryption steps)
  - R06: VPS RAM > 80%
  - R07: Disk > 80%
  - R08: PostgreSQL Connection Exhausted
  - R09: Redis WRONGPASS Errors
- DR plan (`docs/40-operations/43-DisasterRecoveryPlan_v1.0.md`, 2946 lines): Exhaustive recovery procedures for 9 scenarios, 20-component RTO/RPO matrix, 6-category self-healing architecture
- Each runbook includes: trigger condition, severity, numbered steps, verification command

#### 4b. Are rollback steps clear and testable?

**Result: PASS**

Evidence:
- Section 16 (lines 1224–1294): Global Rollback Procedure with 8 verifiable steps:
  1. Notify (kernel message)
  2. Revert Prometheus config (restore from `.bak.*`)
  3. Revert alert rules (`git checkout --`)
  4. Restore deprecated files
  5. Remove Phase 7 additions (`.coveragerc`, test files)
  6. Revert ADR-035 status (`sed` replacement)
  7. Restart monitoring stack
  8. **Verify rollback** — curl-based verification for Prometheus targets, restored files, Hermes alerts
- All commands are scripted and idempotent
- Trigger conditions clearly defined (line 1232–1236)
- Rollback readiness checklist (2.5.1–2.5.4) with 4 specific pre-flight checks

#### 4c. RTO/RPO defined?

**Result: PASS**

Evidence:
- Batch plan Section 13.6 (lines 1098–1104):
  - RPO: < 24 hours (daily full backup)
  - RTO: < 4 hours (full restore)
  - Offsite: S3 + R2 dual-provider backup
- DR plan Section 3 (lines 215–271): Detailed 20-row RTO/RPO matrix with per-service targets:
  - PostgreSQL: RPO < 5 min (WAL), RTO 15 min
  - Redis: RPO < 1 sec (AOF), RTO 5 min
  - Full VPS loss: RPO < 5 min, RTO 4 hours
  - Core services: RTO 5–10 min
- RTO/RPO compliance tracking (DR plan §3.3) with Prometheus metrics and alert thresholds

#### 4d. Offsite backup verified?

**Result: NEEDS REVIEW**

Evidence:
- Step 7.5.3 verifies age key backups at both idcloudhost S3 and Cloudflare R2 offsite locations
- The executive summary (line 49) mentions "restore verification" as part of Step 7.8
- Step 7.8 (Final Backup) is **MISSING from the file** — no content exists for this step
- Step 7.1.4 V26-V30 test matrix includes "Backup & Recovery (checkpoints, dumps, offsite)"

**Rationale**: Offsite backup verification for keys is present, but the main backup step (7.8) that would verify full offsite data backups (restic snapshots, pg_dumpall, restore verification) has no implementation content. The test_verification.py V26-V30 tests are planned but the actual backup verification procedure is absent.

---

## Summary Table

| # | Checklist Item | Result | Evidence |
|---|---|---|---|
| **1a** | hermes security audit step included | **PASS** | Step 7.5.1: `hermes security --format json` |
| **1b** | 0 HIGH verified | **PASS** | Python assertion `len(high)==0` + Gate G02 |
| **1c** | Remediation for findings | **NEEDS REVIEW** | Diagnosis output exists, no structured remediation playbooks |
| **2a** | Open ports check (`ss -tlnp`) | **PASS** | Step 7.5.2 with allowed-set verification |
| **2b** | Only Tailscale ports exposed | **NEEDS REVIEW** | Port 22 allowed; no Tailscale IP binding check; no external port scan |
| **2c** | systemd hardening verified | **FAIL** | No verification step for NoNewPrivileges/ProtectSystem/ProtectHome |
| **3a** | SOPS secrets rotation | **NEEDS REVIEW** | Verification only (decrypt check); no rotation or bootstrap template |
| **3b** | Age key backup verified | **PASS** | rclone checks for both S3 and R2 |
| **3c** | SSL/TLS certificate expiry | **PASS** | Step 7.5.4 with days-left calculation |
| **3d** | Redis AUTH strength | **PASS** | Step 7.5.5: ACL LIST, protected-mode, bind |
| **3e** | PostgreSQL pg_hba.conf | **PASS** | Step 7.5.6: pg_hba.conf, max_connections, SSL |
| **4a** | Recovery procedures documented | **PASS** | Section 12: 9 runbooks (R01-R09) + DR plan (2946 lines) |
| **4b** | Rollback steps clear | **PASS** | Section 16: 8-step scripted procedure with verification |
| **4c** | RTO/RPO defined | **PASS** | §13.6 (batch plan) + §3 (DR plan) with 20-row matrix |
| **4d** | Offsite backup verified | **NEEDS REVIEW** | Key backups verified; main backup step 7.8 is MISSING from file |

---

## Critical Issues Summary

### 🔴 BLOCKING (Must fix before Phase 7 execution)

**C-01: Steps 7.6–7.9 Missing (FAIL)**
- **Where**: Batch plan file — sections 8, 9, 10, 11 in ToC but no content
- **Finding**: The file jumps from Section 7 (Step 7.5) directly to Section 12 (Runbook). Steps 7.6 (Deprecated Files), 7.7 (ADR-029 Tests), 7.8 (Final Backup with offsite verification), and 7.9 (Documentation Update) have zero implementation content.
- **Impact**: 4/9 steps have no defined procedures, commands, or verification. The plan is structurally incomplete.
- **Required Fix**: Add content for Steps 7.6–7.9 before any Phase 7 execution.

### 🟠 HIGH (Should fix before execution)

**C-02: No systemd hardening verification (FAIL)**
- **Where**: Missing from all Step 7.5 sub-steps
- **Finding**: Research report §3.4 requires verification of `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only` across all 13 service files. The batch plan does not include this verification.
- **Impact**: Future service file modifications could silently drop hardening directives with no regression detection.
- **Required Fix**: Add a verification block in Step 7.5 (e.g., 7.5.7: Systemd Hardening Verification) that greps for the three directives across all `.service` files.

**C-03: Port 22 allowed without Tailscale binding check (NEEDS REVIEW)**
- **Where**: Step 7.5.2
- **Finding**: SSH port 22 is in the allowed ports set. ADR-019 mandates zero public ports. The verification should check binding to `100.x.x.x` (Tailscale IP) not `0.0.0.0`.
- **Impact**: Potential public SSH exposure if Tailscale SSH is misconfigured.
- **Required Fix**: Either (a) add `ss -tlnp | grep 22` parsing to verify Tailscale-only binding, or (b) remove port 22 from allowed ports and add explicit Tailscale SSH check.

### 🟡 MEDIUM (Address in this phase or document as backlog)

**C-04: No secrets rotation step (NEEDS REVIEW)**
- **Where**: Step 7.5.3
- **Finding**: Plan verifies current SOPS/age state but doesn't rotate any secrets or reference the Secrets Rotation Runbook.
- **Impact**: Secrets rotation is a hardening best practice that is not operationalized.
- **Suggested Fix**: Either (a) add a step that walks through rotating at least one secret class (e.g., Discord token) following the runbook, or (b) explicitly document in the risk register that no rotation is performed and reference the quarterly rotation schedule.

**C-05: Steps 7.6–7.9 being absent also means final backup (7.8) offsite verification is missing (NEEDS REVIEW)**
- **Where**: Step 7.8 (absent)
- **Finding**: The V26-V30 test matrix and executive summary reference restore verification and offsite backups, but the actual procedure is undefined.
- **Impact**: Cannot verify offsite data backup integrity without Step 7.8 implementation.
- **Required Fix**: Add Step 7.8 content before Phase 7 execution or the offsite backup verification (4d) must remain NEEDS REVIEW.

---

## Positive Findings

Despite the issues, the plan has notable strengths:

1. **Comprehensive monitoring integration**: Prometheus Hermes job, 5 alert rules, Grafana dashboard, Promtail regex fix — all well-specified with exact commands and verification scripts.

2. **Defense-in-depth port audit**: The allowed ports verification is more thorough than typical hardening plans, with a Python script that parses `ss` output and compares against a curated allowlist.

3. **Dual-provider offsite key backup**: Age key backup is verified at both idcloudhost S3 (primary) AND Cloudflare R2 (secondary) — demonstrating strong DR design.

4. **Actionable runbooks**: The 9 operational runbooks (R01-R09) are written for someone who has never seen the codebase, with exact commands, trigger conditions, and verification steps.

5. **Rollback with verification**: The global rollback procedure is unusually complete — most plans stop after reverting changes; this one adds a verification block that checks Prometheus targets, restored files, and alert rule counts.

6. **Binary gates with clear PASS/FAIL criteria**: Gates G01-G07 have unambiguous, machine-checkable PASS/FAIL conditions that prevent subjective "looks good" sign-offs.

7. **Service files already hardened**: Verified independently — all 13 `.service` files in the repo already contain `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only` or equivalent. The gap is only in verification, not in the actual hardening state.

---

## Complete Checklist (Machine-Readable)

| Item | Status | Notes |
|------|--------|-------|
| 1a. hermes security audit step | PASS | Step 7.5.1 |
| 1b. 0 HIGH verification | PASS | Assert `len(high) == 0` |
| 1c. Remediation for findings | NEEDS_REVIEW | Diagnosis only, no playbooks |
| 2a. Open ports check | PASS | `ss -tlnp` + allowlist |
| 2b. Only Tailscale ports exposed | NEEDS_REVIEW | Port 22 + no IP binding check |
| 2c. systemd hardening verified | FAIL | No NoNewPrivileges/ProtectSystem check |
| 3a. SOPS secrets rotation | NEEDS_REVIEW | Verification only, no rotation |
| 3b. Age key backup verified | PASS | Dual-provider rclone check |
| 3c. SSL/TLS certificate expiry | PASS | Caddy cert scan |
| 3d. Redis AUTH strength | PASS | ACL LIST + config checks |
| 3e. PostgreSQL pg_hba.conf | PASS | pg_hba.conf review |
| 4a. Recovery procedures documented | PASS | 9 runbooks + DR plan |
| 4b. Rollback steps clear | PASS | 8-step scripted rollback |
| 4c. RTO/RPO defined | PASS | §13.6 + DR plan §3 |
| 4d. Offsite backup verified | NEEDS_REVIEW | Key backups OK; step 7.8 missing |

**PASS Count**: 10  
**NEEDS_REVIEW Count**: 4  
**FAIL Count**: 1  

---

## FINAL VERDICT: NEEDS REVIEW

The batch plan covers **10/15** checklist items satisfactorily (PASS). However, **1 BLOCKING failure** (C-01: Steps 7.6–7.9 missing — structural incompleteness) and **4 items requiring review** prevent a PASS verdict.

### Required Actions for PASS:

1. **IMMEDIATE**: Add content for Steps 7.6, 7.7, 7.8, and 7.9 to complete the batch plan (C-01).
2. **IMMEDIATE**: Add a systemd hardening verification sub-step (Step 7.5.7 or within 7.5) that greps for `NoNewPrivileges`, `ProtectSystem`, `ProtectHome` across all `.service` files (C-02).
3. **BEFORE EXECUTION**: Update Step 7.5.2 port check to verify Tailscale-only binding for SSH (port 22) or add external port scan (C-03).
4. **BEFORE EXECUTION**: Either add a secrets rotation step or explicitly document that rotation is deferred to quarterly schedule (C-04).
5. **BEFORE EXECUTION**: Once Step 7.8 is added, verify it includes offsite data backup verification with restore test (C-05).

Once these items are addressed and evidence paths exist, a re-audit (Auditor 7-2 bis) should be scheduled to confirm PASS.

---

*Report generated by Auditor 7-2: Security Posture Specialist*  
*Evidence root: `research-reports/phase-6-7-planning/audit-72-security-posture.md`*  
*Compliance: AGENTS.md §2.9 (File-Based Output Discipline), §4 (Post-Step Checklist)*
