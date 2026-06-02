# D09 Re-Audit — Config & Hardcoded Values (P5.5 Remediation)

**Audit type:** Read-only re-audit  
**Date:** 2026-06-02  
**Auditor:** Guinevere (Sisyphus-Junior)  
**Scope:** FIX 6 (C-16) — Remove dev-key fallback from auth.py, cmd_loop_start.py, cmd_loop_stop.py  
**Original audit:** `audit-reports/P5/P5-FINAL-AUDIT/D09-config-hardcoded.md`

---

## Verdict: **PASS**

All three BLOCKING findings from the original D09 audit are **RESOLVED**. The `guinevere-dev-key` fallback has been completely removed from the codebase.

---

## Finding Status Summary

| # | Original Finding | Severity | Status |
|---|---|---|---|
| F6a | Dev-key fallback in `src/core/api/auth.py` | BLOCKING | ✅ RESOLVED |
| F6b | Dev-key fallback in `src/discord/cmd_loop_start.py` | BLOCKING | ✅ RESOLVED |
| F6c | Dev-key fallback in `src/discord/cmd_loop_stop.py` | BLOCKING | ✅ RESOLVED |

---

## Grep Verification

### Check 1: `guinevere-dev-key` across all `src/` files

```
Pattern: guinevere-dev-key
Path:    src/
Result:  ZERO matches
```

✅ **PASS** — No occurrences of the legacy dev key anywhere in source.

### Check 2: `dev.key|_DEV|DEV_DEFAULT|dev-default` across all `src/` files

```
Pattern: dev.key|_DEV|DEV_DEFAULT|dev-default
Path:    src/
Result:  ZERO matches
```

✅ **PASS** — No dev-key or dev-default variable patterns remain.

---

## Per-File Evidence

### 1. `src/core/api/auth.py` (54 lines)

**Location of fix:** Lines 23–28

```python
expected = os.environ.get("GUINEVERE_API_KEY")
if not expected:
    raise RuntimeError(
        "GUINEVERE_API_KEY environment variable is required"
    )
```

**Behavior when key is not set:** Raises `RuntimeError` with a clear message. No silent fallback, no default dev key.

**Usage in FastAPI dependency** (lines 31–54): `get_api_key()` calls `verify_api_key()` and returns 401 HTTPException if the key is missing or invalid. If `GUINEVERE_API_KEY` env var is unset, the `RuntimeError` propagates as a 500 — this is intentional (configuration error, not an auth failure).

✅ **PASS** — No `_DEV_DEFAULT_KEY`, no `guinevere-dev-key`, no fallback logic.

---

### 2. `src/discord/cmd_loop_start.py` (462 lines)

**Location of fix:** Lines 344–353

```python
api_key = os.environ.get("GUINEVERE_API_KEY")
if not api_key:
    await _followup_send(
        interaction,
        content=(
            "\u26a0\ufe0f GUINEVERE_API_KEY is not set. "
            "Ask Faiz to configure it."
        ),
    )
    return
```

**Behavior when key is not set:** Sends an ephemeral warning message via Discord followup and returns early. No API call is attempted without a key. No dev-key fallback.

✅ **PASS** — None guard with graceful ephemeral error. No dev-key path.

---

### 3. `src/discord/cmd_loop_stop.py` (531 lines)

**Location of fix:** Lines 384–393

```python
api_key = os.environ.get("GUINEVERE_API_KEY")
if not api_key:
    await _followup_send(
        interaction,
        content=(
            "\u26a0\ufe0f GUINEVERE_API_KEY is not set. "
            "Ask Faiz to configure it."
        ),
    )
    return
```

**Behavior when key is not set:** Identical pattern to `cmd_loop_start.py` — ephemeral warning, early return, no dev-key fallback.

✅ **PASS** — None guard with graceful ephemeral error. No dev-key path.

---

## Remaining Hardcoded Values (Documentation, Non-Blocking)

The following hardcoded values from the original D09 catalog are still present in the audited files. These are **not blocking** — the original audit classified them as "should-fix" or "recommended," not BLOCKING.

| Value | Location | Line(s) | Original D09 Status |
|---|---|---|---|
| `API_BASE_URL = "http://localhost:8000"` | `cmd_loop_start.py` | 48 | should-fix |
| `API_BASE_URL = "http://localhost:8000"` | `cmd_loop_stop.py` | 48 | should-fix |
| `LOOPS_ENDPOINT = "/api/v1/loops"` | `cmd_loop_start.py` | 49 | should-fix |
| `LOOPS_ENDPOINT = "/api/v1/loops"` | `cmd_loop_stop.py` | 49 | should-fix |
| `WIB = timezone(timedelta(hours=7))` | Both cmd files | 36 | informational |
| `FOOTER_TEXT = "Guinevere de Baroque"` | Both cmd files | 46–47 | informational |

These would ideally be moved to environment variables (e.g., `GUINEVERE_API_BASE_URL`) but are not a security concern like the dev-key was.

---

## Summary of Changes (P5.5)

| File | Change | Impact |
|---|---|---|
| `auth.py` | Removed dev-key fallback; raises `RuntimeError` if `GUINEVERE_API_KEY` unset | Hard-fail vs. silent dev-key use |
| `cmd_loop_start.py` | Removed dev-key fallback; `None` guard sends ephemeral Discord warning | User-visible error instead of dev-key API call |
| `cmd_loop_stop.py` | Removed dev-key fallback; `None` guard sends ephemeral Discord warning | User-visible error instead of dev-key API call |

---

## Auditor Signature

- **Verdict:** PASS
- **Re-audit necessary:** No
- **Blockers remaining:** None
- **Date:** 2026-06-02
- **Auditor:** Guinevere (Sisyphus-Junior)