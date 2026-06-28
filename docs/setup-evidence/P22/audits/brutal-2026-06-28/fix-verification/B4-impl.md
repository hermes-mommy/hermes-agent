# B4 Implementation — Audit Logger + DB Writer Fixes

**Agent**: B4 (audit system owner)
**Findings addressed**: F22, F21, F24, F25, F29, F32
**Date**: 2026-06-28
**Baseline**: 897 passed
**Post-fix**: 953 passed, 1 pre-existing failure (test_l1_list_dir_audited — classifier F04 regression, not B4's)

---

## Files Changed

| File | Changes |
|---|---|
| `src/life_integrations/audit.py` | F22 caller (degraded mode), F24 (verify_chain raises), F25 (UUID v4 comment), F32 (external signature note) |
| `src/life_integrations/audit_db_writer.py` | F22 (seed_last_hash returns None), F21 (prom counter), F29 (configurable chain_version) |
| `tests/p22/test_audit.py` | F24 (updated assertions: verify_chain returns None on success, raises ChainVerificationError on failure) |
| `tests/p22/test_audit_db_writer.py` | F22 (seed_last_hash DB-down returns None), F21 (counter test), F29 (chain_version tests) |
| `tests/p22/test_foundation_proof.py` | F24 (verify_chain returns None assertion) |

---

## Per-Finding Changes

### F22 — seed_last_hash returns None on DB error

**audit_db_writer.py:64-101**:
- Return type: `str` → `str | None`
- Docstring: distinguishes `""` (legitimate fresh chain) from `None` (DB unreachable — caller DEGRADED)
- Empty-result path: still returns `""` (line 89)
- DB exception path: returns `None` (line 101), logs CRITICAL `"p22.audit_seed_failed_critical"` with `error` + `error_type` fields

**audit.py:197-237** (caller fix):
- `AuditLogger.__init__` now accepts `initial_hash: str | None = ""`
- When `initial_hash is None`: sets `self._degraded = True`, logs WARNING `"audit.degraded_mode_activated"`, keeps `self._last_hash = ""`
- New property `AuditLogger.degraded` — for health/dashboard endpoints

**tests/p22/test_audit_db_writer.py**:
- `test_seed_last_hash_db_down_returns_empty` → `test_seed_last_hash_db_down_returns_none` (assertion: `== ""` → `is None`)

---

### F21 — Audit write failures: Prometheus counter + ERROR log

**audit_db_writer.py**:
- Added `from prometheus_client import Counter` (prometheus_client confirmed importable; used in 10+ modules in this repo)
- Module-level counter: `_AUDIT_WRITE_FAILURES = Counter("p22_audit_write_failures_total", ..., ["integration_id", "error_type"])`
- In `write_event` except block: counter incremented with `integration_id` and `error_type` labels; ERROR log retained (now also includes `integration_id` and `error_type` fields)
- New health accessor: `get_audit_write_failure_count() -> int` — sums all label combinations via prometheus collector registry
- Counter implementation chosen: **prometheus_client** (not dict fallback) — confirmed importable, used by `src/core/main.py`, `src/gmail/metrics.py`, etc.

**tests/p22/test_audit_db_writer.py**:
- New test: `test_write_event_db_failure_increments_counter` — verifies counter increments by 1 on DB failure

---

### F24 — verify_chain raises ChainVerificationError

**audit.py:23** (import): `from src.life_integrations.errors import ChainVerificationError`

**audit.py:316-369** (`verify_chain`):
- Return type: `bool` → `None` (success = no exception; failure = raises)
- On previous_hash mismatch: raises `ChainVerificationError(f"chain broken at event {event.event_id}: expected previous_hash={prev_hash[:16]}... got={event.previous_hash[:16]}...")`
- On hash mismatch: raises `ChainVerificationError(f"hash mismatch at event {event.event_id}: stored event_hash={event.event_hash[:16]}... recomputed={computed[:16]}...")`
- `logger.error()` calls preserved (structured error log + exception)

**Caller updates** (not in my files — external callers):
- `test_foundation_proof.py:274`: `assert ...verify_chain(events) is True` → `result = ...verify_chain(events); assert result is None`

**tests/p22/test_audit.py**:
- Added `from src.life_integrations.errors import ChainVerificationError`
- `test_audit_chain_verification_valid`: `assert logger.verify_chain(events) is True` → `assert logger.verify_chain(events) is None`
- `test_audit_chain_verification_tamper_detected`: `assert ...is False` → `with pytest.raises(ChainVerificationError) as excinfo:` + assertions on message content
- New test: `test_audit_chain_verification_hash_mismatch_raises` — exercises the hash-mismatch branch specifically (mutates metadata, does NOT re-seal, verifies the exception mentions "hash mismatch" and the failing event_id)

---

### F25 — UUID v7 decision documented (OBSERVATION)

**audit.py:48-55** (near event_id field):
- Added 6-line comment explaining UUID v4 is intentional. No code change.

---

### F29 — chain_version configurable (OBSERVATION)

**audit_db_writer.py**:
- Added `import os`
- Module-level: `_CHAIN_VERSION = int(os.environ.get("P22_AUDIT_CHAIN_VERSION", "2"))` with upgrade-protocol comment
- SQL: literal `2` → `:chain_version` parameterized placeholder
- INSERT params dict: added `"chain_version": _CHAIN_VERSION`
- Default value unchanged (2)

**tests/p22/test_audit_db_writer.py**:
- New test: `test_chain_version_default_is_2` — verifies `_CHAIN_VERSION == 2` (does NOT reload module to avoid prometheus duplicate registration)
- New test: `test_write_event_inserts_chain_version_from_env` — monkeypatches `_CHAIN_VERSION` to 7, writes an event, verifies `params["chain_version"] == 7`

---

### F32 — External signature note (OBSERVATION)

**audit.py:78-84** (in `compute_hash()` docstring):
- Added NOTE documenting intra-chain SHA256 only, no external signature, relies on DB WORM, suggests ADR for notarization. No code change.

---

## Forbidden Pattern Verification

```
$ grep -rn "AuditChainVerificationError" src/ tests/
NONE (PASS)

$ grep -n "as any\|# type: ignore" src/life_integrations/audit.py src/life_integrations/audit_db_writer.py
NONE (PASS)

$ grep -n 'return ""' src/life_integrations/audit_db_writer.py
89:                return ""  (legitimate empty-table path only — NOT DB error)
PASS
```

---

## Scaffold Grep Results

```
$ grep -n "ChainVerificationError" src/life_integrations/audit.py
23:from src.life_integrations.errors import ChainVerificationError
323:            ChainVerificationError: if the chain is broken ...
349:                raise ChainVerificationError(
362:                raise ChainVerificationError(

$ grep -n "external signature\|Ed25519\|notarization" src/life_integrations/audit.py
78:        NOTE: Audit chain uses intra-chain SHA256 only. No external signature
79:        (no Ed25519 / RSA / Merkle root / timestamping authority).
83:        external notarization — requires an ADR (architecture decision),

$ grep -n "P22_AUDIT_CHAIN_VERSION\|_CHAIN_VERSION" src/life_integrations/audit_db_writer.py
9:- chain_version = 2 (configurable via P22_AUDIT_CHAIN_VERSION env var)
45:# 1. Bump P22_AUDIT_CHAIN_VERSION to the new value.
50:_CHAIN_VERSION = int(os.environ.get("P22_AUDIT_CHAIN_VERSION", "2"))
161:                        "chain_version": _CHAIN_VERSION,

$ grep -n "p22_audit_write_failures\|_AUDIT_WRITE_FAILURES" src/life_integrations/audit_db_writer.py
36:_AUDIT_WRITE_FAILURES = Counter(
37:    "p22_audit_write_failures_total",
169:            _AUDIT_WRITE_FAILURES.labels(
196:        for metric in _AUDIT_WRITE_FAILURES.collect():
```

---

## Test Output (verbatim)

### audit tests only (37/37 pass):

```
$ python -m pytest tests/p22/test_audit*.py -v --no-header
tests/p22/test_audit.py::test_audit_event_compute_hash PASSED
tests/p22/test_audit.py::test_audit_event_seal PASSED
tests/p22/test_audit.py::test_audit_chain_links_hashes PASSED
tests/p22/test_audit.py::test_audit_chain_verification_valid PASSED
tests/p22/test_audit.py::test_audit_chain_verification_tamper_detected PASSED
tests/p22/test_audit.py::test_audit_chain_verification_hash_mismatch_raises PASSED
tests/p22/test_audit.py::test_audit_metadata_redacts_secrets PASSED
tests/p22/test_audit.py::test_audit_metadata_redacts_long_values PASSED
tests/p22/test_audit.py::test_audit_logger_log_action PASSED
tests/p22/test_audit.py::test_audit_logger_with_writer PASSED
tests/p22/test_audit.py::test_audit_logger_project_id_in_event PASSED
tests/p22/test_audit_db_writer.py::test_write_event_inserts_with_project_id PASSED
tests/p22/test_audit_db_writer.py::test_write_event_redacts_via_to_dict PASSED
tests/p22/test_audit_db_writer.py::test_write_event_no_project_id_passes_none PASSED
tests/p22/test_audit_db_writer.py::test_write_event_db_down_no_raise PASSED
tests/p22/test_audit_db_writer.py::test_seed_last_hash_returns_last_hash PASSED
tests/p22/test_audit_db_writer.py::test_seed_last_hash_empty_returns_empty PASSED
tests/p22/test_audit_db_writer.py::test_seed_last_hash_db_down_returns_none PASSED
tests/p22/test_audit_db_writer.py::test_write_event_uses_cast_not_double_colon_jsonb PASSED
tests/p22/test_audit_db_writer.py::test_worm_no_update_path PASSED
tests/p22/test_audit_db_writer.py::test_write_event_db_failure_increments_counter PASSED
tests/p22/test_audit_db_writer.py::test_chain_version_default_is_2 PASSED
tests/p22/test_audit_db_writer.py::test_write_event_inserts_chain_version_from_env PASSED
tests/p22/test_audit_redaction_extra.py::... (14 tests) PASSED
tests/p22/test_audit_writer_production.py::... (5 tests) PASSED
====================== 37 passed, 145 warnings in 29.24s ======================
```

### full P22 suite (953/954 pass):

```
$ python -m pytest tests/p22/ -q --no-header
FAILED tests/p22/test_foundation_proof.py::test_l1_list_dir_audited - src.life_integrations.errors.ConsentDeniedError: consent not granted for scope: consent.filesystem.write
1 failed, 953 passed, 5510 warnings in 43.04s
```

The single failure (`test_l1_list_dir_audited`) is a pre-existing test that expects `list_dir` to be classified as L1_READ without consent. The F04 classifier fix (another agent, prior commit) now defaults unknown actions to L2_WRITE. This is NOT a regression caused by B4's changes.

---

## Summary

| Finding | Status | Code change | Test change |
|---|---|---|---|
| F22 | DONE | seed_last_hash returns None on error; AuditLogger degraded mode | seed-down test updated; new degraded property |
| F21 | DONE | prometheus_client Counter; ERROR log with labels; health accessor | counter-increment test added |
| F24 | DONE | verify_chain raises ChainVerificationError; return None on success | all 3 caller assertions updated; hash-mismatch test added |
| F25 | DONE | UUID v4 comment (observation only) | n/a |
| F29 | DONE | P22_AUDIT_CHAIN_VERSION env var; parameterized SQL | default-is-2 test; param-write test |
| F32 | DONE | External signature docstring note (observation only) | n/a |
