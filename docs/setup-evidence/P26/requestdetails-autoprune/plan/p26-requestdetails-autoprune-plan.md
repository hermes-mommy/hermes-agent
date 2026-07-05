# P26 RequestDetails Autoprune Plan

- Date: 2026-06-27
- Workspace: `C:\Users\faizz\guinevere`
- Evidence Root: `docs/setup-evidence/P26/requestdetails-autoprune`
- Target Host: `root@49.12.82.34 -p 39999`
- Target DB: `/var/lib/9router/db/data.sqlite`
- Target Retention: keep latest `300` rows in `requestDetails` ordered by `timestamp DESC, id DESC`

## 1. Mission

Implement a backup-first, metadata-only `requestDetails` prune and a 15-minute systemd backstop that:

1. Deletes only old rows from `requestDetails`.
2. Never touches `usageHistory`, `usageDaily`, or any other tables.
3. Preserves the newest 300 rows deterministically.
4. Uses `flock`, SQLite `busy_timeout`, `wal_checkpoint(PASSIVE)`, and `PRAGMA optimize`.
5. Never prints payloads, request bodies, response bodies, secrets, or tokens.
6. Produces complete verification and audit evidence.

The user request is authoritative for the `300`-row cap even though earlier research references a `200`-row legacy cap and some timer research suggested `1000`. This plan binds to the user request and records that decision explicitly for audit clarity.

## 2. Known State

- Pre-prune `requestDetails_count` is `1000`.
- `usageHistory_count` is `5939` in the local ground truth snapshot.
- `usageDaily_count` is `2` in the local ground truth snapshot.
- SQLite is in WAL mode and integrity is currently `ok`.
- No existing autoprune script or timer was present in the local evidence snapshot.
- PM2 has two online `9router` workers.
- Dashboard usage routes are auth-gated; unauthenticated route checks are fast and healthy.
- Security review flagged payload/logging risk, so the implementation must stay metadata-only and avoid PM2/app log inspection as evidence.

## 3. Binding Decisions

1. The runtime script will prune to `300` retained rows, not `1000`.
2. The prune path will be an external maintenance backstop, not an app code change.
3. The timer will run every 15 minutes with `OnBootSec=5min`, `OnUnitActiveSec=15min`, and `Persistent=true`.
4. No PM2 restart is expected for prune-only work.
5. No firewall, Tailscale, bind-address, or worker-count changes are in scope.
6. `VACUUM` is out of the recurring path. The recurring maintenance path uses `wal_checkpoint(PASSIVE)` and `PRAGMA optimize` only.
7. Backup is mandatory before any live mutation.
8. Logging is metadata-only. No row content, payload previews, or secret-bearing fields may be printed.

## 4. Dependency Map

| Step | Depends On | Can Run In Parallel |
|---|---|---|
| 1. Finalize plan/scaffold | Read-only research already completed | No |
| 2. Implement prune script | Step 1 | Yes, with Step 3 |
| 3. Install systemd service/timer | Step 1 | Yes, with Step 2 |
| 4. Backup, prune run, post-prune verification | Steps 2 and 3 | No |
| 5. Audit, fix, final report | Step 4 | Audits on different surfaces can run in parallel after parent verification |

## 5. Collision Scan

Shared writers are limited to runtime files and evidence documents.

- Step 2 owns `/usr/local/sbin/9router-prune-requestdetails.sh` and `implementation/prune-script-implementation.md`.
- Step 3 owns `/etc/systemd/system/9router-prune-requestdetails.service`, `/etc/systemd/system/9router-prune-requestdetails.timer`, and `implementation/systemd-timer-implementation.md`.
- Step 4 writes runtime verification artifacts and the backup files on the VPS.
- Step 5 writes audit and final evidence files.

There is no overlap between the script and unit files, so those two implementation steps may proceed in parallel.

## 6. Step Scaffolds

### Step 1. Finalize Plan and Evidence Layout

**Expected Files**

- `docs/setup-evidence/P26/requestdetails-autoprune/plan/p26-requestdetails-autoprune-plan.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/requestdetails-prune-design.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/runtime-dashboard-analysis.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/security-analysis.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/systemd-timer-analysis.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/research/evidence-passfail-analysis.md`

**Forbidden Patterns**

- `requestDetails.data`
- `SELECT *`
- `json_extract(data`
- `DELETE FROM usageHistory`
- `DELETE FROM usageDaily`
- `VACUUM`
- `as any`
- `@ts-ignore`
- `@ts-expect-error`
- `# type: ignore`

**Required Commands**

- Read the research files above.
- Verify the plan file exists after write.
- Confirm the binding decision for cap `300` is recorded.

**Evidence Requirements**

- This plan file is the evidence for step 1.
- Later verification files must reference this plan and the research files.

**Hard Rejection Criteria**

- Any ambiguity about the cap or target tables remains unresolved.
- Any research artifact is missing.
- Any forbidden pattern appears in the plan.

### Step 2. Implement Prune Script

**Expected Files**

- `/usr/local/sbin/9router-prune-requestdetails.sh`
- `docs/setup-evidence/P26/requestdetails-autoprune/implementation/prune-script-implementation.md`

**Forbidden Patterns**

- `set -x`
- `SELECT *`
- `SELECT data`
- `json_extract(data`
- `DELETE FROM usageHistory`
- `DELETE FROM usageDaily`
- `VACUUM`
- `TRUNCATE`
- `rm -rf`
- raw request bodies, response bodies, prompt text, completion text
- `Authorization`, `Bearer`, `Cookie`, `api key`, `token`, `password`, `JWT`

**Required Commands**

- `bash -n /usr/local/sbin/9router-prune-requestdetails.sh`
- `ssh -p 39999 root@49.12.82.34 'grep -nE "(DELETE FROM usageHistory|DELETE FROM usageDaily|SELECT \*|SELECT data|json_extract\(data|set -x|VACUUM|TRUNCATE)" /usr/local/sbin/9router-prune-requestdetails.sh'`
- `ssh -p 39999 root@49.12.82.34 'test -x /usr/local/sbin/9router-prune-requestdetails.sh'`

**Evidence Requirements**

- `docs/setup-evidence/P26/requestdetails-autoprune/implementation/prune-script-implementation.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/pre-prune-snapshot.md`
- Later: `docs/setup-evidence/P26/requestdetails-autoprune/verification/post-prune-snapshot.md`
- Later: `docs/setup-evidence/P26/requestdetails-autoprune/verification/auto-prune-verification.md`

**Hard Rejection Criteria**

- The script can mutate any table other than `requestDetails`.
- The script can run without a lock.
- The script logs payload content or secrets.
- The script lacks backup or integrity gates.
- The script lacks deterministic ordering by `timestamp DESC, id DESC`.

### Step 3. Install Systemd Service and Timer

**Expected Files**

- `/etc/systemd/system/9router-prune-requestdetails.service`
- `/etc/systemd/system/9router-prune-requestdetails.timer`
- `docs/setup-evidence/P26/requestdetails-autoprune/implementation/systemd-timer-implementation.md`

**Forbidden Patterns**

- `VACUUM` in the timer path
- `DELETE FROM usageHistory`
- `DELETE FROM usageDaily`
- `set -x`
- shell loops that inspect row payloads
- any journald command that prints `requestDetails.data`

**Required Commands**

- `ssh -p 39999 root@49.12.82.34 'systemd-analyze verify /etc/systemd/system/9router-prune-requestdetails.service /etc/systemd/system/9router-prune-requestdetails.timer'`
- `ssh -p 39999 root@49.12.82.34 'systemctl daemon-reload'`
- `ssh -p 39999 root@49.12.82.34 'systemctl enable --now 9router-prune-requestdetails.timer'`
- `ssh -p 39999 root@49.12.82.34 'systemctl list-timers 9router-prune-requestdetails.timer --all --no-pager'`
- `ssh -p 39999 root@49.12.82.34 'systemctl status 9router-prune-requestdetails.timer --no-pager'`

**Evidence Requirements**

- `docs/setup-evidence/P26/requestdetails-autoprune/implementation/systemd-timer-implementation.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/auto-prune-verification.md`

**Hard Rejection Criteria**

- Timer is inactive or not enabled.
- Service is not oneshot or does not call the prune script.
- Hardening prevents SQLite access.
- The unit files expose or log secrets/payloads.

### Step 4. Backup, Manual Prune, and Verification

**Expected Files**

- `/var/lib/9router/db/backups/data.sqlite.before-requestdetails-prune-<timestamp>.bak`
- `/var/lib/9router/db/backups/data.sqlite.before-requestdetails-prune-<timestamp>.bak-wal`
- `/var/lib/9router/db/backups/data.sqlite.before-requestdetails-prune-<timestamp>.bak-shm`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/post-prune-snapshot.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/auto-prune-verification.md`

**Forbidden Patterns**

- Any mutation of `usageHistory` or `usageDaily`
- any payload dump
- any `SELECT *`
- `VACUUM`
- PM2 restart unless the prune fails and rollback is needed
- firewall, Tailscale, or endpoint configuration changes

**Required Commands**

- Create a backup before mutation.
- Verify backup integrity and parity with preflight counts.
- Run the prune script once manually.
- Verify `requestDetails_count <= 300`.
- Verify `usageHistory_count` and `usageDaily_count` do not change during the prune.
- Verify `PRAGMA integrity_check` returns `ok`.
- Verify `PRAGMA wal_checkpoint(PASSIVE)` and `PRAGMA optimize` complete.
- Verify the app endpoint remains healthy.

**Evidence Requirements**

- `docs/setup-evidence/P26/requestdetails-autoprune/verification/post-prune-snapshot.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/verification/auto-prune-verification.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/fixes/round-1-fix-log.md` if any fix is needed

**Hard Rejection Criteria**

- Post-prune `requestDetails_count` exceeds `300`.
- Any protected-table count changes.
- Database integrity fails.
- The runtime becomes unhealthy.
- The backup is missing or invalid.

### Step 5. Audit, Fix, and Final Report

**Expected Files**

- `docs/setup-evidence/P26/requestdetails-autoprune/audits/round-1/db-prune-audit.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/audits/round-1/runtime-dashboard-audit.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/audits/round-1/security-audit.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/audits/round-2/final-autoprune-audit.md`
- `docs/setup-evidence/P26/requestdetails-autoprune/final/p26-requestdetails-autoprune-final-report.md`

**Forbidden Patterns**

- unresolved `NEEDS REVIEW` or `FAIL` findings
- raw payloads or secrets in audit text
- unsupported claims about pruning or dashboard behavior

**Required Commands**

- Read each audit report fully.
- Apply only fixes requested by valid findings.
- Re-run the relevant verification commands after fixes.
- Re-run the security/payload scan on evidence text.

**Evidence Requirements**

- All round-1 audit files.
- A fix log if any issue is found.
- A round-2 final audit file.
- The final report with a clear outcome status.

**Hard Rejection Criteria**

- Any audit FAIL is left unresolved.
- The final report omits backup, verification, or timer status.
- The final evidence set is missing the 12-section verification structure.

## 7. Exact Runtime Shape

### Prune Script

Runtime path:

`/usr/local/sbin/9router-prune-requestdetails.sh`

Required behavior:

1. Acquire a lock with `flock`.
2. Record start time and target DB path.
3. Run read-only preflight counts and integrity checks.
4. Create a backup before any live delete.
5. Delete only rows older than the newest 300 by `timestamp DESC, id DESC`.
6. Verify protected table counts did not change.
7. Run `PRAGMA integrity_check`, `PRAGMA wal_checkpoint(PASSIVE)`, and `PRAGMA optimize`.
8. Write metadata-only logs.

### Systemd Backstop

Service:

`/etc/systemd/system/9router-prune-requestdetails.service`

Timer:

`/etc/systemd/system/9router-prune-requestdetails.timer`

Schedule:

- `OnBootSec=5min`
- `OnUnitActiveSec=15min`
- `Persistent=true`

The timer is a backstop for the runtime prune job and must not change endpoint behavior, worker count, or network posture.

## 8. Rollback Plan

If verification fails after prune:

1. Stop the timer.
2. Restore the backup to `/var/lib/9router/db/data.sqlite`.
3. Re-run `PRAGMA integrity_check`.
4. Confirm the app endpoint and PM2 workers remain healthy.
5. Record the rollback in `fixes/round-1-fix-log.md` and the final report.

Rollback is only for the database and the maintenance units. It must not touch unrelated tables or runtime networking.

## 9. Verification Gates

Completion requires all of the following:

1. Backup exists and verifies.
2. Prune script passes syntax and pattern checks.
3. Systemd unit and timer verify cleanly.
4. Manual prune leaves `requestDetails <= 300`.
5. `usageHistory` and `usageDaily` counts remain unchanged during the prune.
6. SQLite integrity is `ok` after the prune.
7. Dashboard/runtime checks stay healthy.
8. Round-1 audits are read and any valid findings are fixed.
9. Round-2 audit passes.
10. Final report exists and reflects the actual runtime outcome.

## 10. Footer

This plan is evidence-first and runtime-bound. It intentionally separates script implementation, systemd installation, runtime pruning, and audits so each step can be verified without overlapping writers or hidden state.
