# Scaffold: STEP-P6-015 — redis

## Expected Files

- `src/mcp/tools/redis_tool.py` — Redis operations tool with auth-level enforcement
- `tests/mcp/test_redis_tool.py` — Unit tests with mocked redis-py

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded passwords or connection strings
- `print(` (use structlog)
- `import logging` (use structlog)
- `aioredis` (use `redis-py` async)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_redis_tool.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/redis_tool.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/redis_tool.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Driver:** `redis.asyncio` (redis-py async interface)
- **Port:** 6380 (non-standard, per project config)
- **DB Allocation:**
  - DB0: Session cache
  - DB1: Memory recall
  - DB2: Surveillance buffer
  - DB3: Agent state
  - DB4: Discord state
  - DB5: Cost tracking (read-only from this tool; P6-020 writes)
- **Auth Levels:**
  - `GET`, `LRANGE`, `HGET`, `HGETALL`, `KEYS`, `SCAN` → `AuthLevel.READ_AUTO`
  - `SET`, `HSET`, `LPUSH`, `RPUSH`, `SADD` → `AuthLevel.WRITE_NOTIFY`
  - `DEL`, `FLUSHDB` → `AuthLevel.DESTRUCTIVE_APPROVAL`
  - `FLUSHALL`, `CONFIG SET`, `DEBUG` → `AuthLevel.FORBIDDEN`
- **Cost:** $0

### Function Signatures

```python
async def redis_get(key: str, db: int = 0) -> str | None:
    """Get a value by key. Auth: READ_AUTO."""

async def redis_set(key: str, value: str, ttl: int | None = None, db: int = 0) -> bool:
    """Set a key-value pair. Auth: WRITE_NOTIFY."""

async def redis_delete(key: str, db: int = 0) -> bool:
    """Delete a key. Auth: DESTRUCTIVE_APPROVAL."""

async def redis_list_range(key: str, start: int = 0, stop: int = -1, db: int = 0) -> list[str]:
    """Get list range. Auth: READ_AUTO."""

async def redis_keys(pattern: str = "*", db: int = 0) -> list[str]:
    """Scan keys matching pattern. Auth: READ_AUTO."""
```

### Command Classification

```python
READ_COMMANDS = {"GET", "LRANGE", "HGET", "HGETALL", "KEYS", "SCAN", "TTL", "EXISTS", "TYPE"}
WRITE_COMMANDS = {"SET", "HSET", "LPUSH", "RPUSH", "SADD", "SETNX", "SETEX", "INCR", "INCRBYFLOAT"}
DESTRUCTIVE_COMMANDS = {"DEL", "FLUSHDB", "EXPIRE", "PERSIST", "RENAME"}
FORBIDDEN_COMMANDS = {"FLUSHALL", "CONFIG", "DEBUG", "SHUTDOWN", "SLAVEOF"}
```

### Error Handling

- Connection refused → log + raise with host:port details
- Forbidden command → raise `ForbiddenOperationError` before execution
- Key not found → return None (not an error)

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-015/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-015/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No hardcoded passwords or connection strings
- [ ] `FLUSHALL` is FORBIDDEN (always blocked)
- [ ] `DEL` requires DESTRUCTIVE_APPROVAL
- [ ] `GET/LRANGE` is READ_AUTO
- [ ] `SET/HSET` is WRITE_NOTIFY
- [ ] Port 6380 used in default config
- [ ] `redis.asyncio` used (not aioredis)
- [ ] DB parameter supported for multi-DB access
- [ ] `structlog` used for all logging
- [ ] Tests verify all 4 auth levels
