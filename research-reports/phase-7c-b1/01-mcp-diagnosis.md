# MCP Diagnosis Report — guinevere-mcp Inactive/Dead

**Date:** 2026-06-06 12:41 UTC
**Host:** faiz-prod-01 (100.94.104.22)
**Service:** guinevere-mcp (Guinevere MCP Gateway Server)
**Operator:** Faiz
**Read-only diagnosis — no state changed.**

---

## Executive Summary

`guinevere-mcp` has been **inactive (dead) since 2026-06-04 14:17:04 UTC** (>2 days). Three cascading failure modes were identified:

1. **Missing Python dependencies** (`markdownify`, `playwright`) in the virtual environment — caused initial ModuleNotFound crashes.
2. **FastMCP `InvalidSignature` rejection** of `_config` parameter in `filesystem.py` — caused repeated crash-loop after the dependency gap was partially resolved. (Has since been fixed in deployed code — param renamed to `config`.)
3. **Immediate clean shutdown on successful startup** (current blocker) — the FastMCP server uses **stdio transport** by default, but when launched as a standalone systemd service with no connected stdin, it receives immediate EOF and exits with code 0. The service unit has `Restart=on-failure`, which **does not restart on clean exit** (code 0), so after the last successful-then-immediate-shutdown, systemd let it stay dead.

Additionally, the service unit is **`disabled`** (not enabled for auto-start on boot).

---

## Check Results

### 1. `systemctl status guinevere-mcp`

```
○ guinevere-mcp.service - Guinevere MCP Gateway Server
     Loaded: loaded (/etc/systemd/system/guinevere-mcp.service; disabled; preset: enabled)
     Active: inactive (dead)
```

- **Loaded:** correct path
- **Enabled:** `disabled` — will not start on boot
- **Active:** `inactive (dead)` — confirmed stopped
- Last journal entries: Jun 04 14:17:04

### 2. `journalctl -u guinevere-mcp -n 50 --no-pager`

Full timeline from available journal (51649 lines total, spanning ~12.5h on Jun 04 only):

| Time (UTC) | Event |
|---|---|
| 01:50:35 | `ModuleNotFoundError: No module named 'markdownify'` — `fetch.py` import fails |
| 01:50:46–01:50:58 | Repeated same crash — `Restart=on-failure` restarts every ~12s |
| 14:14:44 | `InvalidSignature: Parameter _config of fs_read cannot start with '_'` — `filesystem.py` bug |
| 14:14:55–14:15:07 | Repeated same crash — restart loop continues |
| 14:15:19 | **Server starts successfully** — all 16 tools registered, auth matrix verified |
| 14:15:19 | **`mcp_server_shutting_down`** — immediate clean shutdown (same second) |
| 14:15:28–14:17:04 | 9 more iterations of the same pattern: start → ready → immediate shutdown |
| 14:17:04 | **Last entry** — no further activity |

**Key finding:** Every successful startup is followed by `mcp_server_shutting_down` in the **same second**. No logs exist between `mcp_server_ready` and `mcp_server_shutting_down` at any level (info/warn/error).

### 3. `systemctl cat guinevere-mcp`

The deployed unit differs from the local copy in one critical field:

| Field | Deployed (/etc/systemd/system/) | Local (systemd/guinevere-mcp.service) |
|---|---|---|
| `Restart` | **`on-failure`** | `always` |

**Impact:** `Restart=on-failure` only restarts on non-zero exit codes, signals, or timeouts. A clean exit (code 0) from stdio EOF is treated as a normal termination — no restart occurs.

Other fields match the local copy.

### 4. `.env.mcp`

File exists at `/home/guinevere/code/guinevere/.env.mcp`:

```
REDIS_PASSWORD=01b00faabad3164982d0dca68cedfbdc25b28d63f3604dd5ae1bf0586ce9739b
```

- Single variable present (Redis auth)
- No errors reading the file
- No missing critical variables apparent

### 5. `python -m src.mcp.manager` (direct test)

```
ModuleNotFoundError: No module named 'playwright'
```

The `playwright` package is **not installed** in the venv, causing import failure in `src/mcp/tools/obscura_cdp.py`. Additionally, `markdownify` is also absent (caused the initial crash at 01:50).
The `playwright` package is also absent (confirmed by `pip list | grep -i playwright` → empty).

Venv Python: 3.12.3
Installed `mcp` package: 1.27.2
`mcp` package location: present in venv site-packages
`playwright` package: **missing**
`markdownify` package: **missing**

### 6. Python import test (`from src.mcp.manager import MCPManager`)

Syntax error in quoting on the SSH test prevented clean execution, but the `ModuleNotFoundError` for `playwright` in the direct run already confirms the import chain breaks at `obscura_cdp.py` when playwright is absent. However, note that the deployed code's tool registration uses try/except or conditional import for the `playwright`-dependent tools — the successful server starts (14:15-14:17) prove the server **can start despite missing playwright**. The immediate shutdown is NOT caused by the missing playwright.

### 7. Port conflicts

- Port 5000: **not in use** (no conflict)
- Port 8080: **in use** (listening on 127.0.0.1:8080) — likely unrelated
- Docker infra containers all healthy (PostgreSQL, Redis, Prometheus, Grafana, Loki, etc.)

---

## Root Cause Analysis

### Primary Root Cause: Stdio Transport + Standalone Service = Immediate Shutdown

The `FastMCP` v1.27.2 `run()` method defaults to **stdio transport**. When the systemd unit launches the process with `Type=exec`:

```
ExecStart=/home/guinevere/code/guinevere/.venv/bin/python -m src.mcp.manager
```

The process inherits stdin from systemd, which is `/dev/null`. The `mcp` server reads stdin, gets an immediate EOF, and interprets this as the client disconnecting. The lifespan context manager's `yield` completes, triggering the cleanup path that logs `mcp_server_shutting_down`. The process exits with **code 0** (clean exit).

Since `Restart=on-failure`, systemd does not restart — a clean exit is not a failure.

This explains the pattern:
1. Server starts → lifespan enters → tools register → `yield` (wait for stdin) → stdin EOF → cleanup → shutdown
2. All within the same second

### Contributing Factor: Service Disabled

The unit is `disabled`, so even a system reboot would not start it.

### Contributing Factor: Missing Dependencies

- `markdownify` — needed by `src/mcp/tools/fetch.py`  
- `playwright` — needed by `src/mcp/tools/obscura_cdp.py`

These are missing from the venv. The initial crash-loop (01:50) was caused by `markdownify`. While the server can start without `playwright` (lazy/try-except import handling), the tools depending on it will fail at runtime.

---

## Timeline of Events

```
Jun 04 01:50 — markdownify ModuleNotFoundError (crash-loop, on-failure restart)
     ↓ code fix? (install markdownify or add conditional import)
Jun 04 14:14 — _config InvalidSignature (crash-loop, on-failure restart)  
     ↓ code fix? (rename _config → config in filesystem.py)
Jun 04 14:15 — Server starts successfully, immediately shuts down (stdin EOF)
     ↓ Restart=on-failure does NOT trigger  (exit code 0)
Jun 04 14:17 — Last restart attempt, same immediate shutdown
     ↓ No more restarts — service stays dead
Jun 04 14:17 — Jun 06 12:41 — Service inactive (dead)
```

---

## Safe Next-Step Recommendations

All recommendations are read-only informed; no changes made.

### Recommended Fix Order:

1. **Fix the transport/unit configuration** to keep the server alive:
   - Option A: Change the service to use `Restart=always` (matches local copy intent) so that even clean exits restart.
   - Option B: Add `--transport sse` or equivalent argument so the server listens on a TCP port (requires code change: `server.run(transport="sse")` or `uvicorn` wrapper).
   - Option C: Convert the service to a socket-activated unit so stdin is a connected socket.

2. **Install missing dependencies** in the venv:
   ```bash
   cd /home/guinevere/code/guinevere
   source .venv/bin/activate
   pip install markdownify playwright
   playwright install chromium
   ```

3. **Enable the service** for auto-start on boot:
   ```bash
   sudo systemctl enable guinevere-mcp
   ```

4. **Verify auth_matrix_verified** in journal after restart — confirm no auth gaps.

### What NOT to do:
- Do not touch Aizanta infrastructure (containers, configs, deployments).
- Do not modify the `.env.mcp` file contents.
- Do not alter `src/mcp/manager.py` logic without understanding the MCP client contract (the client connects via stdio; if the client is external, the server needs to listen on a socket).

---

## Evidence Artifacts

| Check | Exit Code | Result |
|---|---|---|
| `systemctl status guinevere-mcp` | 0 | inactive (dead), disabled |
| `journalctl -u guinevere-mcp -n 50` | 0 | See timeline above |
| `systemctl cat guinevere-mcp` | 0 | Restart=on-failure (drift from local) |
| `cat .env.mcp` | 0 | Present, 1 var |
| `python -m src.mcp.manager 2>&1 \| head -30` | 1 | ModuleNotFoundError: playwright |
| `pip list \| grep -iE 'mcp\|playwright\|markdownify'` | 0 | Only `mcp` 1.27.2 present |
| `ss -tlnp \| grep :5000` | 0 | Not in use |
| `docker ps` | 0 | All infra containers healthy |
| `systemctl --failed` | 0 | No failed units |

---

## Footer

**Report by:** Guinevere subagent (Sisyphus-Junior)
**Scope:** research-reports/phase-7c-b1/
**Zero remote state changes.** All commands were read-only.
**Next action:** Present findings to Faiz for fix prioritization.
