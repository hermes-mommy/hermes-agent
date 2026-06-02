# Auditor Report — STEP-P0-027 (Backup Baseline)

**Auditor**: Independent Implementation Auditor
**Date**: 2026-05-31
**Scope**: All files listed in STEP-P0-027 context — backup script, systemd units, secrets, SOPS config, README
**Method**: Read all 12 files in full, cross-referenced against DoD, ADR-032, and context documents

---

## Verdict: NEEDS REVIEW

3 critical/high-severity issues prevent production deployment. 6 additional medium/low issues require doc-sync and cleanup. Details below.

---

## Findings Table

| # | Severity | Category | Finding | File(s) | Recommendation |
|---|---|---|---|---|---|
| **F1** | **CRITICAL** | Systemd/User | Service runs as `User=guinevere` but script exits non-0 when not root (line 204: `id -u` check). With `NoNewPrivileges=yes` and `ProtectSystem=strict`, the backup will always fail. | `guinevere-backup@.service:37-38`, `guinevere-backup.sh:204-208` | Either: (a) remove `User=guinevere` from service and run as root, or (b) remove the root check from the script and ensure the `guinevere` user has read access to `/etc`, `/opt/guinevere` via group membership. Option (b) is safer given the `ProtectSystem=strict` hardening. |
| **F2** | **HIGH** | Secrets/Credentials | `guinevere-prune-weekly@.service` has `ExecStart=/usr/bin/restic forget --prune` with NO `sops exec-env` wrapper, no credentials, and no `--keep-*` flags. Cannot connect to any repo; even if it could, `forget` without keep flags would error or remove all snapshots. | `guinevere-prune-weekly@.service:45` | Wrap in `sops exec-env /etc/restic/idcloudhost-s3.env 'restic forget --keep-daily=7 --keep-weekly=4 --keep-monthly=3 --prune'` and add proper `Environment=SOPS_AGE_KEY_FILE=...` or exec the backup script with a `PRUNE_ONLY=1` mode. |
| **F3** | **HIGH** | Redundant Execution | Daily backup script (`guinevere-backup.sh`) always backs up to BOTH primary AND secondary repos (Phase 2 then Phase 5). The `guinevere-backup-weekly@r2-copy.timer` fires the same script, doing the same dual-repo backup redundantly on Sundays. Weekly timer description says "restic copy" but the script does full backup, not copy. | `guinevere-backup.sh` (all phases), `guinevere-backup-weekly@.timer` | Either: (a) Make the script instance-aware via `%I` — split to `guinevere-backup@primary` (backup primary only) and `guinevere-backup@r2-copy` (restic copy primary→secondary), or (b) remove the weekly timer since secondary is already backed up daily. ADR-032 specifies `restic copy` for secondary replication — the script should use `restic copy`, not a second `restic backup`. |
| **F4** | **MEDIUM** | Doc-Sync | README retention table says Primary: "12 monthly" but script has `PRIMARY_KEEP_MONTHLY=3`. ADR-032 retention says 6 monthly for all tiers. Three different numbers across three documents. | `secrets/backup/README.md:116`, `guinevere-backup.sh:68-69`, `ADR-032-backup-storage-strategy.md:173-174` | Align all three: DoD spec says primary=3, secondary=6. Update README table to match (7/4/3 primary, 14/8/6 secondary). Consider updating ADR-032 or add addendum if 3-month primary was a deliberate deviation for cost reasons. |
| **F5** | **MEDIUM** | Doc-Sync | README says backup time "02:30 UTC" but timer is `OnCalendar=*-*-* 02:00:00` in WIB (comment says UTC+7, i.e., 19:00 UTC). Also says "03:00 UTC" for weekly. These times don't match. | `secrets/backup/README.md:116-117`, `guinevere-backup@.timer:26` | Correct README to: Primary Daily **02:00 WIB (19:00 UTC)**, Weekly R2 Copy **Sun 04:00 WIB (21:00 UTC Sat)**. |
| **F6** | **MEDIUM** | Doc-Sync | ADR-032 retention (7 daily / 4 weekly / 6 monthly / 2 yearly) does not differentiate primary vs secondary retention. Script has primary=7/4/3 and secondary=14/8/6. DoD spec matches the script, not ADR-032. | `ADR-032-backup-storage-strategy.md:170-176`, `guinevere-backup.sh:67-74` | Either (a) update ADR-032 to reflect the dual-tier retention (primary=shorter, secondary=longer for DR) or (b) unify to 7/4/6 for both repos. Per DoD, option (a) is correct — ADR-032 needs an addendum. |
| **F7** | **LOW** | Secrets/Deployment | Three `*-plaintext.env` files exist on disk with real credentials (restic password, idcloudhost keys, R2 keys). README says they should be shredded after encryption. Pre-deployment state is valid, but these MUST NOT be committed. | `secrets/backup/*-plaintext.env` | Immediately verify `.gitignore` blocks these files. After SOPS encryption of all three `.env` files, run `shred -u secrets/backup/*-plaintext.env`. Consider adding a pre-commit hook. |
| **F8** | **LOW** | Shell Style | Array expansion uses `[*]` instead of `[@]` inside `sops exec-env` strings (e.g., `"restic ${BACKUP_ARGS[*]}"`). For the current simple args this is safe, but `[@]` is the idiomatic choice for preserving elements. | `guinevere-backup.sh:377,429,464,512,559` | Change to `"${BACKUP_ARGS[@]}"` or restructure to avoid string interpolation of arrays in sops exec-env. |
| **F9** | **INFO** | Architecture | Backup script does not use `%I` instance specifier — both `guinevere-backup@primary.service` and `guinevere-backup@r2-copy.service` run identical code. The template is effectively unused. | `guinevere-backup.sh` (no %I), `guinevere-backup@.service:30` | Either make the script %I-aware or simplify to non-template service (no `@`). |

---

## DoD Checklist Verification

| # | DoD Item | Status | Evidence |
|---|---|---|---|
| 1 | restic backup script created with dual-repo (S3 primary, R2 secondary) | ✅ PASS | `guinevere-backup.sh` Phase 1-7 covers pg_dump → PRIMARY backup → PRIMARY forget → PRIMARY check → SECONDARY backup → SECONDARY forget → success marker |
| 2 | Systemd timer for daily backup at 02:00 WIB (OnCalendar) | ✅ PASS | `guinevere-backup@.timer:26` — `OnCalendar=*-*-* 02:00:00` |
| 3 | Rotation: keep-daily 7, keep-weekly 4, keep-monthly 3 on PRIMARY | ✅ PASS | `guinevere-backup.sh:67-69` — `PRIMARY_KEEP_DAILY=7`, `PRIMARY_KEEP_WEEKLY=4`, `PRIMARY_KEEP_MONTHLY=3` |
| 4 | Secondary has longer retention (14/8/6) | ✅ PASS | `guinevere-backup.sh:72-74` — `SECONDARY_KEEP_DAILY=14`, `SECONDARY_KEEP_WEEKLY=8`, `SECONDARY_KEEP_MONTHLY=6` |
| 5 | NO Backblaze B2 references | ✅ PASS | `grep` for `[Bb]ackblaze\|[Bb]2` across scripts+secrets returned 0 matches (the B2 hits in `redis-password.yaml` and `db-passwords.yaml` are SOPS ciphertext fragments, not Backblaze references) |
| 6 | SOPS exec-env pattern (no plaintext on disk) | ✅ PASS (runtime) | Script uses `sops exec-env` for all restic operations (lines 376-377, 428-429, 463-464, 511-512, 558-559). Plaintext source files flagged in F7 for pre-encryption state. |
| 7 | PostgreSQL dump with validation (never pipe to restic stdin) | ✅ PASS | Phase 1 writes to file, validates via `zcat \| head -1 \| grep "PostgreSQL"`, then includes file in restic paths. Explicit comment at lines 273-276 explains why piping to stdin is avoided. |
| 8 | Prune separated from backup (avoid lock contention) | ⚠️ PASS (script) / FAIL (service) | Backup script runs forget--prune in separate phases after each backup. BUT `guinevere-prune-weekly@.service` is broken (F2). |
| 9 | DRY_RUN mode available | ✅ PASS | `DRY_RUN=1` env var controls all phases (run_cmd/dry_run_echo functions). Pre-flight checks relaxed for dry-run. |
| 10 | Exclude patterns for /proc /sys /dev /tmp etc | ✅ PASS | `EXCLUDE_PATTERNS` array excludes `/proc`, `/sys`, `/dev`, `/run`, `/tmp`, `/mnt`, `/media`, `/lost+found`, `/var/cache`, `/var/tmp` (lines 92-103) |
| 11 | Success marker written | ✅ PASS | Phase 7 writes ISO-8601 timestamp to `/var/log/guinevere/last-backup-success` (line 581) |
| 12 | .sops.yaml has backup rule with input_type: dotenv | ✅ PASS | `.sops.yaml:2-5` — regex `secrets/backup/.*\.env$` with `input_type: dotenv` and `output_type: dotenv` |

---

## Additional Checks

| Check | Result | Notes |
|---|---|---|
| Port 5432 instead of 5433? | ✅ PASS | Script uses `PG_PORT="5433"` (line 56). `preflight-check.sh` explicitly guards 5432 as Aizanta's port. |
| Missing `set -euo pipefail`? | ✅ PASS | Both scripts have it (backup line 39, setup line 9). |
| Logging adequate? | ✅ PASS | Timestamped `log_info/warn/error`, dual output (stdout+log file via tee), full trace to `/var/log/guinevere/backup-*.log`. |
| README encryption commands correct? | ✅ PASS | Correct `sops --encrypt --input-type dotenv --output-type dotenv` syntax. |
| PostgreSQL dump uses file (not pipe to restic)? | ✅ PASS | Writes to `/var/backups/postgres/alldbs-*.sql.gz`, validates, then includes in restic BACKUP_PATHS. |

---

## Summary

**Overall: NEEDS REVIEW (3 blockers, 6 non-blockers)**

The backup script is well-structured with clear phases, good error handling, and proper SOPS integration. All DoD items pass at the script level. However, **3 deployment-blocking issues must be fixed** before this can run in production:

1. **CRITICAL**: User mismatch — systemd service runs as non-root `guinevere` user but script requires root (F1)
2. **HIGH**: Weekly prune service has no credentials or keep-flags, will fail silently (F2)
3. **HIGH**: Weekly R2 timer is redundant — daily script already backups to both repos (F3)

**Doc-sync issues** (F4-F6): The README, ADR-032, and script have conflicting retention numbers and backup times. These need alignment before production, though they don't block a test run.

**Pre-deployment** (F7): Plaintext secrets must be shredded after `sops --encrypt` of all three env files. Verify `.gitignore` blocks `secrets/backup/*-plaintext.env`.

---

## Recommended Fix Order

1. **Fix F1** (root/user) — backup will not run otherwise
2. **Fix F2** (prune service credentials) — prune will silently fail otherwise
3. **Fix F3** (redundant weekly timer) — wasted bandwidth and CPU
4. **Fix F4-F6** (doc-sync) — update README and ADR-032 to match script
5. **Fix F7** (shred plaintext) — before git commit
6. **Fix F8** (array style) — low priority, cosmetic
7. **Resolve F9** (template usage) — architectural cleanup

---

*Audit completed 2026-05-31. Report covers all 12 files listed in context. Cross-reference validated against ADR-032, AGENTS.md ports/config, and DoD spec.*