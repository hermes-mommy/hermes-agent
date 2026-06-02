# Scaffold: STEP-P6-006 — filesystem

## Expected Files

- `src/mcp/tools/filesystem.py` — Filesystem tool with path whitelist enforcement
- `tests/mcp/test_filesystem.py` — Unit tests for read/write/delete with path validation

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded paths outside whitelist config
- `print(` (use structlog)
- `import logging` (use structlog)
- `os.system(` (use pathlib/subprocess)
- `eval(` or `exec(`

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_filesystem.py -v` | 0 | All tests pass, including blocked paths |
| `python -m ruff check src/mcp/tools/filesystem.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/filesystem.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Path Whitelist:** Configurable allowed base paths (frozen dataclass)
- **Default Allowed Paths:** `/home/guinevere/code`, `/home/guinevere/evidence`, `/home/guinevere/data`
- **Symlink Resolution:** `Path.resolve()` before whitelist check to prevent symlink escape
- **Separator-Enforced Prefix Matching:** `str(resolved).startswith(str(allowed) + os.sep)` or exact match
- **Auth Levels:**
  - Read operations → `AuthLevel.READ_AUTO`
  - Write operations → `AuthLevel.WRITE_NOTIFY`
  - Delete operations → `AuthLevel.DESTRUCTIVE_APPROVAL`

### Function Signatures

```python
async def fs_read(path: str) -> str:
    """Read file contents. Auth: READ_AUTO."""

async def fs_write(path: str, content: str) -> dict[str, str]:
    """Write file contents. Auth: WRITE_NOTIFY."""

async def fs_delete(path: str) -> dict[str, str]:
    """Delete a file. Auth: DESTRUCTIVE_APPROVAL."""

async def fs_list(path: str) -> list[str]:
    """List directory contents. Auth: READ_AUTO."""
```

### Path Validation

```python
def validate_path(path: str, allowed_paths: frozenset[str]) -> Path:
    """Resolve symlinks and verify path is within allowed directories."""
    resolved = Path(path).resolve()
    for allowed in allowed_paths:
        allowed_resolved = Path(allowed).resolve()
        if resolved == allowed_resolved or str(resolved).startswith(str(allowed_resolved) + os.sep):
            return resolved
    raise PathForbiddenError(f"Path not in whitelist: {path}")
```

### Error Handling

- Path not in whitelist → raise `PathForbiddenError` with attempted and allowed paths
- File not found → raise `FileNotFoundError` (standard)
- Permission denied → raise `PermissionError` (standard)

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-006/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-006/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No hardcoded secrets or API keys
- [ ] Three auth levels enforced: READ_AUTO (read), WRITE_NOTIFY (write), DESTRUCTIVE_APPROVAL (delete)
- [ ] Symlink resolution via `Path.resolve()` before whitelist check
- [ ] Separator-enforced prefix matching (not naive `startswith`)
- [ ] `/etc/` write attempt blocked in tests
- [ ] `structlog` used for all logging
- [ ] Frozen dataclass for whitelist config
