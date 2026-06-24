# P14 Wearable Integration Points for P7/P8

## Scope
This report maps the **repo-grounded integration points** that P14 wearable work must connect to. It is limited to files in this repository and focuses on the surfaces P14 needs for end-to-end execution: surveillance ingestion/auth/buffering/consumer pipeline, consent gating, device registry, Discord command registration/handlers, observability/metrics/alerts, TimescaleDB migrations, and systemd/service patterns.

## Executive summary
P14 wearable work does **not** plug into a single existing wearable abstraction. Instead, it must connect to an existing **surveillance pipeline** that currently handles:
- HTTP webhook ingestion (`src/surveillance/router.py`)
- replay/HMAC auth (`src/surveillance/auth.py`, `src/surveillance/replay.py`)
- Redis DB2 buffering (`src/surveillance/redis_buffer.py`)
- consent gating (`src/surveillance/consent_gate.py`, `src/surveillance/windows_consent.py`)
- consumer processing and DB persistence (`src/surveillance/consumer.py`, `src/surveillance/timescale.py`)
- Discord status/controls (`src/discord/_entrypoint.py`, `src/discord/cmd_surveillance_status.py`, `src/discord/cmd_pc.py`)
- observability and alerting (`src/core/main.py`, `monitoring/*`, `vps-mirror/systemd-live/*`)
- TimescaleDB schema/migration (`alembic/versions/e401bb5fd274_initial_schema_47_tables.py`, `migrations/p15_add_windows_events_hypertable.sql`)

### Important mismatch for P14
The repo already has **Windows-daemon-specific** WebSocket/consent/command seams (`src/surveillance/windows_ws.py`, `windows_consent.py`, `windows_commands.py`, `windows_models.py`) and a **Windows telemetry** hypertable migration. P14 should **not assume a bespoke wearable subsystem exists**. The wearable path likely needs to reuse the same pattern family, but may require a new wearable-specific adapter rather than extending Windows-only code.

---

## 1) Surveillance ingestion / auth / buffering / consumer pipeline

### 1.1 HTTP webhook ingestion entrypoint
- **File:** `src/surveillance/router.py`
- **Function:** `receive_event(event, auth=Depends(verify_hmac))`
- **Role:** Accepts `POST /surveillance/events`, validates request model, enforces HMAC dependency, logs receipt, and best-effort pushes to Redis buffer.
- **Integration note for P14:** if wearable devices send telemetry over HTTP rather than WebSocket, this is the closest existing intake seam. P14 must preserve the `202 Accepted` best-effort behavior unless product requirements say wearable events should fail closed.
- **Pattern to reuse:** module-level buffer instance via `create_buffer()` and dependency-injected HMAC guard.
- **Mismatch watch:** this router is **HTTP-only** and currently best suited to Tasker/daemon style ingestion, not wearable-native streaming.

### 1.2 HMAC and replay protection
- **File:** `src/surveillance/auth.py`
- **Function:** `verify_hmac(request, x_signature, x_timestamp, x_nonce)`
- **Dependencies:** `src.surveillance.replay.check_nonce`, `src.surveillance.replay.validate_timestamp`, `src.surveillance.secrets.get_hmac_secret`
- **Role:** Fail-closed replay protection and HMAC-SHA256 verification.
- **Integration note for P14:** wearable ingestion must either reuse this exact header/signing pattern or define a compatible equivalent. Any wearable client must know the same signing string format:
  - `<method>:<path>:<timestamp>:<nonce>:<body-as-utf8>`
- **Mismatch watch:** existing auth assumes webhook-style request headers and Redis-backed nonce replay protection.

### 1.3 Redis DB2 buffer
- **File:** `src/surveillance/redis_buffer.py`
- **Class / factory:** `RedisSurveillanceBuffer`, `create_buffer(host="localhost", port=6380, password=None)`
- **Role:** Redis DB2 event queue with `surveillance:buffer` list key, TTL 300s, FIFO pop via pipeline, and fail-soft push behavior.
- **Integration note for P14:** wearable events likely need the same buffer semantics if P14 is not writing directly to PostgreSQL. The TTL and DB2 namespace are hard-coded assumptions in the existing pipeline.
- **Env var:** `REDIS_PASSWORD`
- **Mismatch watch:** P14 must not assume a generic queue abstraction; the current code depends on Redis DB2 + fixed list key.

### 1.4 Consumer loop and persistence path
- **File:** `src/surveillance/consumer.py`
- **Class / function:** `SurveillanceConsumer`, `main()`
- **Role:** Drains Redis DB2, maps event type to consent scope, checks consent, classifies, secret-scans clipboard text, and writes to `surveillance.events` via async DB session.
- **Integration note for P14:** wearable telemetry that should be retained must eventually land in the consumer’s persistence path or a wearable-equivalent pipeline. The consumer is the canonical place where post-buffer enrichment and DB write happen.
- **Env vars:** `REDIS_PASSWORD`, `DATABASE_URL`, `GUINEVERE_DB_PASSWORD`
- **Mismatch watch:** `main()` currently builds a PostgreSQL URL fallback for local host `5433`; wearable work must confirm whether it should target the same DB/role or a separate schema/table.

### 1.5 Timescale writer
- **File:** `src/surveillance/timescale.py`
- **Class:** `TimescaleIngester`
- **Methods:** `ingest_batch`, `ingest_single`, `get_event_count`, `get_last_event`, `_resolve_device_uuid`, `_event_to_row`, `_write_ingestion_log`
- **Role:** Bulk inserts surveillance events and writes ingestion logs.
- **Integration note for P14:** if wearable events are stored in the same time-series shape, this is the ingestion pattern to mirror. It already handles deterministic device UUID mapping and batch audit logging.
- **Mismatch watch:** `_event_to_row()` currently expects `event_type`, `occurred_at`/`timestamp`, `payload`, `summary`, `extracted_facts`. If wearable payload shape differs, P14 needs a translation layer.

---

## 2) Consent gating

### 2.1 Core consent gate
- **File:** `src/surveillance/consent_gate.py`
- **Function:** `check_consent(scope)`
- **Support functions:** `invalidate_cache(scope)`, `_query_ledger(scope)`, `_cache_result(...)`
- **Constants / scopes:** `VALID_SURVEILLANCE_SCOPES`, `CACHE_KEY_PREFIX`, `CACHE_TTL_SECONDS`
- **Role:** Fail-closed consent check against `consent.consent_ledger` with Redis DB2 cache.
- **Integration note for P14:** every wearable event must map to a consent scope before persistence. If P14 introduces new wearable event categories, the scope list must be extended here and in the dependent Discord status surfaces.
- **DB dependency:** `consent.consent_ledger`
- **Mismatch watch:** unknown scopes are immediately blocked; P14 cannot invent a new scope name without updating this file and the DB schema/policy chain.

### 2.2 Windows-specific consent gate pattern
- **File:** `src/surveillance/windows_consent.py`
- **Functions:** `process_windows_event_with_consent`, `check_windows_event_sync`, `resolve_scope`, `set_dropped_event_hook`, `get_dropped_event_count`
- **Role:** Two-layer fail-closed gate: safe-mode + consent.
- **Integration note for P14:** this is the clearest pattern for a device-specific gate wrapper. P14 should likely create a wearable-specific equivalent if wearable events need device-type-specific overrides or safety gating.
- **Mismatch watch:** this file is Windows-specific by design and already references `windows_ws.py` / `windows_commands.py` integration seams.

---

## 3) Device registry and identity

### 3.1 Device registry table
- **File:** `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
- **Table:** `surveillance.device_registry`
- **Columns:** `id`, `device_name`, `device_type`, `tailscale_ip`, `last_seen_at`, `is_active`
- **Foreign keys:** `surveillance.events.device_id`, `surveillance.ingestion_log.device_id` point to this table
- **Integration note for P14:** wearable onboarding almost certainly needs a device registry entry. The current schema uses `UUID` device IDs, names, types, optional Tailscale IP, and activity timestamps.
- **Mismatch watch:** there is **no separate wearable registry table**. P14 must decide whether wearables are represented as `device_type="wearable"` in `device_registry` or require a new table.

### 3.2 Windows device/telemetry identity pattern
- **File:** `migrations/p15_add_windows_events_hypertable.sql`
- **Columns:** `daemon_id`, `sequence_num`, `received_at`, `processed_at`, `payload`
- **Integration note for P14:** this migration shows the repo’s preferred pattern for device-scoped telemetry: immutable identity field, monotonic sequence, received timestamp, payload JSONB, Timescale hypertable, retention policy.
- **Mismatch watch:** wearable work may need a similar migration, but with device naming and payload shape tailored to the wearable transport.

### 3.3 Windows client identity conventions
- **Files:** `clients/windows/src/daemon/config.py`, `clients/windows/src/daemon/event_pipeline.py`, `clients/windows/src/daemon/ws_client.py`, `clients/windows/src/daemon/event_router.py`
- **Relevant fields / patterns:** `device_id`, `GUINEVERE_DEVICE_ID`, `GUINEVERE_WS_URL`, `GUINEVERE_WS_SECRET`
- **Integration note for P14:** wearable clients will likely need the same identity surface: stable `device_id`, secret-backed auth, and per-device routing. If wearable uses a different transport, P14 should still preserve the same conceptual contract.

---

## 4) Discord command registration / handlers

### 4.1 Slash command registration entrypoint
- **File:** `src/discord/_entrypoint.py`
- **Relevant registrations:** `surveillance-status`, `surveillance-pause`, `surveillance-resume`, `pc`, plus generic commands registered via `COMMAND_SPECS`
- **Role:** Central command registration with guild-scoped sync.
- **Integration note for P14:** if wearable work needs operator-facing commands, this is the main registration seam. Do not assume a second command registry exists.
- **Mismatch watch:** P14 should inspect whether a command is wired through explicit `self.tree.command(...)` registration or via registry stubs.

### 4.2 Surveillance status handler
- **File:** `src/discord/cmd_surveillance_status.py`
- **Function:** `surveillance_status_callback(...)`
- **Helper functions:** `_gather_consent_status`, `_gather_device_count`, `_gather_last_event_timestamp`, `_gather_buffer_size`, `_gather_consumer_health`, `_build_status_embed`
- **Role:** Displays consent state, device count, last event, buffer size, and consumer health.
- **Integration note for P14:** wearable support will need to surface its state here or via a parallel command. The current implementation has placeholders for device count and consumer health and explicitly notes that a dedicated device registry and health endpoint are not yet deployed.
- **Mismatch watch:** `_gather_device_count()` and `_gather_last_event_timestamp()` are placeholders and currently return `0` / `N/A`; P14 cannot rely on them as a complete live status source.

### 4.3 PC status handler as degraded-status template
- **File:** `src/discord/cmd_pc.py`
- **Function:** `pc_callback(...)`
- **Role:** Shows graceful degradation for a Windows daemon connection and consent state.
- **Integration note for P14:** useful as a pattern for a wearable status command. It already follows the “report unavailable rather than fake data” rule.
- **Mismatch watch:** this command explicitly says the Windows daemon path is not yet deployed, so it is a template, not a wearable implementation.

### 4.4 Command registry / stub wiring
- **File:** `src/discord/_entrypoint.py`
- **Pattern:** `COMMAND_SPECS`, `self.tree.command(name=..., description=...)(callback)`
- **Integration note for P14:** if wearable introduces a new command, verify whether it should be added as a fully wired callback or as a stub via registry. The repo mixes explicit core commands and registry-driven stubs.

---

## 5) Observability / metrics / alerts

### 5.1 Core app metrics endpoint
- **File:** `src/core/main.py`
- **Metrics:** `guinevere_requests_total`, `guinevere_request_duration_seconds`, `guinevere_health_check_failures_total`
- **Endpoint:** `/metrics`
- **Integration note for P14:** wearable integration should export its own metrics through the same Prometheus scrape path if it affects the core app or a new service that Prometheus scrapes.
- **Env/config:** app lifespan starts an LLM metrics server on `9191`, and surveillance consumer is started in lifespan as a background task.

### 5.2 Monitoring stack config
- **File:** `monitoring/prometheus/prometheus.yml`
- **Jobs:** `prometheus`, `node`, `postgresql`, `redis`, `fastapi`, `loki`, `alertmanager`, `hermes`
- **Integration note for P14:** wearable metrics should either be attached to `fastapi`/core app or added as a new scrape job if the wearable stack runs separately.
- **Mismatch watch:** this config is host-network based and assumes localhost targets. P14 must not assume arbitrary hostnames/ports without updating scrape config.

### 5.3 Alert rules
- **File:** `monitoring/prometheus/rules/guinevere-alerts.yml`
- **Relevant patterns:** SEV0/SEV1/SEV2/SEV3 alert routing, Hermes alerts, service uptime burn-rate, LLM cost alerts
- **Integration note for P14:** wearable-specific alerts should follow the same severity routing style and neutral alert text patterns. If P14 affects surveillance ingestion health, it should add rules in this family rather than inventing a separate alerting convention.
- **Mismatch watch:** this file already references some forward-looking metrics (e.g. planned Hermes-native metrics). P14 must distinguish existing metrics from placeholders.

### 5.4 Alertmanager routing
- **File:** `monitoring/alertmanager/alertmanager.yml`
- **Receivers:** `discord-critical`, `discord-warning`, `discord-info`, `gotify-critical`, `gotify-warning`
- **Integration note for P14:** any wearable alert should route through the same Discord/Gotify pipeline, with severity-based routing and neutral text.
- **Mismatch watch:** Alertmanager webhooks point back to `http://localhost:8000/internal/alertmanager/webhook`; if P14 introduces another service boundary, it must still land in this webhook workflow or equivalent.

### 5.5 Systemd service for monitoring
- **File:** `vps-mirror/systemd-live/guinevere-monitoring.service`
- **Pattern:** Docker Compose-managed monitoring stack, `ExecStart=/usr/bin/docker compose -f monitoring/compose.monitoring.yml up --remove-orphans`
- **Integration note for P14:** wearable observability should fit the existing primary-VPS monitoring stack and service model.

---

## 6) TimescaleDB migrations and retention

### 6.1 Canonical surveillance event hypertable
- **File:** `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
- **Table:** `surveillance.events`
- **Hypertable:** `create_hypertable('surveillance.events', 'occurred_at', chunk_time_interval => INTERVAL '1 day', if_not_exists => TRUE)`
- **Retention:** `add_retention_policy('surveillance.events', INTERVAL '180 days', if_not_exists => TRUE)`
- **Integration note for P14:** this is the main schema path for general surveillance events. If wearable telemetry is “surveillance-like”, this is the schema family to mirror.

### 6.2 Windows telemetry hypertable migration
- **File:** `migrations/p15_add_windows_events_hypertable.sql`
- **Table:** `surveillance.windows_events`
- **Retention:** `90 days`
- **Integration note for P14:** this is the best concrete template for a device-specific telemetry hypertable. It includes index strategy by daemon, type, and sequence.
- **Mismatch watch:** P14 should verify whether wearable data needs a new table or can reuse `surveillance.events` with a wearable-specific `event_type` and `device_type`.

### 6.3 Device-linked foreign keys
- **File:** `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
- **FKs:** `surveillance.events.device_id -> surveillance.device_registry.id`, `surveillance.ingestion_log.device_id -> surveillance.device_registry.id`
- **Integration note for P14:** any wearable ingestion path should maintain this device FK relationship so the device registry remains authoritative.

---

## 7) Systemd / service patterns

### 7.1 Surveillance consumer service
- **File:** `vps-mirror/systemd-live/guinevere-surveillance.service`
- **ExecStart:** `/home/guinevere/code/guinevere/.venv/bin/python -m src.surveillance.consumer`
- **EnvironmentFile:** `/home/guinevere/code/guinevere/.env.surveillance`
- **Integration note for P14:** this is the current service pattern for background surveillance processing. Wearable work that adds a new consumer or daemon should follow this layout.

### 7.2 Main app service / startup integration
- **File:** `src/core/main.py`
- **Role:** Starts consumer background worker during FastAPI lifespan.
- **Integration note for P14:** if wearable functionality is meant to be live in the core API process, lifespan integration may be the active route instead of a separate service.

### 7.3 Monitoring stack service
- **File:** `vps-mirror/systemd-live/guinevere-monitoring.service`
- **Role:** systemd wrapper around Docker Compose monitoring stack.
- **Integration note for P14:** if wearable observability requires additional exporters/dashboards/rules, this service is where the stack is launched.

---

## 8) Wearable-specific repo seams that matter

### 8.1 Windows WebSocket patterns likely to be mirrored, not reused verbatim
- **Files:** `src/surveillance/windows_ws.py`, `src/surveillance/windows_models.py`, `clients/windows/src/daemon/ws_client.py`, `clients/windows/src/daemon/event_pipeline.py`
- **Integration note for P14:** the repo already has a mature device-auth + event-stream model. P14 wearable work should copy the pattern family:
  - first-message auth
  - device ID in payloads
  - monotonic sequence or ordering metadata
  - buffer/persist pipeline
- **Mismatch watch:** these files are Windows-dominant in naming and assumptions. P14 should not rename them or assume the wearable transport is already present.

### 8.2 Windows command channel is a command-transport precedent
- **File:** `src/surveillance/windows_commands.py`
- **Role:** JSON command protocol over WS + Redis DB4 pub/sub.
- **Integration note for P14:** if wearable devices need remote commands or a status pull model, this file is the closest existing protocol precedent.
- **Mismatch watch:** this is explicitly Windows-daemon-focused and may not belong in the wearable path unless command semantics overlap.

### 8.3 Windows status command exposes a gap list
- **File:** `src/discord/cmd_pc.py`
- **Integration note for P14:** use this as a “degraded UX” template. It reveals exactly which fields the repo expects to be available eventually: connection state, active window, project/branch, idle state, consent, dropped events.
- **Mismatch watch:** several data sources are placeholders; do not treat them as production-grade wearable status sources.

---

## 9) P14 execution implications

### P14 must connect to these exact existing contracts
1. **Auth contract:** `X-Signature` / `X-Timestamp` / `X-Nonce` or the Windows auth JSON pattern.
2. **Device identity:** `device_id` + `device_registry` foreign key.
3. **Buffering contract:** Redis DB2, `surveillance:buffer`, TTL 300s.
4. **Consent contract:** `consent.consent_ledger` + fail-closed checks.
5. **Persistence contract:** TimescaleDB hypertable with retention policy and ingestion log.
6. **Operator UI contract:** Discord slash command registration and status embed behavior.
7. **Observability contract:** Prometheus scrape + alert routing via Discord/Gotify.
8. **Service contract:** systemd service or FastAPI lifespan/background worker pattern.

### Places where P14 may be assuming the wrong thing
- **Assumption:** a wearable subsystem already exists.
  - **Reality:** the repo has Windows-specific telemetry and general surveillance pipelines, not a wearable implementation.
- **Assumption:** a device registry lookup API exists for wearables.
  - **Reality:** only the DB table and related FK paths are present here.
- **Assumption:** `/pc` or `/surveillance-status` already includes wearable health.
  - **Reality:** both commands are partially placeholder-driven and need wiring for live device state.
- **Assumption:** a dedicated wearable service unit exists.
  - **Reality:** only generic surveillance/monitoring service patterns exist in `vps-mirror/systemd-live/`.
- **Assumption:** there is a separate wearable alert family.
  - **Reality:** alerting is centralized in Prometheus/Alertmanager with Discord/Gotify routing.

## 10) Bottom line
P14 wearable work should be implemented as a **new device adapter/pipeline** that plugs into the repo’s existing surveillance architecture, not as a standalone system. The minimum integration set is:
- auth/replay
- buffering
- consent gate
- device registry FK
- TimescaleDB retention
- Discord status/command visibility
- Prometheus/Alertmanager observability
- systemd or lifespan service wiring

If P14 follows the Windows telemetry pattern closely, the most useful concrete templates are:
- `src/surveillance/windows_ws.py`
- `src/surveillance/windows_consent.py`
- `src/surveillance/windows_commands.py`
- `migrations/p15_add_windows_events_hypertable.sql`
- `vps-mirror/systemd-live/guinevere-surveillance.service`

If P14 instead uses HTTP intake, the closest templates are:
- `src/surveillance/router.py`
- `src/surveillance/auth.py`
- `src/surveillance/redis_buffer.py`
- `src/surveillance/consumer.py`

---

## Evidence of repo-grounded sources used
- `src/surveillance/router.py`
- `src/surveillance/auth.py`
- `src/surveillance/redis_buffer.py`
- `src/surveillance/consumer.py`
- `src/surveillance/timescale.py`
- `src/surveillance/consent_gate.py`
- `src/surveillance/windows_consent.py`
- `src/surveillance/windows_ws.py`
- `src/surveillance/windows_commands.py`
- `src/surveillance/windows_models.py`
- `src/discord/_entrypoint.py`
- `src/discord/cmd_surveillance_status.py`
- `src/discord/cmd_pc.py`
- `src/core/main.py`
- `clients/windows/src/daemon/config.py`
- `clients/windows/src/daemon/ws_client.py`
- `clients/windows/src/daemon/event_pipeline.py`
- `migrations/p15_add_windows_events_hypertable.sql`
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py`
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/guinevere-alerts.yml`
- `monitoring/alertmanager/alertmanager.yml`
- `vps-mirror/systemd-live/guinevere-surveillance.service`
- `vps-mirror/systemd-live/guinevere-monitoring.service`
