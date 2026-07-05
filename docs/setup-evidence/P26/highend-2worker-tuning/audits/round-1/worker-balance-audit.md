# P26 High-End 2-Worker Tuning - Round 1 Worker Balance Audit

| Field | Value |
|---|---|
| Project | Guinevere P26 highend 2-worker tuning |
| Audit surface | Worker request distribution, 45/55 proof, PM2 worker stability, limitations |
| Evidence root | `docs/setup-evidence/P26/highend-2worker-tuning` |
| Audit path | `docs/setup-evidence/P26/highend-2worker-tuning/audits/round-1/worker-balance-audit.md` |
| Audit date | 2026-06-27 |
| Mode | Read-only evidence audit; no VPS mutation |
| Final verdict | FAIL |

## 1. Scope

This audit checks whether the P26 highend 2-worker tuning evidence proves:

- Requests are distributed across both PM2 workers.
- The requested 45/55 to 55/45 worker balance is achieved.
- PM2 remains stable with exactly 2 online workers after tuning.
- Evidence limitations are documented clearly enough to avoid overstating completion.

## 2. Files Reviewed

- `AGENTS.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/plan/p26-highend-2worker-tuning-plan.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/loadtest/baseline-loadtest.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/loadtest/post-tuning-loadtest.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/pre-tuning-snapshot.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-tuning-snapshot.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-load-error-classification.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/verification/post-marker-sqlite-lock-verification.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/pm2-node-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/sqlite-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/implementation/os-network-tuning.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/fixes/round-1-fix-log.md`
- `docs/setup-evidence/P26/highend-2worker-tuning/research/evidence-passfail-analysis.md`

## 3. Verdict Summary

| Check | Verdict | Reason |
|---|---:|---|
| Exactly 2 PM2 workers online in evidence | PASS WITH LIMITS | Pre/post snapshots and implementation report show 2 online workers, but post evidence covers a short window after restart. |
| PM2 restart loop absent | PASS WITH LIMITS | `unstable_restarts=0` is recorded, and restart count changes from 4 to 5 as expected after the intentional restart. Evidence window is short. |
| Requests hit both workers | PARTIAL | Pre-tuning snapshot contains request log excerpts for both worker prefixes `0|9router` and `1|9router`; no post-load distribution summary proves balanced post-tuning traffic. |
| 45/55 to 55/45 request split achieved | FAIL | No counted post-load worker distribution evidence exists. The loadtest files do not contain the required run results. |
| Loadtest evidence sufficient | FAIL | `baseline-loadtest.md` only contains a title, and `post-tuning-loadtest.md` is empty. |
| Limitations documented | PARTIAL | The plan says insufficient logs must be treated as a limitation, but no final worker-balance limitation statement existed before this audit. |

Final worker-balance gate: FAIL.

## 4. Request Distribution Evidence

### Available Evidence

The pre-tuning snapshot includes recent worker distribution hints showing both PM2 worker prefixes:

- Worker `1|9router` handled repeated `/v1/v1/messages` requests from approximately 17:48 to 17:59.
- Worker `0|9router` handled repeated `/v1/v1/messages` requests from approximately 17:31 to 18:00.

This proves that both workers have received traffic in the broader log history captured before tuning.

### Missing Evidence

The evidence package does not include a post-tuning counted distribution table such as:

- worker 0 request count,
- worker 1 request count,
- total request count,
- percent split,
- collection window,
- log cursor or marker proving only post-load bytes were counted.

The plan explicitly required worker distribution evidence from logs or per-worker PM2 counters. The available post-tuning snapshot lists log mtimes and PM2 status, but it does not provide a counted post-load split.

## 5. 45/55 Proof

The 45/55 proof is not achieved.

Reasons:

- `loadtest/baseline-loadtest.md` contains only `# P26 baseline Loadtest`.
- `loadtest/post-tuning-loadtest.md` is empty.
- No p50/p95/p99 latency summary is present in the loadtest files.
- No HTTP success/failure count is present in the loadtest files.
- No post-load worker 0 versus worker 1 request count is present.
- No calculation shows the split falls between 45/55 and 55/45.

The planner scaffold states that a strongly imbalanced split outside 45/55 to 55/45 is a hard rejection when logs can prove distribution; if logs are insufficient, final status must include the limitation. Here, logs are insufficient to prove the target, so any final PASS claim would be unsupported.

## 6. PM2 Worker Stability

### Evidence Supporting Stability

Pre-tuning snapshot at 2026-06-27T18:01:12+07:00:

- Worker 0: online, PID 31108, uptime 7h, restarts 4.
- Worker 1: online, PID 31121, uptime 7h, restarts 4.
- Both workers in `cluster_mode`.
- `unstable_restarts=0` in PM2 JSON summary.

Implementation restart evidence:

- Before restart: worker 0 and 1 online with restart count 4.
- Intentional `pm2 restart 9router --update-env` ran.
- After restart: worker 0 PID 39839 and worker 1 PID 39852 online with restart count 5.
- `pm2 save` succeeded.

Post-tuning snapshot at 2026-06-27T18:12:27+07:00:

- Worker 0: online, PID 39839, uptime 65s, restarts 5, memory 159.0 MB.
- Worker 1: online, PID 39852, uptime 65s, restarts 5, memory 197.0 MB.
- PM2 JSON summary shows both workers online, `cluster_mode`, `instances=2`, and `unstable_restarts=0`.

Post-marker SQLite verification:

- PM2 status still shows exactly 2 online workers with uptime 3m.
- Worker 0 memory 238.2 MB.
- Worker 1 memory 180.3 MB.

### Stability Limitations

The stability proof is short-window only:

- Post-tuning snapshot was captured roughly 65 seconds after restart.
- Post-marker verification was captured roughly 3 minutes after restart.
- No longer soak window is present.
- No loadtest PM2 before/after state is present.
- No per-worker CPU/memory trend is present.
- No process uptime evidence after the intended loadtest window is present.

Therefore, PM2 worker stability is partially supported for immediate post-restart health, but not proven under sustained load.

## 7. Error and Lock Context

The post-tuning snapshot reports filtered hard error count `6`, but it warns this may include pre-restart lines because log files retained old tails.

The post-load error classification still shows `SqliteError: database is locked`, `SQLITE_BUSY`, and `unhandledRejection` in the sanitized tail for worker 0. This file does not isolate a clean post-marker window.

The clean post-marker SQLite lock verification improves that point:

- Marker captured at 2026-06-27T18:14:55+07:00.
- Probe after marker returned `200 200`.
- New bytes scan reported `0` matches for lock/unhandled patterns across both error logs and both out logs.

This supports "no new lock errors after marker for the small probe window." It does not prove worker balance or loadtest success.

## 8. Live Read-Only Check Note

A read-only SSH check was attempted for current PM2 status and per-worker log counts. The first attempt failed due local/remote quoting, and the second timed out before producing usable output. No mutation commands were issued. Because the check did not produce reliable evidence, it is not used to upgrade the verdict.

## 9. Findings

### F1 - Missing post-load worker distribution proof blocks 45/55 acceptance

Severity: FAIL

The evidence package does not contain counted per-worker post-load request totals or a percentage calculation. Without this, the requested 45/55 to 55/45 proof is absent.

Required remediation:

- Run or record a bounded post-tuning loadtest.
- Mark the log cursor before the test.
- Count worker 0 and worker 1 request lines after the cursor only.
- Record total, percentage split, and pass/fail against 45/55 to 55/45.

### F2 - Loadtest artifacts are effectively empty

Severity: FAIL

The baseline loadtest file contains only a heading, and the post-tuning loadtest file is empty. The plan required at least 200 `/v1/models` requests with concurrency 20 or equivalent, timing summary, success/failure counts, CPU/RAM before and after, and worker distribution evidence.

Required remediation:

- Populate both loadtest files with method, command, timestamp, target endpoint, concurrency, request count, success/failure counts, latency summary, PM2 state, and worker distribution.

### F3 - PM2 stability evidence is immediate-health only

Severity: NEEDS REVIEW

The existing PM2 evidence is useful and shows exactly 2 workers online after restart with no unstable restarts, but it covers only the first few minutes after restart and lacks proof under sustained load.

Required remediation:

- Capture PM2 status after the completed loadtest window.
- Include restart count, uptime, memory, CPU, and `unstable_restarts`.
- Confirm both workers remain online and restart counts do not advance beyond the intentional restart.

### F4 - Error evidence is not cleanly tied to load window

Severity: NEEDS REVIEW

The clean marker verification shows no new SQLite lock patterns after a small probe, but the broader post-load classification still contains old lock lines and provider/upstream errors. The package needs clear separation between pre-restart tail, post-marker probe, and post-load test window.

Required remediation:

- Use marker-based scans for the actual loadtest window.
- Record exact marker sizes/timestamps before loadtest and new-byte scans after loadtest.
- Keep provider 401/403/429/502 errors classified separately from worker/process stability.

## 10. Acceptance Mapping

| Acceptance / Scaffold Item | Status | Evidence |
|---|---:|---|
| Exactly 2 `9router` PM2 workers online | PASS WITH LIMITS | Pre/post snapshots and post-marker verification show 2 online workers. |
| Endpoint reachable at Tailscale `/v1/models` | PASS | Post snapshot and implementation report show HTTP 200 from Tailscale/operator host. |
| No PM2 restart loop | PASS WITH LIMITS | `unstable_restarts=0`, restart count 5 after intentional restart; short window only. |
| Loadtest has 0 HTTP failures | FAIL | No loadtest result content exists. |
| Worker-count regression absent after loadtest | FAIL | No post-load PM2 status tied to a completed loadtest exists. |
| Worker split 45/55 to 55/45 proven | FAIL | No counted worker distribution evidence exists. |
| Limitations stated when logs insufficient | PARTIAL | This audit states the limitation; previous evidence did not close it. |

## 11. Boundary Compliance

Audit boundary: PASS.

- No repo files were modified except this required audit file.
- No VPS mutation command was intentionally issued.
- No service restart, PM2 mutation, firewall change, Tailscale change, sysctl write, deployment, or destructive operation was performed by this audit.
- No secrets, API keys, DB passwords, Authorization headers, cookies, decrypted env values, or raw surveillance data were written into this audit.

## 12. Final Gate

Final verdict: FAIL.

The PM2 immediate-health evidence supports exactly 2 online workers and no observed restart loop in a short window. However, the requested 45/55 worker balance proof is not achieved because the loadtest artifacts are empty and there is no counted post-load worker distribution evidence. Completion must remain blocked or marked PASS WITH LIMITS/PARTIAL until a real loadtest and marker-based worker split proof are recorded.

## Footer

Round-1 worker balance audit for Guinevere P26 highend 2-worker tuning. Read-only audit completed 2026-06-27.
