# P25 Research Summary: 9Router VPS Migration

> **Phase**: P25 — Research Only
> **Date**: 2026-06-25
> **Author**: Agent (automated research)
> **Status**: RESEARCH COMPLETE — 2C4GB CONDITIONAL, LOAD TEST REQUIRED

---

## 1. Executive Summary

P25 investigated whether the existing local 9Router instance (a Node.js API proxy serving Claude Code and OpenCode traffic) can be migrated to a dedicated VPS to handle ~1000 requests per minute.

**Verdict: CONDITIONAL PASS on 2 vCPU / 4 GB RAM.**

9Router is I/O-bound, not CPU-bound. At 1000 req/min with typical coding request durations (10-30s), memory is the binding constraint. At 30s average duration, concurrency reaches ~500 — comfortably within 4 GB. At 60s average duration (worst case), concurrency reaches ~1000 — tight on 4 GB.

**Conditions for production readiness:**
1. Average request duration must stay at or below 30s
2. Node.js heap limited to 2 GB (not the default 6 GB)
3. `usageHistory` pruned regularly (30-day retention)
4. Load test must pass before claiming ready

If the load test fails at 2c/4GB, upgrade to 4c/8GB (estimated $24-48/month). Rollback to local 9Router is instant: change one environment variable.

**Key advantage: Zero risk to production.** The migration touches a completely separate VPS, separate Tailscale IP, separate systemd service, and separate data directory. Hermes/P20/Guinevere remain untouched.

---

## 2. Final Status

```
P25 RESEARCH COMPLETE — 2C4GB CONDITIONAL, LOAD TEST REQUIRED
```

**Conditions:**
- Average request duration <= 30s (typical for coding workloads)
- Node.js heap tuned to 2 GB (not default 6 GB)
- `usageHistory` pruned regularly (30-day retention)
- Load test passes at target throughput before production use

**If load test fails at 2c/4GB:** Upgrade to 4c/8GB.

---

## 3. The 18 Research Questions — Answered

### Q1: Where is local 9Router installed?

**Answer:** npm global install.

| Component | Path |
|-----------|------|
| Package | `C:\Users\faizz\AppData\Roaming\npm\node_modules\9router\` |
| Binary | `C:\Users\faizz\AppData\Roaming\npm\9router.cmd` |
| Data dir | `C:\Users\faizz\AppData\Roaming\9router\` |

**Ref:** `p25-local-9router-inventory.md`

---

### Q2: How is local 9Router started?

**Answer:** CLI command. On VPS, systemd service.

- Local: `9router` or `9router --port 20128 --host 0.0.0.0 --no-browser --skip-update`
- VPS (planned): `ExecStart=/usr/bin/9router --port 20128 --host 0.0.0.0 --no-browser --skip-update`

**Ref:** `p25-systemd-service-design.md`

---

### Q3: Is it Node/npm/binary/Docker?

**Answer:** Node.js npm package. Published on npmjs.com as `9router`. Not Docker. Not a standalone binary. It is a Node.js CLI tool that spawns an internal Next.js server for the dashboard.

**Ref:** `p25-9router-runtime-node-analysis.md`

---

### Q4: Where are config/state/dashboard/history/log files?

**Answer:** All in the data directory.

| Item | Location |
|------|----------|
| Data dir (Windows) | `%APPDATA%\9router\` |
| Data dir (Linux) | `~/.9router/` or `/var/lib/9router/` |
| Config + State | SQLite `db/data.sqlite` (not yaml/json) |
| Dashboard | Built-in Next.js app at `/dashboard` |
| History | `usageHistory` and `usageDaily` tables in SQLite |
| Logs (text) | `log.txt` |
| Logs (structured) | `requestDetails` table in SQLite |

**Ref:** `p25-local-config-state-inventory.md`

---

### Q5: What files must migrate to VPS?

**Answer:** Minimal migration set.

| Priority | File | Size | Notes |
|----------|------|------|-------|
| ESSENTIAL | `db/data.sqlite` | ~1.5 GB | All config, providers, keys, history |
| ESSENTIAL | `jwt-secret` | 64 B | Dashboard auth token signing |
| ESSENTIAL | `machine-id` | 64 B | 9Router instance identity |
| RECOMMENDED | `db/backups/` | ~500 MB | Historical backups |
| RECOMMENDED | `auth/` | ~1 MB | OAuth tokens |

**Total:** ~1.5 GB essential, ~2 GB with recommended.

**Ref:** `p25-local-config-state-inventory.md`

---

### Q6: What must NOT be migrated?

**Answer:** Ephemeral and lock files only.

| File | Reason |
|------|--------|
| `db/data.sqlite-wal` | WAL journal — rebuilt on startup |
| `db/data.sqlite-shm` | Shared memory — rebuilt on startup |
| `db/data.sqlite.bak-*` | Old backups (unless specifically wanted) |
| `db.json` | Legacy format — 9router migrates automatically |
| `usage.json` | Legacy format |
| `request-details.json` | Legacy format |
| `log.txt` | Per-instance log — fresh on VPS |
| `runtime/` | Temporary runtime state |
| `bin/` | Platform-specific binaries |
| `update/` | Update staging area |
| `.migrated-from-json` | Migration marker — recreated if needed |

**Ref:** `p25-local-config-state-inventory.md`

---

### Q7: What secrets exist? (Keys/paths only, never values)

**Answer:** 7 secret locations identified.

| Location | Key Path | Type |
|----------|----------|------|
| `db/data.sqlite` | `providerConnections.data.apiKey` | Provider API keys (Codex, DeepSeek) |
| `db/data.sqlite` | `providerConnections.data.accessToken` | OAuth tokens |
| `db/data.sqlite` | `apiKeys.key` | 9Router local API keys |
| `db/data.sqlite` | `settings.password_hash` | Dashboard password hash |
| File | `jwt-secret` | 64-byte JWT signing secret |
| File | `machine-id` | 64-byte machine identifier |
| Directory | `auth/` | OAuth token files |

**Security note:** All secrets are stored in plaintext SQLite or flat files. The VPS must enforce restrictive file permissions (mode 600, owned by dedicated user).

**Ref:** `p25-local-config-state-inventory.md`, `p25-migration-rollback-risk.md`

---

### Q8: What port does local 9Router use?

**Answer:** `20128` (9Router default).

**Ref:** `p25-local-9router-inventory.md`

---

### Q9: What port should VPS 9Router use?

**Answer:** `20128` (same port, different machine — no conflict).

**Ref:** `p25-tailscale-endpoint-design.md`

---

### Q10: Is 2c/4GB likely enough for 1000 req/min?

**Answer:** CONDITIONAL PASS.

| Resource | Verdict | Detail |
|----------|---------|--------|
| CPU | PASS | 9Router is I/O-bound. <10% utilization expected at 1000 req/min. 2 vCPU is more than sufficient. |
| Memory | CONDITIONAL | Sufficient if avg duration <= 30s (L <= 500 concurrent). Tight at 60s avg (L = 1000). |
| Disk | PASS | 1.5 GB data fits in 25-50 GB VPS disk easily. |

**Binding constraint:** Memory. See Q11 for Little's Law analysis.

**Ref:** `p25-vps-sizing-2c4gb-capacity-analysis.md`

---

### Q11: What concurrency does 1000 req/min imply?

**Answer:** Little's Law (L = lambda x W).

Lambda (arrival rate) = 1000/60 = 16.7 req/sec.

| Avg Duration (W) | Concurrent (L) | Memory Pressure | Verdict |
|-------------------|-----------------|-----------------|---------|
| 10s | 167 | Low | PASS |
| 30s | 500 | Moderate | PASS |
| 60s | 1000 | High | TIGHT |

**Coding workload expectation:** Most coding requests complete in 10-30s. Duration >60s indicates streaming or very large context — likely a minority of traffic.

**Ref:** `p25-1000rpm-load-model.md`

---

### Q12: What OS limits matter?

**Answer:** 6 system limits identified. None expected to be bottlenecks at 1000 req/min.

| Limit | Recommended | Notes |
|-------|-------------|-------|
| File descriptors | 16384 | Default 1024 is too low for 500+ concurrent |
| Socket backlog | `somaxconn=4096` | Kernel default 128 is too low |
| systemd `LimitNOFILE` | 16384 | Match fd limit |
| systemd `MemoryHigh` | 3 GB | Soft memory limit |
| Node.js heap | `--max-old-space-size=2048` | Prevent OOM from V8 heap growth |
| SQLite WAL | Default | Adequate for this workload |

**Ref:** `p25-systemd-service-design.md`, `p25-vps-sizing-2c4gb-capacity-analysis.md`

---

### Q13: What load test is needed before claiming ready?

**Answer:** 5-minute sustained load at 1000 req/min with realistic payloads.

**Test specification:**
- **Duration:** 5 minutes sustained
- **Rate:** 1000 req/min (16.7 req/sec) constant
- **Payload:** Realistic chat completion requests (varying sizes)
- **Pass criteria:**
  - p99 latency < 5s overhead (9Router adds to upstream time)
  - Memory peak < 3 GB (out of 4 GB)
  - CPU utilization < 50% (of 2 vCPU)
  - Zero 5xx errors
  - Event loop lag < 50ms
- **Tool:** k6 or wrk2

**Ref:** `p25-vps-sizing-2c4gb-capacity-analysis.md`

---

### Q14: What metrics prove no 9Router throttling or bottleneck?

**Answer:** 7 metrics to monitor.

| Metric | Threshold | Why |
|--------|-----------|-----|
| 9Router overhead latency | < 100ms (p99) | Proves proxy is not adding delay |
| Memory usage | < 3 GB | 1 GB headroom for spikes |
| CPU utilization | < 50% | Indicates I/O-bound, not CPU-bound |
| 5xx error count | 0 | Any server error is a failure |
| Event loop lag | < 50ms | Proves Node.js is not blocking |
| SQLite write latency | < 10ms | Proves database is not a bottleneck |
| File descriptor usage | < 50% of limit | Proves no fd exhaustion risk |

**Ref:** `p25-vps-sizing-2c4gb-capacity-analysis.md`, `p25-1000rpm-load-model.md`

---

### Q15: What are upgrade/downgrade options if 2c/4GB is insufficient?

**Answer:**

| Option | Specs | Est. Cost | Concurrency Capacity |
|--------|-------|-----------|---------------------|
| Current target | 2c/4GB | ~$12-24/mo | 500 concurrent (30s avg) |
| Upgrade | 4c/8GB | ~$24-48/mo | 2000+ concurrent |
| Downgrade | 1c/2GB | ~$6-12/mo | Not recommended for 1000 rpm |

**Before upgrading, optimize:**
1. Reduce Node.js heap to 1.5 GB
2. Prune `usageHistory` to 7-day retention
3. Disable `requestDetails` logging (if not needed)
4. Increase `MemoryHigh` to use swap as buffer

**Ref:** `p25-vps-sizing-2c4gb-capacity-analysis.md`, `p25-migration-rollback-risk.md`

---

### Q16: How to keep it isolated from Hermes/P20?

**Answer:** Complete separation at every layer.

| Layer | 9Router VPS | Hermes/Guinevere VPS |
|-------|-------------|---------------------|
| Machine | Dedicated VPS | Separate VPS |
| Tailscale IP | Different IP | Different IP |
| Linux user | `nine-router` | `guinevere` |
| systemd slice | `nine-router.slice` | `guinevere.slice` |
| Data directory | `/var/lib/9router/` | `/home/guinevere/.9router/` (or similar) |
| Systemd service | `nine-router.service` | `guinevere-*.service` |
| Shared resources | **None** | **None** |

No shared filesystem, no shared process space, no shared network namespace. Failure of the 9Router VPS has zero impact on Hermes/P20.

**Ref:** `p25-systemd-service-design.md`, `p25-tailscale-endpoint-design.md`

---

### Q17: How to rollback safely to local 9Router?

**Answer:** Instant rollback, zero data loss.

**Procedure:**
1. Change `OPENAI_BASE_URL` in Claude Code / OpenCode config from `http://<tailscale-ip>:20128/v1` back to `http://localhost:20128/v1`
2. Done.

**Characteristics:**
- Time to rollback: < 1 second
- Data loss: None (local 9Router remains running throughout)
- Downtime: Effectively zero (only the client switch moment)
- Risk: None (local instance is never stopped)

**Ref:** `p25-migration-rollback-risk.md`

---

### Q18: What exact implementation waves should P25 use later?

**Answer:** 7 waves, each independently verifiable.

| Wave | Name | Duration | Depends On |
|------|------|----------|------------|
| 1 | VPS Provisioning | ~30 min | — |
| 2 | Data Migration | ~15 min | Wave 1 |
| 3 | Service Setup | ~20 min | Wave 2 |
| 4 | Verification | ~15 min | Wave 3 |
| 5 | Client Switch | ~5 min | Wave 4 |
| 6 | Monitoring | 24 hours | Wave 5 |
| 7 | Cleanup | ~10 min | Wave 6 |

**Ref:** Section 5 below, `p25-systemd-service-design.md`, `p25-claudecode-opencode-endpoint-wiring.md`

---

## 4. Key Findings

### Finding 1: 9Router is I/O-bound, not CPU-bound

9Router is a thin Node.js proxy. CPU usage at 1000 req/min will be negligible (<10% of 2 vCPU). The binding resource is memory, driven by concurrent request count, which is a function of arrival rate and average request duration.

### Finding 2: Memory is the binding constraint

Little's Law analysis shows concurrency ranges from 167 (10s avg) to 1000 (60s avg). At 500 concurrent requests with typical Node.js memory overhead, 4 GB is sufficient. At 1000 concurrent, 4 GB is tight. The 2 GB Node.js heap cap (`--max-old-space-size=2048`) is critical to prevent OOM.

### Finding 3: Rollback is trivially safe

Local 9Router remains running throughout. The "migration" is really a "setup new, then switch clients." Rollback is changing one environment variable. There is no destructive step in the entire process.

### Finding 4: Complete isolation from Hermes/P20

Different VPS, different IP, different user, different service, different data directory. Zero shared resources. This is architecturally clean with no entanglement risk.

### Finding 5: SQLite migration is straightforward but requires care

The 1.5 GB `data.sqlite` file must be copied cleanly (no WAL/shm), CRLF must be fixed on Linux, and file permissions must be set. The `jwt-secret` and `machine-id` files (64 bytes each) are essential — losing them means re-authenticating the dashboard.

---

## 5. Implementation Waves

### Wave 1: VPS Provisioning (~30 min)
- Create VPS (2c/4GB, Ubuntu 24.04)
- Install Tailscale, authenticate
- Install Node.js 20 LTS
- Install 9Router via npm
- Verify `9router --version`

### Wave 2: Data Migration (~15 min)
- Stop local 9Router (or copy with it running — SQLite WAL mode)
- `scp` `data.sqlite`, `jwt-secret`, `machine-id` to VPS
- Fix CRLF line endings (if needed)
- Set file permissions (600, owned by `nine-router`)
- Verify SQLite integrity (`PRAGMA integrity_check`)

### Wave 3: Service Setup (~20 min)
- Create `nine-router` system user
- Create systemd slice with memory/CPU limits
- Create systemd service unit
- Configure environment file
- Set file descriptor limits
- Enable and start service
- Configure UFW (allow Tailscale subnet only)

### Wave 4: Verification (~15 min)
- Health check via `curl http://<tailscale-ip>:20128/health`
- Model listing via `curl http://<tailscale-ip>:20128/v1/models`
- Chat completion test via `curl` with a simple prompt
- Dashboard access verification

### Wave 5: Client Switch (~5 min)
- Update `OPENAI_BASE_URL` in Claude Code config to `http://<tailscale-ip>:20128/v1`
- Update `OPENAI_BASE_URL` in OpenCode config
- Run a test completion from each client
- Verify responses are correct

### Wave 6: Monitoring (24 hours)
- Monitor memory, CPU, error rates
- Run load test (5-minute sustained at 1000 rpm)
- Verify all 7 metrics from Q14 are within thresholds
- Confirm no event loop lag, no 5xx errors

### Wave 7: Cleanup (~10 min)
- Archive old local 9Router backups
- Document the new setup in project docs
- Update memory files with VPS details

---

## 6. Hard Constraints

The following MUST NOT happen:

1. **DO NOT touch Hermes/P20 production services.** The 9Router VPS is a completely separate system.
2. **DO NOT delete local 9Router data.** The local `data.sqlite` must remain as rollback fallback.
3. **DO NOT expose 9Router to the public internet.** Tailscale-only access. UFW must block all non-Tailscale traffic on port 20128.
4. **DO NOT implement without operator approval.** P25 is research-only. Implementation requires explicit go-ahead.
5. **DO NOT skip the load test.** The 2c/4GB verdict is conditional. The load test is the proof.
6. **DO NOT use default Node.js heap size.** The 6 GB default will OOM a 4 GB VPS. `--max-old-space-size=2048` is mandatory.
7. **DO NOT copy WAL/SHM files during migration.** Only copy `data.sqlite` itself. The journal files are ephemeral.

---

## 7. Research Output Files

| # | File | Content |
|---|------|---------|
| 1 | `p25-local-9router-inventory.md` | Local installation paths, npm package details, provider combos, model listings |
| 2 | `p25-local-config-state-inventory.md` | File inventory, migration classification (essential/skip/recommended), secrets inventory |
| 3 | `p25-9router-runtime-node-analysis.md` | Node.js runtime analysis, memory/CPU profiling, systemd design requirements |
| 4 | `p25-vps-sizing-2c4gb-capacity-analysis.md` | Capacity math, CPU/memory/disk analysis, CONDITIONAL PASS verdict |
| 5 | `p25-1000rpm-load-model.md` | Little's Law model, concurrency tables, load test specification |
| 6 | `p25-tailscale-endpoint-design.md` | Tailscale endpoint design, UFW rules, MagicDNS configuration |
| 7 | `p25-systemd-service-design.md` | Complete systemd unit, slice, security hardening, resource limits |
| 8 | `p25-migration-rollback-risk.md` | 10 identified risks, rollback procedure, step-by-step migration |
| 9 | `p25-claudecode-opencode-endpoint-wiring.md` | Client endpoint configuration, verification steps, rollback |
| 10 | **`p25-research-summary.md`** | **This file — synthesis of all findings** |

All files located in: `docs/setup-evidence/P25/evidence/`

---

## 8. Next Steps

After operator approval:

1. **Approve or reject the 2c/4GB sizing.** If unsure, default to 4c/8GB — the cost difference is small.
2. **Provide VPS provider preference** (Hetzner, DigitalOcean, Vultr, etc.) or let the agent choose.
3. **Confirm Tailscale authentication** is available for the new VPS.
4. **Implementation begins** with Wave 1 through Wave 7, each wave independently verifiable.
5. **Load test (Wave 6)** is the go/no-go gate for production use.

If the operator wants to proceed, implementation can begin immediately on Wave 1 (VPS Provisioning). The entire migration is estimated at ~2 hours of wall-clock time, plus 24 hours of monitoring soak.

---

## 9. Footer

```
P25 RESEARCH PHASE — COMPLETE
Status: 2C4GB CONDITIONAL, LOAD TEST REQUIRED
18/18 questions answered
10 research files produced
Risk: LOW (instant rollback, zero production impact)
Next: Operator approval for implementation
```

---

*Generated: 2026-06-25 | Phase: P25 | Research only — no implementation, no deployment, no production changes.*
