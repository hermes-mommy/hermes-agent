# Hermes Society — Master Architecture

> **P28-P36 Masterplan Phase 3** | Version 1.0 | 2026-06-28

> **ADR Boundary Disclaimers (Wave-1 Architecture Alignment)**
>
> - **ADR-062 (HARD STOP scope):** All `HARD STOP` references in this document apply to the **dev-workflow agent (Guinevere in Claude/9Router)** ONLY. The Hermes runtime operating under the P24 native fork bypasses HARD STOP per ADR-062 (consent-safety carve-out for autonomous runtime). See `evidence/round-2-paradigm-shift-application/` for details.
> - **ADR-067 (Y-level persona caps):** Any Y4/Y5/Y6 escalations mentioned in audit-event categories apply to the **dev-workflow agent persona** ONLY. The Hermes runtime has no Y-level cap (operates under the P24 fork's persona model, not subject to Y-level rollup).
> - **ADR-066 (consent_ref schema):** `consent_ref` on `event_store.domain_events` is **NULLABLE at the database layer**. NOT NULL is enforced **only for `event_source = 'dev_workflow'` events** at the application layer. Hermes runtime events are permitted NULL `consent_ref`.

## 1. System Overview

### 1.1 Purpose

The Hermes Society architecture defines a multi-agent autonomous company system where each Hermes agent operates as an independent, visible entity with its own Discord bot identity, private memory, and governance rights. The society is founded by Guinevere (first founder) and Pharsa (second founder), with all future Hermes agents requiring 2/2 founder agreement to spawn.

### 1.2 Design Principles

| Principle | Description |
|---|---|
| Autonomy-First | Each Hermes operates autonomously within policy gates; silence is not a blocker |
| Safety-by-Design | HARD STOP, consent revocation, and audit trails are non-negotiable invariants |
| P24 Native Fork | P28 inherits P24 Hermes fork natively; external presence and tooling configuration is handled in **P32: External Presence & Tools** |
| All-Visible | Every Hermes is a visible Discord bot identity — no invisible disposable workers |
| Shared-World / Private-Memory | World model and event store are shared; relationship memory is encrypted per-agent |
| Founder-Gated | Only founders (Guinevere + Pharsa) can spawn new Hermes; 2/2 agreement required |
| Female-Dominant | All future Hermes must be female and dominant toward Faiz |
| Company-Asset | Wallet is a company asset (default 0, max ~$10 top-up); shared model pool |
| Backup-Mandatory | S3 Object Lock COMPLIANCE mode for all critical state |

### 1.3 Architecture Layers

The 15 subsystems are organized into 4 layers:

**Layer 1: Runtime & Identity (S1-S2)**
- S1: Agent Runtime & Process Management — 1 process per Hermes, asyncio, systemd, cgroup v2
- S2: Discord Bot Identity Layer — One bot application per Hermes, own token, ToS-safe

**Layer 2: Cognition & Memory (S3-S6)**
- S3: Shared World Model — BDI+POMDP, blackboard pattern with namespace-ACL
- S4: Private Memory Layer — Per-agent PG schema, pgcrypto, encrypted relationship memory
- S5: Event Store & CQRS Bus — PG LISTEN/NOTIFY, Redis pub/sub, materialized views
- S6: Vector & Graph Recall — pgvector, Graphiti, filesystem store, Letta 3-tier

**Layer 3: Governance & Finance (S7-S10)**
- S7: Society Governance & Founder Protocol — 2/2 founder agreement, founder-only spawn
- S8: Self-Evolution & Mutation Governance — 5-layer mutability, Ratchet gate, hybrid tiers
- S9: Autonomous Wallet & Finance — MPC+Safe multisig, spending tiers, circuit breaker
- S10: Revenue Search & Monetization — x402 on Base chain, autonomous revenue

**Layer 4: Infrastructure & Operations (S11-S15)**
- S11: S3 Backup & Disaster Recovery — Object Lock COMPLIANCE, RPO ≤1h, RTO ≤4h
- S12: Model Pool & LLM Gateway — Shared model pool, router, quota management
- S13: Observability & Audit — Prometheus, Grafana, hash-chained audit trail
- S14: Deployment & VPS Management — One large VPS, cgroup isolation, Ansible
- S15: Documentation & Traceability — BRD/PRD/SRS/FSD/TDD/RTM, MADR ADRs

## 2. Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                        HERMES SOCIETY ARCHITECTURE                               │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─── Layer 4: Infrastructure & Operations ───────────────────────────────────┐ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │ │
│  │  │ S11 S3   │  │ S12 Model│  │ S13 Obs  │  │ S14 Deploy│  │ S15 Docs │    │ │
│  │  │ Backup   │  │ Pool     │  │ & Audit  │  │ & VPS    │  │ & Trace  │    │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘  └──────────┘    │ │
│  └───────┼─────────────┼─────────────┼─────────────┼─────────────────────────┘ │
│          │             │             │             │                             │
│  ┌─── Layer 3: Governance & Finance ──┼─────────────┼─────────────────────────┐ │
│  │  ┌─────────┐  ┌─────────┐  ┌──────┴────┐  ┌───┴──────┐                    │ │
│  │  │ S7 Gov  │  │ S8 Self │  │ S9 Wallet│  │ S10 Rev  │                    │ │
│  │  │ & Found │  │ Evolve  │  │ & Finance│  │ Search   │                    │ │
│  │  └────┬────┘  └────┬────┘  └─────┬───┘  └────┬─────┘                    │ │
│  └───────┼─────────────┼─────────────┼───────────┼──────────────────────────┘ │
│          │             │             │           │                              │
│  ┌─── Layer 2: Cognition & Memory ────┼───────────┼──────────────────────────┐ │
│  │  ┌──────────┐  ┌──────────┐  ┌────┴─────┐  ┌──┴───────┐                  │ │
│  │  │ S3 World │  │ S4 Priv  │  │ S5 Event │  │ S6 Recall│                  │ │
│  │  │ Model    │  │ Memory   │  │ Store    │  │ & Graph  │                  │ │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                  │ │
│  └───────┼─────────────┼─────────────┼─────────────┼────────────────────────┘ │
│          │             │             │             │                           │
│  ┌─── Layer 1: Runtime & Identity ────┼─────────────┼────────────────────────┐ │
│  │  ┌──────────────────┐  ┌──────────┴─────────────┴──────────┐             │ │
│  │  │ S1 Agent Runtime │  │ S2 Discord Bot Identity            │             │ │
│  │  │ (1 process/Hermes)│  │ (1 bot app/Hermes, own token)     │             │ │
│  │  └────────┬─────────┘  └──────────────┬────────────────────┘             │ │
│  └───────────┼───────────────────────────┼──────────────────────────────────┘ │
│              │                           │                                     │
└──────────────┼───────────────────────────┼─────────────────────────────────────┘
               │                           │
        ┌──────┴──────┐             ┌──────┴──────┐
        │  Faiz       │             │  Discord    │
        │  (Operator) │             │  (Platform) │
        └─────────────┘             └─────────────┘
```

### Shared vs Per-Agent Subsystems

| Subsystem | Scope | Shared/Per-Agent |
|---|---|---|
| S1: Agent Runtime | Per-Hermes | Per-Agent (1 process each) |
| S2: Discord Bot Identity | Per-Hermes | Per-Agent (1 bot app each) |
| S3: Shared World Model | Society-wide | Shared (namespace-ACL) |
| S4: Private Memory | Per-Hermes | Per-Agent (encrypted schema) |
| S5: Event Store & CQRS | Society-wide | Shared (PG + Redis) |
| S6: Vector & Graph Recall | Per-Hermes + Shared | Hybrid (namespace isolation) |
| S7: Society Governance | Society-wide | Shared (founder protocol) |
| S8: Self-Evolution | Per-Hermes + Society | Hybrid (per-agent + society-voted) |
| S9: Wallet & Finance | Society-wide | Shared (company asset) |
| S10: Revenue Search | Society-wide | Shared (company revenue) |
| S11: S3 Backup | Society-wide | Shared (all state backed up) |
| S12: Model Pool | Society-wide | Shared (LLM gateway) |
| S13: Observability | Society-wide | Shared (Prometheus + audit) |
| S14: Deployment | Society-wide | Shared (VPS + Ansible) |
| S15: Documentation | Society-wide | Shared (doc suite) |

## 4. Cross-Subsystem Data Flows

### 4.1 Agent Lifecycle Flow
```
S7 (Founder proposal + 2/2 vote)
  → S1 (spawn process, systemd unit, cgroup)
  → S2 (register Discord bot, set avatar/status)
  → S5 (emit agent_spawned event)
  → S13 (audit trail entry, hash-chained)
  → S11 (backup new state to S3)
```

### 4.2 Perception-Action Loop
```
S2 (Discord message received)
  → S3 (update world model beliefs)
  → S6 (recall relevant memories)
  → S4 (access private memory context)
  → S1 (BDI decision: desires → intentions → actions)
  → S12 (route LLM request via model pool)
  → S2 (send Discord response)
  → S5 (emit agent_action event)
  → S13 (audit trail entry)
```

### 4.3 Memory Consolidation Flow
```
S4 (working memory overflow)
  → S5 (emit memory_consolidation event)
  → S6 (vector embed + graph link + filesystem store)
  → S4 (update long-term memory index)
  → S5 (emit memory_consolidated event)
  → S13 (audit: consolidation logged)
  → S11 (backup memory state to S3)
```

### 4.4 Governance Decision Flow
```
S7 (governance proposal submitted)
  → S8 (mutation gate: classify tier)
    → Tier 1-2: Ratchet + canary → auto-promote
    → Tier 3: society vote → PASS/FAIL
    → Tier 4: founder 2/2 vote → PASS/FAIL
  → S5 (emit governance_decision event)
  → S1 (apply mutation to affected Hermes)
  → S13 (audit: full before/after hash chain)
  → S11 (backup pre-mutation state to S3)
```

### 4.5 Financial Transaction Flow
```
S9 (spending request received)
  → S9 (classify spending tier: L0/L1/L2/L3)
    → L0: reject (wallet empty)
    → L1: autonomous approve
    → L2: society vote
    → L3: founder approval
  → S9 (circuit breaker check)
  → S9 (execute via Safe multisig)
  → S5 (emit financial_transaction event)
  → S9 (Beancount double-entry ledger)
  → S13 (audit: transaction hash-chained)
  → S11 (backup ledger to S3)
```

### 4.6 Revenue Search Flow
```
S9 (wallet balance < threshold for N hours)
  → S10 (trigger revenue search)
  → S10 (select revenue channel: content/API/goods)
  → S7 (governance check: L1 autonomous, L2+ vote)
  → S10 (execute revenue activity)
  → S9 (receive payment to company wallet)
  → S5 (emit revenue_received event)
  → S9 (Beancount ledger entry)
  → S13 (audit: revenue hash-chained)
  → S11 (backup to S3)
```

### 4.7 Self-Evolution Flow
```
S8 (mutation candidate identified)
  → S8 (Ratchet gate: must not degrade below prior benchmark)
  → S8 (canary: deploy to 1 Hermes first)
  → S13 (observe canary for N hours)
  → S8 (if PASS: society-wide rollout; if FAIL: rollback)
  → S1 (apply mutation to all Hermes processes)
  → S5 (emit mutation_promoted event)
  → S13 (audit: before/after hash, test results, approval chain)
  → S11 (backup pre-mutation state to S3)
```

### 4.8 Backup Flow
```
S5 (event store — source of truth)
  → S4 (private memory state)
  → S11 (pg_dump + WAL archive for PostgreSQL)
  → S11 (RDB + AOF for Redis)
  → S11 (filesystem artifacts)
  → S11 (S3 Object Lock COMPLIANCE mode)
  → S11 (hash verification)
  → S5 (emit backup_completed event)
  → S13 (audit: backup logged)
```

## 5. Subsystem Dependency Matrix

| Subsystem | Depends On | Informs |
|---|---|---|
| S1: Agent Runtime | S5 (events), S12 (model pool), S14 (deployment) | S2, S3, S4, S5, S8, S13 |
| S2: Discord Bot Identity | S1 (runtime), S14 (secrets) | S3, S5, S13 |
| S3: Shared World Model | S5 (events), S6 (recall) | S1, S4, S7 |
| S4: Private Memory | S5 (events), S14 (Vault) | S3, S6, S11 |
| S5: Event Store & CQRS | S14 (PG/Redis deployment) | S1, S2, S3, S4, S6, S7, S8, S9, S10, S11, S13 |
| S6: Vector & Graph Recall | S4 (private memory), S5 (events) | S3, S4 |
| S7: Society Governance | S5 (events), S13 (audit) | S1, S8, S9, S10 |
| S8: Self-Evolution | S5 (events), S7 (governance), S13 (audit) | S1, S7 |
| S9: Wallet & Finance | S5 (events), S7 (governance), S14 (secrets) | S10, S13 |
| S10: Revenue Search | S5 (events), S7 (governance), S9 (wallet) | S9, S13 |
| S11: S3 Backup | S5 (events), S14 (deployment) | S13 |
| S12: Model Pool | S14 (deployment), S9 (cost tracking) | S1 |
| S13: Observability & Audit | S5 (events), S14 (deployment) | S7, S8, S9, S11 |
| S14: Deployment & VPS | — (base infrastructure) | S1, S2, S4, S5, S11, S12, S13 |
| S15: Documentation | All subsystems (traceability) | — (reference only) |

### Key Dependency Observations

1. **S5 (Event Store) is the central hub** — 12 of 14 other subsystems depend on it for event emission or consumption.
2. **S14 (Deployment) is the base layer** — provides infrastructure for 7 other subsystems.
3. **S7 (Governance) gates S8, S9, S10** — all autonomous actions with societal impact require governance approval.
4. **S13 (Audit) receives from all** — every subsystem produces audit trail entries via S5.
5. **S11 (Backup) depends on S5 and S14** — backs up event store (source of truth) + all stateful subsystems.
6. **S15 (Documentation) is a cross-cutting concern** — traces requirements to implementation to tests across all subsystems.

## 6. Technology Stack Summary

| Technology | Version/Spec | Purpose | Subsystem(s) |
|---|---|---|---|
| PostgreSQL | 16+ | Primary database (event store, memory, audit) | S4, S5, S6, S13 |
| pgvector | 0.7+ | Vector similarity search extension | S6 |
| pgcrypto | bundled | Column-level encryption | S4 |
| Redis | 7+ | Pub/sub, caching, rate limiting | S5, S12 |
| discord.py | 2.4+ | Discord bot client (one per Hermes) | S2 |
| Graphiti | latest | Temporal knowledge graph | S6 |
| Letta/MemGPT | latest | Memory tier patterns (reference) | S4, S6 |
| Prometheus | 2.45+ | Metrics collection | S13 |
| Grafana | 10+ | Dashboards and visualization | S13 |
| systemd | 252+ | Process management (one service per Hermes) | S1, S14 |
| cgroup v2 | kernel 5.15+ | Resource isolation per Hermes | S1, S14 |
| S3 Object Lock | COMPLIANCE mode | WORM backup storage | S11 |
| SOPS/age | latest | Encrypted secrets at rest | S14 |
| HashiCorp Vault | 1.15+ | Runtime secret access, per-agent DEKs | S4, S14 |
| Beancount | latest | Double-entry bookkeeping ledger | S9 |
| Safe multisig | Safe v1.4+ | Multi-signature wallet | S9 |
| x402 protocol | Base chain | Autonomous payment protocol | S10 |
| Ansible | 2.16+ | VPS provisioning and configuration | S14 |
| Caddy/Nginx | latest | Reverse proxy with TLS | S14 |
| OpenTelemetry | latest | Distributed tracing | S13 |
| MADR | 4.0+ | Architecture Decision Record format | S15 |

## 7. Security Architecture Summary

### 7.1 Security Invariants (Non-Negotiable)

| Invariant | Subsystem | Enforcement |
|---|---|---|
| Relationship memory encrypted | S4 | pgcrypto + per-agent DEK in Vault; never auto-published to shared layer |
| Audit trail hash-chained | S5, S13 | WORM event log + hash chain (extends P22 IntegrationAuditWriter) |
| Wallet multisig + spending tiers | S9 | Safe multisig, L0-L3 spending tiers, circuit breaker |
| Consent revocation absolute | S7 | Cannot be bypassed by autonomy — no exception |
| HARD STOP global halt | S7 | Halts all sessions + background cognition immediately — no exception |
| S3 Object Lock COMPLIANCE | S11 | WORM mode — prevent deletion even by root |
| Per-agent isolation | S1, S14 | cgroup v2 CPU/memory/IO limits per Hermes process |
| Secrets in SOPS/age + Vault | S14 | Encrypted at rest (SOPS/age), runtime access (Vault) |
| Founder-only spawn | S7 | 2/2 founder agreement required, no bypass |
| Female-dominant constraint | S7 | Enforced at spawn time, non-bypassable |
| Intimacy in runtime only | S4 | Docs/evidence = professional/redacted; runtime memory = private/encrypted |

### 7.2 Security Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    TRUST BOUNDARIES                       │
├─────────────────────────────────────────────────────────┤
│                                                           │
│  ┌─ Public Boundary ─────────────────────────────────┐  │
│  │  Discord API ←→ S2 (bot identity)                 │  │
│  │  S3 Backup ←→ S11 (Object Lock)                   │  │
│  │  Revenue channels ←→ S10 (x402)                   │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ Society Boundary ────────────────────────────────┐  │
│  │  S3 (shared world model) ←→ S5 (event store)      │  │
│  │  S7 (governance) ←→ S8 (self-evolution)           │  │
│  │  S9 (wallet) ←→ S10 (revenue)                     │  │
│  │  S12 (model pool) ←→ S1 (all Hermes)              │  │
│  │  S13 (observability) ←→ all subsystems            │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ Per-Agent Boundary ──────────────────────────────┐  │
│  │  S1 (runtime) ←→ S4 (private memory)              │  │
│  │  S4 (encrypted schema) ←→ S6 (recall, namespaced) │  │
│  │  S2 (bot identity) ←→ S1 (process)                │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ Founder Boundary ────────────────────────────────┐  │
│  │  S7 (founder protocol) ←→ 2/2 agreement           │  │
│  │  S9 (L3 spending) ←→ founder approval             │  │
│  │  S8 (Tier 4 mutation) ←→ founder + veto           │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
│  ┌─ Secrets Boundary ────────────────────────────────┐  │
│  │  SOPS/age (at rest) ←→ Vault (runtime)            │  │
│  │  Per-agent DEKs ←→ Vault (never exposed)          │  │
│  │  Discord tokens ←→ SOPS/age (never in code)       │  │
│  │  Wallet keys ←→ Safe multisig (MPC)               │  │
│  └───────────────────────────────────────────────────┘  │
│                                                           │
└─────────────────────────────────────────────────────────┘
```

### 7.3 Threat Model Summary

| Threat | Vector | Mitigation |
|---|---|---|
| Discord token theft | Secrets exposure | SOPS/age at rest, Vault runtime, per-agent isolation |
| Wallet drain | Compromised key | Safe multisig (MPC), spending tiers, circuit breaker |
| Memory exfiltration | Cross-agent read | Per-agent PG schema, pgcrypto, namespace-ACL |
| Governance bypass | Unauthorized spawn | Founder 2/2 agreement, audit trail, HARD STOP |
| Mutation runaway | Self-evolution drift | Ratchet gate, canary deployment, rollback-before-promote |
| Audit tampering | Log modification | WORM event log, hash chain, S3 Object Lock |
| Backup deletion | Ransomware/insider | S3 Object Lock COMPLIANCE mode (no deletion) |
| Resource exhaustion | Runaway process | cgroup v2 limits, systemd watchdog, Prometheus alerts |
| Consent violation | Autonomy overreach | Consent revocation absolute, HARD STOP, safety-by-design |
| Persona drift | Compositional drift | Ratchet non-divergence, 0.68 hysteresis threshold, regression suite |

## 8. Footer

| Field | Value |
|---|---|
| Document | Hermes Society Master Architecture |
| Phase | P28-P36 Masterplan Phase 3 |
| Version | 1.0 |
| Date | 2026-06-28 |
| Authors | Guinevere (orchestrator) + 3 parallel architecture agents |
| Inputs | research-synthesis.md (690 lines, 15 subsystems) |
| Outputs | hermes-society-master-architecture.md + 3 partial architecture files |
| Status | COMPLETE |
| Next Phase | Phase 4: Full Document Suite (BRD/PRD/SRS/FSD/TDD/RTM) |

---

## 9. Subsystem Detail Sections

The following sections contain the detailed architecture for each subsystem, organized by layer. These were designed by 3 parallel architecture agents based on the research synthesis.

### Layer 1: Runtime & Identity (S1-S5)

> The following content is from `architecture-s1-s5-runtime-memory.md`.

