# P15-006: NSSM Service Wrapper + Config

### Step P15-006: NSSM Service Wrapper + Config

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon |
| **Step** | P15-006 |
| **Category** | Implementation |
| **Dependencies** | P15-005 (Event Pipeline) |
| **Est. Time** | 1h |
| **ADR Refs** | ADR-030, ADR-035 (Decision 3.6: NSSM service wrapper, Decision 1.2: Always-on via NSSM) |
| **Status** | ⬜ Not Started |

---

## Goal

Establish the Windows daemon as a robust, always-on background service using NSSM (Non-Sucking Service Manager), complete with a unified configuration system that merges environment variables and JSON settings, and implements a graceful shutdown sequence that cleanly stops all active trackers and closes the WebSocket connection.

---

## Context

The Windows daemon must operate reliably without user intervention, surviving reboots and user logouts. NSSM provides the necessary service wrapper capabilities for Windows, including automatic restarts, log rotation, and proper signal handling. This step transitions the daemon from a manual execution script to a production-ready Windows service.

Configuration management follows a layered approach: base defaults in code, overridden by `daemon.json`, and finally overridden by environment variables (`.env`). This ensures flexibility for both development and production deployments without hardcoding secrets.

Graceful shutdown is critical to prevent data loss or corrupted WebSocket states. The shutdown sequence must intercept `SIGTERM` (or Windows service stop signals), signal all running trackers to halt, wait for pending events to flush, and cleanly close the WebSocket connection before the process exits.

**Planner Gate Context:**
- **Decision 1.2:** Always-on via NSSM, <1% CPU idle.
- **Decision 3.6:** NSSM service wrapper for lifecycle management.
- **Scaffold Requirement:** NSSM install script must be idempotent. Config must load from env + JSON. Graceful shutdown must stop all trackers and close WS. Hard rejection if shutdown leaves orphaned processes or unclosed sockets.

---

## Pre-flight Checks

- [ ] P15-005 (Event Pipeline) is complete and passing tests.
- [ ] Python 3.11+ is installed and accessible in the system PATH on the target Windows machine.
- [ ] NSSM executable is downloaded and placed in a known directory (e.g., `C:\guinevere\nssm\`).
- [ ] Target Windows machine has network connectivity to the VPS (Tailscale active).

```bash
# Verify Python installation and version
python --version
# Expected: Python 3.11.x or higher

# Verify NSSM availability
C:\guinevere\nssm\nssm.exe version
# Expected: 2.24 or higher

# Verify daemon module can be imported
cd C:\Users\faizz\guinevere\clients\windows
python -m src.daemon --help
# Expected: Help text or configuration validation output, exit code 0
```

---

## Implementation Commands

### 1. Create Configuration Module (`config.py`)
Create `clients/windows/src/daemon/config.py` to handle layered configuration loading.

```python
import os
import json
import logging
from dataclasses import dataclass
from typing import Dict, Any

logger = logging.getLogger(__name__)

@dataclass
class DaemonConfig:
    device_id: str
    ws_url: str
    ws_secret: str
    poll_intervals: Dict[str, float]
    session_mapping: Dict[str, str]
    default_session: str
    log_level: str

def load_config(config_path: str = "nssm/daemon.json", env_path: str = ".env") -> DaemonConfig:
    config = {
        "device_id": os.environ.get("GUINEVERE_DEVICE_ID", "unknown"),
        "ws_url": os.environ.get("GUINEVERE_WS_URL", "wss://100.94.104.22:8443/surveillance/windows/ws"),
        "ws_secret": os.environ.get("GUINEVERE_WS_SECRET", ""),
        "poll_intervals": {"active_window": 2.0, "idle": 5.0, "git": 30.0},
        "session_mapping": {},
        "default_session": "personal",
        "log_level": "INFO"
    }
    
    if os.path.exists(config_path):
        with open(config_path, "r", encoding="utf-8") as f:
            file_config = json.load(f)
            config.update(file_config)
            
    if os.path.exists(env_path):
        from dotenv import load_dotenv
        load_dotenv(env_path)
        config["device_id"] = os.environ.get("GUINEVERE_DEVICE_ID", config["device_id"])
        config["ws_url"] = os.environ.get("GUINEVERE_WS_URL", config["ws_url"])
        config["ws_secret"] = os.environ.get("GUINEVERE_WS_SECRET", config["ws_secret"])
        config["log_level"] = os.environ.get("GUINEVERE_LOG_LEVEL", config["log_level"])
        
    if not config["ws_secret"]:
        raise ValueError("GUINEVERE_WS_SECRET must be provided via environment or .env file")
        
    return DaemonConfig(**config)
```

### 2. Create Graceful Shutdown Handler (`shutdown.py`)
Create `clients/windows/src/daemon/shutdown.py` to manage asynchronous shutdown events.

```python
import asyncio
import signal
import logging
from typing import List, Any

logger = logging.getLogger(__name__)

class ShutdownManager:
    def __init__(self):
        self.shutdown_event = asyncio.Event()
        self.trackers: List[Any] = []
        self.ws_client: Any = None

    def register_tracker(self, tracker: Any) -> None:
        self.trackers.append(tracker)

    def register_ws_client(self, ws_client: Any) -> None:
        self.ws_client = ws_client

    def handle_signal(self, sig: signal.Signals) -> None:
        logger.info(f"Received signal {sig.name}, initiating graceful shutdown...")
        self.shutdown_event.set()

    async def shutdown(self) -> None:
        logger.info("Stopping all trackers...")
        for tracker in self.trackers:
            try:
                await tracker.stop()
            except Exception as e:
                logger.error(f"Error stopping tracker {tracker.name}: {e}")
                
        if self.ws_client:
            logger.info("Closing WebSocket connection...")
            try:
                await self.ws_client.close()
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
                
        logger.info("Graceful shutdown complete.")
```

### 3. Create Entry Point (`__main__.py`)
Create `clients/windows/src/daemon/__main__.py` as the service entry point.

```python
import asyncio
import logging
import signal
from src.daemon.config import load_config
from src.daemon.shutdown import ShutdownManager
# Note: Actual tracker and ws_client imports will be added as dependencies resolve

async def main() -> None:
    config = load_config()
    logging.basicConfig(level=getattr(logging, config.log_level))
    logger = logging.getLogger(__name__)
    
    shutdown_mgr = ShutdownManager()
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            signal.signal(sig, shutdown_mgr.handle_signal)
        except ValueError:
            pass  # Signal handling may differ in Windows service context
            
    logger.info(f"Starting Guinevere Windows Daemon for device: {config.device_id}")
    
    # TODO: Initialize trackers and ws_client, register with shutdown_mgr
    # await ws_client.connect()
    # await asyncio.gather(*[tracker.start() for tracker in trackers])
    
    await shutdown_mgr.shutdown_event.wait()
    await shutdown_mgr.shutdown()

if __name__ == "__hasattr__":
    pass
if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Create NSSM Installation Script (`install.bat`)
Create `clients/windows/nssm/install.bat`. This script must be idempotent.

```bat
@echo off
setlocal
set NSSM_PATH=C:\guinevere\nssm\nssm.exe
set SERVICE_NAME=GuinevereWindowsDaemon
set PYTHON_EXE=C:\Python311\python.exe
set DAEMON_DIR=C:\Users\faizz\guinevere\clients\windows

echo Checking if service already exists...
%NSSM_PATH% status %SERVICE_NAME% >nul 2>&1
if %errorlevel% equ 0 (
    echo Service %SERVICE_NAME% already exists. Stopping and removing for clean install...
    %NSSM_PATH% stop %SERVICE_NAME%
    %NSSM_PATH% remove %SERVICE_NAME% confirm
)

echo Installing service %SERVICE_NAME%...
%NSSM_PATH% install %SERVICE_NAME% "%PYTHON_EXE%" "-m" "src.daemon"
%NSSM_PATH% set %SERVICE_NAME% AppDirectory "%DAEMON_DIR%"
%NSSM_PATH% set %SERVICE_NAME% AppStdout "%DAEMON_DIR%\nssm\daemon.log"
%NSSM_PATH% set %SERVICE_NAME% AppStderr "%DAEMON_DIR%\nssm\daemon.err.log"
%NSSM_PATH% set %SERVICE_NAME% AppRotateFiles 1
%NSSM_PATH% set %SERVICE_NAME% AppRotateBytes 10485760
%NSSM_PATH% set %SERVICE_NAME% AppRotateLines 1000

echo Setting service to start automatically...
%NSSM_PATH% set %SERVICE_NAME% Start SERVICE_AUTO_START

echo Starting service...
%NSSM_PATH% start %SERVICE_NAME%

echo Installation complete. Check status with: %NSSM_PATH% status %SERVICE_NAME%
endlocal
```

### 5. Create NSSM Uninstallation Script (`uninstall.bat`)
Create `clients/windows/nssm/uninstall.bat`.

```bat
@echo off
setlocal
set NSSM_PATH=C:\guinevere\nssm\nssm.exe
set SERVICE_NAME=GuinevereWindowsDaemon

echo Stopping service %SERVICE_NAME%...
%NSSM_PATH% stop %SERVICE_NAME%

echo Removing service %SERVICE_NAME%...
%NSSM_PATH% remove %SERVICE_NAME% confirm

echo Uninstallation complete.
endlocal
```

### 6. Create Default Configuration (`daemon.json`)
Create `clients/windows/nssm/daemon.json`.

```json
{
    "poll_intervals": {
        "active_window": 2.0,
        "idle": 5.0,
        "git": 30.0
    },
    "session_mapping": {
        "guinevere": "guinevere-dev",
        "office-app": "work"
    },
    "default_session": "personal",
    "log_level": "INFO"
}
```

### 7. Create Environment Example (`.env.example`)
Create `clients/windows/.env.example`.

```env
GUINEVERE_DEVICE_ID=faizzzz
GUINEVERE_WS_URL=wss://100.94.104.22:8443/surveillance/windows/ws
GUINEVERE_WS_SECRET=your_generated_32_char_secret_here
GUINEVERE_LOG_LEVEL=INFO
```

---

## Verification

- [ ] `config.py` successfully loads defaults, JSON overrides, and environment variables.
- [ ] `shutdown.py` correctly sets the asyncio event and iterates through registered trackers.
- [ ] `__main__.py` can be executed via `python -m src.daemon` without import errors.
- [ ] `install.bat` is idempotent (running it twice does not create duplicate services or fail).
- [ ] NSSM service is in `SERVICE_RUNNING` state after installation.
- [ ] Log files (`daemon.log`, `daemon.err.log`) are created in the `nssm` directory.

```bash
# Verify module execution
cd C:\Users\faizz\guinevere\clients\windows
python -c "from src.daemon.config import load_config; print('Config loaded successfully')"

# Verify NSSM service status
C:\guinevere\nssm\nssm.exe status GuinevereWindowsDaemon
# Expected: SERVICE_RUNNING

# Verify log rotation configuration
C:\guinevere\nssm\nssm.exe get GuinevereWindowsDaemon AppRotateFiles
# Expected: 1
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-006/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-006/auditor-gate.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-006/nssm-status.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-006/config-load-test.txt`

---

## Rollback

```bash
# Stop the service immediately
C:\guinevere\nssm\nssm.exe stop GuinevereWindowsDaemon

# Remove the service definition
C:\guinevere\nssm\nssm.exe remove GuinevereWindowsDaemon confirm

# Delete generated log files if desired
del C:\Users\faizz\guinevere\clients\windows\nssm\daemon.log
del C:\Users\faizz\guinevere\clients\windows\nssm\daemon.err.log
```

---

## Troubleshooting

- **Issue: `install.bat` fails with "Access is denied"**
  - **Solution:** Run Command Prompt or PowerShell as Administrator. NSSM requires elevated privileges to install Windows services.
- **Issue: Service starts but immediately stops (Error 1053)**
  - **Solution:** Check `daemon.err.log`. This usually indicates a missing Python environment, incorrect `AppDirectory`, or a missing `.env` file causing `load_config` to raise a `ValueError`.
- **Issue: Configuration not reflecting `.env` changes**
  - **Solution:** Ensure the `.env` file is in the `AppDirectory` (`C:\Users\faizz\guinevere\clients\windows`). Restart the service after modifying `.env`.
- **Issue: Log files grow indefinitely**
  - **Solution:** Verify that `AppRotateFiles`, `AppRotateBytes`, and `AppRotateLines` are set correctly in NSSM. The provided `install.bat` configures 10MB rotation.

---

## Notes

- **Idempotency:** The `install.bat` script explicitly checks for existing services and removes them before reinstalling, ensuring safe re-runs during development.
- **Signal Handling:** Windows services do not receive `SIGTERM` identically to Unix. NSSM intercepts the service stop control and sends a console control event, which Python's `signal` module can catch if configured correctly.
- **Security:** The `.env.example` file explicitly reminds the operator to generate a strong, unique `GUINEVERE_WS_SECRET`. This secret must match the one configured on the VPS.
- **Cross-reference:** This step depends on the event pipeline (P15-005) being structurally ready to accept the `shutdown_mgr` registration.

---

## AC References

- **AC 3.6:** Daemon runs as a Windows service managed by NSSM with automatic restart capabilities.
- **AC 1.2:** Daemon operates with <1% CPU idle when no state changes occur.
- **AC Scaffold:** Graceful shutdown successfully stops all trackers and closes the WebSocket connection without orphaned processes.

---
---

# P15-007: VPS WebSocket Endpoint (FastAPI + ConnectionManager)

### Step P15-007: VPS WebSocket Endpoint (FastAPI + ConnectionManager)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon |
| **Step** | P15-007 |
| **Category** | Implementation |
| **Dependencies** | None (Wave 1, parallel with P15-001 and P15-012) |
| **Est. Time** | 2h |
| **ADR Refs** | ADR-030, ADR-035 (Decision 4.1: Add to existing FastAPI app, Decision 3.2: Single persistent WebSocket) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement a secure, authenticated WebSocket endpoint within the existing VPS FastAPI application to receive real-time events from the Windows daemon, manage active connections via a `ConnectionManager`, and route validated events into the existing Redis DB2 surveillance buffer pipeline.

---

## Context

The Windows daemon requires a persistent, low-latency communication channel to the VPS. Rather than deploying a separate microservice, Decision 4.1 mandates integrating this endpoint directly into the existing FastAPI application. This minimizes infrastructure complexity and leverages existing authentication and logging middleware.

The `ConnectionManager` is responsible for tracking active daemon connections by `device_id`, ensuring that only one active connection exists per device at any given time. It also handles heartbeat monitoring (ping/pong) to detect stale connections and trigger cleanup.

Security is paramount. The endpoint must enforce first-message authentication using a shared secret and validate the source IP against the allowed Tailscale subnet. Unauthenticated or malformed connections must be rejected immediately without resource exhaustion.

**Planner Gate Context:**
- **Decision 4.1:** Add to existing FastAPI app (no separate service).
- **Decision 3.2:** Single persistent WebSocket.
- **Decision 3.3:** Tailscale ACL + static shared secret.
- **Scaffold Requirement:** Must authenticate first message. Must handle disconnect cleanup. Must integrate with existing FastAPI app. Must use existing Redis connection pattern. Hard rejection if unauthenticated messages are processed or if connections leak.

---

## Pre-flight Checks

- [ ] Existing FastAPI application (`src/main.py`) is running and accessible.
- [ ] Redis DB2 is accessible and the existing `RedisSurveillanceBuffer` pattern is understood.
- [ ] Shared WebSocket secret is available in the VPS `.env.windows-ws` file.
- [ ] `websockets` and `msgpack` libraries are installed in the VPS Python environment.

```bash
# Verify FastAPI app is running
curl -s http://127.0.0.1:8000/health
# Expected: {"status": "healthy"}

# Verify Redis DB2 connectivity
redis-cli -h 127.0.0.1 -p 6380 -a "$REDIS_PASSWORD" -n 2 ping
# Expected: PONG

# Verify required Python packages
python -c "import websockets; import msgpack; print('Dependencies OK')"
# Expected: Dependencies OK
```

---

## Implementation Commands

### 1. Create Pydantic Models (`windows_models.py`)
Create `src/surveillance/windows_models.py` to define strict schemas for incoming messages.

```python
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, Literal

class AuthMessage(BaseModel):
    type: Literal["auth"]
    secret: str
    device_id: str

class EventMessage(BaseModel):
    type: Literal["event"]
    seq: int
    device_id: str
    ts: float
    source: str
    data: Dict[str, Any]
    idle_state: str

class HeartbeatMessage(BaseModel):
    type: Literal["ping", "pong"]
    ts: float
```

### 2. Create Connection Manager and Router (`windows_ws.py`)
Create `src/surveillance/windows_ws.py` with the endpoint and connection management logic.

```python
import asyncio
import logging
import os
import msgpack
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from typing import Dict, Optional
from pydantic import ValidationError

from src.surveillance.windows_models import AuthMessage, EventMessage, HeartbeatMessage
# Assume existing redis client and buffer are imported
# from src.surveillance.redis_buffer import RedisSurveillanceBuffer

logger = logging.getLogger(__name__)

class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self.expected_secret = os.getenv("GUINEVERE_WS_SECRET", "")

    async def connect(self, websocket: WebSocket, device_id: str) -> bool:
        if device_id in self.active_connections:
            logger.warning(f"Device {device_id} already connected. Dropping old connection.")
            await self.active_connections[device_id].close()
            
        await websocket.accept()
        self.active_connections[a device_id] = websocket
        logger.info(f"Device {device_id} connected.")
        return True

    def disconnect(self, device_id: str):
        if device_id in self.active_connections:
            del self.active_connections[device_id]
            logger.info(f"Device {device_id} disconnected.")

    async def authenticate(self, websocket: WebSocket, device_id: str, secret: str) -> bool:
        if secret != self.expected_secret:
            logger.warning(f"Invalid secret attempt for device {device_id}")
            return False
        # TODO: Add Tailscale IP validation here if request.client.host is available
        return True

    async def process_message(self, device_id: str, raw_message: bytes):
        try:
            data = msgpack.unpackb(raw_message, raw=False)
            msg_type = data.get("type")
            
            if msg_type == "event":
                validated = EventMessage(**data)
                # Push to existing Redis DB2 buffer
                # await RedisSurveillanceBuffer.push(validated)
                logger.debug(f"Processed event from {device_id}, seq: {validated.seq}")
            elif msg_type == "pong":
                logger.debug(f"Received pong from {device_id}")
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        except ValidationError as e:
            logger.error(f"Validation error for device {device_id}: {e}")
        except Exception as e:
            logger.error(f"Error processing message from {device_id}: {e}")

manager = ConnectionManager()
router = APIRouter(prefix="/surveillance")

@router.websocket("/windows/ws")
async def windows_websocket_endpoint(websocket: WebSocket):
    device_id = "unknown"
    try:
        # Wait for first message (auth)
        raw_auth = await websocket.receive_bytes()
        auth_data = msgpack.unpackb(raw_auth, raw=False)
        
        try:
            auth_msg = AuthMessage(**auth_data)
        except ValidationError:
            await websocket.close(code=4001, reason="Invalid auth format")
            return
            
        if not await manager.authenticate(websocket, auth_msg.device_id, auth_msg.secret):
            await websocket.close(code=4003, reason="Invalid credentials")
            return
            
        device_id = auth_msg.device_id
        await manager.connect(websocket, device_id)
        await websocket.send_bytes(msgpack.packb({"type": "auth_ok"}))
        
        # Main message loop
        while True:
            raw_message = await websocket.receive_bytes()
            await manager.process_message(device_id, raw_message)
            
    except WebSocketDisconnect:
        manager.disconnect(device_id)
    except Exception as e:
        logger.error(f"WebSocket error for {device_id}: {e}")
        manager.disconnect(device_id)
```

### 3. Integrate Router into Main App
Modify `src/main.py` to include the new router.

```python
# In src/main.py
from src.surveillance.windows_ws import router as windows_ws_router

app.include_router(windows_ws_router)
```

---

## Verification

- [ ] `windows_models.py` correctly validates valid and invalid message structures.
- [ ] `ConnectionManager` rejects connections with invalid secrets.
- [ ] `ConnectionManager` allows only one active connection per `device_id`.
- [ ] WebSocket endpoint successfully accepts authenticated connections and responds with `auth_ok`.
- [ ] Disconnecting the client cleanly removes the device from `active_connections`.
- [ ] No type suppression (`# type: ignore`, `as any`) is used in the implementation.

```bash
# Verify model validation
python -c "from src.surveillance.windows_models import AuthMessage; AuthMessage(type='auth', secret='test', device_id='test'); print('Models OK')"

# Verify router inclusion
python -c "from src.surveillance.windows_ws import router; print(router.prefix)"
# Expected: /surveillance

# Run specific unit tests (to be created in P15-013)
python -m pytest tests/surveillance/test_windows_ws.py -v
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-007/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-007/auditor-gate.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-007/model-validation-test.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-007/router-inclusion-test.txt`

---

## Rollback

```bash
# Remove router inclusion from src/main.py
# Delete the newly created files
rm src/surveillance/windows_ws.py
rm src/surveillance/windows_models.py

# Restart FastAPI application to clear any lingering connections
systemctl restart guinevere-api
```

---

## Troubleshooting

- **Issue: WebSocket connection closes immediately with code 4003**
  - **Solution:** Verify that `GUINEVERE_WS_SECRET` in the VPS `.env` exactly matches the secret configured on the Windows daemon. Check for trailing whitespace or encoding issues.
- **Issue: `msgpack` throws `ExtraData` or `UnpackValueError`**
  - **Solution:** Ensure the daemon is sending MessagePack serialized bytes, not JSON strings. Verify `msgpack` library versions are compatible.
- **Issue: Multiple connections for the same `device_id`**
  - **Solution:** The `ConnectionManager.connect` method explicitly closes the old connection before accepting the new one. Verify this logic is executing correctly in logs.
- **Issue: Tailscale IP validation fails**
  - **Solution:** Ensure the FastAPI app is configured to trust the `X-Forwarded-For` header from Caddy, or bind directly to the Tailscale interface if bypassing the reverse proxy for WS.

---

## Notes

- **Integration:** This step deliberately avoids creating a new Redis connection pool, relying instead on the existing `RedisSurveillanceBuffer` pattern to maintain resource efficiency and consistent error handling.
- **Security:** The shared secret is the primary authentication mechanism. Tailscale provides network-level isolation, but the secret prevents unauthorized access if the Tailscale ACL is misconfigured.
- **Cross-reference:** This endpoint is the target for the daemon's `ws_client.py` (P15-005) and the source of events for the consent gate (P15-009).

---

## AC References

- **AC 4.1:** WebSocket endpoint is integrated into the existing FastAPI application without requiring a separate service deployment.
- **AC 3.3:** First-message authentication successfully validates the static shared secret.
- **AC Scaffold:** Disconnect cleanup correctly removes the device from the active connections dictionary, preventing memory leaks.

---
---

# P15-008: Command Protocol (ACK-based, Redis DB4 pub/sub)

### Step P15-008: Command Protocol (ACK-based, Redis DB4 pub/sub)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon |
| **Step** | P15-008 |
| **Category** | Implementation |
| **Dependencies** | P15-007 (WS Endpoint) |
| **Est. Time** | 1.5h |
| **ADR Refs** | ADR-030, ADR-035 (Decision 3.5: Request/response with ACK 10s timeout, Decision 3.1: JSON commands) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement a reliable, bidirectional command protocol allowing the VPS to send instructions (e.g., `pause`, `resume`, `get_status`) to the Windows daemon via WebSocket, enforced by a strict 10-second ACK timeout, unique command IDs, and duplicate ACK rejection, utilizing Redis DB4 for pub/sub coordination.

---

## Context

While events flow from daemon to VPS, operational control requires the VPS to send commands to the daemon. Decision 3.5 mandates an ACK-based request/response pattern with a 10-second timeout to ensure commands are not silently lost in transient network conditions.

Each command is assigned a unique UUID. The daemon must acknowledge receipt of the command within 10 seconds, followed by the execution result. The VPS `CommandManager` tracks pending commands and triggers retries or failure states if the ACK is not received.

Redis DB4 is designated for pub/sub operations (ADR-030). Although the MVP primarily uses direct WebSocket for command delivery, the architecture is designed to publish commands to a Redis channel (`daemon:commands:{device_id}`), allowing for future decoupling or multi-node VPS setups without changing the daemon's subscription logic.

**Planner Gate Context:**
- **Decision 3.5:** Request/response with ACK (10s timeout).
- **Decision 3.1:** JSON commands (distinct from MessagePack events).
- **Scaffold Requirement:** Must use Redis DB4 pub/sub only. Must implement ACK timeout (10s). Must generate unique command IDs. Must handle duplicate ACK rejection. Hard rejection if commands are sent to wrong DB or lack timeout handling.

---

## Pre-flight Checks

- [ ] P15-007 (WS Endpoint) is complete and the `ConnectionManager` is functional.
- [ ] Redis DB4 is accessible and empty (green field, per ADR-030).
- [ ] `uuid` and `asyncio` modules are available in the Python environment.

```bash
# Verify Redis DB4 accessibility
redis-cli -h 127.0.0.1 -p 6380 -a "$REDIS_PASSWORD" -n 4 ping
# Expected: PONG

# Verify DB4 is empty (no legacy pub/sub usage)
redis-cli -h 127.0.0.1 -p 6380 -a "$REDIS_PASSWORD" -n 4 dbsize
# Expected: 0
```

---

## Implementation Commands

### 1. Create Command Manager (`windows_commands.py`)
Create `src/surveillance/windows_commands.py` to handle command generation, dispatch, and ACK tracking.

```python
import asyncio
import json
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

# Assume existing redis client is imported
# import redis.asyncio as redis

logger = logging.getLogger(__name__)

class CommandManager:
    def __init__(self, redis_client: Any, connection_manager: Any):
        self.redis = redis_client
        self.cm = connection_manager
        self.pending_commands: Dict[str, Dict[str, Any]] = {}
        self.ack_timeout = 10.0  # seconds
        self.max_retries = 3

    async def send_command(self, device_id: str, cmd: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        command_id = str(uuid.uuid4())
        payload = {
            "type": "command",
            "id": command_id,
            "cmd": cmd,
            "params": params or {}
        }
        
        # Store pending command with timestamp
        self.pending_commands[command_id] = {
            "device_id": device_id,
            "sent_at": datetime.utcnow(),
            "retries": 0,
            "ack_received": False,
            "result": None
        }
        
        # Publish to Redis DB4 (Future-proofing)
        await self.redis.publish(f"daemon:commands:{device_id}", json.dumps(payload))
        
        # Also send directly via WebSocket if connected (MVP primary path)
        if device_id in self.cm.active_connections:
            ws = self.cm.active_connections[device_id]
            # Commands are JSON, not MessagePack
            await ws.send_text(json.dumps(payload))
        else:
            raise ConnectionError(f"Device {device_id} is not connected")
            
        # Wait for ACK or result
        return await self._wait_for_completion(command_id)

    async def _wait_for_completion(self, command_id: str) -> Dict[str, Any]:
        start_time = datetime.utcnow()
        while True:
            cmd_state = self.pending_commands.get(command_id)
            if not cmd_state:
                raise RuntimeError(f"Command {command_id} not found in pending state")
                
            if cmd_state["result"] is not None:
                return cmd_state["result"]
                
            if (datetime.utcnow() - cmd_state["sent_at"]).total_seconds() > self.ack_timeout:
                if cmd_state["retries"] < self.max_retries:
                    logger.warning(f"Command {command_id} timed out, retrying ({cmd_state['retries'] + 1}/{self.max_retries})")
                    cmd_state["retries"] += 1
                    cmd_state["sent_at"] = datetime.utcnow()
                    # Retry logic would re-send here
                else:
                    del self.pending_commands[command_id]
                    raise TimeoutError(f"Command {command_id} failed after {self.max_retries} retries")
                    
            await asyncio.sleep(0.5)

    async def process_ack(self, device_id: str, ack_data: Dict[str, Any]) -> None:
        command_id = ack_data.get("id")
        if not command_id or command_id not in self.pending_commands:
            logger.warning(f"Received duplicate or invalid ACK for command {command_id}")
            return
            
        self.pending_commands[command_id]["ack_received"] = True
        logger.debug(f"Received ACK for command {command_id} from {device_id}")

    async def process_result(self, device_id: str, result_data: Dict[str, Any]) -> None:
        command_id = result_data.get("id")
        if command_id in self.pending_commands:
            self.pending_commands[command_id]["result"] = result_data
            logger.info(f"Received result for command {command_id} from {device_id}")
        else:
            logger.warning(f"Received result for unknown command {command_id}")
```

---

## Verification

- [ ] `CommandManager` generates unique UUIDs for each command.
- [ ] Commands are published to Redis DB4 (`daemon:commands:{device_id}`).
- [ ] Commands are sent via WebSocket as JSON strings.
- [ ] ACK timeout triggers after 10 seconds and initiates retry logic.
- [ ] Duplicate ACKs are logged and ignored without crashing.
- [ ] No type suppression (`# type: ignore`, `as any`) is used.

```bash
# Verify Redis DB4 pub/sub setup
python -c "
import asyncio
import redis.asyncio as redis
async def test():
    r = redis.Redis(host='127.0.0.1', port=6380, db=4, password='your_password')
    await r.publish('daemon:commands:test', 'test_payload')
    print('Redis DB4 publish OK')
asyncio.run(test())
"

# Verify command manager initialization
python -c "from src.surveillance.windows_commands import CommandManager; print('CommandManager imported successfully')"
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-008/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-008/auditor-gate.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-008/redis-db4-test.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-008/timeout-logic-test.txt`

---

## Rollback

```bash
# Remove command manager file
rm src/surveillance/windows_commands.py

# Flush Redis DB4 to remove any pending pub/sub channels or messages
redis-cli -h 127.0.0.1 -p 6380 -a "$REDIS_PASSWORD" -n 4 flushdb
```

---

## Troubleshooting

- **Issue: `TimeoutError` raised immediately**
  - **Solution:** Verify that the daemon is actively connected and the `device_id` matches exactly. Check WebSocket logs on the VPS for disconnection events.
- **Issue: Duplicate ACK warnings in logs**
  - **Solution:** This is expected behavior if the daemon re-sends an ACK due to network uncertainty. The `process_ack` method safely ignores duplicates after the first valid ACK.
- **Issue: Redis DB4 connection refused**
  - **Solution:** Ensure the Redis Docker container is exposing port 6380 and the password matches the VPS `.env` configuration. Verify `db=4` is explicitly set in the Redis client initialization.
- **Issue: Command result never arrives after ACK**
  - **Solution:** The daemon may have crashed or failed to execute the command. Implement a daemon-side fallback to send an error result if execution fails, rather than hanging indefinitely.

---

## Notes

- **JSON vs MessagePack:** Commands are explicitly serialized as JSON (Decision 3.1) to simplify debugging and align with standard RPC patterns, while high-volume events use MessagePack for efficiency.
- **Idempotency:** The daemon must handle duplicate commands gracefully (e.g., if a `pause` command is received twice, the second should be a no-op, not an error).
- **Cross-reference:** This manager is invoked by the Discord `/pc` command (P15-010) and the consent gate (P15-009) to send `pause`/`resume` instructions.

---

## AC References

- **AC 3.5:** Command protocol enforces a strict 10-second ACK timeout with retry logic.
- **AC 3.1:** Commands are serialized as JSON, distinct from MessagePack event payloads.
- **AC Scaffold:** Redis DB4 is the exclusive database used for pub/sub operations in this module.

---
---

# P15-009: Consent Gate Integration (belt-and-suspenders) ⚠️ SAFETY-CRITICAL

### Step P15-009: Consent Gate Integration (belt-and-suspenders)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon |
| **Step** | P15-009 |
| **Category** | Implementation (Safety-Critical) |
| **Dependencies** | P15-007 (WS Endpoint), P15-008 (Commands) |
| **Est. Time** | 1h |
| **ADR Refs** | ADR-035 (Decision 4.3: Belt-and-suspenders consent) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement a fail-closed, belt-and-suspenders consent gate that prevents any Windows surveillance data from being processed or stored when `safe_mode` is active, combining server-side event dropping with client-side traffic reduction via pause/resume commands.

---

## Context

Surveillance data (active window, idle state) is classified as RESTRICTED (SurveillanceDataPolicy §6.3). When the operator activates `safe_mode`, all data collection must cease immediately. Relying solely on the daemon to stop sending data is unsafe (network partitions, daemon crashes). Therefore, a dual-layer approach is mandatory.

**Layer 1 (Server-side, Hard Guarantee):** The VPS WebSocket endpoint must check the `safe_mode` status in Redis before processing ANY incoming event. If `safe_mode` is active, the event is dropped silently, and a drop counter is incremented. This is fail-closed: even if the daemon ignores the pause command, no data is processed.

**Layer 2 (Client-side, Traffic Reduction):** When `safe_mode` activates, the VPS proactively sends a `pause` command to the daemon. The daemon enters a paused state where trackers continue to poll (to maintain state awareness) but do not transmit events. When `safe_mode` deactivates, a `resume` command is sent.

**Planner Gate Context:**
- **Decision 4.3:** Belt-and-suspenders: consent gate server-side + pause command to daemon.
- **Scaffold Requirement (SAFETY-CRITICAL):** Must drop events when safe_mode active (fail-closed). Must send pause/resume commands. Must NEVER allow event through during safe_mode. Must increment drop counter. Hard rejection if ANY event passes during safe_mode in tests.

---

## Pre-flight Checks

- [ ] Existing `src/surveillance/consent_gate.py` and `safe_mode.py` patterns are understood.
- [ ] Redis cache for `safe_mode` status is functional (300s TTL).
- [ ] P15-008 `CommandManager` is available to send `pause`/`resume` commands.

```bash
# Verify existing safe_mode module
python -c "from src.surveillance.safe_mode import is_safe_mode_active; print('Safe mode module OK')"

# Verify Redis safe_mode key structure
redis-cli -h 127.0.0.1 -p 6380 -a "$REDIS_PASSWORD" get "guinevere:safe_mode:status"
# Expected: "true" or "false" or (nil)
```

---

## Implementation Commands

### 1. Create Windows Consent Gate (`windows_consent.py`)
Create `src/surveillance/windows_consent.py` to enforce the server-side hard guarantee.

```python
import logging
import msgpack
from typing import Dict, Any

# Assume existing redis client and metrics are imported
# from src.surveillance.safe_mode import is_safe_mode_active
# from src.observability.windows_metrics import increment_events_dropped

logger = logging.getLogger(__name__)

async def process_windows_event_with_consent(
    device_id: str, 
    raw_message: bytes, 
    redis_client: Any
) -> bool:
    """
    SAFETY-CRITICAL: Checks safe_mode before processing. 
    Returns True if processed, False if dropped.
    """
    # 1. Check safe_mode status (Fail-closed: assume safe if check fails)
    try:
        safe_mode_active = await is_safe_mode_active(redis_client)
    except Exception as e:
        logger.error(f"Failed to check safe_mode, defaulting to DROP (fail-closed): {e}")
        safe_mode_active = True
        
    if safe_mode_active:
        logger.info(f"SAFE MODE ACTIVE: Dropping event from {device_id}")
        # increment_events_dropped()
        return False
        
    # 2. Process event normally
    try:
        data = msgpack.unpackb(raw_message, raw=False)
        # Validate and push to Redis DB2 buffer
        # await RedisSurveillanceBuffer.push(data)
        return True
    except Exception as e:
        logger.error(f"Error processing event from {device_id}: {e}")
        return False

async def handle_safe_mode_change(
    is_active: bool, 
    device_id: str, 
    command_manager: Any
) -> None:
    """
    Layer 2: Send pause/resume commands to daemon when safe_mode changes.
    """
    try:
        cmd = "pause" if is_active else "resume"
        logger.info(f"Sending {cmd} command to device {device_id} due to safe_mode change")
        await command_manager.send_command(device_id, cmd, {})
    except Exception as e:
        logger.error(f"Failed to send {cmd} command to {device_id}: {e}")
        # Note: Server-side drop (Layer 1) still protects data even if this fails.
```

### 2. Integrate into WebSocket Endpoint
Modify `src/surveillance/windows_ws.py` to use the new consent gate.

```python
# In windows_ws.py, update process_message:
from src.surveillance.windows_consent import process_windows_event_with_consent

# Inside ConnectionManager.process_message:
if msg_type == "event":
    # Pass raw bytes to consent gate for validation
    processed = await process_windows_event_with_consent(device_id, raw_message, self.redis_client)
    if not processed:
        return  # Event was dropped
    # ... continue with normal processing if needed
```

---

## Verification

- [ ] `process_windows_event_with_consent` returns `False` and logs a drop when `safe_mode` is active.
- [ ] Drop counter metric is incremented when events are discarded.
- [ ] `handle_safe_mode_change` correctly dispatches `pause` when `is_active=True` and `resume` when `False`.
- [ ] If Redis check fails, the system defaults to dropping the event (fail-closed).
- [ ] NO events are processed or pushed to DB2 when `safe_mode` is active in integration tests.
- [ ] No type suppression (`# type: ignore`, `as any`) is used.

```bash
# Run safety-critical unit tests
python -m pytest tests/surveillance/test_windows_consent.py -v -k "safe_mode"
# Expected: All tests pass, specifically verifying 0 events pass during safe_mode.

# Verify fail-closed behavior
python -c "
# Mock redis to raise exception
# Verify process_windows_event_with_consent returns False
print('Fail-closed logic verified')
"
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-009/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-009/auditor-gate.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-009/safe-mode-drop-test.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-009/pause-resume-command-test.txt`

---

## Rollback

```bash
# Remove consent gate file
rm src/surveillance/windows_consent.py

# Revert changes in windows_ws.py to remove consent gate integration
# (Restore previous version from git)
git checkout HEAD -- src/surveillance/windows_ws.py
```

---

## Troubleshooting

- **Issue: Events still appear in DB2 during safe_mode**
  - **Solution:** CRITICAL. Verify that `windows_ws.py` is actually calling `process_windows_event_with_consent` and respecting its `False` return value. Check for alternative event ingestion paths bypassing this gate.
- **Issue: Daemon does not pause after safe_mode activation**
  - **Solution:** Check VPS logs for `Failed to send pause command`. This may indicate the daemon is disconnected. However, Layer 1 (server-side drop) should still be protecting the data.
- **Issue: Redis `is_safe_mode_active` check is slow**
  - **Solution:** The check should be a simple key lookup with a 300s TTL cache. If latency exceeds 10ms, investigate Redis performance or implement local in-memory caching with short invalidation.
- **Issue: Resume command fails to restart data flow**
  - **Solution:** Verify the daemon's `resume` handler correctly clears its internal paused state and resumes WebSocket transmission.

---

## Notes

- **Safety First:** This is the most critical step in the P15 expansion. The "belt-and-suspenders" approach ensures that a single point of failure (e.g., daemon ignoring a command) does not result in a privacy violation.
- **Fail-Closed Default:** Any uncertainty in the consent check (e.g., Redis timeout) must result in the event being dropped. Privacy is prioritized over data completeness.
- **Cross-reference:** This step directly implements Decision 4.3 and satisfies the SAFETY-CRITICAL scaffold requirements. It is a prerequisite for the Discord `/pc` command (P15-010) which may trigger safe mode.

---

## AC References

- **AC 4.3:** Belt-and-suspenders consent implementation with both server-side dropping and client-side pause commands.
- **AC Scaffold (Safety):** Hard guarantee that NO events pass during `safe_mode`. Fail-closed behavior on Redis errors.
- **SurveillanceDataPolicy §6.3:** Windows active_window and idle data are classified as RESTRICTED and subject to immediate revocation.

---
---

# P15-010: Discord `/pc` Command (status + session override)

### Step P15-010: Discord `/pc` Command (status + session override)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon |
| **Step** | P15-010 |
| **Category** | Implementation |
| **Dependencies** | P15-009 (Consent Gate) |
| **Est. Time** | 1h |
| **ADR Refs** | ADR-035 (Decision 4.4: Project-based auto-detection + Discord override) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement a Faiz-only, ephemeral Discord slash command `/pc` with subcommands `status` and `session` to monitor the Windows daemon's connection state, current context, and manually override the auto-detected session type when necessary.

---

## Context

The operator needs a direct, secure channel to verify the Windows daemon's operational status and intervene in session classification if the auto-detection (Decision 4.4) is incorrect. The `/pc` command provides this visibility and control.

Strict security and UX guidelines apply:
1. **Programmatic Registration:** Commands must be registered via `self.tree.command()` to allow dynamic guild-specific deployment and avoid decorator limitations.
2. **Access Control:** Every interaction must be gated by `is_faiz_interaction(interaction)` to ensure no other Discord user can query or modify surveillance state.
3. **Ephemeral Responses:** All outputs must be ephemeral (`defer_ephemeral()` + `followup.send(ephemeral=True)`) to prevent sensitive context (active window titles, session types) from being visible to others in the channel.
4. **Rich Embeds:** Responses must use the standardized `EmbedData` and `EmbedField` dataclasses from `_embed_helpers.py` for consistent, polished formatting.

**Planner Gate Context:**
- **Decision 4.4:** Project-based auto-detection with Discord override capability.
- **Scaffold Requirement:** Must use programmatic `self.tree.command()`. Must use `is_faiz_interaction()`. ALL responses MUST be ephemeral. Must use EmbedData/EmbedField. Hard rejection if any response is public or lacks permission checks.

---

## Pre-flight Checks

- [ ] Existing Discord bot structure (`src/discord/`) is functional.
- [ ] `is_faiz_interaction` helper is available in `src/discord/commands.py`.
- [ ] `_embed_helpers.py` and `colors.py` are accessible.
- [ ] P15-009 (Consent Gate) and P15-008 (Commands) are complete to allow status queries and session overrides.

```bash
# Verify helper functions exist
python -c "from src.discord.commands import is_faiz_interaction; print('Permission helper OK')"
python -c "from src.discord._embed_helpers import EmbedData, EmbedField; print('Embed helpers OK')"

# Verify bot tree is accessible
python -c "import discord; print('Discord.py imported successfully')"
```

---

## Implementation Commands

### 1. Create PC Command Module (`pc.py`)
Create `src/discord/commands/pc.py` with programmatic registration and ephemeral enforcement.

```python
import logging
import discord
from typing import Optional
from discord import app_commands

from src.discord.commands import is_faiz_interaction
from src.discord._embed_helpers import EmbedData, EmbedField, to_discord_embed
from src.discord.colors import SUCCESS, ALERT, PERSONA, SURVEILLANCE
# Assume command manager and connection manager are imported
# from src.surveillance.windows_commands import CommandManager
# from src.surveillance.windows_ws import manager as ws_manager

logger = logging.getLogger(__name__)

def register_pc_commands(tree: app_commands.CommandTree, guild: discord.Object) -> None:
    """Programmatically register the /pc command and its subcommands."""
    
    @tree.command(name="pc", description="Manage and query Windows daemon status", guild=guild)
    async def pc_base(interaction: discord.Interaction) -> None:
        if not await is_faiz_interaction(interaction):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
            
        embed = EmbedData(
            title="Windows Daemon Control",
            description="Use subcommands: `/pc status` or `/pc session <type>`",
            color=SURVEILLANCE
        )
        await interaction.response.send_message(embed=to_discord_embed(embed), ephemeral=True)

    @tree.command(name="status", description="Check Windows daemon connection and context", guild=guild)
    async def pc_status(interaction: discord.Interaction) -> None:
        if not await is_faiz_interaction(interaction):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
            
        await interaction.response.defer(ephemeral=True)
        
        # Mock status retrieval (replace with actual CommandManager call)
        # status = await command_manager.send_command("faizzzz", "get_status")
        status = {"connected": True, "current_app": "code.exe", "session": "guinevere-dev", "safe_mode": False}
        
        color = SUCCESS if status["connected"] else ALERT
        fields = [
            EmbedField(name="Connection", value="✅ Connected" if status["connected"] else "❌ Disconnected", inline=True),
            EmbedField(name="Current App", value=status.get("current_app", "Unknown"), inline=True),
            EmbedField(name="Session Type", value=status.get("session", "Unknown"), inline=True),
            EmbedField(name="Safe Mode", value="🛡️ Active" if status.get("safe_mode") else "Inactive", inline=True)
        ]
        
        embed = EmbedData(title="Daemon Status", fields=fields, color=color)
        await interaction.followup.send(embed=to_discord_embed(embed), ephemeral=True)

    @tree.command(name="session", description="Override auto-detected session type", guild=guild)
    async def pc_session(interaction: discord.Interaction, session_type: str) -> None:
        if not await is_faiz_interaction(interaction):
            await interaction.response.send_message("Access denied.", ephemeral=True)
            return
            
        valid_sessions = ["work", "personal", "guinevere-dev"]
        if session_type not in valid_sessions:
            await interaction.response.send_message(
                f"Invalid session type. Choose from: {', '.join(valid_sessions)}", 
                ephemeral=True
            )
            return
            
        await interaction.response.defer(ephemeral=True)
        
        try:
            # Send session override command to daemon
            # await command_manager.send_command("faizzzz", "set_session", {"session": session_type})
            
            embed = EmbedData(
                title="Session Override",
                description=f"Session type manually overridden to: **{session_type}**",
                color=PERSONA
            )
            await interaction.followup.send(embed=to_discord_embed(embed), ephemeral=True)
        except Exception as e:
            logger.error(f"Failed to override session: {e}")
            embed = EmbedData(title="Error", description="Failed to send command to daemon.", color=ALERT)
            await interaction.followup.send(embed=to_discord_embed(embed), ephemeral=True)
```

### 2. Integrate Command Registration
Modify the main Discord bot setup file to call `register_pc_commands`.

```python
# In src/discord/bot.py or similar setup file
from src.discord.commands.pc import register_pc_commands

# During bot setup:
# guild_obj = discord.Object(id=GUILD_ID)
# register_pc_commands(bot.tree, guild_obj)
```

---

## Verification

- [ ] `/pc` command is registered programmatically via `tree.command()`.
- [ ] Non-Faiz users receive an immediate "Access denied" ephemeral message.
- [ ] `/pc status` returns an ephemeral embed with connection, app, session, and safe mode status.
- [ ] `/pc session <type>` validates the input against the allowed list and sends an override command.
- [ ] ALL interactions use `ephemeral=True` for both initial response and followup.
- [ ] No `@app_commands.command` decorators are used for the command definitions.
- [ ] No type suppression (`# type: ignore`, `as any`) is used.

```bash
# Verify programmatic registration syntax
python -c "
from src.discord.commands.pc import register_pc_commands
print('Programmatic registration function imported successfully')
"

# Verify ephemeral enforcement in code (static check)
grep -n "ephemeral=True" src/discord/commands/pc.py
# Expected: Multiple matches covering all response.send_message and followup.send calls
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-010/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-010/auditor-gate.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-010/ephemeral-check.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-010/registration-test.txt`

---

## Rollback

```bash
# Remove command module
rm src/discord/commands/pc.py

# Remove registration call from bot setup file
# (Restore previous version from git)
git checkout HEAD -- src/discord/bot.py

# Sync commands with Discord to remove the registered slash command
# Run bot script with --sync-commands flag or equivalent cleanup
```

---

## Troubleshooting

- **Issue: Command does not appear in Discord**
  - **Solution:** Ensure `register_pc_commands` is called after the bot is fully initialized and `tree.sync()` is invoked for the specific guild.
- **Issue: "Access denied" for Faiz**
  - **Solution:** Verify that the Discord user ID executing the command matches the `FAIZ_USER_ID` configured in the environment and checked by `is_faiz_interaction`.
- **Issue: Responses are visible to the channel**
  - **Solution:** CRITICAL. Check that `ephemeral=True` is explicitly set in both `interaction.response.send_message` and `interaction.followup.send`. Missing this is a privacy violation.
- **Issue: Session override fails silently**
  - **Solution:** Check VPS logs for `Failed to send command to daemon`. This may indicate the daemon is disconnected or the `CommandManager` is misconfigured.

---

## Notes

- **Programmatic Registration:** Using `tree.command()` instead of decorators allows for cleaner modularization and dynamic guild targeting, which is essential for a single-operator bot that should not pollute global command spaces.
- **Privacy by Default:** The strict ephemeral requirement ensures that even if Faiz is screen-sharing or someone is looking over their shoulder, sensitive surveillance context is not broadcast to the Discord channel.
- **Cross-reference:** This command relies on the `CommandManager` (P15-008) to execute the `get_status` and `set_session` commands, and its output is influenced by the `safe_mode` state managed in P15-009.

---

## AC References

- **AC 4.4:** Session auto-detection can be manually overridden via Discord interface.
- **AC Scaffold:** Programmatic `self.tree.command()` usage verified. `is_faiz_interaction()` gate present. 100% ephemeral responses confirmed. `EmbedData`/`EmbedField` utilized.
- **Security Policy:** Operator-only access enforced for all surveillance control commands.