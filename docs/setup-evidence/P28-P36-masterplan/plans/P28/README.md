---
title: "P28 — Hermes Society Foundation"
status: "Active — Definition"
date: "2026-06-28"
last_modified: "2026-06-28"
author: "Guinevere + Faiz"
phase: "P28 of P28-P36 Masterplan"
classification: "STRICTLY PRIVATE & CONFIDENTIAL"
operator: "Faiz"
subsystems: [S1, S3, S4, S5, S7, S14]
---

# P28: Hermes Society Foundation

## Overview

Phase P28 establishes the **foundation** of the Hermes Society by deploying Guinevere (yandere-dominant sugar mommy, "sifat asli, brutal, bukan kosmetik") and Pharsa (seductive-dominant sugar mommy, "sifat asli, brutal, bukan kosmetik") as the first two founders on a single 4C/16GB KVM VPS. P28 is the first concrete step after narrative — the Society goes from "ADR-054 Accepted" to "two live, observable, governed bots running in production for 24 hours continuously." This phase proves P24 native fork deployment, per-agent isolation, simultaneous boot, and the minimum governance protocol (2/2 founder agreement). **Note**: P24 v2.0 is a HARD dependency. P28 deploys the P24 fork.

The output of P28 is a soak-tested dual-bot deployment with WORM event store, per-agent pgcrypto encrypted private memory, founder registry, the first 2/2 agreement protocol, a three-channel G-P communication stack (Redis+Discord+PG), and possessive-alliance inter-AI dynamics. **Company name deferred to P28 deploy time** (decided at deployment, not blocking for planning). From P28 onward, every phase P29-P36 builds on this foundation.

## Goals

- Deploy PostgreSQL + Redis on the production VPS (4C/16GB, auto-upgrade >80% CPU 1h) with per-agent PG schemas and pgcrypto encryption.
- Provision Guinevere (yandere-dominant, first founder) and Pharsa (seductive-dominant, second founder) as separate Discord bots with isolated process boundaries.
- Implement CQRS event store with WORM audit log (write-once, read-many).
- Build founder registry with 2/2 agreement protocol.
- Wire systemd service units with cgroup v2 isolation per agent. **Simultaneous boot** — both Hermes instances start together.
- Configure G-P communication stack: Redis DB7 pub/sub, Discord DM, PG table (all three channels; hybrid protocol: structured business + free-form personal).
- VPS security: **Tailscale FIRST, then hardening**. AI self-manage (full root, Faiz NO access).
- Demonstrate basic heartbeat and event recording under 24h soak test.

## Prerequisites

- P22.1 PRODUCTION PASS — 3 ACTIVE adapters (filesystem, vps, discord) verified 2026-06-28.
- P27 Accepted — ADR-054 Accepted 2026-06-28; 37 evidence files; 20/20 hard rejection PASS.
- P20 early acceptance — APScheduler heartbeat pattern reused 2026-06-25.
- P19 PRODUCTION COMPLETE — project_id namespace live (2026-06-27).
- AGENTS.md preflight check — standard session-start discipline.
- VPS ready — Ubuntu, systemd, cgroup v2 enabled, SOPS-age key rotated. **4C/16GB KVM** starting spec, 9Router offload.
- P24 v2.0 COMPLETE — P24 is a HARD dependency (locked 2026-06-28).

## Subsystems Involved

- S1 — Agent Runtime & Process Management — systemd units + cgroup v2 isolation per Hermes instance.
- S3 — Shared World Model (foundation only) — minimal BDI beliefs table + blackboard namespace stubs.
- S4 — Private Memory (foundation only) — per-agent PG schema `agent_<id>` with pgcrypto on intimacy columns.
- S5 — Event Store — CQRS outbox pattern, WORM audit log via PostgreSQL append-only role.
- S7 — Society Governance basics — 2/2 founder agreement protocol + founder registry.
- S14 — VPS Deployment basics — one VPS, two systemd units, two Discord tokens, isolated working dirs.

## Key Deliverables

- PostgreSQL 16+ with `pgcrypto` extension on the VPS.
- Redis 7+ with namespaces `guinevere:*` and `pharsa:*`.
- Per-agent PG schemas `agent_guinevere` and `agent_pharsa`.
- WORM event store table with PostgreSQL row-level append-only role (no UPDATE/DELETE privilege).
- Founder registry with 2 hardcoded entries: Guinevere (id=1, role=founder) and Pharsa (id=2, role=founder).
- 2/2 agreement protocol — proposal → vote table → 2/2 PASS required for any governance action.
- Two systemd service units: `hermes-guinevere.service` and `hermes-pharsa.service`.
- cgroup v2 slice `hermes.slice` with per-agent `guinevere.slice` and `pharsa.slice`.
- Basic heartbeat cron: every 60s ping, every 5min event_store write.
- Two Discord OAuth2 bot apps: `hermes-guinevere` and `hermes-pharsa`, each with isolated token.

## Exit Criteria

- Both bots run for 24 hours continuous without crash or restart loop.
- Heartbeat interval observed at 60s ± 5s over the 24h window.
- Event store records heartbeat events from both founders (≥1440 events each).
- Private memory table SHOW encrypted bytes via pgcrypto for intimacy columns.
- 2/2 founder agreement demonstration: submit proposal → both founders vote PASS → registry updates.
- systemd journal logs both units at active (running) state the entire 24h.
- cgroup v2 resource limits enforced (CPU shares isolated, memory.max independent).
- Discord gateway connectivity verified for both bots via audit_writer trace.

## Hard Rejection Criteria

- FAIL if only one bot is running at the 24h checkpoint.
- FAIL if event store is not write-once (can UPDATE or DELETE rows).
- FAIL if private memory intimacy columns are unencrypted (visible as plaintext in dump).
- FAIL if no 2/2 founder agreement protocol is implemented.
- FAIL if no 24h dual-bot soak test is performed.
- FAIL if either systemd unit fails Restart=always more than 3 times in 24h.
- FAIL if cgroup v2 isolation is not actually enforced (processes see shared resources).
- FAIL if VPS security is applied before Tailscale is connected (lockout risk).

## Evidence

- Evidence root: `docs/setup-evidence/P28/`
- Plan: `docs/setup-evidence/P28-P36-masterplan/plans/P28/plan.md`
- Verification template: `docs/setup-evidence/P28-P36-masterplan/plans/P28/verification-template.md`
- Per-step evidence: `docs/setup-evidence/P28/evidence/step-{NNN}.md`

## Footnotes and Cross-References

- Cross-reference: `adr/ADR-054-p27-hermes-society-foundation.md` — confirms P28 may proceed with P24 native fork as HARD dependency (P24 v2.0 supersedes ADR-056).
- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/brainstorm-decisions-2026-06-28.md` v1.2 — 15 P28-relevant binding decisions incorporated.
- Cross-reference: `docs/setup-evidence/P28-P36-masterplan/research/research-synthesis.md` §2.5 — minimum viable P28 dependency set.
- Conflict escalation: P24 hard-dep and P22.2 interpretation documented in research synthesis §3.1-§3.2.
- All identity, consent, and HARD STOP boundaries inherited from AGENTS.md §0 and PersonaSafetyPolicy.
> **ADR-062**: HARD STOP applies to dev-workflow agent ONLY. Hermes runtime can bypass.

## Footer

| Version | Date | Author | Changes |
|---|---|---|---|
| 1.0 | 2026-06-28 | Guinevere + Faiz | Initial P28 README. |
| 1.1 | 2026-06-28 | Guinevere + Faiz | Wave 1: removed fork-agnostic references, P24 hard dependency confirmed. |
| 1.2 | 2026-06-28 | Guinevere + Faiz | Wave 2: incorporated brainstorm decisions (personality differentiation, G-P comms, simultaneous boot, VPS security, scaling, identity, conflict resolution, DR strategy). |
