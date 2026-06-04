---
title: "P15 Windows Daemon — Planner Gate v1.0"
status: "Planner Gate — Awaiting Parent Verification"
date: "2026-06-04"
phase: "P15.1 (MVP)"
owner: "Faiz"
executor: "Guinevere"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
---

# P15 Windows Daemon — Planner Gate v1.0

## 1. Master Todo — Atomic Task List

| Step | Title | Parallelism | Est. Time | Dependency |
|------|-------|-------------|-----------|------------|
| P15-001 | Project Scaffold + Base Tracker ABC | parallel | 1h | — |
| P15-002 | Active Window Tracker (win32gui + psutil) | sequential | 1.5h | P15-001 |
| P15-003 | Idle Tracker (GetLastInputInfo, graduated) | sequential | 1h | P15-001 |
| P15-004 | Git Context Tracker (traversal + project mapping) | sequential | 1h | P15-001 |
| P15-005 | Event Pipeline (MessagePack + EventRouter + WS Client) | sequential | 2h | P15-002, P15-003, P15-004 |
| P15-006 | NSSM Service Wrapper + Config | sequential | 1h | P15-005 |
| P15-007 | VPS WebSocket Endpoint (FastAPI + ConnectionManager) | parallel | 2h | — |
| P15-008 | Command Protocol (ACK-based, Redis DB4 pub/sub) | sequential | 1.5h | P15-007 |
| P15-009 | Consent Gate Integration (belt-and-suspenders) | sequential | 1h | P15-007, P15-008 |
| P15-010 | Discord `/pc` Command (status + session override) | sequential | 1h | P15-009 |
| P15-011 | Observability (Prometheus metrics + Grafana dashboard) | sequential | 2h | P15-009 |
| P15-012 | TimescaleDB Migration (windows_events hypertable) | parallel | 0.5h | — |
| P15-013 | Test Suite (unit + integration + E2E) | sequential | 3h | P15-005, P15-007, P15-008 |
| P15-014 | Integration Test: End-to-End Daemon ↔ VPS | sequential | 1h | P15-013 |
| P15-015 | Deployment + Smoke Test | sequential | 1h | P15-014 |

**Total estimated: ~20h of sub-agent implementation time.**

---

## 2. Dependency Map

```
P15-001 (Scaffold) ─┬─→ P15-002 (Active Window)  ─┐
                     ├─→ P15-003 (Idle)            ├─→ P15-005 (Event Pipeline) → P15-006 (NSSM)
                     └─→ P15-004 (Git Context)     ─┘

P15-007 (WS Endpoint) ─→ P15-008 (Commands) ─→ P15-009 (Consent) ─→ P15-010 (Discord)
                                                       └───────────→ P15-011 (Observability)

P15-012 (DB Migration) [independent, parallel]

P15-005 + P15-007 + P15-008 ─→ P15-013 (Tests) ─→ P15-014 (E2E) ─→ P15-015 (Deploy)
```

### Parallelism Groups

| Wave | Steps | Rationale |
|------|-------|-----------|
| **Wave 1** | P15-001, P15-007, P15-012 | Independent scaffolds: daemon project, VPS endpoint, DB migration |
| **Wave 2** | P15-002, P15-003, P15-004 | All 3 trackers depend only on P15-001 (BaseTracker ABC) |
| **Wave 3** | P15-005, P15-008 | Event pipeline + command protocol (depend on trackers + WS endpoint) |
| **Wave 4** | P15-006, P15-009 | NSSM wrapper + consent gate (depend on pipeline + commands) |
| **Wave 5** | P15-010, P15-011 | Discord command + observability (depend on consent integration) |
| **Wave 6** | P15-013, P15-014 | Test suite (depends on all implementation) |
| **Wave 7** | P15-015 | Deployment (depends on all tests pass) |

### Audit Batches

| Batch | Steps | Timing |
|-------|-------|--------|
| Audit-1 | P15-001, P15-007, P15-012 | After Wave 1 parent verification |
| Audit-2 | P15-002, P15-003, P15-004 | After Wave 2 parent verification |
| Audit-3 | P15-005, P15-008 | After Wave 3 parent verification |
| Audit-4 | P15-006, P15-009, P15-010, P15-011 | After Wave 4-5 parent verification |
| Audit-5 | P15-013, P15-014, P15-015 | After Wave 6-7 parent verification |

---

## 3. Research Inputs

| Agent | Type | Key Findings |
|-------|------|-------------|
| P7 Surveillance Architecture | explore | Event flow: POST→HMAC→Redis DB2→Consumer. Classification: active_window/idle=RESTRICTED. Consent gate: fail-closed. |
| P5 Agent Loop | explore | Memory: `store_episode(session, content, source="windows-daemon")`. Guardian: 30s heartbeat. |
| Network Topology | explore | VPS 100.94.104.22, Windows 100.112.201.124 via Tailscale. Caddy binds 100.94.104.22. All Docker on 127.0.0.1. |
| Codebase Structure | explore | src/ has 10 modules. systemd naming: `guinevere-<component>.service`. Daemon at `clients/windows/`. |
| Windows Daemon Patterns | librarian | NSSM wrapper. win32gui.GetForegroundWindow. GetLastInputInfo + GetTickCount64. websockets asyncio. |
| WebSocket Bridge Patterns | librarian | FastAPI @app.websocket + first-message auth. MessagePack serialization. Exponential backoff + jitter. |
| PC Context Awareness | librarian | WakaTime heartbeats. Git repo detection (.git traversal). VS Code extension API. OpenCode plugin hooks. |
| WebSocket Endpoints | explore | ZERO WebSocket in codebase. Building from scratch. Documented at `/surveillance/windows/ws`. |
| StepPrompts Gold Standard | explore | 14-section template, 60-90 lines/step, copy-paste commands. Old P11 was anti-pattern. |
| Discord Commands | explore | Programmatic `self.tree.command()`. `is_faiz_interaction()`. Embeds via EmbedData/EmbedField. All ephemeral. |
| systemd Templates | explore | Type=exec, User=guinevere, Slice=guinevere.slice. EnvironmentFile per service. Security hardening. |
| Redis Pub/Sub | explore | DB4 allocated but UNUSED. No .publish()/.subscribe() in src/. DB2 for surveillance buffer. Port 6380. |

---

## 4. Known State

### Existing Infrastructure
- **FastAPI app**: `src/main.py` on VPS, behind Caddy at `100.94.104.22:8443`
- **Redis**: Docker, port 6380, DB0-DB5 assigned (ADR-030), DB4 pub/sub unused
- **PostgreSQL**: Docker, port 5433, `guinevere` database
- **TimescaleDB**: Extension enabled, `surveillance_events` hypertable exists for Android
- **Tailscale**: Active mesh, VPS 100.94.104.22, Windows 100.112.201.124
- **Surveillance pipeline**: `src/surveillance/` — router, consumer, auth, replay, classification, consent_gate, safe_mode, redis_buffer, timescale, secrets, models
- **Discord bot**: Programmatic command registration, Faiz-only ephemeral commands
- **systemd services**: 7 existing services following `guinevere-<component>.service` pattern

### What Does NOT Exist (Green Field)
- No WebSocket endpoints in codebase
- No ConnectionManager
- No Redis pub/sub usage
- No `clients/` directory
- No Windows daemon code
- No `guinevere-windows-sync.service`

---

## 5. Binding Decisions (27 Decisions from 4 Research Rounds)

### Round 1 — Scope & Identity
| # | Decision |
|---|----------|
| 1.1 | Hybrid (C): MVP = dev context (active window, idle, git), surveillance expandable |
| 1.2 | Always-on via NSSM, <1% CPU idle |
| 1.3 | Bidirectional: VPS→daemon commands in MVP |
| 1.4 | Standalone at `clients/windows/`, separate deployment |

### Round 2 — Data & Enrichment
| # | Decision |
|---|----------|
| 2.1 | Enriched: exe + title + project + branch + repo-relative path |
| 2.2 | Git traversal MVP, VS Code extension post-MVP |
| 2.3 | Graduated idle: 2m away / 5m idle / 15m deep_idle |
| 2.4 | Hybrid sessions: auto-detect + Discord override |
| 2.5 | Interface-first BaseTracker ABC |

### Round 3 — Architecture
| # | Decision |
|---|----------|
| 3.1 | Hybrid: MessagePack events, JSON commands |
| 3.2 | Single persistent WebSocket |
| 3.3 | Tailscale ACL + static shared secret |
| 3.4 | Redis DB2 buffer → existing consumer pipeline |
| 3.5 | Request/response with ACK (10s timeout) |
| 3.6 | NSSM service wrapper |

### Round 4 — Integration & Scope
| # | Decision |
|---|----------|
| 4.1 | Add to existing FastAPI app (no separate service) |
| 4.2 | SurveillanceConsumer writes memory via existing pipeline |
| 4.3 | Belt-and-suspenders: consent gate server-side + pause command to daemon |
| 4.4 | Project-based auto-detection (config mapping) |
| 4.5 | Full dashboard: Prometheus metrics + Grafana + alerting rules |
| 4.6 | Accept MVP boundary (see §8 IN/OUT scope) |

---

## 6. Collision Scan

| Shared Resource | Steps Touching It | Mitigation |
|-----------------|-------------------|------------|
| `src/surveillance/` | P15-007 (new ws file), P15-009 (consent mod) | P15-007 creates NEW file, P15-009 modifies EXISTING — sequential |
| `src/discord/` | P15-010 (new command file) | New file only, no modification of existing commands |
| `src/observability/` | P15-011 (metrics + dashboard) | New metrics file + Grafana JSON — no modification of existing |
| Redis DB2 | P15-005 (daemon push), P15-007 (VPS receive) | Daemon pushes via WS→VPS→rpush, no direct Redis from daemon |
| Redis DB4 | P15-008 (command pub/sub) | Green field, no existing usage |
| `docs/setup-evidence/` | All steps write evidence | Each step writes to own `STEP-P15-NNN/` directory |
| TimescaleDB | P15-012 (migration), P15-009 (consumer) | Migration first (parallel wave 1), consumer reads from existing tables |
| Caddy config | None | No Caddy changes needed — WS endpoint behind existing FastAPI proxy |
| `AGENTS.md` / ADR-Index | Parent-only | Parent handles doc sync post-implementation |

### Verdict: No blocking collisions detected. Sequential dependencies handle shared files.

---

## 7. Files to Create/Modify

### Windows Daemon (`clients/windows/`)

| File | Action | Step |
|------|--------|------|
| `clients/windows/pyproject.toml` | CREATE | P15-001 |
| `clients/windows/src/daemon/__init__.py` | CREATE | P15-001 |
| `clients/windows/src/daemon/base_tracker.py` | CREATE | P15-001 |
| `clients/windows/src/daemon/active_window.py` | CREATE | P15-002 |
| `clients/windows/src/daemon/idle_tracker.py` | CREATE | P15-003 |
| `clients/windows/src/daemon/git_context.py` | CREATE | P15-004 |
| `clients/windows/src/daemon/event_pipeline.py` | CREATE | P15-005 |
| `clients/windows/src/daemon/event_router.py` | CREATE | P15-005 |
| `clients/windows/src/daemon/ws_client.py` | CREATE | P15-005 |
| `clients/windows/src/daemon/serialization.py` | CREATE | P15-005 |
| `clients/windows/src/daemon/config.py` | CREATE | P15-006 |
| `clients/windows/src/daemon/shutdown.py` | CREATE | P15-006 |
| `clients/windows/src/daemon/__main__.py` | CREATE | P15-006 |
| `clients/windows/nssm/install.bat` | CREATE | P15-006 |
| `clients/windows/nssm/uninstall.bat` | CREATE | P15-006 |
| `clients/windows/nssm/daemon.json` | CREATE | P15-006 |
| `clients/windows/tests/test_base_tracker.py` | CREATE | P15-013 |
| `clients/windows/tests/test_active_window.py` | CREATE | P15-013 |
| `clients/windows/tests/test_idle_tracker.py` | CREATE | P15-013 |
| `clients/windows/tests/test_git_context.py` | CREATE | P15-013 |
| `clients/windows/tests/test_event_pipeline.py` | CREATE | P15-013 |
| `clients/windows/tests/test_ws_client.py` | CREATE | P15-013 |
| `clients/windows/tests/conftest.py` | CREATE | P15-013 |
| `clients/windows/.env.example` | CREATE | P15-006 |
| `clients/windows/README.md` | CREATE | P15-015 |

### VPS Server-Side (`src/`)

| File | Action | Step |
|------|--------|------|
| `src/surveillance/windows_ws.py` | CREATE | P15-007 |
| `src/surveillance/windows_models.py` | CREATE | P15-007 |
| `src/surveillance/windows_commands.py` | CREATE | P15-008 |
| `src/surveillance/windows_consent.py` | CREATE | P15-009 |
| `src/discord/commands/pc.py` | CREATE | P15-010 |
| `src/observability/windows_metrics.py` | CREATE | P15-011 |
| `tests/surveillance/test_windows_ws.py` | CREATE | P15-013 |
| `tests/surveillance/test_windows_commands.py` | CREATE | P15-013 |
| `tests/surveillance/test_windows_consent.py` | CREATE | P15-013 |
| `tests/discord/commands/test_pc.py` | CREATE | P15-013 |
| `tests/integration/test_windows_e2e.py` | CREATE | P15-014 |

### Database

| File | Action | Step |
|------|--------|------|
| `migrations/NNN_add_windows_events_hypertable.sql` | CREATE | P15-012 |

### Grafana

| File | Action | Step |
|------|--------|------|
| `grafana/dashboards/windows-daemon.json` | CREATE | P15-011 |
| `grafana/alerts/windows-daemon-disconnected.json` | CREATE | P15-011 |

### Evidence

| File | Action | Step |
|------|--------|------|
| `docs/setup-evidence/p15-expansion/STEP-P15-NNN/*` | CREATE | Each step |

---

## 8. Implementation Design

### 8.1 MVP Scope Boundary

**IN scope (P15.1):**
- Windows daemon: active window tracker, idle tracker, git context tracker
- BaseTracker ABC + 3 concrete trackers
- Single WebSocket connection (WSS over Tailscale)
- MessagePack events, JSON commands
- VPS WebSocket endpoint in existing FastAPI
- Redis DB2 buffer integration
- Consent gate + safe mode pause command (belt-and-suspenders)
- ACK-based command protocol (10s timeout)
- NSSM service wrapper
- `/pc` Discord command (status + session override)
- Prometheus metrics + Grafana dashboard + alerting
- TimescaleDB windows_events hypertable
- Unit tests + integration tests + E2E tests

**OUT of scope (post-MVP):**
- Clipboard tracker
- VS Code extension
- OpenCode plugin integration
- Screenshot/camera capture
- Audio recording
- Session summary memory episodes (periodic work summaries)
- Multi-monitor deep support
- Application-specific deep integrations
- Wearable correlation

### 8.2 Protocol Specification

#### Event Format (MessagePack, daemon → VPS)

```python
{
    "type": "event",           # Fixed
    "seq": 42,                 # Monotonic sequence number
    "device_id": "faizzzz",    # Tailscale hostname
    "ts": 1717500000.123,      # Unix timestamp (float)
    "source": "active_window", # Tracker name
    "data": {                  # Tracker-specific payload
        "exe": "code.exe",
        "title": "p15-windows-daemon.md — guinevere",
        "project": "guinevere",
        "branch": "main",
        "file": "docs/setup-evidence/plans/p15-windows-daemon.md",
        "session_type": "guinevere-dev"
    },
    "idle_state": "active"     # active | away | idle | deep_idle
}
```

#### Command Format (JSON, VPS → daemon)

```python
# Request
{
    "type": "command",
    "id": "uuid-4",
    "cmd": "get_status",       # get_status | pause | resume | get_screenshot
    "params": {}
}

# ACK (daemon → VPS, within 10s)
{
    "type": "ack",
    "id": "uuid-4"
}

# Result (daemon → VPS)
{
    "type": "result",
    "id": "uuid-4",
    "status": "ok",            # ok | error
    "data": { ... }
}
```

#### Heartbeat (bidirectional, every 30s)

```python
{"type": "ping", "ts": 1717500000}   # VPS → daemon
{"type": "pong", "ts": 1717500001}   # daemon → VPS
```

### 8.3 Connection Lifecycle

```
1. Daemon starts → load config → init trackers
2. Connect: wss://100.94.104.22:8443/surveillance/windows/ws
3. First message: {"type": "auth", "secret": "<shared_secret>", "device_id": "faizzzz"}
4. Server validates secret + Tailscale IP → respond {"type": "auth_ok"}
5. Enter main loop:
   - Trackers poll on intervals (active_window: 2s, idle: 5s, git: 30s)
   - On state change → serialize MessagePack → send via WS
   - Every 30s → respond to server ping with pong
   - On command received → ACK within 10s → execute → send result
6. On disconnect → exponential backoff (1s, 2s, 4s, 8s, max 60s + jitter)
7. On SIGTERM/SIGINT → graceful shutdown → close WS → stop trackers
```

### 8.4 BaseTracker ABC

```python
class BaseTracker(ABC):
    """Interface-first design (Decision 2.5)."""

    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    async def start(self) -> None: ...

    @abstractmethod
    async def stop(self) -> None: ...

    @abstractmethod
    async def poll(self) -> Optional[dict]: ...

    @property
    @abstractmethod
    def poll_interval(self) -> float: ...
```

### 8.5 Graduated Idle States (Decision 2.3)

```python
IDLE_THRESHOLDS = {
    "active": 0,       # < 2 minutes
    "away": 120,       # 2 minutes
    "idle": 300,       # 5 minutes
    "deep_idle": 900,  # 15 minutes
}
```

### 8.6 Session Auto-Detection (Decision 4.4)

```python
# nssm/daemon.json
{
    "session_mapping": {
        "guinevere": "guinevere-dev",
        "office-app": "work",
        "client-project-x": "work"
    },
    "default_session": "personal"
}
```

### 8.7 Consent Gate Integration (Decision 4.3)

**Server-side (hard guarantee):**
1. `windows_consent.py` checks `safe_mode` status from Redis before processing events
2. If safe_mode active → drop event silently, increment `events_dropped` counter
3. This is the FAIL-CLOSED guarantee — even if pause command fails, events are dropped

**Client-side (traffic reduction):**
1. When safe_mode activates, VPS sends `{"cmd": "pause"}` to daemon
2. Daemon enters paused state: trackers still poll but events are NOT sent
3. When safe_mode deactivates, VPS sends `{"cmd": "resume"}`
4. Daemon resumes sending events

### 8.8 Grafana Dashboard Panels (Decision 4.5)

| Panel | Type | Metric |
|-------|------|--------|
| Daemon Connection Status | Stat (green/red) | `guinevere_windows_daemon_connected` |
| Events Received (rate) | Time series | `rate(guinevere_windows_events_received_total[5m])` |
| Events by Source | Pie chart | `guinevere_windows_events_received_total` by source |
| Events Dropped (safe mode) | Counter | `guinevere_windows_events_dropped_total` |
| WebSocket Reconnections | Counter | `guinevere_windows_ws_reconnects_total` |
| Command Latency | Histogram | `guinevere_windows_command_latency_seconds` |
| Idle State Timeline | State timeline | `guinevere_windows_idle_state` |
| Active App Top 10 | Bar gauge | Top apps by event count |
| Session Type Distribution | Pie chart | Events by session_type |

### 8.9 Alerting Rules (Decision 4.5)

| Alert | Condition | Severity |
|-------|-----------|----------|
| DaemonDisconnected | `guinevere_windows_daemon_connected == 0` for >5m | warning |
| HighEventDropRate | `rate(events_dropped[5m]) > 10` for >10m | info |
| CommandTimeout | `rate(command_timeout_total[5m]) > 0.5` | warning |
| NoEventsReceived | `increase(events_received_total[15m]) == 0` while connected | info |

---

## 9. Token/Secret Handling

| Secret | Location | Access Pattern |
|--------|----------|----------------|
| WebSocket shared secret | VPS: `.env.windows-ws`; Daemon: `.env` | Loaded at startup, never logged |
| Tailscale IP | Hardcoded `100.94.104.22` or config | Not a secret |
| Redis password | Existing `REDIS_PASSWORD` env | Shared with existing infrastructure |

### Rules
- Shared secret generated via `secrets.token_urlsafe(32)` — stored in `.env.windows-ws` on VPS and `.env` on daemon
- Secret NEVER committed to git — `.env` in `.gitignore`
- Secret NEVER logged — all auth logging redacts secret value
- Secret rotation: manual for MVP, documented runbook

---

## 10. Evidence Paths

Each step writes evidence to `docs/setup-evidence/p15-expansion/STEP-P15-NNN/`:

| Step | Evidence Directory |
|------|-------------------|
| P15-001 | `STEP-P15-001/` |
| P15-002 | `STEP-P15-002/` |
| P15-003 | `STEP-P15-003/` |
| P15-004 | `STEP-P15-004/` |
| P15-005 | `STEP-P15-005/` |
| P15-006 | `STEP-P15-006/` |
| P15-007 | `STEP-P15-007/` |
| P15-008 | `STEP-P15-008/` |
| P15-009 | `STEP-P15-009/` |
| P15-010 | `STEP-P15-010/` |
| P15-011 | `STEP-P15-011/` |
| P15-012 | `STEP-P15-012/` |
| P15-013 | `STEP-P15-013/` |
| P15-014 | `STEP-P15-014/` |
| P15-015 | `STEP-P15-015/` |

### Required Evidence Files per Step
- `verification.md` — 12-section verification report
- `auditor-gate.md` — Auditor verdict and findings
- Step-specific artifacts (config files, test output, screenshots)

---

## 11. Auditor Matrix

| Step | Auditor Focus Areas | Safety Domain |
|------|-------------------|---------------|
| P15-001 | Code structure, ABC correctness, dependency versions | — |
| P15-002 | win32 API correctness, state change detection, no secret leakage in titles | Data minimization |
| P15-003 | GetTickCount64 overflow handling, threshold accuracy | — |
| P15-004 | Git traversal safety, path sanitization, no `.git/config` secrets | Data minimization |
| P15-005 | MessagePack schema correctness, reconnection logic, sequence numbers | — |
| P15-006 | NSSM config correctness, log rotation, graceful shutdown | — |
| P15-007 | WebSocket auth, connection limits, error handling, no type suppression | Security boundary |
| P15-008 | ACK timeout handling, command validation, Redis DB4 isolation | — |
| P15-009 | **Consent gate correctness, fail-closed behavior, safe-mode integration** | **SAFETY-CRITICAL** |
| P15-010 | Permission check (`is_faiz_interaction`), ephemeral-only, embed format | — |
| P15-011 | Metric naming conventions, dashboard JSON validity, alert thresholds | — |
| P15-012 | Migration idempotency, hypertable schema, index correctness | — |
| P15-013 | Test coverage, mock quality, no skipped tests | — |
| P15-014 | E2E test realism, network simulation, error path coverage | — |
| P15-015 | Deployment script safety, NSSM install, smoke test | — |

---

## 12. Rollback Plan

| Component | Rollback Strategy |
|-----------|-------------------|
| Windows daemon | NSSM stop + uninstall. Daemon is standalone — stopping it has zero VPS impact. |
| VPS WebSocket endpoint | Remove route from FastAPI. Existing endpoints unaffected. |
| Redis DB4 | Flush DB4 only. No other component uses DB4. |
| TimescaleDB | DROP TABLE `windows_events`. No foreign keys from other tables. |
| Discord `/pc` command | Unregister command from bot tree. Other commands unaffected. |
| Grafana | Delete dashboard JSON + alert rules. Other dashboards unaffected. |

### Full Rollback Order
1. NSSM stop on Windows (daemon disconnects)
2. Restart FastAPI (removes WS endpoint)
3. Flush Redis DB4
4. DROP TABLE windows_events
5. Remove Grafana dashboard + alerts
6. Unregister Discord `/pc` command

---

## 13. Tracker Sync Plan

| Doc/Index | Action | Timing |
|-----------|--------|--------|
| ADR-Index | Add ADR-035 (Windows Daemon Architecture) if new ADR needed | Post-implementation |
| `docs/README.md` | Add P15 evidence link | Post Wave 7 |
| SurveillanceDataPolicy Appendix A | Add Windows daemon sources with classification | Post-implementation |
| Technical Architecture | Add Windows daemon component diagram | Post-implementation |
| Evidence index | Add p15-expansion entry | Per-step |

---

## 14. Caveats

1. **win32gui requires Windows** — Trackers can only be tested on Windows. CI/CD for daemon must run on Windows or use mocks.
2. **Tailscale IP may change** — Config should support hostname resolution, not just hardcoded IP.
3. **MessagePack version pinning** — Must pin `msgpack` version on both sides to avoid serialization incompatibility.
4. **Redis DB4 is green field** — First usage of pub/sub in codebase. Pattern needs to be documented for future consumers.
5. **Consent gate latency** — Redis cache check adds ~1ms per event. Acceptable for daemon event rates (~1 event/2s).
6. **Grafana dashboard provisioning** — Requires Grafana provisioning config update to load new dashboard JSON.
7. **NSSM log rotation** — NSSM stdout logging needs `AppStdout` + `AppStderr` + `AppRotateFiles` configuration.

---

## 15. Per-Step Verification Scaffold

### P15-001: Project Scaffold + Base Tracker ABC

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/pyproject.toml`, `clients/windows/src/daemon/__init__.py`, `clients/windows/src/daemon/base_tracker.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, `except:`, bare `except Exception` without log |
| Required Commands | `python -c "from src.daemon.base_tracker import BaseTracker; print(BaseTracker.__abstractmethods__)"` → exit 0, prints abstract methods |
| Evidence Requirements | `STEP-P15-001/verification.md` |
| Hard Rejection Criteria | BaseTracker missing any of: `name`, `start`, `stop`, `poll`, `poll_interval` |

### P15-002: Active Window Tracker

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/src/daemon/active_window.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, password/token regex in title field, `except:` |
| Required Commands | `python -c "from src.daemon.active_window import ActiveWindowTracker; print('OK')"` → exit 0 |
| Evidence Requirements | `STEP-P15-002/verification.md` |
| Hard Rejection Criteria | Must implement BaseTracker. Must detect state change only (not blind polling). Must include title regex redaction for sensitive patterns. |

### P15-003: Idle Tracker

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/src/daemon/idle_tracker.py` |
| Forbidden Patterns | `GetTickCount` (32-bit — must use `GetTickCount64`), `as any`, `# type: ignore` |
| Required Commands | `python -c "from src.daemon.idle_tracker import IdleTracker; t = IdleTracker(); print(t.poll_interval)"` → exit 0 |
| Evidence Requirements | `STEP-P15-003/verification.md` |
| Hard Rejection Criteria | Must use GetTickCount64 (not 32-bit). Must implement graduated thresholds (2m/5m/15m). Must handle 49.7-day overflow. |

### P15-004: Git Context Tracker

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/src/daemon/git_context.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, reading `.git/config` credentials, `os.system` |
| Required Commands | `python -c "from src.daemon.git_context import GitContextTracker; print('OK')"` → exit 0 |
| Evidence Requirements | `STEP-P15-004/verification.md` |
| Hard Rejection Criteria | Must traverse up for `.git`. Must read HEAD for branch. Must produce repo-relative paths. Must NOT read `.git/config` or any credentials file. |

### P15-005: Event Pipeline

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/src/daemon/event_pipeline.py`, `event_router.py`, `ws_client.py`, `serialization.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, `except:`, JSON for events (must use MessagePack) |
| Required Commands | `python -c "from src.daemon.serialization import pack_event, unpack_event; e = pack_event({'type':'event','seq':1}); print(len(e))"` → exit 0, prints small int |
| Evidence Requirements | `STEP-P15-005/verification.md` |
| Hard Rejection Criteria | Events MUST use MessagePack. Commands MUST use JSON. WS client MUST have exponential backoff + jitter. Sequence numbers MUST be monotonic. |

### P15-006: NSSM Service Wrapper

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/src/daemon/config.py`, `shutdown.py`, `__main__.py`, `clients/windows/nssm/install.bat`, `uninstall.bat`, `daemon.json`, `clients/windows/.env.example` |
| Forbidden Patterns | Hardcoded secrets, `as any`, `# type: ignore` |
| Required Commands | `python -m src.daemon --help` → exit 0 (or equivalent config check) |
| Evidence Requirements | `STEP-P15-006/verification.md` |
| Hard Rejection Criteria | NSSM install script must be idempotent. Config must load from env + JSON. Graceful shutdown must stop all trackers and close WS. |

### P15-007: VPS WebSocket Endpoint

| Field | Value |
|-------|-------|
| Expected Files | `src/surveillance/windows_ws.py`, `src/surveillance/windows_models.py` |
| Forbidden Patterns | `as any`, `@ts-ignore`, `except:`, `@app_commands.command` decorator |
| Required Commands | `python -c "from src.surveillance.windows_ws import router; print(router.prefix)"` → exit 0 |
| Evidence Requirements | `STEP-P15-007/verification.md` |
| Hard Rejection Criteria | Must authenticate first message. Must handle disconnect cleanup. Must integrate with existing FastAPI app. Must use existing Redis connection pattern. |

### P15-008: Command Protocol

| Field | Value |
|-------|-------|
| Expected Files | `src/surveillance/windows_commands.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, `except:`, Redis DB other than DB4 |
| Required Commands | `python -c "from src.surveillance.windows_commands import CommandManager; print('OK')"` → exit 0 |
| Evidence Requirements | `STEP-P15-008/verification.md` |
| Hard Rejection Criteria | Must use Redis DB4 pub/sub only. Must implement ACK timeout (10s). Must generate unique command IDs. Must handle duplicate ACK rejection. |

### P15-009: Consent Gate Integration

| Field | Value |
|-------|-------|
| Expected Files | `src/surveillance/windows_consent.py` |
| Forbidden Patterns | `as any`, `# type: ignore`, `except:`, bypass safe_mode check, `pass` in consent check |
| Required Commands | `python -m pytest tests/surveillance/test_windows_consent.py -v` → exit 0 |
| Evidence Requirements | `STEP-P15-009/verification.md` |
| Hard Rejection Criteria | **SAFETY-CRITICAL**: Must drop events when safe_mode active (fail-closed). Must send pause/resume commands. Must NEVER allow event through during safe_mode. Must increment drop counter. |

### P15-010: Discord `/pc` Command

| Field | Value |
|-------|-------|
| Expected Files | `src/discord/commands/pc.py` |
| Forbidden Patterns | `@app_commands.command`, non-ephemeral responses, `as any`, `# type: ignore` |
| Required Commands | `python -c "from src.discord.commands.pc import register_pc_commands; print('OK')"` → exit 0 |
| Evidence Requirements | `STEP-P15-010/verification.md` |
| Hard Rejection Criteria | Must use programmatic `self.tree.command()`. Must use `is_faiz_interaction()`. ALL responses MUST be ephemeral. Must use EmbedData/EmbedField. |

### P15-011: Observability

| Field | Value |
|-------|-------|
| Expected Files | `src/observability/windows_metrics.py`, `grafana/dashboards/windows-daemon.json`, `grafana/alerts/windows-daemon-disconnected.json` |
| Forbidden Patterns | `as any`, `# type: ignore`, invalid Prometheus metric names |
| Required Commands | `python -c "from src.observability.windows_metrics import register_windows_metrics; print('OK')"` → exit 0 |
| Evidence Requirements | `STEP-P15-011/verification.md` |
| Hard Rejection Criteria | Must include all 5 core metrics (connected gauge, events counter, dropped counter, reconnects counter, command latency histogram). Dashboard JSON must be valid. Alert rules must be syntactically correct. |

### P15-012: TimescaleDB Migration

| Field | Value |
|-------|-------|
| Expected Files | `migrations/NNN_add_windows_events_hypertable.sql` |
| Forbidden Patterns | `DROP TABLE`, `TRUNCATE`, non-idempotent operations |
| Required Commands | `psql -h localhost -p 5433 -U guinevere -d guinevere -f migrations/NNN_add_windows_events_hypertable.sql` → exit 0 |
| Evidence Requirements | `STEP-P15-012/verification.md` |
| Hard Rejection Criteria | Must be idempotent (IF NOT EXISTS). Must create hypertable. Must include required columns per SurveillanceDataPolicy §6.1. |

### P15-013: Test Suite

| Field | Value |
|-------|-------|
| Expected Files | All test files listed in §7 |
| Forbidden Patterns | `@pytest.mark.skip` without justification, `assert True`, mock everything without testing logic |
| Required Commands | `python -m pytest tests/surveillance/test_windows_*.py tests/discord/commands/test_pc.py -v --tb=short` → exit 0 |
| Evidence Requirements | `STEP-P15-013/verification.md` |
| Hard Rejection Criteria | All tests must pass. No skipped tests without documented reason. Must include: happy path, error path, edge case for each component. |

### P15-014: E2E Integration Test

| Field | Value |
|-------|-------|
| Expected Files | `tests/integration/test_windows_e2e.py` |
| Forbidden Patterns | Hardcoded secrets, real network calls without mock/stub |
| Required Commands | `python -m pytest tests/integration/test_windows_e2e.py -v` → exit 0 |
| Evidence Requirements | `STEP-P15-014/verification.md` |
| Hard Rejection Criteria | Must test: connect → auth → event flow → command → disconnect → reconnect. Must test consent gate blocks events in safe mode. |

### P15-015: Deployment + Smoke Test

| Field | Value |
|-------|-------|
| Expected Files | `clients/windows/README.md` |
| Forbidden Patterns | Committed secrets, hardcoded paths without config override |
| Required Commands | `nssm status GuinevereWindowsDaemon` → RUNNING (on actual Windows machine) |
| Evidence Requirements | `STEP-P15-015/verification.md` |
| Hard Rejection Criteria | Daemon must start, connect, send at least 1 event, respond to 1 command, and shut down cleanly. README must include full install/config/run guide. |

---

## 16. Execution Checklist

- [ ] Parent reads and approves this planner gate
- [ ] `docs/setup-evidence/p15-expansion/` directory created
- [ ] Shared secret generated and stored in `.env.windows-ws` (VPS) and documented for daemon `.env`
- [ ] Wave 1 agents spawned: P15-001, P15-007, P15-012
- [ ] Wave 1 parent verification + audit
- [ ] Wave 2 agents spawned: P15-002, P15-003, P15-004
- [ ] Wave 2 parent verification + audit
- [ ] Wave 3 agents spawned: P15-005, P15-008
- [ ] Wave 3 parent verification + audit
- [ ] Wave 4 agents spawned: P15-006, P15-009
- [ ] Wave 5 agents spawned: P15-010, P15-011
- [ ] Wave 4-5 parent verification + audit
- [ ] Wave 6 agents spawned: P15-013, P15-014
- [ ] Wave 6 parent verification + audit
- [ ] Wave 7: P15-015 deployment + smoke test
- [ ] Final audit batch
- [ ] Doc sync (ADR-Index, docs/README.md, SurveillanceDataPolicy appendix)
- [ ] Final report to Faiz

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-06-04 | Guinevere (Sisyphus) | Initial planner gate. 15 atomic steps, 7 waves, 5 audit batches. Based on 27 decisions from 4 research rounds and 12 parallel research agents. |
