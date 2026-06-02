# P0-028 Pre-Flight Verification — Implementation Auditor Report

**Auditor**: Independent implementation auditor (balance)
**Date**: 2026-05-31
**Scope**: `scripts/preflight-check.sh` (463 lines)
**Method**: Line-by-line audit against 17-item DoD checklist + shell correctness review

---

## Verdict: NEEDS REVIEW

---

## DoD Checklist Audit

| # | DoD Item | Result | Evidence |
|---|---|---|---|
| 1 | PostgreSQL pg_isready :5433 | ✅ PASS | Line 158-159: `pg_isready -h 127.0.0.1 -p 5433 -q` |
| 2 | PgBouncer port 5434 SHOW VERSION | ✅ PASS | Line 161-162: `psql -h 127.0.0.1 -p 5434 -U guinevere -d pgbouncer -c "SHOW VERSION;"` |
| 3 | Redis :6380 PING | ✅ PASS | Line 173-174: `redis-cli -h 127.0.0.1 -p 6380 PING` |
| 4 | fail2ban sshd jail | ✅ PASS | Line 203-204: `fail2ban-client status sshd` with "Jail list" check |
| 5 | CrowdSec LAPI status | ✅ PASS | Line 206-207: `cscli lapi status` |
| 6 | Caddy 8443 + 3443 + 9443 | ✅ PASS | Lines 182-189: three independent `ss -tlnp` checks, one per port |
| 7 | UFW status | ✅ PASS | Lines 197-201: `ufw status` for "Status: active" + "22/tcp" |
| 8 | Tailscale IP 100.94.104.22 | ✅ PASS | Line 270-271: `tailscale ip -4` verified against literal "100.94.104.22" |
| 9 | Cloudflare Tunnel (cloudflared) | ✅ PASS | Line 274-275: `ps aux` + systemctl at line 148 |
| 10 | SOPS decrypt test | ✅ PASS | Lines 303-312: two-path fallback, actual decrypt with `SOPS_AGE_KEY_FILE` — not a stub |
| 11 | Disk space >= 40GB | ✅ PASS | Lines 337-345: `df -BG /` extracting available GB |
| 12 | Aizanta >= 5 containers, healthy | ✅ PASS | Lines 379-397: `--filter name=aizanta`, count + health filter |
| 13 | **Port isolation: 5432 & 6379 not bound** | 🔴 NEEDS REVIEW | Lines 239-255 — see Finding F1 below |
| 14 | Backup timer in systemctl list-timers | ✅ PASS | Lines 420-431: `grep -c "guinevere-backup"` with `|| true` guard |
| 15 | Aggregate PASS/FAIL/WARN counters | ✅ PASS | Line 33 initialised; all helpers increment; summary at lines 449-453 |
| 16 | Exit 0 = all PASS, exit 1 = any FAIL | ✅ PASS | Line 463: `exit "$OVERALL_EXIT"`, set to 1 on any FAIL |
| 17 | Individual systemctl is-active per service | ✅ PASS | Lines 142-149: nine separate `check_systemctl` calls |

**DoD pass rate**: 16/17 PASS, 1 NEEDS REVIEW

---

## Findings

### F1: Port Isolation False Positive (CRITICAL)

**Location**: Lines 215, 239-255
**Severity**: HIGH

**Problem**: The port isolation check collects ALL listening TCP ports via `ss -tlnp -n` (line 215), then checks whether ports 5432 and 6379 appear in that list (lines 239, 248). Since Aizanta Docker containers are expected to be running (Section 9 verifies >= 5 containers), Aizanta's own PostgreSQL (5432) and Redis (6379) WILL appear in the system's listening ports. The check will FAIL unconditionally whenever Aizanta is healthy.

**Root cause**: The `ALL_PORTS` variable captures every TCP listener on the system — not only Guinevere-owned services. The intent is to verify Guinevere doesn't bind 5432/6379, but the check cannot distinguish between Aizanta-owned and Guinevere-owned listeners.

**Impact**: False alarm on every run where Aizanta is up. Operator will see `[FAIL] Port conflict: 5432` even though no conflict exists.

**Recommended fix**: Filter `ss -tlnp -n` output to exclude Aizanta/Docker-owned processes, or use `ss -tlnp -n '( sport = :5432 or sport = :6379 )'` and inspect the process name column to check whether the owning process is a Guinevere service. Alternatively, document this as an informational check with WARN severity and explicit context in the output.

### F2: Cloudflared Check Redundancy (OBSERVATION)

**Location**: Line 274-275
**Severity**: LOW

`cloudflared.service` is already checked via `systemctl is-active` at line 148. The `ps aux | grep cloudflared` at line 274-275 adds a second, redundant process-level check. Not wrong — both can pass or fail independently — but the `ps aux` approach is fragile (binary name may differ; output truncation on long command lines). `pgrep cloudflared` would be more robust if the redundant check is kept.

### F3: Memory Check — Free Column Dependence (OBSERVATION)

**Location**: Line 348
**Severity**: LOW

`free -m | awk '/^Mem:/{print $7}'` relies on column 7 being the "available" column. This is correct on Ubuntu 20.04+ (procps-ng 3.3.16+), but on older `free` versions column 7 may not exist. Since the target VPS is Ubuntu with modern systemd, this is unlikely to cause issues in practice. Acceptable risk.

### F4: `require_bin` WARN Without Counter (OBSERVATION)

**Location**: Lines 113-115
**Severity**: COSMETIC

`require_bin` calls `log_warn` but does not increment `WARN`. This is intentional (commented as "informational only" at line 118), but means the WARN counter only reflects service/functional warnings, not missing binary warnings. The operator won't see missing dependencies reflected in the summary counts. Consider incrementing WARN or adding a separate informational counter.

---

## Shell Correctness Review

| Check | Result |
|---|---|
| `set -euo pipefail` present | ✅ Line 20 |
| Undefined variable guard (`-u`) | ✅ Active |
| Pipefail enabled | ✅ Active |
| `check_cmd_output` has `|| true` guard | ✅ Line 75 — prevents script exit on grep mismatch |
| Backup timer grep has `|| true` guard | ✅ Line 420 |
| SOPS decrypt uses subshells for env isolation | ✅ Lines 305-306, 308 — `bash -c '...'` with scoped env |
| No unquoted variable expansion | ✅ All expansions are quoted or in safe contexts |
| No `rm -rf`, no destructive operations | ✅ Entirely read-only |
| Integer arithmetic uses `((...))` | ✅ |
| String-to-integer comparisons use `[ "$x" -ge N ]` | ✅ Lines 338, 349, 380, 391 |
| Path checks use `[ -f ... ]` before access | ✅ Lines 303, 306, 315, 434 |

**Shell correctness**: No issues found.

---

## Missing Checks (Out of Scope for DoD but Noteworthy)

The following are NOT in the current DoD but may be relevant for production readiness:

- No HTTPS/TLS certificate validity check (Caddy cert expiry)
- No PostgreSQL connection pool check (idle connections, max_connections)
- No Redis memory usage or eviction policy check
- No Prometheus/Grafana endpoint health check
- No systemd-journald log flow check (for Loki ingestion)
- No check that `guinevere-backup.service` (not just timer) exists

None of these are required by the DoD — they are forward-looking suggestions for P1 or future preflight iterations.

---

## Recommendations

| # | Recommendation | Priority |
|---|---|---|
| R1 | Fix port isolation false positive (F1) before deploying to VPS | HIGH |
| R2 | Replace `ps aux | grep cloudflared` with `pgrep cloudflared` or remove redundant check | LOW |
| R3 | Consider incrementing WARN in `require_bin` or adding informational-only counter | LOW |

---

## Summary

**17-item DoD**: 16 PASS, 1 NEEDS REVIEW (port isolation false positive — F1).

The script is well-structured, uses correct ports throughout (5433 not 5432, 6380 not 6379, all three Caddy ports), has `set -euo pipefail`, proper error handling with `|| true` guards in grep-based checks, functional SOPS decrypt (not a stub), correct resource thresholds (40GB disk, 512M mem), individual service checks, proper Aizanta container filtering, and correct aggregate counters. The only blocking issue is **F1**: the port isolation check for 5432/6379 will produce false failures whenever Aizanta containers are running, because it scans all system listening ports without filtering to Guinevere-owned processes.

**Recommended action**: Fix F1, re-verify, then mark step complete. All other findings are cosmetic or informational.