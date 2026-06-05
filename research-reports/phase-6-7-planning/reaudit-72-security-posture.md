# Re-Audit 7-2: Security Posture — Post-Fix Verification

> **Auditor ID**: A7-2 (Security Posture Specialist) — Re-audit  
> **Phase**: Phase 7 — Hardening + Monitoring (Terminal Phase)  
> **Target**: `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md`  
> **Date**: 2026-06-05  
> **Status**: COMPLETE  
> **Prior audit**: `research-reports/phase-6-7-planning/audit-72-security-posture.md` (verdict: NEEDS REVIEW)

---

## Executive Summary

This re-audit verifies whether the batch plan's security-posture gaps identified in the prior Auditor 7-2 report have been resolved by subsequent planning-doc fixes.

**Prior audit found 4 critical gaps:**
1. **C-01 (BLOCKING)**: Steps 7.6–7.9 were missing from the file
2. **C-02 (FAIL)**: No systemd hardening verification step
3. **C-03 (NEEDS REVIEW)**: Port 22 allowed without Tailscale binding check
4. **C-04 (NEEDS REVIEW)**: No secrets rotation step
5. **C-05 (NEEDS REVIEW)**: Steps 7.6–7.9 absent → final backup/offsite verification missing

**Re-audit findings after planning-doc fixes:**

| Issue | Prior Status | Current Status | Change |
|---|---|---|---|
| C-01: Steps 7.6–7.9 missing | BLOCKING (FAIL) | **RESOLVED** | Content added for all 4 steps |
| C-02: No systemd hardening verification | FAIL | **NOT RESOLVED** | No sub-step added |
| C-03: Port 22 without Tailscale binding check | NEEDS REVIEW | **NOT RESOLVED** | No fix applied |
| C-04: No secrets rotation step | NEEDS REVIEW | **NOT RESOLVED** | No fix applied |
| C-05: Offsite/final backup verification missing | NEEDS REVIEW | **RESOLVED** | Step 7.8 now includes backup + restore verification |

**FINAL VERDICT: NEEDS REVIEW**

The BLOCKING structural failure (C-01) is resolved — Steps 7.6–7.9 now have complete implementation content with commands, verification, on-failure tables, and evidence paths. However, **3 of the 5 prior gaps remain unresolved**, preventing a PASS verdict.

---

## Detailed Findings

### C-01: Steps 7.6–7.9 Present (Previously BLOCKING)

**Prior finding**: File jumped from Section 7 (Step 7.5) directly to Section 12 (Runbook). Steps 7.6 (Deprecated Files), 7.7 (ADR-029 Tests), 7.8 (Final Backup), and 7.9 (Documentation Update) had zero implementation content.

**Re-audit**: All 4 steps now have complete content:

| Step | Lines | Key Content |
|---|---|---|
| 7.6 — Deprecated Files Cleanup | 925–1051 | Archive-first approach (`git mv`), help.py refactor contract, obsolete tests listed, pre/post archive dependency scan, 4 verification steps (V-7.6.1–V-7.6.4), on-failure rollback table |
| 7.7 — ADR-029 Automated Tests | 1053–1184 | Coverage config contract, safety-critical paths contract, T1–T10 test contract, auto-rollback test contract, 4 verification steps (V-7.7.1–V-7.7.4), CI/CD integration note |
| 7.8 — Final Backup | 1187–1274 | Hermes backup/checkpoint creation, `pg_dump`, Redis `BGSAVE`, restic backup + restore verification, 5 verification steps (V-7.8.1–V-7.8.5), on-failure table |
| 7.9 — Documentation Update | 1277–1415 | ADR-035 to IMPLEMENTED script, PROGRESS/CHECKLIST update contracts, decisions-log entry, implementation guide update, runbook structure gate, 6 verification steps (V-7.9.1–V-7.9.6) |

Each step includes:
- Pre-conditions checklist
- Exact shell commands with SSH invocation
- Verification commands with expected output
- On-failure table with rollback/fix actions
- Evidence path to `docs/setup-evidence/hermes-migration/phase-7/STEP-7.N/verification.md`

**Verdict: RESOLVED**

---

### C-02: No Systemd Hardening Verification (Previously FAIL)

**Prior finding**: Research report 10-security-hardening.md section 3.4 mandates verification of `NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=read-only` across all 13 `.service` files. The batch plan did not include this verification.

**Required fix** (from recheck-context-phase7-sections.md CC-4): Add Step 7.5.7: Systemd Hardening Verification with:
```bash
ssh guinevere-vps 'grep -E "NoNewPrivileges|ProtectSystem|ProtectHome" systemd/*.service deploy/discord/*.service scripts/*.service'
```

**Re-audit**: Step 7.5 (Security Audit, lines 788–920) contains 6 sub-steps (7.5.1–7.5.6):
- 7.5.1: hermes security audit
- 7.5.2: Open Ports Review
- 7.5.3: SOPS + Age Key Audit
- 7.5.4: SSL/TLS Certificate Expiry
- 7.5.5: Redis AUTH Strength
- 7.5.6: PostgreSQL pg_hba.conf Review

**No Step 7.5.7 exists.** A grep for `NoNewPrivileges|ProtectSystem|ProtectHome` across the entire batch plan file returns zero matches beyond the prior audit report references.

All 13 `.service` files in the repo DO contain these hardening directives (verified independently by prior audit), but the plan provides **no operational verification step** to catch future regression.

**Impact**: If a future modification removes hardening directives, there is no Phase 7 regression check to detect it.

**Verdict: NOT RESOLVED** (remains FAIL)

---

### C-03: Port 22 Without Tailscale Binding Check (Previously NEEDS REVIEW)

**Prior finding**: Step 7.5.2 defines an allowed port set including port 22 (SSH). The verification script checks if ports are **in the allowed set** but does NOT check if they are bound to Tailscale IP (`100.x.x.x`) vs public (`0.0.0.0`). ADR-019 mandates zero public ports.

**Required fix** (from recheck-context-phase7-sections.md CC-5): Add check after allowed-set verification:
```python
ssh_check = [l for l in r.stdout.split("\n") if ":22" in l]
for line in ssh_check:
    if "0.0.0.0:22" in line:
        print("FAIL: SSH bound to 0.0.0.0 (public)")
    elif "100." in line and ":22" in line:
        print("PASS: SSH bound to Tailscale IP")
```

**Re-audit**: Step 7.5.2 (lines 836–854) is unchanged from the prior audit version:
- The allowed port set still includes `22`
- The verification logic checks only whether ports are in the allowed set, not their binding address
- No `grep` for `100.x.x.x` or `0.0.0.0:22` is present
- No external port scan step is included

**Verdict: NOT RESOLVED** (remains NEEDS REVIEW)

---

### C-04: No Secrets Rotation Step (Previously NEEDS REVIEW)

**Prior finding**: Step 7.5.3 verifies SOPS/age decryption and offsite age key backups but does not include a scheduled secrets rotation or reference the Secrets Rotation Runbook (`docs/20-security/23-SecretsRotationRunbook_v1.0.md`).

**Required fix** (from prior audit): Either (a) add a step that walks through rotating at least one secret class (e.g., Discord token) following the runbook, or (b) explicitly document in the risk register that no rotation is performed and reference the quarterly rotation schedule.

**Re-audit**: Step 7.5.3 (lines 857–869) remains verification-only:
- `ls -la /home/guinevere/secrets/` - lists secrets
- `grep "public key" /home/guinevere/secrets/age-key.txt` - checks key
- `sops --decrypt` loop - verifies decryption works
- `rclone ls` checks - verifies offsite backups

No rotation step was added. No reference to `23-SecretsRotationRunbook_v1.0.md`. No risk register entry documents a rotation deferral or quarterly schedule.

**Verdict: NOT RESOLVED** (remains NEEDS REVIEW)

---

### C-05: Offsite/Final Backup Verification Missing (Previously NEEDS REVIEW)

**Prior finding**: Step 7.8 was missing, so the final backup procedure — including offsite data backup verification with restore test — had no implementation.

**Re-audit**: Step 7.8 (lines 1187–1274) now includes:
1. Hermes backup and checkpoint creation (lines 1207–1209)
2. `pg_dump` full backup with `sha256sum` (lines 1213–1216)
3. Redis `BGSAVE` with `LASTSAVE` verification (lines 1220–1221)
4. Restic backup to configured repositories (lines 1223–1227)
5. Restore verification to `/tmp/` without overwriting production (lines 1229–1233)
6. Five verification checks (V-7.8.1–V-7.8.5):
   - Hermes backup listed
   - Hermes checkpoint listed
   - PostgreSQL dump non-empty with header
   - Redis LASTSAVE timestamp
   - Restic restore check returns >= 1 restored file

The restic backup writes to "configured repositories" which should include offsite targets (idcloudhost S3 + Cloudflare R2 per ADR-032). The restore verification confirms the backup is readable and files can be extracted.

**Caveat**: The procedure does not explicitly verify the offsite restic snapshot separately (e.g., `restic snapshots` for each remote repository). This is implicit rather than explicit.

**Verdict: RESOLVED** (Step 7.8 now exists with measurable backup/restore verification)

---

## Summary Table

| # | Prior Issue | Prior Status | Current Status | Notes |
|---|---|---|---|---|
| C-01 | Steps 7.6-7.9 missing | BLOCKING | **RESOLVED** | All 4 steps now have complete content |
| C-02 | No systemd hardening verification | FAIL | **NOT RESOLVED** | Step 7.5.7 not added; no grep for directives |
| C-03 | Port 22 without Tailscale binding check | NEEDS REVIEW | **NOT RESOLVED** | Step 7.5.2 unchanged |
| C-04 | No secrets rotation step | NEEDS REVIEW | **NOT RESOLVED** | Step 7.5.3 unchanged |
| C-05 | Offsite/final backup verification missing | NEEDS REVIEW | **RESOLVED** | Step 7.8 now exists with full backup + restore |

---

## Updated Checklist

| # | Checklist Item | Prior Result | Current Result | Evidence |
|---|---|---|---|---|
| 1a | hermes security audit step | PASS | PASS | Step 7.5.1 unchanged |
| 1b | 0 HIGH verified | PASS | PASS | Step 7.5.1 assertion + Gate G02 |
| 1c | Remediation for findings | NEEDS REVIEW | NEEDS REVIEW | No structured playbooks (unchanged) |
| 2a | Open ports check (ss -tlnp) | PASS | PASS | Step 7.5.2 |
| 2b | Only Tailscale ports exposed | NEEDS REVIEW | NEEDS REVIEW | C-03 not resolved |
| 2c | systemd hardening verified | FAIL | FAIL | C-02 not resolved |
| 3a | SOPS secrets rotation | NEEDS REVIEW | NEEDS REVIEW | C-04 not resolved |
| 3b | Age key backup verified | PASS | PASS | Step 7.5.3 unchanged |
| 3c | SSL/TLS certificate expiry | PASS | PASS | Step 7.5.4 unchanged |
| 3d | Redis AUTH strength | PASS | PASS | Step 7.5.5 unchanged |
| 3e | PostgreSQL pg_hba.conf | PASS | PASS | Step 7.5.6 unchanged |
| 4a | Recovery procedures documented | PASS | PASS | Section 12 runbooks + RTO/RPO/Verify/Escalate matrix |
| 4b | Rollback steps clear | PASS | PASS | Section 16 unchanged |
| 4c | RTO/RPO defined | PASS | PASS | Section 13.6 unchanged |
| 4d | Offsite backup verified | NEEDS REVIEW | PASS | Step 7.8 now includes restic + restore verification |

**PASS Count**: 11 (up from 10)
**NEEDS_REVIEW Count**: 3 (down from 4)
**FAIL Count**: 1 (unchanged)

---

## Remaining Gaps

### FAIL: C-02 — No Systemd Hardening Verification

**Location**: Step 7.5 (Security Audit) — no sub-step for systemd hardening

**Required action**: Add Step 7.5.7 (or equivalent) before Phase 7 execution with:
```bash
ssh guinevere-vps 'grep -E "NoNewPrivileges|ProtectSystem|ProtectHome" systemd/*.service deploy/discord/*.service scripts/*.service'
```
Evidence path: `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/systemd-hardening.txt`

### NEEDS REVIEW: C-03 — Tailscale Binding Check for Port 22

**Location**: Step 7.5.2

**Required action**: After the allowed-set check, add port 22 binding analysis:
```python
ssh_lines = [l for l in r.stdout.split("\n") if ":22" in l]
for line in ssh_lines:
    if "0.0.0.0:22" in line:
        print("FAIL: SSH bound to 0.0.0.0 (public)")
    elif "127.0.0.1:22" in line or "100." in line:
        print("PASS: SSH not publicly exposed")
```

### NEEDS REVIEW: C-04 — No Secrets Rotation

**Location**: Step 7.5.3

**Required action**: Either (a) rotate at least one secret class (e.g., Discord token) following `docs/20-security/23-SecretsRotationRunbook_v1.0.md`, OR (b) add a risk register entry explicitly deferring rotation to quarterly schedule.

---

## Positive Findings Confirmed

Despite remaining gaps, the planning-doc fixes have strengthened the plan:

1. **Steps 7.6–7.9 are complete and well-structured** — each has pre-conditions, commands, verification, on-failure procedures, and evidence paths. Deprecated cleanup uses archive-first (`git mv`), not delete.

2. **Step 7.8 restore verification is thorough** — restic restores to `/tmp/` (no production overwrite), then checks file count and size.

3. **Step 7.6 import safety is meticulous** — pre-archive dependency scan, help.py refactor contract, post-archive import scan, clear rollback paths.

4. **Runbook structure gate** (Section 12.0) enforces RTO/RPO/Verify/Escalate for all 9 runbooks.

5. **Evidence paths are measurable** — every step has a defined evidence path under `docs/setup-evidence/hermes-migration/phase-7/STEP-7.N/`, with specific file artifacts in Section 18.

---

## FINAL VERDICT: NEEDS REVIEW

**PASS condition not met** — 1 FAIL (C-02) and 2 NEEDS REVIEW items (C-03, C-04) remain unresolved.

The BLOCKING structural failure is fixed, and the plan is now operationally complete. The remaining 3 hardening gaps affect only Step 7.5 sub-steps and are independently fixable. A third audit pass should be scheduled after these fixes are applied.

### Required Actions for PASS:

| Priority | Action | Issue |
|---|---|---|
| HIGH | Add Step 7.5.7: systemd hardening verification (grep for NoNewPrivileges/ProtectSystem/ProtectHome across .service files) | C-02 |
| MEDIUM | Update Step 7.5.2 port check to verify Tailscale-only binding for SSH port 22 | C-03 |
| MEDIUM | Add secrets rotation step or explicit deferral with quarterly schedule reference | C-04 |

---

*Report generated by Auditor 7-2: Security Posture Specialist (Re-audit)*
*Evidence root: `research-reports/phase-6-7-planning/reaudit-72-security-posture.md`*
*Previous audit: `research-reports/phase-6-7-planning/audit-72-security-posture.md`*
