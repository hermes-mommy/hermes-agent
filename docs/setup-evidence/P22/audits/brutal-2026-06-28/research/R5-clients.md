# R5-clients — P22 Brutal Audit 2026-06-28

## Verdict Table

| Finding | Verdict | Concern                                      | Key file:line                                                |
|---------|---------|----------------------------------------------|--------------------------------------------------------------|
| F08     | HOLDS   | GitHub shim silent []/{} on non-200, no 429  | `adapters/_clients/github_client_shim.py:145,199,207,226,...` |
| F09     | PARTIAL | Calendar: 401-refresh OK, 429 retry MISSING; Drive: 429→ProviderError, no retry | `adapters/_clients/calendar_client.py:412-771`; `adapters/_clients/drive_client.py:288-320` |

---

## F08 — GitHub shim silently returns [] / {} on non-200 (and on every transport/parse error)

**Verdict: HOLDS**

The finding holds in its entirety. EVERY inline-REST method in `github_client_shim.py` follows an identical silent-fail pattern: log a warning, return an empty container (`[]` or `{}` or `{"…": False, "message": …}` shape), never raise. There is NO 429 handling, NO rate-limit awareness, and the only treated status is "exactly 200" (or 200/201/204 for writes).

### Global grep results on the file

| Grep term    | Hit count | Notes                                                                 |
|--------------|-----------|-----------------------------------------------------------------------|
| `429`        | 0         | No mention of HTTP 429 anywhere in the file.                          |
| `RateLimit`  | 0         | No `RateLimit*` mention anywhere in the file.                         |
| `Retry-After`| 0         | Header never read.                                                    |
| `X-RateLimit`| 0         | GitHub rate-limit headers never inspected.                            |
| `retry`      | 0         | No retry keyword.                                                     |
| `backoff`    | 0         | No backoff logic.                                                     |
| `tenacity`   | 0         | No decorative retry; delegated MCP tools have their own retry but the inline REST shim does not. |

### Per-method verification — what is returned on non-200

| Method (file:line)          | Transport error              | Non-200 status                                    | Parse error                  | Primary return shape |
|-----------------------------|------------------------------|---------------------------------------------------|------------------------------|----------------------|
| `check_auth` (83-130)       | `return False`               | `return False` (line 107-112)                     | `return False`               | `bool`               |
| `list_repos` (132-155)      | N/A (delegates MCP tool)     | N/A (delegates)                                   | N/A                          | `list[dict]` (delegated; MCP handles internally) |
| `get_file` (157-166)        | N/A (delegates MCP tool)     | N/A (delegates)                                   | N/A                          | `str`                |
| `search_code` (168-177)     | N/A (delegates MCP tool)     | N/A (delegates)                                   | N/A                          | `list[dict]`         |
| `list_issues` (179-226)     | **`return []`**  (line 199)  | **`return []`**  (line 201-207)                    | **`return []`**  (line 217)  | `list[dict]`         |
| `list_prs` (228-270)        | **`return []`**  (line 248)  | **`return []`**  (line 250-256)                    | **`return []`**  (line 266)  | `list[dict]`         |
| `create_issue` (272-281)    | N/A (delegates MCP tool)     | N/A (delegates)                                   | N/A                          | `dict`               |
| `create_pr` (283-294)       | N/A (delegates MCP tool)     | N/A (delegates)                                   | N/A                          | `dict`               |
| `get_repo` (296-336)        | **`return {}`**  (line 316)  | **`return {}`**  (line 318-324)                    | **`return {}`**  (line 334)  | `dict`               |
| `get_pr` (338-385)          | **`return {}`**  (line 363)  | **`return {}`**  (line 365-372)                    | **`return {}`**  (line 383)  | `dict`               |
| `merge_pr` (387-451)        | `return {"merged": False, …}` (421) | `return {"merged": False, …}` (423-436)  | `return {"merged": False, …}` (447) | `dict`        |
| `get_branch` (453-501)      | **`return {}`**  (line 479)  | **`return {}`**  (line 481-488)                    | **`return {}`**  (line 499)  | `dict`               |
| `delete_branch` (503-569)   | `return {"deleted": False, …}` (537) | `return {"deleted": False, …}` (541-554) | `return {"deleted": False, …}` (565) | `dict` |
| `list_releases` (573-623)   | **`return []`**  (line 603)  | **`return []`**  (line 605-611)                    | **`return []`**  (line 621)  | `list[dict]`         |
| `create_release` (625-701)  | `return {"created": False, …}` (671) | `return {"created": False, …}` (673-686) | `return {"created": False, …}` (696) | `dict` |
| `add_collaborator` (703-759)| `return {"invited": False, …}` (742) | `return {"invited": False, …}` (746-759) | (covered by same branch) | `dict` |
| `list_webhooks` (761-820)   | **`return []`**  (line 791)  | **`return []`**  (line 793-799)                    | **`return []`**  (line 809)  | `list[dict]`         |
| `create_webhook` (822-898)  | `return {"created": False, …}` (866) | `return {"created": False, …}` (868-881) | `return {"created": False, …}` (891) | `dict` |

### Verbatim excerpt — exact silent `return []` pattern in `list_issues`

```
        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.list_issues.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            return []
```

(source: `src\life_integrations\adapters\_clients\github_client_shim.py`, lines 201-207)

The same code-mould is repeated in `list_prs` (line 250-256), `list_releases` (line 605-611), `list_webhooks` (line 793-799), and the transport-error in `list_repos` (line 141-149). For `dict`-returning methods (`get_repo`, `get_pr`, `get_branch`), the silent return is `{}`:

```
        if response.status_code != 200:
            logger.warning(
                "p22.github.shim.get_repo.http_error",
                status=response.status_code,
                repo=f"{owner}/{repo}",
            )
            return {}
```

(`get_repo`, lines 318-324; mirrored at `get_pr` lines 365-372 and `get_branch` lines 481-488.)

### Status-code handling summary

- **200 (GET) / 200,201 (POST/PUT) / 204 (DELETE)**: success path.
- **Everything else**: silent `[]` / `{}` / `{"merged": False…}` / `{"created": False…}` / `{"invited": False…}` / `{"deleted": False…}` — the L2/L3 write methods carry a `message` field but the boolean flag (False) is the only signal — caller cannot distinguish 401/403/404/429/5xx by inspecting the return value without re-reading logs.

### Contradictions / mitigating evidence

- The shim docstring claims it is a "thin transport wrapper" and delegates L2 write consent to the router — the silent failure of L1 reads is *not* attributable to consent gating.
- Inline REST routes are explicitly described as "gap-fillers" because no MCP tool exists; checking `src\mcp\tools\github.py` is out of scope for this R5 audit but the delegated methods do not surface non-200 to the shim caller through any other channel.
- Health endpoint (`check_auth`) correctly returns a `bool` — but it too cannot distinguish 401 from 403 from 429 from 5xx; only status==200 produces True.

---

## F09 — Calendar/Drive: 429 retry/backoff

**Verdict: PARTIAL** — 401-refresh-retry is **PRESENT** in calendar (and in drive); however, 429 retry/backoff is **MISSING in both** — the drive client correctly raises `ProviderError` on 429 but **without any retry/backoff wrapper**, and the calendar client treats anything other than `status == 401` as a hard fail (raises `ConfigurationMissingError`) with **no 429 branch at all**.

### F09a — Calendar (401-refresh PRESENT, 429 retry MISSING)

**File:** `src\life_integrations\adapters\_clients\calendar_client.py` (lines 412-771)

#### grep on calendar_client.py

| Grep term    | Hit count | Notes                                                                                  |
|--------------|-----------|----------------------------------------------------------------------------------------|
| `429`        | 0         | No literal `429` anywhere.                                                             |
| `RateLimit`  | 0         | No `RateLimit*`.                                                                       |
| `Retry-After`| 0         | Header never read.                                                                     |
| `retry`      | 2         | Both occurrences are `_do_refresh` / "401_retry" method names (semantic retry only).   |
| `backoff`    | 0         | No backoff.                                                                            |

#### 401-refresh logic — verbatim excerpt (`list_events`, lines 438-466)

```
        except Exception as exc:
            error_type = type(exc).__name__
            status = getattr(
                getattr(exc, "resp", None), "status", None,
            )
            if status == 401:
                # Opportunistic refresh-then-retry on 401.
                try:
                    self._do_refresh()
                    self._service = self._build_service(self._credentials)
                    response = (
                        self._service.events()
                        .list(
                            calendarId=calendar_id,
                            maxResults=max_results,
                        )
                        .execute()
                    )
                except Exception as exc2:
                    self._log.warning(
                        "calendar_list_events_401_retry_failed",
                        calendar_id=calendar_id,
                        error_type=type(exc2).__name__,
                    )
                    _fail_missing(
                        "Calendar client: list_events authentication "
                        "recovery failed",
                    )
```

This exact 401-handling pattern is repeated in all CRUD methods:

- `get_event` — lines 514-551 (verbatim retry at lines 519-540)
- `create_event` — lines 587-622 (verbatim retry at lines 592-612)
- `update_event` — lines 665-703 (verbatim retry at lines 670-692)
- `delete_event` — lines 731-764 (verbatim retry at lines 736-753)
- `health` — lines 369-408 (inline retry at lines 384-401)

In every case, when status is **not** 401 (i.e. 404, 429, 5xx, anything), the client falls into the `else:` branch (e.g. lines 466-476 for `list_events`):

```
            else:
                self._log.error(
                    "calendar_list_events_failed",
                    calendar_id=calendar_id,
                    error_type=error_type,
                    status=status,
                )
                _fail_missing(
                    "Calendar client: list_events failed: "
                    f"{error_type}",
                )
```

The except is `except Exception as exc` — a 429 `HttpError` enters the `else`, which is a hard fail via `_fail_missing` raising `ConfigurationMissingError`. The Calendar client therefore REPORTS `CONFIG_MISSING` for any transient 429 — the status is logged (`status=status`) but never acted on.

#### CRUD methods that would need 429 retry wrapping

| Method           | file:line range (try block) | 401 retry (line) | 429 retry    |
|------------------|-----------------------------|------------------|--------------|
| `list_events`    | 429-437                     | 443-465          | **MISSING**  |
| `get_event`      | 505-513                     | 519-540          | **MISSING**  |
| `create_event`   | 578-586                     | 592-612          | **MISSING**  |
| `update_event`   | 655-664                     | 670-692          | **MISSING**  |
| `delete_event`   | 726-730                     | 736-753          | **MISSING**  |

### F09b — Drive (429 → `ProviderError` raise, but NO retry)

**File:** `src\life_integrations\adapters\_clients\drive_client.py`

#### grep on drive_client.py

| Grep term    | Hit count | Notes                                                                                  |
|--------------|-----------|----------------------------------------------------------------------------------------|
| `429`        | 1         | Module-level constant `_HTTP_RATE_LIMIT: int = 429` (line 92)                          |
| `RateLimit`  | 0         | No `RateLimit*` identifier in this file.                                               |
| `Retry-After`| 0         | Header never read.                                                                     |
| `rate limit` | 1         | Only string literal in the `_call_with_retry` raise (line 315).                        |
| `retry`      | 0         | As a function-body keyword the only retry is the method name `_call_with_retry`.       |
| `backoff`    | 0         | No backoff.                                                                            |

#### 429 branch — verbatim excerpt (`_call_with_retry`, lines 288-320)

```
        try:
            return request_factory().execute()
        except self._HttpError as exc:
            status = getattr(exc.resp, "status", 0)
            if status == _HTTP_UNAUTHORIZED:
                logger.info(
                    "drive.client.unauthorized_refreshing",
                    status=status,
                )
                self._refresh_credentials()
                try:
                    return request_factory().execute()
                except self._HttpError as exc2:
                    logger.warning(
                        "drive.client.unauthorized_after_refresh",
                        status=getattr(exc2.resp, "status", 0),
                    )
                    raise ConfigurationMissingError(
                        "Google Drive auth failed even after refresh"
                    ) from exc2
            if status == _HTTP_FORBIDDEN:
                raise PermissionDeniedError(
                    f"Google Drive permission denied (HTTP {status}): {exc}"
                ) from exc
            if status == _HTTP_RATE_LIMIT:
                raise ProviderError(
                    "Google Drive", status,
                    "rate limit hit",
                ) from exc
            raise ProviderError(
                "Google Drive", status,
                str(exc),
            ) from exc
```

So the drive client:
1. **Detects 429** (line 92 constant; line 312 branch).
2. **Maps 429 → `ProviderError("Google Drive", 429, "rate limit hit")`** at line 312-316.
3. **Does NOT retry / parse `Retry-After` / do exponential backoff.** The retry mechanism in `_call_with_retry` is restricted to 401 only.

#### CRUD method table — drive_client.py

| Method              | HTTP wrapper         | file:line | 401-retry | 429-retry   |
|---------------------|----------------------|-----------|-----------|-------------|
| `list_files`        | `_call_with_retry`   | 324-348   | YES       | **MISSING** |
| `get_file`          | `_call_with_retry`   | 350-361   | YES       | **MISSING** |
| `create_file`       | `_call_with_retry`   | 363-395   | YES       | **MISSING** |
| `update_file`       | `_call_with_retry`   | 397-409   | YES       | **MISSING** |
| `trash_file`        | `_call_with_retry`   | 411-424   | YES       | **MISSING** |
| `delete_file`       | `_call_with_retry`   | 426-464   | YES       | **MISSING** |
| `create_permission` | `_call_with_retry`   | 466-491   | YES       | **MISSING** |
| `health`            | `_call_with_retry`   | 493-514   | YES       | **MISSING** |

All eight methods funnel through `_call_with_retry`, so any 429 retry wrapper would only need to be added in one place.

---

## Available exception classes (`errors.py`)

**File:** `src\life_integrations\errors.py`. All exceptions inherit from `IntegrationError`. The implementer can use any of the following without importing new modules.

### Verbatim class definitions

```
class IntegrationError(Exception):
    """Base exception for all P22 integration errors."""


class ConfigurationMissingError(IntegrationError):
    """Raised when required configuration/credentials are missing.

    Integrations must report CONFIG_MISSING status, not fake success.
    """


class ConsentDeniedError(IntegrationError):
    """Raised when consent is revoked or not granted for an action."""


class HardStopBlockedError(IntegrationError):
    """Raised when HARD STOP blocks an action."""


class PermissionDeniedError(IntegrationError):
    """Raised when an action's permission tier is L4_FORBIDDEN."""


class ActionNotSupportedError(IntegrationError):
    """Raised when an adapter does not support the requested action."""


class RateLimitExceededError(IntegrationError):
    """Raised when an integration's rate limit is exceeded."""

    def __init__(self, provider: str, retry_after: int | None = None) -> None:
        self.provider = provider
        self.retry_after = retry_after
        msg = f"rate limit exceeded for {provider}"
        if retry_after:
            msg += f" (retry after {retry_after}s)"
        super().__init__(msg)


class AuthenticationError(IntegrationError):
    """Raised when authentication fails (invalid token, expired OAuth)."""


class ProviderError(IntegrationError):
    """Raised when a provider returns an error response."""

    def __init__(self, provider: str, status: int, message: str) -> None:
        self.provider = provider
        self.status = status
        self.message = message
        super().__init__(f"{provider} error {status}: {message}")


class PreDeleteSnapshotError(IntegrationError):
    """Raised when a pre-delete snapshot cannot be created.

    Destructive operations must abort if snapshot fails (no silent delete).
    """


class ChainVerificationError(IntegrationError):
    """Raised when audit chain verification fails (tamper detected)."""
```

### What is available for the implementer

| Need                                          | Class                                              | Defined line |
|-----------------------------------------------|----------------------------------------------------|--------------|
| Raise a typed rate-limit error after 429      | `RateLimitExceededError(provider, retry_after=)`   | 37-46        |
| Raise a generic provider-error                | `ProviderError(provider, status, message)`         | 53-60        |
| Raise a typed auth error after 401 (calendar) | `AuthenticationError`                              | 49-50        |
| Mark config missing (already used everywhere) | `ConfigurationMissingError`                        | 14-18        |
| Permission / HARD STOP / Consent              | `PermissionDeniedError`, `HardStopBlockedError`, `ConsentDeniedError` | 21-32 |

The wrapper for the GitHub shim should raise `RateLimitExceededError(provider="github", retry_after=<int|None>)` (or fall back to `ProviderError("github", 429, ...)` when no `Retry-After` is available) and let the upstream caller decide retry policy. The Drive client infra already maps 429 to `ProviderError`, so the fix in drive reduces to wrapping `_call_with_retry` with retry-after-respecting backoff (or having it raise `RateLimitExceededError(provider="google-drive", retry_after=…)`). The Calendar client has no 429 branch at all; the fix is to add an `elif status == 429:` that reads `Retry-After` and raises `RateLimitExceededError`.

---

## Recommended scope for the F08/F09 fix

1. **F08 (GitHub shim)** — Either (a) raise typed errors on non-200 (`RateLimitExceededError` for 429, `AuthenticationError` for 401, `ProviderError` otherwise) so callers can distinguish transient from permanent; or (b) leave the silent return shape but attach an `error_type`/`status` metadata field for observability. 18 inline-REST methods need treatment; the 6 delegated MCP methods are out of scope.
2. **F09a (Calendar)** — One `elif status == 429:` branch per CRUD method (5 methods), reading `exc._get_reason()` / header for `Retry-After` and raising `RateLimitExceededError`. Consider wrapping once in a private `_call_with_status_map()` helper analogous to drive's `_call_with_retry`.
3. **F09b (Drive)** — `_call_with_retry` already centralises the path. Two options: (a) inspect and honour `Retry-After` header before raising `ProviderError`; (b) raise `RateLimitExceededError(provider="google-drive", retry_after=…)` instead. Either way, the wrapping change is single-file.

---

## Path summary

- `src\life_integrations\adapters\_clients\github_client_shim.py` (NEW path under `adapters/_clients/` — the standalone `src\life_integrations\_clients\` referenced in the task brief does not exist in this checkout)
- `src\life_integrations\adapters\_clients\calendar_client.py` (same path correction)
- `src\life_integrations\adapters\_clients\drive_client.py` (same path correction)
- `src\life_integrations\errors.py` (correct path as given)
