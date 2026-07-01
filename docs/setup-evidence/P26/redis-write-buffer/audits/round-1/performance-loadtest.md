# P26.1 Audit - Performance Loadtest

Date: 2026-06-28
Scope: reality of the authenticated loadtest, throughput metrics, PM2 stability, backlog drain, and lock regression signals.

## Evidence Reviewed
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\loadtest-results.raw.json`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\sqlite-lock-proof.md`
- `C:\Users\faizz\guinevere\docs\setup-evidence\P26\redis-write-buffer\runtime\worker-health-proof.md`

## Findings

### INFO - Chat latency is materially higher than `/v1/models`, but the observed profile is consistent with the scoped mixed-endpoint test
- `/v1/models` stayed sub-second at p99 across all phases.
- Chat completions showed multi-second latency with a heavy tail, which is expected for upstream model execution and does not by itself indicate buffer regression.
- No restart storm, pending drain failure, deadletter growth, or active-worker lock growth was observed during the authenticated run.

## Verdict

`PASS`

The loadtest is real, materially exercised the production path, and stayed inside the required safety envelope: exactly 2 PM2 workers, `0` restart growth, `0` deadletter growth, and `0` active-worker SQLite busy growth across the `50/200/700` phases.
