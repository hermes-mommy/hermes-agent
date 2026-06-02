# Scaffold: STEP-P6-001 — MCP Gateway + systemd Service

## Expected Files

- `src/mcp/__init__.py` — Module init, exports `MCPServer` class
- `src/mcp/manager.py` — FastMCP server, imports all 16 tool modules, stdio transport
- `src/mcp/tools/__init__.py` — Tools package init, dynamic tool registry
- `src/mcp/auth.py` — Auth decorator skeleton (`@require_approval` with 4 levels)
- `systemd/guinevere-mcp.service` — systemd unit file: Type=exec, User=guinevere, Slice=guinevere.slice
- `tests/mcp/__init__.py` — Test package init
- `tests/mcp/test_manager.py` — Unit tests for MCP gateway

## Forbidden Patterns

- `as any`
- `@ts-ignore`
- `# type: ignore`
- `cast(`
- `except Exception:` (empty/swallowed)
- `except:` (bare)
- Hardcoded API keys or secrets
- `print(` (use structlog)
- `import logging` (use structlog)
- `asyncio.run(` inside module scope

## Required Commands

| Command | Expected Exit Code | Notes |
|---------|-------------------|-------|
| `python -m pytest tests/mcp/test_manager.py -v` | 0 | All gateway tests pass |
| `python -m ruff check src/mcp/manager.py src/mcp/__init__.py src/mcp/auth.py src/mcp/tools/__init__.py` | 0 | No lint errors |
| `python -m mypy src/mcp/manager.py src/mcp/__init__.py src/mcp/auth.py` | 0 | No type errors |
| `python -c "from mcp.server.fastmcp import FastMCP; print('ok')"` | 0 | MCP SDK importable |
| `python -c "from src.mcp.manager import create_server; print('ok')"` | 0 | Server factory importable |

## Implementation Details

### `src/mcp/manager.py`

```python
from mcp.server.fastmcp import FastMCP
import structlog

logger = structlog.get_logger()

def create_server() -> FastMCP:
    """Create and configure the MCP server with all tool registrations."""
    server = FastMCP("guinevere-mcp")
    # Tool registrations happen via imports from src.mcp.tools.*
    # Each tool module registers itself via @server.tool() decorator
    return server
```

### `src/mcp/auth.py`

```python
from enum import Enum
from typing import Callable, Any
import structlog

class AuthLevel(Enum):
    READ_AUTO = "read_auto"
    WRITE_NOTIFY = "write_notify"
    DESTRUCTIVE_APPROVAL = "destructive_approval"
    FORBIDDEN = "forbidden"

def require_approval(level: AuthLevel) -> Callable:
    """Decorator that enforces auth level before tool execution."""
    ...
```

### `systemd/guinevere-mcp.service`

```ini
[Unit]
Description=Guinevere MCP Tool Manager
After=guinevere-core.service

[Service]
Type=exec
User=guinevere
WorkingDirectory=/home/guinevere/code/guinevere
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.mcp.manager
Restart=always
Slice=guinevere.slice

[Install]
WantedBy=multi-user.target
```

### pip Dependencies

```bash
pip install mcp httpx markdownify
```

Note: `redis`, `asyncpg`, `httpx`, `structlog` already in `pyproject.toml`.

## Evidence Requirements

- `docs/setup-evidence/P6/STEP-P6-001/verification.md` — 12-section verification report
- `docs/setup-evidence/P6/STEP-P6-001/auditor-gate.md` — auditor verdict

## Hard Rejection Criteria

- [ ] All expected files exist
- [ ] All forbidden patterns return zero matches
- [ ] All required commands pass (exit 0)
- [ ] Evidence files exist and are non-empty
- [ ] No API keys in any source file
- [ ] `FastMCP` imported from `mcp.server.fastmcp`
- [ ] `structlog` used for all logging (not print or stdlib)
- [ ] `src/mcp/auth.py` defines `AuthLevel` enum with exactly 4 levels
- [ ] `src/mcp/tools/__init__.py` exists as a valid Python package
- [ ] systemd service file specifies `Type=exec`, `User=guinevere`, `Slice=guinevere.slice`
- [ ] `create_server()` function is importable and returns `FastMCP` instance
