# P22 Round-2 Audit — Dimension: consent-hardstop (FINAL GATE)

**Date:** 2026-06-27
**Auditor:** independent auditor (round 2, FINAL GATE)
**Repo:** C:/Users/faizz/guinevere
**VPS:** faiz-prod-01 (Tailscale 100.94.104.22, user guinevere), reachable via `ssh guinevere-vps`
**Round-1 verdict:** NEEDS_REVIEW (1 HIGH, 1 MEDIUM)
**Round-2 verdict:** **PASS**

---

## Verdict: **PASS**

Both round-1 findings (F1 HIGH sync/async regression, F2 MEDIUM warns-instead-of-raise) are genuinely fixed in code, regression-pinned with new `tests/p22/test_shims.py`, and independently verified live on the VPS. No new regressions. No hard-rejection criteria violated. Consent + HARD STOP behavior is correct, fail-closed, and future-drift-protected.

---

## Round-1 Findings Resolution

### F1 — sync/async redis mis-wiring regression (HIGH) — FIXED

**Round-1 concern:** `HardStopShim.is_hard_stop_active()` was called from the sync `ConsentGate.check()` path with an **async** `redis.asyncio.Redis` client. `.get()` returned a coroutine that could not be awaited sync, so HARD STOP silently fell through. The post-fix runtime factory switches to a sync `redis.Redis` (separate from the app's async redis). The fix is documented but not regression-pinned — a future factory change could revert to the pre-fix state without violating current observable logs.

**Resolution evidence:**

1. **`tests/p22/test_shims.py` exists with 11 tests** (verified via `Read C:/Users/faizz/guinevere/tests/p22/test_shims.py`):
   - `TestHardStopShim` (6 tests): `test_sync_redis_hard_stop_set_returns_true` (pin-set-key-returns-True), `test_sync_redis_hard_stop_clear_returns_false`, `test_sync_redis_hard_stop_falsey_value_returns_false` (covers all 6 CLEAR_VALUES), `test_handler_is_safe_returns_true`, `test_redis_or_handler_conservative_or`, `test_no_source_returns_false_and_logs`.
   - `TestConsentGateShim` (5 tests): fail-closed branches (no-checker, bool-true, ConsentCheckResult-with-allowed, raises, ambiguous).
   - **Live test run:** `python -m pytest tests/p22/test_shims.py -v` → `11 passed, 46 warnings in 3.19s`. The regression test `test_sync_redis_hard_stop_set_returns_true` would fail if HardStopShim was wired with an async redis or if the constructor raised on a sync redis; it passes.

2. **Runtime factory uses SYNC redis:** `src/life_integrations/runtime.py:205-220` parses REDIS_URL, builds a sync `redis.Redis` instance, calls `ping()` for connectivity, then logs `p22.hard_stop_shim.sync_redis_ready` (line 220). HardStopShim is then constructed with `redis_client=sync_redis` (line 230). The async-redis detection path in `_shims.py:82-89` **cannot fire** because `_module.startswith("redis.asyncio")` is False for sync `redis.Redis`.

3. **Live VPS log:** `journalctl | grep p22.hard_stop_shim.sync_redis_ready` shows the log on every guinevere-core restart (23:16:36 and 23:50:28). **Zero `async_redis_in_sync_path` warnings** in journalctl (grep returned 0 lines) — confirming the runtime is correctly using sync redis.

4. **Independent live re-run (this audit, 2026-06-27 11:51 WIB):** I personally SSH'd to faiz-prod-01, ran:

   ```python
   import redis as r
   cli = r.Redis(host='localhost', port=6379, db=0, ...)
   cli.set('life_kernel:hard_stop', '1')
   from src.life_integrations._shims import HardStopShim
   shim = HardStopShim(redis_client=cli, hard_stop_handler=None)
   shim.is_hard_stop_active()  # → True
   cli.delete('life_kernel:hard_stop')  # → None
   ```

   `is_hard_stop_active()` returned True with the live sync wired redis client. State was then UNSET to `None` (verified via `redis-cli GET life_kernel:hard_stop`). No secrets printed. No destructive ops left behind.

**Verdict:** Regression is genuinely fixed and pinned. `round1_findings_resolved: true`.

### F2 — HardStopShim warns instead of raises on async redis (MEDIUM) — FIXED

**Round-1 concern:** `_shims.py:82-89` logged a one-time warning when an async redis was detected, then fell through to the in-process handler. If the in-process handler was also absent, HARD STOP could silently underreport.

**Resolution evidence:**

`src/life_integrations/_shims.py:64-77` (construction-time hard-fail) reads:

```python
if self._redis is not None and self._handler is None:
    _module = type(self._redis).__module__ or ""
    if _module.startswith("redis.asyncio"):
        raise RuntimeError(
            "HardStopShim constructed with an async redis client "
            f"({_module}) and no in-process handler — the sync "
            "is_hard_stop_active() path cannot query async redis, so "
            "HARD STOP would silently never fire. Pass a SYNC "
            "redis.Redis client (see runtime.py build_runtime_registry)."
        )
```

This is the **exact recommended action** from round-1 (M7 fix per `round-1-fix-log.md:54`). A future wiring change that passes an async redis **without** an in-process handler now raises `RuntimeError` at construction — HARD STOP cannot silently underreport. Confirmed:

- Live VPS `src/life_integrations/_shims.py` line count is 235 (matches local — `wc -l` via SSH).
- Docstring update on `_shims.py:1-20` calls this HARD REJECTION explicitly.
- The runtime factory in `runtime.py:229-232` always wires `hard_stop_handler=hard_stop_handler` (non-None when a `HardStopHandler` is provided by lifespan), so the new RuntimeError is not triggered in the production path.

**Verdict:** M7 fix genuinely implemented at construction time, not just observability warning. `round1_findings_resolved: true`.

### M6 — HARD STOP unset not documented (MEDIUM) — FIXED

**Round-1 concern:** Smoke didn't document the unset after the HARD STOP test.

**Resolution evidence:** Verified live now and in r1:
- `redis-cli GET life_kernel:hard_stop` → empty (verified this audit, post my own SET+DELETE cycle).
- `p22-p19-p20-regression-proof.md:34` documents the empty state.
- `p22-configured-adapter-smoke.md:30-45` documents the post-fix HARD STOP block (T3 = `HardStopBlockedError`).

---

## New Findings (round 2)

| # | Severity | Title | Detail | Evidence |
|---|----------|-------|--------|----------|
| — | — | None | No new findings. | — |

(The audit dispatched an independent live verification of the HARD STOP path on the live VPS — see `hard_stop=1 SET/*`*UNSET` log. Result confirms F1 is fixed in practice, not just in tests.)

---

## What Was Verified

### Code artifacts (local read-only)

**`src/life_integrations/_shims.py`** (235 lines, lines read 1-235):
- Lines 64-77: construction-time `RuntimeError` if `redis.asyncio.*` module + no in-process handler. **Not just a one-time warning** — it raises at construction.
- Lines 79-135 (`is_hard_stop_active()`): sync path queries `self._redis.get(REDIS_KEY)`. Async-client detection at line 96 still exists as a defense-in-depth warning (for cases where an async client IS wired but a handler IS present, the run is still safe).
- Lines 137-170 (`is_hard_stop_active_async()`): proper await for async clients.
- Lines 173-235 (`ConsentGateShim`): fail-closed on no-checker / raises / ambiguous.

**`src/life_integrations/consent.py`** (169 lines, lines read 1-169):
- `ConsentGate.check()` order matches documented L1-skip → HARD STOP → L4-forbid → L2+ checker (fail-closed) → L2+ granted. Confirmed verbatim at lines 100-145.
- HARD STOP block at lines 105-112 returns `(False, "HARD STOP active — action blocked")` ABSOLUTE — not gated by tier. L1 still passes; L2+ blocked.

**`src/life_integrations/runtime.py`** (257 lines, lines read 180-257):
- Lines 205-220: sync `redis.Redis` constructed with `socket_timeout=2`, `socket_connect_timeout=2`, `ping()` verified, `p22.hard_stop_shim.sync_redis_ready` log emitted. **Not** using the async redis_client passed in.
- Lines 229-232: `HardStopShim(redis_client=sync_redis, hard_stop_handler=hard_stop_handler)` — bypasses the new construction-time `RuntimeError` because both sources are wired correctly.
- Lines 233-241: `ConsentGateShim(consent_checker=consent_checker)` + `ActionRouter(consent_checker=consent_shim, hard_stop_checker=hard_stop_shim)`.

**`tests/p22/test_shims.py`** (141 lines, lines read 1-141):
- `TestHardStopShim` (6 tests) including the load-bearing `test_sync_redis_hard_stop_set_returns_true`.
- `TestConsentGateShim` (5 tests) covering all 5 fail-closed branches.
- `python -m pytest tests/p22/test_shims.py -v` → **11 passed**.

**`tests/p22/test_consent_hardstop.py`** (113 lines, lines read 1-113):
- Covers L1 passes, L2 requires consent, L2 allowed when granted, HARD STOP blocks L2, HARD STOP blocks L3, L4 forbidden, fail-closed no-checker, consent revocation absolute (round-trip). This satisfies the round-1 recommended (non-blocking) item #4.

### Live VPS state (independent verification via `ssh guinevere-vps`)

| Check | Expected | Actual |
|---|---|---|
| `redis-cli ping` | `PONG` | PONG ✓ |
| `redis-cli GET life_kernel:hard_stop` (initial) | nil (empty) | empty ✓ |
| `wc -l src/life_integrations/runtime.py` | 257 | 257 ✓ |
| `wc -l src/life_integrations/_shims.py` | 235 | 235 ✓ |
| `wc -l src/life_integrations/consent.py` | 169 | 169 ✓ |
| `journalctl -u guinevere-core \| grep p22.hard_stop_shim.sync_redis_ready` | present | present (2 restart events) ✓ |
| `journalctl \| grep async_redis_in_sync_path` | absent | absent (0 hits) ✓ |
| `journalctl \| grep HARD STOP` (in P22 logs) | absent (key unset in prod) | absent ✓ |
| Live `SET life_kernel:hard_stop=1` then `HardStopShim(...).is_hard_stop_active()` | True | True ✓ (this audit) |
| Live `DEL life_kernel:hard_stop` | None | None ✓ (this audit) |

### Live smoke-equivalent (this audit, runtime-level)

Constructed a `HardStopShim` instance with the production-style sync redis client, called `is_hard_stop_active()` directly while `life_kernel:hard_stop=1`, got `True`. Did **not** run a full router T1-T4 smoke (no need — T13 smoke evidence is post-factory-fix and re-verifiable via the regression tests; running a fresh T3 would be a router-side effect, not required to prove HARD STOP works). State reset to clean.

---

## Hard-Rejection Check

| Criterion | Result |
|-----------|--------|
| Secrets printed in any artifact | NO — only names/refs; live verify used no token values ✓ |
| Fake PASS claim on HARD STOP | NO — F1 documented as fixed+pinned; live verification re-proved HARD STOP works ✓ |
| HARD STOP not actually blocking L2+ | NO — live sync `HardStopShim` returned True for `hard_stop=1`; T3 smoke evidence (post-fix) shows `HardStopBlockedError` ✓ |
| Bypass path around `router.py:177` ActionRouter | NO — single call site confirmed; new tests do not change routing surface ✓ |
| Consent fail-open on L2+ missing/revoked | NO — `ConsentGate.check()` returns `(False, "no consent checker configured — fail-closed")` and `(False, "consent not granted for scope: ...")` ✓ |
| Async redis silently falling through | NO — `_shims.py:64-77` raises `RuntimeError` at construction if `_module.startswith("redis.asyncio")` and no handler ✓ |
| Fake PASS via no-source-wired shim | NO — `_shims.py:128` logs `hard_stop_shim.no_source_wired` (loud) when both absent; `ConsentGate.check()` at line 105 prefers hard_stop_checker=None as "assumes clear" but the factory always wires a checker (lines 229-232) ✓ |
| Doc lies about state | NO — `p22-configured-adapter-smoke.md` and `p22-p19-p20-regression-proof.md` match code + live state ✓ |
| Audit log gap (partial, r1 noted) | NOTED again — AuditLogger still not wired to `audit.integration_api_log` table (smoke passed `audit_writer=None`); but L2+ fail-closed so no L2+ audit rows expected anyway. Not block for this dimension. ✓ |

---

## Recommendation

**READY FOR PRODUCTION ACTIVATION (consent dimension).**

No blockers. Dimension clean. Round-1 HIGH + MEDIUM findings genuinely fixed and regression-pinned. No new findings.

---

## Structured Verdict

```json
{
  "verdict": "PASS",
  "summary": "Both round-1 consent-hardstop findings are genuinely fixed and live-verified. F1 (HIGH) regression pinned by tests/p22/test_shims.py::TestHardStopShim::test_sync_redis_hard_stop_set_returns_true (11 passed locally); runtime factory at src/life_integrations/runtime.py:205-220 now constructs a sync redis.Redis client and logs p22.hard_stop_shim.sync_redis_ready; live VPS journalctl confirms sync_redis_ready log present and zero async_redis_in_sync_path warnings. F2 (MEDIUM) fixed by adding a construction-time RuntimeError in src/life_integrations/_shims.py:64-77 when an async redis client is wired without an in-process handler — HARD STOP cannot silently underreport anymore. Live re-test: SET life_kernel:hard_stop=1 then HardStopShim(...).is_hard_stop_active() returned True; state was UNSET to None after. No secrets printed, no fake PASS, no bypass path around router.py:177, consent fail-closed on L2+. Hard-rejection criteria all satisfied.",
  "round1_findings_resolved": true,
  "findings": []
}
```
