# P26 High-End 2-Worker Tuning Final Report

Date: 2026-06-27
Evidence root: `docs/setup-evidence/P26/highend-2worker-tuning`
Endpoint: `http://100.104.210.75:20128/v1`
Final status: **P26 HIGH-END 2-WORKER PASS WITH UPSTREAM LIMITS**

## 1. What Was Done

Tuned the existing 9Router v0.5.8 VPS runtime while keeping the same VPS, same endpoint, same Tailscale path, and exactly 2 PM2 workers.

Main runtime changes:

- Backed up SQLite, PM2 state, PM2 systemd unit, sysctl config, and patched runtime files before mutation.
- Patched SQLite runtime PRAGMAs in source, standalone adapter files, and compiled Next.js chunks:
  - `busy_timeout = 30000`
  - `wal_autocheckpoint = 10000`
  - `mmap_size = 268435456`
  - `wal_checkpoint(PASSIVE)` instead of `wal_checkpoint(TRUNCATE)`
- Restarted only PM2 app `9router`.
- Preserved worker count at exactly 2.
- Did not change firewall, SSH, Tailscale, endpoint, VPS size, worker count, or provider credentials.
- Investigated and repaired a discovered SQLite integrity failure using backup-first DB repair.
- Re-ran loadtests and final runtime proof after repair.

## 2. Files Changed

Local evidence files were created/updated under:

- `docs/setup-evidence/P26/highend-2worker-tuning/research/`
- `docs/setup-evidence/P26/highend-2worker-tuning/plan/`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/`
- `docs/setup-evidence/P26/highend-2worker-tuning/loadtest/`
- `docs/setup-evidence/P26/highend-2worker-tuning/audits/`
- `docs/setup-evidence/P26/highend-2worker-tuning/fixes/`
- `docs/setup-evidence/P26/highend-2worker-tuning/final/`

VPS runtime files patched:

- `/root/9router/src/lib/db/schema.js`
- `/root/9router/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/nodeSqliteAdapter.js`
- `/root/9router/src/lib/db/adapters/bunSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/betterSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/nodeSqliteAdapter.js`
- `/root/9router/.next/standalone/src/lib/db/adapters/bunSqliteAdapter.js`
- matching compiled chunks under `/root/9router/.next/standalone/.next/server/chunks/`

VPS DB repair:

- Live corrupt SQLite DB was preserved under `/root/p26-highend-2worker-tuning-backups/repair-20260627-182226/`.
- Repaired candidate was swapped into `/var/lib/9router/db/data.sqlite` only after candidate integrity returned `ok`.

## 3. Validation Results

Final runtime proof:

- PM2 workers: exactly 2 online.
- PM2 mode: `cluster_mode`.
- Worker PIDs: `43086`, `43093`.
- Worker memory: about 175 MB and 218 MB in final proof.
- SQLite integrity: `ok`.
- Local `/v1/models`: HTTP 200.
- Operator Tailscale `/v1/models`: HTTP 200.
- Public IPv4 `49.12.82.34:20128`: blocked/unreachable.
- Tailscale: active.
- Firewall: unchanged, read-only verified.
- Post-marker SQLite/error scan: 0 new matches after 100-request probe.

Loadtests:

- Baseline after repair: 300 requests, concurrency 20, 300/300 HTTP 200, p95 0.349287s.
- Post tuning after repair: 700 requests, concurrency 50, 700/700 HTTP 200, p95 0.621673s.
- SQLite integrity stayed `ok` after both runs.
- PM2 stayed at exactly 2 workers.

## 4. Evidence Artifacts

Key artifacts:

- `verification/pre-tuning-snapshot.md`
- `research/current-runtime-ground-truth.md`
- `plan/p26-highend-2worker-tuning-plan.md`
- `implementation/sqlite-tuning.md`
- `implementation/pm2-node-tuning.md`
- `implementation/os-network-tuning.md`
- `verification/final-runtime-proof.md`
- `verification/sqlite-integrity-investigation.md`
- `verification/sqlite-repair-candidate-inspection.md`
- `fixes/sqlite-repair-log.md`
- `loadtest/baseline-loadtest.md`
- `loadtest/post-tuning-loadtest.md`
- `audits/round-1/runtime-audit.md`
- `audits/round-1/sqlite-lock-audit.md`
- `audits/round-1/worker-balance-audit.md`
- `audits/round-1/security-network-audit.md`
- `audits/round-2/final-runtime-audit.md`

## 5. Doc-Sync Impact

No ADR or governance spec was changed. This task produced scoped P26 evidence only.

Security/network hardening findings remain outside this tuning batch:

- SSH is still broad/root/password-enabled.
- IPv6 INPUT remains default ACCEPT.
- No `[::]:20128` listener is currently present.

## 6. Boundary Compliance

Passed:

- No secrets printed or committed.
- No `.env`, provider credentials, PM2 env values, Authorization headers, cookies, SSH keys, or Tailscale state files were dumped.
- No firewall reset/flush/delete.
- No Tailscale stop/reset/mode change.
- No SSH rule/config change.
- No VPS upgrade.
- Worker count remained 2.
- Only PM2 app `9router` was stopped/started/restarted when needed.

## 7. Rollback and Re-Run Safety

Backups exist on the VPS:

- Initial backup root: `/root/p26-highend-2worker-tuning-backups/20260627-180750`
- Integrity investigation root: `/root/p26-highend-2worker-tuning-backups/integrity-investigation-20260627-182005`
- DB repair root: `/root/p26-highend-2worker-tuning-backups/repair-20260627-182226`

Rollback is possible by restoring runtime files and/or DB files from those backup roots. The corrupt DB copy was preserved for forensic review.

## 8. Design Decisions and Caveats

Decisions:

- Kept PM2 worker count at exactly 2.
- Kept Node heap and PM2 memory restart guardrails as already suitable.
- Did not apply unsupported OS sysctls.
- Kept `net.core.somaxconn=4096`.
- Repaired SQLite DB only after backup and candidate integrity `ok`.

Caveats:

- Strict 45/55 to 55/45 per-request worker split is **not proven**. `/v1/models` did not emit enough per-request worker-attribution logs.
- App write-path retry for `SQLITE_BUSY_SNAPSHOT` is not implemented in this batch. No new lock errors appeared in the audited post-marker windows, but if locks recur under real write pressure, the next executable step is a write-path retry patch.
- Real model smoke was not run at high volume to avoid provider quota burn; gateway load used `/v1/models`.

## 9. Auditor Gate

Round 1:

- Runtime audit: failed initially due SQLite integrity failure and empty loadtest artifacts.
- SQLite lock audit: pass with caveat.
- Worker balance audit: failed strict 45/55 proof.
- Security/network audit: pass with caveats.

Fixes:

- SQLite DB repaired and re-verified.
- Loadtest artifacts regenerated and populated.
- Scaffold violation closed transparently in fix log.

Round 2:

- Final runtime audit: **PASS WITH LIMITATION**.

## 10. Security Scan

Local evidence secret scan found no raw credential patterns requiring redaction. Matches were limited to policy/audit wording about secrets, not secret values.

## 11. Acceptance Criteria Mapping

| Criterion | Result |
|---|---:|
| Exactly 2 workers online | PASS |
| Endpoint stays `http://100.104.210.75:20128/v1` | PASS |
| Tailscale reachable | PASS |
| Public IPv4 app port blocked | PASS |
| Firewall not reset/flushed | PASS |
| SSH still reachable | PASS |
| SQLite integrity `ok` | PASS after repair |
| 0 new SQLite lock errors in audited post-marker windows | PASS |
| Loadtest evidence present | PASS |
| PM2 restart loop absent | PASS |
| CPU/RAM safe | PASS |
| Strict 45/55 worker split proof | LIMITATION |
| Real provider high-volume smoke | NOT RUN; quota-safe limitation |
| No secrets printed | PASS |

## 12. Footer

P26 high-end 2-worker tuning completed with runtime PASS and documented limitations. The system is serving through the same Tailscale endpoint with exactly 2 PM2 workers, repaired SQLite integrity, clean audited load windows, and preserved network/security boundaries.
