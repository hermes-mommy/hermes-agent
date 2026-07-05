# P25 Source Audit — Official Docs MCP Source Map

**Date:** 2026-06-26
**Purpose:** Map every P25 research claim to its authoritative source, flag corrections, and identify unverified assumptions.
**Method:** Context7 MCP library docs, local source inspection (cli.js, package.json, SQLite), Brave Search corroboration.

---

## 1. Executive Summary

Previous P25 research contained **five materially stale or incorrect claims** that this audit corrects:

1. **Default heap was cited as 6 GB** — actual default is **12288 MB (12 GB)**, verified from `cli.js` line 558.
2. **NODE_OPTIONS was cited as sufficient to control heap** — **FALSE**, because `cli.js` spawns Node with an explicit `--max-old-space-size` flag in the args array, which overrides `NODE_OPTIONS`.
3. **Provider count was cited as 2** — actual count is **92**, verified via `SELECT COUNT(*) FROM providerConnections`.
4. **Combo count was cited as 6** — actual count is **11**, verified via `SELECT COUNT(*) FROM combos`.
5. **"No custom server" was claimed** — **FALSE**, `app/custom-server.js` exists and wraps Next.js with Express for real-IP handling.

All other claims (Tailscale install, systemd patterns, k6 executors, Node.js version, 9Router port/host) are **verified** against official documentation or local source. Four claims remain **unverified** and require runtime load testing rather than source inspection.

---

## 2. Source Inventory

| ID | Source | Type | Access Method | Reliability |
|----|--------|------|---------------|-------------|
| S1 | `/decolua/9router` on Context7 | Official README + install docs | Context7 MCP `query-docs` | HIGH — first-party |
| S2 | `/websites/tailscale` on Context7 | Official docs (tailscale.com) | Context7 MCP `query-docs` | HIGH — first-party |
| S3 | `/systemd/systemd` on Context7 | Official systemd docs | Context7 MCP `query-docs` | HIGH — first-party |
| S4 | `/grafana/k6-docs` on Context7 | Official k6 docs | Context7 MCP `query-docs` | HIGH — first-party |
| S5 | `/websites/nodejs_latest-v24_x_api` on Context7 | Official Node.js docs | Context7 MCP `query-docs` | HIGH — first-party |
| S6 | 9Router `cli.js` (27.3 KB) | Source code, locally cloned | `cat` / direct inspection | HIGH — ground truth |
| S7 | 9Router `app/package.json` | Dependency manifest | `cat` / direct inspection | HIGH — ground truth |
| S8 | 9Router SQLite database | Runtime data | `sqlite3` queries | HIGH — ground truth |
| S9 | 9Router `app/custom-server.js` | Source code | `cat` / direct inspection | HIGH — ground truth |
| S10 | 9Router `hooks/sqliteRuntime.js` | Source code | `cat` / direct inspection | HIGH — ground truth |
| S11 | 9Router `hooks/trayRuntime.js` | Source code | `cat` / direct inspection | HIGH — ground truth |

**No anonymous blog posts, Stack Overflow answers, or LLM-generated guesses were used as primary sources.** Every factual claim traces to a first-party document, source file, or database query.

---

## 3. Claim-by-Claim Audit Table

### 3.1 Verified Claims

| # | Claim | Source | Verification Method | Status |
|---|-------|--------|---------------------|--------|
| 1 | 9Router version is 0.5.4 | S7 — `package.json` | `cat package.json` → `"version": "0.5.4"` | VERIFIED |
| 2 | npm latest is 0.5.8 | npm registry | `npm view 9router version` → `0.5.8` | VERIFIED |
| 3 | Next.js 16.1.6 | S7 — `app/package.json` | `"next": "^16.1.6"` | VERIFIED |
| 4 | React 19.2.4 | S7 — `app/package.json` | `"react": "^19.2.4"` | VERIFIED |
| 5 | Express 5.2.1 | S7 — `app/package.json` | `"express": "^5.2.1"` | VERIFIED |
| 6 | Default heap is 12 GB (12288 MB) | S6 — `cli.js` line 558 | `NINEROUTER_NODE_HEAP_MB \|\| "12288"` | VERIFIED |
| 7 | Explicit `--max-old-space-size` in spawn args | S6 — `cli.js` line 578 | `child_process.spawn` args array contains explicit flag | VERIFIED |
| 8 | 92 providers in database | S8 — SQLite | `SELECT COUNT(*) FROM providerConnections` → 92 | VERIFIED |
| 9 | 11 combos in database | S8 — SQLite | `SELECT COUNT(*) FROM combos` → 11 | VERIFIED |
| 10 | 12 tables in database | S8 — SQLite | `SELECT name FROM sqlite_master WHERE type='table'` → 12 | VERIFIED |
| 11 | Default port 20128 | S6 — `cli.js` line 65 | `const DEFAULT_PORT = 20128` | VERIFIED |
| 12 | Default host 0.0.0.0 | S6 — `cli.js` line 66 | `const DEFAULT_HOST = "0.0.0.0"` | VERIFIED |
| 13 | `NINEROUTER_NODE_HEAP_MB` is undocumented | S1 — official README | Env var list in README does NOT include this variable | VERIFIED (absence confirmed) |
| 14 | Tailscale install: `curl -fsSL https://tailscale.com/install.sh \| sh` | S2 — Tailscale docs | Official Ubuntu install page | VERIFIED |
| 15 | Tailscale get IP: `tailscale ip -4` | S2 — Tailscale docs | Official CLI reference | VERIFIED |
| 16 | Tailscale UFW: remove public SSH, allow Tailscale interface only | S2 — Tailscale docs | Security hardening guide | VERIFIED |
| 17 | systemd `Type=simple` for foreground daemons | S3 — systemd docs | Integration test: `sleep-infinity-simple.service` | VERIFIED |
| 18 | systemd `MemoryHigh`/`MemoryMax` resource control | S3 — systemd docs | `CONTROL_GROUP_INTERFACE.md` | VERIFIED |
| 19 | systemd `Restart=always` | S3 — systemd docs | Service restart behavior spec | VERIFIED |
| 20 | systemd `EnvironmentFile=` loads env vars | S3 — systemd docs | Process environment documentation | VERIFIED |
| 21 | systemd security hardening pattern | S3 — systemd docs | `systemd-networkd.service` example: `ProtectSystem=strict`, `ProtectHome=yes`, `NoNewPrivileges=yes` | VERIFIED |
| 22 | systemd `PrivateTmp=disconnected` | S3 — systemd docs | `systemd-resolved.service` example | VERIFIED |
| 23 | k6 `constant-arrival-rate` executor | S4 — k6 docs | Official executor documentation | VERIFIED |
| 24 | k6 thresholds: `http_req_failed`, `http_req_duration` | S4 — k6 docs | Threshold examples | VERIFIED |
| 25 | k6 `http.post()` with JSON payload | S4 — k6 docs | HTTP module documentation | VERIFIED |
| 26 | k6 `check()` for status assertions | S4 — k6 docs | Checks documentation | VERIFIED |
| 27 | Node.js `--max-old-space-size` sets V8 heap | S5 — Node.js docs | CLI options documentation | VERIFIED |
| 28 | Explicit flags in `spawn` args override `NODE_OPTIONS` | S5 — Node.js docs | `child_process.spawn` behavior spec | VERIFIED |
| 29 | Node.js 24.x (Krypton), released May 2025, EOL April 2028 | S5 — Node.js docs | Release schedule | VERIFIED |

### 3.2 Corrected Claims (Stale / Wrong)

| # | Old Claim | Corrected Claim | Source of Truth | Evidence |
|---|-----------|-----------------|-----------------|----------|
| C1 | "Default heap is 6 GB" | Default heap is **12 GB (12288 MB)** | S6 — `cli.js` line 558 | `NINEROUTER_NODE_HEAP_MB \|\| "12288"` — the literal fallback string is `"12288"` |
| C2 | "NODE_OPTIONS can control heap size" | **Cannot** — explicit `--max-old-space-size` in spawn args takes precedence | S6 — `cli.js` line 578, S5 — Node.js docs | `child_process.spawn('node', ['--max-old-space-size=12288', ...])` overrides any `NODE_OPTIONS` env var |
| C3 | "2 providers" | **92 providers** | S8 — SQLite | `SELECT COUNT(*) FROM providerConnections` returns 92 |
| C4 | "6 combos" | **11 combos** | S8 — SQLite | `SELECT COUNT(*) FROM combos` returns 11 |
| C5 | "No custom server, uses Next.js built-in" | **Custom server exists**: `app/custom-server.js` | S9 — source inspection | File wraps Next.js with Express to extract real client IP from proxied headers |

---

## 4. 9Router Official Docs Coverage

Source: `/decolua/9router` on Context7 (S1)

### 4.1 Documented in Official README

| Variable | Purpose |
|----------|---------|
| `JWT_SECRET` | Token signing key |
| `INITIAL_PASSWORD` | First-run admin password |
| `DATA_DIR` | Persistent data directory |
| `PORT` | HTTP listen port |
| `HOSTNAME` | Bind address |
| `NODE_ENV` | Environment mode (`production` / `development`) |
| `NEXT_PUBLIC_BASE_URL` | Public-facing base URL |
| `API_KEY_SECRET` | API key signing |
| `MACHINE_ID_SALT` | Machine identity salt |
| `ENABLE_REQUEST_LOGS` | Toggle request logging |

### 4.2 Documented in Installation Guides

- VPS deployment uses **PM2** or **systemd** as process manager.
- Install command: `npm install -g 9router`.
- Cloud deployment: `export` env vars, `DATA_DIR=/var/lib/9router`, `NODE_ENV=production`.

### 4.3 NOT Documented (Discovered via Source Inspection Only)

| Variable / Behavior | Location | Notes |
|---------------------|----------|-------|
| `NINEROUTER_NODE_HEAP_MB` | `cli.js` line 558 | Hidden env var, not in README, not in install docs. Default: `"12288"` (12 GB) |
| Explicit `--max-old-space-size` in spawn | `cli.js` line 578 | Means `NODE_OPTIONS` is **not** a viable override path |
| `DEFAULT_PORT = 20128` | `cli.js` line 65 | Hardcoded constant, not configurable via env var (only via CLI flag or `PORT`) |
| `DEFAULT_HOST = "0.0.0.0"` | `cli.js` line 66 | Binds all interfaces by default |
| SQLite auto-healing | `hooks/sqliteRuntime.js` | Runtime hook not mentioned in docs |
| Systray runtime | `hooks/trayRuntime.js` | Desktop mode hook not mentioned in docs |
| Custom HTTP server with real-IP | `app/custom-server.js` | Express wrapper for proxy header extraction |

**Gap:** The most operationally critical tuning parameter (heap size) is undocumented. An operator following only official docs would run with a 12 GB default that may be excessive on a 4 GB VPS or insufficient on a 16 GB machine, with no guidance on how to change it.

---

## 5. Tailscale Official Docs Coverage

Source: `/websites/tailscale` on Context7 (S2)

### 5.1 Verified Claims

| Topic | Coverage |
|-------|----------|
| Ubuntu install | `curl -fsSL https://tailscale.com/install.sh \| sh` then `tailscale up` |
| Ubuntu 24.04 (Noble) | Standard install script works |
| Get IPv4 | `tailscale ip -4` |
| UFW hardening | Remove public SSH (`sudo ufw delete 22/tcp`), allow only Tailscale interface |
| MagicDNS | Available when enabled on tailnet |
| Key expiry | Configurable per device |

### 5.2 Gaps

- **Latency overhead** of Tailscale WireGuard tunnel is not quantified in official docs. Claim of "~1-5 ms" is an estimate based on general WireGuard benchmarks, not Tailscale-specific measurements.
- **Exit node performance** is not benchmarked in official docs.

---

## 6. systemd Official Docs Coverage

Source: `/systemd/systemd` on Context7 (S3)

### 6.1 Verified Directives

| Directive | Purpose | Source |
|-----------|---------|--------|
| `Type=simple` | Foreground daemon (default) | Integration tests |
| `MemoryHigh=` | Soft memory limit (cgroup v2) | `CONTROL_GROUP_INTERFACE.md` |
| `MemoryMax=` | Hard memory limit (cgroup v2) | `CONTROL_GROUP_INTERFACE.md` |
| `Restart=always` | Restart on any exit except `SKIP_CONDITION` | Service restart spec |
| `EnvironmentFile=` | Load env vars into process environment | Process environment docs |
| `ProtectSystem=strict` | Read-only `/` except explicit exceptions | `systemd-networkd.service` |
| `ProtectHome=yes` | Make `/home` inaccessible | `systemd-networkd.service` |
| `NoNewPrivileges=yes` | Prevent privilege escalation | `systemd-networkd.service` |
| `RestrictAddressFamilies=` | Limit socket families | `systemd-networkd.service` |
| `SystemCallFilter=@system-service` | Whitelist syscalls | `systemd-networkd.service` |
| `PrivateTmp=disconnected` | Isolated `/tmp`, no mount propagation | `systemd-resolved.service` |

### 6.2 Notes

- `MemoryMax` requires cgroup v2 (unified hierarchy). Ubuntu 24.04 uses cgroup v2 by default — confirmed.
- `PrivateTmp=disconnected` is stricter than `PrivateTmp=yes` — it also disables mount propagation.

---

## 7. k6 Official Docs Coverage

Source: `/grafana/k6-docs` on Context7 (S4)

### 7.1 Verified Patterns

| Feature | Syntax | Source |
|---------|--------|--------|
| Constant arrival rate | `executor: 'constant-arrival-rate'` with `rate`, `timeUnit`, `duration` | Executor docs |
| Thresholds | `http_req_failed: ['rate<0.01']`, `http_req_duration: ['p(95)<200']` | Threshold docs |
| HTTP POST | `http.post(url, JSON.stringify(payload), { headers: { 'Content-Type': 'application/json' } })` | HTTP module |
| Checks | `check(response, { 'status is 200': (r) => r.status === 200 })` | Checks docs |
| Scenarios | Named scenarios with independent executors | Scenario docs |

### 7.2 Notes

- k6 v0.47+ supports `constant-arrival-rate` natively.
- `preAllocatedVUs` and `maxVUs` control virtual user pool size — critical for rate-based testing.

---

## 8. Node.js Official Docs Coverage

Source: `/websites/nodejs_latest-v24_x_api` on Context7 (S5)

### 8.1 Verified Facts

| Topic | Detail |
|-------|--------|
| `--max-old-space-size` | V8 heap limit in MB, set via CLI flag |
| `child_process.spawn` | Explicit args array flags take precedence over `NODE_OPTIONS` |
| Node.js 24.x codename | Krypton |
| Release date | May 2025 |
| EOL | April 2028 |
| Status | Active LTS |

### 8.2 Critical Precedence Note

When `child_process.spawn('node', ['--max-old-space-size=X', 'script.js'])` is called, the `--max-old-space-size=X` in the args array **overrides** any value set via `NODE_OPTIONS` environment variable. This is confirmed by Node.js documentation on CLI argument precedence. **This means setting `NODE_OPTIONS=--max-old-space-size=4096` has no effect when 9Router's `cli.js` explicitly passes `--max-old-space-size=12288` in the spawn args.**

The only correct way to control heap size is via the `NINEROUTER_NODE_HEAP_MB` environment variable, which `cli.js` reads at line 558 and passes into the spawn args.

---

## 9. Stale Claims Corrected (With Evidence)

### C1: Heap Default — 6 GB vs 12 GB

**Old claim:** "Default heap is 6 GB (6144 MB)"
**Correction:** Default heap is **12 GB (12288 MB)**

**Evidence** — `cli.js` line 558:
```javascript
const heapMb = process.env.NINEROUTER_NODE_HEAP_MB || "12288";
```

The fallback string is `"12288"`, not `"6144"`. The previous claim likely came from an older version or was a guess.

### C2: NODE_OPTIONS Override

**Old claim:** "Set NODE_OPTIONS=--max-old-space-size=4096 to limit heap"
**Correction:** This has **no effect**.

**Evidence** — `cli.js` line 578:
```javascript
const child = spawn(process.execPath, [
  `--max-old-space-size=${heapMb}`,
  serverScript,
  ...
], { ... });
```

The explicit `--max-old-space-size` flag in the `spawn` args array takes precedence over `NODE_OPTIONS`. Node.js CLI precedence rules confirm: explicit flags > `NODE_OPTIONS`.

**Correct approach:** Set `NINEROUTER_NODE_HEAP_MB=4096` in the environment or `EnvironmentFile`.

### C3: Provider Count — 2 vs 92

**Old claim:** "2 providers configured"
**Correction:** **92 providers** in the database.

**Evidence:**
```sql
SELECT COUNT(*) FROM providerConnections;
-- Result: 92
```

The old claim was likely from an early setup snapshot or a miscount.

### C4: Combo Count — 6 vs 11

**Old claim:** "6 combos"
**Correction:** **11 combos** in the database.

**Evidence:**
```sql
SELECT COUNT(*) FROM combos;
-- Result: 11
```

### C5: Custom Server — Absent vs Present

**Old claim:** "No custom server, uses Next.js built-in HTTP"
**Correction:** `app/custom-server.js` exists and provides Express-based HTTP wrapping for real-IP extraction from proxy headers.

**Evidence:** File exists at `app/custom-server.js`, imports Express, creates HTTP server, and passes requests to the Next.js handler. This is architecturally significant because it affects how Tailscale + UFW + reverse proxy interact.

---

## 10. Unverified Claims (Requiring Load Test or Further Research)

These claims **cannot be verified by source inspection alone**. They require runtime benchmarking.

| # | Claim | Why Unverified | What's Needed |
|---|-------|---------------|---------------|
| U1 | "2c/4GB VPS is sufficient for 1000 req/min" | Theoretical math only; no load test data | k6 load test at 1000 req/min sustained for 10+ minutes, measuring p95 latency, error rate, and memory RSS |
| U2 | "Tailscale adds ~1-5 ms latency" | No measurement; based on general WireGuard benchmarks | `ping` over Tailscale vs direct, measured from the actual VPS region |
| U3 | "SQLite handles 1000 req/min writes" | Depends on WAL checkpoint frequency, page size, and write amplification | k6 load test with concurrent writes, monitoring `wal_checkpoint` calls and write lock contention |
| U4 | "9Router memory per concurrent request is ~50-100 MB" | Depends on streaming vs non-streaming, payload sizes, and Monaco editor overhead | Memory profiling under load with `--inspect` and Chrome DevTools heap snapshots |
| U5 | "Heap of 4096 MB is sufficient at 1000 req/min" | No load test data for 9Router specifically | k6 test with `NINEROUTER_NODE_HEAP_MB=4096`, monitoring for OOM or GC pressure |
| U6 | "systemd MemoryMax=3500M prevents OOM kill" | Untested with actual 9Router memory patterns | Deploy unit file, run load test, verify no OOM kill in `dmesg` |

**Recommendation:** All six unverified claims should be resolved by a single k6 load test session before P25 implementation begins. The test script should use `constant-arrival-rate` at 1000 req/min (≈16.7 req/sec) with `NINEROUTER_NODE_HEAP_MB=4096` and `MemoryMax=3500M` in the systemd unit.

---

## 11. Source Reliability Ratings

| Rating | Definition | Sources |
|--------|------------|---------|
| **A — Ground Truth** | Direct source code or database query from the running system | S6, S7, S8, S9, S10, S11 |
| **B — First-Party Docs** | Official documentation from the software vendor, accessed via Context7 MCP | S1, S2, S3, S4, S5 |
| **C — Inferred / Estimated** | Based on general knowledge or math, not measured | U1-U6 (unverified claims) |

**No D-rated (anonymous/untrusted) sources were used.**

### Reliability Summary

- **29 claims verified** against A-rated or B-rated sources.
- **5 stale claims corrected** with A-rated evidence (source code + database).
- **6 claims remain unverified** and are explicitly flagged as C-rated, pending load testing.

---

## 12. Footer

**Generated:** 2026-06-26
**Audit scope:** P25 VPS deployment research — 9Router, Tailscale, systemd, k6, Node.js
**Next step:** Resolve unverified claims (U1-U6) via k6 load test before P25 implementation.
**Supersedes:** Any prior P25 research document with conflicting numbers.
