# P26 High-End 2-Worker Tuning: Loadtest Auditor Design Analysis

**Date**: 2026-06-27  
**Role**: Read-only research sub-agent  
**Scope**: Auditor design for validating 9Router VPS loadtest evidence without mutating the VPS  
**VPS target**: `root@49.12.82.34 -p 39999`  
**Output path**: `docs/setup-evidence/P26/highend-2worker-tuning/research/loadtest-design-analysis.md`

---

## 1. Executive Verdict

The safest auditor design is a **read-only baseline/post comparison** around `/v1/models`, PM2 worker state, resource usage, connection counts, and error counters, followed by a **low-quota real model smoke** that proves end-to-end routing without running high-rate traffic against real providers.

The existing P26 evidence already shows a successful 100-subagent workflow burst, but that test was capped by the workflow/orchestration layer rather than by 9Router. A stronger auditor should therefore require:

1. Baseline and post-test `/v1/models` checks.
2. Evidence that **both PM2 workers remain online and stable**.
3. Lightweight proof that load is not pinned to only one worker.
4. Metrics captured before, during, and after the test.
5. Strict abort rules for resource pressure, restarts, Tailscale degradation, model-list regressions, and provider quota risk.

No VPS mutation is required for this design. Commands below intentionally avoid reading environment files, raw secrets, raw provider configs, or unfiltered logs.

---

## 2. Local Context Read

Read and used these local sources:

| Source | Relevant Finding |
|---|---|
| `AGENTS.md` | Read first. Enforces no secrets, no destructive actions, file-based output, and read-only discipline. |
| `docs/setup-evidence/P26/p26-implementation.md` | P26 converted 9Router to PM2 cluster mode with 2 workers, 1.8 GB heap each, PM2 startup, pm2-logrotate, systemd fallback disabled. |
| `docs/setup-evidence/P26/p25-cluster-inventory.md` | VPS is 2-core / 4 GB RAM; 9Router uses SQLite WAL; port `20128`; Tailscale IP documented as `100.104.210.75`. |
| `docs/setup-evidence/P26/p25-cluster-question-gate.md` | Recommended same benchmark after cluster migration and strict rollback on any loadtest error. |
| `docs/setup-evidence/P26/loadtest-100-subagents/final-report.md` | Existing 100-subagent test passed with 0 hard errors but only ~28.4 RPM effective throughput due to workflow cap. |
| `docs/setup-evidence/P26/loadtest-100-subagents/vps-runtime-snapshot.md` | Existing snapshot showed two workers online, no PM2 restart increase, tailscaled active, and minimal resource movement. |
| `docs/setup-evidence/P25/research/p25-load-test-design-refresh.md` | Earlier load design recommends mock upstream for high-rate load and only tiny real-provider smoke to avoid quota burn. |

---

## 3. Live Read-Only Snapshot

A safe SSH snapshot was collected without reading env files, raw logs, provider secrets, or making service changes.

| Check | Observed Result |
|---|---|
| Host | `ninerouter-vps` |
| Snapshot time | `2026-06-27T18:01:14+07:00` |
| `/v1/models` | `models_count=44`; first IDs: `orcestrator,subagent,tester` |
| PM2 workers | 2 online workers, version `0.5.8`, cluster mode |
| Worker memory | about `245.7 MB` and `312.8 MB` |
| PM2 restarts | `4` per worker, unchanged by this read-only check |
| pm2-logrotate | online |
| Memory | 4000 MB total, 3371 MB available |
| Load average | `0.08, 0.12, 0.12` |
| Tailscale | `active` |
| Port | `0.0.0.0:20128` listening |

Important mismatch: older P26 evidence says `/v1/models` returned 74 models, while the live read-only snapshot observed 44. This is not automatically a failure for loadtesting, but it must be treated as a **baseline value** for the current tuning run. A post-test model count lower than this baseline is a regression unless an approved config change explains it.

---

## 4. Safety Rules for the Auditor

The auditor must not:

- Restart PM2, systemd, 9Router, Apache, Tailscale, or the VPS.
- Run `pm2 restart`, `pm2 reload`, `pm2 delete`, `pm2 save`, `systemctl restart`, `systemctl stop`, `systemctl disable`, `ufw`, `iptables`, `nft`, or firewall commands.
- Read `/var/lib/9router/.env`, `/etc/9router/env`, provider config dumps, decrypted secrets, shell history, or raw credential files.
- Print API keys, DB passwords, JWT secrets, provider keys, Tailscale auth keys, or raw sensitive prompts.
- Run high-rate load against real providers.
- Write files on the VPS as part of the audit.

The auditor may:

- Run `curl` against `http://127.0.0.1:20128/v1/models`.
- Run `pm2 status --no-color`.
- Run `free`, `uptime`, `ss`, `ps`, `systemctl is-active tailscaled`, and read-only resource probes.
- Count filtered error terms from PM2 logs only if output is counts, not raw log lines.
- Run a low-quota real model smoke only when an operator-supplied key is read silently and never printed.

---

## 5. Safe Baseline Commands

Run these before any loadtest. They are read-only and avoid secrets.

### 5.1 Local SSH Wrapper

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=8 root@49.12.82.34 'bash -s' <<'AUDIT'
set -eu
echo "=== BASELINE $(date -Is) ==="

echo "--- host ---"
hostname
uptime

echo "--- /v1/models shape ---"
curl -fsS http://127.0.0.1:20128/v1/models \
  | python3 -c 'import sys,json; j=json.load(sys.stdin); d=j.get("data", []); print("models_count=%s" % len(d)); print("first_model_ids=%s" % ",".join([str(x.get("id", "")) for x in d[:5]]))'

echo "--- pm2 status ---"
pm2 status --no-color

echo "--- memory ---"
free -m

echo "--- tailscale ---"
printf "tailscaled="
systemctl is-active tailscaled || true

echo "--- listener ---"
ss -ltn '( sport = :20128 )'

echo "--- tcp summary ---"
ss -s
AUDIT
```

### 5.2 Minimal `/v1/models` Baseline Only

Use this when the auditor only needs model availability and count.

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=8 root@49.12.82.34 \
  'curl -fsS http://127.0.0.1:20128/v1/models | python3 -c '\''import sys,json; d=json.load(sys.stdin).get("data", []); print("models_count=%s" % len(d)); print("ids_sample=%s" % ",".join([x.get("id","") for x in d[:5]]))'\'''
```

### 5.3 Baseline Acceptance

Baseline must pass before load starts:

| Check | Pass Criteria |
|---|---|
| SSH | Connects within 8 seconds using batch mode |
| `/v1/models` | HTTP 200 and JSON parses |
| Model count | Non-zero and recorded as baseline |
| PM2 | Exactly 2 9Router workers online |
| Tailscale | `active` |
| Port | `0.0.0.0:20128` or expected listener present |
| RAM | At least 1000 MB available before test |
| Restarts | PM2 restart count recorded for later comparison |

Abort if baseline fails.

---

## 6. Safe Post-Test Commands

Run immediately after the loadtest and again after a 60-second cool-down.

```bash
ssh -p 39999 -o BatchMode=yes -o ConnectTimeout=8 root@49.12.82.34 'bash -s' <<'AUDIT'
set -eu
echo "=== POST $(date -Is) ==="

echo "--- /v1/models shape ---"
curl -fsS http://127.0.0.1:20128/v1/models \
  | python3 -c 'import sys,json; j=json.load(sys.stdin); d=j.get("data", []); print("models_count=%s" % len(d)); print("first_model_ids=%s" % ",".join([str(x.get("id", "")) for x in d[:5]]))'

echo "--- pm2 status ---"
pm2 status --no-color

echo "--- resources ---"
free -m
uptime

echo "--- tailscale ---"
printf "tailscaled="
systemctl is-active tailscaled || true

echo "--- listener ---"
ss -ltn '( sport = :20128 )'

echo "--- tcp summary ---"
ss -s

echo "--- filtered error counts only ---"
pm2 logs 9router --nostream --lines 300 2>/dev/null \
  | grep -Eci 'error|fatal|uncaught|unhandled|SQLITE_BUSY|SQLITE_CORRUPT|ENOMEM|EADDRINUSE|ECONNRESET|ETIMEDOUT' \
  || true
AUDIT
```

Post-test must pass:

| Check | Pass Criteria |
|---|---|
| `/v1/models` | Still HTTP 200 and parseable JSON |
| Model count | Same as baseline unless operator-approved config changed |
| PM2 workers | Exactly 2 workers online |
| PM2 restarts | No increase during test |
| PM2 unstable restarts | 0 |
| Tailscale | Still `active` |
| Listener | Port `20128` still listening |
| RAM | At least 750 MB available after cool-down |
| Error count | 0 matching hard error patterns |

---

## 7. Lightweight Worker Split Evidence Approach

Goal: prove the cluster remains healthy and that traffic does not appear pinned to only one worker, without changing code or reading secrets.

### 7.1 Evidence to Capture

Capture three snapshots:

1. `baseline`: before load.
2. `during`: while load is actively running.
3. `post`: immediately after load.

Each snapshot should include:

```bash
pm2 status --no-color
ps -o pid,ppid,pcpu,pmem,rss,etime,comm -p "$(pgrep -d, -f 'custom-server.js' || true)" 2>/dev/null || true
ss -tan state established '( sport = :20128 )' | wc -l
```

If `pidstat` is available, add:

```bash
PIDS="$(pgrep -d, -f 'custom-server.js' || true)"
if command -v pidstat >/dev/null 2>&1 && [ -n "$PIDS" ]; then
  pidstat -h -r -u -p "$PIDS" 1 10
fi
```

### 7.2 Interpretation

| Observation | Meaning |
|---|---|
| Both workers online before/during/post | Cluster stability PASS |
| Both workers show non-zero CPU at least once during active load | Strong split evidence |
| One worker CPU changes and the other stays flat | Needs review; could be low load, sticky connection behavior, or pinned traffic |
| Memory grows on both workers under concurrent streaming | Supporting split evidence |
| PM2 restart count increases | FAIL |
| One worker disappears or changes status | FAIL |

### 7.3 Low-Impact Split Probe

This probe only calls `/v1/models` repeatedly. It is safe but not strong enough as the only proof because `/v1/models` is lightweight.

```bash
ssh -p 39999 -o BatchMode=yes root@49.12.82.34 'bash -s' <<'AUDIT'
set -eu
echo "=== worker split lightweight probe $(date -Is) ==="
for i in $(seq 1 50); do
  curl -fsS -o /dev/null http://127.0.0.1:20128/v1/models
done
pm2 status --no-color
ps -o pid,ppid,pcpu,pmem,rss,etime,comm -p "$(pgrep -d, -f 'custom-server.js' || true)" 2>/dev/null || true
AUDIT
```

The stronger proof is to run the planned load generator separately, then sample PM2 and per-PID resource movement during that load. The auditor should not start the high-rate load unless explicitly tasked to execute, because this report is design-only.

---

## 8. Low-Quota Real Model Smoke Design

Purpose: prove live provider routing works through 9Router after tuning. This is not a loadtest.

### 8.1 Safety Constraints

- Total requests: 4 to 10.
- Rate: 1 request every 2 to 5 seconds.
- `max_tokens`: 16 to 32.
- Prompt: non-sensitive synthetic prompt only.
- No high-rate real-provider testing.
- Do not paste or echo keys.
- Do not store raw provider keys in files.
- Do not use shell tracing (`set -x`).
- Prefer already-configured 9Router provider credentials; only the 9Router client API key should be entered by operator if required.

### 8.2 Key Handling Pattern

Use silent input and curl config via stdin so the key is not printed in the terminal output. The key can still exist briefly in shell memory; do not run this on shared terminals, do not use `set -x`, and do not paste it into artifacts.

```bash
read -rsp "9Router API key: " NINEROUTER_API_KEY
printf '\n'
export NINEROUTER_API_KEY
```

### 8.3 Non-Streaming Smoke

```bash
for i in $(seq 1 3); do
  curl -fsS --config - <<EOF \
    | python3 -c 'import sys,json; j=json.load(sys.stdin); print("ok choice_count=%s usage_present=%s model=%s" % (len(j.get("choices", [])), "usage" in j, j.get("model", "")))'
url = "http://127.0.0.1:20128/v1/chat/completions"
request = "POST"
header = "Content-Type: application/json"
header = "Authorization: Bearer ${NINEROUTER_API_KEY}"
data = "{\"model\":\"subagent\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with exactly one short sentence.\"}],\"stream\":false,\"max_tokens\":24}"
EOF
  sleep 2
done
unset NINEROUTER_API_KEY
```

### 8.4 Streaming Smoke

```bash
read -rsp "9Router API key: " NINEROUTER_API_KEY
printf '\n'
export NINEROUTER_API_KEY

for i in $(seq 1 3); do
  curl -fsS --no-buffer --config - <<EOF \
    | awk 'BEGIN{done=0; chunks=0} /^data: /{chunks++} /\[DONE\]/{done=1} END{printf "chunks=%d done=%s\n", chunks, done ? "yes" : "no"; exit(done ? 0 : 1)}'
url = "http://127.0.0.1:20128/v1/chat/completions"
request = "POST"
header = "Content-Type: application/json"
header = "Authorization: Bearer ${NINEROUTER_API_KEY}"
data = "{\"model\":\"subagent\",\"messages\":[{\"role\":\"user\",\"content\":\"Reply with five words.\"}],\"stream\":true,\"max_tokens\":24}"
EOF
  sleep 2
done
unset NINEROUTER_API_KEY
```

### 8.5 Smoke Pass/Fail

| Check | PASS | FAIL |
|---|---|---|
| Non-streaming HTTP | All requests return 2xx | Any 5xx, connection failure, timeout |
| Non-streaming shape | `choices` exists | Missing choices or invalid JSON |
| Streaming shape | SSE chunks observed and `[DONE]` present | Missing chunks, missing `[DONE]`, malformed stream |
| Quota usage | 4-10 tiny requests only | Any loop above agreed count |
| Secrets | Key never printed or stored | Key appears in output/artifact/history |

---

## 9. Metrics Collection Matrix

| Metric | Command | Timing | Pass Gate |
|---|---|---|---|
| Model count | `curl /v1/models | python3 ...` | Baseline, post, cool-down | Same count as baseline |
| Worker online state | `pm2 status --no-color` | Baseline, during, post | 2 online workers |
| Worker restarts | `pm2 status --no-color` | Baseline, post | No increase |
| Worker CPU/RSS | `pm2 status`; `ps -o pid,pcpu,pmem,rss` | Baseline, during, post | No single worker runaway |
| System memory | `free -m` | Baseline, during, post | >750 MB available post; >500 MB during |
| Load average | `uptime` | Baseline, during, post | 1m load not sustained above 2.0 after cool-down |
| Tailscale | `systemctl is-active tailscaled` | Baseline, post | `active` |
| Listener | `ss -ltn '( sport = :20128 )'` | Baseline, post | Port still listening |
| TCP pressure | `ss -s`; established count | During, post | No persistent TIME_WAIT/established explosion after cool-down |
| Hard error patterns | Filtered count from PM2 logs | Post only | 0 |
| SQLite trouble | Filtered count for `SQLITE_BUSY`, `SQLITE_CORRUPT` | Post only | 0 |

Do not capture raw PM2 logs into evidence unless they are manually reviewed and redacted. Prefer counts and structured summaries.

---

## 10. Pass/Fail Criteria

### 10.1 PASS

All must be true:

- Baseline `/v1/models` succeeds and model count is recorded.
- Post-test `/v1/models` succeeds and model count matches baseline.
- Both PM2 workers are online before, during, and after.
- PM2 restart count does not increase.
- Tailscale remains active.
- Port `20128` remains listening.
- No hard error patterns in filtered PM2 log count.
- No `SQLITE_BUSY`, `SQLITE_CORRUPT`, OOM, fatal, uncaught, or unhandled errors.
- Memory available remains above 750 MB after cool-down.
- Real-model smoke, if run, uses <=10 low-token requests and passes shape checks.
- No secrets are printed or stored.

### 10.2 PASS_WITH_LIMITATION

Use when the VPS remains healthy but the test does not prove maximum capacity. Examples:

- Workflow/sub-agent orchestration caps concurrency, as in the existing 100-subagent test.
- No per-request latency percentiles are captured.
- Load is real-provider-limited rather than proxy-limited.
- Worker split evidence is inconclusive because the load is too light.

### 10.3 NEEDS REVIEW

Use when:

- Model count differs from baseline but endpoint still works.
- One worker shows no resource movement while the other does all visible work.
- Filtered warnings appear but no hard errors.
- Memory grows by more than 100 MB and does not return near baseline after cool-down.
- TCP connections remain high after 60 seconds.

### 10.4 FAIL

Any one is enough:

- `/v1/models` fails after test.
- PM2 worker count drops below 2.
- PM2 restart count increases during test.
- Tailscale becomes inactive.
- Port `20128` stops listening.
- Any 9Router 5xx spike attributable to the test.
- Any hard error pattern: `fatal`, `uncaught`, `unhandled`, `SQLITE_CORRUPT`, OOM, `ENOMEM`, repeated `SQLITE_BUSY`.
- Real-model smoke leaks a key into output or artifact.
- High-rate load is accidentally run against real providers.

---

## 11. Abort Conditions

Abort the test immediately if any condition appears:

| Condition | Abort Action |
|---|---|
| SSH becomes unreliable or times out repeatedly | Stop test generator; collect post snapshot if possible |
| `/v1/models` fails baseline | Do not start load |
| Tailscale inactive | Do not start or continue load |
| PM2 worker not online | Do not start or continue load |
| PM2 restart count increases | Stop load and mark FAIL |
| Available RAM <500 MB during test | Stop load; wait cool-down; collect post snapshot |
| Load average >4.0 for more than 30 seconds on 2 vCPU | Stop load; collect resource snapshot |
| Filtered PM2 hard error count >0 | Stop load; mark FAIL or NEEDS REVIEW depending severity |
| Any secret appears in output | Stop, redact evidence, record violation |
| Real provider returns quota/rate-limit errors | Stop smoke; do not retry loops blindly |
| Operator says `HARD STOP` | Stop all persona behavior and halt |

The auditor should not perform rollback actions. Rollback is an operator/implementation decision because it mutates service state.

---

## 12. Recommended Evidence Layout

For a future executed audit, write:

```text
docs/setup-evidence/P26/highend-2worker-tuning/evidence/
  baseline.md
  during-snapshots.md
  post-test.md
  real-smoke-summary.md
  auditor-gate.md
```

Each evidence file should include:

- Command executed.
- Timestamp.
- Sanitized output.
- PASS/FAIL interpretation.
- Caveats.
- Secret-safety note.

Do not store raw API keys, raw env files, raw provider configs, raw shell history, or unredacted logs.

---

## 13. Auditor Checklist

| Item | Status Needed |
|---|---|
| AGENTS.md read first | Required |
| Baseline `/v1/models` captured | Required |
| Baseline PM2 status captured | Required |
| Baseline memory/load captured | Required |
| Load generator scope documented | Required |
| During-load worker snapshots captured | Required for worker split claim |
| Post `/v1/models` captured | Required |
| Post PM2 status captured | Required |
| Restart delta checked | Required |
| Tailscale status checked | Required |
| Filtered error count checked | Required |
| Low-quota smoke bounded to <=10 requests | Required if real smoke is run |
| Secret leakage scan of produced evidence | Required |
| PASS/FAIL/NEEDS REVIEW verdict written | Required |

---

## 14. Final Recommendation

Use the existing 100-subagent P26 result as a **functional resilience proof**, not as a maximum-capacity proof. For high-end 2-worker tuning, require a fresh read-only auditor gate around any new loadtest:

1. Baseline `/v1/models` and PM2 worker state.
2. Run the agreed load generator.
3. Capture during-load PM2/per-PID resource snapshots.
4. Post-test `/v1/models`, PM2, Tailscale, listener, memory, and filtered error counts.
5. Run only a tiny real-model smoke, never high-rate real-provider traffic.

Current live baseline for this design: `/v1/models` returns 44 models and PM2 shows two online 9Router workers. Treat `44` as the current baseline unless a new pre-test snapshot says otherwise.

---

## 15. Footer

**Status**: COMPLETE  
**Mutation performed**: None on VPS. Local output file only.  
**Secret exposure**: None. Commands avoid env files and raw provider config.  
**Read-only SSH used**: Yes, limited to `/v1/models`, PM2 status, memory/load, Tailscale active state, and listener state.  
**Caveat**: This document is a design/auditor report; it does not execute a new loadtest.
