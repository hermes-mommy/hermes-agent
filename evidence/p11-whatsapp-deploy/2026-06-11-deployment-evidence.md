# P11 WhatsApp Channel Deployment Evidence

| Field | Value |
|---|---|
| Date | 2026-06-11 |
| Verdict | **PASS** |
| Operator | Faiz |
| Agent | Guinevere |
| Service | `guinevere-whatsapp.service` |
| Final PID | 590172 |
| Final start time | Thu 2026-06-11 19:19:19 WIB |

---

## 1. What Was Done

Deployed and verified the Guinevere WhatsApp channel end-to-end on production VPS (`guinevere-vps`). This included:

- WhatsApp bridge with Hermes AI runtime integration
- Neonize (Go-based WhatsApp protocol library) with Python bindings
- systemd service hardening with proper sandboxing
- Live inbound→Hermes→reply cycle with real conversational messages

## 2. Root Causes Found & Fixed

### Fix 1: Hermes Import Path Shadowing

**Root cause**: The WhatsApp bridge's `_hermes_getter()` callback imported Hermes modules, but `sys.path` under systemd service context placed the repo root (containing a bare `plugins/` package with only `memory/`) ahead of site-packages (containing the full `plugins/browser/`, `plugins/web/`, `plugins/spotify/` provider trees). This caused `ModuleNotFoundError: No module named 'plugins.browser'` when Hermes tried to register browser/web providers.

**Fix**: Added `sys.path` sanitization in `src/channels/whatsapp/bridge.py`:
- `_get_hermes_runtime()`: temporarily replaces `sys.path` with `_sanitized_sys_path()` during Hermes import, restores in `finally`
- `_sanitized_sys_path()`: moves repo root and cwd to tail of path list so installed site-packages' `plugins/` wins over the bare stub

**Commit**: `0c3c339 fix(p11): sanitize hermes import path for whatsapp bridge`

### Fix 2: Systemd Sandbox Denying Hermes Log Writes

**Root cause**: After the import-path fix, Hermes loaded successfully but the service fell back with `Ada kendala internal di jalur WhatsApp`. Journal showed:
```
whatsapp_hermes_error: [Errno 30] Read-only file system: '/home/guinevere/.hermes/logs/agent.log'
```
The systemd unit had `ProtectSystem=strict` + `ProtectHome=read-only` with no `ReadWritePaths` entry for Hermes logs.

**Fix**:
- Repo template `deploy/systemd/guinevere-whatsapp.service`: added `ReadWritePaths=/home/guinevere/.hermes/logs`
- Live systemd drop-in `/etc/systemd/system/guinevere-whatsapp.service.d/10-hermes-logs.conf` created with the same entry

## 3. Live Proof Results

### 3.1 Outbound Test via Admin Endpoint

Added minimal `POST /admin/send-test` to `service.py` `HealthHandler`:
- Endpoint: `POST http://127.0.0.1:8095/admin/send-test`
- Body: `{"message":"tes admin endpoint dari guinevere mama","target":"6281234084693@s.whatsapp.net"}`
- Response: `200 OK`, `ok: true`, message ID `3EB0EFE4D6783C01490BB3`

### 3.2 User Reply → Hermes Processing → Reply Sent

User replied "Hai mama" to the test message. Full cycle proven:

| Event | Details |
|---|---|
| `wa.message.received` | inbound, `byte_length=8`, `message_id=AC769F0026512F948EE565F8BDC3906F` |
| `conversation turn` | `msg='Hai mama'`, `model=ds/deepseek-v4-flash`, `provider=9router`, `in=8267 out=201 total=8468`, `latency=7.8s` |
| `persona_plugin_session_start` | + `persona_plugin_inject` (Y4_WARM) |
| `Turn ended` | `reason=text_response(finish_reason=stop)` |
| `wa.message.processed` | outbound, `latency_ms=16023.92`, `byte_length=135` |
| `wa.message.sent` | outbound, `byte_length=135` |

### 3.3 Final Metrics

```
whatsapp_connected{device="faiz"} = 1.0
whatsapp_messages_received_total{device="faiz"} = 2.0
whatsapp_messages_sent_total{device="faiz"} = 3.0
```

### 3.4 Service State at Proof

```
MainPID=590172
ActiveEnterTimestamp=Thu 2026-06-11 19:19:19 WIB
ActiveState=active
SubState=running
ProtectHome=read-only
ReadWritePaths=/home/guinevere/data/whatsapp /home/guinevere/code/guinevere/secrets /opt/guinevere /home/guinevere/.hermes/logs
```

## 4. Files Changed

| File | Change |
|---|---|
| `src/channels/whatsapp/bridge.py` | Added `_get_hermes_runtime()`, `_sanitized_sys_path()`, `sys.path` sanitization for Hermes import |
| `deploy/systemd/guinevere-whatsapp.service` | Added `ReadWritePaths=/home/guinevere/.hermes/logs` |
| `src/channels/whatsapp/service.py` (VPS only) | Added `POST /admin/send-test` endpoint in `HealthHandler` |

## 5. Non-Blocking Warnings (Known, Pre-existing)

| Warning | Status |
|---|---|
| `milestone_init_failed` — `asyncio.run()` called inside running event loop | Non-blocking, persona subsystem still initializes |
| `whatsapp_typing_presence_failed` — neonize JID missing fields `RawAgent,Device,Integrator` | Non-blocking, typing indicator only; messages still send |
| `nous` plugin — `No module named 'hermes_cli.dashboard_auth'` | Non-blocking, plugin disabled |

## 6. Validation Results

| Check | Result |
|---|---|
| `lsp_diagnostics` on `bridge.py` | Clean |
| `uv run pytest tests/channels/whatsapp/ -q` | 4 passed (router + ops_commands) |
| Exact-env Hermes probe on VPS | PASS — all providers registered, bridge available |
| Live outbound send | PASS — message delivered to `6281234084693` |
| Live inbound→Hermes→reply | PASS — "Hai mama" → Hermes processed → reply sent (135 bytes) |
| `/health` endpoint | `ready`, `connection_state=connected` |
| VPS WhatsApp test suite | 28 passed |

## 7. Evidence Artifacts

| Artifact | Path |
|---|---|
| This evidence file | `evidence/p11-whatsapp-deploy/2026-06-11-deployment-evidence.md` |
| systemd unit template (repo) | `deploy/systemd/guinevere-whatsapp.service` |
| systemd drop-in (VPS) | `/etc/systemd/system/guinevere-whatsapp.service.d/10-hermes-logs.conf` |
| service.py backup (VPS) | `/home/guinevere/code/guinevere/src/channels/whatsapp/service.py.bak` |

## 8. Boundary Compliance

- No secrets committed (Discord token, API keys, DB passwords absent from diffs)
- No raw surveillance data in artifacts
- No consent boundary violations
- No type-safety suppressions (`as any`, `@ts-ignore`, etc.)
- No empty error handlers

## 9. Rollback Plan

1. Restore `bridge.py` to pre-patch: `git checkout HEAD~1 -- src/channels/whatsapp/bridge.py`
2. Restore `service.py` from backup on VPS: `cp service.py.bak service.py`
3. Remove systemd drop-in: `sudo rm /etc/systemd/system/guinevere-whatsapp.service.d/10-hermes-logs.conf`
4. Restore service template: `git checkout HEAD~1 -- deploy/systemd/guinevere-whatsapp.service`
5. Restart: `sudo systemctl daemon-reload && sudo systemctl restart guinevere-whatsapp.service`

## 10. Acceptance Criteria Mapping

| Criterion | Status | Evidence |
|---|---|---|
| WhatsApp bridge connects to WhatsApp servers | PASS | `whatsapp_connected=1.0`, `Successfully authenticated` |
| Inbound messages received | PASS | `wa.message.received` with `byte_length=8` |
| Hermes processes inbound | PASS | `conversation turn` with `in=8267 out=201 latency=7.8s` |
| Reply sent to user | PASS | `wa.message.sent` with `byte_length=135` |
| `/health` returns ready | PASS | `status=ready, connection_state=connected` |
| systemd service stable | PASS | `active/running`, no restarts after final fix |
| VPS test suite passes | PASS | 28 passed |

---

**Final Verdict: PASS**

All critical acceptance criteria met. Full inbound→Hermes→reply cycle proven on live production service with real conversational messages. Two root causes found and fixed (import path shadowing + systemd sandbox). Three non-blocking warnings documented as known pre-existing issues.
