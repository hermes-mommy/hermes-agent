# P3-005 Auditor Gate — Embedding Pipeline (FRESH AUDIT)

| Field | Value |
|---|---|
| File audited | `src/memory/embeddings.py` |
| Module exports | `src/memory/__init__.py` |
| Verification script | `docs/setup-evidence/P3/STEP-P3-005/verify_embeddings.py` |
| Verification output | `docs/setup-evidence/P3/STEP-P3-005/verification-output.txt` |
| Verification report | `docs/setup-evidence/P3/STEP-P3-005/verification.md` |
| Consent gate | `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` |
| Batch plan | `docs/setup-evidence/P3/batch-plan-004-010.md` |
| Auditor | Independent auditor (fresh — this overwrites stale report from prior iteration) |
| Date | 2026-06-02 |
| Verdict | **PASS** |

---

## Why This Is a Fresh Audit

The prior auditor report in this file was stale. It referenced:

| Stale Claim | Current Reality |
|---|---|
| `import structlog` / `structlog.get_logger()` | Stdlib `_Logger` wrapper over `logging.getLogger()` — no structlog import |
| `@retry` decorator from tenacity | Manual `_call_with_retry()` / `_acall_with_retry()` loops with exponential backoff |
| `_call_embedding_api` / `_acall_embedding_api` | These method names no longer exist; current method chain is `_do_sync_request()` / `_do_async_request()` through `_call_with_retry()` |
| "55 tests" / "55/55 verification suite" | Verification suite has exactly **50 tests**, confirmed 50/50 PASS |
| `reportMissingImports` for structlog/tenacity (2 errors) | Current LSP diagnostics: **0 errors, 0 warnings on all files** |

This report overwrites the stale version with findings from current code, diagnostics, and evidence.

---

## Check Points

### CP-01: EmbeddingService exists with sync/async API

**PASS** — `EmbeddingService` class at line ~445 (approx) with:
- `embed()` sync single embedding
- `embed_batch()` sync batch embedding
- `aembed()` async single embedding
- `aembed_batch()` async batch embedding
- All public methods flow through `prepare_embedding_text()` for privacy preprocessing

### CP-02: 9Router-native client — no OpenAI SDK

**PASS** — Confirmed by grep: zero occurrences of `import openai`, `from openai`, or any OpenAI SDK reference in `src/memory/`. Only `httpx` for HTTP. Module docstring explicitly states "No direct OpenAI SDK usage per ADR-009."

### CP-03: Privacy guards — Classification-aware preprocessing

**PASS** — `prepare_embedding_text()` in `embeddings.py` implements:

| Classification | Behavior | Verified |
|---|---|---|
| **Critical** | Raises `CriticalEmbeddingError` (fail closed) unless explicit `sanitized_summary` provided | Verification test "Critical raw text rejected" PASS |
| **Critical + summary** | Uses sanitized_summary text, sets `is_sanitized_summary=True` | Verification test PASS |
| **Critical + empty summary** | Still rejected (empty/whitespace) | Verification test PASS |
| **Confidential** | Same redaction as Restricted | Verification test PASS |
| **Restricted** | `_redact_sensitive()` applied: emails, API keys (sk-*, sk-proj-*), bearer tokens, phones, URL credentials, long hex hashes | Verification tests PASS (email and API key both redacted) |
| **Public/Internal** | No redaction | Verification tests PASS |
| **Unknown** | Raises `ValueError` | Verification test PASS |

Redaction is applied _after_ truncation, ensuring no sensitive data leaks past the `MAX_INPUT_CHARS` limit.

### CP-04: Dimension validation (1536)

**PASS** — `_validate_vector()` checks `len(vector) == expected_dimension` (default 1536) and raises `DimensionMismatchError` on mismatch. Applied in both sync and async paths. Verification confirms 384-dim vector raises error.

### CP-05: Retry logic — manual loop (no tenacity)

**PASS** — Uses `_call_with_retry()` and `_acall_with_retry()`:
- Exponential backoff: 1s → 2s → 4s → 8s → 16s → max(30s) for 6 attempts
- Retry on: `EmbeddingRateLimitError` (429), `EmbeddingServerError` (5xx), `httpx.TimeoutException`, `httpx.ConnectError`
- Non-retryable errors (4xx other than 429) raise `EmbeddingAPIError` outside retry scope
- `EmbeddingConfigurationError` (no API key) is non-retryable
- Async variant uses same pattern with `asyncio.sleep()`

### CP-06: No secrets in source code

**PASS** — Confirmed by targeted secret scan:
- **`sk-or-v1`**: Zero matches in `src/` files
- **`sk-proj-`**: Only in `_REDACTION_PATTERNS` regex literal at line 161 (for redacting keys) — documented acceptable use
- **`OPENROUTER_API_KEY`**: Only as a string literal in `api_key_env_vars` tuple (environment variable name reference)
- API key loaded from `GUINEVERE_9ROUTER_API_KEY` (primary) or `OPENROUTER_API_KEY` (fallback) env vars
- `_api_key` dataclass field: `repr=False, compare=False` — never serialised
- No hardcoded fallback keys; if no env var found, `_api_key` stays `""` and raises `EmbeddingConfigurationError`
- Verification script uses fake key `test-key-redacted` which is deleted after test: `del os.environ["GUINEVERE_9ROUTER_API_KEY"]`
- **`verification.md` reference**: `sk-or-v1` appears only in the security scan section stating "no `sk-or-v1` prefix patterns found" — documentation reference, not a secret

### CP-07: Structlog-free logging (stdlib `_Logger`)

**PASS** — Uses `_Logger` class wrapping `logging.getLogger()`:
- `_Logger.bind()` returns new `_Logger` with merged fields
- `_Logger.info()`, `_Logger.warning()` emit through stdlib
- Logged fields: model, expected_dimension, classification, redaction_applied, char_count, batch_size
- Never logs: raw text, vector values, secrets, API keys

Confirmed `structlog` only appears in comments/docstrings explaining the wrapper approach.

### CP-08: Text truncation to 8000 chars

**PASS** — `_truncate_text()` caps at `MAX_INPUT_CHARS = 8000`. Called in `prepare_embedding_text()` before redaction. Verification confirms: 10000 → 8000 chars; short text unchanged.

### CP-09: Module re-exports via `__init__.py`

**PASS** — `src/memory/__init__.py` re-exports all 20 public symbols:
- 5 classification constants (`PUBLIC`, `INTERNAL`, `RESTRICTED`, `CONFIDENTIAL`, `CRITICAL`)
- 7 error classes (`CriticalEmbeddingError`, `DimensionMismatchError`, `EmbeddingAPIError`, `EmbeddingConfigurationError`, `EmbeddingError`, `EmbeddingRateLimitError`, `EmbeddingServerError`, `RestrictedRedactionError`)
- `EmbeddingConfig`, `EmbeddingService`, `PreparedText`, `prepare_embedding_text`
- 4 convenience functions: `embed`, `embed_batch`, `aembed`, `aembed_batch`

`__all__` list matches exports exactly. No stale or missing exports.

### CP-10: Strict typing — no anti-patterns

**PASS** — Confirmed by grep on both `embeddings.py` and `__init__.py`:
- `typing.Any`: 0 occurrences
- `# type: ignore`: 0 occurrences
- `@ts-ignore` / `@ts-expect-error`: 0 occurrences (Python code, expected)
- Bare `except:`: 0 occurrences
- JSON response typed as `dict[str, object]` with `isinstance` runtime guards — correct pattern
- `cast()` used for pyright type narrowing; runtime `isinstance` validates

### CP-11: LSP diagnostics clean

**PASS** — All files checked:

| File | Errors | Warnings |
|---|---|---|
| `src/memory/embeddings.py` | **0** | **0** |
| `src/memory/__init__.py` | **0** | **0** |
| `docs/setup-evidence/P3/STEP-P3-005/verify_embeddings.py` | **0** | **0** |
| `docs/setup-evidence/P3/STEP-P3-005/verification.md` | **0** | **0** |

### CP-12: Verification suite — 50/50 PASS

**PASS** — `verification-output.txt` confirms:
```
RESULTS: 50 passed, 0 failed
```

All 10 test sections PASS:
1. Module Imports — 4 PASS
2. Classification Constants — 7 PASS
3. Error Hierarchy — 8 PASS
4. Privacy Guards — 15 PASS
5. EmbeddingService mocked 1536-dim — 3 PASS
6. Dimension Mismatch — 1 PASS
7. Batch Embedding — 3 PASS
8. Convenience Functions — 2 PASS
9. Text Truncation — 2 PASS
10. No Secrets in Output — 5 PASS

### CP-13: Verification uses `httpx.MockTransport` (no `unittest.mock`)

**PASS** — `verify_embeddings.py` uses `httpx.MockTransport` for deterministic mock responses:
```python
def make_mock_client(response: httpx.Response) -> httpx.Client:
    def handler(request: httpx.Request) -> httpx.Response:
        _ = request
        return response
    return httpx.Client(transport=httpx.MockTransport(handler))
```

No `from unittest.mock import ...` — avoids `reportAny` diagnostics.

### CP-14: Consent gate documented and approved

**PASS** — `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` exists with:
- Explicit Faiz approval: "Aku approve Guinevere P3-005 pakai text-embedding-3-small via 9Router, dengan privacy guards: no raw Critical memory external, Restricted di-redact."
- Guardrails documented: 8 conditions matching current implementation
- Date: 2026-06-02 12:34:22 Asia/Bangkok
- No API key stored in file

### CP-15: No P3-006 scope creep

**PASS** — No DB writes, migrations, HNSW operations, or index queries in this step. Pure code file creation (`embeddings.py`, `__init__.py`) with mock-based verification.

### CP-16: No stale references in documentation

**PASS** — `verification.md` correctly references:
- Stdlib `_Logger` (not structlog)
- Manual retry loops (not tenacity)
- 50 tests (not 55)
- `httpx.MockTransport` verification
- 0 diagnostics (not `reportMissingImports`)

---

## Detailed Verification Evidence

### Evidence Paths

| Artifact | Path | Status |
|---|---|---|
| Source implementation | `src/memory/embeddings.py` | ~580 lines, current |
| Module exports | `src/memory/__init__.py` | 62 lines, all 20 symbols re-exported |
| Verification script | `docs/setup-evidence/P3/STEP-P3-005/verify_embeddings.py` | ~370 lines, uses `httpx.MockTransport` |
| Verification output | `docs/setup-evidence/P3/STEP-P3-005/verification-output.txt` | 50/50 PASS |
| Verification report | `docs/setup-evidence/P3/STEP-P3-005/verification.md` | Current, no stale claims |
| Consent gate | `docs/setup-evidence/P3/research/faiz-consent-embedding-privacy.md` | APPROVED |
| Batch plan | `docs/setup-evidence/P3/batch-plan-004-010.md` | Binding decisions documented |

### LSP Diagnostics Summary

```
src/memory/embeddings.py:         0 errors, 0 warnings
src/memory/__init__.py:           0 errors, 0 warnings
verify_embeddings.py:             0 errors, 0 warnings
verification.md:                  0 errors, 0 warnings
```

### Secret Scan Summary

| Pattern | src/ match | docs/ match | Verdict |
|---|---|---|---|
| `sk-or-v1` | 0 | 0 in source files; 1 in verification.md (documentation ref only) | PASS |
| `sk-proj-` + 20+ chars (real key) | 0 | 0 (test string in verify script is `sk-proj-test-key-for-redaction-check`, not a real key) | PASS |
| `OPENROUTER_API_KEY` as string literal | 1 (env var name reference) | — | PASS (acceptable) |
| API key in code | 0 | 0 | PASS |
| API key in config repr | 0 | 0 | PASS (confirmed `_api_key repr=False`) |

### Anti-Pattern Scan Summary

| Anti-pattern | Occurrences | Verdict |
|---|---|---|
| `# type: ignore` | 0 | PASS |
| `@ts-ignore` / `@ts-expect-error` | 0 | PASS (Python code) |
| `as any` or equivalent Python `typing.Any` | 0 | PASS |
| Bare `except:` | 0 | PASS |
| `asyncio` imported at module level | No — `import asyncio` inside `_async_sleep()` | PASS |
| Empty catch blocks | 0 | PASS |
| Deleted/skipped tests | No — 50/50 all PASS | PASS |

### Boundary Compliance

| Boundary | Check | Result |
|---|---|---|
| No persona drift | No persona changes in this step | PASS |
| No consent violation | Consent explicitly APPROVED; guardrails enforced in code | PASS |
| No Y6 | Y4 baseline, Y5 ceiling preserved | PASS |
| No HARD STOP bypass | Safe word remains available | PASS |
| No surveillance overreach | No surveillance data processed | PASS |
| No critical data leak | Critical fails closed; Restricted/Confidential redacted | PASS |
| No secrets exposed | Environment-only API key; `repr=False` | PASS |
| No direct OpenAI | Pure httpx, no OpenAI SDK import | PASS |
| No DB changes / P3-006 scope | Pure code-only step | PASS |

---

## Non-Blocking Observations

1. **`RestrictedRedactionError` defined but never raised** — The error class exists in the hierarchy (at module level) but is never raised. The redaction function handles gracefully by returning `(text, applied)` tuple. Not a defect; could be removed or implemented in future iteration.

2. **Async path creates new `httpx.AsyncClient` per call** — `_do_async_request()` uses `async with httpx.AsyncClient(...)` creating a fresh client per request. No connection pooling for async calls. Sync path reuses `_http_client` instance. Not a correctness issue; acceptable for P3-005 scope.

3. **`sk-proj-` redaction regex literal in source** — The pattern `(sk-proj-)[a-zA-Z0-9_-]{20,}` appears in `_REDACTION_PATTERNS`. This is a **redaction regex**, not a real key. It is documented in `verification.md` as acceptable. No action required.

---

## Final Verdict

**PASS** — All 16 check points pass. Current implementation is correct, privacy-safe, properly typed, well-structured, and verified.

| Summary | Count |
|---|---|
| Check points passed | 16/16 |
| Verification tests | 50/50 PASS |
| LSP errors | 0 |
| LSP warnings | 0 |
| Secret exposure | 0 |
| Anti-pattern violations | 0 |
| Stale claims in this report | 0 (fresh audit) |

**Step P3-005 is ready for the parent orchestrator to update trackers and proceed to P3-006.**

---

*Report written by independent auditor. Overwrites stale prior audit that referenced structlog imports, tenacity @retry decorator, and 55-test suite — none of which exist in the current codebase.*