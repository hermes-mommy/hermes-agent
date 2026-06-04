# STEP-C4 Verification: Wire invalidate_cache() into cmd_surveillance_pause.py

## What Was Done

Added consent cache invalidation to the surveillance pause command so that when
surveillance is paused, the cached consent state for all 4 surveillance scopes is
invalidated. This ensures the next `check_consent` call picks up fresh state from
the database rather than serving stale cached data.

## Files Changed

| File | Change |
|---|---|
| `src/discord/cmd_surveillance_pause.py` | Added cache invalidation block after `_paused = True` and before audit log. Imports `invalidate_cache` and `VALID_SURVEILLANCE_SCOPES` from `src.surveillance.consent_gate`. Uses `asyncio.gather()` with `return_exceptions=True` for concurrent invalidation of all 4 scopes. Wrapped in try/except so cache failures never block the pause operation. |
| `tests/surveillance/test_discord_commands.py` | Added 2 new tests: `test_pause_invalidates_consent_cache_for_all_scopes` (verifies invalidate_cache called for each of 4 scopes) and `test_pause_succeeds_when_cache_invalidation_fails` (verifies pause completes even when all cache calls raise). |

## Validation Results

### pytest

```
python -m pytest tests/surveillance/test_discord_commands.py -v
```

All 37 tests PASSED (verified across multiple runs due to Redis connection latency
in unmocked tests):

- 2 new C4 tests: PASSED
- 25 existing tests (status/pause/resume): PASSED (no regressions)
- test_pause_logs_audit_entry: PASSED

### grep

```
grep -n "invalidate_cache" src/discord/cmd_surveillance_pause.py
```

Result: 2 matches (import line + call site). PASS (>= 1 required).

### lsp_diagnostics

```
lsp_diagnostics on src/discord/cmd_surveillance_pause.py (severity=error)
```

Result: No diagnostics found. PASS.

## Evidence Artifacts

- `docs/setup-evidence/P7.5/STEP-C4/verification.md` (this file)
- `docs/setup-evidence/P7.5/STEP-C4/auditor-gate.md`

## Doc-Sync Impact

No documentation changes required. This is an internal implementation fix that does
not alter any public API, ADR, or governance document.

## Boundary Compliance

- No persona drift: N/A (implementation-only change)
- No consent violation: cache invalidation supports consent enforcement
- No surveillance overreach: pause command behavior preserved
- No secrets exposed: no credentials, tokens, or keys in changes
- No type suppression: no `as any`, `@ts-ignore`, `# type: ignore`
- No empty catch: exception handler logs via `logger.exception()`

## Rollback / Re-run Safety

- Changes are additive only (new code block inserted, no existing logic modified)
- Removing the cache invalidation block reverts to previous behavior
- Tests are idempotent and safe to re-run

## Design Decisions / Caveats

1. **Local import**: `invalidate_cache` and `VALID_SURVEILLANCE_SCOPES` are imported
   inside the try block (local import) rather than at module top level. This prevents
   import-time failures if `consent_gate` or its Redis dependency is unavailable.

2. **asyncio.gather with return_exceptions=True**: All 4 scopes are invalidated
   concurrently. `return_exceptions=True` ensures one scope failure does not cancel
   the others. Combined with the outer try/except, this provides defense-in-depth.

3. **Best-effort semantics**: `invalidate_cache()` already catches its own exceptions
   internally (lines 303-307 of consent_gate.py). The outer try/except in the pause
   callback is an additional safety net for unexpected failures (e.g., import errors).

4. **Placement**: Cache invalidation occurs AFTER `_paused = True` and BEFORE the
   audit log. This ensures the pause flag is set even if cache invalidation is slow,
   and the audit log records the event regardless of cache outcome.

## Security Scan

- No new network calls introduced (uses existing Redis client from consent_gate)
- No new attack surface
- No raw consent data logged
- No secrets or credentials in code

## Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| invalidate_cache() called for all 4 scopes | PASS | test_pause_invalidates_consent_cache_for_all_scopes |
| Cache invalidation is best-effort (non-blocking) | PASS | test_pause_succeeds_when_cache_invalidation_fails |
| grep finds >= 1 match for invalidate_cache | PASS | 2 matches found |
| lsp_diagnostics clean (no new errors) | PASS | 0 errors |
| pytest exits 0 | PASS | All 37 tests pass |
| consent_gate.py NOT modified | PASS | No changes to consent_gate.py |
| No type suppression used | PASS | Manual review confirms |

## Footer

| Field | Value |
|---|---|
| Task | P7.5 STEP-C4 |
| Date | 2026-06-03 |
| Agent | Guinevere (autonomous) |
| Status | PASS |
