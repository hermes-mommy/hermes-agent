# Re-Audit 7-2 R2: Security Posture — Planning-Only Patch Verification

> **Auditor ID**: A7-2 (Security Posture Specialist) — Second Re-audit  
> **Phase**: Phase 7 — Hardening + Monitoring (Terminal Phase)  
> **Target**: `docs/setup-evidence/hermes-migration/batch-plan-phase-7.md`  
> **Date**: 2026-06-05  
> **Status**: COMPLETE  
> **Prior re-audit**: `research-reports/phase-6-7-planning/reaudit-72-security-posture.md` (verdict: NEEDS REVIEW — 1 FAIL, 2 NEEDS REVIEW unresolved)

---

## Executive Summary

This second re-audit verifies whether the **3 remaining gaps** (C-02, C-03, C-04) from the prior re-audit have been resolved by the planning-only patch applied to `batch-plan-phase-7.md`.

**Prior re-audit remaining gaps:**
| Issue | Prior Status | Prior Verdict |
|---|---|---|
| C-02: No systemd hardening verification | FAIL | NOT RESOLVED |
| C-03: Port 22 without Tailscale binding check | NEEDS REVIEW | NOT RESOLVED |
| C-04: No secrets rotation step | NEEDS REVIEW | NOT RESOLVED |

**Current verdict after planning patch: ALL 3 RESOLVED**

| Issue | Prior Status | Current Status | Delta |
|---|---|---|---|
| C-02: No systemd hardening verification | FAIL | **RESOLVED** | Step 7.5.7 added |
| C-03: Port 22 without Tailscale binding check | NEEDS REVIEW | **RESOLVED** | Step 7.5.8 added |
| C-04: No secrets rotation step | NEEDS REVIEW | **RESOLVED** | Step 7.5.9 added |
| C-05: Offsite backup verification (already resolved) | NEEDS REVIEW | **RESOLVED** | Step 7.5.10 also added |
| New: Evidence artifacts listing | N/A | **NEEDS MINOR FIX** | Section 18.1 table missing 4 new artifacts |

**FINAL VERDICT: PASS** (with minor evidence-table caveat)

---

## Detailed Findings

### C-02: Systemd Hardening Verification — Now RESOLVED

**Step 7.5.7** (lines 913–968 in current file):

The planning patch adds a complete systemd hardening verification sub-step:

| Component | Content | Status |
|---|---|---|
| Evidence collection | `for unit in systemd/*.service; do grep -E "(NoNewPrivileges|ProtectSystem|ProtectHome|PrivateTmp|CapabilityBoundingSet|RestrictAddressFamilies|MemoryHigh|MemoryMax)=" "$unit" ; done` | ✅ |
| Runtime verification | `systemctl show hermes-gateway guinevere-core ... -p NoNewPrivileges -p ProtectSystem -p ProtectHome -p MemoryHigh -p MemoryMax` | ✅ |
| Automated assertion | Python script checks each `.service` file for `NoNewPrivileges=yes`, `ProtectSystem=strict`, `ProtectHome=read-only`; exits with `SYSTEMD_HARDENING_PASS` or `SYSTEMD_HARDENING_FAIL` | ✅ |
| Post-hoc verification | Greps evidence file for `SYSTEMD_HARDENING_PASS`; falls back to Python re-check if absent | ✅ |
| On-failure procedure | Stop execution; add missing flag; daemon-reload; restart only affected service; re-verify | ✅ |
| Evidence artifact | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/systemd-hardening.txt` | ✅ |

**All 13 `.service` files are checked at the unit-file level AND the runtime level** via `systemctl show`. The prior concern that "no operational verification step exists" is fully addressed.

**Verdict: RESOLVED** ✅

---

### C-03: SSH/Tailscale Binding for Port 22 — Now RESOLVED

**Step 7.5.8** (lines 974–1014 in current file):

The planning patch adds a dedicated SSH/Tailscale binding verification sub-step:

| Component | Content | Status |
|---|---|---|
| Socket inspection | `ss -tlnp | grep -E ":22\s"` to see exact binding address | ✅ |
| Tailscale IP check | `tailscale ip -4` to confirm Tailscale address | ✅ |
| Firewall rules | `ufw status verbose` or `iptables -S | grep -E "22\|tailscale\|100\."` | ✅ |
| SSH config audit | `grep -RInE "^(ListenAddress\|PasswordAuthentication\|PermitRootLogin\|AllowUsers\|AllowGroups)" /etc/ssh/sshd_config*` | ✅ |
| Automated assertion | Python checks for `0.0.0.0:22` without Tailscale indicators (`100.`, `tailscale`, `ListenAddress 100.`); exits `SSH_TAILSCALE_BINDING_PASS` or `SSH_TAILSCALE_BINDING_FAIL` | ✅ |
| Post-hoc verification | Greps evidence for `100.` / `tailscale` / `SSH_TAILSCALE_BINDING_PASS` | ✅ |
| On-failure procedure | Stop execution; restrict to `100.64.0.0/10`; bind to Tailscale IP; or document explicit exception with owner, expiry, compensating controls | ✅ |
| Evidence artifact | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/tailscale-ssh-binding.txt` | ✅ |

**Indicators checked**: `100.64.` through `100.71.` plus `tailscale`, `ListenAddress 100.`, `ALLOW IN`. Prior gap was that only allowed-set membership was checked; now the **binding address** is specifically analyzed.

**Verdict: RESOLVED** ✅

---

### C-04: Secrets Rotation Schedule — Now RESOLVED

**Step 7.5.9** (lines 1016–1061 in current file):

The planning patch adds a secrets rotation schedule verification sub-step:

| Component | Content | Status |
|---|---|---|
| Existing rotation scan | `grep -RInE "rotation\|rotate\|quarterly\|90 days\|age key\|Discord token\|Redis\|PostgreSQL\|SOPS" docs/20-security docs/30-data .sops.yaml` | ✅ |
| Required evidence template | Lists all 5 secret classes: Discord token, Redis AUTH, PostgreSQL password, SOPS age key, NINEROUTER_API_KEY | ✅ |
| Rotation cadence | "Next quarterly rotation date must be <=90 days from Phase 7 completion" | ✅ |
| No plaintext rule | "Evidence must contain metadata only; no plaintext secrets" | ✅ |
| Automated assertion | Python checks for all 5 secret classes + `<=90 days` in evidence; exits `SECRETS_ROTATION_SCHEDULE_PASS` or `SECRETS_ROTATION_SCHEDULE_FAIL` | ✅ |
| Post-hoc verification | Greps for `SECRETS_ROTATION_SCHEDULE_PASS` or the `<=90 days` constraint | ✅ |
| On-failure procedure | Create evidence addendum with owner, rotation scope, next date; do not paste secret values; if age key backup missing, stop Phase 7 | ✅ |
| Evidence artifact | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/secrets-rotation-schedule.txt` | ✅ |

**All 5 secret classes are explicitly enumerated** with a binding <=90-day quarterly rotation window. The "no plaintext secrets" constraint is explicitly stated in the evidence template. Prior gap was no rotation step or reference at all.

**Verdict: RESOLVED** ✅

---

### C-05: Offsite Backup Repository Verification — Now Explicitly Reinforced

**Step 7.5.10** (lines 1063–1096 in current file):

Although C-05 was already marked RESOLVED in the prior re-audit (via Step 7.8), the planning patch now adds a **dedicated offsite backup sub-step within Security Audit** itself:

| Component | Content | Status |
|---|---|---|
| Repository config check | `env \| grep -E "RESTIC_REPOSITORY\|RESTIC_PASSWORD_FILE"` | ✅ |
| Snapshot count | `restic snapshots --json` with Python assertion | ✅ |
| Data integrity check | `restic check --read-data-subset=1/100` | ✅ |
| Restore smoke test | `restic restore latest --target /tmp/... --include "*.sql"` + `find` verification | ✅ |
| Automated verification | Greps for `snapshots=`, `repository is ok` / `no errors were found`, `Restore smoke test` | ✅ |
| On-failure | Fix restic config/credentials; re-run check + restore; cannot close Phase 7 without it | ✅ |
| Evidence artifact | `docs/setup-evidence/hermes-migration/phase-7/STEP-7.5/offsite-backup-repository.txt` | ✅ |

**Verdict: RESOLVED** ✅ (reinforced beyond prior Step 7.8)

---

### Evidence Artifacts Listing for Step 7.5

**Local Step 7.5 evidence section** (lines 1098–1108): **CORRECT** — lists all 10 artifacts:
- `verification.md`, `hermes-security-audit.json`, `port-review.txt`, `cert-expiry.txt`, `redis-security.txt`, `pg-hba-review.txt`
- `systemd-hardening.txt` ✅
- `tailscale-ssh-binding.txt` ✅
- `secrets-rotation-schedule.txt` ✅
- `offsite-backup-repository.txt` ✅

**Section 18.1 Master Evidence Table** (line 2053): **MISSING 4 NEW ARTIFACTS** — only lists:
- `hermes-security-audit.json, port-review.txt, cert-expiry.txt, redis-security.txt, pg-hba-review.txt`

The master evidence table in Section 18.1 was **not updated** when Steps 7.5.7–7.5.10 were added. This is a planning-doc documentation gap, not an implementation gap — the implementation would still produce the correct evidence files because the Step 7.5 sub-step commands reference the correct paths.

**Severity: MINOR** — the evidence IS properly listed in the Step 7.5 per-step section. Only the Section 18.1 consolidated table is stale.

---

### Planning-Only Verification

All changes are **markdown plan modifications only**:
- Shell commands prefixed with `ssh guinevere-vps` (deferred execution)
- Verification scripts using `python3 - <<"PY"` (will run during execution phase)
- Evidence paths as planning references
- No source code modifications
- No file creations or deletions outside the plan document

**Verdict: PASS** ✅

---

## Summary Table

| # | Criterion | Status | Evidence |
|---|---|---|---|
| (a) | Systemd hardening verification (NoNewPrivileges, ProtectSystem, ProtectHome) | ✅ **PASS** | Step 7.5.7 — unit-file grep + runtime `systemctl show` + Python assertion |
| (b) | SSH/Tailscale binding for port 22 | ✅ **PASS** | Step 7.5.8 — `ss -tlnp` for :22 + Tailscale IP + firewall + SSH config + binding-address assertion |
| (c) | Secrets rotation schedule (5 secret classes, <=90 days, no plaintext) | ✅ **PASS** | Step 7.5.9 — all 5 secrets enumerated, quarterly cadence, plaintext prohibition |
| (d) | Offsite backup verification (restic snapshots/check/restore) | ✅ **PASS** | Step 7.5.10 — snapshots + `check --read-data-subset` + restore smoke test |
| (e) | New evidence artifacts listed for Step 7.5 | ⚠️ **MINOR CAVEAT** | Listed correctly in per-step section (lines 1098–1108); Section 18.1 master table stale |
| (f) | Changes remain planning-only | ✅ **PASS** | All SSH-prefixed commands; no source implementation |

---

## Updated Checklist

| # | Checklist Item | Prior Result | Current Result |
|---|---|---|---|
| 1a | hermes security audit step | PASS | PASS |
| 1b | 0 HIGH verified | PASS | PASS |
| 2a | Open ports check (ss -tlnp) | PASS | PASS |
| 2b | Only Tailscale ports exposed | NEEDS REVIEW | **PASS** (Step 7.5.8) |
| 2c | systemd hardening verified | FAIL | **PASS** (Step 7.5.7) |
| 3a | SOPS secrets rotation | NEEDS REVIEW | **PASS** (Step 7.5.9) |
| 3b | Age key backup verified | PASS | PASS |
| 3c | SSL/TLS certificate expiry | PASS | PASS |
| 3d | Redis AUTH strength | PASS | PASS |
| 3e | PostgreSQL pg_hba.conf | PASS | PASS |
| 4a | Recovery procedures documented | PASS | PASS |
| 4b | Rollback steps clear | PASS | PASS |
| 4c | RTO/RPO defined | PASS | PASS |
| 4d | Offsite backup verified | PASS | PASS (reinforced Step 7.5.10) |

**PASS Count**: 14/14 (up from 11)
**NEEDS_REVIEW Count**: 0 (down from 3)
**FAIL Count**: 0 (down from 1)

---

## Caveats

1. **Section 18.1 master evidence table** (line 2053) lists only 5 artifacts for Step 7.5 instead of 10. The per-step evidence section (lines 1098–1108) is correct. Recommend syncing Section 18.1 to match: add `systemd-hardening.txt, tailscale-ssh-binding.txt, secrets-rotation-schedule.txt, offsite-backup-repository.txt` to the Step 7.5 row.

2. This is a **planning-doc re-audit only**. Runtime verification of these steps (actual systemd flag presence, actual SSH binding, actual secrets rotation execution, actual restic repository connectivity) must occur during Phase 7 execution.

---

## FINAL VERDICT: PASS

All 3 remaining gaps from the prior re-audit (C-02, C-03, C-04) are now **RESOLVED** in the planning document. The `batch-plan-phase-7.md` now contains explicit, verifiable planning gates for:

- **Step 7.5.7**: Systemd hardening with binary PASS/FAIL assertion
- **Step 7.5.8**: SSH/Tailscale binding with binding-address analysis
- **Step 7.5.9**: Secrets rotation schedule for all 5 secret classes with <=90-day quarterly constraint
- **Step 7.5.10**: Offsite backup with snapshots, data integrity check, and restore smoke test

PASS condition is met. The single minor documentation caveat (Section 18.1 table sync) does not block the verdict.

---

*Report generated by Auditor 7-2: Security Posture Specialist (Second Re-audit)*  
*Evidence root: `research-reports/phase-6-7-planning/reaudit-72-security-posture-r2.md`*  
*Previous report: `research-reports/phase-6-7-planning/reaudit-72-security-posture.md`*
