# P2-019 Token / Unsafe Scan Verifier

## Scope
- `src/discord/notifications.py`
- `tests/discord/test_notifications.py`

## Checks Performed
1. Plaintext token scan in `notifications.py` and `test_notifications.py`
2. Unsafe syntax scan for `as any`, bare `except:`, and `@ts-ignore`
3. Persona-language scan in `notifications.py` for:
   - `Mommy`
   - `Darling`
   - `sayang`
   - `punishment`
   - `yandere`
   - `surveillance`
4. Mention scan for `@everyone` and `@here`
5. Hardcoded user ID scan, allowing only:
   - `os.getenv("GUINEVERE_FAIZ_MENTION")`
   - `os.getenv("FAIZ_MENTION")`
6. Exception-handler verification at line 232

## Evidence Summary

### 1) Plaintext token scan
- Scanned `src/discord/notifications.py` and `tests/discord/test_notifications.py`.
- No plaintext token value was present in either file.
- The only mention lookup in `notifications.py` is environment-based:
  - `os.getenv("GUINEVERE_FAIZ_MENTION") or os.getenv("FAIZ_MENTION")`

### 2) Unsafe syntax scan
- No `as any` found in either target file.
- No bare `except:` found in either target file.
- No `@ts-ignore` found in either target file.

### 3) Persona-language scan in `notifications.py`
- Searched for: `Mommy|Darling|sayang|punishment|yandere|surveillance`
- Result: **ZERO matches** in `src/discord/notifications.py`.
- This confirms the notification routing module remains neutral in tone.

### 4) Mention scan
- No `@everyone` or `@here` found in `src/discord/notifications.py`.
- Note: the repository contains an unrelated `@everyone` reference in `src/discord/permissions.py`, but it is outside the requested scope.

### 5) Hardcoded user ID scan
- No hardcoded user IDs found in `src/discord/notifications.py`.
- Faiz mention routing is limited to env vars only:
  - `GUINEVERE_FAIZ_MENTION`
  - `FAIZ_MENTION`

### 6) Exception handler verification
- `logger.error(...)` is used in the exception handler at line 232:
  - `logger.error("Failed to send %s alert: %s", sev, exc, exc_info=True)`
- Therefore the exception is not swallowed.

## Verdict
PASS

## Notes
- The target files are compliant with the requested token/unsafe/mention/persona checks.
- Exception handling in `send_alert(...)` logs failures with stack context via `exc_info=True`.
