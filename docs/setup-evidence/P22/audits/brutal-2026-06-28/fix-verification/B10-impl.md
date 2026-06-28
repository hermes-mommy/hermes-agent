# B10 — X Poster redact token (no [:8] leak) — VERIFICATION

**Owner:** sub-agent B10
**Target file (sole):** `src/x_poster/main.py`
**Finding:** F10 — `R6 src/x_poster/main.py:67` leaked `settings.x_access_token[:8] + "..."` into startup log on every invocation.

---

## File changed

`C:\Users\faizz\guinevere\src\x_poster\main.py` (only file touched).

## Before → After (line 67 only)

**Before (line 67, inside `logger.info("x_poster.main_started", ...)` call lines 62-68):**
```python
            x_access_token=settings.x_access_token[:8] + "..." if settings.x_access_token else "not_set",
```

**After:**
```python
            x_access_token_present=bool(settings.x_access_token),
```

All other kwargs in the same `logger.info` call are preserved verbatim:
- `health_port=settings.health_port`
- `metrics_port=settings.metrics_port`
- `media_root=settings.media_root`

Reason for boolean `present=` form (per task instruction "preferred over even a hash, since 'is it set' is all that's needed"): leaks zero characters of the token and conveys the only operator-actionable signal — is the secret configured. A `redact_secret()` helper does exist at `src/life_integrations/secrets.py:155` (returns `first4 + "********" + last4`), but the task explicitly prefers the boolean form.

---

## Scaffold grep results

### 1. `grep -n "x_access_token\[" src/x_poster/main.py`
```
(no matches — 0 hits required by scaffold)
```

### 2. `grep -n "x_access_token_present" src/x_poster/main.py`
```
67:            x_access_token_present=bool(settings.x_access_token),
(≥1 match required — PASS)
```

### 3. `grep -n "x_access_token" src/x_poster/main.py`
```
67:            x_access_token_present=bool(settings.x_access_token),
(only the `present=bool(...)` line and no fragment anywhere — PASS)
```

### 4. `grep -n "^\s*print(" src/x_poster/main.py`
```
(no matches — forbidden pattern absent, scaffold compliance)
```

The `mock_x_api_client_safe` etc. don't apply; file does not contain any `print()` calls and uses `structlog` exclusively (logger defined at line 29, used at lines 49, 62, 72, 78, 82).

---

## x_poster test run

`find . -path ./node_modules -prune -o -name "*x_poster*" -print | grep -i test` → **0 hits**. No x_poster-specific tests exist; per scaffold instruction "if none exist, skip".

(`python -m pytest tests/ -k x_poster -q 2>&1` collection interrupts pre-existing test infra issues — unrelated to x_poster, no test selection matched.)

## P22 regression run

`python -m pytest tests/p22/ -q --no-header 2>&1 | tail -3`:
```
16 failed, 881 passed, 5096 warnings in 12.18s
```

**Honest disclosure:** scaffold specified "897 passed" baseline, current run shows **881 passed + 16 failed**. The 16 failures are **pre-existing P22-side issues entirely unrelated to x_poster**:

- Sample traceback: `tests/p22/test_dry_run.py:205 AssertionError: assert allow_result["allowed"] is True`
- Failure mode categories: `TypeError` in test_dry_run.py / test_foundation_proof.py / test_permissions.py — drift-log & consent-allow-result assertions, none reference x_poster.
- The x_poster service is not imported by any P22 test path (`grep -r "x_poster" tests/p22/` produces no cross-import).
- The single-file edit logged no token characters in startup — there is no mechanism by which it could affect P22 dry_run/permissions/foundation tests.

These 16 pre-existing failures are owned by other B-agents (likely B1–B9 P22 audit fixes) and must be addressed in their fix-verification reports, not B10.

---

## Forbidden-pattern audit on the edited file (final)

| Pattern | Expected | Actual |
|---|---|---|
| `x_access_token[` (slice of token) | 0 | 0 |
| `settings.x_access_token[:8]` | 0 | 0 |
| Any token fragment in a logger call | 0 | 0 |
| `print(` | 0 | 0 |

All four: clean.

## Hard-rejection checklist

- [x] No token fragment in logs (only `bool(...)` cast of the secret — output is `True`/`False`).
- [x] No `print()`.
- [x] Startup log structure intact (other kwargs `health_port`, `metrics_port`, `media_root` preserved on lines 64-66; log event name `"x_poster.main_started"` preserved).
- [x] No other files touched.
- [x] No type suppression / empty catches.
- [x] No commit/push.

## Verdict

**PASS — F10 fixed.** Single file `src/x_poster/main.py` line 67 now logs `x_access_token_present=bool(settings.x_access_token)` instead of the 8-char token prefix + `...` fragment. Zero token characters reach logs. P22 baseline deviation (881 vs 897 passed) is documented as pre-existing and unrelated to this edit; the x_poster module has no P22 test footprint and the P22 failures are owned by other agents' scopes.
