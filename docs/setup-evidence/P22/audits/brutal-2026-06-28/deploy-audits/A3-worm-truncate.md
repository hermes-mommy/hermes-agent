# A3 — WORM TRUNCATE Revocation (Independent Re-Verification)

**Date:** 2026-06-28
**Auditor:** Independent sub-agent (Claude)
**Target:** `audit.integration_api_log` on VPS PostgreSQL
**Migration:** `p22_002_revoke_truncate_audit` (alembic `p22_001_integration_schema` -> `p22_002_revoke_truncate_audit`)

---

## Verdict: PASS

---

## 1. Database Grants (Live VPS Query)

Source: `information_schema.role_table_grants` + `has_table_privilege()` via SSH.

### Explicit grants on `audit.integration_api_log` to `guinevere_core`:

| grantee          | privilege_type |
|------------------|----------------|
| guinevere_core   | INSERT         |
| guinevere_core   | REFERENCES     |
| guinevere_core   | SELECT         |
| guinevere_core   | TRIGGER        |

### `has_table_privilege('guinevere_core', 'audit.integration_api_log', ...)` checks:

| Privilege  | Result |
|------------|--------|
| TRUNCATE   | **False** |
| UPDATE     | **False** |
| DELETE     | **False** |
| INSERT     | True   |
| SELECT     | True   |

## 2. Migration File Verification (VPS disk)

- File exists: `/home/guinevere/code/guinevere/alembic/versions/p22_002_revoke_truncate_audit.py`
- `revision: str = "p22_002_revoke_truncate_audit"`
- `down_revision = "p22_001_integration_schema"`
- Contains `REVOKE TRUNCATE ON audit.integration_api_log FROM guinevere_core;`
- Contains `REVOKE TRUNCATE ON audit.integration_api_log FROM PUBLIC;`

## 3. WORM Contract Assessment

| Property | Status | Notes |
|----------|--------|-------|
| No TRUNCATE | PASS | `has_table_privilege` returns False |
| No UPDATE | PASS | `has_table_privilege` returns False; no UPDATE grant in `role_table_grants` |
| No DELETE | PASS | `has_table_privilege` returns False; no DELETE grant in `role_table_grants` |
| INSERT allowed | PASS | Append-only writes intact |
| SELECT allowed | PASS | Read access intact |
| Migration on disk | PASS | `REVOKE TRUNCATE` from both `guinevere_core` and `PUBLIC` |

**WORM contract is intact.** The `guinevere_core` role can only INSERT (append) and SELECT (read) rows in `audit.integration_api_log`. TRUNCATE, UPDATE, and DELETE are all denied. The audit log is append-only.

---

## Raw SSH Output

```
grants: [('guinevere_core', 'INSERT'), ('guinevere_core', 'REFERENCES'), ('guinevere_core', 'SELECT'), ('guinevere_core', 'TRIGGER')]
guinevere_core TRUNCATE: False
guinevere_core UPDATE: False
guinevere_core DELETE: False
guinevere_core INSERT: True
guinevere_core SELECT: True
```
