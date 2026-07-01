# P19-006c — Pre-Existing Finance Module/DB Drift (Deferred to P9)

**Date:** 2026-06-25
**Discovered by:** P19-006c real-DB testing (VPS `guinevere_p19_test`)
**Operator decision:** Follow established pattern (KG drift → P16); defer to P9.

## 1. The Drift

`src/finance/db.py` uses INSERT column names that do NOT match the real `financial.transactions` schema:

| db.py column | Real column |
|---|---|
| `type` | `transaction_type` |
| `started_at` / `ended_at` (inferred) | `occurred_at` |
| Missing | `classification`, `retention_class`, `access_policy`, `encryption_profile`, `deletion_state` (all NOT NULL) |

The real `financial.transactions` table (22 columns) was created in `e401bb5fd274_initial_schema_47_tables.py` and has `project_id` (nullable, added by P19-003). The finance module's `db.py` was written for a different schema and has never been exercised against the migrated DB.

## 2. P19-006c's position

P19-006c's code change — adding an optional `project_id: Optional[uuid.UUID] = None` param to `FinanceDB.insert_transaction()` — is **correct in design**. The param is passed through to the INSERT via dynamic column construction (only added when not None). The code is verified (syntax OK, 0 forbidden patterns, import OK).

The **test** cannot run against the real DB because the underlying INSERT column names don't match the real schema. This is a pre-existing defect in `db.py`, not caused by P19-006c.

## 3. Why deferred to P9

P9 (Financial Tracking, `⏳ TBD` / unstarted per PROGRESS.md) owns the finance module end-to-end. Fixing `db.py`'s INSERT to match the real `financial.transactions` schema is fundamentally P9's scope (it's a full schema reconciliation, not a project_id addition). P19-006c's `project_id` code is kept; when P9 reconciles the schema, the `project_id` column is already present and the param will work.

## 4. Evidence

- `tests/projects/test_finance_project_aware.py` — `pytestmark = pytest.mark.skip(reason="PRE-EXISTING finance module/DB drift (deferred to P9)...")`. 3 tests skip cleanly.
- `src/finance/db.py` — schema name corrected (`finance.transactions` → `financial.transactions`), `project_id` param added, dynamic INSERT column construction.
- `src/finance/plugin.py` — `project_id` param threaded through.
- `src/finance/hook.py` — `project_id=None` explicit.

## 5. P9 handoff note

When P9 begins, it must:
1. Reconcile `db.py`'s INSERT column names with the real `financial.transactions` schema.
2. Un-skip `tests/projects/test_finance_project_aware.py` and verify the `project_id` isolation passes.
3. The `project_id` column and the P19-006c code change are already in place.

## 6. Footer

| Field | Value |
|---|---|
| Drift type | Pre-existing code/DB column mismatch (finance module) |
| Discovered by | P19-006c real-DB testing |
| Caused by P19? | No |
| P19-006c project_id addition correct? | Yes (source-verified) |
| Resolution owner | P9 (Financial Tracking) |
| Date | 2026-06-25 |