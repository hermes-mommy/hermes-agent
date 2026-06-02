# Scaffold: STEP-P6-017 — docker

## Expected Files

- `src/mcp/tools/docker_tool.py` — Docker container management tool
- `tests/mcp/test_docker_tool.py` — Unit tests with mocked subprocess

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
- `docker-py` / `docker` Python SDK (use subprocess docker CLI)
- `shell=True` in subprocess

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_docker_tool.py -v` | 0 | All tests pass |
| `python -m ruff check src/mcp/tools/docker_tool.py` | 0 | No lint errors |
| `python -m mypy src/mcp/tools/docker_tool.py` | 0 | No type errors |

## Implementation Details

### Key Design

- **Execution:** `asyncio.create_subprocess_exec` calling `docker` CLI
- **Auth Levels:**
  - `docker ps`, `docker logs`, `docker inspect`, `docker images` → `AuthLevel.READ_AUTO`
  - `docker start`, `docker stop`, `docker restart` → `AuthLevel.WRITE_NOTIFY`
  - `docker rm`, `docker rmi` → `AuthLevel.DESTRUCTIVE_APPROVAL`
  - `docker system prune -a`, `docker rm $(docker ps -aq)` → `AuthLevel.FORBIDDEN`
- **Cost:** $0
- **User:** `guinevere` must be in `docker` group

### Function Signatures

```python
async def docker_ps(all: bool = False) -> list[dict[str, str]]:
    """List containers. Auth: READ_AUTO."""

async def docker_logs(container: str, tail: int = 100) -> str:
    """Get container logs. Auth: READ_AUTO."""

async def docker_inspect(container: str) -> dict[str, object]:
    """Inspect container details. Auth: READ_AUTO."""

async def docker_start(container: str) -> dict[str, str]:
    """Start a container. Auth: WRITE_NOTIFY."""

async def docker_stop(container: str) -> dict[str, str]:
    """Stop a container. Auth: WRITE_NOTIFY."""

async def docker_restart(container: str) -> dict[str, str]:
    """Restart a container. Auth: WRITE_NOTIFY."""

async def docker_rm(container: str, force: bool = False) -> dict[str, str]:
    """Remove a container. Auth: DESTRUCTIVE_APPROVAL."""
```

### Forbidden Operations

```python
FORBIDDEN_PATTERNS: frozenset[str] = frozenset({
    "system prune -a",
    "system prune --all",
    "volume prune",
    "network prune",
    "builder prune -a",
})
```

### Error Handling

- Docker not found → raise `ConfigurationError`
- Container not found → log + raise with container name
- Permission denied → raise suggesting `usermod -aG docker guinevere`
- Forbidden operation → raise `ForbiddenOperationError`

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-017/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-017/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] `docker system prune -a` is FORBIDDEN
- [ ] `docker rm` requires DESTRUCTIVE_APPROVAL
- [ ] `docker ps/logs/inspect` is READ_AUTO
- [ ] `docker start/stop/restart` is WRITE_NOTIFY
- [ ] `asyncio.create_subprocess_exec` used (NOT shell=True)
- [ ] `structlog` used for all logging
- [ ] Tests verify all 4 auth levels
