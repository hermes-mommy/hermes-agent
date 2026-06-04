# D10: Operational Safety Audit -- Surveillance Subsystem

| Field | Value |
|---|---|
| Audit ID | D10 |
| Phase | P7 (Surveillance) |
| Scope | systemd service, Redis TTL, RetentionTier, resource budget, graceful shutdown, restart policy |
| Date | 2026-06-03 |
| Auditor | Guinevere (automated) |
| Overall Verdict | **NEEDS REVIEW** |

---

## 1. systemd Service Analysis

### 1.1 Unit Configuration

| Directive | Value | Assessment |
|---|---|---|
| Description | Guinevere Surveillance Consumer | PASS |
| After | guinevere-core.service docker.service network.target | PASS |
| Requires | guinevere-core.service | PASS |
| Type | exec | PASS |
| User | guinevere | PASS |
| Group | guinevere | PASS (explicit; other services omit Group) |
| Slice | guinevere.slice | PASS |

**Notes:**

- `docker.service` appears in `After=` but not in `Requires=`. This is a soft ordering dependency, meaning the service will start after Docker if Docker is running, but will not fail if Docker is absent. This is acceptable for a consumer that connects to Redis/PostgreSQL directly.
- `Group=guinevere` is explicitly set, which is more restrictive than the other services (loops, mcp, scheduler) that only set `User=guinevere`. Good practice.

### 1.2 Resource Limits

| Directive | Value | Assessment |
|---|---|---|
| MemoryHigh | 512M | PASS -- throttling starts at 512M |
| MemoryMax | 768M | PASS -- hard ceiling at 768M |
| CPUQuota | 100% | PASS -- limited to 1 CPU core equivalent |

**Comparison with other services:**

| Service | MemoryHigh | MemoryMax | CPUQuota |
|---|---|---|---|
| guinevere-loops | 1G | 2G | 200% |
| guinevere-mcp | 1G | 2G | 200% |
| guinevere-scheduler | 1G | 2G | 200% |
| guinevere-obscura | 256M | 512M | 100% |
| **guinevere-surveillance** | **512M** | **768M** | **100%** |

Surveillance is correctly sized smaller than the primary daemons and slightly larger than the lightweight obscura CDP server. Resource limits are appropriate for a polling consumer with 5-second intervals and batch size of 10.

### 1.3 Security Hardening

| Directive | Value | Assessment |
|---|---|---|
| NoNewPrivileges | true | PASS -- prevents privilege escalation |
| ProtectSystem | strict | PASS -- filesystem is read-only except ReadWritePaths |
| ProtectHome | read-only | PASS -- home directories read-only except explicit writes |
| ReadWritePaths | /home/guinevere/code/guinevere, /home/guinevere/data, /home/guinevere/logs, /home/guinevere/evidence | PASS -- minimal write surface |

ReadWritePaths is consistent with guinevere-loops, guinevere-mcp, and guinevere-scheduler. The surveillance service does not request any additional write paths beyond the standard set.

### 1.4 Environment and Credentials

| Directive | Assessment |
|---|---|
| REDIS_PASSWORD=%E/REDIS_PASSWORD | PASS -- systemd credential specifier, not plaintext |
| GUINEVERE_DB_PASSWORD=%E/GUINEVERE_DB_PASSWORD | PASS -- systemd credential specifier, not plaintext |
| DATABASE_URL with embedded %E/ | PASS -- credential specifier in connection string |
| PYTHONDONTWRITEBYTECODE=1 | PASS -- prevents .pyc file writes |

No plaintext secrets in the unit file. Credential specifiers (`%E/`) resolve from systemd's encrypted credential store at runtime.

### 1.5 Restart Policy

| Directive | Value | Assessment |
|---|---|---|
| Restart | always | NEEDS REVIEW |
| RestartSec | 10 | PASS -- 10s cooldown between restarts |
| StartLimitIntervalSec | not set | NEEDS REVIEW |
| StartLimitBurst | not set | NEEDS REVIEW |

**Finding:** `Restart=always` will restart the service on any exit (clean or crash) indefinitely. No explicit `StartLimitIntervalSec` or `StartLimitBurst` is configured. The systemd default rate limit (typically 5 starts within 10 seconds) provides minimal protection because `RestartSec=10` ensures only one restart per 10 seconds, which never triggers the rate limiter. A continuously crashing service will restart forever at 10-second intervals.

**Comparison:** guinevere-loops, guinevere-mcp, and guinevere-scheduler all use `Restart=always` with `RestartSec=10` (same pattern). guinevere-obscura uses `Restart=on-failure` with `RestartSec=5`.

**Recommendation:** Add explicit crash-loop protection:

```ini
StartLimitIntervalSec=300
StartLimitBurst=5
```

This would limit the service to 5 restarts within a 5-minute window before systemd stops attempting restarts. Alternatively, consider `Restart=on-failure` to avoid restarting on clean exits (e.g., deliberate maintenance stops).

---

## 2. Redis TTL Verification

All three surveillance Redis keys use TTL-based expiry. No persistent (TTL-less) keys were found.

| Key | Source File | TTL Value | Mechanism | Assessment |
|---|---|---|---|---|
| `surveillance:buffer` | `redis_buffer.py` (line 76) | 300s (5 min) | `expire()` called on every `rpush` (line 95) | PASS |
| Nonce key (dynamic) | `replay.py` (line 36) | 660s (11 min) | `set(nonce_key, "1", nx=True, ex=NONCE_TTL_SECONDS)` (line 130) | PASS |
| Consent cache key (dynamic) | `consent_gate.py` (line 46) | 300s (5 min) | `set(cache_key, ..., ex=CACHE_TTL_SECONDS)` (line 367) | PASS |

**Design correctness:**

- `surveillance:buffer` TTL is refreshed on every push via `expire()`. If no events arrive within 300 seconds, the entire buffer key is auto-deleted. This prevents orphaned buffer keys from accumulating.
- Nonce TTL (660s) is correctly set to >= 2x the timestamp window (300s), ensuring nonces outlive the replay window they protect.
- Consent cache TTL (300s) means consent revocations take effect within 5 minutes even without explicit cache invalidation. This is an acceptable lag for a polling consumer.

**Verdict: PASS** -- All keys have TTL. No persistent keys. TTL values are spec-compliant.

---

## 3. RetentionTier Policy Alignment

Source: `src/surveillance/retention.py`

| Tier | Constant | Value | Policy Requirement | Assessment |
|---|---|---|---|---|
| Raw | `RETENTION_RAW_DAYS` | 7 | 7 days | PASS |
| Aggregated | `RETENTION_AGGREGATED_DAYS` | 90 | 90 days | PASS |
| Summary | `RETENTION_SUMMARY_DAYS` | 365 | 365 days | PASS |

**Additional retention configuration:**

| Constant | Value | Purpose |
|---|---|---|
| `COMPRESSION_AFTER_DAYS` | 7 | TimescaleDB compression kicks in after 7 days |
| `CHUNK_INTERVAL_DAYS` | 1 | Hypertable chunk interval |

**Design safety:**

- `RetentionTier` is a `StrEnum`, preventing free-text tier values.
- `_TIER_DAYS` mapping is `Final[dict]`, immutable at runtime.
- `get_retention_days()` defaults to `RETENTION_RAW_DAYS` (7 days, shortest retention) for unknown tiers. This is a fail-safe: unknown tiers expire quickly rather than persisting indefinitely.
- `calculate_retention_until()` preserves timezone information via `timedelta` addition.

**Verdict: PASS** -- All three tiers match policy exactly. Fail-safe defaults to shortest retention.

---

## 4. Resource Budget Calculation

### 4.1 Service Memory Budget (MemoryMax)

| Service | MemoryMax |
|---|---|
| guinevere-loops | 2048M (2G) |
| guinevere-mcp | 2048M (2G) |
| guinevere-scheduler | 2048M (2G) |
| guinevere-obscura | 512M |
| **guinevere-surveillance** | **768M** |
| **Total** | **7424M (7.25GB)** |

### 4.2 Slice Budget

| Metric | Value |
|---|---|
| guinevere.slice limit (referenced) | 8192M (8GB) |
| Existing services (without surveillance) | 6656M (6.5GB) |
| Surveillance MemoryMax | 768M |
| Total with surveillance | 7424M (7.25GB) |
| Remaining headroom | 768M |
| Utilization | 90.6% |

**Note:** The audit scope references "6.75GB existing" which does not match the sum of MemoryMax values from the four pre-existing service files (6.5GB). The discrepancy (256M) may be attributable to guinevere-core.service or other slice members not present in the `systemd/` directory of this repository. Regardless of which baseline is used, the surveillance service fits within the 8GB slice limit:

- Using service-file baseline: 7.25GB of 8GB (90.6%) -- fits with 768M headroom.
- Using audit-scope baseline (6.75GB existing): 7.5GB of 8GB (93.8%) -- fits with 512M headroom.

**Verdict: PASS** -- Surveillance fits within the slice budget under either calculation. Headroom is adequate but not generous; future services should be sized carefully.

---

## 5. Graceful Shutdown Verification

Source: `src/surveillance/consumer.py`, function `main()` (line ~290)

### 5.1 Signal Handler Registration

```python
for sig in (signal.SIGTERM, signal.SIGINT):
    try:
        loop.add_signal_handler(sig, _on_signal)
    except NotImplementedError:
        logger.warning("consumer_signal_handler_not_supported", os_name=os.name)
```

- Both SIGTERM and SIGINT are handled.
- Windows fallback: `NotImplementedError` is caught (Windows does not support `add_signal_handler`), logged as a warning, and does not crash.

### 5.2 Shutdown Sequence

1. Signal received -> `_on_signal()` called
2. `_on_signal()` calls `consumer.stop()`
3. `stop()` sets `self._running = False`
4. Current `_drain_and_process()` batch completes (no mid-batch interruption)
5. Loop exits after current `asyncio.sleep()` completes
6. `await self._buffer.close()` is called, closing the Redis connection gracefully
7. `logger.info("consumer_stopped")` confirms clean exit

### 5.3 Shutdown Correctness

| Property | Status |
|---|---|
| SIGTERM handled | PASS |
| SIGINT handled | PASS |
| Current batch completes before exit | PASS |
| Redis connection closed on shutdown | PASS |
| No data loss on shutdown (buffer contents preserved in Redis with TTL) | PASS |
| Windows compatibility (graceful degradation) | PASS |

**Verdict: PASS** -- Graceful shutdown is correctly implemented with batch-completion semantics and clean resource teardown.

---

## 6. Summary of Findings

| # | Area | Verdict | Details |
|---|---|---|---|
| 1 | systemd unit config | PASS | Correct dependencies, user/group, slice assignment |
| 2 | Resource limits | PASS | MemoryHigh=512M, MemoryMax=768M, CPUQuota=100% -- appropriately sized |
| 3 | Security hardening | PASS | NoNewPrivileges, ProtectSystem=strict, ProtectHome=read-only, minimal ReadWritePaths |
| 4 | Credential handling | PASS | systemd credential specifiers, no plaintext secrets |
| 5 | Restart policy | NEEDS REVIEW | Restart=always with no StartLimitIntervalSec/StartLimitBurst -- infinite crash-loop possible |
| 6 | Redis TTL (buffer) | PASS | 300s TTL, refreshed on every push |
| 7 | Redis TTL (nonce) | PASS | 660s TTL, >= 2x timestamp window |
| 8 | Redis TTL (consent cache) | PASS | 300s TTL, fail-safe for consent revocation |
| 9 | RetentionTier (raw) | PASS | 7 days matches policy |
| 10 | RetentionTier (aggregated) | PASS | 90 days matches policy |
| 11 | RetentionTier (summary) | PASS | 365 days matches policy |
| 12 | Resource budget | PASS | 7.25GB of 8GB slice (90.6%), 768M headroom |
| 13 | Graceful shutdown | PASS | SIGTERM/SIGINT handled, batch completion, Redis close |

---

## 7. Overall Verdict

### NEEDS REVIEW

The surveillance subsystem is operationally safe across 12 of 13 audit criteria. One finding requires attention:

**Restart policy lacks explicit crash-loop protection (Finding #5).** The service uses `Restart=always` with `RestartSec=10` but does not set `StartLimitIntervalSec` or `StartLimitBurst`. Because `RestartSec=10` prevents the default systemd rate limiter from triggering, a continuously crashing service will restart indefinitely at 10-second intervals. This is consistent with 3 of 4 other services in the slice but represents a gap in operational safety. Recommended fix: add `StartLimitIntervalSec=300` and `StartLimitBurst=5`.

All other criteria (resource limits, security hardening, Redis TTL, RetentionTier policy, resource budget, graceful shutdown) pass without findings.

---

## 8. Recommendations

1. **Add crash-loop rate limiting** to `guinevere-surveillance.service`:
   ```ini
   StartLimitIntervalSec=300
   StartLimitBurst=5
   ```

2. **Consider applying the same rate limiting** to guinevere-loops, guinevere-mcp, and guinevere-scheduler for consistency.

3. **Monitor headroom**: The slice is at 90.6% MemoryMax utilization. Future services added to guinevere.slice should account for the remaining 768M budget.

4. **Document the guinevere.slice definition**: No `.slice` unit file was found in the `systemd/` directory. The 8GB slice limit should be defined in a `guinevere.slice` file and committed to the repository for reproducibility.
