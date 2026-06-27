# P22 Round-1 Audit — Dimension: consent-hardstop

**Date:** 2026-06-27
**Auditor:** independent auditor (round 1, gate before round 2)
**Repo:** C:/Users/faizz/guinevere
**VPS:** faiz-prod-01 (Tailscale 100.94.104.22, user guinevere), reachable via `ssh guinevere-vps`

## Verdict: **NEEDS_REVIEW**

Two findings — one HIGH (defect-class, must fix before round 2) and one MEDIUM (security posture). None of the documented hard-rejection criteria are violated.

---

## Findings

| # | Severity | Title | Detail | Evidence |
|---|----------|-------|--------|----------|
| F1 | **high** | Initial T3 gate smoke ran WITHOUT HARD STOP enforcement (real safety defect — already fixed, but fix is not load-bearing without a regression test) | The runtime factory initially passed an **async** `redis.asyncio.Redis` client to `HardStopShim`, whose `is_hard_stop_active()` is **sync-only** (`_shims.py:65-99`). Result: HARD STOP silently fell through, T3 fell through to the consent check, and the gate smoke reported a PASS that was at best CONSENT and not HARD STOP. This is exactly the "missing or no-op shim silently disables HARD STOP" failure mode the shim docstring (`_shims.py:1-20`) calls a HARD REJECTION. The current code paths are safe (`HardStopShim` logs an explicit `hard_stop_shim.async_redis_in_sync_path` warning when it detects an un-awaitable client), but no automated test exists to prevent the regression. | `docs/setup-evidence/P22/production-activation/runtime/p22-configured-adapter-smoke.md:33-47` ("Initial run had a bug… silent fallback to in-process handler… real safety bug"); `src/life_integrations/_shims.py:54-99` (sync `self._redis.get` accepts async client with a warning, not a raise) |
| F2 | **medium** | `HardStopShim` sync path does not actively `await` async Redis clients — relies on consumer warning | `_shims.py:82-89` detects an async client via `hasattr(value, "__await__")` and logs a **one-time warning** while still passing `False` for `redis_active`. The shim DOES fall through to in-process `HardStopHandler.is_safe`, which is the correct conservative behavior. However: (a) if both sources are absent or the handler's `is_safe` is also False in steady state, a stale async client could underreport HARD STOP; (b) there is no unit test pinning this behavior; (c) the warning says "pass a sync redis.Redis client" but the shim does not raise — it silently relies on the second source. | `src/life_integrations/_shims.py:80-99`; `grep -rn "hard_stop_shim" tests/life_integrations/` → expected empty (no regression test) |

## What Was Verified

### Code artifacts (local read-only)

**`src/life_integrations/consent.py` — `ConsentGate.check()` order (lines 84-145):**
1. `L1_READ` → return `(True, "L1 read — no consent required")` (skip).
2. `hard_stop_checker.is_hard_stop_active()` → return `(False, "HARD STOP active — action blocked")`. ABSOLUTE: not gated by tier, applies to **all L2+ including L3 and L4**.
3. `L4_FORBIDDEN` → return `(False, "L4_FORBIDDEN — never autonomous")`.
4. `tier >= L2_WRITE` and no checker wired → return `(False, "no consent checker configured — fail-closed")`.
5. `tier >= L2_WRITE` and checker returns False → return `(False, "consent not granted for scope: ...")` (fail-closed).

This is the documented L1-skip → HARD STOP → L4-forbid → L2+ consent fail-closed order. Confirmed verbatim.

**`src/life_integrations/_shims.py` — `HardStopShim` (lines 32-156):**
- `is_hard_stop_active()` reads `life_kernel:hard_stop` via `self._redis.get(REDIS_KEY)` (SYNC, line 77) and combines via OR with `self._handler.is_safe` (in-process `HardStopHandler`), line 121: `return redis_active or handler_active`.
- Non-empty / non-"0" / non-"false" Redis value => HARD STOP active (lines 91-93).
- Async-redis detection warns (lines 82-89) but does NOT raise (deliberate conservative-OR fallback to handler).
- Async variant `is_hard_stop_active_async()` (lines 123-156) properly awaits coroutines for async clients.
- `ConsentGateShim.check_consent()` (lines 177-221) is fail-closed: no checker => `False`, checker raises => `False`, ambiguous result shape => `False`. ABSOLUTE: blocks L2+.

**`src/life_integrations/router.py` — single call site (line 177):**
- `grep -rn "adapter.execute_action\|execute_action" src/` confirms 14 adapter methods + 1 call from router (the rest are P20 `life_kernel.domain_minds.finance_mind.py:479`, which is pre-existing P20 closed code not invoked by P22).
- `grep -rn "ActionRouter(\|router.execute(" src/life_integrations/` confirms `wiring.py:38` (import) and `wiring.py:149` (construction) are the only construction sites; only `router.py:54` (docstring example) and `router.py:177` (live `await adapter.execute_action(...)` inside the gated path) call `.execute`.
- No alternate direct gate bypass path observed.

**T13 gate smoke (`p22-configured-adapter-smoke.md`):**
- T1 `list_dir` (L1_READ) → PASS (count=97). ✓
- T2 `write` no HARD STOP, no consent checker → `ConsentDeniedError: consent not granted for scope: consent.filesystem.filesystem.write`. ✓ (consent fail-closed)
- T3 `write` WITH `life_kernel:hard_stop=1` (post-fix) → `HardStopBlockedError: HARD STOP active — action blocked`. ✓ (HARD STOP blocks L2+)
- T4 `gmail read` (CONFIG_MISSING) → `ConfigurationMissingError: Gmail service not configured`. ✓ (honest missing)
- Secret leak scan: 0 hits. ✓

**T14 regression proof (`p22-p19-p20-regression-proof.md`):**
- Redis `life_kernel:hard_stop` clear (empty) on live VPS post-restart ✓
- `HARD_STOP requested - routing to END` 0 hits ✓
- `hard_stop_detected_live` 0 hits ✓
- No P20 closed file modified ✓
- `grep -rn "from src.life_kernel" src/life_integrations/` → 0 hits ✓ (P22 does not import P20 closed modules)

### Live VPS state (read-only via `ssh guinevere-vps`)

- `redis-cli ping` → `PONG` ✓
- `redis-cli get life_kernel:hard_stop` → empty (nil) ✓ — consistent with T14 regression evidence
- Working directory `/home/guinevere/code/guinevere` confirmed; env loading instruction from task spec (`.env.core` grep + export) works.

---

## Hard-Rejection Check

| Criterion | Result |
|-----------|--------|
| Secrets printed in any artifact | NO — 0 hits in `journalctl` secret scan ✓ |
| Fake PASS claim on HARD STOP | NO — initial T3 bug is **documented as PASS post-fix only**, with explicit "Initial run had a bug" acknowledgement ✓ |
| HARD STOP not actually blocking L2+ | NO — post-fix T3 raises `HardStopBlockedError` on `filesystem write` ✓ |
| Bypass path around `router.py:177` ActionRouter | NO — grep confirms single call site, no alternate paths ✓ |
| Consent fail-open on L2+ missing/revoked | NO — `ConsentGate.check()` returns `(False, "no consent checker configured — fail-closed")` and `(False, "consent not granted for scope: ...")` ✓ |
| Migration not applied but claimed pass | N/A (this dimension does not apply) |
| Doc lies about state | NO — `p22-configured-adapter-smoke.md` explicitly discloses the post-fix narrative, including the initial sync/async bug. No forgery. |
| Audit log gap | NOTED — AuditLogger wires to `journalctl` structured logs but **not** to `audit.integration_api_log` DB table (smoke passed `audit_writer=None`). This is documented as accepted gap; L2+ is fail-closed so no L2+ audit rows would be produced anyway. NOT a rejection for this dimension but flagged for `consent-audit` dimension. |

---

## Recommendations (for round 2)

**Required before PASS:**

1. **(F1, block for round 2)** Add an automated regression test that constructs `HardStopShim` with a sync `redis.Redis` client, sets `life_kernel:hard_stop=1`, and asserts `is_hard_stop_active() is True`. This pins the post-fix behavior so future async/sync client mis-wiring cannot silently regress to "HARD STOP fell through". Path suggestion: `tests/life_integrations/test_shims_hard_stop.py::test_sync_redis_hard_stop_blocks`.

2. **(F2, block for round 2)** Make `HardStopShim` **raise** `HardStopShimWiringError` on sync-path-detected-async-redis, OR document the dual-source fallback contract in the runtime factory and add a test that asserts the fallback works when both sources exist. The current one-time warning is fine for observability but is not a regression barrier.

**Recommended (not blocking):**

3. Move the structured audit log → `audit.integration_api_log` table (P19-P22 wiring planned in `p22-real-client-wiring.md`). This closes the partial-audit gap noted in T13.

4. Add a `tests/life_integrations/test_consent_gate.py` covering all five branches of `ConsentGate.check()` (L1 skip / HARD STOP / L4 forbid / L2+ no-checker fail-closed / L2+ consent-denied).

---

## Structured Verdict

```json
{
  "verdict": "NEEDS_REVIEW",
  "summary": "HARD STOP post-fix blocks L2+ absolutely (T3 raises HardStopBlockedError on filesystem write at L2_WRITE; redis life_kernel:hard_stop=1 confirmed via sync shim). Consent fail-closes L2+ (T2 raises ConsentDeniedError with no checker wired; T4 is unrelated CONFIG_MISSING). No secrets printed, no fake PASS, no alternate bypass path around router.py:177. Two findings: F1 (high) — the initial sync/async redis misuse is documented but not regression-pinned, so future drift could re-silence HARD STOP without violating the current observable state; F2 (medium) — the shim warns instead of raises on async-in-sync-path, falling through to in-process handler as the only second source. Neither finding is a hard rejection of the documented evidence, but both should be closed before round-2 PASS.",
  "findings": [
    {
      "severity": "high",
      "title": "Initial T3 silent-fallthrough bug not regression-pinned — sync/async redis mis-wiring could re-silence HARD STOP",
      "detail": "Post-fix evidence is load-bearing only if a test prevents the regression. The original failure mode (async redis client in sync path silently returns False for redis_active) exact-matches the shim docstring's HARD REJECTION scenario. Adding a unit test asserts HardStopShim.is_hard_stop_active() returns True when life_kernel:hard_stop=1 and only a sync redis client is wired. Without this, a future factory change returning to the pre-fix state would exhibit T3 PASS only because of the in-process HardStopHandler fallback, not because the global key is honored.",
      "evidence": "src/life_integrations/_shims.py:65-99 (sync path); docs/setup-evidence/P22/production-activation/runtime/p22-configured-adapter-smoke.md:33-47 (post-fix narrative); tests/life_integrations/ expected to lack a shim regression test (verify in round 2)"
    },
    {
      "severity": "medium",
      "title": "HardStopShim sync path warns but does not raise on async-redis detection",
      "detail": "_shims.py:82-89 detects an un-awaitable value via hasattr(value, '__await__') and logs hard_stop_shim.async_redis_in_sync_path once while continuing. The shim then falls through to handler.is_safe (line 105). If a future deployment loses the in-process handler (e.g., refactor moves it out of the runtime factory) and the only source is an async redis client, HARD STOP will silently fall through. Recommended: hard-fail at startup if HardStopShim is constructed with an async redis and no in-process handler.",
      "evidence": "src/life_integrations/_shims.py:80-99"
    }
  ]
}
```
