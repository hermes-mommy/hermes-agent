# A7 — P22 Test Suite Verification (Local + VPS)

**Date:** 2026-06-28
**Auditor:** Independent sub-agent (not parent)
**Method:** Fresh pytest invocation on both hosts, grep for skip/fail/error markers

---

## Verdict: PASS

Both runs produced zero failures, zero skips, zero errors.

---

## Local (Windows — C:/Users/faizz/guinevere)

```
python -m pytest tests/p22/ -q --no-header -p no:warnings
```

| Metric        | Value      |
|---------------|------------|
| **Passed**    | **972**    |
| Failed        | 0          |
| Skipped       | 0          |
| Errors        | 0          |
| Duration      | 40.53s     |
| Active test files | 55    |

**Note:** One PytestDeprecationWarning from pytest-asyncio about unset `asyncio_default_fixture_loop_scope` — framework-level config notice, not a test defect.

---

## VPS (Ubuntu 24.04 — /home/guinevere/code/guinevere)

```
.venv/bin/python -m pytest tests/p22/ -q --no-header -p no:warnings
```

| Metric        | Value      |
|---------------|------------|
| **Passed**    | **119**    |
| Failed        | 0          |
| Skipped       | 0          |
| Errors        | 0          |
| Duration      | 2.03s      |
| Test files on VPS | 9      |

---

## Count Difference Explanation (972 vs 119)

Local has 55 active test files; VPS has 9 scp'd test files. The 853-test delta is expected and acceptable — VPS only has the subset of test files explicitly deployed for production-activation verification. The missing 46 test files cover adapter dispatch, re-parsing, calendar/drive redispatch, capability matrix, project isolation, onboarding, consent canonical flows, memory wiring, audit redaction, foundation proof, and other integration tests that exercise local-only adapters or full-stack scenarios not relevant to the VPS production runtime.

---

## VPS conftest.py Status

`tests/p22/conftest.py` is **MISSING** on VPS. The 9 VPS test files have no shared fixture file. Tests still pass because the individual test files define their own fixtures or do not depend on conftest-shared fixtures. This is noted but does not constitute a failure.

---

## Requested File Existence Check (VPS)

All 4 specified files confirmed present:

| File | Status |
|------|--------|
| `test_audit_writer_production.py` | EXISTS |
| `test_permissions.py`             | EXISTS |
| `test_registry.py`                | EXISTS |
| `test_dry_run.py`                 | EXISTS |

---

## VPS Test Files (complete list, 9 files)

1. `test_audit_writer_production.py`
2. `test_calendar_429_retry.py`
3. `test_consent_shims_fail_closed.py`
4. `test_drive_429_retry.py`
5. `test_dry_run.py`
6. `test_github_client_errors.py`
7. `test_permissions.py`
8. `test_registry.py`
9. `test_shims.py`

---

## Acceptance Criteria

| Criterion | Status |
|-----------|--------|
| Local = 972 passed | PASS (972 passed, 0 failed) |
| VPS >= 119 passed | PASS (119 passed, 0 failed) |
| 0 failures on either host | PASS |
| 4 specified files exist on VPS | PASS |
| Count difference documented as acceptable | PASS |
