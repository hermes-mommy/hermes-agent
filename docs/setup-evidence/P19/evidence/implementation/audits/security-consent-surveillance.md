# P19 Security / Consent / Surveillance Re-Audit

- Date: 2026-06-26
- Auditor: P19 re-auditor (automated)
- Scope: consent_gate.py, consumer.py, models.py, secrets_vault.py, test_secret_isolation.py, test_consent_isolation.py
- Verdict: **FAIL** — 1 CRITICAL consent bypass, 1 MEDIUM consumer crash, 1 LOW stale-cache window

---

## BUG-1 [CRITICAL] — Legacy project_id=None path queries ALL rows, not global-only

**File:** `src/surveillance/consent_gate.py`
**Lines:** 362-373

### Symptom

When `check_consent(scope, project_id=None)` is called (the legacy path), it
invokes `_query_ledger(scope, max_age_hours=max_age_hours)` with both
`global_only=False` (default) and `project_id=None` (default).

In `_query_ledger` (lines 605-619), the WHERE clause becomes simply
`scope = :scope` — no `project_id IS NULL` filter. This means the query matches
**all** rows for that scope, including project-scoped rows.

### Impact

A project-scoped ACTIVE row with a recent `granted_at` will be returned by
`ORDER BY granted_at DESC LIMIT 1`, even if the global row is WITHDRAWN.

**Attack scenario:** Project A grants consent, then the operator withdraws
global consent (safe-word / HARD STOP). The legacy path still sees Project A's
ACTIVE row and returns `allowed=True`. Any code calling `check_consent(scope)`
without a `project_id` — including new callers not yet migrated to P19 —
silently bypasses the global withdrawal.

### Fix

Line 365, change:
```python
db_result = await _query_ledger(scope, max_age_hours=max_age_hours)
```
to:
```python
db_result = await _query_ledger(scope, global_only=True, max_age_hours=max_age_hours)
```

This ensures the legacy path only sees global (project_id IS NULL) rows,
matching the pre-P19 behavior.

---

## BUG-2 [MEDIUM] — Undefined variable `event_project_id` crashes consumer store step

**File:** `src/surveillance/consumer.py`
**Line:** 237

### Symptom

Line 237 references `event_project_id`, but the variable defined at lines
174-177 is named `project_id_val`. The name `event_project_id` is never
assigned anywhere in the file.

```python
# Line 174: variable is called project_id_val
project_id_val: uuid.UUID | None = None

# Line 237: but store uses undefined name
project_id=event_project_id,  # NameError
```

### Impact

Every event that passes the consent gate will raise `NameError` in the store
step. The retry loop (3 attempts) catches the exception and retries 3 times,
all failing. The event is then dropped (`return False`). This silently breaks
the entire consumer pipeline — no events are ever stored.

### Fix

Line 237, change:
```python
project_id=event_project_id,
```
to:
```python
project_id=project_id_val,
```

---

## BUG-3 [LOW] — Project-scoped cache invalidation does not invalidate global fallback cache

**File:** `src/surveillance/consent_gate.py`
**Lines:** 376-399

### Symptom

When global consent is withdrawn (e.g., safe-word), any previously cached
project-scoped results remain valid in Redis for up to 300 seconds. The
`invalidate_cache(scope, project_id=X)` function only deletes the
project-scoped key `consent:surveillance:scope:X`, not the global key
`consent:surveillance:scope`.

If a caller invalidates global consent via
`invalidate_cache(scope, project_id=None)` and a project-scoped cache entry
still exists, `check_consent(scope, project_id=X)` will hit the stale
project-scoped cache and return `allowed=True` for up to 300 seconds after
the withdrawal.

### Impact

LOW — the window is 300 seconds (CACHE_TTL_SECONDS). The DB is the source of
truth; the cache is best-effort. After TTL expires, the next check correctly
queries the DB. However, in a safe-word / emergency withdrawal scenario, 300
seconds of continued operation on stale cache is undesirable.

### Fix (recommended)

When global consent is withdrawn, callers should also invalidate project-scoped
cache entries. Alternatively, `invalidate_cache` could accept a `global_cascade`
parameter that deletes the global key AND all project-scoped keys matching the
scope pattern:

```python
async def invalidate_cache(scope: str, project_id: uuid.UUID | None = None, *, cascade: bool = False) -> None:
    redis_client = _get_redis()
    if cascade:
        # Delete global key + all project-scoped keys for this scope
        pattern = f"{CACHE_KEY_PREFIX}{scope}*"
        async for key in redis_client.scan_iter(match=pattern):
            await redis_client.delete(key)
    else:
        cache_key = _build_cache_key(scope, project_id)
        await redis_client.delete(cache_key)
```

---

## Non-Issues (verified correct)

### secrets_vault.py — PASS
Project isolation is structurally enforced by `dict[ProjectId, dict[str, str]]`.
Cross-project access is impossible through the public API. Thread-safe via RLock.
No security bugs found.

### test_secret_isolation.py — PASS
11 tests cover isolation, no-leak, fail-closed (unloaded returns None), load/unload
lifecycle, and domains listing. Coverage is adequate.

### test_consent_isolation.py — PASS
25 tests cover project pause isolation, global WITHDRAWN blocks all, no bypass via
project_id, cascade isolation, safe-mode, project-only scopes, high_blast scoping,
and structural invariants. These tests are well-designed but do NOT catch BUG-1 because
they always provide a `project_id` — the legacy `project_id=None` path is never tested
with mixed project-scoped + global rows.

### models.py — PASS (no project_id field)
`SurveillanceEventRequest` does not include a `project_id` field. This is intentional:
events receive project_id from server-side context (consumer extraction), not from
external callers. No issue.

### cache_key build — PASS
`_build_cache_key` correctly appends `:{project_id}` when project_id is set and uses
bare scope when None. No collision risk.

### _GLOBAL_ONLY_SCOPES guard — PASS
Lines 272-279 correctly strip project_id for global-only scopes
(`consent.memory.cross_project`). The warning log is appropriate.

### _PROJECT_ONLY_SCOPES guard — PASS
Lines 332-336 correctly block when project-scoped query returns no result and scope is
project-only (no global fallback).

---

## Test Gap

BUG-1 is not caught by existing tests because `test_consent_isolation.py` always passes
a `project_id` to `check_consent`. A test for the legacy path (no project_id) with a
project-scoped ACTIVE row and global WITHDRAWN row would expose the bypass. Example:

```python
async def test_legacy_path_respects_global_withdrawn_over_project_active(self):
    """Legacy (no project_id) must see only global rows."""
    mock_db = AsyncMock()

    async def _execute(stmt, params=None):
        result = MagicMock()
        # Global row is WITHDRAWN
        result.fetchone.return_value = (ConsentStatus.WITHDRAWN.value,)
        return result

    mock_db.execute = AsyncMock(side_effect=_execute)
    _set_db_session_for_testing(mock_db)

    # Legacy call — must see global WITHDRAWN, not any project-scoped row
    result = await check_consent("surveillance.app_usage")
    assert result.allowed is False
```

This test passes even today (mock returns WITHDRAWN), but it doesn't prove the SQL
query is correct. An integration test with real DB rows is needed to verify the fix.

---

## Verdict: FAIL

| # | Severity | Location | Description |
|---|----------|----------|-------------|
| 1 | CRITICAL | consent_gate.py:365 | Legacy path queries all rows, not global-only — consent bypass |
| 2 | MEDIUM | consumer.py:237 | Undefined `event_project_id` — NameError drops all events |
| 3 | LOW | consent_gate.py:376-399 | Stale project cache up to 300s after global withdrawal |
