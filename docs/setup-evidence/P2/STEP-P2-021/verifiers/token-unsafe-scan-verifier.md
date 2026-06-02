# P2-021 Token / Unsafe Scan Verifier

**Verdict:** FAIL

**Scope:**
- `src/discord/gotify_fallback.py`
- `src/discord/notifications.py`
- `tests/discord/test_gotify_fallback.py`

## Checks

1. **No plaintext `GOTIFY_APP_TOKEN` value — only `os.environ.get("GOTIFY_APP_TOKEN", "")`**
   - PASS
   - `src/discord/gotify_fallback.py:49` uses `os.environ.get("GOTIFY_APP_TOKEN", "")`.

2. **No plaintext `GOTIFY_ADMIN_PASSWORD` value**
   - PASS
   - No occurrence found in the scanned files.

3. **No hardcoded Discord bot tokens**
   - PASS
   - No bot token literals found in the scanned files.

4. **No `type: ignore` or `@ts-ignore`**
   - PASS
   - No matches in the scanned files.

5. **No bare `except:` clause without logging**
   - PASS
   - No bare `except:` clause found.

6. **No empty `except/finally`**
   - PASS
   - No empty `except` or `finally` blocks found.

7. **No bare `raise` without context**
   - PASS
   - No bare `raise` statement found in the scanned files.

8. **`send_fallback` is fail-soft — returns `False` on all error paths, never raises**
   - PASS
   - `src/discord/gotify_fallback.py:47-83` returns `False` for token missing, HTTP failure, timeout, connection error, and generic exception.

9. **`notifications.py` wire-in: lazy import inside `send_alert()`, not at module level**
   - FAIL
   - `src/discord/notifications.py:240` has a module-level `import discord  # noqa: E402  # isort: skip`, which violates the lazy-import-only expectation for the wire-in.

## Notes

- The Gotify fallback implementation itself is fail-soft and matches the required environment-variable access pattern.
- The notification routing file still has a module-level Discord import, so the overall verifier result is **FAIL**.
- No issues were observed in the test file regarding the requested token/unsafe patterns.

## Files Reviewed

- `src/discord/gotify_fallback.py`
- `src/discord/notifications.py`
- `tests/discord/test_gotify_fallback.py`
