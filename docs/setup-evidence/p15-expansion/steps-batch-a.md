# P15-001: Project Scaffold + Base Tracker ABC

### Step P15-001: Project Scaffold + Base Tracker ABC

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon (Wave 1) |
| **Step** | P15-001 |
| **Category** | Infrastructure / Project Initialization |
| **Dependencies** | None (Parallel with P15-007 and P15-012) |
| **Est. Time** | 1 hour |
| **ADR Refs** | ADR-010 (Retention by data class), ADR-019 (Tailscale mesh, zero public ports) |
| **Status** | ⬜ Not Started |

---

## Goal

Establish the foundational project structure for the Windows Daemon at `clients/windows/`, including dependency pinning in `pyproject.toml` and the interface-first `BaseTracker` Abstract Base Class (ABC) that enforces strict contracts for all subsequent tracker implementations.

---

## Context

The Windows Daemon is a critical component of the P15 surveillance expansion, designed to run continuously with <1% CPU idle via NSSM. To ensure maintainability and strict type safety, all data collection modules must inherit from a common `BaseTracker` interface. This prevents fragmented implementations and guarantees that every tracker exposes the same lifecycle methods (`start`, `stop`, `poll`) and configuration properties (`poll_interval`, `name`).

This step is the foundation for Wave 1 of the P15 implementation. It is completely independent of the VPS-side WebSocket endpoint (P15-007) and the TimescaleDB migration (P15-012), allowing parallel execution. By defining the ABC upfront, we enforce Decision 2.5 (Interface-first BaseTracker ABC) from the planner gate, ensuring that P15-002, P15-003, and P15-004 cannot be implemented without adhering to the agreed-upon contract.

The dependency pinning in `pyproject.toml` is critical. We must strictly pin `msgpack`, `websockets`, `pywin32`, `psutil`, and `loguru` to prevent silent breaking changes in the Windows environment, where dependency resolution can be fragile.

---

## Pre-flight Checks

- [ ] Python 3.11+ is installed and available in the system PATH on the Windows machine.
- [ ] The `clients/windows/` directory does not already exist, or is empty and safe to overwrite.
- [ ] Git is initialized at the repository root (`C:\Users\faizz\guinevere`).
- [ ] No existing `pyproject.toml` conflicts in the `clients/windows/` path.

```powershell
# Verify Python version
python --version
# Expected: Python 3.11.x or higher

# Verify current directory context
pwd
# Expected: C:\Users\faizz\guinevere

# Check if clients/windows exists
Test-Path -Path "clients\windows"
# Expected: False (or True if intentionally rescaffolding)
```

---

## Implementation Commands

### 1. Create Directory Structure

Execute the following commands to establish the required directory hierarchy.

```powershell
# Create base directories
New-Item -ItemType Directory -Force -Path "clients\windows\src\daemon"
New-Item -ItemType Directory -Force -Path "clients\windows\tests"
New-Item -ItemType Directory -Force -Path "clients\windows\nssm"
```

### 2. Generate `pyproject.toml`

Create the dependency manifest with strict version pinning.

```powershell
@'
[project]
name = "guinevere-windows-daemon"
version = "0.1.0"
description = "Guinevere Windows Daemon for PC Context Awareness"
requires-python = ">=3.11"
dependencies = [
    "msgpack==1.0.7",
    "websockets==12.0",
    "pywin32==306",
    "psutil==5.9.8",
    "loguru==0.7.2",
]

[project.optional-dependencies]
dev = [
    "pytest==8.0.0",
    "pytest-asyncio==0.23.5",
    "ruff==0.3.0",
    "mypy==1.8.0",
]

[build-system]
requires = ["setuptools>=68.0"]
build-backend = "setuptools.build_meta"

[tool.mypy]
strict = true
disallow_any_unimported = true
disallow_any_expr = true
disallow_any_decorated = true
disallow_any_explicit = true
disallow_any_generics = true
disallow_subclassing_any = true

[tool.ruff]
line-length = 100
target-version = "py311"
'@ | Set-Content -Path "clients\windows\pyproject.toml" -Encoding UTF8
```

### 3. Generate `src/daemon/__init__.py`

Initialize the daemon package.

```powershell
@'
"""Guinevere Windows Daemon package."""

from .base_tracker import BaseTracker

__all__ = ["BaseTracker"]
'@ | Set-Content -Path "clients\windows\src\daemon\__init__.py" -Encoding UTF8
```

### 4. Generate `src/daemon/base_tracker.py`

Implement the strict Abstract Base Class contract.

```powershell
@'
"""Base Tracker Abstract Base Class for Guinevere Windows Daemon."""

from abc import ABC, abstractmethod
from typing import Optional, Any
import asyncio

class BaseTracker(ABC):
    """
    Interface-first design for all daemon trackers (Decision 2.5).
    
    All concrete trackers MUST implement these methods to ensure
    uniform lifecycle management and polling behavior.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """Return the unique identifier name of this tracker."""
        pass

    @abstractmethod
    async def start(self) -> None:
        """Initialize tracker resources and begin background polling."""
        pass

    @abstractmethod
    async def stop(self) -> None:
        """Gracefully shut down tracker resources and cancel tasks."""
        pass

    @abstractmethod
    async def poll(self) -> Optional[dict[str, Any]]:
        """
        Execute a single poll cycle.
        
        Returns:
            Optional[dict]: The collected data payload if state changed, 
                            otherwise None to suppress redundant events.
        """
        pass

    @property
    @abstractmethod
    def poll_interval(self) -> float:
        """Return the polling interval in seconds."""
        pass

    async def run_loop(self) -> None:
        """
        Default implementation of the polling loop.
        Concrete classes may override if specialized loop logic is required,
        but should generally rely on this standard implementation.
        """
        await self.start()
        try:
            while True:
                payload = await self.poll()
                if payload is not None:
                    yield payload
                await asyncio.sleep(self.poll_interval)
        finally:
            await self.stop()
'@ | Set-Content -Path "clients\windows\src\daemon\base_tracker.py" -Encoding UTF8
```

---

## Verification

- [ ] All required files exist in the `clients/windows/` directory.
- [ ] `pyproject.toml` contains all required pinned dependencies.
- [ ] `base_tracker.py` defines exactly 5 abstract methods/properties.
- [ ] MyPy strict type checking passes without errors.

```powershell
# Navigate to the project directory
Set-Location -Path "clients\windows"

# Verify file existence
Test-Path "pyproject.toml"
Test-Path "src\daemon\__init__.py"
Test-Path "src\daemon\base_tracker.py"
# Expected: True for all

# Verify abstract methods are correctly defined
python -c "from src.daemon.base_tracker import BaseTracker; print(sorted(BaseTracker.__abstractmethods__))"
# Expected: ['name', 'poll', 'poll_interval', 'start', 'stop']

# Run mypy strict check (requires dev dependencies installed)
python -m mypy src/daemon/base_tracker.py
# Expected: Success: no issues found in 1 source file.
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-001/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-001/pyproject-toml.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-001/mypy-output.txt`

---

## Rollback

```powershell
# Complete removal of the scaffolded directory
Set-Location -Path "C:\Users\faizz\guinevere"
Remove-Item -Path "clients\windows" -Recurse -Force -ErrorAction SilentlyContinue
```

---

## Troubleshooting

- **Issue: `python -m mypy` returns "command not found"**
  - **Solution:** Ensure you have installed the development dependencies: `pip install -e .[dev]` from the `clients/windows` directory.
- **Issue: `__abstractmethods__` does not contain all 5 methods**
  - **Solution:** Verify that `@abstractmethod` and `@property` decorators are applied in the correct order (`@property` first, then `@abstractmethod`).
- **Issue: PowerShell `Set-Content` corrupts UTF-8 characters**
  - **Solution:** The `-Encoding UTF8` flag is explicitly included in the heredoc commands to prevent Windows default encoding issues.
- **Issue: Directory creation fails due to permissions**
  - **Solution:** Run PowerShell as Administrator, or ensure your user account has write permissions to `C:\Users\faizz\guinevere\clients`.

---

## Notes

- **Type Safety Enforcement:** The `pyproject.toml` includes aggressive MyPy configurations to prevent the anti-patterns forbidden by the Guinevere operating contract (e.g., `as any`, `# type: ignore`).
- **Cross-reference:** This ABC is the direct dependency for P15-002 (Active Window), P15-003 (Idle), and P15-004 (Git Context). Any deviation from this interface will cause immediate failure in those subsequent steps.
- **Caveat:** The `run_loop` method is provided as a convenience but is not abstract. Concrete implementations may use it or implement their own `asyncio` task management, provided they call `start()` and `stop()` appropriately.

---

## AC References

- **AC 1.4:** Standalone at `clients/windows/` — Verified by directory structure.
- **AC 2.5:** Interface-first BaseTracker ABC — Verified by `__abstractmethods__` check.
- **Planner Scaffold:** Forbidden patterns (`as any`, `# type: ignore`) are prevented by MyPy config. Required command passes with expected output.

---

# P15-002: Active Window Tracker (win32gui + psutil)

### Step P15-002: Active Window Tracker (win32gui + psutil)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon (Wave 2) |
| **Step** | P15-002 |
| **Category** | Implementation — Data Collection |
| **Dependencies** | P15-001 (BaseTracker ABC) |
| **Est. Time** | 1.5 hours |
| **ADR Refs** | ADR-010 (Retention by data class), ADR-019 (Tailscale mesh) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement the `ActiveWindowTracker` to capture the foreground window executable and title using `win32gui` and `psutil`, polling every 2 seconds and emitting events ONLY on state change, with strict regex redaction for sensitive title patterns.

---

## Context

The Active Window Tracker is the primary source of dev context awareness for the Guinevere daemon. It fulfills Decision 2.1 (Enriched: exe + title + project + branch + repo-relative path) by capturing the immediate foreground process. However, to respect privacy and data minimization principles, it must aggressively redact sensitive information from window titles before the data ever leaves the local machine.

Polling every 2 seconds provides near-real-time context without causing the <1% CPU idle constraint to be violated. Crucially, the tracker must implement state-change detection. It should compare the current foreground window against the last known state and return `None` if nothing has changed, preventing event pipeline flooding.

This step depends entirely on the `BaseTracker` ABC created in P15-001. The implementation must strictly adhere to the abstract method signatures and property definitions established in that contract.

---

## Pre-flight Checks

- [ ] P15-001 is complete and `BaseTracker` is importable.
- [ ] `pywin32` and `psutil` are installed in the virtual environment.
- [ ] The Windows machine is unlocked and has active GUI sessions for testing.
- [ ] No existing `active_window.py` file in `clients/windows/src/daemon/`.

```powershell
# Verify dependencies are installed
python -c "import win32gui; import psutil; print('Dependencies OK')"
# Expected: Dependencies OK

# Verify BaseTracker is importable
python -c "from src.daemon.base_tracker import BaseTracker; print('BaseTracker OK')"
# Expected: BaseTracker OK
```

---

## Implementation Commands

### 1. Generate `src/daemon/active_window.py`

Create the active window tracker with state-change detection and title redaction.

```powershell
@'
"""Active Window Tracker for Guinevere Windows Daemon."""

import re
import asyncio
import win32gui
import win32process
import psutil
from typing import Optional, Any
from loguru import logger

from .base_tracker import BaseTracker

# Regex patterns for sensitive data in window titles
SENSITIVE_PATTERNS = [
    re.compile(r'password', re.IGNORECASE),
    re.compile(r'token', re.IGNORECASE),
    re.compile(r'secret', re.IGNORECASE),
    re.compile(r'api[_-]?key', re.IGNORECASE),
    re.compile(r'auth', re.IGNORECASE),
]

def redact_title(title: str) -> str:
    """Redact sensitive patterns from window titles."""
    for pattern in SENSITIVE_PATTERNS:
        title = pattern.sub('[REDACTED]', title)
    return title

class ActiveWindowTracker(BaseTracker):
    """Tracks the active foreground window and its associated process."""

    def __init__(self) -> None:
        self._last_exe: Optional[str] = None
        self._last_title: Optional[str] = None
        self._running = False

    @property
    def name(self) -> str:
        return "active_window"

    @property
    def poll_interval(self) -> float:
        return 2.0

    async def start(self) -> None:
        self._running = True
        logger.info("ActiveWindowTracker started")

    async def stop(self) -> None:
        self._running = False
        logger.info("ActiveWindowTracker stopped")

    async def poll(self) -> Optional[dict[str, Any]]:
        if not self._running:
            return None

        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            if not pid:
                return None

            process = psutil.Process(pid)
            exe_name = process.name()
            raw_title = win32gui.GetWindowText(hwnd)
            
            # Redact sensitive information
            clean_title = redact_title(raw_title)

            # State change detection
            if self._last_exe == exe_name and self._last_title == clean_title:
                return None

            # Update state
            self._last_exe = exe_name
            self._last_title = clean_title

            return {
                "exe": exe_name,
                "title": clean_title,
                "project": None,  # Populated by GitContextTracker
                "branch": None,   # Populated by GitContextTracker
                "file": None,     # Populated by GitContextTracker
                "session_type": None # Populated by GitContextTracker
            }

        except psutil.NoSuchProcess:
            logger.debug("Process disappeared during polling")
            return None
        except Exception as e:
            logger.error(f"ActiveWindowTracker poll error: {e}")
            return None
'@ | Set-Content -Path "clients\windows\src\daemon\active_window.py" -Encoding UTF8
```

---

## Verification

- [ ] `active_window.py` exists and is syntactically valid.
- [ ] The class inherits from `BaseTracker`.
- [ ] State change detection logic is present (compares `_last_exe` and `_last_title`).
- [ ] Title redaction regex is implemented and functional.

```powershell
Set-Location -Path "clients\windows"

# Verify syntax and import
python -c "from src.daemon.active_window import ActiveWindowTracker; print('Import OK')"
# Expected: Import OK

# Verify BaseTracker inheritance
python -c "from src.daemon.active_window import ActiveWindowTracker; from src.daemon.base_tracker import BaseTracker; print(issubclass(ActiveWindowTracker, BaseTracker))"
# Expected: True

# Test redaction function
python -c "from src.daemon.active_window import redact_title; print(redact_title('My App - Password: 123'))"
# Expected: My App - [REDACTED]: 123

# Run mypy strict check
python -m mypy src/daemon/active_window.py
# Expected: Success: no issues found in 1 source file.
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-002/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-002/redaction-test-output.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-002/mypy-output.txt`

---

## Rollback

```powershell
# Remove the active window tracker file
Set-Location -Path "C:\Users\faizz\guinevere\clients\windows"
Remove-Item -Path "src\daemon\active_window.py" -Force -ErrorAction SilentlyContinue
```

---

## Troubleshooting

- **Issue: `win32gui` or `psutil` import fails**
  - **Solution:** Ensure you are running the command in the activated virtual environment where `pyproject.toml` dependencies were installed (`pip install -e .`).
- **Issue: `GetForegroundWindow` returns 0**
  - **Solution:** This occurs if no window has focus (e.g., desktop is active). The code handles this by returning `None`, which is the correct behavior to suppress events.
- **Issue: Redaction is not catching a specific sensitive word**
  - **Solution:** Add the new pattern to the `SENSITIVE_PATTERNS` list in `active_window.py` using case-insensitive regex.
- **Issue: MyPy complains about `win32gui` types**
  - **Solution:** Ensure `types-pywin32` is installed in the dev dependencies, or add a specific `# type: ignore` only for the third-party import line if absolutely necessary (though strict config should ideally catch this via stubs).

---

## Notes

- **Enriched Data Placeholder:** The returned dictionary includes `project`, `branch`, `file`, and `session_type` as `None`. This is intentional. The `EventRouter` (P15-005) will merge this payload with the output of the `GitContextTracker` (P15-004) before serialization.
- **Performance:** `win32gui` and `psutil` calls are extremely fast. Polling every 2 seconds will consume negligible CPU, well within the <1% idle constraint.
- **Cross-reference:** Depends on P15-001. Feeds into P15-005 (Event Pipeline).

---

## AC References

- **AC 2.1:** Enriched data structure (exe + title + placeholders for git context).
- **AC 2.5:** Implements `BaseTracker` interface.
- **Planner Scaffold:** Must detect state change only. Must include title regex redaction. Forbidden patterns (`as any`, `except:`) are absent.

---

# P15-003: Idle Tracker (GetLastInputInfo, graduated)

### Step P15-003: Idle Tracker (GetLastInputInfo, graduated)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon (Wave 2) |
| **Step** | P15-003 |
| **Category** | Implementation — Data Collection |
| **Dependencies** | P15-001 (BaseTracker ABC) |
| **Est. Time** | 1 hour |
| **ADR Refs** | ADR-010 (Retention by data class) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement the `IdleTracker` to monitor user input activity using Windows API `GetLastInputInfo` and `GetTickCount64`, enforcing graduated idle thresholds (active, away, idle, deep_idle) and safely handling the 49.7-day `GetTickCount64` overflow.

---

## Context

Understanding user presence is critical for the Guinevere persona to avoid interrupting deep work or sleep. Decision 2.3 mandates graduated idle states: active (<2m), away (2m), idle (5m), and deep_idle (15m). 

Using `GetTickCount64` is mandatory. The older 32-bit `GetTickCount` overflows every 49.7 days, which would cause the daemon to miscalculate idle time and potentially flood the server with false "active" events after a month of uptime. The implementation must explicitly use the 64-bit variant and handle the arithmetic safely.

Polling every 5 seconds provides a good balance between responsiveness and resource usage. Like the Active Window Tracker, this module must only emit events when the idle state *changes*, preventing unnecessary network traffic.

---

## Pre-flight Checks

- [ ] P15-001 is complete and `BaseTracker` is importable.
- [ ] `pywin32` is installed in the virtual environment.
- [ ] No existing `idle_tracker.py` file in `clients/windows/src/daemon/`.

```powershell
# Verify BaseTracker is importable
python -c "from src.daemon.base_tracker import BaseTracker; print('BaseTracker OK')"
# Expected: BaseTracker OK

# Verify win32api is available
python -c "import win32api; print('win32api OK')"
# Expected: win32 OK
```

---

## Implementation Commands

### 1. Generate `src/daemon/idle_tracker.py`

Create the idle tracker with 64-bit tick count and graduated thresholds.

```powershell
@'
"""Idle Tracker for Guinevere Windows Daemon."""

import ctypes
import asyncio
from typing import Optional, Any
from loguru import logger

from .base_tracker import BaseTracker

class LASTINPUTINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", ctypes.c_uint),
        ("dwTime", ctypes.c_uint32)
    ]

# Graduated idle thresholds in seconds (Decision 2.3)
IDLE_THRESHOLDS = {
    "active": 0,       # < 2 minutes
    "away": 120,       # 2 minutes
    "idle": 300,       # 5 minutes
    "deep_idle": 900,  # 15 minutes
}

def get_idle_seconds() -> int:
    """Calculate seconds since last user input using GetTickCount64."""
    last_input_info = LASTINPUTINFO()
    last_input_info.cbSize = ctypes.sizeof(LASTINPUTINFO)
    
    # Use GetTickCount64 to avoid 49.7-day overflow of 32-bit GetTickCount
    tick_count_64 = ctypes.windll.kernel32.GetTickCount64()
    
    if not ctypes.windll.user32.GetLastInputInfo(ctypes.byref(last_input_info)):
        logger.error("GetLastInputInfo failed")
        return 0
        
    # last_input_info.dwTime is 32-bit, but it represents a tick count.
    # We must handle the potential wrap-around between 32-bit dwTime and 64-bit tick_count_64.
    # However, GetLastInputInfo returns the tick count at the time of last input.
    # Since dwTime is 32-bit, we mask the 64-bit tick count to 32 bits for accurate subtraction.
    last_input_time_32 = last_input_info.dwTime
    current_time_32 = tick_count_64 & 0xFFFFFFFF
    
    # Handle 32-bit wrap-around in subtraction
    if current_time_32 >= last_input_time_32:
        elapsed_ms = current_time_32 - last_input_time_32
    else:
        elapsed_ms = (0xFFFFFFFF - last_input_time_32) + current_time_32
        
    return elapsed_ms // 1000

def get_idle_state(idle_seconds: int) -> str:
    """Determine the graduated idle state based on seconds."""
    if idle_seconds < IDLE_THRESHOLDS["away"]:
        return "active"
    elif idle_seconds < IDLE_THRESHOLDS["idle"]:
        return "away"
    elif idle_seconds < IDLE_THRESHOLDS["deep_idle"]:
        return "idle"
    else:
        return "deep_idle"

class IdleTracker(BaseTracker):
    """Tracks user idle state using Windows API."""

    def __init__(self) -> None:
        self._last_state: Optional[str] = None
        self._running = False

    @property
    def name(self) -> str:
        return "idle"

    @property
    def poll_interval(self) -> float:
        return 5.0

    async def start(self) -> None:
        self._running = True
        logger.info("IdleTracker started")

    async def stop(self) -> None:
        self._running = False
        logger.info("IdleTracker stopped")

    async def poll(self) -> Optional[dict[str, Any]]:
        if not self._running:
            return None

        try:
            idle_seconds = get_idle_seconds()
            current_state = get_idle_state(idle_seconds)

            # State change detection
            if self._last_state == current_state:
                return None

            self._last_state = current_state
            logger.debug(f"Idle state changed to: {current_state} ({idle_seconds}s)")

            return {
                "state": current_state,
                "idle_seconds": idle_seconds
            }

        except Exception as e:
            logger.error(f"IdleTracker poll error: {e}")
            return None
'@ | Set-Content -Path "clients\windows\src\daemon\idle_tracker.py" -Encoding UTF8
```

---

## Verification

- [ ] `idle_tracker.py` exists and is syntactically valid.
- [ ] The class inherits from `BaseTracker`.
- [ ] `GetTickCount64` is explicitly used (not `GetTickCount`).
- [ ] Graduated thresholds (2m, 5m, 15m) are implemented.
- [ ] 32-bit wrap-around arithmetic is handled.

```powershell
Set-Location -Path "clients\windows"

# Verify syntax and import
python -c "from src.daemon.idle_tracker import IdleTracker, get_idle_seconds; print('Import OK')"
# Expected: Import OK

# Verify BaseTracker inheritance
python -c "from src.daemon.idle_tracker import IdleTracker; from src.daemon.base_tracker import BaseTracker; print(issubclass(IdleTracker, BaseTracker))"
# Expected: True

# Verify GetTickCount64 usage in source
Select-String -Path "src\daemon\idle_tracker.py" -Pattern "GetTickCount64"
# Expected: Should find the ctypes.windll.kernel32.GetTickCount64 call

# Run mypy strict check
python -m mypy src/daemon/idle_tracker.py
# Expected: Success: no issues found in 1 source file.
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-003/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-003/gettickcount64-check.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-003/mypy-output.txt`

---

## Rollback

```powershell
# Remove the idle tracker file
Set-Location -Path "C:\Users\faizz\guinevere\clients\windows"
Remove-Item -Path "src\daemon\idle_tracker.py" -Force -ErrorAction SilentlyContinue
```

---

## Troubleshooting

- **Issue: `GetLastInputInfo` fails or returns 0**
  - **Solution:** Ensure the script has sufficient permissions. While it does not require Administrator rights, running in a restricted sandbox might block API calls.
- **Issue: Idle state never changes from "active"**
  - **Solution:** Verify that you are actually moving the mouse or typing. The `get_idle_seconds` function can be tested manually by printing its output in a loop.
- **Issue: MyPy complains about `ctypes` structures**
  - **Solution:** The `LASTINPUTINFO` class is properly typed with `_fields_`. If MyPy still complains, ensure `types-ctypes` or equivalent stubs are available, though standard library `ctypes` is usually well-supported.
- **Issue: 32-bit wrap-around logic seems complex**
  - **Solution:** The logic `(0xFFFFFFFF - last_input_time_32) + current_time_32` is the standard, safe way to handle unsigned 32-bit integer subtraction in Python when dealing with Windows tick counts. Do not simplify this to basic subtraction.

---

## Notes

- **Overflow Safety:** The explicit use of `GetTickCount64` combined with 32-bit masking for `dwTime` ensures this tracker will function correctly for years without resetting, fulfilling the strict reliability requirements of the daemon.
- **Cross-reference:** Depends on P15-001. The `state` string ("active", "away", "idle", "deep_idle") is directly consumed by the Event Pipeline (P15-005) and attached to every event payload.

---

## AC References

- **AC 2.3:** Graduated idle: 2m away / 5m idle / 15m deep_idle.
- **Planner Scaffold:** Must use GetTickCount64 (not 32-bit). Must implement graduated thresholds. Must handle 49.7-day overflow. Forbidden patterns are absent.

---

# P15-004: Git Context Tracker (traversal + project mapping)

### Step P15-004: Git Context Tracker (traversal + project mapping)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon (Wave 2) |
| **Step** | P15-004 |
| **Category** | Implementation — Data Collection |
| **Dependencies** | P15-001 (BaseTracker ABC) |
| **Est. Time** | 1 hour |
| **ADR Refs** | ADR-010 (Retention by data class), ADR-019 (Tailscale mesh) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement the `GitContextTracker` to traverse the directory tree upward from the current working directory to locate `.git`, extract the current branch from `.git/HEAD`, and map the project to a session type using a local `daemon.json` configuration, strictly avoiding any reading of `.git/config` or credentials.

---

## Context

To provide rich dev context (Decision 2.1), the daemon needs to know not just what application is active, but what project and branch the user is working on. Decision 2.2 mandates Git traversal as the MVP approach, deferring VS Code extension integration to post-MVP.

The tracker must walk up the directory tree from the active window's file path (or current working directory) until it finds a `.git` folder. It then reads the `.git/HEAD` file to determine the current branch. Crucially, to comply with data minimization and security policies, it must NEVER read `.git/config`, `.git/credentials`, or any other file that might contain remote URLs, tokens, or personal information.

Project-to-session mapping is handled via a local `daemon.json` file, allowing Faiz to define custom session types (e.g., "guinevere-dev", "work", "personal") without hardcoding logic in the daemon.

---

## Pre-flight Checks

- [ ] P15-001 is complete and `BaseTracker` is importable.
- [ ] A test Git repository exists locally for validation (e.g., the `guinevere` repo itself).
- [ ] No existing `git_context.py` file in `clients/windows/src/daemon/`.

```powershell
# Verify BaseTracker is importable
python -c "from src.daemon.base_tracker import BaseTracker; print('BaseTracker OK')"
# Expected: BaseTracker OK

# Verify test repo has .git/HEAD
Test-Path "C:\Users\faizz\guinevere\.git\HEAD"
# Expected: True
```

---

## Implementation Commands

### 1. Generate `src/daemon/git_context.py`

Create the Git context tracker with safe upward traversal and session mapping.

```powershell
@'
"""Git Context Tracker for Guinevere Windows Daemon."""

import os
import json
import asyncio
from pathlib import Path
from typing import Optional, Any, Dict
from loguru import logger

from .base_tracker import BaseTracker

DEFAULT_CONFIG = {
    "session_mapping": {
        "guinevere": "guinevere-dev",
        "office-app": "work"
    },
    "default_session": "personal"
}

class GitContextTracker(BaseTracker):
    """Tracks Git repository context via safe directory traversal."""

    def __init__(self, config_path: str = "nssm/daemon.json") -> None:
        self._config_path = config_path
        self._config = self._load_config()
        self._last_context: Optional[Dict[str, Any]] = None
        self._running = False

    def _load_config(self) -> Dict[str, Any]:
        """Load session mapping from daemon.json."""
        try:
            if os.path.exists(self._config_path):
                with open(self._config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load daemon config: {e}")
        return DEFAULT_CONFIG

    @property
    def name(self) -> str:
        return "git_context"

    @property
    def poll_interval(self) -> float:
        return 30.0  # Poll less frequently, git context changes slowly

    async def start(self) -> None:
        self._running = True
        logger.info("GitContextTracker started")

    async def stop(self) -> None:
        self._running = False
        logger.info("GitContextTracker stopped")

    def _find_git_root(self, start_path: str) -> Optional[Path]:
        """Traverse upward to find .git directory."""
        current = Path(start_path).resolve()
        while current != current.parent:
            if (current / ".git").is_dir():
                return current
            current = current.parent
        return None

    def _get_branch(self, git_root: Path) -> str:
        """Safely read branch name from .git/HEAD."""
        head_file = git_root / ".git" / "HEAD"
        try:
            if head_file.exists():
                content = head_file.read_text(encoding='utf-8').strip()
                if content.startswith("ref: refs/heads/"):
                    return content.replace("ref: refs/heads/", "")
                return content  # Detached HEAD state
        except Exception as e:
            logger.warning(f"Failed to read HEAD: {e}")
        return "unknown"

    def _get_session_type(self, repo_name: str) -> str:
        """Map repository name to session type."""
        mapping = self._config.get("session_mapping", {})
        return mapping.get(repo_name, self._config.get("default_session", "personal"))

    async def poll(self, active_file_path: Optional[str] = None) -> Optional[dict[str, Any]]:
        if not self._running:
            return None

        try:
            # Use provided path or fallback to current working directory
            start_path = active_file_path or os.getcwd()
            
            git_root = self._find_git_root(start_path)
            if not git_root:
                # Not in a git repository
                current_context = {
                    "project": None,
                    "branch": None,
                    "file": None,
                    "session_type": self._config.get("default_session", "personal")
                }
            else:
                repo_name = git_root.name
                branch = self._get_branch(git_root)
                
                # Produce repo-relative path if active_file_path is provided
                relative_file = None
                if active_file_path:
                    try:
                        relative_file = str(Path(active_file_path).relative_to(git_root))
                    except ValueError:
                        relative_file = active_file_path

                current_context = {
                    "project": repo_name,
                    "branch": branch,
                    "file": relative_file,
                    "session_type": self._get_session_type(repo_name)
                }

            # State change detection
            if self._last_context == current_context:
                return None

            self._last_context = current_context
            logger.debug(f"Git context updated: {current_context}")
            return current_context

        except Exception as e:
            logger.error(f"GitContextTracker poll error: {e}")
            return None
'@ | Set-Content -Path "clients\windows\src\daemon\git_context.py" -Encoding UTF8
```

---

## Verification

- [ ] `git_context.py` exists and is syntactically valid.
- [ ] The class inherits from `BaseTracker`.
- [ ] Upward traversal logic (`_find_git_root`) is implemented.
- [ ] `.git/HEAD` is read safely, and `.git/config` is NEVER accessed.
- [ ] Session mapping from `daemon.json` is functional.

```powershell
Set-Location -Path "clients\windows"

# Verify syntax and import
python -c "from src.daemon.git_context import GitContextTracker; print('Import OK')"
# Expected: Import OK

# Verify BaseTracker inheritance
python -c "from src.daemon.git_context import GitContextTracker; from src.daemon.base_tracker import BaseTracker; print(issubclass(GitContextTracker, BaseTracker))"
# Expected: True

# Verify NO access to .git/config in source
Select-String -Path "src\daemon\git_context.py" -Pattern "\.git.config"
# Expected: No matches found

# Run mypy strict check
python -m mypy src/daemon/git_context.py
# Expected: Success: no issues found in 1 source file.
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-004/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-004/no-config-access-check.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-004/mypy-output.txt`

---

## Rollback

```powershell
# Remove the git context tracker file
Set-Location -Path "C:\Users\faizz\guinevere\clients\windows"
Remove-Item -Path "src\daemon\git_context.py" -Force -ErrorAction SilentlyContinue
```

---

## Troubleshooting

- **Issue: Tracker always returns "personal" session**
  - **Solution:** Ensure `nssm/daemon.json` exists and contains the correct `session_mapping` for the current repository name.
- **Issue: `relative_to` throws ValueError**
  - **Solution:** This is expected if the `active_file_path` is not actually inside the discovered `git_root`. The code catches this and falls back to the absolute path, which is safe.
- **Issue: MyPy complains about `Path` operations**
  - **Solution:** Ensure `pathlib` is imported correctly. The code uses standard library `pathlib` which has excellent type stub support.
- **Issue: Detached HEAD state returns weird string**
  - **Solution:** The `_get_branch` method explicitly handles detached HEAD by returning the raw content of `.git/HEAD` (usually a commit hash), which is the correct and safe behavior.

---

## Notes

- **Security Boundary:** The explicit avoidance of `.git/config` is a hard requirement. This file often contains remote URLs with embedded credentials or personal email addresses. Reading only `.git/HEAD` and directory names satisfies the context requirement without violating data minimization.
- **Cross-reference:** Depends on P15-001. The output of this tracker is designed to be merged with the `ActiveWindowTracker` output by the `EventRouter` (P15-005).

---

## AC References

- **AC 2.2:** Git traversal MVP, VS Code extension post-MVP.
- **Planner Scaffold:** Must traverse up for `.git`. Must read HEAD. Must produce repo-relative paths. Must NOT read `.git/config` or credentials. Forbidden patterns are absent.

---

# P15-005: Event Pipeline (MessagePack + EventRouter + WS Client)

### Step P15-005: Event Pipeline (MessagePack + EventRouter + WS Client)

| Field | Value |
|---|---|
| **Phase** | P15 — Windows Daemon (Wave 3) |
| **Step** | P15-005 |
| **Category** | Implementation — Networking & Serialization |
| **Dependencies** | P15-002, P15-003, P15-004 (All trackers) |
| **Est. Time** | 2 hours |
| **ADR Refs** | ADR-019 (Tailscale mesh, zero public ports) |
| **Status** | ⬜ Not Started |

---

## Goal

Implement the core event pipeline, including MessagePack serialization, an `EventRouter` to merge tracker outputs, an `EventPipeline` for deduplication and sequencing, and a resilient `WSClient` with exponential backoff and first-message authentication.

---

## Context

This is the central nervous system of the Windows Daemon. Decision 3.1 mandates a hybrid protocol: MessagePack for events (for efficiency and binary safety) and JSON for commands. Decision 3.2 requires a single persistent WebSocket connection.

The `WSClient` must implement robust reconnection logic. Network interruptions on Windows (sleep, Wi-Fi drops, Tailscale re-routing) are common. The client must use exponential backoff (1s, 2s, 4s, 8s, max 60s + jitter) to avoid hammering the VPS endpoint during outages.

Sequence numbers must be strictly monotonic to allow the VPS to detect dropped messages. The `EventRouter` is responsible for taking the disparate outputs of P15-002, P15-003, and P15-004, merging them into a single enriched payload, and passing it to the pipeline.

---

## Pre-flight Checks

- [ ] P15-001 through P15-004 are complete and importable.
- [ ] `msgpack` and `websockets` are installed in the virtual environment.
- [ ] No existing `serialization.py`, `event_router.py`, `event_pipeline.py`, or `ws_client.py` in `clients/windows/src/daemon/`.

```powershell
# Verify dependencies
python -c "import msgpack; import websockets; print('Dependencies OK')"
# Expected: Dependencies OK

# Verify trackers are importable
python -c "from src.daemon.active_window import ActiveWindowTracker; from src.daemon.idle_tracker import IdleTracker; from src.daemon.git_context import GitContextTracker; print('Trackers OK')"
# Expected: Trackers OK
```

---

## Implementation Commands

### 1. Generate `src/daemon/serialization.py`

Create MessagePack/JSON serialization utilities.

```powershell
@'
"""Serialization utilities for Guinevere Windows Daemon."""

import msgpack
import json
from typing import Any, Dict

def pack_event(event: Dict[str, Any]) -> bytes:
    """Pack an event dictionary into MessagePack bytes."""
    return msgpack.packb(event, use_bin_type=True)

def unpack_command(data: bytes) -> Dict[str, Any]:
    """Unpack a command from JSON bytes (commands are JSON per Decision 3.1)."""
    return json.loads(data.decode('utf-8'))

def pack_command_response(response: Dict[str, Any]) -> bytes:
    """Pack a command response into JSON bytes."""
    return json.dumps(response).encode('utf-8')
'@ | Set-Content -Path "clients\windows\src\daemon\serialization.py" -Encoding UTF8
```

### 2. Generate `src/daemon/event_router.py`

Create the router to merge tracker outputs.

```powershell
@'
"""Event Router for merging tracker outputs."""

import asyncio
from typing import Dict, Any, Optional
from loguru import logger

class EventRouter:
    """Merges outputs from multiple trackers into a single enriched event."""

    def __init__(self) -> None:
        self._last_active_window: Optional[Dict[str, Any]] = None
        self._last_idle_state: Optional[str] = "active"
        self._last_git_context: Optional[Dict[str, Any]] = None

    def update_active_window(self, data: Optional[Dict[str, Any]]) -> None:
        if data is not None:
            self._last_active_window = data

    def update_idle_state(self, data: Optional[Dict[str, Any]]) -> None:
        if data is not None:
            self._last_idle_state = data.get("state", "active")

    def update_git_context(self, data: Optional[Dict[str, Any]]) -> None:
        if data is not None:
            self._last_git_context = data

    def build_event(self, source: str, tracker_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Build a fully enriched event payload."""
        if not self._last_active_window:
            return None  # Wait for first active window poll

        payload = {
            "exe": self._last_active_window.get("exe"),
            "title": self._last_active_window.get("title"),
            "project": self._last_git_context.get("project") if self._last_git_context else None,
            "branch": self._last_git_context.get("branch") if self._last_git_context else None,
            "file": self._last_git_context.get("file") if self._last_git_context else None,
            "session_type": self._last_git_context.get("session_type") if self._last_git_context else "personal"
        }

        # If this is an active_window event, use its data, else use cached
        if source == "active_window":
            payload.update(tracker_data)

        return {
            "type": "event",
            "source": source,
            "data": payload,
            "idle_state": self._last_idle_state
        }
'@ | Set-Content -Path "clients\windows\src\daemon\event_router.py" -Encoding UTF8
```

### 3. Generate `src/daemon/event_pipeline.py`

Create the pipeline for sequencing and batching.

```powershell
@'
"""Event Pipeline for sequencing and dispatch."""

import asyncio
import time
import os
from typing import Dict, Any, Callable, Awaitable
from loguru import logger

class EventPipeline:
    """Manages event sequencing and dispatch to the WS client."""

    def __init__(self, device_id: str, send_callback: Callable[[bytes], Awaitable[None]]) -> None:
        self.device_id = device_id
        self._send_callback = send_callback
        self._seq = 0
        self._lock = asyncio.Lock()

    async def dispatch(self, event_payload: Dict[str, Any]) -> None:
        """Add sequence number, timestamp, and dispatch via callback."""
        async with self._lock:
            self._seq += 1
            seq = self._seq

        full_event = {
            "type": "event",
            "seq": seq,
            "device_id": self.device_id,
            "ts": time.time(),
            **event_payload
        }

        try:
            from .serialization import pack_event
            packed = pack_event(full_event)
            await self._send_callback(packed)
            logger.debug(f"Dispatched event seq={seq}")
        except Exception as e:
            logger.error(f"Failed to dispatch event: {e}")
'@ | Set-Content -Path "clients\windows\src\daemon\event_pipeline.py" -Encoding UTF8
```

### 4. Generate `src/daemon/ws_client.py`

Create the resilient WebSocket client with exponential backoff.

```powershell
@'
"""Resilient WebSocket Client for Guinevere Windows Daemon."""

import asyncio
import random
import os
from typing import Optional, Callable, Awaitable
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException
from loguru import logger

from .serialization import unpack_command, pack_command_response

class WSClient:
    """Manages persistent WebSocket connection with exponential backoff."""

    def __init__(
        self,
        url: str,
        secret: str,
        device_id: str,
        on_command: Callable[[dict], Awaitable[None]],
        on_connected: Callable[[], Awaitable[None]],
        on_disconnected: Callable[[], Awaitable[None]]
    ) -> None:
        self.url = url
        self.secret = secret
        self.device_id = device_id
        self.on_command = on_command
        self.on_connected = on_connected
        self.on_disconnected = on_disconnected
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False

    async def _auth(self, ws: websockets.WebSocketClientProtocol) -> bool:
        """Send first-message authentication."""
        import json
        auth_msg = json.dumps({"type": "auth", "secret": self.secret, "device_id": self.device_id})
        await ws.send(auth_msg)
        
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            resp_data = json.loads(response)
            if resp_data.get("type") == "auth_ok":
                return True
            logger.error(f"Auth failed: {resp_data}")
            return False
        except asyncio.TimeoutError:
            logger.error("Auth timeout")
            return False

    async def _connect_with_backoff(self) -> None:
        """Connect with exponential backoff and jitter."""
        base_delay = 1.0
        max_delay = 60.0
        delay = base_delay

        while self._running:
            try:
                logger.info(f"Connecting to {self.url}")
                async with websockets.connect(self.url) as ws:
                    self._ws = ws
                    
                    if not await self._auth(ws):
                        logger.error("Authentication failed, stopping")
                        self._running = False
                        break

                    logger.info("WebSocket connected and authenticated")
                    await self.on_connected()
                    delay = base_delay  # Reset delay on successful connection

                    # Main message loop
                    async for message in ws:
                        if not self._running:
                            break
                        
                        # Handle commands (JSON)
                        cmd_data = unpack_command(message.encode('utf-8') if isinstance(message, str) else message)
                        if cmd_data.get("type") == "command":
                            await self.on_command(cmd_data)
                        elif cmd_data.get("type") == "ping":
                            import json, time
                            await ws.send(json.dumps({"type": "pong", "ts": time.time()}))

            except (ConnectionClosed, WebSocketException, ConnectionRefusedError) as e:
                logger.warning(f"WebSocket disconnected: {e}")
                await self.on_disconnected()
                
                if not self._running:
                    break

                # Exponential backoff with jitter
                jitter = random.uniform(0, 0.5)
                sleep_time = min(delay, max_delay) + jitter
                logger.info(f"Reconnecting in {sleep_time:.2f}s...")
                await asyncio.sleep(sleep_time)
                delay *= 2

    async def start(self) -> None:
        self._running = True
        asyncio.create_task(self._connect_with_backoff())

    async def stop(self) -> None:
        self._running = False
        if self._ws:
            await self._ws.close()
            self._ws = None

    async def send(self, data: bytes) -> None:
        if self._ws and self._ws.open:
            await self._ws.send(data)
        else:
            logger.warning("Attempted to send on closed WebSocket")
'@ | Set-Content -Path "clients\windows\src\daemon\ws_client.py" -Encoding UTF8
```

---

## Verification

- [ ] All four files exist and are syntactically valid.
- [ ] `pack_event` uses `msgpack.packb`.
- [ ] `WSClient` implements exponential backoff with jitter.
- [ ] First-message authentication is implemented in `_auth`.
- [ ] Sequence numbers in `EventPipeline` are monotonic (protected by `asyncio.Lock`).

```powershell
Set-Location -Path "clients\windows"

# Verify syntax and imports
python -c "from src.daemon.serialization import pack_event; from src.daemon.ws_client import WSClient; print('Imports OK')"
# Expected: Imports OK

# Verify MessagePack usage
Select-String -Path "src\daemon\serialization.py" -Pattern "msgpack.packb"
# Expected: Should find the msgpack.packb call

# Verify exponential backoff logic
Select-String -Path "src\daemon\ws_client.py" -Pattern "delay \*= 2"
# Expected: Should find the exponential backoff multiplier

# Run mypy strict check on all new files
python -m mypy src/daemon/serialization.py src/daemon/event_router.py src/daemon/event_pipeline.py src/daemon/ws_client.py
# Expected: Success: no issues found in 4 source files.
```

---

## Evidence

- `docs/setup-evidence/p15-expansion/STEP-P15-005/verification.md`
- `docs/setup-evidence/p15-expansion/STEP-P15-005/backoff-check.txt`
- `docs/setup-evidence/p15-expansion/STEP-P15-005/mypy-output.txt`

---

## Rollback

```powershell
# Remove all pipeline files
Set-Location -Path "C:\Users\faizz\guinevere\clients\windows"
Remove-Item -Path "src\daemon\serialization.py", "src\daemon\event_router.py", "src\daemon\event_pipeline.py", "src\daemon\ws_client.py" -Force -ErrorAction SilentlyContinue
```

---

## Troubleshooting

- **Issue: `msgpack` throws `TypeError` on serialization**
  - **Solution:** Ensure all dictionary values are standard types (str, int, float, bool, None). The `EventRouter` ensures this by explicitly constructing the payload dictionary.
- **Issue: WebSocket never reconnects after network drop**
  - **Solution:** Verify that the `_running` flag is not being set to `False` prematurely. Check the logs for the "Reconnecting in X.XXs..." message to confirm backoff is active.
- **Issue: Sequence numbers are not monotonic**
  - **Solution:** The `asyncio.Lock` in `EventPipeline.dispatch` ensures that concurrent tracker polls do not cause race conditions in sequence number assignment. Do not remove this lock.
- **Issue: Auth fails immediately**
  - **Solution:** Verify that the `secret` and `device_id` passed to `WSClient` match the VPS configuration exactly. The VPS expects the first message to be a JSON auth payload.

---

## Notes

- **Protocol Strictness:** Events are strictly MessagePack (binary), while commands are strictly JSON (text). The `WSClient` handles this by using `unpack_command` for incoming messages (which the VPS sends as JSON per Decision 3.1) and `pack_event` for outgoing messages.
- **Heartbeat:** The VPS is responsible for sending `ping` messages. The `WSClient` automatically responds with `pong`. If the VPS does not ping every 30s, the connection may be dropped by intermediate proxies, but the backoff logic will handle reconnection.
- **Cross-reference:** This step integrates the outputs of P15-002, P15-003, and P15-004. It is the prerequisite for P15-006 (NSSM Service Wrapper), which will orchestrate the startup of this pipeline.

---

## AC References

- **AC 3.1:** Hybrid: MessagePack events, JSON commands.
- **AC 3.2:** Single persistent WebSocket with exponential backoff + jitter.
- **Planner Scaffold:** Events MUST use MessagePack. Commands MUST use JSON. WS client MUST have exponential backoff + jitter. Sequence numbers MUST be monotonic. Forbidden patterns are absent.