# Scaffold: STEP-P6-018 — Auth Matrix Verification

## Expected Files

- `src/mcp/auth.py` — Complete auth matrix enforcement (update from P6-001 skeleton)
- `tests/mcp/test_auth_matrix.py` — Comprehensive tests for all 16 tools × 4 auth levels

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- Auth bypass: any tool that skips auth check
- Hardcoded webhook URLs (use environment variable)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_auth_matrix.py -v` | 0 | All 16 tools pass auth checks |
| `python -m ruff check src/mcp/auth.py` | 0 | No lint errors |
| `python -m mypy src/mcp/auth.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **4 Auth Levels:**
  1. `READ_AUTO` — Execute immediately, no notification
  2. `WRITE_NOTIFY` — Execute + send Discord webhook notification after
  3. `DESTRUCTIVE_APPROVAL` — Send Discord webhook + wait for Faiz's approval BEFORE executing
  4. `FORBIDDEN` — Block execution, raise error, log attempt

- **Discord Webhook:** Environment variable `DISCORD_WEBHOOK_URL` for Write-Notify and Destructive-Approval notifications
- **Approval Flow:** Destructive-Approval sends webhook, waits for `/approve {request_id}` Discord command response (timeout 5 minutes)

### Auth Matrix (All 16 Tools)

| Tool | READ_AUTO | WRITE_NOTIFY | DESTRUCTIVE_APPROVAL | FORBIDDEN |
|------|-----------|-------------|---------------------|-----------|
| brave_search | ✓ | | | |
| context7 | ✓ | | | |
| exa | ✓ | | | |
| fetch | ✓ | | | |
| filesystem | read | write | delete | |
| github | read/get | create issue/PR | delete repo | |
| grep_app | ✓ | | | |
| obscura_cdp | navigate/read | form fill/click | file upload | |
| sequential_thinking | ✓ | | | |
| time | ✓ | | | |
| websearch | ✓ | | | |
| git | log/diff/status | commit/push | force push | force push to main |
| postgres | SELECT | | INSERT/UPDATE/DELETE | DROP/TRUNCATE |
| redis | GET/LRANGE | SET/HSET | DEL/FLUSHDB | FLUSHALL |
| shell | | | all operations | |
| docker | ps/logs/inspect | start/stop/restart | rm/rmi | system prune -a |

### Decorator Implementation

```python
def require_approval(level: AuthLevel, tool_name: str = "") -> Callable:
    """Decorator that enforces auth level before tool execution.
    
    READ_AUTO: execute immediately
    WRITE_NOTIFY: execute + Discord webhook after
    DESTRUCTIVE_APPROVAL: Discord webhook + wait for approval before
    FORBIDDEN: block + raise ForbiddenOperationError
    """
```

### Test Coverage

Each tool must have at least one test per auth level it uses:
- Test that READ_AUTO executes without notification
- Test that WRITE_NOTIFY executes and triggers webhook
- Test that DESTRUCTIVE_APPROVAL blocks until approval received
- Test that FORBIDDEN raises error immediately

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-018/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-018/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] All 16 tools have correct auth level enforced
- [ ] `AuthLevel` enum has exactly 4 values
- [ ] Discord webhook called for WRITE_NOTIFY (mocked in tests)
- [ ] Discord webhook + approval wait for DESTRUCTIVE_APPROVAL (mocked in tests)
- [ ] FORBIDDEN raises `ForbiddenOperationError` immediately
- [ ] Webhook URL from `os.environ` (not hardcoded)
- [ ] `structlog` used for all logging
- [ ] Tests cover all 16 tools
