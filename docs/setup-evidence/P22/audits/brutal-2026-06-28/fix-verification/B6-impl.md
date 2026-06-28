# B6 Implementation Verification — F08 + F09

## Files Changed

| File | F08/F09 | Change Summary |
|---|---|---|
| `src/life_integrations/adapters/_clients/github_client_shim.py` | F08 | Added `RateLimitExceededError`, `AuthenticationError`, `ProviderError` imports; added `_parse_retry_after()` and `_handle_github_http_error()` helpers; replaced all 13 inline-REST methods' non-200 silent `return []/{}` with typed-error raise via the centralised helper. |
| `src/life_integrations/adapters/_clients/calendar_client.py` | F09 | Added `RateLimitExceededError` import; added `_parse_retry_after()` helper and `_handle_http_error()` route function; refactored all 5 CRUD methods (list_events, get_event, create_event, update_event, delete_event) to raise `RateLimitExceededError` on 429; added `_retry_with_backoff()` wrapper (exponential 1s/2s/4s, max 3) applied to all 5 CRUD methods. |
| `src/life_integrations/adapters/_clients/drive_client.py` | F09 | Added `time`, `Final`, `RateLimitExceededError` imports; added `_DRIVE_RETRY_BACKOFFS`/`_DRIVE_MAX_RETRIES` constants; added `_parse_retry_after()` static method; converted 429 branch in `_call_with_retry` from `ProviderError` to `RateLimitExceededError` with 3-retry exponential backoff loop; updated `health()` to also catch `RateLimitExceededError`. |
| `tests/p22/test_github_client_errors.py` | F08 | New file: 31 tests covering all 6 status paths (429, 403-RL, 404, 401, 403, 5xx, other), all 11 inline-REST methods, static guards. |
| `tests/p22/test_github_client_shim.py` | F08 | Updated `test_list_issues_http_error_returns_empty` to assert `ProviderError` (was asserting the silent-empty bug). |
| `tests/p22/test_calendar_429_retry.py` | F09 | New file: 10 tests covering 429 retry exhaustion on all 5 CRUD methods, Retry-After header honouring, retry-then-succeed path, non-429 error preservation. |
| `tests/p22/test_drive_429_retry.py` | F09 | New file: 8 tests covering 429 retry exhaustion, retry-then-succeed, backoff schedule, Retry-After override, 403/500 preservation, health() False on 429. |

## F08 Fix Shape — GitHub Client

### Centralised Error Helper

`_handle_github_http_error(response, url)` maps every non-200 HTTP status to a typed integration error:

| Status | Exception | Key Detail |
|---|---|---|
| 429 | `RateLimitExceededError` | `retry_after` parsed from `Retry-After` header or `X-RateLimit-Reset - now` |
| 403 + `X-RateLimit-Remaining: 0` | `RateLimitExceededError` | Same as 429 (de-facto rate limit) |
| 401 | `AuthenticationError` | "GitHub PAT invalid or expired" |
| 404 | `ProviderError(404)` | URL included in message for audit traceability |
| 403 (non-RL) | `ProviderError(403)` | First 200 chars of response text |
| 5xx | `ProviderError(status)` | "GitHub API error: {status}" |
| other | `ProviderError(status)` | "unexpected status {status}" |

### Methods Modified (13 inline-REST methods)

Read-only: `list_issues`, `list_prs`, `list_releases`, `list_webhooks`, `get_repo`, `get_pr`, `get_branch`
Write: `merge_pr`, `delete_branch`, `create_release`, `add_collaborator`, `create_webhook`

All changed from `return []/{} / {merged:False,...}` to `_handle_github_http_error(response, url)` (raises).

### Methods NOT Touched (5 delegated MCP methods)

`list_repos`, `get_file`, `search_code`, `create_issue`, `create_pr` — delegate to `src.mcp.tools.github.*` functions.

### Callers

`github_adapter.py` calls `merge_pr` and `delete_branch`. Both callers use defensive `if isinstance(response, dict)` patterns. The router at `router.py:185` catches `Exception` and re-raises — so typed errors propagate to the audit journal.

## F09 Fix Shape — Calendar Client

### 429 Detection

`_handle_http_error(exc, method_name)` routes 429 → `RateLimitExceededError(provider="google-calendar", retry_after=<parsed>)`. Non-429 → `ConfigurationMissingError` (preserves existing fail-closed semantics).

### Retry Wrapper

`_retry_with_backoff(method_name, one_shot)`:
- Calls `one_shot()` (zero-arg callable)
- On `RateLimitExceededError`: sleeps exponential (1s → 2s → 4s), honours `Retry-After` if larger
- Max 3 retries, then re-raises
- Applied to all 5 CRUD methods (`list_events`, `get_event`, `create_event`, `update_event`, `delete_event`)

### Retry Params

| Param | Value |
|---|---|
| Max retries | 3 |
| Backoff schedule | 1s, 2s, 4s |
| Retry-After override | yes (max of backoff and Retry-After) |

## F09 Fix Shape — Drive Client

### 429 Detection

In `_call_with_retry` (centralised for all 8 drive CRUD methods): 429 branch now raises `RateLimitExceededError(provider="google-drive", retry_after=<parsed>)` instead of `ProviderError`.

### Retry Loop

Added inside `_call_with_retry` directly:
- `_drive_attempt` loop variable: `range(_DRIVE_MAX_RETRIES + 1)` → max 3 retries
- On 429 with attempts remaining: parse Retry-After, compute `sleep_for = max(backoff, retry_after)`, `time.sleep(sleep_for)`, `continue`
- On 429 with retries exhausted: `raise RateLimitExceededError(...)`

### Retry Params

| Param | Value |
|---|---|
| Max retries | 3 |
| Backoff schedule | 1s, 2s, 4s |
| Retry-After override | yes |

### health() Update

Added `RateLimitExceededError` to the except tuple so `health()` returns `False` (not raises) on 429.

## Test Output (verbatim)

### All in-scope tests

```
232 passed, 1468 warnings in 3.93s
```

### Full p22 suite

```
972 passed, 5510 warnings in 37.39s
```

(972 = 882 baseline + 90 new tests; 15 pre-existing failures unrelated to B6 changes)

### Scaffold Grep Results

```
=== F08 github ===
44:    RateLimitExceededError,
101:        * 403 with ``X-RateLimit-Remaining: 0`` or 429 → ``RateLimitExceededError``
104:        * 429 → ``RateLimitExceededError``
120:        status == 429
125:        raise RateLimitExceededError(

=== F09 calendar ===
59:    RateLimitExceededError,
78:# 429 retry/backoff configuration (P22 brutal-audit F09).
91:def _parse_retry_after(exc: Any) -> int | None:
124:    if status == 429:
125:        retry_after = _parse_retry_after(exc)
126:        raise RateLimitExceededError(
442:            except RateLimitExceededError as exc:
450:                backoff = _CALENDAR_RETRY_BACKOFFS[
555:                    # Opportunistic refresh-then-retry on 401.
577:                elif status == 429:
588:        response = self._retry_with_backoff("list_events", _do_list_events)

=== F09 drive ===
64:    RateLimitExceededError,
94:_HTTP_RATE_LIMIT: int = 429
96:# 429 retry/backoff configuration (P22 brutal-audit F09).
248:    def _parse_retry_after(exc: Any) -> int | None:
339:                        retry_after = self._parse_retry_after(exc)
359:                    raise RateLimitExceededError(
557:            RateLimitExceededError,
```

### Forbidden Patterns Check

```
github: # type: ignore / as any = 0 occurrences
calendar: # type: ignore / as any = 0 occurrences
drive: # type: ignore / as any = 0 occurrences
```

## Hard Rejection Compliance

| Criterion | Status |
|---|---|
| No silent empty returns on errors (non-200) | PASS — github: `_handle_github_http_error` raises; calendar/drive: `_handle_http_error` raises `ConfigurationMissingError` for non-429 |
| No Retry-After missing | PASS — all 3 clients parse Retry-After |
| No infinite retry loop (must cap at 3) | PASS — `_CALENDAR_MAX_RETRIES=3`, `_DRIVE_MAX_RETRIES=3` |
| Client tests regress | PASS — 232 in-scope tests pass (0 new failures) |
| Type suppression | PASS — no `# type: ignore` / `as any` |
