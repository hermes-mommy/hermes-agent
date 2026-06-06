# Phase 7c B1 — guinevere-mcp Service Fix Verification

> Date: 2026-06-06
> Scope: Fix `guinevere-mcp` inactive/dead root cause without touching Aizanta.
> Status: **FIX APPLIED; SYSTEMD ACTIVE AND ENABLED**

## 1. Root Cause

Research reports under `research-reports/phase-7c-b1/` established that `guinevere-mcp` was inactive/dead because the FastMCP server used default stdio transport under systemd.

Observed behavior:

- `guinevere-mcp` was `inactive (dead)` and `disabled`.
- Deployed unit used `Restart=on-failure`.
- Journal showed the server starting, registering 16 tools, logging `mcp_server_ready`, then immediately logging `mcp_server_shutting_down` with no error.
- FastMCP stdio is session-scoped; under systemd stdin is effectively closed, so the server exits cleanly.

Secondary startup blocker found during dry-run:

- VPS venv was missing `playwright`, while `src.mcp.tools.obscura_cdp` imports `playwright.async_api` at module import time.

## 2. Fix Applied

### Local repository changes

- `src/mcp/manager.py`
  - Configured FastMCP to bind to `127.0.0.1:8090`.
  - Changed entrypoint from default stdio to `server.run(transport="streamable-http")`, matching the installed VPS FastMCP API.
  - Removed avoidable `Any` and replaced broad `except Exception` with `except ImportError` for the auth matrix import guard.
- `pyproject.toml`
  - Added `playwright>=1.56` because MCP tool registration imports `src.mcp.tools.obscura_cdp` at startup.
- `uv.lock`
  - Updated with `uv lock`.

### VPS targeted changes

Because `git pull origin main` was blocked by unrelated dirty VPS files, no pull/merge overwrite was performed.

Targeted patch only:

- Copied verified local `src/mcp/manager.py` to `/home/guinevere/code/guinevere/src/mcp/manager.py`.
- Backed up prior remote file to `src/mcp/manager.py.bak.b1-manual`.
- Installed `playwright>=1.56` into `/home/guinevere/code/guinevere/.venv` using `uv pip install`.

No Aizanta files or services were touched.

## 3. Validation Results

### Local tests

```text
python -m pytest tests/mcp/test_manager.py -q --tb=short
20 passed, 1 warning in 3.41s
```

```text
python -m pytest tests/phase7/test_T3_auth_enforcement.py tests/phase7/test_T10_monitoring_health.py -q --tb=short
33 passed, 1 warning in 2.93s
```

### Local static checks

```text
grep forbidden patterns in src/mcp/manager.py
No matches found for: # type: ignore, except:, except Exception, Any, @ts-ignore, @ts-expect-error, as any
```

`lsp_diagnostics src/mcp/manager.py`:

- 0 errors.
- Remaining warnings are pre-existing `structlog`/logger `Any` diagnostics from untyped third-party logger methods.

### VPS code/dependency proof

Remote `src/mcp/manager.py` excerpt verified:

```python
server = FastMCP(
    name=name,
    host="127.0.0.1",
    port=8090,
    lifespan=_build_lifespan(),
)

server.run(transport="streamable-http")
```

Remote dependency check:

```text
playwright OK
markdownify OK
mcp OK
uvicorn OK
```

Remote manager static check:

```text
{'has_host': True, 'has_streamable': True, 'bad_except': False, 'has_any': False}
```

### Manual runtime proof

Command:

```bash
cd /home/guinevere/code/guinevere
. .venv/bin/activate
timeout 8 python -m src.mcp.manager
```

Result:

```text
mcp_server_created host=127.0.0.1 name=guinevere-mcp port=8090
INFO:     Started server process [339218]
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8090 (Press CTRL+C to quit)
```

The command exited with code `124` only because the `timeout 8` wrapper intentionally terminated it. This proves the MCP server now stays running under HTTP transport instead of immediately shutting down from stdio EOF.

## 4. Systemd Start Status

Root access was provided after the initial sudo blocker. The approved systemd changes were applied as root:

```bash
sed -i 's/Restart=on-failure/Restart=always/' /etc/systemd/system/guinevere-mcp.service
sed -i 's|ExecStart=.*|ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.mcp.manager|' /etc/systemd/system/guinevere-mcp.service
systemctl daemon-reload
systemctl enable guinevere-mcp
systemctl restart guinevere-mcp
```

Final service state:

```text
systemctl is-active guinevere-mcp  -> active
systemctl is-enabled guinevere-mcp -> enabled
```

Runtime verification:

```text
Active: active (running) since Sat 2026-06-06 20:19:34 WIB
Main PID: 348465 (python)
ExecStart: /home/guinevere/code/guinevere/.venv/bin/python -m src.mcp.manager
mcp_server_created host=127.0.0.1 name=guinevere-mcp port=8090
StreamableHTTP session manager started
Uvicorn running on http://127.0.0.1:8090
LISTEN 127.0.0.1:8090 users:(("python",pid=348465,fd=6))
```

Recent journal status shows one non-fatal Python runtime warning about `src.mcp.manager` already being present in `sys.modules` before execution, followed by normal StreamableHTTP/uvicorn startup. No shutdown loop occurred after the restart.

## 5. Boundary Compliance

- No Aizanta files, containers, or services touched.
- No secrets printed or edited.
- No `.env.mcp` values modified.
- No SSH/firewall/port exposure changes.
- MCP binds to `127.0.0.1:8090`, not `0.0.0.0`.
- No deprecated archive/delete performed.
- No ADR-035 IMPLEMENTED claim.

## 6. Caveats

- Recent startup journal includes a non-fatal Python runtime warning about `src.mcp.manager` already being present in `sys.modules` before execution.
- `git pull origin main` on VPS is blocked by unrelated dirty files: `src/core/main.py`, `src/core/services/llm_router.py`, `src/hermes/plugins/persona_plugin.py`, and untracked `src/core/services/llm_metrics.py` plus env/bak files. These were not overwritten or stashed.
- Tool-level API keys in `.env.mcp` may still be incomplete. That can affect individual MCP tools, but not service startup.

## 7. Verdict

The root cause is fixed and systemd activation is complete: FastMCP now uses streamable HTTP, `guinevere-mcp` is enabled, active, and listening on `127.0.0.1:8090` under systemd.

B1 `guinevere-mcp` inactive/dead is resolved for service startup.
