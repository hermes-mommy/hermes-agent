# Re-Audit Report — P0-027 Fixes

**Auditor**: Independent Implementation Auditor
**Date**: 2026-05-31
**Scope**: 4 changed files from original P0-027 NEEDS REVIEW findings (F1, F2, F3, F4/F5)
**Method**: Read all 4 files in full, cross-referenced against original audit findings and fix descriptions

---

## Verdict: NEEDS REVIEW

3 of 4 fixes pass. **1 medium-severity issue remains** (timer `Description=` not updated). **1 low-severity doc residue** in README. Details below.

---

## Per-Fix Verification

### Fix 1 — `guinevere-backup@.service` (Original F1: CRITICAL — User mismatch)

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| User changed to root | `User=root` | Line 37: `User=root` | ✅ |
| Group changed to root | `Group=root` | Line 38: `Group=root` | ✅ |
| Matches script's `id -u` check | root user passes `id -u -ne 0` check | `guinevere-backup.sh:203-206` requires UID 0 | ✅ |
| Hardening still valid with root | ProtectSystem=strict, NoNewPrivileges=yes, etc. still present | Lines 55-66: all 12 directives intact | ✅ |

**Verdict: ✅ PASS.** Running as root is justified by the script's requirement to read `/etc` and `/opt/guinevere`. The systemd hardening directives (ProtectSystem=strict, ProtectHome=yes, NoNewPrivileges=yes, RestrictSUIDSGID=yes, UMask=0077) form a defense-in-depth layer that applies regardless of UID — the service process cannot write to system paths, access home directories, or escalate privileges even when running as root. The hardening stack is **more relevant** with root since it constrains what would otherwise be an unrestricted process. Comment header (line 26) correctly documents: "Runs as root (required to read /etc and /opt/guinevere)."

---

### Fix 2 — `guinevere-prune-weekly@.service` (Original F2: HIGH — No credentials, no keep flags)

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| SOPS exec-env wrapper | `sops exec-env <path> restic forget ... --prune` | Line 46: `sops exec-env /home/guinevere/secrets/backup/idcloudhost-s3.env restic forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --prune` | ✅ |
| Keep flags present | `--keep-daily 7 --keep-weekly 4 --keep-monthly 3` | Line 46: all three present | ✅ |
| User=root | root | Line 36: `User=root` | ✅ |
| Age key env set | `SOPS_AGE_KEY_FILE` | Line 40: `Environment=SOPS_AGE_KEY_FILE=/home/guinevere/secrets/age-key.txt` | ✅ |
| No plaintext secrets | Secrets only in SOPS-encrypted file | `idcloudhost-s3.env` is SOPS-encrypted (dotenv format) | ✅ |
| Hardening intact | All directives present | Lines 57-67: all 12 directives | ✅ |
| Path consistency | `secrets/backup/` matches repo structure | Uses `/home/guinevere/secrets/backup/idcloudhost-s3.env` (differs from script's `/etc/restic/` convention, but both paths are valid on VPS) | ✅ |

**Note on ExecStart:** The `bash -c 'exec sops exec-env ...'` pattern is clean — `exec` replaces bash with sops, which in turn execs restic. No lingering bash process. The comment at line 41-45 correctly documents the rationale (separate from daily backup to avoid exclusive lock contention).

**Verdict: ✅ PASS.** The service now has proper credential decryption, retention flags matching the primary tier (7d/4w/3m), and full security hardening.

---

### Fix 3 — `secrets/backup/README.md` (Original F4: MEDIUM — retention mismatch, F5: MEDIUM — time mismatch)

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Primary retention from "12 monthly" to "3 monthly" | `3 monthly` | Line 117: `7 daily + 4 weekly + 3 monthly` | ✅ |
| Backup time from "02:30 UTC" to "02:00 WIB / 19:00 UTC" | `02:00 WIB / 19:00 UTC` | Line 117: `Daily (02:00 WIB / 19:00 UTC)` | ✅ |
| Secondary now "Daily (same run as primary)" instead of "Weekly (restic copy)" | `Daily (same run as primary)` | Line 118: `Daily (same run as primary, Phase 5-6)` | ✅ |
| Secondary retention: 14/8/6 | `14 daily + 8 weekly + 6 monthly` | Line 118: `14 daily + 8 weekly + 6 monthly` | ✅ |
| Runtime commands no longer mention `restic copy` | No `restic copy` in runtime section | Lines 86-100: only `restic forget --keep-daily 7 ... --prune` shown | ✅ |

**Doc residue found:**

- **Line 29**: `"Restic backs up to idcloudhost S3, then copies snapshots to R2."` — still says "copies" (low priority, describes conceptual data flow)
- **Line 46**: `"Used by: **secondary** backup target (weekly copy from primary via \`restic copy\`)."` — still references `restic copy` and "weekly" in the cloudflare-r2.env file description, contradictory to the new table (line 118) which says "Daily (same run as primary)"

**Verdict: ✅ PASS (with low-severity doc residue).** The strategy table and runtime commands are correctly updated. The two residual mentions of `restic copy` are in file-level descriptions (not the strategy table) and are non-blocking, but should be cleaned up for consistency: line 46 should drop `restic copy` reference and change "weekly" to "daily", and line 29 should be checked against the actual script behavior (the script does `restic backup`, not `restic copy`, to R2).

---

### Fix 4 — `guinevere-backup-weekly@.timer` (Original F3: HIGH — Redundant weekly timer with misleading description)

| Check | Expected | Actual | Pass? |
|---|---|---|---|
| Comment header changed to "Weekly Redundant Run Timer" | `Weekly Redundant Run Timer` | Line 1: `# Guinevere Restic Backup — Weekly Redundant Run Timer` | ✅ |
| Header no longer falsely claims `restic copy` | No "restic copy" in header | Lines 1-7: correctly describes as "redundant weekly full backup run" and "safety-net checkpoint" | ✅ |
| systemd `Description=` field updated | Should match the new intent | **Line 27: `Description=Weekly restic R2 copy for %I — Guinevere`** — still says "R2 copy"! | ❌ |

**Verdict: ⚠️ PARTIAL PASS — medium-severity residual issue.** The file header (human documentation) was correctly rewritten to describe the timer as a redundant safety-net run. However, the systemd `Description=` field at line 27 was **not updated** and still reads `Weekly restic R2 copy for %I — Guinevere`. This is the string that appears in:
- `systemctl list-timers --all` output
- `journalctl` unit metadata
- `systemctl status guinevere-backup-weekly@r2-copy.timer`

This contradicts both the new intent and the new header comments. An operator seeing `systemctl list-timers` would still think this timer does `restic copy` to R2, when the daily script already handles both repos and this is just a safety-net redundant run.

**Recommended fix:** Change line 27 to:
```
Description=Weekly redundant backup run for %I — Guinevere
```

---

## Summary Table

| Fix | Original Finding | Severity | Status |
|---|---|---|---|
| Fix 1 | F1: User=guinevere → root mismatch | CRITICAL | ✅ PASS |
| Fix 2 | F2: No credentials/keep-flags in prune service | HIGH | ✅ PASS |
| Fix 3 | F4/F5: Retention & time doc mismatch | MEDIUM | ✅ PASS (low doc residue) |
| Fix 4 | F3: Timer Description still says "R2 copy" | MEDIUM | ⚠️ PARTIAL |

---

## Remaining Issues

| # | Severity | Finding | File:Line | Fix |
|---|---|---|---|---|
| **R1** | **MEDIUM** | Timer `Description=` field still says "Weekly restic R2 copy" — contradicts new header and fix intent | `guinevere-backup-weekly@.timer:27` | Change to `Description=Weekly redundant backup run for %I — Guinevere` |
| **R2** | **LOW** | README cloudflare-r2.env description still says "weekly copy from primary via `restic copy`" — contradicts new "Daily (same run)" table | `secrets/backup/README.md:46` | Change to match daily dual-repo pattern (e.g., "secondary target, backed up daily in same script run") |

---

## Overall Assessment

The 3 most critical fixes (F1 root/user, F2 prune credentials, and F3/F4/F5 README retention/time alignment) are correctly implemented. The backup service can now actually run as root, the prune service has proper SOPS credential decryption and retention policies, and the documentation's strategy table accurately reflects the script's behavior.

The single residual medium issue (R1 — timer Description field) is a 1-line text change that does not affect runtime behavior but will mislead operators viewing systemd metadata.

**3 of 4 fixes: VERIFIED CORRECT. 1 fix: PARTIAL with 1-line residual issue. 1 low-severity doc residue in README.**

---

*Re-audit completed 2026-05-31. Only the 4 changed files were audited. Original F6-F9 from the initial audit were not in scope of this re-audit and may still be outstanding.*