# P2-021 LSP/static verifier

**Verdict:** FAIL

**Report path:** `docs/setup-evidence/P2/STEP-P2-021/verifiers/lsp-static-verifier.md`

## Scope verified
- `src/discord/gotify_fallback.py`
- `tests/discord/test_gotify_fallback.py`

## Checks performed

1. `python -m py_compile src/discord/gotify_fallback.py tests/discord/test_gotify_fallback.py`
   - **PASS**
2. `pytest tests/discord/test_gotify_fallback.py -v`
   - **PASS**
   - Collected **12 tests**; all **12 passed**
3. `pip install -e .` then `python -c "from src.discord.gotify_fallback import build_gotify_payload, get_priority, send_fallback; print('import OK')"`
   - **FAIL** on `pip install -e .`
   - Editable install failed during Hatchling metadata generation with:
     - `AttributeError: module 'hatchling.build' has no attribute 'prepare_metadata_for_build_editable'`
     - `ValueError: Unable to determine which files to ship inside the wheel...`
   - Direct import check was executed separately and printed `import OK`
4. LSP diagnostics on both files
   - `tests/discord/test_gotify_fallback.py`: **0 errors**
   - `src/discord/gotify_fallback.py`: **1 error**
     - `reportMissingTypeArgument` at line 36:73 for `dict`
5. Static contract checks from source/tests
   - `build_gotify_payload` returns a plain `dict`; **typed dict return not confirmed** from static diagnostics
   - `get_priority` mapping confirmed by tests and source:
     - `SEV0 -> 10`
     - `SEV1 -> 7`
     - `SEV2 -> 5`
     - `SEV3 -> 3`
     - `SEV4 -> 1`
     - unknown -> `0`
   - `send_fallback` confirmed as `async`, uses `httpx.AsyncClient`, and returns `bool`
   - `send_fallback` separately catches `httpx.TimeoutException`, `httpx.ConnectError`, and generic `Exception`

## Summary
- Runtime/static verification is **not fully clean** because `src/discord/gotify_fallback.py` has 1 LSP error and `pip install -e .` fails in this environment.
- Test suite for the target file is solid: **12/12 passing**.
- Direct import of the module succeeds.

## Notes
- The editable-install failure appears to be a packaging/backend configuration issue, not a failure in the target module or its tests.
- Because the requested criteria include zero LSP errors and successful editable install, the overall verdict is **FAIL**.
