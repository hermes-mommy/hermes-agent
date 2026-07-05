# P26 RequestDetails Autoprune Evidence Pass/Fail Analysis

- Date: 2026-06-27
- Scope: read-only research and verification criteria only
- Evidence root: `docs/setup-evidence/P26/requestdetails-autoprune`
- Target table: `requestDetails`
- Output type: pass/fail criteria, hard rejection criteria, audit matrix, and 12-section evidence checklist

## 1. Executive Verdict

Current observed state is **FAIL against the expected bounded `requestDetails` behavior**.

The P26 pre-prune snapshot shows `requestDetails_count|1000`, `requestDetails_total_data_mb|601.27`, and `dbstat requestDetails|605.37|154975`. Prior P25 sizing and inventory research described `requestDetails` as a bounded FIFO detail log capped at 200 records. Therefore, the current evidence indicates the expected FIFO cap is either not active, not set to 200 in the deployed runtime, or insufficient for the observed payload size.

This analysis does not perform pruning, deletion, service restart, timer mutation, firewall change, or payload inspection.

## 2. Inputs Reviewed

| Input | Role | Key Findings |
|---|---|---|
| `AGENTS.md` | Operating contract | Requires evidence-first workflow, file-based structured output, consent/safety boundaries, and no destructive action without explicit approval. |
| `docs/setup-evidence/P26/requestdetails-autoprune/verification/pre-prune-snapshot.md` | Runtime evidence | 9Router online, SQLite WAL mode, `requestDetails` has 1000 rows, ~601.27 MB payload bytes, ~605.37 MB table size, no existing autoprune units/scripts listed. |
| `docs/setup-evidence/P26/requestdetails-autoprune/research/current-dashboard-db-ground-truth.md` | Duplicated ground truth snapshot | Same metrics as pre-prune snapshot. |
| `docs/setup-evidence/P25/research/p25-vps-sizing-2c4gb-capacity-analysis.md` | Prior capacity expectation | States `requestDetails` should be FIFO capped at 200 records and low risk when bounded. |
| `docs/setup-evidence/P25/research/p25-local-config-state-inventory.md` | Prior data inventory | States `requestDetails` is per-request detail logs, max 200 records, FIFO eviction. |
| `docs/setup-evidence/P25/research/p25-local-9router-inventory.md` | Prior local state | Shows local `requestDetails` had 4 records, all errors, and legacy JSON should not be copied. |

## 3. Observed Ground Truth

From the P26 pre-prune snapshot:

| Metric | Observed Value | Pass/Fail Implication |
|---|---:|---|
| `requestDetails_count` | 1000 rows | FAIL if acceptance cap is 200 rows; NEEDS REVIEW if deployed cap intentionally changed to 1000. |
| `requestDetails_total_data_mb` | 601.27 MB | FAIL for a bounded detail log expected to stay small. |
| `requestDetails` dbstat size | 605.37 MB | FAIL for dashboard performance and disk footprint risk. |
| Average `data` length | 630,474.71 bytes | FAIL risk: large payloads make row cap alone insufficient unless payload trimming is added. |
| Maximum `data` length | 2,081,882 bytes | FAIL risk: one row can exceed 2 MB. |
| DB file size | 920 MB main DB, 35 MB WAL | NEEDS REVIEW: not proof of current live bloat alone, but table size is already large. |
| Existing autoprune units/scripts | Empty section | FAIL if acceptance requires an independent scheduled prune. |
| Payload exposure | No `requestDetails.data` printed | PASS for privacy/safety boundary. |
| Mutation | No DB/service/firewall/tailscale mutation | PASS for read-only boundary. |

## 4. Pass/Fail Interpretation

### Current Evidence Verdict

| Criterion | Current Status | Rationale |
|---|---|---|
| `requestDetails` bounded to expected cap | FAIL | Observed count is 1000; prior P25 expectation was max 200 with FIFO eviction. |
| Storage footprint controlled | FAIL | Observed table size is ~605 MB. |
| Payload privacy preserved during research | PASS | Snapshot explicitly avoided printing `requestDetails.data`. |
| Read-only requirement preserved | PASS | Snapshot states no DB mutation or service/network changes. |
| Autoprune mechanism present | FAIL / NEEDS REVIEW | Snapshot section for existing autoprune units/scripts is empty; app-level FIFO may exist but is not proven effective. |
| Dashboard health preserved | NEEDS REVIEW | `/dashboard/usage` redirects quickly, API endpoints require auth; no authenticated dashboard timing evidence was captured. |

### Root Cause Hypotheses To Verify Later

1. Application FIFO cap is configured at 1000 rather than 200.
2. FIFO cap applies by count only, but large `data` payloads make 1000 rows too large.
3. FIFO eviction runs only on writes and may not reclaim SQLite pages without checkpoint/vacuum planning.
4. Clustered PM2 workers may race or bypass a single-worker FIFO assumption.
5. Deployed 9Router version changed `requestDetails` retention behavior from the P25 assumption.

These are hypotheses, not confirmed root cause.

## 5. Acceptance Criteria

The future implementation should be accepted only if all criteria below pass.

| ID | Acceptance Criterion | Required Evidence | PASS Definition |
|---|---|---|---|
| AC-01 | `requestDetails` row count is bounded. | SQL count before/after plus retention config/code proof. | Row count is `<= 200` after prune/autoprune, unless a newer approved plan explicitly sets a different cap and documents why. |
| AC-02 | Oldest rows are pruned deterministically. | SQL min/max timestamp before/after with no payload content. | Rows removed are the oldest by `timestamp` or a documented stable insertion key; newest rows remain. |
| AC-03 | Payload privacy is preserved. | Evidence commands and outputs. | No `requestDetails.data` payload content appears in evidence, logs, terminal transcript, or committed artifacts. |
| AC-04 | Implementation is automatic. | Code/config/timer/service proof. | Autoprune runs without manual SQL after startup/write path or via approved scheduled job. |
| AC-05 | Cluster safety is handled. | Code review or runtime proof under two PM2 workers. | Concurrent workers cannot exceed cap persistently or corrupt DB state. |
| AC-06 | SQLite durability is preserved. | PRAGMA and post-run integrity checks. | `PRAGMA integrity_check` returns `ok`; WAL mode remains expected; no lock/corruption errors. |
| AC-07 | Dashboard remains healthy. | Authenticated or appropriate endpoint timing proof. | Dashboard/API returns expected status and acceptable latency after pruning; no regression in model endpoint health. |
| AC-08 | Storage footprint improves or is bounded. | DB size/table dbstat/WAL metrics before and after. | `requestDetails` table bytes fall materially after prune, or retained rows are proven bounded and future compaction plan is documented. |
| AC-09 | No unrelated data is pruned. | Counts for `usageHistory`, `usageDaily`, and other critical tables before/after. | Only intended `requestDetails` rows are deleted or trimmed. |
| AC-10 | Autoprune is observable. | Log/audit output without sensitive payload. | Prune run records row count pruned, retained count, status, and errors without secrets or payload. |
| AC-11 | Rollback/re-run safety exists. | Backup/copy evidence and idempotency notes. | Re-running autoprune is safe; rollback path is documented for code/config changes. |
| AC-12 | Evidence and auditor gate are complete. | `verification.md` and `auditor-gate.md`. | Evidence has all 12 sections and independent audit returns PASS or documented false-positive disposition. |

## 6. Hard Rejection Criteria

Any item below blocks completion.

| ID | Hard Rejection Criterion | Why It Blocks |
|---|---|---|
| HR-01 | Evidence prints raw `requestDetails.data` payload content. | Violates privacy and personal/intimate data exposure boundary. |
| HR-02 | Implementation deletes or mutates tables other than `requestDetails` without explicit scoped approval. | Hidden data-loss risk. |
| HR-03 | Prune criteria are non-deterministic or not ordered by a stable timestamp/insertion key. | Could delete newer or arbitrary records. |
| HR-04 | Post-prune `requestDetails_count` remains above accepted cap with no approved exception. | Fails core goal. |
| HR-05 | SQLite `PRAGMA integrity_check` fails or DB lock/corruption appears after change. | Data integrity regression. |
| HR-06 | 9Router health check fails after change. | Runtime regression. |
| HR-07 | Firewall/Tailscale/public exposure state changes during this task without explicit approval. | Network boundary drift. |
| HR-08 | PM2/service restart occurs without being required and documented in the implementation plan. | Unscoped runtime mutation. |
| HR-09 | Autoprune requires manual one-off SQL only and has no automatic path. | Does not solve recurrence. |
| HR-10 | Evidence is missing 12-section verification or auditor gate. | Violates project evidence contract. |
| HR-11 | Secrets, DB credentials, tokens, or surveillance/personal data are committed or pasted into artifacts. | Security and consent boundary violation. |
| HR-12 | Failing tests/checks are skipped, deleted, or reclassified without root-cause evidence. | Verification suppression. |

## 7. Audit Matrix

| Audit Surface | Audit Question | Evidence Required | PASS Signal | FAIL Signal |
|---|---|---|---|---|
| Scope control | Did the task only touch approved files/systems? | Git diff, command log, changed-file list. | Only planned files changed; read-only research only changed this report. | Unplanned source/config/runtime changes. |
| Data retention | Is `requestDetails` capped correctly? | SQL counts and timestamps before/after. | Count `<= cap`; oldest removed; newest retained. | Count above cap or arbitrary deletion. |
| Payload minimization | Was sensitive request payload kept out of evidence? | Evidence artifacts and grep for risky payload dumps. | Only lengths/counts/metadata included. | Raw `data` body or request content appears. |
| SQLite integrity | Did DB remain healthy? | `PRAGMA integrity_check`, WAL mode, relevant logs. | `ok`, no corruption/lock errors. | Integrity failure or persistent lock errors. |
| Cluster behavior | Does cap hold with two PM2 workers? | PM2 status plus write-path or runtime validation. | Both workers online; cap still enforced. | Cap drifts upward under cluster writes. |
| Dashboard behavior | Does dashboard/API remain usable? | HTTP status/timing checks with expected auth behavior. | Expected status codes and stable timings. | 5xx, timeouts, auth regressions, slow dashboard. |
| Storage effect | Does table/database footprint improve or remain bounded? | DB file, WAL, dbstat before/after. | Table bytes reduced or bounded; WAL managed. | Footprint grows unbounded or WAL balloons. |
| Observability | Are prune outcomes logged safely? | Log excerpt without payload. | Row counts and status logged. | Silent prune or logs expose payload/secrets. |
| Idempotency | Is repeated run safe? | Re-run proof or reasoning plus command output. | Second run prunes 0 or maintains cap without errors. | Re-run deletes too much or fails. |
| Rollback | Can code/config change be reverted? | Backup path, diff, rollback commands. | Clear rollback and pre-change snapshot. | No rollback route. |
| Governance | Are AGENTS and safety boundaries preserved? | Boundary compliance section. | No HARD STOP, consent, surveillance, persona, or secret boundary touched. | Boundary drift or missing review. |
| Auditor gate | Did an independent audit pass? | Auditor report path. | PASS or documented false-positive disposition. | FAIL/NEEDS REVIEW unresolved. |

## 8. Recommended Verification Commands For Future Implementation

These commands are criteria templates. They must be adapted to the actual host/session and must not print `requestDetails.data`.

| Purpose | Command Pattern | Expected Result |
|---|---|---|
| Count rows | `sqlite3 /var/lib/9router/db/data.sqlite "SELECT count(*) FROM requestDetails;"` | `<= 200` after autoprune. |
| Timestamp range | `sqlite3 /var/lib/9router/db/data.sqlite "SELECT min(timestamp), max(timestamp) FROM requestDetails;"` | Shows retained recent window. |
| Payload size metadata only | `sqlite3 /var/lib/9router/db/data.sqlite "SELECT round(sum(length(data))/1024.0/1024.0,2), round(avg(length(data)),2), max(length(data)) FROM requestDetails;"` | Numeric sizes only; no payload content. |
| Table footprint | `sqlite3 /var/lib/9router/db/data.sqlite "SELECT name, round(sum(pgsize)/1024.0/1024.0,2) FROM dbstat WHERE name='requestDetails' GROUP BY name;"` | Materially reduced or bounded. |
| Integrity | `sqlite3 /var/lib/9router/db/data.sqlite "PRAGMA integrity_check;"` | `ok`. |
| Related table counts | `sqlite3 /var/lib/9router/db/data.sqlite "SELECT 'usageHistory', count(*) FROM usageHistory UNION ALL SELECT 'usageDaily', count(*) FROM usageDaily;"` | No unintended deletion. |
| Runtime health | `curl -sS -o /dev/null -w "%{http_code} %{time_total}\n" http://127.0.0.1:20128/v1/models` | HTTP 200 and stable timing. |
| Exposure boundary | Tailscale and public endpoint probes | Tailscale expected reachable; public IPv4 remains blocked if that is current policy. |

## 9. 12-Section Evidence Checklist

Future `verification.md` should include all sections below.

### 1. What Was Done

- State whether the work was research-only, code/config implementation, runtime prune, scheduled autoprune, or a combination.
- Include exact cap and retention strategy.
- Identify whether pruning is count-based, age-based, size-based, or hybrid.

### 2. Files Changed

- List exact repository files modified.
- List exact runtime files modified only if explicit approval and scope allow it.
- Include `git diff --stat` or equivalent file-level summary.

### 3. Validation Results

- Include row count before/after.
- Include timestamp range before/after.
- Include SQLite integrity check.
- Include runtime health checks.
- Include dashboard/API status checks.

### 4. Evidence Artifacts

- Link pre-prune snapshot.
- Link post-prune snapshot.
- Link implementation log.
- Link auditor gate.
- Link any runtime command transcript with payload-safe output.

### 5. Doc-Sync Impact

- State whether P25/P26 plan assumptions changed.
- If the accepted cap differs from 200, document the approved new cap and update the relevant plan/evidence references.
- State whether docs index updates are needed.

### 6. Boundary Compliance

- Confirm no raw `requestDetails.data` payload content was printed.
- Confirm no secrets, DB passwords, tokens, or surveillance/intimate data were exposed.
- Confirm no consent, persona, HARD STOP, or surveillance policy boundaries changed.
- Confirm no firewall/Tailscale exposure changes occurred unless explicitly in scope.

### 7. Rollback/Re-run Safety

- Document pre-change backup or snapshot.
- Document how to revert code/config changes.
- Document expected behavior of a second autoprune run.
- Document whether SQLite VACUUM/checkpoint was used, skipped, or deferred and why.

### 8. Design Decisions/Caveats

- Explain why the chosen cap/retention strategy is adequate.
- Explain whether count cap alone is enough given observed large payloads.
- Note cluster concurrency assumptions.
- Note any remaining dashboard timing limitations.

### 9. Auditor Gate

- Provide auditor report path.
- Include auditor verdict: PASS, NEEDS REVIEW, or FAIL.
- Document any false-positive disposition.
- Completion requires PASS or explicit accepted false-positive rationale.

### 10. Security Scan

- Include grep/check results for secrets and raw payload leakage in evidence files.
- Include review of command outputs for accidental data exposure.
- Include confirmation that no destructive out-of-scope command was run.

### 11. Acceptance Criteria Mapping

- Map AC-01 through AC-12 to evidence.
- Each criterion must be PASS, FAIL, NEEDS REVIEW, or NOT APPLICABLE with rationale.
- Any FAIL blocks completion.

### 12. Footer

- Include date/time and timezone.
- Include operator/session scope.
- Include final verdict.
- Include next action if any.

## 10. Suggested Implementation-Audit Scaffolds

### Scaffold A: Research-Only Evidence

| Field | Required Value |
|---|---|
| Expected Files | `docs/setup-evidence/P26/requestdetails-autoprune/research/evidence-passfail-analysis.md` |
| Forbidden Patterns | Raw `requestDetails.data` payload content; secrets; DB passwords; API keys; Discord tokens; destructive commands in evidence. |
| Required Commands | Read `AGENTS.md`; read P26 snapshot files; search P25/P26 for `requestDetails` assumptions; verify output file exists. |
| Evidence Requirements | This research file only; no `verification.md` required for implementation because no implementation occurred. |
| Hard Rejection Criteria | Any DB/service/network mutation; any raw payload exposure; missing acceptance criteria; missing hard rejection criteria; missing audit matrix; missing 12-section evidence checklist. |

### Scaffold B: Future Runtime Autoprune Implementation

| Field | Required Value |
|---|---|
| Expected Files | Exact source/config/runtime files must be declared by planner before implementation. |
| Forbidden Patterns | `as any`, `@ts-ignore`, `@ts-expect-error`, `# type: ignore`, empty catch/except, raw `requestDetails.data` in logs/evidence, unscoped `DELETE` without deterministic predicate. |
| Required Commands | SQLite count/range/size checks; `PRAGMA integrity_check`; runtime health; related table counts; relevant app tests if code is changed. |
| Evidence Requirements | `docs/setup-evidence/P26/requestdetails-autoprune/verification/verification.md` and `docs/setup-evidence/P26/requestdetails-autoprune/audit/auditor-gate.md`. |
| Hard Rejection Criteria | Any HR-01 through HR-12 finding. |

## 11. Boundary Compliance For This Research

- Read-only analysis only.
- No database prune/delete/update/insert executed.
- No service restart executed.
- No firewall or Tailscale mutation executed.
- No raw `requestDetails.data` payload content included.
- No secrets or credentials included.
- No consent/surveillance/persona/HARD STOP boundary changed.

## 12. Final Recommendation

Treat P26 `requestDetails` autoprune as a required fix unless an approved newer 9Router retention target intentionally changed the cap from 200 to 1000. Even if 1000 rows is intentional, the observed payload size means a row-count-only cap is not enough for disk/dashboard safety. The implementation should enforce a deterministic cap, preserve newest rows, avoid payload logging, prove SQLite integrity, and produce complete 12-section verification plus independent auditor gate before completion.

