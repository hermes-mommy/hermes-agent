# Scaffold: STEP-P6-013 — git

## Expected Files

- `src/mcp/tools/git_tool.py` — Git operations tool with auth-level enforcement
- `tests/mcp/test_git_tool.py` — Unit tests with mocked subprocess

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- `print(` (use structlog)
- `import logging` (use structlog)
- `os.system(` (use subprocess)
- Hardcoded credentials

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_git_tool.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/git_tool.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/git_tool.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Execution:** `asyncio.create_subprocess_exec` for git commands
- **Auth Levels per Operation:**
  - `git log`, `git diff`, `git status`, `git branch`, `git show` → `AuthLevel.READ_AUTO`
  - `git commit`, `git push` (normal), `git checkout` → `AuthLevel.WRITE_NOTIFY`
  - `git push --force`, `git rebase -i`, `git reset --hard` → `AuthLevel.DESTRUCTIVE_APPROVAL`
  - `git push --force` to `main`/`master` → `AuthLevel.FORBIDDEN` (always blocked)
- **Cost:** $0

### Function Signatures

```python
async def git_status(repo_path: str = ".") -> str:
    """Get git status. Auth: READ_AUTO."""

async def git_log(repo_path: str = ".", count: int = 10) -> str:
    """Get git log. Auth: READ_AUTO."""

async def git_diff(repo_path: str = ".", staged: bool = False) -> str:
    """Get git diff. Auth: READ_AUTO."""

async def git_commit(repo_path: str, message: str, files: list[str] | None = None) -> str:
    """Commit changes. Auth: WRITE_NOTIFY."""

async def git_push(repo_path: str = ".", force: bool = False, branch: str | None = None) -> str:
    """Push to remote. Auth: WRITE_NOTIFY (normal), DESTRUCTIVE_APPROVAL (force), FORBIDDEN (force to main)."""
```

### Forbidden Operation

```python
FORBIDDEN_PATTERNS = [
    ("push", "--force", "main"),
    ("push", "--force", "master"),
    ("push", "-f", "main"),
    ("push", "-f", "master"),
]

def is_forbidden(args: list[str], branch: str | None) -> bool:
    """Check if git operation is forbidden."""
```

### Error Handling

- Git not found → raise `ConfigurationError`
- Non-zero exit code → capture stderr, log, raise `GitCommandError`
- Forbidden operation → raise `ForbiddenOperationError` with explanation

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-013/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-013/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No hardcoded credentials
- [ ] Four auth levels enforced per operation type
- [ ] `git push --force` to main/master is FORBIDDEN (not just Destructive-Approval)
- [ ] `asyncio.create_subprocess_exec` used (not `os.system`)
- [ ] stderr captured on failure
- [ ] `structlog` used for all logging
- [ ] Tests mock subprocess calls
