# STEP-FIX-06: Remove "guinevere-dev-key" Hardcoded Fallbacks

**Date:** 2026-06-02
**Status:** PASS
**Scope:** Security hardening — eliminate hardcoded API key fallbacks

## What Was Done

Removed all `"guinevere-dev-key"` hardcoded fallback values from 3 files. The API key must now come exclusively from the `GUINEVERE_API_KEY` environment variable.

### Changes by File

| File | Change |
|---|---|
| `src/core/api/auth.py` | Removed `_DEV_DEFAULT_KEY` constant and fallback logic. `verify_api_key()` now raises `RuntimeError` if `GUINEVERE_API_KEY` is not set. |
| `src/discord/cmd_loop_start.py` | Removed fallback default from `os.environ.get()`. Added early return with user-facing error message if key is missing. |
| `src/discord/cmd_loop_stop.py` | Same pattern as cmd_loop_start.py — removed fallback, added early return with error message. |

### auth.py Detail

- Removed: `_DEV_DEFAULT_KEY: str = "guinevere-dev-key"` (was line 15)
- Removed: Warning log + fallback to `_DEV_DEFAULT_KEY` when env var missing
- Added: `raise RuntimeError("GUINEVERE_API_KEY environment variable is required")` when env var is falsy
- Preserved: `hmac.compare_digest` comparison, `API_KEY_HEADER`, `get_api_key` FastAPI dependency

### cmd_loop_start.py Detail (line 344)

- Before: `api_key = os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")`
- After: `api_key = os.environ.get("GUINEVERE_API_KEY")` + guard that sends ephemeral error via `_followup_send` and returns early

### cmd_loop_stop.py Detail (line 384)

- Before: `api_key = os.environ.get("GUINEVERE_API_KEY", "guinevere-dev-key")`
- After: Same guard pattern as cmd_loop_start.py

## Validation Results

| Check | Result |
|---|---|
| `grep -rn 'guinevere-dev-key' src/` | **0 matches** |
| LSP diagnostics auth.py | Pre-existing warnings only (import resolution, Any types) — no new issues |
| LSP diagnostics cmd_loop_start.py | Pre-existing warnings only — no new issues |
| LSP diagnostics cmd_loop_stop.py | Pre-existing warnings only — no new issues |
| No method signatures changed | Verified |
| hmac.compare_digest preserved | Verified |
| X-Guinevere-API-Key header preserved | Verified |
| is_faiz gate preserved | Verified |
| Error embed pattern matches existing code | Verified (uses `_followup_send` with `content=`, same as all other error handlers) |

## Evidence Artifacts

- This file: `evidence/phase-5.5/STEP-FIX-06/verification.md`

## Boundary Compliance

- No secrets committed
- No type safety suppression (`as any`, `# type: ignore`)
- No bare except clauses added
- No existing behavior changed beyond removing the dev key fallback
- `_followup_send` already sends ephemeral=True by default

## Files Changed

| File | Lines Changed |
|---|---|
| `src/core/api/auth.py` | 62 → 54 lines (removed constant + simplified function) |
| `src/discord/cmd_loop_start.py` | 1 line replaced with 9-line guard block |
| `src/discord/cmd_loop_stop.py` | 1 line replaced with 9-line guard block |

## Rollback

Revert the 3 edits. The old code is recoverable from git history.
