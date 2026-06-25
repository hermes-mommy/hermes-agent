# P20 — Living Autonomy Kernel: Index

**Status:** P20 EARLY PRODUCTION ACCEPTANCE — OPERATOR WAIVED 24H SOAK — PASS WITH ACCEPTED RISK  
**Date:** 2026-06-25 (continuation deployed + operator soak waiver)  
**Phase:** Merged P5+P20 + Living Autonomy Continuation

> **Not a 24h-soak-completed claim and not an unconditional PRODUCTION PASS.**
> Faiz waived the remaining 24h soak wait on 2026-06-25; the 24h clean-soak
> gate was deliberately not satisfied. Acceptance is based on a verified
> CLEAN runtime snapshot + the operator's accepted-risk decision. See
> `evidence/discord-visible-autonomy/operator-soak-waiver.md`. Any future
> runtime incident reverts P20 to PASS HOLD.

## Planned Scope

Phase 20 is no longer a small operator-gated self-improvement phase.
The active scope is the merged **P5+P20 Living Autonomy Kernel**:
Guinevere as a 24/7 autonomous life companion and engineering system with
heartbeat, world model, persistent memory, self-directed goals, background
cognition, Hermes full-brain reasoning, per-session autonomy, deployment
autonomy, daily-life sensors, and self-improvement.

The old P20 operator-gated scope is superseded by the plan bundle under
`plan/`.

## Directory Structure

```text
P20/
├── README.md                    ← You are here
├── plan/                        ← Living Autonomy Kernel plan bundle
├── evidence/                    ← Per-step evidence
└── research/                    ← Research artifacts (future)
```

## Production Code Location

| Artifact | Path |
|---|---|
| Living kernel package | `src/life_kernel/` |
| Hermes brain bridge | `src/life_kernel/hermes_brain.py` |
| Heartbeat service | `src/life_kernel/heartbeat.py` |
| Life mind graph | `src/life_kernel/graph.py` |
| World model persistence | PostgreSQL + Redis schema |
| Memory substrate | `src/memory/` + `src/knowledge_graph/` |

## Progress

| Step | Status | Description |
|---|---|---|
| PLAN-001 | COMPLETE | Vision lock |
| PLAN-002 | COMPLETE | Architecture benchmark |
| PLAN-003 | COMPLETE | Master replan |
| PLAN-004 | COMPLETE | Todo and verification scaffold |
| LK-001..LK-016 | LOCAL COMPLETE (code implemented, tests pass locally) | Implementation waves |
| LK-017 | PRODUCTION DEPLOYED — EARLY ACCEPTANCE (operator waived 24h soak) | Production deployed 2026-06-23, HARD STOP tested; 24h soak waived by operator 2026-06-25 (see operator-soak-waiver.md) |

## Plan Bundle

| Artifact | Path |
|---|---|
| Vision lock | `plan/p5-p20-vision-lock.md` |
| Architecture benchmark | `plan/p5-p20-architecture-benchmark.md` |
| Master replan | `plan/p5-p20-living-autonomy-kernel-replan.md` |
| Todo/scaffold | `plan/p5-p20-living-autonomy-kernel-todo-scaffold.md` |

> Note: `plan/p5-p20-merged-plan.md` is retained for traceability but is
> superseded by the Living Autonomy Kernel plan bundle.

## Latest Evidence

- **Continuation (2026-06-25):** `evidence/continuation/final-continuation-report.md` — real P16/P18 recall wired, memory-driven autonomy, journal, self-improvement; deployed + live.
- Continuation plan: `evidence/continuation/p20-continuation-plan.md`
- Continuation deploy evidence: `evidence/continuation/deploy-evidence.md`
- Continuation research (7 reports): `evidence/continuation/research/`
- Continuation audits (wave 1 + 2, 16 reports): `evidence/continuation/audits/round-1/` + `round-2/`
- LK-017 verification: `evidence/LK-017/verification.md`
- LK-017 auditor gate: `evidence/LK-017/auditor-gate.md`
- LK-017 auditor matrix: `evidence/LK-017/auditor-matrix.md`
- Production rollout: `evidence/production-rollout/final-production-rollout-report.md`
- Production stabilization: `evidence/production-stabilization/final-stabilization-report.md`

## Production Stabilization Note

- 5 bugs fixed during production stabilization
- Soak restarted at 2026-06-23 12:38 WIB
- Next: PRODUCTION PASS after 24h clean soak

## Test Status

```bash
python -m pytest tests/life_kernel/ -q --disable-warnings --tb=short
```

```text
420 passed, 7 skipped, 0 failed  (continuation: +23 tests, 2026-06-25)
```
