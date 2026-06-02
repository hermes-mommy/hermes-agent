# D03 — Security & Forbidden Patterns Audit

| Field | Value |
|---|---|
| **Auditor** | D03 Security Auditor (independent) |
| **Date** | 2026-06-02 |
| **Scope** | `src/loops/` (21 files), `src/core/api/` (3 files), `src/discord/cmd_loop_start.py`, `src/discord/cmd_loop_stop.py` |
| **Total Files Audited** | 26 |
| **Verdict** | **NEEDS REVIEW** |

---

## Executive Summary

The Agent Loop subsystem is **largely clean** from a security perspective. No hardcoded secrets, no `eval`/`exec`, no bare `except:`, and Discord commands properly enforce Faiz-only access with ephemeral responses. However, **4 findings require attention** before production deployment: a `shell=True` subprocess call with command injection risk, unauthenticated GET API endpoints, dev-key fallback without logging in Discord commands, and `Any` type usage across 5 files.

---

## Findings Summary

| # | ID | Severity | Category | File | Line | Status |
|---|---|---|---|---|---|---|
| 1 | D03-001 | **HIGH** | Command Injection | `src/loops/verify.py` | 110 | NEEDS REVIEW |
| 2 | D03-002 | **MEDIUM** | Unauthenticated Endpoints | `src/core/api/routes.py` | 47, 71 | NEEDS REVIEW |
| 3 | D03-003 | **MEDIUM** | Silent Dev-Key Fallback | `src/discord/cmd_loop_start.py`, `cmd_loop_stop.py` | 344, 384 | NEEDS REVIEW |
| 4 | D03-004 | **LOW** | `typing.cast()` Usage | `src/discord/cmd_loop_start.py`, `cmd_loop_stop.py` | 109 | NEEDS REVIEW |
| 5 | D03-005 | **LOW** | `Any` Type Usage (17 instances) | 5 files in `src/loops/` | various | NEEDS REVIEW |
| 6 | D03-006 | **LOW** | Redis Empty Password Fallback | `src/loops/cost.py` | 37, 45 | NEEDS REVIEW |
| 7 | D03-007 | **INFO** | Hardcoded API Base URL | `src/discord/cmd_loop_start.py`, `cmd_loop_stop.py` | 49 | INFO |

---

## Detailed Findings

### D03-001 — `shell=True` in subprocess (HIGH)

**File:** `src/loops/verify.py:110`
**Severity:** HIGH — Command Injection Risk

```python
proc = subprocess.run(
    command,
    shell=True,          # ← VULNERABILITY
    capture_output=True,
    text=True,
    timeout=30,
)
```

**Analysis:** The `verify_command()` method accepts an arbitrary command string and passes it to `subprocess.run()` with `shell=True`. If the `command` parameter ever originates from LLM output, user input, or any untrusted source, an attacker can inject arbitrary shell commands.

**Risk:** Remote code execution if the verification pipeline processes attacker-controlled commands.

**Recommendation:**
1. Replace `shell=True` with `shell=False` and split the command into a list using `shlex.split()`.
2. If `shell=True` is intentional (e.g., commands include pipes/redirects), implement an allowlist of permitted command prefixes.
3. Add input sanitization: reject commands containing `;`, `&&`, `||`, `|`, `$()`, backticks.

---

### D03-002 — GET Endpoints Without Authentication (MEDIUM)

**File:** `src/core/api/routes.py:47,71`
**Severity:** MEDIUM — Information Disclosure

```python
@router.get("/loops")
async def list_loops() -> dict:
    # NO AUTH — no Depends(get_api_key)
    ...

@router.get("/loops/{loop_id}", response_model=LoopResponse)
async def get_loop(loop_id: str) -> LoopResponse:
    # NO AUTH — no Depends(get_api_key)
    ...
```

**Analysis:** Two GET endpoints (`list_loops`, `get_loop`) are missing the `Depends(get_api_key)` dependency that is present on both POST endpoints (`create_loop`, `cancel_loop`). Any network-reachable client can enumerate and read loop data without authentication.

**Comparison:**
| Endpoint | Method | Auth |
|---|---|---|
| `/api/v1/loops` | GET | **NONE** |
| `/api/v1/loops` | POST | `get_api_key` ✓ |
| `/api/v1/loops/{loop_id}` | GET | **NONE** |
| `/api/v1/loops/{loop_id}/cancel` | POST | `get_api_key` ✓ |

**Risk:** Information disclosure — loop IDs, task descriptions, goals, phase status, and artifacts could be enumerated by an unauthenticated attacker. Currently mitigated by returning stub data, but the vulnerability persists once real data is wired up.

**Recommendation:** Add `_api_key: str = Depends(get_api_key)` parameter to both GET endpoints.

---

### D03-003 — Silent Dev-Key Fallback in Discord Commands (MEDIUM)

**Files:** `src/discord/cmd_loop_start.py:344`, `src/discord/cmd_loop_stop.py:384`
**Severity:** MEDIUM — Silent Insecure Fallback

```python
# cmd_loop_start.py:344
api_key = os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")

# cmd_loop_stop.py:384
api_key = os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")
```

**Analysis:** Both Discord commands silently fall back to the dev key `"guinevere-dev-key"` when `GUINEVERE_API_KEY` is not set. Unlike `auth.py` (which logs a warning), these commands produce **no warning** when using the insecure fallback.

**Contrast with `auth.py` (good pattern):**
```python
if expected is None:
    logger.warning(
        "api_key_env_missing",
        msg="GUINEVERE_API_KEY not set — falling back to dev default key",
    )
```

**Additional risk:** The dev key string `"guinevere-dev-key"` is duplicated in **3 locations** (auth.py:15, cmd_loop_start.py:344, cmd_loop_stop.py:384). If the value changes, all three must be updated — maintenance risk.

**Recommendation:**
1. Add a warning log when falling back to the dev key in both Discord commands.
2. Extract the dev key constant to a shared config module to eliminate duplication.
3. Consider raising an error in production when `GUINEVERE_API_KEY` is missing.

---

### D03-004 — `typing.cast()` Usage (LOW)

**Files:** `src/discord/cmd_loop_start.py:109`, `src/discord/cmd_loop_stop.py:109`
**Severity:** LOW — Type Safety Bypass

```python
return cast(DiscordEmbedModule, cast(object, mod))
```

**Analysis:** Both files use a double-cast pattern `cast(DiscordEmbedModule, cast(object, mod))` to coerce a dynamically imported module into a Protocol type. This bypasses static type checking at the boundary.

**Mitigating factors:**
- `typing.cast()` is a no-op at runtime (no actual type coercion).
- The pattern is necessary because `importlib.import_module()` returns `ModuleType` which cannot satisfy a `Protocol` without casting.
- The Protocol is structural (duck-typed), so the cast is truthful at runtime.

**Recommendation:** Accept as a justified exception for dynamic module imports. Document with an inline comment explaining why the cast is necessary.

---

### D03-005 — `Any` Type Usage (LOW)

**Severity:** LOW — Type Safety Weakening

| File | Import | Usage Count | Usage Pattern |
|---|---|---|---|
| `src/loops/manager.py` | `from typing import Any` | 4 | `dict[str, Any]` return types |
| `src/loops/enforcer.py` | `from typing import Any` | 2 | `dict[str, dict[str, Any]]` |
| `src/loops/guardian.py` | `from typing import Any` | 2 | `dict[str, dict[str, Any]]` |
| `src/loops/verify.py` | `from typing import Any` | 5 | `dict[str, Any]` for results |
| `src/loops/sub_agent.py` | `from typing import Any` | 4 | `dict[str, Any]`, `list[dict[str, Any]]` |

**Total: 17 `Any` usages across 5 files. 0 in `src/core/api/` and 0 in Discord command files.**

**Analysis:** All `Any` usages are in `dict[str, Any]` or `list[dict[str, Any]]` patterns representing heterogeneous data structures (state dicts, agent records, verification results). These are common in Python codebases for flexible data containers.

**Recommendation:** Consider replacing `dict[str, Any]` with typed Pydantic models or TypedDict classes where the structure is known. Lower priority — not a security vulnerability but reduces type-safety guarantees.

---

### D03-006 — Redis Empty Password Fallback (LOW)

**File:** `src/loops/cost.py:37,45`
**Severity:** LOW — Silent Unauthenticated Connection

```python
password=os.environ.get("REDIS_PASSWORD", ""),
```

**Analysis:** When `REDIS_PASSWORD` is not set, Redis connects with an empty password string. If the Redis instance requires authentication, the connection will fail. If it doesn't require authentication, data is stored unencrypted.

**Mitigating factors:**
- Redis is on `localhost:6380` (non-standard port), suggesting it's a dedicated instance.
- `username="guinevere_core"` is set, indicating ACL-based auth is expected.
- Empty string as password will fail ACL authentication, causing an explicit error rather than silent access.

**Recommendation:** Log a warning when `REDIS_PASSWORD` is empty, similar to the API key pattern in `auth.py`.

---

### D03-007 — Hardcoded API Base URL (INFO)

**Files:** `src/discord/cmd_loop_start.py:49`, `src/discord/cmd_loop_stop.py:49`
**Severity:** INFO — Configuration Hardcoding

```python
API_BASE_URL: Final[str] = "http://localhost:8000"
```

**Analysis:** The internal API URL is hardcoded to `localhost:8000`. This is not a security issue but limits deployability to different environments.

**Recommendation:** Read from an environment variable with `localhost:8000` as default.

---

## Forbidden Pattern Scan Results

### Patterns Checked — In Scope Files (26 files)

| Pattern | Matches | Severity | Notes |
|---|---|---|---|
| `# type: ignore` | **0** | — | Clean |
| `as any` | **0** | — | Clean (Python codebase) |
| `@ts-ignore` | **0** | — | Clean (Python codebase) |
| `@ts-expect-error` | **0** | — | Clean (Python codebase) |
| `eval(` | **0** | — | Clean |
| `exec(` | **0** | — | Clean |
| `os.system(` | **0** | — | Clean |
| bare `except:` | **0** | — | Clean |
| `except Exception` with empty body | **0** | — | All have logging + handling |
| `cast(` | **2** | LOW | See D03-004 |
| `shell=True` | **1** | HIGH | See D03-001 |

### Patterns Checked — Project-Wide (for reference)

| Pattern | Matches | In-Scope Matches |
|---|---|---|
| `# type: ignore` | 3 (in `src/persona/mood_persistence.py`, `src/discord/bot.py`) | 0 |
| `except Exception` (all) | 36 across 18 files | 6 (all with bodies) |
| `cast(` | 31 across 17 files | 2 |

---

## Auth Mechanism Analysis

### `hmac.compare_digest` — Timing-Safe ✓

```python
# src/core/api/auth.py:31
return hmac.compare_digest(key, expected)
```

**Assessment:** CORRECT. `hmac.compare_digest` performs a constant-time comparison that prevents timing side-channel attacks. This is the industry-standard approach for API key verification.

### Env Var Fallback Safety

| Component | Env Var | Fallback | Warning Logged |
|---|---|---|---|
| `auth.py` | `GUINEVERE_API_KEY` | `"guinevere-dev-key"` | **YES** ✓ |
| `cmd_loop_start.py` | `GUINEVERE_API_KEY` | `"guinevere-dev-key"` | **NO** ✗ |
| `cmd_loop_stop.py` | `GUINEVERE_API_KEY` | `"guinevere-dev-key"` | **NO** ✗ |
| `cost.py` | `REDIS_PASSWORD` | `""` (empty) | **NO** ✗ |

**Assessment:** The auth module itself is safe. The inconsistency in Discord commands is the concern (see D03-003).

---

## Discord Security Analysis

### is_faiz Gate

| Command | is_faiz Check | Position | Denial Response |
|---|---|---|---|
| `/loop-start` | `is_faiz_interaction()` | Before defer | `"Hanya Faiz yang bisa menggunakan Mommy."` (ephemeral) |
| `/loop-stop` | `is_faiz_interaction()` | Before defer | `"Hanya Faiz yang bisa menggunakan Mommy."` (ephemeral) |

**Assessment:** PASS. Both commands enforce Faiz-only access as the first check before any processing.

### Ephemeral Responses

| Response Type | Ephemeral | File |
|---|---|---|
| Denial message | `ephemeral=True` ✓ | Both files |
| Deferred response | `ephemeral=True` ✓ | Both files |
| Followup messages | `ephemeral=True` ✓ | Both files |
| Error messages | `ephemeral=True` ✓ | Both files |

**Assessment:** PASS. All Discord responses are ephemeral — no sensitive information is exposed to other server members.

---

## Exception Handling Analysis

### `pass` Statements (In Scope)

| File | Line | Context | Justified |
|---|---|---|---|
| `src/loops/manager.py` | 120 | `except asyncio.CancelledError: pass` | YES — standard async cancellation |
| `src/loops/manager.py` | 261 | `except asyncio.CancelledError: pass` | YES — standard async cancellation |
| `src/loops/guardian.py` | 156 | `except asyncio.CancelledError: pass` | YES — standard async cancellation |

**Assessment:** All `pass` statements are inside `except asyncio.CancelledError:` blocks, which is the standard Python pattern for graceful asyncio task cancellation. No unjustified empty `pass` found.

### `except Exception` Handling (In Scope)

| File | Line | Has Body | Action |
|---|---|---|---|
| `src/loops/scheduler.py` | 81 | YES | `logger.warning` + `raise` |
| `src/loops/scheduler.py` | 149 | YES | `logger.error` |
| `src/loops/manager.py` | 214 | YES | `logger.error` + error handling |
| `src/loops/manager.py` | 227 | YES | `logger.warning` + fallback |
| `src/discord/cmd_loop_start.py` | 385 | YES | `logger.exception` + user notification |
| `src/discord/cmd_loop_stop.py` | 454 | YES | `logger.exception` + user notification |

**Assessment:** PASS. All `except Exception` blocks have meaningful bodies with logging and/or error handling. No swallowing of exceptions.

---

## Redis Password Handling

| File | Pattern | Source | Hardcoded |
|---|---|---|---|
| `src/loops/cost.py:37` | `os.environ.get("REDIS_PASSWORD", "")` | Env var | NO ✓ |
| `src/loops/cost.py:45` | `os.environ.get("REDIS_PASSWORD", "")` | Env var | NO ✓ |

**Assessment:** No hardcoded Redis passwords. Passwords are read from environment variables. The empty-string fallback is acceptable because it will fail Redis ACL auth if a password is required.

---

## Hardcoded Secrets Scan

| Search Term | In-Scope Matches | Verdict |
|---|---|---|
| API keys | `"guinevere-dev-key"` (3 locations) | Dev fallback, not a real secret |
| Passwords | None hardcoded | CLEAN |
| Tokens | None hardcoded | CLEAN |
| Database credentials | None hardcoded | CLEAN |
| SOPS/age keys | None | CLEAN |

**Assessment:** No real secrets are hardcoded. The dev key `"guinevere-dev-key"` is a known development placeholder, not a production credential. However, it should never be used in production without the `GUINEVERE_API_KEY` env var being set.

---

## Overall Verdict

### **NEEDS REVIEW**

The codebase is fundamentally sound with no critical security vulnerabilities. The findings are:

| Severity | Count | Action Required |
|---|---|---|
| HIGH | 1 | `shell=True` command injection risk — **fix before production** |
| MEDIUM | 2 | Unauthenticated GET endpoints + silent dev-key fallback — **fix before production** |
| LOW | 3 | `cast()`, `Any` types, Redis fallback — **improve when convenient** |
| INFO | 1 | Hardcoded API URL — **cosmetic improvement** |

### Priority Fix Order

1. **D03-001 (HIGH):** Replace `shell=True` with `shell=False` + `shlex.split()` or implement command allowlist.
2. **D03-002 (MEDIUM):** Add `Depends(get_api_key)` to both GET endpoints.
3. **D03-003 (MEDIUM):** Add warning logs to Discord command dev-key fallbacks; extract shared constant.
4. **D03-004 to D03-007 (LOW/INFO):** Address during routine maintenance.

---

## Methodology

1. Read all 26 files in scope completely.
2. Ran `grep` searches across the entire `src/` directory for each forbidden pattern.
3. Filtered results to in-scope files only.
4. Analyzed authentication mechanisms, exception handling, and secret management patterns.
5. Cross-referenced findings against AGENTS.md BLOCKING rules and anti-pattern catalog.
6. Classified each finding by severity (HIGH/MEDIUM/LOW/INFO) per OWASP-inspired scale.

---

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-02 | D03 Security Auditor | Initial audit — 7 findings, verdict NEEDS REVIEW |
