# P11 WhatsApp Deploy Evidence

- Date: 2026-06-11
- Environment: Guinevere VPS (`faiz-prod-01`)
- Operator: Faiz
- Scope: P11 production deploy status through successful pairing/connectivity, pending final live whitelisted-message proof
- Status: PARTIAL / PAIRED / WAITING FOR LIVE MESSAGE PROOF

## 1. Deploy Objective

Deploy the P11 WhatsApp channel stack to the production VPS, verify service/runtime health, verify the VPS WhatsApp test suite, and proceed through live pairing and E2E validation.

## 2. Code / Artifact Delivery

### Pushed commits

The following P11 deploy stack was pushed to `origin/main`:

1. `87d745f feat(p11): add whatsapp transport foundation`
2. `b924cba feat(p11): add whatsapp safety gates`
3. `c231ca4 feat(p11): add whatsapp runtime orchestration`
4. `57f830f test(p11): add whatsapp test suite`
5. `6b8e5e7 chore(p11): add whatsapp deploy artifacts`
6. `486c2e0 docs(p11): add whatsapp operations runbook`
7. `d6e768c fix(p11): align whatsapp service health and unit paths`
8. `e4f8e93 fix(p11): schedule neonize callbacks on service loop`

### VPS artifact state

The exact P11 stack was copied into the dirty VPS checkout under `/home/guinevere/code/guinevere/`:

- `src/channels/whatsapp/`
- `tests/channels/whatsapp/`
- `deploy/systemd/guinevere-whatsapp.service`
- `deploy/env/.env.whatsapp.template`
- `runbooks/whatsapp-operations.md`
- `pyproject.toml`

## 3. Dependency Install / Runtime Base

### VPS Python / repo / venv

Verified:

- Repo root: `/home/guinevere/code/guinevere`
- Venv: `/home/guinevere/code/guinevere/.venv/bin/python`
- Python: `3.12.3`

### Neonize install

`uv sync` succeeded on VPS and `neonize` imported successfully.

Verified import result:

```text
NEONIZE_IMPORT_OK 0.3.18.post0
```

User-approved fallback `neonize-bot[all]` was **not needed**.

## 4. Secret / Session Provisioning

### Encrypted source env

Created encrypted source file:

- `/home/guinevere/code/guinevere/secrets/.env.whatsapp`

### Runtime env

Created runtime env file:

- `/opt/guinevere/.env.whatsapp`
- owner: `root:root`
- mode: `600`

### Session dir

Created session dir:

- `/home/guinevere/data/whatsapp/session`

### Important note about SOPS

Repo `.sops.yaml` recipient and VPS age key did not match directly. Encryption was completed successfully using the actual VPS recipient/key path so that `.env.whatsapp` is still encrypted at rest.

## 5. Systemd Deployment

### Installed unit

Installed unit file:

- `/etc/systemd/system/guinevere-whatsapp.service`

### Minimum deploy blocker fixes applied before stable bring-up

The production deploy required two minimum deploy fixes:

1. **Systemd topology alignment**
   - fixed dependencies/path assumptions for this VPS
   - corrected working directory and Python path to `/home/guinevere/code/guinevere`
   - enabled terminal QR mode in `ExecStart`

2. **Health endpoint exposure**
   - added live HTTP `/health` and `/metrics` exposure on port `8095`

3. **Neonize callback scheduling fix**
   - fixed off-loop callback scheduling so QR/pair callbacks can safely schedule work onto the service event loop under systemd

## 6. Current Service Status

### systemd

Verified current service state:

```text
active
```

### Health endpoint

Verified current health response:

```json
{"status": "degraded", "connection_state": "unknown", "needs_manual": false, "session_age_seconds": 0.0, "last_check": "2026-06-10T17:21:27.274154+00:00", "degraded_reason": "connection_state=unknown", "heartbeat_stale": false, "service_running": false}
```

Interpretation:
- service process is alive
- HTTP health endpoint is live
- WhatsApp connection is **not yet established** because pairing has not happened
- degraded state is expected pre-pairing

### Metrics endpoint

Verified metrics endpoint is live. Relevant gauge observed:

```text
whatsapp_connected{device="faiz"} 0.0
```

Interpretation:
- observability is up
- device is not yet connected to WhatsApp

## 7. VPS Test Verification

Verified exact VPS command works:

```bash
cd /home/guinevere/code/guinevere && ./.venv/bin/python -m pytest tests/channels/whatsapp -q
```

Latest result:

```text
28 passed in 1.87s
```

This confirms the deployed VPS checkout and venv are functionally consistent with the local green baseline.

## 8. Journal / QR State

Verified recent journal behavior:

- QR blocks are being emitted repeatedly (`=== WHATSAPP QR START ===` / `=== WHATSAPP QR END ===`)
- service remains active while waiting for scan
- health checks continue to run
- no fresh recurrence of the earlier coroutine scheduling warning in the current post-fix run

Observed recent runtime pattern:

- QR emitted
- `Login event: timeout`
- service remains active and re-emits QR
- health remains degraded until pairing completes

## 8.1 Post-scan failure root cause and fix

After Faiz reported that scanning the QR still failed, live VPS investigation confirmed a real production bug in the original deploy:

- journal showed `Failed to pair device: failed to save device store: attempt to write a readonly database`
- root cause: Neonize was still using an implicit database name / cwd-relative device store path under a systemd sandbox with `ProtectSystem=strict`, so the paired device store could not be persisted after QR scan
- compounding issue: pair-status handling only matched fragile string tokens and could miss numeric success/error codes from `PairStatusEv`

Minimum safe fix applied:

1. `src/channels/whatsapp/neonize_client.py`
   - changed client construction to use a concrete writable DB path:
   - `self._database_path = str(self._auth.session_dir / "neonize.db")`
   - `self._client = NewClient(self._database_path, uuid=name)`
2. `src/channels/whatsapp/service.py`
   - changed service wiring to instantiate `NeonizeClient` with the explicit writable DB path derived from the auth/session dir
3. `src/channels/whatsapp/neonize_client.py`
   - patched pair-status handling so numeric success/error codes are understood, not just string-token matches

Verified result of the fix:

- writable DB file now exists on VPS at:
  - `/home/guinevere/data/whatsapp/session/neonize.db`
- service still starts cleanly after the patch
- `/health` and `/metrics` remain live
- the original readonly-database blocker is considered resolved

What remains blocked is no longer storage persistence — it is the still-incomplete live pairing itself.

## 9. What Is Complete vs Incomplete

### Complete

- Code pushed to remote
- VPS dependency install complete
- `neonize` import verified on VPS
- Encrypted `.env.whatsapp` created
- Runtime env created with locked-down permissions
- Session directory created
- systemd unit installed and enabled
- service starts and stays active
- `/health` live
- `/metrics` live
- VPS WhatsApp pytest suite passes (28/28)
- QR is being emitted for manual pairing

### Incomplete / Human-gated

- live whitelisted-message E2E has not happened yet
- final production verdict is waiting on that last live message proof

## 10. Post-Pair Verification Result

Faiz scanned the QR successfully and the service completed pairing/login.

Verified live results:
- `systemctl is-active guinevere-whatsapp.service` -> `active`
- `/health` transitioned to `ready`
- `connection_state=connected`
- `needs_manual=false`
- `whatsapp_connected{device="faiz"} 1.0`
- VPS WhatsApp pytest suite still passes: `28 passed`

Fresh root-journal proof captured:
- `Successfully paired 6287755765340:3@s.whatsapp.net`
- `Login event: success`
- `whatsapp_pair_status_event` with `status: 2`
- `Successfully authenticated`
- `whatsapp_connected_event` with `status: true`
- `whatsapp_transport_connected`

## 11. Live Message Proof Result

The final blocker is **no longer** pairing, transport, whitelist, or consent.

Fresh live proof from the current running process (`PID 432630`, start `Thu 2026-06-11 15:42:47 WIB`) shows a mixed but narrower truth:

1. **Minimal ops command path is working**
   - inbound `/ping` reached service
   - `wa.message.received`
   - `wa.message.processed`
   - `wa.message.sent`
   - user-visible reply observed in WhatsApp screenshot: `pong 2026-06-11T08:48:45.765038+00:00`

2. **Plain conversational text path failed in one observed live attempt**
   - inbound message reached service
   - `wa.message.received` logged
   - that specific attempt failed with:
     - `whatsapp_hermes_unavailable`
     - `error: "No module named 'plugins.browser'"`
   - final event was:
     - `wa.message.failed error="hermes_unavailable"`

3. **Current runtime re-probe now shows Hermes itself is healthy again**
   - a fresh direct bridge probe on the live VPS runtime now succeeds:
     - `BRIDGE_AVAILABLE True`
     - `BRIDGE_OK 452 ds/deepseek-v4-flash`
   - the bridge was also re-probed under the **actual service-equivalent env** and passed there too:
     - `HOME=/home/guinevere`
     - `WorkingDirectory=/home/guinevere/code/guinevere`
     - runtime vars loaded from `/opt/guinevere/.env.whatsapp`
   - current service remains:
     - `active`
     - `/health` = `ready`
     - `connection_state=connected`
     - `whatsapp_connected{device="faiz"} = 1.0`

Additional runtime state verified after pairing:
- whitelist Redis set was empty and has now been seeded with the runtime allowlist number from `/opt/guinevere/.env.whatsapp`
- consent Redis hash was empty and has now been seeded to granted state for WhatsApp

Current seeded runtime values:

```text
WHITELIST_AFTER ['6281234084693']
CONSENT_AFTER {'granted': 'true', 'timestamp': '2026-06-11T07:15:00Z', 'channel': 'whatsapp', 'granted_by': 'Faiz', 'revoked_at': ''}
```

## 12. Current Verdict

**P11 deploy is live, paired, connected, and command-path proven, but it is still not full PASS because one fresh normal conversational reply has not yet been re-proven on the current healthy process.**

Current exact verdict:

- **Service/runtime/dependency/deploy surfaces: PASS**
- **VPS test suite: PASS (28/28)**
- **WhatsApp live connectivity: PASS**
- **Whitelist + consent runtime gate state: SEEDED / READY**
- **Live command-path proof (`/ping`): PASS**
- **Hermes bridge runtime probe (current VPS state): PASS**
- **Fresh normal conversational live reply on current process: NOT YET RE-PROVEN**
- **Final production acceptance: PENDING ONE FRESH NORMAL CHAT REPLY PROOF**

## 13. Evidence Snippets

### Service active

```text
active
```

### Health snapshot

```json
{"status": "ready", "connection_state": "connected", "needs_manual": false, "session_age_seconds": 0.0, "last_check": "2026-06-11T07:13:50.358696+00:00", "degraded_reason": null, "heartbeat_stale": false, "service_running": false}
```

### Metrics snapshot

```text
whatsapp_connected{device="faiz"} 1.0
```

### VPS tests

```text
28 passed in 1.94s
```

## 14. Latest Recheck Snapshot

Latest skeptical recheck confirms the service is still healthy after pairing, but the final production verdict remains blocked on one real inbound/outbound live message proof.

### Latest live status

```text
systemctl is-active guinevere-whatsapp.service -> active
/health -> ready
whatsapp_connected{device="faiz"} -> 1.0
pytest tests/channels/whatsapp -> 28 passed in 1.94s
```

### Latest interpretation

- service is alive and stable under systemd
- HTTP health and metrics are reachable and now reflect a connected state
- WhatsApp is paired and authenticated successfully
- VPS test baseline remains green
- the only remaining blocker is one observed live whitelisted-message E2E reply proof

## 15. Inbound Routing Fix Deployed After Pairing

A real inbound WhatsApp message from the allowed number still produced no reply immediately after pairing. Root-cause investigation showed the service was receiving transport-level events, but dropping them before envelope creation because `raw_jid` extraction was wrong for real `MessageEv` payloads.

### Confirmed root cause

- real inbound message metadata arrived under `MessageEv.Info.MessageSource.*`
- the old implementation only inspected `Info.Sender` / `Info.Chat`
- adapter then logged `whatsapp_event_missing_raw_jid` and returned `None`
- result: the message never reached whitelist / router / bridge / reply path

### Minimum code fix applied

Patched file:

- `src/channels/whatsapp/neonize_client.py`

Key corrections:

1. extract sender/chat JIDs from `Info.MessageSource.*` first
2. populate richer metadata for downstream routing:
   - `raw_jid`
   - `chat_jid`
   - `message_id`
   - `body`
   - `push_name`
   - `timestamp`
   - `media_type`
   - `media_size_bytes`
3. improve message-type/body extraction for real WhatsApp payload branches

### Local verification before deploy

- local diagnostics on `src/channels/whatsapp/neonize_client.py`: clean
- focused local tests:

```text
5 passed in 8.64s
```

- local smoke import:

```text
LOCAL_PATCH_IMPORT_OK True True
```

### Deploy of the inbound fix

Committed and pushed:

- `a8c9dbf fix(p11): normalize inbound whatsapp message source`

Patched file copied to VPS repo path:

- `/home/guinevere/code/guinevere/src/channels/whatsapp/neonize_client.py`

### Post-deploy VPS verification

After restart, VPS service state remained healthy:

```text
systemctl is-active guinevere-whatsapp.service -> active
/health -> ready
whatsapp_connected{device="faiz"} -> 1.0
```

Fresh journal after restart proved the patched service re-authenticated cleanly:

```text
Started guinevere-whatsapp.service
Successfully authenticated
whatsapp_connected_event
whatsapp_transport_connected
```

### Remaining gap

This fix is deployed and the service is healthy again, but a **fresh live inbound message proof after the patch** has not yet been captured in evidence. Final deploy acceptance still requires one real message from the allowed number and one observed successful reply.

