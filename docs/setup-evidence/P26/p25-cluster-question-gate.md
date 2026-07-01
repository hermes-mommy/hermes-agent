# P26: 9Router Cluster Mode — Question Gate

**Date**: 2026-06-26  
**Output**: `docs/setup-evidence/P26/p25-cluster-question-gate.md`  
**Status**: PENDING Faiz approval

---

## Research Summary

| Item | Finding |
|---|---|
| VPS | 2 CPU cores, 3.9GB RAM, 276MB used |
| 9Router | 1 worker, 3.5GB heap, Node.js 22.23.1 |
| SQLite | WAL mode, safe for multi-worker ✅ |
| Auth | Stateless HMAC + JWT, safe ✅ |
| Streaming | Per-request SSE, safe ✅ |
| Apache | Active, ~10MB, no purpose — kill recommended |
| PM2 | Not installed, cluster mode supported |

## Recommendation

**PM2 cluster with 2 workers, 1.75GB heap each, kill Apache.**

---

## Question 1: Heap per worker

Each worker gets its own V8 heap. Under P25 load test (16K req), single worker used 1.5GB RAM.

| Option | Per Worker | Total | Free RAM | Safety |
|---|---|---|---|---|
| A — Aggressive (Recommended) | 1.75GB | 3.5GB | 400MB | Tight but P25-proven |
| B — Conservative | 1.5GB | 3.0GB | 900MB | Safer, less headroom |

**Mama recommends**: Option A. P25 load test proved 1.5GB under load, 1.75GB gives 250MB buffer. After killing Apache, total free RAM ~400MB for OS + PM2 overhead.

---

## Question 2: Apache

Apache is running on port 80, 2 processes, ~10MB RSS. It serves no purpose.

| Option | Description |
|---|---|
| A — Kill now (Recommended) | systemctl stop + disable apache2, free 10MB |
| B — Kill during cluster migration | Same, but later |
| C — Leave alone | Wastes 10MB, no benefit |

**Mama recommends**: A. Free RAM now, no reason to keep Apache.

---

## Question 3: Migration execution

Both workers try to run migration on first start. Migration is guarded by WeakSet per-process — both workers will race to migrate.

| Option | Description |
|---|---|
| A — Run migration once before cluster (Recommended) | Safe, deterministic, no race |
| B — Let first worker handle it | Works if migration is idempotent, but DB is already migrated |

**Mama recommends**: A. DB is already migrated from P25. No migration needed. Just verify schema is current.

---

## Question 4: systemd fallback

After PM2 cluster is confirmed working, should we keep the systemd service as fallback?

| Option | Description |
|---|---|
| A — Keep systemd disabled (Recommended) | PM2's startup handles boot persistence. systemd kept as backup file |
| B — Remove systemd completely | Cleaner, but no automatic fallback |
| C — Keep both active | Conflict risk — both try to bind port 20128 |

**Mama recommends**: A. Keep systemd service file disabled but present. If PM2 fails, `systemctl start 9router` is instant rollback.

---

## Question 5: Load test

After cluster deployment, verify with load test.

| Option | Description |
|---|---|
| A — Same 16K benchmark (Recommended) | Direct comparison: 1 worker vs 2 workers |
| B — Higher target (32K) | Stress test new capacity |
| C — Skip (rely on P25 test) | Not recommended — no cluster proof |

**Mama recommends**: A. Same 16K req (1K/100cc + 5K/200cc + 10K/300cc). Compare CPU/RAM/errors with single-worker baseline.

---

## Question 6: Log management

PM2 generates logs per worker. Without logrotate, logs grow indefinitely.

| Option | Description |
|---|---|
| A — pm2-logrotate (Recommended) | 10MB × 10 files, compressed, auto-cleanup |
| B — stdout only | No disk usage, but no log history |
| C — Custom log rotation | More control, more maintenance |

**Mama recommends**: A. Standard PM2 setup, zero maintenance.

---

## Question 7: Rollback trigger

What threshold triggers automatic rollback?

| Option | Description |
|---|---|
| A — Any error in load test (Recommended) | Strict: if any request fails, rollback |
| B — Error rate > 0.1% | Lenient: 16 errors in 16K req allowed |
| C — CPU > 80% or RAM > 3.5GB | Resource-based, not error-based |

**Mama recommends**: A. 0 errors in P25 single-worker test. Cluster should match or exceed.

---

## Summary

| Q | Topic | Recommended | Alternative |
|---|---|---|---|
| 1 | Heap | 1.75GB/worker | 1.5GB/worker |
| 2 | Apache | Kill now | Kill during migration |
| 3 | Migration | Verify only (already migrated) | Run migration once |
| 4 | systemd | Keep disabled as fallback | Remove |
| 5 | Load test | 16K same benchmark | 32K or skip |
| 6 | Logs | pm2-logrotate | stdout only |
| 7 | Rollback | Any error → rollback | Error rate > 0.1% |

**All recommendations are defaults. Faiz can override any question.**

---

## Hard Rejection Criteria (from Faiz)

- ❌ No implementation before approval
- ❌ No restart before approval
- ❌ No firewall changes
- ❌ No endpoint changes (baseURL stays 100.104.210.75:20128)
- ❌ No Apache kill without proof of what's running
- ❌ No cluster claim without SQLite/session/streaming analysis
- ❌ No pass claim without load test