# FastMCP Transport Research — stdio vs HTTP/Streamable-HTTP for systemd Service

> **Research date**: 2026-06-06
> **Purpose**: Determine whether stdio MCP servers should be long-lived systemd services; whether FastMCP supports streamable-http/SSE/http transport and how; risks of changing transport; recommendation for Guinevere MCP with zero service disruption.

---

## Executive Summary

**For a long-lived systemd service, STDIO transport is fundamentally the wrong choice.** The MCP stdio transport is designed as a session-scoped protocol where the client spawns the server as a subprocess, communicates over stdin/stdout, and the server exits when the session ends (standard input reaches EOF). Running stdio under systemd creates an orphan process risk and wastes resources. FastMCP supports four transports — `stdio`, `http`, `sse`, `streamable-http` — and the authoritative recommendation is to use `streamable-http` (aliased as `"http"` in recent FastMCP versions) for any persistent server deployment.

**Recommendation:** Switch Guinevere MCP from `mcp.run(transport="stdio")` to either `mcp.run(transport="http")` (direct HTTP server) or `mcp.http_app()` behind Uvicorn (ASGI mode with health checks). This enables proper systemd service lifecycle, health monitoring, multi-client support, and eliminates the stdin EOF shutdown issue entirely.

---

## 1. FastMCP Transport Architecture

### 1.1 Supported Transports

FastMCP supports four transport modes, dispatched through `run_async()` / `run()` in `fastmcp_slim/fastmcp/server/mixins/transport.py`:

| Transport string | Class method | Protocol | Use case |
|---|---|---|---|
| `"stdio"` | `run_stdio_async()` | stdin/stdout | Local sessions, Claude Desktop, CLI tools |
| `"http"` | `run_http_async()` | Streamable HTTP (aliased) | **Recommended for production** |
| `"streamable-http"` | `run_http_async()` | Streamable HTTP (explicit) | Same as `"http"` — unified in FastMCP 2.3+ |
| `"sse"` | `run_http_async()` | Legacy SSE | Backward compatibility only |

**Key source:** `fastmcp_slim/fastmcp/server/mixins/transport.py` lines 49-82:

```python
async def run_async(self, transport=None, **transport_kwargs):
    if transport == "stdio":
        await self.run_stdio_async(**transport_kwargs)
    elif transport in {"http", "sse", "streamable-http"}:
        await self.run_http_async(transport=transport, **transport_kwargs)
```

### 1.2 How Stdio Transport Works

The stdio transport is implemented by calling `mcp.server.stdio.stdio_server()` from the official MCP Python SDK. Source: `src/mcp/server/stdio.py` (modelcontextprotocol/python-sdk):

```python
@asynccontextmanager
async def stdio_server(stdin=None, stdout=None):
    if not stdin:
        stdin = anyio.wrap_file(TextIOWrapper(sys.stdin.buffer, encoding="utf-8"))
    if not stdout:
        stdout = anyio.wrap_file(TextIOWrapper(sys.stdout.buffer, encoding="utf-8"))

    async def stdin_reader():
        async for line in stdin:
            # parse and send messages...

    async def stdout_writer():
        async for session_message in write_stream_reader:
            # serialize and write...

    async with anyio.create_task_group() as tg:
        tg.start_soon(stdin_reader)
        tg.start_soon(stdout_writer)
        yield read_stream, write_stream
```

When stdin reaches EOF (parent process closes its end of the pipe), `stdin_reader` exits, which closes the read stream, which causes the server's message loop to exit. **In theory** the process should terminate. **In practice,** GitHub issue modelcontextprotocol/python-sdk#2231 documents a bug: `anyio.wrap_file` reads via `readline()` in a worker thread that may not properly propagate EOF when the parent dies abruptly, causing orphaned processes under systemd.

### 1.3 How HTTP/Streamable-HTTP Transport Works

FastMCP's HTTP transport (aliased from `"streamable-http"` in FastMCP 2.3+) runs a long-lived uvicorn ASGI server:

```python
async def run_http_async(self, transport="http", host=None, port=None, ...):
    app = self.http_app(path=path, transport=transport, ...)
    config = uvicorn.Config(app, host=host, port=port, ...)
    server = uvicorn.Server(config)
    await server.serve()
```

This is a persistent HTTP server that:
- Listens on a TCP port (default 8000)
- Serves the MCP endpoint at `/mcp/` (configurable)
- Supports multiple concurrent clients
- Properly integrates with systemd's socket activation, health checks, and lifecycle management
- Uses the MCP Streamable HTTP protocol (spec 2025-06-18)

### 1.4 ASGI Mode (Production Recommended)

For production deployments, FastMCP recommends the ASGI application pattern:

```python
from fastmcp import FastMCP

mcp = FastMCP("MyServer")

@mcp.tool
def process(data: str) -> str:
    return f"Processed: {data}"

app = mcp.http_app()  # ASGI app for uvicorn/gunicorn
```

Run with:
```bash
uvicorn app:app --host 0.0.0.0 --port 8000 --workers 4
```

This enables:
- Health check endpoints (`@mcp.custom_route("/health", methods=["GET"])`)
- CORS middleware
- OAuth authentication
- Worker process management
- systemd service orchestration

---

## 2. Stdio Transport Under systemd — Analysis

### 2.1 The Orphan Process Problem

**Issue: `modelcontextprotocol/python-sdk#2231`** (confirmed, open)

When an MCP server using `transport="stdio"` has its parent process die (e.g., the MCP client exits, is killed, or crashes), the server process is orphaned and continues running indefinitely under systemd.

The root cause is in `src/mcp/server/stdio.py`:
- `anyio.wrap_file(TextIOWrapper(sys.stdin.buffer))` runs `readline()` in a worker thread
- When the parent's pipe is closed abruptly, the worker thread may not wake up or propagate EOF correctly
- The server remains alive, reparented to init/systemd, consuming resources

### 2.2 Systemd Incompatibility

Stdio servers under systemd face multiple issues:

1. **Stdin EOF ambiguity** — systemd may close stdin to a Type=simple service, causing premature exit
2. **No port binding** — stdio has no network presence; systemd can't monitor it meaningfully
3. **Restart loops** — if the server exits on stdin EOF, systemd immediately restarts it, creating a tight crash loop
4. **Session mismatch** — stdio is designed for one-shot client-spawns-server sessions, not daemon persistence

### 2.3 FastMCP Official Guidance

From `gofastmcp.com/deployment/running-server` (official docs):

> **STDIO transport**: "The client spawns a new server process for each session and manages its lifecycle. The server reads MCP messages from stdin and writes responses to stdout. **This is why STDIO servers don't stay running — they're started on-demand by the client.**"

> **HTTP transport**: "HTTP transport turns your MCP server into a web service accessible via a URL... **an HTTP server can handle multiple clients simultaneously.**"

This is explicit: stdio is **not designed** to be a persistent service.

---

## 3. Transport Recommendations for Guinevere MCP

### 3.1 Recommendation: Switch to Streamable HTTP

| Criterion | Stdio (current) | Streamable HTTP |
|---|---|---|
| Long-lived systemd service | ❌ Not suitable | ✅ Native support |
| Health checks | ❌ No | ✅ Custom routes |
| Multi-client | ❌ Single session | ✅ Concurrent |
| Zero-downtime restarts | ❌ Session breaks | ✅ Rolling deploys |
| Logging/monitoring | ❌ stdout only | ✅ Structured + health |
| Auth integration | ❌ No | ✅ OAuth, JWT, Bearer |
| MCP spec compliance | ✅ Stdio spec | ✅ Streamable HTTP spec (2025-06-18) |

### 3.2 Migration Path

**Phase 1 — Add HTTP transport alongside stdio:**
```python
# src/mcp/manager.py — current
mcp.run(transport="stdio")

# Change to:
mcp.run(transport="http", host="127.0.0.1", port=8090)
```

**Phase 2 — Production ASGI deployment with health checks:**
```python
# app.py
from fastmcp import FastMCP
from starlette.responses import JSONResponse

mcp = FastMCP("guinevere-mcp")

@mcp.tool
def process(data: str) -> str:
    # ... existing tool logic
    return result

@mcp.custom_route("/health", methods=["GET"])
async def health_check(request):
    return JSONResponse({"status": "healthy"})

app = mcp.http_app()
```

systemd service file:
```ini
[Unit]
Description=Guinevere MCP Server
After=network.target

[Service]
Type=simple
User=faizz
WorkingDirectory=/path/to/guinevere
ExecStart=/usr/bin/uvicorn app:app --host 127.0.0.1 --port 8090
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 3.3 Client-Side Proxy (if needed)

Claude Desktop and some MCP clients only support stdio transport natively. To bridge:

```json
{
  "mcpServers": {
    "guinevere": {
      "command": "npx",
      "args": ["-y", "@playmint/mcp-remote", "http://127.0.0.1:8090/mcp"]
    }
  }
}
```

This uses `mcp-remote` as a proxy: Claude talks stdio to mcp-remote, which forwards over HTTP to the server.

### 3.4 Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Client compatibility | Use `mcp-remote` proxy for stdio-only clients |
| Port conflict | Use a dedicated port (8090) bound to 127.0.0.1 |
| Auth exposure | Bind to 127.0.0.1, not 0.0.0.0; add auth layer for remote |
| Session state loss | Streamable HTTP sessions survive restarts with event store |
| Downtime on switch | Deploy ASGI app first, then switch clients to new endpoint; keep old stdio path until migration complete |

---

## 4. Sources

| Source | URL | Key Finding |
|---|---|---|
| FastMCP official docs — Running Server | https://gofastmcp.com/deployment/running-server | Stdio is session-scoped, not for persistent services; HTTP supports multi-client |
| FastMCP official docs — HTTP Deployment | https://gofastmcp.com/deployment/http | ASGI app pattern with uvicorn; health checks; scaling |
| FastMCP transport mixin source | https://github.com/PrefectHQ/fastmcp/blob/main/fastmcp_slim/fastmcp/server/mixins/transport.py | `run_async()` dispatches to `run_stdio_async()` or `run_http_async()` |
| MCP SDK stdio source | https://github.com/modelcontextprotocol/python-sdk/blob/main/src/mcp/server/stdio.py | anyio.wrap_file on stdin; async for line loop exits on EOF in theory |
| MCP SDK issue #2231 | https://github.com/modelcontextprotocol/python-sdk/issues/2231 | Confirmed: stdio server process survives parent death, orphaned under systemd |
| MCP spec — Transports | https://modelcontextprotocol.io/specification/2025-06-18/basic/transports | Stdio is client-spawns-subprocess; Streamable HTTP is persistent |
| Portkey — Converting stdio to Streamable HTTP | https://docs.portkey.ai/docs/guides/converting-stdio-to-streamable-http | Step-by-step conversion guide |
| FastMCP blog — Streamable HTTP 2.3 | https://jlowin.dev/blog/fastmcp-2-3-streamable-http | `"http"` is now alias for `"streamable-http"`; default for network deployments |
| Google Cloud Run — Deploy remote MCP | https://docs.cloud.google.com/run/docs/tutorials/deploy-remote-mcp-server | Production example using `run_async(transport="streamable-http")` |

---

## 5. Concrete Recommendation

**For Guinevere MCP with zero service disruption:**

1. **Switch transport from `stdio` to `http`** — change `mcp.run()` to `mcp.run(transport="http", host="127.0.0.1", port=8090)`. This is a one-line code change in `src/mcp/manager.py` (or wherever `FastMCP.run()` is called).

2. **If the server is already handling active clients**, deploy the ASGI pattern first behind uvicorn, then update the client configuration to point at the HTTP endpoint via `mcp-remote` proxy. The old stdio path and the new HTTP path can coexist during migration.

3. **systemd service** — modify the existing service unit to run `uvicorn` instead of `python -m src.mcp.manager`. Add health check endpoint for monitoring, `Restart=always`, and proper `After=network.target`.

4. **Do NOT attempt to keep stdio alive** — stdio under systemd is fundamentally unreliable due to the EOF shutdown bug (#2231) and architectural mismatch. No amount of `Restart=` configuration can fix the orphan process issue.

---

*Report prepared from official FastMCP source code (commit 3b8538e2), MCP Python SDK source (commit ac96f88), MCP specification 2025-06-18, and confirmed bug reports.*
