# Scaffold: STEP-P6-014 — postgres

## Expected Files

- `src/mcp/tools/postgres_tool.py` — PostgreSQL query tool with read-only enforcement
- `tests/mcp/test_postgres_tool.py` — Unit tests with mocked asyncpg

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded DSN or passwords
- `print(` (use structlog)
- `import logging` (use structlog)
- `psycopg2` (use asyncpg)
- `sqlalchemy` direct query (use asyncpg for raw SQL)
- Raw string concatenation for SQL (must use parameterized queries)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_postgres_tool.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/postgres_tool.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/postgres_tool.py` | 0 | No type errors |
| `grep -iE "DROP|TRUNCATE|ALTER" src/mcp/tools/postgres_tool.py \| grep -v "test\|#\|FORBIDDEN"` | 1 | No DDL in source |

## Implementation Details

### Key Design

- **Driver:** `asyncpg` with connection pool
- **Port:** 5433 (non-standard, per project config)
- **Auth Levels:**
  - `SELECT` queries → `AuthLevel.READ_AUTO`
  - `INSERT`, `UPDATE`, `DELETE` → `AuthLevel.DESTRUCTIVE_APPROVAL`
  - `DROP`, `TRUNCATE`, `ALTER` → `AuthLevel.FORBIDDEN` (always blocked)
- **Defense-in-Depth (3 layers):**
  1. `BEGIN READ ONLY` transaction for SELECT operations
  2. SQL AST parsing to detect forbidden operations
  3. `guinevere_readonly` database role with SELECT-only grants
- **Cost:** $0
- **Parameterized Queries:** All queries must use `$1`, `$2` placeholders

### Function Signatures

```python
async def postgres_query(
    sql: str,
    params: list[object] | None = None,
    read_only: bool = True,
) -> list[dict[str, object]]:
    """Execute a PostgreSQL query. Auth varies by operation type."""

async def postgres_tables() -> list[str]:
    """List all tables in the database. Auth: READ_AUTO."""
```

### SQL Classification

```python
ALLOWED_READ = {"SELECT", "SHOW", "EXPLAIN", "WITH"}
REQUIRES_APPROVAL = {"INSERT", "UPDATE", "DELETE", "UPSERT"}
FORBIDDEN = {"DROP", "TRUNCATE", "ALTER", "CREATE", "GRANT", "REVOKE"}

def classify_sql(sql: str) -> str:
    """Classify SQL statement as read, write, or forbidden."""
```

### Error Handling

- Forbidden SQL → raise `ForbiddenOperationError` before execution
- Connection refused → log + raise with connection details
- Query timeout (30s) → log + raise `QueryTimeoutError`
- Invalid SQL → log + raise with PostgreSQL error message

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-014/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-014/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No hardcoded DSN or passwords
- [ ] `DROP TABLE` blocked at AST parsing layer (before execution)
- [ ] `INSERT/UPDATE/DELETE` requires `DESTRUCTIVE_APPROVAL`
- [ ] `SELECT` uses `BEGIN READ ONLY` transaction
- [ ] Parameterized queries enforced (no string concatenation)
- [ ] Port 5433 used in default config
- [ ] `asyncpg` used (not psycopg2 or sqlalchemy direct)
- [ ] `structlog` used for all logging
- [ ] Tests verify DROP is blocked, SELECT works, INSERT blocked without approval
