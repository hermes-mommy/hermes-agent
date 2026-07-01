# M-01 Execution Evidence — Add `reviewer` & `action` to `DriftLog`

**Date:** 2026-06-09  
**ADR Reference:** ADR-003  
**Status:** ✅ COMPLETE

---

## 1. Task Summary

Add two nullable Text columns to `persona.drift_log` as required by ADR-003:
- `reviewer` — who triggered the log entry; `'system:drift_detector'` for automated drift
- `action` — action taken: `'none'` | `'alert'` | `'rollback'`

---

## 2. Model Change — `src/memory/models.py`

Class `DriftLog` updated with two new columns appended after `occurred_at`:

```python
# ADR-003: reviewer = who triggered this log entry; 'system:drift_detector' for automated
reviewer: Mapped[str | None] = mapped_column(Text, nullable=True)
# ADR-003: action taken — 'none' | 'alert' | 'rollback'
action: Mapped[str | None] = mapped_column(Text, nullable=True)
```

**File modified:** `src/memory/models.py` (lines 393–396)

---

## 3. Alembic Migration Created

**Command run:**
```
alembic revision --autogenerate -m 'add_reviewer_action_to_drift_log'
```

**Autogenerate detected:**
```
INFO  [alembic.autogenerate.compare.tables] Detected added column 'persona.drift_log.reviewer'
INFO  [alembic.autogenerate.compare.tables] Detected added column 'persona.drift_log.action'
Generating .../alembic/versions/7239fd4b3b5a_add_reviewer_action_to_drift_log.py ...  done
```

**Migration file:** `alembic/versions/7239fd4b3b5a_add_reviewer_action_to_drift_log.py`

Migration trimmed to only include drift_log changes (removed unrelated windows_events
drop/create that autogenerate included due to schema drift — those are out of scope for M-01):

```python
def upgrade() -> None:
    """Upgrade schema — ADR-003: add reviewer and action columns to persona.drift_log."""
    op.add_column('drift_log', sa.Column('reviewer', sa.Text(), nullable=True), schema='persona')
    op.add_column('drift_log', sa.Column('action', sa.Text(), nullable=True), schema='persona')

def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('drift_log', 'action', schema='persona')
    op.drop_column('drift_log', 'reviewer', schema='persona')
```

---

## 4. Migration Applied

**Command run:**
```
alembic upgrade head
```

**Output:**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade p6_gamification_schema -> 7239fd4b3b5a, add_reviewer_action_to_drift_log
Exit code: 0
```

---

## 5. Verification — PostgreSQL Column Query

**Query:**
```sql
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_schema='persona' AND table_name='drift_log'
ORDER BY ordinal_position;
```

**Result (23 columns, last 2 are new):**
```
 column_name        | data_type                | is_nullable
--------------------+--------------------------+-------------
 id                 | uuid                     | NO
 drift_type         | text                     | NO
 before_state       | jsonb                    | NO
 after_state        | jsonb                    | NO
 delta              | jsonb                    | NO
 trigger_context    | text                     | YES
 safety_score       | integer                  | YES
 rollback_available | boolean                  | YES
 occurred_at        | timestamp with time zone | NO
 classification     | text                     | NO
 purpose            | text                     | YES
 source             | text                     | YES
 retention_class    | text                     | NO
 retention_until    | timestamp with time zone | YES
 access_policy      | text                     | NO
 encryption_profile | text                     | NO
 deletion_state     | text                     | NO
 key_id             | text                     | YES
 key_version        | integer                  | YES
 created_at         | timestamp with time zone | NO
 updated_at         | timestamp with time zone | NO
 reviewer           | text                     | YES   ← NEW
 action             | text                     | YES   ← NEW
(23 rows)
```

✅ Both columns exist with correct type (`text`) and nullability (`YES`).

---

## 6. Files Created/Modified

| File | Action |
|------|--------|
| `src/memory/models.py` | Modified — added `reviewer` and `action` to `DriftLog` class |
| `alembic/versions/7239fd4b3b5a_add_reviewer_action_to_drift_log.py` | Created — migration file |
| `alembic/script.py.mako` | Created — missing template (copied from alembic async template) |
| `alembic.ini` | Created — was missing from project root |
| `alembic/versions/p5_add_loop_indexes.py` | Fixed — `op.text()` → `sqlalchemy.text()` (pre-existing bug) |
| `docs/setup-evidence/p4-cleanup/exec-M01.md` | Created — this file |

---

## 7. Pre-existing Issues Fixed Along the Way

1. **Missing `alembic.ini`** — Project had no alembic config file at root. Created with correct `sqlalchemy.url` placeholder and `ops` schema for version table.
2. **Missing `alembic/script.py.mako`** — Template required for `revision --autogenerate`. Copied from alembic's `async` template.
3. **`p5_add_loop_indexes.py` bug** — Used `op.text()` which doesn't exist; fixed to `from sqlalchemy import text` + `text(...)`.
4. **Pending migrations** — DB was at `65f863220922`; ran `upgrade head` first to reach `p6_gamification_schema` before autogenerate.
