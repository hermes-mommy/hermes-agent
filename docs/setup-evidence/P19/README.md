# P19 — Multi-Project Context: Index

**Status:** ✅ P19 PRODUCTION COMPLETE — CORE + DISCORD UX LIVE (deployed 2026-06-27, flag ON, commands registered)
**Date:** 2026-06-27 (production deploy + runtime activation complete; see Runtime Activation section below)
**Phase:** Expansion — Multi-Project Context

> **P20 axis gate (DOC-GATE cleanup 2026-06-25):** P20 final status is `P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK` (see `docs/setup-evidence/P20/README.md` + PROGRESS.md). The P20 axis P19 depended on is therefore **satisfied by operator waiver / accepted-risk pass** — not by a 24h soak. P19 no longer waits on "P20 production-pass / 24h soak / LK-017 PRODUCTION PASS". P19 implementation waves that touch P20 production files (`src/life_kernel/heartbeat.py`, `graph.py`, etc.) are held **by operator discretion** (to avoid destabilizing a production system under accepted risk), not by a pending P20 soak gate. See `evidence/p20-waiver-gate-sync.md`.

## Planned Scope

Phase 19 enables Guinevere to maintain separate, isolated context windows
for multiple concurrent projects while sharing a unified persona and
operator profile. Each project gets its own memory namespace, surveillance
scope, agent-loop stack, consent boundary, audit journal, agenda, and
deploy boundary, but persona behavior and core utilities remain shared.
Project switching is explicit, auditable, and reversible. HARD STOP stays
global; project-local pause is a distinct, weaker concept.

Planned deliverables include: project registry and namespace model,
per-project memory/KG partitioning, scoped surveillance/consent filters,
project-aware agent loop / session / background cognition orchestration,
operator-facing project switcher with audit trail and consent gating,
per-project secrets, per-project observability, and migration/backfill
from existing unscoped state.

> **Definition complete (2026-06-25):** P19 is fully defined end-to-end
> (master plan + 11 research files + 2 audit rounds, all PASS). The
> definition adds a `project_id` dimension orthogonally to every
> project-scoped store while keeping the shared persona and global HARD
> STOP. The P20 axis is satisfied by operator waiver (P20 accepted-risk
> pass, 2026-06-25); P19 implementation waves P19-001..012 are scaffolded
> and **ready for implementation by operator approval**. Waves touching P20
> production files are held by operator discretion (not a pending soak gate).
> No runtime code was written, deployed, or restarted in this phase.

## Directory Structure

```
P19/
├── README.md                    ← You are here
├── plan/
│   └── p19-multi-project-context-enterprise-plan.md   ← enterprise plan (planner gate)
├── evidence/
│   ├── audits/
│   │   ├── round-1/             ← 10 audit dimensions (initial, 40 findings)
│   │   └── round-2/             ← 10 audit dimensions (post-amendment, all PASS)
│   ├── p19-definition-verification.md
│   ├── auditor-gate.md
│   └── final-p19-planning-report.md
└── research/
    ├── p19-repo-architecture-inventory.md
    ├── p19-p20-life-kernel-dependency-map.md
    ├── p19-memory-namespace-research.md
    ├── p19-surveillance-consent-scope-research.md
    ├── p19-agent-loop-session-isolation-research.md
    ├── p19-discord-dashboard-project-switcher-research.md
    ├── p19-database-schema-migration-research.md
    ├── p19-security-secrets-boundary-research.md
    ├── p19-observability-audit-evidence-research.md
    ├── p19-p21-p22-integration-dependency-map.md
    └── p19-official-docs-runtime-patterns.md
```

## Production Code Location

| Artifact | Path |
|---|---|
| Package | `src/projects/` (planned — NEW, unblocked but not executed) |
| Project registry | `src/projects/registry.py` (planned) |
| Memory store wrapper | `src/projects/memory_store.py` (planned) |
| Secrets vault | `src/projects/secrets_vault.py` (planned) |
| DB Migration | `alembic/versions/p19_001_project_namespaces.py` (planned, `down_revision=p20_001_life_kernel_schema`) |
| ADR | `adr/ADR-052-multi-project-context.md` (planned — ADR-052, not ADR-039 which is reserved) |
| Secrets | `secrets/projects/{project_id}/*.enc.yaml` (planned, SOPS/age) |

## Plan Bundle

| Artifact | Path | Lines |
|---|---|---|
| Master Plan | [`plan/p19-multi-project-context-enterprise-plan.md`](plan/p19-multi-project-context-enterprise-plan.md) | 800 |
| Research (11 files) | [`research/`](research/) | 2,725 |

## Progress

| Step | Status | Description |
|---|---|---|
| DEFINITION | ✅ COMPLETE | Plan + 11 research files + 2 audit rounds (all PASS) |
| P19-001 | ✅ COMPLETE | Governance + ADR-052 + docs sync — ADR-052 created, ADR Index updated, evidence files created |
| P19-002 | ✅ DEPLOYED | Project registry / domain models (NEW files) |
| P19-003 | ✅ DEPLOYED | DB schema + migrations (additive) |
| P19-004 | ✅ DEPLOYED | Memory/KG namespace partition (NEW + additive) |
| P19-005 | ✅ DEPLOYED | P20 life-kernel project context propagation (P20 production files; split 005a/005b/005c; P20 axis satisfied by waiver) |
| P19-006 | ✅ DEPLOYED | Project-aware sensors and actions |
| P19-007 | ✅ DEPLOYED | Discord dashboard/log/project switcher UX |
| P19-008 | ✅ DEPLOYED | Project-aware agent/session orchestration |
| P19-009 | ✅ DEPLOYED | Consent/surveillance scoped policy enforcement |
| P19-010 | ✅ DEPLOYED | Observability/audit/evidence integration |
| P19-011 | ✅ DEPLOYED | Migration/backfill from existing unscoped state |
| P19-012 | ✅ DEPLOYED | Deploy/canary/rollback/soak/final production gate |

> **Note:** The definition phase is complete. Implementation waves are
> scaffolded with per-step verification (Expected Files / Forbidden
> Patterns / Required Commands / Evidence / Hard Rejection / Rollback /
> Parent Verification / Auditor Assignment) and held by operator approval
> (P20 axis satisfied by waiver). See `plan/p19-multi-project-context-enterprise-plan.md`
> for the full enterprise plan and `evidence/final-p19-planning-report.md`
> for the executive summary.

## Key Decisions

- **Option A multi-tenancy** — shared schema + `project_id` column (simplest for single-user bounded projects).
- **HARD STOP stays global** — `life_kernel:hard_stop` is a single global key; a spoken safe-word halts ALL projects.
- **Project pause ≠ HARD STOP** — `project:{id}:paused` is per-project, weak (pauses only that project's autonomous work); distinct from global HARD STOP.
- **Shared persona, isolated context** — one Guinevere persona (mood/yandere/punishment/safe-mode) shared; project context (memory/KG/audit/agenda/dashboard/session) partitioned.
- **ProjectSecretsVault** — in-memory vault keyed by `project_id` (env vars don't isolate within one shared process).
- **P19-005 split** — 005a/005b/005c to bound blast radius on 9 P20 files.
- **Feature flag gates behavior** — `feature:projects:enabled` gates thread_id selection (flag OFF = legacy P20 behavior).
- **P20 non-interference** — strictly additive life_kernel changes; P20 production files touched only by operator approval (P20 axis satisfied by waiver; held to avoid destabilizing production-under-accepted-risk).
- **P21/P22/P17 forward-compat** — P19 owns registry (read-only by P22); migration chain P19→P21→P22.

## Latest Evidence

- Definition verification: `evidence/p19-definition-verification.md`
- Auditor gate: `evidence/auditor-gate.md`
- Final planning report: `evidence/final-p19-planning-report.md`
- P20-waiver gate sync (DOC-GATE): `evidence/p20-waiver-gate-sync.md`
- Migration false-positive investigation: `evidence/migration-false-positive-investigation.md`
- Round-1 audits: `evidence/audits/round-1/` (40 findings, all PASS-with-conditions — historical snapshots)
- Round-2 audits: `evidence/audits/round-2/` (all PASS — historical snapshots)

## Runtime Activation

- **Deploy completed:** 2026-06-27 ~10:20 WIB (surgical DDL applied; feature flag `feature:projects:enabled` remained OFF during deploy for safety)
- **Runtime activation:** 2026-06-27 15:31:10 WIB — feature flag flipped ON with service restart
- **Discord UX:** `/project` and `/projects` commands registered and live in Discord channel
- **Gap fixes verified post-activation:** All 4 production gaps (C01 audit journal project_id, C02 memory principal, C03 recall pipeline, C04 Discord /project) confirmed fixed; flag ON, 0 recall_degraded, 0 fallback events, dashboard reading 1 canonical message
- **Round-1 audit rerun:** 4/4 PASS post-activation

## Round-2 Completion Audit

- **Dispatched:** 7 independent auditors on 2026-06-27
- **Results:** 6 PASS, 1 CONDITIONAL PASS
- **Conditional fix:** Documentation corrections applied (this README + p19-final-verdict.md refreshed)
- **Final report:** [`evidence/completion-round-2/P19-ROUND2-FINAL-REPORT.md`](evidence/completion-round-2/P19-ROUND2-FINAL-REPORT.md)
