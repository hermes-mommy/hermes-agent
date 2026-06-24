# P14 Existing Wearable/Health Artifacts Inventory

## Scope
This inventory covers existing repository artifacts related to wearable, health, fitness, Xiaomi, Mi Fitness, Gadgetbridge, health schemas, Discord commands, config, monitoring, consent/permission models, and tests.

## Summary
The repository already contains a substantial P14 research and design surface, but almost no production wearable implementation. Most existing artifacts are planning/research docs plus generic health-check code that is unrelated to Xiaomi wearable ingestion. The main canonical decision is ADR-021: wearable integration is post-MVP and should not be treated as an active dependency for MVP behavior.

## File Inventory

| Path | Purpose | Status |
|---|---|---|
| `C:\Users\faizz\guinevere\adr\ADR-021-wearable-integration-post-mvp.md` | Canonical ADR stating wearable integration is post-MVP and not an active dependency for MVP behavior, health reminders, surveillance, or persona inference. | complete |
| `C:\Users\faizz\guinevere\research-reports\p14-expansion\requirements-p14-wearable.md` | P14 requirements/spec draft for wearable/Xiaomi Watch integration, including hybrid Gadgetbridge + Mi Fitness cloud fallback architecture, proposed health schema, commands, and persona behavior. | complete but design-draft |
| `C:\Users\faizz\guinevere\research-reports\P14_xiaomi_health_data_access_methods.md` | Research catalog of Xiaomi wearable data access methods (Gadgetbridge, Health Connect, Mi Fitness cloud), includes implementation tradeoffs. | complete |
| `C:\Users\faizz\guinevere\research-reports\p14-gadgetbridge-schema.md` | Research note correcting assumptions about real Gadgetbridge export schema and timestamp conventions. | complete |
| `C:\Users\faizz\guinevere\src\surveillance\models.py` | Surveillance event schema already includes `event_type="health"`, which is reusable for health-related ingestion but does not define wearable-specific subtypes. | complete (generic) |
| `C:\Users\faizz\guinevere\src\discord\_command_registry.py` | Canonical Discord slash-command registry; currently contains `/health-check` only, no `/health`, `/wearable`, or `/ghi`. | complete (generic) |
| `C:\Users\faizz\guinevere\src\discord\cmd_health_check.py` | Implementation for `/health-check` command, tied to service health endpoint, not wearable health. | complete (generic) |
| `C:\Users\faizz\guinevere\src\hermes_plugins\commands_admin\health_check.py` | Hermes plugin for `/health-check`; generic service-health probe. | complete (generic) |
| `C:\Users\faizz\guinevere\src\hermes_plugins\command_catalog.py` | Command category catalog; includes admin health-check only. | complete (generic) |
| `C:\Users\faizz\guinevere\src\discord\_entrypoint.py` | Discord command routing/bootstrap; references admin health-check registration. | complete (generic) |
| `C:\Users\faizz\guinevere\src\_deprecated\hermes-migration-phase-7\commands.py` | Deprecated command registry snapshot including health-check; historical only. | stale |
| `C:\Users\faizz\guinevere\src\_deprecated\hermes-migration-phase-7\bot.py` | Deprecated bot bootstrap snapshot with health-check command wiring. | stale |
| `C:\Users\faizz\guinevere\src\x_poster\health.py` | X Poster service health endpoint; unrelated to wearable health. | complete (generic) |
| `C:\Users\faizz\guinevere\src\x_poster\metrics.py` | Session health metric for X Poster, not wearable health data. | complete (generic) |
| `C:\Users\faizz\guinevere\src\channels\whatsapp\health.py` | WhatsApp channel health endpoint, generic service health. | complete (generic) |
| `C:\Users\faizz\guinevere\src\gmail\health.py` | Gmail service health endpoint, generic service health. | complete (generic) |
| `C:\Users\faizz\guinevere\src\gmail\service.py` | Gmail service runtime with `/health` endpoint, generic service health. | complete (generic) |
| `C:\Users\faizz\guinevere\monitoring\grafana\dashboards\guinevere-x-poster.json` | Grafana dashboard for X Poster; no wearable/health metrics. | complete (unrelated) |
| `C:\Users\faizz\guinevere\monitoring\prometheus\rules\guinevere-alerts.yml` | Prometheus alert rules for safety, security, ops, Hermes, SLOs; no wearable health recording rules. | complete (unrelated) |
| `C:\Users\faizz\guinevere\monitoring\prometheus\prometheus.yml` | Prometheus scrape config; no wearable-specific jobs found in search. | complete (unrelated) |
| `C:\Users\faizz\guinevere\monitoring\compose.monitoring.yml` | Monitoring compose config; no wearable-specific configuration found in search. | complete (unrelated) |
| `C:\Users\faizz\guinevere\hermes-config\config.yaml` | General Hermes config; search hit on generic health wording only, no wearable-specific vars confirmed. | complete (unrelated) |
| `C:\Users\faizz\guinevere\tests\channels\whatsapp\test_health.py` | Tests for WhatsApp channel health endpoint. | complete (generic) |
| `C:\Users\faizz\guinevere\tests\surveillance\test_discord_commands.py` | Discord command tests; likely includes health-check surface but not wearable-specific commands. | complete (generic) |
| `C:\Users\faizz\guinevere\tests\surveillance\test_router.py` | Surveillance routing tests; generic health event routing may be exercised. | complete (generic) |
| `C:\Users\faizz\guinevere\tests\surveillance\test_retention.py` | Surveillance retention tests; health events may be classified here. | complete (generic) |
| `C:\Users\faizz\guinevere\tests\surveillance\test_e2e.py` | End-to-end surveillance tests; generic health event coverage. | complete (generic) |
| `C:\Users\faizz\guinevere\tests\surveillance\test_secret_scanner.py` | Security scan tests; may touch health-related secret patterns only incidentally. | unrelated |
| `C:\Users\faizz\guinevere\tests\test_p13_e2e.py` | P13 end-to-end test; search hit is likely incidental. | unrelated |
| `C:\Users\faizz\guinevere\tests\fixtures\golden_recall_dataset.json` | Fixture with a health keyword match; not a wearable schema artifact. | unrelated |
| `C:\Users\faizz\guinevere\evidence\v2-doc-update\apply_v2_updates.py` | Documentation migration script updating wearable wording to post-MVP. | complete (doc-sync artifact) |
| `C:\Users\faizz\guinevere\stepprompts\StepPrompts.md` | Step prompt inventory; search hit indicates P14 prompts likely exist there, but file is too broad to treat as a wearable implementation artifact without targeted extraction. | complete (planning surface) |

## Existing Artifacts by Requested Category

### 1) Python files referencing wearable/health/fitness/gadgetbridge/xiaomi/mi-fitness
Confirmed relevant:
- `src/surveillance/models.py` — generic `event_type="health"`
- `src/discord/_command_registry.py` — `/health-check`
- `src/discord/cmd_health_check.py`
- `src/hermes_plugins/commands_admin/health_check.py`
- `src/hermes_plugins/command_catalog.py`
- `src/discord/_entrypoint.py`
- `src/_deprecated/hermes-migration-phase-7/commands.py`
- `src/_deprecated/hermes-migration-phase-7/bot.py`
- `src/x_poster/health.py`
- `src/x_poster/metrics.py`
- `src/channels/whatsapp/health.py`
- `src/gmail/health.py`
- `src/gmail/service.py`

Research-only P14 references:
- `research-reports/P14_xiaomi_health_data_access_methods.md`
- `research-reports/p14-gadgetbridge-schema.md`
- `evidence/v2-doc-update/apply_v2_updates.py`
- `research-reports/p14-expansion/requirements-p14-wearable.md`

### 2) Migration files or SQL for health-related tables
Search found `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` as a match candidate, but no direct wearable-specific table evidence was verified in this pass. No separate health/wearable SQL migration files were confirmed from the search results. The P14 requirements doc proposes a new `health.*` schema, but that schema does not yet appear to exist in production migrations.

### 3) Discord command definitions for `/health`, `/wearable`, `/ghi`
Confirmed existing:
- `/health-check` in `src/discord/_command_registry.py`
- `/health-check` in `src/discord/cmd_health_check.py`
- `/health-check` in `src/hermes_plugins/commands_admin/health_check.py`

Not found in the current codebase search:
- `/health`
- `/wearable`
- `/ghi`

### 4) Alembic migrations touching health/wearable tables
- `alembic/versions/e401bb5fd274_initial_schema_47_tables.py` matched the broad health keyword search, but no wearable-specific migration was established from the available output.
- No dedicated Alembic migration for `health.*` / wearable tables was confirmed.

### 5) Config entries for wearable (env vars, feature flags, YAML)
- No explicit wearable env vars, feature flags, or YAML config entries were confirmed from the search.
- `hermes-config/config.yaml` matched generic health text only.
- `monitoring/prometheus/prometheus.yml` and `monitoring/compose.monitoring.yml` had health keyword matches but no wearable-specific config identified.

### 6) Grafana dashboard JSONs referencing health metrics
- `monitoring/grafana/dashboards/guinevere-x-poster.json` matched on generic “session health” wording only; it is not a wearable dashboard.
- No Grafana JSON specific to wearable/health metrics was confirmed.

### 7) Prometheus recording rules for health data
- `monitoring/prometheus/rules/guinevere-alerts.yml` contains generic operational and Hermes alerting, not wearable health recording rules.
- No wearable-health recording rule file was confirmed.

### 8) Consent/permission models referencing health/wearable scope
Confirmed relevant in the P14 requirements draft:
- `research-reports/p14-expansion/requirements-p14-wearable.md` proposes `surveillance.wearable.health.explicit` scope and extending `VALID_SURVEILLANCE_SCOPES`.

Confirmed repository code reference:
- `src/surveillance/models.py` has generic `event_type="health"` only.

No dedicated consent/permission model file for wearable scope was confirmed in the code search results.

### 9) Test files referencing health/wearable
Confirmed generic health-related tests:
- `tests/channels/whatsapp/test_health.py`
- `tests/surveillance/test_discord_commands.py`
- `tests/surveillance/test_router.py`
- `tests/surveillance/test_retention.py`
- `tests/surveillance/test_e2e.py`

Likely unrelated / incidental hits:
- `tests/test_p13_e2e.py`
- `tests/surveillance/test_secret_scanner.py`
- `tests/fixtures/golden_recall_dataset.json`

No test file specifically asserting `/wearable` or `/ghi` commands was confirmed.

## Validity Under the New Mi Fitness Cloud Approach

### Still valid / reusable
- `research-reports/P14_xiaomi_health_data_access_methods.md`: still useful for comparing Gadgetbridge vs Health Connect vs Mi Fitness cloud, but the priority ranking may need rewriting if Mi Fitness Cloud is now the canonical source.
- `research-reports/p14-gadgetbridge-schema.md`: still useful as a reality check for raw Gadgetbridge exports if Gadgetbridge remains a fallback or migration reference.
- `adr/ADR-021-wearable-integration-post-mvp.md`: still binding for the post-MVP classification, but it does not prescribe the Mi Fitness Cloud implementation details.
- `src/surveillance/models.py`: reusable for generic health event transport, but probably needs extended event typing or payload schema if wearable ingestion becomes a first-class source.
- `/health-check` command surfaces: reusable as generic service health checks, but not wearable user commands.

### Needs full rewrite or heavy refactor
- `research-reports/p14-expansion/requirements-p14-wearable.md`: architecture is Gadgetbridge-primary with Mi Fitness fallback; this is misaligned with a Mi Fitness Cloud-first approach and likely needs a rewrite of source-of-truth, ingestion flow, schema assumptions, and command surface.
- Any future implementation that follows the current draft’s proposed `health.*` schema, device registry, or persona-injection plan should be revisited before coding.
- Any planned scope/permission additions in the P14 draft should be rewritten to reflect the Mi Fitness Cloud consent model and actual cloud access constraints.

### Stale / misleading for new P14 direction
- References implying Gadgetbridge as the primary pipeline (`requirements-p14-wearable.md`) are stale if Mi Fitness Cloud is the chosen primary path.
- Any implicit assumption that `/health-check` is a wearable command is stale; it is service health only.
- The existing x-poster/whatsapp/gmail health endpoints are stale as wearable references because they are generic health-check endpoints.

## Dependency Map

### Core dependency chain discovered
1. `ADR-021-wearable-integration-post-mvp.md`
   → establishes wearable as post-MVP and not active dependency for MVP.
2. `research-reports/p14-expansion/requirements-p14-wearable.md`
   → currently defines the intended P14 product/technical shape, including data source, schema, commands, and persona behavior.
3. `research-reports/P14_xiaomi_health_data_access_methods.md`
   → supports the data-source decision with comparative research.
4. `research-reports/p14-gadgetbridge-schema.md`
   → validates or rejects Gadgetbridge-schema assumptions from the requirements draft.
5. `src/surveillance/models.py`
   → current generic transport model for health events; could be the integration point if wearable data becomes a new event type.
6. `src/discord/_command_registry.py` + `src/discord/cmd_health_check.py` + `src/hermes_plugins/commands_admin/health_check.py`
   → current command system; must be extended if `/wearable` or `/ghi` are introduced.
7. `monitoring/*` configs
   → would need new dashboards/rules if wearable health metrics are operationalized.
8. `tests/*`
   → should be expanded after implementation to cover new commands, ingestion, and consent behavior.

## Practical Conclusion
At present, the repo contains research and generic health-check infrastructure, not a wearable implementation. The only wearable-specific design artifact is the P14 requirements draft plus supporting research. Under a Mi Fitness Cloud approach, that requirements draft is the main artifact to rewrite; most other code should be kept only as generic service-health or generic surveillance plumbing.

## Recommended Next Classification
- Keep: ADR-021, research comparisons, generic health plumbing
- Rewrite: `requirements-p14-wearable.md`
- Discard for wearable-specific planning: any interpretation of `/health-check` or generic health endpoints as wearable features
- Create next: Mi Fitness Cloud-first P14 implementation spec, then schema/command/monitoring work only after the new spec is aligned
