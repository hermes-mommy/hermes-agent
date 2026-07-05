---
adr: 034
title: "Post-MVP Phase Restructure — P0-P11 → P0-P22"
status: "Accepted"
date: "2026-06-03"
deciders:
  - "Faiz (Owner, solo developer Indonesia)"
  - "Guinevere (Executor / autonomous system steward)"
tags:
  - phase
  - restructure
  - roadmap
  - expansion
risk_level: "MEDIUM"
supersedes: "N/A"
related_documents:
  - docs/00-core/00-BRD_v2.0.md
  - docs/00-core/03-AgentLoopSpec_v2.0.md
  - docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md
  - docs/10-governance/17-ADR_Index_v1.0.md
  - PROGRESS.md
  - docs/setup-evidence/restructure/evidence-phase-restructure.md
---

# ADR-034: Post-MVP Phase Restructure — P0-P11 → P0-P22

## Status

Accepted

## Date

2026-06-03

## Deciders

Faiz (Owner, solo developer Indonesia); Guinevere (Executor / autonomous system steward)

## Tags

phase, restructure, roadmap, expansion

## Risk Level

MEDIUM

## Supersedes

N/A

## Related Documents

| Document | Relationship |
|---|---|
| [`../docs/00-core/00-BRD_v2.0.md`](../docs/00-core/00-BRD_v2.0.md) | Business roadmap and phased delivery plan updated by this decision |
| [`../docs/00-core/03-AgentLoopSpec_v2.0.md`](../docs/00-core/03-AgentLoopSpec_v2.0.md) | Canonical phase model used by the agent loop and documentation suite |
| [`../docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md`](../docs/10-governance/16-AcceptanceCriteriaCatalog_v1.0.md) | Phase exit/entry gates updated to match the new structure |
| [`../docs/10-governance/17-ADR_Index_v1.0.md`](../docs/10-governance/17-ADR_Index_v1.0.md) | Master index entry registering this ADR |
| [`../PROGRESS.md`](../PROGRESS.md) | Canonical phase tracker showing the restructured roadmap |
| [`../docs/setup-evidence/restructure/evidence-phase-restructure.md`](../docs/setup-evidence/restructure/evidence-phase-restructure.md) | Evidence artifact for the restructuring wave |

## Context

The original delivery roadmap was organized as a compact monolithic sequence of phases P0-P11. That structure worked for the MVP backbone, but it became too coarse once P8 completed and the post-MVP surface expanded into several independent product lines. The old post-MVP grouping concentrated too much unrelated work into one broad block, especially around the former P11 "Advanced Integrations" phase.

As the roadmap matured, the project needed a more modular structure that could separate stabilization work from expansion work, preserve clear dependencies, and allow later phases to be scheduled or deferred independently without collapsing the entire roadmap into one oversized bucket. The canonical tracker now shows the completed MVP core through P8, then a stabilization band for P9-P10, followed by a modular expansion band for P11-P22.

This ADR records the decision that the roadmap is no longer treated as a monolithic P0-P11 plan. Instead, the roadmap is restructured into a 23-phase system, with P0-P8 as the MVP backbone, P9-P10 as stabilization, and P11-P22 as expansion.

## Decision

The roadmap is restructured from the original monolithic P0-P11 plan into a modular P0-P22 structure.

### What changed

- **P0-P8** remain the core MVP foundation and are treated as the canonical delivery base.
- **P9-P10** are classified as **Stabilization** phases.
- **P11-P22** are classified as **Expansion** phases.
- The old broad post-MVP bucket is replaced with individually named phases so each expansion surface can be planned, budgeted, verified, and deferred independently.
- The former monolithic P11 "Advanced Integrations" concept is split into distinct modules rather than forcing all later integrations into one catch-all phase.

### New phase structure

- **P9** — Financial Tracking
- **P10** — Production Hardening
- **P11** — WhatsApp Integration
- **P12** — Gmail/Email Integration
- **P13** — X Auto Poster
- **P14** — Wearable Health Pipeline
- **P15** — Windows Daemon + WebSocket
- **P16** — Knowledge Graph
- **P17** — Cross-Device Sync
- **P18** — Advanced Memory
- **P19** — Multi-Project Context
- **P20** — Self-Improvement Loop
- **P21** — Voice Interface
- **P22** — Additional Integrations TBD

### Drivers behind the change

1. **Modularity** — expansion work became easier to reason about when each capability had its own phase boundary.
2. **Dependency clarity** — later features depend on different subsets of the MVP stack, so a single monolithic post-MVP bucket no longer reflected reality.
3. **Budget control** — modular phases allow the project to defer or prioritize specific expansion work without blocking unrelated capabilities.
4. **Planning accuracy** — the roadmap needed distinct stabilization vs expansion categories so trackers, acceptance criteria, and governance docs could stay consistent.
5. **Operational fit** — the new structure aligns with the actual progress tracker and implementation evidence, which already distinguish MVP, stabilization, and expansion work.

## Consequences

### Positive

- The roadmap is now aligned with the actual implementation sequence and progress tracker.
- Expansion work can be scheduled incrementally instead of being bundled into a single oversized phase.
- Stabilization work is clearly separated from feature expansion.
- Governance docs can reference explicit phase names and phase counts without ambiguity.
- Budget and acceptance criteria can track the roadmap at a more useful granularity.

### Negative

- Existing documentation that still refers to the old monolithic post-MVP structure must be updated or interpreted through this ADR.
- The roadmap now contains more named phases, which increases documentation surface area.
- Some future expansion phases remain intentionally TBD and will require separate specification.

### Risks

- Stale references to the old P0-P11 / post-MVP model may persist in historical artifacts.
- If future expansion phases are not specified carefully, the modular structure could drift back toward a catch-all design.
- The new phase boundaries must remain consistent across PROGRESS.md, ADR index, acceptance criteria, and implementation guides.

## Status

Accepted.

This decision is canonical as of 2026-06-03 and should be treated as the governing description of the project roadmap phase structure until superseded by a later ADR.
