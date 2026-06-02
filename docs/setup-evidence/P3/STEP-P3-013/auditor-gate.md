# Auditor Gate — STEP-P3-013 Do-Not-Recall Hardening/API

## Verdict

**PASS** ✅

---

## Scope

Independent audit of STEP-P3-013 implementation (DNR hardening/API) against:
- Batch plan `docs/setup-evidence/P3/batch-plan-011-015.md` §P3-013
- Verification evidence `docs/setup-evidence/P3/STEP-P3-013/verification.md`
- Source: `src/memory/dnr.py`, `src/memory/__init__.py`, `tests/memory/test_dnr.py`
- DNR/filter portions of `src/memory/read_pipeline.py`

---

## Auditor Checks

### 1. DNR Mutation Authorization

**Result: PASS** ✅

- `_AUTHORIZED_PRINCIPALS = frozenset({"guinevere_core"})` at `dnr.py:113`.
- `_check_authorized(principal)` called **before** any mutation in both `mark_memory_dnr` (line 214) and `unmark_memory_dnr` (line 300).
- 5 unauthorized principals tested via `pytest.mark.parametrize`: `guinevere_subagent`, `default`, `unknown`, `faiz`, `""` — all raise `DNRAuthorizationError`.
- Fail-closed: no mutation, no audit event emitted for unauthorized callers.

### 2. Metadata-Only Audit/Log Behavior

**Result: PASS** ✅

- `_emit_audit_event()` (line 132) stores only metadata in `event_payload`:
  - `episode_id` (UUID string)
  - `event` (event type constant)
  - `principal`
  - `reason_hash` (SHA-256 first 32 hex chars)
  - `reason_length` (integer)
  - `occurred_at` (ISO timestamp)
- Raw `reason` string is **never** written to audit payload.
- Logger `extra` dict uses `reason_hash` only (16-char prefix at line 253, 341).
- Test `TestNoRawContentInLogsAndEvents` (lines 538–585) asserts:
  - `"raw_content"` not in payload string
  - `"reason"` key not present in payload
  - Raw reason text not in payload string
  - Logger extra dict does not contain raw reason text

### 3. DNR Query-Level Filters — All Three Builders

**Result: PASS** ✅

- **`build_vector_query`** (`read_pipeline.py:407-408`): `if exclude_dnr: stmt = stmt.where(Episodes.do_not_recall.is_(False))`
- **`build_fts_query`** (`read_pipeline.py:433-434`): same pattern.
- **`build_recency_query`** (`read_pipeline.py:456-457`): same pattern.
- **`recall_memories`** default: `exclude_dnr: bool = True` (line 611).
- Tests `TestQueryBuildersPreserveDNR` (4 tests) verify `do_not_recall IS false` in SQL output when `exclude_dnr=True`, absent when `False`.

### 4. Pre-Injection Guard — Fail-Closed

**Result: PASS** ✅

- `verify_recall_results_dnr_free()` (line 385) checks:
  - `dnr_flag is True` (bool, line 406)
  - `dnr_flag == "True" or dnr_flag == "true"` (string variants, line 413)
- Tests verify:
  - Clean results pass (5 entries with `False` or absent flag)
  - Empty results pass
  - `do_not_recall=True` raises `DNRViolationError` with index and ID
  - `do_not_recall="true"` raises `DNRViolationError` with `"string flag"` message
  - DNR entry at middle index correctly identified

### 5. No Type Suppressions, Empty Catches, Skipped/Deleted Tests

**Result: PASS** ✅

- **Grep on `dnr.py`**: zero `# type: ignore`, zero `cast()`, zero empty `except:`, zero `Any` usage.
- **Grep on `test_dnr.py`**: zero `# type: ignore`, zero empty `except:`, zero tests skipped.
- **LSP diagnostics `dnr.py`**: 0 errors, 0 warnings — clean.
- **LSP diagnostics `__init__.py`**: 0 diagnostics — clean.
- **LSP diagnostics `test_dnr.py`**: 1 pre-existing error (`pytest` import unresolved — environment issue, tests run correctly). No type suppressions remain (parent removed them during cleaning).

### 6. No Schema/Migration/Dependency Changes

**Result: PASS** ✅

- No model columns or migrations added. Reuses existing `Episodes.do_not_recall` column.
- No dependency changes (no new requirements).
- No live service/resource changes.
- All tests use `FakeDNRSession` — no DB, no network.
- `RecencyConfig`, `RRF_K`, `VECTOR_WEIGHT`, `FTS_WEIGHT` etc. from P3-011 unaffected.

### 7. Verification and Test Results (Auditor Witnessed)

**Focused tests** (32/32):
```
tests/memory/test_dnr.py ...................... 32 passed in 1.33s
```
1 pre-existing `pytest_asyncio` deprecation warning only.

**Regression** (93/93):
```
test_read_pipeline_hybrid.py .... 43 passed
test_prompt_context_injection.py. 18 passed
test_dnr.py ...................... 32 passed
====================================== 93 passed in 1.67s
```
1 pre-existing `pytest_asyncio` deprecation warning only. No regressions.

### 8. Export Completeness

**Result: PASS** ✅

Symbol alignment between `dnr.py::__all__`, `__init__.py` imports, and `__init__.py::__all__`:

| Symbol | `dnr.py::__all__` | `__init__.py` import | `__init__.py::__all__` |
|---|---|---|---|
| `DNRAuthorizationError` | ✅ | ✅ | ✅ |
| `DNRStateError` | ✅ | ✅ | ✅ |
| `DNRViolationError` | ✅ | ✅ | ✅ |
| `mark_memory_dnr` | ✅ | ✅ | ✅ |
| `unmark_memory_dnr` | ✅ | ✅ | ✅ |
| `is_memory_dnr` | ✅ | ✅ | ✅ |
| `verify_recall_results_dnr_free` | ✅ | ✅ | ✅ |
| `MEMORY_DNR_MARKED` | ✅ | ✅ | ✅ |
| `DNR_REVOKED` | ✅ | ✅ | ✅ |

---

## Verified Acceptance Criteria (from batch plan)

| AC | Description | Status |
|---|---|---|
| P3-013.1 | `do_not_recall=True` causes recall empty across vector/FTS/recency/context injection | ✅ Query builders exclude DNR; guard fails closed; injection calls `exclude_dnr=True` |
| P3-013.2 | DNR mutation emits metadata-only consent/audit event | ✅ `MEMORY_DNR_MARKED` and `DNR_REVOKED` events via `AuditTrail` with hash+length only |
| P3-013.3 | Unauthorized principal cannot mutate DNR | ✅ 5 unauthorized principals fail closed with `DNRAuthorizationError` |
| P3-013.4 | DNR reversal is explicit and audited | ✅ `unmark_memory_dnr()` emits `DNR_REVOKED` audit event |
| P3-013.5 | Zero raw DNR content in logs/evidence | ✅ Verified in `TestNoRawContentInLogsAndEvents`; no `reason`, no `raw_content` in payloads |

---

## Parent Evidence Accuracy Verification

| Claim in `verification.md` | Actual | Verdict |
|---|---|---|
| `dnr.py` — 415 lines | 418 lines | Minor discrepancy (+3 lines, likely from parent cleaning) |
| `test_dnr.py` — 586 lines | 585 lines | Minor discrepancy (-1 line) |
| `__init__.py` modified +14 lines | 170 lines total | Consistent (from git baseline) |
| Diagnostics: 0 errors in source | ✅ Confirmed | Accurate |
| Diagnostics: 1 pre-existing pytest import error | ✅ Confirmed | Accurate |
| 32 passed focused tests | ✅ 32/32 | Accurate |
| 93 passed regression | ✅ 93/93 | Accurate |
| No type suppressions remain | ✅ Confirmed | Accurate |
| Caveats: ConsentLedger, content-hash, Prometheus deferred | ✅ Confirmed | Accurate, properly documented |

---

## Caveats and Minor Notes

### Properly documented (no action needed):
1. **ConsentLedger cross-reference deferred** — `ConsentLedger` lacks `target_memory_id` field; DNR enforcement relies on column filter (Layer 2) + pre-injection guard (Layer 5). Documented in verification.md §8 and batch plan caveats.
2. **Content-hash dedup deferred** — Would require schema changes. Documented.
3. **Prometheus counters deferred** — P8 observability not yet deployed. Structured logs used instead.

### Minor issues (no functional impact):
1. **Line count discrepancy**: `dnr.py` is 418 lines (verification claims 415), `test_dnr.py` is 585 lines (claims 586). Attributed to parent cleaning pass after verification was written. Recommend updating verification line counts.
2. **In-test `import asyncio`**: 15 occurrences of `import asyncio` inside test functions instead of top-level import. Code works but is a minor style inconsistency.
3. **`_where_criteria` private API usage**: Test `FakeDNRSession` accesses SQLAlchemy's `_where_criteria` (protected). Updated batch plan and verification already note this caveat. Acceptable for fake-session pattern.

---

## Boundary Compliance

| Boundary | Status | Evidence |
|---|---|---|
| DNR absolute: no recall/injection/cache exposure | ✅ PASS | Query-level filter + post-recall guard; no raw content in logs |
| Safe-persona: no Y6, no punishment overflow | ✅ PASS | DNR is declarative; no punishment/retry escalation |
| Consent: no revocation bypass | ✅ PASS | DNR marker persists; unmark requires explicit audit |
| No raw private data in artifacts | ✅ PASS | All audit/log uses hash+length only |
| No type suppression | ✅ PASS | 0 `# type: ignore` in source or tests |
| No destructive DB ops | ✅ PASS | Only `UPDATE` statements |
| No Aizanta touch | ✅ PASS | No imports from or references to Aizanta |

---

## Security Scan

| Check | Result |
|---|---|
| Type suppressions in source | 0 |
| Type suppressions in tests | 0 (parent removed) |
| Empty except/catch | 0 |
| Secrets/credentials in code | 0 |
| Raw content in logs/events | 0 |
| Avoidable `Any` in `dnr.py` | 0 (Protocol types only) |
| Destructive DB operations | 0 (`UPDATE` only, transactional) |
| Circular imports | 0 (dnr.py imports only `models`) |

---

## Report Metadata

| Field | Value |
|---|---|
| Step | STEP-P3-013 |
| Auditor | Independent auditor gate |
| Date | 2026-06-02 |
| Verdict | **PASS** |
| Files examined | `src/memory/dnr.py`, `src/memory/__init__.py`, `tests/memory/test_dnr.py`, `src/memory/read_pipeline.py` (DNR portions) |
| Tests run | 32 focused DNR, 93 regression (P3-011+P3-012+P3-013) |
| Diagnostics | 0 errors in source; 1 pre-existing pytest import in test (env limit) |
| Next action | Proceed to STEP-P3-014 |
