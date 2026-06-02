# Scaffold: STEP-P6-016 — shell

## Expected Files

- `src/mcp/tools/shell_tool.py` — Shell command execution with whitelist enforcement
- `tests/mcp/test_shell_tool.py` — Unit tests with mocked subprocess

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- `os.system(` (use asyncio subprocess)
- `eval(` or `exec(`
- Shell=True in subprocess (use exec form)

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_shell_tool.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/shell_tool.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/shell_tool.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Execution:** `asyncio.create_subprocess_exec` (NOT shell=True)
- **Auth Level:** `AuthLevel.DESTRUCTIVE_APPROVAL` for all operations (whitelist narrows scope)
- **Cost:** $0

### Whitelist

```python
ALLOWED_COMMANDS: frozenset[str] = frozenset({
    "ls", "cat", "grep", "find", "wc", "head", "tail",
    "python", "pip", "git", "systemctl status",
    "df", "free", "uptime", "hostname", "whoami", "pwd",
    "echo", "date", "which", "file", "stat",
})

BLOCKED_PATTERNS: frozenset[str] = frozenset({
    "rm -rf", "mkfs", "dd", "sudo", "chmod 777",
    "wget | sh", "curl | sh", "wget|sh", "curl|sh",
    ":(){",  # fork bomb
    "> /dev/sda", "mv / /dev/null",
    "shutdown", "reboot", "halt", "poweroff",
})
```

### Injection Defense

```python
def validate_command(cmd: str) -> tuple[str, list[str]]:
    """Parse and validate shell command against whitelist.
    
    Rejects commands containing: ; | && $() `` that could bypass whitelist.
    Returns (base_command, args) tuple.
    """
```

### Function Signature

```python
async def shell_exec(
    command: str,
    workdir: str | None = None,
    timeout: int = 30,
) -> dict[str, object]:
    """Execute a whitelisted shell command.
    
    Returns dict with exit_code, stdout, stderr, duration_ms.
    Auth: DESTRUCTIVE_APPROVAL (all shell ops require approval).
    """
```

### Error Handling

- Command not in whitelist → raise `CommandForbiddenError` with blocked reason
- Injection pattern detected → raise `CommandForbiddenError`
- Timeout → kill process, return partial output with timeout flag
- Non-zero exit → return result dict (not an exception — caller decides)

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-016/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-016/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] `rm -rf` blocked in tests
- [ ] `sudo` blocked in tests
- [ ] `ls` works when whitelisted
- [ ] Auth level `DESTRUCTIVE_APPROVAL` enforced for ALL shell operations
- [ ] `asyncio.create_subprocess_exec` used (NOT shell=True)
- [ ] Pipe/subshell injection patterns detected and blocked
- [ ] Timeout kills process after specified seconds
- [ ] `structlog` used for all logging
