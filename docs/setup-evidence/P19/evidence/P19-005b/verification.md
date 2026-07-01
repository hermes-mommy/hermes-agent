# P19-005b — Feature-Flagged thread_id Selection — Verification Report

## 1. Overview

| Field | Value |
|-------|-------|
| **Epic** | P19 — Multi-Project Context |
| **Wave** | P19-005b — Feature-flagged `thread_id` selection in heartbeat |
| **Status** | PASS |
| **Date** | 2026-06-25 |
| **Implementing agent** | Sub-agent (005b) |
| **Scope** | 1 source file modified, 1 test file created, 2 evidence files created |

## 2. Files Modified / Created

| File | Change |
|------|--------|
| `src/life_kernel/heartbeat.py` | MODIFIED — added `_resolve_thread_id()` helper, replaced all 6 unconditional `"thread_id": "heartbeat"` with flag-conditional call |
| `tests/life_kernel/test_thread_id_flag.py` | CREATED — 13 unit tests for flag OFF/ON/Redis-unreachable/edge cases |
| `docs/setup-evidence/P19/evidence/P19-005b/verification.md` | CREATED — this file |
| `docs/setup-evidence/P19/evidence/P19-005b/auditor-gate.md` | CREATED — gate checklist |

## 3. Validation

### 3.1 Local syntax checks (all PASS)

```
python -c "import ast; ast.parse(open('src/life_kernel/heartbeat.py',encoding='utf-8').read()); print('heartbeat.py syntax OK')"
```

| File | Result |
|------|--------|
| `src/life_kernel/heartbeat.py` | PASS |
| `tests/life_kernel/test_thread_id_flag.py` | PASS |

### 3.2 Import check (PASS)

```
python -c "import src.life_kernel.heartbeat; print('import OK')"
```

Result: `import OK`

### 3.3 Forbidden pattern check (PASS)

```
grep -rnE "type: ignore| as any|^[[:space:]]*except:" src/life_kernel/heartbeat.py
```

→ **0 matches** (no bare except, no type: ignore, no as any in added code)

### 3.4 Grep: unconditional `thread_id = "heartbeat"` (PASS — 0 unconditional)

```
grep -nE 'thread_id\s*=\s*"heartbeat"' src/life_kernel/heartbeat.py
```

→ **0 matches** (exit code 1). All 6 sites now call `_resolve_thread_id()` which conditionally resolves to `"heartbeat"` when the flag is OFF.

### 3.5 Grep: helper function + flag reference present (PASS)

```
grep -n "_resolve_thread_id\|feature:projects:enabled" src/life_kernel/heartbeat.py
```

→ 7 matches (1 definition + 6 call sites for `_resolve_thread_id`, plus `feature:projects:enabled` key literal in the helper)

### 3.6 Unit test results (local — all 13 PASS)

```
python -m pytest tests/life_kernel/test_thread_id_flag.py -v
```

| Test | Result |
|------|--------|
| `TestThreadIdFlagOff::test_flag_returns_none` | PASS |
| `TestThreadIdFlagOff::test_flag_returns_empty` | PASS |
| `TestThreadIdFlagOff::test_flag_returns_false_string` | PASS |
| `TestThreadIdFlagRedisUnreachable::test_redis_connection_error` | PASS |
| `TestThreadIdFlagRedisUnreachable::test_redis_timeout_error` | PASS |
| `TestThreadIdFlagOn::test_flag_on_with_project` | PASS |
| `TestThreadIdFlagOn::test_flag_on_with_another_project` | PASS |
| `TestThreadIdFlagOn::test_flag_on_with_empty_project` | PASS |
| `TestThreadIdFlagOnNoProject::test_flag_on_no_project` | PASS |
| `TestThreadIdFlagOnNoProject::test_flag_on_project_omitted` | PASS |
| `TestThreadIdFlagEdgeCases::test_flag_value_case_insensitive` | PASS |
| `TestThreadIdFlagEdgeCases::test_flag_value_1` | PASS |
| `TestThreadIdFlagEdgeCases::test_bare_heartbeat_no_flag` | PASS |

**13/13 passed.**

### 3.7 P20 preflight status

Pre-P19-005 preflight at `docs/setup-evidence/P19/evidence/implementation/p20-preflight-pre-P19-005.md` confirmed:
- `hard_stop_requested=False`
- 0 journal errors, 0 restarts, 0 OOM
- **CLEAN — proceed authorized**

### 3.8 VPS regression command (parent to run)

```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings'
```

Expected: all existing P20 tests still pass (426 passed, 7 skipped, 0 failed). The new `test_thread_id_flag.py` must also pass (13/13).

### 3.9 VPS unconditional-thread_id check (parent to run)

```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && grep -nE "thread_id\s*=\s*\"heartbeat\"" src/life_kernel/heartbeat.py'
```

Expected: 0 matches.

## 4. Hard rejection checks

| Check | Status | Notes |
|-------|--------|-------|
| Bare `thread_id="heartbeat"` unconditional remains | PASS | grep returns 0 matches |
| P20 regression: flag OFF behavior differs from current | DEFERRED | Parent to run full `tests/life_kernel/` on VPS |
| Flag-read failure crashes heartbeat or changes thread_id | PASS | `except RedisError` catches and falls back to `"heartbeat"` |
| `thread_id = "heartbeat-None"` when project_id is None | PASS | `flag_on and project_id` — falsy project_id skips conditional branch |
| HARD STOP touched | PASS | No changes to hard_stop logic in `_heartbeat_1s` |
| `# type: ignore` / `as any` / bare except in additions | PASS | grep returns 0 |
| Files other than heartbeat.py + test + evidence modified | PASS | Only heartbeat.py + new test + evidence |
| Evidence files missing | PASS | verification.md + auditor-gate.md created |

## 5. VPS commands

### Full regression
```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings'
```

### Unconditional thread_id grep
```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && grep -nE "thread_id\s*=\s*\"heartbeat\"" src/life_kernel/heartbeat.py'
```

### Production flag status (flag is absent in prod — confirms P20 non-interference)
```bash
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "import redis; r = redis.Redis.from_url(...); print(r.get(\"feature:projects:enabled\"))"'
```

Expected: `None` (flag absent → OFF → legacy `thread_id="heartbeat"`)

### Rollback (if needed)
```bash
# Set flag OFF explicitly (though absent == OFF already):
ssh guinevere-vps 'cd /home/guinevere/code/guinevere && .venv/bin/python -c "import redis; r = redis.Redis.from_url(...); r.delete(\"feature:projects:enabled\")"'

# Revert heartbeat.py:
git checkout -- src/life_kernel/heartbeat.py
```

## 6. Architectural decisions

- **`_resolve_thread_id` is an async method on HeartbeatService** — It reads from `self.redis_client` (the same `aioredis.Redis` instance used for HARD STOP), avoiding a new connection or import. This leverages existing infrastructure.
- **Semantic flag decoding** — The raw Redis bytes are decoded and compared against an explicit allowlist (`"true"`, `"1"`, `"yes"`). This prevents accidental flag writes (e.g. `b"false"` being truthy in Python). Everything else defaults to OFF.
- **FAIL-SAFE design** — If Redis is unreachable (`RedisError`), the helper logs a warning and returns `"heartbeat"`. The heartbeat never crashes from a flag-read failure.
- **No P20 behavior change when flag OFF** — When the feature flag is absent (prod), or when set to any falsy value, all 6 call sites produce exactly `"heartbeat"` — the same string as before this change. P20 semantics are byte-identical.
- **No `"heartbeat-None"` risk** — The condition `if flag_on and project_id:` skips when `project_id` is `None`, `""`, or any other falsy value, so the literal string `"heartbeat-None"` can never appear.
- **RedisError import** — Added `from redis.exceptions import RedisError` at the top of the file (stdlib-level import, no new dependency). This is the only new import.

---

## DB-Verification Addendum (PARENT-VERIFIED)

*Parent to fill after VPS run.*

---

## Parent DB/Regression Addendum (PARENT-VERIFIED, 2026-06-25)

**Status: PASS (full P20 regression verified on VPS).**

### Local verification (parent re-run)
- `heartbeat.py` syntax OK; `grep -nE 'thread_id\s*=\s*"heartbeat"'` → **0 unconditional matches** (critical P20-compat gate). `_resolve_thread_id` helper at line 125 + 6 call sites (343, 383, 410, 492, 510, 677); `feature:projects:enabled` flag at line 143; fail-safe `except RedisError` (line 146). Only `heartbeat.py` modified (+56/-6). 0 `as any`/`# type: ignore`/bare-except in additions.

### Production flag verification (VPS, read-only)
`feature:projects:enabled` key is **ABSENT** across Redis DB 0, 5, 6 → flag OFF → prod P20 behavior is byte-identical (legacy `thread_id="heartbeat"`). No runtime behavior change in production.

### Full P20 regression (VPS)
```
$ .venv/bin/python -m pytest tests/life_kernel/ -q -p no:warnings
439 passed, 7 skipped in 48.65s
```
Includes 13 new `test_thread_id_flag.py` tests (flag OFF/unreachable/ON+project/ON+no-project/edge) + all pre-existing life_kernel tests.

### Parent fix applied (test-infrastructure, not test-skip)

Initial VPS regression showed **1 failure**: `test_heartbeat.py::TestHeartbeat60SGraphInvocation::test_heartbeat_60s_invokes_graph` — `TypeError: object MagicMock can't be used in 'await' expression`.

**Root cause:** 6 of the 12 `mock_redis_client` fixtures in `test_heartbeat.py` created `MagicMock(spec=aioredis.Redis)` WITHOUT overriding `.get` to an `AsyncMock`. The real `aioredis.Redis.get` is async; the new `_resolve_thread_id` calls `await self.redis_client.get(...)`, so the un-awaitable auto-mock failed. The other 6 fixtures (and 6 test-body overrides for HARD-STOP tests) already set `redis_client.get = AsyncMock(...)`.

**Fix:** added `redis_client.get = AsyncMock(return_value=None)` to the 6 fixtures missing it (matching the existing pattern). This completes the mock's async contract — it does NOT delete or skip any test, does NOT weaken any assertion, and models flag-absent/hard-stop-clear (preserving the `thread_id == "heartbeat"` assertion the 60s test still makes and now passes). Legitimate test-infrastructure fix per AGENTS.md (fix root cause; don't skip failing tests).

### Hard-rejection resolution
| Criterion | Status |
|---|---|
| bare `thread_id="heartbeat"` unconditional | ✅ RESOLVED — 0 matches |
| P20 regression (flag OFF) | ✅ RESOLVED — 439 passed, 7 skipped, 0 failed |
| flag-read failure crashes heartbeat | ✅ RESOLVED — `except RedisError` fail-safe to legacy |
| `thread_id="heartbeat-None"` | ✅ RESOLVED — `if flag_on and project_id:` guard |
| HARD STOP touched | ✅ N/A — `life_kernel:hard_stop` untouched |
| `# type: ignore`/`as any`/bare except in additions | ✅ RESOLVED — 0; typed `except RedisError` |

**P19-005b verdict: PASS (P20 regression 439/0 verified; prod flag OFF = byte-identical P20).**
