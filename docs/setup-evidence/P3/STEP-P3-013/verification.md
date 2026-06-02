# STEP-P3-013 — Do-Not-Recall Hardening / API Only

## 1. What Was Done

Implemented a controlled DNR (do-not-recall) API layer with authorization, metadata-only audit events, and pre-injection verification:

- **`src/memory/dnr.py`** — New module (418 lines) with:
  - `mark_memory_dnr(session, memory_id, *, reason, principal)` — Set `do_not_recall=True` on an episode. Only `guinevere_core` authorized.
  - `unmark_memory_dnr(session, memory_id, *, reason, principal)` — Set `do_not_recall=False`. Only `guinevere_core` authorized.
  - `is_memory_dnr(session, memory_id)` — Query `do_not_recall` status.
  - `verify_recall_results_dnr_free(results)` — Post-recall/pre-injection guard that raises `DNRViolationError` if any result has `do_not_recall=True`.
  - Custom errors: `DNRAuthorizationError`, `DNRStateError`, `DNRViolationError`.
  - Event constants: `MEMORY_DNR_MARKED`, `DNR_REVOKED`.
  - Metadata-only audit events via `audit.audit_trail` (using existing `AuditTrail` model fields `event_type`, `event_payload`, `principal`, `event_hash`, `occurred_at`).
  - Raw `reason` is never stored in audit payload; only `reason_hash` (SHA-256 prefix) and `reason_length` are recorded.
- **`src/memory/__init__.py`** — Exports all DNR symbols in both imports and `__all__`.
- **`tests/memory/test_dnr.py`** — 32 tests covering authorized mark/unmark, unauthorized rejection, DNR state queries, query-builder DNR filter preservation, pre-injection guard, and no-raw-content validation.

No model columns or migrations were added. No changes to `read_pipeline.py` query builders (existing DNR WHERE clauses preserved). No changes to `prompt_loader.py`, `hard_stop_handler.py`, or P3-014/P3-015 code.

## 2. Files Changed

| File | Status | Summary |
|---|---|---|
| `src/memory/dnr.py` | **CREATED** | DNR API module (418 lines) |
| `src/memory/__init__.py` | **MODIFIED** | Added DNR imports and `__all__` entries (+14 lines) |
| `tests/memory/test_dnr.py` | **CREATED** | DNR test suite (585 lines) |

## 3. Validation Results

### LSP Diagnostics

**`src/memory/dnr.py`**: **0 errors, 0 warnings** — clean.

**`src/memory/__init__.py`**: 0 diagnostics.

**`tests/memory/test_dnr.py`**: **1 error** (pre-existing environment issue: `import "pytest" could not be resolved` — pytest is installed and tests run correctly; basedpyright type checker cannot resolve the package from the Python 3.14 environment). Remaining warnings are test-only warnings from unresolved pytest/SQLAlchemy typing and deliberate fake-session inspection of SQLAlchemy statement internals (`_where_criteria`, fixture decorator typing, `raises` method typing, `BindParameter` typing). Parent removed avoidable issues: unused imports, unused call-result warnings, invalid `pytest.LogCaptureFixture`, and the prior forbidden type suppression. **No type suppressions remain.**

### Pytest Results

```
test_dnr.py ...................... 32 passed in 1.76s
```

```
test_read_pipeline_hybrid.py .... 43 passed
test_prompt_context_injection.py. 18 passed
test_dnr.py ...................... 32 passed
====================================== 93 passed in 1.99s
```

All P3-011 and P3-012 tests remain passing — no regression.

## 4. Evidence Artifacts

| Artifact | Path |
|---|---|
| DNR source module | `src/memory/dnr.py` |
| DNR tests | `tests/memory/test_dnr.py` |
| Module exports | `src/memory/__init__.py` |
| Batch plan | `docs/setup-evidence/P3/batch-plan-011-015.md` |
| External DNR research | `docs/setup-evidence/P3/research/external-dnr-safe-mode-memory-filtering.md` |
| Safety constraints | `docs/setup-evidence/P3/research/safety-governance-constraints-011-015.md` |
| Security risks | `docs/setup-evidence/P3/research/security-safety-risk-011-015.md` |

## 5. Doc-Sync Impact

- `batch-plan-011-015.md` references P3-013; no structural changes to plan.
- `PROGRESS.md` and `CHECKLIST.md` updated by parent after independent auditor PASS.
- No changes to ADR-Index or PersonaSafetyPolicy.

## 6. Boundary Compliance

| Boundary | Status | Evidence |
|---|---|---|
| **Consent/audit event** | ✅ Compliance | Metadata-only `AuditTrail` records using existing model fields. Reason stored as `reason_hash` + `reason_length` only; no raw reason string. |
| **Authorization** | ✅ Fail-closed | `_check_authorized()` raises `DNRAuthorizationError` for any principal != `guinevere_core`. Tested with 5 unauthorized principals. |
| **State guard** | ✅ Double-mark/double-unmark | `DNRStateError` raised for already-DNR mark or non-DNR unmark. |
| **Pre-injection guard** | ✅ Fail-closed | `verify_recall_results_dnr_free()` raises `DNRViolationError` on `do_not_recall=True` or string `"true"`. |
| **No raw content** | ✅ Evidence | Audit payload contains only metadata (IDs, reason_hash, reason_length, principal). Logger extra uses `reason_hash`, not raw reason. Tests assert `reason` key not present, `SECRET_RAW_CONTENT` not in payload. |
| **No type suppression** | ✅ Clean | No `# type: ignore`, no `Any` misuse in `dnr.py`. Test file avoids `Any` for production types. |
| **No schema changes** | ✅ Satisfied | Existing `Episodes.do_not_recall` column reused. No migrations. |
| **DNR WHERE preserved** | ✅ Verified | `test_vector_query_includes_dnr_filter`, `test_fts_query_includes_dnr_filter`, `test_recency_query_includes_dnr_filter` all PASS. |

## 7. Rollback/Re-run Safety

- All operations use `UPDATE` SQL — safe for re-run.
- `mark_memory_dnr` with `..where(Episodes.do_not_recall.is_(False))` — idempotent guard on already-DNR.
- Tests use fake sessions only; no production DB, no side effects.
- Rollback: delete `src/memory/dnr.py`, revert `src/memory/__init__.py`, delete `tests/memory/test_dnr.py`.

## 8. Design Decisions/Caveats

### Decisions

1. **`AuditTrail` used for metadata events** — `ConsentLedger` lacks `event_type` field. `AuditTrail` has `event_type`, `event_payload`, `principal`, `event_hash`, `occurred_at` — all fitting the event requirement without schema changes.

2. **Return type `uuid.UUID`** — Returns the `memory_id` (episode UUID) for caller confirmation. Not the audit record ID (callers need episode identity).

3. **Reason stored as hash+length only** — Raw reason string is never written to audit payload. Only `reason_hash` (SHA-256 first 32 hex chars) and `reason_length` are persisted, satisfying metadata-only mandate.

4. **Guard in `dnr.py`, not in `read_pipeline`** — `verify_recall_results_dnr_free()` is a standalone function callable anywhere (post-recall, pre-injection). No modification to `recall_memories` required.

### Caveats

1. **No content-hash dedup** — Not implemented as it would require schema changes. Documented deferred.

2. **No Prometheus counter** — P8 (observability) not yet deployed. Structured log metadata used instead.

3. **Layer 1 consent ledger cross-reference not implemented** — `ConsentLedger` lacks `target_memory_id` field; cross-referencing would require schema change. DNR enforcement relies on `Episodes.do_not_recall` column filter (Layer 2) and pre-injection guard (Layer 5).

4. **Test fake session uses SQLAlchemy internals** — Accessing `_where_criteria` on SQLAlchemy's `Update`/`Select` objects. These are private API details; if SQLAlchemy changes them, the fake session needs updating. Alternative: use end-to-end behavioral tests with a test DB.

## 9. Auditor Gate

**Status**: ✅ PASS — independent auditor completed after parent verification.

Auditor verified:
- DNR 100% exclusion in all recall paths (`exclude_dnr=True` default and query-builder WHERE clauses preserved).
- Authorization: unauthorized mutation blocked before mutation/audit; only `guinevere_core` can mark/unmark.
- Metadata-only audit events: no raw content, no raw prompt, no raw reason; `reason_hash` + `reason_length` only.
- Pre-injection guard fails closed on explicit `do_not_recall=True` including string variants.
- Source/test anti-pattern scan clean: no type suppressions, empty catches, skipped tests, or live service changes.
- Focused and regression tests pass. Auditor noted minor evidence line-count drift; parent corrected counts in this verification file.

Auditor report path: `docs/setup-evidence/P3/STEP-P3-013/auditor-gate.md`

## 10. Security Scan

| Check | Result |
|---|---|
| Type suppressions (`# type: ignore`) | 0 in source, 0 in tests, 0 required |
| Empty except/catch | 0 occurrences |
| Secrets/credentials in code | 0 — no tokens, keys, or passwords |
| Raw content in logs/events | 0 — all logs use `extra` metadata dicts; reason stored as hash+length |
| Avoidable `Any` types | 0 in `dnr.py` (type stubs only for protocols) |
| Destructive DB operations | 0 — only `UPDATE` statements (safe, transactional) |

## 11. Acceptance Criteria Mapping

| AC ID | Description | Status | Evidence |
|---|---|---|---|
| AC-MEM-005 | DNR prevents LLM context entry | ✅ PASS | `verify_recall_results_dnr_free` guard; all query builders include `do_not_recall IS false` clause |
| AC-DATA-003 | Faiz DNR rights over personal data | ✅ PARTIAL | DNR mark/unmark API exists. Faiz-level UI not implemented (deferred). |
| AC-DATA-006 | DNR survives backup-restore | ⏳ DESIGN | Backup reconciliation layer not implemented; `do_not_recall` column is persisted in DB. |

## 12. Footer

| Field | Value |
|---|---|
| Step | STEP-P3-013 |
| Batch | P3 memory safety (011-015) |
| Date | 2026-06-02 |
| Author | Guinevere (parent orchestrator + sub-agent) |
| Status | Complete — parent verified, auditor PASS, tracker sync complete |
| Changed files | 3 (1 created src, 1 modified init, 1 created tests) |
| Tests total | 93 (32 new P3-013 + 43 P3-011 + 18 P3-012) |
| Tests passed | 93/93 |
| LSP errors | 0 in source files; 1 pre-existing (pytest import resolution in test file) |
| Auditor gate | PASS — `docs/setup-evidence/P3/STEP-P3-013/auditor-gate.md` |
| Next action | Proceed to STEP-P3-014 safe-mode memory gate |
