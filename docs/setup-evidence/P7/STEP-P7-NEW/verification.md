# STEP-P7-NEW Verification — SOPS Secrets Helper for Surveillance HMAC

| Field | Value |
|---|---|
| Step ID | P7-NEW |
| Task | Create `src/surveillance/secrets.py` with `get_hmac_secret()` + tests |
| Date | 2026-06-02 |
| Status | **PASS** |

## What Was Done

Created a new module `src/surveillance/secrets.py` that provides a `get_hmac_secret() -> str` function for loading the surveillance HMAC secret at runtime. The module supports two resolution strategies (environment variable for dev/CI, SOPS decryption for production) with module-level singleton caching.

Created comprehensive unit tests in `tests/surveillance/test_secrets.py` covering all resolution paths, caching behavior, and error conditions. All 16 tests pass.

## Files Changed

| File | Action | Description |
|---|---|---|
| `src/surveillance/secrets.py` | Created | `get_hmac_secret()` with env var fallback, SOPS subprocess decryption, caching, clear errors |
| `tests/surveillance/test_secrets.py` | Created | 16 unit tests across 4 test classes |
| `docs/setup-evidence/P7/STEP-P7-NEW/verification.md` | Created | This file |
| `docs/setup-evidence/P7/STEP-P7-NEW/auditor-gate.md` | Created | Auditor gate placeholder |

## Validation Results

### Test Execution

```
python -m pytest tests/surveillance/test_secrets.py -v
16 passed, 1 warning in 0.30s
```

### LSP Diagnostics

- `src/surveillance/secrets.py`: 0 errors, 0 warnings
- `tests/surveillance/test_secrets.py`: 0 errors, 0 warnings

## Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| `get_hmac_secret() -> str` function exists | PASS | `src/surveillance/secrets.py` line 82 |
| Environment variable fallback (`SURVEILLANCE_HMAC_SECRET`) | PASS | Lines 93-97, tests `TestEnvVarFallback` (3 tests) |
| SOPS subprocess decryption for production | PASS | `_decrypt_sops_secret()` lines 38-79, tests `TestSopsDecryption` (8 tests) |
| Result caching (no decrypt on every call) | PASS | Module-level `_cached_secret` singleton, tests `TestCaching` (3 tests) |
| Clear error message when secret unavailable | PASS | `RuntimeError` / `FileNotFoundError` with descriptive messages, tests `TestNoSecretAvailable` (2 tests) |
| `structlog.get_logger()` for logging | PASS | Line 17: `logger = structlog.get_logger()` |
| No `# type: ignore` or type suppression | PASS | Zero `# type: ignore` in both files |
| No `logging.getLogger` | PASS | Only `structlog.get_logger()` used |
| No empty except blocks | PASS | All exception handling uses specific exception types with `from exc` |
| No hardcoded secret values in tests | PASS | Tests use mock/fake values, no real secrets |
| `src/surveillance/__init__.py` not modified | PASS | Unchanged |
| `secrets/guinevere-secrets.yaml` not modified | PASS | Unchanged |
| Tests pass with mocked SOPS | PASS | 16/16 pass |

## Design Decisions

1. **Module-level singleton over `functools.lru_cache`**: Simpler, more testable (explicit `_clear_cache()` function), no decorator overhead.

2. **`subprocess.run` with `check=False`**: Explicit return code checking rather than relying on exception propagation. Produces better error messages with stderr content.

3. **Resolution order: cache > env > SOPS**: Matches the task specification. Env var check is O(1) dict lookup; SOPS decryption is an expensive subprocess call.

4. **Path resolution via `Path(__file__).resolve().parents[2]`**: Robust path to `secrets/guinevere-secrets.yaml` that works regardless of working directory.

## Boundary Compliance

- No plaintext secret values stored in code
- No secrets committed to artifacts
- No surveillance data exposure
- No consent boundary changes
- No persona drift

## Rollback / Re-run Safety

- All files are new; rollback = delete the 4 files listed above
- Tests are idempotent (autouse fixture clears cache before/after each test)
- No database, migration, or state changes

## Auditor Gate

See `auditor-gate.md` — PENDING.
