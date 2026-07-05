# ADR-053: P22 Life Integration Hub Architecture

**Status:** Accepted (implementation complete, CONFIG_MISSING adapters documented)
**Date:** 2026-06-27
**Risk:** HIGH
**Tags:** p22, integration, life-hub, consent, audit, architecture

## Context

P22 Life Integration Hub provides a unified, consent-gated, audit-trailed runtime for all external integrations (Discord, Gmail, GitHub, Google Calendar/Drive, Notion, Telegram, WhatsApp, VPS, Finance, Browser, Memory/KG, Filesystem). Prior to P22, integrations were scattered across `src/gmail/`, `src/channels/whatsapp/`, `src/mcp/tools/github.py`, and 8 placeholder sensor adapters in `src/life_kernel/sensor_adapters/` — with no unified permission model, consent gate, or audit trail.

The P22 v2.0 full-capability replan mandated: read/create/update/move/archive/delete/sync/admin across all providers, with L1-L4 permission tiers, semantic action classification (not AuthLevel-only), absolute HARD STOP + consent enforcement, P19 project_id propagation, and P20 non-interference.

## Decision

Implement P22 as a **new standalone package** `src/life_integrations/` that:

1. **Does not modify P20 closed files** — uses `SensorRegistry.register()` API additively via `wiring.py`
2. **Classifies actions semantically** — `SemanticActionClassifier` (P22-local scaffold until P23's lands) determines L1-L4 by parsed intent + provider operation + side-effect risk, NOT MCP AuthLevel alone
3. **Enforces consent + HARD STOP absolutely** — `ConsentGate` blocks all L2+ when HARD STOP active; consent revocation absolute, no autonomy bypass
4. **Audit-trails every action** — hash-chained `AuditLogger` (SHA256 canonical payload + previous_hash) with secret redaction in metadata
5. **Propagates P19 project_id** — every action carries project_id, resource IDs follow `p22:<domain>:<provider>:<resource-id>` template
6. **Reports CONFIG_MISSING honestly** — adapters without credentials raise `ConfigurationMissingError`, never fake success
7. **Preserves V-002** — sensors feed observations to `observe_node`; write actions go through `ActionRouter` gate (classify→consent→hardstop→execute→audit)

### Structure
- `src/life_integrations/` — 13 core modules (types, base, registry, permissions, consent, secrets, audit, project_context, router, scheduler, errors, wiring, __init__)
- `src/life_integrations/adapters/` — 13 adapter files (one per integration)
- `alembic/versions/p22_001_integration_schema.py` — audit.integration_api_log (WORM), p22.integration_registry, p22.secret_ref_metadata
- `tests/p22/` — 6 test files, 60 tests
- `scripts/p22_smoke_test.py` — runtime smoke (12 checks)

## Consequences

**Positive:**
- Unified permission/consent/audit model across all integrations
- No P20 regression (closed files untouched)
- P19 namespace propagation from day 1
- P23 can consume P22 adapters as ExternalExecutor targets (P23-014 gate unblocked)
- P24 can migrate adapters to fork-internal modules (provider pattern ready)
- Honest CONFIG_MISSING status — no fake success

**Negative / accepted risks:**
- 10/13 adapters are CONFIG_MISSING (external creds not provisioned) — operator-gated OAuth flows
- VPS deploy deferred (P22 is development work, not P20 autonomy exception)
- P23 SemanticActionClassifier not yet runtime — P22 uses local scaffold bridge

## Compliance

- AGENTS.md §0.1: HARD STOP absolute ✓, consent revocation absolute ✓, no autonomy bypass ✓
- AGENTS.md §5: no type suppression ✓, no empty catch ✓, no fake fallback ✓
- P22 v2.0 hard rejection criteria: all 11 mitigated ✓
- V-002 sensors-not-triggers: preserved ✓
- P20 non-interference: 0 closed files modified ✓
- P19 read-only consumption: ProjectRegistry not mutated ✓

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-27 | Guinevere | Initial ADR for P22 Life Integration Hub |
