# P23 Research — Windows Desktop Action (Safe PowerShell + Process Isolation)

> Status: RESEARCH
> Date: 2026-06-25
> Scope: P23 Embodied Operations / Personal OS Action Layer — Windows desktop executor

## 1. Objective

Investigate how a future P23 Windows desktop action executor can safely control Faiz's Windows PC. The executor must build on the existing P15 Windows daemon plan, reuse proven Windows APIs and service patterns, and satisfy the project's safety, consent, and isolation requirements. This research answers: what action surfaces are available, how should the executor be isolated, and what primitives can be safely exposed.

## 2. Sources Consulted

### 2.1 Microsoft Learn (retrieved 2026-06-25)

| Topic | URL | Retrieval date |
|---|---|---|
| Start-Process cmdlet | https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/start-process | 2026-06-25 |
| Stop-Process cmdlet | https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/stop-process | 2026-06-25 |
| about_Execution_Policies | https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_execution_policies | 2026-06-25 |
| schtasks commands | https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/schtasks | 2026-06-25 |
| SetInformationJobObject | https://learn.microsoft.com/en-us/windows/win32/api/jobapi2/nf-jobapi2-setinformationjobobject | 2026-06-25 |

### 2.2 Local P15 code and research

| Path | Lines | Relevance |
|---|---|---|
| `research-reports/p15/r1-daemon-current-state.md` | 1-194 | Green-field status, planned `clients/windows/` layout, Tailscale mesh, consent/safe-mode integration points |
| `docs/setup-evidence/plans/p15-windows-daemon.md` | 1-727 | P15 planner gate: NSSM service, WS over Tailscale, command/ACK protocol, consent gate, fail-closed safe mode |
| `src/observability/windows_metrics.py` | 1-207 | Existing Prometheus metrics for Windows daemon; can be extended for P23 action metrics |
| `src/life_kernel/sensor_adapters/wearable_adapter.py` | 1-21 | Placeholder wearable adapter; shows where `.env.wearable` / `android/` style config fits |
| `research-reports/p15/r7-win32gui-patterns.md` | 1-948 | Win32 API patterns for active window, idle time, process enumeration; psutil/wmi usage |
| `research-reports/p15/r8-msgpack-patterns.md` | 1-1011 | MessagePack/WebSocket client with reconnection and exponential backoff |
| `research-reports/p15/r6-nssm-patterns.md` | 1-827 | NSSM service wrapper, graceful shutdown, signal handling, restart policy |

## 3. Findings

### 3.1 Existing Windows infra map

P15 planned a Windows daemon at `clients/windows/` (`r1-daemon-current-state.md:19-39`). It is intended to run as an NSSM service, connect to the VPS over WebSocket through Tailscale, and send surveillance events (active window, idle). The same footprint can host P23's desktop executor as a sibling process.

Key reusable pieces:

- **NSSM service wrapper**: `research-reports/p15/r6-nssm-patterns.md` documents direct venv python.exe invocation, log rotation, restart/backoff, and graceful shutdown. P23 should use the same wrapper but with a separate service name, e.g. `GuinevereDesktopExecutor`.
- **WebSocket/Tailscale transport**: `docs/setup-evidence/plans/p15-windows-daemon.md:279-345` specifies MessagePack events, JSON commands, first-message auth, ACK-based protocol, and 30s heartbeat. P23 actions can reuse the same WS connection by adding a new command family (`desktop_action`).
- **Consent gate / safe mode**: `docs/setup-evidence/plans/p15-windows-daemon.md:397-407` describes server-side fail-closed safe mode plus client-side `pause`/`resume`. P23 must gate every action class through this mechanism.
- **Prometheus metrics**: `src/observability/windows_metrics.py` already exposes `guinevere_windows_*` families. P23 should add action-specific counters/histograms.
- **Wearable/Android style env**: `src/life_kernel/sensor_adapters/wearable_adapter.py:1-21` is a placeholder, but the convention implies a `.env.wearable` and an `android/` directory. P23 should mirror this with `.env.desktop` and `clients/windows/desktop_executor/`.

Proposed P23 process layout on the Windows PC:

```
+------------------------------------------+
|  P15 daemon (NSSM service)               |
|  - active_window, idle trackers            |
|  - WS client to VPS over Tailscale         |
+------------------------------------------+
                  |
                  | local WS / named pipe
                  v
+------------------------------------------+
|  P23 desktop executor (NSSM service)       |
|  - action primitive dispatcher             |
|  - PowerShell runner                       |
|  - job-object sandbox                      |
+------------------------------------------+
```

### 3.2 Windows action surfaces

#### 3.2.1 PowerShell execution

Microsoft Learn (2026-06-25) documents the core primitives. The following table summarises the key parameters that P23 must control:

| Cmdlet | Parameter | P23 usage | Risk control |
|---|---|---|---|
| `Start-Process` | `-FilePath` | app or signed script path | allow-list + hash check |
| `Start-Process` | `-ArgumentList` | arguments to pass | escape user input; reject embedded `"&"` or `";"` |
| `Start-Process` | `-WorkingDirectory` | workspace root | force to `%USERPROFILE%\Guinevere\workspace` |
| `Start-Process` | `-WindowStyle` | `Normal` / `Hidden` | `Hidden` requires L3 |
| `Start-Process` | `-Verb` | forbidden | block `RunAs`, `runas`, `runasuser` |
| `Start-Process` | `-Wait` | optional | use for short scripts only |
| `Start-Process` | `-PassThru` | always | capture process object for PID logging |
| `Stop-Process` | `-Id` | target PID | prefer over `-Name` to avoid killing unrelated instances |
| `Stop-Process` | `-Force` | allowed | only after consent |
| `Stop-Process` | `-Confirm` | omitted | consent handled by executor, not cmdlet |

Example safe invocation:

```powershell
Start-Process -FilePath "notepad.exe" `
              -ArgumentList "`"C:\Users\faizz\Guinevere\workspace\notes.txt`"" `
              -WindowStyle Normal -PassThru
```

`about_Execution_Policies` describes `Restricted`, `AllSigned`, `RemoteSigned`, `Unrestricted`, etc. P23 should require `AllSigned` for any script run via `run_script`. Scripts written by the executor itself should be self-signed with a locally generated code-signing cert, or rejected if not signed.

PowerShell gives rich process control but is also a high-risk surface. The executor must:

- Validate the executable/script path against an allow-list or known hash.
- Never pass user-controlled strings directly into `-ArgumentList` without escaping.
- Never use `-Verb RunAs` or any run-as-admin verb.
- Log every command and its exit code.

#### 3.2.2 Windows Task Scheduler (`schtasks`)

Microsoft Learn (2026-06-25) notes that `schtasks.exe` schedules commands and programs to run periodically or at a specific time. It requires Administrator membership to schedule, view, or change all tasks on the local computer. This is a critical constraint: P23's `schedule_task` primitive must run only in user-space task folders (e.g. `\Guinevere\User\...`) and must not require admin rights. If `schtasks` proves impossible without elevation, the primitive should fall back to an Python-scheduled background thread within the executor process.

Suggested minimal command form (user-only, no admin):

```batch
schtasks /create /tn "Guinevere\User\reminder-001" /tr "pythonw.exe ..." /sc once /st 09:00
```

If this returns an access-denied error, the executor must log the failure and use its internal scheduler instead of prompting for elevation.

#### 3.2.3 App automation (pywinauto / UIAutomation)

For windows that expose automation interfaces, `pywinauto` and `uiautomation` can click buttons, fill fields, and read controls. These are fragile and can trigger UAC prompts for elevated targets. P23 should treat UI automation as L3 (explicit consent per use) and require a visible consent indicator before any automation runs.

Recommended constraints:

- Target only non-elevated processes.
- Fail immediately if the target window title changes or the control cannot be found.
- Record a short audit trace of the control path attempted.

#### 3.2.4 File operations

File reads/writes must be confined to a workspace directory (e.g. `%USERPROFILE%\Guinevere\workspace`). Writes outside this scope are forbidden. Reads outside the workspace require L3 approval and an audit log entry.

Workspace layout proposal:

```
%USERPROFILE%\Guinevere\workspace\
  ├── inbox\
  ├── outbox\
  ├── backups\
  └── tmp\
```

### 3.3 Isolation / job-object design

Microsoft Learn (2026-06-25) documents `SetInformationJobObject`, which sets limits for a Windows job object. P23 should run every action inside a job object with at least the following limits:

- CPU rate control (`JOBOBJECT_CPU_RATE_CONTROL_INFORMATION`)
- Working-set memory limit (`JOBOBJECT_EXTENDED_LIMIT_INFORMATION`)
- Active process limit (prevent fork bombs)
- Kill-on-job-close so the executor can reliably terminate spawned children

The executor itself runs as a separate process from the P15 daemon. It communicates with the daemon over a local, authenticated loopback WebSocket (or named pipe) and with the VPS over the same authenticated WS/Tailscale channel used by P15. It must never run as admin by default.

Job-object limit configuration (illustrative):

| Limit class | Info class | Suggested value | Purpose |
|---|---|---|---|
| CPU rate | `JobObjectCpuRateControlInformation` | 25% per action | prevent CPU hogging |
| Memory | `JobObjectExtendedLimitInformation` | 512 MB working set | cap memory |
| Active processes | `JobObjectBasicLimitInformation` | 8 | prevent fork bombs |
| UI restrictions | `JobObjectBasicUIRestrictions` | deny clipboard + display | isolate desktop effects |
| Kill on close | `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE` | enabled | reliable cleanup |

Illustrative Python sketch using `ctypes`:

```python
import ctypes
from ctypes import wintypes

kernel32 = ctypes.windll.kernel32

def create_job_object(name: str) -> int:
    h_job = kernel32.CreateJobObjectW(None, name)
    if not h_job:
        raise ctypes.WinError(ctypes.get_last_error())
    return h_job

def set_kill_on_job_close(h_job: int) -> None:
    class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_longlong),
            ("PerJobUserTimeLimit", ctypes.c_longlong),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_void_p),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    info = JOBOBJECT_BASIC_LIMIT_INFORMATION()
    info.LimitFlags = 0x00002000  # JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
    kernel32.SetInformationJobObject(
        h_job, 1, ctypes.byref(info), ctypes.sizeof(info)
    )
```

This is a research sketch only; production code must use proper error handling and constants from `winnt.h`.

### 3.4 Action primitive table

| Primitive | API / Tool | Risk tier | Consent scope | Notes |
|---|---|---|---|---|
| `launch_app` | `Start-Process` | L2 | `p23:desktop:launch_app` | Allow-list path; block `-Verb RunAs`; log PID |
| `kill_app` | `Stop-Process` | L2 | `p23:desktop:kill_app` | Target by PID/name; kill-on-job-close fallback |
| `run_script` | `powershell -ExecutionPolicy AllSigned -File ...` | L3 | `p23:desktop:run_script` | Require signed PS1; hash check; 30s timeout |
| `schedule_task` | `schtasks /create` or internal scheduler | L3 | `p23:desktop:schedule_task` | User-space only; no admin |
| `file_read` | Python `open()` | L2 | `p23:desktop:file_read` | Workspace only unless L3 |
| `file_write` | Python `open()` | L3 | `p23:desktop:file_write` | Workspace only; backup before overwrite |
| `notify_toast` | `winrt.windows.ui.notifications` | L1 | `p23:desktop:notify` | Visible indicator; no admin |

All primitives default to L2/L3; there is no L1 autonomous write primitive.

### 3.5 Consent / classification

P23 desktop actions are surveillance-class because they control Faiz's PC. Per the sibling research `p23-policy-gate-risk-classification-research.md`, this maps to CRITICAL tier. Requirements:

- Explicit per-action-class consent under `p23:desktop` scope.
- Visible indicator (tray icon / toast) whenever the executor is active.
- `HARD STOP` honored immediately; all pending actions are cancelled and fail-closed.
- Consent is time-bound and revocable; revocation triggers executor self-pause.

Consent flow:

```
VPS command -> local consent check -> user indicator (if required)
                                    -> execute / deny / queue
```

Risk tier mapping (from sibling research):

| Tier | Autonomous | Consent | Desktop examples |
|---|---|---|---|
| L1 | yes (read-only) | scope grant | `notify_toast`, status query |
| L2 | no | per-class grant | `launch_app`, `kill_app`, `file_read` |
| L3 | no | per-action explicit | `run_script`, `file_write`, `schedule_task` |
| L4 | never | never | installers, disable Defender, touch other profiles |

### 3.6 Safety constraints

- **Never auto-elevate**: UAC prompts are treated as failure conditions, not bypass targets.
- **Never disable Defender / security tools**: forbidden at policy level.
- **Never touch other users' profiles**: workspace is scoped to the running user's profile.
- **Never install software without L3 approval**: `launch_app` may run portable/installed apps only; installers are blocked.
- **Distress handling**: D2+ distress freezes L2/L3 desktop actions. L1 read-only primitives such as status queries may continue.

### 3.7 Rollback design

Each write-capable primitive must support rollback:

| Primitive | Rollback action |
|---|---|
| `launch_app` | `kill_app` by captured PID |
| `kill_app` | none (irreversible) — require L2 consent and log |
| `run_script` | best-effort cleanup; scripts may declare a rollback hook |
| `schedule_task` | `schtasks /delete` for the created task |
| `file_write` | restore from `backups\` if original existed |
| `notify_toast` | dismiss toast (best-effort) |

Rollback is best-effort and must be logged. Irreversible actions (`kill_app`) require explicit consent and cannot be rolled back; they must be clearly marked in the audit log.

### 3.8 Failure modes and self-debug

| Failure | Mitigation |
|---|---|
| Process hang | Job-object timeout + `TerminateProcess` fallback |
| Script error | Capture stderr/exit code; return structured error; no retry without user confirmation |
| UAC prompt | Treat as failure; log and reject; never interact with UAC |
| App not found | Return clear error; suggest allow-list update |
| WS disconnect | Reuse P15 exponential backoff (`r8-msgpack-patterns.md:423-434`) |
| Consent revoked | Immediate cancellation; fail-closed; notify user |

Self-debug data to emit for every action:

- Request ID and timestamp
- Primitive name and normalized parameters
- Consent decision and reason
- Exit code / exception / timeout status
- Resource usage from the job object
- Rollback attempted and outcome

Example action request/response payload over the WS command channel:

```json
{
  "type": "desktop_action",
  "id": "018ff3e0-...",
  "primitive": "launch_app",
  "params": {
    "file_path": "notepad.exe",
    "arguments": ["workspace\\notes.txt"]
  },
  "consent_token": "p23:desktop:launch_app:..."
}
```

```json
{
  "type": "desktop_action_result",
  "id": "018ff3e0-...",
  "status": "ok",
  "pid": 12345,
  "audit_id": "..."
}
```

## 4. Implications for P23 Design

- Reuse P15's `clients/windows/` project layout; add `desktop_executor/` alongside `daemon/`.
- Extend the existing WS command protocol with `desktop_action` messages, using the same ACK and safe-mode integration.
- Implement a PowerShell runner module that enforces signed scripts, path allow-lists, and no-elevation rules.
- Implement a Windows job-object wrapper for resource limits and reliable cleanup.
- Extend `src/observability/windows_metrics.py` with action metrics (attempts, denials, failures, latencies).
- Add `.env.desktop` configuration for executor settings, scoped similarly to `.env.wearable`.
- Add a backup/restore helper for `file_write` rollback.

## 5. Risks / Open Questions

1. **Elevation requirement**: `schtasks` and some app launches may require admin rights. How do we gracefully degrade without ever prompting for UAC?  
2. **Signed PS1 friction**: Generating/ trusting a self-signed cert on the local machine is doable but adds setup friction. Is an allow-list + hash check sufficient for v1?  
3. **UIAutomation fragility**: App automation can be brittle and can surface UAC prompts. Should it be deferred beyond P23 MVP?  
4. **Overlap with P15 daemon**: Should the executor run in the same process or a separate process? Separate is safer but doubles service overhead.  
5. **Rollback granularity**: File writes need a backup/restore strategy; should this be built into `file_write` or handled by a separate journal?

## 6. Recommendations to Planner

- Keep P23 desktop executor as a separate process from the P15 daemon, sharing only the WebSocket/Tailstack connection and local config.
- Start with a minimal primitive set: `launch_app`, `kill_app`, `run_script` (signed only), `file_read/write` (workspace only), `notify_toast`.
- Defer `schedule_task` and UI automation to post-MVP unless explicit use cases justify them.
- Mandate job-object isolation from day one; it is the primary defense against runaway actions.
- Reuse the P15 consent/safe-mode code path (`windows_consent.py`, `safe_mode.py`) by extending it with `p23:desktop` scopes.
- Add visible indicator and HARD STOP hotkey integration before any action is tested end-to-end.
- Add backup/restore to `file_write` from the start; retrofitting rollback is harder.

## 7. Verdict

P23 desktop action is feasible as a safe, isolated executor building directly on the P15 Windows daemon foundation. The Microsoft Learn primitives (`Start-Process`, `Stop-Process`, `schtasks`, `SetInformationJobObject`) are well-documented and sufficient for the proposed action surface. The critical success factor is strict policy enforcement — signed scripts only, workspace-scoped writes, job-object limits, no admin, and fail-closed consent — rather than the availability of Windows APIs.
