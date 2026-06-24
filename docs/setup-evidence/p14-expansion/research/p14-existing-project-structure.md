# P14 Existing Project Structure Report

Date: 2026-06-18
Scope: local repository only
Goal: map the current repo structure and identify where P14 wearable/Xiaomi watch pipeline code would fit.

## 1) High-level source tree

### Primary application source
- `src/core/main.py` — FastAPI app entrypoint; starts core app lifespan, metrics, monthly report scheduler, and surveillance consumer background task.
- `src/core/config/__init__.py` — config package stub; currently minimal.
- `src/core/api/auth.py`, `src/core/api/routes.py` — core API surface.
- `src/core/services/` — shared runtime services:
  - `src/core/services/llm_metrics.py`
  - `src/core/services/monthly_report.py`
  - `src/core/services/hard_stop_handler.py`
  - `src/core/services/llm_router.py`
  - `src/core/services/cost_tracker.py`
  - `src/core/services/prompt_loader.py`

### Discord bot / operator interface
- `src/discord/_entrypoint.py` — active Discord bot runtime entrypoint used by systemd.
- `src/discord/` — command handlers and runtime support:
  - `_auth_guard.py`, `_command_registry.py`, `_embed_utils.py`, `_intents.py`, `_startup.py`
  - `cmd_*.py` command modules for approval, consent, memory, loops, surveillance, etc.
  - `listeners/` for Gmail/X reaction/upload listeners
  - `loops/x_poster_dashboard.py` for x_poster dashboard integration
  - `shadow_pipeline.py`, `shadow_monitor.py`, `notifications.py`
- Deprecated Discord code remains under `src/discord/bot.py.bak.pre-phase2` and `src/discord/conversational_handler.py.bak.pre-phase2`.

### Agent loop / background orchestration
- `src/loops/manager.py` — core loop manager.
- `src/loops/scheduler.py` — APScheduler-based loop scheduler daemon.
- `src/loops/phases/` — phase implementations:
  - `delegate.py`, `execute.py`, `plan_delegate.py`, `research.py`, `setup_evidence.py`, `update_docs.py`, `validate_audit.py`
- `src/loops/verify.py`, `src/loops/state_machine.py`, `src/loops/guardian.py`, `src/loops/sub_agent.py`, `src/loops/evidence.py`, `src/loops/artifacts.py`

### Surveillance / safety / wearable-adjacent systems
- `src/surveillance/` — main surveillance pipeline domain:
  - `consumer.py` — Redis DB2 background worker that drains events and stores them to DB
  - `redis_buffer.py`, `router.py`, `consent_gate.py`, `classification.py`, `retention.py`, `replay.py`, `timescale.py`
  - `auth.py`, `safe_mode.py`, `secrets.py`, `secret_scanner.py`, `windows_*` modules for Windows daemon support
- `src/observability/windows_metrics.py` — Prometheus metrics for the Windows surveillance daemon.
- `src/persona/` — persona engines and scheduler:
  - `ritual_scheduler.py`, `rituals/`, `safe_mode.py`, `yandere_fsm.py`, `drift_*`, `mood_*`, `reward_engine.py`, `punishment_engine.py`
- `src/memory/` — memory pipeline:
  - `db.py`, `read_pipeline.py`, `write_pipeline.py`, `consolidation.py`, `models.py`, `embeddings.py`, `dnr.py`
- `src/hermes/` and `src/hermes/plugins/` — Hermes integration and plugins.
- `src/mcp/` — MCP manager plus tool adapters (`tools/`).
- `src/x_poster/` — X posting pipeline, queueing, scheduling, retries, storage.
- `src/gmail/` — Gmail ingestion/consent/sync pipeline.
- `src/finance/`, `src/gamification/`, `src/observability/`, `src/persona/`, `src/memory/` are additional functional domains.

## 2) Package/config files

### Project/package metadata
- `pyproject.toml` — project metadata and dependency list. Important dependencies for P14 fit: `fastapi`, `uvicorn`, `sqlalchemy[asyncio]`, `asyncpg`, `alembic`, `redis`, `apscheduler`, `sentry-sdk`, `prometheus-client`, `discord.py`, `websockets`, `pydantic-settings`, `cryptography`, `neonize`, `google-cloud-pubsub`, `resend`, `presidio-analyzer`.
- `uv.lock` — resolved dependency lockfile.
- `.coveragerc` — coverage config.
- `.gitignore` — ignore rules.
- `.sops.yaml` — SOPS policy for secrets handling.
- `.env`, `.env.enc.example`, `.env.example` at repo root are config/secrets-related artifacts; plus runtime env templates under `monitoring/` and `vps-mirror/`.

### Runtime/service config patterns
- `systemd/` — service units for deployment on the VPS.
- `alembic.ini` — Alembic configuration.
- `monitoring/compose.monitoring.yml` — Docker Compose for observability stack.
- `monitoring/prometheus/prometheus.yml` and `monitoring/prometheus/rules/*.yml` — scrape config and alert rules.
- `monitoring/grafana/provisioning/*` and `monitoring/grafana/dashboards/*.json` — Grafana provisioning and dashboards.

## 3) Deployment / infrastructure files

### systemd units
- `systemd/guinevere-discord.service` — Discord bot service, runs `python -m src.discord._entrypoint`.
- `systemd/guinevere-loops.service` — agent loop daemon, runs `python -m src.loops.manager`.
- `systemd/guinevere-scheduler.service` — scheduler daemon, runs `python -m src.loops.scheduler`.
- `systemd/guinevere-surveillance.service` — surveillance consumer, runs `python -m src.surveillance.consumer`.
- `systemd/guinevere-monitoring.service` — monitoring service unit.
- `systemd/guinevere-mcp.service` — MCP service unit.
- `systemd/guinevere-obscura.service` — browser/obscura service.
- `systemd/guinevere-x-poster.service` — X poster service.
- `systemd/guinevere-gmail.service` — Gmail service.
- `systemd/guinevere-shadow-monitor.service` and `systemd/guinevere-shadow-monitor.timer` — timered shadow monitoring.
- `systemd/guinevere-whatsapp.service` exists under `systemd/` and appears to be another channel service in the repo root tree.
- `vps-mirror/systemd-live/` mirrors live service units, including `guinevere-core.service`, `guinevere-surveillance.service`, `guinevere-scheduler.service`, `guinevere-discord.service`, `guinevere-loops.service`, `guinevere-monitoring.service`, `guinevere-mcp.service`, `guinevere-obscura.service`, `guinevere-shadow-monitor.service`, `guinevere-shadow-monitor.timer`, `guinevere-9router.service`, `hermes-gateway.service`, and others.

### Monitoring stack
- `monitoring/compose.monitoring.yml` — Prometheus, Alertmanager, Grafana, Loki, Promtail, node-exporter, postgres-exporter, redis-exporter.
- `monitoring/alertmanager/alertmanager.yml`
- `monitoring/loki/loki-config.yml`
- `monitoring/promtail/promtail-config.yml`
- `monitoring/node-exporter/textfile/*.prom`
- `monitoring/postgres-exporter/postgres_exporter_role.sql`
- `monitoring/scripts/backup-metric-collector.sh`
- `grafana/alerts/windows-daemon-disconnected.json`
- `grafana/dashboards/windows-daemon.json`

### VPS / environment mirror artifacts
- `vps-mirror/` contains live-mirror bundles and service files for deployment validation.
- `vps-mirror/audit/*.tar` stores tarred snapshots of repo/systemd/evidence artifacts.

## 4) Database migration tooling

### Alembic / general migration tooling
- `alembic/` — main migration toolchain root.
  - `alembic/env.py`
  - `alembic/script.py.mako`
  - `alembic/versions/` with schema history files:
    - `2bed93fd1dd0_baseline_init.py`
    - `65f863220922_add_search_vector_do_not_recall.py`
    - `7239fd4b3b5a_add_reviewer_action_to_drift_log.py`
    - `e401bb5fd274_initial_schema_47_tables.py`
    - `p5_add_loop_indexes.py`
    - `p5_extend_loop_instances.py`
    - `p6_gamification_schema.py`
    - `p6_gamification_schema.sql`
    - `p7_persona_enhancement_v3.sql`
- `alembic.ini` points version storage to `ops.alembic_version`.

### Domain-specific SQL migrations
- `src/gmail/migrations/001_gmail_tables.sql`
- `src/gmail/migrations/002_gmail_search_vector.sql`
- `src/x_poster/migrations/001_initial_tables.sql`
- `migrations/phase-3/004-hermes-memory-bridge-rbac.sql`
- `migrations/p15_add_windows_events_hypertable.sql`

### DB-related code locations
- `src/memory/db.py`
- `src/surveillance/timescale.py`
- `src/x_poster/db.py`
- `src/gmail/memory_store.py`
- `src/finance/db.py`

## 5) Env / config patterns

### Root and runtime env files
- Root `.env` exists in repo.
- Root `.env.enc.example` and `.env.example` indicate encrypted/example environment convention.
- `tmp-whatsapp-deploy.env` appears to be a temporary deployment env artifact.
- `vps-mirror` and `systemd` units rely on per-service files such as:
  - `.env.discord`
  - `.env.loops`
  - `.env.surveillance`
  - `.env.scheduler`
- `monitoring/.env` and `monitoring/.env.example` exist for observability stack.
- `monitoring/.gitignore` helps keep local environment files out of git.

### Runtime configuration modules
- `src/gmail/config.py`
- `src/x_poster/config.py`
- `src/core/config/__init__.py` (currently minimal)
- `src/surveillance/windows_*` modules for daemon-side runtime control.

### Secrets / safety patterns
- `.sops.yaml` is present for encrypted secret management.
- Surveillance code and systemd units use environment-based injection rather than hardcoded secrets.
- `src/discord/_entrypoint.py` explicitly reads `DISCORD_BOT_TOKEN` from environment.

## 6) Observability / logging / metrics

### Application observability
- `src/core/main.py` exports `/metrics`, `/health`, `/health/detailed` and wires Prometheus counters/histograms.
- `src/observability/sentry_integration.py`
- `src/observability/windows_metrics.py` for Windows daemon Prometheus metrics.
- `src/discord/*structured_logging.py` and `src/gmail/structured_logging.py` and `src/x_poster/structured_logging.py` are domain-specific logging helpers.
- `src/gmail/metrics.py`, `src/x_poster/metrics.py`, `src/channels/whatsapp/metrics.py`.

### Monitoring deployment
- `monitoring/prometheus/prometheus.yml`
- `monitoring/prometheus/rules/guinevere-alerts.yml`
- `monitoring/prometheus/rules/guinevere-backup-alerts.yml`
- `monitoring/grafana/provisioning/dashboards/dashboards.yml`
- `monitoring/grafana/provisioning/datasources/datasources.yml`
- `monitoring/grafana/dashboards/guinevere-*.json`
- `monitoring/loki/loki-config.yml`
- `monitoring/promtail/promtail-config.yml`

## 7) Test layout

### Top-level test organization
- `tests/ab_testing/`
- `tests/channels/whatsapp/`
- `tests/discord/`
- `tests/hermes/`
- `tests/integration/`
- `tests/mcp/`
- `tests/memory/`
- `tests/persona/`
- `tests/phase7/`
- `tests/safety/`
- `tests/smoke/`
- `tests/surveillance/`
- top-level `tests/test_e2e_loop.py`
- top-level `tests/test_p13_e2e.py`

### Relevant tests for pipeline and P14 fit
- Discord/runtime: `tests/discord/test_bot.py`, `tests/discord/test_startup.py`, `tests/discord/test_notifications.py`, `tests/discord/test_hermes_conversational.py`
- Surveillance: `tests/surveillance/test_consumer.py`, `tests/surveillance/test_e2e.py`, `tests/surveillance/test_windows_consent.py`, `tests/surveillance/test_windows_metrics.py`, `tests/surveillance/test_secret_scanner.py`, `tests/surveillance/test_timescale.py`
- Loops/scheduler: `tests/persona/test_ritual_scheduler.py`, `tests/phase7/test_T1_e2e_loop.py`, `tests/phase7/test_T10_monitoring_health.py`, `tests/test_e2e_loop.py`
- Monitoring/observability: `tests/hermes/test_llm_metrics.py`, `tests/mcp/test_*` for tool infrastructure, plus core health/metrics behavior
- Wearable-adjacent or future host integration likely needs new test coverage; current tests are Windows/surveillance/Discord/loop-centric rather than Xiaomi-watch specific.

## 8) Where a P14 wearable/Xiaomi watch pipeline would fit

Based on current structure, P14 would most naturally integrate across these surfaces:

1. `src/surveillance/` — best fit for device event intake, consent gating, retention, replay, and Windows/mobile/watch event normalization.
2. `src/observability/windows_metrics.py` + `monitoring/` — for wearable daemon metrics, dashboards, and alerts.
3. `src/loops/` — for scheduling recurring polling, sync, or device maintenance jobs.
4. `src/discord/` — for user/operator commands to inspect wearable state, pause/resume, and alerting.
5. `systemd/` + `vps-mirror/systemd-live/` — for deploying the wearable-side/background service(s) as managed daemons.
6. `alembic/versions/` and domain SQL migrations — for any new tables needed for wearable devices, event ingestion, pairing, consent state, or sync history.
7. `tests/surveillance/`, `tests/integration/`, `tests/phase7/` — for end-to-end coverage of wearable event flow and failure modes.

### Existing gaps visible from repo structure
- There is no obvious dedicated `src/wearable/` package yet.
- There is no Xiaomi-watch-specific module naming in the source tree.
- Watch support is currently only implied in documentation/architecture, not represented by a first-class code package.
- Current wearable-adjacent work would likely be forced into `surveillance/` or `loops/` unless a new package is introduced.

## 9) Practical notes for phase planning

- The repo already has mature patterns for:
  - service modules + systemd unit wiring
  - async background consumers
  - metrics and dashboards
  - migration history and SQL-based schema evolution
  - Discord command-based operator control
- The most likely end-to-end execution risk for P14 is missing a dedicated device ingestion/service boundary for Xiaomi watch data; that gap is not represented by a current top-level package.
- The second risk is incomplete deployment wiring: a wearable daemon would need a service unit, env template, observability endpoints, and tests in the same style as the existing surveillance/Discord/loops services.

## 10) Evidence used

- `README.md`
- `pyproject.toml`
- `alembic.ini`
- `src/core/main.py`
- `src/discord/_entrypoint.py`
- `src/loops/scheduler.py`
- `src/surveillance/consumer.py`
- `src/observability/windows_metrics.py`
- `monitoring/compose.monitoring.yml`
- `systemd/guinevere-discord.service`
- `systemd/guinevere-loops.service`
- `systemd/guinevere-scheduler.service`
- `systemd/guinevere-surveillance.service`
- directory trees for `src/`, `tests/`, `alembic/`, `migrations/`, `monitoring/`, `grafana/`, `systemd/`, and `vps-mirror/systemd-live/`

