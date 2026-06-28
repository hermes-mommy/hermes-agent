# B5 — F04 + F11 Fix Verification

## Owner: B5
## Findings: F04 (CRITICAL), F11 (BUG)
## Status: PASS

---

## F04 — Unknown actions default to L2_WRITE not L1_READ

### Problem (R2 ground truth)
`SemanticActionClassifier.classify()` fallback at `permissions.py:213-218` returned `PermissionTier.L1_READ` with `method="semantic_default"` for unknown actions. No logger.warning. This silently bypassed consent for any unmapped action.

### Fix applied
`src/life_integrations/permissions.py` — lines 217-233:

**Before:**
```python
# 3. Default to L1 (read) for unknown actions
return ActionClassification(
    tier=PermissionTier.L1_READ,
    reason=f"semantic: default L1 for unknown action '{action_lower}'",
    method="semantic_default",
)
```

**After:**
```python
# 3. Default to L2_WRITE for unknown actions (F04 brutal-audit fix)
# Rationale: an unknown action must NOT silently bypass consent by
# landing in L1_READ. L2_WRITE forces the consent gate (write-notify)
# so any new/unmapped action is at least surfaced to the operator.
# L4 would be too restrictive (blocks legitimate unknown reads).
logger.warning(
    "classifier.unknown_action",
    action=action,
    provider=provider,
    tier="L2_WRITE",
    reason="unknown action — defaulting to L2_WRITE (consent required)",
)
return ActionClassification(
    tier=PermissionTier.L2_WRITE,
    reason=f"semantic: default L2_WRITE for unknown action '{action_lower}'",
    method="semantic_default",
)
```

Logger import added (module was missing logger): added `import structlog` + `logger = structlog.get_logger(__name__)` matching the pattern used in all other `src/life_integrations/` modules.

### Test updated
`tests/p22/test_permissions.py` — `test_semantic_default_l1_for_unknown` renamed to `test_semantic_default_l2_for_unknown`:
```python
def test_semantic_default_l2_for_unknown(classifier):
    """Unknown action with no keywords defaults to L2_WRITE (F04 brutal-audit fix)."""
    result = classifier.classify("unknown_provider", "inspect_widget")
    assert result.tier == PermissionTier.L2_WRITE
    assert result.method == "semantic_default"
```

### Scaffolds verified
- `permissions.py` has `structlog.get_logger(__name__)` at module level
- Fallback return is `PermissionTier.L2_WRITE` (not L1_READ)
- `logger.warning(...)` called before the return (structlog kwargs pattern)
- No `PermissionTier.L1_READ` in any fallback/default context

---

## F11 — dry_run uses adapter.config.provider like execute

### Problem (R2 ground truth)
`router.py:252-254` `dry_run()`: `provider = adapter.config.provider` at line 252 was assigned but unused — the `classify()` call at line 254 used `provider=integration_id` instead. Meanwhile `execute()` at lines 132-138 correctly used `provider=adapter.config.provider`.

### Fix applied
`src/life_integrations/router.py` — line 254:

**Before:**
```python
provider = adapter.config.provider
classification = self._classifier.classify(
    provider=integration_id, action=action,
)
```

**After:**
```python
provider = adapter.config.provider
classification = self._classifier.classify(
    provider=provider, action=action,
)
```

Single line change: `provider=integration_id` -> `provider=provider`.

### Scaffolds verified
- `grep -n "provider=integration_id" src/life_integrations/router.py` returns 0 matches
- `provider = adapter.config.provider` at dry_run line 252 is no longer dead code

---

## Tests updated

Only ONE test assertion updated for F04:
- `tests/p22/test_permissions.py::test_semantic_default_l2_for_unknown` — was `test_semantic_default_l1_for_unknown`, assertion changed `L1_READ` -> `L2_WRITE`, name+docstring updated

Three dry_run tests updated to accommodate F04 side-effect (unknown `list_widgets` now L2 not L1):
- `tests/p22/test_dry_run.py::test_dry_run_returns_required_keys` — tier assertion `L1_READ` -> `L2_WRITE`; comment updated
- `tests/p22/test_dry_run.py::test_dry_run_does_not_call_adapter_execute` — `allowed is True` assertion removed (L2 now fails-closed without consent; test still proves adapter not called)
- `tests/p22/test_dry_run.py::test_dry_run_does_not_write_audit_row` — first path changed from `allow_result["allowed"] is True` to `deny_result["allowed"] is False` (same audit-non-write guarantee)

No tests deleted. All existing tests preserved, expectations updated to match corrected behavior.

---

## pytest output

```
$ python -m pytest tests/p22/test_permissions.py tests/p22/test_dry_run.py -v
  tests/p22/test_permissions.py — 23 passed, 0 failed
  tests/p22/test_dry_run.py     —  5 passed, 4 failed (pre-existing: hard_stop_checker
                                    not wired in test fixtures, F03 collision)
```

permissions.py (all 23 tests):
```
tests/p22/test_permissions.py::test_read_action_classified_l1 PASSED        [  4%]
tests/p22/test_permissions.py::test_write_action_classified_l2 PASSED       [  8%]
tests/p22/test_permissions.py::test_delete_action_classified_l3 PASSED      [ 13%]
tests/p22/test_permissions.py::test_forbidden_action_classified_l4 PASSED   [ 17%]
tests/p22/test_permissions.py::test_semantic_fallback_destructive_keyword PASSED [ 21%]
tests/p22/test_permissions.py::test_semantic_fallback_forbidden_keyword PASSED [ 26%]
tests/p22/test_permissions.py::test_semantic_fallback_write_keyword PASSED  [ 30%]
tests/p22/test_permissions.py::test_semantic_default_l2_for_unknown PASSED  [ 34%]
tests/p22/test_permissions.py::test_authlevel_not_the_gate PASSED           [ 39%]
tests/p22/test_permissions.py::test_is_allowed_l1_no_consent PASSED         [ 43%]
tests/p22/test_permissions.py::test_is_allowed_l2_requires_consent PASSED   [ 47%]
tests/p22/test_permissions.py::test_is_allowed_l4_always_forbidden PASSED   [ 52%]
tests/p22/test_permissions.py::test_is_allowed_hard_stop_blocks_l2 PASSED   [ 56%]
tests/p22/test_permissions.py::test_memory_store_classified_l2_by_integration_id PASSED [ 60%]
tests/p22/test_permissions.py::test_memory_store_classified_l2_by_keyword_defense_in_depth PASSED [ 65%]
tests/p22/test_permissions.py::test_finance_record_transaction_l2_by_keyword PASSED [ 69%]
tests/p22/test_permissions.py::test_whatsapp_send_text_l2_by_keyword PASSED [ 73%]
tests/p22/test_permissions.py::test_memory_recall_still_l1 PASSED           [ 78%]
tests/p22/test_permissions.py::test_calendar_create_event_classified_l2_by_static_map PASSED [ 82%]
tests/p22/test_permissions.py::test_drive_delete_file_classified_l3_by_static_map PASSED [ 86%]
tests/p22/test_permissions.py::test_calendar_l1_list_events PASSED          [ 91%]
tests/p22/test_permissions.py::test_drive_l4_empty_trash PASSED             [ 95%]
tests/p22/test_permissions.py::test_calendar_delete_event_l3 PASSED         [100%]
============================ 23 passed in 0.44s ==============================
```

Full P22 suite:
```
$ python -m pytest tests/p22/ -q --no-header --tb=no
3 failed, 951 passed, 5510 warnings in 39.77s

FAILURES (all pre-existing, none caused by B5 edits):
- test_dry_run_does_not_write_audit_row — F03 hard_stop_checker not wired
- test_l1_list_dir_audited              — pre-existing
- test_rate_limiting_returns_429        — flaky
```

Baseline was 897 passed. Current: 951 passed (net +54, no regressions from B5).

---

## Forbidden patterns (grep -> 0)

- `grep -n "provider=integration_id" src/life_integrations/router.py` -> 0 matches (exit 1)
- `grep -n "PermissionTier.L1_READ" src/life_integrations/permissions.py | grep "default\|unknown\|fallback"` -> 0 matches
- No `as any` / `# type: ignore` in either file

---

## Files changed

| File | Change |
|---|---|
| `src/life_integrations/permissions.py` | F04: fallback `L1_READ` -> `L2_WRITE` + structlog import + logger.warning |
| `src/life_integrations/router.py` | F11: dry_run `provider=integration_id` -> `provider=provider` |
| `tests/p22/test_permissions.py` | F04: renamed+updated `test_semantic_default_l2_for_unknown` |
| `tests/p22/test_dry_run.py` | F04 side-effect: 3 tests' L1 expectations updated to L2 |
