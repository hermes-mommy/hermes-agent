# P14 — Wearable Health Pipeline: Index

**Status:** Implementation in progress (4/20 steps complete)
**Date:** 2026-06-18
**Architecture:** Mi Fitness Cloud API → VPS → TimescaleDB → Anomaly Detection → GHI → Mood Modifier

## Directory Structure

```
p14-expansion/
├── README.md                    ← You are here
├── evidence-p14-expansion.md    ← Master evidence tracker
├── plan/
│   └── → .sisyphus/plans/p14-enterprise-plan.md  ← Enterprise plan (803 lines)
├── evidence/                    ← Per-step implementation evidence
│   ├── step-001-schema.md
│   ├── step-002-config.md
│   ├── step-003-skeleton.md
│   ├── step-004-client-normalizer.md
│   ├── step-005-redis-sync.md
│   └── step-006-writer.md
├── research/                    ← Current research artifacts
│   ├── p14-enterprise-plan.md
│   ├── p14-mi-fitness-cloud-api.md
│   ├── p14-systemd-patterns.md
│   ├── p14-existing-artifacts.md
│   ├── p14-existing-project-structure.md
│   ├── p14-p7-p8-integration-points.md
│   ├── p14-anomaly-detection.md
│   ├── p14-gap-analysis.md
│   └── p14-gadgetbridge-schema.md
└── legacy/                      ← Deprecated: Gadgetbridge-era artifacts
    ├── requirements-p14-wearable.md
    ├── P14-001.md ... P14-027.md (old step prompts)
    ├── discord-patterns.md
    ├── observability-patterns.md
    ├── surveillance-patterns.md
    └── template-research.md
```

## Production Code Location

| Artifact | Path |
|---|---|
| Package | `src/wearable/` |
| DB Migration | `migrations/p14_add_health_schema.sql` |
| Env Template | `.env.wearable.example` |
| Plan (Momus-compatible) | `.sisyphus/plans/p14-enterprise-plan.md` |

## Progress

| Step | Status | Files |
|---|---|---|
| P14-001 | ✅ | `migrations/p14_add_health_schema.sql` |
| P14-002 | ✅ | `.env.wearable.example` + `src/wearable/config.py` |
| P14-003 | ✅ | `src/wearable/errors.py` + `src/wearable/models.py` + `__init__.py` |
| P14-004 | ✅ | `src/wearable/mi_fitness_client.py` + `src/wearable/normalizer.py` |
| P14-005 | 🔄 | `src/wearable/redis_buffer.py` + `src/wearable/sync.py` |
| P14-006 | ✅ | `src/wearable/writer.py` |
| P14-007 | ⬜ | Baseline Calculator |
| P14-008 | ⬜ | Anomaly Detection |
| P14-009 | ⬜ | GHI Scorer |
| P14-010 | ⬜ | Mood Integration |
| P14-011 | ⬜ | Alert Router |
| P14-012 | ⬜ | Consent Integration |
| P14-013 | ⬜ | Discord Commands |
| P14-014 | ⬜ | Systemd Timer + Service |
| P14-015 | ⬜ | Prometheus Metrics |
| P14-016 | ⬜ | Grafana Dashboard |
| P14-017 | ⬜ | Encryption at Rest |
| P14-018 | ⬜ | Unit Tests |
| P14-019 | ⬜ | Integration Tests |
| P14-020 | ⬜ | Evidence + Docs |